#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像提示词处理器
处理图像生成的提示词优化和多语言支持
"""

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from src.models.language_models import LanguageCode
from src.core.language_manager import LanguageManager
from src.services.bilingual_llm_service import BilingualLLMService
from src.utils.logger import logger
from src.core.service_manager import ServiceManager


@dataclass
class ImageGenerationConfig:
    """图像生成配置"""
    prompt: str = ""
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    guidance_scale: float = 7.5
    num_inference_steps: int = 50
    language: LanguageCode = LanguageCode.CHINESE
    provider: str = ""  # 添加provider属性
    style: str = ""  # 添加style属性
    steps: int = 20  # 添加steps属性（与num_inference_steps相同）
    cfg_scale: float = 7.5  # 添加cfg_scale属性（与guidance_scale相同）
    seed: int = -1  # 添加seed属性
    batch_size: int = 1  # 添加batch_size属性
    
    def __post_init__(self):
        # 确保steps和num_inference_steps同步
        if self.steps != 20 and self.num_inference_steps == 50:
            self.num_inference_steps = self.steps
        elif self.num_inference_steps != 50 and self.steps == 20:
            self.steps = self.num_inference_steps
            
        # 确保cfg_scale和guidance_scale同步
        if self.cfg_scale != 7.5 and self.guidance_scale == 7.5:
            self.guidance_scale = self.cfg_scale
        elif self.guidance_scale != 7.5 and self.cfg_scale == 7.5:
            self.cfg_scale = self.guidance_scale


@dataclass
class ImageResult:
    """图像生成结果"""
    shot_id: int
    image_path: str
    prompt: str
    provider: str
    generation_time: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BatchImageResult:
    """批量图像生成结果"""
    success_count: int
    total_count: int
    results: List[ImageResult]
    errors: List[str]
    output_directory: str = ""
    total_time: float = 0.0
    
    @property
    def failed_count(self) -> int:
        """失败数量"""
        return self.total_count - self.success_count


class ImageProcessor:
    """图像提示词处理器"""
    
    def __init__(self, service_manager: ServiceManager):
        self.service_manager = service_manager
        self.language_manager = LanguageManager()
        self.bilingual_llm_service = BilingualLLMService(service_manager.api_manager)
    
    async def optimize_prompt_for_language(self, prompt: str, target_language: Optional[LanguageCode] = None, 
                                          style: Optional[str] = None) -> str:
        """
        根据语言优化提示词
        
        Args:
            prompt: 原始提示词
            target_language: 目标语言，如果为None则使用当前语言
            style: 风格要求
            
        Returns:
            str: 优化后的提示词
        """
        target_lang = target_language or self.language_manager.current_language
        
        try:
            # 调用双语LLM服务进行提示词优化
            result = await self.bilingual_llm_service.optimize_prompt_bilingual(
                prompt=prompt,
                style=style or "",
                language=target_lang
            )
            
            if result.success:
                optimized_prompt = result.data.get('content', prompt)
                logger.info(f"提示词优化完成: {prompt[:50]}... -> {optimized_prompt[:50]}...")
                return optimized_prompt
            else:
                logger.warning(f"提示词优化失败: {result.error}")
                return prompt
                
        except Exception as e:
            logger.error(f"提示词优化异常: {e}")
            return prompt
    
    async def generate_storyboard_images(self, storyboard, config: ImageGenerationConfig = None, 
                                       progress_callback = None) -> BatchImageResult:
        """
        生成分镜图像
        
        Args:
            storyboard: 分镜结果
            config: 图像生成配置
            progress_callback: 进度回调函数
            
        Returns:
            BatchImageResult: 批量图像生成结果
        """
        try:
            if config is None:
                config = ImageGenerationConfig()
            
            logger.info(f"开始生成分镜图像，共 {len(storyboard.shots)} 个镜头")
            
            results = []
            errors = []
            success_count = 0
            
            # 获取图像服务
            from src.core.service_manager import ServiceType
            image_service = self.service_manager.get_service(ServiceType.IMAGE)
            if not image_service:
                raise Exception("图像服务未初始化")
            
            for i, shot in enumerate(storyboard.shots):
                try:
                    if progress_callback:
                        progress = i / len(storyboard.shots)
                        progress_callback(progress, f"正在生成第 {i+1}/{len(storyboard.shots)} 张图像...")
                    
                    # 优化提示词
                    optimized_prompt = await self.optimize_prompt_for_language(
                        shot.image_prompt, 
                        config.language
                    )
                    
                    # 添加延迟避免API限制
                    if i > 0:
                        await asyncio.sleep(1)  # 每次生成间隔1秒
                    
                    # 生成图像，添加重试机制
                    max_retries = 3
                    generation_result = None
                    
                    for retry in range(max_retries):
                        try:
                            generation_result = await image_service.generate_image(
                                prompt=optimized_prompt,
                                negative_prompt=config.negative_prompt,
                                width=config.width,
                                height=config.height,
                                provider=config.provider if config.provider else None
                            )
                            break  # 成功则跳出重试循环
                        except Exception as retry_error:
                            logger.warning(f"镜头 {shot.shot_id} 第 {retry+1} 次生成尝试失败: {retry_error}")
                            if retry < max_retries - 1:
                                await asyncio.sleep(2 ** retry)  # 指数退避
                            else:
                                raise retry_error
                    
                    if generation_result.success and generation_result.data:
                        image_path = generation_result.data.get('image_path', '')
                        if image_path:
                            result = ImageResult(
                                shot_id=shot.shot_id,
                                image_path=image_path,
                                prompt=optimized_prompt,
                                provider=generation_result.metadata.get('provider', 'unknown'),
                                generation_time=generation_result.metadata.get('generation_time', 0.0),
                                metadata=generation_result.metadata
                            )
                            results.append(result)
                            success_count += 1
                            logger.info(f"镜头 {shot.shot_id} 图像生成成功: {image_path}")
                        else:
                            error_msg = f"镜头 {shot.shot_id} 生成失败: 未返回图像路径"
                            errors.append(error_msg)
                            logger.error(error_msg)
                    else:
                        error_msg = f"镜头 {shot.shot_id} 生成失败: {generation_result.error}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        
                except Exception as e:
                    error_msg = f"镜头 {shot.shot_id} 生成异常: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            if progress_callback:
                progress_callback(1.0, "图像生成完成")
            
            # 计算总时间
            total_time = sum(result.generation_time for result in results)
            
            # 获取输出目录（从第一个成功结果中获取）
            output_directory = ""
            if results:
                import os
                output_directory = os.path.dirname(results[0].image_path)
            
            batch_result = BatchImageResult(
                success_count=success_count,
                total_count=len(storyboard.shots),
                results=results,
                errors=errors,
                output_directory=output_directory,
                total_time=total_time
            )
            
            logger.info(f"分镜图像生成完成，成功 {success_count}/{len(storyboard.shots)} 张")
            return batch_result
            
        except Exception as e:
            logger.error(f"生成分镜图像失败: {e}")
            raise