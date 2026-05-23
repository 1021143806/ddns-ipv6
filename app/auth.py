"""用户认证模块：Session + Cookie 简单认证"""

from fastapi import Request, HTTPException, Response
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SESSION_COOKIE = "ddns_session"
MAX_AGE = 86400 * 7  # 7 天


def _get_serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt="ddns-session")


def create_session(response: Response, username: str, secret_key: str) -> None:
    """创建登录 Session Cookie"""
    serializer = _get_serializer(secret_key)
    token = serializer.dumps({"username": username})
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=MAX_AGE,
        httponly=True,
        samesite="lax",
    )


def clear_session(response: Response) -> None:
    """清除 Session Cookie"""
    response.delete_cookie(SESSION_COOKIE)


def get_current_user(request: Request, secret_key: str) -> str:
    """从 Cookie 中获取当前登录用户名，未登录抛出 401"""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")

    serializer = _get_serializer(secret_key)
    try:
        data = serializer.loads(token, max_age=MAX_AGE)
        return data["username"]
    except Exception:
        raise HTTPException(status_code=401, detail="Session 已过期，请重新登录")


def require_auth(request: Request, config: dict):
    """依赖注入：验证登录状态，返回 username"""
    secret_key = config.get("web", {}).get("secret_key", "")
    if not secret_key or secret_key == "change-me-to-a-random-string":
        raise HTTPException(status_code=500, detail="服务器未配置有效的 secret_key，请联系管理员检查 config/env.toml")
    return get_current_user(request, secret_key)
