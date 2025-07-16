# -*- coding: utf-8 -*-
"""
Stability AI 图像生成引擎实现
"""

import asyncio
import aiohttp
import os
import time
import base64
from typing import List, Dict, Optional, Callable
from ..image_engine_base import (
    ImageGenerationEngine, EngineType, EngineStatus, 
    GenerationConfig, GenerationResult, EngineInfo, ConfigConverter
)
from src.utils.logger import logger


class StabilityEngine(ImageGenerationEngine):
    """Stability AI 引擎实现"""
    
    def __init__(self, config: Dict = None):
        super().__init__(EngineType.STABILITY_AI)
        self.config = config or {}
        self.api_key = self.config.get('api_key')
        self.base_url = self.config.get('base_url', 'https://api.stability.ai')
        self.engine_id = self.config.get('engine_id', 'stable-diffusion-xl-1024-v1-0')
        self.session: Optional[aiohttp.ClientSession] = None
        self.project_manager = None
        self.current_project_name = None
        self.output_dir = self._get_output_dir()
        
        if not self.api_key:
            logger.warning("Stability AI引擎未配置API密钥")
    
    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            if not self.api_key:
                self.status = EngineStatus.ERROR
                self.last_error = "缺少Stability AI API密钥"
                return False
            
            # 获取输出目录，不在初始化时创建
            self.output_dir = self._get_output_dir()
            
            # 创建HTTP会话
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            timeout = aiohttp.ClientTimeout(total=300)
            self.session = aiohttp.ClientSession(
                headers=headers, 
                timeout=timeout
            )
            
            # 测试连接
            if await self.test_connection():
                self.status = EngineStatus.IDLE
                logger.info("Stability AI引擎初始化成功")
                return True
            else:
                self.status = EngineStatus.ERROR
                logger.error("Stability AI引擎连接测试失败")
                return False
                
        except Exception as e:
            self.status = EngineStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Stability AI引擎初始化失败: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self.session:
                return False
            
            # 测试API连接（获取用户信息）
            async with self.session.get(f"{self.base_url}/v1/user/account") as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Stability AI连接测试失败: {e}")
            return False

    async def _ensure_session_valid(self):
        """确保HTTP会话在当前事件循环中有效"""
        try:
            # 检查会话是否存在且未关闭
            if self.session and not self.session.closed:
                try:
                    # 尝试获取当前事件循环
                    current_loop = asyncio.get_running_loop()
                    # 检查会话是否在当前事件循环中
                    if hasattr(self.session, '_connector') and hasattr(self.session._connector, '_loop'):
                        session_loop = self.session._connector._loop
                        if session_loop != current_loop:
                            logger.info("检测到事件循环变化，重新创建Stability AI HTTP会话")
                            await self.session.close()
                            self.session = None
                except RuntimeError:
                    # 没有运行中的事件循环，重新创建会话
                    logger.info("没有运行中的事件循环，重新创建Stability AI HTTP会话")
                    if self.session:
                        await self.session.close()
                    self.session = None

            # 如果会话不存在或已关闭，重新创建
            if not self.session or self.session.closed:
                logger.info("重新创建Stability AI HTTP会话")
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                timeout = aiohttp.ClientTimeout(total=300)
                self.session = aiohttp.ClientSession(
                    headers=headers,
                    timeout=timeout
                )

        except Exception as e:
            logger.warning(f"确保Stability AI会话有效时出错: {e}")
            # 重新创建会话
            if self.session:
                try:
                    await self.session.close()
                except Exception:
                    pass

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            timeout = aiohttp.ClientTimeout(total=300)
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )

    async def generate(self, config: GenerationConfig,
                      progress_callback: Optional[Callable] = None,
                      project_manager=None, current_project_name=None) -> GenerationResult:
        """生成图像"""
        start_time = time.time()
        self.status = EngineStatus.BUSY
        
        # 设置项目信息
        if project_manager and current_project_name:
            self.project_manager = project_manager
            self.current_project_name = current_project_name
            # 更新输出目录
            self.output_dir = self._get_output_dir(project_manager, current_project_name)
        
        try:
            # 确保HTTP会话在当前事件循环中有效
            await self._ensure_session_valid()

            if progress_callback:
                progress_callback("准备Stability AI生成请求...")

            # 转换配置
            stability_config = ConfigConverter.to_stability(config)
            
            # 验证配置
            if not self._validate_config(stability_config):
                raise Exception("配置验证失败")
            
            if progress_callback:
                progress_callback("发送请求到Stability AI...")
            
            # 生成图像
            image_data_list = await self._generate_images(stability_config)
            
            if progress_callback:
                progress_callback("保存生成的图像...")
            
            # 保存图像到本地
            image_paths = await self._save_images(image_data_list)
            
            generation_time = time.time() - start_time
            success = len(image_paths) > 0
            
            # 计算成本
            cost = self._calculate_cost(stability_config)
            
            # 更新统计
            error_msg = "" if success else "生成失败"
            self.update_stats(success, cost, error_msg)
            
            result = GenerationResult(
                success=success,
                image_paths=image_paths,
                generation_time=generation_time,
                cost=cost,
                engine_type=self.engine_type,
                metadata={
                    'engine_id': self.engine_id,
                    'stability_config': stability_config
                }
            )
            
            if not success:
                result.error_message = "未能生成任何图像"
            
            return result
            
        except Exception as e:
            error_msg = f"Stability AI生成失败: {e}"
            logger.error(error_msg)
            self.update_stats(False, 0.0, error_msg)
            
            return GenerationResult(
                success=False,
                error_message=error_msg,
                engine_type=self.engine_type
            )
    
    def _validate_config(self, config: Dict) -> bool:
        """验证配置"""
        # 检查尺寸
        width = config['width']
        height = config['height']
        
        # Stability AI支持的尺寸范围
        if width < 128 or width > 1536 or height < 128 or height > 1536:
            logger.error(f"不支持的图像尺寸: {width}x{height}")
            return False
        
        # 检查宽高比
        aspect_ratio = width / height
        if aspect_ratio < 0.5 or aspect_ratio > 2.0:
            logger.error(f"不支持的宽高比: {aspect_ratio}")
            return False
        
        # 检查批次大小
        if config['samples'] > 10:
            logger.error("Stability AI批次大小不能超过10")
            return False
        
        return True
    
    async def _generate_images(self, config: Dict) -> List[bytes]:
        """生成图像并返回图像数据列表"""
        try:
            # 构建请求数据
            request_data = {
                'text_prompts': config['text_prompts'],
                'cfg_scale': config['cfg_scale'],
                'height': config['height'],
                'width': config['width'],
                'samples': config['samples'],
                'steps': config['steps']
            }
            
            # 添加可选参数
            if config.get('seed') is not None:
                request_data['seed'] = config['seed']
            
            if config.get('style_preset'):
                request_data['style_preset'] = config['style_preset']
            
            logger.debug(f"Stability AI请求数据: {request_data}")
            
            # 发送请求
            url = f"{self.base_url}/v1/generation/{self.engine_id}/text-to-image"
            async with self.session.post(url, json=request_data) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # 解码base64图像数据
                    image_data_list = []
                    for artifact in result['artifacts']:
                        if artifact['finishReason'] == 'SUCCESS':
                            image_data = base64.b64decode(artifact['base64'])
                            image_data_list.append(image_data)
                    
                    logger.info(f"Stability AI生成成功，获得 {len(image_data_list)} 张图像")
                    return image_data_list
                    
                else:
                    error_text = await response.text()
                    logger.error(f"Stability AI API错误: {response.status} - {error_text}")
                    raise Exception(f"API请求失败: {response.status}")
                    
        except Exception as e:
            logger.error(f"Stability AI图像生成失败: {e}")
            raise
    
    async def _save_images(self, image_data_list: List[bytes]) -> List[str]:
        """保存图像到本地"""
        saved_paths = []
        
        for i, image_data in enumerate(image_data_list):
            try:
                # 生成本地文件名
                # 使用简洁的文件名，不包含时间戳
                filename = f"stability_{self.engine_id}_{i}.png"
                # 使用当前的输出目录（可能已更新为项目目录）
                current_output_dir = self._get_output_dir(self.project_manager, self.current_project_name)
                filepath = os.path.join(current_output_dir, filename)
                
                # 保存图像
                with open(filepath, 'wb') as f:
                    f.write(image_data)
                
                saved_paths.append(filepath)
                logger.info(f"图像已保存: {filepath}")
                
            except Exception as e:
                logger.error(f"保存图像 {i} 失败: {e}")
        
        return saved_paths
    
    def _calculate_cost(self, config: Dict) -> float:
        """计算生成成本"""
        # Stability AI定价（基于引擎和步数）
        base_costs = {
            'stable-diffusion-xl-1024-v1-0': 0.040,
            'stable-diffusion-v1-6': 0.020,
            'stable-diffusion-512-v2-1': 0.020,
            'stable-diffusion-xl-beta-v2-2-2': 0.040
        }
        
        base_cost = base_costs.get(self.engine_id, 0.030)
        
        # 步数影响成本
        steps_multiplier = config['steps'] / 30  # 基准30步
        
        # 尺寸影响成本
        pixel_count = config['width'] * config['height']
        size_multiplier = pixel_count / (1024 * 1024)  # 基准1024x1024
        
        return base_cost * steps_multiplier * size_multiplier * config['samples']
    
    def _get_output_dir(self, project_manager=None, current_project_name=None) -> str:
        """获取输出目录"""
        try:
            # 优先使用传入的项目管理器
            if project_manager and current_project_name:
                project_root = project_manager.get_project_root(current_project_name)
                if project_root:
                    output_dir = os.path.join(project_root, 'images', 'stability')
                    os.makedirs(output_dir, exist_ok=True)
                    return output_dir
            
            # 尝试使用实例变量
            if self.project_manager and self.current_project_name:
                project_root = self.project_manager.get_project_root(self.current_project_name)
                if project_root:
                    output_dir = os.path.join(project_root, 'images', 'stability')
                    os.makedirs(output_dir, exist_ok=True)
                    return output_dir
            
            # 尝试获取全局项目管理器
            from src.core.project_manager import ProjectManager
            project_manager = ProjectManager()
            current_project = project_manager.get_current_project()
            
            if current_project:
                project_root = current_project.get('project_root')
                if project_root:
                    output_dir = os.path.join(project_root, 'images', 'stability')
                    os.makedirs(output_dir, exist_ok=True)
                    return output_dir
        except Exception as e:
            logger.warning(f"无法获取项目目录: {e}")
        
        # 默认输出目录
        default_dir = os.path.join(os.getcwd(), 'output', 'images', 'stability')
        os.makedirs(default_dir, exist_ok=True)
        return default_dir
    
    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        return [
            'stable-diffusion-xl-1024-v1-0',
            'stable-diffusion-v1-6',
            'stable-diffusion-512-v2-1',
            'stable-diffusion-xl-beta-v2-2-2',
            'stable-diffusion-depth-v2-0',
            'stable-inpainting-v1-0',
            'stable-inpainting-512-v2-0'
        ]
    
    def get_engine_info(self) -> EngineInfo:
        """获取引擎信息"""
        return EngineInfo(
            name="Stability AI",
            version="1.0",
            description="Stability AI的Stable Diffusion模型服务",
            is_free=False,
            supports_batch=True,
            supports_custom_models=False,
            max_batch_size=10,
            supported_sizes=[
                (512, 512), (768, 768), (1024, 1024),
                (1024, 768), (768, 1024),
                (1536, 1024), (1024, 1536),
                (1280, 720), (720, 1280)
            ],
            cost_per_image=0.030,  # 平均成本
            rate_limit=150  # 每分钟150次
        )
    
    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()
            self.session = None
        
        self.status = EngineStatus.OFFLINE
        await super().cleanup()