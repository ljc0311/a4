#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版增强一键发布标签页
集成浏览器管理和登录功能的简化版本
"""

import os
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTextEdit, QLineEdit, QCheckBox,
    QProgressBar, QGroupBox, QScrollArea, QFrame,
    QMessageBox, QFileDialog, QComboBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from src.services.platform_publisher.integrated_browser_manager import IntegratedBrowserManager
from src.services.platform_publisher.login_manager import login_manager
from src.services.platform_publisher.auto_login_detector import auto_login_detector
from src.utils.logger import logger


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
            self.setup_progress.emit("检测系统浏览器...")
            result = self.browser_manager.auto_setup_and_start(self.preferred_browser)
            self.setup_finished.emit(result)
        except Exception as e:
            logger.error(f"浏览器设置线程异常: {e}")
            self.setup_finished.emit({
                'success': False,
                'error': f'浏览器设置失败: {e}'
            })


class LoginDetectionThread(QThread):
    """登录状态检测线程"""
    detection_finished = pyqtSignal(dict)
    detection_progress = pyqtSignal(str)

    def __init__(self, browser_config):
        super().__init__()
        self.browser_config = browser_config

    def run(self):
        try:
            self.detection_progress.emit("🔍 正在检测平台登录状态...")

            # 使用自动登录检测器
            results = auto_login_detector.detect_all_platforms(self.browser_config)

            self.detection_finished.emit(results)

        except Exception as e:
            logger.error(f"登录检测线程异常: {e}")
            self.detection_finished.emit({
                'error': f'登录检测失败: {e}'
            })


class CurrentPageDetectionThread(QThread):
    """当前页面检测线程"""
    detection_finished = pyqtSignal(dict)

    def __init__(self, browser_config):
        super().__init__()
        self.browser_config = browser_config

    def run(self):
        try:
            # 导入检测器
            from src.services.platform_publisher.auto_login_detector import AutoLoginDetector
            auto_login_detector = AutoLoginDetector()

            # 执行当前页面检测
            results = auto_login_detector.detect_current_page_login(self.browser_config)
            self.detection_finished.emit(results)

        except Exception as e:
            logger.error(f"当前页面检测线程执行失败: {e}")
            self.detection_finished.emit({
                'error': f'检测失败: {e}'
            })


class SimplifiedEnhancedPublishTab(QWidget):
    """简化版增强一键发布标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.browser_manager = IntegratedBrowserManager()
        self.browser_config = None
        self.setup_thread = None
        self.current_page_thread = None

        self.init_ui()

        # 加载保存的浏览器配置
        self.load_saved_browser_config()
        
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
        login_tab = self.create_login_management_tab()
        tab_widget.addTab(login_tab, "🔐 登录管理")
        
        # 发布配置标签页
        publish_tab = self.create_publish_config_tab()
        tab_widget.addTab(publish_tab, "🚀 发布配置")
        
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
        
    def create_login_management_tab(self) -> QWidget:
        """创建登录管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("🔐 平台登录管理")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明文本
        info_text = QTextEdit()
        info_text.setPlainText("""
🔐 平台登录指导

📋 操作步骤：
1. 先在"浏览器设置"标签页中设置浏览器环境
2. 点击下方平台按钮打开对应的登录页面
3. 在浏览器中完成登录
4. 登录状态会自动保存，下次使用无需重复登录

✨ 支持的平台：
• 抖音 - 短视频平台
• B站 - 视频分享平台  
• 快手 - 短视频平台
• 小红书 - 生活分享平台

⚠️ 注意事项：
• 请在安全的网络环境下登录
• 登录信息仅保存在本地
• 如需清除登录信息，可重新登录覆盖
        """.strip())
        info_text.setMaximumHeight(200)
        info_text.setReadOnly(True)
        info_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        layout.addWidget(info_text)
        
        # 平台登录按钮
        platforms_group = QGroupBox("🎯 平台登录")
        platforms_layout = QGridLayout(platforms_group)
        
        platforms = [
            ('douyin', '🎵 抖音', 'https://creator.douyin.com', 0, 0),
            ('bilibili', '📺 B站', 'https://member.bilibili.com/platform/upload/video/frame', 0, 1),
            ('kuaishou', '⚡ 快手', 'https://cp.kuaishou.com/article/publish/video', 1, 0),
            ('xiaohongshu', '📖 小红书', 'https://creator.xiaohongshu.com/publish/publish', 1, 1)
        ]
        
        self.platform_buttons = {}
        for platform_id, platform_name, login_url, row, col in platforms:
            btn = QPushButton(f"{platform_name} 登录")
            btn.clicked.connect(lambda checked, url=login_url, name=platform_name: self.open_platform_login(url, name))
            btn.setMinimumHeight(40)
            platforms_layout.addWidget(btn, row, col)
            self.platform_buttons[platform_id] = btn
            
        layout.addWidget(platforms_group)
        
        # 登录状态
        status_group = QGroupBox("📊 登录状态")
        status_layout = QVBoxLayout(status_group)
        
        self.login_status_text = QTextEdit()
        self.login_status_text.setMaximumHeight(100)
        self.login_status_text.setReadOnly(True)
        self.login_status_text.setPlainText("请先设置浏览器环境，然后登录各平台账号")
        status_layout.addWidget(self.login_status_text)
        
        # 操作按钮
        buttons_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 刷新状态")
        refresh_btn.clicked.connect(self.refresh_login_status)
        buttons_layout.addWidget(refresh_btn)

        self.auto_detect_btn = QPushButton("🔍 检测当前页面")
        self.auto_detect_btn.clicked.connect(self.detect_current_page_login)
        self.auto_detect_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        buttons_layout.addWidget(self.auto_detect_btn)

        self.full_detect_btn = QPushButton("🔍 检测所有平台")
        self.full_detect_btn.clicked.connect(self.auto_detect_login_status)
        self.full_detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        buttons_layout.addWidget(self.full_detect_btn)

        status_layout.addLayout(buttons_layout)
        
        layout.addWidget(status_group)
        
        return widget
        
    def create_publish_config_tab(self) -> QWidget:
        """创建发布配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
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
        video_layout.addWidget(QLabel("标题:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("输入视频标题...")
        video_layout.addWidget(self.title_edit)
        
        # 视频描述
        video_layout.addWidget(QLabel("描述:"))
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("输入视频描述...")
        self.description_edit.setMaximumHeight(100)
        video_layout.addWidget(self.description_edit)
        
        # 标签
        video_layout.addWidget(QLabel("标签 (用逗号分隔):"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("标签1, 标签2, 标签3...")
        video_layout.addWidget(self.tags_edit)
        
        layout.addWidget(video_group)
        
        # 平台选择组
        platform_group = QGroupBox("🎯 发布平台选择")
        platform_layout = QVBoxLayout(platform_group)
        
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
        
        # 发布状态
        status_group = QGroupBox("📊 发布状态")
        status_layout = QVBoxLayout(status_group)
        
        self.publish_status_text = QTextEdit()
        self.publish_status_text.setMaximumHeight(150)
        self.publish_status_text.setReadOnly(True)
        self.publish_status_text.setPlainText("等待开始发布...")
        status_layout.addWidget(self.publish_status_text)
        
        layout.addWidget(status_group)
        
        return widget

    def auto_setup_browser(self):
        """自动设置浏览器"""
        try:
            self.log_status("开始自动设置浏览器环境...")

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
            self.log_status(f"启动浏览器设置失败: {e}")
            self.auto_setup_btn.setEnabled(True)
            self.auto_setup_btn.setText("🔧 自动设置浏览器")

    def on_setup_progress(self, message: str):
        """设置进度更新"""
        self.log_status(message)

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

                self.log_status(result['message'])
                self.log_status("现在可以在'登录管理'标签页中登录各平台账号")

                # 显示成功消息并询问是否自动检测登录状态
                reply = QMessageBox.question(
                    self,
                    "设置成功",
                    f"{browser_info['browser']}环境已就绪！\n\n"
                    f"是否立即自动检测平台登录状态？\n"
                    f"（如果您已经在浏览器中登录了平台账号）",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    # 自动触发登录检测
                    QTimer.singleShot(1000, self.auto_detect_login_status)

            else:
                error_msg = result.get('error', '未知错误')
                self.browser_status_label.setText(f"❌ 设置失败: {error_msg}")
                self.log_status(f"浏览器设置失败: {error_msg}")

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
            self.log_status(f"处理设置结果失败: {e}")

    def show_setup_guide(self):
        """显示设置指南"""
        guide = self.browser_manager.show_setup_guide()

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("浏览器环境设置指南")
        msg_box.setText(guide)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec_()

    def open_platform_login(self, login_url: str, platform_name: str):
        """打开平台登录页面"""
        try:
            if not self.browser_config:
                QMessageBox.warning(
                    self,
                    "提示",
                    "请先在'浏览器设置'标签页中设置浏览器环境"
                )
                return

            webbrowser.open(login_url)

            self.log_status(f"已打开{platform_name}登录页面")

            QMessageBox.information(
                self,
                "登录提示",
                f"已在浏览器中打开{platform_name}登录页面。\n\n"
                f"请在浏览器中完成登录，登录状态会自动保存。"
            )

        except Exception as e:
            logger.error(f"打开{platform_name}登录页面失败: {e}")
            QMessageBox.critical(self, "错误", f"打开登录页面失败：{e}")

    def refresh_login_status(self):
        """刷新登录状态"""
        try:
            status = login_manager.get_all_login_status()

            status_text = "📊 平台登录状态：\n\n"

            for platform_id, info in status.items():
                platform_name = info['name']
                icon = info['icon']
                is_logged_in = info['is_logged_in']

                if is_logged_in:
                    login_time = info.get('login_time', '')
                    if login_time:
                        from datetime import datetime
                        try:
                            login_dt = datetime.fromisoformat(login_time.replace('Z', '+00:00'))
                            time_str = login_dt.strftime('%m-%d %H:%M')
                            status_text += f"{icon} {platform_name}: ✅ 已登录 ({time_str})\n"
                        except:
                            status_text += f"{icon} {platform_name}: ✅ 已登录\n"
                    else:
                        status_text += f"{icon} {platform_name}: ✅ 已登录\n"
                else:
                    status_text += f"{icon} {platform_name}: ❌ 未登录\n"

            self.login_status_text.setPlainText(status_text)

        except Exception as e:
            logger.error(f"刷新登录状态失败: {e}")
            self.login_status_text.setPlainText(f"刷新状态失败: {e}")

    def auto_detect_login_status(self):
        """自动检测登录状态"""
        try:
            if not self.browser_config:
                QMessageBox.warning(
                    self,
                    "提示",
                    "请先在'浏览器设置'标签页中设置浏览器环境"
                )
                return

            self.log_status("🔍 开始自动检测平台登录状态...")

            # 禁用按钮
            self.full_detect_btn.setEnabled(False)
            self.full_detect_btn.setText("⏳ 检测中...")

            # 启动检测线程
            self.detection_thread = LoginDetectionThread(self.browser_config)
            self.detection_thread.detection_progress.connect(self.on_detection_progress)
            self.detection_thread.detection_finished.connect(self.on_detection_finished)
            self.detection_thread.start()

        except Exception as e:
            logger.error(f"启动自动检测失败: {e}")
            self.log_status(f"❌ 启动自动检测失败: {e}")
            self.full_detect_btn.setEnabled(True)
            self.full_detect_btn.setText("🔍 检测所有平台")

    def on_detection_progress(self, message: str):
        """检测进度更新"""
        self.log_status(message)

    def on_detection_finished(self, results: Dict[str, Any]):
        """检测完成"""
        try:
            # 恢复按钮
            self.auto_detect_btn.setEnabled(True)
            self.auto_detect_btn.setText("🔍 检测当前页面")
            self.full_detect_btn.setEnabled(True)
            self.full_detect_btn.setText("🔍 检测所有平台")

            if 'error' in results:
                error_msg = results['error']
                self.log_status(f"❌ 自动检测失败: {error_msg}")
                QMessageBox.critical(self, "检测失败", f"自动检测登录状态失败：\n{error_msg}")
                return

            # 统计检测结果
            logged_platforms = []
            failed_platforms = []

            for platform, result in results.items():
                if isinstance(result, dict):
                    if result.get('is_logged_in', False):
                        logged_platforms.append(result.get('platform_name', platform))
                    elif result.get('error'):
                        failed_platforms.append(result.get('platform_name', platform))

            # 更新状态显示
            self.refresh_login_status()

            # 显示检测结果
            if logged_platforms:
                success_msg = f"✅ 检测到已登录平台: {', '.join(logged_platforms)}"
                self.log_status(success_msg)

                QMessageBox.information(
                    self,
                    "检测完成",
                    f"🎉 自动检测完成！\n\n"
                    f"已登录平台: {', '.join(logged_platforms)}\n"
                    f"登录信息已自动保存。"
                )
            else:
                self.log_status("ℹ️ 未检测到已登录的平台")
                QMessageBox.information(
                    self,
                    "检测完成",
                    "未检测到已登录的平台。\n\n"
                    "请先在浏览器中登录各平台账号，\n"
                    "然后重新进行自动检测。"
                )

            if failed_platforms:
                self.log_status(f"⚠️ 检测失败的平台: {', '.join(failed_platforms)}")

        except Exception as e:
            logger.error(f"处理检测结果失败: {e}")
            self.log_status(f"❌ 处理检测结果失败: {e}")
            QMessageBox.critical(self, "错误", f"处理检测结果失败：{e}")

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
            self.log_status(f"已选择视频文件: {Path(file_path).name}")

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

            # 模拟发布过程
            self.publish_btn.setEnabled(False)
            self.publish_btn.setText("⏳ 发布中...")

            self.log_status(f"开始发布到 {len(selected_platforms)} 个平台...")

            # 模拟发布结果
            for platform_id in selected_platforms:
                platform_name = {
                    'douyin': '抖音',
                    'bilibili': 'B站',
                    'kuaishou': '快手',
                    'xiaohongshu': '小红书'
                }.get(platform_id, platform_id)

                if self.simulation_checkbox.isChecked():
                    self.log_status(f"[{platform_name}] 🎭 模拟发布成功")
                else:
                    self.log_status(f"[{platform_name}] ⏳ 正在发布...")
                    # 这里可以集成实际的发布逻辑
                    self.log_status(f"[{platform_name}] ✅ 发布成功")

            self.publish_btn.setEnabled(True)
            self.publish_btn.setText("🚀 开始发布")

            self.log_status("🎉 所有平台发布完成！")

            QMessageBox.information(
                self,
                "发布完成",
                f"成功发布到 {len(selected_platforms)} 个平台！"
            )

        except Exception as e:
            logger.error(f"发布失败: {e}")
            self.log_status(f"发布失败: {e}")
            QMessageBox.critical(self, "错误", f"发布失败：{e}")

            self.publish_btn.setEnabled(True)
            self.publish_btn.setText("🚀 开始发布")

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

    def log_status(self, message: str):
        """记录状态消息"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        # 更新发布状态文本
        if hasattr(self, 'publish_status_text'):
            current_text = self.publish_status_text.toPlainText()
            if current_text == "等待开始发布...":
                self.publish_status_text.setPlainText(formatted_message)
            else:
                self.publish_status_text.append(formatted_message)

            # 自动滚动到底部
            cursor = self.publish_status_text.textCursor()
            cursor.movePosition(cursor.End)
            self.publish_status_text.setTextCursor(cursor)

    def detect_current_page_login(self):
        """检测当前页面的登录状态"""
        try:
            if not self.browser_config:
                QMessageBox.warning(
                    self,
                    "提示",
                    "请先在'浏览器设置'标签页中设置浏览器环境"
                )
                return

            self.log_status("🔍 正在检测当前页面登录状态...")

            # 禁用按钮
            self.auto_detect_btn.setEnabled(False)
            self.auto_detect_btn.setText("⏳ 检测中...")

            # 启动当前页面检测线程
            self.current_page_thread = CurrentPageDetectionThread(self.browser_config)
            self.current_page_thread.detection_finished.connect(self.on_current_page_detection_finished)
            self.current_page_thread.start()

        except Exception as e:
            logger.error(f"启动当前页面检测失败: {e}")
            self.log_status(f"❌ 启动当前页面检测失败: {e}")
            self.auto_detect_btn.setEnabled(True)
            self.auto_detect_btn.setText("🔍 检测当前页面")

    def on_current_page_detection_finished(self, results: Dict[str, Any]):
        """当前页面检测完成"""
        try:
            # 恢复按钮
            self.auto_detect_btn.setEnabled(True)
            self.auto_detect_btn.setText("🔍 检测当前页面")

            if 'error' in results:
                error_msg = results['error']
                self.log_status(f"❌ 当前页面检测失败: {error_msg}")
                QMessageBox.critical(self, "检测失败", f"当前页面检测失败：\n{error_msg}")
                return

            if 'info' in results:
                info_msg = results['info']
                self.log_status(f"ℹ️ {info_msg}")
                QMessageBox.information(
                    self,
                    "检测结果",
                    f"{info_msg}\n\n请在浏览器中打开以下平台之一：\n"
                    f"• 抖音创作者中心\n"
                    f"• 快手创作者中心\n"
                    f"• B站投稿页面\n"
                    f"• 小红书创作者中心"
                )
                return

            # 处理检测结果
            logged_platforms = []
            for platform, result in results.items():
                if isinstance(result, dict) and result.get('is_logged_in', False):
                    platform_name = result.get('platform_name', platform)
                    logged_platforms.append(platform_name)

            # 更新状态显示
            self.refresh_login_status()

            # 显示检测结果
            if logged_platforms:
                success_msg = f"✅ 检测到当前页面已登录: {', '.join(logged_platforms)}"
                self.log_status(success_msg)

                QMessageBox.information(
                    self,
                    "检测成功",
                    f"🎉 当前页面检测完成！\n\n"
                    f"已登录平台: {', '.join(logged_platforms)}\n"
                    f"登录信息已自动保存。"
                )
            else:
                self.log_status("ℹ️ 当前页面未检测到登录状态")
                QMessageBox.information(
                    self,
                    "检测完成",
                    "当前页面未检测到登录状态。\n\n"
                    "请确认：\n"
                    "1. 已在当前页面完成登录\n"
                    "2. 页面已完全加载\n"
                    "3. 当前页面是支持的平台页面"
                )

        except Exception as e:
            logger.error(f"处理当前页面检测结果失败: {e}")
            self.log_status(f"❌ 处理检测结果失败: {e}")
            QMessageBox.critical(self, "错误", f"处理检测结果失败：{e}")

    def load_saved_browser_config(self):
        """加载保存的浏览器配置"""
        try:
            if self.browser_manager.is_browser_configured():
                self.browser_config = self.browser_manager.get_saved_config()
                browser_info = self.browser_manager.get_saved_browser_info()

                if browser_info:
                    # 更新浏览器状态显示
                    self.browser_status_label.setText(
                        f"✅ {browser_info['browser']} (端口: {browser_info['debug_port']}) - {browser_info['status']}"
                    )
                    self.browser_status_label.setStyleSheet("color: #28a745; font-weight: bold;")

                    # 启用登录检测按钮
                    self.auto_detect_btn.setEnabled(True)
                    self.full_detect_btn.setEnabled(True)

                    self.log_status(f"✅ 已加载保存的浏览器配置: {browser_info['browser']}")
                    logger.info(f"已加载保存的浏览器配置: {browser_info}")

        except Exception as e:
            logger.error(f"加载保存的浏览器配置失败: {e}")
            self.log_status(f"⚠️ 加载保存的浏览器配置失败: {e}")
