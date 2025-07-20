#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信视频号发布器使用示例
展示如何使用优化后的微信视频号发布功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.platform_publisher.selenium_wechat_publisher import SeleniumWechatPublisher
from src.utils.logger import logger

async def publish_to_wechat_example():
    """微信视频号发布示例"""
    try:
        logger.info("🚀 开始微信视频号发布示例...")
        
        # 1. 配置发布器
        selenium_config = {
            'headless': False,  # 显示浏览器界面
            'simulation_mode': False,  # 实际发布模式
            'chrome_debug_port': 9222,  # 连接现有Chrome实例
            'timeout': 30,  # 超时时间
            'retry_count': 3  # 重试次数
        }
        
        # 2. 初始化发布器
        publisher = SeleniumWechatPublisher(selenium_config)
        logger.info("✅ 微信视频号发布器初始化完成")
        
        # 3. 准备视频信息
        video_info = {
            # 基本信息
            'video_path': 'path/to/your/video.mp4',  # 替换为实际视频路径
            'title': '我的精彩视频',  # 6-16个字符，符合微信要求
            'description': '这是一个精彩的视频内容，展示了...',  # 描述内容
            'tags': ['生活', '分享', '精彩'],  # 最多3个标签
            
            # 微信视频号特有功能
            'location': '北京市朝阳区',  # 位置信息
            'is_original': True,  # 声明原创
            'collection': '我的日常',  # 添加到合集
            'scheduled_time': '',  # 空表示立即发布，也可以设置具体时间
            
            # 可选配置
            'cover_image': '',  # 自定义封面图片路径
            'privacy_setting': 'public'  # 隐私设置
        }
        
        logger.info("📋 视频发布信息:")
        logger.info(f"  📹 视频路径: {video_info['video_path']}")
        logger.info(f"  📝 标题: {video_info['title']}")
        logger.info(f"  📄 描述: {video_info['description'][:50]}...")
        logger.info(f"  🏷️  标签: {video_info['tags']}")
        logger.info(f"  📍 位置: {video_info['location']}")
        logger.info(f"  ✍️  原创: {video_info['is_original']}")
        logger.info(f"  📚 合集: {video_info['collection']}")
        
        # 4. 执行发布
        logger.info("🎬 开始发布视频到微信视频号...")
        result = await publisher._publish_video_impl(video_info)
        
        # 5. 处理发布结果
        if result['success']:
            logger.info("🎉 视频发布成功！")
            logger.info(f"📝 发布结果: {result['message']}")
            
            # 可以在这里添加后续处理逻辑
            # 例如：记录发布历史、发送通知等
            
        else:
            logger.error("❌ 视频发布失败！")
            logger.error(f"📝 错误信息: {result.get('error', '未知错误')}")
            
            # 可以在这里添加错误处理逻辑
            # 例如：重试、记录错误日志等
        
        return result['success']
        
    except Exception as e:
        logger.error(f"❌ 发布过程中出现异常: {e}")
        return False

def batch_publish_example():
    """批量发布示例"""
    logger.info("📦 批量发布示例...")
    
    # 批量视频信息
    video_list = [
        {
            'video_path': 'video1.mp4',
            'title': '视频1标题',
            'description': '视频1描述',
            'tags': ['标签1', '标签2'],
            'location': '北京市',
            'is_original': True
        },
        {
            'video_path': 'video2.mp4',
            'title': '视频2标题',
            'description': '视频2描述',
            'tags': ['标签3', '标签4'],
            'location': '上海市',
            'is_original': True
        }
    ]
    
    logger.info(f"📊 准备批量发布 {len(video_list)} 个视频")
    
    # 这里可以实现批量发布逻辑
    # 注意：实际使用时需要考虑发布间隔，避免频率过高
    
    return True

def scheduled_publish_example():
    """定时发布示例"""
    logger.info("⏰ 定时发布示例...")
    
    video_info = {
        'video_path': 'scheduled_video.mp4',
        'title': '定时发布视频',
        'description': '这是一个定时发布的视频',
        'tags': ['定时', '发布'],
        'location': '深圳市',
        'is_original': True,
        'scheduled_time': '2024-01-01 12:00:00'  # 设置具体发布时间
    }
    
    logger.info(f"⏰ 设置发布时间: {video_info['scheduled_time']}")
    
    # 这里可以实现定时发布逻辑
    
    return True

def main():
    """主函数"""
    logger.info("🎯 微信视频号发布器使用示例")
    
    print("\n请选择示例类型:")
    print("1. 单个视频发布")
    print("2. 批量发布示例")
    print("3. 定时发布示例")
    print("4. 退出")
    
    choice = input("\n请输入选择 (1-4): ").strip()
    
    if choice == '1':
        # 单个视频发布
        success = asyncio.run(publish_to_wechat_example())
        if success:
            logger.info("✅ 单个视频发布示例完成")
        else:
            logger.error("❌ 单个视频发布示例失败")
            
    elif choice == '2':
        # 批量发布示例
        success = batch_publish_example()
        if success:
            logger.info("✅ 批量发布示例完成")
            
    elif choice == '3':
        # 定时发布示例
        success = scheduled_publish_example()
        if success:
            logger.info("✅ 定时发布示例完成")
            
    elif choice == '4':
        logger.info("👋 退出示例程序")
        return
        
    else:
        logger.warning("⚠️  无效选择，请重新运行程序")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 用户中断程序")
    except Exception as e:
        logger.error(f"❌ 程序运行异常: {e}")
