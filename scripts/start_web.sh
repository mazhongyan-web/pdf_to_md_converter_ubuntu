#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到Python3，请先安装Python3"
    exit 1
fi

# 检查依赖
if ! command -v tesseract &> /dev/null; then
    echo "错误：未找到Tesseract-OCR，请运行install.sh安装依赖"
    exit 1
fi

if ! command -v pdftoppm &> /dev/null; then
    echo "错误：未找到Poppler-utils，请运行install.sh安装依赖"
    exit 1
fi

# 安装Python依赖（如果需要）
if ! python3 -c "import flask" &> /dev/null; then
    echo "安装Python依赖..."
    pip3 install -r "$PROJECT_ROOT/requirements.txt"
fi

# 启动Web服务器
echo "启动Web服务器..."
cd "$PROJECT_ROOT/src"
python3 web_server.py 