"""
信号验证器 - 智慧的守门者

设计哲学：
"不是所有的声音都是信号，不是所有的信号都值得响应。
智慧在于分辨真伪，勇气在于坚持原则。"
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from core.logger import get_logger
from core.exceptions import SignalException, DataValidationException
from .signal_parser import ParsedSignal, SignalAction, SignalType


@dataclass
class ValidationRule:
    """验证规则"""
    name: str
    description: str
    enabled: bool = True
    severity: str = "ERROR"  # ERROR, WARNING, INFO


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    confidence_score: float  # 0-1
    warnings: List[str]
    errors: List[str]
    applied_rules: List[str]
    metadata: Dict[str, Any]


class SignalValidator:
    """
    信号验证器 - 确保信号质量的智慧守护者
    
    设计原则：
    1. 多层验证：从语法到语义的全面检查
    2. 智能评分：给出信号可信度评分
    3. 上下文感知：结合历史信号进行验证
    4. 可配置规则：支持动态调整验证策略
    """
    
    def __init__(self):
        self.logger = get_logger("SignalValidator")
        
        # 验证规则集
        self.validation_rules = self._init_validation_rules()
        
        # 信号历史（用于上下文验证）
        self.signal_history: List[ParsedSignal] = []
        self.max_history_size = 100
        
        # 验证统计
        self.validation_stats = {
            'total_validated': 0,
            'passed_signals': 0,
            'rejected_signals': 0,
            'warning_signals': 0,
            'rule_violations': {}
        }
    
    def _init_validation_rules(self) -> Dict[str, ValidationRule]:
        """初始化验证规则"""
        return {
            'format_check': ValidationRule(
                name="格式检查",
                description="检查信号基本格式是否正确",
                enabled=True,
                severity="ERROR"
            ),
            'quantity_range': ValidationRule(
                name="数量范围检查",
                description="检查交易数量是否在合理范围内",
                enabled=True,
                severity="WARNING"
            ),
            'symbol_validation': ValidationRule(
                name="交易对验证",
                description="验证交易对是否支持",
                enabled=True,
                severity="ERROR"
            ),
            'duplicate_check': ValidationRule(
                name="重复信号检查",
                description="检查是否为重复信号",
                enabled=True,
                severity="WARNING"
            ),
            'timing_check': ValidationRule(
                name="时间合理性检查",
                description="检查信号时间是否合理",
                enabled=True,
                severity="WARNING"
            ),
            'sequence_logic': ValidationRule(
                name="序列逻辑检查",
                description="检查信号序列是否符合交易逻辑",
                enabled=True,
                severity="WARNING"
            ),
            'market_hours': ValidationRule(
                name="市场时间检查",
                description="检查是否在交易时间内",
                enabled=False,  # 加密货币24小时交易
                severity="INFO"
            ),
            'confidence_threshold': ValidationRule(
                name="置信度阈值检查",
                description="检查信号置信度是否达到最低要求",
                enabled=True,
                severity="WARNING"
            )
        }
    
    def validate(self, signal: ParsedSignal) -> ValidationResult:
        """
        验证信号
        
        Args:
            signal: 待验证的信号
            
        Returns:
            验证结果
        """
        self.validation_stats['total_validated'] += 1
        
        result = ValidationResult(
            is_valid=True,
            confidence_score=1.0,
            warnings=[],
            errors=[],
            applied_rules=[],
            metadata={}
        )
        
        # 执行各项验证规则
        validation_methods = [
            self._validate_format,
            self._validate_quantity_range,
            self._validate_symbol,
            self._validate_duplicate,
            self._validate_timing,
            self._validate_sequence_logic,
            self._validate_confidence_threshold
        ]
        
        for method in validation_methods:
            try:
                method(signal, result)
            except Exception as e:
                self.logger.exception(f"验证规则执行异常: {method.__name__}")
                result.errors.append(f"验证异常: {str(e)}")
        
        # 计算最终结果
        self._calculate_final_result(signal, result)
        
        # 更新历史记录
        self._update_signal_history(signal)
        
        # 记录统计信息
        self._update_validation_stats(result)
        
        # 记录验证结果
        self._log_validation_result(signal, result)
        
        return result
    
    def _validate_format(self, signal: ParsedSignal, result: ValidationResult):
        """格式验证"""
        rule = self.validation_rules['format_check']
        if not rule.enabled:
            return
        
        result.applied_rules.append(rule.name)
        
        # 检查必要字段
        if not signal.raw_message:
            result.errors.append("原始消息为空")
        
        if not signal.symbol:
            result.errors.append("交易对为空")
        
        if signal.quantity <= 0:
            result.errors.append("交易数量必须大于0")
        
        if not isinstance(signal.action, SignalAction):
            result.errors.append("交易动作无效")
    
    def _validate_quantity_range(self, signal: ParsedSignal, result: ValidationResult):
        """数量范围验证"""
        rule = self.validation_rules['quantity_range']
        if not rule.enabled:
            return
        
        result.applied_rules.append(rule.name)
        
        # 合理数量范围（根据经验设定）
        min_quantity = 0.1
        max_quantity = 1000.0
        
        if signal.quantity < min_quantity:
            result.warnings.append(f"交易数量过小: {signal.quantity} < {min_quantity}")
            result.confidence_score *= 0.8
        
        if signal.quantity > max_quantity:
            result.warnings.append(f"交易数量过大: {signal.quantity} > {max_quantity}")
            result.confidence_score *= 0.7
        
        # 检查小数点精度
        if signal.quantity != round(signal.quantity, 1):
            result.warnings.append("交易数量精度过高，可能存在解析错误")
            result.confidence_score *= 0.9
    
    def _validate_symbol(self, signal: ParsedSignal, result: ValidationResult):
        """交易对验证"""
        rule = self.validation_rules['symbol_validation']
        if not rule.enabled:
            return
        
        result.applied_rules.append(rule.name)
        
        # 支持的交易对列表
        supported_symbols = [
            'BTC-USDT-SWAP',
            'ETH-USDT-SWAP',
            'CONTROL'  # 控制命令
        ]
        
        if signal.symbol not in supported_symbols:
            if signal.signal_type != SignalType.CONTROL:
                result.warnings.append(f"未知的交易对: {signal.symbol}")
                result.confidence_score *= 0.8
    
    def _validate_duplicate(self, signal: ParsedSignal, result: ValidationResult):
        """重复信号验证"""
        rule = self.validation_rules['duplicate_check']
        if not rule.enabled:
            return
        
        result.applied_rules.append(rule.name)
        
        # 检查最近的信号历史
        recent_threshold = timedelta(minutes=1)
        current_time = signal.timestamp
        
        for historical_signal in reversed(self.signal_history[-10:]):  # 只检查最近10个
            time_diff = current_time - historical_signal.timestamp
            
            if time_diff < recent_threshold:
                # 检查是否为完全相同的信号
                if (historical_signal.raw_message.strip() == signal.raw_message.strip() or
                    (historical_signal.action == signal.action and 
                     historical_signal.quantity == signal.quantity and 
                     historical_signal.symbol == signal.symbol)):
                    
                    result.warnings.append(f"检测到重复信号 (间隔: {time_diff.total_seconds():.1f}秒)")
                    result.confidence_score *= 0.5
                    result.metadata['is_duplicate'] = True
                    break
    
    def _validate_timing(self, signal: ParsedSignal, result: ValidationResult):
        """时间合理性验证"""
        rule = self.validation_rules['timing_check']
        if not rule.enabled:
            return
        
        result.applied_rules.append(rule.name)
        
        current_time = datetime.utcnow()
        signal_time = signal.timestamp
        
        # 检查信号时间是否过于超前或滞后
        time_diff = abs((current_time - signal_time).total_seconds())
        
        if time_diff > 300:  # 5分钟
            result.warnings.append(f"信号时间异常: 与当前时间相差 {time_diff:.1f} 秒")
            result.confidence_score *= 0.8
    
    def _validate_sequence_logic(self, signal: ParsedSignal, result: ValidationResult):
        """序列逻辑验证"""
        rule = self.validation_rules['sequence_logic']
        if not rule.enabled:
            return
        
        result.applied_rules.append(rule.name)
        
        if signal.signal_type != SignalType.FORWARD:
            return
        
        # 获取最近的同类型信号
        recent_signals = self._get_recent_trading_signals(minutes=30)
        
        if not recent_signals:
            return
        
        last_signal = recent_signals[-1]
        
        # 检查开平逻辑
        if signal.metadata.get('is_closing') and last_signal.metadata.get('is_closing'):
            result.warnings.append("连续平仓信号，可能存在逻辑错误")
            result.confidence_score *= 0.9
        
        # 检查数量序列
        if signal.metadata.get('is_opening'):
            recent_quantities = [s.quantity for s in recent_signals if s.metadata.get('is_opening')]
            if recent_quantities:
                # 检查数量是否合理递增
                if len(recent_quantities) >= 2 and signal.quantity < max(recent_quantities):
                    result.warnings.append("开仓数量序列异常，未按预期递增")
                    result.confidence_score *= 0.9
    
    def _validate_confidence_threshold(self, signal: ParsedSignal, result: ValidationResult):
        """置信度阈值验证"""
        rule = self.validation_rules['confidence_threshold']
        if not rule.enabled:
            return
        
        result.applied_rules.append(rule.name)
        
        min_confidence = 0.3
        
        if signal.confidence < min_confidence:
            result.warnings.append(f"信号置信度过低: {signal.confidence:.2f} < {min_confidence}")
            result.confidence_score *= signal.confidence
    
    def _calculate_final_result(self, signal: ParsedSignal, result: ValidationResult):
        """计算最终验证结果"""
        # 如果有错误，则验证失败
        if result.errors:
            result.is_valid = False
            result.confidence_score = 0.0
        
        # 调整置信度分数
        result.confidence_score = min(1.0, max(0.0, result.confidence_score))
        
        # 设置元数据
        result.metadata.update({
            'original_confidence': signal.confidence,
            'validation_timestamp': datetime.utcnow().isoformat(),
            'signal_strength': signal.metadata.get('strength', 'unknown')
        })
    
    def _update_signal_history(self, signal: ParsedSignal):
        """更新信号历史"""
        self.signal_history.append(signal)
        
        # 限制历史记录大小
        if len(self.signal_history) > self.max_history_size:
            self.signal_history = self.signal_history[-self.max_history_size:]
    
    def _update_validation_stats(self, result: ValidationResult):
        """更新验证统计"""
        if result.is_valid:
            if result.warnings:
                self.validation_stats['warning_signals'] += 1
            else:
                self.validation_stats['passed_signals'] += 1
        else:
            self.validation_stats['rejected_signals'] += 1
        
        # 统计规则违反情况
        for rule_name in result.applied_rules:
            if rule_name not in self.validation_stats['rule_violations']:
                self.validation_stats['rule_violations'][rule_name] = 0
            
            if result.errors or result.warnings:
                self.validation_stats['rule_violations'][rule_name] += 1
    
    def _log_validation_result(self, signal: ParsedSignal, result: ValidationResult):
        """记录验证结果"""
        if not result.is_valid:
            self.logger.error(
                f"信号验证失败: {signal.raw_message}",
                signal_data={
                    'signal': signal.to_dict(),
                    'validation_result': {
                        'errors': result.errors,
                        'warnings': result.warnings,
                        'confidence_score': result.confidence_score
                    }
                }
            )
        elif result.warnings:
            self.logger.warning(
                f"信号验证通过但有警告: {signal.raw_message}",
                signal_data={
                    'signal': signal.to_dict(),
                    'validation_result': {
                        'warnings': result.warnings,
                        'confidence_score': result.confidence_score
                    }
                }
            )
        else:
            self.logger.info(
                f"信号验证通过: {signal.action.value} {signal.quantity} {signal.symbol}",
                signal_data={
                    'signal': signal.to_dict(),
                    'confidence_score': result.confidence_score
                }
            )
    
    def _get_recent_trading_signals(self, minutes: int = 30) -> List[ParsedSignal]:
        """获取最近的交易信号"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        return [
            signal for signal in self.signal_history
            if (signal.timestamp >= cutoff_time and 
                signal.signal_type == SignalType.FORWARD)
        ]
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        total = self.validation_stats['total_validated']
        if total == 0:
            return self.validation_stats
        
        return {
            **self.validation_stats,
            'pass_rate': f"{(self.validation_stats['passed_signals'] / total * 100):.2f}%",
            'reject_rate': f"{(self.validation_stats['rejected_signals'] / total * 100):.2f}%",
            'warning_rate': f"{(self.validation_stats['warning_signals'] / total * 100):.2f}%"
        }
    
    def update_rule(self, rule_name: str, enabled: bool = None, severity: str = None):
        """更新验证规则"""
        if rule_name in self.validation_rules:
            rule = self.validation_rules[rule_name]
            if enabled is not None:
                rule.enabled = enabled
            if severity is not None:
                rule.severity = severity
            
            self.logger.info(f"验证规则已更新: {rule_name} enabled={rule.enabled} severity={rule.severity}")
        else:
            self.logger.warning(f"未找到验证规则: {rule_name}")
    
    def clear_history(self):
        """清空信号历史"""
        self.signal_history.clear()
        self.logger.info("信号历史已清空")