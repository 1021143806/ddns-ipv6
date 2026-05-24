# DDNS IPv6



定时检测本机 IPv6 地址变化，通过 [dnshe.com](https://dnshe.com) API 自动更新 AAAA 记录，实现 IPv6 动态域名解析。

**v2.0 新增：现代化 WebUI 管理界面，支持多域名管理、远程添加解析。**

## 作者说

这个项目的目的是为了让自己的设备接入公网，作者 Ptrel 只是个住寝室的小员工，宿舍的网络不支持 ipv6，因此最初通过 frp + 阿里云的服务器搭建了一个让自己电脑的服务开放到公网的这么一个功能。

但是，这并不稳定，而且无法做到 https 网站的搭建，因为 frp 对一些协议的支持不够好，所以不得不使用 nginx 作为对外代理。

这段时间第一次办理了宽带，支持了 ipv6，所以研究了下 ipv6 自带公网，只是需要一个自动域名解析防止断联。阿里云的服务器是一个固定的 ipv4 地址，所以不会丢，但是自己设备接入 ipv6 地址是可能出现自动更新的，现在需要解决这个问题。

如何解决，使用 ddns ，流程简单说就是

1. 本地计算机定时获取自身的 ipv6 地址
2. 获取域名解析网站当前的解析
3. 如果域名解析网站中配置的 ipv6 地址和本地不一样了，那么通过 api 接口进行修改，这样就能保持动态更新。

一般一个网站的搭建需要

1. 域名解析
2. 证书申请

域名解析使用的 dnshe ，免费的域名申请网站
证书申请方法可以见 doc/ssl/README.md

## 关于如何获取公网

首先你的宽带需要是拨号模式
拨号模式相当于你的电脑在裸奔，会被自动分配到 ipv4 地址，这同样是动态的，需要 ddns ，同时在你的路由器中需要 端口转发配置中打开 DMZ ，输入你的服务器的 ipv4 地址，DMZ 将会将所有端口转发到公网 ip 对应的 IP 地址。

ipv6 则不需要额外配置，只需要本机即可，前提依然是宽带需要拨号模式。

- 拨号模式（直连公网）

  获取的是公网 IP：电脑直接暴露在互联网上。

  端口管控：极弱，风险极高。电脑上所有开放端口（如135、445等高危端口）都能被公网直接扫描和攻击，安全全靠 Windows 自带的防火墙，极易被勒索病毒入侵。

- 路由模式（NAT 隔离）

  获取的是内网 IP：路由器形成了一道天然屏障。

  端口管控：强，默认全封闭。外网无法直接访问内网设备。只有当你主动在路由器上设置“端口转发”或“DMZ 主机”，外部才能访问指定端口，控制权完全在你手里。

ipv6 的优势就是你不需要任何配置的情况只要能访问互联网的情况下就可以 ping 通，联系网络供应商（如电信）修改为拨号模式，端口访问就不会被拦截，可以直接使用以及访问。配合 ddns 和域名就可以完成公网访问。

如何改为拨号模式：装宽带时直接要求使用拨号模式且需要宽带账号密码即可。如果已安装完，直接联系供应商远程修改为拨号模式。

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
Supervisor 管理进程:
  ┌─ ddns-ipv6 (ddns_daemon.py) ──────────────────────────┐
  │  循环检测每个域名:                                      │
  │    ├── ip -6 addr show 获取本机 IPv6                   │
  │    ├── 调用 dnshe API 查询/创建/更新 AAAA 记录          │
  │    ├── 自动清理脏数据（name 重复拼接的记录）             │
  │    ├── 写入 SQLite 日志和状态                           │
  │    └── sleep → 下一轮                                   │
  └────────────────────────────────────────────────────────┘
  ┌─ ddns-ipv6-webui (FastAPI :5080) ─────────────────────┐
  │  提供 Web 管理界面:                                     │
  │    ├── 登录认证                                         │
  │    ├── 仪表盘（状态概览）                                │
  │    ├── 域名增删改查                                     │
  │    ├── 手动触发更新                                     │
  │    └── 操作日志查看                                     │
  └────────────────────────────────────────────────────────┘
```

### ⚠️ DNS 缓存说明

DDNS 更新的是 dnshe **系统内部**的 DNS 记录（通过 API 查询可确认已更新），但 **公共 DNS 缓存**（如 114.114.114.114）需要时间同步：

| 步骤 | 耗时 | 说明 |
|------|------|------|
| ① 检测到 IP 变化 | 即时 | 守护进程每轮检测 |
| ② 更新 dnshe 记录 | ~1-2s | API 调用成功 |
| ③ dnshe 权威 DNS 同步 | 即时 | `dig @ns7.dnshe.com` 可查 |
| ④ 公共 DNS 缓存更新 | **~10 分钟** | 取决于 TTL 设置（默认 600s） |

> 💡 更新后立即通过 `dig @8.8.8.8 域名 AAAA` 或 `dig @ns7.dnshe.com 域名 AAAA` 验证。

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
