"""DDNS IPv6 WebUI — FastAPI 应用入口"""

import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core import load_config
from app.routes.pages import router as pages_router
from app.routes.api_domains import router as api_domains_router
from app.routes.api_logs import router as api_logs_router
import os

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="DDNS IPv6 WebUI", version="1.0.0")

# 加载初始配置（失败则退出，不允许无配置运行）
try:
    config = load_config()
except Exception as e:
    print(f"[FATAL] 配置加载失败: {e}，服务无法启动", file=sys.stderr)
    sys.exit(1)

# 启动时校验 secret_key
secret_key = config.get("web", {}).get("secret_key", "")
if not secret_key or secret_key == "change-me-to-a-random-string":
    print("[FATAL] 请在 config/env.toml 中设置有效的 web.secret_key（随机字符串），服务无法启动", file=sys.stderr)
    sys.exit(1)

app.state.config = config

# 注册路由
app.include_router(pages_router)
app.include_router(api_domains_router)
app.include_router(api_logs_router)


@app.on_event("startup")
async def startup():
    """启动时重新加载配置"""
    try:
        app.state.config = load_config()
        print(f"[INFO] WebUI 启动成功，配置已加载")
    except Exception as e:
        print(f"[WARN] 配置加载失败: {e}")
