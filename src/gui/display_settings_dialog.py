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
                            QGroupBox, QComboBox, QMessageBox, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from src.utils.logger import logger


class DisplaySettingsDialog(QDialog):
    """显示设置对话框"""
    
    settings_changed = pyqtSignal()  # 设置改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("显示设置")
        self.setModal(True)
        self.resize(400, 500)
        
        # 当前设置
        self.current_settings = self.load_settings()
        
        self.setup_ui()
        self.load_current_settings()
        
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        
        # 字体设置组
        font_group = QGroupBox("字体设置")
        font_layout = QVBoxLayout(font_group)
        
        # 字体大小
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("字体大小:"))
        
        self.font_size_slider = QSlider(Qt.Horizontal)
        self.font_size_slider.setRange(8, 20)
        self.font_size_slider.setValue(10)
        self.font_size_slider.valueChanged.connect(self.on_font_size_changed)
        
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 20)
        self.font_size_spinbox.setValue(10)
        self.font_size_spinbox.valueChanged.connect(self.on_font_size_spinbox_changed)
        
        font_size_layout.addWidget(self.font_size_slider)
        font_size_layout.addWidget(self.font_size_spinbox)
        font_layout.addLayout(font_size_layout)
        
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
        font_layout.addLayout(font_family_layout)
        
        layout.addWidget(font_group)
        
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
        
        # 窗口设置组
        window_group = QGroupBox("窗口设置")
        window_layout = QVBoxLayout(window_group)
        
        # 自动调整窗口大小
        self.auto_resize_checkbox = QCheckBox("自动调整窗口大小")
        self.auto_resize_checkbox.setChecked(True)
        window_layout.addWidget(self.auto_resize_checkbox)
        
        layout.addWidget(window_group)
        
        # 预览区域
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("这是预览文本 - This is preview text")
        self.preview_label.setStyleSheet("border: 1px solid gray; padding: 10px;")
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(preview_group)
        
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
        
        layout.addLayout(button_layout)
        
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
