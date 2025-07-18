#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目管理器
管理AI视频生成项目的创建、保存、文件组织等功能
"""

import os
import json
import time
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from src.utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class ProjectManager:
    """项目管理器"""

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, base_output_dir: str = "output"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, base_output_dir: str = "output"):
        # 避免重复初始化
        if ProjectManager._initialized:
            return

        self.base_output_dir = Path(base_output_dir)
        self.current_project: Optional[Dict[str, Any]] = None

        # 确保输出目录存在
        self.base_output_dir.mkdir(exist_ok=True)

        ProjectManager._initialized = True
        logger.info(f"项目管理器初始化，项目保存目录: {self.base_output_dir}")
    
    def create_new_project(self, project_name: str, project_description: str = "") -> bool:
        """创建新项目"""
        try:
            # 清理项目名称
            clean_name = self._clean_project_name(project_name)
            
            # 创建项目目录
            project_dir = os.path.join(self.base_output_dir, clean_name)
            # 如果目录已存在，直接使用现有目录，不再创建时间戳后缀
            # 这样可以避免产生重复的时间戳文件夹
            
            # 创建项目结构
            self._create_project_structure(Path(project_dir))
            
            # 获取用户设置的默认值
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            
            # 获取默认风格设置
            default_style = config_manager.get_setting("default_style", "电影风格")
            default_language = config_manager.get_setting("default_language", "zh-CN")
            default_image_quality = config_manager.get_setting("default_image_quality", "high")
            default_image_resolution = config_manager.get_setting("default_image_resolution", "1024x1024")
            default_video_resolution = config_manager.get_setting("default_video_resolution", "1920x1080")
            default_video_format = config_manager.get_setting("default_video_format", "mp4")
            default_subtitle_format = config_manager.get_setting("default_subtitle_format", "srt")
            default_font_family = config_manager.get_setting("default_font_family", "Arial")
            
            # 创建项目配置
            now_str = datetime.now().isoformat()
            project_config = {
                "project_name": project_name,
                "project_description": project_description,
                "project_dir": project_dir,
                "created_at": now_str,
                "created_time": now_str,
                "last_modified": now_str,
                "version": "2.0",
                "files": {
                    "original_text": None,
                    "rewritten_text": None,
                    "storyboard": None,
                    "images": [],
                    "audio": [],
                    "video": None,
                    "subtitles": None
                },
                # 五阶段分镜数据结构
                "five_stage_storyboard": {
                    "stage_data": {
                        "1": {},
                        "2": {},
                        "3": {},
                        "4": {},
                        "5": {}
                    },
                    "current_stage": 1,
                    "selected_characters": [],
                    "selected_scenes": [],
                    "article_text": "",
                    "selected_style": default_style,  # 使用用户设置的默认风格
                    "selected_model": ""
                },
                # 图片生成数据结构
                "image_generation": {
                    "provider": None,  # ComfyUI, Pollinations, etc.
                    "settings": {
                        "style": "realistic",
                        "quality": default_image_quality,  # 使用用户设置的默认质量
                        "resolution": default_image_resolution,  # 使用用户设置的默认分辨率
                        "batch_size": 1
                    },
                    "generated_images": [],
                    "progress": {
                        "total_shots": 0,
                        "completed_shots": 0,
                        "failed_shots": 0,
                        "status": "pending"  # pending, generating, completed, failed
                    }
                },
                # 配音数据结构
                "voice_generation": {
                    "provider": None,  # Azure TTS, OpenAI TTS, etc.
                    "settings": {
                        "voice_name": "",
                        "language": default_language,  # 使用用户设置的默认语言
                        "speed": 1.0,
                        "pitch": 0,
                        "volume": 1.0
                    },
                    "generated_audio": [],
                    "narration_text": "",
                    "progress": {
                        "total_segments": 0,
                        "completed_segments": 0,
                        "failed_segments": 0,
                        "status": "pending"
                    }
                },
                # 🔧 新增：工作流程配置
                "workflow_settings": {
                    "mode": "voice_first",  # voice_first | traditional
                    "voice_first_enabled": True,
                    "image_generation_source": "voice_content",  # voice_content | storyboard_description
                    "auto_generate_images_after_voice": True,
                    "created_time": datetime.now().isoformat()
                },
                # 字幕数据结构
                "subtitle_generation": {
                    "format": default_subtitle_format,  # 使用用户设置的默认字幕格式
                    "settings": {
                        "font_family": default_font_family,  # 使用用户设置的默认字体
                        "font_size": 24,
                        "font_color": "#FFFFFF",
                        "background_color": "#000000",
                        "position": "bottom",
                        "timing_offset": 0
                    },
                    "subtitle_files": [],
                    "subtitle_data": [],
                    "progress": {
                        "status": "pending",
                        "auto_generated": False,
                        "manually_edited": False
                    }
                },
                # 视频合成数据结构
                "video_composition": {
                    "settings": {
                        "resolution": default_video_resolution,  # 使用用户设置的默认视频分辨率
                        "fps": 30,
                        "format": default_video_format,  # 使用用户设置的默认视频格式
                        "quality": default_image_quality,  # 使用用户设置的默认质量
                        "transition_type": "fade",
                        "transition_duration": 0.5
                    },
                    "timeline": {
                        "total_duration": 0,
                        "segments": []
                    },
                    "output_files": {
                        "preview_video": None,
                        "final_video": None,
                        "audio_track": None
                    },
                    "progress": {
                        "status": "pending",
                        "current_step": "",
                        "completion_percentage": 0
                    }
                },
                # 项目统计和元数据
                "project_stats": {
                    "total_shots": 0,
                    "total_characters": 0,
                    "total_scenes": 0,
                    "estimated_duration": 0,
                    "completion_percentage": 0,
                    "last_activity": datetime.now().isoformat()
                },
                # 导出和分享设置
                "export_settings": {
                    "formats": [default_video_format, "mov", "avi"],  # 将用户默认格式放在首位
                    "resolutions": [default_video_resolution, "1280x720", "3840x2160"],  # 将用户默认分辨率放在首位
                    "export_history": [],
                    "sharing_settings": {
                        "watermark": False,
                        "credits": True,
                        "metadata": True
                    }
                },
                # 版本控制和备份
                "version_control": {
                    "current_version": "1.0",
                    "version_history": [],
                    "auto_backup": True,
                    "backup_interval": 300,  # 5分钟
                    "max_backups": 10
                },
                # 🔧 新增：发布内容保存
                "publish_content": {
                    "title": "",
                    "description": "",
                    "tags": "",
                    "cover_image_path": "",
                    "selected_platforms": [],
                    "last_generated_time": "",
                    "ai_optimization_history": []
                }
            }
            
            # 保存项目配置
            project_file = os.path.join(project_dir, "project.json")
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_config, f, ensure_ascii=False, indent=2)
            
            # 设置当前项目
            self.current_project = project_config
            
            logger.info(f"项目创建成功: {project_name}")
            return True
            
        except Exception as e:
            logger.error(f"创建项目失败: {e}")
            return False

    def _clean_project_name(self, name: str) -> str:
        """清理项目名称，移除不合法的文件名字符"""
        # 移除/替换不合法字符
        invalid_chars = '<>:"/\\|?*'
        clean_name = name
        for char in invalid_chars:
            clean_name = clean_name.replace(char, '_')
        
        # 移除前后空格并限制长度
        clean_name = clean_name.strip()[:50]
        
        # 如果为空，使用默认名称
        if not clean_name:
            # 使用简洁的默认名称，不包含时间戳
            clean_name = "Project_Default"
        
        return clean_name
    
    def _create_project_structure(self, project_dir: Path):
        """创建项目目录结构"""
        directories = [
            "texts",        # 文本文件（原始、改写后）
            "storyboard",   # 分镜脚本
            "images",       # 生成的图片
            "audio",        # 音频文件
            "video",        # 视频文件
            "assets",       # 其他资源
            "exports"       # 导出文件
        ]
        
        project_dir.mkdir(exist_ok=True)
        
        for dir_name in directories:
            (project_dir / dir_name).mkdir(exist_ok=True)
        
        logger.info(f"项目目录结构创建完成: {project_dir}")
    
    def load_project(self, project_path: str) -> Dict[str, Any]:
        """加载现有项目"""
        try:
            project_file = Path(project_path)
            
            # 如果是目录，查找project.json
            if project_file.is_dir():
                project_file = project_file / "project.json"
            
            if not project_file.exists():
                raise FileNotFoundError(f"项目文件不存在: {project_file}")
            
            with open(project_file, 'r', encoding='utf-8') as f:
                project_config = json.load(f)
            # 兼容旧项目，补全created_time字段
            if "created_time" not in project_config:
                if "created_at" in project_config:
                    project_config["created_time"] = project_config["created_at"]
                else:
                    project_config["created_time"] = datetime.now().isoformat()
            # 更新最后修改时间
            project_config["last_modified"] = datetime.now().isoformat()
            
            self.current_project = project_config

            project_display_name = project_config.get('project_name') or project_config.get('name', '未知项目')

            # 🔧 修复：只在项目首次加载或切换时记录日志，避免频繁记录
            if not hasattr(self, '_last_loaded_project_name') or self._last_loaded_project_name != project_display_name:
                logger.info(f"项目加载成功: {project_display_name}")
                self._last_loaded_project_name = project_display_name

            return project_config
            
        except Exception as e:
            logger.error(f"加载项目失败: {e}")
            raise
    
    def save_project(self) -> bool:
        """保存当前项目"""
        try:
            if not self.current_project:
                raise ValueError("没有当前项目可保存")
            
            # 更新最后修改时间
            self.current_project["last_modified"] = datetime.now().isoformat()
            
            # 保存项目配置
            project_dir = Path(self.current_project["project_dir"])
            config_file = project_dir / "project.json"
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_project, f, ensure_ascii=False, indent=2)
            
            logger.info(f"项目保存成功: {self.current_project['project_name']}")
            return True
            
        except Exception as e:
            logger.error(f"保存项目失败: {e}")
            return False

    def save_publish_content(self, title: str = "", description: str = "", tags: str = "",
                           cover_image_path: str = "", selected_platforms: list = None) -> bool:
        """🔧 新增：保存发布内容到项目"""
        try:
            if not self.current_project:
                logger.warning("没有当前项目，无法保存发布内容")
                return False

            from datetime import datetime

            # 确保publish_content字段存在
            if "publish_content" not in self.current_project:
                self.current_project["publish_content"] = {
                    "title": "",
                    "description": "",
                    "tags": "",
                    "cover_image_path": "",
                    "selected_platforms": [],
                    "last_generated_time": "",
                    "ai_optimization_history": []
                }

            # 保存发布内容
            publish_content = self.current_project["publish_content"]

            if title:
                publish_content["title"] = title
            if description:
                publish_content["description"] = description
            if tags:
                publish_content["tags"] = tags
            if cover_image_path:
                publish_content["cover_image_path"] = cover_image_path
            if selected_platforms is not None:
                publish_content["selected_platforms"] = selected_platforms

            publish_content["last_generated_time"] = datetime.now().isoformat()

            # 保存项目
            success = self.save_project()
            if success:
                logger.info("✅ 发布内容已保存到项目")
            return success

        except Exception as e:
            logger.error(f"保存发布内容失败: {e}")
            return False

    def get_publish_content(self) -> dict:
        """🔧 新增：获取项目的发布内容"""
        try:
            if not self.current_project:
                return {
                    "title": "",
                    "description": "",
                    "tags": "",
                    "cover_image_path": "",
                    "selected_platforms": [],
                    "last_generated_time": "",
                    "ai_optimization_history": []
                }

            # 确保publish_content字段存在
            if "publish_content" not in self.current_project:
                self.current_project["publish_content"] = {
                    "title": "",
                    "description": "",
                    "tags": "",
                    "cover_image_path": "",
                    "selected_platforms": [],
                    "last_generated_time": "",
                    "ai_optimization_history": []
                }
                self.save_project()  # 保存新增的字段

            return self.current_project["publish_content"]

        except Exception as e:
            logger.error(f"获取发布内容失败: {e}")
            return {
                "title": "",
                "description": "",
                "tags": "",
                "cover_image_path": "",
                "selected_platforms": [],
                "last_generated_time": "",
                "ai_optimization_history": []
            }

    def add_ai_optimization_history(self, optimization_data: dict) -> bool:
        """🔧 新增：添加AI优化历史记录"""
        try:
            if not self.current_project:
                return False

            from datetime import datetime

            # 确保publish_content字段存在
            if "publish_content" not in self.current_project:
                self.current_project["publish_content"] = {
                    "title": "",
                    "description": "",
                    "tags": "",
                    "cover_image_path": "",
                    "selected_platforms": [],
                    "last_generated_time": "",
                    "ai_optimization_history": []
                }

            # 添加时间戳
            optimization_data["timestamp"] = datetime.now().isoformat()

            # 添加到历史记录
            history = self.current_project["publish_content"]["ai_optimization_history"]
            history.append(optimization_data)

            # 保持最近10条记录
            if len(history) > 10:
                history[:] = history[-10:]

            # 保存项目
            return self.save_project()

        except Exception as e:
            logger.error(f"添加AI优化历史失败: {e}")
            return False
    
    def get_project_file_path(self, file_type: str, filename: str = None) -> Path:
        """获取项目文件路径"""
        if not self.current_project:
            raise ValueError("没有当前项目")
        
        project_dir = Path(self.current_project["project_dir"])
        
        # 根据文件类型确定子目录
        type_mapping = {
            "original_text": "texts",
            "rewritten_text": "texts", 
            "storyboard": "storyboard",
            "images": "images",
            "audio": "audio",
            "video": "video",
            "final_video": "video",
            "subtitles": "video",
            "exports": "exports"
        }
        
        if file_type not in type_mapping:
            raise ValueError(f"不支持的文件类型: {file_type}")
        
        subdir = project_dir / type_mapping[file_type]
        
        if filename:
            return subdir / filename
        else:
            return subdir
    
    def save_text_content(self, content: str, text_type: str) -> str:
        """保存文本内容"""
        try:
            if text_type == "original_text":
                filename = "original_text.txt"
            elif text_type == "rewritten_text":
                filename = "rewritten_text.txt"
            else:
                raise ValueError(f"不支持的文本类型: {text_type}")
            
            file_path = self.get_project_file_path(text_type, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 更新项目配置
            self.current_project["files"][text_type] = str(file_path)
            self.save_project()
            
            logger.info(f"文本内容已保存: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"保存文本内容失败: {e}")
            raise
    
    def save_storyboard(self, storyboard_data: Dict[str, Any]) -> str:
        """保存分镜数据"""
        try:
            filename = "storyboard.json"
            file_path = self.get_project_file_path("storyboard", filename)
            
            # 添加保存时间戳
            storyboard_data["saved_time"] = datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(storyboard_data, f, ensure_ascii=False, indent=2)
            
            # 更新项目配置
            self.current_project["files"]["storyboard"] = str(file_path)
            self.save_project()
            
            logger.info(f"分镜数据已保存: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"保存分镜数据失败: {e}")
            raise
    
    def save_image(self, image_path: str, shot_id: str = None) -> str:
        """保存图像文件"""
        try:
            source_path = Path(image_path)
            
            if shot_id:
                filename = f"shot_{shot_id}_{source_path.name}"
            else:
                filename = source_path.name
            
            target_path = self.get_project_file_path("images", filename)
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            # 更新项目配置
            if str(target_path) not in self.current_project["files"]["images"]:
                self.current_project["files"]["images"].append(str(target_path))
                self.save_project()
            
            logger.info(f"图像已保存: {target_path}")
            return str(target_path)
            
        except Exception as e:
            logger.error(f"保存图像失败: {e}")
            raise
    
    def save_video(self, video_path: str, video_type: str = "video") -> str:
        """保存视频文件"""
        try:
            source_path = Path(video_path)
            
            if video_type == "final_video":
                filename = f"final_{source_path.name}"
            else:
                filename = source_path.name
            
            target_path = self.get_project_file_path(video_type, filename)
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            # 更新项目配置
            self.current_project["files"][video_type] = str(target_path)
            self.save_project()
            
            logger.info(f"视频已保存: {target_path}")
            return str(target_path)
            
        except Exception as e:
            logger.error(f"保存视频失败: {e}")
            raise
    
    def export_project(self, export_path: str = None) -> str:
        """导出项目"""
        try:
            if not self.current_project:
                raise ValueError("没有当前项目可导出")
            
            if export_path is None:
                # 使用简洁的文件名，不包含时间戳
                export_filename = f"{self.current_project['clean_name']}_export.json"
                export_path = self.get_project_file_path("exports", export_filename)
            
            # 清理和优化项目数据
            cleaned_project_data = self._clean_project_data_for_export(self.current_project)
            
            export_data = {
                "project_info": cleaned_project_data,
                "export_time": datetime.now().isoformat(),
                "exported_by": "AI Video Generator"
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"项目导出成功: {export_path}")
            return str(export_path)
            
        except Exception as e:
            logger.error(f"导出项目失败: {e}")
            raise
    
    def _clean_project_data_for_export(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """清理项目数据用于导出，移除重复和空内容"""
        try:
            # 深拷贝项目数据以避免修改原始数据
            import copy
            cleaned_data = copy.deepcopy(project_data)
            
            # 清理五阶段分镜数据
            if 'five_stage_storyboard' in cleaned_data:
                five_stage_data = cleaned_data['five_stage_storyboard']
                
                # 清理stage_data中的空对象和重复内容
                if 'stage_data' in five_stage_data:
                    stage_data = five_stage_data['stage_data']
                    cleaned_stage_data = {}
                    
                    # 用于去重的world_bible内容
                    seen_world_bibles = set()
                    shared_world_bible = None
                    
                    for stage_key, stage_content in stage_data.items():
                        if isinstance(stage_content, dict) and stage_content:
                            # 移除空的阶段数据
                            if not any(v for v in stage_content.values() if v):
                                continue
                                
                            # 处理world_bible去重
                            if 'world_bible' in stage_content:
                                world_bible = stage_content['world_bible']
                                if world_bible:
                                    if world_bible not in seen_world_bibles:
                                        seen_world_bibles.add(world_bible)
                                        if shared_world_bible is None:
                                            shared_world_bible = world_bible
                                    # 如果是重复的world_bible，移除它
                                    if world_bible == shared_world_bible and len(seen_world_bibles) > 1:
                                        stage_content = stage_content.copy()
                                        del stage_content['world_bible']
                            
                            # 清理storyboard_results中的重复内容
                            if 'storyboard_results' in stage_content:
                                storyboard_results = stage_content['storyboard_results']
                                if isinstance(storyboard_results, list):
                                    # 去重场景
                                    seen_scenes = set()
                                    unique_results = []
                                    for result in storyboard_results:
                                        if isinstance(result, dict):
                                            scene_info = result.get('scene_info', '')
                                            if scene_info and scene_info not in seen_scenes:
                                                seen_scenes.add(scene_info)
                                                unique_results.append(result)
                                    stage_content['storyboard_results'] = unique_results
                            
                            cleaned_stage_data[stage_key] = stage_content
                    
                    # 如果有共享的world_bible，将其提取到顶层
                    if shared_world_bible and len(seen_world_bibles) > 1:
                        five_stage_data['shared_world_bible'] = shared_world_bible
                    
                    five_stage_data['stage_data'] = cleaned_stage_data
                
                # 清理空的选择列表
                if 'selected_characters' in five_stage_data:
                    characters = five_stage_data['selected_characters']
                    if isinstance(characters, list):
                        five_stage_data['selected_characters'] = [c for c in characters if c]
                
                if 'selected_scenes' in five_stage_data:
                    scenes = five_stage_data['selected_scenes']
                    if isinstance(scenes, list):
                        five_stage_data['selected_scenes'] = [s for s in scenes if s]
            
            logger.info("项目数据清理完成，已移除重复和空内容")
            return cleaned_data
            
        except Exception as e:
            logger.error(f"清理项目数据时出错: {e}")
            # 如果清理失败，返回原始数据
            return project_data
    
    def get_project_status(self) -> Dict[str, Any]:
        """获取项目状态"""
        if not self.current_project:
            return {
                "has_project": False,
                "project_name": None,
                "project_dir": None,
                "files_status": {}
            }
        
        files_status = {}
        for file_type, file_path in self.current_project["files"].items():
            if file_type == "images":
                files_status[file_type] = {
                    "exists": len(file_path) > 0 if isinstance(file_path, list) else False,
                    "count": len(file_path) if isinstance(file_path, list) else 0
                }
            else:
                if file_path:
                    files_status[file_type] = {
                        "exists": Path(file_path).exists() if file_path else False,
                        "path": file_path
                    }
                else:
                    files_status[file_type] = {
                        "exists": False,
                        "path": None
                    }
        
        # 检查五阶段分镜脚本状态
        five_stage_data = self.current_project.get('five_stage_storyboard')
        if five_stage_data:
            stage_data = five_stage_data.get('stage_data', {})
            current_stage = five_stage_data.get('current_stage', 1)
            
            # 检查各阶段完成情况
            stage_status = {}
            for stage in range(1, 6):
                stage_status[f"stage_{stage}"] = bool(stage_data.get(stage))
            
            files_status["storyboard"] = {
                "exists": current_stage >= 4 and bool(stage_data.get(4)),  # 第4阶段：分镜脚本生成
                "path": "五阶段分镜脚本",
                "stage_status": stage_status,
                "current_stage": current_stage
            }
        
        return {
            "has_project": True,
            "project_name": self.current_project["project_name"],
            "project_dir": self.current_project["project_dir"],
            "created_time": self.current_project["created_time"],
            "last_modified": self.current_project["last_modified"],
            "files_status": files_status
        }
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """列出所有项目"""
        try:
            projects = []
            
            for item in self.base_output_dir.iterdir():
                if item.is_dir():
                    project_file = item / "project.json"
                    if project_file.exists():
                        try:
                            with open(project_file, 'r', encoding='utf-8') as f:
                                project_config = json.load(f)
                            
                            # 获取项目名称
                            project_name = project_config.get("project_name")
                            clean_name = project_config.get("clean_name", project_name)
                            
                            # 确保created_time字段存在
                            if "created_time" not in project_config:
                                created_time = project_config.get("created_at", datetime.now().isoformat())
                                project_config["created_time"] = created_time
                                # 保存更新后的配置
                                with open(project_file, 'w', encoding='utf-8') as f:
                                    json.dump(project_config, f, ensure_ascii=False, indent=2)
                            
                            projects.append({
                                "name": project_name,
                                "clean_name": clean_name,
                                "path": str(item),
                                "created_time": project_config["created_time"],
                                "last_modified": project_config["last_modified"]
                            })
                        except Exception as e:
                            logger.warning(f"读取项目配置失败: {project_file}, {e}")
            
            # 按最后修改时间排序
            projects.sort(key=lambda x: x["last_modified"], reverse=True)
            
            return projects
            
        except Exception as e:
            logger.error(f"列出项目失败: {e}")
            return []
    
    def delete_project(self, project_path: str) -> bool:
        """删除项目"""
        try:
            project_dir = Path(project_path)
            
            if project_dir.exists() and project_dir.is_dir():
                shutil.rmtree(project_dir)
                logger.info(f"项目已删除: {project_dir}")
                
                # 如果删除的是当前项目，清空当前项目
                if (self.current_project and 
                    self.current_project["project_dir"] == str(project_dir)):
                    self.current_project = None
                
                return True
            else:
                logger.warning(f"项目目录不存在: {project_dir}")
                return False
                
        except Exception as e:
            logger.error(f"删除项目失败: {e}")
            return False
    
    def clear_current_project(self):
        """清空当前项目"""
        self.current_project = None
        logger.info("当前项目已清空")
    
    def get_project_path(self, project_name: str) -> str:
        """获取项目根目录路径
        
        Args:
            project_name: 项目名称
            
        Returns:
            str: 项目根目录路径
        """
        if self.current_project and self.current_project.get('project_name') == project_name:
            return self.current_project.get('project_dir', '')
        
        # 如果不是当前项目，根据项目名称构建路径
        clean_name = self._clean_project_name(project_name)
        return os.path.join(self.base_output_dir, clean_name)
    
    def get_current_project_path(self) -> str:
        """获取当前项目根目录路径

        Returns:
            str: 当前项目根目录路径，如果没有当前项目则返回空字符串
        """
        if self.current_project:
            return self.current_project.get('project_dir', '')
        return ''

    def get_project_root(self) -> str:
        """获取当前项目根目录路径（兼容方法）

        Returns:
            str: 当前项目根目录路径
        """
        return self.get_current_project_path()
    
    def import_project(self, import_path: str, project_name: str = None) -> bool:
        """从指定路径导入项目
        
        Args:
            import_path: 导入文件路径
            project_name: 项目名称（可选，默认使用文件名）
            
        Returns:
            bool: 导入是否成功
        """
        try:
            if not os.path.exists(import_path):
                logger.error(f"导入文件不存在: {import_path}")
                return False
            
            # 读取导入的项目数据
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 提取项目信息
            if "project_info" in import_data:
                project_data = import_data["project_info"]
            else:
                # 兼容旧格式
                project_data = import_data
            
            # 如果没有指定项目名称，使用文件名
            if not project_name:
                project_name = os.path.splitext(os.path.basename(import_path))[0]
                if project_name.endswith("_export"):
                    # 移除导出文件的后缀
                    project_name = project_name.replace("_export", "")
                    # 移除时间戳
                    import re
                    project_name = re.sub(r'_\d{8}_\d{6}$', '', project_name)
            
            # 清理项目名称
            clean_name = self._clean_project_name(project_name)
            
            # 创建新的项目目录
            project_dir = self.base_output_dir / clean_name
            
            # 如果目录已存在，直接使用现有目录，不再创建时间戳后缀
            # 这样可以避免产生重复的时间戳文件夹
            
            # 创建项目目录结构
            self._create_project_structure(project_dir)
            
            # 更新项目数据
            current_time = datetime.now().isoformat()
            if "created_time" not in project_data:
                if "created_at" in project_data:
                    project_data["created_time"] = project_data["created_at"]
                else:
                    project_data["created_time"] = current_time
            project_data.update({
                "name": project_name,
                "clean_name": clean_name,
                "project_dir": str(project_dir),
                "last_modified": current_time,
                "imported_time": current_time,
                "imported_from": import_path
            })
            
            # 设置为当前项目
            self.current_project = project_data
            
            # 保存项目配置
            self.save_project()
            
            logger.info(f"项目导入成功: {project_name} -> {project_dir}")
            return True
            
        except Exception as e:
            logger.error(f"导入项目失败: {e}")
            return False
    
    def get_five_stage_data(self, stage: int = None) -> Dict[str, Any]:
        """获取五阶段分镜数据"""
        try:
            if not self.current_project:
                return {}
            
            five_stage_data = self.current_project.get("five_stage_storyboard", {})
            
            if stage is not None:
                # 返回指定阶段的数据
                return five_stage_data.get("stage_data", {}).get(str(stage), {})
            else:
                # 返回所有五阶段数据
                return five_stage_data
                
        except Exception as e:
            logger.error(f"获取五阶段数据失败: {e}")
            return {}
    
    def get_image_generation_data(self) -> Dict[str, Any]:
        """获取图片生成数据"""
        try:
            if not self.current_project:
                return {}
            
            return self.current_project.get("image_generation", {})
                
        except Exception as e:
            logger.error(f"获取图片生成数据失败: {e}")
            return {}
    
    def get_voice_generation_data(self) -> Dict[str, Any]:
        """获取配音数据"""
        try:
            if not self.current_project:
                return {}
            
            return self.current_project.get("voice_generation", {})
                
        except Exception as e:
            logger.error(f"获取配音数据失败: {e}")
            return {}
    
    def get_subtitle_data(self) -> Dict[str, Any]:
        """获取字幕数据"""
        try:
            if not self.current_project:
                return {}
            
            return self.current_project.get("subtitle_generation", {})
                
        except Exception as e:
            logger.error(f"获取字幕数据失败: {e}")
            return {}
    
    def get_video_composition_data(self) -> Dict[str, Any]:
        """获取视频合成数据"""
        try:
            if not self.current_project:
                return {}
            
            return self.current_project.get("video_composition", {})
                
        except Exception as e:
            logger.error(f"获取视频合成数据失败: {e}")
            return {}
    
    def get_project_stats(self) -> Dict[str, Any]:
        """获取项目统计信息"""
        try:
            if not self.current_project:
                return {}
            
            return self.current_project.get("project_stats", {})
                
        except Exception as e:
            logger.error(f"获取项目统计失败: {e}")
            return {}
    
    def get_all_project_data(self) -> Dict[str, Any]:
        """获取完整的项目数据"""
        try:
            if not self.current_project:
                return {}
            
            return self.current_project.copy()
                
        except Exception as e:
            logger.error(f"获取项目数据失败: {e}")
            return {}
    
    def get_project_data(self) -> Dict[str, Any]:
        """获取项目数据（兼容方法）"""
        return self.get_all_project_data()
    
    def get_shots_data(self) -> List[Dict[str, Any]]:
        """从project.json中获取分镜数据"""
        try:
            if not self.current_project:
                return []
            
            # 从五阶段数据中获取分镜信息
            five_stage_data = self.current_project.get("five_stage_storyboard", {})
            stage_data = five_stage_data.get("stage_data", {})
            
            # 合并所有阶段的分镜数据
            all_shots = []
            for stage_num in ["1", "2", "3", "4", "5"]:
                stage_shots = stage_data.get(stage_num, {}).get("shots", [])
                if isinstance(stage_shots, list):
                    all_shots.extend(stage_shots)
            
            return all_shots
                
        except Exception as e:
            logger.error(f"获取分镜数据失败: {e}")
            return []

    def update_five_stage_data(self, stage: int, stage_data: Dict[str, Any]) -> bool:
        """更新五阶段分镜数据"""
        try:
            if not self.current_project:
                raise ValueError("没有当前项目")
            
            # 获取用户设置的默认值
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            default_style = config_manager.get_setting("default_style", "电影风格")
            
            # 确保五阶段数据结构存在
            if "five_stage_storyboard" not in self.current_project:
                self.current_project["five_stage_storyboard"] = {
                    "stage_data": {"1": {}, "2": {}, "3": {}, "4": {}, "5": {}},
                    "current_stage": 1,
                    "selected_characters": [],
                    "selected_scenes": [],
                    "article_text": "",
                    "selected_style": default_style,  # 使用用户设置的默认风格
                    "selected_model": ""
                }
            
            # 更新指定阶段的数据
            self.current_project["five_stage_storyboard"]["stage_data"][str(stage)] = stage_data
            
            # 更新最后活动时间
            self.current_project["project_stats"]["last_activity"] = datetime.now().isoformat()
            
            # 保存项目
            return self.save_project()
            
        except Exception as e:
            logger.error(f"更新五阶段数据失败: {e}")
            return False
    
    def update_image_generation_data(self, data: Dict[str, Any]) -> bool:
        """更新图片生成数据"""
        try:
            if not self.current_project:
                raise ValueError("没有当前项目")
            
            # 获取用户设置的默认值
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            default_quality = config_manager.get_setting("default_image_quality", "high")
            default_resolution = config_manager.get_setting("default_image_resolution", "1024x1024")
            
            # 确保图片生成数据结构存在
            if "image_generation" not in self.current_project:
                self.current_project["image_generation"] = {
                    "provider": None,
                    "settings": {"style": "realistic", "quality": default_quality, "resolution": default_resolution, "batch_size": 1},
                    "generated_images": [],
                    "progress": {"total_shots": 0, "completed_shots": 0, "failed_shots": 0, "status": "pending"}
                }
            
            # 更新数据
            for key, value in data.items():
                if key in self.current_project["image_generation"]:
                    if isinstance(self.current_project["image_generation"][key], dict) and isinstance(value, dict):
                        self.current_project["image_generation"][key].update(value)
                    else:
                        self.current_project["image_generation"][key] = value
            
            # 更新最后活动时间
            self.current_project["project_stats"]["last_activity"] = datetime.now().isoformat()
            
            return self.save_project()
            
        except Exception as e:
            logger.error(f"更新图片生成数据失败: {e}")
            return False
    
    def update_voice_generation_data(self, data: Dict[str, Any]) -> bool:
        """更新配音数据"""
        try:
            if not self.current_project:
                raise ValueError("没有当前项目")
            
            # 获取用户设置的默认值
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            default_language = config_manager.get_setting("default_language", "zh-CN")
            
            # 确保配音数据结构存在
            if "voice_generation" not in self.current_project:
                self.current_project["voice_generation"] = {
                    "provider": None,
                    "settings": {"voice_name": "", "language": default_language, "speed": 1.0, "pitch": 0, "volume": 1.0},
                    "generated_audio": [],
                    "narration_text": "",
                    "progress": {"total_segments": 0, "completed_segments": 0, "failed_segments": 0, "status": "pending"}
                }
            
            # 更新数据
            for key, value in data.items():
                if key in self.current_project["voice_generation"]:
                    if isinstance(self.current_project["voice_generation"][key], dict) and isinstance(value, dict):
                        self.current_project["voice_generation"][key].update(value)
                    else:
                        self.current_project["voice_generation"][key] = value
            
            # 更新最后活动时间
            self.current_project["project_stats"]["last_activity"] = datetime.now().isoformat()
            
            return self.save_project()
            
        except Exception as e:
            logger.error(f"更新配音数据失败: {e}")
            return False
    
    def update_subtitle_data(self, data: Dict[str, Any]) -> bool:
        """更新字幕数据"""
        try:
            if not self.current_project:
                raise ValueError("没有当前项目")
            
            # 获取用户设置的默认值
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            default_format = config_manager.get_setting("default_subtitle_format", "srt")
            default_font = config_manager.get_setting("default_font_family", "Arial")
            
            # 确保字幕数据结构存在
            if "subtitle_generation" not in self.current_project:
                self.current_project["subtitle_generation"] = {
                    "format": default_format,
                    "settings": {"font_family": default_font, "font_size": 24, "font_color": "#FFFFFF", "background_color": "#000000", "position": "bottom", "timing_offset": 0},
                    "subtitle_files": [],
                    "subtitle_data": [],
                    "progress": {"status": "pending", "auto_generated": False, "manually_edited": False}
                }
            
            # 更新数据
            for key, value in data.items():
                if key in self.current_project["subtitle_generation"]:
                    if isinstance(self.current_project["subtitle_generation"][key], dict) and isinstance(value, dict):
                        self.current_project["subtitle_generation"][key].update(value)
                    else:
                        self.current_project["subtitle_generation"][key] = value
            
            # 更新最后活动时间
            self.current_project["project_stats"]["last_activity"] = datetime.now().isoformat()
            
            return self.save_project()
            
        except Exception as e:
            logger.error(f"更新字幕数据失败: {e}")
            return False

    def update_video_generation_data(self, data: Dict[str, Any]) -> bool:
        """更新视频生成数据"""
        try:
            if not self.current_project:
                raise ValueError("没有当前项目")

            # 确保video_generation字段存在
            if "video_generation" not in self.current_project:
                self.current_project["video_generation"] = {
                    "videos": [],
                    "settings": {
                        "engine": "cogvideox_flash",
                        "duration": 5,
                        "fps": 30,
                        "motion_intensity": 0.5,
                        "quality": "高质量"
                    },
                    "progress": {
                        "total_videos": 0,
                        "completed_videos": 0,
                        "failed_videos": 0,
                        "status": "pending"
                    }
                }

            # 更新数据
            for key, value in data.items():
                if key in self.current_project["video_generation"]:
                    if isinstance(self.current_project["video_generation"][key], dict) and isinstance(value, dict):
                        self.current_project["video_generation"][key].update(value)
                    else:
                        self.current_project["video_generation"][key] = value

            # 更新最后活动时间
            self.current_project["project_stats"]["last_activity"] = datetime.now().isoformat()

            return self.save_project()

        except Exception as e:
            logger.error(f"更新视频生成数据失败: {e}")
            return False

    def add_video_record(self, video_data: Dict[str, Any]) -> bool:
        """添加视频生成记录"""
        try:
            if not self.current_project:
                raise ValueError("没有当前项目")

            # 确保video_generation字段存在
            if "video_generation" not in self.current_project:
                self.update_video_generation_data({})

            # 添加视频记录
            self.current_project["video_generation"]["videos"].append(video_data)

            # 更新统计
            total_videos = len(self.current_project["video_generation"]["videos"])
            completed_videos = len([v for v in self.current_project["video_generation"]["videos"] if v.get("status") == "已生成"])
            failed_videos = len([v for v in self.current_project["video_generation"]["videos"] if v.get("status") == "生成失败"])

            self.current_project["video_generation"]["progress"].update({
                "total_videos": total_videos,
                "completed_videos": completed_videos,
                "failed_videos": failed_videos
            })

            # 更新最后活动时间
            self.current_project["project_stats"]["last_activity"] = datetime.now().isoformat()

            return self.save_project()

        except Exception as e:
            logger.error(f"添加视频记录失败: {e}")
            return False

    def update_video_composition_data(self, data: Dict[str, Any]) -> bool:
        """更新视频合成数据"""
        try:
            if not self.current_project:
                raise ValueError("没有当前项目")
            
            # 获取用户设置的默认值
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            default_resolution = config_manager.get_setting("default_video_resolution", "1920x1080")
            default_format = config_manager.get_setting("default_video_format", "mp4")
            default_quality = config_manager.get_setting("default_image_quality", "high")
            
            # 确保视频合成数据结构存在
            if "video_composition" not in self.current_project:
                self.current_project["video_composition"] = {
                    "settings": {"resolution": default_resolution, "fps": 30, "format": default_format, "quality": default_quality, "transition_type": "fade", "transition_duration": 0.5},
                    "timeline": {"total_duration": 0, "segments": []},
                    "output_files": {"preview_video": None, "final_video": None, "audio_track": None},
                    "progress": {"status": "pending", "current_step": "", "completion_percentage": 0}
                }
            
            # 更新数据
            for key, value in data.items():
                if key in self.current_project["video_composition"]:
                    if isinstance(self.current_project["video_composition"][key], dict) and isinstance(value, dict):
                        self.current_project["video_composition"][key].update(value)
                    else:
                        self.current_project["video_composition"][key] = value
            
            # 更新最后活动时间
            self.current_project["project_stats"]["last_activity"] = datetime.now().isoformat()
            
            return self.save_project()
            
        except Exception as e:
            logger.error(f"更新视频合成数据失败: {e}")
            return False

    def update_project_stats(self, stats: Dict[str, Any]) -> bool:
        """更新项目统计信息"""
        try:
            if not self.current_project:
                raise ValueError("没有当前项目")
            
            # 确保项目统计数据结构存在
            if "project_stats" not in self.current_project:
                self.current_project["project_stats"] = {
                    "total_shots": 0,
                    "total_characters": 0,
                    "total_scenes": 0,
                    "estimated_duration": 0,
                    "completion_percentage": 0,
                    "last_activity": datetime.now().isoformat()
                }
            
            # 更新统计数据
            for key, value in stats.items():
                if key in self.current_project["project_stats"]:
                    self.current_project["project_stats"][key] = value
            
            # 更新最后活动时间
            self.current_project["project_stats"]["last_activity"] = datetime.now().isoformat()
            
            return self.save_project()
            
        except Exception as e:
            logger.error(f"更新项目统计失败: {e}")
            return False