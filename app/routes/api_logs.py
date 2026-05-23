"""操作日志 REST API"""

from fastapi import APIRouter, Request, Query
from app.models import get_logs, get_today_update_count, get_all_domain_status
from app.auth import require_auth

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs")
async def list_logs(
    request: Request,
    domain_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """查询操作日志（分页）"""
    require_auth(request, request.app.state.config)
    return get_logs(domain_id=domain_id, limit=limit, offset=offset)


@router.get("/status")
async def get_status(request: Request):
    """获取守护进程运行状态概览"""
    require_auth(request, request.app.state.config)
    config = request.app.state.config
    domains = config.get("domains", [])
    status_list = get_all_domain_status()
    status_map = {s["domain_id"]: s for s in status_list}

    online_count = sum(
        1 for s in status_list if s.get("status") == "ok"
    )
    error_count = sum(
        1 for s in status_list if s.get("status") == "error"
    )

    return {
        "total_domains": len(domains),
        "enabled_domains": sum(1 for d in domains if d.get("enabled", True)),
        "online_count": online_count,
        "error_count": error_count,
        "today_updates": get_today_update_count(),
        "check_interval": config.get("daemon", {}).get("check_interval", 300),
    }
