# -*- coding: utf-8 -*-
"""
显示设置配置管理
负责保存和加载显示设置配置
"""

import os
import json
from typing import Dict, Any, Optional
from src.utils.logger import logger


class DisplayConfig:
    """显示设置配置管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "font": {
            "family": "Microsoft YaHei UI",
            "size": 10,
            "auto_size": True
        },
        "dpi": {
            "auto_scaling": True,
            "custom_scale_factor": 1.0,
            "force_dpi": None
        },
        "window": {
            "auto_resize": True,
            "remember_size": True,
            "remember_position": True,
            "default_width": 1200,
            "default_height": 800
        },
        "theme": {
            "name": "light",
            "auto_switch": False
        },
        "accessibility": {
            "high_contrast": False,
            "large_cursor": False,
            "screen_reader_support": False
        }
    }
    
    def __init__(self, config_dir: str = None):
        """初始化配置管理器"""
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".ai_video_generator")
        
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "display_settings.json")
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 加载配置
        self.config = self.load_config()
        
        logger.debug(f"显示配置管理器初始化完成，配置文件: {self.config_file}")
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 合并默认配置（确保所有键都存在）
                merged_config = self._merge_config(self.DEFAULT_CONFIG, config)
                
                logger.info(f"显示配置已加载: {self.config_file}")
                return merged_config
            else:
                logger.info("显示配置文件不存在，使用默认配置")
                return self.DEFAULT_CONFIG.copy()
                
        except Exception as e:
            logger.error(f"加载显示配置失败: {e}")
            return self.DEFAULT_CONFIG.copy()
    
    def save_config(self) -> bool:
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"显示配置已保存: {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存显示配置失败: {e}")
            return False
    
    def get(self, key: str, default=None) -> Any:
        """获取配置值（支持点号分隔的嵌套键）"""
        try:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.error(f"获取配置值失败: {key}, {e}")
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """设置配置值（支持点号分隔的嵌套键）"""
        try:
            keys = key.split('.')
            config = self.config
            
            # 导航到最后一级的父级
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置值
            config[keys[-1]] = value
            
            logger.debug(f"配置值已设置: {key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"设置配置值失败: {key} = {value}, {e}")
            return False
    
    def get_font_config(self) -> Dict[str, Any]:
        """获取字体配置"""
        return self.config.get("font", {})
    
    def set_font_config(self, font_config: Dict[str, Any]) -> bool:
        """设置字体配置"""
        try:
            self.config["font"].update(font_config)
            return True
        except Exception as e:
            logger.error(f"设置字体配置失败: {e}")
            return False
    
    def get_dpi_config(self) -> Dict[str, Any]:
        """获取DPI配置"""
        return self.config.get("dpi", {})
    
    def set_dpi_config(self, dpi_config: Dict[str, Any]) -> bool:
        """设置DPI配置"""
        try:
            self.config["dpi"].update(dpi_config)
            return True
        except Exception as e:
            logger.error(f"设置DPI配置失败: {e}")
            return False
    
    def get_window_config(self) -> Dict[str, Any]:
        """获取窗口配置"""
        return self.config.get("window", {})
    
    def set_window_config(self, window_config: Dict[str, Any]) -> bool:
        """设置窗口配置"""
        try:
            self.config["window"].update(window_config)
            return True
        except Exception as e:
            logger.error(f"设置窗口配置失败: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            self.config = self.DEFAULT_CONFIG.copy()
            logger.info("显示配置已重置为默认值")
            return True
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return False
    
    def export_config(self, file_path: str) -> bool:
        """导出配置到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已导出到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """从文件导入配置"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"配置文件不存在: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 合并配置
            self.config = self._merge_config(self.DEFAULT_CONFIG, imported_config)
            
            logger.info(f"配置已从文件导入: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False
    
    def _merge_config(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置（递归合并字典）"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            "config_file": self.config_file,
            "font_family": self.get("font.family"),
            "font_size": self.get("font.size"),
            "auto_dpi_scaling": self.get("dpi.auto_scaling"),
            "custom_scale_factor": self.get("dpi.custom_scale_factor"),
            "auto_resize": self.get("window.auto_resize"),
            "theme": self.get("theme.name")
        }


# 全局配置实例
_display_config = None

def get_display_config() -> DisplayConfig:
    """获取全局显示配置实例"""
    global _display_config
    if _display_config is None:
        _display_config = DisplayConfig()
    return _display_config

def save_display_config() -> bool:
    """保存显示配置"""
    config = get_display_config()
    return config.save_config()

def reset_display_config() -> bool:
    """重置显示配置"""
    config = get_display_config()
    return config.reset_to_default()
