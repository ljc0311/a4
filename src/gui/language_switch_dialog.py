#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语言切换确认对话框
防止用户意外切换语言导致数据丢失
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QCheckBox, QFrame, QTextEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

from src.models.language_models import LanguageCode
from src.utils.logger import logger


class LanguageSwitchDialog(QDialog):
    """语言切换确认对话框"""
    
    def __init__(self, current_language: LanguageCode, target_language: LanguageCode, 
                 has_unsaved_content: bool = False, parent=None):
        super().__init__(parent)
        self.current_language = current_language
        self.target_language = target_language
        self.has_unsaved_content = has_unsaved_content
        self.user_confirmed = False
        self.dont_ask_again = False
        
        self.setWindowTitle("语言切换确认")
        self.setModal(True)
        self.setFixedSize(450, 300)
        
        self.init_ui()
        self.setup_styles()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("确认语言切换")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 语言切换信息
        info_layout = QVBoxLayout()
        
        current_lang_text = "中文" if self.current_language == LanguageCode.CHINESE else "English"
        target_lang_text = "中文" if self.target_language == LanguageCode.CHINESE else "English"
        
        switch_info = QLabel(f"您正在将内容语言从 <b>{current_lang_text}</b> 切换到 <b>{target_lang_text}</b>")
        switch_info.setWordWrap(True)
        switch_info.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(switch_info)
        
        # 警告信息
        if self.has_unsaved_content:
            warning_label = QLabel("⚠️ 检测到未保存的内容")
            warning_label.setStyleSheet("color: #ff6b35; font-weight: bold;")
            warning_label.setAlignment(Qt.AlignCenter)
            info_layout.addWidget(warning_label)
            
            warning_text = QTextEdit()
            warning_text.setPlainText(
                "切换语言可能会影响以下内容：\n"
                "• 当前编辑的文本内容\n"
                "• 语音合成设置\n"
                "• 字幕样式配置\n"
                "• 界面显示语言\n\n"
                "建议在切换前保存当前项目。"
            )
            warning_text.setReadOnly(True)
            warning_text.setMaximumHeight(120)
            warning_text.setStyleSheet("""
                QTextEdit {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 12px;
                }
            """)
            info_layout.addWidget(warning_text)
        else:
            info_text = QLabel("切换语言将会：\n• 更新界面提示信息\n• 调整语音合成设置\n• 修改字幕样式配置")
            info_text.setWordWrap(True)
            info_text.setStyleSheet("color: #666; font-size: 12px;")
            info_layout.addWidget(info_text)
        
        layout.addLayout(info_layout)
        
        # 不再询问选项
        self.dont_ask_checkbox = QCheckBox("不再询问（直接切换语言）")
        self.dont_ask_checkbox.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(self.dont_ask_checkbox)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # 确认按钮
        confirm_btn = QPushButton("确认切换")
        confirm_btn.setMinimumWidth(80)
        confirm_btn.setDefault(True)
        confirm_btn.clicked.connect(self.accept)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def setup_styles(self):
        """设置样式"""
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:default {
                background-color: #007bff;
                color: white;
                border-color: #007bff;
            }
            QPushButton:default:hover {
                background-color: #0056b3;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #ccc;
                background-color: white;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #007bff;
                background-color: #007bff;
                border-radius: 2px;
            }
        """)
    
    def accept(self):
        """用户确认切换"""
        self.user_confirmed = True
        self.dont_ask_again = self.dont_ask_checkbox.isChecked()
        logger.info(f"用户确认语言切换: {self.current_language.value} -> {self.target_language.value}")
        if self.dont_ask_again:
            logger.info("用户选择不再询问语言切换确认")
        super().accept()
    
    def reject(self):
        """用户取消切换"""
        self.user_confirmed = False
        logger.info("用户取消语言切换")
        super().reject()
    
    @staticmethod
    def show_confirmation(current_language: LanguageCode, target_language: LanguageCode, 
                         has_unsaved_content: bool = False, parent=None) -> tuple[bool, bool]:
        """
        显示语言切换确认对话框
        
        Args:
            current_language: 当前语言
            target_language: 目标语言
            has_unsaved_content: 是否有未保存内容
            parent: 父窗口
            
        Returns:
            tuple: (是否确认切换, 是否不再询问)
        """
        dialog = LanguageSwitchDialog(current_language, target_language, has_unsaved_content, parent)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            return dialog.user_confirmed, dialog.dont_ask_again
        else:
            return False, False