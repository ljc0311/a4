#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版微信视频号页面调试
处理动态加载内容，等待页面完全加载
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def wait_for_dynamic_content(driver, timeout=30):
    """等待动态内容加载"""
    print("⏳ 等待页面动态内容加载...")
    
    # 等待策略1: 等待特定元素出现
    wait_conditions = [
        "input[type='file']",
        "textarea",
        "[data-testid*='upload']",
        "[class*='upload']",
        "[class*='file']",
        ".upload-area",
        ".file-input",
        ".video-upload"
    ]
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        for condition in wait_conditions:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, condition)
                if elements:
                    print(f"✅ 检测到动态内容: {condition} ({len(elements)}个元素)")
                    return True
            except:
                pass
        
        # 检查页面是否还在加载
        ready_state = driver.execute_script("return document.readyState")
        if ready_state != "complete":
            print(f"📄 页面状态: {ready_state}")
        
        time.sleep(2)
    
    print("⚠️ 动态内容加载超时，继续分析当前页面")
    return False

def analyze_page_structure(driver):
    """分析页面结构"""
    print("\n🔍 深度页面结构分析")
    print("="*50)
    
    # 1. 检查iframe
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"🖼️ 发现 {len(iframes)} 个iframe")
    
    for i, iframe in enumerate(iframes):
        try:
            src = iframe.get_attribute("src") or "无src"
            print(f"   iframe {i+1}: {src}")
        except:
            pass
    
    # 2. 检查shadow DOM
    try:
        shadow_hosts = driver.execute_script("""
            var hosts = [];
            var walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_ELEMENT,
                null,
                false
            );
            var node;
            while (node = walker.nextNode()) {
                if (node.shadowRoot) {
                    hosts.push(node.tagName + (node.className ? '.' + node.className.split(' ')[0] : ''));
                }
            }
            return hosts;
        """)
        if shadow_hosts:
            print(f"🌑 发现 {len(shadow_hosts)} 个Shadow DOM: {shadow_hosts}")
    except:
        pass
    
    # 3. 检查所有可能的上传相关元素
    upload_selectors = [
        "[data-testid*='upload']",
        "[data-testid*='file']",
        "[class*='upload']",
        "[class*='file']",
        "[class*='drop']",
        "[id*='upload']",
        "[id*='file']",
        "input[type='file']",
        "input[accept*='video']",
        "input[accept*='mp4']"
    ]
    
    print("\n📁 上传元素搜索:")
    found_elements = []
    
    for selector in upload_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"   ✅ {selector}: {len(elements)}个元素")
                for j, elem in enumerate(elements[:3]):
                    try:
                        tag = elem.tag_name
                        classes = elem.get_attribute("class") or ""
                        style = elem.get_attribute("style") or ""
                        visible = elem.is_displayed()
                        print(f"      {j+1}. <{tag}> visible={visible}")
                        print(f"         class='{classes[:40]}...' if len(classes) > 40 else classes")
                        if "display: none" in style or "visibility: hidden" in style:
                            print(f"         style='{style[:40]}...' if len(style) > 40 else style")
                        found_elements.append((selector, elem))
                    except:
                        pass
        except:
            pass
    
    return found_elements

def test_upload_methods(driver, found_elements):
    """测试上传方法"""
    print("\n🧪 测试上传方法")
    print("="*50)
    
    # 测试文件路径
    test_file = Path.cwd() / "output" / "韩信" / "final_video.mp4"
    if not test_file.exists():
        print("❌ 测试文件不存在，跳过上传测试")
        return
    
    print(f"📁 测试文件: {test_file}")
    
    for selector, element in found_elements[:3]:  # 只测试前3个
        try:
            print(f"\n🎯 测试元素: {selector}")
            
            # 方法1: 直接发送文件路径
            try:
                element.send_keys(str(test_file))
                print("   ✅ 直接发送文件路径成功")
                time.sleep(2)
                
                # 检查是否有上传进度或成功指示
                upload_indicators = driver.find_elements(By.CSS_SELECTOR, 
                    "[class*='progress'], [class*='uploading'], [class*='success']")
                if upload_indicators:
                    print(f"   📊 检测到上传指示器: {len(upload_indicators)}个")
                
                return True
                
            except Exception as e:
                print(f"   ❌ 直接发送失败: {e}")
            
            # 方法2: 点击后发送文件
            try:
                element.click()
                time.sleep(1)
                element.send_keys(str(test_file))
                print("   ✅ 点击后发送文件成功")
                time.sleep(2)
                return True
                
            except Exception as e:
                print(f"   ❌ 点击后发送失败: {e}")
                
        except Exception as e:
            print(f"   ❌ 测试失败: {e}")
    
    return False

def debug_enhanced_wechat():
    """增强版微信调试"""
    publisher = None
    try:
        print("🔍 增强版微信视频号调试")
        print("=" * 60)
        
        # 配置
        config = {
            'driver_type': 'firefox',
            'headless': False,
            'implicit_wait': 10,
            'page_load_timeout': 60,
            'wechat_proxy_bypass': True,
            'simulation_mode': False
        }
        
        print("🚀 创建微信视频号发布器...")
        publisher = SeleniumWechatPublisher(config)
        
        # 访问发布页面
        print("🌐 访问微信视频号发布页面...")
        publisher.driver.get("https://channels.weixin.qq.com/platform/post/create")
        
        # 等待页面基本加载
        time.sleep(5)
        
        current_url = publisher.driver.current_url
        page_title = publisher.driver.title
        
        print(f"📄 当前页面: {current_url}")
        print(f"📝 页面标题: {page_title}")
        
        if 'login' in current_url:
            print("❌ 需要登录，请先运行登录脚本")
            return False
        
        # 等待动态内容加载
        wait_for_dynamic_content(publisher.driver)
        
        # 分析页面结构
        found_elements = analyze_page_structure(publisher.driver)
        
        if found_elements:
            print(f"\n✅ 找到 {len(found_elements)} 个潜在的上传元素")
            
            # 测试上传方法
            if test_upload_methods(publisher.driver, found_elements):
                print("\n🎉 找到可用的上传方法！")
            else:
                print("\n⚠️ 所有上传方法测试失败")
        else:
            print("\n❌ 未找到任何上传元素")
        
        # 生成JavaScript调试代码
        print("\n" + "="*60)
        print("🔧 JavaScript调试代码")
        print("="*60)
        
        js_debug = """
// 在浏览器控制台运行以下代码来查找上传元素:

// 1. 查找所有input元素
console.log('=== INPUT元素 ===');
document.querySelectorAll('input').forEach((input, i) => {
    console.log(`Input ${i+1}:`, {
        type: input.type,
        accept: input.accept,
        class: input.className,
        id: input.id,
        visible: input.offsetParent !== null
    });
});

// 2. 查找所有包含upload的元素
console.log('=== UPLOAD相关元素 ===');
document.querySelectorAll('[class*="upload"], [id*="upload"], [data-testid*="upload"]').forEach((elem, i) => {
    console.log(`Upload ${i+1}:`, {
        tag: elem.tagName,
        class: elem.className,
        id: elem.id,
        text: elem.textContent.slice(0, 50),
        visible: elem.offsetParent !== null
    });
});

// 3. 查找所有可点击的上传区域
console.log('=== 可点击区域 ===');
document.querySelectorAll('[role="button"], button, .clickable, [onclick]').forEach((elem, i) => {
    if (elem.textContent.includes('上传') || elem.textContent.includes('选择') || elem.textContent.includes('文件')) {
        console.log(`Clickable ${i+1}:`, {
            tag: elem.tagName,
            text: elem.textContent.slice(0, 30),
            class: elem.className,
            visible: elem.offsetParent !== null
        });
    }
});
        """
        
        print(js_debug)
        
        # 保持浏览器打开
        print("\n" + "="*60)
        print("🎮 交互式调试")
        print("="*60)
        print("浏览器将保持打开状态，您可以:")
        print("1. 在开发者工具控制台运行上面的JavaScript代码")
        print("2. 手动检查页面元素")
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
    print("🔍 增强版微信视频号调试工具")
    print("=" * 60)
    
    success = debug_enhanced_wechat()
    
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
