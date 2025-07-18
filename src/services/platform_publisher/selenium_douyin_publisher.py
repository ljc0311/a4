#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Selenium的抖音发布器
参考MoneyPrinterPlus的实现，使用更稳定的Selenium方案
"""

import time
import asyncio
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
        """🔧 优化：检查抖音登录状态，修复逻辑问题"""
        try:
            # 等待页面加载完成
            await asyncio.sleep(2)

            # 检查页面URL
            current_url = self.driver.current_url
            logger.info(f"🌐 当前页面URL: {current_url}")

            # 检查页面标题
            try:
                page_title = self.driver.title
                logger.info(f"📄 页面标题: {page_title}")
            except:
                page_title = ""

            # 1. 如果在登录页面，返回False
            login_url_keywords = ['login', 'passport', 'sso', 'auth']
            if any(keyword in current_url.lower() for keyword in login_url_keywords):
                logger.warning("❌ 检测到登录页面URL，需要用户登录")
                return False

            # 2. 如果页面标题包含登录信息，返回False
            if '登录' in page_title or 'login' in page_title.lower():
                logger.warning("❌ 页面标题包含登录信息")
                return False

            # 3. 检查是否在抖音域名下
            if not ('douyin.com' in current_url):
                logger.warning("❌ 不在抖音域名下")
                return False

            # 🔧 修复问题1：如果已经在上传页面，直接检查上传元素
            upload_url = "https://creator.douyin.com/creator-micro/content/upload"
            if upload_url in current_url:
                logger.info("📍 已在视频上传页面")

                # 直接检查上传页面的关键元素
                upload_indicators = [
                    '//input[@type="file"]',  # 文件上传输入
                    '//div[contains(@class, "upload")]',  # 上传区域
                    '//input[contains(@placeholder, "标题")]',  # 标题输入框
                ]

                for selector in upload_indicators:
                    element = self.find_element_safe(By.XPATH, selector, timeout=2)
                    if element:
                        logger.info(f"✅ 在上传页面找到关键元素: {selector}")
                        return True

                # 如果在上传页面但找不到关键元素，可能需要登录
                logger.warning("⚠️ 在上传页面但未找到关键元素，可能需要登录")
                return False

            # 4. 🔧 修复问题1：如果在其他创作者页面，跳转到上传页面
            if 'creator.douyin.com' in current_url:
                logger.info("📍 在抖音创作者中心，准备跳转到上传页面")

                # 🔧 修复问题2：不再查找登录按钮，直接跳转
                try:
                    logger.info(f"🔄 跳转到上传页面: {upload_url}")
                    self.driver.get(upload_url)
                    await asyncio.sleep(3)

                    # 检查跳转后的页面
                    new_url = self.driver.current_url
                    if upload_url in new_url:
                        logger.info("✅ 成功跳转到上传页面")

                        # 检查上传页面元素
                        upload_element = self.find_element_safe(By.XPATH, '//input[@type="file"]', timeout=5)
                        if upload_element:
                            logger.info("✅ 上传页面加载成功，用户已登录")
                            return True
                        else:
                            logger.warning("❌ 上传页面加载失败，可能需要登录")
                            return False
                    else:
                        logger.warning(f"❌ 跳转失败，当前页面: {new_url}")
                        return False

                except Exception as e:
                    logger.error(f"跳转到上传页面失败: {e}")
                    return False

            # 5. 如果在其他抖音页面，尝试跳转到创作者中心
            elif 'douyin.com' in current_url:
                logger.info("📍 在抖音其他页面，尝试跳转到创作者中心")
                try:
                    self.driver.get("https://creator.douyin.com/")
                    await asyncio.sleep(3)

                    # 递归检查登录状态
                    return await self._check_login_status()

                except Exception as e:
                    logger.error(f"跳转到创作者中心失败: {e}")
                    return False

            logger.warning("❌ 不在抖音相关页面")
            return False

        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return False
            
    async def _publish_video_impl(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """🔧 修复：抖音视频发布实现，调整流程顺序"""
        try:
            # 检查是否为模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 模拟模式：模拟抖音视频发布过程")

                # 模拟发布过程
                title = video_info.get('title', '')
                description = video_info.get('description', '')
                video_path = video_info.get('video_path', '')

                logger.info(f"📝 模拟设置标题: {title}")
                logger.info(f"📄 模拟设置描述: {description}")
                logger.info(f"📹 模拟上传视频: {video_path}")
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

            # 🔧 修复问题3：添加进度回调
            progress_callback = video_info.get('progress_callback')
            if progress_callback:
                progress_callback("准备发布视频...", 10)

            # 🔧 修复：正确的抖音发布流程顺序
            # 根据抖音界面实际情况：必须先上传视频文件，然后才会跳转到填写标题、描述的界面

            # 1. 上传视频文件
            if progress_callback:
                progress_callback("准备上传视频文件...", 15)

            video_path = video_info.get('video_path')
            if not video_path:
                return {'success': False, 'error': '视频路径不能为空'}

            logger.info(f"开始上传视频文件: {video_path}")

            # 多种文件上传选择器，提高成功率
            file_input_selectors = [
                '//input[@type="file"]',
                '//input[@accept="video/*"]',
                '//div[contains(@class, "upload")]//input[@type="file"]',
                '//input[contains(@class, "upload-input")]'
            ]

            upload_success = False
            for i, selector in enumerate(file_input_selectors):
                logger.info(f"尝试使用选择器上传: {selector}")
                if progress_callback:
                    progress_callback(f"尝试上传方式 {i+1}/{len(file_input_selectors)}", 20 + i * 5)

                if self.upload_file_safe(By.XPATH, selector, video_path, timeout=10):
                    upload_success = True
                    logger.info("✅ 视频文件上传成功")
                    if progress_callback:
                        progress_callback("视频文件上传成功", 35)
                    break
                time.sleep(1)

            if not upload_success:
                if progress_callback:
                    progress_callback("视频上传失败", 0)
                return {'success': False, 'error': '视频上传失败 - 未找到有效的上传元素'}

            # 🔧 修复：等待视频上传完成，重点检测手机预览
            logger.info("等待视频上传完成...")
            if progress_callback:
                progress_callback("等待视频上传完成...", 40)

            upload_complete = self._wait_for_upload_complete_enhanced(timeout=300, progress_callback=progress_callback)  # 5分钟超时

            if not upload_complete:
                if progress_callback:
                    progress_callback("视频上传超时", 0)
                return {'success': False, 'error': '视频上传超时或失败'}

            # 2. 设置视频标题
            if progress_callback:
                progress_callback("设置视频标题...", 75)

            title = video_info.get('title', '')
            if title:
                logger.info(f"设置标题: {title}")
                title_selector = '//input[@class="semi-input semi-input-default"]'
                if not self.send_keys_safe(By.XPATH, title_selector, title[:30]):  # 抖音标题限制30字
                    logger.warning("标题设置失败")
                else:
                    logger.info("✅ 标题设置成功")
                time.sleep(2)

            # 3. 设置视频描述（增强版）
            if progress_callback:
                progress_callback("设置视频描述...", 80)

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

            if progress_callback:
                progress_callback("准备发布视频...", 85)
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
            if progress_callback:
                progress_callback("查找发布按钮...", 85)

            # 等待页面稳定
            time.sleep(2)

            # 智能检测并点击发布按钮
            publish_success = self._smart_find_publish_button()

            if publish_success:
                # 等待发布完成
                logger.info("发布按钮点击成功，等待发布完成...")
                if progress_callback:
                    progress_callback("发布按钮已点击，等待发布完成...", 90)

                time.sleep(5)  # 增加等待时间确保发布完成

                # 🔧 处理可能的错误弹窗
                self._handle_error_dialogs()

                # 🔧 修复问题4：检查发布结果
                if progress_callback:
                    progress_callback("检查发布结果...", 95)

                publish_result = self._check_publish_result()
                if publish_result['success']:
                    logger.info("✅ 视频发布成功！")
                    if progress_callback:
                        progress_callback("视频发布成功！", 100)
                    return {'success': True, 'message': publish_result['message']}
                else:
                    logger.info("✅ 视频已提交发布，请稍后查看发布状态")
                    if progress_callback:
                        progress_callback("视频已提交发布", 100)
                    return {'success': True, 'message': '视频已提交发布，请稍后查看发布状态'}
            else:
                logger.warning("❌ 自动发布失败，尝试备用方案...")
                if progress_callback:
                    progress_callback("尝试备用发布方案...", 87)

                # 备用方案：尝试更激进的发布按钮检测
                backup_success = self._backup_publish_attempt()
                if backup_success:
                    logger.info("✅ 备用发布方案成功！")
                    if progress_callback:
                        progress_callback("备用发布方案成功！", 100)
                    return {'success': True, 'message': '视频发布成功（备用方案）'}
                else:
                    logger.error("❌ 所有自动发布方案都失败")
                    if progress_callback:
                        progress_callback("发布失败", 0)
                    return {'success': False, 'error': '自动发布失败，请检查页面状态'}
                
        except Exception as e:
            logger.error(f"抖音视频发布失败: {e}")
            return {'success': False, 'error': str(e)}

    def _smart_find_publish_button(self) -> bool:
        """🔧 修复：智能查找并点击发布按钮，增强检测逻辑"""
        try:
            logger.info("开始智能检测发布按钮...")

            # 等待页面稳定
            time.sleep(2)

            # 第一轮：使用最精确的发布按钮选择器
            primary_selectors = [
                # 抖音创作者中心最常用的发布按钮选择器
                '//button[text()="发布"]',
                '//button[contains(text(), "发布") and contains(@class, "semi-button-primary")]',
                '//button[contains(@class, "semi-button-primary") and contains(text(), "发布")]',
                '//button[@class="semi-button semi-button-primary semi-button-size-large semi-button-block"]',

                # 备用精确选择器
                '//button[contains(text(), "发布")]',
                '//span[text()="发布"]/parent::button',
                '//div[text()="发布"]/parent::button',

                # 通过按钮位置和样式查找
                '//div[contains(@class, "publish")]//button[contains(@class, "primary")]',
                '//div[contains(@class, "footer")]//button[contains(text(), "发布")]',
                '//div[contains(@class, "bottom")]//button[contains(text(), "发布")]'
            ]

            for i, selector in enumerate(primary_selectors):
                logger.info(f"尝试主要选择器 {i+1}/{len(primary_selectors)}: {selector}")
                element = self.find_element_safe(By.XPATH, selector, timeout=3)
                if element:
                    try:
                        # 检查元素是否真正可用
                        if element.is_enabled() and element.is_displayed():
                            # 滚动到元素可见位置
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                            time.sleep(1)

                            # 高亮元素便于调试
                            self.driver.execute_script("arguments[0].style.border='3px solid red';", element)
                            time.sleep(0.5)

                            # 先尝试普通点击
                            element.click()
                            logger.info(f"✅ 发布按钮点击成功: {selector}")
                            return True
                        else:
                            logger.info(f"按钮不可用或不可见: enabled={element.is_enabled()}, displayed={element.is_displayed()}")
                    except Exception as e:
                        try:
                            # 如果普通点击失败，尝试JavaScript点击
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info(f"✅ 发布按钮JavaScript点击成功: {selector}")
                            return True
                        except Exception as e2:
                            logger.debug(f"JavaScript点击也失败: {e2}")
                            continue
                else:
                    logger.debug(f"未找到元素: {selector}")

            # 第二轮：智能查找所有按钮并分析
            logger.info("第二轮：智能分析所有按钮元素...")
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            logger.info(f"页面上共找到 {len(all_buttons)} 个按钮")

            # 按优先级排序按钮
            publish_buttons = []
            for button in all_buttons:
                try:
                    if button.is_displayed() and button.is_enabled():
                        button_text = button.text.strip()
                        button_class = button.get_attribute("class") or ""

                        # 检查是否是发布相关按钮
                        if any(keyword in button_text for keyword in ["发布", "立即发布", "确认发布", "提交", "完成"]):
                            priority = 0

                            # 计算优先级
                            if "发布" in button_text:
                                priority += 10
                            if "primary" in button_class:
                                priority += 5
                            if "semi-button-primary" in button_class:
                                priority += 8
                            if button_text == "发布":
                                priority += 15

                            publish_buttons.append((priority, button, button_text, button_class))
                            logger.info(f"发现发布按钮候选: 文本='{button_text}', 类名='{button_class}', 优先级={priority}")

                except Exception as e:
                    logger.debug(f"分析按钮失败: {e}")
                    continue

            # 按优先级排序并尝试点击
            publish_buttons.sort(key=lambda x: x[0], reverse=True)

            for priority, button, text, classes in publish_buttons:
                try:
                    logger.info(f"尝试点击高优先级发布按钮: '{text}' (优先级: {priority})")

                    # 滚动到按钮位置
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                    time.sleep(1)

                    # 高亮按钮
                    self.driver.execute_script("arguments[0].style.border='3px solid green';", button)
                    time.sleep(0.5)

                    # 使用JavaScript点击，更可靠
                    self.driver.execute_script("arguments[0].click();", button)
                    logger.info(f"✅ 发布按钮点击成功: '{text}'")
                    return True

                except Exception as e:
                    logger.debug(f"点击按钮失败: {e}")
                    continue

            # 第三轮：查找包含发布文本的所有可点击元素
            logger.info("第三轮：查找包含发布文本的可点击元素...")
            publish_text_selectors = [
                "//*[text()='发布']",
                "//*[contains(text(), '发布')]",
                "//*[text()='立即发布']",
                "//*[text()='确认发布']"
            ]

            for selector in publish_text_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            tag_name = element.tag_name.lower()
                            if tag_name in ['button', 'a', 'div', 'span']:
                                logger.info(f"尝试点击发布元素: {tag_name} - '{element.text}'")
                                self.driver.execute_script("arguments[0].click();", element)
                                logger.info(f"✅ 发布元素点击成功")
                                return True
                    except Exception as e:
                        logger.debug(f"点击发布元素失败: {e}")
                        continue

            # 调试信息：显示页面状态
            logger.warning("⚠️ 未找到可用的发布按钮，显示调试信息...")
            try:
                # 显示当前页面URL
                logger.info(f"当前页面URL: {self.driver.current_url}")

                # 显示页面标题
                logger.info(f"页面标题: {self.driver.title}")

                # 显示前10个按钮的详细信息
                for i, button in enumerate(all_buttons[:10]):
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

            logger.error("❌ 未找到可用的发布按钮")
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

    def _check_publish_result(self) -> dict:
        """🔧 修复问题4：检查发布结果，返回详细信息"""
        try:
            logger.info("开始检查发布结果...")

            # 等待页面响应
            time.sleep(3)

            # 检查URL变化
            current_url = self.driver.current_url
            logger.info(f"当前页面URL: {current_url}")

            # 1. 检查是否跳转到成功页面
            success_urls = [
                'creator-micro/content/manage',  # 内容管理页面
                'creator-micro/home',  # 创作者首页
                'success',  # 成功页面
                'published'  # 已发布页面
            ]

            for success_url in success_urls:
                if success_url in current_url:
                    logger.info(f"✅ 检测到成功页面URL: {success_url}")
                    return {'success': True, 'message': f'发布成功，已跳转到{success_url}页面'}

            # 2. 检查成功提示文本
            success_indicators = [
                "发布成功",
                "提交成功",
                "上传成功",
                "发布中",
                "审核中",
                "等待审核",
                "已发布",
                "发布完成"
            ]

            page_source = self.driver.page_source
            for indicator in success_indicators:
                if indicator in page_source:
                    logger.info(f"✅ 在页面内容中找到成功指示器: {indicator}")
                    return {'success': True, 'message': f'发布成功: {indicator}'}

                # 也检查元素
                elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{indicator}')]")
                if elements:
                    logger.info(f"✅ 找到成功指示器元素: {indicator}")
                    return {'success': True, 'message': f'发布成功: {indicator}'}

            # 3. 检查是否还在上传页面
            upload_indicators = [
                '//input[@type="file"]',
                '//div[@data-placeholder="添加作品简介"]',
                '//button[contains(text(), "发布")]'
            ]

            still_on_upload = False
            for selector in upload_indicators:
                if self.find_element_safe(By.XPATH, selector, timeout=1):
                    still_on_upload = True
                    logger.info(f"仍在上传页面，找到元素: {selector}")
                    break

            if not still_on_upload:
                logger.info("✅ 已离开上传页面，发布可能成功")
                return {'success': True, 'message': '已离开上传页面，发布可能成功'}

            # 4. 检查错误信息
            error_indicators = [
                "发布失败",
                "上传失败",
                "网络错误",
                "格式不支持",
                "文件过大",
                "审核不通过"
            ]

            for error in error_indicators:
                if error in page_source:
                    logger.warning(f"❌ 发现错误指示器: {error}")
                    return {'success': False, 'message': f'发布失败: {error}'}

            # 5. 默认情况：无法确定结果
            logger.info("⚠️ 无法确定发布结果，可能仍在处理中")
            return {'success': False, 'message': '无法确定发布结果，请手动检查'}

        except Exception as e:
            logger.error(f"检查发布结果失败: {e}")
            return {'success': False, 'message': f'检查发布结果失败: {e}'}

    def _wait_for_upload_complete_enhanced(self, timeout: int = 300, progress_callback=None) -> bool:
        """🔧 修复：增强版上传完成检测，重点检测手机预览中的视频内容"""
        try:
            logger.info("开始增强版上传完成检测...")
            start_time = time.time()
            last_progress_update = 0

            while time.time() - start_time < timeout:
                try:
                    elapsed_time = time.time() - start_time
                    progress_percent = min(40 + (elapsed_time / timeout) * 30, 70)  # 40%-70%

                    # 更新进度回调
                    if progress_callback and progress_percent - last_progress_update >= 5:
                        progress_callback(f"检测上传状态... ({int(elapsed_time)}s)", int(progress_percent))
                        last_progress_update = progress_percent

                    # 🔧 修复：重点检测右侧手机预览中的视频内容
                    # 当手机预览显示视频内容时，说明上传已完成
                    mobile_preview_selectors = [
                        # 手机预览区域的视频元素
                        '//div[contains(@class, "phone-preview")]//video',
                        '//div[contains(@class, "mobile-preview")]//video',
                        '//div[contains(@class, "preview-phone")]//video',
                        '//div[contains(@class, "phone")]//video',
                        # 手机预览区域的canvas元素（视频渲染）
                        '//div[contains(@class, "phone-preview")]//canvas',
                        '//div[contains(@class, "mobile-preview")]//canvas',
                        '//div[contains(@class, "phone")]//canvas',
                        # 通用视频预览元素
                        '//video[contains(@class, "preview")]',
                        '//canvas[contains(@class, "preview")]',
                        # 抖音特有的预览元素
                        '//div[contains(@class, "video-preview")]//video',
                        '//div[contains(@class, "video-preview")]//canvas',
                        # 更通用的视频元素
                        '//video[@src]',
                        '//video[not(@src="")]'
                    ]

                    video_preview_found = False
                    for selector in mobile_preview_selectors:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        if elements:
                            # 检查视频元素是否有内容
                            for element in elements:
                                try:
                                    # 检查视频是否有duration（说明视频已加载）
                                    if element.tag_name == 'video':
                                        duration = self.driver.execute_script("return arguments[0].duration;", element)
                                        readyState = self.driver.execute_script("return arguments[0].readyState;", element)
                                        if duration and duration > 0:
                                            logger.info(f"✅ 检测到手机预览中的视频内容，时长: {duration}秒，状态: {readyState}")
                                            video_preview_found = True
                                            break
                                        elif readyState >= 2:  # HAVE_CURRENT_DATA or higher
                                            logger.info(f"✅ 检测到视频数据已加载，状态: {readyState}")
                                            video_preview_found = True
                                            break
                                    # 检查canvas是否有内容
                                    elif element.tag_name == 'canvas':
                                        width = self.driver.execute_script("return arguments[0].width;", element)
                                        height = self.driver.execute_script("return arguments[0].height;", element)
                                        if width > 0 and height > 0:
                                            logger.info(f"✅ 检测到手机预览中的视频画布，尺寸: {width}x{height}")
                                            video_preview_found = True
                                            break
                                except Exception as e:
                                    logger.debug(f"检查预览元素时出错: {e}")
                                    continue

                        if video_preview_found:
                            break

                    if video_preview_found:
                        # 额外等待确保上传完全完成
                        logger.info("发现视频预览，等待3秒确保上传完成...")
                        time.sleep(3)

                        # 再次确认视频预览仍然存在
                        final_check = False
                        for selector in mobile_preview_selectors[:5]:  # 检查前5个最可靠的选择器
                            elements = self.driver.find_elements(By.XPATH, selector)
                            if elements:
                                final_check = True
                                break

                        if final_check:
                            logger.info("✅ 视频上传完成确认")
                            return True
                        else:
                            logger.info("视频预览消失，继续等待...")

                    # 检查是否有错误信息
                    error_selectors = [
                        '//div[contains(text(), "上传失败")]',
                        '//div[contains(text(), "错误")]',
                        '//div[contains(text(), "失败")]',
                        '//span[contains(text(), "上传失败")]',
                        '//div[contains(@class, "error")]'
                    ]

                    for error_selector in error_selectors:
                        error_elements = self.driver.find_elements(By.XPATH, error_selector)
                        if error_elements:
                            logger.error("发现上传错误信息")
                            return False

                    # 等待一段时间后再次检查
                    time.sleep(4)  # 增加检测间隔

                except Exception as e:
                    logger.debug(f"等待上传完成时出现异常: {e}")
                    time.sleep(3)

            logger.warning("等待上传完成超时")
            return False

        except Exception as e:
            logger.error(f"等待上传完成失败: {e}")
            return False

    def _wait_for_upload_complete(self, timeout: int = 300, progress_callback=None) -> bool:
        """等待视频上传完成（调用增强版方法）"""
        return self._wait_for_upload_complete_enhanced(timeout, progress_callback)

    def _handle_error_dialogs(self):
        """🔧 修复：检查发布后的页面状态，抖音发布成功后会直接跳转，不会显示确认弹窗"""
        try:
            # 等待页面响应
            time.sleep(2)

            # 检查当前URL，如果已跳转到作品管理页面，说明发布成功
            current_url = self.driver.current_url
            if 'creator-micro/content/manage' in current_url:
                logger.info("✅ 已跳转到作品管理页面，发布成功")
                return

            # 只检查真正的错误弹窗（不检查不存在的确认弹窗）
            error_dialog_selectors = [
                '//div[contains(@class, "error")]//button',
                '//div[contains(@class, "fail")]//button',
                '//div[contains(text(), "失败")]//button',
                '//div[contains(text(), "错误")]//button'
            ]

            for selector in error_dialog_selectors:
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
