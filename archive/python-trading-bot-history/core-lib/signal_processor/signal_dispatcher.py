"""
信号分发器 - 智慧的指挥中心

设计哲学：
"正确的信号要传递给正确的策略，在正确的时间做出正确的决策。
分发不仅是传递，更是智慧的协调和资源的优化。"
"""

import asyncio
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from core.logger import get_logger
from core.exceptions import SignalException
from .signal_parser import ParsedSignal, SignalType, SignalAction
from .signal_validator import ValidationResult


class DispatchMode(Enum):
    """分发模式"""
    PARALLEL = "PARALLEL"      # 并行分发：同时发送给所有订阅者
    SEQUENTIAL = "SEQUENTIAL"  # 顺序分发：按优先级顺序发送
    SELECTIVE = "SELECTIVE"    # 选择分发：根据策略选择最佳处理器


@dataclass
class SubscriberInfo:
    """订阅者信息"""
    name: str
    handler: Callable
    priority: int = 0
    filter_func: Optional[Callable] = None
    is_active: bool = True
    max_concurrent: int = 1


@dataclass
class DispatchResult:
    """分发结果"""
    signal_id: str
    total_subscribers: int
    successful_dispatches: int
    failed_dispatches: int
    dispatch_time: float
    results: Dict[str, Any]


class SignalDispatcher:
    """
    信号分发器 - 系统的智慧指挥中心
    
    设计原则：
    1. 智能分发：根据信号类型选择合适的处理器
    2. 负载均衡：避免单个策略过载
    3. 容错处理：单个处理器失败不影响其他
    4. 性能监控：跟踪分发效率和成功率
    """
    
    def __init__(self, mode: DispatchMode = DispatchMode.PARALLEL):
        self.logger = get_logger("SignalDispatcher")
        self.mode = mode
        
        # 订阅者管理
        self.subscribers: Dict[str, SubscriberInfo] = {}
        self.active_tasks: Dict[str, List[asyncio.Task]] = {}
        
        # 分发统计
        self.dispatch_stats = {
            'total_dispatched': 0,
            'successful_dispatches': 0,
            'failed_dispatches': 0,
            'avg_dispatch_time': 0.0,
            'subscriber_performance': {}
        }
        
        # 信号队列（用于缓冲和重试）
        self.signal_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.is_processing = False
    
    def subscribe(
        self,
        name: str,
        handler: Callable,
        priority: int = 0,
        filter_func: Optional[Callable] = None,
        max_concurrent: int = 1
    ):
        """
        订阅信号
        
        Args:
            name: 订阅者名称
            handler: 处理函数，接收(ParsedSignal, ValidationResult)参数
            priority: 优先级（数字越大优先级越高）
            filter_func: 过滤函数，用于筛选感兴趣的信号
            max_concurrent: 最大并发处理数
        """
        subscriber = SubscriberInfo(
            name=name,
            handler=handler,
            priority=priority,
            filter_func=filter_func,
            max_concurrent=max_concurrent
        )
        
        self.subscribers[name] = subscriber
        self.active_tasks[name] = []
        self.dispatch_stats['subscriber_performance'][name] = {
            'total_received': 0,
            'successful_processed': 0,
            'failed_processed': 0,
            'avg_processing_time': 0.0,
            'last_processed': None
        }
        
        self.logger.info(f"新订阅者已注册: {name} (优先级: {priority})")
    
    def unsubscribe(self, name: str):
        """取消订阅"""
        if name in self.subscribers:
            # 取消所有活跃任务
            if name in self.active_tasks:
                for task in self.active_tasks[name]:
                    if not task.done():
                        task.cancel()
                del self.active_tasks[name]
            
            del self.subscribers[name]
            
            if name in self.dispatch_stats['subscriber_performance']:
                del self.dispatch_stats['subscriber_performance'][name]
            
            self.logger.info(f"订阅者已移除: {name}")
    
    def set_subscriber_active(self, name: str, active: bool):
        """设置订阅者激活状态"""
        if name in self.subscribers:
            self.subscribers[name].is_active = active
            self.logger.info(f"订阅者状态更新: {name} -> {'激活' if active else '停用'}")
    
    async def dispatch(self, signal: ParsedSignal, validation_result: ValidationResult) -> DispatchResult:
        """
        分发信号
        
        Args:
            signal: 解析后的信号
            validation_result: 验证结果
            
        Returns:
            分发结果
        """
        start_time = datetime.utcnow()
        signal_id = f"{signal.timestamp.isoformat()}_{hash(signal.raw_message)}"
        
        self.dispatch_stats['total_dispatched'] += 1
        
        # 获取符合条件的订阅者
        eligible_subscribers = self._get_eligible_subscribers(signal, validation_result)
        
        if not eligible_subscribers:
            self.logger.warning(f"没有符合条件的订阅者处理信号: {signal.raw_message}")
            return DispatchResult(
                signal_id=signal_id,
                total_subscribers=0,
                successful_dispatches=0,
                failed_dispatches=0,
                dispatch_time=0.0,
                results={}
            )
        
        # 根据模式执行分发
        if self.mode == DispatchMode.PARALLEL:
            results = await self._dispatch_parallel(signal, validation_result, eligible_subscribers)
        elif self.mode == DispatchMode.SEQUENTIAL:
            results = await self._dispatch_sequential(signal, validation_result, eligible_subscribers)
        else:  # SELECTIVE
            results = await self._dispatch_selective(signal, validation_result, eligible_subscribers)
        
        # 计算分发结果
        successful = sum(1 for r in results.values() if r.get('success', False))
        failed = len(results) - successful
        
        end_time = datetime.utcnow()
        dispatch_time = (end_time - start_time).total_seconds()
        
        # 更新统计信息
        self.dispatch_stats['successful_dispatches'] += successful
        self.dispatch_stats['failed_dispatches'] += failed
        self._update_avg_dispatch_time(dispatch_time)
        
        dispatch_result = DispatchResult(
            signal_id=signal_id,
            total_subscribers=len(eligible_subscribers),
            successful_dispatches=successful,
            failed_dispatches=failed,
            dispatch_time=dispatch_time,
            results=results
        )
        
        # 记录分发结果
        self._log_dispatch_result(signal, dispatch_result)
        
        return dispatch_result
    
    def _get_eligible_subscribers(self, signal: ParsedSignal, validation_result: ValidationResult) -> List[SubscriberInfo]:
        """获取符合条件的订阅者"""
        eligible = []
        
        for subscriber in self.subscribers.values():
            # 检查是否激活
            if not subscriber.is_active:
                continue
            
            # 检查过滤条件
            if subscriber.filter_func:
                try:
                    if not subscriber.filter_func(signal, validation_result):
                        continue
                except Exception as e:
                    self.logger.exception(f"订阅者过滤函数异常: {subscriber.name}")
                    continue
            
            # 检查并发限制
            active_count = len([task for task in self.active_tasks[subscriber.name] if not task.done()])
            if active_count >= subscriber.max_concurrent:
                self.logger.warning(f"订阅者 {subscriber.name} 已达到最大并发限制")
                continue
            
            eligible.append(subscriber)
        
        # 按优先级排序
        eligible.sort(key=lambda s: s.priority, reverse=True)
        
        return eligible
    
    async def _dispatch_parallel(self, signal: ParsedSignal, validation_result: ValidationResult, subscribers: List[SubscriberInfo]) -> Dict[str, Any]:
        """并行分发"""
        tasks = []
        
        for subscriber in subscribers:
            task = asyncio.create_task(
                self._invoke_subscriber(subscriber, signal, validation_result)
            )
            tasks.append((subscriber.name, task))
            self.active_tasks[subscriber.name].append(task)
        
        # 等待所有任务完成
        results = {}
        for name, task in tasks:
            try:
                result = await task
                results[name] = result
            except Exception as e:
                results[name] = {'success': False, 'error': str(e)}
            finally:
                # 清理完成的任务
                if task in self.active_tasks[name]:
                    self.active_tasks[name].remove(task)
        
        return results
    
    async def _dispatch_sequential(self, signal: ParsedSignal, validation_result: ValidationResult, subscribers: List[SubscriberInfo]) -> Dict[str, Any]:
        """顺序分发"""
        results = {}
        
        for subscriber in subscribers:
            try:
                task = asyncio.create_task(
                    self._invoke_subscriber(subscriber, signal, validation_result)
                )
                self.active_tasks[subscriber.name].append(task)
                
                result = await task
                results[subscriber.name] = result
                
                # 如果处理失败，考虑是否继续
                if not result.get('success', False):
                    self.logger.warning(f"订阅者 {subscriber.name} 处理失败，继续下一个")
                
            except Exception as e:
                results[subscriber.name] = {'success': False, 'error': str(e)}
            finally:
                # 清理任务
                if subscriber.name in self.active_tasks and task in self.active_tasks[subscriber.name]:
                    self.active_tasks[subscriber.name].remove(task)
        
        return results
    
    async def _dispatch_selective(self, signal: ParsedSignal, validation_result: ValidationResult, subscribers: List[SubscriberInfo]) -> Dict[str, Any]:
        """选择性分发"""
        # 根据信号类型和特征选择最佳处理器
        selected_subscribers = self._select_best_subscribers(signal, validation_result, subscribers)
        
        # 使用并行模式处理选中的订阅者
        return await self._dispatch_parallel(signal, validation_result, selected_subscribers)
    
    def _select_best_subscribers(self, signal: ParsedSignal, validation_result: ValidationResult, subscribers: List[SubscriberInfo]) -> List[SubscriberInfo]:
        """选择最佳订阅者"""
        # 根据信号特征选择处理器
        selected = []
        
        # 针对不同类型的信号选择不同的策略
        if signal.signal_type == SignalType.CONTROL:
            # 控制信号：选择系统管理相关的处理器
            selected = [s for s in subscribers if 'control' in s.name.lower() or 'system' in s.name.lower()]
        
        elif signal.is_reverse_trigger():
            # 反向信号触发：选择反向策略处理器
            selected = [s for s in subscribers if 'reverse' in s.name.lower()]
        
        elif signal.is_forward_trigger():
            # 正向信号触发：选择正向策略处理器
            selected = [s for s in subscribers if 'forward' in s.name.lower() or 'main' in s.name.lower()]
        
        # 如果没有特定的处理器，使用所有可用的
        if not selected:
            selected = subscribers
        
        # 限制并发数量
        max_concurrent_subscribers = 3
        return selected[:max_concurrent_subscribers]
    
    async def _invoke_subscriber(self, subscriber: SubscriberInfo, signal: ParsedSignal, validation_result: ValidationResult) -> Dict[str, Any]:
        """调用订阅者处理函数"""
        start_time = datetime.utcnow()
        
        try:
            # 更新统计
            stats = self.dispatch_stats['subscriber_performance'][subscriber.name]
            stats['total_received'] += 1
            
            # 调用处理函数
            if asyncio.iscoroutinefunction(subscriber.handler):
                result = await subscriber.handler(signal, validation_result)
            else:
                result = subscriber.handler(signal, validation_result)
            
            # 计算处理时间
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 更新成功统计
            stats['successful_processed'] += 1
            stats['last_processed'] = datetime.utcnow().isoformat()
            self._update_subscriber_avg_time(subscriber.name, processing_time)
            
            return {
                'success': True,
                'result': result,
                'processing_time': processing_time
            }
            
        except Exception as e:
            # 计算处理时间
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 更新失败统计
            stats = self.dispatch_stats['subscriber_performance'][subscriber.name]
            stats['failed_processed'] += 1
            
            self.logger.exception(f"订阅者处理异常: {subscriber.name}")
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': processing_time
            }
    
    def _update_avg_dispatch_time(self, dispatch_time: float):
        """更新平均分发时间"""
        current_avg = self.dispatch_stats['avg_dispatch_time']
        total_count = self.dispatch_stats['total_dispatched']
        
        # 计算移动平均
        self.dispatch_stats['avg_dispatch_time'] = (current_avg * (total_count - 1) + dispatch_time) / total_count
    
    def _update_subscriber_avg_time(self, subscriber_name: str, processing_time: float):
        """更新订阅者平均处理时间"""
        stats = self.dispatch_stats['subscriber_performance'][subscriber_name]
        current_avg = stats['avg_processing_time']
        total_count = stats['successful_processed']
        
        if total_count > 0:
            stats['avg_processing_time'] = (current_avg * (total_count - 1) + processing_time) / total_count
        else:
            stats['avg_processing_time'] = processing_time
    
    def _log_dispatch_result(self, signal: ParsedSignal, result: DispatchResult):
        """记录分发结果"""
        if result.failed_dispatches > 0:
            self.logger.warning(
                f"信号分发完成，部分失败: {signal.raw_message}",
                signal_data={
                    'signal': signal.to_dict(),
                    'dispatch_result': {
                        'total_subscribers': result.total_subscribers,
                        'successful': result.successful_dispatches,
                        'failed': result.failed_dispatches,
                        'dispatch_time': result.dispatch_time
                    }
                }
            )
        else:
            self.logger.info(
                f"信号分发成功: {signal.action.value} {signal.quantity} {signal.symbol}",
                signal_data={
                    'signal': signal.to_dict(),
                    'dispatch_result': {
                        'subscribers': result.total_subscribers,
                        'dispatch_time': result.dispatch_time
                    }
                }
            )
    
    async def start_queue_processing(self):
        """启动队列处理"""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.logger.info("信号分发队列处理已启动")
        
        while self.is_processing:
            try:
                # 从队列获取信号
                signal_data = await asyncio.wait_for(self.signal_queue.get(), timeout=1.0)
                signal, validation_result = signal_data
                
                # 分发信号
                await self.dispatch(signal, validation_result)
                
                # 标记任务完成
                self.signal_queue.task_done()
                
            except asyncio.TimeoutError:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                self.logger.exception(f"队列处理异常: {str(e)}")
    
    async def stop_queue_processing(self):
        """停止队列处理"""
        self.is_processing = False
        
        # 等待队列中的任务完成
        await self.signal_queue.join()
        
        # 取消所有活跃任务
        for tasks in self.active_tasks.values():
            for task in tasks:
                if not task.done():
                    task.cancel()
        
        self.logger.info("信号分发队列处理已停止")
    
    async def enqueue_signal(self, signal: ParsedSignal, validation_result: ValidationResult):
        """将信号加入队列"""
        try:
            await self.signal_queue.put((signal, validation_result))
        except asyncio.QueueFull:
            self.logger.error("信号队列已满，丢弃信号")
            raise SignalException("信号队列已满")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'dispatch_stats': self.dispatch_stats.copy(),
            'queue_size': self.signal_queue.qsize(),
            'is_processing': self.is_processing,
            'active_subscribers': len([s for s in self.subscribers.values() if s.is_active]),
            'total_subscribers': len(self.subscribers),
            'mode': self.mode.value
        }