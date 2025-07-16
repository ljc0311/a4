# -*- coding: utf-8 -*-
"""
图像生成服务 - 多引擎版本
支持多种图像生成引擎：Pollinations、ComfyUI、DALL-E、Stability AI等
"""

import asyncio
from typing import List, Dict, Optional, Callable
from .image_engine_manager import ImageEngineManager, RoutingStrategy, EnginePreference
from .image_engine_base import EngineType, GenerationConfig, GenerationResult
from .image_engine_factory import get_engine_factory
from src.models.llm_api import LLMApi
from src.utils.logger import logger
import os

class ImageGenerationService:
    """多引擎图像生成服务"""
    
    def __init__(self, config: Dict = None):
        """初始化图像生成服务
        
        Args:
            config: 服务配置，包含各引擎的配置信息
        """
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', "output/images")
        
        # 初始化引擎管理器
        self.engine_manager = ImageEngineManager()
        
        # 设置路由策略
        strategy_name = self.config.get('routing_strategy', 'priority')
        try:
            strategy = RoutingStrategy(strategy_name)
            self.engine_manager.set_routing_strategy(strategy)
        except ValueError:
            logger.warning(f"未知的路由策略: {strategy_name}，使用默认策略")
        
        # 不自动创建输出目录，避免生成无用的空文件夹
        
        # 初始化状态
        self._initialized = False
        
        logger.info("多引擎图像生成服务初始化完成")
    
    async def initialize(self) -> bool:
        """初始化服务和所有引擎"""
        if self._initialized:
            return True
        
        try:
            # 获取引擎工厂
            factory = get_engine_factory()
            
            # 根据配置初始化引擎
            # 支持两种配置格式：直接的engines配置或image_generation配置
            engines_config = self.config.get('engines', {})
            if not engines_config and 'image_generation' in self.config:
                engines_config = self.config['image_generation']
            
            # 构建引擎配置字典
            engine_configs = {}
            
            # Pollinations引擎
            if engines_config.get('pollinations', {}).get('enabled', True):
                pollinations_config = engines_config.get('pollinations', {})
                pollinations_config['enabled'] = True
                engine_configs[EngineType.POLLINATIONS] = pollinations_config
            
            # ComfyUI引擎
            comfyui_config = engines_config.get('comfyui', {})
            if comfyui_config.get('enabled', True):
                # 本地ComfyUI
                if comfyui_config.get('local', {}).get('enabled', True):
                    local_config = comfyui_config.get('local', {})
                    local_config['enabled'] = True
                    engine_configs[EngineType.COMFYUI_LOCAL] = local_config
                
                # 云端ComfyUI
                if comfyui_config.get('cloud', {}).get('enabled', False):
                    cloud_config = comfyui_config.get('cloud', {})
                    cloud_config['enabled'] = True
                    engine_configs[EngineType.COMFYUI_CLOUD] = cloud_config
            
            # 付费API引擎
            if engines_config.get('dalle', {}).get('enabled', False):
                dalle_config = engines_config.get('dalle', {})
                dalle_config['enabled'] = True
                engine_configs[EngineType.OPENAI_DALLE] = dalle_config
            
            if engines_config.get('stability', {}).get('enabled', False):
                stability_config = engines_config.get('stability', {})
                stability_config['enabled'] = True
                engine_configs[EngineType.STABILITY_AI] = stability_config
            
            if engines_config.get('imagen', {}).get('enabled', False):
                imagen_config = engines_config.get('imagen', {})
                imagen_config['enabled'] = True
                engine_configs[EngineType.GOOGLE_IMAGEN] = imagen_config

            # CogView-3 Flash (智谱AI免费)
            if engines_config.get('cogview_3_flash', {}).get('enabled', False):
                cogview_config = engines_config.get('cogview_3_flash', {})
                cogview_config['enabled'] = True
                engine_configs[EngineType.COGVIEW_3_FLASH] = cogview_config

            # 初始化所有引擎
            await self.engine_manager.initialize_engines(engine_configs)
            
            # 设置引擎偏好
            preferences = self.config.get('engine_preferences', [])
            if preferences:
                # 将字符串偏好转换为EnginePreference对象
                pref_objects = self._convert_preferences_to_objects(preferences)
                self.engine_manager.update_engine_preferences(pref_objects)
            
            self._initialized = True
            logger.info("图像生成服务初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"图像生成服务初始化失败: {e}")
            return False
    
    def set_output_directory(self, directory: str):
        """设置输出目录"""
        self.output_dir = directory
        # 不自动创建目录，只在实际需要时创建
        logger.info(f"已设置输出目录: {directory}")
    
    async def test_connection(self) -> Dict[str, bool]:
        """测试所有引擎的连接"""
        if not self._initialized:
            await self.initialize()
        
        return await self.engine_manager.test_all_connections()
    
    async def generate_image(self, prompt: str, config: Dict = None,
                           engine_preference: str = None,
                           progress_callback: Optional[Callable] = None,
                           project_manager=None, current_project_name=None) -> GenerationResult:
        """生成图像
        
        Args:
            prompt: 图像描述提示词
            config: 生成配置参数
            progress_callback: 进度回调函数
        
        Returns:
            GenerationResult对象，包含生成结果
        """
        logger.info(f"=== 开始生成图像 ===")
        logger.info(f"提示词: {prompt}")
        logger.info(f"配置: {config}")
        logger.info(f"项目信息: project_manager={project_manager is not None}, current_project_name={current_project_name}")
        
        # 确保服务已初始化
        if not self._initialized:
            await self.initialize()
        
        # 验证输入参数
        if not prompt or not prompt.strip():
            error_msg = "提示词不能为空"
            logger.error(error_msg)
            return GenerationResult(
                success=False,
                error_message=error_msg
            )
        
        try:
            # 构建生成配置
            custom_params = config.get('custom_params', {}) if config else {}
            
            # 将workflow_id添加到custom_params中
            if config and 'workflow_id' in config:
                custom_params['workflow_id'] = config['workflow_id']
            
            # 将UI配置参数添加到custom_params中
            if config:
                # Pollinations特有参数
                if 'enhance' in config:
                    custom_params['enhance'] = config['enhance']
                if 'nologo' in config:
                    custom_params['nologo'] = config['nologo']
            
            generation_config = GenerationConfig(
                prompt=prompt,
                width=config.get('width', 512) if config else 512,
                height=config.get('height', 512) if config else 512,
                steps=config.get('steps', 20) if config else 20,
                cfg_scale=config.get('guidance_scale', 7.5) if config else 7.5,
                seed=config.get('seed', -1) if config else -1,
                negative_prompt=config.get('negative_prompt', '') if config else '',
                model=config.get('model') if config else None,
                style=config.get('style') if config else None,
                custom_params=custom_params
            )
            
            # 使用引擎管理器生成图像
            preferred_engines = None
            if engine_preference:
                # 确保engine_preference是字符串类型
                if isinstance(engine_preference, dict):
                    logger.warning(f"engine_preference应该是字符串，但收到字典: {engine_preference}")
                    # 如果是字典，尝试提取引擎名称或使用默认值
                    engine_preference = "pollinations"  # 默认使用pollinations
                elif not isinstance(engine_preference, str):
                    logger.warning(f"engine_preference类型错误: {type(engine_preference)}, 使用默认值")
                    engine_preference = "pollinations"
                
                # 将引擎偏好字符串转换为EngineType列表
                from .image_engine_base import EngineType
                engine_map = {
                    'pollinations': EngineType.POLLINATIONS,
                    'comfyui_local': EngineType.COMFYUI_LOCAL,
                    'comfyui_cloud': EngineType.COMFYUI_CLOUD,
                    'dalle': EngineType.OPENAI_DALLE,
                    'stability': EngineType.STABILITY_AI,
                    'imagen': EngineType.GOOGLE_IMAGEN,
                    'cogview_3_flash': EngineType.COGVIEW_3_FLASH
                }
                if engine_preference in engine_map:
                    preferred_engines = [engine_map[engine_preference]]
                    logger.info(f"设置引擎偏好: {engine_preference} -> {preferred_engines}")
                else:
                    logger.warning(f"未知的引擎偏好: {engine_preference}, 使用默认引擎")
            
            # 设置引擎的项目信息
            if preferred_engines:
                for engine_type in preferred_engines:
                    engine = self.engine_manager.factory.get_engine(engine_type)
                    if engine and hasattr(engine, 'set_project_info'):
                        engine.set_project_info(project_manager, current_project_name)
            else:
                # 为所有可用引擎设置项目信息
                for engine_type in self.engine_manager.factory.get_active_engines():
                    engine = self.engine_manager.factory.get_engine(engine_type)
                    if engine and hasattr(engine, 'set_project_info'):
                        engine.set_project_info(project_manager, current_project_name)
            
            result = await self.engine_manager.generate_image(
                generation_config, 
                preferred_engines,
                progress_callback,
                project_manager,
                current_project_name
            )
            
            if result.success:
                logger.info(f"图像生成成功，共 {len(result.image_paths)} 张图片")
                logger.info(f"=== 图像生成完成 ===")
            else:
                logger.error(f"图像生成失败: {result.error_message}")
                logger.error(f"=== 图像生成失败 ===")
            
            return result
                
        except Exception as e:
            error_msg = f"图像生成过程中发生异常: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"=== 图像生成异常 ===")
            return GenerationResult(
                success=False,
                error_message=error_msg
            )
    
    def get_available_engines(self) -> List[Dict[str, any]]:
        """获取可用的引擎列表"""
        if not self._initialized:
            return []
        
        engines = []
        # 通过工厂获取已创建的引擎
        for engine_type in self.engine_manager.factory.get_active_engines():
            engine = self.engine_manager.factory.get_engine(engine_type)
            if engine:
                info = engine.get_engine_info()
                engines.append({
                    'type': engine_type.value,
                    'name': info.name,
                    'status': engine.status.value,
                    'is_free': info.is_free,
                    'description': info.description,
                    'supported_sizes': info.supported_sizes,
                    'max_batch_size': info.max_batch_size
                })
        
        return engines
    
    def get_available_models(self, engine_type: str = None) -> Dict[str, List[str]]:
        """获取可用的模型列表"""
        if not self._initialized:
            return {}
        
        models = {}
        
        if engine_type:
            try:
                engine_enum = EngineType(engine_type)
                engine = self.engine_manager.factory.get_engine(engine_enum)
                if engine:
                    models[engine_type] = engine.get_available_models()
            except ValueError:
                logger.warning(f"未知的引擎类型: {engine_type}")
        else:
            for engine_type_enum in self.engine_manager.factory.get_active_engines():
                engine = self.engine_manager.factory.get_engine(engine_type_enum)
                if engine:
                    models[engine_type_enum.value] = engine.get_available_models()
        
        return models
    
    def set_routing_strategy(self, strategy: str) -> bool:
        """设置路由策略"""
        try:
            strategy_enum = RoutingStrategy(strategy)
            self.engine_manager.set_routing_strategy(strategy_enum)
            logger.info(f"路由策略已设置为: {strategy}")
            return True
        except ValueError:
            logger.error(f"无效的路由策略: {strategy}")
            return False
    
    def _convert_preferences_to_objects(self, preferences: List[str]):
        """将字符串偏好转换为EnginePreference对象"""
        from .image_engine_manager import EnginePreference
        pref_objects = []
        priority = 1
        
        for pref in preferences:
            if pref == 'free':
                # 免费引擎：Pollinations, CogView-3 Flash
                pref_objects.append(EnginePreference(
                    engine_type=EngineType.POLLINATIONS,
                    priority=priority,
                    max_cost_per_image=0.0
                ))
                pref_objects.append(EnginePreference(
                    engine_type=EngineType.COGVIEW_3_FLASH,
                    priority=priority + 1,
                    max_cost_per_image=0.0
                ))
            elif pref == 'cogview_3_flash':
                # 直接指定CogView-3 Flash引擎
                pref_objects.append(EnginePreference(
                    engine_type=EngineType.COGVIEW_3_FLASH,
                    priority=priority,
                    max_cost_per_image=0.0
                ))
            elif pref == 'quality':
                # 高质量引擎：DALL-E, Stability AI, Google Imagen
                pref_objects.append(EnginePreference(
                    engine_type=EngineType.OPENAI_DALLE,
                    priority=priority
                ))
                pref_objects.append(EnginePreference(
                    engine_type=EngineType.STABILITY_AI,
                    priority=priority + 1
                ))
                pref_objects.append(EnginePreference(
                    engine_type=EngineType.GOOGLE_IMAGEN,
                    priority=priority + 2
                ))
            elif pref == 'local':
                # 本地引擎：ComfyUI Local
                pref_objects.append(EnginePreference(
                    engine_type=EngineType.COMFYUI_LOCAL,
                    priority=priority
                ))
            priority += 3
        
        return pref_objects
    
    def set_engine_preferences(self, preferences: List[str]) -> bool:
        """设置引擎偏好"""
        try:
            pref_objects = self._convert_preferences_to_objects(preferences)
            self.engine_manager.update_engine_preferences(pref_objects)
            logger.info(f"引擎偏好已设置: {preferences}")
            return True
        except Exception as e:
            logger.error(f"设置引擎偏好失败: {e}")
            return False
    
    async def get_service_status(self) -> Dict:
        """获取服务状态"""
        if not self._initialized:
            await self.initialize()

        status = {
            'initialized': self._initialized,
            'output_directory': self.output_dir,
            'routing_strategy': self.engine_manager.routing_strategy.value,
            'engine_preferences': [pref.engine_type.value for pref in self.engine_manager.engine_preferences],
            'engines': {},
            'manager_status': self.engine_manager.get_manager_status()
        }

        # 获取各引擎状态 - 通过factory获取引擎
        for engine_type in self.engine_manager.factory.get_active_engines():
            engine = self.engine_manager.factory.get_engine(engine_type)
            if engine:
                engine_info = engine.get_engine_info()
                status['engines'][engine_type.value] = {
                    'status': engine.status.value,
                    'name': engine_info.name,
                    'is_free': engine_info.is_free,
                    'last_error': engine.last_error,
                    'performance': getattr(engine, 'performance_stats', {})
                }

        return status
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.engine_manager:
                await self.engine_manager.cleanup()
            
            self._initialized = False
            logger.info("图像生成服务资源清理完成")
        except Exception as e:
            logger.error(f"清理资源时发生异常: {str(e)}")