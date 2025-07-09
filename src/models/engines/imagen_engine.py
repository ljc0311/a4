# -*- coding: utf-8 -*-
"""
Google Imagen 图像生成引擎实现
注意：这是一个占位符实现，Google Imagen API可能需要特殊访问权限
"""

import asyncio
import aiohttp
import os
import time
from typing import List, Dict, Optional, Callable
from ..image_engine_base import (
    ImageGenerationEngine, EngineType, EngineStatus, 
    GenerationConfig, GenerationResult, EngineInfo
)
from src.utils.logger import logger


class ImagenEngine(ImageGenerationEngine):
    """Google Imagen 引擎实现（使用Gemini API）"""
    
    def __init__(self, config: Dict = None):
        super().__init__(EngineType.GOOGLE_IMAGEN)
        self.config = config or {}
        self.api_key = self.config.get('api_key')
        self.project_id = self.config.get('project_id', '')  # 项目ID可选
        self.base_url = self.config.get('base_url', 'https://generativelanguage.googleapis.com')
        self.model = self.config.get('model', 'imagen-3.0-generate-001')
        self.session: Optional[aiohttp.ClientSession] = None
        self.project_manager = None
        self.current_project_name = None
        self.output_dir = self._get_output_dir()
        
        if not self.api_key:
            logger.warning("Google Imagen引擎未配置API密钥")
    
    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            if not self.api_key:
                self.status = EngineStatus.ERROR
                self.last_error = "缺少Google Gemini API密钥"
                return False
            
            # 获取输出目录，不在初始化时创建
            self.output_dir = self._get_output_dir()
            
            # 创建HTTP会话（Gemini API使用查询参数传递API密钥）
            headers = {
                'Content-Type': 'application/json'
            }
            timeout = aiohttp.ClientTimeout(total=300)
            self.session = aiohttp.ClientSession(
                headers=headers, 
                timeout=timeout
            )
            
            # 测试API连接
            test_result = await self._test_connection()
            if test_result:
                self.status = EngineStatus.READY
                logger.info("Google Imagen引擎初始化成功")
                return True
            else:
                self.status = EngineStatus.ERROR
                return False
                
        except Exception as e:
            self.status = EngineStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Google Imagen引擎初始化失败: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """内部连接测试方法"""
        try:
            # 测试Gemini API连接
            url = f"{self.base_url}/v1beta/models?key={self.api_key}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    logger.info("Google Gemini API连接测试成功")
                    return True
                else:
                    self.last_error = f"API连接失败，状态码: {response.status}"
                    logger.error(self.last_error)
                    return False
                    
        except Exception as e:
            self.last_error = f"连接测试异常: {str(e)}"
            logger.error(f"Google Gemini连接测试失败: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试连接"""
        return await self._test_connection()
    
    async def generate(self, config: GenerationConfig, 
                      progress_callback: Optional[Callable] = None,
                      project_manager=None, current_project_name=None) -> GenerationResult:
        """生成图像"""
        # 设置项目信息
        if project_manager and current_project_name:
            self.project_manager = project_manager
            self.current_project_name = current_project_name
            # 更新输出目录
            self.output_dir = self._get_output_dir(project_manager, current_project_name)
        
        try:
            if self.status != EngineStatus.READY:
                return GenerationResult(
                    success=False,
                    error_message="引擎未就绪",
                    engine_type=self.engine_type
                )
            
            if progress_callback:
                progress_callback(0, "开始生成图像...")
            
            # 构建请求数据
            request_data = {
                "prompt": {
                    "text": config.prompt
                },
                "sampleCount": config.num_images or 1,
                "aspectRatio": self._get_aspect_ratio(config.width, config.height),
                "safetyFilterLevel": "BLOCK_SOME",
                "personGeneration": "ALLOW_ADULT"
            }
            
            if config.negative_prompt:
                request_data["prompt"]["negativeText"] = config.negative_prompt
            
            # 发送请求
            url = f"{self.base_url}/v1beta/models/{self.model}:generateImages?key={self.api_key}"
            
            if progress_callback:
                progress_callback(30, "发送生成请求...")
            
            async with self.session.post(url, json=request_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return GenerationResult(
                        success=False,
                        error_message=f"API请求失败: {response.status} - {error_text}",
                        engine_type=self.engine_type
                    )
                
                result_data = await response.json()
                
                if progress_callback:
                    progress_callback(70, "处理生成结果...")
                
                # 处理响应
                image_paths = await self._process_response(result_data, config)
                
                if progress_callback:
                    progress_callback(100, "图像生成完成")
                
                return GenerationResult(
                    success=True,
                    image_paths=image_paths,
                    engine_type=self.engine_type,
                    generation_time=time.time() - time.time()  # 简化的时间计算
                )
                
        except Exception as e:
            error_msg = f"图像生成失败: {str(e)}"
            logger.error(error_msg)
            return GenerationResult(
                success=False,
                error_message=error_msg,
                engine_type=self.engine_type
            )
    
    def _get_aspect_ratio(self, width: int, height: int) -> str:
        """根据宽高获取宽高比字符串"""
        if width == height:
            return "ASPECT_RATIO_SQUARE"
        elif width > height:
            if width / height >= 1.5:
                return "ASPECT_RATIO_LANDSCAPE"
            else:
                return "ASPECT_RATIO_SQUARE"
        else:
            if height / width >= 1.5:
                return "ASPECT_RATIO_PORTRAIT"
            else:
                return "ASPECT_RATIO_SQUARE"
    
    async def _process_response(self, result_data: Dict, config: GenerationConfig) -> List[str]:
        """处理API响应并保存图像"""
        image_paths = []
        
        try:
            if 'generatedImages' not in result_data:
                logger.error(f"API响应格式错误: {result_data}")
                return image_paths
            
            for i, image_data in enumerate(result_data['generatedImages']):
                if 'bytesBase64Encoded' in image_data:
                    # 解码base64图像数据
                    import base64
                    image_bytes = base64.b64decode(image_data['bytesBase64Encoded'])
                    
                    # 生成文件名
                    # 使用简洁的文件名，不包含时间戳
                    filename = f"imagen_{i+1}.png"
                    # 使用当前的输出目录（可能已更新为项目目录）
                    current_output_dir = self._get_output_dir(self.project_manager, self.current_project_name)
                    filepath = os.path.join(current_output_dir, filename)
                    
                    # 保存图像
                    with open(filepath, 'wb') as f:
                        f.write(image_bytes)
                    
                    image_paths.append(filepath)
                    logger.info(f"图像已保存: {filepath}")
                
        except Exception as e:
            logger.error(f"处理图像响应失败: {e}")
        
        return image_paths
     
    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        # 基于Gemini API的Imagen模型
        return [
            'imagen-3.0-generate-001',
            'imagen-3.0-fast-generate-001'
        ]
    
    def get_engine_info(self) -> EngineInfo:
        """获取引擎信息"""
        return EngineInfo(
            name="Google Imagen (Gemini API)",
            version="3.0",
            description="基于Gemini API的Google Imagen高质量图像生成模型",
            is_free=False,
            supports_batch=True,
            supports_custom_models=False,
            max_batch_size=4,
            supported_sizes=[
                (256, 256), (512, 512), (1024, 1024),
                (1024, 768), (768, 1024)
            ],
            cost_per_image=0.040,  # 根据配置的成本
            rate_limit=60  # 估计限制
        )
    
    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()
            self.session = None
        
        self.status = EngineStatus.OFFLINE
        await super().cleanup()
    
    def _get_output_dir(self, project_manager=None, current_project_name=None) -> str:
        """获取输出目录"""
        try:
            # 优先使用传入的项目管理器
            if project_manager and current_project_name:
                project_root = project_manager.get_project_root(current_project_name)
                if project_root:
                    output_dir = os.path.join(project_root, 'images', 'imagen')
                    os.makedirs(output_dir, exist_ok=True)
                    return output_dir
            
            # 尝试使用实例变量
            if self.project_manager and self.current_project_name:
                project_root = self.project_manager.get_project_root(self.current_project_name)
                if project_root:
                    output_dir = os.path.join(project_root, 'images', 'imagen')
                    os.makedirs(output_dir, exist_ok=True)
                    return output_dir
            
            # 尝试获取全局项目管理器
            from src.core.project_manager import ProjectManager
            project_manager = ProjectManager()
            current_project = project_manager.get_current_project()
            
            if current_project:
                project_root = current_project.get('project_root')
                if project_root:
                    output_dir = os.path.join(project_root, 'images', 'imagen')
                    os.makedirs(output_dir, exist_ok=True)
                    return output_dir
        except Exception as e:
            logger.warning(f"无法获取项目目录: {e}")
        
        # 默认输出目录
        default_dir = os.path.join(os.getcwd(), 'output', 'images', 'imagen')
        os.makedirs(default_dir, exist_ok=True)
        return default_dir