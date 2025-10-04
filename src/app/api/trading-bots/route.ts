import { NextRequest, NextResponse } from 'next/server';
import { BotType, BotStatus, TradeType } from '@/modules/trading-bots/models/bot.enum';

// 反向跟单核心逻辑
const reverseSignal = (originalSignal: string): TradeType => {
  switch (originalSignal) {
    case '开多':
      return TradeType.OPEN_SHORT;  // 信号开多 → 我们开空
    case '开空':
      return TradeType.OPEN_LONG;   // 信号开空 → 我们开多
    case '平多':
      return TradeType.CLOSE_SHORT; // 信号平多 → 我们平空
    case '平空':
      return TradeType.CLOSE_LONG;  // 信号平空 → 我们平多
    default:
      throw new Error(`未知信号类型: ${originalSignal}`);
  }
};

// GET: 获取机器人状态
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const botType = searchParams.get('type') as BotType;

    // 模拟机器人状态数据 (后续从 D1 数据库获取)
    const botStatus = {
      type: botType || BotType.SIMPLE_REVERSE,
      status: BotStatus.RUNNING,
      performance: {
        totalTrades: 156,
        winRate: 0.73,
        totalPnL: 2856.42,
        dailyPnL: 89.23,
        maxDrawdown: -0.08
      },
      positions: {
        active: 2,
        maxConcurrent: 5,
        totalVolume: 18.5
      },
      lastSignal: {
        timestamp: new Date().toISOString(),
        original: '开多',
        reversed: '开空',
        quantity: 1,
        market: 'BTC-USDT-SWAP'
      }
    };

    return NextResponse.json({
      success: true,
      data: botStatus
    });

  } catch (error) {
    console.error('获取机器人状态失败:', error);
    return NextResponse.json(
      { success: false, error: '服务器错误' },
      { status: 500 }
    );
  }
}

// POST: 处理交易信号
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { signal, quantity, market, botType } = body as { signal: string; quantity: number; market: string; botType?: string };

    // 验证输入
    if (!signal || !quantity || !market) {
      return NextResponse.json(
        { success: false, error: '缺少必需参数' },
        { status: 400 }
      );
    }

    // 反向信号转换
    const reversedAction = reverseSignal(signal);
    
    // 构造交易请求 (这里模拟，实际会调用 OKX API)
    const tradeRequest = {
      action: reversedAction,
      quantity: quantity,
      market: market,
      timestamp: Date.now(),
      originalSignal: signal,
      botType: botType || BotType.SIMPLE_REVERSE
    };

    // 模拟 OKX API 响应
    const mockResponse = {
      code: '0',
      data: [{
        clOrdId: '',
        ordId: String(Date.now() + Math.floor(Math.random() * 1000)),
        sCode: '0',
        sMsg: 'Order placed',
        tag: '',
        ts: String(Date.now())
      }],
      inTime: String(Date.now()),
      msg: '',
      outTime: String(Date.now() + 1)
    };

    // 记录交易日志 (后续存储到 D1 数据库)
    console.log(`[反向交易] 原始信号: ${signal} → 执行: ${reversedAction} | 数量: ${quantity} | 市场: ${market}`);

    return NextResponse.json({
      success: true,
      data: {
        tradeRequest,
        response: mockResponse,
        message: `反向交易执行成功: ${signal} → ${reversedAction}`
      }
    });

  } catch (error) {
    console.error('交易信号处理失败:', error);
    return NextResponse.json(
      { success: false, error: '交易执行失败' },
      { status: 500 }
    );
  }
}

// PUT: 更新机器人配置
export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { botType, config } = body as { botType: string; config: any };

    // 验证配置 (后续存储到 D1 数据库)
    const updatedConfig = {
      botType,
      ...config,
      updatedAt: new Date().toISOString()
    };

    return NextResponse.json({
      success: true,
      data: updatedConfig,
      message: '机器人配置更新成功'
    });

  } catch (error) {
    console.error('更新机器人配置失败:', error);
    return NextResponse.json(
      { success: false, error: '配置更新失败' },
      { status: 500 }
    );
  }
}
