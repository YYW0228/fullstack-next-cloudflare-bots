"""
仓位管理器 - 精确的资产守护者

设计哲学：
"仓位管理是交易的灵魂，风险控制是生存的根本。
每一张合约都承载着我们的信念，每一次调整都体现着我们的智慧。"
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading

from core.logger import get_logger
from core.exceptions import PositionNotFoundException, PositionSizeExceededException


class PositionSide(Enum):
    """仓位方向"""
    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(Enum):
    """仓位状态"""
    OPEN = "OPEN"           # 开仓
    PARTIAL = "PARTIAL"     # 部分平仓
    CLOSED = "CLOSED"       # 已平仓
    LIQUIDATED = "LIQUIDATED"  # 强平


@dataclass
class Position:
    """
    仓位对象 - 承载交易智慧的容器
    """
    id: str                                 # 仓位ID
    symbol: str                            # 交易对
    side: PositionSide                     # 方向
    size: float                            # 数量
    entry_price: float                     # 开仓价格
    current_price: float = 0.0             # 当前价格
    status: PositionStatus = PositionStatus.OPEN
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # 交易记录
    entry_orders: List[Dict[str, Any]] = field(default_factory=list)
    exit_orders: List[Dict[str, Any]] = field(default_factory=list)
    
    # 策略信息
    strategy_name: str = ""
    signal_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 风控信息
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    max_loss: Optional[float] = None
    
    def calculate_pnl(self) -> float:
        """计算未实现盈亏"""
        if self.current_price <= 0:
            return 0.0
        
        if self.side == PositionSide.LONG:
            return (self.current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - self.current_price) * self.size
    
    def calculate_pnl_percentage(self) -> float:
        """计算盈亏百分比"""
        if self.entry_price <= 0:
            return 0.0
        
        pnl = self.calculate_pnl()
        return (pnl / (self.entry_price * self.size)) * 100
    
    def calculate_weighted_avg_price(self) -> float:
        """计算加权平均价格"""
        if not self.entry_orders:
            return self.entry_price
        
        total_value = 0.0
        total_quantity = 0.0
        
        for order in self.entry_orders:
            price = order.get('price', 0.0)
            quantity = order.get('quantity', 0.0)
            total_value += price * quantity
            total_quantity += quantity
        
        return total_value / total_quantity if total_quantity > 0 else self.entry_price
    
    def update_price(self, new_price: float):
        """更新当前价格"""
        self.current_price = new_price
        self.updated_at = datetime.utcnow()
    
    def add_entry_order(self, order: Dict[str, Any]):
        """添加开仓订单"""
        self.entry_orders.append({
            **order,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.updated_at = datetime.utcnow()
        
        # 重新计算平均价格
        self.entry_price = self.calculate_weighted_avg_price()
    
    def add_exit_order(self, order: Dict[str, Any]):
        """添加平仓订单"""
        self.exit_orders.append({
            **order,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.updated_at = datetime.utcnow()
        
        # 更新仓位大小
        exit_quantity = order.get('quantity', 0.0)
        self.size = max(0.0, self.size - exit_quantity)
        
        # 更新状态
        if self.size <= 0:
            self.status = PositionStatus.CLOSED
        elif len(self.exit_orders) > 0:
            self.status = PositionStatus.PARTIAL
    
    def check_stop_loss(self) -> bool:
        """检查止损"""
        if not self.stop_loss:
            return False
        
        if self.side == PositionSide.LONG:
            return self.current_price <= self.stop_loss
        else:
            return self.current_price >= self.stop_loss
    
    def check_take_profit(self) -> bool:
        """检查止盈"""
        if not self.take_profit:
            return False
        
        if self.side == PositionSide.LONG:
            return self.current_price >= self.take_profit
        else:
            return self.current_price <= self.take_profit
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side.value,
            'size': self.size,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'strategy_name': self.strategy_name,
            'signal_id': self.signal_id,
            'pnl': self.calculate_pnl(),
            'pnl_percentage': self.calculate_pnl_percentage(),
            'entry_orders_count': len(self.entry_orders),
            'exit_orders_count': len(self.exit_orders),
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'metadata': self.metadata
        }


class PositionManager:
    """
    仓位管理器 - 智慧的资产守护者
    
    设计原则：
    1. 精确跟踪：准确记录每一个仓位的状态
    2. 风险控制：实时监控风险并采取措施
    3. 性能分析：提供详细的仓位分析
    4. 线程安全：支持多线程环境
    """
    
    def __init__(self):
        self.logger = get_logger("PositionManager")
        
        # 仓位存储
        self.positions: Dict[str, Position] = {}
        self.position_lock = threading.RLock()
        
        # 按策略分组的仓位
        self.strategy_positions: Dict[str, List[str]] = {}
        
        # 按交易对分组的仓位
        self.symbol_positions: Dict[str, List[str]] = {}
        
        # 统计信息
        self.stats = {
            'total_positions': 0,
            'open_positions': 0,
            'closed_positions': 0,
            'total_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'realized_pnl': 0.0
        }
    
    def create_position(
        self,
        symbol: str,
        side: PositionSide,
        size: float,
        entry_price: float,
        strategy_name: str = "",
        signal_id: str = "",
        metadata: Dict[str, Any] = None
    ) -> Position:
        """
        创建新仓位
        
        Args:
            symbol: 交易对
            side: 仓位方向
            size: 仓位大小
            entry_price: 开仓价格
            strategy_name: 策略名称
            signal_id: 信号ID
            metadata: 元数据
            
        Returns:
            创建的仓位对象
        """
        with self.position_lock:
            # 生成仓位ID
            position_id = self._generate_position_id(symbol, side, strategy_name)
            
            # 创建仓位对象
            position = Position(
                id=position_id,
                symbol=symbol,
                side=side,
                size=size,
                entry_price=entry_price,
                current_price=entry_price,
                strategy_name=strategy_name,
                signal_id=signal_id,
                metadata=metadata or {}
            )
            
            # 存储仓位
            self.positions[position_id] = position
            
            # 更新分组索引
            self._update_strategy_index(strategy_name, position_id)
            self._update_symbol_index(symbol, position_id)
            
            # 更新统计
            self._update_stats()
            
            self.logger.info(
                f"创建仓位: {position_id} {side.value} {size} {symbol} @ {entry_price}",
                trade_data=position.to_dict()
            )
            
            return position
    
    def get_position(self, position_id: str) -> Optional[Position]:
        """获取仓位"""
        with self.position_lock:
            return self.positions.get(position_id)
    
    def update_position_price(self, position_id: str, new_price: float) -> bool:
        """更新仓位价格"""
        with self.position_lock:
            position = self.positions.get(position_id)
            if not position:
                return False
            
            position.update_price(new_price)
            self._update_stats()
            return True
    
    def add_to_position(self, position_id: str, quantity: float, price: float, order_data: Dict[str, Any] = None) -> bool:
        """增加仓位"""
        with self.position_lock:
            position = self.positions.get(position_id)
            if not position or position.status == PositionStatus.CLOSED:
                return False
            
            # 添加开仓订单记录
            order = {
                'quantity': quantity,
                'price': price,
                'type': 'add',
                **(order_data or {})
            }
            position.add_entry_order(order)
            
            # 更新仓位大小
            position.size += quantity
            
            self.logger.info(
                f"增仓: {position_id} +{quantity} @ {price}",
                trade_data={'position_id': position_id, 'add_quantity': quantity, 'price': price}
            )
            
            self._update_stats()
            return True
    
    def reduce_position(self, position_id: str, quantity: float, price: float, order_data: Dict[str, Any] = None) -> bool:
        """减少仓位"""
        with self.position_lock:
            position = self.positions.get(position_id)
            if not position or position.status == PositionStatus.CLOSED:
                return False
            
            # 检查减仓数量
            if quantity > position.size:
                quantity = position.size
            
            # 添加平仓订单记录
            order = {
                'quantity': quantity,
                'price': price,
                'type': 'reduce',
                **(order_data or {})
            }
            position.add_exit_order(order)
            
            self.logger.info(
                f"减仓: {position_id} -{quantity} @ {price}",
                trade_data={'position_id': position_id, 'reduce_quantity': quantity, 'price': price}
            )
            
            self._update_stats()
            return True
    
    def close_position(self, position_id: str, close_price: float, order_data: Dict[str, Any] = None) -> bool:
        """平仓"""
        with self.position_lock:
            position = self.positions.get(position_id)
            if not position or position.status == PositionStatus.CLOSED:
                return False
            
            # 添加平仓订单记录
            order = {
                'quantity': position.size,
                'price': close_price,
                'type': 'close',
                **(order_data or {})
            }
            position.add_exit_order(order)
            
            # 计算最终盈亏
            position.update_price(close_price)
            final_pnl = position.calculate_pnl()
            
            self.logger.info(
                f"平仓: {position_id} 数量:{position.size} 价格:{close_price} 盈亏:{final_pnl:.2f}",
                trade_data={
                    'position_id': position_id,
                    'close_quantity': position.size,
                    'close_price': close_price,
                    'final_pnl': final_pnl
                }
            )
            
            self._update_stats()
            return True
    
    def get_positions_by_strategy(self, strategy_name: str) -> List[Position]:
        """获取策略的所有仓位"""
        with self.position_lock:
            position_ids = self.strategy_positions.get(strategy_name, [])
            return [self.positions[pos_id] for pos_id in position_ids if pos_id in self.positions]
    
    def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """获取交易对的所有仓位"""
        with self.position_lock:
            position_ids = self.symbol_positions.get(symbol, [])
            return [self.positions[pos_id] for pos_id in position_ids if pos_id in self.positions]
    
    def get_open_positions(self) -> List[Position]:
        """获取所有开仓仓位"""
        with self.position_lock:
            return [pos for pos in self.positions.values() if pos.status == PositionStatus.OPEN]
    
    def get_positions_summary(self) -> Dict[str, Any]:
        """获取仓位汇总"""
        with self.position_lock:
            open_positions = self.get_open_positions()
            
            # 按方向分组
            long_positions = [pos for pos in open_positions if pos.side == PositionSide.LONG]
            short_positions = [pos for pos in open_positions if pos.side == PositionSide.SHORT]
            
            # 计算总值
            total_long_size = sum(pos.size for pos in long_positions)
            total_short_size = sum(pos.size for pos in short_positions)
            
            # 计算总盈亏
            total_unrealized_pnl = sum(pos.calculate_pnl() for pos in open_positions)
            
            return {
                'total_positions': len(self.positions),
                'open_positions': len(open_positions),
                'long_positions': len(long_positions),
                'short_positions': len(short_positions),
                'total_long_size': total_long_size,
                'total_short_size': total_short_size,
                'net_position': total_long_size - total_short_size,
                'total_unrealized_pnl': total_unrealized_pnl,
                'positions_by_strategy': {
                    strategy: len(positions) for strategy, positions in self.strategy_positions.items()
                },
                'positions_by_symbol': {
                    symbol: len(positions) for symbol, positions in self.symbol_positions.items()
                }
            }
    
    def check_risk_limits(self, symbol: str, side: PositionSide, new_size: float, max_position_size: float) -> bool:
        """检查风险限制"""
        with self.position_lock:
            # 获取当前同方向的仓位
            existing_positions = [
                pos for pos in self.get_positions_by_symbol(symbol)
                if pos.side == side and pos.status == PositionStatus.OPEN
            ]
            
            current_size = sum(pos.size for pos in existing_positions)
            total_size = current_size + new_size
            
            if total_size > max_position_size:
                self.logger.warning(
                    f"仓位超限: {symbol} {side.value} 当前:{current_size} 新增:{new_size} 总计:{total_size} 限制:{max_position_size}"
                )
                return False
            
            return True
    
    def cleanup_closed_positions(self, days_old: int = 7):
        """清理旧的已平仓位"""
        with self.position_lock:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            positions_to_remove = []
            
            for position_id, position in self.positions.items():
                if (position.status == PositionStatus.CLOSED and 
                    position.updated_at < cutoff_date):
                    positions_to_remove.append(position_id)
            
            for position_id in positions_to_remove:
                self._remove_position(position_id)
            
            if positions_to_remove:
                self.logger.info(f"清理了 {len(positions_to_remove)} 个旧仓位")
    
    def _generate_position_id(self, symbol: str, side: PositionSide, strategy_name: str) -> str:
        """生成仓位ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        return f"{strategy_name}_{symbol}_{side.value}_{timestamp}"
    
    def _update_strategy_index(self, strategy_name: str, position_id: str):
        """更新策略索引"""
        if strategy_name not in self.strategy_positions:
            self.strategy_positions[strategy_name] = []
        self.strategy_positions[strategy_name].append(position_id)
    
    def _update_symbol_index(self, symbol: str, position_id: str):
        """更新交易对索引"""
        if symbol not in self.symbol_positions:
            self.symbol_positions[symbol] = []
        self.symbol_positions[symbol].append(position_id)
    
    def _remove_position(self, position_id: str):
        """移除仓位"""
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        
        # 从索引中移除
        if position.strategy_name in self.strategy_positions:
            if position_id in self.strategy_positions[position.strategy_name]:
                self.strategy_positions[position.strategy_name].remove(position_id)
        
        if position.symbol in self.symbol_positions:
            if position_id in self.symbol_positions[position.symbol]:
                self.symbol_positions[position.symbol].remove(position_id)
        
        # 删除仓位
        del self.positions[position_id]
        
        self._update_stats()
    
    def _update_stats(self):
        """更新统计信息"""
        open_positions = [pos for pos in self.positions.values() if pos.status == PositionStatus.OPEN]
        closed_positions = [pos for pos in self.positions.values() if pos.status == PositionStatus.CLOSED]
        
        self.stats.update({
            'total_positions': len(self.positions),
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
            'unrealized_pnl': sum(pos.calculate_pnl() for pos in open_positions),
            'realized_pnl': sum(pos.calculate_pnl() for pos in closed_positions)
        })
        
        self.stats['total_pnl'] = self.stats['unrealized_pnl'] + self.stats['realized_pnl']
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.position_lock:
            return {
                **self.stats,
                'summary': self.get_positions_summary()
            }