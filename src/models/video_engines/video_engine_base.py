# -*- coding: utf-8 -*-
"""
视频生成引擎抽象基类
定义统一的视频生成引擎接口，支持多种视频生成服务
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
import asyncio
from src.utils.logger import logger


class VideoEngineType(Enum):
    """视频引擎类型枚举"""
    COGVIDEOX_FLASH = "cogvideox_flash"
    DOUBAO_SEEDANCE_PRO = "doubao_seedance_pro"
    DOUBAO_SEEDANCE_LITE = "doubao_seedance_lite"
    REPLICATE_SVD = "replicate_svd"
    PIXVERSE = "pixverse"
    HAIPER = "haiper"
    RUNWAY_ML = "runway_ml"
    PIKA_LABS = "pika_labs"
    VHEER = "vheer"


class VideoEngineStatus(Enum):
    """视频引擎状态枚举"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


@dataclass
class VideoGenerationConfig:
    """视频生成配置"""
    # 输入配置
    input_image_path: str = ""
    input_prompt: str = ""
    
    # 视频参数
    duration: float = 5.0  # 视频时长（秒）
    fps: int = 30  # 帧率（修改为CogVideoX支持的默认帧率）
    width: int = 1024  # 宽度
    height: int = 1024  # 高度
    
    # 生成参数
    motion_intensity: float = 0.5  # 运动强度 (0.0-1.0)
    seed: Optional[int] = None  # 随机种子
    guidance_scale: float = 7.5  # 引导强度
    num_inference_steps: int = 50  # 推理步数

    # 音效配置
    audio_hint: Optional[str] = None  # 音效提示，用于CogSound集成

    # 输出配置
    output_format: str = "mp4"  # 输出格式
    output_dir: str = "output/videos"  # 输出目录

    # 引擎特定参数
    engine_specific_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VideoGenerationResult:
    """视频生成结果"""
    success: bool
    video_path: str = ""
    error_message: str = ""
    generation_time: float = 0.0
    cost: float = 0.0
    engine_type: Optional[VideoEngineType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 视频信息
    duration: float = 0.0
    fps: int = 0
    resolution: tuple = (0, 0)
    file_size: int = 0  # 文件大小（字节）


@dataclass
class VideoEngineInfo:
    """视频引擎信息"""
    name: str
    version: str
    description: str
    is_free: bool
    supports_image_to_video: bool
    supports_text_to_video: bool
    max_duration: float  # 最大支持时长（秒）
    supported_resolutions: List[tuple]
    supported_fps: List[int]
    cost_per_second: float = 0.0
    rate_limit: int = 0  # 每分钟请求数限制
    max_concurrent_tasks: int = 1  # 最大并发任务数


class VideoGenerationEngine(ABC):
    """视频生成引擎抽象基类"""
    
    def __init__(self, engine_type: VideoEngineType):
        self.engine_type = engine_type
        self.status = VideoEngineStatus.OFFLINE
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
    async def generate_video(self, config: VideoGenerationConfig, 
                           progress_callback: Optional[Callable] = None,
                           project_manager=None, current_project_name=None) -> VideoGenerationResult:
        """生成视频"""
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
    def get_engine_info(self) -> VideoEngineInfo:
        """获取引擎信息"""
        pass
    
    def get_status(self) -> VideoEngineStatus:
        """获取引擎状态"""
        return self.status
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        success_rate = (self.success_count / self.request_count * 100) if self.request_count > 0 else 0
        return {
            "engine_type": self.engine_type.value,
            "status": self.status.value,
            "request_count": self.request_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": round(success_rate, 2),
            "total_cost": self.total_cost,
            "last_error": self.last_error
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_cost = 0.0
        self.last_error = ""


class ConfigConverter:
    """配置转换器 - 将通用配置转换为引擎特定配置"""
    
    @staticmethod
    def to_engine_config(config: VideoGenerationConfig, engine_type: VideoEngineType) -> Dict[str, Any]:
        """转换为引擎特定配置"""
        base_config = {
            "input_image": config.input_image_path,
            "prompt": config.input_prompt,
            "duration": config.duration,
            "fps": config.fps,
            "width": config.width,
            "height": config.height,
            "motion_intensity": config.motion_intensity,
            "seed": config.seed,
            "output_format": config.output_format
        }
        
        # 合并引擎特定参数
        base_config.update(config.engine_specific_params)
        
        return base_config
