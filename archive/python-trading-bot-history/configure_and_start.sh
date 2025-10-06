#!/bin/bash
# 智慧配置启动器 - 体现Linus的哲学: "Talk is cheap. Show me the code."

echo "🧠 反向跟单机器人智慧配置器"
echo "================================"
echo "哥，让我们以代码的方式对话，用行动证明一切"
echo ""

# 颜色和样式
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# 哲学函数：问题的本质是选择
philosophical_choice() {
    local question="$1"
    local option1="$2"
    local option2="$3"
    local default="$4"
    
    echo -e "${PURPLE}🤔 哲学思考: $question${NC}"
    echo -e "   1) $option1"
    echo -e "   2) $option2"
    echo -e "   ${CYAN}默认选择 ($default) 体现了什么哲学？${NC}"
    echo ""
    read -p "您的选择 (1/2, 默认$default): " choice
    echo "$choice"
}

# 检查当前配置状态
check_current_state() {
    echo -e "${BLUE}📊 当前状态诊断${NC}"
    
    if [ -f "simple-reverse-bot/config/config.json" ]; then
        if grep -q "YOUR_" "simple-reverse-bot/config/config.json"; then
            echo -e "   简单机器人: ${YELLOW}需要配置${NC}"
            return 1
        else
            echo -e "   简单机器人: ${GREEN}已配置${NC}"
        fi
    else
        echo -e "   简单机器人: ${RED}配置缺失${NC}"
        return 1
    fi
    
    if [ -f "turtle-reverse-bot/config/config.json" ]; then
        if grep -q "YOUR_" "turtle-reverse-bot/config/config.json"; then
            echo -e "   海龟机器人: ${YELLOW}需要配置${NC}"
            return 1
        else
            echo -e "   海龟机器人: ${GREEN}已配置${NC}"
        fi
    else
        echo -e "   海龟机器人: ${RED}配置缺失${NC}"
        return 1
    fi
    
    return 0
}

# 哲学层面的战略选择
strategic_choice() {
    echo -e "${BOLD}${PURPLE}🎯 战略哲学选择${NC}"
    echo "Linus说：'好的软件是进化的结果，不是设计的结果'"
    echo ""
    
    choice=$(philosophical_choice \
        "您希望如何开始这个进化过程？" \
        "快速配置并立即开始测试 (实用主义)" \
        "详细配置每个参数 (完美主义)" \
        "1")
    
    if [ "$choice" = "2" ]; then
        echo -e "${CYAN}💭 您选择了完美主义路径...${NC}"
        echo "正如Linus所说：'细节中藏着魔鬼，也藏着上帝'"
        detailed_configuration=true
    else
        echo -e "${CYAN}💭 您选择了实用主义路径...${NC}"
        echo "正如Linus所说：'先让它运行，再让它正确，最后让它快速'"
        detailed_configuration=false
    fi
}

# 执行配置流程
execute_configuration() {
    echo ""
    echo -e "${GREEN}🔧 执行配置...${NC}"
    
    # 检查配置向导是否存在
    if [ ! -f "api_config_wizard.sh" ]; then
        echo -e "${RED}❌ 配置向导不存在${NC}"
        return 1
    fi
    
    # 执行配置
    echo -e "${CYAN}启动API配置向导...${NC}"
    ./api_config_wizard.sh
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 配置过程中发生错误${NC}"
        return 1
    fi
    
    return 0
}

# 验证配置质量
verify_configuration() {
    echo ""
    echo -e "${BLUE}🔍 配置验证 (Linus级别的严谨性)${NC}"
    
    if [ ! -f "verify_config.py" ]; then
        echo -e "${RED}❌ 配置验证器不存在${NC}"
        return 1
    fi
    
    python3 verify_config.py
    return $?
}

# 智慧启动选择
intelligent_startup() {
    echo ""
    echo -e "${BOLD}${GREEN}🚀 智慧启动决策${NC}"
    echo "配置已完成，现在让我们选择启动策略"
    echo ""
    
    startup_choice=$(philosophical_choice \
        "您希望如何体验反向跟单的智慧？" \
        "启动简单机器人 (30%固定止盈，稳健路线)" \
        "启动海龟机器人 (分层滚仓，激进路线)" \
        "1")
    
    if [ "$startup_choice" = "2" ]; then
        echo -e "${PURPLE}🐢 海龟的智慧: 慢即是快，复杂即是美${NC}"
        target_bot="turtle"
        startup_script="./start_turtle_bot.sh"
        log_file="turtle-reverse-bot/logs/bot.log"
    else
        echo -e "${BLUE}🤖 简单的智慧: 大道至简，少即是多${NC}"
        target_bot="simple"
        startup_script="./start_simple_bot.sh"
        log_file="simple-reverse-bot/logs/bot.log"
    fi
    
    # 启动确认
    echo ""
    echo -e "${YELLOW}⚠️ 启动确认${NC}"
    echo "即将启动: $target_bot 反向机器人"
    echo "启动脚本: $startup_script"
    echo "监控日志: $log_file"
    echo ""
    
    read -p "确认启动? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${GREEN}🎉 启动机器人...${NC}"
        echo "正如Linus所说：'只有代码是诚实的'"
        echo ""
        
        # 创建日志目录
        mkdir -p "$(dirname "$log_file")"
        
        # 启动机器人
        echo -e "${CYAN}执行: $startup_script${NC}"
        $startup_script &
        bot_pid=$!
        
        echo -e "${GREEN}✅ 机器人已启动 (PID: $bot_pid)${NC}"
        echo ""
        echo -e "${BLUE}📊 监控命令:${NC}"
        echo "   实时日志: tail -f $log_file"
        echo "   停止机器人: kill $bot_pid"
        echo "   检查进程: ps aux | grep python"
        echo ""
        echo -e "${PURPLE}🧠 哲学思考:${NC}"
        echo "   机器人现在正在执行反向跟单逻辑"
        echo "   它将把市场的贪婪转化为我们的理性"
        echo "   时间套利的智慧正在发生作用..."
        echo ""
        
        # 等待几秒钟让机器人启动
        sleep 3
        
        # 检查启动状态
        if kill -0 $bot_pid 2>/dev/null; then
            echo -e "${GREEN}✅ 机器人运行正常${NC}"
            
            # 提供监控选项
            echo ""
            read -p "是否查看实时日志? (y/N): " view_logs
            if [[ "$view_logs" =~ ^[Yy]$ ]]; then
                echo -e "${CYAN}启动实时日志监控...${NC}"
                echo "按 Ctrl+C 退出日志监控"
                sleep 1
                tail -f "$log_file"
            fi
        else
            echo -e "${RED}❌ 机器人启动失败${NC}"
            echo "请检查配置和依赖"
        fi
    else
        echo -e "${YELLOW}⏸️ 启动已取消${NC}"
        echo "您可以稍后手动运行: $startup_script"
    fi
}

# 主流程
main() {
    echo -e "${BOLD}欢迎来到反向跟单的哲学世界${NC}"
    echo "这里每一行代码都承载着对市场的深刻理解"
    echo ""
    
    # 检查当前状态
    if check_current_state; then
        echo -e "${GREEN}✅ 配置已存在${NC}"
        
        read -p "是否重新配置? (y/N): " reconfigure
        if [[ ! "$reconfigure" =~ ^[Yy]$ ]]; then
            echo "跳过配置，直接进入启动流程"
            verify_configuration && intelligent_startup
            return $?
        fi
    fi
    
    # 战略选择
    strategic_choice
    
    # 执行配置
    if execute_configuration; then
        echo -e "${GREEN}✅ 配置完成${NC}"
        
        # 验证配置
        if verify_configuration; then
            echo -e "${GREEN}✅ 配置验证通过${NC}"
            
            # 智慧启动
            intelligent_startup
        else
            echo -e "${RED}❌ 配置验证失败，请修复问题后重试${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ 配置失败${NC}"
        return 1
    fi
}

# 信号处理
trap 'echo -e "\n${YELLOW}⏹️ 配置过程被中断${NC}"; exit 1' INT TERM

# 执行主流程
main "$@"