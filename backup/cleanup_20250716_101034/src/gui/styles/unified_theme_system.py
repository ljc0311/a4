#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一主题系统
整合所有样式组件，提供现代化的Material Design 3.0风格界面
支持深浅色主题切换、响应式设计和无障碍访问
"""

import os
from typing import Dict, Optional, Callable
from enum import Enum
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QObject, pyqtSignal, QSettings
from PyQt5.QtGui import QPalette, QColor, QFont

from src.utils.logger import logger


class ThemeMode(Enum):
    """主题模式"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"  # 跟随系统


class ColorPalette:
    """现代化配色方案"""
    
    @staticmethod
    def get_light_colors() -> Dict[str, str]:
        """浅色主题配色"""
        return {
            # Material Design 3.0 主色系
            "primary": "#1976D2",
            "primary_container": "#E3F2FD",
            "on_primary": "#FFFFFF",
            "on_primary_container": "#0D47A1",
            
            # 次要色系
            "secondary": "#03DAC6",
            "secondary_container": "#E0F7FA",
            "on_secondary": "#000000",
            "on_secondary_container": "#00695C",
            
            # 表面色系
            "surface": "#FFFFFF",
            "surface_variant": "#F5F5F5",
            "surface_container": "#FAFAFA",
            "surface_container_high": "#F0F0F0",
            "on_surface": "#1C1B1F",
            "on_surface_variant": "#49454F",
            
            # 背景色系
            "background": "#FEFBFF",
            "on_background": "#1C1B1F",
            
            # 轮廓色
            "outline": "#79747E",
            "outline_variant": "#CAC4D0",
            
            # 状态色
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336",
            "info": "#2196F3",
            
            # 特殊色
            "shadow": "rgba(0, 0, 0, 0.1)",
            "scrim": "rgba(0, 0, 0, 0.32)",
            "inverse_surface": "#313033",
            "inverse_on_surface": "#F4EFF4",
        }
    
    @staticmethod
    def get_dark_colors() -> Dict[str, str]:
        """深色主题配色"""
        return {
            # Material Design 3.0 主色系
            "primary": "#90CAF9",
            "primary_container": "#1565C0",
            "on_primary": "#0D47A1",
            "on_primary_container": "#E3F2FD",
            
            # 次要色系
            "secondary": "#80CBC4",
            "secondary_container": "#00695C",
            "on_secondary": "#00251A",
            "on_secondary_container": "#A7F3D0",
            
            # 表面色系
            "surface": "#121212",
            "surface_variant": "#1E1E1E",
            "surface_container": "#1F1F1F",
            "surface_container_high": "#2C2C2C",
            "on_surface": "#E6E1E5",
            "on_surface_variant": "#CAC4D0",
            
            # 背景色系
            "background": "#0F0F0F",
            "on_background": "#E6E1E5",
            
            # 轮廓色
            "outline": "#938F99",
            "outline_variant": "#49454F",
            
            # 状态色
            "success": "#66BB6A",
            "warning": "#FFB74D",
            "error": "#EF5350",
            "info": "#42A5F5",
            
            # 特殊色
            "shadow": "rgba(0, 0, 0, 0.3)",
            "scrim": "rgba(0, 0, 0, 0.6)",
            "inverse_surface": "#E6E1E5",
            "inverse_on_surface": "#313033",
        }


class StyleGenerator:
    """样式生成器"""
    
    def __init__(self, colors: Dict[str, str]):
        self.colors = colors
    
    def generate_complete_stylesheet(self) -> str:
        """生成完整的样式表"""
        styles = []
        
        # 基础样式
        styles.append(self._generate_base_styles())
        
        # 组件样式
        styles.append(self._generate_button_styles())
        styles.append(self._generate_input_styles())
        styles.append(self._generate_list_styles())
        styles.append(self._generate_tab_styles())
        styles.append(self._generate_scrollbar_styles())
        styles.append(self._generate_menu_styles())
        styles.append(self._generate_dialog_styles())
        styles.append(self._generate_progress_styles())
        styles.append(self._generate_card_styles())
        
        return "\n\n".join(styles)
    
    def _generate_base_styles(self) -> str:
        """生成基础样式"""
        return f"""
/* ===== 基础样式 ===== */
QWidget {{
    background-color: {self.colors['background']};
    color: {self.colors['on_background']};
    font-family: "Microsoft YaHei UI", "Segoe UI", "Microsoft YaHei", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
    font-size: 14px;
    selection-background-color: {self.colors['primary_container']};
    selection-color: {self.colors['on_primary_container']};
}}

QMainWindow {{
    background-color: {self.colors['background']};
    color: {self.colors['on_background']};
}}

QFrame {{
    background-color: {self.colors['surface']};
    color: {self.colors['on_surface']};
    border: 1px solid {self.colors['outline_variant']};
    border-radius: 12px;
}}

QLabel {{
    background-color: transparent;
    color: {self.colors['on_surface']};
    border: none;
}}

QGroupBox {{
    background-color: {self.colors['surface_container']};
    color: {self.colors['on_surface']};
    border: 2px solid {self.colors['outline_variant']};
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
    font-size: 15px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: {self.colors['primary']};
    background-color: {self.colors['surface_container']};
}}"""
    
    def _generate_button_styles(self) -> str:
        """生成按钮样式"""
        return f"""
/* ===== 按钮样式 ===== */
QPushButton {{
    background-color: {self.colors['primary']};
    color: {self.colors['on_primary']};
    border: none;
    border-radius: 20px;
    padding: 12px 24px;
    font-weight: 500;
    font-size: 14px;
    min-height: 20px;
    min-width: 80px;
}}

QPushButton:hover {{
    background-color: {self.colors['primary_container']};
    color: {self.colors['on_primary_container']};
    border: 2px solid {self.colors['primary']};
}}

QPushButton:pressed {{
    background-color: {self.colors['primary']};
    color: {self.colors['on_primary']};
    border: 2px solid {self.colors['primary']};
}}

QPushButton:disabled {{
    background-color: {self.colors['surface_variant']};
    color: {self.colors['on_surface_variant']};
    border: none;
}}

QPushButton:focus {{
    outline: 2px solid {self.colors['primary']};
    outline-offset: 2px;
}}

/* 扁平按钮 */
QPushButton[flat="true"] {{
    background-color: transparent;
    color: {self.colors['primary']};
    border: 1px solid {self.colors['outline']};
}}

QPushButton[flat="true"]:hover {{
    background-color: {self.colors['surface_container_high']};
    border-color: {self.colors['primary']};
}}

/* 危险按钮 */
QPushButton[danger="true"] {{
    background-color: {self.colors['error']};
    color: {self.colors['on_primary']};
}}

QPushButton[danger="true"]:hover {{
    background-color: #D32F2F;
}}

/* 成功按钮 */
QPushButton[success="true"] {{
    background-color: {self.colors['success']};
    color: {self.colors['on_primary']};
}}

QPushButton[success="true"]:hover {{
    background-color: #388E3C;
}}"""
    
    def _generate_input_styles(self) -> str:
        """生成输入框样式"""
        return f"""
/* ===== 输入框样式 ===== */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {self.colors['surface']};
    color: {self.colors['on_surface']};
    border: 2px solid {self.colors['outline_variant']};
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 14px;
    selection-background-color: {self.colors['primary_container']};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {self.colors['primary']};
    outline: none;
}}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {self.colors['surface_variant']};
    color: {self.colors['on_surface_variant']};
    border-color: {self.colors['outline_variant']};
}}

QComboBox {{
    background-color: {self.colors['surface']};
    color: {self.colors['on_surface']};
    border: 2px solid {self.colors['outline_variant']};
    border-radius: 8px;
    padding: 12px 16px;
    min-height: 20px;
    font-size: 14px;
}}

QComboBox:focus {{
    border-color: {self.colors['primary']};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {self.colors['on_surface']};
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {self.colors['surface']};
    color: {self.colors['on_surface']};
    border: 1px solid {self.colors['outline_variant']};
    border-radius: 8px;
    selection-background-color: {self.colors['primary']};
    selection-color: {self.colors['on_primary']};
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    padding: 12px 16px;
    border: none;
    min-height: 20px;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: {self.colors['surface_container_high']};
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {self.colors['surface']};
    color: {self.colors['on_surface']};
    border: 2px solid {self.colors['outline_variant']};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {self.colors['primary']};
}}"""
    
    def _generate_list_styles(self) -> str:
        """生成列表样式"""
        return f"""
/* ===== 列表样式 ===== */
QListWidget, QTreeWidget {{
    background-color: {self.colors['surface']};
    color: {self.colors['on_surface']};
    border: 1px solid {self.colors['outline_variant']};
    border-radius: 8px;
    outline: none;
    font-size: 14px;
}}

QListWidget::item, QTreeWidget::item {{
    padding: 12px 16px;
    border: none;
    border-radius: 6px;
    margin: 2px 4px;
}}

QListWidget::item:hover, QTreeWidget::item:hover {{
    background-color: {self.colors['surface_container_high']};
}}

QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {self.colors['primary']};
    color: {self.colors['on_primary']};
}}

QTableWidget {{
    background-color: {self.colors['surface']};
    color: {self.colors['on_surface']};
    border: 1px solid {self.colors['outline_variant']};
    border-radius: 8px;
    gridline-color: {self.colors['outline_variant']};
    selection-background-color: {self.colors['primary_container']};
    font-size: 14px;
}}

QTableWidget::item {{
    padding: 8px 12px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: {self.colors['primary']};
    color: {self.colors['on_primary']};
}}

QHeaderView::section {{
    background-color: {self.colors['surface_container']};
    color: {self.colors['on_surface']};
    border: 1px solid {self.colors['outline_variant']};
    padding: 8px 12px;
    font-weight: 600;
}}"""
    
    def _generate_tab_styles(self) -> str:
        """生成标签页样式"""
        return f"""
/* ===== 标签页样式 ===== */
QTabWidget::pane {{
    background-color: {self.colors['surface']};
    border: 1px solid {self.colors['outline_variant']};
    border-radius: 8px;
    margin-top: 2px;
}}

QTabBar::tab {{
    background-color: {self.colors['surface_variant']};
    color: {self.colors['on_surface_variant']};
    border: 1px solid {self.colors['outline_variant']};
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    padding: 12px 20px;
    margin-right: 2px;
    font-weight: 500;
    font-size: 14px;
}}

QTabBar::tab:selected {{
    background-color: {self.colors['primary']};
    color: {self.colors['on_primary']};
    border-color: {self.colors['primary']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {self.colors['surface_container_high']};
    color: {self.colors['on_surface']};
}}"""
    
    def _generate_scrollbar_styles(self) -> str:
        """生成滚动条样式"""
        return f"""
/* ===== 滚动条样式 ===== */
QScrollBar:vertical {{
    background-color: {self.colors['surface_variant']};
    width: 12px;
    border-radius: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {self.colors['outline']};
    border-radius: 6px;
    min-height: 20px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {self.colors['primary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
}}

QScrollBar:horizontal {{
    background-color: {self.colors['surface_variant']};
    height: 12px;
    border-radius: 6px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {self.colors['outline']};
    border-radius: 6px;
    min-width: 20px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {self.colors['primary']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    border: none;
}}"""
    
    def _generate_menu_styles(self) -> str:
        """生成菜单样式"""
        return f"""
/* ===== 菜单样式 ===== */
QMenuBar {{
    background-color: {self.colors['surface_container']};
    color: {self.colors['on_surface']};
    border: none;
    padding: 4px;
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 8px 16px;
    border-radius: 6px;
    margin: 2px;
}}

QMenuBar::item:selected {{
    background-color: {self.colors['surface_container_high']};
}}

QMenu {{
    background-color: {self.colors['surface']};
    color: {self.colors['on_surface']};
    border: 1px solid {self.colors['outline_variant']};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 16px;
    border-radius: 6px;
    margin: 2px;
}}

QMenu::item:selected {{
    background-color: {self.colors['primary']};
    color: {self.colors['on_primary']};
}}

QMenu::separator {{
    height: 1px;
    background-color: {self.colors['outline_variant']};
    margin: 4px 8px;
}}"""
    
    def _generate_dialog_styles(self) -> str:
        """生成对话框样式"""
        return f"""
/* ===== 对话框样式 ===== */
QDialog {{
    background-color: {self.colors['surface']};
    color: {self.colors['on_surface']};
    border: 1px solid {self.colors['outline_variant']};
    border-radius: 12px;
}}

QMessageBox {{
    background-color: {self.colors['surface']};
    color: {self.colors['on_surface']};
}}

QMessageBox QPushButton {{
    min-width: 80px;
    padding: 8px 16px;
}}"""
    
    def _generate_progress_styles(self) -> str:
        """生成进度条样式"""
        return f"""
/* ===== 进度条样式 ===== */
QProgressBar {{
    background-color: {self.colors['surface_variant']};
    border: none;
    border-radius: 8px;
    height: 8px;
    text-align: center;
    font-size: 12px;
    color: {self.colors['on_surface']};
}}

QProgressBar::chunk {{
    background-color: {self.colors['primary']};
    border-radius: 8px;
}}

QSlider::groove:horizontal {{
    background-color: {self.colors['surface_variant']};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background-color: {self.colors['primary']};
    width: 20px;
    height: 20px;
    border-radius: 10px;
    margin: -7px 0;
}}

QSlider::handle:horizontal:hover {{
    background-color: {self.colors['primary_container']};
    border: 2px solid {self.colors['primary']};
}}"""
    
    def _generate_card_styles(self) -> str:
        """生成卡片样式"""
        return f"""
/* ===== 卡片样式 ===== */
QFrame[cardStyle="true"] {{
    background-color: {self.colors['surface']};
    border: 1px solid {self.colors['outline_variant']};
    border-radius: 12px;
    padding: 16px;
}}

QWidget[elevated="true"] {{
    background-color: {self.colors['surface_container']};
    border: none;
    border-radius: 12px;
}}

/* 特殊组件样式 */
QCheckBox {{
    color: {self.colors['on_surface']};
    font-size: 14px;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {self.colors['outline']};
    border-radius: 4px;
    background-color: {self.colors['surface']};
}}

QCheckBox::indicator:checked {{
    background-color: {self.colors['primary']};
    border-color: {self.colors['primary']};
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
}}

QRadioButton {{
    color: {self.colors['on_surface']};
    font-size: 14px;
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {self.colors['outline']};
    border-radius: 9px;
    background-color: {self.colors['surface']};
}}

QRadioButton::indicator:checked {{
    background-color: {self.colors['primary']};
    border-color: {self.colors['primary']};
}}

QRadioButton::indicator:checked::after {{
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 4px;
    background-color: {self.colors['on_primary']};
    position: absolute;
    top: 3px;
    left: 3px;
}}"""


class UnifiedThemeSystem(QObject):
    """统一主题系统"""
    
    # 信号
    theme_changed = pyqtSignal(str)  # 主题模式变化
    
    _instance: Optional['UnifiedThemeSystem'] = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        super().__init__()
        self._initialized = True
        
        # 当前主题设置
        self.current_mode = ThemeMode.LIGHT
        self.current_colors = ColorPalette.get_light_colors()
        
        # 样式生成器
        self.style_generator = StyleGenerator(self.current_colors)
        
        # 设置管理
        self.settings = QSettings("AIVideoGenerator", "UnifiedTheme")
        
        # 加载保存的设置
        self.load_settings()
        
        logger.info("统一主题系统初始化完成")
    
    def load_settings(self):
        """加载保存的主题设置"""
        try:
            mode_name = self.settings.value("theme_mode", ThemeMode.LIGHT.value)
            try:
                self.current_mode = ThemeMode(mode_name)
            except ValueError:
                self.current_mode = ThemeMode.LIGHT
            
            self._update_colors()
            logger.info(f"已加载主题设置: {self.current_mode.value}")
            
        except Exception as e:
            logger.warning(f"加载主题设置失败: {e}")
            self.reset_to_default()
    
    def save_settings(self):
        """保存主题设置"""
        try:
            self.settings.setValue("theme_mode", self.current_mode.value)
            self.settings.sync()
            logger.debug("主题设置已保存")
        except Exception as e:
            logger.error(f"保存主题设置失败: {e}")
    
    def set_theme_mode(self, mode: ThemeMode):
        """设置主题模式"""
        if self.current_mode != mode:
            self.current_mode = mode
            self._update_colors()
            self.save_settings()
            self.theme_changed.emit(mode.value)
            logger.info(f"主题模式已切换到: {mode.value}")
    
    def toggle_theme_mode(self):
        """切换主题模式"""
        new_mode = ThemeMode.DARK if self.current_mode == ThemeMode.LIGHT else ThemeMode.LIGHT
        self.set_theme_mode(new_mode)
    
    def _update_colors(self):
        """更新颜色配置"""
        if self.current_mode == ThemeMode.DARK:
            self.current_colors = ColorPalette.get_dark_colors()
        else:
            self.current_colors = ColorPalette.get_light_colors()
        
        # 更新样式生成器
        self.style_generator = StyleGenerator(self.current_colors)
    
    def apply_to_application(self, app: Optional[QApplication] = None):
        """应用主题到整个应用程序"""
        if app is None:
            app = QApplication.instance()
        
        if app is None:
            logger.warning("无法获取应用程序实例")
            return
        
        try:
            # 生成并应用样式表
            stylesheet = self.style_generator.generate_complete_stylesheet()
            app.setStyleSheet(stylesheet)
            
            # 设置应用程序字体
            font = QFont("Microsoft YaHei UI", 10)
            font.setHintingPreference(QFont.PreferFullHinting)
            app.setFont(font)
            
            logger.info(f"已应用{self.current_mode.value}主题到应用程序")
            
        except Exception as e:
            logger.error(f"应用主题失败: {e}")
    
    def apply_to_widget(self, widget: QWidget):
        """应用主题到指定控件"""
        try:
            stylesheet = self.style_generator.generate_complete_stylesheet()
            widget.setStyleSheet(stylesheet)
            logger.debug(f"已应用主题到控件: {widget.__class__.__name__}")
        except Exception as e:
            logger.error(f"应用控件主题失败: {e}")
    
    def get_color(self, key: str, fallback: str = "#000000") -> str:
        """获取当前主题颜色"""
        return self.current_colors.get(key, fallback)
    
    def get_current_mode(self) -> ThemeMode:
        """获取当前主题模式"""
        return self.current_mode
    
    def reset_to_default(self):
        """重置为默认主题"""
        self.set_theme_mode(ThemeMode.LIGHT)
        logger.info("主题已重置为默认设置")


# 全局主题系统实例
_theme_system: Optional[UnifiedThemeSystem] = None


def get_theme_system() -> UnifiedThemeSystem:
    """获取全局主题系统实例"""
    global _theme_system
    if _theme_system is None:
        _theme_system = UnifiedThemeSystem()
    return _theme_system


def apply_unified_theme(app: Optional[QApplication] = None):
    """应用统一主题"""
    theme_system = get_theme_system()
    theme_system.apply_to_application(app)


def set_theme_mode(mode: ThemeMode):
    """设置主题模式"""
    theme_system = get_theme_system()
    theme_system.set_theme_mode(mode)


def toggle_theme():
    """切换主题模式"""
    theme_system = get_theme_system()
    theme_system.toggle_theme_mode()


def get_current_color(key: str, fallback: str = "#000000") -> str:
    """获取当前主题颜色"""
    theme_system = get_theme_system()
    return theme_system.get_color(key, fallback)