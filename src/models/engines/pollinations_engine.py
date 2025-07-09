"""
Pollinations AI 图像生成引擎实现
"""

import asyncio
import requests
import os
import time
import urllib.parse
from typing import List, Dict, Optional, Callable
from ..image_engine_base import (
    ImageGenerationEngine, EngineType, EngineStatus, 
    GenerationConfig, GenerationResult, EngineInfo, ConfigConverter
)
from src.utils.logger import logger


class PollinationsEngine(ImageGenerationEngine):
    """Pollinations AI 引擎实现"""
    
    def __init__(self, config: Dict = None):
        super().__init__(EngineType.POLLINATIONS)
        self.config = config or {}
        self.base_url = "https://image.pollinations.ai/prompt"
        # 默认输出目录，会在生成时动态更新
        self.output_dir = self.config.get('output_dir', 'temp/image_cache')
        self.session = None
        # 项目相关信息
        self.project_manager = None
        self.current_project_name = None
        
    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            # 动态获取输出目录
            self.output_dir = self._get_output_dir()
            # 不在初始化时创建目录，只在实际生成图像时创建
            
            # 创建requests会话
            self.session = requests.Session()
            self.session.timeout = 30  # 设置超时
            
            # 测试连接
            if await self.test_connection():
                self.status = EngineStatus.IDLE
                logger.info("Pollinations引擎初始化成功")
                return True
            else:
                self.status = EngineStatus.ERROR
                logger.error("Pollinations引擎连接测试失败")
                return False
                
        except Exception as e:
            self.status = EngineStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Pollinations引擎初始化失败: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self.session:
                return False
                
            # 发送简单的测试请求
            test_url = f"{self.base_url}/test?width=64&height=64"
            response = self.session.get(test_url, timeout=10)
            return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Pollinations连接测试失败: {e}")
            return False
    
    def set_project_info(self, project_manager=None, current_project_name=None):
        """设置项目信息"""
        self.project_manager = project_manager
        self.current_project_name = current_project_name
        logger.info(f"Pollinations引擎设置项目信息: project_manager={project_manager is not None}, current_project_name={current_project_name}")
    
    def _get_output_dir(self, project_manager=None, current_project_name=None) -> str:
        """获取输出目录"""
        try:
            # 优先使用传入的项目管理器
            if project_manager and current_project_name:
                try:
                    # 尝试使用get_current_project_path方法
                    project_root = project_manager.get_current_project_path()
                    if project_root:
                        output_dir = os.path.join(project_root, 'images', 'pollinations')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"使用项目输出目录: {output_dir}")
                        return output_dir
                except AttributeError:
                    # 如果没有get_current_project_path方法，尝试其他方法
                    if hasattr(project_manager, 'current_project') and project_manager.current_project:
                        project_root = project_manager.current_project.get('project_dir')
                        if project_root:
                            output_dir = os.path.join(project_root, 'images', 'pollinations')
                            os.makedirs(output_dir, exist_ok=True)
                            logger.info(f"使用项目输出目录: {output_dir}")
                            return output_dir

            # 尝试使用实例变量
            if self.project_manager:
                try:
                    # 使用get_current_project_path方法获取当前项目路径
                    project_root = self.project_manager.get_current_project_path()
                    if project_root:
                        output_dir = os.path.join(project_root, 'images', 'pollinations')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"使用项目输出目录: {output_dir}")
                        return output_dir
                    else:
                        logger.info("当前没有加载项目，使用默认目录")
                except AttributeError:
                    # 如果没有get_current_project_path方法，尝试其他方法
                    if hasattr(self.project_manager, 'current_project') and self.project_manager.current_project:
                        project_root = self.project_manager.current_project.get('project_dir')
                        if project_root:
                            output_dir = os.path.join(project_root, 'images', 'pollinations')
                            os.makedirs(output_dir, exist_ok=True)
                            logger.info(f"使用项目输出目录: {output_dir}")
                            return output_dir
                except Exception as e:
                    logger.warning(f"获取项目路径失败: {e}，使用默认目录")

        except Exception as e:
            logger.warning(f"无法获取项目目录: {e}")

        # 无项目时使用temp/image_cache
        output_dir = os.path.join(os.getcwd(), 'temp', 'image_cache', 'pollinations')
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"使用默认输出目录: {output_dir}")
        return output_dir
    
    async def generate(self, config: GenerationConfig, 
                      progress_callback: Optional[Callable] = None,
                      project_manager=None, current_project_name=None) -> GenerationResult:
        """生成图像"""
        # 设置项目信息
        if project_manager and current_project_name:
            self.project_manager = project_manager
            self.current_project_name = current_project_name
            # 更新输出目录
            self.output_dir = self._get_output_dir()
        
        start_time = time.time()
        self.status = EngineStatus.BUSY
        
        try:
            if progress_callback:
                progress_callback("准备Pollinations生成请求...")
            
            # 转换配置
            pollinations_config = ConfigConverter.to_pollinations(config)
            
            # 生成图像
            image_paths = []
            for i in range(config.batch_size):
                if progress_callback:
                    progress_callback(f"生成第 {i+1}/{config.batch_size} 张图像...")
                
                image_path = await self._generate_single_image(pollinations_config, i)
                if image_path:
                    image_paths.append(image_path)
                else:
                    # 单张失败不影响其他图像生成
                    logger.warning(f"第 {i+1} 张图像生成失败")
            
            generation_time = time.time() - start_time
            success = len(image_paths) > 0
            
            # 更新统计
            self.update_stats(success, 0.0, "" if success else "部分或全部图像生成失败")
            
            result = GenerationResult(
                success=success,
                image_paths=image_paths,
                generation_time=generation_time,
                cost=0.0,  # Pollinations免费
                engine_type=self.engine_type,
                metadata={
                    'total_requested': config.batch_size,
                    'total_generated': len(image_paths),
                    'config': pollinations_config
                }
            )
            
            if not success:
                result.error_message = f"仅生成了 {len(image_paths)}/{config.batch_size} 张图像"
            
            return result
            
        except Exception as e:
            error_msg = f"Pollinations生成失败: {e}"
            logger.error(error_msg)
            self.update_stats(False, 0.0, error_msg)
            
            return GenerationResult(
                success=False,
                error_message=error_msg,
                engine_type=self.engine_type
            )
        finally:
            self.status = EngineStatus.IDLE
    
    async def _generate_single_image(self, config: Dict, index: int) -> Optional[str]:
        """生成单张图像"""
        try:
            # 构建请求参数 - 只包含Pollinations API支持的参数
            params = {
                'width': config['width'],
                'height': config['height'],
                'model': config.get('model', 'flux'),
                'nologo': str(config.get('nologo', True)).lower(),
                'enhance': str(config.get('enhance', False)).lower(),
                'safe': str(config.get('safe', True)).lower()
            }

            # 添加seed参数（如果存在）
            if config.get('seed') is not None:
                params['seed'] = config['seed'] + index  # 为每张图像使用不同种子

            # 添加private参数（如果存在）
            if config.get('private') is not None:
                params['private'] = str(config.get('private', False)).lower()

            # 记录实际发送的参数
            logger.info(f"Pollinations API 请求参数: {params}")

            # URL编码提示词
            encoded_prompt = urllib.parse.quote(config['prompt'])
            url = f"{self.base_url}/{encoded_prompt}"

            # 发送请求 - 使用requests而不是aiohttp
            response = self.session.get(url, params=params, timeout=60)

            if response.status_code == 200:
                # 动态获取输出目录
                current_output_dir = self._get_output_dir()
                os.makedirs(current_output_dir, exist_ok=True)

                # 🔧 修复：使用workflow_id生成唯一文件名，避免覆盖
                workflow_id = config.get('workflow_id', f'shot_{index}')
                # 将workflow_id中的特殊字符替换为下划线，确保文件名安全
                safe_workflow_id = workflow_id.replace('-', '_').replace(':', '_')
                filename = f"pollinations_{safe_workflow_id}.png"
                filepath = os.path.join(current_output_dir, filename)

                with open(filepath, 'wb') as f:
                    f.write(response.content)

                logger.info(f"图像已保存: {filepath}")
                return filepath
            else:
                logger.error(f"Pollinations请求失败: HTTP {response.status_code}")
                logger.error(f"请求URL: {url}")
                logger.error(f"请求参数: {params}")
                return None

        except Exception as e:
            logger.error(f"生成单张图像失败: {e}")
            return None
    
    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        return [
            'flux',
            'flux-realism', 
            'flux-cablyai',
            'flux-anime',
            'flux-3d',
            'any-dark',
            'flux-pro'
        ]
    
    def get_engine_info(self) -> EngineInfo:
        """获取引擎信息"""
        return EngineInfo(
            name="Pollinations AI",
            version="1.0",
            description="免费的AI图像生成服务，支持多种模型",
            is_free=True,
            supports_batch=True,
            supports_custom_models=False,
            max_batch_size=10,
            supported_sizes=[
                (512, 512), (768, 768), (1024, 1024),
                (1024, 768), (768, 1024),
                (1280, 720), (720, 1280)
            ],
            cost_per_image=0.0,
            rate_limit=60  # 估计值
        )
    
    async def cleanup(self):
        """清理资源"""
        if self.session:
            self.session.close()
            self.session = None
        
        self.status = EngineStatus.OFFLINE
        await super().cleanup()