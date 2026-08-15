"""API 帮助接口 — 供 AI / 外部调用方查询使用说明与接口文档

提供 GET /api/help 返回结构化的：
- 服务概览（双 provider 架构）
- 认证方式
- 全部接口清单（含参数说明与示例）
- AI 决策规则（如何区分 dnshe / 阿里云）
- 常见错误与处理
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["help"])


@router.get("/help")
async def api_help():
    """返回服务使用说明与接口文档（无需登录，供发现服务能力）"""
    return {
        "service": "DDNS IPv6 WebUI",
        "version": "2.2",
        "description": "多 provider 动态域名解析管理服务。定时检测本机 IP（IPv6/IPv4）变化，"
                       "通过 dnshe.com 或阿里云云解析 API 自动更新 DNS 记录。",
        "providers": [
            {
                "name": "dnshe",
                "domains": "*.ptrel.cc.cd 系列",
                "note": "需 subdomain_id；name 传子域名前缀；60次/分钟限流"
            },
            {
                "name": "aliyun",
                "domains": "*.ptrel.asia 系列",
                "note": "subdomain_id 填 0；name 传完整域名（自动拆分 RR+主域）；无需限流"
            }
        ],
        "authentication": {
            "method": "Session Cookie",
            "login": {
                "method": "POST",
                "path": "/login",
                "content_type": "application/x-www-form-urlencoded",
                "body": "username=admin&password=admin123",
                "example": "curl -c /tmp/cookies.txt -X POST http://localhost:5080/login -d 'username=admin&password=admin123'",
                "note": "登录后所有请求携带 Cookie：curl -b /tmp/cookies.txt"
            }
        },
        "base_url": "http://localhost:5080 或 https://ddns.ptrel.cc.cd",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/help",
                "desc": "本接口：返回使用说明与接口文档",
                "auth": False,
                "params": [],
                "example": "curl http://localhost:5080/api/help"
            },
            {
                "method": "GET",
                "path": "/api/status",
                "desc": "服务状态概览（域名数、在线数、今日更新、检查间隔）",
                "auth": True,
                "params": [],
                "example": "curl -b /tmp/cookies.txt http://localhost:5080/api/status"
            },
            {
                "method": "GET",
                "path": "/api/domains",
                "desc": "域名列表（含 provider/状态/IP/最近检查时间）",
                "auth": True,
                "params": [],
                "example": "curl -b /tmp/cookies.txt http://localhost:5080/api/domains"
            },
            {
                "method": "POST",
                "path": "/api/domains",
                "desc": "添加域名到 DDNS 监控（按 provider 区分参数）",
                "auth": True,
                "params": [
                    {"name": "record_name", "type": "string", "required": True, "desc": "完整域名，如 ddns.ptrel.cc.cd 或 ipv6.ptrel.asia"},
                    {"name": "provider", "type": "string", "required": False, "default": "dnshe", "desc": "dnshe 或 aliyun"},
                    {"name": "subdomain_id", "type": "int", "required": "dnshe必填", "desc": "dnshe 子域名 ID；阿里云填 0"},
                    {"name": "record_type", "type": "string", "required": False, "default": "AAAA", "desc": "AAAA / A / TXT"},
                    {"name": "ttl", "type": "int", "required": False, "default": 600},
                    {"name": "enabled", "type": "bool", "required": False, "default": True}
                ],
                "example": "curl -b /tmp/cookies.txt -X POST http://localhost:5080/api/domains -H 'Content-Type: application/json' -d '{\"id\":\"ddns\",\"record_name\":\"ddns.ptrel.cc.cd\",\"subdomain_id\":404037,\"record_type\":\"AAAA\",\"ttl\":600,\"enabled\":true}'"
            },
            {
                "method": "POST",
                "path": "/api/domains/register-subdomain",
                "desc": "创建子域名。dnshe=注册新子域名；aliyun=直接添加 AAAA 记录",
                "auth": True,
                "params": [
                    {"name": "provider", "type": "string", "required": False, "default": "dnshe", "desc": "dnshe 或 aliyun"},
                    {"name": "subdomain", "type": "string", "required": True, "desc": "子域名前缀"},
                    {"name": "rootdomain", "type": "string", "required": True, "desc": "根域名，如 ptrel.cc.cd / ptrel.asia"}
                ],
                "example": "curl -b /tmp/cookies.txt -X POST http://localhost:5080/api/domains/register-subdomain -H 'Content-Type: application/json' -d '{\"provider\":\"aliyun\",\"subdomain\":\"test\",\"rootdomain\":\"ptrel.asia\"}'"
            },
            {
                "method": "GET",
                "path": "/api/domains/dns-records",
                "desc": "全部 DNS 记录（dnshe + 阿里云合并，每条带 provider 标签）",
                "auth": True,
                "params": [],
                "example": "curl -b /tmp/cookies.txt http://localhost:5080/api/domains/dns-records"
            },
            {
                "method": "POST",
                "path": "/api/domains/dns-record/create",
                "desc": "创建 DNS 记录。dnshe name 传子域名前缀；aliyun name 传完整域名",
                "auth": True,
                "params": [
                    {"name": "provider", "type": "string", "required": False, "default": "dnshe", "desc": "dnshe 或 aliyun"},
                    {"name": "subdomain_id", "type": "int", "required": "dnshe必填", "desc": "dnshe 子域名 ID"},
                    {"name": "type", "type": "string", "required": True, "desc": "AAAA / A / TXT / CNAME"},
                    {"name": "name", "type": "string", "required": True, "desc": "dnshe=前缀；aliyun=完整域名"},
                    {"name": "content", "type": "string", "required": True, "desc": "记录值"},
                    {"name": "ttl", "type": "int", "required": False, "default": 600}
                ],
                "example": "curl -b /tmp/cookies.txt -X POST http://localhost:5080/api/domains/dns-record/create -H 'Content-Type: application/json' -d '{\"provider\":\"aliyun\",\"type\":\"AAAA\",\"name\":\"test.ptrel.asia\",\"content\":\"240e:390:3c7:ef00::8a8\",\"ttl\":600}'"
            },
            {
                "method": "PUT",
                "path": "/api/domains/dns-record/{record_id}",
                "desc": "更新 DNS 记录",
                "auth": True,
                "params": [
                    {"name": "record_id", "type": "path", "required": True, "desc": "记录 ID（dns-records 返回的 record_id/id）"},
                    {"name": "type", "type": "string", "required": True},
                    {"name": "name", "type": "string", "required": True},
                    {"name": "content", "type": "string", "required": True},
                    {"name": "ttl", "type": "int", "required": False, "default": 600}
                ]
            },
            {
                "method": "DELETE",
                "path": "/api/domains/dns-record/{record_id}",
                "desc": "删除 DNS 记录",
                "auth": True,
                "params": [{"name": "record_id", "type": "path", "required": True}]
            },
            {
                "method": "POST",
                "path": "/api/domains/{domain_id}/check",
                "desc": "手动触发单域名检测+更新",
                "auth": True,
                "params": [{"name": "domain_id", "type": "path", "required": True, "desc": "域名配置 id"}],
                "example": "curl -b /tmp/cookies.txt -X POST http://localhost:5080/api/domains/ipv6/check"
            },
            {
                "method": "POST",
                "path": "/api/domains/check-all",
                "desc": "手动触发全部域名检测",
                "auth": True,
                "params": []
            },
            {
                "method": "POST",
                "path": "/api/domains/dns-records/refresh",
                "desc": "刷新 dnshe 记录缓存",
                "auth": True,
                "params": []
            },
            {
                "method": "GET",
                "path": "/api/logs",
                "desc": "查询操作日志",
                "auth": True,
                "params": [
                    {"name": "domain_id", "type": "string", "required": False},
                    {"name": "limit", "type": "int", "required": False, "default": 50},
                    {"name": "offset", "type": "int", "required": False, "default": 0}
                ],
                "example": "curl -b /tmp/cookies.txt 'http://localhost:5080/api/logs?limit=20'"
            },
            {
                "method": "GET",
                "path": "/api/logs/daemon",
                "desc": "读取守护进程日志",
                "auth": True,
                "params": [
                    {"name": "lines", "type": "int", "required": False, "default": 100},
                    {"name": "keyword", "type": "string", "required": False},
                    {"name": "tail", "type": "bool", "required": False, "default": False}
                ],
                "example": "curl -b /tmp/cookies.txt 'http://localhost:5080/api/logs/daemon?lines=100&tail=true&keyword=error'"
            }
        ],
        "ai_decision_rules": {
            "which_provider": "record_name 以 .asia 或 .aliyuncs.com 结尾 → aliyun；否则 dnshe",
            "create_or_update": "dns-records 已有同名同类型 → 更新(用 record_id)；否则创建",
            "dnshe_create": {"name": "子域名前缀", "subdomain_id": "必填(如404037)"},
            "aliyun_create": {"name": "完整域名", "subdomain_id": 0},
            "ipv6_now": "240e:390:3c7:ef00::8a8（本机 IPv6，可调 /api/status 或日志确认）",
            "ipv4_now": "115.197.187.231（公网出口 IPv4）"
        },
        "errors": [
            {"code": 429, "desc": "dnshe 限流(60/min)，等 1 分钟重试"},
            {"code": 400, "desc": "参数错误：如阿里云漏 provider、记录名含下划线(禁 _ 用 -)"},
            {"code": 401, "desc": "未登录或 Cookie 过期"},
            {"code": "DomainRecordDuplicate", "desc": "阿里云记录已存在，改走更新接口"}
        ],
        "security": "阿里云 AccessKey 仅在服务器本地 config/env.toml，禁止写入任何文档/git 跟踪文件"
    }
