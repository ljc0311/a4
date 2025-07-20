# -*- coding: utf-8 -*-
"""
Vheer.com 图生视频引擎
基于浏览器自动化技术实现的图像到视频生成引擎
"""

import os
import time
import asyncio
import base64
import logging
from typing import Optional, Callable, Dict, List
from pathlib import Path

from ..video_engine_base import VideoGenerationEngine, VideoEngineType, VideoEngineStatus
from ..video_engine_base import VideoGenerationConfig, VideoGenerationResult, VideoEngineInfo
from src.utils.logger import logger


class VheerVideoEngine(VideoGenerationEngine):
    """Vheer.com 图生视频引擎"""
    
    def __init__(self, config: Dict = None):
        super().__init__(VideoEngineType.VHEER)
        self.config = config or {}
        self.driver = None
        self.output_dir = self.config.get('output_dir', 'output/videos/vheer')
        self.headless = self.config.get('headless', True)
        self.max_wait_time = self.config.get('max_wait_time', 300)  # 5分钟超时
        self.max_concurrent = self.config.get('max_concurrent', 1)  # 默认单并发
        self.current_tasks = 0
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"Vheer视频引擎初始化，输出目录: {self.output_dir}")
        
    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            # 检查依赖
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                logger.info("✅ Selenium依赖检查通过")
            except ImportError as e:
                logger.error(f"❌ Selenium依赖缺失: {e}")
                logger.error("请安装: pip install selenium")
                self.status = VideoEngineStatus.ERROR
                self.last_error = "Selenium依赖缺失"
                return False
                
            # 检查ChromeDriver
            if not self._check_chromedriver():
                logger.error("❌ ChromeDriver不可用")
                self.status = VideoEngineStatus.ERROR
                self.last_error = "ChromeDriver不可用"
                return False
                
            # 测试浏览器启动
            if not await self._test_browser_startup():
                logger.error("❌ 浏览器启动测试失败")
                self.status = VideoEngineStatus.ERROR
                self.last_error = "浏览器启动失败"
                return False
                
            self.status = VideoEngineStatus.IDLE
            logger.info("✅ Vheer视频引擎初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ Vheer视频引擎初始化失败: {e}")
            self.status = VideoEngineStatus.ERROR
            self.last_error = str(e)
            return False
            
    def _check_chromedriver(self) -> bool:
        """检查ChromeDriver是否可用"""
        try:
            # 检查当前目录
            if os.path.exists("chromedriver.exe"):
                return True
                
            # 检查PATH中的chromedriver
            import shutil
            if shutil.which("chromedriver"):
                return True
                
            logger.warning("⚠️ 未找到ChromeDriver，请确保已安装")
            return False
            
        except Exception as e:
            logger.error(f"检查ChromeDriver失败: {e}")
            return False
            
    async def _test_browser_startup(self) -> bool:
        """测试浏览器启动"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                driver.get("https://www.google.com")
                title = driver.title
                logger.info(f"✅ 浏览器测试成功，页面标题: {title}")
                return True
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"浏览器启动测试失败: {e}")
            return False
            
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                # 测试访问Vheer网站
                driver.get("https://vheer.com/app/image-to-video")
                
                # 等待页面加载
                await asyncio.sleep(3)
                
                current_url = driver.current_url
                page_title = driver.title
                
                logger.info(f"✅ Vheer网站连接测试成功")
                logger.info(f"URL: {current_url}")
                logger.info(f"标题: {page_title}")
                
                return True
                
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"Vheer连接测试失败: {e}")
            return False
            
    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        return ["vheer-image-to-video"]

    def get_engine_info(self) -> VideoEngineInfo:
        """获取引擎信息"""
        return VideoEngineInfo(
            name="Vheer.com",
            version="1.0.0",
            description="Vheer.com免费图生视频服务，基于浏览器自动化技术",
            is_free=True,
            supports_image_to_video=True,
            supports_text_to_video=False,
            max_duration=10.0,
            supported_resolutions=[(512, 512), (1024, 1024)],
            supported_fps=[24, 30],
            cost_per_second=0.0,
            rate_limit=60,  # 估算每分钟60次请求
            max_concurrent_tasks=self.max_concurrent
        )

    async def _translate_prompt_to_english(self, prompt: str) -> str:
        """将提示词翻译为英文"""
        if not prompt:
            return ""

        try:
            # 检查是否已经是英文
            if prompt.isascii() and all(ord(c) < 128 for c in prompt):
                logger.info("提示词已经是英文，无需翻译")
                return prompt

            # 使用程序中已有的翻译功能
            try:
                from src.services.service_manager import ServiceManager
                service_manager = ServiceManager()
                llm_service = service_manager.get_service('llm_service')
            except ImportError:
                # 如果服务管理器不可用，尝试直接使用翻译服务
                try:
                    from src.services.translation_service import TranslationService
                    translation_service = TranslationService()
                    translated = await translation_service.translate_text(prompt, target_language='en')
                    if translated and translated.strip():
                        logger.info(f"提示词翻译: {prompt} -> {translated.strip()}")
                        return translated.strip()
                except ImportError:
                    logger.warning("翻译服务不可用，使用原文")
                    return prompt
                except Exception as e:
                    logger.warning(f"翻译服务调用失败: {e}，使用原文")
                    return prompt

                logger.warning("服务管理器不可用，使用原文")
                return prompt

            if llm_service:
                translation_prompt = f"请将以下中文文本翻译为英文，只返回翻译结果，不要添加任何解释：\n{prompt}"

                translated = await llm_service.generate_text_async(
                    prompt=translation_prompt,
                    max_tokens=200,
                    temperature=0.1
                )

                if translated and translated.strip():
                    logger.info(f"提示词翻译: {prompt} -> {translated.strip()}")
                    return translated.strip()

            logger.warning("无法翻译提示词，使用原文")
            return prompt

        except Exception as e:
            logger.warning(f"提示词翻译失败: {e}，使用原文")
            return prompt

    async def generate_video(self, config: VideoGenerationConfig,
                           progress_callback: Optional[Callable] = None,
                           project_manager=None, current_project_name=None) -> VideoGenerationResult:
        """生成视频"""
        
        # 检查并发限制
        if self.current_tasks >= self.max_concurrent:
            return VideoGenerationResult(
                success=False,
                error_message=f"超过最大并发限制 ({self.max_concurrent})"
            )
            
        self.current_tasks += 1
        self.status = VideoEngineStatus.BUSY
        
        try:
            # 🔧 修复：更新配置参数
            if hasattr(config, 'headless'):
                self.headless = config.headless
                logger.info(f"🔧 更新无头模式设置: {self.headless}")
            if hasattr(config, 'timeout'):
                self.max_wait_time = config.timeout
                logger.info(f"🔧 更新超时时间: {self.max_wait_time}s")

            # 验证输入
            if not config.input_image_path or not os.path.exists(config.input_image_path):
                return VideoGenerationResult(
                    success=False,
                    error_message=f"输入图像不存在: {config.input_image_path}"
                )

            logger.info(f"🎬 开始Vheer视频生成: {config.input_image_path}")
            logger.info(f"🔧 当前设置: 无头模式={self.headless}, 超时={self.max_wait_time}s")

            # 翻译提示词为英文
            english_prompt = ""
            if config.input_prompt:
                if progress_callback:
                    progress_callback("翻译提示词...")
                english_prompt = await self._translate_prompt_to_english(config.input_prompt)

            if progress_callback:
                progress_callback("初始化浏览器...")
                
            # 设置浏览器
            driver = await self._setup_browser()
            if not driver:
                return VideoGenerationResult(
                    success=False,
                    error_message="浏览器设置失败"
                )
                
            try:
                # 执行视频生成流程
                result = await self._execute_video_generation(
                    driver, config, progress_callback
                )
                
                if result.success:
                    self.success_count += 1
                    logger.info(f"✅ Vheer视频生成成功: {result.video_path}")
                else:
                    self.error_count += 1
                    logger.error(f"❌ Vheer视频生成失败: {result.error_message}")
                    
                return result
                
            finally:
                driver.quit()
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ Vheer视频生成异常: {e}")
            return VideoGenerationResult(
                success=False,
                error_message=str(e)
            )
        finally:
            self.current_tasks -= 1
            if self.current_tasks == 0:
                self.status = VideoEngineStatus.IDLE
                
    async def _setup_browser(self):
        """设置浏览器"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
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
            
            driver = webdriver.Chrome(options=chrome_options)
            
            # 执行反检测脚本
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
            
        except Exception as e:
            logger.error(f"浏览器设置失败: {e}")
            return None

    async def _execute_video_generation(self, driver, config: VideoGenerationConfig,
                                      progress_callback: Optional[Callable] = None) -> VideoGenerationResult:
        """执行视频生成流程"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # 步骤1: 访问页面
            if progress_callback:
                progress_callback("访问Vheer图生视频页面...")

            logger.info("📖 访问Vheer图生视频页面...")
            driver.get("https://vheer.com/app/image-to-video")

            # 等待页面加载
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            await asyncio.sleep(5)  # 额外等待JavaScript加载

            # 检查页面是否正确加载
            try:
                page_title = driver.title
                logger.info(f"页面标题: {page_title}")

                # 检查是否有上传按钮或相关元素
                upload_elements = driver.find_elements(By.CSS_SELECTOR, "input[type='file'], [class*='upload'], [class*='drop']")
                logger.info(f"找到 {len(upload_elements)} 个上传相关元素")

            except Exception as e:
                logger.warning(f"页面检查失败: {e}")

            # 步骤2: 上传图像
            if progress_callback:
                progress_callback("上传图像文件...")

            logger.info("📤 上传图像文件...")
            if not await self._upload_image(driver, config.input_image_path):
                return VideoGenerationResult(
                    success=False,
                    error_message="图像上传失败"
                )

            # 等待上传处理和Generate按钮出现
            if progress_callback:
                progress_callback("等待Generate按钮出现...")

            logger.info("⏳ 等待Generate按钮出现...")
            await asyncio.sleep(5)  # 给更多时间让按钮出现

            # 步骤3: 点击Generate按钮（右侧紫色按钮）
            if progress_callback:
                progress_callback("点击Generate按钮...")

            logger.info("🎬 点击Generate按钮...")
            if not await self._click_generate_button(driver):
                return VideoGenerationResult(
                    success=False,
                    error_message="Generate按钮点击失败"
                )

            # 步骤4: 等待视频生成完成并获取下载链接（约1分钟）
            if progress_callback:
                progress_callback("等待视频生成完成（约1分钟）...")

            logger.info("⏳ 等待视频生成完成并获取下载链接（约1分钟）...")
            video_url = await self._wait_for_video_and_download(driver, progress_callback)

            if not video_url:
                return VideoGenerationResult(
                    success=False,
                    error_message="视频生成超时或失败"
                )

            # 步骤5: 保存视频文件
            if progress_callback:
                progress_callback("保存生成的视频...")

            logger.info("📥 保存生成的视频...")
            video_path = await self._download_video(driver, video_url, config)

            if not video_path:
                return VideoGenerationResult(
                    success=False,
                    error_message="视频下载失败"
                )

            # 验证视频文件
            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                file_size = os.path.getsize(video_path)
                logger.info(f"✅ 视频生成成功: {video_path} ({file_size} bytes)")

                # 🔧 自动去除左上角水印区域
                cleaned_video_path = await self._remove_watermark(video_path)
                if cleaned_video_path and os.path.exists(cleaned_video_path):
                    final_video_path = cleaned_video_path
                    final_file_size = os.path.getsize(cleaned_video_path)
                    logger.info(f"✅ 水印处理完成: {final_video_path} ({final_file_size} bytes)")
                else:
                    final_video_path = video_path
                    final_file_size = file_size
                    logger.warning("⚠️ 水印处理失败，使用原始视频")

                return VideoGenerationResult(
                    success=True,
                    video_path=final_video_path,
                    duration=config.duration,
                    resolution=f"{config.width}x{config.height}",
                    file_size=final_file_size,
                    engine_type=self.engine_type.value
                )
            else:
                return VideoGenerationResult(
                    success=False,
                    error_message="生成的视频文件无效"
                )

        except Exception as e:
            logger.error(f"视频生成流程执行失败: {e}")
            return VideoGenerationResult(
                success=False,
                error_message=str(e)
            )

    async def _upload_image(self, driver, image_path: str) -> bool:
        """上传图像文件"""
        try:
            from selenium.webdriver.common.by import By

            # 查找文件输入框
            file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")

            if not file_inputs:
                logger.error("❌ 未找到文件输入框")
                return False

            # 使用第一个可用的文件输入框
            for file_input in file_inputs:
                try:
                    if file_input.is_enabled():
                        abs_path = os.path.abspath(image_path)
                        file_input.send_keys(abs_path)
                        logger.info("✅ 图像上传成功")
                        await asyncio.sleep(3)  # 等待上传处理
                        return True
                except Exception as e:
                    logger.debug(f"文件输入框上传失败: {e}")
                    continue

            logger.error("❌ 所有文件输入框都不可用")
            return False

        except Exception as e:
            logger.error(f"上传图像失败: {e}")
            return False

    async def _click_generate_button(self, driver) -> bool:
        """点击右侧的Generate按钮（紫色按钮）"""
        try:
            from selenium.webdriver.common.by import By

            # 多次尝试查找按钮，因为按钮可能需要时间加载
            max_attempts = 3
            for attempt in range(max_attempts):
                logger.info(f"🔍 尝试查找Generate按钮 (第{attempt + 1}次)...")

                # 方法1: 查找包含"Generate"文本的按钮
                button_texts = ['Generate', '生成', 'generate']
                for text in button_texts:
                    try:
                        # 使用XPath查找包含指定文本的按钮
                        xpath = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
                        buttons = driver.find_elements(By.XPATH, xpath)

                        for button in buttons:
                            if button.is_displayed() and button.is_enabled():
                                logger.info(f"✅ 找到Generate按钮: '{button.text}'")
                                # 滚动到按钮位置
                                driver.execute_script("arguments[0].scrollIntoView();", button)
                                await asyncio.sleep(1)

                                try:
                                    button.click()
                                    logger.info(f"✅ Generate按钮点击成功: {text}")
                                    return True
                                except:
                                    # 如果普通点击失败，使用JavaScript点击
                                    driver.execute_script("arguments[0].click();", button)
                                    logger.info(f"✅ Generate按钮JavaScript点击成功: {text}")
                                    return True

                    except Exception as e:
                        logger.debug(f"查找按钮 '{text}' 失败: {e}")
                        continue

                # 方法2: 查找所有按钮并检查文本内容
                try:
                    all_buttons = driver.find_elements(By.CSS_SELECTOR, "button")
                    logger.info(f"🔍 页面中共有 {len(all_buttons)} 个按钮")

                    for i, button in enumerate(all_buttons):
                        try:
                            if button.is_displayed() and button.is_enabled():
                                button_text = button.text.strip().lower()
                                button_classes = button.get_attribute('class') or ''

                                # 检查按钮文本或类名是否包含generate相关关键词
                                if (button_text and ('generate' in button_text or '生成' in button_text)) or \
                                   ('generate' in button_classes.lower()):
                                    logger.info(f"✅ 找到可能的Generate按钮 {i+1}: '{button.text}' class='{button_classes}'")

                                    # 滚动到按钮位置
                                    driver.execute_script("arguments[0].scrollIntoView();", button)
                                    await asyncio.sleep(1)

                                    try:
                                        button.click()
                                        logger.info(f"✅ Generate按钮点击成功: {button.text}")
                                        return True
                                    except:
                                        driver.execute_script("arguments[0].click();", button)
                                        logger.info(f"✅ Generate按钮JavaScript点击成功: {button.text}")
                                        return True
                        except:
                            continue

                except Exception as e:
                    logger.debug(f"遍历所有按钮失败: {e}")

                # 方法3: 查找特定的CSS选择器
                try:
                    selectors = [
                        "button[class*='generate']",
                        "button[class*='primary']",
                        "button[class*='submit']",
                        "button[type='submit']",
                        ".btn-primary",
                        "button.btn",
                        "[role='button']"
                    ]

                    for selector in selectors:
                        try:
                            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                            for button in buttons:
                                if button.is_displayed() and button.is_enabled():
                                    button_text = button.text.strip()
                                    if button_text:  # 只要有文本就尝试点击
                                        logger.info(f"✅ 尝试点击按钮: '{button_text}' (选择器: {selector})")

                                        try:
                                            button.click()
                                            logger.info(f"✅ 按钮点击成功: {button_text}")
                                            return True
                                        except:
                                            driver.execute_script("arguments[0].click();", button)
                                            logger.info(f"✅ 按钮JavaScript点击成功: {button_text}")
                                            return True
                        except Exception as e:
                            logger.debug(f"选择器 {selector} 失败: {e}")
                            continue

                except Exception as e:
                    logger.debug(f"CSS选择器查找失败: {e}")

                # 如果这次尝试失败，等待一下再试
                if attempt < max_attempts - 1:
                    logger.info(f"⏳ 第{attempt + 1}次尝试失败，等待3秒后重试...")
                    await asyncio.sleep(3)

            logger.error("❌ 未找到Generate按钮")
            return False

        except Exception as e:
            logger.error(f"点击Generate按钮失败: {e}")
            return False

    async def _wait_for_video_and_download(self, driver, progress_callback: Optional[Callable] = None) -> Optional[str]:
        """等待视频生成完成并下载（约1分钟）"""
        try:
            from selenium.webdriver.common.by import By

            start_time = time.time()
            logger.info("⏳ 开始等待视频生成完成...")

            check_count = 0
            while time.time() - start_time < self.max_wait_time:
                try:
                    check_count += 1
                    elapsed = time.time() - start_time

                    # 每15秒输出一次进度
                    if check_count % 15 == 0:
                        logger.info(f"⏳ 等待视频生成中... ({elapsed:.0f}s/{self.max_wait_time}s)")
                        if progress_callback:
                            progress_callback(f"等待视频生成中... ({elapsed:.0f}s)")

                    # 首先检查是否有生成完成的视频（查找下载按钮）
                    download_button = await self._find_download_button(driver)
                    if download_button:
                        logger.info("✅ 发现下载按钮，视频生成完成！")

                        # 点击下载按钮
                        video_url = await self._click_download_button(driver, download_button)
                        if video_url:
                            return video_url

                        # 如果点击下载失败，尝试其他方法获取视频URL
                        logger.info("🔄 点击下载失败，尝试其他方法获取视频...")

                    # 检查是否有生成的视频元素
                    video_url = await self._check_generated_video(driver)
                    if video_url:
                        return video_url

                    await asyncio.sleep(2)

                except Exception as e:
                    logger.debug(f"检查视频生成状态时出错: {e}")
                    await asyncio.sleep(2)

            logger.warning(f"⚠️ 等待视频生成超时 ({self.max_wait_time}s)")
            return None

        except Exception as e:
            logger.error(f"等待视频生成失败: {e}")
            return None

    async def _find_download_button(self, driver):
        """查找视频上方的下载按钮"""
        try:
            from selenium.webdriver.common.by import By

            # 根据截图，下载按钮是视频上方的图标按钮
            download_selectors = [
                # 优先查找下载相关的按钮
                "button[title*='download']",
                "button[aria-label*='download']",
                "a[title*='download']",
                "a[aria-label*='download']",
                "[class*='download']",
                # 查找包含下载图标的按钮（通常是SVG图标）
                "button:has(svg)",
                "a:has(svg)",
                # 通用的图标按钮
                "button[class*='icon']",
                "a[class*='icon']",
                # 查找视频容器附近的按钮
                "video + button",
                "video ~ button",
                ".video-container button",
                ".video-wrapper button"
            ]

            for selector in download_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            # 检查按钮的位置是否在视频附近
                            return element
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue

            return None

        except Exception as e:
            logger.debug(f"查找下载按钮失败: {e}")
            return None

    async def _click_download_button(self, driver, download_button) -> Optional[str]:
        """点击下载按钮并获取视频URL"""
        try:
            # 滚动到按钮位置
            driver.execute_script("arguments[0].scrollIntoView();", download_button)
            await asyncio.sleep(1)

            # 监听网络请求以捕获下载链接
            # 这里我们先尝试点击，然后检查是否有新的视频URL出现

            try:
                download_button.click()
                logger.info("✅ 成功点击下载按钮")
            except:
                # 如果普通点击失败，使用JavaScript点击
                driver.execute_script("arguments[0].click();", download_button)
                logger.info("✅ JavaScript点击下载按钮成功")

            # 等待一下，让下载开始
            await asyncio.sleep(2)

            # 尝试获取下载的视频URL
            # 方法1: 检查是否有新的blob URL
            video_url = await self._check_generated_video(driver)
            if video_url:
                return video_url

            # 方法2: 检查下载链接
            download_links = driver.find_elements(By.CSS_SELECTOR, "a[download], a[href*='.mp4'], a[href*='.webm']")
            for link in download_links:
                if link.is_displayed():
                    href = link.get_attribute('href')
                    if href and ('.mp4' in href or '.webm' in href) and not self._is_demo_video(href):
                        logger.info(f"✅ 发现下载链接: {href[:100]}...")
                        return href

            return None

        except Exception as e:
            logger.error(f"点击下载按钮失败: {e}")
            return None

    async def _check_generated_video(self, driver) -> Optional[str]:
        """检查是否有生成的视频"""
        try:
            from selenium.webdriver.common.by import By

            # 查找video元素
            videos = driver.find_elements(By.CSS_SELECTOR, "video")

            for video in videos:
                if video.is_displayed():
                    src = video.get_attribute('src')
                    if src and src != "" and not self._is_demo_video(src):
                        logger.info(f"✅ 发现生成的视频: {src[:100]}...")
                        return src

            return None

        except Exception as e:
            logger.debug(f"检查生成视频失败: {e}")
            return None

    def _is_demo_video(self, url: str) -> bool:
        """检查是否为演示视频"""
        if not url:
            return True

        demo_patterns = [
            '/how/how.webm',
            '/demo/',
            '/example/',
            '/sample/',
            'placeholder',
            'demo.webm',
            'example.webm',
            'sample.webm'
        ]

        url_lower = url.lower()
        return any(pattern in url_lower for pattern in demo_patterns)

    async def _download_video(self, driver, video_url: str, config: VideoGenerationConfig) -> Optional[str]:
        """下载视频文件"""
        try:
            import requests

            # 生成输出文件名，根据URL确定格式
            timestamp = int(time.time())

            # 根据视频URL确定文件扩展名
            if '.webm' in video_url.lower():
                file_ext = '.webm'
            elif '.mp4' in video_url.lower():
                file_ext = '.mp4'
            elif '.mov' in video_url.lower():
                file_ext = '.mov'
            else:
                # 默认使用webm，因为Vheer主要提供webm格式
                file_ext = '.webm'

            filename = f"vheer_video_{timestamp}{file_ext}"
            filepath = os.path.join(self.output_dir, filename)

            logger.info(f"📥 开始下载视频: {filename}")

            if video_url.startswith('blob:'):
                # 🔧 改进：处理 Blob URL，直接获取视频数据
                script = f"""
                return new Promise((resolve) => {{
                    fetch('{video_url}')
                        .then(response => {{
                            if (!response.ok) {{
                                throw new Error('Network response was not ok: ' + response.status);
                            }}
                            return response.blob();
                        }})
                        .then(blob => {{
                            if (blob.size === 0) {{
                                throw new Error('Empty blob received');
                            }}
                            const reader = new FileReader();
                            reader.onloadend = () => {{
                                const result = reader.result;
                                if (result && result.startsWith('data:')) {{
                                    resolve(result);
                                }} else {{
                                    resolve(null);
                                }}
                            }};
                            reader.onerror = () => resolve(null);
                            reader.readAsDataURL(blob);
                        }})
                        .catch(error => {{
                            console.error('Blob fetch error:', error);
                            resolve(null);
                        }});
                }});
                """

                logger.info("🔄 正在通过JavaScript获取Blob视频数据...")
                try:
                    data_url = driver.execute_async_script(script)

                    if data_url and data_url.startswith('data:'):
                        header, data = data_url.split(',', 1)
                        video_data = base64.b64decode(data)

                        # 确保有足够的数据
                        if len(video_data) > 1000:  # 至少1KB
                            with open(filepath, 'wb') as f:
                                f.write(video_data)

                            logger.info(f"✅ Blob视频下载成功: {filepath} ({len(video_data)} bytes)")
                            return filepath
                        else:
                            logger.warning(f"⚠️ Blob数据太小，可能无效: {len(video_data)} bytes")
                    else:
                        logger.warning("⚠️ 无法获取有效的Blob数据")

                except Exception as e:
                    logger.error(f"❌ Blob处理失败: {e}")

                # 如果Blob处理失败，返回None让程序尝试其他方法
                return None

            elif video_url.startswith('data:'):
                # 处理 Base64 视频
                header, data = video_url.split(',', 1)
                video_data = base64.b64decode(data)

                with open(filepath, 'wb') as f:
                    f.write(video_data)

                logger.info(f"✅ Base64视频保存成功: {filepath}")
                return filepath

            else:
                # 处理普通 HTTP URL
                response = requests.get(video_url, timeout=60, stream=True)
                response.raise_for_status()

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                logger.info(f"✅ HTTP视频下载成功: {filepath}")
                return filepath

        except Exception as e:
            logger.error(f"❌ 下载视频失败: {e}")
            return None

    async def _remove_watermark(self, video_path: str) -> Optional[str]:
        """去除视频左上角的水印区域"""
        try:
            import subprocess
            from pathlib import Path

            # 检查FFmpeg是否可用
            try:
                subprocess.run(['ffmpeg', '-version'],
                             capture_output=True, timeout=5)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("⚠️ FFmpeg未安装，跳过水印处理")
                return None

            video_path = Path(video_path)
            cleaned_path = video_path.parent / f"{video_path.stem}_cleaned{video_path.suffix}"

            logger.info("🔄 正在去除视频水印...")

            # 使用FFmpeg裁剪左上角区域
            # 假设水印区域约占左侧25%宽度
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-vf', 'crop=3*iw/4:ih:iw/4:0',  # 裁剪掉左侧1/4，保留右侧3/4
                '-c:a', 'copy',  # 音频直接复制
                '-y',  # 覆盖输出文件
                str(cleaned_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode == 0 and cleaned_path.exists():
                # 删除原始文件，重命名清理后的文件
                try:
                    video_path.unlink()  # 删除原文件
                    cleaned_path.rename(video_path)  # 重命名为原文件名
                    logger.info("✅ 水印处理完成")
                    return str(video_path)
                except Exception as e:
                    logger.error(f"❌ 文件重命名失败: {e}")
                    return str(cleaned_path)
            else:
                logger.warning(f"⚠️ 水印处理失败: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ 水印处理异常: {e}")
            return None
