# DNSHE 免费域名 API 使用文档（V2.0）

> 来源：https://my.dnshe.com/knowledgebase/13/DNSHE-Free-Domain-API-User-Guide-V2.0.html

## 基本信息

| 项目 | 说明 |
|------|------|
| API 地址 | `https://api005.dnshe.com/index.php?m=domain_hub` |
| 认证方式 | API Key + API Secret（HTTP Header） |
| 支持格式 | JSON |
| 速率限制 | 60 请求/分钟 |

## 认证

### 获取 API 密钥

1. 登录客户区
2. 进入"免费域名管理"页面
3. 在左侧导航栏找到"API 管理"
4. 点击"创建 API 密钥"

### 认证方式

**推荐：HTTP Header**

```bash
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"
```

> ⚠️ `api_key` / `api_secret` 不再支持通过 URL Query 或请求体传递。请仅使用 `X-API-Key` 和 `X-API-Secret` 请求头认证。

---

## API 端点

### 1. 子域名管理

#### 1.1 列出子域名

- **端点**: `subdomains`
- **操作**: `list`
- **方法**: `GET`

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | integer | 否 | 1 | 页码（从 1 开始） |
| per_page | integer | 否 | 200 | 每页数量（1-500） |
| include_total | boolean | 否 | false | 是否返回总数（大数据量时较慢） |
| search | string | 否 | - | 搜索关键词（匹配 subdomain 或 rootdomain） |
| rootdomain | string | 否 | - | 按根域名过滤 |
| status | string | 否 | - | 按状态过滤（active/suspended/expired） |
| created_from | string | 否 | - | 创建时间起始（YYYY-MM-DD） |
| created_to | string | 否 | - | 创建时间结束（YYYY-MM-DD） |
| sort_by | string | 否 | id | 排序字段 |
| sort_dir | string | 否 | desc | 排序方向（asc/desc） |
| fields | string | 否 | all | 返回字段（逗号分隔，自定义时会自动补充 id） |

**请求示例**:

```bash
# 默认获取第 1 页（200 条）
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

# 分页：第 1 页，每页 100 条
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list&page=1&per_page=100" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

# 搜索包含 "test" 的域名
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list&search=test" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

# 只返回 ID 和域名字段
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list&fields=id,subdomain,rootdomain,status" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"
```

**响应示例**:

```json
{
  "success": true,
  "count": 2,
  "subdomains": [
    {
      "id": 1,
      "subdomain": "test",
      "rootdomain": "example.com",
      "full_domain": "test.example.com",
      "status": "active",
      "created_at": "2025-10-19 10:00:00",
      "updated_at": "2025-10-19 10:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 200,
    "has_more": false
  }
}
```

**性能优化建议**:
- 默认每页 200 条，建议根据需求调整 `per_page`（推荐 50-100）
- `include_total=1` 会执行 COUNT 查询，数据量大时可能较慢，仅在必要时使用
- 通过 `pagination.has_more` 判断是否有下一页，比依赖 `total` 更高效
- 使用 `fields` 参数可以显著减少数据传输量
- 最大 `per_page=500`，超过会自动限制为 500

---

#### 1.2 注册子域名

- **端点**: `subdomains`
- **操作**: `register`
- **方法**: `POST`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| subdomain | string | 是 | 子域名前缀 |
| rootdomain | string | 是 | 根域名 |

**请求示例**:

```bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=register" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{"subdomain": "myapp", "rootdomain": "example.com"}'
```

**响应示例**:

```json
{
  "success": true,
  "message": "Subdomain registered successfully",
  "subdomain_id": 3,
  "full_domain": "myapp.example.com"
}
```

---

#### 1.3 获取子域名详情

- **端点**: `subdomains`
- **操作**: `get`
- **方法**: `GET`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| subdomain_id | integer | 是 | 子域名 ID |

**请求示例**:

```bash
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=get&subdomain_id=1" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"
```

**响应示例**:

```json
{
  "success": true,
  "subdomain": {
    "id": 1,
    "subdomain": "test",
    "rootdomain": "example.com",
    "full_domain": "test.example.com",
    "status": "active",
    "created_at": "2025-10-19 10:00:00",
    "updated_at": "2025-10-19 10:00:00"
  },
  "dns_records": [...],
  "dns_count": 1
}
```

---

#### 1.4 删除子域名

- **端点**: `subdomains`
- **操作**: `delete`
- **方法**: `POST` 或 `DELETE`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| subdomain_id | integer | 是 | 子域名 ID |

**请求示例**:

```bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=delete" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{"subdomain_id": 1}'
```

**响应示例**:

```json
{
  "success": true,
  "message": "Subdomain deleted successfully",
  "subdomain_id": 1,
  "full_domain": "test.example.com",
  "dns_records_deleted": 4
}
```

---

#### 1.5 续期子域名

- **端点**: `subdomains`
- **操作**: `renew`
- **方法**: `POST` 或 `PUT`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| subdomain_id | integer | 是 | 子域名 ID |

**请求示例**:

```bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=renew" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{"subdomain_id": 3}'
```

**响应示例**:

```json
{
  "success": true,
  "message": "Subdomain renewed successfully (charged 9.90 credit)",
  "subdomain_id": 3,
  "subdomain": "myapp",
  "previous_expires_at": "2025-05-01 00:00:00",
  "new_expires_at": "2026-05-01 00:00:00",
  "renewed_at": "2025-04-10 12:34:56",
  "never_expires": 0,
  "status": "active",
  "remaining_days": 366,
  "charged_amount": 9.9
}
```

**可能的错误**:

| 错误码 | 说明 |
|--------|------|
| 403 renewal disabled | 后台未配置有效的注册年限 |
| 422 renewal not yet available | 尚未进入免费续期窗口 |
| 403 renewal window expired | 已超过续期宽限期 |
| 404 subdomain not found | 找不到对应子域名或不属于当前 API Key |

---

### 2. DNS 记录管理

#### 2.1 列出 DNS 记录

- **端点**: `dns_records`
- **操作**: `list`
- **方法**: `GET`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| subdomain_id | integer | 是 | 子域名 ID |

**请求示例**:

```bash
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=dns_records&action=list&subdomain_id=1" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"
```

**响应示例**:

```json
{
  "success": true,
  "count": 2,
  "records": [
    {
      "id": 1,
      "record_id": "5a0ce6c4d1d4c71bc5e60a2a2a0e4997",
      "name": "test.example.com",
      "type": "A",
      "content": "192.168.1.1",
      "ttl": 600,
      "priority": null,
      "status": "active",
      "created_at": "2025-10-19 10:05:00",
      "updated_at": "2025-10-19 10:05:00"
    }
  ]
}
```

> 💡 列表同时返回模块内部 `id` 和云解析服务商 `record_id`。`update`/`delete` 可使用任意一个字段定位记录（推荐优先使用 `id`）。

---

#### 2.2 创建 DNS 记录

- **端点**: `dns_records`
- **操作**: `create`
- **方法**: `POST`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| subdomain_id | integer | 是 | 子域名 ID |
| type | string | 是 | 记录类型（A/AAAA/CNAME/MX/TXT/NS/SRV/CAA） |
| name | string | 否 | 记录名称（`@` 或留空=当前子域本身） |
| content | string | 条件必填 | 记录值 |
| ttl | integer | 否 | TTL 值（默认 600） |
| priority | integer | 否 | MX/SRV 优先级 |
| line | string | 否 | 解析线路 |

> ⚠️ **重要**：`name` 参数必须传**子域名前缀**（如 `maiapi`），不能传完整域名。实测传完整域名会导致 name 被重复拼接（如 `maiapi.ptrel.cc.cd.ptrel.cc.cd`），且返回 `id=0, record_id=null`。

**请求示例**:

```bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=dns_records&action=create" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{
    "subdomain_id": 1,
    "type": "A",
    "name": "myapp",
    "content": "192.168.1.100",
    "ttl": 600
  }'
```

**响应示例**:

```json
{
  "success": true,
  "message": "DNS record created successfully",
  "id": 3,
  "record_id": "5a0ce6c4d1d4c71bc5e60a2a2a0e4997"
}
```

---

#### 2.3 更新 DNS 记录

- **端点**: `dns_records`
- **操作**: `update`
- **方法**: `POST` 或 `PUT` 或 `PATCH`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | integer | 否 | 模块内部记录 ID（推荐） |
| record_id | string | 否 | 记录定位 ID |
| type | string | 否 | 新类型 |
| name | string | 否 | 新名称 |
| content | string | 否 | 新记录值 |
| ttl | integer | 否 | 新 TTL 值 |

> ⚠️ **重要**：至少提供 `record_id` 或 `id` 其中之一。
>
> ⚠️ **已知 Bug**：`name` 参数行为异常，经实测：
> - 传子域名前缀 → 成功，但 `record_id` 会变化
> - 不传 name → name 会被重置为 `xxx.ptrel.cc.cd.ptrel.cc.cd.ptrel.cc.cd`（三重拼接！）
> - 传完整域名 → 返回 `Record conflict` 错误
>
> **推荐做法**：始终传子域名前缀作为 name，如果 update 失败则执行"先删后建"。

**请求示例**:

```bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=dns_records&action=update" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "type": "A",
    "name": "myapp",
    "content": "192.168.1.200",
    "ttl": 600
  }'
```

**响应示例**:

```json
{
  "success": true,
  "message": "DNS record updated successfully",
  "id": 1,
  "record_id": "5a0ce6c4d1d4c71bc5e60a2a2a0e4997"
}
```

---

#### 2.4 删除 DNS 记录

- **端点**: `dns_records`
- **操作**: `delete`
- **方法**: `POST` 或 `DELETE`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | integer | 否 | 模块内部记录 ID（推荐） |
| record_id | string | 否 | 云解析服务商返回的记录 ID |

> 至少提供 `record_id` 或 `id` 其中之一。

**请求示例**:

```bash
# 用数字 id 删除（推荐）
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=dns_records&action=delete" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{"id": 1}'

# 用 record_id 字符串删除
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=dns_records&action=delete" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{"record_id": "5a0ce6c4d1d4c71bc5e60a2a2a0e4997"}'
```

**响应示例**:

```json
{
  "success": true,
  "message": "DNS record deleted successfully"
}
```

---

### 3. API 密钥管理

#### 3.1 列出 API 密钥

- **端点**: `keys`
- **操作**: `list`
- **方法**: `GET`

**请求示例**:

```bash
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=keys&action=list" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"
```

**响应示例**:

```json
{
  "success": true,
  "count": 2,
  "keys": [
    {
      "id": 1,
      "key_name": "生产环境密钥",
      "api_key": "cfsd_xxxxxxxxxx",
      "status": "active",
      "request_count": 1523,
      "last_used_at": "2025-10-19 15:30:00",
      "created_at": "2025-10-19 10:00:00"
    }
  ]
}
```

#### 3.2 创建 API 密钥

- **端点**: `keys`
- **操作**: `create`
- **方法**: `POST`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| key_name | string | 是 | 密钥名称 |
| ip_whitelist | string | 否 | IP 白名单 |

**请求示例**:

```bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=keys&action=create" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{"key_name": "新密钥", "ip_whitelist": "192.168.1.1,192.168.1.2"}'
```

> ⚠️ `api_secret` 只显示一次，请妥善保存！

#### 3.3 删除 API 密钥

- **端点**: `keys`
- **操作**: `delete`
- **方法**: `POST` 或 `DELETE`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| key_id | integer | 是 | 密钥 ID |

#### 3.4 重新生成 API 密钥

- **端点**: `keys`
- **操作**: `regenerate`
- **方法**: `POST`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| key_id | integer | 是 | 密钥 ID |

---

### 4. 配额查询

- **端点**: `quota`
- **方法**: `GET`

```bash
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=quota" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"
```

```json
{
  "success": true,
  "quota": {
    "used": 3, "base": 5, "invite_bonus": 2, "total": 7, "available": 4
  }
}
```

---

### 5. WHOIS 查询（公开接口）

- **端点**: `whois`
- **方法**: `GET`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| domain | string | 是 | 完整子域名 |

```bash
# 公共模式（无需 API Key）
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=whois&domain=foo.example.com"
```

---

## 错误代码

所有 API 错误响应统一结构：

```json
{
  "success": false,
  "error_code": "auth_invalid_credentials",
  "message": "Invalid API key",
  "details": {},
  "error": "Invalid API key"
}
```

### 常见错误码

| error_code | HTTP | 说明 |
|------------|------|------|
| bad_request | 400 | 请求参数错误 |
| auth_invalid_credentials | 401 | API Key/Secret 无效或缺失 |
| auth_ip_not_allowed | 403 | 请求 IP 不在白名单 |
| not_found | 404 | 资源不存在 |
| quota_exceeded | 429 | 额度不足 |
| rate_limit_exceeded | 429 | 请求频率超限 |
| provider_operation_failed | 502 | 上游 DNS 提供商执行失败 |
| internal_error | 500 | 服务内部异常 |

---

## 已知问题与注意事项（实测总结）

### 1. DNS 记录 name 参数（重要！）

dnshe API 的 `name` 参数行为存在严重问题，经实测验证：

| 操作 | name 传值 | 结果 |
|------|-----------|------|
| **create** | 子域名前缀（如 `testapi`） | ✅ name=`testapi.ptrel.cc.cd`，正确 |
| **create** | 完整域名（如 `testapi.ptrel.cc.cd`） | ❌ 重复拼接，返回 `id=0, record_id=null` |
| **update** | 子域名前缀（如 `testapi`） | ⚠️ 成功，但 `record_id` 会变化 |
| **update** | 不传 name | ❌ 三重拼接！ |

**结论**：
- create 时必须传**子域名前缀**
- update 时必须传**子域名前缀**，不能不传
- update 失败时直接执行"先删后建"

### 2. record_id 变化

`record_id` 是基于 name/type 的哈希值，每次 update 都可能改变。**不要持久化存储 `record_id`**，推荐优先使用数字 `id`。

### 3. 更新失败处理

1. 优先用数字 `id` 直接 update（传子域名前缀 name）
2. 失败则执行"先删后建"：用数字 `id` 删除 → 用子域名前缀创建
