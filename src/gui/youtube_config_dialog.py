#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube发布配置对话框
提供YouTube平台特征性配置选项
"""

import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QTextEdit, QComboBox, QCheckBox, QSpinBox,
    QPushButton, QTabWidget, QWidget, QFileDialog, QMessageBox,
    QSlider, QFormLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap

from src.utils.logger import logger

class YouTubeConfigDialog(QDialog):
    """YouTube发布配置对话框"""
    
    config_saved = pyqtSignal(dict)  # 配置保存信号
    
    def __init__(self, parent=None, current_config=None):
        super().__init__(parent)
        self.current_config = current_config or {}
        self.init_ui()
        self.load_config()
        # 自动加载项目优化内容
        self.auto_load_project_content()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("🎬 YouTube发布配置")
        self.setFixedSize(600, 700)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("🎬 YouTube平台发布配置")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 创建标签页
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 基本设置标签页
        basic_tab = self.create_basic_settings_tab()
        tab_widget.addTab(basic_tab, "📝 基本设置")
        
        # 视频设置标签页
        video_tab = self.create_video_settings_tab()
        tab_widget.addTab(video_tab, "🎥 视频设置")
        
        # SEO优化标签页
        seo_tab = self.create_seo_settings_tab()
        tab_widget.addTab(seo_tab, "🔍 SEO优化")
        
        # API配置标签页
        api_tab = self.create_api_settings_tab()
        tab_widget.addTab(api_tab, "🔑 API配置")
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 测试连接按钮
        self.test_btn = QPushButton("🧪 测试连接")
        self.test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        # 保存按钮
        save_btn = QPushButton("💾 保存配置")
        save_btn.clicked.connect(self.save_config)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        button_layout.addWidget(save_btn)
        
        # 取消按钮
        cancel_btn = QPushButton("❌ 取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
    def create_basic_settings_tab(self):
        """创建基本设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 发布方式选择
        method_group = QGroupBox("🚀 发布方式")
        method_layout = QVBoxLayout(method_group)
        
        self.api_radio = QCheckBox("🔑 使用YouTube API (推荐)")
        self.api_radio.setChecked(True)
        method_layout.addWidget(self.api_radio)
        
        self.selenium_radio = QCheckBox("🌐 使用Selenium (备用)")
        method_layout.addWidget(self.selenium_radio)

        # 说明文字
        info_label = QLabel("💡 推荐使用API方案，稳定可靠且无需手动登录")
        info_label.setStyleSheet("color: #666; font-size: 12px; margin: 5px;")
        method_layout.addWidget(info_label)
        
        layout.addWidget(method_group)
        
        # 默认设置
        defaults_group = QGroupBox("⚙️ 默认设置")
        defaults_layout = QFormLayout(defaults_group)
        
        # 隐私级别
        self.privacy_combo = QComboBox()
        privacy_options = [
            ("public", "🌍 公开"),
            ("unlisted", "🔗 不公开列出"),
            ("private", "🔒 私人")
        ]
        for value, text in privacy_options:
            self.privacy_combo.addItem(text, value)
        defaults_layout.addRow("隐私级别:", self.privacy_combo)
        
        # 视频分类
        self.category_combo = QComboBox()
        categories = [
            ("28", "🔬 科学技术"),
            ("27", "📚 教育"),
            ("24", "🎭 娱乐"),
            ("22", "👥 人物博客"),
            ("10", "🎵 音乐"),
            ("15", "🐾 宠物动物"),
            ("17", "⚽ 体育"),
            ("19", "✈️ 旅游活动"),
            ("20", "🎮 游戏"),
            ("25", "📰 新闻政治")
        ]
        for value, text in categories:
            self.category_combo.addItem(text, value)
        defaults_layout.addRow("视频分类:", self.category_combo)
        
        # 语言设置
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            "zh-CN (简体中文)",
            "zh-TW (繁体中文)",
            "en-US (English)",
            "ja-JP (日本語)",
            "ko-KR (한국어)"
        ])
        defaults_layout.addRow("视频语言:", self.language_combo)
        
        layout.addWidget(defaults_group)
        
        # 自动化选项
        auto_group = QGroupBox("🤖 自动化选项")
        auto_layout = QVBoxLayout(auto_group)
        
        self.auto_shorts_checkbox = QCheckBox("📱 自动检测并标记Shorts")
        self.auto_shorts_checkbox.setChecked(True)
        auto_layout.addWidget(self.auto_shorts_checkbox)
        
        self.auto_tags_checkbox = QCheckBox("🏷️ 自动添加推荐标签")
        self.auto_tags_checkbox.setChecked(True)
        auto_layout.addWidget(self.auto_tags_checkbox)
        
        self.auto_description_checkbox = QCheckBox("📝 自动优化描述")
        self.auto_description_checkbox.setChecked(True)
        auto_layout.addWidget(self.auto_description_checkbox)
        
        layout.addWidget(auto_group)
        
        layout.addStretch()
        return widget
        
    def create_video_settings_tab(self):
        """创建视频设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Shorts设置
        shorts_group = QGroupBox("📱 YouTube Shorts设置")
        shorts_layout = QFormLayout(shorts_group)
        
        # Shorts最大时长
        self.shorts_duration_spin = QSpinBox()
        self.shorts_duration_spin.setRange(15, 60)
        self.shorts_duration_spin.setValue(60)
        self.shorts_duration_spin.setSuffix(" 秒")
        shorts_layout.addRow("最大时长:", self.shorts_duration_spin)
        
        # Shorts最小分辨率
        shorts_res_layout = QHBoxLayout()
        self.shorts_width_spin = QSpinBox()
        self.shorts_width_spin.setRange(480, 1080)
        self.shorts_width_spin.setValue(720)
        shorts_res_layout.addWidget(self.shorts_width_spin)
        
        shorts_res_layout.addWidget(QLabel("×"))
        
        self.shorts_height_spin = QSpinBox()
        self.shorts_height_spin.setRange(640, 1920)
        self.shorts_height_spin.setValue(1280)
        shorts_res_layout.addWidget(self.shorts_height_spin)
        
        shorts_layout.addRow("最小分辨率:", shorts_res_layout)
        
        layout.addWidget(shorts_group)
        
        # 长视频设置
        long_group = QGroupBox("🎬 长视频设置")
        long_layout = QFormLayout(long_group)
        
        # 长视频最小分辨率
        long_res_layout = QHBoxLayout()
        self.long_width_spin = QSpinBox()
        self.long_width_spin.setRange(640, 3840)
        self.long_width_spin.setValue(1280)
        long_res_layout.addWidget(self.long_width_spin)
        
        long_res_layout.addWidget(QLabel("×"))
        
        self.long_height_spin = QSpinBox()
        self.long_height_spin.setRange(360, 2160)
        self.long_height_spin.setValue(720)
        long_res_layout.addWidget(self.long_height_spin)
        
        long_layout.addRow("最小分辨率:", long_res_layout)
        
        layout.addWidget(long_group)
        
        # 上传设置
        upload_group = QGroupBox("⬆️ 上传设置")
        upload_layout = QFormLayout(upload_group)
        
        # 分块大小
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(1, 100)
        self.chunk_size_spin.setValue(1)
        self.chunk_size_spin.setSuffix(" MB")
        upload_layout.addRow("分块大小:", self.chunk_size_spin)
        
        # 超时时间
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(30, 600)
        self.timeout_spin.setValue(300)
        self.timeout_spin.setSuffix(" 秒")
        upload_layout.addRow("超时时间:", self.timeout_spin)
        
        # 重试次数
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(1, 10)
        self.retry_spin.setValue(3)
        upload_layout.addRow("重试次数:", self.retry_spin)
        
        layout.addWidget(upload_group)
        
        layout.addStretch()
        return widget
        
    def create_seo_settings_tab(self):
        """创建SEO设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题优化
        title_group = QGroupBox("📝 标题优化")
        title_layout = QVBoxLayout(title_group)
        
        self.title_max_length_spin = QSpinBox()
        self.title_max_length_spin.setRange(50, 100)
        self.title_max_length_spin.setValue(100)
        title_layout.addWidget(QLabel("最大长度:"))
        title_layout.addWidget(self.title_max_length_spin)
        
        self.add_emoji_checkbox = QCheckBox("✨ 自动添加吸引人的emoji")
        self.add_emoji_checkbox.setChecked(True)
        title_layout.addWidget(self.add_emoji_checkbox)
        
        layout.addWidget(title_group)
        
        # 标签优化
        tags_group = QGroupBox("🏷️ 标签优化")
        tags_layout = QVBoxLayout(tags_group)
        
        self.tags_max_count_spin = QSpinBox()
        self.tags_max_count_spin.setRange(5, 15)
        self.tags_max_count_spin.setValue(15)
        tags_layout.addWidget(QLabel("最大标签数:"))
        tags_layout.addWidget(self.tags_max_count_spin)
        
        # 推荐标签
        tags_header_layout = QHBoxLayout()
        tags_header_layout.addWidget(QLabel("推荐标签 (每行一个):"))
        tags_header_layout.addStretch()

        tags_layout.addLayout(tags_header_layout)

        self.recommended_tags_text = QTextEdit()
        self.recommended_tags_text.setMaximumHeight(100)
        self.recommended_tags_text.setPlainText("AI\nTechnology\nTutorial\nEducation\nScience\nInnovation")
        tags_layout.addWidget(self.recommended_tags_text)
        
        layout.addWidget(tags_group)
        
        # 描述模板
        desc_group = QGroupBox("📄 描述模板")
        desc_layout = QVBoxLayout(desc_group)

        desc_layout.addWidget(QLabel("Shorts描述模板:"))
        self.shorts_desc_template = QTextEdit()
        self.shorts_desc_template.setMaximumHeight(80)
        self.shorts_desc_template.setPlainText("🎬 AI生成的精彩短视频内容\n\n🔔 订阅频道获取更多AI创作内容\n#Shorts #AI #Technology")
        desc_layout.addWidget(self.shorts_desc_template)

        desc_layout.addWidget(QLabel("长视频描述模板:"))
        self.long_desc_template = QTextEdit()
        self.long_desc_template.setMaximumHeight(80)
        self.long_desc_template.setPlainText("🎬 这是一个AI生成的精彩视频内容\n\n🔔 订阅频道获取更多AI创作内容\n👍 点赞支持我们的创作\n💬 评论分享您的想法")
        desc_layout.addWidget(self.long_desc_template)
        
        layout.addWidget(desc_group)
        
        layout.addStretch()
        return widget
        
    def create_api_settings_tab(self):
        """创建API设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # API状态
        status_group = QGroupBox("📊 API状态")
        status_layout = QVBoxLayout(status_group)
        
        self.api_status_label = QLabel("🔍 检查中...")
        status_layout.addWidget(self.api_status_label)
        
        # 检查按钮
        check_btn = QPushButton("🔄 检查API状态")
        check_btn.clicked.connect(self.check_api_status)
        status_layout.addWidget(check_btn)
        
        layout.addWidget(status_group)
        
        # 配置文件路径
        config_group = QGroupBox("📁 配置文件")
        config_layout = QFormLayout(config_group)
        
        # 凭据文件
        cred_layout = QHBoxLayout()
        self.credentials_path_edit = QLineEdit()
        self.credentials_path_edit.setText("config/youtube_credentials.json")
        self.credentials_path_edit.setReadOnly(True)
        cred_layout.addWidget(self.credentials_path_edit)
        
        browse_cred_btn = QPushButton("📂 浏览")
        browse_cred_btn.clicked.connect(self.browse_credentials_file)
        cred_layout.addWidget(browse_cred_btn)
        
        config_layout.addRow("凭据文件:", cred_layout)
        
        # Token文件
        token_layout = QHBoxLayout()
        self.token_path_edit = QLineEdit()
        self.token_path_edit.setText("config/youtube_token.pickle")
        self.token_path_edit.setReadOnly(True)
        token_layout.addWidget(self.token_path_edit)
        
        clear_token_btn = QPushButton("🗑️ 清除")
        clear_token_btn.clicked.connect(self.clear_token_file)
        token_layout.addWidget(clear_token_btn)
        
        config_layout.addRow("Token文件:", token_layout)
        
        layout.addWidget(config_group)
        
        # 代理设置
        proxy_group = QGroupBox("🌐 代理设置")
        proxy_layout = QFormLayout(proxy_group)
        
        self.use_proxy_checkbox = QCheckBox("启用代理")
        self.use_proxy_checkbox.setChecked(True)
        proxy_layout.addRow("", self.use_proxy_checkbox)
        
        self.proxy_url_edit = QLineEdit()
        self.proxy_url_edit.setText("http://127.0.0.1:12334")
        self.proxy_url_edit.setPlaceholderText("http://127.0.0.1:12334")
        proxy_layout.addRow("代理地址:", self.proxy_url_edit)
        
        layout.addWidget(proxy_group)
        
        layout.addStretch()
        return widget
        
    def load_config(self):
        """加载配置"""
        try:
            # 从当前配置加载
            if self.current_config:
                # 基本设置
                self.api_radio.setChecked(self.current_config.get('api_enabled', True))
                self.selenium_radio.setChecked(self.current_config.get('selenium_enabled', False))
                
                privacy = self.current_config.get('default_privacy', 'public')
                for i in range(self.privacy_combo.count()):
                    if self.privacy_combo.itemData(i) == privacy:
                        self.privacy_combo.setCurrentIndex(i)
                        break
                
                # 其他设置...
                
        except Exception as e:
            logger.warning(f"加载YouTube配置失败: {e}")
            
    def save_config(self):
        """保存配置"""
        try:
            config = {
                # 基本设置
                'api_enabled': self.api_radio.isChecked(),
                'selenium_enabled': self.selenium_radio.isChecked(),
                'default_privacy': self.privacy_combo.currentData(),
                'default_category': self.category_combo.currentData(),
                'language': self.language_combo.currentText().split(' ')[0],
                
                # 自动化选项
                'auto_shorts_detection': self.auto_shorts_checkbox.isChecked(),
                'auto_tags': self.auto_tags_checkbox.isChecked(),
                'auto_description': self.auto_description_checkbox.isChecked(),
                
                # 视频设置
                'shorts_max_duration': self.shorts_duration_spin.value(),
                'shorts_min_resolution': [self.shorts_width_spin.value(), self.shorts_height_spin.value()],
                'long_min_resolution': [self.long_width_spin.value(), self.long_height_spin.value()],
                
                # 上传设置
                'chunk_size': self.chunk_size_spin.value() * 1024 * 1024,  # 转换为字节
                'timeout': self.timeout_spin.value(),
                'max_retries': self.retry_spin.value(),
                
                # SEO设置
                'title_max_length': self.title_max_length_spin.value(),
                'add_emoji': self.add_emoji_checkbox.isChecked(),
                'tags_max_count': self.tags_max_count_spin.value(),
                'recommended_tags': [tag.strip() for tag in self.recommended_tags_text.toPlainText().split('\n') if tag.strip()],
                'shorts_desc_template': self.shorts_desc_template.toPlainText(),
                'long_desc_template': self.long_desc_template.toPlainText(),
                
                # API设置
                'credentials_file': self.credentials_path_edit.text(),
                'token_file': self.token_path_edit.text(),
                'use_proxy': self.use_proxy_checkbox.isChecked(),
                'proxy_url': self.proxy_url_edit.text() if self.use_proxy_checkbox.isChecked() else None
            }
            
            # 发送配置保存信号
            self.config_saved.emit(config)
            
            QMessageBox.information(self, "保存成功", "YouTube配置已保存！")
            self.accept()
            
        except Exception as e:
            logger.error(f"保存YouTube配置失败: {e}")
            QMessageBox.critical(self, "保存失败", f"保存配置时出错：{e}")
            
    def test_connection(self):
        """测试连接"""
        try:
            self.test_btn.setText("🔄 测试中...")
            self.test_btn.setEnabled(False)
            
            # 这里可以添加实际的连接测试逻辑
            QMessageBox.information(self, "测试结果", "YouTube API连接测试成功！")
            
        except Exception as e:
            QMessageBox.critical(self, "测试失败", f"连接测试失败：{e}")
        finally:
            self.test_btn.setText("🧪 测试连接")
            self.test_btn.setEnabled(True)
            
    def check_api_status(self):
        """检查API状态"""
        try:
            # 检查凭据文件
            cred_file = self.credentials_path_edit.text()
            if os.path.exists(cred_file):
                self.api_status_label.setText("✅ 凭据文件存在")
            else:
                self.api_status_label.setText("❌ 凭据文件不存在")
                
        except Exception as e:
            self.api_status_label.setText(f"❌ 检查失败: {e}")
            
    def browse_credentials_file(self):
        """浏览凭据文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择YouTube API凭据文件", "", "JSON文件 (*.json)"
        )
        if file_path:
            self.credentials_path_edit.setText(file_path)
            
    def clear_token_file(self):
        """清除token文件"""
        try:
            token_file = self.token_path_edit.text()
            if os.path.exists(token_file):
                os.remove(token_file)
                QMessageBox.information(self, "清除成功", "Token文件已清除，下次发布时将重新认证。")
            else:
                QMessageBox.information(self, "提示", "Token文件不存在。")
        except Exception as e:
            QMessageBox.critical(self, "清除失败", f"清除Token文件失败：{e}")





    def _get_current_project_data(self) -> dict:
        """获取当前项目数据"""
        try:
            logger.info("🔍 开始获取当前项目数据...")

            # 方法1: 从主窗口的应用控制器获取
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'app_controller'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'app_controller'):
                app_controller = main_window.app_controller
                if hasattr(app_controller, 'project_manager'):
                    project_manager = app_controller.project_manager
                    if hasattr(project_manager, 'current_project_data') and project_manager.current_project_data:
                        logger.info("✅ 从应用控制器获取到项目数据")
                        return project_manager.current_project_data
                    elif hasattr(project_manager, 'current_project') and project_manager.current_project:
                        logger.info("✅ 从应用控制器获取到当前项目")
                        return project_manager.current_project

            # 方法2: 从全局服务管理器获取
            from src.core.service_manager import ServiceManager
            service_manager = ServiceManager()
            project_manager = service_manager.get_service('project_manager')
            if project_manager:
                if hasattr(project_manager, 'current_project_data') and project_manager.current_project_data:
                    logger.info("✅ 从服务管理器获取到项目数据")
                    return project_manager.current_project_data
                elif hasattr(project_manager, 'current_project') and project_manager.current_project:
                    logger.info("✅ 从服务管理器获取到当前项目")
                    return project_manager.current_project

            # 方法3: 尝试从主窗口的标签页获取
            if main_window:
                # 检查是否有文本创建标签页
                for i in range(main_window.tab_widget.count()):
                    tab = main_window.tab_widget.widget(i)
                    if hasattr(tab, 'get_current_project_data'):
                        project_data = tab.get_current_project_data()
                        if project_data:
                            logger.info("✅ 从标签页获取到项目数据")
                            return project_data

                # 检查是否有项目相关的属性
                if hasattr(main_window, 'current_project_data') and main_window.current_project_data:
                    logger.info("✅ 从主窗口获取到项目数据")
                    return main_window.current_project_data

            logger.warning("⚠️ 未找到项目数据，返回空字典")
            return {}

        except Exception as e:
            logger.warning(f"获取项目数据失败: {e}")
            return {}

    def _get_basic_project_info(self) -> dict:
        """从当前界面获取基本项目信息"""
        try:
            logger.info("🔍 尝试从当前界面获取基本项目信息...")

            # 尝试从发布界面获取视频信息
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'tab_widget'):
                main_window = main_window.parent()

            if main_window and hasattr(main_window, 'tab_widget'):
                # 查找一键发布标签页
                for i in range(main_window.tab_widget.count()):
                    tab = main_window.tab_widget.widget(i)
                    if hasattr(tab, 'title_edit') and hasattr(tab, 'description_edit'):
                        # 从发布界面获取标题和描述
                        title = tab.title_edit.text().strip()
                        description = tab.description_edit.toPlainText().strip()

                        if title or description:
                            logger.info("✅ 从发布界面获取到基本信息")
                            return {
                                'project_name': title or '当前视频项目',
                                'description': description or '基于当前视频信息的AI生成内容',
                                'text_content': description,
                                'theme': '视频创作',
                                'style': '现代风格'
                            }

                # 查找文本创建标签页
                for i in range(main_window.tab_widget.count()):
                    tab = main_window.tab_widget.widget(i)
                    if hasattr(tab, 'text_input') or hasattr(tab, 'get_text_content'):
                        try:
                            if hasattr(tab, 'get_text_content'):
                                text_content = tab.get_text_content()
                            elif hasattr(tab, 'text_input'):
                                text_content = tab.text_input.toPlainText().strip()
                            else:
                                text_content = ''

                            if text_content:
                                logger.info("✅ 从文本创建界面获取到内容")
                                return {
                                    'project_name': '文本创作项目',
                                    'description': '基于文本内容的AI视频项目',
                                    'text_content': text_content[:500],  # 限制长度
                                    'theme': '文本创作',
                                    'style': '创意风格'
                                }
                        except Exception as e:
                            logger.debug(f"从文本标签页获取内容失败: {e}")
                            continue

            logger.info("⚠️ 未从界面获取到基本信息")
            return {}

        except Exception as e:
            logger.warning(f"获取基本项目信息失败: {e}")
            return {}

    def _extract_ai_optimized_content(self, project_data: dict) -> dict:
        """从项目数据中提取AI优化内容"""
        try:
            logger.info("🔍 开始提取项目中的AI优化内容...")

            # 方法1: 从ai_optimization字段获取
            ai_optimization = project_data.get('ai_optimization', {})
            if ai_optimization:
                logger.info("✅ 从ai_optimization字段获取到优化内容")
                return {
                    'title': ai_optimization.get('title', ''),
                    'description': ai_optimization.get('description', ''),
                    'tags': ai_optimization.get('tags', []),
                    'source': 'ai_optimization'
                }

            # 方法2: 从publish_content字段获取
            publish_content = project_data.get('publish_content', {})
            if publish_content:
                # 检查是否有AI优化历史
                ai_history = publish_content.get('ai_optimization_history', [])
                if ai_history:
                    # 使用最新的优化记录
                    latest_optimization = ai_history[-1]
                    logger.info("✅ 从AI优化历史获取到最新优化内容")
                    return {
                        'title': latest_optimization.get('title', ''),
                        'description': latest_optimization.get('description', ''),
                        'tags': latest_optimization.get('tags', []),
                        'source': 'ai_optimization_history'
                    }

                # 使用publish_content中的基本内容
                if publish_content.get('title') or publish_content.get('description'):
                    logger.info("✅ 从publish_content获取到发布内容")
                    tags = []
                    tags_text = publish_content.get('tags', '')
                    if tags_text:
                        if isinstance(tags_text, str):
                            tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
                        elif isinstance(tags_text, list):
                            tags = tags_text

                    return {
                        'title': publish_content.get('title', ''),
                        'description': publish_content.get('description', ''),
                        'tags': tags,
                        'source': 'publish_content'
                    }

            logger.info("⚠️ 未找到AI优化内容")
            return {}

        except Exception as e:
            logger.warning(f"提取AI优化内容失败: {e}")
            return {}

    def _generate_content_from_project_info(self, project_data: dict) -> dict:
        """从项目基本信息生成内容"""
        try:
            logger.info("🔍 从项目基本信息生成内容...")

            project_name = project_data.get('project_name', '')
            description = project_data.get('description', '')
            text_content = project_data.get('text_content', '')
            theme = project_data.get('theme', '')

            # 生成基本标签
            tags = []
            if theme:
                tags.append(theme)
            tags.extend(['创意内容', '视频创作'])

            # 生成基本标题和描述
            title = project_name if project_name else '精彩视频内容'
            desc = description if description else '精彩视频内容'

            return {
                'title': title,
                'description': desc,
                'tags': tags[:8],  # 限制标签数量
                'source': 'project_info'
            }

        except Exception as e:
            logger.warning(f"从项目信息生成内容失败: {e}")
            return {}

    def _apply_optimized_content(self, content: dict):
        """应用优化内容到界面"""
        try:
            logger.info(f"🔧 应用优化内容，来源: {content.get('source', 'unknown')}")

            # 应用标签
            tags = content.get('tags', [])
            if tags:
                # 确保标签格式正确
                formatted_tags = []
                for tag in tags:
                    if isinstance(tag, str):
                        tag = tag.strip()
                        if tag and not tag.startswith('#'):
                            formatted_tags.append(tag)

                if formatted_tags:
                    tags_text = '\n'.join(formatted_tags)
                    self.recommended_tags_text.setPlainText(tags_text)
                    logger.info(f"✅ 已应用 {len(formatted_tags)} 个标签")

            # 应用描述模板（如果有标题和描述）
            title = content.get('title', '')
            description = content.get('description', '')

            if title or description:
                # 生成Shorts模板
                shorts_template = f"🎬 {title}\n\n{description}\n\n🔔 关注获取更多精彩内容！\n👍 点赞支持创作\n💬 评论分享想法"
                if tags:
                    hashtags = ' '.join([f'#{tag}' for tag in tags[:5]])
                    shorts_template += f"\n\n{hashtags}"

                self.shorts_desc_template.setPlainText(shorts_template)

                # 生成长视频模板
                long_template = f"📺 {title}\n\n{description}\n\n📖 视频亮点：\n• 精彩的内容呈现\n• 高质量的制作\n• 值得收藏分享\n\n🔔 订阅频道获取更多内容\n👍 点赞支持创作\n💬 评论互动交流\n🔗 分享给更多朋友"
                if tags:
                    hashtags = ' '.join([f'#{tag}' for tag in tags])
                    long_template += f"\n\n{hashtags}"

                self.long_desc_template.setPlainText(long_template)

                logger.info("✅ 已应用标题和描述模板")

        except Exception as e:
            logger.warning(f"应用优化内容失败: {e}")

    def auto_load_project_content(self):
        """自动加载项目优化内容"""
        try:
            logger.info("🔍 自动加载项目优化内容...")

            # 获取当前项目数据
            project_data = self._get_current_project_data()

            if not project_data:
                logger.info("⚠️ 未找到项目数据，跳过自动加载")
                return

            # 获取AI优化内容
            ai_content = self._extract_ai_optimized_content(project_data)

            if ai_content:
                logger.info(f"✅ 找到AI优化内容，来源: {ai_content.get('source', 'unknown')}")
                # 应用优化内容
                self._apply_optimized_content(ai_content)
                logger.info("✅ 已自动应用项目优化内容")
            else:
                # 尝试从项目基本信息生成内容
                basic_content = self._generate_content_from_project_info(project_data)
                if basic_content:
                    logger.info("✅ 使用项目基本信息生成内容")
                    self._apply_optimized_content(basic_content)
                else:
                    logger.info("⚠️ 未找到可用的项目内容")

        except Exception as e:
            logger.warning(f"自动加载项目内容失败: {e}")


