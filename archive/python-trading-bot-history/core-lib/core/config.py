"""
配置管理模块 - 单一真相源

设计哲学：
"配置应该是活的，能够适应环境变化，而不是死板的常量。
真正的智慧在于知道何时坚持，何时调整。"
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class TelegramConfig:
    """Telegram配置"""
    api_id: str
    api_hash: str
    phone_number: str
    group_ids: list
    channel_id: int


@dataclass
class ExchangeConfig:
    """交易所配置"""
    api_key: str
    secret: str
    password: str
    sandbox_mode: bool = True
    enable_rate_limit: bool = True
    default_type: str = 'swap'


@dataclass
class TradingConfig:
    """交易配置"""
    symbol: str = 'BTC-USDT-SWAP'
    default_leverage: int = 20
    max_retries: int = 5
    retry_delay: int = 2
    
    # 反向跟单配置
    reverse_trading_enabled: bool = True
    simple_bot_enabled: bool = True
    turtle_bot_enabled: bool = True


@dataclass
class RiskConfig:
    """风控配置"""
    max_position_size: float = 1000.0
    max_daily_loss: float = 0.1  # 10%
    max_drawdown: float = 0.2    # 20%
    position_timeout_hours: int = 4
    emergency_stop_loss: float = 0.15  # 15%


@dataclass
class MonitoringConfig:
    """监控配置"""
    check_interval: int = 2  # 秒
    alert_thresholds: Dict[str, float] = None
    performance_window: int = 24  # 小时
    
    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                'high_loss': 0.05,
                'position_timeout': 3600,
                'api_error_rate': 0.1
            }


class Config:
    """
    配置管理器 - 系统的智慧中枢
    
    设计原则：
    1. 单一真相源：所有配置都在这里
    2. 环境感知：根据环境自动调整
    3. 热更新：支持运行时配置更新
    4. 类型安全：强类型配置，避免错误
    """
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self._config_data: Dict[str, Any] = {}
        self._load_config()
        
        # 初始化各模块配置
        self.telegram = self._create_telegram_config()
        self.exchange = self._create_exchange_config()
        self.trading = self._create_trading_config()
        self.risk = self._create_risk_config()
        self.monitoring = self._create_monitoring_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config_data = json.load(f)
            else:
                # 创建默认配置
                self._create_default_config()
                self._save_config()
        except Exception as e:
            raise ConfigException(f"加载配置文件失败: {e}")
    
    def _create_default_config(self) -> None:
        """创建默认配置"""
        self._config_data = {
            "telegram": {
                "api_id": os.getenv("TELEGRAM_API_ID", ""),
                "api_hash": os.getenv("TELEGRAM_API_HASH", ""),
                "phone_number": os.getenv("TELEGRAM_PHONE", ""),
                "group_ids": [-1001911467666],
                "channel_id": -1002356209964
            },
            "exchange": {
                "api_key": os.getenv("OKX_API_KEY", ""),
                "secret": os.getenv("OKX_SECRET", ""),
                "password": os.getenv("OKX_PASSWORD", ""),
                "sandbox_mode": True,
                "enable_rate_limit": True,
                "default_type": "swap"
            },
            "trading": {
                "symbol": "BTC-USDT-SWAP",
                "default_leverage": 20,
                "max_retries": 5,
                "retry_delay": 2,
                "reverse_trading_enabled": True,
                "simple_bot_enabled": True,
                "turtle_bot_enabled": True
            },
            "risk": {
                "max_position_size": 1000.0,
                "max_daily_loss": 0.1,
                "max_drawdown": 0.2,
                "position_timeout_hours": 4,
                "emergency_stop_loss": 0.15
            },
            "monitoring": {
                "check_interval": 2,
                "alert_thresholds": {
                    "high_loss": 0.05,
                    "position_timeout": 3600,
                    "api_error_rate": 0.1
                },
                "performance_window": 24
            }
        }
    
    def _save_config(self) -> None:
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise ConfigException(f"保存配置文件失败: {e}")
    
    def _create_telegram_config(self) -> TelegramConfig:
        """创建Telegram配置对象"""
        data = self._config_data.get("telegram", {})
        return TelegramConfig(**data)
    
    def _create_exchange_config(self) -> ExchangeConfig:
        """创建交易所配置对象"""
        data = self._config_data.get("exchange", {})
        return ExchangeConfig(**data)
    
    def _create_trading_config(self) -> TradingConfig:
        """创建交易配置对象"""
        data = self._config_data.get("trading", {})
        return TradingConfig(**data)
    
    def _create_risk_config(self) -> RiskConfig:
        """创建风控配置对象"""
        data = self._config_data.get("risk", {})
        return RiskConfig(**data)
    
    def _create_monitoring_config(self) -> MonitoringConfig:
        """创建监控配置对象"""
        data = self._config_data.get("monitoring", {})
        return MonitoringConfig(**data)
    
    def update_config(self, section: str, key: str, value: Any) -> None:
        """
        更新配置项
        
        Args:
            section: 配置段名
            key: 配置键
            value: 配置值
        """
        if section not in self._config_data:
            self._config_data[section] = {}
        
        self._config_data[section][key] = value
        self._save_config()
        
        # 重新加载对应的配置对象
        self._reload_section_config(section)
    
    def _reload_section_config(self, section: str) -> None:
        """重新加载指定段的配置"""
        if section == "telegram":
            self.telegram = self._create_telegram_config()
        elif section == "exchange":
            self.exchange = self._create_exchange_config()
        elif section == "trading":
            self.trading = self._create_trading_config()
        elif section == "risk":
            self.risk = self._create_risk_config()
        elif section == "monitoring":
            self.monitoring = self._create_monitoring_config()
    
    def get_config(self, section: str, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            section: 配置段名
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self._config_data.get(section, {}).get(key, default)
    
    def validate_config(self) -> bool:
        """
        验证配置的完整性和有效性
        
        Returns:
            是否有效
        """
        required_fields = {
            "telegram": ["api_id", "api_hash", "phone_number"],
            "exchange": ["api_key", "secret", "password"]
        }
        
        for section, fields in required_fields.items():
            section_data = self._config_data.get(section, {})
            for field in fields:
                if not section_data.get(field):
                    raise ConfigException(f"缺少必要配置: {section}.{field}")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "telegram": asdict(self.telegram),
            "exchange": asdict(self.exchange),
            "trading": asdict(self.trading),
            "risk": asdict(self.risk),
            "monitoring": asdict(self.monitoring)
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Config(file={self.config_file})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"Config(file={self.config_file}, sections={list(self._config_data.keys())})"


class ConfigException(Exception):
    """配置异常"""
    pass


# 全局配置实例
_global_config: Optional[Config] = None


def get_config() -> Config:
    """
    获取全局配置实例
    
    Returns:
        全局配置对象
    """
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


def init_config(config_file: str = "config.json") -> Config:
    """
    初始化全局配置
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        配置对象
    """
    global _global_config
    _global_config = Config(config_file)
    return _global_config