#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Selenium的YouTube Shorts发布器
参考MoneyPrinterPlus的实现，支持YouTube Shorts平台视频发布
"""

import time
import asyncio
from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from .selenium_publisher_base import SeleniumPublisherBase
from src.utils.logger import logger


class SeleniumYoutubePublisher(SeleniumPublisherBase):
    """基于Selenium的YouTube Shorts发布器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__('youtube', config)
        
    def _get_platform_url(self) -> str:
        """获取YouTube创作者中心URL"""
        return "https://studio.youtube.com/channel/UC/videos/upload"
        
    async def _check_login_status(self) -> bool:
        """检查YouTube登录状态"""
        try:
            # 等待页面加载完成
            await asyncio.sleep(3)
            
            # 检查页面URL
            current_url = self.driver.current_url
            logger.info(f"当前页面URL: {current_url}")
            
            # 如果在登录页面，返回False
            if any(keyword in current_url for keyword in ['accounts.google.com', 'signin']):
                logger.warning("检测到登录页面，需要用户登录")
                return False
                
            # 检查是否在YouTube Studio
            if 'studio.youtube.com' in current_url:
                # YouTube登录状态检查
                login_indicators = [
                    # 上传相关元素
                    '//input[@type="file"]',
                    '//div[contains(@class, "upload")]//input[@type="file"]',
                    
                    # 标题输入框
                    '//div[@id="textbox" and @contenteditable="true"]',
                    '//textarea[@id="description-textarea"]',
                    
                    # 发布按钮
                    '//ytcp-button[@id="done-button"]',
                    '//button[contains(text(), "Publish")]'
                ]

                # 使用更稳定的元素检查方法
                for selector in login_indicators:
                    element = self.find_element_safe(By.XPATH, selector, timeout=3)
                    if element:
                        logger.debug(f"找到登录指示器: {selector}")
                        return True
                        
            return False
            
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return False
            
    async def _publish_video_impl(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """YouTube Shorts视频发布实现"""
        try:
            # 检查是否为模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 模拟模式：模拟YouTube Shorts视频发布过程")
                
                # 模拟发布过程
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

                logger.info("✅ 模拟发布成功！")
                return {'success': True, 'message': '模拟发布成功'}

            # 确保在上传页面
            upload_url = "https://studio.youtube.com/channel/UC/videos/upload"
            if 'upload' not in self.driver.current_url:
                self.driver.get(upload_url)
                time.sleep(5)
                
            # 1. 上传视频文件
            video_path = video_info.get('video_path')
            if not video_path:
                return {'success': False, 'error': '视频路径不能为空'}
                
            logger.info(f"开始上传视频文件: {video_path}")
            
            # YouTube的文件上传选择器
            file_input_selectors = [
                '//input[@type="file"]',
                '//input[@accept="video/*"]',
                '//ytcp-upload-file-picker//input[@type="file"]'
            ]
            
            upload_success = False
            for selector in file_input_selectors:
                logger.info(f"尝试使用选择器上传: {selector}")
                if self.upload_file_safe(By.XPATH, selector, video_path, timeout=10):
                    upload_success = True
                    logger.info("✅ 视频文件上传成功")
                    break
                time.sleep(2)
            
            if not upload_success:
                return {'success': False, 'error': '视频上传失败 - 未找到有效的上传元素'}
                
            # 等待视频上传完成
            logger.info("等待视频上传完成...")
            upload_complete = self._wait_for_upload_complete(timeout=900)  # YouTube上传较慢，15分钟超时
            
            if not upload_complete:
                return {'success': False, 'error': '视频上传超时或失败'}
                
            # 2. 设置视频标题
            title = video_info.get('title', '')
            if title:
                logger.info(f"设置标题: {title}")
                title_selectors = [
                    '//div[@id="textbox" and @contenteditable="true"]',
                    '//ytcp-social-suggestions-textbox[@label="Title"]//div[@contenteditable="true"]'
                ]
                
                title_set = False
                for selector in title_selectors:
                    element = self.find_element_safe(By.XPATH, selector, timeout=5)
                    if element:
                        element.clear()
                        element.send_keys(title[:100])  # YouTube标题限制
                        title_set = True
                        break
                
                if not title_set:
                    logger.warning("标题设置失败")
                time.sleep(2)
                
            # 3. 设置视频描述
            description = video_info.get('description', '')
            if description:
                logger.info(f"设置描述: {description}")
                desc_selectors = [
                    '//div[@id="description-container"]//div[@contenteditable="true"]',
                    '//ytcp-social-suggestions-textbox[@label="Description"]//div[@contenteditable="true"]'
                ]
                
                for selector in desc_selectors:
                    element = self.find_element_safe(By.XPATH, selector, timeout=5)
                    if element:
                        element.clear()
                        # 添加#Shorts标签确保被识别为Shorts
                        shorts_description = f"{description}\n\n#Shorts"
                        element.send_keys(shorts_description[:5000])  # YouTube描述限制
                        break
                time.sleep(2)
                
            # 4. 设置标签
            tags = video_info.get('tags', [])
            if tags:
                logger.info(f"设置标签: {tags}")
                try:
                    # 点击显示更多选项
                    more_options_selector = '//ytcp-button[@id="toggle-button"]'
                    if self.click_element_safe(By.XPATH, more_options_selector):
                        time.sleep(2)
                        
                        # 设置标签
                        tags_selector = '//input[@aria-label="Tags"]'
                        element = self.find_element_safe(By.XPATH, tags_selector, timeout=5)
                        if element:
                            tag_text = ', '.join(tags[:10])  # YouTube标签限制
                            element.send_keys(tag_text)
                        time.sleep(2)
                except Exception as e:
                    logger.warning(f"设置标签失败: {e}")
                    
            # 5. 设置为Shorts（通过缩略图或其他方式）
            try:
                # YouTube会自动检测短视频并标记为Shorts
                # 这里可以添加额外的Shorts设置逻辑
                logger.info("YouTube将自动检测并标记为Shorts")
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Shorts设置失败: {e}")
                
            # 6. 设置可见性（默认公开）
            visibility = video_info.get('visibility', 'public')
            logger.info(f"设置可见性: {visibility}")
            try:
                # 点击可见性选项
                visibility_selector = '//ytcp-video-visibility-select'
                if self.click_element_safe(By.XPATH, visibility_selector):
                    time.sleep(2)
                    
                    # 选择可见性选项
                    visibility_options = {
                        'public': '//tp-yt-paper-radio-button[@name="PUBLIC"]',
                        'unlisted': '//tp-yt-paper-radio-button[@name="UNLISTED"]',
                        'private': '//tp-yt-paper-radio-button[@name="PRIVATE"]'
                    }
                    
                    option_selector = visibility_options.get(visibility, visibility_options['public'])
                    self.click_element_safe(By.XPATH, option_selector)
                    time.sleep(2)
            except Exception as e:
                logger.warning(f"设置可见性失败: {e}")
                
            # 7. 发布视频
            logger.info("开始发布视频...")
            time.sleep(3)
            
            # 智能检测并点击发布按钮
            publish_success = self._smart_find_publish_button()
            
            if publish_success:
                logger.info("发布按钮点击成功，等待发布完成...")
                time.sleep(10)  # YouTube发布需要较长时间
                
                # 处理可能的错误弹窗
                self._handle_error_dialogs()
                
                # 检查发布结果
                if self._check_publish_result():
                    logger.info("✅ 视频发布成功！")
                    return {'success': True, 'message': '视频发布成功'}
                else:
                    logger.info("✅ 视频已提交发布，请稍后查看发布状态")
                    return {'success': True, 'message': '视频已提交发布'}
            else:
                return {'success': False, 'error': '发布按钮点击失败'}
                
        except Exception as e:
            logger.error(f"YouTube Shorts视频发布失败: {e}")
            return {'success': False, 'error': str(e)}

    def _wait_for_upload_complete(self, timeout: int = 900) -> bool:
        """等待视频上传完成"""
        try:
            logger.info("等待YouTube视频上传完成...")
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # 检查上传进度指示器
                    progress_indicators = [
                        '//ytcp-video-upload-progress',
                        '//div[contains(@class, "progress")]',
                        '//div[contains(text(), "Uploading")]',
                        '//div[contains(text(), "Processing")]'
                    ]
                    
                    uploading = False
                    for selector in progress_indicators:
                        if self.find_element_safe(By.XPATH, selector, timeout=1):
                            uploading = True
                            break
                    
                    if not uploading:
                        # 检查完成指示器
                        completion_indicators = [
                            '//div[@id="textbox" and @contenteditable="true"]',  # 标题输入框
                            '//ytcp-button[@id="done-button"]',  # 完成按钮
                            '//button[contains(text(), "Publish")]'  # 发布按钮
                        ]
                        
                        for selector in completion_indicators:
                            element = self.find_element_safe(By.XPATH, selector, timeout=2)
                            if element and element.is_enabled():
                                logger.info("✅ 检测到上传完成")
                                return True
                    
                    time.sleep(10)  # YouTube上传检查间隔较长
                    
                except Exception as e:
                    logger.debug(f"等待上传完成时出现异常: {e}")
                    time.sleep(5)
            
            logger.warning("等待上传完成超时")
            return False
            
        except Exception as e:
            logger.error(f"等待上传完成失败: {e}")
            return False

    def _smart_find_publish_button(self) -> bool:
        """智能查找并点击发布按钮"""
        try:
            logger.info("开始智能检测YouTube发布按钮...")
            
            # YouTube发布按钮选择器
            publish_selectors = [
                '//ytcp-button[@id="done-button"]',
                '//button[contains(text(), "Publish")]',
                '//ytcp-button[contains(text(), "Publish")]',
                '//button[@aria-label="Publish"]'
            ]
            
            for i, selector in enumerate(publish_selectors):
                logger.info(f"尝试发布按钮选择器 {i+1}/{len(publish_selectors)}: {selector}")
                element = self.find_element_safe(By.XPATH, selector, timeout=5)
                if element and element.is_enabled() and element.is_displayed():
                    try:
                        # 滚动到元素可见位置
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(2)
                        
                        # 点击发布按钮
                        element.click()
                        logger.info("✅ 发布按钮点击成功")
                        return True
                        
                    except Exception as e:
                        logger.warning(f"点击发布按钮失败: {e}")
                        continue
            
            logger.warning("未找到可用的发布按钮")
            return False
            
        except Exception as e:
            logger.error(f"智能查找发布按钮失败: {e}")
            return False

    def _check_publish_result(self) -> bool:
        """检查发布结果"""
        try:
            # 检查成功提示
            success_indicators = [
                "Video published",
                "Published",
                "Upload complete",
                "Processing",
                "Scheduled"
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
                '//button[contains(text(), "OK")]',
                '//button[contains(text(), "Got it")]',
                '//ytcp-button[contains(text(), "OK")]'
            ]
            
            for selector in error_dialogs:
                element = self.find_element_safe(By.XPATH, selector, timeout=2)
                if element:
                    element.click()
                    logger.info("处理了错误弹窗")
                    time.sleep(2)
                    
        except Exception as e:
            logger.debug(f"处理错误弹窗失败: {e}")
