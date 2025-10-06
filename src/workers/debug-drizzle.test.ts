import { describe, it, expect, vi } from 'vitest';

// Mock D1 and other environment dependencies
const mockDb = {
    query: {
        strategyInstances: {
            findMany: vi.fn(),
        },
    },
};

const mockEnv = {
    TRADING_BOTS_DB: {},
    // ... other env vars
} as any;

// Mock drizzle to avoid actual DB connection
vi.mock('drizzle-orm/d1', () => ({
    drizzle: () => mockDb,
}));

// Import the function to be tested AFTER mocking
import { processSignal } from './reverse-trading-bot'; // Assuming processSignal is exported

describe('processSignal in waitUntil context', () => {

    it('should not throw when accessing the database', async () => {
        // Arrange: Setup mock return value for the DB query
        mockDb.query.strategyInstances.findMany.mockResolvedValue([]);
        const signalText = '[开多] 数量:1 市场:BTC-USDT-SWAP';

        // Act & Assert: Expect the function to run without throwing the 'prepare' error
        await expect(processSignal(signalText, mockEnv)).resolves.not.toThrow();
        
        // Verify that the mocked DB function was called
        expect(mockDb.query.strategyInstances.findMany).toHaveBeenCalled();
    });
});
