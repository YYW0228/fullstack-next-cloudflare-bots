import { eq } from "drizzle-orm";

import { getDb } from "@/db";
import { strategyInstances } from "@/db/schema/trading-bots";
import { requireAuth } from "@/modules/auth/utils/auth-utils";
import { BotCard } from "./bot-card";

export async function BotList() {
    // This is a server component, so we can fetch data directly from the DB.
    const user = await requireAuth();
    const db = await getDb();

    const instances = await db
        .select()
        .from(strategyInstances)
        .where(eq(strategyInstances.userId, user.id));

    if (instances.length === 0) {
        return (
            <div className="text-center py-12 text-gray-500 border-2 border-dashed rounded-lg">
                <h3 className="text-xl font-semibold">No Strategy Instances Found</h3>
                <p className="mt-2">
                    Click the &quot;Create Bot&quot; button to configure a new strategy.
                </p>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {instances.map((instance) => (
                <BotCard key={instance.id} instance={instance} />
            ))}
        </div>
    );
}