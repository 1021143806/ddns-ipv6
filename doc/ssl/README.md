# SSL 证书管理

## 证书信息

| 项目 | 说明 |
|------|------|
| 域名 | `*.ptrel.cc.cd`（通配符证书） |
| 颁发者 | Let's Encrypt（E8） |
| 有效期 | 3 个月（2026-05-23 ~ 2026-08-21） |
| 证书文件 | `/etc/nginx/ssl/ptrel_fullchain.crt` |
| 密钥文件 | `/etc/nginx/ssl/ptrel.key` |
| 申请工具 | acme.sh |

## 申请证书

### 1. 安装 acme.sh

```bash
curl https://get.acme.sh | sh
# 或
wget -O - https://get.acme.sh | sh
```

安装后重新加载 shell 或执行：
```bash
source ~/.bashrc
```

### 2. 设置 DNS API

acme.sh 支持多种 DNS 服务商的 API 来验证域名所有权。以 Cloudflare 为例：

```bash
# 设置 Cloudflare API 凭据
export CF_Token="your_cloudflare_api_token"
export CF_Zone_ID="your_zone_id"
```

### 3. 申请通配符证书

```bash
# DNS 验证方式（推荐，无需 80 端口）
acme.sh --issue --dns dns_cf -d '*.ptrel.cc.cd' -d ptrel.cc.cd

# 或 standalone 方式（需要 80 端口）
acme.sh --issue --standalone -d '*.ptrel.cc.cd' -d ptrel.cc.cd
```

### 4. 安装证书到 nginx

```bash
acme.sh --install-cert -d '*.ptrel.cc.cd' \
  --key-file /etc/nginx/ssl/ptrel.key \
  --fullchain-file /etc/nginx/ssl/ptrel_fullchain.crt \
  --reloadcmd "sudo nginx -s reload"
```

## 自动续期

acme.sh 安装后会默认添加定时任务自动续期。检查定时任务：

```bash
crontab -l
```

应该能看到类似：
```
0 0 * * * "/root/.acme.sh"/acme.sh --cron --home "/root/.acme.sh" > /dev/null
```

acme.sh 会在证书到期前自动续期，并通过 `--reloadcmd` 重载 nginx。

### 手动续期测试

```bash
acme.sh --renew -d '*.ptrel.cc.cd' --force
```

## 验证证书

```bash
# 查看证书详情
openssl x509 -in /etc/nginx/ssl/ptrel_fullchain.crt -text -noout | grep -E "Subject:|Issuer:|Not Before|Not After"

# 测试 SSL 连接
curl -I https://ddns.ptrel.cc.cd
```

## 注意事项

- Let's Encrypt 证书有效期为 90 天，acme.sh 会在到期前 30 天自动续期
- DNS 验证方式需要 DNS 服务商支持 API
- 如果更换 DNS 服务商，需要重新申请证书
- 证书文件权限建议设为 600（仅 root 可读）
