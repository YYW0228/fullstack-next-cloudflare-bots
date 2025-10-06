"""
订单执行器 - 精确的交易执行引擎

设计哲学：
"执行即是一切，精确的执行是策略成功的保证。
每个订单都承载着策略的意图，必须被完美地执行。"
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import uuid

from ..core.logger import get_logger
from ..core.exceptions import ExecutionException, OrderExecutionException, InsufficientBalanceException
from .exchange_client import ExchangeClient


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"           # 市价单
    LIMIT = "limit"             # 限价单
    STOP = "stop"               # 停损单
    STOP_LIMIT = "stop_limit"   # 停损限价单
    TAKE_PROFIT = "take_profit" # 止盈单
    TAKE_PROFIT_LIMIT = "take_profit_limit" # 止盈限价单


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"         # 等待执行
    SUBMITTED = "SUBMITTED"     # 已提交
    FILLED = "FILLED"           # 已成交
    PARTIALLY_FILLED = "PARTIALLY_FILLED" # 部分成交
    CANCELLED = "CANCELLED"     # 已取消
    REJECTED = "REJECTED"       # 被拒绝
    EXPIRED = "EXPIRED"         # 已过期
    FAILED = "FAILED"           # 执行失败


@dataclass
class OrderRequest:
    """订单请求"""
    id: str
    symbol: str
    order_type: OrderType
    side: OrderSide
    amount: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"  # GTC, IOC, FOK
    client_order_id: Optional[str] = None
    strategy_name: str = ""
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}
        if self.client_order_id is None:
            self.client_order_id = f"order_{uuid.uuid4().hex[:8]}"


@dataclass
class OrderResult:
    """订单执行结果"""
    request_id: str
    exchange_order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_amount: float = 0.0
    remaining_amount: float = 0.0
    average_price: float = 0.0
    fees: float = 0.0
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None
    exchange_response: Optional[Dict[str, Any]] = None


class OrderExecutor:
    """
    订单执行器 - 智慧的交易执行引擎
    
    设计原则：
    1. 精确执行：确保每个订单都按预期执行
    2. 错误恢复：优雅处理执行失败和网络问题
    3. 状态跟踪：实时跟踪订单状态变化
    4. 性能监控：记录执行性能和成功率
    """
    
    def __init__(self, exchange_client: ExchangeClient):
        self.logger = get_logger("OrderExecutor")
        self.exchange_client = exchange_client
        
        # 订单管理
        self.pending_orders: Dict[str, OrderRequest] = {}
        self.completed_orders: Dict[str, OrderResult] = {}
        
        # 执行队列
        self.execution_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.is_processing = False
        
        # 执行统计
        self.execution_stats = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'total_volume': 0.0,
            'avg_execution_time': 0.0,
            'last_execution_time': None
        }
        
        # 回调函数
        self.order_callbacks: List[Callable] = []
        
        # 执行配置
        self.config = {
            'max_retries': 3,
            'retry_delay': 1.0,
            'order_timeout': 30.0,
            'slippage_tolerance': 0.005,  # 0.5%滑点容忍度
            'min_order_amount': 0.01
        }
    
    async def submit_order(self, order_request: OrderRequest) -> str:
        """
        提交订单到执行队列
        
        Args:
            order_request: 订单请求
            
        Returns:
            订单ID
        """
        try:
            # 验证订单
            self._validate_order(order_request)
            
            # 添加到待执行队列
            self.pending_orders[order_request.id] = order_request
            await self.execution_queue.put(order_request)
            
            self.logger.info(
                f"订单已提交: {order_request.side.value} {order_request.amount} {order_request.symbol}",
                trade_data={
                    'order_id': order_request.id,
                    'symbol': order_request.symbol,
                    'side': order_request.side.value,
                    'amount': order_request.amount,
                    'type': order_request.order_type.value,
                    'strategy': order_request.strategy_name
                }
            )
            
            return order_request.id
            
        except Exception as e:
            self.logger.exception(f"提交订单失败: {str(e)}")
            raise ExecutionException(f"订单提交失败: {str(e)}")
    
    def _validate_order(self, order_request: OrderRequest):
        """验证订单有效性"""
        # 检查基本参数
        if order_request.amount <= 0:
            raise OrderExecutionException("订单数量必须大于0", {
                'order_id': order_request.id,
                'amount': order_request.amount
            })
        
        if order_request.amount < self.config['min_order_amount']:
            raise OrderExecutionException(f"订单数量低于最小值: {self.config['min_order_amount']}", {
                'order_id': order_request.id,
                'amount': order_request.amount,
                'min_amount': self.config['min_order_amount']
            })
        
        # 检查限价单价格
        if order_request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
            if order_request.price is None or order_request.price <= 0:
                raise OrderExecutionException("限价单必须指定有效价格", {
                    'order_id': order_request.id,
                    'order_type': order_request.order_type.value,
                    'price': order_request.price
                })
        
        # 检查停损单停损价格
        if order_request.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            if order_request.stop_price is None or order_request.stop_price <= 0:
                raise OrderExecutionException("停损单必须指定有效停损价格", {
                    'order_id': order_request.id,
                    'order_type': order_request.order_type.value,
                    'stop_price': order_request.stop_price
                })
    
    async def start_processing(self):
        """启动订单处理"""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.logger.info("订单执行器已启动")
        
        while self.is_processing:
            try:
                # 从队列获取订单
                order_request = await asyncio.wait_for(
                    self.execution_queue.get(),
                    timeout=1.0
                )
                
                # 执行订单
                await self._execute_order(order_request)
                
                # 标记任务完成
                self.execution_queue.task_done()
                
            except asyncio.TimeoutError:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                self.logger.exception(f"订单处理异常: {str(e)}")
    
    async def stop_processing(self):
        """停止订单处理"""
        self.is_processing = False
        
        # 等待队列中的订单处理完成
        await self.execution_queue.join()
        
        self.logger.info("订单执行器已停止")
    
    async def _execute_order(self, order_request: OrderRequest):
        """执行单个订单"""
        start_time = datetime.utcnow()
        order_result = OrderResult(request_id=order_request.id)
        
        try:
            self.execution_stats['total_orders'] += 1
            
            # 执行订单
            if order_request.order_type == OrderType.MARKET:
                exchange_result = await self._execute_market_order(order_request)
            elif order_request.order_type == OrderType.LIMIT:
                exchange_result = await self._execute_limit_order(order_request)
            elif order_request.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
                exchange_result = await self._execute_stop_order(order_request)
            else:
                raise OrderExecutionException(f"不支持的订单类型: {order_request.order_type.value}")
            
            # 处理执行结果
            if exchange_result:
                order_result.exchange_order_id = exchange_result.get('id')
                order_result.status = OrderStatus.FILLED
                order_result.filled_amount = exchange_result.get('filled', 0)
                order_result.remaining_amount = order_request.amount - order_result.filled_amount
                order_result.average_price = exchange_result.get('average', 0) or exchange_result.get('price', 0)
                order_result.fees = exchange_result.get('fee', {}).get('cost', 0)
                order_result.executed_at = datetime.utcnow()
                order_result.exchange_response = exchange_result
                
                # 更新统计
                self.execution_stats['successful_orders'] += 1
                self.execution_stats['total_volume'] += order_result.filled_amount * order_result.average_price
                
                self.logger.info(
                    f"订单执行成功: {order_request.side.value} {order_result.filled_amount} {order_request.symbol} @ {order_result.average_price}",
                    trade_data={
                        'order_id': order_request.id,
                        'exchange_order_id': order_result.exchange_order_id,
                        'filled_amount': order_result.filled_amount,
                        'average_price': order_result.average_price,
                        'fees': order_result.fees
                    }
                )
            else:
                order_result.status = OrderStatus.FAILED
                order_result.error_message = "交易所返回空结果"
                self.execution_stats['failed_orders'] += 1
        
        except Exception as e:
            order_result.status = OrderStatus.FAILED
            order_result.error_message = str(e)
            self.execution_stats['failed_orders'] += 1
            
            self.logger.exception(f"订单执行失败: {order_request.id}")
        
        finally:
            # 计算执行时间
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_execution_time(execution_time)
            
            # 移除待执行订单
            if order_request.id in self.pending_orders:
                del self.pending_orders[order_request.id]
            
            # 保存执行结果
            self.completed_orders[order_request.id] = order_result
            
            # 调用回调函数
            await self._notify_callbacks(order_request, order_result)
    
    async def _execute_market_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """执行市价单"""
        try:
            # 构建订单参数
            params = {
                'posSide': 'long' if order_request.side == OrderSide.BUY else 'short'
            }
            
            # 添加策略标识
            if order_request.strategy_name:
                params['tag'] = order_request.strategy_name[:8]
            
            # 执行市价单
            result = await self.exchange_client.create_order(
                symbol=order_request.symbol,
                order_type='market',
                side=order_request.side.value,
                amount=order_request.amount,
                params=params
            )
            
            return result
            
        except Exception as e:
            if "Insufficient" in str(e) or "insufficient" in str(e):
                raise InsufficientBalanceException(
                    required_amount=order_request.amount,
                    available_amount=0  # 需要从交易所获取实际余额
                )
            raise OrderExecutionException(f"市价单执行失败: {str(e)}")
    
    async def _execute_limit_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """执行限价单"""
        try:
            params = {
                'posSide': 'long' if order_request.side == OrderSide.BUY else 'short',
                'timeInForce': order_request.time_in_force
            }
            
            if order_request.strategy_name:
                params['tag'] = order_request.strategy_name[:8]
            
            result = await self.exchange_client.create_order(
                symbol=order_request.symbol,
                order_type='limit',
                side=order_request.side.value,
                amount=order_request.amount,
                price=order_request.price,
                params=params
            )
            
            # 限价单可能需要等待成交
            if result and result.get('status') != 'closed':
                result = await self._wait_for_fill(result.get('id'), order_request.symbol)
            
            return result
            
        except Exception as e:
            raise OrderExecutionException(f"限价单执行失败: {str(e)}")
    
    async def _execute_stop_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """执行停损单"""
        try:
            params = {
                'posSide': 'long' if order_request.side == OrderSide.BUY else 'short',
                'stopPrice': order_request.stop_price
            }
            
            if order_request.strategy_name:
                params['tag'] = order_request.strategy_name[:8]
            
            order_type = 'stop' if order_request.order_type == OrderType.STOP else 'stop_limit'
            
            result = await self.exchange_client.create_order(
                symbol=order_request.symbol,
                order_type=order_type,
                side=order_request.side.value,
                amount=order_request.amount,
                price=order_request.price,
                params=params
            )
            
            return result
            
        except Exception as e:
            raise OrderExecutionException(f"停损单执行失败: {str(e)}")
    
    async def _wait_for_fill(self, order_id: str, symbol: str, timeout: float = None) -> Dict[str, Any]:
        """等待订单成交"""
        if timeout is None:
            timeout = self.config['order_timeout']
        
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            try:
                order = await self.exchange_client.fetch_order(order_id, symbol)
                
                if order.get('status') in ['closed', 'filled']:
                    return order
                elif order.get('status') in ['canceled', 'cancelled', 'rejected']:
                    raise OrderExecutionException(f"订单被取消或拒绝: {order.get('status')}")
                
                # 等待一段时间后重试
                await asyncio.sleep(1.0)
                
            except Exception as e:
                self.logger.warning(f"查询订单状态失败: {str(e)}")
                await asyncio.sleep(2.0)
        
        # 超时后尝试取消订单
        try:
            await self.exchange_client.cancel_order(order_id, symbol)
            self.logger.warning(f"订单超时已取消: {order_id}")
        except:
            pass
        
        raise OrderExecutionException(f"订单执行超时: {order_id}")
    
    def _update_execution_time(self, execution_time: float):
        """更新执行时间统计"""
        current_avg = self.execution_stats['avg_execution_time']
        total_orders = self.execution_stats['total_orders']
        
        if total_orders > 0:
            self.execution_stats['avg_execution_time'] = (
                (current_avg * (total_orders - 1) + execution_time) / total_orders
            )
        
        self.execution_stats['last_execution_time'] = datetime.utcnow().isoformat()
    
    async def _notify_callbacks(self, order_request: OrderRequest, order_result: OrderResult):
        """通知回调函数"""
        for callback in self.order_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(order_request, order_result)
                else:
                    callback(order_request, order_result)
            except Exception as e:
                self.logger.exception(f"订单回调异常: {str(e)}")
    
    def add_callback(self, callback: Callable):
        """添加订单回调函数"""
        self.order_callbacks.append(callback)
        self.logger.info(f"已添加订单回调: {callback.__name__}")
    
    def remove_callback(self, callback: Callable):
        """移除订单回调函数"""
        if callback in self.order_callbacks:
            self.order_callbacks.remove(callback)
            self.logger.info(f"已移除订单回调: {callback.__name__}")
    
    async def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        try:
            # 检查是否在待执行队列中
            if order_id in self.pending_orders:
                order_request = self.pending_orders[order_id]
                
                # 如果还未执行，直接从队列移除
                del self.pending_orders[order_id]
                
                # 创建取消结果
                order_result = OrderResult(
                    request_id=order_id,
                    status=OrderStatus.CANCELLED,
                    error_message="用户取消"
                )
                self.completed_orders[order_id] = order_result
                
                self.logger.info(f"订单已取消: {order_id}")
                return True
            
            # 如果已提交到交易所，尝试取消
            if order_id in self.completed_orders:
                order_result = self.completed_orders[order_id]
                if order_result.exchange_order_id:
                    # 需要从订单请求中获取交易对信息
                    # 这里简化处理，实际可能需要更复杂的订单状态管理
                    pass
            
            return False
            
        except Exception as e:
            self.logger.exception(f"取消订单失败: {order_id}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[OrderResult]:
        """获取订单状态"""
        return self.completed_orders.get(order_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计"""
        total_orders = self.execution_stats['total_orders']
        success_rate = (
            self.execution_stats['successful_orders'] / total_orders * 100
            if total_orders > 0 else 0
        )
        
        return {
            **self.execution_stats,
            'success_rate': f"{success_rate:.2f}%",
            'pending_orders': len(self.pending_orders),
            'completed_orders': len(self.completed_orders),
            'queue_size': self.execution_queue.qsize(),
            'is_processing': self.is_processing
        }