# DDNS IPv6

定时检测本机 IPv6 地址变化，通过 [dnshe.com](https://dnshe.com) API 自动更新 AAAA 记录，实现 IPv6 动态域名解析。

**v2.0 新增：现代化 WebUI 管理界面，支持多域名管理、远程添加解析。**

## 项目结构

```
ddns-ipv6/
├── app/                            # 应用代码
│   ├── core.py                     # 核心逻辑：IPv6 检测 + API 调用
│   ├── models.py                   # SQLite 数据层（日志 + 状态）
│   ├── auth.py                     # 用户认证（Session）
│   ├── webui.py                    # FastAPI Web 应用入口
│   ├── routes/
│   │   ├── api_domains.py          # 域名管理 REST API
│   │   ├── api_logs.py             # 日志查询 REST API
│   │   └── pages.py                # 页面路由
│   └── templates/                  # Jinja2 模板
│       ├── base.html               # 基础布局
│       ├── login.html              # 登录页
│       ├── dashboard.html          # 仪表盘
│       ├── domains.html            # 域名管理
│       └── logs.html               # 操作日志
├── config/
│   ├── env.toml                    # 配置文件（已 .gitignore）
│   ├── old/                        # 旧配置备份
│   └── template/
│       └── env.template.toml       # 配置模板
├── data/                           # SQLite 数据库（已 .gitignore）
├── ddns_daemon.py                  # 后台守护进程
├── ddns.py                         # 旧版脚本（保留兼容）
├── ddns-ipv6.conf                  # Supervisor: 守护进程
├── ddns-ipv6-webui.conf            # Supervisor: WebUI
├── deploy.sh                       # 一键部署脚本
├── test/
│   └── test_ddns.py                # 测试脚本
├── backup/
├── plans/
│   └── webui-architecture.md       # 架构设计文档
├── .gitignore
└── README.md
```

## 工作流程

```
Supervisor 管理两个进程:
  ┌─ ddns-ipv6 (ddns_daemon.py) ─────────────────────┐
  │  循环检测每个域名:                                  │
  │    ├── ip -6 addr show 获取本机 IPv6               │
  │    ├── 调用 dnshe API 查询/创建/更新 AAAA 记录      │
  │    ├── 写入 SQLite 日志和状态                       │
  │    └── sleep → 下一轮                               │
  └────────────────────────────────────────────────────┘
  ┌─ ddns-ipv6-webui (FastAPI :5080) ─────────────────┐
  │  提供 Web 管理界面:                                 │
  │    ├── 登录认证                                     │
  │    ├── 仪表盘（状态概览）                            │
  │    ├── 域名增删改查                                 │
  │    ├── 手动触发更新                                 │
  │    └── 操作日志查看                                 │
  └────────────────────────────────────────────────────┘
```

## 快速部署

```bash
# 1. 编辑配置文件
cp config/template/env.template.toml config/env.toml
vim config/env.toml

# 2. 一键部署（含依赖安装）
sudo bash deploy.sh

# 3. 查看状态
supervisorctl status ddns-ipv6 ddns-ipv6-webui

# 4. 访问 WebUI
# http://<服务器IP>:5080
# 默认用户名: admin  密码: admin123

# 5. 查看日志
tail -f /main/log/app/ddns-ipv6.log        # 守护进程日志
tail -f /main/log/app/ddns-ipv6-webui.log  # WebUI 日志
```

## 配置说明

### Web 配置 `[web]`

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `host` | 监听地址 | `0.0.0.0` |
| `port` | 监听端口 | `5080` |
| `username` | 登录用户名 | `admin` |
| `password` | 登录密码 | `admin123` |
| `secret_key` | Session 签名密钥 | - |

### API 配置 `[api]`

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `base_url` | dnshe API 地址 | `https://api005.dnshe.com/index.php` |
| `api_key` | API 密钥 | - |
| `api_secret` | API 密钥 | - |

### 守护进程 `[daemon]`

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `check_interval` | 全局检查间隔（秒） | `300` |

### 网络 `[network]`

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `interface` | 网卡接口（留空自动检测） | `""` |

### 域名配置 `[[domains]]`（可多个）

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `id` | 唯一标识 | 自动生成 |
| `subdomain_id` | 子域名 ID | - |
| `record_name` | 完整域名记录名 | - |
| `record_type` | 记录类型 | `AAAA` |
| `ttl` | TTL（秒） | `600` |
| `enabled` | 是否启用 | `true` |
| `check_interval` | 自定义检查间隔（可选） | - |

## 依赖

### 守护进程
- Python 3.11+ 标准库（`tomllib`, `subprocess`, `json`, `urllib`）

### WebUI（新增）
- `fastapi` - Web 框架
- `uvicorn` - ASGI 服务器
- `jinja2` - 模板引擎
- `python-multipart` - 表单解析
- `itsdangerous` - Session 签名

## 手动运行

```bash
cd /main/app/github/ddns-ipv6

# 守护进程
python3 ddns_daemon.py

# WebUI（开发模式）
uvicorn app.webui:app --host 0.0.0.0 --port 5080 --reload
```
