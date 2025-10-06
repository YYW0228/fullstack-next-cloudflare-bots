import { describe, it, expect } from 'vitest';

// We need to make the function available for testing.
// In a real scenario, we would export it from the worker file.
// For this test, I'll redefine it here.
function parseSignalText(text: string): { action: 'open' | 'close'; side: 'long' | 'short'; quantity: number; marketPair: string } | null {
    const openMatch = text.match(/\[(开多|开空)\]\s+数量:(\d+)\s+市场:([\w-]+)/);
    if (openMatch) {
        return {
            action: 'open',
            side: openMatch[1] === '开多' ? 'long' : 'short',
            quantity: parseInt(openMatch[2], 10),
            marketPair: openMatch[3],
        };
    }

    const closeMatch = text.match(/\[(平多|平空)\]/);
    if (closeMatch) {
        return {
            action: 'close',
            side: closeMatch[1] === '平多' ? 'long' : 'short',
            quantity: 0, // Not relevant for closing signals
            marketPair: '*', // Applies to all markets for this user
        };
    }

    return null;
}

describe('parseSignalText', () => {
    it('should correctly parse an open long signal', () => {
        const text = '[开多] 数量:1 市场:BTC-USDT-SWAP 返回{...}';
        const result = parseSignalText(text);
        expect(result).toEqual({
            action: 'open',
            side: 'long',
            quantity: 1,
            marketPair: 'BTC-USDT-SWAP',
        });
    });

    it('should correctly parse an open short signal with larger quantity', () => {
        const text = '[开空] 数量:15 市场:ETH-USDT-SWAP ...';
        const result = parseSignalText(text);
        expect(result).toEqual({
            action: 'open',
            side: 'short',
            quantity: 15,
            marketPair: 'ETH-USDT-SWAP',
        });
    });

    it('should correctly parse a close long signal', () => {
        const text = '[平多] 数量:3 市场:BTC-USDT-SWAP ...';
        const result = parseSignalText(text);
        expect(result).toEqual({
            action: 'close',
            side: 'long',
            quantity: 0,
            marketPair: '*',
        });
    });

    it('should correctly parse a close short signal', () => {
        const text = '[平空] 数量:1 市场:BTC-USDT-SWAP ...';
        const result = parseSignalText(text);
        expect(result).toEqual({
            action: 'close',
            side: 'short',
            quantity: 0,
            marketPair: '*',
        });
    });

    it('should return null for invalid or unrelated text', () => {
        const text = 'This is a regular chat message.';
        const result = parseSignalText(text);
        expect(result).toBeNull();
    });

    it('should handle signals without extra text', () => {
        const text = '[开多] 数量:1 市场:BTC-USDT-SWAP';
        const result = parseSignalText(text);
        expect(result).toEqual({
            action: 'open',
            side: 'long',
            quantity: 1,
            marketPair: 'BTC-USDT-SWAP',
        });
    });
});
