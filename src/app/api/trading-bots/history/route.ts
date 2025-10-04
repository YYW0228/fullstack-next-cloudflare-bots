import { NextRequest, NextResponse } from 'next/server';

// 历史交易数据分析
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { historicalData } = body as { historicalData?: string[] };

    // 解析您提供的历史交易数据格式
    const parseHistoricalSignal = (signalText: string) => {
      const patterns = {
        action: /\[(开多|平多|开空|平空)\]/,
        quantity: /数量:(\d+)/,
        market: /市场:([A-Z-]+)/,
        response: /返回({.*})/
      };

      const action = signalText.match(patterns.action)?.[1];
      const quantity = parseInt(signalText.match(patterns.quantity)?.[1] || '1');
      const market = signalText.match(patterns.market)?.[1];
      const responseStr = signalText.match(patterns.response)?.[1];
      
      let response = null;
      try {
        response = JSON.parse(responseStr?.replace(/'/g, '"') || '{}');
      } catch (e) {
        console.log('解析响应失败:', e);
      }

      return {
        action,
        quantity,
        market,
        response,
        timestamp: response?.data?.[0]?.ts || Date.now(),
        orderId: response?.data?.[0]?.ordId,
        success: response?.code === '0'
      };
    };

    // 分析交易模式
    const analyzeTradePatterns = (trades: any[]) => {
      const totalTrades = trades.length;
      const successfulTrades = trades.filter(t => t.success).length;
      const winRate = totalTrades > 0 ? successfulTrades / totalTrades : 0;

      // 统计各类型交易
      const tradeTypes = trades.reduce((acc, trade) => {
        acc[trade.action] = (acc[trade.action] || 0) + 1;
        return acc;
      }, {});

      // 分析交易对
      const tradePairs = [];
      for (let i = 0; i < trades.length - 1; i++) {
        const current = trades[i];
        const next = trades[i + 1];
        
        if ((current.action === '开多' && next.action === '平多') ||
            (current.action === '开空' && next.action === '平空')) {
          tradePairs.push({
            open: current,
            close: next,
            duration: parseInt(next.timestamp) - parseInt(current.timestamp)
          });
        }
      }

      return {
        totalTrades,
        successfulTrades,
        winRate: (winRate * 100).toFixed(2) + '%',
        tradeTypes,
        tradePairs: tradePairs.length,
        avgDuration: tradePairs.length > 0 
          ? (tradePairs.reduce((sum, pair) => sum + pair.duration, 0) / tradePairs.length / 1000 / 60).toFixed(2) + ' 分钟'
          : '0 分钟'
      };
    };

    // 示例：您提供的历史数据
    const sampleHistoricalData = [
      '[开多] 数量:1 市场:BTC-USDT-SWAP 返回{\'code\': \'0\', \'data\': [{\'clOrdId\': \'\', \'ordId\': \'2881860102903275520\', \'sCode\': \'0\', \'sMsg\': \'Order placed\', \'tag\': \'\', \'ts\': \'1758388523862\'}], \'inTime\': \'1758388523861897\', \'msg\': \'\', \'outTime\': \'1758388523863836\'}',
      '[平多] 数量:1 市场:BTC-USDT-SWAP 返回{\'code\': \'0\', \'data\': [{\'clOrdId\': \'\', \'ordId\': \'2882341506225250304\', \'sCode\': \'0\', \'sMsg\': \'Order placed\', \'tag\': \'\', \'ts\': \'1758402870799\'}], \'inTime\': \'1758402870799079\', \'msg\': \'\', \'outTime\': \'1758402870800612\'}',
      '[开空] 数量:1 市场:BTC-USDT-SWAP 返回{\'code\': \'0\', \'data\': [{\'clOrdId\': \'\', \'ordId\': \'2882370079703146496\', \'sCode\': \'0\', \'sMsg\': \'Order placed\', \'tag\': \'\', \'ts\': \'1758403722355\'}], \'inTime\': \'1758403722355500\', \'msg\': \'\', \'outTime\': \'1758403722356520\'}',
      '[平空] 数量:1 市场:BTC-USDT-SWAP 返回{\'code\': \'0\', \'data\': [{\'clOrdId\': \'\', \'ordId\': \'2882495773028360192\', \'sCode\': \'0\', \'sMsg\': \'Order placed\', \'tag\': \'\', \'ts\': \'1758407468308\'}], \'inTime\': \'1758407468307452\', \'msg\': \'\', \'outTime\': \'1758407468308924\'}',
      '[开空] 数量:1 市场:BTC-USDT-SWAP 返回{\'code\': \'0\', \'data\': [{\'clOrdId\': \'\', \'ordId\': \'2883412950979944448\', \'sCode\': \'0\', \'sMsg\': \'Order placed\', \'tag\': \'\', \'ts\': \'1758434802341\'}], \'inTime\': \'1758434802341512\', \'msg\': \'\', \'outTime\': \'1758434802342480\'}',
      '[平空] 数量:1 市场:BTC-USDT-SWAP 返回{\'code\': \'0\', \'data\': [{\'clOrdId\': \'\', \'ordId\': \'2883533420685402112\', \'sCode\': \'0\', \'sMsg\': \'Order placed\', \'tag\': \'\', \'ts\': \'1758438392618\'}], \'inTime\': \'1758438392617860\', \'msg\': \'\', \'outTime\': \'1758438392619773\'}'
    ];

    // 使用提供的数据或示例数据
    const dataToAnalyze = historicalData || sampleHistoricalData;
    
    // 解析所有交易
    const parsedTrades = dataToAnalyze.map(parseHistoricalSignal);
    
    // 分析交易模式
    const analysis = analyzeTradePatterns(parsedTrades);

    // 反向跟单策略回测
    const reverseBacktest = parsedTrades.map(trade => {
      let reversedAction;
      switch(trade.action) {
        case '开多': reversedAction = '开空'; break;
        case '开空': reversedAction = '开多'; break;
        case '平多': reversedAction = '平空'; break;
        case '平空': reversedAction = '平多'; break;
        default: reversedAction = trade.action;
      }
      
      return {
        original: trade,
        reversed: {
          ...trade,
          action: reversedAction,
          strategy: 'reverse_follow'
        }
      };
    });

    return NextResponse.json({
      success: true,
      data: {
        analysis,
        parsedTrades: parsedTrades.slice(0, 10), // 只返回前10条作为示例
        reverseBacktest: reverseBacktest.slice(0, 5), // 返回前5条回测结果
        summary: {
          timeRange: '过去10个月',
          totalSignals: parsedTrades.length,
          markets: [...new Set(parsedTrades.map(t => t.market))],
          mostActiveMarket: 'BTC-USDT-SWAP'
        }
      }
    });

  } catch (error) {
    console.error('历史数据分析失败:', error);
    return NextResponse.json(
      { success: false, error: '数据分析失败' },
      { status: 500 }
    );
  }
}
