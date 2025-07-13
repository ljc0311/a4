#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vheer.com 图生视频调试测试脚本
用于调试和验证基础功能
"""

import os
import time
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

def test_selenium_basic():
    """测试Selenium基础功能"""
    logger.info("🔧 测试Selenium基础功能...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        logger.info("✅ Selenium导入成功")
        
        # 设置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1280,720")
        
        # 尝试启动浏览器
        logger.info("🌐 尝试启动Chrome浏览器...")
        
        # 检查chromedriver是否存在
        if os.path.exists("chromedriver.exe"):
            logger.info("✅ 找到chromedriver.exe")
        else:
            logger.error("❌ 未找到chromedriver.exe")
            return False
            
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("✅ Chrome浏览器启动成功")
        
        # 测试访问Google
        logger.info("🔗 测试访问Google...")
        driver.get("https://www.google.com")
        
        # 等待页面加载
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        title = driver.title
        logger.info(f"✅ 页面标题: {title}")
        
        # 关闭浏览器
        driver.quit()
        logger.info("✅ 浏览器关闭成功")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Selenium测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vheer_access():
    """测试访问Vheer网站"""
    logger.info("🌐 测试访问Vheer网站...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1280,720")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            logger.info("📖 访问Vheer主页...")
            driver.get("https://vheer.com")
            
            # 等待页面加载
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            title = driver.title
            logger.info(f"✅ Vheer主页标题: {title}")
            
            # 尝试访问图生视频页面
            logger.info("🎬 访问图生视频页面...")
            driver.get("https://vheer.com/app/image-to-video")
            
            # 等待页面加载
            time.sleep(5)
            
            current_url = driver.current_url
            logger.info(f"✅ 当前URL: {current_url}")
            
            # 检查页面内容
            page_source = driver.page_source
            if "image" in page_source.lower() and "video" in page_source.lower():
                logger.info("✅ 页面包含图像和视频相关内容")
            else:
                logger.warning("⚠️ 页面内容可能不正确")
                
            # 查找可能的上传元素
            logger.info("🔍 查找页面元素...")
            
            # 查找文件输入框
            file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            logger.info(f"📁 找到 {len(file_inputs)} 个文件输入框")
            
            # 查找按钮
            buttons = driver.find_elements(By.CSS_SELECTOR, "button")
            logger.info(f"🔘 找到 {len(buttons)} 个按钮")
            
            # 查找上传相关元素
            upload_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='upload'], [class*='drop']")
            logger.info(f"📤 找到 {len(upload_elements)} 个上传相关元素")
            
            return True
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"❌ Vheer访问测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_test_image():
    """创建测试图像"""
    logger.info("🖼️ 创建测试图像...")
    
    try:
        from PIL import Image, ImageDraw
        
        # 创建一个简单的测试图像
        width, height = 512, 512
        image = Image.new('RGB', (width, height), color=(100, 150, 200))
        
        draw = ImageDraw.Draw(image)
        
        # 添加一些图形
        draw.rectangle([50, 50, width-50, height-50], outline=(255, 255, 255), width=5)
        draw.ellipse([150, 150, width-150, height-150], fill=(255, 200, 100))
        draw.line([0, 0, width, height], fill=(255, 0, 0), width=3)
        draw.line([width, 0, 0, height], fill=(0, 255, 0), width=3)
        
        # 保存图像
        filename = "debug_test_image.jpg"
        image.save(filename, 'JPEG', quality=95)
        
        logger.info(f"✅ 测试图像创建成功: {filename}")
        return filename
        
    except ImportError:
        logger.error("❌ PIL未安装，无法创建测试图像")
        return None
    except Exception as e:
        logger.error(f"❌ 创建测试图像失败: {e}")
        return None

def test_image_upload():
    """测试图像上传功能"""
    logger.info("📤 测试图像上传功能...")
    
    # 首先创建测试图像
    test_image = create_test_image()
    if not test_image:
        logger.error("❌ 无法创建测试图像")
        return False
        
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1280,720")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # 访问图生视频页面
            logger.info("📖 访问图生视频页面...")
            driver.get("https://vheer.com/app/image-to-video")
            
            # 等待页面加载
            time.sleep(8)
            
            # 查找文件输入框
            logger.info("🔍 查找文件输入框...")
            file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            
            if not file_inputs:
                logger.warning("⚠️ 未找到文件输入框，尝试其他方法...")
                
                # 尝试查找上传按钮
                upload_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Upload') or contains(text(), 'Choose') or contains(text(), '上传') or contains(text(), '选择')]")
                
                if upload_buttons:
                    logger.info(f"✅ 找到 {len(upload_buttons)} 个上传按钮")
                    
                    # 点击第一个上传按钮
                    upload_buttons[0].click()
                    time.sleep(2)
                    
                    # 再次查找文件输入框
                    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    
            if file_inputs:
                logger.info(f"✅ 找到 {len(file_inputs)} 个文件输入框")
                
                # 尝试上传文件
                abs_path = os.path.abspath(test_image)
                logger.info(f"📁 上传文件: {abs_path}")
                
                file_inputs[0].send_keys(abs_path)
                logger.info("✅ 文件上传命令发送成功")
                
                # 等待上传处理
                time.sleep(5)
                
                # 查找生成按钮
                logger.info("🔍 查找生成按钮...")
                generate_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Generate') or contains(text(), 'Create') or contains(text(), '生成')]")
                
                if generate_buttons:
                    logger.info(f"✅ 找到 {len(generate_buttons)} 个生成按钮")
                    
                    # 点击生成按钮
                    generate_buttons[0].click()
                    logger.info("✅ 生成按钮点击成功")
                    
                    # 等待一段时间观察结果
                    logger.info("⏳ 等待生成过程...")
                    time.sleep(10)
                    
                    # 检查是否有视频元素出现
                    videos = driver.find_elements(By.CSS_SELECTOR, "video")
                    if videos:
                        logger.info(f"🎬 发现 {len(videos)} 个视频元素")
                        return True
                    else:
                        logger.info("⏳ 暂未发现视频元素，可能还在生成中...")
                        return True  # 上传和点击都成功了
                        
                else:
                    logger.warning("⚠️ 未找到生成按钮")
                    
            else:
                logger.error("❌ 未找到文件输入框")
                return False
                
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"❌ 图像上传测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    return True

def main():
    """主函数"""
    print("🔧 Vheer.com 图生视频调试测试")
    print("=" * 50)
    
    # 测试1: Selenium基础功能
    print("\n🔧 测试1: Selenium基础功能")
    if test_selenium_basic():
        print("✅ Selenium基础功能测试通过")
    else:
        print("❌ Selenium基础功能测试失败")
        return
        
    # 测试2: Vheer网站访问
    print("\n🌐 测试2: Vheer网站访问")
    if test_vheer_access():
        print("✅ Vheer网站访问测试通过")
    else:
        print("❌ Vheer网站访问测试失败")
        return
        
    # 测试3: 图像上传功能
    print("\n📤 测试3: 图像上传功能")
    if test_image_upload():
        print("✅ 图像上传功能测试通过")
    else:
        print("❌ 图像上传功能测试失败")
        
    print("\n" + "=" * 50)
    print("🎉 调试测试完成")
    
    # 检查生成的文件
    if os.path.exists("debug_test_image.jpg"):
        print(f"📷 测试图像: debug_test_image.jpg")
        
    print("\n💡 如果所有测试都通过，说明基础功能正常")
    print("💡 可以继续运行完整的图生视频测试程序")

if __name__ == "__main__":
    main()
