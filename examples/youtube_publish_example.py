#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube发布功能示例
演示如何使用集成的YouTube发布功能
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.platform_publisher.publisher_factory import PublisherFactory
from src.utils.logger import logger

async def youtube_publish_example():
    """YouTube发布示例"""
    try:
        print("🎬 YouTube发布功能示例")
        print("=" * 50)
        
        # 1. 准备视频信息
        video_info = {
            'video_path': 'path/to/your/video.mp4',  # 替换为实际视频路径
            'title': '🎬 精彩视频内容',
            'description': '''🎬 精彩视频内容

📖 视频亮点：
• 精彩的内容呈现
• 高质量的制作
• 引人入胜的故事情节

🔔 订阅频道获取更多内容
👍 点赞支持创作
💬 评论分享您的想法
🔗 分享给更多朋友

#Video #Content #Creative #Story #Entertainment''',
            'tags': ['Video', 'Content', 'Creative', 'Story', 'Entertainment', 'Quality'],
            'privacy': 'public',  # public, unlisted, private
            'category': '22'  # People & Blogs
        }
        
        # 检查视频文件是否存在
        if not os.path.exists(video_info['video_path']):
            print("❌ 视频文件不存在，请修改video_path为实际的视频文件路径")
            print("示例路径格式: 'output/final_video.mp4'")
            return
        
        # 2. 创建YouTube发布器
        print("🔧 创建YouTube发布器...")
        youtube_config = {
            'api': {
                'enabled': True,
                'credentials_file': 'config/youtube_credentials.json',
                'token_file': 'config/youtube_token.pickle'
            },
            'selenium': {
                'enabled': True,
                'headless': False,
                'timeout': 30
            }
        }
        
        publisher = PublisherFactory.create_publisher('youtube', youtube_config)
        if not publisher:
            print("❌ 无法创建YouTube发布器")
            return
        
        print("✅ YouTube发布器创建成功")
        
        # 3. 发布视频
        print("\n🚀 开始发布视频到YouTube...")
        print("注意：首次使用时会打开浏览器进行OAuth认证")
        
        result = await publisher.publish_video(video_info)
        
        # 4. 处理结果
        if result.get('success'):
            print("\n🎉 YouTube发布成功！")
            print(f"📺 视频ID: {result.get('video_id', 'N/A')}")
            print(f"🔗 视频链接: {result.get('video_url', 'N/A')}")
            print(f"📊 发布方式: {result.get('method', 'N/A')}")
            
            # 显示优化信息
            if 'optimization_info' in result:
                opt_info = result['optimization_info']
                print(f"\n✨ 平台优化信息:")
                print(f"   视频类型: {opt_info.get('video_type', 'N/A')}")
                print(f"   标题长度: {len(opt_info.get('optimized_title', ''))}")
                print(f"   标签数量: {len(opt_info.get('optimized_tags', []))}")
        else:
            print(f"\n❌ YouTube发布失败: {result.get('error', '未知错误')}")
            
            # 显示详细错误信息
            if 'details' in result:
                print(f"详细信息: {result['details']}")
        
    except Exception as e:
        logger.error(f"YouTube发布示例失败: {e}")
        print(f"❌ 示例运行失败: {e}")

async def youtube_shorts_example():
    """YouTube Shorts发布示例"""
    try:
        print("\n📱 YouTube Shorts发布示例")
        print("=" * 50)
        
        # Shorts视频信息
        shorts_info = {
            'video_path': 'path/to/your/shorts.mp4',  # 替换为实际Shorts视频路径
            'title': '🔥 AI生成的精彩Shorts内容 #Shorts',
            'description': '''🎬 AI生成的精彩短视频内容

🔔 订阅频道获取更多AI创作内容
👍 点赞支持我们的创作
💬 评论分享您的想法

#Shorts #AI #Technology #Innovation''',
            'tags': ['Shorts', 'AI', 'Technology', 'Quick', 'Viral'],
            'privacy': 'public'
        }
        
        # 检查视频文件
        if not os.path.exists(shorts_info['video_path']):
            print("❌ Shorts视频文件不存在，请修改video_path为实际的视频文件路径")
            return
        
        # 创建发布器并发布
        publisher = PublisherFactory.create_publisher('youtube_shorts')
        if publisher:
            result = await publisher.publish_video(shorts_info)
            
            if result.get('success'):
                print("🎉 YouTube Shorts发布成功！")
                print(f"📱 Shorts ID: {result.get('video_id', 'N/A')}")
                print(f"🔗 Shorts链接: {result.get('video_url', 'N/A')}")
            else:
                print(f"❌ YouTube Shorts发布失败: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ Shorts发布示例失败: {e}")

async def batch_youtube_publish_example():
    """批量YouTube发布示例"""
    try:
        print("\n📦 批量YouTube发布示例")
        print("=" * 50)
        
        # 批量视频信息
        video_list = [
            {
                'video_path': 'path/to/video1.mp4',
                'title': '🚀 AI视频系列 - 第1集',
                'description': '这是AI视频系列的第一集...',
                'tags': ['AI', 'Series', 'Episode1'],
                'privacy': 'public'
            },
            {
                'video_path': 'path/to/video2.mp4',
                'title': '🚀 AI视频系列 - 第2集',
                'description': '这是AI视频系列的第二集...',
                'tags': ['AI', 'Series', 'Episode2'],
                'privacy': 'public'
            }
        ]
        
        # 批量发布
        results = []
        for i, video_info in enumerate(video_list, 1):
            print(f"\n📹 发布第 {i} 个视频...")
            
            if not os.path.exists(video_info['video_path']):
                print(f"⚠️ 跳过第 {i} 个视频（文件不存在）")
                continue
            
            # 使用工厂方法发布
            result = await PublisherFactory.publish_to_youtube(video_info)
            results.append(result)
            
            if result.get('success'):
                print(f"✅ 第 {i} 个视频发布成功")
            else:
                print(f"❌ 第 {i} 个视频发布失败: {result.get('error')}")
            
            # 添加延迟避免API限制
            await asyncio.sleep(5)
        
        # 统计结果
        success_count = sum(1 for r in results if r.get('success'))
        print(f"\n📊 批量发布完成: {success_count}/{len(results)} 成功")
        
    except Exception as e:
        print(f"❌ 批量发布示例失败: {e}")

async def youtube_config_example():
    """YouTube配置示例"""
    try:
        print("\n⚙️ YouTube配置示例")
        print("=" * 50)
        
        # 显示当前配置
        from src.services.platform_publisher.youtube_platform_optimizer import youtube_optimizer
        
        print("📋 当前YouTube平台配置:")
        config = youtube_optimizer.youtube_config
        
        print(f"   标题最大长度: {config['title_max_length']}")
        print(f"   描述最大长度: {config['description_max_length']}")
        print(f"   最大标签数: {config['tags_max_count']}")
        print(f"   Shorts最大时长: {config['shorts_max_duration']}秒")
        print(f"   Shorts最小分辨率: {config['shorts_min_resolution']}")
        print(f"   长视频最小分辨率: {config['long_video_min_resolution']}")
        
        print(f"\n🏷️ 推荐标签: {', '.join(config['popular_tags'])}")
        print(f"🔥 热门关键词: {', '.join(config['trending_keywords'][:5])}...")
        
        # 演示视频优化
        sample_video = {
            'video_path': 'sample_video.mp4',  # 假设的视频路径
            'title': '人工智能技术教程',
            'description': '这是一个关于AI技术的教程视频',
            'tags': ['教程', '技术']
        }
        
        print(f"\n🔧 视频信息优化示例:")
        print(f"原始标题: {sample_video['title']}")
        
        optimized = youtube_optimizer.optimize_video_info(sample_video)
        print(f"优化标题: {optimized['title']}")
        print(f"视频类型: {optimized.get('video_type', 'unknown')}")
        print(f"优化标签: {', '.join(optimized['tags'][:5])}...")
        
    except Exception as e:
        print(f"❌ 配置示例失败: {e}")

async def main():
    """主函数"""
    print("🎬 YouTube发布功能完整示例")
    print("=" * 60)
    
    # 检查配置
    print("🔍 检查YouTube配置...")
    
    credentials_file = "config/youtube_credentials.json"
    if not os.path.exists(credentials_file):
        print(f"⚠️ YouTube API凭据文件不存在: {credentials_file}")
        print("请按照以下步骤配置:")
        print("1. 访问 https://console.developers.google.com/")
        print("2. 创建项目并启用YouTube Data API v3")
        print("3. 创建OAuth 2.0凭据并下载JSON文件")
        print(f"4. 将文件保存为: {credentials_file}")
        print("\n继续运行配置示例...")
        
        # 只运行配置示例
        await youtube_config_example()
        return
    
    print("✅ YouTube API凭据文件存在")
    
    # 运行所有示例
    try:
        # 1. 基本发布示例
        await youtube_publish_example()
        
        # 2. Shorts发布示例
        await youtube_shorts_example()
        
        # 3. 批量发布示例
        await batch_youtube_publish_example()
        
        # 4. 配置示例
        await youtube_config_example()
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断示例运行")
    except Exception as e:
        print(f"\n❌ 示例运行失败: {e}")
    
    print("\n🎉 YouTube发布功能示例完成！")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
