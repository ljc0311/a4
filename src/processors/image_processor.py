#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像生成处理器
基于新的服务架构的图像生成和处理功能
优化版本：支持内存管理、异步处理优化
"""

import os
import asyncio
import base64
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from pathlib import Path

from src.utils.logger import logger
from src.core.service_manager import ServiceManager, ServiceType
from src.core.service_base import ServiceResult
from src.processors.text_processor import Shot, StoryboardResult
from src.utils.memory_optimizer import memory_manager, monitor_memory

@dataclass
class ImageGenerationConfig:
    """图像生成配置"""
    provider: str = "comfyui"
    style: str = None
    width: int = 1024
    height: int = 576
    steps: int = 20
    cfg_scale: float = 7.0
    seed: int = -1
    batch_size: int = 1
    negative_prompt: str = "low quality, blurry, distorted"
    
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
    results: List[ImageResult]
    total_time: float
    success_count: int
    failed_count: int
    output_directory: str
    
class ImageProcessor:
    """图像生成处理器 - 优化版本"""
    
    def __init__(self, service_manager: ServiceManager, output_dir: str = "output/images"):
        self.service_manager = service_manager
        self.output_dir = Path(output_dir)
        
        # 默认配置
        self.default_config = ImageGenerationConfig()
        if self.default_config.style is None:
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            self.default_config.style = config_manager.get_setting("default_style", "电影风格")
        
        # 风格预设
        self.style_presets = {
            "电影风格": {
                "negative_prompt": "low quality, blurry, cartoon, anime, distorted, deformed",
                "cfg_scale": 7.0,
                "steps": 25
            },
            "动漫风格": {
                "negative_prompt": "realistic, photographic, 3d render, low quality, blurry",
                "cfg_scale": 8.0,
                "steps": 20
            },
            "吉卜力风格": {
                "negative_prompt": "realistic, dark, horror, low quality, blurry",
                "cfg_scale": 7.5,
                "steps": 22
            },
            "赛博朋克风格": {
                "negative_prompt": "bright, cheerful, natural, low quality, blurry",
                "cfg_scale": 8.5,
                "steps": 28
            },
            "水彩插画风格": {
                "negative_prompt": "realistic, photographic, dark, low quality, blurry",
                "cfg_scale": 6.5,
                "steps": 18
            },
            "像素风格": {
                "negative_prompt": "realistic, high resolution, smooth, low quality, blurry",
                "cfg_scale": 7.0,
                "steps": 15
            },
            "写实摄影风格": {
                "negative_prompt": "cartoon, anime, painting, drawing, low quality, blurry",
                "cfg_scale": 6.0,
                "steps": 30
            }
        }
        
        # 注册内存清理回调
        memory_manager.register_cleanup_callback(self._cleanup_temp_files)
        
        logger.info(f"图像处理器初始化完成，输出目录: {self.output_dir}")
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if self.output_dir.exists():
                # 清理超过1小时的临时文件
                current_time = time.time()
                for file_path in self.output_dir.rglob("*"):
                    if file_path.is_file():
                        file_age = current_time - file_path.stat().st_mtime
                        if file_age > 3600:  # 1小时
                            try:
                                file_path.unlink()
                                logger.debug(f"清理临时文件: {file_path}")
                            except Exception as e:
                                logger.error(f"清理临时文件失败 {file_path}: {e}")
        except Exception as e:
            logger.error(f"清理临时文件异常: {e}")
    
    @monitor_memory("分镜图像生成")
    async def generate_storyboard_images(self, storyboard: StoryboardResult, 
                                       config: ImageGenerationConfig = None,
                                       progress_callback: Callable = None,
                                       project_dir: str = None) -> BatchImageResult:
        """为分镜生成图像 - 优化版本"""
        try:
            if config is None:
                config = self.default_config
            
            # 应用风格预设
            config = self._apply_style_preset(config, storyboard.style)
            
            logger.info(f"开始为 {len(storyboard.shots)} 个镜头生成图像")
            
            # 检查内存状态
            if memory_manager.check_memory_pressure():
                logger.warning("内存压力过大，执行清理")
                memory_manager.force_cleanup()
            
            total_shots = len(storyboard.shots)
            start_time = time.time()
            
            # 创建项目输出目录
            if project_dir:
                output_dir = Path(project_dir) / "images"
            else:
                output_dir = self.output_dir / f"storyboard_{int(start_time)}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 准备批量生成的提示词
            prompts = [shot.image_prompt for shot in storyboard.shots]
            
            # 使用优化的批量生成
            image_service = self.service_manager.get_service(ServiceType.IMAGE)
            if image_service and hasattr(image_service, 'generate_batch_images'):
                service_results = await image_service.generate_batch_images(
                    prompts=prompts,
                    style=storyboard.style,
                    negative_prompt=config.negative_prompt,
                    provider=config.provider,
                    progress_callback=progress_callback,
                    width=config.width,
                    height=config.height,
                    steps=config.steps,
                    cfg_scale=config.cfg_scale,
                    seed=config.seed
                )
            else:
                # 回退到逐个生成
                service_results = await self._generate_images_sequentially(
                    storyboard.shots, config, progress_callback
                )
            
            # 处理结果并保存图像
            results = []
            for i, (shot, service_result) in enumerate(zip(storyboard.shots, service_results)):
                if service_result.success:
                    try:
                        image_result = await self._save_image_result(
                            shot, service_result, config, output_dir, start_time
                        )
                        if image_result:
                            results.append(image_result)
                    except Exception as e:
                        logger.error(f"保存第 {shot.shot_id} 张图像失败: {e}")
                else:
                    logger.error(f"生成第 {shot.shot_id} 张图像失败: {service_result.error}")
            
            total_time = time.time() - start_time
            
            if progress_callback:
                progress_callback(1.0, "图像生成完成")
            
            batch_result = BatchImageResult(
                results=results,
                total_time=total_time,
                success_count=len(results),
                failed_count=total_shots - len(results),
                output_directory=str(output_dir)
            )
            
            logger.info(f"批量图像生成完成，成功: {batch_result.success_count}, 失败: {batch_result.failed_count}")
            return batch_result
            
        except Exception as e:
            logger.error(f"批量图像生成失败: {e}")
            raise
    
    async def _generate_images_sequentially(self, shots: List[Shot], config: ImageGenerationConfig, 
                                          progress_callback: Callable = None) -> List[ServiceResult]:
        """顺序生成图像（回退方案）"""
        results = []
        total_shots = len(shots)
        
        for i, shot in enumerate(shots):
            try:
                if progress_callback:
                    progress_callback(i / total_shots, f"生成第 {i+1}/{total_shots} 张图像...")
                
                result = await self.service_manager.execute_service_method(
                    ServiceType.IMAGE,
                    "generate_image",
                    prompt=shot.image_prompt,
                    style=config.style,
                    negative_prompt=config.negative_prompt,
                    provider=config.provider,
                    width=config.width,
                    height=config.height,
                    steps=config.steps,
                    cfg_scale=config.cfg_scale,
                    seed=config.seed
                )
                
                results.append(result)
                
                # 避免请求过于频繁
                await asyncio.sleep(0.3)
                
            except Exception as e:
                logger.error(f"生成第 {shot.shot_id} 张图像失败: {e}")
                results.append(ServiceResult(success=False, error=str(e)))
        
        return results
    
    async def _save_image_result(self, shot: Shot, service_result: ServiceResult, 
                               config: ImageGenerationConfig, output_dir: Path, 
                               start_time: float) -> Optional[ImageResult]:
        """保存图像结果"""
        try:
            image_filename = f"shot_{shot.shot_id:03d}.png"
            image_path = output_dir / image_filename
            
            if 'image_data' in service_result.data:
                # Base64编码的图像数据
                if isinstance(service_result.data['image_data'], str):
                    image_data = base64.b64decode(service_result.data['image_data'])
                else:
                    image_data = service_result.data['image_data']
                
                with open(image_path, 'wb') as f:
                    f.write(image_data)
                    
            elif 'image_path' in service_result.data:
                # 图像文件路径
                import shutil
                shutil.copy2(service_result.data['image_path'], image_path)
            else:
                logger.error("图像生成结果中没有图像数据")
                return None
            
            generation_time = time.time() - start_time
            
            return ImageResult(
                shot_id=shot.shot_id,
                image_path=str(image_path),
                prompt=shot.image_prompt,
                provider=config.provider,
                generation_time=generation_time,
                metadata={
                    "scene": shot.scene,
                    "characters": shot.characters,
                    "action": shot.action,
                    "config": {
                        "width": config.width,
                        "height": config.height,
                        "steps": config.steps,
                        "cfg_scale": config.cfg_scale,
                        "seed": config.seed
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"保存图像结果失败: {e}")
            return None
    
    async def _generate_single_image(self, shot: Shot, config: ImageGenerationConfig, 
                                   output_dir: Path) -> Optional[ImageResult]:
        """生成单张图像"""
        try:
            shot_start_time = asyncio.get_event_loop().time()
            
            # 准备生成参数
            generation_params = {
                "prompt": shot.image_prompt,
                "negative_prompt": config.negative_prompt,
                "width": config.width,
                "height": config.height,
                "steps": config.steps,
                "cfg_scale": config.cfg_scale,
                "seed": config.seed if config.seed > 0 else None
            }
            
            # 调用图像生成服务
            result = await self.service_manager.execute_service_method(
                ServiceType.IMAGE,
                "generate_image",
                provider=config.provider,
                **generation_params
            )
            
            if not result.success:
                logger.error(f"图像生成失败: {result.error}")
                return None
            
            # 保存图像
            image_filename = f"shot_{shot.shot_id:03d}.png"
            image_path = output_dir / image_filename
            
            if 'image_data' in result.data:
                # Base64编码的图像数据
                image_data = base64.b64decode(result.data['image_data'])
                with open(image_path, 'wb') as f:
                    f.write(image_data)
            elif 'image_path' in result.data:
                # 图像文件路径
                import shutil
                shutil.copy2(result.data['image_path'], image_path)
            else:
                logger.error("图像生成结果中没有图像数据")
                return None
            
            generation_time = asyncio.get_event_loop().time() - shot_start_time
            
            image_result = ImageResult(
                shot_id=shot.shot_id,
                image_path=str(image_path),
                prompt=shot.image_prompt,
                provider=config.provider,
                generation_time=generation_time,
                metadata={
                    "scene": shot.scene,
                    "characters": shot.characters,
                    "action": shot.action,
                    "config": {
                        "width": config.width,
                        "height": config.height,
                        "steps": config.steps,
                        "cfg_scale": config.cfg_scale,
                        "seed": generation_params.get("seed")
                    }
                }
            )
            
            logger.info(f"镜头 {shot.shot_id} 图像生成完成: {image_path}")
            return image_result
            
        except Exception as e:
            logger.error(f"生成镜头 {shot.shot_id} 图像失败: {e}")
            return None
    
    def _apply_style_preset(self, config: ImageGenerationConfig, style: str) -> ImageGenerationConfig:
        """应用风格预设"""
        if style in self.style_presets:
            preset = self.style_presets[style]
            
            # 创建新的配置对象
            new_config = ImageGenerationConfig(
                provider=config.provider,
                style=style,
                width=config.width,
                height=config.height,
                steps=preset.get("steps", config.steps),
                cfg_scale=preset.get("cfg_scale", config.cfg_scale),
                seed=config.seed,
                batch_size=config.batch_size,
                negative_prompt=preset.get("negative_prompt", config.negative_prompt)
            )
            
            return new_config
        
        return config
    
    async def generate_single_image(self, prompt: str, config: ImageGenerationConfig = None,
                                  output_filename: str = None) -> Optional[ImageResult]:
        """生成单张图像"""
        try:
            if config is None:
                config = self.default_config
            
            if output_filename is None:
                # 使用简洁的文件名，不包含时间戳
                output_filename = "image.png"
            
            output_path = self.output_dir / output_filename
            
            # 创建临时Shot对象
            temp_shot = Shot(
                shot_id=1,
                scene="",
                characters=[],
                action="",
                dialogue="",
                image_prompt=prompt
            )
            
            result = await self._generate_single_image(temp_shot, config, self.output_dir)
            
            if result:
                # 重命名文件
                os.rename(result.image_path, output_path)
                result.image_path = str(output_path)
            
            return result
            
        except Exception as e:
            logger.error(f"生成单张图像失败: {e}")
            return None
    
    async def image_to_image(self, input_image_path: str, prompt: str, 
                           config: ImageGenerationConfig = None,
                           strength: float = 0.7) -> Optional[ImageResult]:
        """图像到图像生成"""
        try:
            if config is None:
                config = self.default_config
            
            if not os.path.exists(input_image_path):
                raise FileNotFoundError(f"输入图像不存在: {input_image_path}")
            
            generation_params = {
                "prompt": prompt,
                "input_image_path": input_image_path,
                "strength": strength,
                "negative_prompt": config.negative_prompt,
                "width": config.width,
                "height": config.height,
                "steps": config.steps,
                "cfg_scale": config.cfg_scale,
                "seed": config.seed if config.seed > 0 else None
            }
            
            result = await self.service_manager.execute_service_method(
                ServiceType.IMAGE,
                "image_to_image",
                provider=config.provider,
                **generation_params
            )
            
            if not result.success:
                logger.error(f"图像到图像生成失败: {result.error}")
                return None
            
            # 保存结果
            # 使用简洁的文件名，不包含时间戳
            output_filename = "img2img.png"
            output_path = self.output_dir / output_filename
            
            if 'image_data' in result.data:
                image_data = base64.b64decode(result.data['image_data'])
                with open(output_path, 'wb') as f:
                    f.write(image_data)
            elif 'image_path' in result.data:
                import shutil
                shutil.copy2(result.data['image_path'], output_path)
            
            return ImageResult(
                shot_id=0,
                image_path=str(output_path),
                prompt=prompt,
                provider=config.provider,
                generation_time=0,
                metadata={
                    "input_image": input_image_path,
                    "strength": strength
                }
            )
            
        except Exception as e:
            logger.error(f"图像到图像生成失败: {e}")
            return None
    
    async def upscale_image(self, image_path: str, scale_factor: int = 2) -> Optional[str]:
        """图像放大"""
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图像文件不存在: {image_path}")
            
            result = await self.service_manager.execute_service_method(
                ServiceType.IMAGE,
                "upscale_image",
                image_path=image_path,
                scale_factor=scale_factor
            )
            
            if not result.success:
                logger.error(f"图像放大失败: {result.error}")
                return None
            
            # 保存放大后的图像
            # 使用简洁的文件名，不包含时间戳
            output_filename = "upscaled.png"
            output_path = self.output_dir / output_filename
            
            if 'image_data' in result.data:
                image_data = base64.b64decode(result.data['image_data'])
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                return str(output_path)
            elif 'image_path' in result.data:
                import shutil
                shutil.copy2(result.data['image_path'], output_path)
                return str(output_path)
            
            return None
            
        except Exception as e:
            logger.error(f"图像放大失败: {e}")
            return None
    
    def get_available_providers(self) -> List[str]:
        """获取可用的图像生成提供商"""
        try:
            image_service = self.service_manager.get_service(ServiceType.IMAGE)
            if image_service:
                return image_service.get_available_providers()
            return []
        except Exception as e:
            logger.error(f"获取图像生成提供商失败: {e}")
            return []
    
    def get_style_presets(self) -> Dict[str, Dict]:
        """获取风格预设"""
        return self.style_presets.copy()
    
    def add_style_preset(self, name: str, preset: Dict):
        """添加风格预设"""
        self.style_presets[name] = preset
        logger.info(f"已添加风格预设: {name}")
    
    def update_config(self, **kwargs):
        """更新默认配置"""
        for key, value in kwargs.items():
            if hasattr(self.default_config, key):
                setattr(self.default_config, key, value)
                logger.info(f"已更新配置 {key}: {value}")
    
    def get_generation_stats(self, batch_result: BatchImageResult) -> Dict[str, Any]:
        """获取生成统计信息"""
        if not batch_result.results:
            return {}
        
        total_time = sum(r.generation_time for r in batch_result.results)
        avg_time = total_time / len(batch_result.results)
        
        providers = {}
        for result in batch_result.results:
            provider = result.provider
            if provider not in providers:
                providers[provider] = 0
            providers[provider] += 1
        
        return {
            "total_images": len(batch_result.results),
            "total_generation_time": total_time,
            "average_generation_time": avg_time,
            "success_rate": batch_result.success_count / (batch_result.success_count + batch_result.failed_count),
            "providers_used": providers,
            "output_directory": batch_result.output_directory
        }
    
    def cleanup_old_images(self, days: int = 7):
        """清理旧图像文件"""
        try:
            from src.utils.file_cleanup_manager import cleanup_old_images
            stats = cleanup_old_images(self.output_dir, days)
            logger.info(f"已清理 {stats['deleted']} 个旧图像文件，释放 {stats['freed_size_mb']:.2f}MB")
            return stats

        except Exception as e:
            logger.error(f"清理旧图像文件失败: {e}")
            return None