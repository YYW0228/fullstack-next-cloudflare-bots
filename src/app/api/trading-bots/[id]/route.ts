import { NextResponse } from "next/server";
import { headers } from "next/headers";
import { and, eq } from "drizzle-orm";
import { z } from "zod";

import { getDb } from "@/db";
import { strategyInstances } from "@/db/schema/trading-bots";
import handleApiError from "@/lib/api-error";
import { getAuthInstance } from "@/modules/auth/utils/auth-utils";

// Zod schema for updating a strategy instance's config.
// This needs to be flexible to accommodate different strategies.
const updateStrategySchema = z.object({
    name: z.string().min(3).optional(),
    config: z.record(z.string(), z.any()).optional(), // Allows any JSON object for config
});

/**
 * PUT /api/trading-bots/[id]
 * Updates a strategy instance's name and/or configuration.
 */
export async function PUT(
    request: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    try {
        const { id: instanceId } = await params;

        // 1. Authenticate and get user
        const auth = await getAuthInstance();
        const session = await auth.api.getSession({ headers: await headers() });
        if (!session?.user) {
            return NextResponse.json({ success: false, error: "Authentication required" }, { status: 401 });
        }

        // 2. Validate request body
        const body = await request.json();
        const validatedData = updateStrategySchema.parse(body);

        // 3. Fetch the instance to verify ownership
        const db = await getDb();
        const [instance] = await db
            .select({ id: strategyInstances.id })
            .from(strategyInstances)
            .where(and(eq(strategyInstances.id, instanceId), eq(strategyInstances.userId, session.user.id)));

        if (!instance) {
            return NextResponse.json({ success: false, error: "Strategy instance not found or access denied" }, { status: 404 });
        }

        // 4. Update the instance
        const [updatedInstance] = await db
            .update(strategyInstances)
            .set({
                name: validatedData.name,
                config: validatedData.config,
                updatedAt: new Date(),
            })
            .where(eq(strategyInstances.id, instanceId))
            .returning();

        return NextResponse.json({ success: true, data: updatedInstance });

    } catch (error) {
        return handleApiError(error);
    }
}

// Zod schema for updating the status.
const updateStatusSchema = z.object({
    status: z.enum(["running", "stopped", "paused"]),
});

/**
 * PATCH /api/trading-bots/[id]
 * Updates a strategy instance's status (e.g., start, stop, pause).
 */
export async function PATCH(
    request: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    try {
        const { id: instanceId } = await params;

        // 1. Authenticate and get user
        const auth = await getAuthInstance();
        const session = await auth.api.getSession({ headers: await headers() });
        if (!session?.user) {
            return NextResponse.json({ success: false, error: "Authentication required" }, { status: 401 });
        }

        // 2. Validate status
        const body = await request.json();
        const { status } = updateStatusSchema.parse(body);

        // 3. Verify ownership
        const db = await getDb();
        const [instance] = await db
            .select({ id: strategyInstances.id })
            .from(strategyInstances)
            .where(and(eq(strategyInstances.id, instanceId), eq(strategyInstances.userId, session.user.id)));

        if (!instance) {
            return NextResponse.json({ success: false, error: "Strategy instance not found or access denied" }, { status: 404 });
        }

        // 4. Update status
        const [updatedInstance] = await db
            .update(strategyInstances)
            .set({ status, updatedAt: new Date() })
            .where(eq(strategyInstances.id, instanceId))
            .returning();

        return NextResponse.json({ success: true, data: updatedInstance });

    } catch (error) {
        return handleApiError(error);
    }
}

/**
 * DELETE /api/trading-bots/[id]
 * Deletes a strategy instance and all its related data (cascading delete).
 */
export async function DELETE(
    request: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    try {
        const { id: instanceId } = await params;

        // 1. Authenticate and get user
        const auth = await getAuthInstance();
        const session = await auth.api.getSession({ headers: await headers() });
        if (!session?.user) {
            return NextResponse.json({ success: false, error: "Authentication required" }, { status: 401 });
        }

        // 2. Verify ownership before deleting
        const db = await getDb();
        const [instance] = await db
            .select({ id: strategyInstances.id })
            .from(strategyInstances)
            .where(and(eq(strategyInstances.id, instanceId), eq(strategyInstances.userId, session.user.id)));

        if (!instance) {
            return NextResponse.json({ success: false, error: "Strategy instance not found or access denied" }, { status: 404 });
        }

        // 3. Delete the instance (database foreign key with 'onDelete: "cascade"' will handle related data)
        await db.delete(strategyInstances).where(eq(strategyInstances.id, instanceId));

        return NextResponse.json({ success: true, message: "Strategy instance deleted successfully" });

    } catch (error) {
        return handleApiError(error);
    }
}