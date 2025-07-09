# -*- coding: utf-8 -*-
"""
OpenAI DALL-E 图像生成引擎实现
"""

import asyncio
import aiohttp
import os
import time
import json
from typing import List, Dict, Optional, Callable
from ..image_engine_base import (
    ImageGenerationEngine, EngineType, EngineStatus, 
    GenerationConfig, GenerationResult, EngineInfo, ConfigConverter
)
from src.utils.logger import logger


class DalleEngine(ImageGenerationEngine):
    """OpenAI DALL-E 引擎实现"""
    
    def __init__(self, config: Dict = None):
        super().__init__(EngineType.OPENAI_DALLE)
        self.config = config or {}
        self.api_key = self.config.get('api_key')
        self.base_url = self.config.get('base_url', 'https://api.openai.com/v1')
        self.model = self.config.get('model', 'dall-e-3')
        self.session: Optional[aiohttp.ClientSession] = None
        self.project_manager = None
        self.current_project_name = None
        self.output_dir = self._get_output_dir()
        
        if not self.api_key:
            logger.warning("DALL-E引擎未配置API密钥")
    
    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            if not self.api_key:
                self.status = EngineStatus.ERROR
                self.last_error = "缺少OpenAI API密钥"
                return False
            
            # 获取输出目录，不在初始化时创建
            self.output_dir = self._get_output_dir()
            
            # 创建HTTP会话
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            timeout = aiohttp.ClientTimeout(total=300)
            self.session = aiohttp.ClientSession(
                headers=headers, 
                timeout=timeout
            )
            
            # 测试连接
            if await self.test_connection():
                self.status = EngineStatus.IDLE
                logger.info("DALL-E引擎初始化成功")
                return True
            else:
                self.status = EngineStatus.ERROR
                logger.error("DALL-E引擎连接测试失败")
                return False
                
        except Exception as e:
            self.status = EngineStatus.ERROR
            self.last_error = str(e)
            logger.error(f"DALL-E引擎初始化失败: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self.session:
                return False
            
            # 测试API连接（获取模型列表）
            async with self.session.get(f"{self.base_url}/models") as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"DALL-E连接测试失败: {e}")
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
                            logger.info("检测到事件循环变化，重新创建DALL-E HTTP会话")
                            await self.session.close()
                            self.session = None
                except RuntimeError:
                    # 没有运行中的事件循环，重新创建会话
                    logger.info("没有运行中的事件循环，重新创建DALL-E HTTP会话")
                    if self.session:
                        await self.session.close()
                    self.session = None

            # 如果会话不存在或已关闭，重新创建
            if not self.session or self.session.closed:
                logger.info("重新创建DALL-E HTTP会话")
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                timeout = aiohttp.ClientTimeout(total=300)
                self.session = aiohttp.ClientSession(
                    headers=headers,
                    timeout=timeout
                )

        except Exception as e:
            logger.warning(f"确保DALL-E会话有效时出错: {e}")
            # 重新创建会话
            if self.session:
                try:
                    await self.session.close()
                except Exception:
                    pass

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
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
                progress_callback("准备DALL-E生成请求...")

            # 转换配置
            dalle_config = ConfigConverter.to_dalle(config)
            
            # 验证配置
            if not self._validate_config(dalle_config):
                raise Exception("配置验证失败")
            
            if progress_callback:
                progress_callback("发送请求到OpenAI...")
            
            # 发送生成请求
            image_urls = await self._generate_images(dalle_config)
            
            if progress_callback:
                progress_callback("下载生成的图像...")
            
            # 下载图像到本地
            image_paths = await self._download_images(image_urls)
            
            generation_time = time.time() - start_time
            success = len(image_paths) > 0
            
            # 计算成本
            cost = self._calculate_cost(dalle_config)
            
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
                    'model': self.model,
                    'dalle_config': dalle_config,
                    'image_urls': image_urls
                }
            )
            
            if not success:
                result.error_message = "未能生成任何图像"
            
            return result
            
        except Exception as e:
            error_msg = f"DALL-E生成失败: {e}"
            logger.error(error_msg)
            self.update_stats(False, 0.0, error_msg)
            
            return GenerationResult(
                success=False,
                error_message=error_msg,
                engine_type=self.engine_type
            )
    
    def _validate_config(self, config: Dict) -> bool:
        """验证配置"""
        # 检查提示词长度
        if len(config['prompt']) > 4000:
            logger.error("DALL-E提示词长度超过4000字符")
            return False
        
        # 检查批次大小
        if config['n'] > 10:
            logger.error("DALL-E批次大小不能超过10")
            return False
        
        return True
    
    async def _generate_images(self, config: Dict) -> List[str]:
        """生成图像并返回URL列表"""
        try:
            # 构建请求数据
            request_data = {
                'model': self.model,
                'prompt': config['prompt'],
                'n': config['n'],
                'size': config['size'],
                'quality': config['quality'],
                'response_format': 'url'
            }
            
            # 添加可选参数
            if 'style' in config and config['style'] != 'natural':
                request_data['style'] = config['style']
            
            logger.debug(f"DALL-E请求数据: {request_data}")
            
            # 发送请求
            async with self.session.post(
                f"{self.base_url}/images/generations",
                json=request_data
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    image_urls = [item['url'] for item in result['data']]
                    logger.info(f"DALL-E生成成功，获得 {len(image_urls)} 个图像URL")
                    return image_urls
                else:
                    error_text = await response.text()
                    logger.error(f"DALL-E API错误: {response.status} - {error_text}")
                    raise Exception(f"API请求失败: {response.status}")
                    
        except Exception as e:
            logger.error(f"DALL-E图像生成失败: {e}")
            raise
    
    async def _download_images(self, image_urls: List[str]) -> List[str]:
        """下载图像到本地"""
        downloaded_paths = []
        
        for i, url in enumerate(image_urls):
            try:
                # 生成本地文件名
                # 使用简洁的文件名，不包含时间戳
                filename = f"dalle_{self.model}_{i}.png"
                # 使用当前的输出目录（可能已更新为项目目录）
                current_output_dir = self._get_output_dir(self.project_manager, self.current_project_name)
                filepath = os.path.join(current_output_dir, filename)
                
                # 下载图像
                async with self.session.get(url) as response:
                    if response.status == 200:
                        with open(filepath, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        downloaded_paths.append(filepath)
                        logger.info(f"图像已下载: {filepath}")
                    else:
                        logger.error(f"下载图像失败: HTTP {response.status}")
                        
            except Exception as e:
                logger.error(f"下载图像 {i} 失败: {e}")
        
        return downloaded_paths
    
    def _calculate_cost(self, config: Dict) -> float:
        """计算生成成本"""
        # DALL-E 3 定价（2024年价格）
        if self.model == 'dall-e-3':
            if config['size'] == '1024x1024':
                if config['quality'] == 'hd':
                    return 0.080 * config['n']  # $0.080 per image
                else:
                    return 0.040 * config['n']
    
    def _get_output_dir(self, project_manager=None, current_project_name=None) -> str:
        """获取输出目录"""
        try:
            # 优先使用传入的项目管理器
            if project_manager and current_project_name:
                project_root = project_manager.get_project_root(current_project_name)
                if project_root:
                    output_dir = os.path.join(project_root, 'images', 'dalle')
                    os.makedirs(output_dir, exist_ok=True)
                    return output_dir
            
            # 尝试使用实例变量
            if self.project_manager and self.current_project_name:
                project_root = self.project_manager.get_project_root(self.current_project_name)
                if project_root:
                    output_dir = os.path.join(project_root, 'images', 'dalle')
                    os.makedirs(output_dir, exist_ok=True)
                    return output_dir
            
            # 尝试获取全局项目管理器
            from src.core.project_manager import ProjectManager
            project_manager = ProjectManager()
            current_project = project_manager.get_current_project()
            
            if current_project:
                project_root = current_project.get('project_root')
                if project_root:
                    output_dir = os.path.join(project_root, 'images', 'dalle')
                    os.makedirs(output_dir, exist_ok=True)
                    return output_dir
        except Exception as e:
            logger.warning(f"无法获取项目目录: {e}")
        
        # 默认输出目录
        default_dir = os.path.join(os.getcwd(), 'output', 'images', 'dalle')
        os.makedirs(default_dir, exist_ok=True)
        return default_dir
    
    def _calculate_cost(self, config: Dict) -> float:
        """计算生成成本"""
        # DALL-E 3 定价
        if self.model == 'dall-e-3':
            if config['size'] == '1024x1024':
                if config['quality'] == 'hd':
                    return 0.080 * config['n']  # $0.080 per image
                else:
                    return 0.040 * config['n']  # $0.040 per image
            elif config['size'] in ['1792x1024', '1024x1792']:
                if config['quality'] == 'hd':
                    return 0.120 * config['n']  # $0.120 per image
                else:
                    return 0.080 * config['n']  # $0.080 per image
        
        # DALL-E 2 定价
        elif self.model == 'dall-e-2':
            if config['size'] == '1024x1024':
                return 0.020 * config['n']  # $0.020 per image
            elif config['size'] == '512x512':
                return 0.018 * config['n']  # $0.018 per image
            elif config['size'] == '256x256':
                return 0.016 * config['n']  # $0.016 per image
        
        # 默认成本
        return 0.040 * config['n']
    
    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        return ['dall-e-3', 'dall-e-2']
    
    def get_engine_info(self) -> EngineInfo:
        """获取引擎信息"""
        return EngineInfo(
            name="OpenAI DALL-E",
            version="3.0",
            description="OpenAI的高质量图像生成模型",
            is_free=False,
            supports_batch=True,
            supports_custom_models=False,
            max_batch_size=10,
            supported_sizes=[
                (1024, 1024), (1792, 1024), (1024, 1792),
                (512, 512), (256, 256)  # DALL-E 2
            ],
            cost_per_image=0.040,  # 平均成本
            rate_limit=50  # 每分钟50次（估计值）
        )
    
    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()
            self.session = None
        
        self.status = EngineStatus.OFFLINE
        await super().cleanup()