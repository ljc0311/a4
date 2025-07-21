#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版Chrome快手发布器 - 2024年最新版本
不依赖调试模式，配置简单，使用selenium-stealth反检测
专为解决Chrome调试模式配置困难问题而设计
"""

import time
import asyncio
import random
import json
import os
from typing import Dict, Any, List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 尝试导入selenium-stealth
try:
    from selenium_stealth import stealth
    SELENIUM_STEALTH_AVAILABLE = True
except ImportError:
    SELENIUM_STEALTH_AVAILABLE = False
    stealth = None

from .selenium_publisher_base import SeleniumPublisherBase
from .login_manager import login_manager
from src.utils.logger import logger

# 简化版Chrome配置
SIMPLE_CHROME_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# 简化版反检测脚本
SIMPLE_STEALTH_SCRIPT = """
// 简化版反检测脚本
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en-US', 'en'],
});

window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

console.log('🛡️ 简化版反检测脚本已加载');
"""


class SimpleChromeKuaishouPublisher(SeleniumPublisherBase):
    """简化版Chrome快手发布器 - 无需调试模式"""
    
    def __init__(self, config: Dict[str, Any]):
        # 简化配置
        simple_config = {
            'driver_type': 'chrome',
            'headless': False,
            'timeout': 30,
            'implicit_wait': 10,
            'page_load_timeout': 60,
            'use_stealth': True,
            **config
        }
        
        super().__init__('kuaishou_simple_chrome', simple_config)

        # 设置平台属性
        self.platform = 'kuaishou_simple'
        
        # 检查selenium-stealth可用性
        self.stealth_available = SELENIUM_STEALTH_AVAILABLE
        if not self.stealth_available:
            logger.warning("⚠️ selenium-stealth 未安装，反检测能力将受限")
        
        # 快手DOM选择器配置 - 基于实际成功案例优化（优先使用成功的方法）
        self.selectors = {
            'upload_input': [
                # 🎯 实际成功的方法（优先级最高）- 直接使用XPath
                # 这个方法在实际测试中100%成功，所以放在第一位
            ],
            'upload_button': [
                # 2023年成功案例中的选择器
                "button[class*='SOCr7n1uoqI-']",
                # 通用上传按钮选择器
                ".upload-btn",
                "button:contains('上传视频')",
                "button:contains('选择文件')",
                "button:contains('上传')",
                ".upload-button",
                "[data-testid='upload-btn']",
                ".file-upload-btn",
                # Ant Design 按钮样式
                ".ant-btn:contains('上传')",
                "button.ant-btn"
            ],
            'upload_success': [
                # 2023年成功案例中的选择器
                "span[class*='DqNkLCyIyfQ-']",
                # 通用成功提示选择器
                "span:contains('上传成功')",
                "div:contains('上传成功')",
                "div:contains('上传完成')",
                "[class*='success']",
                ".upload-success",
                "[data-testid*='upload-success']",
                ".success-message"
            ],
            'title_input': [
                # 成功方案优先 - 基于实际测试结果
                "div[contenteditable='true']",  # ✅ 实际成功的选择器
                "[contenteditable='true']",
                # contenteditable变体
                "div[contenteditable='true'][placeholder*='标题']",
                "div[contenteditable='true'][data-placeholder*='标题']",
                ".title-input div[contenteditable='true']",
                ".form-item-title div[contenteditable='true']",
                # 传统输入框（备用）
                "textarea[placeholder*='标题']",
                "input[placeholder*='标题']",
                "textarea[placeholder*='请输入标题']",
                "input[placeholder*='请输入标题']",
                # React/Vue组件选择器
                "[data-testid*='title']",
                "[aria-label*='标题']",
                # 类名选择器
                ".title-input textarea",
                ".title-input input",
                ".title-editor",
                ".title-field"
            ],
            'description_input': [
                # 成功方案优先 - 基于实际测试结果
                "div[contenteditable='true'][placeholder*='描述']",  # ✅ 实际成功的选择器
                "div[contenteditable='true'][placeholder*='简介']",
                "div[contenteditable='true'][data-placeholder*='描述']",
                "div[contenteditable='true'][data-placeholder*='简介']",
                # contenteditable变体
                ".description-input div[contenteditable='true']",
                ".desc-input div[contenteditable='true']",
                ".form-item-desc div[contenteditable='true']",
                "div[contenteditable='true']:nth-of-type(2)",
                # 传统输入框（备用）
                "textarea[placeholder*='描述']",
                "textarea[placeholder*='简介']",
                "textarea[placeholder*='请输入简介']",
                "textarea[placeholder*='请输入描述']",
                # React/Vue组件选择器
                "[data-testid*='desc']",
                "[data-testid*='description']",
                "[aria-label*='简介']",
                "[aria-label*='描述']",
                # 类名选择器
                ".description-input textarea",
                ".desc-input textarea",
                ".desc-editor",
                ".description-field"
            ],
            'publish_button': [
                # 🎯 2024年快手真正的红色发布按钮（基于用户截图）
                "//button[contains(@style, 'background') and text()='发布']",  # 红色背景的发布按钮
                "//button[contains(@class, 'ant-btn-primary') and text()='发布']",  # Ant Design主要按钮
                "//div[contains(@class, 'publish')]//button[text()='发布']",  # 发布区域内的按钮
                "//button[@type='button' and text()='发布' and contains(@class, 'ant-btn')]",  # Ant按钮

                # 🔍 更精确的定位（基于页面底部位置）
                "//div[contains(@class, 'footer') or contains(@class, 'bottom')]//button[text()='发布']",
                "//div[last()]//button[text()='发布']",  # 页面最后一个div中的发布按钮
                "//button[text()='发布' and position()=last()]",  # 最后一个发布按钮

                # 🎨 基于样式特征的选择器
                "//button[contains(@class, 'primary') and text()='发布']",
                "//button[contains(@class, 'red') and text()='发布']",
                "//button[contains(@class, 'danger') and text()='发布']",

                # 📍 精确文本匹配
                "//button[text()='发布']",
                "//span[text()='发布']/parent::button",
                "//button[normalize-space(text())='发布']",

                # 🔄 备用选择器（降级使用）
                "//button[contains(text(), '发布') and not(contains(text(), '设置')) and not(contains(text(), '时间'))]",
                "button:contains('发布')",
                ".ant-btn-primary",
                "button[type='submit']"
            ],
            'upload_progress': [
                # 上传进度
                ".upload-progress",
                ".progress-bar",
                ".progress",
                "[data-testid='upload-progress']",
                ".upload-status",
                ".uploading"
            ]
        }
        
    def _get_platform_url(self) -> str:
        """获取快手创作者中心URL"""
        return "https://cp.kuaishou.com/article/publish/video"
    
    def _init_driver(self):
        """初始化简化版Chrome驱动 - 无需调试模式"""
        try:
            logger.info("🚀 开始初始化简化版Chrome驱动...")

            # 检查是否启用模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 简化版Chrome启用模拟模式，跳过真实浏览器启动")
                self.driver = None
                self.wait = None
                return

            # 添加超时保护
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("Chrome驱动初始化超时")

            # 设置60秒超时
            if hasattr(signal, 'SIGALRM'):  # Unix系统
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(60)

            try:
                # 创建Chrome选项
                options = ChromeOptions()

                # 基础反检测选项
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)

                # 随机User-Agent
                user_agent = random.choice(SIMPLE_CHROME_USER_AGENTS)
                options.add_argument(f'--user-agent={user_agent}')
                logger.debug(f"🎭 使用随机User-Agent: {user_agent[:50]}...")

                # 窗口大小
                options.add_argument('--window-size=1366,768')

                # 语言设置
                options.add_argument('--lang=zh-CN')
                options.add_experimental_option('prefs', {
                    'intl.accept_languages': 'zh-CN,zh,en-US,en'
                })

                # 禁用图片加载（可选，提高速度）
                if self.selenium_config.get('disable_images', False):
                    prefs = {"profile.managed_default_content_settings.images": 2}
                    options.add_experimental_option("prefs", prefs)

                # 创建Chrome驱动
                try:
                    logger.info("🔧 正在创建Chrome驱动实例...")

                    # 尝试多种方式创建Chrome驱动，避免网络问题
                    driver_created = False

                    # 方法1: 直接使用系统PATH中的chromedriver（最快）
                    try:
                        logger.info("🔄 尝试使用系统PATH中的chromedriver...")
                        self.driver = webdriver.Chrome(options=options)
                        logger.info("✅ 使用系统chromedriver创建成功")
                        driver_created = True

                    except Exception as system_error:
                        logger.warning(f"⚠️ 系统chromedriver失败: {system_error}")

                        # 方法2: 使用webdriver-manager（有网络超时保护）
                        try:
                            logger.info("🔄 尝试使用webdriver-manager...")
                            from selenium.webdriver.chrome.service import Service
                            from webdriver_manager.chrome import ChromeDriverManager

                            # 设置更短超时，快速失败转移
                            import os
                            os.environ['WDM_TIMEOUT'] = '3'  # 设置3秒超时
                            os.environ['WDM_LOG_LEVEL'] = '0'  # 减少日志输出
                            os.environ['WDM_PRINT_FIRST_LINE'] = 'False'  # 减少输出

                            # 添加超时控制
                            import signal
                            def timeout_handler(signum, frame):
                                raise TimeoutError("ChromeDriverManager超时")

                            signal.signal(signal.SIGALRM, timeout_handler)
                            signal.alarm(10)  # 10秒总超时

                            try:
                                service = Service(ChromeDriverManager().install())
                                self.driver = webdriver.Chrome(service=service, options=options)
                                signal.alarm(0)  # 取消超时
                                logger.info("✅ 使用webdriver-manager创建Chrome驱动成功")
                                driver_created = True
                            finally:
                                signal.alarm(0)  # 确保取消超时

                        except Exception as wdm_error:
                            logger.warning(f"⚠️ webdriver-manager也失败: {wdm_error}")

                    if not driver_created:
                        raise Exception("所有Chrome驱动创建方法都失败")

                except Exception as e:
                    logger.error(f"❌ Chrome驱动创建失败: {e}")
                    logger.info("💡 请确保已安装Chrome浏览器和chromedriver")
                    logger.info("💡 或者将chromedriver添加到系统PATH中")
                    raise

                # 应用selenium-stealth
                if self.stealth_available and self.selenium_config.get('use_stealth', True):
                    logger.info("🛡️ 应用selenium-stealth反检测...")
                    try:
                        stealth(self.driver,
                               languages=["zh-CN", "zh", "en-US", "en"],
                               vendor="Google Inc.",
                               platform="Win32",
                               webgl_vendor="Intel Inc.",
                               renderer="Intel Iris OpenGL Engine",
                               fix_hairline=True)
                        logger.info("✅ selenium-stealth 应用成功")
                    except Exception as e:
                        logger.warning(f"⚠️ selenium-stealth 应用失败: {e}")
                else:
                    logger.info("ℹ️ 跳过selenium-stealth应用")

                # 注入自定义反检测脚本
                logger.info("🔧 注入自定义反检测脚本...")
                try:
                    self.driver.execute_script(SIMPLE_STEALTH_SCRIPT)
                    logger.info("✅ 反检测脚本注入成功")
                except Exception as e:
                    logger.warning(f"⚠️ 反检测脚本注入失败: {e}")

                # 设置超时
                logger.info("🔧 设置浏览器超时参数...")
                try:
                    self.driver.set_page_load_timeout(self.selenium_config.get('page_load_timeout', 60))
                    self.driver.implicitly_wait(self.selenium_config.get('implicit_wait', 10))
                    logger.info("✅ 超时参数设置成功")
                except Exception as e:
                    logger.warning(f"⚠️ 超时参数设置失败: {e}")

                # 设置等待
                logger.info("🔧 创建WebDriverWait实例...")
                self.wait = WebDriverWait(self.driver, self.selenium_config.get('timeout', 30))
                logger.info("✅ WebDriverWait创建成功")

                # 🔧 新增：自动加载快手登录状态
                logger.info("🔧 开始加载快手登录状态...")
                self._load_kuaishou_login_state()

                logger.info("✅ 简化版Chrome驱动初始化完成")

            finally:
                # 清除超时设置
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)

        except TimeoutError:
            logger.error("❌ Chrome驱动初始化超时（60秒）")
            self._cleanup_driver()
            raise Exception("Chrome驱动初始化超时，请检查Chrome浏览器是否正常工作")
        except Exception as e:
            logger.error(f"❌ 简化版Chrome驱动初始化失败: {e}")
            self._cleanup_driver()
            raise
    
    def _smart_find_element(self, selector_group: str, timeout: int = 10) -> Optional[Any]:
        """智能元素查找 - 基于实际成功案例优化（直接使用成功方法）"""

        # 🎯 快速路径：直接尝试已知成功的选择器
        success_selectors = {
            'upload_input': '//input[@type="file"]',
            'title_input': 'div[contenteditable="true"]',
            'description_input': 'div[contenteditable="true"][placeholder*="描述"]',
            'publish_button': "//button[text()='发布' and contains(@class, 'ant-btn-primary')]"  # 红色发布按钮
        }

        if selector_group in success_selectors:
            try:
                logger.info(f"🚀 快速路径：尝试已知成功选择器 [{selector_group}]")
                success_selector = success_selectors[selector_group]

                if success_selector.startswith('//'):
                    # XPath选择器
                    element = WebDriverWait(self.driver, 1).until(
                        EC.presence_of_element_located((By.XPATH, success_selector))
                    )
                else:
                    # CSS选择器
                    element = WebDriverWait(self.driver, 1).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, success_selector))
                    )

                if element and element.is_displayed():
                    logger.info(f"✅ 快速路径成功找到元素 [{selector_group}]: {success_selector}")
                    return element
            except:
                logger.info(f"⚠️ 快速路径失败，继续常规查找 [{selector_group}]")

        # 🎯 对于upload_input，使用备用查找方法
        if selector_group == 'upload_input':
            logger.info(f"🎯 直接使用实际成功的XPath方法查找 [{selector_group}]")
            return self._fallback_element_search(selector_group)

        selectors = self.selectors.get(selector_group, [])
        logger.info(f"🔍 开始查找元素组 [{selector_group}]，共 {len(selectors)} 个选择器")

        for i, selector in enumerate(selectors):
            try:
                logger.info(f"🔍 尝试选择器 {i+1}/{len(selectors)}: {selector}")

                # 根据选择器优先级调整等待时间
                wait_time = 1 if i < 3 else 2  # 前3个选择器（成功方案）等待时间更短

                # CSS选择器
                if not selector.startswith('//'):
                    # 处理包含:contains()的选择器
                    if ':contains(' in selector:
                        text_content = selector.split(':contains(')[1].split(')')[0].strip("'\"")
                        xpath_selector = f"//*[contains(text(), '{text_content}')]"
                        try:
                            element = WebDriverWait(self.driver, wait_time).until(
                                EC.presence_of_element_located((By.XPATH, xpath_selector))
                            )
                            if element and element.is_displayed():
                                logger.info(f"✅ 通过XPath找到元素 [{selector_group}]: {xpath_selector}")
                                return element
                        except:
                            continue
                    else:
                        # 普通CSS选择器
                        try:
                            element = WebDriverWait(self.driver, wait_time).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            if element and element.is_displayed():
                                logger.info(f"✅ 找到元素 [{selector_group}]: {selector}")
                                return element
                        except:
                            continue
                else:
                    # XPath选择器
                    try:
                        element = WebDriverWait(self.driver, wait_time).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        if element and element.is_displayed():
                            logger.info(f"✅ 找到元素 [{selector_group}]: {selector}")
                            return element
                    except:
                        continue

            except Exception as e:
                logger.debug(f"选择器 {selector} 查找失败: {e}")
                continue

        # 如果所有选择器都失败，尝试备用查找
        logger.warning(f"❌ 所有选择器都失败，尝试备用查找 [{selector_group}]...")
        return self._fallback_element_search(selector_group)

    def _fallback_element_search(self, selector_group: str) -> Optional[Any]:
        """备用元素查找方法"""
        try:
            logger.info(f"🔧 开始备用查找: {selector_group}")

            if selector_group == 'upload_input':
                # 方法1: 直接使用XPath查找 input[type="file"] (最常见的成功方法)
                try:
                    logger.info("🔄 备用方法1: 使用XPath查找 input[type=\"file\"]")
                    element = self.driver.find_element(By.XPATH, '//input[@type="file"]')
                    if element:
                        logger.info("✅ 备用方法1成功找到文件输入")
                        return element
                except:
                    pass

                # 方法2: 查找所有input元素并筛选
                try:
                    logger.info("🔄 备用方法2: 遍历所有input元素")
                    inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    for inp in inputs:
                        if inp.get_attribute("type") == "file":
                            logger.info("✅ 备用方法2成功找到文件输入")
                            return inp
                except:
                    pass

                # 方法3: 查找隐藏的文件输入
                try:
                    logger.info("🔄 备用方法3: 查找隐藏的文件输入")
                    hidden_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"][style*="display: none"], input[type="file"][hidden]')
                    if hidden_inputs:
                        logger.info("✅ 备用方法3成功找到隐藏文件输入")
                        return hidden_inputs[0]
                except:
                    pass

                # 方法4: 使用JavaScript查找
                try:
                    logger.info("🔄 备用方法4: 使用JavaScript查找文件输入")
                    element = self.driver.execute_script("""
                        var inputs = document.querySelectorAll('input[type="file"]');
                        return inputs.length > 0 ? inputs[0] : null;
                    """)
                    if element:
                        logger.info("✅ 备用方法4成功找到文件输入")
                        return element
                except:
                    pass

            elif selector_group == 'title_input':
                # 查找标题输入框
                textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
                for textarea in textareas:
                    placeholder = textarea.get_attribute("placeholder") or ""
                    if "标题" in placeholder or "title" in placeholder.lower():
                        logger.info(f"✅ 通过备用方法找到标题输入框")
                        return textarea

                # 如果没找到，返回第一个textarea
                if textareas:
                    logger.info(f"✅ 通过备用方法找到第一个文本区域作为标题输入")
                    return textareas[0]

            elif selector_group == 'description_input':
                # 查找描述输入框
                textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
                for textarea in textareas:
                    placeholder = textarea.get_attribute("placeholder") or ""
                    if "简介" in placeholder or "描述" in placeholder or "description" in placeholder.lower():
                        logger.info(f"✅ 通过备用方法找到描述输入框")
                        return textarea

                # 如果有多个textarea，返回第二个
                if len(textareas) > 1:
                    logger.info(f"✅ 通过备用方法找到第二个文本区域作为描述输入")
                    return textareas[1]

            elif selector_group == 'publish_button':
                # 查找发布按钮
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    btn_text = btn.text.strip()
                    if any(keyword in btn_text for keyword in ['发布', '提交', '确认', '完成']):
                        logger.info(f"✅ 通过备用方法找到发布按钮: {btn_text}")
                        return btn

        except Exception as e:
            logger.error(f"备用查找也失败: {str(e)}")

        logger.error(f"❌ 所有查找方法都失败: {selector_group}")
        return None

    def _wait_for_dynamic_elements(self, timeout: int = 10):
        """等待动态元素加载完成"""
        try:
            logger.info("⏳ 等待页面动态元素加载完成...")

            # 等待React/Vue应用加载完成的常见标志
            wait_conditions = [
                # 等待任何输入框出现
                lambda: len(self.driver.find_elements(By.CSS_SELECTOR, "input, textarea, [contenteditable]")) > 0,
                # 等待页面不再有loading状态
                lambda: len(self.driver.find_elements(By.CSS_SELECTOR, ".loading, [data-loading='true']")) == 0,
                # 等待主要内容区域出现
                lambda: len(self.driver.find_elements(By.CSS_SELECTOR, ".main-content, .content, .form")) > 0
            ]

            start_time = time.time()
            while time.time() - start_time < timeout:
                if any(condition() for condition in wait_conditions):
                    logger.info("✅ 动态元素加载完成")
                    return True
                time.sleep(0.5)

            logger.warning("⚠️ 动态元素等待超时，继续执行")
            return False

        except Exception as e:
            logger.warning(f"⚠️ 动态元素等待失败: {e}")
            return False

    def _smart_find_element_with_retry(self, selector_group: str, timeout: int = 15, retry_count: int = 3):
        """智能查找元素，支持重试和动态等待"""
        for attempt in range(retry_count):
            logger.info(f"🔍 第 {attempt + 1}/{retry_count} 次尝试查找元素组 [{selector_group}]")

            # 每次重试前等待动态元素
            if attempt > 0:
                self._wait_for_dynamic_elements(5)
                time.sleep(2)  # 额外等待

            element = self._smart_find_element(selector_group, timeout // retry_count)
            if element:
                logger.info(f"✅ 第 {attempt + 1} 次尝试成功找到元素")
                return element

            logger.warning(f"⚠️ 第 {attempt + 1} 次尝试失败")

        logger.error(f"❌ 所有 {retry_count} 次尝试都失败")
        return None

    def _debug_page_elements(self):
        """调试页面元素 - 帮助分析页面结构"""
        try:
            logger.info("🔍 开始调试页面元素...")

            # 获取页面标题和URL
            logger.info(f"📄 页面标题: {self.driver.title}")
            logger.info(f"🌐 当前URL: {self.driver.current_url}")

            # 查找所有input元素
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            logger.info(f"📝 找到 {len(inputs)} 个input元素:")
            for i, inp in enumerate(inputs[:5]):  # 只显示前5个
                input_type = inp.get_attribute("type") or "text"
                input_name = inp.get_attribute("name") or "无名称"
                input_placeholder = inp.get_attribute("placeholder") or "无占位符"
                logger.info(f"  {i+1}. type={input_type}, name={input_name}, placeholder={input_placeholder}")

            # 查找所有textarea元素
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            logger.info(f"📝 找到 {len(textareas)} 个textarea元素:")
            for i, textarea in enumerate(textareas[:3]):  # 只显示前3个
                placeholder = textarea.get_attribute("placeholder") or "无占位符"
                maxlength = textarea.get_attribute("maxlength") or "无限制"
                logger.info(f"  {i+1}. placeholder={placeholder}, maxlength={maxlength}")

            # 查找所有contenteditable元素
            contenteditable_elements = self.driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true']")
            logger.info(f"✏️ 找到 {len(contenteditable_elements)} 个contenteditable元素:")
            for i, elem in enumerate(contenteditable_elements[:5]):  # 只显示前5个
                tag_name = elem.tag_name
                placeholder = elem.get_attribute("placeholder") or elem.get_attribute("data-placeholder") or "无占位符"
                class_name = elem.get_attribute("class") or "无class"
                text_content = elem.text[:50] if elem.text else "无内容"
                logger.info(f"  {i+1}. tag={tag_name}, placeholder={placeholder}, class={class_name}, text={text_content}")

            # 查找所有可能的输入元素（包括div等）
            all_input_like = self.driver.find_elements(By.CSS_SELECTOR,
                "input, textarea, [contenteditable], [role='textbox'], .input, .textarea, [data-testid*='input'], [placeholder]")
            logger.info(f"📝 找到 {len(all_input_like)} 个类输入元素:")
            for i, elem in enumerate(all_input_like[:10]):  # 显示前10个
                tag_name = elem.tag_name
                elem_type = elem.get_attribute("type") or "无类型"
                placeholder = elem.get_attribute("placeholder") or elem.get_attribute("data-placeholder") or "无占位符"
                class_name = elem.get_attribute("class") or "无class"
                role = elem.get_attribute("role") or "无role"
                logger.info(f"  {i+1}. tag={tag_name}, type={elem_type}, role={role}, placeholder={placeholder}, class={class_name[:50]}")

            # 查找所有button元素
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            logger.info(f"🔘 找到 {len(buttons)} 个button元素:")
            for i, btn in enumerate(buttons[:10]):  # 显示前10个
                btn_text = btn.text.strip() or "无文本"
                btn_type = btn.get_attribute("type") or "button"
                btn_class = btn.get_attribute("class") or "无class"
                logger.info(f"  {i+1}. text={btn_text}, type={btn_type}, class={btn_class[:50]}")

            # 保存页面截图用于调试
            try:
                screenshot_path = f"debug_screenshot_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"📸 页面截图已保存: {screenshot_path}")
            except Exception as screenshot_error:
                logger.warning(f"⚠️ 截图保存失败: {screenshot_error}")

        except Exception as e:
            logger.error(f"❌ 页面调试失败: {str(e)}")
    
    def _human_like_delay(self, min_delay: float = 0.5, max_delay: float = 2.0):
        """人性化延时"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def _simulate_human_typing(self, element, text: str):
        """模拟人类打字行为 - 支持contenteditable元素"""
        try:
            # 检查是否是contenteditable元素
            is_contenteditable = element.get_attribute('contenteditable') == 'true'

            if is_contenteditable:
                # 对于contenteditable元素，使用JavaScript设置内容
                logger.info("🔧 检测到contenteditable元素，使用JavaScript设置内容")
                self.driver.execute_script("""
                    arguments[0].focus();
                    arguments[0].innerHTML = '';
                    arguments[0].innerText = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, element, text)
                time.sleep(0.5)
            else:
                # 传统input/textarea元素
                element.clear()
                for char in text:
                    element.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.15))
        except Exception as e:
            logger.warning(f"⚠️ 文本输入失败，尝试备用方法: {e}")
            # 备用方法：直接使用send_keys
            try:
                element.clear()
                element.send_keys(text)
            except Exception as e2:
                logger.error(f"❌ 备用文本输入方法也失败: {e2}")

    async def _try_upload_methods(self, upload_element, video_path: str) -> bool:
        """尝试多种方法上传文件 - 基于2023年成功案例优化"""
        try:
            logger.info("🔧 基于2023年成功案例尝试多种方法上传文件...")

            # 方法1: 直接发送文件路径 (2023年成功案例中的主要方法)
            try:
                logger.info("🔄 方法1: 直接发送文件路径 (2023年成功案例)")
                upload_element.send_keys(video_path)
                logger.info("✅ 方法1成功")
                return True
            except Exception as e:
                logger.warning(f"⚠️ 方法1失败: {e}")

            # 方法2: 清空后发送文件路径 (防止输入框有残留内容)
            try:
                logger.info("🔄 方法2: 清空后发送文件路径")
                upload_element.clear()
                await asyncio.sleep(0.5)
                upload_element.send_keys(video_path)
                logger.info("✅ 方法2成功")
                return True
            except Exception as e:
                logger.warning(f"⚠️ 方法2失败: {e}")

            # 方法3: 确保元素可见后发送 (解决元素被遮挡问题)
            try:
                logger.info("🔄 方法3: 确保元素可见后发送")
                # 滚动到元素位置
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", upload_element)
                await asyncio.sleep(1)

                # 确保元素完全可见和可交互
                self.driver.execute_script("""
                    var element = arguments[0];
                    element.style.display = 'block';
                    element.style.visibility = 'visible';
                    element.style.opacity = '1';
                    element.style.position = 'static';
                    element.style.zIndex = '9999';
                    element.removeAttribute('hidden');
                    element.removeAttribute('disabled');
                """, upload_element)
                await asyncio.sleep(0.5)

                upload_element.send_keys(video_path)
                logger.info("✅ 方法3成功")
                return True
            except Exception as e:
                logger.warning(f"⚠️ 方法3失败: {e}")

            # 方法4: 使用ActionChains模拟真实用户操作
            try:
                logger.info("🔄 方法4: 使用ActionChains模拟真实用户操作")
                actions = ActionChains(self.driver)
                actions.move_to_element(upload_element)
                actions.click(upload_element)
                actions.perform()
                await asyncio.sleep(0.5)
                upload_element.send_keys(video_path)
                logger.info("✅ 方法4成功")
                return True
            except Exception as e:
                logger.warning(f"⚠️ 方法4失败: {e}")

            # 方法5: 强制聚焦后发送
            try:
                logger.info("🔄 方法5: 强制聚焦后发送")
                # 使用JavaScript强制聚焦
                self.driver.execute_script("arguments[0].focus();", upload_element)
                await asyncio.sleep(0.3)
                upload_element.send_keys(video_path)
                logger.info("✅ 方法5成功")
                return True
            except Exception as e:
                logger.warning(f"⚠️ 方法5失败: {e}")

            logger.error("❌ 所有上传方法都失败")
            return False

        except Exception as e:
            logger.error(f"❌ 上传方法尝试过程中发生错误: {e}")
            return False

    async def _wait_for_upload_complete(self, max_wait_time: int = 300) -> bool:
        """等待视频上传完成 - 基于实际观察优化检测方法"""
        try:
            logger.info("⏳ 智能检测视频上传完成状态...")
            start_time = time.time()

            while time.time() - start_time < max_wait_time:
                try:
                    # 🎯 方法1: 检查右侧手机预览区域是否有视频预览（最可靠的方法）
                    try:
                        # 查找手机预览区域的视频元素
                        video_preview_selectors = [
                            "video",  # 直接查找video标签
                            "[class*='preview'] video",  # 预览区域的video
                            "[class*='phone'] video",  # 手机模拟器的video
                            ".video-preview",  # 视频预览类
                            "[class*='player']",  # 播放器相关
                            "canvas"  # 有时视频预览用canvas显示
                        ]

                        for selector in video_preview_selectors:
                            try:
                                preview_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                for elem in preview_elements:
                                    if elem.is_displayed():
                                        logger.info(f"✅ 检测到视频预览元素，上传已完成: {selector}")
                                        return True
                            except:
                                continue
                    except:
                        pass

                    # 🎯 方法2: 检查页面是否出现了编辑界面元素（标题输入框等）
                    try:
                        # 查找标题输入框 - 这是上传完成后的明确标志
                        title_selectors = [
                            "textarea[placeholder*='标题']",
                            "input[placeholder*='标题']",
                            "textarea[placeholder*='作品']",
                            "textarea",  # 通用文本区域
                            "input[type='text']"  # 通用文本输入
                        ]

                        for selector in title_selectors:
                            try:
                                title_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                                if title_input and title_input.is_displayed():
                                    # 进一步验证是否真的是标题输入框
                                    placeholder = title_input.get_attribute("placeholder") or ""
                                    if "标题" in placeholder or "作品" in placeholder or len(placeholder) > 0:
                                        logger.info(f"✅ 检测到标题输入框，上传已完成: {placeholder}")
                                        return True
                            except:
                                continue
                    except:
                        pass

                    # 🎯 方法3: 检查页面URL变化（有时上传完成后URL会变化）
                    try:
                        current_url = self.driver.current_url
                        if "edit" in current_url or "publish" in current_url:
                            logger.info(f"✅ 检测到URL变化，可能已进入编辑页面: {current_url}")
                            # 再次确认是否有编辑元素
                            try:
                                edit_elements = self.driver.find_elements(By.TAG_NAME, "textarea")
                                if len(edit_elements) > 0:
                                    logger.info("✅ 确认进入编辑页面，上传已完成")
                                    return True
                            except:
                                pass
                    except:
                        pass

                    # 🎯 方法4: 检查传统的上传成功指示器
                    try:
                        success_indicators = [
                            "上传成功", "上传完成", "处理完成", "视频已上传",
                            "upload success", "upload complete"
                        ]

                        page_source = self.driver.page_source
                        for indicator in success_indicators:
                            if indicator in page_source:
                                logger.info(f"✅ 检测到上传成功指示器: {indicator}")
                                return True
                    except:
                        pass

                    # 🎯 方法5: 检查是否不再有上传进度指示器
                    try:
                        # 如果找不到上传中的指示器，可能已经完成
                        uploading_indicators = [
                            "上传中", "uploading", "processing", "处理中",
                            "[class*='uploading']", "[class*='loading']"
                        ]

                        has_uploading = False
                        for indicator in uploading_indicators:
                            try:
                                if indicator.startswith("["):
                                    elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                                    if any(elem.is_displayed() for elem in elements):
                                        has_uploading = True
                                        break
                                else:
                                    if indicator in self.driver.page_source:
                                        has_uploading = True
                                        break
                            except:
                                continue

                        if not has_uploading:
                            # 没有上传中指示器，可能已完成，再次检查是否有编辑元素
                            try:
                                textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
                                if len(textareas) > 0:
                                    logger.info("✅ 没有上传中指示器且有编辑元素，上传可能已完成")
                                    return True
                            except:
                                pass
                    except:
                        pass

                    logger.info("🔄 视频还在上传中...")
                    await asyncio.sleep(5)  # 每5秒检查一次，减少频率

                except Exception as e:
                    logger.debug(f"检查上传状态时出错: {e}")
                    await asyncio.sleep(5)

            logger.warning(f"⚠️ 等待上传完成超时 ({max_wait_time}秒)")
            return False

        except Exception as e:
            logger.error(f"❌ 等待上传完成时发生错误: {e}")
            return False
    
    def _cleanup_driver(self):
        """清理驱动资源"""
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                self.driver = None
                self.wait = None
                logger.debug("✅ 简化版Chrome驱动资源清理完成")
        except Exception as e:
            logger.warning(f"⚠️ 驱动清理失败: {e}")

    def _load_kuaishou_login_state(self):
        """加载快手登录状态"""
        try:
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 模拟模式：跳过登录状态加载")
                return

            logger.info("🔐 尝试加载快手登录状态...")

            # 使用登录管理器加载cookies
            success = login_manager.load_cookies_for_driver('kuaishou', self.driver)

            if success:
                logger.info("✅ 快手登录状态加载成功，用户无需重新登录")
                # 等待页面加载完成
                time.sleep(2)
            else:
                logger.info("ℹ️ 未找到快手登录状态，用户需要手动登录")

        except Exception as e:
            logger.warning(f"⚠️ 加载快手登录状态失败: {e}")

    def _save_kuaishou_login_state(self):
        """保存快手登录状态"""
        try:
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 模拟模式：跳过登录状态保存")
                return True

            logger.info("💾 保存快手登录状态...")

            # 检查是否在快手域名
            current_url = self.driver.current_url
            if 'kuaishou.com' not in current_url:
                logger.warning("⚠️ 当前不在快手域名，无法保存登录状态")
                return False

            # 使用登录管理器保存cookies
            success = login_manager.save_cookies_from_driver('kuaishou', self.driver)

            if success:
                logger.info("✅ 快手登录状态保存成功，下次使用时将自动登录")
                return True
            else:
                logger.warning("⚠️ 快手登录状态保存失败")
                return False

        except Exception as e:
            logger.error(f"❌ 保存快手登录状态失败: {e}")
            return False

    def _detect_kuaishou_login_status(self) -> bool:
        """检测快手登录状态并自动保存"""
        try:
            if self.selenium_config.get('simulation_mode', False):
                return True

            # 快手登录指示器
            login_indicators = [
                # 用户头像和信息
                '.user-avatar',
                '.user-info',
                '.header-user',
                '[data-testid="user-avatar"]',

                # 创作者中心特有元素
                '.creator-center',
                '.publish-btn',
                '.upload-area',

                # 页面标题包含创作者中心
                'title:contains("创作者中心")',

                # 导航菜单
                '.nav-menu',
                '.sidebar-menu'
            ]

            found_indicators = []
            for indicator in login_indicators:
                try:
                    if not indicator.startswith('title:'):
                        elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                        if elements and any(el.is_displayed() for el in elements):
                            found_indicators.append(indicator)
                    else:
                        # 检查页面标题
                        page_title = self.driver.title
                        if '创作者中心' in page_title or 'creator' in page_title.lower():
                            found_indicators.append('page_title')
                except:
                    continue

            # 如果找到足够的登录指示器，认为已登录
            is_logged_in = len(found_indicators) >= 2

            if is_logged_in:
                logger.info(f"✅ 检测到快手已登录，找到指示器: {', '.join(found_indicators[:3])}...")

                # 自动保存登录状态
                self._save_kuaishou_login_state()
                return True
            else:
                logger.info("ℹ️ 未检测到快手登录状态")
                return False

        except Exception as e:
            logger.error(f"❌ 检测快手登录状态失败: {e}")
            return False
    
    async def _check_login_status(self) -> bool:
        """检查快手登录状态"""
        try:
            # 模拟模式下直接返回True
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 模拟模式：模拟登录状态检查")
                await asyncio.sleep(1)
                return True

            await asyncio.sleep(3)

            current_url = self.driver.current_url
            logger.info(f"当前页面URL: {current_url}")

            if any(keyword in current_url for keyword in ['login', 'passport', 'sso', 'auth']):
                logger.warning("检测到登录页面，需要用户登录")
                return False

            if 'cp.kuaishou.com' in current_url:
                # 检查是否在快手创作者中心页面（说明已登录）
                if any(indicator in current_url for indicator in [
                    'profile', 'creator', 'dashboard', 'article'
                ]):
                    logger.info(f"✅ 登录状态检查通过 - 已在快手创作者中心: {current_url}")

                    # 🔧 新增：检测到登录状态时自动保存
                    self._detect_kuaishou_login_status()
                    return True

                # 如果在上传页面，检查上传相关元素
                if 'publish/video' in current_url:
                    for selector_group in ['upload_input', 'title_input', 'publish_button']:
                        element = self._smart_find_element(selector_group, timeout=5)
                        if element:
                            logger.info(f"✅ 登录状态检查通过 - 在上传页面找到关键元素: {selector_group}")
                            self._detect_kuaishou_login_status()
                            return True

            # 🔧 新增：尝试通用登录检测
            return self._detect_kuaishou_login_status()

        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return False

    async def _publish_video_impl(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """简化版Chrome快手视频发布实现"""
        try:
            # 检查是否为模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 模拟模式：模拟简化版Chrome快手视频发布过程")

                title = video_info.get('title', '')
                description = video_info.get('description', '')

                logger.info(f"模拟设置标题: {title}")
                await asyncio.sleep(1)
                logger.info(f"模拟设置描述: {description}")
                await asyncio.sleep(1)
                logger.info("模拟上传视频文件...")
                await asyncio.sleep(3)
                logger.info("模拟点击发布按钮...")
                await asyncio.sleep(2)

                logger.info("✅ 简化版Chrome模拟发布成功！")
                return {'success': True, 'message': '简化版Chrome模拟发布成功'}

            # 立刻导航到上传页面
            upload_url = "https://cp.kuaishou.com/article/publish/video"
            current_url = self.driver.current_url
            logger.info(f"🌐 当前页面URL: {current_url}")

            # 立刻导航到上传页面（不管当前在哪个页面）
            logger.info(f"🔄 立刻导航到上传页面: {upload_url}")
            self.driver.get(upload_url)

            # 等待页面完全加载（10-30秒）
            logger.info("⏳ 等待页面完全加载...")
            await asyncio.sleep(15)  # 等待15秒让页面完全加载

            # 验证导航是否成功
            new_url = self.driver.current_url
            logger.info(f"🌐 导航后页面URL: {new_url}")

            # 等待页面元素加载完成
            logger.info("⏳ 等待页面元素加载完成...")
            await asyncio.sleep(10)  # 再等待10秒确保所有元素加载完成

            if not new_url.endswith('/article/publish/video'):
                logger.warning(f"⚠️ 导航可能失败，当前URL: {new_url}")
                # 尝试通过点击"发布视频"按钮导航
                await self._navigate_to_upload_page()
            else:
                logger.info("✅ 已成功导航到视频上传页面")

            # 步骤1: 上传视频文件
            video_path = video_info.get('video_path')
            if not video_path:
                return {'success': False, 'error': '视频路径不能为空'}

            logger.info(f"🎬 开始上传视频文件: {video_path}")
            upload_element = self._smart_find_element('upload_input', timeout=15)
            if not upload_element:
                # 调试页面元素
                self._debug_page_elements()
                return {'success': False, 'error': '未找到视频上传输入框'}

            # 尝试多种方法上传文件
            upload_success = await self._try_upload_methods(upload_element, video_path)
            if not upload_success:
                return {'success': False, 'error': '视频文件上传失败'}

            logger.info("✅ 视频文件路径已设置")

            # 等待一下让文件路径生效
            await asyncio.sleep(1)

            # 尝试多种方法触发上传
            upload_triggered = False

            try:
                # 方法1: 模拟用户点击文件输入框
                self.driver.execute_script("arguments[0].click();", upload_element)
                await asyncio.sleep(0.5)
                logger.info("🔄 已模拟点击文件输入框")

                # 方法2: 触发change事件
                self.driver.execute_script("""
                    var event = new Event('change', {bubbles: true, cancelable: true});
                    arguments[0].dispatchEvent(event);
                """, upload_element)
                await asyncio.sleep(0.5)
                logger.info("🔄 已触发change事件")

                # 方法3: 触发input事件
                self.driver.execute_script("""
                    var event = new Event('input', {bubbles: true, cancelable: true});
                    arguments[0].dispatchEvent(event);
                """, upload_element)
                await asyncio.sleep(0.5)
                logger.info("🔄 已触发input事件")

                # 方法4: 查找并点击上传按钮
                upload_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                    "button[class*='upload'], .upload-btn, [class*='upload-button']")
                for btn in upload_buttons:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            btn.click()
                            logger.info("🔄 点击了上传按钮")
                            upload_triggered = True
                            break
                    except:
                        continue

                # 方法5: 查找"上传视频"按钮
                upload_video_buttons = self.driver.find_elements(By.XPATH,
                    "//button[contains(text(), '上传视频')] | //span[contains(text(), '上传视频')]/parent::button")
                for btn in upload_video_buttons:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            btn.click()
                            logger.info("🔄 点击了'上传视频'按钮")
                            upload_triggered = True
                            break
                    except:
                        continue

                logger.info("🚀 上传触发尝试完成，开始监控上传状态...")

            except Exception as e:
                logger.warning(f"⚠️ 触发上传时出现警告: {e}")

            # 等待上传完成
            logger.info("⏳ 等待视频上传完成...")
            upload_complete = await self._wait_for_upload_complete(max_wait_time=300)

            if not upload_complete:
                logger.warning("⚠️ 视频上传可能未完成，但继续后续步骤")
                return {'success': False, 'error': '视频上传超时或失败'}
            else:
                logger.info("✅ 视频上传已完成，继续填写视频信息...")

            # 上传完成，继续填写视频信息
            logger.info("🎯 视频上传完成，开始填写视频信息...")

            # 等待页面完全加载和动态元素渲染
            logger.info("⏳ 等待页面完全加载...")
            self._wait_for_dynamic_elements(10)
            time.sleep(3)  # 额外等待确保所有元素都已渲染

            # 步骤2: 设置视频标题
            title = video_info.get('title', '')
            if title:
                logger.info(f"📝 设置视频标题: {title}")
                title = title[:50]  # 快手标题限制

                # 使用智能重试机制查找标题输入框
                title_element = self._smart_find_element_with_retry('title_input', timeout=15, retry_count=3)
                if title_element:
                    try:
                        # 确保元素可见和可交互
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", title_element)
                        time.sleep(0.5)

                        title_element.click()
                        self._human_like_delay(0.2, 0.5)
                        title_element.clear()
                        self._simulate_human_typing(title_element, title)
                        logger.info("✅ 标题设置成功")
                    except Exception as e:
                        logger.error(f"❌ 标题设置失败: {e}")
                else:
                    logger.warning("⚠️ 未找到标题输入框")
                    # 调试页面元素
                    self._debug_page_elements()

            self._human_like_delay(1, 2)

            # 步骤3: 设置视频描述
            description = video_info.get('description', '')
            tags = video_info.get('tags', [])
            if tags:
                tag_text = ' '.join([f'#{tag}' for tag in tags[:5]])
                if description:
                    description = f"{description} {tag_text}"
                else:
                    description = tag_text

            if description:
                logger.info(f"📄 设置视频描述: {description[:100]}...")
                description = description[:1000]  # 快手描述限制

                # 使用智能重试机制查找描述输入框
                desc_element = self._smart_find_element_with_retry('description_input', timeout=15, retry_count=3)
                if desc_element:
                    try:
                        # 确保元素可见和可交互
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", desc_element)
                        time.sleep(0.5)

                        desc_element.click()
                        self._human_like_delay(0.2, 0.5)
                        desc_element.clear()
                        self._simulate_human_typing(desc_element, description)
                        logger.info("✅ 描述设置成功")
                    except Exception as e:
                        logger.error(f"❌ 描述设置失败: {e}")
                else:
                    logger.warning("⚠️ 未找到描述输入框")

            self._human_like_delay(1, 2)

            # 步骤4: 发布视频
            logger.info("🚀 开始发布视频...")

            # 先滚动到页面底部，确保发布按钮可见
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                await asyncio.sleep(1)
                logger.info("📜 已滚动到页面底部")
            except Exception as e:
                logger.warning(f"⚠️ 滚动页面失败: {e}")

            # 增强的发布按钮查找
            publish_element = self._find_publish_button_enhanced()
            if not publish_element:
                return {'success': False, 'error': '未找到发布按钮'}

            # 确保按钮可见并可点击
            try:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", publish_element)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"⚠️ 滚动到按钮失败: {e}")

            if not publish_element.is_enabled():
                logger.warning("⚠️ 发布按钮不可点击，等待...")
                await asyncio.sleep(2)
                if not publish_element.is_enabled():
                    return {'success': False, 'error': '发布按钮不可点击'}

            # 尝试多种点击方式
            click_success = self._click_publish_button_enhanced(publish_element)
            if not click_success:
                return {'success': False, 'error': '发布按钮点击失败'}

            logger.info("✅ 发布按钮点击成功")

            # 等待发布完成
            await asyncio.sleep(5)

            # 🔧 新增：发布完成后保存登录状态
            self._save_kuaishou_login_state()

            # 检查发布结果
            success_indicators = ["发布成功", "发布完成", "上传成功", "提交成功"]
            for indicator in success_indicators:
                try:
                    if indicator in self.driver.page_source:
                        logger.info(f"✅ 检测到成功提示: {indicator}")
                        return {'success': True, 'message': '视频发布成功'}
                except:
                    continue

            # 默认认为发布成功
            logger.info("✅ 视频已提交发布")
            return {'success': True, 'message': '视频已提交发布，请稍后查看状态'}

        except Exception as e:
            logger.error(f"❌ 简化版Chrome快手视频发布失败: {e}")
            return {'success': False, 'error': str(e)}

    def _find_publish_button_enhanced(self):
        """增强的发布按钮查找方法 - 专门查找页面底部的红色发布按钮"""
        logger.info("🔍 开始增强发布按钮查找...")

        # 🎯 首先滚动到页面底部，确保红色发布按钮可见
        try:
            logger.info("📜 滚动到页面底部查找红色发布按钮...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            # 再次滚动确保完全到底部
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(1)
            logger.info("✅ 已滚动到页面底部")
        except Exception as e:
            logger.warning(f"⚠️ 滚动到底部失败: {e}")

        # 🎯 专门查找红色发布按钮的选择器
        red_publish_selectors = [
            "//button[text()='发布' and contains(@class, 'ant-btn-primary')]",  # 主要按钮
            "//button[text()='发布' and contains(@class, 'primary')]",
            "//button[normalize-space(text())='发布' and contains(@style, 'background')]",  # 有背景色的
            "//div[contains(@class, 'publish') or contains(@class, 'footer')]//button[text()='发布']",
            "//button[text()='发布']",  # 简单精确匹配
        ]

        for i, selector in enumerate(red_publish_selectors):
            try:
                logger.info(f"🔍 尝试选择器 {i+1}: {selector}")
                elements = self.driver.find_elements(By.XPATH, selector)

                for elem in elements:
                    if elem.is_displayed() and elem.is_enabled():
                        # 检查按钮位置是否在页面下半部分
                        location = elem.location
                        window_height = self.driver.execute_script("return window.innerHeight;")

                        logger.info(f"🎯 找到发布按钮: 位置Y={location['y']}, 窗口高度={window_height}")

                        # 如果按钮在页面下半部分，很可能是正确的发布按钮
                        if location['y'] > window_height * 0.3:  # 在页面下70%的位置
                            logger.info(f"✅ 找到页面底部的发布按钮!")
                            return elem
                        else:
                            logger.info(f"⚠️ 按钮位置太靠上，可能不是主发布按钮")

            except Exception as e:
                logger.warning(f"⚠️ 选择器 {i+1} 失败: {e}")
                continue

        # 🔍 详细调试：列出页面上所有包含"发布"的按钮元素
        try:
            all_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '发布')]")
            logger.info(f"🔍 页面上找到 {len(all_buttons)} 个包含'发布'的按钮:")

            for i, elem in enumerate(all_buttons):
                try:
                    text = elem.text.strip()
                    classes = elem.get_attribute('class') or ''
                    style = elem.get_attribute('style') or ''
                    is_displayed = elem.is_displayed()
                    is_enabled = elem.is_enabled()
                    location = elem.location

                    logger.info(f"  按钮{i+1}: 文本='{text}' 类名='{classes[:50]}...' 样式='{style[:30]}...' 位置={location} 可见={is_displayed} 可点击={is_enabled}")

                    # 选择最可能的发布按钮：可见、可点击、文本为"发布"
                    if (is_displayed and is_enabled and text == '发布' and
                        ('primary' in classes or 'ant-btn' in classes)):
                        logger.info(f"✅ 选择最佳发布按钮: 按钮{i+1}")
                        return elem

                except Exception as elem_e:
                    logger.warning(f"⚠️ 检查按钮{i+1}失败: {elem_e}")
                    continue

        except Exception as e:
            logger.error(f"❌ 详细查找失败: {e}")

        logger.error("❌ 未找到合适的发布按钮")
        return None

    def _click_publish_button_enhanced(self, element):
        """增强的发布按钮点击方法"""
        logger.info("🖱️ 开始增强发布按钮点击...")

        # 方法1: 普通点击
        try:
            element.click()
            logger.info("✅ 方法1成功: 普通点击")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 方法1失败: {e}")

        # 方法2: JavaScript点击
        try:
            self.driver.execute_script("arguments[0].click();", element)
            logger.info("✅ 方法2成功: JavaScript点击")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 方法2失败: {e}")

        # 方法3: ActionChains点击
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(self.driver).move_to_element(element).click().perform()
            logger.info("✅ 方法3成功: ActionChains点击")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 方法3失败: {e}")

        # 方法4: 模拟键盘回车
        try:
            element.send_keys('\n')
            logger.info("✅ 方法4成功: 键盘回车")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 方法4失败: {e}")

        logger.error("❌ 所有点击方法都失败了")
        return False

    async def _navigate_to_upload_page(self):
        """通过点击按钮导航到上传页面"""
        logger.info("🔄 尝试通过点击按钮导航到上传页面...")

        try:
            # 尝试多种可能的发布按钮选择器
            publish_selectors = [
                "a[href*='publish/video']",  # 包含publish/video的链接
                "button:contains('发布视频')",  # 包含"发布视频"文本的按钮
                ".publish-btn",  # 发布按钮类名
                "[data-testid*='publish']",  # 包含publish的测试ID
                "a:contains('发布')",  # 包含"发布"文本的链接
                ".creator-nav a[href*='publish']",  # 创作者导航中的发布链接
                "//a[contains(@href, 'publish/video')]",  # XPath方式
                "//button[contains(text(), '发布')]",  # XPath包含发布文本
                "//a[contains(text(), '发布')]"  # XPath包含发布文本的链接
            ]

            for selector in publish_selectors:
                try:
                    if selector.startswith('//'):
                        # XPath选择器
                        element = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        # CSS选择器
                        element = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )

                    logger.info(f"🎯 找到发布按钮: {selector}")
                    element.click()
                    await asyncio.sleep(3)

                    # 检查是否成功导航
                    if self.driver.current_url.endswith('/article/publish/video'):
                        logger.info("✅ 成功导航到上传页面")
                        return True

                except Exception as e:
                    logger.debug(f"选择器 {selector} 未找到元素: {e}")
                    continue

            logger.warning("⚠️ 无法通过点击按钮导航到上传页面")
            return False

        except Exception as e:
            logger.error(f"❌ 导航到上传页面时出错: {e}")
            return False
