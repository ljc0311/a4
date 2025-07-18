#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Selenium的发布器基类
参考MoneyPrinterPlus的设计思路，使用Selenium替代Playwright
"""

import os
import time
import json
import asyncio  # 🔧 修复：添加asyncio导入
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
            'headless': False,
            'simulation_mode': False  # 新增：模拟模式，用于测试
        }

        # 🔧 新增：登录状态保存配置
        self.login_state_file = f"login_state_{platform_name}.json"
        self.login_state_dir = os.path.join(os.path.expanduser("~"), ".ai_video_generator", "login_states")
        os.makedirs(self.login_state_dir, exist_ok=True)
        
        # 合并配置
        self.selenium_config = {**self.default_config, **config}
        
    def initialize(self) -> bool:
        """初始化发布器（改为同步方法）"""
        try:
            # 检查是否启用模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info(f"🎭 {self.platform_name} 启用模拟模式，跳过真实浏览器启动")
                self.driver = None  # 模拟模式下不创建真实驱动
                self.wait = None
                logger.info(f"{self.platform_name} 模拟模式初始化完成")
                return True

            self._init_driver()
            return True
        except Exception as e:
            logger.error(f"{self.platform_name} 发布器初始化失败: {e}")
            return False
            
    def _init_driver(self):
        """初始化Selenium驱动（改为同步方法）"""
        try:
            logger.info(f"开始初始化 {self.platform_name} Selenium驱动...")

            # 检查是否启用模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info(f"🎭 {self.platform_name} 启用模拟模式，跳过真实浏览器启动")
                self.driver = None  # 模拟模式下不创建真实驱动
                self.wait = None
                logger.info(f"{self.platform_name} 模拟模式初始化完成")
                return

            driver_type = self.selenium_config['driver_type']

            if driver_type == 'chrome':
                self._init_chrome_driver()
            elif driver_type == 'firefox':
                self._init_firefox_driver()
            else:
                raise ValueError(f"不支持的驱动类型: {driver_type}")

            # 设置等待（只有在驱动创建成功后才设置）
            if self.driver:
                self.wait = WebDriverWait(self.driver, self.selenium_config['timeout'])
                logger.info(f"{self.platform_name} Selenium驱动初始化完成")
            else:
                raise RuntimeError("驱动创建失败，driver为None")

        except Exception as e:
            logger.error(f"{self.platform_name} Selenium驱动初始化失败: {e}")
            # 清理资源
            try:
                if hasattr(self, 'driver') and self.driver:
                    self.driver.quit()
                    self.driver = None
            except:
                pass
            raise
            
    def _init_chrome_driver(self):
        """初始化Chrome驱动"""
        options = ChromeOptions()

        # 基本选项
        if self.selenium_config['headless']:
            options.add_argument('--headless')

        # 🔧 优先尝试调试模式连接
        debugger_address = self.selenium_config.get('debugger_address', '127.0.0.1:9222')

        # 首先尝试连接到调试模式的Chrome
        try:
            logger.info(f"尝试连接到Chrome调试模式: {debugger_address}")

            # 创建新的选项对象，专门用于调试模式
            debug_options = ChromeOptions()
            debug_options.add_experimental_option("debuggerAddress", debugger_address)

            # 添加必要的选项
            debug_options.add_argument("--no-sandbox")
            debug_options.add_argument("--disable-dev-shm-usage")

            # 禁用版本检查
            os.environ['WDM_LOG_LEVEL'] = '0'
            os.environ['WDM_PRINT_FIRST_LINE'] = 'False'
            os.environ['CHROME_DRIVER_DISABLE_VERSION_CHECK'] = '1'
            os.environ['SELENIUM_DISABLE_VERSION_CHECK'] = '1'

            # 使用项目中的ChromeDriver
            chromedriver_path = os.path.join(os.getcwd(), "chromedriver.exe")
            if os.path.exists(chromedriver_path):
                service = ChromeService(
                    executable_path=chromedriver_path,
                    service_args=['--verbose', '--log-path=chromedriver.log']
                )
                logger.info(f"使用项目中的ChromeDriver: {chromedriver_path}")
                self.driver = webdriver.Chrome(service=service, options=debug_options)
            else:
                logger.info("使用系统PATH中的ChromeDriver")
                self.driver = webdriver.Chrome(options=debug_options)

            # 测试连接
            current_url = self.driver.current_url
            logger.info(f"✅ 成功连接到Chrome调试模式，当前URL: {current_url}")
            return

        except Exception as e:
            logger.warning(f"连接Chrome调试模式失败: {e}")
            logger.info("🔄 切换到普通模式启动Chrome...")

            # 清理失败的驱动
            try:
                if hasattr(self, 'driver') and self.driver:
                    self.driver.quit()
                    self.driver = None
            except:
                pass

        # 如果调试模式失败，使用普通模式
        options = ChromeOptions()  # 重新创建选项，移除调试地址

        # 基本选项
        if self.selenium_config['headless']:
            options.add_argument('--headless')

        # 添加反检测选项
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

        # 🔧 修复SSL错误和网络问题（移除不安全的--disable-web-security参数）
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
        import threading
        import time

        driver_created = False
        driver_error = None

        def create_driver():
            nonlocal driver_created, driver_error
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

                # 设置页面加载超时
                self.driver.set_page_load_timeout(30)
                self.driver.implicitly_wait(self.selenium_config['implicit_wait'])

                driver_created = True
                logger.info("Chrome普通模式启动成功")
            except Exception as e:
                driver_error = e
                logger.error(f"Chrome驱动创建线程中出错: {e}")

        try:
            # 创建线程启动驱动
            driver_thread = threading.Thread(target=create_driver)
            driver_thread.daemon = True
            driver_thread.start()

            # 等待30秒
            timeout = 30
            start_time = time.time()
            while not driver_created and time.time() - start_time < timeout:
                if driver_error:
                    raise driver_error
                time.sleep(0.5)

            # 检查是否超时
            if not driver_created:
                logger.error("Chrome驱动启动超时（30秒）")

                logger.error("尝试使用headless模式...")
                # 尝试headless模式
                try:
                    options.add_argument('--headless')
                    self.driver = webdriver.Chrome(options=options)
                    self.driver.set_page_load_timeout(30)
                    self.driver.implicitly_wait(self.selenium_config['implicit_wait'])
                    logger.info("Chrome headless模式启动成功")
                except Exception as e2:
                    logger.error(f"Chrome headless模式也失败: {e2}")
                    raise TimeoutError("Chrome驱动启动超时，所有模式都失败")

            if driver_error:
                raise driver_error

        except Exception as e:
            logger.error(f"Chrome驱动创建失败: {e}")
            logger.error("可能的解决方案:")
            logger.error("1. 确保Chrome已正确安装")
            logger.error("2. 检查ChromeDriver版本是否与Chrome版本匹配")
            logger.error("3. 尝试重新下载ChromeDriver")
            logger.error("4. 检查是否有其他Chrome进程占用")
            logger.error("5. 尝试重启计算机")

            # 清理可能的残留进程
            try:
                if hasattr(self, 'driver') and self.driver:
                    self.driver.quit()
            except:
                pass
            raise


            
    def _init_firefox_driver(self):
        """🔧 优化：初始化Firefox驱动（用户友好模式）"""
        logger.info("🦊 开始初始化Firefox驱动...")

        options = FirefoxOptions()

        # 基本配置
        if self.selenium_config['headless']:
            options.add_argument('--headless')

        # 🔧 用户友好配置
        options.set_preference("dom.webdriver.enabled", False)  # 隐藏webdriver标识
        options.set_preference("useAutomationExtension", False)  # 禁用自动化扩展
        options.set_preference("general.useragent.override",
                             "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")

        # 禁用通知和弹窗
        options.set_preference("dom.push.enabled", False)
        options.set_preference("dom.webnotifications.enabled", False)

        # 🔧 优化：网络和性能配置
        options.set_preference("network.http.connection-timeout", 60)  # 连接超时60秒
        options.set_preference("network.http.response.timeout", 60)    # 响应超时60秒
        options.set_preference("dom.max_script_run_time", 60)          # 脚本运行超时60秒
        options.set_preference("browser.cache.disk.enable", True)     # 启用磁盘缓存
        options.set_preference("browser.cache.memory.enable", True)   # 启用内存缓存

        # 禁用图片加载以提高速度（可选）
        # options.set_preference("permissions.default.image", 2)  # 0=允许, 1=询问, 2=禁止

        # 禁用CSS和JavaScript（如果不需要页面交互，可以启用以提高速度）
        # options.set_preference("javascript.enabled", False)
        # options.set_preference("permissions.default.stylesheet", 2)

        try:
            # 🔧 简化：直接创建Firefox驱动，无需调试模式
            driver_location = self.selenium_config.get('driver_location')
            if driver_location and os.path.exists(driver_location):
                service = FirefoxService(driver_location)
                logger.info(f"使用指定的GeckoDriver: {driver_location}")
                self.driver = webdriver.Firefox(service=service, options=options)
            else:
                # 使用系统PATH中的geckodriver
                logger.info("使用系统PATH中的GeckoDriver")
                self.driver = webdriver.Firefox(options=options)

            # 🔧 优化：设置更长的页面加载超时
            self.driver.set_page_load_timeout(90)  # 增加到90秒
            self.driver.implicitly_wait(self.selenium_config.get('implicit_wait', 15))  # 增加到15秒

            # 设置脚本执行超时
            self.driver.set_script_timeout(60)  # 脚本执行超时60秒

            logger.info("🦊 Firefox驱动初始化成功")

        except Exception as e:
            logger.error(f"🦊 Firefox驱动初始化失败: {e}")
            # 提供用户友好的错误提示
            if "geckodriver" in str(e).lower():
                logger.error("💡 请确保已安装GeckoDriver或Firefox浏览器")
                logger.error("💡 下载地址: https://github.com/mozilla/geckodriver/releases")
            raise
            
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """认证实现 - 简化版本，依赖用户手动登录"""
        try:
            # 检查是否启用模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info(f"🎭 {self.platform_name} 模拟模式：模拟登录成功")
                self.is_authenticated = True
                return True

            if not self.driver:
                self._init_driver()

            # 🔧 优化：导航到平台页面，增加重试机制
            platform_url = self._get_platform_url()
            logger.info(f"访问 {self.platform_name} 页面: {platform_url}")

            # 尝试多次访问页面
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"第 {attempt + 1}/{max_retries} 次尝试访问页面...")

                    # 使用JavaScript导航，更可靠
                    self.driver.execute_script(f"window.location.href = '{platform_url}';")

                    # 等待页面开始加载
                    time.sleep(5)

                    # 检查页面是否加载成功
                    current_url = self.driver.current_url
                    if platform_url.split('/')[-1] in current_url or self.platform_name in current_url:
                        logger.info(f"✅ 页面访问成功: {current_url}")
                        break
                    else:
                        logger.warning(f"⚠️ 页面可能未完全加载: {current_url}")

                except Exception as e:
                    logger.warning(f"第 {attempt + 1} 次访问失败: {e}")
                    if attempt == max_retries - 1:
                        # 最后一次尝试失败，使用传统方法
                        logger.info("使用传统方法访问页面...")
                        self.driver.get(platform_url)
                        time.sleep(8)  # 增加等待时间

            # 🔧 新增：尝试加载已保存的登录状态
            logger.info(f"🔄 尝试恢复 {self.platform_name} 登录状态...")
            if self.load_login_state():
                # 验证恢复的登录状态是否有效
                await self._wait_for_page_ready()
                if await self._check_login_status():
                    self.is_authenticated = True
                    logger.info(f"🎉 {self.platform_name} 登录状态恢复成功！")
                    return True
                else:
                    logger.warning(f"⚠️ {self.platform_name} 保存的登录状态已失效")
                    self.clear_login_state()

            # 🔧 优化：等待页面完全加载
            await self._wait_for_page_ready()

            # 检查登录状态
            if await self._check_login_status():
                self.is_authenticated = True
                logger.info(f"✅ {self.platform_name} 已登录")
                # 保存登录状态
                self.save_login_state()
                return True
            else:
                logger.warning(f"⚠️ {self.platform_name} 未登录，需要手动登录")
                logger.info(f"🔗 请在Firefox浏览器中登录 {self.platform_name}")
                logger.info(f"📍 当前页面: {self.driver.current_url}")

                # 给用户一些时间手动登录
                logger.info("等待30秒供用户登录...")
                await asyncio.sleep(30)

                # 再次检查登录状态
                if await self._check_login_status():
                    self.is_authenticated = True
                    logger.info(f"✅ {self.platform_name} 登录成功")
                    # 🔧 新增：保存登录状态
                    self.save_login_state()
                    return True
                else:
                    logger.error(f"❌ {self.platform_name} 登录验证失败")
                    logger.info("💡 请确保在Firefox中完成登录后重试")
                    return False
                    
        except Exception as e:
            logger.error(f"{self.platform_name} 认证失败: {e}")
            return False

    async def _wait_for_page_ready(self, timeout: int = 30):
        """🔧 新增：等待页面完全加载"""
        try:
            logger.info("⏳ 等待页面完全加载...")

            # 等待页面加载状态变为complete
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    ready_state = self.driver.execute_script("return document.readyState")
                    if ready_state == "complete":
                        logger.info("✅ 页面加载完成")
                        break
                except:
                    pass
                await asyncio.sleep(1)

            # 额外等待JavaScript执行
            await asyncio.sleep(3)

            # 检查页面是否有基本内容
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                if body and len(body.text.strip()) > 0:
                    logger.info("✅ 页面内容检测正常")
                else:
                    logger.warning("⚠️ 页面内容可能未完全加载")
            except:
                logger.warning("⚠️ 无法检测页面内容")

        except Exception as e:
            logger.warning(f"页面就绪检测失败: {e}")

    def save_login_state(self):
        """🔧 新增：保存登录状态（Cookies和Session）"""
        try:
            if not self.driver:
                return

            login_state_path = os.path.join(self.login_state_dir, self.login_state_file)

            # 获取当前页面的cookies
            cookies = self.driver.get_cookies()

            # 获取当前URL和页面信息
            current_url = self.driver.current_url
            page_title = self.driver.title

            # 保存登录状态
            login_state = {
                'platform': self.platform_name,
                'cookies': cookies,
                'current_url': current_url,
                'page_title': page_title,
                'timestamp': time.time(),
                'user_agent': self.driver.execute_script("return navigator.userAgent;")
            }

            with open(login_state_path, 'w', encoding='utf-8') as f:
                json.dump(login_state, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ {self.platform_name} 登录状态已保存: {login_state_path}")

        except Exception as e:
            logger.error(f"❌ 保存 {self.platform_name} 登录状态失败: {e}")

    def load_login_state(self) -> bool:
        """🔧 新增：加载登录状态"""
        try:
            login_state_path = os.path.join(self.login_state_dir, self.login_state_file)

            if not os.path.exists(login_state_path):
                logger.info(f"📝 {self.platform_name} 登录状态文件不存在")
                return False

            with open(login_state_path, 'r', encoding='utf-8') as f:
                login_state = json.load(f)

            # 检查登录状态是否过期（24小时）
            if time.time() - login_state.get('timestamp', 0) > 24 * 3600:
                logger.warning(f"⏰ {self.platform_name} 登录状态已过期")
                return False

            if not self.driver:
                return False

            # 先访问平台主页
            platform_url = self._get_platform_url()
            base_url = '/'.join(platform_url.split('/')[:3])  # 获取域名

            logger.info(f"🔄 加载 {self.platform_name} 登录状态...")
            self.driver.get(base_url)
            time.sleep(2)

            # 恢复cookies
            for cookie in login_state.get('cookies', []):
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"添加cookie失败: {e}")

            # 刷新页面以应用cookies
            self.driver.refresh()
            time.sleep(3)

            logger.info(f"✅ {self.platform_name} 登录状态已恢复")
            return True

        except Exception as e:
            logger.error(f"❌ 加载 {self.platform_name} 登录状态失败: {e}")
            return False

    def clear_login_state(self):
        """🔧 新增：清除登录状态"""
        try:
            login_state_path = os.path.join(self.login_state_dir, self.login_state_file)
            if os.path.exists(login_state_path):
                os.remove(login_state_path)
                logger.info(f"🗑️ {self.platform_name} 登录状态已清除")
        except Exception as e:
            logger.error(f"❌ 清除 {self.platform_name} 登录状态失败: {e}")

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
            self._init_driver()
            return self._check_session_valid()

        except Exception as e:
            logger.error(f"重新初始化驱动失败: {e}")
            return False

    async def publish_video(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """发布视频"""
        try:
            # 检查是否启用模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info(f"🎭 {self.platform_name} 模拟模式：模拟视频发布")
                # 生成一个模拟的成功结果
                video_title = video_info.get('title', '未命名视频')
                mock_result = {
                    'success': True,
                    'video_id': f"mock_{int(time.time())}",
                    'video_url': f"https://{self.platform_name}.example.com/video/mock_{int(time.time())}",
                    'platform': self.platform_name,
                    'title': video_title,
                    'upload_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f"模拟发布成功: {video_title}"
                }
                logger.info(f"🎭 {self.platform_name} 模拟发布成功: {video_title}")
                return mock_result

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
        """🔧 优化：安全上传文件，修复路径问题"""
        try:
            # 🔧 修复：规范化文件路径
            normalized_path = os.path.normpath(file_path)
            absolute_path = os.path.abspath(normalized_path)

            logger.info(f"🔍 检查文件路径:")
            logger.info(f"  原始路径: {file_path}")
            logger.info(f"  规范化路径: {normalized_path}")
            logger.info(f"  绝对路径: {absolute_path}")

            # 检查文件是否存在
            if not os.path.exists(absolute_path):
                logger.error(f"❌ 文件不存在: {absolute_path}")

                # 🔧 新增：尝试其他可能的路径格式
                alternative_paths = [
                    file_path.replace('/', '\\'),  # 正斜杠转反斜杠
                    file_path.replace('\\', '/'),  # 反斜杠转正斜杠
                    os.path.join(*file_path.split('/')),  # 使用os.path.join重建路径
                    os.path.join(*file_path.split('\\'))  # 使用os.path.join重建路径
                ]

                for alt_path in alternative_paths:
                    if os.path.exists(alt_path):
                        logger.info(f"✅ 找到替代路径: {alt_path}")
                        absolute_path = os.path.abspath(alt_path)
                        break
                else:
                    # 列出目录内容帮助调试
                    parent_dir = os.path.dirname(absolute_path)
                    if os.path.exists(parent_dir):
                        logger.info(f"📁 父目录内容: {parent_dir}")
                        try:
                            files = os.listdir(parent_dir)
                            for f in files[:10]:  # 只显示前10个文件
                                logger.info(f"  - {f}")
                        except:
                            pass
                    return False

            logger.info(f"✅ 使用文件路径: {absolute_path}")

            # 查找上传元素
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )

            # 🔧 优化：使用绝对路径上传
            element.send_keys(absolute_path)
            logger.info(f"✅ 文件上传命令已发送")
            return True

        except TimeoutException:
            logger.warning(f"⏰ 文件上传超时: {by}={value}")
            return False
        except Exception as e:
            logger.error(f"❌ 文件上传异常: {e}")
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
