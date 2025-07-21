#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在手动登录后保存微信视频号登录状态
连接到已经打开的Firefox浏览器并保存登录状态
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from src.utils.logger import logger
from src.services.publisher_database_service import PublisherDatabaseService

def save_login_from_open_browser():
    """从已打开的浏览器保存登录状态"""
    driver = None
    try:
        logger.info("🔗 连接到已打开的Firefox浏览器...")
        
        # 创建Firefox选项
        options = FirefoxOptions()
        
        # 尝试连接到现有的Firefox实例
        try:
            # 方法1: 尝试连接到调试端口
            options.add_argument("--marionette-port=2828")
            driver = webdriver.Firefox(options=options)
        except:
            try:
                # 方法2: 创建新的连接
                driver = webdriver.Firefox(options=options)
            except Exception as e:
                logger.error(f"无法连接到Firefox: {e}")
                return False
        
        logger.info("✅ 成功连接到Firefox浏览器")
        
        # 获取所有窗口
        windows = driver.window_handles
        logger.info(f"🪟 发现 {len(windows)} 个浏览器窗口")
        
        # 查找微信视频号窗口
        wechat_window = None
        for window in windows:
            driver.switch_to.window(window)
            current_url = driver.current_url
            
            if 'weixin.qq.com' in current_url or 'channels.weixin.qq.com' in current_url:
                logger.info(f"✅ 找到微信视频号窗口: {current_url}")
                wechat_window = window
                break
        
        if not wechat_window:
            # 如果没找到，访问微信视频号
            logger.info("🌐 访问微信视频号平台...")
            driver.get("https://channels.weixin.qq.com/platform")
            time.sleep(3)
        
        # 检查当前页面
        current_url = driver.current_url
        page_title = driver.title
        
        logger.info(f"📄 当前页面: {current_url}")
        logger.info(f"📝 页面标题: {page_title}")
        
        print(f"📄 当前页面: {current_url}")
        print(f"📝 页面标题: {page_title}")
        
        # 检查是否已登录
        if 'login' in current_url or 'passport' in current_url:
            print("❌ 检测到登录页面，请先完成登录")
            return False
        
        # 检查页面内容验证登录状态
        page_source = driver.page_source
        
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
        
        if len(found_indicators) >= 1:
            print("✅ 确认已登录微信视频号")
            logger.info("✅ 确认已登录微信视频号")
            
            # 保存登录状态
            print("💾 正在保存登录状态...")
            logger.info("💾 开始保存登录状态...")
            
            # 创建数据服务
            db_service = PublisherDatabaseService()
            
            # 获取cookies
            cookies = driver.get_cookies()
            
            # 获取localStorage
            local_storage = {}
            try:
                local_storage = driver.execute_script("""
                    var storage = {};
                    for (var i = 0; i < localStorage.length; i++) {
                        var key = localStorage.key(i);
                        storage[key] = localStorage.getItem(key);
                    }
                    return storage;
                """)
            except:
                pass
            
            # 获取sessionStorage
            session_storage = {}
            try:
                session_storage = driver.execute_script("""
                    var storage = {};
                    for (var i = 0; i < sessionStorage.length; i++) {
                        var key = sessionStorage.key(i);
                        storage[key] = sessionStorage.getItem(key);
                    }
                    return storage;
                """)
            except:
                pass
            
            # 保存登录状态
            login_data = {
                'platform': 'wechat',
                'cookies': cookies,
                'local_storage': local_storage,
                'session_storage': session_storage,
                'current_url': current_url,
                'page_title': page_title
            }
            
            success = db_service.save_login_state('wechat', login_data)
            
            if success and db_service.is_login_state_valid('wechat', expire_hours=168):
                print("\n🎉 登录状态保存成功！")
                print("📋 保存信息:")
                print(f"  平台: 微信视频号")
                print(f"  页面: {current_url}")
                print(f"  标题: {page_title}")
                print(f"  Cookies: {len(cookies)} 个")
                print(f"  LocalStorage: {len(local_storage)} 项")
                print(f"  SessionStorage: {len(session_storage)} 项")
                print(f"  有效期: 7天")
                print(f"  登录指示器: {', '.join(found_indicators)}")
                
                logger.info("✅ 登录状态保存成功！")
                return True
            else:
                print("❌ 登录状态保存失败")
                logger.error("❌ 登录状态保存失败")
                return False
        else:
            print("❌ 未检测到有效的登录状态")
            print("请确保:")
            print("1. 已成功扫码登录微信视频号")
            print("2. 能正常访问创作者中心页面")
            print("3. 页面完全加载完成")
            return False
            
    except Exception as e:
        logger.error(f"保存登录状态失败: {e}")
        print(f"❌ 操作失败: {e}")
        return False
        
    finally:
        # 不关闭浏览器，让用户继续使用
        if driver:
            print("\n🌐 浏览器保持打开状态")
            print("💡 您可以继续在浏览器中使用微信视频号")

def main():
    """主函数"""
    print("💾 保存微信视频号登录状态")
    print("=" * 50)
    
    print("📋 前提条件:")
    print("1. Firefox浏览器已打开")
    print("2. 已在浏览器中登录微信视频号")
    print("3. 能正常访问创作者中心")
    
    confirm = input("\n确认已完成登录? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 请先完成登录后再运行此脚本")
        return False
    
    # 执行保存操作
    success = save_login_from_open_browser()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 微信视频号登录状态保存完成！")
        print("✅ 现在可以使用自动发布功能")
        print("\n🚀 测试自动发布:")
        print("python scripts/simple_hanxin_test.py")
    else:
        print("❌ 登录状态保存失败")
        print("🔧 请检查登录状态后重试")
    
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
