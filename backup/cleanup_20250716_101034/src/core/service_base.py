#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务层基类
为所有AI服务提供统一的接口、错误处理和重试机制
"""

import time
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

from src.utils.logger import logger
from .api_manager import APIManager, APIConfig, APIType

class ServiceStatus(Enum):
    """服务状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"

@dataclass
class ServiceResult:
    """服务执行结果"""
    success: bool
    data: Any = None
    error: str = ""
    execution_time: float = 0.0
    api_used: str = ""
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ServiceBase(ABC):
    """服务基类"""
    
    def __init__(self, api_manager: APIManager, service_name: str):
        self.api_manager = api_manager
        self.service_name = service_name
        self.status = ServiceStatus.IDLE
        self.last_error = ""
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 1.0  # 秒
        self.backoff_factor = 2.0
        
        logger.info(f"服务 {service_name} 初始化完成")
    
    @abstractmethod
    def get_api_type(self) -> APIType:
        """获取服务对应的API类型"""
        pass
    
    @abstractmethod
    async def _execute_request(self, api_config: APIConfig, **kwargs) -> ServiceResult:
        """执行具体的API请求（子类实现）"""
        pass
    
    def get_available_providers(self) -> List[str]:
        """获取可用的服务提供商列表"""
        apis = self.api_manager.get_available_apis(self.get_api_type())
        return list(set(api.provider for api in apis))
    
    async def execute(self, provider: Optional[str] = None, **kwargs) -> ServiceResult:
        """执行服务请求"""
        self.status = ServiceStatus.RUNNING
        start_time = time.time()
        
        try:
            result = await self._execute_with_retry(provider, **kwargs)
            
            if result.success:
                self.success_count += 1
                self.status = ServiceStatus.IDLE
            else:
                self.error_count += 1
                self.last_error = result.error
                self.status = ServiceStatus.ERROR
            
            self.request_count += 1
            result.execution_time = time.time() - start_time
            
            return result
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            self.status = ServiceStatus.ERROR
            
            logger.error(f"服务 {self.service_name} 执行失败: {e}")
            
            return ServiceResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    async def _execute_with_retry(self, provider: Optional[str] = None, **kwargs) -> ServiceResult:
        """带重试机制的执行"""
        last_error = ""
        
        for attempt in range(self.max_retries + 1):
            try:
                # 获取最佳API
                api_config = self.api_manager.get_best_api(self.get_api_type(), provider)
                
                if not api_config:
                    return ServiceResult(
                        success=False,
                        error=f"没有可用的 {self.get_api_type().value} API"
                    )
                
                # 记录请求
                self.api_manager.record_request(api_config)
                
                # 执行请求
                result = await self._execute_request(api_config, **kwargs)
                result.api_used = f"{api_config.provider}:{api_config.name}"
                
                if result.success:
                    if attempt > 0:
                        logger.info(f"服务 {self.service_name} 在第 {attempt + 1} 次尝试后成功")
                    return result
                
                last_error = result.error
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"服务 {self.service_name} 第 {attempt + 1} 次尝试失败: {e}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < self.max_retries:
                delay = self.retry_delay * (self.backoff_factor ** attempt)
                logger.info(f"服务 {self.service_name} 将在 {delay:.1f} 秒后重试")
                await asyncio.sleep(delay)
        
        return ServiceResult(
            success=False,
            error=f"所有重试都失败了，最后错误: {last_error}"
        )
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'service_name': self.service_name,
            'status': self.status.value,
            'request_count': self.request_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': self.success_count / max(self.request_count, 1),
            'last_error': self.last_error,
            'available_providers': self.get_available_providers()
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_error = ""
        logger.info(f"服务 {self.service_name} 统计信息已重置")
    
    def stop(self):
        """停止服务"""
        self.status = ServiceStatus.STOPPED
        logger.info(f"服务 {self.service_name} 已停止")