"""
反向跟单机器人核心库

设计哲学：
"分享智慧，传承经验。
核心库是整个生态系统的灵魂，承载着所有项目的共同智慧。"
"""

__version__ = "1.0.0"
__author__ = "RovoDev Team"
__description__ = "反向跟单机器人核心库"

# 导出核心组件
from .core import Config, Logger, get_logger
from .core.exceptions import (
    TradingBotException,
    SignalException,
    StrategyException,
    RiskException,
    ExecutionException,
    NetworkException
)

# 导出信号处理组件
from .signal_processor import (
    TelegramListener,
    SignalParser,
    ParsedSignal,
    SignalValidator,
    SignalDispatcher
)

# 导出交易引擎组件
from .trading_engine import (
    ExchangeClient,
    OrderExecutor,
    PriceMonitor,
    BalanceManager
)

# 导出工具组件
from .utils import (
    TimeUtils,
    MathUtils,
    ValidationUtils
)

__all__ = [
    # 版本信息
    '__version__',
    '__author__',
    '__description__',
    
    # 核心组件
    'Config',
    'Logger',
    'get_logger',
    
    # 异常类
    'TradingBotException',
    'SignalException',
    'StrategyException', 
    'RiskException',
    'ExecutionException',
    'NetworkException',
    
    # 信号处理
    'TelegramListener',
    'SignalParser',
    'ParsedSignal',
    'SignalValidator',
    'SignalDispatcher',
    
    # 交易引擎
    'ExchangeClient',
    'OrderExecutor',
    'PriceMonitor',
    'BalanceManager',
    
    # 工具类
    'TimeUtils',
    'MathUtils',
    'ValidationUtils'
]