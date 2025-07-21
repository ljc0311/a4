#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试登录数据 - 查看保存的登录状态详细信息
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.publisher_database_service import PublisherDatabaseService
from src.utils.logger import logger

def debug_login_data():
    """调试登录数据"""
    try:
        print("🔍 调试微信视频号登录数据")
        print("=" * 50)
        
        # 创建数据库服务
        db_service = PublisherDatabaseService()
        
        # 检查是否有有效的登录状态
        if not db_service.is_login_state_valid('wechat', expire_hours=168):
            print("❌ 没有有效的登录状态")
            return False
        
        # 加载登录状态
        login_data = db_service.load_login_state('wechat')
        if not login_data:
            print("❌ 登录数据为空")
            return False
        
        print("✅ 找到登录数据")
        print(f"📅 保存时间: {login_data.get('saved_at', 'N/A')}")
        print(f"🌐 页面URL: {login_data.get('current_url', 'N/A')}")
        print(f"📝 页面标题: {login_data.get('page_title', 'N/A')}")
        print()
        
        # 分析Cookies
        cookies = login_data.get('cookies', [])
        print(f"🍪 Cookies ({len(cookies)}个):")
        for i, cookie in enumerate(cookies):
            name = cookie.get('name', 'N/A')
            domain = cookie.get('domain', 'N/A')
            secure = cookie.get('secure', False)
            httpOnly = cookie.get('httpOnly', False)
            print(f"  {i+1}. {name} (domain: {domain}, secure: {secure}, httpOnly: {httpOnly})")
        print()
        
        # 分析LocalStorage
        local_storage = login_data.get('local_storage', {})
        print(f"📦 LocalStorage ({len(local_storage)}个项目):")
        for key, value in local_storage.items():
            value_preview = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
            print(f"  • {key}: {value_preview}")
        print()
        
        # 分析SessionStorage
        session_storage = login_data.get('session_storage', {})
        print(f"📦 SessionStorage ({len(session_storage)}个项目):")
        for key, value in session_storage.items():
            value_preview = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
            print(f"  • {key}: {value_preview}")
        print()
        
        # 查找可能的认证相关键
        print("🔑 可能的认证相关信息:")
        auth_keywords = ['token', 'auth', 'session', 'login', 'user', 'wechat', 'wx', 'ticket', 'access']
        
        found_auth_items = []
        
        # 在cookies中查找
        for cookie in cookies:
            name = cookie.get('name', '').lower()
            if any(keyword in name for keyword in auth_keywords):
                found_auth_items.append(f"Cookie: {cookie.get('name')}")
        
        # 在localStorage中查找
        for key in local_storage.keys():
            if any(keyword in key.lower() for keyword in auth_keywords):
                found_auth_items.append(f"LocalStorage: {key}")
        
        # 在sessionStorage中查找
        for key in session_storage.keys():
            if any(keyword in key.lower() for keyword in auth_keywords):
                found_auth_items.append(f"SessionStorage: {key}")
        
        if found_auth_items:
            for item in found_auth_items:
                print(f"  • {item}")
        else:
            print("  ❌ 未找到明显的认证相关信息")
        
        print()
        print("💡 建议:")
        print("1. 检查是否需要特定的微信认证token")
        print("2. 验证浏览器指纹是否一致")
        print("3. 考虑使用相同的浏览器会话")
        print("4. 检查是否有其他隐藏的认证机制")
        
        return True
        
    except Exception as e:
        logger.error(f"调试登录数据失败: {e}")
        print(f"❌ 调试失败: {e}")
        return False

def main():
    """主函数"""
    print("🔍 微信视频号登录数据调试工具")
    print("=" * 60)
    
    success = debug_login_data()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 登录数据调试完成")
    else:
        print("❌ 登录数据调试失败")
    
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
