# -*- coding: utf-8 -*-
"""
视频生成引擎工厂
负责创建和管理不同类型的视频生成引擎
"""

from typing import Dict, List, Optional, Type
from .video_engine_base import VideoGenerationEngine, VideoEngineType, VideoEngineStatus
from src.utils.logger import logger
import importlib


class VideoEngineFactory:
    """视频生成引擎工厂类"""
    
    def __init__(self):
        self._engines: Dict[VideoEngineType, VideoGenerationEngine] = {}
        self._engine_classes: Dict[VideoEngineType, Type[VideoGenerationEngine]] = {}
        self._register_default_engines()
    
    def _register_default_engines(self):
        """注册默认引擎类"""
        # 注册引擎类映射
        engine_mappings = {
            VideoEngineType.COGVIDEOX_FLASH: ('cogvideox_engine', 'CogVideoXEngine'),
            VideoEngineType.DOUBAO_SEEDANCE_PRO: ('doubao_engine', 'DoubaoEngine'),
            VideoEngineType.DOUBAO_SEEDANCE_LITE: ('doubao_lite_engine', 'DoubaoLiteEngine'),
            VideoEngineType.REPLICATE_SVD: ('replicate_engine', 'ReplicateVideoEngine'),
            VideoEngineType.PIXVERSE: ('pixverse_engine', 'PixVerseEngine'),
            VideoEngineType.VHEER: ('vheer_engine', 'VheerVideoEngine'),
        }
        
        for engine_type, (module_name, class_name) in engine_mappings.items():
            try:
                module = importlib.import_module(f'.engines.{module_name}', package=__package__)
                engine_class = getattr(module, class_name)
                self._engine_classes[engine_type] = engine_class
                logger.info(f"已注册视频引擎类: {engine_type.value}")
            except (ImportError, AttributeError) as e:
                logger.warning(f"无法加载视频引擎 {engine_type.value}: {e}")
    
    async def create_engine(self, engine_type: VideoEngineType,
                           config: Optional[Dict] = None) -> Optional[VideoGenerationEngine]:
        """创建引擎实例"""
        # 🔧 修复：检查缓存的引擎状态，如果是ERROR状态则尝试重新初始化
        if engine_type in self._engines:
            cached_engine = self._engines[engine_type]
            if cached_engine.status == VideoEngineStatus.ERROR:
                logger.info(f"引擎 {engine_type.value} 处于ERROR状态，尝试重新初始化")
                try:
                    # 尝试重新初始化
                    if await cached_engine.initialize():
                        logger.info(f"引擎 {engine_type.value} 重新初始化成功")
                        return cached_engine
                    else:
                        logger.warning(f"引擎 {engine_type.value} 重新初始化失败，移除缓存")
                        # 重新初始化失败，移除缓存，稍后创建新实例
                        del self._engines[engine_type]
                except Exception as e:
                    logger.warning(f"引擎 {engine_type.value} 重新初始化异常: {e}，移除缓存")
                    del self._engines[engine_type]
            else:
                # 状态正常，直接返回缓存的引擎
                return cached_engine
        
        if engine_type not in self._engine_classes:
            logger.error(f"未找到视频引擎类: {engine_type.value}")
            return None
        
        try:
            engine_class = self._engine_classes[engine_type]
            # 🔧 修复：确保传递正确的配置参数
            engine_config = config or {}
            logger.debug(f"创建引擎 {engine_type.value}，配置: {engine_config}")

            engine = engine_class(engine_config)

            # 初始化引擎
            logger.info(f"正在初始化视频引擎 {engine_type.value}...")
            if await engine.initialize():
                self._engines[engine_type] = engine
                logger.info(f"视频引擎 {engine_type.value} 创建并初始化成功，状态: {engine.status}")
                return engine
            else:
                logger.error(f"视频引擎 {engine_type.value} 初始化失败，状态: {engine.status}")
                return None

        except Exception as e:
            logger.error(f"创建视频引擎 {engine_type.value} 时出错: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None
    
    def get_engine(self, engine_type: VideoEngineType) -> Optional[VideoGenerationEngine]:
        """获取已创建的引擎实例"""
        return self._engines.get(engine_type)
    
    def get_available_engines(self) -> List[VideoEngineType]:
        """获取可用的引擎类型"""
        return list(self._engine_classes.keys())
    
    def get_active_engines(self) -> List[VideoEngineType]:
        """获取已激活的引擎"""
        return [engine_type for engine_type, engine in self._engines.items() 
                if engine.status != VideoEngineStatus.OFFLINE]
    
    def get_engine_statistics(self) -> Dict[VideoEngineType, Dict]:
        """获取所有引擎的统计信息"""
        stats = {}
        for engine_type, engine in self._engines.items():
            stats[engine_type] = engine.get_statistics()
        return stats
    
    async def test_all_engines(self) -> Dict[VideoEngineType, bool]:
        """测试所有引擎连接"""
        results = {}
        for engine_type, engine in self._engines.items():
            try:
                results[engine_type] = await engine.test_connection()
            except Exception as e:
                logger.error(f"测试视频引擎 {engine_type.value} 连接失败: {e}")
                results[engine_type] = False
        return results
    
    async def shutdown_all_engines(self):
        """关闭所有引擎"""
        for engine_type, engine in self._engines.items():
            try:
                if hasattr(engine, 'shutdown'):
                    await engine.shutdown()
                logger.info(f"视频引擎 {engine_type.value} 已关闭")
            except Exception as e:
                logger.error(f"关闭视频引擎 {engine_type.value} 失败: {e}")
        
        self._engines.clear()
    
    def register_custom_engine(self, engine_type: VideoEngineType, 
                              engine_class: Type[VideoGenerationEngine]):
        """注册自定义引擎类"""
        self._engine_classes[engine_type] = engine_class
        logger.info(f"已注册自定义视频引擎: {engine_type.value}")


# 全局工厂实例
video_engine_factory = VideoEngineFactory()


def get_video_engine_factory() -> VideoEngineFactory:
    """获取视频引擎工厂实例"""
    return video_engine_factory
