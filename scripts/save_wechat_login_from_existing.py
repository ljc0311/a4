#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从现有浏览器会话保存微信视频号登录状态
连接到用户已经登录的浏览器会话来保存登录状态
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.platform_publisher.selenium_wechat_publisher import SeleniumWechatPublisher
from src.utils.logger import logger

def save_from_existing_session():
    """从现有浏览器会话保存登录状态"""
    try:
        logger.info("💾 从现有浏览器会话保存微信视频号登录状态...")
        
        print("📋 操作说明:")
        print("1. 请在您已登录的浏览器中访问微信视频号")
        print("2. 确保能正常看到创作者中心")
        print("3. 保持浏览器窗口打开")
        print("4. 程序将连接到现有会话并保存登录状态")
        
        # 尝试不同的连接方式
        connection_methods = [
            {
                'name': 'Chrome调试模式',
                'config': {
                    'driver_type': 'chrome',
                    'headless': False,
                    'debugger_address': '127.0.0.1:9222',
                    'implicit_wait': 10,
                    'wechat_proxy_bypass': True,
                    'simulation_mode': False
                }
            },
            {
                'name': 'Firefox调试模式',
                'config': {
                    'driver_type': 'firefox',
                    'headless': False,
                    'debugger_address': '127.0.0.1:9222',
                    'implicit_wait': 10,
                    'wechat_proxy_bypass': True,
                    'simulation_mode': False
                }
            }
        ]
        
        for method in connection_methods:
            try:
                logger.info(f"🔗 尝试连接方式: {method['name']}")
                print(f"\n🔗 尝试连接: {method['name']}")
                
                # 创建发布器实例
                publisher = SeleniumWechatPublisher(method['config'])
                
                # 获取所有窗口句柄
                windows = publisher.driver.window_handles
                logger.info(f"🪟 发现 {len(windows)} 个浏览器窗口")
                
                # 遍历所有窗口查找微信视频号
                wechat_window = None
                for window in windows:
                    publisher.driver.switch_to.window(window)
                    current_url = publisher.driver.current_url
                    
                    if 'weixin.qq.com' in current_url or 'channels.weixin.qq.com' in current_url:
                        logger.info(f"✅ 找到微信视频号窗口: {current_url}")
                        wechat_window = window
                        break
                
                if not wechat_window:
                    logger.warning("⚠️ 未找到微信视频号窗口")
                    publisher.cleanup()
                    continue
                
                # 切换到微信视频号窗口
                publisher.driver.switch_to.window(wechat_window)
                current_url = publisher.driver.current_url
                page_title = publisher.driver.title
                
                logger.info(f"📄 当前页面: {current_url}")
                logger.info(f"📝 页面标题: {page_title}")
                
                # 检查登录状态
                if 'login' in current_url or 'passport' in current_url:
                    logger.warning("⚠️ 当前页面是登录页面")
                    publisher.cleanup()
                    continue
                
                # 验证登录状态
                logger.info("🔍 验证登录状态...")
                page_source = publisher.driver.page_source
                
                login_indicators = [
                    '创作者中心', '发布视频', '数据概览', '内容管理',
                    'creator', 'publish', 'dashboard', '我的作品',
                    '视频管理', '粉丝', '收益'
                ]
                
                found_indicators = []
                for indicator in login_indicators:
                    if indicator in page_source:
                        found_indicators.append(indicator)
                
                logger.info(f"🔍 找到登录指示器: {found_indicators}")
                
                if len(found_indicators) >= 2:
                    logger.info("✅ 确认已登录微信视频号")
                    
                    # 保存登录状态
                    logger.info("💾 开始保存登录状态...")
                    publisher.save_login_state()
                    
                    # 验证保存结果
                    if publisher.db_service.is_login_state_valid('wechat', expire_hours=168):
                        logger.info("✅ 登录状态保存成功！")
                        
                        # 显示保存的信息
                        login_data = publisher.db_service.get_login_state('wechat')
                        
                        print(f"\n✅ 登录状态保存成功！")
                        print(f"📋 连接方式: {method['name']}")
                        print(f"📄 页面: {current_url}")
                        print(f"📝 标题: {page_title}")
                        print(f"🍪 Cookies: {len(login_data.get('cookies', []))} 个")
                        print(f"💾 存储数据: {len(login_data.get('local_storage', {}))} 项")
                        print(f"⏰ 有效期: 7天")
                        print(f"🔍 登录指示器: {', '.join(found_indicators)}")
                        
                        publisher.cleanup()
                        return True
                    else:
                        logger.error("❌ 登录状态保存验证失败")
                        publisher.cleanup()
                        continue
                else:
                    logger.warning("⚠️ 登录状态不确定")
                    publisher.cleanup()
                    continue
                    
            except Exception as e:
                logger.warning(f"连接方式 {method['name']} 失败: {e}")
                try:
                    if 'publisher' in locals():
                        publisher.cleanup()
                except:
                    pass
                continue
        
        # 如果所有方法都失败了
        logger.error("❌ 所有连接方式都失败了")
        return False
        
    except Exception as e:
        logger.error(f"保存登录状态失败: {e}")
        return False

def manual_save_instructions():
    """显示手动保存说明"""
    print("\n📋 手动保存登录状态说明:")
    print("=" * 50)
    print("如果自动连接失败，请按以下步骤手动操作:")
    print()
    print("方法1: Chrome调试模式")
    print("1. 关闭所有Chrome窗口")
    print("2. 启动Chrome调试模式:")
    print("   chrome.exe --remote-debugging-port=9222 --user-data-dir=selenium")
    print("3. 在Chrome中登录微信视频号")
    print("4. 重新运行此脚本")
    print()
    print("方法2: 直接在新窗口登录")
    print("1. 运行脚本时会打开新的浏览器窗口")
    print("2. 在新窗口中扫码登录微信视频号")
    print("3. 登录成功后脚本会自动保存状态")
    print()
    print("方法3: 使用现有Firefox会话")
    print("1. 在Firefox中登录微信视频号")
    print("2. 保持Firefox窗口打开")
    print("3. 运行脚本连接到现有会话")

def main():
    """主函数"""
    print("💾 从现有会话保存微信视频号登录状态")
    print("=" * 60)
    
    print("⚠️ 重要说明:")
    print("- 此脚本会尝试连接到您已登录的浏览器")
    print("- 请确保微信视频号已在浏览器中登录")
    print("- 支持Chrome和Firefox浏览器")
    print("- 登录状态有效期为7天")
    
    confirm = input("\n确认开始保存登录状态? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 操作已取消")
        manual_save_instructions()
        return False
    
    # 执行保存操作
    success = save_from_existing_session()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 登录状态保存完成！")
        print("✅ 现在可以使用自动发布功能")
        print("💡 下次发布时将自动使用保存的登录状态")
        print("\n🚀 可以运行以下命令测试发布:")
        print("python scripts/simple_hanxin_test.py")
    else:
        print("❌ 登录状态保存失败")
        manual_save_instructions()
    
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
