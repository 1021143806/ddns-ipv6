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
    lines.append(f"https_port = {web.get('https_port', 443)}")
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

    优先选择 /128 固定后缀地址（noprefixroute），
    其次选择临时地址（temporary dynamic），
    最后选择 mngtmpaddr 地址。

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
        candidates = {"fixed": None, "temporary": None, "mngtmpaddr": None}
        for line in lines:
            line = line.strip()
            if "scope global" not in line:
                continue
            parts = line.split()
            addr_part = None
            for part in parts:
                if "/" in part and ":" in part:
                    addr_part = part.split("/")[0]
                    break
            if not addr_part:
                continue

            if "temporary" in line:
                if candidates["temporary"] is None:
                    candidates["temporary"] = addr_part
            elif "mngtmpaddr" in line:
                if candidates["mngtmpaddr"] is None:
                    candidates["mngtmpaddr"] = addr_part
            else:
                # noprefixroute 或其它，优先 /128 固定地址
                if candidates["fixed"] is None:
                    candidates["fixed"] = addr_part

        # 按优先级选择
        for key in ("fixed", "temporary", "mngtmpaddr"):
            if candidates[key]:
                log(f"[INFO] 检测到 IPv6 地址: {candidates[key]} (优先级: {key})")
                return candidates[key]

        log("[WARN] 未找到 global dynamic IPv6 地址")
        return None
    except Exception as e:
        log(f"[ERROR] 获取 IPv6 地址异常: {e}")
        return None


def get_ipv4_address() -> str | None:
    """通过外部 HTTP 服务获取本机公网 IPv4 地址

    依次尝试多个服务，提高成功率。每个服务超时 5 秒。

    Returns:
        IPv4 地址字符串，失败返回 None
    """
    services = [
        "https://checkip.amazonaws.com/",
        "https://ifconfig.me/ip",
        "https://icanhazip.com/",
    ]

    for service in services:
        try:
            req = urllib.request.Request(service)
            with urllib.request.urlopen(req, timeout=5) as resp:
                ip = resp.read().decode("utf-8").strip()
                if ip and ":" not in ip and "." in ip:
                    log(f"[INFO] 检测到 IPv4 地址: {ip} (来源: {service})")
                    return ip
        except Exception as e:
            log(f"[WARN] 从 {service} 获取 IPv4 失败: {e}")
            continue

    log("[WARN] 所有服务均无法获取公网 IPv4 地址")
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
        with urllib.request.urlopen(req, timeout=10) as resp:
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


def update_dns_record(config: dict, record_id: str, record_type: str, name: str, content: str, ttl: int = 600, line: str = "") -> bool:
    """更新 DNS 记录（先比较新旧值，相同则跳过；不同则先删后建）

    dnshe API 的 update 接口存在已知问题（即使返回 success 也可能把 name 改坏），
    因此需要修改时走"先删后建"路径。

    Args:
        config: 完整配置
        record_id: 记录 ID
        record_type: 记录类型
        name: 记录名称（子域名前缀）
        content: 记录值
        ttl: TTL
        line: 解析线路

    Returns:
        成功返回 True，失败返回 False
    """
    subdomain_id = None
    domains = config.get("domains", [])
    for d in domains:
        subdomain_id = d.get("subdomain_id")
        if subdomain_id:
            break

    if not subdomain_id:
        log("[ERROR] 无法获取 subdomain_id")
        return False

    # 从 dnshe 查询最新记录
    log(f"[INFO] 查询最新记录: record_id={record_id}")
    records = list_all_dns_records(config, subdomain_id)
    if not records:
        log("[ERROR] 查询记录失败")
        return False

    # 查找匹配的记录
    matched = None
    for r in records:
        if r.get("record_id") == record_id:
            matched = r
            break

    if matched is None:
        log(f"[WARN] 未找到匹配记录: record_id={record_id}")
        return False

    num_id = matched.get("id")
    cur_content = matched.get("content", "")
    cur_ttl = matched.get("ttl", 600)
    log(f"[INFO] 当前记录: id={num_id}, content={cur_content}, ttl={cur_ttl}")

    # 比较新旧值，相同则跳过
    if cur_content == content and int(cur_ttl) == ttl:
        log(f"[INFO] 记录未变化，跳过更新")
        return True

    # 不同则先删后建
    log(f"[INFO] 记录已变化，执行先删后建: {name} → {content} (ttl={ttl})")

    # 删除旧记录
    if num_id:
        delete_dns_record(config, record_id=str(num_id))

    # 创建新记录
    body = {
        "subdomain_id": subdomain_id,
        "type": record_type,
        "name": name,
        "content": content,
        "ttl": ttl,
    }
    if line:
        body["line"] = line
    resp = api_request(
        config,
        endpoint="dns_records",
        action="create",
        method="POST",
        body=body,
    )
    if resp is not None:
        log(f"[INFO] 创建新记录成功: {name} → {content} (id={resp.get('id')})")
        # 同步更新本地缓存
        try:
            from app.models import update_dns_records_cache
            fresh = list_all_dns_records(config, subdomain_id)
            if fresh:
                update_dns_records_cache(fresh, subdomain_id)
        except Exception:
            pass
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


def _refresh_dns_cache(config: dict, subdomain_id: int) -> None:
    """刷新本地 DNS 记录缓存"""
    try:
        from app.models import update_dns_records_cache
        fresh = list_all_dns_records(config, subdomain_id)
        if fresh:
            update_dns_records_cache(fresh, subdomain_id)
    except Exception:
        pass


def check_and_update_domain(config: dict, domain_cfg: dict) -> dict:
    """对单个域名执行完整的检测+更新流程（自动清理脏数据）"""
    domain_id = domain_cfg.get("id", domain_cfg["record_name"])
    record_name = domain_cfg["record_name"]
    full_name = domain_cfg["record_name"]
    subdomain_prefix = get_record_name(domain_cfg)
    record_type = domain_cfg.get("record_type", "AAAA")

    # 1. 根据记录类型获取本机 IP
    if record_type == "A":
        current_ip = get_ipv4_address()
        ip_type = "IPv4"
    else:
        interface = config.get("network", {}).get("interface", "")
        current_ip = get_ipv6_address(interface)
        ip_type = "IPv6"

    if current_ip is None:
        return {
            "domain_id": domain_id,
            "record_name": record_name,
            "action": "error",
            "old_ip": None,
            "new_ip": None,
            "message": f"无法获取本机 {ip_type} 地址",
        }

    # 2. 查询当前记录，同时检查脏数据
    subdomain_id = domain_cfg["subdomain_id"]
    resp = api_request(
        config,
        endpoint="dns_records",
        action="list",
        extra_params={"subdomain_id": subdomain_id},
    )
    if resp is None:
        return {
            "domain_id": domain_id,
            "record_name": record_name,
            "action": "error",
            "old_ip": None,
            "new_ip": current_ip,
            "message": "查询 DNS 记录失败",
        }
    records = resp.get("records", resp.get("data", resp)) if isinstance(resp, dict) else resp
    if not isinstance(records, list):
        return {
            "domain_id": domain_id,
            "record_name": record_name,
            "action": "error",
            "old_ip": None,
            "new_ip": current_ip,
            "message": "API 返回格式异常",
        }

    # 查找正确 name 的记录和脏数据
    good_record = None
    dirty_records = []
    for r in records:
        r_name = r.get("name", "")
        r_type = r.get("type", "")
        if r_type != record_type:
            continue
        if r_name == full_name:
            good_record = r
        elif r_name == subdomain_prefix or r_name == f"{full_name}.{full_name.split('.', 1)[1]}":
            dirty_records.append(r)

    # 3. 处理脏数据：先删除所有脏记录
    for dr in dirty_records:
        dr_id = dr.get("id")
        if dr_id:
            log(f"[INFO] 清理脏数据: id={dr_id}, name={dr.get('name')}")
            delete_dns_record(config, record_id=str(dr_id))

    # 4. 创建或更新
    if good_record is None:
        # 没有正确记录，创建新记录
        resp = create_record(config, domain_cfg, current_ip)
        if resp is None:
            return {
                "domain_id": domain_id,
                "record_name": record_name,
                "action": "error",
                "old_ip": None,
                "new_ip": current_ip,
                "message": f"创建 {record_type} 记录失败",
            }
        # 刷新本地 DNS 记录缓存
        _refresh_dns_cache(config, subdomain_id)
        return {
            "domain_id": domain_id,
            "record_name": record_name,
            "action": "create",
            "old_ip": None,
            "new_ip": current_ip,
            "message": f"创建成功: {current_ip}",
        }
    else:
        current_content = good_record.get("content", "")
        if current_content == current_ip:
            return {
                "domain_id": domain_id,
                "record_name": record_name,
                "action": "skip",
                "old_ip": current_content,
                "new_ip": current_ip,
                "message": "地址未变化，跳过更新",
            }
        record_id = good_record.get("id")
        if record_id is None:
            return {
                "domain_id": domain_id,
                "record_name": record_name,
                "action": "error",
                "old_ip": current_content,
                "new_ip": current_ip,
                "message": "记录 ID 缺失，无法更新",
            }
        success = update_record(config, domain_cfg, record_id, current_ip)
        if not success:
            return {
                "domain_id": domain_id,
                "record_name": record_name,
                "action": "error",
                "old_ip": current_content,
                "new_ip": current_ip,
                "message": f"更新 {record_type} 记录失败",
            }
        # 刷新本地 DNS 记录缓存
        _refresh_dns_cache(config, subdomain_id)
        return {
            "domain_id": domain_id,
            "record_name": record_name,
            "action": "update",
            "old_ip": current_content,
            "new_ip": current_ip,
            "message": f"更新成功: {current_content} → {current_ip}",
        }
