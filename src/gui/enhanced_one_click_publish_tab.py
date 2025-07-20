#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版一键发布标签页
集成自动浏览器管理，减少用户配置依赖
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTextEdit, QLineEdit, QCheckBox,
    QProgressBar, QGroupBox, QScrollArea, QFrame,
    QMessageBox, QFileDialog, QComboBox, QSpinBox,
    QTabWidget, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap

from src.services.platform_publisher.integrated_browser_manager import IntegratedBrowserManager
from src.services.platform_publisher.selenium_publisher_factory import selenium_publisher_manager
from src.services.platform_publisher.base_publisher import VideoMetadata
from src.services.platform_publisher.login_manager import login_manager
from src.gui.platform_login_widget import PlatformLoginWidget
from src.utils.logger import logger

# 🔧 新增：AI优化相关导入
try:
    from src.services.service_manager import ServiceManager
    from src.services.content_optimizer import ContentOptimizer
    AI_OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AI优化服务不可用: {e}")
    AI_OPTIMIZATION_AVAILABLE = False


class AIOptimizeWorker(QThread):
    """AI优化工作线程"""
    optimization_completed = pyqtSignal(object)  # 优化结果
    optimization_failed = pyqtSignal(str)  # 错误信息

    def __init__(self, content_optimizer, title, description, platforms):
        super().__init__()
        self.content_optimizer = content_optimizer
        self.title = title
        self.description = description
        self.platforms = platforms

    def run(self):
        """执行AI优化"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 执行优化
            result = loop.run_until_complete(
                self.content_optimizer.optimize_content(
                    title=self.title,
                    description=self.description,
                    platforms=self.platforms
                )
            )

            self.optimization_completed.emit(result)

        except Exception as e:
            logger.error(f"AI优化工作线程错误: {e}")
            self.optimization_failed.emit(str(e))
        finally:
            loop.close()


class BrowserSetupThread(QThread):
    """浏览器设置线程"""
    setup_finished = pyqtSignal(dict)
    setup_progress = pyqtSignal(str)
    
    def __init__(self, preferred_browser='chrome'):
        super().__init__()
        self.preferred_browser = preferred_browser
        self.browser_manager = IntegratedBrowserManager()
        
    def run(self):
        try:
            self.setup_progress.emit("🔍 检测系统浏览器...")
            
            # 自动设置浏览器环境
            result = self.browser_manager.auto_setup_and_start(self.preferred_browser)
            
            self.setup_finished.emit(result)
            
        except Exception as e:
            logger.error(f"浏览器设置线程异常: {e}")
            self.setup_finished.emit({
                'success': False,
                'error': f'浏览器设置失败: {e}'
            })


class PublishThread(QThread):
    """发布线程"""
    publish_progress = pyqtSignal(str, str)  # platform, message
    publish_finished = pyqtSignal(dict)
    
    def __init__(self, platforms, video_info, selenium_config):
        super().__init__()
        self.platforms = platforms
        self.video_info = video_info
        self.selenium_config = selenium_config
        
    def run(self):
        try:
            # 配置Selenium发布器
            selenium_publisher_manager.set_config(self.selenium_config)
            
            results = {}
            
            for platform in self.platforms:
                self.publish_progress.emit(platform, f"开始发布到{platform}...")
                
                # 执行发布
                result = asyncio.run(
                    selenium_publisher_manager.publish_video(platform, self.video_info)
                )
                
                results[platform] = result
                
                if result.get('success'):
                    self.publish_progress.emit(platform, "✅ 发布成功")
                else:
                    error_msg = result.get('error', '未知错误')
                    self.publish_progress.emit(platform, f"❌ 发布失败: {error_msg}")
                    
            self.publish_finished.emit(results)
            
        except Exception as e:
            logger.error(f"发布线程异常: {e}")
            self.publish_finished.emit({
                'error': f'发布过程异常: {e}'
            })


class EnhancedOneClickPublishTab(QWidget):
    """增强版一键发布标签页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.browser_manager = IntegratedBrowserManager()
        self.browser_config = None
        self.setup_thread = None
        self.publish_thread = None

        # 🔧 新增：初始化AI优化服务
        self.service_manager = None
        self.content_optimizer = None
        self.ai_worker = None

        if AI_OPTIMIZATION_AVAILABLE:
            try:
                self.service_manager = ServiceManager()
                llm_service = self.service_manager.get_service('llm')
                self.content_optimizer = ContentOptimizer(llm_service)
                logger.info("✅ AI优化服务初始化成功")
            except Exception as e:
                logger.warning(f"AI优化服务初始化失败: {e}")
                self.content_optimizer = None

        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("🚀 增强版一键发布")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 创建标签页
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # 浏览器设置标签页
        browser_tab = self.create_browser_setup_tab()
        tab_widget.addTab(browser_tab, "🔧 浏览器设置")

        # 登录管理标签页
        self.login_widget = PlatformLoginWidget(self)
        tab_widget.addTab(self.login_widget, "🔐 登录管理")

        # 发布配置标签页
        publish_tab = self.create_publish_config_tab()
        tab_widget.addTab(publish_tab, "🚀 发布配置")

        # 状态监控标签页
        status_tab = self.create_status_tab()
        tab_widget.addTab(status_tab, "📊 发布状态")
        
    def create_browser_setup_tab(self) -> QWidget:
        """创建浏览器设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # 浏览器设置组
        browser_group = QGroupBox("🌐 浏览器环境设置")
        browser_layout = QVBoxLayout(browser_group)

        # 浏览器选择
        browser_select_layout = QHBoxLayout()
        browser_select_layout.addWidget(QLabel("首选浏览器:"))

        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Chrome", "Edge", "Firefox"])
        browser_select_layout.addWidget(self.browser_combo)

        self.auto_setup_btn = QPushButton("🔧 自动设置浏览器")
        self.auto_setup_btn.clicked.connect(self.auto_setup_browser)
        browser_select_layout.addWidget(self.auto_setup_btn)

        browser_layout.addLayout(browser_select_layout)

        # 浏览器状态
        self.browser_status_label = QLabel("❌ 浏览器未配置")
        browser_layout.addWidget(self.browser_status_label)

        # 设置指南按钮
        self.show_guide_btn = QPushButton("📖 查看设置指南")
        self.show_guide_btn.clicked.connect(self.show_setup_guide)
        browser_layout.addWidget(self.show_guide_btn)

        layout.addWidget(browser_group)
        layout.addStretch()

        return widget

    def create_publish_config_tab(self) -> QWidget:
        """创建发布配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # 🔧 新增：AI优化组
        ai_group = QGroupBox("🎯 AI内容优化")
        ai_layout = QVBoxLayout(ai_group)

        # AI优化按钮行
        ai_button_row = QHBoxLayout()

        self.ai_optimize_button = QPushButton("🎯 AI优化内容")
        self.ai_optimize_button.clicked.connect(self.optimize_content_with_ai)
        self.ai_optimize_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        self.ai_status_label = QLabel()
        self.ai_status_label.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")

        ai_button_row.addWidget(self.ai_optimize_button)
        ai_button_row.addWidget(self.ai_status_label)
        ai_button_row.addStretch()

        ai_layout.addLayout(ai_button_row)
        layout.addWidget(ai_group)

        # 视频信息组
        video_group = QGroupBox("📹 视频信息")
        video_layout = QVBoxLayout(video_group)

        # 视频文件选择
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("视频文件:"))

        self.video_path_edit = QLineEdit()
        self.video_path_edit.setPlaceholderText("选择要发布的视频文件...")
        file_layout.addWidget(self.video_path_edit)

        self.select_file_btn = QPushButton("📁 选择文件")
        self.select_file_btn.clicked.connect(self.select_video_file)
        file_layout.addWidget(self.select_file_btn)

        video_layout.addLayout(file_layout)

        # 视频标题
        video_layout.addWidget(QLabel("📝 标题:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("AI将基于项目内容自动生成标题...")
        self.title_edit.setMinimumHeight(35)
        video_layout.addWidget(self.title_edit)

        # 视频描述
        video_layout.addWidget(QLabel("📄 描述:"))
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("AI将基于项目内容自动生成描述...")
        self.description_edit.setMaximumHeight(100)
        video_layout.addWidget(self.description_edit)

        # 标签
        video_layout.addWidget(QLabel("🏷️ 标签 (用逗号分隔):"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("AI将基于项目内容自动生成标签...")
        self.tags_edit.setMinimumHeight(35)
        video_layout.addWidget(self.tags_edit)

        layout.addWidget(video_group)
        # 平台选择组
        platform_group = QGroupBox("🎯 发布平台选择")
        platform_layout = QVBoxLayout(platform_group)

        # 登录状态提示
        self.login_status_label = QLabel("💡 请先在'登录管理'标签页中登录各平台账号")
        self.login_status_label.setStyleSheet("color: #007acc; font-weight: bold;")
        platform_layout.addWidget(self.login_status_label)

        # 平台复选框
        platforms_grid = QGridLayout()

        self.platform_checkboxes = {}
        platforms = [
            ('douyin', '🎵 抖音', 0, 0),
            ('bilibili', '📺 B站', 0, 1),
            ('kuaishou', '⚡ 快手', 1, 0),
            ('xiaohongshu', '📖 小红书', 1, 1),
            ('youtube', '🎬 YouTube', 2, 0),
            ('wechat', '💬 微信视频号', 2, 1)
        ]

        for platform_id, platform_name, row, col in platforms:
            checkbox = QCheckBox(platform_name)
            self.platform_checkboxes[platform_id] = checkbox
            platforms_grid.addWidget(checkbox, row, col)

        # 单独为YouTube添加配置按钮
        youtube_config_btn = QPushButton("⚙️配置")
        youtube_config_btn.setMaximumWidth(60)
        youtube_config_btn.setMaximumHeight(30)
        youtube_config_btn.setToolTip("YouTube发布配置")
        youtube_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        youtube_config_btn.clicked.connect(self.show_youtube_config)
        platforms_grid.addWidget(youtube_config_btn, 2, 2)  # YouTube在第2行第0列，配置按钮在第2行第2列

        platform_layout.addLayout(platforms_grid)

        # 发布选项
        options_layout = QHBoxLayout()

        self.simulation_checkbox = QCheckBox("🎭 模拟模式 (测试)")
        options_layout.addWidget(self.simulation_checkbox)

        self.auto_publish_checkbox = QCheckBox("🚀 自动发布")
        self.auto_publish_checkbox.setChecked(True)
        options_layout.addWidget(self.auto_publish_checkbox)

        platform_layout.addLayout(options_layout)

        layout.addWidget(platform_group)

        # 发布按钮
        self.publish_btn = QPushButton("🚀 开始发布")
        self.publish_btn.clicked.connect(self.start_publish)
        self.publish_btn.setEnabled(False)
        self.publish_btn.setMinimumHeight(50)
        self.publish_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        layout.addWidget(self.publish_btn)

        layout.addStretch()
        return widget

    def create_status_tab(self) -> QWidget:
        """创建状态监控标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        # 状态组
        status_group = QGroupBox("📊 发布状态监控")
        status_layout = QVBoxLayout(status_group)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)

        # 状态表格
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(3)
        self.status_table.setHorizontalHeaderLabels(["平台", "状态", "消息"])

        # 设置表格属性
        header = self.status_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        self.status_table.setColumnWidth(0, 100)
        self.status_table.setColumnWidth(1, 100)

        self.status_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.status_table.setAlternatingRowColors(True)

        status_layout.addWidget(self.status_table)

        layout.addWidget(status_group)

        # 日志组
        log_group = QGroupBox("📝 详细日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        return widget

    def auto_setup_browser(self):
        """自动设置浏览器"""
        try:
            self.log_message("🔧 开始自动设置浏览器环境...")

            # 禁用按钮
            self.auto_setup_btn.setEnabled(False)
            self.auto_setup_btn.setText("⏳ 设置中...")

            # 获取首选浏览器
            preferred_browser = self.browser_combo.currentText().lower()

            # 启动设置线程
            self.setup_thread = BrowserSetupThread(preferred_browser)
            self.setup_thread.setup_progress.connect(self.on_setup_progress)
            self.setup_thread.setup_finished.connect(self.on_setup_finished)
            self.setup_thread.start()

        except Exception as e:
            logger.error(f"启动浏览器设置失败: {e}")
            self.log_message(f"❌ 启动浏览器设置失败: {e}")
            self.auto_setup_btn.setEnabled(True)
            self.auto_setup_btn.setText("🔧 自动设置浏览器")

    def on_setup_progress(self, message: str):
        """设置进度更新"""
        self.log_message(message)

    def on_setup_finished(self, result: Dict[str, Any]):
        """设置完成"""
        try:
            self.auto_setup_btn.setEnabled(True)
            self.auto_setup_btn.setText("🔧 自动设置浏览器")

            if result['success']:
                self.browser_config = result

                # 更新状态显示
                browser_info = result['browser_info']
                debug_info = result['debug_info']

                status_text = f"✅ {browser_info['browser']} {browser_info['version']} (端口: {debug_info['port']})"
                self.browser_status_label.setText(status_text)

                # 启用发布按钮
                self.publish_btn.setEnabled(True)

                # 设置登录管理器的浏览器配置
                self.login_widget.set_browser_manager(self.browser_manager, result)

                self.log_message(result['message'])
                self.log_message("💡 现在可以在'登录管理'标签页中登录各平台账号")

                # 更新登录状态提示
                self.update_login_status_display()

                # 显示成功消息
                QMessageBox.information(
                    self,
                    "设置成功",
                    f"{browser_info['browser']}环境已就绪！\n\n"
                    f"请在弹出的浏览器中登录各平台账号，\n"
                    f"然后返回程序开始发布。"
                )

            else:
                error_msg = result.get('error', '未知错误')
                self.browser_status_label.setText(f"❌ 设置失败: {error_msg}")
                self.log_message(f"❌ 浏览器设置失败: {error_msg}")

                # 显示错误和建议
                suggestions = result.get('suggestions', [])
                if suggestions:
                    suggestion_text = "\n".join(suggestions)
                    QMessageBox.warning(
                        self,
                        "设置失败",
                        f"浏览器环境设置失败：\n{error_msg}\n\n"
                        f"建议解决方案：\n{suggestion_text}"
                    )

        except Exception as e:
            logger.error(f"处理设置结果失败: {e}")
            self.log_message(f"❌ 处理设置结果失败: {e}")

    def show_setup_guide(self):
        """显示设置指南"""
        guide = self.browser_manager.show_setup_guide()

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("浏览器环境设置指南")
        msg_box.setText(guide)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec_()

    def select_video_file(self):
        """选择视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv);;所有文件 (*)"
        )

        if file_path:
            self.video_path_edit.setText(file_path)
            self.log_message(f"📁 已选择视频文件: {Path(file_path).name}")

    def start_publish(self):
        """开始发布"""
        try:
            # 验证输入
            if not self.validate_inputs():
                return

            # 获取选中的平台
            selected_platforms = []
            for platform_id, checkbox in self.platform_checkboxes.items():
                if checkbox.isChecked():
                    selected_platforms.append(platform_id)

            if not selected_platforms:
                QMessageBox.warning(self, "警告", "请至少选择一个发布平台")
                return

            # 准备视频信息
            video_info = {
                'video_path': self.video_path_edit.text(),
                'title': self.title_edit.text(),
                'description': self.description_edit.toPlainText(),
                'tags': [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()],
                'category': '科技',
                'privacy': 'public',
                'auto_publish': self.auto_publish_checkbox.isChecked()
            }

            # 获取Selenium配置
            selenium_config = self.browser_config['selenium_config'].copy()
            selenium_config['simulation_mode'] = self.simulation_checkbox.isChecked()

            # 初始化状态表格
            self.init_status_table(selected_platforms)

            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 无限进度条

            # 禁用发布按钮
            self.publish_btn.setEnabled(False)
            self.publish_btn.setText("⏳ 发布中...")

            self.log_message(f"🚀 开始发布到 {len(selected_platforms)} 个平台...")

            # 启动发布线程
            self.publish_thread = PublishThread(selected_platforms, video_info, selenium_config)
            self.publish_thread.publish_progress.connect(self.on_publish_progress)
            self.publish_thread.publish_finished.connect(self.on_publish_finished)
            self.publish_thread.start()

        except Exception as e:
            logger.error(f"启动发布失败: {e}")
            self.log_message(f"❌ 启动发布失败: {e}")
            QMessageBox.critical(self, "错误", f"启动发布失败：{e}")

    def validate_inputs(self) -> bool:
        """验证输入"""
        if not self.browser_config:
            QMessageBox.warning(self, "警告", "请先设置浏览器环境")
            return False

        if not self.video_path_edit.text():
            QMessageBox.warning(self, "警告", "请选择视频文件")
            return False

        if not Path(self.video_path_edit.text()).exists():
            QMessageBox.warning(self, "警告", "视频文件不存在")
            return False

        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入视频标题")
            return False

        return True

    def init_status_table(self, platforms: list):
        """初始化状态表格"""
        self.status_table.setRowCount(len(platforms))

        platform_names = {
            'douyin': '抖音',
            'bilibili': 'B站',
            'kuaishou': '快手',
            'xiaohongshu': '小红书',
            'youtube': 'YouTube',
            'wechat': '微信视频号'
        }

        for i, platform in enumerate(platforms):
            # 平台名称
            platform_item = QTableWidgetItem(platform_names.get(platform, platform))
            self.status_table.setItem(i, 0, platform_item)

            # 状态
            status_item = QTableWidgetItem("⏳ 等待中")
            self.status_table.setItem(i, 1, status_item)

            # 消息
            message_item = QTableWidgetItem("准备发布...")
            self.status_table.setItem(i, 2, message_item)

    def on_publish_progress(self, platform: str, message: str):
        """发布进度更新"""
        self.log_message(f"[{platform}] {message}")

        # 更新状态表格
        for row in range(self.status_table.rowCount()):
            platform_item = self.status_table.item(row, 0)
            if platform_item and platform in platform_item.text().lower():
                # 更新状态
                if "成功" in message:
                    status_item = QTableWidgetItem("✅ 成功")
                elif "失败" in message:
                    status_item = QTableWidgetItem("❌ 失败")
                else:
                    status_item = QTableWidgetItem("⏳ 进行中")

                self.status_table.setItem(row, 1, status_item)

                # 更新消息
                message_item = QTableWidgetItem(message)
                self.status_table.setItem(row, 2, message_item)
                break

    def on_publish_finished(self, results: Dict[str, Any]):
        """发布完成"""
        try:
            # 隐藏进度条
            self.progress_bar.setVisible(False)

            # 恢复发布按钮
            self.publish_btn.setEnabled(True)
            self.publish_btn.setText("🚀 开始发布")

            if 'error' in results:
                self.log_message(f"❌ 发布过程异常: {results['error']}")
                QMessageBox.critical(self, "发布失败", f"发布过程异常：{results['error']}")
                return

            # 统计结果
            success_count = sum(1 for result in results.values() if result.get('success'))
            total_count = len(results)

            self.log_message(f"📊 发布完成: {success_count}/{total_count} 成功")

            # 显示结果消息
            if success_count == total_count:
                QMessageBox.information(
                    self,
                    "发布成功",
                    f"🎉 所有平台发布成功！\n\n"
                    f"成功发布到 {success_count} 个平台"
                )
            elif success_count > 0:
                QMessageBox.warning(
                    self,
                    "部分成功",
                    f"⚠️ 部分平台发布成功\n\n"
                    f"成功: {success_count}/{total_count}\n"
                    f"请查看详细状态信息"
                )
            else:
                QMessageBox.critical(
                    self,
                    "发布失败",
                    f"❌ 所有平台发布失败\n\n"
                    f"请检查网络连接和账号登录状态"
                )

        except Exception as e:
            logger.error(f"处理发布结果失败: {e}")
            self.log_message(f"❌ 处理发布结果失败: {e}")

    def log_message(self, message: str):
        """记录日志消息"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        self.log_text.append(formatted_message)

        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

    def show_youtube_config(self):
        """显示YouTube配置对话框"""
        try:
            from .youtube_config_dialog import YouTubeConfigDialog

            # 加载当前YouTube配置
            current_config = self.load_youtube_config()

            dialog = YouTubeConfigDialog(self, current_config)
            dialog.config_saved.connect(self.save_youtube_config)

            if dialog.exec_() == QDialog.Accepted:
                self.log_message("✅ YouTube配置已更新")

        except Exception as e:
            logger.error(f"显示YouTube配置对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"无法打开YouTube配置：{e}")

    def load_youtube_config(self) -> dict:
        """加载YouTube配置"""
        try:
            config_file = "config/youtube_ui_config.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"加载YouTube配置失败: {e}")
            return {}

    def save_youtube_config(self, config: dict):
        """保存YouTube配置"""
        try:
            # 确保配置目录存在
            os.makedirs("config", exist_ok=True)

            # 保存UI配置
            config_file = "config/youtube_ui_config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            # 更新YouTube发布器配置
            self.update_youtube_publisher_config(config)

            logger.info("YouTube配置已保存")

        except Exception as e:
            logger.error(f"保存YouTube配置失败: {e}")
            QMessageBox.critical(self, "保存失败", f"保存YouTube配置失败：{e}")

    def update_youtube_publisher_config(self, config: dict):
        """更新YouTube发布器配置"""
        try:
            # 更新YouTube配置文件
            youtube_config_file = "config/youtube_config.py"

            # 这里可以动态更新配置文件
            # 或者通过其他方式传递配置给发布器

            logger.info("YouTube发布器配置已更新")

        except Exception as e:
            logger.warning(f"更新YouTube发布器配置失败: {e}")

    def update_login_status_display(self):
        """更新登录状态显示"""
        try:
            logged_in_platforms = self.login_widget.get_logged_in_platforms()

            if logged_in_platforms:
                platform_names = []
                for platform_id in logged_in_platforms:
                    platform_config = login_manager.platforms.get(platform_id, {})
                    platform_names.append(platform_config.get('name', platform_id))

                status_text = f"✅ 已登录平台: {', '.join(platform_names)}"
                self.login_status_label.setStyleSheet("color: #28a745; font-weight: bold;")

                # 自动勾选已登录的平台
                for platform_id in logged_in_platforms:
                    if platform_id in self.platform_checkboxes:
                        self.platform_checkboxes[platform_id].setChecked(True)

            else:
                status_text = "💡 请先在'登录管理'标签页中登录各平台账号"
                self.login_status_label.setStyleSheet("color: #007acc; font-weight: bold;")

            self.login_status_label.setText(status_text)

        except Exception as e:
            logger.error(f"更新登录状态显示失败: {e}")

    def showEvent(self, event):
        """界面显示时更新登录状态"""
        super().showEvent(event)
        if hasattr(self, 'login_widget'):
            self.update_login_status_display()

        # 🔧 新增：更新AI按钮状态
        self._update_ai_button_state()

    def _update_ai_button_state(self):
        """更新AI按钮状态"""
        if self.content_optimizer:
            self.ai_optimize_button.setEnabled(True)
            self.ai_status_label.setText("AI优化可用")
        else:
            self.ai_optimize_button.setEnabled(False)
            self.ai_status_label.setText("AI优化不可用")

    def optimize_content_with_ai(self):
        """使用AI优化内容"""
        if not self.content_optimizer:
            QMessageBox.warning(self, "警告", "AI优化服务不可用")
            return

        try:
            logger.info("🔍 开始AI内容优化...")

            # 获取当前内容
            title = self.title_edit.text().strip()
            description = self.description_edit.toPlainText().strip()

            # 获取选中的平台
            selected_platforms = []
            for platform_id, checkbox in self.platform_checkboxes.items():
                if checkbox.isChecked():
                    selected_platforms.append(platform_id)

            if not selected_platforms:
                selected_platforms = ['bilibili']  # 默认平台

            # 禁用按钮并显示进度
            self.ai_optimize_button.setEnabled(False)
            self.ai_status_label.setText("AI优化中...")

            # 创建AI优化工作线程
            self.ai_worker = AIOptimizeWorker(
                self.content_optimizer,
                title,
                description,
                selected_platforms
            )

            self.ai_worker.optimization_completed.connect(self.on_ai_optimization_completed)
            self.ai_worker.optimization_failed.connect(self.on_ai_optimization_failed)
            self.ai_worker.start()

        except Exception as e:
            logger.error(f"启动AI优化失败: {e}")
            QMessageBox.critical(self, "错误", f"AI优化失败: {e}")
            self._update_ai_button_state()

    def on_ai_optimization_completed(self, optimized_content):
        """AI优化完成"""
        try:
            # 更新界面内容
            self.title_edit.setText(optimized_content.title)
            self.description_edit.setPlainText(optimized_content.description)

            # 更新标签
            if optimized_content.tags:
                tags_text = ', '.join(optimized_content.tags)
                self.tags_edit.setText(tags_text)

            # 显示优化结果
            self.show_optimization_results(optimized_content)

        except Exception as e:
            logger.error(f"处理AI优化结果失败: {e}")

        finally:
            self._update_ai_button_state()

    def on_ai_optimization_failed(self, error_message):
        """AI优化失败"""
        QMessageBox.critical(self, "AI优化失败", f"优化过程中出现错误:\n{error_message}")
        self._update_ai_button_state()

    def show_optimization_results(self, optimized_content):
        """显示优化结果对话框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QTabWidget

        dialog = QDialog(self)
        dialog.setWindowTitle("AI优化结果")
        dialog.setModal(True)
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)

        # 创建标签页
        tab_widget = QTabWidget()

        # 标题标签页
        title_tab = QWidget()
        title_layout = QVBoxLayout(title_tab)
        title_layout.addWidget(QLabel("优化后的标题:"))
        title_text = QTextEdit()
        title_text.setPlainText(optimized_content.title)
        title_text.setReadOnly(True)
        title_layout.addWidget(title_text)
        tab_widget.addTab(title_tab, "📝 标题")

        # 描述标签页
        desc_tab = QWidget()
        desc_layout = QVBoxLayout(desc_tab)
        desc_layout.addWidget(QLabel("优化后的描述:"))
        desc_text = QTextEdit()
        desc_text.setPlainText(optimized_content.description)
        desc_text.setReadOnly(True)
        desc_layout.addWidget(desc_text)
        tab_widget.addTab(desc_tab, "📄 描述")

        # 标签标签页
        tags_tab = QWidget()
        tags_layout = QVBoxLayout(tags_tab)
        tags_layout.addWidget(QLabel("优化后的标签:"))
        tags_text = QTextEdit()
        if optimized_content.tags:
            tags_text.setPlainText('\n'.join(optimized_content.tags))
        tags_text.setReadOnly(True)
        tags_layout.addWidget(tags_text)
        tab_widget.addTab(tags_tab, "🏷️ 标签")

        layout.addWidget(tab_widget)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        dialog.exec_()
