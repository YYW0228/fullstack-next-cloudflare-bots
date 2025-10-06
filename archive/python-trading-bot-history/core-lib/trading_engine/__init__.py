"""
交易执行引擎 - 系统的执行力

设计哲学：
"策略是思想，执行是行动。
思想再完美，没有精确的执行也是空谈。
执行再快速，没有智慧的策略也是盲动。"

本模块负责：
1. 交易所接口封装和管理
2. 订单执行和状态跟踪
3. 价格监控和市场数据
4. 资金管理和风险控制

核心原则：
- 精确执行：确保每个订单都按预期执行
- 实时监控：持续跟踪市场变化
- 容错恢复：优雅处理网络和API异常
- 性能优化：最小化延迟和资源消耗
"""

from .exchange_client import ExchangeClient, ExchangeConfig
from .order_executor import OrderExecutor, OrderType, OrderSide
from .price_monitor import PriceMonitor, PriceData
from .balance_manager import BalanceManager, AccountBalance

__all__ = [
    'ExchangeClient',
    'ExchangeConfig',
    'OrderExecutor', 
    'OrderType',
    'OrderSide',
    'PriceMonitor',
    'PriceData',
    'BalanceManager',
    'AccountBalance'
]