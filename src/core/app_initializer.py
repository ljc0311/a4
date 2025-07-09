#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步应用初始化器
使用QThread在后台线程中安全地运行asyncio事件循环和初始化任务，避免阻塞UI主线程。
"""

import asyncio
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool

from src.utils.logger import logger
from src.core.service_manager import ServiceManager

class AsyncInitializer(QObject):
    """
    在单独的线程中运行异步初始化任务。
    """
    # 信号定义
    initialization_started = pyqtSignal()
    initialization_finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, service_manager: ServiceManager):
        super().__init__()
        self.service_manager = service_manager

    def run_initialization(self):
        """
        启动初始化过程。
        """
        self.initialization_started.emit()
        
        # 使用QThreadPool来管理后台任务
        runnable = InitializationRunnable(self.service_manager)
        # 连接runnable的完成信号到我们自己的完成槽
        runnable.signals.finished.connect(self.on_finished)
        QThreadPool.globalInstance().start(runnable)
        logger.info("已将异步初始化任务提交到全局线程池。")

    def on_finished(self, success, message):
        """
        当后台任务完成时由信号触发。
        这个方法确保信号被正确地从这个对象发出。
        """
        self.initialization_finished.emit(success, message)

class InitializationRunnable(QRunnable):
    """
    一个QRunnable任务，用于执行异步初始化。
    """
    def __init__(self, service_manager: ServiceManager):
        super().__init__()
        self.service_manager = service_manager
        self.signals = self._Signals()

    class _Signals(QObject):
        finished = pyqtSignal(bool, str)

    def run(self):
        """
        在线程池的线程中执行。
        """
        try:
            logger.info("后台线程：开始执行异步初始化...")
            # 创建并设置此线程的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行异步初始化方法
            loop.run_until_complete(self.service_manager.initialize())
            
            # 运行服务检查
            status = loop.run_until_complete(self.service_manager.check_all_services())
            
            loop.close()
            
            logger.info(f"后台线程：异步初始化完成。服务状态: {status}")
            self.signals.finished.emit(True, "所有服务已成功初始化。")

        except Exception as e:
            logger.error(f"后台线程：异步初始化过程中发生严重错误: {e}", exc_info=True)
            self.signals.finished.emit(False, f"初始化失败: {e}")
