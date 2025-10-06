#!/bin/bash
# macOS 环境检查脚本

echo "🍎 macOS 反向跟单机器人环境检查"
echo "================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "✅ $1: ${GREEN}已安装${NC}"
        return 0
    else
        echo -e "❌ $1: ${RED}未安装${NC}"
        return 1
    fi
}

check_python_version() {
    if command -v python3 &> /dev/null; then
        version=$(python3 --version 2>&1 | cut -d' ' -f2)
        major=$(echo $version | cut -d'.' -f1)
        minor=$(echo $version | cut -d'.' -f2)
        
        if [ "$major" -eq 3 ] && [ "$minor" -ge 8 ]; then
            echo -e "✅ Python3: ${GREEN}$version (满足要求 ≥3.8)${NC}"
            return 0
        else
            echo -e "❌ Python3: ${RED}$version (需要 ≥3.8)${NC}"
            return 1
        fi
    else
        echo -e "❌ Python3: ${RED}未安装${NC}"
        return 1
    fi
}

# 系统信息
echo "📋 系统信息:"
echo "   系统版本: $(sw_vers -productName) $(sw_vers -productVersion)"
echo "   架构: $(uname -m)"
echo "   内存: $(system_profiler SPHardwareDataType | grep "Memory:" | awk '{print $2 " " $3}')"
echo ""

# 基础环境检查
echo "🔍 基础环境检查:"
check_python_version
python_ok=$?

check_command "pip3"
pip_ok=$?

check_command "git"
git_ok=$?

echo ""

# Python 模块检查
echo "📦 Python 模块检查:"
modules=("ccxt" "telethon" "nest_asyncio" "pytz")
module_errors=0

for module in "${modules[@]}"; do
    if python3 -c "import $module" &> /dev/null; then
        echo -e "✅ $module: ${GREEN}已安装${NC}"
    else
        echo -e "❌ $module: ${RED}未安装${NC}"
        ((module_errors++))
    fi
done

echo ""

# 网络连接检查
echo "🌐 网络连接检查:"
if ping -c 1 google.com &> /dev/null; then
    echo -e "✅ 互联网连接: ${GREEN}正常${NC}"
    network_ok=0
else
    echo -e "❌ 互联网连接: ${RED}异常${NC}"
    network_ok=1
fi

# API 端点检查
endpoints=("api.telegram.org" "www.okx.com")
for endpoint in "${endpoints[@]}"; do
    if ping -c 1 $endpoint &> /dev/null; then
        echo -e "✅ $endpoint: ${GREEN}可访问${NC}"
    else
        echo -e "❌ $endpoint: ${RED}不可访问${NC}"
    fi
done

echo ""

# 文件系统检查
echo "📁 项目文件检查:"
required_files=(
    "core-lib/setup.py"
    "simple-reverse-bot/main.py"
    "turtle-reverse-bot/main.py"
    "simple-reverse-bot/config/config.json"
    "turtle-reverse-bot/config/config.json"
    "requirements.txt"
)

file_errors=0
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "✅ $file: ${GREEN}存在${NC}"
    else
        echo -e "❌ $file: ${RED}缺失${NC}"
        ((file_errors++))
    fi
done

echo ""

# 权限检查
echo "🔒 权限检查:"
if [ -w "." ]; then
    echo -e "✅ 写入权限: ${GREEN}正常${NC}"
    write_ok=0
else
    echo -e "❌ 写入权限: ${RED}不足${NC}"
    write_ok=1
fi

# 端口检查
echo "🔌 端口检查:"
ports_to_check=(8080 9090 443 80)
for port in "${ports_to_check[@]}"; do
    if lsof -i :$port &> /dev/null; then
        echo -e "⚠️  端口 $port: ${YELLOW}已被占用${NC}"
    else
        echo -e "✅ 端口 $port: ${GREEN}可用${NC}"
    fi
done

echo ""

# 配置检查
echo "⚙️ 配置文件检查:"
config_files=("simple-reverse-bot/config/config.json" "turtle-reverse-bot/config/config.json")
config_warnings=0

for config_file in "${config_files[@]}"; do
    if [ -f "$config_file" ]; then
        if grep -q "YOUR_" "$config_file"; then
            echo -e "⚠️  $config_file: ${YELLOW}包含占位符，需要配置 API 密钥${NC}"
            ((config_warnings++))
        else
            echo -e "✅ $config_file: ${GREEN}配置完整${NC}"
        fi
        
        # 检查 JSON 格式
        if python3 -c "import json; json.load(open('$config_file'))" &> /dev/null; then
            echo -e "✅ $config_file: ${GREEN}JSON 格式正确${NC}"
        else
            echo -e "❌ $config_file: ${RED}JSON 格式错误${NC}"
            ((config_warnings++))
        fi
    fi
done

echo ""

# 总结
echo "📊 环境检查总结:"
echo "================================="

total_errors=0
((total_errors += !python_ok))
((total_errors += !pip_ok))
((total_errors += !git_ok))
((total_errors += module_errors))
((total_errors += network_ok))
((total_errors += file_errors))
((total_errors += write_ok))

if [ $total_errors -eq 0 ]; then
    echo -e "${GREEN}🎉 环境检查通过！系统已准备就绪。${NC}"
    echo ""
    echo "🚀 下一步操作:"
    if [ $config_warnings -gt 0 ]; then
        echo "   1. 配置 API 密钥到 config.json 文件"
        echo "   2. 运行: ./start_simple_bot.sh 或 ./start_turtle_bot.sh"
    else
        echo "   1. 运行: ./start_simple_bot.sh 或 ./start_turtle_bot.sh"
    fi
    echo "   2. 监控日志: tail -f simple-reverse-bot/logs/bot.log"
else
    echo -e "${RED}❌ 发现 $total_errors 个问题需要解决${NC}"
    echo ""
    echo "🔧 解决建议:"
    
    if [ $python_ok -ne 0 ]; then
        echo "   - 安装 Python 3.8+: brew install python@3.9"
    fi
    
    if [ $pip_ok -ne 0 ]; then
        echo "   - 安装 pip: python3 -m ensurepip --upgrade"
    fi
    
    if [ $module_errors -gt 0 ]; then
        echo "   - 安装 Python 模块: pip3 install -r requirements.txt"
    fi
    
    if [ $network_ok -ne 0 ]; then
        echo "   - 检查网络连接和防火墙设置"
    fi
    
    if [ $file_errors -gt 0 ]; then
        echo "   - 确保项目文件完整，重新下载/解压项目"
    fi
    
    if [ $write_ok -ne 0 ]; then
        echo "   - 修复权限: sudo chown -R $(whoami) ."
    fi
fi

echo ""
echo "💡 如需帮助，请查看 macos_deployment_guide.md"