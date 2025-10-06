"""
策略引擎模块 - 系统的智慧大脑

设计哲学：
"策略是智慧的结晶，执行是勇气的体现。
真正的智慧不在于预测未来，而在于适应变化。"

本模块负责：
1. 策略抽象和管理
2. 反向跟单策略实现
3. 仓位管理和风险控制
4. 策略性能监控和优化

核心原则：
- 策略与执行分离：策略负责决策，执行负责实现
- 多策略并行：支持同时运行多个策略
- 自适应学习：从市场反馈中持续优化
- 风险优先：所有决策都要考虑风险
"""

from .base_strategy import BaseStrategy, StrategyState
from .simple_reverse_bot import SimpleReverseBot
from .turtle_reverse_bot import TurtleReverseBot
from .strategy_selector import StrategySelector
from .position_manager import PositionManager, Position

__all__ = [
    'BaseStrategy',
    'StrategyState',
    'SimpleReverseBot',
    'TurtleReverseBot', 
    'StrategySelector',
    'PositionManager',
    'Position'
]