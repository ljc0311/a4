#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内存优化工具
提供内存监控、清理和优化功能
"""

import gc
import psutil
import threading
import time
from typing import Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from src.utils.logger import logger


class MemoryMonitor(QObject):
    """内存监控器"""
    
    memory_warning = pyqtSignal(float)  # 内存使用率警告
    memory_critical = pyqtSignal(float)  # 内存使用率严重警告
    
    def __init__(self, warning_threshold: float = 0.8, critical_threshold: float = 0.9):
        super().__init__()
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.monitoring = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_memory)
        
    def start_monitoring(self, interval_ms: int = 5000):
        """开始内存监控"""
        self.monitoring = True
        self.timer.start(interval_ms)
        logger.info(f"内存监控已启动，检查间隔: {interval_ms}ms")
        
    def stop_monitoring(self):
        """停止内存监控"""
        self.monitoring = False
        self.timer.stop()
        logger.info("内存监控已停止")
        
    def _check_memory(self):
        """检查内存使用情况"""
        try:
            memory_percent = psutil.virtual_memory().percent / 100.0
            
            if memory_percent >= self.critical_threshold:
                self.memory_critical.emit(memory_percent)
                logger.warning(f"内存使用率严重警告: {memory_percent:.1%}")
                self._auto_cleanup()
            elif memory_percent >= self.warning_threshold:
                self.memory_warning.emit(memory_percent)
                logger.info(f"内存使用率警告: {memory_percent:.1%}")
                
        except Exception as e:
            logger.error(f"内存检查失败: {e}")
            
    def _auto_cleanup(self):
        """自动内存清理"""
        logger.info("执行自动内存清理...")
        gc.collect()
        
    def get_memory_info(self) -> dict:
        """获取详细内存信息"""
        try:
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                'system_total': memory.total,
                'system_available': memory.available,
                'system_percent': memory.percent,
                'process_rss': process_memory.rss,
                'process_vms': process_memory.vms,
                'process_percent': process.memory_percent()
            }
        except Exception as e:
            logger.error(f"获取内存信息失败: {e}")
            return {}


class ImageMemoryManager:
    """图像内存管理器 - 优化版"""
    
    def __init__(self, max_cache_size: int = 100, max_memory_mb: int = 500):
        self.max_cache_size = max_cache_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.image_cache = {}
        self.access_order = []
        self.cache_size_bytes = 0
        self._lock = threading.Lock()
        
    def cache_image(self, key: str, image_data: bytes):
        """缓存图像数据 - 支持内存限制"""
        with self._lock:
            data_size = len(image_data)
            
            # 检查是否超过内存限制
            while (self.cache_size_bytes + data_size > self.max_memory_bytes or 
                   len(self.image_cache) >= self.max_cache_size) and self.image_cache:
                self._evict_oldest()
            
            # 如果key已存在，先移除旧数据
            if key in self.image_cache:
                old_size = len(self.image_cache[key])
                self.cache_size_bytes -= old_size
                self.access_order.remove(key)
            
            self.image_cache[key] = image_data
            self.cache_size_bytes += data_size
            self.access_order.append(key)
            
            logger.debug(f"图像缓存: {key}, 大小: {data_size/1024:.1f}KB, 总缓存: {self.cache_size_bytes/1024/1024:.1f}MB")
        
    def get_image(self, key: str) -> Optional[bytes]:
        """获取缓存的图像"""
        with self._lock:
            if key in self.image_cache:
                # 更新访问顺序
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.image_cache[key]
            return None
        
    def _evict_oldest(self):
        """移除最旧的缓存项"""
        if self.access_order:
            oldest_key = self.access_order.pop(0)
            if oldest_key in self.image_cache:
                data_size = len(self.image_cache[oldest_key])
                self.cache_size_bytes -= data_size
                del self.image_cache[oldest_key]
                logger.debug(f"移除缓存: {oldest_key}, 释放: {data_size/1024:.1f}KB")
            
    def clear_cache(self):
        """清空缓存"""
        with self._lock:
            self.image_cache.clear()
            self.access_order.clear()
            self.cache_size_bytes = 0
            gc.collect()
            logger.info("图像缓存已清空")
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        with self._lock:
            return {
                'cache_count': len(self.image_cache),
                'cache_size_mb': self.cache_size_bytes / 1024 / 1024,
                'max_cache_size': self.max_cache_size,
                'max_memory_mb': self.max_memory_bytes / 1024 / 1024,
                'memory_usage_percent': (self.cache_size_bytes / self.max_memory_bytes) * 100
            }
    
    def cleanup_if_needed(self) -> bool:
        """根据需要清理缓存"""
        with self._lock:
            if self.cache_size_bytes > self.max_memory_bytes * 0.8:  # 超过80%时清理
                # 清理一半的缓存
                cleanup_count = len(self.image_cache) // 2
                for _ in range(cleanup_count):
                    if self.access_order:
                        self._evict_oldest()
                logger.info(f"自动清理缓存，释放 {cleanup_count} 个项目")
                return True
            return False


def optimize_memory():
    """执行内存优化"""
    logger.info("开始内存优化...")
    
    # 强制垃圾回收
    collected = gc.collect()
    logger.info(f"垃圾回收完成，回收对象数: {collected}")
    
    # 获取内存使用情况
    memory = psutil.virtual_memory()
    logger.info(f"内存使用率: {memory.percent:.1f}%")
    
    return memory.percent


def memory_limit_decorator(max_memory_mb: int):
    """内存限制装饰器"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # 检查内存使用
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > max_memory_mb:
                logger.warning(f"内存使用超限: {memory_mb:.1f}MB > {max_memory_mb}MB")
                optimize_memory()
                
            return func(*args, **kwargs)
        return wrapper
    return decorator


# 全局内存监控器实例
memory_monitor = MemoryMonitor()
image_memory_manager = ImageMemoryManager()
