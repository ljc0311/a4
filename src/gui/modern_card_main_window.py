#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化卡片式主窗口
基于用户提供的界面设计，采用左侧导航、中央卡片区域、右侧信息面板的布局
"""

import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QSplitter, QProgressBar,
    QApplication, QStackedWidget, QListWidget, QListWidgetItem, QMessageBox, QDialog,
    QProgressDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QPixmap

from src.utils.logger import logger
from src.core.app_controller import AppController
# from src.core.project_manager import ProjectManager  # 不再直接使用，通过app_controller获取
from src.utils.project_manager import StoryboardProjectManager
from .modern_card_styles import apply_modern_card_styles

# 导入服务管理器和新的异步执行器
from src.core.service_manager import ServiceManager, ServiceType
from src.utils.async_runner import async_runner
from src.utils.ui_utils import show_success

# 导入现有的功能标签页
from .five_stage_storyboard_tab import FiveStageStoryboardTab
from .voice_generation_tab import VoiceGenerationTab
from .storyboard_image_generation_tab import StoryboardImageGenerationTab
from .video_generation_tab import VideoGenerationTab
from .video_composition_tab import VideoCompositionTab
from .settings_tab import SettingsTab
from .consistency_control_panel import ConsistencyControlPanel
from .info_panel import InfoPanel


class ModernCardButton(QPushButton):
    """现代化卡片式按钮"""
    
    def __init__(self, text, icon_text="", parent=None):
        super().__init__(parent)
        self.setText(text)
        self.icon_text = icon_text
        self.setup_style()
    
    def setup_style(self):
        """设置按钮样式"""
        self.setMinimumHeight(50)
        self.setMinimumWidth(160)
        self.setFont(QFont("Microsoft YaHei UI", 10, QFont.Medium))

        # 设置样式类
        self.setProperty("class", "modern-card-button")
        self.setCheckable(True)


class ModernCard(QFrame):
    """现代化卡片容器"""
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.title = title
        self.setup_ui()
        self.setup_style()
    
    def setup_ui(self):
        """设置UI"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 16, 20, 20)
        self.layout.setSpacing(12)
        
        # 标题
        if self.title:
            self.title_label = QLabel(self.title)
            self.title_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
            self.title_label.setStyleSheet("color: #333333; margin-bottom: 8px;")
            self.layout.addWidget(self.title_label)
    
    def setup_style(self):
        """设置卡片样式"""
        self.setProperty("class", "modern-card")
    
    def add_widget(self, widget):
        """添加控件到卡片"""
        self.layout.addWidget(widget)
    
    def add_layout(self, layout):
        """添加布局到卡片"""
        self.layout.addLayout(layout)


class StatusCard(ModernCard):
    """状态显示卡片"""
    
    def __init__(self, parent=None):
        super().__init__("系统状态", parent)
        self.setup_status_ui()
    
    def setup_status_ui(self):
        """设置状态UI"""
        # GPU状态
        gpu_layout = QHBoxLayout()
        gpu_label = QLabel("GPU:")
        gpu_label.setProperty("class", "status-label")
        gpu_status = QLabel("●")
        gpu_status.setProperty("class", "status-indicator")
        gpu_status.setStyleSheet("color: #4CAF50;")
        gpu_layout.addWidget(gpu_label)
        gpu_layout.addWidget(gpu_status)
        gpu_layout.addStretch()
        self.add_layout(gpu_layout)

        # 内存状态
        memory_layout = QHBoxLayout()
        memory_label = QLabel("内存:")
        memory_label.setProperty("class", "status-label")
        memory_status = QLabel("●")
        memory_status.setProperty("class", "status-indicator")
        memory_status.setStyleSheet("color: #FF9800;")
        memory_layout.addWidget(memory_label)
        memory_layout.addWidget(memory_status)
        memory_layout.addStretch()
        self.add_layout(memory_layout)

        # 网络状态
        network_layout = QHBoxLayout()
        network_label = QLabel("网络:")
        network_label.setProperty("class", "status-label")
        network_status = QLabel("●")
        network_status.setProperty("class", "status-indicator")
        network_status.setStyleSheet("color: #4CAF50;")
        network_layout.addWidget(network_label)
        network_layout.addWidget(network_status)
        network_layout.addStretch()
        self.add_layout(network_layout)


class ProgressCard(ModernCard):
    """进度显示卡片"""
    
    def __init__(self, parent=None):
        super().__init__("量化进度", parent)
        self.setup_progress_ui()
    
    def setup_progress_ui(self):
        """设置进度UI"""
        progress_items = [
            ("分镜脚本", 85),
            ("图像生成", 60),
            ("音频合成", 30),
            ("视频制作", 10)
        ]
        
        for name, value in progress_items:
            # 进度项布局
            item_layout = QVBoxLayout()
            
            # 标签和百分比
            label_layout = QHBoxLayout()
            name_label = QLabel(name)
            name_label.setProperty("class", "progress-name")
            name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333333;")

            value_label = QLabel(f"{value}%")
            value_label.setProperty("class", "progress-value")
            value_label.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: #2196F3;
                background-color: #E3F2FD;
                padding: 4px 8px;
                border-radius: 4px;
                min-width: 50px;
                text-align: center;
            """)
            value_label.setAlignment(Qt.AlignCenter)

            label_layout.addWidget(name_label)
            label_layout.addStretch()
            label_layout.addWidget(value_label)

            # 进度条
            progress_bar = QProgressBar()
            progress_bar.setValue(value)
            progress_bar.setMaximumHeight(8)
            progress_bar.setProperty("class", "modern-progress")
            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                    background-color: #F5F5F5;
                    text-align: center;
                    font-size: 12px;
                    font-weight: bold;
                    color: #333333;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                              stop: 0 #42a5f5, stop: 1 #1976d2);
                    border-radius: 3px;
                }
            """)
            
            item_layout.addLayout(label_layout)
            item_layout.addWidget(progress_bar)
            item_layout.addSpacing(8)
            
            self.add_layout(item_layout)


class ModernCardMainWindow(QMainWindow):
    """现代化卡片式主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化控制器
        self.app_controller = AppController()

        # 使用应用控制器的项目管理器实例（确保一致性）
        self.project_manager = self.app_controller.project_manager

        # 获取全局服务管理器
        try:
            logger.info("获取全局服务管理器...")
            self.service_manager = ServiceManager()
        except Exception as e:
            logger.error(f"获取服务管理器失败: {e}", exc_info=True)
            self.service_manager = None

        # 初始化分镜项目管理器（用于五阶段分镜功能）
        self.storyboard_project_manager = StoryboardProjectManager("config")

        # 用于跟踪异步AI任务
        self.active_ai_tasks = {}

        # 跟踪当前活跃的项目名称
        self.current_active_project = None
        
        # 当前选中的页面
        self.current_page = None

        # 初始化显示设置
        self.init_display_settings()

        # 设置窗口
        self.setup_window()
        self.setup_ui()
        self.setup_connections()
        
        # 默认选中第一个页面
        self.switch_to_page("workflow")
        
        logger.info("现代化卡片式主窗口初始化完成")
    
    def setup_window(self):
        """设置窗口属性"""
        self.setWindowTitle("🎬 AI视频生成器 - 现代化界面")
        self.setMinimumSize(1400, 900)
        
        # 居中显示
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
        
        # 应用现代化样式
        apply_modern_card_styles(self)

    def setup_ui(self):
        """设置用户界面"""
        # 创建中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局 - 水平分割器
        main_splitter = QSplitter(Qt.Horizontal)
        central_layout = QHBoxLayout(central_widget)
        central_layout.setContentsMargins(12, 12, 12, 12)
        central_layout.addWidget(main_splitter)

        # 左侧导航栏
        self.setup_sidebar(main_splitter)

        # 中央内容区域
        self.setup_content_area(main_splitter)

        # 右侧信息面板
        self.setup_info_panel(main_splitter)

        # 设置分割器比例 (导航:内容:信息 = 1:3:1)
        main_splitter.setSizes([200, 800, 300])
        main_splitter.setCollapsible(0, False)  # 导航栏不可折叠
        main_splitter.setCollapsible(2, True)   # 信息面板可折叠

    def setup_sidebar(self, parent_splitter):
        """设置左侧导航栏"""
        sidebar_widget = QWidget()
        sidebar_widget.setMaximumWidth(220)
        sidebar_widget.setMinimumWidth(180)

        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(8, 16, 8, 16)
        sidebar_layout.setSpacing(12)

        # 导航标题
        nav_title = QLabel("🎬 导航菜单")
        nav_title.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        nav_title.setProperty("class", "nav-title")
        nav_title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(nav_title)

        # 导航按钮
        self.nav_buttons = {}
        nav_items = [
            ("workflow", "🎭 工作流程"),
            ("text_creation", "📝 文章创作"),
            ("storyboard", "🎬 分镜脚本"),
            ("voice", "🎵 配音制作"),
            ("image", "🖼️ 图像生成"),
            ("video", "🎞️ 图转视频"),
            ("composition", "🎬 视频合成"),
            ("consistency", "🎨 一致性控制"),
            ("project", "📁 项目管理"),
            ("settings", "⚙️ 系统设置")
        ]

        for page_id, text in nav_items:
            btn = ModernCardButton(text)
            btn.clicked.connect(lambda checked, pid=page_id: self.switch_to_page(pid))
            self.nav_buttons[page_id] = btn
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # 切换主题按钮
        theme_btn = ModernCardButton("🌙 切换主题")
        theme_btn.clicked.connect(self.toggle_theme)
        sidebar_layout.addWidget(theme_btn)

        parent_splitter.addWidget(sidebar_widget)

    def setup_content_area(self, parent_splitter):
        """设置中央内容区域"""
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(12)

        # 顶部工具栏卡片
        self.setup_toolbar_card(content_layout)

        # 主要内容区域 - 使用堆叠控件
        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack)

        # 创建各个页面
        self.create_pages()

        parent_splitter.addWidget(content_widget)

    def setup_toolbar_card(self, parent_layout):
        """设置顶部工具栏卡片"""
        # 🔧 修复：创建无标题的卡片，避免占用额外行高
        toolbar_card = ModernCard("")  # 不使用标题，节省空间
        # 🔧 修复：调整项目工作台卡片的高度和边距
        toolbar_card.layout.setContentsMargins(16, 12, 16, 12)  # 增加上下边距确保文字显示完整
        toolbar_card.layout.setSpacing(0)  # 设置为0，因为只有一行内容
        toolbar_card.setMinimumHeight(60)  # 🔧 修复：设置最小高度确保内容显示完整
        toolbar_card.setMaximumHeight(70)  # 🔧 修复：增加最大高度到70像素

        # 🔧 修复：创建单行布局，标题和按钮在同一行
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(12)  # 设置元素间距
        toolbar_layout.setContentsMargins(0, 0, 0, 0)  # 确保布局边距为0

        # 🔧 修复：添加标题标签到水平布局的左侧
        title_label = QLabel("🎯 项目工作台")
        title_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))  # 稍微增大字体
        title_label.setStyleSheet("color: #333333; padding: 0px;")  # 移除margin，使用padding
        title_label.setMinimumWidth(140)  # 增加最小宽度确保标题显示完整
        title_label.setMinimumHeight(36)  # 🔧 修复：设置与按钮相同的高度
        title_label.setMaximumHeight(36)  # 🔧 修复：限制最大高度确保对齐
        toolbar_layout.addWidget(title_label)

        # 项目操作按钮
        project_buttons = [
            ("新建项目", "toolbar-button-green", self.new_project),
            ("打开项目", "toolbar-button-blue", self.open_project),
            ("保存项目", "toolbar-button-orange", self.save_project),
            ("刷新", "toolbar-button-purple", self.refresh_project)
        ]

        for text, style_class, handler in project_buttons:
            btn = QPushButton(text)
            btn.setMinimumHeight(36)  # 🔧 修复：设置合适的按钮高度
            btn.setMaximumHeight(36)  # 🔧 修复：限制最大高度确保对齐
            btn.setMinimumWidth(80)   # 🔧 修复：设置最小宽度确保按钮大小一致
            btn.setFont(QFont("Microsoft YaHei UI", 9, QFont.Medium))
            btn.setProperty("class", f"toolbar-button {style_class}")
            btn.clicked.connect(handler)
            toolbar_layout.addWidget(btn)

        toolbar_layout.addStretch()

        # 版本信息
        version_label = QLabel("v2.0.0")
        version_label.setFont(QFont("Microsoft YaHei UI", 8))
        version_label.setProperty("class", "version-label")
        toolbar_layout.addWidget(version_label)

        toolbar_card.add_layout(toolbar_layout)
        parent_layout.addWidget(toolbar_card)

    def setup_info_panel(self, parent_splitter):
        """设置右侧信息面板"""
        # 创建信息面板组件
        self.info_panel = InfoPanel(self)
        self.info_panel.set_project_manager(self.project_manager)

        # 添加到分割器
        parent_splitter.addWidget(self.info_panel)

        # 存储分割器引用以便控制显示/隐藏
        self.main_splitter = parent_splitter

    def create_pages(self):
        """创建各个功能页面"""
        self.pages = {}

        # 工作流程页面
        self.pages["workflow"] = self.create_workflow_page()
        self.content_stack.addWidget(self.pages["workflow"])

        # 文本创作页面
        self.pages["text_creation"] = self.create_text_creation_page()
        self.content_stack.addWidget(self.pages["text_creation"])

        # 项目管理页面
        self.pages["project"] = self.create_project_page()
        self.content_stack.addWidget(self.pages["project"])

        # 分镜脚本页面
        self.pages["storyboard"] = FiveStageStoryboardTab(self)
        self.content_stack.addWidget(self.pages["storyboard"])

        # 图像生成页面
        self.pages["image"] = StoryboardImageGenerationTab(self.app_controller, self.project_manager, self)
        self.content_stack.addWidget(self.pages["image"])

        # 配音制作页面
        self.pages["voice"] = VoiceGenerationTab(self.app_controller, self.project_manager, self)
        self.content_stack.addWidget(self.pages["voice"])

        # 图转视频页面
        self.pages["video"] = VideoGenerationTab(self.app_controller, self.project_manager, self)
        self.content_stack.addWidget(self.pages["video"])

        # 视频合成页面 - 恢复完整功能版本
        try:
            self.pages["composition"] = VideoCompositionTab(self.project_manager)
            self.content_stack.addWidget(self.pages["composition"])
            logger.info("完整版视频合成页面创建成功")
        except Exception as e:
            logger.error(f"视频合成页面创建失败: {e}")
            # 如果创建失败，使用简化版作为备用
            try:
                from src.gui.simple_video_composition_tab import SimpleVideoCompositionTab
                self.pages["composition"] = SimpleVideoCompositionTab(self.project_manager)
                self.content_stack.addWidget(self.pages["composition"])
                logger.info("使用简化版视频合成页面作为备用")
            except Exception as e2:
                logger.error(f"简化版视频合成页面也创建失败: {e2}")
                # 最后的备用方案
                placeholder_widget = QWidget()
                placeholder_layout = QVBoxLayout(placeholder_widget)
                placeholder_label = QLabel(f"🎬 视频合成功能暂时不可用\n错误: {e}")
                placeholder_label.setAlignment(Qt.AlignCenter)
                placeholder_layout.addWidget(placeholder_label)
                self.pages["composition"] = placeholder_widget
                self.content_stack.addWidget(self.pages["composition"])

        # 一致性控制页面
        self.pages["consistency"] = ConsistencyControlPanel(None, self.project_manager, self)
        self.content_stack.addWidget(self.pages["consistency"])

        # 系统设置页面
        self.pages["settings"] = SettingsTab(self)
        self.content_stack.addWidget(self.pages["settings"])

    def create_workflow_page(self):
        """创建工作流程页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 当前项目卡片
        current_project_card = ModernCard("📋 当前项目")

        # 项目信息
        project_info_layout = QVBoxLayout()
        project_name_label = QLabel("我的AI视频项目")
        project_name_label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        project_name_label.setStyleSheet("color: #333333;")

        project_desc_label = QLabel("这是一个使用AI技术生成的视频项目，包含智能分镜、自动配音等功能。")
        project_desc_label.setFont(QFont("Microsoft YaHei UI", 9))
        project_desc_label.setStyleSheet("color: #666666; line-height: 1.4;")
        project_desc_label.setWordWrap(True)

        project_info_layout.addWidget(project_name_label)
        project_info_layout.addWidget(project_desc_label)
        current_project_card.add_layout(project_info_layout)

        layout.addWidget(current_project_card)

        # 快捷操作卡片
        quick_actions_card = ModernCard("⚡ 快捷操作")
        actions_grid = QGridLayout()

        quick_actions = [
            ("📝 文本创作", "text_creation"),
            ("🎬 生成分镜", "storyboard"),
            ("🎵 合成配音", "voice"),
            ("🖼️ 创建图像", "image"),
            ("🎞️ 图转视频", "video"),
            ("🎬 视频合成", "composition")
        ]

        for i, (text, page_id) in enumerate(quick_actions):
            btn = QPushButton(text)
            btn.setMinimumHeight(60)
            btn.setFont(QFont("Microsoft YaHei UI", 10, QFont.Medium))
            btn.setProperty("class", "quick-action-button")
            btn.clicked.connect(lambda checked, pid=page_id: self.switch_to_page(pid))
            actions_grid.addWidget(btn, i // 2, i % 2)

        quick_actions_card.add_layout(actions_grid)
        layout.addWidget(quick_actions_card)

        layout.addStretch()
        return page

    def create_text_creation_page(self):
        """创建美观的文章创作页面"""
        from PyQt5.QtWidgets import QGroupBox, QTextEdit, QComboBox, QHBoxLayout, QFormLayout, QSizePolicy
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QFont, QIcon

        page = QWidget()
        page.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #f8f9fa, stop: 1 #e9ecef);
                font-family: "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif;
            }
        """)

        # 主滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #f1f3f4;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #c1c8cd;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a8b1ba;
            }
        """)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 15, 20, 15)  # 减小边距
        layout.setSpacing(12)  # 大幅减小间距

        # 页面标题 - 大幅缩小尺寸
        title_widget = QWidget()
        title_widget.setMaximumHeight(35)  # 进一步限制最大高度
        title_widget.setMinimumHeight(35)  # 固定高度
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)  # 减小间距

        title_label = QLabel("✨ 智能文章创作工坊")
        title_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))  # 进一步减小到12
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                background: transparent;
                padding: 2px 0;
                margin: 0;
            }
        """)

        subtitle_label = QLabel("让AI助力您的创作灵感")
        subtitle_label.setFont(QFont("Microsoft YaHei UI", 9))  # 进一步减小到9
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                background: transparent;
                margin: 0;
                padding: 0;
            }
        """)

        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        title_layout.addStretch()
        layout.addWidget(title_widget)

        # 创作配置卡片
        config_card = self.create_beautiful_card("🎨 创作配置", "#e74c3c")
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(15, 12, 15, 12)  # 减小内边距
        config_layout.setSpacing(8)  # 减小间距

        # 创作配置行 - 风格选择和模型选择
        config_row = QWidget()
        config_row_layout = QHBoxLayout(config_row)
        config_row_layout.setContentsMargins(0, 0, 0, 0)
        config_row_layout.setSpacing(15)  # 减小间距

        # 风格选择部分
        style_section = QWidget()
        style_section_layout = QHBoxLayout(style_section)
        style_section_layout.setContentsMargins(0, 0, 0, 0)

        style_label = QLabel("创作风格")
        style_label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Medium))
        style_label.setStyleSheet("color: #2c3e50; min-width: 80px;")

        self.style_combo = QComboBox()
        self.style_combo.addItems([
            "🎬 电影风格", "🎌 动漫风格", "🌸 吉卜力风格", "🌃 赛博朋克风格",
            "🎨 水彩插画风格", "🎮 像素风格", "📸 写实摄影风格"
        ])
        self.style_combo.setMinimumHeight(40)

        style_section_layout.addWidget(style_label)
        style_section_layout.addWidget(self.style_combo, 1)

        # 大模型选择部分
        model_section = QWidget()
        model_section_layout = QHBoxLayout(model_section)
        model_section_layout.setContentsMargins(0, 0, 0, 0)

        model_label = QLabel("AI模型")
        model_label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Medium))
        model_label.setStyleSheet("color: #2c3e50; min-width: 80px;")

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "🤖 通义千问", "🧠 智谱AI", "🚀 Deepseek", "🌟 Google Gemini",
            "⚡ OpenAI", "🔥 SiliconFlow"
        ])
        self.model_combo.setMinimumHeight(40)
        # 通用下拉框样式
        combo_style = """
            QComboBox {
                padding: 8px 15px;
                border: 2px solid #ecf0f1;
                border-radius: 8px;
                background: white;
                font-size: 13px;
                color: #2c3e50;
                selection-background-color: #3498db;
            }
            QComboBox:hover {
                border-color: #3498db;
                background: #f8f9fa;
            }
            QComboBox:focus {
                border-color: #2980b9;
                background: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #7f8c8d;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #ecf0f1;
                border-radius: 8px;
                background: white;
                selection-background-color: #e8f4fd;
                outline: none;
            }
        """

        self.style_combo.setStyleSheet(combo_style)
        self.model_combo.setStyleSheet(combo_style)

        model_section_layout.addWidget(model_label)
        model_section_layout.addWidget(self.model_combo, 1)

        # 将两个部分添加到配置行
        config_row_layout.addWidget(style_section, 1)
        config_row_layout.addWidget(model_section, 1)
        config_layout.addWidget(config_row)

        config_card.add_layout(config_layout)
        layout.addWidget(config_card)

        # 文本输入卡片
        input_card = self.create_beautiful_card("📝 文本输入", "#3498db")
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(15, 12, 15, 15)  # 减小内边距
        input_layout.setSpacing(8)  # 减小间距

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("✍️ 在这里输入您的创作内容，或者描述您想要创作的故事主题...\n\n💡 提示：您可以输入故事大纲、角色设定、情节描述等，AI将帮助您完善和扩展内容。")
        self.text_input.setMinimumHeight(150)  # 减小最小高度
        self.text_input.setFont(QFont("Microsoft YaHei UI", 11))  # 稍微减小字体
        self.text_input.setStyleSheet("""
            QTextEdit {
                border: 2px solid #ecf0f1;
                border-radius: 8px;
                padding: 10px;
                background: white;
                color: #2c3e50;
                line-height: 1.5;
                selection-background-color: #e8f4fd;
            }
            QTextEdit:focus {
                border-color: #3498db;
                background: #fdfdfd;
            }
            QTextEdit:hover {
                border-color: #bdc3c7;
            }
        """)
        # 连接文本变化信号，用于项目检测
        self.text_input.textChanged.connect(self.on_text_input_changed)
        input_layout.addWidget(self.text_input)

        input_card.add_layout(input_layout)
        layout.addWidget(input_card)

        # 操作按钮卡片
        actions_card = self.create_beautiful_card("🚀 AI创作助手", "#9b59b6")
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(15, 12, 15, 12)  # 减小内边距
        actions_layout.setSpacing(10)  # 减小间距

        # AI创作按钮
        ai_create_btn = QPushButton("🎭 AI创作故事")
        ai_create_btn.setMinimumHeight(40)  # 减小按钮高度
        ai_create_btn.setFont(QFont("Microsoft YaHei UI", 12, QFont.Medium))
        ai_create_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #3498db, stop: 1 #2980b9);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 20px;
                font-weight: 600;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #5dade2, stop: 1 #3498db);
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #2980b9, stop: 1 #1f618d);
            }
        """)
        ai_create_btn.clicked.connect(self.ai_create_story)
        actions_layout.addWidget(ai_create_btn)

        # 文本改写按钮
        rewrite_btn = QPushButton("✨ AI改写优化")
        rewrite_btn.setMinimumHeight(40)  # 减小按钮高度
        rewrite_btn.setFont(QFont("Microsoft YaHei UI", 12, QFont.Medium))
        rewrite_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #2ecc71, stop: 1 #27ae60);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 20px;
                font-weight: 600;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #58d68d, stop: 1 #2ecc71);
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #27ae60, stop: 1 #1e8449);
            }
        """)
        rewrite_btn.clicked.connect(self.rewrite_text)
        actions_layout.addWidget(rewrite_btn)

        actions_card.add_layout(actions_layout)
        layout.addWidget(actions_card)

        # 结果展示卡片
        result_card = self.create_beautiful_card("🎯 创作结果", "#e67e22")
        result_layout = QVBoxLayout()
        result_layout.setContentsMargins(15, 12, 15, 15)  # 减小内边距
        result_layout.setSpacing(8)  # 减小间距

        self.rewritten_text = QTextEdit()
        self.rewritten_text.setPlaceholderText("🎉 AI创作的精彩内容将在这里呈现...\n\n📖 您可以在这里查看AI生成的故事、改写的文本或优化建议。")
        self.rewritten_text.setMinimumHeight(180)  # 减小最小高度
        self.rewritten_text.setFont(QFont("Microsoft YaHei UI", 11))  # 稍微减小字体
        self.rewritten_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #ecf0f1;
                border-radius: 8px;
                padding: 10px;
                background: #f8f9fa;
                color: #2c3e50;
                line-height: 1.5;
                selection-background-color: #fff3cd;
            }
            QTextEdit:focus {
                border-color: #f39c12;
                background: white;
            }
            QTextEdit:hover {
                border-color: #bdc3c7;
            }
        """)
        result_layout.addWidget(self.rewritten_text)

        result_card.add_layout(result_layout)
        layout.addWidget(result_card)

        layout.addStretch()

        scroll_area.setWidget(content_widget)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll_area)

        return page

    def create_beautiful_card(self, title, accent_color="#3498db"):
        """创建美观的卡片组件"""
        card = ModernCard(title)
        card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 2px solid #ecf0f1;
                border-radius: 16px;
                border-left: 4px solid {accent_color};
                margin: 4px;
                padding: 2px;
            }}
            QFrame:hover {{
                border-color: #bdc3c7;
                background: #fdfdfd;
            }}
            QLabel {{
                color: #2c3e50;
                font-weight: 600;
                font-size: 14px;
                background: transparent;
                padding: 8px 0;
            }}
        """)
        return card

    def create_project_page(self):
        """创建项目管理页面"""
        from PyQt5.QtWidgets import QScrollArea

        page = QWidget()
        page.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #f8f9fa, stop: 1 #e9ecef);
                font-family: "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif;
            }
        """)

        # 主滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #f1f3f4;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #c1c8cd;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a8b1ba;
            }
        """)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)

        # 页面标题
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("📁 项目管理中心")
        title_label.setFont(QFont("Microsoft YaHei UI", 24, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                background: transparent;
                padding: 10px 0;
            }
        """)

        subtitle_label = QLabel("管理您的AI视频创作项目")
        subtitle_label.setFont(QFont("Microsoft YaHei UI", 12))
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                background: transparent;
                margin-left: 10px;
            }
        """)

        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        title_layout.addStretch()
        layout.addWidget(title_widget)

        # 项目操作卡片
        actions_card = self.create_beautiful_card("🚀 项目操作", "#3498db")
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(25, 20, 25, 20)
        actions_layout.setSpacing(15)

        # 新建项目按钮
        new_project_btn = QPushButton("📝 新建项目")
        new_project_btn.setMinimumHeight(50)
        new_project_btn.setFont(QFont("Microsoft YaHei UI", 12, QFont.Medium))
        new_project_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #3498db, stop: 1 #2980b9);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 20px;
                font-weight: 600;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #5dade2, stop: 1 #3498db);
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #2980b9, stop: 1 #1f618d);
            }
        """)
        new_project_btn.clicked.connect(self.new_project)
        actions_layout.addWidget(new_project_btn)

        # 打开项目按钮
        open_project_btn = QPushButton("📂 打开项目")
        open_project_btn.setMinimumHeight(50)
        open_project_btn.setFont(QFont("Microsoft YaHei UI", 12, QFont.Medium))
        open_project_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #2ecc71, stop: 1 #27ae60);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 20px;
                font-weight: 600;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #58d68d, stop: 1 #2ecc71);
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #27ae60, stop: 1 #1e8449);
            }
        """)
        open_project_btn.clicked.connect(self.open_project)
        actions_layout.addWidget(open_project_btn)

        # 刷新项目按钮
        refresh_btn = QPushButton("🔄 刷新列表")
        refresh_btn.setMinimumHeight(50)
        refresh_btn.setFont(QFont("Microsoft YaHei UI", 12, QFont.Medium))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #f39c12, stop: 1 #e67e22);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 20px;
                font-weight: 600;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #f7dc6f, stop: 1 #f39c12);
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #e67e22, stop: 1 #d35400);
            }
        """)
        refresh_btn.clicked.connect(self.refresh_project_list)
        actions_layout.addWidget(refresh_btn)

        actions_card.add_layout(actions_layout)
        layout.addWidget(actions_card)

        # 项目列表卡片
        self.projects_list_card = self.create_beautiful_card("📋 项目列表", "#9b59b6")
        self.projects_list_layout = QVBoxLayout()
        self.projects_list_layout.setContentsMargins(25, 20, 25, 25)
        self.projects_list_layout.setSpacing(10)

        # 初始加载项目列表
        self.refresh_project_list()

        self.projects_list_card.add_layout(self.projects_list_layout)
        layout.addWidget(self.projects_list_card)

        layout.addStretch()

        scroll_area.setWidget(content_widget)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll_area)

        return page

    def setup_connections(self):
        """设置信号连接"""
        logger.info("正在连接异步任务执行器的信号...")
        async_runner.signal_success.connect(self._on_ai_task_success)
        async_runner.signal_failed.connect(self._on_ai_task_failed)
        async_runner.signal_finished.connect(self._on_ai_task_finished)

    def switch_to_page(self, page_id):
        """切换到指定页面"""
        if page_id in self.pages:
            # 更新按钮状态
            for btn_id, btn in self.nav_buttons.items():
                btn.setChecked(btn_id == page_id)

            # 切换页面
            self.content_stack.setCurrentWidget(self.pages[page_id])
            self.current_page = page_id

            # 控制信息面板的显示/隐藏
            self.update_info_panel_visibility(page_id)

            logger.info(f"切换到页面: {page_id}")

    def update_info_panel_visibility(self, page_id):
        """根据当前页面更新信息面板的显示状态"""
        try:
            # 只在工作流程和系统设置页面显示信息面板
            show_info_panel = page_id in ['workflow', 'settings']

            if hasattr(self, 'info_panel') and hasattr(self, 'main_splitter'):
                if show_info_panel:
                    # 显示信息面板
                    self.info_panel.show()
                    # 恢复分割器比例 (导航:内容:信息 = 1:3:1)
                    self.main_splitter.setSizes([200, 800, 280])
                else:
                    # 隐藏信息面板
                    self.info_panel.hide()
                    # 调整分割器比例，给内容区域更多空间 (导航:内容 = 1:4)
                    self.main_splitter.setSizes([200, 1000, 0])

                logger.debug(f"信息面板显示状态: {show_info_panel} (页面: {page_id})")

        except Exception as e:
            logger.error(f"更新信息面板显示状态失败: {e}")

    def toggle_theme(self):
        """切换主题"""
        # 这里可以实现主题切换逻辑
        logger.info("主题切换功能待实现")

    def new_project(self):
        """新建项目"""
        try:
            from src.gui.project_dialog import NewProjectDialog
            from src.utils.ui_utils import show_success

            dialog = NewProjectDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                project_info = dialog.get_project_info()

                # 创建新项目
                if self.project_manager.create_new_project(
                    project_info["name"],
                    project_info["description"]
                ):
                    # 设置当前活跃项目
                    self.current_active_project = project_info["name"]
                    logger.info(f"💾 设置当前活跃项目: {self.current_active_project}")

                    show_success(f"项目 '{project_info['name']}' 创建成功！")
                    self.setWindowTitle(f"AI 视频生成系统 - {project_info['name']}")
                    logger.info(f"新项目创建成功: {project_info['name']}")
                else:
                    QMessageBox.critical(self, "错误", "项目创建失败！")

        except Exception as e:
            logger.error(f"新建项目失败: {e}")
            QMessageBox.critical(self, "错误", f"新建项目失败：{e}")

    def open_project(self):
        """打开项目"""
        try:
            from src.gui.project_dialog import OpenProjectDialog
            from src.utils.ui_utils import show_success

            if not hasattr(self, 'project_manager') or not self.project_manager:
                QMessageBox.warning(self, "警告", "项目管理器未初始化！")
                return

            # 获取项目列表
            projects = self.project_manager.list_projects()

            if not projects:
                QMessageBox.information(self, "提示", "没有找到任何项目，请先创建一个项目。")
                return

            # 显示打开项目对话框
            dialog = OpenProjectDialog(projects, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_project = dialog.get_selected_project()
                if selected_project:
                    try:
                        # 加载项目
                        project_config = self.project_manager.load_project(selected_project["path"])

                        if project_config:
                            # 设置当前项目名称
                            project_name = project_config.get('project_name') or selected_project.get('name')
                            current_project_name = project_name or os.path.basename(selected_project["path"])

                            # 设置当前活跃项目
                            self.current_active_project = current_project_name
                            logger.info(f"💾 设置当前活跃项目: {self.current_active_project}")

                            # 更新窗口标题
                            self.setWindowTitle(f"AI 视频生成系统 - {current_project_name}")

                            # 🔧 重要：延迟加载项目数据到所有界面组件，确保UI完全初始化
                            QTimer.singleShot(500, lambda: self.load_project_data_to_ui(project_config))

                            # 显示成功消息
                            show_success(f"项目 '{current_project_name}' 打开成功！")

                            logger.info(f"项目打开成功: {current_project_name}")
                        else:
                            QMessageBox.critical(self, "错误", "项目加载失败！")
                    except Exception as e:
                        logger.error(f"加载项目失败: {e}")
                        QMessageBox.critical(self, "错误", f"加载项目失败：{e}")

        except Exception as e:
            logger.error(f"打开项目失败: {e}")
            QMessageBox.critical(self, "错误", f"打开项目失败：{e}")

    def save_project(self):
        """保存项目"""
        try:
            from src.utils.ui_utils import show_success

            if not hasattr(self, 'project_manager') or not self.project_manager:
                QMessageBox.warning(self, "警告", "项目管理器未初始化！")
                return

            if not self.project_manager.current_project:
                QMessageBox.warning(self, "警告", "没有打开的项目可以保存！")
                return

            if self.project_manager.save_project():
                show_success("项目保存成功！")
                logger.info("项目保存成功")
            else:
                QMessageBox.critical(self, "错误", "项目保存失败！")

        except Exception as e:
            logger.error(f"保存项目失败: {e}")
            QMessageBox.critical(self, "错误", f"保存项目失败：{e}")

    def refresh_project(self):
        """刷新项目"""
        try:
            from src.utils.ui_utils import show_success

            if not hasattr(self, 'project_manager') or not self.project_manager:
                QMessageBox.warning(self, "警告", "项目管理器未初始化！")
                return

            if not self.project_manager.current_project:
                QMessageBox.information(self, "提示", "当前没有打开的项目")
                return

            # 重新加载项目数据
            project_path = self.project_manager.current_project.get("project_dir")
            if project_path:
                project_file = os.path.join(project_path, "project.json")
                if os.path.exists(project_file):
                    self.project_manager.load_project(project_file)
                    show_success("项目数据刷新完成！")
                    logger.info("项目数据刷新完成")
                else:
                    QMessageBox.warning(self, "警告", "项目文件不存在！")
            else:
                QMessageBox.warning(self, "警告", "无法确定项目路径！")

        except Exception as e:
            logger.error(f"刷新项目失败: {e}")
            QMessageBox.critical(self, "错误", f"刷新项目失败：{e}")

    def refresh_project_list(self):
        """刷新项目列表显示"""
        try:
            # 清空现有列表
            for i in reversed(range(self.projects_list_layout.count())):
                child = self.projects_list_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)

            if not hasattr(self, 'project_manager') or not self.project_manager:
                no_manager_label = QLabel("⚠️ 项目管理器未初始化")
                no_manager_label.setStyleSheet("""
                    QLabel {
                        color: #e74c3c;
                        font-size: 14px;
                        padding: 20px;
                        text-align: center;
                        background: transparent;
                    }
                """)
                self.projects_list_layout.addWidget(no_manager_label)
                return

            # 获取项目列表
            projects = self.project_manager.list_projects()

            if not projects:
                no_projects_label = QLabel("📝 暂无项目，点击上方按钮创建您的第一个项目")
                no_projects_label.setStyleSheet("""
                    QLabel {
                        color: #7f8c8d;
                        font-size: 14px;
                        padding: 30px;
                        text-align: center;
                        background: transparent;
                    }
                """)
                self.projects_list_layout.addWidget(no_projects_label)
                return

            # 显示项目列表
            for project in projects:
                project_widget = self.create_project_item(project)
                self.projects_list_layout.addWidget(project_widget)

            logger.info(f"项目列表已刷新，共 {len(projects)} 个项目")

        except Exception as e:
            logger.error(f"刷新项目列表失败: {e}")
            error_label = QLabel(f"❌ 刷新失败：{e}")
            error_label.setStyleSheet("""
                QLabel {
                    color: #e74c3c;
                    font-size: 12px;
                    padding: 20px;
                    text-align: center;
                    background: transparent;
                }
            """)
            self.projects_list_layout.addWidget(error_label)

    def create_project_item(self, project):
        """创建项目列表项"""
        from PyQt5.QtCore import QDateTime

        item_widget = QWidget()
        item_widget.setStyleSheet("""
            QWidget {
                background: white;
                border: 1px solid #ecf0f1;
                border-radius: 8px;
                margin: 2px;
                padding: 2px;
            }
            QWidget:hover {
                border-color: #3498db;
                background: #f8f9fa;
            }
        """)

        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(12)

        # 项目信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # 项目名称
        name_label = QLabel(f"📁 {project.get('name', '未知项目')}")
        name_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        name_label.setStyleSheet("color: #2c3e50; background: transparent;")
        info_layout.addWidget(name_label)

        # 项目时间信息
        try:
            created_time = project.get('created_time', '')
            if created_time:
                if 'T' in created_time:
                    created_time = created_time.split('T')[0] + ' ' + created_time.split('T')[1][:8]
                else:
                    created_time = created_time[:19] if len(created_time) > 19 else created_time
        except:
            created_time = '未知'

        try:
            modified_time = project.get('last_modified', '')
            if modified_time:
                if 'T' in modified_time:
                    modified_time = modified_time.split('T')[0] + ' ' + modified_time.split('T')[1][:8]
                else:
                    modified_time = modified_time[:19] if len(modified_time) > 19 else modified_time
        except:
            modified_time = '未知'

        time_label = QLabel(f"🕒 创建: {created_time}  |  📝 修改: {modified_time}")
        time_label.setFont(QFont("Microsoft YaHei UI", 9))
        time_label.setStyleSheet("color: #7f8c8d; background: transparent;")
        info_layout.addWidget(time_label)

        layout.addLayout(info_layout, 1)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        # 打开按钮
        open_btn = QPushButton("打开")
        open_btn.setMinimumHeight(32)
        open_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #2980b9;
            }
        """)
        open_btn.clicked.connect(lambda: self.load_project_by_path(project.get('path')))
        btn_layout.addWidget(open_btn)

        layout.addLayout(btn_layout)

        return item_widget

    def load_project_by_path(self, project_path):
        """通过路径加载项目"""
        try:
            from src.utils.ui_utils import show_success

            if not hasattr(self, 'project_manager') or not self.project_manager:
                QMessageBox.warning(self, "警告", "项目管理器未初始化！")
                return

            if not project_path:
                QMessageBox.warning(self, "警告", "项目路径无效！")
                return

            # 加载项目
            project_config = self.project_manager.load_project(project_path)

            if project_config:
                # 获取项目名称
                project_name = project_config.get('project_name') or os.path.basename(project_path)

                # 更新窗口标题
                self.setWindowTitle(f"AI 视频生成系统 - {project_name}")

                # 🔧 重要：延迟加载项目数据到所有界面组件，确保UI完全初始化
                QTimer.singleShot(500, lambda: self.load_project_data_to_ui(project_config))

                # 显示成功消息
                show_success(f"项目 '{project_name}' 加载成功！")

                logger.info(f"项目加载成功: {project_name}")
            else:
                QMessageBox.critical(self, "错误", "项目加载失败！")

        except Exception as e:
            logger.error(f"加载项目失败: {e}")
            QMessageBox.critical(self, "错误", f"加载项目失败：{e}")

    def load_project_data_to_ui(self, project_config):
        """将项目数据加载到所有界面组件"""
        try:
            logger.info("开始将项目数据同步到界面组件...")

            # 1. 加载文章创作数据
            self.load_text_creation_data(project_config)

            # 2. 加载五阶段分镜数据
            self.load_five_stage_data(project_config)

            # 3. 加载图像生成数据
            self.load_image_generation_data(project_config)

            # 4. 加载配音数据
            self.load_voice_generation_data(project_config)

            # 5. 加载视频合成数据
            self.load_video_synthesis_data(project_config)

            # 6. 加载一致性控制数据
            self.load_consistency_control_data(project_config)

            # 7. 更新工作流程状态
            self.update_workflow_status(project_config)

            logger.info("项目数据同步到界面组件完成")

        except Exception as e:
            logger.error(f"同步项目数据到界面失败: {e}")

    def load_text_creation_data(self, project_config):
        """加载文章创作数据"""
        try:
            logger.info("开始加载文章创作数据...")

            # 加载原始文本 - 尝试多个可能的位置
            original_text = ""

            # 方法1：从text_content中获取
            if "text_content" in project_config:
                original_text = project_config["text_content"].get("original_text", "")

            # 方法2：直接从根级别获取
            if not original_text:
                original_text = project_config.get("original_text", "")

            # 方法3：从text_creation中获取
            if not original_text:
                text_creation_data = project_config.get("text_creation", {})
                original_text = text_creation_data.get("original_text", "")

            # 方法4：从五阶段数据中获取
            if not original_text:
                five_stage_data = project_config.get("five_stage_storyboard", {})
                original_text = five_stage_data.get("article_text", "")

            if original_text and hasattr(self, 'text_input'):
                self.text_input.setPlainText(original_text)
                logger.info(f"已恢复文章创作的原始文本，长度: {len(original_text)}")
            else:
                logger.info("未找到原始文本数据")

            # 加载改写文本 - 尝试多个可能的位置
            rewritten_text = ""

            # 方法1：从text_creation中获取
            text_creation_data = project_config.get("text_creation", {})
            rewritten_text = text_creation_data.get("rewritten_text", "")

            # 方法2：从text_content中获取
            if not rewritten_text:
                text_content = project_config.get("text_content", {})
                rewritten_text = text_content.get("rewritten_text", "")

            # 方法3：直接从根级别获取
            if not rewritten_text:
                rewritten_text = project_config.get("rewritten_text", "")

            if rewritten_text and hasattr(self, 'rewritten_text'):
                self.rewritten_text.setPlainText(rewritten_text)
                logger.info(f"已恢复文章创作的改写文本，长度: {len(rewritten_text)}")
            else:
                logger.info("未找到改写结果数据")

            # 加载风格设置 - 尝试多个可能的位置
            style_setting = ""

            # 方法1：从text_creation中获取
            text_creation_data = project_config.get("text_creation", {})
            style_setting = text_creation_data.get("selected_style", "")

            # 方法2：从五阶段数据中获取
            if not style_setting:
                five_stage_data = project_config.get("five_stage_storyboard", {})
                style_setting = five_stage_data.get("selected_style", "")

            # 方法3：从图像生成设置中获取
            if not style_setting:
                image_settings = project_config.get("image_generation", {}).get("settings", {})
                style_setting = image_settings.get("style", "")

            # 方法4：从根级别获取
            if not style_setting:
                style_setting = project_config.get("style_setting", "")

            if style_setting and hasattr(self, 'style_combo'):
                # 查找匹配的风格选项
                for i in range(self.style_combo.count()):
                    item_text = self.style_combo.itemText(i)
                    if style_setting in item_text or item_text in style_setting:
                        self.style_combo.setCurrentIndex(i)
                        logger.info(f"已恢复风格设置: {style_setting}")
                        break
                else:
                    logger.warning(f"未找到匹配的风格选项: {style_setting}")
            else:
                logger.info("未找到风格设置数据")

            # 加载改写结果 - 尝试多个可能的位置
            rewritten_text = ""

            # 方法1：从text_content中获取
            if "text_content" in project_config:
                rewritten_text = project_config["text_content"].get("rewritten_text", "")

            # 方法2：直接从根级别获取
            if not rewritten_text:
                rewritten_text = project_config.get("rewritten_text", "")

            if rewritten_text and hasattr(self, 'rewritten_text'):
                self.rewritten_text.setPlainText(rewritten_text)
                logger.info(f"已恢复文章改写结果，长度: {len(rewritten_text)}")
            else:
                logger.info("未找到改写结果数据")

        except Exception as e:
            logger.error(f"加载文章创作数据失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")

    def load_five_stage_data(self, project_config):
        """加载五阶段分镜数据"""
        try:
            # 直接调用五阶段分镜标签页的加载方法
            if hasattr(self, 'pages') and 'storyboard' in self.pages:
                storyboard_tab = self.pages['storyboard']
                if hasattr(storyboard_tab, 'load_from_project'):
                    # 确保项目管理器已设置（使用有get_character_scene_manager方法的版本）
                    if hasattr(self, 'storyboard_project_manager'):
                        storyboard_tab.project_manager = self.storyboard_project_manager

                    # 确保父窗口引用已设置
                    if not hasattr(storyboard_tab, 'parent_window'):
                        storyboard_tab.parent_window = self

                    # 强制加载项目数据
                    storyboard_tab.load_from_project(force_load=True)
                    logger.info("已触发五阶段分镜数据加载")
                else:
                    logger.warning("五阶段分镜标签页没有load_from_project方法")
            else:
                logger.warning("未找到五阶段分镜标签页")

        except Exception as e:
            logger.error(f"加载五阶段分镜数据失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")

    def load_image_generation_data(self, project_config):
        """加载图像生成数据"""
        try:
            # 直接调用图像生成标签页的加载方法
            if hasattr(self, 'pages') and 'image' in self.pages:
                image_tab = self.pages['image']
                if hasattr(image_tab, 'load_storyboard_data'):
                    image_tab.load_storyboard_data()
                    logger.info("已触发图像生成数据加载")
                elif hasattr(image_tab, 'refresh_data'):
                    image_tab.refresh_data()
                    logger.info("已触发图像生成数据刷新")
                else:
                    logger.warning("图像生成标签页没有数据加载方法")
            else:
                logger.warning("未找到图像生成标签页")

        except Exception as e:
            logger.error(f"加载图像生成数据失败: {e}")

    def load_voice_generation_data(self, project_config):
        """加载配音数据"""
        try:
            # 直接调用配音标签页的加载方法
            if hasattr(self, 'pages') and 'voice' in self.pages:
                voice_tab = self.pages['voice']
                if hasattr(voice_tab, 'load_project_data'):
                    voice_tab.load_project_data()
                    logger.info("已触发配音数据加载")
                elif hasattr(voice_tab, 'refresh_data'):
                    voice_tab.refresh_data()
                    logger.info("已触发配音数据刷新")
                else:
                    logger.warning("配音标签页没有数据加载方法")
            else:
                logger.warning("未找到配音标签页")

        except Exception as e:
            logger.error(f"加载配音数据失败: {e}")

    def load_video_synthesis_data(self, project_config):
        """加载视频合成数据"""
        try:
            # 直接调用视频合成标签页的加载方法
            if hasattr(self, 'pages') and 'video' in self.pages:
                video_tab = self.pages['video']
                if hasattr(video_tab, 'load_scenes_data'):
                    video_tab.load_scenes_data(project_config)
                    logger.info("已触发视频合成数据加载")
                elif hasattr(video_tab, 'load_project_data'):
                    video_tab.load_project_data()
                    logger.info("已触发视频合成数据加载")
                elif hasattr(video_tab, 'refresh_data'):
                    video_tab.refresh_data()
                    logger.info("已触发视频合成数据刷新")
                else:
                    logger.warning("视频合成标签页没有数据加载方法")
            else:
                logger.warning("未找到视频合成标签页")

        except Exception as e:
            logger.error(f"加载视频合成数据失败: {e}")

    def load_consistency_control_data(self, project_config):
        """加载一致性控制数据"""
        try:
            # 直接调用一致性控制标签页的加载方法
            if hasattr(self, 'pages') and 'consistency' in self.pages:
                consistency_tab = self.pages['consistency']
                if hasattr(consistency_tab, 'load_project_data'):
                    consistency_tab.load_project_data()
                    logger.info("已触发一致性控制数据加载")
                elif hasattr(consistency_tab, 'refresh_data'):
                    consistency_tab.refresh_data()
                    logger.info("已触发一致性控制数据刷新")
                else:
                    logger.warning("一致性控制标签页没有数据加载方法")
            else:
                logger.warning("未找到一致性控制标签页")

        except Exception as e:
            logger.error(f"加载一致性控制数据失败: {e}")

    def update_workflow_status(self, project_config):
        """更新工作流程状态"""
        try:
            # 获取工作流程状态
            workflow_status = project_config.get("workflow_status", {})

            if workflow_status:
                logger.info(f"工作流程状态: {workflow_status}")

                # 这里可以根据需要更新工作流程页面的状态显示
                # 例如更新进度条、状态指示器等

        except Exception as e:
            logger.error(f"更新工作流程状态失败: {e}")

    def _call_ai_service(self, coro, task_info):
        """
        通用AI服务调用方法。
        :param coro: 要执行的协程。
        :param task_info: 包含任务信息的字典, e.g., {'title': 'AI创作中', 'message': '正在使用AI创作故事...'}
        """
        try:
            progress = QProgressDialog(task_info['message'], "取消", 0, 0, self)
            progress.setWindowTitle(task_info['title'])
            progress.setModal(True)
            progress.show()

            task_id = async_runner.run(coro)
            self.active_ai_tasks[task_id] = {
                'progress': progress,
                'info': task_info
            }
            logger.info(f"已提交AI任务 '{task_id}': {task_info['title']}")

        except Exception as e:
            logger.error(f"提交AI任务失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"无法启动AI任务: {e}")

    @pyqtSlot(str, object)
    def _on_ai_task_success(self, task_id, result):
        """处理AI任务成功完成的槽函数。"""
        if task_id not in self.active_ai_tasks:
            return

        logger.info(f"AI任务 '{task_id}' 成功完成。")
        task_data = self.active_ai_tasks.get(task_id, {})
        
        if result.success:
            content = result.data.get('content', '操作完成，但内容为空。')
            self.rewritten_text.setPlainText(content)
            self._save_ai_creation_result(content)
            show_success(f"{task_data.get('info', {}).get('title', 'AI任务')}已完成！")
        else:
            error_msg = f"AI任务失败: {result.error}"
            logger.error(error_msg)
            QMessageBox.warning(self, "任务失败", error_msg)

    @pyqtSlot(str, object)
    def _on_ai_task_failed(self, task_id, exception):
        """处理AI任务执行失败的槽函数。"""
        if task_id not in self.active_ai_tasks:
            return
        
        error_msg = f"AI任务执行时发生严重错误: {exception}"
        logger.error(error_msg, exc_info=True)
        QMessageBox.critical(self, "严重错误", error_msg)

    @pyqtSlot(str)
    def _on_ai_task_finished(self, task_id):
        """处理AI任务结束（无论成功或失败）的槽函数。"""
        if task_id in self.active_ai_tasks:
            task_data = self.active_ai_tasks.pop(task_id)
            if task_data and task_data.get('progress'):
                task_data['progress'].close()
            logger.info(f"AI任务 '{task_id}' 已清理。")

    def on_text_input_changed(self):
        """文本输入变化时的处理"""
        try:
            # 获取当前文本内容
            text_content = self.text_input.toPlainText().strip()

            # 如果文本为空，不需要检查项目
            if not text_content:
                return

            # 检查是否有当前项目
            if not self.project_manager or not self.project_manager.current_project:
                # 延迟检查，避免频繁弹窗
                if not hasattr(self, '_project_check_timer'):
                    from PyQt5.QtCore import QTimer
                    self._project_check_timer = QTimer()
                    self._project_check_timer.setSingleShot(True)
                    self._project_check_timer.timeout.connect(self._check_and_prompt_project)

                # 重置计时器，2秒后检查
                self._project_check_timer.stop()
                self._project_check_timer.start(2000)

        except Exception as e:
            logger.error(f"文本输入变化处理失败: {e}")

    def _check_and_prompt_project(self):
        """检查项目状态并提示用户"""
        try:
            # 再次检查文本内容和项目状态
            text_content = self.text_input.toPlainText().strip()
            if not text_content:
                return

            if not self.project_manager or not self.project_manager.current_project:
                self._show_project_reminder()

        except Exception as e:
            logger.error(f"项目检查失败: {e}")

    def _show_project_reminder(self):
        """显示项目提醒对话框"""
        try:
            from PyQt5.QtWidgets import QMessageBox

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("💡 项目提醒")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText("检测到您已经开始输入文本内容！")
            msg_box.setInformativeText(
                "为了更好地管理您的创作内容，建议先创建一个项目。\n\n"
                "创建项目后，您的文本内容将自动保存，\n"
                "并且可以使用完整的AI创作功能。"
            )

            # 添加自定义按钮
            create_btn = msg_box.addButton("🆕 立即创建项目", QMessageBox.AcceptRole)
            continue_btn = msg_box.addButton("📝 继续输入", QMessageBox.RejectRole)
            msg_box.setDefaultButton(create_btn)

            # 设置样式
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #f8f9fa;
                    font-family: "Microsoft YaHei UI";
                }
                QMessageBox QLabel {
                    color: #2c3e50;
                    font-size: 12px;
                }
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 500;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #1f618d;
                }
            """)

            result = msg_box.exec_()

            # 处理用户选择
            if msg_box.clickedButton() == create_btn:
                self.new_project()

        except Exception as e:
            logger.error(f"显示项目提醒失败: {e}")

    def ai_create_story(self):
        """AI创作故事（重构后）"""
        theme = self.text_input.toPlainText().strip()
        if not theme:
            QMessageBox.warning(self, "警告", "请先在文本框中输入故事主题或关键词")
            return

        # 检查项目状态
        if not self.project_manager or not self.project_manager.current_project:
            QMessageBox.warning(self, "警告", "请先创建或打开一个项目，然后再使用AI创作功能")
            return

        llm_service = self.service_manager.get_service(ServiceType.LLM)
        if not llm_service:
            QMessageBox.critical(self, "错误", "LLM服务不可用。")
            return

        provider = self._get_selected_provider()
        coro = llm_service.create_story_from_theme(theme, provider)
        task_info = {'title': 'AI创作故事', 'message': '正在连接AI为您创作故事...'}
        self._call_ai_service(coro, task_info)

    def _save_ai_creation_result(self, content):
        """保存AI创作结果到项目数据"""
        try:
            # 获取当前项目管理器
            project_manager = self.app_controller.project_manager
            if not project_manager:
                logger.warning("💾 项目管理器不存在，无法保存AI创作结果")
                return

            # 检查当前项目状态
            current_project_name = None
            if not project_manager.current_project:
                logger.warning("💾 没有当前项目，尝试重新加载项目状态...")
                # 尝试从项目列表中获取当前项目
                if hasattr(self, 'project_list') and self.project_list.currentItem():
                    current_project_name = self.project_list.currentItem().text()
                    logger.info(f"💾 尝试重新加载项目: {current_project_name}")
                    try:
                        project_manager.load_project(current_project_name)
                        logger.info(f"💾 项目重新加载成功: {current_project_name}")
                    except Exception as e:
                        logger.error(f"💾 项目重新加载失败: {e}")
                else:
                    # 尝试从应用控制器获取当前项目名称
                    if hasattr(self.app_controller, 'current_project_name'):
                        current_project_name = self.app_controller.current_project_name
                        logger.info(f"💾 从应用控制器获取项目名称: {current_project_name}")
                    else:
                        # 最后尝试：从最近打开的项目中获取
                        logger.info("💾 尝试从最近打开的项目中获取...")
                        # 这里可以添加从配置文件或其他地方获取最近项目的逻辑

            # 如果仍然没有项目，尝试直接操作项目文件
            if not project_manager.current_project:
                if current_project_name:
                    logger.info(f"💾 尝试直接保存到项目文件: {current_project_name}")
                    self._save_to_project_file_directly(current_project_name, content)
                    return
                else:
                    # 最后的备用方案：尝试从最近的项目操作中获取
                    logger.warning("💾 无法确定当前项目，尝试从最近操作中获取...")
                    recent_project_name = self._get_most_recent_project()
                    if recent_project_name:
                        logger.info(f"💾 使用最近项目: {recent_project_name}")
                        self._save_to_project_file_directly(recent_project_name, content)
                        return
                    else:
                        logger.error("💾 无法确定任何项目，无法保存AI创作结果")
                        return

            # 保存到文章创作数据
            logger.info("💾 保存AI创作结果到文章创作数据...")

            # 获取当前选择的风格和模型
            style = self.style_combo.currentText() if hasattr(self, 'style_combo') else "默认风格"
            model = self.model_combo.currentText() if hasattr(self, 'model_combo') else "默认模型"

            # 判断是原始文本还是改写文本
            original_text = self.text_input.toPlainText().strip() if hasattr(self, 'text_input') else ""

            # 构建文章创作数据
            text_creation_data = {
                "selected_style": style,
                "selected_model": model,
                "last_modified": datetime.now().isoformat(),
                "content_length": len(content)
            }

            # 如果有原始文本，说明这是改写结果
            if original_text:
                text_creation_data["original_text"] = original_text
                text_creation_data["rewritten_text"] = content
                logger.info("💾 保存为AI改写结果")
            else:
                text_creation_data["rewritten_text"] = content
                logger.info("💾 保存为AI创作结果")

            # 保存到项目数据
            project_data = project_manager.current_project
            if "text_creation" not in project_data:
                project_data["text_creation"] = {}

            project_data["text_creation"].update(text_creation_data)

            # 保存项目文件
            project_manager.save_project()

            logger.info(f"💾 AI创作结果已保存到项目数据，内容长度: {len(content)} 字符")

        except Exception as e:
            logger.error(f"💾 保存AI创作结果失败: {e}")
            import traceback
            logger.error(f"💾 详细错误: {traceback.format_exc()}")

    def _save_to_project_file_directly(self, project_name, content):
        """直接保存到项目文件"""
        try:
            import json
            import os

            project_file = os.path.join("output", project_name, "project.json")
            logger.info(f"💾 直接保存到项目文件: {project_file}")

            # 读取现有项目数据
            project_data = {}
            if os.path.exists(project_file):
                try:
                    with open(project_file, 'r', encoding='utf-8') as f:
                        project_data = json.load(f)
                    logger.info("💾 成功读取现有项目数据")
                except Exception as e:
                    logger.warning(f"💾 读取现有项目数据失败，创建新数据: {e}")
                    project_data = {"project_name": project_name}
            else:
                logger.info("💾 项目文件不存在，创建新数据")
                project_data = {"project_name": project_name}

            # 获取当前选择的风格和模型
            style = self.style_combo.currentText() if hasattr(self, 'style_combo') else "默认风格"
            model = self.model_combo.currentText() if hasattr(self, 'model_combo') else "默认模型"

            # 判断是原始文本还是改写文本
            original_text = self.text_input.toPlainText().strip() if hasattr(self, 'text_input') else ""

            # 构建文章创作数据
            text_creation_data = {
                "selected_style": style,
                "selected_model": model,
                "last_modified": datetime.now().isoformat(),
                "content_length": len(content)
            }

            # 如果有原始文本，说明这是改写结果
            if original_text:
                text_creation_data["original_text"] = original_text
                text_creation_data["rewritten_text"] = content
                logger.info("💾 保存为AI改写结果")
            else:
                text_creation_data["rewritten_text"] = content
                logger.info("💾 保存为AI创作结果")

            # 更新项目数据
            if "text_creation" not in project_data:
                project_data["text_creation"] = {}

            project_data["text_creation"].update(text_creation_data)
            project_data["last_modified"] = datetime.now().isoformat()

            # 保存到文件
            os.makedirs(os.path.dirname(project_file), exist_ok=True)
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 AI创作结果已直接保存到项目文件，内容长度: {len(content)} 字符")

        except Exception as e:
            logger.error(f"💾 直接保存到项目文件失败: {e}")
            import traceback
            logger.error(f"💾 详细错误: {traceback.format_exc()}")

    def _get_most_recent_project(self):
        """获取最近操作的项目名称"""
        try:
            import os
            import json
            from datetime import datetime

            # 方法1：优先使用当前活跃项目
            if hasattr(self, 'current_active_project') and self.current_active_project:
                logger.info(f"💾 使用当前活跃项目: {self.current_active_project}")
                return self.current_active_project

            # 方法2：检查项目列表中的选中项
            if hasattr(self, 'project_list') and self.project_list.currentItem():
                project_name = self.project_list.currentItem().text()
                logger.info(f"💾 从项目列表获取当前项目: {project_name}")
                return project_name

            # 方法3：查找最近修改的项目文件
            output_dir = "output"
            if os.path.exists(output_dir):
                projects = []
                for item in os.listdir(output_dir):
                    project_dir = os.path.join(output_dir, item)
                    project_file = os.path.join(project_dir, "project.json")
                    if os.path.isdir(project_dir) and os.path.exists(project_file):
                        try:
                            # 获取文件修改时间
                            mtime = os.path.getmtime(project_file)
                            projects.append((item, mtime))
                        except:
                            continue

                if projects:
                    # 按修改时间排序，获取最新的项目
                    projects.sort(key=lambda x: x[1], reverse=True)
                    recent_project = projects[0][0]
                    logger.info(f"💾 从文件修改时间获取最近项目: {recent_project}")
                    return recent_project

            # 方法4：检查是否有项目创建的记录
            # 这里可以添加更多的项目识别逻辑

            logger.warning("💾 无法获取最近项目")
            return None

        except Exception as e:
            logger.error(f"💾 获取最近项目失败: {e}")
            return None

    def rewrite_text(self):
        """AI改写文本（重构后）"""
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请先输入要改写的文本内容")
            return

        # 检查项目状态
        if not self.project_manager or not self.project_manager.current_project:
            QMessageBox.warning(self, "警告", "请先创建或打开一个项目，然后再使用AI改写功能")
            return

        llm_service = self.service_manager.get_service(ServiceType.LLM)
        if not llm_service:
            QMessageBox.critical(self, "错误", "LLM服务不可用。")
            return

        provider = self._get_selected_provider()
        coro = llm_service.rewrite_text(text, provider)
        task_info = {'title': 'AI改写优化', 'message': '正在连接AI为您改写文本...'}
        self._call_ai_service(coro, task_info)

    def _get_selected_provider(self):
        """从UI获取当前选择的AI模型提供商。"""
        selected_model = self.model_combo.currentText()
        provider_map = {
            "🤖 通义千问": "tongyi",
            "🧠 智谱AI": "zhipu",
            "🚀 Deepseek": "deepseek",
            "🌟 Google Gemini": "google",
            "⚡ OpenAI": "openai",
            "🔥 SiliconFlow": "siliconflow"
        }
        return provider_map.get(selected_model, "tongyi")




    def init_display_settings(self):
        """初始化显示设置"""
        try:
            # 初始化显示配置
            from src.utils.display_config import get_display_config
            self.display_config = get_display_config()

            # 初始化DPI适配器
            from src.utils.dpi_adapter import get_dpi_adapter
            self.dpi_adapter = get_dpi_adapter()

            # 应用保存的字体设置
            font_config = self.display_config.get_font_config()
            if font_config.get("auto_size", True):
                # 使用DPI适配器的推荐字体大小
                font_size = self.dpi_adapter.get_recommended_font_size()
            else:
                # 使用保存的字体大小
                font_size = font_config.get("size", 10)

            font_family = font_config.get("family", "Microsoft YaHei UI")

            # 更新DPI适配器设置
            self.dpi_adapter.font_family = font_family
            self.dpi_adapter.current_font_size = font_size

            # 应用DPI设置
            dpi_config = self.display_config.get_dpi_config()
            if dpi_config.get("auto_scaling", True):
                self.dpi_adapter.set_auto_dpi_scaling(True)
            else:
                custom_factor = dpi_config.get("custom_scale_factor", 1.0)
                self.dpi_adapter.set_custom_scale_factor(custom_factor)
                self.dpi_adapter.set_auto_dpi_scaling(False)

            # 应用字体到应用程序
            font = self.dpi_adapter.create_scaled_font(family=font_family, size=font_size)
            app = QApplication.instance()
            if app:
                app.setFont(font)

            # 应用窗口设置
            window_config = self.display_config.get_window_config()
            if window_config.get("auto_resize", True):
                # 使用自适应窗口大小
                width, height = self.dpi_adapter.get_adaptive_window_size()
                self.resize(width, height)
            else:
                # 使用保存的窗口大小
                width = window_config.get("default_width", 1400)
                height = window_config.get("default_height", 900)
                self.resize(width, height)

            logger.info(f"显示设置已初始化 - 字体: {font_family} {font_size}pt, 窗口: {self.width()}x{self.height()}")

        except Exception as e:
            logger.error(f"初始化显示设置失败: {e}")


# 测试代码
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用程序样式
    app.setStyle("Fusion")

    window = ModernCardMainWindow()
    window.show()

    sys.exit(app.exec_())
