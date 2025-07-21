#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的韩信项目微信视频号发布测试
跳过复杂的前提检查，直接测试发布功能
"""

import sys
import os
import asyncio
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.platform_publisher.selenium_wechat_publisher import SeleniumWechatPublisher
from src.utils.logger import logger

def get_hanxin_project_info():
    """获取韩信项目信息"""
    project_dir = project_root / "output" / "韩信"
    video_file = project_dir / "final_video.mp4"
    
    if not video_file.exists():
        raise FileNotFoundError(f"韩信项目视频文件不存在: {video_file}")
    
    # 韩信项目的视频信息
    video_info = {
        'video_path': str(video_file),
        'title': '韩信投汉 - 萧何月下追韩信',
        'description': '''📚 历史故事：韩信投汉

🎭 秋风萧瑟的夜晚，年轻的韩信因不得重用而悄然离去，却在山路上遇到了追来的萧何。这段"萧何月下追韩信"的佳话，不仅改变了韩信的命运，也影响了整个历史的走向。

✨ 故事亮点：
• 韩信的雄心壮志与现实困境
• 萧何的慧眼识珠与义气相助  
• 刘邦的用人之道与王者气度

#历史故事 #韩信 #萧何''',
        'tags': ['历史故事', '韩信', '萧何'],
        'location': '',
        'is_original': True,
        'scheduled_time': '',
        'collection': ''
    }
    
    return video_info

async def test_wechat_publish():
    """测试微信视频号发布"""
    try:
        logger.info("🧪 开始简化的微信视频号发布测试...")
        
        # 配置 - 优先使用Firefox
        config = {
            'driver_type': 'firefox',
            'headless': False,
            'implicit_wait': 10,
            'page_load_timeout': 60,
            'wechat_proxy_bypass': True,
            'no_proxy_domains': ['weixin.qq.com', 'channels.weixin.qq.com'],
            'simulation_mode': False
        }
        
        # 获取韩信项目信息
        video_info = get_hanxin_project_info()
        
        logger.info("📋 韩信项目信息:")
        logger.info(f"  视频文件: {video_info['video_path']}")
        logger.info(f"  标题: {video_info['title']}")
        logger.info(f"  标签: {video_info['tags']}")
        
        # 检查视频文件
        video_path = Path(video_info['video_path'])
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        file_size = video_path.stat().st_size / (1024 * 1024)
        logger.info(f"📁 视频文件大小: {file_size:.2f} MB")
        
        # 用户确认
        print("\n" + "="*50)
        print("🎬 韩信项目微信视频号发布测试")
        print("="*50)
        print(f"📝 标题: {video_info['title']}")
        print(f"📊 文件大小: {file_size:.2f} MB")
        print(f"🏷️ 标签: {', '.join(video_info['tags'])}")
        print("="*50)
        
        print("⚠️ 重要提醒:")
        print("1. 这将尝试真实发布到微信视频号")
        print("2. 优先使用Firefox，失败时切换Chrome")
        print("3. 请确保已登录微信视频号")
        print()
        
        confirm = input("确认继续测试? (输入 'yes'): ").strip().lower()
        if confirm != 'yes':
            logger.info("❌ 用户取消测试")
            return False
        
        # 创建发布器并测试
        logger.info("🚀 创建微信视频号发布器...")
        start_time = time.time()
        
        try:
            publisher = SeleniumWechatPublisher(config)
            logger.info("✅ 发布器创建成功")
            
            # 开始发布
            logger.info("🎬 开始发布流程...")
            result = await publisher._publish_video_impl(video_info)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 输出结果
            print("\n" + "="*50)
            print("📊 测试结果")
            print("="*50)
            
            if result['success']:
                logger.info("🎉 发布测试成功！")
                print("✅ 状态: 成功")
                print(f"⏱️ 耗时: {duration:.2f} 秒")
                print(f"📋 信息: {result.get('message', '发布完成')}")
                return True
            else:
                logger.error("❌ 发布测试失败")
                print("❌ 状态: 失败")
                print(f"⏱️ 耗时: {duration:.2f} 秒")
                print(f"📋 错误: {result.get('error', '未知错误')}")
                return False
                
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            logger.error(f"❌ 发布器创建或发布失败: {e}")
            print("\n" + "="*50)
            print("📊 测试结果")
            print("="*50)
            print("❌ 状态: 异常")
            print(f"⏱️ 耗时: {duration:.2f} 秒")
            print(f"📋 错误: {e}")
            return False
            
        finally:
            # 清理资源
            try:
                if 'publisher' in locals():
                    await publisher.cleanup()
                    logger.info("🧹 资源清理完成")
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}")
        print(f"\n❌ 测试异常: {e}")
        return False

async def main():
    """主函数"""
    print("🧪 韩信项目微信视频号发布测试（简化版）")
    print("=" * 60)
    
    # 基础检查
    project_dir = project_root / "output" / "韩信"
    video_file = project_dir / "final_video.mp4"
    
    if not project_dir.exists():
        print("❌ 韩信项目目录不存在")
        return False
        
    if not video_file.exists():
        print("❌ 韩信项目视频文件不存在")
        return False
    
    print("✅ 韩信项目文件检查通过")
    
    # 运行测试
    success = await test_wechat_publish()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 韩信项目发布测试成功！")
        print("✅ Firefox优先策略验证成功")
        print("🔧 增强的微信发布器工作正常")
    else:
        print("❌ 韩信项目发布测试失败")
        print("🔧 请检查错误信息并调整")
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        sys.exit(1)
