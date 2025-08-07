#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置持久化管理器
负责保存和加载用户界面设置
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from src.utils.logger import logger


class SettingsPersistence:
    """设置持久化管理器"""
    
    def __init__(self, project_manager=None):
        self.project_manager = project_manager
        self.settings_cache = {}
        
        # 全局设置文件路径
        self.global_settings_dir = Path("config/user_settings")
        self.global_settings_dir.mkdir(parents=True, exist_ok=True)
        self.global_settings_file = self.global_settings_dir / "ui_settings.json"
        
    def save_ui_settings(self, component_name: str, settings: Dict[str, Any], 
                        save_to_project: bool = True, save_globally: bool = True) -> bool:
        """
        保存UI设置
        
        Args:
            component_name: 组件名称（如 'image_generation', 'voice_generation'）
            settings: 设置数据
            save_to_project: 是否保存到当前项目
            save_globally: 是否保存到全局设置
            
        Returns:
            bool: 保存是否成功
        """
        success = True
        
        try:
            # 保存到项目
            if save_to_project and self.project_manager and self.project_manager.current_project:
                success &= self._save_to_project(component_name, settings)
            
            # 保存到全局设置
            if save_globally:
                success &= self._save_to_global(component_name, settings)
                
            # 更新缓存
            self.settings_cache[component_name] = settings.copy()
            
            logger.info(f"设置已保存: {component_name}")
            return success
            
        except Exception as e:
            logger.error(f"保存设置失败 {component_name}: {e}")
            return False
    
    def load_ui_settings(self, component_name: str, 
                        prefer_project: bool = True) -> Optional[Dict[str, Any]]:
        """
        加载UI设置
        
        Args:
            component_name: 组件名称
            prefer_project: 是否优先使用项目设置
            
        Returns:
            Optional[Dict[str, Any]]: 设置数据，如果没有则返回None
        """
        try:
            # 检查缓存
            if component_name in self.settings_cache:
                return self.settings_cache[component_name].copy()
            
            settings = None
            
            # 优先从项目加载
            if prefer_project and self.project_manager and self.project_manager.current_project:
                settings = self._load_from_project(component_name)
            
            # 如果项目中没有，从全局设置加载
            if not settings:
                settings = self._load_from_global(component_name)
            
            # 更新缓存
            if settings:
                self.settings_cache[component_name] = settings.copy()
                logger.info(f"设置已加载: {component_name}")
            
            return settings
            
        except Exception as e:
            logger.error(f"加载设置失败 {component_name}: {e}")
            return None
    
    def _save_to_project(self, component_name: str, settings: Dict[str, Any]) -> bool:
        """保存设置到项目"""
        try:
            project_data = self.project_manager.current_project
            
            # 确保设置结构存在
            if 'data' not in project_data:
                project_data['data'] = {}
            if 'ui_settings' not in project_data['data']:
                project_data['data']['ui_settings'] = {}
            
            project_data['data']['ui_settings'][component_name] = settings
            
            # 保存项目（ProjectManager的save_project方法不需要参数）
            return self.project_manager.save_project()
            
        except Exception as e:
            logger.error(f"保存设置到项目失败: {e}")
            return False
    
    def _load_from_project(self, component_name: str) -> Optional[Dict[str, Any]]:
        """从项目加载设置"""
        try:
            project_data = self.project_manager.current_project
            
            # 尝试从新的数据结构加载
            data = project_data.get('data', {})
            ui_settings = data.get('ui_settings', {})
            settings = ui_settings.get(component_name)
            
            # 如果新结构中没有，尝试从旧结构加载（兼容性）
            if not settings:
                # 对于图像生成设置，检查旧的image_generation_settings字段
                if component_name == 'image_generation':
                    old_settings = project_data.get('image_generation_settings', {})
                    if old_settings:
                        # 迁移旧设置到新结构
                        migrated_settings = self._migrate_old_image_settings(old_settings)
                        if migrated_settings:
                            # 保存迁移后的设置
                            self._save_to_project(component_name, migrated_settings)
                            return migrated_settings
            
            return settings
            
        except Exception as e:
            logger.error(f"从项目加载设置失败: {e}")
            return None
    
    def _save_to_global(self, component_name: str, settings: Dict[str, Any]) -> bool:
        """保存设置到全局文件"""
        try:
            # 加载现有全局设置
            global_settings = {}
            if self.global_settings_file.exists():
                with open(self.global_settings_file, 'r', encoding='utf-8') as f:
                    global_settings = json.load(f)
            
            # 更新设置
            global_settings[component_name] = settings
            
            # 保存到文件
            with open(self.global_settings_file, 'w', encoding='utf-8') as f:
                json.dump(global_settings, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"保存全局设置失败: {e}")
            return False
    
    def _load_from_global(self, component_name: str) -> Optional[Dict[str, Any]]:
        """从全局文件加载设置"""
        try:
            if not self.global_settings_file.exists():
                return None
            
            with open(self.global_settings_file, 'r', encoding='utf-8') as f:
                global_settings = json.load(f)
            
            return global_settings.get(component_name)
            
        except Exception as e:
            logger.error(f"加载全局设置失败: {e}")
            return None
    
    def clear_cache(self):
        """清空设置缓存"""
        self.settings_cache.clear()
        logger.info("设置缓存已清空")
    
    def set_project_manager(self, project_manager):
        """设置项目管理器"""
        self.project_manager = project_manager
        self.clear_cache()  # 清空缓存，重新加载设置
    
    def _migrate_old_image_settings(self, old_settings: Dict[str, Any]) -> Dict[str, Any]:
        """迁移旧的图像生成设置格式"""
        try:
            migrated = {}
            
            # 引擎设置迁移
            if "engine" in old_settings:
                engine_display = old_settings["engine"]
                # 将显示名称转换为引擎标识符
                engine_mapping = {
                    "CogView-3 Flash (免费)": "cogview_3_flash",
                    "Pollinations AI (免费)": "pollinations",
                    "ComfyUI本地": "comfyui_local",
                    "ComfyUI云端": "comfyui_cloud"
                }
                migrated["engine"] = engine_mapping.get(engine_display, "pollinations")
            
            # 直接映射的设置
            direct_mappings = [
                "width", "height", "steps", "cfg_scale", "seed_mode", "seed_value",
                "sampler", "negative_prompt", "retry_count", "delay", "batch_size",
                "concurrent_tasks", "pollinations_model", "pollinations_enhance", 
                "pollinations_logo"
            ]
            for key in direct_mappings:
                if key in old_settings:
                    migrated[key] = old_settings[key]
            
            # 添加默认值
            defaults = {
                "style": "电影风格",
                "batch_size": 1,
                "concurrent_tasks": 3,
                "seed_mode": "随机"
            }
            for key, default_value in defaults.items():
                if key not in migrated:
                    migrated[key] = default_value
            
            logger.info(f"迁移图像设置: {len(old_settings)} -> {len(migrated)} 项")
            return migrated
            
        except Exception as e:
            logger.error(f"迁移旧设置失败: {e}")
            return {}