#!/bin/bash
# Python 3.11 升级到 3.12 的快速脚本
# 适用于 Ubuntu/Debian 系统

set -e  # 遇到错误立即退出

echo "🐍 Python 升级脚本"
echo "=================="
echo ""

# 检查当前 Python 版本
CURRENT_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "当前 Python 版本: $CURRENT_VERSION"

# 检查是否已经是 3.12
if [[ "$CURRENT_VERSION" == 3.12* ]]; then
    echo "✅ 你已经安装了 Python 3.12，无需升级！"
    exit 0
fi

echo ""
echo "开始升级到 Python 3.12..."
echo ""

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo "❌ 无法检测操作系统"
    exit 1
fi

echo "检测到操作系统: $OS $VER"
echo ""

# Ubuntu/Debian 系统
if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
    echo "📦 使用 deadsnakes PPA 安装 Python 3.12..."
    
    # 更新包列表
    sudo apt update
    
    # 安装必要的依赖
    sudo apt install -y software-properties-common
    
    # 添加 deadsnakes PPA
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    
    # 更新包列表
    sudo apt update
    
    # 安装 Python 3.12
    echo "正在安装 Python 3.12..."
    sudo apt install -y python3.12 python3.12-venv python3.12-dev
    
    # 安装 pip
    echo "正在安装 pip..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12
    
    # 验证安装
    echo ""
    echo "✅ 安装完成！"
    echo ""
    python3.12 --version
    python3.12 -m pip --version
    
    echo ""
    echo "💡 提示："
    echo "   - 使用 'python3.12' 命令调用新版本"
    echo "   - 创建虚拟环境: python3.12 -m venv venv"
    echo "   - 查看详细指南: cat PYTHON_UPGRADE_GUIDE.md"
    
else
    echo "❌ 此脚本目前仅支持 Ubuntu/Debian 系统"
    echo ""
    echo "对于其他系统，请参考 PYTHON_UPGRADE_GUIDE.md："
    echo "  - macOS: 使用 Homebrew 或 pyenv"
    echo "  - Windows: 使用官方安装程序"
    echo "  - 其他 Linux: 使用 pyenv 或从源码编译"
    exit 1
fi
