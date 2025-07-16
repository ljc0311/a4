#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
响应式布局管理器
根据屏幕大小和DPI自动调整界面布局
"""

from PyQt5.QtWidgets import QApplication, QWidget, QLayout, QLayoutItem
from PyQt5.QtCore import Qt, QRect, QSize, QTimer, pyqtSignal
from PyQt5.QtGui import QResizeEvent

from src.utils.dpi_adapter import dpi_adapter
from src.utils.logger import logger


class ResponsiveBreakpoints:
    """响应式断点定义"""
    
    # 屏幕宽度断点（像素）
    MOBILE = 480
    TABLET = 768
    DESKTOP = 1024
    LARGE_DESKTOP = 1440
    
    @classmethod
    def get_breakpoint(cls, width: int) -> str:
        """根据宽度获取断点类型"""
        if width < cls.MOBILE:
            return "mobile"
        elif width < cls.TABLET:
            return "tablet"
        elif width < cls.DESKTOP:
            return "desktop"
        elif width < cls.LARGE_DESKTOP:
            return "large"
        else:
            return "xlarge"


class ResponsiveWidget(QWidget):
    """响应式控件基类"""
    
    breakpoint_changed = pyqtSignal(str)  # 断点改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_breakpoint = "desktop"
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.on_resize_finished)
        self.setup_responsive()
    
    def setup_responsive(self):
        """设置响应式行为"""
        # 初始化断点
        self.update_breakpoint()
    
    def resizeEvent(self, event: QResizeEvent):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        
        # 延迟处理，避免频繁触发
        self.resize_timer.start(100)
    
    def on_resize_finished(self):
        """大小改变完成处理"""
        old_breakpoint = self.current_breakpoint
        self.update_breakpoint()
        
        if old_breakpoint != self.current_breakpoint:
            self.breakpoint_changed.emit(self.current_breakpoint)
            self.on_breakpoint_changed(old_breakpoint, self.current_breakpoint)
    
    def update_breakpoint(self):
        """更新断点"""
        width = self.width()
        self.current_breakpoint = ResponsiveBreakpoints.get_breakpoint(width)
    
    def on_breakpoint_changed(self, old_breakpoint: str, new_breakpoint: str):
        """断点改变时的处理"""
        logger.info(f"断点改变: {old_breakpoint} -> {new_breakpoint}")
        self.adjust_layout_for_breakpoint(new_breakpoint)
    
    def adjust_layout_for_breakpoint(self, breakpoint: str):
        """根据断点调整布局"""
        # 子类重写此方法实现具体的布局调整
        pass
    
    def get_responsive_size(self, base_size: int) -> int:
        """获取响应式大小"""
        scale_factor = dpi_adapter.scale_factor
        
        # 根据断点调整缩放
        breakpoint_scales = {
            "mobile": 0.8,
            "tablet": 0.9,
            "desktop": 1.0,
            "large": 1.1,
            "xlarge": 1.2
        }
        
        breakpoint_scale = breakpoint_scales.get(self.current_breakpoint, 1.0)
        return int(base_size * scale_factor * breakpoint_scale)
    
    def get_responsive_font_size(self, base_size: int) -> int:
        """获取响应式字体大小"""
        scale_factor = dpi_adapter.scale_factor
        
        # 根据断点调整字体大小
        breakpoint_scales = {
            "mobile": 0.9,
            "tablet": 0.95,
            "desktop": 1.0,
            "large": 1.05,
            "xlarge": 1.1
        }
        
        breakpoint_scale = breakpoint_scales.get(self.current_breakpoint, 1.0)
        return max(8, int(base_size * scale_factor * breakpoint_scale))


class ResponsiveLayout(QLayout):
    """响应式布局"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.current_breakpoint = "desktop"
    
    def addItem(self, item: QLayoutItem):
        """添加布局项"""
        self.items.append(item)
    
    def count(self) -> int:
        """获取项目数量"""
        return len(self.items)
    
    def itemAt(self, index: int) -> QLayoutItem:
        """获取指定索引的项目"""
        if 0 <= index < len(self.items):
            return self.items[index]
        return None
    
    def takeAt(self, index: int) -> QLayoutItem:
        """移除并返回指定索引的项目"""
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None
    
    def setGeometry(self, rect: QRect):
        """设置几何形状"""
        super().setGeometry(rect)
        self.arrange_items(rect)
    
    def sizeHint(self) -> QSize:
        """获取建议大小"""
        return QSize(400, 300)
    
    def minimumSize(self) -> QSize:
        """获取最小大小"""
        return QSize(200, 150)
    
    def arrange_items(self, rect: QRect):
        """排列项目"""
        if not self.items:
            return
        
        # 根据断点决定布局方式
        width = rect.width()
        breakpoint = ResponsiveBreakpoints.get_breakpoint(width)
        
        if breakpoint in ["mobile", "tablet"]:
            self.arrange_vertical(rect)
        else:
            self.arrange_horizontal(rect)
    
    def arrange_vertical(self, rect: QRect):
        """垂直排列"""
        item_height = rect.height() // len(self.items)
        
        for i, item in enumerate(self.items):
            item_rect = QRect(
                rect.x(),
                rect.y() + i * item_height,
                rect.width(),
                item_height
            )
            item.setGeometry(item_rect)
    
    def arrange_horizontal(self, rect: QRect):
        """水平排列"""
        item_width = rect.width() // len(self.items)
        
        for i, item in enumerate(self.items):
            item_rect = QRect(
                rect.x() + i * item_width,
                rect.y(),
                item_width,
                rect.height()
            )
            item.setGeometry(item_rect)


class ResponsiveMainWindow(ResponsiveWidget):
    """响应式主窗口"""
    
    def __init__(self):
        super().__init__()
        self.sidebar_visible = True
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        self.setMinimumSize(800, 600)
        
        # 根据屏幕大小设置初始窗口大小
        screen = QApplication.desktop().screenGeometry()
        width, height = dpi_adapter.get_recommended_window_size(1200, 800)
        
        # 确保窗口不超过屏幕大小
        width = min(width, int(screen.width() * 0.9))
        height = min(height, int(screen.height() * 0.9))
        
        self.resize(width, height)
        
        # 居中显示
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.move(x, y)
    
    def adjust_layout_for_breakpoint(self, breakpoint: str):
        """根据断点调整布局"""
        super().adjust_layout_for_breakpoint(breakpoint)
        
        # 在小屏幕上隐藏侧边栏
        if breakpoint in ["mobile", "tablet"]:
            self.hide_sidebar()
        else:
            self.show_sidebar()
        
        # 调整字体大小
        self.adjust_fonts_for_breakpoint(breakpoint)
    
    def hide_sidebar(self):
        """隐藏侧边栏"""
        if hasattr(self, 'sidebar') and self.sidebar_visible:
            self.sidebar.hide()
            self.sidebar_visible = False
            logger.info("侧边栏已隐藏（小屏幕模式）")
    
    def show_sidebar(self):
        """显示侧边栏"""
        if hasattr(self, 'sidebar') and not self.sidebar_visible:
            self.sidebar.show()
            self.sidebar_visible = True
            logger.info("侧边栏已显示（大屏幕模式）")
    
    def adjust_fonts_for_breakpoint(self, breakpoint: str):
        """根据断点调整字体"""
        base_font_size = 10
        font_size = self.get_responsive_font_size(base_font_size)
        
        # 应用到应用程序
        app = QApplication.instance()
        if app:
            font = app.font()
            font.setPointSize(font_size)
            app.setFont(font)
            
            logger.info(f"字体大小已调整为: {font_size}pt (断点: {breakpoint})")


class ResponsiveGridLayout:
    """响应式网格布局助手"""
    
    @staticmethod
    def get_grid_columns(width: int) -> int:
        """根据宽度获取网格列数"""
        breakpoint = ResponsiveBreakpoints.get_breakpoint(width)
        
        column_map = {
            "mobile": 1,
            "tablet": 2,
            "desktop": 3,
            "large": 4,
            "xlarge": 5
        }
        
        return column_map.get(breakpoint, 3)
    
    @staticmethod
    def get_item_size(container_width: int, columns: int, spacing: int = 16) -> int:
        """计算网格项目大小"""
        total_spacing = spacing * (columns - 1)
        available_width = container_width - total_spacing
        return available_width // columns


class ResponsiveUtils:
    """响应式工具类"""
    
    @staticmethod
    def scale_for_dpi(size: int) -> int:
        """根据DPI缩放大小"""
        return dpi_adapter.scale_size(size)
    
    @staticmethod
    def get_adaptive_spacing(base_spacing: int = 16) -> int:
        """获取自适应间距"""
        return dpi_adapter.scale_size(base_spacing)
    
    @staticmethod
    def get_adaptive_margins(base_margin: int = 16) -> tuple:
        """获取自适应边距"""
        margin = dpi_adapter.scale_size(base_margin)
        return (margin, margin, margin, margin)
    
    @staticmethod
    def is_high_dpi() -> bool:
        """检查是否为高DPI"""
        return dpi_adapter.scale_factor > 1.25
    
    @staticmethod
    def get_touch_friendly_size(base_size: int = 44) -> int:
        """获取触摸友好的大小（最小44px）"""
        scaled_size = dpi_adapter.scale_size(base_size)
        return max(44, scaled_size)  # 确保最小触摸目标大小
