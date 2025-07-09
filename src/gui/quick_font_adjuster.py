#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速字体调整工具
提供快捷键和工具栏按钮来快速调整字体大小
"""

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, 
                            QSlider, QApplication, QToolBar, QAction)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QKeySequence
from src.utils.logger import logger


class QuickFontAdjuster(QWidget):
    """快速字体调整器"""
    
    font_size_changed = pyqtSignal(int)  # 字体大小改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_font_size = 10
        self.min_font_size = 8
        self.max_font_size = 24
        
        self.setup_ui()
        self.setup_shortcuts()
        
    def setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # 减小字体按钮
        self.decrease_btn = QPushButton("A-")
        self.decrease_btn.setToolTip("减小字体 (Ctrl+-)")
        self.decrease_btn.setMaximumWidth(30)
        self.decrease_btn.clicked.connect(self.decrease_font_size)
        layout.addWidget(self.decrease_btn)
        
        # 字体大小滑块
        self.font_slider = QSlider(Qt.Horizontal)
        self.font_slider.setRange(self.min_font_size, self.max_font_size)
        self.font_slider.setValue(self.current_font_size)
        self.font_slider.setMaximumWidth(100)
        self.font_slider.valueChanged.connect(self.on_slider_changed)
        layout.addWidget(self.font_slider)
        
        # 增大字体按钮
        self.increase_btn = QPushButton("A+")
        self.increase_btn.setToolTip("增大字体 (Ctrl++)")
        self.increase_btn.setMaximumWidth(30)
        self.increase_btn.clicked.connect(self.increase_font_size)
        layout.addWidget(self.increase_btn)
        
        # 字体大小标签
        self.size_label = QLabel(f"{self.current_font_size}pt")
        self.size_label.setMinimumWidth(35)
        self.size_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.size_label)
        
        # 重置按钮
        self.reset_btn = QPushButton("重置")
        self.reset_btn.setToolTip("重置字体大小 (Ctrl+0)")
        self.reset_btn.setMaximumWidth(40)
        self.reset_btn.clicked.connect(self.reset_font_size)
        layout.addWidget(self.reset_btn)
        
    def setup_shortcuts(self):
        """设置快捷键"""
        if self.parent():
            # 增大字体快捷键
            increase_action = QAction(self.parent())
            increase_action.setShortcut(QKeySequence("Ctrl++"))
            increase_action.triggered.connect(self.increase_font_size)
            self.parent().addAction(increase_action)
            
            # 减小字体快捷键
            decrease_action = QAction(self.parent())
            decrease_action.setShortcut(QKeySequence("Ctrl+-"))
            decrease_action.triggered.connect(self.decrease_font_size)
            self.parent().addAction(decrease_action)
            
            # 重置字体快捷键
            reset_action = QAction(self.parent())
            reset_action.setShortcut(QKeySequence("Ctrl+0"))
            reset_action.triggered.connect(self.reset_font_size)
            self.parent().addAction(reset_action)
            
    def increase_font_size(self):
        """增大字体"""
        new_size = min(self.current_font_size + 1, self.max_font_size)
        self.set_font_size(new_size)
        
    def decrease_font_size(self):
        """减小字体"""
        new_size = max(self.current_font_size - 1, self.min_font_size)
        self.set_font_size(new_size)
        
    def reset_font_size(self):
        """重置字体大小"""
        self.set_font_size(10)
        
    def set_font_size(self, size):
        """设置字体大小"""
        if size != self.current_font_size:
            self.current_font_size = size
            self.font_slider.setValue(size)
            self.size_label.setText(f"{size}pt")
            self.font_size_changed.emit(size)
            
            # 应用到当前应用程序
            self.apply_font_size_to_app(size)
            
            logger.info(f"字体大小已调整为: {size}pt")
            
    def on_slider_changed(self, value):
        """滑块值改变"""
        self.set_font_size(value)
        
    def apply_font_size_to_app(self, size):
        """应用字体大小到整个应用程序"""
        try:
            app = QApplication.instance()
            if app:
                font = app.font()
                font.setPointSize(size)
                app.setFont(font)
                
                # 更新所有窗口
                for widget in app.allWidgets():
                    if widget.isWindow():
                        self.update_widget_font(widget, size)
                        
        except Exception as e:
            logger.error(f"应用字体大小失败: {e}")
            
    def update_widget_font(self, widget, size):
        """递归更新控件字体"""
        try:
            # 更新当前控件字体
            font = widget.font()
            font.setPointSize(size)
            widget.setFont(font)
            
            # 递归更新子控件
            for child in widget.findChildren(QWidget):
                child_font = child.font()
                child_font.setPointSize(size)
                child.setFont(child_font)
                
        except Exception as e:
            logger.error(f"更新控件字体失败: {e}")


class FontAdjusterToolBar(QToolBar):
    """字体调整工具栏"""
    
    def __init__(self, parent=None):
        super().__init__("字体调整", parent)
        self.setMovable(False)
        
        # 添加字体调整器
        self.font_adjuster = QuickFontAdjuster(parent)
        self.addWidget(self.font_adjuster)
        
        # 添加分隔符
        self.addSeparator()
        
        # 添加预设字体大小按钮
        self.add_preset_buttons()
        
    def add_preset_buttons(self):
        """添加预设字体大小按钮"""
        presets = [
            ("小", 9),
            ("中", 11),
            ("大", 14),
            ("特大", 18)
        ]
        
        for name, size in presets:
            action = QAction(name, self)
            action.setToolTip(f"设置字体为{size}pt")
            action.triggered.connect(lambda checked, s=size: self.font_adjuster.set_font_size(s))
            self.addAction(action)


def add_font_adjuster_to_window(window):
    """为窗口添加字体调整功能"""
    try:
        # 创建字体调整工具栏
        font_toolbar = FontAdjusterToolBar(window)
        window.addToolBar(Qt.TopToolBarArea, font_toolbar)
        
        logger.info("字体调整工具栏已添加到窗口")
        return font_toolbar
        
    except Exception as e:
        logger.error(f"添加字体调整工具栏失败: {e}")
        return None


def create_font_size_menu(parent):
    """创建字体大小菜单"""
    from PyQt5.QtWidgets import QMenu
    
    font_menu = QMenu("字体大小", parent)
    
    # 添加快速调整选项
    increase_action = QAction("增大字体 (Ctrl++)", parent)
    increase_action.setShortcut(QKeySequence("Ctrl++"))
    font_menu.addAction(increase_action)
    
    decrease_action = QAction("减小字体 (Ctrl+-)", parent)
    decrease_action.setShortcut(QKeySequence("Ctrl+-"))
    font_menu.addAction(decrease_action)
    
    reset_action = QAction("重置字体 (Ctrl+0)", parent)
    reset_action.setShortcut(QKeySequence("Ctrl+0"))
    font_menu.addAction(reset_action)
    
    font_menu.addSeparator()
    
    # 添加预设大小
    presets = [
        ("极小 (8pt)", 8),
        ("小 (9pt)", 9),
        ("正常 (10pt)", 10),
        ("中等 (11pt)", 11),
        ("大 (12pt)", 12),
        ("较大 (14pt)", 14),
        ("特大 (16pt)", 16),
        ("超大 (18pt)", 18),
        ("巨大 (20pt)", 20)
    ]
    
    for name, size in presets:
        action = QAction(name, parent)
        action.triggered.connect(lambda checked, s=size: apply_font_size_globally(s))
        font_menu.addAction(action)
    
    return font_menu


def apply_font_size_globally(size):
    """全局应用字体大小"""
    try:
        app = QApplication.instance()
        if app:
            font = app.font()
            font.setPointSize(size)
            app.setFont(font)
            
            logger.info(f"全局字体大小已设置为: {size}pt")
            
    except Exception as e:
        logger.error(f"全局应用字体大小失败: {e}")
