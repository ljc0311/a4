#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动画效果系统
为界面交互提供平滑的动画和过渡效果
"""

from PyQt5.QtWidgets import QWidget, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt5.QtCore import (QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, 
                         QSequentialAnimationGroup, QTimer, pyqtProperty, QRect, QPoint)
from PyQt5.QtGui import QColor

from src.utils.logger import logger


class AnimationManager:
    """动画管理器"""
    
    def __init__(self):
        self.animations = {}
        self.animation_groups = {}
    
    def create_fade_animation(self, widget: QWidget, duration: int = 300, 
                            start_opacity: float = 0.0, end_opacity: float = 1.0) -> QPropertyAnimation:
        """创建淡入淡出动画"""
        # 创建透明度效果
        opacity_effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(opacity_effect)
        
        # 创建动画
        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(start_opacity)
        animation.setEndValue(end_opacity)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        
        return animation
    
    def create_slide_animation(self, widget: QWidget, direction: str = "up", 
                             duration: int = 300, distance: int = 50) -> QPropertyAnimation:
        """创建滑动动画"""
        start_pos = widget.pos()
        
        if direction == "up":
            end_pos = QPoint(start_pos.x(), start_pos.y() - distance)
        elif direction == "down":
            end_pos = QPoint(start_pos.x(), start_pos.y() + distance)
        elif direction == "left":
            end_pos = QPoint(start_pos.x() - distance, start_pos.y())
        elif direction == "right":
            end_pos = QPoint(start_pos.x() + distance, start_pos.y())
        else:
            end_pos = start_pos
        
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setStartValue(end_pos)
        animation.setEndValue(start_pos)
        animation.setEasingCurve(QEasingCurve.OutBack)
        
        return animation
    
    def create_scale_animation(self, widget: QWidget, duration: int = 200,
                             start_scale: float = 0.8, end_scale: float = 1.0) -> QPropertyAnimation:
        """创建缩放动画"""
        current_geometry = widget.geometry()
        center = current_geometry.center()
        
        # 计算起始几何形状
        start_width = int(current_geometry.width() * start_scale)
        start_height = int(current_geometry.height() * start_scale)
        start_geometry = QRect(
            center.x() - start_width // 2,
            center.y() - start_height // 2,
            start_width,
            start_height
        )
        
        animation = QPropertyAnimation(widget, b"geometry")
        animation.setDuration(duration)
        animation.setStartValue(start_geometry)
        animation.setEndValue(current_geometry)
        animation.setEasingCurve(QEasingCurve.OutBack)
        
        return animation
    
    def create_bounce_animation(self, widget: QWidget, duration: int = 600) -> QSequentialAnimationGroup:
        """创建弹跳动画"""
        group = QSequentialAnimationGroup()
        
        # 第一次弹跳
        bounce1 = QPropertyAnimation(widget, b"pos")
        bounce1.setDuration(duration // 3)
        start_pos = widget.pos()
        bounce_pos = QPoint(start_pos.x(), start_pos.y() - 20)
        bounce1.setStartValue(start_pos)
        bounce1.setEndValue(bounce_pos)
        bounce1.setEasingCurve(QEasingCurve.OutQuad)
        
        # 回落
        fall1 = QPropertyAnimation(widget, b"pos")
        fall1.setDuration(duration // 3)
        fall1.setStartValue(bounce_pos)
        fall1.setEndValue(start_pos)
        fall1.setEasingCurve(QEasingCurve.InQuad)
        
        # 第二次小弹跳
        bounce2 = QPropertyAnimation(widget, b"pos")
        bounce2.setDuration(duration // 6)
        small_bounce_pos = QPoint(start_pos.x(), start_pos.y() - 10)
        bounce2.setStartValue(start_pos)
        bounce2.setEndValue(small_bounce_pos)
        bounce2.setEasingCurve(QEasingCurve.OutQuad)
        
        # 最终回落
        fall2 = QPropertyAnimation(widget, b"pos")
        fall2.setDuration(duration // 6)
        fall2.setStartValue(small_bounce_pos)
        fall2.setEndValue(start_pos)
        fall2.setEasingCurve(QEasingCurve.InQuad)
        
        group.addAnimation(bounce1)
        group.addAnimation(fall1)
        group.addAnimation(bounce2)
        group.addAnimation(fall2)
        
        return group
    
    def create_glow_animation(self, widget: QWidget, duration: int = 1000) -> QPropertyAnimation:
        """创建发光动画"""
        # 创建阴影效果
        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(20)
        glow_effect.setColor(QColor(100, 150, 255, 100))
        glow_effect.setOffset(0, 0)
        widget.setGraphicsEffect(glow_effect)
        
        # 创建发光动画
        animation = QPropertyAnimation(glow_effect, b"color")
        animation.setDuration(duration)
        animation.setStartValue(QColor(100, 150, 255, 50))
        animation.setEndValue(QColor(100, 150, 255, 150))
        animation.setEasingCurve(QEasingCurve.InOutSine)
        animation.setLoopCount(-1)  # 无限循环
        
        return animation
    
    def create_entrance_animation(self, widget: QWidget) -> QParallelAnimationGroup:
        """创建入场动画组合"""
        group = QParallelAnimationGroup()
        
        # 淡入
        fade_in = self.create_fade_animation(widget, 400, 0.0, 1.0)
        
        # 从下方滑入
        slide_in = self.create_slide_animation(widget, "up", 400, 30)
        
        # 轻微缩放
        scale_in = self.create_scale_animation(widget, 400, 0.95, 1.0)
        
        group.addAnimation(fade_in)
        group.addAnimation(slide_in)
        group.addAnimation(scale_in)
        
        return group
    
    def create_exit_animation(self, widget: QWidget) -> QParallelAnimationGroup:
        """创建退场动画组合"""
        group = QParallelAnimationGroup()
        
        # 淡出
        fade_out = self.create_fade_animation(widget, 200, 1.0, 0.0)
        
        # 向上滑出
        slide_out = self.create_slide_animation(widget, "down", 200, 20)
        
        # 轻微缩放
        scale_out = self.create_scale_animation(widget, 200, 1.0, 0.9)
        
        group.addAnimation(fade_out)
        group.addAnimation(slide_out)
        group.addAnimation(scale_out)
        
        return group
    
    def play_animation(self, animation_id: str, animation):
        """播放动画"""
        if animation_id in self.animations:
            self.animations[animation_id].stop()
        
        self.animations[animation_id] = animation
        animation.start()
        
        # 动画完成后清理
        animation.finished.connect(lambda: self.cleanup_animation(animation_id))
    
    def cleanup_animation(self, animation_id: str):
        """清理动画"""
        if animation_id in self.animations:
            del self.animations[animation_id]
    
    def stop_all_animations(self):
        """停止所有动画"""
        for animation in self.animations.values():
            animation.stop()
        self.animations.clear()


class AnimatedWidget(QWidget):
    """带动画效果的控件基类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation_manager = AnimationManager()
        self.setup_animations()
    
    def setup_animations(self):
        """设置动画"""
        pass
    
    def show_with_animation(self):
        """带动画显示"""
        self.show()
        entrance_animation = self.animation_manager.create_entrance_animation(self)
        self.animation_manager.play_animation("entrance", entrance_animation)
    
    def hide_with_animation(self):
        """带动画隐藏"""
        exit_animation = self.animation_manager.create_exit_animation(self)
        exit_animation.finished.connect(self.hide)
        self.animation_manager.play_animation("exit", exit_animation)
    
    def bounce(self):
        """弹跳动画"""
        bounce_animation = self.animation_manager.create_bounce_animation(self)
        self.animation_manager.play_animation("bounce", bounce_animation)
    
    def glow(self, enable: bool = True):
        """发光效果"""
        if enable:
            glow_animation = self.animation_manager.create_glow_animation(self)
            self.animation_manager.play_animation("glow", glow_animation)
        else:
            if "glow" in self.animation_manager.animations:
                self.animation_manager.animations["glow"].stop()
                self.setGraphicsEffect(None)


class TransitionEffects:
    """过渡效果工具类"""
    
    @staticmethod
    def smooth_scroll_to(scroll_area, target_value: int, duration: int = 300):
        """平滑滚动到指定位置"""
        scroll_bar = scroll_area.verticalScrollBar()
        
        animation = QPropertyAnimation(scroll_bar, b"value")
        animation.setDuration(duration)
        animation.setStartValue(scroll_bar.value())
        animation.setEndValue(target_value)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.start()
        
        return animation
    
    @staticmethod
    def fade_between_widgets(old_widget: QWidget, new_widget: QWidget, duration: int = 300):
        """在两个控件之间淡入淡出切换"""
        animation_manager = AnimationManager()
        
        # 淡出旧控件
        fade_out = animation_manager.create_fade_animation(old_widget, duration, 1.0, 0.0)
        fade_out.finished.connect(old_widget.hide)
        
        # 淡入新控件
        fade_in = animation_manager.create_fade_animation(new_widget, duration, 0.0, 1.0)
        
        # 显示新控件并开始动画
        new_widget.show()
        fade_out.start()
        
        # 延迟启动淡入动画
        QTimer.singleShot(duration // 2, fade_in.start)
        
        return fade_out, fade_in
    
    @staticmethod
    def slide_between_widgets(old_widget: QWidget, new_widget: QWidget, 
                            direction: str = "left", duration: int = 300):
        """在两个控件之间滑动切换"""
        animation_manager = AnimationManager()
        
        # 滑出旧控件
        slide_out = animation_manager.create_slide_animation(old_widget, direction, duration, 100)
        slide_out.finished.connect(old_widget.hide)
        
        # 滑入新控件
        opposite_direction = {"left": "right", "right": "left", "up": "down", "down": "up"}
        slide_in = animation_manager.create_slide_animation(
            new_widget, opposite_direction.get(direction, "right"), duration, 100
        )
        
        # 显示新控件并开始动画
        new_widget.show()
        slide_out.start()
        slide_in.start()
        
        return slide_out, slide_in


# 全局动画管理器实例
_global_animation_manager = None

def get_animation_manager() -> AnimationManager:
    """获取全局动画管理器"""
    global _global_animation_manager
    if _global_animation_manager is None:
        _global_animation_manager = AnimationManager()
    return _global_animation_manager

def animate_widget_entrance(widget: QWidget):
    """为控件添加入场动画"""
    manager = get_animation_manager()
    animation = manager.create_entrance_animation(widget)
    manager.play_animation(f"entrance_{id(widget)}", animation)

def animate_widget_exit(widget: QWidget, callback=None):
    """为控件添加退场动画"""
    manager = get_animation_manager()
    animation = manager.create_exit_animation(widget)
    if callback:
        animation.finished.connect(callback)
    manager.play_animation(f"exit_{id(widget)}", animation)
