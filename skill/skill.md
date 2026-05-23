# DDNS IPv6 项目 Skill

## 项目概述
DDNS IPv6 动态域名解析服务，通过 dnshe.com API 自动更新 AAAA 记录。
v2.0 新增 FastAPI WebUI 管理界面。

## 关键路径
- 项目根目录: `/main/app/github/ddns-ipv6`
- 配置文件: `config/env.toml`（已 gitignore）
- 配置模板: `config/template/env.template.toml`
- SQLite 数据库: `data/ddns.db`（已 gitignore）
- 日志目录: `/main/log/app/`

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

## ds 说
- 2026-05-23: v2.0 重构完成，新增 FastAPI WebUI，支持多域名管理、用户认证、操作日志。
  - 核心逻辑从 ddns.py 提取到 app/core.py，供守护进程和 WebUI 共用
  - 配置从单域名扩展为多域名数组 [[domains]]
  - SQLite 存储操作日志和域名状态快照
  - 前端使用 Tailwind CSS CDN + Alpine.js，零构建依赖
  - 两个 Supervisor 进程独立运行，互不阻塞
