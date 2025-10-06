"""
数学工具类 - 精确计算的智慧

设计哲学：
"数学是宇宙的语言，精确的计算是交易成功的基础。"
"""

import math
from typing import List, Optional, Union, Tuple
from decimal import Decimal, ROUND_HALF_UP
import statistics


class MathUtils:
    """
    数学工具类 - 提供交易中常用的数学计算功能
    
    功能：
    1. 精确的浮点数计算
    2. 统计分析函数
    3. 技术指标计算
    4. 风险度量计算
    """
    
    @staticmethod
    def round_decimal(value: float, precision: int) -> float:
        """
        精确的小数点舍入
        
        Args:
            value: 要舍入的值
            precision: 小数点位数
            
        Returns:
            舍入后的值
        """
        decimal_value = Decimal(str(value))
        rounded = decimal_value.quantize(
            Decimal('0.' + '0' * precision), 
            rounding=ROUND_HALF_UP
        )
        return float(rounded)
    
    @staticmethod
    def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
        """
        安全除法，避免除零错误
        
        Args:
            numerator: 分子
            denominator: 分母
            default: 分母为零时的默认值
            
        Returns:
            除法结果
        """
        if abs(denominator) < 1e-10:  # 避免浮点数精度问题
            return default
        return numerator / denominator
    
    @staticmethod
    def percentage_change(old_value: float, new_value: float) -> float:
        """
        计算百分比变化
        
        Args:
            old_value: 原值
            new_value: 新值
            
        Returns:
            百分比变化（小数形式）
        """
        if abs(old_value) < 1e-10:
            return 0.0
        return (new_value - old_value) / old_value
    
    @staticmethod
    def compound_return(returns: List[float]) -> float:
        """
        计算复合收益率
        
        Args:
            returns: 收益率列表（小数形式）
            
        Returns:
            复合收益率
        """
        if not returns:
            return 0.0
        
        compound = 1.0
        for r in returns:
            compound *= (1 + r)
        
        return compound - 1.0
    
    @staticmethod
    def annualized_return(total_return: float, days: int) -> float:
        """
        计算年化收益率
        
        Args:
            total_return: 总收益率
            days: 投资天数
            
        Returns:
            年化收益率
        """
        if days <= 0:
            return 0.0
        
        return (1 + total_return) ** (365.25 / days) - 1
    
    @staticmethod
    def volatility(returns: List[float], annualized: bool = True) -> float:
        """
        计算波动率（标准差）
        
        Args:
            returns: 收益率列表
            annualized: 是否年化
            
        Returns:
            波动率
        """
        if len(returns) < 2:
            return 0.0
        
        vol = statistics.stdev(returns)
        
        if annualized:
            # 假设252个交易日
            vol *= math.sqrt(252)
        
        return vol
    
    @staticmethod
    def sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
        """
        计算夏普比率
        
        Args:
            returns: 收益率列表
            risk_free_rate: 无风险利率
            
        Returns:
            夏普比率
        """
        if len(returns) < 2:
            return 0.0
        
        excess_returns = [r - risk_free_rate for r in returns]
        mean_excess = statistics.mean(excess_returns)
        std_excess = statistics.stdev(excess_returns)
        
        return MathUtils.safe_divide(mean_excess, std_excess)
    
    @staticmethod
    def max_drawdown(values: List[float]) -> float:
        """
        计算最大回撤
        
        Args:
            values: 净值序列
            
        Returns:
            最大回撤（正数）
        """
        if len(values) < 2:
            return 0.0
        
        peak = values[0]
        max_dd = 0.0
        
        for value in values[1:]:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    @staticmethod
    def calmar_ratio(total_return: float, max_drawdown: float) -> float:
        """
        计算卡尔玛比率
        
        Args:
            total_return: 总收益率
            max_drawdown: 最大回撤
            
        Returns:
            卡尔玛比率
        """
        return MathUtils.safe_divide(total_return, max_drawdown)
    
    @staticmethod
    def win_rate(trades: List[float]) -> float:
        """
        计算胜率
        
        Args:
            trades: 交易盈亏列表
            
        Returns:
            胜率（0-1之间）
        """
        if not trades:
            return 0.0
        
        winning_trades = sum(1 for trade in trades if trade > 0)
        return winning_trades / len(trades)
    
    @staticmethod
    def profit_factor(trades: List[float]) -> float:
        """
        计算盈利因子
        
        Args:
            trades: 交易盈亏列表
            
        Returns:
            盈利因子
        """
        if not trades:
            return 0.0
        
        gross_profit = sum(trade for trade in trades if trade > 0)
        gross_loss = abs(sum(trade for trade in trades if trade < 0))
        
        return MathUtils.safe_divide(gross_profit, gross_loss, float('inf'))
    
    @staticmethod
    def average_win_loss_ratio(trades: List[float]) -> float:
        """
        计算平均盈亏比
        
        Args:
            trades: 交易盈亏列表
            
        Returns:
            平均盈亏比
        """
        if not trades:
            return 0.0
        
        winning_trades = [trade for trade in trades if trade > 0]
        losing_trades = [abs(trade) for trade in trades if trade < 0]
        
        if not winning_trades or not losing_trades:
            return float('inf') if winning_trades else 0.0
        
        avg_win = statistics.mean(winning_trades)
        avg_loss = statistics.mean(losing_trades)
        
        return MathUtils.safe_divide(avg_win, avg_loss)
    
    @staticmethod
    def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        计算凯利公式最优仓位
        
        Args:
            win_rate: 胜率
            avg_win: 平均盈利
            avg_loss: 平均亏损
            
        Returns:
            最优仓位比例（0-1）
        """
        if avg_loss <= 0:
            return 0.0
        
        b = avg_win / avg_loss  # 盈亏比
        p = win_rate  # 胜率
        q = 1 - p  # 败率
        
        kelly = (b * p - q) / b
        
        # 限制在合理范围内
        return max(0.0, min(1.0, kelly))
    
    @staticmethod
    def position_size_by_risk(
        account_balance: float,
        risk_percentage: float,
        entry_price: float,
        stop_loss_price: float,
        contract_size: float = 1.0
    ) -> float:
        """
        根据风险百分比计算仓位大小
        
        Args:
            account_balance: 账户余额
            risk_percentage: 风险百分比（如0.02表示2%）
            entry_price: 入场价格
            stop_loss_price: 止损价格
            contract_size: 合约大小
            
        Returns:
            建议仓位大小
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return 0.0
        
        # 计算每单位的风险
        risk_per_unit = abs(entry_price - stop_loss_price) * contract_size
        
        if risk_per_unit <= 0:
            return 0.0
        
        # 计算总风险金额
        total_risk = account_balance * risk_percentage
        
        # 计算仓位大小
        position_size = total_risk / risk_per_unit
        
        return position_size
    
    @staticmethod
    def fibonacci_levels(high: float, low: float) -> dict:
        """
        计算斐波那契回调位
        
        Args:
            high: 最高价
            low: 最低价
            
        Returns:
            斐波那契水平位字典
        """
        diff = high - low
        
        return {
            '0%': high,
            '23.6%': high - 0.236 * diff,
            '38.2%': high - 0.382 * diff,
            '50%': high - 0.5 * diff,
            '61.8%': high - 0.618 * diff,
            '78.6%': high - 0.786 * diff,
            '100%': low
        }
    
    @staticmethod
    def ema(values: List[float], period: int) -> List[float]:
        """
        计算指数移动平均线
        
        Args:
            values: 价格序列
            period: 周期
            
        Returns:
            EMA序列
        """
        if len(values) < period:
            return []
        
        alpha = 2.0 / (period + 1)
        ema_values = []
        
        # 第一个值使用SMA
        sma = sum(values[:period]) / period
        ema_values.append(sma)
        
        # 后续值使用EMA公式
        for i in range(period, len(values)):
            ema = alpha * values[i] + (1 - alpha) * ema_values[-1]
            ema_values.append(ema)
        
        return ema_values
    
    @staticmethod
    def rsi(values: List[float], period: int = 14) -> List[float]:
        """
        计算相对强弱指数
        
        Args:
            values: 价格序列
            period: 周期
            
        Returns:
            RSI序列
        """
        if len(values) < period + 1:
            return []
        
        # 计算价格变化
        changes = [values[i] - values[i-1] for i in range(1, len(values))]
        
        # 分离涨跌
        gains = [max(0, change) for change in changes]
        losses = [abs(min(0, change)) for change in changes]
        
        rsi_values = []
        
        # 计算初始平均涨跌幅
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        for i in range(period, len(changes)):
            # 更新平均涨跌幅
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            # 计算RSI
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        return rsi_values
    
    @staticmethod
    def bollinger_bands(values: List[float], period: int = 20, std_dev: float = 2.0) -> dict:
        """
        计算布林带
        
        Args:
            values: 价格序列
            period: 周期
            std_dev: 标准差倍数
            
        Returns:
            布林带字典（upper, middle, lower）
        """
        if len(values) < period:
            return {'upper': [], 'middle': [], 'lower': []}
        
        upper, middle, lower = [], [], []
        
        for i in range(period - 1, len(values)):
            window = values[i - period + 1:i + 1]
            sma = sum(window) / period
            variance = sum((x - sma) ** 2 for x in window) / period
            std = math.sqrt(variance)
            
            middle.append(sma)
            upper.append(sma + std_dev * std)
            lower.append(sma - std_dev * std)
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }


class StatisticsCalculator:
    """统计计算器 - 专门用于交易统计分析"""
    
    def __init__(self):
        self.trades = []
        self.equity_curve = []
    
    def add_trade(self, pnl: float):
        """添加交易记录"""
        self.trades.append(pnl)
        
        # 更新权益曲线
        if self.equity_curve:
            self.equity_curve.append(self.equity_curve[-1] + pnl)
        else:
            self.equity_curve.append(pnl)
    
    def get_statistics(self) -> dict:
        """获取完整的交易统计"""
        if not self.trades:
            return {}
        
        return {
            'total_trades': len(self.trades),
            'total_pnl': sum(self.trades),
            'win_rate': MathUtils.win_rate(self.trades),
            'profit_factor': MathUtils.profit_factor(self.trades),
            'avg_win_loss_ratio': MathUtils.average_win_loss_ratio(self.trades),
            'max_drawdown': MathUtils.max_drawdown(self.equity_curve),
            'sharpe_ratio': MathUtils.sharpe_ratio(self.trades),
            'volatility': MathUtils.volatility(self.trades),
            'best_trade': max(self.trades) if self.trades else 0,
            'worst_trade': min(self.trades) if self.trades else 0,
            'average_trade': statistics.mean(self.trades)
        }


def calculate_position_size(account_balance: float, risk_percentage: float, 
                          entry_price: float, stop_loss_price: float,
                          min_size: float = 0.01, max_size: float = None) -> float:
    """
    计算仓位大小
    
    Args:
        account_balance: 账户余额
        risk_percentage: 风险比例 (0-1)
        entry_price: 入场价格
        stop_loss_price: 止损价格
        min_size: 最小仓位
        max_size: 最大仓位
    
    Returns:
        计算出的仓位大小
    """
    if entry_price <= 0 or stop_loss_price <= 0 or account_balance <= 0:
        return min_size
    
    # 计算风险金额
    risk_amount = account_balance * risk_percentage
    
    # 计算价格差异
    price_diff = abs(entry_price - stop_loss_price)
    if price_diff == 0:
        return min_size
    
    # 计算仓位大小
    position_size = risk_amount / price_diff
    
    # 应用最小和最大限制
    position_size = max(position_size, min_size)
    if max_size is not None:
        position_size = min(position_size, max_size)
    
    return round(position_size, 8)