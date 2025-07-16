#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的现代UI组件库
提供更丰富的Material Design 3.0风格组件
包含动画、渐变、阴影等现代UI效果
"""

from PyQt5.QtWidgets import (
    QPushButton, QFrame, QLabel, QVBoxLayout, QHBoxLayout, 
    QWidget, QGraphicsDropShadowEffect, QProgressBar, QSlider,
    QComboBox, QLineEdit, QTextEdit, QListWidget, QTabWidget,
    QScrollArea, QGroupBox, QCheckBox, QRadioButton, QSpinBox,
    QApplication, QSizePolicy
)
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect,
    QTimer, pyqtSignal, QParallelAnimationGroup, QSequentialAnimationGroup,
    QSize, QPoint
)
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPalette, QPixmap,
    QLinearGradient, QRadialGradient, QPainterPath, QFontMetrics
)

from ..styles.enhanced_color_palette import EnhancedColorPalette


class EnhancedMaterialButton(QPushButton):
    """增强的Material Design按钮"""
    
    # 按钮类型
    FILLED = "filled"
    OUTLINED = "outlined"
    TEXT = "text"
    FAB = "fab"
    ICON = "icon"
    
    def __init__(self, text="", button_type=FILLED, icon=None, parent=None):
        super().__init__(text, parent)
        self.button_type = button_type
        self.icon_name = icon
        self._is_animating = False
        
        self.setup_style()
        self.setup_animations()
        self.setup_effects()
    
    def setup_style(self):
        """设置按钮样式"""
        # 基础设置
        self.setMinimumHeight(48 if self.button_type != self.FAB else 56)
        self.setFont(QFont("Segoe UI", 10, QFont.Medium))
        self.setCursor(Qt.PointingHandCursor)
        
        # 根据类型设置属性
        if self.button_type == self.OUTLINED:
            self.setProperty("flat", True)
        elif self.button_type == self.TEXT:
            self.setProperty("flat", True)
            self.setProperty("text", True)
        elif self.button_type == self.FAB:
            self.setProperty("fab", True)
            self.setFixedSize(56, 56)
        elif self.button_type == self.ICON:
            self.setProperty("icon", True)
            self.setFixedSize(40, 40)
    
    def setup_animations(self):
        """设置动画效果"""
        # 点击动画
        self.press_animation = QPropertyAnimation(self, b"geometry")
        self.press_animation.setDuration(100)
        self.press_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # 悬停动画
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(200)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def setup_effects(self):
        """设置视觉效果"""
        if self.button_type == self.FILLED or self.button_type == self.FAB:
            # 添加阴影效果
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(12)
            shadow.setColor(QColor(0, 0, 0, 40))
            shadow.setOffset(0, 4)
            self.setGraphicsEffect(shadow)
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        if not self._is_animating:
            self.start_hover_animation(True)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        if not self._is_animating:
            self.start_hover_animation(False)
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.start_press_animation()
        super().mousePressEvent(event)
    
    def start_hover_animation(self, entering):
        """开始悬停动画"""
        if self._is_animating:
            return
        
        self._is_animating = True
        current_rect = self.geometry()
        
        if entering:
            # 轻微放大
            new_rect = QRect(
                current_rect.x() - 1,
                current_rect.y() - 1,
                current_rect.width() + 2,
                current_rect.height() + 2
            )
        else:
            # 恢复原始大小
            new_rect = QRect(
                current_rect.x() + 1,
                current_rect.y() + 1,
                current_rect.width() - 2,
                current_rect.height() - 2
            )
        
        self.hover_animation.setStartValue(current_rect)
        self.hover_animation.setEndValue(new_rect)
        self.hover_animation.finished.connect(self._on_animation_finished)
        self.hover_animation.start()
    
    def start_press_animation(self):
        """开始按压动画"""
        if self._is_animating:
            return
        
        self._is_animating = True
        current_rect = self.geometry()
        
        # 轻微缩小
        pressed_rect = QRect(
            current_rect.x() + 2,
            current_rect.y() + 2,
            current_rect.width() - 4,
            current_rect.height() - 4
        )
        
        self.press_animation.setStartValue(current_rect)
        self.press_animation.setEndValue(pressed_rect)
        self.press_animation.finished.connect(self._on_press_finished)
        self.press_animation.start()
    
    def _on_animation_finished(self):
        """动画完成回调"""
        self._is_animating = False
        self.hover_animation.finished.disconnect()
    
    def _on_press_finished(self):
        """按压动画完成回调"""
        # 恢复原始大小
        current_rect = self.geometry()
        original_rect = QRect(
            current_rect.x() - 2,
            current_rect.y() - 2,
            current_rect.width() + 4,
            current_rect.height() + 4
        )
        
        self.press_animation.setStartValue(current_rect)
        self.press_animation.setEndValue(original_rect)
        self.press_animation.finished.connect(self._on_animation_finished)
        self.press_animation.start()


class GradientCard(QFrame):
    """渐变卡片组件"""
    
    def __init__(self, gradient_colors=None, elevation=1, parent=None):
        super().__init__(parent)
        self.gradient_colors = gradient_colors or ["#6750A4", "#7C4DFF"]
        self.elevation = elevation
        
        self.setup_style()
        self.setup_effects()
    
    def setup_style(self):
        """设置样式"""
        self.setProperty("card", True)
        self.setFrameStyle(QFrame.NoFrame)
        
        # 设置最小尺寸
        self.setMinimumHeight(80)
        
        # 设置边距
        self.setContentsMargins(16, 16, 16, 16)
    
    def setup_effects(self):
        """设置阴影效果"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8 + self.elevation * 4)
        shadow.setColor(QColor(0, 0, 0, 20 + self.elevation * 10))
        shadow.setOffset(0, 2 + self.elevation)
        self.setGraphicsEffect(shadow)
    
    def paintEvent(self, event):
        """绘制渐变背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 创建渐变
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(self.gradient_colors[0]))
        gradient.setColorAt(1, QColor(self.gradient_colors[1]))
        
        # 绘制圆角矩形
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 16, 16)
        painter.fillPath(path, QBrush(gradient))
        
        super().paintEvent(event)


class AnimatedProgressBar(QProgressBar):
    """动画进度条"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_style()
        self.setup_animation()
    
    def setup_style(self):
        """设置样式"""
        self.setMinimumHeight(8)
        self.setMaximumHeight(8)
        self.setTextVisible(False)
    
    def setup_animation(self):
        """设置动画"""
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def setValue(self, value):
        """设置值（带动画）"""
        if self.value() != value:
            self.animation.setStartValue(self.value())
            self.animation.setEndValue(value)
            self.animation.start()
        else:
            super().setValue(value)


class FloatingActionButton(EnhancedMaterialButton):
    """浮动操作按钮"""
    
    def __init__(self, icon=None, parent=None):
        super().__init__("", self.FAB, icon, parent)
        self.setup_fab_style()
    
    def setup_fab_style(self):
        """设置FAB特有样式"""
        # 设置圆形
        self.setStyleSheet("""
            QPushButton {
                border-radius: 28px;
                font-size: 24px;
            }
        """)
        
        # 增强阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)


class StatusIndicator(QWidget):
    """状态指示器"""
    
    # 状态类型
    INACTIVE = "inactive"
    ACTIVE = "active"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    
    def __init__(self, status=INACTIVE, text="", parent=None):
        super().__init__(parent)
        self.status = status
        self.text = text
        
        self.setup_ui()
        self.setup_animation()
    
    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # 状态指示点
        self.indicator = QLabel()
        self.indicator.setFixedSize(12, 12)
        self.indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {self.get_status_color()};
                border-radius: 6px;
            }}
        """)
        
        # 状态文本
        self.label = QLabel(self.text)
        self.label.setFont(QFont("Segoe UI", 9))
        
        layout.addWidget(self.indicator)
        layout.addWidget(self.label)
        layout.addStretch()
    
    def setup_animation(self):
        """设置动画"""
        if self.status == self.ACTIVE:
            # 活跃状态的脉冲动画
            self.pulse_animation = QPropertyAnimation(self.indicator, b"geometry")
            self.pulse_animation.setDuration(1000)
            self.pulse_animation.setLoopCount(-1)  # 无限循环
            self.pulse_animation.setEasingCurve(QEasingCurve.InOutSine)
            
            # 设置动画值
            current_rect = self.indicator.geometry()
            expanded_rect = QRect(
                current_rect.x() - 2,
                current_rect.y() - 2,
                current_rect.width() + 4,
                current_rect.height() + 4
            )
            
            self.pulse_animation.setStartValue(current_rect)
            self.pulse_animation.setEndValue(expanded_rect)
            self.pulse_animation.start()
    
    def get_status_color(self):
        """获取状态颜色"""
        colors = EnhancedColorPalette.get_modern_light_colors()
        
        color_map = {
            self.INACTIVE: colors.get("outline_variant", "#CAC4D0"),
            self.ACTIVE: colors.get("primary", "#6750A4"),
            self.SUCCESS: colors.get("success", "#00C853"),
            self.WARNING: colors.get("warning", "#FF8F00"),
            self.ERROR: colors.get("error", "#BA1A1A"),
        }
        
        return color_map.get(self.status, colors.get("outline_variant", "#CAC4D0"))
    
    def set_status(self, status, text=None):
        """设置状态"""
        self.status = status
        if text is not None:
            self.text = text
            self.label.setText(text)
        
        # 更新指示器颜色
        self.indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {self.get_status_color()};
                border-radius: 6px;
            }}
        """)
        
        # 重新设置动画
        if hasattr(self, 'pulse_animation'):
            self.pulse_animation.stop()
        
        self.setup_animation()


class LoadingSpinner(QWidget):
    """加载动画组件"""
    
    def __init__(self, size=32, color=None, parent=None):
        super().__init__(parent)
        self.size = size
        self.color = color or EnhancedColorPalette.get_modern_light_colors().get("primary", "#6750A4")
        self.angle = 0
        
        self.setFixedSize(size, size)
        self.setup_animation()
    
    def setup_animation(self):
        """设置旋转动画"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.rotate)
        self.timer.start(50)  # 50ms间隔
    
    def rotate(self):
        """旋转动画"""
        self.angle = (self.angle + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        """绘制加载动画"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置画笔
        pen = QPen(QColor(self.color))
        pen.setWidth(3)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        # 绘制圆弧
        rect = self.rect().adjusted(5, 5, -5, -5)
        painter.drawArc(rect, self.angle * 16, 120 * 16)
    
    def start(self):
        """开始动画"""
        self.timer.start(50)
    
    def stop(self):
        """停止动画"""
        self.timer.stop()


# 便捷函数
def create_enhanced_button(text, button_type=EnhancedMaterialButton.FILLED, icon=None, parent=None):
    """创建增强按钮"""
    return EnhancedMaterialButton(text, button_type, icon, parent)


def create_gradient_card(gradient_colors=None, elevation=1, parent=None):
    """创建渐变卡片"""
    return GradientCard(gradient_colors, elevation, parent)


def create_status_indicator(status=StatusIndicator.INACTIVE, text="", parent=None):
    """创建状态指示器"""
    return StatusIndicator(status, text, parent)


def create_loading_spinner(size=32, color=None, parent=None):
    """创建加载动画"""
    return LoadingSpinner(size, color, parent)


def create_floating_action_button(icon=None, parent=None):
    """创建浮动操作按钮"""
    return FloatingActionButton(icon, parent)
