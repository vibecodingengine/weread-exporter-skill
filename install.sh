#!/bin/bash
# WeRead Exporter Installation Script
# 一键安装脚本

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

# 检查 Python 是否安装
check_python() {
    print_info "检查 Python 环境..."

    if ! command -v python3 &> /dev/null; then
        print_error "未找到 python3，请先安装 Python 3.7 或更高版本"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_success "找到 Python $PYTHON_VERSION"
}

# 安装 Python 依赖
install_dependencies() {
    print_info "创建隔离的 Python 环境并安装依赖..."

    if ! python3 -m venv .venv; then
        print_error "创建 .venv 失败，请安装 python3-venv"
        exit 1
    fi
    if ! .venv/bin/python -m pip install --upgrade pip; then
        print_error "pip 升级失败"
        exit 1
    fi
    if ! .venv/bin/python -m pip install --require-hashes -r requirements.lock; then
        print_error "依赖安装失败"
        exit 1
    fi
    if ! .venv/bin/python -m pip install --no-deps -e .; then
        print_error "项目安装失败"
        exit 1
    fi
    if ! .venv/bin/python -m playwright install chromium; then
        print_error "Playwright Chromium 安装失败"
        exit 1
    fi

    print_success "依赖安装完成"
}

# 检查 Claude Code CLI 是否安装
check_claude() {
    print_info "检查 Claude Code CLI..."

    if ! command -v claude &> /dev/null; then
        print_error "未找到 Claude Code CLI"
        print_info "请访问 https://claude.ai/download 安装 Claude Code"
        exit 1
    fi

    print_success "Claude Code CLI 已安装"
}

# 安装 Claude 插件
install_plugin() {
    print_info "安装 Claude 插件..."

    if claude plugin install --scope user .claude-plugin/; then
        print_success "插件安装成功"
    else
        print_error "插件安装失败"
        print_info "您可以手动运行: claude plugin install --scope user .claude-plugin/"
        exit 1
    fi
}

# 显示使用说明
show_usage() {
    echo ""
    echo "=========================================="
    print_success "安装完成！"
    echo "=========================================="
    echo ""
    echo "使用方法："
    echo "  1. 在 Claude Code 中使用："
    echo "     \"Export the WeRead book with ID <book_id> to epub\""
    echo ""
    echo "  2. 或者直接命令行使用："
    echo "     .venv/bin/python -m weread_exporter -b <book_id> -o epub"
    echo ""
    echo "  更多信息请查看 .claude-plugin/README.md"
    echo ""
}

# 主安装流程
main() {
    echo ""
    echo "=========================================="
    echo "  WeRead Exporter 安装向导"
    echo "=========================================="
    echo ""

    # 检查是否在项目根目录
    if [ ! -f "setup.py" ] || [ ! -d ".claude-plugin" ]; then
        print_error "请在项目根目录运行此脚本"
        exit 1
    fi

    # 执行安装步骤
    check_python
    install_dependencies
    if command -v claude &> /dev/null; then
        install_plugin
    else
        print_info "未安装 Claude Code，跳过 Claude 插件注册"
    fi
    show_usage
}

# 运行主程序
main
