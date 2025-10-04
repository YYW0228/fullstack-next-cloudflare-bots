#!/bin/bash
# 反向跟单机器人 Cloudflare 部署脚本

echo "🚀 部署反向跟单机器人到 Cloudflare"
echo "=================================="

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查依赖
check_dependencies() {
    echo -e "${BLUE}📦 检查依赖...${NC}"
    
    if ! command -v wrangler &> /dev/null; then
        echo -e "${RED}❌ Wrangler CLI 未安装${NC}"
        echo "请运行: npm install -g wrangler"
        exit 1
    fi
    
    if ! command -v pnpm &> /dev/null; then
        echo -e "${RED}❌ pnpm 未安装${NC}"
        echo "请运行: npm install -g pnpm"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 依赖检查完成${NC}"
}

# 安装项目依赖
install_dependencies() {
    echo -e "${BLUE}📥 安装项目依赖...${NC}"
    pnpm install
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
}

# 构建项目
build_project() {
    echo -e "${BLUE}🔨 构建项目...${NC}"
    pnpm run build:cf
    echo -e "${GREEN}✅ 项目构建完成${NC}"
}

# 创建 D1 数据库
setup_d1_database() {
    echo -e "${BLUE}🗄️ 设置 D1 数据库...${NC}"
    
    # 创建数据库
    wrangler d1 create trading-bots-db || echo "数据库可能已存在"
    
    # 运行迁移
    echo -e "${YELLOW}⚠️ 请手动更新 wrangler.trading-bot.toml 中的 database_id${NC}"
    echo "从上面的输出中复制 database_id 并更新配置文件"
    
    read -p "已更新 database_id? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        # 生成数据库迁移
        pnpm run db:generate
        
        # 应用迁移到本地
        wrangler d1 migrations apply trading-bots-db --local --config wrangler.trading-bot.toml
        
        # 应用迁移到远程
        wrangler d1 migrations apply trading-bots-db --config wrangler.trading-bot.toml
        
        echo -e "${GREEN}✅ D1 数据库设置完成${NC}"
    else
        echo -e "${YELLOW}⏸️ 请先配置 database_id${NC}"
        exit 1
    fi
}

# 设置环境变量
setup_secrets() {
    echo -e "${BLUE}🔐 设置敏感环境变量...${NC}"
    
    echo "请设置以下敏感信息:"
    
    read -p "OKX API Key: " okx_api_key
    read -s -p "OKX Secret: " okx_secret
    echo ""
    read -s -p "OKX Passphrase: " okx_passphrase
    echo ""
    read -p "Telegram Bot Token: " telegram_token
    read -p "Telegram API ID: " telegram_api_id
    read -p "Telegram API Hash: " telegram_api_hash
    
    # 设置 secrets
    echo "$okx_api_key" | wrangler secret put OKX_API_KEY --config wrangler.trading-bot.toml
    echo "$okx_secret" | wrangler secret put OKX_SECRET --config wrangler.trading-bot.toml
    echo "$okx_passphrase" | wrangler secret put OKX_PASSPHRASE --config wrangler.trading-bot.toml
    echo "$telegram_token" | wrangler secret put TELEGRAM_BOT_TOKEN --config wrangler.trading-bot.toml
    echo "$telegram_api_id" | wrangler secret put TELEGRAM_API_ID --config wrangler.trading-bot.toml
    echo "$telegram_api_hash" | wrangler secret put TELEGRAM_API_HASH --config wrangler.trading-bot.toml
    
    echo -e "${GREEN}✅ 环境变量设置完成${NC}"
}

# 部署到测试环境
deploy_staging() {
    echo -e "${BLUE}🧪 部署到测试环境...${NC}"
    wrangler deploy --env staging --config wrangler.trading-bot.toml
    echo -e "${GREEN}✅ 测试环境部署完成${NC}"
}

# 部署到生产环境
deploy_production() {
    echo -e "${BLUE}🚀 部署到生产环境...${NC}"
    echo -e "${YELLOW}⚠️ 确认要部署到生产环境吗？这将启用实盘交易！${NC}"
    read -p "确认部署到生产环境? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        wrangler deploy --env production --config wrangler.trading-bot.toml
        echo -e "${GREEN}✅ 生产环境部署完成${NC}"
        
        echo ""
        echo -e "${GREEN}🎉 反向跟单机器人部署成功！${NC}"
        echo ""
        echo "📊 访问地址:"
        echo "   管理界面: https://your-domain.com/trading"
        echo "   API 文档: https://reverse-trading-bot-prod.your-subdomain.workers.dev"
        echo ""
        echo "🔧 Webhook 配置:"
        echo "   Telegram: https://reverse-trading-bot-prod.your-subdomain.workers.dev/webhook/telegram"
        echo ""
        echo "💡 下一步:"
        echo "   1. 配置 Telegram Webhook"
        echo "   2. 测试信号接收"
        echo "   3. 监控交易执行"
    else
        echo -e "${YELLOW}⏸️ 生产环境部署已取消${NC}"
    fi
}

# 导入历史数据
import_historical_data() {
    echo -e "${BLUE}📊 导入历史交易数据...${NC}"
    
    # 这里可以添加导入您10个月历史数据的逻辑
    echo "历史数据导入功能准备就绪"
    echo "可以通过 /api/trading-bots/history 接口导入您的历史数据"
}

# 主菜单
main_menu() {
    echo ""
    echo -e "${BLUE}选择操作:${NC}"
    echo "1) 完整部署 (推荐新用户)"
    echo "2) 仅部署到测试环境"
    echo "3) 仅部署到生产环境"
    echo "4) 设置数据库"
    echo "5) 设置环境变量"
    echo "6) 导入历史数据"
    echo "7) 退出"
    echo ""
    
    read -p "请选择 (1-7): " choice
    
    case $choice in
        1)
            check_dependencies
            install_dependencies
            build_project
            setup_d1_database
            setup_secrets
            deploy_staging
            deploy_production
            import_historical_data
            ;;
        2)
            check_dependencies
            build_project
            deploy_staging
            ;;
        3)
            check_dependencies
            build_project
            deploy_production
            ;;
        4)
            setup_d1_database
            ;;
        5)
            setup_secrets
            ;;
        6)
            import_historical_data
            ;;
        7)
            echo "退出部署脚本"
            exit 0
            ;;
        *)
            echo "无效选择"
            main_menu
            ;;
    esac
}

# 欢迎信息
echo -e "${GREEN}哥，欢迎使用反向跟单机器人部署脚本！${NC}"
echo ""
echo "🎯 这个脚本将帮您:"
echo "   ✅ 部署到 Cloudflare 全球边缘网络"
echo "   ✅ 配置 D1 数据库存储交易数据"
echo "   ✅ 设置环境变量和 API 密钥"
echo "   ✅ 集成您的历史交易数据"
echo "   ✅ 提供完整的监控界面"
echo ""

# 运行主菜单
main_menu
