"""阿里云云解析 DNS Provider

通过阿里云 OpenAPI（RPC 风格，HMAC-SHA1 签名）管理域名解析记录。
作为 ddns-ipv6 的第二个 provider，与 dnshe provider 并存。

支持的 API：
- DescribeDomainRecords: 查询记录列表
- AddDomainRecord:      添加记录
- UpdateDomainRecord:   更新记录（本实现走"先删后建"，与 dnshe 逻辑对齐）
- DeleteDomainRecord:   删除记录

依赖：仅 Python 标准库（hashlib/hmac/base64/urllib）
"""

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

# 阿里云云解析 API 入口
ALIYUN_ENDPOINT = "https://alidns.aliyuncs.com/"
API_VERSION = "2015-01-09"


class AliyunDNSError(Exception):
    """阿里云 API 调用异常"""


def _sign(secret: str, string_to_sign: str) -> str:
    """HMAC-SHA1 签名，返回 base64 字符串"""
    digest = hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def api_request(access_key_id: str, access_key_secret: str,
                action: str, params: dict | None = None, method: str = "GET") -> dict:
    """调用阿里云 OpenAPI（RPC 风格）

    Args:
        access_key_id: AccessKey ID
        access_key_secret: AccessKey Secret
        action: API Action（如 DescribeDomainRecords）
        params: 业务参数
        method: HTTP 方法（阿里云 RPC 用 GET 即可）

    Returns:
        响应 JSON 字典；失败抛 AliyunDNSError
    """
    all_params = {
        "AccessKeyId": access_key_id,
        "Action": action,
        "Format": "JSON",
        "Version": API_VERSION,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureVersion": "1.0",
        "SignatureNonce": str(uuid.uuid4()),
        "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if params:
        all_params.update(params)

    # 1. 参数按字典序排序
    sorted_params = sorted(all_params.items())
    # 2. 构造规范化查询串（URL 编码，RFC3986）
    canonical = "&".join(
        f"{urllib.parse.quote(str(k), safe='')}={urllib.parse.quote(str(v), safe='')}"
        for k, v in sorted_params
    )
    # 3. 待签名字符串
    string_to_sign = (
        method + "&" + urllib.parse.quote("/", safe="") + "&" + urllib.parse.quote(canonical, safe="")
    )
    # 4. 签名（密钥 = Secret + "&"）
    signature = _sign(access_key_secret + "&", string_to_sign)
    all_params["Signature"] = signature

    url = f"{ALIYUN_ENDPOINT}?{urllib.parse.urlencode(all_params)}"
    req = urllib.request.Request(url, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = {"Message": e.reason}
        code = body.get("Code", f"HTTP_{e.code}")
        msg = body.get("Message", e.reason)
        raise AliyunDNSError(f"[{code}] {msg}") from e
    except urllib.error.URLError as e:
        raise AliyunDNSError(f"连接失败: {e.reason}") from e


# ==================== 域名解析工具函数 ====================

def split_domain(record_name: str) -> tuple[str, str]:
    """把完整记录名拆分为 (RR, 主域名)

    阿里云记录名如 ipv6.ptrel.asia → RR="ipv6", 主域="ptrel.asia"
    主域名记录如 ptrel.asia → RR="@"，主域="ptrel.asia"
    """
    parts = record_name.strip().rstrip(".").split(".")
    if len(parts) >= 3:
        return parts[0], ".".join(parts[1:])
    return "@", ".".join(parts)


def _record_key(rr: str, record_type: str) -> str:
    """记录唯一键（RR 转小写 + 类型，用于匹配）"""
    return f"{rr.lower()}|{record_type.upper()}"


def list_records(access_key_id: str, access_key_secret: str, domain_name: str) -> list[dict]:
    """查询某域名下全部解析记录

    Returns:
        记录列表，每条含 RecordId/RR/Type/Value/TTL/Line
    """
    params = {"DomainName": domain_name}
    result = api_request(access_key_id, access_key_secret, "DescribeDomainRecords", params)

    records = result.get("DomainRecords", {}).get("Record", [])
    # 统一字段命名，与 dnshe provider 的 list 返回对齐
    normalized = []
    for r in records:
        normalized.append({
            "id": str(r.get("RecordId", "")),
            "name": f"{r.get('RR', '@')}.{domain_name}".lstrip("@.") or domain_name,
            "rr": r.get("RR", "@"),
            "type": r.get("Type", ""),
            "content": r.get("Value", ""),
            "ttl": r.get("TTL", 600),
            "line": r.get("Line", "default"),
        })
    return normalized


def get_record(access_key_id: str, access_key_secret: str, domain_name: str,
               record_name: str, record_type: str | None = "AAAA") -> dict | None:
    """按完整记录名 + 类型查找记录

    record_type 传 None 时匹配任意类型的第一条记录
    """
    rr, _ = split_domain(record_name)
    for rec in list_records(access_key_id, access_key_secret, domain_name):
        if record_type is None or _record_key(rec["rr"], rec["type"]) == _record_key(rr, record_type):
            return rec
    return None


def create_record(access_key_id: str, access_key_secret: str, domain_name: str,
                  record_name: str, record_type: str, content: str, ttl: int = 600,
                  line: str = "default") -> dict:
    """添加解析记录"""
    rr, _ = split_domain(record_name)
    params = {
        "DomainName": domain_name,
        "RR": rr,
        "Type": record_type.upper(),
        "Value": content,
        "TTL": ttl,
        "Line": line,
    }
    return api_request(access_key_id, access_key_secret, "AddDomainRecord", params)


def update_record(access_key_id: str, access_key_secret: str, record_id: str,
                  domain_name: str, rr: str, record_type: str, content: str,
                  ttl: int = 600, line: str = "default") -> dict:
    """更新解析记录（阿里云 UpdateDomainRecord 可用，直接更新）"""
    params = {
        "RecordId": record_id,
        "RR": rr,
        "Type": record_type.upper(),
        "Value": content,
        "TTL": ttl,
        "Line": line,
    }
    return api_request(access_key_id, access_key_secret, "UpdateDomainRecord", params)


def delete_record(access_key_id: str, access_key_secret: str, record_id: str) -> dict:
    """删除解析记录"""
    params = {"RecordId": record_id}
    return api_request(access_key_id, access_key_secret, "DeleteDomainRecord", params)
