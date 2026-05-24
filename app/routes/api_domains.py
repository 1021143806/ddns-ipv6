"""域名管理 REST API"""

from fastapi import APIRouter, Request, HTTPException
from app.core import load_config, save_config, check_and_update_domain, register_subdomain, list_all_dns_records, update_dns_record, delete_dns_record
from app.models import (
    add_log,
    upsert_domain_status,
    get_all_domain_status,
    delete_domain_status,
    update_dns_records_cache,
    get_cached_dns_records,
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


@router.get("/dns-records")
async def api_list_dns_records(request: Request):
    """获取 DNS 记录（优先从本地缓存读取）"""
    require_auth(request, _get_config(request))

    # 从本地缓存读取
    cached = get_cached_dns_records()
    if cached:
        return {"records": cached, "total": len(cached), "from_cache": True}

    # 缓存为空时尝试从 dnshe API 拉取
    config = _reload_config(request)
    domains = config.get("domains", [])
    all_records = []
    seen_ids = set()
    for d in domains:
        subdomain_id = d.get("subdomain_id")
        if subdomain_id and subdomain_id not in seen_ids:
            seen_ids.add(subdomain_id)
            records = list_all_dns_records(config, subdomain_id)
            if records:
                all_records.extend(records)
                update_dns_records_cache(records, subdomain_id)

    return {"records": all_records, "total": len(all_records), "from_cache": False}


@router.post("/dns-records/refresh")
async def api_refresh_dns_records(request: Request):
    """从 dnshe API 刷新 DNS 记录缓存"""
    require_auth(request, _get_config(request))
    config = _reload_config(request)
    domains = config.get("domains", [])

    all_records = []
    seen_ids = set()
    for d in domains:
        subdomain_id = d.get("subdomain_id")
        if subdomain_id and subdomain_id not in seen_ids:
            seen_ids.add(subdomain_id)
            records = list_all_dns_records(config, subdomain_id)
            if records:
                all_records.extend(records)
                update_dns_records_cache(records, subdomain_id)

    return {"records": all_records, "total": len(all_records), "message": "缓存已更新"}


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


@router.get("/nginx-configs")
async def list_nginx_configs(request: Request):
    """列出 /etc/nginx/conf.d/ 下已有的 Nginx 配置"""
    require_auth(request, _get_config(request))
    import os, glob

    configs = []
    conf_dir = "/etc/nginx/conf.d"
    if os.path.isdir(conf_dir):
        for f in sorted(glob.glob(os.path.join(conf_dir, "*.conf"))):
            try:
                with open(f) as fh:
                    content = fh.read()
                # 提取 server_name 和 proxy_pass
                server_names = []
                proxy_passes = []
                for line in content.split("\n"):
                    line_s = line.strip()
                    if line_s.startswith("server_name"):
                        server_names.append(line_s.split(";")[0].replace("server_name", "").strip())
                    if "proxy_pass" in line_s and "http" in line_s:
                        proxy_passes.append(line_s.split(";")[0].replace("proxy_pass", "").strip())

                configs.append({
                    "filename": os.path.basename(f),
                    "path": f,
                    "server_names": server_names,
                    "proxy_passes": proxy_passes,
                    "size": len(content),
                })
            except Exception:
                pass

    return {"configs": configs, "total": len(configs)}


@router.post("/nginx-config")
async def generate_nginx_config(request: Request):
    """生成并部署 Nginx 反向代理配置"""
    require_auth(request, _get_config(request))
    body = await request.json()

    domain = body.get("domain", "")
    proxy_pass = body.get("proxy_pass", "")
    ssl_cert = body.get("ssl_cert", "/etc/nginx/ssl/ptrel_fullchain.crt")
    ssl_key = body.get("ssl_key", "/etc/nginx/ssl/ptrel.key")

    if not domain or not proxy_pass:
        raise HTTPException(status_code=400, detail="缺少必填字段: domain, proxy_pass")

    # 生成配置内容
    config_lines = [
        f"# Nginx config for {domain} - generated by DDNS WebUI",
        "server {",
        f'    listen 443 ssl http2;',
        f'    listen [::]:443 ssl http2;',
        f'    server_name {domain};',
        "",
        f'    ssl_certificate {ssl_cert};',
        f'    ssl_certificate_key {ssl_key};',
        "",
        "    location / {",
        f'        proxy_pass {proxy_pass};',
        "        proxy_http_version 1.1;",
        '        proxy_set_header Upgrade $http_upgrade;',
        '        proxy_set_header Connection "upgrade";',
        "        proxy_set_header Host $host;",
        "        proxy_set_header X-Real-IP $remote_addr;",
        "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "        proxy_set_header X-Forwarded-Proto $scheme;",
        "    }",
        "}",
        "",
        "server {",
        "    listen 80;",
        "    listen [::]:80;",
        f'    server_name {domain};',
        "    return 301 https://$server_name$request_uri;",
        "}",
        "",
    ]
    config_text = "\n".join(config_lines)

    # 写入配置文件
    config_path = f"/etc/nginx/conf.d/{domain}.conf"
    try:
        with open(config_path, "w") as f:
            f.write(config_text)
    except Exception as e:
        return {
            "success": False,
            "config": config_text,
            "detail": f"配置文件写入失败: {e}",
            "config_path": config_path,
        }

    # 尝试自动重载 nginx
    reload_success = False
    reload_msg = ""
    import subprocess
    try:
        result = subprocess.run(
            ["nginx", "-t"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            result2 = subprocess.run(
                ["nginx", "-s", "reload"],
                capture_output=True, text=True, timeout=10,
            )
            if result2.returncode == 0:
                reload_success = True
                reload_msg = "Nginx 已自动重载"
            else:
                reload_msg = f"重载失败: {result2.stderr.strip()}"
        else:
            reload_msg = f"配置测试失败: {result.stderr.strip()}"
    except FileNotFoundError:
        reload_msg = "nginx 命令未找到"
    except Exception as e:
        reload_msg = f"重载异常: {e}"

    add_log(domain, domain, "config_add", message=f"生成 Nginx 配置: {domain} → {proxy_pass}")
    return {
        "success": True,
        "config": config_text,
        "config_path": config_path,
        "reload_success": reload_success,
        "message": f"Nginx 配置已写入 {config_path}，{'已自动重载生效' if reload_success else reload_msg}",
    }


@router.post("/dns-record/create")
async def api_create_dns_record(request: Request):
    """通过后端代理创建 DNS 记录（避免前端 CORS 问题）"""
    require_auth(request, _get_config(request))
    body = await request.json()

    required = ["subdomain_id", "type", "name", "content"]
    for field in required:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"缺少必填字段: {field}")

    config = _reload_config(request)

    from app.core import api_request as core_api_request
    create_body = {
        "subdomain_id": int(body["subdomain_id"]),
        "type": body["type"],
        "name": body["name"],
        "content": body["content"],
        "ttl": int(body.get("ttl", 600)),
    }
    if "line" in body and body["line"]:
        create_body["line"] = body["line"]
    resp = core_api_request(
        config,
        endpoint="dns_records",
        action="create",
        method="POST",
        body=create_body,
    )

    if resp is None:
        raise HTTPException(status_code=429, detail="dnshe API 请求被拒绝（可能触发了速率限制），请等待一分钟后再试")

    return {"success": True, "result": resp}


@router.put("/dns-record/{record_id}")
async def api_update_dns_record(record_id: str, request: Request):
    """更新 DNS 记录"""
    require_auth(request, _get_config(request))
    body = await request.json()

    required = ["type", "name", "content"]
    for field in required:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"缺少必填字段: {field}")

    config = _reload_config(request)

    success = update_dns_record(
        config,
        record_id=record_id,
        record_type=body["type"],
        name=body["name"],
        content=body["content"],
        ttl=int(body.get("ttl", 600)),
        line=body.get("line", ""),
    )

    if not success:
        raise HTTPException(status_code=429, detail="dnshe API 请求被拒绝（可能触发了速率限制），请等待一分钟后再试")

    add_log(f"dns_{record_id}", body["name"], "config_update", message=f"更新 DNS 记录: {body['name']} → {body['content']}")
    return {"success": True}


@router.delete("/dns-record/{record_id}")
async def api_delete_dns_record(record_id: str, request: Request):
    """删除 DNS 记录"""
    require_auth(request, _get_config(request))
    config = _reload_config(request)

    success = delete_dns_record(config, record_id=record_id)
    if not success:
        # 删除失败，检查是否是 404（dnshe 上已不存在）
        # 自动清理本地缓存
        from app.models import get_db
        conn = get_db()
        try:
            dnshe_id = int(record_id) if record_id.isdigit() else -1
        except (ValueError, TypeError):
            dnshe_id = -1
        deleted = conn.execute(
            "DELETE FROM dns_records_cache WHERE record_id = ? OR dnshe_id = ?",
            (record_id, dnshe_id),
        ).rowcount
        conn.commit()

        if deleted > 0:
            add_log(f"dns_{record_id}", "", "config_delete",
                    message=f"DNS 记录在 dnshe 上已不存在，已清理本地缓存: id={record_id}")
            return {"success": True, "warning": True,
                    "message": "该记录在 dnshe 上已不存在，已自动从本地缓存中移除"}
        else:
            raise HTTPException(status_code=500, detail="删除 DNS 记录失败，请确认该记录在 dnshe 上是否存在")

    # 同步删除本地缓存
    from app.models import get_db
    conn = get_db()
    try:
        dnshe_id = int(record_id) if record_id.isdigit() else -1
    except (ValueError, TypeError):
        dnshe_id = -1
    conn.execute("DELETE FROM dns_records_cache WHERE record_id = ? OR dnshe_id = ?",
                 (record_id, dnshe_id))
    conn.commit()

    add_log(f"dns_{record_id}", "", "config_delete", message=f"删除 DNS 记录: id={record_id}")
    return {"success": True}
