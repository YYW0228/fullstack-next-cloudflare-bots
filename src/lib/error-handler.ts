/**
 * 增强的错误处理系统
 * 提供统一的错误处理、日志记录和用户友好的错误信息
 */

export class TradingBotError extends Error {
    public readonly code: string;
    public readonly severity: 'low' | 'medium' | 'high' | 'critical';
    public readonly metadata?: Record<string, any>;
    public readonly timestamp: Date;

    constructor(
        message: string,
        code: string = 'UNKNOWN_ERROR',
        severity: 'low' | 'medium' | 'high' | 'critical' = 'medium',
        metadata?: Record<string, any>
    ) {
        super(message);
        this.name = 'TradingBotError';
        this.code = code;
        this.severity = severity;
        this.metadata = metadata;
        this.timestamp = new Date();
    }

    toJSON() {
        return {
            name: this.name,
            message: this.message,
            code: this.code,
            severity: this.severity,
            metadata: this.metadata,
            timestamp: this.timestamp.toISOString(),
            stack: this.stack,
        };
    }
}

export class ValidationError extends TradingBotError {
    constructor(message: string, field?: string, value?: any) {
        super(message, 'VALIDATION_ERROR', 'low', { field, value });
        this.name = 'ValidationError';
    }
}

export class AuthenticationError extends TradingBotError {
    constructor(message: string = 'Authentication required') {
        super(message, 'AUTH_ERROR', 'high');
        this.name = 'AuthenticationError';
    }
}

export class TradingError extends TradingBotError {
    constructor(message: string, orderData?: any) {
        super(message, 'TRADING_ERROR', 'critical', { orderData });
        this.name = 'TradingError';
    }
}

export class DatabaseError extends TradingBotError {
    constructor(message: string, query?: string) {
        super(message, 'DATABASE_ERROR', 'high', { query });
        this.name = 'DatabaseError';
    }
}

export class ConfigurationError extends TradingBotError {
    constructor(message: string, configKey?: string) {
        super(message, 'CONFIG_ERROR', 'medium', { configKey });
        this.name = 'ConfigurationError';
    }
}

/**
 * 错误日志记录器
 */
export class ErrorLogger {
    private static instance: ErrorLogger;
    private logs: TradingBotError[] = [];
    private maxLogs = 1000;

    static getInstance(): ErrorLogger {
        if (!ErrorLogger.instance) {
            ErrorLogger.instance = new ErrorLogger();
        }
        return ErrorLogger.instance;
    }

    log(error: TradingBotError | Error, context?: Record<string, any>) {
        const tradingError = error instanceof TradingBotError 
            ? error 
            : new TradingBotError(error.message, 'SYSTEM_ERROR', 'medium', context);

        // 添加到内存日志
        this.logs.unshift(tradingError);
        if (this.logs.length > this.maxLogs) {
            this.logs = this.logs.slice(0, this.maxLogs);
        }

        // 控制台输出（开发环境）
        if (process.env.NODE_ENV === 'development') {
            console.error('🚨 Trading Bot Error:', {
                ...tradingError.toJSON(),
                context,
            });
        }

        // 生产环境可以发送到监控服务
        if (process.env.NODE_ENV === 'production' && tradingError.severity === 'critical') {
            this.sendToMonitoring(tradingError, context);
        }
    }

    getRecentErrors(limit: number = 50): TradingBotError[] {
        return this.logs.slice(0, limit);
    }

    getErrorsByCode(code: string): TradingBotError[] {
        return this.logs.filter(error => error.code === code);
    }

    getErrorsBySeverity(severity: string): TradingBotError[] {
        return this.logs.filter(error => error.severity === severity);
    }

    clearLogs() {
        this.logs = [];
    }

    private async sendToMonitoring(error: TradingBotError, context?: Record<string, any>) {
        try {
            // 这里可以集成 Sentry、DataDog 等监控服务
            // 或者发送到 Cloudflare Analytics
            console.error('Critical Error - Should be sent to monitoring:', {
                error: error.toJSON(),
                context,
            });
        } catch (e) {
            console.error('Failed to send error to monitoring:', e);
        }
    }
}

/**
 * 全局错误处理器
 */
export function handleError(error: unknown, context?: Record<string, any>): TradingBotError {
    const logger = ErrorLogger.getInstance();

    if (error instanceof TradingBotError) {
        logger.log(error, context);
        return error;
    }

    if (error instanceof Error) {
        const tradingError = new TradingBotError(error.message, 'SYSTEM_ERROR', 'medium', context);
        logger.log(tradingError, context);
        return tradingError;
    }

    const unknownError = new TradingBotError(
        String(error) || 'Unknown error occurred',
        'UNKNOWN_ERROR',
        'medium',
        { originalError: error, ...context }
    );
    logger.log(unknownError, context);
    return unknownError;
}

/**
 * API 路由错误处理中间件
 */
export function createApiErrorHandler() {
    return (error: unknown, req?: Request) => {
        const tradingError = handleError(error, {
            url: req?.url,
            method: req?.method,
            timestamp: new Date().toISOString(),
        });

        // 根据错误类型返回适当的 HTTP 状态码
        let status = 500;
        switch (tradingError.code) {
            case 'VALIDATION_ERROR':
                status = 400;
                break;
            case 'AUTH_ERROR':
                status = 401;
                break;
            case 'NOT_FOUND':
                status = 404;
                break;
            case 'TRADING_ERROR':
            case 'DATABASE_ERROR':
                status = 500;
                break;
            case 'CONFIG_ERROR':
                status = 422;
                break;
        }

        return {
            error: {
                code: tradingError.code,
                message: tradingError.message,
                severity: tradingError.severity,
                timestamp: tradingError.timestamp.toISOString(),
                // 在生产环境中不要暴露敏感信息
                ...(process.env.NODE_ENV === 'development' && {
                    metadata: tradingError.metadata,
                    stack: tradingError.stack,
                }),
            },
            status,
        };
    };
}

/**
 * 用户友好的错误信息映射
 */
export const ERROR_MESSAGES = {
    VALIDATION_ERROR: '输入数据格式不正确，请检查后重试',
    AUTH_ERROR: '身份验证失败，请重新登录',
    TRADING_ERROR: '交易执行失败，请稍后重试',
    DATABASE_ERROR: '数据保存失败，请稍后重试',
    CONFIG_ERROR: '配置参数错误，请检查设置',
    NETWORK_ERROR: '网络连接失败，请检查网络连接',
    API_RATE_LIMIT: '请求过于频繁，请稍后重试',
    INSUFFICIENT_BALANCE: '账户余额不足',
    MARKET_CLOSED: '市场已关闭',
    UNKNOWN_ERROR: '系统错误，请联系技术支持',
} as const;

/**
 * 获取用户友好的错误信息
 */
export function getUserFriendlyMessage(error: TradingBotError): string {
    return ERROR_MESSAGES[error.code as keyof typeof ERROR_MESSAGES] || ERROR_MESSAGES.UNKNOWN_ERROR;
}

/**
 * 错误重试机制
 */
export class RetryHandler {
    static async withRetry<T>(
        operation: () => Promise<T>,
        maxRetries: number = 3,
        delayMs: number = 1000,
        backoffMultiplier: number = 2
    ): Promise<T> {
        let lastError: Error;
        let delay = delayMs;

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                return await operation();
            } catch (error) {
                lastError = error instanceof Error ? error : new Error(String(error));
                
                if (attempt === maxRetries) {
                    throw new TradingBotError(
                    `Operation failed after ${maxRetries + 1} attempts: ${lastError.message}`,
                        'RETRY_EXHAUSTED',
                        'high',
                        { attempts: attempt + 1, lastError: lastError.message }
                    );
                }

                // 等待后重试
                await new Promise(resolve => setTimeout(resolve, delay));
                delay *= backoffMultiplier;
            }
        }

        throw lastError!;
    }
}

/**
 * 性能监控错误
 */
export class PerformanceError extends TradingBotError {
    constructor(operation: string, duration: number, threshold: number) {
        super(
            `Operation '${operation}' took ${duration}ms, exceeding threshold of ${threshold}ms`,
            'PERFORMANCE_ERROR',
            'medium',
            { operation, duration, threshold }
        );
        this.name = 'PerformanceError';
    }
}

/**
 * 性能监控装饰器
 */
export function withPerformanceMonitoring<T extends (...args: any[]) => Promise<any>>(
    fn: T,
    operationName: string,
    thresholdMs: number = 5000
): T {
    return (async (...args: any[]) => {
        const start = Date.now();
        try {
            const result = await fn(...args);
            const duration = Date.now() - start;
            
            if (duration > thresholdMs) {
                const logger = ErrorLogger.getInstance();
                logger.log(new PerformanceError(operationName, duration, thresholdMs));
            }
            
            return result;
        } catch (error) {
            const duration = Date.now() - start;
            throw handleError(error, { operation: operationName, duration });
        }
    }) as T;
}