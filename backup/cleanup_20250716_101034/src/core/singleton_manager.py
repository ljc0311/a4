#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单例管理器
确保关键服务只初始化一次，避免重复加载
"""

import threading
from typing import Dict, Any, Optional, Type
from src.utils.logger import logger


class SingletonManager:
    """单例管理器，确保服务只初始化一次"""
    
    _instance = None
    _lock = threading.Lock()
    _services: Dict[str, Any] = {}
    _initialized: Dict[str, bool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 避免重复初始化
        if hasattr(self, '_initialized_singleton'):
            return
        self._initialized_singleton = True
        logger.info("单例管理器初始化完成")
    
    def get_or_create_service(self, service_key: str, factory_func, *args, **kwargs) -> Any:
        """获取或创建服务实例"""
        if service_key in self._services:
            logger.debug(f"复用现有服务: {service_key}")
            return self._services[service_key]
        
        with self._lock:
            # 双重检查锁定
            if service_key in self._services:
                return self._services[service_key]
            
            logger.info(f"创建新服务: {service_key}")
            try:
                service = factory_func(*args, **kwargs)
                self._services[service_key] = service
                self._initialized[service_key] = True
                return service
            except Exception as e:
                logger.error(f"创建服务 {service_key} 失败: {e}")
                raise
    
    def get_service(self, service_key: str) -> Optional[Any]:
        """获取已存在的服务"""
        return self._services.get(service_key)
    
    def is_service_initialized(self, service_key: str) -> bool:
        """检查服务是否已初始化"""
        return self._initialized.get(service_key, False)
    
    def register_service(self, service_key: str, service_instance: Any):
        """注册已存在的服务实例"""
        with self._lock:
            if service_key not in self._services:
                self._services[service_key] = service_instance
                self._initialized[service_key] = True
                logger.info(f"注册服务: {service_key}")
            else:
                logger.debug(f"服务已存在，跳过注册: {service_key}")
    
    def remove_service(self, service_key: str):
        """移除服务"""
        with self._lock:
            if service_key in self._services:
                del self._services[service_key]
                self._initialized.pop(service_key, None)
                logger.info(f"移除服务: {service_key}")
    
    def clear_all_services(self):
        """清除所有服务（用于测试或重置）"""
        with self._lock:
            self._services.clear()
            self._initialized.clear()
            logger.info("清除所有服务")
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取所有服务状态"""
        return {
            'total_services': len(self._services),
            'initialized_services': list(self._initialized.keys()),
            'service_types': {key: type(service).__name__ for key, service in self._services.items()}
        }


# 全局单例实例
singleton_manager = SingletonManager()


def get_singleton_service(service_key: str, factory_func=None, *args, **kwargs):
    """便捷函数：获取或创建单例服务"""
    if factory_func is None:
        return singleton_manager.get_service(service_key)
    return singleton_manager.get_or_create_service(service_key, factory_func, *args, **kwargs)


def register_singleton_service(service_key: str, service_instance: Any):
    """便捷函数：注册单例服务"""
    singleton_manager.register_service(service_key, service_instance)


def is_service_initialized(service_key: str) -> bool:
    """便捷函数：检查服务是否已初始化"""
    return singleton_manager.is_service_initialized(service_key)
