#!/bin/bash

echo "开始安装PDF转Markdown工具..."

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "请使用sudo运行此安装脚本"
    exit 1
fi

# 更新包列表
echo "更新系统包列表..."
apt-get update

# 安装系统依赖
echo "安装系统依赖..."
apt-get install -y python3-pip python3-tk tesseract-ocr tesseract-ocr-chi-sim poppler-utils zenity

# 安装Python依赖
echo "安装Python依赖..."
pip3 install -r requirements.txt

# 设置执行权限
echo "设置执行权限..."
chmod +x pdf_to_md_converter_ubuntu.py

echo "安装完成！"
echo "您可以通过运行 python3 pdf_to_md_converter_ubuntu.py 来启动程序" 