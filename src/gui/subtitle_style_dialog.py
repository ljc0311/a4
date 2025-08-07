#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕样式编辑对话框
提供字幕样式的可视化编辑界面，支持实时预览
"""

import sys
from typing import Dict, Any, Optional, Callable
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, 
    QPushButton, QColorDialog, QCheckBox, QSlider, QGroupBox,
    QTextEdit, QFrame, QSizePolicy, QScrollArea, QWidget,
    QButtonGroup, QRadioButton, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QPainter

from src.models.language_models import (
    SubtitleSettings, LanguageCode, SubtitlePosition, WordWrapStyle
)
from src.services.subtitle_service import SubtitleFormatter
from src.core.language_manager import LanguageManager
from src.utils.logger import logger


class ColorButton(QPushButton):
    """颜色选择按钮"""
    colorChanged = pyqtSignal(str)
    
    def __init__(self, color: str = "#FFFFFF", parent=None):
        super().__init__(parent)
        self.current_color = color
        self.setFixedSize(40, 30)
        self.update_color_display()
        self.clicked.connect(self.choose_color)
    
    def update_color_display(self):
        """更新颜色显示"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color};
                border: 2px solid #666;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #999;
            }}
        """)
    
    def choose_color(self):
        """选择颜色"""
        color = QColorDialog.getColor(QColor(self.current_color), self)
        if color.isValid():
            self.current_color = color.name()
            self.update_color_display()
            self.colorChanged.emit(self.current_color)
    
    def set_color(self, color: str):
        """设置颜色"""
        self.current_color = color
        self.update_color_display()


class SubtitlePreviewWidget(QWidget):
    """字幕预览组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 200)
        self.setStyleSheet("background-color: #000000; border: 1px solid #666;")
        
        self.subtitle_settings = SubtitleSettings()
        self.preview_text = "这是字幕预览文本\nThis is subtitle preview text"
        
    def update_preview(self, settings: SubtitleSettings):
        """更新预览"""
        self.subtitle_settings = settings
        self.update()
    
    def set_preview_text(self, text: str):
        """设置预览文本"""
        self.preview_text = text
        self.update()
    
    def paintEvent(self, event):
        """绘制预览"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置字体
        font = QFont(self.subtitle_settings.font_family, self.subtitle_settings.font_size)
        if self.subtitle_settings.font_weight == "bold":
            font.setBold(True)
        if self.subtitle_settings.font_style == "italic":
            font.setItalic(True)
        painter.setFont(font)
        
        # 计算文本位置
        rect = self.rect()
        text_rect = painter.fontMetrics().boundingRect(rect, Qt.AlignCenter, self.preview_text)
        
        # 根据位置设置调整
        if self.subtitle_settings.position == SubtitlePosition.BOTTOM:
            y_offset = rect.height() - text_rect.height() - self.subtitle_settings.margin_bottom
        elif self.subtitle_settings.position == SubtitlePosition.TOP:
            y_offset = self.subtitle_settings.margin_bottom
        else:  # CENTER
            y_offset = (rect.height() - text_rect.height()) // 2
        
        text_rect.moveTop(y_offset)
        
        # 绘制背景
        if self.subtitle_settings.background_enabled:
            bg_color = QColor(self.subtitle_settings.background_color)
            bg_color.setAlphaF(self.subtitle_settings.background_opacity)
            painter.fillRect(text_rect.adjusted(
                -self.subtitle_settings.background_padding,
                -self.subtitle_settings.background_padding,
                self.subtitle_settings.background_padding,
                self.subtitle_settings.background_padding
            ), bg_color)
        
        # 绘制阴影
        if self.subtitle_settings.shadow_enabled:
            shadow_color = QColor(self.subtitle_settings.shadow_color)
            painter.setPen(shadow_color)
            shadow_rect = text_rect.adjusted(
                self.subtitle_settings.shadow_offset_x,
                self.subtitle_settings.shadow_offset_y,
                self.subtitle_settings.shadow_offset_x,
                self.subtitle_settings.shadow_offset_y
            )
            painter.drawText(shadow_rect, Qt.AlignCenter, self.preview_text)
        
        # 绘制描边
        if self.subtitle_settings.border_enabled:
            border_color = QColor(self.subtitle_settings.border_color)
            painter.setPen(border_color)
            for dx in range(-self.subtitle_settings.border_width, self.subtitle_settings.border_width + 1):
                for dy in range(-self.subtitle_settings.border_width, self.subtitle_settings.border_width + 1):
                    if dx != 0 or dy != 0:
                        border_rect = text_rect.adjusted(dx, dy, dx, dy)
                        painter.drawText(border_rect, Qt.AlignCenter, self.preview_text)
        
        # 绘制主文本
        text_color = QColor(self.subtitle_settings.font_color)
        painter.setPen(text_color)
        painter.drawText(text_rect, Qt.AlignCenter, self.preview_text)


class SubtitleStyleDialog(QDialog):
    """字幕样式编辑对话框"""
    
    settingsChanged = pyqtSignal(SubtitleSettings)
    
    def __init__(self, initial_settings: Optional[SubtitleSettings] = None, 
                 language_manager: Optional[LanguageManager] = None, parent=None):
        super().__init__(parent)
        self.language_manager = language_manager or LanguageManager()
        self.subtitle_formatter = SubtitleFormatter()
        
        # 初始化设置
        self.current_settings = initial_settings or SubtitleSettings()
        self.original_settings = SubtitleSettings.from_dict(self.current_settings.to_dict())
        
        # 设置对话框
        self.setWindowTitle("字幕样式设置")
        self.setModal(True)
        self.resize(800, 600)
        
        # 设置实时预览更新
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_preview)
        
        # 创建界面
        self.setup_ui()
        self.load_settings()
        
        logger.info("字幕样式编辑对话框初始化完成")
    
    def setup_ui(self):
        """设置用户界面"""
        layout = QHBoxLayout(self)
        
        # 左侧：设置面板
        settings_widget = self.create_settings_panel()
        layout.addWidget(settings_widget, 2)
        
        # 右侧：预览面板
        preview_widget = self.create_preview_panel()
        layout.addWidget(preview_widget, 1)
    
    def create_settings_panel(self) -> QWidget:
        """创建设置面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 字体标签页
        font_tab = self.create_font_tab()
        tab_widget.addTab(font_tab, "字体设置")
        
        # 颜色标签页
        color_tab = self.create_color_tab()
        tab_widget.addTab(color_tab, "颜色设置")
        
        # 位置标签页
        position_tab = self.create_position_tab()
        tab_widget.addTab(position_tab, "位置设置")
        
        # 效果标签页
        effects_tab = self.create_effects_tab()
        tab_widget.addTab(effects_tab, "特效设置")
        
        layout.addWidget(tab_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 重置按钮
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset_settings)
        button_layout.addWidget(reset_btn)
        
        # 预设按钮
        preset_btn = QPushButton("应用预设")
        preset_btn.clicked.connect(self.apply_preset)
        button_layout.addWidget(preset_btn)
        
        button_layout.addStretch()
        
        # 确定/取消按钮
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        return widget
    
    def create_font_tab(self) -> QWidget:
        """创建字体设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 字体选择组
        font_group = QGroupBox("字体选择")
        font_layout = QGridLayout(font_group)
        
        # 字体族
        font_layout.addWidget(QLabel("字体:"), 0, 0)
        self.font_combo = QComboBox()
        self.populate_font_combo()
        self.font_combo.currentTextChanged.connect(self.on_setting_changed)
        font_layout.addWidget(self.font_combo, 0, 1)
        
        # 字体大小
        font_layout.addWidget(QLabel("大小:"), 1, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)
        self.font_size_spin.valueChanged.connect(self.on_setting_changed)
        font_layout.addWidget(self.font_size_spin, 1, 1)
        
        # 字体粗细
        font_layout.addWidget(QLabel("粗细:"), 2, 0)
        self.font_weight_combo = QComboBox()
        self.font_weight_combo.addItems(["normal", "bold"])
        self.font_weight_combo.currentTextChanged.connect(self.on_setting_changed)
        font_layout.addWidget(self.font_weight_combo, 2, 1)
        
        # 字体样式
        font_layout.addWidget(QLabel("样式:"), 3, 0)
        self.font_style_combo = QComboBox()
        self.font_style_combo.addItems(["normal", "italic"])
        self.font_style_combo.currentTextChanged.connect(self.on_setting_changed)
        font_layout.addWidget(self.font_style_combo, 3, 1)
        
        layout.addWidget(font_group)
        
        # 文本格式组
        format_group = QGroupBox("文本格式")
        format_layout = QGridLayout(format_group)
        
        # 对齐方式
        format_layout.addWidget(QLabel("对齐:"), 0, 0)
        self.text_align_combo = QComboBox()
        self.text_align_combo.addItems(["left", "center", "right"])
        self.text_align_combo.currentTextChanged.connect(self.on_setting_changed)
        format_layout.addWidget(self.text_align_combo, 0, 1)
        
        # 行间距
        format_layout.addWidget(QLabel("行间距:"), 1, 0)
        self.line_spacing_spin = QDoubleSpinBox()
        self.line_spacing_spin.setRange(0.5, 3.0)
        self.line_spacing_spin.setSingleStep(0.1)
        self.line_spacing_spin.valueChanged.connect(self.on_setting_changed)
        format_layout.addWidget(self.line_spacing_spin, 1, 1)
        
        # 每行最大字符数
        format_layout.addWidget(QLabel("每行字符数:"), 2, 0)
        self.max_chars_spin = QSpinBox()
        self.max_chars_spin.setRange(10, 100)
        self.max_chars_spin.valueChanged.connect(self.on_setting_changed)
        format_layout.addWidget(self.max_chars_spin, 2, 1)
        
        # 换行方式
        format_layout.addWidget(QLabel("换行方式:"), 3, 0)
        self.wrap_style_combo = QComboBox()
        self.wrap_style_combo.addItems(["character", "word"])
        self.wrap_style_combo.currentTextChanged.connect(self.on_setting_changed)
        format_layout.addWidget(self.wrap_style_combo, 3, 1)
        
        layout.addWidget(format_group)
        layout.addStretch()
        
        return widget
    
    def create_color_tab(self) -> QWidget:
        """创建颜色设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 文字颜色组
        text_color_group = QGroupBox("文字颜色")
        text_color_layout = QGridLayout(text_color_group)
        
        text_color_layout.addWidget(QLabel("文字颜色:"), 0, 0)
        self.font_color_btn = ColorButton(self.current_settings.font_color)
        self.font_color_btn.colorChanged.connect(self.on_setting_changed)
        text_color_layout.addWidget(self.font_color_btn, 0, 1)
        
        layout.addWidget(text_color_group)
        
        # 描边设置组
        stroke_group = QGroupBox("描边设置")
        stroke_layout = QGridLayout(stroke_group)
        
        self.border_enabled_check = QCheckBox("启用描边")
        self.border_enabled_check.toggled.connect(self.on_setting_changed)
        stroke_layout.addWidget(self.border_enabled_check, 0, 0, 1, 2)
        
        stroke_layout.addWidget(QLabel("描边颜色:"), 1, 0)
        self.border_color_btn = ColorButton(self.current_settings.border_color)
        self.border_color_btn.colorChanged.connect(self.on_setting_changed)
        stroke_layout.addWidget(self.border_color_btn, 1, 1)
        
        stroke_layout.addWidget(QLabel("描边宽度:"), 2, 0)
        self.border_width_spin = QSpinBox()
        self.border_width_spin.setRange(0, 10)
        self.border_width_spin.valueChanged.connect(self.on_setting_changed)
        stroke_layout.addWidget(self.border_width_spin, 2, 1)
        
        layout.addWidget(stroke_group)
        
        # 阴影设置组
        shadow_group = QGroupBox("阴影设置")
        shadow_layout = QGridLayout(shadow_group)
        
        self.shadow_enabled_check = QCheckBox("启用阴影")
        self.shadow_enabled_check.toggled.connect(self.on_setting_changed)
        shadow_layout.addWidget(self.shadow_enabled_check, 0, 0, 1, 2)
        
        shadow_layout.addWidget(QLabel("阴影颜色:"), 1, 0)
        self.shadow_color_btn = ColorButton(self.current_settings.shadow_color)
        self.shadow_color_btn.colorChanged.connect(self.on_setting_changed)
        shadow_layout.addWidget(self.shadow_color_btn, 1, 1)
        
        shadow_layout.addWidget(QLabel("水平偏移:"), 2, 0)
        self.shadow_offset_x_spin = QSpinBox()
        self.shadow_offset_x_spin.setRange(-20, 20)
        self.shadow_offset_x_spin.valueChanged.connect(self.on_setting_changed)
        shadow_layout.addWidget(self.shadow_offset_x_spin, 2, 1)
        
        shadow_layout.addWidget(QLabel("垂直偏移:"), 3, 0)
        self.shadow_offset_y_spin = QSpinBox()
        self.shadow_offset_y_spin.setRange(-20, 20)
        self.shadow_offset_y_spin.valueChanged.connect(self.on_setting_changed)
        shadow_layout.addWidget(self.shadow_offset_y_spin, 3, 1)
        
        shadow_layout.addWidget(QLabel("模糊半径:"), 4, 0)
        self.shadow_blur_spin = QSpinBox()
        self.shadow_blur_spin.setRange(0, 20)
        self.shadow_blur_spin.valueChanged.connect(self.on_setting_changed)
        shadow_layout.addWidget(self.shadow_blur_spin, 4, 1)
        
        layout.addWidget(shadow_group)
        
        # 背景设置组
        bg_group = QGroupBox("背景设置")
        bg_layout = QGridLayout(bg_group)
        
        self.background_enabled_check = QCheckBox("启用背景")
        self.background_enabled_check.toggled.connect(self.on_setting_changed)
        bg_layout.addWidget(self.background_enabled_check, 0, 0, 1, 2)
        
        bg_layout.addWidget(QLabel("背景颜色:"), 1, 0)
        self.background_color_btn = ColorButton(self.current_settings.background_color)
        self.background_color_btn.colorChanged.connect(self.on_setting_changed)
        bg_layout.addWidget(self.background_color_btn, 1, 1)
        
        bg_layout.addWidget(QLabel("透明度:"), 2, 0)
        self.background_opacity_spin = QDoubleSpinBox()
        self.background_opacity_spin.setRange(0.0, 1.0)
        self.background_opacity_spin.setSingleStep(0.1)
        self.background_opacity_spin.valueChanged.connect(self.on_setting_changed)
        bg_layout.addWidget(self.background_opacity_spin, 2, 1)
        
        bg_layout.addWidget(QLabel("内边距:"), 3, 0)
        self.background_padding_spin = QSpinBox()
        self.background_padding_spin.setRange(0, 50)
        self.background_padding_spin.valueChanged.connect(self.on_setting_changed)
        bg_layout.addWidget(self.background_padding_spin, 3, 1)
        
        layout.addWidget(bg_group)
        layout.addStretch()
        
        return widget
    
    def create_position_tab(self) -> QWidget:
        """创建位置设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 位置设置组
        position_group = QGroupBox("字幕位置")
        position_layout = QGridLayout(position_group)
        
        # 位置选择
        position_layout.addWidget(QLabel("位置:"), 0, 0)
        self.position_combo = QComboBox()
        self.position_combo.addItems(["bottom", "center", "top"])
        self.position_combo.currentTextChanged.connect(self.on_setting_changed)
        position_layout.addWidget(self.position_combo, 0, 1)
        
        # 边距
        position_layout.addWidget(QLabel("边距:"), 1, 0)
        self.margin_bottom_spin = QSpinBox()
        self.margin_bottom_spin.setRange(0, 200)
        self.margin_bottom_spin.valueChanged.connect(self.on_setting_changed)
        position_layout.addWidget(self.margin_bottom_spin, 1, 1)
        
        layout.addWidget(position_group)
        layout.addStretch()
        
        return widget
    
    def create_effects_tab(self) -> QWidget:
        """创建特效设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 动画设置组
        animation_group = QGroupBox("动画效果")
        animation_layout = QGridLayout(animation_group)
        
        self.animation_enabled_check = QCheckBox("启用动画")
        self.animation_enabled_check.toggled.connect(self.on_setting_changed)
        animation_layout.addWidget(self.animation_enabled_check, 0, 0, 1, 2)
        
        animation_layout.addWidget(QLabel("动画类型:"), 1, 0)
        self.animation_type_combo = QComboBox()
        self.animation_type_combo.addItems(["fade", "slide", "typewriter"])
        self.animation_type_combo.currentTextChanged.connect(self.on_setting_changed)
        animation_layout.addWidget(self.animation_type_combo, 1, 1)
        
        animation_layout.addWidget(QLabel("持续时长倍数:"), 2, 0)
        self.duration_multiplier_spin = QDoubleSpinBox()
        self.duration_multiplier_spin.setRange(0.1, 5.0)
        self.duration_multiplier_spin.setSingleStep(0.1)
        self.duration_multiplier_spin.valueChanged.connect(self.on_setting_changed)
        animation_layout.addWidget(self.duration_multiplier_spin, 2, 1)
        
        layout.addWidget(animation_group)
        layout.addStretch()
        
        return widget
    
    def create_preview_panel(self) -> QWidget:
        """创建预览面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 预览标题
        title_label = QLabel("实时预览")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
        layout.addWidget(title_label)
        
        # 预览组件
        self.preview_widget = SubtitlePreviewWidget()
        layout.addWidget(self.preview_widget, 0, Qt.AlignCenter)
        
        # 预览文本编辑
        preview_text_label = QLabel("预览文本:")
        layout.addWidget(preview_text_label)
        
        self.preview_text_edit = QTextEdit()
        self.preview_text_edit.setMaximumHeight(100)
        self.preview_text_edit.setPlainText("这是字幕预览文本\nThis is subtitle preview text")
        self.preview_text_edit.textChanged.connect(self.on_preview_text_changed)
        layout.addWidget(self.preview_text_edit)
        
        layout.addStretch()
        
        return widget
    
    def populate_font_combo(self):
        """填充字体下拉框"""
        current_language = self.language_manager.current_language
        font_info = self.subtitle_formatter.get_language_specific_fonts(current_language, include_details=True)
        
        # 添加推荐字体（标记为推荐）
        recommended_fonts = font_info['recommended_fonts']
        for font in recommended_fonts:
            self.font_combo.addItem(f"★ {font}", font)
        
        # 添加分隔符
        self.font_combo.insertSeparator(len(recommended_fonts))
        
        # 添加其他字体
        all_fonts = font_info['all_fonts']
        other_fonts = [f for f in all_fonts if f not in recommended_fonts]
        for font in other_fonts:
            self.font_combo.addItem(font, font)
    
    def load_settings(self):
        """加载设置到界面"""
        # 字体设置
        font_index = self.font_combo.findData(self.current_settings.font_family)
        if font_index >= 0:
            self.font_combo.setCurrentIndex(font_index)
        
        self.font_size_spin.setValue(self.current_settings.font_size)
        self.font_weight_combo.setCurrentText(self.current_settings.font_weight)
        self.font_style_combo.setCurrentText(self.current_settings.font_style)
        self.text_align_combo.setCurrentText(self.current_settings.text_align)
        self.line_spacing_spin.setValue(self.current_settings.line_spacing)
        self.max_chars_spin.setValue(self.current_settings.max_chars_per_line)
        self.wrap_style_combo.setCurrentText(self.current_settings.word_wrap_style.value)
        
        # 颜色设置
        self.font_color_btn.set_color(self.current_settings.font_color)
        self.border_enabled_check.setChecked(self.current_settings.border_enabled)
        self.border_color_btn.set_color(self.current_settings.border_color)
        self.border_width_spin.setValue(self.current_settings.border_width)
        
        self.shadow_enabled_check.setChecked(self.current_settings.shadow_enabled)
        self.shadow_color_btn.set_color(self.current_settings.shadow_color)
        self.shadow_offset_x_spin.setValue(self.current_settings.shadow_offset_x)
        self.shadow_offset_y_spin.setValue(self.current_settings.shadow_offset_y)
        self.shadow_blur_spin.setValue(self.current_settings.shadow_blur)
        
        self.background_enabled_check.setChecked(self.current_settings.background_enabled)
        self.background_color_btn.set_color(self.current_settings.background_color)
        self.background_opacity_spin.setValue(self.current_settings.background_opacity)
        self.background_padding_spin.setValue(self.current_settings.background_padding)
        
        # 位置设置
        self.position_combo.setCurrentText(self.current_settings.position.value)
        self.margin_bottom_spin.setValue(self.current_settings.margin_bottom)
        
        # 特效设置
        self.animation_enabled_check.setChecked(self.current_settings.animation_enabled)
        self.animation_type_combo.setCurrentText(self.current_settings.animation_type)
        self.duration_multiplier_spin.setValue(self.current_settings.duration_multiplier)
        
        # 更新预览
        self.update_preview()
    
    def on_setting_changed(self):
        """设置改变时的处理"""
        # 延迟更新预览，避免频繁更新
        self.preview_timer.start(100)
    
    def on_preview_text_changed(self):
        """预览文本改变时的处理"""
        text = self.preview_text_edit.toPlainText()
        self.preview_widget.set_preview_text(text)
    
    def update_preview(self):
        """更新预览"""
        # 从界面获取当前设置
        settings = self.get_current_settings()
        
        # 更新预览组件
        self.preview_widget.update_preview(settings)
        
        # 发送设置改变信号
        self.settingsChanged.emit(settings)
    
    def get_current_settings(self) -> SubtitleSettings:
        """从界面获取当前设置"""
        font_family = self.font_combo.currentData() or self.font_combo.currentText()
        if font_family.startswith("★ "):
            font_family = font_family[2:]  # 移除推荐标记
        
        return SubtitleSettings(
            font_family=font_family,
            font_size=self.font_size_spin.value(),
            font_color=self.font_color_btn.current_color,
            background_color=self.background_color_btn.current_color,
            background_opacity=self.background_opacity_spin.value(),
            position=SubtitlePosition(self.position_combo.currentText()),
            line_spacing=self.line_spacing_spin.value(),
            max_chars_per_line=self.max_chars_spin.value(),
            word_wrap_style=WordWrapStyle(self.wrap_style_combo.currentText()),
            margin_bottom=self.margin_bottom_spin.value(),
            stroke_color=self.border_color_btn.current_color,
            stroke_width=self.border_width_spin.value(),
            font_weight=self.font_weight_combo.currentText(),
            font_style=self.font_style_combo.currentText(),
            text_align=self.text_align_combo.currentText(),
            shadow_enabled=self.shadow_enabled_check.isChecked(),
            shadow_color=self.shadow_color_btn.current_color,
            shadow_offset_x=self.shadow_offset_x_spin.value(),
            shadow_offset_y=self.shadow_offset_y_spin.value(),
            shadow_blur=self.shadow_blur_spin.value(),
            border_enabled=self.border_enabled_check.isChecked(),
            border_color=self.border_color_btn.current_color,
            border_width=self.border_width_spin.value(),
            background_enabled=self.background_enabled_check.isChecked(),
            background_padding=self.background_padding_spin.value(),
            animation_enabled=self.animation_enabled_check.isChecked(),
            animation_type=self.animation_type_combo.currentText(),
            duration_multiplier=self.duration_multiplier_spin.value()
        )
    
    def reset_settings(self):
        """重置设置"""
        self.current_settings = SubtitleSettings()
        self.load_settings()
    
    def apply_preset(self):
        """应用预设"""
        current_language = self.language_manager.current_language
        
        if current_language == LanguageCode.CHINESE:
            # 中文预设
            preset = SubtitleSettings(
                font_family="Microsoft YaHei",
                font_size=24,
                font_color="#FFFFFF",
                border_enabled=True,
                border_color="#000000",
                border_width=2,
                shadow_enabled=True,
                shadow_color="#000000",
                shadow_offset_x=2,
                shadow_offset_y=2,
                position=SubtitlePosition.BOTTOM,
                max_chars_per_line=20,
                word_wrap_style=WordWrapStyle.CHARACTER
            )
        else:
            # 英文预设
            preset = SubtitleSettings(
                font_family="Arial",
                font_size=22,
                font_color="#FFFFFF",
                border_enabled=True,
                border_color="#000000",
                border_width=1,
                shadow_enabled=True,
                shadow_color="#000000",
                shadow_offset_x=1,
                shadow_offset_y=1,
                position=SubtitlePosition.BOTTOM,
                max_chars_per_line=40,
                word_wrap_style=WordWrapStyle.WORD
            )
        
        self.current_settings = preset
        self.load_settings()
    
    def accept(self):
        """确定按钮处理"""
        self.current_settings = self.get_current_settings()
        super().accept()
    
    def reject(self):
        """取消按钮处理"""
        self.current_settings = self.original_settings
        super().reject()
    
    def get_settings(self) -> SubtitleSettings:
        """获取最终设置"""
        return self.current_settings


# 测试代码
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 创建测试对话框
    dialog = SubtitleStyleDialog()
    
    if dialog.exec_() == QDialog.Accepted:
        settings = dialog.get_settings()
        print("用户确认的设置:")
        print(settings.to_dict())
    else:
        print("用户取消了设置")
    
    sys.exit()