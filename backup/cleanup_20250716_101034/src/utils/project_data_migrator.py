#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目数据迁移工具
将现有项目数据迁移到统一的project.json格式
避免创建重复的时间戳文件夹
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from src.utils.logger import logger


class ProjectDataMigrator:
    """项目数据迁移器"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.migrated_projects = []
        
    def migrate_all_projects(self) -> List[str]:
        """迁移所有项目"""
        migrated = []
        
        if not self.output_dir.exists():
            logger.info("输出目录不存在，无需迁移")
            return migrated
            
        for project_dir in self.output_dir.iterdir():
            if project_dir.is_dir():
                try:
                    if self.migrate_project(project_dir):
                        migrated.append(str(project_dir))
                except Exception as e:
                    logger.error(f"迁移项目失败 {project_dir}: {e}")
                    
        return migrated
    
    def migrate_project(self, project_dir: Path) -> bool:
        """迁移单个项目"""
        try:
            project_json = project_dir / "project.json"
            
            # 如果已经有统一的project.json，检查是否需要更新
            if project_json.exists():
                return self._update_existing_project(project_json)
            else:
                return self._create_unified_project_json(project_dir)
                
        except Exception as e:
            logger.error(f"迁移项目失败 {project_dir}: {e}")
            return False
    
    def _update_existing_project(self, project_json: Path) -> bool:
        """更新现有的project.json"""
        try:
            with open(project_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否需要更新数据结构
            updated = False
            
            # 确保有统一的数据结构
            if not self._has_unified_structure(data):
                data = self._merge_to_unified_structure(data)
                updated = True
            
            # 清理重复的时间戳文件夹引用
            if self._clean_timestamp_references(data):
                updated = True
            
            if updated:
                # 创建备份
                backup_path = project_json.with_suffix('.json.backup')
                shutil.copy2(project_json, backup_path)
                
                # 保存更新后的数据
                with open(project_json, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"项目数据已更新: {project_json}")
                
            return True
            
        except Exception as e:
            logger.error(f"更新项目数据失败 {project_json}: {e}")
            return False
    
    def _create_unified_project_json(self, project_dir: Path) -> bool:
        """为项目创建统一的project.json"""
        try:
            # 收集现有数据
            existing_data = self._collect_existing_data(project_dir)
            
            # 创建统一数据结构
            unified_data = self._create_unified_structure(project_dir.name, existing_data)
            
            # 保存到project.json
            project_json = project_dir / "project.json"
            with open(project_json, 'w', encoding='utf-8') as f:
                json.dump(unified_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"统一项目数据已创建: {project_json}")
            return True
            
        except Exception as e:
            logger.error(f"创建统一项目数据失败 {project_dir}: {e}")
            return False
    
    def _collect_existing_data(self, project_dir: Path) -> Dict[str, Any]:
        """收集现有的项目数据"""
        data = {}
        
        # 收集文本文件
        texts_dir = project_dir / "texts"
        if texts_dir.exists():
            for text_file in texts_dir.glob("*.txt"):
                if "original" in text_file.name.lower():
                    data["original_text_file"] = str(text_file)
                elif "rewritten" in text_file.name.lower():
                    data["rewritten_text_file"] = str(text_file)
        
        # 收集分镜数据
        storyboard_files = list(project_dir.glob("**/storyboard*.json"))
        if storyboard_files:
            data["storyboard_file"] = str(storyboard_files[0])
        
        # 收集图片文件
        images_dir = project_dir / "images"
        if images_dir.exists():
            data["image_files"] = [str(f) for f in images_dir.rglob("*.png")]
            data["image_files"].extend([str(f) for f in images_dir.rglob("*.jpg")])
        
        # 收集音频文件
        audio_dir = project_dir / "audio"
        if audio_dir.exists():
            data["audio_files"] = [str(f) for f in audio_dir.rglob("*.wav")]
            data["audio_files"].extend([str(f) for f in audio_dir.rglob("*.mp3")])
        
        # 收集视频文件
        videos_dir = project_dir / "videos"
        if videos_dir.exists():
            data["video_files"] = [str(f) for f in videos_dir.rglob("*.mp4")]
        
        return data
    
    def _create_unified_structure(self, project_name: str, existing_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建统一的数据结构"""
        return {
            "project_name": project_name,
            "created_time": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "version": "2.0",
            
            # 文本内容
            "original_text": "",
            "rewritten_text": "",
            
            # 五阶段分镜系统
            "five_stage_storyboard": {},
            
            # 图像生成 - 统一管理所有绘图数据
            "image_generation": {
                "settings": {
                    "default_engine": "pollinations",
                    "style": "动漫风格",
                    "quality": "高质量",
                    "resolution": "1024x1024"
                },
                "generated_images": {},
                "shot_image_mappings": {},
                "generation_history": [],
                "prompt_templates": {},
                "character_consistency": {}
            },
            
            # 配音功能 - 统一管理所有配音数据
            "voice_generation": {
                "settings": {
                    "default_voice_engine": "Azure TTS",
                    "voice_speed": 1.0,
                    "voice_volume": 1.0,
                    "output_format": "wav"
                },
                "character_voices": {},
                "shot_voice_mappings": {},
                "voice_segments": [],
                "generated_files": {},
                "generation_history": []
            },
            
            # 字幕功能 - 统一管理所有字幕数据
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
                "shot_subtitle_mappings": {},
                "subtitle_files": {},
                "subtitle_data": {},
                "generation_history": []
            },
            
            # 视频生成 - 统一管理所有视频数据
            "video_generation": {
                "settings": {
                    "default_engine": "Runway ML",
                    "video_duration": 5.0,
                    "video_fps": 24,
                    "video_resolution": "1920x1080",
                    "motion_intensity": 0.5
                },
                "generated_videos": {},
                "shot_video_mappings": {},
                "generation_history": [],
                "video_segments": [],
                "processing_queue": []
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
            
            # 文件路径映射（从现有数据迁移）
            "files": existing_data
        }
    
    def _has_unified_structure(self, data: Dict[str, Any]) -> bool:
        """检查是否有统一的数据结构"""
        required_sections = [
            "voice_generation",
            "subtitle_generation", 
            "image_generation",
            "video_generation",
            "project_status"
        ]
        
        return all(section in data for section in required_sections)
    
    def _merge_to_unified_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """将现有数据合并到统一结构"""
        # 创建新的统一结构
        project_name = data.get("project_name", "Unknown Project")
        unified = self._create_unified_structure(project_name, {})
        
        # 合并现有数据
        for key, value in data.items():
            if key in unified:
                if isinstance(value, dict) and isinstance(unified[key], dict):
                    unified[key].update(value)
                else:
                    unified[key] = value
        
        return unified
    
    def _clean_timestamp_references(self, data: Dict[str, Any]) -> bool:
        """清理时间戳文件夹引用"""
        cleaned = False
        
        # 递归清理所有路径引用中的时间戳文件夹
        def clean_paths(obj):
            nonlocal cleaned
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and self._is_timestamp_path(value):
                        obj[key] = self._remove_timestamp_from_path(value)
                        cleaned = True
                    elif isinstance(value, (dict, list)):
                        clean_paths(value)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, str) and self._is_timestamp_path(item):
                        obj[i] = self._remove_timestamp_from_path(item)
                        cleaned = True
                    elif isinstance(item, (dict, list)):
                        clean_paths(item)
        
        clean_paths(data)
        return cleaned
    
    def _is_timestamp_path(self, path: str) -> bool:
        """检查路径是否包含时间戳文件夹"""
        import re
        # 匹配形如 _20241226_123456 的时间戳
        timestamp_pattern = r'_\d{8}_\d{6}'
        return bool(re.search(timestamp_pattern, path))
    
    def _remove_timestamp_from_path(self, path: str) -> str:
        """从路径中移除时间戳"""
        import re
        timestamp_pattern = r'_\d{8}_\d{6}'
        return re.sub(timestamp_pattern, '', path)
    
    def remove_duplicate_timestamp_folders(self) -> List[str]:
        """移除重复的时间戳文件夹"""
        removed_folders = []
        
        if not self.output_dir.exists():
            return removed_folders
        
        # 找到所有时间戳文件夹
        timestamp_folders = []
        for item in self.output_dir.iterdir():
            if item.is_dir() and self._is_timestamp_folder(item.name):
                timestamp_folders.append(item)
        
        # 按基础名称分组
        folder_groups = {}
        for folder in timestamp_folders:
            base_name = self._get_base_name(folder.name)
            if base_name not in folder_groups:
                folder_groups[base_name] = []
            folder_groups[base_name].append(folder)
        
        # 对于每个组，保留最新的，删除其他的
        for base_name, folders in folder_groups.items():
            if len(folders) > 1:
                # 按修改时间排序，保留最新的
                folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                
                # 检查是否有非时间戳的原始文件夹
                original_folder = self.output_dir / base_name
                if original_folder.exists() and original_folder.is_dir():
                    # 如果原始文件夹存在，删除所有时间戳文件夹
                    for folder in folders:
                        try:
                            shutil.rmtree(folder)
                            removed_folders.append(str(folder))
                            logger.info(f"已删除重复的时间戳文件夹: {folder}")
                        except Exception as e:
                            logger.error(f"删除文件夹失败 {folder}: {e}")
                else:
                    # 保留最新的，删除其他的
                    for folder in folders[1:]:
                        try:
                            shutil.rmtree(folder)
                            removed_folders.append(str(folder))
                            logger.info(f"已删除重复的时间戳文件夹: {folder}")
                        except Exception as e:
                            logger.error(f"删除文件夹失败 {folder}: {e}")
        
        return removed_folders
    
    def _is_timestamp_folder(self, folder_name: str) -> bool:
        """检查是否是时间戳文件夹"""
        import re
        timestamp_pattern = r'.*_\d{8}_\d{6}$'
        return bool(re.match(timestamp_pattern, folder_name))
    
    def _get_base_name(self, folder_name: str) -> str:
        """获取文件夹的基础名称（去除时间戳）"""
        import re
        timestamp_pattern = r'_\d{8}_\d{6}$'
        return re.sub(timestamp_pattern, '', folder_name)
