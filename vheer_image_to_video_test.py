#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vheer.com 图生视频功能专门测试程序
专注于测试 Vheer.com 的 Image-to-Video 功能
"""

import asyncio
import os
import time
import base64
import logging
from typing import Optional, Dict, List
from pathlib import Path

# 设置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class VheerImageToVideoTester:
    """Vheer 图生视频测试器"""
    
    def __init__(self, headless: bool = False, output_dir: str = "temp/vheer_videos"):
        self.headless = headless
        self.output_dir = output_dir
        self.driver = None
        self.test_results = []
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"初始化 Vheer 图生视频测试器")
        logger.info(f"输出目录: {output_dir}")
        logger.info(f"无头模式: {headless}")
        
    def setup_browser(self) -> bool:
        """设置浏览器环境"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless")
                logger.info("启用无头模式")
            else:
                logger.info("启用有头模式 - 您可以观察整个过程")
            
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
            
            # 允许文件上传
            chrome_options.add_argument("--allow-file-access-from-files")
            chrome_options.add_argument("--disable-web-security")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # 执行反检测脚本
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("✅ 浏览器启动成功")
            return True
            
        except ImportError:
            logger.error("❌ Selenium 未安装，请运行: pip install selenium")
            return False
        except Exception as e:
            logger.error(f"❌ 浏览器启动失败: {e}")
            return False
            
    def wait_for_page_load(self, timeout: int = 30):
        """等待页面完全加载"""
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # 额外等待 JavaScript 执行
            time.sleep(3)
            logger.info("✅ 页面加载完成")
            
        except Exception as e:
            logger.warning(f"⚠️ 页面加载等待超时: {e}")
            
    def find_upload_element(self) -> Optional[object]:
        """智能查找图像上传元素"""
        from selenium.webdriver.common.by import By

        logger.info("🔍 开始查找上传元素...")

        # 首先打印页面信息用于调试
        try:
            page_title = self.driver.title
            current_url = self.driver.current_url
            logger.info(f"📄 当前页面: {page_title}")
            logger.info(f"🔗 当前URL: {current_url}")
        except:
            pass

        # 可能的上传元素选择器
        upload_selectors = [
            # 文件输入框 (最常见)
            "input[type='file']",
            "input[accept*='image']",
            "input[accept*='*']",

            # 上传区域
            ".upload-area",
            ".drop-zone",
            ".file-upload",
            ".image-upload",
            ".upload-zone",
            ".dropzone",

            # 通用选择器
            "[data-testid*='upload']",
            "[data-testid*='file']",
            "[class*='upload']",
            "[class*='file']",
            "[class*='drop']",
            "[id*='upload']",
            "[id*='file']"
        ]

        # 先查找所有可能的文件输入框
        logger.info("🔍 查找文件输入框...")
        file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        logger.info(f"📁 找到 {len(file_inputs)} 个文件输入框")

        for i, input_elem in enumerate(file_inputs):
            try:
                is_displayed = input_elem.is_displayed()
                is_enabled = input_elem.is_enabled()
                accept_attr = input_elem.get_attribute('accept')
                class_attr = input_elem.get_attribute('class')
                id_attr = input_elem.get_attribute('id')

                logger.info(f"  文件输入框 {i+1}: 显示={is_displayed}, 启用={is_enabled}")
                logger.info(f"    accept='{accept_attr}', class='{class_attr}', id='{id_attr}'")

                # 即使不显示也尝试使用
                if is_enabled:
                    logger.info(f"✅ 选择文件输入框 {i+1}")
                    return input_elem

            except Exception as e:
                logger.debug(f"检查文件输入框 {i+1} 失败: {e}")

        # 查找其他上传相关元素
        for selector in upload_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                logger.info(f"🔍 选择器 '{selector}': 找到 {len(elements)} 个元素")

                for i, element in enumerate(elements):
                    try:
                        is_displayed = element.is_displayed()
                        is_enabled = element.is_enabled()
                        tag_name = element.tag_name
                        text = element.text[:50] if element.text else ""

                        logger.info(f"  元素 {i+1}: {tag_name}, 显示={is_displayed}, 启用={is_enabled}, 文本='{text}'")

                        if is_displayed and is_enabled:
                            logger.info(f"✅ 找到上传元素: {selector} (元素 {i+1})")
                            return element

                    except Exception as e:
                        logger.debug(f"检查元素 {i+1} 失败: {e}")

            except Exception as e:
                logger.debug(f"选择器 {selector} 查找失败: {e}")
                continue

        # 查找包含特定文本的按钮
        button_texts = ['Upload', 'Choose', 'Select', 'Browse', '上传', '选择', '浏览', 'Add Image', 'Select Image']

        for text in button_texts:
            try:
                xpath = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
                elements = self.driver.find_elements(By.XPATH, xpath)

                if elements:
                    logger.info(f"🔍 找到包含 '{text}' 的按钮: {len(elements)} 个")
                    for i, element in enumerate(elements):
                        try:
                            if element.is_displayed() and element.is_enabled():
                                logger.info(f"✅ 找到上传按钮: '{text}' (按钮 {i+1})")
                                return element
                        except:
                            continue

            except Exception as e:
                logger.debug(f"查找按钮文本 '{text}' 失败: {e}")

        # 最后尝试查找所有按钮，看是否有相关的
        try:
            all_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button")
            logger.info(f"🔍 页面总共有 {len(all_buttons)} 个按钮")

            for i, button in enumerate(all_buttons[:10]):  # 只检查前10个
                try:
                    text = button.text.lower()
                    class_attr = button.get_attribute('class') or ""
                    id_attr = button.get_attribute('id') or ""

                    if any(keyword in text for keyword in ['upload', 'choose', 'select', 'file', 'image']):
                        logger.info(f"🎯 可能的上传按钮 {i+1}: '{button.text}', class='{class_attr}', id='{id_attr}'")
                        if button.is_displayed() and button.is_enabled():
                            logger.info(f"✅ 选择可能的上传按钮 {i+1}")
                            return button

                except:
                    continue

        except Exception as e:
            logger.debug(f"查找所有按钮失败: {e}")

        logger.warning("⚠️ 未找到上传元素")

        # 打印页面源码的一部分用于调试
        try:
            page_source = self.driver.page_source
            if 'upload' in page_source.lower() or 'file' in page_source.lower():
                logger.info("📄 页面包含 'upload' 或 'file' 关键词")
            else:
                logger.warning("📄 页面不包含 'upload' 或 'file' 关键词")
        except:
            pass

        return None
        
    def find_generate_button(self) -> Optional[object]:
        """智能查找生成按钮"""
        from selenium.webdriver.common.by import By
        
        # 文本匹配模式
        text_patterns = [
            "Generate", "Create", "Start", "Convert", "Make Video",
            "生成", "创建", "开始", "转换", "制作视频"
        ]
        
        for pattern in text_patterns:
            try:
                xpath = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern.lower()}')]"
                elements = self.driver.find_elements(By.XPATH, xpath)
                
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        logger.info(f"✅ 找到生成按钮 (文本): {pattern}")
                        return element
                        
            except Exception as e:
                logger.debug(f"文本模式 {pattern} 查找失败: {e}")
                
        # 选择器匹配
        button_selectors = [
            "button[type='submit']",
            ".generate-btn", ".create-btn", ".start-btn",
            ".btn-primary", ".btn-generate", ".btn-create",
            "button:last-of-type",
            "button"
        ]
        
        for selector in button_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        text = element.text.lower()
                        if any(keyword in text for keyword in ['generate', 'create', 'start', '生成', '创建']):
                            logger.info(f"✅ 找到生成按钮 (选择器): {selector}")
                            return element
                            
            except Exception as e:
                logger.debug(f"选择器 {selector} 查找失败: {e}")
                
        logger.warning("⚠️ 未找到生成按钮")
        return None
        
    def upload_image(self, image_path: str) -> bool:
        """上传图像文件"""
        try:
            logger.info(f"📤 开始上传图像: {image_path}")
            
            # 检查文件是否存在
            if not os.path.exists(image_path):
                logger.error(f"❌ 图像文件不存在: {image_path}")
                return False
                
            # 查找上传元素
            upload_element = self.find_upload_element()
            if not upload_element:
                logger.error("❌ 未找到上传元素")
                return False
                
            # 获取绝对路径
            abs_path = os.path.abspath(image_path)
            logger.info(f"📁 使用绝对路径: {abs_path}")
            
            # 尝试不同的上传方法
            try:
                # 方法1: 直接发送文件路径到input元素
                if upload_element.tag_name == "input":
                    upload_element.send_keys(abs_path)
                    logger.info("✅ 方法1: 直接上传成功")
                    return True
                else:
                    # 方法2: 点击按钮然后查找input元素
                    upload_element.click()
                    time.sleep(1)
                    
                    # 查找隐藏的input元素
                    from selenium.webdriver.common.by import By
                    file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    
                    for file_input in file_inputs:
                        try:
                            file_input.send_keys(abs_path)
                            logger.info("✅ 方法2: 点击后上传成功")
                            return True
                        except:
                            continue
                            
            except Exception as e:
                logger.warning(f"⚠️ 标准上传方法失败: {e}")
                
            # 方法3: 使用JavaScript上传
            try:
                logger.info("🔄 尝试JavaScript上传方法...")
                
                # 读取文件内容
                with open(abs_path, 'rb') as f:
                    file_content = f.read()
                    
                # 转换为base64
                file_base64 = base64.b64encode(file_content).decode('utf-8')
                file_name = os.path.basename(abs_path)
                
                # 使用JavaScript创建文件并触发上传
                script = f"""
                const dataTransfer = new DataTransfer();
                const file = new File([Uint8Array.from(atob('{file_base64}'), c => c.charCodeAt(0))], '{file_name}', {{type: 'image/jpeg'}});
                dataTransfer.items.add(file);
                
                const fileInput = document.querySelector('input[type="file"]');
                if (fileInput) {{
                    fileInput.files = dataTransfer.files;
                    fileInput.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return true;
                }}
                return false;
                """
                
                result = self.driver.execute_script(script)
                if result:
                    logger.info("✅ 方法3: JavaScript上传成功")
                    return True
                    
            except Exception as e:
                logger.warning(f"⚠️ JavaScript上传失败: {e}")
                
            logger.error("❌ 所有上传方法都失败了")
            return False
            
        except Exception as e:
            logger.error(f"❌ 上传图像失败: {e}")
            return False
            
    def wait_for_video_generation(self, max_wait: int = 300) -> Optional[str]:
        """等待视频生成完成并获取下载链接"""
        from selenium.webdriver.common.by import By
        
        logger.info(f"⏳ 等待视频生成完成 (最多等待 {max_wait} 秒)...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # 查找生成的视频元素
                video_selectors = [
                    "video",
                    "video[src]",
                    ".video-result video",
                    ".generated-video video",
                    ".output-video video",
                    "[data-testid*='video']"
                ]
                
                for selector in video_selectors:
                    try:
                        videos = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for video in videos:
                            if video.is_displayed():
                                src = video.get_attribute('src')
                                if src and src != "":
                                    logger.info(f"✅ 发现生成的视频: {src[:100]}...")
                                    return src
                    except:
                        continue
                        
                # 查找下载链接
                download_selectors = [
                    "a[download]",
                    "a[href*='.mp4']",
                    "a[href*='.webm']",
                    "a[href*='download']",
                    "button:contains('Download')",
                    "button:contains('下载')",
                    ".download-btn",
                    ".download-link"
                ]
                
                for selector in download_selectors:
                    try:
                        if ":contains" in selector:
                            text = selector.split(":contains('")[1].split("')")[0]
                            xpath = f"//button[contains(text(), '{text}')]"
                            elements = self.driver.find_elements(By.XPATH, xpath)
                        else:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                        for element in elements:
                            if element.is_displayed():
                                href = element.get_attribute('href')
                                if href:
                                    logger.info(f"✅ 发现下载链接: {href[:100]}...")
                                    return href
                    except:
                        continue
                        
                # 检查是否还在生成中
                loading_selectors = [
                    ".loading", ".spinner", ".progress",
                    "[class*='loading']", "[class*='spinner']", "[class*='progress']",
                    "text():contains('Generating')", "text():contains('Processing')",
                    "text():contains('生成中')", "text():contains('处理中')"
                ]
                
                still_loading = False
                for selector in loading_selectors:
                    try:
                        if "text():" in selector:
                            text = selector.split("text():contains('")[1].split("')")[0]
                            xpath = f"//*[contains(text(), '{text}')]"
                            elements = self.driver.find_elements(By.XPATH, xpath)
                        else:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                        if elements:
                            still_loading = True
                            break
                    except:
                        continue
                        
                if still_loading:
                    elapsed = int(time.time() - start_time)
                    logger.info(f"🔄 视频生成中... ({elapsed}s)")
                    time.sleep(5)
                else:
                    # 没有加载指示器，可能已完成但我们没找到视频
                    time.sleep(2)
                    
            except Exception as e:
                logger.debug(f"等待视频生成时出错: {e}")
                time.sleep(2)
                
        logger.warning(f"⚠️ 等待视频生成超时 ({max_wait}s)")
        return None

    def download_video(self, video_url: str, filename: str = None) -> Optional[str]:
        """下载生成的视频"""
        try:
            import requests

            if not filename:
                timestamp = int(time.time())
                filename = f"vheer_video_{timestamp}.mp4"

            filepath = os.path.join(self.output_dir, filename)

            logger.info(f"📥 开始下载视频: {filename}")

            if video_url.startswith('blob:'):
                # 处理 Blob URL - 需要在浏览器中执行 JavaScript
                script = f"""
                return new Promise((resolve) => {{
                    fetch('{video_url}')
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
                if data_url and data_url.startswith('data:'):
                    # 处理 data URL
                    header, data = data_url.split(',', 1)
                    video_data = base64.b64decode(data)

                    with open(filepath, 'wb') as f:
                        f.write(video_data)

                    logger.info(f"✅ Blob视频下载成功: {filepath}")
                    return filepath

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

    def test_image_to_video(self, image_path: str, test_name: str = "default") -> Dict:
        """测试图生视频的完整流程"""
        test_result = {
            'test_name': test_name,
            'image_path': image_path,
            'start_time': time.time(),
            'success': False,
            'video_path': None,
            'error_message': None,
            'steps_completed': []
        }

        try:
            logger.info(f"🚀 开始测试: {test_name}")
            logger.info(f"📷 输入图像: {image_path}")

            # 步骤1: 访问页面
            logger.info("📖 步骤1: 访问 Vheer 图生视频页面...")
            self.driver.get("https://vheer.com/app/image-to-video")
            self.wait_for_page_load()
            test_result['steps_completed'].append('page_loaded')

            # 步骤2: 上传图像
            logger.info("📤 步骤2: 上传图像文件...")
            if not self.upload_image(image_path):
                test_result['error_message'] = "图像上传失败"
                return test_result
            test_result['steps_completed'].append('image_uploaded')

            # 等待上传处理
            time.sleep(3)

            # 步骤3: 查找并点击生成按钮
            logger.info("🎬 步骤3: 启动视频生成...")
            generate_button = self.find_generate_button()
            if not generate_button:
                test_result['error_message'] = "未找到生成按钮"
                return test_result

            # 滚动到按钮位置并点击
            self.driver.execute_script("arguments[0].scrollIntoView();", generate_button)
            time.sleep(1)

            try:
                generate_button.click()
            except Exception as e:
                logger.warning(f"⚠️ 普通点击失败，尝试JavaScript点击: {e}")
                self.driver.execute_script("arguments[0].click();", generate_button)

            test_result['steps_completed'].append('generation_started')

            # 步骤4: 等待视频生成
            logger.info("⏳ 步骤4: 等待视频生成完成...")
            video_url = self.wait_for_video_generation(max_wait=300)  # 5分钟超时

            if not video_url:
                test_result['error_message'] = "视频生成超时或失败"
                return test_result

            test_result['steps_completed'].append('video_generated')

            # 步骤5: 下载视频
            logger.info("📥 步骤5: 下载生成的视频...")
            video_filename = f"{test_name}_{int(time.time())}.mp4"
            video_path = self.download_video(video_url, video_filename)

            if not video_path:
                test_result['error_message'] = "视频下载失败"
                return test_result

            test_result['video_path'] = video_path
            test_result['steps_completed'].append('video_downloaded')
            test_result['success'] = True

            # 验证视频文件
            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                file_size = os.path.getsize(video_path)
                logger.info(f"✅ 视频文件验证成功: {video_path} ({file_size} bytes)")
            else:
                logger.warning("⚠️ 视频文件验证失败")

        except Exception as e:
            test_result['error_message'] = str(e)
            logger.error(f"❌ 测试过程中出错: {e}")

        finally:
            test_result['end_time'] = time.time()
            test_result['duration'] = test_result['end_time'] - test_result['start_time']

            # 记录测试结果
            self.test_results.append(test_result)

            # 打印测试总结
            self.print_test_summary(test_result)

        return test_result

    def print_test_summary(self, result: Dict):
        """打印测试总结"""
        logger.info("=" * 60)
        logger.info(f"📊 测试总结: {result['test_name']}")
        logger.info(f"📷 输入图像: {result['image_path']}")
        logger.info(f"⏱️ 测试时长: {result['duration']:.1f} 秒")
        logger.info(f"✅ 成功状态: {'成功' if result['success'] else '失败'}")

        if result['success']:
            logger.info(f"🎬 输出视频: {result['video_path']}")
        else:
            logger.info(f"❌ 错误信息: {result['error_message']}")

        logger.info(f"📋 完成步骤: {', '.join(result['steps_completed'])}")
        logger.info("=" * 60)

    def create_test_image(self, filename: str = "test_image.jpg") -> str:
        """创建一个测试图像"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import random

            # 创建一个简单的测试图像
            width, height = 512, 512
            image = Image.new('RGB', (width, height), color=(random.randint(100, 255), random.randint(100, 255), random.randint(100, 255)))

            draw = ImageDraw.Draw(image)

            # 添加一些图形
            for _ in range(5):
                x1, y1 = random.randint(0, width//2), random.randint(0, height//2)
                x2, y2 = random.randint(width//2, width), random.randint(height//2, height)
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                draw.rectangle([x1, y1, x2, y2], fill=color)

            # 添加文本
            try:
                draw.text((width//4, height//2), "Test Image", fill=(255, 255, 255))
            except:
                pass  # 如果没有字体也没关系

            # 保存图像
            filepath = os.path.join(self.output_dir, filename)
            image.save(filepath, 'JPEG')

            logger.info(f"✅ 创建测试图像: {filepath}")
            return filepath

        except ImportError:
            logger.warning("⚠️ PIL 未安装，无法创建测试图像")
            logger.info("请安装: pip install Pillow")
            return None
        except Exception as e:
            logger.error(f"❌ 创建测试图像失败: {e}")
            return None

    def cleanup(self):
        """清理资源"""
        if self.driver:
            self.driver.quit()
            logger.info("🧹 浏览器已关闭")

def main():
    """主测试函数"""
    print("🎬 Vheer.com 图生视频功能专门测试程序")
    print("=" * 60)

    # 创建测试器实例
    tester = VheerImageToVideoTester(headless=False)  # 设置为False以观察过程

    try:
        # 设置浏览器
        if not tester.setup_browser():
            logger.error("❌ 浏览器设置失败，退出程序")
            return

        # 准备测试图像
        test_images = []

        # 检查是否有现有的测试图像
        sample_images = [
            "test_image.jpg",
            "sample.jpg",
            "test.png",
            "image.jpg"
        ]

        for img_name in sample_images:
            if os.path.exists(img_name):
                test_images.append(img_name)
                logger.info(f"📷 发现现有图像: {img_name}")

        # 如果没有现有图像，创建一个测试图像
        if not test_images:
            logger.info("📷 未找到现有图像，创建测试图像...")
            test_image = tester.create_test_image()
            if test_image:
                test_images.append(test_image)

        if not test_images:
            logger.error("❌ 没有可用的测试图像")
            return

        # 执行测试
        logger.info(f"🚀 开始测试，共 {len(test_images)} 张图像")

        for i, image_path in enumerate(test_images, 1):
            test_name = f"test_{i}_{Path(image_path).stem}"
            logger.info(f"\n🎯 执行测试 {i}/{len(test_images)}: {test_name}")

            result = tester.test_image_to_video(image_path, test_name)

            if result['success']:
                logger.info(f"✅ 测试 {i} 成功完成")
            else:
                logger.error(f"❌ 测试 {i} 失败: {result['error_message']}")

            # 测试间隔
            if i < len(test_images):
                logger.info("⏸️ 等待 10 秒后进行下一个测试...")
                time.sleep(10)

        # 打印最终总结
        print("\n" + "=" * 60)
        print("📊 最终测试总结")
        print("=" * 60)

        total_tests = len(tester.test_results)
        successful_tests = sum(1 for r in tester.test_results if r['success'])

        print(f"总测试数: {total_tests}")
        print(f"成功测试: {successful_tests}")
        print(f"失败测试: {total_tests - successful_tests}")
        print(f"成功率: {successful_tests/total_tests*100:.1f}%" if total_tests > 0 else "0%")

        if successful_tests > 0:
            print(f"\n✅ 成功生成的视频:")
            for result in tester.test_results:
                if result['success']:
                    print(f"  - {result['video_path']}")

        print("\n🎉 测试完成！")

    except KeyboardInterrupt:
        logger.info("\n⏹️ 用户中断测试")
    except Exception as e:
        logger.error(f"❌ 测试程序出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()
