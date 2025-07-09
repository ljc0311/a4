#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DPI适配工具
自动适配不同分辨率和DPI设置的显示器
"""

import os
import sys
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics
from src.utils.logger import logger


class DPIAdapter:
    """DPI适配器"""
    
    def __init__(self):
        self.scale_factor = 1.0
        self.base_font_size = 9
        self.current_font_size = 9
        self._detect_dpi_settings()
        
    def _detect_dpi_settings(self):
        """检测DPI设置"""
        try:
            app = QApplication.instance()
            if app is None:
                return
                
            # 获取主屏幕
            screen = app.primaryScreen()
            if screen is None:
                return
                
            # 获取DPI信息
            dpi = screen.logicalDotsPerInch()
            physical_dpi = screen.physicalDotsPerInch()
            device_pixel_ratio = screen.devicePixelRatio()
            
            # 计算缩放因子
            standard_dpi = 96  # Windows标准DPI
            self.scale_factor = dpi / standard_dpi
            
            # 根据DPI调整字体大小
            if dpi >= 144:  # 150% 缩放
                self.current_font_size = 12
            elif dpi >= 120:  # 125% 缩放
                self.current_font_size = 11
            elif dpi >= 96:   # 100% 缩放
                self.current_font_size = 10
            else:
                self.current_font_size = 9
                
            logger.info(f"DPI检测结果: DPI={dpi}, 物理DPI={physical_dpi}, "
                       f"设备像素比={device_pixel_ratio}, 缩放因子={self.scale_factor:.2f}, "
                       f"字体大小={self.current_font_size}")
                       
        except Exception as e:
            logger.warning(f"DPI检测失败: {e}")
            self.scale_factor = 1.0
            self.current_font_size = 10
            
    def setup_high_dpi_support(self):
        """设置高DPI支持"""
        try:
            # 设置环境变量
            os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
            os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
            os.environ['QT_SCALE_FACTOR'] = str(self.scale_factor)
            
            # 设置Qt属性
            if hasattr(Qt, 'AA_EnableHighDpiScaling'):
                QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
            if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
                QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
                
            logger.info("高DPI支持设置完成")
            
        except Exception as e:
            logger.error(f"设置高DPI支持失败: {e}")
            
    def apply_font_scaling(self, app: QApplication):
        """应用字体缩放"""
        try:
            # 设置应用程序默认字体
            font = QFont()
            font.setFamily("Microsoft YaHei UI")  # 使用微软雅黑
            font.setPointSize(self.current_font_size)
            app.setFont(font)
            
            logger.info(f"应用字体缩放: {self.current_font_size}pt")
            
        except Exception as e:
            logger.error(f"应用字体缩放失败: {e}")
            
    def scale_size(self, size: int) -> int:
        """缩放尺寸"""
        return int(size * self.scale_factor)
        
    def scale_font_size(self, base_size: int) -> int:
        """缩放字体大小"""
        return max(8, int(base_size * self.scale_factor))
        
    def get_scaled_stylesheet(self, base_stylesheet: str) -> str:
        """获取缩放后的样式表"""
        try:
            # 简单的字体大小缩放
            import re
            
            def replace_font_size(match):
                size = int(match.group(1))
                scaled_size = self.scale_font_size(size)
                return f"font-size: {scaled_size}px"
                
            # 替换font-size属性
            scaled_stylesheet = re.sub(
                r'font-size:\s*(\d+)px',
                replace_font_size,
                base_stylesheet
            )
            
            return scaled_stylesheet
            
        except Exception as e:
            logger.error(f"样式表缩放失败: {e}")
            return base_stylesheet
            
    def apply_widget_scaling(self, widget: QWidget):
        """应用控件缩放"""
        try:
            # 设置控件字体
            font = widget.font()
            font.setPointSize(self.current_font_size)
            widget.setFont(font)
            
            # 设置最小尺寸
            min_size = widget.minimumSize()
            if min_size.width() > 0 or min_size.height() > 0:
                widget.setMinimumSize(
                    self.scale_size(min_size.width()) if min_size.width() > 0 else 0,
                    self.scale_size(min_size.height()) if min_size.height() > 0 else 0
                )
                
        except Exception as e:
            logger.error(f"控件缩放失败: {e}")
            
    def get_recommended_window_size(self, base_width: int, base_height: int) -> tuple:
        """获取推荐的窗口大小"""
        try:
            app = QApplication.instance()
            if app is None:
                return base_width, base_height
                
            screen = app.primaryScreen()
            if screen is None:
                return base_width, base_height
                
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            
            # 计算推荐大小（屏幕的80%）
            recommended_width = min(self.scale_size(base_width), int(screen_width * 0.8))
            recommended_height = min(self.scale_size(base_height), int(screen_height * 0.8))
            
            logger.info(f"推荐窗口大小: {recommended_width}x{recommended_height} "
                       f"(屏幕: {screen_width}x{screen_height})")
                       
            return recommended_width, recommended_height
            
        except Exception as e:
            logger.error(f"计算推荐窗口大小失败: {e}")
            return base_width, base_height
            
    def create_adaptive_stylesheet(self) -> str:
        """创建自适应样式表"""
        font_size = self.current_font_size
        button_height = self.scale_size(32)
        input_height = self.scale_size(28)
        
        stylesheet = f"""
        QWidget {{
            font-family: "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif;
            font-size: {font_size}px;
        }}
        
        QPushButton {{
            font-size: {font_size}px;
            min-height: {button_height}px;
            padding: 4px 12px;
        }}
        
        QLineEdit, QTextEdit, QPlainTextEdit {{
            font-size: {font_size}px;
            min-height: {input_height}px;
            padding: 4px;
        }}
        
        QLabel {{
            font-size: {font_size}px;
        }}
        
        QComboBox {{
            font-size: {font_size}px;
            min-height: {input_height}px;
        }}
        
        QTabWidget::pane {{
            border: 1px solid #c0c0c0;
        }}
        
        QTabBar::tab {{
            font-size: {font_size}px;
            padding: 6px 12px;
            min-width: 80px;
        }}
        
        QListWidget, QTreeWidget, QTableWidget {{
            font-size: {font_size}px;
        }}
        
        QGroupBox {{
            font-size: {font_size}px;
            font-weight: bold;
            padding-top: 10px;
        }}
        
        QCheckBox, QRadioButton {{
            font-size: {font_size}px;
        }}
        """
        
        return stylesheet


# 全局DPI适配器实例
dpi_adapter = DPIAdapter()


def setup_dpi_awareness():
    """设置DPI感知"""
    try:
        # Windows DPI感知设置
        if sys.platform == "win32":
            import ctypes
            try:
                # 设置DPI感知级别
                ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
            except:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()  # 备用方案
                except:
                    pass
                    
        logger.info("DPI感知设置完成")
        
    except Exception as e:
        logger.warning(f"DPI感知设置失败: {e}")


def apply_dpi_scaling(app: QApplication):
    """应用DPI缩放"""
    dpi_adapter.setup_high_dpi_support()
    dpi_adapter.apply_font_scaling(app)
    
    # 应用自适应样式表
    stylesheet = dpi_adapter.create_adaptive_stylesheet()
    app.setStyleSheet(stylesheet)
    
    logger.info("DPI缩放应用完成")
