#!/bin/bash

# 🚀 部署前全面检查脚本
echo "🔍 开始部署前全面检查..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查计数器
PASS=0
FAIL=0
WARN=0

# 检查函数
check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARN++))
}

echo "📋 1. 检查数据库配置..."
if [ -f "src/drizzle/0000_panoramic_nightmare.sql" ]; then
    check_pass "Migration文件存在"
else
    check_fail "Migration文件缺失"
fi

wrangler d1 execute trading-bots-db --remote --command="SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_cf_%';" --json > /tmp/db_check.json 2>/dev/null
if [ $? -eq 0 ]; then
    TABLE_COUNT=$(cat /tmp/db_check.json | jq -r '.[0].results[0].table_count' 2>/dev/null)
    if [ "$TABLE_COUNT" -ge "4" ]; then
        check_pass "数据库表已正确创建 ($TABLE_COUNT 个表)"
    else
        check_fail "数据库表不足 (只有 $TABLE_COUNT 个表)"
    fi
else
    check_fail "无法连接到远程数据库"
fi

echo ""
echo "📋 2. 检查环境变量配置..."
if [ -f ".dev.vars" ]; then
    check_pass ".dev.vars 文件存在"
    
    # 检查占位符
    PLACEHOLDER_COUNT=$(grep -c "your-.*-here\|your-.*-secret\|your-.*-key\|your-.*-id\|your-.*-token" .dev.vars 2>/dev/null || echo "0")
    if [ "$PLACEHOLDER_COUNT" -eq "0" ]; then
        check_pass "没有发现占位符凭证"
    else
        check_warn "发现 $PLACEHOLDER_COUNT 个占位符凭证需要配置"
    fi
else
    check_fail ".dev.vars 文件不存在"
fi

echo ""
echo "📋 3. 检查Wrangler配置一致性..."
TOML_FILES=("wrangler.toml" "wrangler.prod.toml" "wrangler.trading-bot.toml")
for file in "${TOML_FILES[@]}"; do
    if [ -f "$file" ]; then
        if grep -q "3c71ce69-4ea4-4b0b-933f-6653091cc29b" "$file"; then
            check_pass "$file 使用正确的数据库ID"
        else
            check_fail "$file 数据库ID不正确"
        fi
    else
        check_warn "$file 文件不存在"
    fi
done

echo ""
echo "📋 4. 检查代码质量..."
if ! grep -q "TODO:" src/constants/validation.constant.ts; then
    check_pass "validation.constant.ts 已清理TODO代码"
else
    check_warn "validation.constant.ts 仍有TODO代码"
fi

echo ""
echo "📋 5. 检查构建状态..."
if pnpm build:cf > /dev/null 2>&1; then
    check_pass "项目构建成功"
else
    check_fail "项目构建失败"
fi

echo ""
echo "🎯 检查结果总结:"
echo -e "${GREEN}✅ 通过: $PASS${NC}"
echo -e "${YELLOW}⚠️  警告: $WARN${NC}"
echo -e "${RED}❌ 失败: $FAIL${NC}"

if [ "$FAIL" -eq "0" ]; then
    echo ""
    echo -e "${GREEN}🚀 所有关键检查通过，可以安全部署！${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}🚨 发现 $FAIL 个严重问题，建议修复后再部署${NC}"
    exit 1
fi