"""
信号解析器 - 市场语言的翻译者

设计哲学：
"理解信号的真实意图，不被表面的噪音迷惑。
每个信号都承载着市场的智慧，我们要准确解读。"
"""

import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.logger import get_logger
from core.exceptions import SignalException, InvalidSignalFormatException


class SignalAction(Enum):
    """信号动作枚举"""
    OPEN_LONG = "开多"
    OPEN_SHORT = "开空"
    CLOSE_LONG = "平多"
    CLOSE_SHORT = "平空"


class SignalType(Enum):
    """信号类型枚举"""
    FORWARD = "FORWARD"    # 正向信号
    REVERSE = "REVERSE"    # 反向信号
    CONTROL = "CONTROL"    # 控制信号


@dataclass
class ParsedSignal:
    """
    解析后的信号对象
    
    承载了信号的所有重要信息，是系统决策的基础
    """
    raw_message: str              # 原始消息
    action: SignalAction          # 交易动作
    quantity: float               # 数量
    symbol: str                   # 交易对
    signal_type: SignalType       # 信号类型
    timestamp: datetime           # 时间戳
    confidence: float = 1.0       # 信号置信度 (0-1)
    metadata: Dict[str, Any] = None  # 额外元数据
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # 自动判断信号类型
        if self.signal_type == SignalType.FORWARD:
            self._analyze_signal_characteristics()
    
    def _analyze_signal_characteristics(self):
        """分析信号特征"""
        # 根据数量判断信号强度
        if self.quantity <= 2:
            self.metadata['strength'] = 'weak'
            self.confidence = 0.3
        elif self.quantity == 3:
            self.metadata['strength'] = 'medium'
            self.confidence = 0.7
        elif self.quantity >= 4:
            self.metadata['strength'] = 'strong'
            self.confidence = 0.9
        
        # 判断是否为开仓信号
        self.metadata['is_opening'] = self.action in [SignalAction.OPEN_LONG, SignalAction.OPEN_SHORT]
        self.metadata['is_closing'] = self.action in [SignalAction.CLOSE_LONG, SignalAction.CLOSE_SHORT]
        
        # 判断方向
        self.metadata['direction'] = 'long' if self.action in [SignalAction.OPEN_LONG, SignalAction.CLOSE_SHORT] else 'short'
    
    def is_reverse_trigger(self) -> bool:
        """判断是否为反向信号触发条件"""
        return (
            self.metadata.get('is_opening', False) and 
            self.quantity in [1, 2] and 
            self.signal_type == SignalType.FORWARD
        )
    
    def is_forward_trigger(self) -> bool:
        """判断是否为正向信号触发条件"""
        return (
            self.metadata.get('is_opening', False) and 
            self.quantity >= 3 and 
            self.signal_type == SignalType.FORWARD
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'raw_message': self.raw_message,
            'action': self.action.value,
            'quantity': self.quantity,
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence,
            'metadata': self.metadata
        }


class SignalParser:
    """
    信号解析器 - 市场语言的智慧翻译者
    
    设计原则：
    1. 精确解析：准确提取信号要素
    2. 容错处理：处理各种异常格式
    3. 智能推断：补充缺失信息
    4. 学习能力：从错误中改进
    """
    
    def __init__(self):
        self.logger = get_logger("SignalParser")
        
        # 基础信号模式
        self.signal_patterns = [
            # 标准格式: [开空] 数量:1 市场:BTC-USDT-SWAP
            r'\[(开空|平空|开多|平多)\]\s*数量:(\d+\.?\d*)\s*市场:([\w-]+)',
            
            # 简化格式: 开空 1 BTC
            r'(开空|平空|开多|平多)\s+(\d+\.?\d*)\s+([\w-]*)',
            
            # 口语化格式: 开空1张BTC
            r'(开空|平空|开多|平多)(\d+\.?\d*)张?\s*([\w-]*)',
        ]
        
        # 控制命令模式
        self.control_patterns = [
            r'^(暂停|重启|正常开单|保守开单|运行时间)$',
            r'^(\d+)倍$'  # 倍数设置
        ]
        
        # 统计信息
        self.parse_stats = {
            'total_parsed': 0,
            'successful_parsed': 0,
            'failed_parsed': 0,
            'pattern_usage': {}
        }
    
    def parse(self, raw_message: str) -> Optional[ParsedSignal]:
        """
        解析原始信号消息
        
        Args:
            raw_message: 原始消息文本
            
        Returns:
            解析后的信号对象，解析失败返回None
        """
        self.parse_stats['total_parsed'] += 1
        
        try:
            # 清理消息
            cleaned_message = self._clean_message(raw_message)
            
            # 首先检查是否为控制命令
            control_result = self._parse_control_command(cleaned_message)
            if control_result:
                self.parse_stats['successful_parsed'] += 1
                return control_result
            
            # 解析交易信号
            signal_result = self._parse_trading_signal(cleaned_message)
            if signal_result:
                self.parse_stats['successful_parsed'] += 1
                self.logger.info(
                    f"信号解析成功: {signal_result.action.value} {signal_result.quantity} {signal_result.symbol}",
                    signal_data=signal_result.to_dict()
                )
                return signal_result
            
            # 解析失败
            self.parse_stats['failed_parsed'] += 1
            self.logger.warning(f"信号解析失败: {raw_message}")
            
            raise InvalidSignalFormatException(
                raw_signal=raw_message,
                expected_format="[动作] 数量:数值 市场:交易对"
            )
            
        except Exception as e:
            self.parse_stats['failed_parsed'] += 1
            self.logger.exception(
                f"信号解析异常: {raw_message}",
                error_data={'raw_message': raw_message, 'error': str(e)}
            )
            raise SignalException(f"信号解析异常: {str(e)}")
    
    def _clean_message(self, message: str) -> str:
        """清理消息文本"""
        if not message:
            return ""
        
        # 去除首尾空白
        cleaned = message.strip()
        
        # 去除多余的空格
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # 去除特殊字符（保留必要的符号）
        cleaned = re.sub(r'[^\w\s\[\]:：.-]', '', cleaned)
        
        return cleaned
    
    def _parse_control_command(self, message: str) -> Optional[ParsedSignal]:
        """解析控制命令"""
        for pattern in self.control_patterns:
            match = re.search(pattern, message)
            if match:
                command = match.group(1)
                
                # 记录模式使用统计
                self._update_pattern_stats(pattern)
                
                return ParsedSignal(
                    raw_message=message,
                    action=SignalAction.OPEN_LONG,  # 占位符
                    quantity=0,
                    symbol="CONTROL",
                    signal_type=SignalType.CONTROL,
                    timestamp=datetime.utcnow(),
                    metadata={'command': command}
                )
        
        return None
    
    def _parse_trading_signal(self, message: str) -> Optional[ParsedSignal]:
        """解析交易信号"""
        for pattern in self.signal_patterns:
            match = re.search(pattern, message)
            if match:
                try:
                    # 提取基础信息
                    action_str = match.group(1)
                    quantity_str = match.group(2)
                    symbol_str = match.group(3) if len(match.groups()) >= 3 else "BTC-USDT-SWAP"
                    
                    # 转换动作
                    action = self._parse_action(action_str)
                    
                    # 转换数量
                    quantity = float(quantity_str)
                    
                    # 规范化交易对
                    symbol = self._normalize_symbol(symbol_str)
                    
                    # 记录模式使用统计
                    self._update_pattern_stats(pattern)
                    
                    return ParsedSignal(
                        raw_message=message,
                        action=action,
                        quantity=quantity,
                        symbol=symbol,
                        signal_type=SignalType.FORWARD,
                        timestamp=datetime.utcnow()
                    )
                    
                except (ValueError, AttributeError) as e:
                    self.logger.warning(f"信号字段解析失败: {e}")
                    continue
        
        return None
    
    def _parse_action(self, action_str: str) -> SignalAction:
        """解析交易动作"""
        action_mapping = {
            "开多": SignalAction.OPEN_LONG,
            "开空": SignalAction.OPEN_SHORT,
            "平多": SignalAction.CLOSE_LONG,
            "平空": SignalAction.CLOSE_SHORT
        }
        
        action = action_mapping.get(action_str)
        if action is None:
            raise ValueError(f"未知的交易动作: {action_str}")
        
        return action
    
    def _normalize_symbol(self, symbol_str: str) -> str:
        """规范化交易对符号"""
        if not symbol_str or symbol_str in ["", "BTC", "比特币"]:
            return "BTC-USDT-SWAP"
        
        # 统一格式
        symbol = symbol_str.upper()
        
        # 补充缺失的部分
        if "-" not in symbol:
            if symbol.startswith("BTC"):
                symbol = "BTC-USDT-SWAP"
            elif symbol.startswith("ETH"):
                symbol = "ETH-USDT-SWAP"
            else:
                symbol = f"{symbol}-USDT-SWAP"
        
        # 补充SWAP后缀
        if not symbol.endswith("-SWAP"):
            symbol = f"{symbol}-SWAP"
        
        return symbol
    
    def _update_pattern_stats(self, pattern: str):
        """更新模式使用统计"""
        if pattern not in self.parse_stats['pattern_usage']:
            self.parse_stats['pattern_usage'][pattern] = 0
        self.parse_stats['pattern_usage'][pattern] += 1
    
    def get_parse_statistics(self) -> Dict[str, Any]:
        """获取解析统计信息"""
        total = self.parse_stats['total_parsed']
        success_rate = (self.parse_stats['successful_parsed'] / total * 100) if total > 0 else 0
        
        return {
            'total_parsed': total,
            'successful_parsed': self.parse_stats['successful_parsed'],
            'failed_parsed': self.parse_stats['failed_parsed'],
            'success_rate': f"{success_rate:.2f}%",
            'pattern_usage': self.parse_stats['pattern_usage']
        }
    
    def analyze_signal_sequence(self, signals: List[ParsedSignal]) -> Dict[str, Any]:
        """
        分析信号序列特征
        
        Args:
            signals: 信号序列
            
        Returns:
            序列分析结果
        """
        if not signals:
            return {}
        
        # 按时间排序
        sorted_signals = sorted(signals, key=lambda s: s.timestamp)
        
        # 分析序列模式
        sequence_pattern = []
        for signal in sorted_signals:
            if signal.signal_type == SignalType.FORWARD:
                sequence_pattern.append(signal.quantity)
        
        # 判断序列类型
        is_progressive = self._is_progressive_sequence(sequence_pattern)
        is_reverse_opportunity = self._is_reverse_opportunity(sequence_pattern)
        
        # 计算时间间隔
        time_intervals = []
        for i in range(1, len(sorted_signals)):
            interval = (sorted_signals[i].timestamp - sorted_signals[i-1].timestamp).total_seconds()
            time_intervals.append(interval)
        
        avg_interval = sum(time_intervals) / len(time_intervals) if time_intervals else 0
        
        return {
            'sequence_pattern': sequence_pattern,
            'is_progressive': is_progressive,
            'is_reverse_opportunity': is_reverse_opportunity,
            'signal_count': len(signals),
            'avg_time_interval': avg_interval,
            'total_duration': (sorted_signals[-1].timestamp - sorted_signals[0].timestamp).total_seconds(),
            'last_signal': sorted_signals[-1].to_dict() if sorted_signals else None
        }
    
    def _is_progressive_sequence(self, pattern: List[float]) -> bool:
        """判断是否为递增序列"""
        if len(pattern) < 2:
            return False
        
        for i in range(1, len(pattern)):
            if pattern[i] <= pattern[i-1]:
                return False
        
        return True
    
    def _is_reverse_opportunity(self, pattern: List[float]) -> bool:
        """判断是否为反向交易机会"""
        # 检查是否符合 1->2->3 或 1->3 的模式
        if len(pattern) >= 2:
            # 检查前两个是否为1,2
            if pattern[0] == 1 and (len(pattern) == 1 or pattern[1] in [2, 3]):
                return True
        
        return False