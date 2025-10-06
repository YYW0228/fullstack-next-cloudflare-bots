# 🔌 API 文档

## 概览

反向跟单机器人提供完整的 RESTful API，支持策略管理、交易监控和用户认证。

## 基础信息

- **Base URL**: `https://your-domain.com/api`
- **认证方式**: Bearer Token (Better Auth)
- **数据格式**: JSON
- **HTTP 状态码**: 标准 RESTful 状态码

## 认证 API

### POST /api/auth/signin
用户登录

**请求体:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应:**
```json
{
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "name": "User Name"
  },
  "session": {
    "token": "jwt_token_here",
    "expiresAt": "2024-01-01T00:00:00Z"
  }
}
```

### POST /api/auth/signup
用户注册

**请求体:**
```json
{
  "email": "newuser@example.com",
  "password": "password123",
  "name": "New User"
}
```

### POST /api/auth/signout
用户登出

## 策略实例管理 API

### GET /api/trading-bots
获取用户的所有策略实例

**查询参数:**
- `status` (可选): `running` | `stopped` | `paused` | `error`
- `strategyType` (可选): `simple-reverse` | `turtle-reverse`

**响应:**
```json
{
  "instances": [
    {
      "id": "bot_123",
      "name": "我的BTC简单反向",
      "marketPair": "BTC-USDT-SWAP",
      "strategyType": "simple-reverse",
      "status": "running",
      "config": {
        "basePositionSize": 10,
        "maxPositionSize": 100,
        "profitTarget": 0.30,
        "stopLoss": -0.15,
        "maxConcurrentPositions": 5,
        "positionTimeoutHours": 6
      },
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

### POST /api/trading-bots
创建新的策略实例

**请求体:**
```json
{
  "name": "我的新策略",
  "marketPair": "BTC-USDT-SWAP",
  "strategyType": "turtle-reverse",
  "config": {
    "positionSizes": {
      "1": 10, "2": 20, "3": 30, "4": 40,
      "5": 50, "6": 60, "7": 70, "8": 80
    },
    "profitThresholds": {
      "1": 0.0, "2": 0.0, "3": 0.50, "4": 0.30,
      "5": 0.30, "6": 0.30, "7": 0.30, "8": 0.30
    },
    "closeRatios": {
      "1": 0.0, "2": 0.0, "3": 0.50, "4": 0.80,
      "5": 0.90, "6": 0.90, "7": 0.90, "8": 1.00
    },
    "emergencyStopLoss": -0.20,
    "sequenceTimeoutHours": 8,
    "maxPositionSize": 1000
  }
}
```

### GET /api/trading-bots/{id}
获取特定策略实例详情

### PUT /api/trading-bots/{id}
更新策略实例

### DELETE /api/trading-bots/{id}
删除策略实例

### POST /api/trading-bots/{id}/start
启动策略实例

### POST /api/trading-bots/{id}/stop
停止策略实例

## 交易历史 API

### GET /api/trading-bots/history
获取交易历史记录

**查询参数:**
- `instanceId` (可选): 特定策略实例ID
- `startDate` (可选): 开始日期 (ISO 8601)
- `endDate` (可选): 结束日期 (ISO 8601)
- `limit` (可选): 返回记录数量限制 (默认50)
- `offset` (可选): 分页偏移量

**响应:**
```json
{
  "trades": [
    {
      "id": "trade_123",
      "instanceId": "bot_123",
      "type": "simple" | "turtle",
      "side": "开多" | "开空",
      "size": 10.5,
      "entryPrice": 50000.0,
      "exitPrice": 51000.0,
      "pnl": 1000.0,
      "pnlPercentage": 0.02,
      "status": "closed",
      "openedAt": "2024-01-01T00:00:00Z",
      "closedAt": "2024-01-01T01:00:00Z",
      "closeReason": "profit_target"
    }
  ],
  "pagination": {
    "total": 100,
    "limit": 50,
    "offset": 0,
    "hasMore": true
  }
}
```

## Webhook API (for Telegram signals)

### POST /webhook/telegram
接收 Telegram 信号

**请求体:**
```json
{
  "message": {
    "text": "[开多] 数量:1 市场:BTC-USDT-SWAP"
  }
}
```

**响应:**
```json
{
  "status": "received",
  "processed": true,
  "message": "Signal processed successfully"
}
```

## 错误响应格式

所有错误响应遵循统一格式:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数无效",
    "details": {
      "field": "marketPair",
      "reason": "不支持的交易对"
    }
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## HTTP 状态码

- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证
- `403 Forbidden`: 权限不足
- `404 Not Found`: 资源不存在
- `429 Too Many Requests`: 请求频率限制
- `500 Internal Server Error`: 服务器内部错误

## 限流政策

- **认证 API**: 每分钟最多 10 次请求
- **策略管理 API**: 每分钟最多 60 次请求
- **历史查询 API**: 每分钟最多 30 次请求
- **Webhook API**: 每秒最多 5 次请求

## 示例代码

### JavaScript/TypeScript
```typescript
const apiClient = {
  baseURL: 'https://your-domain.com/api',
  token: localStorage.getItem('auth_token'),
  
  async request(endpoint: string, options: RequestInit = {}) {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`,
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    
    return response.json();
  },
  
  // 获取策略列表
  async getBots() {
    return this.request('/trading-bots');
  },
  
  // 创建新策略
  async createBot(data: any) {
    return this.request('/trading-bots', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};
```

### Python
```python
import requests
from typing import Dict, Any

class TradingBotAPI:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
    
    def get_bots(self) -> Dict[str, Any]:
        response = requests.get(
            f'{self.base_url}/trading-bots',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def create_bot(self, data: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(
            f'{self.base_url}/trading-bots',
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
```

## 安全注意事项

1. **API 密钥管理**: 始终使用 HTTPS，不要在客户端代码中硬编码 API 密钥
2. **输入验证**: 所有输入都会进行严格验证
3. **CORS 配置**: 生产环境需要正确配置 CORS 策略
4. **日志记录**: 敏感信息不会记录在日志中

## 版本控制

当前 API 版本: `v1`

版本控制通过 URL 路径实现: `/api/v1/trading-bots`

## 支持

如有问题请联系技术支持或查看 GitHub Issues。