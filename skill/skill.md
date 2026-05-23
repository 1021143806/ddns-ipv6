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
- `ddns-ipv6`: 后台检测守护进程 (`ddns_daemon.py`)
- `ddns-ipv6-webui`: Web 管理界面 (`app/webui.py`, 端口 5080)

## 部署命令
```bash
sudo bash deploy.sh
supervisorctl status ddns-ipv6 ddns-ipv6-webui
```

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

## API 文档
详见 [`doc/api/README.md`](doc/api/README.md)

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
