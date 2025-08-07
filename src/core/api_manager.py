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
                # 🔧 修复：根据提供商类型设置默认模型名称
                provider_type = model.get('type', '').lower()
                default_model_name = ''

                if provider_type == 'deepseek':
                    default_model_name = 'deepseek-chat'
                elif provider_type == 'tongyi':
                    default_model_name = 'qwen-plus'
                elif provider_type == 'zhipu':
                    default_model_name = 'glm-4-flash'
                elif provider_type == 'google':
                    default_model_name = 'gemini-1.5-flash'

                api_config = APIConfig(
                    name=model.get('name', ''),
                    api_type=APIType.LLM,
                    provider=model.get('type', ''),
                    api_key=model.get('key', ''),
                    api_url=model.get('url', ''),
                    model_name=model.get('model_name', default_model_name),
                    priority=model.get('priority', 1),
                    enabled=model.get('enabled', True)
                )
                self.apis[APIType.LLM].append(api_config)
            
            # 加载TTS配置
            self._load_tts_configs()
            
            # 加载图像生成API配置
            self._load_image_generation_configs()
            
            logger.info(f"已加载 {len(self.apis[APIType.LLM])} 个LLM API配置")
            logger.info(f"已加载 {len(self.apis[APIType.TEXT_TO_SPEECH])} 个TTS API配置")
            logger.info(f"已加载 {len(self.apis[APIType.IMAGE_GENERATION])} 个图像生成 API配置")
            
        except Exception as e:
            logger.error(f"加载API配置失败: {e}")
    
    def _load_tts_configs(self):
        """加载TTS配置"""
        try:
            import os
            import json
            
            # 获取TTS配置文件路径
            config_dir = self.config_manager.config_dir
            tts_config_path = os.path.join(config_dir, 'tts_config.json')
            
            if not os.path.exists(tts_config_path):
                logger.warning(f"TTS配置文件不存在: {tts_config_path}")
                return
            
            with open(tts_config_path, 'r', encoding='utf-8') as f:
                tts_config = json.load(f)
            
            # 加载Edge-TTS配置
            if tts_config.get('edge_tts', {}).get('enabled', False):
                edge_tts_config = APIConfig(
                    name="Edge-TTS",
                    api_type=APIType.TEXT_TO_SPEECH,
                    provider="azure",
                    api_key="",  # Edge-TTS不需要API密钥
                    api_url="",  # Edge-TTS不需要URL
                    model_name="edge-tts",
                    priority=1,
                    enabled=True,
                    extra_params={
                        'default_voice': tts_config.get('default_voice', 'zh-CN-YunxiNeural'),
                        'default_rate': tts_config.get('default_rate', 1.0),
                        'default_volume': tts_config.get('default_volume', 1.0),
                        'output_format': tts_config.get('output_format', 'mp3'),
                        'output_dir': tts_config.get('audio', {}).get('output_dir', 'output/audio')
                    }
                )
                self.apis[APIType.TEXT_TO_SPEECH].append(edge_tts_config)
                logger.info("已加载Edge-TTS配置")
            
            # 加载SiliconFlow TTS配置
            siliconflow_config = tts_config.get('siliconflow', {})
            if siliconflow_config.get('enabled', False) and siliconflow_config.get('api_key'):
                sf_tts_config = APIConfig(
                    name="SiliconFlow-TTS",
                    api_type=APIType.TEXT_TO_SPEECH,
                    provider="siliconflow",
                    api_key=siliconflow_config.get('api_key', ''),
                    api_url=siliconflow_config.get('base_url', 'https://api.siliconflow.cn/v1'),
                    model_name="tts-1",
                    priority=2,
                    enabled=True,
                    extra_params={
                        'output_format': tts_config.get('output_format', 'mp3'),
                        'output_dir': tts_config.get('audio', {}).get('output_dir', 'output/audio')
                    }
                )
                self.apis[APIType.TEXT_TO_SPEECH].append(sf_tts_config)
                logger.info("已加载SiliconFlow TTS配置")
                
        except Exception as e:
            logger.error(f"加载TTS配置失败: {e}")
    
    def _load_image_generation_configs(self):
        """加载图像生成API配置"""
        try:
            import os
            import sys
            
            # 获取图像生成配置文件路径
            config_dir = self.config_manager.config_dir
            image_config_path = os.path.join(config_dir, 'image_generation_config.py')
            
            if not os.path.exists(image_config_path):
                logger.warning(f"图像生成配置文件不存在: {image_config_path}")
                return
            
            # 动态导入配置模块
            sys.path.insert(0, config_dir)
            try:
                import image_generation_config
                config = image_generation_config.get_config('development')
                
                # 加载各个引擎的配置
                engines = config.get('engines', {})
                
                # Pollinations AI (免费)
                if engines.get('pollinations', {}).get('enabled', False):
                    pollinations_config = APIConfig(
                        name="Pollinations AI",
                        api_type=APIType.IMAGE_GENERATION,
                        provider="pollinations",
                        api_key="",  # 免费服务不需要API密钥
                        api_url="https://image.pollinations.ai/prompt/",
                        model_name="flux",
                        priority=1,
                        enabled=True,
                        extra_params=engines.get('pollinations', {})
                    )
                    self.apis[APIType.IMAGE_GENERATION].append(pollinations_config)
                    logger.info("已加载Pollinations AI配置")
                
                # CogView-3 Flash (智谱AI免费)
                if engines.get('cogview_3_flash', {}).get('enabled', False):
                    # 从LLM配置中获取智谱AI的API密钥
                    zhipu_api_key = ""
                    for llm_api in self.apis[APIType.LLM]:
                        if llm_api.provider == "zhipu":
                            zhipu_api_key = llm_api.api_key
                            break
                    
                    if zhipu_api_key:
                        cogview_config = APIConfig(
                            name="CogView-3 Flash",
                            api_type=APIType.IMAGE_GENERATION,
                            provider="cogview_3_flash",
                            api_key=zhipu_api_key,
                            api_url="https://open.bigmodel.cn/api/paas/v4/images/generations",
                            model_name="cogview-3-flash",
                            priority=2,
                            enabled=True,
                            extra_params=engines.get('cogview_3_flash', {})
                        )
                        self.apis[APIType.IMAGE_GENERATION].append(cogview_config)
                        logger.info("已加载CogView-3 Flash配置")
                    else:
                        logger.warning("未找到智谱AI API密钥，跳过CogView-3 Flash配置")
                
                # ComfyUI本地
                comfyui_config = engines.get('comfyui', {})
                if comfyui_config.get('local', {}).get('enabled', False):
                    local_config = APIConfig(
                        name="ComfyUI Local",
                        api_type=APIType.IMAGE_GENERATION,
                        provider="comfyui_local",
                        api_key="",
                        api_url=comfyui_config['local'].get('url', 'http://127.0.0.1:8188'),
                        model_name="comfyui",
                        priority=3,
                        enabled=True,
                        extra_params=comfyui_config.get('local', {})
                    )
                    self.apis[APIType.IMAGE_GENERATION].append(local_config)
                    logger.info("已加载ComfyUI Local配置")
                
            finally:
                # 清理sys.path
                if config_dir in sys.path:
                    sys.path.remove(config_dir)
                    
        except Exception as e:
            logger.error(f"加载图像生成配置失败: {e}")
    
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