#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一API管理器
负责管理所有AI服务的API接口，包括LLM、图像生成、语音合成等
支持动态切换和负载均衡
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from src.utils.logger import logger
from src.utils.config_manager import ConfigManager

class APIType(Enum):
    """API类型枚举"""
    LLM = "llm"
    IMAGE_GENERATION = "image_generation"
    TEXT_TO_SPEECH = "text_to_speech"
    SPEECH_TO_TEXT = "speech_to_text"
    TRANSLATION = "translation"
    IMAGE_TO_VIDEO = "image_to_video"

@dataclass
class APIConfig:
    """API配置数据类"""
    name: str
    api_type: APIType
    provider: str  # deepseek, tongyi, zhipu, comfyui, etc.
    api_key: str
    api_url: str
    model_name: str = ""
    max_requests_per_minute: int = 60
    timeout: int = 30
    priority: int = 1  # 优先级，数字越小优先级越高
    enabled: bool = True
    extra_params: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}

class APIManager:
    """统一API管理器"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.apis: Dict[APIType, List[APIConfig]] = {api_type: [] for api_type in APIType}
        self.request_counts: Dict[str, List[float]] = {}  # API请求计数
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # 加载配置
        self._load_api_configs()
        
        logger.info("API管理器初始化完成")
    
    async def initialize(self):
        """异步初始化方法"""
        try:
            # 这里可以添加异步初始化逻辑
            # 比如测试API连接等
            logger.info("API管理器异步初始化完成")
        except Exception as e:
            logger.error(f"API管理器异步初始化失败: {e}")
            raise
    
    def _load_api_configs(self):
        """从配置文件加载API配置"""
        try:
            # 加载LLM配置
            llm_models = self.config_manager.get_models()
            for model in llm_models:
                api_config = APIConfig(
                    name=model.get('name', ''),
                    api_type=APIType.LLM,
                    provider=model.get('type', ''),
                    api_key=model.get('key', ''),
                    api_url=model.get('url', ''),
                    model_name=model.get('model_name', ''),
                    priority=model.get('priority', 1),
                    enabled=model.get('enabled', True)
                )
                self.apis[APIType.LLM].append(api_config)
            
            # TODO: 加载其他类型API配置
            # 图像生成、语音合成等配置
            
            logger.info(f"已加载 {len(self.apis[APIType.LLM])} 个LLM API配置")
            
        except Exception as e:
            logger.error(f"加载API配置失败: {e}")
    
    def get_available_apis(self, api_type: APIType, provider: Optional[str] = None) -> List[APIConfig]:
        """获取可用的API列表"""
        apis = self.apis.get(api_type, [])
        
        # 过滤启用的API
        available_apis = [api for api in apis if api.enabled]
        
        # 按提供商过滤
        if provider:
            available_apis = [api for api in available_apis if api.provider == provider]
        
        # 按优先级排序
        available_apis.sort(key=lambda x: x.priority)
        
        return available_apis
    
    def get_best_api(self, api_type: APIType, provider: Optional[str] = None) -> Optional[APIConfig]:
        """获取最佳API（考虑优先级和请求限制）"""
        available_apis = self.get_available_apis(api_type, provider)
        
        if not available_apis:
            return None
        
        # 检查请求限制
        for api in available_apis:
            if self._can_make_request(api):
                return api
        
        # 如果所有API都达到限制，返回优先级最高的
        return available_apis[0]
    
    def _can_make_request(self, api_config: APIConfig) -> bool:
        """检查是否可以向指定API发送请求"""
        api_key = f"{api_config.api_type.value}_{api_config.name}"
        current_time = time.time()
        
        if api_key not in self.request_counts:
            self.request_counts[api_key] = []
        
        # 清理1分钟前的请求记录
        self.request_counts[api_key] = [
            req_time for req_time in self.request_counts[api_key]
            if current_time - req_time < 60
        ]
        
        # 检查是否超过限制
        return len(self.request_counts[api_key]) < api_config.max_requests_per_minute
    
    def record_request(self, api_config: APIConfig):
        """记录API请求"""
        api_key = f"{api_config.api_type.value}_{api_config.name}"
        current_time = time.time()
        
        if api_key not in self.request_counts:
            self.request_counts[api_key] = []
        
        self.request_counts[api_key].append(current_time)
    
    def add_api_config(self, api_config: APIConfig):
        """添加API配置"""
        self.apis[api_config.api_type].append(api_config)
        logger.info(f"已添加API配置: {api_config.name} ({api_config.api_type.value})")
    
    def remove_api_config(self, api_type: APIType, name: str):
        """移除API配置"""
        self.apis[api_type] = [
            api for api in self.apis[api_type] if api.name != name
        ]
        logger.info(f"已移除API配置: {name} ({api_type.value})")
    
    def update_api_config(self, api_config: APIConfig):
        """更新API配置"""
        apis = self.apis[api_config.api_type]
        for i, api in enumerate(apis):
            if api.name == api_config.name:
                apis[i] = api_config
                logger.info(f"已更新API配置: {api_config.name}")
                return
        
        # 如果没找到，则添加
        self.add_api_config(api_config)
    
    def get_api_status(self) -> Dict[str, Any]:
        """获取所有API的状态信息"""
        status = {}
        
        for api_type, apis in self.apis.items():
            status[api_type.value] = []
            for api in apis:
                api_key = f"{api_type.value}_{api.name}"
                recent_requests = len(self.request_counts.get(api_key, []))
                
                status[api_type.value].append({
                    'name': api.name,
                    'provider': api.provider,
                    'enabled': api.enabled,
                    'recent_requests': recent_requests,
                    'can_make_request': self._can_make_request(api)
                })
        
        return status
    
    def reload_configs(self):
        """重新加载配置"""
        self.apis = {api_type: [] for api_type in APIType}
        self._load_api_configs()
        logger.info("API配置已重新加载")
    
    def shutdown(self):
        """关闭API管理器"""
        self.executor.shutdown(wait=True)
        logger.info("API管理器已关闭")