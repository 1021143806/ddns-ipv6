# DDNS IPv6 设计哲学

## 一、实用主义优先（Pragmatism First）

### 解决真实问题
项目源于作者 Ptrel 的实际需求轨迹：
1. 宿舍网络不支持 IPv6 → 用 frp + 阿里云服务器搭建公网访问
2. frp 对 HTTPS 协议支持不够好 → 引入 nginx 反向代理
3. 办理宽带后支持 IPv6 → 研究 DDNS 自动域名解析
4. 单域名脚本不够用 → 多域名支持 + WebUI 管理界面

**原则**：不为了技术而技术，每个功能都是真实需求的产物。

### 不追求完美，追求可用
- dnshe API 的 update 接口有 bug（name 参数会重复拼接域名如 `ddns.ptrel.cc.cd.ptrel.cc.cd`）
- 解决方案：**直接放弃 update 接口**，改为"先删后建"策略
- 虽然多了一次 API 调用，但保证了结果正确

**原则**：在不可靠的系统上构建可靠的应用，而不是抱怨上游。

### 渐进式增强
```
单域名脚本 (ddns.py)
  → 多域名支持
    → FastAPI WebUI 管理界面
      → 暗黑模式 + 毛玻璃 UI
        → 按钮加载动画 + 实时耗时
          → 流式调试日志 (SSE)
            → HTTPS 端口可配置
```

**原则**：每一步都是用户实际需求驱动，不提前过度设计。

---

## 二、防御性编程（Defensive Programming）

### 对上游 API 的不信任
dnshe API 存在多个已知问题：
- update 接口 name 参数会损坏记录
- 偶尔超时（`The read operation timed out`）
- 响应格式不稳定（有时返回 `records` 数组，有时在 `data` 字段）

**应对策略**：
```python
# 多种响应格式兼容
records = resp.get("records", resp.get("data", resp))
# 超时保护
urllib.request.urlopen(req, timeout=10)
# 速率限制
API_HOURLY_LIMIT = 300
```

### 脏数据自动清理
守护进程每次检查时，自动检测并清理 dnshe 产生的脏数据：
```python
r_name == f"{full_name}.{full_name.split('.', 1)[1]}"
# 如: ddns.ptrel.cc.cd.ptrel.cc.cd → 删除
```

### 双循环检测架构
```
快速检测 (10s): 只查本机 IP，不调 API，变化后立即更新
全量同步 (300s): 查远端记录，确保一致性，兜底
```

### 数据库保护
- SQLite WAL 模式提高并发
- 线程局部连接复用
- 权限问题处理

---

## 三、用户掌控感（User Empowerment）

### 所有操作可见
- **按钮加载动画**：点击后显示 `⏳ 操作名... (1,234ms)`，实时递增
- **流式调试日志**：编辑 DNS 记录时 SSE 推送每步操作
- **折线图 IP 变更标记**：鼠标 hover 显示历史 IP

### 知识透明
每个信息点都提供 ℹ️ 说明按钮：
- IPv4/IPv6 公网地址查询原理
- HTTPS 端口配置说明

### 灵活配置
- HTTPS 端口前端直接修改
- Nginx 配置、域名链接自动适配

---

## 四、美学一致性（Aesthetic Consistency）

### Apple/macOS 风格视觉系统
- **毛玻璃效果**：`backdrop-filter: blur(32px) saturate(140%)`
- **色彩语义化**：蓝=操作/IPv4、绿=成功/IPv6、橙=警告、红=错误
- **字体栈**：`-apple-system, 'SF Pro Display', 'PingFang SC'`
- **缓动曲线**：`cubic-bezier(0.25,0.1,0.25,1)`

### 交互细节
- 按钮按压效果 `scale(0.985)`
- 模态框入场动画
- 暗黑模式自动跟随系统

---

## 五、零依赖原则（Zero Dependency）

### 守护进程
- **纯 Python 标准库**，无需 pip install
- Python 3.11+ 即可运行

### WebUI
- 最小依赖：fastapi, uvicorn, jinja2, python-multipart, itsdangerous
- 前端零构建：Tailwind CSS + Chart.js 使用 CDN

### 部署
- 单文件部署，单进程运行
- Supervisor 一个 program 配置

---

## 六、渐进式复杂度（Progressive Complexity）

```
v1.0: 单域名 DDNS 脚本
v2.0: FastAPI WebUI + 多域名 + SQLite
v2.1: 双循环检测 + 流式日志 + HTTPS 端口配置
```

---

## 七、开发者体验（Developer Experience）

- 配置文件热加载，修改即时生效
- 所有 API 调用有详细日志
- 错误友好模态框提示

---

## 总结

> **在不可靠的现实中，构建可靠且美观的工具，让用户掌控一切。**

- 实用主义：不追求完美，解决真实问题
- 防御性：对上游 API 不信任，做好兜底
- 透明：所有操作可见，知识可查
- 美观：Apple 风格，细节到位
- 简洁：零依赖，单文件部署
- 渐进：从简单到复杂，逐步演进
