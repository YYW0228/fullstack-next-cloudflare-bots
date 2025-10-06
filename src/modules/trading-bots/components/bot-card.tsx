'use client';

import type { InferSelectModel } from 'drizzle-orm';
import { Bot, Pause, Pencil, Play, Trash2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import type { strategyInstances } from '@/db/schema/trading-bots';

type StrategyInstance = InferSelectModel<typeof strategyInstances>;

// Helper to determine badge color based on status
const getStatusVariant = (status: string) => {
    switch (status) {
        case 'running':
            return 'bg-green-500';
        case 'stopped':
            return 'bg-red-500';
        case 'paused':
            return 'bg-yellow-500';
        default:
            return 'bg-gray-500';
    }
};

export function BotCard({ instance }: { instance: StrategyInstance }) {
    const config = instance.config as { marketPair?: string };

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Bot className="w-8 h-8 text-gray-500" />
                        <div>
                            <CardTitle>{instance.name}</CardTitle>
                            <CardDescription>
                                {instance.strategyType} on <strong>{instance.marketPair}</strong>
                            </CardDescription>
                        </div>
                    </div>
                    <Badge className={`text-white ${getStatusVariant(instance.status)}`}>
                        {instance.status}
                    </Badge>
                </div>
            </CardHeader>
            <CardContent>
                <div className="text-sm text-gray-600 space-y-1">
                    <p>
                        <strong>ID:</strong> <span className="font-mono text-xs">{instance.id}</span>
                    </p>
                    <p>
                        <strong>Last Updated:</strong>{' '}
                        {new Date(instance.updatedAt).toLocaleString()}
                    </p>
                </div>
            </CardContent>
            <CardFooter className="flex justify-end gap-2">
                <Button variant="outline" size="sm">
                    <Pencil className="w-4 h-4 mr-2" />
                    Edit
                </Button>
                {instance.status === 'running' ? (
                    <Button variant="destructive" size="sm">
                        <Pause className="w-4 h-4 mr-2" />
                        Stop
                    </Button>
                ) : (
                    <Button
                        variant="default"
                        size="sm"
                        className="bg-green-600 hover:bg-green-700"
                    >
                        <Play className="w-4 h-4 mr-2" />
                        Start
                    </Button>
                )}
                <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-500 hover:text-red-600"
                >
                    <Trash2 className="w-4 h-4" />
                </Button>
            </CardFooter>
        </Card>
    );
}