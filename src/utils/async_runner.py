#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用异步任务执行器
提供一个全局的、持久的后台线程来运行asyncio事件循环，
用于从PyQt UI线程安全地调用异步函数。
"""

import asyncio
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool

from src.utils.logger import logger

class AsyncRunner(QObject):
    """
    管理一个专用的后台线程来执行所有异步任务。
    """
    _instance = None
    _lock = threading.Lock()

    # 信号定义
    # signal_success: (task_id, result)
    # signal_failed: (task_id, exception)
    # signal_finished: (task_id)
    signal_success = pyqtSignal(str, object)
    signal_failed = pyqtSignal(str, object)
    signal_finished = pyqtSignal(str)

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        # 防止重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.loop = None
        self.thread = None
        self._initialized = True
        self.task_counter = 0
        
        self.start_event_loop_thread()

    def start_event_loop_thread(self):
        """启动后台事件循环线程"""
        if self.thread is not None and self.thread.is_alive():
            logger.warning("AsyncRunner后台线程已在运行。")
            return

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()
        logger.info("🚀 通用异步任务执行器后台线程已启动。")

    def run_loop(self):
        """事件循环的入口点"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run(self, coro, task_id=None):
        """
        在后台事件循环中安排一个协程的执行。

        :param coro: 要执行的协程。
        :param task_id: (可选) 任务的唯一标识符。
        :return: 任务ID。
        """
        if not self.loop or not self.thread.is_alive():
            logger.error("事件循环未运行。无法安排任务。")
            raise RuntimeError("AsyncRunner event loop is not running.")

        if task_id is None:
            self.task_counter += 1
            task_id = f"task_{self.task_counter}"

        # 使用asyncio.run_coroutine_threadsafe，因为我们是从不同的线程提交任务
        future = asyncio.run_coroutine_threadsafe(self._wrapper(coro, task_id), self.loop)
        return task_id

    async def _wrapper(self, coro, task_id):
        """包装协程以捕获结果和异常，并发出信号。"""
        try:
            result = await coro
            self.signal_success.emit(task_id, result)
        except Exception as e:
            logger.error(f"异步任务 '{task_id}' 执行失败: {e}", exc_info=True)
            self.signal_failed.emit(task_id, e)
        finally:
            self.signal_finished.emit(task_id)

    def shutdown(self):
        """优雅地关闭后台线程。"""
        if self.loop and self.loop.is_running():
            logger.info("正在关闭通用异步任务执行器...")
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join()
            logger.info("✅ 通用异步任务执行器已关闭。")

# 全局实例
async_runner = AsyncRunner()
