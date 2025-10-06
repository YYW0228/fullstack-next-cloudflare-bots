"""
验证工具类 - 数据验证的智慧

设计哲学：
"验证是对错误的预防，预防胜过治疗。
严格的输入验证是系统稳定性的基石。"
"""

import re
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal


class ValidationUtils:
    """
    验证工具类 - 提供通用的数据验证功能
    
    功能：
    1. 参数验证
    2. 数据格式验证  
    3. 业务规则验证
    4. API响应验证
    """
    
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """验证交易对格式"""
        if not isinstance(symbol, str):
            return False
        
        # 常见格式: BTC-USDT-SWAP, BTC/USDT, BTCUSDT
        patterns = [
            r'^[A-Z]+[-/][A-Z]+(-SWAP)?$',  # BTC-USDT, BTC-USDT-SWAP
            r'^[A-Z]+[A-Z]+$'               # BTCUSDT
        ]
        
        return any(re.match(pattern, symbol.upper()) for pattern in patterns)
    
    @staticmethod
    def validate_price(price: Union[float, str, Decimal]) -> bool:
        """验证价格"""
        try:
            price_val = float(price)
            return price_val > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_quantity(quantity: Union[float, str, Decimal]) -> bool:
        """验证数量"""
        try:
            qty_val = float(quantity)
            return qty_val > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_percentage(percentage: Union[float, str]) -> bool:
        """验证百分比 (0-100)"""
        try:
            pct_val = float(percentage)
            return 0 <= pct_val <= 100
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_ratio(ratio: Union[float, str]) -> bool:
        """验证比例 (0-1)"""
        try:
            ratio_val = float(ratio)
            return 0 <= ratio_val <= 1
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_api_keys(api_config: Dict[str, Any]) -> bool:
        """验证API配置"""
        required_keys = ['api_key', 'secret']
        
        for key in required_keys:
            if key not in api_config:
                return False
            
            if not isinstance(api_config[key], str):
                return False
                
            if not api_config[key].strip():
                return False
        
        return True
    
    @staticmethod
    def validate_signal_data(signal: Dict[str, Any]) -> bool:
        """验证信号数据"""
        required_fields = ['action', 'symbol', 'quantity']
        
        for field in required_fields:
            if field not in signal:
                return False
        
        # 验证具体字段
        valid_actions = ['开多', '开空', '平多', '平空', 'BUY', 'SELL', 'CLOSE']
        if signal['action'] not in valid_actions:
            return False
        
        if not ValidationUtils.validate_symbol(signal['symbol']):
            return False
        
        if not isinstance(signal['quantity'], (int, float)) or signal['quantity'] <= 0:
            return False
        
        return True
    
    @staticmethod
    def validate_config_section(config: Dict[str, Any], section: str, required_keys: List[str]) -> bool:
        """验证配置文件的特定部分"""
        if section not in config:
            return False
        
        section_config = config[section]
        if not isinstance(section_config, dict):
            return False
        
        for key in required_keys:
            if key not in section_config:
                return False
        
        return True
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """清理字符串输入"""
        if not isinstance(value, str):
            return ""
        
        # 移除危险字符
        sanitized = re.sub(r'[<>"\']', '', value)
        
        # 限制长度
        return sanitized[:max_length]
    
    @staticmethod
    def validate_timeframe(timeframe: str) -> bool:
        """验证时间周期格式"""
        if not isinstance(timeframe, str):
            return False
        
        # 常见格式: 1m, 5m, 15m, 1h, 4h, 1d
        pattern = r'^(\d+)([mhd])$'
        return bool(re.match(pattern, timeframe.lower()))
    
    @staticmethod
    def validate_risk_parameters(risk_config: Dict[str, Any]) -> bool:
        """验证风险参数"""
        required_keys = ['max_daily_loss', 'max_position_size', 'max_drawdown']
        
        if not ValidationUtils.validate_config_section(risk_config, '', required_keys):
            return False
        
        # 验证数值范围
        if not ValidationUtils.validate_ratio(risk_config.get('max_daily_loss', 0)):
            return False
        
        if not ValidationUtils.validate_ratio(risk_config.get('max_drawdown', 0)):
            return False
        
        if not ValidationUtils.validate_quantity(risk_config.get('max_position_size', 0)):
            return False
        
        return True


def validate_symbol(symbol: str) -> bool:
    """便捷函数 - 验证交易对"""
    return ValidationUtils.validate_symbol(symbol)


def validate_price(price: Union[float, str, Decimal]) -> bool:
    """便捷函数 - 验证价格"""
    return ValidationUtils.validate_price(price)


def validate_quantity(quantity: Union[float, str, Decimal]) -> bool:
    """便捷函数 - 验证数量"""
    return ValidationUtils.validate_quantity(quantity)


def validate_signal_data(signal: Dict[str, Any]) -> bool:
    """便捷函数 - 验证信号数据"""
    return ValidationUtils.validate_signal_data(signal)