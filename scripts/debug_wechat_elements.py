#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试微信视频号页面元素
实时分析页面结构，找到正确的元素选择器
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.platform_publisher.selenium_wechat_publisher import SeleniumWechatPublisher
from src.utils.logger import logger
from selenium.webdriver.common.by import By

def debug_page_elements():
    """调试页面元素"""
    publisher = None
    try:
        print("🔍 微信视频号页面元素调试")
        print("=" * 60)
        
        # 配置
        config = {
            'driver_type': 'firefox',
            'headless': False,
            'implicit_wait': 5,
            'wechat_proxy_bypass': True,
            'simulation_mode': False
        }
        
        print("🚀 创建微信视频号发布器...")
        publisher = SeleniumWechatPublisher(config)
        
        # 访问发布页面
        print("🌐 访问微信视频号发布页面...")
        publisher.driver.get("https://channels.weixin.qq.com/platform/post/create")
        time.sleep(5)
        
        current_url = publisher.driver.current_url
        page_title = publisher.driver.title
        
        print(f"📄 当前页面: {current_url}")
        print(f"📝 页面标题: {page_title}")
        
        if 'login' in current_url:
            print("❌ 需要登录，请先运行登录脚本")
            return False
        
        print("\n" + "="*60)
        print("🔍 页面元素分析")
        print("="*60)
        
        # 1. 查找所有input元素
        print("\n1️⃣ INPUT元素分析:")
        inputs = publisher.driver.find_elements(By.TAG_NAME, "input")
        print(f"   找到 {len(inputs)} 个input元素")
        
        file_inputs = []
        text_inputs = []
        
        for i, input_elem in enumerate(inputs):
            try:
                input_type = input_elem.get_attribute("type") or "text"
                input_class = input_elem.get_attribute("class") or ""
                input_id = input_elem.get_attribute("id") or ""
                input_placeholder = input_elem.get_attribute("placeholder") or ""
                is_displayed = input_elem.is_displayed()
                is_enabled = input_elem.is_enabled()
                
                print(f"   Input {i+1}: type={input_type}, visible={is_displayed}, enabled={is_enabled}")
                print(f"            class='{input_class[:50]}...' if len(input_class) > 50 else input_class")
                print(f"            id='{input_id}', placeholder='{input_placeholder}'")
                
                if input_type == "file":
                    file_inputs.append((i+1, input_elem))
                elif input_type in ["text", "textarea"] and input_placeholder:
                    text_inputs.append((i+1, input_elem, input_placeholder))
                    
            except Exception as e:
                print(f"   Input {i+1}: 获取属性失败 - {e}")
        
        # 2. 查找所有textarea元素
        print("\n2️⃣ TEXTAREA元素分析:")
        textareas = publisher.driver.find_elements(By.TAG_NAME, "textarea")
        print(f"   找到 {len(textareas)} 个textarea元素")
        
        for i, textarea in enumerate(textareas):
            try:
                textarea_placeholder = textarea.get_attribute("placeholder") or ""
                textarea_class = textarea.get_attribute("class") or ""
                textarea_id = textarea.get_attribute("id") or ""
                is_displayed = textarea.is_displayed()
                is_enabled = textarea.is_enabled()
                
                print(f"   Textarea {i+1}: visible={is_displayed}, enabled={is_enabled}")
                print(f"                class='{textarea_class[:50]}...' if len(textarea_class) > 50 else textarea_class")
                print(f"                id='{textarea_id}', placeholder='{textarea_placeholder}'")
                
            except Exception as e:
                print(f"   Textarea {i+1}: 获取属性失败 - {e}")
        
        # 3. 查找所有button元素
        print("\n3️⃣ BUTTON元素分析:")
        buttons = publisher.driver.find_elements(By.TAG_NAME, "button")
        print(f"   找到 {len(buttons)} 个button元素")
        
        publish_buttons = []
        
        for i, button in enumerate(buttons):
            try:
                button_text = button.text.strip()
                button_class = button.get_attribute("class") or ""
                button_type = button.get_attribute("type") or ""
                is_displayed = button.is_displayed()
                is_enabled = button.is_enabled()
                
                print(f"   Button {i+1}: text='{button_text}', visible={is_displayed}, enabled={is_enabled}")
                print(f"              class='{button_class[:50]}...' if len(button_class) > 50 else button_class")
                print(f"              type='{button_type}'")
                
                if any(keyword in button_text for keyword in ["发布", "发表", "提交", "确定"]):
                    publish_buttons.append((i+1, button, button_text))
                    
            except Exception as e:
                print(f"   Button {i+1}: 获取属性失败 - {e}")
        
        # 4. 查找包含关键词的元素
        print("\n4️⃣ 关键词元素分析:")
        keywords = ["上传", "视频", "文件", "标题", "描述", "发布", "发表", "选择文件", "点击上传"]
        
        for keyword in keywords:
            try:
                elements = publisher.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                if elements:
                    print(f"   包含'{keyword}'的元素: {len(elements)}个")
                    for i, elem in enumerate(elements[:3]):  # 只显示前3个
                        try:
                            tag_name = elem.tag_name
                            elem_text = elem.text[:30] if elem.text else ""
                            elem_class = elem.get_attribute("class") or ""
                            is_displayed = elem.is_displayed()
                            
                            print(f"     {i+1}. <{tag_name}> text='{elem_text}', visible={is_displayed}")
                            print(f"        class='{elem_class[:40]}...' if len(elem_class) > 40 else elem_class")
                        except:
                            pass
            except:
                pass
        
        # 5. 生成建议的选择器
        print("\n" + "="*60)
        print("💡 建议的元素选择器")
        print("="*60)
        
        if file_inputs:
            print("\n📁 文件上传元素:")
            for idx, elem in file_inputs:
                try:
                    xpath = publisher.driver.execute_script("""
                        function getXPath(element) {
                            if (element.id !== '') return "//*[@id='" + element.id + "']";
                            if (element === document.body) return '/html/body';
                            
                            var ix = 0;
                            var siblings = element.parentNode.childNodes;
                            for (var i = 0; i < siblings.length; i++) {
                                var sibling = siblings[i];
                                if (sibling === element) {
                                    return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                                }
                                if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;
                            }
                        }
                        return getXPath(arguments[0]);
                    """, elem)
                    print(f"   Input {idx}: {xpath}")
                except:
                    print(f"   Input {idx}: 无法生成XPath")
        
        if text_inputs:
            print("\n📝 文本输入元素:")
            for idx, elem, placeholder in text_inputs:
                print(f"   Input {idx}: placeholder='{placeholder}'")
        
        if publish_buttons:
            print("\n🚀 发布按钮元素:")
            for idx, elem, text in publish_buttons:
                print(f"   Button {idx}: text='{text}'")
        
        # 6. 交互式测试
        print("\n" + "="*60)
        print("🎮 交互式测试")
        print("="*60)
        print("浏览器将保持打开状态，您可以:")
        print("1. 手动检查页面元素")
        print("2. 使用开发者工具查看元素")
        print("3. 测试元素交互")
        print("\n按回车键继续...")
        input()
        
        return True
        
    except Exception as e:
        logger.error(f"调试失败: {e}")
        print(f"❌ 调试失败: {e}")
        return False
        
    finally:
        if publisher and publisher.driver:
            print("\n🌐 浏览器仍在运行中...")
            keep_open = input("是否保持浏览器打开以便进一步调试? (y/N): ").strip().lower()
            if keep_open != 'y':
                try:
                    publisher.cleanup()
                    print("🧹 清理完成")
                except:
                    pass

def main():
    """主函数"""
    print("🔍 微信视频号页面元素调试工具")
    print("=" * 60)
    
    success = debug_page_elements()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 调试完成")
    else:
        print("❌ 调试失败")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 调试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 调试异常: {e}")
        sys.exit(1)
