#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语言管理相关数据模型
定义语言配置、项目语言设置、字幕设置等数据结构
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class LanguageCode(Enum):
    """支持的语言代码枚举"""
    CHINESE = "zh-CN"
    ENGLISH = "en-US"


class TextDirection(Enum):
    """文本方向枚举"""
    LEFT_TO_RIGHT = "ltr"
    RIGHT_TO_LEFT = "rtl"


class SubtitlePosition(Enum):
    """字幕位置枚举"""
    BOTTOM = "bottom"
    TOP = "top"
    CENTER = "center"


class WordWrapStyle(Enum):
    """换行样式枚举"""
    CHARACTER = "character"  # 按字符换行（中文）
    WORD = "word"  # 按单词换行（英文）


@dataclass
class SubtitleSettings:
    """字幕设置配置"""
    font_family: str = "Microsoft YaHei"
    font_size: int = 24
    font_color: str = "#FFFFFF"
    background_color: str = "#000000"
    background_opacity: float = 0.7
    position: SubtitlePosition = SubtitlePosition.BOTTOM
    line_spacing: float = 1.2
    max_chars_per_line: int = 20
    word_wrap_style: WordWrapStyle = WordWrapStyle.CHARACTER
    margin_bottom: int = 50
    stroke_color: str = "#000000"
    stroke_width: int = 2
    # 新增字幕样式自定义选项
    font_weight: str = "normal"  # normal, bold
    font_style: str = "normal"   # normal, italic
    text_align: str = "center"   # left, center, right
    shadow_enabled: bool = True
    shadow_color: str = "#000000"
    shadow_offset_x: int = 2
    shadow_offset_y: int = 2
    shadow_blur: int = 3
    border_enabled: bool = True
    border_color: str = "#000000"
    border_width: int = 2
    background_enabled: bool = False
    background_padding: int = 10
    animation_enabled: bool = False
    animation_type: str = "fade"  # fade, slide, typewriter
    duration_multiplier: float = 1.0  # 字幕显示时长倍数
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'font_family': self.font_family,
            'font_size': self.font_size,
            'font_color': self.font_color,
            'background_color': self.background_color,
            'background_opacity': self.background_opacity,
            'position': self.position.value,
            'line_spacing': self.line_spacing,
            'max_chars_per_line': self.max_chars_per_line,
            'word_wrap_style': self.word_wrap_style.value,
            'margin_bottom': self.margin_bottom,
            'stroke_color': self.stroke_color,
            'stroke_width': self.stroke_width,
            'font_weight': self.font_weight,
            'font_style': self.font_style,
            'text_align': self.text_align,
            'shadow_enabled': self.shadow_enabled,
            'shadow_color': self.shadow_color,
            'shadow_offset_x': self.shadow_offset_x,
            'shadow_offset_y': self.shadow_offset_y,
            'shadow_blur': self.shadow_blur,
            'border_enabled': self.border_enabled,
            'border_color': self.border_color,
            'border_width': self.border_width,
            'background_enabled': self.background_enabled,
            'background_padding': self.background_padding,
            'animation_enabled': self.animation_enabled,
            'animation_type': self.animation_type,
            'duration_multiplier': self.duration_multiplier
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubtitleSettings':
        """从字典创建实例"""
        return cls(
            font_family=data.get('font_family', 'Microsoft YaHei'),
            font_size=data.get('font_size', 24),
            font_color=data.get('font_color', '#FFFFFF'),
            background_color=data.get('background_color', '#000000'),
            background_opacity=data.get('background_opacity', 0.7),
            position=SubtitlePosition(data.get('position', 'bottom')),
            line_spacing=data.get('line_spacing', 1.2),
            max_chars_per_line=data.get('max_chars_per_line', 20),
            word_wrap_style=WordWrapStyle(data.get('word_wrap_style', 'character')),
            margin_bottom=data.get('margin_bottom', 50),
            stroke_color=data.get('stroke_color', '#000000'),
            stroke_width=data.get('stroke_width', 2),
            font_weight=data.get('font_weight', 'normal'),
            font_style=data.get('font_style', 'normal'),
            text_align=data.get('text_align', 'center'),
            shadow_enabled=data.get('shadow_enabled', True),
            shadow_color=data.get('shadow_color', '#000000'),
            shadow_offset_x=data.get('shadow_offset_x', 2),
            shadow_offset_y=data.get('shadow_offset_y', 2),
            shadow_blur=data.get('shadow_blur', 3),
            border_enabled=data.get('border_enabled', True),
            border_color=data.get('border_color', '#000000'),
            border_width=data.get('border_width', 2),
            background_enabled=data.get('background_enabled', False),
            background_padding=data.get('background_padding', 10),
            animation_enabled=data.get('animation_enabled', False),
            animation_type=data.get('animation_type', 'fade'),
            duration_multiplier=data.get('duration_multiplier', 1.0)
        )


@dataclass
class VoiceSettings:
    """语音设置配置"""
    default_voice_id: str
    default_voice_name: str
    default_speed: float = 1.0
    default_pitch: int = 0
    default_volume: float = 1.0
    supported_voices: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'default_voice_id': self.default_voice_id,
            'default_voice_name': self.default_voice_name,
            'default_speed': self.default_speed,
            'default_pitch': self.default_pitch,
            'default_volume': self.default_volume,
            'supported_voices': self.supported_voices
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VoiceSettings':
        """从字典创建实例"""
        return cls(
            default_voice_id=data.get('default_voice_id', ''),
            default_voice_name=data.get('default_voice_name', ''),
            default_speed=data.get('default_speed', 1.0),
            default_pitch=data.get('default_pitch', 0),
            default_volume=data.get('default_volume', 1.0),
            supported_voices=data.get('supported_voices', [])
        )


@dataclass
class LanguageConfig:
    """语言配置模型"""
    code: LanguageCode
    name: str
    display_name: str
    text_direction: TextDirection = TextDirection.LEFT_TO_RIGHT
    character_encoding: str = "utf-8"
    subtitle_settings: SubtitleSettings = field(default_factory=SubtitleSettings)
    voice_settings: VoiceSettings = field(default_factory=lambda: VoiceSettings("", ""))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'code': self.code.value,
            'name': self.name,
            'display_name': self.display_name,
            'text_direction': self.text_direction.value,
            'character_encoding': self.character_encoding,
            'subtitle_settings': self.subtitle_settings.to_dict(),
            'voice_settings': self.voice_settings.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LanguageConfig':
        """从字典创建实例"""
        return cls(
            code=LanguageCode(data.get('code', 'zh-CN')),
            name=data.get('name', ''),
            display_name=data.get('display_name', ''),
            text_direction=TextDirection(data.get('text_direction', 'ltr')),
            character_encoding=data.get('character_encoding', 'utf-8'),
            subtitle_settings=SubtitleSettings.from_dict(data.get('subtitle_settings', {})),
            voice_settings=VoiceSettings.from_dict(data.get('voice_settings', {}))
        )


@dataclass
class ProjectLanguageSettings:
    """项目语言设置模型"""
    primary_language: LanguageCode
    content_language: LanguageCode
    voice_language: LanguageCode
    subtitle_language: LanguageCode
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'primary_language': self.primary_language.value,
            'content_language': self.content_language.value,
            'voice_language': self.voice_language.value,
            'subtitle_language': self.subtitle_language.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectLanguageSettings':
        """从字典创建实例"""
        return cls(
            primary_language=LanguageCode(data.get('primary_language', 'zh-CN')),
            content_language=LanguageCode(data.get('content_language', 'zh-CN')),
            voice_language=LanguageCode(data.get('voice_language', 'zh-CN')),
            subtitle_language=LanguageCode(data.get('subtitle_language', 'zh-CN')),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        )
    
    def update_timestamp(self):
        """更新时间戳"""
        self.updated_at = datetime.now()


@dataclass
class VoiceModel:
    """语音模型配置"""
    id: str
    name: str
    language: LanguageCode
    gender: str
    style: str
    provider: str
    sample_rate: int = 16000
    supported_formats: List[str] = field(default_factory=lambda: ["mp3", "wav"])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'language': self.language.value,
            'gender': self.gender,
            'style': self.style,
            'provider': self.provider,
            'sample_rate': self.sample_rate,
            'supported_formats': self.supported_formats
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VoiceModel':
        """从字典创建实例"""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            language=LanguageCode(data.get('language', 'zh-CN')),
            gender=data.get('gender', ''),
            style=data.get('style', ''),
            provider=data.get('provider', ''),
            sample_rate=data.get('sample_rate', 16000),
            supported_formats=data.get('supported_formats', ['mp3', 'wav'])
        )


# 预定义的语言配置
DEFAULT_LANGUAGE_CONFIGS = {
    LanguageCode.CHINESE: LanguageConfig(
        code=LanguageCode.CHINESE,
        name="中文",
        display_name="中文 (简体)",
        text_direction=TextDirection.LEFT_TO_RIGHT,
        character_encoding="utf-8",
        subtitle_settings=SubtitleSettings(
            font_family="Microsoft YaHei",
            font_size=24,
            max_chars_per_line=20,
            word_wrap_style=WordWrapStyle.CHARACTER
        ),
        voice_settings=VoiceSettings(
            default_voice_id="zh-CN-YunxiNeural",
            default_voice_name="云希-男声",
            supported_voices=[
                "zh-CN-YunxiNeural",
                "zh-CN-XiaoxiaoNeural",
                "zh-CN-YunyangNeural",
                "zh-CN-XiaoyiNeural"
            ]
        )
    ),
    LanguageCode.ENGLISH: LanguageConfig(
        code=LanguageCode.ENGLISH,
        name="English",
        display_name="English (US)",
        text_direction=TextDirection.LEFT_TO_RIGHT,
        character_encoding="utf-8",
        subtitle_settings=SubtitleSettings(
            font_family="Arial",
            font_size=22,
            max_chars_per_line=40,
            word_wrap_style=WordWrapStyle.WORD
        ),
        voice_settings=VoiceSettings(
            default_voice_id="en-US-AvaNeural",
            default_voice_name="Ava",
            supported_voices=[
                "en-US-AvaNeural",
                "en-US-AndrewNeural",
                "en-US-EmmaNeural",
                "en-US-BrianNeural",
                "en-US-AnaNeural",
                "en-US-AndrewMultilingualNeural"
            ]
        )
    )
}