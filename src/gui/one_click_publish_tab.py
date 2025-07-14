# -*- coding: utf-8 -*-
"""
一键发布标签页
提供多平台视频发布功能的用户界面
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QTextEdit, QPushButton, QCheckBox, QComboBox,
    QProgressBar, QTableWidget, QTableWidgetItem, QTabWidget,
    QFileDialog, QMessageBox, QScrollArea, QFrame, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon

from src.services.one_click_publisher import OneClickPublisher
from src.services.platform_publisher.base_publisher import VideoMetadata
from src.services.publisher_database_service import PublisherDatabaseService
from src.utils.logger import logger
from src.utils.async_runner import AsyncRunner

class PublishWorker(QThread):
    """发布工作线程"""
    progress_updated = pyqtSignal(float, str)  # 进度, 消息
    publish_completed = pyqtSignal(dict)  # 发布结果
    error_occurred = pyqtSignal(str)  # 错误信息
    
    def __init__(self, publisher: OneClickPublisher, video_path: str, 
                 metadata: VideoMetadata, platforms: List[str], project_name: str = None):
        super().__init__()
        self.publisher = publisher
        self.video_path = video_path
        self.metadata = metadata
        self.platforms = platforms
        self.project_name = project_name
        
    def run(self):
        """执行发布任务"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 执行异步发布
            result = loop.run_until_complete(
                self.publisher.publish_video(
                    video_path=self.video_path,
                    metadata=self.metadata,
                    target_platforms=self.platforms,
                    project_name=self.project_name,
                    progress_callback=self.progress_updated.emit
                )
            )
            
            self.publish_completed.emit(result)
            
        except Exception as e:
            logger.error(f"发布工作线程错误: {e}")
            self.error_occurred.emit(str(e))
        finally:
            loop.close()

class OneClickPublishTab(QWidget):
    """一键发布标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.publisher = OneClickPublisher()
        self.db_service = PublisherDatabaseService()
        self.async_runner = AsyncRunner()
        
        # 当前发布任务
        self.current_worker = None
        
        self.init_ui()
        self.load_platform_accounts()
        
        # 定时刷新状态
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.refresh_publish_history)
        self.status_timer.start(30000)  # 30秒刷新一次
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧：发布配置
        left_widget = self.create_publish_config_widget()
        splitter.addWidget(left_widget)
        
        # 右侧：状态监控
        right_widget = self.create_status_monitor_widget()
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setSizes([400, 600])
        
    def create_publish_config_widget(self) -> QWidget:
        """创建智能发布配置部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # 视频文件选择
        file_group = QGroupBox("📹 视频文件")
        file_layout = QVBoxLayout(file_group)

        file_row = QHBoxLayout()
        self.video_path_edit = QLineEdit()
        self.video_path_edit.setPlaceholderText("选择要发布的视频文件...")
        self.video_path_edit.textChanged.connect(self.on_video_file_changed)

        self.browse_button = QPushButton("📁 浏览")
        self.browse_button.clicked.connect(self.browse_video_file)
        self.browse_button.setFixedWidth(80)

        file_row.addWidget(self.video_path_edit)
        file_row.addWidget(self.browse_button)
        file_layout.addLayout(file_row)

        layout.addWidget(file_group)
        
        # 智能内容生成
        content_group = QGroupBox("🤖 AI智能内容")
        content_layout = QVBoxLayout(content_group)

        # AI优化按钮行
        ai_button_row = QHBoxLayout()

        # 发布方式选择
        publish_mode_group = QGroupBox("📤 发布方式")
        publish_mode_layout = QVBoxLayout(publish_mode_group)

        self.api_mode_radio = QRadioButton("🔌 API发布 (推荐快速)")
        self.api_mode_radio.setChecked(True)
        self.browser_mode_radio = QRadioButton("🌐 浏览器自动化发布 (支持抖音等)")

        publish_mode_layout.addWidget(self.api_mode_radio)
        publish_mode_layout.addWidget(self.browser_mode_radio)

        # 发布方式说明
        mode_info = QLabel()
        mode_info.setText("""
        💡 发布方式说明:
        • API发布: 使用官方API，速度快，稳定可靠，自动获取
        • 浏览器自动化: 基于MoneyPrinterPlus方案，支持抖音等，需要登录Chrome浏览器
        """)
        mode_info.setWordWrap(True)
        mode_info.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        publish_mode_layout.addWidget(mode_info)

        ai_button_row.addWidget(publish_mode_group)

        self.ai_optimize_button = QPushButton("🎯 AI优化内容")
        self.ai_optimize_button.clicked.connect(self.optimize_content_with_ai)
        self.ai_optimize_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)

        self.generate_cover_button = QPushButton("🖼️ AI生成封面")
        self.generate_cover_button.clicked.connect(self.generate_cover_with_ai)
        self.generate_cover_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)

        ai_buttons = QVBoxLayout()
        ai_buttons.addWidget(self.ai_optimize_button)
        ai_buttons.addWidget(self.generate_cover_button)
        ai_button_row.addLayout(ai_buttons)

        content_layout.addLayout(ai_button_row)

        # 内容显示区域
        content_form = QFormLayout()
        content_form.setVerticalSpacing(10)
        content_form.setHorizontalSpacing(15)

        # 标题
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("AI将基于项目内容自动生成标题...")
        self.title_edit.setMinimumHeight(35)
        content_form.addRow("📝 标题:", self.title_edit)

        # 描述
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("AI将基于项目内容自动生成描述...")
        self.description_edit.setMaximumHeight(120)
        self.description_edit.setMinimumHeight(80)
        content_form.addRow("📄 描述:", self.description_edit)

        # 标签
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("AI将自动生成适合的标签...")
        self.tags_edit.setMinimumHeight(35)
        content_form.addRow("🏷️ 标签:", self.tags_edit)

        # 封面
        cover_widget = QWidget()
        cover_layout = QVBoxLayout(cover_widget)
        cover_layout.setContentsMargins(0, 0, 0, 0)

        # 封面输入行
        cover_input_widget = QWidget()
        cover_input_layout = QHBoxLayout(cover_input_widget)
        cover_input_layout.setContentsMargins(0, 0, 0, 0)

        self.cover_path_edit = QLineEdit()
        self.cover_path_edit.setPlaceholderText("AI将自动生成适配的封面图片...")
        self.cover_path_edit.setMinimumHeight(35)
        self.cover_path_edit.textChanged.connect(self.on_cover_path_changed)

        self.cover_browse_button = QPushButton("📁")
        self.cover_browse_button.clicked.connect(self.browse_cover_file)
        self.cover_browse_button.setFixedSize(35, 35)
        self.cover_browse_button.setToolTip("手动选择封面图片")

        cover_input_layout.addWidget(self.cover_path_edit)
        cover_input_layout.addWidget(self.cover_browse_button)
        cover_input_layout.addWidget(self.generate_cover_button)

        # 封面预览区域
        self.cover_preview_label = QLabel()
        self.cover_preview_label.setFixedSize(200, 120)  # 16:9 比例的预览尺寸
        self.cover_preview_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #cccccc;
                border-radius: 8px;
                background-color: #f8f9fa;
                color: #666666;
                font-size: 12px;
                text-align: center;
            }
        """)
        self.cover_preview_label.setText("封面预览\n点击生成或选择封面")
        self.cover_preview_label.setAlignment(Qt.AlignCenter)
        self.cover_preview_label.setScaledContents(True)

        cover_layout.addWidget(cover_input_widget)
        cover_layout.addWidget(self.cover_preview_label)

        content_form.addRow("🖼️ 封面:", cover_widget)

        content_layout.addLayout(content_form)
        layout.addWidget(content_group)
        
        # 平台选择
        platform_group = QGroupBox("🎯 目标平台")
        platform_layout = QGridLayout(platform_group)

        self.platform_checkboxes = {}
        supported_platforms = self.publisher.get_supported_platforms()

        # 平台图标映射
        platform_icons = {
            'douyin': '🎵',
            'bilibili': '📺',
            'kuaishou': '⚡',
            'xiaohongshu': '📖',
            'youtube': '📹',
            'wechat_channels': '💬'
        }

        # 使用网格布局，每行2个平台
        row = 0
        col = 0
        for platform in supported_platforms:
            icon = platform_icons.get(platform, '📱')
            platform_name = platform.upper().replace('_', ' ')
            checkbox = QCheckBox(f"{icon} {platform_name}")
            checkbox.setStyleSheet("QCheckBox { font-size: 12px; padding: 5px; }")

            self.platform_checkboxes[platform] = checkbox
            platform_layout.addWidget(checkbox, row, col)

            col += 1
            if col >= 2:  # 每行2个
                col = 0
                row += 1

        layout.addWidget(platform_group)
        
        # 发布按钮
        button_layout = QHBoxLayout()
        
        self.publish_button = QPushButton("开始发布")
        self.publish_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.publish_button.clicked.connect(self.start_publish)
        
        self.cancel_button = QPushButton("取消发布")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_publish)
        
        button_layout.addWidget(self.publish_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        
        return widget
        
    def create_status_monitor_widget(self) -> QWidget:
        """创建状态监控部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 发布历史标签页
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        
        # 刷新按钮
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh_publish_history)
        history_layout.addWidget(refresh_button)
        
        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "时间", "标题", "平台", "状态", "视频链接", "错误信息"
        ])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        history_layout.addWidget(self.history_table)
        
        tab_widget.addTab(history_tab, "发布历史")
        
        # 账号管理标签页
        account_tab = QWidget()
        account_layout = QVBoxLayout(account_tab)
        
        # 账号管理按钮
        account_button_layout = QHBoxLayout()
        self.add_account_button = QPushButton("添加账号")
        self.add_account_button.clicked.connect(self.add_platform_account)
        self.remove_account_button = QPushButton("删除账号")
        self.remove_account_button.clicked.connect(self.remove_platform_account)
        
        account_button_layout.addWidget(self.add_account_button)
        account_button_layout.addWidget(self.remove_account_button)
        account_button_layout.addStretch()
        account_layout.addLayout(account_button_layout)
        
        # 账号列表
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(4)
        self.account_table.setHorizontalHeaderLabels([
            "平台", "账号名称", "最后登录", "状态"
        ])
        self.account_table.horizontalHeader().setStretchLastSection(True)
        account_layout.addWidget(self.account_table)
        
        tab_widget.addTab(account_tab, "账号管理")
        
        # 统计信息标签页
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        
        self.stats_label = QLabel("加载统计信息中...")
        stats_layout.addWidget(self.stats_label)
        
        tab_widget.addTab(stats_tab, "统计信息")
        
        layout.addWidget(tab_widget)
        
        return widget
        
    def browse_video_file(self):
        """浏览视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv);;所有文件 (*)"
        )
        if file_path:
            self.video_path_edit.setText(file_path)
            
    def browse_cover_file(self):
        """浏览封面文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择封面图片", "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif);;所有文件 (*)"
        )
        if file_path:
            self.cover_path_edit.setText(file_path)

    def on_cover_path_changed(self):
        """封面路径变化时更新预览"""
        try:
            cover_path = self.cover_path_edit.text().strip()
            if cover_path and os.path.exists(cover_path):
                # 加载并显示封面预览
                pixmap = QPixmap(cover_path)
                if not pixmap.isNull():
                    # 缩放图像以适应预览区域
                    scaled_pixmap = pixmap.scaled(
                        self.cover_preview_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.cover_preview_label.setPixmap(scaled_pixmap)
                    self.cover_preview_label.setToolTip(f"封面预览: {os.path.basename(cover_path)}")
                else:
                    self.reset_cover_preview("无法加载图像")
            else:
                self.reset_cover_preview()

        except Exception as e:
            logger.error(f"更新封面预览失败: {e}")
            self.reset_cover_preview("预览加载失败")

    def reset_cover_preview(self, message="封面预览\n点击生成或选择封面"):
        """重置封面预览"""
        self.cover_preview_label.clear()
        self.cover_preview_label.setText(message)
        self.cover_preview_label.setToolTip("")
            
    def start_publish(self):
        """开始发布"""
        try:
            # 验证输入
            if not self.video_path_edit.text().strip():
                QMessageBox.warning(self, "警告", "请选择视频文件")
                return
                
            if not self.title_edit.text().strip():
                QMessageBox.warning(self, "警告", "请输入视频标题")
                return
                
            # 获取选中的平台
            selected_platforms = []
            for platform, checkbox in self.platform_checkboxes.items():
                if checkbox.isChecked():
                    selected_platforms.append(platform)
                    
            if not selected_platforms:
                QMessageBox.warning(self, "警告", "请至少选择一个发布平台")
                return
                
            # 创建视频元数据
            metadata = VideoMetadata(
                title=self.title_edit.text().strip(),
                description=self.description_edit.toPlainText().strip(),
                tags=[tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()],
                cover_path=self.cover_path_edit.text().strip() or None
            )
            
            # 创建并启动工作线程
            self.current_worker = PublishWorker(
                publisher=self.publisher,
                video_path=self.video_path_edit.text().strip(),
                metadata=metadata,
                platforms=selected_platforms
            )
            
            # 连接信号
            self.current_worker.progress_updated.connect(self.on_progress_updated)
            self.current_worker.publish_completed.connect(self.on_publish_completed)
            self.current_worker.error_occurred.connect(self.on_publish_error)
            
            # 更新UI状态
            self.publish_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_label.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 启动线程
            self.current_worker.start()
            
        except Exception as e:
            logger.error(f"启动发布失败: {e}")
            QMessageBox.critical(self, "错误", f"启动发布失败: {e}")
            
    def cancel_publish(self):
        """取消发布"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.terminate()
            self.current_worker.wait()
            
        self.reset_ui_state()
        
    def on_progress_updated(self, progress: float, message: str):
        """进度更新"""
        self.progress_bar.setValue(int(progress * 100))
        self.progress_label.setText(message)
        
    def on_publish_completed(self, result: Dict[str, Any]):
        """发布完成"""
        self.reset_ui_state()
        
        success_count = result.get('success_count', 0)
        total_platforms = result.get('total_platforms', 0)
        
        if success_count == total_platforms:
            QMessageBox.information(self, "成功", f"视频已成功发布到所有 {total_platforms} 个平台！")
        elif success_count > 0:
            QMessageBox.warning(self, "部分成功", f"视频已发布到 {success_count}/{total_platforms} 个平台")
        else:
            QMessageBox.critical(self, "失败", "视频发布失败，请检查错误信息")
            
        # 刷新发布历史
        self.refresh_publish_history()
        
    def on_publish_error(self, error_message: str):
        """发布错误"""
        self.reset_ui_state()
        QMessageBox.critical(self, "发布错误", f"发布过程中出现错误:\n{error_message}")
        
    def reset_ui_state(self):
        """重置UI状态"""
        self.publish_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.current_worker = None

    def load_platform_accounts(self):
        """加载平台账号"""
        try:
            accounts = self.db_service.get_platform_accounts()

            self.account_table.setRowCount(len(accounts))

            for row, account in enumerate(accounts):
                self.account_table.setItem(row, 0, QTableWidgetItem(account['platform_name']))
                self.account_table.setItem(row, 1, QTableWidgetItem(account['account_name']))

                last_login = account['last_login']
                last_login_str = last_login.strftime('%Y-%m-%d %H:%M') if last_login else '从未登录'
                self.account_table.setItem(row, 2, QTableWidgetItem(last_login_str))

                status = "活跃" if account['is_active'] else "禁用"
                self.account_table.setItem(row, 3, QTableWidgetItem(status))

        except Exception as e:
            logger.error(f"加载平台账号失败: {e}")

    def refresh_publish_history(self):
        """刷新发布历史"""
        try:
            records = self.publisher.get_publish_history(limit=100)

            self.history_table.setRowCount(len(records))

            for row, record in enumerate(records):
                # 时间
                created_time = record['created_at'].strftime('%m-%d %H:%M') if record['created_at'] else ''
                self.history_table.setItem(row, 0, QTableWidgetItem(created_time))

                # 标题
                title = record['published_title'] or '未知标题'
                self.history_table.setItem(row, 1, QTableWidgetItem(title))

                # 平台
                platform = record['platform_name']
                self.history_table.setItem(row, 2, QTableWidgetItem(platform))

                # 状态
                status_map = {
                    'published': '已发布',
                    'failed': '失败',
                    'uploading': '上传中',
                    'processing': '处理中'
                }
                status = status_map.get(record['status'], record['status'])
                self.history_table.setItem(row, 3, QTableWidgetItem(status))

                # 视频链接
                video_url = record['platform_video_url'] or ''
                self.history_table.setItem(row, 4, QTableWidgetItem(video_url))

                # 错误信息
                error_msg = record['error_message'] or ''
                self.history_table.setItem(row, 5, QTableWidgetItem(error_msg))

            # 更新统计信息
            self.update_statistics()

        except Exception as e:
            logger.error(f"刷新发布历史失败: {e}")

    def update_statistics(self):
        """更新统计信息"""
        try:
            stats = self.publisher.get_statistics(days=30)

            stats_text = f"""
            <h3>最近30天统计</h3>
            <p><b>总任务数:</b> {stats.get('total_tasks', 0)}</p>
            <p><b>已完成:</b> {stats.get('status_counts', {}).get('completed', 0)}</p>
            <p><b>处理中:</b> {stats.get('status_counts', {}).get('processing', 0)}</p>
            <p><b>失败:</b> {stats.get('status_counts', {}).get('failed', 0)}</p>

            <h4>平台发布统计</h4>
            """

            platform_stats = stats.get('platform_stats', {})
            for platform, data in platform_stats.items():
                success_rate = (data['success'] / data['total'] * 100) if data['total'] > 0 else 0
                stats_text += f"""
                <p><b>{platform}:</b> 总计 {data['total']}, 成功 {data['success']}, 成功率 {success_rate:.1f}%</p>
                """

            self.stats_label.setText(stats_text)

        except Exception as e:
            logger.error(f"更新统计信息失败: {e}")
            self.stats_label.setText("统计信息加载失败")

    def add_platform_account(self):
        """添加平台账号"""
        try:
            from .account_config_dialog import AccountConfigDialog
        except ImportError:
            QMessageBox.warning(self, "警告", "账号配置对话框模块未找到")
            return

        try:
            dialog = AccountConfigDialog(self)
            if dialog.exec_() == dialog.Accepted:
                account_data = dialog.get_account_data()

                # 创建账号
                self.db_service.create_platform_account(
                    platform=account_data['platform'],
                    account_name=account_data['account_name'],
                    credentials=account_data['credentials']
                )

                # 刷新账号列表
                self.load_platform_accounts()

                QMessageBox.information(self, "成功", "账号添加成功！")

        except Exception as e:
            logger.error(f"添加平台账号失败: {e}")
            QMessageBox.critical(self, "错误", f"添加账号失败: {e}")

    def remove_platform_account(self):
        """删除平台账号"""
        current_row = self.account_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请选择要删除的账号")
            return

        reply = QMessageBox.question(
            self, "确认删除", "确定要删除选中的账号吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 这里需要实现删除账号的逻辑
                # 由于我们还没有实现删除方法，暂时显示提示
                QMessageBox.information(self, "提示", "删除功能将在后续版本中实现")

            except Exception as e:
                logger.error(f"删除平台账号失败: {e}")
                QMessageBox.critical(self, "错误", f"删除账号失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        # 停止定时器
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()

        # 取消正在进行的发布任务
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.terminate()
            self.current_worker.wait()

        # 关闭异步运行器
        if hasattr(self, 'async_runner'):
            self.async_runner.stop()

        event.accept()

    def browse_video_file(self):
        """浏览视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)"
        )
        if file_path:
            self.video_path_edit.setText(file_path)

    def browse_cover_file(self):
        """浏览封面文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择封面图片", "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif)"
        )
        if file_path:
            self.cover_path_edit.setText(file_path)

    def on_video_file_changed(self):
        """视频文件改变时的处理"""
        video_path = self.video_path_edit.text().strip()
        if video_path and os.path.exists(video_path):
            # 自动触发AI内容优化
            self.auto_optimize_content()

    def auto_optimize_content(self):
        """自动优化内容（当有项目加载时）"""
        try:
            # 检查是否有当前项目
            from src.core.service_manager import ServiceManager
            service_manager = ServiceManager()
            project_manager = service_manager.get_service('project_manager')

            if project_manager and hasattr(project_manager, 'current_project') and project_manager.current_project:
                logger.info("检测到当前项目，自动生成AI内容...")
                self.optimize_content_with_ai()
            else:
                logger.info("未检测到当前项目，跳过自动内容生成")

        except Exception as e:
            logger.debug(f"自动内容优化失败: {e}")

    def optimize_content_with_ai(self):
        """使用AI优化内容"""
        try:
            self.ai_optimize_button.setText("🔄 生成中...")
            self.ai_optimize_button.setEnabled(False)

            # 获取项目管理器
            from src.core.service_manager import ServiceManager
            service_manager = ServiceManager()
            project_manager = service_manager.get_service('project_manager')

            if not project_manager or not hasattr(project_manager, 'current_project') or not project_manager.current_project:
                QMessageBox.warning(self, "提示", "请先加载一个项目，AI将基于项目内容生成标题、描述和标签")
                self.ai_optimize_button.setText("🎯 AI优化内容")
                self.ai_optimize_button.setEnabled(True)
                return

            # 获取项目数据
            project = project_manager.current_project
            project_name = project.get('name', '未命名项目')

            # 获取项目的原文或世界观
            source_content = ""
            if 'article_content' in project:
                source_content = project['article_content']
            elif 'world_bible' in project:
                source_content = project['world_bible']
            elif 'scenes' in project:
                # 从场景数据中提取内容
                scenes = project['scenes']
                if isinstance(scenes, list) and scenes:
                    source_content = "\n".join([scene.get('content', '') for scene in scenes[:3]])  # 取前3个场景

            if not source_content:
                QMessageBox.warning(self, "提示", "项目中没有找到可用的内容数据（原文、世界观或场景）")
                self.ai_optimize_button.setText("🎯 AI优化内容")
                self.ai_optimize_button.setEnabled(True)
                return

            # 启动AI内容生成线程
            self.start_ai_content_generation(project_name, source_content)

        except Exception as e:
            logger.error(f"AI内容优化失败: {e}")
            QMessageBox.critical(self, "错误", f"AI内容优化失败: {str(e)}")
            self.ai_optimize_button.setText("🎯 AI优化内容")
            self.ai_optimize_button.setEnabled(True)

    def start_ai_content_generation(self, project_name: str, source_content: str):
        """启动AI内容生成线程"""
        try:
            from PyQt5.QtCore import QThread, pyqtSignal

            class AIContentWorker(QThread):
                content_generated = pyqtSignal(dict)
                error_occurred = pyqtSignal(str)

                def __init__(self, project_name, source_content):
                    super().__init__()
                    self.project_name = project_name
                    self.source_content = source_content

                def run(self):
                    try:
                        # 获取LLM服务
                        from src.core.service_manager import ServiceManager
                        service_manager = ServiceManager()
                        llm_service = service_manager.get_service('llm')

                        if not llm_service:
                            self.error_occurred.emit("LLM服务不可用")
                            return

                        # 生成标题
                        title_prompt = f"""
                        基于以下项目内容，为短视频生成一个吸引人的标题（15-30字）：

                        项目名称：{self.project_name}
                        内容摘要：{self.source_content[:500]}

                        要求：
                        1. 标题要吸引眼球，适合短视频平台
                        2. 突出内容亮点和情感价值
                        3. 15-30字之间
                        4. 只返回标题，不要其他内容
                        """

                        title = llm_service.generate_response(title_prompt.strip())

                        # 生成标签（先生成标签）
                        tags_prompt = f"""
                        基于以下项目内容，生成5-8个适合短视频平台的标签：

                        项目名称：{self.project_name}
                        内容：{self.source_content[:500]}

                        要求：
                        1. 标签要热门且相关
                        2. 包含内容类型、情感、主题等
                        3. 5-8个标签
                        4. 用逗号分隔
                        5. 只返回标签，不要其他内容
                        """

                        tags_text = llm_service.generate_response(tags_prompt.strip())

                        # 处理标签，转换为带#的格式
                        if tags_text and tags_text.strip():
                            tag_list = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
                            hashtags = ' '.join([f'#{tag}' for tag in tag_list[:8]])  # 限制8个标签
                        else:
                            hashtags = '#视频 #分享'

                        # 生成描述（包含标签）
                        description_prompt = f"""
                        基于以下项目内容，为短视频生成一个详细的描述（100-150字）：

                        项目名称：{self.project_name}
                        内容：{self.source_content[:800]}

                        要求：
                        1. 描述要详细介绍视频内容
                        2. 包含情感共鸣点
                        3. 适合短视频平台的语言风格
                        4. 100-150字之间
                        5. 只返回描述内容，不要包含标签
                        6. 语言要生动有趣，能吸引观众
                        """

                        base_description = llm_service.generate_response(description_prompt.strip())

                        # 将标签添加到描述末尾
                        description = f"{base_description.strip()}\n\n{hashtags}"

                        # 返回结果
                        result = {
                            'title': title.strip(),
                            'description': description.strip(),
                            'tags': tags_text.strip() if tags_text and tags_text.strip() else '视频,分享'
                        }

                        self.content_generated.emit(result)

                    except Exception as e:
                        self.error_occurred.emit(str(e))

            # 创建并启动工作线程
            self.ai_worker = AIContentWorker(project_name, source_content)
            self.ai_worker.content_generated.connect(self.on_ai_content_generated)
            self.ai_worker.error_occurred.connect(self.on_ai_content_error)
            self.ai_worker.start()

        except Exception as e:
            logger.error(f"启动AI内容生成失败: {e}")
            self.ai_optimize_button.setText("🎯 AI优化内容")
            self.ai_optimize_button.setEnabled(True)

    def on_ai_content_generated(self, content: dict):
        """AI内容生成完成"""
        try:
            self.title_edit.setText(content.get('title', ''))
            self.description_edit.setPlainText(content.get('description', ''))
            self.tags_edit.setText(content.get('tags', ''))

            logger.info("✅ AI内容生成完成")
            QMessageBox.information(self, "成功", "AI内容生成完成！")

        except Exception as e:
            logger.error(f"设置AI生成内容失败: {e}")
        finally:
            self.ai_optimize_button.setText("🎯 AI优化内容")
            self.ai_optimize_button.setEnabled(True)

    def on_ai_content_error(self, error_msg: str):
        """AI内容生成错误"""
        logger.error(f"AI内容生成失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"AI内容生成失败: {error_msg}")
        self.ai_optimize_button.setText("🎯 AI优化内容")
        self.ai_optimize_button.setEnabled(True)

    def generate_cover_with_ai(self):
        """使用AI生成封面"""
        try:
            self.generate_cover_button.setText("🔄 生成中...")
            self.generate_cover_button.setEnabled(False)

            # 获取当前的标题和描述
            title = self.title_edit.text().strip()
            description = self.description_edit.toPlainText().strip()

            if not title and not description:
                QMessageBox.warning(self, "提示", "请先生成或输入标题和描述，AI将基于这些内容生成封面")
                self.generate_cover_button.setText("🖼️ AI生成封面")
                self.generate_cover_button.setEnabled(True)
                return

            # 启动AI封面生成线程
            self.start_ai_cover_generation(title, description)

        except Exception as e:
            logger.error(f"AI封面生成失败: {e}")
            QMessageBox.critical(self, "错误", f"AI封面生成失败: {str(e)}")
            self.generate_cover_button.setText("🖼️ AI生成封面")
            self.generate_cover_button.setEnabled(True)

    def start_ai_cover_generation(self, title: str, description: str):
        """启动AI封面生成线程"""
        try:
            from PyQt5.QtCore import QThread, pyqtSignal

            class AICoverWorker(QThread):
                cover_generated = pyqtSignal(str)
                error_occurred = pyqtSignal(str)

                def __init__(self, title, description):
                    super().__init__()
                    self.title = title
                    self.description = description

                def run(self):
                    try:
                        # 获取图像生成服务
                        from src.core.service_manager import ServiceManager
                        from src.models.image_generation_service import ImageGenerationService

                        # 尝试多种方式获取图像生成服务
                        image_service = None

                        # 方式1：从服务管理器获取
                        try:
                            service_manager = ServiceManager()
                            image_service = service_manager.get_service('image')
                        except Exception as e:
                            logger.warning(f"从服务管理器获取图像服务失败: {e}")

                        # 方式2：直接创建图像生成服务
                        if not image_service:
                            try:
                                image_service = ImageGenerationService()
                                # 确保服务已初始化
                                import asyncio
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(image_service.initialize())
                                loop.close()
                            except Exception as e:
                                logger.warning(f"直接创建图像服务失败: {e}")

                        if not image_service:
                            self.error_occurred.emit("图像生成服务未初始化")
                            return

                        # 构建封面生成提示词
                        cover_prompt = f"""
                        为短视频生成一个吸引人的封面图片：

                        标题：{self.title}
                        描述：{self.description[:200]}

                        要求：
                        1. 图片要醒目、吸引眼球
                        2. 适合短视频平台的封面风格
                        3. 色彩鲜明，构图简洁
                        4. 体现视频主题和情感
                        5. 高质量，专业制作
                        6. 16:9横版比例，适合视频封面

                        电影感，超写实，4K，胶片颗粒，景深
                        """

                        # 使用异步方式调用图像生成服务
                        import asyncio
                        import tempfile
                        import os

                        # 创建临时目录
                        temp_dir = tempfile.mkdtemp()

                        # 设置事件循环
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        # 创建新的事件循环
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        try:
                            # 调用异步图像生成服务
                            result = loop.run_until_complete(
                                image_service.generate_image(
                                    prompt=cover_prompt.strip(),
                                    config={
                                        'width': 1024,
                                        'height': 576,  # 16:9 比例
                                        'quality': '高质量',
                                        'style': '电影风格'
                                    }
                                )
                            )

                            if result and result.success and result.image_paths:
                                # 使用第一个生成的图像
                                image_path = result.image_paths[0]
                                if os.path.exists(image_path):
                                    self.cover_generated.emit(image_path)
                                else:
                                    self.error_occurred.emit("生成的图像文件不存在")
                            else:
                                error_msg = result.error_message if result else "图像生成失败"
                                self.error_occurred.emit(error_msg)

                        finally:
                            loop.close()

                    except Exception as e:
                        self.error_occurred.emit(str(e))

            # 创建并启动工作线程
            self.cover_worker = AICoverWorker(title, description)
            self.cover_worker.cover_generated.connect(self.on_ai_cover_generated)
            self.cover_worker.error_occurred.connect(self.on_ai_cover_error)
            self.cover_worker.start()

        except Exception as e:
            logger.error(f"启动AI封面生成失败: {e}")
            self.generate_cover_button.setText("🖼️ AI生成封面")
            self.generate_cover_button.setEnabled(True)

    def on_ai_cover_generated(self, cover_path: str):
        """AI封面生成完成"""
        try:
            # 将临时文件复制到项目目录
            import shutil
            import os
            from datetime import datetime

            # 创建封面保存目录
            cover_dir = os.path.join("output", "covers")
            os.makedirs(cover_dir, exist_ok=True)

            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_cover_path = os.path.join(cover_dir, f"ai_cover_{timestamp}.png")

            # 复制文件
            shutil.copy2(cover_path, final_cover_path)

            # 设置到界面
            self.cover_path_edit.setText(final_cover_path)

            logger.info(f"✅ AI封面生成完成: {final_cover_path}")
            QMessageBox.information(self, "成功", f"AI封面生成完成！\n保存位置: {final_cover_path}")

        except Exception as e:
            logger.error(f"保存AI生成封面失败: {e}")
            QMessageBox.warning(self, "警告", f"封面生成成功但保存失败: {str(e)}")
        finally:
            self.generate_cover_button.setText("🖼️ AI生成封面")
            self.generate_cover_button.setEnabled(True)

    def on_ai_cover_error(self, error_msg: str):
        """AI封面生成错误"""
        logger.error(f"AI封面生成失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"AI封面生成失败: {error_msg}")
        self.generate_cover_button.setText("🖼️ AI生成封面")
        self.generate_cover_button.setEnabled(True)
