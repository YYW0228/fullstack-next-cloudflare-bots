"""
反向跟单机器人主程序 - 智慧与勇气的结合

设计哲学：
"系统的价值不在于单个组件的完美，而在于整体的和谐。
真正的智慧是让复杂的系统以简单的方式运行。"

这是整个系统的入口点，负责：
1. 系统初始化和配置加载
2. 各模块的协调和管理
3. 优雅的启动和关闭
4. 系统状态监控和健康检查
"""

import asyncio
import signal
import sys
from typing import Optional
from datetime import datetime

from core.config import init_config, get_config
from core.logger import get_logger
from core.exceptions import TradingBotException

from signal_processor import (
    TelegramListener, SignalParser, SignalValidator, SignalDispatcher
)
from strategy_engine import (
    SimpleReverseBot, TurtleReverseBot, StrategySelector, PositionManager
)
from trading_engine import ExchangeClient


class ReverseTradingBot:
    """
    反向跟单机器人 - 系统的智慧大脑
    
    这是整个系统的核心协调者，负责管理所有组件的生命周期
    和协调各模块之间的交互。
    """
    
    def __init__(self, config_file: str = "config.json"):
        # 初始化配置和日志
        self.config = init_config(config_file)
        self.logger = get_logger("ReverseTradingBot")
        
        # 系统状态
        self.is_running = False
        self.startup_time = None
        self.shutdown_time = None
        
        # 核心组件
        self.telegram_listener: Optional[TelegramListener] = None
        self.signal_dispatcher: Optional[SignalDispatcher] = None
        self.exchange_client: Optional[ExchangeClient] = None
        self.position_manager: Optional[PositionManager] = None
        
        # 策略实例
        self.simple_bot: Optional[SimpleReverseBot] = None
        self.turtle_bot: Optional[TurtleReverseBot] = None
        self.strategy_selector: Optional[StrategySelector] = None
        
        # 后台任务
        self.background_tasks = []
        
        self.logger.info("反向跟单机器人已创建")
    
    async def initialize(self) -> bool:
        """
        系统初始化
        
        Returns:
            是否初始化成功
        """
        try:
            self.logger.info("开始系统初始化...")
            
            # 验证配置
            if not self.config.validate_config():
                self.logger.error("配置验证失败")
                return False
            
            # 初始化交易所客户端
            self.exchange_client = ExchangeClient()
            if not await self.exchange_client.initialize():
                self.logger.error("交易所客户端初始化失败")
                return False
            
            # 初始化仓位管理器
            self.position_manager = PositionManager()
            
            # 初始化信号处理组件
            self.telegram_listener = TelegramListener()
            self.signal_dispatcher = SignalDispatcher()
            
            # 初始化策略
            await self._initialize_strategies()
            
            # 设置信号处理
            self._setup_signal_handlers()
            
            # 设置系统信号处理
            self._setup_system_signals()
            
            self.logger.info("系统初始化完成")
            return True
            
        except Exception as e:
            self.logger.exception(f"系统初始化失败: {str(e)}")
            return False
    
    async def _initialize_strategies(self):
        """初始化交易策略"""
        try:
            # 创建策略配置
            strategy_config = {
                'exchange_client': self.exchange_client,
                'position_manager': self.position_manager,
                'max_position_size': self.config.risk.max_position_size,
                'risk_limit': self.config.risk.max_daily_loss
            }
            
            # 初始化简单反向策略
            if self.config.trading.simple_bot_enabled:
                self.simple_bot = SimpleReverseBot("SimpleReverse", strategy_config)
                self.signal_dispatcher.subscribe(
                    name="simple_reverse",
                    handler=self.simple_bot.process_signal,
                    priority=1,
                    filter_func=self._simple_bot_filter
                )
            
            # 初始化海龟滚仓策略
            if self.config.trading.turtle_bot_enabled:
                self.turtle_bot = TurtleReverseBot("TurtleReverse", strategy_config)
                self.signal_dispatcher.subscribe(
                    name="turtle_reverse", 
                    handler=self.turtle_bot.process_signal,
                    priority=2,
                    filter_func=self._turtle_bot_filter
                )
            
            # 初始化策略选择器
            strategies = []
            if self.simple_bot:
                strategies.append(self.simple_bot)
            if self.turtle_bot:
                strategies.append(self.turtle_bot)
            
            self.strategy_selector = StrategySelector(strategies)
            
            self.logger.info(f"已初始化 {len(strategies)} 个交易策略")
            
        except Exception as e:
            self.logger.exception(f"策略初始化失败: {str(e)}")
            raise
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        # 将信号分发器作为主要处理器
        self.telegram_listener.add_signal_handler(
            self.signal_dispatcher.dispatch
        )
        
        # 添加原始消息处理器（用于转发消息）
        self.telegram_listener.add_raw_message_handler(
            self._handle_raw_message
        )
    
    def _setup_system_signals(self):
        """设置系统信号处理"""
        def signal_handler(signum, frame):
            self.logger.info(f"收到系统信号 {signum}，开始优雅关闭...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self) -> bool:
        """
        启动系统
        
        Returns:
            是否启动成功
        """
        try:
            if self.is_running:
                self.logger.warning("系统已在运行中")
                return True
            
            # 初始化系统
            if not await self.initialize():
                return False
            
            # 启动策略
            await self._start_strategies()
            
            # 启动后台任务
            await self._start_background_tasks()
            
            # 启动信号分发队列处理
            await self.signal_dispatcher.start_queue_processing()
            
            # 最后启动Telegram监听（这会阻塞）
            self.is_running = True
            self.startup_time = datetime.utcnow()
            
            self.logger.info("🚀 反向跟单机器人已启动")
            
            # 开始监听（这会阻塞主线程）
            await self.telegram_listener.start_listening()
            
            return True
            
        except Exception as e:
            self.logger.exception(f"系统启动失败: {str(e)}")
            await self.shutdown()
            return False
    
    async def _start_strategies(self):
        """启动所有策略"""
        strategies = [self.simple_bot, self.turtle_bot]
        
        for strategy in strategies:
            if strategy and strategy.start():
                self.logger.info(f"策略 {strategy.name} 已启动")
            elif strategy:
                self.logger.error(f"策略 {strategy.name} 启动失败")
    
    async def _start_background_tasks(self):
        """启动后台任务"""
        # 健康检查任务
        health_task = asyncio.create_task(self._health_check_loop())
        self.background_tasks.append(health_task)
        
        # 性能统计任务
        stats_task = asyncio.create_task(self._stats_reporting_loop())
        self.background_tasks.append(stats_task)
        
        # 连接保活任务
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.background_tasks.append(heartbeat_task)
        
        self.logger.info(f"已启动 {len(self.background_tasks)} 个后台任务")
    
    async def shutdown(self):
        """优雅关闭系统"""
        if not self.is_running:
            return
        
        self.logger.info("开始关闭系统...")
        self.is_running = False
        self.shutdown_time = datetime.utcnow()
        
        try:
            # 停止策略
            await self._stop_strategies()
            
            # 取消后台任务
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
            
            # 等待后台任务完成
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # 停止信号处理
            if self.signal_dispatcher:
                await self.signal_dispatcher.stop_queue_processing()
            
            # 停止Telegram监听
            if self.telegram_listener:
                await self.telegram_listener.stop_listening()
            
            # 记录系统运行时间
            if self.startup_time:
                uptime = self.shutdown_time - self.startup_time
                self.logger.info(f"系统运行时间: {uptime}")
            
            self.logger.info("🛑 系统已优雅关闭")
            
        except Exception as e:
            self.logger.exception(f"关闭系统时出错: {str(e)}")
    
    async def _stop_strategies(self):
        """停止所有策略"""
        strategies = [self.simple_bot, self.turtle_bot]
        
        for strategy in strategies:
            if strategy and strategy.stop():
                self.logger.info(f"策略 {strategy.name} 已停止")
    
    async def _handle_raw_message(self, message: str, event):
        """处理原始消息"""
        # 转发消息到指定频道
        try:
            if self.telegram_listener:
                await self.telegram_listener.send_message(message)
        except Exception as e:
            self.logger.exception(f"转发消息失败: {str(e)}")
    
    def _simple_bot_filter(self, signal, validation_result) -> bool:
        """简单策略过滤器"""
        # 简单策略处理所有有效信号
        return validation_result.is_valid
    
    def _turtle_bot_filter(self, signal, validation_result) -> bool:
        """海龟策略过滤器"""
        # 海龟策略只处理高置信度的信号
        return (validation_result.is_valid and 
                validation_result.confidence_score >= 0.7)
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while self.is_running:
            try:
                # 检查各组件健康状态
                health_status = await self._get_system_health()
                
                if not health_status['overall_healthy']:
                    self.logger.warning("系统健康检查发现问题", 
                                      system_data=health_status)
                
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"健康检查异常: {str(e)}")
                await asyncio.sleep(30)
    
    async def _stats_reporting_loop(self):
        """统计报告循环"""
        while self.is_running:
            try:
                # 每小时报告一次统计信息
                stats = await self._get_system_statistics()
                self.logger.info("系统统计报告", system_data=stats)
                
                await asyncio.sleep(3600)  # 每小时报告一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"统计报告异常: {str(e)}")
                await asyncio.sleep(1800)  # 出错时等待30分钟
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.is_running:
            try:
                # 检查交易所连接
                if self.exchange_client:
                    if not await self.exchange_client.check_connection():
                        self.logger.warning("交易所连接异常，尝试重连")
                        await self.exchange_client.reconnect()
                
                await asyncio.sleep(30)  # 每30秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"心跳检查异常: {str(e)}")
                await asyncio.sleep(60)
    
    async def _get_system_health(self) -> dict:
        """获取系统健康状态"""
        health_checks = []
        
        # 检查Telegram连接
        if self.telegram_listener:
            telegram_health = self.telegram_listener.get_health_status()
            health_checks.append(telegram_health['overall_healthy'])
        
        # 检查交易所连接
        if self.exchange_client:
            exchange_health = await self.exchange_client.check_connection()
            health_checks.append(exchange_health)
        
        # 检查策略状态
        if self.simple_bot:
            health_checks.append(self.simple_bot.state.value == "ACTIVE")
        if self.turtle_bot:
            health_checks.append(self.turtle_bot.state.value == "ACTIVE")
        
        overall_healthy = all(health_checks)
        
        return {
            'overall_healthy': overall_healthy,
            'component_health': health_checks,
            'check_time': datetime.utcnow().isoformat()
        }
    
    async def _get_system_statistics(self) -> dict:
        """获取系统统计信息"""
        stats = {
            'uptime_seconds': (datetime.utcnow() - self.startup_time).total_seconds() if self.startup_time else 0,
            'telegram': self.telegram_listener.get_statistics() if self.telegram_listener else {},
            'signal_dispatcher': self.signal_dispatcher.get_statistics() if self.signal_dispatcher else {},
            'exchange': self.exchange_client.get_statistics() if self.exchange_client else {},
            'positions': self.position_manager.get_statistics() if self.position_manager else {},
            'strategies': {}
        }
        
        # 策略统计
        if self.simple_bot:
            stats['strategies']['simple_bot'] = self.simple_bot.get_status()
        if self.turtle_bot:
            stats['strategies']['turtle_bot'] = self.turtle_bot.get_status()
        
        return stats


async def main():
    """主函数"""
    try:
        # 创建机器人实例
        bot = ReverseTradingBot()
        
        # 启动系统
        success = await bot.start()
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n收到中断信号，正在关闭...")
    except Exception as e:
        logger = get_logger("Main")
        logger.exception(f"系统运行异常: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())