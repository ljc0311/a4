# -*- coding: utf-8 -*-
"""
发布器工厂类 - 基于Selenium的发布解决方案
"""

from typing import Dict, Any, Optional
from src.utils.logger import logger

# 导入Selenium发布器
try:
    from .selenium_douyin_publisher import SeleniumDouyinPublisher
    from .selenium_bilibili_publisher import SeleniumBilibiliPublisher
    from .selenium_kuaishou_publisher import SeleniumKuaishouPublisher
    from .selenium_xiaohongshu_publisher import SeleniumXiaohongshuPublisher
    from .selenium_wechat_publisher import SeleniumWechatPublisher
    from .selenium_youtube_publisher import SeleniumYoutubePublisher
    from .selenium_publisher_factory import selenium_publisher_manager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    SeleniumDouyinPublisher = None
    SeleniumBilibiliPublisher = None
    SeleniumKuaishouPublisher = None
    SeleniumXiaohongshuPublisher = None
    SeleniumWechatPublisher = None
    SeleniumYoutubePublisher = None
    selenium_publisher_manager = None


class PublisherFactory:
    """发布器工厂类 - 基于Selenium的发布解决方案"""
    
    # Selenium发布器映射
    SELENIUM_PUBLISHERS = {}
    
    @classmethod
    def create_publisher(cls, platform: str, config: Optional[Dict[str, Any]] = None):
        """
        创建指定平台的发布器实例
        
        Args:
            platform: 平台名称
            config: 配置参数
            
        Returns:
            发布器实例或None
        """
        # 初始化平台映射
        if not cls.SELENIUM_PUBLISHERS:
            cls._init_platform_publishers()
        
        platform_lower = platform.lower()
        
        # 使用Selenium发布器
        if platform_lower in cls.SELENIUM_PUBLISHERS:
            publisher_class = cls.SELENIUM_PUBLISHERS[platform_lower]
            try:
                # 默认配置，启用模拟模式避免Chrome启动问题
                default_config = {
                    'simulation_mode': True,  # 默认启用模拟模式
                    'headless': True,
                    'timeout': 30
                }
                # 合并用户配置
                final_config = {**default_config, **(config or {})}

                logger.info(f"创建 {platform} 发布器成功")
                return publisher_class(final_config)
            except Exception as e:
                logger.error(f"创建Selenium发布器失败 {platform}: {e}")
                return None
        
        logger.warning(f"不支持的平台: {platform}")
        return None
    
    @classmethod
    def _init_platform_publishers(cls):
        """初始化平台发布器映射"""
        # 使用Selenium发布器
        if SELENIUM_AVAILABLE:
            cls.SELENIUM_PUBLISHERS.update({
                'douyin': SeleniumDouyinPublisher,
                '抖音': SeleniumDouyinPublisher,
                'tiktok': SeleniumDouyinPublisher,
                'bilibili': SeleniumBilibiliPublisher,
                'b站': SeleniumBilibiliPublisher,
                'kuaishou': SeleniumKuaishouPublisher,
                '快手': SeleniumKuaishouPublisher,
                'xiaohongshu': SeleniumXiaohongshuPublisher,
                '小红书': SeleniumXiaohongshuPublisher,
                'wechat': SeleniumWechatPublisher,
                '微信视频号': SeleniumWechatPublisher,
                'wechat_channels': SeleniumWechatPublisher,
                'youtube': SeleniumYoutubePublisher,
                'youtube_shorts': SeleniumYoutubePublisher,
            })
    
    @classmethod
    def get_supported_platforms(cls) -> list:
        """获取支持的平台列表"""
        if not cls.SELENIUM_PUBLISHERS:
            cls._init_platform_publishers()
        return list(cls.SELENIUM_PUBLISHERS.keys())
    
    @classmethod
    async def publish_with_selenium(cls, platform: str, video_info: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        使用Selenium发布器发布视频
        
        Args:
            platform: 平台名称
            video_info: 视频信息
            config: 配置参数
            
        Returns:
            发布结果
        """
        if not SELENIUM_AVAILABLE:
            return {'success': False, 'error': 'Selenium发布器不可用'}
        
        try:
            return await selenium_publisher_manager.publish_video(platform, video_info)
        except Exception as e:
            logger.error(f"Selenium发布失败 {platform}: {e}")
            return {'success': False, 'error': str(e)}
    
    @classmethod
    async def publish_to_multiple_platforms(cls, platforms: list, video_info: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发布到多个平台
        
        Args:
            platforms: 平台列表
            video_info: 视频信息
            config: 配置参数
            
        Returns:
            发布结果
        """
        if not SELENIUM_AVAILABLE:
            return {'success': False, 'error': 'Selenium发布器不可用'}
        
        try:
            return await selenium_publisher_manager.publish_to_multiple_platforms(platforms, video_info)
        except Exception as e:
            logger.error(f"多平台发布失败: {e}")
            return {'success': False, 'error': str(e)}


# 向后兼容的别名
create_publisher = PublisherFactory.create_publisher
get_supported_platforms = PublisherFactory.get_supported_platforms
