#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Selenium的发布器基类
参考MoneyPrinterPlus的设计思路，使用Selenium替代Playwright
"""

import os
import time
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.utils.logger import logger


class SeleniumPublisherBase(ABC):
    """基于Selenium的发布器基类"""
    
    def __init__(self, platform_name: str, config: Dict[str, Any]):
        self.platform_name = platform_name
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.is_authenticated = False
        
        # 默认配置
        self.default_config = {
            'driver_type': 'chrome',
            'driver_location': '',
            'debugger_address': '127.0.0.1:9222',
            'timeout': 30,
            'implicit_wait': 10,
            'headless': False
        }
        
        # 合并配置
        self.selenium_config = {**self.default_config, **config}
        
    async def initialize(self) -> bool:
        """初始化发布器"""
        try:
            await self._init_driver()
            return True
        except Exception as e:
            logger.error(f"{self.platform_name} 发布器初始化失败: {e}")
            return False
            
    async def _init_driver(self):
        """初始化Selenium驱动"""
        try:
            driver_type = self.selenium_config['driver_type']
            
            if driver_type == 'chrome':
                self._init_chrome_driver()
            elif driver_type == 'firefox':
                self._init_firefox_driver()
            else:
                raise ValueError(f"不支持的驱动类型: {driver_type}")
                
            # 设置等待
            self.driver.implicitly_wait(self.selenium_config['implicit_wait'])
            self.wait = WebDriverWait(self.driver, self.selenium_config['timeout'])
            
            logger.info(f"{self.platform_name} Selenium驱动初始化完成")
            
        except Exception as e:
            logger.error(f"{self.platform_name} Selenium驱动初始化失败: {e}")
            raise
            
    def _init_chrome_driver(self):
        """初始化Chrome驱动"""
        options = ChromeOptions()

        # 基本选项
        if self.selenium_config['headless']:
            options.add_argument('--headless')

        # 🔧 临时修复：跳过调试模式，直接使用普通模式
        logger.info("使用普通模式启动Chrome（跳过调试模式）")

        # 添加反检测选项
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # 🔧 修复SSL错误和网络问题
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors-spki-list')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')  # 减少网络请求

        # 🔧 减少日志输出
        options.add_argument('--log-level=3')  # 只显示致命错误
        options.add_argument('--silent')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)

        # 🔧 优化性能
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-backgrounding-occluded-windows')

        # 设置用户数据目录以保持登录状态
        user_data_dir = os.path.join(os.getcwd(), "selenium_chrome_data")
        os.makedirs(user_data_dir, exist_ok=True)
        options.add_argument(f'--user-data-dir={user_data_dir}')

        # 🔧 修复：添加驱动创建超时处理
        try:
            # 创建Chrome驱动
            driver_location = self.selenium_config.get('driver_location')
            if driver_location and os.path.exists(driver_location):
                service = ChromeService(driver_location)
                logger.info(f"使用指定的ChromeDriver: {driver_location}")
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                # 使用系统PATH中的chromedriver
                logger.info("使用系统PATH中的ChromeDriver")
                self.driver = webdriver.Chrome(options=options)

            logger.info("Chrome普通模式启动成功")

        except Exception as e:
            logger.error(f"Chrome驱动创建失败: {e}")
            logger.error("可能的解决方案:")
            logger.error("1. 确保Chrome已正确安装")
            logger.error("2. 检查ChromeDriver版本是否与Chrome版本匹配")
            logger.error("3. 尝试重新下载ChromeDriver")
            raise
            
    def _init_firefox_driver(self):
        """初始化Firefox驱动"""
        options = FirefoxOptions()
        
        if self.selenium_config['headless']:
            options.add_argument('--headless')
            
        # Firefox调试模式
        debugger_address = self.selenium_config.get('debugger_address', '127.0.0.1:2828')
        
        # 创建服务
        driver_location = self.selenium_config.get('driver_location')
        if driver_location and os.path.exists(driver_location):
            service = FirefoxService(
                driver_location,
                service_args=['--marionette-port', '2828', '--connect-existing']
            )
            self.driver = webdriver.Firefox(service=service, options=options)
        else:
            self.driver = webdriver.Firefox(options=options)
            
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """认证实现 - 简化版本，依赖用户手动登录"""
        try:
            if not self.driver:
                await self._init_driver()
                
            # 导航到平台页面
            platform_url = self._get_platform_url()
            logger.info(f"访问 {self.platform_name} 页面: {platform_url}")
            
            self.driver.get(platform_url)
            time.sleep(3)
            
            # 检查登录状态
            if await self._check_login_status():
                self.is_authenticated = True
                logger.info(f"{self.platform_name} 已登录")
                return True
            else:
                logger.warning(f"{self.platform_name} 未登录，请手动登录后重试")
                # 等待用户手动登录
                input(f"请在浏览器中手动登录 {self.platform_name}，完成后按回车继续...")
                
                # 再次检查登录状态
                if await self._check_login_status():
                    self.is_authenticated = True
                    logger.info(f"{self.platform_name} 登录成功")
                    return True
                else:
                    logger.error(f"{self.platform_name} 登录验证失败")
                    return False
                    
        except Exception as e:
            logger.error(f"{self.platform_name} 认证失败: {e}")
            return False

    def _check_session_valid(self) -> bool:
        """检查Selenium会话是否有效"""
        try:
            if not self.driver:
                return False
            # 尝试获取当前URL来测试会话
            _ = self.driver.current_url
            return True
        except Exception as e:
            logger.warning(f"Selenium会话无效: {e}")
            return False

    async def _ensure_driver_ready(self) -> bool:
        """确保驱动准备就绪，如果会话无效则重新初始化"""
        if self._check_session_valid():
            return True

        logger.info("检测到会话无效，正在重新初始化Chrome驱动...")
        try:
            # 清理旧的驱动
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

            # 重新初始化
            await self._init_driver()
            return self._check_session_valid()

        except Exception as e:
            logger.error(f"重新初始化驱动失败: {e}")
            return False

    async def publish_video(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """发布视频"""
        try:
            # 确保驱动准备就绪
            if not await self._ensure_driver_ready():
                logger.error(f"{self.platform_name} 驱动初始化失败")
                return {'success': False, 'error': '驱动初始化失败'}

            if not self.is_authenticated:
                logger.error(f"{self.platform_name} 未认证，无法发布")
                return {'success': False, 'error': '未认证'}

            logger.info(f"开始发布视频到 {self.platform_name}")

            # 调用具体平台的发布实现
            result = await self._publish_video_impl(video_info)

            if result.get('success'):
                logger.info(f"{self.platform_name} 视频发布成功")
            else:
                logger.error(f"{self.platform_name} 视频发布失败: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"{self.platform_name} 发布视频失败: {e}")
            return {'success': False, 'error': str(e)}
            
    async def cleanup(self):
        """清理资源"""
        try:
            if self.driver:
                # 不关闭浏览器，保持连接状态供下次使用
                logger.info(f"{self.platform_name} 保持浏览器连接状态")
        except Exception as e:
            logger.error(f"{self.platform_name} 清理资源失败: {e}")
            
    # 辅助方法
    def find_element_safe(self, by: By, value: str, timeout: int = 10) -> Optional[Any]:
        """安全查找元素"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.warning(f"元素未找到: {by}={value}")
            return None
            
    def click_element_safe(self, by: By, value: str, timeout: int = 10) -> bool:
        """安全点击元素"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
            return True
        except TimeoutException:
            logger.warning(f"元素不可点击: {by}={value}")
            return False
            
    def send_keys_safe(self, by: By, value: str, text: str, timeout: int = 10) -> bool:
        """安全输入文本"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            element.clear()
            element.send_keys(text)
            return True
        except TimeoutException:
            logger.warning(f"元素输入失败: {by}={value}")
            return False
            
    def upload_file_safe(self, by: By, value: str, file_path: str, timeout: int = 10) -> bool:
        """安全上传文件"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return False
                
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            element.send_keys(file_path)
            return True
        except TimeoutException:
            logger.warning(f"文件上传失败: {by}={value}")
            return False
            
    # 抽象方法 - 子类必须实现
    @abstractmethod
    def _get_platform_url(self) -> str:
        """获取平台URL"""
        pass
        
    @abstractmethod
    async def _check_login_status(self) -> bool:
        """检查登录状态"""
        pass
        
    @abstractmethod
    async def _publish_video_impl(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """具体的视频发布实现"""
        pass
