"""
简单反向机器人 - 稳健的反向跟单策略

设计哲学：
"简单即是美，稳健胜过激进。
30%的确定性收益胜过100%的不确定性梦想。"
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

from core.logger import get_logger
from core.exceptions import StrategyException, PositionSizeExceededException
from .base_strategy import BaseStrategy, StrategyDecision, SignalDecision
from .position_manager import PositionManager, Position, PositionSide
from signal_processor.signal_parser import ParsedSignal, SignalAction
from signal_processor.signal_validator import ValidationResult


class SimpleReverseBot(BaseStrategy):
    """
    简单反向机器人 - 追求稳健收益的智慧策略
    
    核心理念：
    1. 完全反向：信号开空我们开多，信号开多我们开空
    2. 固定止盈：每个仓位达到30%收益立即平仓
    3. 独立处理：每个信号独立开仓，互不影响
    4. 风险优先：严格的仓位和风险控制
    """
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        
        # 策略特定参数
        self.strategy_params = {
            'profit_target': 0.30,           # 30%止盈目标
            'stop_loss': -0.15,              # 15%止损
            'position_timeout_hours': 6,     # 6小时超时平仓
            'max_concurrent_positions': 5,   # 最大并发仓位数
            'base_position_size': 10,        # 基础仓位大小
            **self.params
        }
        
        # 获取外部组件
        self.exchange_client = config.get('exchange_client')
        self.position_manager = config.get('position_manager') or PositionManager()
        
        # 活跃仓位跟踪
        self.active_positions: Dict[str, Position] = {}
        
        # 监控任务
        self.monitor_task: Optional[asyncio.Task] = None
        
        self.logger.info(f"简单反向机器人已创建，止盈目标: {self.strategy_params['profit_target']:.1%}")
    
    def _initialize(self) -> bool:
        """初始化策略"""
        try:
            # 验证必要组件
            if not self.exchange_client:
                raise StrategyException("缺少交易所客户端")
            
            # 启动仓位监控
            self.monitor_task = asyncio.create_task(self._monitor_positions())
            
            self.logger.info("简单反向机器人初始化成功")
            return True
            
        except Exception as e:
            self.logger.exception(f"简单反向机器人初始化失败: {str(e)}")
            return False
    
    def _cleanup(self):
        """清理资源"""
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
    
    async def _make_decision(self, signal: ParsedSignal, validation_result: ValidationResult) -> StrategyDecision:
        """
        制定交易决策
        
        Args:
            signal: 解析后的信号
            validation_result: 验证结果
            
        Returns:
            策略决策
        """
        try:
            # 检查信号置信度
            if validation_result.confidence_score < 0.3:
                return StrategyDecision(
                    decision=SignalDecision.IGNORE,
                    reasoning=f"信号置信度过低: {validation_result.confidence_score:.2f}"
                )
            
            # 检查并发仓位限制
            if len(self.active_positions) >= self.strategy_params['max_concurrent_positions']:
                return StrategyDecision(
                    decision=SignalDecision.IGNORE,
                    reasoning=f"达到最大并发仓位限制: {len(self.active_positions)}"
                )
            
            # 只处理开仓信号（忽略平仓信号，我们自己控制平仓）
            if signal.action not in [SignalAction.OPEN_LONG, SignalAction.OPEN_SHORT]:
                return StrategyDecision(
                    decision=SignalDecision.IGNORE,
                    reasoning="忽略平仓信号，我们自主控制平仓"
                )
            
            # 计算反向动作和仓位大小
            reverse_action = self._get_reverse_action(signal.action)
            position_size = self._calculate_position_size(signal)
            
            # 风险检查
            if not self._check_risk_limits(reverse_action, position_size):
                return StrategyDecision(
                    decision=SignalDecision.IGNORE,
                    reasoning="风险限制检查未通过"
                )
            
            # 制定执行决策
            return StrategyDecision(
                decision=SignalDecision.EXECUTE,
                action=reverse_action,
                quantity=position_size,
                symbol=signal.symbol,
                confidence=validation_result.confidence_score,
                reasoning=f"反向跟单: 信号{signal.action.value}，我们{reverse_action}",
                metadata={
                    'original_signal': signal.to_dict(),
                    'strategy_type': 'simple_reverse',
                    'expected_profit': self.strategy_params['profit_target'],
                    'position_timeout': self.strategy_params['position_timeout_hours']
                }
            )
            
        except Exception as e:
            self.logger.exception(f"决策制定异常: {str(e)}")
            return StrategyDecision(
                decision=SignalDecision.IGNORE,
                reasoning=f"决策异常: {str(e)}"
            )
    
    def _get_reverse_action(self, original_action: SignalAction) -> str:
        """获取反向动作"""
        reverse_mapping = {
            SignalAction.OPEN_LONG: "开空",   # 信号开多，我们开空
            SignalAction.OPEN_SHORT: "开多",  # 信号开空，我们开多
        }
        return reverse_mapping.get(original_action, "")
    
    def _calculate_position_size(self, signal: ParsedSignal) -> float:
        """
        计算仓位大小
        
        策略：基础仓位 × 信号数量
        """
        base_size = self.strategy_params['base_position_size']
        
        # 根据信号数量调整仓位
        quantity_multiplier = signal.quantity
        position_size = base_size * quantity_multiplier
        
        # 应用风险限制
        max_size = self.params['max_position_size']
        position_size = min(position_size, max_size)
        
        # 根据信号置信度调整
        confidence_factor = max(0.5, signal.confidence)  # 最低50%
        position_size *= confidence_factor
        
        return round(position_size, 1)
    
    async def execute_decision(self, decision: StrategyDecision) -> bool:
        """
        执行交易决策
        
        Args:
            decision: 策略决策
            
        Returns:
            是否执行成功
        """
        if decision.decision != SignalDecision.EXECUTE:
            return True
        
        try:
            # 确定仓位方向
            position_side = PositionSide.LONG if decision.action == "开多" else PositionSide.SHORT
            
            # 执行开仓
            order_result = await self.exchange_client.create_order(
                symbol=decision.symbol,
                order_type='market',
                side='buy' if decision.action == "开多" else 'sell',
                amount=decision.quantity,
                params={'posSide': 'long' if decision.action == "开多" else 'short'}
            )
            
            if order_result:
                # 创建仓位记录
                position = self.position_manager.create_position(
                    symbol=decision.symbol,
                    side=position_side,
                    size=decision.quantity,
                    entry_price=order_result.get('price', 0),
                    strategy_name=self.name,
                    signal_id=decision.metadata.get('original_signal', {}).get('timestamp', ''),
                    metadata=decision.metadata
                )
                
                # 设置止盈止损
                entry_price = position.entry_price
                if position_side == PositionSide.LONG:
                    position.take_profit = entry_price * (1 + self.strategy_params['profit_target'])
                    position.stop_loss = entry_price * (1 + self.strategy_params['stop_loss'])
                else:
                    position.take_profit = entry_price * (1 - self.strategy_params['profit_target'])
                    position.stop_loss = entry_price * (1 - self.strategy_params['stop_loss'])
                
                # 添加到活跃仓位
                self.active_positions[position.id] = position
                
                self.logger.info(
                    f"反向开仓成功: {decision.action} {decision.quantity} {decision.symbol}",
                    trade_data={
                        'position_id': position.id,
                        'entry_price': entry_price,
                        'take_profit': position.take_profit,
                        'stop_loss': position.stop_loss,
                        'order_result': order_result
                    }
                )
                
                return True
            
        except Exception as e:
            self.logger.exception(f"执行交易决策失败: {str(e)}")
            
        return False
    
    async def _monitor_positions(self):
        """监控仓位状态"""
        while self.state.value == "ACTIVE":
            try:
                if not self.active_positions:
                    await asyncio.sleep(5)
                    continue
                
                # 获取当前价格
                positions_to_close = []
                
                for position_id, position in list(self.active_positions.items()):
                    try:
                        # 获取最新价格
                        ticker = await self.exchange_client.fetch_ticker(position.symbol)
                        current_price = ticker['last']
                        position.update_price(current_price)
                        
                        # 检查平仓条件
                        should_close, reason = self._should_close_position(position)
                        
                        if should_close:
                            positions_to_close.append((position, reason))
                        
                    except Exception as e:
                        self.logger.exception(f"监控仓位 {position_id} 异常: {str(e)}")
                
                # 执行平仓
                for position, reason in positions_to_close:
                    await self._close_position(position, reason)
                
                await asyncio.sleep(2)  # 每2秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"仓位监控循环异常: {str(e)}")
                await asyncio.sleep(10)
    
    def _should_close_position(self, position: Position) -> tuple[bool, str]:
        """判断是否应该平仓"""
        # 检查止盈
        if position.check_take_profit():
            return True, f"达到止盈目标: {position.calculate_pnl_percentage():.2f}%"
        
        # 检查止损
        if position.check_stop_loss():
            return True, f"触发止损: {position.calculate_pnl_percentage():.2f}%"
        
        # 检查超时
        timeout_hours = self.strategy_params['position_timeout_hours']
        if datetime.utcnow() - position.created_at > timedelta(hours=timeout_hours):
            return True, f"仓位超时: {timeout_hours}小时"
        
        return False, ""
    
    async def _close_position(self, position: Position, reason: str):
        """平仓操作"""
        try:
            # 执行平仓订单
            close_side = 'sell' if position.side == PositionSide.LONG else 'buy'
            
            order_result = await self.exchange_client.create_order(
                symbol=position.symbol,
                order_type='market',
                side=close_side,
                amount=position.size,
                params={'posSide': position.side.value.lower()}
            )
            
            if order_result:
                # 更新仓位状态
                close_price = order_result.get('price', position.current_price)
                self.position_manager.close_position(position.id, close_price, {
                    'close_reason': reason,
                    'order_result': order_result
                })
                
                # 计算盈亏
                final_pnl = position.calculate_pnl()
                pnl_percentage = position.calculate_pnl_percentage()
                
                # 更新策略性能
                self.update_performance({
                    'success': final_pnl > 0,
                    'pnl': final_pnl,
                    'pnl_percentage': pnl_percentage,
                    'duration': (datetime.utcnow() - position.created_at).total_seconds()
                })
                
                # 从活跃仓位中移除
                if position.id in self.active_positions:
                    del self.active_positions[position.id]
                
                self.logger.info(
                    f"平仓完成: {position.symbol} 盈亏:{final_pnl:.2f} ({pnl_percentage:.2f}%) 原因:{reason}",
                    trade_data={
                        'position_id': position.id,
                        'close_price': close_price,
                        'pnl': final_pnl,
                        'pnl_percentage': pnl_percentage,
                        'close_reason': reason
                    }
                )
            
        except Exception as e:
            self.logger.exception(f"平仓操作失败: {position.id}")
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        active_count = len(self.active_positions)
        total_unrealized_pnl = sum(pos.calculate_pnl() for pos in self.active_positions.values())
        
        return {
            **self.get_status(),
            'strategy_specific': {
                'active_positions': active_count,
                'max_concurrent': self.strategy_params['max_concurrent_positions'],
                'total_unrealized_pnl': total_unrealized_pnl,
                'profit_target': f"{self.strategy_params['profit_target']:.1%}",
                'stop_loss': f"{self.strategy_params['stop_loss']:.1%}",
                'position_timeout_hours': self.strategy_params['position_timeout_hours'],
                'positions': [pos.to_dict() for pos in self.active_positions.values()]
            }
        }