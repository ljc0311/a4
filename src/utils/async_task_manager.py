#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步任务管理器
提供高效的异步任务调度和管理功能
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from src.utils.logger import logger


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """任务结果数据类"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[Exception] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def duration(self) -> Optional[float]:
        """获取任务执行时长"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class AsyncTaskManager(QObject):
    """异步任务管理器"""
    
    task_started = pyqtSignal(str)  # task_id
    task_completed = pyqtSignal(str, object)  # task_id, result
    task_failed = pyqtSignal(str, Exception)  # task_id, error
    task_progress = pyqtSignal(str, int)  # task_id, progress_percent
    all_tasks_completed = pyqtSignal()
    
    def __init__(self, max_workers: int = 4):
        super().__init__()
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: Dict[str, TaskResult] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        self._task_counter = 0
        
    def submit_task(self, func: Callable, *args, task_id: str = None, **kwargs) -> str:
        """提交任务"""
        if task_id is None:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}"
            
        # 创建任务结果对象
        task_result = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        self.tasks[task_id] = task_result
        
        # 提交任务到线程池
        future = self.executor.submit(self._execute_task, task_id, func, *args, **kwargs)
        
        logger.info(f"任务已提交: {task_id}")
        return task_id
        
    def _execute_task(self, task_id: str, func: Callable, *args, **kwargs):
        """执行任务"""
        task_result = self.tasks[task_id]
        
        try:
            # 更新任务状态
            task_result.status = TaskStatus.RUNNING
            task_result.start_time = time.time()
            self.task_started.emit(task_id)
            
            # 执行任务
            result = func(*args, **kwargs)
            
            # 任务完成
            task_result.status = TaskStatus.COMPLETED
            task_result.result = result
            task_result.end_time = time.time()
            
            self.task_completed.emit(task_id, result)
            logger.info(f"任务完成: {task_id}, 耗时: {task_result.duration:.2f}s")
            
        except Exception as e:
            # 任务失败
            task_result.status = TaskStatus.FAILED
            task_result.error = e
            task_result.end_time = time.time()
            
            self.task_failed.emit(task_id, e)
            logger.error(f"任务失败: {task_id}, 错误: {e}")
            
        finally:
            # 检查是否所有任务都完成
            self._check_all_tasks_completed()
            
    def _check_all_tasks_completed(self):
        """检查是否所有任务都已完成"""
        pending_tasks = [t for t in self.tasks.values() 
                        if t.status in [TaskStatus.PENDING, TaskStatus.RUNNING]]
        
        if not pending_tasks:
            self.all_tasks_completed.emit()
            
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.tasks:
            task_result = self.tasks[task_id]
            if task_result.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task_result.status = TaskStatus.CANCELLED
                logger.info(f"任务已取消: {task_id}")
                return True
        return False
        
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        if task_id in self.tasks:
            return self.tasks[task_id].status
        return None
        
    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        return self.tasks.get(task_id)
        
    def get_all_tasks(self) -> Dict[str, TaskResult]:
        """获取所有任务"""
        return self.tasks.copy()
        
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        completed_tasks = [task_id for task_id, task in self.tasks.items()
                          if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]]
        
        for task_id in completed_tasks:
            del self.tasks[task_id]
            
        logger.info(f"已清理 {len(completed_tasks)} 个已完成任务")
        
    def shutdown(self, wait: bool = True):
        """关闭任务管理器"""
        logger.info("正在关闭异步任务管理器...")
        self.executor.shutdown(wait=wait)


class BatchTaskProcessor:
    """批量任务处理器"""
    
    def __init__(self, task_manager: AsyncTaskManager):
        self.task_manager = task_manager
        
    def process_batch(self, tasks: List[Dict[str, Any]], 
                     progress_callback: Optional[Callable] = None) -> List[TaskResult]:
        """批量处理任务"""
        task_ids = []
        
        # 提交所有任务
        for i, task_info in enumerate(tasks):
            func = task_info['func']
            args = task_info.get('args', ())
            kwargs = task_info.get('kwargs', {})
            task_id = task_info.get('task_id', f"batch_task_{i}")
            
            submitted_task_id = self.task_manager.submit_task(func, *args, task_id=task_id, **kwargs)
            task_ids.append(submitted_task_id)
            
        # 等待所有任务完成
        results = []
        completed_count = 0
        
        while completed_count < len(task_ids):
            time.sleep(0.1)  # 短暂等待
            
            for task_id in task_ids:
                task_result = self.task_manager.get_task_result(task_id)
                if task_result and task_result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    if task_result not in results:
                        results.append(task_result)
                        completed_count += 1
                        
                        # 调用进度回调
                        if progress_callback:
                            progress = int((completed_count / len(task_ids)) * 100)
                            progress_callback(progress)
                            
        return results


# 全局任务管理器实例
global_task_manager = AsyncTaskManager(max_workers=4)
batch_processor = BatchTaskProcessor(global_task_manager)
