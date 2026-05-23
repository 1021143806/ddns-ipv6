#!/bin/bash
# DDNS IPv6 一键部署脚本
set -e

PROJECT_DIR="/main/app/github/ddns-ipv6"
VENV_DIR="$PROJECT_DIR/venv"
SUPERVISOR_CONF="/main/server/supervisor/conf.d/ddns-ipv6.conf"
SUPERVISOR_CONF_SRC="$PROJECT_DIR/ddns-ipv6.conf"

echo "========================================="
echo "  DDNS IPv6 部署脚本"
echo "========================================="

# 1. 创建 venv（如不存在）
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/5] 创建 Python 虚拟环境..."
    python3 -m venv "$VENV_DIR"
    echo "  ✓ venv 创建完成"
else
    echo "[1/5] venv 已存在，跳过"
fi

# 2. 复制 env.template.toml → env.toml（如 env.toml 不存在）
if [ ! -f "$PROJECT_DIR/config/env.toml" ]; then
    echo "[2/5] 创建配置文件..."
    cp "$PROJECT_DIR/config/template/env.template.toml" "$PROJECT_DIR/config/env.toml"
    echo "  ⚠ 请编辑 config/env.toml 填入实际 API 密钥和域名信息！"
else
    echo "[2/5] 配置文件已存在，跳过"
fi

# 3. 复制 supervisor 配置
echo "[3/5] 部署 supervisor 配置..."
if [ -f "$SUPERVISOR_CONF_SRC" ]; then
    cp "$SUPERVISOR_CONF_SRC" "$SUPERVISOR_CONF"
    echo "  ✓ supervisor 配置已复制到 $SUPERVISOR_CONF"
else
    echo "  ✗ supervisor 配置文件不存在: $SUPERVISOR_CONF_SRC"
    echo "  请先创建 ddns-ipv6.conf 文件"
    exit 1
fi

# 4. supervisorctl update && start
echo "[4/5] 更新 supervisor 配置..."
supervisorctl update
echo "  ✓ supervisor 配置已更新"

echo "[5/5] 启动 ddns-ipv6 服务..."
supervisorctl start ddns-ipv6
echo "  ✓ 服务已启动"

# 5. 检查状态
echo ""
echo "========================================="
echo "  部署完成！服务状态："
echo "========================================="
supervisorctl status ddns-ipv6
echo ""
echo "查看日志: tail -f /main/log/app/ddns-ipv6.log"
