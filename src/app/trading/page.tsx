import { CreateBotDialog } from "@/modules/trading-bots/components/bot-form";
import { BotList } from "@/modules/trading-bots/components/bot-list";
import { Suspense } from "react";

function BotListSkeleton() {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(3)].map((_, i) => (
                <div key={i} className="bg-gray-200 rounded-lg h-64 animate-pulse" />
            ))}
        </div>
    );
}

export default async function TradingBotsPage() {
    return (
        <div className="container mx-auto p-6 space-y-6">
            {/* 页面标题和操作按钮 */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold">交易机器人管理</h1>
                    <p className="text-gray-600 mt-2">
                        创建、配置和监控您的自动化交易策略。
                    </p>
                </div>
                <CreateBotDialog />
            </div>

            {/* 机器人列表容器 */}
            <div className="border-t pt-6">
                <Suspense fallback={<BotListSkeleton />}>
                    <BotList />
                </Suspense>
            </div>
        </div>
    );
}
