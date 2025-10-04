/**
 * Cloudflare Worker for Reverse Trading Bot
 * 反向跟单机器人 - 边缘计算核心逻辑
 * 
 * 部署在 Cloudflare 全球300+节点，实现超低延迟的反向跟单
 */

interface Env {
  // Cloudflare bindings
  TRADING_BOTS_DB: D1Database;
  TRADING_LOGS: R2Bucket;
  
  // API Keys
  OKX_API_KEY: string;
  OKX_SECRET: string;
  OKX_PASSPHRASE: string;
  OKX_SANDBOX: string;
  
  // Telegram
  TELEGRAM_BOT_TOKEN: string;
  TELEGRAM_API_ID: string;
  TELEGRAM_API_HASH: string;
  
  // Trading Config
  DEFAULT_MARKET: string;
  DEFAULT_QUANTITY: string;
  REVERSE_TRADING_ENABLED: string;
}

// 反向信号转换核心逻辑
const reverseSignalMapping = {
  '开多': 'OPEN_SHORT',
  '开空': 'OPEN_LONG', 
  '平多': 'CLOSE_SHORT',
  '平空': 'CLOSE_LONG'
} as const;

// OKX API 客户端
class OKXClient {
  private apiKey: string;
  private secret: string;
  private passphrase: string;
  private sandbox: boolean;
  
  constructor(env: Env) {
    this.apiKey = env.OKX_API_KEY;
    this.secret = env.OKX_SECRET;
    this.passphrase = env.OKX_PASSPHRASE;
    this.sandbox = env.OKX_SANDBOX === 'true';
  }
  
  private getBaseUrl(): string {
    return this.sandbox 
      ? 'https://www.okx.com/api/v5' 
      : 'https://www.okx.com/api/v5';
  }
  
  private async sign(timestamp: string, method: string, requestPath: string, body: string = ''): Promise<string> {
    const message = timestamp + method + requestPath + body;
    const key = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(this.secret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );
    
    const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
    return btoa(String.fromCharCode(...new Uint8Array(signature)));
  }
  
  async placeOrder(action: string, market: string, quantity: number): Promise<any> {
    const timestamp = new Date().toISOString();
    const requestPath = '/api/v5/trade/order';
    
    // 构造订单参数
    const orderSide = action.includes('LONG') ? 'buy' : 'sell';
    const orderType = action.includes('OPEN') ? 'market' : 'market';
    
    const body = JSON.stringify({
      instId: market,
      tdMode: 'cross', // 全仓模式
      side: orderSide,
      ordType: orderType,
      sz: quantity.toString(),
      ccy: 'USDT'
    });
    
    const signature = await this.sign(timestamp, 'POST', requestPath, body);
    
    const response = await fetch(this.getBaseUrl() + requestPath, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'OK-ACCESS-KEY': this.apiKey,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': this.passphrase,
        'x-simulated-trading': this.sandbox ? '1' : '0'
      },
      body
    });
    
    return await response.json();
  }
}

// 反向跟单处理器
class ReverseTradingProcessor {
  private env: Env;
  private okxClient: OKXClient;
  
  constructor(env: Env) {
    this.env = env;
    this.okxClient = new OKXClient(env);
  }
  
  async processSignal(signalData: {
    original: string;
    quantity: number;
    market: string;
    source: string;
    timestamp: number;
  }): Promise<any> {
    // 1. 验证信号有效性
    if (!reverseSignalMapping[signalData.original as keyof typeof reverseSignalMapping]) {
      throw new Error(`未知信号类型: ${signalData.original}`);
    }
    
    // 2. 反向信号转换
    const reversedAction = reverseSignalMapping[signalData.original as keyof typeof reverseSignalMapping];
    
    // 3. 记录信号到数据库
    await this.saveSignalToDatabase(signalData, reversedAction);
    
    // 4. 执行反向交易
    if (this.env.REVERSE_TRADING_ENABLED === 'true') {
      const tradeResult = await this.executeReverseTrade(reversedAction, signalData);
      
      // 5. 记录交易结果
      await this.saveTradeExecution(signalData, reversedAction, tradeResult);
      
      return {
        success: true,
        originalSignal: signalData.original,
        reversedAction,
        tradeResult,
        message: `反向交易执行成功: ${signalData.original} → ${reversedAction}`
      };
    }
    
    return {
      success: true,
      originalSignal: signalData.original,
      reversedAction,
      message: `信号已记录，交易功能未启用`
    };
  }
  
  private async saveSignalToDatabase(signalData: any, reversedAction: string): Promise<void> {
    const query = `
      INSERT INTO trading_signals (original_signal, reversed_signal, quantity, market, timestamp, source)
      VALUES (?, ?, ?, ?, ?, ?)
    `;
    
    await this.env.TRADING_BOTS_DB.prepare(query).bind(
      signalData.original,
      reversedAction,
      signalData.quantity,
      signalData.market,
      signalData.timestamp,
      signalData.source
    ).run();
  }
  
  private async executeReverseTrade(action: string, signalData: any): Promise<any> {
    try {
      const result = await this.okxClient.placeOrder(
        action,
        signalData.market,
        signalData.quantity
      );
      
      console.log(`[Cloudflare Worker] 反向交易执行:`, {
        originalSignal: signalData.original,
        reversedAction: action,
        market: signalData.market,
        quantity: signalData.quantity,
        result
      });
      
      return result;
      
    } catch (error) {
      console.error(`[Cloudflare Worker] 交易执行失败:`, error);
      throw error;
    }
  }
  
  private async saveTradeExecution(signalData: any, action: string, result: any): Promise<void> {
    const query = `
      INSERT INTO trade_executions (action, quantity, market, order_id, status, response, executed_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `;
    
    const orderId = result?.data?.[0]?.ordId || null;
    const status = result?.code === '0' ? 'filled' : 'failed';
    
    await this.env.TRADING_BOTS_DB.prepare(query).bind(
      action,
      signalData.quantity,
      signalData.market,
      orderId,
      status,
      JSON.stringify(result),
      Date.now()
    ).run();
  }
}

// Cloudflare Worker 主处理函数
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    
    // CORS 处理
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    };
    
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }
    
    try {
      const processor = new ReverseTradingProcessor(env);
      
      // 路由处理
      if (url.pathname === '/webhook/telegram' && request.method === 'POST') {
        // Telegram Webhook 处理
        const telegramData = await request.json() as any;
        
        // 解析 Telegram 消息中的交易信号
        const message = telegramData.message?.text || '';
        const signalMatch = message.match(/\[(开多|开空|平多|平空)\].*?数量:(\d+).*?市场:([A-Z-]+)/);
        
        if (signalMatch) {
          const signalData = {
            original: signalMatch[1],
            quantity: parseInt(signalMatch[2]),
            market: signalMatch[3],
            source: 'telegram',
            timestamp: Date.now()
          };
          
          const result = await processor.processSignal(signalData);
          
          return new Response(JSON.stringify(result), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          });
        }
        
        return new Response('OK', { headers: corsHeaders });
      }
      
      if (url.pathname === '/api/process-signal' && request.method === 'POST') {
        // 手动信号处理
        const signalData = await request.json() as any;
        const result = await processor.processSignal(signalData);
        
        return new Response(JSON.stringify(result), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }
      
      if (url.pathname === '/api/bot-status' && request.method === 'GET') {
        // 机器人状态查询
        const stats = await env.TRADING_BOTS_DB.prepare(`
          SELECT 
            COUNT(*) as total_signals,
            COUNT(CASE WHEN status = 'filled' THEN 1 END) as successful_trades
          FROM trade_executions 
          WHERE executed_at > ?
        `).bind(Date.now() - 24 * 60 * 60 * 1000).first();
        
        return new Response(JSON.stringify({
          success: true,
          data: {
            status: 'running',
            location: request.cf?.colo || 'unknown', // Cloudflare 数据中心位置
            stats
          }
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
      }
      
      // 默认响应
      return new Response(JSON.stringify({
        service: 'Reverse Trading Bot',
        version: '1.0.0',
        powered_by: 'Cloudflare Workers',
        edge_location: request.cf?.colo,
        timestamp: new Date().toISOString()
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
      
    } catch (error) {
      console.error('Worker error:', error);
      
      return new Response(JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
  },
  
  // 定时任务 - 每分钟检查机器人状态
  async scheduled(controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    console.log('Scheduled task running at:', new Date().toISOString());
    
    // 这里可以添加定时任务逻辑，比如：
    // - 检查机器人健康状态
    // - 清理过期数据
    // - 生成性能报告
    // - 风险监控
  }
};
