"""域名管理 REST API"""

from fastapi import APIRouter, Request, HTTPException
from app.core import load_config, save_config, check_and_update_domain, register_subdomain
from app.models import (
    add_log,
    upsert_domain_status,
    get_all_domain_status,
    delete_domain_status,
)
from app.auth import require_auth

router = APIRouter(prefix="/api/domains", tags=["domains"])


def _get_config(request: Request) -> dict:
    """获取当前配置"""
    return request.app.state.config


def _reload_config(request: Request) -> dict:
    """重新加载配置并更新 app state"""
    config = load_config()
    request.app.state.config = config
    return config


@router.get("")
async def list_domains(request: Request):
    """获取所有域名列表及状态"""
    require_auth(request, _get_config(request))
    config = _reload_config(request)
    domains = config.get("domains", [])
    status_map = {s["domain_id"]: s for s in get_all_domain_status()}

    result = []
    for d in domains:
        domain_id = d.get("id", d["record_name"])
        status = status_map.get(domain_id, {})
        result.append({
            "id": domain_id,
            "record_name": d["record_name"],
            "record_type": d.get("record_type", "AAAA"),
            "subdomain_id": d.get("subdomain_id", 0),
            "ttl": d.get("ttl", 600),
            "enabled": d.get("enabled", True),
            "check_interval": d.get("check_interval"),
            "current_ip": status.get("current_ip"),
            "last_check_at": status.get("last_check_at"),
            "last_update_at": status.get("last_update_at"),
            "status": status.get("status", "unknown"),
        })
    return {"domains": result}


@router.post("/register-subdomain")
async def api_register_subdomain(request: Request):
    """通过 dnshe API 注册子域名"""
    require_auth(request, _get_config(request))
    body = await request.json()

    required = ["subdomain", "rootdomain"]
    for field in required:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"缺少必填字段: {field}")

    config = _reload_config(request)
    resp = register_subdomain(config, body["subdomain"], body["rootdomain"])

    if resp is None:
        raise HTTPException(status_code=500, detail="注册子域名失败，请检查 API 密钥和域名信息")

    return {"success": True, "result": resp}


@router.post("")
async def add_domain(request: Request):
    """添加新域名"""
    require_auth(request, _get_config(request))
    body = await request.json()

    # 验证必填字段
    required = ["record_name", "subdomain_id"]
    for field in required:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"缺少必填字段: {field}")

    config = _reload_config(request)
    domains = config.get("domains", [])

    # 生成 ID
    domain_id = body.get("id", body["record_name"].split(".")[0])
    # 检查重复
    for d in domains:
        if d.get("id") == domain_id:
            raise HTTPException(status_code=400, detail=f"域名 ID 已存在: {domain_id}")

    new_domain = {
        "id": domain_id,
        "subdomain_id": int(body["subdomain_id"]),
        "record_name": body["record_name"],
        "record_type": body.get("record_type", "AAAA"),
        "ttl": int(body.get("ttl", 600)),
        "enabled": body.get("enabled", True),
    }
    if "check_interval" in body:
        new_domain["check_interval"] = int(body["check_interval"])

    domains.append(new_domain)
    config["domains"] = domains
    save_config(config)
    request.app.state.config = config

    add_log(domain_id, body["record_name"], "config_add", message="添加域名配置")
    return {"success": True, "domain": new_domain}


@router.put("/{domain_id}")
async def update_domain(domain_id: str, request: Request):
    """更新域名配置"""
    require_auth(request, _get_config(request))
    body = await request.json()

    config = _reload_config(request)
    domains = config.get("domains", [])

    found = False
    for i, d in enumerate(domains):
        if d.get("id") == domain_id:
            if "record_name" in body:
                d["record_name"] = body["record_name"]
            if "subdomain_id" in body:
                d["subdomain_id"] = int(body["subdomain_id"])
            if "record_type" in body:
                d["record_type"] = body["record_type"]
            if "ttl" in body:
                d["ttl"] = int(body["ttl"])
            if "enabled" in body:
                d["enabled"] = body["enabled"]
            if "check_interval" in body:
                if body["check_interval"] is None:
                    d.pop("check_interval", None)
                else:
                    d["check_interval"] = int(body["check_interval"])
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail=f"域名不存在: {domain_id}")

    config["domains"] = domains
    save_config(config)
    request.app.state.config = config

    add_log(domain_id, d.get("record_name", ""), "config_update", message="更新域名配置")
    return {"success": True, "domain": d}


@router.delete("/{domain_id}")
async def delete_domain(domain_id: str, request: Request):
    """删除域名"""
    require_auth(request, _get_config(request))

    config = _reload_config(request)
    domains = config.get("domains", [])

    deleted = None
    new_domains = []
    for d in domains:
        if d.get("id") == domain_id:
            deleted = d
        else:
            new_domains.append(d)

    if deleted is None:
        raise HTTPException(status_code=404, detail=f"域名不存在: {domain_id}")

    config["domains"] = new_domains
    save_config(config)
    request.app.state.config = config

    delete_domain_status(domain_id)
    add_log(domain_id, deleted["record_name"], "config_delete", message="删除域名配置")
    return {"success": True}


@router.post("/{domain_id}/check")
async def check_domain(domain_id: str, request: Request):
    """手动触发单域名检测更新"""
    require_auth(request, _get_config(request))

    config = _reload_config(request)
    domains = config.get("domains", [])

    domain_cfg = None
    for d in domains:
        if d.get("id") == domain_id:
            domain_cfg = d
            break

    if domain_cfg is None:
        raise HTTPException(status_code=404, detail=f"域名不存在: {domain_id}")

    if not domain_cfg.get("enabled", True):
        raise HTTPException(status_code=400, detail="域名已禁用")

    result = check_and_update_domain(config, domain_cfg)

    # 记录日志和状态
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

    return {"success": True, "result": result}


@router.post("/check-all")
async def check_all_domains(request: Request):
    """手动触发全部域名检测"""
    require_auth(request, _get_config(request))

    config = _reload_config(request)
    domains = config.get("domains", [])

    results = []
    for d in domains:
        if not d.get("enabled", True):
            results.append({
                "domain_id": d.get("id"),
                "action": "skip",
                "message": "域名已禁用",
            })
            continue

        result = check_and_update_domain(config, d)
        results.append(result)

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

    return {"success": True, "results": results}
