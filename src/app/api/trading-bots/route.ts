import { NextResponse } from "next/server";
import { headers } from "next/headers";
import { eq, desc } from "drizzle-orm";
import { z } from "zod";

import { getDb } from "@/db";
import { strategyInstances } from "@/db/schema/trading-bots";
import handleApiError from "@/lib/api-error";
import { getAuthInstance } from "@/modules/auth/utils/auth-utils";

/**
 * GET /api/trading-bots
 * Retrieves all strategy instances for the authenticated user.
 */
export async function GET(request: Request) {
    try {
        // 1. Authenticate the user
        const auth = await getAuthInstance();
        const session = await auth.api.getSession({ headers: await headers() });
        if (!session?.user) {
            return NextResponse.json({ success: false, error: "Authentication required" }, { status: 401 });
        }

        // 2. Fetch all instances for the user, ordered by creation date
        const db = await getDb();
        const instances = await db
            .select()
            .from(strategyInstances)
            .where(eq(strategyInstances.userId, session.user.id))
            .orderBy(desc(strategyInstances.createdAt));

        return NextResponse.json({ success: true, data: instances });

    } catch (error) {
        return handleApiError(error);
    }
}

/**
 * Zod schema for creating a new strategy instance.
 */
const createInstanceSchema = z.object({
    name: z.string().min(3, "Name must be at least 3 characters long"),
    marketPair: z.string().min(1, "Market pair is required"),
    strategyType: z.enum(["simple-reverse", "turtle-reverse"]),
    // Config is a JSON object, so we accept a record.
    config: z.record(z.string(), z.any()).refine((data) => Object.keys(data).length > 0, {
        message: "Config cannot be empty",
    }),
});

/**
 * POST /api/trading-bots
 * Creates a new strategy instance for the authenticated user.
 */
export async function POST(request: Request) {
    try {
        // 1. Authenticate the user
        const auth = await getAuthInstance();
        const session = await auth.api.getSession({ headers: await headers() });
        if (!session?.user) {
            return NextResponse.json({ success: false, error: "Authentication required" }, { status: 401 });
        }

        // 2. Validate the request body
        const body = await request.json();
        const validatedData = createInstanceSchema.parse(body);

        // 3. Insert the new instance into the database
        const db = await getDb();
        const [newInstance] = await db
            .insert(strategyInstances)
            .values({
                ...validatedData,
                userId: session.user.id,
                status: "stopped", // Always start in a stopped state
            })
            .returning();

        // 4. Return the newly created instance
        return NextResponse.json({ success: true, data: newInstance }, { status: 201 });

    } catch (error) {
        return handleApiError(error);
    }
}
