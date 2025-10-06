"""
信号处理模块 - 系统的感知层

设计哲学：
"信号是市场的语言，我们要做忠实的翻译者。
纯净的感知，准确的理解，及时的传递。"

本模块负责：
1. 监听Telegram信号
2. 解析和验证信号
3. 分发信号到策略引擎

核心原则：
- 单一数据流：确保信号的完整性
- 实时性：最小化信号延迟
- 容错性：优雅处理异常信号
- 可扩展性：支持多种信号源
"""

from .telegram_listener import TelegramListener
from .signal_parser import SignalParser, ParsedSignal
from .signal_validator import SignalValidator
from .signal_dispatcher import SignalDispatcher

__all__ = [
    'TelegramListener',
    'SignalParser',
    'ParsedSignal', 
    'SignalValidator',
    'SignalDispatcher'
]