# -*- coding: utf-8 -*-
"""
图像生成引擎工厂
负责创建和管理不同类型的图像生成引擎
"""

from typing import Dict, List, Optional, Type
from .image_engine_base import ImageGenerationEngine, EngineType, EngineStatus
from src.utils.logger import logger
import importlib


class EngineFactory:
    """图像生成引擎工厂类"""
    
    def __init__(self):
        self._engines: Dict[EngineType, ImageGenerationEngine] = {}
        self._engine_classes: Dict[EngineType, Type[ImageGenerationEngine]] = {}
        self._register_default_engines()
    
    def _register_default_engines(self):
        """注册默认引擎类"""
        # 注册引擎类映射
        engine_mappings = {
            EngineType.POLLINATIONS: ('pollinations_engine', 'PollinationsEngine'),
            EngineType.COMFYUI_LOCAL: ('comfyui_engine', 'ComfyUILocalEngine'),
            EngineType.COMFYUI_CLOUD: ('comfyui_engine', 'ComfyUICloudEngine'),
            EngineType.OPENAI_DALLE: ('dalle_engine', 'DalleEngine'),
            EngineType.GOOGLE_IMAGEN: ('imagen_engine', 'ImagenEngine'),
            EngineType.STABILITY_AI: ('stability_engine', 'StabilityEngine'),
            EngineType.COGVIEW_3_FLASH: ('cogview_3_flash_engine', 'CogView3FlashEngine'),
            EngineType.VHEER: ('vheer_engine', 'VheerEngine')
        }
        
        for engine_type, (module_name, class_name) in engine_mappings.items():
            try:
                module = importlib.import_module(f'src.models.engines.{module_name}')
                engine_class = getattr(module, class_name)
                self._engine_classes[engine_type] = engine_class
                logger.info(f"已注册引擎类: {engine_type.value}")
            except (ImportError, AttributeError) as e:
                logger.warning(f"无法加载引擎 {engine_type.value}: {e}")
    
    async def create_engine(self, engine_type: EngineType, 
                           config: Optional[Dict] = None) -> Optional[ImageGenerationEngine]:
        """创建引擎实例"""
        if engine_type in self._engines:
            return self._engines[engine_type]
        
        if engine_type not in self._engine_classes:
            logger.error(f"未找到引擎类: {engine_type.value}")
            return None
        
        try:
            engine_class = self._engine_classes[engine_type]
            engine = engine_class(config or {})
            
            # 初始化引擎
            if await engine.initialize():
                self._engines[engine_type] = engine
                logger.info(f"引擎 {engine_type.value} 创建成功")
                return engine
            else:
                logger.error(f"引擎 {engine_type.value} 初始化失败")
                return None
                
        except Exception as e:
            logger.error(f"创建引擎 {engine_type.value} 时出错: {e}")
            return None
    
    def get_engine(self, engine_type: EngineType) -> Optional[ImageGenerationEngine]:
        """获取已创建的引擎实例"""
        return self._engines.get(engine_type)
    
    def get_available_engines(self) -> List[EngineType]:
        """获取可用的引擎类型"""
        return list(self._engine_classes.keys())
    
    def get_active_engines(self) -> List[EngineType]:
        """获取已激活的引擎"""
        return [engine_type for engine_type, engine in self._engines.items() 
                if engine.status != EngineStatus.OFFLINE]
    
    def get_engines_status(self) -> Dict[str, Dict]:
        """获取所有引擎状态"""
        status = {}
        for engine_type in self._engine_classes.keys():
            if engine_type in self._engines:
                status[engine_type.value] = self._engines[engine_type].get_status()
            else:
                status[engine_type.value] = {
                    'engine_type': engine_type.value,
                    'status': 'not_created',
                    'available': True
                }
        return status
    
    async def remove_engine(self, engine_type: EngineType):
        """移除引擎实例"""
        if engine_type in self._engines:
            engine = self._engines[engine_type]
            await engine.cleanup()
            del self._engines[engine_type]
            logger.info(f"引擎 {engine_type.value} 已移除")
    
    async def cleanup_all(self):
        """清理所有引擎"""
        for engine_type in list(self._engines.keys()):
            await self.remove_engine(engine_type)
        logger.info("所有引擎已清理完成")
    
    def register_custom_engine(self, engine_type: EngineType, 
                              engine_class: Type[ImageGenerationEngine]):
        """注册自定义引擎类"""
        self._engine_classes[engine_type] = engine_class
        logger.info(f"已注册自定义引擎: {engine_type.value}")


# 全局工厂实例
engine_factory = EngineFactory()


def get_engine_factory() -> EngineFactory:
    """获取引擎工厂实例"""
    return engine_factory