# -*- coding: utf-8 -*-
"""
发布器数据库服务（简化版）
管理发布相关的数据操作，使用JSON文件存储
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import os
from enum import Enum

from src.utils.logger import logger


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PublishStatus(Enum):
    """发布状态"""
    PENDING = "pending"
    UPLOADING = "uploading"
    PUBLISHED = "published"
    FAILED = "failed"


class ConversionStatus(Enum):
    """转换状态"""
    PENDING = "pending"
    CONVERTING = "converting"
    COMPLETED = "completed"
    FAILED = "failed"


class PublisherDatabaseService:
    """发布器数据库服务（简化版，使用JSON文件存储）"""
    
    def __init__(self, database_path: str = None):
        if database_path is None:
            # 默认使用JSON文件
            db_dir = "data/publisher"
            os.makedirs(db_dir, exist_ok=True)
            self.database_path = f"{db_dir}/publisher_data.json"
        else:
            self.database_path = database_path
            
        # 初始化数据结构
        self.data = {
            "video_tasks": [],
            "publish_records": [],
            "platform_accounts": [],
            "publish_templates": [],
            "publish_schedules": [],
            "conversion_records": [],
            "login_states": {}  # 新增：平台登录状态数据
        }
        
        # 加载数据
        self._load_data()
        
        logger.info(f"发布器数据服务初始化完成: {self.database_path}")
        
    def _load_data(self):
        """加载数据"""
        try:
            if os.path.exists(self.database_path):
                with open(self.database_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                logger.info(f"已加载发布器数据: {self.database_path}")
            else:
                # 创建新数据文件
                self._save_data()
                logger.info(f"已创建新的发布器数据文件: {self.database_path}")
        except Exception as e:
            logger.error(f"加载发布器数据失败: {e}")
            
    def _save_data(self):
        """保存数据（私有方法）"""
        try:
            with open(self.database_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存发布器数据: {self.database_path}")
        except Exception as e:
            logger.error(f"保存发布器数据失败: {e}")

    def save_data(self):
        """🔧 新增：保存数据（公有方法）"""
        return self._save_data()
    
    # 简化的方法实现
    def create_video_task(self, task_data: Dict[str, Any]) -> str:
        """创建视频任务"""
        task_id = f"task_{len(self.data['video_tasks']) + 1}_{int(datetime.now().timestamp())}"
        task = {
            "id": task_id,
            "created_at": datetime.now().isoformat(),
            "status": TaskStatus.PENDING.value,
            **task_data
        }
        self.data['video_tasks'].append(task)
        self._save_data()
        return task_id
    
    def get_video_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取视频任务"""
        for task in self.data['video_tasks']:
            if task['id'] == task_id:
                return task
        return None
    
    def update_video_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """更新视频任务"""
        for task in self.data['video_tasks']:
            if task['id'] == task_id:
                task.update(updates)
                task['updated_at'] = datetime.now().isoformat()
                self._save_data()
                return True
        return False

    def update_task_status(self, task_id: str, status: str, message: str = None, progress: float = None) -> bool:
        """更新任务状态"""
        for task in self.data['video_tasks']:
            if task['id'] == task_id:
                task['status'] = status
                task['updated_at'] = datetime.now().isoformat()
                if message:
                    task['message'] = message
                if progress is not None:
                    task['progress'] = progress
                self._save_data()
                return True
        return False

    def create_conversion_record(self, record_data: Dict[str, Any]) -> str:
        """创建转换记录"""
        record_id = f"conversion_{len(self.data.get('conversion_records', [])) + 1}_{int(datetime.now().timestamp())}"

        # 确保conversion_records存在
        if 'conversion_records' not in self.data:
            self.data['conversion_records'] = []

        record = {
            "id": record_id,
            "created_at": datetime.now().isoformat(),
            "status": ConversionStatus.PENDING.value,
            **record_data
        }
        self.data['conversion_records'].append(record)
        self._save_data()
        return record_id
    
    def create_publish_record(self, record_data: Dict[str, Any]) -> str:
        """创建发布记录"""
        record_id = f"record_{len(self.data['publish_records']) + 1}_{int(datetime.now().timestamp())}"
        record = {
            "id": record_id,
            "created_at": datetime.now().isoformat(),
            "status": PublishStatus.PENDING.value,
            **record_data
        }
        self.data['publish_records'].append(record)
        self._save_data()
        return record_id
    
    def get_publish_records(self, task_id: str = None) -> List[Dict[str, Any]]:
        """获取发布记录"""
        if task_id:
            return [r for r in self.data['publish_records'] if r.get('task_id') == task_id]
        return self.data['publish_records']
    
    def close(self):
        """关闭服务"""
        self._save_data()
        logger.info("发布器数据服务已关闭")

    # 🔧 新增：登录状态管理方法
    def save_login_state(self, platform: str, login_data: Dict[str, Any]) -> bool:
        """保存平台登录状态"""
        try:
            # 确保login_states存在
            if 'login_states' not in self.data:
                self.data['login_states'] = {}

            # 只在没有saved_at时才添加时间戳（保持原有时间戳用于测试）
            if 'saved_at' not in login_data:
                login_data['saved_at'] = datetime.now().isoformat()
            login_data['platform'] = platform

            # 保存登录状态
            self.data['login_states'][platform] = login_data
            self._save_data()

            logger.info(f"✅ {platform} 登录状态已保存到数据库")
            return True

        except Exception as e:
            logger.error(f"❌ 保存 {platform} 登录状态失败: {e}")
            return False

    def load_login_state(self, platform: str) -> Dict[str, Any]:
        """加载平台登录状态"""
        try:
            if 'login_states' not in self.data:
                return {}

            return self.data['login_states'].get(platform, {})

        except Exception as e:
            logger.error(f"❌ 加载 {platform} 登录状态失败: {e}")
            return {}

    def clear_login_state(self, platform: str) -> bool:
        """清除平台登录状态"""
        try:
            if 'login_states' not in self.data:
                return True

            if platform in self.data['login_states']:
                del self.data['login_states'][platform]
                self._save_data()
                logger.info(f"🗑️ {platform} 登录状态已从数据库清除")

            return True

        except Exception as e:
            logger.error(f"❌ 清除 {platform} 登录状态失败: {e}")
            return False

    def get_all_login_states(self) -> Dict[str, Dict[str, Any]]:
        """获取所有平台的登录状态"""
        try:
            return self.data.get('login_states', {})
        except Exception as e:
            logger.error(f"❌ 获取所有登录状态失败: {e}")
            return {}

    def is_login_state_valid(self, platform: str, expire_hours: int = 168) -> bool:
        """检查登录状态是否有效（默认7天过期）"""
        try:
            login_state = self.load_login_state(platform)
            if not login_state:
                return False

            # 检查时间戳（优先使用timestamp，其次使用saved_at）
            timestamp = login_state.get('timestamp')
            saved_at = login_state.get('saved_at')

            if timestamp:
                # 使用Unix时间戳
                import time
                current_time = time.time()
                expire_time = timestamp + (expire_hours * 3600)
                is_valid = current_time < expire_time
            elif saved_at:
                # 使用ISO格式时间
                from datetime import datetime, timedelta
                saved_time = datetime.fromisoformat(saved_at)
                expire_time = saved_time + timedelta(hours=expire_hours)
                is_valid = datetime.now() < expire_time
            else:
                logger.warning(f"⚠️ {platform} 登录状态缺少时间戳")
                return False

            if not is_valid:
                logger.info(f"⏰ {platform} 登录状态已过期")

            return is_valid

        except Exception as e:
            logger.error(f"❌ 检查 {platform} 登录状态有效性失败: {e}")
            return False
