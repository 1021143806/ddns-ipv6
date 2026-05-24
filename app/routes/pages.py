"""页面路由：登录、仪表盘、域名管理、日志"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.auth import create_session, clear_session, require_auth
from app.models import get_logs, get_today_update_count, get_all_domain_status
import os
import time

router = APIRouter()

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 简易登录速率限制：记录最近失败尝试
_login_attempts: dict[str, list[float]] = {}
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW = 60  # 秒


def _get_config(request: Request) -> dict:
    return request.app.state.config


def _auth_context(request: Request) -> dict:
    """获取模板渲染的认证上下文（不传 config，避免 Jinja2 缓存 key 不可哈希）"""
    config = _get_config(request)
    try:
        username = require_auth(request, config)
        return {"user": username}
    except HTTPException as e:
        if e.status_code == 401:
            return {"user": None}
        raise


# ============================================================
# 登录相关
# ============================================================

@router.get("/login")
async def login_page(request: Request):
    """登录页面"""
    ctx = _auth_context(request)
    if ctx["user"]:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"request": request, **ctx})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """登录提交"""
    # 速率限制检查
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    attempts = _login_attempts.get(client_ip, [])
    # 清理过期记录
    attempts = [t for t in attempts if now - t < _LOGIN_WINDOW]
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "user": None,
             "error": f"登录尝试过于频繁，请 {_LOGIN_WINDOW} 秒后再试"},
        )

    config = _get_config(request)
    web_cfg = config.get("web", {})
    cfg_user = web_cfg.get("username", "admin")
    cfg_pass = web_cfg.get("password", "admin123")

    if username == cfg_user and password == cfg_pass:
        _login_attempts.pop(client_ip, None)  # 登录成功清除记录
        response = RedirectResponse("/dashboard", status_code=302)
        create_session(response, username, web_cfg.get("secret_key", "default"))
        return response

    # 登录失败记录
    attempts.append(now)
    _login_attempts[client_ip] = attempts

    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "user": None, "error": "用户名或密码错误"},
    )


@router.get("/logout")
async def logout():
    """登出"""
    response = RedirectResponse("/login", status_code=302)
    clear_session(response)
    return response


# ============================================================
# 页面路由
# ============================================================

@router.get("/")
async def root():
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/dashboard")
async def dashboard(request: Request):
    """仪表盘"""
    ctx = _auth_context(request)
    if not ctx["user"]:
        return RedirectResponse("/login", status_code=302)

    config = _get_config(request)
    domains = config.get("domains", [])
    status_list = get_all_domain_status()
    status_map = {s["domain_id"]: s for s in status_list}

    domain_statuses = []
    for d in domains:
        domain_id = d.get("id", d["record_name"])
        s = status_map.get(domain_id, {})
        domain_statuses.append({
            "id": domain_id,
            "record_name": d["record_name"],
            "enabled": d.get("enabled", True),
            "current_ip": s.get("current_ip", "-"),
            "last_check_at": s.get("last_check_at", "-"),
            "status": s.get("status", "unknown"),
        })

    online = sum(1 for ds in domain_statuses if ds["status"] == "ok")
    error = sum(1 for ds in domain_statuses if ds["status"] == "error")

    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "user": ctx["user"],
        "domain_statuses": domain_statuses,
        "total_domains": len(domains),
        "enabled_domains": sum(1 for d in domains if d.get("enabled", True)),
        "online_count": online,
        "error_count": error,
        "today_updates": get_today_update_count(),
    })


@router.get("/domains")
async def domains_page(request: Request):
    """域名管理页面"""
    ctx = _auth_context(request)
    if not ctx["user"]:
        return RedirectResponse("/login", status_code=302)

    config = _get_config(request)
    domains = config.get("domains", [])
    status_list = get_all_domain_status()
    status_map = {s["domain_id"]: s for s in status_list}

    domain_list = []
    for d in domains:
        domain_id = d.get("id", d["record_name"])
        s = status_map.get(domain_id, {})
        domain_list.append({
            "id": domain_id,
            "record_name": d["record_name"],
            "record_type": d.get("record_type", "AAAA"),
            "subdomain_id": d.get("subdomain_id", 0),
            "ttl": d.get("ttl", 600),
            "enabled": d.get("enabled", True),
            "check_interval": d.get("check_interval", ""),
            "current_ip": s.get("current_ip", "-"),
            "last_check_at": s.get("last_check_at", "-"),
            "status": s.get("status", "unknown"),
        })

    return templates.TemplateResponse(request, "domains.html", {
        "request": request,
        "user": ctx["user"],
        "domains": domain_list,
    })


@router.get("/logs")
async def logs_page(request: Request):
    """操作日志页面"""
    ctx = _auth_context(request)
    if not ctx["user"]:
        return RedirectResponse("/login", status_code=302)

    config = _get_config(request)
    domains = config.get("domains", [])
    log_data = get_logs(limit=100, offset=0)

    return templates.TemplateResponse(request, "logs.html", {
        "request": request,
        "user": ctx["user"],
        "logs": log_data["logs"],
        "total": log_data["total"],
        "domains": domains,
    })


@router.get("/dns-records")
async def dns_records_page(request: Request):
    """DNS 记录管理页面"""
    ctx = _auth_context(request)
    if not ctx["user"]:
        return RedirectResponse("/login", status_code=302)

    return templates.TemplateResponse(request, "dns_records.html", {
        "request": request,
        "user": ctx["user"],
    })
