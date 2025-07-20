#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MoneyPrinterPlus风格的小红书发布器
"""

import time
from typing import Dict, Any, List

from .moneyprinter_style_publisher import MoneyPrinterStylePublisher
from src.utils.logger import logger


class MoneyPrinterXiaohongshuPublisher(MoneyPrinterStylePublisher):
    """MoneyPrinterPlus风格的小红书发布器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.platform_name = "小红书"
        self.upload_url = "https://creator.xiaohongshu.com/publish/publish"
    
    def get_success_indicators(self) -> List[str]:
        """小红书平台的成功指示器"""
        return [
            '//input[@type="file"]',
            '//button[contains(text(), "发布笔记")]',
            '//div[contains(@class, "title")]//input',
            '//div[contains(@class, "content")]//textarea'
        ]
    
    def publish_video(self, video_path: str, title: str, description: str, tags: List[str] = None) -> bool:
        """发布视频到小红书 - MoneyPrinterPlus风格"""
        try:
            logger.info("开始发布视频到小红书...")
            
            # 1. 导航到上传页面
            if not self.navigate_to_upload_page():
                return False
            
            # 2. 检查登录状态
            if not self.check_login_status():
                logger.warning("小红书未登录，请手动登录后重试")
                input("请在浏览器中手动登录小红书，完成后按回车继续...")
                
                if not self.check_login_status():
                    logger.error("登录检查仍然失败")
                    return False
                
                logger.info("小红书登录成功")
            
            # 3. 上传视频文件
            if not self.upload_video_file(video_path):
                return False
            
            # 4. 等待上传完成
            if not self.wait_for_upload_complete():
                return False
            
            # 5. 设置标题
            if not self.set_title(title):
                logger.warning("标题设置失败，但继续执行")
            
            # 6. 设置描述
            if not self.set_description(description):
                logger.warning("描述设置失败，但继续执行")
            
            # 7. 设置标签
            if tags:
                if not self.set_tags(tags):
                    logger.warning("标签设置失败，但继续执行")
            
            # 8. 发布视频
            if not self.publish():
                return False
            
            logger.info("✅ 小红书视频发布成功！")
            return True
            
        except Exception as e:
            logger.error(f"小红书视频发布失败: {e}")
            return False
    
    def set_title(self, title: str) -> bool:
        """设置标题 - MoneyPrinterPlus风格"""
        try:
            logger.info(f"设置标题: {title}")
            
            # 小红书标题输入框选择器
            title_selectors = [
                '//div[contains(@class, "title")]//input',
                '//input[contains(@placeholder, "标题")]',
                '//input[contains(@placeholder, "请输入标题")]',
                '//div[contains(@class, "c-input")]//input'
            ]
            
            # 使用智能查找
            for selector in title_selectors:
                if self.send_keys_safe(selector, title[:20], timeout=3):  # 小红书标题限制20字
                    logger.info("✅ 标题设置成功")
                    return True
            
            # 爬虫辅助设置标题
            logger.info("🕷️ 启用爬虫辅助设置标题...")
            return self.crawler_assisted_set_title(title[:20])
            
        except Exception as e:
            logger.error(f"设置标题失败: {e}")
            return False
    
    def set_description(self, description: str) -> bool:
        """设置描述 - MoneyPrinterPlus风格"""
        try:
            logger.info(f"设置描述: {description[:100]}...")
            
            # 小红书描述输入框选择器
            desc_selectors = [
                '//div[contains(@class, "content")]//textarea',
                '//textarea[contains(@placeholder, "分享你刚刚发生的新鲜事")]',
                '//div[contains(@class, "c-input")]//textarea',
                '//div[@contenteditable="true"]'
            ]
            
            # 使用智能查找
            for selector in desc_selectors:
                if self.send_keys_safe(selector, description[:1000], timeout=3):
                    logger.info("✅ 描述设置成功")
                    return True
            
            # 爬虫辅助设置描述
            logger.info("🕷️ 启用爬虫辅助设置描述...")
            return self.crawler_assisted_set_description(description[:1000])
            
        except Exception as e:
            logger.error(f"设置描述失败: {e}")
            return False
    
    def set_tags(self, tags: List[str]) -> bool:
        """设置标签 - MoneyPrinterPlus风格"""
        try:
            logger.info(f"设置标签: {tags}")
            
            # 小红书标签通常在描述中以#形式添加
            tag_text = " " + " ".join([f"#{tag}" for tag in tags[:10]])  # 限制标签数量
            
            # 查找描述输入框并添加标签
            desc_selectors = [
                '//div[contains(@class, "content")]//textarea',
                '//textarea[contains(@placeholder, "分享你刚刚发生的新鲜事")]'
            ]
            
            for selector in desc_selectors:
                try:
                    element = self.driver.find_element_by_xpath(selector)
                    if element and element.is_displayed():
                        current_text = element.get_attribute('value') or ''
                        new_text = current_text + tag_text
                        element.clear()
                        element.send_keys(new_text)
                        logger.info("✅ 标签设置成功")
                        return True
                except:
                    continue
            
            logger.warning("标签设置失败")
            return False
            
        except Exception as e:
            logger.error(f"设置标签失败: {e}")
            return False
    
    def publish(self) -> bool:
        """发布视频 - MoneyPrinterPlus风格"""
        try:
            logger.info("开始发布视频...")
            
            # 小红书发布按钮选择器
            publish_selectors = [
                '//button[contains(text(), "发布笔记")]',
                '//button[contains(text(), "发布")]',
                '//div[contains(@class, "publish-btn")]//button',
                '//button[contains(@class, "publish")]'
            ]
            
            # 使用智能查找并点击
            if self.smart_find_and_click(publish_selectors, "发布按钮"):
                logger.info("✅ 发布按钮点击成功")
                
                # 等待发布完成
                time.sleep(3)
                
                # 检查是否有成功提示
                success_indicators = [
                    '//div[contains(text(), "发布成功")]',
                    '//div[contains(text(), "已发布")]',
                    '//span[contains(text(), "发布成功")]'
                ]
                
                for indicator in success_indicators:
                    if self.find_element_safe(indicator, timeout=10):
                        logger.info("✅ 检测到发布成功提示")
                        return True
                
                # 如果没有明确的成功提示，等待一段时间后认为成功
                time.sleep(5)
                logger.info("✅ 发布操作完成")
                return True
            else:
                logger.error("❌ 发布按钮点击失败")
                return False
                
        except Exception as e:
            logger.error(f"发布视频失败: {e}")
            return False
    
    def crawler_assisted_set_title(self, title: str) -> bool:
        """爬虫辅助设置标题"""
        try:
            all_inputs = self.driver.find_elements_by_tag_name("input")
            title_keywords = ['标题', 'title', '主题']
            
            for element in all_inputs:
                try:
                    if not element.is_displayed() or not element.is_enabled():
                        continue
                    
                    placeholder = element.get_attribute('placeholder') or ''
                    element_class = element.get_attribute('class') or ''
                    
                    if any(keyword in placeholder for keyword in title_keywords):
                        element.clear()
                        element.send_keys(title)
                        logger.info("✅ 爬虫辅助标题设置成功")
                        return True
                        
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"爬虫辅助设置标题失败: {e}")
            return False
    
    def crawler_assisted_set_description(self, description: str) -> bool:
        """爬虫辅助设置描述"""
        try:
            all_textareas = (self.driver.find_elements_by_tag_name("textarea") + 
                           self.driver.find_elements_by_xpath('//div[@contenteditable="true"]'))
            
            desc_keywords = ['分享', '新鲜事', 'content', '内容']
            
            for element in all_textareas:
                try:
                    if not element.is_displayed():
                        continue
                    
                    placeholder = element.get_attribute('placeholder') or element.get_attribute('data-placeholder') or ''
                    
                    if any(keyword in placeholder for keyword in desc_keywords):
                        if element.tag_name.lower() == 'div':
                            element.click()
                            element.clear()
                            element.send_keys(description)
                        else:
                            element.clear()
                            element.send_keys(description)
                        logger.info("✅ 爬虫辅助描述设置成功")
                        return True
                        
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"爬虫辅助设置描述失败: {e}")
            return False
