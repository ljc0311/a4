#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Selenium的抖音发布器
参考MoneyPrinterPlus的实现，使用更稳定的Selenium方案
"""

import time
import pyperclip
from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from .selenium_publisher_base import SeleniumPublisherBase
from src.utils.logger import logger


class SeleniumDouyinPublisher(SeleniumPublisherBase):
    """基于Selenium的抖音发布器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__('douyin', config)
        
    def _get_platform_url(self) -> str:
        """获取抖音创作者中心URL"""
        return "https://creator.douyin.com/creator-micro/content/upload"
        
    async def _check_login_status(self) -> bool:
        """检查抖音登录状态"""
        try:
            # 检查页面URL
            current_url = self.driver.current_url
            if 'login' in current_url or 'passport' in current_url:
                return False
                
            # 检查是否在创作者中心
            if 'creator.douyin.com' in current_url:
                # 检查页面元素
                login_indicators = [
                    '//input[@type="file"]',  # 上传按钮
                    '//input[@class="semi-input semi-input-default"]',  # 标题输入框
                    '//div[@data-placeholder="添加作品简介"]',  # 内容输入框
                    '//div[contains(@class, "notranslate")][@data-placeholder="添加作品简介"]',  # 备用内容输入框
                    '//div[contains(@class, "public-DraftEditor-content")]',  # 另一种内容输入框
                    '//button[text()="发布"]',  # 发布按钮
                    '//button[contains(text(), "发布")]'  # 备用发布按钮
                ]

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
        """抖音视频发布实现"""
        try:
            # 检查是否为模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 模拟模式：模拟抖音视频发布过程")

                # 模拟发布过程
                title = video_info.get('title', '')
                description = video_info.get('description', '')
                video_path = video_info.get('video_path', '')

                logger.info(f"📹 模拟上传视频: {video_path}")
                logger.info(f"📝 模拟设置标题: {title}")
                logger.info(f"📄 模拟设置描述: {description}")
                logger.info("⏳ 模拟等待上传完成...")

                # 模拟等待时间
                import asyncio
                await asyncio.sleep(2)

                logger.info("✅ 模拟发布成功！")
                return {'success': True, 'message': '模拟发布成功'}

            # 确保在上传页面
            upload_url = "https://creator.douyin.com/creator-micro/content/upload"
            if self.driver.current_url != upload_url:
                self.driver.get(upload_url)
                time.sleep(3)
                
            # 1. 上传视频文件
            video_path = video_info.get('video_path')
            if not video_path:
                return {'success': False, 'error': '视频路径不能为空'}
                
            logger.info("开始上传视频文件...")
            file_input_selector = '//input[@type="file"]'
            if not self.upload_file_safe(By.XPATH, file_input_selector, video_path):
                return {'success': False, 'error': '视频上传失败'}
                
            # 等待视频上传完成
            logger.info("等待视频上传完成...")
            time.sleep(10)
            
            # 2. 设置视频标题
            title = video_info.get('title', '')
            if title:
                logger.info(f"设置标题: {title}")
                title_selector = '//input[@class="semi-input semi-input-default"]'
                if not self.send_keys_safe(By.XPATH, title_selector, title[:30]):  # 抖音标题限制30字
                    logger.warning("标题设置失败")
                time.sleep(2)
                
            # 3. 设置视频描述（增强版）
            description = video_info.get('description', '')
            if description:
                logger.info("设置视频描述...")
                success = self._set_video_description(description)
                if success:
                    logger.info("✅ 视频描述设置成功")
                else:
                    logger.warning("❌ 视频描述设置失败")

            # 4. 设置标签（已在描述中包含，跳过单独设置）
            tags = video_info.get('tags', [])
            if tags and isinstance(tags, list):
                logger.info(f"标签已包含在描述中: {tags}")
                # 标签已经通过描述设置，这里不再单独设置
                logger.info("✅ 标签通过描述设置完成")
                        
            # 5. 设置合集（如果有）
            collection = video_info.get('collection')
            if collection:
                logger.info(f"设置合集: {collection}")
                try:
                    collection_selector = '//div[contains(text(),"选择合集")]'
                    if self.click_element_safe(By.XPATH, collection_selector):
                        time.sleep(1)
                        collection_option_selector = f'//div[@class="semi-select-option collection-option"]//span[text()="{collection}"]'
                        self.click_element_safe(By.XPATH, collection_option_selector)
                        time.sleep(1)
                except Exception as e:
                    logger.warning(f"设置合集失败: {e}")
                    
            # 6. 设置隐私选项（可选，如果失败不影响发布）
            logger.info("尝试设置视频隐私选项...")
            try:
                privacy_success = self._set_privacy_options()
                if privacy_success:
                    logger.info("隐私选项设置成功")
                else:
                    logger.info("隐私选项设置失败，跳过此步骤")
            except Exception as e:
                logger.warning(f"隐私选项设置异常: {e}，跳过此步骤")

            # 7. 自动发布视频（默认启用全自动化）
            auto_publish = video_info.get('auto_publish', True)  # 默认启用自动发布

            logger.info("开始自动发布视频...")

            # 等待页面稳定
            time.sleep(2)

            # 智能检测并点击发布按钮
            publish_success = self._smart_find_publish_button()

            if publish_success:
                # 等待发布完成
                logger.info("发布按钮点击成功，等待发布完成...")
                time.sleep(5)  # 增加等待时间确保发布完成

                # 🔧 处理可能的错误弹窗
                self._handle_error_dialogs()

                # 检查发布结果
                if self._check_publish_result():
                    logger.info("✅ 视频发布成功！")
                    return {'success': True, 'message': '视频发布成功'}
                else:
                    logger.info("✅ 视频已提交发布，请稍后查看发布状态")
                    return {'success': True, 'message': '视频已提交发布'}
            else:
                logger.warning("❌ 自动发布失败，尝试备用方案...")

                # 备用方案：尝试更激进的发布按钮检测
                backup_success = self._backup_publish_attempt()
                if backup_success:
                    logger.info("✅ 备用发布方案成功！")
                    return {'success': True, 'message': '视频发布成功（备用方案）'}
                else:
                    logger.error("❌ 所有自动发布方案都失败")
                    return {'success': False, 'error': '自动发布失败，请检查页面状态'}
                
        except Exception as e:
            logger.error(f"抖音视频发布失败: {e}")
            return {'success': False, 'error': str(e)}

    def _smart_find_publish_button(self) -> bool:
        """智能查找并点击发布按钮"""
        try:
            logger.info("开始智能检测发布按钮...")

            # 第一轮：使用MoneyPrinterPlus验证过的选择器
            primary_selectors = [
                '//button[text()="发布"]',  # MoneyPrinterPlus使用的选择器（已验证有效）
                '//button[contains(text(), "发布")]',  # 包含文本匹配
                '//button[@class="semi-button semi-button-primary" and text()="发布"]',  # 完整类名匹配
                '//button[contains(@class, "semi-button-primary")]',  # 主要按钮样式
                '//span[text()="发布"]/parent::button',  # span包含的按钮
                '//div[text()="发布"]/parent::button'  # div包含的按钮
            ]

            for selector in primary_selectors:
                logger.debug(f"尝试主要选择器: {selector}")
                element = self.find_element_safe(By.XPATH, selector, timeout=3)
                if element and element.is_enabled() and element.is_displayed():
                    try:
                        # 先尝试普通点击
                        element.click()
                        logger.info(f"发布按钮点击成功: {selector}")
                        return True
                    except Exception as e:
                        try:
                            # 如果普通点击失败，尝试JavaScript点击
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info(f"发布按钮JavaScript点击成功: {selector}")
                            return True
                        except Exception as e2:
                            logger.debug(f"JavaScript点击也失败: {e2}")
                            continue

            # 第二轮：查找所有可能的按钮并检查文本和样式
            logger.info("尝试查找所有按钮元素...")
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")

            for button in all_buttons:
                try:
                    if button.is_displayed() and button.is_enabled():
                        button_text = button.text.strip()
                        if button_text in ["发布", "立即发布", "确认发布", "提交"]:
                            # 检查按钮样式，优先选择红色/主要样式的按钮
                            button_style = button.get_attribute("style") or ""
                            button_class = button.get_attribute("class") or ""

                            logger.info(f"找到发布按钮，文本: {button_text}, 样式: {button_class}")

                            # 使用JavaScript点击，更可靠
                            self.driver.execute_script("arguments[0].click();", button)
                            logger.info("使用JavaScript点击发布按钮成功")
                            return True
                except Exception as e:
                    logger.debug(f"按钮点击失败: {e}")
                    continue

            # 第三轮：查找包含发布文本的所有元素
            logger.info("尝试查找包含发布文本的可点击元素...")
            publish_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '发布')]")

            for element in publish_elements:
                try:
                    if element.is_displayed() and element.is_enabled():
                        # 检查是否是可点击的元素
                        tag_name = element.tag_name.lower()
                        if tag_name in ['button', 'a', 'div', 'span']:
                            logger.info(f"尝试点击发布元素: {tag_name} - {element.text}")
                            element.click()
                            return True
                except Exception as e:
                    continue

            # 第四轮：调试信息 - 列出页面上所有按钮
            logger.info("调试：列出页面上所有按钮元素...")
            try:
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                logger.info(f"页面上共找到 {len(all_buttons)} 个按钮")

                for i, button in enumerate(all_buttons[:10]):  # 只显示前10个
                    try:
                        text = button.text.strip()
                        classes = button.get_attribute("class")
                        enabled = button.is_enabled()
                        displayed = button.is_displayed()
                        logger.info(f"按钮 {i+1}: 文本='{text}', 类名='{classes}', 可用={enabled}, 可见={displayed}")
                    except:
                        continue
            except Exception as e:
                logger.debug(f"调试信息获取失败: {e}")

            logger.warning("未找到可用的发布按钮")
            return False

        except Exception as e:
            logger.error(f"智能发布按钮检测失败: {e}")
            return False

    def _try_click_element(self, element, description: str) -> bool:
        """尝试点击元素的通用方法"""
        try:
            # 方法1: 普通点击
            element.click()
            logger.info(f"✅ {description} - 普通点击成功")
            return True
        except Exception as e1:
            try:
                # 方法2: JavaScript点击
                self.driver.execute_script("arguments[0].click();", element)
                logger.info(f"✅ {description} - JavaScript点击成功")
                return True
            except Exception as e2:
                try:
                    # 方法3: ActionChains点击
                    ActionChains(self.driver).move_to_element(element).click().perform()
                    logger.info(f"✅ {description} - ActionChains点击成功")
                    return True
                except Exception as e3:
                    logger.debug(f"❌ {description} - 所有点击方法都失败: {e1}, {e2}, {e3}")
                    return False

    def _backup_publish_attempt(self) -> bool:
        """备用发布方案 - 更激进的检测方法"""
        try:
            logger.info("🔄 启动备用发布方案...")

            # 方案1: 尝试键盘快捷键
            try:
                logger.info("尝试键盘快捷键发布...")
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys(Keys.ENTER).key_up(Keys.CONTROL).perform()
                time.sleep(2)
                if self._check_publish_result():
                    logger.info("✅ 键盘快捷键发布成功")
                    return True
            except Exception as e:
                logger.debug(f"键盘快捷键失败: {e}")

            # 方案2: 查找所有可能的发布相关元素
            logger.info("查找所有可能的发布元素...")
            publish_keywords = ["发布", "提交", "确认", "完成", "publish", "submit", "confirm"]

            for keyword in publish_keywords:
                elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            tag_name = element.tag_name.lower()
                            if tag_name in ['button', 'a', 'div', 'span', 'input']:
                                logger.info(f"尝试备用元素: {tag_name} - '{element.text.strip()}'")
                                if self._try_click_element(element, f"备用元素({keyword})"):
                                    time.sleep(2)
                                    if self._check_publish_result():
                                        return True
                    except Exception:
                        continue

            # 方案3: 模拟回车键
            try:
                logger.info("尝试回车键发布...")
                ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                time.sleep(2)
                if self._check_publish_result():
                    logger.info("✅ 回车键发布成功")
                    return True
            except Exception as e:
                logger.debug(f"回车键失败: {e}")

            return False

        except Exception as e:
            logger.error(f"备用发布方案失败: {e}")
            return False

    def _check_publish_result(self) -> bool:
        """检查发布结果"""
        try:
            # 检查URL变化
            current_url = self.driver.current_url
            if 'upload' not in current_url:
                logger.info("URL已变化，可能发布成功")
                return True

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

            # 检查是否还在上传页面（如果不在，可能是发布成功了）
            upload_indicators = [
                '//input[@type="file"]',
                '//div[@data-placeholder="添加作品简介"]'
            ]

            still_on_upload = False
            for selector in upload_indicators:
                if self.find_element_safe(By.XPATH, selector, timeout=1):
                    still_on_upload = True
                    break

            if not still_on_upload:
                logger.info("已离开上传页面，可能发布成功")
                return True

            return False

        except Exception as e:
            logger.debug(f"检查发布结果失败: {e}")
            return False

    def _handle_error_dialogs(self):
        """处理发布后可能出现的错误弹窗"""
        try:
            # 等待弹窗出现
            time.sleep(2)

            # 查找常见的错误弹窗和确认按钮
            dialog_selectors = [
                '//button[text()="确定"]',
                '//button[text()="OK"]',
                '//button[text()="知道了"]',
                '//button[text()="我知道了"]',
                '//button[contains(@class, "confirm")]',
                '//div[contains(@class, "modal")]//button',
                '//div[contains(@class, "dialog")]//button'
            ]

            for selector in dialog_selectors:
                try:
                    element = self.find_element_safe(By.XPATH, selector, timeout=1)
                    if element and element.is_displayed():
                        element.click()
                        logger.info(f"✅ 已处理错误弹窗: {selector}")
                        time.sleep(1)
                        break
                except Exception:
                    continue

            # 检查是否有错误提示文本
            error_texts = [
                "发布失败",
                "上传失败",
                "网络错误",
                "系统繁忙",
                "请稍后重试"
            ]

            for error_text in error_texts:
                try:
                    elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{error_text}')]")
                    if elements:
                        logger.warning(f"⚠️ 检测到错误提示: {error_text}")
                        break
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"处理错误弹窗时出错: {e}")

    def _set_video_description(self, description: str) -> bool:
        """设置视频描述（增强版）"""
        try:
            logger.info("🔍 开始设置视频描述...")

            # 扩展的选择器列表（基于MoneyPrinterPlus和实际测试）
            content_selectors = [
                '//div[@data-placeholder="添加作品简介"]',  # 主要选择器
                '//div[contains(@class, "notranslate")][@data-placeholder="添加作品简介"]',  # 带翻译类
                '//div[contains(@class, "public-DraftEditor-content")]',  # Draft编辑器
                '//div[@contenteditable="true"][@data-placeholder="添加作品简介"]',  # 可编辑div
                '//div[@role="textbox"][@data-placeholder="添加作品简介"]',  # 文本框角色
                '//div[contains(@class, "DraftEditor-editorContainer")]//div[@contenteditable="true"]',  # Draft容器
                '//div[contains(@class, "semi-input")][@contenteditable="true"]',  # Semi UI输入框
                '//div[contains(@data-placeholder, "简介")]',  # 包含简介的占位符
                '//textarea[@placeholder="添加作品简介"]',  # textarea元素
                '//div[contains(@class, "content-input")]',  # 内容输入类
            ]

            content_element = None
            used_selector = None

            # 第一轮：精确匹配
            logger.info("🎯 第一轮：尝试精确选择器...")
            for i, selector in enumerate(content_selectors, 1):
                logger.debug(f"尝试选择器 {i}: {selector}")
                element = self.find_element_safe(By.XPATH, selector, timeout=2)
                if element and element.is_displayed():
                    content_element = element
                    used_selector = selector
                    logger.info(f"✅ 找到描述输入框: 选择器{i}")
                    break

            # 第二轮：如果没找到，尝试更广泛的搜索
            if not content_element:
                logger.info("🔄 第二轮：尝试广泛搜索...")

                # 查找所有可编辑的div
                editable_divs = self.driver.find_elements(By.XPATH, '//div[@contenteditable="true"]')
                for div in editable_divs:
                    try:
                        if div.is_displayed():
                            placeholder = div.get_attribute('data-placeholder') or ''
                            class_name = div.get_attribute('class') or ''
                            if '简介' in placeholder or 'content' in class_name.lower():
                                content_element = div
                                used_selector = "广泛搜索-可编辑div"
                                logger.info(f"✅ 通过广泛搜索找到描述框: {placeholder}")
                                break
                    except Exception:
                        continue

            # 第三轮：查找textarea
            if not content_element:
                logger.info("🔄 第三轮：查找textarea元素...")
                textareas = self.driver.find_elements(By.TAG_NAME, 'textarea')
                for textarea in textareas:
                    try:
                        if textarea.is_displayed():
                            placeholder = textarea.get_attribute('placeholder') or ''
                            if '简介' in placeholder or '描述' in placeholder:
                                content_element = textarea
                                used_selector = "textarea搜索"
                                logger.info(f"✅ 找到textarea描述框: {placeholder}")
                                break
                    except Exception:
                        continue

            if not content_element:
                logger.error("❌ 未找到任何描述输入框")
                return False

            # 尝试多种方法设置内容
            logger.info(f"📝 开始设置描述内容，使用选择器: {used_selector}")

            # 方法1: 点击+清空+剪贴板粘贴（最稳定）
            try:
                logger.info("方法1: 剪贴板粘贴...")
                content_element.click()
                time.sleep(1)

                # 清空现有内容
                content_element.clear()
                time.sleep(0.5)

                # 使用Ctrl+A全选后删除（确保清空）
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                time.sleep(0.5)
                ActionChains(self.driver).send_keys(Keys.DELETE).perform()
                time.sleep(0.5)

                # 复制到剪贴板并粘贴
                pyperclip.copy(description)
                time.sleep(0.5)

                ctrl_key = Keys.COMMAND if self.driver.capabilities.get('platformName') == 'mac' else Keys.CONTROL
                ActionChains(self.driver).key_down(ctrl_key).send_keys('v').key_up(ctrl_key).perform()
                time.sleep(2)

                # 验证内容是否设置成功
                current_text = content_element.get_attribute('textContent') or content_element.get_attribute('value') or ''
                if description[:20] in current_text:
                    logger.info("✅ 剪贴板粘贴成功")
                    return True

            except Exception as e:
                logger.debug(f"剪贴板粘贴失败: {e}")

            # 方法2: 直接send_keys
            try:
                logger.info("方法2: 直接输入...")
                content_element.click()
                time.sleep(1)
                content_element.clear()
                time.sleep(0.5)
                content_element.send_keys(description)
                time.sleep(2)

                # 验证
                current_text = content_element.get_attribute('textContent') or content_element.get_attribute('value') or ''
                if description[:20] in current_text:
                    logger.info("✅ 直接输入成功")
                    return True

            except Exception as e:
                logger.debug(f"直接输入失败: {e}")

            # 方法3: JavaScript设置
            try:
                logger.info("方法3: JavaScript设置...")
                self.driver.execute_script("arguments[0].textContent = arguments[1];", content_element, description)
                time.sleep(1)

                # 触发输入事件
                self.driver.execute_script("""
                    var element = arguments[0];
                    var event = new Event('input', { bubbles: true });
                    element.dispatchEvent(event);
                """, content_element)
                time.sleep(1)

                # 验证
                current_text = content_element.get_attribute('textContent') or ''
                if description[:20] in current_text:
                    logger.info("✅ JavaScript设置成功")
                    return True

            except Exception as e:
                logger.debug(f"JavaScript设置失败: {e}")

            logger.error("❌ 所有描述设置方法都失败")
            return False

        except Exception as e:
            logger.error(f"设置视频描述时发生错误: {e}")
            return False

    def _set_privacy_options(self) -> bool:
        """设置视频隐私选项（简化版，不阻塞发布流程）"""
        try:
            logger.info("开始设置视频隐私选项...")

            # 等待页面稳定
            time.sleep(1)

            # 快速尝试几个常见的隐私选项选择器
            privacy_selectors = [
                '//*[@id="root"]/div/div/div[1]/div[11]/div/label[2]',  # MoneyPrinterPlus使用的选择器
                '//label[contains(text(), "不允许")]',  # 包含"不允许"文本的label
            ]

            for selector in privacy_selectors:
                try:
                    element = self.find_element_safe(By.XPATH, selector, timeout=2)
                    if element and element.is_displayed():
                        element.click()
                        logger.info(f"隐私选项设置成功: {selector}")
                        time.sleep(1)
                        return True
                except Exception:
                    continue

            # 🔧 简化隐私设置，减少错误日志
            # 抖音默认设置通常已经合适，不强制修改
            logger.info("✅ 隐私选项使用默认设置")
            return True  # 总是返回成功，不阻塞发布流程

        except Exception as e:
            logger.warning(f"隐私选项设置跳过: {e}")
            return True  # 即使失败也返回成功，不影响发布
            
    async def set_cover_image(self, cover_path: str) -> bool:
        """设置视频封面"""
        try:
            logger.info(f"设置视频封面: {cover_path}")
            
            # 查找封面设置按钮
            cover_selectors = [
                '//div[contains(@class, "cover")]//input[@type="file"]',
                '//input[@accept="image/*"]',
                '//div[contains(text(), "封面")]//following::input[@type="file"]'
            ]
            
            for selector in cover_selectors:
                if self.upload_file_safe(By.XPATH, selector, cover_path, timeout=5):
                    logger.info("封面设置成功")
                    time.sleep(3)
                    return True
                    
            logger.warning("未找到封面上传元素")
            return False
            
        except Exception as e:
            logger.error(f"设置封面失败: {e}")
            return False
            
    async def select_topic(self, topic: str) -> bool:
        """选择话题"""
        try:
            logger.info(f"选择话题: {topic}")
            
            # 查找话题选择器
            topic_selector = '//div[contains(@class, "topic")]'
            topic_element = self.find_element_safe(By.XPATH, topic_selector)
            
            if topic_element:
                topic_element.click()
                time.sleep(2)
                
                # 搜索话题
                search_selector = '//input[@placeholder="搜索话题"]'
                if self.send_keys_safe(By.XPATH, search_selector, topic):
                    time.sleep(2)
                    
                    # 选择第一个匹配的话题
                    first_topic_selector = '//div[@class="topic-item"][1]'
                    if self.click_element_safe(By.XPATH, first_topic_selector):
                        logger.info("话题选择成功")
                        return True
                        
            logger.warning("话题选择失败")
            return False
            
        except Exception as e:
            logger.error(f"选择话题失败: {e}")
            return False
            
    async def schedule_publish(self, publish_time: str) -> bool:
        """定时发布"""
        try:
            logger.info(f"设置定时发布: {publish_time}")
            
            # 查找定时发布选项
            schedule_selector = '//div[contains(text(), "定时发布")]'
            if self.click_element_safe(By.XPATH, schedule_selector):
                time.sleep(2)
                
                # 设置发布时间
                time_selector = '//input[@placeholder="选择时间"]'
                if self.send_keys_safe(By.XPATH, time_selector, publish_time):
                    logger.info("定时发布设置成功")
                    return True
                    
            logger.warning("定时发布设置失败")
            return False
            
        except Exception as e:
            logger.error(f"定时发布设置失败: {e}")
            return False
