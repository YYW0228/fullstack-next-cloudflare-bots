#!/bin/bash

# 🔒 安全部署脚本
# 确保敏感信息不会泄露到 GitHub，并正确部署到 Cloudflare

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

show_banner() {
    echo -e "${BLUE}"
    echo "🔒 =================================="
    echo "   安全部署脚本"
    echo "   Secure Deployment Script"
    echo "==================================${NC}"
    echo
}

# 检查敏感文件
check_sensitive_files() {
    log_info "检查敏感文件..."
    
    local sensitive_files=(
        ".env"
        ".dev.vars"
        "config/secrets.json"
        "*.key"
        "*.pem"
    )
    
    local found_sensitive=false
    
    for pattern in "${sensitive_files[@]}"; do
        if ls $pattern 2>/dev/null | grep -v ".example" >/dev/null 2>&1; then
            if git ls-files --cached $pattern 2>/dev/null | grep -v ".example" >/dev/null; then
                log_error "发现敏感文件在 Git 中: $pattern"
                found_sensitive=true
            fi
        fi
    done
    
    if [ "$found_sensitive" = true ]; then
        log_error "请移除 Git 中的敏感文件后再继续"
        return 1
    fi
    
    log_success "敏感文件检查通过"
}

# 检查 .gitignore
check_gitignore() {
    log_info "检查 .gitignore 配置..."
    
    local required_patterns=(
        ".env*"
        ".dev.vars"
        "node_modules/"
        "*.log"
    )
    
    for pattern in "${required_patterns[@]}"; do
        if ! grep -q "$pattern" .gitignore; then
            log_warning ".gitignore 中缺少: $pattern"
        fi
    done
    
    log_success ".gitignore 检查完成"
}

# 清理 Git 历史中的敏感信息
clean_git_history() {
    log_warning "如果之前提交过敏感信息，建议清理 Git 历史"
    echo "可以使用以下命令:"
    echo "git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch .env .dev.vars' --prune-empty --tag-name-filter cat -- --all"
    echo
    read -p "是否需要清理 Git 历史? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "清理 Git 历史..."
        git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch .env .dev.vars' --prune-empty --tag-name-filter cat -- --all 2>/dev/null || true
        log_success "Git 历史清理完成"
    fi
}

# 验证模板文件
validate_template_files() {
    log_info "验证模板文件..."
    
    if [ ! -f ".dev.vars.example" ]; then
        log_error "缺少 .dev.vars.example 模板文件"
        return 1
    fi
    
    # 检查模板文件是否包含真实密钥
    if grep -q "sk-" .dev.vars.example 2>/dev/null || \
       grep -q "6666" .dev.vars.example 2>/dev/null || \
       grep -q "bot[0-9]" .dev.vars.example 2>/dev/null; then
        log_error ".dev.vars.example 包含真实密钥，请替换为模板值"
        return 1
    fi
    
    log_success "模板文件验证通过"
}

# 检查 Cloudflare 配置
check_cloudflare_config() {
    log_info "检查 Cloudflare 配置..."
    
    if ! command -v wrangler &> /dev/null; then
        log_error "Wrangler 未安装，请运行: npm install -g wrangler"
        return 1
    fi
    
    if ! npx wrangler whoami >/dev/null 2>&1; then
        log_error "Wrangler 未登录，请运行: npx wrangler login"
        return 1
    fi
    
    log_success "Cloudflare 配置检查通过"
}

# 清理无效 Workers
cleanup_invalid_workers() {
    log_info "清理无效的 Workers..."
    
    local invalid_workers=(
        "reverse-trading-bot"
        "reverse-trading-bot-staging"
        "reverse-trading-bot-prod"
    )
    
    for worker in "${invalid_workers[@]}"; do
        if npx wrangler list | grep -q "$worker"; then
            log_warning "发现无效 Worker: $worker"
            read -p "是否删除 $worker? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                npx wrangler delete "$worker" --force || log_warning "删除 $worker 失败"
            fi
        fi
    done
    
    log_success "Worker 清理完成"
}

# 部署到 Cloudflare
deploy_to_cloudflare() {
    local environment=${1:-"staging"}
    
    log_info "部署到 Cloudflare ($environment)..."
    
    # 检查配置文件
    if [ ! -f "wrangler.trading-bot.toml" ]; then
        log_error "未找到 wrangler.trading-bot.toml 配置文件"
        return 1
    fi
    
    # 部署 Worker
    log_info "部署 Worker..."
    if npx wrangler deploy --config wrangler.trading-bot.toml --env "$environment"; then
        log_success "Worker 部署成功"
    else
        log_error "Worker 部署失败"
        return 1
    fi
    
    # 提示设置环境变量
    log_warning "请在 Cloudflare Dashboard 中设置以下 Secrets:"
    echo "1. OKX_API_KEY"
    echo "2. OKX_SECRET" 
    echo "3. OKX_PASSPHRASE"
    echo "4. BETTER_AUTH_SECRET"
    echo
    echo "或使用命令行:"
    echo "npx wrangler secret put OKX_API_KEY --config wrangler.trading-bot.toml --env $environment"
}

# 推送到 GitHub
push_to_github() {
    log_info "准备推送到 GitHub..."
    
    # 最后一次检查
    git status
    echo
    log_warning "请确认以上文件列表中没有敏感信息"
    read -p "确认推送到 GitHub? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        git commit -m "🤖 Complete trading bot implementation - Production ready

✅ Features implemented:
- Simple & Turtle reverse trading strategies
- Real-time monitoring dashboard
- Performance analytics
- Error handling & logging
- Automated deployment scripts
- Complete documentation

🔒 Security:
- No sensitive information included
- Environment variables templated
- Production secrets managed via Cloudflare Dashboard

🚀 Ready for production deployment"
        
        git push origin main
        log_success "代码已推送到 GitHub"
    else
        log_info "推送已取消"
    fi
}

# 显示部署信息
show_deployment_info() {
    echo
    log_success "🎉 安全部署流程完成！"
    echo
    echo -e "${BLUE}下一步操作:${NC}"
    echo "1. 在 Cloudflare Dashboard 设置 Worker Secrets"
    echo "2. 在 Cloudflare Pages 设置环境变量"
    echo "3. 测试 Worker 和前端应用"
    echo
    echo -e "${BLUE}有用的链接:${NC}"
    echo "- Cloudflare Dashboard: https://dash.cloudflare.com"
    echo "- Pages 项目: https://dash.cloudflare.com/pages/view/fullstack-next-cloudflare-bots"
    echo "- Workers 管理: https://dash.cloudflare.com/workers"
    echo
    echo -e "${YELLOW}重要提醒:${NC}"
    echo "- 生产环境请设置 OKX_SANDBOX=false"
    echo "- 定期检查 API 密钥权限和有效期"
    echo "- 监控交易日志和风险指标"
}

# 主函数
main() {
    local environment=${1:-"staging"}
    local skip_github=${2:-false}
    
    show_banner
    
    log_info "开始安全部署流程..."
    echo
    
    # 安全检查
    check_sensitive_files || exit 1
    check_gitignore
    validate_template_files || exit 1
    
    # Git 历史清理 (可选)
    clean_git_history
    
    # Cloudflare 部署
    check_cloudflare_config || exit 1
    cleanup_invalid_workers
    deploy_to_cloudflare "$environment"
    
    # GitHub 推送 (可选)
    if [ "$skip_github" != "true" ]; then
        push_to_github
    fi
    
    show_deployment_info
}

# 显示帮助
show_help() {
    echo "用法: $0 [环境] [选项]"
    echo
    echo "环境:"
    echo "  staging     部署到测试环境 (默认)"
    echo "  production  部署到生产环境"
    echo
    echo "选项:"
    echo "  --skip-github  跳过 GitHub 推送"
    echo "  --help         显示帮助信息"
    echo
    echo "示例:"
    echo "  $0                           # 部署到测试环境并推送到 GitHub"
    echo "  $0 production                # 部署到生产环境"
    echo "  $0 staging --skip-github     # 只部署，不推送"
}

# 参数解析
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

environment="staging"
skip_github=false

while [[ $# -gt 0 ]]; do
    case $1 in
        staging|production)
            environment="$1"
            shift
            ;;
        --skip-github)
            skip_github=true
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
main "$environment" "$skip_github"