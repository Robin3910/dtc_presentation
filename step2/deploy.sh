#!/bin/bash
# AI 素材审核助手 · Step 2 部署脚本
# ======================================
# 使用方法：
#   bash deploy.sh              # 交互式部署
#   bash deploy.sh --install    # 安装并启动
#   bash deploy.sh --restart   # 重启服务
#   bash deploy.sh --stop       # 停止服务
#   bash deploy.sh --status     # 查看状态

set -e

# 配置
SERVICE_NAME="ai-reviewer"
SERVICE_USER="www-data"
APP_DIR=$(dirname "$(readlink -f "$0")")
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以 root 权限运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_warn "建议使用 root 权限运行此脚本：sudo bash deploy.sh"
    fi
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装，请先安装 Python 3.8+"
        exit 1
    fi
    
    # 检查 pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 未安装"
        exit 1
    fi
    
    # 检查 git（可选）
    if command -v git &> /dev/null; then
        log_info "Git 已安装"
    fi
    
    log_info "依赖检查完成"
}

# 安装依赖
install_dependencies() {
    log_info "安装 Python 依赖..."
    
    cd "$APP_DIR"
    
    # 创建虚拟环境（可选）
    if [ -d "venv" ]; then
        log_info "使用已有虚拟环境"
        source venv/bin/activate
    else
        log_info "创建虚拟环境..."
        python3 -m venv venv
        source venv/bin/activate
    fi
    
    # 安装依赖
    pip install -r requirements.txt
    
    log_info "依赖安装完成"
}

# 创建服务文件
create_service_file() {
    log_info "创建 systemd 服务文件..."
    
    # 获取当前用户
    CURRENT_USER=${SUDO_USER:-$(whoami)}
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=AI Material Reviewer - Step 2
Documentation=
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=${APP_DIR}/venv/bin/python ${APP_DIR}/app.py --prod
Restart=always
RestartSec=10

# 日志配置
StandardOutput=append:${APP_DIR}/logs/stdout.log
StandardError=append:${APP_DIR}/logs/stderr.log

[Install]
WantedBy=multi-user.target
EOF
    
    log_info "服务文件已创建：$SERVICE_FILE"
}

# 配置防火墙（可选）
configure_firewall() {
    log_info "检查防火墙配置..."
    
    if command -v ufw &> /dev/null; then
        log_info "检测到 UFW 防火墙，开放端口 8080..."
        ufw allow 8080/tcp
        log_info "端口 8080 已开放"
    elif command -v firewall-cmd &> /dev/null; then
        log_info "检测到 firewalld，开放端口 8080..."
        firewall-cmd --permanent --add-port=8080/tcp
        firewall-cmd --reload
        log_info "端口 8080 已开放"
    fi
}

# 安装服务
install() {
    log_info "开始安装 AI 素材审核助手..."
    
    check_root
    check_dependencies
    install_dependencies
    create_service_file
    configure_firewall
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    # 启用服务
    systemctl enable ${SERVICE_NAME}
    
    # 启动服务
    systemctl start ${SERVICE_NAME}
    
    # 检查状态
    sleep 2
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        log_info "服务启动成功！"
        show_status
    else
        log_error "服务启动失败，请检查日志："
        journalctl -u ${SERVICE_NAME} -n 20 --no-pager
        exit 1
    fi
}

# 启动服务
start() {
    log_info "启动服务..."
    systemctl start ${SERVICE_NAME}
    sleep 2
    show_status
}

# 停止服务
stop() {
    log_info "停止服务..."
    systemctl stop ${SERVICE_NAME}
    log_info "服务已停止"
}

# 重启服务
restart() {
    log_info "重启服务..."
    systemctl restart ${SERVICE_NAME}
    sleep 2
    show_status
}

# 查看状态
show_status() {
    echo ""
    echo "======================================"
    echo "  AI 素材审核助手 · 服务状态"
    echo "======================================"
    echo ""
    
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        log_info "服务状态：运行中 ✅"
    else
        log_error "服务状态：已停止 ❌"
    fi
    
    echo ""
    echo "  Web 访问：http://localhost:8080/"
    echo "  上传页面：http://localhost:8080/"
    echo "  管理后台：http://localhost:8080/admin"
    echo ""
    
    # 显示最近日志
    echo "  最近日志（最后 5 行）："
    echo "  --------------------------------"
    journalctl -u ${SERVICE_NAME} -n 5 --no-pager | sed 's/^/  /'
    echo ""
}

# 查看日志
show_logs() {
    echo ""
    echo "======================================"
    echo "  AI 素材审核助手 · 日志"
    echo "======================================"
    echo ""
    journalctl -u ${SERVICE_NAME} -f --no-pager
}

# 卸载
uninstall() {
    log_warn "即将卸载 AI 素材审核助手..."
    
    read -p "确认卸载？(y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "取消卸载"
        exit 0
    fi
    
    log_info "停止并禁用服务..."
    systemctl stop ${SERVICE_NAME}
    systemctl disable ${SERVICE_NAME}
    
    log_info "删除服务文件..."
    rm -f ${SERVICE_FILE}
    
    log_info "重新加载 systemd..."
    systemctl daemon-reload
    
    log_info "卸载完成！"
    log_info "注意：数据文件（uploads/、reports/、logs/、review.db）未删除"
}

# 显示帮助
show_help() {
    echo ""
    echo "AI 素材审核助手 · Step 2 部署脚本"
    echo ""
    echo "使用方法：bash deploy.sh [选项]"
    echo ""
    echo "选项："
    echo "  --install    安装并启动服务"
    echo "  --start      启动服务"
    echo "  --stop       停止服务"
    echo "  --restart    重启服务"
    echo "  --status     查看服务状态"
    echo "  --logs       查看服务日志"
    echo "  --uninstall  卸载服务"
    echo "  --help       显示此帮助信息"
    echo ""
}

# 主程序
case "${1:-}" in
    --install)
        install
        ;;
    --start)
        start
        ;;
    --stop)
        stop
        ;;
    --restart)
        restart
        ;;
    --status)
        show_status
        ;;
    --logs)
        show_logs
        ;;
    --uninstall)
        uninstall
        ;;
    --help)
        show_help
        ;;
    "")
        show_help
        echo "请指定操作选项，或使用交互式菜单："
        echo ""
        echo "  1) 安装并启动服务"
        echo "  2) 启动服务"
        echo "  3) 停止服务"
        echo "  4) 重启服务"
        echo "  5) 查看状态"
        echo "  6) 查看日志"
        echo "  7) 卸载服务"
        echo "  0) 退出"
        echo ""
        read -p "请选择 [0-7]: " choice
        case "$choice" in
            1) install ;;
            2) start ;;
            3) stop ;;
            4) restart ;;
            5) show_status ;;
            6) show_logs ;;
            7) uninstall ;;
            0) exit 0 ;;
            *) log_error "无效选项" ;;
        esac
        ;;
    *)
        log_error "未知选项：$1"
        show_help
        exit 1
        ;;
esac
