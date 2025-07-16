#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成浏览器管理器
自动处理浏览器安装、配置和启动，减少用户依赖
"""

import os
import sys
import json
import time
import shutil
import zipfile
import requests
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from src.utils.logger import logger


class IntegratedBrowserManager:
    """集成浏览器管理器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.browsers_dir = self.project_root / "browsers"
        self.drivers_dir = self.project_root / "drivers"
        self.user_data_dir = self.project_root / "browser_data"
        self.config_file = self.project_root / "browser_config.json"

        # 确保目录存在
        self.browsers_dir.mkdir(exist_ok=True)
        self.drivers_dir.mkdir(exist_ok=True)
        self.user_data_dir.mkdir(exist_ok=True)

        # 加载保存的配置
        self.saved_config = self._load_browser_config()
        
        self.supported_browsers = {
            'chrome': {
                'name': 'Google Chrome',
                'portable_url': 'https://dl.google.com/chrome/install/googlechromeportable.exe',
                'driver_base_url': 'https://chromedriver.storage.googleapis.com',
                'debug_port': 9222
            },
            'edge': {
                'name': 'Microsoft Edge',
                'portable_url': None,  # Edge通常预装在Windows上
                'driver_base_url': 'https://msedgedriver.azureedge.net',
                'debug_port': 9223
            },
            'firefox': {
                'name': 'Mozilla Firefox',
                'portable_url': 'https://download.mozilla.org/?product=firefox-latest&os=win64&lang=zh-CN',
                'driver_base_url': 'https://github.com/mozilla/geckodriver/releases',
                'debug_port': 2828
            }
        }
        
    def detect_system_browsers(self) -> Dict[str, Dict[str, Any]]:
        """检测系统已安装的浏览器"""
        detected = {}
        
        # Chrome检测路径
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                detected['chrome'] = {
                    'path': path,
                    'version': self._get_browser_version(path),
                    'type': 'system'
                }
                break
                
        # Edge检测路径
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]
        
        for path in edge_paths:
            if os.path.exists(path):
                detected['edge'] = {
                    'path': path,
                    'version': self._get_browser_version(path),
                    'type': 'system'
                }
                break
                
        # Firefox检测路径
        firefox_paths = [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
        ]
        
        for path in firefox_paths:
            if os.path.exists(path):
                detected['firefox'] = {
                    'path': path,
                    'version': self._get_browser_version(path),
                    'type': 'system'
                }
                break
                
        return detected
        
    def _get_browser_version(self, browser_path: str) -> Optional[str]:
        """获取浏览器版本"""
        try:
            # 减少超时时间，避免长时间等待
            timeout = 5

            if 'chrome' in browser_path.lower():
                result = subprocess.run([browser_path, '--version'],
                                      capture_output=True, text=True, timeout=timeout)
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    logger.info(f"检测到Chrome版本: {version}")
                    return version
            elif 'msedge' in browser_path.lower():
                result = subprocess.run([browser_path, '--version'],
                                      capture_output=True, text=True, timeout=timeout)
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    logger.info(f"检测到Edge版本: {version}")
                    return version
            elif 'firefox' in browser_path.lower():
                result = subprocess.run([browser_path, '--version'],
                                      capture_output=True, text=True, timeout=timeout)
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    logger.info(f"检测到Firefox版本: {version}")
                    return version
        except subprocess.TimeoutExpired:
            logger.warning(f"获取浏览器版本超时 {browser_path}")
        except Exception as e:
            logger.warning(f"获取浏览器版本失败 {browser_path}: {e}")

        return None
        
    def download_portable_chrome(self) -> bool:
        """下载便携版Chrome"""
        try:
            logger.info("🌐 开始下载便携版Chrome...")
            
            # 使用Chrome便携版的替代方案
            # 实际实现中可以使用第三方便携版或者引导用户安装
            chrome_portable_dir = self.browsers_dir / "chrome_portable"
            chrome_portable_dir.mkdir(exist_ok=True)
            
            # 这里可以实现实际的下载逻辑
            # 或者提供安装指导
            logger.info("💡 便携版Chrome下载功能开发中...")
            logger.info("建议用户安装系统版Chrome以获得最佳体验")
            
            return False
            
        except Exception as e:
            logger.error(f"下载便携版Chrome失败: {e}")
            return False
            
    def download_chromedriver(self, chrome_version: str) -> bool:
        """下载匹配的ChromeDriver"""
        try:
            logger.info(f"📥 下载ChromeDriver for Chrome {chrome_version}...")

            # 检查版本是否有效
            if not chrome_version or chrome_version == 'None':
                logger.warning("Chrome版本无效，尝试下载最新版本的ChromeDriver")
                # 尝试获取最新版本
                try:
                    response = requests.get("https://chromedriver.storage.googleapis.com/LATEST_RELEASE", timeout=10)
                    if response.status_code == 200:
                        driver_version = response.text.strip()
                        logger.info(f"获取到最新ChromeDriver版本: {driver_version}")
                    else:
                        logger.error("无法获取最新ChromeDriver版本")
                        return False
                except Exception as e:
                    logger.error(f"获取最新ChromeDriver版本失败: {e}")
                    return False
            else:
                # 获取主版本号
                major_version = chrome_version.split('.')[0]
            
                # 获取最新的ChromeDriver版本
                version_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
                response = requests.get(version_url, timeout=10)

                if response.status_code != 200:
                    logger.error(f"无法获取ChromeDriver版本信息: {response.status_code}")
                    return False

                driver_version = response.text.strip()
            
            # 下载ChromeDriver
            download_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_win32.zip"
            
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                response = requests.get(download_url, timeout=60)
                if response.status_code == 200:
                    tmp_file.write(response.content)
                    tmp_path = tmp_file.name
                else:
                    logger.error(f"下载ChromeDriver失败: {response.status_code}")
                    return False
                    
            # 解压到drivers目录
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extract('chromedriver.exe', self.drivers_dir)
                
            # 清理临时文件
            os.unlink(tmp_path)
            
            logger.info(f"✅ ChromeDriver {driver_version} 下载完成")
            return True
            
        except Exception as e:
            logger.error(f"下载ChromeDriver失败: {e}")
            return False
            
    def setup_browser_environment(self, preferred_browser: str = 'chrome') -> Dict[str, Any]:
        """设置浏览器环境"""
        try:
            logger.info("🔧 开始设置浏览器环境...")
            
            # 1. 检测系统浏览器
            detected_browsers = self.detect_system_browsers()
            logger.info(f"检测到浏览器: {list(detected_browsers.keys())}")
            
            # 2. 选择最佳浏览器
            selected_browser = None
            browser_config = None
            
            if preferred_browser in detected_browsers:
                selected_browser = preferred_browser
                browser_config = detected_browsers[preferred_browser]
            elif detected_browsers:
                # 按优先级选择：Chrome > Edge > Firefox
                for browser in ['chrome', 'edge', 'firefox']:
                    if browser in detected_browsers:
                        selected_browser = browser
                        browser_config = detected_browsers[browser]
                        break
                        
            if not selected_browser:
                logger.error("❌ 未检测到支持的浏览器")
                return {
                    'success': False,
                    'error': '未检测到支持的浏览器，请安装Chrome、Edge或Firefox',
                    'suggestions': [
                        '1. 安装Google Chrome: https://www.google.com/chrome/',
                        '2. 或使用系统自带的Microsoft Edge',
                        '3. 或安装Mozilla Firefox: https://www.mozilla.org/firefox/'
                    ]
                }
                
            logger.info(f"✅ 选择浏览器: {selected_browser} ({browser_config['version']})")
            
            # 3. 设置驱动程序
            driver_path = None
            if selected_browser == 'chrome':
                driver_path = self.drivers_dir / "chromedriver.exe"
                if not driver_path.exists():
                    if not self.download_chromedriver(browser_config['version']):
                        logger.warning("ChromeDriver下载失败，将尝试使用系统PATH中的驱动")
                        
            # 4. 返回配置
            return {
                'success': True,
                'browser': selected_browser,
                'browser_path': browser_config['path'],
                'browser_version': browser_config['version'],
                'driver_path': str(driver_path) if driver_path and driver_path.exists() else None,
                'debug_port': self.supported_browsers[selected_browser]['debug_port'],
                'user_data_dir': str(self.user_data_dir / selected_browser)
            }
            
        except Exception as e:
            logger.error(f"设置浏览器环境失败: {e}")
            return {
                'success': False,
                'error': f'浏览器环境设置失败: {e}'
            }
            
    def start_browser_debug_mode(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """启动浏览器调试模式"""
        try:
            browser = config['browser']
            browser_path = config['browser_path']
            debug_port = config['debug_port']
            user_data_dir = config['user_data_dir']

            logger.info(f"🚀 启动{browser}调试模式...")

            # 🔧 修复：先检查调试端口是否已经可用
            if self._is_debug_port_ready(debug_port, max_attempts=1):
                logger.info(f"✅ {browser}调试模式已在运行 (端口: {debug_port})")
                return {
                    'success': True,
                    'browser': browser,
                    'debug_port': debug_port,
                    'debug_url': f'http://127.0.0.1:{debug_port}',
                    'process_id': None,  # 现有进程，不记录PID
                    'message': '使用现有的调试模式浏览器'
                }

            # 只有在调试端口不可用时才关闭现有进程
            logger.info("调试端口不可用，关闭现有浏览器进程...")
            self._kill_browser_processes(browser)

            # 确保用户数据目录存在
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)

            # 构建启动命令
            cmd = [
                browser_path,
                f"--remote-debugging-port={debug_port}",
                f"--user-data-dir={user_data_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--disable-features=VizDisplayCompositor",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding"
            ]

            # 启动浏览器
            logger.info(f"启动新的{browser}调试模式实例...")
            process = subprocess.Popen(cmd,
                                     creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)

            # 等待启动
            logger.info("⏳ 等待浏览器启动...")
            time.sleep(5)

            # 验证调试端口是否启动成功
            if self._is_debug_port_ready(debug_port):
                logger.info(f"✅ {browser}调试模式启动成功 (端口: {debug_port})")
                return {
                    'success': True,
                    'browser': browser,
                    'debug_port': debug_port,
                    'debug_url': f'http://127.0.0.1:{debug_port}',
                    'process_id': process.pid
                }
            else:
                logger.error(f"❌ {browser}调试模式启动失败")
                return {
                    'success': False,
                    'error': f'{browser}调试端口{debug_port}不可用'
                }

        except Exception as e:
            logger.error(f"启动浏览器调试模式失败: {e}")
            return {
                'success': False,
                'error': f'启动失败: {e}'
            }
            
    def _kill_browser_processes(self, browser: str):
        """关闭浏览器进程"""
        try:
            if browser == 'chrome':
                process_names = ['chrome.exe', 'chromedriver.exe']
            elif browser == 'edge':
                process_names = ['msedge.exe', 'msedgedriver.exe']
            elif browser == 'firefox':
                process_names = ['firefox.exe', 'geckodriver.exe']
            else:
                return
                
            for process_name in process_names:
                try:
                    subprocess.run(['taskkill', '/f', '/im', process_name], 
                                 capture_output=True, timeout=10)
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"关闭{browser}进程失败: {e}")
            
    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('127.0.0.1', port))
                return result == 0  # 0表示连接成功，端口被占用
        except:
            return False

    def _is_debug_port_ready(self, port: int, max_attempts: int = 10) -> bool:
        """检查调试端口是否就绪"""
        import socket
        import requests

        for attempt in range(max_attempts):
            try:
                # 首先检查端口是否被监听
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    result = s.connect_ex(('127.0.0.1', port))
                    if result == 0:  # 端口被占用
                        # 再检查是否可以访问调试API
                        try:
                            response = requests.get(f'http://127.0.0.1:{port}/json/version', timeout=2)
                            if response.status_code == 200:
                                logger.info(f"调试端口 {port} 已就绪")
                                return True
                        except:
                            pass

                # 等待一段时间再重试
                time.sleep(1)
                logger.info(f"等待调试端口 {port} 就绪... (尝试 {attempt + 1}/{max_attempts})")

            except Exception as e:
                logger.warning(f"检查调试端口失败: {e}")

        logger.error(f"调试端口 {port} 在 {max_attempts} 次尝试后仍未就绪")
        return False
            
    def get_selenium_config(self, browser_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取Selenium配置"""
        return {
            'driver_type': browser_config['browser'],
            'driver_location': browser_config.get('driver_path'),
            'debugger_address': f"127.0.0.1:{browser_config['debug_port']}",
            'timeout': 30,
            'headless': False,
            'simulation_mode': False
        }

    def auto_setup_and_start(self, preferred_browser: str = 'chrome') -> Dict[str, Any]:
        """自动设置并启动浏览器环境"""
        try:
            logger.info("🚀 开始自动设置浏览器环境...")

            # 1. 设置浏览器环境
            setup_result = self.setup_browser_environment(preferred_browser)
            if not setup_result['success']:
                return setup_result

            # 2. 启动调试模式
            debug_result = self.start_browser_debug_mode(setup_result)
            if not debug_result['success']:
                return debug_result

            # 3. 生成Selenium配置
            selenium_config = self.get_selenium_config(setup_result)

            # 4. 返回完整配置
            config = {
                'success': True,
                'browser_info': {
                    'browser': setup_result['browser'],
                    'version': setup_result['browser_version'],
                    'path': setup_result['browser_path']
                },
                'debug_info': {
                    'port': debug_result['debug_port'],
                    'url': debug_result['debug_url'],
                    'process_id': debug_result['process_id']
                },
                'selenium_config': selenium_config,
                'message': f"✅ {setup_result['browser']}环境已就绪，可以开始发布"
            }

            # 5. 保存配置
            self._save_browser_config(config)
            self.saved_config = config

            return config

        except Exception as e:
            logger.error(f"自动设置失败: {e}")
            return {
                'success': False,
                'error': f'自动设置失败: {e}'
            }

    def show_setup_guide(self) -> str:
        """显示设置指南"""
        guide = """
🔧 一键发布浏览器环境设置指南

📋 自动检测和配置：
1. 程序会自动检测您系统中已安装的浏览器
2. 优先使用Chrome，其次Edge，最后Firefox
3. 自动下载匹配的浏览器驱动程序
4. 自动启动浏览器调试模式

💡 如果自动设置失败：

方案1：安装Chrome浏览器
• 访问: https://www.google.com/chrome/
• 下载并安装最新版Chrome
• 重新运行程序

方案2：使用系统Edge浏览器
• Windows 10/11通常预装Edge
• 程序会自动检测并使用

方案3：手动配置
• 确保浏览器已安装
• 手动下载对应的驱动程序
• 将驱动程序放在项目的drivers目录

🚀 使用步骤：
1. 点击"🔧 自动设置浏览器"按钮
2. 等待自动检测和配置完成
3. 在弹出的浏览器中登录各平台账号
4. 返回程序开始一键发布

⚠️ 注意事项：
• 首次使用需要在浏览器中手动登录各平台
• 登录信息会保存，后续使用更便捷
• 保持浏览器窗口开启直到发布完成
        """
        return guide.strip()

    def _save_browser_config(self, config: Dict[str, Any]):
        """保存浏览器配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"浏览器配置已保存: {self.config_file}")
        except Exception as e:
            logger.error(f"保存浏览器配置失败: {e}")

    def _load_browser_config(self) -> Dict[str, Any]:
        """加载浏览器配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"已加载浏览器配置: {self.config_file}")
                return config
        except Exception as e:
            logger.error(f"加载浏览器配置失败: {e}")
        return {}

    def get_saved_config(self) -> Optional[Dict[str, Any]]:
        """获取保存的浏览器配置"""
        return self.saved_config if self.saved_config else None

    def is_browser_configured(self) -> bool:
        """检查是否已配置浏览器"""
        return bool(self.saved_config and self.saved_config.get('success', False))

    def get_saved_browser_info(self) -> Optional[Dict[str, Any]]:
        """获取保存的浏览器信息"""
        if self.saved_config and self.saved_config.get('success', False):
            return {
                'browser': self.saved_config.get('browser_info', {}).get('browser'),
                'version': self.saved_config.get('browser_info', {}).get('version'),
                'debug_port': self.saved_config.get('debug_info', {}).get('port'),
                'status': '已配置'
            }
        return None
