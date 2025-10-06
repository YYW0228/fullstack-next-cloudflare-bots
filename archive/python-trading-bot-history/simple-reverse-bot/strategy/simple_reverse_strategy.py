"""
简单反向策略 - 30%固定止盈的智慧

设计哲学：
"简单即是美，稳健胜过激进。
30%的确定性收益胜过100%的不确定性梦想。"
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core-lib"))

from core.logger import get_logger
from core.exceptions import StrategyException
from trading_engine.order_executor import OrderExecutor, OrderRequest, OrderType, OrderSide
from signal_processor.signal_parser import ParsedSignal, SignalAction
from signal_processor.signal_validator import ValidationResult
from utils.time_utils import Timer


@dataclass
class SimplePosition:
    """简单仓位记录"""
    id: str
    symbol: str
    side: str                    # "开多" or "开空"
    size: float
    entry_price: float
    current_price: float = 0.0
    created_at: datetime = None
    order_id: str = ""
    strategy_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.strategy_metadata is None:
            self.strategy_metadata = {}
    
    def calculate_pnl_percentage(self) -> float:
        """计算盈亏百分比"""
        if self.entry_price <= 0 or self.current_price <= 0:
            return 0.0
        
        if self.side == "开多":
            return (self.current_price - self.entry_price) / self.entry_price
        else:  # 开空
            return (self.entry_price - self.current_price) / self.entry_price
    
    def calculate_pnl_amount(self) -> float:
        """计算盈亏金额"""
        return self.calculate_pnl_percentage() * self.entry_price * self.size
    
    def should_take_profit(self, target_percentage: float = 0.30) -> bool:
        """是否应该止盈"""
        return self.calculate_pnl_percentage() >= target_percentage
    
    def should_stop_loss(self, stop_percentage: float = -0.15) -> bool:
        """是否应该止损"""
        return self.calculate_pnl_percentage() <= stop_percentage
    
    def is_timeout(self, timeout_hours: int = 6) -> bool:
        """是否超时"""
        return datetime.utcnow() - self.created_at > timedelta(hours=timeout_hours)


class SimpleReverseStrategy:
    """
    简单反向策略 - 追求稳健收益的智慧策略
    
    核心理念：
    1. 完全反向：信号开空我们开多，信号开多我们开空
    2. 快进快出：只用市价单，追求执行速度
    3. 固定止盈：每个仓位达到30%收益立即平仓
    4. 独立处理：每个信号独立开仓，互不影响
    5. 严格风控：超时、止损双重保护
    """
    
    def __init__(self, config, order_executor: OrderExecutor):
        self.config = config
        self.order_executor = order_executor
        self.logger = get_logger("SimpleReverseStrategy")
        
        # 策略参数
        self.params = {
            'profit_target': 0.30,           # 30%止盈目标
            'stop_loss': -0.15,              # 15%止损
            'position_timeout_hours': 6,     # 6小时超时
            'max_concurrent_positions': 5,   # 最大并发仓位数
            'base_position_size': 10,        # 基础仓位大小(张)
            'max_position_size': 100,        # 单个仓位最大大小
            'min_signal_confidence': 0.3,    # 最低信号置信度
            'price_update_interval': 3       # 价格更新间隔(秒)
        }
        
        # 活跃仓位管理
        self.active_positions: Dict[str, SimplePosition] = {}
        
        # 策略状态
        self.is_running = False
        self.total_signals = 0
        self.executed_signals = 0
        self.total_trades = 0
        self.successful_trades = 0
        self.total_pnl = 0.0
        
        # 监控任务
        self.monitor_task: Optional[asyncio.Task] = None
        
        # 订单回调
        self.order_executor.add_callback(self._on_order_completed)
        
        self.logger.info(f"简单反向策略已创建，目标止盈: {self.params['profit_target']:.1%}")
    
    def start(self) -> bool:
        """启动策略"""
        try:
            if self.is_running:
                return True
            
            self.is_running = True
            
            # 启动价格监控任务
            self.monitor_task = asyncio.create_task(self._monitor_positions())
            
            self.logger.info("简单反向策略已启动")
            return True
            
        except Exception as e:
            self.logger.exception(f"策略启动失败: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """停止策略"""
        try:
            self.is_running = False
            
            # 取消监控任务
            if self.monitor_task and not self.monitor_task.done():
                self.monitor_task.cancel()
            
            self.logger.info("简单反向策略已停止")
            return True
            
        except Exception as e:
            self.logger.exception(f"策略停止失败: {str(e)}")
            return False
    
    async def process_signal(self, signal: ParsedSignal, validation_result: ValidationResult):
        """
        处理信号 - 策略的核心入口
        
        Args:
            signal: 解析后的信号
            validation_result: 验证结果
        """
        try:
            self.total_signals += 1
            
            # 检查策略状态
            if not self.is_running:
                self.logger.warning("策略未运行，忽略信号")
                return
            
            # 验证信号质量
            if not self._validate_signal(signal, validation_result):
                return
            
            # 检查并发仓位限制
            if len(self.active_positions) >= self.params['max_concurrent_positions']:
                self.logger.warning(f"达到最大并发仓位限制: {len(self.active_positions)}")
                return
            
            # 只处理开仓信号
            if signal.action not in [SignalAction.OPEN_LONG, SignalAction.OPEN_SHORT]:
                self.logger.info("忽略非开仓信号")
                return
            
            # 执行反向开仓
            await self._execute_reverse_entry(signal, validation_result)
            
        except Exception as e:
            self.logger.exception(f"处理信号异常: {str(e)}")
    
    def _validate_signal(self, signal: ParsedSignal, validation_result: ValidationResult) -> bool:
        """验证信号有效性"""
        # 检查信号置信度
        if validation_result.confidence_score < self.params['min_signal_confidence']:
            self.logger.info(f"信号置信度过低: {validation_result.confidence_score:.2f}")
            return False
        
        # 检查信号验证结果
        if not validation_result.is_valid:
            self.logger.warning("信号验证失败")
            return False
        
        return True
    
    async def _execute_reverse_entry(self, signal: ParsedSignal, validation_result: ValidationResult):
        """执行反向开仓"""
        try:
            # 确定反向动作
            reverse_side = self._get_reverse_side(signal.action)
            
            # 计算仓位大小
            position_size = self._calculate_position_size(signal, validation_result)
            
            # 创建仓位记录
            position_id = f"simple_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # 创建订单请求
            order_request = OrderRequest(
                id=f"order_{position_id}",
                symbol=signal.symbol,
                order_type=OrderType.MARKET,  # 只使用市价单
                side=OrderSide.BUY if reverse_side == "开多" else OrderSide.SELL,
                amount=position_size,
                strategy_name="SimpleReverse",
                metadata={
                    'position_id': position_id,
                    'original_signal': signal.to_dict(),
                    'reverse_side': reverse_side,
                    'expected_profit': self.params['profit_target']
                }
            )
            
            # 提交订单
            order_id = await self.order_executor.submit_order(order_request)
            
            # 创建仓位记录（等待订单成交后更新价格）
            position = SimplePosition(
                id=position_id,
                symbol=signal.symbol,
                side=reverse_side,
                size=position_size,
                entry_price=0.0,  # 等待订单成交后更新
                order_id=order_id,
                strategy_metadata={
                    'signal_quantity': signal.quantity,
                    'signal_confidence': validation_result.confidence_score,
                    'original_action': signal.action.value
                }
            )
            
            # 添加到活跃仓位
            self.active_positions[position_id] = position
            
            self.executed_signals += 1
            
            self.logger.info(
                f"反向开仓: 信号{signal.action.value} → 我们{reverse_side} {position_size}张 {signal.symbol}",
                trade_data={
                    'position_id': position_id,
                    'order_id': order_id,
                    'reverse_side': reverse_side,
                    'size': position_size,
                    'original_signal_quantity': signal.quantity
                }
            )
            
        except Exception as e:
            self.logger.exception(f"反向开仓失败: {str(e)}")
    
    def _get_reverse_side(self, original_action: SignalAction) -> str:
        """获取反向交易方向"""
        reverse_mapping = {
            SignalAction.OPEN_LONG: "开空",   # 信号开多，我们开空
            SignalAction.OPEN_SHORT: "开多",  # 信号开空，我们开多
        }
        return reverse_mapping.get(original_action, "")
    
    def _calculate_position_size(self, signal: ParsedSignal, validation_result: ValidationResult) -> float:
        """计算仓位大小"""
        # 基础仓位
        base_size = self.params['base_position_size']
        
        # 根据信号数量调整
        quantity_multiplier = signal.quantity
        position_size = base_size * quantity_multiplier
        
        # 根据信号置信度调整
        confidence_factor = max(0.5, validation_result.confidence_score)
        position_size *= confidence_factor
        
        # 应用最大仓位限制
        position_size = min(position_size, self.params['max_position_size'])
        
        return round(position_size, 1)
    
    async def _on_order_completed(self, order_request: OrderRequest, order_result):
        """订单完成回调"""
        try:
            position_id = order_request.metadata.get('position_id')
            if not position_id or position_id not in self.active_positions:
                return
            
            position = self.active_positions[position_id]
            
            if order_result.status.value == "FILLED":
                # 订单成交，更新仓位信息
                position.entry_price = order_result.average_price
                position.current_price = order_result.average_price
                
                self.logger.info(
                    f"开仓成交: {position.side} {position.size}张 @ {position.entry_price}",
                    trade_data={
                        'position_id': position_id,
                        'entry_price': position.entry_price,
                        'size': position.size
                    }
                )
            else:
                # 订单失败，移除仓位记录
                del self.active_positions[position_id]
                self.logger.error(f"开仓失败: {order_result.error_message}")
                
        except Exception as e:
            self.logger.exception(f"订单回调处理异常: {str(e)}")
    
    async def _monitor_positions(self):
        """监控仓位状态"""
        while self.is_running:
            try:
                if not self.active_positions:
                    await asyncio.sleep(self.params['price_update_interval'])
                    continue
                
                # 获取所有活跃仓位的当前价格
                await self._update_positions_prices()
                
                # 检查平仓条件
                positions_to_close = []
                
                for position_id, position in list(self.active_positions.items()):
                    close_reason = self._check_close_conditions(position)
                    if close_reason:
                        positions_to_close.append((position, close_reason))
                
                # 执行平仓
                for position, reason in positions_to_close:
                    await self._close_position(position, reason)
                
                await asyncio.sleep(self.params['price_update_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"仓位监控异常: {str(e)}")
                await asyncio.sleep(10)
    
    async def _update_positions_prices(self):
        """更新仓位价格"""
        # 获取所有需要更新的交易对
        symbols = list(set(pos.symbol for pos in self.active_positions.values()))
        
        for symbol in symbols:
            try:
                # 这里需要从exchange_client获取价格
                # 简化处理，实际需要实现价格获取接口
                ticker = await self._get_ticker(symbol)
                current_price = ticker.get('last', 0)
                
                # 更新所有该交易对的仓位价格
                for position in self.active_positions.values():
                    if position.symbol == symbol:
                        position.current_price = current_price
                        
            except Exception as e:
                self.logger.warning(f"更新价格失败 {symbol}: {str(e)}")
    
    async def _get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取价格行情（需要实现）"""
        # 这里应该调用exchange_client的接口
        # 暂时返回模拟数据
        return {'last': 50000.0}  # 需要实现实际的价格获取
    
    def _check_close_conditions(self, position: SimplePosition) -> Optional[str]:
        """检查平仓条件"""
        if position.entry_price <= 0 or position.current_price <= 0:
            return None
        
        # 检查止盈
        if position.should_take_profit(self.params['profit_target']):
            pnl_pct = position.calculate_pnl_percentage()
            return f"止盈平仓({pnl_pct:.2%})"
        
        # 检查止损
        if position.should_stop_loss(self.params['stop_loss']):
            pnl_pct = position.calculate_pnl_percentage()
            return f"止损平仓({pnl_pct:.2%})"
        
        # 检查超时
        if position.is_timeout(self.params['position_timeout_hours']):
            return "超时平仓"
        
        return None
    
    async def _close_position(self, position: SimplePosition, reason: str):
        """平仓操作"""
        try:
            # 创建平仓订单
            close_side = OrderSide.SELL if position.side == "开多" else OrderSide.BUY
            
            order_request = OrderRequest(
                id=f"close_{position.id}_{datetime.utcnow().strftime('%H%M%S')}",
                symbol=position.symbol,
                order_type=OrderType.MARKET,  # 市价单快速平仓
                side=close_side,
                amount=position.size,
                strategy_name="SimpleReverse",
                metadata={
                    'position_id': position.id,
                    'close_reason': reason,
                    'is_closing': True
                }
            )
            
            # 提交平仓订单
            order_id = await self.order_executor.submit_order(order_request)
            
            # 计算盈亏
            pnl_amount = position.calculate_pnl_amount()
            pnl_percentage = position.calculate_pnl_percentage()
            
            # 更新统计
            self.total_trades += 1
            self.total_pnl += pnl_amount
            
            if pnl_amount > 0:
                self.successful_trades += 1
            
            # 从活跃仓位中移除
            if position.id in self.active_positions:
                del self.active_positions[position.id]
            
            self.logger.info(
                f"平仓完成: {position.symbol} {reason} 盈亏:{pnl_amount:.2f}({pnl_percentage:.2%})",
                trade_data={
                    'position_id': position.id,
                    'close_reason': reason,
                    'pnl_amount': pnl_amount,
                    'pnl_percentage': pnl_percentage,
                    'close_order_id': order_id,
                    'entry_price': position.entry_price,
                    'close_price': position.current_price
                }
            )
            
        except Exception as e:
            self.logger.exception(f"平仓失败: {position.id}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        active_count = len(self.active_positions)
        win_rate = self.successful_trades / self.total_trades if self.total_trades > 0 else 0
        
        # 计算未实现盈亏
        unrealized_pnl = sum(pos.calculate_pnl_amount() for pos in self.active_positions.values())
        
        return {
            'strategy_name': 'SimpleReverse',
            'is_running': self.is_running,
            'total_signals': self.total_signals,
            'executed_signals': self.executed_signals,
            'execution_rate': f"{self.executed_signals/self.total_signals*100:.1f}%" if self.total_signals > 0 else "0%",
            'active_positions': active_count,
            'max_positions': self.params['max_concurrent_positions'],
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'win_rate': f"{win_rate:.2%}",
            'total_pnl': self.total_pnl,
            'unrealized_pnl': unrealized_pnl,
            'profit_target': f"{self.params['profit_target']:.1%}",
            'positions': [
                {
                    'id': pos.id,
                    'symbol': pos.symbol,
                    'side': pos.side,
                    'size': pos.size,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'pnl_percentage': pos.calculate_pnl_percentage(),
                    'duration_minutes': (datetime.utcnow() - pos.created_at).total_seconds() / 60
                }
                for pos in self.active_positions.values()
            ]
        }
    
    async def emergency_close_all(self, reason: str = "紧急平仓"):
        """紧急平仓所有仓位"""
        self.logger.warning(f"执行紧急平仓: {reason}")
        
        for position in list(self.active_positions.values()):
            await self._close_position(position, f"紧急平仓({reason})")
        
        self.logger.info("所有仓位已紧急平仓")