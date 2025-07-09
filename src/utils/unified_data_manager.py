#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一数据管理器
确保所有功能数据都保存在project.json中，避免分散保存
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class UnifiedDataManager:
    """统一数据管理器 - 确保所有功能数据都保存在project.json中"""
    
    def __init__(self, project_path: str):
        """
        初始化统一数据管理器
        
        Args:
            project_path: 项目路径
        """
        self.project_path = Path(project_path)
        self.project_json_path = self.project_path / "project.json"
        self._data = {}
        self._load_project_data()
    
    def _load_project_data(self):
        """加载项目数据"""
        try:
            if self.project_json_path.exists():
                with open(self.project_json_path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                logger.info(f"项目数据加载成功: {self.project_json_path}")
            else:
                self._data = self._create_default_structure()
                logger.info("创建默认项目数据结构")
        except Exception as e:
            logger.error(f"加载项目数据失败: {e}")
            self._data = self._create_default_structure()
    
    def _create_default_structure(self) -> Dict[str, Any]:
        """创建默认的项目数据结构"""
        return {
            "project_name": "",
            "created_time": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "project_root": str(self.project_path),
            "project_dir": str(self.project_path),
            
            # 文本内容
            "original_text": "",
            "rewritten_text": "",
            
            # 五阶段分镜系统
            "five_stage_storyboard": {},
            
            # 图像生成
            "image_generation": {},
            "image_generation_settings": {},
            "shot_image_mappings": {},
            
            # 配音功能
            "voice_generation": {
                "settings": {
                    "default_voice_engine": "Azure TTS",
                    "voice_speed": 1.0,
                    "voice_volume": 1.0,
                    "output_format": "wav"
                },
                "character_voices": {},
                "shot_voice_mappings": {}
            },
            
            # 字幕功能
            "subtitle_generation": {
                "settings": {
                    "font_family": "微软雅黑",
                    "font_size": 24,
                    "font_color": "#FFFFFF",
                    "background_color": "#000000",
                    "background_opacity": 0.7,
                    "position": "bottom",
                    "margin": 50
                },
                "shot_subtitle_mappings": {}
            },
            
            # 图生视频功能
            "image_to_video": {
                "settings": {
                    "default_engine": "Runway ML",
                    "video_duration": 5.0,
                    "video_fps": 24,
                    "video_resolution": "1920x1080",
                    "motion_intensity": 0.5
                },
                "shot_video_mappings": {}
            },
            
            # 视频合成功能
            "video_composition": {
                "settings": {
                    "output_resolution": "1920x1080",
                    "output_fps": 24,
                    "output_format": "mp4",
                    "video_codec": "h264",
                    "audio_codec": "aac",
                    "bitrate": "5000k"
                },
                "composition_timeline": {
                    "total_duration": 0.0,
                    "scenes": []
                },
                "output_files": {},
                "composition_history": []
            },
            
            # 项目状态管理
            "project_status": {
                "workflow_progress": {
                    "text_creation": "not_started",
                    "storyboard_generation": "not_started",
                    "image_generation": "not_started",
                    "voice_generation": "not_started",
                    "subtitle_generation": "not_started",
                    "video_generation": "not_started",
                    "final_composition": "not_started"
                },
                "statistics": {
                    "total_scenes": 0,
                    "total_shots": 0,
                    "generated_images": 0,
                    "generated_voices": 0,
                    "generated_videos": 0,
                    "completion_percentage": 0.0
                }
            },
            
            # 其他现有字段
            "drawing_settings": {},
            "voice_settings": {},
            "workflow_settings": {},
            "progress_status": {},
            "files": {}
        }
    
    def save_data(self, backup: bool = True) -> bool:
        """
        保存项目数据到project.json
        
        Args:
            backup: 是否创建备份
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 更新最后修改时间
            self._data['last_modified'] = datetime.now().isoformat()
            
            # 创建备份
            if backup and self.project_json_path.exists():
                # 使用简洁的备份文件名，不包含时间戳
                backup_path = self.project_json_path.with_suffix('.json.backup')
                import shutil
                shutil.copy2(self.project_json_path, backup_path)
                logger.info(f"备份已创建: {backup_path}")
            
            # 保存数据
            with open(self.project_json_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"项目数据已保存: {self.project_json_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存项目数据失败: {e}")
            return False
    
    def get_data(self, key_path: str = None) -> Any:
        """
        获取项目数据
        
        Args:
            key_path: 数据路径，如 "voice_generation.settings"
            
        Returns:
            Any: 数据内容
        """
        if key_path is None:
            return self._data
        
        keys = key_path.split('.')
        data = self._data
        
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return None
        
        return data
    
    def set_data(self, key_path: str, value: Any, auto_save: bool = True) -> bool:
        """
        设置项目数据
        
        Args:
            key_path: 数据路径，如 "voice_generation.settings.voice_speed"
            value: 要设置的值
            auto_save: 是否自动保存
            
        Returns:
            bool: 设置是否成功
        """
        try:
            keys = key_path.split('.')
            data = self._data
            
            # 导航到目标位置
            for key in keys[:-1]:
                if key not in data:
                    data[key] = {}
                data = data[key]
            
            # 设置值
            data[keys[-1]] = value
            
            if auto_save:
                return self.save_data()
            
            return True
            
        except Exception as e:
            logger.error(f"设置数据失败: {key_path} = {value}, 错误: {e}")
            return False
    
    def update_voice_mapping(self, scene_id: str, shot_id: str, voice_data: Dict[str, Any]) -> bool:
        """更新镜头配音映射"""
        shot_key = f"{scene_id}_{shot_id}"
        return self.set_data(f"voice_generation.shot_voice_mappings.{shot_key}", voice_data)
    
    def update_subtitle_mapping(self, scene_id: str, shot_id: str, subtitle_data: Dict[str, Any]) -> bool:
        """更新镜头字幕映射"""
        shot_key = f"{scene_id}_{shot_id}"
        return self.set_data(f"subtitle_generation.shot_subtitle_mappings.{shot_key}", subtitle_data)
    
    def update_video_mapping(self, scene_id: str, shot_id: str, video_data: Dict[str, Any]) -> bool:
        """更新镜头视频映射"""
        shot_key = f"{scene_id}_{shot_id}"
        return self.set_data(f"image_to_video.shot_video_mappings.{shot_key}", video_data)
    
    def update_project_status(self, workflow_step: str, status: str) -> bool:
        """更新项目工作流状态"""
        return self.set_data(f"project_status.workflow_progress.{workflow_step}", status)
    
    def get_shot_data(self, scene_id: str, shot_id: str) -> Dict[str, Any]:
        """获取镜头的完整数据"""
        shot_key = f"{scene_id}_{shot_id}"
        
        return {
            "image": self.get_data(f"shot_image_mappings.{shot_key}"),
            "voice": self.get_data(f"voice_generation.shot_voice_mappings.{shot_key}"),
            "subtitle": self.get_data(f"subtitle_generation.shot_subtitle_mappings.{shot_key}"),
            "video": self.get_data(f"image_to_video.shot_video_mappings.{shot_key}")
        }
    
    def ensure_data_structure(self) -> bool:
        """确保数据结构完整"""
        try:
            default_structure = self._create_default_structure()
            
            def merge_structure(current: dict, default: dict):
                for key, value in default.items():
                    if key not in current:
                        current[key] = value
                    elif isinstance(value, dict) and isinstance(current[key], dict):
                        merge_structure(current[key], value)
            
            merge_structure(self._data, default_structure)
            return self.save_data()
            
        except Exception as e:
            logger.error(f"确保数据结构失败: {e}")
            return False
