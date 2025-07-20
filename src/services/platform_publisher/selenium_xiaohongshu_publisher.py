#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Selenium的小红书发布器
参考MoneyPrinterPlus的实现，支持小红书平台视频发布
"""

import time
import asyncio
from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from .selenium_publisher_base import SeleniumPublisherBase
from src.utils.logger import logger


class SeleniumXiaohongshuPublisher(SeleniumPublisherBase):
    """基于Selenium的小红书发布器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__('xiaohongshu', config)
        
    def _get_platform_url(self) -> str:
        """获取小红书创作者中心URL"""
        return "https://creator.xiaohongshu.com/publish/publish"
        
    async def _check_login_status(self) -> bool:
        """检查小红书登录状态"""
        try:
            # 等待页面加载完成
            await asyncio.sleep(2)
            
            # 检查页面URL
            current_url = self.driver.current_url
            logger.info(f"当前页面URL: {current_url}")
            
            # 如果在登录页面，返回False
            if any(keyword in current_url for keyword in ['login', 'passport', 'sso']):
                logger.warning("检测到登录页面，需要用户登录")
                return False
                
            # 检查是否在创作者中心
            if 'creator.xiaohongshu.com' in current_url:
                # 小红书登录状态检查
                login_indicators = [
                    # 上传相关元素
                    '//input[@type="file"]',
                    '//div[contains(@class, "upload")]//input[@type="file"]',
                    
                    # 标题输入框
                    '//input[contains(@placeholder, "标题")]',
                    '//textarea[contains(@placeholder, "标题")]',
                    
                    # 内容输入框
                    '//textarea[contains(@placeholder, "添加正文")]',
                    '//div[contains(@class, "editor")]',
                    
                    # 发布按钮
                    '//button[text()="发布笔记"]',
                    '//button[contains(text(), "发布")]'
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
        """小红书视频发布实现"""
        try:
            # 检查是否为模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 模拟模式：模拟小红书视频发布过程")
                
                # 模拟发布过程
                title = video_info.get('title', '')
                description = video_info.get('description', '')
                
                logger.info(f"模拟设置标题: {title}")
                await asyncio.sleep(1)
                logger.info(f"模拟设置正文: {description}")
                await asyncio.sleep(1)
                logger.info("模拟上传视频文件...")
                await asyncio.sleep(3)
                logger.info("模拟点击发布按钮...")
                await asyncio.sleep(2)

                logger.info("✅ 模拟发布成功！")
                return {'success': True, 'message': '模拟发布成功'}

            # 确保在上传页面
            upload_url = "https://creator.xiaohongshu.com/publish/publish"
            if self.driver.current_url != upload_url:
                self.driver.get(upload_url)
                time.sleep(3)
                
            # 1. 上传视频文件
            video_path = video_info.get('video_path')
            if not video_path:
                return {'success': False, 'error': '视频路径不能为空'}
                
            logger.info(f"开始上传视频文件: {video_path}")
            
            # 小红书的文件上传选择器
            file_input_selectors = [
                '//input[@type="file"]',
                '//input[@accept="video/*,image/*"]',
                '//div[contains(@class, "upload")]//input[@type="file"]',
                '//input[contains(@class, "upload-input")]'
            ]
            
            upload_success = False
            for selector in file_input_selectors:
                logger.info(f"尝试使用选择器上传: {selector}")
                if self.upload_file_safe(By.XPATH, selector, video_path, timeout=10):
                    upload_success = True
                    logger.info("✅ 视频文件上传成功")
                    break
                time.sleep(1)
            
            if not upload_success:
                return {'success': False, 'error': '视频上传失败 - 未找到有效的上传元素'}
                
            # 等待视频上传完成
            logger.info("等待视频上传完成...")
            upload_complete = self._wait_for_upload_complete(timeout=300)
            
            if not upload_complete:
                return {'success': False, 'error': '视频上传超时或失败'}
                
            # 2. 设置视频标题
            title = video_info.get('title', '')
            if title:
                logger.info(f"设置标题: {title}")
                title_selectors = [
                    '//input[contains(@placeholder, "标题")]',
                    '//textarea[contains(@placeholder, "标题")]',
                    '//input[contains(@placeholder, "填写标题")]'
                ]
                
                title_set = False
                for selector in title_selectors:
                    if self.send_keys_safe(By.XPATH, selector, title[:100]):  # 小红书标题限制
                        title_set = True
                        break
                
                if not title_set:
                    logger.warning("标题设置失败")
                time.sleep(2)
                
            # 3. 设置视频正文内容
            description = video_info.get('description', '')
            if description:
                logger.info(f"设置正文: {description}")
                desc_selectors = [
                    '//textarea[contains(@placeholder, "添加正文")]',
                    '//textarea[contains(@placeholder, "正文")]',
                    '//div[contains(@class, "editor")]//textarea'
                ]
                
                for selector in desc_selectors:
                    if self.send_keys_safe(By.XPATH, selector, description[:1000]):  # 小红书正文限制
                        break
                time.sleep(2)
                
            # 4. 设置标签（小红书通过#标签）
            tags = video_info.get('tags', [])
            if tags:
                logger.info(f"设置标签: {tags}")
                # 小红书通过在正文中添加#标签的方式设置标签
                tag_text = ' '.join([f'#{tag}' for tag in tags[:10]])  # 限制10个标签
                
                # 在正文末尾添加标签
                desc_selectors = [
                    '//textarea[contains(@placeholder, "添加正文")]',
                    '//textarea[contains(@placeholder, "正文")]'
                ]
                
                for selector in desc_selectors:
                    element = self.find_element_safe(By.XPATH, selector, timeout=3)
                    if element:
                        # 在现有内容后添加标签
                        element.send_keys(f" {tag_text}")
                        break
                time.sleep(2)
                
            # 5. 设置话题（小红书特有）
            topic = video_info.get('topic')
            if topic:
                logger.info(f"设置话题: {topic}")
                try:
                    # 小红书话题通过@话题的方式添加
                    desc_selectors = [
                        '//textarea[contains(@placeholder, "添加正文")]',
                        '//textarea[contains(@placeholder, "正文")]'
                    ]
                    
                    for selector in desc_selectors:
                        element = self.find_element_safe(By.XPATH, selector, timeout=3)
                        if element:
                            element.send_keys(f" @{topic}")
                            break
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"设置话题失败: {e}")
                    
            # 6. 设置地点（可选）
            location = video_info.get('location')
            if location:
                logger.info(f"设置地点: {location}")
                try:
                    location_selector = '//div[contains(text(),"添加地点")]'
                    if self.click_element_safe(By.XPATH, location_selector):
                        time.sleep(1)
                        # 输入地点名称
                        location_input_selector = '//input[contains(@placeholder, "搜索地点")]'
                        if self.send_keys_safe(By.XPATH, location_input_selector, location):
                            time.sleep(2)
                            # 选择第一个搜索结果
                            first_result_selector = '//div[contains(@class, "location-item")][1]'
                            self.click_element_safe(By.XPATH, first_result_selector)
                        time.sleep(1)
                except Exception as e:
                    logger.warning(f"设置地点失败: {e}")
                    
            # 7. 发布视频
            logger.info("开始发布视频...")
            time.sleep(2)
            
            # 智能检测并点击发布按钮
            publish_success = self._smart_find_publish_button()
            
            if publish_success:
                logger.info("发布按钮点击成功，等待发布完成...")
                time.sleep(5)
                
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
            logger.error(f"小红书视频发布失败: {e}")
            return {'success': False, 'error': str(e)}

    def _wait_for_upload_complete(self, timeout: int = 300) -> bool:
        """等待视频上传完成"""
        try:
            logger.info("等待小红书视频上传完成...")
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # 检查上传进度指示器
                    progress_indicators = [
                        '//div[contains(@class, "progress")]',
                        '//div[contains(text(), "上传中")]',
                        '//div[contains(text(), "处理中")]',
                        '//div[contains(text(), "%")]'
                    ]
                    
                    uploading = False
                    for selector in progress_indicators:
                        if self.find_element_safe(By.XPATH, selector, timeout=1):
                            uploading = True
                            break
                    
                    if not uploading:
                        # 检查完成指示器
                        completion_indicators = [
                            '//video',  # 视频预览
                            '//input[contains(@placeholder, "标题")]',  # 标题输入框
                            '//button[text()="发布笔记"]'  # 发布按钮
                        ]
                        
                        for selector in completion_indicators:
                            element = self.find_element_safe(By.XPATH, selector, timeout=2)
                            if element and element.is_enabled():
                                logger.info("✅ 检测到上传完成")
                                return True
                    
                    time.sleep(3)
                    
                except Exception as e:
                    logger.debug(f"等待上传完成时出现异常: {e}")
                    time.sleep(2)
            
            logger.warning("等待上传完成超时")
            return False
            
        except Exception as e:
            logger.error(f"等待上传完成失败: {e}")
            return False

    def _smart_find_publish_button(self) -> bool:
        """智能查找并点击发布按钮"""
        try:
            logger.info("开始智能检测小红书发布按钮...")
            
            # 小红书发布按钮选择器
            publish_selectors = [
                '//button[text()="发布笔记"]',
                '//button[contains(text(), "发布笔记")]',
                '//button[contains(text(), "发布")]',
                '//span[text()="发布笔记"]/parent::button',
                '//button[contains(@class, "publish")]'
            ]
            
            for i, selector in enumerate(publish_selectors):
                logger.info(f"尝试发布按钮选择器 {i+1}/{len(publish_selectors)}: {selector}")
                element = self.find_element_safe(By.XPATH, selector, timeout=5)
                if element and element.is_enabled() and element.is_displayed():
                    try:
                        # 滚动到元素可见位置
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(1)
                        
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
            time.sleep(2)
            
            # 常见错误弹窗处理
            error_dialogs = [
                '//div[contains(text(), "确定")]',
                '//button[contains(text(), "确定")]',
                '//button[contains(text(), "知道了")]'
            ]
            
            for selector in error_dialogs:
                element = self.find_element_safe(By.XPATH, selector, timeout=2)
                if element:
                    element.click()
                    logger.info("处理了错误弹窗")
                    time.sleep(1)
                    
        except Exception as e:
            logger.debug(f"处理错误弹窗失败: {e}")
