# DDNS IPv6 WebUI API 文档

## 基础信息

- **Base URL**: `http://<服务器IP>:5080` 或 `https://ddns.ptrel.cc.cd`
- **认证方式**: Session Cookie（先登录获取）
- **内容类型**: `application/json`

---

## 1. 认证

### 1.1 登录

获取 Session Cookie，后续所有 API 请求需携带此 Cookie。

```bash
curl -c /tmp/cookies.txt -X POST http://localhost:5080/login \
  -d "username=admin&password=admin123"
```

**响应**: `302 Found`（重定向到 `/dashboard`），Cookie 自动保存到 `/tmp/cookies.txt`

### 1.2 登出

```bash
curl -b /tmp/cookies.txt http://localhost:5080/logout
```

---

## 2. 域名管理

### 2.1 获取域名列表

```bash
curl -b /tmp/cookies.txt http://localhost:5080/api/domains
```

**响应示例**:
```json
{
    "domains": [
        {
            "id": "ipv6",
            "record_name": "ipv6.ptrel.cc.cd",
            "record_type": "AAAA",
            "subdomain_id": 404037,
            "ttl": 600,
            "enabled": true,
            "check_interval": null,
            "current_ip": "240e:390:364:1771::137",
            "last_check_at": "2026-05-23 09:07:27",
            "last_update_at": null,
            "status": "ok"
        }
    ]
}
```

### 2.2 添加域名

```bash
curl -b /tmp/cookies.txt -X POST http://localhost:5080/api/domains \
  -H "Content-Type: application/json" \
  -d '{
    "id": "ddns",
    "record_name": "ddns.ptrel.cc.cd",
    "subdomain_id": 404037,
    "record_type": "AAAA",
    "ttl": 600,
    "enabled": true
  }'
```

**参数说明**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 否 | 唯一标识，默认取子域名前缀 |
| `record_name` | string | 是 | 完整域名，如 `ddns.ptrel.cc.cd` |
| `subdomain_id` | int | 是 | dnshe 子域名 ID |
| `record_type` | string | 否 | 默认 `AAAA` |
| `ttl` | int | 否 | 默认 `600` |
| `enabled` | bool | 否 | 默认 `true` |
| `check_interval` | int | 否 | 自定义检查间隔（秒） |

### 2.3 更新域名

```bash
curl -b /tmp/cookies.txt -X PUT http://localhost:5080/api/domains/ipv6 \
  -H "Content-Type: application/json" \
  -d '{
    "ttl": 300,
    "enabled": true
  }'
```

### 2.4 删除域名

```bash
curl -b /tmp/cookies.txt -X DELETE http://localhost:5080/api/domains/ipv6
```

### 2.5 注册子域名

通过 dnshe API 直接创建子域名，无需登录 dnshe 面板。

```bash
curl -b /tmp/cookies.txt -X POST http://localhost:5080/api/domains/register-subdomain \
  -H "Content-Type: application/json" \
  -d '{
    "subdomain": "ddns",
    "rootdomain": "ptrel.cc.cd"
  }'
```

**参数说明**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `subdomain` | string | 是 | 子域名前缀，如 `ddns` |
| `rootdomain` | string | 是 | 根域名，如 `ptrel.cc.cd` |

**响应示例**:
```json
{
    "success": true,
    "result": {
        "success": true,
        "message": "...",
        "id": 404038,
        "subdomain_id": 404038
    }
}
```

> 返回的 `id` 或 `subdomain_id` 即为后续添加域名时所需的 `subdomain_id`。

---

## 3. 检测更新

### 3.1 手动触发单域名检测

```bash
curl -b /tmp/cookies.txt -X POST http://localhost:5080/api/domains/ipv6/check
```

**响应示例**:
```json
{
    "success": true,
    "result": {
        "domain_id": "ipv6",
        "record_name": "ipv6.ptrel.cc.cd",
        "action": "skip",
        "old_ip": "240e:390:364:1771::137",
        "new_ip": "240e:390:364:1771::137",
        "message": "地址未变化，跳过更新"
    }
}
```

**action 取值**:

| 值 | 说明 |
|----|------|
| `create` | 创建了新记录 |
| `update` | 更新了记录 |
| `skip` | 地址未变化，跳过 |
| `error` | 检测失败 |

### 3.2 手动触发全部域名检测

```bash
curl -b /tmp/cookies.txt -X POST http://localhost:5080/api/domains/check-all
```

---

## 4. 日志查询

### 4.1 查询操作日志

```bash
# 查询最近 50 条
curl -b /tmp/cookies.txt http://localhost:5080/api/logs

# 按域名筛选 + 分页
curl -b /tmp/cookies.txt "http://localhost:5080/api/logs?domain_id=ipv6&limit=20&offset=0"
```

**参数说明**:

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `domain_id` | string | - | 按域名筛选 |
| `limit` | int | 50 | 每页条数（最大 500） |
| `offset` | int | 0 | 偏移量 |

**响应示例**:
```json
{
    "logs": [
        {
            "id": 1,
            "domain_id": "ipv6",
            "record_name": "ipv6.ptrel.cc.cd",
            "action": "skip",
            "old_ip": "240e:390:364:1771::137",
            "new_ip": "240e:390:364:1771::137",
            "message": "地址未变化，跳过更新",
            "created_at": "2026-05-23 09:07:27"
        }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0
}
```

---

## 5. 状态查询

### 5.1 获取服务状态概览

```bash
curl -b /tmp/cookies.txt http://localhost:5080/api/status
```

**响应示例**:
```json
{
    "total_domains": 2,
    "enabled_domains": 2,
    "online_count": 2,
    "error_count": 0,
    "today_updates": 0,
    "check_interval": 300
}
```

---

## 6. 错误处理

所有 API 在出错时返回标准 HTTP 状态码和错误信息：

```json
{
    "detail": "错误描述信息"
}
```

| 状态码 | 说明 |
|--------|------|
| `200` | 成功 |
| `302` | 重定向（登录成功） |
| `400` | 请求参数错误 |
| `401` | 未登录或 Session 过期 |
| `404` | 资源不存在 |
| `500` | 服务器内部错误 |

---

## 8. 守护进程日志

### 8.1 读取守护进程日志

读取 `/main/log/app/ddns-ipv6.log` 文件内容，支持行数限制和关键词筛选。

```bash
# 读取最近 100 行
curl -b /tmp/cookies.txt "http://localhost:5080/api/logs/daemon?lines=100&tail=true"

# 读取开头 50 行
curl -b /tmp/cookies.txt "http://localhost:5080/api/logs/daemon?lines=50"

# 按关键词筛选（如 error）
curl -b /tmp/cookies.txt "http://localhost:5080/api/logs/daemon?lines=200&tail=true&keyword=error"
```

**参数说明**:

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `lines` | int | 100 | 返回行数（最大 5000） |
| `keyword` | string | - | 关键词筛选（大小写敏感） |
| `tail` | bool | false | 是否只返回末尾行（最新日志） |

**响应示例**:
```json
{
    "lines": [
        "[2026-05-24 02:44:30] DDNS IPv6 守护进程启动（含 WebUI）\n",
        "[2026-05-24 02:44:30] [INFO] WebUI 子线程已启动\n"
    ],
    "total": 1250,
    "returned": 100,
    "lines_requested": 100,
    "file": "/main/log/app/ddns-ipv6.log",
    "tail": true,
    "keyword": null
}
```

---

## 9. 完整使用示例

```bash
#!/bin/bash
# 1. 登录
curl -c /tmp/ddns.txt -X POST http://localhost:5080/login \
  -d "username=admin&password=admin123"

# 2. 查看状态
curl -b /tmp/ddns.txt http://localhost:5080/api/status

# 3. 创建子域名
curl -b /tmp/ddns.txt -X POST http://localhost:5080/api/domains/register-subdomain \
  -H "Content-Type: application/json" \
  -d '{"subdomain": "myapp", "rootdomain": "example.com"}'

# 4. 添加域名到 DDNS 监控
curl -b /tmp/ddns.txt -X POST http://localhost:5080/api/domains \
  -H "Content-Type: application/json" \
  -d '{
    "id": "myapp",
    "record_name": "myapp.example.com",
    "subdomain_id": 123456,
    "record_type": "AAAA",
    "ttl": 600,
    "enabled": true
  }'

# 5. 手动触发检测
curl -b /tmp/ddns.txt -X POST http://localhost:5080/api/domains/myapp/check

# 6. 查看日志
curl -b /tmp/ddns.txt "http://localhost:5080/api/logs?domain_id=myapp&limit=10"
```
