# -*- coding: utf-8 -*-
"""
自动保存管理器
提供实时自动保存功能，避免用户数据丢失
"""

import os
import json
import time
import threading
from typing import Dict, Any, Callable, Optional
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from src.utils.logger import logger


class AutoSaveManager(QObject):
    """自动保存管理器"""
    
    save_completed = pyqtSignal(str)  # 保存完成信号
    save_failed = pyqtSignal(str, str)  # 保存失败信号 (path, error)
    
    def __init__(self, save_interval_seconds: int = 30):
        super().__init__()
        self.save_interval = save_interval_seconds * 1000  # 转换为毫秒
        self.auto_save_enabled = True
        self.save_callbacks = {}  # 保存回调函数
        self.last_save_times = {}  # 最后保存时间
        self.pending_saves = set()  # 待保存的项目
        self._lock = threading.Lock()
        
        # 创建定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self._perform_auto_save)
        
        # 创建备份目录
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"自动保存管理器初始化，保存间隔: {save_interval_seconds}秒")
    
    def start_auto_save(self):
        """启动自动保存"""
        if not self.timer.isActive():
            self.timer.start(self.save_interval)
            logger.info("自动保存已启动")
    
    def stop_auto_save(self):
        """停止自动保存"""
        if self.timer.isActive():
            self.timer.stop()
            logger.info("自动保存已停止")
    
    def register_save_callback(self, key: str, callback: Callable[[], Dict[str, Any]], 
                             save_path: str, priority: int = 0):
        """注册保存回调函数
        
        Args:
            key: 唯一标识符
            callback: 返回要保存数据的回调函数
            save_path: 保存路径
            priority: 优先级（数字越小优先级越高）
        """
        with self._lock:
            self.save_callbacks[key] = {
                'callback': callback,
                'save_path': save_path,
                'priority': priority,
                'last_data_hash': None
            }
            logger.debug(f"注册自动保存回调: {key} -> {save_path}")
    
    def unregister_save_callback(self, key: str):
        """取消注册保存回调函数"""
        with self._lock:
            if key in self.save_callbacks:
                del self.save_callbacks[key]
                if key in self.last_save_times:
                    del self.last_save_times[key]
                self.pending_saves.discard(key)
                logger.debug(f"取消注册自动保存回调: {key}")
    
    def mark_dirty(self, key: str):
        """标记数据已修改，需要保存"""
        with self._lock:
            if key in self.save_callbacks:
                self.pending_saves.add(key)
                logger.debug(f"标记需要保存: {key}")
    
    def save_immediately(self, key: str = None) -> bool:
        """立即保存
        
        Args:
            key: 指定保存的项目，None表示保存所有
        
        Returns:
            bool: 是否保存成功
        """
        try:
            if key:
                return self._save_single_item(key)
            else:
                return self._save_all_items()
        except Exception as e:
            logger.error(f"立即保存失败: {e}")
            return False
    
    def _perform_auto_save(self):
        """执行自动保存"""
        if not self.auto_save_enabled:
            return
        
        try:
            with self._lock:
                if not self.pending_saves:
                    return
                
                # 按优先级排序
                sorted_keys = sorted(
                    self.pending_saves,
                    key=lambda k: self.save_callbacks.get(k, {}).get('priority', 999)
                )
            
            for key in sorted_keys:
                try:
                    self._save_single_item(key)
                    with self._lock:
                        self.pending_saves.discard(key)
                except Exception as e:
                    logger.error(f"自动保存失败 {key}: {e}")
                    
        except Exception as e:
            logger.error(f"自动保存过程失败: {e}")
    
    def _save_single_item(self, key: str) -> bool:
        """保存单个项目"""
        try:
            with self._lock:
                if key not in self.save_callbacks:
                    return False
                
                callback_info = self.save_callbacks[key]
            
            # 获取数据
            data = callback_info['callback']()
            if not data:
                return True  # 空数据不需要保存
            
            # 检查数据是否有变化
            data_hash = hash(str(sorted(data.items())) if isinstance(data, dict) else str(data))
            if callback_info['last_data_hash'] == data_hash:
                return True  # 数据未变化，无需保存
            
            # 保存数据
            save_path = Path(callback_info['save_path'])
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建备份
            if save_path.exists():
                self._create_backup(save_path)
            
            # 保存到临时文件，然后重命名（原子操作）
            temp_path = save_path.with_suffix(save_path.suffix + '.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                if isinstance(data, dict):
                    json.dump(data, f, ensure_ascii=False, indent=2)
                else:
                    f.write(str(data))
            
            # 原子重命名
            temp_path.replace(save_path)
            
            # 更新状态
            with self._lock:
                callback_info['last_data_hash'] = data_hash
                self.last_save_times[key] = time.time()
            
            logger.debug(f"自动保存完成: {key} -> {save_path}")
            self.save_completed.emit(str(save_path))
            return True
            
        except Exception as e:
            logger.error(f"保存项目失败 {key}: {e}")
            self.save_failed.emit(callback_info.get('save_path', ''), str(e))
            return False
    
    def _save_all_items(self) -> bool:
        """保存所有项目"""
        success_count = 0
        total_count = 0
        
        with self._lock:
            keys = list(self.save_callbacks.keys())
        
        for key in keys:
            total_count += 1
            if self._save_single_item(key):
                success_count += 1
        
        logger.info(f"批量保存完成: {success_count}/{total_count}")
        return success_count == total_count
    
    def _create_backup(self, file_path: Path):
        """创建备份文件"""
        try:
            if not file_path.exists():
                return
            
            # 生成备份文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            # 复制文件
            import shutil
            shutil.copy2(file_path, backup_path)
            
            # 清理旧备份（保留最近10个）
            self._cleanup_old_backups(file_path.stem)
            
            logger.debug(f"创建备份: {backup_path}")
            
        except Exception as e:
            logger.warning(f"创建备份失败: {e}")
    
    def _cleanup_old_backups(self, file_stem: str, keep_count: int = 10):
        """清理旧备份文件"""
        try:
            # 查找相关备份文件
            backup_files = []
            for backup_file in self.backup_dir.glob(f"{file_stem}_*"):
                if backup_file.is_file():
                    backup_files.append(backup_file)
            
            # 按修改时间排序，保留最新的
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 删除多余的备份
            for old_backup in backup_files[keep_count:]:
                old_backup.unlink()
                logger.debug(f"删除旧备份: {old_backup}")
                
        except Exception as e:
            logger.warning(f"清理旧备份失败: {e}")
    
    def get_save_status(self) -> Dict[str, Any]:
        """获取保存状态"""
        with self._lock:
            return {
                'auto_save_enabled': self.auto_save_enabled,
                'save_interval_seconds': self.save_interval // 1000,
                'registered_callbacks': len(self.save_callbacks),
                'pending_saves': len(self.pending_saves),
                'last_save_times': dict(self.last_save_times)
            }
    
    def set_auto_save_enabled(self, enabled: bool):
        """设置自动保存开关"""
        self.auto_save_enabled = enabled
        if enabled:
            self.start_auto_save()
        else:
            self.stop_auto_save()
        logger.info(f"自动保存{'启用' if enabled else '禁用'}")
    
    def set_save_interval(self, seconds: int):
        """设置保存间隔"""
        self.save_interval = seconds * 1000
        if self.timer.isActive():
            self.timer.stop()
            self.timer.start(self.save_interval)
        logger.info(f"自动保存间隔设置为: {seconds}秒")


# 全局自动保存管理器实例
_auto_save_manager = None


def get_auto_save_manager() -> AutoSaveManager:
    """获取全局自动保存管理器实例"""
    global _auto_save_manager
    if _auto_save_manager is None:
        _auto_save_manager = AutoSaveManager()
    return _auto_save_manager


def register_auto_save(key: str, callback: Callable[[], Dict[str, Any]], 
                      save_path: str, priority: int = 0):
    """注册自动保存（便捷函数）"""
    manager = get_auto_save_manager()
    manager.register_save_callback(key, callback, save_path, priority)


def mark_dirty(key: str):
    """标记数据已修改（便捷函数）"""
    manager = get_auto_save_manager()
    manager.mark_dirty(key)


def save_immediately(key: str = None) -> bool:
    """立即保存（便捷函数）"""
    manager = get_auto_save_manager()
    return manager.save_immediately(key)