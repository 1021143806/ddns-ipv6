# AI 操作指导：通过 POST 接口管理域名解析

> 供 AI（或任何自动化调用方）通过 ddns-ipv6 WebUI API 完成"域名解析管理"。
> 核心原则：**所有操作先登录拿 Cookie，全部用 POST 接口**；阿里云与 dnshe 双 provider 按域名归属区分。

## 一、操作前必读

1. **登录**：所有接口需携带 Session Cookie（`/login` 拿）
2. **区分 provider**：
   - `ptrel.cc.cd` 系列 → `provider = "dnshe"`（需 subdomain_id）
   - `ptrel.asia` 系列 → `provider = "aliyun"`（subdomain_id 填 0）
3. **dnshe 限流**：60 次/分钟，操作频繁会 429，需等 1 分钟
4. **AccessKey 勿提交**：阿里云凭据只在服务器本地 config/env.toml，任何文档/代码不得写密钥

## 二、标准操作流程

### 步骤 0：登录（必须先做）

```bash
curl -c /tmp/cookies.txt -X POST http://localhost:5080/login \
  -d "username=admin&password=admin123"
```

### 步骤 1：查域名列表（确认目标域名归属哪个 provider）

```bash
curl -b /tmp/cookies.txt http://localhost:5080/api/domains
```
返回每条含 `provider` 字段（dnshe/aliyun）和当前状态。

### 步骤 2：查 DNS 记录（确认记录是否已存在）

```bash
curl -b /tmp/cookies.txt http://localhost:5080/api/domains/dns-records
```
返回全部记录（dnshe + 阿里云合并），每条带 `provider` 标签。

### 步骤 3：创建/更新记录

**如果记录已存在** → 用 `dns-record/{record_id}` PUT 更新；
**如果不存在** → 用 `dns-record/create` POST 创建，或 `register-subdomain` 创建子域名。

### 步骤 4：加入 DDNS 自动监控（可选）

用 `POST /api/domains` 添加域名配置，守护进程会每 300s 自动同步 IP。

### 步骤 5：验证

```bash
# 触发单域名检查
curl -b /tmp/cookies.txt -X POST http://localhost:5080/api/domains/{id}/check
# 看操作日志
curl -b /tmp/cookies.txt "http://localhost:5080/api/logs?limit=10"
# 权威 DNS 验证
dig @ns7.dnshe.com 域名 AAAA        # dnshe
dig @ns1.alidns.com 域名 AAAA       # 阿里云
```

## 三、常用 POST 接口速查

| 操作 | 接口 | 关键参数 |
|------|------|---------|
| 登录 | `POST /login` | `username`, `password` |
| 添加域名 | `POST /api/domains` | `record_name`, `provider`, `subdomain_id`, `record_type` |
| 创建子域名 | `POST /api/domains/register-subdomain` | `provider`, `subdomain`, `rootdomain` |
| 创建记录 | `POST /api/domains/dns-record/create` | `provider`, `type`, `name`, `content`, `ttl` |
| 单域名检查 | `POST /api/domains/{id}/check` | - |
| 全部检查 | `POST /api/domains/check-all` | - |
| 刷新记录缓存 | `POST /api/domains/dns-records/refresh` | - |

## 四、AI 决策规则（重要）

**1. 判断域名归属：**
```python
def which_provider(record_name: str) -> str:
    if record_name.endswith(".asia") or record_name.endswith(".aliyuncs.com"):
        return "aliyun"
    return "dnshe"
```

**2. 判断创建还是更新：**
- `dns-records` 里已有同名同类型记录 → **更新**（用 record_id）
- 没有 → **创建**

**3. 创建时参数差异：**

| 参数 | dnshe | 阿里云 |
|------|-------|--------|
| `name` | 子域名前缀（如 `test`） | 完整域名（如 `test.ptrel.asia`） |
| `subdomain_id` | 必填（如 404037） | 填 `0` |
| `provider` | 缺省即可 | 必填 `"aliyun"` |

**4. 值填什么：**
- AAAA 记录 → 本机 IPv6（当前 `240e:390:3c7:ef00::8a8`）
- A 记录 → 公网出口 IPv4（当前 `115.197.187.231`）
- 不确定时调用 `/api/status` 或守护进程日志查最近检测值

**5. 创建后的验证顺序：**
1. 看接口响应（success 字段）
2. `dig` 权威 DNS 确认
3. 加入 DDNS 后等 300s 全量同步，看日志确认 skip/update

## 五、典型场景脚本

### 场景 A：给新服务域名配 DDNS（dnshe）

```bash
# 1. 登录
curl -c /tmp/c.txt -X POST http://localhost:5080/login -d "username=admin&password=admin123"
# 2. 创建子域名（若 dnshe 面板还没建）
curl -b /tmp/c.txt -X POST http://localhost:5080/api/domains/register-subdomain \
  -H "Content-Type: application/json" \
  -d '{"subdomain": "newsvc", "rootdomain": "ptrel.cc.cd"}'
# 3. 加 DDNS 监控
curl -b /tmp/c.txt -X POST http://localhost:5080/api/domains \
  -H "Content-Type: application/json" \
  -d '{"id": "newsvc", "record_name": "newsvc.ptrel.cc.cd", "subdomain_id": 404037, "record_type": "AAAA", "ttl": 600, "enabled": true}'
# 4. 验证
curl -b /tmp/c.txt -X POST http://localhost:5080/api/domains/newsvc/check
```

### 场景 B：给阿里云域名配 DDNS

```bash
# 1. 登录
curl -c /tmp/c.txt -X POST http://localhost:5080/login -d "username=admin&password=admin123"
# 2. 创建记录（阿里云"创建子域名"= 直接建 AAAA 记录）
curl -b /tmp/c.txt -X POST http://localhost:5080/api/domains/register-subdomain \
  -H "Content-Type: application/json" \
  -d '{"provider": "aliyun", "subdomain": "newsvc", "rootdomain": "ptrel.asia"}'
# 3. 加 DDNS 监控
curl -b /tmp/c.txt -X POST http://localhost:5080/api/domains \
  -H "Content-Type: application/json" \
  -d '{"id": "newsvc", "record_name": "newsvc.ptrel.asia", "provider": "aliyun", "subdomain_id": 0, "record_type": "AAAA", "ttl": 600, "enabled": true}'
# 4. 验证
curl -b /tmp/c.txt -X POST http://localhost:5080/api/domains/newsvc/check
dig @ns1.alidns.com newsvc.ptrel.asia AAAA
```

### 场景 C：查询域名状态

```bash
curl -c /tmp/c.txt -X POST http://localhost:5080/login -d "username=admin&password=admin123"
curl -b /tmp/c.txt http://localhost:5080/api/status
curl -b /tmp/c.txt http://localhost:5080/api/domains
```

## 六、常见错误与处理

| 错误 | 原因 | 处理 |
|------|------|------|
| `429 Too Many Requests` | dnshe 限流（60/min） | 等 1 分钟重试，勿连续调用 |
| `400 缺 subdomain_id` | 阿里云域名漏传 provider | 阿里云填 `subdomain_id: 0` 且 `provider: "aliyun"` |
| `400 记录名含下划线` | dnshe A/AAAA 记录名禁 `_` | 用连字符 `-` |
| `DomainRecordDuplicate` | 阿里云记录已存在 | 改走更新接口 |
| `401` | Cookie 过期 | 重新登录 |

## 七、安全铁律

1. **绝不把 AccessKey 写进任何会被 git 跟踪的文件**（README/skill/doc）
2. 阿里云凭据只在服务器本地 `config/env.toml`
3. 操作用 RAM 子账号最小权限（仅云解析记录管理）
