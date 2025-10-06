# 🚀 完整部署指南

## 概览

本指南将引导您完成反向跟单机器人的完整部署流程，从开发环境到生产环境。

## 前置要求

### 必需服务
- [Cloudflare 账户](https://dash.cloudflare.com/) (免费版即可)
- [OKX 交易所账户](https://www.okx.com/) 
- [Node.js 18+](https://nodejs.org/)
- [pnpm](https://pnpm.io/) 包管理器

### 建议工具
- [Git](https://git-scm.com/)
- [VS Code](https://code.visualstudio.com/) + TypeScript 扩展

## 第一步：克隆和环境准备

```bash
# 克隆项目
git clone <repository-url>
cd fullstack-next-cloudflare-bots

# 安装依赖
pnpm install

# 复制环境变量模板
cp .dev.vars.example .dev.vars
```

## 第二步：Cloudflare 配置

### 2.1 创建 D1 数据库

```bash
# 登录 Cloudflare
npx wrangler login

# 创建 D1 数据库
npx wrangler d1 create trading-bots-db
```

记录输出的 `database_id`，更新 `wrangler.trading-bot.toml`:

```toml
[[d1_databases]]
binding = "TRADING_BOTS_DB"
database_name = "trading-bots-db"
database_id = "your-database-id-here"  # 替换为实际 ID
```

### 2.2 初始化数据库架构

```bash
# 运行数据库迁移
npx wrangler d1 execute trading-bots-db --local --file=src/drizzle/0000_initial_schemas_migration.sql

# 对生产数据库也运行迁移
npx wrangler d1 execute trading-bots-db --file=src/drizzle/0000_initial_schemas_migration.sql
```

### 2.3 创建 R2 存储桶 (可选)

```bash
# 创建 R2 存储桶用于日志存储
npx wrangler r2 bucket create trading-logs-bucket
```

### 2.4 创建 KV 命名空间 (可选)

```bash
# 创建 KV 命名空间用于缓存
npx wrangler kv:namespace create "BOT_STATUS"
```

记录 `id` 并更新 `wrangler.trading-bot.toml`。

## 第三步：OKX API 配置

### 3.1 获取 API 凭证

1. 登录 [OKX](https://www.okx.com/)
2. 进入 **设置** → **API 管理**
3. 创建新的 API Key，权限设置为 **Trade**
4. 记录以下信息：
   - API Key
   - Secret Key  
   - Passphrase

### 3.2 配置环境变量

编辑 `.dev.vars` 文件：

```bash
# OKX API 凭证
OKX_API_KEY=your-api-key
OKX_SECRET=your-secret-key
OKX_PASSPHRASE=your-passphrase
OKX_SANDBOX=true  # 开发环境使用沙盒

# 认证配置
BETTER_AUTH_SECRET=your-very-long-random-secret-key-here
BETTER_AUTH_URL=http://localhost:3000

# Google OAuth (可选)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Cloudflare 凭证 (用于数据库管理)
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_D1_TOKEN=your-d1-token
```

## 第四步：本地开发环境

### 4.1 启动开发服务器

```bash
# 启动 Next.js 开发服务器
pnpm dev

# 在另一个终端启动 Worker 开发环境
pnpm dev:worker
```

### 4.2 测试基本功能

1. 访问 http://localhost:3000
2. 注册/登录用户账户
3. 创建一个测试策略实例
4. 检查数据库是否正确创建记录

### 4.3 测试 Worker 功能

```bash
# 运行 E2E 测试
pnpm test:e2e

# 手动测试 Webhook
curl -X POST http://localhost:8787/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{"message":{"text":"[开多] 数量:1 市场:BTC-USDT-SWAP"}}'
```

## 第五步：生产部署

### 5.1 配置生产环境变量

在 Cloudflare Dashboard 中设置以下 Secrets：

```bash
# 为 Worker 设置 secrets
npx wrangler secret put OKX_API_KEY
npx wrangler secret put OKX_SECRET  
npx wrangler secret put OKX_PASSPHRASE
npx wrangler secret put BETTER_AUTH_SECRET

# 设置生产环境变量
npx wrangler secret put OKX_SANDBOX --text "false"
```

### 5.2 部署前端 (Pages)

```bash
# 构建前端
pnpm build

# 部署到 Cloudflare Pages
npx wrangler pages deploy .next --project-name=trading-bot-frontend
```

### 5.3 部署 Worker

```bash
# 部署交易 Worker
npx wrangler deploy --config wrangler.trading-bot.toml

# 验证部署
npx wrangler tail --config wrangler.trading-bot.toml
```

### 5.4 配置自定义域名 (可选)

1. 在 Cloudflare Dashboard 中添加您的域名
2. 为 Pages 和 Worker 配置自定义路由
3. 更新 DNS 记录

## 第六步：生产验证

### 6.1 健康检查

```bash
# 检查 Worker 状态
curl https://your-worker-domain.workers.dev/health

# 检查前端应用
curl https://your-domain.com/api/health
```

### 6.2 日志监控

```bash
# 实时查看 Worker 日志
npx wrangler tail --config wrangler.trading-bot.toml

# 查看特定时间段的日志
npx wrangler tail --config wrangler.trading-bot.toml --since 1h
```

### 6.3 配置 Telegram Webhook

如果使用 Telegram 信号：

```bash
# 设置 Telegram Webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://your-worker-domain.workers.dev/webhook/telegram"}'
```

## 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查数据库配置
npx wrangler d1 info trading-bots-db

# 重新运行迁移
npx wrangler d1 execute trading-bots-db --file=src/drizzle/0000_initial_schemas_migration.sql
```

#### 2. OKX API 错误
- 检查 API 凭证是否正确
- 确认 IP 白名单设置（如果启用）
- 验证 API 权限设置

#### 3. Worker 部署失败
```bash
# 检查配置文件
npx wrangler whoami
npx wrangler dev --config wrangler.trading-bot.toml

# 查看详细错误信息
npx wrangler deploy --config wrangler.trading-bot.toml --verbose
```

#### 4. 前端构建失败
```bash
# 清理缓存重新构建
rm -rf .next node_modules
pnpm install
pnpm build
```

### 日志分析

重要的日志文件位置：
- Worker 日志: Cloudflare Dashboard → Workers → Logs
- 构建日志: Cloudflare Dashboard → Pages → Deployments
- 本地日志: `.wrangler/logs/`

### 性能优化

#### 1. Worker 优化
- 启用 Smart Placement
- 配置适当的 CPU 限制
- 使用 Durable Objects (如需要)

#### 2. Pages 优化
- 启用自动压缩
- 配置缓存策略
- 使用 CDN 加速

#### 3. 数据库优化
- 创建适当的索引
- 定期清理旧数据
- 监控查询性能

## 安全最佳实践

### 1. API 密钥管理
- 使用 Wrangler Secrets 存储敏感信息
- 定期轮换 API 密钥
- 限制 API 权限范围

### 2. 网络安全
- 启用 HTTPS 强制重定向
- 配置适当的 CORS 策略
- 使用 CSP (Content Security Policy)

### 3. 访问控制
- 实施适当的身份验证
- 使用角色基础的访问控制
- 记录所有敏感操作

## 监控和维护

### 1. 监控指标
- Worker 执行时间和错误率
- 数据库查询性能
- API 调用成功率
- 交易执行统计

### 2. 告警设置
```bash
# 设置 Cloudflare 告警
# 通过 Dashboard 配置或使用 API
```

### 3. 备份策略
```bash
# 定期备份数据库
npx wrangler d1 export trading-bots-db --output backup-$(date +%Y%m%d).sql

# 备份配置文件
git add . && git commit -m "Config backup $(date)"
```

## 成本估算

### Cloudflare 服务 (免费额度)
- **Workers**: 100,000 请求/天
- **Pages**: 无限制
- **D1**: 5GB 存储 + 500万行读取/月
- **R2**: 10GB 存储/月

### 预期使用量
- 轻度使用: 完全在免费额度内
- 中等使用: ~$5-10/月
- 重度使用: ~$20-50/月

## 下一步

部署完成后，您可以：

1. **配置交易策略**: 在 Web 界面中创建和配置策略
2. **设置监控**: 配置告警和监控面板
3. **优化性能**: 根据使用情况调整配置
4. **扩展功能**: 添加更多交易策略或市场

---

## 支持和社区

- 📖 [官方文档](./API_DOCUMENTATION.md)
- 🐛 [问题反馈](../../issues)
- 💬 [讨论区](../../discussions)
- 📧 技术支持: support@your-domain.com

**祝您交易顺利！** 🚀