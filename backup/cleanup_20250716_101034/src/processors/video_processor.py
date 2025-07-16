#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频处理器
基于新的服务架构的视频生成和处理功能
"""

import os
import asyncio
import json
import time
import subprocess
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from pathlib import Path

from src.utils.logger import logger
from src.core.service_manager import ServiceManager, ServiceType
from src.core.service_base import ServiceResult
from src.processors.text_processor import StoryboardResult
from src.processors.image_processor import BatchImageResult, ImageResult

# 导入视频生成引擎
try:
    from src.models.video_engines.video_generation_service import VideoGenerationService
    from src.models.video_engines.video_engine_base import VideoGenerationConfig, VideoGenerationResult
    from config.video_generation_config import get_config as get_video_config
    VIDEO_ENGINES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"视频生成引擎不可用: {e}")
    VIDEO_ENGINES_AVAILABLE = False

@dataclass
class VideoConfig:
    """视频生成配置"""
    fps: int = 30  # 修改为CogVideoX支持的帧率
    duration_per_shot: float = 3.0
    resolution: tuple = (1920, 1080)
    codec: str = "libx264"
    bitrate: str = "5M"
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"
    transition_type: str = "fade"  # fade, cut, dissolve, slide
    transition_duration: float = 0.5
    background_music: Optional[str] = None
    background_music_volume: float = 0.3
    
@dataclass
class AudioTrack:
    """音频轨道"""
    file_path: str
    start_time: float
    duration: float
    volume: float = 1.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    track_type: str = "voice"  # voice, music, sfx
    
@dataclass
class VideoClip:
    """视频片段"""
    shot_id: int
    image_path: str
    start_time: float
    duration: float
    audio_tracks: List[AudioTrack]
    effects: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.audio_tracks is None:
            self.audio_tracks = []
        if self.effects is None:
            self.effects = []

@dataclass
class VideoProject:
    """视频项目"""
    clips: List[VideoClip]
    config: VideoConfig
    total_duration: float
    output_path: str
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class VideoProcessor:
    """视频处理器"""
    
    def __init__(self, service_manager: ServiceManager, output_dir: str = "output/videos"):
        self.service_manager = service_manager
        self.output_dir = Path(output_dir)
        # 不自动创建目录，假设目录已存在

        # 默认配置
        self.default_config = VideoConfig()

        # 🔧 修复：使用单例模式管理视频生成服务，避免重复创建引擎
        self.video_generation_service = None
        if VIDEO_ENGINES_AVAILABLE:
            try:
                from src.core.singleton_manager import get_singleton_service

                def create_video_service():
                    video_config = get_video_config('development')
                    return VideoGenerationService(video_config)

                # 使用单例管理器确保只有一个视频生成服务实例
                self.video_generation_service = get_singleton_service(
                    'video_generation_service',
                    create_video_service
                )
                logger.info("视频生成引擎服务初始化成功（单例模式）")
            except Exception as e:
                logger.warning(f"视频生成引擎服务初始化失败: {e}")
                self.video_generation_service = None
        
        # 转场效果配置
        self.transition_effects = {
            "fade": {"type": "fade", "duration": 0.5},
            "cut": {"type": "cut", "duration": 0.0},
            "dissolve": {"type": "dissolve", "duration": 0.8},
            "slide_left": {"type": "slide", "direction": "left", "duration": 1.0},
            "slide_right": {"type": "slide", "direction": "right", "duration": 1.0},
            "zoom_in": {"type": "zoom", "direction": "in", "duration": 1.2},
            "zoom_out": {"type": "zoom", "direction": "out", "duration": 1.2}
        }
        
        # 视觉效果预设
        self.visual_effects = {
            "ken_burns": {"type": "ken_burns", "zoom_factor": 1.2, "pan_direction": "random"},
            "parallax": {"type": "parallax", "layers": 3, "speed_factor": 0.5},
            "particle": {"type": "particle", "particle_type": "snow", "density": 50},
            "color_grade": {"type": "color_grade", "preset": "cinematic"},
            "vignette": {"type": "vignette", "strength": 0.3},
            "film_grain": {"type": "film_grain", "strength": 0.2}
        }
        
        logger.info(f"视频处理器初始化完成，输出目录: {self.output_dir}")
    
    async def create_video_from_storyboard(self, storyboard: StoryboardResult, 
                                         image_results: BatchImageResult,
                                         config: Optional[VideoConfig] = None,
                                         progress_callback: Optional[Callable] = None) -> VideoProject:
        """从分镜和图像创建视频项目"""
        try:
            if config is None:
                config = self.default_config
            
            logger.info(f"开始创建视频项目，共 {len(storyboard.shots)} 个镜头")
            
            # 创建视频片段
            clips = []
            current_time = 0.0
            
            # 创建图像路径映射
            image_map = {result.shot_id: result.image_path for result in image_results.results}
            
            for i, shot in enumerate(storyboard.shots):
                if progress_callback:
                    progress_callback(i / len(storyboard.shots), f"处理镜头 {i+1}/{len(storyboard.shots)}...")
                
                # 获取对应的图像
                image_path = image_map.get(shot.shot_id)
                if not image_path or not os.path.exists(image_path):
                    logger.warning(f"镜头 {shot.shot_id} 的图像不存在，跳过")
                    continue
                
                # 创建音频轨道
                audio_tracks = []
                if shot.dialogue:
                    # 生成语音
                    voice_result = await self._generate_voice_for_shot(shot, config)
                    if voice_result:
                        audio_tracks.append(voice_result)
                
                # 创建视觉效果
                effects = self._create_shot_effects(shot, config)
                
                # 创建视频片段
                clip = VideoClip(
                    shot_id=shot.shot_id,
                    image_path=image_path,
                    start_time=current_time,
                    duration=shot.duration,
                    audio_tracks=audio_tracks,
                    effects=effects,
                    metadata={
                        "scene": shot.scene,
                        "characters": shot.characters,
                        "action": shot.action,
                        "dialogue": shot.dialogue,
                        "camera_angle": shot.camera_angle,
                        "lighting": shot.lighting,
                        "mood": shot.mood
                    }
                )
                
                clips.append(clip)
                current_time += shot.duration
            
            # 创建输出路径
            # 使用简洁的文件名，不包含时间戳
            output_filename = "video.mp4"
            output_path = self.output_dir / output_filename
            
            project = VideoProject(
                clips=clips,
                config=config,
                total_duration=current_time,
                output_path=str(output_path),
                metadata={
                    "storyboard_style": storyboard.style,
                    "total_shots": len(clips),
                    "characters": storyboard.characters,
                    "scenes": storyboard.scenes,
                    "creation_time": time.time()
                }
            )
            
            if progress_callback:
                progress_callback(1.0, "视频项目创建完成")
            
            logger.info(f"视频项目创建完成，总时长: {current_time:.1f}秒")
            return project
            
        except Exception as e:
            logger.error(f"创建视频项目失败: {e}")
            raise
    
    async def _generate_voice_for_shot(self, shot, config: VideoConfig) -> Optional[AudioTrack]:
        """为镜头生成语音"""
        try:
            if not shot.dialogue:
                return None
            
            # 调用语音服务
            result = await self.service_manager.execute_service_method(
                ServiceType.VOICE,
                "text_to_speech",
                text=shot.dialogue,
                voice_id="default",
                speed=1.0,
                pitch=1.0
            )
            
            if not result.success:
                logger.warning(f"镜头 {shot.shot_id} 语音生成失败: {result.error}")
                return None
            
            audio_path = result.data.get('audio_path')
            if not audio_path:
                logger.warning(f"镜头 {shot.shot_id} 语音生成结果中没有音频路径")
                return None
            
            return AudioTrack(
                file_path=audio_path,
                start_time=0.0,
                duration=shot.duration,
                volume=1.0,
                track_type="voice"
            )
            
        except Exception as e:
            logger.error(f"生成镜头 {shot.shot_id} 语音失败: {e}")
            return None
    
    def _create_shot_effects(self, shot, config: VideoConfig) -> List[Dict[str, Any]]:
        """为镜头创建视觉效果"""
        effects = []
        
        # 根据镜头信息添加效果
        if shot.camera_angle == "特写":
            effects.append(self.visual_effects["ken_burns"].copy())
        elif shot.camera_angle == "远景":
            effects.append(self.visual_effects["parallax"].copy())
        
        # 根据情绪添加效果
        if shot.mood in ["紧张", "恐怖"]:
            effects.append(self.visual_effects["vignette"].copy())
        elif shot.mood in ["梦幻", "回忆"]:
            effects.append(self.visual_effects["film_grain"].copy())
        
        # 根据场景添加效果
        if "雪" in shot.scene or "冬" in shot.scene:
            particle_effect = self.visual_effects["particle"].copy()
            particle_effect["particle_type"] = "snow"
            effects.append(particle_effect)
        elif "雨" in shot.scene:
            particle_effect = self.visual_effects["particle"].copy()
            particle_effect["particle_type"] = "rain"
            effects.append(particle_effect)
        
        return effects
    
    async def render_video(self, project: VideoProject,
                         progress_callback: Optional[Callable] = None) -> str:
        """渲染视频"""
        try:
            logger.info(f"开始渲染视频: {project.output_path}")
            
            if progress_callback:
                progress_callback(0.0, "准备渲染...")
            
            # 准备渲染参数
            render_params = {
                "clips": [
                    {
                        "image_path": clip.image_path,
                        "start_time": clip.start_time,
                        "duration": clip.duration,
                        "audio_tracks": [
                            {
                                "file_path": track.file_path,
                                "start_time": track.start_time,
                                "duration": track.duration,
                                "volume": track.volume,
                                "fade_in": track.fade_in,
                                "fade_out": track.fade_out
                            }
                            for track in clip.audio_tracks
                        ],
                        "effects": clip.effects
                    }
                    for clip in project.clips
                ],
                "config": {
                    "fps": project.config.fps,
                    "resolution": project.config.resolution,
                    "codec": project.config.codec,
                    "bitrate": project.config.bitrate,
                    "audio_codec": project.config.audio_codec,
                    "audio_bitrate": project.config.audio_bitrate,
                    "transition_type": project.config.transition_type,
                    "transition_duration": project.config.transition_duration
                },
                "output_path": project.output_path,
                "background_music": project.config.background_music,
                "background_music_volume": project.config.background_music_volume
            }
            
            # 调用视频渲染服务
            result = await self.service_manager.execute_service_method(
                ServiceType.VIDEO,
                "render_video",
                **render_params
            )
            
            if not result.success:
                raise Exception(f"视频渲染失败: {result.error}")
            
            if progress_callback:
                progress_callback(1.0, "视频渲染完成")
            
            logger.info(f"视频渲染完成: {project.output_path}")
            return project.output_path
            
        except Exception as e:
            logger.error(f"视频渲染失败: {e}")
            raise
    
    async def create_animated_video(self, image_results: BatchImageResult,
                                  config: Optional[VideoConfig] = None,
                                  animation_type: str = "ken_burns",
                                  progress_callback: Optional[Callable] = None) -> str:
        """创建动画视频（图像到动画）"""
        try:
            if config is None:
                config = self.default_config
            
            logger.info(f"开始创建动画视频，动画类型: {animation_type}")
            
            # 创建输出路径
            # 使用简洁的文件名，不包含时间戳
            output_filename = "animated.mp4"
            output_path = self.output_dir / output_filename
            
            # 准备动画参数
            animation_params = {
                "images": [
                    {
                        "path": result.image_path,
                        "duration": config.duration_per_shot,
                        "prompt": result.prompt
                    }
                    for result in image_results.results
                ],
                "animation_type": animation_type,
                "fps": config.fps,
                "resolution": config.resolution,
                "output_path": str(output_path)
            }
            
            if progress_callback:
                progress_callback(0.1, "开始图像动画化...")
            
            # 调用动画生成服务
            result = await self.service_manager.execute_service_method(
                ServiceType.VIDEO,
                "create_animation",
                **animation_params
            )
            
            if not result.success:
                raise Exception(f"动画创建失败: {result.error}")
            
            if progress_callback:
                progress_callback(1.0, "动画视频创建完成")
            
            logger.info(f"动画视频创建完成: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"创建动画视频失败: {e}")
            raise

    async def generate_video_from_image(self, image_path: str,
                                      prompt: str = "",
                                      duration: float = 5.0,
                                      fps: int = 30,  # 修改为CogVideoX支持的帧率
                                      width: int = 1024,
                                      height: int = 1024,
                                      motion_intensity: float = 0.5,
                                      preferred_engine: str = "cogvideox_flash",
                                      progress_callback: Optional[Callable] = None,
                                      project_manager=None,
                                      current_project_name=None,
                                      max_concurrent_tasks: int = 3,
                                      audio_hint: Optional[str] = None) -> str:
        """使用AI引擎从图像生成视频"""
        try:
            if not VIDEO_ENGINES_AVAILABLE or not self.video_generation_service:
                raise Exception("视频生成引擎不可用，请检查配置")

            if not os.path.exists(image_path):
                raise FileNotFoundError(f"输入图像不存在: {image_path}")

            logger.info(f"开始从图像生成视频: {image_path}")

            if progress_callback:
                progress_callback(0.1, "准备视频生成...")

            # 生成视频
            result = await self.video_generation_service.generate_video(
                prompt=prompt,
                image_path=image_path,
                duration=duration,
                fps=fps,
                width=width,
                height=height,
                motion_intensity=motion_intensity,
                preferred_engines=[preferred_engine] if preferred_engine else None,
                progress_callback=lambda msg: progress_callback(0.5, msg) if progress_callback else None,
                project_manager=project_manager,
                current_project_name=current_project_name,
                audio_hint=audio_hint  # 传递音效提示
            )

            if not result.success:
                raise Exception(f"视频生成失败: {result.error_message}")

            if progress_callback:
                progress_callback(1.0, "视频生成完成!")

            logger.info(f"视频生成完成: {result.video_path}")
            return result.video_path

        except asyncio.CancelledError:
            logger.warning("从图像生成视频任务被取消")
            raise
        except Exception as e:
            logger.error(f"从图像生成视频失败: {e}")
            raise

    async def batch_generate_videos_from_images(self, image_results: BatchImageResult,
                                              base_prompt: str = "",
                                              duration: float = 5.0,
                                              fps: int = 24,
                                              width: int = 1024,
                                              height: int = 1024,
                                              motion_intensity: float = 0.5,
                                              preferred_engine: str = "cogvideox_flash",
                                              progress_callback: Optional[Callable] = None,
                                              project_manager=None,
                                              current_project_name=None) -> List[str]:
        """批量从图像生成视频"""
        try:
            if not VIDEO_ENGINES_AVAILABLE or not self.video_generation_service:
                raise Exception("视频生成引擎不可用，请检查配置")

            logger.info(f"开始批量生成视频，共 {len(image_results.results)} 张图像")

            video_paths = []
            total_count = len(image_results.results)

            for i, image_result in enumerate(image_results.results):
                try:
                    if progress_callback:
                        progress_callback(i / total_count, f"生成视频 {i+1}/{total_count}...")

                    # 组合提示词
                    prompt = f"{base_prompt} {image_result.prompt}".strip()

                    # 生成视频
                    video_path = await self.generate_video_from_image(
                        image_path=image_result.image_path,
                        prompt=prompt,
                        duration=duration,
                        fps=fps,
                        width=width,
                        height=height,
                        motion_intensity=motion_intensity,
                        preferred_engine=preferred_engine,
                        progress_callback=None,  # 不传递内部进度回调
                        project_manager=project_manager,
                        current_project_name=current_project_name
                    )

                    video_paths.append(video_path)
                    logger.info(f"第 {i+1} 个视频生成完成: {video_path}")

                except Exception as e:
                    logger.error(f"生成第 {i+1} 个视频失败: {e}")
                    # 继续处理下一个，不中断整个批次
                    continue

            if progress_callback:
                progress_callback(1.0, f"批量视频生成完成，成功 {len(video_paths)}/{total_count}")

            logger.info(f"批量视频生成完成，成功 {len(video_paths)}/{total_count}")
            return video_paths

        except Exception as e:
            logger.error(f"批量生成视频失败: {e}")
            raise

    def get_available_video_engines(self) -> List[str]:
        """获取可用的视频生成引擎"""
        if not VIDEO_ENGINES_AVAILABLE or not self.video_generation_service:
            return []
        return self.video_generation_service.get_available_engines()

    def get_video_engine_info(self, engine_name: str) -> Optional[Dict]:
        """获取视频引擎信息"""
        if not VIDEO_ENGINES_AVAILABLE or not self.video_generation_service:
            return None
        return self.video_generation_service.get_engine_info(engine_name)

    async def test_video_engine(self, engine_name: str) -> bool:
        """测试视频引擎连接"""
        if not VIDEO_ENGINES_AVAILABLE or not self.video_generation_service:
            return False
        return await self.video_generation_service.test_engine(engine_name)

    async def test_all_video_engines(self) -> Dict[str, bool]:
        """测试所有视频引擎"""
        if not VIDEO_ENGINES_AVAILABLE or not self.video_generation_service:
            return {}
        return await self.video_generation_service.test_all_engines()

    def get_video_generation_statistics(self) -> Dict:
        """获取视频生成统计信息"""
        if not VIDEO_ENGINES_AVAILABLE or not self.video_generation_service:
            return {}
        return self.video_generation_service.get_service_statistics()

    def set_video_generation_config(self, config: Dict):
        """设置视频生成配置"""
        if VIDEO_ENGINES_AVAILABLE:
            try:
                self.video_generation_service = VideoGenerationService(config)
                logger.info("视频生成配置已更新")
            except Exception as e:
                logger.error(f"更新视频生成配置失败: {e}")

    async def shutdown_video_engines(self):
        """关闭视频生成引擎"""
        if self.video_generation_service:
            try:
                await self.video_generation_service.shutdown()
                logger.info("视频生成引擎已关闭")
            except Exception as e:
                logger.error(f"关闭视频生成引擎失败: {e}")
    
    async def add_background_music(self, video_path: str, music_path: str, 
                                 volume: float = 0.3, fade_in: float = 2.0,
                                 fade_out: float = 2.0) -> str:
        """添加背景音乐"""
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
            if not os.path.exists(music_path):
                raise FileNotFoundError(f"音乐文件不存在: {music_path}")
            
            # 创建输出路径
            # 使用简洁的文件名，不包含时间戳
            output_filename = "with_music.mp4"
            output_path = self.output_dir / output_filename
            
            result = await self.service_manager.execute_service_method(
                ServiceType.VIDEO,
                "add_background_music",
                video_path=video_path,
                music_path=music_path,
                output_path=str(output_path),
                volume=volume,
                fade_in=fade_in,
                fade_out=fade_out
            )
            
            if not result.success:
                raise Exception(f"添加背景音乐失败: {result.error}")
            
            logger.info(f"背景音乐添加完成: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"添加背景音乐失败: {e}")
            raise
    
    async def add_subtitles(self, video_path: str, storyboard: StoryboardResult,
                          subtitle_style: Optional[Dict[str, Any]] = None) -> str:
        """添加字幕"""
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
            # 默认字幕样式
            if subtitle_style is None:
                from src.utils.config_manager import ConfigManager
                config_manager = ConfigManager()
                default_font = config_manager.get_setting("default_font_family", "Arial")
                
                subtitle_style = {
                    "font_family": default_font,
                    "font_size": 24,
                    "font_color": "white",
                    "background_color": "black",
                    "background_opacity": 0.7,
                    "position": "bottom",
                    "margin": 50
                }
            
            # 准备字幕数据
            subtitles = []
            current_time = 0.0
            
            for shot in storyboard.shots:
                if shot.dialogue:
                    subtitles.append({
                        "start_time": current_time,
                        "end_time": current_time + shot.duration,
                        "text": shot.dialogue
                    })
                current_time += shot.duration
            
            if not subtitles:
                logger.warning("没有找到对话内容，无法添加字幕")
                return video_path
            
            # 创建输出路径
            # 使用简洁的文件名，不包含时间戳
            output_filename = "with_subtitles.mp4"
            output_path = self.output_dir / output_filename
            
            result = await self.service_manager.execute_service_method(
                ServiceType.VIDEO,
                "add_subtitles",
                video_path=video_path,
                subtitles=subtitles,
                style=subtitle_style,
                output_path=str(output_path)
            )
            
            if not result.success:
                raise Exception(f"添加字幕失败: {result.error}")
            
            logger.info(f"字幕添加完成: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"添加字幕失败: {e}")
            raise
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """获取视频信息"""
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")

            # 确定ffprobe的路径
            ffprobe_path = "ffmpeg/bin/ffprobe.exe"
            if not os.path.exists(ffprobe_path):
                logger.warning(f"ffprobe not found at {ffprobe_path}, trying system path.")
                ffprobe_path = "ffprobe"

            command = [
                ffprobe_path,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]

            result = subprocess.run(command, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            
            file_size = os.path.getsize(video_path)
            
            return {
                "file_path": video_path,
                "file_size": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "duration": duration
            }
            
        except FileNotFoundError:
            logger.error("ffprobe not found. Please ensure ffmpeg is installed and in your PATH.")
            return {}
        except subprocess.CalledProcessError as e:
            logger.error(f"ffprobe failed: {e.stderr}")
            return {}
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            return {}
    
    def get_available_transitions(self) -> List[str]:
        """获取可用的转场效果"""
        return list(self.transition_effects.keys())
    
    def get_available_effects(self) -> List[str]:
        """获取可用的视觉效果"""
        return list(self.visual_effects.keys())
    
    def update_config(self, **kwargs):
        """更新默认配置"""
        for key, value in kwargs.items():
            if hasattr(self.default_config, key):
                setattr(self.default_config, key, value)
                logger.info(f"已更新视频配置 {key}: {value}")
    
    def export_project(self, project: VideoProject, format: str = "json") -> str:
        """导出视频项目"""
        try:
            if format.lower() == "json":
                project_data = {
                    "clips": [
                        {
                            "shot_id": clip.shot_id,
                            "image_path": clip.image_path,
                            "start_time": clip.start_time,
                            "duration": clip.duration,
                            "audio_tracks": [
                                {
                                    "file_path": track.file_path,
                                    "start_time": track.start_time,
                                    "duration": track.duration,
                                    "volume": track.volume,
                                    "track_type": track.track_type
                                }
                                for track in clip.audio_tracks
                            ],
                            "effects": clip.effects,
                            "metadata": clip.metadata
                        }
                        for clip in project.clips
                    ],
                    "config": {
                        "fps": project.config.fps,
                        "duration_per_shot": project.config.duration_per_shot,
                        "resolution": project.config.resolution,
                        "codec": project.config.codec,
                        "bitrate": project.config.bitrate,
                        "transition_type": project.config.transition_type,
                        "transition_duration": project.config.transition_duration
                    },
                    "total_duration": project.total_duration,
                    "output_path": project.output_path,
                    "metadata": project.metadata
                }
                
                return json.dumps(project_data, ensure_ascii=False, indent=2)
            
            else:
                raise ValueError(f"不支持的导出格式: {format}")
                
        except Exception as e:
            logger.error(f"导出视频项目失败: {e}")
            raise
    
    def cleanup_old_videos(self, days: int = 30):
        """清理旧视频文件"""
        try:
            from src.utils.file_cleanup_manager import cleanup_old_videos
            stats = cleanup_old_videos(self.output_dir, days)
            logger.info(f"已清理 {stats['deleted']} 个旧视频文件，释放 {stats['freed_size_mb']:.2f}MB")
            return stats

        except Exception as e:
            logger.error(f"清理旧视频文件失败: {e}")
            return None
