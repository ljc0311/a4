#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置缓存管理器
避免重复读取配置文件，提高性能
"""

import os
import json
import threading
import time
from typing import Dict, Any, Optional
from src.utils.logger import logger


class ConfigCache:
    """配置缓存管理器"""
    
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
        
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._file_timestamps: Dict[str, float] = {}
        self._cache_lock = threading.RLock()
        
        logger.info("配置缓存管理器初始化完成")
    
    def get_config(self, file_path: str, force_reload: bool = False) -> Optional[Dict[str, Any]]:
        """获取配置，优先从缓存读取"""
        abs_path = os.path.abspath(file_path)
        
        with self._cache_lock:
            # 检查文件是否存在
            if not os.path.exists(abs_path):
                logger.warning(f"配置文件不存在: {abs_path}")
                return None
            
            # 获取文件修改时间
            current_mtime = os.path.getmtime(abs_path)
            cached_mtime = self._file_timestamps.get(abs_path, 0)
            
            # 检查是否需要重新加载
            if (force_reload or 
                abs_path not in self._cache or 
                current_mtime > cached_mtime):
                
                try:
                    logger.debug(f"加载配置文件: {abs_path}")
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    self._cache[abs_path] = config_data
                    self._file_timestamps[abs_path] = current_mtime
                    
                    logger.debug(f"配置文件已缓存: {abs_path}")
                    return config_data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误 {abs_path}: {e}")
                    return None
                except Exception as e:
                    logger.error(f"读取配置文件失败 {abs_path}: {e}")
                    return None
            else:
                logger.debug(f"使用缓存配置: {abs_path}")
                return self._cache[abs_path]
    
    def invalidate_cache(self, file_path: str = None):
        """使缓存失效"""
        with self._cache_lock:
            if file_path:
                abs_path = os.path.abspath(file_path)
                self._cache.pop(abs_path, None)
                self._file_timestamps.pop(abs_path, None)
                logger.info(f"清除配置缓存: {abs_path}")
            else:
                self._cache.clear()
                self._file_timestamps.clear()
                logger.info("清除所有配置缓存")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """获取缓存状态"""
        with self._cache_lock:
            return {
                'cached_files': len(self._cache),
                'files': list(self._cache.keys()),
                'total_size': sum(len(str(config)) for config in self._cache.values())
            }


class ModelConfigCache:
    """模型配置专用缓存"""
    
    _instance = None
    _lock = threading.Lock()
    _models_cache = None
    _last_load_time = 0
    _cache_duration = 300  # 5分钟缓存
    
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
        logger.debug("模型配置缓存初始化完成")
    
    def get_models(self, config_manager) -> list:
        """获取模型配置，使用缓存机制"""
        current_time = time.time()
        
        with self._lock:
            # 检查缓存是否有效
            if (self._models_cache is not None and 
                current_time - self._last_load_time < self._cache_duration):
                logger.debug("使用缓存的模型配置")
                return self._models_cache
            
            # 重新加载模型配置
            logger.debug("重新加载模型配置")
            self._models_cache = config_manager.get_models()
            self._last_load_time = current_time
            
            return self._models_cache
    
    def invalidate(self):
        """使模型缓存失效"""
        with self._lock:
            self._models_cache = None
            self._last_load_time = 0
            logger.debug("模型配置缓存已失效")


# 全局实例
config_cache = ConfigCache()
model_config_cache = ModelConfigCache()


def get_cached_config(file_path: str, force_reload: bool = False) -> Optional[Dict[str, Any]]:
    """便捷函数：获取缓存的配置"""
    return config_cache.get_config(file_path, force_reload)


def invalidate_config_cache(file_path: str = None):
    """便捷函数：使配置缓存失效"""
    config_cache.invalidate_cache(file_path)


def get_cached_models(config_manager) -> list:
    """便捷函数：获取缓存的模型配置"""
    return model_config_cache.get_models(config_manager)
