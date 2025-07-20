#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用控制器
统一管理整个应用的核心功能和工作流程
"""

import asyncio
import json
import os
import time
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path

from src.utils.logger import logger
from src.utils.config_manager import ConfigManager
from src.core.service_manager import ServiceManager, ServiceType
from src.processors.text_processor import TextProcessor, StoryboardResult
from src.processors.image_processor import ImageProcessor, ImageGenerationConfig, BatchImageResult
from src.processors.video_processor import VideoProcessor, VideoConfig, VideoProject

class AppController:
    """应用控制器"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls, config_path: str = "config/config.json"):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance
    
    def __init__(self, config_path: str = "config/config.json"):
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # 初始化配置管理器
        self.config_manager = ConfigManager(config_path)
        
        # 初始化服务管理器
        self.service_manager = ServiceManager(self.config_manager)
        
        # 初始化处理器
        self.text_processor = TextProcessor(self.service_manager)
        self.image_processor = ImageProcessor(self.service_manager)
        self.video_processor = VideoProcessor(self.service_manager)
        
        # 初始化项目管理器（使用单例模式确保全局唯一）
        from src.utils.project_manager import StoryboardProjectManager
        from src.core.singleton_manager import get_singleton_service
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')

        # 使用单例管理器获取项目管理器实例
        self.project_manager = get_singleton_service(
            'project_manager',
            lambda: StoryboardProjectManager(config_dir)
        )
        
        # 工作流程状态
        self.current_workflow = None
        self.workflow_progress = {}
        
        # 项目数据
        self.current_project = {
            "text": "",
            "storyboard": None,
            "images": None,
            "video_project": None,
            "final_video": None
        }
        
        logger.info("应用控制器初始化完成")
    
    async def initialize(self):
        """初始化应用"""
        try:
            logger.info("开始初始化应用...")
            
            # 初始化服务管理器
            await self.service_manager.initialize()
            
            # 检查服务状态
            service_status = await self.service_manager.check_all_services()
            logger.info(f"服务状态检查完成: {service_status}")
            
            logger.info("应用初始化完成")
            
        except Exception as e:
            logger.error(f"应用初始化失败: {e}")
            raise
    
    async def shutdown(self):
        """关闭应用"""
        try:
            logger.info("开始关闭应用...")
            
            # 关闭服务管理器
            await self.service_manager.shutdown()
            
            logger.info("应用关闭完成")
            
        except Exception as e:
            logger.error(f"应用关闭失败: {e}")
    
    async def create_video_from_text(self, text: str,
                                   style: Optional[str] = None,
                                   image_config: Optional[ImageGenerationConfig] = None,
                                   video_config: Optional[VideoConfig] = None,
                                   providers: Optional[Dict[str, str]] = None,
                                   progress_callback: Optional[Callable] = None) -> str:
        """从文本创建视频的完整工作流程"""
        try:
            # 如果没有指定风格，从配置中获取默认风格
            if style is None:
                from src.utils.config_manager import ConfigManager
                config_manager = ConfigManager()
                style_setting = config_manager.get_setting("default_style", "电影风格")
                style = str(style_setting) if style_setting else "电影风格"
            
            logger.info("开始文本到视频的完整工作流程")
            
            if providers is None:
                providers = {}
            
            # 更新项目数据
            self.current_project["text"] = text
            
            # 步骤1: 文本解析和分镜生成
            if progress_callback:
                progress_callback(0.0, "正在解析文本并生成分镜...")
            
            storyboard = await self.text_processor.parse_text(
                text=text,
                style=style,
                provider=providers.get("llm"),
                progress_callback=lambda p, msg: progress_callback(p * 0.3, msg) if progress_callback else None
            )
            
            self.current_project["storyboard"] = storyboard
            logger.info(f"分镜生成完成，共 {len(storyboard.shots)} 个镜头")
            
            # 步骤2: 图像生成
            if progress_callback:
                progress_callback(0.3, "正在生成图像...")
            
            if image_config is None:
                image_config = ImageGenerationConfig()
            
            if providers.get("image"):
                image_config.provider = providers["image"]
            
            image_results = await self.image_processor.generate_storyboard_images(
                storyboard=storyboard,
                config=image_config,
                progress_callback=lambda p, msg: progress_callback(0.3 + p * 0.4, msg) if progress_callback else None
            )
            
            self.current_project["images"] = image_results
            logger.info(f"图像生成完成，成功 {image_results.success_count} 张")
            
            # 步骤3: 创建视频项目
            if progress_callback:
                progress_callback(0.7, "正在创建视频项目...")
            
            if video_config is None:
                video_config = VideoConfig()
            
            video_project = await self.video_processor.create_video_from_storyboard(
                storyboard=storyboard,
                image_results=image_results,
                config=video_config,
                progress_callback=lambda p, msg: progress_callback(0.7 + p * 0.15, msg) if progress_callback else None
            )
            
            self.current_project["video_project"] = video_project
            logger.info(f"视频项目创建完成，总时长 {video_project.total_duration:.1f}秒")
            
            # 步骤4: 渲染视频
            if progress_callback:
                progress_callback(0.85, "正在渲染视频...")
            
            final_video_path = await self.video_processor.render_video(
                project=video_project,
                progress_callback=lambda p, msg: progress_callback(0.85 + p * 0.15, msg) if progress_callback else None
            )
            
            self.current_project["final_video"] = final_video_path
            
            if progress_callback:
                progress_callback(1.0, "视频创建完成")
            
            logger.info(f"完整工作流程完成，视频保存至: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            logger.error(f"文本到视频工作流程失败: {e}")
            raise
    
    async def generate_storyboard_only(self, text: str, style: Optional[str] = None,
                                     provider: Optional[str] = None,
                                     progress_callback: Optional[Callable] = None) -> StoryboardResult:
        """仅生成分镜"""
        try:
            # 如果没有指定风格，从配置中获取默认风格
            if style is None:
                from src.utils.config_manager import ConfigManager
                config_manager = ConfigManager()
                style_setting = config_manager.get_setting("default_style", "电影风格")
                style = str(style_setting) if style_setting else "电影风格"
            
            logger.info("开始生成分镜")
            
            storyboard = await self.text_processor.parse_text(
                text=text,
                style=style,
                provider=provider,
                progress_callback=progress_callback
            )
            
            self.current_project["text"] = text
            self.current_project["storyboard"] = storyboard
            
            logger.info(f"分镜生成完成，共 {len(storyboard.shots)} 个镜头")
            return storyboard
            
        except Exception as e:
            logger.error(f"分镜生成失败: {e}")
            raise
    
    async def generate_images_only(self, storyboard: StoryboardResult = None,
                                 config: ImageGenerationConfig = None,
                                 progress_callback: Callable = None) -> BatchImageResult:
        """仅生成图像"""
        try:
            if storyboard is None:
                storyboard = self.current_project.get("storyboard")
                if storyboard is None:
                    raise ValueError("没有可用的分镜数据")
            
            logger.info("开始生成图像")
            
            image_results = await self.image_processor.generate_storyboard_images(
                storyboard=storyboard,
                config=config,
                progress_callback=progress_callback
            )
            
            self.current_project["images"] = image_results
            
            logger.info(f"图像生成完成，成功 {image_results.success_count} 张")
            return image_results
            
        except Exception as e:
            logger.error(f"图像生成失败: {e}")
            raise
    
    async def create_video_only(self, storyboard: StoryboardResult = None,
                              image_results: BatchImageResult = None,
                              config: VideoConfig = None,
                              progress_callback: Callable = None) -> str:
        """仅创建视频"""
        try:
            if storyboard is None:
                storyboard = self.current_project.get("storyboard")
                if storyboard is None:
                    raise ValueError("没有可用的分镜数据")
            
            if image_results is None:
                image_results = self.current_project.get("images")
                if image_results is None:
                    raise ValueError("没有可用的图像数据")
            
            logger.info("开始创建视频")
            
            # 创建视频项目
            video_project = await self.video_processor.create_video_from_storyboard(
                storyboard=storyboard,
                image_results=image_results,
                config=config,
                progress_callback=lambda p, msg: progress_callback(p * 0.3, msg) if progress_callback else None
            )
            
            self.current_project["video_project"] = video_project
            
            # 渲染视频
            final_video_path = await self.video_processor.render_video(
                project=video_project,
                progress_callback=lambda p, msg: progress_callback(0.3 + p * 0.7, msg) if progress_callback else None
            )
            
            self.current_project["final_video"] = final_video_path
            
            logger.info(f"视频创建完成: {final_video_path}")
            return final_video_path
            
        except Exception as e:
            logger.error(f"视频创建失败: {e}")
            raise
    
    async def create_animated_video(self, image_results: BatchImageResult = None,
                                  animation_type: str = "ken_burns",
                                  config: VideoConfig = None,
                                  progress_callback: Callable = None) -> str:
        """创建动画视频"""
        try:
            if image_results is None:
                image_results = self.current_project.get("images")
                if image_results is None:
                    raise ValueError("没有可用的图像数据")
            
            logger.info(f"开始创建动画视频，动画类型: {animation_type}")
            
            animated_video_path = await self.video_processor.create_animated_video(
                image_results=image_results,
                config=config,
                animation_type=animation_type,
                progress_callback=progress_callback
            )
            
            logger.info(f"动画视频创建完成: {animated_video_path}")
            return animated_video_path
            
        except Exception as e:
            logger.error(f"动画视频创建失败: {e}")
            raise
    
    async def rewrite_text(self, text: str, provider: str = None) -> str:
        """改写文本"""
        try:
            result = await self.text_processor.rewrite_text(text, provider)

            if result.success:
                return result.data['content']
            else:
                raise Exception(f"文本改写失败: {result.error}")

        except Exception as e:
            logger.error(f"文本改写失败: {e}")
            raise

    async def create_story_from_theme(self, theme: str, provider: str = None) -> str:
        """根据主题创作故事"""
        try:
            result = await self.text_processor.create_story_from_theme(theme, provider)

            if result.success:
                return result.data['content']
            else:
                raise Exception(f"故事创作失败: {result.error}")

        except Exception as e:
            logger.error(f"故事创作失败: {e}")
            raise

    async def add_background_music(self, video_path: str = None, music_path: str = None,
                                 volume: float = 0.3) -> str:
        """添加背景音乐"""
        try:
            if video_path is None:
                video_path = self.current_project.get("final_video")
                if video_path is None:
                    raise ValueError("没有可用的视频文件")
            
            if music_path is None:
                raise ValueError("请提供音乐文件路径")
            
            result_path = await self.video_processor.add_background_music(
                video_path=video_path,
                music_path=music_path,
                volume=volume
            )
            
            logger.info(f"背景音乐添加完成: {result_path}")
            return result_path
            
        except Exception as e:
            logger.error(f"添加背景音乐失败: {e}")
            raise
    
    async def add_subtitles(self, video_path: str = None, 
                          storyboard: StoryboardResult = None,
                          subtitle_style: Dict[str, Any] = None) -> str:
        """添加字幕"""
        try:
            if video_path is None:
                video_path = self.current_project.get("final_video")
                if video_path is None:
                    raise ValueError("没有可用的视频文件")
            
            if storyboard is None:
                storyboard = self.current_project.get("storyboard")
                if storyboard is None:
                    raise ValueError("没有可用的分镜数据")
            
            result_path = await self.video_processor.add_subtitles(
                video_path=video_path,
                storyboard=storyboard,
                subtitle_style=subtitle_style
            )
            
            logger.info(f"字幕添加完成: {result_path}")
            return result_path
            
        except Exception as e:
            logger.error(f"添加字幕失败: {e}")
            raise
    
    def get_available_providers(self) -> Dict[str, List[str]]:
        """获取可用的服务提供商"""
        try:
            return {
                "llm": self.service_manager.get_available_providers(ServiceType.LLM),
                "image": self.service_manager.get_available_providers(ServiceType.IMAGE),
                "voice": self.service_manager.get_available_providers(ServiceType.VOICE),
                "video": self.service_manager.get_available_providers(ServiceType.VIDEO)
            }
        except Exception as e:
            logger.error(f"获取可用提供商失败: {e}")
            return {}
    
    def get_available_styles(self) -> List[str]:
        """获取可用的风格"""
        return self.text_processor.get_available_styles()
    
    def get_project_status(self) -> Dict[str, Any]:
        """获取项目状态"""
        status = {
            "has_text": bool(self.current_project.get("text")),
            "has_storyboard": bool(self.current_project.get("storyboard")),
            "has_images": bool(self.current_project.get("images")),
            "has_video_project": bool(self.current_project.get("video_project")),
            "has_final_video": bool(self.current_project.get("final_video"))
        }
        
        if status["has_storyboard"]:
            storyboard = self.current_project["storyboard"]
            status["storyboard_info"] = {
                "shots_count": len(storyboard.shots),
                "total_duration": storyboard.total_duration,
                "style": storyboard.style,
                "characters": storyboard.characters,
                "scenes": storyboard.scenes
            }
        
        if status["has_images"]:
            images = self.current_project["images"]
            status["images_info"] = {
                "success_count": images.success_count,
                "failed_count": images.failed_count,
                "total_time": images.total_time,
                "output_directory": images.output_directory
            }
        
        if status["has_final_video"]:
            video_path = self.current_project["final_video"]
            status["video_info"] = self.video_processor.get_video_info(video_path)
        
        return status
    
    def export_project(self, format: str = "json") -> str:
        """导出项目数据"""
        try:
            project_data = {
                "text": self.current_project.get("text", ""),
                "creation_time": time.time()
            }
            
            # 导出分镜
            if self.current_project.get("storyboard"):
                storyboard_data = self.text_processor.export_storyboard(
                    self.current_project["storyboard"], format
                )
                if format.lower() == "json":
                    project_data["storyboard"] = json.loads(storyboard_data)
                else:
                    project_data["storyboard"] = storyboard_data
            
            # 导出视频项目
            if self.current_project.get("video_project"):
                video_project_data = self.video_processor.export_project(
                    self.current_project["video_project"], format
                )
                if format.lower() == "json":
                    project_data["video_project"] = json.loads(video_project_data)
                else:
                    project_data["video_project"] = video_project_data
            
            # 添加其他信息
            if self.current_project.get("images"):
                images = self.current_project["images"]
                project_data["images_info"] = {
                    "success_count": images.success_count,
                    "failed_count": images.failed_count,
                    "output_directory": images.output_directory
                }
            
            if self.current_project.get("final_video"):
                project_data["final_video_path"] = self.current_project["final_video"]
            
            if format.lower() == "json":
                return json.dumps(project_data, ensure_ascii=False, indent=2)
            else:
                # 可以添加其他格式的导出
                return str(project_data)
                
        except Exception as e:
            logger.error(f"导出项目失败: {e}")
            raise
    
    def clear_project(self):
        """清空当前项目"""
        self.current_project = {
            "text": "",
            "storyboard": None,
            "images": None,
            "video_project": None,
            "final_video": None
        }
        logger.info("项目数据已清空")
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置信息"""
        return self.config_manager.get_all_config()
    
    def update_config(self, config_updates: Dict[str, Any]):
        """更新配置"""
        try:
            for key, value in config_updates.items():
                self.config_manager.set_config(key, value)
            
            # 重新初始化服务管理器
            asyncio.create_task(self.service_manager.reload_config())
            
            logger.info("配置更新完成")
            
        except Exception as e:
            logger.error(f"配置更新失败: {e}")
            raise