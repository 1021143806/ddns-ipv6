#!/bin/bash
# DDNS IPv6 一键部署脚本（含 WebUI）
set -e

PROJECT_DIR="/main/app/github/ddns-ipv6"
VENV_DIR="$PROJECT_DIR/venv"
SUPERVISOR_DIR="/main/server/supervisor/conf.d"

echo "========================================="
echo "  DDNS IPv6 部署脚本 (含 WebUI)"
echo "========================================="

# 1. 创建 venv（如不存在）
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/6] 创建 Python 虚拟环境..."
    python3 -m venv "$VENV_DIR"
    echo "  ✓ venv 创建完成"
else
    echo "[1/6] venv 已存在，跳过"
fi

# 2. 安装依赖
echo "[2/6] 安装 Python 依赖..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install fastapi uvicorn jinja2 python-multipart itsdangerous -q
echo "  ✓ 依赖安装完成"

# 3. 复制 env.template.toml → env.toml（如 env.toml 不存在）
if [ ! -f "$PROJECT_DIR/config/env.toml" ]; then
    echo "[3/6] 创建配置文件..."
    cp "$PROJECT_DIR/config/template/env.template.toml" "$PROJECT_DIR/config/env.toml"
    echo "  ⚠ 请编辑 config/env.toml 填入实际 API 密钥和域名信息！"
else
    echo "[3/6] 配置文件已存在，跳过"
fi

# 4. 复制 supervisor 配置
echo "[4/6] 部署 supervisor 配置..."
cp "$PROJECT_DIR/ddns-ipv6.conf" "$SUPERVISOR_DIR/ddns-ipv6.conf"
echo "  ✓ ddns-ipv6.conf"
cp "$PROJECT_DIR/ddns-ipv6-webui.conf" "$SUPERVISOR_DIR/ddns-ipv6-webui.conf"
echo "  ✓ ddns-ipv6-webui.conf"

# 5. supervisorctl update && start
echo "[5/6] 更新 supervisor 配置..."
supervisorctl update
echo "  ✓ supervisor 配置已更新"

echo "[6/6] 启动服务..."
supervisorctl start ddns-ipv6 ddns-ipv6-webui
echo "  ✓ 服务已启动"

# 6. 检查状态
echo ""
echo "========================================="
echo "  部署完成！服务状态："
echo "========================================="
supervisorctl status ddns-ipv6 ddns-ipv6-webui
echo ""
echo "WebUI 地址: http://$(hostname -I | awk '{print $1}'):5080"
echo "守护进程日志: tail -f /main/log/app/ddns-ipv6.log"
echo "WebUI 日志:    tail -f /main/log/app/ddns-ipv6-webui.log"
