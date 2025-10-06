"""
日志系统模块 - 智慧的记录者

设计哲学：
"日志不仅是记录，更是系统的记忆和学习的基础。
每一条日志都应该承载智慧，帮助系统进化。"
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum
import json


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    WISDOM = "WISDOM"  # 自定义级别：智慧日志


class ColorFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'WISDOM': '\033[94m',     # 蓝色
        'RESET': '\033[0m'        # 重置
    }
    
    def format(self, record):
        # 获取颜色
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # 格式化消息
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record):
        # 创建结构化日志
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'module': record.name,
            'message': record.getMessage(),
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加额外字段
        if hasattr(record, 'trade_data'):
            log_entry['trade_data'] = record.trade_data
        if hasattr(record, 'strategy_data'):
            log_entry['strategy_data'] = record.strategy_data
        if hasattr(record, 'error_data'):
            log_entry['error_data'] = record.error_data
            
        return json.dumps(log_entry, ensure_ascii=False)


class Logger:
    """
    智慧日志器 - 系统的记忆和学习中心
    
    设计原则：
    1. 分层日志：不同级别的日志用于不同目的
    2. 结构化：便于分析和挖掘
    3. 智慧记录：记录决策过程和学习点
    4. 性能友好：异步写入，不阻塞主流程
    """
    
    def __init__(self, name: str = "TradingBot"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
        
        # 添加自定义日志级别
        self._add_custom_levels()
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 控制台处理器（彩色输出）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColorFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 主日志文件（详细信息）
        main_handler = self._create_file_handler(
            'logs/main.log', 
            logging.DEBUG,
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        self.logger.addHandler(main_handler)
        
        # 交易日志文件（交易相关）
        trade_handler = self._create_file_handler(
            'logs/trade.log',
            logging.INFO,
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        # 只记录包含trade_data的日志
        trade_handler.addFilter(lambda record: hasattr(record, 'trade_data'))
        self.logger.addHandler(trade_handler)
        
        # 错误日志文件（错误和异常）
        error_handler = self._create_file_handler(
            'logs/error.log',
            logging.ERROR,
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s\n%(exc_info)s'
        )
        self.logger.addHandler(error_handler)
        
        # 智慧日志文件（学习和决策）
        wisdom_handler = self._create_file_handler(
            'logs/wisdom.log',
            logging.DEBUG,
            '%(asctime)s - %(message)s'
        )
        # 只记录WISDOM级别的日志
        wisdom_handler.addFilter(lambda record: record.levelname == 'WISDOM')
        self.logger.addHandler(wisdom_handler)
        
        # 结构化日志文件（JSON格式）
        structured_handler = self._create_file_handler(
            'logs/structured.jsonl',
            logging.DEBUG,
            None
        )
        structured_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(structured_handler)
    
    def _create_file_handler(self, filename: str, level: int, format_str: Optional[str]):
        """创建文件处理器"""
        # 确保日志目录存在
        log_path = Path(filename)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(filename, encoding='utf-8')
        handler.setLevel(level)
        
        if format_str:
            formatter = logging.Formatter(format_str)
            handler.setFormatter(formatter)
        
        return handler
    
    def _add_custom_levels(self):
        """添加自定义日志级别"""
        # 添加WISDOM级别
        logging.addLevelName(25, 'WISDOM')
        
        def wisdom(self, message, *args, **kwargs):
            if self.isEnabledFor(25):
                self._log(25, message, args, **kwargs)
        
        logging.Logger.wisdom = wisdom
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def wisdom(self, message: str, **kwargs):
        """智慧日志 - 记录学习和决策过程"""
        self._log_with_context(25, message, **kwargs)
    
    def trade(self, message: str, trade_data: Dict[str, Any], **kwargs):
        """交易日志 - 记录交易相关信息"""
        kwargs['trade_data'] = trade_data
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def strategy(self, message: str, strategy_data: Dict[str, Any], **kwargs):
        """策略日志 - 记录策略决策过程"""
        kwargs['strategy_data'] = strategy_data
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def exception(self, message: str, error_data: Optional[Dict[str, Any]] = None, **kwargs):
        """异常日志 - 记录异常和错误详情"""
        if error_data:
            kwargs['error_data'] = error_data
        kwargs['exc_info'] = True
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """带上下文的日志记录"""
        # 创建日志记录
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            __file__,
            0,
            message,
            (),
            None,
            func=None,
            extra=kwargs
        )
        
        # 添加额外属性
        for key, value in kwargs.items():
            setattr(record, key, value)
        
        self.logger.handle(record)
    
    def performance(self, operation: str, duration: float, **kwargs):
        """性能日志 - 记录操作耗时"""
        self.info(
            f"性能统计: {operation} 耗时 {duration:.3f}秒",
            performance_data={
                'operation': operation,
                'duration': duration,
                **kwargs
            }
        )
    
    def decision(self, decision: str, reasoning: str, data: Optional[Dict] = None):
        """决策日志 - 记录重要决策过程"""
        self.wisdom(
            f"决策: {decision} | 理由: {reasoning}",
            decision_data={
                'decision': decision,
                'reasoning': reasoning,
                'data': data or {}
            }
        )
    
    def learn(self, experience: str, lesson: str, data: Optional[Dict] = None):
        """学习日志 - 记录从经验中学到的教训"""
        self.wisdom(
            f"学习: {experience} | 教训: {lesson}",
            learning_data={
                'experience': experience,
                'lesson': lesson,
                'data': data or {}
            }
        )


class LoggerManager:
    """日志管理器 - 管理系统中的所有日志器"""
    
    _loggers: Dict[str, Logger] = {}
    
    @classmethod
    def get_logger(cls, name: str = "TradingBot") -> Logger:
        """
        获取日志器实例
        
        Args:
            name: 日志器名称
            
        Returns:
            日志器实例
        """
        if name not in cls._loggers:
            cls._loggers[name] = Logger(name)
        return cls._loggers[name]
    
    @classmethod
    def set_level(cls, level: str):
        """设置所有日志器的级别"""
        log_level = getattr(logging, level.upper())
        for logger in cls._loggers.values():
            logger.logger.setLevel(log_level)
    
    @classmethod
    def cleanup(cls):
        """清理所有日志器"""
        for logger in cls._loggers.values():
            for handler in logger.logger.handlers:
                handler.close()
        cls._loggers.clear()


# 便捷函数
def get_logger(name: str = "TradingBot") -> Logger:
    """获取日志器"""
    return LoggerManager.get_logger(name)