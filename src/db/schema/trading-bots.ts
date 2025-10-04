import { sqliteTable, text, integer, real } from 'drizzle-orm/sqlite-core';
import { createId } from '@paralleldrive/cuid2';

// 交易机器人配置表
export const tradingBots = sqliteTable('trading_bots', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  name: text('name').notNull(),
  type: text('type').notNull(), // 'simple-reverse' | 'turtle-reverse'
  status: text('status').notNull().default('stopped'), // 'running' | 'stopped' | 'error' | 'paused'
  config: text('config'), // JSON string of bot configuration
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull().$defaultFn(() => new Date()),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull().$defaultFn(() => new Date()),
  userId: text('user_id').notNull(),
});

// 交易信号表
export const tradingSignals = sqliteTable('trading_signals', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  originalSignal: text('original_signal').notNull(), // '开多', '开空', '平多', '平空'
  reversedSignal: text('reversed_signal').notNull(), // 反向信号
  quantity: integer('quantity').notNull(),
  market: text('market').notNull(), // 'BTC-USDT-SWAP'
  confidence: real('confidence').default(1.0),
  timestamp: integer('timestamp', { mode: 'timestamp' }).notNull().$defaultFn(() => new Date()),
  source: text('source').default('telegram'), // 信号来源
  groupId: text('group_id'), // Telegram 群组ID
  botId: text('bot_id').references(() => tradingBots.id),
});

// 交易执行表
export const tradeExecutions = sqliteTable('trade_executions', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  signalId: text('signal_id').references(() => tradingSignals.id),
  botId: text('bot_id').references(() => tradingBots.id),
  action: text('action').notNull(), // 'OPEN_LONG', 'OPEN_SHORT', 'CLOSE_LONG', 'CLOSE_SHORT'
  quantity: real('quantity').notNull(),
  price: real('price'),
  market: text('market').notNull(),
  orderId: text('order_id'), // 交易所返回的订单ID
  status: text('status').notNull().default('pending'), // 'pending', 'filled', 'cancelled', 'failed'
  executedAt: integer('executed_at', { mode: 'timestamp' }).notNull().$defaultFn(() => new Date()),
  response: text('response'), // JSON string of exchange response
  pnl: real('pnl').default(0), // 盈亏
  fees: real('fees').default(0), // 手续费
});

// 机器人性能表
export const botPerformance = sqliteTable('bot_performance', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  botId: text('bot_id').references(() => tradingBots.id),
  date: text('date').notNull(), // YYYY-MM-DD format
  totalTrades: integer('total_trades').default(0),
  successfulTrades: integer('successful_trades').default(0),
  winRate: real('win_rate').default(0),
  totalPnL: real('total_pnl').default(0),
  dailyPnL: real('daily_pnl').default(0),
  maxDrawdown: real('max_drawdown').default(0),
  volume: real('volume').default(0),
  activePositions: integer('active_positions').default(0),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull().$defaultFn(() => new Date()),
});

// 风险管理记录表
export const riskManagement = sqliteTable('risk_management', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  botId: text('bot_id').references(() => tradingBots.id),
  riskType: text('risk_type').notNull(), // 'daily_loss', 'max_drawdown', 'position_size'
  threshold: real('threshold').notNull(),
  currentValue: real('current_value').notNull(),
  action: text('action').notNull(), // 'warning', 'stop_trading', 'reduce_position'
  triggeredAt: integer('triggered_at', { mode: 'timestamp' }).notNull().$defaultFn(() => new Date()),
  resolved: integer('resolved', { mode: 'boolean' }).default(false),
});

// 历史数据导入表（用于您的10个月数据）
export const historicalData = sqliteTable('historical_data', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  originalSignal: text('original_signal').notNull(),
  quantity: integer('quantity').notNull(),
  market: text('market').notNull(),
  timestamp: integer('timestamp').notNull(),
  orderId: text('order_id'),
  response: text('response'), // 原始JSON响应
  success: integer('success', { mode: 'boolean' }).default(true),
  importedAt: integer('imported_at', { mode: 'timestamp' }).notNull().$defaultFn(() => new Date()),
});

// 系统配置表
export const systemConfig = sqliteTable('system_config', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  key: text('key').notNull().unique(),
  value: text('value').notNull(),
  description: text('description'),
  category: text('category').default('general'),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull().$defaultFn(() => new Date()),
  updatedBy: text('updated_by'),
});
