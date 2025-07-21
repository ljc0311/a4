#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一版一键发布标签页
整合简化版和增强版的优点，提供最佳用户体验
"""

import os
import time
import asyncio
from typing import Dict, List, Any, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QTextEdit, QPushButton, QCheckBox, QComboBox,
    QProgressBar, QTableWidget, QTableWidgetItem, QTabWidget,
    QFileDialog, QMessageBox, QScrollArea, QFrame, QSplitter,
    QRadioButton, QButtonGroup, QFormLayout, QDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon

from src.services.simple_publisher_service import SimplePublisherService
from src.services.platform_publisher.base_publisher import VideoMetadata
from src.services.content_optimizer import ContentOptimizer
from src.core.service_manager import ServiceManager, ServiceType
from src.utils.logger import logger

# 导入Selenium发布器
try:
    from src.services.platform_publisher.selenium_publisher_factory import selenium_publisher_manager
    SELENIUM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Selenium发布器不可用: {e}")
    SELENIUM_AVAILABLE = False

# 导入集成浏览器管理器
try:
    from src.services.platform_publisher.integrated_browser_manager import IntegratedBrowserManager
    INTEGRATED_BROWSER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"集成浏览器管理器不可用: {e}")
    INTEGRATED_BROWSER_AVAILABLE = False


class AIOptimizeWorker(QThread):
    """AI内容优化工作线程"""
    optimization_completed = pyqtSignal(object)
    optimization_failed = pyqtSignal(str)

    def __init__(self, content_optimizer, title, description, platforms):
        super().__init__()
        self.content_optimizer = content_optimizer
        self.title = title
        self.description = description
        self.platforms = platforms

    def run(self):
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 执行AI优化（使用正确的参数名）
            result = loop.run_until_complete(
                self.content_optimizer.optimize_content(
                    original_title=self.title,
                    original_description=self.description,
                    target_platforms=self.platforms
                )
            )
            self.optimization_completed.emit(result)
        except Exception as e:
            logger.error(f"AI优化失败: {e}")
            self.optimization_failed.emit(str(e))
        finally:
            loop.close()


class ProjectBasedAIOptimizeWorker(QThread):
    """基于项目内容的AI优化工作线程 - 与简化版相同的逻辑"""
    content_generated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, project_name, source_content):
        super().__init__()
        self.project_name = project_name
        self.source_content = source_content

    def run(self):
        try:
            # 获取LLM服务
            from src.core.service_manager import ServiceManager, ServiceType
            import asyncio

            service_manager = ServiceManager()
            llm_service = service_manager.get_service(ServiceType.LLM)

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

            # 创建事件循环用于异步调用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 生成标题
                title_result = loop.run_until_complete(
                    llm_service.generate_text(title_prompt.strip(), max_tokens=100, temperature=0.7)
                )
                title = title_result.data.get('content', '') if title_result.success else '未生成标题'

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

                tags_result = loop.run_until_complete(
                    llm_service.generate_text(tags_prompt.strip(), max_tokens=200, temperature=0.7)
                )
                tags_text = tags_result.data.get('content', '') if tags_result.success else '未生成标签'

                # 处理标签，转换为带#的格式
                if tags_text and tags_text != '未生成标签':
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

                description_result = loop.run_until_complete(
                    llm_service.generate_text(description_prompt.strip(), max_tokens=500, temperature=0.7)
                )
                base_description = description_result.data.get('content', '') if description_result.success else '未生成描述'

                # 将标签添加到描述末尾
                description = f"{base_description.strip()}\n\n{hashtags}"

                # 返回结果
                result = {
                    'title': title.strip(),
                    'description': description.strip(),
                    'tags': tags_text.strip() if tags_text != '未生成标签' else '视频,分享'
                }

                self.content_generated.emit(result)

            finally:
                loop.close()

        except Exception as e:
            logger.error(f"基于项目的AI优化失败: {e}")
            self.error_occurred.emit(str(e))


class PublishWorker(QThread):
    """发布工作线程 - 使用与简化版相同的逻辑"""
    progress_updated = pyqtSignal(float, str)  # 进度, 消息 (与简化版保持一致)
    publish_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, video_path, metadata, platforms, config, project_name=None):
        super().__init__()
        self.video_path = video_path
        self.metadata = metadata
        self.platforms = platforms
        self.config = config
        self.project_name = project_name

    def run(self):
        """执行发布任务 - 使用与简化版完全相同的逻辑"""
        try:
            if not SELENIUM_AVAILABLE:
                self.error_occurred.emit("Selenium发布器不可用")
                return

            # 创建新的事件循环
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 设置配置
            if self.config:
                selenium_publisher_manager.set_config(self.config)

            # 创建进度回调函数
            def progress_callback(message: str, progress: int):
                """进度回调函数"""
                try:
                    # 将进度转换为0-1范围
                    normalized_progress = progress / 100.0
                    self.progress_updated.emit(normalized_progress, message)
                except Exception as e:
                    logger.debug(f"进度回调失败: {e}")

            # 准备视频信息
            video_info = {
                'video_path': self.video_path,
                'title': self.metadata.title,
                'description': self.metadata.description,
                'tags': self.metadata.tags,
                'auto_publish': True,  # 启用自动发布
                'progress_callback': progress_callback,  # 传递进度回调
            }

            # 发布到各平台
            results = {}
            total_platforms = len(self.platforms)

            for i, platform in enumerate(self.platforms):
                try:
                    base_progress = (i / total_platforms) * 100
                    progress_callback(f"开始发布到 {platform}...", int(base_progress))

                    # 🔧 修复：YouTube使用专用API发布器，其他平台使用Selenium
                    if platform.lower() in ['youtube', 'youtube_shorts', 'yt']:
                        # 使用YouTube API发布器
                        from src.services.platform_publisher.publisher_factory import PublisherFactory
                        result = loop.run_until_complete(
                            PublisherFactory.publish_to_youtube(video_info, self.config)
                        )
                        logger.info(f"🎬 使用YouTube API发布器发布到 {platform}")
                    else:
                        # 🔧 优化：快手平台使用备用Chrome发布器（带故障恢复）
                        if platform.lower() == 'kuaishou':
                            # 使用备用Chrome快手发布器
                            result = loop.run_until_complete(
                                selenium_publisher_manager.publish_video('kuaishou_fallback', video_info)
                            )
                            logger.info(f"🛡️ 使用备用Chrome发布器发布到 {platform}")
                        else:
                            # 使用标准Selenium发布器
                            result = loop.run_until_complete(
                                selenium_publisher_manager.publish_video(platform, video_info)
                            )
                            logger.info(f"🌐 使用Selenium发布器发布到 {platform}")

                    results[platform] = result

                    # 🔧 修复：安全检查result类型
                    if isinstance(result, dict) and result.get('success'):
                        logger.info(f"✅ 发布到 {platform} 成功")
                        progress_callback(f"✅ {platform} 发布成功", int(base_progress + 100/total_platforms))
                    else:
                        error_msg = result.get('error', '未知错误') if isinstance(result, dict) else str(result)
                        logger.error(f"❌ 发布到 {platform} 失败: {error_msg}")
                        progress_callback(f"❌ {platform} 发布失败", int(base_progress + 100/total_platforms))

                except Exception as e:
                    logger.error(f"发布到 {platform} 时出错: {e}")
                    results[platform] = {'success': False, 'error': str(e)}
                    progress_callback(f"❌ {platform} 发布出错", int(base_progress + 100/total_platforms))

            # 🔧 修复：统计结果时安全检查类型
            success_count = sum(1 for result in results.values()
                              if isinstance(result, dict) and result.get('success'))
            total_count = len(results)

            final_result = {
                'success_count': success_count,
                'total_platforms': total_count,
                'results': results,
                'overall_success': success_count > 0
            }

            self.publish_completed.emit(final_result)

        except Exception as e:
            logger.error(f"发布工作线程错误: {e}")
            self.error_occurred.emit(str(e))
        finally:
            if 'loop' in locals():
                loop.close()


class UnifiedOneClickPublishTab(QWidget):
    """统一版一键发布标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # 初始化服务
        self.init_services()
        
        # 初始化UI
        self.init_ui()
        
        # 初始化状态
        self.current_worker = None
        self.ai_worker = None
        
        # 自动加载项目数据
        QTimer.singleShot(100, self.auto_load_project_data)

        # 更新AI按钮状态
        QTimer.singleShot(200, self.update_ai_button_state)
        
    def init_services(self):
        """初始化服务"""
        try:
            # 发布服务
            self.publisher = SimplePublisherService()
            
            # 内容优化服务
            try:
                logger.info("🔍 开始初始化AI内容优化服务...")
                service_manager = ServiceManager()
                logger.info("✅ ServiceManager创建成功")

                llm_service = service_manager.get_service(ServiceType.LLM)  # 修复：使用ServiceType枚举
                logger.info(f"🔍 LLM服务获取结果: {llm_service is not None}")

                if llm_service:
                    self.content_optimizer = ContentOptimizer(llm_service)
                    logger.info("✅ AI内容优化服务初始化成功")
                else:
                    logger.warning("❌ LLM服务不可用，无法初始化内容优化服务")
                    self.content_optimizer = None
            except Exception as e:
                logger.error(f"❌ 内容优化服务初始化失败: {e}")
                import traceback
                logger.error(f"错误详情: {traceback.format_exc()}")
                self.content_optimizer = None
                
        except Exception as e:
            logger.error(f"服务初始化失败: {e}")
            
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("🚀 统一版一键发布")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
                border-radius: 8px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # 创建主要内容区域
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # 左侧：发布配置
        left_widget = self.create_publish_config_widget()
        main_splitter.addWidget(left_widget)
        
        # 右侧：状态监控和高级功能
        right_widget = self.create_advanced_features_widget()
        main_splitter.addWidget(right_widget)
        
        # 设置分割比例 (70:30)
        main_splitter.setSizes([700, 300])
        main_splitter.setStretchFactor(0, 7)
        main_splitter.setStretchFactor(1, 3)
        
    def create_publish_config_widget(self) -> QWidget:
        """创建发布配置部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 视频文件选择
        file_group = QGroupBox("📹 视频文件")
        file_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        file_layout = QVBoxLayout(file_group)
        
        file_row = QHBoxLayout()
        self.video_path_edit = QLineEdit()
        self.video_path_edit.setPlaceholderText("选择要发布的视频文件...")
        self.video_path_edit.setMinimumHeight(35)
        self.video_path_edit.textChanged.connect(self.on_video_file_changed)
        
        self.browse_button = QPushButton("📁 浏览")
        self.browse_button.clicked.connect(self.browse_video_file)
        self.browse_button.setMinimumHeight(35)
        self.browse_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        file_row.addWidget(self.video_path_edit)
        file_row.addWidget(self.browse_button)
        file_layout.addLayout(file_row)
        
        layout.addWidget(file_group)
        
        # AI智能内容生成
        ai_group = QGroupBox("🤖 AI智能内容")
        ai_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        ai_layout = QVBoxLayout(ai_group)
        
        # AI按钮行
        ai_button_row = QHBoxLayout()
        
        self.ai_optimize_button = QPushButton("🎯 AI优化内容")
        self.ai_optimize_button.clicked.connect(self.optimize_content_with_ai)
        self.ai_optimize_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        self.refresh_content_btn = QPushButton("🔄 刷新")
        self.refresh_content_btn.clicked.connect(self.refresh_ai_content)
        self.refresh_content_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        
        self.ai_status_label = QLabel()
        self.ai_status_label.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        
        ai_button_row.addWidget(self.ai_optimize_button)
        ai_button_row.addWidget(self.refresh_content_btn)
        ai_button_row.addWidget(self.ai_status_label)
        ai_button_row.addStretch()
        
        ai_layout.addLayout(ai_button_row)
        
        # 内容表单
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(12)
        form_layout.setHorizontalSpacing(15)
        
        # 标题
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("AI将基于项目内容自动生成标题...")
        self.title_edit.setMinimumHeight(35)
        self.title_edit.textChanged.connect(self.save_publish_content)
        form_layout.addRow("📝 标题:", self.title_edit)
        
        # 描述
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("AI将基于项目内容自动生成描述...")
        self.description_edit.setMinimumHeight(100)
        self.description_edit.textChanged.connect(self.save_publish_content)
        form_layout.addRow("📄 描述:", self.description_edit)
        
        # 标签
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("AI将自动生成相关标签，用逗号分隔...")
        self.tags_edit.setMinimumHeight(35)
        self.tags_edit.textChanged.connect(self.save_publish_content)
        form_layout.addRow("🏷️ 标签:", self.tags_edit)
        
        ai_layout.addLayout(form_layout)
        layout.addWidget(ai_group)

        # 平台选择
        platform_group = QGroupBox("🎯 发布平台选择")
        platform_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #27ae60;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        platform_layout = QVBoxLayout(platform_group)

        # 登录状态提示
        self.login_status_label = QLabel("💡 请确保已登录各平台账号")
        self.login_status_label.setStyleSheet("color: #27ae60; font-weight: bold; padding: 5px;")
        platform_layout.addWidget(self.login_status_label)

        # 快手增强版提示
        kuaishou_tip_label = QLabel("🚀 快手使用增强版发布器，配置简单，成功率高(75-85%)")
        kuaishou_tip_label.setStyleSheet("color: #3498db; font-size: 11px; padding: 2px;")
        platform_layout.addWidget(kuaishou_tip_label)

        # 平台复选框网格
        platforms_grid = QGridLayout()
        self.platform_checkboxes = {}

        # 获取支持的平台
        all_supported_platforms = self.publisher.get_supported_platforms()
        main_platforms = ['douyin', 'bilibili', 'kuaishou', 'xiaohongshu', 'wechat', 'youtube']
        supported_platforms = [p for p in main_platforms if p in all_supported_platforms]

        # 平台信息映射
        platform_info = {
            'douyin': {'icon': '🎵', 'name': '抖音'},
            'bilibili': {'icon': '📺', 'name': 'B站'},
            'kuaishou': {'icon': '🚀', 'name': '快手(增强版)'},  # 使用增强版发布器
            'xiaohongshu': {'icon': '📖', 'name': '小红书'},
            'wechat': {'icon': '💬', 'name': '微信视频号'},
            'youtube': {'icon': '🎬', 'name': 'YouTube'}
        }

        # 使用网格布局，每行3个平台
        row = 0
        col = 0
        for platform in supported_platforms:
            info = platform_info.get(platform, {'icon': '📱', 'name': platform.upper()})
            checkbox = QCheckBox(f"{info['icon']} {info['name']}")
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-size: 12px;
                    padding: 5px;
                    min-width: 120px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                }
            """)

            if platform == 'bilibili':  # 默认选中B站
                checkbox.setChecked(True)

            checkbox.stateChanged.connect(self.save_publish_content)
            self.platform_checkboxes[platform] = checkbox
            platforms_grid.addWidget(checkbox, row, col)

            # 为YouTube添加配置按钮
            if platform == 'youtube':
                config_btn = QPushButton("⚙️配置")
                config_btn.setMaximumWidth(60)
                config_btn.setMaximumHeight(30)
                config_btn.setToolTip("YouTube发布配置")
                config_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
                config_btn.clicked.connect(self.show_youtube_config)
                platforms_grid.addWidget(config_btn, row, col + 1)

            col += 1
            if col >= 3:  # 每行3个
                col = 0
                row += 1

        platform_layout.addLayout(platforms_grid)

        # 发布选项
        options_layout = QHBoxLayout()

        self.simulation_checkbox = QCheckBox("🎭 模拟模式 (测试)")
        self.simulation_checkbox.setToolTip("启用后将模拟发布过程，不会真正发布视频")
        options_layout.addWidget(self.simulation_checkbox)

        self.auto_publish_checkbox = QCheckBox("🚀 自动发布")
        self.auto_publish_checkbox.setChecked(True)
        self.auto_publish_checkbox.setToolTip("自动完成发布流程")
        options_layout.addWidget(self.auto_publish_checkbox)

        platform_layout.addLayout(options_layout)
        layout.addWidget(platform_group)

        # 发布按钮
        button_layout = QHBoxLayout()

        self.publish_button = QPushButton("🚀 开始发布")
        self.publish_button.clicked.connect(self.start_publish)
        self.publish_button.setMinimumHeight(50)
        self.publish_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)

        self.cancel_button = QPushButton("❌ 取消发布")
        self.cancel_button.clicked.connect(self.cancel_publish)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setMinimumHeight(50)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)

        button_layout.addWidget(self.publish_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        return widget

    def create_advanced_features_widget(self) -> QWidget:
        """创建高级功能部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        # 创建标签页
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # 发布状态标签页
        status_tab = self.create_status_monitor_tab()
        tab_widget.addTab(status_tab, "📊 发布状态")

        # 浏览器管理标签页
        browser_tab = self.create_browser_management_tab()
        tab_widget.addTab(browser_tab, "🔧 浏览器管理")

        # 发布历史标签页
        history_tab = self.create_publish_history_tab()
        tab_widget.addTab(history_tab, "📈 发布历史")

        return widget

    def create_status_monitor_tab(self) -> QWidget:
        """创建状态监控标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 进度显示
        progress_group = QGroupBox("📊 发布进度")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("准备就绪")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        progress_layout.addWidget(self.progress_label)

        layout.addWidget(progress_group)

        # 状态表格
        status_group = QGroupBox("📋 平台状态")
        status_layout = QVBoxLayout(status_group)

        self.status_table = QTableWidget()
        self.status_table.setColumnCount(3)
        self.status_table.setHorizontalHeaderLabels(["平台", "状态", "结果"])
        self.status_table.horizontalHeader().setStretchLastSection(True)
        self.status_table.setAlternatingRowColors(True)
        self.status_table.setSelectionBehavior(QTableWidget.SelectRows)
        status_layout.addWidget(self.status_table)

        layout.addWidget(status_group)

        # 日志显示
        log_group = QGroupBox("📝 发布日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        return widget

    def create_browser_management_tab(self) -> QWidget:
        """创建浏览器管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 浏览器状态
        browser_group = QGroupBox("🌐 浏览器状态")
        browser_layout = QVBoxLayout(browser_group)

        self.browser_status_label = QLabel("浏览器未启动")
        self.browser_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        browser_layout.addWidget(self.browser_status_label)

        # 浏览器控制按钮
        browser_button_layout = QHBoxLayout()

        self.start_browser_btn = QPushButton("🚀 启动浏览器")
        self.start_browser_btn.clicked.connect(self.start_browser)
        self.start_browser_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)

        self.stop_browser_btn = QPushButton("🛑 停止浏览器")
        self.stop_browser_btn.clicked.connect(self.stop_browser)
        self.stop_browser_btn.setEnabled(False)
        self.stop_browser_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)

        browser_button_layout.addWidget(self.start_browser_btn)
        browser_button_layout.addWidget(self.stop_browser_btn)
        browser_layout.addLayout(browser_button_layout)

        layout.addWidget(browser_group)

        # 登录管理
        login_group = QGroupBox("🔐 登录管理")
        login_layout = QVBoxLayout(login_group)

        login_info = QLabel("在此管理各平台的登录状态")
        login_info.setStyleSheet("color: #666; font-size: 12px;")
        login_layout.addWidget(login_info)

        # 平台登录状态
        self.login_status_table = QTableWidget()
        self.login_status_table.setColumnCount(2)
        self.login_status_table.setHorizontalHeaderLabels(["平台", "登录状态"])
        self.login_status_table.horizontalHeader().setStretchLastSection(True)
        self.login_status_table.setMaximumHeight(120)
        login_layout.addWidget(self.login_status_table)

        layout.addWidget(login_group)

        layout.addStretch()
        return widget

    def create_publish_history_tab(self) -> QWidget:
        """创建发布历史标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 统计信息
        stats_group = QGroupBox("📈 发布统计")
        stats_layout = QGridLayout(stats_group)

        self.total_published_label = QLabel("总发布数: 0")
        self.success_rate_label = QLabel("成功率: 0%")
        self.last_publish_label = QLabel("最后发布: 无")

        stats_layout.addWidget(self.total_published_label, 0, 0)
        stats_layout.addWidget(self.success_rate_label, 0, 1)
        stats_layout.addWidget(self.last_publish_label, 1, 0, 1, 2)

        layout.addWidget(stats_group)

        # 历史记录
        history_group = QGroupBox("📋 发布历史")
        history_layout = QVBoxLayout(history_group)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["时间", "平台", "标题", "状态"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setAlternatingRowColors(True)
        history_layout.addWidget(self.history_table)

        layout.addWidget(history_group)

        return widget

    # 核心功能方法
    def browse_video_file(self):
        """浏览视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件",
            "", "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)"
        )
        if file_path:
            self.video_path_edit.setText(file_path)
            self.log_message(f"📁 已选择视频文件: {os.path.basename(file_path)}")

    def on_video_file_changed(self):
        """视频文件改变时的处理"""
        video_path = self.video_path_edit.text().strip()
        if video_path and os.path.exists(video_path):
            self.log_message(f"✅ 视频文件有效: {os.path.basename(video_path)}")

        # 更新AI按钮状态
        self.update_ai_button_state()

    def update_ai_button_state(self):
        """更新AI按钮状态"""
        if self.content_optimizer:
            self.ai_optimize_button.setEnabled(True)
            self.ai_status_label.setText("AI优化可用")
            self.log_message("✅ AI优化服务可用")
        else:
            self.ai_optimize_button.setEnabled(False)
            self.ai_status_label.setText("AI功能暂时不可用")
            self.log_message("❌ AI优化服务不可用")

    def showEvent(self, event):
        """界面显示时更新状态"""
        super().showEvent(event)
        # 更新AI按钮状态
        self.update_ai_button_state()

    def optimize_content_with_ai(self):
        """使用AI优化内容 - 基于项目世界观内容生成"""
        try:
            # 首先尝试从项目获取内容
            project_name, source_content = self.get_project_content_for_ai()

            self.log_message(f"🔍 项目数据获取结果: project_name={project_name}, content_length={len(source_content) if source_content else 0}")

            if not project_name or not source_content:
                # 如果没有项目内容，使用通用AI优化
                self.log_message("⚠️ 未找到项目内容，使用通用AI优化")
                self.optimize_content_with_generic_ai()
                return

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
            self.log_message("🤖 开始基于项目内容的AI优化...")

            # 创建基于项目内容的AI优化工作线程
            self.ai_worker = ProjectBasedAIOptimizeWorker(
                project_name,
                source_content
            )

            self.ai_worker.content_generated.connect(self.on_project_ai_completed)
            self.ai_worker.error_occurred.connect(self.on_ai_optimization_failed)
            self.ai_worker.start()

        except Exception as e:
            logger.error(f"AI优化启动失败: {e}")
            QMessageBox.critical(self, "错误", f"AI优化启动失败: {e}")
            self.ai_optimize_button.setEnabled(True)

    def optimize_content_with_generic_ai(self):
        """使用通用AI优化（当没有项目内容时）"""
        try:
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

            # 创建通用AI优化工作线程
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
            logger.error(f"启动通用AI优化失败: {e}")
            QMessageBox.critical(self, "错误", f"启动通用AI优化失败: {e}")
            self.reset_ui_state()

    def on_project_ai_completed(self, result):
        """基于项目的AI优化完成"""
        try:
            # 更新界面内容
            self.title_edit.setText(result.get('title', ''))
            self.description_edit.setPlainText(result.get('description', ''))
            self.tags_edit.setText(result.get('tags', ''))

            self.log_message("✅ 基于项目内容的AI优化完成")
            self.ai_status_label.setText("优化完成")

        except Exception as e:
            logger.error(f"处理项目AI优化结果失败: {e}")
        finally:
            self.ai_optimize_button.setEnabled(True)
            self.ai_status_label.setText("")

    def on_ai_optimization_completed(self, result):
        """AI优化完成"""
        try:
            # 更新内容
            if hasattr(result, 'title') and result.title:
                self.title_edit.setText(result.title)

            if hasattr(result, 'description') and result.description:
                self.description_edit.setPlainText(result.description)

            if hasattr(result, 'tags') and result.tags:
                self.tags_edit.setText(', '.join(result.tags))

            self.log_message("✅ AI内容优化完成")
            self.ai_status_label.setText("优化完成")

        except Exception as e:
            logger.error(f"处理AI优化结果失败: {e}")
            self.log_message(f"❌ 处理AI优化结果失败: {e}")
        finally:
            self.ai_optimize_button.setEnabled(True)

    def on_ai_optimization_failed(self, error_msg):
        """AI优化失败"""
        self.log_message(f"❌ AI优化失败: {error_msg}")
        self.ai_status_label.setText("优化失败")
        self.ai_optimize_button.setEnabled(True)
        QMessageBox.warning(self, "AI优化失败", f"AI优化失败:\n{error_msg}")

    def refresh_ai_content(self):
        """刷新AI内容"""
        try:
            self.log_message("🔄 刷新AI内容...")

            # 清空当前内容
            self.title_edit.clear()
            self.description_edit.clear()
            self.tags_edit.clear()

            # 重新生成AI内容
            self.optimize_content_with_ai()

        except Exception as e:
            logger.error(f"刷新AI内容失败: {e}")
            QMessageBox.warning(self, "刷新失败", f"刷新AI内容时出现错误:\n{e}")

    def get_project_content_for_ai(self):
        """获取项目内容用于AI生成 - 与简化版相同的逻辑"""
        try:
            project_manager = None

            # 方法1：遍历所有父级窗口查找项目管理器
            current_widget = self
            while current_widget:
                parent = current_widget.parent()
                if parent and hasattr(parent, 'project_manager') and parent.project_manager:
                    project_manager = parent.project_manager
                    logger.info(f"🔍 从父窗口获取到项目管理器: {type(parent).__name__}")
                    break
                elif parent and hasattr(parent, 'app_controller') and hasattr(parent.app_controller, 'project_manager'):
                    project_manager = parent.app_controller.project_manager
                    logger.info(f"🔍 从app_controller获取到项目管理器: {type(parent).__name__}")
                    break
                elif parent and hasattr(parent, 'storyboard_project_manager') and parent.storyboard_project_manager:
                    project_manager = parent.storyboard_project_manager
                    logger.info(f"🔍 从storyboard_project_manager获取到项目管理器: {type(parent).__name__}")
                    break
                current_widget = parent

            # 方法2：从服务管理器获取
            if not project_manager:
                try:
                    from src.core.service_manager import ServiceManager
                    service_manager = ServiceManager()
                    project_manager = service_manager.get_service('project_manager')
                    if project_manager:
                        logger.info("🔍 从服务管理器获取到项目管理器")
                except Exception as e:
                    logger.error(f"从服务管理器获取项目管理器失败: {e}")

            if not project_manager:
                logger.warning("❌ 未找到任何项目管理器")
                return None, None

            # 调试项目管理器的属性
            logger.info(f"🔍 项目管理器类型: {type(project_manager).__name__}")

            if not hasattr(project_manager, 'current_project') or not project_manager.current_project:
                logger.warning("❌ 项目管理器存在但没有当前项目")
                return None, None

            # 获取项目数据
            current_project = project_manager.current_project

            # 如果current_project是字符串，尝试获取项目数据
            if isinstance(current_project, str):
                logger.info(f"🔍 current_project是字符串: {current_project}")
                # 尝试从项目管理器获取项目数据
                project = None
                if hasattr(project_manager, 'get_project_data'):
                    try:
                        project = project_manager.get_project_data(current_project)
                        logger.info(f"🔍 通过get_project_data获取项目: {bool(project)}")
                    except Exception as e:
                        logger.warning(f"get_project_data失败: {e}")

                if not project and hasattr(project_manager, 'projects'):
                    try:
                        project = project_manager.projects.get(current_project)
                        logger.info(f"🔍 通过projects属性获取项目: {bool(project)}")
                    except Exception as e:
                        logger.warning(f"从projects属性获取失败: {e}")

                if not project:
                    logger.warning(f"❌ 无法获取项目数据: {current_project}")
                    return None, None

                project_name = current_project
            else:
                # current_project本身就是项目数据
                project = current_project
                project_name = project.get('project_name', project.get('name', '未命名项目'))

            logger.info(f"🔍 发布界面获取到项目: {project_name}")
            logger.info(f"🔍 项目数据键: {list(project.keys())[:10]}")  # 只显示前10个键

            # 专门提取世界观内容用于AI生成标题、简介和标签
            world_bible_content = ""

            # 优先从五阶段分镜数据中获取世界观
            if 'five_stage_storyboard' in project:
                five_stage = project['five_stage_storyboard']
                logger.info(f"🔍 五阶段数据键: {list(five_stage.keys()) if isinstance(five_stage, dict) else type(five_stage)}")

                # 从阶段1获取世界观
                if '1' in five_stage and isinstance(five_stage['1'], dict):
                    stage1_data = five_stage['1']
                    if 'world_bible' in stage1_data:
                        world_bible_content = stage1_data['world_bible']
                        logger.info(f"🔍 从五阶段阶段1获取世界观，长度: {len(world_bible_content)}")

                # 如果阶段1没有，尝试从五阶段根级别获取
                if not world_bible_content and 'world_bible' in five_stage:
                    world_bible_content = five_stage['world_bible']
                    logger.info(f"🔍 从五阶段根级别获取世界观，长度: {len(world_bible_content)}")

            # 如果五阶段没有，尝试从项目根级别获取
            if not world_bible_content and 'world_bible' in project:
                world_bible_content = project['world_bible']
                logger.info(f"🔍 从项目根级别获取世界观，长度: {len(world_bible_content)}")

            # 如果还没有，尝试从文本创建模块获取
            if not world_bible_content and 'text_creation' in project:
                text_creation = project['text_creation']
                if isinstance(text_creation, dict):
                    if 'rewritten_text' in text_creation:
                        world_bible_content = text_creation['rewritten_text']
                        logger.info(f"🔍 从文本创建模块获取改写文本作为世界观，长度: {len(world_bible_content)}")
                    elif 'original_text' in text_creation:
                        world_bible_content = text_creation['original_text']
                        logger.info(f"🔍 从文本创建模块获取原始文本作为世界观，长度: {len(world_bible_content)}")

            if not world_bible_content:
                logger.warning("❌ 未找到世界观内容")
                return None, None

            logger.info(f"✅ 成功提取世界观内容，长度: {len(world_bible_content)}")
            logger.info(f"🔍 世界观内容预览: {world_bible_content[:200]}..." if len(world_bible_content) > 200 else f"🔍 完整世界观内容: {world_bible_content}")

            return project_name, world_bible_content

        except Exception as e:
            logger.error(f"获取项目内容失败: {e}")
            return None, None

    def start_publish(self):
        """开始发布 - 使用与简化版相同的逻辑"""
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

            # 🔧 修复：区分YouTube API和Selenium发布器
            # 分析选中的平台
            youtube_platforms = []
            selenium_platforms = []

            for platform in selected_platforms:
                if platform.lower() in ['youtube', 'youtube_shorts', 'yt']:
                    youtube_platforms.append(platform)
                else:
                    selenium_platforms.append(platform)

            # 如果有Selenium平台，检查Selenium是否可用
            if selenium_platforms and not SELENIUM_AVAILABLE:
                QMessageBox.critical(
                    self, "错误",
                    "浏览器自动化发布器不可用，请检查依赖是否正确安装。"
                )
                return

            # 🔧 修复：只有Selenium平台才显示Firefox准备提示
            if selenium_platforms:
                # 构建平台列表文本
                platform_list = []
                for platform in selenium_platforms:
                    if platform == 'douyin':
                        platform_list.append("• 抖音创作者平台：https://creator.douyin.com/")
                    elif platform == 'bilibili':
                        platform_list.append("• B站创作中心：https://member.bilibili.com/")
                    elif platform == 'kuaishou':
                        platform_list.append("• 快手创作者平台：https://cp.kuaishou.com/")
                    elif platform == 'xiaohongshu':
                        platform_list.append("• 小红书创作者平台：https://creator.xiaohongshu.com/")
                    else:
                        platform_list.append(f"• {platform}平台")

                platform_text = "\n   ".join(platform_list)

                reply = QMessageBox.question(
                    self, "🦊 Firefox一键发布",
                    f"""🚀 Firefox一键发布准备：

1. 确保Firefox浏览器已启动：
   • 打开Firefox浏览器
   • 无需特殊配置，直接使用

2. 在Firefox中手动登录以下平台账号：
   {platform_text}

3. 保持Firefox浏览器开启状态

✨ Firefox更稳定：无需调试模式，发布成功率更高！

{'📺 YouTube平台将使用API发布，无需Firefox登录' if youtube_platforms else ''}

是否已完成准备工作并开始发布？""",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply != QMessageBox.Yes:
                    return
            elif youtube_platforms:
                # 仅YouTube平台，显示API发布提示
                reply = QMessageBox.question(
                    self, "🎬 YouTube API发布",
                    """🚀 YouTube API发布准备：

✅ 将使用YouTube API发布，无需Firefox浏览器

📋 发布信息：
• 使用已配置的YouTube API凭据
• 首次使用时会进行OAuth授权
• 发布成功率更高，避免登录问题

是否开始发布？""",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply != QMessageBox.Yes:
                    return

            # 创建视频元数据
            metadata = VideoMetadata(
                title=self.title_edit.text().strip(),
                description=self.description_edit.toPlainText().strip(),
                tags=[tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()]
            )

            # 🔧 修复：使用Firefox浏览器自动化发布（参考简易版本成功经验）
            selenium_config = {
                'driver_type': 'firefox',  # 使用Firefox（参考简易版本）
                'timeout': 30,
                'implicit_wait': 10,
                'headless': False,
                'simulation_mode': self.simulation_checkbox.isChecked(),  # 支持模拟模式
                'firefox_profile': None,   # 使用默认配置文件
                'firefox_options': {
                    'user_friendly': True,  # 用户友好模式
                    'auto_detect': True     # 自动检测已打开的Firefox
                }
            }

            # 初始化状态表格
            self.init_status_table(selected_platforms)

            # 更新UI状态
            self.publish_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)  # 使用百分比进度条
            self.progress_label.setText("🚀 开始发布...")

            self.log_message(f"🚀 开始发布到 {len(selected_platforms)} 个平台...")

            # 启动发布线程（使用与简化版相同的逻辑）
            self.current_worker = PublishWorker(
                video_path=self.video_path_edit.text().strip(),
                metadata=metadata,
                platforms=selected_platforms,
                config=selenium_config,
                project_name=self.get_current_project_name()
            )

            self.current_worker.progress_updated.connect(self.on_progress_updated)
            self.current_worker.publish_completed.connect(self.on_publish_completed)
            self.current_worker.error_occurred.connect(self.on_publish_error)
            self.current_worker.start()

        except Exception as e:
            logger.error(f"启动发布失败: {e}")
            QMessageBox.critical(self, "错误", f"启动发布失败: {e}")
            self.reset_ui_state()

    def cancel_publish(self):
        """取消发布"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.terminate()
            self.current_worker.wait()
            self.log_message("❌ 发布已取消")

        self.reset_ui_state()

    def validate_inputs(self) -> bool:
        """验证输入"""
        if not self.video_path_edit.text().strip():
            QMessageBox.warning(self, "警告", "请选择视频文件")
            return False

        if not os.path.exists(self.video_path_edit.text().strip()):
            QMessageBox.warning(self, "警告", "视频文件不存在")
            return False

        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入视频标题")
            return False

        return True

    # 辅助方法
    def init_status_table(self, platforms):
        """初始化状态表格"""
        self.status_table.setRowCount(len(platforms))

        platform_names = {
            'douyin': '🎵 抖音',
            'bilibili': '📺 B站',
            'kuaishou': '⚡ 快手',
            'xiaohongshu': '📖 小红书',
            'wechat': '💬 微信视频号',
            'youtube': '🎬 YouTube'
        }

        for i, platform in enumerate(platforms):
            name = platform_names.get(platform, platform)
            self.status_table.setItem(i, 0, QTableWidgetItem(name))
            self.status_table.setItem(i, 1, QTableWidgetItem("等待中..."))
            self.status_table.setItem(i, 2, QTableWidgetItem(""))

    def on_progress_updated(self, progress: float, message: str):
        """更新进度 - 与简化版保持一致"""
        try:
            # 确保进度值在有效范围内
            progress_value = max(0, min(100, int(progress * 100)))
            self.progress_bar.setValue(progress_value)
            self.progress_label.setText(message)

            # 记录进度日志
            self.log_message(f"📊 发布进度: {progress_value}% - {message}")

            # 强制刷新UI
            self.progress_bar.repaint()
            self.progress_label.repaint()

            # 更新状态表格（如果消息包含平台信息）
            for i in range(self.status_table.rowCount()):
                platform_item = self.status_table.item(i, 0)
                if platform_item:
                    platform_name = platform_item.text()
                    # 检查消息是否与该平台相关
                    for platform_key in ['抖音', 'B站', '快手', '小红书', '微信', 'YouTube']:
                        if platform_key in platform_name and platform_key in message:
                            self.status_table.setItem(i, 1, QTableWidgetItem(message))
                            break

        except Exception as e:
            logger.error(f"更新进度失败: {e}")

    def on_publish_completed(self, final_result):
        """发布完成"""
        self.log_message("🎉 发布完成!")

        # 🔧 修复：从final_result中提取真正的results
        results = final_result.get('results', {})

        # 🔧 修复：更新状态表格时安全检查类型
        for platform, result in results.items():
            for i in range(self.status_table.rowCount()):
                platform_item = self.status_table.item(i, 0)
                if platform_item and platform in platform_item.text():
                    if isinstance(result, dict) and result.get('success'):
                        self.status_table.setItem(i, 1, QTableWidgetItem("✅ 成功"))
                        self.status_table.setItem(i, 2, QTableWidgetItem(result.get('url', '已发布')))
                    else:
                        self.status_table.setItem(i, 1, QTableWidgetItem("❌ 失败"))
                        error_msg = result.get('error', '未知错误') if isinstance(result, dict) else str(result)
                        self.status_table.setItem(i, 2, QTableWidgetItem(error_msg))
                    break

        self.reset_ui_state()
        self.update_statistics()

        # 🔧 修复：使用final_result中的统计数据
        success_count = final_result.get('success_count', 0)
        total_count = final_result.get('total_platforms', len(results))

        if success_count == total_count:
            QMessageBox.information(self, "发布成功", f"所有 {total_count} 个平台发布成功!")
        elif success_count > 0:
            QMessageBox.warning(self, "部分成功", f"{success_count}/{total_count} 个平台发布成功")
        else:
            QMessageBox.critical(self, "发布失败", "所有平台发布失败")

    def on_publish_error(self, error_msg):
        """发布错误"""
        self.log_message(f"❌ 发布错误: {error_msg}")
        QMessageBox.critical(self, "发布错误", f"发布过程中出现错误:\n{error_msg}")
        self.reset_ui_state()

    def reset_ui_state(self):
        """重置UI状态"""
        self.publish_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("准备就绪")

    def log_message(self, message):
        """记录日志消息"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)
        logger.info(message)

    def show_youtube_config(self):
        """显示YouTube配置对话框"""
        try:
            from src.gui.youtube_config_dialog import YouTubeConfigDialog

            dialog = YouTubeConfigDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                logger.info("YouTube配置已保存")
                QMessageBox.information(self, "配置成功", "YouTube配置已保存！")

        except ImportError as e:
            logger.error(f"无法导入YouTube配置对话框: {e}")
            QMessageBox.warning(
                self, "配置不可用",
                "YouTube配置功能暂时不可用，请检查相关文件是否存在。"
            )
        except Exception as e:
            logger.error(f"显示YouTube配置对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"打开YouTube配置失败:\n{e}")

    def save_publish_content(self):
        """保存发布内容到项目"""
        try:
            # 获取项目管理器
            project_manager = self.get_project_manager()
            if not project_manager or not project_manager.current_project:
                return

            # 检查项目管理器是否有save_publish_content方法
            if not hasattr(project_manager, 'save_publish_content'):
                return

            # 获取当前内容
            title = self.title_edit.text().strip()
            description = self.description_edit.toPlainText().strip()
            tags = self.tags_edit.text().strip()

            # 获取选中的平台
            selected_platforms = []
            for platform, checkbox in self.platform_checkboxes.items():
                if checkbox.isChecked():
                    selected_platforms.append(platform)

            # 保存到项目
            project_manager.save_publish_content(
                title=title,
                description=description,
                tags=tags,
                selected_platforms=selected_platforms
            )

        except Exception as e:
            logger.debug(f"保存发布内容失败: {e}")

    def auto_load_project_data(self):
        """自动加载项目数据"""
        try:
            # 自动检测项目视频文件
            self.auto_detect_project_video()

            # 加载项目的发布内容
            self.load_project_publish_content()

            # 更新统计信息
            self.update_statistics()

            self.log_message("📂 已自动加载项目数据")

        except Exception as e:
            logger.error(f"自动加载项目数据失败: {e}")

    def auto_detect_project_video(self):
        """自动检测项目视频文件"""
        try:
            project_manager = self.get_project_manager()
            if not project_manager or not project_manager.current_project:
                return

            project_path = project_manager.current_project.get('project_path', '')
            if not project_path or not os.path.exists(project_path):
                return

            # 查找项目中的视频文件
            video_candidates = [
                os.path.join(project_path, 'final_video.mp4'),
                os.path.join(project_path, 'output.mp4'),
                os.path.join(project_path, 'video.mp4')
            ]

            for video_path in video_candidates:
                if os.path.exists(video_path):
                    self.video_path_edit.setText(video_path)
                    self.log_message(f"🎬 自动检测到项目视频: {os.path.basename(video_path)}")
                    break

        except Exception as e:
            logger.debug(f"自动检测项目视频失败: {e}")

    def load_project_publish_content(self):
        """加载项目发布内容"""
        try:
            project_manager = self.get_project_manager()
            if not project_manager or not hasattr(project_manager, 'get_publish_content'):
                return

            publish_content = project_manager.get_publish_content()
            if not publish_content:
                return

            # 恢复内容
            if publish_content.get("title"):
                self.title_edit.setText(publish_content["title"])

            if publish_content.get("description"):
                self.description_edit.setPlainText(publish_content["description"])

            if publish_content.get("tags"):
                self.tags_edit.setText(publish_content["tags"])

            # 恢复选中的平台
            selected_platforms = publish_content.get("selected_platforms", [])
            for platform, checkbox in self.platform_checkboxes.items():
                checkbox.setChecked(platform in selected_platforms)

            self.log_message("📋 已加载项目发布内容")

        except Exception as e:
            logger.debug(f"加载项目发布内容失败: {e}")

    def get_project_manager(self):
        """获取项目管理器"""
        try:
            # 从父窗口获取项目管理器
            if hasattr(self.parent_window, 'project_manager'):
                return self.parent_window.project_manager
            elif hasattr(self.parent_window, 'storyboard_project_manager'):
                return self.parent_window.storyboard_project_manager
            return None
        except:
            return None

    def get_current_project_name(self):
        """获取当前项目名称"""
        try:
            project_manager = self.get_project_manager()
            if project_manager and project_manager.current_project:
                return project_manager.current_project.get('name', 'Unknown')
            return None
        except:
            return None

    # 浏览器管理方法
    def start_browser(self):
        """启动浏览器"""
        try:
            self.browser_status_label.setText("正在启动浏览器...")
            self.browser_status_label.setStyleSheet("color: #f39c12; font-weight: bold;")

            # 这里可以添加实际的浏览器启动逻辑
            # 暂时模拟启动成功
            QTimer.singleShot(2000, self.on_browser_started)

        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            self.browser_status_label.setText("浏览器启动失败")
            self.browser_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")

    def on_browser_started(self):
        """浏览器启动完成"""
        self.browser_status_label.setText("浏览器已启动")
        self.browser_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        self.start_browser_btn.setEnabled(False)
        self.stop_browser_btn.setEnabled(True)
        self.log_message("🌐 浏览器已启动")

    def stop_browser(self):
        """停止浏览器"""
        try:
            self.browser_status_label.setText("浏览器已停止")
            self.browser_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.start_browser_btn.setEnabled(True)
            self.stop_browser_btn.setEnabled(False)
            self.log_message("🛑 浏览器已停止")

        except Exception as e:
            logger.error(f"停止浏览器失败: {e}")

    def update_statistics(self):
        """更新统计信息"""
        try:
            # 这里可以添加实际的统计逻辑
            # 暂时显示模拟数据
            self.total_published_label.setText("总发布数: 0")
            self.success_rate_label.setText("成功率: 0%")
            self.last_publish_label.setText("最后发布: 无")

        except Exception as e:
            logger.debug(f"更新统计信息失败: {e}")
