#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
显示设置对话框
允许用户调整字体大小、DPI缩放等显示设置
"""

import json
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QSlider, QSpinBox, QCheckBox, QPushButton,
                            QGroupBox, QComboBox, QMessageBox, QApplication,
                            QFormLayout, QTabWidget, QWidget, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QFontDatabase
from src.utils.logger import logger
from src.utils.dpi_adapter import get_dpi_adapter


class DisplaySettingsDialog(QDialog):
    """显示设置对话框"""
    
    settings_changed = pyqtSignal()  # 设置改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("显示设置")
        self.setModal(True)
        self.resize(500, 600)

        # DPI适配器
        self.dpi_adapter = get_dpi_adapter()

        # 当前设置
        self.current_settings = self.load_settings()

        self.setup_ui()
        self.load_current_settings()
        self.connect_signals()
        
    def setup_ui(self):
        """设置界面 - 增强版"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 字体设置标签页
        font_tab = self.create_font_tab()
        self.tab_widget.addTab(font_tab, "字体设置")

        # DPI缩放标签页
        dpi_tab = self.create_dpi_tab()
        self.tab_widget.addTab(dpi_tab, "DPI缩放")

        # 窗口设置标签页
        window_tab = self.create_window_tab()
        self.tab_widget.addTab(window_tab, "窗口设置")

        # 预览区域
        self.create_preview_area(layout)

        # 按钮区域
        self.create_button_area(layout)

    def create_font_tab(self):
        """创建字体设置标签页"""
        font_widget = QWidget()
        layout = QVBoxLayout(font_widget)

        # 字体大小设置组
        font_size_group = QGroupBox("字体大小")
        font_size_layout = QFormLayout(font_size_group)

        # 字体大小滑块和数值
        font_size_control_layout = QHBoxLayout()

        self.font_size_slider = QSlider(Qt.Horizontal)
        self.font_size_slider.setRange(8, 20)
        self.font_size_slider.setValue(self.dpi_adapter.current_font_size)
        self.font_size_slider.valueChanged.connect(self.on_font_size_changed)

        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 20)
        self.font_size_spinbox.setValue(self.dpi_adapter.current_font_size)
        self.font_size_spinbox.valueChanged.connect(self.on_font_size_spinbox_changed)
        
        font_size_control_layout.addWidget(self.font_size_slider)
        font_size_control_layout.addWidget(self.font_size_spinbox)

        font_size_layout.addRow("字体大小:", font_size_control_layout)
        
        # 字体族
        font_family_layout = QHBoxLayout()
        font_family_layout.addWidget(QLabel("字体:"))
        
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems([
            "Microsoft YaHei UI",
            "SimSun",
            "SimHei", 
            "Arial",
            "Segoe UI",
            "Tahoma"
        ])
        self.font_family_combo.currentTextChanged.connect(self.on_font_family_changed)
        
        font_family_layout.addWidget(self.font_family_combo)
        font_size_layout.addRow("字体族:", font_family_layout)

        layout.addWidget(font_size_group)

        return font_widget

    def create_dpi_tab(self):
        """创建DPI缩放标签页"""
        dpi_widget = QWidget()
        layout = QVBoxLayout(dpi_widget)

        # DPI缩放设置组
        dpi_group = QGroupBox("DPI缩放设置")
        dpi_layout = QVBoxLayout(dpi_group)
        
        # 自动DPI缩放
        self.auto_dpi_checkbox = QCheckBox("自动DPI缩放")
        self.auto_dpi_checkbox.setChecked(True)
        self.auto_dpi_checkbox.toggled.connect(self.on_auto_dpi_toggled)
        dpi_layout.addWidget(self.auto_dpi_checkbox)
        
        # 自定义缩放因子
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("缩放因子:"))
        
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(50, 300)  # 0.5x 到 3.0x
        self.scale_slider.setValue(100)  # 1.0x
        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        
        self.scale_label = QLabel("100%")
        self.scale_label.setMinimumWidth(50)
        
        scale_layout.addWidget(self.scale_slider)
        scale_layout.addWidget(self.scale_label)
        dpi_layout.addLayout(scale_layout)
        
        layout.addWidget(dpi_group)

        return dpi_widget

    def create_window_tab(self):
        """创建窗口设置标签页"""
        window_widget = QWidget()
        layout = QVBoxLayout(window_widget)

        # 窗口设置组
        window_group = QGroupBox("窗口设置")
        window_layout = QVBoxLayout(window_group)
        
        # 自动调整窗口大小
        self.auto_resize_checkbox = QCheckBox("自动调整窗口大小")
        self.auto_resize_checkbox.setChecked(True)
        window_layout.addWidget(self.auto_resize_checkbox)
        
        layout.addWidget(window_group)

        return window_widget

    def create_preview_area(self, parent_layout):
        """创建预览区域"""
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_label = QLabel("这是预览文本 - This is preview text\n字体大小和样式预览")
        self.preview_label.setStyleSheet("border: 1px solid gray; padding: 10px; min-height: 60px;")
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)

        parent_layout.addWidget(preview_group)

    def create_button_area(self, parent_layout):
        """创建按钮区域"""
        # 按钮
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("应用")
        self.apply_button.clicked.connect(self.apply_settings)
        
        self.reset_button = QPushButton("重置")
        self.reset_button.clicked.connect(self.reset_settings)
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept_settings)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        parent_layout.addLayout(button_layout)

    def connect_signals(self):
        """连接信号"""
        # 信号连接已在控件创建时完成
        pass

    def load_settings(self):
        """加载设置"""
        try:
            config_path = os.path.join("config", "display_settings.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载显示设置失败: {e}")
            
        # 默认设置
        return {
            "display": {
                "auto_dpi_scaling": True,
                "custom_scale_factor": 1.0,
                "font_family": "Microsoft YaHei UI",
                "base_font_size": 10,
                "window_size": {
                    "width": 1200,
                    "height": 800,
                    "auto_resize": True
                }
            }
        }
        
    def save_settings(self):
        """保存设置"""
        try:
            config_dir = "config"
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            config_path = os.path.join(config_dir, "display_settings.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_settings, f, indent=4, ensure_ascii=False)
                
            logger.info("显示设置已保存")
            
        except Exception as e:
            logger.error(f"保存显示设置失败: {e}")
            QMessageBox.warning(self, "警告", f"保存设置失败: {e}")
            
    def load_current_settings(self):
        """加载当前设置到界面"""
        display = self.current_settings.get("display", {})
        
        # 字体设置
        font_size = display.get("base_font_size", 10)
        self.font_size_slider.setValue(font_size)
        self.font_size_spinbox.setValue(font_size)
        
        font_family = display.get("font_family", "Microsoft YaHei UI")
        index = self.font_family_combo.findText(font_family)
        if index >= 0:
            self.font_family_combo.setCurrentIndex(index)
            
        # DPI设置
        auto_dpi = display.get("auto_dpi_scaling", True)
        self.auto_dpi_checkbox.setChecked(auto_dpi)
        
        scale_factor = display.get("custom_scale_factor", 1.0)
        self.scale_slider.setValue(int(scale_factor * 100))
        self.scale_label.setText(f"{int(scale_factor * 100)}%")
        
        # 窗口设置
        window_size = display.get("window_size", {})
        auto_resize = window_size.get("auto_resize", True)
        self.auto_resize_checkbox.setChecked(auto_resize)
        
        # 更新预览
        self.update_preview()
        
    def on_font_size_changed(self, value):
        """字体大小滑块改变"""
        self.font_size_spinbox.setValue(value)
        self.update_preview()
        
    def on_font_size_spinbox_changed(self, value):
        """字体大小输入框改变"""
        self.font_size_slider.setValue(value)
        self.update_preview()
        
    def on_font_family_changed(self, family):
        """字体族改变"""
        self.update_preview()
        
    def on_auto_dpi_toggled(self, checked):
        """自动DPI切换"""
        self.scale_slider.setEnabled(not checked)
        
    def on_scale_changed(self, value):
        """缩放因子改变"""
        scale_factor = value / 100.0
        self.scale_label.setText(f"{value}%")
        self.update_preview()
        
    def update_preview(self):
        """更新预览"""
        try:
            font_size = self.font_size_spinbox.value()
            font_family = self.font_family_combo.currentText()
            
            if not self.auto_dpi_checkbox.isChecked():
                scale_factor = self.scale_slider.value() / 100.0
                font_size = int(font_size * scale_factor)
                
            font = QFont(font_family, font_size)
            self.preview_label.setFont(font)
            
        except Exception as e:
            logger.error(f"更新预览失败: {e}")
            
    def apply_settings(self):
        """应用设置"""
        try:
            # 更新设置
            display = self.current_settings.setdefault("display", {})
            display["base_font_size"] = self.font_size_spinbox.value()
            display["font_family"] = self.font_family_combo.currentText()
            display["auto_dpi_scaling"] = self.auto_dpi_checkbox.isChecked()
            display["custom_scale_factor"] = self.scale_slider.value() / 100.0
            
            window_size = display.setdefault("window_size", {})
            window_size["auto_resize"] = self.auto_resize_checkbox.isChecked()
            
            # 保存设置
            self.save_settings()
            
            # 发送信号
            self.settings_changed.emit()
            
            QMessageBox.information(self, "提示", "设置已应用，重启程序后生效")
            
        except Exception as e:
            logger.error(f"应用设置失败: {e}")
            QMessageBox.warning(self, "错误", f"应用设置失败: {e}")
            
    def reset_settings(self):
        """重置设置"""
        self.font_size_slider.setValue(10)
        self.font_size_spinbox.setValue(10)
        self.font_family_combo.setCurrentText("Microsoft YaHei UI")
        self.auto_dpi_checkbox.setChecked(True)
        self.scale_slider.setValue(100)
        self.auto_resize_checkbox.setChecked(True)
        self.update_preview()
        
    def accept_settings(self):
        """确定设置"""
        self.apply_settings()
        self.accept()
