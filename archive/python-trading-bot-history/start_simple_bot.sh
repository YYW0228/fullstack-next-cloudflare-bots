#!/bin/bash
# 简单反向机器人启动脚本 (macOS)

echo "🤖 启动简单反向机器人 (macOS)..."
echo "=================================="

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查并创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ 虚拟环境创建失败，请检查 Python 安装"
        exit 1
    fi
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 验证虚拟环境
if [ "$VIRTUAL_ENV" == "" ]; then
    echo "❌ 虚拟环境激活失败"
    exit 1
fi

echo "✅ 虚拟环境已激活: $VIRTUAL_ENV"

# 安装核心库
echo "📥 安装核心库..."
cd core-lib
pip install -e . > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 核心库安装失败"
    cd ..
    exit 1
fi
cd ..

# 安装其他依赖
echo "📥 检查依赖包..."
pip install -r requirements.txt > /dev/null 2>&1

# 检查配置文件
echo "⚙️ 检查配置文件..."
if [ ! -f "simple-reverse-bot/config/config.json" ]; then
    echo "❌ 配置文件不存在: simple-reverse-bot/config/config.json"
    exit 1
fi

# 检查 API 配置
if grep -q "YOUR_" "simple-reverse-bot/config/config.json"; then
    echo "⚠️  警告: 配置文件包含占位符，请先配置 API 密钥"
    echo "📝 编辑文件: simple-reverse-bot/config/config.json"
    echo ""
    echo "是否继续启动? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "❌ 启动已取消"
        exit 1
    fi
fi

# 创建日志目录
mkdir -p simple-reverse-bot/logs

# 显示启动信息
echo ""
echo "🚀 启动简单反向机器人..."
echo "策略: 30% 固定止盈反向跟单"
echo "时间: $(date)"
echo "目录: $(pwd)/simple-reverse-bot"
echo ""

# 启动机器人
cd simple-reverse-bot

# 设置信号处理
trap 'echo "🛑 接收到停止信号，正在关闭机器人..."; kill $BOT_PID 2>/dev/null; exit 0' INT TERM

# 启动机器人并获取 PID
python main.py &
BOT_PID=$!

echo "✅ 简单反向机器人已启动 (PID: $BOT_PID)"
echo "📊 监控日志: tail -f logs/bot.log"
echo "🛑 停止机器人: Ctrl+C 或 kill $BOT_PID"
echo ""

# 等待进程
wait $BOT_PID
echo "🏁 简单反向机器人已停止"