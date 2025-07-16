#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MoneyPrinterPlus风格的发布管理器
统一管理所有平台的发布功能
"""

import time
from typing import Dict, Any, List
from pathlib import Path

from .moneyprinter_kuaishou_publisher import MoneyPrinterKuaishouPublisher
from .moneyprinter_xiaohongshu_publisher import MoneyPrinterXiaohongshuPublisher
from .selenium_douyin_publisher import SeleniumDouyinPublisher  # 抖音已经优化过了
from src.utils.logger import logger


class MoneyPrinterPublisherManager:
    """MoneyPrinterPlus风格的发布管理器"""
    
    def __init__(self):
        self.publishers = {}
        self.config = {
            'driver_type': 'chrome',
            'debugger_address': '127.0.0.1:9222',
            'timeout': 30,
            'headless': False,
            'simulation_mode': False
        }
    
    def initialize_publishers(self, platforms: List[str]) -> bool:
        """初始化指定平台的发布器"""
        try:
            logger.info("初始化MoneyPrinterPlus风格发布器...")
            
            publisher_classes = {
                'douyin': SeleniumDouyinPublisher,
                'kuaishou': MoneyPrinterKuaishouPublisher,
                'xiaohongshu': MoneyPrinterXiaohongshuPublisher
            }
            
            success_count = 0
            for platform in platforms:
                if platform in publisher_classes:
                    try:
                        publisher_class = publisher_classes[platform]
                        publisher = publisher_class(self.config)
                        
                        if publisher.initialize():
                            self.publishers[platform] = publisher
                            success_count += 1
                            logger.info(f"✅ {platform} 发布器初始化成功")
                        else:
                            logger.error(f"❌ {platform} 发布器初始化失败")
                    except Exception as e:
                        logger.error(f"❌ {platform} 发布器创建失败: {e}")
                else:
                    logger.warning(f"⚠️  不支持的平台: {platform}")
            
            logger.info(f"发布器初始化完成，成功: {success_count}/{len(platforms)}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"初始化发布器失败: {e}")
            return False
    
    def publish_to_all_platforms(self, video_path: str, title: str, description: str, 
                                tags: List[str] = None, platforms: List[str] = None) -> Dict[str, bool]:
        """发布到所有平台 - MoneyPrinterPlus风格"""
        try:
            logger.info("开始MoneyPrinterPlus风格的多平台发布...")
            
            # 验证视频文件
            if not Path(video_path).exists():
                logger.error(f"视频文件不存在: {video_path}")
                return {}
            
            # 确定要发布的平台
            target_platforms = platforms or list(self.publishers.keys())
            results = {}
            
            # 显示发布信息
            logger.info("=" * 60)
            logger.info("📹 视频信息:")
            logger.info(f"   文件: {video_path}")
            logger.info(f"   标题: {title}")
            logger.info(f"   描述: {description[:100]}...")
            logger.info(f"   标签: {tags}")
            logger.info(f"   平台: {target_platforms}")
            logger.info("=" * 60)
            
            # 逐个平台发布
            for platform in target_platforms:
                if platform not in self.publishers:
                    logger.warning(f"⚠️  平台 {platform} 未初始化，跳过")
                    results[platform] = False
                    continue
                
                logger.info(f"\n🚀 开始发布到 {platform}...")
                
                try:
                    publisher = self.publishers[platform]
                    
                    # 根据平台类型调用不同的发布方法
                    if hasattr(publisher, 'publish_video'):
                        # MoneyPrinterPlus风格的发布器
                        success = publisher.publish_video(video_path, title, description, tags)
                    else:
                        # 传统发布器（如抖音）
                        success = publisher.publish(video_path, title, description, tags)
                    
                    results[platform] = success
                    
                    if success:
                        logger.info(f"✅ {platform} 发布成功！")
                    else:
                        logger.error(f"❌ {platform} 发布失败！")
                    
                    # 平台间间隔
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ {platform} 发布异常: {e}")
                    results[platform] = False
            
            # 显示发布结果
            self.show_publish_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"多平台发布失败: {e}")
            return {}
    
    def show_publish_results(self, results: Dict[str, bool]):
        """显示发布结果"""
        try:
            logger.info("\n" + "=" * 60)
            logger.info("📊 发布结果汇总:")
            logger.info("=" * 60)
            
            success_count = 0
            total_count = len(results)
            
            for platform, success in results.items():
                status = "✅ 成功" if success else "❌ 失败"
                logger.info(f"   {platform.ljust(10)}: {status}")
                if success:
                    success_count += 1
            
            logger.info("=" * 60)
            logger.info(f"📈 总体结果: {success_count}/{total_count} 平台发布成功")
            
            if success_count == total_count:
                logger.info("🎉 所有平台发布成功！")
            elif success_count > 0:
                logger.info("⚠️  部分平台发布成功")
            else:
                logger.error("❌ 所有平台发布失败")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"显示发布结果失败: {e}")
    
    def check_all_login_status(self) -> Dict[str, bool]:
        """检查所有平台的登录状态"""
        try:
            logger.info("检查所有平台登录状态...")
            results = {}
            
            for platform, publisher in self.publishers.items():
                try:
                    if hasattr(publisher, 'check_login_status'):
                        status = publisher.check_login_status()
                    else:
                        # 对于传统发布器，使用异步方法
                        import asyncio
                        status = asyncio.run(publisher._check_login_status())
                    
                    results[platform] = status
                    status_text = "✅ 已登录" if status else "❌ 未登录"
                    logger.info(f"   {platform.ljust(10)}: {status_text}")
                    
                except Exception as e:
                    logger.error(f"检查 {platform} 登录状态失败: {e}")
                    results[platform] = False
            
            return results
            
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return {}
    
    def get_platform_urls(self) -> Dict[str, str]:
        """获取各平台的上传页面URL"""
        return {
            'douyin': 'https://creator.douyin.com/creator-micro/content/upload',
            'kuaishou': 'https://cp.kuaishou.com/article/publish/video',
            'xiaohongshu': 'https://creator.xiaohongshu.com/publish/publish',
            'bilibili': 'https://member.bilibili.com/platform/upload/video/frame',
            'weixin': 'https://channels.weixin.qq.com/platform/post/create'
        }
    
    def show_login_instructions(self):
        """显示登录指导"""
        logger.info("\n" + "=" * 60)
        logger.info("📋 MoneyPrinterPlus风格发布使用指南:")
        logger.info("=" * 60)
        logger.info("1. 确保Chrome以调试模式启动:")
        logger.info("   chrome.exe --remote-debugging-port=9222 --user-data-dir=selenium")
        logger.info("")
        logger.info("2. 在Chrome中手动登录以下平台:")
        
        urls = self.get_platform_urls()
        for platform, url in urls.items():
            if platform in self.publishers:
                logger.info(f"   {platform.ljust(10)}: {url}")
        
        logger.info("")
        logger.info("3. 登录完成后，运行发布程序")
        logger.info("4. 程序会自动检测登录状态并进行发布")
        logger.info("=" * 60)
    
    def cleanup(self):
        """清理所有发布器"""
        try:
            logger.info("清理发布器资源...")
            for platform, publisher in self.publishers.items():
                try:
                    if hasattr(publisher, 'cleanup'):
                        publisher.cleanup()
                except Exception as e:
                    logger.debug(f"清理 {platform} 发布器失败: {e}")
            
            self.publishers.clear()
            logger.info("✅ 发布器资源清理完成")
            
        except Exception as e:
            logger.error(f"清理发布器失败: {e}")


# 便捷函数
def create_moneyprinter_publisher(platforms: List[str] = None) -> MoneyPrinterPublisherManager:
    """创建MoneyPrinterPlus风格的发布管理器"""
    if platforms is None:
        platforms = ['douyin', 'kuaishou', 'xiaohongshu']
    
    manager = MoneyPrinterPublisherManager()
    
    if manager.initialize_publishers(platforms):
        return manager
    else:
        logger.error("发布管理器初始化失败")
        return None


def quick_publish(video_path: str, title: str, description: str, 
                 tags: List[str] = None, platforms: List[str] = None) -> Dict[str, bool]:
    """快速发布到多个平台"""
    manager = create_moneyprinter_publisher(platforms)
    if manager:
        try:
            results = manager.publish_to_all_platforms(video_path, title, description, tags, platforms)
            return results
        finally:
            manager.cleanup()
    return {}
