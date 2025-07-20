#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI工具函数
提供通用的UI相关工具函数
"""

from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon

try:
    from src.utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def show_success(message, title="成功", duration=3000):
    """显示成功消息"""
    try:
        # 创建消息框
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # 设置样式
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: white;
                color: #333333;
                font-size: 12px;
            }
            QMessageBox QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 60px;
            }
            QMessageBox QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        # 显示消息框
        msg_box.exec_()
        
        logger.info(f"显示成功消息: {message}")
        
    except Exception as e:
        logger.error(f"显示成功消息失败: {e}")
        print(f"成功: {message}")  # 备用显示方式


def show_error(message, title="错误"):
    """显示错误消息"""
    try:
        # 创建消息框
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # 设置样式
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: white;
                color: #333333;
                font-size: 12px;
            }
            QMessageBox QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 60px;
            }
            QMessageBox QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        
        # 显示消息框
        msg_box.exec_()
        
        logger.error(f"显示错误消息: {message}")
        
    except Exception as e:
        logger.error(f"显示错误消息失败: {e}")
        print(f"错误: {message}")  # 备用显示方式


def show_warning(message, title="警告"):
    """显示警告消息"""
    try:
        # 创建消息框
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # 设置样式
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: white;
                color: #333333;
                font-size: 12px;
            }
            QMessageBox QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 60px;
            }
            QMessageBox QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        
        # 显示消息框
        msg_box.exec_()
        
        logger.warning(f"显示警告消息: {message}")
        
    except Exception as e:
        logger.error(f"显示警告消息失败: {e}")
        print(f"警告: {message}")  # 备用显示方式


def show_info(message, title="信息"):
    """显示信息消息"""
    try:
        # 创建消息框
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # 设置样式
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: white;
                color: #333333;
                font-size: 12px;
            }
            QMessageBox QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 60px;
            }
            QMessageBox QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        # 显示消息框
        msg_box.exec_()
        
        logger.info(f"显示信息消息: {message}")
        
    except Exception as e:
        logger.error(f"显示信息消息失败: {e}")
        print(f"信息: {message}")  # 备用显示方式


def confirm_dialog(message, title="确认"):
    """显示确认对话框"""
    try:
        # 创建消息框
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        # 设置样式
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: white;
                color: #333333;
                font-size: 12px;
            }
            QMessageBox QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 60px;
                margin: 2px;
            }
            QMessageBox QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        # 显示消息框并返回结果
        result = msg_box.exec_()
        
        logger.info(f"确认对话框: {message}, 结果: {result == QMessageBox.Yes}")
        
        return result == QMessageBox.Yes
        
    except Exception as e:
        logger.error(f"显示确认对话框失败: {e}")
        return False


def center_window(window, parent=None):
    """将窗口居中显示"""
    try:
        if parent:
            # 相对于父窗口居中
            parent_geometry = parent.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - window.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - window.height()) // 2
        else:
            # 相对于屏幕居中
            screen = QApplication.desktop().screenGeometry()
            x = (screen.width() - window.width()) // 2
            y = (screen.height() - window.height()) // 2
        
        window.move(x, y)
        
    except Exception as e:
        logger.error(f"窗口居中失败: {e}")


def apply_modern_style(widget):
    """应用现代化样式"""
    try:
        widget.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
                color: #333333;
                font-family: "Microsoft YaHei UI", Arial, sans-serif;
                font-size: 12px;
            }
            QPushButton {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 6px 12px;
                color: #333333;
                font-size: 12px;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
                border-color: #999999;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
            }
            QLineEdit, QTextEdit {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 4px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #2196F3;
            }
        """)
        
    except Exception as e:
        logger.error(f"应用现代化样式失败: {e}")
