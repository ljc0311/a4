#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式微信视频号登录状态保存
打开浏览器，等待用户登录，然后保存登录状态
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.platform_publisher.selenium_wechat_publisher import SeleniumWechatPublisher
from src.utils.logger import logger

def interactive_login_and_save():
    """交互式登录并保存状态"""
    publisher = None
    try:
        logger.info("🎭 开始交互式微信视频号登录...")
        
        # 配置
        config = {
            'driver_type': 'firefox',
            'headless': False,
            'implicit_wait': 10,
            'wechat_proxy_bypass': True,
            'no_proxy_domains': ['weixin.qq.com', 'channels.weixin.qq.com'],
            'simulation_mode': False
        }
        
        print("🚀 正在启动Firefox浏览器...")
        print("请稍等，浏览器启动中...")
        
        # 创建发布器实例
        publisher = SeleniumWechatPublisher(config)
        
        print("✅ Firefox浏览器已启动")
        print("🌐 正在访问微信视频号登录页面...")
        
        # 访问微信视频号登录页面
        publisher.driver.get("https://channels.weixin.qq.com")
        time.sleep(3)
        
        print("\n" + "="*60)
        print("📱 请在浏览器中完成微信视频号登录")
        print("="*60)
        print("1. 在打开的Firefox窗口中扫码登录微信视频号")
        print("2. 确保能正常访问创作者中心")
        print("3. 登录完成后回到此窗口按回车键")
        print("4. 程序将自动检测并保存登录状态")
        print("="*60)
        
        # 等待用户登录
        input("\n✅ 登录完成后请按回车键继续...")
        
        print("\n🔍 检测登录状态...")
        
        # 检测登录状态
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                current_url = publisher.driver.current_url
                page_title = publisher.driver.title
                
                logger.info(f"📄 当前页面: {current_url}")
                logger.info(f"📝 页面标题: {page_title}")
                
                print(f"📄 当前页面: {current_url}")
                print(f"📝 页面标题: {page_title}")
                
                # 如果还在登录页面，给用户更多时间
                if 'login' in current_url or 'passport' in current_url:
                    if attempt < max_attempts - 1:
                        print(f"⚠️ 仍在登录页面，等待登录完成... (尝试 {attempt + 1}/{max_attempts})")
                        time.sleep(5)
                        continue
                    else:
                        print("❌ 登录超时，请确保已完成登录")
                        return False
                
                # 检查页面内容
                page_source = publisher.driver.page_source
                
                login_indicators = [
                    '创作者中心', '发布视频', '数据概览', '内容管理',
                    'creator', 'publish', 'dashboard', '我的作品',
                    '视频管理', '粉丝', '收益', '创作', '发表'
                ]
                
                found_indicators = []
                for indicator in login_indicators:
                    if indicator in page_source:
                        found_indicators.append(indicator)
                
                print(f"🔍 找到登录指示器: {found_indicators}")
                logger.info(f"🔍 找到登录指示器: {found_indicators}")
                
                if len(found_indicators) >= 1:  # 降低要求，只需要1个指示器
                    print("✅ 确认已登录微信视频号")
                    logger.info("✅ 确认已登录微信视频号")
                    
                    # 保存登录状态
                    print("💾 正在保存登录状态...")
                    logger.info("💾 开始保存登录状态...")
                    
                    publisher.save_login_state()
                    
                    # 验证保存结果
                    if publisher.db_service.is_login_state_valid('wechat', expire_hours=168):
                        login_data = publisher.db_service.get_login_state('wechat')
                        
                        print("\n🎉 登录状态保存成功！")
                        print("📋 保存信息:")
                        print(f"  平台: 微信视频号")
                        print(f"  页面: {current_url}")
                        print(f"  标题: {page_title}")
                        print(f"  Cookies: {len(login_data.get('cookies', []))} 个")
                        print(f"  存储数据: {len(login_data.get('local_storage', {}))} 项")
                        print(f"  有效期: 7天")
                        print(f"  登录指示器: {', '.join(found_indicators)}")
                        
                        logger.info("✅ 登录状态保存成功！")
                        return True
                    else:
                        print("❌ 登录状态保存验证失败")
                        logger.error("❌ 登录状态保存验证失败")
                        return False
                else:
                    if attempt < max_attempts - 1:
                        print(f"⚠️ 未检测到足够的登录指示器，重试中... (尝试 {attempt + 1}/{max_attempts})")
                        
                        # 尝试访问创作者中心
                        try:
                            publisher.driver.get("https://channels.weixin.qq.com/platform")
                            time.sleep(3)
                        except:
                            pass
                        continue
                    else:
                        print("❌ 未检测到有效的登录状态")
                        print("请确保:")
                        print("1. 已成功扫码登录微信视频号")
                        print("2. 能正常访问创作者中心页面")
                        print("3. 页面完全加载完成")
                        return False
                        
            except Exception as e:
                logger.error(f"检测登录状态时出错: {e}")
                if attempt < max_attempts - 1:
                    print(f"⚠️ 检测出错，重试中... (尝试 {attempt + 1}/{max_attempts})")
                    time.sleep(3)
                    continue
                else:
                    print(f"❌ 检测登录状态失败: {e}")
                    return False
        
        return False
        
    except Exception as e:
        logger.error(f"交互式登录保存失败: {e}")
        print(f"❌ 操作失败: {e}")
        return False
        
    finally:
        # 询问是否关闭浏览器
        if publisher:
            try:
                print("\n🌐 浏览器仍在运行中...")
                choice = input("是否关闭浏览器? (y/N): ").strip().lower()
                if choice == 'y':
                    publisher.cleanup()
                    print("🔒 浏览器已关闭")
                else:
                    print("🌐 浏览器保持打开状态")
                    print("💡 您可以继续在浏览器中使用微信视频号")
            except:
                pass

def main():
    """主函数"""
    print("🎭 交互式微信视频号登录状态保存")
    print("=" * 60)
    
    print("📋 操作流程:")
    print("1. 程序将启动Firefox浏览器")
    print("2. 自动访问微信视频号登录页面")
    print("3. 您在浏览器中扫码登录")
    print("4. 登录完成后程序自动保存登录状态")
    print("5. 保存成功后可用于自动发布")
    
    print("\n⚠️ 重要提醒:")
    print("- 请确保网络连接正常")
    print("- 准备好微信扫码登录")
    print("- 登录状态有效期为7天")
    print("- 过程中请勿关闭浏览器")
    
    confirm = input("\n确认开始交互式登录? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 操作已取消")
        return False
    
    # 执行交互式登录和保存
    success = interactive_login_and_save()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 微信视频号登录状态保存完成！")
        print("✅ 现在可以使用自动发布功能")
        print("\n🚀 测试自动发布:")
        print("python scripts/simple_hanxin_test.py")
        print("\n💡 提示:")
        print("- 登录状态有效期为7天")
        print("- 过期后需要重新保存登录状态")
        print("- 可以随时重新运行此脚本更新登录状态")
    else:
        print("❌ 登录状态保存失败")
        print("🔧 请检查网络连接和登录状态后重试")
        print("\n💡 故障排除:")
        print("1. 确保网络连接正常")
        print("2. 确保微信扫码登录成功")
        print("3. 确保能正常访问创作者中心")
        print("4. 重新运行此脚本")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 操作异常: {e}")
        sys.exit(1)
