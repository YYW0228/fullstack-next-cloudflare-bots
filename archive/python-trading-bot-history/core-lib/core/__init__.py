"""
核心模块 - 系统的哲学基础

这个模块包含了整个系统的基础设施：
- 配置管理：单一真相源
- 日志系统：智慧的记录者
- 异常体系：优雅的失败处理

设计哲学：
"一个好的系统，应该像一个有智慧的生命体，
能够感知、思考、决策、执行，并从错误中学习。"
"""

__version__ = "1.0.0"
__author__ = "Rovo Dev"
__description__ = "反向跟单机器人核心模块"

# 导出核心组件
from .config import Config
from .logger import Logger, get_logger
from .exceptions import (
    TradingBotException,
    SignalException,
    StrategyException,
    RiskException,
    ExecutionException
)

__all__ = [
    'Config',
    'Logger', 
    'get_logger',
    'TradingBotException',
    'SignalException', 
    'StrategyException',
    'RiskException',
    'ExecutionException'
]