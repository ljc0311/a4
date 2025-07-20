#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Selenium的微信视频号发布器
参考MoneyPrinterPlus的实现，支持微信视频号平台视频发布
🔧 优化：添加代理绕过功能，解决微信平台拒绝代理访问的问题
"""

import time
import asyncio
import os
from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

from .selenium_publisher_base import SeleniumPublisherBase
from src.utils.logger import logger
from src.config.wechat_publisher_config import get_wechat_config, validate_video_info


class SeleniumWechatPublisher(SeleniumPublisherBase):
    """基于Selenium的微信视频号发布器
    🔧 优化：支持代理绕过，解决微信平台访问限制
    """

    def __init__(self, config: Dict[str, Any]):
        # 🔧 新增：为微信平台配置代理绕过
        self._configure_wechat_proxy_bypass(config)

        # 🔧 修改：微信平台使用Chrome（与用户测试环境保持一致）
        if 'driver_type' not in config:
            config['driver_type'] = 'chrome'
            logger.info("🌐 微信平台默认使用Chrome驱动（与测试环境保持一致）")

        super().__init__('wechat', config)
        # 🆕 加载微信视频号配置
        self.wechat_config = get_wechat_config()
        logger.info(f"✅ 已加载微信视频号配置")

    def _init_chrome_driver(self):
        """🔧 重写：为微信平台初始化Chrome驱动，支持代理绕过"""
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.chrome.options import Options as ChromeOptions

        options = ChromeOptions()

        # 基本选项
        if self.selenium_config['headless']:
            options.add_argument('--headless')

        # 🔧 微信平台特殊配置：代理绕过
        if self.selenium_config.get('wechat_proxy_bypass', False):
            logger.info("🔧 为微信平台配置Chrome代理绕过...")

            # Chrome代理配置 - 禁用代理
            options.add_argument('--no-proxy-server')

            # 设置不使用代理的域名列表
            no_proxy_domains = self.selenium_config.get('no_proxy_domains', [])
            if no_proxy_domains:
                proxy_bypass_list = ';'.join(no_proxy_domains)
                options.add_argument(f'--proxy-bypass-list={proxy_bypass_list}')
                logger.info(f"🔧 Chrome代理绕过域名: {proxy_bypass_list}")

            logger.info("✅ Chrome代理绕过配置完成")

        # 🔧 微信平台专用配置
        # 设置User-Agent
        wechat_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        options.add_argument(f'--user-agent={wechat_user_agent}')

        # 网络和安全配置
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-web-security')

        # 禁用一些可能影响微信访问的功能
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-extensions')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        # 性能优化
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')

        # 🔧 微信平台特殊：允许弹窗和重定向
        options.add_argument('--disable-popup-blocking')

        # 🔧 优先尝试调试模式连接
        debugger_address = self.selenium_config.get('debugger_address', '127.0.0.1:9222')

        try:
            # 首先尝试连接到调试模式的Chrome
            logger.info(f"尝试连接到Chrome调试模式: {debugger_address}")

            # 创建新的选项对象，专门用于调试模式
            debug_options = ChromeOptions()
            debug_options.add_experimental_option("debuggerAddress", debugger_address)

            # 添加微信平台的特殊配置到调试选项
            debug_options.add_argument('--no-sandbox')
            debug_options.add_argument('--disable-dev-shm-usage')
            debug_options.add_argument(f'--user-agent={wechat_user_agent}')

            # 🔧 为调试模式添加代理绕过配置
            if self.selenium_config.get('wechat_proxy_bypass', False):
                no_proxy_domains = self.selenium_config.get('no_proxy_domains', [])
                if no_proxy_domains:
                    proxy_bypass_list = ';'.join(no_proxy_domains)
                    debug_options.add_argument(f'--proxy-bypass-list={proxy_bypass_list}')
                    debug_options.add_argument('--no-proxy-server')
                    logger.info(f"🔧 Chrome调试模式代理绕过配置: {proxy_bypass_list}")

            # 使用项目中的ChromeDriver
            chromedriver_path = os.path.join(os.getcwd(), "chromedriver.exe")
            if os.path.exists(chromedriver_path):
                service = ChromeService(chromedriver_path)
                logger.info(f"使用项目中的ChromeDriver: {chromedriver_path}")
                self.driver = webdriver.Chrome(service=service, options=debug_options)
            else:
                logger.info("使用系统PATH中的ChromeDriver")
                self.driver = webdriver.Chrome(options=debug_options)

            # 测试连接
            current_url = self.driver.current_url
            logger.info(f"✅ 成功连接到Chrome调试模式，当前URL: {current_url}")

            # 设置超时
            self.driver.set_page_load_timeout(90)  # 微信页面加载较慢
            self.driver.implicitly_wait(self.selenium_config.get('implicit_wait', 15))
            self.driver.set_script_timeout(60)

            logger.info("✅ Chrome驱动初始化成功（微信代理绕过模式）")
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
        try:
            # 创建Chrome驱动
            driver_location = self.selenium_config.get('driver_location')
            if driver_location and os.path.exists(driver_location):
                service = ChromeService(driver_location)
                logger.info(f"使用指定的ChromeDriver: {driver_location}")
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                logger.info("使用系统PATH中的ChromeDriver")
                self.driver = webdriver.Chrome(options=options)

            # 设置超时
            self.driver.set_page_load_timeout(90)  # 微信页面加载较慢
            self.driver.implicitly_wait(self.selenium_config.get('implicit_wait', 15))
            self.driver.set_script_timeout(60)

            logger.info("✅ Chrome普通模式启动成功（微信平台）")

        except Exception as e:
            logger.error(f"Chrome驱动初始化失败: {e}")
            raise

    def _configure_wechat_proxy_bypass(self, config: Dict[str, Any]):
        """🔧 新增：配置微信平台的代理绕过设置"""
        try:
            # 检测是否有系统代理
            proxy_detected = self._detect_system_proxy()

            if proxy_detected:
                logger.info("🔍 检测到系统代理，为微信平台配置代理绕过...")

                # 设置代理绕过配置
                config['wechat_proxy_bypass'] = True
                config['no_proxy_domains'] = [
                    'weixin.qq.com',
                    'channels.weixin.qq.com',
                    'mp.weixin.qq.com',
                    'wx.qq.com',
                    '*.weixin.qq.com',
                    '*.wx.qq.com'
                ]

                # 设置环境变量
                no_proxy_list = ','.join(config['no_proxy_domains'])
                os.environ['NO_PROXY'] = no_proxy_list
                os.environ['no_proxy'] = no_proxy_list

                logger.info(f"✅ 微信平台代理绕过配置完成: {no_proxy_list}")
            else:
                logger.info("未检测到系统代理，使用默认配置")
                config['wechat_proxy_bypass'] = False

        except Exception as e:
            logger.warning(f"配置微信代理绕过失败: {e}")
            config['wechat_proxy_bypass'] = False

    def _detect_system_proxy(self) -> bool:
        """🔧 新增：检测系统是否配置了代理"""
        try:
            # 检查环境变量
            proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
            for var in proxy_vars:
                if os.environ.get(var):
                    logger.info(f"检测到代理环境变量: {var}={os.environ.get(var)}")
                    return True

            # 检查Windows代理设置（简单检测）
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                  r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
                    proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                    if proxy_enable:
                        logger.info("检测到Windows系统代理已启用")
                        return True
            except:
                pass

            return False

        except Exception as e:
            logger.debug(f"代理检测失败: {e}")
            return False

    def _init_firefox_driver(self):
        """🔧 重写：为微信平台初始化Firefox驱动，支持代理绕过"""
        from selenium import webdriver
        from selenium.webdriver.firefox.service import Service as FirefoxService

        options = FirefoxOptions()

        # 基本选项
        if self.selenium_config['headless']:
            options.add_argument('--headless')

        # 🔧 微信平台特殊配置：代理绕过
        if self.selenium_config.get('wechat_proxy_bypass', False):
            logger.info("🔧 为微信平台配置Firefox代理绕过...")

            # Firefox代理配置 - 完全禁用代理
            options.set_preference("network.proxy.type", 0)  # 0 = 无代理，1 = 手动代理，4 = 自动检测，5 = 系统代理

            # 设置不使用代理的域名列表
            no_proxy_domains = self.selenium_config.get('no_proxy_domains', [])
            if no_proxy_domains:
                no_proxy_list = ','.join(no_proxy_domains)
                options.set_preference("network.proxy.no_proxies_on", no_proxy_list)
                logger.info(f"🔧 Firefox代理绕过域名: {no_proxy_list}")

            # 禁用代理自动检测和配置
            options.set_preference("network.proxy.autoconfig_url", "")
            options.set_preference("network.proxy.share_proxy_settings", False)
            options.set_preference("network.proxy.socks_remote_dns", False)

            # 强制禁用所有代理设置
            options.set_preference("network.proxy.http", "")
            options.set_preference("network.proxy.http_port", 0)
            options.set_preference("network.proxy.ssl", "")
            options.set_preference("network.proxy.ssl_port", 0)
            options.set_preference("network.proxy.socks", "")
            options.set_preference("network.proxy.socks_port", 0)

            logger.info("✅ Firefox代理绕过配置完成")

        # 🔧 微信平台专用配置
        # 设置User-Agent
        wechat_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
        options.set_preference("general.useragent.override", wechat_user_agent)

        # 网络和安全配置
        options.set_preference("security.tls.insecure_fallback_hosts", "weixin.qq.com,channels.weixin.qq.com")
        options.set_preference("security.mixed_content.block_active_content", False)
        options.set_preference("security.mixed_content.block_display_content", False)

        # 禁用一些可能影响微信访问的功能
        options.set_preference("privacy.trackingprotection.enabled", False)
        options.set_preference("privacy.trackingprotection.pbmode.enabled", False)
        options.set_preference("network.cookie.cookieBehavior", 0)  # 接受所有cookie

        # 性能优化
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("dom.disable_beforeunload", True)

        # 🔧 微信平台特殊：允许弹窗和重定向
        options.set_preference("dom.popup_maximum", 0)
        options.set_preference("privacy.popups.showBrowserMessage", False)

        try:
            # 创建Firefox驱动
            driver_location = self.selenium_config.get('driver_location')
            if driver_location and os.path.exists(driver_location):
                service = FirefoxService(driver_location)
                logger.info(f"使用指定的GeckoDriver: {driver_location}")
                self.driver = webdriver.Firefox(service=service, options=options)
            else:
                logger.info("使用系统PATH中的GeckoDriver")
                self.driver = webdriver.Firefox(options=options)

            # 设置超时
            self.driver.set_page_load_timeout(90)  # 微信页面加载较慢
            self.driver.implicitly_wait(self.selenium_config.get('implicit_wait', 15))
            self.driver.set_script_timeout(60)

            logger.info("✅ Firefox驱动初始化成功（微信代理绕过模式）")

        except Exception as e:
            logger.error(f"Firefox驱动初始化失败: {e}")
            raise

    def _get_platform_url(self) -> str:
        """获取微信视频号创作者中心URL"""
        return "https://channels.weixin.qq.com/platform/post/create"

    def _smart_find_element(self, selector_list: list, element_name: str = "元素", timeout: int = 10):
        """🔧 优化：智能查找元素，支持动态页面"""
        try:
            logger.info(f"开始智能查找{element_name}...")

            # 首先等待页面稳定
            time.sleep(2)

            for i, selector in enumerate(selector_list):
                logger.debug(f"尝试选择器 {i+1}/{len(selector_list)}: {selector}")

                # 尝试XPath选择器
                element = self.find_element_safe(By.XPATH, selector, timeout=3)
                if element and element.is_displayed():
                    logger.info(f"✅ 找到{element_name}，使用XPath选择器: {selector}")
                    return element

                # 如果XPath失败，尝试转换为CSS选择器（如果可能）
                try:
                    if selector.startswith("//"):
                        # 简单的XPath到CSS转换
                        if "input[@type='file']" in selector:
                            css_selector = "input[type='file']"
                            elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
                            for elem in elements:
                                if elem.is_displayed():
                                    logger.info(f"✅ 找到{element_name}，使用CSS选择器: {css_selector}")
                                    return elem
                except:
                    pass

            # 🔧 新增：使用JavaScript查找隐藏的文件输入框
            if "文件上传" in element_name:
                try:
                    logger.info("🔍 尝试JavaScript查找文件输入框...")
                    js_script = """
                    var inputs = document.querySelectorAll('input[type="file"]');
                    for (var i = 0; i < inputs.length; i++) {
                        var input = inputs[i];
                        // 检查是否接受视频文件
                        var accept = input.getAttribute('accept') || '';
                        if (accept.includes('video') || accept.includes('.mp4') || accept.accept === '*/*' || accept === '') {
                            return input;
                        }
                    }
                    return null;
                    """
                    element = self.driver.execute_script(js_script)
                    if element:
                        logger.info("✅ 通过JavaScript找到文件输入框")
                        return element
                except Exception as e:
                    logger.debug(f"JavaScript查找失败: {e}")

            logger.warning(f"⚠️ 未找到{element_name}，尝试了{len(selector_list)}个选择器")
            return None

        except Exception as e:
            logger.error(f"智能查找{element_name}失败: {e}")
            return None

    def _wait_for_page_elements(self, timeout: int = 30) -> bool:
        """🔧 优化：等待现代化页面元素加载完成"""
        try:
            logger.info("等待微信视频号页面元素加载...")

            start_time = time.time()
            while time.time() - start_time < timeout:
                # 🔧 新增：检查页面是否为React/Vue应用
                try:
                    # 等待React/Vue应用完全渲染
                    js_check = """
                    return document.readyState === 'complete' &&
                           (window.React || window.Vue || document.querySelector('[data-reactroot]') ||
                            document.querySelector('.app') || document.querySelector('#app'));
                    """
                    app_ready = self.driver.execute_script(js_check)
                    if app_ready:
                        logger.info("✅ 检测到现代化前端应用已加载")
                        time.sleep(3)  # 额外等待组件渲染
                        break
                except:
                    pass

                # 检查页面特征文本（从截图中看到的）
                page_indicators = [
                    "上传时长8小时内",
                    "大小不超过20GB",
                    "视频号助手",
                    "发表",
                    "标题",
                    "位置",
                    "声明原创"
                ]

                found_indicators = 0
                for indicator in page_indicators:
                    try:
                        if indicator in self.driver.page_source:
                            found_indicators += 1
                    except:
                        pass

                if found_indicators >= 3:
                    logger.info(f"✅ 页面特征检测完成，找到{found_indicators}个指示器")
                    time.sleep(2)  # 等待动态元素加载
                    return True

                time.sleep(1)

            logger.warning("⚠️ 页面元素加载超时")
            return False

        except Exception as e:
            logger.error(f"等待页面元素失败: {e}")
            return False

    def _find_upload_area_by_text(self):
        """🔧 新增：通过文本内容查找上传区域"""
        try:
            logger.info("🔍 通过文本内容查找上传区域...")

            # 查找包含上传提示文本的元素
            upload_texts = [
                "上传时长8小时内",
                "大小不超过20GB",
                "点击上传",
                "选择文件",
                "拖拽文件到此处"
            ]

            for text in upload_texts:
                try:
                    # 查找包含文本的元素
                    text_element = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{text}')]")
                    if text_element:
                        logger.info(f"✅ 找到上传提示文本: {text}")

                        # 在该元素的父级或兄弟元素中查找文件输入框
                        parent = text_element.find_element(By.XPATH, "./..")

                        # 在父元素中查找文件输入框
                        file_inputs = parent.find_elements(By.XPATH, ".//input[@type='file']")
                        if file_inputs:
                            for input_elem in file_inputs:
                                if input_elem.is_enabled():
                                    logger.info("✅ 在上传区域找到文件输入框")
                                    return input_elem

                        # 查找可点击的上传区域
                        clickable_areas = parent.find_elements(By.XPATH, ".//*[@role='button' or contains(@class, 'upload') or contains(@class, 'click')]")
                        if clickable_areas:
                            logger.info("✅ 找到可点击的上传区域")
                            return clickable_areas[0]

                except Exception as e:
                    logger.debug(f"查找文本'{text}'失败: {e}")
                    continue

            return None

        except Exception as e:
            logger.error(f"通过文本查找上传区域失败: {e}")
            return None

    def _smart_element_finder(self, element_type: str, timeout: int = 10):
        """🔧 增强：智能元素查找器，支持现代化页面"""
        try:
            logger.info(f"🔍 开始智能查找{element_type}元素...")

            # 获取对应的选择器列表
            selectors = self.wechat_config['selectors'].get(element_type, [])
            if not selectors:
                logger.warning(f"⚠️ 没有找到{element_type}的选择器配置")
                return None

            start_time = time.time()
            while time.time() - start_time < timeout:
                # 1. 尝试标准选择器
                for i, selector in enumerate(selectors):
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        if element and element.is_displayed() and element.is_enabled():
                            logger.info(f"✅ 通过选择器{i+1}找到{element_type}元素: {selector[:50]}...")
                            return element
                    except:
                        continue

                # 2. 增强的JavaScript查找（现代化应用）
                if element_type == 'file_upload':
                    element = self._find_file_input_js()
                    if element:
                        return element

                # 3. 尝试基于文本内容查找
                if element_type == 'file_upload':
                    element = self._find_upload_area_by_text()
                    if element:
                        return element

                # 4. 尝试基于页面结构推断
                if element_type == 'title_input':
                    element = self._find_title_input_smart()
                    if element:
                        return element

                # 5. 尝试基于描述查找
                if element_type == 'description_input':
                    element = self._find_description_input_smart()
                    if element:
                        return element

                # 6. 尝试基于发布按钮查找
                if element_type == 'publish_button':
                    element = self._find_publish_button_smart()
                    if element:
                        return element

                time.sleep(1)

            logger.warning(f"⚠️ 智能查找{element_type}元素超时")
            return None

        except Exception as e:
            logger.error(f"智能查找{element_type}元素失败: {e}")
            return None

    def _find_file_input_js(self):
        """🔧 新增：使用JavaScript查找文件输入框"""
        try:
            js_script = """
            // 查找所有可能的文件输入框
            var inputs = document.querySelectorAll('input[type="file"]');
            var candidates = [];

            for (var i = 0; i < inputs.length; i++) {
                var input = inputs[i];
                var rect = input.getBoundingClientRect();
                var style = window.getComputedStyle(input);

                // 检查元素是否可见或可交互
                var isVisible = rect.width > 0 || rect.height > 0 ||
                               input.offsetParent !== null ||
                               style.opacity !== '0' ||
                               style.visibility !== 'hidden';

                if (isVisible) {
                    candidates.push({
                        element: input,
                        score: 0
                    });
                }
            }

            // 如果没有找到可见的，查找隐藏的
            if (candidates.length === 0) {
                for (var i = 0; i < inputs.length; i++) {
                    candidates.push({
                        element: inputs[i],
                        score: 0
                    });
                }
            }

            // 评分系统：优先选择最可能的上传框
            for (var i = 0; i < candidates.length; i++) {
                var input = candidates[i].element;
                var parent = input.parentElement;

                // 检查accept属性
                if (input.accept && (input.accept.includes('video') || input.accept.includes('.mp4'))) {
                    candidates[i].score += 10;
                }

                // 检查父元素类名
                if (parent) {
                    var className = parent.className.toLowerCase();
                    if (className.includes('upload') || className.includes('video') || className.includes('file')) {
                        candidates[i].score += 5;
                    }
                }

                // 检查周围文本
                var nearbyText = input.parentElement ? input.parentElement.textContent : '';
                if (nearbyText.includes('上传') || nearbyText.includes('视频') || nearbyText.includes('文件')) {
                    candidates[i].score += 3;
                }
            }

            // 返回得分最高的元素
            if (candidates.length > 0) {
                candidates.sort(function(a, b) { return b.score - a.score; });
                return candidates[0].element;
            }

            return null;
            """
            element = self.driver.execute_script(js_script)
            if element:
                logger.info("✅ 通过增强JavaScript找到文件上传元素")
                return element
        except Exception as e:
            logger.debug(f"JavaScript增强查找失败: {e}")
        return None

    def _find_title_input_smart(self):
        """🔧 新增：智能查找标题输入框"""
        try:
            # 尝试多种方法查找标题输入框
            methods = [
                "//input[contains(@placeholder, '标题') or contains(@placeholder, 'title')]",
                "//textarea[contains(@placeholder, '标题') or contains(@placeholder, 'title')]",
                "//div[contains(text(), '标题')]//following-sibling::*//input",
                "//div[contains(text(), '标题')]//following-sibling::*//textarea",
                "//label[contains(text(), '标题')]//following-sibling::*//input",
                "//input[@type='text'][1]",  # 第一个文本输入框
                "//textarea[1]"  # 第一个文本区域
            ]

            for method in methods:
                try:
                    element = self.driver.find_element(By.XPATH, method)
                    if element and element.is_displayed():
                        logger.info(f"✅ 智能找到标题输入框: {method}")
                        return element
                except:
                    continue
        except Exception as e:
            logger.debug(f"智能查找标题输入框失败: {e}")
        return None

    def _find_description_input_smart(self):
        """🔧 新增：智能查找描述输入框"""
        try:
            methods = [
                "//textarea[contains(@placeholder, '描述') or contains(@placeholder, '简介')]",
                "//input[contains(@placeholder, '描述') or contains(@placeholder, '简介')]",
                "//div[contains(text(), '描述')]//following-sibling::*//textarea",
                "//div[contains(text(), '简介')]//following-sibling::*//textarea",
                "//textarea[position()>1]"  # 第二个或之后的文本区域
            ]

            for method in methods:
                try:
                    element = self.driver.find_element(By.XPATH, method)
                    if element and element.is_displayed():
                        logger.info(f"✅ 智能找到描述输入框: {method}")
                        return element
                except:
                    continue
        except Exception as e:
            logger.debug(f"智能查找描述输入框失败: {e}")
        return None

    def _find_publish_button_smart(self):
        """🔧 新增：智能查找发布按钮"""
        try:
            methods = [
                "//button[contains(text(), '发布') or contains(text(), '发表')]",
                "//span[contains(text(), '发布') or contains(text(), '发表')]//parent::button",
                "//div[contains(text(), '发布') or contains(text(), '发表')]//parent::button",
                "//button[contains(@class, 'publish') or contains(@class, 'submit')]",
                "//button[@type='submit']",
                "//button[last()]"  # 最后一个按钮（通常是主要操作按钮）
            ]

            for method in methods:
                try:
                    element = self.driver.find_element(By.XPATH, method)
                    if element and element.is_displayed() and element.is_enabled():
                        logger.info(f"✅ 智能找到发布按钮: {method}")
                        return element
                except:
                    continue
        except Exception as e:
            logger.debug(f"智能查找发布按钮失败: {e}")
        return None

    def _debug_page_elements(self):
        """🔧 新增：调试页面元素，帮助分析页面结构"""
        try:
            logger.info("🔍 开始调试页面元素...")

            # 1. 基本页面信息
            title = self.driver.title
            url = self.driver.current_url
            logger.info(f"📄 页面标题: {title}")
            logger.info(f"🌐 当前URL: {url}")

            # 2. 查找所有input元素
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            logger.info(f"🔍 找到 {len(inputs)} 个input元素:")
            for i, input_elem in enumerate(inputs[:10]):  # 只显示前10个
                try:
                    input_type = input_elem.get_attribute("type") or "text"
                    input_class = input_elem.get_attribute("class") or ""
                    input_id = input_elem.get_attribute("id") or ""
                    input_placeholder = input_elem.get_attribute("placeholder") or ""
                    is_displayed = input_elem.is_displayed()
                    logger.info(f"  Input {i+1}: type={input_type}, class={input_class[:30]}, id={input_id}, placeholder={input_placeholder[:20]}, visible={is_displayed}")
                except Exception as e:
                    logger.debug(f"  Input {i+1}: 获取属性失败 - {e}")

            # 3. 查找所有button元素
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            logger.info(f"🔍 找到 {len(buttons)} 个button元素:")
            for i, button in enumerate(buttons[:10]):  # 只显示前10个
                try:
                    button_text = button.text[:30] if button.text else ""
                    button_class = button.get_attribute("class") or ""
                    button_type = button.get_attribute("type") or ""
                    is_displayed = button.is_displayed()
                    is_enabled = button.is_enabled()
                    logger.info(f"  Button {i+1}: text='{button_text}', class={button_class[:30]}, type={button_type}, visible={is_displayed}, enabled={is_enabled}")
                except Exception as e:
                    logger.debug(f"  Button {i+1}: 获取属性失败 - {e}")

            # 4. 查找所有textarea元素
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            logger.info(f"🔍 找到 {len(textareas)} 个textarea元素:")
            for i, textarea in enumerate(textareas[:5]):  # 只显示前5个
                try:
                    textarea_placeholder = textarea.get_attribute("placeholder") or ""
                    textarea_class = textarea.get_attribute("class") or ""
                    is_displayed = textarea.is_displayed()
                    logger.info(f"  Textarea {i+1}: placeholder={textarea_placeholder[:30]}, class={textarea_class[:30]}, visible={is_displayed}")
                except Exception as e:
                    logger.debug(f"  Textarea {i+1}: 获取属性失败 - {e}")

            # 5. 查找包含关键词的元素
            keywords = ["上传", "视频", "文件", "标题", "描述", "发布", "发表"]
            for keyword in keywords:
                try:
                    elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                    if elements:
                        logger.info(f"🔍 包含'{keyword}'的元素: {len(elements)}个")
                        for i, elem in enumerate(elements[:3]):  # 只显示前3个
                            try:
                                tag_name = elem.tag_name
                                text = elem.text[:50] if elem.text else ""
                                logger.info(f"  {keyword} {i+1}: <{tag_name}> {text}")
                            except:
                                pass
                except Exception as e:
                    logger.debug(f"查找'{keyword}'元素失败: {e}")

            # 6. 使用JavaScript获取更多信息
            try:
                js_info = self.driver.execute_script("""
                return {
                    fileInputs: document.querySelectorAll('input[type="file"]').length,
                    hiddenInputs: document.querySelectorAll('input[style*="display: none"], input[style*="opacity: 0"]').length,
                    uploadDivs: document.querySelectorAll('div[class*="upload"], div[id*="upload"]').length,
                    reactElements: document.querySelectorAll('[data-reactroot], [data-react-class]').length,
                    vueElements: document.querySelectorAll('[data-v-]').length
                };
                """)
                logger.info(f"📊 JavaScript分析结果: {js_info}")
            except Exception as e:
                logger.debug(f"JavaScript分析失败: {e}")

        except Exception as e:
            logger.error(f"页面元素调试失败: {e}")

    def _get_platform_url(self) -> str:
        """获取微信视频号创作者中心URL"""
        return "https://channels.weixin.qq.com/platform/post/create"

    def _wait_for_element_interactive(self, element, timeout: int = 5):
        """🔧 新增：等待元素变为可交互状态"""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if element.is_displayed() and element.is_enabled():
                    # 额外检查元素是否真正可交互
                    try:
                        # 尝试获取元素的位置和大小
                        rect = element.rect
                        if rect['width'] > 0 and rect['height'] > 0:
                            return True
                    except:
                        pass
                time.sleep(0.2)
            return False
        except:
            return False

    def _enhanced_click(self, element):
        """🔧 新增：增强的点击方法"""
        try:
            # 1. 尝试标准点击
            try:
                element.click()
                logger.info("✅ 标准点击成功")
                return True
            except Exception as e:
                logger.debug(f"标准点击失败: {e}")

            # 2. 尝试JavaScript点击
            try:
                self.driver.execute_script("arguments[0].click();", element)
                logger.info("✅ JavaScript点击成功")
                return True
            except Exception as e:
                logger.debug(f"JavaScript点击失败: {e}")

            # 3. 尝试ActionChains点击
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(self.driver).move_to_element(element).click().perform()
                logger.info("✅ ActionChains点击成功")
                return True
            except Exception as e:
                logger.debug(f"ActionChains点击失败: {e}")

            return False

        except Exception as e:
            logger.error(f"增强点击失败: {e}")
            return False

    async def _check_login_status(self) -> bool:
        """🔧 优化：检查微信视频号登录状态"""
        try:
            # 等待页面加载完成
            await asyncio.sleep(3)

            # 检查页面URL
            current_url = self.driver.current_url
            logger.info(f"📍 当前页面URL: {current_url}")

            # 🔧 修复：如果在登录页面，尝试恢复登录状态
            if any(keyword in current_url for keyword in ['login', 'passport', 'sso']):
                logger.warning("⚠️ 检测到登录页面，尝试恢复登录状态...")

                # 尝试加载保存的登录状态
                if self.load_login_state():
                    logger.info("🔄 登录状态恢复成功，重新检查...")
                    await asyncio.sleep(3)

                    # 重新获取当前URL
                    current_url = self.driver.current_url
                    logger.info(f"📍 恢复后页面URL: {current_url}")

                    # 如果仍在登录页面，返回False
                    if any(keyword in current_url for keyword in ['login', 'passport', 'sso']):
                        logger.warning("❌ 登录状态恢复失败，仍在登录页面")
                        return False
                else:
                    logger.warning("❌ 没有可用的登录状态，需要用户登录")
                    return False

            # 检查是否在微信视频号域名
            if 'channels.weixin.qq.com' in current_url:
                # 🔧 优化：使用更全面的登录状态检查
                login_indicators = [
                    # 上传相关元素（更新的选择器）
                    '//input[@type="file"]',
                    '//input[@accept="video/*"]',
                    '//div[contains(@class, "upload")]//input[@type="file"]',
                    '//div[contains(@class, "upload-area")]//input[@type="file"]',

                    # 标题输入框（更新的选择器）
                    '//input[contains(@placeholder, "标题")]',
                    '//textarea[contains(@placeholder, "标题")]',
                    '//input[contains(@placeholder, "请输入标题")]',
                    '//input[contains(@placeholder, "微信视频号主页内容")]',

                    # 内容输入框（更新的选择器）
                    '//textarea[contains(@placeholder, "描述")]',
                    '//textarea[contains(@placeholder, "简介")]',
                    '//div[contains(@class, "editor")]//textarea',
                    '//textarea[contains(@placeholder, "请输入描述")]',

                    # 发布按钮（更新的选择器）
                    '//button[text()="发表"]',
                    '//button[contains(text(), "发表")]',
                    '//button[contains(text(), "发布")]',
                    '//span[text()="发表"]/parent::button',
                    '//button[contains(@class, "publish")]',

                    # 页面特征元素
                    '//div[contains(text(), "声明原创")]',
                    '//div[contains(text(), "位置")]',
                    '//div[contains(text(), "上传时长8小时内")]'
                ]

                # 🔧 优化：使用更稳定的元素检查方法
                found_indicators = 0
                for selector in login_indicators:
                    element = self.find_element_safe(By.XPATH, selector, timeout=2)
                    if element:
                        logger.debug(f"找到登录指示器: {selector}")
                        found_indicators += 1
                        # 如果找到至少2个指示器，认为已登录
                        if found_indicators >= 2:
                            logger.info(f"✅ 微信视频号登录状态验证成功（找到{found_indicators}个指示器）")
                            return True

                # 🔧 优化：检查页面标题和内容
                try:
                    page_title = self.driver.title
                    page_source = self.driver.page_source

                    # 检查页面标题
                    title_keywords = ['创作者中心', '发布', '视频号', '视频号助手']
                    title_match = any(keyword in page_title for keyword in title_keywords)

                    # 检查页面内容特征
                    content_keywords = ['上传时长8小时内', '大小不超过20GB', '声明原创', '发表']
                    content_matches = sum(1 for keyword in content_keywords if keyword in page_source)

                    if title_match or content_matches >= 2:
                        logger.info(f"✅ 通过页面特征验证登录状态: 标题='{page_title}', 内容匹配={content_matches}个")

                        # 🔧 新增：登录成功后立即保存状态
                        try:
                            self.save_login_state()
                            logger.info("💾 登录状态已保存")
                        except Exception as e:
                            logger.warning(f"保存登录状态失败: {e}")

                        return True
                except Exception as e:
                    logger.debug(f"页面特征检查失败: {e}")

            logger.warning("❌ 未找到足够的登录指示器")
            return False

        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return False

    def _force_restore_login_state(self) -> bool:
        """🔧 新增：强制恢复登录状态"""
        try:
            logger.info("🔄 开始强制恢复微信视频号登录状态...")

            # 检查是否有保存的登录状态
            if not self.db_service.is_login_state_valid(self.platform_name, expire_hours=168):
                logger.warning("❌ 没有有效的登录状态可恢复")
                return False

            # 先访问微信视频号主页
            main_url = "https://channels.weixin.qq.com"
            logger.info(f"🌐 访问微信视频号主页: {main_url}")
            self.driver.get(main_url)
            time.sleep(3)

            # 加载登录状态
            if self.load_login_state():
                logger.info("✅ 登录状态加载成功")

                # 访问创作页面验证
                create_url = "https://channels.weixin.qq.com/platform/post/create"
                logger.info(f"🌐 验证登录状态，访问: {create_url}")
                self.driver.get(create_url)
                time.sleep(5)

                # 检查是否成功
                current_url = self.driver.current_url
                if 'login' not in current_url:
                    logger.info("✅ 登录状态恢复成功")
                    return True
                else:
                    logger.warning("❌ 登录状态恢复失败，仍跳转到登录页")
                    return False
            else:
                logger.warning("❌ 登录状态加载失败")
                return False

        except Exception as e:
            logger.error(f"强制恢复登录状态失败: {e}")
            return False
            
    async def _publish_video_impl(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """微信视频号视频发布实现"""
        try:
            # 🆕 验证视频信息是否符合微信视频号要求
            validation_result = validate_video_info(video_info)
            if not validation_result['valid']:
                logger.error(f"❌ 视频信息验证失败: {validation_result['errors']}")
                return {'success': False, 'error': f"视频信息不符合要求: {'; '.join(validation_result['errors'])}"}

            if validation_result['warnings']:
                for warning in validation_result['warnings']:
                    logger.warning(f"⚠️  {warning}")

            # 检查是否为模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 模拟模式：模拟微信视频号视频发布过程")
                
                # 模拟发布过程
                title = video_info.get('title', '')
                description = video_info.get('description', '')
                
                logger.info(f"模拟设置标题: {title}")
                await asyncio.sleep(1)
                logger.info(f"模拟设置描述: {description}")
                await asyncio.sleep(1)
                logger.info("模拟上传视频文件...")
                await asyncio.sleep(3)
                logger.info("模拟点击发表按钮...")
                await asyncio.sleep(2)

                logger.info("✅ 模拟发布成功！")
                return {'success': True, 'message': '模拟发布成功'}

            # 🔧 优化：智能登录状态管理
            upload_url = "https://channels.weixin.qq.com/platform/post/create"

            # 第一次尝试：直接访问发布页面
            logger.info(f"🌐 访问微信视频号发布页面: {upload_url}")
            self.driver.get(upload_url)
            time.sleep(5)  # 微信页面加载较慢

            # 检查是否跳转到登录页面
            current_url = self.driver.current_url
            if 'login' in current_url:
                logger.warning("⚠️ 跳转到登录页面，尝试恢复登录状态...")

                # 尝试强制恢复登录状态
                if self._force_restore_login_state():
                    logger.info("✅ 登录状态恢复成功")
                else:
                    logger.error("❌ 登录状态恢复失败")
                    return {'success': False, 'error': '登录状态已过期，请手动登录后重试'}

            # 最终验证登录状态
            if await self._check_login_status():
                logger.info("✅ 微信视频号登录状态验证成功")
            else:
                logger.error("❌ 微信视频号登录状态验证失败")
                return {'success': False, 'error': '登录状态验证失败，请在浏览器中手动登录后重试'}
                
            # 1. 上传视频文件
            video_path = video_info.get('video_path')
            if not video_path:
                return {'success': False, 'error': '视频路径不能为空'}
                
            logger.info(f"开始上传视频文件: {video_path}")

            # 🔧 优化：等待现代化页面元素加载完成
            if not self._wait_for_page_elements():
                return {'success': False, 'error': '页面元素加载超时，请检查网络连接'}

            # 🔧 优化：使用新的智能元素查找器
            logger.info("🔍 开始查找文件上传元素...")
            file_input = self._smart_element_finder('file_upload', timeout=15)

            if not file_input:
                logger.warning("⚠️ 无法找到文件上传元素，开始页面调试...")
                self._debug_page_elements()
                return {'success': False, 'error': '无法找到文件上传元素，请检查页面是否正确加载。页面调试信息已记录到日志中。'}

            # 🔧 优化：智能文件上传
            logger.info(f"📁 开始上传视频文件: {video_path}")

            # 等待元素变为可交互状态
            if not self._wait_for_element_interactive(file_input, timeout=5):
                logger.warning("⚠️ 文件输入框未完全加载，尝试继续...")

            upload_success = False
            try:
                # 方法1：直接发送文件路径
                file_input.send_keys(video_path)
                upload_success = True
                logger.info("✅ 视频文件上传成功（直接方法）")
            except Exception as e:
                logger.warning(f"直接上传失败: {e}")

                # 方法2：JavaScript上传
                try:
                    js_script = f"""
                    var input = arguments[0];
                    var file = new File([''], '{video_path}', {{type: 'video/mp4'}});
                    var dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    input.files = dataTransfer.files;
                    input.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return true;
                    """
                    result = self.driver.execute_script(js_script, file_input)
                    if result:
                        upload_success = True
                        logger.info("✅ 视频文件上传成功（JavaScript方法）")
                except Exception as e2:
                    logger.warning(f"JavaScript上传失败: {e2}")

                    # 方法3：备用安全上传
                    if self.upload_file_safe(By.XPATH, "//input[@type='file']", video_path, timeout=10):
                        upload_success = True
                        logger.info("✅ 视频文件上传成功（安全方法）")

            if not upload_success:
                return {'success': False, 'error': '视频上传失败 - 所有上传方法都失败了，请检查文件路径和格式'}
                
            # 等待视频上传完成
            logger.info("等待视频上传完成...")
            upload_complete = self._wait_for_upload_complete(timeout=600)  # 微信上传较慢，10分钟超时
            
            if not upload_complete:
                return {'success': False, 'error': '视频上传超时或失败'}
                
            # 2. 设置视频标题
            title = video_info.get('title', '')
            if title:
                logger.info(f"设置标题: {title}")

                # 根据微信建议，标题控制在6-16个字
                max_length = self.wechat_config['limits']['title_max_length']
                title_text = title[:max_length] if len(title) > max_length else title

                # 🔧 优化：使用智能元素查找器
                logger.info("🔍 查找标题输入框...")
                title_input = self._smart_element_finder('title_input', timeout=10)

                title_set = False
                if title_input:
                    try:
                        # 等待元素可交互
                        if self._wait_for_element_interactive(title_input, timeout=3):
                            # 清空并输入标题
                            title_input.clear()
                            time.sleep(0.5)  # 等待清空完成
                            title_input.send_keys(title_text)
                            title_set = True
                            logger.info(f"✅ 标题设置成功: {title_text}")
                        else:
                            logger.warning("⚠️ 标题输入框未完全加载")
                    except Exception as e:
                        logger.warning(f"标题输入失败: {e}")

                # 备用方法：JavaScript输入
                if not title_set:
                    try:
                        # 转义单引号以防止JavaScript错误
                        safe_title = title_text.replace("'", "\\'").replace('"', '\\"')
                        js_script = f"""
                        var inputs = document.querySelectorAll('input, textarea');
                        for (var i = 0; i < inputs.length; i++) {{
                            var input = inputs[i];
                            var placeholder = input.placeholder || '';
                            var className = input.className || '';
                            if (placeholder.includes('标题') || placeholder.includes('title') ||
                                className.includes('title') || i === 0) {{
                                input.value = '{safe_title}';
                                input.focus();
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                input.blur();
                                return true;
                            }}
                        }}
                        return false;
                        """
                        result = self.driver.execute_script(js_script)
                        if result:
                            title_set = True
                            logger.info(f"✅ JavaScript设置标题成功: {title_text}")
                    except Exception as e:
                        logger.warning(f"JavaScript设置标题失败: {e}")

                if not title_set:
                    logger.warning("⚠️ 标题设置失败，但继续发布流程")
                time.sleep(2)
                
            # 3. 设置视频描述
            description = video_info.get('description', '')
            if description:
                logger.info(f"设置描述: {description}")

                # 根据微信限制，控制描述长度
                max_desc_length = self.wechat_config['limits']['description_max_length']
                desc_text = description[:max_desc_length] if len(description) > max_desc_length else description

                # 🔧 优化：使用智能元素查找器
                logger.info("🔍 查找描述输入框...")
                desc_input = self._smart_element_finder('description_input', timeout=10)

                desc_set = False
                if desc_input:
                    try:
                        # 等待元素可交互
                        if self._wait_for_element_interactive(desc_input, timeout=3):
                            # 处理不同类型的输入框
                            if desc_input.tag_name.lower() == 'div' and desc_input.get_attribute('contenteditable'):
                                # 对于contenteditable的div
                                self.driver.execute_script("arguments[0].focus();", desc_input)
                                time.sleep(0.5)
                                self.driver.execute_script("arguments[0].innerText = arguments[1];", desc_input, desc_text)
                                self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", desc_input)
                                self.driver.execute_script("arguments[0].blur();", desc_input)
                            else:
                                # 对于textarea或input
                                desc_input.clear()
                                time.sleep(0.5)
                                desc_input.send_keys(desc_text)
                            desc_set = True
                            logger.info("✅ 描述设置成功")
                        else:
                            logger.warning("⚠️ 描述输入框未完全加载")
                    except Exception as e:
                        logger.warning(f"描述输入失败: {e}")

                # 备用方法：JavaScript输入
                if not desc_set:
                    try:
                        # 转义文本以防止JavaScript错误
                        safe_desc = desc_text.replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n')
                        js_script = f"""
                        var elements = document.querySelectorAll('textarea, div[contenteditable="true"], input');
                        for (var i = 0; i < elements.length; i++) {{
                            var elem = elements[i];
                            var placeholder = elem.placeholder || '';
                            var className = elem.className || '';
                            var tagName = elem.tagName.toLowerCase();

                            // 跳过已经处理过的标题输入框
                            if (placeholder.includes('标题') || className.includes('title')) {{
                                continue;
                            }}

                            if (placeholder.includes('描述') || placeholder.includes('简介') ||
                                className.includes('desc') || className.includes('content') ||
                                tagName === 'textarea') {{
                                elem.focus();
                                if (elem.contentEditable === 'true') {{
                                    elem.innerText = '{safe_desc}';
                                }} else {{
                                    elem.value = '{safe_desc}';
                                }}
                                elem.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                elem.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                elem.blur();
                                return true;
                            }}
                        }}
                        return false;
                        """
                        result = self.driver.execute_script(js_script)
                        if result:
                            desc_set = True
                            logger.info("✅ JavaScript设置描述成功")
                    except Exception as e:
                        logger.warning(f"JavaScript设置描述失败: {e}")

                if not desc_set:
                    logger.warning("⚠️ 描述设置失败，但继续发布流程")
                time.sleep(2)
                
            # 4. 设置标签（微信视频号通过#标签）
            tags = video_info.get('tags', [])
            if tags:
                logger.info(f"设置标签: {tags}")
                # 微信视频号通过在描述中添加#标签的方式设置标签
                tag_text = ' '.join([f'#{tag}' for tag in tags[:3]])  # 限制3个标签
                
                # 在描述末尾添加标签
                desc_selectors = [
                    '//textarea[contains(@placeholder, "描述")]',
                    '//textarea[contains(@placeholder, "简介")]'
                ]
                
                for selector in desc_selectors:
                    element = self.find_element_safe(By.XPATH, selector, timeout=3)
                    if element:
                        # 在现有内容后添加标签
                        element.send_keys(f" {tag_text}")
                        break
                time.sleep(2)

            # 4.5. 🆕 设置微信视频号特有功能
            await self._set_wechat_specific_features(video_info)

            # 5. 设置封面（如果有）
            cover_path = video_info.get('cover_path')
            if cover_path:
                logger.info(f"设置封面: {cover_path}")
                try:
                    cover_selector = '//div[contains(text(),"选择封面")]'
                    if self.click_element_safe(By.XPATH, cover_selector):
                        time.sleep(2)
                        # 上传自定义封面
                        cover_upload_selector = '//input[@type="file" and contains(@accept, "image")]'
                        if self.upload_file_safe(By.XPATH, cover_upload_selector, cover_path):
                            time.sleep(3)
                            # 确认封面
                            confirm_selector = '//button[contains(text(), "确定")]'
                            self.click_element_safe(By.XPATH, confirm_selector)
                        time.sleep(2)
                except Exception as e:
                    logger.warning(f"设置封面失败: {e}")
                    
            # 6. 设置可见性（默认公开）
            visibility = video_info.get('visibility', 'public')
            if visibility == 'private':
                logger.info("设置为私密")
                try:
                    private_selector = '//input[@type="radio" and @value="private"]'
                    self.click_element_safe(By.XPATH, private_selector)
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"设置可见性失败: {e}")
                    
            # 7. 发布视频
            logger.info("开始发布视频...")
            time.sleep(3)
            
            # 🔧 优化：智能发布流程
            logger.info("🚀 开始发布视频...")
            time.sleep(3)  # 等待页面稳定

            # 使用智能元素查找器查找发布按钮
            logger.info("🔍 查找发布按钮...")
            publish_button = self._smart_element_finder('publish_button', timeout=15)

            if not publish_button:
                return {'success': False, 'error': '无法找到发布按钮，请检查页面是否完全加载'}

            # 等待发布按钮可交互
            if not self._wait_for_element_interactive(publish_button, timeout=5):
                logger.warning("⚠️ 发布按钮未完全加载，尝试继续...")

            # 使用增强点击方法
            logger.info("🖱️ 点击发布按钮...")
            if self._enhanced_click(publish_button):
                logger.info("✅ 发布按钮点击成功，等待发布完成...")
                time.sleep(8)  # 微信发布需要更长时间

                # 处理可能的错误弹窗
                self._handle_error_dialogs()

                # 检查发布结果
                if self._check_publish_result():
                    logger.info("🎉 视频发布成功！")
                    return {'success': True, 'message': '视频发布成功'}
                else:
                    logger.info("✅ 视频已提交发布，请稍后查看发布状态")
                    return {'success': True, 'message': '视频已提交发布'}
            else:
                return {'success': False, 'error': '发布按钮点击失败，请手动完成发布'}
                
        except Exception as e:
            logger.error(f"微信视频号视频发布失败: {e}")
            return {'success': False, 'error': str(e)}

    def _wait_for_upload_complete(self, timeout: int = 600) -> bool:
        """等待视频上传完成"""
        try:
            logger.info("等待微信视频号视频上传完成...")
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # 🔧 优化：使用配置文件中的上传进度指示器
                    progress_indicators = self.wechat_config['selectors']['upload_progress']
                    
                    uploading = False
                    for selector in progress_indicators:
                        if self.find_element_safe(By.XPATH, selector, timeout=1):
                            uploading = True
                            break
                    
                    if not uploading:
                        # 🔧 优化：使用配置文件中的上传完成指示器
                        completion_indicators = self.wechat_config['selectors']['upload_complete']

                        for selector in completion_indicators:
                            element = self.find_element_safe(By.XPATH, selector, timeout=2)
                            if element and element.is_enabled():
                                logger.info("✅ 检测到上传完成")
                                return True
                    
                    time.sleep(5)  # 微信上传检查间隔较长
                    
                except Exception as e:
                    logger.debug(f"等待上传完成时出现异常: {e}")
                    time.sleep(3)
            
            logger.warning("等待上传完成超时")
            return False
            
        except Exception as e:
            logger.error(f"等待上传完成失败: {e}")
            return False

    def _smart_find_publish_button(self) -> bool:
        """🔧 优化：智能查找并点击发布按钮"""
        try:
            logger.info("开始智能检测微信视频号发布按钮...")

            # 方法1：使用配置文件中的发布按钮选择器
            publish_selectors = self.wechat_config['selectors']['publish_button']

            for i, selector in enumerate(publish_selectors):
                logger.debug(f"尝试发布按钮选择器 {i+1}/{len(publish_selectors)}: {selector}")
                element = self.find_element_safe(By.XPATH, selector, timeout=3)
                if element and element.is_enabled() and element.is_displayed():
                    try:
                        # 滚动到元素可见位置
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(1)

                        # 点击发布按钮
                        element.click()
                        logger.info("✅ 发布按钮点击成功（XPath选择器）")
                        return True

                    except Exception as e:
                        logger.debug(f"点击发布按钮失败: {e}")
                        continue

            # 方法2：通过文本内容查找发布按钮
            logger.info("🔄 尝试通过文本内容查找发布按钮...")
            publish_texts = ["发表", "发布", "提交", "确定"]
            for text in publish_texts:
                try:
                    elements = self.driver.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            # 检查按钮是否在页面底部（通常发布按钮在底部）
                            location = element.location
                            if location['y'] > 300:  # 假设发布按钮在页面下半部分
                                try:
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                    time.sleep(1)
                                    element.click()
                                    logger.info(f"✅ 发布按钮点击成功（文本: {text}）")
                                    return True
                                except Exception as e:
                                    logger.debug(f"点击按钮'{text}'失败: {e}")
                                    continue
                except Exception as e:
                    logger.debug(f"查找文本'{text}'失败: {e}")
                    continue

            # 方法3：JavaScript强制查找发布按钮
            logger.info("🔄 尝试JavaScript强制查找发布按钮...")
            try:
                js_script = """
                var buttons = document.querySelectorAll('button, input[type="submit"], div[role="button"]');
                var publishButton = null;
                var maxY = 0;

                for (var i = 0; i < buttons.length; i++) {
                    var btn = buttons[i];
                    var text = (btn.innerText || btn.textContent || btn.value || '').trim();
                    var rect = btn.getBoundingClientRect();

                    if ((text.includes('发表') || text.includes('发布') || text.includes('提交')) &&
                        rect.width > 0 && rect.height > 0 && rect.top > maxY) {
                        publishButton = btn;
                        maxY = rect.top;
                    }
                }

                if (publishButton) {
                    publishButton.scrollIntoView(true);
                    publishButton.click();
                    return true;
                }
                return false;
                """
                result = self.driver.execute_script(js_script)
                if result:
                    logger.info("✅ JavaScript强制点击发布按钮成功")
                    return True
            except Exception as e:
                logger.debug(f"JavaScript查找发布按钮失败: {e}")

            logger.warning("⚠️ 所有方法都未找到可用的发布按钮")
            return False

        except Exception as e:
            logger.error(f"智能查找发布按钮失败: {e}")
            return False

    def _check_publish_result(self) -> bool:
        """检查发布结果"""
        try:
            # 检查成功提示
            success_indicators = [
                "发表成功",
                "发布成功",
                "提交成功",
                "上传成功",
                "发布中",
                "审核中"
            ]

            for indicator in success_indicators:
                elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{indicator}')]")
                if elements:
                    logger.info(f"找到成功指示器: {indicator}")
                    return True

            return False

        except Exception as e:
            logger.debug(f"检查发布结果失败: {e}")
            return False

    def _handle_error_dialogs(self):
        """处理发布后可能出现的错误弹窗"""
        try:
            time.sleep(3)
            
            # 常见错误弹窗处理
            error_dialogs = [
                '//div[contains(text(), "确定")]',
                '//button[contains(text(), "确定")]',
                '//button[contains(text(), "知道了")]',
                '//button[contains(text(), "我知道了")]'
            ]
            
            for selector in error_dialogs:
                element = self.find_element_safe(By.XPATH, selector, timeout=2)
                if element:
                    element.click()
                    logger.info("处理了错误弹窗")
                    time.sleep(2)
                    
        except Exception as e:
            logger.debug(f"处理错误弹窗失败: {e}")

    async def _set_wechat_specific_features(self, video_info: Dict[str, Any]):
        """🆕 设置微信视频号特有功能"""
        try:
            logger.info("开始设置微信视频号特有功能...")

            # 1. 设置位置信息
            location = video_info.get('location', '')
            if location:
                await self._set_location(location)

            # 2. 设置原创声明
            is_original = video_info.get('is_original', False)
            if is_original:
                await self._set_original_claim()

            # 3. 设置定时发布
            scheduled_time = video_info.get('scheduled_time', '')
            if scheduled_time:
                await self._set_scheduled_publish(scheduled_time)

            # 4. 添加到合集
            collection = video_info.get('collection', '')
            if collection:
                await self._add_to_collection(collection)

        except Exception as e:
            logger.warning(f"设置微信特有功能时出现异常: {e}")

    async def _set_location(self, location: str):
        """设置位置信息"""
        try:
            logger.info(f"设置位置: {location}")

            # 🔧 优化：使用配置文件中的位置设置选择器
            location_selectors = self.wechat_config['selectors']['location_button']

            for selector in location_selectors:
                element = self.find_element_safe(By.XPATH, selector, timeout=3)
                if element:
                    element.click()
                    time.sleep(1)

                    # 🔧 优化：使用配置文件中的位置输入框选择器
                    location_input_selectors = self.wechat_config['selectors']['location_input']

                    for input_selector in location_input_selectors:
                        if self.send_keys_safe(By.XPATH, input_selector, location):
                            time.sleep(2)
                            # 选择第一个搜索结果
                            result_selector = '//div[contains(@class, "location-result")]//div[1]'
                            result_element = self.find_element_safe(By.XPATH, result_selector, timeout=3)
                            if result_element:
                                result_element.click()
                                logger.info("✅ 位置设置成功")
                                return
                    break

        except Exception as e:
            logger.warning(f"设置位置失败: {e}")

    async def _set_original_claim(self):
        """设置原创声明"""
        try:
            logger.info("设置原创声明...")

            # 🔧 优化：使用配置文件中的原创声明选择器
            original_selectors = self.wechat_config['selectors']['original_claim']

            for selector in original_selectors:
                element = self.find_element_safe(By.XPATH, selector, timeout=3)
                if element and not element.is_selected():
                    element.click()
                    logger.info("✅ 原创声明设置成功")
                    time.sleep(1)
                    return

        except Exception as e:
            logger.warning(f"设置原创声明失败: {e}")

    async def _set_scheduled_publish(self, scheduled_time: str):
        """设置定时发布"""
        try:
            logger.info(f"设置定时发布: {scheduled_time}")

            # 查找定时发表选项
            schedule_selectors = [
                '//div[contains(text(), "定时发表")]',
                '//span[contains(text(), "定时发表")]',
                '//input[@type="radio"]//following-sibling::*[contains(text(), "定时")]',
                '//label[contains(text(), "定时")]//input[@type="radio"]'
            ]

            for selector in schedule_selectors:
                element = self.find_element_safe(By.XPATH, selector, timeout=3)
                if element:
                    element.click()
                    time.sleep(1)

                    # 查找时间输入框
                    time_input_selectors = [
                        '//input[@type="datetime-local"]',
                        '//input[contains(@placeholder, "选择时间")]',
                        '//input[contains(@class, "time-picker")]'
                    ]

                    for time_selector in time_input_selectors:
                        if self.send_keys_safe(By.XPATH, time_selector, scheduled_time):
                            logger.info("✅ 定时发布设置成功")
                            return
                    break

        except Exception as e:
            logger.warning(f"设置定时发布失败: {e}")

    async def _add_to_collection(self, collection: str):
        """添加到合集"""
        try:
            logger.info(f"添加到合集: {collection}")

            # 查找合集设置按钮
            collection_selectors = [
                '//div[contains(text(), "添加到合集")]',
                '//span[contains(text(), "合集")]',
                '//button[contains(text(), "合集")]',
                '//div[contains(@class, "collection")]'
            ]

            for selector in collection_selectors:
                element = self.find_element_safe(By.XPATH, selector, timeout=3)
                if element:
                    element.click()
                    time.sleep(1)

                    # 查找合集搜索或选择框
                    collection_input_selectors = [
                        '//input[contains(@placeholder, "搜索合集")]',
                        '//input[contains(@placeholder, "合集名称")]',
                        '//input[contains(@class, "collection-input")]'
                    ]

                    for input_selector in collection_input_selectors:
                        if self.send_keys_safe(By.XPATH, input_selector, collection):
                            time.sleep(2)
                            # 选择第一个搜索结果或创建新合集
                            result_selector = '//div[contains(@class, "collection-result")]//div[1]'
                            result_element = self.find_element_safe(By.XPATH, result_selector, timeout=3)
                            if result_element:
                                result_element.click()
                                logger.info("✅ 合集设置成功")
                                return
                    break

        except Exception as e:
            logger.warning(f"添加到合集失败: {e}")
