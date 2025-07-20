#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的YouTube Selenium发布器
使用反检测技术，提高成功率
"""

import time
import random
import asyncio
from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium import webdriver

from .selenium_publisher_base import SeleniumPublisherBase
from src.utils.logger import logger

class YouTubeStealthPublisher(SeleniumPublisherBase):
    """增强的YouTube Selenium发布器，使用反检测技术"""
    
    def __init__(self, config: Dict[str, Any]):
        # 强制使用Chrome并配置反检测
        config['driver_type'] = 'chrome'
        super().__init__('youtube_stealth', config)
        
    def _init_chrome_driver(self):
        """初始化反检测Chrome驱动"""
        options = ChromeOptions()
        
        # 基本选项
        if self.selenium_config['headless']:
            options.add_argument('--headless')
        
        # 🔧 反检测配置
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 🔧 模拟真实用户
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        # 🔧 窗口大小随机化
        window_sizes = ['1920,1080', '1366,768', '1440,900', '1536,864']
        options.add_argument(f'--window-size={random.choice(window_sizes)}')
        
        # 🔧 语言和地区
        options.add_argument('--lang=zh-CN')
        options.add_preference('intl.accept_languages', 'zh-CN,zh,en-US,en')
        
        # 🔧 禁用图片加载（可选，提高速度）
        if self.selenium_config.get('disable_images', False):
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
        
        try:
            # 优先尝试连接调试模式
            debugger_address = self.selenium_config.get('debugger_address', '127.0.0.1:9222')
            
            try:
                logger.info(f"🔗 尝试连接Chrome调试模式: {debugger_address}")
                debug_options = ChromeOptions()
                debug_options.add_experimental_option("debuggerAddress", debugger_address)
                
                self.driver = webdriver.Chrome(options=debug_options)
                logger.info("✅ 成功连接到Chrome调试模式")
                
                # 注入反检测脚本
                self._inject_stealth_scripts()
                return
                
            except Exception as e:
                logger.warning(f"连接调试模式失败: {e}")
                logger.info("🔄 切换到普通模式...")
            
            # 普通模式启动
            self.driver = webdriver.Chrome(options=options)
            
            # 注入反检测脚本
            self._inject_stealth_scripts()
            
            # 设置超时
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(self.selenium_config.get('implicit_wait', 10))
            
            logger.info("✅ Chrome反检测驱动初始化成功")
            
        except Exception as e:
            logger.error(f"❌ Chrome驱动初始化失败: {e}")
            raise
    
    def _inject_stealth_scripts(self):
        """注入增强反检测脚本"""
        try:
            # 综合反检测脚本
            stealth_script = """
            // 隐藏webdriver属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            // 隐藏Chrome自动化扩展
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

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

            // 修改User-Agent相关
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });

            // 隐藏Selenium标识
            delete window.document.$cdc_asdjflasutopfhvcZLmcfl_;
            delete window.$chrome_asyncScriptInfo;
            delete window.$cdc_asdjflasutopfhvcZLmcfl_;

            // 模拟真实浏览器行为
            window.outerHeight = window.screen.height;
            window.outerWidth = window.screen.width;

            // 隐藏自动化检测
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 4
            });
            """

            self.driver.execute_script(stealth_script)
            logger.debug("✅ 增强反检测脚本注入成功")

        except Exception as e:
            logger.warning(f"⚠️ 反检测脚本注入失败: {e}")
    
    def _get_platform_url(self) -> str:
        """获取YouTube Studio上传页面URL"""
        return "https://studio.youtube.com/channel/UC/videos/upload"
    
    async def _check_login_status(self) -> bool:
        """检查YouTube登录状态"""
        try:
            # 访问YouTube Studio
            self.driver.get("https://studio.youtube.com")
            await asyncio.sleep(3)
            
            # 检查是否需要登录
            current_url = self.driver.current_url
            if 'accounts.google.com' in current_url or 'signin' in current_url:
                logger.warning("⚠️ 需要登录YouTube")
                return False
            
            # 检查是否在Studio页面
            if 'studio.youtube.com' in current_url:
                logger.info("✅ YouTube登录状态正常")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 检查登录状态失败: {e}")
            return False
    
    async def upload_video(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """上传视频到YouTube"""
        try:
            logger.info("🚀 开始YouTube视频上传...")
            
            # 检查登录状态
            if not await self._check_login_status():
                return {
                    'success': False, 
                    'error': '请先在浏览器中登录YouTube Studio'
                }
            
            # 访问上传页面
            upload_url = "https://studio.youtube.com/channel/UC/videos/upload"
            logger.info(f"🌐 访问上传页面: {upload_url}")
            self.driver.get(upload_url)
            
            # 随机等待，模拟人类行为
            await asyncio.sleep(random.uniform(2, 4))
            
            # 1. 上传视频文件
            video_path = video_info.get('video_path')
            if not video_path:
                return {'success': False, 'error': '视频路径不能为空'}
            
            logger.info(f"📁 上传视频文件: {video_path}")
            
            # 查找文件输入框
            file_input = await self._find_file_input()
            if not file_input:
                return {'success': False, 'error': '未找到文件上传元素'}
            
            # 上传文件
            file_input.send_keys(video_path)
            logger.info("✅ 文件上传开始")
            
            # 等待上传界面加载
            await asyncio.sleep(5)
            
            # 2. 设置标题
            title = video_info.get('title', '')
            if title:
                await self._set_title(title)
            
            # 3. 设置描述
            description = video_info.get('description', '')
            if description:
                await self._set_description(description)
            
            # 4. 等待上传完成
            if not await self._wait_for_upload_complete():
                return {'success': False, 'error': '视频上传超时'}
            
            # 5. 发布视频
            if await self._publish_video():
                logger.info("🎉 视频发布成功!")
                return {'success': True, 'message': '视频发布成功'}
            else:
                return {'success': False, 'error': '发布失败'}
                
        except Exception as e:
            logger.error(f"❌ YouTube视频上传失败: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _find_file_input(self) -> Any:
        """查找文件输入框"""
        selectors = [
            'input[type="file"]',
            'input[accept*="video"]',
            '#select-files-button input',
            'ytcp-upload-file-picker input'
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element:
                    logger.info(f"✅ 找到文件输入框: {selector}")
                    return element
            except:
                continue
        
        logger.warning("⚠️ 未找到文件输入框")
        return None
    
    async def _set_title(self, title: str):
        """设置视频标题"""
        try:
            # YouTube标题输入框通常是contenteditable的div
            title_selectors = [
                'div[aria-label*="title" i][contenteditable="true"]',
                'div[data-placeholder*="title" i][contenteditable="true"]',
                '#textbox[contenteditable="true"]'
            ]
            
            for selector in title_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element:
                        # 清空并输入标题
                        element.clear()
                        await asyncio.sleep(0.5)
                        element.send_keys(title[:100])  # YouTube标题限制
                        logger.info(f"✅ 标题设置成功: {title[:50]}...")
                        return
                except:
                    continue
            
            logger.warning("⚠️ 未找到标题输入框")
            
        except Exception as e:
            logger.warning(f"⚠️ 设置标题失败: {e}")
    
    async def _set_description(self, description: str):
        """设置视频描述"""
        try:
            # YouTube描述输入框
            desc_selectors = [
                'div[aria-label*="description" i][contenteditable="true"]',
                'div[data-placeholder*="description" i][contenteditable="true"]',
                '#description-textarea'
            ]
            
            for selector in desc_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element:
                        element.clear()
                        await asyncio.sleep(0.5)
                        element.send_keys(description[:5000])  # YouTube描述限制
                        logger.info("✅ 描述设置成功")
                        return
                except:
                    continue
            
            logger.warning("⚠️ 未找到描述输入框")
            
        except Exception as e:
            logger.warning(f"⚠️ 设置描述失败: {e}")
    
    async def _wait_for_upload_complete(self, timeout: int = 600) -> bool:
        """等待上传完成"""
        logger.info("⏳ 等待视频上传完成...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 检查上传进度
                progress_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    '[role="progressbar"], .progress-bar, [aria-label*="progress" i]'
                )
                
                if progress_elements:
                    # 还在上传中
                    await asyncio.sleep(5)
                    continue
                
                # 检查是否出现"发布"按钮
                publish_buttons = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    'button[aria-label*="publish" i], button:contains("发布"), #done-button'
                )
                
                if publish_buttons:
                    logger.info("✅ 视频上传完成")
                    return True
                
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.debug(f"检查上传状态时出错: {e}")
                await asyncio.sleep(5)
        
        logger.warning("⚠️ 等待上传完成超时")
        return False
    
    async def _publish_video(self) -> bool:
        """发布视频"""
        try:
            # 查找发布按钮
            publish_selectors = [
                '#done-button',
                'button[aria-label*="publish" i]',
                'ytcp-button[id="done-button"]',
                'button:contains("发布")',
                'button:contains("Publish")'
            ]
            
            for selector in publish_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.is_enabled():
                        # 滚动到按钮位置
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        await asyncio.sleep(1)
                        
                        # 点击发布
                        element.click()
                        logger.info("✅ 发布按钮点击成功")
                        
                        # 等待发布完成
                        await asyncio.sleep(10)
                        return True
                except:
                    continue
            
            logger.warning("⚠️ 未找到发布按钮")
            return False
            
        except Exception as e:
            logger.error(f"❌ 发布视频失败: {e}")
            return False
