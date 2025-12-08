#!/bin/bash
# 快速启动脚本

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python"
    exit 1
fi

# 检查是否安装了依赖
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 安装Playwright浏览器
echo "安装Playwright浏览器..."
playwright install chromium

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "警告: 未找到.env文件，请复制.env.example并配置"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "已创建.env文件，请编辑并填入你的API密钥"
    fi
fi

# 运行主程序
if [ $# -eq 0 ]; then
    echo "使用方法: ./run.sh <搜索领域>"
    echo "例如: ./run.sh 'Python编程'"
    exit 1
fi

python main.py "$@"
