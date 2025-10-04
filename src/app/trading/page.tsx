'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Play, 
  Pause, 
  BarChart3, 
  TrendingUp, 
  TrendingDown, 
  Activity,
  Settings,
  History,
  AlertTriangle,
  CheckCircle,
  XCircle
} from 'lucide-react';

interface BotStatus {
  type: string;
  status: string;
  performance: {
    totalTrades: number;
    winRate: number;
    totalPnL: number;
    dailyPnL: number;
    maxDrawdown: number;
  };
  positions: {
    active: number;
    maxConcurrent: number;
    totalVolume: number;
  };
  lastSignal: {
    timestamp: string;
    original: string;
    reversed: string;
    quantity: number;
    market: string;
  };
}

const TradingBotsPage = () => {
  const [simpleBotStatus, setSimpleBotStatus] = useState<BotStatus | null>(null);
  const [turtleBotStatus, setTurtleBotStatus] = useState<BotStatus | null>(null);
  const [historicalAnalysis, setHistoricalAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // 获取机器人状态
  const fetchBotStatus = async (botType: string) => {
    try {
      const response = await fetch(`/api/trading-bots?type=${botType}`);
      const result = await response.json();
      return (result as any)?.success ? (result as any)?.data : null;
    } catch (error) {
      console.error(`获取${botType}状态失败:`, error);
      return null;
    }
  };

  // 获取历史数据分析
  const fetchHistoricalAnalysis = async () => {
    try {
      const response = await fetch('/api/trading-bots/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const result = await response.json();
      return (result as any)?.success ? (result as any)?.data : null;
    } catch (error) {
      console.error('获取历史分析失败:', error);
      return null;
    }
  };

  // 初始化数据
  useEffect(() => {
    const initializeData = async () => {
      setLoading(true);
      
      const [simpleStatus, turtleStatus, analysis] = await Promise.all([
        fetchBotStatus('simple-reverse'),
        fetchBotStatus('turtle-reverse'),
        fetchHistoricalAnalysis()
      ]);

      setSimpleBotStatus(simpleStatus);
      setTurtleBotStatus(turtleStatus);
      setHistoricalAnalysis(analysis);
      setLoading(false);
    };

    initializeData();
  }, []);

  // 机器人状态卡片组件
  const BotStatusCard = ({ bot, title, description }: { 
    bot: BotStatus | null, 
    title: string, 
    description: string 
  }) => (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="text-xl">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
        <div className="flex items-center space-x-2">
          {bot?.status === 'running' ? (
            <Badge variant="default" className="bg-green-500">
              <CheckCircle className="w-3 h-3 mr-1" />
              运行中
            </Badge>
          ) : (
            <Badge variant="secondary">
              <XCircle className="w-3 h-3 mr-1" />
              已停止
            </Badge>
          )}
          <Button size="sm" variant="outline">
            {bot?.status === 'running' ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {bot ? (
          <div className="space-y-4">
            {/* 性能指标 */}
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {bot.performance.totalPnL > 0 ? '+' : ''}{bot.performance.totalPnL.toFixed(2)}
                </div>
                <div className="text-sm text-gray-500">总盈亏 USDT</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {(bot.performance.winRate * 100).toFixed(1)}%
                </div>
                <div className="text-sm text-gray-500">胜率</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {bot.performance.totalTrades}
                </div>
                <div className="text-sm text-gray-500">总交易</div>
              </div>
            </div>

            {/* 最新信号 */}
            <div className="border-t pt-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium">最新反向信号</span>
                <span className="text-xs text-gray-500">
                  {new Date(bot.lastSignal.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <Badge variant="outline">{bot.lastSignal.original}</Badge>
                <span>→</span>
                <Badge variant="default">{bot.lastSignal.reversed}</Badge>
                <span className="text-sm text-gray-500">
                  {bot.lastSignal.market} × {bot.lastSignal.quantity}
                </span>
              </div>
            </div>

            {/* 活跃仓位 */}
            <div className="border-t pt-4">
              <div className="flex justify-between text-sm">
                <span>活跃仓位</span>
                <span>{bot.positions.active} / {bot.positions.maxConcurrent}</span>
              </div>
              <Progress 
                value={(bot.positions.active / bot.positions.maxConcurrent) * 100} 
                className="mt-2"
              />
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            机器人数据加载中...
          </div>
        )}
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Activity className="w-8 h-8 animate-spin mx-auto mb-4" />
            <p>加载交易机器人数据中...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">反向跟单交易机器人</h1>
          <p className="text-gray-600 mt-2">智能时间套利 · 反向智慧 · 风险隔离</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline">
            <Settings className="w-4 h-4 mr-2" />
            配置
          </Button>
          <Button>
            <BarChart3 className="w-4 h-4 mr-2" />
            详细分析
          </Button>
        </div>
      </div>

      {/* 核心哲学提示 */}
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          <strong>反向跟单核心逻辑:</strong> 信号开多→我们开空 | 信号开空→我们开多 | 利用200人群体的信息传递延迟进行时间套利
        </AlertDescription>
      </Alert>

      {/* 主要内容标签 */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">机器人概览</TabsTrigger>
          <TabsTrigger value="historical">历史分析</TabsTrigger>
          <TabsTrigger value="signals">信号监控</TabsTrigger>
          <TabsTrigger value="settings">系统配置</TabsTrigger>
        </TabsList>

        {/* 机器人概览 */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid md:grid-cols-2 gap-6">
            <BotStatusCard 
              bot={simpleBotStatus}
              title="简单反向机器人"
              description="30%固定止盈 · 快进快出 · 稳健获利"
            />
            <BotStatusCard 
              bot={turtleBotStatus}
              title="海龟反向机器人"
              description="分层滚仓 · 递进加仓 · 最大化收益"
            />
          </div>

          {/* 整体性能仪表板 */}
          <Card>
            <CardHeader>
              <CardTitle>整体性能仪表板</CardTitle>
              <CardDescription>反向跟单策略的综合表现</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-blue-600">
                    {historicalAnalysis?.summary?.totalSignals || 0}
                  </div>
                  <div className="text-sm text-gray-500">历史信号总数</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-600">
                    {historicalAnalysis?.analysis?.winRate || '0%'}
                  </div>
                  <div className="text-sm text-gray-500">历史胜率</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-purple-600">
                    {historicalAnalysis?.analysis?.tradePairs || 0}
                  </div>
                  <div className="text-sm text-gray-500">完整交易对</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-orange-600">
                    {historicalAnalysis?.analysis?.avgDuration || '0 分钟'}
                  </div>
                  <div className="text-sm text-gray-500">平均持仓时间</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 历史分析 */}
        <TabsContent value="historical" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>历史交易数据分析</CardTitle>
              <CardDescription>基于您过去10个月的交易信号进行反向策略回测</CardDescription>
            </CardHeader>
            <CardContent>
              {historicalAnalysis ? (
                <div className="space-y-6">
                  {/* 交易类型分布 */}
                  <div>
                    <h4 className="font-semibold mb-3">交易类型分布</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {Object.entries(historicalAnalysis.analysis.tradeTypes || {}).map(([type, count]) => (
                        <div key={type} className="text-center p-4 border rounded-lg">
                          <div className="text-2xl font-bold">{count as number}</div>
                          <div className="text-sm text-gray-500">{type}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 反向策略示例 */}
                  <div>
                    <h4 className="font-semibold mb-3">反向策略示例</h4>
                    <div className="space-y-2">
                      {historicalAnalysis.reverseBacktest?.slice(0, 3).map((trade: any, index: number) => (
                        <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                          <div className="flex items-center space-x-4">
                            <Badge variant="outline">{trade.original.action}</Badge>
                            <span>→</span>
                            <Badge variant="default">{trade.reversed.action}</Badge>
                          </div>
                          <div className="text-sm text-gray-500">
                            {trade.original.market} × {trade.original.quantity}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  历史数据分析中...
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 信号监控 */}
        <TabsContent value="signals" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>实时信号监控</CardTitle>
              <CardDescription>监控 Telegram 群组信号并执行反向交易</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                <Activity className="w-12 h-12 mx-auto mb-4" />
                <p>等待新的交易信号...</p>
                <p className="text-sm mt-2">连接到 Telegram 群组: -1001911467666</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 系统配置 */}
        <TabsContent value="settings" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Cloudflare 部署配置</CardTitle>
              <CardDescription>VPS 集成和环境变量配置</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    系统已配置为 Cloudflare Workers 边缘计算环境，具备全球300+节点的超低延迟优势
                  </AlertDescription>
                </Alert>
                
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="p-4 border rounded-lg">
                    <h4 className="font-semibold mb-2">VPS 集成状态</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>VPS 连接:</span>
                        <Badge variant="default">已连接</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span>历史数据:</span>
                        <Badge variant="default">10个月数据</Badge>
                      </div>
                    </div>
                  </div>
                  
                  <div className="p-4 border rounded-lg">
                    <h4 className="font-semibold mb-2">Cloudflare 状态</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Workers 部署:</span>
                        <Badge variant="default">活跃</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span>D1 数据库:</span>
                        <Badge variant="default">已连接</Badge>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default TradingBotsPage;
