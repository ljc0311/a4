#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色场景数据同步器
实现一致性控制面板和五阶段分镜之间的双向数据同步
"""

import threading
from typing import Dict, Any, Optional, Callable, List
from src.utils.logger import logger


class CharacterSceneSyncManager:
    """角色场景数据同步管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # 注册的组件
        self.consistency_panel = None
        self.five_stage_tab = None
        
        # 数据变更监听器
        self.character_listeners: List[Callable] = []
        self.scene_listeners: List[Callable] = []
        
        logger.info("角色场景数据同步管理器初始化完成")
    
    def register_consistency_panel(self, panel):
        """注册一致性控制面板"""
        self.consistency_panel = panel
        logger.info("已注册一致性控制面板")
    
    def register_five_stage_tab(self, tab):
        """注册五阶段分镜标签页"""
        self.five_stage_tab = tab
        logger.info("已注册五阶段分镜标签页")
    
    def add_character_listener(self, listener: Callable):
        """添加角色数据变更监听器"""
        if listener not in self.character_listeners:
            self.character_listeners.append(listener)
    
    def add_scene_listener(self, listener: Callable):
        """添加场景数据变更监听器"""
        if listener not in self.scene_listeners:
            self.scene_listeners.append(listener)
    
    def notify_character_changed(self, character_id: str, character_data: Dict[str, Any], operation: str = 'update'):
        """通知角色数据变更"""
        try:
            logger.info(f"角色数据变更通知: {operation} - {character_id}")
            
            # 同步到一致性控制面板
            if self.consistency_panel and hasattr(self.consistency_panel, 'load_character_scene_data'):
                self.consistency_panel.load_character_scene_data()
            
            # 同步到五阶段分镜
            if self.five_stage_tab and hasattr(self.five_stage_tab, 'refresh_character_data'):
                self.five_stage_tab.refresh_character_data()
            
            # 通知所有监听器
            for listener in self.character_listeners:
                try:
                    listener(character_id, character_data, operation)
                except Exception as e:
                    logger.error(f"角色数据变更监听器执行失败: {e}")
                    
        except Exception as e:
            logger.error(f"角色数据变更通知失败: {e}")
    
    def notify_scene_changed(self, scene_id: str, scene_data: Dict[str, Any], operation: str = 'update'):
        """通知场景数据变更"""
        try:
            logger.info(f"场景数据变更通知: {operation} - {scene_id}")
            
            # 同步到一致性控制面板
            if self.consistency_panel and hasattr(self.consistency_panel, 'load_character_scene_data'):
                self.consistency_panel.load_character_scene_data()
            
            # 同步到五阶段分镜
            if self.five_stage_tab and hasattr(self.five_stage_tab, 'refresh_scene_data'):
                self.five_stage_tab.refresh_scene_data()
            
            # 通知所有监听器
            for listener in self.scene_listeners:
                try:
                    listener(scene_id, scene_data, operation)
                except Exception as e:
                    logger.error(f"场景数据变更监听器执行失败: {e}")
                    
        except Exception as e:
            logger.error(f"场景数据变更通知失败: {e}")
    
    def sync_character_from_consistency_to_five_stage(self, character_id: str, character_data: Dict[str, Any]):
        """从一致性面板同步角色数据到五阶段分镜"""
        try:
            if self.five_stage_tab and hasattr(self.five_stage_tab, 'character_scene_manager'):
                cs_manager = self.five_stage_tab.character_scene_manager
                if cs_manager:
                    cs_manager.save_character(character_id, character_data)
                    logger.info(f"角色数据已同步到五阶段分镜: {character_id}")
        except Exception as e:
            logger.error(f"同步角色数据到五阶段分镜失败: {e}")
    
    def sync_scene_from_consistency_to_five_stage(self, scene_id: str, scene_data: Dict[str, Any]):
        """从一致性面板同步场景数据到五阶段分镜"""
        try:
            if self.five_stage_tab and hasattr(self.five_stage_tab, 'character_scene_manager'):
                cs_manager = self.five_stage_tab.character_scene_manager
                if cs_manager:
                    cs_manager.save_scene(scene_id, scene_data)
                    logger.info(f"场景数据已同步到五阶段分镜: {scene_id}")
        except Exception as e:
            logger.error(f"同步场景数据到五阶段分镜失败: {e}")
    
    def sync_character_from_five_stage_to_consistency(self, character_id: str, character_data: Dict[str, Any]):
        """从五阶段分镜同步角色数据到一致性面板"""
        try:
            if self.consistency_panel and hasattr(self.consistency_panel, 'cs_manager'):
                cs_manager = self.consistency_panel.cs_manager
                if cs_manager:
                    cs_manager.save_character(character_id, character_data)
                    logger.info(f"角色数据已同步到一致性面板: {character_id}")
        except Exception as e:
            logger.error(f"同步角色数据到一致性面板失败: {e}")
    
    def sync_scene_from_five_stage_to_consistency(self, scene_id: str, scene_data: Dict[str, Any]):
        """从五阶段分镜同步场景数据到一致性面板"""
        try:
            if self.consistency_panel and hasattr(self.consistency_panel, 'cs_manager'):
                cs_manager = self.consistency_panel.cs_manager
                if cs_manager:
                    cs_manager.save_scene(scene_id, scene_data)
                    logger.info(f"场景数据已同步到一致性面板: {scene_id}")
        except Exception as e:
            logger.error(f"同步场景数据到一致性面板失败: {e}")
    
    def force_sync_all_data(self):
        """强制同步所有数据"""
        try:
            logger.info("开始强制同步所有角色场景数据...")
            
            # 刷新一致性控制面板
            if self.consistency_panel and hasattr(self.consistency_panel, 'load_character_scene_data'):
                self.consistency_panel.load_character_scene_data()
            
            # 刷新五阶段分镜
            if self.five_stage_tab:
                if hasattr(self.five_stage_tab, 'refresh_character_data'):
                    self.five_stage_tab.refresh_character_data()
                if hasattr(self.five_stage_tab, 'refresh_scene_data'):
                    self.five_stage_tab.refresh_scene_data()
            
            logger.info("强制同步所有数据完成")
            
        except Exception as e:
            logger.error(f"强制同步所有数据失败: {e}")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            'consistency_panel_registered': self.consistency_panel is not None,
            'five_stage_tab_registered': self.five_stage_tab is not None,
            'character_listeners_count': len(self.character_listeners),
            'scene_listeners_count': len(self.scene_listeners)
        }


# 全局同步管理器实例
sync_manager = CharacterSceneSyncManager()


def get_sync_manager() -> CharacterSceneSyncManager:
    """获取同步管理器实例"""
    return sync_manager


def register_consistency_panel(panel):
    """便捷函数：注册一致性控制面板"""
    sync_manager.register_consistency_panel(panel)


def register_five_stage_tab(tab):
    """便捷函数：注册五阶段分镜标签页"""
    sync_manager.register_five_stage_tab(tab)


def notify_character_changed(character_id: str, character_data: Dict[str, Any], operation: str = 'update'):
    """便捷函数：通知角色数据变更"""
    sync_manager.notify_character_changed(character_id, character_data, operation)


def notify_scene_changed(scene_id: str, scene_data: Dict[str, Any], operation: str = 'update'):
    """便捷函数：通知场景数据变更"""
    sync_manager.notify_scene_changed(scene_id, scene_data, operation)
