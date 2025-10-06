import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";
import { createId } from "@paralleldrive/cuid2";

/**
 * Strategy Instances Table
 *
 * This table stores the configuration for each active strategy instance.
 * A user can have multiple strategy instances for different market pairs.
 * For example, one user can run both a 'simple-reverse' and a 'turtle-reverse'
 * strategy on the 'BTC-USDT-SWAP' market simultaneously.
 */
export const strategyInstances = sqliteTable("strategy_instances", {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    userId: text("user_id").notNull(),
    name: text("name").notNull(), // e.g., "My Simple BTC Bot"
    marketPair: text("market_pair").notNull(), // e.g., "BTC-USDT-SWAP"
    strategyType: text("strategy_type").notNull(), // 'simple-reverse' | 'turtle-reverse'
    status: text("status").notNull().default("stopped"), // 'running' | 'stopped' | 'paused' | 'error'
    
    // JSON string containing strategy-specific parameters.
    // This design allows for maximum flexibility.
    config: text("config", { mode: "json" }).notNull(),
    
    createdAt: integer("created_at", { mode: "timestamp" }).notNull().$defaultFn(() => new Date()),
    updatedAt: integer("updated_at", { mode: "timestamp" }).notNull().$defaultFn(() => new Date()),
});

/**
 * Simple Positions Table
 *
 * Persists the state for each individual position created by the 'simple-reverse' strategy.
 * This is crucial for the stateless Cloudflare Worker environment.
 */
export const simplePositions = sqliteTable("simple_positions", {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    strategyInstanceId: text("strategy_instance_id").references(() => strategyInstances.id, { onDelete: "cascade" }),
    
    // Position details
    side: text("side").notNull(), // Our side: '开多' or '开空'
    size: real("size").notNull(),
    entryPrice: real("entry_price").notNull(),
    
    // State tracking
    status: text("status").notNull().default("active"), // 'active' | 'closing' | 'closed'
    orderId: text("order_id").notNull(),
    openedAt: integer("opened_at", { mode: "timestamp" }).notNull().$defaultFn(() => new Date()),
    closedAt: integer("closed_at", { mode: "timestamp" }),
    
    // PnL and reason for closing
    pnl: real("pnl"),
    closeReason: text("close_reason"), // 'profit_target' | 'stop_loss' | 'timeout' | 'emergency'
});

/**
 * Turtle Sequences Table
 *
 * Persists the state for each trading sequence managed by the 'turtle-reverse' strategy.
 * A sequence is a series of related trades starting from signal quantity 1.
 */
export const turtleSequences = sqliteTable("turtle_sequences", {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    strategyInstanceId: text("strategy_instance_id").references(() => strategyInstances.id, { onDelete: "cascade" }),
    
    // Sequence details
    direction: text("direction").notNull(), // Our direction: 'long' or 'short'
    status: text("status").notNull().default("active"), // 'active' | 'closing' | 'closed'
    
    // State tracking
    currentMaxQuantity: integer("current_max_quantity").notNull().default(0),
    startedAt: integer("started_at", { mode: "timestamp" }).notNull().$defaultFn(() => new Date()),
    closedAt: integer("closed_at", { mode: "timestamp" }),
});

/**
 * Turtle Positions Table
 *
 * Persists the state for each individual position within a turtle sequence.
 * This table has a many-to-one relationship with turtleSequences.
 */
export const turtlePositions = sqliteTable("turtle_positions", {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    sequenceId: text("sequence_id").references(() => turtleSequences.id, { onDelete: "cascade" }),
    
    // Position details
    side: text("side").notNull(), // '开多' or '开空'
    size: real("size").notNull(),
    entryPrice: real("entry_price").notNull(),
    signalQuantity: integer("signal_quantity").notNull(), // The signal number (1, 2, 3...) that triggered this position
    
    // State tracking
    status: text("status").notNull().default("active"), // 'active' | 'partially_closed' | 'closed'
    orderId: text("order_id").notNull(),
    openedAt: integer("opened_at", { mode: "timestamp" }).notNull().$defaultFn(() => new Date()),
});