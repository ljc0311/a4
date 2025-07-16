#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化UI组件库
提供Material Design 3.0风格的统一UI组件
支持响应式设计、无障碍访问和动画效果
"""

from PyQt5.QtWidgets import (
    QPushButton, QFrame, QLabel, QVBoxLayout, QHBoxLayout, 
    QWidget, QGraphicsDropShadowEffect, QProgressBar, QSlider,
    QComboBox, QLineEdit, QTextEdit, QListWidget, QTabWidget,
    QScrollArea, QGroupBox, QCheckBox, QRadioButton, QSpinBox,
    QDoubleSpinBox, QTableWidget, QTreeWidget, QSplitter
)
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect,
    QTimer, pyqtSignal, QParallelAnimationGroup, QSequentialAnimationGroup
)
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPalette, QPixmap,
    QLinearGradient, QRadialGradient, QPainterPath
)

from .styles.unified_theme_system import get_theme_system, get_current_color
from src.utils.logger import logger


class MaterialButton(QPushButton):
    """Material Design 3.0 按钮"""
    
    def __init__(self, text="", button_type="filled", parent=None):
        super().__init__(text, parent)
        self.button_type = button_type  # filled, outlined, text
        self.setup_style()
        self.setup_animations()
    
    def setup_style(self):
        """设置按钮样式"""
        self.setMinimumHeight(48)
        self.setFont(QFont("Microsoft YaHei UI", 10, QFont.Medium))
        
        # 设置按钮类型属性
        if self.button_type == "outlined":
            self.setProperty("flat", True)
        elif self.button_type == "text":
            self.setProperty("flat", True)
            self.setStyleSheet("QPushButton { border: none; background: transparent; }")
        
        # 添加阴影效果（仅填充按钮）
        if self.button_type == "filled":
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(8)
            shadow.setColor(QColor(0, 0, 0, 60))
            shadow.setOffset(0, 2)
            self.setGraphicsEffect(shadow)
    
    def setup_animations(self):
        """设置动画效果"""
        self.press_animation = QPropertyAnimation(self, b"geometry")
        self.press_animation.setDuration(100)
        self.press_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def mousePressEvent(self, event):
        """鼠标按下动画"""
        if self.button_type == "filled":
            current_rect = self.geometry()
            pressed_rect = QRect(
                current_rect.x() + 1,
                current_rect.y() + 1,
                current_rect.width() - 2,
                current_rect.height() - 2
            )
            self.press_animation.setStartValue(current_rect)
            self.press_animation.setEndValue(pressed_rect)
            self.press_animation.start()
        
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放动画"""
        if self.button_type == "filled":
            current_rect = self.geometry()
            normal_rect = QRect(
                current_rect.x() - 1,
                current_rect.y() - 1,
                current_rect.width() + 2,
                current_rect.height() + 2
            )
            self.press_animation.setStartValue(current_rect)
            self.press_animation.setEndValue(normal_rect)
            self.press_animation.start()
        
        super().mouseReleaseEvent(event)


class MaterialCard(QFrame):
    """Material Design 3.0 卡片"""
    
    def __init__(self, elevation=1, parent=None):
        super().__init__(parent)
        self.elevation = elevation
        self.setup_style()
    
    def setup_style(self):
        """设置卡片样式"""
        self.setFrameStyle(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setProperty("cardStyle", True)
        
        # 根据elevation设置阴影
        shadow = QGraphicsDropShadowEffect()
        if self.elevation == 1:
            shadow.setBlurRadius(4)
            shadow.setOffset(0, 1)
            shadow.setColor(QColor(0, 0, 0, 20))
        elif self.elevation == 2:
            shadow.setBlurRadius(8)
            shadow.setOffset(0, 2)
            shadow.setColor(QColor(0, 0, 0, 30))
        elif self.elevation == 3:
            shadow.setBlurRadius(12)
            shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 0, 0, 40))
        else:
            shadow.setBlurRadius(16)
            shadow.setOffset(0, 6)
            shadow.setColor(QColor(0, 0, 0, 50))
        
        self.setGraphicsEffect(shadow)


class MaterialProgressBar(QProgressBar):
    """Material Design 3.0 进度条"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_style()
        self.setup_animations()
    
    def setup_style(self):
        """设置进度条样式"""
        self.setMinimumHeight(4)
        self.setMaximumHeight(4)
        self.setTextVisible(False)
        
        # 设置圆角
        self.setStyleSheet("""
            QProgressBar {
                border-radius: 2px;
            }
            QProgressBar::chunk {
                border-radius: 2px;
            }
        """)
    
    def setup_animations(self):
        """设置动画效果"""
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def setValue(self, value):
        """带动画的设置值"""
        self.animation.setStartValue(self.value())
        self.animation.setEndValue(value)
        self.animation.start()


class MaterialSlider(QSlider):
    """Material Design 3.0 滑块"""
    
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setup_style()
    
    def setup_style(self):
        """设置滑块样式"""
        self.setMinimumHeight(32)
        
        # 自定义样式
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 20px;
                height: 20px;
                border-radius: 10px;
                margin: -8px 0;
            }
        """)


class MaterialComboBox(QComboBox):
    """Material Design 3.0 下拉框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_style()
    
    def setup_style(self):
        """设置下拉框样式"""
        self.setMinimumHeight(48)
        self.setFont(QFont("Microsoft YaHei UI", 10))
        
        # 设置图标
        self.setStyleSheet("""
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """)


class MaterialLineEdit(QLineEdit):
    """Material Design 3.0 输入框"""
    
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        if placeholder:
            self.setPlaceholderText(placeholder)
        self.setup_style()
        self.setup_animations()
    
    def setup_style(self):
        """设置输入框样式"""
        self.setMinimumHeight(48)
        self.setFont(QFont("Microsoft YaHei UI", 10))
        
        # 设置内边距
        self.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
            }
        """)
    
    def setup_animations(self):
        """设置动画效果"""
        self.focus_animation = QPropertyAnimation(self, b"styleSheet")
        self.focus_animation.setDuration(200)
    
    def focusInEvent(self, event):
        """获得焦点时的动画"""
        super().focusInEvent(event)
        # 这里可以添加焦点动画效果
    
    def focusOutEvent(self, event):
        """失去焦点时的动画"""
        super().focusOutEvent(event)
        # 这里可以添加失焦动画效果


class MaterialTextEdit(QTextEdit):
    """Material Design 3.0 文本编辑器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_style()
    
    def setup_style(self):
        """设置文本编辑器样式"""
        self.setFont(QFont("Microsoft YaHei UI", 10))
        
        # 设置内边距
        self.setStyleSheet("""
            QTextEdit {
                padding: 12px 16px;
            }
        """)


class MaterialListWidget(QListWidget):
    """Material Design 3.0 列表"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_style()
    
    def setup_style(self):
        """设置列表样式"""
        self.setFont(QFont("Microsoft YaHei UI", 10))
        self.setAlternatingRowColors(False)
        
        # 设置项目间距
        self.setSpacing(2)


class MaterialTabWidget(QTabWidget):
    """Material Design 3.0 标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_style()
    
    def setup_style(self):
        """设置标签页样式"""
        self.setFont(QFont("Microsoft YaHei UI", 10, QFont.Medium))
        
        # 设置标签页位置
        self.setTabPosition(QTabWidget.North)


class FloatingActionButton(QPushButton):
    """悬浮操作按钮 (FAB)"""
    
    def __init__(self, icon_text="+", parent=None):
        super().__init__(icon_text, parent)
        self.setup_style()
        self.setup_animations()
    
    def setup_style(self):
        """设置FAB样式"""
        self.setFixedSize(56, 56)
        self.setFont(QFont("Microsoft YaHei UI", 16))
        
        # 设置圆形样式
        self.setStyleSheet("""
            QPushButton {
                border-radius: 28px;
                font-weight: bold;
            }
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
    
    def setup_animations(self):
        """设置动画效果"""
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        current_rect = self.geometry()
        hover_rect = QRect(
            current_rect.x() - 2,
            current_rect.y() - 2,
            current_rect.width() + 4,
            current_rect.height() + 4
        )
        self.hover_animation.setStartValue(current_rect)
        self.hover_animation.setEndValue(hover_rect)
        self.hover_animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        current_rect = self.geometry()
        normal_rect = QRect(
            current_rect.x() + 2,
            current_rect.y() + 2,
            current_rect.width() - 4,
            current_rect.height() - 4
        )
        self.hover_animation.setStartValue(current_rect)
        self.hover_animation.setEndValue(normal_rect)
        self.hover_animation.start()
        super().leaveEvent(event)


class MaterialToolBar(QFrame):
    """Material Design 3.0 工具栏"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_style()
        self.setup_layout()
    
    def setup_style(self):
        """设置工具栏样式"""
        self.setFixedHeight(64)
        self.setFrameStyle(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        # 添加底部阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
    
    def setup_layout(self):
        """设置布局"""
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(16, 8, 16, 8)
        self.layout.setSpacing(16)


class StatusIndicator(QLabel):
    """状态指示器"""
    
    def __init__(self, status="inactive", parent=None):
        super().__init__(parent)
        self.status = status
        self.setup_style()
    
    def setup_style(self):
        """设置样式"""
        self.setFixedSize(12, 12)
        self.setAlignment(Qt.AlignCenter)
        self.update_status(self.status)
    
    def update_status(self, status):
        """更新状态"""
        self.status = status
        colors = {
            "active": get_current_color("success", "#4CAF50"),
            "warning": get_current_color("warning", "#FF9800"),
            "error": get_current_color("error", "#F44336"),
            "inactive": get_current_color("outline", "#757575")
        }
        
        color = colors.get(status, colors["inactive"])
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)
    
    def set_status(self, status_text, color=None):
        """设置状态（兼容性方法）"""
        # 根据状态文本映射到内部状态
        status_mapping = {
            "正常": "active",
            "警告": "warning", 
            "错误": "error",
            "离线": "inactive"
        }
        
        mapped_status = status_mapping.get(status_text, "inactive")
        self.update_status(mapped_status)
        
        # 如果提供了自定义颜色，直接使用
        if color:
            self.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    border-radius: 6px;
                }}
            """)


class LoadingSpinner(QLabel):
    """加载动画"""
    
    def __init__(self, size=24, parent=None):
        super().__init__(parent)
        self.size = size
        self.angle = 0
        self.setup_style()
        self.setup_animation()
    
    def setup_style(self):
        """设置样式"""
        self.setFixedSize(self.size, self.size)
        self.setAlignment(Qt.AlignCenter)
    
    def setup_animation(self):
        """设置动画"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.rotate)
        self.timer.setInterval(50)  # 20 FPS
    
    def start_animation(self):
        """开始动画"""
        self.timer.start()
    
    def stop_animation(self):
        """停止动画"""
        self.timer.stop()
    
    def rotate(self):
        """旋转动画"""
        self.angle = (self.angle + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        """绘制加载动画"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置画笔
        pen = QPen(QColor(get_current_color("primary", "#1976D2")))
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        # 绘制圆弧
        rect = QRect(2, 2, self.size - 4, self.size - 4)
        painter.drawArc(rect, self.angle * 16, 120 * 16)


class MaterialGroupBox(QGroupBox):
    """Material Design 3.0 分组框"""
    
    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setup_style()
    
    def setup_style(self):
        """设置分组框样式"""
        self.setFont(QFont("Microsoft YaHei UI", 11, QFont.DemiBold))
        
        # 设置样式
        self.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                padding-top: 16px;
                margin-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }
        """)


class MaterialCheckBox(QCheckBox):
    """Material Design 3.0 复选框"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setup_style()
        self.setup_animations()
    
    def setup_style(self):
        """设置复选框样式"""
        self.setFont(QFont("Microsoft YaHei UI", 10))
    
    def setup_animations(self):
        """设置动画效果"""
        self.check_animation = QPropertyAnimation(self, b"geometry")
        self.check_animation.setDuration(150)
        self.check_animation.setEasingCurve(QEasingCurve.OutCubic)


class MaterialRadioButton(QRadioButton):
    """Material Design 3.0 单选按钮"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setup_style()
    
    def setup_style(self):
        """设置单选按钮样式"""
        self.setFont(QFont("Microsoft YaHei UI", 10))


class MaterialSplitter(QSplitter):
    """Material Design 3.0 分割器"""
    
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setup_style()
    
    def setup_style(self):
        """设置分割器样式"""
        self.setHandleWidth(8)
        
        # 设置分割器样式
        self.setStyleSheet("""
            QSplitter::handle {
                background-color: transparent;
            }
            QSplitter::handle:hover {
                background-color: rgba(25, 118, 210, 0.1);
            }
        """)


class ResponsiveContainer(QWidget):
    """响应式容器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_layout()
    
    def setup_layout(self):
        """设置响应式布局"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(16)
    
    def resizeEvent(self, event):
        """响应式调整"""
        super().resizeEvent(event)
        width = event.size().width()
        
        # 根据宽度调整布局
        if width < 600:  # 小屏幕
            self.layout.setContentsMargins(8, 8, 8, 8)
            self.layout.setSpacing(8)
        elif width < 1200:  # 中等屏幕
            self.layout.setContentsMargins(16, 16, 16, 16)
            self.layout.setSpacing(12)
        else:  # 大屏幕
            self.layout.setContentsMargins(24, 24, 24, 24)
            self.layout.setSpacing(16)


# 便捷函数
def create_material_button(text, button_type="filled", parent=None):
    """创建Material按钮"""
    return MaterialButton(text, button_type, parent)


def create_material_card(elevation=1, parent=None):
    """创建Material卡片"""
    return MaterialCard(elevation, parent)


def create_loading_spinner(size=24, parent=None):
    """创建加载动画"""
    return LoadingSpinner(size, parent)


def create_status_indicator(status="inactive", parent=None):
    """创建状态指示器"""
    return StatusIndicator(status, parent)


def create_responsive_container(parent=None):
    """创建响应式容器"""
    return ResponsiveContainer(parent)
