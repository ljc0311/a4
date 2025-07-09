# -*- coding: utf-8 -*-
"""
图像生成引擎抽象基类
定义统一的引擎接口，支持多种图像生成服务
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
import asyncio
from src.utils.logger import logger


class EngineType(Enum):
    """引擎类型枚举"""
    POLLINATIONS = "pollinations"
    COMFYUI_LOCAL = "comfyui_local"
    COMFYUI_CLOUD = "comfyui_cloud"
    OPENAI_DALLE = "openai_dalle"
    GOOGLE_IMAGEN = "google_imagen"
    MIDJOURNEY = "midjourney"
    STABILITY_AI = "stability_ai"
    COGVIEW_3_FLASH = "cogview_3_flash"


class EngineStatus(Enum):
    """引擎状态枚举"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


@dataclass
class GenerationConfig:
    """统一生成配置"""
    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    steps: int = 20
    cfg_scale: float = 7.0
    seed: int = -1
    batch_size: int = 1
    model: str = "default"
    style: str = "default"
    quality: str = "standard"  # standard, hd, ultra
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'prompt': self.prompt,
            'negative_prompt': self.negative_prompt,
            'width': self.width,
            'height': self.height,
            'steps': self.steps,
            'cfg_scale': self.cfg_scale,
            'seed': self.seed,
            'batch_size': self.batch_size,
            'model': self.model,
            'style': self.style,
            'quality': self.quality,
            'custom_params': self.custom_params
        }


@dataclass
class GenerationResult:
    """生成结果"""
    success: bool
    image_paths: List[str] = field(default_factory=list)
    error_message: str = ""
    generation_time: float = 0.0
    cost: float = 0.0
    engine_type: Optional[EngineType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineInfo:
    """引擎信息"""
    name: str
    version: str
    description: str
    is_free: bool
    supports_batch: bool
    supports_custom_models: bool
    max_batch_size: int
    supported_sizes: List[tuple]
    cost_per_image: float = 0.0
    rate_limit: int = 0  # 每分钟请求数限制
    

class ImageGenerationEngine(ABC):
    """图像生成引擎抽象基类"""
    
    def __init__(self, engine_type: EngineType):
        self.engine_type = engine_type
        self.status = EngineStatus.OFFLINE
        self.last_error = ""
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_cost = 0.0
        
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化引擎"""
        pass
    
    @abstractmethod
    async def generate(self, config: GenerationConfig, 
                      progress_callback: Optional[Callable] = None) -> GenerationResult:
        """生成图像"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """测试连接"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        pass
    
    @abstractmethod
    def get_engine_info(self) -> EngineInfo:
        """获取引擎信息"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        success_rate = (self.success_count / self.request_count * 100) if self.request_count > 0 else 0
        
        return {
            'engine_type': self.engine_type.value,
            'status': self.status.value,
            'last_error': self.last_error,
            'request_count': self.request_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': round(success_rate, 2),
            'total_cost': self.total_cost
        }
    
    def update_stats(self, success: bool, cost: float = 0.0, error: str = ""):
        """更新统计信息"""
        self.request_count += 1
        if success:
            self.success_count += 1
            self.status = EngineStatus.IDLE
        else:
            self.error_count += 1
            self.last_error = error
            self.status = EngineStatus.ERROR
        
        self.total_cost += cost
        
    async def cleanup(self):
        """清理资源"""
        logger.info(f"引擎 {self.engine_type.value} 清理完成")


class ConfigConverter:
    """配置转换器 - 将统一配置转换为各引擎特定格式"""
    
    @staticmethod
    def to_pollinations(config: GenerationConfig) -> Dict[str, Any]:
        """转换为Pollinations格式 - 只包含Pollinations API支持的参数"""
        result = {
            'prompt': config.prompt,
            'width': config.width,
            'height': config.height,
            'model': config.model or 'flux',
            'nologo': config.custom_params.get('nologo', True),  # 默认去除logo
            'enhance': config.custom_params.get('enhance', False),  # 默认不增强
            'safe': config.custom_params.get('safe', True)  # 默认安全模式
        }

        # 只有当seed有效时才添加
        if config.seed is not None and config.seed > 0:
            result['seed'] = config.seed

        # 添加private参数（如果需要）
        if 'private' in config.custom_params:
            result['private'] = config.custom_params['private']

        # 🔧 修复：传递workflow_id用于生成唯一文件名
        if 'workflow_id' in config.custom_params:
            result['workflow_id'] = config.custom_params['workflow_id']

        # 移除Pollinations不支持的参数
        # Pollinations不支持：negative_prompt, steps, cfg_scale, sampler, batch_size, guidance_scale, api_key, base_url, workflow_id

        return result
    
    @staticmethod
    def to_comfyui(config: GenerationConfig) -> Dict[str, Any]:
        """转换为ComfyUI格式"""
        return {
            'prompt': config.prompt,
            'negative_prompt': config.negative_prompt,
            'width': config.width,
            'height': config.height,
            'steps': config.steps,
            'cfg_scale': config.cfg_scale,
            'seed': config.seed,
            'batch_size': config.batch_size,
            'sampler_name': config.custom_params.get('sampler', 'euler'),
            'scheduler': config.custom_params.get('scheduler', 'normal')
        }
    
    @staticmethod
    def to_dalle(config: GenerationConfig) -> Dict[str, Any]:
        """转换为DALL-E格式"""
        # DALL-E支持的尺寸
        size_map = {
            (1024, 1024): "1024x1024",
            (1792, 1024): "1792x1024", 
            (1024, 1792): "1024x1792"
        }
        
        size = size_map.get((config.width, config.height), "1024x1024")
        
        return {
            'prompt': config.prompt,
            'size': size,
            'quality': config.quality,
            'n': min(config.batch_size, 10),  # DALL-E最大10张
            'style': config.custom_params.get('style', 'natural')
        }
    
    @staticmethod
    def to_stability(config: GenerationConfig) -> Dict[str, Any]:
        """转换为Stability AI格式"""
        return {
            'text_prompts': [{'text': config.prompt, 'weight': 1.0}],
            'width': config.width,
            'height': config.height,
            'steps': config.steps,
            'cfg_scale': config.cfg_scale,
            'seed': config.seed if config.seed > 0 else None,
            'samples': config.batch_size,
            'style_preset': config.style if config.style != 'default' else None
        }