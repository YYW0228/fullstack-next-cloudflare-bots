import { Toucan } from 'toucan-js';
import { OKXClient } from '@/lib/okx-client';
// Type for strategy instance
type StrategyInstance = {
    id: string;
    name: string;
    marketPair: string;
    strategyType: string;
    config: any;
    status: string;
};

// --- Type Definitions ---
interface Env {
    TRADING_BOTS_DB: D1Database;
    OKX_API_KEY: string;
    OKX_SECRET: string;
    OKX_PASSPHRASE: string;
    OKX_SANDBOX: string;
    SENTRY_DSN?: string;
}

// --- Main Worker Logic ---
export default {
    async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
        const sentry = new Toucan({ dsn: env.SENTRY_DSN, context: ctx, request });
        try {
            const url = new URL(request.url);
            if (url.pathname === '/webhook/telegram' && request.method === 'POST') {
                const body = await request.json<{ message?: { text?: string } }>();
                const signalText = body.message?.text;
                if (!signalText) return new Response('Invalid request', { status: 400 });
                ctx.waitUntil(processSignal(signalText, env));
                return new Response('Signal received', { status: 202 });
            }
            return new Response('Not found', { status: 404 });
        } catch (err) {
            sentry.captureException(err);
            return new Response('Internal Server Error', { status: 500 });
        }
    },

    async scheduled(controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
        const sentry = new Toucan({ dsn: env.SENTRY_DSN, context: ctx });
        try {
            console.log('Cron job started: Checking active strategies...');
            const { results: activeInstances } = await env.TRADING_BOTS_DB.prepare(
                "SELECT * FROM strategy_instances WHERE status = ?"
            ).bind('running').all<StrategyInstance>();

            if (!activeInstances || activeInstances.length === 0) {
                console.log('No active strategies to check.');
                return;
            }

            const promises = activeInstances.map(instance => {
                if (instance.strategyType === 'simple-reverse') return checkSimpleReversePositions(instance, env);
                if (instance.strategyType === 'turtle-reverse') return checkTurtleReverseSequences(instance, env);
                return Promise.resolve();
            });
            await Promise.all(promises);
            console.log(`Cron job finished: Checked ${activeInstances.length} strategies.`);
        } catch (err) {
            sentry.captureException(err);
        }
    },
};

// --- Signal Processing & Strategy Logic ---

async function processSignal(signalText: string, env: Env) {
    const parsedSignal = parseSignalText(signalText);
    if (!parsedSignal) return;

    const { action, marketPair } = parsedSignal;
    const { results: instances } = await env.TRADING_BOTS_DB.prepare(
        "SELECT * FROM strategy_instances WHERE status = ? AND market_pair = ?"
    ).bind('running', marketPair).all<StrategyInstance>();

    if (!instances || instances.length === 0) return;

    const promises = instances.map(instance => {
        if (action === 'open') {
            if (instance.strategyType === 'simple-reverse') return handleSimpleReverseEntry(instance, parsedSignal, env);
            if (instance.strategyType === 'turtle-reverse') return handleTurtleReverseEntry(instance, parsedSignal, env);
        } else if (action === 'close') {
            // Handle control handover for close signals
            return handleControlHandover(instance, parsedSignal, env);
        }
        return Promise.resolve();
    });
    await Promise.all(promises);
}

async function handleSimpleReverseEntry(instance: StrategyInstance, signal: any, env: Env) {
    const config = instance.config as any;
    const { results: activePositions } = await env.TRADING_BOTS_DB.prepare(
        "SELECT id FROM simple_positions WHERE strategy_instance_id = ? AND status = ?"
    ).bind(instance.id, 'active').all();

    if (activePositions.length >= (config.maxConcurrentPositions || 5)) return;

    const positionSize = Math.round(Math.min((config.basePositionSize || 10) * signal.quantity, config.maxPositionSize || 100) * 10) / 10;
    const reverseSide = signal.side === 'long' ? 'sell' : 'buy';
    const okx = new OKXClient(env);

    try {
        const order = await okx.placeMarketOrder(instance.marketPair, reverseSide, positionSize);
        if (order.code !== '0') throw new Error(order.sMsg);
        const orderId = order.data[0].ordId;
        const details = await okx.getOrderDetails(instance.marketPair, orderId);
        
        await env.TRADING_BOTS_DB.prepare(
            `INSERT INTO simple_positions (strategy_instance_id, side, size, entry_price, status, order_id) VALUES (?, ?, ?, ?, ?, ?)`
        ).bind(instance.id, signal.side === 'long' ? '开空' : '开多', positionSize, details.avgPx, 'active', orderId).run();

    } catch (e) { console.error(`Simple entry failed for ${instance.name}:`, e); }
}

async function checkSimpleReversePositions(instance: StrategyInstance, env: Env) {
    const { results: positions } = await env.TRADING_BOTS_DB.prepare(
        "SELECT * FROM simple_positions WHERE strategy_instance_id = ? AND status = ?"
    ).bind(instance.id, 'active').all<any>();

    if (!positions || positions.length === 0) return;

    const okx = new OKXClient(env);
    try {
        const price = await okx.getMarkPrice(instance.marketPair);
        for (const pos of positions) {
            if (pos.entry_price <= 0) continue;
            const pnl = (pos.side === '开多') ? (price - pos.entry_price) / pos.entry_price : (pos.entry_price - price) / pos.entry_price;
            
            let reason: string | null = null;
            const config = instance.config as any;
            if (pnl >= (config.profitTarget || 0.3)) reason = 'profit_target';
            else if (pnl <= (config.stopLoss || -0.15)) reason = 'stop_loss';
            else if (Date.now() - new Date(pos.opened_at).getTime() > (config.positionTimeoutHours || 6) * 36e5) reason = 'timeout';

            if (reason) {
                await okx.placeMarketOrder(instance.marketPair, pos.side === '开多' ? 'sell' : 'buy', pos.size);
                await env.TRADING_BOTS_DB.prepare(
                    `UPDATE simple_positions SET status = 'closed', closed_at = ?, close_reason = ?, pnl = ? WHERE id = ?`
                ).bind(new Date().toISOString(), reason, pnl * pos.entry_price * pos.size, pos.id).run();
            }
        }
    } catch (e) { console.error(`Check simple positions failed for ${instance.name}:`, e); }
}

function parseSignalText(text: string) {
    const openMatch = text.match(/\[(开多|开空)\]\s+数量:(\d+)\s+市场:([\w-]+)/);
    if (openMatch) return { action: 'open', side: openMatch[1] === '开多' ? 'long' : 'short', quantity: parseInt(openMatch[2], 10), marketPair: openMatch[3] };
    const closeMatch = text.match(/\[(平多|平空)\]/);
    if (closeMatch) return { action: 'close', side: closeMatch[1] === '平多' ? 'long' : 'short', quantity: 0, marketPair: '*' };
    return null;
}

// === TURTLE REVERSE STRATEGY IMPLEMENTATION ===

async function handleTurtleReverseEntry(instance: StrategyInstance, signal: any, env: Env) {
    const config = instance.config as any;
    const { action, marketPair, quantity } = signal;
    
    // Get turtle strategy parameters
    const positionSizes = config.positionSizes || { 1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60, 7: 70, 8: 80 };
    const signalQuantity = parseInt(quantity, 10);
    
    // Determine our reverse direction
    const originalDirection = action === 'open' && signal.side === 'long' ? 'long' : 'short';
    const reverseDirection = originalDirection === 'long' ? 'short' : 'long';
    const reverseSide = originalDirection === 'long' ? 'sell' : 'buy';
    const ourSide = originalDirection === 'long' ? '开空' : '开多';
    
    try {
        // Find or create active sequence for this direction
        const { results: existingSequences } = await env.TRADING_BOTS_DB.prepare(
            `SELECT * FROM turtle_sequences WHERE strategy_instance_id = ? AND status = 'active' 
             AND direction = ? AND datetime(started_at) > datetime('now', '-8 hours')`
        ).bind(instance.id, reverseDirection).all<any>();
        
        let sequenceId: string;
        let currentMaxQuantity = 0;
        
        if (existingSequences && existingSequences.length > 0) {
            // Use existing sequence
            const sequence = existingSequences[0];
            sequenceId = sequence.id;
            currentMaxQuantity = sequence.current_max_quantity;
            
            // Check if we already have a position for this signal quantity
            const { results: existingPositions } = await env.TRADING_BOTS_DB.prepare(
                `SELECT id FROM turtle_positions WHERE sequence_id = ? AND signal_quantity = ? AND status = 'active'`
            ).bind(sequenceId, signalQuantity).all();
            
            if (existingPositions && existingPositions.length > 0) {
                console.log(`Turtle sequence ${sequenceId} already has position for quantity ${signalQuantity}`);
                return;
            }
        } else {
            // Create new sequence
            sequenceId = `turtle_${reverseDirection}_${Date.now()}`;
            await env.TRADING_BOTS_DB.prepare(
                `INSERT INTO turtle_sequences (id, strategy_instance_id, direction, status, current_max_quantity, started_at) 
                 VALUES (?, ?, ?, 'active', ?, ?)`
            ).bind(sequenceId, instance.id, reverseDirection, 0, new Date().toISOString()).run();
            console.log(`Created new turtle sequence: ${sequenceId}`);
        }
        
        // Calculate position size based on signal quantity
        const basePositionSize = positionSizes[signalQuantity] || signalQuantity * 10;
        const positionSize = Math.round(Math.min(basePositionSize, config.maxPositionSize || 1000) * 10) / 10;
        
        if (positionSize <= 0) return;
        
        // Execute reverse order
        const okx = new OKXClient(env);
        const order = await okx.placeMarketOrder(marketPair, reverseSide, positionSize);
        
        if (order.code !== '0') {
            console.error(`Turtle order failed: ${order.sMsg}`);
            return;
        }
        
        const orderId = order.data[0].ordId;
        const details = await okx.getOrderDetails(marketPair, orderId);
        
        // Create turtle position record
        const positionId = `turtle_pos_${Date.now()}`;
        await env.TRADING_BOTS_DB.prepare(
            `INSERT INTO turtle_positions (id, sequence_id, side, size, entry_price, signal_quantity, status, order_id, opened_at) 
             VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)`
        ).bind(positionId, sequenceId, ourSide, positionSize, details.avgPx, signalQuantity, orderId, new Date().toISOString()).run();
        
        // Update sequence max quantity
        const newMaxQuantity = Math.max(currentMaxQuantity, signalQuantity);
        await env.TRADING_BOTS_DB.prepare(
            `UPDATE turtle_sequences SET current_max_quantity = ? WHERE id = ?`
        ).bind(newMaxQuantity, sequenceId).run();
        
        console.log(`Turtle reverse entry: ${ourSide} ${positionSize} ${marketPair} at ${details.avgPx} (quantity ${signalQuantity})`);
        
    } catch (e) {
        console.error(`Turtle reverse entry failed for ${instance.name}:`, e);
    }
}

async function checkTurtleReverseSequences(instance: StrategyInstance, env: Env) {
    const config = instance.config as any;
    
    // Get turtle strategy parameters
    const profitThresholds = config.profitThresholds || { 1: 0.0, 2: 0.0, 3: 0.50, 4: 0.30, 5: 0.30, 6: 0.30, 7: 0.30, 8: 0.30 };
    const closeRatios = config.closeRatios || { 1: 0.0, 2: 0.0, 3: 0.50, 4: 0.80, 5: 0.90, 6: 0.90, 7: 0.90, 8: 1.00 };
    const emergencyStopLoss = config.emergencyStopLoss || -0.20;
    
    try {
        // Get all active turtle sequences for this instance
        const { results: activeSequences } = await env.TRADING_BOTS_DB.prepare(
            `SELECT * FROM turtle_sequences WHERE strategy_instance_id = ? AND status = 'active'`
        ).bind(instance.id).all<any>();
        
        if (!activeSequences || activeSequences.length === 0) return;
        
        const okx = new OKXClient(env);
        const currentPrice = await okx.getMarkPrice(instance.marketPair);
        
        for (const sequence of activeSequences) {
            // Check if sequence is too old (timeout)
            const sequenceAge = Date.now() - new Date(sequence.started_at).getTime();
            const timeoutHours = config.sequenceTimeoutHours || 8;
            if (sequenceAge > timeoutHours * 3600000) {
                await closeEntireSequence(sequence.id, 'sequence_timeout', env);
                continue;
            }
            
            // Get all active positions in this sequence
            const { results: positions } = await env.TRADING_BOTS_DB.prepare(
                `SELECT * FROM turtle_positions WHERE sequence_id = ? AND status = 'active'`
            ).bind(sequence.id).all<any>();
            
            if (!positions || positions.length === 0) {
                // Mark sequence as closed if no active positions
                await env.TRADING_BOTS_DB.prepare(
                    `UPDATE turtle_sequences SET status = 'closed', closed_at = ? WHERE id = ?`
                ).bind(new Date().toISOString(), sequence.id).run();
                continue;
            }
            
            // Calculate sequence total PnL
            let totalPnl = 0;
            let totalInvested = 0;
            
            for (const pos of positions) {
                if (pos.entry_price <= 0) continue;
                
                const pnl = (pos.side === '开多') ? 
                    (currentPrice - pos.entry_price) / pos.entry_price : 
                    (pos.entry_price - currentPrice) / pos.entry_price;
                
                const positionValue = pos.entry_price * pos.size;
                totalPnl += pnl * positionValue;
                totalInvested += positionValue;
            }
            
            if (totalInvested <= 0) continue;
            
            const pnlPercentage = totalPnl / totalInvested;
            
            // Check emergency stop loss
            if (pnlPercentage <= emergencyStopLoss) {
                console.log(`Emergency stop loss triggered for sequence ${sequence.id}: ${(pnlPercentage * 100).toFixed(2)}%`);
                await closeEntireSequence(sequence.id, 'emergency_stop_loss', env);
                continue;
            }
            
            // Check partial profit taking based on current max quantity
            const currentMaxQuantity = sequence.current_max_quantity;
            const profitThreshold = profitThresholds[currentMaxQuantity] || 0.30;
            const closeRatio = closeRatios[currentMaxQuantity] || 0.0;
            
            if (profitThreshold > 0 && closeRatio > 0 && pnlPercentage >= profitThreshold) {
                console.log(`Partial profit taking for sequence ${sequence.id}: ${(pnlPercentage * 100).toFixed(2)}% >= ${(profitThreshold * 100).toFixed(0)}%`);
                await executePartialProfitTaking(sequence.id, closeRatio, instance.marketPair, env);
            }
        }
        
    } catch (e) {
        console.error(`Check turtle sequences failed for ${instance.name}:`, e);
    }
}

async function executePartialProfitTaking(sequenceId: string, closeRatio: number, marketPair: string, env: Env) {
    try {
        const { results: positions } = await env.TRADING_BOTS_DB.prepare(
            `SELECT * FROM turtle_positions WHERE sequence_id = ? AND status = 'active'`
        ).bind(sequenceId).all<any>();
        
        if (!positions || positions.length === 0) return;
        
        const okx = new OKXClient(env);
        
        for (const pos of positions) {
            const closeSize = Math.round(pos.size * closeRatio * 10) / 10;
            if (closeSize <= 0) continue;
            
            const closeSide = pos.side === '开多' ? 'sell' : 'buy';
            
            try {
                const closeOrder = await okx.placeMarketOrder(marketPair, closeSide, closeSize);
                if (closeOrder.code === '0') {
                    const closeDetails = await okx.getOrderDetails(marketPair, closeOrder.data[0].ordId);
                    const remainingSize = pos.size - closeSize;
                    
                    if (remainingSize <= 0.001) {
                        // Close position completely
                        await env.TRADING_BOTS_DB.prepare(
                            `UPDATE turtle_positions SET status = 'closed' WHERE id = ?`
                        ).bind(pos.id).run();
                    } else {
                        // Update position size
                        await env.TRADING_BOTS_DB.prepare(
                            `UPDATE turtle_positions SET size = ? WHERE id = ?`
                        ).bind(remainingSize, pos.id).run();
                    }
                    
                    console.log(`Partial close: ${pos.side} -${closeSize} (${(closeRatio * 100).toFixed(0)}%) at ${closeDetails.avgPx}`);
                }
            } catch (e) {
                console.error(`Failed to partial close position ${pos.id}:`, e);
            }
        }
        
    } catch (e) {
        console.error(`Partial profit taking failed for sequence ${sequenceId}:`, e);
    }
}

async function closeEntireSequence(sequenceId: string, reason: string, env: Env) {
    try {
        // Get all active positions in sequence
        const { results: positions } = await env.TRADING_BOTS_DB.prepare(
            `SELECT tp.*, ts.strategy_instance_id, si.market_pair 
             FROM turtle_positions tp 
             JOIN turtle_sequences ts ON tp.sequence_id = ts.id 
             JOIN strategy_instances si ON ts.strategy_instance_id = si.id 
             WHERE tp.sequence_id = ? AND tp.status = 'active'`
        ).bind(sequenceId).all<any>();
        
        if (!positions || positions.length === 0) {
            // Just mark sequence as closed
            await env.TRADING_BOTS_DB.prepare(
                `UPDATE turtle_sequences SET status = 'closed', closed_at = ? WHERE id = ?`
            ).bind(new Date().toISOString(), sequenceId).run();
            return;
        }
        
        const okx = new OKXClient(env);
        
        for (const pos of positions) {
            const closeSide = pos.side === '开多' ? 'sell' : 'buy';
            
            try {
                const closeOrder = await okx.placeMarketOrder(pos.market_pair, closeSide, pos.size);
                if (closeOrder.code === '0') {
                    await env.TRADING_BOTS_DB.prepare(
                        `UPDATE turtle_positions SET status = 'closed' WHERE id = ?`
                    ).bind(pos.id).run();
                    console.log(`Closed turtle position: ${pos.side} -${pos.size} reason: ${reason}`);
                }
            } catch (e) {
                console.error(`Failed to close turtle position ${pos.id}:`, e);
            }
        }
        
        // Mark sequence as closed
        await env.TRADING_BOTS_DB.prepare(
            `UPDATE turtle_sequences SET status = 'closed', closed_at = ? WHERE id = ?`
        ).bind(new Date().toISOString(), sequenceId).run();
        
        console.log(`Turtle sequence ${sequenceId} closed completely: ${reason}`);
        
    } catch (e) {
        console.error(`Failed to close turtle sequence ${sequenceId}:`, e);
    }
}

// === EMERGENCY CONTROL HANDOVER IMPLEMENTATION ===

async function handleControlHandover(instance: StrategyInstance, signal: any, env: Env) {
    console.log(`Control handover triggered for ${instance.name}: ${signal.action} signal detected`);
    
    try {
        // Close all simple positions for this instance
        const { results: simplePositions } = await env.TRADING_BOTS_DB.prepare(
            `SELECT * FROM simple_positions WHERE strategy_instance_id = ? AND status = 'active'`
        ).bind(instance.id).all<any>();
        
        if (simplePositions && simplePositions.length > 0) {
            const okx = new OKXClient(env);
            
            for (const pos of simplePositions) {
                const closeSide = pos.side === '开多' ? 'sell' : 'buy';
                
                try {
                    await okx.placeMarketOrder(instance.marketPair, closeSide, pos.size);
                    await env.TRADING_BOTS_DB.prepare(
                        `UPDATE simple_positions SET status = 'closed', closed_at = ?, close_reason = 'control_handover' WHERE id = ?`
                    ).bind(new Date().toISOString(), pos.id).run();
                    console.log(`Control handover closed simple position: ${pos.side} -${pos.size}`);
                } catch (e) {
                    console.error(`Failed to close simple position during handover:`, e);
                }
            }
        }
        
        // Close all turtle sequences for this instance
        const { results: turtleSequences } = await env.TRADING_BOTS_DB.prepare(
            `SELECT id FROM turtle_sequences WHERE strategy_instance_id = ? AND status = 'active'`
        ).bind(instance.id).all<any>();
        
        if (turtleSequences && turtleSequences.length > 0) {
            for (const seq of turtleSequences) {
                await closeEntireSequence(seq.id, 'control_handover', env);
            }
        }
        
        console.log(`Control handover completed for ${instance.name}: all positions closed`);
        
    } catch (e) {
        console.error(`Control handover failed for ${instance.name}:`, e);
    }
}