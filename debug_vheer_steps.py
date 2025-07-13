#!/usr/bin/env python3
"""
调试Vheer.com各个步骤的测试脚本
逐步测试每个功能点
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_browser_setup():
    """测试浏览器设置"""
    print("🌐 测试浏览器设置...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # 配置Chrome选项
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        # 不使用headless模式，这样可以看到实际操作
        # options.add_argument('--headless')
        
        print("🚀 启动Chrome浏览器...")
        driver = webdriver.Chrome(options=options)
        
        print("✅ 浏览器启动成功")
        
        # 访问Vheer页面
        print("📖 访问Vheer页面...")
        driver.get("https://vheer.com/app/image-to-video")
        
        # 等待页面加载
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        print(f"✅ 页面加载完成: {driver.title}")
        print(f"🔗 当前URL: {driver.current_url}")
        
        # 等待用户观察
        input("按Enter继续...")
        
        # 查找上传元素
        print("🔍 查找上传元素...")
        upload_elements = driver.find_elements(By.CSS_SELECTOR, "input[type='file'], [class*='upload'], [class*='drop']")
        print(f"找到 {len(upload_elements)} 个上传相关元素")
        
        for i, elem in enumerate(upload_elements):
            try:
                tag = elem.tag_name
                classes = elem.get_attribute('class') or ''
                visible = elem.is_displayed()
                print(f"  元素{i+1}: <{tag}> class='{classes}' visible={visible}")
            except:
                pass
        
        # 查找Generate按钮
        print("\n🔍 查找Generate按钮...")
        generate_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Generate')]")
        print(f"找到 {len(generate_buttons)} 个Generate按钮")
        
        for i, btn in enumerate(generate_buttons):
            try:
                text = btn.text
                classes = btn.get_attribute('class') or ''
                visible = btn.is_displayed()
                enabled = btn.is_enabled()
                print(f"  按钮{i+1}: '{text}' class='{classes}' visible={visible} enabled={enabled}")
            except:
                pass
        
        # 等待用户观察
        input("按Enter关闭浏览器...")
        
        driver.quit()
        print("✅ 浏览器测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 浏览器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_image_upload():
    """测试图片上传功能"""
    print("\n📤 测试图片上传功能...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from PIL import Image
        import tempfile
        
        # 创建测试图片
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            img = Image.new('RGB', (400, 300), color='red')
            img.save(tmp_file.name, 'JPEG')
            test_image_path = tmp_file.name
        
        print(f"📷 测试图片已创建: {test_image_path}")
        
        # 启动浏览器
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(options=options)
        driver.get("https://vheer.com/app/image-to-video")
        
        # 等待页面加载
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        await asyncio.sleep(3)
        
        # 查找文件输入元素
        file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        
        if file_inputs:
            print(f"✅ 找到 {len(file_inputs)} 个文件输入元素")
            
            # 尝试上传文件
            file_input = file_inputs[0]
            file_input.send_keys(test_image_path)
            
            print("✅ 文件上传命令已发送")
            
            # 等待上传处理
            await asyncio.sleep(5)
            
            # 检查是否有图片预览
            images = driver.find_elements(By.CSS_SELECTOR, "img")
            print(f"页面中有 {len(images)} 个图片元素")
            
        else:
            print("❌ 未找到文件输入元素")
        
        input("按Enter继续...")
        
        driver.quit()
        os.unlink(test_image_path)  # 删除临时文件
        
        return True
        
    except Exception as e:
        print(f"❌ 图片上传测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_generate_button():
    """测试Generate按钮点击"""
    print("\n🎬 测试Generate按钮点击...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(options=options)
        driver.get("https://vheer.com/app/image-to-video")
        
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        await asyncio.sleep(3)
        
        # 查找Generate按钮
        generate_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Generate')]")
        
        if generate_buttons:
            button = generate_buttons[-1]  # 选择最后一个（通常是主要按钮）
            
            print(f"✅ 找到Generate按钮: '{button.text}'")
            print(f"   可见: {button.is_displayed()}")
            print(f"   可点击: {button.is_enabled()}")
            
            if button.is_displayed() and button.is_enabled():
                # 滚动到按钮位置
                driver.execute_script("arguments[0].scrollIntoView();", button)
                await asyncio.sleep(1)
                
                print("🖱️  尝试点击Generate按钮...")
                try:
                    button.click()
                    print("✅ 按钮点击成功")
                except:
                    # 尝试JavaScript点击
                    driver.execute_script("arguments[0].click();", button)
                    print("✅ JavaScript点击成功")
                
                # 等待反应
                await asyncio.sleep(3)
                
                # 检查页面变化
                print("🔍 检查页面变化...")
                
            else:
                print("❌ 按钮不可点击")
        else:
            print("❌ 未找到Generate按钮")
        
        input("按Enter继续...")
        driver.quit()
        
        return True
        
    except Exception as e:
        print(f"❌ Generate按钮测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🧪 Vheer.com 分步调试测试")
    print("=" * 50)
    
    tests = [
        ("浏览器设置", test_browser_setup),
        ("图片上传", test_image_upload),
        ("Generate按钮", test_generate_button),
    ]
    
    for test_name, test_func in tests:
        print(f"\n🔬 开始测试: {test_name}")
        print("-" * 30)
        
        try:
            success = await test_func()
            if success:
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
                
            # 询问是否继续
            if test_name != tests[-1][0]:  # 不是最后一个测试
                continue_test = input(f"\n继续下一个测试 ({tests[tests.index((test_name, test_func)) + 1][0]})? (y/n): ")
                if continue_test.lower() != 'y':
                    break
                    
        except KeyboardInterrupt:
            print(f"\n⚠️  {test_name} 测试被中断")
            break
        except Exception as e:
            print(f"💥 {test_name} 测试异常: {e}")
    
    print("\n🏁 调试测试完成")

if __name__ == "__main__":
    print("🔧 Vheer.com 调试工具")
    print("此工具将逐步测试Vheer.com的各个功能")
    print("请确保Chrome浏览器已安装")
    
    input("\n按Enter开始调试...")
    
    asyncio.run(main())
