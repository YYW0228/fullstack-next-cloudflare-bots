import fs from 'fs/promises';
import path from 'path';
import { unstable_dev } from 'wrangler';
import type { Unstable_DevWorker } from 'wrangler';

// --- E2E Test Script using unstable_dev ---

interface HistoricalSignal {
    signal: string;
    timestamp_ms: number;
    raw_message: string;
}

const DATA_FILE_PATH = path.join(__dirname, '../../data/historical_signals.json');

async function runTest() {
    console.log('--- Starting E2E Test with unstable_dev ---');

    let worker: Unstable_DevWorker | undefined;

    try {
        // 1. Start the worker programmatically
        console.log('Starting worker...');
        worker = await unstable_dev('src/workers/reverse-trading-bot.ts', {
            experimental: { disableExperimentalWarning: true },
        });
        console.log('Worker started successfully.');

        // 2. Read historical data
        let signals: HistoricalSignal[];
        try {
            const fileContent = await fs.readFile(DATA_FILE_PATH, 'utf-8');
            signals = JSON.parse(fileContent);
            console.log(`Loaded ${signals.length} historical signals.`);
        } catch (error) {
            console.error(`Failed to read or parse data file: ${DATA_FILE_PATH}`);
            throw error; // Rethrow to be caught by the outer try-catch
        }

        if (signals.length === 0) {
            console.log('No signals to test.');
            return;
        }

        // 3. Send each signal to the worker
        for (const signal of signals) {
            console.log(`
Sending signal: ${signal.raw_message}`);

            const resp = await worker.fetch('/webhook/telegram', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: { text: signal.raw_message } }),
            });

            console.log(`  -> Worker responded with status ${resp.status}`);
            if (resp.status !== 202) {
                throw new Error(`Assertion failed: expected status 202, but got ${resp.status}`);
            }
        }

        console.log('\n--- E2E Test Finished Successfully ---');

    } catch (error) {
        console.error('\n--- E2E Test FAILED ---');
        console.error(error);
        process.exit(1); // Exit with error code
    } finally {
        // 4. Stop the worker
        if (worker) {
            console.log("\nStopping worker...");
            await worker.stop();
            console.log("Worker stopped.");
        }
    }
}

runTest();
