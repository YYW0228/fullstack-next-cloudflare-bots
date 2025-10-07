import { createHmac } from 'crypto';

// --- OKX API Client ---

interface OKXEnv {
    OKX_API_KEY: string;
    OKX_SECRET: string;
    OKX_PASSPHRASE: string;
    // 注意：仅支持模拟盘交易，保证测试安全
}

export class OKXClient {
    private readonly apiKey: string;
    private readonly secret: string;
    private readonly passphrase: string;
    private readonly isSandbox: boolean = true; // 强制使用模拟盘，确保安全
    private readonly baseUrl: string;

    constructor(env: OKXEnv) {
        this.apiKey = env.OKX_API_KEY;
        this.secret = env.OKX_SECRET;
        this.passphrase = env.OKX_PASSPHRASE;
        // 强制使用模拟盘模式，确保跟单测试安全
        this.baseUrl = 'https://www.okx.com';
    }

    private sign(timestamp: string, method: string, requestPath: string, body: string = ''): string {
        const message = timestamp + method + requestPath + body;
        const hmac = createHmac('sha256', this.secret);
        hmac.update(message);
        return hmac.digest('base64');
    }

    private async request(method: string, path: string, body: object | null = null): Promise<any> {
        const timestamp = new Date().toISOString();
        const bodyString = body ? JSON.stringify(body) : '';
        const signature = this.sign(timestamp, method, path, bodyString);

        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            'OK-ACCESS-KEY': this.apiKey,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': this.passphrase,
        };

        // 强制启用模拟交易头，所有订单都在模拟环境执行
        headers['x-simulated-trading'] = '1';

        const response = await fetch(`${this.baseUrl}${path}`, {
            method,
            headers,
            body: body ? bodyString : undefined,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`OKX API Error: ${response.status} ${errorText}`);
        }

        return response.json();
    }

    /**
     * Places a new market order.
     * @param marketPair e.g., "BTC-USDT-SWAP"
     * @param side 'buy' or 'sell'
     * @param size The amount to trade (in contracts)
     * @returns The API response from OKX.
     */
    async placeMarketOrder(marketPair: string, side: 'buy' | 'sell', size: number): Promise<any> {
        const body = {
            instId: marketPair,
            tdMode: 'cross', // Using cross-margin mode as per Python code
            side,
            ordType: 'market',
            sz: size.toString(),
        };

        return this.request('POST', '/api/v5/trade/order', body);
    }
    
    /**
     * Fetches the current mark price for a given market pair.
     * @param marketPair e.g., "BTC-USDT-SWAP"
     * @returns The mark price.
     */
    async getMarkPrice(marketPair: string): Promise<number> {
        const response = await this.request('GET', `/api/v5/public/mark-price?instType=SWAP&instId=${marketPair}`);
        
        if (response.code === '0' && response.data.length > 0) {
            return parseFloat(response.data[0].markPx);
        }
        
        throw new Error(`Failed to fetch mark price for ${marketPair}`);
    }

    /**
     * Fetches the details of a filled order to get the average fill price.
     * @param marketPair e.g., "BTC-USDT-SWAP"
     * @param orderId The order ID from the trade response.
     * @returns The average fill price of the order.
     */
    async getOrderDetails(marketPair: string, orderId: string): Promise<{ avgPx: number }> {
        const response = await this.request('GET', `/api/v5/trade/order?instId=${marketPair}&ordId=${orderId}`);

        if (response.code === '0' && response.data.length > 0) {
            const order = response.data[0];
            if (order.state === 'filled') {
                return { avgPx: parseFloat(order.avgPx) };
            }
            // For market orders, they might fill instantly or within a short time.
            // A real production system might need to poll this endpoint a few times.
            // For now, we assume it fills quickly.
            if (order.avgPx) {
                 return { avgPx: parseFloat(order.avgPx) };
            }
        }

        throw new Error(`Failed to get details for order ${orderId}`);
    }
}
