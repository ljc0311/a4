#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
保存微信视频号登录状态
用于保存用户手动登录后的状态，以便后续自动使用
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.platform_publisher.selenium_wechat_publisher import SeleniumWechatPublisher
from src.utils.logger import logger

def save_current_login_state():
    """保存当前的微信视频号登录状态"""
    try:
        logger.info("💾 开始保存微信视频号登录状态...")
        
        # 配置 - 连接到现有的浏览器会话
        config = {
            'driver_type': 'firefox',
            'headless': False,
            'debugger_address': '127.0.0.1:9222',  # 如果有调试模式
            'implicit_wait': 10,
            'wechat_proxy_bypass': True,
            'no_proxy_domains': ['weixin.qq.com', 'channels.weixin.qq.com'],
            'simulation_mode': False
        }
        
        # 创建发布器实例
        logger.info("🚀 创建微信视频号发布器实例...")
        publisher = SeleniumWechatPublisher(config)
        
        # 访问微信视频号平台验证登录状态
        logger.info("🌐 访问微信视频号平台验证登录状态...")
        publisher.driver.get("https://channels.weixin.qq.com/platform")
        time.sleep(3)
        
        # 检查当前页面
        current_url = publisher.driver.current_url
        page_title = publisher.driver.title
        
        logger.info(f"📄 当前页面: {current_url}")
        logger.info(f"📝 页面标题: {page_title}")
        
        # 检查是否已登录
        if 'login' in current_url or 'passport' in current_url:
            logger.error("❌ 检测到登录页面，请先手动登录微信视频号")
            print("\n❌ 未检测到登录状态")
            print("请按以下步骤操作:")
            print("1. 在浏览器中访问 https://channels.weixin.qq.com")
            print("2. 扫码登录微信视频号")
            print("3. 确保能正常访问创作者平台")
            print("4. 重新运行此脚本")
            return False
        
        # 进一步验证登录状态
        logger.info("🔍 验证登录状态...")
        
        # 检查页面内容
        try:
            page_source = publisher.driver.page_source
            
            # 检查登录相关的关键词
            login_indicators = [
                '创作者中心', '发布视频', '数据概览', '内容管理',
                'creator', 'publish', 'dashboard', '我的作品'
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
                    if login_data:
                        logger.info(f"📊 保存的登录信息:")
                        logger.info(f"  平台: {login_data.get('platform', 'N/A')}")
                        logger.info(f"  保存时间: {login_data.get('created_at', 'N/A')}")
                        logger.info(f"  Cookies数量: {len(login_data.get('cookies', []))}")
                        logger.info(f"  LocalStorage项目: {len(login_data.get('local_storage', {}))}")
                    
                    print("\n✅ 微信视频号登录状态保存成功！")
                    print("📋 保存信息:")
                    print(f"  平台: 微信视频号")
                    print(f"  有效期: 7天")
                    print(f"  Cookies: {len(login_data.get('cookies', []))} 个")
                    print(f"  存储数据: {len(login_data.get('local_storage', {}))} 项")
                    print("\n💡 现在可以使用自动发布功能，无需重复登录！")
                    
                    return True
                else:
                    logger.error("❌ 登录状态保存验证失败")
                    return False
            else:
                logger.warning("⚠️ 登录状态不确定，可能需要重新登录")
                print("\n⚠️ 登录状态不确定")
                print("请确保:")
                print("1. 已成功登录微信视频号")
                print("2. 能正常访问创作者中心")
                print("3. 页面完全加载完成")
                return False
                
        except Exception as e:
            logger.error(f"验证登录状态时出错: {e}")
            return False
            
    except Exception as e:
        logger.error(f"保存登录状态失败: {e}")
        print(f"\n❌ 保存登录状态失败: {e}")
        return False
        
    finally:
        # 清理资源
        try:
            if 'publisher' in locals():
                publisher.cleanup()
                logger.info("🧹 资源清理完成")
        except:
            pass

def check_existing_login_state():
    """检查现有的登录状态"""
    try:
        logger.info("🔍 检查现有的微信视频号登录状态...")
        
        # 创建临时发布器实例来访问数据库服务
        config = {'simulation_mode': True}
        publisher = SeleniumWechatPublisher(config)
        
        # 检查登录状态
        if publisher.db_service.is_login_state_valid('wechat', expire_hours=168):
            login_data = publisher.db_service.get_login_state('wechat')
            
            print("✅ 发现有效的登录状态:")
            print(f"  保存时间: {login_data.get('created_at', 'N/A')}")
            print(f"  Cookies数量: {len(login_data.get('cookies', []))}")
            print(f"  LocalStorage项目: {len(login_data.get('local_storage', {}))}")
            
            return True
        else:
            print("❌ 没有有效的登录状态")
            return False
            
    except Exception as e:
        logger.error(f"检查登录状态失败: {e}")
        return False

def main():
    """主函数"""
    print("💾 微信视频号登录状态保存工具")
    print("=" * 50)
    
    # 检查现有登录状态
    print("🔍 检查现有登录状态...")
    has_existing = check_existing_login_state()
    
    if has_existing:
        print("\n⚠️ 已存在有效的登录状态")
        choice = input("是否要覆盖现有状态? (y/N): ").strip().lower()
        if choice != 'y':
            print("❌ 操作已取消")
            return False
    
    print("\n📋 操作说明:")
    print("1. 请确保已在浏览器中登录微信视频号")
    print("2. 访问 https://channels.weixin.qq.com/platform")
    print("3. 确认能正常看到创作者中心界面")
    print("4. 然后运行此脚本保存登录状态")
    
    print("\n⚠️ 重要提醒:")
    print("- 此操作会启动新的浏览器窗口")
    print("- 请确保微信视频号已登录")
    print("- 登录状态有效期为7天")
    
    confirm = input("\n确认开始保存登录状态? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 操作已取消")
        return False
    
    # 执行保存操作
    success = save_current_login_state()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 登录状态保存完成！")
        print("✅ 现在可以使用自动发布功能")
        print("💡 下次发布时将自动使用保存的登录状态")
    else:
        print("❌ 登录状态保存失败")
        print("🔧 请检查登录状态并重试")
    
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
