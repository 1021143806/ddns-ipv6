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

from app.core import load_config, check_and_update_domain, log
from app.models import add_log, upsert_domain_status


def start_webui(config: dict) -> None:
    """在子线程中启动 WebUI"""
    web_cfg = config.get("web", {})
    host = web_cfg.get("host", "0.0.0.0")
    port = web_cfg.get("port", 5080)

    try:
        import uvicorn
        from app.webui import app
        log(f"[INFO] WebUI 启动: http://{host}:{port}")
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except ImportError:
        log("[WARN] uvicorn 未安装，WebUI 不可用")
    except Exception as e:
        log(f"[ERROR] WebUI 启动失败: {e}")


def main() -> None:
    """主循环"""
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
    log(f"全局检查间隔: {daemon_cfg.get('check_interval', 300)} 秒")
    log("=" * 50)

    # 记录每个域名的上次 IPv6 地址，用于跳过未变化的情况
    last_ip_map: dict[str, str] = {}

    while True:
        try:
            # 热加载配置
            config = load_config()
            domains = config.get("domains", [])

            for domain_cfg in domains:
                domain_id = domain_cfg.get("id", domain_cfg["record_name"])

                # 跳过禁用的域名
                if not domain_cfg.get("enabled", True):
                    continue

                try:
                    result = check_and_update_domain(config, domain_cfg)

                    # 如果地址未变化且之前已记录，减少日志噪音
                    if result["action"] == "skip" and last_ip_map.get(domain_id) == result["new_ip"]:
                        # 仅更新检查时间，不写日志
                        upsert_domain_status(
                            domain_id=result["domain_id"],
                            record_name=result["record_name"],
                            current_ip=result["new_ip"],
                            status="ok",
                            is_update=False,
                        )
                    else:
                        # 记录日志
                        add_log(
                            domain_id=result["domain_id"],
                            record_name=result["record_name"],
                            action=result["action"],
                            old_ip=result["old_ip"],
                            new_ip=result["new_ip"],
                            message=result["message"],
                        )
                        # 更新状态
                        upsert_domain_status(
                            domain_id=result["domain_id"],
                            record_name=result["record_name"],
                            current_ip=result["new_ip"],
                            status="ok" if result["action"] in ("create", "update", "skip") else "error",
                            is_update=(result["action"] in ("create", "update")),
                        )

                    if result["new_ip"]:
                        last_ip_map[domain_id] = result["new_ip"]

                except Exception as e:
                    log(f"[ERROR] 域名 {domain_cfg.get('record_name', '?')} 处理异常: {e}")
                    add_log(
                        domain_id=domain_id,
                        record_name=domain_cfg.get("record_name", ""),
                        action="error",
                        message=str(e),
                    )
                    upsert_domain_status(
                        domain_id=domain_id,
                        record_name=domain_cfg.get("record_name", ""),
                        status="error",
                    )

            # 使用全局检查间隔
            check_interval = daemon_cfg.get("check_interval", 300)
            log(f"[INFO] 等待 {check_interval} 秒后进行下一轮检查...")
            time.sleep(check_interval)

        except Exception as e:
            log(f"[ERROR] 主循环异常: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
