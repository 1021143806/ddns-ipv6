https://my.dnshe.com/knowledgebase/13/DNSHE-Free-Domain-API-User-Guide-V2.0.html?language=chinese&autolang=1

帮助中心
客户中心  帮助中心  免费域名服务API使用文档  DNSHE免费域名API使用文档（V2.0)
  分类
3
免费域名服务API使用文档
DNSHE免费域名API使用文档（V2.0)
DNSHE免费域名API使用文档（V2.0)

基本信息

API地址：`https://api005.dnshe.com/index.php?m=domain_hub`

认证方式：API Key + API Secret

支持格式：JSON

速率限制：默认 30 请求/分钟

认证：获取API密钥

登录客户区
进入"免费域名管理"页面
在左侧导航栏找到"API管理"
点击"创建API密钥"
认证方式

方式1：HTTP Header（推荐）

bash
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

方式2：URL/Body 参数（已禁用）

出于安全原因，`api_key` / `api_secret` 不再支持通过 URL Query 或请求体传递。请仅使用 `X-API-Key` 和 `X-API-Secret` 请求头认证。

 

API端点

子域名管理
1.1 列出子域名

端点：`subdomains`  

操作：`list`  

方法：`GET`

查询参数：

参数

类型

必填

默认值

说明

page

integer

否

1

页码（从1开始）

per_page

integer

否

200

每页数量（1-500）

include_total

boolean

否

false

是否返回总数（大数据量时较慢）

search

string

否

-

搜索关键词（匹配subdomain或rootdomain）

rootdomain

string

否

-

按根域名过滤

status

string

否

-

按状态过滤（active/suspended/expired）

created_from

string

否

-

创建时间起始（YYYY-MM-DD）

created_to

string

否

-

创建时间结束（YYYY-MM-DD）

sort_by

string

否

id

排序字段（id/created_at/updated_at/expires_at/subdomain）

sort_dir

string

否

desc

排序方向（asc/desc）

fields

string

否

all

返回字段（逗号分隔）。可选：id,subdomain,rootdomain,full_domain,status,created_at,updated_at,expires_at,never_expires,cloudflare_zone_id,provider_account_id；自定义 fields 时会自动补充 id

基础请求示例：

bash
# 默认获取第1页（200条）
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

分页请求示例：

bash
# 获取第1页（每页100条）
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list&page=1&per_page=100" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

# 获取第2页并返回总数
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list&page=2&per_page=100&include_total=1" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

搜索和过滤示例：

bash
# 搜索包含"test"的域名
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list&search=test" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

# 只查看example.com的域名
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list&rootdomain=example.com" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

# 查看已暂停的域名
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list&status=suspended" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

# 查看2025年1月创建的域名
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list&created_from=2025-01-01&created_to=2025-01-31" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

# 按过期时间升序排列
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list&sort_by=expires_at&sort_dir=asc" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

# 组合查询：搜索test开头的active状态域名，按创建时间倒序，每页50条
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list&search=test&status=active&sort_by=created_at&sort_dir=desc&per_page=50" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

# 只返回ID和域名字段（减少数据传输）
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=list&fields=id,subdomain,rootdomain,status" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

基础响应示例：

json
{
  "success": true,
  "count": 2,
  "subdomains": [
    {
      "id": 1,
      "subdomain": "test",
      "rootdomain": "example.com",
      "full_domain": "test.example.com",
      "status": "active",
      "created_at": "2025-10-19 10:00:00",
      "updated_at": "2025-10-19 10:00:00"
    },
    {
      "id": 2,
      "subdomain": "api",
      "rootdomain": "example.com",
      "full_domain": "api.example.com",
      "status": "active",
      "created_at": "2025-10-19 11:00:00",
      "updated_at": "2025-10-19 11:00:00"
    }
  ]
}

分页响应示例：

json
{
  "success": true,
  "count": 100,
  "subdomains": [
    {
      "id": 201,
      "subdomain": "app201",
      "rootdomain": "example.com",
      "full_domain": "app201.example.com",
      "status": "active",
      "created_at": "2025-10-19 10:00:00",
      "updated_at": "2025-10-19 10:00:00"
    }
    // ... 99 more items
  ],
  "pagination": {
    "page": 2,
    "per_page": 100,
    "has_more": true,
    "next_page": 3,
    "prev_page": 1,
    "total": 12500
  }
}

性能优化建议：

默认每页200条，建议根据需求调整`per_page`（推荐50-100）
`include_total=1`会执行COUNT查询，数据量大时可能较慢，仅在必要时使用
通过`pagination.has_more`判断是否有下一页，比依赖`total`更高效
使用`fields`参数可以显著减少数据传输量
最大`per_page=500`，超过会自动限制为500
对于1万+域名，建议使用搜索和过滤功能精确定位目标域名
 

1.2 注册子域名

端点：`subdomains`  

操作：`register`  

方法：`POST`

请求参数：

参数

类型

必填

说明

subdomain

string

是

子域名前缀

rootdomain

string

是

根域名

请求示例：

bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=register" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{
    "subdomain": "myapp",
    "rootdomain": "example.com"
  }'

响应示例：

json
{
  "success": true,
  "message": "Subdomain registered successfully",
  "subdomain_id": 3,
  "full_domain": "myapp.example.com"
}

 

1.3 获取子域名详情

端点：`subdomains`  

操作：`get`  

方法：`GET`

请求参数：

参数

类型

必填

说明

subdomain_id

integer

是

子域名ID

请求示例：

bash
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=get&subdomain_id=1" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

响应示例：

json
{
  "success": true,
  "subdomain": {
    "id": 1,
    "subdomain": "test",
    "rootdomain": "example.com",
    "full_domain": "test.example.com",
    "status": "active",
    "created_at": "2025-10-19 10:00:00",
    "updated_at": "2025-10-19 10:00:00"
  },
  "dns_records": [
    {
      "id": 1,
      "name": "test.example.com",
      "type": "A",
      "content": "192.168.1.1",
      "ttl": 600,
      "priority": null,
      "status": "active",
      "created_at": "2025-10-19 10:05:00"
    }
  ],
  "dns_count": 1
}

 

1.4 删除子域名

端点：`subdomains`  

操作：`delete`  

方法：`POST` 或 `DELETE`

请求参数：

参数

类型

必填

说明

subdomain_id

integer

是

子域名ID

请求示例：

bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=delete" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{
    "subdomain_id": 1
  }'

响应示例：

json
{
  "success": true,
  "message": "Subdomain deleted successfully",
  "subdomain_id": 1,
  "full_domain": "test.example.com",
  "dns_records_deleted": 4
}

 

1.5 续期子域名

端点：`subdomains`

操作：`renew`

方法：`POST` 或 `PUT`

请求参数：

参数

类型

必填

说明

subdomain_id

integer

是

子域名ID

请求示例：

bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=subdomains&action=renew" \
-H "X-API-Key: cfsd_xxxxxxxxxx" \
-H "X-API-Secret: yyyyyyyyyyyy" \
-H "Content-Type: application/json" \
-d '{
  "subdomain_id": 3
}'

响应示例：

json
{
  "success": true,
  "message": "Subdomain renewed successfully (charged 9.90 credit)",
  "subdomain_id": 3,
  "subdomain": "myapp",
  "previous_expires_at": "2025-05-01 00:00:00",
  "new_expires_at": "2026-05-01 00:00:00",
  "renewed_at": "2025-04-10 12:34:56",
  "never_expires": 0,
  "status": "active",
  "remaining_days": 366,
  "charged_amount": 9.9
}

说明：

`charged_amount` 表示本次续期从用户账户余额中扣除的金额。免费续期或扣费金额为 0 时，该字段值为 `0`。
可能的错误：

`403 renewal disabled`：后台未配置有效的注册年限。
`422 renewal not yet available`：尚未进入免费续期窗口（同时返回 `error_code=renewal_not_yet_available` 与剩余时间字段）。
`403 redemption period requires administrator`：域名处于赎回期且后台配置为人工处理。
`403 renewal window expired`：已超过续期宽限期。
`402 insufficient balance for redemption renewal`：赎回期设置为自动扣费，但账户余额不足。
`404 subdomain not found`：找不到对应子域名或不属于当前 API Key。
 

DNS记录管理
2.1 列出DNS记录

端点：`dns_records`  

操作：`list`  

方法：`GET`

请求参数：

参数

类型

必填

说明

subdomain_id

integer

是

子域名ID

请求示例：

bash
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=dns_records&action=list&subdomain_id=1" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

响应示例：

json
{
  "success": true,
  "count": 2,
  "records": [
    {
      "id": 1,
      "record_id": "5a0ce6c4d1d4c71bc5e60a2a2a0e4997",
      "name": "test.example.com",
      "type": "A",
      "content": "192.168.1.1",
      "ttl": 600,
      "priority": null,
      "line": null,
      "proxied": false,
      "status": "active",
      "created_at": "2025-10-19 10:05:00",
      "updated_at": "2025-10-19 10:05:00"
    },
    {
      "id": 2,
      "name": "www.test.example.com",
      "type": "CNAME",
      "content": "test.example.com",
      "ttl": 600,
      "priority": null,
      "proxied": false,
      "status": "active",
      "created_at": "2025-10-19 10:10:00"
    }
  ]
}

 

提示：列表同时返回模块内部 `id` 和云解析服务商 `record_id`。`update`/`delete` 可使用任意一个字段定位记录（推荐优先使用 `id`）。

 

2.2 创建DNS记录

端点：`dns_records`  

操作：`create`  

方法：`POST`

请求参数：

参数

类型

必填

说明

subdomain_id

integer

是

子域名ID

type

string

是

记录类型（A/AAAA/CNAME/MX/TXT/NS/SRV/CAA）

name

string

否

记录名称（`@` 或留空=当前子域本身；支持完整域名）

content

string

条件必填

记录值（SRV/CAA 可由结构化参数自动组装）

ttl

integer

否

TTL值（默认600）

priority

integer

否

MX优先级（MX默认10）/SRV优先级（默认0）

line

string

否

解析线路（us.ci/cn.mt可用，其他域名自动忽略）

record_weight / weight

integer

否

SRV 权重

record_port / port

integer

否

SRV 端口（1-65535）

record_target / target

string

否

SRV 目标主机

caa_flag

integer

否

CAA flag（默认0）

caa_tag

string

否

CAA tag（默认 issue）

caa_value

string

否

CAA value

 

说明：DNS 管理（`disable_ns_management`）为禁用状态，则 `NS` 类型写入会被拒绝。

请求示例：

bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=dns_records&action=create" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{
    "subdomain_id": 1,
    "type": "A",
    "content": "192.168.1.100",
    "ttl": 600
  }'

响应示例：

json
{
  "success": true,
  "message": "DNS record created successfully",
  "id": 3,
  "record_id": "5a0ce6c4d1d4c71bc5e60a2a2a0e4997"
}

 

2.3 更新DNS记录

端点：`dns_records`  

操作：`update`  

方法：`POST` 或 `PUT` 或 `PATCH`

请求参数：

参数

类型

必填

说明

record_id

string

否

记录定位ID（可传模块 `id` 或供应商 `record_id`）

id

integer

否

模块内部记录ID（推荐）

type

string

否

新类型（A/AAAA/CNAME/MX/TXT/NS/SRV/CAA）

name

string

否

新名称（`@` 或留空=当前子域本身）

content

string

否

新记录值

ttl

integer

否

新TTL值

priority

integer

否

MX/SRV优先级

line

string

否

解析线路

record_weight / weight

integer

否

SRV 权重

record_port / port

integer

否

SRV 端口

record_target / target

string

否

SRV 目标主机

caa_flag / caa_tag / caa_value

mixed

否

CAA结构化参数

 

至少提供 `record_id` 或 `id` 其中之一。

请求示例：

bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=dns_records&action=update" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "type": "A",
    "content": "192.168.1.200",
    "ttl": 600
  }'

响应示例：

json
{
  "success": true,
  "message": "DNS record updated successfully",
  "id": 1,
  "record_id": "5a0ce6c4d1d4c71bc5e60a2a2a0e4997"
}

 

2.4 删除DNS记录

端点：`dns_records`  

操作：`delete`

方法：`POST` 或 `DELETE`

请求参数：

参数

类型

必填

说明

record_id

string

否

云解析服务商返回的记录ID。若提供，将首先按该字段匹配。

id

integer

否

模块内部记录ID，可直接使用 `list` 接口返回的 `id` 值。

 

至少提供 `record_id` 或 `id` 其中之一。

请求示例：

bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=dns_records&action=delete" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1
  }'

 

bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=dns_records&action=delete" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "5a0ce6c4d1d4c71bc5e60a2a2a0e4997"
  }'

响应示例：

json
{
  "success": true,
  "message": "DNS record deleted successfully"
}

 

API密钥管理
3.1 列出API密钥

端点：`keys`  

操作：`list`  

方法：`GET`

请求示例：

bash
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=keys&action=list" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

响应示例：

json
{
  "success": true,
  "count": 2,
  "keys": [
    {
      "id": 1,
      "key_name": "生产环境密钥",
      "api_key": "cfsd_xxxxxxxxxx",
      "status": "active",
      "request_count": 1523,
      "last_used_at": "2025-10-19 15:30:00",
      "created_at": "2025-10-19 10:00:00"
    },
    {
       "id": 2,
"key_name": "测试环境密钥",
"api_key": "cfsd_yyyyyyyyyy",
"status": "active",
"request_count": 45,
"last_used_at": "2025-10-19 14:00:00",
"created_at": "2025-10-19 11:00:00"
}
]
}

DNSHE 免费域名 API 文档

3.2 创建API密钥

端点：`keys`

操作：`create`  

方法：`POST`

请求参数：

参数

类型

必填

说明

key_name

string

是

密钥名称

ip_whitelist

string

否

IP白名单（逗号/换行/分号分隔，支持单IP或CIDR；需后台开启“启用API IP白名单”）

请求示例：

bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=keys&action=create" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{
    "key_name": "新密钥",
    "ip_whitelist": "192.168.1.1,192.168.1.2"
  }'

响应示例：

json
{
  "success": true,
  "message": "API key created successfully",
  "api_key": "cfsd_zzzzzzzzzz",
  "api_secret": "aaaaaaaaaaaaaaaa",
  "warning": "Please save the api_secret, it will not be shown again"
}

 

重要： `api_secret` 只显示一次，请妥善保存！

 

3.3 删除API密钥

端点：`keys`  

操作：`delete`  

方法：`POST` 或 `DELETE`

请求参数：

参数

类型

必填

说明

key_id

integer

是

密钥ID

请求示例：

bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=keys&action=delete" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{
    "key_id": 2
  }'

响应示例：

json
{
  "success": true,
  "message": "API key deleted successfully"
}

 

3.4 重新生成API密钥

端点：`keys`  

操作：`regenerate`  

方法：`POST`

请求参数：

参数

类型

必填

说明

key_id

integer

是

密钥ID

请求示例：

bash
curl -X POST "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=keys&action=regenerate" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy" \
  -H "Content-Type: application/json" \
  -d '{
    "key_id": 1
  }'

响应示例：

json
{
  "success": true,
  "message": "API secret regenerated successfully",
  "api_key": "cfsd_xxxxxxxxxx",
  "api_secret": "new_secret_here",
  "warning": "Please save the new api_secret, it will not be shown again"
}

 

配额查询
4.1 查询配额

端点：`quota`  

方法：`GET`

请求示例：

bash
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=quota" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

响应示例：

json
{
  "success": true,
  "quota": {
    "used": 3,
    "base": 5,
    "invite_bonus": 2,
    "total": 7,
    "available": 4
  }
}

 

错误代码与统一错误结构

从当前版本开始，所有 API 错误响应统一为以下结构：

json
{
  "success": false,
  "error_code": "auth_invalid_credentials",
  "message": "Invalid API key",
  "details": {
    "request_id": "optional"
  },
  "error": "Invalid API key"
}

字段说明：

字段

类型

说明

success

boolean

固定为 false

error_code

string

稳定错误码（建议业务侧按此字段处理）

message

string

人类可读错误描述

details

object

可选，附加上下文（如 limit/remaining/reset_at）

error

string

兼容旧版客户端（等同 message）

常见错误码：

error_code

HTTP状态码

说明

bad_request

400

请求参数错误

auth_invalid_credentials

401

API Key/Secret 无效或缺失

auth_ip_not_allowed

403

请求 IP 不在白名单

api_access_disabled

403

后台关闭了 API 访问

not_found / subdomain_not_found / dns_record_not_found

404

资源不存在

quota_exceeded

429

额度不足

rate_limit_exceeded

429

请求频率超限

provider_operation_failed

502

上游 DNS 提供商执行失败

internal_error

500

服务内部异常

 

速率限制

默认限制： 60 请求/分钟

响应头：

- 请求响应中会包含速率限制信息

超限响应示例：

json
{
  "success": false,
  "error_code": "rate_limit_exceeded",
  "message": "Rate limit exceeded",
  "details": {
    "limit": 60,
    "remaining": 0,
    "reset_at": "2025-10-19 15:31:00"
  },
  "error": "Rate limit exceeded"
}

 

SDK示例

PHP示例

php
<?php
class CloudflareSubdomainAPI {
    private $baseUrl;
    private $apiKey;
    private $apiSecret;
    
    public function __construct($baseUrl, $apiKey, $apiSecret) {
        $this->baseUrl = rtrim($baseUrl, '/');
        $this->apiKey = $apiKey;
        $this->apiSecret = $apiSecret;
    }
    
    private function request($endpoint, $action, $method = 'GET', $data = []) {
        $url = $this->baseUrl . '?m=domain_hub&endpoint=' . $endpoint . '&action=' . $action;
        
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            'X-API-Key: ' . $this->apiKey,
            'X-API-Secret: ' . $this->apiSecret,
            'Content-Type: application/json'
        ]);
        
        if ($method === 'POST') {
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        }
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        return json_decode($response, true);
    }
    
    // 列出子域名
    public function listSubdomains() {
        return $this->request('subdomains', 'list', 'GET');
    }
    
    // 注册子域名
    public function registerSubdomain($subdomain, $rootdomain) {
        return $this->request('subdomains', 'register', 'POST', [
            'subdomain' => $subdomain,
            'rootdomain' => $rootdomain
        ]);
    }
    
    // 创建DNS记录
    public function createDnsRecord($subdomainId, $type, $content, $ttl = 600) {
        return $this->request('dns_records', 'create', 'POST', [
            'subdomain_id' => $subdomainId,
            'type' => $type,
            'content' => $content,
            'ttl' => $ttl
        ]);
    }
}

// 使用示例
$api = new CloudflareSubdomainAPI(
    'https://api005.dnshe.com/index.php',
    'cfsd_xxxxxxxxxx',
    'yyyyyyyyyyyy'
);

// 列出子域名
$result = $api->listSubdomains();
print_r($result);

// 注册新子域名
$result = $api->registerSubdomain('myapp', 'example.com');
print_r($result);

Python示例

python
import requests
import json

class CloudflareSubdomainAPI:
    def __init__(self, base_url, api_key, api_secret):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.api_secret = api_secret
        self.headers = {
            'X-API-Key': api_key,
            'X-API-Secret': api_secret,
            'Content-Type': 'application/json'
        }
    
    def request(self, endpoint, action, method='GET', data=None):
        url = f"{self.base_url}?m=domain_hub&endpoint={endpoint}&action={action}"
        
        if method == 'GET':
            response = requests.get(url, headers=self.headers)
        else:
            response = requests.post(url, headers=self.headers, json=data)
        
        return response.json()
    
    def list_subdomains(self):
        return self.request('subdomains', 'list', 'GET')
    
    def register_subdomain(self, subdomain, rootdomain):
        return self.request('subdomains', 'register', 'POST', {
            'subdomain': subdomain,
            'rootdomain': rootdomain
        })
    
    def create_dns_record(self, subdomain_id, record_type, content, ttl=600):
        return self.request('dns_records', 'create', 'POST', {
            'subdomain_id': subdomain_id,
            'type': record_type,
            'content': content,
            'ttl': ttl
        })

# 使用示例
api = CloudflareSubdomainAPI(
    'https://api005.dnshe.com/index.php',
    'cfsd_xxxxxxxxxx',
    'yyyyyyyyyyyy'
)

# 列出子域名
result = api.list_subdomains()
print(result)

# 注册新子域名
result = api.register_subdomain('myapp', 'example.com')
print(result)

JavaScript示例

javascript
class CloudflareSubdomainAPI {
    constructor(baseUrl, apiKey, apiSecret) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiKey = apiKey;
        this.apiSecret = apiSecret;
    }
    
    async request(endpoint, action, method = 'GET', data = null) {
        const url = `${this.baseUrl}?m=domain_hub&endpoint=${endpoint}&action=${action}`;
        
        const options = {
            method: method,
            headers: {
                'X-API-Key': this.apiKey,
                'X-API-Secret': this.apiSecret,
                'Content-Type': 'application/json'
            }
        };
        
        if (method === 'POST' && data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        return await response.json();
    }
    
    async listSubdomains() {
        return await this.request('subdomains', 'list', 'GET');
    }
    
    async registerSubdomain(subdomain, rootdomain) {
        return await this.request('subdomains', 'register', 'POST', {
            subdomain: subdomain,
            rootdomain: rootdomain
        });
    }
    
    async createDnsRecord(subdomainId, type, content, ttl = 600) {
        return await this.request('dns_records', 'create', 'POST', {
            subdomain_id: subdomainId,
            type: type,
            content: content,
            ttl: ttl
        });
    }
}

// 使用示例
const api = new CloudflareSubdomainAPI(
    'https://api005.dnshe.com/index.php',
    'cfsd_xxxxxxxxxx',
    'yyyyyyyyyyyy'
);

// 列出子域名
api.listSubdomains().then(result => {
    console.log(result);
});

// 注册新子域名
api.registerSubdomain('myapp', 'example.com').then(result => {
    console.log(result);
});

 

WHOIS 查询（公开接口）
该接口用于对外查询 WHOIS 信息，支持系统内二级域名与外部域名。默认无需 API Key，系统会基于访问 IP 做速率限制（默认 30 次/分钟），如果系统开启强制api验证要求 则必须使用 API Key查询。

- 端点： `whois`

- 方法： `GET`

- 参数：

参数

类型

必填

说明

domain

string

是

完整子域名，例如 `foo.example.com`

请求示例（公共模式）：

bash
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=whois&domain=foo.example.com"

请求示例（要求 API Key 时）：

bash
curl -X GET "https://api005.dnshe.com/index.php?m=domain_hub&endpoint=whois&domain=foo.example.com" \
  -H "X-API-Key: cfsd_xxxxxxxxxx" \
  -H "X-API-Secret: yyyyyyyyyyyy"

响应示例（已注册）：

json
{
  "success": true,
  "domain": "foo.example.com",
  "status": "active",
  "registered_at": "2025-01-10 08:30:00",
  "expires_at": "2026-01-10 08:30:00",
  "registrant_email": "whois@example.com",
  "nameservers": [
    "ns1.example.net",
    "ns2.example.net"
  ],
  "rate_limit": {
    "limit": 2,
    "remaining": 1,
    "reset_at": "2025-01-10 08:31:00"
  }
}

响应示例（未注册）：

json
{
  "success": true,
  "domain": "foo.example.com",
  "registered": false,
  "status": "unregistered",
  "message": "domain not registered"
}

 

说明：

- `registrant_email` 的内容取决于是否开启域名隐私保护。

- 同时会返回 `name_servers` 字段，内容与 `nameservers` 一致，便于不同 SDK 兼容。

- 未注册域名会返回 `registered=false` 与 `status=unregistered`，同时附带查询的完整域名。

- 当未启用 API Key 模式时，返回体中的 `rate_limit` 字段展示当前 IP 的剩余额度。

<!-- [if gte mso 9]> <w:LsdException Locked="false" Prior

 API使用文档, DNSHE Free Domain API User Guide (V2.0), DNSHE免费域名API使用文档（V2.0), api, 使用, 文档, v2.0, v2 3 用户发现这个很有用
