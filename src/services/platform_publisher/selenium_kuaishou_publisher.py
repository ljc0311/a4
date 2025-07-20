#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Selenium的快手发布器
参考MoneyPrinterPlus的实现，支持快手平台视频发布
"""

import time
import asyncio
from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from .selenium_publisher_base import SeleniumPublisherBase
from src.utils.logger import logger


class SeleniumKuaishouPublisher(SeleniumPublisherBase):
    """基于Selenium的快手发布器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__('kuaishou', config)
        
    def _get_platform_url(self) -> str:
        """获取快手创作者中心URL"""
        return "https://cp.kuaishou.com/article/publish/video"
        
    async def _check_login_status(self) -> bool:
        """检查快手登录状态"""
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
            if 'cp.kuaishou.com' in current_url:
                # 快手登录状态检查
                login_indicators = [
                    # 上传相关元素
                    '//input[@type="file"]',
                    '//div[contains(@class, "upload")]//input[@type="file"]',
                    
                    # 标题输入框
                    '//input[contains(@placeholder, "标题")]',
                    '//textarea[contains(@placeholder, "标题")]',
                    
                    # 内容输入框
                    '//textarea[contains(@placeholder, "简介") or contains(@placeholder, "描述")]',
                    '//div[contains(@class, "editor")]',
                    
                    # 发布按钮
                    '//button[text()="发布作品"]',
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
        """快手视频发布实现"""
        try:
            # 检查是否为模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 模拟模式：模拟快手视频发布过程")
                
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
            upload_url = "https://cp.kuaishou.com/article/publish/video"
            if self.driver.current_url != upload_url:
                self.driver.get(upload_url)
                time.sleep(3)
                
            # 1. 上传视频文件
            video_path = video_info.get('video_path')
            if not video_path:
                return {'success': False, 'error': '视频路径不能为空'}
                
            logger.info(f"开始上传视频文件: {video_path}")
            
            # 快手的文件上传选择器
            file_input_selectors = [
                '//input[@type="file"]',
                '//input[@accept="video/*"]',
                '//div[contains(@class, "upload")]//input[@type="file"]'
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
                    '//textarea[contains(@placeholder, "标题")]'
                ]
                
                title_set = False
                for selector in title_selectors:
                    if self.send_keys_safe(By.XPATH, selector, title[:50]):  # 快手标题限制
                        title_set = True
                        break
                
                if not title_set:
                    # 启用爬虫辅助智能检测标题输入框
                    logger.info("🕷️ 启用爬虫辅助检测标题输入框...")
                    title_set = self._crawler_assisted_set_title(title[:50])
                    if not title_set:
                        logger.warning("标题设置失败")
                time.sleep(2)
                
            # 3. 设置视频描述
            description = video_info.get('description', '')
            if description:
                logger.info(f"设置描述: {description}")
                desc_selectors = [
                    '//textarea[contains(@placeholder, "简介")]',
                    '//textarea[contains(@placeholder, "描述")]',
                    '//div[contains(@class, "editor")]//textarea'
                ]
                
                desc_set = False
                for selector in desc_selectors:
                    if self.send_keys_safe(By.XPATH, selector, description[:1000]):  # 快手描述限制
                        desc_set = True
                        break

                if not desc_set:
                    # 启用爬虫辅助智能检测描述输入框
                    logger.info("🕷️ 启用爬虫辅助检测描述输入框...")
                    self._crawler_assisted_set_description(description[:1000])

                time.sleep(2)
                
            # 4. 设置标签（通过描述中的#标签）
            tags = video_info.get('tags', [])
            if tags:
                logger.info(f"设置标签: {tags}")
                # 快手通过在描述中添加#标签的方式设置标签
                tag_text = ' '.join([f'#{tag}' for tag in tags[:5]])  # 限制5个标签
                
                # 在描述末尾添加标签
                desc_selectors = [
                    '//textarea[contains(@placeholder, "简介")]',
                    '//textarea[contains(@placeholder, "描述")]'
                ]
                
                for selector in desc_selectors:
                    element = self.find_element_safe(By.XPATH, selector, timeout=3)
                    if element:
                        # 在现有内容后添加标签
                        element.send_keys(f" {tag_text}")
                        break
                time.sleep(2)
                
            # 5. 设置领域（快手特有）
            domain = video_info.get('domain')
            if domain:
                logger.info(f"设置领域: {domain}")
                try:
                    domain_selector = '//div[contains(text(),"选择领域")]'
                    if self.click_element_safe(By.XPATH, domain_selector):
                        time.sleep(1)
                        domain_option_selector = f'//div[contains(text(),"{domain}")]'
                        self.click_element_safe(By.XPATH, domain_option_selector)
                        time.sleep(1)
                except Exception as e:
                    logger.warning(f"设置领域失败: {e}")
                    
            # 6. 发布视频
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
            logger.error(f"快手视频发布失败: {e}")
            return {'success': False, 'error': str(e)}

    def _wait_for_upload_complete(self, timeout: int = 300) -> bool:
        """等待视频上传完成"""
        try:
            logger.info("等待快手视频上传完成...")
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
                            '//button[text()="发布作品"]'  # 发布按钮
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
            logger.info("开始智能检测快手发布按钮...")
            
            # 快手发布按钮选择器
            publish_selectors = [
                '//button[text()="发布作品"]',
                '//button[contains(text(), "发布作品")]',
                '//button[contains(text(), "发布")]',
                '//span[text()="发布作品"]/parent::button',
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
            
            # 如果传统选择器都失败，启用爬虫辅助检测
            logger.info("🕷️ 启动爬虫辅助智能检测...")
            return self._crawler_assisted_find_publish_button()

        except Exception as e:
            logger.error(f"智能查找发布按钮失败: {e}")
            return False

    def _crawler_assisted_find_publish_button(self) -> bool:
        """爬虫辅助查找发布按钮"""
        try:
            logger.info("🔍 爬虫辅助：分析页面结构查找发布按钮...")

            # 1. 查找所有按钮元素
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            logger.info(f"📊 页面共找到 {len(all_buttons)} 个按钮元素")

            # 2. 分析按钮文本和属性
            publish_keywords = ['发布', '发表', '提交', 'publish', 'submit', '完成', 'done', '作品']

            for i, button in enumerate(all_buttons):
                try:
                    if not button.is_displayed() or not button.is_enabled():
                        continue

                    # 获取按钮信息
                    button_text = button.text.strip()
                    button_class = button.get_attribute('class') or ''
                    button_id = button.get_attribute('id') or ''
                    button_type = button.get_attribute('type') or ''

                    # 检查是否包含发布相关关键词
                    text_match = any(keyword in button_text for keyword in publish_keywords)
                    class_match = any(keyword in button_class.lower() for keyword in ['publish', 'submit', 'primary', 'main'])
                    id_match = any(keyword in button_id.lower() for keyword in ['publish', 'submit'])

                    if text_match or class_match or id_match:
                        logger.info(f"🎯 发现疑似发布按钮 #{i+1}:")
                        logger.info(f"   文本: '{button_text}'")
                        logger.info(f"   类名: '{button_class}'")
                        logger.info(f"   ID: '{button_id}'")
                        logger.info(f"   类型: '{button_type}'")

                        # 尝试点击
                        try:
                            # 滚动到元素可见位置
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(1)

                            button.click()
                            logger.info("✅ 爬虫辅助：发布按钮点击成功！")
                            return True
                        except Exception as click_error:
                            logger.debug(f"按钮点击失败: {click_error}")
                            continue

                except Exception as e:
                    logger.debug(f"分析按钮 #{i+1} 时出错: {e}")
                    continue

            # 3. 查找包含发布文本的其他元素
            logger.info("🔍 爬虫辅助：查找包含发布文本的其他可点击元素...")

            for keyword in publish_keywords:
                # 查找包含关键词的所有元素
                elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")

                for element in elements:
                    try:
                        if not element.is_displayed():
                            continue

                        tag_name = element.tag_name.lower()
                        element_text = element.text.strip()

                        # 检查是否为可点击元素
                        if tag_name in ['button', 'a', 'div', 'span'] and element_text:
                            logger.info(f"🎯 发现包含'{keyword}'的元素:")
                            logger.info(f"   标签: {tag_name}")
                            logger.info(f"   文本: '{element_text}'")

                            try:
                                # 滚动到元素可见位置
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                time.sleep(1)

                                element.click()
                                logger.info("✅ 爬虫辅助：发布元素点击成功！")
                                return True
                            except Exception as click_error:
                                logger.debug(f"元素点击失败: {click_error}")
                                continue

                    except Exception as e:
                        logger.debug(f"分析元素时出错: {e}")
                        continue

            logger.warning("❌ 爬虫辅助：未找到可用的发布按钮")
            return False

        except Exception as e:
            logger.error(f"爬虫辅助查找发布按钮失败: {e}")
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

    def _crawler_assisted_set_title(self, title: str) -> bool:
        """爬虫辅助设置标题"""
        try:
            logger.info("🔍 爬虫辅助：智能查找标题输入框...")

            # 1. 查找所有输入框
            all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
            all_textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            all_elements = all_inputs + all_textareas

            logger.info(f"📊 页面共找到 {len(all_elements)} 个输入元素")

            # 2. 分析输入框属性
            title_keywords = ['标题', 'title', '主题', 'subject']

            for i, element in enumerate(all_elements):
                try:
                    if not element.is_displayed() or not element.is_enabled():
                        continue

                    # 获取元素信息
                    placeholder = element.get_attribute('placeholder') or ''
                    element_class = element.get_attribute('class') or ''
                    element_id = element.get_attribute('id') or ''
                    element_name = element.get_attribute('name') or ''

                    # 检查是否为标题相关输入框
                    placeholder_match = any(keyword in placeholder for keyword in title_keywords)
                    class_match = any(keyword in element_class.lower() for keyword in title_keywords)
                    id_match = any(keyword in element_id.lower() for keyword in title_keywords)
                    name_match = any(keyword in element_name.lower() for keyword in title_keywords)

                    if placeholder_match or class_match or id_match or name_match:
                        logger.info(f"🎯 发现疑似标题输入框 #{i+1}:")
                        logger.info(f"   占位符: '{placeholder}'")
                        logger.info(f"   类名: '{element_class}'")
                        logger.info(f"   ID: '{element_id}'")
                        logger.info(f"   名称: '{element_name}'")

                        # 尝试输入标题
                        try:
                            # 清空并输入
                            element.clear()
                            element.send_keys(title)
                            logger.info("✅ 爬虫辅助：标题设置成功！")
                            return True
                        except Exception as input_error:
                            logger.debug(f"输入标题失败: {input_error}")
                            continue

                except Exception as e:
                    logger.debug(f"分析输入框 #{i+1} 时出错: {e}")
                    continue

            # 3. 如果没找到明确的标题框，尝试第一个可见的输入框
            logger.info("🔍 爬虫辅助：尝试第一个可见输入框...")
            for element in all_elements:
                try:
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(title)
                        logger.info("✅ 爬虫辅助：使用第一个输入框设置标题成功！")
                        return True
                except Exception:
                    continue

            logger.warning("❌ 爬虫辅助：未找到可用的标题输入框")
            return False

        except Exception as e:
            logger.error(f"爬虫辅助设置标题失败: {e}")
            return False

    def _crawler_assisted_set_description(self, description: str) -> bool:
        """爬虫辅助设置描述"""
        try:
            logger.info("🔍 爬虫辅助：智能查找描述输入框...")

            # 1. 查找所有文本区域和可编辑div
            all_textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            all_editable_divs = self.driver.find_elements(By.XPATH, '//div[@contenteditable="true"]')
            all_elements = all_textareas + all_editable_divs

            logger.info(f"📊 页面共找到 {len(all_elements)} 个文本输入元素")

            # 2. 分析输入框属性
            desc_keywords = ['简介', '描述', 'description', 'content', '内容', '详情']

            for i, element in enumerate(all_elements):
                try:
                    if not element.is_displayed():
                        continue

                    # 获取元素信息
                    placeholder = element.get_attribute('placeholder') or element.get_attribute('data-placeholder') or ''
                    element_class = element.get_attribute('class') or ''
                    element_id = element.get_attribute('id') or ''
                    element_name = element.get_attribute('name') or ''

                    # 检查是否为描述相关输入框
                    placeholder_match = any(keyword in placeholder for keyword in desc_keywords)
                    class_match = any(keyword in element_class.lower() for keyword in desc_keywords)
                    id_match = any(keyword in element_id.lower() for keyword in desc_keywords)
                    name_match = any(keyword in element_name.lower() for keyword in desc_keywords)

                    if placeholder_match or class_match or id_match or name_match:
                        logger.info(f"🎯 发现疑似描述输入框 #{i+1}:")
                        logger.info(f"   占位符: '{placeholder}'")
                        logger.info(f"   类名: '{element_class}'")
                        logger.info(f"   ID: '{element_id}'")
                        logger.info(f"   名称: '{element_name}'")

                        # 尝试输入描述
                        try:
                            if element.tag_name.lower() == 'div':
                                # 对于contenteditable的div
                                element.click()
                                element.clear()
                                element.send_keys(description)
                            else:
                                # 对于textarea
                                element.clear()
                                element.send_keys(description)
                            logger.info("✅ 爬虫辅助：描述设置成功！")
                            return True
                        except Exception as input_error:
                            logger.debug(f"输入描述失败: {input_error}")
                            continue

                except Exception as e:
                    logger.debug(f"分析输入框 #{i+1} 时出错: {e}")
                    continue

            # 3. 如果没找到明确的描述框，尝试最大的文本区域
            logger.info("🔍 爬虫辅助：尝试最大的文本区域...")
            largest_element = None
            largest_size = 0

            for element in all_elements:
                try:
                    if element.is_displayed():
                        size = element.size
                        area = size['width'] * size['height']
                        if area > largest_size:
                            largest_size = area
                            largest_element = element
                except Exception:
                    continue

            if largest_element:
                try:
                    if largest_element.tag_name.lower() == 'div':
                        largest_element.click()
                        largest_element.clear()
                        largest_element.send_keys(description)
                    else:
                        largest_element.clear()
                        largest_element.send_keys(description)
                    logger.info("✅ 爬虫辅助：使用最大文本区域设置描述成功！")
                    return True
                except Exception:
                    pass

            logger.warning("❌ 爬虫辅助：未找到可用的描述输入框")
            return False

        except Exception as e:
            logger.error(f"爬虫辅助设置描述失败: {e}")
            return False
