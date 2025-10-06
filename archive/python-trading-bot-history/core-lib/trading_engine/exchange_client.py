"""
交易所客户端 - 与市场对话的桥梁

设计哲学：
"与市场对话需要耐心、准确和韧性。
每一次API调用都承载着我们的期望，每一次重试都体现着我们的坚持。"
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import ccxt

from core.config import get_config
from core.logger import get_logger
from core.exceptions import NetworkException, APIException, ExecutionException


class ExchangeStatus(Enum):
    """交易所状态"""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"
    MAINTENANCE = "MAINTENANCE"


@dataclass
class ExchangeConfig:
    """交易所配置"""
    name: str
    api_key: str
    secret: str
    password: str
    sandbox_mode: bool = True
    rate_limit: bool = True
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class MarketInfo:
    """市场信息"""
    symbol: str
    base: str
    quote: str
    active: bool
    min_amount: float
    max_amount: float
    amount_precision: int
    price_precision: int
    fees: Dict[str, float]


class ExchangeClient:
    """
    交易所客户端 - 智慧的市场连接器
    
    设计原则：
    1. 连接管理：稳定的连接和自动重连
    2. 错误处理：优雅的错误恢复和重试机制
    3. 性能优化：请求缓存和批量处理
    4. 安全保障：API密钥管理和请求签名
    """
    
    def __init__(self, exchange_config: Optional[ExchangeConfig] = None):
        self.logger = get_logger("ExchangeClient")
        
        # 使用提供的配置或从全局配置获取
        if exchange_config:
            self.config = exchange_config
        else:
            config = get_config()
            self.config = ExchangeConfig(
                name="okx",
                api_key=config.exchange.api_key,
                secret=config.exchange.secret,
                password=config.exchange.password,
                sandbox_mode=config.exchange.sandbox_mode,
                rate_limit=config.exchange.enable_rate_limit
            )
        
        # 交易所实例
        self.exchange: Optional[ccxt.Exchange] = None
        self.status = ExchangeStatus.DISCONNECTED
        
        # 市场信息缓存
        self.markets_cache: Dict[str, MarketInfo] = {}
        self.cache_expiry = 3600  # 1小时
        self.last_markets_update = 0
        
        # 请求统计
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0,
            'last_request_time': None,
            'rate_limit_hits': 0
        }
        
        # 连接管理
        self.last_heartbeat = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
    
    async def initialize(self) -> bool:
        """
        初始化交易所连接
        
        Returns:
            是否初始化成功
        """
        try:
            self.status = ExchangeStatus.CONNECTING
            
            # 创建交易所实例
            self.exchange = ccxt.okx({
                'apiKey': self.config.api_key,
                'secret': self.config.secret,
                'password': self.config.password,
                'enableRateLimit': self.config.rate_limit,
                'timeout': self.config.timeout * 1000,  # ccxt使用毫秒
                'options': {
                    'defaultType': 'swap',
                    'adjustForTimeDifference': True
                }
            })
            
            # 设置沙盒模式
            if self.config.sandbox_mode:
                self.exchange.set_sandbox_mode(True)
                self.exchange.headers.update({'x-simulated-trading': '1'})
                self.logger.info("已启用沙盒模式")
            
            # 测试连接
            await self._test_connection()
            
            # 加载市场信息
            await self._load_markets()
            
            self.status = ExchangeStatus.CONNECTED
            self.last_heartbeat = time.time()
            self.reconnect_attempts = 0
            
            self.logger.info(f"交易所 {self.config.name} 连接成功")
            return True
            
        except Exception as e:
            self.status = ExchangeStatus.ERROR
            self.logger.exception(f"交易所初始化失败: {str(e)}")
            return False
    
    async def _test_connection(self):
        """测试连接"""
        try:
            # 获取账户信息来测试连接
            await self._make_request('fetch_balance')
            self.logger.info("连接测试成功")
        except Exception as e:
            raise NetworkException(f"连接测试失败: {str(e)}")
    
    async def _load_markets(self):
        """加载市场信息"""
        try:
            markets_data = await self._make_request('load_markets')
            
            for symbol, market in markets_data.items():
                self.markets_cache[symbol] = MarketInfo(
                    symbol=symbol,
                    base=market.get('base', ''),
                    quote=market.get('quote', ''),
                    active=market.get('active', False),
                    min_amount=market.get('limits', {}).get('amount', {}).get('min', 0.0),
                    max_amount=market.get('limits', {}).get('amount', {}).get('max', float('inf')),
                    amount_precision=market.get('precision', {}).get('amount', 8),
                    price_precision=market.get('precision', {}).get('price', 8),
                    fees=market.get('fees', {})
                )
            
            self.last_markets_update = time.time()
            self.logger.info(f"已加载 {len(self.markets_cache)} 个市场信息")
            
        except Exception as e:
            self.logger.exception(f"加载市场信息失败: {str(e)}")
    
    async def _make_request(self, method: str, *args, **kwargs) -> Any:
        """
        发起API请求
        
        Args:
            method: API方法名
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            API响应结果
        """
        if not self.exchange:
            raise NetworkException("交易所未初始化")
        
        start_time = time.time()
        self.request_stats['total_requests'] += 1
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # 获取方法
                func = getattr(self.exchange, method)
                
                # 执行请求
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    # 对于同步方法，在执行器中运行
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, func, *args, **kwargs)
                
                # 更新统计
                response_time = time.time() - start_time
                self._update_request_stats(True, response_time)
                
                return result
                
            except ccxt.RateLimitExceeded as e:
                self.request_stats['rate_limit_hits'] += 1
                self.logger.warning(f"触发速率限制，等待 {self.config.retry_delay} 秒")
                
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                else:
                    raise APIException(f"速率限制超时: {str(e)}")
            
            except ccxt.NetworkError as e:
                self.logger.warning(f"网络错误 (尝试 {attempt + 1}/{self.config.max_retries + 1}): {str(e)}")
                
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                else:
                    raise NetworkException(f"网络错误: {str(e)}")
            
            except ccxt.ExchangeError as e:
                self.logger.error(f"交易所错误: {str(e)}")
                raise APIException(f"交易所错误: {str(e)}")
            
            except Exception as e:
                self.logger.exception(f"未知错误: {str(e)}")
                raise ExecutionException(f"请求执行失败: {str(e)}")
        
        # 更新失败统计
        self._update_request_stats(False, time.time() - start_time)
    
    def _update_request_stats(self, success: bool, response_time: float):
        """更新请求统计"""
        if success:
            self.request_stats['successful_requests'] += 1
        else:
            self.request_stats['failed_requests'] += 1
        
        # 更新平均响应时间
        total_requests = self.request_stats['successful_requests']
        if total_requests > 0:
            current_avg = self.request_stats['avg_response_time']
            self.request_stats['avg_response_time'] = (
                (current_avg * (total_requests - 1) + response_time) / total_requests
            )
        
        self.request_stats['last_request_time'] = datetime.utcnow().isoformat()
    
    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建订单
        
        Args:
            symbol: 交易对
            order_type: 订单类型 (market, limit)
            side: 买卖方向 (buy, sell)
            amount: 数量
            price: 价格 (限价单需要)
            params: 额外参数
            
        Returns:
            订单信息
        """
        try:
            # 验证市场信息
            if not await self._validate_order_params(symbol, amount, price):
                raise ExecutionException("订单参数验证失败")
            
            # 构建参数
            order_params = params or {}
            
            # 发起订单请求
            if order_type.lower() == 'market':
                result = await self._make_request(
                    'create_market_order',
                    symbol, side, amount, params=order_params
                )
            else:
                result = await self._make_request(
                    'create_limit_order',
                    symbol, side, amount, price, params=order_params
                )
            
            self.logger.info(
                f"订单创建成功: {side} {amount} {symbol} @ {price or 'market'}",
                trade_data={
                    'order_id': result.get('id'),
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': price,
                    'type': order_type
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.exception(f"创建订单失败: {str(e)}")
            raise
    
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """取消订单"""
        try:
            result = await self._make_request('cancel_order', order_id, symbol)
            
            self.logger.info(
                f"订单取消成功: {order_id}",
                trade_data={'order_id': order_id, 'symbol': symbol}
            )
            
            return result
            
        except Exception as e:
            self.logger.exception(f"取消订单失败: {str(e)}")
            raise
    
    async def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """获取订单信息"""
        return await self._make_request('fetch_order', order_id, symbol)
    
    async def fetch_orders(self, symbol: str, since: Optional[int] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取订单列表"""
        return await self._make_request('fetch_orders', symbol, since, limit)
    
    async def fetch_balance(self) -> Dict[str, Any]:
        """获取账户余额"""
        return await self._make_request('fetch_balance')
    
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取价格行情"""
        return await self._make_request('fetch_ticker', symbol)
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', since: Optional[int] = None, limit: Optional[int] = None) -> List[List]:
        """获取K线数据"""
        return await self._make_request('fetch_ohlcv', symbol, timeframe, since, limit)
    
    async def fetch_positions(self, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """获取持仓信息"""
        return await self._make_request('fetch_positions', symbols)
    
    async def _validate_order_params(self, symbol: str, amount: float, price: Optional[float]) -> bool:
        """验证订单参数"""
        # 检查市场信息
        if symbol not in self.markets_cache:
            # 尝试重新加载市场信息
            if time.time() - self.last_markets_update > self.cache_expiry:
                await self._load_markets()
        
        market = self.markets_cache.get(symbol)
        if not market:
            self.logger.error(f"未找到市场信息: {symbol}")
            return False
        
        if not market.active:
            self.logger.error(f"市场已停止交易: {symbol}")
            return False
        
        # 检查数量限制
        if amount < market.min_amount:
            self.logger.error(f"订单数量低于最小限制: {amount} < {market.min_amount}")
            return False
        
        if amount > market.max_amount:
            self.logger.error(f"订单数量超过最大限制: {amount} > {market.max_amount}")
            return False
        
        # 检查精度
        amount_str = f"{amount:.{market.amount_precision}f}"
        if float(amount_str) != amount:
            self.logger.warning(f"订单数量精度调整: {amount} -> {amount_str}")
        
        return True
    
    async def check_connection(self) -> bool:
        """检查连接状态"""
        try:
            await self._make_request('fetch_status')
            self.last_heartbeat = time.time()
            return True
        except Exception:
            return False
    
    async def reconnect(self) -> bool:
        """重新连接"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error("达到最大重连次数，停止重连")
            return False
        
        self.reconnect_attempts += 1
        self.logger.info(f"尝试重连 (第 {self.reconnect_attempts} 次)")
        
        try:
            self.status = ExchangeStatus.CONNECTING
            await asyncio.sleep(min(self.reconnect_attempts * 2, 30))  # 指数退避
            
            return await self.initialize()
            
        except Exception as e:
            self.logger.exception(f"重连失败: {str(e)}")
            return False
    
    def get_market_info(self, symbol: str) -> Optional[MarketInfo]:
        """获取市场信息"""
        return self.markets_cache.get(symbol)
    
    def get_status(self) -> Dict[str, Any]:
        """获取客户端状态"""
        return {
            'status': self.status.value,
            'config': {
                'name': self.config.name,
                'sandbox_mode': self.config.sandbox_mode,
                'rate_limit': self.config.rate_limit,
                'timeout': self.config.timeout
            },
            'connection': {
                'last_heartbeat': self.last_heartbeat,
                'reconnect_attempts': self.reconnect_attempts,
                'max_reconnect_attempts': self.max_reconnect_attempts
            },
            'markets': {
                'total_markets': len(self.markets_cache),
                'last_update': self.last_markets_update
            },
            'statistics': self.request_stats
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取详细统计信息"""
        total_requests = self.request_stats['total_requests']
        success_rate = (
            self.request_stats['successful_requests'] / total_requests * 100
            if total_requests > 0 else 0
        )
        
        return {
            **self.request_stats,
            'success_rate': f"{success_rate:.2f}%",
            'connection_uptime': time.time() - self.last_heartbeat if self.last_heartbeat else 0,
            'markets_cached': len(self.markets_cache)
        }