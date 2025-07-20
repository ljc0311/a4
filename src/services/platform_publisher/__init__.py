# -*- coding: utf-8 -*-
"""
平台发布器模块
支持多平台视频发布功能
"""

from .publisher_factory import PublisherFactory

# 导入Selenium发布器
try:
    from .selenium_publisher_factory import SeleniumPublisherFactory, selenium_publisher_manager
    from .selenium_publisher_base import SeleniumPublisherBase
    from .selenium_douyin_publisher import SeleniumDouyinPublisher
    from .selenium_bilibili_publisher import SeleniumBilibiliPublisher
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    SeleniumPublisherFactory = None
    selenium_publisher_manager = None
    SeleniumPublisherBase = None
    SeleniumDouyinPublisher = None
    SeleniumBilibiliPublisher = None

__all__ = [
    'PublisherFactory'
]

# 如果Selenium发布器可用，添加到导出列表
if SELENIUM_AVAILABLE:
    __all__.extend([
        'SeleniumPublisherFactory',
        'selenium_publisher_manager',
        'SeleniumPublisherBase',
        'SeleniumDouyinPublisher',
        'SeleniumBilibiliPublisher'
    ])
