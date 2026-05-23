# DDNS IPv6

定时检测本机 IPv6 地址变化，通过 [dnshe.com](https://dnshe.com) API 自动更新 AAAA 记录，实现 IPv6 动态域名解析。

## 项目结构

```
ddns-ipv6/
├── config/
│   ├── env.toml              # 配置文件（含 API 凭证，已 .gitignore）
│   └── template/
│       └── env.template.toml # 配置模板（不含敏感信息）
├── ddns.py                    # 核心脚本：获取 IPv6 + 更新 DNS 记录
├── ddns-ipv6.conf             # Supervisor 配置文件
├── deploy.sh                  # 一键部署脚本
├── .gitignore
├── README.md
├── backup/                    # 备份目录
└── test/
    └── test_ddns.py           # 测试脚本
```

## 工作流程

```
Supervisor 启动 ddns.py
  ├── 读取 config/env.toml
  ├── ip -6 addr show 获取本机 global dynamic IPv6
  ├── 调用 dnshe API 查询当前 AAAA 记录
  ├── 对比变化 → 按需创建/更新/跳过
  └── sleep 300s → 循环
```

## 快速部署

```bash
# 1. 编辑配置文件
cp config/template/env.template.toml config/env.toml
vim config/env.toml

# 2. 一键部署
sudo bash deploy.sh

# 3. 查看状态
supervisorctl status ddns-ipv6

# 4. 查看日志
tail -f /main/log/app/ddns-ipv6.log
```

## 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `api.base_url` | dnshe API 地址 | `https://api005.dnshe.com/index.php` |
| `api.api_key` | API 密钥 | - |
| `api.api_secret` | API 密钥 | - |
| `dns.subdomain_id` | 子域名 ID | - |
| `dns.record_name` | 完整域名记录名 | - |
| `dns.record_type` | 记录类型 | `AAAA` |
| `dns.ttl` | TTL（秒） | `600` |
| `network.interface` | 网卡接口（留空自动检测） | `""` |
| `daemon.check_interval` | 检查间隔（秒） | `300` |

## 依赖

仅使用 Python 标准库（Python 3.11+），无需额外 pip 依赖：
- `subprocess` - 执行系统命令获取 IPv6
- `json` - 解析 API 响应
- `urllib.request` - HTTP 请求
- `tomllib` - 解析 TOML 配置

## 日志

日志输出到 stdout，由 Supervisor 管理：
- 日志文件：`/main/log/app/ddns-ipv6.log`
- 最大大小：1MB
- 自动轮转

## 手动运行

```bash
cd /main/app/github/ddns-ipv6
python3 ddns.py
```
