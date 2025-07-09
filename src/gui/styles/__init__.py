#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一样式系统
整合所有样式相关功能，提供简洁的API接口
"""

# 导入核心组件
from .unified_theme_system import UnifiedThemeSystem, ThemeMode, get_theme_system

# 版本信息
__version__ = "2.0.0"
__author__ = "AI Video Generator Team"

# 导出的公共API
__all__ = [
    # 核心类
    'UnifiedThemeSystem', 'ThemeMode',
    
    # 实例获取函数
    'get_theme_system',
]

# 便捷导入
def init_style_system():
    """初始化样式系统"""
    try:
        theme_system = get_theme_system()
        theme_system.apply_to_application()
        return True
    except Exception as e:
        print(f"样式系统初始化失败: {e}")
        return False


# 兼容性函数（向后兼容）
def apply_modern_style(widget=None):
    """应用现代样式（兼容性函数）"""
    try:
        theme_system = get_theme_system()
        if widget:
            theme_system.apply_to_widget(widget)
        else:
            theme_system.apply_to_application()
    except Exception as e:
        print(f"应用样式失败: {e}")


def toggle_theme():
    """切换主题（兼容性函数）"""
    try:
        theme_system = get_theme_system()
        theme_system.toggle_theme_mode()
    except Exception as e:
        print(f"切换主题失败: {e}")


def get_style_manager():
    """获取样式管理器（兼容性函数）"""
    return get_theme_system()
