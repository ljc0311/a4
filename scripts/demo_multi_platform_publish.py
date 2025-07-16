#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多平台发布功能演示脚本
展示一键发布到多个平台的完整流程
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.platform_publisher.selenium_publisher_factory import SeleniumPublisherFactory
from src.services.platform_publisher.base_publisher import VideoMetadata
from src.utils.logger import logger


class MultiPlatformPublishDemo:
    """多平台发布演示器"""
    
    def __init__(self):
        self.supported_platforms = SeleniumPublisherFactory.SUPPORTED_PLATFORMS.keys()
        
    async def run_demo(self):
        """运行演示"""
        print("🚀 多平台发布功能演示")
        print("=" * 60)
        
        # 显示支持的平台
        self._show_supported_platforms()
        
        # 创建演示视频元数据
        metadata = self._create_demo_metadata()
        
        # 创建临时视频文件
        demo_video_path = self._create_demo_video()
        
        try:
            # 演示模拟发布到所有平台
            await self._demo_multi_platform_publish(demo_video_path, metadata)
            
        finally:
            # 清理临时文件
            if os.path.exists(demo_video_path):
                os.unlink(demo_video_path)
    
    def _show_supported_platforms(self):
        """显示支持的平台"""
        print(f"📱 支持的发布平台 ({len(self.supported_platforms)}个):")
        
        platform_info = {
            'douyin': {'name': '抖音', 'icon': '🎵', 'url': 'https://creator.douyin.com'},
            'kuaishou': {'name': '快手', 'icon': '⚡', 'url': 'https://cp.kuaishou.com'},
            'xiaohongshu': {'name': '小红书', 'icon': '📖', 'url': 'https://creator.xiaohongshu.com'},
            'bilibili': {'name': 'B站', 'icon': '📺', 'url': 'https://member.bilibili.com'},
            'wechat': {'name': '微信视频号', 'icon': '💬', 'url': 'https://channels.weixin.qq.com'},
            'youtube': {'name': 'YouTube Shorts', 'icon': '🎬', 'url': 'https://studio.youtube.com'}
        }
        
        for platform in self.supported_platforms:
            info = platform_info.get(platform, {'name': platform, 'icon': '📱', 'url': 'N/A'})
            print(f"  {info['icon']} {info['name']} ({platform})")
            print(f"     URL: {info['url']}")
        
        print()
    
    def _create_demo_metadata(self) -> VideoMetadata:
        """创建演示视频元数据"""
        print("📋 创建演示视频元数据...")
        
        metadata = VideoMetadata(
            title="AI视频生成器演示 - 多平台发布测试",
            description="""这是一个AI视频生成器的多平台发布功能演示。

🚀 主要功能：
• 一键发布到6个主流平台
• AI智能内容优化
• 自动适配平台特性
• 完整的发布流程管理

#AI视频 #多平台发布 #自动化""",
            tags=["AI视频", "多平台发布", "自动化", "演示", "测试"],
            cover_path=None
        )
        
        print(f"✅ 标题: {metadata.title}")
        print(f"✅ 描述长度: {len(metadata.description)}字符")
        print(f"✅ 标签: {metadata.tags}")
        print()
        
        return metadata
    
    def _create_demo_video(self) -> str:
        """创建演示视频文件"""
        print("🎬 创建演示视频文件...")
        
        # 创建临时视频文件
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            # 写入模拟视频内容
            temp_file.write(b'DEMO VIDEO CONTENT - This is a fake video file for demonstration purposes.')
            demo_video_path = temp_file.name
        
        print(f"✅ 演示视频文件: {demo_video_path}")
        print()
        
        return demo_video_path
    
    async def _demo_multi_platform_publish(self, video_path: str, metadata: VideoMetadata):
        """演示多平台发布"""
        print("🎯 开始多平台发布演示...")
        print("⚠️ 注意：这是模拟模式演示，不会实际发布视频")
        print()
        
        # 配置模拟模式
        config = {
            'selenium': {
                'driver_type': 'chrome',
                'headless': True,
                'simulation_mode': True,  # 启用模拟模式
                'timeout': 30
            }
        }
        
        results = {}
        
        # 逐个平台演示发布
        for platform in self.supported_platforms:
            print(f"📤 正在发布到 {platform}...")
            
            try:
                # 创建平台发布器
                publisher = SeleniumPublisherFactory.create_publisher(platform, config)
                
                # 准备平台特定的视频信息
                video_info = self._prepare_platform_video_info(platform, video_path, metadata)
                
                # 模拟发布
                result = await publisher._publish_video_impl(video_info)
                results[platform] = result
                
                if result.get('success'):
                    print(f"  ✅ {platform} 发布成功")
                else:
                    print(f"  ❌ {platform} 发布失败: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                print(f"  ❌ {platform} 发布异常: {e}")
                results[platform] = {'success': False, 'error': str(e)}
            
            print()
        
        # 显示发布结果统计
        self._show_publish_results(results)
    
    def _prepare_platform_video_info(self, platform: str, video_path: str, metadata: VideoMetadata) -> dict:
        """为特定平台准备视频信息"""
        # 基础视频信息
        video_info = {
            'video_path': video_path,
            'title': metadata.title,
            'description': metadata.description,
            'tags': metadata.tags,
            'cover_path': metadata.cover_path
        }
        
        # 平台特定优化
        if platform == 'douyin':
            # 抖音：标题限制55字符
            video_info['title'] = metadata.title[:55]
            video_info['description'] = metadata.description[:2200]
            
        elif platform == 'kuaishou':
            # 快手：标题限制50字符，支持领域设置
            video_info['title'] = metadata.title[:50]
            video_info['description'] = metadata.description[:1000]
            video_info['domain'] = '科技'
            
        elif platform == 'xiaohongshu':
            # 小红书：标题限制100字符，支持话题和地点
            video_info['title'] = metadata.title[:100]
            video_info['description'] = metadata.description[:1000]
            video_info['topic'] = 'AI科技'
            video_info['location'] = '北京'
            
        elif platform == 'wechat':
            # 微信视频号：标题限制30字符
            video_info['title'] = metadata.title[:30]
            video_info['description'] = metadata.description[:600]
            video_info['visibility'] = 'public'
            
        elif platform == 'youtube':
            # YouTube：支持更长的描述，自动添加#Shorts
            video_info['title'] = metadata.title[:100]
            video_info['description'] = f"{metadata.description}\n\n#Shorts"[:5000]
            video_info['visibility'] = 'public'
            
        elif platform == 'bilibili':
            # B站：需要分区设置
            video_info['title'] = metadata.title[:80]
            video_info['description'] = metadata.description[:2000]
            video_info['category'] = '科技'
        
        return video_info
    
    def _show_publish_results(self, results: dict):
        """显示发布结果"""
        print("📊 发布结果统计:")
        print("-" * 40)
        
        success_count = 0
        failed_count = 0
        
        for platform, result in results.items():
            status = "✅ 成功" if result.get('success') else "❌ 失败"
            print(f"  {platform:12} {status}")
            
            if result.get('success'):
                success_count += 1
            else:
                failed_count += 1
        
        print("-" * 40)
        print(f"总计: {len(results)}个平台")
        print(f"成功: {success_count}个")
        print(f"失败: {failed_count}个")
        print(f"成功率: {success_count/len(results)*100:.1f}%")
        
        print("\n💡 实际使用说明:")
        print("1. 关闭模拟模式 (simulation_mode=False)")
        print("2. 确保Chrome浏览器和ChromeDriver已安装")
        print("3. 手动登录各平台账号")
        print("4. 准备真实的视频文件")
        print("5. 运行一键发布功能")


async def main():
    """主函数"""
    demo = MultiPlatformPublishDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
