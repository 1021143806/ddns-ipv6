# DDNS IPv6 项目 Skill

> 本项目同时有全局 skill：`/main/skill/ddns-ipv6.md`（服务器运维视角，含当前域名清单、SSL 证书、已知问题）。本项目文件侧重开发与配置细节。
> 🔒 **敏感凭据（阿里云 AccessKey、密码）见本地 `skill/secret.md`**（该文件已 gitignore，不提交）。本文档及任何被 git 跟踪的文件**严禁**出现凭据明文。

## 项目概述
DDNS IPv6 动态域名解析服务，通过 dnshe.com API 自动更新 AAAA 记录。
v2.0 新增 FastAPI WebUI 管理界面，支持多域名管理、用户认证、操作日志。
v2.1 新增双循环检测架构（10s 快速检测 + 300s 全量同步）、HTTPS 端口可配置、DNS 记录在线编辑、API 调用统计可视化。
v2.2（进行中）新增**阿里云云解析 provider**：原有 dnshe 功能完全不动，通过 `[[domains]].provider` 字段选择 `dnshe` 或 `aliyun` 后端，两套 CRUD 并存。

## 关键路径
- 项目根目录: `/main/app/github/ddns-ipv6`
- 配置文件: `config/env.toml`（已 gitignore）
- 配置模板: `config/template/env.template.toml`
- SQLite 数据库: `data/ddns.db`（已 gitignore）
- 日志目录: `/main/log/app/`
- API 文档: `doc/api/README.md`
- 证书文档: `doc/ssl/README.md`（acme.sh 申请 *.ptrel.cc.cd 通配符证书）
- 阿里云接入文档: `doc/aliyun.md`（v2.2 阿里云 provider 完整接入步骤）
- 外部设备排查指引: `doc/troubleshooting.md`（IPv6 连不上/解析不生效排查流程）

## 阿里云云解析支持（v2.2 进行中）

> 目标：ddns-ipv6 同时支持 **dnshe** 与 **阿里云云解析** 两个 provider，原有 dnshe 功能不动，通过配置切换。

### 架构
```
config/env.toml
  [aliyun]            ← 新增段：access_key_id / access_key_secret
  [[domains]]
    provider = "dnshe"  ← 默认（原有）
    provider = "aliyun" ← 新增，走阿里云 OpenAPI
```

### 代码结构
| 文件 | 说明 |
|------|------|
| `app/aliyun_dns.py`（新增） | 阿里云 OpenAPI 封装：HMAC-SHA1 签名、`DescribeDomainRecords`/`AddDomainRecord`/`UpdateDomainRecord`/`DeleteDomainRecord` |
| `app/core.py` | `check_and_update_domain` 按 `provider` 分发：`_check_and_update_domain_dnshe`（原逻辑）/ `_check_and_update_domain_aliyun`（新增） |
| `config/env.toml` | `[aliyun]` 段 + 各域名 `provider` 字段 |
| WebUI | 域名列表按 provider 显示徽章（dnshe 灰 / 阿里云 橙），dns-records 接口合并两provider记录并打标签；创建子域名/添加记录模态框带 provider 下拉（dnshe 注册子域名 / 阿里云直接建 AAAA 记录） |
| `GET /api/help` | 无需登录返回使用说明+接口文档+AI 决策规则（供外部工具/AI 发现服务能力） |

### 阿里云凭据（RAM 子账号 power-user-access）
- 🔒 **AccessKey 明文见本地 `skill/secret.md`**（已 gitignore）与 `config/env.toml` 的 `[aliyun]` 段
- 已授权：云解析 DNS 记录管理（DescribeDomainRecords/AddDomainRecord/UpdateDomainRecord/DeleteDomainRecord）
- ⚠️ **严禁**把 AccessKey 写入 skill/README/doc 等被 git 跟踪的文件，否则 GitHub push protection 拦截；泄露需到阿里云 RAM 轮换密钥
- 若本地 config/env.toml 缺失该段，从 `skill/secret.md` 补写

### 阿里云托管域名（2026-08-15 实测）
| 域名 | 已有记录 | 说明 |
|------|---------|------|
| `ptrel.asia` | `ipv6.AAAA → 240e:390:3c7:ef00::8a8`、`@.A → 47.98.244.173`、`ant.A → 47.98.244.173`、`newapi.A / newapi2.A → 47.98.244.173` | 云解析中唯一域名，NS 托管在阿里云 |

**ant.ptrel.asia（Antigravity 2 API，2026-08-15 配置）**
- A 记录 → `47.98.244.173`（阿里云固定 IP，**手动维护，勿加 DDNS**——DDNS 会覆盖成本机 NAT IP）
- 证书：Let's Encrypt ECC，`/etc/nginx/ssl/ant_ptrel_asia_fullchain.crt`（acme.sh DNS 验证，2026-10-13 自动续期，到 2026-11-13）
- nginx：`/etc/nginx/conf.d/ant-ptrel-asia.conf`，443 反代 → `127.0.0.1:58045`（frp 隧道 → 本机 8045）
- 访问：`https://ant.ptrel.asia`（HTTP 自动 301 跳 HTTPS）
- frp：`ant2api8045` 隧道（本地 8045 → 公网 58045）

**newapi.ptrel.asia（New API #1，2026-08-15 配置）**
- A 记录 → 47.98.244.173（手动，勿加 DDNS）；证书 `/etc/nginx/ssl/newapi_ptrel_asia_fullchain.crt`
- nginx `newapi-ptrel-asia.conf`：443 → `127.0.0.1:53100`（frp `newapi3100`：本地 3100 → 公网 53100）
- 访问 `https://newapi.ptrel.asia`

**newapi2.ptrel.asia（New API #2，2026-08-15 配置）**
- A 记录 → 47.98.244.173（手动，勿加 DDNS）；证书 `/etc/nginx/ssl/newapi2_ptrel_asia_fullchain.crt`
- nginx `newapi2-ptrel-asia.conf`：443 → `127.0.0.1:53102`（frp `newapi3102`：本地 3102 → 公网 53102）
- 访问 `https://newapi2.ptrel.asia`

**git.ptrel.asia（Gitea，2026-08-15 配置）**
- A 记录 → 47.98.244.173（手动，勿加 DDNS）；证书 `/etc/nginx/ssl/git_ptrel_asia_fullchain.crt`
- nginx `git-ptrel-asia.conf`：443 → `https://127.0.0.1:53103`（**注意反代用 https，gitea 自身 PROTOCOL=https**）+ `proxy_ssl_verify off`
- gitea 配置 `/main/app/gitea/config/app.ini`：DOMAIN/ROOT_URL/SSH_DOMAIN 已改为 `git.ptrel.asia`
- frp：`gitea3103`（本地 3103 → 公网 53103）、`giteaSSH2222`（本地 2222 → 公网 52222）
- 访问：`https://git.ptrel.asia`（Web）、SSH 克隆 `git@git.ptrel.asia:52222:a1/repo.git`（或 :2222 内网）

**postsup.ptrel.asia（PostSup，2026-08-15 部署）**
- PostSup = supervisor 管理平台（Go 单二进制，项目 `/main/app/github/postsup`）
- A 记录 → 47.98.244.173（手动，勿加 DDNS）；证书 `/etc/nginx/ssl/postsup_ptrel_asia_fullchain.crt`
- nginx `postsup-ptrel-asia.conf`：443 → `127.0.0.1:55014`（frp `postsup5014`：本地 5014 → 公网 55014）
- supervisor：`/main/server/supervisor/conf.d/postsup.conf`，程序 `postsup`
- ⚠️ 端口从默认 5013 改 **5014**（5013 被 supervisor-webui 占用）；supervisor_dir 改本机 `/main/server/supervisor/conf.d/`
- 账号：admin / 🔒（密码见 `skill/secret.md`，配置在 `config/ops.toml` `[account.users]`）
- 访问：`https://postsup.ptrel.asia`；构建：`go build -o bin/psupd ./cmd/psupd`（需代理拉依赖）
- 登录 API：`POST /api/login`（`{"username","password"}` → `{"ok":true}`）
- ⚠️ gitea 是 HTTPS 服务，nginx 反代必须 `proxy_pass https://` + `proxy_ssl_verify off`；若用 http 反代会 400

> 注意：`ptrel.cc.cd` 的 NS 在 dnshe（免费域名，无法迁到阿里云），阿里云只能管理 `ptrel.asia` 等托管在阿里云云解析的域名。

### 接入步骤（供后续实施）
1. 确保 `config/env.toml` 有 `[aliyun]` 段（AccessKey 已写入）
2. 在 `[[domains]]` 添加阿里云域名，如：
   ```toml
   [[domains]]
   id = "asia-ipv6"
   provider = "aliyun"
   subdomain_id = 0            # 阿里云不用 subdomain_id，占位即可
   record_name = "ipv6.ptrel.asia"
   record_type = "AAAA"
   ttl = 600
   enabled = true
   ```
3. 重启：`supervisorctl restart ddns-ipv6`
4. 验证：`dig @ns1.alidns.com ipv6.ptrel.asia AAAA`
5. 全量同步时按 provider 分发，阿里云走 `app/aliyun_dns.py`

### 阿里云 API 已知坑
- 记录名拆分：`ipv6.ptrel.asia` → RR=`ipv6`，主域=`ptrel.asia`；主域记录 RR=`@`
- `UpdateDomainRecord` 阿里云可用（与 dnshe 不同，无需先删后建）
- 签名算法：HMAC-SHA1，密钥 = Secret + "&"，规范化查询串按字典序 URL 编码

## Supervisor 进程
守护进程和 WebUI 合并为同一个进程（WebUI 在子线程中运行）：
- `ddns-ipv6`: 后台检测守护进程 + WebUI 管理界面（`ddns_daemon.py`，端口 5080）
- 旧 `ddns-ipv6-webui` 独立进程已废弃，勿再部署

### 配置文件
- 项目内模板: [`ddns-ipv6.conf`](ddns-ipv6.conf)（单个 program）
- 部署目标: `/main/server/supervisor/conf.d/ddns-ipv6.conf`
  （`/etc/supervisord.conf` 的 `[include]` 加载 `/main/server/supervisor/conf.d/*.conf`）

### 部署流程
```bash
# 1. 复制配置文件到 supervisor 目录
sudo cp ddns-ipv6.conf /main/server/supervisor/conf.d/

# 2. 更新 supervisor 并启动
sudo supervisorctl update

# 3. 查看状态
sudo supervisorctl status ddns-ipv6
```

### 常用命令
```bash
# 查看状态
supervisorctl status ddns-ipv6

# 重启
supervisorctl restart ddns-ipv6

# 查看日志
tail -f /main/log/app/ddns-ipv6.log

# 修改配置后重载
supervisorctl update
```

### 一键部署脚本
```bash
sudo bash deploy.sh
```

### 注意事项
- 修改 supervisor 配置后必须执行 `supervisorctl update` 才能生效
- 日志文件限制 1MB，自动轮转（保留 0 个备份）
- WebUI 在守护进程的子线程中运行，进程退出时自动关闭
- 如果 supervisor 未安装，先安装：`apt install supervisor`

## 依赖
- 守护进程: Python 3.11+ 标准库
- WebUI: fastapi, uvicorn, jinja2, python-multipart, itsdangerous

## 注意事项
- 配置文件格式为 TOML，多域名使用 `[[domains]]` 数组
- WebUI 默认用户名/密码: admin/admin123
- 修改 supervisor 配置后需 `supervisorctl update`
- 旧版 `ddns.py` 保留兼容，新版守护进程为 `ddns_daemon.py`

## 公网服务部署方法（完整流程，2026-08-15 实操验证）

> 把本机服务暴露到公网并配域名访问的**标准流程**。适用两类域名：
> - **ptrel.cc.cd**（dnshe 托管，动态 IP → DDNS 自动更新）
> - **ptrel.asia**（阿里云云解析，固定 IP → 手动 A 记录）

### 流程总览

```
┌──────────────────────────────────────────────────────────┐
│ 步骤1 服务本机运行（supervisor / docker）                │
│ 步骤2 内网可达（本机 127.0.0.1:PORT）                    │
│ 步骤3 公网可达（frp 隧道 或 直接公网 IP）                │
│ 步骤4 DNS 记录（A/AAAA 指向公网入口）                    │
│ 步骤5 SSL 证书（*.ptrel.cc.cd 通配 / 单域名）            │
│ 步骤6 阿里云 nginx 443 反代 → 公网端口                   │
│ 步骤7 验证 https://域名                                │
└──────────────────────────────────────────────────────────┘
```

### 步骤详解

**① 本机服务**
- supervisor 部署：`/main/server/supervisor/conf.d/*.conf` + `supervisorctl update`
- 确认监听：`ss -tlnp | grep PORT`

**② frp 隧道（内网→公网）**
- 修改 `/main/app/github/frp/frpc_a5.toml`：
```toml
[[proxies]]
name = "mysvc-PORT"
type = "tcp"
localIP = "127.0.0.1"
localPort = PORT
remotePort = 58xxx          # 公网端口（5 位数）
```
- 重启：`supervisorctl restart frpc`（**严禁重启 frpc22 / kill**）
- 验证：阿里云上 `timeout 5 bash -c 'echo > /dev/tcp/127.0.0.1/58xxx'`

**③ 判断域名归属 → 加 DNS 记录**

| 域名 | provider | 记录方式 | IP |
|------|----------|---------|-----|
| `*.ptrel.cc.cd` | dnshe | **DDNS 自动**（env.toml 加 [[domains]] + restart） | 本机动态 IP |
| `*.ptrel.asia` | aliyun | **手动 A 记录**（勿加 DDNS！） | 阿里云固定 IP `47.98.244.173` |

- dnshe：`config/env.toml` 加 `[[domains]]` → `supervisorctl restart ddns-ipv6`
- 阿里云：WebUI「创建子域名」选阿里云 或 直接调 `app/aliyun_dns.py`
- ⚠️ **阿里云域名的 A 记录指向 47.98.244.173（frps 服务器），绝不能被 DDNS 覆盖成本机 NAT IP**

**④ SSL 证书**

| 情况 | 方法 |
|------|------|
| `*.ptrel.cc.cd` | 已有通配符 `/etc/nginx/ssl/ptrel_fullchain.crt`（acme.sh 自动续期） |
| 新 `.asia` 域名 | 阿里云服务器：`~/.acme.sh/acme.sh --issue --dns dns_ali -d 域名`（用阿里云 AccessKey DNS 验证）→ 拷贝到 `/etc/nginx/ssl/` |

**⑤ 阿里云 nginx 反代**（`/etc/nginx/conf.d/xxx.conf`）
```nginx
server {
    listen 443 ssl http2;
    server_name 域名;
    ssl_certificate /etc/nginx/ssl/证书.crt;
    ssl_certificate_key /etc/nginx/ssl/证书.key;
    location / {
        proxy_pass http://127.0.0.1:58xxx;   # frp 公网端口
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
server { listen 80; server_name 域名; return 301 https://$server_name$request_uri; }
```
- `nginx -t && nginx -s reload`

**⑥ 验证**
```bash
dig @114.114.114.114 域名 A
curl -sk -o /dev/null -w "%{http_code}\n" https://域名/
```

### 已应用实例
- **ant.ptrel.asia**（Antigravity 2 API）：A 记录 47.98.244.173 + acme 证书 + nginx 443→58045→frp→本机8045
- **ddns.ptrel.cc.cd**：DDNS AAAA + 通配符证书 + nginx 443→5080
- **dsh.ptrel.cc.cd**：A 记录 47.98.244.173 + nginx 443→53080→frp→本机3080

### ⚠️ ant2api 区域限制修复记录（2026-08-15）
- **现象**：ant2api 调用返回 `400 User location is not supported for the API use`（FAILED_PRECONDITION）
- **根因**：ant2api 上游 `daily-cloudcode-pa.sandbox.googleapis.com`（Cloud Code 内部 API）按**出口 IP 地区**判定，而 mihomo 默认节点（日本高级 IEPL 专线 2 等）出口被 Google 标记为不支持区域
- **排查过程**：本地直连/公网端口/域名 HTTPS 全链路都通（403/401 是上游拒绝），逐个节点测试才定位到节点 IP 问题
- **修复**：mihomo 新增 `ant2api-SG` 分组（`filter: 新加坡高级 IEPL 专线 3`）+ rules 加 `DOMAIN-SUFFIX,googleapis.com,ant2api-SG` → Cloud Code API 走新加坡节点
- **可用节点实测**：`🇸🇬 新加坡高级 IEPL 专线 3`（3/3 稳定）✅；`🇯🇵 日本实验性 IEPL 专线 1`（2/3 不稳定）
- **教训**：Google 系 API 的区域限制是**节点 IP 级**，不是账号级；换节点即可解决，无需动 ant2api/账号

### 常见坑
- frp 隧道端口必须 5 位数（如 58045），避免与公网常见端口冲突
- 阿里云 nginx 反代目标 = **frp 公网端口**（127.0.0.1:58xxx），不是本机原始端口
- HTTPS 服务如遇 WebSocket/SSE 需 `proxy_buffering off` + Upgrade 头
- acme.sh 的 `--server letsencrypt` 与 ARI 续期窗口（自动，无需 cron 手动）

## 公网访问配置

### 方式一：Nginx HTTPS 反向代理（推荐）

已有通配符 SSL 证书 `/etc/nginx/ssl/ptrel_fullchain.crt`，域名 `*.ptrel.cc.cd`。

```nginx
# /etc/nginx/conf.d/ddns-webui.conf
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ddns.ptrel.cc.cd;

    ssl_certificate /etc/nginx/ssl/ptrel_fullchain.crt;
    ssl_certificate_key /etc/nginx/ssl/ptrel.key;

    location / {
        proxy_pass http://127.0.0.1:5080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    listen [::]:80;
    server_name ddns.ptrel.cc.cd;
    return 301 https://$server_name$request_uri;
}
```

重载 nginx：
```bash
sudo nginx -s reload
```

### 方式二：直接端口访问
WebUI 默认监听 `0.0.0.0:5080`，防火墙放行即可：
```bash
# 如果使用 firewalld
firewall-cmd --add-port=5080/tcp --permanent
firewall-cmd --reload
```

### 方式三：frp 内网穿透
如果服务器在内网，通过 frp 暴露：
```ini
# frpc.ini
[ddns-webui]
type = tcp
local_ip = 127.0.0.1
local_port = 5080
remote_port = 5080
```

### DNS 记录
在 dnshe.com 面板添加 AAAA 记录指向服务器 IPv6 地址：
```
名称: ddns
类型: AAAA
值: 240e:390:364:1771::137
TTL: 600
```

或通过 WebUI API 直接创建：
```bash
# 先登录
curl -c /tmp/cookies.txt -X POST http://localhost:5080/login \
  -d "username=admin&password=admin123"

# 创建子域名
curl -b /tmp/cookies.txt -X POST http://localhost:5080/api/domains/register-subdomain \
  -H "Content-Type: application/json" \
  -d '{"subdomain": "ddns", "rootdomain": "ptrel.cc.cd"}'

# 添加 DDNS 监控
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

## 日志查看

### 方式一：WebUI 页面
访问 `/logs` 页面，切换到 **⚙️ 守护进程日志** Tab：
- 支持选择行数（50/100/200/500）
- 支持关键词筛选（如输入 `error` 只看错误日志）
- 支持手动刷新

### 方式二：API 接口
```bash
# 先登录
curl -c /tmp/cookies.txt -X POST http://localhost:5080/login \
  -d "username=admin&password=admin123"

# 读取最新 100 行
curl -b /tmp/cookies.txt "http://localhost:5080/api/logs/daemon?lines=100&tail=true"

# 按关键词筛选（如 error）
curl -b /tmp/cookies.txt "http://localhost:5080/api/logs/daemon?lines=200&tail=true&keyword=error"

# 读取开头 50 行
curl -b /tmp/cookies.txt "http://localhost:5080/api/logs/daemon?lines=50"
```

### 方式三：服务器直接查看
```bash
# 实时跟踪最新日志
tail -f /main/log/app/ddns-ipv6.log

# 查看最近 100 行
tail -100 /main/log/app/ddns-ipv6.log

# 只看错误
grep "ERROR" /main/log/app/ddns-ipv6.log

# 按时间范围查看（如 5 月 24 日）
grep "2026-05-24" /main/log/app/ddns-ipv6.log
```

### 日志文件说明
| 文件 | 说明 |
|------|------|
| `/main/log/app/ddns-ipv6.log` | 守护进程日志（含 WebUI 启动信息） |
| `data/ddns.db` 的 `ddns_logs` 表 | WebUI 操作日志（通过 API 查询） |

## API 文档
详见 [`doc/api/README.md`](doc/api/README.md)

## 速率限制
- dnshe API 限制：**60 次/分钟**（文档标注）
- 软件预警阈值：**300 次/小时**（`app/models.py` 中 `API_HOURLY_LIMIT`）
- 超出预警时：跳过本次调用，等待下一轮（不缓存，避免积压）
- 每次 API 调用自动记录到 `api_call_log` 表
- 仪表盘展示折线图 + 实时速率状态

## v2.1 双循环检测架构
- **快速检测循环**：10s 间隔，`ip -6 addr show` 获取本机 IPv6，与上次对比，变化则立即更新
- **全量同步循环**：300s 间隔，遍历所有 enabled 域名，dnshe API 查询/创建/更新（先删后建），自动清理 name 重复拼接的脏数据
- 双循环协同：快速检测保响应速度，全量同步保最终一致性

## 已知问题（2026-08-15 已修复）
- ~~守护进程日志持续出现 `API HTTP 错误 400: Bad Request` + `创建 AAAA 记录失败`~~
- ✅ **已定位并修复**：根因是 `napcat_na` / `napcat_Hilda` / `napcat_hilda` 三个域名带下划线，dnshe 的 A/AAAA 记录名不允许下划线 → 每轮创建必 400。已重命名为 `napcat-na` / `napcat-Hilda` / `napcat-hilda`（连字符），创建成功。
- 恢复：重启 ddns-ipv6 后 400 不再出现；首次重启触发 dnshe 60次/分钟限流(429)属瞬时现象，下一轮全量同步自动恢复。

## 2026-08-15 双栈改造记录
- 给所有 AAAA 域名补了对应 A 记录（IPv4 DDNS），实现 A+AAAA 双栈
  - env.toml 每域名两个 `[[domains]]` 块（record_type 不同），id 用 `-a` 后缀区分（如 ddns + ddns-a）
  - 全局共 31 条域名配置（15 AAAA + 16 A，含原有 ipv4z）
- **背景**：外部设备纯 IPv6 出口不可用（test-ipv6 实测），加 A 记录让其 fallback 到 IPv4
  - ⚠️ A 记录指向公网出口 `115.197.187.231`（NAT 后），公网 80/443 不可达，内网设备可经 NAT 回流访问
  - 公网访问仍走 frp + 阿里云反代；域名无 nginx 站点时外部仍不可达
- `/domains` WebUI：`renderRecords` 重构为按域名分组，A+AAAA 合并为一行显示（`buildStackRow`），各自记录保留独立编辑/删除
- **全量同步优化**（防 dnshe 429 限流）：快速检测(10s)已覆盖 IP 变化，全量同步(300s)增加跳过逻辑
  - `last_sync_map`（domain_id -> (ip, status)）记录上次同步结果
  - 非强制轮次：IP 未变且上次 ok → 跳过远端 API 调用（A 记录用缓存 IPv4 判断）
  - 强制轮：`force_full_interval = 1800s` 兜底真查远端（防远端记录被外部改/删）
  - 双栈后 32 域名每轮全量必触发 dnshe 60次/分钟限流，优化后非强制轮几乎零 API 调用

## ds 说
- 2026-08-15 (PostSup 部署): postsup.ptrel.asia 部署完成。⚠️ 坑：① 5013 被 supervisor-webui 占用→改 5014 ② supervisor_dir 改本机路径 ③ go build 需代理（GOPROXY=goproxy.cn）。frp 隧道 postsup5014(55014)。完整链路 https://postsup.ptrel.asia 验证通过。
- 2026-08-15 (HTTP/2禁用): 阿里云 nginx **全局禁用 HTTP/2**（6 个 conf 共 10 处 `listen 443/8443 ssl http2` → `listen ... ssl`），因 Rikka Hub(okhttp) 与 HTTP/2+反代连接复用有偶发 `Connection reset` 兼容问题。HTTP/1.1 高频 20/20 稳定。备份在 `/etc/nginx/backup/20260815_http2/`。ALPN 不再协商 h2。⚠️ 后续新增反代配置**不要带 http2**。
- 2026-08-15 (napcat30 恢复): napcat30 容器 8/14 被 SIGKILL(137) 后未自动拉起（restart=unless-stopped 失效），`docker start` 恢复。napcat27/25 按需移除（`docker stop && rm`）。清理失效 nginx 配置 `napcat_na`/`napcat_hilda`（下划线旧域名，dnshe 已改连字符，无 DNS 记录）→ 备份至 `/etc/nginx/conf.d/old_20260815/`。⚠️ **WebUI 访问坑**：napcat WebUI 是 HTTP 服务，frp 隧道(56128→6128)是 TCP 纯隧道，**必须用 `http://47.98.244.173:56128/webui/` 访问**，用 https 会握手失败(Connection reset)。本机 nginx 443/4443 已有大量 `conflicting server name`/`protocol options redefined` 警告（mcphub.conf 与 mcphub.ptrel.cc.cd.conf 等重复），待清理。
- 2026-08-15 (gitea): git.ptrel.asia 阿里云 HTTPS 完成。⚠️ 坑：gitea 自身 PROTOCOL=https，nginx 反代必须 `proxy_pass https://` + `proxy_ssl_verify off`，用 http 会 400。gitea DOMAIN/ROOT_URL/SSH_DOMAIN 已切到新域名。
- 2026-08-15 (ant2api 修复): Cloud Code API 区域限制问题修复。mihomo 新增 ant2api-SG 分组强制走新加坡节点 + googleapis.com 域名规则。✅ 域名调用恢复。
- 2026-08-15 (newapi 双实例): newapi.ptrel.asia + newapi2.ptrel.asia 走通阿里云 HTTPS 方案（A 记录 + acme DNS 证书 + nginx 443 反代 frp 端口）。容器/frp 隧道未动，仅新增域名访问层。访问 https://newapi.ptrel.asia / https://newapi2.ptrel.asia
- 2026-08-15 (ant.ptrel.asia): Antigravity 2 API 域名访问配置完成。A 记录(手动,47.98.244.173) + acme.sh DNS 验证证书(自动续期至 2026-10-13) + 阿里云 nginx 443 反代 58045(frp→本机8045)。访问 https://ant.ptrel.asia。⚠️ 该 A 记录指向阿里云固定 IP，勿加 DDNS（会覆盖成本机 NAT IP）。
- 2026-08-15 (安全事件): GitHub push protection 拦截——AccessKey 曾误写入 doc/aliyun.md 和 skill/skill.md（被 git 跟踪），已 `git reset --soft` 回退、清除密钥、重新提交推送。**教训：任何密钥只进 config/env.toml 与 skill/secret.md（gitignore），禁止写入会被 git 跟踪的文档/skill**。若密钥曾进过远端历史需轮换。
- 2026-08-15: 同步全局 skill `/main/skill/ddns-ipv6.md`。修正 supervisor 部署路径为 `/main/server/supervisor/conf.d/`（经 /etc/supervisord.conf include 加载），废弃旧 WebUI 独立进程描述。记录当前 dnshe 400 创建 AAAA 失败问题（影响 ant2api 等新增域名），待跟进。
- 2026-08-15 (下午): 修复 400 根因（napcat 下划线→连字符）；全域名双栈（A+AAAA）；/domains 页面合并双栈行；开始新增阿里云 provider（app/aliyun_dns.py 已建、core.py 已分发，`_check_and_update_domain_aliyun` 待实现）。阿里云 AccessKey 与 ptrel.asia 域名信息见上文"阿里云云解析支持"章节。
- 2026-05-23: v2.0 重构完成，新增 FastAPI WebUI，支持多域名管理、用户认证、操作日志。
  - 核心逻辑从 ddns.py 提取到 app/core.py，供守护进程和 WebUI 共用
  - 配置从单域名扩展为多域名数组 [[domains]]
  - SQLite 存储操作日志和域名状态快照
  - 前端使用 Apple/macOS 风格毛玻璃 UI，支持暗黑模式
  - 两个 Supervisor 进程独立运行，互不阻塞
  - Nginx HTTPS 反向代理已配置，域名 ddns.ptrel.cc.cd
  - 已注册子域名 ddns.ptrel.cc.cd 并加入 DDNS 监控
  - 已添加"创建子域名"功能，可直接通过 dnshe API 注册子域名
  - 已添加 API 调用计数 + 速率限制保护（30次/小时）
  - 仪表盘添加 Chart.js 折线图展示 API 调用趋势
  - 超出限制时自动跳过，日志记录警告，不缓存积压
- 2026-05-24: v2.0.1 修复多个问题
  - 修复日志时间显示 UTC 而非北京时间的问题（app/core.py, app/models.py, ddns.py）
  - 修复 dnshe API update 接口 name 参数导致的 Record conflict 错误
  - 修复 maiapi 域名 record_name 配置为子域名前缀而非完整域名的问题
  - 修复 update_dns_record 中非数字 record_id 无法正确查询数字 id 的问题
  - 优化 doc/dnshe/api.md 文档，删除原始杂乱内容，补充实测发现的 API 问题
  - 编辑 DNS 记录时添加详细调试信息显示
  - 导航栏标题添加版本号 v2.0.1
  - 修复前端直接调用 dnshe API 的 CORS 问题，改为后端代理
  - 修复数据库文件权限导致的 readonly 错误
  - 修复 update_dns_record 完全放弃 dnshe update 接口（有 bug），改为先删后建
  - 域名管理表格添加列排序功能
  - 所有错误提示改为友好模态框弹窗
  - 添加网站 SVG 图标
  - 添加 Cache-Control 禁用浏览器缓存
  - 优化编辑响应速度，移除多余的 API 调用
