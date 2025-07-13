#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vheer.com 图生视频快速测试脚本
简化版本，用于快速验证功能
"""

import os
import time
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

def create_sample_image():
    """创建一个示例图像用于测试"""
    try:
        from PIL import Image, ImageDraw
        
        # 创建一个简单的渐变图像
        width, height = 512, 512
        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)
        
        # 创建渐变效果
        for y in range(height):
            color_value = int(255 * (y / height))
            draw.line([(0, y), (width, y)], fill=(color_value, 100, 255 - color_value))
            
        # 添加一些几何图形
        draw.ellipse([width//4, height//4, 3*width//4, 3*height//4], outline=(255, 255, 255), width=3)
        draw.rectangle([width//3, height//3, 2*width//3, 2*height//3], outline=(255, 255, 0), width=2)
        
        # 保存图像
        filename = "sample_test_image.jpg"
        image.save(filename, 'JPEG', quality=95)
        logger.info(f"✅ 创建示例图像: {filename}")
        return filename
        
    except ImportError:
        logger.error("❌ 需要安装 Pillow: pip install Pillow")
        return None
    except Exception as e:
        logger.error(f"❌ 创建示例图像失败: {e}")
        return None

def quick_test():
    """快速测试函数"""
    logger.info("🎬 Vheer.com 图生视频快速测试")
    logger.info("=" * 50)
    
    try:
        # 检查依赖
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError:
            logger.error("❌ 需要安装 Selenium: pip install selenium")
            return False
            
        # 准备测试图像
        test_image = None
        
        # 查找现有图像
        for ext in ['jpg', 'jpeg', 'png', 'webp']:
            for name in ['test', 'sample', 'image', 'photo']:
                filename = f"{name}.{ext}"
                if os.path.exists(filename):
                    test_image = filename
                    logger.info(f"📷 使用现有图像: {filename}")
                    break
            if test_image:
                break
                
        # 如果没有现有图像，创建一个
        if not test_image:
            test_image = create_sample_image()
            
        if not test_image:
            logger.error("❌ 无法获取测试图像")
            return False
            
        # 设置浏览器
        logger.info("🌐 启动浏览器...")
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # 注意：这里设置为有头模式，您可以观察整个过程
        # 如果想要无头模式，取消下面这行的注释
        # chrome_options.add_argument("--headless")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # 访问页面
            logger.info("📖 访问 Vheer 图生视频页面...")
            driver.get("https://vheer.com/app/image-to-video")
            
            # 等待页面加载
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(5)  # 额外等待JavaScript加载
            
            logger.info("✅ 页面加载完成")
            
            # 查找并上传图像
            logger.info("📤 查找上传元素...")
            
            # 尝试多种方式查找上传元素
            upload_element = None
            
            # 方法1: 查找文件输入框
            try:
                file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                for file_input in file_inputs:
                    if file_input.is_displayed() or True:  # 即使隐藏也尝试
                        upload_element = file_input
                        logger.info("✅ 找到文件输入框")
                        break
            except:
                pass
                
            # 方法2: 查找上传按钮
            if not upload_element:
                try:
                    upload_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Upload') or contains(text(), 'Choose') or contains(text(), '上传') or contains(text(), '选择')]")
                    if upload_buttons:
                        upload_element = upload_buttons[0]
                        logger.info("✅ 找到上传按钮")
                except:
                    pass
                    
            if not upload_element:
                logger.error("❌ 未找到上传元素")
                return False
                
            # 上传图像
            logger.info(f"📤 上传图像: {test_image}")
            abs_path = os.path.abspath(test_image)
            
            if upload_element.tag_name == "input":
                upload_element.send_keys(abs_path)
            else:
                # 点击按钮后查找input
                upload_element.click()
                time.sleep(2)
                file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                if file_inputs:
                    file_inputs[0].send_keys(abs_path)
                    
            logger.info("✅ 图像上传完成")
            time.sleep(5)  # 等待上传处理
            
            # 查找生成按钮
            logger.info("🎬 查找生成按钮...")
            generate_button = None
            
            # 尝试多种方式查找生成按钮
            button_texts = ['Generate', 'Create', 'Start', 'Convert', '生成', '创建', '开始']
            
            for text in button_texts:
                try:
                    buttons = driver.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            generate_button = button
                            logger.info(f"✅ 找到生成按钮: {text}")
                            break
                    if generate_button:
                        break
                except:
                    continue
                    
            if not generate_button:
                # 尝试通用按钮选择器
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, "button")
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = button.text.lower()
                            if any(word in button_text for word in ['generate', 'create', 'start', '生成']):
                                generate_button = button
                                logger.info(f"✅ 找到生成按钮: {button.text}")
                                break
                except:
                    pass
                    
            if not generate_button:
                logger.error("❌ 未找到生成按钮")
                return False
                
            # 点击生成按钮
            logger.info("🚀 开始生成视频...")
            driver.execute_script("arguments[0].scrollIntoView();", generate_button)
            time.sleep(1)
            generate_button.click()
            
            # 等待视频生成
            logger.info("⏳ 等待视频生成完成...")
            max_wait = 300  # 5分钟
            start_time = time.time()
            
            video_found = False
            while time.time() - start_time < max_wait:
                try:
                    # 查找视频元素
                    videos = driver.find_elements(By.CSS_SELECTOR, "video")
                    for video in videos:
                        if video.is_displayed():
                            src = video.get_attribute('src')
                            if src:
                                logger.info(f"✅ 发现生成的视频!")
                                logger.info(f"🎬 视频URL: {src[:100]}...")
                                video_found = True
                                break
                                
                    if video_found:
                        break
                        
                    # 检查下载链接
                    download_links = driver.find_elements(By.CSS_SELECTOR, "a[download], a[href*='.mp4']")
                    if download_links:
                        for link in download_links:
                            if link.is_displayed():
                                href = link.get_attribute('href')
                                if href:
                                    logger.info(f"✅ 发现下载链接!")
                                    logger.info(f"🔗 下载URL: {href[:100]}...")
                                    video_found = True
                                    break
                                    
                    if video_found:
                        break
                        
                    elapsed = int(time.time() - start_time)
                    if elapsed % 10 == 0:  # 每10秒打印一次进度
                        logger.info(f"🔄 等待中... ({elapsed}s)")
                        
                    time.sleep(2)
                    
                except Exception as e:
                    logger.debug(f"检查视频时出错: {e}")
                    time.sleep(2)
                    
            if video_found:
                logger.info("🎉 视频生成成功!")
                logger.info("✅ 快速测试通过 - Vheer 图生视频功能可用")
                return True
            else:
                logger.warning("⚠️ 视频生成超时或失败")
                return False
                
        finally:
            logger.info("🧹 关闭浏览器...")
            driver.quit()
            
    except Exception as e:
        logger.error(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🎬 Vheer.com 图生视频快速测试")
    print("=" * 50)
    print("这个脚本将快速测试 Vheer.com 的图生视频功能")
    print("测试过程:")
    print("1. 创建或使用现有的测试图像")
    print("2. 打开 Vheer 图生视频页面")
    print("3. 上传图像")
    print("4. 启动视频生成")
    print("5. 等待并检测生成结果")
    print()
    
    try:
        input("按 Enter 键开始测试...")
    except KeyboardInterrupt:
        print("\n测试取消")
        return
        
    success = quick_test()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 测试结果: 成功!")
        print("✅ Vheer.com 图生视频功能可用")
        print("💡 建议: 可以继续开发完整的集成方案")
    else:
        print("❌ 测试结果: 失败")
        print("💡 建议: 检查网络连接或网站是否有变化")
        
    print("=" * 50)

if __name__ == "__main__":
    main()
