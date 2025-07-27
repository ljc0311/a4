#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内存优化管理器
提供内存监控、清理和优化功能
"""

import gc
import os
import sys
import time
import threading
import weakref
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from contextlib import contextmanager

try:
    import psutil
except ImportError:
    psutil = None

from src.utils.logger import logger

@dataclass
class MemoryStats:
    """内存统计信息"""
    rss_mb: float  # 物理内存使用量(MB)
    vms_mb: float  # 虚拟内存使用量(MB)
    percent: float  # 内存使用百分比
    available_mb: float  # 可用内存(MB)
    timestamp: float

class MemoryManager:
    """内存管理器"""
    
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
        self.max_memory_mb = 2048  # 默认最大内存限制2GB
        self.cleanup_threshold = 0.8  # 内存使用率超过80%时清理
        self.monitoring_enabled = True
        self.cleanup_callbacks: List[Callable] = []
        self.object_registry: Dict[str, weakref.WeakSet] = {}
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_memory, daemon=True)
        self.monitor_thread.start()
        
        logger.info("内存管理器初始化完成")
    
    def get_memory_stats(self) -> MemoryStats:
        """获取当前内存统计信息"""
        if psutil is None:
            # 如果没有psutil，使用基础方法
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            rss_mb = usage.ru_maxrss / 1024  # Linux下是KB，需要转换
            if sys.platform == 'darwin':  # macOS下是字节
                rss_mb = usage.ru_maxrss / 1024 / 1024
            
            return MemoryStats(
                rss_mb=rss_mb,
                vms_mb=0,
                percent=0,
                available_mb=0,
                timestamp=time.time()
            )
        
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()
            
            return MemoryStats(
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                percent=process.memory_percent(),
                available_mb=system_memory.available / 1024 / 1024,
                timestamp=time.time()
            )
        except Exception as e:
            logger.error(f"获取内存统计失败: {e}")
            return MemoryStats(0, 0, 0, 0, time.time())
    
    def set_memory_limit(self, limit_mb: int):
        """设置内存限制"""
        self.max_memory_mb = limit_mb
        logger.info(f"内存限制设置为: {limit_mb}MB")
    
    def register_cleanup_callback(self, callback: Callable):
        """注册清理回调函数"""
        self.cleanup_callbacks.append(callback)
        logger.debug(f"注册内存清理回调: {callback.__name__}")
    
    def register_object(self, category: str, obj: Any):
        """注册对象到内存管理器"""
        if category not in self.object_registry:
            self.object_registry[category] = weakref.WeakSet()
        
        # 检查对象是否支持弱引用
        try:
            self.object_registry[category].add(obj)
        except TypeError:
            # 对于不支持弱引用的对象（如bytes, int, str等），我们跳过注册
            # 这些基础类型通常由Python自动管理内存
            logger.debug(f"对象类型 {type(obj).__name__} 不支持弱引用，跳过注册")
            pass
    
    def get_object_count(self, category: str) -> int:
        """获取指定类别的对象数量"""
        if category in self.object_registry:
            return len(self.object_registry[category])
        return 0
    
    def get_all_object_counts(self) -> Dict[str, int]:
        """获取所有类别的对象数量"""
        return {category: len(obj_set) for category, obj_set in self.object_registry.items()}
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """获取内存使用摘要"""
        stats = self.get_memory_stats()
        object_counts = self.get_all_object_counts()
        
        return {
            'memory_stats': {
                'rss_mb': stats.rss_mb,
                'vms_mb': stats.vms_mb,
                'percent': stats.percent,
                'available_mb': stats.available_mb
            },
            'object_counts': object_counts,
            'total_registered_objects': sum(object_counts.values()),
            'memory_pressure': self.check_memory_pressure(),
            'cache_info': {
                'image_cache_size_mb': getattr(image_memory_manager, 'current_cache_size', 0) / 1024 / 1024,
                'image_cache_items': len(getattr(image_memory_manager, 'image_cache', {}))
            }
        }
    
    def cleanup_objects(self, category: str = None):
        """清理指定类别的对象"""
        if category:
            if category in self.object_registry:
                count = len(self.object_registry[category])
                self.object_registry[category].clear()
                logger.info(f"清理了 {count} 个 {category} 对象")
        else:
            total_count = 0
            for cat, obj_set in self.object_registry.items():
                count = len(obj_set)
                obj_set.clear()
                total_count += count
                logger.debug(f"清理了 {count} 个 {cat} 对象")
            logger.info(f"总共清理了 {total_count} 个对象")
    
    def force_cleanup(self) -> Dict[str, Any]:
        """强制内存清理"""
        logger.info("开始强制内存清理...")
        
        stats_before = self.get_memory_stats()
        
        # 1. 执行注册的清理回调
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"执行清理回调失败: {e}")
        
        # 2. 清理对象注册表
        self.cleanup_objects()
        
        # 3. 强制垃圾回收
        collected = gc.collect()
        
        # 4. 清理模块缓存（谨慎使用）
        self._cleanup_module_cache()
        
        stats_after = self.get_memory_stats()
        
        cleanup_result = {
            'memory_before_mb': stats_before.rss_mb,
            'memory_after_mb': stats_after.rss_mb,
            'memory_freed_mb': stats_before.rss_mb - stats_after.rss_mb,
            'gc_collected': collected,
            'timestamp': time.time()
        }
        
        logger.info(f"内存清理完成: 释放 {cleanup_result['memory_freed_mb']:.1f}MB, "
                   f"GC回收 {collected} 个对象")
        
        return cleanup_result
    
    def _cleanup_module_cache(self):
        """清理模块缓存"""
        try:
            # 清理PIL图像缓存
            try:
                from PIL import Image
                Image._decompression_bomb_check = lambda size: None
            except ImportError:
                pass
            
            # 清理matplotlib缓存
            try:
                import matplotlib
                matplotlib.pyplot.close('all')
            except ImportError:
                pass
            
            # 清理numpy缓存
            try:
                import numpy as np
                # numpy没有直接的缓存清理方法，但可以清理临时数组
                pass
            except ImportError:
                pass
                
        except Exception as e:
            logger.error(f"清理模块缓存失败: {e}")
    
    def check_memory_pressure(self) -> bool:
        """检查是否存在内存压力"""
        stats = self.get_memory_stats()
        
        # 检查物理内存使用
        if stats.rss_mb > self.max_memory_mb:
            return True
        
        # 检查系统内存使用率
        if stats.percent > self.cleanup_threshold * 100:
            return True
        
        # 检查可用内存
        if psutil and stats.available_mb < 500:  # 可用内存少于500MB
            return True
        
        return False
    
    def _monitor_memory(self):
        """内存监控线程"""
        while self.monitoring_enabled:
            try:
                if self.check_memory_pressure():
                    logger.warning("检测到内存压力，开始自动清理...")
                    self.force_cleanup()
                
                time.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                logger.error(f"内存监控线程异常: {e}")
                time.sleep(60)  # 出错后等待更长时间
    
    def stop_monitoring(self):
        """停止内存监控"""
        self.monitoring_enabled = False
        logger.info("内存监控已停止")
    
    @contextmanager
    def memory_context(self, description: str = "操作"):
        """内存监控上下文管理器"""
        stats_before = self.get_memory_stats()
        start_time = time.time()
        
        try:
            yield
        finally:
            stats_after = self.get_memory_stats()
            duration = time.time() - start_time
            memory_delta = stats_after.rss_mb - stats_before.rss_mb
            
            if memory_delta > 50:  # 内存增长超过50MB时记录
                logger.warning(f"{description} 内存增长: {memory_delta:.1f}MB, 耗时: {duration:.2f}s")
            elif memory_delta > 10:  # 内存增长超过10MB时调试记录
                logger.debug(f"{description} 内存增长: {memory_delta:.1f}MB, 耗时: {duration:.2f}s")

class ImageMemoryManager:
    """图像内存管理器"""
    
    def __init__(self):
        self.image_cache: Dict[str, Any] = {}
        self.cache_size_limit = 200 * 1024 * 1024  # 200MB图像缓存限制
        self.current_cache_size = 0
        
    def add_image_to_cache(self, key: str, image_data: bytes):
        """添加图像到缓存"""
        image_size = len(image_data)
        
        # 如果单个图像过大，不缓存
        if image_size > 50 * 1024 * 1024:  # 50MB
            logger.warning(f"图像过大({image_size/1024/1024:.1f}MB)，不加入缓存")
            return
        
        # 清理缓存空间
        while self.current_cache_size + image_size > self.cache_size_limit:
            if not self.image_cache:
                break
            
            # 删除最旧的缓存项
            oldest_key = next(iter(self.image_cache))
            old_size = len(self.image_cache[oldest_key])
            del self.image_cache[oldest_key]
            self.current_cache_size -= old_size
        
        self.image_cache[key] = image_data
        self.current_cache_size += image_size
        
        logger.debug(f"图像缓存: {key}, 大小: {image_size/1024:.1f}KB, "
                    f"总缓存: {self.current_cache_size/1024/1024:.1f}MB")
    
    def get_image_from_cache(self, key: str) -> Optional[bytes]:
        """从缓存获取图像"""
        return self.image_cache.get(key)
    
    def clear_image_cache(self):
        """清理图像缓存"""
        cache_size = self.current_cache_size
        self.image_cache.clear()
        self.current_cache_size = 0
        logger.info(f"清理图像缓存: {cache_size/1024/1024:.1f}MB")

# 全局实例
memory_manager = MemoryManager()
image_memory_manager = ImageMemoryManager()

def monitor_memory(description: str = "操作"):
    """内存监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with memory_manager.memory_context(f"{description}({func.__name__})"):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def cleanup_on_low_memory():
    """低内存时的清理函数"""
    if memory_manager.check_memory_pressure():
        memory_manager.force_cleanup()
        image_memory_manager.clear_image_cache()
        return True
    return False