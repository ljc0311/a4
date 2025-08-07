#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频合成服务 - 扩展视频合成功能，支持双语字幕嵌入
"""

import os
import tempfile
import subprocess
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

from src.services.subtitle_service import SubtitleService, TextSegment
from src.processors.video_composer import VideoComposer
from src.core.language_manager import LanguageManager
from src.models.language_models import LanguageCode, SubtitleSettings
from src.utils.logger import logger


class VideoCompositionService:
    """视频合成服务 - 支持双语字幕嵌入功能"""
    
    def __init__(self, language_manager: Optional[LanguageManager] = None):
        self.language_manager = language_manager or LanguageManager()
        self.subtitle_service = SubtitleService(self.language_manager)
        self.video_composer = VideoComposer()
        self.temp_dir = tempfile.mkdtemp(prefix="video_composition_")
        
        logger.info("视频合成服务初始化完成")
    
    def embed_subtitles_in_video(self, 
                               video_path: str, 
                               subtitle_path: str, 
                               output_path: str,
                               language: Optional[LanguageCode] = None,
                               subtitle_settings: Optional[SubtitleSettings] = None,
                               enable_subtitles: bool = True) -> str:
        """
        将字幕嵌入到视频中
        
        Args:
            video_path: 输入视频文件路径
            subtitle_path: 字幕文件路径（SRT格式）
            output_path: 输出视频文件路径
            language: 语言代码，用于字体选择
            subtitle_settings: 字幕样式设置
            enable_subtitles: 是否启用字幕显示
            
        Returns:
            str: 输出视频路径
        """
        try:
            if not enable_subtitles:
                # 如果禁用字幕，直接复制原视频
                logger.info("字幕显示已禁用，复制原视频")
                return self._copy_video_without_subtitles(video_path, output_path)
            
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
            if not os.path.exists(subtitle_path):
                raise FileNotFoundError(f"字幕文件不存在: {subtitle_path}")
            
            target_language = language or self.language_manager.current_language
            language_config = self.language_manager.get_language_config(target_language)
            
            # 使用提供的字幕设置或默认设置
            if subtitle_settings is None:
                subtitle_settings = language_config.subtitle_settings
            
            # 获取语言特定字体
            fonts = self.subtitle_service.get_language_specific_fonts(target_language)
            font_family = fonts[0] if fonts else "Arial"
            
            # 构建FFmpeg字幕嵌入命令
            cmd = self._build_subtitle_embed_command(
                video_path, subtitle_path, output_path, 
                font_family, subtitle_settings
            )
            
            logger.info(f"开始嵌入字幕: {video_path} -> {output_path}")
            logger.debug(f"FFmpeg命令: {' '.join(cmd)}")
            
            # 执行FFmpeg命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"字幕嵌入成功: {output_path}")
                return output_path
            else:
                error_msg = result.stderr or "未知错误"
                logger.error(f"字幕嵌入失败: {error_msg}")
                raise Exception(f"FFmpeg执行失败: {error_msg}")
                
        except Exception as e:
            logger.error(f"字幕嵌入失败: {e}")
            raise
    
    def embed_subtitles_from_segments(self,
                                    video_path: str,
                                    text_segments: List[TextSegment],
                                    output_path: str,
                                    language: Optional[LanguageCode] = None,
                                    subtitle_settings: Optional[SubtitleSettings] = None,
                                    enable_subtitles: bool = True) -> str:
        """
        从文本段落直接嵌入字幕到视频中
        
        Args:
            video_path: 输入视频文件路径
            text_segments: 文本段落列表
            output_path: 输出视频文件路径
            language: 语言代码
            subtitle_settings: 字幕样式设置
            enable_subtitles: 是否启用字幕显示
            
        Returns:
            str: 输出视频路径
        """
        try:
            if not enable_subtitles:
                return self._copy_video_without_subtitles(video_path, output_path)
            
            # 生成临时SRT文件
            temp_srt_path = os.path.join(self.temp_dir, "temp_subtitles.srt")
            self.subtitle_service.generate_srt_file(text_segments, temp_srt_path, language)
            
            # 嵌入字幕
            return self.embed_subtitles_in_video(
                video_path, temp_srt_path, output_path, 
                language, subtitle_settings, enable_subtitles
            )
            
        except Exception as e:
            logger.error(f"从文本段落嵌入字幕失败: {e}")
            raise
    
    def create_subtitle_preview(self,
                              text_segments: List[TextSegment],
                              language: Optional[LanguageCode] = None,
                              subtitle_settings: Optional[SubtitleSettings] = None) -> Dict[str, Any]:
        """
        创建字幕预览
        
        Args:
            text_segments: 文本段落列表
            language: 语言代码
            subtitle_settings: 字幕样式设置
            
        Returns:
            Dict[str, Any]: 预览信息
        """
        try:
            target_language = language or self.language_manager.current_language
            
            # 获取基本预览信息
            preview_data = self.subtitle_service.get_subtitle_preview(text_segments, target_language)
            
            # 添加样式预览信息
            if subtitle_settings is None:
                language_config = self.language_manager.get_language_config(target_language)
                subtitle_settings = language_config.subtitle_settings
            
            preview_data.update({
                'subtitle_settings': {
                    'font_family': subtitle_settings.font_family,
                    'font_size': subtitle_settings.font_size,
                    'font_color': subtitle_settings.font_color,
                    'background_color': subtitle_settings.background_color,
                    'position': subtitle_settings.position,
                    'line_spacing': subtitle_settings.line_spacing,
                    'max_chars_per_line': subtitle_settings.max_chars_per_line
                },
                'preview_srt_content': self._generate_preview_srt(text_segments[:3])  # 只预览前3个段落
            })
            
            logger.info(f"字幕预览创建成功，共 {len(text_segments)} 个段落")
            return preview_data
            
        except Exception as e:
            logger.error(f"创建字幕预览失败: {e}")
            raise
    
    def toggle_subtitle_display(self,
                              video_with_subtitles_path: str,
                              original_video_path: str,
                              output_path: str,
                              enable_subtitles: bool) -> str:
        """
        切换字幕显示状态
        
        Args:
            video_with_subtitles_path: 带字幕的视频路径
            original_video_path: 原始视频路径
            output_path: 输出视频路径
            enable_subtitles: 是否启用字幕
            
        Returns:
            str: 输出视频路径
        """
        try:
            if enable_subtitles:
                # 启用字幕，使用带字幕的视频
                source_path = video_with_subtitles_path
                logger.info("启用字幕显示")
            else:
                # 禁用字幕，使用原始视频
                source_path = original_video_path
                logger.info("禁用字幕显示")
            
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"源视频文件不存在: {source_path}")
            
            # 复制视频文件
            return self._copy_video_without_subtitles(source_path, output_path)
            
        except Exception as e:
            logger.error(f"切换字幕显示失败: {e}")
            raise
    
    def _build_subtitle_embed_command(self,
                                    video_path: str,
                                    subtitle_path: str,
                                    output_path: str,
                                    font_family: str,
                                    subtitle_settings: SubtitleSettings) -> List[str]:
        """
        构建字幕嵌入的FFmpeg命令
        
        Args:
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径
            output_path: 输出文件路径
            font_family: 字体名称
            subtitle_settings: 字幕设置
            
        Returns:
            List[str]: FFmpeg命令列表
        """
        # 转义字幕文件路径
        subtitle_path_escaped = subtitle_path.replace('\\', '/').replace(':', '\\\\:')
        
        # 构建字幕样式
        style_parts = [
            f"FontName={font_family}",
            f"FontSize={subtitle_settings.font_size}",
            f"PrimaryColour={self._hex_to_ass_color(subtitle_settings.font_color)}",
            f"BackColour={self._hex_to_ass_color(subtitle_settings.background_color)}",
            f"Outline=2",
            f"OutlineColour=&H000000",  # 黑色描边
        ]
        
        # 设置字幕位置
        if subtitle_settings.position == "bottom":
            style_parts.append("Alignment=2")  # 底部居中
        elif subtitle_settings.position == "top":
            style_parts.append("Alignment=8")  # 顶部居中
        else:
            style_parts.append("Alignment=5")  # 中间居中
        
        style = ",".join(style_parts)
        
        # 构建FFmpeg命令
        cmd = [
            self._get_ffmpeg_path(),
            "-i", video_path,
            "-vf", f"subtitles={subtitle_path_escaped}:force_style='{style}'",
            "-c:a", "copy",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-y",  # 覆盖输出文件
            output_path
        ]
        
        return cmd
    
    def _copy_video_without_subtitles(self, source_path: str, output_path: str) -> str:
        """
        复制视频文件（不包含字幕）
        
        Args:
            source_path: 源视频路径
            output_path: 输出视频路径
            
        Returns:
            str: 输出视频路径
        """
        try:
            cmd = [
                self._get_ffmpeg_path(),
                "-i", source_path,
                "-c", "copy",  # 直接复制，不重新编码
                "-y",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info(f"视频复制成功: {output_path}")
                return output_path
            else:
                error_msg = result.stderr or "未知错误"
                logger.error(f"视频复制失败: {error_msg}")
                raise Exception(f"视频复制失败: {error_msg}")
                
        except Exception as e:
            logger.error(f"复制视频失败: {e}")
            raise
    
    def _generate_preview_srt(self, text_segments: List[TextSegment]) -> str:
        """
        生成预览用的SRT内容
        
        Args:
            text_segments: 文本段落列表
            
        Returns:
            str: SRT格式内容
        """
        return self.subtitle_service.subtitle_generator.generate_srt_content(text_segments)
    
    def _hex_to_ass_color(self, hex_color: str) -> str:
        """
        将十六进制颜色转换为ASS格式
        
        Args:
            hex_color: 十六进制颜色 (#RRGGBB)
            
        Returns:
            str: ASS格式颜色 (&HBBGGRR)
        """
        try:
            hex_color = hex_color.lstrip('#')
            
            if len(hex_color) != 6:
                hex_color = "FFFFFF"  # 默认白色
            
            # 验证是否为有效的十六进制字符
            for char in hex_color:
                if char not in '0123456789ABCDEFabcdef':
                    hex_color = "FFFFFF"  # 默认白色
                    break
            
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            return f"&H{b:02X}{g:02X}{r:02X}"
            
        except (ValueError, IndexError):
            # 如果转换失败，返回默认白色
            return "&HFFFFFF"
    
    def _get_ffmpeg_path(self) -> str:
        """获取FFmpeg可执行文件路径"""
        return self.video_composer.ffmpeg_path
    
    def cleanup(self):
        """清理临时文件"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info("临时文件清理完成")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")