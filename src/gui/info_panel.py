"""
信息面板组件
显示项目状态、系统状态、进度信息等
"""

import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QFrame, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QPainter, QBrush, QColor

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.logger import logger


class InfoPanel(QWidget):
    """信息面板组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.project_manager = None
        self.init_ui()
        self.setup_timer()
        
    def init_ui(self):
        """初始化界面"""
        self.setFixedWidth(280)
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-left: 1px solid #e9ecef;
            }
        """)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f1f3f4;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #c1c8cd;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a8b1b8;
            }
        """)
        
        # 内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)
        
        # 添加各个信息区块
        self.create_project_info_section(content_layout)
        self.create_help_section(content_layout)
        self.create_system_status_section(content_layout)
        self.create_progress_section(content_layout)
        
        # 添加弹性空间
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
    def create_section_header(self, title, icon=""):
        """创建区块标题"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # 图标和标题
        title_label = QLabel(f"{icon} {title}")
        title_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        title_label.setStyleSheet("color: #495057; margin-bottom: 5px;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        return header_widget
        
    def create_info_item(self, label, value="", color="#6c757d"):
        """创建信息项"""
        logger.debug(f"开始创建信息项: {label}")

        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)  # 改为水平布局
        item_layout.setContentsMargins(8, 4, 8, 4)
        item_layout.setSpacing(8)

        # 标签
        label_widget = QLabel(label)
        label_widget.setFont(QFont("Microsoft YaHei", 9))
        label_widget.setStyleSheet("color: #6c757d;")
        label_widget.setMinimumWidth(40)

        # 状态指示器
        indicator_widget = QLabel("●")
        indicator_widget.setFont(QFont("Microsoft YaHei", 12))
        indicator_widget.setStyleSheet(f"color: {color};")
        indicator_widget.setFixedWidth(16)

        # 值
        value_widget = QLabel(value)
        value_widget.setFont(QFont("Microsoft YaHei", 9))
        value_widget.setStyleSheet("color: #333333; font-weight: 500;")
        value_widget.setWordWrap(True)

        item_layout.addWidget(label_widget)
        item_layout.addWidget(indicator_widget)
        item_layout.addWidget(value_widget)
        item_layout.addStretch()

        # 存储标签以便更新
        item_widget.value_label = value_widget
        item_widget.indicator_label = indicator_widget  # 添加指示器标签

        logger.debug(f"信息项创建完成: {label}, 属性已设置: value_label={hasattr(item_widget, 'value_label')}, indicator_label={hasattr(item_widget, 'indicator_label')}")

        return item_widget
        
    def create_project_info_section(self, parent_layout):
        """创建项目信息区块"""
        # 标题
        header = self.create_section_header("项目信息", "📁")
        parent_layout.addWidget(header)
        
        # 项目信息容器
        self.project_info_container = QWidget()
        project_layout = QVBoxLayout(self.project_info_container)
        project_layout.setContentsMargins(10, 10, 10, 10)
        project_layout.setSpacing(12)
        
        # 设置容器样式
        self.project_info_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            }
        """)
        
        # 项目名称
        self.project_name_item = self.create_info_item("项目名称", "未选择项目")
        project_layout.addWidget(self.project_name_item)
        
        # 创建时间
        self.created_time_item = self.create_info_item("创建时间", "-")
        project_layout.addWidget(self.created_time_item)
        
        # 最后修改
        self.modified_time_item = self.create_info_item("最后修改", "-")
        project_layout.addWidget(self.modified_time_item)
        
        parent_layout.addWidget(self.project_info_container)
        
    def create_help_section(self, parent_layout):
        """创建帮助区块"""
        # 标题
        header = self.create_section_header("帮助", "💡")
        parent_layout.addWidget(header)
        
        # 帮助容器
        help_container = QWidget()
        help_layout = QVBoxLayout(help_container)
        help_layout.setContentsMargins(10, 10, 10, 10)
        help_layout.setSpacing(8)
        
        help_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            }
        """)
        
        # 帮助项目
        help_items = [
            ("🔗", "官网"),
            ("📖", "文档"),
            ("🎯", "教程"),
            ("💬", "配置参数"),
            ("📞", "联系客服")
        ]
        
        for icon, text in help_items:
            help_item = QLabel(f"{icon} {text}")
            help_item.setFont(QFont("Microsoft YaHei", 9))
            help_item.setStyleSheet("""
                QLabel {
                    color: #495057;
                    padding: 4px 0px;
                    border-radius: 4px;
                }
                QLabel:hover {
                    background-color: #f8f9fa;
                    color: #007bff;
                }
            """)
            help_item.setCursor(Qt.PointingHandCursor)
            help_layout.addWidget(help_item)
        
        parent_layout.addWidget(help_container)
        
    def create_system_status_section(self, parent_layout):
        """创建系统状态区块"""
        # 标题
        header = self.create_section_header("系统状态", "⚙️")
        parent_layout.addWidget(header)
        
        # 状态容器
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(10, 10, 10, 10)
        status_layout.setSpacing(12)
        
        status_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            }
        """)
        
        # CPU状态 - 添加调试日志
        logger.debug("创建CPU状态项...")
        self.cpu_item = self.create_info_item("CPU", "●", "#28a745")
        logger.debug(f"CPU状态项创建完成，属性: value_label={hasattr(self.cpu_item, 'value_label')}, indicator_label={hasattr(self.cpu_item, 'indicator_label')}")
        status_layout.addWidget(self.cpu_item)

        # 内存状态 - 添加调试日志
        logger.debug("创建内存状态项...")
        self.memory_item = self.create_info_item("内存", "●", "#ffc107")
        logger.debug(f"内存状态项创建完成，属性: value_label={hasattr(self.memory_item, 'value_label')}, indicator_label={hasattr(self.memory_item, 'indicator_label')}")
        status_layout.addWidget(self.memory_item)

        # 网络状态 - 添加调试日志
        logger.debug("创建网络状态项...")
        self.network_item = self.create_info_item("网络", "●", "#28a745")
        logger.debug(f"网络状态项创建完成，属性: value_label={hasattr(self.network_item, 'value_label')}, indicator_label={hasattr(self.network_item, 'indicator_label')}")
        status_layout.addWidget(self.network_item)
        
        parent_layout.addWidget(status_container)
        
    def create_progress_section(self, parent_layout):
        """创建进度区块"""
        # 标题
        header = self.create_section_header("整体进度", "📊")
        parent_layout.addWidget(header)
        
        # 进度容器
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(10, 10, 10, 10)
        progress_layout.setSpacing(12)
        
        progress_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            }
        """)
        
        # 🔧 修复：创建真实的项目进度项目
        self.progress_items = {}

        progress_names = [
            ("文本创作", "text_creation"),
            ("图像生成", "image_generation"),
            ("音频合成", "voice_generation"),
            ("视频制作", "video_composition")
        ]

        for name, key in progress_names:
            progress_item = self.create_progress_item(name, 0)  # 初始值为0
            progress_layout.addWidget(progress_item)
            self.progress_items[key] = progress_item
        
        parent_layout.addWidget(progress_container)
        
    def create_progress_item(self, name, value):
        """创建进度项"""
        item_widget = QWidget()
        item_layout = QVBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(4)
        
        # 名称和百分比
        header_layout = QHBoxLayout()
        name_label = QLabel(name)
        name_label.setFont(QFont("Microsoft YaHei", 8))
        name_label.setStyleSheet("color: #495057;")
        
        percent_label = QLabel(f"{value}%")
        percent_label.setFont(QFont("Microsoft YaHei", 8))
        percent_label.setStyleSheet("color: #6c757d;")
        
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        header_layout.addWidget(percent_label)
        
        # 进度条
        progress_bar = QProgressBar()
        progress_bar.setMaximum(100)
        progress_bar.setValue(value)
        progress_bar.setFixedHeight(6)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #e9ecef;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 3px;
            }
        """)
        
        item_layout.addLayout(header_layout)
        item_layout.addWidget(progress_bar)
        
        # 存储进度条和百分比标签以便更新
        item_widget.progress_bar = progress_bar
        item_widget.percent_label = percent_label
        
        return item_widget
        
    def setup_timer(self):
        """设置定时器更新状态"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(5000)  # 每5秒更新一次
        
    def update_status(self):
        """更新状态信息"""
        try:
            # 更新项目信息
            self.update_project_info()
            
            # 更新系统状态
            self.update_system_status()
            
        except Exception as e:
            logger.error(f"更新信息面板状态失败: {e}")
            
    def update_project_info(self):
        """更新项目信息"""
        try:
            if self.project_manager and self.project_manager.current_project:
                project = self.project_manager.current_project
                
                # 项目名称
                project_name = project.get('project_name', '未命名项目')
                self.project_name_item.value_label.setText(project_name)
                
                # 创建时间
                created_time = project.get('created_time', '-')
                if created_time and created_time != '-':
                    # 格式化时间显示
                    try:
                        from datetime import datetime
                        if isinstance(created_time, str):
                            dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                            formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                        else:
                            formatted_time = str(created_time)
                        self.created_time_item.value_label.setText(formatted_time)
                    except:
                        self.created_time_item.value_label.setText(created_time)
                
                # 最后修改时间
                modified_time = project.get('last_modified', '-')
                if modified_time and modified_time != '-':
                    try:
                        from datetime import datetime
                        if isinstance(modified_time, str):
                            dt = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
                            formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                        else:
                            formatted_time = str(modified_time)
                        self.modified_time_item.value_label.setText(formatted_time)
                    except:
                        self.modified_time_item.value_label.setText(modified_time)

                # 🔧 修复：更新真实的项目进度
                self._update_project_progress(project)

            else:
                # 没有项目时显示默认信息
                self.project_name_item.value_label.setText("未选择项目")
                self.created_time_item.value_label.setText("-")
                self.modified_time_item.value_label.setText("-")

                # 重置进度显示
                self._reset_progress_display()
                
        except Exception as e:
            logger.error(f"更新项目信息失败: {e}")
            
    def update_system_status(self):
        """更新系统状态"""
        try:
            # 🔧 修复：实现真实的系统状态监控

            # 更新GPU状态
            self._update_gpu_status()

            # 更新内存状态
            self._update_memory_status()

            # 更新网络状态
            self._update_network_status()

        except Exception as e:
            logger.error(f"更新系统状态失败: {e}")

    def _update_gpu_status(self):
        """更新GPU状态"""
        try:
            # 检查GPU可用性
            gpu_available = False
            gpu_info = "未检测到"
            gpu_color = "#dc3545"  # 红色

            try:
                import torch
                if torch.cuda.is_available():
                    gpu_count = torch.cuda.device_count()
                    current_device = torch.cuda.current_device()
                    gpu_name = torch.cuda.get_device_name(current_device)
                    gpu_memory = torch.cuda.get_device_properties(current_device).total_memory
                    gpu_memory_gb = gpu_memory / (1024**3)

                    gpu_available = True
                    gpu_info = f"{gpu_name[:20]}... ({gpu_memory_gb:.1f}GB)"
                    gpu_color = "#28a745"  # 绿色

            except ImportError:
                # 尝试其他GPU检测方法
                try:
                    import subprocess
                    result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        lines = result.stdout.strip().split('\n')
                        if lines:
                            gpu_name, memory = lines[0].split(', ')
                            gpu_available = True
                            gpu_info = f"{gpu_name[:20]}... ({int(memory)/1024:.1f}GB)"
                            gpu_color = "#28a745"  # 绿色
                except:
                    pass

            # 更新GPU状态显示 - 增强错误检查
            if hasattr(self, 'cpu_item'):
                if hasattr(self.cpu_item, 'value_label') and hasattr(self.cpu_item, 'indicator_label'):
                    self.cpu_item.value_label.setText(gpu_info)
                    self.cpu_item.indicator_label.setStyleSheet(f"color: {gpu_color};")
                else:
                    logger.warning(f"cpu_item缺少必要属性: value_label={hasattr(self.cpu_item, 'value_label')}, indicator_label={hasattr(self.cpu_item, 'indicator_label')}")
            else:
                logger.warning("cpu_item属性不存在")

        except Exception as e:
            logger.error(f"更新GPU状态失败: {e}")

    def _update_memory_status(self):
        """更新内存状态"""
        try:
            memory_info = "未知"
            memory_color = "#6c757d"  # 灰色

            try:
                import psutil
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_used_gb = memory.used / (1024**3)
                memory_total_gb = memory.total / (1024**3)

                memory_info = f"{memory_used_gb:.1f}/{memory_total_gb:.1f}GB ({memory_percent:.1f}%)"

                # 根据内存使用率设置颜色
                if memory_percent < 70:
                    memory_color = "#28a745"  # 绿色
                elif memory_percent < 85:
                    memory_color = "#ffc107"  # 黄色
                else:
                    memory_color = "#dc3545"  # 红色

            except ImportError:
                memory_info = "需要psutil库"
                memory_color = "#6c757d"

            # 更新内存状态显示 - 增强错误检查
            if hasattr(self, 'memory_item'):
                if hasattr(self.memory_item, 'value_label') and hasattr(self.memory_item, 'indicator_label'):
                    self.memory_item.value_label.setText(memory_info)
                    self.memory_item.indicator_label.setStyleSheet(f"color: {memory_color};")
                else:
                    logger.warning(f"memory_item缺少必要属性: value_label={hasattr(self.memory_item, 'value_label')}, indicator_label={hasattr(self.memory_item, 'indicator_label')}")
            else:
                logger.warning("memory_item属性不存在")

        except Exception as e:
            logger.error(f"更新内存状态失败: {e}")

    def _update_network_status(self):
        """更新网络状态"""
        try:
            network_info = "未知"
            network_color = "#6c757d"  # 灰色

            try:
                import socket
                import time

                # 测试网络连接
                start_time = time.time()
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                ping_time = (time.time() - start_time) * 1000

                network_info = f"已连接 ({ping_time:.0f}ms)"

                # 根据延迟设置颜色
                if ping_time < 100:
                    network_color = "#28a745"  # 绿色
                elif ping_time < 300:
                    network_color = "#ffc107"  # 黄色
                else:
                    network_color = "#dc3545"  # 红色

            except:
                network_info = "连接异常"
                network_color = "#dc3545"  # 红色

            # 更新网络状态显示 - 增强错误检查
            if hasattr(self, 'network_item'):
                if hasattr(self.network_item, 'value_label') and hasattr(self.network_item, 'indicator_label'):
                    self.network_item.value_label.setText(network_info)
                    self.network_item.indicator_label.setStyleSheet(f"color: {network_color};")
                else:
                    logger.warning(f"network_item缺少必要属性: value_label={hasattr(self.network_item, 'value_label')}, indicator_label={hasattr(self.network_item, 'indicator_label')}")
            else:
                logger.warning("network_item属性不存在")

        except Exception as e:
            logger.error(f"更新网络状态失败: {e}")
            
    def set_project_manager(self, project_manager):
        """设置项目管理器"""
        self.project_manager = project_manager
        self.update_project_info()

    def _update_project_progress(self, project):
        """更新项目进度"""
        try:
            # 计算文本创作进度
            text_progress = self._calculate_text_creation_progress(project)
            self._update_progress_item('text_creation', text_progress)

            # 计算图像生成进度
            image_progress = self._calculate_image_generation_progress(project)
            self._update_progress_item('image_generation', image_progress)

            # 计算音频合成进度
            voice_progress = self._calculate_voice_generation_progress(project)
            self._update_progress_item('voice_generation', voice_progress)

            # 计算视频制作进度
            video_progress = self._calculate_video_composition_progress(project)
            self._update_progress_item('video_composition', video_progress)

        except Exception as e:
            logger.error(f"更新项目进度失败: {e}")

    def _calculate_text_creation_progress(self, project):
        """计算文本创作进度"""
        try:
            text_creation = project.get('text_creation', {})

            # 检查是否有原始文本
            has_original = bool(text_creation.get('original_text', '').strip())

            # 检查是否有改写文本
            has_rewritten = bool(text_creation.get('rewritten_text', '').strip())

            if has_rewritten:
                return 100
            elif has_original:
                return 50
            else:
                return 0

        except Exception as e:
            logger.error(f"计算文本创作进度失败: {e}")
            return 0

    def _calculate_image_generation_progress(self, project):
        """计算图像生成进度"""
        try:
            # 检查图像生成数据 - 使用shot_image_mappings
            shot_mappings = project.get('shot_image_mappings', {})

            if not shot_mappings:
                logger.debug("没有找到shot_image_mappings数据")
                return 0

            total_shots = len(shot_mappings)
            generated_shots = 0

            for shot_key, mapping in shot_mappings.items():
                # 检查是否有生成的图像
                has_main_image = bool(mapping.get('main_image_path'))
                has_generated_images = bool(mapping.get('generated_images'))
                status = mapping.get('status', '未生成')

                if has_main_image or has_generated_images or status == '已生成':
                    generated_shots += 1

            if total_shots > 0:
                progress = int((generated_shots / total_shots) * 100)
                logger.debug(f"图像生成进度: {generated_shots}/{total_shots} = {progress}%")
                return progress
            else:
                return 0

        except Exception as e:
            logger.error(f"计算图像生成进度失败: {e}")
            return 0

    def _calculate_voice_generation_progress(self, project):
        """计算音频合成进度"""
        try:
            voice_data = project.get('voice_generation', {})
            voice_segments = voice_data.get('voice_segments', [])

            if not voice_segments:
                logger.debug("没有找到voice_segments数据")
                return 0

            total_segments = len(voice_segments)
            generated_segments = 0

            for segment in voice_segments:
                # 检查多种可能的状态字段
                has_audio_file = bool(segment.get('audio_file') or segment.get('audio_path'))
                status = segment.get('status', '未生成')

                if has_audio_file or status in ['completed', '已生成', '完成']:
                    generated_segments += 1

            if total_segments > 0:
                progress = int((generated_segments / total_segments) * 100)
                logger.debug(f"配音生成进度: {generated_segments}/{total_segments} = {progress}%")
                return progress
            else:
                return 0

        except Exception as e:
            logger.error(f"计算音频合成进度失败: {e}")
            return 0

    def _calculate_video_composition_progress(self, project):
        """计算视频制作进度"""
        try:
            video_data = project.get('video_composition', {})

            # 检查是否有视频合成配置
            has_config = bool(video_data.get('composition_settings'))

            # 检查是否有输出文件
            has_output = bool(video_data.get('output_file'))

            # 检查合成状态
            status = video_data.get('status', '')

            if status == 'completed' and has_output:
                return 100
            elif status == 'processing':
                return 75
            elif has_config:
                return 25
            else:
                return 0

        except Exception as e:
            logger.error(f"计算视频制作进度失败: {e}")
            return 0

    def _update_progress_item(self, key, value):
        """更新进度项显示"""
        try:
            if key in self.progress_items:
                item = self.progress_items[key]
                item.progress_bar.setValue(value)
                item.percent_label.setText(f"{value}%")

                # 根据进度设置颜色
                if value == 100:
                    color = "#28a745"  # 绿色
                elif value >= 50:
                    color = "#007bff"  # 蓝色
                elif value > 0:
                    color = "#ffc107"  # 黄色
                else:
                    color = "#e9ecef"  # 灰色

                item.progress_bar.setStyleSheet(f"""
                    QProgressBar {{
                        border: none;
                        background-color: #e9ecef;
                        border-radius: 3px;
                    }}
                    QProgressBar::chunk {{
                        background-color: {color};
                        border-radius: 3px;
                    }}
                """)

        except Exception as e:
            logger.error(f"更新进度项 {key} 失败: {e}")

    def _reset_progress_display(self):
        """重置进度显示"""
        try:
            for key in self.progress_items:
                self._update_progress_item(key, 0)
        except Exception as e:
            logger.error(f"重置进度显示失败: {e}")
