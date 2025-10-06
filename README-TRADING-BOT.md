# 🤖 反向跟单机器人 (Reverse Trading Bot)

一个基于 Next.js 15、Cloudflare Workers 和 D1 数据库构建的智能交易机器人系统。

## ✨ 核心特性

### 🔄 交易策略
- **简单反向策略**: 快速响应，适合震荡市场
- **海龟反向策略**: 分层止盈，适合趋势市场
- **风险管理**: 智能止盈止损和仓位控制
- **实时监控**: 24/7 自动交易执行

### 📊 监控与分析
- **实时仪表盘**: 交易状态、盈亏、风险指标
- **性能分析**: 详细的图表和统计数据
- **策略对比**: 多策略表现对比分析
- **风险监控**: 回撤分析和风险预警

### 🛡️ 安全与可靠性
- **错误处理**: 完善的错误捕获和恢复机制
- **配置验证**: 自动化的环境和配置检查
- **部署自动化**: 一键部署脚本和环境检查
- **监控告警**: 实时系统状态监控

## 🏗️ 系统架构

```
Frontend (Next.js 15)
    ↓
API Routes (Next.js API)
    ↓
Database (Cloudflare D1)
    ↓
Trading Worker (Cloudflare Worker)
    ↓
OKX Exchange API
```

### 技术栈
- **前端**: Next.js 15, React, TypeScript, Tailwind CSS
- **后端**: Cloudflare Workers, D1 Database
- **交易接口**: OKX API
- **认证**: Better Auth
- **监控**: 自建监控系统 + Sentry 集成
- **部署**: Cloudflare Pages + Workers

## 🚀 快速开始

### 环境要求
- Node.js 18+
- pnpm 8+
- Cloudflare 账户
- OKX 交易所账户

### 1. 克隆项目
```bash
git clone https://github.com/your-repo/reverse-trading-bot.git
cd reverse-trading-bot
```

### 2. 安装依赖
```bash
pnpm install
```

### 3. 环境配置
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

**必需的环境变量：**
```env
# Cloudflare
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_D1_TOKEN=your-d1-token

# OKX API
OKX_API_KEY=your-api-key
OKX_SECRET=your-secret-key
OKX_PASSPHRASE=your-passphrase
OKX_SANDBOX=true

# 认证
BETTER_AUTH_SECRET=your-32-char-secret
BETTER_AUTH_URL=http://localhost:3000
```

### 4. 数据库初始化
```bash
# 创建 D1 数据库
npx wrangler d1 create trading-bots-db

# 运行数据库迁移
npx wrangler d1 execute trading-bots-db --file=src/drizzle/0000_initial_schemas_migration.sql
```

### 5. 启动开发环境
```bash
# 启动前端
pnpm dev

# 启动 Worker (新终端)
pnpm dev:worker
```

### 6. 环境检查
```bash
# 运行完整的环境检查
pnpm exec tsx scripts/check-environment.ts
```

## 📝 策略配置

### 简单反向策略
```json
{
  "name": "BTC 简单反向",
  "marketPair": "BTC-USDT-SWAP",
  "strategyType": "simple-reverse",
  "config": {
    "basePositionSize": 10,
    "maxPositionSize": 100,
    "profitTarget": 0.3,
    "stopLoss": -0.15,
    "positionTimeoutHours": 6,
    "maxConcurrentPositions": 5
  }
}
```

### 海龟反向策略
```json
{
  "name": "ETH 海龟反向",
  "marketPair": "ETH-USDT-SWAP", 
  "strategyType": "turtle-reverse",
  "config": {
    "positionSizes": {
      "1": 10, "2": 20, "3": 30, "4": 40,
      "5": 50, "6": 60, "7": 70, "8": 80
    },
    "profitThresholds": {
      "1": 0.0, "2": 0.0, "3": 0.50, "4": 0.30,
      "5": 0.30, "6": 0.30, "7": 0.30, "8": 0.30
    },
    "closeRatios": {
      "1": 0.0, "2": 0.0, "3": 0.50, "4": 0.80,
      "5": 0.90, "6": 0.90, "7": 0.90, "8": 1.00
    },
    "emergencyStopLoss": -0.20,
    "sequenceTimeoutHours": 8,
    "maxPositionSize": 1000
  }
}
```

## 🔧 部署

### 自动化部署
```bash
# 部署到测试环境
./scripts/deploy-automation.sh staging

# 部署到生产环境  
./scripts/deploy-automation.sh production
```

### 手动部署
```bash
# 构建项目
pnpm build

# 部署 Worker
npx wrangler deploy --config wrangler.trading-bot.toml

# 部署前端
npx wrangler pages deploy .next --project-name=trading-bot-frontend
```

### Telegram Webhook 设置
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://your-worker-domain.workers.dev/webhook/telegram"}'
```

## 📊 监控与维护

### 实时监控
- 访问 `/dashboard` 查看实时交易数据
- 访问 `/trading` 管理策略实例
- 查看 Cloudflare Dashboard 监控 Worker 状态

### 日志查看
```bash
# 实时查看 Worker 日志
npx wrangler tail --config wrangler.trading-bot.toml

# 查看特定时间段的日志
npx wrangler tail --config wrangler.trading-bot.toml --since 1h
```

### 健康检查
```bash
# 检查 Worker 状态
curl https://your-worker-domain.workers.dev/health

# 运行 E2E 测试
pnpm test:e2e
```

## 📚 文档

- [API 文档](docs/API_DOCUMENTATION.md)
- [部署指南](docs/DEPLOYMENT_GUIDE.md) 
- [策略配置详解](docs/STRATEGY_CONFIGURATION.md)

## 🔐 安全注意事项

1. **API 密钥安全**
   - 使用 Wrangler Secrets 存储敏感信息
   - 定期轮换 API 密钥
   - 限制 API 权限范围

2. **网络安全**
   - 启用 HTTPS 强制重定向
   - 配置适当的 CORS 策略
   - 使用 CSP (Content Security Policy)

3. **资金安全**
   - 建议先在沙盒环境测试
   - 设置合理的仓位限制
   - 定期检查交易记录

## 💰 成本估算

### Cloudflare 免费额度
- **Workers**: 100,000 请求/天
- **Pages**: 无限制
- **D1**: 5GB 存储 + 500万行读取/月
- **R2**: 10GB 存储/月

### 预期成本
- **轻度使用**: 完全免费
- **中等使用**: ~$5-10/月
- **重度使用**: ~$20-50/月

## 🐛 故障排除

### 常见问题

**1. Worker 部署失败**
```bash
# 检查配置
npx wrangler whoami
npx wrangler dev --config wrangler.trading-bot.toml
```

**2. 数据库连接失败**
```bash
# 检查数据库状态
npx wrangler d1 info trading-bots-db
```

**3. OKX API 错误**
- 检查 API 凭证是否正确
- 确认 IP 白名单设置
- 验证 API 权限

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发流程
1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## ⚠️ 免责声明

本软件仅供教育和研究目的。数字货币交易存在高风险，可能导致资金损失。使用本软件进行实际交易的风险由用户自行承担。

## 📞 支持

- 📖 [文档](docs/)
- 🐛 [问题反馈](../../issues)
- 💬 [讨论区](../../discussions)

---

**祝您交易顺利！** 🚀📈