#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube发布器使用示例
展示如何使用YouTube发布器管理器进行视频发布
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.platform_publisher.youtube_publisher_manager import YouTubePublisherManager
from src.utils.logger import logger

async def test_youtube_api():
    """测试YouTube API发布"""
    try:
        logger.info("🧪 测试YouTube API发布...")
        
        # 创建API发布器
        from src.services.platform_publisher.youtube_api_publisher import YouTubeAPIPublisher
        
        api_config = {
            'credentials_file': 'config/youtube_credentials.json',
            'token_file': 'config/youtube_token.pickle'
        }
        
        publisher = YouTubeAPIPublisher(api_config)
        
        # 检查凭据文件
        if not os.path.exists(api_config['credentials_file']):
            logger.warning("⚠️ YouTube API凭据文件不存在")
            logger.info("📝 请按照以下步骤配置:")
            logger.info("1. 访问 https://console.developers.google.com/")
            logger.info("2. 创建项目并启用YouTube Data API v3")
            logger.info("3. 创建OAuth 2.0凭据并下载JSON文件")
            logger.info(f"4. 保存为: {api_config['credentials_file']}")
            return False
        
        # 测试初始化
        if await publisher.initialize():
            logger.info("✅ YouTube API初始化成功")
            
            # 测试获取频道信息
            channel_info = await publisher.get_channel_info()
            if channel_info.get('success'):
                logger.info(f"📺 频道信息: {channel_info['title']}")
                logger.info(f"👥 订阅者: {channel_info.get('subscriber_count', 'N/A')}")
                return True
            else:
                logger.error(f"❌ 获取频道信息失败: {channel_info.get('error')}")
                return False
        else:
            logger.error("❌ YouTube API初始化失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ YouTube API测试失败: {e}")
        return False

async def test_youtube_selenium():
    """测试YouTube Selenium发布"""
    try:
        logger.info("🧪 测试YouTube Selenium发布...")
        
        # 创建Selenium发布器
        from src.services.platform_publisher.youtube_stealth_publisher import YouTubeStealthPublisher
        
        selenium_config = {
            'driver_type': 'chrome',
            'headless': False,
            'stealth_mode': True,
            'use_debug_mode': True,
            'debug_port': 9222
        }
        
        publisher = YouTubeStealthPublisher(selenium_config)
        
        # 检查Chrome调试模式
        logger.info("🔍 检查Chrome调试模式...")
        logger.info("请确保已启动Chrome调试模式:")
        logger.info("chrome.exe --remote-debugging-port=9222 --user-data-dir=youtube_selenium")
        
        # 测试初始化
        if publisher.initialize():
            logger.info("✅ YouTube Selenium初始化成功")
            
            # 测试登录状态
            if await publisher._check_login_status():
                logger.info("✅ YouTube登录状态正常")
                return True
            else:
                logger.warning("⚠️ 需要在浏览器中登录YouTube Studio")
                return False
        else:
            logger.error("❌ YouTube Selenium初始化失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ YouTube Selenium测试失败: {e}")
        return False

async def test_youtube_manager():
    """测试YouTube发布器管理器"""
    try:
        logger.info("🧪 测试YouTube发布器管理器...")
        
        # 创建管理器
        manager = YouTubePublisherManager()
        
        # 测试配置加载
        logger.info(f"📋 API启用: {manager.config.get('api', {}).get('enabled', False)}")
        logger.info(f"📋 Selenium启用: {manager.config.get('selenium', {}).get('enabled', True)}")
        
        # 模拟视频信息
        video_info = {
            'video_path': 'test_video.mp4',  # 这里使用模拟路径
            'title': '测试视频标题',
            'description': '这是一个测试视频的描述内容',
            'tags': ['测试', 'AI', '自动化'],
            'privacy': 'unlisted'  # 使用unlisted避免公开发布测试视频
        }
        
        # 预处理测试
        processed_info = manager._preprocess_video_info(video_info)
        logger.info(f"✅ 视频信息预处理成功")
        logger.info(f"📝 处理后标题: {processed_info['title']}")
        logger.info(f"🏷️ 处理后标签: {processed_info['tags']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ YouTube管理器测试失败: {e}")
        return False

async def publish_test_video():
    """发布测试视频示例"""
    try:
        logger.info("🚀 YouTube视频发布示例...")
        
        # 检查测试视频文件
        test_video_path = "test_video.mp4"
        if not os.path.exists(test_video_path):
            logger.warning("⚠️ 测试视频文件不存在，创建模拟发布...")
            
            # 模拟发布（不实际上传）
            video_info = {
                'video_path': test_video_path,
                'title': 'AI生成测试视频',
                'description': '''这是一个AI生成的测试视频。

🤖 使用AI技术自动生成
🔔 订阅获取更多AI内容！

#AI #测试 #自动化''',
                'tags': ['AI', '测试', '自动化', '科技'],
                'privacy': 'unlisted'
            }
            
            logger.info("🎭 模拟发布模式（不会实际上传）")
            logger.info(f"📝 标题: {video_info['title']}")
            logger.info(f"📄 描述: {video_info['description'][:100]}...")
            logger.info(f"🏷️ 标签: {video_info['tags']}")
            logger.info(f"🔒 隐私: {video_info['privacy']}")
            
            return {'success': True, 'message': '模拟发布成功'}
        
        # 实际发布
        manager = YouTubePublisherManager()
        result = await manager.publish_video(video_info)
        
        if result.get('success'):
            logger.info("🎉 视频发布成功!")
            if 'video_url' in result:
                logger.info(f"🔗 视频链接: {result['video_url']}")
        else:
            logger.error(f"❌ 视频发布失败: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 发布测试视频失败: {e}")
        return {'success': False, 'error': str(e)}

def show_setup_guide():
    """显示设置指南"""
    print("\n" + "="*70)
    print("📋 YouTube发布器设置指南")
    print("="*70)
    print()
    print("🔑 方案1: YouTube API（推荐）")
    print("1. 访问 https://console.developers.google.com/")
    print("2. 创建项目并启用 YouTube Data API v3")
    print("3. 创建 OAuth 2.0 客户端ID凭据")
    print("4. 下载凭据JSON文件，保存为 config/youtube_credentials.json")
    print("5. 首次运行时会自动打开浏览器进行授权")
    print()
    print("🌐 方案2: Selenium（备用）")
    print("1. 启动Chrome调试模式:")
    print("   chrome.exe --remote-debugging-port=9222 --user-data-dir=youtube_selenium")
    print("2. 在浏览器中手动登录 YouTube Studio")
    print("3. 运行发布程序")
    print()
    print("💡 建议:")
    print("- 优先配置API方案，更稳定可靠")
    print("- Selenium作为备用，API失败时自动切换")
    print("- 测试视频建议设置为 unlisted 避免公开")
    print()
    print("="*70)

async def main():
    """主函数"""
    logger.info("🚀 YouTube发布器测试开始...")
    
    # 显示设置指南
    show_setup_guide()
    
    # 询问用户要测试哪个方案
    print("\n请选择要测试的方案:")
    print("1. YouTube API测试")
    print("2. YouTube Selenium测试")
    print("3. YouTube管理器测试")
    print("4. 模拟视频发布")
    print("5. 全部测试")
    
    choice = input("\n请输入选择 (1-5): ").strip()
    
    if choice == '1':
        await test_youtube_api()
    elif choice == '2':
        await test_youtube_selenium()
    elif choice == '3':
        await test_youtube_manager()
    elif choice == '4':
        await publish_test_video()
    elif choice == '5':
        logger.info("🧪 开始全部测试...")
        await test_youtube_api()
        await test_youtube_selenium()
        await test_youtube_manager()
        await publish_test_video()
    else:
        logger.info("👋 测试已取消")
    
    logger.info("✅ YouTube发布器测试完成")

if __name__ == "__main__":
    asyncio.run(main())
