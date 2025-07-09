#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能优化工具
提供图片缓存、内存管理、异步处理优化等功能
"""

import os
import gc
import sys
import time
import hashlib
import threading
import weakref
from typing import Dict, Optional, Any, Callable, List, Tuple
from pathlib import Path
from functools import wraps, lru_cache
from dataclasses import dataclass
from collections import OrderedDict
import pickle

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QTimer, QThread, QObject, pyqtSignal, QMutex
from PyQt5.QtGui import QPixmap, QImage

from src.utils.logger import logger

@dataclass
class CacheEntry:
    """缓存条目"""
    data: Any
    size: int  # 字节大小
    access_time: float = 0.0
    access_count: int = 0
    
    def __post_init__(self):
        if self.access_time == 0.0:
            self.access_time = time.time()

class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, max_size: int = 100, max_memory: int = 100 * 1024 * 1024):  # 100MB
        self.max_size = max_size
        self.max_memory = max_memory
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.current_memory = 0
        self.mutex = threading.Lock()
        
        # 统计信息
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        with self.mutex:
            if key in self.cache:
                # 移动到末尾（最近使用）
                entry = self.cache.pop(key)
                entry.access_time = time.time()
                entry.access_count += 1
                self.cache[key] = entry
                self.hits += 1
                return entry.data
            else:
                self.misses += 1
                return None
    
    def put(self, key: str, data: Any, size: int = None):
        """添加缓存项"""
        with self.mutex:
            if size is None:
                size = self._estimate_size(data)
            
            # 如果已存在，先删除
            if key in self.cache:
                old_entry = self.cache.pop(key)
                self.current_memory -= old_entry.size
            
            # 创建新条目
            entry = CacheEntry(data, size)
            
            # 检查内存限制
            while (self.current_memory + size > self.max_memory or 
                   len(self.cache) >= self.max_size):
                if not self.cache:
                    break
                self._evict_least_recent()
            
            # 添加新条目
            self.cache[key] = entry
            self.current_memory += size
    
    def remove(self, key: str):
        """移除缓存项"""
        with self.mutex:
            if key in self.cache:
                entry = self.cache.pop(key)
                self.current_memory -= entry.size
    
    def clear(self):
        """清空缓存"""
        with self.mutex:
            self.cache.clear()
            self.current_memory = 0
    
    def _evict_least_recent(self):
        """移除最少使用的缓存项"""
        if self.cache:
            key, entry = self.cache.popitem(last=False)
            self.current_memory -= entry.size
    
    def _estimate_size(self, data: Any) -> int:
        """估算数据大小"""
        try:
            if isinstance(data, (QPixmap, QImage)):
                # QPixmap/QImage 大小估算
                if hasattr(data, 'width') and hasattr(data, 'height'):
                    return data.width() * data.height() * 4  # RGBA
                return 1024  # 默认大小
            elif isinstance(data, bytes):
                return len(data)
            elif isinstance(data, str):
                return len(data.encode('utf-8'))
            else:
                # 使用pickle估算大小
                return len(pickle.dumps(data))
        except:
            return 1024  # 默认大小
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.mutex:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'memory_usage': self.current_memory,
                'memory_usage_mb': self.current_memory / 1024 / 1024,
                'max_size': self.max_size,
                'max_memory_mb': self.max_memory / 1024 / 1024,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate
            }

class ImageCache:
    """图片缓存管理器"""
    
    def __init__(self, cache_dir: str = None, max_size: int = 200):
        if cache_dir is None:
            # 动态获取项目根目录下的temp文件夹
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            cache_dir = os.path.join(project_root, "temp", "image_cache")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存
        self.memory_cache = LRUCache(max_size=max_size, max_memory=200 * 1024 * 1024)  # 200MB
        
        # 磁盘缓存索引
        self.disk_index_file = self.cache_dir / "index.json"
        self.disk_index = self._load_disk_index()
    
    def get_image(self, image_path: str, size: Tuple[int, int] = None) -> Optional[QPixmap]:
        """获取图片（带缓存）"""
        cache_key = self._generate_cache_key(image_path, size)
        
        # 先检查内存缓存
        pixmap = self.memory_cache.get(cache_key)
        if pixmap:
            return pixmap
        
        # 检查磁盘缓存
        pixmap = self._load_from_disk(cache_key)
        if pixmap:
            self.memory_cache.put(cache_key, pixmap)
            return pixmap
        
        # 加载原始图片
        pixmap = self._load_original_image(image_path, size)
        if pixmap:
            # 保存到缓存
            self.memory_cache.put(cache_key, pixmap)
            self._save_to_disk(cache_key, pixmap)
        
        return pixmap
    
    def preload_images(self, image_paths: List[str], size: Tuple[int, int] = None):
        """预加载图片"""
        def preload_worker():
            for path in image_paths:
                try:
                    self.get_image(path, size)
                except Exception as e:
                    logger.warning(f"预加载图片失败 {path}: {e}")
        
        # 在后台线程中预加载
        thread = threading.Thread(target=preload_worker, daemon=True)
        thread.start()
    
    def _generate_cache_key(self, image_path: str, size: Tuple[int, int] = None) -> str:
        """生成缓存键"""
        key_data = f"{image_path}_{size}_{os.path.getmtime(image_path) if os.path.exists(image_path) else 0}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _load_original_image(self, image_path: str, size: Tuple[int, int] = None) -> Optional[QPixmap]:
        """加载原始图片"""
        try:
            if not os.path.exists(image_path):
                return None
            
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return None
            
            # 如果指定了大小，进行缩放
            if size:
                width, height = size
                pixmap = pixmap.scaled(width, height, aspectRatioMode=1, transformMode=1)  # 平滑缩放
            
            return pixmap
        except Exception as e:
            logger.error(f"加载图片失败 {image_path}: {e}")
            return None
    
    def _load_from_disk(self, cache_key: str) -> Optional[QPixmap]:
        """从磁盘加载缓存图片"""
        try:
            if cache_key not in self.disk_index:
                return None
            
            cache_file = self.cache_dir / f"{cache_key}.png"
            if not cache_file.exists():
                # 从索引中移除无效条目
                del self.disk_index[cache_key]
                self._save_disk_index()
                return None
            
            pixmap = QPixmap(str(cache_file))
            return pixmap if not pixmap.isNull() else None
        except Exception as e:
            logger.warning(f"从磁盘加载缓存失败 {cache_key}: {e}")
            return None
    
    def _save_to_disk(self, cache_key: str, pixmap: QPixmap):
        """保存图片到磁盘缓存"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.png"
            if pixmap.save(str(cache_file), "PNG"):
                self.disk_index[cache_key] = {
                    'file': str(cache_file),
                    'created': time.time(),
                    'size': cache_file.stat().st_size if cache_file.exists() else 0
                }
                self._save_disk_index()
        except Exception as e:
            logger.warning(f"保存磁盘缓存失败 {cache_key}: {e}")
    
    def _load_disk_index(self) -> Dict:
        """加载磁盘缓存索引"""
        try:
            if self.disk_index_file.exists():
                import json
                with open(self.disk_index_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载磁盘缓存索引失败: {e}")
        return {}
    
    def _save_disk_index(self):
        """保存磁盘缓存索引"""
        try:
            import json
            with open(self.disk_index_file, 'w') as f:
                json.dump(self.disk_index, f, indent=2)
        except Exception as e:
            logger.warning(f"保存磁盘缓存索引失败: {e}")
    
    def clear_cache(self):
        """清空所有缓存"""
        self.memory_cache.clear()
        
        # 清空磁盘缓存
        try:
            for cache_file in self.cache_dir.glob("*.png"):
                cache_file.unlink()
            self.disk_index.clear()
            self._save_disk_index()
        except Exception as e:
            logger.error(f"清空磁盘缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        memory_stats = self.memory_cache.get_stats()
        
        disk_size = sum(info.get('size', 0) for info in self.disk_index.values())
        
        return {
            'memory': memory_stats,
            'disk': {
                'files': len(self.disk_index),
                'size_bytes': disk_size,
                'size_mb': disk_size / 1024 / 1024
            }
        }

class MemoryMonitor(QObject):
    """内存监控器"""
    
    memory_warning = pyqtSignal(float)  # 内存使用率
    memory_critical = pyqtSignal(float)
    
    def __init__(self, warning_threshold: float = 0.8, critical_threshold: float = 0.9):
        super().__init__()
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_memory)
        self.timer.start(5000)  # 每5秒检查一次
        
        self.last_warning_time = 0
        self.last_critical_time = 0
    
    def check_memory(self):
        """检查内存使用情况"""
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent / 100.0
            
            current_time = time.time()
            
            # 避免频繁发送警告
            if (memory_percent > self.critical_threshold and 
                current_time - self.last_critical_time > 30):  # 30秒间隔
                self.memory_critical.emit(memory_percent)
                self.last_critical_time = current_time
                logger.warning(f"内存使用率达到危险水平: {memory_percent:.1%}")
                
            elif (memory_percent > self.warning_threshold and 
                  current_time - self.last_warning_time > 60):  # 60秒间隔
                self.memory_warning.emit(memory_percent)
                self.last_warning_time = current_time
                logger.info(f"内存使用率较高: {memory_percent:.1%}")
                
        except ImportError:
            logger.debug("psutil未安装，无法监控内存")
        except Exception as e:
            logger.error(f"内存监控失败: {e}")

class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self):
        self.profiles = {}
        self.active_profiles = {}
    
    def start_profile(self, name: str):
        """开始性能分析"""
        self.active_profiles[name] = time.time()
    
    def end_profile(self, name: str):
        """结束性能分析"""
        if name in self.active_profiles:
            duration = time.time() - self.active_profiles[name]
            del self.active_profiles[name]
            
            if name not in self.profiles:
                self.profiles[name] = []
            self.profiles[name].append(duration)
            
            return duration
        return None
    
    def profile_function(self, func_name: str = None):
        """装饰器：函数性能分析"""
        def decorator(func):
            name = func_name or f"{func.__module__}.{func.__name__}"
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                self.start_profile(name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = self.end_profile(name)
                    if duration and duration > 1.0:  # 超过1秒的函数记录警告
                        logger.warning(f"函数 {name} 执行时间较长: {duration:.2f}秒")
            
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = {}
        for name, durations in self.profiles.items():
            if durations:
                stats[name] = {
                    'count': len(durations),
                    'total': sum(durations),
                    'average': sum(durations) / len(durations),
                    'min': min(durations),
                    'max': max(durations)
                }
        return stats

class AsyncTaskOptimizer:
    """异步任务优化器"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.active_tasks = 0
        self.task_queue = []
        self.mutex = threading.Lock()
    
    def submit_task(self, func: Callable, *args, callback: Callable = None, **kwargs):
        """提交异步任务"""
        with self.mutex:
            if self.active_tasks < self.max_workers:
                self._execute_task(func, args, kwargs, callback)
            else:
                self.task_queue.append((func, args, kwargs, callback))
    
    def _execute_task(self, func: Callable, args: tuple, kwargs: dict, callback: Callable = None):
        """执行任务"""
        def worker():
            with self.mutex:
                self.active_tasks += 1
            
            try:
                result = func(*args, **kwargs)
                if callback:
                    callback(result)
            except Exception as e:
                logger.error(f"异步任务执行失败: {e}")
                if callback:
                    callback(None)
            finally:
                with self.mutex:
                    self.active_tasks -= 1
                    # 检查队列中的待执行任务
                    if self.task_queue:
                        next_task = self.task_queue.pop(0)
                        self._execute_task(*next_task)
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

class PerformanceOptimizer:
    """性能优化器主类"""
    
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
        
        # 初始化各个组件
        self.image_cache = ImageCache()
        self.memory_monitor = MemoryMonitor()
        self.profiler = PerformanceProfiler()
        self.task_optimizer = AsyncTaskOptimizer()
        
        # 连接内存警告信号
        self.memory_monitor.memory_warning.connect(self._on_memory_warning)
        self.memory_monitor.memory_critical.connect(self._on_memory_critical)
        
        # 定期清理
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup)
        self.cleanup_timer.start(300000)  # 5分钟清理一次
    
    def _on_memory_warning(self, usage: float):
        """内存警告处理"""
        logger.warning(f"内存使用率警告: {usage:.1%}，开始清理...")
        self.cleanup(aggressive=False)
    
    def _on_memory_critical(self, usage: float):
        """内存危险处理"""
        logger.error(f"内存使用率危险: {usage:.1%}，开始强制清理...")
        self.cleanup(aggressive=True)
    
    def cleanup(self, aggressive: bool = False):
        """清理内存和缓存"""
        try:
            # 强制垃圾回收
            gc.collect()
            
            if aggressive:
                # 激进清理：清空部分缓存
                cache_stats = self.image_cache.memory_cache.get_stats()
                if cache_stats['memory_usage_mb'] > 50:  # 超过50MB时清理一半
                    old_size = len(self.image_cache.memory_cache.cache)
                    # 清理最少使用的一半缓存
                    items_to_remove = list(self.image_cache.memory_cache.cache.keys())[:old_size//2]
                    for key in items_to_remove:
                        self.image_cache.memory_cache.remove(key)
                    logger.info(f"激进清理: 移除了 {len(items_to_remove)} 个缓存项")
            
            # 清理过期的磁盘缓存（7天前的）
            current_time = time.time()
            expired_keys = []
            for key, info in self.image_cache.disk_index.items():
                if current_time - info.get('created', 0) > 7 * 24 * 3600:  # 7天
                    expired_keys.append(key)
            
            for key in expired_keys:
                cache_file = self.image_cache.cache_dir / f"{key}.png"
                if cache_file.exists():
                    cache_file.unlink()
                del self.image_cache.disk_index[key]
            
            if expired_keys:
                self.image_cache._save_disk_index()
                logger.info(f"清理过期磁盘缓存: {len(expired_keys)} 个文件")
                
        except Exception as e:
            logger.error(f"清理操作失败: {e}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            'image_cache': self.image_cache.get_cache_stats(),
            'profiler': self.profiler.get_stats(),
            'memory': {
                'warning_threshold': self.memory_monitor.warning_threshold,
                'critical_threshold': self.memory_monitor.critical_threshold
            },
            'async_tasks': {
                'active': self.task_optimizer.active_tasks,
                'queued': len(self.task_optimizer.task_queue),
                'max_workers': self.task_optimizer.max_workers
            }
        }

# 全局性能优化器实例
performance_optimizer = PerformanceOptimizer()

# 便捷函数
def get_cached_image(image_path: str, size: Tuple[int, int] = None) -> Optional[QPixmap]:
    """获取缓存图片"""
    return performance_optimizer.image_cache.get_image(image_path, size)

def preload_images(image_paths: List[str], size: Tuple[int, int] = None):
    """预加载图片"""
    performance_optimizer.image_cache.preload_images(image_paths, size)

def profile_function(func_name: str = None):
    """性能分析装饰器"""
    return performance_optimizer.profiler.profile_function(func_name)

def submit_async_task(func: Callable, *args, callback: Callable = None, **kwargs):
    """提交异步任务"""
    performance_optimizer.task_optimizer.submit_task(func, *args, callback=callback, **kwargs)

def force_cleanup():
    """强制清理"""
    performance_optimizer.cleanup(aggressive=True)

def get_performance_stats() -> Dict[str, Any]:
    """获取性能统计"""
    return performance_optimizer.get_performance_report()