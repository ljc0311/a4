#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Selenium的B站发布器
参考MoneyPrinterPlus的实现
"""

import time
import pyperclip
from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from .selenium_publisher_base import SeleniumPublisherBase
from src.utils.logger import logger


class SeleniumBilibiliPublisher(SeleniumPublisherBase):
    """基于Selenium的B站发布器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__('bilibili', config)
        
    def _get_platform_url(self) -> str:
        """获取B站投稿页面URL"""
        return "https://member.bilibili.com/platform/upload/video/frame"
        
    async def _check_login_status(self) -> bool:
        """检查B站登录状态"""
        try:
            # 检查页面URL
            current_url = self.driver.current_url
            if 'login' in current_url or 'passport' in current_url:
                return False
                
            # 检查是否在投稿页面
            if 'member.bilibili.com' in current_url:
                # 检查页面元素
                login_indicators = [
                    '//*[@id="video-up-app"]/div[1]/div[2]/div/div[1]/div/div/input',  # 视频上传
                    '//*[@id="video-up-app"]/div[2]/div[1]/div[2]/div[3]/div/div[2]/div[1]/div/input',  # 标题输入
                ]
                
                for selector in login_indicators:
                    element = self.find_element_safe(By.XPATH, selector, timeout=5)
                    if element:
                        logger.debug(f"找到B站登录指示器: {selector}")
                        return True
                        
            return False
            
        except Exception as e:
            logger.error(f"检查B站登录状态失败: {e}")
            return False
            
    async def _publish_video_impl(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """B站视频发布实现"""
        try:
            # 确保在投稿页面
            upload_url = "https://member.bilibili.com/platform/upload/video/frame"
            if self.driver.current_url != upload_url:
                self.driver.get(upload_url)
                time.sleep(3)
                
            # 1. 上传视频文件
            video_path = video_info.get('video_path')
            if not video_path:
                return {'success': False, 'error': '视频路径不能为空'}
                
            logger.info("开始上传视频文件...")
            file_input_selector = '//*[@id="video-up-app"]/div[1]/div[2]/div/div[1]/div/div/input'
            if not self.upload_file_safe(By.XPATH, file_input_selector, video_path):
                return {'success': False, 'error': '视频上传失败'}
                
            # 等待视频上传完成
            logger.info("等待视频上传完成...")
            time.sleep(15)
            
            # 2. 设置视频标题
            title = video_info.get('title', '')
            if title:
                logger.info(f"设置标题: {title}")
                title_selector = '//*[@id="video-up-app"]/div[2]/div[1]/div[2]/div[3]/div/div[2]/div[1]/div/input'
                title_element = self.find_element_safe(By.XPATH, title_selector)
                if title_element:
                    title_element.clear()
                    time.sleep(2)
                    title_element.send_keys(title[:80])  # B站标题限制80字
                    time.sleep(2)
                else:
                    logger.warning("标题输入框未找到")
                    
            # 3. 设置分区
            category = video_info.get('category')
            if category:
                await self._set_category(category)
                
            # 4. 设置标签
            tags = video_info.get('tags', [])
            if tags and isinstance(tags, list):
                logger.info(f"设置标签: {tags}")
                await self._set_tags(tags)
                
            # 5. 设置视频描述
            description = video_info.get('description', '')
            if description:
                logger.info("设置视频描述...")
                await self._set_description(description)
                
            # 6. 设置封面
            cover_path = video_info.get('cover_path')
            if cover_path:
                await self.set_cover_image(cover_path)
                
            # 7. 发布视频
            auto_publish = video_info.get('auto_publish', False)
            if auto_publish:
                logger.info("自动发布视频...")
                publish_selector = '//button[@class="submit-add"]'
                if self.click_element_safe(By.XPATH, publish_selector):
                    logger.info("B站视频发布成功")
                    return {'success': True, 'message': 'B站视频发布成功'}
                else:
                    logger.warning("发布按钮点击失败")
                    return {'success': False, 'error': '发布按钮点击失败'}
            else:
                logger.info("视频已准备就绪，等待手动发布")
                return {'success': True, 'message': '视频已准备就绪，请手动点击发布'}
                
        except Exception as e:
            logger.error(f"B站视频发布失败: {e}")
            return {'success': False, 'error': str(e)}
            
    async def _set_category(self, category: Dict[str, str]):
        """设置B站分区"""
        try:
            level1 = category.get('level1')
            level2 = category.get('level2')
            
            if not level1 or not level2:
                logger.warning("分区信息不完整")
                return
                
            logger.info(f"设置分区: {level1} -> {level2}")
            
            # 点击分区选择器
            section_selector = '//div[@class="select-controller"]'
            if self.click_element_safe(By.XPATH, section_selector):
                time.sleep(3)
                
                # 选择一级分区
                level1_selector = f'//p[@class="f-item-content" and text()="{level1}"]'
                if self.click_element_safe(By.XPATH, level1_selector):
                    time.sleep(2)
                    
                    # 选择二级分区
                    level2_selector = f'//p[@class="item-main" and text()="{level2}"]'
                    if self.click_element_safe(By.XPATH, level2_selector):
                        logger.info("分区设置成功")
                        time.sleep(1)
                    else:
                        logger.warning(f"二级分区选择失败: {level2}")
                else:
                    logger.warning(f"一级分区选择失败: {level1}")
            else:
                logger.warning("分区选择器点击失败")
                
        except Exception as e:
            logger.error(f"设置分区失败: {e}")
            
    async def _set_tags(self, tags: list):
        """设置B站标签"""
        try:
            tags_selector = '//input[@placeholder="按回车键Enter创建标签"]'
            tags_element = self.find_element_safe(By.XPATH, tags_selector)
            
            if not tags_element:
                logger.warning("标签输入框未找到")
                return
                
            # 清除自动生成的标签
            for i in range(10):
                tags_element.send_keys(Keys.BACK_SPACE)
                time.sleep(0.5)
                
            # 添加新标签
            for i, tag in enumerate(tags[:10]):  # B站最多10个标签
                logger.info(f"添加标签: {tag}")
                tags_element.send_keys(' ')
                tags_element.send_keys(tag)
                time.sleep(2)
                tags_element.send_keys(Keys.ENTER)
                time.sleep(1)
                tags_element.send_keys(' ')
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"设置标签失败: {e}")
            
    async def _set_description(self, description: str):
        """设置B站视频描述"""
        try:
            content_selector = '//*[@id="video-up-app"]/div[2]/div[1]/div[2]/div[7]/div/div[2]/div/div[1]/div[1]'
            content_element = self.find_element_safe(By.XPATH, content_selector)
            
            if content_element:
                content_element.click()
                time.sleep(2)
                
                # 使用剪贴板粘贴内容
                pyperclip.copy(description)
                action_chains = ActionChains(self.driver)
                ctrl_key = Keys.COMMAND if self.driver.capabilities['platformName'] == 'mac' else Keys.CONTROL
                action_chains.key_down(ctrl_key).send_keys('v').key_up(ctrl_key).perform()
                time.sleep(2)
                logger.info("描述设置成功")
            else:
                logger.warning("描述输入框未找到")
                
        except Exception as e:
            logger.error(f"设置描述失败: {e}")
            
    async def set_cover_image(self, cover_path: str) -> bool:
        """设置B站视频封面"""
        try:
            logger.info(f"设置视频封面: {cover_path}")
            
            # B站封面上传选择器
            cover_selectors = [
                '//input[@accept="image/png,image/jpeg,image/jpg"]',
                '//div[contains(@class, "cover")]//input[@type="file"]',
                '//input[@type="file" and contains(@accept, "image")]'
            ]
            
            for selector in cover_selectors:
                if self.upload_file_safe(By.XPATH, selector, cover_path, timeout=5):
                    logger.info("B站封面设置成功")
                    time.sleep(3)
                    return True
                    
            logger.warning("未找到B站封面上传元素")
            return False
            
        except Exception as e:
            logger.error(f"设置B站封面失败: {e}")
            return False
            
    async def set_original_content(self, is_original: bool = True):
        """设置原创内容"""
        try:
            if is_original:
                logger.info("设置为原创内容")
                original_selector = '//input[@type="checkbox" and contains(@class, "original")]'
                original_element = self.find_element_safe(By.XPATH, original_selector)
                
                if original_element and not original_element.is_selected():
                    original_element.click()
                    logger.info("原创标记设置成功")
                    
        except Exception as e:
            logger.error(f"设置原创内容失败: {e}")
            
    async def set_monetization(self, enable: bool = True):
        """设置商业化权限"""
        try:
            if enable:
                logger.info("开启商业化权限")
                monetization_selector = '//input[@type="checkbox" and contains(@class, "monetization")]'
                monetization_element = self.find_element_safe(By.XPATH, monetization_selector)
                
                if monetization_element and not monetization_element.is_selected():
                    monetization_element.click()
                    logger.info("商业化权限设置成功")
                    
        except Exception as e:
            logger.error(f"设置商业化权限失败: {e}")
