"""SQLite 数据层：操作日志 + 域名状态快照"""

import os
import sqlite3
import threading
from datetime import datetime

# 数据库文件路径
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_DIR, "data", "ddns.db")

# 线程局部存储：每个线程复用同一个连接
_local = threading.local()


def get_db() -> sqlite3.Connection:
    """获取当前线程的数据库连接（复用），自动创建目录和表"""
    conn = getattr(_local, "conn", None)
    if conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _init_tables(conn)
        _local.conn = conn
    return conn


def _init_tables(conn: sqlite3.Connection) -> None:
    """初始化数据库表"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ddns_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain_id TEXT NOT NULL,
            record_name TEXT NOT NULL,
            action TEXT NOT NULL,
            old_ip TEXT,
            new_ip TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS domain_status (
            domain_id TEXT PRIMARY KEY,
            record_name TEXT NOT NULL,
            current_ip TEXT,
            last_check_at TIMESTAMP,
            last_update_at TIMESTAMP,
            status TEXT DEFAULT 'unknown'
        )
    """)
    conn.commit()


# ============================================================
# 日志操作
# ============================================================

def add_log(
    domain_id: str,
    record_name: str,
    action: str,
    old_ip: str | None = None,
    new_ip: str | None = None,
    message: str = "",
) -> int:
    """添加操作日志，返回日志 ID"""
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute(
        "INSERT INTO ddns_logs (domain_id, record_name, action, old_ip, new_ip, message, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (domain_id, record_name, action, old_ip, new_ip, message, now),
    )
    conn.commit()
    return cursor.lastrowid


def get_logs(
    domain_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """查询操作日志（分页）"""
    conn = get_db()
    if domain_id:
        rows = conn.execute(
            "SELECT * FROM ddns_logs WHERE domain_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (domain_id, limit, offset),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM ddns_logs WHERE domain_id = ?", (domain_id,)
        ).fetchone()[0]
    else:
        rows = conn.execute(
            "SELECT * FROM ddns_logs ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM ddns_logs").fetchone()[0]
    return {
        "logs": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_avg_update_interval() -> dict:
    """计算 IP 地址变更的平均间隔时间（按 new_ip 去重，只统计真正的 IP 变化）

    Returns:
        {"avg_seconds": 平均间隔秒数, "count": 变更次数, "first_time": 首次变更时间, "last_time": 末次变更时间}
        如果变更次数少于 2 次，返回 None
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT new_ip, created_at FROM ddns_logs WHERE action IN ('create', 'update') AND new_ip IS NOT NULL ORDER BY id ASC"
    ).fetchall()

    # 按 new_ip 去重，只保留第一次出现的时间（真正的 IP 变更）
    seen_ips = set()
    ip_change_times = []
    for r in rows:
        ip = r["new_ip"]
        if ip not in seen_ips:
            seen_ips.add(ip)
            try:
                t = datetime.fromisoformat(r["created_at"])
                ip_change_times.append(t)
            except (ValueError, TypeError):
                continue

    if len(ip_change_times) < 2:
        return {"avg_seconds": None, "count": len(ip_change_times), "first_time": None, "last_time": None}

    intervals = []
    for i in range(1, len(ip_change_times)):
        diff = (ip_change_times[i] - ip_change_times[i-1]).total_seconds()
        intervals.append(diff)

    avg_seconds = sum(intervals) / len(intervals)
    return {
        "avg_seconds": round(avg_seconds, 1),
        "count": len(ip_change_times),
        "first_time": ip_change_times[0].isoformat(),
        "last_time": ip_change_times[-1].isoformat(),
    }


def get_today_update_count() -> int:
    """获取今日更新次数"""
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT COUNT(*) FROM ddns_logs WHERE action IN ('create', 'update') AND date(created_at) = ?",
        (today,),
    ).fetchone()
    return row[0] if row else 0


# ============================================================
# 域名状态操作
# ============================================================

def upsert_domain_status(
    domain_id: str,
    record_name: str,
    current_ip: str | None = None,
    status: str = "unknown",
    is_update: bool = False,
) -> None:
    """更新或插入域名状态"""
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = conn.execute(
        "SELECT domain_id FROM domain_status WHERE domain_id = ?", (domain_id,)
    ).fetchone()

    if existing:
        if is_update:
            conn.execute(
                "UPDATE domain_status SET current_ip=?, last_check_at=?, last_update_at=?, status=? "
                "WHERE domain_id=?",
                (current_ip, now, now, status, domain_id),
            )
        else:
            conn.execute(
                "UPDATE domain_status SET current_ip=?, last_check_at=?, status=? "
                "WHERE domain_id=?",
                (current_ip, now, status, domain_id),
            )
    else:
        conn.execute(
            "INSERT INTO domain_status (domain_id, record_name, current_ip, last_check_at, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (domain_id, record_name, current_ip, now, status),
        )
    conn.commit()


def get_all_domain_status() -> list[dict]:
    """获取所有域名状态"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM domain_status").fetchall()
    return [dict(r) for r in rows]


def get_domain_status(domain_id: str) -> dict | None:
    """获取单个域名状态"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM domain_status WHERE domain_id = ?", (domain_id,)
    ).fetchone()
    return dict(row) if row else None


def delete_domain_status(domain_id: str) -> None:
    """删除域名状态"""
    conn = get_db()
    conn.execute("DELETE FROM domain_status WHERE domain_id = ?", (domain_id,))
    conn.commit()


# ============================================================
# API 调用计数 + 速率限制
# ============================================================

API_HOURLY_LIMIT = 300  # dnshe API 限制 60次/分钟，设 300次/小时作为软件预警


def _init_api_call_table(conn: sqlite3.Connection) -> None:
    """初始化 API 调用日志表"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_call_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT NOT NULL,
            action TEXT NOT NULL,
            success INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_call_created
        ON api_call_log(created_at)
    """)
    conn.commit()


def record_api_call(endpoint: str, action: str, success: bool = True) -> None:
    """记录一次 API 调用"""
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO api_call_log (endpoint, action, success, created_at) VALUES (?, ?, ?, ?)",
        (endpoint, action, 1 if success else 0, now),
    )
    conn.commit()


def get_hourly_api_count() -> int:
    """获取当前小时内的 API 调用次数"""
    conn = get_db()
    now = datetime.now()
    hour_start = now.strftime("%Y-%m-%d %H:00:00")
    row = conn.execute(
        "SELECT COUNT(*) FROM api_call_log WHERE created_at >= ?",
        (hour_start,),
    ).fetchone()
    return row[0] if row else 0


def get_hourly_api_stats(hours: int = 24) -> list[dict]:
    """获取最近 N 小时的 API 调用统计（按半小时聚合，区分操作类型）

    Returns:
        [{"hour": "...", "count": 5, "list": 3, "create": 1, "update": 1, "delete": 0, "limit": 300}, ...]
    """
    conn = get_db()
    from datetime import timedelta
    start = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:00:00")
    rows = conn.execute(
        """SELECT strftime('%Y-%m-%d %H:', created_at) ||
                  CASE
                      WHEN CAST(strftime('%M', created_at) AS INTEGER) < 30 THEN '00'
                      ELSE '30'
                  END as slot,
                  endpoint, action,
                  COUNT(*) as count
           FROM api_call_log
           WHERE created_at >= ?
           GROUP BY slot, endpoint, action
           ORDER BY slot ASC""",
        (start,),
    ).fetchall()

    # 按 slot 聚合
    slot_map: dict[str, dict] = {}
    for r in rows:
        slot = r["slot"] + ":00"
        if slot not in slot_map:
            slot_map[slot] = {"hour": slot, "count": 0, "list": 0, "create": 0, "update": 0, "delete": 0, "limit": API_HOURLY_LIMIT}
        entry = slot_map[slot]
        entry["count"] += r["count"]
        action_key = r["action"]
        if action_key in ("list", "create", "update", "delete"):
            entry[action_key] += r["count"]

    return list(slot_map.values())


def get_api_rate_status() -> dict:
    """获取当前 API 速率状态"""
    current = get_hourly_api_count()
    return {
        "current": current,
        "limit": API_HOURLY_LIMIT,
        "remaining": max(0, API_HOURLY_LIMIT - current),
        "blocked": current >= API_HOURLY_LIMIT,
    }


# ============================================================
# 全量检查时间记录
# ============================================================

def save_last_full_check_time(timestamp: float) -> None:
    """保存最近一次全量同步的时间戳"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daemon_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO daemon_state (key, value) VALUES (?, ?)",
        ("last_full_check_time", str(timestamp)),
    )
    conn.commit()


def get_last_full_check_time() -> float | None:
    """获取最近一次全量同步的时间戳"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT value FROM daemon_state WHERE key = ?",
            ("last_full_check_time",),
        ).fetchone()
        if row:
            return float(row["value"])
    except Exception:
        pass
    return None


# ============================================================
# DNS 记录缓存（本地 SQLite，减少 dnshe API 调用）
# ============================================================

def _init_dns_cache_table(conn: sqlite3.Connection) -> None:
    """初始化 DNS 记录缓存表"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dns_records_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL,
            dnshe_id INTEGER DEFAULT 0,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            ttl INTEGER DEFAULT 600,
            status TEXT DEFAULT 'active',
            subdomain_id INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_dns_cache_record_id
        ON dns_records_cache(record_id)
    """)
    # 兼容旧表：如果 dnshe_id 列不存在则添加
    try:
        conn.execute("ALTER TABLE dns_records_cache ADD COLUMN dnshe_id INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 列已存在
    conn.commit()


# 合并所有表初始化
_orig_init_final = _init_tables
def _init_tables(conn: sqlite3.Connection) -> None:
    _orig_init_final(conn)
    _init_api_call_table(conn)
    _init_dns_cache_table(conn)


def update_dns_records_cache(records: list[dict], subdomain_id: int = 0) -> None:
    """更新 DNS 记录缓存（先清空再写入，避免残留旧记录）"""
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 先清空该子域名的所有缓存
    conn.execute("DELETE FROM dns_records_cache WHERE subdomain_id = ?", (subdomain_id,))

    for r in records:
        record_id = r.get("record_id") or str(r.get("id", ""))
        if not record_id:
            continue
        # dnshe API 返回的模块内部数字 id（用于 delete/update）
        dnshe_id = r.get("id", 0)
        conn.execute("""
            INSERT INTO dns_records_cache
            (record_id, dnshe_id, name, type, content, ttl, status, subdomain_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record_id,
            dnshe_id,
            r.get("name", ""),
            r.get("type", ""),
            r.get("content", ""),
            r.get("ttl", 600),
            r.get("status", "active"),
            subdomain_id,
            now,
        ))
    conn.commit()


def get_cached_dns_records() -> list[dict]:
    """从本地缓存获取 DNS 记录"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM dns_records_cache ORDER BY name ASC"
    ).fetchall()
    return [dict(r) for r in rows]
