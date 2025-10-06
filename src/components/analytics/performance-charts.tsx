"use client";

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { 
    LineChart, 
    Line, 
    XAxis, 
    YAxis, 
    CartesianGrid, 
    Tooltip, 
    ResponsiveContainer,
    BarChart,
    Bar,
    PieChart,
    Pie,
    Cell,
    AreaChart,
    Area
} from 'recharts';

// 模拟数据生成
const generatePnLData = () => {
    const data = [];
    let cumulative = 0;
    for (let i = 0; i < 30; i++) {
        const daily = (Math.random() - 0.45) * 100; // 轻微正偏
        cumulative += daily;
        data.push({
            date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toLocaleDateString(),
            daily: parseFloat(daily.toFixed(2)),
            cumulative: parseFloat(cumulative.toFixed(2))
        });
    }
    return data;
};

const generateTradeData = () => {
    return Array.from({ length: 24 }, (_, i) => ({
        hour: `${i.toString().padStart(2, '0')}:00`,
        trades: Math.floor(Math.random() * 10) + 1,
        winRate: parseFloat((Math.random() * 40 + 50).toFixed(1))
    }));
};

const generateStrategyData = () => {
    return [
        { name: 'Simple Reverse', trades: 125, pnl: 456.78, winRate: 68.5, color: '#8884d8' },
        { name: 'Turtle Reverse', trades: 89, pnl: 234.56, winRate: 72.3, color: '#82ca9d' },
        { name: 'Others', trades: 34, pnl: 123.45, winRate: 65.2, color: '#ffc658' }
    ];
};

const generateDrawdownData = () => {
    const data = [];
    let peak = 0;
    let current = 0;
    for (let i = 0; i < 30; i++) {
        const change = (Math.random() - 0.45) * 50;
        current += change;
        if (current > peak) peak = current;
        const drawdown = current - peak;
        data.push({
            date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toLocaleDateString(),
            drawdown: parseFloat(drawdown.toFixed(2)),
            portfolio: parseFloat(current.toFixed(2))
        });
    }
    return data;
};

export function PerformanceCharts() {
    const [pnlData, setPnlData] = useState(generatePnLData());
    const [tradeData, setTradeData] = useState(generateTradeData());
    const [strategyData, setStrategyData] = useState(generateStrategyData());
    const [drawdownData, setDrawdownData] = useState(generateDrawdownData());

    // 计算关键指标
    const totalPnL = pnlData[pnlData.length - 1]?.cumulative || 0;
    const maxDrawdown = Math.min(...drawdownData.map(d => d.drawdown));
    const totalTrades = strategyData.reduce((sum, s) => sum + s.trades, 0);
    const avgWinRate = strategyData.reduce((sum, s) => sum + s.winRate * s.trades, 0) / totalTrades;

    // 自动刷新数据
    useEffect(() => {
        const interval = setInterval(() => {
            // 每30秒更新一次图表数据
            setPnlData(generatePnLData());
            setTradeData(generateTradeData());
            setDrawdownData(generateDrawdownData());
        }, 30000);

        return () => clearInterval(interval);
    }, []);

    const formatCurrency = (value: number) => `$${value.toFixed(2)}`;
    const formatPercent = (value: number) => `${value.toFixed(1)}%`;

    return (
        <div className="space-y-6">
            {/* 关键指标概览 */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-muted-foreground">总盈亏</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatCurrency(totalPnL)}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-muted-foreground">最大回撤</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-red-600">
                            {formatCurrency(maxDrawdown)}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-muted-foreground">总交易次数</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {totalTrades}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-muted-foreground">平均胜率</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-600">
                            {formatPercent(avgWinRate)}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* 图表标签页 */}
            <Tabs defaultValue="pnl" className="space-y-4">
                <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="pnl">盈亏分析</TabsTrigger>
                    <TabsTrigger value="trades">交易分布</TabsTrigger>
                    <TabsTrigger value="strategy">策略对比</TabsTrigger>
                    <TabsTrigger value="risk">风险分析</TabsTrigger>
                </TabsList>

                {/* 盈亏分析 */}
                <TabsContent value="pnl">
                    <Card>
                        <CardHeader>
                            <CardTitle>盈亏趋势分析</CardTitle>
                            <CardDescription>
                                显示每日盈亏和累计盈亏趋势
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ResponsiveContainer width="100%" height={400}>
                                <LineChart data={pnlData}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis 
                                        dataKey="date" 
                                        fontSize={12}
                                        tickFormatter={(value) => value.split('/').slice(0, 2).join('/')}
                                    />
                                    <YAxis fontSize={12} />
                                    <Tooltip 
                                        formatter={(value, name) => [
                                            formatCurrency(Number(value)), 
                                            name === 'daily' ? '日盈亏' : '累计盈亏'
                                        ]}
                                        labelFormatter={(label) => `日期: ${label}`}
                                    />
                                    <Bar dataKey="daily" fill="#8884d8" opacity={0.6} />
                                    <Line 
                                        type="monotone" 
                                        dataKey="cumulative" 
                                        stroke="#ff7300" 
                                        strokeWidth={2}
                                        dot={false}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 交易分布 */}
                <TabsContent value="trades">
                    <Card>
                        <CardHeader>
                            <CardTitle>24小时交易分布</CardTitle>
                            <CardDescription>
                                显示不同时段的交易频率和胜率
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ResponsiveContainer width="100%" height={400}>
                                <BarChart data={tradeData}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis 
                                        dataKey="hour" 
                                        fontSize={12}
                                        interval={1}
                                    />
                                    <YAxis yAxisId="left" fontSize={12} />
                                    <YAxis yAxisId="right" orientation="right" fontSize={12} />
                                    <Tooltip 
                                        formatter={(value, name) => [
                                            name === 'trades' ? value : formatPercent(Number(value)),
                                            name === 'trades' ? '交易次数' : '胜率'
                                        ]}
                                    />
                                    <Bar yAxisId="left" dataKey="trades" fill="#8884d8" />
                                    <Line 
                                        yAxisId="right"
                                        type="monotone" 
                                        dataKey="winRate" 
                                        stroke="#ff7300" 
                                        strokeWidth={2}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* 策略对比 */}
                <TabsContent value="strategy">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <Card>
                            <CardHeader>
                                <CardTitle>策略盈亏对比</CardTitle>
                                <CardDescription>
                                    各策略的盈亏贡献度
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ResponsiveContainer width="100%" height={300}>
                                    <PieChart>
                                        <Pie
                                            data={strategyData}
                                            cx="50%"
                                            cy="50%"
                                            outerRadius={80}
                                            dataKey="pnl"
                                            label={({ name, percent }: any) => `${name} ${(percent * 100).toFixed(0)}%`}
                                        >
                                            {strategyData.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color} />
                                            ))}
                                        </Pie>
                                        <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                                    </PieChart>
                                </ResponsiveContainer>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>策略详细对比</CardTitle>
                                <CardDescription>
                                    各策略的详细表现指标
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    {strategyData.map((strategy, index) => (
                                        <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                                            <div className="flex items-center space-x-3">
                                                <div 
                                                    className="w-4 h-4 rounded-full" 
                                                    style={{ backgroundColor: strategy.color }}
                                                />
                                                <div>
                                                    <h4 className="font-medium">{strategy.name}</h4>
                                                    <p className="text-sm text-muted-foreground">
                                                        {strategy.trades} 笔交易
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className={`font-medium ${strategy.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                    {formatCurrency(strategy.pnl)}
                                                </div>
                                                <Badge variant="secondary">
                                                    {formatPercent(strategy.winRate)}
                                                </Badge>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* 风险分析 */}
                <TabsContent value="risk">
                    <Card>
                        <CardHeader>
                            <CardTitle>回撤分析</CardTitle>
                            <CardDescription>
                                资产组合回撤和恢复情况
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ResponsiveContainer width="100%" height={400}>
                                <AreaChart data={drawdownData}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis 
                                        dataKey="date" 
                                        fontSize={12}
                                        tickFormatter={(value) => value.split('/').slice(0, 2).join('/')}
                                    />
                                    <YAxis fontSize={12} />
                                    <Tooltip 
                                        formatter={(value, name) => [
                                            formatCurrency(Number(value)),
                                            name === 'drawdown' ? '回撤' : '组合价值'
                                        ]}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="portfolio"
                                        stackId="1"
                                        stroke="#8884d8"
                                        fill="#8884d8"
                                        fillOpacity={0.3}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="drawdown"
                                        stackId="2"
                                        stroke="#ff0000"
                                        fill="#ff0000"
                                        fillOpacity={0.5}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}