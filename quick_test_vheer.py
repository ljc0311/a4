#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vheer.com 快速测试脚本
"""

import asyncio
from vheer_advanced_integration import VheerBrowserIntegration

async def quick_test():
    print("Vheer.com 快速测试")
    
    integration = VheerBrowserIntegration(headless=False)
    
    try:
        if not integration.setup_browser():
            print("❌ 浏览器设置失败")
            return
            
        print("✅ 浏览器设置成功")
        
        # 测试生成
        prompt = "a beautiful sunset over mountains"
        print(f"测试生成: {prompt}")
        
        result = integration.generate_image(prompt)
        
        if result:
            print("✅ 生成成功!")
            for path in result:
                print(f"  图像保存在: {path}")
        else:
            print("❌ 生成失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        
    finally:
        integration.cleanup()

if __name__ == "__main__":
    asyncio.run(quick_test())
