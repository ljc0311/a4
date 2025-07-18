# -*- coding: utf-8 -*-
"""
简化版一键发布标签页
不依赖复杂的数据库，使用JSON文件存储
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
    QRadioButton, QButtonGroup, QFormLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon

from src.services.simple_publisher_service import SimplePublisherService
from src.services.platform_publisher.base_publisher import VideoMetadata
from src.services.content_optimizer import ContentOptimizer
from src.core.service_manager import ServiceManager
from src.utils.logger import logger

# 导入Selenium发布器
try:
    from src.services.platform_publisher.selenium_publisher_factory import selenium_publisher_manager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    selenium_publisher_manager = None

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

            # 执行异步优化
            result = loop.run_until_complete(
                self.content_optimizer.optimize_content(
                    original_title=self.title,
                    original_description=self.description,
                    target_platforms=self.platforms
                )
            )

            self.optimization_completed.emit(result)

        except Exception as e:
            logger.error(f"AI优化工作线程错误: {e}")
            self.optimization_failed.emit(str(e))
        finally:
            loop.close()

class SimplePublishWorker(QThread):
    """简化版发布工作线程"""
    progress_updated = pyqtSignal(float, str)  # 进度, 消息
    publish_completed = pyqtSignal(dict)  # 发布结果
    error_occurred = pyqtSignal(str)  # 错误信息
    
    def __init__(self, publisher: SimplePublisherService, video_path: str, 
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

class SeleniumPublishWorker(QThread):
    """Selenium发布工作线程"""
    progress_updated = pyqtSignal(float, str)  # 进度, 消息
    publish_completed = pyqtSignal(dict)  # 发布结果
    error_occurred = pyqtSignal(str)  # 错误信息

    def __init__(self, video_path: str, metadata: VideoMetadata, platforms: List[str], config: Dict[str, Any] = None):
        super().__init__()
        self.video_path = video_path
        self.metadata = metadata
        self.platforms = platforms
        self.config = config or {}

    def run(self):
        """执行Selenium发布任务"""
        try:
            if not SELENIUM_AVAILABLE:
                self.error_occurred.emit("Selenium发布器不可用")
                return

            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 设置配置
            if self.config:
                selenium_publisher_manager.set_config(self.config)

            # 🔧 修复问题3：创建进度回调函数
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
                'auto_publish': True,  # 🔧 修复：启用自动发布
                'progress_callback': progress_callback,  # 🔧 修复问题3：传递进度回调
            }

            # 发布到各平台
            results = {}
            total_platforms = len(self.platforms)

            for i, platform in enumerate(self.platforms):
                try:
                    base_progress = (i / total_platforms) * 100
                    progress_callback(f"开始发布到 {platform}...", int(base_progress))

                    result = loop.run_until_complete(
                        selenium_publisher_manager.publish_video(platform, video_info)
                    )

                    results[platform] = result

                    if result.get('success'):
                        logger.info(f"✅ Selenium发布到 {platform} 成功")
                        progress_callback(f"✅ {platform} 发布成功", int(base_progress + 100/total_platforms))
                    else:
                        logger.error(f"❌ Selenium发布到 {platform} 失败: {result.get('error')}")
                        progress_callback(f"❌ {platform} 发布失败", int(base_progress + 100/total_platforms))

                except Exception as e:
                    logger.error(f"💥 Selenium发布到 {platform} 异常: {e}")
                    results[platform] = {'success': False, 'error': str(e)}
                    progress_callback(f"💥 {platform} 发布异常", int(base_progress + 100/total_platforms))

            progress_callback("🎉 所有平台发布完成", 100)
            self.publish_completed.emit(results)

        except Exception as e:
            logger.error(f"Selenium发布工作线程错误: {e}")
            self.error_occurred.emit(str(e))
        finally:
            loop.close()

class CoverGenerationWorker(QThread):
    """封面生成工作线程"""
    finished = pyqtSignal(str)  # 生成完成，传递文件路径
    error_occurred = pyqtSignal(str)  # 发生错误

    def __init__(self, title: str, image_service=None):
        super().__init__()
        self.title = title
        self.image_service = image_service

    def run(self):
        """执行封面生成"""
        try:
            from src.core.service_manager import ServiceManager
            from src.models.image_generation_service import ImageGenerationService

            # 🔧 修复：优先使用传入的图像服务
            image_service = self.image_service

            # 如果没有传入图像服务，尝试多种方式获取
            if not image_service:
                # 方式1：从服务管理器获取
                try:
                    service_manager = ServiceManager()
                    image_service = service_manager.get_service('image')
                    logger.info("从服务管理器获取图像服务成功")
                except Exception as e:
                    logger.warning(f"从服务管理器获取图像服务失败: {e}")

                # 方式2：直接创建图像生成服务
                if not image_service:
                    try:
                        image_service = ImageGenerationService()
                        # 确保服务已初始化
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(image_service.initialize())
                        loop.close()
                        logger.info("直接创建图像服务成功")
                    except Exception as e:
                        logger.warning(f"直接创建图像服务失败: {e}")

            if not image_service:
                self.error_occurred.emit("图像生成服务未初始化")
                return

            # 生成封面提示词
            prompt = f"视频封面设计: {self.title}, 高质量, 吸引人的, 现代风格, 16:9比例"

            # 创建输出目录
            cover_dir = "output/covers"
            os.makedirs(cover_dir, exist_ok=True)

            # 生成图像
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 🔧 修复：使用正确的参数格式调用图像生成
                result = loop.run_until_complete(
                    image_service.generate_image(
                        prompt=prompt.strip(),
                        config={
                            'width': 1024,
                            'height': 576,  # 16:9 比例
                            'quality': '高质量',
                            'style': '电影风格'
                        }
                    )
                )

                # 🔧 修复：适配新的返回格式
                if result and result.success and result.image_paths:
                    # 使用第一个生成的图像
                    source_image_path = result.image_paths[0]
                    if os.path.exists(source_image_path):
                        # 复制到封面目录
                        import shutil
                        from datetime import datetime

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        cover_filename = f"cover_{timestamp}.png"
                        cover_path = os.path.join(cover_dir, cover_filename)

                        shutil.copy2(source_image_path, cover_path)
                        self.finished.emit(cover_path)
                        logger.info(f"封面生成成功: {cover_path}")
                    else:
                        self.error_occurred.emit("生成的图像文件不存在")
                else:
                    error_msg = result.error_message if result else "图像生成失败"
                    self.error_occurred.emit(error_msg)

            finally:
                loop.close()

        except Exception as e:
            logger.error(f"封面生成异常: {e}")
            self.error_occurred.emit(str(e))

class PlatformLoginWorker(QThread):
    """平台登录工作线程"""
    login_success = pyqtSignal(str, str, str)  # platform, platform_name, account_name
    login_failed = pyqtSignal(str, str, str)   # platform, platform_name, error_msg

    def __init__(self, platform: str, platform_name: str):
        super().__init__()
        self.platform = platform
        self.platform_name = platform_name

    def run(self):
        """执行平台登录"""
        try:
            from src.services.platform_publisher.publisher_factory import PublisherFactory

            # 创建发布器
            publisher = PublisherFactory.create_publisher(self.platform, {
                'headless': False,  # 显示浏览器
                'timeout': 120000   # 2分钟超时
            })

            if not publisher:
                self.login_failed.emit(
                    self.platform,
                    self.platform_name,
                    "无法创建发布器，请检查平台支持"
                )
                return

            # 执行登录
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 执行认证
                success = loop.run_until_complete(publisher.authenticate({}))

                if success:
                    # 获取账号信息
                    account_name = f"{self.platform_name}_用户_{int(time.time())}"

                    # 保存登录信息到数据库
                    self.save_login_credentials(publisher, account_name)

                    self.login_success.emit(self.platform, self.platform_name, account_name)
                else:
                    self.login_failed.emit(
                        self.platform,
                        self.platform_name,
                        "登录验证失败，请重试"
                    )

            finally:
                loop.close()
                # 清理浏览器资源
                if hasattr(publisher, 'cleanup'):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(publisher.cleanup())
                    finally:
                        loop.close()

        except Exception as e:
            self.login_failed.emit(self.platform, self.platform_name, str(e))

    def save_login_credentials(self, publisher, account_name: str):
        """保存登录凭证"""
        try:
            from src.services.simple_publisher_service import SimplePublisherService
            import time

            # 获取Cookie或其他凭证
            credentials = {}

            if hasattr(publisher, 'page') and publisher.page:
                # 获取浏览器Cookie
                loop = asyncio.get_event_loop()
                cookies = loop.run_until_complete(publisher.page.context.cookies())

                # 转换为字典格式
                cookie_dict = {}
                for cookie in cookies:
                    cookie_dict[cookie['name']] = cookie['value']

                credentials = {'cookies': cookie_dict}

            # 保存到数据库
            simple_publisher = SimplePublisherService()
            simple_publisher.create_platform_account(
                platform=self.platform,
                account_name=account_name,
                credentials=credentials
            )

        except Exception as e:
            logger.error(f"保存登录凭证失败: {e}")

class ProjectContentWorker(QThread):
    """项目内容生成工作线程"""
    content_generated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, project_name: str, source_content: str):
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
            self.error_occurred.emit(str(e))

class SimpleOneClickPublishTab(QWidget):
    """简化版一键发布标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.publisher = SimplePublisherService()

        # 初始化服务管理器
        self.service_manager = ServiceManager()

        # 初始化AI优化服务
        try:
            llm_service = self.service_manager.get_service('llm')
            self.content_optimizer = ContentOptimizer(llm_service)
        except Exception as e:
            logger.warning(f"AI优化服务初始化失败: {e}")
            self.content_optimizer = None

        # 🔧 新增：初始化图像生成服务
        try:
            self.image_service = self.service_manager.get_service('image')
            if self.image_service:
                logger.info("简化版发布界面：图像生成服务初始化成功")
            else:
                logger.warning("简化版发布界面：图像生成服务未找到")
        except Exception as e:
            logger.warning(f"简化版发布界面：图像生成服务初始化失败: {e}")
            self.image_service = None

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
        
        # 设置分割比例 (75:25) - 右侧功能区占比更小
        splitter.setSizes([750, 250])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        # 初始化AI优化状态
        self._update_ai_button_state()

        # 🔧 新增：加载项目发布内容
        self.load_project_publish_content()

        # 🔧 新增：自动检测项目视频文件
        self.auto_detect_project_video()
        
    def create_publish_config_widget(self) -> QWidget:
        """创建发布配置部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 视频文件选择
        file_group = QGroupBox("视频文件")
        file_layout = QVBoxLayout(file_group)
        
        file_row = QHBoxLayout()
        self.video_path_edit = QLineEdit()
        self.video_path_edit.setPlaceholderText("选择要发布的视频文件...")
        self.video_path_edit.textChanged.connect(self.on_video_file_changed)
        self.browse_button = QPushButton("浏览")
        self.browse_button.clicked.connect(self.browse_video_file)
        
        file_row.addWidget(self.video_path_edit)
        file_row.addWidget(self.browse_button)
        file_layout.addLayout(file_row)
        
        layout.addWidget(file_group)
        
        # 智能内容生成
        content_group = QGroupBox("🤖 AI智能内容")
        content_layout = QVBoxLayout(content_group)
        content_layout.setSpacing(15)

        # AI优化按钮行
        ai_button_row = QHBoxLayout()

        self.ai_optimize_button = QPushButton("🎯 AI优化内容")
        self.ai_optimize_button.clicked.connect(self.optimize_content_with_ai)
        self.ai_optimize_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        # 🔧 新增：刷新按钮（您要求的特征）
        self.refresh_content_btn = QPushButton("🔄 刷新")
        self.refresh_content_btn.clicked.connect(self.refresh_ai_content)
        self.refresh_content_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 15px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.generate_cover_btn = QPushButton("🖼️ AI生成封面")
        self.generate_cover_btn.clicked.connect(self.generate_cover_image)
        self.generate_cover_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.ai_status_label = QLabel()
        self.ai_status_label.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")

        ai_button_row.addWidget(self.ai_optimize_button)
        ai_button_row.addWidget(self.refresh_content_btn)  # 🔧 新增：刷新按钮
        ai_button_row.addWidget(self.generate_cover_btn)
        ai_button_row.addWidget(self.ai_status_label)
        ai_button_row.addStretch()

        content_layout.addLayout(ai_button_row)

        # 内容表单
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(12)
        form_layout.setHorizontalSpacing(15)

        # 标题
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("AI将基于项目内容自动生成标题...")
        self.title_edit.setMinimumHeight(35)
        # 🔧 新增：内容变化时自动保存
        self.title_edit.textChanged.connect(self.save_publish_content)
        form_layout.addRow("📝 标题:", self.title_edit)

        # 描述
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("AI将基于项目内容自动生成描述...")
        self.description_edit.setMaximumHeight(120)
        self.description_edit.setMinimumHeight(80)
        # 🔧 新增：内容变化时自动保存
        self.description_edit.textChanged.connect(self.save_publish_content)
        form_layout.addRow("📄 描述:", self.description_edit)

        # 标签
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("AI将自动生成适合的标签...")
        self.tags_edit.setMinimumHeight(35)
        # 🔧 新增：内容变化时自动保存
        self.tags_edit.textChanged.connect(self.save_publish_content)
        form_layout.addRow("🏷️ 标签:", self.tags_edit)

        # 封面
        cover_widget = QWidget()
        cover_layout = QHBoxLayout(cover_widget)
        cover_layout.setContentsMargins(0, 0, 0, 0)

        self.cover_path_edit = QLineEdit()
        self.cover_path_edit.setPlaceholderText("AI将自动生成适配的封面图片...")
        self.cover_path_edit.setMinimumHeight(35)

        self.browse_cover_btn = QPushButton("📁")
        self.browse_cover_btn.setFixedSize(35, 35)
        self.browse_cover_btn.clicked.connect(self.browse_cover_image)
        self.browse_cover_btn.setToolTip("手动选择封面图片")

        cover_layout.addWidget(self.cover_path_edit)
        cover_layout.addWidget(self.browse_cover_btn)

        form_layout.addRow("🖼️ 封面:", cover_widget)

        content_layout.addLayout(form_layout)
        layout.addWidget(content_group)

        # 🔧 优化：平台选择区域
        platform_group = QGroupBox("🎯 选择发布平台")
        platform_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FF9800;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #fff8f0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #FF9800;
            }
            QCheckBox {
                font-size: 13px;
                padding: 8px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #ddd;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 2px solid #4CAF50;
            }
        """)
        platform_layout = QGridLayout(platform_group)

        self.platform_checkboxes = {}
        all_supported_platforms = self.publisher.get_supported_platforms()

        # 界面显示的主要平台（避免重复显示中英文名称）
        main_platforms = ['douyin', 'bilibili', 'kuaishou', 'xiaohongshu', 'wechat', 'youtube']
        supported_platforms = [p for p in main_platforms if p in all_supported_platforms]

        # 平台图标和显示名称映射
        platform_info = {
            'douyin': {'icon': '🎵', 'name': '抖音'},
            'bilibili': {'icon': '📺', 'name': 'B站'},
            'kuaishou': {'icon': '⚡', 'name': '快手'},
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
            # 🔧 新增：平台选择变化时自动保存
            checkbox.stateChanged.connect(self.save_publish_content)
            self.platform_checkboxes[platform] = checkbox
            platform_layout.addWidget(checkbox, row, col)

            col += 1
            if col >= 3:  # 每行3个
                col = 0
                row += 1
            
        layout.addWidget(platform_group)
        
        # 🔧 优化：发布按钮区域
        button_group = QGroupBox()
        button_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #f9f9f9;
            }
        """)
        button_layout = QHBoxLayout(button_group)

        self.publish_button = QPushButton("🚀 一键发布")
        self.publish_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                min-width: 200px;
                min-height: 50px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #45a049, stop:1 #3d8b40);
                transform: translateY(-2px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3d8b40, stop:1 #2e7d32);
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.publish_button.clicked.connect(self.start_publish)

        self.cancel_button = QPushButton("❌ 取消发布")
        self.cancel_button.setEnabled(False)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel_publish)

        button_layout.addStretch()
        button_layout.addWidget(self.publish_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()

        layout.addWidget(button_group)
        
        # 🔧 优化：进度显示区域
        progress_group = QGroupBox("📊 发布进度")
        progress_group.setVisible(False)
        progress_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #f3f8ff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2196F3;
            }
        """)
        progress_layout = QVBoxLayout(progress_group)

        self.progress_label = QLabel("准备发布...")
        self.progress_label.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 14px;
                padding: 5px;
            }
        """)
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                background-color: #f0f0f0;
                height: 25px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #2196F3);
                border-radius: 6px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        self.progress_group = progress_group  # 保存引用以便控制显示/隐藏
        layout.addWidget(progress_group)
        
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
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "时间", "标题", "平台", "状态", "错误信息"
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
        self.account_table.setColumnCount(3)
        self.account_table.setHorizontalHeaderLabels([
            "平台", "账号名称", "状态"
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
                
            # 🔧 简化：统一使用浏览器自动化发布
            # 检查Selenium是否可用
            if not SELENIUM_AVAILABLE:
                QMessageBox.critical(
                    self, "错误",
                    "浏览器自动化发布器不可用，请检查依赖是否正确安装。"
                )
                return

            # 🔧 优化：Firefox浏览器准备提示
            reply = QMessageBox.question(
                self, "🦊 Firefox一键发布",
                """🚀 Firefox一键发布准备：

1. 确保Firefox浏览器已启动：
   • 打开Firefox浏览器
   • 无需特殊配置，直接使用

2. 在Firefox中手动登录各个平台账号：
   • 抖音创作者平台
   • B站创作中心
   • 其他选中的平台

3. 保持Firefox浏览器开启状态

✨ Firefox更简单：无需命令行启动，直接使用！

是否已完成准备工作并开始发布？""",
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

            # 🔧 优化：统一使用Firefox浏览器自动化发布
            selenium_config = {
                'driver_type': 'firefox',  # 使用Firefox
                'timeout': 30,
                'headless': False,
                'simulation_mode': False,  # 默认真实发布
                'firefox_profile': None,   # 使用默认配置文件
                'firefox_options': {
                    'user_friendly': True,  # 用户友好模式
                    'auto_detect': True     # 自动检测已打开的Firefox
                }
            }

            self.current_worker = SeleniumPublishWorker(
                video_path=self.video_path_edit.text().strip(),
                metadata=metadata,
                platforms=selected_platforms,
                config=selenium_config
            )
            
            # 连接信号
            self.current_worker.progress_updated.connect(self.on_progress_updated)
            self.current_worker.publish_completed.connect(self.on_publish_completed)
            self.current_worker.error_occurred.connect(self.on_publish_error)
            
            # 🔧 优化：更新UI状态
            self.publish_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.progress_group.setVisible(True)  # 显示整个进度组
            self.progress_bar.setValue(0)
            self.progress_label.setText("🚀 开始发布...")
            
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
        """🔧 修复问题3：进度更新"""
        try:
            # 确保进度值在有效范围内
            progress_value = max(0, min(100, int(progress * 100)))
            self.progress_bar.setValue(progress_value)
            self.progress_label.setText(message)

            # 记录进度日志
            logger.info(f"📊 发布进度: {progress_value}% - {message}")

            # 强制刷新UI
            self.progress_bar.repaint()
            self.progress_label.repaint()

        except Exception as e:
            logger.error(f"更新进度失败: {e}")
        
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
        """🔧 优化：重置UI状态"""
        self.publish_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_group.setVisible(False)  # 隐藏整个进度组
        self.current_worker = None

    def load_platform_accounts(self):
        """加载平台账号"""
        try:
            accounts = self.publisher.get_platform_accounts()

            self.account_table.setRowCount(len(accounts))

            for row, account in enumerate(accounts):
                self.account_table.setItem(row, 0, QTableWidgetItem(account['platform_name']))
                self.account_table.setItem(row, 1, QTableWidgetItem(account['account_name']))

                status = "活跃" if account.get('is_active', True) else "禁用"
                self.account_table.setItem(row, 2, QTableWidgetItem(status))

        except Exception as e:
            logger.error(f"加载平台账号失败: {e}")

    def refresh_publish_history(self):
        """刷新发布历史"""
        try:
            records = self.publisher.get_publish_history(limit=100)

            self.history_table.setRowCount(len(records))

            for row, record in enumerate(records):
                # 时间
                created_time = record.get('created_at', '')[:16] if record.get('created_at') else ''
                self.history_table.setItem(row, 0, QTableWidgetItem(created_time))

                # 标题
                title = record.get('published_title', '未知标题')
                self.history_table.setItem(row, 1, QTableWidgetItem(title))

                # 平台
                platform = record.get('platform_name', '')
                self.history_table.setItem(row, 2, QTableWidgetItem(platform))

                # 状态
                status_map = {
                    'published': '已发布',
                    'failed': '失败',
                    'uploading': '上传中',
                    'processing': '处理中'
                }
                status = status_map.get(record.get('status'), record.get('status', ''))
                self.history_table.setItem(row, 3, QTableWidgetItem(status))

                # 错误信息
                error_msg = record.get('error_message', '')
                self.history_table.setItem(row, 4, QTableWidgetItem(error_msg))

            # 更新统计信息
            self.update_statistics()

        except Exception as e:
            logger.error(f"刷新发布历史失败: {e}")

    def update_statistics(self):
        """更新统计信息"""
        try:
            stats = self.publisher.get_statistics(days=30)

            stats_text = f"""
            <h3>统计信息</h3>
            <p><b>总任务数:</b> {stats.get('total_tasks', 0)}</p>
            <p><b>总发布记录:</b> {stats.get('total_records', 0)}</p>

            <h4>任务状态统计</h4>
            """

            status_counts = stats.get('status_counts', {})
            status_names = {
                'completed': '已完成',
                'processing': '处理中',
                'failed': '失败',
                'partially_completed': '部分完成'
            }

            for status, count in status_counts.items():
                status_name = status_names.get(status, status)
                stats_text += f"<p><b>{status_name}:</b> {count}</p>"

            stats_text += "<h4>平台发布统计</h4>"

            platform_stats = stats.get('platform_stats', {})
            platform_names = {
                'bilibili': 'B站',
                'b站': 'B站',
                'douyin': '抖音',
                '抖音': '抖音',
                'tiktok': '抖音',
                'kuaishou': '快手',
                '快手': '快手',
                'xiaohongshu': '小红书',
                '小红书': '小红书',
                'redbook': '小红书',
                'wechat_channels': '微信视频号',
                'youtube': 'YouTube'
            }

            for platform, data in platform_stats.items():
                platform_name = platform_names.get(platform, platform)
                success_rate = (data['success'] / data['total'] * 100) if data['total'] > 0 else 0
                stats_text += f"""
                <p><b>{platform_name}:</b> 总计 {data['total']}, 成功 {data['success']}, 成功率 {success_rate:.1f}%</p>
                """

            self.stats_label.setText(stats_text)

        except Exception as e:
            logger.error(f"更新统计信息失败: {e}")
            self.stats_label.setText("统计信息加载失败")

    def add_platform_account(self):
        """添加平台账号"""
        try:
            # 显示平台选择对话框
            self.show_platform_selection_dialog()
        except Exception as e:
            logger.error(f"添加平台账号失败: {e}")
            QMessageBox.critical(self, "错误", f"添加账号失败: {e}")

    def show_platform_selection_dialog(self):
        """显示平台选择对话框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QListWidget, QListWidgetItem

        dialog = QDialog(self)
        dialog.setWindowTitle("选择要添加的平台")
        dialog.setFixedSize(300, 400)

        layout = QVBoxLayout(dialog)

        # 平台列表
        platform_list = QListWidget()

        # 定义主要平台
        main_platforms = {
            'bilibili': 'B站 (Bilibili)',
            'douyin': '抖音 (TikTok)',
            'kuaishou': '快手 (Kuaishou)',
            'xiaohongshu': '小红书 (RedBook)',
            'wechat_channels': '微信视频号',
            'youtube': 'YouTube Shorts'
        }

        for platform, display_name in main_platforms.items():
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, platform)
            platform_list.addItem(item)

        layout.addWidget(platform_list)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec_() == QDialog.Accepted:
            current_item = platform_list.currentItem()
            if current_item:
                platform = current_item.data(Qt.UserRole)
                platform_name = current_item.text()
                self.start_platform_login(platform, platform_name)

    def start_platform_login(self, platform: str, platform_name: str):
        """启动平台登录流程"""
        try:
            # 创建登录工作线程
            self.login_worker = PlatformLoginWorker(platform, platform_name)
            self.login_worker.login_success.connect(self.on_login_success)
            self.login_worker.login_failed.connect(self.on_login_failed)
            self.login_worker.start()

            # 显示登录进度对话框
            self.show_login_progress_dialog(platform_name)

        except Exception as e:
            logger.error(f"启动平台登录失败: {e}")
            QMessageBox.critical(self, "错误", f"启动登录失败: {e}")

    def show_login_progress_dialog(self, platform_name: str):
        """显示登录进度对话框"""
        from PyQt5.QtWidgets import QProgressDialog

        self.login_progress = QProgressDialog(
            f"正在启动 {platform_name} 登录...\n请在弹出的浏览器中完成登录操作",
            "取消",
            0, 0,
            self
        )
        self.login_progress.setWindowTitle("平台登录")
        self.login_progress.setModal(True)
        self.login_progress.canceled.connect(self.cancel_login)
        self.login_progress.show()

    def cancel_login(self):
        """取消登录"""
        if hasattr(self, 'login_worker') and self.login_worker.isRunning():
            self.login_worker.terminate()
            self.login_worker.wait()

    def on_login_success(self, platform: str, platform_name: str, account_name: str):
        """登录成功"""
        try:
            if hasattr(self, 'login_progress'):
                self.login_progress.close()

            # 刷新账号列表
            self.load_platform_accounts()

            QMessageBox.information(
                self,
                "登录成功",
                f"{platform_name} 账号 '{account_name}' 登录成功！\n登录信息已自动保存。"
            )

        except Exception as e:
            logger.error(f"处理登录成功事件失败: {e}")

    def on_login_failed(self, platform: str, platform_name: str, error_msg: str):
        """登录失败"""
        try:
            if hasattr(self, 'login_progress'):
                self.login_progress.close()

            QMessageBox.warning(
                self,
                "登录失败",
                f"{platform_name} 登录失败：\n{error_msg}\n\n请检查网络连接或重试。"
            )

        except Exception as e:
            logger.error(f"处理登录失败事件失败: {e}")

    def show_simple_account_dialog(self):
        """显示简单的账号添加对话框"""
        from PyQt5.QtWidgets import QDialog, QFormLayout, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("添加平台账号")
        dialog.setModal(True)

        layout = QFormLayout(dialog)

        # 平台选择
        platform_combo = QComboBox()
        platforms = self.publisher.get_supported_platforms()
        platform_names = {
            'bilibili': 'B站 (Bilibili)',
            'b站': 'B站 (Bilibili)',
            'douyin': '抖音 (TikTok)',
            '抖音': '抖音 (TikTok)',
            'tiktok': '抖音 (TikTok)',
            'kuaishou': '快手 (Kuaishou)',
            '快手': '快手 (Kuaishou)',
            'xiaohongshu': '小红书 (RedBook)',
            '小红书': '小红书 (RedBook)',
            'redbook': '小红书 (RedBook)',
            'wechat_channels': '微信视频号',
            'youtube': 'YouTube Shorts'
        }

        for platform in platforms:
            display_name = platform_names.get(platform, platform.upper())
            platform_combo.addItem(display_name, platform)

        layout.addRow("平台:", platform_combo)

        # 账号名称
        account_name_edit = QLineEdit()
        account_name_edit.setPlaceholderText("输入账号显示名称...")
        layout.addRow("账号名称:", account_name_edit)

        # Cookie信息
        cookie_edit = QTextEdit()
        cookie_edit.setPlaceholderText("输入Cookie信息（从浏览器复制）...")
        cookie_edit.setMaximumHeight(100)
        layout.addRow("Cookie:", cookie_edit)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)

        if dialog.exec_() == QDialog.Accepted:
            try:
                platform = platform_combo.currentData()
                account_name = account_name_edit.text().strip()
                cookie_text = cookie_edit.toPlainText().strip()

                if not account_name or not cookie_text:
                    QMessageBox.warning(self, "警告", "请填写完整信息")
                    return

                # 解析Cookie
                cookies = {}
                for item in cookie_text.split(';'):
                    if '=' in item:
                        key, value = item.split('=', 1)
                        cookies[key.strip()] = value.strip()

                # 创建账号
                self.publisher.create_platform_account(
                    platform=platform,
                    account_name=account_name,
                    credentials={'cookies': cookies}
                )

                # 刷新账号列表
                self.load_platform_accounts()

                QMessageBox.information(self, "成功", "账号添加成功！")

            except Exception as e:
                logger.error(f"添加账号失败: {e}")
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
                # 获取所有账号，找到对应的ID
                accounts = self.publisher.get_platform_accounts()
                if current_row < len(accounts):
                    account_id = accounts[current_row]['id']

                    if self.publisher.delete_platform_account(account_id):
                        QMessageBox.information(self, "成功", "账号删除成功！")
                        self.load_platform_accounts()
                    else:
                        QMessageBox.warning(self, "失败", "账号删除失败")

            except Exception as e:
                logger.error(f"删除平台账号失败: {e}")
                QMessageBox.critical(self, "错误", f"删除账号失败: {e}")

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
            # 添加详细的调试信息
            logger.info("🔍 开始AI内容优化...")

            # 首先尝试从项目获取内容
            project_name, source_content = self.get_project_content_for_ai()

            logger.info(f"🔍 项目数据获取结果: project_name={project_name}, content_length={len(source_content) if source_content else 0}")

            if project_name and source_content:
                # 基于项目数据生成内容
                logger.info(f"🎯 使用项目数据生成内容: {project_name}")
                self.generate_content_from_project(project_name, source_content)
            else:
                # 获取当前内容进行优化
                title = self.title_edit.text().strip()
                description = self.description_edit.toPlainText().strip()

                if not title and not description:
                    QMessageBox.warning(self, "警告", "请先加载项目或输入标题/描述")
                    return

                # 获取选中的平台
                selected_platforms = []
                for platform, checkbox in self.platform_checkboxes.items():
                    if checkbox.isChecked():
                        selected_platforms.append(platform)

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

    def generate_content_from_project(self, project_name: str, source_content: str):
        """基于项目数据生成内容"""
        try:
            # 禁用按钮并显示进度
            self.ai_optimize_button.setEnabled(False)
            self.ai_status_label.setText("基于项目数据生成中...")

            # 创建项目内容生成工作线程
            self.project_ai_worker = ProjectContentWorker(project_name, source_content)
            self.project_ai_worker.content_generated.connect(self.on_project_content_generated)
            self.project_ai_worker.error_occurred.connect(self.on_project_content_error)
            self.project_ai_worker.start()

        except Exception as e:
            logger.error(f"启动项目内容生成失败: {e}")
            QMessageBox.critical(self, "错误", f"项目内容生成失败: {e}")
            self._update_ai_button_state()

    def on_ai_optimization_completed(self, optimized_content):
        """AI优化完成"""
        try:
            # 更新界面内容
            self.title_edit.setText(optimized_content.title)
            self.description_edit.setPlainText(optimized_content.description)

            # 更新标签
            if optimized_content.tags:
                tags_text = ', '.join(optimized_content.tags[:10])
                self.tags_edit.setText(tags_text)

            # 🔧 新增：保存AI优化结果到项目
            optimization_data = {
                "title": optimized_content.title,
                "description": optimized_content.description,
                "tags": optimized_content.tags,
                "hashtags": getattr(optimized_content, 'hashtags', []),
                "keywords": getattr(optimized_content, 'keywords', []),
                "platform_specific": getattr(optimized_content, 'platform_specific', {}),
                "optimization_type": "ai_generated"
            }
            self.save_ai_optimization_result(optimization_data)

            # 显示优化结果对话框
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

        # 通用优化结果
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        general_text = f"""
标题: {optimized_content.title}

描述:
{optimized_content.description}

标签: {', '.join(optimized_content.tags)}

话题标签: {', '.join(optimized_content.hashtags)}

关键词: {', '.join(optimized_content.keywords)}
"""

        general_edit = QTextEdit()
        general_edit.setPlainText(general_text)
        general_edit.setReadOnly(True)
        general_layout.addWidget(general_edit)

        tab_widget.addTab(general_tab, "通用优化")

        # 平台特定优化
        for platform, content in optimized_content.platform_specific.items():
            platform_tab = QWidget()
            platform_layout = QVBoxLayout(platform_tab)

            platform_text = f"""
平台: {platform}

标题: {content.get('title', '')}

描述:
{content.get('description', '')}

建议标签: {', '.join(content.get('suggested_hashtags', []))}

优化建议:
{content.get('optimization_tips', '')}
"""

            platform_edit = QTextEdit()
            platform_edit.setPlainText(platform_text)
            platform_edit.setReadOnly(True)
            platform_layout.addWidget(platform_edit)

            tab_widget.addTab(platform_tab, platform.title())

        layout.addWidget(tab_widget)

        # 按钮
        button_layout = QHBoxLayout()

        apply_button = QPushButton("应用优化")
        apply_button.clicked.connect(dialog.accept)

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addWidget(apply_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.exec_()

    def closeEvent(self, event):
        """关闭事件"""
        # 停止定时器
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()

        # 取消正在进行的发布任务
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.terminate()
            self.current_worker.wait()

        # 取消AI优化任务
        if hasattr(self, 'ai_worker') and self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.terminate()
            self.ai_worker.wait()

        event.accept()

    def browse_cover_image(self):
        """浏览选择封面图片"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择封面图片",
                "",
                "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*)"
            )

            if file_path:
                self.cover_path_edit.setText(file_path)
                logger.info(f"选择封面图片: {file_path}")

        except Exception as e:
            logger.error(f"选择封面图片失败: {e}")
            QMessageBox.warning(self, "错误", f"选择封面图片失败: {str(e)}")

    def generate_cover_image(self):
        """AI生成封面图片"""
        try:
            # 获取视频标题作为生成提示
            title = self.title_edit.text().strip()
            if not title:
                QMessageBox.warning(self, "提示", "请先输入视频标题，用于生成封面")
                return

            # 禁用按钮，显示生成中状态
            self.generate_cover_btn.setEnabled(False)
            self.generate_cover_btn.setText("生成中...")

            # 🔧 修复：创建并启动封面生成工作线程，传入图像服务
            self.cover_worker = CoverGenerationWorker(title, self.image_service)
            self.cover_worker.finished.connect(self.on_cover_generated)
            self.cover_worker.error_occurred.connect(self.on_cover_generation_error)
            self.cover_worker.start()

        except Exception as e:
            logger.error(f"启动封面生成失败: {e}")
            QMessageBox.warning(self, "错误", f"启动封面生成失败: {str(e)}")
            self.generate_cover_btn.setEnabled(True)
            self.generate_cover_btn.setText("AI生成")

    def on_cover_generated(self, cover_path: str):
        """封面生成完成"""
        try:
            self.cover_path_edit.setText(cover_path)
            logger.info(f"AI生成封面完成: {cover_path}")
            QMessageBox.information(self, "成功", f"封面生成成功！\n保存位置: {cover_path}")

        except Exception as e:
            logger.error(f"处理生成的封面失败: {e}")

        finally:
            self.generate_cover_btn.setEnabled(True)
            self.generate_cover_btn.setText("AI生成")

    def on_cover_generation_error(self, error_msg: str):
        """封面生成失败"""
        logger.error(f"封面生成失败: {error_msg}")
        QMessageBox.warning(self, "错误", f"封面生成失败: {error_msg}")

        self.generate_cover_btn.setEnabled(True)
        self.generate_cover_btn.setText("AI生成")

    def on_video_file_changed(self):
        """视频文件改变时的处理"""
        video_path = self.video_path_edit.text().strip()
        if video_path and os.path.exists(video_path):
            # 自动触发AI内容优化
            self.auto_optimize_content()

    def auto_optimize_content(self):
        """自动优化内容（当有项目加载时）"""
        try:
            # 🔧 修复：增强项目检测逻辑
            project_manager = None

            # 方式1：从服务管理器获取
            try:
                from src.core.service_manager import ServiceManager
                service_manager = ServiceManager()
                project_manager = service_manager.get_service('project_manager')
            except Exception as e:
                logger.debug(f"从服务管理器获取项目管理器失败: {e}")

            # 方式2：从主窗口获取
            if not project_manager:
                try:
                    main_window = self.get_main_window()
                    if main_window and hasattr(main_window, 'project_manager'):
                        project_manager = main_window.project_manager
                        logger.debug("从主窗口获取项目管理器成功")
                except Exception as e:
                    logger.debug(f"从主窗口获取项目管理器失败: {e}")

            # 方式3：从应用控制器获取
            if not project_manager:
                try:
                    from src.core.app_controller import AppController
                    app_controller = AppController()
                    if hasattr(app_controller, 'project_manager'):
                        project_manager = app_controller.project_manager
                        logger.debug("从应用控制器获取项目管理器成功")
                except Exception as e:
                    logger.debug(f"从应用控制器获取项目管理器失败: {e}")

            # 检查项目状态
            if project_manager and hasattr(project_manager, 'current_project') and project_manager.current_project:
                project_name = getattr(project_manager.current_project, 'get', lambda x, default: default)('project_name', '未知项目')
                logger.info(f"检测到当前项目: {project_name}，自动生成AI内容...")
                self.optimize_content_with_ai()
            else:
                logger.info("未检测到当前项目，跳过自动内容生成")

        except Exception as e:
            logger.debug(f"自动内容优化失败: {e}")

    def get_project_content_for_ai(self):
        """获取项目内容用于AI生成"""
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
            logger.info(f"🔍 项目管理器属性: {[attr for attr in dir(project_manager) if not attr.startswith('_')][:20]}")

            if hasattr(project_manager, 'current_project'):
                logger.info(f"🔍 current_project类型: {type(project_manager.current_project)}")
                logger.info(f"🔍 current_project值: {project_manager.current_project}")

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

    def on_project_content_generated(self, content: dict):
        """项目内容生成完成"""
        try:
            self.title_edit.setText(content.get('title', ''))
            self.description_edit.setPlainText(content.get('description', ''))
            self.tags_edit.setText(content.get('tags', ''))

            # 🔧 新增：保存项目内容生成结果
            optimization_data = {
                "title": content.get('title', ''),
                "description": content.get('description', ''),
                "tags": content.get('tags', '').split(',') if content.get('tags') else [],
                "optimization_type": "project_based"
            }
            self.save_ai_optimization_result(optimization_data)

            logger.info("✅ 基于项目数据的AI内容生成完成")
            QMessageBox.information(self, "成功", "基于项目数据的AI内容生成完成！")

        except Exception as e:
            logger.error(f"设置AI生成内容失败: {e}")
        finally:
            self.ai_optimize_button.setEnabled(True)
            self.ai_status_label.setText("AI优化可用")

    def on_project_content_error(self, error_msg: str):
        """项目内容生成错误"""
        logger.error(f"项目内容生成失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"项目内容生成失败: {error_msg}")
        self.ai_optimize_button.setEnabled(True)
        self.ai_status_label.setText("AI优化可用")

    def get_main_window(self):
        """获取主窗口"""
        try:
            # 向上遍历父级窗口，找到主窗口
            widget = self
            while widget:
                if hasattr(widget, 'project_manager') or widget.__class__.__name__ == 'ModernMainWindow':
                    return widget
                widget = widget.parent()
            return None
        except Exception as e:
            logger.debug(f"获取主窗口失败: {e}")
            return None

    def save_publish_content(self):
        """🔧 新增：保存发布内容到项目"""
        try:
            # 获取项目管理器
            main_window = self.get_main_window()
            if not main_window or not hasattr(main_window, 'project_manager'):
                return

            project_manager = main_window.project_manager
            if not project_manager or not project_manager.current_project:
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
            logger.debug(f"保存发布内容失败: {e}")  # 使用debug级别，避免频繁日志

    def load_project_publish_content(self):
        """🔧 新增：从项目加载发布内容"""
        try:
            # 获取项目管理器
            main_window = self.get_main_window()
            if not main_window or not hasattr(main_window, 'project_manager'):
                return

            project_manager = main_window.project_manager
            if not project_manager or not project_manager.current_project:
                return

            # 获取发布内容
            publish_content = project_manager.get_publish_content()

            # 临时断开信号连接，避免触发保存
            self.title_edit.textChanged.disconnect()
            self.description_edit.textChanged.disconnect()
            self.tags_edit.textChanged.disconnect()

            try:
                # 加载内容到界面
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

                # 显示加载信息
                if any([publish_content.get("title"), publish_content.get("description"), publish_content.get("tags")]):
                    last_time = publish_content.get("last_generated_time", "")
                    if last_time:
                        from datetime import datetime
                        try:
                            dt = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                            time_str = dt.strftime("%m-%d %H:%M")
                            logger.info(f"✅ 已加载项目发布内容 (最后更新: {time_str})")
                        except:
                            logger.info("✅ 已加载项目发布内容")
                    else:
                        logger.info("✅ 已加载项目发布内容")

            finally:
                # 重新连接信号
                self.title_edit.textChanged.connect(self.save_publish_content)
                self.description_edit.textChanged.connect(self.save_publish_content)
                self.tags_edit.textChanged.connect(self.save_publish_content)

        except Exception as e:
            logger.error(f"加载项目发布内容失败: {e}")

    def save_ai_optimization_result(self, optimization_data: dict):
        """🔧 新增：保存AI优化结果到项目历史"""
        try:
            # 获取项目管理器
            main_window = self.get_main_window()
            if not main_window or not hasattr(main_window, 'project_manager'):
                return

            project_manager = main_window.project_manager
            if not project_manager or not project_manager.current_project:
                return

            # 保存AI优化历史
            project_manager.add_ai_optimization_history(optimization_data)
            logger.info("✅ AI优化结果已保存到项目历史")

        except Exception as e:
            logger.error(f"保存AI优化结果失败: {e}")

    def auto_detect_project_video(self):
        """🔧 新增：自动检测项目视频文件"""
        try:
            # 获取项目管理器
            main_window = self.get_main_window()
            if not main_window or not hasattr(main_window, 'project_manager'):
                return

            project_manager = main_window.project_manager
            if not project_manager or not project_manager.current_project:
                return

            # 获取项目路径
            project_path = project_manager.current_project.get('project_path', '')
            if not project_path or not os.path.exists(project_path):
                return

            # 查找项目中的final_video.mp4
            video_candidates = [
                os.path.join(project_path, 'final_video.mp4'),
                os.path.join(project_path, 'output.mp4'),
                os.path.join(project_path, 'video.mp4')
            ]

            # 也检查videos子目录
            videos_dir = os.path.join(project_path, 'videos')
            if os.path.exists(videos_dir):
                for file in os.listdir(videos_dir):
                    if file.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                        video_candidates.append(os.path.join(videos_dir, file))

            # 查找存在的视频文件
            for video_path in video_candidates:
                if os.path.exists(video_path):
                    # 检查当前是否已经设置了视频路径
                    current_path = self.video_path_edit.text().strip()
                    if not current_path or not os.path.exists(current_path):
                        self.video_path_edit.setText(video_path)
                        logger.info(f"✅ 自动检测到项目视频: {video_path}")
                        return

            logger.debug("未找到项目视频文件")

        except Exception as e:
            logger.debug(f"自动检测项目视频失败: {e}")

    def get_project_video_info(self) -> dict:
        """🔧 新增：获取项目视频信息，用于调试"""
        try:
            # 获取项目管理器
            main_window = self.get_main_window()
            if not main_window or not hasattr(main_window, 'project_manager'):
                return {}

            project_manager = main_window.project_manager
            if not project_manager or not project_manager.current_project:
                return {}

            project_path = project_manager.current_project.get('project_path', '')
            if not project_path:
                return {}

            info = {
                'project_path': project_path,
                'project_exists': os.path.exists(project_path),
                'video_files': []
            }

            if os.path.exists(project_path):
                # 列出项目目录中的所有视频文件
                for root, dirs, files in os.walk(project_path):
                    for file in files:
                        if file.endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, project_path)
                            info['video_files'].append({
                                'name': file,
                                'relative_path': rel_path,
                                'full_path': full_path,
                                'exists': os.path.exists(full_path),
                                'size': os.path.getsize(full_path) if os.path.exists(full_path) else 0
                            })

            return info

        except Exception as e:
            logger.error(f"获取项目视频信息失败: {e}")
            return {}

    def refresh_ai_content(self):
        """🔄 刷新AI内容 - 您要求的刷新功能"""
        try:
            logger.info("🔄 开始刷新AI内容...")

            # 清空当前内容
            self.title_edit.clear()
            self.description_edit.clear()
            self.tags_edit.clear()

            # 重新生成AI内容
            self.optimize_content_with_ai()

            logger.info("✅ AI内容刷新完成")

        except Exception as e:
            logger.error(f"刷新AI内容失败: {e}")
            QMessageBox.warning(self, "刷新失败", f"刷新AI内容时出现错误:\n{e}")
