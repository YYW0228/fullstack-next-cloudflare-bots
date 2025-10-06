#!/bin/bash

# 🚀 反向跟单机器人自动化部署脚本
# 该脚本提供完整的部署自动化，包括环境检查、构建、测试和部署

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 显示横幅
show_banner() {
    echo -e "${BLUE}"
    echo "🤖 =================================="
    echo "   反向跟单机器人部署脚本"
    echo "   Trading Bot Deployment Script"
    echo "==================================${NC}"
    echo
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    local deps=("node" "pnpm" "git")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "缺少以下依赖: ${missing_deps[*]}"
        log_info "请安装缺少的依赖后重新运行脚本"
        exit 1
    fi
    
    log_success "所有系统依赖检查通过"
}

# 检查 Node.js 版本
check_node_version() {
    log_info "检查 Node.js 版本..."
    
    local node_version=$(node -v | cut -d'v' -f2)
    local required_version="18.0.0"
    
    if [ "$(printf '%s\n' "$required_version" "$node_version" | sort -V | head -n1)" != "$required_version" ]; then
        log_error "Node.js 版本过低。需要 >= $required_version，当前版本: $node_version"
        exit 1
    fi
    
    log_success "Node.js 版本检查通过: v$node_version"
}

# 检查环境变量
check_environment() {
    log_info "检查环境变量配置..."
    
    local required_vars=(
        "CLOUDFLARE_ACCOUNT_ID"
        "CLOUDFLARE_D1_TOKEN" 
        "OKX_API_KEY"
        "OKX_SECRET"
        "OKX_PASSPHRASE"
        "BETTER_AUTH_SECRET"
    )
    
    local missing_vars=()
    
    # 检查 .env 文件
    if [ ! -f ".env" ]; then
        log_warning ".env 文件不存在，将从模板创建"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_info "已从 .env.example 创建 .env 文件，请编辑并填入正确的配置"
        else
            log_error "未找到 .env.example 模板文件"
            return 1
        fi
    fi
    
    # 加载环境变量
    set -o allexport
    source .env
    set +o allexport
    
    # 检查必需变量
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "缺少以下环境变量: ${missing_vars[*]}"
        log_info "请在 .env 文件中配置这些变量"
        return 1
    fi
    
    log_success "环境变量检查通过"
}

# 安装依赖
install_dependencies() {
    log_info "安装项目依赖..."
    
    if [ ! -f "pnpm-lock.yaml" ]; then
        log_info "首次安装，这可能需要一些时间..."
    fi
    
    pnpm install --frozen-lockfile
    
    log_success "依赖安装完成"
}

# 运行类型检查
run_type_check() {
    log_info "运行 TypeScript 类型检查..."
    
    pnpm run type-check || {
        log_error "TypeScript 类型检查失败"
        return 1
    }
    
    log_success "类型检查通过"
}

# 运行测试
run_tests() {
    log_info "运行测试套件..."
    
    # 检查是否有测试文件
    if find . -name "*.test.*" -o -name "*.spec.*" | grep -q .; then
        pnpm test || {
            log_error "测试失败"
            return 1
        }
        log_success "所有测试通过"
    else
        log_warning "未找到测试文件，跳过测试"
    fi
}

# 构建项目
build_project() {
    log_info "构建项目..."
    
    # 清理之前的构建
    rm -rf .next
    
    pnpm build || {
        log_error "项目构建失败"
        return 1
    }
    
    log_success "项目构建完成"
}

# 验证 Wrangler 配置
validate_wrangler_config() {
    log_info "验证 Wrangler 配置..."
    
    if [ ! -f "wrangler.trading-bot.toml" ]; then
        log_error "未找到 wrangler.trading-bot.toml 配置文件"
        return 1
    fi
    
    # 检查 Wrangler 是否已安装
    if ! command -v wrangler &> /dev/null; then
        log_info "安装 Wrangler..."
        pnpm add -g wrangler
    fi
    
    # 验证配置
    npx wrangler whoami || {
        log_error "Wrangler 认证失败，请运行 'npx wrangler login'"
        return 1
    }
    
    log_success "Wrangler 配置验证通过"
}

# 创建/更新数据库
setup_database() {
    log_info "设置数据库..."
    
    # 检查数据库是否存在
    local db_name="trading-bots-db"
    
    if npx wrangler d1 list | grep -q "$db_name"; then
        log_info "数据库 $db_name 已存在"
    else
        log_info "创建数据库 $db_name..."
        npx wrangler d1 create "$db_name"
    fi
    
    # 运行迁移
    if [ -f "src/drizzle/0000_initial_schemas_migration.sql" ]; then
        log_info "运行数据库迁移..."
        npx wrangler d1 execute "$db_name" --file=src/drizzle/0000_initial_schemas_migration.sql
    fi
    
    log_success "数据库设置完成"
}

# 部署到 Cloudflare
deploy_to_cloudflare() {
    local environment=${1:-"staging"}
    
    log_info "部署到 Cloudflare ($environment)..."
    
    # 设置环境变量
    log_info "设置 Worker 环境变量..."
    
    local secrets=(
        "OKX_API_KEY"
        "OKX_SECRET" 
        "OKX_PASSPHRASE"
        "BETTER_AUTH_SECRET"
    )
    
    for secret in "${secrets[@]}"; do
        if [ -n "${!secret}" ]; then
            echo "${!secret}" | npx wrangler secret put "$secret" --config wrangler.trading-bot.toml --env "$environment"
        fi
    done
    
    # 部署 Worker
    npx wrangler deploy --config wrangler.trading-bot.toml --env "$environment" || {
        log_error "Worker 部署失败"
        return 1
    }
    
    log_success "Worker 部署完成"
    
    # 部署前端 (如果需要)
    if [ "$environment" = "production" ]; then
        log_info "部署前端到 Cloudflare Pages..."
        npx wrangler pages deploy .next --project-name=trading-bot-frontend || {
            log_warning "前端部署失败，但 Worker 已成功部署"
        }
    fi
}

# 运行部署后测试
run_post_deploy_tests() {
    local environment=${1:-"staging"}
    
    log_info "运行部署后测试..."
    
    # 等待服务启动
    sleep 10
    
    # 健康检查
    local worker_url
    if [ "$environment" = "production" ]; then
        worker_url="https://reverse-trading-bot-prod.your-subdomain.workers.dev"
    else
        worker_url="https://reverse-trading-bot-staging.your-subdomain.workers.dev"
    fi
    
    # 简单的健康检查
    if curl -f -s "$worker_url/health" > /dev/null 2>&1; then
        log_success "Worker 健康检查通过"
    else
        log_warning "Worker 健康检查失败，但部署可能仍然成功"
    fi
    
    # 运行 E2E 测试（如果环境允许）
    if [ "$environment" = "staging" ] && [ -f "src/workers/e2e-test.ts" ]; then
        log_info "运行 E2E 测试..."
        timeout 300 pnpm exec tsx src/workers/e2e-test.ts || {
            log_warning "E2E 测试失败或超时"
        }
    fi
}

# 清理函数
cleanup() {
    log_info "清理临时文件..."
    # 清理操作
}

# 显示部署信息
show_deployment_info() {
    local environment=${1:-"staging"}
    
    echo
    log_success "🎉 部署完成！"
    echo
    echo -e "${BLUE}部署信息:${NC}"
    echo "环境: $environment"
    echo "时间: $(date)"
    echo
    echo -e "${BLUE}访问链接:${NC}"
    if [ "$environment" = "production" ]; then
        echo "前端: https://your-domain.com"
        echo "Worker: https://reverse-trading-bot-prod.your-subdomain.workers.dev"
    else
        echo "Worker: https://reverse-trading-bot-staging.your-subdomain.workers.dev"
    fi
    echo
    echo -e "${BLUE}监控:${NC}"
    echo "Cloudflare Dashboard: https://dash.cloudflare.com"
    echo "Worker 日志: npx wrangler tail --config wrangler.trading-bot.toml --env $environment"
    echo
    echo -e "${YELLOW}注意事项:${NC}"
    echo "1. 请在 Telegram 中设置 Webhook 指向 Worker URL"
    echo "2. 监控系统日志确保一切正常运行"
    echo "3. 定期检查策略性能和风险指标"
}

# 主函数
main() {
    local environment=${1:-"staging"}
    local skip_tests=${2:-false}
    
    show_banner
    
    # 设置错误处理
    trap cleanup EXIT
    
    log_info "开始部署到环境: $environment"
    echo
    
    # 执行检查和部署流程
    check_dependencies
    check_node_version
    check_environment
    install_dependencies
    run_type_check
    
    if [ "$skip_tests" != "true" ]; then
        run_tests
    fi
    
    build_project
    validate_wrangler_config
    setup_database
    deploy_to_cloudflare "$environment"
    
    if [ "$skip_tests" != "true" ]; then
        run_post_deploy_tests "$environment"
    fi
    
    show_deployment_info "$environment"
}

# 显示帮助信息
show_help() {
    echo "用法: $0 [环境] [选项]"
    echo
    echo "环境:"
    echo "  staging     部署到测试环境 (默认)"
    echo "  production  部署到生产环境"
    echo
    echo "选项:"
    echo "  --skip-tests  跳过测试"
    echo "  --help        显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0                      # 部署到测试环境"
    echo "  $0 production           # 部署到生产环境"
    echo "  $0 staging --skip-tests # 部署到测试环境并跳过测试"
}

# 解析命令行参数
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

# 处理参数
environment="staging"
skip_tests=false

while [[ $# -gt 0 ]]; do
    case $1 in
        staging|production)
            environment="$1"
            shift
            ;;
        --skip-tests)
            skip_tests=true
            shift
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 执行主函数
main "$environment" "$skip_tests"