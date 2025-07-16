import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from src.utils.logger import logger
from src.utils.character_scene_manager import CharacterSceneManager

class StoryboardProjectManager:
    """分镜项目管理器 - 负责分镜数据管理和图片处理"""
    
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        # 将项目保存到output文件夹下，而不是config/projects
        # 获取项目根目录（AI_Video_Generator）
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.projects_dir = os.path.join(project_root, 'output')
        os.makedirs(self.projects_dir, exist_ok=True)
        # 添加current_project属性
        self.current_project = None
        self.current_project_name = None
        logger.info(f"项目管理器初始化，项目保存目录: {self.projects_dir}")
    
    def create_new_project(self, project_name: str, project_description: str = "") -> Dict[str, Any]:
        """创建新项目
        
        Args:
            project_name: 项目名称
            project_description: 项目描述
            
        Returns:
            Dict[str, Any]: 项目配置数据
        """
        try:
            # 清理项目名称
            clean_name = self._clean_project_name(project_name)
            
            # 创建项目文件夹结构
            project_root = self.create_project_structure(clean_name)
            
            # 创建项目配置
            current_time = datetime.now().isoformat()
            project_config = {
                'project_name': project_name,
                'description': project_description,
                'created_time': current_time,
                'last_modified': current_time,
                'project_root': project_root,
                'project_dir': project_root,  # 添加project_dir字段，与project_root相同
                'progress_status': {},
                'drawing_settings': {'generated_images': []},
                'voice_settings': {},
                'voice_generation': {
                    'provider': 'edge_tts',
                    'settings': {
                        'voice': 'zh-CN-YunxiNeural',
                        'speed': 1.0,
                        'pitch': 0,
                        'volume': 1.0,
                        'language': 'zh-CN'
                    },
                    'generated_audio': [],
                    'voice_segments': [],
                    'progress': {
                        'total_segments': 0,
                        'completed_segments': 0,
                        'status': 'pending'
                    }
                },
                'workflow_settings': {},
                'five_stage_storyboard': {},
                'files': {},
                'original_text': '',
                'rewritten_text': '',
                'shots_data': []
            }
            
            # 保存项目配置文件
            project_config_file = os.path.join(project_root, 'project.json')
            with open(project_config_file, 'w', encoding='utf-8') as f:
                json.dump(project_config, f, ensure_ascii=False, indent=2)
            
            # 设置当前项目
            self.current_project = project_config
            self.current_project_name = project_name
            
            # 初始化角色场景管理器
            self._character_scene_manager = CharacterSceneManager(project_root)
            
            logger.info(f"新项目创建成功: {project_name} -> {project_root}")
            return project_config
            
        except Exception as e:
            logger.error(f"创建项目失败: {e}")
            raise e
        
    def create_project_structure(self, project_name: str) -> str:
        """创建项目文件夹结构
        
        Args:
            project_name: 项目名称
            
        Returns:
            str: 项目根目录路径
        """
        project_root = os.path.join(self.projects_dir, project_name)
        
        # 创建项目根目录
        os.makedirs(project_root, exist_ok=True)
        
        # 创建子目录
        subdirs = [
            'texts',      # 文本文件（原始文本、改写文本）
            'shots',      # 分镜表格文件
            'images',     # 生成的图片
            'audio',      # 配音文件
            'subtitles',  # 字幕文件
            'videos',     # 视频文件
            'temp'        # 临时文件
        ]
        
        for subdir in subdirs:
            os.makedirs(os.path.join(project_root, subdir), exist_ok=True)
        
        # 创建图片子目录
        image_subdirs = [
            'images/comfyui',      # ComfyUI生成的图片
            'images/pollinations'  # Pollinations生成的图片
        ]
        
        for subdir in image_subdirs:
            os.makedirs(os.path.join(project_root, subdir), exist_ok=True)
        
        logger.info(f"项目文件夹结构已创建: {project_root}")
        return project_root
        
    def get_project_path(self, project_name: str) -> str:
        """获取项目根目录路径"""
        return os.path.join(self.projects_dir, project_name)
        
    def get_project_config_path(self, project_name: str) -> str:
        """获取项目配置文件路径"""
        return os.path.join(self.get_project_path(project_name), 'project.json')
        
    def save_project(self, project_name: str, project_data: Dict[str, Any]) -> bool:
        """保存项目状态 - 统一保存所有数据到project.json

        Args:
            project_name: 项目名称
            project_data: 项目数据，包含以下字段：
                - original_text: 原始文本
                - rewritten_text: 改写后文本
                - shots_data: 分镜数据
                - drawing_settings: 绘图设置
                - voice_settings: 配音设置
                - workflow_settings: 工作流设置
                - progress_status: 进度状态
                - created_time: 创建时间
                - last_modified: 最后修改时间
                - five_stage_storyboard: 五阶段分镜数据
                - image_generation: 图像生成数据
                - image_generation_settings: 图像生成设置
                - shot_image_mappings: 镜头图片关联信息

        Returns:
            bool: 保存是否成功
        """
        try:
            # 确保项目文件夹结构存在
            project_root = self.create_project_structure(project_name)

            # 添加时间戳和项目路径信息
            current_time = datetime.now().isoformat()
            project_data['last_modified'] = current_time
            if 'created_time' not in project_data:
                project_data['created_time'] = current_time

            # 确保项目路径信息正确
            project_data['project_root'] = project_root
            project_data['project_dir'] = project_root

            # 统一保存所有数据到project.json文件
            config_file = os.path.join(project_root, 'project.json')

            # 创建备份（如果原文件存在）
            if os.path.exists(config_file):
                backup_file = config_file + '.backup'
                try:
                    import shutil
                    shutil.copy2(config_file, backup_file)
                    logger.info(f"已创建项目配置备份: {backup_file}")
                except Exception as backup_error:
                    logger.warning(f"创建备份失败: {backup_error}")

            # 保存完整的项目数据到project.json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)

            logger.info(f"项目数据已统一保存到: {config_file}")
            return True

            
        except Exception as e:
            logger.error(f"保存项目失败: {e}")
            return False
    
    def load_project(self, project_name_or_path: str) -> Optional[Dict[str, Any]]:
        """加载项目数据 - 统一从project.json加载所有数据

        Args:
            project_name_or_path: 项目名称或项目路径

        Returns:
            Optional[Dict[str, Any]]: 项目数据，如果加载失败返回None
        """
        try:
            # 判断传入的是项目名称还是项目路径
            if os.path.isdir(project_name_or_path):
                # 传入的是项目路径
                project_root = project_name_or_path
                project_name = os.path.basename(project_root)
                project_config_file = os.path.join(project_root, 'project.json')
            else:
                # 传入的是项目名称
                project_name = project_name_or_path
                project_root = self.get_project_path(project_name)
                project_config_file = self.get_project_config_path(project_name)

            if not os.path.exists(project_config_file):
                logger.warning(f"项目配置文件不存在: {project_config_file}")
                return None

            # 统一从project.json加载所有项目数据
            with open(project_config_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 确保项目路径信息正确
            project_data['project_root'] = project_root
            project_data['project_dir'] = project_root

            # 确保必要的字段存在
            if 'original_text' not in project_data:
                project_data['original_text'] = ''
            if 'rewritten_text' not in project_data:
                project_data['rewritten_text'] = ''
            if 'shots_data' not in project_data:
                project_data['shots_data'] = []
            if 'five_stage_storyboard' not in project_data:
                project_data['five_stage_storyboard'] = {}
            if 'image_generation' not in project_data:
                project_data['image_generation'] = {}
            if 'image_generation_settings' not in project_data:
                project_data['image_generation_settings'] = {}
            if 'shot_image_mappings' not in project_data:
                project_data['shot_image_mappings'] = {}
            if 'drawing_settings' not in project_data:
                project_data['drawing_settings'] = {}
            if 'voice_settings' not in project_data:
                project_data['voice_settings'] = {}
            if 'workflow_settings' not in project_data:
                project_data['workflow_settings'] = {}
            if 'progress_status' not in project_data:
                project_data['progress_status'] = {}
            if 'files' not in project_data:
                project_data['files'] = {}

            # 初始化角色场景管理器（暂时不传入service_manager，因为这里没有可用的实例）
            character_scene_manager = CharacterSceneManager(project_root)

            # 将CharacterSceneManager实例存储为类属性，而不是项目数据的一部分
            self._character_scene_manager = character_scene_manager
            
            # 设置当前项目
            self.current_project = project_data
            self.current_project_name = project_name

            # 🔧 修复：只在项目首次加载或切换时记录日志，避免频繁记录
            if not hasattr(self, '_last_loaded_project') or self._last_loaded_project != project_name:
                logger.info(f"项目已加载: {project_name} <- {project_root}")
                self._last_loaded_project = project_name

            return project_data
            
        except Exception as e:
            logger.error(f"加载项目失败: {e}")
            return None
    
    def get_character_scene_manager(self, service_manager=None):
        """获取角色场景管理器实例
        
        Args:
            service_manager: 服务管理器实例（可选）
            
        Returns:
            CharacterSceneManager: 角色场景管理器实例，如果没有当前项目则返回None
        """
        if not self.current_project:
            return None
            
        # 如果已经有实例且项目路径匹配，直接返回
        if (hasattr(self, '_character_scene_manager') and 
            self._character_scene_manager and 
            self._character_scene_manager.project_root == self.current_project.get('project_root')):
            # 如果提供了新的service_manager，更新它
            if service_manager:
                self._character_scene_manager.service_manager = service_manager
            return self._character_scene_manager
        
        # 创建新的实例
        from .character_scene_manager import CharacterSceneManager
        project_root = self.current_project.get('project_root')
        if project_root:
            self._character_scene_manager = CharacterSceneManager(project_root, service_manager)
            return self._character_scene_manager
        
        return None
    
    def list_projects(self) -> List[Dict[str, str]]:
        """列出所有项目
        
        Returns:
            List[Dict[str, str]]: 项目列表，每个项目包含name, created_time, last_modified
        """
        projects = []
        try:
            if not os.path.exists(self.projects_dir):
                return projects
            
            for item in os.listdir(self.projects_dir):
                item_path = os.path.join(self.projects_dir, item)
                # 检查是否为目录且包含project.json配置文件
                if os.path.isdir(item_path):
                    config_file = os.path.join(item_path, 'project.json')
                    if os.path.exists(config_file):
                        try:
                            with open(config_file, 'r', encoding='utf-8') as f:
                                project_data = json.load(f)
                            
                            projects.append({
                                'name': item,
                                'path': item_path,
                                'created_time': project_data.get('created_time', '未知'),
                                'last_modified': project_data.get('last_modified', '未知'),
                                'progress_status': project_data.get('progress_status', {})
                            })
                        except Exception as e:
                            logger.warning(f"读取项目文件失败: {config_file}, 错误: {e}")
                            continue
            
            # 按最后修改时间排序
            projects.sort(key=lambda x: x['last_modified'], reverse=True)
            
        except Exception as e:
            logger.error(f"列出项目失败: {e}")
        
        return projects
    
    def get_project_list(self) -> List[str]:
        """获取所有项目名称列表
        
        Returns:
            List[str]: 项目名称列表
        """
        try:
            projects = []
            for item in os.listdir(self.projects_dir):
                item_path = os.path.join(self.projects_dir, item)
                # 检查是否为目录且包含project.json配置文件
                if os.path.isdir(item_path):
                    config_file = os.path.join(item_path, 'project.json')
                    if os.path.exists(config_file):
                        projects.append(item)
            
            return sorted(projects)
            
        except Exception as e:
            logger.error(f"获取项目列表失败: {e}")
            return []
    
    def delete_project(self, project_name: str) -> bool:
        """删除项目及其所有相关文件
        
        Args:
            project_name: 项目名称
        
        Returns:
            bool: 删除是否成功
        """
        try:
            project_root = self.get_project_path(project_name)
            
            if os.path.exists(project_root):
                # 删除整个项目文件夹
                shutil.rmtree(project_root)
                logger.info(f"项目及所有相关文件已删除: {project_name} -> {project_root}")
                return True
            else:
                logger.warning(f"项目文件夹不存在: {project_root}")
                return False
                
        except Exception as e:
            logger.error(f"删除项目失败: {e}")
            return False
    
    def export_project(self, project_name: str, export_path: str) -> bool:
        """导出项目到指定路径
        
        Args:
            project_name: 项目名称
            export_path: 导出路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            project_data = self.load_project(project_name)
            if not project_data:
                return False
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"项目已导出: {project_name} -> {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出项目失败: {e}")
            return False
    
    def import_project(self, import_path: str, project_name: str = None) -> bool:
        """从指定路径导入项目
        
        Args:
            import_path: 导入路径
            project_name: 项目名称，如果为None则使用文件名
            
        Returns:
            bool: 导入是否成功
        """
        try:
            if not os.path.exists(import_path):
                logger.error(f"导入文件不存在: {import_path}")
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            if not project_name:
                project_name = os.path.splitext(os.path.basename(import_path))[0]
            
            return self.save_project(project_name, project_data)
            
        except Exception as e:
            logger.error(f"导入项目失败: {e}")
            return False
    
    def get_project_status(self, project_name: str) -> Dict[str, Any]:
        """获取项目状态信息
        
        Args:
            project_name: 项目名称
            
        Returns:
            Dict[str, Any]: 项目状态信息
        """
        project_data = self.load_project(project_name)
        if not project_data:
            return {
                "has_project": False,
                "project_name": None,
                "project_dir": None,
                "files_status": {}
            }
        
        progress_status = project_data.get('progress_status', {})
        
        # 构建文件状态信息
        files_status = {
            "original_text": {
                "exists": bool(project_data.get('original_text')),
                "path": "原始文本"
            },
            "rewritten_text": {
                "exists": bool(project_data.get('rewritten_text')),
                "path": "改写文本"
            },
            "storyboard": {
                "exists": len(project_data.get('shots_data', [])) > 0,
                "path": "分镜脚本"
            }
        }
        
        return {
            "has_project": True,
            "project_name": project_name,
            "project_dir": project_data.get('project_dir', ''),
            "created_time": project_data.get('created_time', ''),
            "last_modified": project_data.get('last_modified', ''),
            "files_status": files_status,
            # 保持向后兼容
            'name': project_name,
            'has_original_text': bool(project_data.get('original_text')),
            'has_rewritten_text': bool(project_data.get('rewritten_text')),
            'shots_count': len(project_data.get('shots_data', [])),
            'progress_status': progress_status,
            'completion_percentage': self._calculate_completion_percentage(progress_status)
        }
    
    def add_image_to_project(self, project_name: str, image_path: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """将图片添加到项目中
        
        Args:
            project_name: 项目名称
            image_path: 图片路径
            metadata: 图片元数据
            
        Returns:
            Optional[str]: 项目中的图片路径，如果保存失败返回None
        """
        try:
            if not project_name or not image_path:
                logger.warning("项目名称或图片路径为空")
                return None
                
            if not os.path.exists(image_path):
                logger.warning(f"图片文件不存在: {image_path}")
                return None
            
            # 获取项目路径
            project_root = self.get_project_path(project_name)
            
            # 根据图片来源确定保存目录
            if 'comfyui' in image_path.lower() or 'ComfyUI' in image_path:
                project_images_dir = os.path.join(project_root, 'images', 'comfyui')
            elif 'pollinations' in image_path.lower():
                project_images_dir = os.path.join(project_root, 'images', 'pollinations')
            else:
                # 根据metadata中的source字段判断
                source = metadata.get('source', '').lower() if metadata else ''
                if 'pollinations' in source:
                    project_images_dir = os.path.join(project_root, 'images', 'pollinations')
                else:
                    project_images_dir = os.path.join(project_root, 'images', 'comfyui')
            
            # 确保目标目录存在
            os.makedirs(project_images_dir, exist_ok=True)
            
            # 检查图片是否已经在项目目录中
            if os.path.commonpath([image_path, project_images_dir]) == project_images_dir:
                # 图片已经在项目目录中，直接返回路径
                logger.info(f"图片已在项目目录中: {image_path}")
                return image_path
            
            # 生成新的文件名（避免重复）
            # 使用简洁的文件名，不包含时间戳
            original_filename = os.path.basename(image_path)
            name, ext = os.path.splitext(original_filename)
            new_filename = f"{name}{ext}"
            
            # 目标路径
            target_path = os.path.join(project_images_dir, new_filename)
            
            # 复制文件
            shutil.copy2(image_path, target_path)
            
            logger.info(f"图片已添加到项目: {image_path} -> {target_path}")
            return target_path
            
        except Exception as e:
            logger.error(f"添加图片到项目失败: {e}")
            return None
    
    def save_project(self):
        """保存当前项目配置"""
        if not self.current_project:
            logger.warning("没有当前项目可保存")
            return False
        
        try:
            project_file = Path(self.current_project["project_dir"]) / "project.json"
            
            # 清理和验证项目数据
            self._clean_project_data(self.current_project)
            
            # 更新最后修改时间
            self.current_project["last_modified"] = datetime.now().isoformat()
            
            # 创建备份（如果原文件存在）
            if project_file.exists():
                backup_file = project_file.with_suffix('.json.backup')
                try:
                    import shutil
                    shutil.copy2(project_file, backup_file)
                    logger.info(f"已创建项目配置备份: {backup_file}")
                except Exception as backup_error:
                    logger.warning(f"创建备份失败: {backup_error}")
            
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_project, f, ensure_ascii=False, indent=2)
            
            logger.info(f"项目配置已保存: {project_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存项目配置失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False

    def save_project_data(self, project_data: Dict[str, Any]) -> bool:
        """保存项目数据到project.json文件

        Args:
            project_data: 要保存的项目数据

        Returns:
            bool: 保存是否成功
        """
        try:
            if not self.current_project:
                logger.warning("没有当前项目可保存")
                return False

            # 更新当前项目数据
            self.current_project.update(project_data)

            # 使用现有的保存方法
            return self.save_project()

        except Exception as e:
            logger.error(f"保存项目数据失败: {e}")
            return False

    def _calculate_completion_percentage(self, progress_status: Dict[str, Any]) -> int:
        """计算项目完成百分比"""
        total_steps = 5  # 文本改写、分镜生成、绘图、配音、视频合成
        completed_steps = 0
        
        if progress_status.get('text_rewritten', False):
            completed_steps += 1
        if progress_status.get('shots_generated', False):
            completed_steps += 1
        if progress_status.get('images_generated', False):
            completed_steps += 1
        if progress_status.get('voices_generated', False):
            completed_steps += 1
        if progress_status.get('video_composed', False):
            completed_steps += 1
        
        return int((completed_steps / total_steps) * 100)
    
    def _clean_project_data(self, project_data):
        """清理项目数据，移除空的或重复的条目"""
        try:
            # 清理五阶段分镜数据
            if 'five_stage_storyboard' in project_data:
                five_stage_data = project_data['five_stage_storyboard']
                
                # 验证五阶段数据结构
                if not isinstance(five_stage_data, dict):
                    logger.warning("五阶段数据格式错误，重新初始化")
                    project_data['five_stage_storyboard'] = {
                        'stage_data': {"1": {}, "2": {}, "3": {}, "4": {}, "5": {}},
                        'current_stage': 1,
                        'selected_characters': [],
                        'selected_scenes': [],
                        'article_text': '',
                        'selected_style': '电影风格',
                        'selected_model': ''
                    }
                    return
                
                # 确保必要的字段存在
                required_fields = {
                    'stage_data': {"1": {}, "2": {}, "3": {}, "4": {}, "5": {}},
                    'current_stage': 1,
                    'selected_characters': [],
                    'selected_scenes': [],
                    'article_text': '',
                    'selected_style': '电影风格',
                    'selected_model': ''
                }
                
                for field, default_value in required_fields.items():
                    if field not in five_stage_data:
                        five_stage_data[field] = default_value
                        logger.info(f"添加缺失的五阶段字段: {field}")
                
                # 清理空的阶段数据
                if 'stage_data' in five_stage_data:
                    stage_data = five_stage_data['stage_data']
                    if not isinstance(stage_data, dict):
                        five_stage_data['stage_data'] = {"1": {}, "2": {}, "3": {}, "4": {}, "5": {}}
                    else:
                        # 确保所有阶段都存在
                        for stage_num in range(1, 6):
                            stage_str = str(stage_num)
                            if stage_str not in stage_data:
                                stage_data[stage_str] = {}
                        
                        # 清理无效的阶段数据
                        for stage_num in list(stage_data.keys()):
                            if not isinstance(stage_data[stage_num], dict):
                                stage_data[stage_num] = {}
                
                # 验证当前阶段
                current_stage = five_stage_data.get('current_stage', 1)
                if not isinstance(current_stage, int) or current_stage < 1 or current_stage > 5:
                    five_stage_data['current_stage'] = 1
                    logger.warning("当前阶段值无效，重置为1")
                
                # 清理重复的世界观数据
                if 'stage_data' in five_stage_data and 1 in five_stage_data['stage_data']:
                    world_bible = five_stage_data['stage_data'][1].get('world_bible', '')
                    if world_bible and isinstance(world_bible, str):
                        # 如果有重复的世界观数据，保留最新的
                        project_data['world_bible'] = world_bible
                
                # 清理重复的分镜结果
                if 'stage_data' in five_stage_data and 4 in five_stage_data['stage_data']:
                    storyboard_results = five_stage_data['stage_data'][4].get('storyboard_results', [])
                    if storyboard_results and isinstance(storyboard_results, list):
                        project_data['storyboard_results'] = storyboard_results
            
            # 验证其他项目数据
            if 'files' not in project_data:
                project_data['files'] = {}
            
            # 处理项目名称字段的重复键问题
            if 'name' in project_data and 'project_name' in project_data:
                # 如果同时存在name和project_name，删除name字段，保留project_name
                del project_data['name']
                logger.info("删除重复的name字段，保留project_name字段")
            elif 'name' in project_data and 'project_name' not in project_data:
                # 如果只有name字段，将其重命名为project_name
                project_data['project_name'] = project_data['name']
                del project_data['name']
                logger.info("将name字段重命名为project_name字段")
            elif 'project_name' not in project_data:
                # 如果两个字段都不存在，创建project_name字段
                project_data['project_name'] = 'Unnamed Project'
                logger.warning("项目名称缺失，使用默认名称")
            
            logger.info("项目数据清理和验证完成")
            
        except Exception as e:
            logger.error(f"清理项目数据时出错: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
    
    def get_project_data(self) -> Dict[str, Any]:
        """获取当前项目数据（兼容方法）"""
        try:
            if not self.current_project_name:
                return {}
            return self.load_project(self.current_project_name)
        except Exception as e:
            logger.error(f"获取项目数据失败: {e}")
            return {}

    
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
            str: 当前项目根目录路径，如果没有当前项目则返回空字符串
        """
        return self.get_current_project_path()
    
    def get_project_file_path(self, file_type: str, filename: str = None):
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
            if self.current_project:
                self.current_project["files"][text_type] = str(file_path)
                self.save_project()
            
            logger.info(f"文本内容已保存: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"保存文本内容失败: {e}")
            raise

    def add_video_record(self, video_data: Dict[str, Any]) -> bool:
        """添加视频生成记录"""
        try:
            if not self.current_project:
                logger.warning("没有当前项目，无法添加视频记录")
                return False

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

            # 更新最后修改时间
            self.current_project["last_modified"] = datetime.now().isoformat()

            # 保存项目
            self.save_project()

            return True

        except Exception as e:
            logger.error(f"添加视频记录失败: {e}")
            return False

    def update_video_generation_data(self, data: Dict[str, Any]) -> bool:
        """更新视频生成数据"""
        try:
            if not self.current_project:
                logger.warning("没有当前项目，无法更新视频生成数据")
                return False

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

            # 更新最后修改时间
            self.current_project["last_modified"] = datetime.now().isoformat()

            # 保存项目
            self.save_project()

            return True

        except Exception as e:
            logger.error(f"更新视频生成数据失败: {e}")
            return False