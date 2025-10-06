"""
海龟反向策略 - 滚仓分层止盈的智慧

设计哲学：
"复杂源于智慧，滚仓源于坚持。
分层止盈是对贪婪的控制，仓位递减是对风险的敬畏。"
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid

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
class TurtlePosition:
    """海龟仓位记录"""
    id: str
    symbol: str
    side: str                    # "开多" or "开空"
    size: float
    entry_price: float
    current_price: float = 0.0
    signal_quantity: int = 1     # 对应的信号数量
    sequence_id: str = ""        # 所属序列ID
    created_at: datetime = None
    order_id: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}
    
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


@dataclass
class TurtleSequence:
    """海龟交易序列"""
    id: str
    direction: str               # "long" or "short" (我们的交易方向)
    original_direction: str      # 原始信号方向
    start_time: datetime
    positions: List[TurtlePosition] = field(default_factory=list)
    current_max_quantity: int = 0
    total_size: float = 0.0
    is_active: bool = True
    last_signal_time: Optional[datetime] = None
    profit_taken_at: Dict[int, float] = field(default_factory=dict)  # 记录各数量级的止盈时间
    
    def get_total_unrealized_pnl(self) -> float:
        """获取序列总未实现盈亏"""
        return sum(pos.calculate_pnl_amount() for pos in self.positions if pos.current_price > 0)
    
    def get_total_invested(self) -> float:
        """获取总投入金额"""
        return sum(pos.entry_price * pos.size for pos in self.positions if pos.entry_price > 0)
    
    def get_pnl_percentage(self) -> float:
        """获取序列总盈亏百分比"""
        total_invested = self.get_total_invested()
        if total_invested <= 0:
            return 0.0
        return self.get_total_unrealized_pnl() / total_invested
    
    def should_partial_profit(self, quantity: int, threshold: float) -> bool:
        """判断是否应该分层止盈"""
        if quantity in self.profit_taken_at:
            return False  # 已经止盈过了
        
        return self.get_pnl_percentage() >= threshold
    
    def is_timeout(self, timeout_hours: int = 8) -> bool:
        """判断序列是否超时"""
        return datetime.utcnow() - self.start_time > timedelta(hours=timeout_hours)


class TurtleReverseStrategy:
    """
    海龟反向策略 - 追求收益最大化的智慧策略
    
    核心理念：
    1. 完全反向：始终与原信号方向相反
    2. 滚仓加码：随着信号数量递增而加仓
    3. 分层止盈：不同阶段采用不同的止盈策略
    4. 仓位递减：后期仓位逐渐减小，控制风险
    5. 快进快出：只用市价单，追求执行速度
    """
    
    def __init__(self, config, order_executor: OrderExecutor):
        self.config = config
        self.order_executor = order_executor
        self.logger = get_logger("TurtleReverseStrategy")
        
        # 从配置读取海龟参数
        strategy_config = config.get_config("strategy", {})
        
        self.params = {
            # 各数量级的仓位大小
            'position_sizes': strategy_config.get('position_sizes', {
                1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60, 7: 70, 8: 80
            }),
            # 止盈阈值
            'profit_thresholds': strategy_config.get('profit_thresholds', {
                1: 0.0, 2: 0.0, 3: 0.50, 4: 0.30, 5: 0.30, 6: 0.30, 7: 0.30, 8: 0.30
            }),
            # 平仓比例
            'close_ratios': strategy_config.get('close_ratios', {
                1: 0.0, 2: 0.0, 3: 0.50, 4: 0.80, 5: 0.90, 6: 0.90, 7: 0.90, 8: 1.00
            }),
            # 其他参数
            'sequence_timeout_hours': strategy_config.get('sequence_timeout_hours', 8),
            'emergency_stop_loss': strategy_config.get('emergency_stop_loss', -0.20),
            'max_concurrent_sequences': strategy_config.get('max_concurrent_sequences', 3),
            'min_signal_confidence': strategy_config.get('min_signal_confidence', 0.6),
            'price_update_interval': 2
        }
        
        # 活跃序列管理
        self.active_sequences: Dict[str, TurtleSequence] = {}
        
        # 信号历史（用于判断序列连续性）
        self.recent_signals: List[ParsedSignal] = []
        self.max_signal_history = 50
        
        # 策略状态
        self.is_running = False
        self.total_signals = 0
        self.executed_signals = 0
        self.total_sequences = 0
        self.successful_sequences = 0
        self.total_pnl = 0.0
        
        # 监控任务
        self.monitor_task: Optional[asyncio.Task] = None
        
        # 订单回调
        self.order_executor.add_callback(self._on_order_completed)
        
        self.logger.info("海龟反向策略已创建")
    
    def start(self) -> bool:
        """启动策略"""
        try:
            if self.is_running:
                return True
            
            self.is_running = True
            
            # 启动序列监控任务
            self.monitor_task = asyncio.create_task(self._monitor_sequences())
            
            self.logger.info("海龟反向策略已启动")
            return True
            
        except Exception as e:
            self.logger.exception(f"海龟策略启动失败: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """停止策略"""
        try:
            self.is_running = False
            
            # 取消监控任务
            if self.monitor_task and not self.monitor_task.done():
                self.monitor_task.cancel()
            
            self.logger.info("海龟反向策略已停止")
            return True
            
        except Exception as e:
            self.logger.exception(f"海龟策略停止失败: {str(e)}")
            return False
    
    async def process_signal(self, signal: ParsedSignal, validation_result: ValidationResult):
        """处理信号 - 海龟策略的核心入口"""
        try:
            self.total_signals += 1
            
            if not self.is_running:
                return
            
            # 验证信号质量
            if not self._validate_signal(signal, validation_result):
                return
            
            # 更新信号历史
            self._update_signal_history(signal)
            
            # 只处理开仓信号
            if signal.action not in [SignalAction.OPEN_LONG, SignalAction.OPEN_SHORT]:
                # 如果是平仓信号，执行让出控制权
                if signal.action in [SignalAction.CLOSE_LONG, SignalAction.CLOSE_SHORT]:
                    await self._handle_control_handover(signal)
                return
            
            # 分析序列并执行反向开仓
            await self._execute_turtle_strategy(signal, validation_result)
            
        except Exception as e:
            self.logger.exception(f"海龟策略处理信号异常: {str(e)}")
    
    def _validate_signal(self, signal: ParsedSignal, validation_result: ValidationResult) -> bool:
        """验证信号有效性"""
        if validation_result.confidence_score < self.params['min_signal_confidence']:
            return False
        if not validation_result.is_valid:
            return False
        return True
    
    async def _execute_turtle_strategy(self, signal: ParsedSignal, validation_result: ValidationResult):
        """执行海龟策略逻辑"""
        # 找到或创建序列
        sequence = await self._get_or_create_sequence(signal)
        
        # 计算仓位大小
        position_size = self._calculate_turtle_position_size(signal, sequence)
        
        if position_size <= 0:
            return
        
        # 执行反向开仓
        await self._execute_reverse_entry(signal, sequence, position_size)
        
        # 检查分层止盈
        await self._check_partial_profit(sequence, int(signal.quantity))
    
    async def _get_or_create_sequence(self, signal: ParsedSignal) -> TurtleSequence:
        """获取或创建交易序列"""
        signal_direction = "long" if signal.action == SignalAction.OPEN_LONG else "short"
        reverse_direction = "short" if signal_direction == "long" else "long"
        
        # 查找现有序列
        for sequence in self.active_sequences.values():
            if (sequence.is_active and 
                sequence.original_direction == signal_direction and
                not sequence.is_timeout(self.params['sequence_timeout_hours'])):
                return sequence
        
        # 创建新序列
        sequence_id = f"turtle_{reverse_direction}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        sequence = TurtleSequence(
            id=sequence_id,
            direction=reverse_direction,
            original_direction=signal_direction,
            start_time=datetime.utcnow()
        )
        
        self.active_sequences[sequence_id] = sequence
        self.total_sequences += 1
        
        self.logger.info(f"创建新海龟序列: {sequence_id} 方向:{reverse_direction}")
        return sequence
    
    def _calculate_turtle_position_size(self, signal: ParsedSignal, sequence: TurtleSequence) -> float:
        """计算海龟仓位大小"""
        quantity = int(signal.quantity)
        base_size = self.params['position_sizes'].get(quantity, quantity * 10)
        
        # 检查是否已有该数量级的仓位
        existing_quantities = [pos.signal_quantity for pos in sequence.positions]
        if quantity in existing_quantities:
            self.logger.warning(f"序列中已存在数量{quantity}的仓位")
            return 0
        
        return float(base_size)
    
    async def emergency_close_all_sequences(self, reason: str = "紧急平仓"):
        """紧急平掉所有序列"""
        self.logger.warning(f"执行序列紧急平仓: {reason}")
        
        for sequence in list(self.active_sequences.values()):
            if sequence.is_active:
                await self._close_sequence_completely(sequence, f"紧急平仓({reason})")
    
    async def _close_sequence_completely(self, sequence: TurtleSequence, reason: str):
        """完全关闭序列"""
        # 简化实现，实际需要完整的平仓逻辑
        sequence.is_active = False
        self.logger.info(f"序列已关闭: {sequence.id} 原因:{reason}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        active_sequences = len([s for s in self.active_sequences.values() if s.is_active])
        
        return {
            'strategy_name': 'TurtleReverse',
            'is_running': self.is_running,
            'total_signals': self.total_signals,
            'executed_signals': self.executed_signals,
            'active_sequences': active_sequences,
            'max_sequences': self.params['max_concurrent_sequences'],
            'total_sequences': self.total_sequences,
            'params': self.params
        }
    
    def get_sequences_summary(self) -> Dict[str, Any]:
        """获取序列摘要"""
        active = [s for s in self.active_sequences.values() if s.is_active]
        return {
            'active_sequences': len(active),
            'high_risk_sequences': 0,  # 简化实现
            'total_unrealized_pnl': sum(s.get_total_unrealized_pnl() for s in active)
        }