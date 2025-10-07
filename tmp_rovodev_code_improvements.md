# 🛠️ 代码品味优化建议

## ❌ 坏味道 #1：数据库 Schema 不一致
**问题：** 迁移文件包含无关表，实际 schema 缺失
**影响：** 部署时数据库结构错误
**修复：** 生成正确的交易机器人表迁移

## ❌ 坏味道 #2：策略分发逻辑复杂化
**问题：** if-else 分支过多，违反开闭原则
**影响：** 新增策略需修改核心逻辑
**修复：** 引入策略工厂模式

## ❌ 坏味道 #3：硬编码配置分散
**问题：** 魔数散布在多处
**影响：** 维护困难，配置不统一
**修复：** 提取配置常量

## ❌ 坏味道 #4：OKX Client 的沙盒 URL 错误
**问题：** 沙盒和生产环境 URL 相同
**影响：** 无法正确区分测试和实盘
**修复：** 修正沙盒 URL

## 🟢 优化后的代码示例：

### 策略工厂模式
```typescript
interface Strategy {
  handleEntry(instance: StrategyInstance, signal: SignalData, env: Env): Promise<void>;
  checkPositions(instance: StrategyInstance, env: Env): Promise<void>;
}

class StrategyFactory {
  private strategies = new Map<string, Strategy>([
    ['simple-reverse', new SimpleReverseStrategy()],
    ['turtle-reverse', new TurtleReverseStrategy()],
  ]);
  
  getStrategy(type: string): Strategy {
    const strategy = this.strategies.get(type);
    if (!strategy) throw new Error(`Unknown strategy: ${type}`);
    return strategy;
  }
}
```

### 配置常量提取
```typescript
export const TRADING_CONFIG = {
  SIMPLE_REVERSE: {
    DEFAULT_BASE_POSITION_SIZE: 10,
    DEFAULT_MAX_POSITION_SIZE: 100,
    DEFAULT_PROFIT_TARGET: 0.3,
    DEFAULT_STOP_LOSS: -0.15,
    DEFAULT_TIMEOUT_HOURS: 6,
    DEFAULT_MAX_CONCURRENT: 5,
  },
  TURTLE_REVERSE: {
    POSITION_SIZES: { 1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60, 7: 70, 8: 80 },
    PROFIT_THRESHOLDS: { 1: 0.0, 2: 0.0, 3: 0.50, 4: 0.30, 5: 0.30, 6: 0.30, 7: 0.30, 8: 0.30 },
    CLOSE_RATIOS: { 1: 0.0, 2: 0.0, 3: 0.50, 4: 0.80, 5: 0.90, 6: 0.90, 7: 0.90, 8: 1.00 },
    DEFAULT_EMERGENCY_STOP: -0.20,
    DEFAULT_TIMEOUT_HOURS: 8,
  }
} as const;
```