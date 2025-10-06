"""
海龟反向机器人 - 主程序入口

设计哲学：
"复杂源于智慧，滚仓源于坚持。
分层止盈是对贪婪的控制，仓位递减是对风险的敬畏。"
"""

import asyncio
import signal
import sys
from pathlib import Path

# 添加核心库路径
sys.path.insert(0, str(Path(__file__).parent.parent / "core-lib"))

from reverse_trading_core import (
    Config, get_logger, TelegramListener, SignalDispatcher,
    ExchangeClient, OrderExecutor
)
from reverse_trading_core.core.exceptions import TradingBotException
from strategy.turtle_reverse_strategy import TurtleReverseStrategy


class TurtleReverseBotApp:
    """
    海龟反向机器人应用
    
    核心理念：
    - 海龟滚仓策略
    - 分层止盈机制
    - 仓位递减风控
    - 收益最大化
    """
    
    def __init__(self, config_file: str = "config/config.json"):
        # 初始化配置和日志
        self.config = Config(config_file)
        self.logger = get_logger("TurtleReverseBot")
        
        # 系统状态
        self.is_running = False
        self.startup_time = None
        
        # 核心组件
        self.telegram_listener = None
        self.signal_dispatcher = None
        self.exchange_client = None
        self.order_executor = None
        self.strategy = None
        
        # 后台任务
        self.background_tasks = []
        
        self.logger.info("海龟反向机器人已创建")
    
    async def initialize(self) -> bool:
        """系统初始化"""
        try:
            self.logger.info("开始初始化海龟反向机器人...")
            
            # 验证配置
            if not self.config.validate_config():
                self.logger.error("配置验证失败")
                return False
            
            # 初始化交易所客户端
            self.exchange_client = ExchangeClient()
            if not await self.exchange_client.initialize():
                self.logger.error("交易所客户端初始化失败")
                return False
            
            # 初始化订单执行器（只用市价单）
            self.order_executor = OrderExecutor(self.exchange_client)
            self.order_executor.config.update({
                'market_order_only': True,  # 只使用市价单
                'max_slippage': 0.002,      # 最大2‰滑点
                'fast_execution': True      # 快速执行模式
            })
            
            # 初始化海龟策略
            self.strategy = TurtleReverseStrategy(self.config, self.order_executor)
            
            # 初始化信号处理
            self.telegram_listener = TelegramListener()
            self.signal_dispatcher = SignalDispatcher()
            
            # 连接信号处理链
            self.telegram_listener.add_signal_handler(self.signal_dispatcher.dispatch)
            self.signal_dispatcher.subscribe(
                name="turtle_reverse_strategy",
                handler=self.strategy.process_signal,
                priority=1,
                filter_func=self._turtle_signal_filter
            )
            
            # 设置系统信号处理
            self._setup_system_signals()
            
            self.logger.info("海龟反向机器人初始化完成")
            return True
            
        except Exception as e:
            self.logger.exception(f"初始化失败: {str(e)}")
            return False
    
    def _turtle_signal_filter(self, signal, validation_result) -> bool:
        """海龟策略信号过滤器"""
        # 海龟策略只处理高质量信号
        return (validation_result.is_valid and 
                validation_result.confidence_score >= 0.6 and
                signal.quantity >= 1)
    
    def _setup_system_signals(self):
        """设置系统信号处理"""
        def signal_handler(signum, frame):
            self.logger.info(f"收到系统信号 {signum}，开始优雅关闭...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self) -> bool:
        """启动系统"""
        try:
            if self.is_running:
                self.logger.warning("系统已在运行中")
                return True
            
            # 初始化系统
            if not await self.initialize():
                return False
            
            # 启动策略
            if not self.strategy.start():
                self.logger.error("海龟策略启动失败")
                return False
            
            # 启动订单执行器（快速执行模式）
            order_task = asyncio.create_task(self.order_executor.start_processing())
            self.background_tasks.append(order_task)
            
            # 启动信号分发处理
            dispatch_task = asyncio.create_task(self.signal_dispatcher.start_queue_processing())
            self.background_tasks.append(dispatch_task)
            
            # 启动序列监控任务
            sequence_task = asyncio.create_task(self._monitor_sequences())
            self.background_tasks.append(sequence_task)
            
            # 启动系统监控任务
            monitor_task = asyncio.create_task(self._monitor_system())
            self.background_tasks.append(monitor_task)
            
            self.is_running = True
            self.startup_time = asyncio.get_event_loop().time()
            
            self.logger.info("🐢 海龟反向机器人已启动 - 滚仓分层止盈策略")
            
            # 开始监听信号（这会阻塞主线程）
            await self.telegram_listener.start_listening()
            
            return True
            
        except Exception as e:
            self.logger.exception(f"启动失败: {str(e)}")
            await self.shutdown()
            return False
    
    async def shutdown(self):
        """优雅关闭系统"""
        if not self.is_running:
            return
        
        self.logger.info("开始关闭海龟反向机器人...")
        self.is_running = False
        
        try:
            # 先平掉所有活跃序列（紧急风控）
            if self.strategy:
                await self.strategy.emergency_close_all_sequences("系统关闭")
                self.strategy.stop()
                self.logger.info("海龟策略已停止，所有序列已平仓")
            
            # 停止订单执行器
            if self.order_executor:
                await self.order_executor.stop_processing()
                self.logger.info("订单执行器已停止")
            
            # 停止信号处理
            if self.signal_dispatcher:
                await self.signal_dispatcher.stop_queue_processing()
                self.logger.info("信号分发器已停止")
            
            # 取消后台任务
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
            
            # 等待后台任务完成
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # 停止Telegram监听
            if self.telegram_listener:
                await self.telegram_listener.stop_listening()
                self.logger.info("Telegram监听已停止")
            
            # 计算运行时间
            if self.startup_time:
                uptime = asyncio.get_event_loop().time() - self.startup_time
                self.logger.info(f"系统运行时间: {uptime:.2f}秒")
            
            self.logger.info("🛑 海龟反向机器人已优雅关闭")
            
        except Exception as e:
            self.logger.exception(f"关闭系统时出错: {str(e)}")
    
    async def _monitor_sequences(self):
        """序列监控循环"""
        while self.is_running:
            try:
                if self.strategy:
                    # 检查序列状态和风险
                    sequences_stats = self.strategy.get_sequences_summary()
                    
                    # 如果有风险序列，记录警告
                    if sequences_stats.get('high_risk_sequences', 0) > 0:
                        self.logger.warning(
                            f"发现高风险序列: {sequences_stats['high_risk_sequences']}个",
                            strategy_data=sequences_stats
                        )
                
                await asyncio.sleep(10)  # 每10秒检查一次序列
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"序列监控异常: {str(e)}")
                await asyncio.sleep(30)
    
    async def _monitor_system(self):
        """系统监控循环"""
        while self.is_running:
            try:
                # 每3分钟报告一次状态
                await asyncio.sleep(180)
                
                if self.is_running:
                    stats = await self._get_system_stats()
                    self.logger.info("海龟系统状态报告", strategy_data=stats)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"系统监控异常: {str(e)}")
                await asyncio.sleep(60)
    
    async def _get_system_stats(self) -> dict:
        """获取系统统计信息"""
        stats = {
            'uptime_seconds': asyncio.get_event_loop().time() - self.startup_time if self.startup_time else 0,
            'is_running': self.is_running,
            'bot_type': 'turtle_reverse'
        }
        
        # 海龟策略统计
        if self.strategy:
            strategy_stats = self.strategy.get_status()
            stats['strategy'] = strategy_stats
            
            # 特别关注序列信息
            sequences_info = self.strategy.get_sequences_summary()
            stats['sequences_summary'] = sequences_info
        
        # 订单执行统计
        if self.order_executor:
            stats['order_executor'] = self.order_executor.get_statistics()
        
        # 信号处理统计
        if self.telegram_listener:
            stats['telegram'] = self.telegram_listener.get_statistics()
        
        if self.signal_dispatcher:
            stats['signal_dispatcher'] = self.signal_dispatcher.get_statistics()
        
        # 交易所连接状态
        if self.exchange_client:
            stats['exchange'] = self.exchange_client.get_status()
        
        return stats
    
    async def get_performance_report(self) -> dict:
        """获取详细的性能报告"""
        if not self.strategy:
            return {}
        
        return {
            'strategy_performance': self.strategy.get_performance_metrics(),
            'sequences_detail': self.strategy.get_all_sequences_detail(),
            'risk_metrics': self.strategy.get_risk_metrics(),
            'execution_performance': self.order_executor.get_statistics() if self.order_executor else {}
        }


async def main():
    """主函数"""
    try:
        # 创建海龟反向机器人
        bot = TurtleReverseBotApp()
        
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
    # 打印启动信息
    print("🐢 海龟反向机器人启动中...")
    print("📊 策略: 滚仓分层止盈")
    print("🎯 理念: 复杂源于智慧，收益来自坚持")
    print("⚡ 执行: 市价单快进快出")
    print("=" * 50)
    
    # 运行主程序
    asyncio.run(main())