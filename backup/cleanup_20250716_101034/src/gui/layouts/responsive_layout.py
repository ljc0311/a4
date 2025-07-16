#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
响应式布局管理器
根据窗口大小自动调整布局和组件尺寸
支持断点、流式布局和自适应设计
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QSplitter, QScrollArea, QFrame, QSizePolicy,
    QApplication
)
from PyQt5.QtCore import Qt, QSize, QRect, pyqtSignal, QTimer
from PyQt5.QtGui import QResizeEvent
from typing import Dict, List, Tuple, Optional
from enum import Enum


class BreakPoint(Enum):
    """响应式断点"""
    XS = "xs"  # < 600px
    SM = "sm"  # 600px - 960px
    MD = "md"  # 960px - 1280px
    LG = "lg"  # 1280px - 1920px
    XL = "xl"  # > 1920px


class ResponsiveContainer(QWidget):
    """响应式容器"""
    
    # 信号
    breakpoint_changed = pyqtSignal(str)  # 断点变化信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_breakpoint = BreakPoint.MD
        self.breakpoint_configs = {}
        self.adaptive_widgets = []
        
        # 设置默认断点配置
        self.setup_default_breakpoints()
        
        # 延迟调整定时器（避免频繁调整）
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.apply_responsive_layout)
        
        # 初始化布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
    
    def setup_default_breakpoints(self):
        """设置默认断点配置"""
        self.breakpoint_configs = {
            BreakPoint.XS: {
                "max_width": 600,
                "columns": 1,
                "spacing": 8,
                "margins": (8, 8, 8, 8),
                "card_width": "100%",
                "sidebar_visible": False,
                "toolbar_compact": True
            },
            BreakPoint.SM: {
                "max_width": 960,
                "columns": 2,
                "spacing": 12,
                "margins": (12, 12, 12, 12),
                "card_width": "48%",
                "sidebar_visible": True,
                "toolbar_compact": True
            },
            BreakPoint.MD: {
                "max_width": 1280,
                "columns": 3,
                "spacing": 16,
                "margins": (16, 16, 16, 16),
                "card_width": "32%",
                "sidebar_visible": True,
                "toolbar_compact": False
            },
            BreakPoint.LG: {
                "max_width": 1920,
                "columns": 4,
                "spacing": 20,
                "margins": (20, 20, 20, 20),
                "card_width": "24%",
                "sidebar_visible": True,
                "toolbar_compact": False
            },
            BreakPoint.XL: {
                "max_width": float('inf'),
                "columns": 5,
                "spacing": 24,
                "margins": (24, 24, 24, 24),
                "card_width": "20%",
                "sidebar_visible": True,
                "toolbar_compact": False
            }
        }
    
    def get_current_breakpoint(self, width: int) -> BreakPoint:
        """根据宽度获取当前断点"""
        if width < 600:
            return BreakPoint.XS
        elif width < 960:
            return BreakPoint.SM
        elif width < 1280:
            return BreakPoint.MD
        elif width < 1920:
            return BreakPoint.LG
        else:
            return BreakPoint.XL
    
    def get_config(self, key: str, default=None):
        """获取当前断点的配置值"""
        config = self.breakpoint_configs.get(self.current_breakpoint, {})
        return config.get(key, default)
    
    def add_adaptive_widget(self, widget: QWidget, config: Dict):
        """添加自适应组件"""
        self.adaptive_widgets.append({
            "widget": widget,
            "config": config
        })
    
    def resizeEvent(self, event: QResizeEvent):
        """窗口大小变化事件"""
        super().resizeEvent(event)
        
        # 使用定时器延迟处理，避免频繁调整
        self.resize_timer.stop()
        self.resize_timer.start(100)  # 100ms延迟
    
    def apply_responsive_layout(self):
        """应用响应式布局"""
        current_width = self.width()
        new_breakpoint = self.get_current_breakpoint(current_width)
        
        if new_breakpoint != self.current_breakpoint:
            self.current_breakpoint = new_breakpoint
            self.breakpoint_changed.emit(new_breakpoint.value)
            
            # 应用布局调整
            self.adjust_layout()
            self.adjust_widgets()
    
    def adjust_layout(self):
        """调整布局"""
        config = self.breakpoint_configs[self.current_breakpoint]
        
        # 调整边距
        margins = config.get("margins", (16, 16, 16, 16))
        self.main_layout.setContentsMargins(*margins)
        
        # 调整间距
        spacing = config.get("spacing", 16)
        self.main_layout.setSpacing(spacing)
    
    def adjust_widgets(self):
        """调整组件"""
        for item in self.adaptive_widgets:
            widget = item["widget"]
            config = item["config"]
            
            # 根据断点调整组件属性
            self.apply_widget_config(widget, config)
    
    def apply_widget_config(self, widget: QWidget, config: Dict):
        """应用组件配置"""
        breakpoint_config = config.get(self.current_breakpoint.value, {})
        
        # 调整可见性
        if "visible" in breakpoint_config:
            widget.setVisible(breakpoint_config["visible"])
        
        # 调整尺寸
        if "size" in breakpoint_config:
            size = breakpoint_config["size"]
            if isinstance(size, tuple):
                widget.setFixedSize(size[0], size[1])
            elif isinstance(size, QSize):
                widget.setFixedSize(size)
        
        # 调整最小/最大尺寸
        if "min_size" in breakpoint_config:
            min_size = breakpoint_config["min_size"]
            widget.setMinimumSize(min_size[0], min_size[1])
        
        if "max_size" in breakpoint_config:
            max_size = breakpoint_config["max_size"]
            widget.setMaximumSize(max_size[0], max_size[1])
        
        # 调整样式
        if "style" in breakpoint_config:
            widget.setStyleSheet(breakpoint_config["style"])


class FlexLayout(QHBoxLayout):
    """弹性布局"""
    
    def __init__(self, direction="row", wrap=True, justify="start", align="start"):
        super().__init__()
        self.direction = direction  # row, column
        self.wrap = wrap
        self.justify = justify  # start, center, end, space-between, space-around
        self.align = align  # start, center, end, stretch
        
        self.flex_items = []
    
    def addWidget(self, widget, flex=0, **kwargs):
        """添加弹性组件"""
        super().addWidget(widget)
        
        self.flex_items.append({
            "widget": widget,
            "flex": flex,
            "kwargs": kwargs
        })
        
        # 设置弹性策略
        if flex > 0:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        else:
            widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)


class GridResponsiveLayout(QGridLayout):
    """响应式网格布局"""
    
    def __init__(self, columns=12, parent=None):
        super().__init__(parent)
        self.total_columns = columns
        self.grid_items = []
        self.current_breakpoint = BreakPoint.MD
    
    def addWidget(self, widget, row=0, col=0, row_span=1, col_span=1, 
                  responsive_config=None):
        """添加响应式组件"""
        # 默认响应式配置
        if responsive_config is None:
            responsive_config = {
                BreakPoint.XS.value: {"col_span": 12},
                BreakPoint.SM.value: {"col_span": 6},
                BreakPoint.MD.value: {"col_span": 4},
                BreakPoint.LG.value: {"col_span": 3},
                BreakPoint.XL.value: {"col_span": 2},
            }
        
        self.grid_items.append({
            "widget": widget,
            "row": row,
            "col": col,
            "row_span": row_span,
            "col_span": col_span,
            "responsive_config": responsive_config
        })
        
        # 初始添加
        super().addWidget(widget, row, col, row_span, col_span)
    
    def update_layout_for_breakpoint(self, breakpoint: BreakPoint):
        """根据断点更新布局"""
        self.current_breakpoint = breakpoint
        
        # 清除现有布局
        for i in reversed(range(self.count())):
            self.itemAt(i).widget().setParent(None)
        
        # 重新排列组件
        current_row = 0
        current_col = 0
        
        for item in self.grid_items:
            widget = item["widget"]
            config = item["responsive_config"].get(breakpoint.value, {})
            
            # 获取响应式列跨度
            col_span = config.get("col_span", item["col_span"])
            row_span = config.get("row_span", item["row_span"])
            
            # 检查是否需要换行
            if current_col + col_span > self.total_columns:
                current_row += 1
                current_col = 0
            
            # 添加组件
            super().addWidget(widget, current_row, current_col, row_span, col_span)
            
            # 更新位置
            current_col += col_span


class AdaptiveScrollArea(QScrollArea):
    """自适应滚动区域"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_scroll_area()
    
    def setup_scroll_area(self):
        """设置滚动区域"""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 设置样式
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: rgba(0, 0, 0, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0, 0, 0, 0.5);
            }
        """)


class ResponsiveSplitter(QSplitter):
    """响应式分割器"""
    
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.breakpoint_configs = {}
        self.current_breakpoint = BreakPoint.MD
        
        self.setup_default_configs()
    
    def setup_default_configs(self):
        """设置默认配置"""
        self.breakpoint_configs = {
            BreakPoint.XS: {"sizes": [0, 100], "collapsible": [True, False]},
            BreakPoint.SM: {"sizes": [25, 75], "collapsible": [True, False]},
            BreakPoint.MD: {"sizes": [30, 70], "collapsible": [False, False]},
            BreakPoint.LG: {"sizes": [25, 75], "collapsible": [False, False]},
            BreakPoint.XL: {"sizes": [20, 80], "collapsible": [False, False]},
        }
    
    def update_for_breakpoint(self, breakpoint: BreakPoint):
        """根据断点更新分割器"""
        self.current_breakpoint = breakpoint
        config = self.breakpoint_configs.get(breakpoint, {})
        
        # 设置尺寸比例
        if "sizes" in config:
            total_size = sum(config["sizes"])
            actual_sizes = [int(self.width() * size / total_size) for size in config["sizes"]]
            self.setSizes(actual_sizes)
        
        # 设置可折叠性
        if "collapsible" in config:
            for i, collapsible in enumerate(config["collapsible"]):
                if i < self.count():
                    self.setCollapsible(i, collapsible)


# 便捷函数
def create_responsive_container(parent=None):
    """创建响应式容器"""
    return ResponsiveContainer(parent)


def create_flex_layout(direction="row", wrap=True, justify="start", align="start"):
    """创建弹性布局"""
    return FlexLayout(direction, wrap, justify, align)


def create_grid_layout(columns=12, parent=None):
    """创建响应式网格布局"""
    return GridResponsiveLayout(columns, parent)


def create_adaptive_scroll_area(parent=None):
    """创建自适应滚动区域"""
    return AdaptiveScrollArea(parent)


def create_responsive_splitter(orientation=Qt.Horizontal, parent=None):
    """创建响应式分割器"""
    return ResponsiveSplitter(orientation, parent)
