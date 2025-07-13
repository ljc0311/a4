#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DPI适配工具
自动适配不同分辨率和DPI设置的显示器
支持完整的显示设置功能
"""

import os
import sys
import json
from typing import Tuple, Dict, Any, Optional
from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QFont, QFontMetrics, QScreen
from src.utils.logger import logger


class DPIAdapter:
    """DPI适配器 - 增强版"""

    # 标准DPI值
    STANDARD_DPI = 96

    # DPI阈值和对应的推荐字体大小
    DPI_THRESHOLDS = {
        96: 10,   # 100% 缩放 - 标准字体
        120: 11,  # 125% 缩放
        144: 12,  # 150% 缩放
        168: 13,  # 175% 缩放
        192: 14,  # 200% 缩放
        240: 16,  # 250% 缩放
        288: 18,  # 300% 缩放
    }

    # 字体大小预设
    FONT_SIZE_PRESETS = {
        "极小": 8,
        "小": 9,
        "正常": 10,
        "中等": 11,
        "大": 12,
        "较大": 14,
        "特大": 16,
        "超大": 18,
        "巨大": 20
    }

    def __init__(self):
        self.scale_factor = 1.0
        self.base_font_size = 10
        self.current_font_size = 10
        self.custom_scale_factor = None
        self.auto_dpi_scaling = True
        self.font_family = "Microsoft YaHei UI"
        self._screen_geometry = None
        self._current_dpi = None

        # 检测DPI设置
        self._detect_dpi_settings()
        
    def _detect_dpi_settings(self):
        """检测DPI设置 - 增强版"""
        try:
            app = QApplication.instance()
            if app is None:
                logger.warning("QApplication实例不存在，使用默认DPI设置")
                self._current_dpi = self.STANDARD_DPI
                self.scale_factor = 1.0
                return

            # 获取主屏幕
            screen = app.primaryScreen()
            if screen is None:
                # 尝试使用桌面widget获取屏幕信息
                desktop = QDesktopWidget()
                screen_rect = desktop.screenGeometry()
                self._screen_geometry = screen_rect
                self._current_dpi = self.STANDARD_DPI
                self.scale_factor = 1.0
                logger.warning("无法获取主屏幕信息，使用默认设置")
                return

            # 获取DPI信息
            dpi = screen.logicalDotsPerInch()
            physical_dpi = screen.physicalDotsPerInch()
            device_pixel_ratio = screen.devicePixelRatio()

            # 保存DPI信息
            self._current_dpi = dpi

            # 获取屏幕几何信息
            self._screen_geometry = screen.availableGeometry()

            # 计算缩放因子
            self.scale_factor = dpi / self.STANDARD_DPI

            # 根据DPI获取推荐字体大小
            self.current_font_size = self.get_recommended_font_size(self.base_font_size)

            logger.info(f"DPI检测结果: DPI={dpi}, 物理DPI={physical_dpi}, "
                       f"设备像素比={device_pixel_ratio}, 缩放因子={self.scale_factor:.2f}, "
                       f"推荐字体大小={self.current_font_size}pt")
            logger.info(f"屏幕可用区域: {self._screen_geometry.width()}x{self._screen_geometry.height()}")

        except Exception as e:
            logger.error(f"DPI检测失败: {e}")
            self._current_dpi = self.STANDARD_DPI
            self.scale_factor = 1.0
            self.current_font_size = self.base_font_size

    @property
    def current_dpi(self) -> float:
        """获取当前DPI"""
        return self._current_dpi or self.STANDARD_DPI

    @property
    def screen_geometry(self) -> Optional[QRect]:
        """获取屏幕几何信息"""
        return self._screen_geometry

    def get_recommended_font_size(self, base_size: int = 10) -> int:
        """根据DPI获取推荐字体大小"""
        try:
            current_dpi = int(self.current_dpi)

            # 查找最接近的DPI阈值
            best_match_dpi = self.STANDARD_DPI
            for dpi_threshold in sorted(self.DPI_THRESHOLDS.keys()):
                if current_dpi >= dpi_threshold:
                    best_match_dpi = dpi_threshold
                else:
                    break

            # 获取推荐字体大小
            recommended_size = self.DPI_THRESHOLDS.get(best_match_dpi, base_size)

            logger.debug(f"DPI {current_dpi} -> 推荐字体大小: {recommended_size}pt")
            return recommended_size

        except Exception as e:
            logger.error(f"计算推荐字体大小失败: {e}")
            return base_size

    def get_adaptive_window_size(self, base_width: int = 1200, base_height: int = 800) -> Tuple[int, int]:
        """获取自适应窗口大小"""
        try:
            if not self._screen_geometry:
                return base_width, base_height

            # 获取屏幕可用区域
            screen_width = self._screen_geometry.width()
            screen_height = self._screen_geometry.height()

            # 计算窗口大小（屏幕的80%）
            target_width = int(screen_width * 0.8)
            target_height = int(screen_height * 0.8)

            # 应用最小和最大限制
            min_width, min_height = 800, 600
            max_width = int(screen_width * 0.95)
            max_height = int(screen_height * 0.95)

            # 限制在合理范围内
            adaptive_width = max(min_width, min(target_width, max_width))
            adaptive_height = max(min_height, min(target_height, max_height))

            logger.info(f"自适应窗口大小: {adaptive_width}x{adaptive_height}")
            return adaptive_width, adaptive_height

        except Exception as e:
            logger.error(f"计算自适应窗口大小失败: {e}")
            return base_width, base_height

    def create_scaled_font(self, family: str = None, size: int = None,
                          custom_factor: float = None) -> QFont:
        """创建缩放后的字体"""
        try:
            # 使用默认值
            if family is None:
                family = self.font_family
            if size is None:
                size = self.current_font_size

            # 计算缩放后的字体大小
            if custom_factor is not None:
                scaled_size = int(size * custom_factor)
            elif self.custom_scale_factor is not None:
                scaled_size = int(size * self.custom_scale_factor)
            else:
                scaled_size = size

            # 验证字体大小
            scaled_size = self.validate_font_size(scaled_size)

            # 创建字体
            font = QFont(family, scaled_size)
            font.setStyleHint(QFont.SansSerif)

            logger.debug(f"创建缩放字体: {family} {scaled_size}pt")
            return font

        except Exception as e:
            logger.error(f"创建缩放字体失败: {e}")
            return QFont(self.font_family, self.current_font_size)

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

    def get_dpi_info(self) -> Dict[str, Any]:
        """获取DPI信息摘要"""
        return {
            "current_dpi": self.current_dpi,
            "scale_factor": self.scale_factor,
            "screen_width": self._screen_geometry.width() if self._screen_geometry else 0,
            "screen_height": self._screen_geometry.height() if self._screen_geometry else 0,
            "recommended_font_size": self.get_recommended_font_size(),
            "dpi_category": self._get_dpi_category(),
            "font_family": self.font_family,
            "auto_dpi_scaling": self.auto_dpi_scaling
        }

    def _get_dpi_category(self) -> str:
        """获取DPI类别描述"""
        dpi = self.current_dpi
        if dpi <= 96:
            return "标准DPI (100%)"
        elif dpi <= 120:
            return "中等DPI (125%)"
        elif dpi <= 144:
            return "高DPI (150%)"
        elif dpi <= 192:
            return "超高DPI (200%)"
        else:
            return "极高DPI (250%+)"

    def set_custom_scale_factor(self, factor: float):
        """设置自定义缩放因子"""
        self.custom_scale_factor = self.validate_scale_factor(factor)
        logger.info(f"设置自定义缩放因子: {self.custom_scale_factor}")

    def set_font_family(self, family: str):
        """设置字体族"""
        self.font_family = family
        logger.info(f"设置字体族: {family}")

    def set_auto_dpi_scaling(self, enabled: bool):
        """设置自动DPI缩放"""
        self.auto_dpi_scaling = enabled
        logger.info(f"自动DPI缩放: {'启用' if enabled else '禁用'}")

    @staticmethod
    def get_font_size_presets() -> Dict[str, int]:
        """获取字体大小预设"""
        return DPIAdapter.FONT_SIZE_PRESETS.copy()

    @staticmethod
    def validate_font_size(size: int) -> int:
        """验证并修正字体大小"""
        return max(8, min(20, size))

    @staticmethod
    def validate_scale_factor(factor: float) -> float:
        """验证并修正缩放因子"""
        return max(0.5, min(3.0, factor))


# 全局DPI适配器实例
_dpi_adapter = None

def get_dpi_adapter() -> DPIAdapter:
    """获取全局DPI适配器实例"""
    global _dpi_adapter
    if _dpi_adapter is None:
        _dpi_adapter = DPIAdapter()
    return _dpi_adapter

def refresh_dpi_adapter():
    """刷新DPI适配器（在屏幕配置改变时调用）"""
    global _dpi_adapter
    _dpi_adapter = None
    return get_dpi_adapter()

# 保持向后兼容性
dpi_adapter = get_dpi_adapter()


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
