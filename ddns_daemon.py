#!/usr/bin/env python3
"""DDNS IPv6 后台守护进程（含 WebUI）

定时检测本机 IPv6 地址变化，通过 dnshe.com API 自动更新 AAAA 记录。
同时内嵌 WebUI 管理界面（子线程运行 uvicorn），
支持多域名配置，与 WebUI 共享配置文件和 SQLite 数据库。
"""

import sys
import time
import os
import threading

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core import load_config, check_and_update_domain, log, get_ipv6_address, get_ipv4_address
from app.models import add_log, upsert_domain_status


def start_webui(config: dict) -> None:
    """在子线程中启动 WebUI（同时监听 IPv4 和 IPv6）"""
    import socket

    web_cfg = config.get("web", {})
    host = web_cfg.get("host", "0.0.0.0")
    port = web_cfg.get("port", 5080)

    try:
        import uvicorn
        from app.webui import app

        # 创建 IPv6 socket（IPV6_V6ONLY=0 同时处理 IPv4 映射连接）
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        sock.bind(("::", port))
        sock.listen(2048)

        log(f"[INFO] WebUI 启动: http://[::]:{port} (IPv4+IPv6)")

        # 使用 uvicorn.Server 方式传入自定义 socket
        from uvicorn.config import Config
        from uvicorn.server import Server
        cfg = Config(app=app, log_level="warning")
        server = Server(cfg)
        server.run(sockets=[sock])
    except ImportError:
        log("[WARN] uvicorn 未安装，WebUI 不可用")
    except Exception as e:
        log(f"[ERROR] WebUI 启动失败: {e}")


def main() -> None:
    """主循环（双循环架构：快速检测 + 全量同步）"""
    log("=" * 50)
    log("DDNS IPv6 守护进程启动（含 WebUI）")

    config = load_config()
    daemon_cfg = config.get("daemon", {})
    domains = config.get("domains", [])

    # 在子线程中启动 WebUI
    webui_thread = threading.Thread(target=start_webui, args=(config,), daemon=True)
    webui_thread.start()
    log("[INFO] WebUI 子线程已启动")

    log(f"域名数量: {len(domains)}")
    full_check_interval = daemon_cfg.get("check_interval", 300)
    fast_check_interval = daemon_cfg.get("fast_check_interval", 10)
    # 强制全量兜底周期：超过该时长强制真查远端（防远端记录被外部改动/删除），
    # 期间若本机 IP 未变则跳过 API 调用，避免 dnshe 60次/分钟限流
    force_full_interval = daemon_cfg.get("force_full_interval", 1800)
    log(f"快速检测间隔: {fast_check_interval} 秒")
    log(f"全量同步间隔: {full_check_interval} 秒")
    log(f"强制全量周期: {force_full_interval} 秒")
    log("=" * 50)

    # 记录每个域名的上次同步结果（domain_id -> (ip, status)）
    last_sync_map: dict[str, tuple[str, str]] = {}
    # 记录本机当前 IPv6 地址（快速检测用）
    last_local_ipv6: str | None = None
    last_full_check_time = 0.0
    # 下次强制全量的时间点（启动首轮即强制）
    force_full_until = 0.0

    # 启动时立即执行一次全量同步（首轮强制）
    log("[INFO] 启动时执行首次全量同步检查（强制）")
    for domain_cfg in domains:
        domain_id = domain_cfg.get("id", domain_cfg["record_name"])
        if not domain_cfg.get("enabled", True):
            continue
        try:
            result = check_and_update_domain(config, domain_cfg)
            _handle_result(result, domain_id, last_sync_map)
        except Exception as e:
            log(f"[ERROR] 域名 {domain_cfg.get('record_name', '?')} 处理异常: {e}")
            add_log(domain_id=domain_id, record_name=domain_cfg.get("record_name", ""),
                    action="error", message=str(e))
            upsert_domain_status(domain_id=domain_id,
                                 record_name=domain_cfg.get("record_name", ""), status="error")
    last_full_check_time = time.time()
    force_full_until = time.time() + force_full_interval
    from app.models import save_last_full_check_time
    save_last_full_check_time(last_full_check_time)

    while True:
        try:
            # 热加载配置
            config = load_config()
            domains = config.get("domains", [])
            daemon_cfg = config.get("daemon", {})
            full_check_interval = daemon_cfg.get("check_interval", 300)
            fast_check_interval = daemon_cfg.get("fast_check_interval", 10)
            now = time.time()

            # ===== 快速检测：只查本机 IPv6 是否变化 =====
            interface = config.get("network", {}).get("interface", "")
            current_local_ipv6 = get_ipv6_address(interface)

            if current_local_ipv6 and current_local_ipv6 != last_local_ipv6:
                log(f"[INFO] 检测到本机 IPv6 地址变化: {last_local_ipv6} → {current_local_ipv6}，立即更新远端")
                last_local_ipv6 = current_local_ipv6
                last_full_check_time = now  # 重置全量检查计时器

                # 立即更新所有启用的域名
                for domain_cfg in domains:
                    domain_id = domain_cfg.get("id", domain_cfg["record_name"])
                    if not domain_cfg.get("enabled", True):
                        continue
                    try:
                        result = check_and_update_domain(config, domain_cfg)
                        _handle_result(result, domain_id, last_sync_map)
                    except Exception as e:
                        log(f"[ERROR] 域名 {domain_cfg.get('record_name', '?')} 处理异常: {e}")
                        add_log(domain_id=domain_id, record_name=domain_cfg.get("record_name", ""),
                                action="error", message=str(e))
                        upsert_domain_status(domain_id=domain_id,
                                             record_name=domain_cfg.get("record_name", ""), status="error")
            elif current_local_ipv6 is None:
                log("[WARN] 无法获取本机 IPv6 地址")
            else:
                # 地址未变化，记录首次获取的地址
                if last_local_ipv6 is None:
                    last_local_ipv6 = current_local_ipv6

            # ===== 全量同步：定期查询远端确保一致性（IP 未变则跳过 API） =====
            if now - last_full_check_time >= full_check_interval:
                force = now >= force_full_until
                if force:
                    log(f"[INFO] 执行强制全量同步检查（兜底校验远端，周期 {force_full_interval} 秒）")
                    force_full_until = now + force_full_interval
                else:
                    log(f"[INFO] 执行全量同步检查（间隔 {full_check_interval} 秒，IP 未变跳过 API）")
                last_full_check_time = now
                from app.models import save_last_full_check_time
                save_last_full_check_time(last_full_check_time)

                # IPv4 目标 IP 缓存（全量同步一轮只查一次外部服务，避免重复请求）
                cached_ipv4: str | None = None

                for domain_cfg in domains:
                    domain_id = domain_cfg.get("id", domain_cfg["record_name"])
                    if not domain_cfg.get("enabled", True):
                        continue

                    # 优化：非强制轮次且上次同步成功且 IP 未变 → 跳过远端 API 调用
                    if not force:
                        prev_ip, prev_status = last_sync_map.get(domain_id, (None, None))
                        # 按记录类型取当前目标 IP：A 记录用 IPv4，其余用 IPv6
                        if domain_cfg.get("record_type", "AAAA") == "A":
                            if cached_ipv4 is None:
                                cached_ipv4 = get_ipv4_address()
                            target_ip = cached_ipv4
                        else:
                            target_ip = current_local_ipv6
                        if prev_status == "ok" and prev_ip == target_ip:
                            continue

                    try:
                        result = check_and_update_domain(config, domain_cfg)
                        _handle_result(result, domain_id, last_sync_map)
                    except Exception as e:
                        log(f"[ERROR] 域名 {domain_cfg.get('record_name', '?')} 处理异常: {e}")
                        add_log(domain_id=domain_id, record_name=domain_cfg.get("record_name", ""),
                                action="error", message=str(e))
                        upsert_domain_status(domain_id=domain_id,
                                             record_name=domain_cfg.get("record_name", ""), status="error")

            time.sleep(fast_check_interval)

        except Exception as e:
            log(f"[ERROR] 主循环异常: {e}")
            time.sleep(60)


def _handle_result(result: dict, domain_id: str, last_sync_map: dict) -> None:
    """处理单个域名的检测结果（记录日志、更新状态）

    last_sync_map: domain_id -> (ip, status)，供全量同步跳过判断用
    """
    if result["action"] == "skip" and last_sync_map.get(domain_id, (None, None))[0] == result["new_ip"]:
        upsert_domain_status(
            domain_id=result["domain_id"],
            record_name=result["record_name"],
            current_ip=result["new_ip"],
            status="ok",
            is_update=False,
        )
    else:
        add_log(
            domain_id=result["domain_id"],
            record_name=result["record_name"],
            action=result["action"],
            old_ip=result["old_ip"],
            new_ip=result["new_ip"],
            message=result["message"],
        )
        upsert_domain_status(
            domain_id=result["domain_id"],
            record_name=result["record_name"],
            current_ip=result["new_ip"],
            status="ok" if result["action"] in ("create", "update", "skip") else "error",
            is_update=(result["action"] in ("create", "update")),
        )
    if result["new_ip"]:
        last_sync_map[domain_id] = (result["new_ip"], "ok" if result["action"] in ("create", "update", "skip") else "error")


if __name__ == "__main__":
    main()
