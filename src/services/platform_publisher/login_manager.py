#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台登录管理器
自动管理各平台的登录状态和用户信息保存
"""

import os
import json
import time
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

from src.utils.logger import logger


class LoginManager:
    """平台登录管理器"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path.cwd() / "user_data"
        self.data_dir.mkdir(exist_ok=True)
        
        # 登录数据文件
        self.login_data_file = self.data_dir / "login_data.json"
        self.cookies_dir = self.data_dir / "cookies"
        self.cookies_dir.mkdir(exist_ok=True)
        
        # 加密密钥
        self.key_file = self.data_dir / "login.key"
        self.cipher = self._get_or_create_cipher()
        
        # 支持的平台配置
        self.platforms = {
            'douyin': {
                'name': '抖音',
                'login_url': 'https://creator.douyin.com',
                'check_selector': '.semi-avatar',
                'login_check_text': '登录',
                'icon': '🎵'
            },
            'bilibili': {
                'name': 'B站',
                'login_url': 'https://member.bilibili.com/platform/upload/video/frame',
                'check_selector': '.user-info',
                'login_check_text': '登录',
                'icon': '📺'
            },
            'kuaishou': {
                'name': '快手',
                'login_url': 'https://cp.kuaishou.com/article/publish/video',
                'check_selector': '.user-avatar',
                'login_check_text': '登录',
                'icon': '⚡'
            },
            'xiaohongshu': {
                'name': '小红书',
                'login_url': 'https://creator.xiaohongshu.com/publish/publish',
                'check_selector': '.avatar',
                'login_check_text': '登录',
                'icon': '📖'
            }
        }
        
        # 加载已保存的登录数据
        self.login_data = self._load_login_data()
        
    def _get_or_create_cipher(self) -> Fernet:
        """获取或创建加密密钥"""
        try:
            if self.key_file.exists():
                with open(self.key_file, 'rb') as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                    
            return Fernet(key)
            
        except Exception as e:
            logger.error(f"创建加密密钥失败: {e}")
            # 使用默认密钥
            return Fernet(Fernet.generate_key())
            
    def _load_login_data(self) -> Dict[str, Any]:
        """加载登录数据"""
        try:
            if self.login_data_file.exists():
                with open(self.login_data_file, 'r', encoding='utf-8') as f:
                    encrypted_data = json.load(f)
                    
                # 解密数据
                decrypted_data = {}
                for platform, data in encrypted_data.items():
                    if isinstance(data, dict) and 'encrypted' in data:
                        try:
                            decrypted_bytes = self.cipher.decrypt(data['encrypted'].encode())
                            decrypted_data[platform] = json.loads(decrypted_bytes.decode())
                        except Exception as e:
                            logger.warning(f"解密{platform}登录数据失败: {e}")
                            decrypted_data[platform] = {}
                    else:
                        decrypted_data[platform] = data
                        
                return decrypted_data
                
        except Exception as e:
            logger.error(f"加载登录数据失败: {e}")
            
        return {}
        
    def _save_login_data(self):
        """保存登录数据"""
        try:
            # 加密数据
            encrypted_data = {}
            for platform, data in self.login_data.items():
                if data:
                    data_bytes = json.dumps(data, ensure_ascii=False).encode()
                    encrypted_bytes = self.cipher.encrypt(data_bytes)
                    encrypted_data[platform] = {
                        'encrypted': encrypted_bytes.decode(),
                        'updated_at': datetime.now().isoformat()
                    }
                    
            # 保存到文件
            with open(self.login_data_file, 'w', encoding='utf-8') as f:
                json.dump(encrypted_data, f, ensure_ascii=False, indent=2)
                
            logger.info("登录数据保存成功")
            
        except Exception as e:
            logger.error(f"保存登录数据失败: {e}")
            
    def get_platform_login_urls(self) -> Dict[str, Dict[str, str]]:
        """获取各平台登录URL和信息"""
        return {
            platform_id: {
                'name': config['name'],
                'url': config['login_url'],
                'icon': config['icon']
            }
            for platform_id, config in self.platforms.items()
        }
        
    def save_login_info(self, platform: str, user_info: Dict[str, Any], cookies: List[Dict] = None):
        """保存平台登录信息"""
        try:
            if platform not in self.platforms:
                logger.warning(f"不支持的平台: {platform}")
                return False
                
            # 保存用户信息
            self.login_data[platform] = {
                'user_info': user_info,
                'login_time': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),
                'is_logged_in': True
            }
            
            # 保存Cookies
            if cookies:
                cookies_file = self.cookies_dir / f"{platform}_cookies.json"
                with open(cookies_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                    
                self.login_data[platform]['cookies_file'] = str(cookies_file)
                
            # 保存数据
            self._save_login_data()
            
            logger.info(f"✅ {self.platforms[platform]['name']}登录信息保存成功")
            return True
            
        except Exception as e:
            logger.error(f"保存{platform}登录信息失败: {e}")
            return False
            
    def get_login_info(self, platform: str) -> Optional[Dict[str, Any]]:
        """获取平台登录信息"""
        try:
            if platform not in self.login_data:
                return None
                
            login_info = self.login_data[platform]
            
            # 检查是否过期
            if 'expires_at' in login_info:
                expires_at = datetime.fromisoformat(login_info['expires_at'])
                if datetime.now() > expires_at:
                    logger.info(f"{platform}登录信息已过期")
                    self.clear_login_info(platform)
                    return None
                    
            return login_info
            
        except Exception as e:
            logger.error(f"获取{platform}登录信息失败: {e}")
            return None
            
    def is_logged_in(self, platform: str) -> bool:
        """检查平台是否已登录"""
        login_info = self.get_login_info(platform)
        return login_info is not None and login_info.get('is_logged_in', False)
        
    def clear_login_info(self, platform: str):
        """清除平台登录信息"""
        try:
            if platform in self.login_data:
                # 删除cookies文件
                if 'cookies_file' in self.login_data[platform]:
                    cookies_file = Path(self.login_data[platform]['cookies_file'])
                    if cookies_file.exists():
                        cookies_file.unlink()
                        
                # 清除登录数据
                del self.login_data[platform]
                self._save_login_data()
                
                logger.info(f"✅ {self.platforms.get(platform, {}).get('name', platform)}登录信息已清除")
                
        except Exception as e:
            logger.error(f"清除{platform}登录信息失败: {e}")
            
    def get_all_login_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有平台的登录状态"""
        status = {}
        
        for platform_id, config in self.platforms.items():
            login_info = self.get_login_info(platform_id)
            
            status[platform_id] = {
                'name': config['name'],
                'icon': config['icon'],
                'is_logged_in': login_info is not None,
                'user_info': login_info.get('user_info', {}) if login_info else {},
                'login_time': login_info.get('login_time') if login_info else None
            }
            
        return status
        
    def load_cookies_for_driver(self, platform: str, driver):
        """为Selenium驱动加载cookies"""
        try:
            login_info = self.get_login_info(platform)
            if not login_info or 'cookies_file' not in login_info:
                return False
                
            cookies_file = Path(login_info['cookies_file'])
            if not cookies_file.exists():
                return False
                
            # 加载cookies
            with open(cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                
            # 先访问域名
            platform_config = self.platforms[platform]
            driver.get(platform_config['login_url'])
            
            # 添加cookies
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"添加cookie失败: {e}")
                    
            # 刷新页面使cookies生效
            driver.refresh()
            
            logger.info(f"✅ {platform_config['name']}的cookies加载成功")
            return True
            
        except Exception as e:
            logger.error(f"为{platform}加载cookies失败: {e}")
            return False
            
    def save_cookies_from_driver(self, platform: str, driver):
        """从Selenium驱动保存cookies"""
        try:
            cookies = driver.get_cookies()
            
            # 获取用户信息（如果可能）
            user_info = self._extract_user_info(platform, driver)
            
            # 保存登录信息
            return self.save_login_info(platform, user_info, cookies)
            
        except Exception as e:
            logger.error(f"从{platform}保存cookies失败: {e}")
            return False
            
    def _extract_user_info(self, platform: str, driver) -> Dict[str, Any]:
        """从页面提取用户信息"""
        try:
            user_info = {
                'platform': platform,
                'extracted_at': datetime.now().isoformat()
            }
            
            # 根据平台提取不同的用户信息
            if platform == 'douyin':
                try:
                    # 尝试获取用户头像和昵称
                    avatar_elem = driver.find_element("css selector", ".semi-avatar")
                    if avatar_elem:
                        user_info['avatar_url'] = avatar_elem.get_attribute('src')
                except:
                    pass
                    
            elif platform == 'bilibili':
                try:
                    # 尝试获取B站用户信息
                    user_elem = driver.find_element("css selector", ".user-info")
                    if user_elem:
                        user_info['username'] = user_elem.text
                except:
                    pass
                    
            # 添加更多平台的用户信息提取逻辑...
            
            return user_info
            
        except Exception as e:
            logger.warning(f"提取{platform}用户信息失败: {e}")
            return {'platform': platform}
            
    def get_login_guide_text(self) -> str:
        """获取登录指导文本"""
        return """
🔐 平台登录指导

📋 操作步骤：
1. 点击"🌐 打开登录页面"按钮
2. 在弹出的浏览器中登录各平台账号
3. 登录成功后点击"💾 保存登录状态"
4. 系统会自动保存您的登录信息

✨ 优势：
• 一次登录，长期有效（30天）
• 自动保存登录状态和用户信息
• 加密存储，安全可靠
• 支持多平台同时登录

⚠️ 注意事项：
• 请在安全的网络环境下登录
• 登录信息仅保存在本地
• 如需清除登录信息，可点击"🗑️ 清除登录"
        """.strip()
        
    def cleanup_expired_logins(self):
        """清理过期的登录信息"""
        try:
            expired_platforms = []
            
            for platform in list(self.login_data.keys()):
                login_info = self.login_data[platform]
                if 'expires_at' in login_info:
                    expires_at = datetime.fromisoformat(login_info['expires_at'])
                    if datetime.now() > expires_at:
                        expired_platforms.append(platform)
                        
            for platform in expired_platforms:
                self.clear_login_info(platform)
                
            if expired_platforms:
                logger.info(f"清理了{len(expired_platforms)}个过期的登录信息")
                
        except Exception as e:
            logger.error(f"清理过期登录信息失败: {e}")


# 全局登录管理器实例
login_manager = LoginManager()
