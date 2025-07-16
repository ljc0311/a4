#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加载状态管理器
统一管理各种加载状态和进度指示器
"""

import sys
import time
import threading
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass
from enum import Enum

from PyQt5.QtWidgets import (
    QWidget, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout,
    QPushButton, QGraphicsOpacityEffect, QFrame, QApplication
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, 
    pyqtSignal, QObject, QThread, QMutex
)
from PyQt5.QtGui import QMovie, QPixmap, QPainter, QColor, QFont

class LoadingType(Enum):
    """加载类型枚举"""
    SPINNER = "spinner"           # 旋转加载器
    PROGRESS_BAR = "progress_bar" # 进度条
    DOTS = "dots"                 # 点状加载器
    PULSE = "pulse"               # 脉冲加载器
    SKELETON = "skeleton"         # 骨架屏
    CIRCULAR = "circular"         # 圆形进度

@dataclass
class LoadingState:
    """加载状态数据类"""
    task_id: str
    message: str
    progress: float = 0.0
    is_indeterminate: bool = True
    can_cancel: bool = False
    start_time: float = 0.0
    
    def __post_init__(self):
        if self.start_time == 0.0:
            self.start_time = time.time()
    
    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time

class LoadingWidget(QWidget):
    """通用加载组件"""
    
    # 取消信号
    cancelRequested = pyqtSignal(str)  # task_id
    
    def __init__(self, loading_type: LoadingType, parent=None):
        super().__init__(parent)
        self.loading_type = loading_type
        self.is_active = False
        self.current_state: Optional[LoadingState] = None
        
        self.init_ui()
        self.setup_animations()
    
    def init_ui(self):
        """初始化界面"""
        self.setFixedSize(300, 120)
        
        # 主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # 加载指示器容器
        self.indicator_container = QFrame()
        self.indicator_container.setFixedHeight(40)
        indicator_layout = QHBoxLayout(self.indicator_container)
        indicator_layout.setAlignment(Qt.AlignCenter)
        
        # 根据类型创建不同的加载指示器
        self.create_indicator(indicator_layout)
        
        layout.addWidget(self.indicator_container)
        
        # 消息标签
        self.message_label = QLabel("加载中...")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        # 进度信息
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.progress_label)
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedSize(80, 30)
        self.cancel_btn.clicked.connect(self.on_cancel_clicked)
        self.cancel_btn.hide()  # 默认隐藏
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 应用样式
        self.apply_style()
    
    def create_indicator(self, layout):
        """根据类型创建加载指示器"""
        if self.loading_type == LoadingType.SPINNER:
            self.create_spinner(layout)
        elif self.loading_type == LoadingType.PROGRESS_BAR:
            self.create_progress_bar(layout)
        elif self.loading_type == LoadingType.DOTS:
            self.create_dots(layout)
        elif self.loading_type == LoadingType.PULSE:
            self.create_pulse(layout)
        elif self.loading_type == LoadingType.CIRCULAR:
            self.create_circular(layout)
        else:
            self.create_spinner(layout)  # 默认使用旋转器
    
    def create_spinner(self, layout):
        """创建旋转加载器"""
        self.spinner_label = QLabel()
        self.spinner_label.setFixedSize(32, 32)
        self.spinner_label.setAlignment(Qt.AlignCenter)
        
        # 创建旋转图标
        self.create_spinner_icon()
        
        layout.addWidget(self.spinner_label)
    
    def create_spinner_icon(self):
        """创建旋转图标"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制旋转圆环
        painter.setPen(QColor(100, 100, 100, 80))
        painter.drawEllipse(2, 2, 28, 28)
        
        painter.setPen(QColor(33, 150, 243, 255))
        painter.drawArc(2, 2, 28, 28, 0, 90 * 16)  # 90度弧线
        
        painter.end()
        self.spinner_label.setPixmap(pixmap)
    
    def create_progress_bar(self, layout):
        """创建进度条"""
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setTextVisible(True)
        # 应用现代化样式
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #f5f5f5;
                text-align: center;
                font-size: 12px;
                color: #666;
                font-weight: normal;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 #42a5f5, stop: 1 #1976d2);
                border-radius: 3px;
                margin: 0px;
            }
        """)
        layout.addWidget(self.progress_bar)
    
    def create_dots(self, layout):
        """创建点状加载器"""
        self.dots_container = QWidget()
        dots_layout = QHBoxLayout(self.dots_container)
        dots_layout.setSpacing(8)
        
        self.dots = []
        for i in range(3):
            dot = QLabel("●")
            dot.setFixedSize(16, 16)
            dot.setAlignment(Qt.AlignCenter)
            dot.setStyleSheet("color: #ccc; font-size: 16px;")
            self.dots.append(dot)
            dots_layout.addWidget(dot)
        
        layout.addWidget(self.dots_container)
    
    def create_pulse(self, layout):
        """创建脉冲加载器"""
        self.pulse_label = QLabel("●")
        self.pulse_label.setFixedSize(32, 32)
        self.pulse_label.setAlignment(Qt.AlignCenter)
        self.pulse_label.setStyleSheet("color: #2196F3; font-size: 24px;")
        layout.addWidget(self.pulse_label)
    
    def create_circular(self, layout):
        """创建圆形进度"""
        self.circular_widget = CircularProgress()
        layout.addWidget(self.circular_widget)
    
    def setup_animations(self):
        """设置动画"""
        if self.loading_type == LoadingType.SPINNER:
            self.setup_spinner_animation()
        elif self.loading_type == LoadingType.DOTS:
            self.setup_dots_animation()
        elif self.loading_type == LoadingType.PULSE:
            self.setup_pulse_animation()
    
    def setup_spinner_animation(self):
        """设置旋转动画"""
        self.rotation_timer = QTimer()
        self.rotation_timer.timeout.connect(self.rotate_spinner)
        self.rotation_angle = 0
    
    def setup_dots_animation(self):
        """设置点状动画"""
        self.dots_timer = QTimer()
        self.dots_timer.timeout.connect(self.animate_dots)
        self.dots_index = 0
    
    def setup_pulse_animation(self):
        """设置脉冲动画"""
        self.pulse_effect = QGraphicsOpacityEffect()
        self.pulse_label.setGraphicsEffect(self.pulse_effect)
        
        self.pulse_animation = QPropertyAnimation(self.pulse_effect, b"opacity")
        self.pulse_animation.setDuration(1000)
        self.pulse_animation.setStartValue(0.3)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.pulse_animation.finished.connect(self.reverse_pulse)
        self.pulse_reverse = False
    
    def start_loading(self, state: LoadingState):
        """开始加载"""
        self.current_state = state
        self.is_active = True
        
        # 更新界面
        self.message_label.setText(state.message)
        
        # 显示/隐藏取消按钮
        if state.can_cancel:
            self.cancel_btn.show()
        else:
            self.cancel_btn.hide()
        
        # 启动动画
        self.start_animations()
        
        # 更新进度
        self.update_progress(state.progress, state.is_indeterminate)
    
    def stop_loading(self):
        """停止加载"""
        self.is_active = False
        self.current_state = None
        
        # 停止动画
        self.stop_animations()
    
    def update_progress(self, progress: float, is_indeterminate: bool = False):
        """更新进度"""
        if self.loading_type == LoadingType.PROGRESS_BAR:
            if is_indeterminate:
                self.progress_bar.setRange(0, 0)  # 不确定进度
            else:
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(int(progress))
        
        elif self.loading_type == LoadingType.CIRCULAR:
            self.circular_widget.setValue(progress)
        
        # 更新进度标签
        if not is_indeterminate:
            self.progress_label.setText(f"{progress:.1f}%")
        else:
            if self.current_state:
                elapsed = self.current_state.elapsed_time
                self.progress_label.setText(f"已用时: {elapsed:.1f}秒")
    
    def start_animations(self):
        """启动动画"""
        if self.loading_type == LoadingType.SPINNER:
            self.rotation_timer.start(50)  # 20 FPS
        elif self.loading_type == LoadingType.DOTS:
            self.dots_timer.start(500)
        elif self.loading_type == LoadingType.PULSE:
            self.pulse_animation.start()
    
    def stop_animations(self):
        """停止动画"""
        if hasattr(self, 'rotation_timer'):
            self.rotation_timer.stop()
        if hasattr(self, 'dots_timer'):
            self.dots_timer.stop()
        if hasattr(self, 'pulse_animation'):
            self.pulse_animation.stop()
    
    def rotate_spinner(self):
        """旋转动画"""
        if not self.is_active:
            return
        
        self.rotation_angle = (self.rotation_angle + 10) % 360
        self.create_spinner_icon_rotated(self.rotation_angle)
    
    def create_spinner_icon_rotated(self, angle):
        """创建旋转的图标"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(16, 16)  # 移动到中心
        painter.rotate(angle)      # 旋转
        painter.translate(-16, -16)  # 移回原位
        
        # 绘制旋转圆环
        painter.setPen(QColor(100, 100, 100, 80))
        painter.drawEllipse(2, 2, 28, 28)
        
        painter.setPen(QColor(33, 150, 243, 255))
        painter.drawArc(2, 2, 28, 28, 0, 90 * 16)
        
        painter.end()
        self.spinner_label.setPixmap(pixmap)
    
    def animate_dots(self):
        """点状动画"""
        if not self.is_active:
            return
        
        # 重置所有点的颜色
        for dot in self.dots:
            dot.setStyleSheet("color: #ccc; font-size: 16px;")
        
        # 高亮当前点
        self.dots[self.dots_index].setStyleSheet("color: #2196F3; font-size: 16px;")
        
        self.dots_index = (self.dots_index + 1) % len(self.dots)
    
    def reverse_pulse(self):
        """反向脉冲"""
        if not self.is_active:
            return
        
        if self.pulse_reverse:
            self.pulse_animation.setStartValue(0.3)
            self.pulse_animation.setEndValue(1.0)
        else:
            self.pulse_animation.setStartValue(1.0)
            self.pulse_animation.setEndValue(0.3)
        
        self.pulse_reverse = not self.pulse_reverse
        self.pulse_animation.start()
    
    def on_cancel_clicked(self):
        """取消按钮点击"""
        if self.current_state:
            self.cancelRequested.emit(self.current_state.task_id)
    
    def apply_style(self):
        """应用样式"""
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 10px;
                border: 1px solid #ddd;
            }
            
            QLabel {
                color: #333;
                font-size: 14px;
                background: transparent;
            }
            
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            
            QPushButton:hover {
                background-color: #d32f2f;
            }
            
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #f5f5f5;
                text-align: center;
                height: 8px;
                font-size: 12px;
                color: #666;
                font-weight: normal;
            }

            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 #42a5f5, stop: 1 #1976d2);
                border-radius: 3px;
                margin: 0px;
            }
        """)

class CircularProgress(QWidget):
    """圆形进度组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.value = 0
    
    def setValue(self, value):
        """设置进度值"""
        self.value = max(0, min(100, value))
        self.update()
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 背景圆环
        painter.setPen(QColor(230, 230, 230))
        painter.drawEllipse(2, 2, 36, 36)
        
        # 进度圆弧
        painter.setPen(QColor(33, 150, 243))
        start_angle = 90 * 16  # 从顶部开始
        span_angle = -int(self.value * 360 / 100 * 16)  # 顺时针
        painter.drawArc(2, 2, 36, 36, start_angle, span_angle)
        
        # 中心文本
        painter.setPen(QColor(33, 33, 33))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, f"{int(self.value)}%")

class LoadingManager(QObject):
    """加载状态管理器"""
    
    # 信号
    loading_started = pyqtSignal(str, str)  # task_id, message
    loading_updated = pyqtSignal(str, float, str)  # task_id, progress, message
    loading_finished = pyqtSignal(str)  # task_id
    loading_cancelled = pyqtSignal(str)  # task_id
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        super().__init__()
        self._initialized = True
        
        self.active_loadings: Dict[str, LoadingState] = {}
        self.loading_widgets: Dict[str, LoadingWidget] = {}
        self.overlay_widgets: Dict[str, QWidget] = {}
        self.mutex = QMutex()
    
    def start_loading(self, task_id: str, message: str, 
                     loading_type: LoadingType = LoadingType.SPINNER,
                     can_cancel: bool = False, 
                     parent_widget: Optional[QWidget] = None) -> LoadingWidget:
        """开始加载任务"""
        with self.mutex:
            # 创建加载状态
            state = LoadingState(
                task_id=task_id,
                message=message,
                can_cancel=can_cancel
            )
            
            self.active_loadings[task_id] = state
            
            # 创建加载组件
            loading_widget = LoadingWidget(loading_type)
            loading_widget.cancelRequested.connect(self.cancel_loading)
            loading_widget.start_loading(state)
            
            self.loading_widgets[task_id] = loading_widget
            
            # 如果指定了父组件，创建覆盖层
            if parent_widget:
                self.create_overlay(task_id, loading_widget, parent_widget)
            
            # 发送信号
            self.loading_started.emit(task_id, message)
            
            return loading_widget
    
    def update_loading(self, task_id: str, progress: float = None, 
                      message: str = None, is_indeterminate: bool = None):
        """更新加载进度"""
        with self.mutex:
            if task_id not in self.active_loadings:
                return
            
            state = self.active_loadings[task_id]
            
            if progress is not None:
                state.progress = progress
                state.is_indeterminate = False
            
            if message is not None:
                state.message = message
            
            if is_indeterminate is not None:
                state.is_indeterminate = is_indeterminate
            
            # 更新加载组件
            if task_id in self.loading_widgets:
                widget = self.loading_widgets[task_id]
                widget.update_progress(state.progress, state.is_indeterminate)
                if message:
                    widget.message_label.setText(message)
            
            # 发送信号
            self.loading_updated.emit(task_id, state.progress, state.message)
    
    def finish_loading(self, task_id: str):
        """完成加载任务"""
        with self.mutex:
            if task_id not in self.active_loadings:
                return
            
            # 停止加载
            if task_id in self.loading_widgets:
                widget = self.loading_widgets[task_id]
                widget.stop_loading()
                del self.loading_widgets[task_id]
            
            # 移除覆盖层
            if task_id in self.overlay_widgets:
                overlay = self.overlay_widgets[task_id]
                overlay.hide()
                overlay.deleteLater()
                del self.overlay_widgets[task_id]
            
            # 清理状态
            del self.active_loadings[task_id]
            
            # 发送信号
            self.loading_finished.emit(task_id)
    
    def cancel_loading(self, task_id: str):
        """取消加载任务"""
        with self.mutex:
            if task_id in self.active_loadings:
                self.finish_loading(task_id)
                self.loading_cancelled.emit(task_id)
    
    def create_overlay(self, task_id: str, loading_widget: LoadingWidget, 
                      parent_widget: QWidget):
        """创建覆盖层"""
        # 创建半透明覆盖层
        overlay = QWidget(parent_widget)
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
        overlay.resize(parent_widget.size())
        overlay.move(0, 0)
        
        # 布局
        layout = QVBoxLayout(overlay)
        layout.addStretch()
        
        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(loading_widget)
        center_layout.addStretch()
        
        layout.addLayout(center_layout)
        layout.addStretch()
        
        overlay.show()
        self.overlay_widgets[task_id] = overlay
    
    def is_loading(self, task_id: str) -> bool:
        """检查任务是否正在加载"""
        return task_id in self.active_loadings
    
    def get_loading_state(self, task_id: str) -> Optional[LoadingState]:
        """获取加载状态"""
        return self.active_loadings.get(task_id)

# 全局加载管理器实例
loading_manager = LoadingManager()

# 便捷函数
def start_loading(task_id: str, message: str, 
                 loading_type: LoadingType = LoadingType.SPINNER,
                 can_cancel: bool = False, 
                 parent_widget: Optional[QWidget] = None) -> LoadingWidget:
    """开始加载"""
    return loading_manager.start_loading(task_id, message, loading_type, can_cancel, parent_widget)

def update_loading(task_id: str, progress: float = None, message: str = None):
    """更新加载进度"""
    loading_manager.update_loading(task_id, progress, message)

def finish_loading(task_id: str):
    """完成加载"""
    loading_manager.finish_loading(task_id)

def cancel_loading(task_id: str):
    """取消加载"""
    loading_manager.cancel_loading(task_id)

# 测试代码
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 创建测试窗口
    main_window = QWidget()
    main_window.setWindowTitle("加载管理器测试")
    main_window.resize(400, 300)
    main_window.show()
    
    # 测试不同类型的加载器
    spinner = start_loading("test1", "正在加载数据...", LoadingType.SPINNER, True, main_window)
    
    # 模拟进度更新
    def update_progress():
        for i in range(101):
            update_loading("test1", i, f"正在处理... {i}%")
            time.sleep(0.05)
        finish_loading("test1")
    
    # 在后台线程中更新进度
    import threading
    threading.Thread(target=update_progress, daemon=True).start()
    
    sys.exit(app.exec_()) 