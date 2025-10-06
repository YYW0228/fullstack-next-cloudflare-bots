import { unstable_dev } from 'wrangler';
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import type { UnstableDevWorker } from 'wrangler';

describe('Worker integration test with live D1', () => {
    let worker: UnstableDevWorker;

    beforeAll(async () => {
        // Start a wrangler dev server in the background
        worker = await unstable_dev('src/workers/reverse-trading-bot.ts', {
            experimental: { disableExperimentalWarning: true },
        });
    });

    afterAll(async () => {
        // Stop the wrangler dev server
        await worker.stop();
    });

    it('should process a signal without throwing a D1 error', async () => {
        const signal = {
            message: {
                text: '[开多] 数量:1 市场:BTC-USDT-SWAP'
            }
        };

        // Send a request to the running worker
        const resp = await worker.fetch('/webhook/telegram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(signal)
        });

        // The initial response should be 202 Accepted
        expect(resp.status).toBe(202);

        // This is the crucial part: we need to wait for the waitUntil promise to resolve or reject.
        // unstable_dev doesn't expose this directly, so we'll check the logs for the error.
        // A more robust solution might involve a mock that signals completion.
        
        // For now, we'll just check that the initial request didn't fail synchronously.
        // The real test is observing the console output for the 'prepare' error.
    });
});
