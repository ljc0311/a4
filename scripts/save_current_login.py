#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
保存当前微信视频号登录状态
使用微信发布器直接保存登录状态
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.platform_publisher.selenium_wechat_publisher import SeleniumWechatPublisher
from src.utils.logger import logger

def save_current_wechat_login():
    """保存当前微信视频号登录状态"""
    publisher = None
    try:
        logger.info("💾 开始保存微信视频号登录状态...")
        
        # 配置
        config = {
            'driver_type': 'firefox',
            'headless': False,
            'implicit_wait': 10,
            'wechat_proxy_bypass': True,
            'no_proxy_domains': ['weixin.qq.com', 'channels.weixin.qq.com'],
            'simulation_mode': False
        }
        
        print("🚀 正在启动Firefox并连接到微信视频号...")
        
        # 创建发布器实例
        publisher = SeleniumWechatPublisher(config)
        
        print("✅ Firefox浏览器已启动")
        print("🌐 正在访问微信视频号平台...")
        
        # 访问微信视频号平台
        publisher.driver.get("https://channels.weixin.qq.com/platform")
        time.sleep(5)  # 等待页面加载
        
        # 检查当前页面
        current_url = publisher.driver.current_url
        page_title = publisher.driver.title
        
        logger.info(f"📄 当前页面: {current_url}")
        logger.info(f"📝 页面标题: {page_title}")
        
        print(f"📄 当前页面: {current_url}")
        print(f"📝 页面标题: {page_title}")
        
        # 如果跳转到登录页面，提示用户登录
        if 'login' in current_url or 'passport' in current_url:
            print("\n📱 检测到登录页面，请在浏览器中完成登录")
            print("=" * 50)
            print("1. 在Firefox窗口中扫码登录微信视频号")
            print("2. 确保能正常访问创作者中心")
            print("3. 登录完成后回到此窗口按回车键")
            print("=" * 50)
            
            input("\n✅ 登录完成后请按回车键继续...")
            
            # 重新检查页面
            time.sleep(2)
            current_url = publisher.driver.current_url
            page_title = publisher.driver.title
            
            print(f"📄 更新后页面: {current_url}")
            print(f"📝 更新后标题: {page_title}")
        
        # 检查登录状态
        if 'login' in current_url or 'passport' in current_url:
            print("❌ 仍在登录页面，请确保已完成登录")
            return False
        
        # 检查页面内容
        try:
            page_source = publisher.driver.page_source
            
            # 扩展登录指示器列表
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
            
            print(f"🔍 找到登录指示器: {found_indicators}")
            logger.info(f"🔍 找到登录指示器: {found_indicators}")
            
            # 降低要求，只需要找到任何指示器
            if found_indicators:
                print("✅ 确认已登录微信视频号")
                logger.info("✅ 确认已登录微信视频号")
                
                # 保存登录状态
                print("💾 正在保存登录状态...")
                logger.info("💾 开始保存登录状态...")
                
                # 使用发布器的保存方法
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
                    print(f"  LocalStorage: {len(login_data.get('local_storage', {}))} 项")
                    print(f"  有效期: 7天")
                    print(f"  登录指示器: {', '.join(found_indicators[:5])}...")  # 只显示前5个
                    
                    logger.info("✅ 登录状态保存成功！")
                    return True
                else:
                    print("❌ 登录状态保存验证失败")
                    logger.error("❌ 登录状态保存验证失败")
                    return False
            else:
                print("❌ 未检测到登录指示器")
                print("页面内容可能还在加载中，请稍等...")
                
                # 再等待一下并重试
                time.sleep(5)
                page_source = publisher.driver.page_source
                
                found_indicators = []
                for indicator in login_indicators:
                    if indicator in page_source:
                        found_indicators.append(indicator)
                
                if found_indicators:
                    print(f"🔍 重试后找到登录指示器: {found_indicators}")
                    
                    # 保存登录状态
                    print("💾 正在保存登录状态...")
                    publisher.save_login_state()
                    
                    if publisher.db_service.is_login_state_valid('wechat', expire_hours=168):
                        print("✅ 登录状态保存成功！")
                        return True
                
                print("❌ 未检测到有效的登录状态")
                print("请确保:")
                print("1. 已成功扫码登录微信视频号")
                print("2. 能正常访问创作者中心页面")
                print("3. 页面完全加载完成")
                return False
                
        except Exception as e:
            logger.error(f"检查页面内容时出错: {e}")
            print(f"❌ 检查页面内容时出错: {e}")
            return False
            
    except Exception as e:
        logger.error(f"保存登录状态失败: {e}")
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
    print("💾 保存微信视频号登录状态")
    print("=" * 50)
    
    print("📋 操作说明:")
    print("1. 程序将启动Firefox浏览器")
    print("2. 自动访问微信视频号平台")
    print("3. 如需登录，请在浏览器中扫码")
    print("4. 程序自动检测并保存登录状态")
    
    print("\n⚠️ 重要提醒:")
    print("- 如果您已在其他Firefox窗口登录，可能需要重新登录")
    print("- 登录状态有效期为7天")
    print("- 保存成功后可用于自动发布")
    
    confirm = input("\n确认开始保存登录状态? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 操作已取消")
        return False
    
    # 执行保存操作
    success = save_current_wechat_login()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 微信视频号登录状态保存完成！")
        print("✅ 现在可以使用自动发布功能")
        print("\n🚀 测试自动发布:")
        print("python scripts/simple_hanxin_test.py")
        print("\n💡 提示:")
        print("- 登录状态有效期为7天")
        print("- 可以随时重新运行此脚本更新登录状态")
    else:
        print("❌ 登录状态保存失败")
        print("🔧 请检查网络连接和登录状态后重试")
    
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
