# 阿里云云解析接入指引（v2.2）

> ddns-ipv6 支持双 provider：**dnshe**（默认，原有）与 **阿里云云解析**（新增）。
> 本文档为接入阿里云的完整操作步骤，供后续使用。

## 一、前提条件

1. 已有阿里云账号，且在**云解析 DNS** 控制台添加了要管理的域名（NS 指向 `ns*.alidns.com`）
2. 已有 AccessKey（RAM 子账号，建议最小权限）
3. 当前托管域名：**`ptrel.asia`**（2026-08-15 实测，唯一）

## 二、配置步骤

### 1. 在 `config/env.toml` 添加 `[aliyun]` 段

```toml
[aliyun]
access_key_id = "LTAI...你的AK_ID"      # ⚠️ 实际值见服务器本地 config/env.toml（已 gitignore，勿提交）
access_key_secret = "你的AK_SECRET"      # ⚠️ 实际值见服务器本地 config/env.toml（已 gitignore，勿提交）
```

> ⚠️ **安全提醒**：AccessKey 是敏感凭据，只写入本地 `config/env.toml`（已被 .gitignore 忽略，不会进 git）。
> 严禁写入 `doc/`、`skill/`、`README.md` 等会被 git 跟踪的文件，否则 GitHub 推送保护会拦截。

### 2. 添加阿里云域名到 `[[domains]]`

```toml
[[domains]]
id = "asia-ipv6"            # 唯一标识
provider = "aliyun"         # 关键：走阿里云后端
subdomain_id = 0            # 阿里云不需要，占位
record_name = "ipv6.ptrel.asia"
record_type = "AAAA"
ttl = 600
enabled = true
```

### 3. 重启生效

```bash
supervisorctl restart ddns-ipv6
```

### 4. 验证

```bash
# 查权威（阿里云 NS）
dig @ns1.alidns.com ipv6.ptrel.asia AAAA
# 查公共
dig @114.114.114.114 ipv6.ptrel.asia AAAA
# 看守护进程日志
grep -E "aliyun|创建|更新" /main/log/app/ddns-ipv6.log | tail -20
```

## 三、阿里云 API 说明

| 操作 | Action | 说明 |
|------|--------|------|
| 查询记录 | `DescribeDomainRecords` | 参数 DomainName |
| 添加记录 | `AddDomainRecord` | RR/Type/Value/TTL/Line |
| 更新记录 | `UpdateDomainRecord` | **阿里云可用**（dnshe 的 update 有 bug，这里直接更新即可） |
| 删除记录 | `DeleteDomainRecord` | RecordId |

### 签名算法（HMAC-SHA1）
- 规范查询串：参数按字典序排序，RFC3986 编码，`&` 连接
- 待签字符串：`GET&/&<规范化串>`（URL 编码两次）
- 签名密钥：`<AccessKeySecret>&`
- 请求地址：`https://alidns.aliyuncs.com/`

### 记录名拆分
- `ipv6.ptrel.asia` → RR=`ipv6`，主域=`ptrel.asia`
- `ptrel.asia`（主域） → RR=`@`
- 代码：`app/aliyun_dns.py` 的 `split_domain()`

## 四、代码结构

```
app/aliyun_dns.py   # 新增：OpenAPI 封装（签名 + 4 个 CRUD）
app/core.py         # check_and_update_domain 按 provider 分发
                    #   → _check_and_update_domain_dnshe（原逻辑）
                    #   → _check_and_update_domain_aliyun（新增，待实现）
config/env.toml     # [aliyun] 段 + [[domains]].provider 字段
```

## 五、注意事项

- ⚠️ **`ptrel.cc.cd` 无法迁到阿里云**（NS 在 dnshe，免费域名），阿里云只管托管在阿里云的域名
- AccessKey 只用于云解析 DNS，若后续权限调整需谨慎
- 阿里云 API 频率限制远高于 dnshe（一般 100 QPS），无需担心 429
- 双 provider 并存：dnshe 域名不带 `provider` 字段或写 `"dnshe"`，互不影响
