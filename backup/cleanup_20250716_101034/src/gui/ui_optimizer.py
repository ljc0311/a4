#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI界面优化器
将现代化设计应用到现有界面
提供一键优化功能
"""

from PyQt5.QtWidgets import (
    QWidget, QApplication, QPushButton, QFrame, QLabel,
    QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox,
    QLineEdit, QTextEdit, QComboBox, QProgressBar,
    QTableWidget, QListWidget, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

from .styles.enhanced_color_palette import EnhancedColorPalette
from .styles.modern_style_generator import ModernStyleGenerator
from .components.enhanced_ui_components import (
    EnhancedMaterialButton, GradientCard, StatusIndicator,
    LoadingSpinner, FloatingActionButton
)
from .layouts.responsive_layout import ResponsiveContainer, BreakPoint

from src.utils.logger import logger


class UIOptimizer:
    """UI界面优化器"""
    
    def __init__(self):
        self.color_palette = EnhancedColorPalette()
        self.current_colors = self.color_palette.get_modern_light_colors()
        self.style_generator = ModernStyleGenerator(self.current_colors)
        
        # 优化配置
        self.optimization_config = {
            "apply_modern_colors": True,
            "enhance_buttons": True,
            "add_animations": True,
            "improve_spacing": True,
            "add_shadows": True,
            "responsive_layout": True,
            "modern_typography": True,
            "status_indicators": True
        }
    
    def optimize_application(self, app: QApplication = None):
        """优化整个应用程序"""
        if app is None:
            app = QApplication.instance()
        
        if app is None:
            logger.warning("无法获取应用程序实例")
            return False
        
        try:
            # 应用现代化样式表
            stylesheet = self.style_generator.generate_complete_stylesheet()
            app.setStyleSheet(stylesheet)
            
            # 设置现代化字体
            self.apply_modern_typography(app)
            
            logger.info("应用程序UI优化完成")
            return True
            
        except Exception as e:
            logger.error(f"应用程序UI优化失败: {e}")
            return False
    
    def optimize_widget(self, widget: QWidget):
        """优化单个控件"""
        try:
            # 应用样式表
            if self.optimization_config["apply_modern_colors"]:
                self.apply_modern_styles(widget)
            
            # 增强按钮
            if self.optimization_config["enhance_buttons"]:
                self.enhance_buttons(widget)
            
            # 改进间距
            if self.optimization_config["improve_spacing"]:
                self.improve_spacing(widget)
            
            # 添加阴影效果
            if self.optimization_config["add_shadows"]:
                self.add_shadow_effects(widget)
            
            # 应用响应式布局
            if self.optimization_config["responsive_layout"]:
                self.apply_responsive_layout(widget)
            
            # 现代化字体
            if self.optimization_config["modern_typography"]:
                self.apply_modern_typography_to_widget(widget)
            
            logger.info(f"控件 {widget.__class__.__name__} 优化完成")
            return True
            
        except Exception as e:
            logger.error(f"控件优化失败: {e}")
            return False
    
    def apply_modern_styles(self, widget: QWidget):
        """应用现代化样式"""
        stylesheet = self.style_generator.generate_complete_stylesheet()
        widget.setStyleSheet(stylesheet)
    
    def enhance_buttons(self, widget: QWidget):
        """增强按钮样式"""
        # 查找所有按钮并应用增强样式
        buttons = widget.findChildren(QPushButton)
        
        for button in buttons:
            # 设置现代化按钮属性
            button.setMinimumHeight(48)
            button.setFont(QFont("Segoe UI", 10, QFont.Medium))
            button.setCursor(Qt.PointingHandCursor)
            
            # 根据按钮文本或属性确定类型
            if button.property("flat"):
                button.setProperty("button_type", "outlined")
            elif "主要" in button.text() or "确定" in button.text() or "生成" in button.text():
                button.setProperty("button_type", "filled")
            else:
                button.setProperty("button_type", "outlined")
    
    def improve_spacing(self, widget: QWidget):
        """改进间距"""
        # 改进布局间距
        layout = widget.layout()
        if layout:
            # 设置现代化间距
            layout.setSpacing(16)
            layout.setContentsMargins(16, 16, 16, 16)
            
            # 递归处理子布局
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget():
                    self.improve_spacing(item.widget())
    
    def add_shadow_effects(self, widget: QWidget):
        """添加阴影效果"""
        # 为卡片和容器添加阴影
        frames = widget.findChildren(QFrame)
        group_boxes = widget.findChildren(QGroupBox)
        
        for frame in frames:
            if frame.frameStyle() != QFrame.NoFrame:
                self.add_card_shadow(frame)
        
        for group_box in group_boxes:
            self.add_card_shadow(group_box)
    
    def add_card_shadow(self, widget: QWidget):
        """为控件添加卡片阴影"""
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        from PyQt5.QtGui import QColor
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        widget.setGraphicsEffect(shadow)
    
    def apply_responsive_layout(self, widget: QWidget):
        """应用响应式布局"""
        # 如果控件还没有响应式容器，则包装它
        if not isinstance(widget.parent(), ResponsiveContainer):
            # 创建响应式容器
            responsive_container = ResponsiveContainer()
            
            # 将原控件移到响应式容器中
            if widget.parent():
                parent_layout = widget.parent().layout()
                if parent_layout:
                    parent_layout.addWidget(responsive_container)
            
            # 设置响应式配置
            responsive_container.add_adaptive_widget(widget, {
                BreakPoint.XS.value: {"visible": True, "min_size": (300, 200)},
                BreakPoint.SM.value: {"visible": True, "min_size": (400, 300)},
                BreakPoint.MD.value: {"visible": True, "min_size": (600, 400)},
                BreakPoint.LG.value: {"visible": True, "min_size": (800, 600)},
                BreakPoint.XL.value: {"visible": True, "min_size": (1000, 700)},
            })
    
    def apply_modern_typography(self, app: QApplication):
        """应用现代化字体"""
        # 设置应用程序默认字体
        font = QFont("Segoe UI", 10)
        font.setHintingPreference(QFont.PreferFullHinting)
        app.setFont(font)
    
    def apply_modern_typography_to_widget(self, widget: QWidget):
        """为控件应用现代化字体"""
        # 标题字体
        labels = widget.findChildren(QLabel)
        for label in labels:
            text = label.text()
            if any(keyword in text for keyword in ["标题", "Title", "🎬", "📝", "🎨", "🎤", "🎥"]):
                font = QFont("Segoe UI", 14, QFont.Bold)
                label.setFont(font)
            elif text.startswith("###") or text.startswith("##"):
                font = QFont("Segoe UI", 12, QFont.Medium)
                label.setFont(font)
    
    def add_status_indicators(self, widget: QWidget):
        """添加状态指示器"""
        # 查找需要状态指示的控件
        progress_bars = widget.findChildren(QProgressBar)
        
        for progress_bar in progress_bars:
            # 在进度条旁边添加状态指示器
            if progress_bar.parent():
                layout = progress_bar.parent().layout()
                if layout and isinstance(layout, (QVBoxLayout, QHBoxLayout)):
                    status_indicator = StatusIndicator(StatusIndicator.INACTIVE, "就绪")
                    layout.addWidget(status_indicator)
    
    def create_floating_action_button(self, parent: QWidget, icon: str = "+", 
                                    position: str = "bottom-right"):
        """创建浮动操作按钮"""
        fab = FloatingActionButton(icon, parent)
        
        # 设置位置
        def update_fab_position():
            if position == "bottom-right":
                x = parent.width() - fab.width() - 24
                y = parent.height() - fab.height() - 24
            elif position == "bottom-left":
                x = 24
                y = parent.height() - fab.height() - 24
            elif position == "top-right":
                x = parent.width() - fab.width() - 24
                y = 24
            else:  # top-left
                x = 24
                y = 24
            
            fab.move(x, y)
        
        # 监听父控件大小变化
        def on_parent_resize():
            QTimer.singleShot(0, update_fab_position)
        
        parent.resizeEvent = lambda event: (
            QWidget.resizeEvent(parent, event),
            on_parent_resize()
        )
        
        # 初始位置
        update_fab_position()
        
        return fab
    
    def optimize_main_window(self, main_window):
        """优化主窗口"""
        try:
            # 设置窗口属性
            main_window.setAttribute(Qt.WA_StyledBackground, True)
            
            # 优化整个窗口
            self.optimize_widget(main_window)
            
            # 添加浮动操作按钮（可选）
            if hasattr(main_window, 'add_fab') and main_window.add_fab:
                fab = self.create_floating_action_button(main_window, "⚙", "bottom-right")
                fab.clicked.connect(lambda: self.show_optimization_dialog(main_window))
            
            logger.info("主窗口优化完成")
            return True
            
        except Exception as e:
            logger.error(f"主窗口优化失败: {e}")
            return False
    
    def show_optimization_dialog(self, parent):
        """显示优化配置对话框"""
        from PyQt5.QtWidgets import QDialog, QCheckBox, QDialogButtonBox
        
        dialog = QDialog(parent)
        dialog.setWindowTitle("UI优化设置")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # 优化选项
        checkboxes = {}
        for key, value in self.optimization_config.items():
            checkbox = QCheckBox(self.get_config_display_name(key))
            checkbox.setChecked(value)
            checkboxes[key] = checkbox
            layout.addWidget(checkbox)
        
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            # 更新配置
            for key, checkbox in checkboxes.items():
                self.optimization_config[key] = checkbox.isChecked()
            
            # 重新优化
            self.optimize_widget(parent)
    
    def get_config_display_name(self, key: str) -> str:
        """获取配置项显示名称"""
        names = {
            "apply_modern_colors": "应用现代化配色",
            "enhance_buttons": "增强按钮样式",
            "add_animations": "添加动画效果",
            "improve_spacing": "改进间距布局",
            "add_shadows": "添加阴影效果",
            "responsive_layout": "响应式布局",
            "modern_typography": "现代化字体",
            "status_indicators": "状态指示器"
        }
        return names.get(key, key)
    
    def set_theme_mode(self, mode: str):
        """设置主题模式"""
        if mode == "dark":
            self.current_colors = self.color_palette.get_modern_dark_colors()
        else:
            self.current_colors = self.color_palette.get_modern_light_colors()
        
        self.style_generator = ModernStyleGenerator(self.current_colors)


# 全局优化器实例
_ui_optimizer = None


def get_ui_optimizer() -> UIOptimizer:
    """获取全局UI优化器实例"""
    global _ui_optimizer
    if _ui_optimizer is None:
        _ui_optimizer = UIOptimizer()
    return _ui_optimizer


def optimize_application(app: QApplication = None):
    """优化应用程序"""
    optimizer = get_ui_optimizer()
    return optimizer.optimize_application(app)


def optimize_widget(widget: QWidget):
    """优化控件"""
    optimizer = get_ui_optimizer()
    return optimizer.optimize_widget(widget)


def optimize_main_window(main_window):
    """优化主窗口"""
    optimizer = get_ui_optimizer()
    return optimizer.optimize_main_window(main_window)
