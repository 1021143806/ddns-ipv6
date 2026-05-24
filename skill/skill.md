# DDNS IPv6 项目 Skill

## 项目概述
DDNS IPv6 动态域名解析服务，通过 dnshe.com API 自动更新 AAAA 记录。
v2.0 新增 FastAPI WebUI 管理界面，支持多域名管理、用户认证、操作日志。

## 关键路径
- 项目根目录: `/main/app/github/ddns-ipv6`
- 配置文件: `config/env.toml`（已 gitignore）
- 配置模板: `config/template/env.template.toml`
- SQLite 数据库: `data/ddns.db`（已 gitignore）
- 日志目录: `/main/log/app/`
- API 文档: `doc/api/README.md`

## Supervisor 进程
守护进程和 WebUI 合并为同一个进程（WebUI 在子线程中运行）：
- `ddns-ipv6`: 后台检测守护进程 + WebUI 管理界面（`ddns_daemon.py`，端口 5080）

### 配置文件
- 项目内模板: [`ddns-ipv6.conf`](ddns-ipv6.conf)（单个 program）
- 部署目标: `/main/server/supervisor/ddns-ipv6.conf`

### 部署流程
```bash
# 1. 复制配置文件到 supervisor 目录
sudo cp ddns-ipv6.conf /main/server/supervisor/

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
- dnshe API 限制：**30 次/小时**
- 超出限制时：跳过本次调用，等待下一轮（不缓存，避免积压）
- 每次 API 调用自动记录到 `api_call_log` 表
- 仪表盘展示折线图 + 实时速率状态

## ds 说
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
