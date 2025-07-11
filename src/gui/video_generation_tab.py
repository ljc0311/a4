# -*- coding: utf-8 -*-
"""
视频生成标签页
用于将配音、图像等数据传递到视频生成界面，进行视频生成操作
"""

import os
import json
import asyncio
import time
from typing import Dict, List, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QComboBox, QFormLayout, QGroupBox, QMessageBox,
    QProgressBar, QTextEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QFrame,
    QSplitter, QHeaderView, QAbstractItemView, QSlider
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap

from src.utils.logger import logger
from src.utils.project_manager import StoryboardProjectManager
from src.utils.shot_id_manager import ShotIDManager, ShotMapping


class VideoGenerationWorker(QThread):
    """视频生成工作线程"""
    
    progress_updated = pyqtSignal(int, str)  # 进度, 消息
    video_generated = pyqtSignal(str, bool, str)  # 视频路径, 成功状态, 错误信息
    
    def __init__(self, scene_data, generation_config, project_manager, project_name):
        super().__init__()
        self.scene_data = scene_data
        self.generation_config = generation_config
        self.project_manager = project_manager
        self.project_name = project_name
        self.is_cancelled = False
        self._current_loop = None  # 保存当前事件循环引用

    def cancel(self):
        """取消任务"""
        self.is_cancelled = True
        logger.info("视频生成任务已标记为取消")

        # 如果有正在运行的事件循环，尝试取消其中的任务
        if self._current_loop and not self._current_loop.is_closed():
            try:
                # 获取循环中的所有任务并取消
                pending_tasks = [task for task in asyncio.all_tasks(self._current_loop)
                               if not task.done()]
                for task in pending_tasks:
                    task.cancel()
                logger.info(f"已取消 {len(pending_tasks)} 个异步任务")
            except Exception as e:
                logger.warning(f"取消异步任务时出错: {e}")

    def run(self):
        """运行视频生成（修复Event loop问题）"""
        loop = None
        try:
            # 检查是否已被取消
            if self.is_cancelled:
                logger.info("任务在启动前已被取消")
                self.video_generated.emit("", False, "任务已取消")
                return

            # 确保在新线程中创建新的事件循环
            try:
                # 检查是否已有事件循环
                existing_loop = asyncio.get_event_loop()
                if existing_loop and not existing_loop.is_closed():
                    existing_loop.close()
            except RuntimeError:
                # 没有现有循环，这是正常的
                pass

            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._current_loop = loop  # 保存循环引用

            # 运行异步生成
            result = loop.run_until_complete(self._generate_video_async())

            if result and result.success:
                self.video_generated.emit(result.video_path, True, "")
            else:
                error_msg = result.error_message if result else "未知错误"
                self.video_generated.emit("", False, error_msg)

        except asyncio.CancelledError:
            logger.warning("视频生成任务被取消")
            self.video_generated.emit("", False, "视频生成任务被取消，请重试")
        except Exception as e:
            logger.error(f"视频生成线程异常: {e}")
            # 提供更友好的错误信息
            if "CancelledError" in str(e):
                error_msg = "视频生成任务被取消，请重试"
            elif "504" in str(e):
                error_msg = "服务器响应超时，请稍后重试"
            elif "timeout" in str(e).lower():
                error_msg = "网络连接超时，请检查网络连接后重试"
            elif "different loop" in str(e):
                error_msg = "事件循环冲突，请重试"
            else:
                error_msg = str(e)
            self.video_generated.emit("", False, error_msg)
        finally:
            # 安全关闭事件循环
            if 'loop' in locals() and loop and not loop.is_closed():
                try:
                    # 取消所有未完成的任务
                    try:
                        pending = asyncio.all_tasks(loop)
                        if pending:
                            for task in pending:
                                if not task.done():
                                    task.cancel()

                            # 等待任务取消完成，设置较短的超时时间
                            try:
                                loop.run_until_complete(
                                    asyncio.wait_for(
                                        asyncio.gather(*pending, return_exceptions=True),
                                        timeout=5.0
                                    )
                                )
                            except asyncio.TimeoutError:
                                logger.warning("等待任务取消超时，强制关闭")
                            except Exception as gather_error:
                                logger.warning(f"等待任务取消时出错: {gather_error}")
                    except Exception as task_error:
                        logger.warning(f"处理未完成任务时出错: {task_error}")

                    # 关闭事件循环
                    loop.close()
                except Exception as cleanup_error:
                    logger.warning(f"关闭事件循环时出错: {cleanup_error}")
                finally:
                    # 确保清理事件循环引用
                    try:
                        asyncio.set_event_loop(None)
                    except Exception:
                        pass
    
    async def _generate_video_async(self):
        """异步生成视频"""
        # 定义结果类
        class Result:
            def __init__(self, success, video_path="", error_message=""):
                self.success = success
                self.video_path = video_path
                self.error_message = error_message

        try:
            # 检查是否已被取消
            if self.is_cancelled:
                logger.info("异步任务在开始前已被取消")
                return Result(False, "", "任务已取消")

            from src.processors.video_processor import VideoProcessor
            from src.core.service_manager import ServiceManager

            # 🔧 修复：使用共享的服务管理器实例，避免引擎状态冲突
            service_manager = ServiceManager()  # ServiceManager已经是单例
            processor = VideoProcessor(service_manager)

            # 🔧 调试：检查引擎状态
            scene_id = self.scene_data.get('shot_id', 'unknown')
            logger.info(f"VideoGenerationWorker启动 - 场景ID: {scene_id}")
            logger.info(f"ServiceManager实例ID: {id(service_manager)}")

            # 更新进度
            self.progress_updated.emit(10, "准备视频生成...")

            # 从场景数据生成视频
            image_path = self.scene_data.get('image_path', '')

            # 获取提示词 - 优先使用scene_data中的prompt字段
            original_prompt = self.scene_data.get('prompt', '') or self._get_prompt_from_file() or self.scene_data.get('enhanced_description', self.scene_data.get('description', ''))

            # 优化提示词以适合视频生成
            shot_id = self.scene_data.get('shot_id', '')
            duration = self.generation_config.get('duration', 5.0)

            # 调用视频提示词优化
            try:
                from src.processors.cogvideox_prompt_optimizer import CogVideoXPromptOptimizer
                optimizer = CogVideoXPromptOptimizer()
                shot_info = {'shot_type': 'medium_shot', 'camera_angle': 'eye_level', 'movement': 'static'}
                optimized_prompt = optimizer.optimize_for_video(original_prompt, shot_info, duration)
                logger.info(f"视频提示词优化成功: {original_prompt[:50]}... -> {optimized_prompt[:50]}...")
            except Exception as e:
                logger.warning(f"视频提示词优化失败，使用原始提示词: {e}")
                optimized_prompt = original_prompt

            logger.info(f"视频生成提示词: {optimized_prompt}")

            if not image_path or not os.path.exists(image_path):
                raise Exception(f"图像文件不存在: {image_path}")

            # 再次检查是否已被取消
            if self.is_cancelled:
                logger.info("任务在视频生成前已被取消")
                return Result(False, "", "任务已取消")

            self.progress_updated.emit(30, "开始生成视频...")

            # 生成视频（使用正确的分辨率）
            video_path = await processor.generate_video_from_image(
                image_path=image_path,
                prompt=optimized_prompt,
                duration=self.generation_config.get('duration', 5.0),
                fps=self.generation_config.get('fps', 30),  # 使用CogVideoX支持的帧率
                width=self.generation_config.get('width', 1024),
                height=self.generation_config.get('height', 1024),
                motion_intensity=self.generation_config.get('motion_intensity', 0.5),
                preferred_engine=self.generation_config.get('engine', 'cogvideox_flash'),
                progress_callback=lambda p, msg: self.progress_updated.emit(30 + int(p * 60), msg),
                project_manager=self.project_manager,
                current_project_name=self.project_name,
                max_concurrent_tasks=self.generation_config.get('max_concurrent_tasks', 3),  # 使用用户设置的并发数
                audio_hint=self.generation_config.get('audio_hint')  # 传递音效提示
            )

            self.progress_updated.emit(100, "视频生成完成!")
            return Result(True, video_path)

        except Exception as e:
            logger.error(f"异步视频生成失败: {e}")
            return Result(False, "", str(e))

    def _get_prompt_from_file(self):
        """从prompt.json文件获取提示词"""
        try:
            if not self.project_manager or not self.project_name:
                return None

            # 获取项目目录
            project_data = self.project_manager.get_project_data()
            if not project_data:
                return None

            project_dir = project_data.get('project_dir', '')
            if not project_dir:
                return None

            # 构建prompt.json文件路径
            prompt_file = os.path.join(project_dir, 'texts', 'prompt.json')
            if not os.path.exists(prompt_file):
                logger.debug(f"prompt.json文件不存在: {prompt_file}")
                return None

            # 读取prompt.json文件
            import json
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = json.load(f)

            # 获取当前镜头的shot_id
            shot_id = self.scene_data.get('shot_id', '')
            if not shot_id:
                return None

            # 查找对应的提示词
            # prompt.json的结构是 {"scenes": {"场景名": [镜头数组]}}
            scenes_data = prompt_data.get('scenes', {})

            # 提取shot_id中的数字部分
            shot_index = None
            if shot_id.startswith('text_segment_'):
                try:
                    shot_index = int(shot_id.replace('text_segment_', ''))
                except ValueError:
                    pass

            if shot_index is None:
                logger.debug(f"无法从shot_id '{shot_id}' 提取索引")
                return None

            # 遍历所有场景，找到对应索引的镜头
            current_index = 1
            for scene_name, shots in scenes_data.items():
                if isinstance(shots, list):
                    for shot in shots:
                        if current_index == shot_index:
                            content = shot.get('content', '')
                            if content:
                                logger.debug(f"从prompt.json获取镜头 {shot_id} (索引{shot_index}) 的提示词")
                                return content
                        current_index += 1

            logger.debug(f"在prompt.json中未找到镜头 {shot_id} 的提示词")
            return None

        except Exception as e:
            logger.warning(f"从prompt.json获取提示词失败: {e}")
            return None
    
    def cancel(self):
        """取消生成"""
        self.is_cancelled = True


class VideoGenerationTab(QWidget):
    """图转视频标签页 - 将图片转换为视频片段"""
    
    def __init__(self, app_controller, project_manager: StoryboardProjectManager, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.project_manager = project_manager
        self.parent_window = parent
        
        # 当前数据
        self.current_scenes = []
        self.current_voices = []
        self.generation_queue = []
        self.current_worker = None

        # 并发生成管理
        self.active_workers = {}  # {scene_id: worker}
        self.max_concurrent_videos = 3  # 默认并发数，会根据用户设置动态调整

        # 🔧 新增：统一镜头ID管理器
        self.shot_id_manager = ShotIDManager()
        
        self.init_ui()
        self.load_project_data()

    def on_concurrent_changed(self, new_value):
        """当用户改变并发数时的处理"""
        try:
            new_concurrent = int(new_value)
            old_concurrent = self.max_concurrent_videos
            self.max_concurrent_videos = new_concurrent
            logger.info(f"用户调整并发数: {old_concurrent} -> {new_concurrent}")

            # 如果当前有活跃任务，显示提示
            if self.active_workers:
                active_count = len(self.active_workers)
                if new_concurrent < active_count:
                    logger.warning(f"当前有 {active_count} 个活跃任务，新并发数 {new_concurrent} 将在下次生成时生效")
                elif new_concurrent > active_count and self.generation_queue:
                    logger.info(f"并发数增加，将启动更多任务")
                    # 如果队列中还有任务且并发数增加，启动更多任务
                    self.start_concurrent_generation()

        except ValueError:
            logger.error(f"无效的并发数: {new_value}")
        except Exception as e:
            logger.error(f"处理并发数变化时出错: {e}")

    def _optimize_prompt_for_cogvideox(self, original_prompt: str, shot_id: str = "", duration: float = 5.0) -> str:
        """使用CogVideoX优化器优化视频提示词"""
        try:
            from src.processors.cogvideox_prompt_optimizer import CogVideoXPromptOptimizer

            # 创建优化器实例
            optimizer = CogVideoXPromptOptimizer()

            # 获取镜头信息（如果有的话）
            shot_info = self._get_shot_technical_info(shot_id)

            # 使用视频专用优化方法
            optimized = optimizer.optimize_for_video(original_prompt, shot_info, duration)

            logger.info(f"视频提示词优化: {original_prompt[:50]}... -> {optimized[:50]}...")
            return optimized

        except Exception as e:
            logger.warning(f"视频提示词优化失败，使用原始提示词: {e}")
            return original_prompt

    def _get_shot_technical_info(self, shot_id: str) -> Dict:
        """获取镜头的技术信息"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return {}

            project_dir = self.project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return {}

            # 构建prompt.json文件路径
            prompt_file = os.path.join(project_dir, 'texts', 'prompt.json')
            if not os.path.exists(prompt_file):
                return {}

            # 读取prompt.json文件
            import json
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = json.load(f)

            # 查找对应镜头的技术信息
            shot_index = None
            if shot_id.startswith('text_segment_'):
                try:
                    shot_index = int(shot_id.replace('text_segment_', ''))
                except ValueError:
                    return {}

            if shot_index is None:
                return {}

            # 遍历找到对应镜头
            current_index = 1
            for scene_name, shots in prompt_data.get('scenes', {}).items():
                if isinstance(shots, list):
                    for shot in shots:
                        if current_index == shot_index:
                            # 从original_description提取技术信息
                            original_desc = shot.get('original_description', '')
                            return self._parse_technical_info(original_desc)
                        current_index += 1

            return {}

        except Exception as e:
            logger.warning(f"获取镜头技术信息失败: {e}")
            return {}

    def _parse_technical_info(self, description: str) -> Dict:
        """解析技术信息"""
        info = {}

        # 解析镜头类型
        if '全景' in description:
            info['shot_type'] = 'wide shot'
        elif '中景' in description:
            info['shot_type'] = 'medium shot'
        elif '特写' in description:
            info['shot_type'] = 'close-up shot'

        # 解析机位角度
        if '平视' in description:
            info['camera_angle'] = 'eye level'
        elif '俯视' in description:
            info['camera_angle'] = 'high angle'
        elif '仰视' in description:
            info['camera_angle'] = 'low angle'
        elif '侧面' in description:
            info['camera_angle'] = 'side angle'

        # 解析镜头运动
        if '静止' in description:
            info['camera_movement'] = 'static'
        elif '推进' in description:
            info['camera_movement'] = 'dolly in'
        elif '拉远' in description:
            info['camera_movement'] = 'dolly out'

        return info
    
    def init_ui(self):
        """初始化UI界面"""
        main_layout = QVBoxLayout()
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel("🎬 图转视频")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新数据")
        refresh_btn.clicked.connect(self.load_project_data)
        refresh_btn.setToolTip("重新加载项目中的配音和图像数据")
        title_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(title_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：场景列表
        left_panel = self.create_scene_list_panel()
        splitter.addWidget(left_panel)
        
        # 右侧：生成控制面板
        right_panel = self.create_generation_control_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setSizes([600, 400])
        main_layout.addWidget(splitter)
        
        # 底部：进度条和状态
        self.create_progress_area(main_layout)
        
        self.setLayout(main_layout)
    
    def create_scene_list_panel(self):
        """创建场景列表面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # 标题
        title_label = QLabel("📋 镜头列表")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 场景表格
        self.scene_table = QTableWidget()
        self.scene_table.setColumnCount(6)
        self.scene_table.setHorizontalHeaderLabels([
            "选择", "镜头", "配音", "图像", "视频", "状态"
        ])
        
        # 设置表格属性
        self.scene_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.scene_table.setAlternatingRowColors(True)
        
        # 设置表格可调整大小
        header = self.scene_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # 允许手动调整列宽
        header.setStretchLastSection(False)  # 最后一列不自动拉伸

        # 设置垂直表头可调整行高
        v_header = self.scene_table.verticalHeader()
        v_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # 允许手动调整行高
        v_header.setVisible(True)  # 显示行号以便调整行高
        v_header.setDefaultSectionSize(60)  # 设置默认行高为60像素，适合显示两行文本

        # 设置初始列宽
        self.scene_table.setColumnWidth(0, 50)   # 选择
        self.scene_table.setColumnWidth(1, 180)  # 镜头（增加宽度以显示旁白预览）
        self.scene_table.setColumnWidth(2, 100)  # 配音（增加宽度显示时长）
        self.scene_table.setColumnWidth(3, 120)  # 图像
        self.scene_table.setColumnWidth(4, 120)  # 视频
        self.scene_table.setColumnWidth(5, 150)  # 状态
        
        layout.addWidget(self.scene_table)
        
        # 批量操作按钮
        batch_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_scenes)
        batch_layout.addWidget(self.select_all_btn)
        
        self.select_none_btn = QPushButton("取消全选")
        self.select_none_btn.clicked.connect(self.select_none_scenes)
        batch_layout.addWidget(self.select_none_btn)
        
        batch_layout.addStretch()
        
        self.batch_generate_btn = QPushButton("🎬 批量生成")
        self.batch_generate_btn.clicked.connect(self.start_batch_generation)
        self.batch_generate_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        batch_layout.addWidget(self.batch_generate_btn)
        
        layout.addLayout(batch_layout)
        
        return panel

    def create_generation_control_panel(self):
        """创建生成控制面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)

        # 标题
        title_label = QLabel("⚙️ 生成设置")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # CogVideoX-Flash 设置组
        cogvideox_group = QGroupBox("CogVideoX-Flash 设置")
        cogvideox_form = QFormLayout()

        # 视频时长 - CogVideoX-Flash支持的时长
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(["5", "10"])  # CogVideoX-Flash只支持5秒和10秒
        self.duration_combo.setCurrentText("5")
        self.duration_combo.setToolTip("视频时长（CogVideoX-Flash支持5秒、10秒）")
        cogvideox_form.addRow("视频时长:", self.duration_combo)

        # 分辨率说明 - 自动根据图像尺寸确定
        resolution_label = QLabel("分辨率: 自动根据图像尺寸确定")
        resolution_label.setStyleSheet("color: #666; font-style: italic;")
        cogvideox_form.addRow("", resolution_label)

        # 帧率 - CogVideoX-Flash只支持30和60fps
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["30", "60"])
        self.fps_combo.setCurrentText("30")
        cogvideox_form.addRow("帧率:", self.fps_combo)

        # 并发任务数 - CogVideoX-Flash支持多个并发任务
        self.concurrent_tasks_combo = QComboBox()
        self.concurrent_tasks_combo.addItems(["1", "2", "3", "4", "5"])
        self.concurrent_tasks_combo.setCurrentText("3")
        self.concurrent_tasks_combo.setToolTip("同时进行的视频生成任务数量。数量越多速度越快，但可能增加服务器负载")
        # 连接信号，当用户改变并发数时实时更新
        self.concurrent_tasks_combo.currentTextChanged.connect(self.on_concurrent_changed)
        cogvideox_form.addRow("并发任务数:", self.concurrent_tasks_combo)

        # 运动强度
        motion_layout = QHBoxLayout()
        self.motion_slider = QSlider(Qt.Orientation.Horizontal)
        self.motion_slider.setRange(0, 100)
        self.motion_slider.setValue(50)
        self.motion_label = QLabel("50%")
        self.motion_slider.valueChanged.connect(
            lambda v: self.motion_label.setText(f"{v}%")
        )
        motion_layout.addWidget(self.motion_slider)
        motion_layout.addWidget(self.motion_label)
        cogvideox_form.addRow("运动强度:", motion_layout)

        cogvideox_group.setLayout(cogvideox_form)
        layout.addWidget(cogvideox_group)

        # 输出设置组
        output_group = QGroupBox("输出设置")
        output_form = QFormLayout()

        # 输出目录显示
        self.output_dir_label = QLabel("项目/videos/cogvideox/")
        self.output_dir_label.setStyleSheet("color: #666; font-style: italic;")
        output_form.addRow("输出目录:", self.output_dir_label)

        # 自动播放
        self.auto_play_check = QCheckBox("生成完成后自动播放")
        self.auto_play_check.setChecked(True)
        output_form.addRow(self.auto_play_check)

        output_group.setLayout(output_form)
        layout.addWidget(output_group)

        # 预览区域
        preview_group = QGroupBox("当前选择预览")
        preview_layout = QVBoxLayout()

        # 图像预览
        self.image_preview = QLabel("选择场景查看图像预览")
        self.image_preview.setMinimumHeight(150)
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setStyleSheet("border: 1px solid #ccc; background-color: #f9f9f9;")
        preview_layout.addWidget(self.image_preview)

        # 描述预览
        self.description_preview = QTextEdit()
        self.description_preview.setMaximumHeight(80)
        self.description_preview.setPlaceholderText("选择场景查看描述")
        self.description_preview.setReadOnly(True)
        preview_layout.addWidget(self.description_preview)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # 单个生成按钮
        self.single_generate_btn = QPushButton("🎥 生成当前选择")
        self.single_generate_btn.clicked.connect(self.start_single_generation)
        self.single_generate_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
        layout.addWidget(self.single_generate_btn)

        layout.addStretch()
        return panel

    def create_progress_area(self, parent_layout):
        """创建进度区域"""
        progress_frame = QFrame()
        progress_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        progress_frame.setMaximumHeight(80)  # 限制进度区域高度
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(5, 5, 5, 5)  # 减少边距
        progress_layout.setSpacing(3)  # 减少间距

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)  # 限制进度条高度
        progress_layout.addWidget(self.progress_bar)

        # 状态标签和控制按钮在同一行
        status_control_layout = QHBoxLayout()

        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        status_control_layout.addWidget(self.status_label)

        status_control_layout.addStretch()

        # 控制按钮
        self.cancel_btn = QPushButton("❌ 取消生成")
        self.cancel_btn.clicked.connect(self.cancel_generation)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setMaximumHeight(25)
        status_control_layout.addWidget(self.cancel_btn)

        self.open_output_btn = QPushButton("📁 打开输出目录")
        self.open_output_btn.clicked.connect(self.open_output_directory)
        self.open_output_btn.setMaximumHeight(25)
        status_control_layout.addWidget(self.open_output_btn)

        progress_layout.addLayout(status_control_layout)
        parent_layout.addWidget(progress_frame)

    def load_project_data(self):
        """加载项目数据"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                self.status_label.setText("未加载项目")
                return

            project_data = self.project_manager.get_project_data()
            if not project_data:
                self.status_label.setText("项目数据为空")
                return

            # 🔧 新增：初始化ID管理器
            self.shot_id_manager.initialize_from_project_data(project_data)
            logger.info("视频生成界面：ID管理器初始化完成")

            # 加载场景数据
            self.load_scenes_data(project_data)

            # 更新状态
            scene_count = len(self.current_scenes)
            self.status_label.setText(f"已加载 {scene_count} 个镜头")

        except Exception as e:
            logger.error(f"加载项目数据失败: {e}")
            self.status_label.setText(f"加载失败: {e}")

    def load_scenes_data(self, project_data):
        """加载场景数据"""
        try:
            self.current_scenes = []
            logger.info(f"开始加载场景数据，项目数据键: {list(project_data.keys())}")

            # 尝试多种数据源加载场景数据
            scenes_loaded = False

            # 方法1：从新的项目数据结构中提取
            if not scenes_loaded:
                scenes_loaded = self._load_from_new_structure(project_data)

            # 方法2：从旧的项目数据结构中提取
            if not scenes_loaded:
                scenes_loaded = self._load_from_legacy_structure(project_data)

            # 方法3：从分镜图像生成数据中提取
            if not scenes_loaded:
                scenes_loaded = self._load_from_storyboard_data(project_data)

            if not scenes_loaded:
                logger.warning("未能从任何数据源加载镜头数据")
                self.status_label.setText("未找到镜头数据")
                return

            # 更新表格显示
            self.update_scene_table()
            logger.info(f"成功加载 {len(self.current_scenes)} 个场景")

        except Exception as e:
            logger.error(f"加载场景数据失败: {e}")
            raise

    def _load_from_new_structure(self, project_data):
        """从新的项目数据结构加载"""
        try:
            # 方法1：从voice_generation.voice_segments加载（优先）
            voice_generation = project_data.get('voice_generation', {})
            voice_segments = voice_generation.get('voice_segments', [])
            if voice_segments:
                logger.info(f"从voice_generation.voice_segments加载，找到 {len(voice_segments)} 个镜头")
                return self._load_from_voice_segments(voice_segments, project_data)

            # 方法2：从shots_data加载
            shots_data = project_data.get('shots_data', [])
            if shots_data:
                logger.info(f"从shots_data加载，找到 {len(shots_data)} 个镜头")
                return self._load_from_shots_data(shots_data, project_data)

            # 方法3：从storyboard.shots加载
            storyboard = project_data.get('storyboard', {})
            shots = storyboard.get('shots', [])
            if shots:
                logger.info(f"从storyboard.shots加载，找到 {len(shots)} 个镜头")
                return self._load_from_storyboard_shots(shots, project_data)

            # 方法4：从五阶段数据加载（最后选择）
            five_stage_data = project_data.get('five_stage_storyboard', {})
            if five_stage_data:
                logger.info("尝试从五阶段数据加载")
                return self._load_from_five_stage_data(five_stage_data, project_data)

            return False

        except Exception as e:
            logger.error(f"从新结构加载失败: {e}")
            return False

    def _load_from_voice_segments(self, voice_segments, project_data):
        """从voice_generation.voice_segments加载"""
        try:
            self.current_scenes = []

            # 获取enhanced_descriptions和image_generation数据
            enhanced_descriptions = project_data.get('enhanced_descriptions', {})
            image_generation = project_data.get('image_generation', {})

            for segment in voice_segments:
                scene_data = self._create_scene_data_from_voice_segment(segment, enhanced_descriptions, image_generation, project_data)
                if scene_data:
                    self.current_scenes.append(scene_data)

            logger.info(f"从voice_segments加载了 {len(self.current_scenes)} 个镜头")
            return len(self.current_scenes) > 0

        except Exception as e:
            logger.error(f"从voice_segments加载失败: {e}")
            return False

    def _create_scene_data_from_voice_segment(self, segment, enhanced_descriptions, image_generation, project_data):
        """从voice_segment创建场景数据"""
        try:
            shot_id = segment.get('shot_id', '')
            scene_id = segment.get('scene_id', '')

            # 获取原文内容 - 优先从多个字段中获取
            original_text = (
                segment.get('original_text', '') or
                segment.get('text', '') or
                segment.get('content', '') or
                segment.get('narration', '') or
                ''
            )

            # 获取分镜描述
            storyboard_description = (
                segment.get('storyboard_description', '') or
                segment.get('description', '') or
                segment.get('enhanced_description', '') or
                ''
            )

            # 创建基础场景数据
            scene_data = {
                'shot_id': shot_id,
                'scene_id': scene_id,
                'shot_number': shot_id,
                'shot_title': shot_id,  # 添加shot_title字段
                'scene_title': scene_id,  # 添加scene_title字段
                'narration': original_text,  # 使用获取到的原文
                'original_text': original_text,  # 保留原文字段
                'description': storyboard_description,
                'enhanced_description': '',
                'voice_path': segment.get('audio_path', ''),
                'voice_duration': 0.0,
                'image_path': '',
                'video_path': '',
                'status': '未生成'
            }

            # 获取配音时长 - 优先从segment中获取，然后从文件获取
            voice_duration = segment.get('duration', 0.0) or segment.get('voice_duration', 0.0)
            if voice_duration > 0:
                scene_data['voice_duration'] = voice_duration
                logger.info(f"从segment获取音频时长: {shot_id} -> {voice_duration:.1f}s")
            elif scene_data['voice_path'] and os.path.exists(scene_data['voice_path']):
                voice_duration = self._get_audio_duration(scene_data['voice_path'])
                scene_data['voice_duration'] = voice_duration
                logger.info(f"从文件获取音频时长: {scene_data['voice_path']} -> {voice_duration:.1f}s")
            else:
                logger.warning(f"无法获取音频时长: {shot_id}, 音频路径: {scene_data['voice_path']}")

            # 从enhanced_descriptions获取图像信息
            shot_key = f"### {shot_id}"
            if shot_key in enhanced_descriptions:
                enhanced_data = enhanced_descriptions[shot_key]
                scene_data['enhanced_description'] = enhanced_data.get('enhanced_prompt', '')

            # 从多个数据源获取图像路径
            image_path = ''
            image_status = '未生成'

            # 方法1：从shot_image_mappings获取（主要数据源）
            shot_image_mappings = project_data.get('shot_image_mappings', {})
            if shot_image_mappings:
                # 🔧 修复：使用统一ID管理器进行转换
                possible_keys = [shot_id]  # 直接使用shot_id

                # 使用ID管理器转换为统一格式
                if hasattr(self, 'shot_id_manager') and self.shot_id_manager.shot_mappings:
                    unified_key = self.shot_id_manager.convert_id(shot_id, "unified")
                    if unified_key:
                        possible_keys.append(unified_key)
                        logger.debug(f"ID管理器转换: {shot_id} -> {unified_key}")

                # 保留原有的转换逻辑作为备用
                if shot_id.startswith('text_segment_'):
                    shot_number = shot_id.split('_')[-1]
                    shot_num = str(int(shot_number))
                    possible_keys.extend([
                        f"scene_1_{shot_id}",  # scene_1_text_segment_001
                        f"scene_1_shot_{shot_num}",  # scene_1_shot_1
                        f"scene_1_shot_{shot_number}",  # scene_1_shot_001
                        f"shot_{shot_num}",  # shot_1
                        f"shot_{shot_number}",  # shot_001
                    ])

                for key in possible_keys:
                    if key in shot_image_mappings:
                        img_data = shot_image_mappings[key]
                        # 🔧 修复：优先获取主图路径，确保视频生成使用用户选择的主图
                        image_path = img_data.get('main_image_path', '') or img_data.get('image_path', '')
                        image_status = img_data.get('status', '未生成')
                        logger.debug(f"从shot_image_mappings找到图像: {key} -> {image_path} (主图优先)")
                        break

            # 方法2：从image_generation获取
            if not image_path:
                if shot_id in image_generation:
                    image_data = image_generation[shot_id]
                    if isinstance(image_data, dict):
                        # 🔧 修复：优先获取主图路径
                        image_path = image_data.get('main_image_path', '') or image_data.get('image_path', '')
                        image_status = image_data.get('status', '未生成')
                    elif isinstance(image_data, str):
                        image_path = image_data
                        image_status = '已生成' if os.path.exists(image_path) else '未生成'

            # 方法3：从images列表中查找
            if not image_path:
                images_list = image_generation.get('images', [])
                for img in images_list:
                    if isinstance(img, dict) and img.get('shot_id') == shot_id:
                        # 🔧 修复：优先获取主图路径
                        image_path = img.get('main_image_path', '') or img.get('image_path', '')
                        image_status = img.get('status', '未生成')
                        break

            # 验证图像文件是否存在
            if image_path and os.path.exists(image_path):
                image_status = '已生成'
            elif image_path:
                logger.warning(f"图像文件不存在: {image_path}")
                image_path = ''
                image_status = '未生成'

            scene_data['image_path'] = image_path

            # 🔧 新增：获取视频路径信息
            video_path = ''
            video_status = '未生成'

            # 方法1：从shot_mappings获取（新的保存方式）
            shot_mappings = project_data.get('shot_mappings', {})
            if shot_id in shot_mappings:
                mapping_data = shot_mappings[shot_id]
                video_path = mapping_data.get('video_path', '')
                video_status = mapping_data.get('video_status', '未生成')
                logger.debug(f"从shot_mappings找到视频: {shot_id} -> {video_path}")

            # 方法2：从video_generation.videos获取
            if not video_path:
                video_generation = project_data.get('video_generation', {})
                videos = video_generation.get('videos', [])
                for video in videos:
                    if isinstance(video, dict) and video.get('shot_id') == shot_id:
                        video_path = video.get('video_path', '')
                        video_status = video.get('status', '未生成')
                        logger.debug(f"从video_generation找到视频: {shot_id} -> {video_path}")
                        break

            # 验证视频文件是否存在
            if video_path and os.path.exists(video_path):
                video_status = '已生成'
                scene_data['status'] = '已生成'  # 如果有视频，状态设为已生成
            elif video_path:
                logger.warning(f"视频文件不存在: {video_path}")
                video_path = ''
                video_status = '未生成'

            scene_data['video_path'] = video_path

            # 更新状态：如果有视频则为已生成，否则根据图像状态决定
            if video_status == '已生成':
                scene_data['status'] = '已生成'
            else:
                scene_data['status'] = image_status

            logger.debug(f"镜头 {shot_id} 信息: 图像={image_path}, 视频={video_path}, 状态={scene_data['status']}")

            return scene_data

        except Exception as e:
            logger.error(f"创建场景数据失败: {e}")
            return None

    def _load_from_shots_data(self, shots_data, project_data):
        """从shots_data加载"""
        try:
            # 获取配音数据
            voice_generation = project_data.get('voice_generation', {})
            voice_segments = voice_generation.get('segments', [])

            # 获取图像数据
            image_generation = project_data.get('image_generation', {})
            images = image_generation.get('images', [])

            # 获取视频数据
            video_generation = project_data.get('video_generation', {})
            videos = video_generation.get('videos', [])

            # 处理每个镜头
            for i, shot in enumerate(shots_data):
                shot_id = shot.get('shot_id', f'shot_{i+1}')
                scene_id = shot.get('scene_id', f'scene_{i//5+1}')  # 假设每5个镜头一个场景

                scene_data = self._create_scene_data(shot_id, scene_id, shot, voice_segments, images, videos)
                self.current_scenes.append(scene_data)

            return len(self.current_scenes) > 0

        except Exception as e:
            logger.error(f"从shots_data加载失败: {e}")
            return False

    def _load_from_storyboard_shots(self, shots, project_data):
        """从storyboard.shots加载"""
        try:
            # 获取配音数据
            voice_generation = project_data.get('voice_generation', {})
            voice_segments = voice_generation.get('segments', [])

            # 获取图像数据
            image_generation = project_data.get('image_generation', {})
            images = image_generation.get('images', [])

            # 获取视频数据
            video_generation = project_data.get('video_generation', {})
            videos = video_generation.get('videos', [])

            # 处理每个镜头
            for shot in shots:
                shot_id = shot.get('shot_id', '')
                scene_id = shot.get('scene_id', '')

                scene_data = self._create_scene_data(shot_id, scene_id, shot, voice_segments, images, videos)
                self.current_scenes.append(scene_data)

            return len(self.current_scenes) > 0

        except Exception as e:
            logger.error(f"从storyboard.shots加载失败: {e}")
            return False

    def _load_from_five_stage_data(self, five_stage_data, project_data):
        """从五阶段数据加载"""
        try:
            stage_data = five_stage_data.get('stage_data', {})

            # 从第5阶段获取最终分镜数据
            stage_5 = stage_data.get('5', {})
            final_storyboard = stage_5.get('final_storyboard', [])

            if not final_storyboard:
                # 尝试从第4阶段获取
                stage_4 = stage_data.get('4', {})
                storyboard_results = stage_4.get('storyboard_results', [])
                if storyboard_results:
                    # 展开所有场景的镜头
                    final_storyboard = []
                    for scene_result in storyboard_results:
                        voice_segments = scene_result.get('voice_segments', [])
                        final_storyboard.extend(voice_segments)

            if not final_storyboard:
                return False

            logger.info(f"从五阶段数据加载，找到 {len(final_storyboard)} 个镜头")

            # 获取配音数据
            voice_generation = project_data.get('voice_generation', {})
            voice_segments = voice_generation.get('segments', [])

            # 获取图像数据
            image_generation = project_data.get('image_generation', {})
            images = image_generation.get('images', [])

            # 获取视频数据
            video_generation = project_data.get('video_generation', {})
            videos = video_generation.get('videos', [])

            # 处理每个镜头
            for i, shot in enumerate(final_storyboard):
                shot_id = shot.get('shot_id', f'shot_{i+1}')
                scene_id = shot.get('scene_id', f'scene_{i//5+1}')

                scene_data = self._create_scene_data(shot_id, scene_id, shot, voice_segments, images, videos)
                self.current_scenes.append(scene_data)

            return len(self.current_scenes) > 0

        except Exception as e:
            logger.error(f"从五阶段数据加载失败: {e}")
            return False

    def _load_from_legacy_structure(self, project_data):
        """从旧的项目数据结构加载"""
        try:
            # 方法1：从shot_image_mappings加载
            shot_image_mappings = project_data.get('shot_image_mappings', {})
            if shot_image_mappings:
                logger.info(f"从shot_image_mappings加载，找到 {len(shot_image_mappings)} 个镜头映射")
                return self._load_from_shot_mappings(shot_image_mappings, project_data)

            # 方法2：从旧的voices/images/videos结构加载
            voices = project_data.get('voices', {})
            images = project_data.get('images', {})
            videos = project_data.get('videos', {})
            scenes = project_data.get('scenes', [])

            if not scenes and not voices and not images:
                return False

            # 如果有voices/images数据但没有scenes，尝试从键名推断
            if (voices or images) and not scenes:
                return self._load_from_voice_image_keys(voices, images, videos, project_data)

            # 标准的scenes结构
            for scene_idx, scene in enumerate(scenes):
                shots = scene.get('shots', [])
                for shot_idx, shot in enumerate(shots):
                    shot_key = f"scene_{scene_idx}_shot_{shot_idx}"

                    scene_data = {
                        'scene_id': f"scene_{scene_idx}",
                        'shot_id': f"shot_{shot_idx}",
                        'scene_title': scene.get('title', f'场景{scene_idx + 1}'),
                        'shot_title': shot.get('title', f'镜头{shot_idx + 1}'),
                        'description': shot.get('description', ''),
                        'enhanced_description': shot.get('enhanced_description', ''),
                        'original_text': shot.get('original_text', ''),
                        'voice_path': '',
                        'voice_duration': 0.0,
                        'image_path': '',
                        'video_path': '',
                        'status': '未生成'
                    }

                    # 查找配音文件
                    if shot_key in voices:
                        voice_info = voices[shot_key]
                        if isinstance(voice_info, dict):
                            scene_data['voice_path'] = voice_info.get('file_path', '')
                            scene_data['voice_duration'] = voice_info.get('duration', 0.0)
                        else:
                            scene_data['voice_path'] = str(voice_info)

                    # 查找图像文件
                    if shot_key in images:
                        image_info = images[shot_key]
                        if isinstance(image_info, dict):
                            scene_data['image_path'] = image_info.get('file_path', '')
                        else:
                            scene_data['image_path'] = str(image_info)

                    # 查找视频文件
                    if shot_key in videos:
                        video_info = videos[shot_key]
                        if isinstance(video_info, dict):
                            scene_data['video_path'] = video_info.get('file_path', '')
                            if scene_data['video_path'] and os.path.exists(scene_data['video_path']):
                                scene_data['status'] = '已生成'

                    self.current_scenes.append(scene_data)

            return len(self.current_scenes) > 0

        except Exception as e:
            logger.error(f"从旧结构加载失败: {e}")
            return False

    def _load_from_shot_mappings(self, shot_mappings, project_data):
        """从shot_image_mappings加载"""
        try:
            # 获取配音数据
            voice_generation = project_data.get('voice_generation', {})
            voice_segments = voice_generation.get('segments', [])

            # 获取视频数据
            video_generation = project_data.get('video_generation', {})
            videos = video_generation.get('videos', [])

            for shot_key, mapping_data in shot_mappings.items():
                # 解析shot_key (如: scene_1_shot_1)
                parts = shot_key.split('_')
                if len(parts) >= 4:
                    scene_id = f"{parts[0]}_{parts[1]}"
                    shot_id = f"{parts[2]}_{parts[3]}"
                else:
                    scene_id = f"scene_{len(self.current_scenes)//5+1}"
                    shot_id = f"shot_{len(self.current_scenes)+1}"

                scene_data = {
                    'scene_id': scene_id,
                    'shot_id': shot_id,
                    'scene_title': scene_id.replace('_', ' ').title(),
                    'shot_title': shot_id.replace('_', ' ').title(),
                    'description': mapping_data.get('enhanced_description', ''),
                    'enhanced_description': mapping_data.get('enhanced_description', ''),
                    'original_text': mapping_data.get('original_text', ''),
                    'voice_path': '',
                    'voice_duration': 0.0,
                    'image_path': mapping_data.get('main_image_path', ''),
                    'video_path': '',
                    'status': mapping_data.get('status', '未生成')
                }

                # 查找配音文件
                for voice_segment in voice_segments:
                    if (voice_segment.get('shot_id') == shot_id or
                        voice_segment.get('shot_id') == shot_key):
                        audio_path = voice_segment.get('audio_path', '')
                        if audio_path and os.path.exists(audio_path):
                            scene_data['voice_path'] = audio_path
                            scene_data['voice_duration'] = voice_segment.get('duration', 0.0)
                        break

                # 查找视频文件
                for video in videos:
                    if (video.get('shot_id') == shot_id or
                        video.get('shot_id') == shot_key):
                        video_path = video.get('video_path', '')
                        if video_path and os.path.exists(video_path):
                            scene_data['video_path'] = video_path
                            scene_data['status'] = '已生成'
                        break

                self.current_scenes.append(scene_data)

            return len(self.current_scenes) > 0

        except Exception as e:
            logger.error(f"从shot_mappings加载失败: {e}")
            return False

    def _load_from_voice_image_keys(self, voices, images, videos, project_data):
        """从voice/image键名推断镜头数据"""
        try:
            # 收集所有的镜头键
            all_keys = set()
            all_keys.update(voices.keys())
            all_keys.update(images.keys())
            all_keys.update(videos.keys())

            if not all_keys:
                return False

            for shot_key in sorted(all_keys):
                # 解析shot_key
                parts = shot_key.split('_')
                if len(parts) >= 4:
                    scene_id = f"{parts[0]}_{parts[1]}"
                    shot_id = f"{parts[2]}_{parts[3]}"
                else:
                    scene_id = f"scene_{len(self.current_scenes)//5+1}"
                    shot_id = f"shot_{len(self.current_scenes)+1}"

                scene_data = {
                    'scene_id': scene_id,
                    'shot_id': shot_id,
                    'scene_title': scene_id.replace('_', ' ').title(),
                    'shot_title': shot_id.replace('_', ' ').title(),
                    'description': '',
                    'enhanced_description': '',
                    'original_text': '',
                    'voice_path': '',
                    'voice_duration': 0.0,
                    'image_path': '',
                    'video_path': '',
                    'status': '未生成'
                }

                # 处理配音数据
                if shot_key in voices:
                    voice_info = voices[shot_key]
                    if isinstance(voice_info, dict):
                        scene_data['voice_path'] = voice_info.get('file_path', '')
                        scene_data['voice_duration'] = voice_info.get('duration', 0.0)
                    else:
                        scene_data['voice_path'] = str(voice_info)

                # 处理图像数据
                if shot_key in images:
                    image_info = images[shot_key]
                    if isinstance(image_info, dict):
                        scene_data['image_path'] = image_info.get('file_path', '')
                    else:
                        scene_data['image_path'] = str(image_info)

                # 处理视频数据
                if shot_key in videos:
                    video_info = videos[shot_key]
                    if isinstance(video_info, dict):
                        scene_data['video_path'] = video_info.get('file_path', '')
                        if scene_data['video_path'] and os.path.exists(scene_data['video_path']):
                            scene_data['status'] = '已生成'

                self.current_scenes.append(scene_data)

            return len(self.current_scenes) > 0

        except Exception as e:
            logger.error(f"从voice/image键加载失败: {e}")
            return False

    def _load_from_storyboard_data(self, project_data):
        """从分镜数据加载"""
        try:
            # 尝试从分镜图像生成的数据中加载
            if hasattr(self.project_manager, 'get_storyboard_data'):
                storyboard_data = self.project_manager.get_storyboard_data()
                if storyboard_data:
                    for i, shot_data in enumerate(storyboard_data):
                        scene_data = {
                            'scene_id': f"scene_{i // 5 + 1}",  # 假设每5个镜头一个场景
                            'shot_id': f"shot_{i + 1}",
                            'scene_title': f"场景{i // 5 + 1}",
                            'shot_title': f"镜头{i + 1}",
                            'description': shot_data.get('description', ''),
                            'enhanced_description': shot_data.get('enhanced_description', ''),
                            'original_text': shot_data.get('original_text', ''),
                            'voice_path': shot_data.get('voice_path', ''),
                            'voice_duration': shot_data.get('voice_duration', 0.0),
                            'image_path': shot_data.get('image_path', ''),
                            'video_path': '',
                            'status': '未生成'
                        }
                        self.current_scenes.append(scene_data)

                    return len(self.current_scenes) > 0

            return False

        except Exception as e:
            logger.error(f"从分镜数据加载失败: {e}")
            return False

    def _create_scene_data(self, shot_id, scene_id, shot, voice_segments, images, videos):
        """创建场景数据"""
        # 处理不同的数据格式
        if isinstance(shot, dict):
            # 从shots_data或storyboard数据
            description = shot.get('enhanced_description') or shot.get('scene_description') or shot.get('description', '')
            original_text = shot.get('shot_original_text') or shot.get('original_text', '')
            shot_title = shot.get('shot_type') or shot.get('sequence') or '镜头'
        else:
            # 其他格式
            description = ''
            original_text = ''
            shot_title = '镜头'

        scene_data = {
            'scene_id': scene_id,
            'shot_id': shot_id,
            'scene_title': scene_id.replace('_', ' ').title(),
            'shot_title': shot_title,
            'description': description,
            'enhanced_description': description,
            'original_text': original_text,
            'voice_path': '',
            'voice_duration': 0.0,
            'image_path': '',
            'video_path': '',
            'status': '未生成'
        }

        # 查找对应的配音文件
        for voice_segment in voice_segments:
            # 支持多种匹配方式
            voice_shot_id = voice_segment.get('shot_id', '')
            if (voice_shot_id == shot_id or
                voice_shot_id == f"shot_{shot_id}" or
                voice_shot_id.endswith(f"_{shot_id}")):

                audio_path = voice_segment.get('audio_path', '')
                if audio_path and os.path.exists(audio_path):
                    scene_data['voice_path'] = audio_path
                    # 尝试从数据中获取时长，如果没有则检测音频文件
                    duration = voice_segment.get('duration', 0.0)
                    if duration <= 0:
                        duration = self._get_audio_duration(audio_path)
                    scene_data['voice_duration'] = duration
                break

        # 查找对应的图像文件 - 支持多种数据格式
        image_found = False

        # 方法1：从images数组查找
        for image in images:
            image_shot_id = image.get('shot_id', '')
            if (image_shot_id == shot_id or
                image_shot_id == f"shot_{shot_id}" or
                image_shot_id.endswith(f"_{shot_id}")):

                if image.get('is_main', False):
                    image_path = image.get('image_path', '')
                    if image_path and os.path.exists(image_path):
                        scene_data['image_path'] = image_path
                        image_found = True
                        break

        # 方法2：如果没找到，尝试从shot数据本身获取
        if not image_found and isinstance(shot, dict):
            # 🔧 修复：优先获取主图路径
            image_path = shot.get('main_image_path', '') or shot.get('image_path', '')
            if image_path and os.path.exists(image_path):
                scene_data['image_path'] = image_path
                image_found = True

        # 查找对应的视频文件
        for video in videos:
            video_shot_id = video.get('shot_id', '')
            if (video_shot_id == shot_id or
                video_shot_id == f"shot_{shot_id}" or
                video_shot_id.endswith(f"_{shot_id}")):

                video_path = video.get('video_path', '')
                if video_path and os.path.exists(video_path):
                    scene_data['video_path'] = video_path
                    # 确保状态是字符串类型
                    status = video.get('status', '已生成')
                    scene_data['status'] = str(status) if status is not None else '已生成'
                break

        return scene_data

    def _get_audio_duration(self, audio_path):
        """获取音频文件时长"""
        try:
            # 检查文件是否存在
            if not audio_path or not os.path.exists(audio_path):
                return 0.0

            # 方法1：使用mutagen（最稳定，优先使用）
            try:
                from mutagen._file import File
                audio_file = File(audio_path)
                if audio_file is not None and hasattr(audio_file, 'info') and audio_file.info is not None:
                    if hasattr(audio_file.info, 'length') and audio_file.info.length is not None:
                        duration = float(audio_file.info.length)
                        logger.debug(f"mutagen获取音频时长成功: {audio_path} -> {duration:.1f}s")
                        return duration
            except ImportError:
                logger.warning("mutagen库未安装")
            except Exception as e:
                logger.warning(f"mutagen获取音频时长失败: {e}")

            # 方法2：使用pydub
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(audio_path)
                duration = len(audio) / 1000.0  # 转换为秒
                logger.debug(f"pydub获取音频时长成功: {audio_path} -> {duration:.1f}s")
                return float(duration)
            except Exception as e:
                logger.warning(f"pydub获取音频时长失败: {e}")

            # 方法3：使用wave模块（仅支持wav文件）
            try:
                import wave
                if audio_path.lower().endswith('.wav'):
                    with wave.open(audio_path, 'r') as wav_file:
                        frames = wav_file.getnframes()
                        rate = wav_file.getframerate()
                        duration = frames / float(rate)
                        logger.debug(f"wave获取音频时长成功: {audio_path} -> {duration:.1f}s")
                        return duration
            except Exception as e:
                logger.warning(f"wave获取音频时长失败: {e}")

            # 如果所有方法都失败，返回默认值
            logger.warning(f"无法获取音频时长，使用默认值5秒: {audio_path}")
            return 5.0  # 默认5秒

        except Exception as e:
            logger.error(f"获取音频时长失败: {e}")
            return 5.0

    def _check_voice_duration_match(self, scene_data):
        """检查配音时长是否需要多个图像"""
        voice_duration = scene_data.get('voice_duration', 0.0)
        if voice_duration <= 0:
            return 1, []  # 没有配音，使用1个图像

        # 每个视频片段的最大时长（秒）
        max_segment_duration = 10.0  # CogVideoX-Flash最大支持10秒

        # 计算需要的图像数量
        required_images = max(1, int(voice_duration / max_segment_duration) + (1 if voice_duration % max_segment_duration > 0 else 0))

        # 计算每个片段的时长
        segment_durations = []
        remaining_duration = voice_duration

        for i in range(required_images):
            if remaining_duration > max_segment_duration:
                segment_durations.append(max_segment_duration)
                remaining_duration -= max_segment_duration
            else:
                segment_durations.append(remaining_duration)
                break

        return required_images, segment_durations

    def _get_scene_images(self, scene_data):
        """获取场景的所有图像"""
        shot_id = scene_data.get('shot_id', '')
        if not shot_id:
            return []

        # 从项目数据中获取该镜头的所有图像
        project_data = self.project_manager.get_project_data() if self.project_manager else {}
        image_generation = project_data.get('image_generation', {})
        images = image_generation.get('images', [])

        scene_images = []
        for image in images:
            if image.get('shot_id') == shot_id:
                # 🔧 修复：优先获取主图路径
                image_path = image.get('main_image_path', '') or image.get('image_path', '')
                if image_path and os.path.exists(image_path):
                    scene_images.append({
                        'path': image_path,
                        'is_main': image.get('is_main', False)
                    })

        # 按主图像优先排序
        scene_images.sort(key=lambda x: not x['is_main'])
        return scene_images

    def update_scene_table(self):
        """更新场景表格"""
        try:
            self.scene_table.setRowCount(len(self.current_scenes))

            for row, scene_data in enumerate(self.current_scenes):
                # 选择复选框
                checkbox = QCheckBox()
                checkbox.stateChanged.connect(self.on_scene_selection_changed)
                self.scene_table.setCellWidget(row, 0, checkbox)

                # 镜头信息 - 显示镜头ID和旁白内容预览
                shot_id = scene_data.get('shot_id', f'镜头{row+1}')
                narration = scene_data.get('narration', scene_data.get('original_text', ''))

                # 构建显示文本：镜头ID + 旁白预览
                if narration:
                    # 截取旁白前30个字符作为预览
                    narration_preview = narration[:30] + "..." if len(narration) > 30 else narration
                    shot_text = f"{shot_id}\n{narration_preview}"
                else:
                    shot_text = shot_id

                shot_item = QTableWidgetItem(shot_text)
                shot_item.setToolTip(f"镜头ID: {shot_id}\n完整旁白: {narration}")  # 悬停显示完整内容
                self.scene_table.setItem(row, 1, shot_item)

                # 配音状态和时长
                voice_widget = QWidget()
                voice_layout = QHBoxLayout(voice_widget)
                voice_layout.setContentsMargins(2, 2, 2, 2)

                voice_status = "✅" if scene_data['voice_path'] and os.path.exists(scene_data['voice_path']) else "❌"
                voice_status_label = QLabel(voice_status)
                voice_layout.addWidget(voice_status_label)

                # 显示配音时长
                voice_duration = scene_data.get('voice_duration', 0.0)
                if voice_duration > 0:
                    duration_label = QLabel(f"{voice_duration:.1f}s")
                    duration_label.setStyleSheet("color: #666; font-size: 10px;")
                    voice_layout.addWidget(duration_label)

                self.scene_table.setCellWidget(row, 2, voice_widget)

                # 图像预览（去掉绿勾，放大缩略图）
                image_widget = QWidget()
                image_layout = QHBoxLayout(image_widget)
                image_layout.setContentsMargins(2, 2, 2, 2)

                # 如果有图像，添加放大的预览
                if scene_data['image_path'] and os.path.exists(scene_data['image_path']):
                    image_preview = QLabel()
                    pixmap = QPixmap(scene_data['image_path'])
                    if not pixmap.isNull():
                        # 放大缩略图尺寸（从40x30改为80x60）
                        scaled_pixmap = pixmap.scaled(80, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        image_preview.setPixmap(scaled_pixmap)
                        image_preview.setToolTip(f"图像: {os.path.basename(scene_data['image_path'])}")
                        image_layout.addWidget(image_preview)
                else:
                    # 没有图像时显示占位符
                    no_image_label = QLabel("暂无图像")
                    no_image_label.setStyleSheet("color: #666; font-size: 12px;")
                    no_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    image_layout.addWidget(no_image_label)

                self.scene_table.setCellWidget(row, 3, image_widget)

                # 视频预览和播放（去掉状态图标，添加缩略图）
                video_widget = QWidget()
                video_layout = QHBoxLayout(video_widget)
                video_layout.setContentsMargins(2, 2, 2, 2)

                # 如果有视频，添加缩略图和播放按钮
                if scene_data['video_path'] and os.path.exists(scene_data['video_path']):
                    logger.debug(f"尝试为视频生成缩略图: {scene_data['video_path']}")
                    # 生成视频缩略图
                    video_thumbnail = self._generate_video_thumbnail(scene_data['video_path'])
                    if video_thumbnail:
                        logger.debug(f"视频缩略图生成成功: {scene_data['video_path']}")
                    else:
                        logger.warning(f"视频缩略图生成失败: {scene_data['video_path']}")

                    if video_thumbnail:
                        thumbnail_label = QLabel()
                        # 与图像缩略图保持一致的尺寸（80x60）
                        scaled_thumbnail = video_thumbnail.scaled(80, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        thumbnail_label.setPixmap(scaled_thumbnail)
                        thumbnail_label.setToolTip(f"视频: {os.path.basename(scene_data['video_path'])}")
                        video_layout.addWidget(thumbnail_label)

                    # 播放按钮
                    play_btn = QPushButton("▶")
                    play_btn.setMaximumSize(30, 25)
                    play_btn.setToolTip("播放视频")
                    play_btn.clicked.connect(lambda checked=False, path=scene_data['video_path']: self.play_video(path))
                    video_layout.addWidget(play_btn)
                else:
                    # 没有视频时显示占位符
                    no_video_label = QLabel("暂无视频")
                    no_video_label.setStyleSheet("color: #666; font-size: 12px;")
                    no_video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    video_layout.addWidget(no_video_label)

                self.scene_table.setCellWidget(row, 4, video_widget)

                # 状态按钮
                action_widget = QWidget()
                action_layout = QVBoxLayout(action_widget)
                action_layout.setContentsMargins(2, 2, 2, 2)
                action_layout.setSpacing(2)

                # 检查配音时长和所需图像数量
                voice_duration = scene_data.get('voice_duration', 0.0)
                required_images, segment_durations = self._check_voice_duration_match(scene_data)
                scene_images = self._get_scene_images(scene_data)

                # 生成视频按钮
                generate_btn = QPushButton("🎬 生成")
                generate_btn.setMaximumSize(80, 25)

                # 根据状态设置按钮样式和文本
                status = scene_data.get('status', '未生成')
                if status == '已生成':
                    generate_btn.setText("🔄 重新生成")
                    generate_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-size: 10px; }")
                elif status == '生成中':
                    generate_btn.setText("⏸ 生成中...")
                    generate_btn.setEnabled(False)
                    generate_btn.setStyleSheet("QPushButton { background-color: #FFC107; color: black; font-size: 10px; }")
                else:
                    generate_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-size: 10px; }")

                # 检查是否有足够的图像文件
                has_enough_images = len(scene_images) >= required_images

                # 设置按钮状态和提示
                if voice_duration > 10.0 and not has_enough_images:
                    generate_btn.setEnabled(False)
                    generate_btn.setToolTip(f"配音时长{voice_duration:.1f}s，需要{required_images}个图像，当前只有{len(scene_images)}个")
                    generate_btn.setStyleSheet("QPushButton { background-color: #F44336; color: white; font-size: 10px; }")
                elif voice_duration > 10.0:
                    generate_btn.setEnabled(True)
                    generate_btn.setToolTip(f"配音时长{voice_duration:.1f}s，将生成{required_images}个视频片段")
                else:
                    has_image = scene_data['image_path'] and os.path.exists(scene_data['image_path'])
                    has_voice = scene_data['voice_path'] and os.path.exists(scene_data['voice_path'])
                    is_not_generating = scene_data.get('status', '未生成') != '生成中'

                    # 确保所有值都是布尔类型
                    enable_button = bool(has_image and has_voice and is_not_generating)
                    generate_btn.setEnabled(enable_button)

                    if voice_duration > 0:
                        generate_btn.setToolTip(f"配音时长{voice_duration:.1f}s，生成单个视频")
                    else:
                        generate_btn.setToolTip("生成视频")

                generate_btn.clicked.connect(lambda checked=False, r=row: self.generate_single_video(r))
                action_layout.addWidget(generate_btn)

                # 如果需要多个图像，显示提示信息
                if voice_duration > 10.0:
                    info_label = QLabel(f"需要{required_images}图")
                    info_label.setStyleSheet("color: #666; font-size: 9px;")
                    info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    action_layout.addWidget(info_label)

                self.scene_table.setCellWidget(row, 5, action_widget)

            # 连接行选择事件
            self.scene_table.itemSelectionChanged.connect(self.on_scene_row_selected)

        except Exception as e:
            logger.error(f"更新场景表格失败: {e}")

    def play_video(self, video_path):
        """播放视频"""
        try:
            import subprocess
            import platform

            if platform.system() == "Windows":
                subprocess.run(["start", video_path], shell=True, check=True)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", video_path], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", video_path], check=True)

        except Exception as e:
            logger.error(f"播放视频失败: {e}")
            QMessageBox.warning(self, "警告", f"无法播放视频: {str(e)}")

    def generate_single_video(self, row):
        """生成单个视频"""
        try:
            if row < 0 or row >= len(self.current_scenes):
                return

            scene_data = self.current_scenes[row]

            # 检查必要文件
            if not scene_data['image_path'] or not os.path.exists(scene_data['image_path']):
                QMessageBox.warning(self, "警告", "该场景缺少图像文件")
                return

            # 开始生成
            self.start_generation([scene_data])

        except Exception as e:
            logger.error(f"生成单个视频失败: {e}")
            QMessageBox.critical(self, "错误", f"生成失败: {str(e)}")

    def on_scene_selection_changed(self):
        """场景选择状态改变"""
        selected_count = self.get_selected_scene_count()
        self.batch_generate_btn.setText(f"🎬 批量生成 ({selected_count})")
        self.batch_generate_btn.setEnabled(selected_count > 0)

    def on_scene_row_selected(self):
        """场景行被选中"""
        try:
            current_row = self.scene_table.currentRow()
            if 0 <= current_row < len(self.current_scenes):
                scene_data = self.current_scenes[current_row]

                # 更新图像预览
                self.update_image_preview(scene_data['image_path'])

                # 更新描述预览 - 显示 original_prompt + technical_details
                original_prompt = scene_data.get('original_prompt', '')
                technical_details = scene_data.get('technical_details', '')

                preview_text = ""
                if original_prompt:
                    preview_text += f"原始描述：\n{original_prompt}\n\n"
                if technical_details:
                    preview_text += f"技术细节：\n{technical_details}"

                if not preview_text:
                    # 如果没有这两个字段，使用原来的逻辑
                    preview_text = scene_data.get('enhanced_description') or scene_data.get('description', '')

                self.description_preview.setPlainText(preview_text)

                # 启用单个生成按钮
                image_path = scene_data.get('image_path', '')
                has_image = bool(image_path and os.path.exists(image_path))
                self.single_generate_btn.setEnabled(has_image)

        except Exception as e:
            logger.error(f"处理场景选择失败: {e}")

    def update_image_preview(self, image_path):
        """更新图像预览"""
        try:
            if image_path and os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    # 缩放图像以适应预览区域
                    scaled_pixmap = pixmap.scaled(
                        self.image_preview.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.image_preview.setPixmap(scaled_pixmap)
                else:
                    self.image_preview.setText("无法加载图像")
            else:
                self.image_preview.setText("无图像文件")

        except Exception as e:
            logger.error(f"更新图像预览失败: {e}")
            self.image_preview.setText("图像加载失败")

    def get_selected_scene_count(self):
        """获取选中的场景数量"""
        count = 0
        for row in range(self.scene_table.rowCount()):
            checkbox = self.scene_table.cellWidget(row, 0)
            if checkbox and isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                count += 1
        return count

    def get_selected_scenes(self):
        """获取选中的场景数据"""
        selected_scenes = []
        for row in range(self.scene_table.rowCount()):
            checkbox = self.scene_table.cellWidget(row, 0)
            if checkbox and isinstance(checkbox, QCheckBox) and checkbox.isChecked() and row < len(self.current_scenes):
                selected_scenes.append(self.current_scenes[row])
        return selected_scenes

    def select_all_scenes(self):
        """全选场景"""
        for row in range(self.scene_table.rowCount()):
            checkbox = self.scene_table.cellWidget(row, 0)
            if checkbox and isinstance(checkbox, QCheckBox):
                checkbox.setChecked(True)

    def select_none_scenes(self):
        """取消全选场景"""
        for row in range(self.scene_table.rowCount()):
            checkbox = self.scene_table.cellWidget(row, 0)
            if checkbox and isinstance(checkbox, QCheckBox):
                checkbox.setChecked(False)

    def start_single_generation(self):
        """开始单个视频生成"""
        try:
            current_row = self.scene_table.currentRow()
            if current_row < 0 or current_row >= len(self.current_scenes):
                QMessageBox.warning(self, "警告", "请先选择一个场景")
                return

            scene_data = self.current_scenes[current_row]

            # 检查必要文件
            if not scene_data['image_path'] or not os.path.exists(scene_data['image_path']):
                QMessageBox.warning(self, "警告", "该场景缺少图像文件")
                return

            # 开始生成
            self.start_generation([scene_data])

        except Exception as e:
            logger.error(f"开始单个生成失败: {e}")
            QMessageBox.critical(self, "错误", f"开始生成失败: {str(e)}")

    def start_batch_generation(self):
        """开始批量视频生成"""
        try:
            selected_scenes = self.get_selected_scenes()

            if not selected_scenes:
                QMessageBox.warning(self, "警告", "请先选择要生成的场景")
                return

            # 检查选中场景的图像文件
            missing_images = []
            for scene in selected_scenes:
                if not scene['image_path'] or not os.path.exists(scene['image_path']):
                    missing_images.append(f"{scene['scene_title']}-{scene['shot_title']}")

            if missing_images:
                reply = QMessageBox.question(
                    self, "确认",
                    f"以下场景缺少图像文件，是否跳过？\n\n{chr(10).join(missing_images)}",
                    QMessageBox.StandardButton.Yes,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

                # 过滤掉缺少图像的场景
                selected_scenes = [s for s in selected_scenes if s['image_path'] and os.path.exists(s['image_path'])]

            if not selected_scenes:
                QMessageBox.warning(self, "警告", "没有可生成的场景")
                return

            # 开始生成
            self.start_generation(selected_scenes)

        except Exception as e:
            logger.error(f"开始批量生成失败: {e}")
            QMessageBox.critical(self, "错误", f"开始生成失败: {str(e)}")

    def start_generation(self, scenes_to_generate):
        """开始视频生成（并发模式）"""
        try:
            # 🔧 修复：动态获取用户设置的并发数
            user_concurrent = int(self.concurrent_tasks_combo.currentText())
            self.max_concurrent_videos = user_concurrent
            logger.info(f"使用用户设置的并发数: {self.max_concurrent_videos}")

            # 检查是否有正在运行的任务
            if len(self.active_workers) >= self.max_concurrent_videos:
                QMessageBox.warning(self, "警告", f"已达到最大并发数({self.max_concurrent_videos})，请等待当前任务完成")
                return

            # 🔧 修复：记录实际提交的场景，用于正确统计
            self._submitted_scenes = scenes_to_generate.copy()

            # 设置生成队列
            self.generation_queue = scenes_to_generate.copy()

            logger.info(f"开始并发生成 {len(scenes_to_generate)} 个视频，最大并发数: {self.max_concurrent_videos}")

            # 启动并发生成
            self.start_concurrent_generation()

        except Exception as e:
            logger.error(f"开始生成失败: {e}")
            QMessageBox.critical(self, "错误", f"开始生成失败: {str(e)}")

    def start_concurrent_generation(self):
        """启动并发生成"""
        try:
            # 启动尽可能多的并发任务
            while (len(self.active_workers) < self.max_concurrent_videos and
                   self.generation_queue):

                # 获取下一个场景
                current_scene = self.generation_queue.pop(0)
                scene_id = current_scene.get('shot_id', f"scene_{len(self.active_workers)}")

                # 启动单个生成任务
                self.start_single_video_generation(current_scene, scene_id)

            logger.info(f"当前活跃任务数: {len(self.active_workers)}/{self.max_concurrent_videos}, 队列剩余: {len(self.generation_queue)}")

        except Exception as e:
            logger.error(f"启动并发生成失败: {e}")

    def start_single_video_generation(self, scene, scene_id):
        """启动单个视频生成任务"""
        try:
            # 获取并设置提示词
            shot_id = scene.get('shot_id', '')
            prompt_from_file = self._get_prompt_for_shot(shot_id)
            if prompt_from_file:
                scene['prompt'] = prompt_from_file
                logger.info(f"为镜头 {shot_id} 设置提示词: {prompt_from_file[:50]}...")
            else:
                scene['prompt'] = scene.get('enhanced_description', scene.get('description', ''))

            # 获取音效提示
            audio_hint = self._get_audio_hint_for_shot(shot_id)
            if audio_hint:
                scene['audio_hint'] = audio_hint

            # 更新状态
            self.update_scene_status(scene, '生成中')

            # 获取生成配置
            image_path = scene.get('image_path', '')
            voice_duration = scene.get('voice_duration', 0.0)

            # 调试日志：检查图像路径
            logger.info(f"准备生成视频 - 镜头ID: {scene.get('shot_id')}, 图像路径: {image_path}")
            if image_path and os.path.exists(image_path):
                logger.info(f"图像文件存在，将进行分辨率调整")
            else:
                logger.warning(f"图像文件不存在或路径为空，将使用默认分辨率1024x1024")

            # 检查是否需要多片段生成
            required_images, segment_durations = self._check_voice_duration_match(scene)
            scene_images = self._get_scene_images(scene)

            if voice_duration > 10.0 and len(scene_images) >= required_images:
                # 多片段生成模式
                self._generate_multi_segment_video(scene, scene_images, segment_durations)
                return
            else:
                # 单片段生成模式
                audio_hint = scene.get('audio_hint')
                generation_config = self.get_generation_config(image_path, voice_duration if voice_duration > 0 else None, audio_hint)

                # 调试日志：检查生成配置
                logger.info(f"生成配置 - 分辨率: {generation_config.get('width')}x{generation_config.get('height')}, 引擎: {generation_config.get('engine')}")

            # 创建工作线程
            worker = VideoGenerationWorker(
                scene,
                generation_config,
                self.project_manager,
                self.project_manager.current_project_name if self.project_manager else None
            )

            # 连接信号
            worker.progress_updated.connect(lambda p, msg, sid=scene_id: self.on_concurrent_progress_updated(sid, p, msg))
            worker.video_generated.connect(lambda path, success, error, sid=scene_id: self.on_concurrent_video_generated(sid, path, success, error))

            # 添加到活跃任务
            self.active_workers[scene_id] = {
                'worker': worker,
                'scene': scene,
                'start_time': time.time()
            }

            # 显示进度界面（如果是第一个任务）
            if len(self.active_workers) == 1:
                self.show_generation_progress()

            # 开始生成
            worker.start()
            logger.info(f"启动视频生成任务: {scene_id}")

        except Exception as e:
            logger.error(f"启动单个生成任务失败: {e}")
            self.update_scene_status(scene, '失败')

    def process_next_generation(self):
        """处理下一个生成任务"""
        try:
            if not self.generation_queue:
                # 所有任务完成
                self.on_all_generation_complete()
                return

            # 获取下一个场景
            current_scene = self.generation_queue.pop(0)

            # 获取并设置提示词
            shot_id = current_scene.get('shot_id', '')
            prompt_from_file = self._get_prompt_for_shot(shot_id)
            if prompt_from_file:
                # 🔧 新增：使用CogVideoX优化器优化提示词
                optimized_prompt = self._optimize_prompt_for_cogvideox(prompt_from_file, shot_id)
                current_scene['prompt'] = optimized_prompt
                logger.info(f"为镜头 {shot_id} 设置优化提示词: {optimized_prompt[:80]}...")
            else:
                # 使用原有的描述作为提示词，也进行优化
                original_desc = current_scene.get('enhanced_description', current_scene.get('description', ''))
                optimized_prompt = self._optimize_prompt_for_cogvideox(original_desc, shot_id)
                current_scene['prompt'] = optimized_prompt

            # 获取音效提示
            audio_hint = self._get_audio_hint_for_shot(shot_id)
            if audio_hint:
                current_scene['audio_hint'] = audio_hint

            # 保存当前生成的场景
            self._current_generating_scene = current_scene

            # 更新状态
            self.update_scene_status(current_scene, '生成中')

            # 检查是否需要多片段生成
            voice_duration = current_scene.get('voice_duration', 0.0)
            required_images, segment_durations = self._check_voice_duration_match(current_scene)
            scene_images = self._get_scene_images(current_scene)

            # 获取生成配置
            image_path = current_scene.get('image_path', '')

            if voice_duration > 10.0 and len(scene_images) >= required_images:
                # 多片段生成模式
                self._generate_multi_segment_video(current_scene, scene_images, segment_durations)
            else:
                # 单片段生成模式
                audio_hint = current_scene.get('audio_hint')
                generation_config = self.get_generation_config(image_path, voice_duration if voice_duration > 0 else None, audio_hint)

            # 创建工作线程
            self.current_worker = VideoGenerationWorker(
                current_scene,
                generation_config,
                self.project_manager,
                self.project_manager.current_project_name if self.project_manager else None
            )

            # 连接信号
            self.current_worker.progress_updated.connect(self.on_progress_updated)
            self.current_worker.video_generated.connect(self.on_video_generated)

            # 显示进度界面
            self.show_generation_progress()

            # 开始生成
            self.current_worker.start()

        except Exception as e:
            logger.error(f"处理下一个生成任务失败: {e}")
            self.on_generation_error(str(e))

    def get_generation_config(self, image_path=None, target_duration=None, audio_hint=None):
        """获取生成配置"""
        try:
            # 默认分辨率
            width, height = 1024, 1024

            # 如果提供了图像路径，尝试获取图像尺寸并调整为支持的分辨率
            if image_path and os.path.exists(image_path):
                try:
                    from PIL import Image
                    with Image.open(image_path) as img:
                        img_width, img_height = img.size
                        logger.info(f"使用图像尺寸: {img_width}x{img_height}")

                        # 调整为支持的分辨率
                        adjusted_resolution = self._adjust_to_supported_resolution(img_width, img_height)
                        width, height = adjusted_resolution

                        if (width, height) != (img_width, img_height):
                            logger.info(f"分辨率调整: {img_width}x{img_height} -> {width}x{height}")

                except Exception as e:
                    logger.warning(f"无法获取图像尺寸，使用默认值: {e}")
            elif not image_path:
                # 只有在没有提供图像路径时才显示警告
                logger.debug("没有提供图像路径，使用默认分辨率 1024x1024")

            # 确定视频时长
            if target_duration is not None:
                # 使用指定的目标时长，自动调整到支持的时长
                original_duration = target_duration
                duration = self._validate_duration(target_duration)
                if duration != original_duration:
                    logger.info(f"目标时长已自动调整: {original_duration}s -> {duration}s")
            else:
                # 使用UI设置的时长
                duration = int(self.duration_combo.currentText())

            config = {
                'engine': 'cogvideox_flash',
                'duration': duration,
                'fps': int(self.fps_combo.currentText()),
                'width': width,
                'height': height,
                'motion_intensity': self.motion_slider.value() / 100.0,
                'max_concurrent_tasks': int(self.concurrent_tasks_combo.currentText())
            }

            # 添加音效提示
            if audio_hint:
                config['audio_hint'] = audio_hint

            return config

        except Exception as e:
            logger.error(f"获取生成配置失败: {e}")
            return {
                'engine': 'cogvideox_flash',
                'duration': 5,
                'fps': 30,
                'width': 1024,
                'height': 1024,
                'motion_intensity': 0.5,
                'max_concurrent_tasks': 3
            }

    def _validate_duration(self, duration):
        """验证并调整视频时长到最接近的支持时长"""
        supported_durations = [5, 10]  # CogVideoX-Flash只支持5秒和10秒

        # 🔧 优化：根据配音时长智能选择视频时长
        # 检查用户是否明确选择了时长
        user_selected_duration = int(self.duration_combo.currentText()) if hasattr(self, 'duration_combo') else 5

        # 如果有目标时长（通常来自配音时长），智能选择最合适的视频时长
        if duration > 0:
            if duration <= 5:
                # 配音时长5秒以内，使用5秒视频
                adjusted_duration = 5
                logger.info(f"配音时长{duration:.1f}s ≤ 5s，选择5秒视频时长")
            elif duration <= 10:
                # 配音时长5-10秒，使用10秒视频
                adjusted_duration = 10
                logger.info(f"配音时长{duration:.1f}s ≤ 10s，选择10秒视频时长")
            else:
                # 配音时长超过10秒，使用10秒视频（后续通过循环播放匹配）
                adjusted_duration = 10
                logger.info(f"配音时长{duration:.1f}s > 10s，选择10秒视频时长（将通过循环播放匹配配音时长）")
        else:
            # 没有目标时长，使用用户选择的时长
            adjusted_duration = user_selected_duration
            logger.info(f"使用用户选择的时长: {adjusted_duration}s")

        return adjusted_duration

    def _adjust_to_supported_resolution(self, width, height):
        """调整为支持的分辨率，优先保持宽高比"""
        # CogVideoX-Flash官方支持的完整分辨率列表
        supported_resolutions = [
            (720, 480),     # 标准清晰度
            (1024, 1024),   # 正方形
            (1280, 960),    # 4:3 横屏
            (960, 1280),    # 3:4 竖屏
            (1920, 1080),   # Full HD 横屏
            (1080, 1920),   # Full HD 竖屏
            (2048, 1080),   # 超宽屏
            (3840, 2160),   # 4K
        ]

        target_ratio = width / height

        # 首先按照图像方向分类
        if target_ratio > 1.2:
            # 横屏图像 (宽 > 高)
            candidate_resolutions = [(w, h) for w, h in supported_resolutions if w > h]
        elif target_ratio < 0.8:
            # 竖屏图像 (高 > 宽)
            candidate_resolutions = [(w, h) for w, h in supported_resolutions if h > w]
        else:
            # 接近正方形的图像
            candidate_resolutions = [(w, h) for w, h in supported_resolutions if 0.8 <= w/h <= 1.2]

        # 如果没有找到同方向的分辨率，使用所有分辨率
        if not candidate_resolutions:
            candidate_resolutions = supported_resolutions

        # 在候选分辨率中找到最佳匹配
        best_resolution = candidate_resolutions[0]
        best_score = float('inf')

        for res_width, res_height in candidate_resolutions:
            res_ratio = res_width / res_height

            # 计算比例差异（权重最高）
            ratio_diff = abs(target_ratio - res_ratio) / max(target_ratio, res_ratio)

            # 计算面积差异
            target_area = width * height
            res_area = res_width * res_height
            area_diff = abs(target_area - res_area) / max(target_area, res_area)

            # 综合评分（比例权重0.8，面积权重0.2）
            score = ratio_diff * 0.8 + area_diff * 0.2

            if score < best_score:
                best_score = score
                best_resolution = (res_width, res_height)

        return best_resolution

    def _generate_video_thumbnail(self, video_path):
        """生成视频缩略图"""
        try:
            # 检查视频文件是否存在
            if not os.path.exists(video_path):
                logger.warning(f"视频文件不存在: {video_path}")
                return None

            # 检查文件大小
            file_size = os.path.getsize(video_path)
            if file_size == 0:
                logger.warning(f"视频文件为空: {video_path}")
                return None

            logger.debug(f"尝试生成视频缩略图: {video_path} (大小: {file_size} 字节)")

            import cv2

            # 打开视频文件
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.warning(f"无法打开视频文件: {video_path}")
                return None

            # 获取视频信息
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps if fps > 0 else 0

            logger.debug(f"视频信息: 帧数={frame_count}, FPS={fps:.2f}, 时长={duration:.2f}秒")

            # 尝试跳到视频的1/4位置获取帧（避免黑屏）
            if frame_count > 10:
                target_frame = min(frame_count // 4, 30)  # 最多跳到第30帧
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                logger.debug(f"跳转到第{target_frame}帧")

            # 获取视频帧
            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                logger.warning(f"无法读取视频帧: {video_path}")
                return None

            # 检查帧的有效性
            if frame.size == 0:
                logger.warning(f"读取到空帧: {video_path}")
                return None

            # 将OpenCV的BGR格式转换为RGB格式
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 转换为QPixmap
            from PyQt5.QtGui import QImage, QPixmap
            height, width, _ = frame_rgb.shape  # 忽略channel变量
            bytes_per_line = 3 * width
            q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)

            if pixmap.isNull():
                logger.warning(f"生成的QPixmap为空: {video_path}")
                return None

            logger.debug(f"成功生成视频缩略图: {video_path} -> {width}x{height}")
            return pixmap

        except ImportError:
            logger.warning("OpenCV未安装，无法生成视频缩略图")
            return None
        except Exception as e:
            logger.error(f"生成视频缩略图失败: {video_path} -> {e}")
            return None

    def _get_prompt_for_shot(self, shot_id):
        """获取指定镜头的提示词"""
        try:
            if not self.project_manager:
                return None

            # 获取项目目录
            project_data = self.project_manager.get_project_data()
            if not project_data:
                return None

            project_dir = project_data.get('project_dir', '')
            if not project_dir:
                # 尝试使用当前项目名称构建路径
                if hasattr(self.project_manager, 'current_project_name') and self.project_manager.current_project_name:
                    project_dir = os.path.join(self.project_manager.projects_dir, self.project_manager.current_project_name)
                elif hasattr(self.project_manager, 'projects_dir'):
                    # 尝试使用默认项目
                    project_dir = os.path.join(self.project_manager.projects_dir, "感人故事")
                else:
                    return None

            # 构建prompt.json文件路径
            prompt_file = os.path.join(project_dir, 'texts', 'prompt.json')
            if not os.path.exists(prompt_file):
                logger.debug(f"prompt.json文件不存在: {prompt_file}")
                return None

            # 读取prompt.json文件
            import json
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = json.load(f)

            # 查找对应的提示词
            # prompt.json的结构是 {"scenes": {"场景名": [镜头数组]}}
            scenes_data = prompt_data.get('scenes', {})

            # 提取shot_id中的数字部分
            shot_index = None
            if shot_id.startswith('text_segment_'):
                try:
                    shot_index = int(shot_id.replace('text_segment_', ''))
                except ValueError:
                    pass

            if shot_index is None:
                logger.debug(f"无法从shot_id '{shot_id}' 提取索引")
                return None

            # 遍历所有场景，找到对应索引的镜头
            current_index = 1
            for scene_name, shots in scenes_data.items():
                if isinstance(shots, list):
                    for shot in shots:
                        if current_index == shot_index:
                            # 🔧 优先使用优化后的提示词
                            optimized_content = shot.get('optimized_content', '')
                            if optimized_content:
                                logger.debug(f"从prompt.json获取镜头 {shot_id} (索引{shot_index}) 的优化提示词")
                                return optimized_content

                            # 如果没有优化提示词，使用原始content
                            content = shot.get('content', '')
                            if content:
                                logger.debug(f"从prompt.json获取镜头 {shot_id} (索引{shot_index}) 的原始提示词")
                                return content
                        current_index += 1

            logger.debug(f"在prompt.json中未找到镜头 {shot_id} 的提示词")
            return None

        except Exception as e:
            logger.warning(f"从prompt.json获取提示词失败: {e}")
            return None

    def _get_audio_hint_for_shot(self, shot_id):
        """获取指定镜头的音效提示"""
        try:
            if not self.project_manager:
                return None

            # 获取项目目录
            project_data = self.project_manager.get_project_data()
            if not project_data:
                return None

            project_dir = project_data.get('project_dir', '')
            if not project_dir:
                # 尝试使用当前项目名称构建路径
                if hasattr(self.project_manager, 'current_project_name') and self.project_manager.current_project_name:
                    project_dir = os.path.join(self.project_manager.projects_dir, self.project_manager.current_project_name)
                elif hasattr(self.project_manager, 'projects_dir'):
                    # 尝试使用默认项目
                    project_dir = os.path.join(self.project_manager.projects_dir, "感人故事")
                else:
                    return None

            # 构建prompt.json文件路径
            prompt_file = os.path.join(project_dir, 'texts', 'prompt.json')
            if not os.path.exists(prompt_file):
                return None

            # 读取prompt.json文件
            import json
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = json.load(f)

            # 查找对应的音效提示
            scenes_data = prompt_data.get('scenes', {})

            # 提取shot_id中的数字部分
            shot_index = None
            if shot_id.startswith('text_segment_'):
                try:
                    shot_index = int(shot_id.replace('text_segment_', ''))
                except ValueError:
                    pass

            if shot_index is None:
                return None

            # 遍历所有场景，找到对应索引的镜头
            current_index = 1
            for scene_name, shots in scenes_data.items():
                if isinstance(shots, list):
                    for shot in shots:
                        if current_index == shot_index:
                            # 从original_description中提取音效提示
                            original_desc = shot.get('original_description', '')
                            import re
                            audio_match = re.search(r'音效提示[：:]\s*([^\n]+)', original_desc)
                            if audio_match:
                                audio_hint = audio_match.group(1).strip()
                                if audio_hint and audio_hint != "无":
                                    logger.info(f"找到镜头 {shot_id} 的音效提示: {audio_hint}")
                                    return audio_hint
                        current_index += 1

            return None

        except Exception as e:
            logger.warning(f"从prompt.json获取音效提示失败: {e}")
            return None

    def _generate_multi_segment_video(self, scene_data, scene_images, segment_durations):
        """生成多片段视频"""
        try:
            # 创建多片段生成工作线程
            self.current_worker = MultiSegmentVideoWorker(
                scene_data,
                scene_images,
                segment_durations,
                self.project_manager,
                self.project_manager.current_project_name if self.project_manager else None
            )

            # 连接信号
            self.current_worker.progress_updated.connect(self.on_progress_updated)
            self.current_worker.video_generated.connect(self.on_video_generated)

            # 显示进度界面
            self.show_generation_progress()

            # 开始生成
            self.current_worker.start()

        except Exception as e:
            logger.error(f"多片段视频生成失败: {e}")
            self.on_generation_error(str(e))

    def show_generation_progress(self):
        """显示生成进度"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.cancel_btn.setVisible(True)
        self.batch_generate_btn.setEnabled(False)
        self.single_generate_btn.setEnabled(False)

    def hide_generation_progress(self):
        """隐藏生成进度"""
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.batch_generate_btn.setEnabled(True)
        self.single_generate_btn.setEnabled(True)

    def update_scene_status(self, scene_data, status):
        """更新场景状态"""
        try:
            logger.info(f"尝试更新场景状态: {scene_data.get('shot_id', 'unknown')} -> {status}")

            # 在场景列表中找到对应场景并更新状态
            scene_found = False
            for i, scene in enumerate(self.current_scenes):
                # 使用多种方式匹配场景
                scene_match = False

                # 方式1：通过scene_id和shot_id匹配
                if (scene.get('scene_id') == scene_data.get('scene_id') and
                    scene.get('shot_id') == scene_data.get('shot_id')):
                    scene_match = True

                # 方式2：通过scene_index和shot_index匹配（兼容旧格式）
                elif (scene.get('scene_index') == scene_data.get('scene_index') and
                      scene.get('shot_index') == scene_data.get('shot_index')):
                    scene_match = True

                # 方式3：通过索引匹配
                elif i < len(self.current_scenes) and scene == scene_data:
                    scene_match = True

                if scene_match:
                    scene['status'] = status
                    scene_found = True
                    logger.info(f"成功更新场景状态: {scene.get('shot_id', 'unknown')} -> {status}")
                    # 刷新表格显示
                    self.update_scene_table()
                    break

            if not scene_found:
                logger.warning(f"未找到匹配的场景，无法更新状态: {scene_data.get('shot_id', 'unknown')}")

        except Exception as e:
            logger.error(f"更新场景状态失败: {e}")

    def on_concurrent_progress_updated(self, scene_id, progress, message):
        """并发进度更新"""
        # 更新总体进度（所有任务的平均进度）
        if self.active_workers:
            total_progress = sum([50 for _ in self.active_workers])  # 假设每个任务50%进度
            avg_progress = total_progress // len(self.active_workers)
            self.progress_bar.setValue(avg_progress)

        # 更新状态信息
        active_count = len(self.active_workers)
        queue_count = len(self.generation_queue)
        self.status_label.setText(f"并发生成中({active_count}个活跃, {queue_count}个等待): {message}")

    def on_concurrent_video_generated(self, scene_id, video_path, success, error_message):
        """并发视频生成完成"""
        try:
            if scene_id not in self.active_workers:
                logger.warning(f"收到未知场景的生成结果: {scene_id}")
                return

            worker_info = self.active_workers[scene_id]
            scene = worker_info['scene']

            if success:
                # 保存视频路径到项目数据
                self._current_generating_scene = scene  # 临时设置用于保存
                self.save_video_to_project(video_path)

                # 更新场景状态
                self.update_scene_status(scene, '已生成')

                # 自动播放视频（仅第一个完成的）
                if self.auto_play_check.isChecked() and len([w for w in self.active_workers.values() if w.get('completed')]) == 0:
                    self.play_video(video_path)

                logger.info(f"视频生成成功: {scene_id} -> {os.path.basename(video_path)}")

                # 标记为完成
                worker_info['completed'] = True

            else:
                # 更新失败状态
                self.update_scene_status(scene, '失败')
                logger.error(f"视频生成失败: {scene_id} -> {error_message}")

            # 从活跃任务中移除
            del self.active_workers[scene_id]

            # 启动下一个任务（如果队列中还有）
            if self.generation_queue:
                logger.info(f"启动下一轮任务，队列剩余: {len(self.generation_queue)}")
                # 🔧 修复：增加延迟以避免网络连接冲突和引擎状态问题
                QTimer.singleShot(3000, self.start_concurrent_generation)  # 增加到3秒延迟

            # 检查是否所有任务都完成
            if not self.active_workers and not self.generation_queue:
                self.on_all_generation_complete()
            else:
                # 更新进度显示
                completed_count = len([s for s in self.current_scenes if s.get('status') == '已生成'])
                total_count = len(self.current_scenes)
                overall_progress = int((completed_count / total_count) * 100) if total_count > 0 else 0
                self.progress_bar.setValue(overall_progress)

                active_count = len(self.active_workers)
                queue_count = len(self.generation_queue)
                self.status_label.setText(f"并发生成中({active_count}个活跃, {queue_count}个等待)")

        except Exception as e:
            logger.error(f"处理并发视频生成结果失败: {e}")

    def on_all_generation_complete(self):
        """所有生成任务完成"""
        try:
            # 隐藏进度界面
            self.hide_generation_progress()

            # 🔧 修复：统计应该基于实际提交的任务，而不是所有场景
            # 获取实际提交的任务ID列表
            submitted_scene_ids = set()
            if hasattr(self, '_submitted_scenes'):
                submitted_scene_ids = set(scene.get('shot_id', '') for scene in self._submitted_scenes)

            # 如果没有记录提交的场景，则使用所有场景（向后兼容）
            if not submitted_scene_ids:
                target_scenes = self.current_scenes
                logger.warning("未找到提交的场景记录，使用所有场景进行统计")
            else:
                # 只统计实际提交的场景
                target_scenes = [s for s in self.current_scenes if s.get('shot_id', '') in submitted_scene_ids]
                logger.info(f"统计基于实际提交的 {len(target_scenes)} 个场景")

            # 更新状态统计
            completed_count = len([s for s in target_scenes if s.get('status') == '已生成'])
            failed_count = len([s for s in target_scenes if s.get('status') == '失败'])
            total_count = len(target_scenes)

            self.status_label.setText(f"所有生成任务完成！成功: {completed_count}, 失败: {failed_count}, 总计: {total_count}")

            # 显示完成通知
            if failed_count == 0:
                QMessageBox.information(self, "完成", f"所有 {completed_count} 个视频生成完成！")
            else:
                QMessageBox.warning(self, "完成", f"生成完成！成功: {completed_count}, 失败: {failed_count}")

            logger.info(f"所有视频生成任务完成 - 成功: {completed_count}, 失败: {failed_count}")

        except Exception as e:
            logger.error(f"处理所有生成完成事件失败: {e}")

    def on_progress_updated(self, progress, message):
        """进度更新（兼容旧版本）"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def on_video_generated(self, video_path, success, error_message):
        """视频生成完成"""
        try:
            if success:
                # 保存视频路径到项目数据
                self.save_video_to_project(video_path)

                # 更新当前场景状态
                if hasattr(self, '_current_generating_scene'):
                    self.update_scene_status(self._current_generating_scene, '已生成')

                # 自动播放视频
                if self.auto_play_check.isChecked():
                    self.play_video(video_path)

                self.status_label.setText(f"视频生成成功: {os.path.basename(video_path)}")

            else:
                # 更新失败状态
                if hasattr(self, '_current_generating_scene'):
                    logger.info(f"更新场景状态为失败: {self._current_generating_scene.get('shot_id', 'unknown')}")
                    self.update_scene_status(self._current_generating_scene, '失败')
                else:
                    logger.warning("没有找到当前生成的场景，无法更新失败状态")

                self.status_label.setText(f"视频生成失败: {error_message}")
                QMessageBox.critical(self, "生成失败", f"视频生成失败:\n{error_message}")

            # 处理下一个任务
            QTimer.singleShot(1000, self.process_next_generation)

        except Exception as e:
            logger.error(f"处理视频生成结果失败: {e}")
            self.on_generation_error(str(e))



    def on_generation_error(self, error_message):
        """生成错误处理"""
        self.hide_generation_progress()
        self.status_label.setText(f"生成错误: {error_message}")
        logger.error(f"视频生成错误: {error_message}")

    def cancel_generation(self):
        """取消生成（支持并发）"""
        try:
            # 取消所有活跃的工作线程
            for scene_id, worker_info in list(self.active_workers.items()):
                worker = worker_info['worker']
                if worker and worker.isRunning():
                    try:
                        if hasattr(worker, 'cancel'):
                            worker.cancel()
                        worker.quit()
                        worker.wait(3000)  # 等待3秒
                    except Exception as e:
                        logger.warning(f"取消工作线程 {scene_id} 时出错: {e}")

            # 取消传统的单线程工作
            if self.current_worker and self.current_worker.isRunning():
                try:
                    if hasattr(self.current_worker, 'cancel'):
                        self.current_worker.cancel()
                    self.current_worker.quit()
                    self.current_worker.wait(3000)  # 等待3秒
                except Exception as e:
                    logger.warning(f"取消当前工作线程时出错: {e}")

            # 清理状态
            self.active_workers.clear()
            self.generation_queue.clear()
            self.hide_generation_progress()
            self.status_label.setText("生成已取消")

            logger.info("所有视频生成任务已取消")

        except Exception as e:
            logger.error(f"取消生成失败: {e}")

    def save_video_to_project(self, video_path):
        """保存视频路径到项目"""
        try:
            if not self.project_manager or not hasattr(self, '_current_generating_scene'):
                return

            # 获取当前生成的场景
            current_scene = self._current_generating_scene
            shot_id = current_scene.get('shot_id', '')

            # 在current_scenes中找到对应场景并更新视频路径
            for scene in self.current_scenes:
                if scene.get('shot_id') == shot_id:
                    scene['video_path'] = video_path
                    logger.info(f"为镜头 {shot_id} 保存视频路径: {video_path}")

                    # 刷新表格显示
                    self.update_scene_table()
                    break

            # 记录视频生成信息到项目数据
            self.record_video_generation(video_path, current_scene)

        except Exception as e:
            logger.error(f"保存视频到项目失败: {e}")

    def record_video_generation(self, video_path, scene_data):
        """记录视频生成信息到项目数据"""
        try:
            if not self.project_manager:
                return

            import os
            import time
            from datetime import datetime

            # 获取视频文件信息
            file_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0

            # 获取生成配置
            config = self.get_generation_config()

            # 创建视频记录
            video_record = {
                "video_id": f"video_{int(time.time())}_{scene_data.get('shot_id', '')}",
                "shot_id": scene_data.get('shot_id', ''),
                "scene_id": scene_data.get('scene_id', ''),
                "video_path": video_path,
                "source_image_path": scene_data.get('image_path', ''),
                "prompt": scene_data.get('enhanced_description', ''),
                "duration": config.get('duration', 5),
                "fps": config.get('fps', 30),
                "width": config.get('width', 1024),
                "height": config.get('height', 1024),
                "motion_intensity": config.get('motion_intensity', 0.5),
                "engine": config.get('engine', 'cogvideox_flash'),
                "generation_time": datetime.now().isoformat(),
                "status": "已生成",
                "file_size": file_size,
                "created_time": datetime.now().isoformat()
            }

            # 添加到项目数据
            self.project_manager.add_video_record(video_record)

            # 🔧 新增：同时保存到shot_mappings中，确保重新加载时能找到视频路径
            try:
                shot_id = scene_data.get('shot_id', '')
                if shot_id and hasattr(self.project_manager, 'current_project') and self.project_manager.current_project:
                    # 直接更新项目数据中的shot_mappings
                    if 'shot_mappings' not in self.project_manager.current_project:
                        self.project_manager.current_project['shot_mappings'] = {}

                    if shot_id not in self.project_manager.current_project['shot_mappings']:
                        self.project_manager.current_project['shot_mappings'][shot_id] = {}

                    self.project_manager.current_project['shot_mappings'][shot_id]['video_path'] = video_path
                    self.project_manager.current_project['shot_mappings'][shot_id]['video_status'] = 'completed'

                    # 保存项目数据
                    self.project_manager.save_project()
                    logger.debug(f"已保存视频路径到shot_mappings: {shot_id} -> {video_path}")
            except Exception as e:
                logger.warning(f"保存视频路径到shot_mappings失败: {e}")

            logger.info(f"已记录视频生成信息: {video_record['video_id']}")

        except Exception as e:
            logger.error(f"记录视频生成信息失败: {e}")

    def play_video(self, video_path):
        """播放视频"""
        try:
            import subprocess
            import platform

            if platform.system() == "Windows":
                os.startfile(video_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", video_path])
            else:  # Linux
                subprocess.run(["xdg-open", video_path])

        except Exception as e:
            logger.error(f"播放视频失败: {e}")

    def open_output_directory(self):
        """打开输出目录"""
        try:
            output_dir = "output/videos"
            if self.project_manager and self.project_manager.current_project:
                project_data = self.project_manager.get_project_data()
                if project_data and 'project_path' in project_data:
                    output_dir = os.path.join(project_data['project_path'], 'videos')

            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            import subprocess
            import platform

            if platform.system() == "Windows":
                os.startfile(output_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", output_dir])
            else:  # Linux
                subprocess.run(["xdg-open", output_dir])

        except Exception as e:
            logger.error(f"打开输出目录失败: {e}")
            QMessageBox.critical(self, "错误", f"打开输出目录失败: {str(e)}")


class MultiSegmentVideoWorker(QThread):
    """多片段视频生成工作线程"""
    progress_updated = pyqtSignal(int, str)
    video_generated = pyqtSignal(bool, str, str)

    def __init__(self, scene_data, scene_images, segment_durations, project_manager, project_name):
        super().__init__()
        self.scene_data = scene_data
        self.scene_images = scene_images
        self.segment_durations = segment_durations
        self.project_manager = project_manager
        self.project_name = project_name

    def run(self):
        """运行多片段视频生成（修复Event loop问题）"""
        try:
            self.progress_updated.emit(0, "开始生成多片段视频...")

            # 创建一个事件循环用于整个生成过程
            import asyncio

            # 确保在新线程中创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 运行异步生成方法
                final_video_path = loop.run_until_complete(self._generate_all_videos_async())
            finally:
                # 确保事件循环正确关闭
                try:
                    # 取消所有未完成的任务
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        for task in pending:
                            task.cancel()

                        # 等待所有任务完成或取消
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

                except Exception as cleanup_error:
                    logger.warning(f"清理事件循环时出错: {cleanup_error}")
                finally:
                    loop.close()

            self.progress_updated.emit(100, "视频生成完成")
            self.video_generated.emit(True, "多片段视频生成成功", final_video_path)

        except Exception as e:
            logger.error(f"多片段视频生成失败: {e}")
            self.video_generated.emit(False, str(e), "")

    async def _generate_all_videos_async(self):
        """异步生成所有视频片段"""
        from src.models.video_engines.video_generation_service import VideoGenerationService

        # 创建视频生成服务
        video_service = VideoGenerationService()
        generated_videos = []
        total_segments = len(self.segment_durations)

        for i, duration in enumerate(self.segment_durations):
            if i >= len(self.scene_images):
                break

            self.progress_updated.emit(
                int((i / total_segments) * 80),
                f"生成第{i+1}/{total_segments}个片段..."
            )

            # 获取当前片段的图像
            image_path = self.scene_images[i]['path']

            try:
                # 生成视频
                result = await video_service.generate_video(
                    prompt=self.scene_data.get('enhanced_description', ''),
                    image_path=image_path,
                    duration=duration,
                    fps=24,
                    width=1024,
                    height=1024,
                    motion_intensity=0.5,
                    preferred_engines=["cogvideox_flash"],
                    project_manager=self.project_manager,
                    current_project_name=self.project_name
                )

                if result.success:
                    generated_videos.append(result.video_path)
                    logger.info(f"片段{i+1}生成成功: {result.video_path}")
                else:
                    raise Exception(result.error_message)

            except Exception as e:
                logger.error(f"片段{i+1}生成失败: {e}")
                raise Exception(f"片段{i+1}生成失败: {e}")

        # 合并视频片段
        self.progress_updated.emit(85, "合并视频片段...")
        final_video_path = self._merge_video_segments(generated_videos)

        return final_video_path

    def _merge_video_segments(self, video_paths):
        """合并视频片段"""
        try:
            if len(video_paths) == 1:
                return video_paths[0]

            # 使用ffmpeg合并视频
            import subprocess
            import tempfile

            # 创建输出文件路径
            output_dir = os.path.dirname(video_paths[0])
            shot_id = self.scene_data.get('shot_id', 'unknown')
            output_path = os.path.join(output_dir, f"{shot_id}_merged.mp4")

            # 创建文件列表
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for video_path in video_paths:
                    f.write(f"file '{video_path}'\n")
                list_file = f.name

            try:
                # 使用ffmpeg合并
                cmd = [
                    'ffmpeg', '-f', 'concat', '-safe', '0',
                    '-i', list_file, '-c', 'copy', output_path, '-y'
                ]
                subprocess.run(cmd, check=True, capture_output=True)

                # 删除临时文件
                os.unlink(list_file)

                # 删除原始片段文件
                for video_path in video_paths:
                    try:
                        os.unlink(video_path)
                    except:
                        pass

                return output_path

            except subprocess.CalledProcessError as e:
                logger.error(f"ffmpeg合并失败: {e}")
                # 如果合并失败，返回第一个片段
                return video_paths[0]

        except Exception as e:
            logger.error(f"合并视频片段失败: {e}")
            # 如果合并失败，返回第一个片段
            return video_paths[0] if video_paths else ""
