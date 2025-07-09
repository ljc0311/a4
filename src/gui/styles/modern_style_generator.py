#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化样式生成器
生成Material Design 3.0风格的QSS样式表
支持动画、渐变、阴影等现代UI效果
"""

from typing import Dict, Optional
from .enhanced_color_palette import EnhancedColorPalette


class ModernStyleGenerator:
    """现代化样式生成器"""
    
    def __init__(self, colors: Dict[str, str]):
        self.colors = colors
    
    def generate_complete_stylesheet(self) -> str:
        """生成完整的样式表"""
        styles = [
            self._generate_base_styles(),
            self._generate_button_styles(),
            self._generate_input_styles(),
            self._generate_container_styles(),
            self._generate_navigation_styles(),
            self._generate_table_styles(),
            self._generate_dialog_styles(),
            self._generate_animation_styles(),
        ]
        
        return "\n\n".join(styles)
    
    def _generate_base_styles(self) -> str:
        """生成基础样式"""
        return f"""
/* === 基础样式 === */
QWidget {{
    background-color: {self.colors.get('background', '#FFFFFF')};
    color: {self.colors.get('on_background', '#000000')};
    font-family: "Segoe UI", "Microsoft YaHei UI", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
    font-size: 14px;
    selection-background-color: {self.colors.get('primary_alpha_24', 'rgba(103, 80, 164, 0.24)')};
    selection-color: {self.colors.get('on_primary', '#FFFFFF')};
}}

QMainWindow {{
    background-color: {self.colors.get('background', '#FFFFFF')};
    border: none;
}}

/* 滚动条样式 */
QScrollBar:vertical {{
    background: {self.colors.get('surface_container', '#F1ECF4')};
    width: 12px;
    border-radius: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {self.colors.get('outline_variant', '#CAC4D0')};
    border-radius: 6px;
    min-height: 20px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: {self.colors.get('outline', '#79747E')};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: {self.colors.get('surface_container', '#F1ECF4')};
    height: 12px;
    border-radius: 6px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {self.colors.get('outline_variant', '#CAC4D0')};
    border-radius: 6px;
    min-width: 20px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {self.colors.get('outline', '#79747E')};
}}
"""
    
    def _generate_button_styles(self) -> str:
        """生成按钮样式"""
        return f"""
/* === 按钮样式 === */
QPushButton {{
    background-color: {self.colors.get('primary', '#6750A4')};
    color: {self.colors.get('on_primary', '#FFFFFF')};
    border: none;
    border-radius: 20px;
    padding: 12px 24px;
    font-weight: 500;
    font-size: 14px;
    min-height: 40px;
    outline: none;
}}

QPushButton:hover {{
    background-color: {self.colors.get('primary_container', '#EADDFF')};
    color: {self.colors.get('on_primary_container', '#21005D')};
}}

QPushButton:pressed {{
    background-color: {self.colors.get('primary_alpha_24', 'rgba(103, 80, 164, 0.24)')};
    transform: scale(0.98);
}}

QPushButton:disabled {{
    background-color: {self.colors.get('surface_variant', '#E7E0EC')};
    color: {self.colors.get('on_surface_variant', '#49454F')};
}}

/* 轮廓按钮 */
QPushButton[flat="true"] {{
    background-color: transparent;
    color: {self.colors.get('primary', '#6750A4')};
    border: 2px solid {self.colors.get('outline', '#79747E')};
}}

QPushButton[flat="true"]:hover {{
    background-color: {self.colors.get('primary_alpha_12', 'rgba(103, 80, 164, 0.12)')};
    border-color: {self.colors.get('primary', '#6750A4')};
}}

/* 文本按钮 */
QPushButton[text="true"] {{
    background-color: transparent;
    color: {self.colors.get('primary', '#6750A4')};
    border: none;
    padding: 8px 16px;
}}

QPushButton[text="true"]:hover {{
    background-color: {self.colors.get('primary_alpha_12', 'rgba(103, 80, 164, 0.12)')};
}}

/* 浮动操作按钮 */
QPushButton[fab="true"] {{
    background-color: {self.colors.get('primary_container', '#EADDFF')};
    color: {self.colors.get('on_primary_container', '#21005D')};
    border-radius: 28px;
    min-width: 56px;
    min-height: 56px;
    max-width: 56px;
    max-height: 56px;
    font-size: 24px;
}}
"""
    
    def _generate_input_styles(self) -> str:
        """生成输入控件样式"""
        return f"""
/* === 输入控件样式 === */
QLineEdit {{
    background-color: {self.colors.get('surface_container', '#F1ECF4')};
    color: {self.colors.get('on_surface', '#1C1B1F')};
    border: 2px solid {self.colors.get('outline_variant', '#CAC4D0')};
    border-radius: 12px;
    padding: 12px 16px;
    font-size: 14px;
    min-height: 20px;
}}

QLineEdit:focus {{
    border-color: {self.colors.get('primary', '#6750A4')};
    background-color: {self.colors.get('surface', '#FFFBFE')};
}}

QLineEdit:disabled {{
    background-color: {self.colors.get('surface_variant', '#E7E0EC')};
    color: {self.colors.get('on_surface_variant', '#49454F')};
    border-color: {self.colors.get('outline_variant', '#CAC4D0')};
}}

QTextEdit {{
    background-color: {self.colors.get('surface_container', '#F1ECF4')};
    color: {self.colors.get('on_surface', '#1C1B1F')};
    border: 2px solid {self.colors.get('outline_variant', '#CAC4D0')};
    border-radius: 12px;
    padding: 12px;
    font-size: 14px;
    line-height: 1.5;
}}

QTextEdit:focus {{
    border-color: {self.colors.get('primary', '#6750A4')};
    background-color: {self.colors.get('surface', '#FFFBFE')};
}}

QComboBox {{
    background-color: {self.colors.get('surface_container', '#F1ECF4')};
    color: {self.colors.get('on_surface', '#1C1B1F')};
    border: 2px solid {self.colors.get('outline_variant', '#CAC4D0')};
    border-radius: 12px;
    padding: 8px 16px;
    min-height: 24px;
}}

QComboBox:hover {{
    border-color: {self.colors.get('outline', '#79747E')};
}}

QComboBox:focus {{
    border-color: {self.colors.get('primary', '#6750A4')};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {self.colors.get('on_surface_variant', '#49454F')};
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {self.colors.get('surface_container', '#F1ECF4')};
    border: 1px solid {self.colors.get('outline_variant', '#CAC4D0')};
    border-radius: 8px;
    selection-background-color: {self.colors.get('primary_alpha_12', 'rgba(103, 80, 164, 0.12)')};
    padding: 4px;
}}
"""
    
    def _generate_container_styles(self) -> str:
        """生成容器样式"""
        return f"""
/* === 容器样式 === */
QFrame {{
    background-color: {self.colors.get('surface', '#FFFBFE')};
    border: 1px solid {self.colors.get('outline_variant', '#CAC4D0')};
    border-radius: 12px;
}}

QGroupBox {{
    background-color: {self.colors.get('surface_container', '#F1ECF4')};
    border: 2px solid {self.colors.get('outline_variant', '#CAC4D0')};
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 500;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {self.colors.get('primary', '#6750A4')};
    background-color: {self.colors.get('surface_container', '#F1ECF4')};
    border-radius: 4px;
    margin-left: 8px;
}}

/* 卡片样式 */
QFrame[card="true"] {{
    background-color: {self.colors.get('surface_container', '#F1ECF4')};
    border: none;
    border-radius: 16px;
    padding: 16px;
}}

QFrame[card="elevated"] {{
    background-color: {self.colors.get('surface_container_high', '#ECE6F0')};
    border: none;
    border-radius: 16px;
    padding: 16px;
}}
"""
    
    def _generate_navigation_styles(self) -> str:
        """生成导航样式"""
        return f"""
/* === 导航样式 === */
QTabWidget::pane {{
    background-color: {self.colors.get('surface', '#FFFBFE')};
    border: 1px solid {self.colors.get('outline_variant', '#CAC4D0')};
    border-radius: 12px;
    margin-top: -1px;
}}

QTabBar::tab {{
    background-color: {self.colors.get('surface_container', '#F1ECF4')};
    color: {self.colors.get('on_surface_variant', '#49454F')};
    border: none;
    border-radius: 20px;
    padding: 12px 24px;
    margin: 2px;
    min-width: 80px;
}}

QTabBar::tab:selected {{
    background-color: {self.colors.get('secondary_container', '#E8DEF8')};
    color: {self.colors.get('on_secondary_container', '#1D192B')};
    font-weight: 500;
}}

QTabBar::tab:hover:!selected {{
    background-color: {self.colors.get('primary_alpha_12', 'rgba(103, 80, 164, 0.12)')};
}}

QMenuBar {{
    background-color: {self.colors.get('surface_container', '#F1ECF4')};
    color: {self.colors.get('on_surface', '#1C1B1F')};
    border: none;
    padding: 4px;
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 8px 16px;
    border-radius: 8px;
}}

QMenuBar::item:selected {{
    background-color: {self.colors.get('primary_alpha_12', 'rgba(103, 80, 164, 0.12)')};
}}

QMenu {{
    background-color: {self.colors.get('surface_container', '#F1ECF4')};
    border: 1px solid {self.colors.get('outline_variant', '#CAC4D0')};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 16px;
    border-radius: 6px;
}}

QMenu::item:selected {{
    background-color: {self.colors.get('primary_alpha_12', 'rgba(103, 80, 164, 0.12)')};
}}
"""
    
    def _generate_table_styles(self) -> str:
        """生成表格样式"""
        return f"""
/* === 表格样式 === */
QTableWidget {{
    background-color: {self.colors.get('surface', '#FFFBFE')};
    alternate-background-color: {self.colors.get('surface_container_low', '#F7F2FA')};
    gridline-color: {self.colors.get('outline_variant', '#CAC4D0')};
    border: 1px solid {self.colors.get('outline_variant', '#CAC4D0')};
    border-radius: 8px;
}}

QTableWidget::item {{
    padding: 8px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: {self.colors.get('primary_alpha_12', 'rgba(103, 80, 164, 0.12)')};
    color: {self.colors.get('on_surface', '#1C1B1F')};
}}

QHeaderView::section {{
    background-color: {self.colors.get('surface_container_high', '#ECE6F0')};
    color: {self.colors.get('on_surface', '#1C1B1F')};
    padding: 12px 8px;
    border: none;
    border-bottom: 2px solid {self.colors.get('primary', '#6750A4')};
    font-weight: 500;
}}

QListWidget {{
    background-color: {self.colors.get('surface', '#FFFBFE')};
    border: 1px solid {self.colors.get('outline_variant', '#CAC4D0')};
    border-radius: 8px;
    padding: 4px;
}}

QListWidget::item {{
    padding: 8px;
    border-radius: 6px;
    margin: 1px;
}}

QListWidget::item:selected {{
    background-color: {self.colors.get('primary_alpha_12', 'rgba(103, 80, 164, 0.12)')};
    color: {self.colors.get('on_surface', '#1C1B1F')};
}}

QListWidget::item:hover {{
    background-color: {self.colors.get('surface_alpha_08', 'rgba(255, 251, 254, 0.08)')};
}}
"""
    
    def _generate_dialog_styles(self) -> str:
        """生成对话框样式"""
        return f"""
/* === 对话框样式 === */
QDialog {{
    background-color: {self.colors.get('surface_container_high', '#ECE6F0')};
    border-radius: 16px;
}}

QMessageBox {{
    background-color: {self.colors.get('surface_container_high', '#ECE6F0')};
    border-radius: 16px;
}}

QProgressBar {{
    background-color: {self.colors.get('surface_container', '#F1ECF4')};
    border: none;
    border-radius: 8px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {self.colors.get('primary', '#6750A4')};
    border-radius: 8px;
}}

QCheckBox {{
    color: {self.colors.get('on_surface', '#1C1B1F')};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid {self.colors.get('outline', '#79747E')};
    border-radius: 4px;
    background-color: {self.colors.get('surface', '#FFFBFE')};
}}

QCheckBox::indicator:checked {{
    background-color: {self.colors.get('primary', '#6750A4')};
    border-color: {self.colors.get('primary', '#6750A4')};
}}

QRadioButton {{
    color: {self.colors.get('on_surface', '#1C1B1F')};
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid {self.colors.get('outline', '#79747E')};
    border-radius: 10px;
    background-color: {self.colors.get('surface', '#FFFBFE')};
}}

QRadioButton::indicator:checked {{
    background-color: {self.colors.get('primary', '#6750A4')};
    border-color: {self.colors.get('primary', '#6750A4')};
}}
"""
    
    def _generate_animation_styles(self) -> str:
        """生成动画样式"""
        return f"""
/* === 动画和特效样式 === */
QWidget[animated="true"] {{
    /* 为支持动画的控件预留 */
}}

QStatusBar {{
    background-color: {self.colors.get('surface_container', '#F1ECF4')};
    color: {self.colors.get('on_surface_variant', '#49454F')};
    border: none;
    border-top: 1px solid {self.colors.get('outline_variant', '#CAC4D0')};
    padding: 4px 8px;
}}

QToolTip {{
    background-color: {self.colors.get('inverse_surface', '#313033')};
    color: {self.colors.get('inverse_on_surface', '#F4EFF4')};
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}}
"""
