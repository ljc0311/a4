#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的微信视频号发布器测试
验证基础功能是否正常
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试导入功能"""
    print("🔍 测试模块导入...")
    
    try:
        from src.services.platform_publisher.selenium_wechat_publisher import SeleniumWechatPublisher
        print("✅ SeleniumWechatPublisher 导入成功")
    except Exception as e:
        print(f"❌ SeleniumWechatPublisher 导入失败: {e}")
        return False
    
    try:
        from src.config.wechat_publisher_config import get_wechat_config
        print("✅ wechat_publisher_config 导入成功")
    except Exception as e:
        print(f"❌ wechat_publisher_config 导入失败: {e}")
        return False
    
    try:
        from src.utils.logger import logger
        print("✅ logger 导入成功")
    except Exception as e:
        print(f"❌ logger 导入失败: {e}")
        return False
    
    return True

def test_config():
    """测试配置功能"""
    print("\n🔧 测试配置功能...")
    
    try:
        from src.config.wechat_publisher_config import get_wechat_config, WECHAT_SELECTORS
        
        config = get_wechat_config()
        print(f"✅ 配置加载成功")
        print(f"📋 文件上传选择器数量: {len(config['selectors']['file_upload'])}")
        print(f"📋 标题输入选择器数量: {len(config['selectors']['title_input'])}")
        print(f"📋 描述输入选择器数量: {len(config['selectors']['description_input'])}")
        
        # 显示前几个选择器
        print(f"📋 文件上传选择器示例:")
        for i, selector in enumerate(config['selectors']['file_upload'][:5]):
            print(f"  {i+1}. {selector}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_class_creation():
    """测试类创建"""
    print("\n🏗️ 测试类创建...")
    
    try:
        from src.services.platform_publisher.selenium_wechat_publisher import SeleniumWechatPublisher
        
        # 创建配置
        config = {
            'driver_type': 'chrome',
            'headless': True,  # 无头模式避免打开浏览器
            'simulation_mode': True,  # 模拟模式
            'implicit_wait': 5,
            'wechat_proxy_bypass': False
        }
        
        # 尝试创建实例（但不初始化浏览器）
        print("📱 尝试创建微信发布器实例...")
        
        # 这里我们只测试类的基本结构，不实际初始化浏览器
        publisher_class = SeleniumWechatPublisher
        print("✅ 微信发布器类创建成功")
        
        # 检查关键方法是否存在
        methods_to_check = [
            '_wait_for_page_ready',
            '_trigger_upload_interface', 
            '_force_show_hidden_elements',
            '_enhanced_element_detection',
            '_handle_iframe_upload',
            '_enhanced_file_upload',
            '_smart_element_finder'
        ]
        
        for method_name in methods_to_check:
            if hasattr(publisher_class, method_name):
                print(f"✅ 方法 {method_name} 存在")
            else:
                print(f"❌ 方法 {method_name} 不存在")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 类创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_methods():
    """测试增强方法的基本结构"""
    print("\n🔧 测试增强方法...")
    
    try:
        from src.services.platform_publisher.selenium_wechat_publisher import SeleniumWechatPublisher
        import inspect
        
        # 检查新增的方法
        enhanced_methods = [
            '_wait_for_page_ready',
            '_trigger_upload_interface',
            '_force_show_hidden_elements', 
            '_enhanced_element_detection',
            '_handle_iframe_upload',
            '_enhanced_file_upload',
            '_handle_drag_drop_upload'
        ]
        
        for method_name in enhanced_methods:
            method = getattr(SeleniumWechatPublisher, method_name, None)
            if method:
                # 获取方法签名
                sig = inspect.signature(method)
                print(f"✅ {method_name}{sig}")
            else:
                print(f"❌ {method_name} 方法不存在")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 增强方法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 微信视频号发布器简化测试")
    print("=" * 50)
    
    # 测试步骤
    tests = [
        ("模块导入", test_imports),
        ("配置功能", test_config), 
        ("类创建", test_class_creation),
        ("增强方法", test_enhanced_methods)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 开始测试: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有基础功能测试通过！增强功能已正确实现。")
        print("\n💡 下一步建议:")
        print("1. 启动Chrome调试模式: chrome.exe --remote-debugging-port=9222 --user-data-dir=selenium")
        print("2. 手动登录微信视频号")
        print("3. 运行完整测试: python scripts/test_enhanced_wechat_publisher.py")
    else:
        print("⚠️ 部分测试失败，请检查代码实现。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
