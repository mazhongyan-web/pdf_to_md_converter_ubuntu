#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 检查Python虚拟环境
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv "$PROJECT_ROOT/.venv"
fi

# 激活虚拟环境
source "$PROJECT_ROOT/.venv/bin/activate"

# 启动程序
echo "启动PDF转Markdown工具..."
cd "$PROJECT_ROOT/src"
python pdf_to_md_converter.py 