"use client";

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { 
    TrendingUp, 
    TrendingDown, 
    Activity, 
    DollarSign, 
    AlertTriangle,
    CheckCircle,
    XCircle,
    Clock,
    BarChart3
} from 'lucide-react';

interface TradingStats {
    totalPnL: number;
    todayPnL: number;
    activePositions: number;
    totalTrades: number;
    winRate: number;
    avgTradeTime: number;
    lastUpdated: string;
}

interface StrategyStatus {
    id: string;
    name: string;
    status: 'running' | 'stopped' | 'error';
    type: 'simple-reverse' | 'turtle-reverse';
    activePositions: number;
    todayPnL: number;
    lastSignal: string;
}

interface SystemHealth {
    workerStatus: 'healthy' | 'degraded' | 'down';
    dbConnections: number;
    apiResponseTime: number;
    errorRate: number;
    lastHealthCheck: string;
}

export function RealTimeDashboard() {
    const [stats, setStats] = useState<TradingStats>({
        totalPnL: 1250.75,
        todayPnL: 125.50,
        activePositions: 8,
        totalTrades: 156,
        winRate: 68.5,
        avgTradeTime: 245,
        lastUpdated: new Date().toLocaleTimeString()
    });

    const [strategies, setStrategies] = useState<StrategyStatus[]>([
        {
            id: '1',
            name: 'BTC Simple Reverse',
            status: 'running',
            type: 'simple-reverse',
            activePositions: 3,
            todayPnL: 45.20,
            lastSignal: '2 minutes ago'
        },
        {
            id: '2',
            name: 'ETH Turtle Reverse',
            status: 'running',
            type: 'turtle-reverse',
            activePositions: 5,
            todayPnL: 80.30,
            lastSignal: '15 minutes ago'
        },
        {
            id: '3',
            name: 'SOL Simple Reverse',
            status: 'error',
            type: 'simple-reverse',
            activePositions: 0,
            todayPnL: 0,
            lastSignal: '1 hour ago'
        }
    ]);

    const [systemHealth, setSystemHealth] = useState<SystemHealth>({
        workerStatus: 'healthy',
        dbConnections: 5,
        apiResponseTime: 120,
        errorRate: 0.5,
        lastHealthCheck: new Date().toLocaleTimeString()
    });

    // 模拟实时数据更新
    useEffect(() => {
        const interval = setInterval(() => {
            // 更新统计数据
            setStats(prev => ({
                ...prev,
                todayPnL: prev.todayPnL + (Math.random() - 0.5) * 10,
                totalPnL: prev.totalPnL + (Math.random() - 0.5) * 10,
                lastUpdated: new Date().toLocaleTimeString()
            }));

            // 更新系统健康状态
            setSystemHealth(prev => ({
                ...prev,
                apiResponseTime: 80 + Math.random() * 100,
                errorRate: Math.random() * 2,
                lastHealthCheck: new Date().toLocaleTimeString()
            }));
        }, 5000); // 每5秒更新一次

        return () => clearInterval(interval);
    }, []);

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'running':
            case 'healthy':
                return 'text-green-600 bg-green-100';
            case 'error':
            case 'down':
                return 'text-red-600 bg-red-100';
            case 'degraded':
                return 'text-yellow-600 bg-yellow-100';
            default:
                return 'text-gray-600 bg-gray-100';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'running':
            case 'healthy':
                return <CheckCircle className="h-4 w-4" />;
            case 'error':
            case 'down':
                return <XCircle className="h-4 w-4" />;
            case 'degraded':
                return <AlertTriangle className="h-4 w-4" />;
            default:
                return <Clock className="h-4 w-4" />;
        }
    };

    return (
        <div className="space-y-6">
            {/* 系统状态概览 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">总盈亏</CardTitle>
                        <DollarSign className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            <span className={stats.totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}>
                                ${stats.totalPnL.toFixed(2)}
                            </span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                            今日: ${stats.todayPnL.toFixed(2)}
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">活跃仓位</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.activePositions}</div>
                        <p className="text-xs text-muted-foreground">
                            总交易: {stats.totalTrades}
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">胜率</CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.winRate.toFixed(1)}%</div>
                        <Progress value={stats.winRate} className="mt-2" />
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">平均持仓时间</CardTitle>
                        <Clock className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.avgTradeTime}分钟</div>
                        <p className="text-xs text-muted-foreground">
                            最后更新: {stats.lastUpdated}
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* 系统健康状态 */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <BarChart3 className="h-5 w-5" />
                        系统健康状态
                    </CardTitle>
                    <CardDescription>
                        实时监控系统组件状态和性能指标
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium">Worker 状态</span>
                                <Badge className={getStatusColor(systemHealth.workerStatus)}>
                                    {getStatusIcon(systemHealth.workerStatus)}
                                    <span className="ml-1 capitalize">{systemHealth.workerStatus}</span>
                                </Badge>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm">API 响应时间</span>
                                <span className="text-sm font-mono">{systemHealth.apiResponseTime.toFixed(0)}ms</span>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-sm">数据库连接</span>
                                <span className="text-sm font-mono">{systemHealth.dbConnections}/10</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm">错误率</span>
                                <span className="text-sm font-mono">{systemHealth.errorRate.toFixed(1)}%</span>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-sm">最后检查</span>
                                <span className="text-sm font-mono">{systemHealth.lastHealthCheck}</span>
                            </div>
                            <Progress 
                                value={systemHealth.apiResponseTime > 200 ? 20 : 100} 
                                className="h-2" 
                            />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* 策略状态 */}
            <Card>
                <CardHeader>
                    <CardTitle>策略实例状态</CardTitle>
                    <CardDescription>
                        当前运行的策略实例及其性能
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {strategies.map((strategy) => (
                            <div key={strategy.id} className="flex items-center justify-between p-4 border rounded-lg">
                                <div className="flex items-center space-x-4">
                                    <Badge className={getStatusColor(strategy.status)}>
                                        {getStatusIcon(strategy.status)}
                                        <span className="ml-1 capitalize">{strategy.status}</span>
                                    </Badge>
                                    <div>
                                        <h4 className="font-medium">{strategy.name}</h4>
                                        <p className="text-sm text-muted-foreground">
                                            {strategy.type} • {strategy.activePositions} 仓位
                                        </p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className={`font-medium ${strategy.todayPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                        ${strategy.todayPnL.toFixed(2)}
                                    </div>
                                    <p className="text-sm text-muted-foreground">
                                        最后信号: {strategy.lastSignal}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* 实时告警 */}
            {systemHealth.errorRate > 1 && (
                <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>系统警告</AlertTitle>
                    <AlertDescription>
                        当前错误率为 {systemHealth.errorRate.toFixed(1)}%，超过正常范围。建议检查系统状态。
                    </AlertDescription>
                </Alert>
            )}

            {stats.activePositions > 10 && (
                <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>仓位警告</AlertTitle>
                    <AlertDescription>
                        当前活跃仓位数量为 {stats.activePositions}，接近系统限制。建议检查风险管理设置。
                    </AlertDescription>
                </Alert>
            )}
        </div>
    );
}