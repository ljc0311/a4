#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动登录状态检测器
自动检测浏览器中的平台登录状态并保存
"""

import time
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.services.platform_publisher.login_manager import login_manager
from src.services.platform_publisher.integrated_browser_manager import IntegratedBrowserManager
from src.utils.logger import logger


class AutoLoginDetector:
    """自动登录状态检测器"""
    
    def __init__(self):
        self.browser_manager = IntegratedBrowserManager()
        
        # 平台登录检测配置
        self.platform_configs = {
            'douyin': {
                'name': '抖音',
                'url': 'https://creator.douyin.com',
                'login_indicators': [
                    {'type': 'css', 'selector': '.semi-avatar', 'method': 'presence'},
                    {'type': 'css', 'selector': '.user-info', 'method': 'presence'},
                    {'type': 'text', 'text': '登录', 'method': 'absence'}
                ],
                'user_info_selectors': {
                    'avatar': '.semi-avatar img',
                    'username': '.user-name, .username'
                }
            },
            'kuaishou': {
                'name': '快手',
                'url': 'https://cp.kuaishou.com/article/publish/video',
                'login_indicators': [
                    {'type': 'css', 'selector': '.user-avatar', 'method': 'presence'},
                    {'type': 'css', 'selector': '.avatar', 'method': 'presence'},
                    {'type': 'text', 'text': '登录', 'method': 'absence'}
                ],
                'user_info_selectors': {
                    'avatar': '.user-avatar img, .avatar img',
                    'username': '.user-name, .username'
                }
            },
            'bilibili': {
                'name': 'B站',
                'url': 'https://member.bilibili.com/platform/upload/video/frame',
                'login_indicators': [
                    {'type': 'css', 'selector': '.user-info', 'method': 'presence'},
                    {'type': 'css', 'selector': '.nav-user-info', 'method': 'presence'},
                    {'type': 'text', 'text': '登录', 'method': 'absence'}
                ],
                'user_info_selectors': {
                    'avatar': '.user-info img, .nav-user-info img',
                    'username': '.user-info .name, .nav-user-info .name'
                }
            },
            'xiaohongshu': {
                'name': '小红书',
                'url': 'https://creator.xiaohongshu.com/publish/publish',
                'login_indicators': [
                    {'type': 'css', 'selector': '.avatar', 'method': 'presence'},
                    {'type': 'css', 'selector': '.user-avatar', 'method': 'presence'},
                    {'type': 'text', 'text': '登录', 'method': 'absence'}
                ],
                'user_info_selectors': {
                    'avatar': '.avatar img, .user-avatar img',
                    'username': '.username, .user-name'
                }
            }
        }
        
    def create_driver(self, browser_config: Dict[str, Any]) -> Optional[webdriver.Chrome]:
        """创建浏览器驱动 - 连接到现有浏览器实例"""
        try:
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            options = Options()

            # 连接到现有的浏览器实例（关键配置）
            debug_info = browser_config.get('debug_info', {})
            debug_port = debug_info.get('port', browser_config.get('debug_port', 9222))

            logger.info(f"🔗 连接到现有浏览器实例: 127.0.0.1:{debug_port}")
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")

            # 不启动新的浏览器实例
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")

            # 创建服务
            selenium_config = browser_config.get('selenium_config', {})
            driver_path = selenium_config.get('driver_location') or browser_config.get('driver_path')

            if driver_path and os.path.exists(driver_path):
                logger.info(f"使用指定的ChromeDriver: {driver_path}")
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                logger.info("使用系统PATH中的ChromeDriver")
                driver = webdriver.Chrome(options=options)

            # 验证连接
            try:
                current_url = driver.current_url
                logger.info(f"✅ 成功连接到现有浏览器，当前页面: {current_url}")
                return driver
            except Exception as e:
                logger.error(f"验证浏览器连接失败: {e}")
                driver.quit()
                return None

        except Exception as e:
            logger.error(f"创建浏览器驱动失败: {e}")
            return None
            
    def check_platform_login_status(self, platform: str, driver: webdriver.Chrome) -> Dict[str, Any]:
        """检查单个平台的登录状态"""
        try:
            if platform not in self.platform_configs:
                return {'is_logged_in': False, 'error': f'不支持的平台: {platform}'}

            config = self.platform_configs[platform]
            platform_url = config['url']

            logger.info(f"正在检查{config['name']}登录状态...")

            # 首先检查是否已经在目标平台页面
            current_url = driver.current_url
            is_on_platform = self._is_on_platform_domain(current_url, platform_url)

            if is_on_platform:
                logger.info(f"当前已在{config['name']}页面，直接检测登录状态")
            else:
                # 检查是否有现有标签页已经打开了该平台
                existing_tab = self._find_platform_tab(driver, platform_url)
                if existing_tab:
                    logger.info(f"找到现有{config['name']}标签页，切换到该标签页")
                    driver.switch_to.window(existing_tab)
                else:
                    # 在新标签页中打开平台页面
                    logger.info(f"在新标签页中打开{config['name']}页面")
                    driver.execute_script(f"window.open('{platform_url}', '_blank');")
                    driver.switch_to.window(driver.window_handles[-1])

            # 等待页面加载
            time.sleep(3)

            # 检查登录指示器
            is_logged_in = self._check_login_indicators(driver, config['login_indicators'])

            result = {
                'platform': platform,
                'platform_name': config['name'],
                'is_logged_in': is_logged_in,
                'check_time': datetime.now().isoformat(),
                'url': config['url']
            }

            # 如果已登录，提取用户信息
            if is_logged_in:
                user_info = self._extract_user_info(driver, config.get('user_info_selectors', {}))
                result['user_info'] = user_info

                # 获取cookies
                cookies = driver.get_cookies()
                result['cookies'] = cookies

            return result

        except Exception as e:
            logger.error(f"检查{platform}登录状态失败: {e}")
            return {
                'platform': platform,
                'is_logged_in': False,
                'error': str(e),
                'check_time': datetime.now().isoformat()
            }

    def _is_on_platform_domain(self, current_url: str, platform_url: str) -> bool:
        """检查当前是否在平台域名下"""
        try:
            from urllib.parse import urlparse
            current_domain = urlparse(current_url).netloc
            platform_domain = urlparse(platform_url).netloc
            is_match = current_domain == platform_domain
            logger.info(f"🌐 域名匹配检查: {current_domain} vs {platform_domain} = {'匹配' if is_match else '不匹配'}")
            return is_match
        except Exception as e:
            logger.warning(f"⚠️ 域名匹配检查失败: {e}")
            return False

    def _find_platform_tab(self, driver: webdriver.Chrome, platform_url: str) -> Optional[str]:
        """查找已打开的平台标签页"""
        try:
            from urllib.parse import urlparse
            platform_domain = urlparse(platform_url).netloc

            current_window = driver.current_window_handle

            for window_handle in driver.window_handles:
                try:
                    driver.switch_to.window(window_handle)
                    current_url = driver.current_url
                    current_domain = urlparse(current_url).netloc

                    if current_domain == platform_domain:
                        return window_handle
                except:
                    continue

            # 恢复到原始窗口
            driver.switch_to.window(current_window)
            return None

        except Exception as e:
            logger.warning(f"查找平台标签页失败: {e}")
            return None
            
    def _check_login_indicators(self, driver: webdriver.Chrome, indicators: List[Dict]) -> bool:
        """检查登录指示器"""
        try:
            logger.info(f"🔍 开始检查登录指示器，共{len(indicators)}个指示器")

            for i, indicator in enumerate(indicators, 1):
                indicator_type = indicator['type']
                method = indicator['method']
                logger.info(f"检查指示器 {i}/{len(indicators)}: {indicator_type} - {method}")

                if indicator_type == 'css':
                    selector = indicator['selector']
                    logger.info(f"🎯 查找CSS选择器: {selector}")
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        logger.info(f"找到 {len(elements)} 个匹配元素")

                        if method == 'presence' and elements:
                            logger.info(f"✅ 找到登录指示器: {selector}")
                            return True
                        elif method == 'absence' and not elements:
                            logger.info(f"✅ 确认元素不存在: {selector}")
                            continue
                        else:
                            logger.info(f"❌ 指示器条件不满足: {selector} ({method})")
                    except Exception as e:
                        logger.warning(f"⚠️ 查找CSS选择器失败: {selector}, 错误: {e}")
                        continue

                elif indicator_type == 'text':
                    text = indicator['text']
                    logger.info(f"🔤 查找文本内容: '{text}'")
                    try:
                        page_source = driver.page_source
                        text_found = text in page_source
                        logger.info(f"文本查找结果: {'找到' if text_found else '未找到'}")

                        if method == 'presence' and text_found:
                            logger.info(f"✅ 找到登录指示文本: '{text}'")
                            return True
                        elif method == 'absence' and not text_found:
                            logger.info(f"✅ 确认文本不存在: '{text}'")
                            continue
                        else:
                            logger.info(f"❌ 文本指示器条件不满足: '{text}' ({method})")
                    except Exception as e:
                        logger.warning(f"⚠️ 查找文本内容失败: '{text}', 错误: {e}")
                        continue

            logger.info("❌ 所有登录指示器检查完毕，未找到登录状态")
            return False

        except Exception as e:
            logger.error(f"❌ 检查登录指示器失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
            
    def _extract_user_info(self, driver: webdriver.Chrome, selectors: Dict[str, str]) -> Dict[str, Any]:
        """提取用户信息"""
        user_info = {}
        
        try:
            for info_type, selector in selectors.items():
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    if info_type == 'avatar':
                        user_info['avatar_url'] = element.get_attribute('src')
                    elif info_type == 'username':
                        user_info['username'] = element.text.strip()
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"提取用户信息失败: {e}")
            
        return user_info
        
    def detect_all_platforms(self, browser_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """检测所有平台的登录状态"""
        results = {}
        driver = None
        original_window = None

        try:
            # 创建浏览器驱动
            driver = self.create_driver(browser_config)
            if not driver:
                return {'error': '无法连接到现有浏览器实例，请确保浏览器调试模式正常运行'}

            # 记录原始窗口
            original_window = driver.current_window_handle
            logger.info(f"记录原始窗口: {original_window}")

            # 检查每个平台
            for platform in self.platform_configs.keys():
                try:
                    result = self.check_platform_login_status(platform, driver)
                    results[platform] = result

                    # 如果检测到已登录，自动保存登录信息
                    if result.get('is_logged_in', False):
                        self._save_login_info(platform, result)

                except Exception as e:
                    logger.error(f"检测{platform}失败: {e}")
                    results[platform] = {
                        'platform': platform,
                        'is_logged_in': False,
                        'error': str(e)
                    }

                # 短暂延迟，避免请求过快
                time.sleep(1)

        except Exception as e:
            logger.error(f"检测登录状态失败: {e}")
            results['error'] = str(e)

        finally:
            if driver:
                try:
                    # 恢复到原始窗口
                    if original_window and original_window in driver.window_handles:
                        driver.switch_to.window(original_window)
                        logger.info("已恢复到原始窗口")

                    # 不要quit驱动，因为这会关闭用户的浏览器
                    # driver.quit()  # 注释掉这行
                    logger.info("保持浏览器连接，不关闭用户浏览器")

                except Exception as e:
                    logger.warning(f"恢复浏览器状态时出错: {e}")

        return results
        
    def _save_login_info(self, platform: str, result: Dict[str, Any]):
        """保存登录信息到登录管理器"""
        try:
            user_info = result.get('user_info', {})
            user_info.update({
                'platform': platform,
                'detected_at': result.get('check_time'),
                'detection_method': 'auto_detector'
            })
            
            cookies = result.get('cookies', [])
            
            # 保存到登录管理器
            success = login_manager.save_login_info(platform, user_info, cookies)
            
            if success:
                platform_name = self.platform_configs[platform]['name']
                logger.info(f"✅ 自动保存{platform_name}登录信息成功")
            else:
                logger.error(f"❌ 自动保存{platform}登录信息失败")
                
        except Exception as e:
            logger.error(f"保存{platform}登录信息失败: {e}")
            
    def quick_detect_logged_platforms(self, browser_config: Dict[str, Any]) -> List[str]:
        """快速检测已登录的平台（仅返回平台列表）"""
        try:
            results = self.detect_all_platforms(browser_config)
            
            logged_platforms = []
            for platform, result in results.items():
                if isinstance(result, dict) and result.get('is_logged_in', False):
                    logged_platforms.append(platform)
                    
            return logged_platforms
            
        except Exception as e:
            logger.error(f"快速检测登录状态失败: {e}")
            return []

    def detect_current_page_login(self, browser_config: Dict[str, Any]) -> Dict[str, Any]:
        """检测当前页面的登录状态（不打开新窗口）"""
        driver = None

        try:
            logger.info("🔍 开始检测当前页面登录状态...")

            # 创建浏览器驱动
            logger.info("📡 正在连接到浏览器实例...")
            driver = self.create_driver(browser_config)
            if not driver:
                logger.error("❌ 无法连接到现有浏览器实例")
                return {'error': '无法连接到现有浏览器实例'}

            logger.info("✅ 浏览器连接成功，获取当前页面信息...")
            current_url = driver.current_url
            logger.info(f"📄 当前页面URL: {current_url}")

            # 检查当前页面属于哪个平台
            logger.info("🔎 正在识别平台类型...")
            detected_platform = None
            for platform, config in self.platform_configs.items():
                logger.info(f"检查是否为{config['name']}平台...")
                if self._is_on_platform_domain(current_url, config['url']):
                    detected_platform = platform
                    logger.info(f"✅ 识别为{config['name']}平台")
                    break

            if detected_platform:
                logger.info(f"🎯 检测到当前页面为{self.platform_configs[detected_platform]['name']}")

                # 检查登录状态
                logger.info("🔐 正在检查登录状态...")
                config = self.platform_configs[detected_platform]
                is_logged_in = self._check_login_indicators(driver, config['login_indicators'])
                logger.info(f"登录状态检查结果: {'已登录' if is_logged_in else '未登录'}")

                result = {
                    'platform': detected_platform,
                    'platform_name': config['name'],
                    'is_logged_in': is_logged_in,
                    'check_time': datetime.now().isoformat(),
                    'url': current_url
                }

                if is_logged_in:
                    logger.info("👤 正在提取用户信息...")
                    user_info = self._extract_user_info(driver, config.get('user_info_selectors', {}))
                    result['user_info'] = user_info

                    logger.info("🍪 正在获取登录Cookie...")
                    cookies = driver.get_cookies()
                    result['cookies'] = cookies

                    # 自动保存登录信息
                    logger.info("💾 正在保存登录信息...")
                    self._save_login_info(detected_platform, result)
                    logger.info("✅ 登录信息保存完成")

                logger.info("🎉 当前页面检测完成")
                return {detected_platform: result}
            else:
                logger.info("ℹ️ 当前页面不是支持的平台页面")
                return {'info': '当前页面不是支持的平台页面'}

        except Exception as e:
            logger.error(f"❌ 检测当前页面登录状态失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return {'error': str(e)}

        finally:
            # 不关闭驱动，保持用户浏览器状态
            logger.info("🔚 检测流程结束，保持浏览器状态")
            pass


# 全局自动登录检测器实例
auto_login_detector = AutoLoginDetector()
