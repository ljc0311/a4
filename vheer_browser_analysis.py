#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Selenium模拟浏览器操作来分析Vheer的实际API调用
"""

import asyncio
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VheerBrowserAnalyzer:
    """Vheer浏览器分析器"""
    
    def __init__(self):
        self.driver = None
        self.network_logs = []
        
    def setup_driver(self):
        """设置Chrome浏览器"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # 启用网络日志
        chrome_options.add_argument("--enable-logging")
        chrome_options.add_argument("--log-level=0")
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # 启用性能日志来捕获网络请求
        chrome_options.set_capability('goog:loggingPrefs', {
            'performance': 'ALL',
            'browser': 'ALL'
        })
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Chrome浏览器启动成功")
            return True
        except Exception as e:
            logger.error(f"启动Chrome浏览器失败: {e}")
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
            logger.error(f"捕获网络请求失败: {e}")
            
    def analyze_vheer_page(self):
        """分析Vheer页面"""
        try:
            # 访问Vheer文本到图像页面
            logger.info("访问Vheer文本到图像页面...")
            self.driver.get("https://vheer.com/app/text-to-image")
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 捕获初始网络请求
            self.capture_network_requests()
            
            # 查找输入框
            logger.info("查找提示词输入框...")
            prompt_inputs = [
                "textarea[placeholder*='prompt']",
                "textarea[placeholder*='describe']", 
                "input[placeholder*='prompt']",
                "input[placeholder*='describe']",
                "textarea",
                "input[type='text']"
            ]
            
            prompt_element = None
            for selector in prompt_inputs:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        prompt_element = elements[0]
                        logger.info(f"找到输入框: {selector}")
                        break
                except:
                    continue
                    
            if not prompt_element:
                logger.warning("未找到提示词输入框")
                return
                
            # 输入测试提示词
            test_prompt = "a beautiful sunset over mountains"
            logger.info(f"输入测试提示词: {test_prompt}")
            prompt_element.clear()
            prompt_element.send_keys(test_prompt)
            
            # 查找生成按钮
            logger.info("查找生成按钮...")
            button_selectors = [
                "button[type='submit']",
                "button:contains('Generate')",
                "button:contains('Create')",
                "button:contains('Submit')",
                ".generate-btn",
                ".create-btn",
                ".submit-btn",
                "button"
            ]
            
            generate_button = None
            for selector in button_selectors:
                try:
                    if ":contains" in selector:
                        # 使用XPath查找包含特定文本的按钮
                        text = selector.split(":contains('")[1].split("')")[0]
                        xpath = f"//button[contains(text(), '{text}')]"
                        elements = self.driver.find_elements(By.XPATH, xpath)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                    if elements:
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                generate_button = element
                                logger.info(f"找到生成按钮: {selector}")
                                break
                        if generate_button:
                            break
                except:
                    continue
                    
            if not generate_button:
                logger.warning("未找到生成按钮")
                return
                
            # 点击生成按钮前清空网络日志
            self.network_logs.clear()
            
            # 点击生成按钮
            logger.info("点击生成按钮...")
            try:
                # 滚动到按钮位置
                self.driver.execute_script("arguments[0].scrollIntoView();", generate_button)
                time.sleep(1)
                
                # 点击按钮
                generate_button.click()
                logger.info("生成按钮点击成功")
                
            except Exception as e:
                logger.error(f"点击生成按钮失败: {e}")
                # 尝试使用JavaScript点击
                try:
                    self.driver.execute_script("arguments[0].click();", generate_button)
                    logger.info("使用JavaScript点击成功")
                except Exception as e2:
                    logger.error(f"JavaScript点击也失败: {e2}")
                    return
                    
            # 等待并捕获网络请求
            logger.info("等待API调用...")
            for i in range(30):  # 等待30秒
                time.sleep(1)
                self.capture_network_requests()
                
                # 检查是否有新的网络请求
                if len(self.network_logs) > 0:
                    logger.info(f"捕获到 {len(self.network_logs)} 个网络请求")
                    
            # 分析捕获的网络请求
            self.analyze_network_logs()
            
        except Exception as e:
            logger.error(f"分析Vheer页面失败: {e}")
            
    def analyze_network_logs(self):
        """分析网络日志"""
        logger.info("=== 分析网络请求 ===")
        
        api_requests = []
        
        for log in self.network_logs:
            try:
                message = log['message']
                
                if message['method'] == 'Network.requestWillBeSent':
                    request = message['params']['request']
                    url = request['url']
                    method = request['method']
                    
                    # 过滤出可能的API请求
                    if any(keyword in url.lower() for keyword in ['api', 'generate', 'create', 'submit']):
                        api_info = {
                            'url': url,
                            'method': method,
                            'headers': request.get('headers', {}),
                            'postData': request.get('postData', '')
                        }
                        api_requests.append(api_info)
                        
                        logger.info(f"发现API请求: {method} {url}")
                        
                        # 打印请求详情
                        if request.get('postData'):
                            logger.info(f"  POST数据: {request['postData'][:200]}...")
                            
            except Exception as e:
                logger.error(f"分析网络日志条目失败: {e}")
                
        # 保存API请求到文件
        if api_requests:
            with open('vheer_api_requests.json', 'w', encoding='utf-8') as f:
                json.dump(api_requests, f, indent=2, ensure_ascii=False)
            logger.info(f"保存了 {len(api_requests)} 个API请求到 vheer_api_requests.json")
        else:
            logger.warning("未发现任何API请求")
            
    def get_page_source_analysis(self):
        """获取页面源码分析"""
        try:
            # 获取页面源码
            page_source = self.driver.page_source
            
            # 查找可能的API端点
            import re
            
            patterns = [
                r'fetch\(["\']([^"\']+)["\']',
                r'axios\.[a-z]+\(["\']([^"\']+)["\']',
                r'\.post\(["\']([^"\']+)["\']',
                r'\.get\(["\']([^"\']+)["\']',
                r'action=["\']([^"\']+)["\']',
                r'url:["\s]*["\']([^"\']+)["\']',
                r'endpoint:["\s]*["\']([^"\']+)["\']',
            ]
            
            found_endpoints = set()
            for pattern in patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                for match in matches:
                    if any(keyword in match.lower() for keyword in ['api', 'generate', 'create', 'submit']):
                        found_endpoints.add(match)
                        
            if found_endpoints:
                logger.info("从页面源码中发现的端点:")
                for endpoint in sorted(found_endpoints):
                    logger.info(f"  - {endpoint}")
                    
            return found_endpoints
            
        except Exception as e:
            logger.error(f"分析页面源码失败: {e}")
            return set()
            
    def cleanup(self):
        """清理资源"""
        if self.driver:
            self.driver.quit()
            logger.info("浏览器已关闭")

def main():
    """主函数"""
    analyzer = VheerBrowserAnalyzer()
    
    try:
        if not analyzer.setup_driver():
            logger.error("无法启动浏览器，退出程序")
            return
            
        logger.info("开始分析Vheer网站...")
        
        # 分析页面
        analyzer.analyze_vheer_page()
        
        # 分析页面源码
        analyzer.get_page_source_analysis()
        
        logger.info("分析完成")
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
    finally:
        analyzer.cleanup()

if __name__ == "__main__":
    main()
