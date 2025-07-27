#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步任务管理器
优化异步任务的执行、监控和资源管理
"""

import asyncio
import time
import weakref
from typing import Dict, List, Optional, Any, Callable, Coroutine
from dataclasses import dataclass
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

from src.utils.logger import logger
from src.utils.memory_optimizer import memory_manager

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    name: str
    status: TaskStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class AsyncTaskManager:
    """异步任务管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.tasks: Dict[str, TaskInfo] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_callbacks: Dict[str, List[Callable]] = {}
        
        # 任务限制
        self.max_concurrent_tasks = 10
        self.max_task_history = 100
        
        # 线程池用于CPU密集型任务
        self.thread_pool = ThreadPoolExecutor(
            max_workers=4, 
            thread_name_prefix="AsyncTaskManager"
        )
        
        # 任务清理定时器
        self.cleanup_interval = 300  # 5分钟
        self.last_cleanup = time.time()
        
        # 注册内存清理回调
        memory_manager.register_cleanup_callback(self.cleanup_completed_tasks)
        
        logger.info("异步任务管理器初始化完成")
    
    def create_task(self, coro: Coroutine, name: str = None, 
                   callback: Callable = None, metadata: Dict = None) -> str:
        """创建异步任务"""
        task_id = f"task_{int(time.time() * 1000)}_{id(coro)}"
        
        if name is None:
            name = f"Task_{len(self.tasks) + 1}"
        
        # 检查并发任务数量
        running_count = len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING])
        if running_count >= self.max_concurrent_tasks:
            logger.warning(f"并发任务数量达到限制({self.max_concurrent_tasks})，任务将排队等待")
        
        # 创建任务信息
        task_info = TaskInfo(
            task_id=task_id,
            name=name,
            status=TaskStatus.PENDING,
            created_at=time.time(),
            metadata=metadata or {}
        )
        
        self.tasks[task_id] = task_info
        
        # 注册回调
        if callback:
            self.register_callback(task_id, callback)
        
        # 创建并启动asyncio任务
        task = asyncio.create_task(self._run_task(task_id, coro))
        self.running_tasks[task_id] = task
        
        logger.info(f"创建任务: {name} (ID: {task_id})")
        return task_id
    
    async def _run_task(self, task_id: str, coro: Coroutine):
        """运行任务的包装器"""
        task_info = self.tasks.get(task_id)
        if not task_info:
            logger.error(f"任务信息不存在: {task_id}")
            return
        
        try:
            # 更新任务状态
            task_info.status = TaskStatus.RUNNING
            task_info.started_at = time.time()
            
            logger.info(f"开始执行任务: {task_info.name}")
            
            # 执行任务
            result = await coro
            
            # 任务完成
            task_info.status = TaskStatus.COMPLETED
            task_info.completed_at = time.time()
            task_info.result = result
            task_info.progress = 1.0
            
            duration = task_info.completed_at - task_info.started_at
            logger.info(f"任务完成: {task_info.name}, 耗时: {duration:.2f}s")
            
            # 执行回调
            await self._execute_callbacks(task_id, result, None)
            
        except asyncio.CancelledError:
            task_info.status = TaskStatus.CANCELLED
            task_info.completed_at = time.time()
            logger.info(f"任务被取消: {task_info.name}")
            
        except Exception as e:
            task_info.status = TaskStatus.FAILED
            task_info.completed_at = time.time()
            task_info.error = str(e)
            
            logger.error(f"任务执行失败: {task_info.name}, 错误: {e}")
            
            # 执行回调
            await self._execute_callbacks(task_id, None, e)
            
        finally:
            # 清理运行中的任务引用
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            
            # 定期清理
            await self._periodic_cleanup()
    
    async def _execute_callbacks(self, task_id: str, result: Any, error: Exception):
        """执行任务回调"""
        callbacks = self.task_callbacks.get(task_id, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task_id, result, error)
                else:
                    callback(task_id, result, error)
            except Exception as e:
                logger.error(f"执行任务回调失败: {e}")
        
        # 清理回调
        if task_id in self.task_callbacks:
            del self.task_callbacks[task_id]
    
    def register_callback(self, task_id: str, callback: Callable):
        """注册任务回调"""
        if task_id not in self.task_callbacks:
            self.task_callbacks[task_id] = []
        
        self.task_callbacks[task_id].append(callback)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()
            logger.info(f"取消任务: {task_id}")
            return True
        
        return False
    
    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def get_running_tasks(self) -> List[TaskInfo]:
        """获取正在运行的任务"""
        return [info for info in self.tasks.values() if info.status == TaskStatus.RUNNING]
    
    def get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        total_tasks = len(self.tasks)
        running_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING])
        completed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])
        failed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED])
        
        return {
            'total_tasks': total_tasks,
            'running_tasks': running_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'success_rate': completed_tasks / total_tasks if total_tasks > 0 else 0
        }
    
    def update_task_progress(self, task_id: str, progress: float, message: str = None):
        """更新任务进度"""
        task_info = self.tasks.get(task_id)
        if task_info:
            task_info.progress = max(0.0, min(1.0, progress))
            if message:
                task_info.metadata['progress_message'] = message
    
    async def run_in_thread(self, func: Callable, *args, **kwargs) -> Any:
        """在线程池中运行CPU密集型任务"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, func, *args, **kwargs)
    
    def cleanup_completed_tasks(self):
        """清理已完成的任务"""
        current_time = time.time()
        
        # 保留最近的任务和正在运行的任务
        tasks_to_keep = {}
        running_tasks = []
        completed_tasks = []
        
        for task_id, task_info in self.tasks.items():
            if task_info.status == TaskStatus.RUNNING:
                running_tasks.append((task_id, task_info))
            elif task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                completed_tasks.append((task_id, task_info))
        
        # 保留所有运行中的任务
        for task_id, task_info in running_tasks:
            tasks_to_keep[task_id] = task_info
        
        # 按完成时间排序，保留最近的任务
        completed_tasks.sort(key=lambda x: x[1].completed_at or 0, reverse=True)
        
        keep_count = min(len(completed_tasks), self.max_task_history - len(running_tasks))
        for task_id, task_info in completed_tasks[:keep_count]:
            tasks_to_keep[task_id] = task_info
        
        # 更新任务字典
        removed_count = len(self.tasks) - len(tasks_to_keep)
        self.tasks = tasks_to_keep
        
        if removed_count > 0:
            logger.info(f"清理了 {removed_count} 个已完成的任务")
    
    async def _periodic_cleanup(self):
        """定期清理"""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            self.cleanup_completed_tasks()
            self.last_cleanup = current_time
    
    async def wait_for_task(self, task_id: str, timeout: float = None) -> Any:
        """等待任务完成"""
        if task_id not in self.running_tasks:
            task_info = self.tasks.get(task_id)
            if task_info:
                if task_info.status == TaskStatus.COMPLETED:
                    return task_info.result
                elif task_info.status == TaskStatus.FAILED:
                    raise Exception(task_info.error)
            raise ValueError(f"任务不存在: {task_id}")
        
        task = self.running_tasks[task_id]
        
        try:
            if timeout:
                result = await asyncio.wait_for(task, timeout=timeout)
            else:
                result = await task
            
            # 从任务信息中获取结果
            task_info = self.tasks.get(task_id)
            if task_info and task_info.result is not None:
                return task_info.result
            
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"等待任务超时: {task_id}")
            raise
    
    def shutdown(self):
        """关闭任务管理器"""
        logger.info("关闭异步任务管理器...")
        
        # 取消所有运行中的任务
        for task_id, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
        
        # 关闭线程池
        try:
            self.thread_pool.shutdown(wait=False)  # 不等待，避免阻塞
        except Exception as e:
            logger.error(f"关闭线程池失败: {e}")
        
        logger.info("异步任务管理器已关闭")

# 全局实例
task_manager = AsyncTaskManager()

def create_task(coro: Coroutine, name: str = None, callback: Callable = None, 
               metadata: Dict = None) -> str:
    """创建异步任务的便捷函数"""
    return task_manager.create_task(coro, name, callback, metadata)

def cancel_task(task_id: str) -> bool:
    """取消任务的便捷函数"""
    return task_manager.cancel_task(task_id)

def get_task_info(task_id: str) -> Optional[TaskInfo]:
    """获取任务信息的便捷函数"""
    return task_manager.get_task_info(task_id)

async def wait_for_task(task_id: str, timeout: float = None) -> Any:
    """等待任务完成的便捷函数"""
    return await task_manager.wait_for_task(task_id, timeout)