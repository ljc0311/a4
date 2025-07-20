# -*- coding: utf-8 -*-
"""
一键发布服务
统一管理多平台视频发布流程
"""

import asyncio
import os
import time
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from pathlib import Path

from .platform_publisher.publisher_factory import PublisherFactory
from .video_format_converter import VideoFormatConverter
from .publisher_database_service import PublisherDatabaseService
from .platform_publisher.base_publisher import VideoMetadata, PublishResult
from src.utils.logger import logger

class OneClickPublisher:
    """一键发布服务"""
    
    def __init__(self):
        self.publisher_factory = PublisherFactory()
        self.video_converter = VideoFormatConverter()
        self.db_service = PublisherDatabaseService()
        
        # 创建输出目录
        self.output_dir = Path("output/published_videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("一键发布服务初始化完成")
        
    async def publish_video(self, 
                           video_path: str,
                           metadata: VideoMetadata,
                           target_platforms: List[str],
                           project_name: str = None,
                           progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        一键发布视频到多个平台
        
        Args:
            video_path: 视频文件路径
            metadata: 视频元数据
            target_platforms: 目标平台列表
            project_name: 项目名称
            progress_callback: 进度回调函数
            
        Returns:
            Dict: 发布结果
        """
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
                
            if progress_callback:
                progress_callback(0.05, "创建发布任务...")
                
            # 1. 创建发布任务
            task_id = self._create_publish_task(
                video_path, metadata, target_platforms, project_name
            )
            
            if progress_callback:
                progress_callback(0.1, "开始视频格式转换...")
                
            # 2. 视频格式转换
            conversion_results = await self._convert_videos_for_platforms(
                task_id, video_path, target_platforms,
                lambda p, msg: progress_callback(0.1 + p * 0.3, msg) if progress_callback else None
            )
            
            if progress_callback:
                progress_callback(0.4, "开始发布到各平台...")
                
            # 3. 并行发布到各平台
            publish_results = await self._publish_to_platforms(
                task_id, metadata, target_platforms, conversion_results,
                lambda p, msg: progress_callback(0.4 + p * 0.5, msg) if progress_callback else None
            )
            
            # 4. 更新任务状态
            success_count = sum(1 for r in publish_results.values() if r.get('success', False))
            if success_count == len(target_platforms):
                self.db_service.update_task_status(task_id, 'completed', 1.0)
                status = 'completed'
            elif success_count > 0:
                self.db_service.update_task_status(task_id, 'partially_completed', 1.0)
                status = 'partially_completed'
            else:
                self.db_service.update_task_status(task_id, 'failed', 1.0, "所有平台发布失败")
                status = 'failed'
                
            if progress_callback:
                progress_callback(1.0, f"发布完成，成功 {success_count}/{len(target_platforms)} 个平台")
                
            return {
                'task_id': task_id,
                'status': status,
                'success_count': success_count,
                'total_platforms': len(target_platforms),
                'conversion_results': conversion_results,
                'publish_results': publish_results
            }
            
        except Exception as e:
            logger.error(f"一键发布失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def _create_publish_task(self, video_path: str, metadata: VideoMetadata, 
                           target_platforms: List[str], project_name: str = None) -> str:
        """创建发布任务"""
        task_data = {
            'project_name': project_name,
            'video_path': video_path,
            'title': metadata.title,
            'description': metadata.description,
            'tags': metadata.tags,
            'cover_path': metadata.cover_path,
            'target_platforms': target_platforms
        }
        
        return self.db_service.create_video_task(task_data)
        
    async def _convert_videos_for_platforms(self, task_id: str, video_path: str, 
                                          platforms: List[str],
                                          progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """为各平台转换视频格式"""
        conversion_results = {}
        total_platforms = len(platforms)
        
        # 创建任务专用输出目录
        task_output_dir = self.output_dir / task_id
        task_output_dir.mkdir(exist_ok=True)
        
        for i, platform in enumerate(platforms):
            try:
                if progress_callback:
                    progress_callback(i / total_platforms, f"转换 {platform} 格式...")
                    
                # 更新任务状态
                self.db_service.update_task_status(task_id, 'converting', (i + 0.5) / total_platforms)
                
                # 执行转换
                result = await self.video_converter.convert_for_platform(
                    input_path=video_path,
                    platform=platform,
                    output_dir=str(task_output_dir),
                    progress_callback=None  # 不传递内部进度
                )
                
                conversion_results[platform] = result
                
                # 记录转换结果
                platform_spec = self.video_converter.PLATFORM_SPECS.get(platform)
                self.db_service.create_conversion_record(task_id, platform, {
                    'input_path': video_path,
                    'output_path': result.get('output_path'),
                    'success': result.get('success', False),
                    'target_resolution': platform_spec.resolution if platform_spec else None,
                    'target_fps': platform_spec.fps if platform_spec else None,
                    'target_bitrate': platform_spec.bitrate if platform_spec else None,
                    'target_format': platform_spec.format if platform_spec else None,
                    'original_size': result.get('original_size'),
                    'converted_size': result.get('converted_size'),
                    'error_message': result.get('error')
                })
                
                logger.info(f"平台 {platform} 视频转换完成")
                
            except Exception as e:
                logger.error(f"平台 {platform} 视频转换失败: {e}")
                conversion_results[platform] = {
                    'success': False,
                    'error': str(e),
                    'platform': platform
                }
                
        if progress_callback:
            progress_callback(1.0, "视频转换完成")
            
        return conversion_results
        
    async def _publish_to_platforms(self, task_id: str, metadata: VideoMetadata,
                                   platforms: List[str], conversion_results: Dict[str, Any],
                                   progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """并行发布到各平台"""
        publish_results = {}
        
        # 创建发布任务
        publish_tasks = []
        for platform in platforms:
            task = self._publish_to_single_platform(
                task_id, platform, metadata, conversion_results.get(platform, {})
            )
            publish_tasks.append((platform, task))
            
        # 等待所有发布任务完成
        total_platforms = len(publish_tasks)
        completed = 0
        
        for platform, task in publish_tasks:
            try:
                result = await task
                publish_results[platform] = result
                completed += 1
                
                if progress_callback:
                    progress_callback(completed / total_platforms, f"已完成 {completed}/{total_platforms} 个平台")
                    
            except Exception as e:
                logger.error(f"平台 {platform} 发布失败: {e}")
                publish_results[platform] = {
                    'success': False,
                    'error': str(e),
                    'platform': platform
                }
                completed += 1
                
        return publish_results
        
    async def _publish_to_single_platform(self, task_id: str, platform: str, 
                                         metadata: VideoMetadata, 
                                         conversion_result: Dict[str, Any]) -> Dict[str, Any]:
        """发布到单个平台"""
        try:
            # 检查转换结果
            if not conversion_result.get('success', False):
                raise Exception(f"视频转换失败: {conversion_result.get('error', '未知错误')}")
                
            # 获取平台账号
            accounts = self.db_service.get_platform_accounts(platform)
            if not accounts:
                raise Exception(f"未找到 {platform} 平台的可用账号")
                
            account = accounts[0]  # 使用第一个可用账号
            
            # 创建发布器
            publisher = self.publisher_factory.create_publisher(platform)
            if not publisher:
                raise Exception(f"不支持的平台: {platform}")
                
            # 认证
            auth_success = await publisher.authenticate(account['credentials'])
            if not auth_success:
                raise Exception(f"平台 {platform} 认证失败")
                
            # 更新登录时间
            self.db_service.update_account_login_time(account['id'])
            
            # 获取转换后的视频路径
            video_path = conversion_result.get('output_path')
            if not video_path or not os.path.exists(video_path):
                raise Exception("转换后的视频文件不存在")
                
            # 执行发布流程（适配不同类型的发布器）
            result = await self._execute_publish_workflow(publisher, video_path, metadata, platform)
            
            # 记录发布结果
            self.db_service.create_publish_record(
                task_id=task_id,
                account_id=account['id'],
                platform=platform,
                result={
                    'success': result.success,
                    'video_id': result.video_id,
                    'video_url': result.video_url,
                    'title': metadata.title,
                    'description': metadata.description,
                    'tags': metadata.tags,
                    'converted_video_path': video_path,
                    'error_message': result.error_message,
                    'raw_response': result.raw_response
                }
            )
            
            return {
                'success': result.success,
                'platform': platform,
                'video_id': result.video_id,
                'video_url': result.video_url,
                'error_message': result.error_message
            }
            
        except Exception as e:
            logger.error(f"发布到 {platform} 失败: {e}")
            
            # 记录失败结果
            try:
                accounts = self.db_service.get_platform_accounts(platform)
                if accounts:
                    self.db_service.create_publish_record(
                        task_id=task_id,
                        account_id=accounts[0]['id'],
                        platform=platform,
                        result={
                            'success': False,
                            'error_message': str(e)
                        }
                    )
            except:
                pass  # 忽略记录失败的错误
                
            return {
                'success': False,
                'platform': platform,
                'error': str(e)
            }
            
    def get_supported_platforms(self) -> List[str]:
        """获取支持的平台列表"""
        return self.publisher_factory.get_supported_platforms()
        
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.db_service.get_task_by_id(task_id)
        
    def get_publish_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取发布历史"""
        return self.db_service.get_publish_records(limit=limit)
        
    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取统计信息"""
        return self.db_service.get_task_statistics(days)

    async def _execute_publish_workflow(self, publisher, video_path: str, metadata: VideoMetadata, platform: str):
        """执行发布流程的适配器方法"""
        try:
            # 检查发布器类型
            from .platform_publisher.selenium_publisher_base import SeleniumPublisherBase
            from .platform_publisher.base_publisher import BasePublisher
            from .platform_publisher.youtube_publisher_manager import YouTubePublisherManager

            # 特殊处理YouTube平台
            if isinstance(publisher, YouTubePublisherManager):
                logger.info(f"使用YouTube增强发布器发布到 {platform}")

                # 准备YouTube视频信息
                video_info = {
                    'video_path': video_path,
                    'title': metadata.title,
                    'description': metadata.description,
                    'tags': metadata.tags,
                    'privacy': 'public',  # 默认公开
                    'cover_path': metadata.cover_path
                }

                # 调用YouTube发布器管理器
                result = await publisher.publish_video(video_info)

                # 转换结果格式
                from .platform_publisher.base_publisher import PublishResult, PublishStatus

                if result.get('success'):
                    return PublishResult(
                        success=True,
                        platform=platform,
                        video_id=result.get('video_id', ''),
                        video_url=result.get('video_url', ''),
                        status=PublishStatus.PUBLISHED,
                        message=result.get('message', 'YouTube发布成功'),
                        raw_response=result
                    )
                else:
                    return PublishResult(
                        success=False,
                        platform=platform,
                        status=PublishStatus.FAILED,
                        error_message=result.get('error', 'YouTube发布失败'),
                        raw_response=result
                    )

            elif isinstance(publisher, SeleniumPublisherBase):
                # Selenium发布器
                logger.info(f"使用Selenium发布器发布到 {platform}")

                # 准备视频信息
                video_info = {
                    'video_path': video_path,
                    'title': metadata.title,
                    'description': metadata.description,
                    'tags': metadata.tags,
                    'auto_publish': True  # 启用自动发布
                }

                # 调用Selenium发布器的发布方法
                result = await publisher.publish_video(video_info)

                # 转换结果格式以匹配期望的PublishResult
                from .platform_publisher.base_publisher import PublishResult, PublishStatus

                if result.get('success'):
                    return PublishResult(
                        success=True,
                        platform=platform,
                        video_id=result.get('video_id', f"{platform}_{int(time.time())}"),
                        video_url=result.get('video_url', ''),
                        status=PublishStatus.PUBLISHED,
                        message=result.get('message', '发布成功'),
                        raw_response=result
                    )
                else:
                    return PublishResult(
                        success=False,
                        platform=platform,
                        status=PublishStatus.FAILED,
                        error_message=result.get('error', '发布失败'),
                        raw_response=result
                    )

            elif isinstance(publisher, BasePublisher):
                # 标准发布器
                logger.info(f"使用标准发布器发布到 {platform}")
                return await publisher.full_publish_workflow(video_path, metadata)

            else:
                # 未知类型
                logger.error(f"未知的发布器类型: {type(publisher)}")
                from .platform_publisher.base_publisher import PublishResult, PublishStatus
                return PublishResult(
                    success=False,
                    platform=platform,
                    status=PublishStatus.FAILED,
                    error_message="不支持的发布器类型"
                )

        except Exception as e:
            logger.error(f"执行发布流程失败: {e}")
            from .platform_publisher.base_publisher import PublishResult, PublishStatus
            return PublishResult(
                success=False,
                platform=platform,
                status=PublishStatus.FAILED,
                error_message=str(e)
            )
