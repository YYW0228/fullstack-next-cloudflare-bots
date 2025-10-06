#!/bin/bash

echo "🤖 启动反向跟单机器人..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行部署脚本"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查配置文件
if [ ! -f "config.json" ]; then
    echo "❌ 配置文件不存在，请先配置 config.json"
    exit 1
fi

# 检查数据库
if [ ! -f "trading_bot.db" ]; then
    echo "❌ 数据库不存在，请先运行数据库初始化"
    exit 1
fi

# 启动机器人
echo "🚀 启动交易机器人..."
python main.py

