# 🚀 反向跟单机器人 Cloudflare 部署指南

## 第一步：推送到 GitHub

```bash
# 1. 在 GitHub 上创建新仓库 (建议命名: reverse-trading-bot)
# 2. 设置远程仓库
git remote add origin https://github.com/YYW0228/reverse-trading-bot.git

# 3. 推送代码
git branch -M main
git push -u origin main
```

## 第二步：Cloudflare Pages 部署

### 1. 连接 GitHub 仓库
1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **Pages** > **Create a project**
3. 选择 **Connect to Git**
4. 选择您的 GitHub 仓库: `reverse-trading-bot`

### 2. 配置构建设置
```yaml
Framework preset: Next.js
Build command: pnpm run build:cf
Build output directory: .open-next
Root directory: /
```

### 3. 环境变量配置
在 Cloudflare Pages 设置中添加：

```bash
# 必需的环境变量
NEXTJS_ENV=production
BETTER_AUTH_SECRET=your-better-auth-secret
BETTER_AUTH_URL=https://your-domain.pages.dev

# 交易相关
OKX_API_KEY=your-okx-api-key
OKX_SECRET=your-okx-secret  
OKX_PASSPHRASE=your-okx-passphrase
OKX_SANDBOX=true

# Telegram
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_API_ID=your-telegram-api-id
TELEGRAM_API_HASH=your-telegram-api-hash
```

## 第三步：Cloudflare Workers 部署

### 1. 安装 Wrangler CLI
```bash
npm install -g wrangler
wrangler auth login
```

### 2. 创建 D1 数据库
```bash
wrangler d1 create trading-bots-db
# 复制返回的 database_id 到 wrangler.trading-bot.toml
```

### 3. 部署 Worker
```bash
wrangler deploy --config wrangler.trading-bot.toml
```

## 第四步：访问您的应用

- **主应用**: https://reverse-trading-bot.pages.dev
- **交易界面**: https://reverse-trading-bot.pages.dev/trading  
- **API**: https://reverse-trading-bot-worker.your-subdomain.workers.dev

## 第五步：配置 Telegram Webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://reverse-trading-bot-worker.your-subdomain.workers.dev/webhook/telegram"}'
```

## 🎯 部署完成后的测试

1. **访问管理界面**: `/trading`
2. **测试 API**: `/api/trading-bots`
3. **发送测试信号**: 通过 Telegram 群组
4. **查看交易日志**: Cloudflare Dashboard

## 💡 故障排除

### 常见问题：
1. **构建失败**: 检查 Node.js 版本 (需要 18+)
2. **API 错误**: 验证环境变量设置
3. **数据库连接**: 确认 D1 database_id 正确
4. **Webhook 失败**: 检查 Telegram Bot Token

### 调试命令：
```bash
# 本地测试
pnpm dev:cf

# 查看 Worker 日志
wrangler tail

# 测试数据库连接
wrangler d1 execute trading-bots-db --command "SELECT 1"
```

---

🎉 **部署成功后，您的反向跟单机器人将运行在 Cloudflare 全球边缘网络上！**
