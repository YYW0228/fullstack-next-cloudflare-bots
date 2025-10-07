#!/bin/bash
# 修复部署问题的脚本

echo "🔧 修复 Worker 部署问题..."

# 1. 使用正确的配置文件重新部署 staging
echo "📦 重新部署 staging 环境..."
wrangler deploy --config wrangler.trading-bot.toml --env staging

# 2. 检查部署状态
echo "✅ 检查部署状态..."
wrangler deployments list --name reverse-trading-bot-staging

echo "🎯 修复完成！"