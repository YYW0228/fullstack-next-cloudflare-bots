"""
策略选择器 - 智慧的指挥官

设计哲学：
"选择比努力更重要，协调比竞争更智慧。
让合适的策略在合适的时机发挥合适的作用。"
"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import asyncio

from core.logger import get_logger
from core.exceptions import StrategyException
from .base_strategy import BaseStrategy, StrategyDecision, SignalDecision
from signal_processor.signal_parser import ParsedSignal
from signal_processor.signal_validator import ValidationResult


class SelectionMode(Enum):
    """选择模式"""
    ALL_ACTIVE = "ALL_ACTIVE"           # 所有策略都处理
    BEST_MATCH = "BEST_MATCH"           # 选择最匹配的策略
    LOAD_BALANCE = "LOAD_BALANCE"       # 负载均衡分配
    CONDITIONAL = "CONDITIONAL"         # 条件选择


class StrategySelector:
    """
    策略选择器 - 多策略协调的智慧大脑
    
    设计原则：
    1. 智能分配：根据信号特征选择最合适的策略
    2. 负载均衡：避免单个策略过载
    3. 性能监控：跟踪各策略表现并动态调整
    4. 冲突解决：处理策略间的资源竞争
    """
    
    def __init__(self, strategies: List[BaseStrategy], mode: SelectionMode = SelectionMode.CONDITIONAL):
        self.logger = get_logger("StrategySelector")
        
        # 策略管理
        self.strategies: Dict[str, BaseStrategy] = {strategy.name: strategy for strategy in strategies}
        self.selection_mode = mode
        
        # 选择统计
        self.selection_stats = {
            'total_signals': 0,
            'strategy_selections': {name: 0 for name in self.strategies.keys()},
            'selection_reasons': {},
            'performance_scores': {name: 1.0 for name in self.strategies.keys()}
        }
        
        # 条件选择规则
        self.selection_rules = self._init_selection_rules()
        
        self.logger.info(f"策略选择器已创建，管理 {len(strategies)} 个策略，模式: {mode.value}")
    
    def _init_selection_rules(self) -> List[Callable]:
        """初始化选择规则"""
        return [
            self._rule_signal_confidence,
            self._rule_signal_quantity,
            self._rule_strategy_performance,
            self._rule_strategy_capacity,
            self._rule_signal_type
        ]
    
    async def process_signal(self, signal: ParsedSignal, validation_result: ValidationResult) -> List[StrategyDecision]:
        """
        处理信号并分配给合适的策略
        
        Args:
            signal: 解析后的信号
            validation_result: 验证结果
            
        Returns:
            策略决策列表
        """
        self.selection_stats['total_signals'] += 1
        
        try:
            # 选择策略
            selected_strategies = await self._select_strategies(signal, validation_result)
            
            if not selected_strategies:
                self.logger.warning("没有策略被选中处理信号")
                return []
            
            # 并行处理信号
            decisions = []
            tasks = []
            
            for strategy in selected_strategies:
                task = asyncio.create_task(
                    self._process_strategy_signal(strategy, signal, validation_result)
                )
                tasks.append((strategy.name, task))
            
            # 等待所有策略处理完成
            for strategy_name, task in tasks:
                try:
                    decision = await task
                    if decision:
                        decisions.append(decision)
                        
                        # 更新选择统计
                        self.selection_stats['strategy_selections'][strategy_name] += 1
                        
                except Exception as e:
                    self.logger.exception(f"策略 {strategy_name} 处理信号异常: {str(e)}")
            
            # 记录选择结果
            self._log_selection_result(signal, selected_strategies, decisions)
            
            return decisions
            
        except Exception as e:
            self.logger.exception(f"信号处理异常: {str(e)}")
            return []
    
    async def _select_strategies(self, signal: ParsedSignal, validation_result: ValidationResult) -> List[BaseStrategy]:
        """选择合适的策略"""
        if self.selection_mode == SelectionMode.ALL_ACTIVE:
            return self._select_all_active()
        
        elif self.selection_mode == SelectionMode.BEST_MATCH:
            return await self._select_best_match(signal, validation_result)
        
        elif self.selection_mode == SelectionMode.LOAD_BALANCE:
            return await self._select_load_balanced(signal, validation_result)
        
        elif self.selection_mode == SelectionMode.CONDITIONAL:
            return await self._select_conditional(signal, validation_result)
        
        else:
            return list(self.strategies.values())
    
    def _select_all_active(self) -> List[BaseStrategy]:
        """选择所有活跃策略"""
        return [strategy for strategy in self.strategies.values() 
                if strategy.state.value == "ACTIVE"]
    
    async def _select_best_match(self, signal: ParsedSignal, validation_result: ValidationResult) -> List[BaseStrategy]:
        """选择最匹配的策略"""
        scores = {}
        
        for strategy in self.strategies.values():
            if strategy.state.value != "ACTIVE":
                continue
            
            # 计算匹配分数
            score = await self._calculate_match_score(strategy, signal, validation_result)
            scores[strategy.name] = score
        
        if not scores:
            return []
        
        # 选择分数最高的策略
        best_strategy_name = max(scores, key=scores.get)
        return [self.strategies[best_strategy_name]]
    
    async def _select_load_balanced(self, signal: ParsedSignal, validation_result: ValidationResult) -> List[BaseStrategy]:
        """负载均衡选择"""
        active_strategies = self._select_all_active()
        
        if not active_strategies:
            return []
        
        # 计算每个策略的负载
        loads = {}
        for strategy in active_strategies:
            # 获取策略当前负载（可以是活跃仓位数、处理的信号数等）
            load = await self._calculate_strategy_load(strategy)
            loads[strategy.name] = load
        
        # 选择负载最低的策略
        min_load_strategy_name = min(loads, key=loads.get)
        return [self.strategies[min_load_strategy_name]]
    
    async def _select_conditional(self, signal: ParsedSignal, validation_result: ValidationResult) -> List[BaseStrategy]:
        """条件选择策略"""
        selected = []
        selection_reasons = []
        
        # 应用选择规则
        for rule in self.selection_rules:
            try:
                rule_result = rule(signal, validation_result)
                if rule_result:
                    strategy_name, reason = rule_result
                    if (strategy_name in self.strategies and 
                        self.strategies[strategy_name].state.value == "ACTIVE"):
                        
                        strategy = self.strategies[strategy_name]
                        if strategy not in selected:
                            selected.append(strategy)
                            selection_reasons.append(reason)
                            
            except Exception as e:
                self.logger.exception(f"选择规则执行异常: {rule.__name__}")
        
        # 记录选择原因
        if selection_reasons:
            reasons_key = "|".join(selection_reasons)
            self.selection_stats['selection_reasons'][reasons_key] = (
                self.selection_stats['selection_reasons'].get(reasons_key, 0) + 1
            )
        
        return selected
    
    def _rule_signal_confidence(self, signal: ParsedSignal, validation_result: ValidationResult) -> Optional[tuple]:
        """信号置信度规则"""
        confidence = validation_result.confidence_score
        
        if confidence >= 0.8:
            # 高置信度信号：海龟策略更适合
            return ("TurtleReverse", "高置信度信号")
        elif confidence >= 0.5:
            # 中等置信度：简单策略更安全
            return ("SimpleReverse", "中等置信度信号")
        
        return None
    
    def _rule_signal_quantity(self, signal: ParsedSignal, validation_result: ValidationResult) -> Optional[tuple]:
        """信号数量规则"""
        quantity = signal.quantity
        
        if quantity >= 3:
            # 数量3+：海龟策略的滚仓机会
            return ("TurtleReverse", f"信号数量{quantity}适合滚仓")
        elif quantity in [1, 2]:
            # 数量1-2：简单策略试水
            return ("SimpleReverse", f"信号数量{quantity}适合简单策略")
        
        return None
    
    def _rule_strategy_performance(self, signal: ParsedSignal, validation_result: ValidationResult) -> Optional[tuple]:
        """策略性能规则"""
        # 选择当前表现较好的策略
        best_strategy = max(self.selection_stats['performance_scores'], 
                          key=self.selection_stats['performance_scores'].get)
        
        if self.selection_stats['performance_scores'][best_strategy] > 1.2:
            return (best_strategy, "性能表现优秀")
        
        return None
    
    def _rule_strategy_capacity(self, signal: ParsedSignal, validation_result: ValidationResult) -> Optional[tuple]:
        """策略容量规则"""
        # 检查策略是否还有处理能力
        for strategy_name, strategy in self.strategies.items():
            if strategy.state.value == "ACTIVE":
                # 这里可以检查策略的活跃仓位数等
                status = strategy.get_status()
                
                # 简单策略的容量检查
                if strategy_name == "SimpleReverse":
                    active_positions = status.get('strategy_specific', {}).get('active_positions', 0)
                    max_positions = 5  # 假设最大5个并发仓位
                    
                    if active_positions < max_positions:
                        return (strategy_name, f"简单策略有容量({active_positions}/{max_positions})")
                
                # 海龟策略的容量检查
                elif strategy_name == "TurtleReverse":
                    active_sequences = status.get('strategy_specific', {}).get('active_sequences', 0)
                    max_sequences = 3  # 假设最大3个并发序列
                    
                    if active_sequences < max_sequences:
                        return (strategy_name, f"海龟策略有容量({active_sequences}/{max_sequences})")
        
        return None
    
    def _rule_signal_type(self, signal: ParsedSignal, validation_result: ValidationResult) -> Optional[tuple]:
        """信号类型规则"""
        # 根据信号的元数据特征选择策略
        strength = signal.metadata.get('strength', 'unknown')
        
        if strength == 'weak':
            return ("SimpleReverse", "弱信号适合简单策略")
        elif strength in ['medium', 'strong']:
            return ("TurtleReverse", f"{strength}信号适合海龟策略")
        
        return None
    
    async def _process_strategy_signal(self, strategy: BaseStrategy, signal: ParsedSignal, validation_result: ValidationResult) -> Optional[StrategyDecision]:
        """处理单个策略的信号"""
        try:
            decision = await strategy.process_signal(signal, validation_result)
            
            # 如果策略决定执行，则实际执行
            if decision.decision == SignalDecision.EXECUTE:
                success = await strategy.execute_decision(decision)
                if success:
                    # 更新策略性能分数
                    self._update_performance_score(strategy.name, True)
                else:
                    self._update_performance_score(strategy.name, False)
                    decision.decision = SignalDecision.IGNORE
                    decision.reasoning += " (执行失败)"
            
            return decision
            
        except Exception as e:
            self.logger.exception(f"策略 {strategy.name} 处理信号异常")
            self._update_performance_score(strategy.name, False)
            return None
    
    async def _calculate_match_score(self, strategy: BaseStrategy, signal: ParsedSignal, validation_result: ValidationResult) -> float:
        """计算策略匹配分数"""
        score = 0.0
        
        # 基础分数
        score += validation_result.confidence_score * 0.3
        
        # 策略特定分数
        if strategy.name == "SimpleReverse":
            # 简单策略偏好低风险信号
            if signal.quantity <= 3:
                score += 0.4
            if validation_result.confidence_score >= 0.5:
                score += 0.3
        
        elif strategy.name == "TurtleReverse":
            # 海龟策略偏好连续信号
            if signal.quantity >= 3:
                score += 0.5
            if validation_result.confidence_score >= 0.7:
                score += 0.3
        
        # 性能加权
        performance_factor = self.selection_stats['performance_scores'].get(strategy.name, 1.0)
        score *= performance_factor
        
        return score
    
    async def _calculate_strategy_load(self, strategy: BaseStrategy) -> float:
        """计算策略负载"""
        status = strategy.get_status()
        
        # 根据策略类型计算负载
        if strategy.name == "SimpleReverse":
            active_positions = status.get('strategy_specific', {}).get('active_positions', 0)
            return active_positions / 5.0  # 假设最大5个仓位
        
        elif strategy.name == "TurtleReverse":
            active_sequences = status.get('strategy_specific', {}).get('active_sequences', 0)
            return active_sequences / 3.0  # 假设最大3个序列
        
        return 0.0
    
    def _update_performance_score(self, strategy_name: str, success: bool):
        """更新策略性能分数"""
        current_score = self.selection_stats['performance_scores'].get(strategy_name, 1.0)
        
        if success:
            # 成功时略微增加分数
            new_score = min(2.0, current_score * 1.02)
        else:
            # 失败时降低分数
            new_score = max(0.1, current_score * 0.95)
        
        self.selection_stats['performance_scores'][strategy_name] = new_score
    
    def _log_selection_result(self, signal: ParsedSignal, selected_strategies: List[BaseStrategy], decisions: List[StrategyDecision]):
        """记录选择结果"""
        strategy_names = [s.name for s in selected_strategies]
        executed_count = len([d for d in decisions if d.decision == SignalDecision.EXECUTE])
        
        self.logger.info(
            f"策略选择: {signal.action.value} 数量{signal.quantity} → 选中{strategy_names} → 执行{executed_count}个",
            strategy_data={
                'signal': signal.to_dict(),
                'selected_strategies': strategy_names,
                'decisions': [d.to_dict() for d in decisions],
                'selection_mode': self.selection_mode.value
            }
        )
    
    def add_strategy(self, strategy: BaseStrategy):
        """添加新策略"""
        self.strategies[strategy.name] = strategy
        self.selection_stats['strategy_selections'][strategy.name] = 0
        self.selection_stats['performance_scores'][strategy.name] = 1.0
        
        self.logger.info(f"策略已添加: {strategy.name}")
    
    def remove_strategy(self, strategy_name: str):
        """移除策略"""
        if strategy_name in self.strategies:
            strategy = self.strategies[strategy_name]
            strategy.stop()
            
            del self.strategies[strategy_name]
            del self.selection_stats['strategy_selections'][strategy_name]
            del self.selection_stats['performance_scores'][strategy_name]
            
            self.logger.info(f"策略已移除: {strategy_name}")
    
    def set_selection_mode(self, mode: SelectionMode):
        """设置选择模式"""
        self.selection_mode = mode
        self.logger.info(f"选择模式已更新: {mode.value}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取选择器统计信息"""
        total_selections = sum(self.selection_stats['strategy_selections'].values())
        
        return {
            'total_signals': self.selection_stats['total_signals'],
            'total_selections': total_selections,
            'selection_mode': self.selection_mode.value,
            'strategy_count': len(self.strategies),
            'active_strategies': len([s for s in self.strategies.values() if s.state.value == "ACTIVE"]),
            'strategy_selections': self.selection_stats['strategy_selections'],
            'performance_scores': self.selection_stats['performance_scores'],
            'selection_reasons': self.selection_stats['selection_reasons'],
            'strategy_status': {
                name: strategy.get_status()
                for name, strategy in self.strategies.items()
            }
        }
    
    async def start_all_strategies(self) -> Dict[str, bool]:
        """启动所有策略"""
        results = {}
        
        for name, strategy in self.strategies.items():
            try:
                success = strategy.start()
                results[name] = success
                
                if success:
                    self.logger.info(f"策略 {name} 启动成功")
                else:
                    self.logger.error(f"策略 {name} 启动失败")
                    
            except Exception as e:
                self.logger.exception(f"启动策略 {name} 异常")
                results[name] = False
        
        return results
    
    async def stop_all_strategies(self) -> Dict[str, bool]:
        """停止所有策略"""
        results = {}
        
        for name, strategy in self.strategies.items():
            try:
                success = strategy.stop()
                results[name] = success
                
                if success:
                    self.logger.info(f"策略 {name} 停止成功")
                else:
                    self.logger.error(f"策略 {name} 停止失败")
                    
            except Exception as e:
                self.logger.exception(f"停止策略 {name} 异常")
                results[name] = False
        
        return results