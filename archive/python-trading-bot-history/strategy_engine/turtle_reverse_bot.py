"""
海龟滚仓反向机器人 - 复杂而精妙的反向跟单策略

设计哲学：
"复杂源于智慧，滚仓源于坚持。
分层止盈是对贪婪的控制，仓位递减是对风险的敬畏。"
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass

from core.logger import get_logger
from core.exceptions import StrategyException
from .base_strategy import BaseStrategy, StrategyDecision, SignalDecision
from .position_manager import PositionManager, Position, PositionSide
from signal_processor.signal_parser import ParsedSignal, SignalAction
from signal_processor.signal_validator import ValidationResult


@dataclass
class TurtleSequence:
    """海龟序列记录"""
    sequence_id: str
    start_time: datetime
    positions: List[Position]
    current_quantity: int
    total_size: float
    direction: str  # "long" or "short"
    is_active: bool = True


class TurtleReverseBot(BaseStrategy):
    """
    海龟滚仓反向机器人 - 追求收益最大化的智慧策略
    
    核心理念：
    1. 完全反向：始终与信号方向相反
    2. 滚仓加码：随着信号数量递增而加仓
    3. 分层止盈：不同阶段采用不同的止盈策略
    4. 风险递减：后期仓位逐渐减小，控制风险
    """
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        
        # 海龟策略参数
        self.turtle_params = {
            # 各数量级的仓位大小
            'position_sizes': {
                1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60, 7: 70, 8: 80
            },
            # 止盈阈值
            'profit_thresholds': {
                1: 0.0, 2: 0.0, 3: 0.50, 4: 0.30, 5: 0.30, 6: 0.30, 7: 0.30, 8: 0.30
            },
            # 平仓比例
            'close_ratios': {
                1: 0.0, 2: 0.0, 3: 0.50, 4: 0.80, 5: 0.90, 6: 0.90, 7: 0.90, 8: 0.90
            },
            # 序列超时时间（小时）
            'sequence_timeout_hours': 8,
            # 强制止损
            'emergency_stop_loss': -0.20,  # 20%强制止损
            **self.params
        }
        
        # 获取外部组件
        self.exchange_client = config.get('exchange_client')
        self.position_manager = config.get('position_manager') or PositionManager()
        
        # 活跃序列跟踪
        self.active_sequences: Dict[str, TurtleSequence] = {}
        
        # 最近信号记录（用于判断序列连续性）
        self.recent_signals: List[ParsedSignal] = []
        self.max_signal_history = 20
        
        # 监控任务
        self.monitor_task: Optional[asyncio.Task] = None
        
        self.logger.info("海龟滚仓反向机器人已创建")
    
    def _initialize(self) -> bool:
        """初始化策略"""
        try:
            if not self.exchange_client:
                raise StrategyException("缺少交易所客户端")
            
            # 启动序列监控
            self.monitor_task = asyncio.create_task(self._monitor_sequences())
            
            self.logger.info("海龟滚仓反向机器人初始化成功")
            return True
            
        except Exception as e:
            self.logger.exception(f"海龟机器人初始化失败: {str(e)}")
            return False
    
    def _cleanup(self):
        """清理资源"""
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
    
    async def _make_decision(self, signal: ParsedSignal, validation_result: ValidationResult) -> StrategyDecision:
        """制定交易决策"""
        try:
            # 只处理开仓信号
            if signal.action not in [SignalAction.OPEN_LONG, SignalAction.OPEN_SHORT]:
                # 检查是否是平仓信号，如果是则执行让出控制权
                if signal.action in [SignalAction.CLOSE_LONG, SignalAction.CLOSE_SHORT]:
                    await self._handle_control_handover(signal)
                
                return StrategyDecision(
                    decision=SignalDecision.IGNORE,
                    reasoning="海龟策略只响应开仓信号"
                )
            
            # 更新信号历史
            self._update_signal_history(signal)
            
            # 判断信号序列
            sequence_info = self._analyze_signal_sequence(signal)
            
            # 制定反向开仓决策
            reverse_action = self._get_reverse_action(signal.action)
            position_size = self._calculate_turtle_position_size(signal, sequence_info)
            
            if position_size <= 0:
                return StrategyDecision(
                    decision=SignalDecision.IGNORE,
                    reasoning="计算的仓位大小为0"
                )
            
            # 风险检查
            if not self._check_turtle_risk_limits(reverse_action, position_size, sequence_info):
                return StrategyDecision(
                    decision=SignalDecision.IGNORE,
                    reasoning="海龟风险限制检查未通过"
                )
            
            return StrategyDecision(
                decision=SignalDecision.EXECUTE,
                action=reverse_action,
                quantity=position_size,
                symbol=signal.symbol,
                confidence=validation_result.confidence_score,
                reasoning=f"海龟反向滚仓: 信号{signal.action.value}数量{signal.quantity}，我们{reverse_action}",
                metadata={
                    'strategy_type': 'turtle_reverse',
                    'signal_quantity': signal.quantity,
                    'sequence_info': sequence_info,
                    'original_signal': signal.to_dict(),
                    'is_new_sequence': sequence_info.get('is_new_sequence', False),
                    'expected_profit_threshold': self.turtle_params['profit_thresholds'].get(int(signal.quantity), 0.30)
                }
            )
            
        except Exception as e:
            self.logger.exception(f"海龟策略决策异常: {str(e)}")
            return StrategyDecision(
                decision=SignalDecision.IGNORE,
                reasoning=f"决策异常: {str(e)}"
            )
    
    def _update_signal_history(self, signal: ParsedSignal):
        """更新信号历史"""
        self.recent_signals.append(signal)
        
        # 限制历史记录大小
        if len(self.recent_signals) > self.max_signal_history:
            self.recent_signals = self.recent_signals[-self.max_signal_history:]
    
    def _analyze_signal_sequence(self, signal: ParsedSignal) -> Dict[str, Any]:
        """分析信号序列"""
        # 获取最近的同方向信号
        current_direction = "long" if signal.action == SignalAction.OPEN_LONG else "short"
        
        # 查找最近2小时内的同方向信号
        recent_threshold = datetime.utcnow() - timedelta(hours=2)
        recent_same_direction = [
            s for s in self.recent_signals
            if (s.timestamp >= recent_threshold and
                ((s.action == SignalAction.OPEN_LONG and current_direction == "long") or
                 (s.action == SignalAction.OPEN_SHORT and current_direction == "short")))
        ]
        
        # 判断是否是新序列
        is_new_sequence = True
        sequence_id = None
        
        # 查找活跃序列
        for seq_id, sequence in self.active_sequences.items():
            if (sequence.is_active and 
                sequence.direction == current_direction and
                (datetime.utcnow() - sequence.start_time).total_seconds() < 7200):  # 2小时内
                
                is_new_sequence = False
                sequence_id = seq_id
                break
        
        # 如果是新序列，生成新的序列ID
        if is_new_sequence:
            sequence_id = f"turtle_{current_direction}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            'sequence_id': sequence_id,
            'is_new_sequence': is_new_sequence,
            'direction': current_direction,
            'recent_signals_count': len(recent_same_direction),
            'signal_quantity': signal.quantity
        }
    
    def _get_reverse_action(self, original_action: SignalAction) -> str:
        """获取反向动作"""
        reverse_mapping = {
            SignalAction.OPEN_LONG: "开空",   # 信号开多，我们开空
            SignalAction.OPEN_SHORT: "开多",  # 信号开空，我们开多
        }
        return reverse_mapping.get(original_action, "")
    
    def _calculate_turtle_position_size(self, signal: ParsedSignal, sequence_info: Dict[str, Any]) -> float:
        """计算海龟仓位大小"""
        signal_quantity = int(signal.quantity)
        
        # 获取基础仓位大小
        base_size = self.turtle_params['position_sizes'].get(signal_quantity, signal_quantity * 10)
        
        # 如果是序列中的后续信号，需要考虑已有仓位
        if not sequence_info['is_new_sequence']:
            sequence_id = sequence_info['sequence_id']
            if sequence_id in self.active_sequences:
                sequence = self.active_sequences[sequence_id]
                
                # 检查是否已经有这个数量级的仓位
                existing_quantities = [pos.metadata.get('signal_quantity', 0) for pos in sequence.positions]
                if signal_quantity in existing_quantities:
                    self.logger.warning(f"序列 {sequence_id} 中已存在数量 {signal_quantity} 的仓位")
                    return 0
        
        # 应用信号置信度调整
        confidence_factor = max(0.7, signal.confidence)  # 海龟策略最低70%置信度
        adjusted_size = base_size * confidence_factor
        
        # 应用风险限制
        max_size = self.params.get('max_position_size', 1000)
        adjusted_size = min(adjusted_size, max_size)
        
        return round(adjusted_size, 1)
    
    def _check_turtle_risk_limits(self, action: str, size: float, sequence_info: Dict[str, Any]) -> bool:
        """检查海龟策略特定的风险限制"""
        # 检查序列总仓位
        if not sequence_info['is_new_sequence']:
            sequence_id = sequence_info['sequence_id']
            if sequence_id in self.active_sequences:
                sequence = self.active_sequences[sequence_id]
                total_size = sequence.total_size + size
                
                # 限制单个序列的最大仓位
                max_sequence_size = self.params.get('max_position_size', 1000) * 0.8
                if total_size > max_sequence_size:
                    self.logger.warning(f"序列总仓位超限: {total_size} > {max_sequence_size}")
                    return False
        
        # 检查活跃序列数量
        active_count = len([seq for seq in self.active_sequences.values() if seq.is_active])
        if active_count >= 3 and sequence_info['is_new_sequence']:  # 最多3个活跃序列
            self.logger.warning(f"活跃序列数量超限: {active_count}")
            return False
        
        return True
    
    async def execute_decision(self, decision: StrategyDecision) -> bool:
        """执行海龟策略决策"""
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
                    metadata={
                        **decision.metadata,
                        'signal_quantity': decision.metadata.get('signal_quantity'),
                        'entry_order': order_result
                    }
                )
                
                # 管理序列
                await self._manage_turtle_sequence(position, decision.metadata)
                
                self.logger.info(
                    f"海龟反向开仓: {decision.action} {decision.quantity} {decision.symbol}",
                    trade_data={
                        'position_id': position.id,
                        'sequence_id': decision.metadata.get('sequence_info', {}).get('sequence_id'),
                        'signal_quantity': decision.metadata.get('signal_quantity'),
                        'entry_price': position.entry_price,
                        'order_result': order_result
                    }
                )
                
                return True
            
        except Exception as e:
            self.logger.exception(f"执行海龟决策失败: {str(e)}")
            
        return False
    
    async def _manage_turtle_sequence(self, position: Position, metadata: Dict[str, Any]):
        """管理海龟序列"""
        sequence_info = metadata.get('sequence_info', {})
        sequence_id = sequence_info.get('sequence_id')
        
        if not sequence_id:
            return
        
        # 创建或更新序列
        if sequence_id not in self.active_sequences:
            # 创建新序列
            self.active_sequences[sequence_id] = TurtleSequence(
                sequence_id=sequence_id,
                start_time=datetime.utcnow(),
                positions=[position],
                current_quantity=metadata.get('signal_quantity', 1),
                total_size=position.size,
                direction=sequence_info.get('direction', 'long')
            )
        else:
            # 更新现有序列
            sequence = self.active_sequences[sequence_id]
            sequence.positions.append(position)
            sequence.current_quantity = max(sequence.current_quantity, metadata.get('signal_quantity', 1))
            sequence.total_size += position.size
        
        # 检查是否需要分层止盈
        await self._check_partial_profit_taking(sequence_id)
    
    async def _check_partial_profit_taking(self, sequence_id: str):
        """检查分层止盈"""
        if sequence_id not in self.active_sequences:
            return
        
        sequence = self.active_sequences[sequence_id]
        current_quantity = sequence.current_quantity
        
        # 获取止盈阈值和平仓比例
        profit_threshold = self.turtle_params['profit_thresholds'].get(current_quantity, 0.30)
        close_ratio = self.turtle_params['close_ratios'].get(current_quantity, 0.0)
        
        if profit_threshold <= 0 or close_ratio <= 0:
            return  # 无需止盈
        
        # 计算序列总盈亏
        total_pnl = 0
        total_invested = 0
        
        for position in sequence.positions:
            if position.status.value == "OPEN":
                # 获取最新价格
                try:
                    ticker = await self.exchange_client.fetch_ticker(position.symbol)
                    position.update_price(ticker['last'])
                    
                    total_pnl += position.calculate_pnl()
                    total_invested += position.entry_price * position.size
                except Exception as e:
                    self.logger.exception(f"获取价格失败: {position.symbol}")
                    continue
        
        if total_invested <= 0:
            return
        
        # 计算盈利百分比
        profit_percentage = total_pnl / total_invested
        
        if profit_percentage >= profit_threshold:
            await self._execute_partial_profit_taking(sequence_id, close_ratio, profit_percentage)
    
    async def _execute_partial_profit_taking(self, sequence_id: str, close_ratio: float, profit_percentage: float):
        """执行分层止盈"""
        sequence = self.active_sequences[sequence_id]
        
        # 计算需要平仓的总量
        total_open_size = sum(pos.size for pos in sequence.positions if pos.status.value == "OPEN")
        close_size = total_open_size * close_ratio
        
        self.logger.info(
            f"执行分层止盈: 序列{sequence_id} 盈利{profit_percentage:.2%} 平仓{close_ratio:.0%}",
            trade_data={
                'sequence_id': sequence_id,
                'profit_percentage': profit_percentage,
                'close_ratio': close_ratio,
                'close_size': close_size
            }
        )
        
        # 按比例平仓所有开仓仓位
        remaining_close_size = close_size
        
        for position in sequence.positions:
            if position.status.value == "OPEN" and remaining_close_size > 0:
                position_close_size = min(position.size * close_ratio, remaining_close_size)
                
                if position_close_size > 0:
                    await self._partial_close_position(position, position_close_size, "分层止盈")
                    remaining_close_size -= position_close_size
    
    async def _partial_close_position(self, position: Position, close_size: float, reason: str):
        """部分平仓"""
        try:
            close_side = 'sell' if position.side == PositionSide.LONG else 'buy'
            
            order_result = await self.exchange_client.create_order(
                symbol=position.symbol,
                order_type='market',
                side=close_side,
                amount=close_size,
                params={'posSide': position.side.value.lower()}
            )
            
            if order_result:
                # 更新仓位
                close_price = order_result.get('price', position.current_price)
                self.position_manager.reduce_position(position.id, close_size, close_price, {
                    'close_reason': reason,
                    'order_result': order_result
                })
                
                self.logger.info(
                    f"部分平仓: {position.symbol} -{close_size} 原因:{reason}",
                    trade_data={
                        'position_id': position.id,
                        'close_size': close_size,
                        'close_price': close_price,
                        'remaining_size': position.size - close_size
                    }
                )
            
        except Exception as e:
            self.logger.exception(f"部分平仓失败: {position.id}")
    
    async def _handle_control_handover(self, signal: ParsedSignal):
        """处理让出控制权（正向平仓信号）"""
        self.logger.warning(f"检测到正向平仓信号，准备让出控制权: {signal.raw_message}")
        
        # 平掉所有活跃仓位
        for sequence in self.active_sequences.values():
            if sequence.is_active:
                await self._close_sequence(sequence.sequence_id, "让出控制权")
    
    async def _close_sequence(self, sequence_id: str, reason: str):
        """关闭整个序列"""
        if sequence_id not in self.active_sequences:
            return
        
        sequence = self.active_sequences[sequence_id]
        
        for position in sequence.positions:
            if position.status.value == "OPEN":
                await self._close_position_completely(position, reason)
        
        sequence.is_active = False
        
        self.logger.info(f"序列已关闭: {sequence_id} 原因:{reason}")
    
    async def _close_position_completely(self, position: Position, reason: str):
        """完全平仓"""
        try:
            close_side = 'sell' if position.side == PositionSide.LONG else 'buy'
            
            order_result = await self.exchange_client.create_order(
                symbol=position.symbol,
                order_type='market',
                side=close_side,
                amount=position.size,
                params={'posSide': position.side.value.lower()}
            )
            
            if order_result:
                close_price = order_result.get('price', position.current_price)
                self.position_manager.close_position(position.id, close_price, {
                    'close_reason': reason,
                    'order_result': order_result
                })
                
                # 更新策略性能
                final_pnl = position.calculate_pnl()
                self.update_performance({
                    'success': final_pnl > 0,
                    'pnl': final_pnl,
                    'pnl_percentage': position.calculate_pnl_percentage(),
                    'duration': (datetime.utcnow() - position.created_at).total_seconds()
                })
                
                self.logger.info(
                    f"完全平仓: {position.symbol} 盈亏:{final_pnl:.2f} 原因:{reason}",
                    trade_data={
                        'position_id': position.id,
                        'close_price': close_price,
                        'pnl': final_pnl,
                        'close_reason': reason
                    }
                )
            
        except Exception as e:
            self.logger.exception(f"完全平仓失败: {position.id}")
    
    async def _monitor_sequences(self):
        """监控海龟序列"""
        while self.state.value == "ACTIVE":
            try:
                if not self.active_sequences:
                    await asyncio.sleep(10)
                    continue
                
                current_time = datetime.utcnow()
                sequences_to_close = []
                
                for sequence_id, sequence in self.active_sequences.items():
                    if not sequence.is_active:
                        continue
                    
                    # 检查超时
                    if (current_time - sequence.start_time).total_seconds() > self.turtle_params['sequence_timeout_hours'] * 3600:
                        sequences_to_close.append((sequence_id, "序列超时"))
                        continue
                    
                    # 检查止盈条件
                    await self._check_partial_profit_taking(sequence_id)
                    
                    # 检查紧急止损
                    await self._check_emergency_stop_loss(sequence_id)
                
                # 关闭需要关闭的序列
                for sequence_id, reason in sequences_to_close:
                    await self._close_sequence(sequence_id, reason)
                
                await asyncio.sleep(5)  # 每5秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"序列监控异常: {str(e)}")
                await asyncio.sleep(30)
    
    async def _check_emergency_stop_loss(self, sequence_id: str):
        """检查紧急止损"""
        sequence = self.active_sequences[sequence_id]
        
        # 计算序列总亏损
        total_loss = 0
        total_invested = 0
        
        for position in sequence.positions:
            if position.status.value == "OPEN":
                try:
                    ticker = await self.exchange_client.fetch_ticker(position.symbol)
                    position.update_price(ticker['last'])
                    
                    pnl = position.calculate_pnl()
                    total_loss += pnl
                    total_invested += position.entry_price * position.size
                except:
                    continue
        
        if total_invested > 0:
            loss_percentage = total_loss / total_invested
            
            if loss_percentage <= self.turtle_params['emergency_stop_loss']:
                self.logger.warning(f"触发紧急止损: 序列{sequence_id} 亏损{loss_percentage:.2%}")
                await self._close_sequence(sequence_id, "紧急止损")
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """获取海龟策略状态"""
        active_sequences_count = len([seq for seq in self.active_sequences.values() if seq.is_active])
        total_positions = sum(len(seq.positions) for seq in self.active_sequences.values())
        total_unrealized_pnl = 0
        
        for sequence in self.active_sequences.values():
            if sequence.is_active:
                for position in sequence.positions:
                    if position.status.value == "OPEN":
                        total_unrealized_pnl += position.calculate_pnl()
        
        return {
            **self.get_status(),
            'strategy_specific': {
                'active_sequences': active_sequences_count,
                'total_positions': total_positions,
                'total_unrealized_pnl': total_unrealized_pnl,
                'turtle_params': self.turtle_params,
                'sequences': {
                    seq_id: {
                        'sequence_id': seq.sequence_id,
                        'start_time': seq.start_time.isoformat(),
                        'direction': seq.direction,
                        'current_quantity': seq.current_quantity,
                        'total_size': seq.total_size,
                        'positions_count': len(seq.positions),
                        'is_active': seq.is_active
                    }
                    for seq_id, seq in self.active_sequences.items()
                }
            }
        }