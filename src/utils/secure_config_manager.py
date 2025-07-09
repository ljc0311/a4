#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全配置管理器
提供API密钥加密存储和安全配置管理功能
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from src.utils.logger import logger


class SecureConfigManager:
    """安全配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # 加密密钥文件
        self.key_file = self.config_dir / ".encryption_key"
        self.encrypted_config_file = self.config_dir / "secure_config.enc"
        
        # 初始化加密
        self._init_encryption()
        
    def _init_encryption(self):
        """初始化加密系统"""
        if self.key_file.exists():
            # 加载现有密钥
            with open(self.key_file, 'rb') as f:
                self.key = f.read()
        else:
            # 生成新密钥
            self.key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(self.key)
            # 设置文件权限（仅所有者可读写）
            os.chmod(self.key_file, 0o600)
            
        self.cipher = Fernet(self.key)
        
    def encrypt_api_key(self, api_key: str) -> str:
        """加密API密钥"""
        encrypted_key = self.cipher.encrypt(api_key.encode())
        return base64.urlsafe_b64encode(encrypted_key).decode()
        
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """解密API密钥"""
        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_key.encode())
            decrypted_key = self.cipher.decrypt(encrypted_data)
            return decrypted_key.decode()
        except Exception as e:
            logger.error(f"解密API密钥失败: {e}")
            return ""
            
    def save_secure_config(self, config: Dict[str, Any]):
        """保存加密配置"""
        try:
            # 加密敏感配置
            secure_config = self._encrypt_sensitive_data(config)
            
            # 保存到加密文件
            config_json = json.dumps(secure_config, ensure_ascii=False, indent=2)
            encrypted_config = self.cipher.encrypt(config_json.encode())
            
            with open(self.encrypted_config_file, 'wb') as f:
                f.write(encrypted_config)
                
            logger.info("安全配置已保存")
            
        except Exception as e:
            logger.error(f"保存安全配置失败: {e}")
            
    def load_secure_config(self) -> Dict[str, Any]:
        """加载加密配置"""
        try:
            if not self.encrypted_config_file.exists():
                return {}
                
            with open(self.encrypted_config_file, 'rb') as f:
                encrypted_config = f.read()
                
            # 解密配置
            config_json = self.cipher.decrypt(encrypted_config).decode()
            secure_config = json.loads(config_json)
            
            # 解密敏感数据
            config = self._decrypt_sensitive_data(secure_config)
            
            logger.info("安全配置已加载")
            return config
            
        except Exception as e:
            logger.error(f"加载安全配置失败: {e}")
            return {}
            
    def _encrypt_sensitive_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """加密敏感数据"""
        encrypted_config = config.copy()
        
        # 加密API密钥
        if 'models' in config:
            encrypted_config['models'] = []
            for model in config['models']:
                encrypted_model = model.copy()
                if 'key' in model and model['key']:
                    encrypted_model['key'] = self.encrypt_api_key(model['key'])
                encrypted_config['models'].append(encrypted_model)
                
        return encrypted_config
        
    def _decrypt_sensitive_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """解密敏感数据"""
        decrypted_config = config.copy()
        
        # 解密API密钥
        if 'models' in config:
            decrypted_config['models'] = []
            for model in config['models']:
                decrypted_model = model.copy()
                if 'key' in model and model['key']:
                    decrypted_model['key'] = self.decrypt_api_key(model['key'])
                decrypted_config['models'].append(decrypted_model)
                
        return decrypted_config
        
    def migrate_existing_config(self, config_file: str):
        """迁移现有配置到安全存储"""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                logger.warning(f"配置文件不存在: {config_file}")
                return
                
            # 读取现有配置
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 保存到安全存储
            self.save_secure_config(config)
            
            # 备份原文件
            backup_file = config_path.with_suffix('.backup')
            config_path.rename(backup_file)
            
            logger.info(f"配置已迁移到安全存储，原文件备份为: {backup_file}")
            
        except Exception as e:
            logger.error(f"迁移配置失败: {e}")
            
    def get_api_key(self, provider: str, model_name: str = "") -> Optional[str]:
        """获取指定提供商的API密钥"""
        config = self.load_secure_config()
        
        if 'models' in config:
            for model in config['models']:
                if model.get('type') == provider or model.get('name') == provider:
                    if not model_name or model.get('name') == model_name:
                        return model.get('key', '')
                        
        return None
        
    def set_api_key(self, provider: str, api_key: str, model_name: str = ""):
        """设置API密钥"""
        config = self.load_secure_config()
        
        if 'models' not in config:
            config['models'] = []
            
        # 查找现有模型配置
        model_found = False
        for model in config['models']:
            if model.get('type') == provider or model.get('name') == provider:
                if not model_name or model.get('name') == model_name:
                    model['key'] = api_key
                    model_found = True
                    break
                    
        # 如果没有找到，创建新的模型配置
        if not model_found:
            new_model = {
                'name': model_name or provider,
                'type': provider,
                'key': api_key
            }
            config['models'].append(new_model)
            
        # 保存配置
        self.save_secure_config(config)
        logger.info(f"API密钥已设置: {provider}")
        
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置完整性"""
        required_fields = ['models']
        
        for field in required_fields:
            if field not in config:
                logger.error(f"配置缺少必需字段: {field}")
                return False
                
        # 验证模型配置
        if 'models' in config:
            for i, model in enumerate(config['models']):
                required_model_fields = ['name', 'type']
                for field in required_model_fields:
                    if field not in model:
                        logger.error(f"模型配置 {i} 缺少必需字段: {field}")
                        return False
                        
        return True


# 全局安全配置管理器实例
secure_config_manager = SecureConfigManager()
