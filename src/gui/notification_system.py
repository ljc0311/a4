#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化通知系统
提供美观的通知提示，替代传统的MessageBox
"""

import sys
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QGraphicsDropShadowEffect, QApplication, QFrame
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, 
    QRect, pyqtSignal, QPoint
)
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QPen
from enum import Enum
from typing import Optional, List
import threading
import time

class NotificationType(Enum):
    """通知类型枚举"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    LOADING = "loading"

class NotificationWidget(QWidget):
    """单个通知组件"""
    
    # 点击关闭信号
    closeRequested = pyqtSignal()
    
    def __init__(self, message: str, notification_type: NotificationType, 
                 duration: int = 3000, parent=None):
        super().__init__(parent)
        self.message = message
        self.notification_type = notification_type
        self.duration = duration
        self.is_closing = False
        
        self.init_ui()
        self.setup_animation()
        
        # 自动关闭定时器
        if duration > 0:
            self.auto_close_timer = QTimer()
            self.auto_close_timer.timeout.connect(self.start_close_animation)
            self.auto_close_timer.start(duration)
    
    def init_ui(self):
        """初始化界面"""
        # 设置窗口大小，使用系统实际要求的尺寸避免几何警告
        self.resize(350, 86)  # 使用86高度，匹配系统实际要求
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # 显示时不激活
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus  # 避免焦点问题
        )
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 8, 12, 8)
        
        # 内容框架
        content_frame = QFrame()
        content_frame.setObjectName("notification_frame")
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(16, 12, 16, 12)
        
        # 图标标签
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.icon_label)
        
        # 消息标签
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignVCenter)
        content_layout.addWidget(self.message_label, 1)
        
        # 关闭按钮
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setObjectName("close_btn")
        self.close_btn.clicked.connect(self.start_close_animation)
        content_layout.addWidget(self.close_btn)
        
        main_layout.addWidget(content_frame)
        self.setLayout(main_layout)
        
        # 设置样式
        self.apply_style()
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        content_frame.setGraphicsEffect(shadow)
    
    def apply_style(self):
        """应用样式"""
        # 根据通知类型设置不同的颜色和图标
        colors = {
            NotificationType.SUCCESS: {
                'bg': '#d4edda', 'border': '#28a745', 'text': '#155724',
                'icon': '✓', 'btn_hover': '#c3e5cb'
            },
            NotificationType.WARNING: {
                'bg': '#fff3cd', 'border': '#ffc107', 'text': '#856404',
                'icon': '⚠', 'btn_hover': '#ffeaa3'
            },
            NotificationType.ERROR: {
                'bg': '#f8d7da', 'border': '#dc3545', 'text': '#721c24',
                'icon': '✗', 'btn_hover': '#f1b6bb'
            },
            NotificationType.INFO: {
                'bg': '#d1ecf1', 'border': '#17a2b8', 'text': '#0c5460',
                'icon': 'ℹ', 'btn_hover': '#bee5eb'
            },
            NotificationType.LOADING: {
                'bg': '#e2e3e5', 'border': '#6c757d', 'text': '#383d41',
                'icon': '⟳', 'btn_hover': '#d1d2d3'
            }
        }
        
        style_config = colors[self.notification_type]
        
        # 设置图标
        self.icon_label.setText(style_config['icon'])
        
        # 应用样式表
        self.setStyleSheet(f"""
            #notification_frame {{
                background-color: {style_config['bg']};
                border: 2px solid {style_config['border']};
                border-radius: 8px;
                color: {style_config['text']};
            }}
            
            QLabel {{
                color: {style_config['text']};
                font-size: 14px;
                background: transparent;
            }}
            
            #close_btn {{
                background-color: transparent;
                border: none;
                color: {style_config['text']};
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
            }}
            
            #close_btn:hover {{
                background-color: {style_config['btn_hover']};
            }}
        """)
        
        # 设置字体
        font = QFont()
        font.setPointSize(10)
        self.message_label.setFont(font)
        
        icon_font = QFont()
        icon_font.setPointSize(14)
        icon_font.setBold(True)
        self.icon_label.setFont(icon_font)
    
    def setup_animation(self):
        """设置动画"""
        # 滑入动画
        self.slide_in_animation = QPropertyAnimation(self, b"pos")
        self.slide_in_animation.setDuration(300)
        self.slide_in_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # 滑出动画
        self.slide_out_animation = QPropertyAnimation(self, b"pos")
        self.slide_out_animation.setDuration(250)
        self.slide_out_animation.setEasingCurve(QEasingCurve.InCubic)
        self.slide_out_animation.finished.connect(self.close)
    
    def show_animation(self, start_pos: QPoint, end_pos: QPoint):
        """显示动画"""
        self.move(start_pos)
        self.show()
        
        self.slide_in_animation.setStartValue(start_pos)
        self.slide_in_animation.setEndValue(end_pos)
        self.slide_in_animation.start()
    
    def start_close_animation(self):
        """开始关闭动画"""
        if self.is_closing:
            return
            
        self.is_closing = True
        
        # 停止自动关闭定时器
        if hasattr(self, 'auto_close_timer'):
            self.auto_close_timer.stop()
        
        # 滑出动画
        current_pos = self.pos()
        end_pos = QPoint(current_pos.x() + 400, current_pos.y())
        
        self.slide_out_animation.setStartValue(current_pos)
        self.slide_out_animation.setEndValue(end_pos)
        self.slide_out_animation.start()
        
        # 发送关闭信号
        self.closeRequested.emit()

class NotificationManager(QWidget):
    """通知管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 先调用父类初始化
        super().__init__()
        
        # 检查是否已经初始化（防止单例重复初始化）
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.notifications: List[NotificationWidget] = []
        self.max_notifications = 5
        self.spacing = 10
        self.margin = 20
        
        # 隐藏管理器窗口
        self.hide()
    
    def show_notification(self, message: str, notification_type: NotificationType, 
                         duration: int = 3000, parent: Optional[QWidget] = None) -> NotificationWidget:
        """显示通知"""
        try:
            # 创建通知组件
            notification = NotificationWidget(message, notification_type, duration, parent)
            notification.closeRequested.connect(lambda: self.remove_notification(notification))
            
            # 添加到列表
            self.notifications.append(notification)
            
            # 限制最大通知数量
            while len(self.notifications) > self.max_notifications:
                old_notification = self.notifications.pop(0)
                old_notification.start_close_animation()
            
            # 计算位置并显示
            self.position_notifications()
            
            return notification
            
        except Exception as e:
            print(f"显示通知失败: {e}")
            return None
    
    def position_notifications(self):
        """重新定位所有通知"""
        if not self.notifications:
            return
        
        try:
            # 获取屏幕尺寸
            screen = QApplication.desktop().screenGeometry()
            
            # 确保通知不会超出屏幕边界
            notification_width = 350
            notification_height = 86  # 匹配实际窗口高度
            
            # 计算安全的起始位置（右上角，但留足够边距）
            start_x = max(0, screen.width() - notification_width - self.margin)
            start_y = max(self.margin, 30)  # 确保不会被标题栏遮挡
            
            for i, notification in enumerate(self.notifications):
                target_y = start_y + i * (notification_height + self.spacing)
                
                # 确保通知不会超出屏幕底部
                if target_y + notification_height > screen.height():
                    # 如果超出屏幕，从旧通知开始移除
                    for j in range(i, len(self.notifications)):
                        old_notification = self.notifications[j]
                        old_notification.start_close_animation()
                    break
                
                start_pos = QPoint(screen.width(), target_y)  # 从右侧滑入
                end_pos = QPoint(start_x, target_y)
                
                # 如果通知已经显示，只需要调整位置
                if notification.isVisible():
                    # 使用动画移动到新位置
                    notification.slide_in_animation.setStartValue(notification.pos())
                    notification.slide_in_animation.setEndValue(end_pos)
                    notification.slide_in_animation.start()
                else:
                    # 新通知，使用滑入动画
                    notification.show_animation(start_pos, end_pos)
                    
        except Exception as e:
            print(f"定位通知失败: {e}")
    
    def remove_notification(self, notification: NotificationWidget):
        """移除通知"""
        try:
            if notification in self.notifications:
                self.notifications.remove(notification)
                self.position_notifications()  # 重新定位剩余通知
        except Exception as e:
            print(f"移除通知失败: {e}")
    
    def clear_all_notifications(self):
        """清除所有通知"""
        try:
            for notification in self.notifications.copy():
                notification.start_close_animation()
            self.notifications.clear()
        except Exception as e:
            print(f"清除通知失败: {e}")

# 全局通知管理器实例（延迟初始化）
_notification_manager = None

def get_notification_manager():
    """获取通知管理器实例（延迟初始化）"""
    global _notification_manager
    if _notification_manager is None:
        try:
            # 检查是否有QApplication实例
            app = QApplication.instance()
            if app is None:
                print("警告：没有QApplication实例，通知系统将不可用")
                return None
            _notification_manager = NotificationManager()
        except Exception as e:
            print(f"创建通知管理器失败: {e}")
            return None
    return _notification_manager

# 便捷函数
def show_success(message: str, duration: int = 3000):
    """显示成功通知"""
    manager = get_notification_manager()
    if manager:
        return manager.show_notification(message, NotificationType.SUCCESS, duration)
    else:
        print(f"成功: {message}")
        return None

def show_warning(message: str, duration: int = 4000):
    """显示警告通知"""
    manager = get_notification_manager()
    if manager:
        return manager.show_notification(message, NotificationType.WARNING, duration)
    else:
        print(f"警告: {message}")
        return None

def show_error(message: str, duration: int = 5000):
    """显示错误通知"""
    manager = get_notification_manager()
    if manager:
        return manager.show_notification(message, NotificationType.ERROR, duration)
    else:
        print(f"错误: {message}")
        return None

def show_info(message: str, duration: int = 3000):
    """显示信息通知"""
    manager = get_notification_manager()
    if manager:
        return manager.show_notification(message, NotificationType.INFO, duration)
    else:
        print(f"信息: {message}")
        return None

def show_loading(message: str, duration: int = 0):
    """显示加载通知（不自动关闭）"""
    manager = get_notification_manager()
    if manager:
        return manager.show_notification(message, NotificationType.LOADING, duration)
    else:
        print(f"加载: {message}")
        return None

def clear_all():
    """清除所有通知"""
    manager = get_notification_manager()
    if manager:
        manager.clear_all_notifications()

# 测试代码
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 测试不同类型的通知
    show_success("操作成功完成！")
    show_warning("这是一个警告消息")
    show_error("发生了错误")
    show_info("这是一条信息")
    loading_notification = show_loading("正在处理中...")
    
    # 5秒后关闭加载通知
    def close_loading():
        if loading_notification:
            loading_notification.start_close_animation()
    
    QTimer.singleShot(5000, close_loading)
    
    sys.exit(app.exec_()) 