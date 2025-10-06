"""
异常体系模块 - 优雅的失败处理

设计哲学：
"失败不是终点，而是学习的起点。
每个异常都应该携带足够的信息，帮助系统理解问题并自我修复。"
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "LOW"           # 低：不影响主要功能
    MEDIUM = "MEDIUM"     # 中：影响部分功能
    HIGH = "HIGH"         # 高：影响核心功能
    CRITICAL = "CRITICAL" # 严重：系统无法继续运行


class ErrorCategory(Enum):
    """错误分类"""
    SIGNAL = "SIGNAL"           # 信号相关错误
    STRATEGY = "STRATEGY"       # 策略相关错误
    EXECUTION = "EXECUTION"     # 执行相关错误
    RISK = "RISK"              # 风控相关错误
    NETWORK = "NETWORK"        # 网络相关错误
    DATA = "DATA"              # 数据相关错误
    CONFIG = "CONFIG"          # 配置相关错误
    SYSTEM = "SYSTEM"          # 系统相关错误


class TradingBotException(Exception):
    """
    交易机器人基础异常类
    
    设计原则：
    1. 携带丰富的上下文信息
    2. 支持错误分类和严重程度
    3. 便于日志记录和分析
    4. 支持自动恢复建议
    """
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestion: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.recovery_suggestion = recovery_suggestion
        self.original_exception = original_exception
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于日志记录"""
        return {
            'exception_type': self.__class__.__name__,
            'message': self.message,
            'category': self.category.value,
            'severity': self.severity.value,
            'context': self.context,
            'recovery_suggestion': self.recovery_suggestion,
            'original_exception': str(self.original_exception) if self.original_exception else None
        }
    
    def is_recoverable(self) -> bool:
        """判断异常是否可恢复"""
        return self.severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]
    
    def requires_immediate_attention(self) -> bool:
        """判断是否需要立即关注"""
        return self.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
    
    def __str__(self) -> str:
        return f"[{self.category.value}|{self.severity.value}] {self.message}"


class SignalException(TradingBotException):
    """信号相关异常"""
    
    def __init__(
        self,
        message: str,
        signal_data: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if signal_data:
            context.update({'signal_data': signal_data})
        
        super().__init__(
            message=message,
            category=ErrorCategory.SIGNAL,
            severity=severity,
            context=context,
            **{k: v for k, v in kwargs.items() if k != 'context'}
        )


class InvalidSignalFormatException(SignalException):
    """无效信号格式异常"""
    
    def __init__(self, raw_signal: str, expected_format: str = None):
        super().__init__(
            message=f"信号格式无效: {raw_signal}",
            signal_data={'raw_signal': raw_signal, 'expected_format': expected_format},
            severity=ErrorSeverity.LOW,
            recovery_suggestion="检查信号源是否正常，或更新信号解析规则"
        )


class SignalTimeoutException(SignalException):
    """信号超时异常"""
    
    def __init__(self, timeout_seconds: int):
        super().__init__(
            message=f"信号接收超时: {timeout_seconds}秒",
            context={'timeout_seconds': timeout_seconds},
            severity=ErrorSeverity.MEDIUM,
            recovery_suggestion="检查网络连接和信号源状态"
        )


class StrategyException(TradingBotException):
    """策略相关异常"""
    
    def __init__(
        self,
        message: str,
        strategy_name: Optional[str] = None,
        strategy_data: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if strategy_name:
            context.update({'strategy_name': strategy_name})
        if strategy_data:
            context.update({'strategy_data': strategy_data})
        
        super().__init__(
            message=message,
            category=ErrorCategory.STRATEGY,
            severity=severity,
            context=context,
            **{k: v for k, v in kwargs.items() if k != 'context'}
        )


class PositionCalculationException(StrategyException):
    """仓位计算异常"""
    
    def __init__(self, calculation_error: str, input_data: Dict[str, Any]):
        super().__init__(
            message=f"仓位计算错误: {calculation_error}",
            strategy_data=input_data,
            severity=ErrorSeverity.HIGH,
            recovery_suggestion="检查计算参数和市场数据"
        )


class StrategyLogicException(StrategyException):
    """策略逻辑异常"""
    
    def __init__(self, logic_error: str, strategy_state: Dict[str, Any]):
        super().__init__(
            message=f"策略逻辑错误: {logic_error}",
            strategy_data=strategy_state,
            severity=ErrorSeverity.HIGH,
            recovery_suggestion="检查策略参数和市场条件"
        )


class ExecutionException(TradingBotException):
    """执行相关异常"""
    
    def __init__(
        self,
        message: str,
        order_data: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if order_data:
            context.update({'order_data': order_data})
        
        super().__init__(
            message=message,
            category=ErrorCategory.EXECUTION,
            severity=severity,
            context=context,
            **{k: v for k, v in kwargs.items() if k != 'context'}
        )


class OrderExecutionException(ExecutionException):
    """订单执行异常"""
    
    def __init__(self, order_error: str, order_details: Dict[str, Any]):
        super().__init__(
            message=f"订单执行失败: {order_error}",
            order_data=order_details,
            severity=ErrorSeverity.HIGH,
            recovery_suggestion="检查账户余额、网络连接和交易所状态"
        )


class InsufficientBalanceException(ExecutionException):
    """余额不足异常"""
    
    def __init__(self, required_amount: float, available_amount: float):
        super().__init__(
            message=f"余额不足: 需要 {required_amount}, 可用 {available_amount}",
            order_data={
                'required_amount': required_amount,
                'available_amount': available_amount
            },
            severity=ErrorSeverity.HIGH,
            recovery_suggestion="等待资金到账或调整仓位大小"
        )


class PositionNotFoundException(ExecutionException):
    """仓位不存在异常"""
    
    def __init__(self, position_info: str):
        super().__init__(
            message=f"未找到仓位: {position_info}",
            severity=ErrorSeverity.MEDIUM,
            recovery_suggestion="检查仓位状态同步或忽略此次平仓操作"
        )


class RiskException(TradingBotException):
    """风控相关异常"""
    
    def __init__(
        self,
        message: str,
        risk_data: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if risk_data:
            context.update({'risk_data': risk_data})
        
        super().__init__(
            message=message,
            category=ErrorCategory.RISK,
            severity=severity,
            context=context,
            **{k: v for k, v in kwargs.items() if k != 'context'}
        )


class PositionSizeExceededException(RiskException):
    """仓位超限异常"""
    
    def __init__(self, current_size: float, max_size: float):
        super().__init__(
            message=f"仓位超限: 当前 {current_size}, 最大 {max_size}",
            risk_data={
                'current_size': current_size,
                'max_size': max_size
            },
            severity=ErrorSeverity.CRITICAL,
            recovery_suggestion="立即减仓到安全水平"
        )


class DrawdownExceededException(RiskException):
    """回撤超限异常"""
    
    def __init__(self, current_drawdown: float, max_drawdown: float):
        super().__init__(
            message=f"回撤超限: 当前 {current_drawdown:.2%}, 最大 {max_drawdown:.2%}",
            risk_data={
                'current_drawdown': current_drawdown,
                'max_drawdown': max_drawdown
            },
            severity=ErrorSeverity.CRITICAL,
            recovery_suggestion="停止交易并评估风险"
        )


class RiskLimitBreachException(RiskException):
    """风控限制违反异常"""
    
    def __init__(self, limit_type: str, current_value: float, limit_value: float):
        super().__init__(
            message=f"风控限制违反: {limit_type} 当前值 {current_value}, 限制值 {limit_value}",
            risk_data={
                'limit_type': limit_type,
                'current_value': current_value,
                'limit_value': limit_value
            },
            severity=ErrorSeverity.HIGH,
            recovery_suggestion="调整仓位或暂停交易"
        )


class NetworkException(TradingBotException):
    """网络相关异常"""
    
    def __init__(
        self,
        message: str,
        network_data: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if network_data:
            context.update({'network_data': network_data})
        
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=severity,
            context=context,
            recovery_suggestion="检查网络连接，稍后重试",
            **{k: v for k, v in kwargs.items() if k != 'context'}
        )


class APIException(NetworkException):
    """API异常"""
    
    def __init__(self, api_error: str, status_code: Optional[int] = None):
        super().__init__(
            message=f"API错误: {api_error}",
            network_data={'status_code': status_code} if status_code else None,
            severity=ErrorSeverity.MEDIUM if status_code != 500 else ErrorSeverity.HIGH
        )


class ConnectionTimeoutException(NetworkException):
    """连接超时异常"""
    
    def __init__(self, timeout_seconds: int, target: str):
        super().__init__(
            message=f"连接超时: {target} ({timeout_seconds}秒)",
            network_data={'timeout_seconds': timeout_seconds, 'target': target},
            severity=ErrorSeverity.MEDIUM
        )


class DataException(TradingBotException):
    """数据相关异常"""
    
    def __init__(
        self,
        message: str,
        data_info: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if data_info:
            context.update({'data_info': data_info})
        
        super().__init__(
            message=message,
            category=ErrorCategory.DATA,
            severity=severity,
            context=context,
            **{k: v for k, v in kwargs.items() if k != 'context'}
        )


class DataValidationException(DataException):
    """数据验证异常"""
    
    def __init__(self, validation_error: str, invalid_data: Any):
        super().__init__(
            message=f"数据验证失败: {validation_error}",
            data_info={'invalid_data': str(invalid_data)},
            severity=ErrorSeverity.LOW,
            recovery_suggestion="检查数据格式和来源"
        )


class ConfigException(TradingBotException):
    """配置相关异常"""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if config_key:
            context.update({'config_key': config_key})
        
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIG,
            severity=severity,
            context=context,
            recovery_suggestion="检查配置文件完整性",
            **{k: v for k, v in kwargs.items() if k != 'context'}
        )


# 异常处理装饰器
def handle_exceptions(
    default_return=None,
    log_errors: bool = True,
    re_raise: bool = False
):
    """
    异常处理装饰器
    
    Args:
        default_return: 发生异常时的默认返回值
        log_errors: 是否记录错误日志
        re_raise: 是否重新抛出异常
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except TradingBotException as e:
                if log_errors:
                    # 这里需要在实际使用时导入logger
                    print(f"业务异常: {e}")
                
                if re_raise:
                    raise
                return default_return
            except Exception as e:
                if log_errors:
                    print(f"系统异常: {e}")
                
                if re_raise:
                    # 包装为业务异常
                    raise TradingBotException(
                        message=f"未预期的系统错误: {str(e)}",
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.HIGH,
                        original_exception=e
                    )
                return default_return
        return wrapper
    return decorator