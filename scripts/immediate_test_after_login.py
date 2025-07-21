#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
登录后立即测试发布功能
在同一个浏览器会话中完成登录和发布测试
"""

import sys
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

async def test_immediate_publish():
    """在同一会话中登录并立即测试发布"""
    publisher = None
    try:
        logger.info("🧪 开始同会话登录+发布测试...")
        
        # 配置
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
        file_size = Path(video_info['video_path']).stat().st_size / (1024 * 1024)
        
        print("\n" + "="*60)
        print("🎬 同会话登录+发布测试")
        print("="*60)
        print(f"📝 标题: {video_info['title']}")
        print(f"📊 文件大小: {file_size:.2f} MB")
        print(f"🏷️ 标签: {', '.join(video_info['tags'])}")
        print("="*60)
        
        print("📋 测试流程:")
        print("1. 启动Firefox浏览器")
        print("2. 访问微信视频号平台")
        print("3. 等待用户手动登录")
        print("4. 保存登录状态")
        print("5. 立即测试发布功能")
        print()
        
        confirm = input("确认开始测试? (输入 'yes'): ").strip().lower()
        if confirm != 'yes':
            logger.info("❌ 用户取消测试")
            return False
        
        # 创建发布器
        logger.info("🚀 创建微信视频号发布器...")
        publisher = SeleniumWechatPublisher(config)
        
        # 访问微信视频号平台
        logger.info("🌐 访问微信视频号平台...")
        publisher.driver.get("https://channels.weixin.qq.com")
        time.sleep(3)
        
        # 检查是否需要登录
        current_url = publisher.driver.current_url
        if 'login' in current_url:
            print("\n📱 检测到登录页面")
            print("请在Firefox浏览器中完成登录...")
            print("登录完成后回到此窗口按回车键继续")
            input("✅ 登录完成后按回车键: ")
        
        # 验证登录状态
        logger.info("🔍 验证登录状态...")
        current_url = publisher.driver.current_url
        page_title = publisher.driver.title
        
        print(f"📄 当前页面: {current_url}")
        print(f"📝 页面标题: {page_title}")
        
        # 检查登录指示器
        page_source = publisher.driver.page_source
        login_indicators = [
            '创作者中心', '发布视频', '数据概览', '内容管理',
            'creator', 'publish', 'dashboard', '我的作品',
            '视频管理', '粉丝', '收益', '创作', '发表',
            '视频号', '助手', '发布', '管理', '数据',
            'platform', 'post', 'create', 'video'
        ]
        
        found_indicators = []
        for indicator in login_indicators:
            if indicator in page_source:
                found_indicators.append(indicator)
        
        if not found_indicators:
            print("❌ 未检测到登录指示器，可能未成功登录")
            return False
        
        print(f"✅ 检测到登录指示器: {', '.join(found_indicators[:5])}...")
        
        # 保存登录状态
        logger.info("💾 保存当前登录状态...")
        publisher.save_login_state()
        
        # 立即测试发布功能
        print("\n🎬 立即测试发布功能...")
        print("⚠️ 这将在同一个浏览器会话中测试发布")
        
        test_confirm = input("确认测试发布? (输入 'yes'): ").strip().lower()
        if test_confirm != 'yes':
            logger.info("❌ 用户取消发布测试")
            return False
        
        # 开始发布测试
        logger.info("🎬 开始发布流程...")
        start_time = time.time()
        
        result = await publisher._publish_video_impl(video_info)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 输出结果
        print("\n" + "="*60)
        print("📊 测试结果")
        print("="*60)
        
        if result['success']:
            logger.info("🎉 同会话发布测试成功！")
            print("✅ 状态: 成功")
            print(f"⏱️ 耗时: {duration:.2f} 秒")
            print(f"📋 信息: {result.get('message', '发布完成')}")
            print("\n💡 这证明登录状态在同一会话中是有效的")
            return True
        else:
            logger.error("❌ 同会话发布测试失败")
            print("❌ 状态: 失败")
            print(f"⏱️ 耗时: {duration:.2f} 秒")
            print(f"📋 错误: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}")
        print(f"\n❌ 测试异常: {e}")
        return False
        
    finally:
        # 询问是否保持浏览器打开
        if publisher and publisher.driver:
            print("\n🌐 浏览器仍在运行中...")
            keep_open = input("是否保持浏览器打开以便进一步测试? (y/N): ").strip().lower()
            if keep_open != 'y':
                try:
                    await publisher.cleanup()
                    logger.info("🧹 资源清理完成")
                except:
                    pass

async def main():
    """主函数"""
    print("🧪 微信视频号同会话登录+发布测试")
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
    success = await test_immediate_publish()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 同会话测试成功！")
        print("💡 这说明登录状态在同一浏览器会话中是有效的")
        print("🔧 问题可能在于跨会话的状态恢复机制")
    else:
        print("❌ 同会话测试失败")
        print("🔧 需要进一步调试登录和发布流程")
    
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
