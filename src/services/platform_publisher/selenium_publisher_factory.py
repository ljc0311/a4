#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Selenium的发布器工厂
参考MoneyPrinterPlus的设计，提供更稳定的发布解决方案
"""

from typing import Dict, Any, Optional
from .selenium_publisher_base import SeleniumPublisherBase
from .selenium_douyin_publisher import SeleniumDouyinPublisher
from .selenium_bilibili_publisher import SeleniumBilibiliPublisher
from .selenium_kuaishou_publisher import SeleniumKuaishouPublisher
from .selenium_xiaohongshu_publisher import SeleniumXiaohongshuPublisher
from .selenium_wechat_publisher import SeleniumWechatPublisher
from .selenium_youtube_publisher import SeleniumYoutubePublisher
from src.utils.logger import logger


class SeleniumPublisherFactory:
    """基于Selenium的发布器工厂"""
    
    # 支持的平台
    SUPPORTED_PLATFORMS = {
        'douyin': SeleniumDouyinPublisher,
        'bilibili': SeleniumBilibiliPublisher,
        'kuaishou': SeleniumKuaishouPublisher,
        'xiaohongshu': SeleniumXiaohongshuPublisher,
        'wechat': SeleniumWechatPublisher,
        'youtube': SeleniumYoutubePublisher,
        # 可以继续添加其他平台
    }
    
    @classmethod
    def create_publisher(cls, platform: str, config: Dict[str, Any] = None) -> Optional[SeleniumPublisherBase]:
        """创建发布器实例"""
        try:
            if platform not in cls.SUPPORTED_PLATFORMS:
                logger.error(f"不支持的平台: {platform}")
                return None
                
            publisher_class = cls.SUPPORTED_PLATFORMS[platform]
            
            # 默认配置
            default_config = {
                'driver_type': 'chrome',
                'debugger_address': '127.0.0.1:9222',
                'timeout': 30,
                'implicit_wait': 10,
                'headless': False,
                'simulation_mode': False  # 默认不启用模拟模式
            }
            
            # 合并配置
            final_config = {**default_config, **(config or {})}
            
            # 创建发布器实例
            publisher = publisher_class(final_config)
            
            logger.info(f"创建 {platform} 发布器成功")
            return publisher
            
        except Exception as e:
            logger.error(f"创建 {platform} 发布器失败: {e}")
            return None
            
    @classmethod
    def get_supported_platforms(cls) -> list:
        """获取支持的平台列表"""
        return list(cls.SUPPORTED_PLATFORMS.keys())
        
    @classmethod
    def is_platform_supported(cls, platform: str) -> bool:
        """检查平台是否支持"""
        return platform in cls.SUPPORTED_PLATFORMS


class SeleniumPublisherManager:
    """Selenium发布器管理器"""
    
    def __init__(self):
        self.publishers: Dict[str, SeleniumPublisherBase] = {}
        self.config = {
            'driver_type': 'chrome',
            'debugger_address': '127.0.0.1:9222',
            'timeout': 30,
            'implicit_wait': 10,
            'headless': False
        }
        
    def set_config(self, config: Dict[str, Any]):
        """设置全局配置"""
        self.config.update(config)
        
    async def get_publisher(self, platform: str) -> Optional[SeleniumPublisherBase]:
        """获取发布器实例（单例模式）"""
        try:
            if platform not in self.publishers:
                publisher = SeleniumPublisherFactory.create_publisher(platform, self.config)
                if publisher:
                    # 初始化发布器（同步方法）
                    if publisher.initialize():
                        self.publishers[platform] = publisher
                    else:
                        logger.error(f"{platform} 发布器初始化失败")
                        return None
                else:
                    return None

            return self.publishers[platform]

        except Exception as e:
            logger.error(f"获取 {platform} 发布器失败: {e}")
            return None
            
    async def authenticate_platform(self, platform: str, credentials: Dict[str, Any] = None) -> bool:
        """认证平台"""
        try:
            publisher = await self.get_publisher(platform)
            if not publisher:
                return False
                
            return await publisher.authenticate(credentials or {})
            
        except Exception as e:
            logger.error(f"{platform} 认证失败: {e}")
            return False
            
    async def publish_video(self, platform: str, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """发布视频到指定平台"""
        try:
            publisher = await self.get_publisher(platform)
            if not publisher:
                return {'success': False, 'error': f'{platform} 发布器获取失败'}
                
            # 检查认证状态
            if not publisher.is_authenticated:
                logger.warning(f"{platform} 未认证，尝试自动认证...")
                if not await publisher.authenticate({}):
                    return {'success': False, 'error': f'{platform} 认证失败'}
                    
            # 发布视频
            return await publisher.publish_video(video_info)
            
        except Exception as e:
            logger.error(f"发布视频到 {platform} 失败: {e}")
            return {'success': False, 'error': str(e)}
            
    async def publish_to_multiple_platforms(self, platforms: list, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """发布视频到多个平台"""
        results = {}
        
        for platform in platforms:
            try:
                logger.info(f"开始发布到 {platform}...")
                result = await self.publish_video(platform, video_info)
                results[platform] = result
                
                if result.get('success'):
                    logger.info(f"{platform} 发布成功")
                else:
                    logger.error(f"{platform} 发布失败: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"发布到 {platform} 异常: {e}")
                results[platform] = {'success': False, 'error': str(e)}
                
        return results
        
    async def cleanup_all(self):
        """清理所有发布器"""
        for platform, publisher in self.publishers.items():
            try:
                await publisher.cleanup()
                logger.info(f"{platform} 发布器清理完成")
            except Exception as e:
                logger.error(f"{platform} 发布器清理失败: {e}")
                
        self.publishers.clear()
        
    def get_platform_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有平台状态"""
        status = {}
        
        for platform, publisher in self.publishers.items():
            status[platform] = {
                'initialized': True,
                'authenticated': publisher.is_authenticated,
                'driver_type': publisher.selenium_config.get('driver_type'),
                'debugger_address': publisher.selenium_config.get('debugger_address')
            }
            
        # 添加未初始化的平台
        for platform in SeleniumPublisherFactory.get_supported_platforms():
            if platform not in status:
                status[platform] = {
                    'initialized': False,
                    'authenticated': False,
                    'driver_type': self.config.get('driver_type'),
                    'debugger_address': self.config.get('debugger_address')
                }
                
        return status


# 全局发布器管理器实例
selenium_publisher_manager = SeleniumPublisherManager()


# 便捷函数
async def create_selenium_publisher(platform: str, config: Dict[str, Any] = None) -> Optional[SeleniumPublisherBase]:
    """创建Selenium发布器的便捷函数"""
    return SeleniumPublisherFactory.create_publisher(platform, config)


async def publish_video_selenium(platform: str, video_info: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """使用Selenium发布视频的便捷函数"""
    if config:
        selenium_publisher_manager.set_config(config)
        
    return await selenium_publisher_manager.publish_video(platform, video_info)


async def publish_to_multiple_platforms_selenium(platforms: list, video_info: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """使用Selenium发布到多个平台的便捷函数"""
    if config:
        selenium_publisher_manager.set_config(config)
        
    return await selenium_publisher_manager.publish_to_multiple_platforms(platforms, video_info)


def get_selenium_supported_platforms() -> list:
    """获取Selenium支持的平台列表"""
    return SeleniumPublisherFactory.get_supported_platforms()


async def get_selenium_platform_status() -> Dict[str, Dict[str, Any]]:
    """获取Selenium平台状态"""
    return selenium_publisher_manager.get_platform_status()
