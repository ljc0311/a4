# -*- coding: utf-8 -*-
"""
简化版一键发布服务
不依赖SQLAlchemy，使用JSON文件存储数据
"""

import os
import json
import uuid
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from pathlib import Path

from .platform_publisher.publisher_factory import PublisherFactory
from .platform_publisher.base_publisher import VideoMetadata, PublishResult
from src.utils.logger import logger
from src.services.publisher_database_service import PublisherDatabaseService

class SimplePublisherService:
    """简化版发布服务"""
    
    def __init__(self):
        self.publisher_factory = PublisherFactory()

        # 🔧 优化：使用统一的数据库服务
        self.db_service = PublisherDatabaseService()

        # 保留数据存储目录用于兼容性（如果需要迁移旧数据）
        self.data_dir = Path("data/publisher")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 数据文件路径（用于数据迁移）
        self.accounts_file = self.data_dir / "accounts.json"
        self.tasks_file = self.data_dir / "tasks.json"
        self.records_file = self.data_dir / "records.json"

        # 🔧 新增：自动迁移旧数据到数据库
        self._migrate_old_data_if_needed()

        logger.info("简化版发布服务初始化完成（使用统一数据库）")

    def _migrate_old_data_if_needed(self):
        """🔧 新增：迁移旧数据到统一数据库"""
        try:
            migrated_count = 0

            # 迁移账号数据
            if self.accounts_file.exists():
                accounts = self._load_json(self.accounts_file)
                for account in accounts:
                    # 转换为数据库格式并保存
                    account_data = {
                        'platform_name': account.get('platform_name', ''),
                        'account_name': account.get('account_name', ''),
                        'credentials': account.get('credentials', {}),
                        'is_active': account.get('is_active', True),
                        'last_login': account.get('last_login'),
                        'created_at': account.get('created_at', datetime.now().isoformat()),
                        'updated_at': account.get('updated_at', datetime.now().isoformat())
                    }

                    # 检查是否已存在
                    existing_accounts = self.db_service.data.get('platform_accounts', [])
                    account_exists = any(
                        acc.get('platform_name') == account_data['platform_name'] and
                        acc.get('account_name') == account_data['account_name']
                        for acc in existing_accounts
                    )

                    if not account_exists:
                        account_data['id'] = f"account_{len(existing_accounts) + 1}_{int(datetime.now().timestamp())}"
                        self.db_service.data['platform_accounts'].append(account_data)
                        migrated_count += 1

                logger.info(f"迁移了 {migrated_count} 个账号到数据库")

            # 迁移任务数据
            if self.tasks_file.exists():
                tasks = self._load_json(self.tasks_file)
                for task in tasks:
                    # 检查是否已存在
                    existing_tasks = self.db_service.data.get('video_tasks', [])
                    task_exists = any(
                        t.get('id') == task.get('id') for t in existing_tasks
                    )

                    if not task_exists:
                        self.db_service.data['video_tasks'].append(task)
                        migrated_count += 1

                logger.info(f"迁移了 {len(tasks)} 个任务到数据库")

            # 迁移发布记录
            if self.records_file.exists():
                records = self._load_json(self.records_file)
                for record in records:
                    # 检查是否已存在
                    existing_records = self.db_service.data.get('publish_records', [])
                    record_exists = any(
                        r.get('id') == record.get('id') for r in existing_records
                    )

                    if not record_exists:
                        self.db_service.data['publish_records'].append(record)
                        migrated_count += 1

                logger.info(f"迁移了 {len(records)} 个发布记录到数据库")

            # 保存迁移后的数据
            if migrated_count > 0:
                self.db_service._save_data()
                logger.info(f"✅ 数据迁移完成，共迁移 {migrated_count} 条记录")

        except Exception as e:
            logger.error(f"数据迁移失败: {e}")

    def _init_data_files(self):
        """初始化数据文件"""
        for file_path in [self.accounts_file, self.tasks_file, self.records_file]:
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                    
    def _load_json(self, file_path: Path) -> List[Dict]:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载JSON文件失败 {file_path}: {e}")
            return []
            
    def _save_json(self, file_path: Path, data: List[Dict]) -> bool:
        """保存JSON文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"保存JSON文件失败 {file_path}: {e}")
            return False
            
    # ==================== 账号管理 ====================
    
    def create_platform_account(self, platform: str, account_name: str,
                              credentials: Dict[str, Any]) -> str:
        """🔧 优化：创建平台账号（使用数据库）"""
        try:
            account_data = {
                'platform_name': platform,
                'account_name': account_name,
                'credentials': credentials,
                'is_active': True,
                'last_login': None,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            # 生成账号ID
            account_id = f"account_{len(self.db_service.data.get('platform_accounts', [])) + 1}_{int(datetime.now().timestamp())}"
            account_data['id'] = account_id

            # 保存到数据库
            if 'platform_accounts' not in self.db_service.data:
                self.db_service.data['platform_accounts'] = []

            self.db_service.data['platform_accounts'].append(account_data)
            self.db_service._save_data()

            logger.info(f"创建平台账号成功: {platform} - {account_name}")
            return account_id
                
        except Exception as e:
            logger.error(f"创建平台账号失败: {e}")
            raise
            
    def get_platform_accounts(self, platform: str = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """🔧 优化：获取平台账号列表（使用数据库）"""
        try:
            accounts = self.db_service.data.get('platform_accounts', [])

            result = []
            for account in accounts:
                if platform and account.get('platform_name') != platform:
                    continue
                if active_only and not account.get('is_active', True):
                    continue

                result.append(account)

            return result

        except Exception as e:
            logger.error(f"获取平台账号失败: {e}")
            return []
            
    def delete_platform_account(self, account_id: str) -> bool:
        """删除平台账号"""
        try:
            accounts = self._load_json(self.accounts_file)
            
            # 找到并删除账号
            accounts = [acc for acc in accounts if acc.get('id') != account_id]
            
            if self._save_json(self.accounts_file, accounts):
                logger.info(f"删除平台账号成功: {account_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"删除平台账号失败: {e}")
            return False
            
    # ==================== 发布功能 ====================
    
    async def publish_video(self, 
                           video_path: str,
                           metadata: VideoMetadata,
                           target_platforms: List[str],
                           project_name: str = None,
                           progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """发布视频到多个平台"""
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
                
            if progress_callback:
                progress_callback(0.1, "开始发布任务...")
                
            # 创建任务记录
            task_id = str(uuid.uuid4())
            task_data = {
                'task_id': task_id,
                'project_name': project_name,
                'video_path': video_path,
                'title': metadata.title,
                'description': metadata.description,
                'tags': metadata.tags,
                'target_platforms': target_platforms,
                'status': 'processing',
                'created_at': datetime.now().isoformat()
            }
            
            # 保存任务
            tasks = self._load_json(self.tasks_file)
            tasks.append(task_data)
            self._save_json(self.tasks_file, tasks)
            
            if progress_callback:
                progress_callback(0.2, "开始发布到各平台...")
                
            # 发布到各平台
            publish_results = {}
            success_count = 0
            
            for i, platform in enumerate(target_platforms):
                try:
                    if progress_callback:
                        progress = 0.2 + (i / len(target_platforms)) * 0.7
                        progress_callback(progress, f"发布到 {platform}...")
                        
                    result = await self._publish_to_single_platform(
                        task_id, platform, metadata, video_path
                    )
                    
                    publish_results[platform] = result
                    if result.get('success', False):
                        success_count += 1
                        
                except Exception as e:
                    logger.error(f"发布到 {platform} 失败: {e}")
                    publish_results[platform] = {
                        'success': False,
                        'error': str(e),
                        'platform': platform
                    }
                    
            # 更新任务状态
            if success_count == len(target_platforms):
                status = 'completed'
            elif success_count > 0:
                status = 'partially_completed'
            else:
                status = 'failed'
                
            # 更新任务记录
            tasks = self._load_json(self.tasks_file)
            for task in tasks:
                if task['task_id'] == task_id:
                    task['status'] = status
                    task['completed_at'] = datetime.now().isoformat()
                    break
            self._save_json(self.tasks_file, tasks)
            
            if progress_callback:
                progress_callback(1.0, f"发布完成，成功 {success_count}/{len(target_platforms)} 个平台")
                
            return {
                'task_id': task_id,
                'status': status,
                'success_count': success_count,
                'total_platforms': len(target_platforms),
                'publish_results': publish_results
            }
            
        except Exception as e:
            logger.error(f"发布视频失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def _publish_to_single_platform(self, task_id: str, platform: str, 
                                         metadata: VideoMetadata, video_path: str) -> Dict[str, Any]:
        """发布到单个平台"""
        try:
            # 获取平台账号
            accounts = self.get_platform_accounts(platform)
            if not accounts:
                raise Exception(f"未找到 {platform} 平台的可用账号")
                
            account = accounts[0]  # 使用第一个可用账号
            
            # 创建发布器
            publisher = self.publisher_factory.create_publisher(platform)
            if not publisher:
                raise Exception(f"不支持的平台: {platform}")
                
            # 认证（目前使用模拟认证）
            auth_success = await publisher.authenticate(account['credentials'])
            if not auth_success:
                raise Exception(f"平台 {platform} 认证失败")
                
            # 执行发布（目前使用模拟发布）
            result = await publisher.full_publish_workflow(video_path, metadata)
            
            # 记录发布结果
            record = {
                'id': str(uuid.uuid4()),
                'task_id': task_id,
                'account_id': account['id'],
                'platform_name': platform,
                'platform_video_id': result.video_id,
                'platform_video_url': result.video_url,
                'published_title': metadata.title,
                'published_description': metadata.description,
                'published_tags': metadata.tags,
                'status': 'published' if result.success else 'failed',
                'error_message': result.error_message,
                'publish_time': datetime.now().isoformat() if result.success else None,
                'created_at': datetime.now().isoformat()
            }
            
            records = self._load_json(self.records_file)
            records.append(record)
            self._save_json(self.records_file, records)
            
            return {
                'success': result.success,
                'platform': platform,
                'video_id': result.video_id,
                'video_url': result.video_url,
                'error_message': result.error_message
            }
            
        except Exception as e:
            logger.error(f"发布到 {platform} 失败: {e}")
            return {
                'success': False,
                'platform': platform,
                'error': str(e)
            }
            
    # ==================== 查询功能 ====================
    
    def get_supported_platforms(self) -> List[str]:
        """获取支持的平台列表"""
        return self.publisher_factory.get_supported_platforms()
        
    def get_publish_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """🔧 优化：获取发布历史（使用数据库）"""
        try:
            records = self.db_service.data.get('publish_records', [])
            # 按创建时间倒序排列
            records.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return records[:limit]
        except Exception as e:
            logger.error(f"获取发布历史失败: {e}")
            return []
            
    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """🔧 优化：获取统计信息（使用数据库）"""
        try:
            records = self.db_service.data.get('publish_records', [])
            tasks = self.db_service.data.get('video_tasks', [])

            # 简单统计
            total_tasks = len(tasks)
            total_records = len(records)

            # 按状态统计
            status_counts = {}
            for task in tasks:
                status = task.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1

            # 按平台统计
            platform_stats = {}
            for record in records:
                platform = record.get('platform_name', 'unknown')
                if platform not in platform_stats:
                    platform_stats[platform] = {'total': 0, 'success': 0, 'failed': 0}

                platform_stats[platform]['total'] += 1
                if record.get('status') == 'published':
                    platform_stats[platform]['success'] += 1
                else:
                    platform_stats[platform]['failed'] += 1

            return {
                'total_tasks': total_tasks,
                'total_records': total_records,
                'status_counts': status_counts,
                'platform_stats': platform_stats,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
