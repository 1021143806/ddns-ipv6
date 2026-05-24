"""DDNS IPv6 核心逻辑模块

提供纯函数：获取 IPv6、调用 dnshe API、CRUD DNS 记录。
从原 ddns.py 提取，供守护进程和 WebUI 共用。
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

# Python 3.11+ 使用 tomllib，低版本使用 tomli
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        print("[ERROR] 需要 Python 3.11+ 或安装 tomli 包", file=sys.stderr)
        sys.exit(1)

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_DIR, "config", "env.toml")


def load_config() -> dict:
    """加载配置文件"""
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_PATH}")
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def _escape_toml_string(s: str) -> str:
    """转义 TOML 字符串中的特殊字符"""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def save_config(config: dict) -> None:
    """保存配置到文件（手动序列化 TOML，避免依赖 tomli_w）"""
    lines = []
    lines.append("# DDNS IPv6 配置文件\n")

    # [web]
    web = config.get("web", {})
    lines.append("\n[web]")
    lines.append(f'host = "{_escape_toml_string(web.get("host", "0.0.0.0"))}"')
    lines.append(f"port = {web.get('port', 5080)}")
    lines.append(f'username = "{_escape_toml_string(web.get("username", "admin"))}"')
    lines.append(f'password = "{_escape_toml_string(web.get("password", "admin123"))}"')
    lines.append(f'secret_key = "{_escape_toml_string(web.get("secret_key", ""))}"')

    # [api]
    api = config.get("api", {})
    lines.append("\n[api]")
    lines.append(f'base_url = "{_escape_toml_string(api.get("base_url", ""))}"')
    lines.append(f'api_key = "{_escape_toml_string(api.get("api_key", ""))}"')
    lines.append(f'api_secret = "{_escape_toml_string(api.get("api_secret", ""))}"')

    # [daemon]
    daemon = config.get("daemon", {})
    lines.append("\n[daemon]")
    lines.append(f"check_interval = {daemon.get('check_interval', 300)}")

    # [network]
    network = config.get("network", {})
    lines.append("\n[network]")
    lines.append(f'interface = "{_escape_toml_string(network.get("interface", ""))}"')

    # [[domains]]
    for domain in config.get("domains", []):
        lines.append("\n[[domains]]")
        lines.append(f'id = "{_escape_toml_string(domain.get("id", ""))}"')
        lines.append(f"subdomain_id = {domain.get('subdomain_id', 0)}")
        lines.append(f'record_name = "{_escape_toml_string(domain.get("record_name", ""))}"')
        lines.append(f'record_type = "{_escape_toml_string(domain.get("record_type", "AAAA"))}"')
        lines.append(f"ttl = {domain.get('ttl', 600)}")
        lines.append(f"enabled = {str(domain.get('enabled', True)).lower()}")
        if "check_interval" in domain:
            lines.append(f"check_interval = {domain['check_interval']}")

    lines.append("")  # 末尾空行
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def log(msg: str) -> str:
    """生成带时间戳的日志字符串，同时返回"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line, flush=True)
    return line


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
            if "scope global dynamic" in line and "mngtmpaddr" not in line:
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
    """调用 dnshe API（含速率限制保护）

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
    from app.models import record_api_call

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
            result = json.loads(resp.read().decode("utf-8"))
            record_api_call(endpoint, action, success=True)
            return result
    except urllib.error.HTTPError as e:
        log(f"[ERROR] API HTTP 错误 {e.code}: {e.reason}")
        record_api_call(endpoint, action, success=False)
        return None
    except urllib.error.URLError as e:
        log(f"[ERROR] API 连接错误: {e.reason}")
        record_api_call(endpoint, action, success=False)
        return None
    except json.JSONDecodeError as e:
        log(f"[ERROR] API 响应 JSON 解析失败: {e}")
        record_api_call(endpoint, action, success=False)
        return None
    except Exception as e:
        log(f"[ERROR] API 请求异常: {e}")
        record_api_call(endpoint, action, success=False)
        return None


def get_record_name(domain_cfg: dict) -> str:
    """从完整域名中提取子域名前缀

    dnshe API 的 name 参数只需要子域名前缀（如 ipv6），
    不需要完整域名（如 ipv6.ptrel.cc.cd）。
    """
    record_name = domain_cfg["record_name"]
    return record_name.split(".")[0]


def get_full_record_name(domain_cfg: dict) -> str:
    """获取完整域名（用于 dnshe API 的 name 参数）

    dnshe API 的 create/update 接口，name 参数传完整域名更稳定，
    避免 dnshe 自动拼接时出现重复域名（如 maiapi.ptrel.cc.cd.ptrel.cc.cd）。
    """
    return domain_cfg["record_name"]


def get_current_record(config: dict, domain_cfg: dict) -> dict | None:
    """查询当前 AAAA 记录

    Args:
        config: 完整配置
        domain_cfg: 单域名配置字典

    Returns:
        记录字典（含 id, content 等），不存在返回 None
    """
    subdomain_id = domain_cfg["subdomain_id"]
    record_name = get_record_name(domain_cfg)
    record_type = domain_cfg.get("record_type", "AAAA")

    resp = api_request(
        config,
        endpoint="dns_records",
        action="list",
        extra_params={"subdomain_id": subdomain_id},
    )

    if resp is None:
        return None

    records = resp.get("records", resp.get("data", resp)) if isinstance(resp, dict) else resp
    if not isinstance(records, list):
        log(f"[WARN] API 返回格式异常: {resp}")
        return None

    for record in records:
        rec_name = record.get("name", "")
        full_name = domain_cfg["record_name"]
        # 匹配：完整域名优先，其次子域名前缀，最后兼容重复拼接的脏数据
        if rec_name == full_name and record.get("type") == record_type:
            log(f"[INFO] 找到现有记录: id={record.get('id')}, name={rec_name}, content={record.get('content')}")
            return record

    # 第二遍：匹配子域名前缀或重复拼接的脏数据（兜底）
    for record in records:
        rec_name = record.get("name", "")
        full_name = domain_cfg["record_name"]
        if (rec_name == record_name or rec_name == f"{full_name}.{full_name.split('.', 1)[1]}") and record.get("type") == record_type:
            log(f"[INFO] 找到现有记录: id={record.get('id')}, name={rec_name}, content={record.get('content')}")
            return record

    log(f"[INFO] 未找到 {record_type} 记录: {record_name}")
    return None


def create_record(config: dict, domain_cfg: dict, ipv6: str) -> dict | None:
    """创建 AAAA 记录

    Returns:
        API 响应字典，失败返回 None
    """
    body = {
        "subdomain_id": domain_cfg["subdomain_id"],
        "type": domain_cfg.get("record_type", "AAAA"),
        "name": get_record_name(domain_cfg),
        "content": ipv6,
        "ttl": domain_cfg.get("ttl", 600),
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
        return None

    log(f"[INFO] 创建 AAAA 记录成功: {ipv6} (id={resp.get('id')})")
    return resp


def update_record(config: dict, domain_cfg: dict, record_id: int, ipv6: str) -> bool:
    """更新 AAAA 记录"""
    body = {
        "id": record_id,
        "type": domain_cfg.get("record_type", "AAAA"),
        "name": get_record_name(domain_cfg),
        "content": ipv6,
        "ttl": domain_cfg.get("ttl", 600),
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


def delete_dns_record(config: dict, record_id: str) -> bool:
    """删除 DNS 记录

    Args:
        config: 完整配置
        record_id: 记录 ID（优先用 dnshe 的数字 id，其次用 record_id 字符串）

    Returns:
        成功返回 True，失败返回 False
    """
    # 先尝试用数字 id 删除（dnshe API 推荐方式）
    if record_id.isdigit():
        body = {"id": int(record_id)}
        resp = api_request(
            config,
            endpoint="dns_records",
            action="delete",
            method="POST",
            body=body,
        )
        if resp is not None:
            log(f"[INFO] 删除 DNS 记录成功: id={record_id}")
            return True

    # 如果数字 id 方式失败，尝试用 record_id 字符串
    body = {"record_id": record_id}
    resp = api_request(
        config,
        endpoint="dns_records",
        action="delete",
        method="POST",
        body=body,
    )
    if resp is not None:
        log(f"[INFO] 删除 DNS 记录成功: {record_id}")
        return True

    log(f"[ERROR] 删除 DNS 记录失败: {record_id}")
    return False


def update_dns_record(config: dict, record_id: str, record_type: str, name: str, content: str, ttl: int = 600) -> bool:
    """更新 DNS 记录（先尝试直接更新，失败则先删后建）

    Args:
        config: 完整配置
        record_id: 记录 ID（优先用 dnshe 的数字 id，其次用 record_id 字符串）
        record_type: 记录类型 (A, AAAA, TXT...)
        name: 记录名称（子域名前缀）
        content: 记录值
        ttl: TTL

    Returns:
        成功返回 True，失败返回 False
    """
    # 优先用数字 id（dnshe API 推荐方式）
    if record_id.isdigit():
        body = {
            "id": int(record_id),
            "type": record_type,
            "name": name,
            "content": content,
            "ttl": ttl,
        }
        resp = api_request(
            config,
            endpoint="dns_records",
            action="update",
            method="POST",
            body=body,
        )
        if resp is not None:
            log(f"[INFO] 更新 DNS 记录成功: id={record_id}, {name} → {content}")
            return True

    # 非数字 id（如 pdns_xxx），尝试从 dnshe 查询对应的数字 id
    subdomain_id = None
    domains = config.get("domains", [])
    for d in domains:
        subdomain_id = d.get("subdomain_id")
        if subdomain_id:
            break

    if not subdomain_id:
        log("[ERROR] 无法获取 subdomain_id")
        return False

    log(f"[INFO] record_id 不是数字，尝试查询数字 id: {record_id}")
    try:
        records = list_all_dns_records(config, subdomain_id)
        if records:
            for r in records:
                if r.get("record_id") == record_id:
                    num_id = r.get("id")
                    if num_id:
                        log(f"[INFO] 找到数字 id: {num_id} → 用于更新")
                        body = {
                            "id": int(num_id),
                            "type": record_type,
                            "name": name,
                            "content": content,
                            "ttl": ttl,
                        }
                        resp = api_request(
                            config,
                            endpoint="dns_records",
                            action="update",
                            method="POST",
                            body=body,
                        )
                        if resp is not None:
                            log(f"[INFO] 更新 DNS 记录成功: id={num_id}, {name} → {content}")
                            return True
                        log(f"[WARN] 用数字 id {num_id} 更新失败，尝试先删后建")
                        # 删除旧记录
                        delete_dns_record(config, record_id=str(num_id))
                        break
    except Exception as e:
        log(f"[WARN] 查询数字 id 异常: {e}")

    # 直接创建新记录（先删后建）
    log(f"[INFO] 直接创建新记录（先删后建）: {name} → {content}")
    body = {
        "subdomain_id": subdomain_id,
        "type": record_type,
        "name": name,
        "content": content,
        "ttl": ttl,
    }
    resp = api_request(
        config,
        endpoint="dns_records",
        action="create",
        method="POST",
        body=body,
    )
    if resp is not None:
        log(f"[INFO] 先删后建成功: {name} → {content} (id={resp.get('id')})")
        return True

    log(f"[ERROR] 更新 DNS 记录失败: id={record_id}")
    return False


def list_all_dns_records(config: dict, subdomain_id: int) -> list[dict] | None:
    """获取指定子域名的所有 DNS 记录

    Args:
        config: 完整配置
        subdomain_id: 子域名 ID

    Returns:
        DNS 记录列表，失败返回 None
    """
    resp = api_request(
        config,
        endpoint="dns_records",
        action="list",
        extra_params={"subdomain_id": subdomain_id},
    )

    if resp is None:
        return None

    records = resp.get("records", resp.get("data", resp)) if isinstance(resp, dict) else resp
    if not isinstance(records, list):
        log(f"[WARN] API 返回格式异常: {resp}")
        return None

    return records


def register_subdomain(config: dict, subdomain: str, rootdomain: str) -> dict | None:
    """通过 dnshe API 注册子域名

    Args:
        config: 完整配置
        subdomain: 子域名前缀（如 ddns）
        rootdomain: 根域名（如 ptrel.cc.cd）

    Returns:
        API 响应字典（含 subdomain_id），失败返回 None
    """
    body = {
        "subdomain": subdomain,
        "rootdomain": rootdomain,
    }

    resp = api_request(
        config,
        endpoint="subdomains",
        action="register",
        method="POST",
        body=body,
    )

    if resp is None:
        log(f"[ERROR] 注册子域名失败: {subdomain}.{rootdomain}")
        return None

    log(f"[INFO] 注册子域名成功: {subdomain}.{rootdomain} (id={resp.get('id')})")
    return resp


def check_and_update_domain(config: dict, domain_cfg: dict) -> dict:
    """对单个域名执行完整的检测+更新流程

    Args:
        config: 完整配置
        domain_cfg: 单域名配置

    Returns:
        {
            "domain_id": str,
            "record_name": str,
            "action": "create"|"update"|"skip"|"error",
            "old_ip": str|None,
            "new_ip": str|None,
            "message": str,
        }
    """
    domain_id = domain_cfg.get("id", domain_cfg["record_name"])
    record_name = domain_cfg["record_name"]

    # 1. 获取本机 IPv6
    interface = config.get("network", {}).get("interface", "")
    ipv6 = get_ipv6_address(interface)
    if ipv6 is None:
        return {
            "domain_id": domain_id,
            "record_name": record_name,
            "action": "error",
            "old_ip": None,
            "new_ip": None,
            "message": "无法获取本机 IPv6 地址",
        }

    # 2. 查询当前记录
    record = get_current_record(config, domain_cfg)

    # 3. 创建或更新
    if record is None:
        resp = create_record(config, domain_cfg, ipv6)
        if resp is None:
            return {
                "domain_id": domain_id,
                "record_name": record_name,
                "action": "error",
                "old_ip": None,
                "new_ip": ipv6,
                "message": "创建 AAAA 记录失败",
            }
        return {
            "domain_id": domain_id,
            "record_name": record_name,
            "action": "create",
            "old_ip": None,
            "new_ip": ipv6,
            "message": f"创建成功: {ipv6}",
        }
    else:
        current_content = record.get("content", "")
        if current_content == ipv6:
            return {
                "domain_id": domain_id,
                "record_name": record_name,
                "action": "skip",
                "old_ip": current_content,
                "new_ip": ipv6,
                "message": "地址未变化，跳过更新",
            }
        record_id = record.get("id")
        if record_id is None:
            return {
                "domain_id": domain_id,
                "record_name": record_name,
                "action": "error",
                "old_ip": current_content,
                "new_ip": ipv6,
                "message": "记录 ID 缺失，无法更新",
            }
        success = update_record(config, domain_cfg, record_id, ipv6)
        if not success:
            return {
                "domain_id": domain_id,
                "record_name": record_name,
                "action": "error",
                "old_ip": current_content,
                "new_ip": ipv6,
                "message": "更新 AAAA 记录失败",
            }
        return {
            "domain_id": domain_id,
            "record_name": record_name,
            "action": "update",
            "old_ip": current_content,
            "new_ip": ipv6,
            "message": f"更新成功: {current_content} → {ipv6}",
        }
