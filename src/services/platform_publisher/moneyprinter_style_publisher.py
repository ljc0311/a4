#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MoneyPrinterPlus风格的发布器基类
参考MoneyPrinterPlus的成功实现方式
"""

import time
import asyncio
from typing import Dict, Any, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.utils.logger import logger


class MoneyPrinterStylePublisher:
    """MoneyPrinterPlus风格的发布器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.driver = None
        self.platform_name = "unknown"
        self.upload_url = ""
        
    def initialize(self) -> bool:
        """初始化发布器 - MoneyPrinterPlus风格"""
        try:
            logger.info(f"初始化 {self.platform_name} 发布器...")
            
            # 1. 连接到现有的Chrome调试实例（MoneyPrinterPlus方式）
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            
            # 2. 创建WebDriver实例
            self.driver = webdriver.Chrome(options=chrome_options)
            
            logger.info(f"{self.platform_name} 发布器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"{self.platform_name} 发布器初始化失败: {e}")
            return False
    
    def navigate_to_upload_page(self) -> bool:
        """导航到上传页面"""
        try:
            logger.info(f"导航到 {self.platform_name} 上传页面: {self.upload_url}")
            self.driver.get(self.upload_url)
            time.sleep(3)
            return True
        except Exception as e:
            logger.error(f"导航到上传页面失败: {e}")
            return False
    
    def check_login_status(self) -> bool:
        """检查登录状态 - MoneyPrinterPlus风格"""
        try:
            current_url = self.driver.current_url
            logger.info(f"当前页面URL: {current_url}")
            
            # 1. 基本检查
            if self.upload_url.split('/')[2] not in current_url:
                logger.warning(f"不在 {self.platform_name} 页面")
                return False
            
            # 2. 检查登录页面标识
            if any(keyword in current_url.lower() for keyword in ['login', 'passport', 'sso']):
                logger.warning("检测到登录页面")
                return False
            
            # 3. 检查页面标题
            try:
                page_title = self.driver.title
                if '登录' in page_title or 'login' in page_title.lower():
                    logger.warning("页面标题包含登录信息")
                    return False
            except:
                pass
            
            # 4. 检查关键成功指示器
            success_indicators = self.get_success_indicators()
            found_count = 0
            
            for selector in success_indicators:
                if self.find_element_safe(selector, timeout=1):
                    found_count += 1
            
            if found_count > 0:
                logger.info(f"{self.platform_name} 登录检测成功！找到 {found_count} 个关键元素")
                return True
            
            # 5. 最终检测：如果没有明显的登录按钮，认为已登录
            login_buttons = self.driver.find_elements(By.XPATH, '//button[contains(text(), "登录")]')
            if not login_buttons:
                logger.info(f"MoneyPrinterPlus风格检测：在 {self.platform_name} 且无登录按钮，认为已登录")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return False
    
    def find_element_safe(self, selector: str, timeout: int = 5) -> bool:
        """安全查找元素"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, selector))
            )
            return element.is_displayed() and element.is_enabled()
        except:
            return False
    
    def click_element_safe(self, selector: str, timeout: int = 5) -> bool:
        """安全点击元素"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, selector))
            )
            # 滚动到元素可见
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            element.click()
            return True
        except Exception as e:
            logger.debug(f"点击元素失败 {selector}: {e}")
            return False
    
    def send_keys_safe(self, selector: str, text: str, timeout: int = 5) -> bool:
        """安全输入文本"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, selector))
            )
            if element.is_displayed() and element.is_enabled():
                # 滚动到元素可见
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                element.clear()
                element.send_keys(text)
                return True
        except Exception as e:
            logger.debug(f"输入文本失败 {selector}: {e}")
            return False
    
    def upload_video_file(self, video_path: str) -> bool:
        """上传视频文件 - MoneyPrinterPlus通用方法"""
        try:
            logger.info(f"开始上传视频文件: {video_path}")
            
            # 查找文件上传输入框
            file_selectors = [
                '//input[@type="file"]',
                '//input[@accept*="video"]',
                '//input[contains(@accept, ".mp4")]'
            ]
            
            for selector in file_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element:
                        element.send_keys(video_path)
                        logger.info("✅ 视频文件上传成功")
                        return True
                except:
                    continue
            
            logger.error("❌ 未找到文件上传输入框")
            return False
            
        except Exception as e:
            logger.error(f"上传视频文件失败: {e}")
            return False
    
    def wait_for_upload_complete(self, timeout: int = 300) -> bool:
        """等待上传完成 - MoneyPrinterPlus通用方法"""
        try:
            logger.info("等待视频上传完成...")
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # 检查上传进度指示器
                progress_indicators = [
                    '//div[contains(@class, "progress")]',
                    '//div[contains(text(), "上传中")]',
                    '//div[contains(text(), "处理中")]',
                    '//div[contains(text(), "%")]'
                ]
                
                upload_in_progress = False
                for indicator in progress_indicators:
                    if self.find_element_safe(indicator, timeout=1):
                        upload_in_progress = True
                        break
                
                if not upload_in_progress:
                    logger.info("✅ 检测到上传完成")
                    return True
                
                time.sleep(2)
            
            logger.warning("等待上传完成超时")
            return False
            
        except Exception as e:
            logger.error(f"等待上传完成失败: {e}")
            return False
    
    def smart_find_and_click(self, selectors: List[str], element_name: str) -> bool:
        """智能查找并点击元素 - MoneyPrinterPlus风格"""
        try:
            logger.info(f"智能查找 {element_name}...")
            
            for i, selector in enumerate(selectors, 1):
                logger.info(f"尝试选择器 {i}/{len(selectors)}: {selector}")
                if self.click_element_safe(selector, timeout=3):
                    logger.info(f"✅ {element_name} 点击成功")
                    return True
            
            # 如果传统选择器都失败，使用爬虫辅助
            logger.info(f"🕷️ 启用爬虫辅助查找 {element_name}...")
            return self.crawler_assisted_find_and_click(element_name)
            
        except Exception as e:
            logger.error(f"智能查找 {element_name} 失败: {e}")
            return False
    
    def crawler_assisted_find_and_click(self, element_name: str) -> bool:
        """爬虫辅助查找并点击 - 通用实现"""
        try:
            # 根据元素名称确定关键词
            keywords_map = {
                "发布按钮": ['发布', '发表', '提交', 'publish', 'submit'],
                "标题输入框": ['标题', 'title'],
                "描述输入框": ['简介', '描述', 'description', 'content']
            }
            
            keywords = keywords_map.get(element_name, [element_name])
            
            # 查找所有可能的元素
            all_elements = []
            if "按钮" in element_name:
                all_elements = self.driver.find_elements(By.TAG_NAME, "button")
            elif "输入框" in element_name:
                all_elements = (self.driver.find_elements(By.TAG_NAME, "input") + 
                              self.driver.find_elements(By.TAG_NAME, "textarea"))
            
            # 分析元素属性
            for element in all_elements:
                try:
                    if not element.is_displayed() or not element.is_enabled():
                        continue
                    
                    element_text = element.text.strip()
                    element_placeholder = element.get_attribute('placeholder') or ''
                    element_class = element.get_attribute('class') or ''
                    
                    # 检查是否匹配关键词
                    text_match = any(keyword in element_text for keyword in keywords)
                    placeholder_match = any(keyword in element_placeholder for keyword in keywords)
                    class_match = any(keyword in element_class.lower() for keyword in keywords)
                    
                    if text_match or placeholder_match or class_match:
                        logger.info(f"🎯 爬虫辅助找到 {element_name}: {element_text or element_placeholder}")
                        
                        # 滚动到元素可见并点击
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(0.5)
                        element.click()
                        logger.info(f"✅ 爬虫辅助 {element_name} 操作成功")
                        return True
                        
                except Exception:
                    continue
            
            logger.warning(f"❌ 爬虫辅助未找到 {element_name}")
            return False
            
        except Exception as e:
            logger.error(f"爬虫辅助查找失败: {e}")
            return False
    
    def get_success_indicators(self) -> List[str]:
        """获取成功指示器 - 子类需要重写"""
        return [
            '//input[@type="file"]',
            '//button[contains(text(), "发布")]'
        ]
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
