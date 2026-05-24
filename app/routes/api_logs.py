"""操作日志 REST API"""

import os
from fastapi import APIRouter, Request, Query, HTTPException
from app.models import (
    get_logs, get_today_update_count, get_all_domain_status,
    get_hourly_api_stats, get_api_rate_status,
)
from app.auth import require_auth

router = APIRouter(prefix="/api", tags=["logs"])

# 守护进程日志文件路径
DAEMON_LOG_PATH = "/main/log/app/ddns-ipv6.log"


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


@router.get("/logs/daemon")
async def get_daemon_logs(
    request: Request,
    lines: int = Query(100, ge=1, le=5000, description="返回行数"),
    keyword: str | None = Query(None, description="关键词筛选"),
    tail: bool = Query(False, description="是否只返回末尾行（最新日志）"),
):
    """读取守护进程日志文件（/main/log/app/ddns-ipv6.log）"""
    require_auth(request, request.app.state.config)

    if not os.path.exists(DAEMON_LOG_PATH):
        raise HTTPException(status_code=404, detail="守护进程日志文件不存在")

    try:
        with open(DAEMON_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志文件失败: {e}")

    total = len(all_lines)

    if tail:
        # 取末尾 N 行
        selected = all_lines[-lines:]
    else:
        # 取开头 N 行
        selected = all_lines[:lines]

    # 关键词筛选
    if keyword:
        selected = [l for l in selected if keyword in l]

    return {
        "lines": selected,
        "total": total,
        "returned": len(selected),
        "lines_requested": lines,
        "file": DAEMON_LOG_PATH,
        "tail": tail,
        "keyword": keyword,
    }


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
        "api_rate": get_api_rate_status(),
    }


@router.get("/stats/hourly")
async def get_hourly_stats(request: Request, hours: int = Query(24, ge=1, le=72)):
    """获取 API 调用按小时统计（用于折线图）"""
    require_auth(request, request.app.state.config)
    return {
        "stats": get_hourly_api_stats(hours=hours),
        "current": get_api_rate_status(),
    }


@router.post("/stats/seed")
async def seed_test_data(request: Request):
    """生成测试数据（仅开发用）"""
    require_auth(request, request.app.state.config)
    from app.models import get_db
    from datetime import datetime, timedelta, timezone
    import random

    conn = get_db()
    now = datetime.now(timezone.utc)
    random.seed(42)

    # 清空旧数据
    conn.execute("DELETE FROM api_call_log")

    for i in range(48):
        t = now - timedelta(hours=23) + timedelta(minutes=30 * i)
        count = random.randint(0, 8)
        for _ in range(count):
            ts = t + timedelta(seconds=random.randint(0, 1700))
            conn.execute(
                "INSERT INTO api_call_log (endpoint, action, success, created_at) VALUES (?, ?, ?, ?)",
                ('dns_records', 'list', 1, ts.strftime('%Y-%m-%d %H:%M:%S'))
            )

    conn.commit()
    return {"success": True, "message": "测试数据已生成"}
