#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟发布演示脚本
直接测试模拟模式的发布功能
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
from src.utils.logger import logger


class SimulationPublishDemo:
    """模拟发布演示器"""
    
    def __init__(self):
        self.supported_platforms = SeleniumPublisherFactory.SUPPORTED_PLATFORMS.keys()
        
    async def run_demo(self):
        """运行演示"""
        print("🎭 模拟发布功能演示")
        print("=" * 50)
        
        # 创建测试视频信息
        video_info = self._create_test_video_info()
        
        # 配置模拟模式
        config = {
            'simulation_mode': True,
            'headless': True,
            'timeout': 30
        }
        
        results = {}
        
        # 测试每个平台的模拟发布
        for platform in self.supported_platforms:
            print(f"\n📤 测试 {platform} 模拟发布...")
            
            try:
                # 创建发布器
                publisher = SeleniumPublisherFactory.create_publisher(platform, config)
                
                # 初始化发布器（模拟模式）
                if publisher.initialize():
                    # 调用发布实现
                    result = await publisher._publish_video_impl(video_info)
                    results[platform] = result
                    
                    if result.get('success'):
                        print(f"  ✅ {platform} 模拟发布成功")
                    else:
                        print(f"  ❌ {platform} 模拟发布失败: {result.get('error', '未知错误')}")
                else:
                    print(f"  ❌ {platform} 发布器初始化失败")
                    results[platform] = {'success': False, 'error': '发布器初始化失败'}
                    
            except Exception as e:
                print(f"  ❌ {platform} 发布异常: {e}")
                results[platform] = {'success': False, 'error': str(e)}
        
        # 显示结果统计
        self._show_results(results)
    
    def _create_test_video_info(self) -> dict:
        """创建测试视频信息"""
        # 创建临时视频文件
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_file.write(b'DEMO VIDEO CONTENT')
            video_path = temp_file.name
        
        video_info = {
            'video_path': video_path,
            'title': 'AI视频生成器 - 模拟发布测试',
            'description': '这是一个模拟发布测试视频，用于验证多平台发布功能。#AI视频 #测试',
            'tags': ['AI视频', '测试', '模拟发布'],
            'cover_path': None
        }
        
        print(f"📋 测试视频信息:")
        print(f"  标题: {video_info['title']}")
        print(f"  描述: {video_info['description'][:50]}...")
        print(f"  标签: {video_info['tags']}")
        print(f"  视频文件: {video_path}")
        
        return video_info
    
    def _show_results(self, results: dict):
        """显示结果统计"""
        print("\n" + "=" * 50)
        print("📊 模拟发布结果统计:")
        print("-" * 30)
        
        success_count = 0
        failed_count = 0
        
        platform_names = {
            'douyin': '抖音',
            'kuaishou': '快手', 
            'xiaohongshu': '小红书',
            'bilibili': 'B站',
            'wechat': '微信视频号',
            'youtube': 'YouTube'
        }
        
        for platform, result in results.items():
            name = platform_names.get(platform, platform)
            status = "✅ 成功" if result.get('success') else "❌ 失败"
            print(f"  {name:10} {status}")
            
            if result.get('success'):
                success_count += 1
            else:
                failed_count += 1
                error = result.get('error', '未知错误')
                print(f"             错误: {error}")
        
        print("-" * 30)
        print(f"总计: {len(results)}个平台")
        print(f"成功: {success_count}个")
        print(f"失败: {failed_count}个")
        print(f"成功率: {success_count/len(results)*100:.1f}%")
        
        if success_count == len(results):
            print("\n🎉 所有平台模拟发布测试通过！")
            print("💡 模拟模式功能正常，可以进行实际发布测试")
        else:
            print(f"\n⚠️ 有 {failed_count} 个平台测试失败，需要检查相关代码")
        
        print("\n📝 下一步:")
        print("1. 修复失败的平台发布器")
        print("2. 准备真实的视频文件")
        print("3. 配置Chrome浏览器和ChromeDriver")
        print("4. 手动登录各平台账号")
        print("5. 关闭模拟模式进行实际发布测试")


async def main():
    """主函数"""
    demo = SimulationPublishDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
