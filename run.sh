#!/bin/bash
# 快速启动脚本

echo "小红书AI Agent系统启动脚本"
echo "================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请先安装 Python 3.8+"
    exit 1
fi

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo "错误: 未找到 requirements.txt"
    exit 1
fi

# 检查是否已安装依赖
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "正在安装依赖..."
    pip install -r requirements.txt
    echo "正在安装 Playwright 浏览器..."
    playwright install chromium
fi

# 检查环境变量
if [ ! -f ".env" ]; then
    echo "警告: 未找到 .env 文件，请先配置环境变量"
    echo "可以复制 .env.example 为 .env 并填写配置"
    if [ -f ".env.example" ]; then
        read -p "是否现在复制 .env.example 为 .env? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env.example .env
            echo "已创建 .env 文件，请编辑填写配置"
            exit 0
        fi
    fi
fi

# 创建必要目录
mkdir -p .auth
mkdir -p data

# 运行主程序
if [ $# -eq 0 ]; then
    echo "请输入搜索关键词作为参数，例如:"
    echo "  ./run.sh 'Python编程'"
    echo ""
    echo "或者直接运行: python3 main.py '关键词'"
    exit 1
else
    python3 main.py "$@"
fi
