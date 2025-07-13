#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vheer.com 高级集成方案
使用浏览器自动化和网络监控来实现真实的图像生成
"""

import asyncio
import json
import time
import base64
import os
from typing import Optional, Dict, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import requests
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VheerBrowserIntegration:
    """Vheer 浏览器集成方案"""
    
    def __init__(self, headless: bool = False):
        self.driver = None
        self.headless = headless
        self.network_logs = []
        self.generated_images = []
        
    def setup_browser(self) -> bool:
        """设置浏览器环境"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            # 基础设置
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 模拟真实用户
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # 启用网络日志
            chrome_options.set_capability('goog:loggingPrefs', {
                'performance': 'ALL',
                'browser': 'ALL'
            })
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # 执行反检测脚本
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("浏览器启动成功")
            return True
            
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            return False
            
    def capture_network_requests(self):
        """捕获网络请求"""
        try:
            logs = self.driver.get_log('performance')
            for log in logs:
                message = json.loads(log['message'])
                if message['message']['method'] in ['Network.requestWillBeSent', 'Network.responseReceived']:
                    self.network_logs.append(message)
        except Exception as e:
            logger.debug(f"捕获网络请求失败: {e}")
            
    def wait_for_page_load(self, timeout: int = 30):
        """等待页面完全加载"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # 额外等待 JavaScript 执行
            time.sleep(3)
            
        except Exception as e:
            logger.warning(f"页面加载等待超时: {e}")
            
    def find_input_element(self) -> Optional[object]:
        """智能查找输入框"""
        selectors = [
            # 常见的提示词输入框选择器
            "textarea[placeholder*='prompt']",
            "textarea[placeholder*='describe']",
            "textarea[placeholder*='输入']",
            "input[placeholder*='prompt']",
            "input[placeholder*='describe']",
            "input[placeholder*='输入']",
            # 通用选择器
            "textarea",
            "input[type='text']",
            # 可能的类名
            ".prompt-input",
            ".text-input",
            ".description-input",
            "#prompt",
            "#description"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        # 检查元素是否可能是提示词输入框
                        placeholder = element.get_attribute('placeholder') or ''
                        name = element.get_attribute('name') or ''
                        id_attr = element.get_attribute('id') or ''
                        
                        keywords = ['prompt', 'describe', 'text', 'input', '输入', '描述']
                        if any(keyword in (placeholder + name + id_attr).lower() for keyword in keywords):
                            logger.info(f"找到输入框: {selector}")
                            return element
                            
                # 如果没找到关键词匹配的，返回第一个可见的
                if elements and elements[0].is_displayed():
                    logger.info(f"使用默认输入框: {selector}")
                    return elements[0]
                    
            except Exception as e:
                logger.debug(f"选择器 {selector} 查找失败: {e}")
                continue
                
        return None
        
    def find_generate_button(self) -> Optional[object]:
        """智能查找生成按钮"""
        # 先尝试文本匹配
        text_patterns = [
            "Generate", "Create", "Submit", "生成", "创建", "提交",
            "Start", "Run", "Make", "开始", "运行", "制作"
        ]
        
        for pattern in text_patterns:
            try:
                # 使用 XPath 查找包含特定文本的按钮
                xpath = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern.lower()}')]"
                elements = self.driver.find_elements(By.XPATH, xpath)
                
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        logger.info(f"找到生成按钮 (文本): {pattern}")
                        return element
                        
            except Exception as e:
                logger.debug(f"文本模式 {pattern} 查找失败: {e}")
                
        # 尝试选择器匹配
        selectors = [
            "button[type='submit']",
            ".generate-btn", ".create-btn", ".submit-btn",
            ".btn-primary", ".btn-generate", ".btn-create",
            "button:last-of-type",  # 通常生成按钮是最后一个
            "button"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        # 检查按钮文本是否包含相关关键词
                        text = element.text.lower()
                        if any(keyword in text for keyword in ['generate', 'create', 'submit', '生成', '创建']):
                            logger.info(f"找到生成按钮 (选择器): {selector}")
                            return element
                            
                # 如果没有关键词匹配，尝试最后一个按钮
                if selector == "button" and elements:
                    last_button = elements[-1]
                    if last_button.is_displayed() and last_button.is_enabled():
                        logger.info("使用最后一个按钮作为生成按钮")
                        return last_button
                        
            except Exception as e:
                logger.debug(f"选择器 {selector} 查找失败: {e}")
                
        return None
        
    def extract_generated_images(self) -> List[str]:
        """提取生成的图像"""
        image_urls = []
        
        # 等待图像生成
        max_wait = 60  # 最多等待60秒
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # 查找图像元素
                img_selectors = [
                    "img[src*='blob:']",  # Blob URL
                    "img[src*='data:image']",  # Base64 图像
                    "img[src*='generated']",  # 可能的生成图像路径
                    "img[src*='result']",
                    "img[src*='output']",
                    ".result-image img",
                    ".generated-image img",
                    ".output-image img"
                ]
                
                for selector in img_selectors:
                    images = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for img in images:
                        if img.is_displayed():
                            src = img.get_attribute('src')
                            if src and src not in image_urls:
                                image_urls.append(src)
                                logger.info(f"发现生成的图像: {src[:100]}...")
                                
                if image_urls:
                    break
                    
                # 检查是否有加载指示器
                loading_selectors = [
                    ".loading", ".spinner", ".progress",
                    "[class*='loading']", "[class*='spinner']"
                ]
                
                still_loading = False
                for selector in loading_selectors:
                    if self.driver.find_elements(By.CSS_SELECTOR, selector):
                        still_loading = True
                        break
                        
                if not still_loading:
                    # 如果没有加载指示器，可能已经完成但我们没找到图像
                    time.sleep(2)
                else:
                    time.sleep(1)
                    
            except Exception as e:
                logger.debug(f"提取图像时出错: {e}")
                time.sleep(1)
                
        return image_urls
        
    def download_image(self, image_url: str, save_path: str) -> bool:
        """下载图像"""
        try:
            if image_url.startswith('data:image'):
                # 处理 Base64 图像
                header, data = image_url.split(',', 1)
                image_data = base64.b64decode(data)
                
                with open(save_path, 'wb') as f:
                    f.write(image_data)
                    
                logger.info(f"Base64 图像保存成功: {save_path}")
                return True
                
            elif image_url.startswith('blob:'):
                # 处理 Blob URL - 需要在浏览器中执行 JavaScript
                script = f"""
                return new Promise((resolve) => {{
                    fetch('{image_url}')
                        .then(response => response.blob())
                        .then(blob => {{
                            const reader = new FileReader();
                            reader.onload = () => resolve(reader.result);
                            reader.readAsDataURL(blob);
                        }})
                        .catch(() => resolve(null));
                }});
                """
                
                data_url = self.driver.execute_async_script(script)
                if data_url:
                    return self.download_image(data_url, save_path)
                    
            else:
                # 处理普通 HTTP URL
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()
                
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                    
                logger.info(f"HTTP 图像下载成功: {save_path}")
                return True
                
        except Exception as e:
            logger.error(f"下载图像失败: {e}")
            return False
            
        return False
        
    def generate_image(self, prompt: str, output_dir: str = "temp/vheer_images") -> List[str]:
        """生成图像的主要方法"""
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 访问 Vheer 页面
            logger.info("访问 Vheer 页面...")
            self.driver.get("https://vheer.com/app/text-to-image")
            self.wait_for_page_load()
            
            # 查找输入框
            logger.info("查找输入框...")
            input_element = self.find_input_element()
            if not input_element:
                logger.error("未找到输入框")
                return []
                
            # 输入提示词
            logger.info(f"输入提示词: {prompt}")
            input_element.clear()
            input_element.send_keys(prompt)
            
            # 等待一下让页面响应
            time.sleep(1)
            
            # 查找生成按钮
            logger.info("查找生成按钮...")
            generate_button = self.find_generate_button()
            if not generate_button:
                logger.error("未找到生成按钮")
                return []
                
            # 清空网络日志
            self.network_logs.clear()
            
            # 点击生成按钮
            logger.info("点击生成按钮...")
            try:
                # 滚动到按钮位置
                self.driver.execute_script("arguments[0].scrollIntoView();", generate_button)
                time.sleep(0.5)
                
                # 尝试点击
                generate_button.click()
                
            except Exception as e:
                logger.warning(f"普通点击失败，尝试 JavaScript 点击: {e}")
                self.driver.execute_script("arguments[0].click();", generate_button)
                
            logger.info("等待图像生成...")
            
            # 提取生成的图像
            image_urls = self.extract_generated_images()
            
            if not image_urls:
                logger.warning("未找到生成的图像")
                return []
                
            # 下载图像
            downloaded_paths = []
            for i, url in enumerate(image_urls):
                timestamp = int(time.time())
                filename = f"vheer_generated_{timestamp}_{i}.png"
                save_path = os.path.join(output_dir, filename)
                
                if self.download_image(url, save_path):
                    downloaded_paths.append(save_path)
                    
            logger.info(f"成功生成并下载了 {len(downloaded_paths)} 张图像")
            return downloaded_paths
            
        except Exception as e:
            logger.error(f"图像生成过程失败: {e}")
            return []
            
    def cleanup(self):
        """清理资源"""
        if self.driver:
            self.driver.quit()
            logger.info("浏览器已关闭")

async def test_vheer_browser_integration():
    """测试浏览器集成方案"""
    integration = VheerBrowserIntegration(headless=False)  # 设置为 False 以便观察过程
    
    try:
        if not integration.setup_browser():
            logger.error("浏览器设置失败")
            return
            
        # 测试生成图像
        test_prompts = [
            "a beautiful sunset over mountains",
            "a cute cat sitting on a windowsill",
            "a futuristic city skyline at night"
        ]
        
        for prompt in test_prompts:
            logger.info(f"\n=== 测试提示词: {prompt} ===")
            
            result_paths = integration.generate_image(prompt)
            
            if result_paths:
                logger.info(f"✅ 成功生成图像:")
                for path in result_paths:
                    logger.info(f"  - {path}")
            else:
                logger.error(f"❌ 图像生成失败")
                
            # 等待一下再进行下一次生成
            time.sleep(5)
            
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        
    finally:
        integration.cleanup()

if __name__ == "__main__":
    asyncio.run(test_vheer_browser_integration())
