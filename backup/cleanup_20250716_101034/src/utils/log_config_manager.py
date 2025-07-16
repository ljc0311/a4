# -*- coding: utf-8 -*-
"""
日志配置管理器
提供动态调整日志级别的功能
"""

import logging
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


class LogConfigManager:
    """日志配置管理器"""
    
    def __init__(self, config_file: str = None):
        """初始化日志配置管理器"""
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'log_config.json')
        
        self.config_file = config_file
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载日志配置"""
        default_config = {
            "console_level": "WARNING",  # 控制台只显示警告及以上
            "file_level": "DEBUG",      # 文件记录所有日志
            "error_file_level": "ERROR", # 错误文件只记录错误
            "enable_console": True,
            "enable_file": True,
            "enable_error_file": True,
            "suppress_repeated_logs": True,
            "suppress_threshold": 10,
            "suppress_interval": 60,
            "log_format": "[%(asctime)s] [%(levelname)s] [%(name)s] [%(module)s:%(lineno)d] [%(funcName)s] %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S"
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并默认配置和加载的配置
                    default_config.update(loaded_config)
            else:
                # 创建默认配置文件
                self._save_config(default_config)
        except Exception as e:
            print(f"加载日志配置失败，使用默认配置: {e}")
            
        return default_config
    
    def _save_config(self, config: Dict[str, Any] = None):
        """保存日志配置"""
        if config is None:
            config = self.config
            
        try:
            # 确保配置目录存在
            config_dir = os.path.dirname(self.config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存日志配置失败: {e}")
    
    def get_console_level(self) -> int:
        """获取控制台日志级别"""
        level_str = self.config.get("console_level", "WARNING")
        return getattr(logging, level_str.upper(), logging.WARNING)
    
    def get_file_level(self) -> int:
        """获取文件日志级别"""
        level_str = self.config.get("file_level", "DEBUG")
        return getattr(logging, level_str.upper(), logging.DEBUG)
    
    def get_error_file_level(self) -> int:
        """获取错误文件日志级别"""
        level_str = self.config.get("error_file_level", "ERROR")
        return getattr(logging, level_str.upper(), logging.ERROR)
    
    def set_console_level(self, level: str):
        """设置控制台日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level.upper() in valid_levels:
            self.config["console_level"] = level.upper()
            self._save_config()
            self._apply_config()
        else:
            raise ValueError(f"无效的日志级别: {level}，有效级别: {valid_levels}")
    
    def set_file_level(self, level: str):
        """设置文件日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level.upper() in valid_levels:
            self.config["file_level"] = level.upper()
            self._save_config()
            self._apply_config()
        else:
            raise ValueError(f"无效的日志级别: {level}，有效级别: {valid_levels}")
    
    def enable_verbose_mode(self):
        """启用详细模式（显示所有日志）"""
        self.config["console_level"] = "DEBUG"
        self.config["file_level"] = "DEBUG"
        self._save_config()
        self._apply_config()
        print("已启用详细日志模式")
    
    def enable_quiet_mode(self):
        """启用安静模式（只显示错误）"""
        self.config["console_level"] = "ERROR"
        self.config["file_level"] = "WARNING"
        self._save_config()
        self._apply_config()
        print("已启用安静日志模式")
    
    def enable_normal_mode(self):
        """启用正常模式（推荐设置）"""
        self.config["console_level"] = "WARNING"
        self.config["file_level"] = "DEBUG"
        self._save_config()
        self._apply_config()
        print("已启用正常日志模式")
    
    def _apply_config(self):
        """应用配置到现有的日志记录器"""
        try:
            # 更新所有现有的日志记录器
            for name, logger in logging.Logger.manager.loggerDict.items():
                if isinstance(logger, logging.Logger):
                    for handler in logger.handlers:
                        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                            # 控制台处理器
                            handler.setLevel(self.get_console_level())
                        elif isinstance(handler, logging.FileHandler):
                            # 文件处理器
                            if "error" in handler.baseFilename.lower():
                                handler.setLevel(self.get_error_file_level())
                            else:
                                handler.setLevel(self.get_file_level())
        except Exception as e:
            print(f"应用日志配置失败: {e}")
    
    def get_config_summary(self) -> str:
        """获取配置摘要"""
        return f"""
当前日志配置:
- 控制台级别: {self.config.get('console_level', 'WARNING')}
- 文件级别: {self.config.get('file_level', 'DEBUG')}
- 错误文件级别: {self.config.get('error_file_level', 'ERROR')}
- 启用控制台: {self.config.get('enable_console', True)}
- 启用文件: {self.config.get('enable_file', True)}
- 抑制重复日志: {self.config.get('suppress_repeated_logs', True)}
"""
    
    def reset_to_default(self):
        """重置为默认配置"""
        self.config = {
            "console_level": "WARNING",
            "file_level": "DEBUG",
            "error_file_level": "ERROR",
            "enable_console": True,
            "enable_file": True,
            "enable_error_file": True,
            "suppress_repeated_logs": True,
            "suppress_threshold": 10,
            "suppress_interval": 60,
            "log_format": "[%(asctime)s] [%(levelname)s] [%(name)s] [%(module)s:%(lineno)d] [%(funcName)s] %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S"
        }
        self._save_config()
        self._apply_config()
        print("已重置为默认日志配置")


# 全局日志配置管理器实例
log_config_manager = LogConfigManager()

# 便捷函数
def set_console_level(level: str):
    """设置控制台日志级别"""
    log_config_manager.set_console_level(level)

def set_file_level(level: str):
    """设置文件日志级别"""
    log_config_manager.set_file_level(level)

def enable_verbose_mode():
    """启用详细模式"""
    log_config_manager.enable_verbose_mode()

def enable_quiet_mode():
    """启用安静模式"""
    log_config_manager.enable_quiet_mode()

def enable_normal_mode():
    """启用正常模式"""
    log_config_manager.enable_normal_mode()

def get_config_summary() -> str:
    """获取配置摘要"""
    return log_config_manager.get_config_summary()

def reset_to_default():
    """重置为默认配置"""
    log_config_manager.reset_to_default()