#!/usr/bin/env python3
"""DDNS IPv6 动态域名解析脚本

定时检测本机 IPv6 地址变化，通过 dnshe.com API 自动更新 AAAA 记录。
仅使用 Python 标准库，无需额外依赖。
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

# Python 3.11+ 使用 tomllib，低版本使用 tomli（需安装）
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        print("[ERROR] 需要 Python 3.11+ 或安装 tomli 包", file=sys.stderr)
        sys.exit(1)

# 项目根目录（脚本所在目录）
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_DIR, "config", "env.toml")


def load_config() -> dict:
    """加载配置文件"""
    if not os.path.exists(CONFIG_PATH):
        log(f"[ERROR] 配置文件不存在: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def log(msg: str) -> None:
    """输出带时间戳的日志到 stdout"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def get_ipv6_address(interface: str = "") -> str | None:
    """获取本机 global dynamic IPv6 地址

    Args:
        interface: 网卡接口名，为空则自动检测

    Returns:
        IPv6 地址（不含前缀长度），失败返回 None
    """
    try:
        if interface:
            cmd = ["ip", "-6", "addr", "show", interface]
        else:
            cmd = ["ip", "-6", "addr", "show"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            log(f"[WARN] ip 命令执行失败: {result.stderr.strip()}")
            return None

        lines = result.stdout.split("\n")
        for line in lines:
            line = line.strip()
            # 匹配 global dynamic 且非 mngtmpaddr（临时地址）
            if "scope global dynamic" in line and "mngtmpaddr" not in line:
                # 格式: inet6 240e:390:364:1771::137/64 scope global dynamic ...
                parts = line.split()
                for part in parts:
                    if "/" in part and ":" in part:
                        addr = part.split("/")[0]
                        log(f"[INFO] 检测到 IPv6 地址: {addr}")
                        return addr

        log("[WARN] 未找到 global dynamic IPv6 地址")
        return None
    except Exception as e:
        log(f"[ERROR] 获取 IPv6 地址异常: {e}")
        return None


def api_request(
    config: dict,
    endpoint: str,
    action: str,
    extra_params: dict | None = None,
    method: str = "GET",
    body: dict | None = None,
) -> dict | None:
    """调用 dnshe API

    Args:
        config: 配置字典
        endpoint: API endpoint
        action: API action
        extra_params: 额外 URL 参数
        method: HTTP 方法
        body: POST 请求体

    Returns:
        API 响应 JSON，失败返回 None
    """
    api_cfg = config["api"]
    base_url = api_cfg["base_url"]
    api_key = api_cfg["api_key"]
    api_secret = api_cfg["api_secret"]

    params = f"m=domain_hub&endpoint={endpoint}&action={action}"
    if extra_params:
        for k, v in extra_params.items():
            params += f"&{k}={v}"

    url = f"{base_url}?{params}"

    headers = {
        "X-API-Key": api_key,
        "X-API-Secret": api_secret,
    }

    data = None
    if body:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        log(f"[ERROR] API HTTP 错误 {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        log(f"[ERROR] API 连接错误: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        log(f"[ERROR] API 响应 JSON 解析失败: {e}")
        return None
    except Exception as e:
        log(f"[ERROR] API 请求异常: {e}")
        return None


def get_record_name(config: dict) -> str:
    """从完整域名中提取子域名前缀

    dnshe API 的 name 参数只需要子域名前缀（如 ipv6），
    不需要完整域名（如 ipv6.ptrel.cc.cd）。
    """
    record_name = config["dns"]["record_name"]
    # 提取第一个点之前的部分作为子域名前缀
    return record_name.split(".")[0]


def get_current_record(config: dict) -> dict | None:
    """查询当前 AAAA 记录

    Returns:
        记录字典（含 id, content 等），不存在返回 None
    """
    dns_cfg = config["dns"]
    subdomain_id = dns_cfg["subdomain_id"]
    record_name = get_record_name(config)
    record_type = dns_cfg["record_type"]

    resp = api_request(
        config,
        endpoint="dns_records",
        action="list",
        extra_params={"subdomain_id": subdomain_id},
    )

    if resp is None:
        return None

    # API 响应格式: {"success": true, "records": [...], ...}
    records = resp.get("records", resp.get("data", resp)) if isinstance(resp, dict) else resp
    if not isinstance(records, list):
        log(f"[WARN] API 返回格式异常: {resp}")
        return None

    for record in records:
        rec_name = record.get("name", "")
        # 匹配：前缀相等 或 完整域名相等
        if (rec_name == record_name or rec_name == dns_cfg["record_name"]) and record.get("type") == record_type:
            log(f"[INFO] 找到现有记录: id={record.get('id')}, name={rec_name}, content={record.get('content')}")
            return record

    log(f"[INFO] 未找到 {record_type} 记录: {record_name}")
    return None


def create_record(config: dict, ipv6: str) -> bool:
    """创建 AAAA 记录"""
    dns_cfg = config["dns"]

    body = {
        "subdomain_id": dns_cfg["subdomain_id"],
        "type": dns_cfg["record_type"],
        "name": get_record_name(config),
        "content": ipv6,
        "ttl": dns_cfg["ttl"],
    }

    resp = api_request(
        config,
        endpoint="dns_records",
        action="create",
        method="POST",
        body=body,
    )

    if resp is None:
        log("[ERROR] 创建 AAAA 记录失败")
        return False

    log(f"[INFO] 创建 AAAA 记录成功: {ipv6} (id={resp.get('id')})")
    return True


def update_record(config: dict, record_id: int, ipv6: str) -> bool:
    """更新 AAAA 记录"""
    dns_cfg = config["dns"]

    body = {
        "id": record_id,
        "type": dns_cfg["record_type"],
        "name": get_record_name(config),
        "content": ipv6,
        "ttl": dns_cfg["ttl"],
    }

    resp = api_request(
        config,
        endpoint="dns_records",
        action="update",
        method="POST",
        body=body,
    )

    if resp is None:
        log("[ERROR] 更新 AAAA 记录失败")
        return False

    log(f"[INFO] 更新 AAAA 记录成功: {ipv6}")
    return True


def main() -> None:
    """主循环"""
    log("=" * 50)
    log("DDNS IPv6 服务启动")
    log(f"配置文件: {CONFIG_PATH}")

    config = load_config()
    dns_cfg = config["dns"]
    net_cfg = config["network"]
    daemon_cfg = config["daemon"]

    log(f"域名: {dns_cfg['record_name']}")
    log(f"检查间隔: {daemon_cfg['check_interval']} 秒")
    log("=" * 50)

    last_ipv6: str | None = None

    while True:
        try:
            # 重新加载配置（支持热更新）
            config = load_config()
            net_cfg = config["network"]
            daemon_cfg = config["daemon"]
            dns_cfg = config["dns"]

            # 1. 获取本机 IPv6
            interface = net_cfg.get("interface", "")
            ipv6 = get_ipv6_address(interface)
            if ipv6 is None:
                log("[WARN] 无法获取 IPv6 地址，等待下次检查")
                time.sleep(daemon_cfg["check_interval"])
                continue

            # 2. 如果地址未变化，跳过
            if ipv6 == last_ipv6:
                log(f"[INFO] IPv6 地址未变化: {ipv6}，跳过更新")
                time.sleep(daemon_cfg["check_interval"])
                continue

            # 3. 查询当前记录
            record = get_current_record(config)

            # 4. 创建或更新
            if record is None:
                success = create_record(config, ipv6)
            else:
                current_content = record.get("content", "")
                if current_content == ipv6:
                    log(f"[INFO] DNS 记录已是最新: {ipv6}，跳过更新")
                    last_ipv6 = ipv6
                    time.sleep(daemon_cfg["check_interval"])
                    continue
                record_id = record.get("id")
                if record_id is None:
                    log("[ERROR] 记录 ID 缺失，无法更新")
                    time.sleep(daemon_cfg["check_interval"])
                    continue
                success = update_record(config, record_id, ipv6)

            if success:
                last_ipv6 = ipv6

        except Exception as e:
            log(f"[ERROR] 主循环异常: {e}")

        time.sleep(daemon_cfg["check_interval"])


if __name__ == "__main__":
    main()
