# -*- coding: utf-8 -*-
"""
视频生成服务 - 多引擎版本
支持多种视频生成引擎：CogVideoX-Flash、Replicate、PixVerse等
"""

import asyncio
from typing import List, Dict, Optional, Callable
from .video_engine_manager import VideoEngineManager, VideoRoutingStrategy, VideoEnginePreference
from .video_engine_base import VideoEngineType, VideoGenerationConfig, VideoGenerationResult
from .video_engine_factory import get_video_engine_factory
from src.utils.logger import logger
import os


class VideoGenerationService:
    """视频生成服务主类"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.manager = VideoEngineManager(self.config)
        self.factory = get_video_engine_factory()
        
        logger.info("视频生成服务初始化完成")
    
    async def generate_video(self,
                           prompt: str = "",
                           image_path: str = "",
                           duration: float = 5.0,
                           fps: int = 24,
                           width: int = 1024,
                           height: int = 1024,
                           motion_intensity: float = 0.5,
                           output_format: str = "mp4",
                           preferred_engines: Optional[List[str]] = None,
                           progress_callback: Optional[Callable] = None,
                           project_manager=None,
                           current_project_name=None,
                           audio_hint: Optional[str] = None) -> VideoGenerationResult:
        """生成视频（简化接口）"""
        
        # 创建生成配置
        config = VideoGenerationConfig(
            input_prompt=prompt,
            input_image_path=image_path,
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            motion_intensity=motion_intensity,
            output_format=output_format,
            output_dir=self.config.get('output_dir', 'output/videos'),
            audio_hint=audio_hint  # 添加音效提示
        )
        
        # 转换引擎名称为枚举
        preferred_engine_types = None
        if preferred_engines:
            preferred_engine_types = []
            for engine_name in preferred_engines:
                try:
                    engine_type = VideoEngineType(engine_name)
                    preferred_engine_types.append(engine_type)
                except ValueError:
                    logger.warning(f"未知的视频引擎: {engine_name}")
        
        return await self.manager.generate_video(
            config=config,
            preferred_engines=preferred_engine_types,
            progress_callback=progress_callback,
            project_manager=project_manager,
            current_project_name=current_project_name
        )
    
    async def generate_video_from_config(self, 
                                       config: VideoGenerationConfig,
                                       preferred_engines: Optional[List[VideoEngineType]] = None,
                                       progress_callback: Optional[Callable] = None,
                                       project_manager=None,
                                       current_project_name=None) -> VideoGenerationResult:
        """使用配置对象生成视频"""
        return await self.manager.generate_video(
            config=config,
            preferred_engines=preferred_engines,
            progress_callback=progress_callback,
            project_manager=project_manager,
            current_project_name=current_project_name
        )
    
    async def batch_generate_videos(self,
                                  configs: List[VideoGenerationConfig],
                                  preferred_engines: Optional[List[VideoEngineType]] = None,
                                  progress_callback: Optional[Callable] = None,
                                  project_manager=None,
                                  current_project_name=None) -> List[VideoGenerationResult]:
        """批量生成视频"""
        results = []
        total_count = len(configs)
        
        for i, config in enumerate(configs):
            try:
                if progress_callback:
                    progress_callback(f"生成视频 {i+1}/{total_count}...")
                
                result = await self.generate_video_from_config(
                    config=config,
                    preferred_engines=preferred_engines,
                    progress_callback=None,  # 不传递内部进度回调
                    project_manager=project_manager,
                    current_project_name=current_project_name
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"批量生成第 {i+1} 个视频失败: {e}")
                results.append(VideoGenerationResult(
                    success=False,
                    error_message=f"生成失败: {e}"
                ))
        
        return results
    
    def get_available_engines(self) -> List[str]:
        """获取可用引擎列表"""
        return [engine_type.value for engine_type in self.factory.get_available_engines()]
    
    def get_engine_info(self, engine_name: str) -> Optional[Dict]:
        """获取引擎信息"""
        try:
            engine_type = VideoEngineType(engine_name)
            engine = self.factory.get_engine(engine_type)
            if engine:
                info = engine.get_engine_info()
                return {
                    'name': info.name,
                    'version': info.version,
                    'description': info.description,
                    'is_free': info.is_free,
                    'supports_image_to_video': info.supports_image_to_video,
                    'supports_text_to_video': info.supports_text_to_video,
                    'max_duration': info.max_duration,
                    'supported_resolutions': info.supported_resolutions,
                    'supported_fps': info.supported_fps,
                    'cost_per_second': info.cost_per_second,
                    'rate_limit': info.rate_limit
                }
        except ValueError:
            logger.warning(f"未知的视频引擎: {engine_name}")
        return None
    
    def get_service_statistics(self) -> Dict:
        """获取服务统计信息"""
        return self.manager.get_engine_statistics()
    
    async def test_engine(self, engine_name: str) -> bool:
        """测试特定引擎"""
        try:
            engine_type = VideoEngineType(engine_name)
            engine_config = self.config.get('engines', {}).get(engine_name, {})
            engine = await self.factory.create_engine(engine_type, engine_config)
            if engine:
                return await engine.test_connection()
        except ValueError:
            logger.warning(f"未知的视频引擎: {engine_name}")
        return False
    
    async def test_all_engines(self) -> Dict[str, bool]:
        """测试所有引擎"""
        results = await self.manager.test_all_engines()
        return {engine_type.value: result for engine_type, result in results.items()}
    
    def set_routing_strategy(self, strategy: str):
        """设置路由策略"""
        try:
            self.manager.routing_strategy = VideoRoutingStrategy(strategy)
            logger.info(f"视频路由策略已设置为: {strategy}")
        except ValueError:
            logger.error(f"无效的路由策略: {strategy}")
    
    def set_engine_preferences(self, preferences: List[str]):
        """设置引擎偏好"""
        try:
            self.manager.engine_preferences = [VideoEnginePreference(pref) for pref in preferences]
            logger.info(f"视频引擎偏好已设置为: {preferences}")
        except ValueError as e:
            logger.error(f"设置引擎偏好失败: {e}")
    
    async def shutdown(self):
        """关闭服务"""
        await self.manager.shutdown()
        logger.info("视频生成服务已关闭")


# 便捷函数
async def generate_video_simple(prompt: str,
                              image_path: str = "",
                              duration: float = 5.0,
                              fps: int = 24,
                              width: int = 1024,
                              height: int = 1024,
                              motion_intensity: float = 0.5,
                              output_dir: str = "output/videos",
                              api_key: str = "") -> VideoGenerationResult:
    """简单的视频生成函数"""
    config = {
        'output_dir': output_dir,
        'engines': {
            'cogvideox_flash': {
                'enabled': True,
                'api_key': api_key
            }
        }
    }

    service = VideoGenerationService(config)

    try:
        result = await service.generate_video(
            prompt=prompt,
            image_path=image_path,
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            motion_intensity=motion_intensity
        )
        return result
    finally:
        await service.shutdown()


async def generate_video_from_image(image_path: str,
                                  prompt: str = "",
                                  duration: float = 5.0,
                                  output_dir: str = "output/videos",
                                  api_key: str = "") -> VideoGenerationResult:
    """从图像生成视频的便捷函数"""
    if not os.path.exists(image_path):
        return VideoGenerationResult(
            success=False,
            error_message=f"输入图像不存在: {image_path}"
        )
    
    return await generate_video_simple(
        prompt=prompt,
        image_path=image_path,
        duration=duration,
        output_dir=output_dir,
        api_key=api_key
    )
