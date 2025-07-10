#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新的主窗口
基于重构后的应用控制器的现代化GUI界面
"""

import sys
import os
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QProgressBar, QTextEdit,
    QSplitter, QMessageBox, QComboBox, QLineEdit, QFormLayout,
    QGroupBox, QScrollArea, QGridLayout, QSpacerItem, QSizePolicy,
    QSpinBox, QDoubleSpinBox, QCheckBox, QSlider, QFileDialog,
    QFrame, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QDialog, QDesktopWidget, QMenuBar, QMenu, QAction
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject, QSize, QDateTime
from PyQt5.QtGui import QIcon, QPixmap, QFont, QPalette, QColor

# 导入重构后的核心组件
from src.core.app_controller import AppController
from src.utils.project_manager import StoryboardProjectManager
from src.utils.auto_save_manager import AutoSaveManager
from src.utils.memory_optimizer import MemoryMonitor, ImageMemoryManager
from src.processors.text_processor import StoryboardResult
from src.processors.image_processor import ImageGenerationConfig, BatchImageResult
from src.processors.video_processor import VideoConfig
from src.processors.consistency_enhanced_image_processor import ConsistencyEnhancedImageProcessor
from src.utils.logger import logger
# StoryboardTab已被五阶段分镜系统代替，不再需要导入
from .five_stage_storyboard_tab import FiveStageStoryboardTab
from .consistency_control_panel import ConsistencyControlPanel
from .storyboard_image_generation_tab import StoryboardImageGenerationTab
from .voice_generation_tab import VoiceGenerationTab
from src.gui.project_dialog import NewProjectDialog, OpenProjectDialog
from src.gui.log_dialog import LogDialog

# 导入现代UI组件
from .modern_ui_components import (
    MaterialButton, MaterialCard, MaterialTabWidget, 
    MaterialProgressBar, StatusIndicator
)

# 导入主题系统
try:
    # 当从main.py运行时使用相对导入
    from .styles.unified_theme_system import UnifiedThemeSystem, get_theme_system, ThemeMode
    from .modern_ui_components import (
        MaterialButton, MaterialCard, MaterialProgressBar, MaterialSlider,
        MaterialComboBox, MaterialLineEdit, MaterialTextEdit, MaterialListWidget,
        MaterialTabWidget, FloatingActionButton, MaterialToolBar, StatusIndicator,
        LoadingSpinner, MaterialGroupBox, MaterialCheckBox, MaterialRadioButton,
        ResponsiveContainer, create_material_button, create_material_card
    )
    from .notification_system import show_success, show_info
except ImportError:
    # 当直接运行或测试时使用绝对导入
    from styles.unified_theme_system import UnifiedThemeSystem, get_theme_system, ThemeMode
    from modern_ui_components import (
        MaterialButton, MaterialCard, MaterialProgressBar, MaterialSlider,
        MaterialComboBox, MaterialLineEdit, MaterialTextEdit, MaterialListWidget,
        MaterialTabWidget, FloatingActionButton, MaterialToolBar, StatusIndicator,
        LoadingSpinner, MaterialGroupBox, MaterialCheckBox, MaterialRadioButton,
        ResponsiveContainer, create_material_button, create_material_card
    )
    from notification_system import show_success, show_info

class WorkerSignals(QObject):
    """工作线程信号"""
    progress = pyqtSignal(float, str)  # 进度, 消息
    finished = pyqtSignal(object)  # 结果
    error = pyqtSignal(str)  # 错误信息

class AsyncWorker(QThread):
    """异步工作线程"""
    
    def __init__(self, coro, *args, **kwargs):
        super().__init__()
        self.coro = coro
        self.args = args
        self.kwargs = kwargs
        # 确保signals在主线程中创建
        self.signals = WorkerSignals()
        # 将signals移动到主线程，避免跨线程问题
        self.signals.moveToThread(QApplication.instance().thread())
        self.result = None
        
    def run(self):
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 运行协程
                self.result = loop.run_until_complete(
                    self.coro(*self.args, **self.kwargs)
                )
                
                self.signals.finished.emit(self.result)
                
            except Exception as e:
                logger.error(f"异步任务执行失败: {e}")
                self.signals.error.emit(str(e))
            finally:
                # 确保事件循环正确关闭
                try:
                    # 取消所有未完成的任务
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    
                    # 等待所有任务完成或取消
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        
                except Exception as cleanup_error:
                    logger.warning(f"清理事件循环时出错: {cleanup_error}")
                finally:
                    loop.close()
                    
        except Exception as e:
            logger.error(f"线程执行失败: {e}")
            self.signals.error.emit(str(e))

class NewMainWindow(QMainWindow):
    """新的主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化应用控制器
        self.app_controller = AppController()

        # 使用应用控制器的项目管理器实例（确保一致性）
        self.project_manager = self.app_controller.project_manager
        
        # 初始化一致性增强图像处理器（延迟初始化）
        self.consistency_image_processor = None
        
        # 当前项目名称
        self.current_project_name = None
        
        # 当前工作线程
        self.current_worker = None
        
        # 初始化自动保存管理器
        from src.utils.auto_save_manager import get_auto_save_manager
        self.auto_save_manager = get_auto_save_manager()
        
        # 初始化内存监控
        from src.utils.memory_optimizer import MemoryMonitor, ImageMemoryManager
        self.memory_monitor = MemoryMonitor()
        self.image_memory_manager = ImageMemoryManager()
        
        # 初始化UI
        self.init_ui()
        
        # 初始化应用控制器
        self.init_app_controller()
        
        # 应用现代化主题
        self.init_theme_system()
        
        # 设置自动保存和内存监控
        self._setup_auto_save()
        self._setup_memory_monitoring()
        
        # 初始化项目状态显示
        self.update_project_status()
        
        # 初始化文本占位符
        self.update_text_placeholder()
        
        logger.info("新主窗口初始化完成")
    
    def _setup_auto_save(self):
        """设置自动保存功能"""
        try:
            # 注册文本内容自动保存
            def get_text_data():
                if not hasattr(self, 'text_input') or not hasattr(self, 'rewritten_text'):
                    return {}
                return {
                    'original_text': self.text_input.toPlainText() if hasattr(self, 'text_input') else '',
                    'rewritten_text': self.rewritten_text.toPlainText() if hasattr(self, 'rewritten_text') else '',
                    'timestamp': time.time()
                }
            
            # 注册项目数据自动保存
            def get_project_data():
                if not self.project_manager or not self.project_manager.current_project:
                    return {}
                return self.project_manager.get_project_data()
            
            # 创建自动保存目录
            auto_save_dir = Path("auto_save")
            auto_save_dir.mkdir(exist_ok=True)
            
            # 注册自动保存回调
            self.auto_save_manager.register_save_callback(
                'text_content',
                get_text_data,
                str(auto_save_dir / 'text_content.json'),
                priority=1
            )
            
            self.auto_save_manager.register_save_callback(
                'project_data',
                get_project_data,
                str(auto_save_dir / 'project_data.json'),
                priority=0
            )
            
            # 启动自动保存
            self.auto_save_manager.start_auto_save()
            
            # 连接保存信号
            self.auto_save_manager.save_completed.connect(self._on_auto_save_completed)
            self.auto_save_manager.save_failed.connect(self._on_auto_save_failed)
            
            logger.info("自动保存功能设置完成")
            
        except Exception as e:
            logger.error(f"设置自动保存功能失败: {e}")
    
    def _setup_memory_monitoring(self):
        """设置内存监控功能"""
        try:
            # 连接内存警告信号
            self.memory_monitor.memory_warning.connect(self._on_memory_warning)
            self.memory_monitor.memory_critical.connect(self._on_memory_critical)
            
            # 启动内存监控
            self.memory_monitor.start_monitoring(interval_ms=10000)  # 每10秒检查一次
            
            logger.info("内存监控功能设置完成")
            
        except Exception as e:
            logger.error(f"设置内存监控功能失败: {e}")
    
    def _on_auto_save_completed(self, save_path: str):
        """自动保存完成处理"""
        logger.debug(f"自动保存完成: {save_path}")
        # 可以在状态栏显示保存状态
        if hasattr(self, 'status_label'):
            self.status_label.setText("自动保存完成")
            QTimer.singleShot(2000, lambda: self.status_label.setText("就绪"))
    
    def _on_auto_save_failed(self, save_path: str, error: str):
        """自动保存失败处理"""
        logger.warning(f"自动保存失败 {save_path}: {error}")
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"自动保存失败: {error}")
    
    def _on_memory_warning(self, memory_percent: float):
        """内存警告处理"""
        logger.warning(f"内存使用率警告: {memory_percent:.1%}")
        # 执行轻度清理
        self.image_memory_manager.cleanup_if_needed()
        
        # 显示警告信息
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"内存使用率: {memory_percent:.1%}")
            self.status_label.setStyleSheet("color: orange;")
    
    def _on_memory_critical(self, memory_percent: float):
        """内存严重警告处理"""
        logger.error(f"内存使用率严重警告: {memory_percent:.1%}")
        
        # 执行强制清理
        self.image_memory_manager.clear_cache()
        import gc
        gc.collect()
        
        # 显示严重警告
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"内存不足: {memory_percent:.1%}")
            self.status_label.setStyleSheet("color: red;")
        
        # 显示用户提示
        from src.gui.notification_system import show_warning
        show_warning(
            "内存使用率过高！\n\n"
            "系统已自动清理缓存，建议：\n"
            "1. 保存当前工作\n"
            "2. 关闭不必要的标签页\n"
            "3. 重启应用程序"
        )
    
    def mark_content_dirty(self):
        """标记内容已修改，需要自动保存"""
        try:
            self.auto_save_manager.mark_dirty('text_content')
            if self.project_manager and self.project_manager.current_project:
                self.auto_save_manager.mark_dirty('project_data')
        except Exception as e:
            logger.error(f"标记内容修改失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        try:
            # 停止自动保存和内存监控
            if hasattr(self, 'auto_save_manager'):
                self.auto_save_manager.stop_auto_save()
                # 执行最后一次保存
                self.auto_save_manager.save_immediately()
            
            if hasattr(self, 'memory_monitor'):
                self.memory_monitor.stop_monitoring()
            
            # 停止工作流程状态检查定时器
            if hasattr(self, 'workflow_status_timer'):
                self.workflow_status_timer.stop()
            
            logger.info("应用程序正常关闭")
            event.accept()
            
        except Exception as e:
            logger.error(f"关闭应用程序时出错: {e}")
            event.accept()
    

    
    def init_ui(self):
        """初始化现代化用户界面"""
        self.setWindowTitle("🎬 AI视频生成助手 - 现代化界面")

        # 初始化图像列表组件
        self.image_list = QListWidget()

        # 获取屏幕尺寸并设置合适的窗口大小
        screen = QApplication.desktop().screenGeometry()

        # 设置窗口为屏幕的90%，但不超过最大尺寸
        max_width = min(1600, int(screen.width() * 0.9))
        max_height = min(1000, int(screen.height() * 0.9))

        # 计算居中位置
        x = (screen.width() - max_width) // 2
        y = (screen.height() - max_height) // 2

        self.setGeometry(x, y, max_width, max_height)

        # 设置最小窗口大小
        self.setMinimumSize(1200, 800)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局（添加边距以获得更好的视觉效果）
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 8, 12, 12)
        main_layout.setSpacing(8)

        # 创建菜单栏
        self.create_menu_bar()

        # 创建现代化工具栏
        self.create_toolbar(main_layout)

        # 创建主要内容区域（使用卡片布局）
        self.create_main_content(main_layout)

        # 创建状态栏
        self.create_status_bar()

        # 🎨 应用UI优化
        self.apply_ui_optimizations()

    def apply_ui_optimizations(self):
        """应用UI优化"""
        try:
            # 导入UI优化器
            from .ui_optimizer import get_ui_optimizer

            # 获取优化器实例
            optimizer = get_ui_optimizer()

            # 优化主窗口
            optimizer.optimize_main_window(self)

            # 设置现代化窗口属性
            self.setAttribute(Qt.WA_StyledBackground, True)

            # 应用现代化样式表
            self.apply_modern_stylesheet()

            logger.info("UI优化应用成功")

        except Exception as e:
            logger.error(f"UI优化应用失败: {e}")

    def apply_modern_stylesheet(self):
        """应用现代化样式表"""
        modern_style = """
        /* 主窗口样式 */
        QMainWindow {
            background-color: #FFFBFE;
            color: #1C1B1F;
        }

        /* 工具栏增强样式 */
        QFrame[toolbar="true"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #F7F2FA, stop:1 #F1ECF4);
            border: 1px solid #E6E0E9;
            border-radius: 12px;
            padding: 8px;
        }

        /* 标签页增强样式 */
        QTabWidget::pane {
            background-color: #FFFBFE;
            border: 1px solid #E6E0E9;
            border-radius: 12px;
            margin-top: -1px;
        }

        QTabBar::tab {
            background-color: #F1ECF4;
            color: #49454F;
            border: none;
            border-radius: 20px;
            padding: 12px 24px;
            margin: 2px;
            min-width: 80px;
            font-weight: 500;
        }

        QTabBar::tab:selected {
            background-color: #EADDFF;
            color: #21005D;
            font-weight: 600;
        }

        QTabBar::tab:hover:!selected {
            background-color: rgba(103, 80, 164, 0.12);
        }

        /* 按钮增强样式 */
        QPushButton {
            background-color: #6750A4;
            color: #FFFFFF;
            border: none;
            border-radius: 20px;
            padding: 12px 24px;
            font-weight: 500;
            font-size: 14px;
            min-height: 40px;
        }

        QPushButton:hover {
            background-color: #7C4DFF;
            transform: translateY(-1px);
        }

        QPushButton:pressed {
            background-color: #5E35B1;
            transform: translateY(0px);
        }

        QPushButton[flat="true"] {
            background-color: transparent;
            color: #6750A4;
            border: 2px solid #CAC4D0;
        }

        QPushButton[flat="true"]:hover {
            background-color: rgba(103, 80, 164, 0.12);
            border-color: #6750A4;
        }

        /* 输入框增强样式 */
        QLineEdit, QTextEdit {
            background-color: #F1ECF4;
            color: #1C1B1F;
            border: 2px solid #CAC4D0;
            border-radius: 12px;
            padding: 12px 16px;
            font-size: 14px;
        }

        QLineEdit:focus, QTextEdit:focus {
            border-color: #6750A4;
            background-color: #FFFBFE;
        }

        /* 状态栏样式 */
        QStatusBar {
            background-color: #F1ECF4;
            color: #49454F;
            border: none;
            border-top: 1px solid #E6E0E9;
            padding: 8px;
            font-size: 12px;
        }
        """

        self.setStyleSheet(modern_style)
    
    def create_toolbar(self, parent_layout):
        """创建现代化工具栏"""
        # 使用MaterialCard作为工具栏容器
        toolbar_card = MaterialCard(elevation=1)
        toolbar_card.setMaximumHeight(60)  # 🔧 修复：限制工具栏最大高度，节省界面空间
        toolbar_layout = QHBoxLayout(toolbar_card)
        toolbar_layout.setContentsMargins(12, 6, 12, 6)  # 🔧 修复：减少上下边距，从12减少到6
        toolbar_layout.setSpacing(8)  # 🔧 修复：减少按钮间距，从12减少到8
        
        # 项目操作区域
        project_section = QWidget()
        project_layout = QHBoxLayout(project_section)
        project_layout.setContentsMargins(0, 0, 0, 0)
        project_layout.setSpacing(8)
        
        # 使用MaterialButton创建现代化按钮
        self.new_project_btn = MaterialButton("新建项目", "filled")
        self.new_project_btn.clicked.connect(self.new_project)
        project_layout.addWidget(self.new_project_btn)

        self.open_project_btn = MaterialButton("打开项目", "outlined")
        self.open_project_btn.clicked.connect(self.open_project)
        project_layout.addWidget(self.open_project_btn)
        
        self.save_project_btn = MaterialButton("保存项目", "outlined")
        self.save_project_btn.clicked.connect(self.save_project)
        project_layout.addWidget(self.save_project_btn)

        self.refresh_btn = MaterialButton("刷新", "outlined")
        self.refresh_btn.clicked.connect(self.refresh_project_data)
        project_layout.addWidget(self.refresh_btn)
        
        toolbar_layout.addWidget(project_section)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("QFrame { color: #E0E0E0; }")
        toolbar_layout.addWidget(separator)
        
        # 状态信息区域
        status_section = QWidget()
        status_layout = QHBoxLayout(status_section)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(12)
        
        # 服务状态指示器（使用StatusIndicator）
        self.service_status_indicator = StatusIndicator("服务状态")
        status_layout.addWidget(self.service_status_indicator)
        
        # 刷新服务按钮
        self.refresh_services_btn = MaterialButton("刷新服务", "text")
        self.refresh_services_btn.clicked.connect(self.refresh_services)
        status_layout.addWidget(self.refresh_services_btn)
        
        toolbar_layout.addWidget(status_section)
        
        # 弹性空间
        toolbar_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # 主题切换按钮
        self.theme_toggle_btn = MaterialButton("🌙", "text")
        self.theme_toggle_btn.setToolTip("切换深色/浅色主题")
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        self.theme_toggle_btn.setMaximumWidth(48)
        toolbar_layout.addWidget(self.theme_toggle_btn)
        
        parent_layout.addWidget(toolbar_card)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_project_action = QAction("新建项目", self)
        new_project_action.setShortcut("Ctrl+N")
        new_project_action.triggered.connect(self.new_project)
        file_menu.addAction(new_project_action)
        
        open_project_action = QAction("打开项目", self)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.triggered.connect(self.open_project)
        file_menu.addAction(open_project_action)
        
        file_menu.addSeparator()
        
        save_project_action = QAction("保存项目", self)
        save_project_action.setShortcut("Ctrl+S")
        save_project_action.triggered.connect(self.save_project)
        file_menu.addAction(save_project_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        # 日志管理子菜单
        log_menu = tools_menu.addMenu("日志管理")
        
        view_log_action = QAction("查看系统日志", self)
        view_log_action.triggered.connect(self.show_log_dialog)
        log_menu.addAction(view_log_action)
        
        clear_log_action = QAction("清空日志", self)
        clear_log_action.triggered.connect(self.clear_log)
        log_menu.addAction(clear_log_action)
        
        export_log_action = QAction("导出日志", self)
        export_log_action.triggered.connect(self.export_log)
        log_menu.addAction(export_log_action)
        
        tools_menu.addSeparator()
        
        refresh_services_action = QAction("刷新服务", self)
        refresh_services_action.triggered.connect(self.refresh_services)
        tools_menu.addAction(refresh_services_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        toggle_theme_action = QAction("切换主题", self)
        toggle_theme_action.setShortcut("Ctrl+T")
        toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(toggle_theme_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        help_action = QAction("使用帮助", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
    
    def create_main_content(self, parent_layout):
        """创建现代化主要内容区域"""
        # 创建主要内容容器
        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        
        # 左侧导航面板
        self.create_navigation_panel(content_layout)
        
        # 右侧主要工作区域
        self.create_work_area(content_layout)
        
        parent_layout.addWidget(content_container)
    
    def create_navigation_panel(self, parent_layout):
        """创建左侧导航面板"""
        # 导航面板卡片
        nav_card = MaterialCard(elevation=2)
        nav_card.setFixedWidth(280)
        nav_layout = QVBoxLayout(nav_card)
        nav_layout.setContentsMargins(16, 16, 16, 16)
        nav_layout.setSpacing(8)
        
        # 导航标题
        nav_title = QLabel("🎬 导航菜单")
        nav_title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        nav_title.setStyleSheet("color: #1976D2; margin-bottom: 8px;")
        nav_layout.addWidget(nav_title)
        
        # 创建导航按钮组
        self.nav_buttons = []
        nav_items = [
            ("🎭 工作流程", "workflow", "工作流程指导"),
            ("📝 AI创作", "text_creation", "文本创作和AI改写"),
            ("✍️ 分镜脚本", "storyboard", "五阶段分镜系统"),
            ("🖼️ 图像生成", "image_generation", "AI图像生成和处理"),
            ("🎵 配音合成", "voice_synthesis", "AI配音和音频处理"),
            ("🎬 视频制作", "video_production", "视频生成和合成"),
            ("🎨 一致性控制", "consistency", "角色和场景一致性"),
            ("📁 项目管理", "project_management", "创建、打开和管理项目"),
            ("⚙️ 系统设置", "settings", "应用程序设置")
        ]
        
        for text, key, tooltip in nav_items:
            btn = MaterialButton(text, "text")
            btn.setToolTip(tooltip)
            btn.setProperty("nav_key", key)
            btn.clicked.connect(lambda checked, k=key: self.switch_to_section(k))
            btn.setMinimumHeight(48)
            btn.setStyleSheet("""
                MaterialButton {
                    text-align: left;
                    padding-left: 16px;
                    border-radius: 8px;
                }
                MaterialButton:hover {
                    background-color: rgba(25, 118, 210, 0.08);
                }
                MaterialButton:pressed {
                    background-color: rgba(25, 118, 210, 0.12);
                }
            """)
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        # 添加弹性空间
        nav_layout.addStretch()
        
        # 系统状态区域
        status_card = MaterialCard(elevation=1)
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(12, 12, 12, 12)
        
        status_title = QLabel("📊 系统状态")
        status_title.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        status_layout.addWidget(status_title)
        
        # 系统状态指示器
        self.gpu_status = StatusIndicator("GPU")
        self.memory_status = StatusIndicator("内存")
        self.network_status = StatusIndicator("网络")
        
        status_layout.addWidget(self.gpu_status)
        status_layout.addWidget(self.memory_status)
        status_layout.addWidget(self.network_status)
        
        nav_layout.addWidget(status_card)
        
        parent_layout.addWidget(nav_card)
    
    def create_work_area(self, parent_layout):
        """创建右侧工作区域"""
        # 工作区域容器
        work_container = QWidget()
        work_container.setMaximumHeight(400)  # 🔧 修复：将工作台高度减少一半，节省界面空间
        work_layout = QVBoxLayout(work_container)
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(6)  # 进一步减少间距
        
        # 创建标签页（现代化风格）
        self.tab_widget = MaterialTabWidget()
        
        # 🎯 配音驱动工作流程 - 重新设计标签页顺序

        # 工作流程指导界面
        from src.gui.workflow_guide_widget import WorkflowGuideWidget
        self.workflow_guide = WorkflowGuideWidget(self)
        self.workflow_guide.switch_to_tab.connect(self.switch_to_tab_by_name)
        self.tab_widget.addTab(self.workflow_guide, "🎭 工作流程指南")

        # 启动工作流程状态检查定时器
        self.workflow_status_timer = QTimer()
        self.workflow_status_timer.timeout.connect(self.check_workflow_progress)
        self.workflow_status_timer.start(5000)  # 每5秒检查一次

        # 🔧 优化：按配音优先工作流程调整标签顺序

        # 第1步：文本创作（文本改写/AI创作）
        self.text_tab = self.create_text_tab()
        self.tab_widget.addTab(self.text_tab, "📝 文本创作")

        # 第2步：五阶段分镜（生成分镜脚本，为配音提供基础）
        self.five_stage_storyboard_tab = self.create_five_stage_storyboard_tab()
        self.tab_widget.addTab(self.five_stage_storyboard_tab, "🎬 五阶段分镜")

        # 第3步：一致性控制（在配音前进行一致性预览和设置）
        self.consistency_panel = ConsistencyControlPanel(None, self.project_manager, self)
        self.tab_widget.addTab(self.consistency_panel, "🎨 一致性控制")

        # 第4步：AI配音生成（基于分镜脚本生成配音）
        self.voice_generation_tab = VoiceGenerationTab(self.app_controller, self.project_manager, self)
        self.tab_widget.addTab(self.voice_generation_tab, "🎵 AI配音生成")

        # 第5步：图像生成（包含两个子标签：传统分镜生图 + 配音时长生图）
        self.image_generation_container = self.create_image_generation_container()
        self.tab_widget.addTab(self.image_generation_container, "🖼️ 图像生成")

        # 第6步：视频生成（AI视频生成）
        self.video_generation_tab = self.create_video_generation_tab()
        self.tab_widget.addTab(self.video_generation_tab, "🎬 视频生成")

        # 第7步：视频合成（传统视频合成）
        self.video_synthesis_tab = self.create_video_synthesis_tab()
        self.tab_widget.addTab(self.video_synthesis_tab, "🎞️ 视频合成")

        # 设置标签页
        from src.gui.settings_tab import SettingsTab
        self.settings_tab = SettingsTab(self)
        self.tab_widget.addTab(self.settings_tab, "⚙️ 设置")

        # 🔧 连接配音驱动工作流程信号
        self._connect_voice_driven_workflow_signals()
        
        work_layout.addWidget(self.tab_widget)
        parent_layout.addWidget(work_container)
    
    def switch_to_section(self, section_key):
        """切换到指定的功能区域"""
        try:
            # 更新导航按钮状态
            for btn in self.nav_buttons:
                if btn.property("nav_key") == section_key:
                    btn.setStyleSheet("""
                        MaterialButton {
                            text-align: left;
                            padding-left: 16px;
                            border-radius: 8px;
                            background-color: rgba(25, 118, 210, 0.12);
                            color: #1976D2;
                            font-weight: bold;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        MaterialButton {
                            text-align: left;
                            padding-left: 16px;
                            border-radius: 8px;
                        }
                        MaterialButton:hover {
                            background-color: rgba(25, 118, 210, 0.08);
                        }
                        MaterialButton:pressed {
                            background-color: rgba(25, 118, 210, 0.12);
                        }
                    """)
            
            # 根据section_key切换到对应的标签页
            section_mapping = {
                "workflow": "🎭 工作流程指南",
                "text_creation": "📝 文本创作",
                "storyboard": "🎬 五阶段分镜",
                "image_generation": "🖼️ 图像生成",
                "voice_synthesis": "🎵 AI配音生成",
                "video_production": "🎬 视频生成",
                "consistency": "🎨 一致性控制",
                "project_management": "🎭 工作流程指南",  # 暂时映射到工作流程指南
                "settings": "⚙️ 设置"
            }
            
            if section_key in section_mapping:
                tab_name = section_mapping[section_key]
                self.switch_to_tab_by_name(tab_name)
                logger.info(f"切换到功能区域: {section_key} -> {tab_name}")
            
        except Exception as e:
            logger.error(f"切换功能区域失败: {e}")

    def _connect_voice_driven_workflow_signals(self):
        """连接配音驱动工作流程的信号"""
        try:
            # 连接配音数据准备完成信号到图像生成模块
            if hasattr(self, 'voice_generation_tab'):
                # 连接到传统分镜生图标签（向后兼容）
                if hasattr(self, 'traditional_image_tab'):
                    if hasattr(self.voice_generation_tab, 'voice_data_ready'):
                        self.voice_generation_tab.voice_data_ready.connect(
                            self.traditional_image_tab.receive_voice_data
                        )

                # 连接到配音时长生图标签
                if hasattr(self, 'voice_driven_image_tab'):
                    if hasattr(self.voice_generation_tab, 'voice_data_ready'):
                        self.voice_generation_tab.voice_data_ready.connect(
                            self.voice_driven_image_tab.load_voice_data
                        )

                if hasattr(self.voice_generation_tab, 'voice_batch_completed'):
                    self.voice_generation_tab.voice_batch_completed.connect(
                        self._on_voice_batch_completed
                    )

                # 🔧 新增：配音驱动分镜生成完成信号
                if hasattr(self.voice_generation_tab, 'voice_driven_storyboard_completed'):
                    self.voice_generation_tab.voice_driven_storyboard_completed.connect(
                        self._on_voice_driven_storyboard_completed
                    )

                logger.info("配音驱动工作流程信号连接成功")
            else:
                logger.warning("无法连接配音驱动工作流程信号：标签页未初始化")
        except Exception as e:
            logger.error(f"连接配音驱动工作流程信号失败: {e}")

    def _connect_voice_first_workflow_signals(self):
        """连接配音优先工作流程的信号（向后兼容）"""
        # 调用新的配音驱动工作流程信号连接
        self._connect_voice_driven_workflow_signals()

    def _on_voice_batch_completed(self, voice_data_list):
        """配音批量生成完成处理"""
        try:
            logger.info(f"配音批量生成完成，共 {len(voice_data_list)} 个段落")

            # 检查是否启用配音优先工作流程
            if self.project_manager and self.project_manager.current_project:
                workflow_settings = self.project_manager.current_project.get('workflow_settings', {})
                if workflow_settings.get('mode') == 'voice_first' and workflow_settings.get('auto_generate_images_after_voice', True):
                    # 自动切换到图像生成标签页
                    for i in range(self.tab_widget.count()):
                        if self.tab_widget.tabText(i) == "📋 分镜图像生成":
                            self.tab_widget.setCurrentIndex(i)
                            logger.info("已自动切换到分镜图像生成标签页")
                            break

                    # 显示提示信息
                    from src.gui.notification_system import show_info
                    show_info("配音生成完成！已自动切换到图像生成界面，请查看基于配音内容生成的图像提示词。")

        except Exception as e:
            logger.error(f"处理配音批量生成完成事件失败: {e}")

    def _on_voice_driven_storyboard_completed(self, storyboard_data):
        """配音驱动分镜生成完成处理"""
        try:
            logger.info("配音驱动分镜生成完成")

            # 自动切换到配音驱动分镜标签页
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "🎭 配音驱动分镜":
                    self.tab_widget.setCurrentIndex(i)
                    logger.info("已自动切换到配音驱动分镜标签页")
                    break

            # 刷新五阶段分镜界面
            if hasattr(self, 'five_stage_storyboard_tab') and hasattr(self.five_stage_storyboard_tab, 'refresh_from_project'):
                self.five_stage_storyboard_tab.refresh_from_project()

            # 显示成功信息
            from src.gui.notification_system import show_info
            show_info(
                "配音驱动分镜生成完成！\n\n"
                "系统已基于配音内容重新生成五阶段分镜，\n"
                "确保分镜与配音内容完全一致。\n\n"
                "现在可以查看分镜结果或直接进行图像生成。"
            )

        except Exception as e:
            logger.error(f"处理配音驱动分镜生成完成事件失败: {e}")

    def refresh_five_stage_storyboard(self):
        """刷新五阶段分镜界面"""
        try:
            if hasattr(self, 'five_stage_storyboard_tab') and hasattr(self.five_stage_storyboard_tab, 'refresh_from_project'):
                self.five_stage_storyboard_tab.refresh_from_project()
                logger.info("五阶段分镜界面已刷新")
        except Exception as e:
            logger.error(f"刷新五阶段分镜界面失败: {e}")

    def switch_to_tab_by_name(self, tab_name):
        """根据标签页名称切换标签页"""
        try:
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == tab_name:
                    self.tab_widget.setCurrentIndex(i)
                    logger.info(f"已切换到标签页: {tab_name}")

                    # 🔧 更新：工作流程指导的步骤状态（配音优先工作流程）
                    if hasattr(self, 'workflow_guide'):
                        step_mapping = {
                            "📝 文本创作": 1,
                            "🎬 五阶段分镜": 2,
                            "🎨 一致性控制": 3,
                            "🎵 AI配音生成": 4,
                            "🖼️ 图像生成": 5,
                            "🎬 视频合成": 6
                        }

                        if tab_name in step_mapping:
                            step_number = step_mapping[tab_name]
                            self.workflow_guide.update_step_status(step_number, "active")

                    return

            logger.warning(f"未找到标签页: {tab_name}")

        except Exception as e:
            logger.error(f"切换标签页失败: {e}")

    def check_workflow_progress(self):
        """检查工作流程进度并更新状态"""
        try:
            # 🔧 修复：添加更严格的检查条件，避免KeyboardInterrupt
            if not hasattr(self, 'workflow_guide') or not self.workflow_guide:
                return

            # 🔧 修复：添加线程安全检查
            if not hasattr(self, '_checking_progress'):
                self._checking_progress = False

            if self._checking_progress:
                return  # 避免重复检查

            self._checking_progress = True

            # 检查各个步骤的完成状态
            step_status = self._get_workflow_step_status()

            # 更新工作流程指南的状态
            for step_num, status in step_status.items():
                if status == "completed":
                    self.workflow_guide.update_step_status(step_num, "completed")
                elif status == "active":
                    self.workflow_guide.update_step_status(step_num, "active")

        except KeyboardInterrupt:
            # 🔧 修复：正确处理键盘中断
            logger.warning("工作流程进度检查被用户中断")
        except Exception as e:
            logger.debug(f"检查工作流程进度失败: {e}")
        finally:
            # 🔧 修复：确保标志位被重置
            if hasattr(self, '_checking_progress'):
                self._checking_progress = False

    def _get_workflow_step_status(self):
        """获取工作流程各步骤的状态"""
        status = {}

        try:
            # 步骤1：文本创作 - 检查是否有改写文本或原始文本
            if hasattr(self, 'rewritten_text') and self.rewritten_text.toPlainText().strip():
                status[1] = "completed"
            elif hasattr(self, 'text_input') and self.text_input.toPlainText().strip():
                status[1] = "completed"
            else:
                status[1] = "active"

            # 🔧 更新：步骤2：五阶段分镜 - 检查是否有分镜数据
            storyboard_completed = False
            if hasattr(self, 'five_stage_storyboard_tab') and self.five_stage_storyboard_tab:
                try:
                    # 检查是否有分镜数据（可以检查项目数据或界面状态）
                    if self.project_manager and self.project_manager.current_project:
                        project_data = self.project_manager.get_project_data()
                        if project_data and project_data.get('storyboard_data'):
                            storyboard_completed = True
                except:
                    pass

            if storyboard_completed:
                status[2] = "completed"
            elif status[1] == "completed":
                status[2] = "active"
            else:
                status[2] = "pending"

            # 🔧 更新：步骤3：AI配音生成 - 检查是否有配音数据
            voice_completed = False
            if hasattr(self, 'voice_generation_tab') and self.voice_generation_tab:
                try:
                    # 检查配音表格是否有数据
                    table = self.voice_generation_tab.voice_table
                    if table.rowCount() > 0:
                        # 检查是否有生成的配音文件
                        for row in range(table.rowCount()):
                            narration_item = table.item(row, 2)  # 旁白文件列
                            if narration_item and narration_item.text().strip() and narration_item.text() != "未生成":
                                voice_completed = True
                                break
                except:
                    pass

            if voice_completed:
                status[3] = "completed"
            elif status[2] == "completed":
                status[3] = "active"
            else:
                status[3] = "pending"

            # 🔧 更新：步骤4：图像生成 - 检查是否有生成的图像
            image_completed = False
            if hasattr(self, 'storyboard_image_tab') and self.storyboard_image_tab:
                try:
                    # 检查项目数据中是否有生成的图像
                    if self.project_manager and self.project_manager.current_project:
                        project_data = self.project_manager.get_project_data()
                        if project_data and project_data.get('image_generation'):
                            image_data = project_data.get('image_generation', {})
                            if image_data.get('generated_images'):
                                image_completed = True
                except:
                    pass

            if image_completed:
                status[4] = "completed"
            elif status[3] == "completed":
                status[4] = "active"
            else:
                status[4] = "pending"

            # 🔧 更新：步骤5：一致性控制 - 检查是否有角色或场景数据
            consistency_completed = False
            if hasattr(self, 'consistency_panel') and self.consistency_panel:
                try:
                    # 检查是否有角色或场景数据
                    if (hasattr(self.consistency_panel, 'character_manager') and
                        self.consistency_panel.character_manager and
                        len(self.consistency_panel.character_manager.characters) > 0):
                        consistency_completed = True
                    elif (hasattr(self.consistency_panel, 'scene_manager') and
                          self.consistency_panel.scene_manager and
                          len(self.consistency_panel.scene_manager.scenes) > 0):
                        consistency_completed = True
                except:
                    pass

            if consistency_completed:
                status[5] = "completed"
            elif status[4] == "completed":
                status[5] = "active"
            else:
                status[5] = "pending"

            # 🔧 更新：步骤6：视频合成 - 检查是否有合成的视频
            video_completed = False
            if hasattr(self, 'video_tab') and self.video_tab:
                try:
                    # 检查项目数据中是否有合成的视频
                    if self.project_manager and self.project_manager.current_project:
                        project_data = self.project_manager.get_project_data()
                        if project_data and project_data.get('video_generation'):
                            video_data = project_data.get('video_generation', {})
                            if video_data.get('output_video_path'):
                                video_completed = True
                except:
                    pass

            if video_completed:
                status[6] = "completed"
            elif status[5] == "completed":
                status[6] = "active"
            else:
                status[6] = "pending"

        except Exception as e:
            logger.debug(f"获取工作流程状态失败: {e}")

        return status

    def create_text_tab(self):
        """创建文本处理标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 文本输入区域
        text_group = QGroupBox("📝 文本输入")
        text_layout = QVBoxLayout(text_group)
        text_layout.setContentsMargins(8, 8, 8, 8)  # 减少边距
        text_layout.setSpacing(6)  # 减少间距
        
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("请先创建项目，然后输入要转换为视频的文本内容...")
        self.text_input.setMinimumHeight(150)  # 减少最小高度
        self.text_input.setMaximumHeight(200)  # 限制最大高度
        # 连接文本变化信号，自动保存
        self.text_input.textChanged.connect(self.on_text_changed)
        text_layout.addWidget(self.text_input)
        
        # 🔧 新增：视频配置选择区域
        config_group = QGroupBox("🎬 视频配置")
        config_layout = QHBoxLayout(config_group)
        config_layout.setContentsMargins(8, 8, 8, 8)  # 减少边距
        config_layout.setSpacing(10)  # 设置合适的间距

        # 风格选择
        config_layout.addWidget(QLabel("风格:"))
        self.text_style_combo = QComboBox()
        self.text_style_combo.addItems([
            "电影风格", "动漫风格", "吉卜力风格", "赛博朋克风格",
            "水彩插画风格", "像素风格", "写实摄影风格"
        ])
        self.text_style_combo.setCurrentText("电影风格")  # 默认选择
        self.text_style_combo.setToolTip("选择视频的整体风格，将影响后续的分镜生成和图像生成")
        self.text_style_combo.currentTextChanged.connect(self.on_text_style_changed)
        config_layout.addWidget(self.text_style_combo)

        # 添加间距
        config_layout.addSpacing(20)

        # 模型选择
        config_layout.addWidget(QLabel("模型:"))
        self.text_model_combo = QComboBox()
        self.text_model_combo.addItems(["通义千问", "智谱AI", "百度文心", "腾讯混元"])
        self.text_model_combo.setCurrentText("通义千问")  # 默认选择
        self.text_model_combo.setToolTip("选择用于文本创作和改写的大模型")
        self.text_model_combo.currentTextChanged.connect(self.on_text_model_changed)
        config_layout.addWidget(self.text_model_combo)

        config_layout.addStretch()
        text_layout.addWidget(config_group)

        # 恢复上次的选择
        self.restore_text_style_and_model_selection()

        # 文本操作按钮
        text_buttons_layout = QHBoxLayout()

        self.load_text_btn = QPushButton("加载文本文件")
        self.load_text_btn.clicked.connect(self.load_text_file)
        text_buttons_layout.addWidget(self.load_text_btn)

        self.ai_create_btn = QPushButton("🤖 AI创作故事")
        self.ai_create_btn.clicked.connect(self.ai_create_story)
        self.ai_create_btn.setToolTip("根据输入的主题或关键词，AI自动创作1500-2000字的完整故事\n适用场景：当您有创作灵感但需要完整故事时使用")
        text_buttons_layout.addWidget(self.ai_create_btn)

        self.rewrite_text_btn = QPushButton("AI改写文本")
        self.rewrite_text_btn.clicked.connect(self.rewrite_text)
        self.rewrite_text_btn.setToolTip("对已有文本进行润色和改写，保持原意但提升表达效果\n适用场景：当您已有文本内容但需要优化语言表达时使用")
        text_buttons_layout.addWidget(self.rewrite_text_btn)

        self.clear_text_btn = QPushButton("清空文本")
        self.clear_text_btn.clicked.connect(self.clear_text)
        text_buttons_layout.addWidget(self.clear_text_btn)

        text_buttons_layout.addStretch()
        text_layout.addLayout(text_buttons_layout)

        # 添加功能说明
        help_label = QLabel("""
<div style='background-color: #f0f8ff; padding: 10px; border-radius: 5px; border: 1px solid #d0e7ff;'>
<b>💡 功能说明：</b><br>
• <b>🤖 AI创作故事</b>：输入主题关键词（如"星球大战"），AI自动创作1500-2000字完整故事<br>
• <b>AI改写文本</b>：对已有文本进行润色优化，保持原意但提升表达效果<br>
• <b>使用建议</b>：有创作灵感时用AI创作，有现成文本时用AI改写
</div>
        """)
        help_label.setWordWrap(True)
        help_label.setStyleSheet("QLabel { margin: 5px; }")
        text_layout.addWidget(help_label)

        layout.addWidget(text_group)
        
        # 改写后的文本显示区域
        rewritten_group = QGroupBox("✨ 改写后的文本")
        rewritten_layout = QVBoxLayout(rewritten_group)
        rewritten_layout.setContentsMargins(8, 8, 8, 8)  # 减少边距
        rewritten_layout.setSpacing(6)  # 减少间距
        
        self.rewritten_text = QTextEdit()
        self.rewritten_text.setReadOnly(True)
        self.rewritten_text.setMinimumHeight(120)  # 减少最小高度
        self.rewritten_text.setMaximumHeight(180)  # 限制最大高度
        rewritten_layout.addWidget(self.rewritten_text)
        
        layout.addWidget(rewritten_group)
        
        # 改写文本进度条
        progress_layout = QHBoxLayout()
        
        self.rewrite_progress = QProgressBar()
        self.rewrite_progress.setVisible(False)
        self.rewrite_progress.setFixedHeight(12)
        # 应用现代化样式
        self.rewrite_progress.setStyleSheet("""
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
                                          stop: 0 #66bb6a, stop: 1 #4caf50);
                border-radius: 3px;
                margin: 0px;
            }
        """)
        progress_layout.addWidget(self.rewrite_progress)
        
        layout.addLayout(progress_layout)
        
        return tab
    

    
    def create_five_stage_storyboard_tab(self):
        """创建五阶段分镜生成标签页"""
        # 使用新的五阶段分镜生成标签页
        return FiveStageStoryboardTab(self)
    
    def auto_switch_to_five_stage_storyboard(self):
        """自动跳转到五阶段分镜系统的第一阶段"""
        try:
            # 查找五阶段分镜标签页的索引
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "🎬 五阶段分镜":
                    # 切换到五阶段分镜标签页
                    self.tab_widget.setCurrentIndex(i)
                    
                    # 确保五阶段分镜标签页切换到第一阶段
                    if hasattr(self, 'five_stage_storyboard_tab') and self.five_stage_storyboard_tab:
                        # 切换到第一个标签页（阶段1）
                        if hasattr(self.five_stage_storyboard_tab, 'tab_widget'):
                            self.five_stage_storyboard_tab.tab_widget.setCurrentIndex(0)
                        
                        # 如果有改写后的文本，自动加载到五阶段分镜的输入框
                        if hasattr(self.five_stage_storyboard_tab, 'load_text_from_main'):
                            self.five_stage_storyboard_tab.load_text_from_main()
                    
                    logger.info("已自动跳转到五阶段分镜系统的第一阶段")
                    show_info("文本改写完成！已自动跳转到五阶段分镜系统，请继续进行全局分析。")
                    break
        except Exception as e:
            logger.error(f"自动跳转到五阶段分镜失败: {e}")
    
    def create_image_generation_container(self):
        """🔧 新增：创建图像生成容器，包含两个子标签"""
        from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout

        # 创建容器widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建子标签widget
        sub_tab_widget = QTabWidget()

        # 传统分镜生图标签
        self.traditional_image_tab = StoryboardImageGenerationTab(self.app_controller, self.project_manager, self)
        sub_tab_widget.addTab(self.traditional_image_tab, "📋 传统分镜生图")

        # 配音时长生图标签
        self.voice_driven_image_tab = self.create_voice_driven_image_tab()
        sub_tab_widget.addTab(self.voice_driven_image_tab, "🎵 配音时长生图")

        layout.addWidget(sub_tab_widget)

        # 保持向后兼容性，将传统标签设为主要引用
        self.storyboard_image_tab = self.traditional_image_tab

        return container

    def create_voice_driven_image_tab(self):
        """🔧 新增：创建配音时长生图标签"""
        from src.gui.voice_driven_image_tab import VoiceDrivenImageTab
        return VoiceDrivenImageTab(self.app_controller, self.project_manager, self)
    
    def create_video_generation_tab(self):
        """创建AI视频生成标签页"""
        from src.gui.video_generation_tab import VideoGenerationTab
        return VideoGenerationTab(self.app_controller, self.project_manager, self)

    def create_video_synthesis_tab(self):
        """创建传统视频合成标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 视频配置
        config_group = QGroupBox("视频生成配置")
        config_layout = QFormLayout(config_group)
        
        # 帧率
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(15, 60)
        self.fps_spin.setValue(30)  # 修改为CogVideoX支持的帧率
        config_layout.addRow("帧率 (FPS):", self.fps_spin)
        
        # 每镜头时长
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(1.0, 10.0)
        self.duration_spin.setValue(3.0)
        self.duration_spin.setSingleStep(0.5)
        config_layout.addRow("每镜头时长 (秒):", self.duration_spin)
        
        # 转场效果
        self.transition_combo = QComboBox()
        self.transition_combo.addItems(["fade", "cut", "dissolve", "slide_left", "slide_right", "zoom_in", "zoom_out"])
        config_layout.addRow("转场效果:", self.transition_combo)
        
        # 背景音乐
        music_layout = QHBoxLayout()
        self.music_path_edit = QLineEdit()
        self.music_path_edit.setPlaceholderText("选择背景音乐文件...")
        music_layout.addWidget(self.music_path_edit)
        
        self.browse_music_btn = QPushButton("浏览")
        self.browse_music_btn.clicked.connect(self.browse_music_file)
        music_layout.addWidget(self.browse_music_btn)
        
        config_layout.addRow("背景音乐:", music_layout)
        
        # 音乐音量
        self.music_volume_slider = QSlider(Qt.Horizontal)  # type: ignore
        self.music_volume_slider.setRange(0, 100)
        self.music_volume_slider.setValue(30)
        config_layout.addRow("音乐音量:", self.music_volume_slider)
        
        layout.addWidget(config_group)
        
        # 视频操作按钮
        video_buttons_layout = QHBoxLayout()
        
        self.create_video_btn = QPushButton("创建视频")
        self.create_video_btn.clicked.connect(self.create_video)
        video_buttons_layout.addWidget(self.create_video_btn)
        
        self.create_animated_btn = QPushButton("创建动画视频")
        self.create_animated_btn.clicked.connect(self.create_animated_video)
        video_buttons_layout.addWidget(self.create_animated_btn)
        
        self.add_subtitles_btn = QPushButton("添加字幕")
        self.add_subtitles_btn.clicked.connect(self.add_subtitles)
        video_buttons_layout.addWidget(self.add_subtitles_btn)
        
        video_buttons_layout.addStretch()
        layout.addLayout(video_buttons_layout)
        
        # 视频预览区域
        self.video_info_label = QLabel("暂无视频")
        self.video_info_label.setAlignment(Qt.AlignCenter)  # type: ignore
        self.video_info_label.setMinimumHeight(200)
        self.video_info_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #555555;
                border-radius: 8px;
                background-color: #404040;
            }
        """)
        layout.addWidget(self.video_info_label)
        
        return tab

    def on_text_style_changed(self, style_text):
        """文本创作界面风格选择变化时的处理"""
        from src.utils.logger import logger
        logger.info(f"文本创作界面风格选择变更: {style_text}")

        # 保存风格选择到配置
        self.save_text_style_selection(style_text)

        # 同步到其他界面的风格选择
        self.sync_style_to_other_tabs(style_text)

    def on_text_model_changed(self, model_text):
        """文本创作界面模型选择变化时的处理"""
        from src.utils.logger import logger
        logger.info(f"文本创作界面模型选择变更: {model_text}")

        # 保存模型选择到配置
        self.save_text_model_selection(model_text)

        # 同步到其他界面的模型选择
        self.sync_model_to_other_tabs(model_text)

    def save_text_style_selection(self, style_text):
        """保存文本创作界面的风格选择"""
        try:
            if hasattr(self, 'config_manager') and self.config_manager:
                config = self.config_manager.config
                if 'ui_settings' not in config:
                    config['ui_settings'] = {}
                config['ui_settings']['text_selected_style'] = style_text
                self.config_manager.save_config(config)

                from src.utils.logger import logger
                logger.debug(f"文本创作风格选择已保存: {style_text}")
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"保存文本创作风格选择失败: {e}")

    def save_text_model_selection(self, model_text):
        """保存文本创作界面的模型选择"""
        try:
            if hasattr(self, 'config_manager') and self.config_manager:
                config = self.config_manager.config
                if 'ui_settings' not in config:
                    config['ui_settings'] = {}
                config['ui_settings']['text_selected_model'] = model_text
                self.config_manager.save_config(config)

                from src.utils.logger import logger
                logger.debug(f"文本创作模型选择已保存: {model_text}")
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"保存文本创作模型选择失败: {e}")

    def sync_style_to_other_tabs(self, style_text):
        """同步风格选择到其他标签页"""
        try:
            # 同步到五阶段分镜标签页
            if hasattr(self, 'five_stage_storyboard_tab') and self.five_stage_storyboard_tab:
                if hasattr(self.five_stage_storyboard_tab, 'style_combo'):
                    self.five_stage_storyboard_tab.style_combo.setCurrentText(style_text)

                # 🔧 修复：同步后保存到项目文件中
                self._save_style_to_project(style_text)

            # 同步到传统分镜标签页
            if hasattr(self, 'storyboard_tab') and self.storyboard_tab:
                if hasattr(self.storyboard_tab, 'style_combo'):
                    self.storyboard_tab.style_combo.setCurrentText(style_text)

            from src.utils.logger import logger
            logger.debug(f"风格选择已同步到其他标签页: {style_text}")
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"同步风格选择失败: {e}")

    def sync_model_to_other_tabs(self, model_text):
        """同步模型选择到其他标签页"""
        try:
            # 同步到五阶段分镜标签页
            if hasattr(self, 'five_stage_storyboard_tab') and self.five_stage_storyboard_tab:
                if hasattr(self.five_stage_storyboard_tab, 'model_combo'):
                    # 查找对应的模型选项
                    for i in range(self.five_stage_storyboard_tab.model_combo.count()):
                        if model_text in self.five_stage_storyboard_tab.model_combo.itemText(i):
                            self.five_stage_storyboard_tab.model_combo.setCurrentIndex(i)
                            break

                # 🔧 修复：同步后保存到项目文件中
                self._save_model_to_project(model_text)

            # 同步到传统分镜标签页
            if hasattr(self, 'storyboard_tab') and self.storyboard_tab:
                if hasattr(self.storyboard_tab, 'model_combo'):
                    # 查找对应的模型选项
                    for i in range(self.storyboard_tab.model_combo.count()):
                        if model_text in self.storyboard_tab.model_combo.itemText(i):
                            self.storyboard_tab.model_combo.setCurrentIndex(i)
                            break

            from src.utils.logger import logger
            logger.debug(f"模型选择已同步到其他标签页: {model_text}")
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"同步模型选择失败: {e}")

    def _save_style_to_project(self, style_text):
        """保存风格选择到当前项目文件"""
        try:
            if hasattr(self, 'project_manager') and self.project_manager and self.project_manager.current_project:
                project_data = self.project_manager.current_project

                # 确保五阶段分镜数据结构存在
                if 'five_stage_storyboard' not in project_data:
                    project_data['five_stage_storyboard'] = {}

                # 更新风格设置
                project_data['five_stage_storyboard']['selected_style'] = style_text

                # 保存项目文件
                self.project_manager.save_project()

                from src.utils.logger import logger
                logger.info(f"风格选择已保存到项目文件: {style_text}")
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"保存风格选择到项目文件失败: {e}")

    def _save_model_to_project(self, model_text):
        """保存模型选择到当前项目文件"""
        try:
            if hasattr(self, 'project_manager') and self.project_manager and self.project_manager.current_project:
                project_data = self.project_manager.current_project

                # 确保五阶段分镜数据结构存在
                if 'five_stage_storyboard' not in project_data:
                    project_data['five_stage_storyboard'] = {}

                # 更新模型设置
                project_data['five_stage_storyboard']['selected_model'] = model_text

                # 保存项目文件
                self.project_manager.save_project()

                from src.utils.logger import logger
                logger.info(f"模型选择已保存到项目文件: {model_text}")
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"保存模型选择到项目文件失败: {e}")

    def restore_text_creation_settings_from_project(self, project_config):
        """从项目配置中恢复文章创作界面的风格和模型选择"""
        try:
            from src.utils.logger import logger

            # 恢复风格选择 - 尝试多个可能的位置
            style_setting = ""

            # 方法1：从五阶段分镜数据中获取
            five_stage_data = project_config.get("five_stage_storyboard", {})
            style_setting = five_stage_data.get("selected_style", "")

            # 方法2：从text_creation中获取
            if not style_setting:
                text_creation_data = project_config.get("text_creation", {})
                style_setting = text_creation_data.get("selected_style", "")

            # 方法3：从图像生成设置中获取
            if not style_setting:
                image_settings = project_config.get("image_generation", {}).get("settings", {})
                style_setting = image_settings.get("style", "")

            # 方法4：从根级别获取
            if not style_setting:
                style_setting = project_config.get("style_setting", "")

            if style_setting and hasattr(self, 'text_style_combo'):
                # 查找匹配的风格选项
                for i in range(self.text_style_combo.count()):
                    item_text = self.text_style_combo.itemText(i)
                    if style_setting in item_text or item_text in style_setting:
                        self.text_style_combo.setCurrentIndex(i)
                        logger.info(f"从项目恢复文章创作风格设置: {style_setting}")
                        break
                else:
                    logger.warning(f"未找到匹配的风格选项: {style_setting}")

            # 恢复模型选择 - 尝试多个可能的位置
            model_setting = ""

            # 方法1：从五阶段分镜数据中获取
            model_setting = five_stage_data.get("selected_model", "")

            # 方法2：从text_creation中获取
            if not model_setting:
                text_creation_data = project_config.get("text_creation", {})
                model_setting = text_creation_data.get("selected_model", "")

            # 方法3：从根级别获取
            if not model_setting:
                model_setting = project_config.get("model_setting", "")

            if model_setting and hasattr(self, 'text_model_combo'):
                # 查找匹配的模型选项
                for i in range(self.text_model_combo.count()):
                    item_text = self.text_model_combo.itemText(i)
                    if model_setting in item_text or item_text in model_setting:
                        self.text_model_combo.setCurrentIndex(i)
                        logger.info(f"从项目恢复文章创作模型设置: {model_setting}")
                        break
                else:
                    logger.warning(f"未找到匹配的模型选项: {model_setting}")

            # 同步到其他标签页
            if style_setting:
                self.sync_style_to_other_tabs(style_setting)
            if model_setting:
                self.sync_model_to_other_tabs(model_setting)

        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"从项目恢复文章创作设置失败: {e}")

    def restore_text_style_and_model_selection(self):
        """恢复文本创作界面的风格和模型选择"""
        try:
            if hasattr(self, 'config_manager') and self.config_manager:
                config = self.config_manager.config
                ui_settings = config.get('ui_settings', {})

                # 恢复风格选择
                saved_style = ui_settings.get('text_selected_style', '电影风格')
                if hasattr(self, 'text_style_combo'):
                    index = self.text_style_combo.findText(saved_style)
                    if index >= 0:
                        self.text_style_combo.setCurrentIndex(index)

                # 恢复模型选择
                saved_model = ui_settings.get('text_selected_model', '通义千问')
                if hasattr(self, 'text_model_combo'):
                    index = self.text_model_combo.findText(saved_model)
                    if index >= 0:
                        self.text_model_combo.setCurrentIndex(index)

                from src.utils.logger import logger
                logger.debug(f"恢复文本创作选择 - 风格: {saved_style}, 模型: {saved_model}")
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"恢复文本创作选择失败: {e}")

    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = self.statusBar()
        
        # 进度条 - 现代化样式
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(12)
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
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)
    
    def init_app_controller(self):
        """初始化应用控制器"""
        def on_init_finished():
            self.update_service_status()
            self.update_providers()
            self._init_consistency_processor()
            self.status_label.setText("应用初始化完成")
        
        def on_init_error(error):
            self.status_label.setText(f"初始化失败: {error}")
            QMessageBox.critical(self, "初始化失败", f"应用初始化失败:\n{error}")
        
        # 创建初始化工作线程
        self.init_worker = AsyncWorker(self.app_controller.initialize)
        self.init_worker.signals.finished.connect(on_init_finished)
        self.init_worker.signals.error.connect(on_init_error)
        self.init_worker.start()
        
        self.status_label.setText("正在初始化应用...")
    
    def update_service_status(self):
        """更新服务状态"""
        # 这里可以添加服务状态检查逻辑
        try:
            if hasattr(self, 'gpu_status'):
                self.gpu_status.set_status("正常", "#28a745")
            if hasattr(self, 'memory_status'):
                self.memory_status.set_status("正常", "#28a745")
            if hasattr(self, 'network_status'):
                self.network_status.set_status("正常", "#28a745")
        except Exception as e:
            logger.error(f"更新服务状态失败: {e}")
    
    def update_providers(self):
        """更新提供商列表"""
        try:
            providers = self.app_controller.get_available_providers()

            # 图像提供商配置已移至设置标签页，这里不再需要更新
            logger.info(f"可用提供商: {providers}")

            # 通过storyboard_tab更新LLM提供商
            if hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'load_providers'):
                self.storyboard_tab.load_providers()

        except Exception as e:
            logger.error(f"更新提供商列表失败: {e}")
    
    def show_progress(self, progress: float, message: str):
        """显示进度"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(int(progress * 100))
        self.status_label.setText(message)
    
    def hide_progress(self):
        """隐藏进度"""
        self.progress_bar.setVisible(False)
        self.status_label.setText("就绪")
    
    # 事件处理方法
    def new_project(self):
        """新建项目"""
        # 检查是否有未保存的内容
        if self.project_manager and self.project_manager.current_project:
            reply = QMessageBox.question(
                self, "新建项目", 
                "当前项目尚未保存，确定要新建项目吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # 显示新建项目对话框
        dialog = NewProjectDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                project_info = dialog.get_project_info()
                
                # 创建新项目
                if not self.project_manager:
                    raise Exception("项目管理器未初始化")
                project_config = self.project_manager.create_new_project(
                    project_info["name"],
                    project_info["description"]
                )
                
                # 设置当前项目名称
                self.current_project_name = project_info["name"]
                
                # 清空界面
                self.clear_all_content()
                
                # 立即保存当前内容（如果有的话）
                self.save_current_content()
                
                # 更新项目状态显示
                self.update_project_status()
                
                # 显示成功消息
                show_success(f"项目 '{project_info['name']}' 创建成功！")
                
                # 更新窗口标题
                self.setWindowTitle(f"AI 视频生成系统 - {project_info['name']}")
                
                # 更新文本框占位符
                self.update_text_placeholder()
                
                logger.info(f"新项目创建成功: {project_info['name']}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建项目失败：{e}")
                logger.error(f"创建项目失败: {e}")
    
    def clear_all_content(self, clear_project_name=True):
        """清空所有内容"""
        try:
            # 暂时禁用自动保存
            self._disable_auto_save = True
            
            # 清空当前项目名称（可选）
            if clear_project_name:
                self.current_project_name = None
            
            # 清空文本输入
            self.text_input.clear()
            self.rewritten_text.clear()
            
            # 分镜生成标签页已被五阶段分镜系统代替，无需清空
            
            # 清空图像列表
            self.image_list.clear()
            
            # 重置视频信息
            self.video_info_label.setText("暂无视频")
            
            # 清空应用控制器
            self.app_controller.clear_project()
            
            # 更新文本框占位符
            self.update_text_placeholder()
            
            # 重新启用自动保存
            self._disable_auto_save = False
            
        except Exception as e:
            logger.error(f"清空内容失败: {e}")
            self._disable_auto_save = False
    
    def open_project(self):
        """打开项目"""
        try:
            # 检查项目管理器
            if not self.project_manager:
                QMessageBox.critical(self, "错误", "项目管理器未初始化")
                return

            # 获取项目列表
            projects = self.project_manager.list_projects()
            
            # 显示打开项目对话框
            dialog = OpenProjectDialog(projects, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_project = dialog.get_selected_project()
                if selected_project:
                    try:
                        # 加载项目
                        project_config = self.project_manager.load_project(selected_project["path"])
                        
                        # 设置当前项目名称
                        project_name = project_config.get('project_name') or selected_project.get('name')
                        self.current_project_name = project_name or os.path.basename(selected_project["path"])
                        
                        # 确保项目配置包含必要字段
                        if 'project_name' not in project_config:
                            project_config['project_name'] = self.current_project_name
                        if 'project_dir' not in project_config:
                            project_config['project_dir'] = selected_project["path"]
                        if 'files' not in project_config:
                            project_config['files'] = {}
                        
                        # 验证项目数据完整性
                        self._validate_project_data(project_config)
                        
                        # 清空当前内容（但保留项目名称）
                        self.clear_all_content(clear_project_name=False)
                        
                        # 重新初始化一致性处理器（确保使用正确的项目目录）
                        self._init_consistency_processor()
                        
                        # 加载项目内容到界面
                        self.load_project_content(project_config)
                        
                        # 分阶段加载复杂组件数据
                        self._load_complex_components(project_config)
                        
                        # 更新项目状态
                        self.update_project_status()
                        
                        # 更新窗口标题
                        project_display_name = project_config.get('project_name') or project_config.get('name', '未知项目')
                        self.setWindowTitle(f"AI 视频生成系统 - {project_display_name}")
                        
                        # 更新文本框占位符
                        self.update_text_placeholder()
                        
                        # 显示成功消息
                        project_display_name = project_config.get('project_name') or project_config.get('name', '未知项目')
                        show_success(f"项目 '{project_display_name}' 加载成功！")
                        
                        # 强制刷新界面
                        self.repaint()
                        
                        project_display_name = project_config.get('project_name') or project_config.get('name', '未知项目')
                        logger.info(f"项目加载成功: {project_display_name}")
                        
                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"加载项目失败：{e}")
                        logger.error(f"加载项目失败: {e}")
                        import traceback
                        logger.error(f"详细错误信息: {traceback.format_exc()}")
                        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开项目失败：{e}")
            logger.error(f"打开项目失败: {e}")
    
    def load_project_content(self, project_config):
        """加载项目内容到界面 - 统一从project.json加载所有数据"""
        try:
            # 暂时禁用自动保存
            self._disable_auto_save = True

            logger.info("开始从project.json加载项目内容")

            # 加载原始文本 - 优先从project_config，然后从文件，最后从五阶段数据
            original_text = project_config.get("original_text", "")

            # 如果project_config中没有，尝试从文件加载
            if not original_text:
                original_text_file = project_config.get("files", {}).get("original_text", "")
                if original_text_file and os.path.exists(original_text_file):
                    try:
                        with open(original_text_file, 'r', encoding='utf-8') as f:
                            original_text = f.read().strip()
                        logger.info(f"从文件加载原始文本成功: {original_text_file}")
                    except Exception as e:
                        logger.warning(f"从文件加载原始文本失败: {e}")

            # 如果还是没有，尝试从五阶段数据加载
            if not original_text:
                five_stage_data = project_config.get("five_stage_storyboard", {}).get("stage_data", {})
                stage_1_data = five_stage_data.get("1", {})
                if stage_1_data.get("article_text"):
                    original_text = stage_1_data["article_text"]
                    logger.info("从五阶段数据加载原始文本成功")

            if original_text:
                self.text_input.setPlainText(original_text)
                logger.info(f"原始文本加载成功，长度: {len(original_text)}")
            else:
                logger.info("项目中没有找到原始文本内容")

            # 加载改写后的文本 - 优先从project_config，然后从文件
            rewritten_text = project_config.get("rewritten_text", "")

            # 如果project_config中没有，尝试从文件加载
            if not rewritten_text:
                rewritten_text_file = project_config.get("files", {}).get("rewritten_text", "")
                if rewritten_text_file and os.path.exists(rewritten_text_file):
                    try:
                        with open(rewritten_text_file, 'r', encoding='utf-8') as f:
                            rewritten_text = f.read().strip()
                        logger.info(f"从文件加载改写文本成功: {rewritten_text_file}")
                    except Exception as e:
                        logger.warning(f"从文件加载改写文本失败: {e}")

            if rewritten_text:
                self.rewritten_text.setPlainText(rewritten_text)
                logger.info(f"改写文本加载成功，长度: {len(rewritten_text)}")
            else:
                logger.info("项目中没有找到改写文本内容")

            # 加载图像数据（如果有的话）
            drawing_settings = project_config.get("drawing_settings", {})
            generated_images = drawing_settings.get("generated_images", [])
            if generated_images:
                logger.info(f"加载图像列表: {len(generated_images)} 张图片")
                for image_info in generated_images:
                    if isinstance(image_info, dict) and 'path' in image_info:
                        image_path = image_info['path']
                        if Path(image_path).exists():
                            self.add_image_to_list(image_path)
                        else:
                            logger.warning(f"图像文件不存在: {image_path}")

            # 🔧 新增：恢复文章创作界面的风格和模型选择
            self.restore_text_creation_settings_from_project(project_config)

            logger.info("项目内容加载完成")

            # 重新启用自动保存
            self._disable_auto_save = False

        except Exception as e:
            logger.error(f"加载项目内容失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            # 确保重新启用自动保存
            self._disable_auto_save = False
    
    def add_image_to_list(self, image_path):
        """添加图像到列表"""
        try:
            item = QListWidgetItem()
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # type: ignore
                item.setIcon(QIcon(scaled_pixmap))
            
            filename = Path(image_path).name
            item.setText(filename)
            item.setToolTip(str(image_path))
            self.image_list.addItem(item)
            
        except Exception as e:
            logger.error(f"添加图像到列表失败: {e}")
    
    def save_project(self):
        """保存项目"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                QMessageBox.warning(self, "警告", "没有打开的项目可以保存！")
                return
            
            # 保存当前界面内容到项目
            self.save_current_content()
            
            # 保存项目
            if self.project_manager.save_project():
                show_success("项目保存成功！")
                self.status_label.setText("项目已保存")
                logger.info("项目保存成功")
            else:
                QMessageBox.critical(self, "错误", "项目保存失败！")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存项目失败：{e}")
            logger.error(f"保存项目失败: {e}")
    
    def on_text_changed(self):
        """文本内容变化时自动保存"""
        try:
            # 检查是否禁用自动保存
            if getattr(self, '_disable_auto_save', False):
                return
            
            # 检查是否有当前项目，如果没有且有文本内容，强制创建项目
            if hasattr(self, 'project_manager'):
                text_content = self.text_input.toPlainText().strip()
                
                if not self.project_manager.current_project and text_content:
                    # 用户输入了内容但没有项目，强制创建项目
                    self.force_create_project()
                    return
                
                if self.project_manager and self.project_manager.current_project:
                    # 标记内容已修改，触发自动保存
                    self.mark_content_dirty()
                    
                    # 延迟保存，避免频繁保存
                    if hasattr(self, '_save_timer'):
                        self._save_timer.stop()
                    
                    self._save_timer = QTimer()
                    self._save_timer.setSingleShot(True)
                    self._save_timer.timeout.connect(self.auto_save_original_text)
                    self._save_timer.start(2000)  # 2秒后保存
        except Exception as e:
            logger.error(f"文本变化处理失败: {e}")
    
    def force_create_project(self):
        """强制创建项目"""
        try:
            # 暂时禁用自动保存，防止递归
            self._disable_auto_save = True
            
            # 获取当前文本内容
            current_text = self.text_input.toPlainText().strip()
            
            QMessageBox.information(
                self, 
                "需要创建项目", 
                "检测到您输入了文本内容，但还没有创建项目。\n\n请先创建一个项目来保存您的工作内容。"
            )
            
            # 显示新建项目对话框
            dialog = NewProjectDialog(self)
            dialog.setWindowTitle("创建项目 - 必需")
            
            # 循环直到用户创建项目或清空文本
            while True:
                if dialog.exec_() == QDialog.Accepted:
                    try:
                        project_info = dialog.get_project_info()
                        
                        # 创建新项目
                        project_config = self.project_manager.create_new_project(
                            project_info["name"], 
                            project_info["description"]
                        )
                        
                        # 重新启用自动保存
                        self._disable_auto_save = False
                        
                        # 保存当前文本到项目
                        if current_text:
                            self.project_manager.save_text_content(current_text, "original_text")
                        
                        # 更新项目状态显示
                        self.update_project_status()
                        
                        # 显示成功消息
                        show_success(f"项目 '{project_info['name']}' 创建成功！文本内容已保存。")
                        
                        # 更新窗口标题
                        self.setWindowTitle(f"AI 视频生成系统 - {project_info['name']}")
                        
                        # 更新文本框占位符
                        self.update_text_placeholder()
                        
                        logger.info(f"强制新项目创建成功: {project_info['name']}")
                        break
                        
                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"创建项目失败：{e}")
                        logger.error(f"强制创建项目失败: {e}")
                        # 继续循环，让用户重新尝试
                        continue
                
                else:
                    # 用户取消了，询问是否清空文本
                    reply = QMessageBox.question(
                        self, 
                        "确认操作", 
                        "您取消了项目创建。\n\n要继续工作，必须创建一个项目。\n是否清空文本内容？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        # 清空文本
                        self.text_input.clear()
                        self._disable_auto_save = False
                        logger.info("用户选择清空文本内容")
                        break
                    else:
                        # 继续要求创建项目
                        continue
            
            # 重新启用自动保存
            self._disable_auto_save = False
            
        except Exception as e:
            logger.error(f"强制创建项目过程失败: {e}")
            self._disable_auto_save = False
    
    def update_text_placeholder(self):
        """更新文本框占位符"""
        try:
            if self.project_manager and self.project_manager.current_project:
                # 兼容新旧项目格式
                project_name = self.project_manager.current_project.get("project_name") or self.project_manager.current_project.get("name", "当前项目")
                placeholder = f"项目：{project_name}\n请输入要转换为视频的文本内容..."
            else:
                placeholder = "请先创建项目，然后输入要转换为视频的文本内容..."
            
            self.text_input.setPlaceholderText(placeholder)
            
        except Exception as e:
            logger.error(f"更新文本占位符失败: {e}")
    
    def auto_save_original_text(self):
        """自动保存原始文本"""
        try:
            if self.project_manager and self.project_manager.current_project:
                original_text = self.text_input.toPlainText().strip()
                if original_text:
                    self.project_manager.save_text_content(original_text, "original_text")
                    logger.debug("原始文本已自动保存")
        except Exception as e:
            logger.error(f"自动保存原始文本失败: {e}")

    def save_text_creation_settings_to_project(self):
        """保存文章创作界面的风格和模型选择到项目"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            from src.utils.logger import logger

            # 确保text_creation数据结构存在
            if 'text_creation' not in self.project_manager.current_project:
                self.project_manager.current_project['text_creation'] = {}

            # 保存风格选择
            if hasattr(self, 'text_style_combo'):
                current_style = self.text_style_combo.currentText()
                self.project_manager.current_project['text_creation']['selected_style'] = current_style
                logger.debug(f"保存文章创作风格选择到项目: {current_style}")

            # 保存模型选择
            if hasattr(self, 'text_model_combo'):
                current_model = self.text_model_combo.currentText()
                self.project_manager.current_project['text_creation']['selected_model'] = current_model
                logger.debug(f"保存文章创作模型选择到项目: {current_model}")

        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"保存文章创作设置到项目失败: {e}")

    def save_current_content(self):
        """保存当前界面内容到项目"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return
            
            # 保存原始文本
            original_text = self.text_input.toPlainText().strip()
            if original_text:
                self.project_manager.save_text_content(original_text, "original_text")
            
            # 保存改写后的文本
            rewritten_text = self.rewritten_text.toPlainText().strip()
            if rewritten_text:
                self.project_manager.save_text_content(rewritten_text, "rewritten_text")

            # 🔧 新增：保存文章创作界面的风格和模型选择
            self.save_text_creation_settings_to_project()

            # 触发一致性面板保存预览数据
            if hasattr(self, 'consistency_panel') and self.consistency_panel:
                current_preview = self.consistency_panel.preview_text.toPlainText().strip()
                if current_preview:
                    self.consistency_panel._save_preview_data(current_preview)
            
            # 自动保存完整项目数据到project.json
            self.auto_save_project_data()
            
            logger.info("当前内容已保存到项目")
            
        except Exception as e:
            logger.error(f"保存当前内容失败: {e}")
    
    def auto_save_project_data(self):
        """自动保存完整项目数据到指定的project.json文件"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return
            
            # 从current_project开始，保留完整的项目结构
            project_data = self.project_manager.current_project.copy()
            
            # 更新基本信息
            project_data['last_modified'] = datetime.now().isoformat()
            
            # 分镜数据现在由五阶段分镜系统管理，无需单独收集
            
            # 收集五阶段分镜数据
            if hasattr(self, 'five_stage_storyboard_tab') and self.five_stage_storyboard_tab:
                try:
                    five_stage_data = self.five_stage_storyboard_tab.get_project_data()
                    if five_stage_data and 'five_stage_storyboard' in five_stage_data:
                        # 直接更新五阶段数据，避免重复键
                        project_data['five_stage_storyboard'] = five_stage_data['five_stage_storyboard']
                except Exception as e:
                    logger.warning(f"获取五阶段分镜数据失败: {e}")
            
            # 绘图设置已移至设置标签页中，不再单独收集
            
            # 收集一致性控制数据
            if hasattr(self, 'consistency_panel') and self.consistency_panel:
                try:
                    consistency_data = self.consistency_panel.get_project_data()
                    if consistency_data:
                        # 安全地合并数据，避免重复键
                        for key, value in consistency_data.items():
                            project_data[key] = value
                except Exception as e:
                    logger.warning(f"获取一致性控制数据失败: {e}")
            
            # 收集分镜图像生成数据
            if hasattr(self, 'storyboard_image_tab') and self.storyboard_image_tab:
                try:
                    image_gen_data = self.storyboard_image_tab.get_project_data()
                    if image_gen_data:
                        # 安全地合并数据，避免重复键
                        for key, value in image_gen_data.items():
                            project_data[key] = value
                except Exception as e:
                    logger.warning(f"获取分镜图像生成数据失败: {e}")
            
            # 收集AI配音生成数据
            if hasattr(self, 'voice_generation_tab') and self.voice_generation_tab:
                try:
                    voice_data = self.voice_generation_tab.get_project_data()
                    if voice_data:
                        # 安全地合并数据，避免重复键
                        for key, value in voice_data.items():
                            project_data[key] = value
                except Exception as e:
                    logger.warning(f"获取AI配音生成数据失败: {e}")

            # 收集视频生成设置
            if hasattr(self, 'video_tab') and self.video_tab:
                try:
                    video_settings = self.video_tab.get_settings()
                    if video_settings:
                        project_data['video_settings'] = video_settings
                except Exception as e:
                    logger.warning(f"获取视频生成设置失败: {e}")
            
            # 构建目标保存路径
            project_name = self.project_manager.current_project.get('project_name', '')
            if project_name:
                target_dir = f"d:\\AI_Video_Generator\\output\\{project_name}"
                os.makedirs(target_dir, exist_ok=True)
                target_file = os.path.join(target_dir, "project.json")
                
                # 保存到指定路径
                with open(target_file, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"项目数据已自动保存到: {target_file}")
            
        except Exception as e:
            logger.error(f"自动保存项目数据失败: {e}")
    
    def refresh_services(self):
        """刷新服务"""
        self.update_service_status()
        self.update_providers()
        self.status_label.setText("服务状态已刷新")

    def refresh_project_data(self):
        """刷新项目数据"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                QMessageBox.information(self, "提示", "当前没有打开的项目")
                return

            # 重新加载项目数据
            self.load_project_data()

            # 刷新各个标签页的数据
            if hasattr(self, 'five_stage_storyboard_tab'):
                self.five_stage_storyboard_tab.load_project_data()

            if hasattr(self, 'voice_generation_tab'):
                self.voice_generation_tab.load_project_data()

            # 更新状态
            self.status_label.setText("项目数据已刷新")
            show_success("项目数据刷新完成！")
            logger.info("项目数据刷新完成")

        except Exception as e:
            logger.error(f"刷新项目数据失败: {e}")
            QMessageBox.critical(self, "错误", f"刷新项目数据失败：{e}")
    
    def load_text_file(self):
        """加载文本文件"""
        # 检查是否有项目，如果没有提示创建
        if not self.project_manager or not self.project_manager.current_project:
            reply = QMessageBox.question(
                self, "需要创建项目", 
                "加载文本文件需要先创建一个项目。\n是否现在创建项目？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.new_project()
                if not self.project_manager or not self.project_manager.current_project:
                    return  # 用户取消了项目创建
            else:
                return
        
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文本文件", "", "文本文件 (*.txt *.md)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.text_input.setPlainText(content)
                
                # 自动保存到项目
                self.project_manager.save_text_content(content, "original_text")
                
                self.status_label.setText(f"文本文件已加载并保存到项目: {file_path}")
                show_success("文本文件加载成功并已保存到项目！")
                
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"无法加载文本文件:\n{e}")

    def ai_create_story(self):
        """AI创作故事"""
        from src.utils.logger import logger

        theme = self.text_input.toPlainText().strip()
        if not theme:
            QMessageBox.warning(self, "警告", "请先输入创作主题或关键词")
            return

        logger.info(f"[AI创作] 开始AI故事创作，主题: {theme}")

        # 检查是否有项目，如果没有提示创建
        if not self.project_manager or not self.project_manager.current_project:
            reply = QMessageBox.question(
                self, "需要创建项目",
                "AI创作功能需要先创建一个项目来保存结果。\n是否现在创建项目？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.new_project()
                if not self.project_manager or not self.project_manager.current_project:
                    logger.warning("[AI创作] 用户取消了项目创建，终止AI创作")
                    return  # 用户取消了项目创建
            else:
                logger.warning("[AI创作] 用户拒绝创建项目，终止AI创作")
                return

        def on_create_finished(result):
            self.rewritten_text.setPlainText(result)
            
            # 标记内容已修改，触发自动保存
            self.mark_content_dirty()

            # 自动保存创作后的文本到项目
            try:
                if self.project_manager and self.project_manager.current_project:
                    self.project_manager.save_text_content(result, "rewritten_text")
                    logger.info("AI创作的故事已自动保存到项目")
            except Exception as e:
                logger.error(f"保存创作故事失败: {e}")

            # 隐藏进度条
            self.rewrite_progress.setVisible(False)
            self.hide_progress()
            # 更新左下角状态显示
            self.status_label.setText("✅ AI故事创作完成")
            show_success("AI故事创作已完成！创作的内容已显示在下方文本框中。")

            # 同步到分镜标签页
            if hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'load_rewritten_text_from_main'):
                self.storyboard_tab.load_rewritten_text_from_main()

            # 🔧 新增：同步风格和模型选择到其他标签页
            if hasattr(self, 'text_style_combo'):
                current_style = self.text_style_combo.currentText()
                self.sync_style_to_other_tabs(current_style)
                logger.info(f"AI创作完成后同步风格: {current_style}")

            if hasattr(self, 'text_model_combo'):
                current_model = self.text_model_combo.currentText()
                self.sync_model_to_other_tabs(current_model)
                logger.info(f"AI创作完成后同步模型: {current_model}")

            # 自动跳转到五阶段分镜系统的第一阶段
            self.auto_switch_to_five_stage_storyboard()

        def on_create_error(error):
            # 隐藏进度条
            self.rewrite_progress.setVisible(False)
            self.hide_progress()
            # 更新左下角状态显示
            self.status_label.setText("❌ AI故事创作失败")
            QMessageBox.critical(self, "创作失败", f"AI故事创作失败:\n{error}")

        def on_progress(progress, message):
            # 显示和更新进度条
            self.rewrite_progress.setVisible(True)
            self.rewrite_progress.setValue(progress)
            self.rewrite_progress.setFormat(f"正在创作故事... {progress}%")
            # 更新左下角状态显示
            self.status_label.setText(f"🔄 正在创作故事...")
            self.show_progress(progress, message)

        # 显示进度条
        self.rewrite_progress.setVisible(True)
        self.rewrite_progress.setValue(0)
        self.rewrite_progress.setFormat("准备创作故事...")

        # 创建AI创作工作线程
        provider = self.storyboard_tab.rewrite_provider_combo.currentText() if hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'rewrite_provider_combo') and self.storyboard_tab.rewrite_provider_combo.currentText() != "自动选择" else None
        self.current_worker = AsyncWorker(self.app_controller.create_story_from_theme, theme, provider)
        self.current_worker.signals.finished.connect(on_create_finished)
        self.current_worker.signals.error.connect(on_create_error)
        self.current_worker.signals.progress.connect(on_progress)
        self.current_worker.start()

    def rewrite_text(self):
        """AI改写文本"""
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请先输入文本内容")
            return
        
        # 检查是否有项目，如果没有提示创建
        if not self.project_manager or not self.project_manager.current_project:
            reply = QMessageBox.question(
                self, "需要创建项目", 
                "AI改写功能需要先创建一个项目来保存结果。\n是否现在创建项目？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.new_project()
                if not self.project_manager or not self.project_manager.current_project:
                    return  # 用户取消了项目创建
            else:
                return
        
        def on_rewrite_finished(result):
            self.rewritten_text.setPlainText(result)
            
            # 标记内容已修改，触发自动保存
            self.mark_content_dirty()
            
            # 自动保存改写后的文本到项目
            try:
                if self.project_manager and self.project_manager.current_project:
                    self.project_manager.save_text_content(result, "rewritten_text")
                    logger.info("改写后的文本已自动保存到项目")
            except Exception as e:
                logger.error(f"保存改写文本失败: {e}")
            
            # 隐藏进度条
            self.rewrite_progress.setVisible(False)
            self.hide_progress()
            # 更新左下角状态显示
            self.status_label.setText("✅ 文本改写完成")
            show_success("文本改写已完成！改写后的内容已显示在下方文本框中。")
            
            # 同步到分镜标签页
            if hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'load_rewritten_text_from_main'):
                self.storyboard_tab.load_rewritten_text_from_main()

            # 🔧 新增：同步风格和模型选择到其他标签页
            if hasattr(self, 'text_style_combo'):
                current_style = self.text_style_combo.currentText()
                self.sync_style_to_other_tabs(current_style)
                logger.info(f"文本改写完成后同步风格: {current_style}")

            if hasattr(self, 'text_model_combo'):
                current_model = self.text_model_combo.currentText()
                self.sync_model_to_other_tabs(current_model)
                logger.info(f"文本改写完成后同步模型: {current_model}")

            # 自动跳转到五阶段分镜系统的第一阶段
            self.auto_switch_to_five_stage_storyboard()
        
        def on_rewrite_error(error):
            # 隐藏进度条
            self.rewrite_progress.setVisible(False)
            self.hide_progress()
            # 更新左下角状态显示
            self.status_label.setText("❌ 文本改写失败")
            QMessageBox.critical(self, "改写失败", f"文本改写失败:\n{error}")
        
        def on_progress(progress, message):
            # 显示和更新进度条
            self.rewrite_progress.setVisible(True)
            self.rewrite_progress.setValue(progress)
            self.rewrite_progress.setFormat(f"正在改写文本... {progress}%")
            # 更新左下角状态显示
            self.status_label.setText(f"🔄 正在改写文章...")
            self.show_progress(progress, message)
        
        # 显示进度条
        self.rewrite_progress.setVisible(True)
        self.rewrite_progress.setValue(0)
        self.rewrite_progress.setFormat("准备改写文本...")
        
        # 创建改写工作线程
        provider = self.storyboard_tab.rewrite_provider_combo.currentText() if hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'rewrite_provider_combo') and self.storyboard_tab.rewrite_provider_combo.currentText() != "自动选择" else None
        self.current_worker = AsyncWorker(self.app_controller.rewrite_text, text, provider)
        self.current_worker.signals.finished.connect(on_rewrite_finished)
        self.current_worker.signals.error.connect(on_rewrite_error)
        self.current_worker.signals.progress.connect(on_progress)
        self.current_worker.start()
    
    def clear_text(self):
        """清空文本"""
        self.text_input.clear()
        self.rewritten_text.clear()
    
    def quick_generate_video(self):
        """一键生成视频"""
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请先输入文本内容")
            return
        
        def on_generate_finished(result):
            self.hide_progress()
            self.video_info_label.setText(f"视频已生成: {result}")
            self.update_project_status()
            self.status_label.setText("视频生成完成")
            QMessageBox.information(self, "生成完成", f"视频已生成:\n{result}")
        
        def on_generate_error(error):
            self.hide_progress()
            QMessageBox.critical(self, "生成失败", f"视频生成失败:\n{error}")
        
        def on_progress(progress, message):
            self.show_progress(progress, message)
        
        # 准备配置
        if hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'style_combo'):
            style = self.storyboard_tab.style_combo.currentText()
        else:
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            style = config_manager.get_setting("default_style", "电影风格")
        providers = {
            "llm": self.storyboard_tab.rewrite_provider_combo.currentText() if hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'rewrite_provider_combo') and self.storyboard_tab.rewrite_provider_combo.currentText() != "自动选择" else None,
            "image": "pollinations"  # 默认使用pollinations，图像提供商配置已移至设置标签页
        }
        
        image_config = ImageGenerationConfig(
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            steps=self.steps_spin.value(),
            cfg_scale=self.cfg_scale_spin.value(),
            negative_prompt=self.negative_prompt_edit.text()
        )
        
        video_config = VideoConfig(
            fps=self.fps_spin.value(),
            duration_per_shot=self.duration_spin.value(),
            transition_type=self.transition_combo.currentText(),
            background_music=self.music_path_edit.text() if self.music_path_edit.text() else None,
            background_music_volume=self.music_volume_slider.value() / 100.0
        )
        
        # 创建生成工作线程
        self.current_worker = AsyncWorker(
            self.app_controller.create_video_from_text,
            text, style, image_config, video_config, providers, on_progress
        )
        self.current_worker.signals.finished.connect(on_generate_finished)
        self.current_worker.signals.error.connect(on_generate_error)
        self.current_worker.start()
    
    def generate_storyboard(self):
        """生成分镜"""
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请先输入文本内容")
            return

        def on_storyboard_finished(result):
            self.display_storyboard(result)
            self.hide_progress()
            self.update_project_status()
            self.status_label.setText("分镜生成完成")

        def on_storyboard_error(error):
            self.hide_progress()
            QMessageBox.critical(self, "生成失败", f"分镜生成失败:\n{error}")

        def on_progress(progress, message):
            self.show_progress(progress, message)

        # 🔧 修复：优先从文章创作界面获取风格选择，然后从分镜标签页获取，最后使用默认值
        style = None

        # 方法1：从文章创作界面的风格选择获取
        if hasattr(self, 'text_style_combo'):
            style = self.text_style_combo.currentText()
            from src.utils.logger import logger
            logger.info(f"从文章创作界面获取风格: {style}")

        # 方法2：如果文章创作界面没有风格选择，从分镜标签页获取
        if not style and hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'style_combo'):
            style = self.storyboard_tab.style_combo.currentText()
            from src.utils.logger import logger
            logger.info(f"从分镜标签页获取风格: {style}")

        # 方法3：如果都没有，使用配置中的默认风格
        if not style:
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            style = config_manager.get_setting("default_style", "电影风格")
            from src.utils.logger import logger
            logger.info(f"使用默认风格: {style}")

        # 获取大模型提供商
        provider = None
        if hasattr(self, 'text_model_combo'):
            model_text = self.text_model_combo.currentText()
            # 将中文模型名称映射到提供商名称
            model_mapping = {
                "通义千问": "qwen",
                "智谱AI": "zhipu",
                "百度文心": "baidu",
                "腾讯混元": "tencent"
            }
            provider = model_mapping.get(model_text)
            from src.utils.logger import logger
            logger.info(f"从文章创作界面获取模型: {model_text} -> {provider}")
        elif hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'rewrite_provider_combo') and self.storyboard_tab.rewrite_provider_combo.currentText() != "自动选择":
            provider = self.storyboard_tab.rewrite_provider_combo.currentText()
            from src.utils.logger import logger
            logger.info(f"从分镜标签页获取提供商: {provider}")

        self.current_worker = AsyncWorker(
            self.app_controller.generate_storyboard_only,
            text, style, provider, on_progress
        )
        self.current_worker.signals.finished.connect(on_storyboard_finished)
        self.current_worker.signals.error.connect(on_storyboard_error)
        self.current_worker.start()
    
    def display_storyboard(self, storyboard: StoryboardResult):
        """显示分镜"""
        # 通过storyboard_tab显示分镜数据
        if hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'show_shots_table'):
            # 转换数据格式以适配StoryboardTab的show_shots_table方法
            shots_data = []
            for shot in storyboard.shots:
                shots_data.append({
                    'shot_id': shot.shot_id,
                    'scene': shot.scene,
                    'characters': shot.characters,
                    'action': shot.action,
                    'dialogue': shot.dialogue,
                    'image_prompt': shot.image_prompt
                })
            self.storyboard_tab.show_shots_table(shots_data)
        else:
            logger.warning("无法显示分镜：storyboard_tab不可用")
    
    def export_storyboard(self):
        """导出分镜"""
        project_status = self.app_controller.get_project_status()
        if not project_status.get("has_storyboard"):
            QMessageBox.warning(self, "警告", "没有可导出的分镜数据")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self, "导出分镜", "", "JSON文件 (*.json);;Markdown文件 (*.md)")
        if file_path:
            try:
                if file_path.endswith('.json'):
                    format_type = "json"
                else:
                    format_type = "markdown"
                
                storyboard = self.app_controller.current_project["storyboard"]
                content = self.app_controller.text_processor.export_storyboard(storyboard, format_type)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.status_label.setText(f"分镜已导出: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"无法导出分镜:\n{e}")
    
    def generate_images(self):
        """生成图像"""
        project_status = self.app_controller.get_project_status()
        if not project_status.get("has_storyboard"):
            QMessageBox.warning(self, "警告", "请先生成分镜")
            return
        
        def on_images_finished(result):
            self.display_images(result)
            self.hide_progress()
            self.update_project_status()
            self.status_label.setText(f"图像生成完成，成功 {result.success_count} 张")
        
        def on_images_error(error):
            self.hide_progress()
            QMessageBox.critical(self, "生成失败", f"图像生成失败:\n{error}")
        
        def on_progress(progress, message):
            self.show_progress(progress, message)
        
        config = ImageGenerationConfig(
            provider="pollinations",  # 默认使用pollinations，图像提供商配置已移至设置标签页
            width=1024,
            height=1024,
            steps=20,
            cfg_scale=7.0,
            negative_prompt="blurry, low quality"
        )
        
        self.current_worker = AsyncWorker(
            self.app_controller.generate_images_only,
            None, config, on_progress
        )
        self.current_worker.signals.finished.connect(on_images_finished)
        self.current_worker.signals.error.connect(on_images_error)
        self.current_worker.start()
    
    def display_images(self, image_results: BatchImageResult):
        """显示图像"""
        self.image_list.clear()
        
        for result in image_results.results:
            if os.path.exists(result.image_path):
                item = QListWidgetItem()
                pixmap = QPixmap(result.image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # type: ignore
                    item.setIcon(QIcon(scaled_pixmap))
                item.setText(f"镜头 {result.shot_id}")
                item.setToolTip(result.prompt)
                self.image_list.addItem(item)
    
    def view_images(self):
        """查看图像"""
        project_status = self.app_controller.get_project_status()
        if not project_status.get("has_images"):
            QMessageBox.warning(self, "警告", "没有可查看的图像")
            return
        
        # 打开图像输出目录
        images_info = project_status.get("images_info", {})
        output_dir = images_info.get("output_directory")
        if output_dir and os.path.exists(output_dir):
            os.startfile(output_dir)
    
    def create_video(self):
        """创建视频"""
        project_status = self.app_controller.get_project_status()
        if not project_status.get("has_storyboard") or not project_status.get("has_images"):
            QMessageBox.warning(self, "警告", "请先生成分镜和图像")
            return
        
        def on_video_finished(result):
            self.video_info_label.setText(f"视频已生成: {result}")
            self.hide_progress()
            self.update_project_status()
            self.status_label.setText("视频创建完成")
            QMessageBox.information(self, "创建完成", f"视频已创建:\n{result}")
        
        def on_video_error(error):
            self.hide_progress()
            QMessageBox.critical(self, "创建失败", f"视频创建失败:\n{error}")
        
        def on_progress(progress, message):
            self.show_progress(progress, message)
        
        config = VideoConfig(
            fps=self.fps_spin.value(),
            duration_per_shot=self.duration_spin.value(),
            transition_type=self.transition_combo.currentText(),
            background_music=self.music_path_edit.text() if self.music_path_edit.text() else None,
            background_music_volume=self.music_volume_slider.value() / 100.0
        )
        
        self.current_worker = AsyncWorker(
            self.app_controller.create_video_only,
            None, None, config, on_progress
        )
        self.current_worker.signals.finished.connect(on_video_finished)
        self.current_worker.signals.error.connect(on_video_error)
        self.current_worker.start()
    
    def create_animated_video(self):
        """创建动画视频"""
        project_status = self.app_controller.get_project_status()
        if not project_status.get("has_images"):
            QMessageBox.warning(self, "警告", "请先生成图像")
            return
        
        def on_animated_finished(result):
            self.video_info_label.setText(f"动画视频已生成: {result}")
            self.hide_progress()
            self.status_label.setText("动画视频创建完成")
            QMessageBox.information(self, "创建完成", f"动画视频已创建:\n{result}")
        
        def on_animated_error(error):
            self.hide_progress()
            QMessageBox.critical(self, "创建失败", f"动画视频创建失败:\n{error}")
        
        def on_progress(progress, message):
            self.show_progress(progress, message)
        
        config = VideoConfig(
            fps=self.fps_spin.value(),
            duration_per_shot=self.duration_spin.value()
        )
        
        self.current_worker = AsyncWorker(
            self.app_controller.create_animated_video,
            None, "ken_burns", config, on_progress
        )
        self.current_worker.signals.finished.connect(on_animated_finished)
        self.current_worker.signals.error.connect(on_animated_error)
        self.current_worker.start()
    
    def add_subtitles(self):
        """添加字幕"""
        project_status = self.app_controller.get_project_status()
        if not project_status.get("has_final_video") or not project_status.get("has_storyboard"):
            QMessageBox.warning(self, "警告", "请先生成视频和分镜")
            return
        
        def on_subtitles_finished(result):
            self.video_info_label.setText(f"带字幕视频已生成: {result}")
            self.hide_progress()
            self.status_label.setText("字幕添加完成")
            QMessageBox.information(self, "添加完成", f"带字幕视频已生成:\n{result}")
        
        def on_subtitles_error(error):
            self.hide_progress()
            QMessageBox.critical(self, "添加失败", f"字幕添加失败:\n{error}")
        
        self.current_worker = AsyncWorker(self.app_controller.add_subtitles)
        self.current_worker.signals.finished.connect(on_subtitles_finished)
        self.current_worker.signals.error.connect(on_subtitles_error)
        self.current_worker.start()
        
        self.show_progress(0.5, "正在添加字幕...")
    
    def browse_music_file(self):
        """浏览音乐文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择音乐文件", "", "音频文件 (*.mp3 *.wav *.m4a *.aac)")
        if file_path:
            self.music_path_edit.setText(file_path)
    
    def browse_output_dir(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_edit.setText(dir_path)
    

    
    def config_apis(self):
        """配置API"""
        QMessageBox.information(self, "配置API", "API配置功能正在开发中...")
    
    def update_project_status(self):
        """更新项目状态"""
        try:
            # 检查是否有当前项目
            if not self.current_project_name:
                # 没有项目时，只更新窗口标题
                self.setWindowTitle("AI 视频生成系统")
                return

            # 获取项目管理器状态
            if not self.project_manager:
                logger.warning("项目管理器未初始化")
                return

            # 更新窗口标题显示当前项目
            if self.current_project_name:
                self.setWindowTitle(f"AI 视频生成系统 - {self.current_project_name}")
            else:
                self.setWindowTitle("AI 视频生成系统")

        except Exception as e:
            logger.error(f"更新项目状态失败: {e}")
    
    def init_theme_system(self):
        """初始化主题系统"""
        try:
            # 使用统一主题系统
            theme_system = get_theme_system()
            theme_system.apply_to_widget(self)
            
            # 设置窗口属性
            self.setAttribute(Qt.WA_StyledBackground, True)
            
            # 更新主题切换按钮
            self.update_theme_button()
            
            logger.info("主题系统初始化完成")
        except Exception as e:
            logger.error(f"主题系统初始化失败: {e}")
    
    def refresh_theme_styles(self):
        """刷新主题样式"""
        try:
            theme_system = get_theme_system()
            theme_system.apply_to_widget(self)
            
            # 强制更新所有子控件
            self.update()
            
            # 递归更新所有子控件
            for widget in self.findChildren(QWidget):
                widget.update()
                
            logger.info("主题样式已刷新")
        except Exception as e:
            logger.error(f"刷新主题样式失败: {e}")
    
    def toggle_theme(self):
        """切换主题"""
        try:
            theme_system = get_theme_system()
            current_mode = theme_system.get_current_mode()
            new_mode = ThemeMode.DARK if current_mode == ThemeMode.LIGHT else ThemeMode.LIGHT
            theme_system.set_theme_mode(new_mode)
            theme_system.apply_to_widget(self)
            show_success("主题切换成功！")
        except Exception as e:
            logger.error(f"主题切换失败: {e}")
    
    def on_theme_changed(self, theme_name: str):
        """主题变化响应"""
        try:
            # 刷新样式
            self.refresh_theme_styles()
            
            # 更新主题按钮
            self.update_theme_button()
            
            # 显示切换成功通知
            show_success(f"已切换到{theme_name}主题")
            logger.info(f"主题已切换到: {theme_name}")
        except Exception as e:
            logger.error(f"主题变化响应失败: {e}")
    
    def update_theme_button(self):
        """更新主题切换按钮"""
        try:
            theme_system = get_theme_system()
            current_mode = theme_system.get_current_mode()
            if current_mode == ThemeMode.DARK:
                self.theme_toggle_btn.setText("☀️")
                self.theme_toggle_btn.setToolTip("切换到浅色主题")
            else:
                self.theme_toggle_btn.setText("🌙")
                self.theme_toggle_btn.setToolTip("切换到深色主题")
        except Exception as e:
            # 默认状态
            self.theme_toggle_btn.setText("🌙")
            self.theme_toggle_btn.setToolTip("切换主题")
            logger.error(f"更新主题按钮失败: {e}")
    
    def process_draw_request(self, row_index: int, prompt: str):
        """处理分镜图像生成请求"""
        try:
            logger.info(f"处理第{row_index+1}行的图像生成请求")
            logger.info(f"提示词: {prompt}")

            # 使用默认配置（AI绘图功能已移至设置标签页）
            config = {
                'width': 1024,
                'height': 1024,
                'model': 'flux',
                'enhance': False,
                'nologo': True,
                'safe': True
            }

            logger.info(f"使用配置: {config}")

            # AI绘图功能已移至设置标签页，此处暂时跳过图像生成
            logger.info("AI绘图功能已移至设置标签页，请在设置页面中使用AI绘图功能")
            self.on_storyboard_image_error(row_index, "AI绘图功能已移至设置标签页")

        except Exception as e:
            logger.error(f"处理图像生成请求失败: {e}")
            QMessageBox.critical(self, "错误", f"处理图像生成请求失败: {str(e)}")

    def on_storyboard_image_generated(self, row_index: int, image_path: str):
        """分镜图像生成完成回调"""
        try:
            logger.info(f"第{row_index+1}行图像生成完成: {image_path}")

            # 更新分镜表格中的图像
            if hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'update_shot_image'):
                self.storyboard_tab.update_shot_image(row_index, image_path)

            # 隐藏进度提示
            if hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'hide_progress'):
                self.storyboard_tab.hide_progress()

            # 显示成功消息
            from .notification_system import show_success
            show_success(f"第{row_index+1}行图像生成完成！")

        except Exception as e:
            logger.error(f"处理图像生成完成回调失败: {e}")

    def on_storyboard_image_error(self, row_index: int, error: str):
        """分镜图像生成错误回调"""
        try:
            logger.error(f"第{row_index+1}行图像生成失败: {error}")

            # 隐藏进度提示
            if hasattr(self, 'storyboard_tab') and hasattr(self.storyboard_tab, 'hide_progress'):
                self.storyboard_tab.hide_progress()

            # 显示错误消息
            QMessageBox.critical(self, "图像生成失败", f"第{row_index+1}行图像生成失败:\n{error}")

        except Exception as e:
            logger.error(f"处理图像生成错误回调失败: {e}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        reply = QMessageBox.question(self, "退出", "确定要退出应用吗？")
        if reply == QMessageBox.Yes:
            # 关闭应用控制器
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.app_controller.shutdown())
                loop.close()
            except Exception as e:
                logger.error(f"关闭应用控制器失败: {e}")

            event.accept()
        else:
            event.ignore()
    
    def show_log_dialog(self):
        """显示日志对话框"""
        try:
            log_dialog = LogDialog(self)
            log_dialog.exec_()
        except Exception as e:
            logger.error(f"显示日志对话框失败: {e}")
            QMessageBox.warning(self, "错误", f"无法显示日志对话框: {e}")
    
    def clear_log(self):
        """清空日志文件"""
        reply = QMessageBox.question(
            self, "确认清空", 
            "确定要清空系统日志吗？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 获取日志文件路径
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                log_file_path = os.path.join(project_root, "logs", "system.log")
                
                if os.path.exists(log_file_path):
                    # 清空日志文件
                    with open(log_file_path, 'w', encoding='utf-8') as f:
                        f.write("")
                    
                    logger.info("系统日志已被用户清空")
                    QMessageBox.information(self, "成功", "日志已清空")
                else:
                    QMessageBox.information(self, "提示", "日志文件不存在")
                    
            except Exception as e:
                logger.error(f"清空日志失败: {e}")
                QMessageBox.warning(self, "错误", f"清空日志失败: {e}")
    
    def export_log(self):
        """导出日志文件"""
        try:
            # 获取日志文件路径
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_file_path = os.path.join(project_root, "logs", "system.log")
            
            if not os.path.exists(log_file_path):
                QMessageBox.information(self, "提示", "日志文件不存在")
                return
            
            # 选择保存位置
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出日志文件",
                f"system_log_{QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss')}.log",
                "日志文件 (*.log);;文本文件 (*.txt);;所有文件 (*.*)"
            )
            
            if save_path:
                # 复制日志文件
                import shutil
                shutil.copy2(log_file_path, save_path)
                
                logger.info(f"日志已导出到: {save_path}")
                QMessageBox.information(self, "成功", f"日志已导出到:\n{save_path}")
                
        except Exception as e:
            logger.error(f"导出日志失败: {e}")
            QMessageBox.warning(self, "错误", f"导出日志失败: {e}")
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>AI 视频生成系统</h2>
        <p><b>版本:</b> 2.0</p>
        <p><b>描述:</b> 基于AI技术的智能视频生成系统</p>
        <p><b>功能特性:</b></p>
        <ul>
            <li>智能文本处理与改写</li>
            <li>自动分镜生成</li>
            <li>AI图像生成</li>
            <li>视频合成与处理</li>
            <li>项目管理</li>
            <li>日志管理</li>
        </ul>
        <p><b>技术栈:</b> Python, PyQt5, ComfyUI, 大语言模型</p>
        """
        
        QMessageBox.about(self, "关于 AI 视频生成系统", about_text)
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
        <h2>使用帮助</h2>
        
        <h3>快速开始:</h3>
        <ol>
            <li>点击"新建项目"创建一个新项目</li>
            <li>在"文本处理"标签页输入要转换的文本</li>
            <li>使用"分镜生成"功能生成分镜脚本</li>
            <li>在"图像生成"标签页生成对应图像</li>
            <li>最后在"视频生成"标签页合成视频</li>
        </ol>
        
        <h3>快捷键:</h3>
        <ul>
            <li><b>Ctrl+N:</b> 新建项目</li>
            <li><b>Ctrl+O:</b> 打开项目</li>
            <li><b>Ctrl+S:</b> 保存项目</li>
            <li><b>Ctrl+T:</b> 切换主题</li>
            <li><b>Ctrl+Q:</b> 退出程序</li>
            <li><b>F1:</b> 显示帮助</li>
        </ul>
        
        <h3>日志管理:</h3>
        <p>通过"工具" -> "日志管理"菜单可以:</p>
        <ul>
            <li>查看系统运行日志</li>
            <li>清空历史日志</li>
            <li>导出日志文件</li>
        </ul>
        """
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("使用帮助")
        msg_box.setText(help_text)
        msg_box.setTextFormat(Qt.RichText)  # type: ignore
        msg_box.exec_()
    
    def _validate_project_data(self, project_config):
        """验证项目数据完整性"""
        try:
            # 检查必要的项目字段
            required_fields = ['name', 'project_dir', 'files']
            for field in required_fields:
                if field not in project_config:
                    logger.warning(f"项目配置缺少必要字段: {field}")
                    if field == 'name':
                        project_config['name'] = '未命名项目'
                    elif field == 'project_dir':
                        project_config['project_dir'] = ''
                    elif field == 'files':
                        project_config['files'] = {}
            
            # 验证项目目录是否存在
            project_dir = Path(project_config.get('project_dir', ''))
            if not project_dir.exists():
                raise FileNotFoundError(f"项目目录不存在: {project_dir}")
            
            # 验证文件路径
            files = project_config.get('files', {})
            for file_type, file_path in files.items():
                if file_type == 'images' and isinstance(file_path, list):
                    # 验证图像文件列表
                    valid_images = []
                    for img_path in file_path:
                        if Path(img_path).exists():
                            valid_images.append(img_path)
                        else:
                            logger.warning(f"图像文件不存在: {img_path}")
                    files['images'] = valid_images
                elif file_path and not isinstance(file_path, list):
                    # 验证单个文件
                    if not Path(file_path).exists():
                        logger.warning(f"文件不存在: {file_path}")
                        files[file_type] = None
            
            logger.info("项目数据验证完成")
            
        except Exception as e:
            logger.error(f"项目数据验证失败: {e}")
            raise
    
    def _load_complex_components(self, project_config):
        """分阶段加载复杂组件数据"""
        try:
            # 第一阶段：加载五阶段分镜数据
            if hasattr(self, 'five_stage_storyboard_tab') and self.five_stage_storyboard_tab:
                logger.info("开始加载五阶段分镜数据...")
                # 使用多次延迟确保UI完全初始化
                QTimer.singleShot(100, lambda: self._load_five_stage_data(project_config))

            # 第二阶段：更新分镜图像生成标签页
            if hasattr(self, 'storyboard_image_tab') and self.storyboard_image_tab:
                logger.info("开始更新分镜图像生成标签页...")
                QTimer.singleShot(200, self._update_storyboard_image_tab)

            # 第三阶段：更新AI配音生成标签页
            if hasattr(self, 'voice_generation_tab') and self.voice_generation_tab:
                logger.info("开始更新AI配音生成标签页...")
                QTimer.singleShot(250, self._update_voice_generation_tab)

            # 第四阶段：更新一致性控制面板
            QTimer.singleShot(300, self._update_consistency_after_load)

            # 第五阶段：验证数据完整性
            QTimer.singleShot(500, self._verify_load_completion)

        except Exception as e:
            logger.error(f"加载复杂组件数据失败: {e}")
    
    def _load_five_stage_data(self, project_config):
        """加载五阶段分镜数据"""
        try:
            if hasattr(self, 'five_stage_storyboard_tab') and self.five_stage_storyboard_tab:
                # 检查项目中是否有五阶段数据
                if 'five_stage_storyboard' in project_config:
                    logger.info("发现五阶段分镜数据，开始加载...")
                    self.five_stage_storyboard_tab.delayed_load_from_project()
                else:
                    logger.info("项目中没有五阶段分镜数据")
        except Exception as e:
            logger.error(f"加载五阶段分镜数据失败: {e}")

    def _update_storyboard_image_tab(self):
        """更新分镜图像生成标签页"""
        try:
            if hasattr(self, 'storyboard_image_tab') and self.storyboard_image_tab:
                logger.info("开始更新分镜图像生成标签页...")
                # 重新加载分镜数据
                self.storyboard_image_tab.load_storyboard_data()
                # 加载生成设置
                self.storyboard_image_tab.load_generation_settings()
                logger.info("分镜图像生成标签页更新完成")
        except Exception as e:
            logger.error(f"更新分镜图像生成标签页失败: {e}")

    def _update_voice_generation_tab(self):
        """更新AI配音生成标签页"""
        try:
            if hasattr(self, 'voice_generation_tab') and self.voice_generation_tab:
                logger.info("开始更新AI配音生成标签页...")
                # 重新加载项目数据
                self.voice_generation_tab.load_project_data()
                logger.info("AI配音生成标签页更新完成")
        except Exception as e:
            logger.error(f"更新AI配音生成标签页失败: {e}")

    def _update_consistency_after_load(self):
        """项目加载后更新一致性控制面板"""
        try:
            # 确保一致性处理器已正确初始化
            if hasattr(self, 'consistency_panel') and self.consistency_panel:
                # 强制重新加载角色场景数据（不检查cs_manager状态）
                self.consistency_panel.load_character_scene_data()
                
                # 如果有五阶段数据，传递给一致性面板（项目加载时禁用自动增强）
                if hasattr(self, 'five_stage_storyboard_tab') and self.five_stage_storyboard_tab:
                    # 项目加载时不自动进行场景描述增强，避免重复处理
                    if hasattr(self.five_stage_storyboard_tab, '_update_consistency_panel'):
                        # 检查方法是否支持auto_enhance参数
                        import inspect
                        sig = inspect.signature(self.five_stage_storyboard_tab._update_consistency_panel)
                        if 'auto_enhance' in sig.parameters:
                            self.five_stage_storyboard_tab._update_consistency_panel(auto_enhance=False)
                        else:
                            self.five_stage_storyboard_tab._update_consistency_panel()
                    else:
                        logger.warning("五阶段分镜标签页缺少_update_consistency_panel方法")
                
                logger.info("一致性控制面板数据更新完成")
                
            # 更新分镜图像生成标签页数据
            if hasattr(self, 'storyboard_image_tab') and self.storyboard_image_tab:
                try:
                    self.storyboard_image_tab.load_storyboard_data()
                    logger.info("分镜图像生成标签页数据更新完成")
                except Exception as e:
                    logger.error(f"更新分镜图像生成标签页失败: {e}")
                    
        except Exception as e:
            logger.error(f"更新一致性控制面板失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _verify_load_completion(self):
        """验证项目加载完成情况"""
        try:
            # 兼容新旧项目格式
            project_name = self.project_manager.current_project.get('project_name') or self.project_manager.current_project.get('name', 'Unknown')
            
            # 检查各组件加载状态
            load_status = {
                '文本内容': bool(self.text_input.toPlainText()),
                '改写文本': bool(self.rewritten_text.toPlainText()),
                '五阶段数据': False,
                '一致性面板': False,
                '分镜图像生成': False,
                'AI配音生成': False
            }
            
            # 检查五阶段数据
            if hasattr(self, 'five_stage_storyboard_tab') and self.five_stage_storyboard_tab:
                if hasattr(self.five_stage_storyboard_tab, 'stage_data') and self.five_stage_storyboard_tab.stage_data:
                    load_status['五阶段数据'] = any(self.five_stage_storyboard_tab.stage_data.values())
            
            # 检查一致性面板
            if hasattr(self, 'consistency_panel') and self.consistency_panel:
                if hasattr(self.consistency_panel, 'cs_manager') and self.consistency_panel.cs_manager:
                    characters = self.consistency_panel.cs_manager.get_all_characters()
                    scenes = self.consistency_panel.cs_manager.get_all_scenes()
                    load_status['一致性面板'] = len(characters) > 0 or len(scenes) > 0
            
            # 检查分镜图像生成标签页
            if hasattr(self, 'storyboard_image_tab') and self.storyboard_image_tab:
                if hasattr(self.storyboard_image_tab, 'storyboard_data') and self.storyboard_image_tab.storyboard_data:
                    load_status['分镜图像生成'] = len(self.storyboard_image_tab.storyboard_data) > 0

            # 检查AI配音生成标签页
            if hasattr(self, 'voice_generation_tab') and self.voice_generation_tab:
                if hasattr(self.voice_generation_tab, 'voice_segments') and self.voice_generation_tab.voice_segments:
                    load_status['AI配音生成'] = len(self.voice_generation_tab.voice_segments) > 0
            
            # 记录加载状态
            logger.info(f"项目 '{project_name}' 加载状态: {load_status}")
            
            # 统计成功加载的组件
            loaded_count = sum(1 for status in load_status.values() if status)
            total_count = len(load_status)
            
            if loaded_count == total_count:
                logger.info(f"项目 '{project_name}' 所有组件加载完成")
            else:
                logger.warning(f"项目 '{project_name}' 部分组件未加载: {loaded_count}/{total_count}")
                
        except Exception as e:
            logger.error(f"验证项目加载完成情况失败: {e}")
    
    def _init_consistency_processor(self):
        """初始化一致性增强图像处理器"""
        try:
            from src.utils.character_scene_manager import CharacterSceneManager
            
            # 获取当前项目目录
            project_dir = None
            if self.project_manager and self.project_manager.current_project:
                project_dir = self.project_manager.current_project.get("project_dir")
            
            if project_dir:
                # 使用项目管理器获取角色场景管理器
                character_scene_manager = self.project_manager.get_character_scene_manager(self.app_controller.service_manager)
                
                if character_scene_manager:
                    # 初始化一致性增强图像处理器
                    self.consistency_image_processor = ConsistencyEnhancedImageProcessor(
                        self.app_controller.service_manager,
                        character_scene_manager
                    )
                    
                    # 如果一致性控制面板已经创建，更新其处理器和管理器引用
                    if hasattr(self, 'consistency_panel') and self.consistency_panel:
                        self.consistency_panel.image_processor = self.consistency_image_processor
                        self.consistency_panel.cs_manager = character_scene_manager
                        logger.info("一致性控制面板引用已更新")
                    
                    logger.info("一致性增强图像处理器初始化完成")
                else:
                    logger.warning("无法获取角色场景管理器，跳过一致性增强图像处理器初始化")
            else:
                # 没有项目时，不创建角色场景管理器，避免在output目录生成文件
                self.consistency_image_processor = None
                if hasattr(self, 'consistency_panel') and self.consistency_panel:
                    self.consistency_panel.image_processor = None
                    self.consistency_panel.cs_manager = None
                logger.info("未加载项目，跳过一致性增强图像处理器初始化")
            
        except Exception as e:
            logger.error(f"初始化一致性增强图像处理器失败: {e}")
            # 创建一个空的处理器作为备用
            self.consistency_image_processor = None

# 移除main函数，避免与主程序冲突
# def main():
#     """主函数"""
#     app = QApplication(sys.argv)
#     
#     # 设置应用信息
#     app.setApplicationName("AI视频生成系统")
#     app.setApplicationVersion("2.0")
#     app.setOrganizationName("AI Video Generator")
#     
#     # 创建主窗口
#     window = NewMainWindow()
#     window.show()
#     
#     # 运行应用
#     sys.exit(app.exec_())

# 移除独立的应用程序入口点，避免与主程序冲突
# if __name__ == "__main__":
#     main()