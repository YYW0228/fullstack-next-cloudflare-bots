"""
策略基类 - 智慧的抽象

设计哲学：
"所有策略的本质都是对不确定性的回应。
好的策略不是预测未来，而是在任何情况下都能生存并盈利。"
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from core.logger import get_logger
from core.exceptions import StrategyException
from signal_processor.signal_parser import ParsedSignal
from signal_processor.signal_validator import ValidationResult


class StrategyState(Enum):
    """策略状态"""
    INACTIVE = "INACTIVE"       # 未激活
    ACTIVE = "ACTIVE"           # 激活中
    PAUSED = "PAUSED"           # 暂停
    ERROR = "ERROR"             # 错误状态
    STOPPED = "STOPPED"         # 已停止


class SignalDecision(Enum):
    """信号决策"""
    IGNORE = "IGNORE"           # 忽略信号
    EXECUTE = "EXECUTE"         # 执行信号
    DELAY = "DELAY"             # 延迟执行
    MODIFY = "MODIFY"           # 修改后执行


@dataclass
class StrategyDecision:
    """策略决策结果"""
    decision: SignalDecision
    action: Optional[str] = None           # 交易动作
    quantity: float = 0.0                  # 交易数量
    symbol: str = ""                       # 交易对
    confidence: float = 0.0                # 决策置信度
    reasoning: str = ""                    # 决策理由
    metadata: Dict[str, Any] = field(default_factory=dict)
    delay_seconds: int = 0                 # 延迟秒数（如果是DELAY决策）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'decision': self.decision.value,
            'action': self.action,
            'quantity': self.quantity,
            'symbol': self.symbol,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'metadata': self.metadata,
            'delay_seconds': self.delay_seconds
        }


@dataclass
class StrategyMetrics:
    """策略性能指标"""
    total_signals: int = 0
    executed_signals: int = 0
    ignored_signals: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    avg_trade_duration: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    last_update: Optional[datetime] = None


class BaseStrategy(ABC):
    """
    策略基类 - 所有策略的智慧基础
    
    设计原则：
    1. 策略独立：每个策略都是独立的决策单元
    2. 状态管理：清晰的状态转换和管理
    3. 风险优先：所有决策都要考虑风险
    4. 可监控：提供详细的性能指标和状态信息
    """
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.logger = get_logger(f"Strategy_{name}")
        
        # 策略状态
        self.state = StrategyState.INACTIVE
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        
        # 性能指标
        self.metrics = StrategyMetrics()
        
        # 决策历史
        self.decision_history: List[StrategyDecision] = []
        self.max_history_size = 1000
        
        # 策略参数（子类可以覆盖）
        self.default_params = {
            'max_position_size': 1000.0,
            'risk_limit': 0.1,
            'confidence_threshold': 0.5,
            'max_daily_trades': 50
        }
        
        # 合并配置参数
        self.params = {**self.default_params, **self.config}
        
        self.logger.info(f"策略已创建: {self.name}")
    
    def start(self) -> bool:
        """
        启动策略
        
        Returns:
            是否启动成功
        """
        try:
            if self.state != StrategyState.INACTIVE:
                self.logger.warning(f"策略 {self.name} 当前状态不允许启动: {self.state}")
                return False
            
            # 初始化策略
            if not self._initialize():
                self.logger.error(f"策略 {self.name} 初始化失败")
                self.state = StrategyState.ERROR
                return False
            
            self.state = StrategyState.ACTIVE
            self.started_at = datetime.utcnow()
            
            self.logger.info(f"策略 {self.name} 已启动")
            return True
            
        except Exception as e:
            self.logger.exception(f"策略 {self.name} 启动异常")
            self.state = StrategyState.ERROR
            return False
    
    def stop(self) -> bool:
        """
        停止策略
        
        Returns:
            是否停止成功
        """
        try:
            if self.state == StrategyState.STOPPED:
                return True
            
            # 清理资源
            self._cleanup()
            
            self.state = StrategyState.STOPPED
            self.stopped_at = datetime.utcnow()
            
            self.logger.info(f"策略 {self.name} 已停止")
            return True
            
        except Exception as e:
            self.logger.exception(f"策略 {self.name} 停止异常")
            return False
    
    def pause(self) -> bool:
        """暂停策略"""
        if self.state == StrategyState.ACTIVE:
            self.state = StrategyState.PAUSED
            self.logger.info(f"策略 {self.name} 已暂停")
            return True
        return False
    
    def resume(self) -> bool:
        """恢复策略"""
        if self.state == StrategyState.PAUSED:
            self.state = StrategyState.ACTIVE
            self.logger.info(f"策略 {self.name} 已恢复")
            return True
        return False
    
    def reset(self) -> bool:
        """重置策略"""
        try:
            self.stop()
            
            # 重置状态和指标
            self.state = StrategyState.INACTIVE
            self.metrics = StrategyMetrics()
            self.decision_history.clear()
            self.started_at = None
            self.stopped_at = None
            
            self.logger.info(f"策略 {self.name} 已重置")
            return True
            
        except Exception as e:
            self.logger.exception(f"策略 {self.name} 重置异常")
            return False
    
    async def process_signal(self, signal: ParsedSignal, validation_result: ValidationResult) -> StrategyDecision:
        """
        处理信号 - 策略的核心决策方法
        
        Args:
            signal: 解析后的信号
            validation_result: 验证结果
            
        Returns:
            策略决策
        """
        # 检查策略状态
        if self.state != StrategyState.ACTIVE:
            return StrategyDecision(
                decision=SignalDecision.IGNORE,
                reasoning=f"策略未激活 (状态: {self.state.value})"
            )
        
        # 更新指标
        self.metrics.total_signals += 1
        
        try:
            # 调用子类实现的决策逻辑
            decision = await self._make_decision(signal, validation_result)
            
            # 记录决策
            self._record_decision(decision, signal)
            
            # 更新指标
            if decision.decision == SignalDecision.EXECUTE:
                self.metrics.executed_signals += 1
            else:
                self.metrics.ignored_signals += 1
            
            return decision
            
        except Exception as e:
            self.logger.exception(f"策略 {self.name} 处理信号异常")
            
            return StrategyDecision(
                decision=SignalDecision.IGNORE,
                reasoning=f"处理异常: {str(e)}"
            )
    
    def update_performance(self, trade_result: Dict[str, Any]):
        """
        更新策略性能
        
        Args:
            trade_result: 交易结果
        """
        try:
            if trade_result.get('success', False):
                self.metrics.successful_trades += 1
                pnl = trade_result.get('pnl', 0.0)
                self.metrics.total_pnl += pnl
            else:
                self.metrics.failed_trades += 1
            
            # 计算胜率
            total_trades = self.metrics.successful_trades + self.metrics.failed_trades
            if total_trades > 0:
                self.metrics.win_rate = self.metrics.successful_trades / total_trades
            
            # 更新时间
            self.metrics.last_update = datetime.utcnow()
            
            # 记录性能更新
            self.logger.info(
                f"策略 {self.name} 性能更新",
                strategy_data={
                    'trade_result': trade_result,
                    'current_metrics': self._get_metrics_dict()
                }
            )
            
        except Exception as e:
            self.logger.exception(f"策略 {self.name} 性能更新异常")
    
    def get_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        uptime = None
        if self.started_at:
            if self.stopped_at:
                uptime = (self.stopped_at - self.started_at).total_seconds()
            else:
                uptime = (datetime.utcnow() - self.started_at).total_seconds()
        
        return {
            'name': self.name,
            'state': self.state.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'stopped_at': self.stopped_at.isoformat() if self.stopped_at else None,
            'uptime_seconds': uptime,
            'metrics': self._get_metrics_dict(),
            'config': self.config,
            'params': self.params
        }
    
    def _get_metrics_dict(self) -> Dict[str, Any]:
        """获取指标字典"""
        return {
            'total_signals': self.metrics.total_signals,
            'executed_signals': self.metrics.executed_signals,
            'ignored_signals': self.metrics.ignored_signals,
            'successful_trades': self.metrics.successful_trades,
            'failed_trades': self.metrics.failed_trades,
            'total_pnl': self.metrics.total_pnl,
            'win_rate': f"{self.metrics.win_rate:.2%}",
            'avg_trade_duration': self.metrics.avg_trade_duration,
            'max_drawdown': self.metrics.max_drawdown,
            'sharpe_ratio': self.metrics.sharpe_ratio,
            'last_update': self.metrics.last_update.isoformat() if self.metrics.last_update else None
        }
    
    def _record_decision(self, decision: StrategyDecision, signal: ParsedSignal):
        """记录决策历史"""
        self.decision_history.append(decision)
        
        # 限制历史记录大小
        if len(self.decision_history) > self.max_history_size:
            self.decision_history = self.decision_history[-self.max_history_size:]
        
        # 记录决策日志
        self.logger.decision(
            decision=f"{decision.decision.value}: {decision.action} {decision.quantity}",
            reasoning=decision.reasoning,
            data={
                'signal': signal.to_dict(),
                'decision': decision.to_dict()
            }
        )
    
    def get_recent_decisions(self, count: int = 10) -> List[StrategyDecision]:
        """获取最近的决策"""
        return self.decision_history[-count:]
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        self.config.update(new_config)
        self.params.update(new_config)
        self.logger.info(f"策略 {self.name} 配置已更新")
    
    # 抽象方法 - 子类必须实现
    
    @abstractmethod
    async def _make_decision(self, signal: ParsedSignal, validation_result: ValidationResult) -> StrategyDecision:
        """
        制定决策 - 子类必须实现的核心逻辑
        
        Args:
            signal: 信号
            validation_result: 验证结果
            
        Returns:
            策略决策
        """
        pass
    
    @abstractmethod
    def _initialize(self) -> bool:
        """
        初始化策略 - 子类可以覆盖
        
        Returns:
            是否初始化成功
        """
        return True
    
    def _cleanup(self):
        """
        清理资源 - 子类可以覆盖
        """
        pass
    
    # 工具方法
    
    def _validate_params(self) -> bool:
        """验证策略参数"""
        required_params = ['max_position_size', 'risk_limit', 'confidence_threshold']
        
        for param in required_params:
            if param not in self.params:
                self.logger.error(f"缺少必要参数: {param}")
                return False
        
        return True
    
    def _check_risk_limits(self, proposed_action: str, quantity: float) -> bool:
        """检查风险限制"""
        # 检查仓位大小
        if quantity > self.params['max_position_size']:
            self.logger.warning(f"仓位超限: {quantity} > {self.params['max_position_size']}")
            return False
        
        # 检查日交易次数
        today_trades = len([d for d in self.decision_history 
                           if d.decision == SignalDecision.EXECUTE and 
                           (datetime.utcnow() - self.created_at).days == 0])
        
        if today_trades >= self.params['max_daily_trades']:
            self.logger.warning(f"日交易次数超限: {today_trades} >= {self.params['max_daily_trades']}")
            return False
        
        return True
    
    def _calculate_position_size(self, signal: ParsedSignal, base_quantity: float) -> float:
        """计算仓位大小"""
        # 基础仓位调整
        adjusted_quantity = base_quantity
        
        # 根据信号置信度调整
        confidence_factor = signal.confidence
        adjusted_quantity *= confidence_factor
        
        # 应用风险限制
        max_size = self.params['max_position_size']
        adjusted_quantity = min(adjusted_quantity, max_size)
        
        return adjusted_quantity