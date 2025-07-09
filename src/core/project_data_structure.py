#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构的项目数据结构管理器
统一管理所有项目数据，避免重复和冗余
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class SceneData:
    """场景数据结构"""
    scene_id: str
    scene_name: str
    scene_description: str
    main_characters: List[str]
    emotional_tone: str
    key_events: List[str]
    transition_suggestion: str
    key_dialogue: str
    voice_guidance: str
    visual_focus: str


@dataclass
class ShotData:
    """镜头数据结构"""
    shot_id: str
    scene_id: str
    shot_original_text: str  # 🔧 新增：镜头对应的原文内容
    shot_type: str
    camera_angle: str
    camera_movement: str
    depth_of_field: str
    composition: str
    lighting: str
    color_tone: str
    characters: List[str]
    scene_description: str
    dialogue_narration: str
    sound_effects: str
    transition: str


@dataclass
class VoiceSegment:
    """配音段落数据结构"""
    segment_id: str
    scene_id: str
    shot_id: str
    original_text: str
    dialogue_text: str
    sound_effect: str
    audio_path: str
    sound_effect_path: str
    duration: float
    status: str  # 未生成/已生成/生成失败
    # 🔧 新增：字幕相关字段
    subtitle_path: str = ""  # 字幕文件路径
    subtitle_data: Optional[List[Dict[str, Any]]] = None  # 字幕数据（时间轴信息）
    subtitle_format: str = "srt"  # 字幕格式（srt/vtt/json）


@dataclass
class ImageData:
    """图像数据结构"""
    image_id: str
    shot_id: str
    image_path: str
    prompt: str
    enhanced_prompt: str
    consistency_prompt: str
    engine: str
    generation_time: str
    is_main: bool


@dataclass
class VideoData:
    """视频数据结构"""
    video_id: str
    shot_id: str
    scene_id: str
    video_path: str
    source_image_path: str
    prompt: str
    duration: float
    fps: int
    width: int
    height: int
    motion_intensity: float
    engine: str
    generation_time: str
    status: str  # 未生成/生成中/已生成/生成失败
    file_size: int = 0
    created_time: str = ""


class ProjectDataStructure:
    """重构的项目数据结构管理器"""
    
    def __init__(self, project_root: str):
        """
        初始化项目数据结构管理器
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root)
        self.project_file = self.project_root / "project.json"
        
        # 确保项目目录存在
        self.project_root.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据结构
        self.data = self._init_data_structure()
        
        logger.info(f"项目数据结构管理器初始化完成: {self.project_root}")
    
    def _init_data_structure(self) -> Dict[str, Any]:
        """初始化项目数据结构"""
        return {
            # 基本项目信息
            "project_info": {
                "project_name": "",
                "description": "",
                "created_time": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat(),
                "version": "2.0"
            },
            
            # 文本内容
            "text_content": {
                "original_text": "",
                "rewritten_text": ""
            },
            
            # 五阶段分镜数据
            "storyboard": {
                # 阶段1：世界观分析
                "world_bible": "",
                "style": "",
                
                # 阶段2：角色场景管理
                "characters": {},  # {character_id: {name, appearance, personality, ...}}
                "scenes": {},      # {scene_id: {name, description, environment, ...}}
                
                # 阶段3：场景分割
                "scene_analysis": [],  # List[SceneData]
                
                # 阶段4：分镜生成
                "shots": [],  # List[ShotData]
                
                # 阶段5：优化预览
                "optimization_suggestions": []
            },
            
            # 配音数据
            "voice_generation": {
                "segments": [],  # List[VoiceSegment]
                "settings": {
                    "engine": "edge_tts",
                    "voice": "zh-CN-XiaoxiaoNeural",
                    "speed": 1.0,
                    "pitch": 1.0
                }
            },
            
            # 图像生成数据
            "image_generation": {
                "images": [],  # List[ImageData]
                "settings": {
                    "engine": "pollinations",
                    "style": "动漫风格",
                    "quality": "高质量"
                }
            },

            # 视频生成数据
            "video_generation": {
                "videos": [],  # List[VideoData]
                "settings": {
                    "engine": "cogvideox_flash",
                    "duration": 5.0,
                    "fps": 30,  # 修改为CogVideoX支持的帧率
                    "motion_intensity": 0.5,
                    "quality": "高质量"
                }
            },
            
            # 工作流程状态
            "workflow_status": {
                "text_creation": False,
                "storyboard_generation": False,
                "voice_generation": False,
                "image_generation": False,
                "video_synthesis": False
            },
            
            # 文件路径映射
            "file_paths": {
                "texts": {},
                "audio": {},
                "images": {},
                "videos": {}
            }
        }
    
    def load_project(self) -> bool:
        """加载项目数据"""
        try:
            if self.project_file.exists():
                with open(self.project_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                
                # 合并数据，保持结构完整性
                self._merge_data(loaded_data)
                
                logger.info(f"项目数据加载成功: {self.project_file}")
                return True
            else:
                logger.info("项目文件不存在，使用默认数据结构")
                return False
                
        except Exception as e:
            logger.error(f"加载项目数据失败: {e}")
            return False
    
    def save_project(self) -> bool:
        """保存项目数据"""
        try:
            # 更新最后修改时间
            self.data["project_info"]["last_modified"] = datetime.now().isoformat()
            
            # 保存到文件
            with open(self.project_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"项目数据保存成功: {self.project_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存项目数据失败: {e}")
            return False
    
    def _merge_data(self, loaded_data: Dict[str, Any]):
        """合并加载的数据与默认结构"""
        def merge_dict(default: Dict, loaded: Dict) -> Dict:
            """递归合并字典"""
            result = default.copy()
            for key, value in loaded.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dict(result[key], value)
                else:
                    result[key] = value
            return result
        
        self.data = merge_dict(self.data, loaded_data)
    
    # 数据访问方法
    def get_project_info(self) -> Dict[str, Any]:
        """获取项目基本信息"""
        return self.data["project_info"]
    
    def get_text_content(self) -> Dict[str, str]:
        """获取文本内容"""
        return self.data["text_content"]
    
    def get_storyboard_data(self) -> Dict[str, Any]:
        """获取分镜数据"""
        return self.data["storyboard"]
    
    def get_voice_data(self) -> Dict[str, Any]:
        """获取配音数据"""
        return self.data["voice_generation"]
    
    def get_image_data(self) -> Dict[str, Any]:
        """获取图像数据"""
        return self.data["image_generation"]

    def get_video_data(self) -> Dict[str, Any]:
        """获取视频数据"""
        return self.data["video_generation"]

    def get_workflow_status(self) -> Dict[str, bool]:
        """获取工作流程状态"""
        return self.data["workflow_status"]
    
    # 数据更新方法
    def update_project_info(self, **kwargs):
        """更新项目信息"""
        self.data["project_info"].update(kwargs)
    
    def update_text_content(self, original_text: Optional[str] = None, rewritten_text: Optional[str] = None):
        """更新文本内容"""
        if original_text is not None:
            self.data["text_content"]["original_text"] = original_text
        if rewritten_text is not None:
            self.data["text_content"]["rewritten_text"] = rewritten_text

    def update_world_bible(self, world_bible: str, style: Optional[str] = None):
        """更新世界观圣经"""
        self.data["storyboard"]["world_bible"] = world_bible
        if style:
            self.data["storyboard"]["style"] = style
    
    def update_scene_analysis(self, scenes_analysis_text: str):
        """更新场景分析数据"""
        # 解析场景分析文本并保存
        scenes = self._parse_scenes_from_text(scenes_analysis_text)
        self.data["storyboard"]["scene_analysis"] = scenes
        self.data["storyboard"]["scene_analysis_text"] = scenes_analysis_text

    def update_shots(self, shots_data: List[Dict]):
        """更新镜头数据"""
        self.data["storyboard"]["shots"] = shots_data

    def _parse_scenes_from_text(self, scenes_text: str) -> List[Dict]:
        """从场景分析文本中解析场景数据 - 简化版本，只解析场景标题"""
        scenes = []
        try:
            lines = scenes_text.split('\n')

            for line in lines:
                line_strip = line.strip()

                if line_strip.startswith('### 场景') or line_strip.startswith('## 场景'):
                    # 提取场景标题
                    scene_title = line_strip.replace('###', '').replace('##', '').strip()
                    parts = scene_title.split('：', 1)
                    if len(parts) == 2:
                        scene_name = parts[1].strip()
                    else:
                        scene_name = scene_title

                    scenes.append({
                        'scene_name': scene_name,
                        'scene_title': scene_title  # 兼容性字段
                    })

        except Exception as e:
            logger.error(f"解析场景文本失败: {e}")

        return scenes
    
    def update_voice_segments(self, segments: List[VoiceSegment]):
        """更新配音段落数据"""
        self.data["voice_generation"]["segments"] = [asdict(segment) for segment in segments]
    
    def update_workflow_status(self, **status):
        """更新工作流程状态"""
        self.data["workflow_status"].update(status)
    
    def add_image(self, image: ImageData):
        """添加图像数据"""
        self.data["image_generation"]["images"].append(asdict(image))

    def add_video(self, video: VideoData):
        """添加视频数据"""
        self.data["video_generation"]["videos"].append(asdict(video))

    def update_video_status(self, video_id: str, status: str, video_path: Optional[str] = None):
        """更新视频状态"""
        for video in self.data["video_generation"]["videos"]:
            if video["video_id"] == video_id:
                video["status"] = status
                if video_path:
                    video["video_path"] = video_path
                break

    def get_all_data(self) -> Dict[str, Any]:
        """获取所有项目数据"""
        return self.data
