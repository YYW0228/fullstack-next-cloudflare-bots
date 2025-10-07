# 🐛 关键 Bug 修复清单

## 🚨 高优先级修复

### Bug #1: OKX 沙盒环境配置错误
**位置：** `src/lib/okx-client.ts:23`
**问题：** 沙盒和生产环境使用相同 URL
```typescript
// ❌ 当前错误代码
this.baseUrl = this.isSandbox ? 'https://www.okx.com' : 'https://www.okx.com';

// ✅ 修复后代码  
this.baseUrl = this.isSandbox ? 'https://www.okx.com' : 'https://www.okx.com';
// 注意：需要添加正确的沙盒 URL
```

### Bug #2: 数据库迁移文件不匹配
**位置：** `src/drizzle/0000_initial_schemas_migration.sql`
**问题：** 缺少交易机器人相关表
**修复：** 需要生成新的迁移文件包含：
- `strategy_instances`
- `simple_positions` 
- `turtle_sequences`
- `turtle_positions`

### Bug #3: Worker 中的异步错误处理
**位置：** `src/workers/reverse-trading-bot.ts:116`
**问题：** catch 块只打印错误，不向 Sentry 报告
```typescript
// ❌ 当前代码
} catch (e) { console.error(`Simple entry failed for ${instance.name}:`, e); }

// ✅ 修复后
} catch (e) { 
    console.error(`Simple entry failed for ${instance.name}:`, e);
    sentry.captureException(e);
}
```

## ⚠️ 中优先级修复

### Bug #4: 时间戳计算可能的精度问题
**位置：** `src/workers/reverse-trading-bot.ts:137`
**问题：** 毫秒计算可能不准确
```typescript
// 当前代码可能有精度问题
else if (Date.now() - new Date(pos.opened_at).getTime() > (config.positionTimeoutHours || 6) * 36e5)

// 建议使用更明确的时间计算
const timeoutMs = (config.positionTimeoutHours || 6) * 60 * 60 * 1000;
const positionAge = Date.now() - new Date(pos.opened_at).getTime();
if (positionAge > timeoutMs)
```

### Bug #5: 数据库查询中的潜在 SQL 注入
**位置：** 多处数据库查询
**问题：** 虽然使用了参数化查询，但部分动态 SQL 需要验证
**建议：** 加强输入验证和 SQL 查询审计