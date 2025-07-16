#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化主窗口
重新设计的Material Design风格主界面
"""

import sys
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QStackedWidget, QFrame, QLabel, QPushButton, QSpacerItem, 
    QSizePolicy, QApplication, QMenuBar, QStatusBar, QToolBar,
    QAction, QMessageBox
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

from .styles.unified_theme_system import UnifiedThemeSystem, get_theme_system
from .modern_ui_components import (
    MaterialButton, MaterialCard, MaterialProgressBar, MaterialSlider,
    MaterialComboBox, MaterialLineEdit, MaterialTextEdit, MaterialListWidget,
    MaterialTabWidget, FloatingActionButton, MaterialToolBar, StatusIndicator,
    LoadingSpinner, MaterialGroupBox, MaterialCheckBox, MaterialRadioButton,
    ResponsiveContainer, create_material_button, create_material_card
)
try:
    from .styles import toggle_theme
except ImportError:
    # 如果新样式系统不可用，定义空函数
    def toggle_theme():
        pass
from src.utils.logger import logger


class ModernSidebar(QFrame):
    """现代化侧边栏"""
    
    page_changed = pyqtSignal(str)  # 页面切换信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = "text"
        self.setup_ui()
        self.setup_style()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(8)
        
        # 标题
        title = QLabel("AI视频生成器")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(24)
        
        # 导航按钮
        self.nav_buttons = {}
        nav_items = [
            ("text", "📝", "文本创作"),
            ("storyboard", "🎬", "分镜设计"),
            ("image", "🎨", "图像生成"),
            ("voice", "🎤", "配音制作"),
            ("video", "🎥", "视频合成"),
            ("export", "📤", "导出发布")
        ]
        
        for page_id, icon, title in nav_items:
            btn = self.create_nav_button(page_id, icon, title)
            self.nav_buttons[page_id] = btn
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # 底部工具
        settings_btn = MaterialButton("⚙️ 设置", "text")
        settings_btn.clicked.connect(self.show_settings)
        layout.addWidget(settings_btn)
        
        help_btn = MaterialButton("❓ 帮助", "text")
        help_btn.clicked.connect(self.show_help)
        layout.addWidget(help_btn)
    
    def create_nav_button(self, page_id, icon, title):
        """创建导航按钮"""
        btn = MaterialButton(f"{icon} {title}", "text")
        btn.setMinimumHeight(48)
        btn.setFont(QFont("Segoe UI", 11))
        btn.clicked.connect(lambda: self.switch_page(page_id))
        
        # 设置按钮样式
        if page_id == self.current_page:
            btn.setProperty("selected", True)
        
        return btn
    
    def setup_style(self):
        """设置样式"""
        self.setFixedWidth(240)
        self.setFrameStyle(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setProperty("sidebarStyle", True)
    
    def switch_page(self, page_id):
        """切换页面"""
        if page_id != self.current_page:
            # 更新按钮状态
            if self.current_page in self.nav_buttons:
                self.nav_buttons[self.current_page].setProperty("selected", False)
                self.nav_buttons[self.current_page].style().unpolish(self.nav_buttons[self.current_page])
                self.nav_buttons[self.current_page].style().polish(self.nav_buttons[self.current_page])
            
            self.nav_buttons[page_id].setProperty("selected", True)
            self.nav_buttons[page_id].style().unpolish(self.nav_buttons[page_id])
            self.nav_buttons[page_id].style().polish(self.nav_buttons[page_id])
            
            self.current_page = page_id
            self.page_changed.emit(page_id)
    
    def show_settings(self):
        """显示设置"""
        # TODO: 实现设置对话框
        QMessageBox.information(self, "设置", "设置功能正在开发中...")
    
    def show_help(self):
        """显示帮助"""
        # TODO: 实现帮助对话框
        QMessageBox.information(self, "帮助", "帮助功能正在开发中...")


class ModernHeaderBar(MaterialToolbar):
    """现代化标题栏"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_content()
    
    def setup_content(self):
        """设置内容"""
        # 项目信息
        self.project_label = QLabel("未选择项目")
        self.project_label.setFont(QFont("Segoe UI", 12, QFont.Medium))
        self.add_widget(self.project_label)
        
        # 状态指示器
        self.status_indicator = StatusIndicator("unknown")
        self.add_widget(self.status_indicator)
        
        self.add_stretch()
        
        # 操作按钮
        self.new_btn = MaterialButton("新建", "outlined")
        self.new_btn.setMaximumWidth(80)
        self.add_widget(self.new_btn)
        
        self.open_btn = MaterialButton("打开", "outlined")
        self.open_btn.setMaximumWidth(80)
        self.add_widget(self.open_btn)
        
        self.save_btn = MaterialButton("保存", "filled")
        self.save_btn.setMaximumWidth(80)
        self.add_widget(self.save_btn)
        
        # 主题切换按钮
        self.theme_btn = MaterialButton("🌙", "text")
        self.theme_btn.setFixedSize(40, 40)
        self.theme_btn.setToolTip("切换深色/浅色主题")
        self.theme_btn.clicked.connect(toggle_theme)
        self.add_widget(self.theme_btn)
    
    def update_project_info(self, project_name):
        """更新项目信息"""
        self.project_label.setText(project_name or "未选择项目")
    
    def update_status(self, status):
        """更新状态"""
        self.status_indicator.update_status(status)


class ModernContentArea(QWidget):
    """现代化内容区域"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_pages()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 页面标题
        self.page_title = QLabel("文本创作")
        self.page_title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(self.page_title)
        
        layout.addSpacing(16)
        
        # 内容堆栈
        self.content_stack = QStackedWidget()
        layout.addWidget(self.content_stack)
    
    def setup_pages(self):
        """设置页面"""
        # 创建各个功能页面
        self.pages = {}
        
        # 文本创作页面
        text_page = self.create_text_page()
        self.pages["text"] = text_page
        self.content_stack.addWidget(text_page)
        
        # 分镜设计页面
        storyboard_page = self.create_storyboard_page()
        self.pages["storyboard"] = storyboard_page
        self.content_stack.addWidget(storyboard_page)
        
        # 图像生成页面
        image_page = self.create_image_page()
        self.pages["image"] = image_page
        self.content_stack.addWidget(image_page)
        
        # 配音制作页面
        voice_page = self.create_voice_page()
        self.pages["voice"] = voice_page
        self.content_stack.addWidget(voice_page)
        
        # 视频合成页面
        video_page = self.create_video_page()
        self.pages["video"] = video_page
        self.content_stack.addWidget(video_page)
        
        # 导出发布页面
        export_page = self.create_export_page()
        self.pages["export"] = export_page
        self.content_stack.addWidget(export_page)
    
    def create_text_page(self):
        """创建文本创作页面"""
        page = MaterialCard()
        layout = QVBoxLayout(page)
        
        label = QLabel("文本创作功能")
        label.setFont(QFont("Segoe UI", 14))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        return page
    
    def create_storyboard_page(self):
        """创建分镜设计页面"""
        page = MaterialCard()
        layout = QVBoxLayout(page)
        
        label = QLabel("分镜设计功能")
        label.setFont(QFont("Segoe UI", 14))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        return page
    
    def create_image_page(self):
        """创建图像生成页面"""
        page = MaterialCard()
        layout = QVBoxLayout(page)
        
        label = QLabel("图像生成功能")
        label.setFont(QFont("Segoe UI", 14))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        return page
    
    def create_voice_page(self):
        """创建配音制作页面"""
        page = MaterialCard()
        layout = QVBoxLayout(page)
        
        label = QLabel("配音制作功能")
        label.setFont(QFont("Segoe UI", 14))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        return page
    
    def create_video_page(self):
        """创建视频合成页面"""
        page = MaterialCard()
        layout = QVBoxLayout(page)
        
        label = QLabel("视频合成功能")
        label.setFont(QFont("Segoe UI", 14))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        return page
    
    def create_export_page(self):
        """创建导出发布页面"""
        page = MaterialCard()
        layout = QVBoxLayout(page)
        
        label = QLabel("导出发布功能")
        label.setFont(QFont("Segoe UI", 14))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        return page
    
    def switch_page(self, page_id):
        """切换页面"""
        if page_id in self.pages:
            self.content_stack.setCurrentWidget(self.pages[page_id])
            
            # 更新页面标题
            titles = {
                "text": "文本创作",
                "storyboard": "分镜设计", 
                "image": "图像生成",
                "voice": "配音制作",
                "video": "视频合成",
                "export": "导出发布"
            }
            self.page_title.setText(titles.get(page_id, "未知页面"))


class ModernMainWindow(QMainWindow):
    """现代化主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_connections()
        self.apply_modern_style()
    
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("AI视频生成器 - 现代版")
        self.setMinimumSize(1200, 800)
        
        # 创建中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 标题栏
        self.header_bar = ModernHeaderBar()
        main_layout.addWidget(self.header_bar)
        
        # 内容区域
        content_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(content_splitter)
        
        # 侧边栏
        self.sidebar = ModernSidebar()
        content_splitter.addWidget(self.sidebar)
        
        # 主内容区域
        self.content_area = ModernContentArea()
        content_splitter.addWidget(self.content_area)
        
        # 设置分割器比例
        content_splitter.setSizes([240, 960])
        content_splitter.setCollapsible(0, False)  # 侧边栏不可折叠
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
    
    def setup_connections(self):
        """设置信号连接"""
        self.sidebar.page_changed.connect(self.content_area.switch_page)
    
    def apply_modern_style(self):
        """应用现代化样式"""
        # 使用统一主题系统
        theme_system = get_theme_system()
        theme_system.apply_to_widget(self)
        
        # 设置窗口属性
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        # 应用响应式设计
        self.setup_responsive_layout()
        
        # 设置窗口特定样式
        self.setStyleSheet("""
            ModernSidebar[sidebarStyle="true"] {
                background-color: #F1ECF4;
                border-right: 1px solid #CAC4D0;
            }
            QPushButton[selected="true"] {
                background-color: #EADDFF;
                color: #21005D;
                font-weight: 600;
            }
        """)
    
    def setup_responsive_layout(self):
        """设置响应式布局"""
        # 响应式布局逻辑
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernMainWindow()
    window.show()
    sys.exit(app.exec_())
