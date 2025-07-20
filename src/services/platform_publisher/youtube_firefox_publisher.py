#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Firefox发布器
专门为Firefox浏览器优化的YouTube视频发布器
"""

import os
import time
import asyncio
import random
from typing import Dict, Any
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .selenium_publisher_base import SeleniumPublisherBase
from src.utils.logger import logger


class YouTubeFirefoxPublisher(SeleniumPublisherBase):
    """YouTube Firefox发布器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__('youtube', config)
        self.upload_url = "https://studio.youtube.com/channel/UC/videos/upload"
        
    def initialize(self) -> bool:
        """初始化Firefox驱动"""
        try:
            logger.info("🦊 初始化YouTube Firefox发布器...")
            
            # 检查模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 模拟模式启用，跳过浏览器初始化")
                return True
            
            self._init_firefox_driver()
            return True
            
        except Exception as e:
            logger.error(f"❌ Firefox驱动初始化失败: {e}")
            return False
    
    def _init_firefox_driver(self):
        """初始化Firefox驱动"""
        logger.info("🦊 开始初始化Firefox驱动...")
        
        options = FirefoxOptions()
        
        # 基本配置
        if self.selenium_config.get('headless', False):
            options.add_argument('--headless')
        
        # YouTube优化配置
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        
        # 用户代理设置
        if self.selenium_config.get('random_user_agent', True):
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/109.0"
            ]
            options.set_preference("general.useragent.override", random.choice(user_agents))
        
        # 媒体设置（YouTube需要）
        options.set_preference("media.navigator.enabled", True)
        options.set_preference("media.navigator.permission.disabled", True)
        
        # 下载设置
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.helperApps.neverAsk.saveToDisk", "video/mp4,video/avi,video/mov")
        
        # 性能优化
        if self.selenium_config.get('disable_images', False):
            options.set_preference("permissions.default.image", 2)
        
        # 通知设置
        options.set_preference("dom.webnotifications.enabled", False)
        options.set_preference("dom.push.enabled", False)
        
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
            self.driver.set_page_load_timeout(self.selenium_config.get('page_load_timeout', 90))
            self.driver.implicitly_wait(self.selenium_config.get('implicit_wait', 15))
            self.driver.set_script_timeout(self.selenium_config.get('script_timeout', 60))
            
            # 窗口大小设置
            if self.selenium_config.get('random_window_size', True):
                widths = [1366, 1440, 1920]
                heights = [768, 900, 1080]
                width = random.choice(widths)
                height = random.choice(heights)
                self.driver.set_window_size(width, height)
            
            # 注入反检测脚本
            if self.selenium_config.get('inject_stealth_scripts', True):
                self._inject_firefox_stealth_scripts()
            
            logger.info("✅ Firefox驱动初始化成功")
            
        except Exception as e:
            logger.error(f"❌ Firefox驱动初始化失败: {e}")
            raise
    
    def _inject_firefox_stealth_scripts(self):
        """注入Firefox反检测脚本"""
        try:
            # Firefox特定的反检测脚本
            stealth_script = """
            // 隐藏webdriver属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 修改plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // 修改语言
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en'],
            });
            
            // 隐藏自动化标识
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'granted' })
                })
            });
            
            // Firefox特定优化
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 4
            });
            
            // 模拟真实浏览器行为
            window.outerHeight = window.screen.height;
            window.outerWidth = window.screen.width;
            """
            
            self.driver.execute_script(stealth_script)
            logger.debug("✅ Firefox反检测脚本注入成功")
            
        except Exception as e:
            logger.warning(f"⚠️ Firefox反检测脚本注入失败: {e}")
    
    async def _check_login_status(self) -> bool:
        """检查YouTube登录状态"""
        try:
            logger.info("🔍 检查YouTube登录状态...")
            
            # 访问YouTube Studio
            self.driver.get("https://studio.youtube.com")
            await asyncio.sleep(5)  # Firefox需要更长加载时间
            
            # 检查当前URL
            current_url = self.driver.current_url
            logger.info(f"当前页面URL: {current_url}")
            
            # 如果在登录页面
            if any(keyword in current_url for keyword in ['accounts.google.com', 'signin']):
                logger.warning("⚠️ 检测到登录页面，需要手动登录")
                logger.info("请在Firefox浏览器中手动登录YouTube Studio")
                return False
            
            # 检查是否在YouTube Studio
            if 'studio.youtube.com' in current_url:
                # 检查登录指示器
                login_indicators = [
                    "//ytcp-button[@id='create-button']",  # 创建按钮
                    "//div[@id='avatar-btn']",             # 头像按钮
                    "//ytcp-upload-file-picker",           # 上传组件
                ]
                
                for selector in login_indicators:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        if element:
                            logger.info("✅ YouTube登录状态正常")
                            return True
                    except TimeoutException:
                        continue
            
            logger.warning("⚠️ 未检测到登录状态")
            return False
            
        except Exception as e:
            logger.error(f"❌ 检查登录状态失败: {e}")
            return False
    
    async def upload_video(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """上传视频到YouTube"""
        try:
            logger.info("🚀 开始YouTube视频上传（Firefox）...")
            
            # 检查模拟模式
            if self.selenium_config.get('simulation_mode', False):
                return await self._simulate_upload(video_info)
            
            # 检查登录状态
            if not await self._check_login_status():
                return {
                    'success': False,
                    'error': '请先在Firefox浏览器中登录YouTube Studio'
                }
            
            # 访问上传页面
            logger.info("🌐 访问YouTube上传页面...")
            self.driver.get(self.upload_url)
            await asyncio.sleep(5)
            
            # 上传视频文件
            video_path = video_info.get('video_path')
            if not video_path or not os.path.exists(video_path):
                return {'success': False, 'error': '视频文件不存在'}
            
            if not await self._upload_video_file(video_path):
                return {'success': False, 'error': '视频文件上传失败'}
            
            # 等待上传完成
            if not await self._wait_for_upload_complete():
                return {'success': False, 'error': '视频上传超时'}
            
            # 设置视频信息
            await self._set_video_info(video_info)
            
            # 发布视频
            if await self._publish_video():
                logger.info("✅ YouTube视频发布成功！")
                return {'success': True, 'message': '视频发布成功'}
            else:
                return {'success': False, 'error': '视频发布失败'}
                
        except Exception as e:
            logger.error(f"❌ YouTube视频上传失败: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _simulate_upload(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """模拟上传过程"""
        logger.info("🎭 模拟YouTube视频上传过程...")
        
        title = video_info.get('title', '未命名视频')
        logger.info(f"模拟设置标题: {title}")
        await asyncio.sleep(2)
        
        description = video_info.get('description', '')
        if description:
            logger.info(f"模拟设置描述: {description[:50]}...")
            await asyncio.sleep(2)
        
        logger.info("模拟上传视频文件...")
        await asyncio.sleep(5)
        
        logger.info("模拟等待处理完成...")
        await asyncio.sleep(3)
        
        logger.info("模拟发布视频...")
        await asyncio.sleep(2)
        
        logger.info("✅ 模拟发布成功！")
        return {'success': True, 'message': '模拟发布成功'}

    async def _upload_video_file(self, video_path: str) -> bool:
        """上传视频文件"""
        try:
            logger.info(f"📁 开始上传视频文件: {video_path}")

            # Firefox文件上传选择器
            file_input_selectors = [
                "//input[@type='file']",
                "//input[@accept='video/*']",
                "//ytcp-upload-file-picker//input[@type='file']",
                "//input[contains(@accept, 'video')]"
            ]

            for selector in file_input_selectors:
                try:
                    logger.info(f"尝试选择器: {selector}")

                    # 等待元素出现
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )

                    if element:
                        # 发送文件路径
                        element.send_keys(video_path)
                        logger.info("✅ 视频文件上传成功")
                        await asyncio.sleep(3)
                        return True

                except TimeoutException:
                    logger.debug(f"选择器超时: {selector}")
                    continue
                except Exception as e:
                    logger.debug(f"选择器失败: {selector}, 错误: {e}")
                    continue

            logger.error("❌ 未找到文件上传元素")
            return False

        except Exception as e:
            logger.error(f"❌ 上传视频文件失败: {e}")
            return False

    async def _wait_for_upload_complete(self, timeout: int = 900) -> bool:
        """等待视频上传完成"""
        try:
            logger.info("⏳ 等待视频上传完成...")
            start_time = time.time()

            while time.time() - start_time < timeout:
                try:
                    # 检查上传进度
                    progress_selectors = [
                        "//span[contains(text(), '正在处理')]",
                        "//span[contains(text(), 'Processing')]",
                        "//div[@class='progress-label']",
                        "//ytcp-video-upload-progress"
                    ]

                    upload_in_progress = False
                    for selector in progress_selectors:
                        try:
                            element = self.driver.find_element(By.XPATH, selector)
                            if element and element.is_displayed():
                                upload_in_progress = True
                                break
                        except NoSuchElementException:
                            continue

                    if not upload_in_progress:
                        # 检查是否到达详情页面
                        detail_selectors = [
                            "//div[@id='textbox']",  # 标题输入框
                            "//div[contains(@class, 'title-input')]",
                            "//ytcp-social-suggestions-textbox"
                        ]

                        for selector in detail_selectors:
                            try:
                                element = self.driver.find_element(By.XPATH, selector)
                                if element:
                                    logger.info("✅ 视频上传完成，进入详情设置")
                                    return True
                            except NoSuchElementException:
                                continue

                    await asyncio.sleep(5)

                except Exception as e:
                    logger.debug(f"检查上传状态时出错: {e}")
                    await asyncio.sleep(5)

            logger.warning("⚠️ 视频上传超时")
            return False

        except Exception as e:
            logger.error(f"❌ 等待上传完成失败: {e}")
            return False

    async def _set_video_info(self, video_info: Dict[str, Any]):
        """设置视频信息"""
        try:
            logger.info("📝 设置视频信息...")

            # 设置标题
            title = video_info.get('title', '')
            if title:
                await self._set_title(title)

            # 设置描述
            description = video_info.get('description', '')
            if description:
                await self._set_description(description)

            # 设置标签
            tags = video_info.get('tags', [])
            if tags:
                await self._set_tags(tags)

            # 设置隐私级别
            privacy = video_info.get('privacy', 'public')
            await self._set_privacy(privacy)

            logger.info("✅ 视频信息设置完成")

        except Exception as e:
            logger.error(f"❌ 设置视频信息失败: {e}")

    async def _set_title(self, title: str):
        """设置视频标题"""
        try:
            title_selectors = [
                "//div[@id='textbox' and @contenteditable='true']",
                "//div[contains(@class, 'title-input')]//div[@contenteditable='true']",
                "//ytcp-social-suggestions-textbox//div[@contenteditable='true']"
            ]

            for selector in title_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )

                    if element:
                        # 清空并输入标题
                        element.clear()
                        element.click()
                        await asyncio.sleep(1)
                        element.send_keys(title)
                        logger.info(f"✅ 标题设置成功: {title}")
                        return

                except TimeoutException:
                    continue

            logger.warning("⚠️ 未找到标题输入框")

        except Exception as e:
            logger.error(f"❌ 设置标题失败: {e}")

    async def _set_description(self, description: str):
        """设置视频描述"""
        try:
            description_selectors = [
                "//div[@id='description-textarea']//div[@contenteditable='true']",
                "//ytcp-social-suggestions-textbox[@label='描述']//div[@contenteditable='true']",
                "//div[contains(@class, 'description')]//div[@contenteditable='true']"
            ]

            for selector in description_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )

                    if element:
                        element.clear()
                        element.click()
                        await asyncio.sleep(1)
                        element.send_keys(description)
                        logger.info("✅ 描述设置成功")
                        return

                except TimeoutException:
                    continue

            logger.warning("⚠️ 未找到描述输入框")

        except Exception as e:
            logger.error(f"❌ 设置描述失败: {e}")

    async def _set_tags(self, tags: list):
        """设置视频标签"""
        try:
            # 点击显示更多选项
            more_options_selectors = [
                "//ytcp-button[@id='toggle-button']",
                "//button[contains(text(), '显示更多')]",
                "//button[contains(text(), 'Show more')]"
            ]

            for selector in more_options_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element and element.is_displayed():
                        element.click()
                        await asyncio.sleep(2)
                        break
                except NoSuchElementException:
                    continue

            # 设置标签
            tags_text = ', '.join(tags[:15])  # YouTube最多15个标签

            tags_selectors = [
                "//input[@id='tags-input']",
                "//ytcp-form-input-container[@label='标签']//input",
                "//input[contains(@placeholder, '标签')]"
            ]

            for selector in tags_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )

                    if element:
                        element.clear()
                        element.send_keys(tags_text)
                        logger.info(f"✅ 标签设置成功: {tags_text}")
                        return

                except TimeoutException:
                    continue

            logger.warning("⚠️ 未找到标签输入框")

        except Exception as e:
            logger.error(f"❌ 设置标签失败: {e}")

    async def _set_privacy(self, privacy: str):
        """设置隐私级别"""
        try:
            # 点击隐私设置
            privacy_selectors = [
                "//ytcp-video-visibility-select",
                "//div[contains(@class, 'privacy')]//ytcp-dropdown-trigger",
                "//button[contains(@aria-label, '隐私')]"
            ]

            for selector in privacy_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )

                    if element:
                        element.click()
                        await asyncio.sleep(2)

                        # 选择隐私级别
                        privacy_options = {
                            'public': ['公开', 'Public'],
                            'unlisted': ['不公开列出', 'Unlisted'],
                            'private': ['私人', 'Private']
                        }

                        options = privacy_options.get(privacy, ['公开', 'Public'])

                        for option_text in options:
                            try:
                                option_element = self.driver.find_element(
                                    By.XPATH, f"//span[contains(text(), '{option_text}')]"
                                )
                                if option_element:
                                    option_element.click()
                                    logger.info(f"✅ 隐私级别设置为: {privacy}")
                                    return
                            except NoSuchElementException:
                                continue

                        break

                except TimeoutException:
                    continue

            logger.warning("⚠️ 未找到隐私设置")

        except Exception as e:
            logger.error(f"❌ 设置隐私级别失败: {e}")

    async def _publish_video(self) -> bool:
        """发布视频"""
        try:
            logger.info("🚀 开始发布视频...")

            # 发布按钮选择器
            publish_selectors = [
                "//ytcp-button[@id='done-button']",
                "//button[contains(text(), '发布')]",
                "//button[contains(text(), 'Publish')]",
                "//ytcp-button[contains(@class, 'done-button')]"
            ]

            for selector in publish_selectors:
                try:
                    element = WebDriverWait(self.driver, 15).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )

                    if element:
                        # 滚动到按钮位置
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        await asyncio.sleep(2)

                        # 点击发布
                        element.click()
                        logger.info("✅ 发布按钮点击成功")

                        # 等待发布完成
                        await asyncio.sleep(10)
                        return True

                except TimeoutException:
                    continue

            logger.warning("⚠️ 未找到发布按钮")
            return False

        except Exception as e:
            logger.error(f"❌ 发布视频失败: {e}")
            return False
