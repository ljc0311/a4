#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动保存微信视频号登录信息
通过手动输入cookies等信息来保存登录状态
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.publisher_database_service import PublisherDatabaseService
from src.utils.logger import logger

def manual_save_login_info():
    """手动保存登录信息"""
    try:
        print("📋 手动保存微信视频号登录信息")
        print("=" * 50)
        
        print("📱 请在您已登录的Firefox浏览器中执行以下操作:")
        print("1. 按F12打开开发者工具")
        print("2. 切换到Console(控制台)标签")
        print("3. 复制并执行以下JavaScript代码:")
        print()
        
        js_code = '''
// 获取所有cookies
var cookies = document.cookie.split(';').map(function(cookie) {
    var parts = cookie.trim().split('=');
    return {
        name: parts[0],
        value: parts.slice(1).join('='),
        domain: window.location.hostname,
        path: '/',
        secure: window.location.protocol === 'https:',
        httpOnly: false
    };
});

// 获取localStorage
var localStorage_data = {};
for (var i = 0; i < localStorage.length; i++) {
    var key = localStorage.key(i);
    localStorage_data[key] = localStorage.getItem(key);
}

// 获取sessionStorage
var sessionStorage_data = {};
for (var i = 0; i < sessionStorage.length; i++) {
    var key = sessionStorage.key(i);
    sessionStorage_data[key] = sessionStorage.getItem(key);
}

// 输出结果
var result = {
    cookies: cookies,
    localStorage: localStorage_data,
    sessionStorage: sessionStorage_data,
    url: window.location.href,
    title: document.title
};

console.log("=== 微信视频号登录信息 ===");
console.log(JSON.stringify(result, null, 2));
console.log("=== 复制上面的JSON数据 ===");
'''
        
        print("```javascript")
        print(js_code)
        print("```")
        
        print("\n4. 复制控制台输出的JSON数据")
        print("5. 回到此窗口粘贴JSON数据")
        print("6. 按回车键完成保存")
        
        print("\n" + "=" * 50)
        print("请粘贴从浏览器控制台复制的JSON数据:")
        print("(粘贴完成后按回车键)")
        
        # 读取多行输入
        lines = []
        print("开始输入JSON数据 (输入'END'结束):")
        
        while True:
            try:
                line = input()
                if line.strip() == 'END':
                    break
                lines.append(line)
            except EOFError:
                break
        
        json_data = '\n'.join(lines)
        
        if not json_data.strip():
            print("❌ 未输入任何数据")
            return False
        
        # 解析JSON数据
        try:
            login_info = json.loads(json_data)
            
            print("✅ JSON数据解析成功")
            print(f"📄 页面: {login_info.get('url', 'N/A')}")
            print(f"📝 标题: {login_info.get('title', 'N/A')}")
            print(f"🍪 Cookies: {len(login_info.get('cookies', []))} 个")
            print(f"💾 LocalStorage: {len(login_info.get('localStorage', {}))} 项")
            print(f"📦 SessionStorage: {len(login_info.get('sessionStorage', {}))} 项")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON数据格式错误: {e}")
            return False
        
        # 验证数据
        if not login_info.get('cookies'):
            print("⚠️ 警告: 未找到cookies数据")
        
        if 'weixin.qq.com' not in login_info.get('url', ''):
            print("⚠️ 警告: URL不是微信视频号域名")
        
        # 保存到数据库
        print("\n💾 正在保存登录状态...")
        
        db_service = PublisherDatabaseService()
        
        # 准备保存的数据
        save_data = {
            'platform': 'wechat',
            'cookies': login_info.get('cookies', []),
            'local_storage': login_info.get('localStorage', {}),
            'session_storage': login_info.get('sessionStorage', {}),
            'current_url': login_info.get('url', ''),
            'page_title': login_info.get('title', ''),
            'manual_save': True,
            'save_time': datetime.now().isoformat()
        }
        
        success = db_service.save_login_state('wechat', save_data)
        
        if success and db_service.is_login_state_valid('wechat', expire_hours=168):
            print("🎉 登录状态保存成功！")
            print("📋 保存信息:")
            print(f"  平台: 微信视频号")
            print(f"  页面: {save_data['current_url']}")
            print(f"  标题: {save_data['page_title']}")
            print(f"  Cookies: {len(save_data['cookies'])} 个")
            print(f"  LocalStorage: {len(save_data['local_storage'])} 项")
            print(f"  SessionStorage: {len(save_data['session_storage'])} 项")
            print(f"  有效期: 7天")
            print(f"  保存方式: 手动保存")
            
            logger.info("✅ 手动保存登录状态成功")
            return True
        else:
            print("❌ 登录状态保存失败")
            logger.error("❌ 手动保存登录状态失败")
            return False
            
    except Exception as e:
        logger.error(f"手动保存登录状态失败: {e}")
        print(f"❌ 操作失败: {e}")
        return False

def main():
    """主函数"""
    print("📱 微信视频号登录状态手动保存工具")
    print("=" * 60)
    
    print("💡 使用说明:")
    print("- 此工具通过手动复制浏览器数据来保存登录状态")
    print("- 适用于已经登录但自动保存失败的情况")
    print("- 需要在浏览器开发者工具中执行JavaScript代码")
    print("- 保存的登录状态有效期为7天")
    
    confirm = input("\n确认开始手动保存? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 操作已取消")
        return False
    
    # 执行手动保存
    success = manual_save_login_info()
    
    print("\n" + "=" * 60)
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
        print("🔧 请检查输入的数据格式是否正确")
    
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
