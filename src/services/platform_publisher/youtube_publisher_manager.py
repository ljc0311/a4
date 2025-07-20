#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube发布器管理器
整合API和Selenium两种发布方案，提供最佳的发布体验
"""

import os
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from .youtube_api_publisher import YouTubeAPIPublisher
from .youtube_stealth_publisher import YouTubeStealthPublisher
from .youtube_platform_optimizer import youtube_optimizer
from src.utils.logger import logger

class YouTubePublisherManager:
    """YouTube发布器管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.api_publisher = None
        self.selenium_publisher = None
        
        # 加载配置
        self._load_config()
        
        # 初始化发布器
        self._init_publishers()
    
    def _load_config(self):
        """加载配置"""
        try:
            # 尝试加载用户配置
            config_file = Path('config/youtube_config.py')
            if config_file.exists():
                import sys
                sys.path.insert(0, str(config_file.parent))
                from youtube_config import get_youtube_config
                self.config = get_youtube_config()
                logger.info("✅ 加载用户YouTube配置成功")
            else:
                # 使用默认配置
                from config.youtube_config_example import get_youtube_config
                self.config = get_youtube_config()
                logger.info("📋 使用默认YouTube配置")
                
        except Exception as e:
            logger.warning(f"⚠️ 加载YouTube配置失败: {e}")
            # 使用最小配置
            self.config = {
                'api': {'enabled': False},
                'selenium': {'enabled': True, 'stealth_mode': True}
            }
    
    def _init_publishers(self):
        """初始化发布器"""
        try:
            # 初始化API发布器
            if self.config.get('api', {}).get('enabled', False):
                self.api_publisher = YouTubeAPIPublisher(self.config['api'])
                logger.info("🔑 YouTube API发布器已初始化")
            
            # 初始化Selenium发布器
            if self.config.get('selenium', {}).get('enabled', True):
                self.selenium_publisher = YouTubeStealthPublisher(self.config['selenium'])
                logger.info("🌐 YouTube Selenium发布器已初始化")
                
        except Exception as e:
            logger.error(f"❌ 初始化YouTube发布器失败: {e}")
    
    async def publish_video(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        发布视频到YouTube
        优先使用API，失败时回退到Selenium
        """
        try:
            logger.info("🚀 开始YouTube视频发布...")

            # YouTube平台特征性优化
            optimized_info = youtube_optimizer.optimize_video_info(video_info)

            # 预处理视频信息
            processed_info = self._preprocess_video_info(optimized_info)
            
            # 方案1: 尝试API发布（推荐）
            if self.api_publisher and self.config.get('api', {}).get('enabled', False):
                logger.info("🔑 尝试使用YouTube API发布...")
                
                try:
                    result = await self.api_publisher.upload_video(processed_info)
                    if result.get('success'):
                        logger.info("✅ YouTube API发布成功!")
                        return result
                    else:
                        logger.warning(f"⚠️ YouTube API发布失败: {result.get('error')}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ YouTube API发布异常: {e}")
            
            # 方案2: 回退到Selenium发布（Chrome）
            if self.selenium_publisher and self.config.get('selenium', {}).get('enabled', True):
                logger.info("🌐 回退到Selenium发布（Chrome）...")

                try:
                    # 检查是否需要初始化Selenium
                    if not self.selenium_publisher.driver:
                        if not self.selenium_publisher.initialize():
                            return {'success': False, 'error': 'Selenium初始化失败'}

                    result = await self.selenium_publisher.upload_video(processed_info)
                    if result.get('success'):
                        logger.info("✅ YouTube Selenium发布成功!")
                        return result
                    else:
                        logger.error(f"❌ YouTube Selenium发布失败: {result.get('error')}")
                        return result

                except Exception as e:
                    logger.error(f"❌ YouTube Selenium发布异常: {e}")
                    return {'success': False, 'error': f'Selenium发布异常: {e}'}
            
            # 所有方案都失败
            return {
                'success': False, 
                'error': '所有YouTube发布方案都失败，请检查配置和网络连接'
            }
            
        except Exception as e:
            logger.error(f"❌ YouTube发布管理器异常: {e}")
            return {'success': False, 'error': f'发布管理器异常: {e}'}
    
    def _preprocess_video_info(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """预处理视频信息"""
        try:
            processed = video_info.copy()
            content_config = self.config.get('content', {})
            
            # 处理标题
            title = processed.get('title', '未命名视频')
            max_title_length = content_config.get('title_max_length', 100)
            processed['title'] = title[:max_title_length]
            
            # 处理描述
            description = processed.get('description', '')
            description_template = content_config.get('description_template', '{description}')
            processed['description'] = description_template.format(description=description)
            
            max_desc_length = content_config.get('description_max_length', 5000)
            processed['description'] = processed['description'][:max_desc_length]
            
            # 处理标签
            tags = processed.get('tags', [])
            default_tags = content_config.get('default_tags', [])
            all_tags = list(set(tags + default_tags))  # 去重
            max_tags = content_config.get('tags_max_count', 15)
            processed['tags'] = all_tags[:max_tags]
            
            # 检测Shorts
            if self._is_shorts_video(processed.get('video_path', '')):
                processed = self._apply_shorts_settings(processed)
            
            # 设置默认隐私级别
            if 'privacy' not in processed:
                processed['privacy'] = self.config.get('api', {}).get('default_privacy', 'public')
            
            return processed
            
        except Exception as e:
            logger.warning(f"⚠️ 预处理视频信息失败: {e}")
            return video_info
    
    def _is_shorts_video(self, video_path: str) -> bool:
        """检测是否为Shorts视频"""
        try:
            if not video_path or not os.path.exists(video_path):
                return False
            
            # 使用ffprobe检测视频时长
            import subprocess
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_entries', 
                'format=duration', '-of', 'csv=p=0', video_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                shorts_max_duration = self.config.get('content', {}).get('shorts_max_duration', 60)
                return duration <= shorts_max_duration
            
        except Exception as e:
            logger.debug(f"检测Shorts失败: {e}")
        
        return False
    
    def _apply_shorts_settings(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """应用Shorts设置"""
        try:
            content_config = self.config.get('content', {})
            
            # 添加Shorts标题后缀
            title_suffix = content_config.get('shorts_title_suffix', ' #Shorts')
            if not video_info['title'].endswith(title_suffix):
                video_info['title'] += title_suffix
            
            # 添加Shorts描述后缀
            desc_suffix = content_config.get('shorts_description_suffix', '\n\n#Shorts')
            if desc_suffix not in video_info['description']:
                video_info['description'] += desc_suffix
            
            # 添加Shorts标签
            shorts_tags = content_config.get('shorts_tags', ['Shorts'])
            video_info['tags'].extend(shorts_tags)
            video_info['tags'] = list(set(video_info['tags']))  # 去重
            
            logger.info("🎬 已应用Shorts设置")
            
        except Exception as e:
            logger.warning(f"⚠️ 应用Shorts设置失败: {e}")
        
        return video_info
    
    async def get_channel_info(self) -> Dict[str, Any]:
        """获取频道信息"""
        try:
            if self.api_publisher:
                return await self.api_publisher.get_channel_info()
            else:
                return {'success': False, 'error': 'YouTube API未配置'}
                
        except Exception as e:
            logger.error(f"❌ 获取频道信息失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.selenium_publisher and hasattr(self.selenium_publisher, 'driver'):
                if self.selenium_publisher.driver:
                    self.selenium_publisher.driver.quit()
                    logger.info("🧹 Selenium资源已清理")
                    
        except Exception as e:
            logger.warning(f"⚠️ 清理资源失败: {e}")
    
    def __del__(self):
        """析构函数"""
        self.cleanup()
