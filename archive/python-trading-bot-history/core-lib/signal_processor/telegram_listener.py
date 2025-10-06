"""
Telegram监听器 - 系统的耳朵

设计哲学：
"倾听是智慧的开始，专注是力量的源泉。
我们要做市场最忠实的听众，捕捉每一个重要的声音。"
"""

import asyncio
from typing import List, Callable, Optional, Dict, Any
from datetime import datetime
from telethon import TelegramClient, events

from core.config import get_config
from core.logger import get_logger
from core.exceptions import NetworkException, ConnectionTimeoutException
from .signal_parser import SignalParser
from .signal_validator import SignalValidator


class TelegramListener:
    """
    Telegram监听器 - 专注而智慧的信号接收者
    
    设计原则：
    1. 专注监听：只关注重要的信号源
    2. 实时响应：最小化信号延迟
    3. 稳定连接：自动重连和错误恢复
    4. 智能过滤：初步过滤无效消息
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger("TelegramListener")
        
        # Telegram客户端
        self.client: Optional[TelegramClient] = None
        
        # 信号处理组件
        self.signal_parser = SignalParser()
        self.signal_validator = SignalValidator()
        
        # 事件处理器列表
        self.signal_handlers: List[Callable] = []
        self.raw_message_handlers: List[Callable] = []
        
        # 运行状态
        self.is_running = False
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # 统计信息
        self.stats = {
            'messages_received': 0,
            'signals_parsed': 0,
            'signals_validated': 0,
            'errors_count': 0,
            'last_message_time': None,
            'connection_uptime': None
        }
    
    async def initialize(self) -> bool:
        """
        初始化Telegram客户端
        
        Returns:
            是否初始化成功
        """
        try:
            telegram_config = self.config.telegram
            
            # 验证配置
            if not all([telegram_config.api_id, telegram_config.api_hash, telegram_config.phone_number]):
                raise NetworkException("Telegram配置不完整")
            
            # 创建客户端
            self.client = TelegramClient(
                'bot_session',
                telegram_config.api_id,
                telegram_config.api_hash
            )
            
            # 连接并验证
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                self.logger.warning("Telegram客户端未授权，需要重新认证")
                return False
            
            self.is_connected = True
            self.stats['connection_uptime'] = datetime.utcnow()
            
            # 设置事件处理器
            self._setup_event_handlers()
            
            self.logger.info("Telegram客户端初始化成功")
            return True
            
        except Exception as e:
            self.logger.exception(f"Telegram客户端初始化失败: {str(e)}")
            self.is_connected = False
            return False
    
    def _setup_event_handlers(self):
        """设置事件处理器"""
        if not self.client:
            return
        
        # 监听指定群组的新消息
        @self.client.on(events.NewMessage(chats=self.config.telegram.group_ids))
        async def message_handler(event):
            await self._handle_new_message(event)
        
        # 监听连接状态变化
        @self.client.on(events.ConnectionUpdate)
        async def connection_handler(event):
            await self._handle_connection_update(event)
    
    async def _handle_new_message(self, event):
        """处理新消息"""
        try:
            self.stats['messages_received'] += 1
            self.stats['last_message_time'] = datetime.utcnow()
            
            # 获取消息内容
            message_text = event.message.text
            if not message_text:
                return
            
            # 记录原始消息
            self.logger.info(f"收到新消息: {message_text}")
            
            # 调用原始消息处理器
            for handler in self.raw_message_handlers:
                try:
                    await handler(message_text, event)
                except Exception as e:
                    self.logger.exception(f"原始消息处理器异常: {str(e)}")
            
            # 解析信号
            try:
                parsed_signal = self.signal_parser.parse(message_text)
                if parsed_signal:
                    self.stats['signals_parsed'] += 1
                    
                    # 验证信号
                    validation_result = self.signal_validator.validate(parsed_signal)
                    
                    if validation_result.is_valid:
                        self.stats['signals_validated'] += 1
                        
                        # 调用信号处理器
                        for handler in self.signal_handlers:
                            try:
                                await handler(parsed_signal, validation_result)
                            except Exception as e:
                                self.logger.exception(f"信号处理器异常: {str(e)}")
                    else:
                        self.logger.warning(
                            f"信号验证失败: {message_text}",
                            signal_data={
                                'validation_errors': validation_result.errors,
                                'validation_warnings': validation_result.warnings
                            }
                        )
                        
            except Exception as e:
                self.stats['errors_count'] += 1
                self.logger.exception(f"信号处理异常: {str(e)}")
                
        except Exception as e:
            self.stats['errors_count'] += 1
            self.logger.exception(f"消息处理异常: {str(e)}")
    
    async def _handle_connection_update(self, event):
        """处理连接状态更新"""
        if hasattr(event, 'connected'):
            if event.connected:
                self.is_connected = True
                self.reconnect_attempts = 0
                self.logger.info("Telegram连接已建立")
            else:
                self.is_connected = False
                self.logger.warning("Telegram连接已断开")
                
                # 尝试重连
                if self.is_running and self.reconnect_attempts < self.max_reconnect_attempts:
                    await self._attempt_reconnect()
    
    async def _attempt_reconnect(self):
        """尝试重连"""
        self.reconnect_attempts += 1
        
        self.logger.info(f"尝试重连 Telegram (第 {self.reconnect_attempts} 次)")
        
        try:
            # 等待一段时间后重连
            await asyncio.sleep(min(self.reconnect_attempts * 2, 30))
            
            if self.client:
                await self.client.connect()
                
                if await self.client.is_user_authorized():
                    self.is_connected = True
                    self.logger.info("Telegram重连成功")
                else:
                    self.logger.error("Telegram重连失败：未授权")
                    
        except Exception as e:
            self.logger.exception(f"Telegram重连异常: {str(e)}")
            
            if self.reconnect_attempts >= self.max_reconnect_attempts:
                self.logger.error("达到最大重连次数，停止重连")
                self.is_running = False
    
    def add_signal_handler(self, handler: Callable):
        """
        添加信号处理器
        
        Args:
            handler: 处理函数，接收(ParsedSignal, ValidationResult)参数
        """
        self.signal_handlers.append(handler)
        self.logger.info(f"已添加信号处理器: {handler.__name__}")
    
    def add_raw_message_handler(self, handler: Callable):
        """
        添加原始消息处理器
        
        Args:
            handler: 处理函数，接收(message_text, event)参数
        """
        self.raw_message_handlers.append(handler)
        self.logger.info(f"已添加原始消息处理器: {handler.__name__}")
    
    def remove_signal_handler(self, handler: Callable):
        """移除信号处理器"""
        if handler in self.signal_handlers:
            self.signal_handlers.remove(handler)
            self.logger.info(f"已移除信号处理器: {handler.__name__}")
    
    def remove_raw_message_handler(self, handler: Callable):
        """移除原始消息处理器"""
        if handler in self.raw_message_handlers:
            self.raw_message_handlers.remove(handler)
            self.logger.info(f"已移除原始消息处理器: {handler.__name__}")
    
    async def start_listening(self):
        """开始监听"""
        if not self.client or not self.is_connected:
            if not await self.initialize():
                raise NetworkException("无法初始化Telegram客户端")
        
        self.is_running = True
        self.logger.info(f"开始监听群组: {self.config.telegram.group_ids}")
        
        try:
            # 运行事件循环
            await self.client.run_until_disconnected()
        except Exception as e:
            self.logger.exception(f"监听过程异常: {str(e)}")
            raise
        finally:
            self.is_running = False
    
    async def stop_listening(self):
        """停止监听"""
        self.is_running = False
        
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
        
        self.logger.info("已停止监听")
    
    async def send_message(self, message: str, channel_id: Optional[int] = None):
        """
        发送消息
        
        Args:
            message: 消息内容
            channel_id: 目标频道ID，默认使用配置中的频道
        """
        if not self.client or not self.is_connected:
            raise NetworkException("Telegram客户端未连接")
        
        target_id = channel_id or self.config.telegram.channel_id
        
        try:
            await self.client.send_message(target_id, message)
            self.logger.info(f"消息发送成功: {message[:50]}...")
        except Exception as e:
            self.logger.exception(f"消息发送失败: {str(e)}")
            raise NetworkException(f"消息发送失败: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        
        # 添加运行时信息
        stats.update({
            'is_running': self.is_running,
            'is_connected': self.is_connected,
            'reconnect_attempts': self.reconnect_attempts,
            'signal_handlers_count': len(self.signal_handlers),
            'raw_handlers_count': len(self.raw_message_handlers)
        })
        
        # 计算连接时长
        if self.stats['connection_uptime']:
            uptime = datetime.utcnow() - self.stats['connection_uptime']
            stats['connection_uptime_seconds'] = uptime.total_seconds()
        
        # 添加解析和验证统计
        stats.update({
            'parser_stats': self.signal_parser.get_parse_statistics(),
            'validator_stats': self.signal_validator.get_validation_statistics()
        })
        
        return stats
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        now = datetime.utcnow()
        
        # 检查连接状态
        connection_healthy = self.is_connected and self.is_running
        
        # 检查最近是否有消息
        last_message_healthy = True
        if self.stats['last_message_time']:
            time_since_last = (now - self.stats['last_message_time']).total_seconds()
            # 如果超过10分钟没有消息，可能有问题
            last_message_healthy = time_since_last < 600
        
        # 检查错误率
        total_messages = self.stats['messages_received']
        error_rate = (self.stats['errors_count'] / total_messages) if total_messages > 0 else 0
        error_rate_healthy = error_rate < 0.1  # 错误率小于10%
        
        overall_healthy = connection_healthy and last_message_healthy and error_rate_healthy
        
        return {
            'overall_healthy': overall_healthy,
            'connection_healthy': connection_healthy,
            'last_message_healthy': last_message_healthy,
            'error_rate_healthy': error_rate_healthy,
            'error_rate': f"{error_rate:.2%}",
            'last_message_ago_seconds': (now - self.stats['last_message_time']).total_seconds() if self.stats['last_message_time'] else None,
            'reconnect_attempts': self.reconnect_attempts,
            'max_reconnect_attempts': self.max_reconnect_attempts
        }


class TelegramListenerManager:
    """Telegram监听器管理器"""
    
    _instance: Optional[TelegramListener] = None
    
    @classmethod
    def get_instance(cls) -> TelegramListener:
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = TelegramListener()
        return cls._instance
    
    @classmethod
    async def start(cls) -> TelegramListener:
        """启动监听器"""
        instance = cls.get_instance()
        
        # 在后台任务中启动监听
        asyncio.create_task(instance.start_listening())
        
        # 等待连接建立
        max_wait = 30  # 最多等待30秒
        wait_time = 0
        while not instance.is_connected and wait_time < max_wait:
            await asyncio.sleep(1)
            wait_time += 1
        
        if not instance.is_connected:
            raise ConnectionTimeoutException(max_wait, "Telegram")
        
        return instance
    
    @classmethod
    async def stop(cls):
        """停止监听器"""
        if cls._instance:
            await cls._instance.stop_listening()
            cls._instance = None