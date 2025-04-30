#!/bin/bash

# 安装系统依赖
sudo ./install.sh

# 安装生产环境依赖
pip3 install gunicorn

# 创建日志目录
mkdir -p logs

# 创建上传目录
mkdir -p uploads

# 设置权限
chmod 755 uploads
chmod 755 logs

# 启动应用（使用 gunicorn）
gunicorn --worker-class eventlet -w 4 -b 0.0.0.0:5000 app:app --access-logfile logs/access.log --error-logfile logs/error.log 