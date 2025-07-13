#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Vheer视频生成过程
观察网站的实际行为，找到正确的视频下载位置
"""

import asyncio
import time
import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from PIL import Image, ImageDraw

# 设置日志
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

def create_test_image():
    """创建测试图像"""
    try:
        width, height = 512, 512
        image = Image.new('RGB', (width, height), color=(100, 150, 200))
        
        draw = ImageDraw.Draw(image)
        draw.rectangle([50, 50, width-50, height-50], outline=(255, 255, 255), width=3)
        draw.ellipse([150, 150, width-150, height-150], fill=(255, 100, 100))
        
        filename = "debug_test_image.jpg"
        image.save(filename, 'JPEG', quality=95)
        
        logger.info(f"✅ 创建测试图像: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"❌ 创建测试图像失败: {e}")
        return None

async def debug_vheer_generation():
    """调试Vheer视频生成过程"""
    
    # 创建测试图像
    test_image = create_test_image()
    if not test_image:
        return
        
    # 设置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    # chrome_options.add_argument('--headless')  # 注释掉以便观察
    
    driver = None
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        logger.info("🌐 访问Vheer网站...")
        driver.get("https://vheer.com/app/image-to-video")
        
        # 等待页面加载
        await asyncio.sleep(3)
        
        logger.info("📤 上传图像...")
        
        # 查找文件上传元素
        file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        if not file_inputs:
            logger.error("❌ 未找到文件上传元素")
            return
            
        file_input = file_inputs[0]
        file_input.send_keys(os.path.abspath(test_image))
        
        await asyncio.sleep(3)
        logger.info("✅ 图像上传完成")
        
        # 点击生成按钮
        logger.info("🎬 点击生成按钮...")
        
        # 查找生成按钮
        generate_buttons = driver.find_elements(By.CSS_SELECTOR,
            "button, [class*='generate'], [class*='create'], [class*='start']")
        
        if not generate_buttons:
            # 尝试其他选择器
            generate_buttons = driver.find_elements(By.CSS_SELECTOR, "button")
            
        if generate_buttons:
            for i, btn in enumerate(generate_buttons):
                if btn.is_displayed() and btn.is_enabled():
                    text = btn.text.lower()
                    if any(word in text for word in ['generate', 'create', 'start', '生成', '开始']):
                        logger.info(f"🎯 点击按钮: {btn.text}")
                        btn.click()
                        break
            else:
                # 如果没找到明确的按钮，点击最后一个可见按钮
                if generate_buttons:
                    btn = generate_buttons[-1]
                    if btn.is_displayed() and btn.is_enabled():
                        logger.info(f"🎯 点击按钮: {btn.text}")
                        btn.click()
        
        await asyncio.sleep(5)
        
        # 开始监控页面变化
        logger.info("👀 开始监控页面变化...")
        
        start_time = time.time()
        last_video_count = 0
        last_page_source_hash = hash(driver.page_source)
        
        while time.time() - start_time < 120:  # 监控2分钟
            try:
                current_time = int(time.time() - start_time)
                
                # 检查页面是否有变化
                current_page_hash = hash(driver.page_source)
                if current_page_hash != last_page_source_hash:
                    logger.info(f"📄 页面内容发生变化 ({current_time}s)")
                    last_page_source_hash = current_page_hash
                
                # 查找所有视频元素
                videos = driver.find_elements(By.CSS_SELECTOR, "video")
                if len(videos) != last_video_count:
                    logger.info(f"🎬 发现 {len(videos)} 个视频元素 ({current_time}s)")
                    last_video_count = len(videos)
                    
                    for i, video in enumerate(videos):
                        src = video.get_attribute('src')
                        poster = video.get_attribute('poster')
                        classes = video.get_attribute('class')
                        parent_classes = video.find_element(By.XPATH, "..").get_attribute('class')
                        
                        logger.info(f"  视频 {i+1}:")
                        logger.info(f"    src: {src}")
                        logger.info(f"    poster: {poster}")
                        logger.info(f"    classes: {classes}")
                        logger.info(f"    parent_classes: {parent_classes}")
                        logger.info(f"    displayed: {video.is_displayed()}")
                        
                        # 检查是否为新生成的视频
                        if src and '/how/how.webm' not in src:
                            logger.info(f"🎯 可能的生成视频: {src}")
                
                # 查找下载链接
                download_links = driver.find_elements(By.CSS_SELECTOR, 
                    "a[download], a[href*='.mp4'], a[href*='.webm'], [class*='download']")
                
                for i, link in enumerate(download_links):
                    if link.is_displayed():
                        href = link.get_attribute('href')
                        download_attr = link.get_attribute('download')
                        text = link.text
                        
                        if href and ('.mp4' in href or '.webm' in href):
                            logger.info(f"🔗 下载链接 {i+1}: {href}")
                            logger.info(f"    download属性: {download_attr}")
                            logger.info(f"    链接文本: {text}")
                            
                            if '/how/how.webm' not in href:
                                logger.info(f"🎯 可能的生成视频下载链接: {href}")
                
                # 查找进度指示器
                progress_elements = driver.find_elements(By.CSS_SELECTOR, 
                    "[class*='progress'], [class*='loading'], [class*='generating']")
                
                if progress_elements:
                    for elem in progress_elements:
                        if elem.is_displayed():
                            logger.info(f"⏳ 进度指示器: {elem.text} ({elem.get_attribute('class')})")
                
                # 查找完成指示器
                complete_elements = driver.find_elements(By.CSS_SELECTOR,
                    "[class*='complete'], [class*='done'], [class*='finished'], [class*='success']")
                
                if complete_elements:
                    for elem in complete_elements:
                        if elem.is_displayed():
                            logger.info(f"✅ 完成指示器: {elem.text} ({elem.get_attribute('class')})")
                
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ 监控过程中出错: {e}")
                await asyncio.sleep(3)
        
        logger.info("⏰ 监控时间结束")
        
        # 最终检查
        logger.info("🔍 最终检查所有视频和链接...")
        
        final_videos = driver.find_elements(By.CSS_SELECTOR, "video")
        for i, video in enumerate(final_videos):
            src = video.get_attribute('src')
            if src and '/how/how.webm' not in src:
                logger.info(f"🎬 最终视频 {i+1}: {src}")
        
        final_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='.webm'], a[href*='.mp4']")
        for i, link in enumerate(final_links):
            href = link.get_attribute('href')
            if href and '/how/how.webm' not in href:
                logger.info(f"🔗 最终链接 {i+1}: {href}")
        
    except Exception as e:
        logger.error(f"❌ 调试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()
            
        # 清理测试文件
        try:
            if os.path.exists(test_image):
                os.remove(test_image)
                logger.info("🧹 清理测试文件")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(debug_vheer_generation())
