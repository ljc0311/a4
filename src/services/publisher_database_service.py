# -*- coding: utf-8 -*-
"""
发布器数据库服务
管理发布相关的数据操作
"""

from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import os
from cryptography.fernet import Fernet

from src.models.publisher_models import (
    Base, VideoTask, PublishRecord, PlatformAccount, 
    PublishTemplate, PublishSchedule, ConversionRecord,
    TaskStatus, PublishStatus, ConversionStatus
)
from src.utils.logger import logger

class PublisherDatabaseService:
    """发布器数据库服务"""
    
    def __init__(self, database_url: str = None):
        if database_url is None:
            # 默认使用SQLite数据库
            db_dir = "data/publisher"
            os.makedirs(db_dir, exist_ok=True)
            database_url = f"sqlite:///{db_dir}/publisher.db"
            
        self.engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # 初始化加密密钥
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        
        logger.info(f"发布器数据库服务初始化完成: {database_url}")
        
    def _get_or_create_encryption_key(self) -> bytes:
        """获取或创建加密密钥"""
        key_file = "config/publisher_encryption.key"
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            logger.info("创建新的加密密钥")
            return key
            
    # ==================== 视频任务管理 ====================
    
    def create_video_task(self, task_data: Dict[str, Any]) -> str:
        """创建视频任务"""
        try:
            with self.SessionLocal() as session:
                task = VideoTask(
                    project_name=task_data.get('project_name'),
                    video_path=task_data['video_path'],
                    title=task_data['title'],
                    description=task_data.get('description', ''),
                    tags=task_data.get('tags', []),
                    cover_path=task_data.get('cover_path'),
                    target_platforms=task_data.get('target_platforms', []),
                    schedule_time=task_data.get('schedule_time'),
                    priority=task_data.get('priority', 0)
                )
                session.add(task)
                session.commit()
                
                logger.info(f"创建视频任务成功: {task.task_id}")
                return task.task_id
                
        except Exception as e:
            logger.error(f"创建视频任务失败: {e}")
            raise
            
    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取任务"""
        try:
            with self.SessionLocal() as session:
                task = session.query(VideoTask).filter(VideoTask.task_id == task_id).first()
                if task:
                    return {
                        'task_id': task.task_id,
                        'project_name': task.project_name,
                        'video_path': task.video_path,
                        'title': task.title,
                        'description': task.description,
                        'tags': task.tags,
                        'cover_path': task.cover_path,
                        'target_platforms': task.target_platforms,
                        'schedule_time': task.schedule_time,
                        'priority': task.priority,
                        'status': task.status,
                        'progress': task.progress,
                        'error_message': task.error_message,
                        'created_at': task.created_at,
                        'updated_at': task.updated_at,
                        'completed_at': task.completed_at
                    }
                return None
        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return None
            
    def update_task_status(self, task_id: str, status: str, progress: float = None, 
                          error_message: str = None) -> bool:
        """更新任务状态"""
        try:
            with self.SessionLocal() as session:
                task = session.query(VideoTask).filter(VideoTask.task_id == task_id).first()
                if task:
                    task.status = status
                    if progress is not None:
                        task.progress = progress
                    if error_message is not None:
                        task.error_message = error_message
                    if status == TaskStatus.COMPLETED:
                        task.completed_at = datetime.utcnow()
                    task.updated_at = datetime.utcnow()
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            return False
            
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """获取待处理任务"""
        try:
            with self.SessionLocal() as session:
                tasks = session.query(VideoTask).filter(
                    VideoTask.status == TaskStatus.PENDING
                ).order_by(VideoTask.priority.desc(), VideoTask.created_at).all()
                
                return [self._task_to_dict(task) for task in tasks]
        except Exception as e:
            logger.error(f"获取待处理任务失败: {e}")
            return []
            
    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """获取需要执行的定时任务"""
        try:
            with self.SessionLocal() as session:
                now = datetime.utcnow()
                tasks = session.query(VideoTask).filter(
                    and_(
                        VideoTask.status == TaskStatus.PENDING,
                        VideoTask.schedule_time <= now
                    )
                ).all()
                
                return [self._task_to_dict(task) for task in tasks]
        except Exception as e:
            logger.error(f"获取定时任务失败: {e}")
            return []
            
    def _task_to_dict(self, task: VideoTask) -> Dict[str, Any]:
        """将任务对象转换为字典"""
        return {
            'task_id': task.task_id,
            'project_name': task.project_name,
            'video_path': task.video_path,
            'title': task.title,
            'description': task.description,
            'tags': task.tags,
            'cover_path': task.cover_path,
            'target_platforms': task.target_platforms,
            'schedule_time': task.schedule_time,
            'priority': task.priority,
            'status': task.status,
            'progress': task.progress,
            'error_message': task.error_message,
            'created_at': task.created_at,
            'updated_at': task.updated_at,
            'completed_at': task.completed_at
        }
        
    # ==================== 平台账号管理 ====================
    
    def create_platform_account(self, platform: str, account_name: str, 
                              credentials: Dict[str, Any]) -> int:
        """创建平台账号"""
        try:
            with self.SessionLocal() as session:
                # 加密凭证
                encrypted_credentials = self.cipher.encrypt(
                    json.dumps(credentials).encode()
                )
                
                account = PlatformAccount(
                    platform_name=platform,
                    account_name=account_name,
                    credentials=encrypted_credentials.decode()
                )
                session.add(account)
                session.commit()
                
                logger.info(f"创建平台账号成功: {platform} - {account_name}")
                return account.id
                
        except Exception as e:
            logger.error(f"创建平台账号失败: {e}")
            raise
            
    def get_platform_accounts(self, platform: str = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """获取平台账号列表"""
        try:
            with self.SessionLocal() as session:
                query = session.query(PlatformAccount)
                
                if platform:
                    query = query.filter(PlatformAccount.platform_name == platform)
                if active_only:
                    query = query.filter(PlatformAccount.is_active == True)
                
                accounts = query.all()
                
                result = []
                for account in accounts:
                    try:
                        # 解密凭证
                        decrypted_credentials = json.loads(
                            self.cipher.decrypt(account.credentials.encode()).decode()
                        )
                        
                        result.append({
                            'id': account.id,
                            'platform_name': account.platform_name,
                            'account_name': account.account_name,
                            'account_id': account.account_id,
                            'credentials': decrypted_credentials,
                            'last_login': account.last_login,
                            'is_active': account.is_active,
                            'created_at': account.created_at
                        })
                    except Exception as e:
                        logger.error(f"解密账号凭证失败: {e}")
                        continue
                
                return result
                
        except Exception as e:
            logger.error(f"获取平台账号失败: {e}")
            return []
            
    def get_account_by_id(self, account_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取账号"""
        try:
            with self.SessionLocal() as session:
                account = session.query(PlatformAccount).filter(
                    PlatformAccount.id == account_id
                ).first()
                
                if account:
                    # 解密凭证
                    decrypted_credentials = json.loads(
                        self.cipher.decrypt(account.credentials.encode()).decode()
                    )
                    
                    return {
                        'id': account.id,
                        'platform_name': account.platform_name,
                        'account_name': account.account_name,
                        'account_id': account.account_id,
                        'credentials': decrypted_credentials,
                        'last_login': account.last_login,
                        'is_active': account.is_active
                    }
                return None
                
        except Exception as e:
            logger.error(f"获取账号失败: {e}")
            return None
            
    def update_account_login_time(self, account_id: int) -> bool:
        """更新账号登录时间"""
        try:
            with self.SessionLocal() as session:
                account = session.query(PlatformAccount).filter(
                    PlatformAccount.id == account_id
                ).first()
                
                if account:
                    account.last_login = datetime.utcnow()
                    account.updated_at = datetime.utcnow()
                    session.commit()
                    return True
                return False
                
        except Exception as e:
            logger.error(f"更新账号登录时间失败: {e}")
            return False

    # ==================== 发布记录管理 ====================

    def create_publish_record(self, task_id: str, account_id: int, platform: str,
                            result: Dict[str, Any]) -> int:
        """创建发布记录"""
        try:
            with self.SessionLocal() as session:
                record = PublishRecord(
                    task_id=task_id,
                    account_id=account_id,
                    platform_name=platform,
                    platform_video_id=result.get('video_id'),
                    platform_video_url=result.get('video_url'),
                    published_title=result.get('title'),
                    published_description=result.get('description'),
                    published_tags=result.get('tags'),
                    converted_video_path=result.get('converted_video_path'),
                    status=PublishStatus.PUBLISHED if result.get('success') else PublishStatus.FAILED,
                    error_message=result.get('error_message'),
                    publish_time=datetime.utcnow() if result.get('success') else None,
                    raw_response=result.get('raw_response')
                )
                session.add(record)
                session.commit()

                logger.info(f"创建发布记录成功: {task_id} -> {platform}")
                return record.id

        except Exception as e:
            logger.error(f"创建发布记录失败: {e}")
            raise

    def get_publish_records(self, task_id: str = None, platform: str = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """获取发布记录"""
        try:
            with self.SessionLocal() as session:
                query = session.query(PublishRecord)

                if task_id:
                    query = query.filter(PublishRecord.task_id == task_id)
                if platform:
                    query = query.filter(PublishRecord.platform_name == platform)

                records = query.order_by(PublishRecord.created_at.desc()).limit(limit).all()

                return [self._record_to_dict(record) for record in records]

        except Exception as e:
            logger.error(f"获取发布记录失败: {e}")
            return []

    def _record_to_dict(self, record: PublishRecord) -> Dict[str, Any]:
        """将发布记录对象转换为字典"""
        return {
            'id': record.id,
            'task_id': record.task_id,
            'account_id': record.account_id,
            'platform_name': record.platform_name,
            'platform_video_id': record.platform_video_id,
            'platform_video_url': record.platform_video_url,
            'published_title': record.published_title,
            'published_description': record.published_description,
            'published_tags': record.published_tags,
            'converted_video_path': record.converted_video_path,
            'status': record.status,
            'error_message': record.error_message,
            'publish_time': record.publish_time,
            'view_count': record.view_count,
            'like_count': record.like_count,
            'comment_count': record.comment_count,
            'share_count': record.share_count,
            'raw_response': record.raw_response,
            'created_at': record.created_at,
            'updated_at': record.updated_at
        }

    # ==================== 转换记录管理 ====================

    def create_conversion_record(self, task_id: str, platform: str,
                               conversion_data: Dict[str, Any]) -> int:
        """创建转换记录"""
        try:
            with self.SessionLocal() as session:
                record = ConversionRecord(
                    task_id=task_id,
                    platform_name=platform,
                    input_path=conversion_data['input_path'],
                    output_path=conversion_data.get('output_path'),
                    conversion_status=ConversionStatus.COMPLETED if conversion_data.get('success') else ConversionStatus.FAILED,
                    target_resolution=conversion_data.get('target_resolution'),
                    target_fps=conversion_data.get('target_fps'),
                    target_bitrate=conversion_data.get('target_bitrate'),
                    target_format=conversion_data.get('target_format'),
                    original_size=conversion_data.get('original_size'),
                    converted_size=conversion_data.get('converted_size'),
                    conversion_time=conversion_data.get('conversion_time'),
                    error_message=conversion_data.get('error_message')
                )
                session.add(record)
                session.commit()

                return record.id

        except Exception as e:
            logger.error(f"创建转换记录失败: {e}")
            raise

    def get_converted_video_path(self, task_id: str, platform: str) -> Optional[str]:
        """获取转换后的视频路径"""
        try:
            with self.SessionLocal() as session:
                record = session.query(ConversionRecord).filter(
                    and_(
                        ConversionRecord.task_id == task_id,
                        ConversionRecord.platform_name == platform,
                        ConversionRecord.conversion_status == ConversionStatus.COMPLETED
                    )
                ).first()

                return record.output_path if record else None

        except Exception as e:
            logger.error(f"获取转换视频路径失败: {e}")
            return None

    # ==================== 统计和查询 ====================

    def get_task_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取任务统计信息"""
        try:
            with self.SessionLocal() as session:
                start_date = datetime.utcnow() - timedelta(days=days)

                # 总任务数
                total_tasks = session.query(VideoTask).filter(
                    VideoTask.created_at >= start_date
                ).count()

                # 各状态任务数
                status_counts = {}
                for status in [TaskStatus.PENDING, TaskStatus.PROCESSING, TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    count = session.query(VideoTask).filter(
                        and_(
                            VideoTask.created_at >= start_date,
                            VideoTask.status == status
                        )
                    ).count()
                    status_counts[status] = count

                # 平台发布统计
                platform_stats = {}
                records = session.query(PublishRecord).filter(
                    PublishRecord.created_at >= start_date
                ).all()

                for record in records:
                    platform = record.platform_name
                    if platform not in platform_stats:
                        platform_stats[platform] = {'total': 0, 'success': 0, 'failed': 0}

                    platform_stats[platform]['total'] += 1
                    if record.status == PublishStatus.PUBLISHED:
                        platform_stats[platform]['success'] += 1
                    else:
                        platform_stats[platform]['failed'] += 1

                return {
                    'total_tasks': total_tasks,
                    'status_counts': status_counts,
                    'platform_stats': platform_stats,
                    'period_days': days
                }

        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            return {}

    def cleanup_old_records(self, days: int = 90) -> int:
        """清理旧记录"""
        try:
            with self.SessionLocal() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)

                # 清理已完成的旧任务
                deleted_tasks = session.query(VideoTask).filter(
                    and_(
                        VideoTask.status == TaskStatus.COMPLETED,
                        VideoTask.completed_at < cutoff_date
                    )
                ).delete()

                # 清理旧的转换记录
                deleted_conversions = session.query(ConversionRecord).filter(
                    ConversionRecord.created_at < cutoff_date
                ).delete()

                session.commit()

                total_deleted = deleted_tasks + deleted_conversions
                logger.info(f"清理旧记录完成，删除 {total_deleted} 条记录")
                return total_deleted

        except Exception as e:
            logger.error(f"清理旧记录失败: {e}")
            return 0

    def delete_platform_account(self, account_id: int) -> bool:
        """删除平台账号"""
        try:
            with self.SessionLocal() as session:
                account = session.query(PlatformAccount).filter(
                    PlatformAccount.id == account_id
                ).first()

                if account:
                    session.delete(account)
                    session.commit()
                    logger.info(f"删除平台账号成功: {account_id}")
                    return True
                return False

        except Exception as e:
            logger.error(f"删除平台账号失败: {e}")
            return False
