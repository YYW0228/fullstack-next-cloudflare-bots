#!/bin/bash

# 🔍 数据库状态检查脚本
# 每次修改schema前运行此脚本

echo "🔍 检查数据库migration状态..."

# 1. 检查当前migration文件
echo "📂 当前migration文件:"
ls -la src/drizzle/*.sql 2>/dev/null || echo "  无migration文件"

# 2. 检查远程数据库状态
echo ""
echo "🌐 远程数据库表状态:"
wrangler d1 execute trading-bots-db --remote --command="SELECT name FROM sqlite_master WHERE type='table';" --json | jq -r '.[] | .results[] | .name' 2>/dev/null || echo "  无法连接远程数据库"

# 3. 检查环境变量配置
echo ""
echo "⚙️  环境变量检查:"
if [ -f ".dev.vars" ]; then
    echo "  ✅ .dev.vars 文件存在"
    if grep -q "your-.*-here" .dev.vars; then
        echo "  ⚠️  发现占位符凭证，需要更新"
    else
        echo "  ✅ 凭证已配置"
    fi
else
    echo "  ❌ .dev.vars 文件不存在"
fi

echo ""
echo "🎯 如果要修改schema:"
echo "1. 运行此脚本检查状态"
echo "2. 修改 src/db/schema.ts"  
echo "3. 运行 pnpm db:generate"
echo "4. 检查生成的migration文件"
echo "5. 运行 pnpm db:apply 应用到远程"