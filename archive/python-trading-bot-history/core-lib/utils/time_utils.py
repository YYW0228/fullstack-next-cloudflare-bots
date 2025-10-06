"""
时间工具类 - 时间的智慧管理者

设计哲学：
"时间是最宝贵的资源，精确处理时间是系统稳定的基础。"
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import pytz


class TimeUtils:
    """
    时间工具类 - 提供统一的时间处理功能
    
    功能：
    1. 时区转换和标准化
    2. 时间格式化和解析
    3. 交易时间判断
    4. 性能计时工具
    """
    
    # 常用时区
    UTC = pytz.UTC
    BEIJING = pytz.timezone('Asia/Shanghai')
    NEW_YORK = pytz.timezone('America/New_York')
    LONDON = pytz.timezone('Europe/London')
    
    @staticmethod
    def now(tz: Optional[timezone] = None) -> datetime:
        """
        获取当前时间
        
        Args:
            tz: 时区，默认UTC
            
        Returns:
            当前时间
        """
        if tz is None:
            tz = TimeUtils.UTC
        return datetime.now(tz)
    
    @staticmethod
    def utc_now() -> datetime:
        """获取UTC当前时间"""
        return datetime.utcnow().replace(tzinfo=TimeUtils.UTC)
    
    @staticmethod
    def beijing_now() -> datetime:
        """获取北京时间"""
        return TimeUtils.now(TimeUtils.BEIJING)
    
    @staticmethod
    def to_timestamp(dt: datetime) -> float:
        """转换为时间戳"""
        return dt.timestamp()
    
    @staticmethod
    def from_timestamp(timestamp: float, tz: Optional[timezone] = None) -> datetime:
        """从时间戳创建datetime"""
        if tz is None:
            tz = TimeUtils.UTC
        return datetime.fromtimestamp(timestamp, tz)
    
    @staticmethod
    def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化日期时间"""
        return dt.strftime(fmt)
    
    @staticmethod
    def parse_datetime(dt_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
        """解析日期时间字符串"""
        return datetime.strptime(dt_str, fmt)
    
    @staticmethod
    def convert_timezone(dt: datetime, from_tz: timezone, to_tz: timezone) -> datetime:
        """时区转换"""
        if dt.tzinfo is None:
            dt = from_tz.localize(dt)
        return dt.astimezone(to_tz)
    
    @staticmethod
    def is_market_hours(dt: Optional[datetime] = None, market: str = "crypto") -> bool:
        """
        判断是否在交易时间内
        
        Args:
            dt: 时间，默认当前时间
            market: 市场类型 (crypto, forex, stock_us, stock_cn)
            
        Returns:
            是否在交易时间内
        """
        if dt is None:
            dt = TimeUtils.utc_now()
        
        if market == "crypto":
            return True  # 加密货币24小时交易
        
        elif market == "forex":
            # 外汇周一到周五24小时
            weekday = dt.weekday()
            return 0 <= weekday <= 4  # 周一到周五
        
        elif market == "stock_us":
            # 美股交易时间（UTC）
            ny_time = TimeUtils.convert_timezone(dt, TimeUtils.UTC, TimeUtils.NEW_YORK)
            weekday = ny_time.weekday()
            hour = ny_time.hour
            
            # 周一到周五 9:30-16:00
            return 0 <= weekday <= 4 and 9.5 <= hour + ny_time.minute/60 <= 16
        
        elif market == "stock_cn":
            # A股交易时间（北京时间）
            bj_time = TimeUtils.convert_timezone(dt, TimeUtils.UTC, TimeUtils.BEIJING)
            weekday = bj_time.weekday()
            hour = bj_time.hour
            
            # 周一到周五 9:30-11:30, 13:00-15:00
            return (0 <= weekday <= 4 and 
                   ((9.5 <= hour + bj_time.minute/60 <= 11.5) or 
                    (13 <= hour + bj_time.minute/60 <= 15)))
        
        return True
    
    @staticmethod
    def get_trading_session(dt: Optional[datetime] = None) -> str:
        """
        获取当前交易时段
        
        Returns:
            交易时段字符串
        """
        if dt is None:
            dt = TimeUtils.utc_now()
        
        utc_hour = dt.hour
        
        if 0 <= utc_hour < 6:
            return "亚洲盘"
        elif 6 <= utc_hour < 14:
            return "欧洲盘"
        elif 14 <= utc_hour < 22:
            return "美洲盘"
        else:
            return "亚洲盘"
    
    @staticmethod
    def time_until_next_session(current_session: str) -> timedelta:
        """计算到下一个交易时段的时间"""
        now = TimeUtils.utc_now()
        sessions = {
            "亚洲盘": 0,
            "欧洲盘": 6, 
            "美洲盘": 14
        }
        
        session_mapping = ["亚洲盘", "欧洲盘", "美洲盘", "亚洲盘"]
        current_idx = session_mapping.index(current_session)
        next_session = session_mapping[current_idx + 1]
        
        next_hour = sessions[next_session]
        if next_session == "亚洲盘" and current_session != "亚洲盘":
            next_hour = 24  # 明天的亚洲盘
        
        next_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        if next_hour == 24:
            next_time = next_time + timedelta(days=1)
            next_time = next_time.replace(hour=0)
        
        return next_time - now
    
    @staticmethod
    def duration_to_string(duration: timedelta) -> str:
        """
        将时间差转换为可读字符串
        
        Args:
            duration: 时间差
            
        Returns:
            可读的时间字符串
        """
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}秒"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}分{seconds}秒"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}小时{minutes}分钟"
        else:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            return f"{days}天{hours}小时"
    
    @staticmethod
    def seconds_to_string(seconds: float) -> str:
        """
        将秒数转换为可读字符串
        
        Args:
            seconds: 秒数
            
        Returns:
            可读的时间字符串
        """
        if seconds < 1:
            return f"{seconds*1000:.1f}毫秒"
        elif seconds < 60:
            return f"{seconds:.2f}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{int(minutes)}分{secs:.1f}秒"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{int(hours)}小时{int(minutes)}分钟"


class Timer:
    """
    计时器类 - 用于性能测量和计时
    """
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed_time = None
    
    def start(self):
        """开始计时"""
        self.start_time = time.perf_counter()
        self.end_time = None
        self.elapsed_time = None
        return self
    
    def stop(self) -> float:
        """
        停止计时
        
        Returns:
            经过的时间（秒）
        """
        if self.start_time is None:
            raise ValueError("计时器未启动")
        
        self.end_time = time.perf_counter()
        self.elapsed_time = self.end_time - self.start_time
        return self.elapsed_time
    
    def elapsed(self) -> float:
        """
        获取当前经过的时间
        
        Returns:
            经过的时间（秒）
        """
        if self.start_time is None:
            return 0.0
        
        current_time = time.perf_counter()
        return current_time - self.start_time
    
    def __enter__(self):
        """上下文管理器入口"""
        return self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
    
    def __str__(self) -> str:
        """字符串表示"""
        if self.elapsed_time is not None:
            return f"Timer(elapsed={TimeUtils.seconds_to_string(self.elapsed_time)})"
        elif self.start_time is not None:
            return f"Timer(running={TimeUtils.seconds_to_string(self.elapsed())})"
        else:
            return "Timer(not_started)"


class RateLimiter:
    """
    速率限制器 - 控制操作频率
    """
    
    def __init__(self, max_calls: int, time_window: float):
        """
        初始化速率限制器
        
        Args:
            max_calls: 时间窗口内最大调用次数
            time_window: 时间窗口（秒）
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def can_proceed(self) -> bool:
        """
        检查是否可以继续操作
        
        Returns:
            是否可以操作
        """
        now = time.time()
        
        # 清理过期的调用记录
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < self.time_window]
        
        return len(self.calls) < self.max_calls
    
    def record_call(self):
        """记录一次调用"""
        self.calls.append(time.time())
    
    def wait_time(self) -> float:
        """
        获取需要等待的时间
        
        Returns:
            等待时间（秒）
        """
        if self.can_proceed():
            return 0.0
        
        # 计算最早的调用何时过期
        now = time.time()
        earliest_call = min(self.calls)
        return self.time_window - (now - earliest_call)
    
    async def wait_if_needed(self):
        """如果需要则等待"""
        wait_time = self.wait_time()
        if wait_time > 0:
            import asyncio
            await asyncio.sleep(wait_time)