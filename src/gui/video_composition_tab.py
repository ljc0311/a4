#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频合成标签页 - 将视频片段、配音、字幕、背景音乐合成为完整短片
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QTextEdit, QGroupBox, QFormLayout, QSpinBox,
    QDoubleSpinBox, QComboBox, QCheckBox, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QSlider,
    QTabWidget, QSplitter, QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon

from src.utils.logger import logger
from src.processors.video_composer import VideoComposer
from src.processors.video_processor import VideoProcessor
from src.core.service_manager import ServiceManager

@dataclass
class VideoSegment:
    """视频片段数据类"""
    id: str
    video_path: str
    audio_path: str
    duration: float
    start_time: float = 0.0
    end_time: float = 0.0
    subtitle_text: str = ""

class VideoCompositionWorker(QThread):
    """视频合成工作线程"""
    progress_updated = pyqtSignal(int, str)
    composition_completed = pyqtSignal(str, bool, str)
    
    def __init__(self, segments: List[VideoSegment], output_path: str, config: Dict):
        super().__init__()
        self.segments = segments
        self.output_path = output_path
        self.config = config
        self.is_cancelled = False
    
    def cancel(self):
        """取消合成"""
        self.is_cancelled = True
    
    def run(self):
        """执行视频合成"""
        composer = None
        try:
            self.progress_updated.emit(5, "初始化视频合成器...")
            composer = VideoComposer()

            if self.is_cancelled:
                return

            self.progress_updated.emit(10, "准备视频片段...")

            # 准备视频片段数据
            video_segments = []
            audio_segments = []

            for i, segment in enumerate(self.segments):
                logger.info(f"片段 {i+1}: video={segment.video_path}, audio={segment.audio_path}")

                # 重新获取准确的配音时长（不信任segment.duration）
                actual_duration = segment.duration  # 默认使用segment中的时长

                if segment.audio_path and os.path.exists(segment.audio_path):
                    # 使用可靠的音频时长检测器重新获取时长
                    try:
                        from src.utils.reliable_audio_duration import get_audio_duration
                        audio_duration = get_audio_duration(segment.audio_path)
                        if audio_duration > 0:
                            actual_duration = audio_duration
                            logger.info(f"✅ 重新获取片段 {i+1} 准确时长: {actual_duration:.2f}s (原时长: {segment.duration:.2f}s)")
                        else:
                            logger.warning(f"⚠️ 无法获取片段 {i+1} 音频时长，使用原时长: {segment.duration:.2f}s")
                    except Exception as e:
                        logger.warning(f"⚠️ 获取片段 {i+1} 音频时长失败: {e}，使用原时长: {segment.duration:.2f}s")

                if os.path.exists(segment.video_path):
                    video_segments.append({
                        'video_path': segment.video_path,
                        'duration': actual_duration,  # 使用准确的时长
                        'subtitle_text': segment.subtitle_text
                    })

                if segment.audio_path and os.path.exists(segment.audio_path):
                    logger.info(f"添加音频片段: {segment.audio_path} (时长: {actual_duration:.2f}s)")
                    audio_segments.append({
                        'audio_path': segment.audio_path,
                        'duration': actual_duration  # 使用准确的时长
                    })
                else:
                    logger.warning(f"音频文件不存在或路径为空: {segment.audio_path}")

            logger.info(f"准备合成: {len(video_segments)} 个视频片段, {len(audio_segments)} 个音频片段")

            if self.is_cancelled:
                return

            self.progress_updated.emit(30, "合成视频片段...")

            # 执行实际的视频合成
            success = composer.compose_final_video(
                video_segments,
                audio_segments,
                self.config.get('background_music', ''),
                self.output_path,
                self.config
            )

            if self.is_cancelled:
                return

            if success:
                self.progress_updated.emit(100, "合成完成！")
                self.composition_completed.emit(self.output_path, True, "视频合成成功")
            else:
                self.composition_completed.emit("", False, "视频合成失败，请检查日志")

        except Exception as e:
            logger.error(f"视频合成失败: {e}")
            self.composition_completed.emit("", False, f"合成失败: {str(e)}")
        finally:
            if composer:
                composer.cleanup()

class VideoCompositionTab(QWidget):
    """视频合成标签页"""
    
    def __init__(self, project_manager=None):
        super().__init__()
        self.project_manager = project_manager
        self.current_segments = []
        self.composition_worker = None
        self.background_music_path = ""

        # 标记初始化状态，避免在初始化过程中触发事件
        self._initializing = True

        try:
            self.init_ui()
            # 初始化完成后再连接信号和加载项目数据
            self._initializing = False
            self._connect_signals()
            # 延迟加载项目数据，避免阻塞
            QTimer.singleShot(500, self.load_project_data)
            logger.info("视频合成页面初始化完成")
        except Exception as e:
            logger.error(f"视频合成页面初始化失败: {e}")
            self._initializing = False

    def _connect_signals(self):
        """连接信号，在初始化完成后调用"""
        try:
            # 连接转场模式切换信号
            self.transition_mode_combo.currentTextChanged.connect(self.on_transition_mode_changed)
            logger.debug("转场信号连接完成")
        except Exception as e:
            logger.warning(f"信号连接失败: {e}")
    
    def init_ui(self):
        """初始化UI界面"""
        main_layout = QVBoxLayout()
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel("🎬 视频合成")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新数据")
        refresh_btn.clicked.connect(self.load_project_data)
        title_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(title_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：视频片段列表和设置
        left_widget = self.create_left_panel()
        splitter.addWidget(left_widget)
        
        # 右侧：预览和控制
        right_widget = self.create_right_panel()
        splitter.addWidget(right_widget)
        
        # 设置分割器比例 - 给左侧更多空间用于视频列表
        splitter.setSizes([500, 400])
        main_layout.addWidget(splitter)
        
        self.setLayout(main_layout)
    
    def create_left_panel(self):
        """创建左侧面板"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 视频片段列表
        segments_group = QGroupBox("📹 视频片段列表")
        segments_layout = QVBoxLayout()
        
        # 片段表格
        self.segments_table = QTableWidget()
        self.segments_table.setColumnCount(5)
        self.segments_table.setHorizontalHeaderLabels([
            "片段", "时长", "配音", "状态", "操作"
        ])
        
        # 设置表格属性
        header = self.segments_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        
        self.segments_table.setColumnWidth(1, 80)
        self.segments_table.setColumnWidth(2, 80)
        self.segments_table.setColumnWidth(3, 80)
        self.segments_table.setColumnWidth(4, 100)

        # 设置表格最小高度，让它占用更多空间
        self.segments_table.setMinimumHeight(400)

        segments_layout.addWidget(self.segments_table)
        segments_group.setLayout(segments_layout)
        layout.addWidget(segments_group, 2)  # 给视频列表更大的拉伸权重
        
        # 合成设置
        settings_group = QGroupBox("⚙️ 合成设置")
        settings_layout = QFormLayout()
        
        # 输出格式
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(["MP4", "AVI", "MOV", "MKV"])
        self.output_format_combo.setCurrentText("MP4")
        settings_layout.addRow("输出格式:", self.output_format_combo)
        
        # 视频质量
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高质量", "标准质量", "压缩质量"])
        self.quality_combo.setCurrentText("标准质量")
        settings_layout.addRow("视频质量:", self.quality_combo)
        
        # 帧率
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setRange(15, 60)
        self.fps_spinbox.setValue(30)
        self.fps_spinbox.setSuffix(" fps")
        settings_layout.addRow("帧率:", self.fps_spinbox)
        
        # 分辨率
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "1920x1080 (1080p)",
            "1280x720 (720p)", 
            "854x480 (480p)",
            "640x360 (360p)"
        ])
        self.resolution_combo.setCurrentText("1280x720 (720p)")
        settings_layout.addRow("分辨率:", self.resolution_combo)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group, 0)  # 不拉伸

        # 字幕样式设置
        subtitle_group = QGroupBox("📝 字幕样式")
        subtitle_layout = QVBoxLayout()

        # 字体设置
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("字体大小:"))
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(12, 72)
        self.font_size_spinbox.setValue(24)
        self.font_size_spinbox.setSuffix(" px")
        font_layout.addWidget(self.font_size_spinbox)

        font_layout.addWidget(QLabel("字体颜色:"))
        self.font_color_button = QPushButton("白色")
        self.font_color_button.setStyleSheet("background-color: white; color: black; padding: 5px;")
        self.font_color_button.clicked.connect(self.select_font_color)
        self.font_color = "#ffffff"  # 默认白色
        font_layout.addWidget(self.font_color_button)

        subtitle_layout.addLayout(font_layout)

        # 描边设置
        outline_layout = QHBoxLayout()
        outline_layout.addWidget(QLabel("描边大小:"))
        self.outline_size_spinbox = QSpinBox()
        self.outline_size_spinbox.setRange(0, 10)
        self.outline_size_spinbox.setValue(2)
        self.outline_size_spinbox.setSuffix(" px")
        outline_layout.addWidget(self.outline_size_spinbox)

        outline_layout.addWidget(QLabel("描边颜色:"))
        self.outline_color_button = QPushButton("黑色")
        self.outline_color_button.setStyleSheet("background-color: black; color: white; padding: 5px;")
        self.outline_color_button.clicked.connect(self.select_outline_color)
        self.outline_color = "#000000"  # 默认黑色
        outline_layout.addWidget(self.outline_color_button)

        subtitle_layout.addLayout(outline_layout)

        # 位置设置
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("字幕位置:"))
        self.subtitle_position_combo = QComboBox()
        self.subtitle_position_combo.addItems(["底部", "顶部", "中间"])
        self.subtitle_position_combo.setCurrentText("底部")
        position_layout.addWidget(self.subtitle_position_combo)

        subtitle_layout.addLayout(position_layout)

        subtitle_group.setLayout(subtitle_layout)
        layout.addWidget(subtitle_group, 0)  # 不拉伸

        
        widget.setLayout(layout)
        return widget
    
    def create_right_panel(self):
        """创建右侧面板"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 预览区域
        preview_group = QGroupBox("👁️ 预览")
        preview_layout = QVBoxLayout()
        
        # 预览信息
        self.preview_info = QTextEdit()
        self.preview_info.setMaximumHeight(150)
        self.preview_info.setPlaceholderText("合成预览信息将显示在这里...")
        preview_layout.addWidget(self.preview_info)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # 转场效果设置
        transition_group = QGroupBox("🎞️ 转场效果")
        transition_layout = QVBoxLayout()

        # 转场模式选择
        transition_mode_layout = QHBoxLayout()
        transition_mode_layout.addWidget(QLabel("转场模式:"))
        self.transition_mode_combo = QComboBox()
        self.transition_mode_combo.addItems(["随机转场", "统一转场", "自定义转场"])
        self.transition_mode_combo.setCurrentText("随机转场")
        transition_mode_layout.addWidget(self.transition_mode_combo)
        transition_layout.addLayout(transition_mode_layout)

        # 统一转场类型选择（默认隐藏）
        self.uniform_transition_layout = QHBoxLayout()
        self.uniform_transition_layout.addWidget(QLabel("转场类型:"))
        self.uniform_transition_combo = QComboBox()
        self.uniform_transition_combo.addItems([
            "淡入淡出", "左滑", "右滑", "上滑", "下滑",
            "缩放", "旋转", "溶解", "擦除", "推拉"
        ])
        self.uniform_transition_combo.setCurrentText("淡入淡出")
        self.uniform_transition_layout.addWidget(self.uniform_transition_combo)
        transition_layout.addLayout(self.uniform_transition_layout)

        # 转场时长和强度设置
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("转场时长:"))
        self.transition_duration_spinbox = QDoubleSpinBox()
        self.transition_duration_spinbox.setRange(0.1, 3.0)
        self.transition_duration_spinbox.setValue(0.5)
        self.transition_duration_spinbox.setSuffix(" 秒")
        self.transition_duration_spinbox.setSingleStep(0.1)
        duration_layout.addWidget(self.transition_duration_spinbox)
        transition_layout.addLayout(duration_layout)

        # 转场强度
        intensity_layout = QHBoxLayout()
        intensity_layout.addWidget(QLabel("转场强度:"))
        self.transition_intensity_slider = QSlider(Qt.Horizontal)
        self.transition_intensity_slider.setRange(1, 10)
        self.transition_intensity_slider.setValue(5)
        self.transition_intensity_label = QLabel("5")
        self.transition_intensity_slider.valueChanged.connect(
            lambda v: self.transition_intensity_label.setText(str(v))
        )
        intensity_layout.addWidget(self.transition_intensity_slider)
        intensity_layout.addWidget(self.transition_intensity_label)
        transition_layout.addLayout(intensity_layout)

        # 初始隐藏统一转场选项
        try:
            self.uniform_transition_combo.setVisible(False)
            if hasattr(self, 'uniform_transition_layout') and self.uniform_transition_layout:
                for i in range(self.uniform_transition_layout.count()):
                    item = self.uniform_transition_layout.itemAt(i)
                    if item and item.widget():
                        item.widget().setVisible(False)
        except Exception as e:
            logger.warning(f"隐藏统一转场选项时出错: {e}")

        transition_group.setLayout(transition_layout)
        layout.addWidget(transition_group)

        # 背景音乐设置
        music_group = QGroupBox("🎵 背景音乐")
        music_layout = QVBoxLayout()

        # 音乐文件选择
        music_file_layout = QHBoxLayout()
        self.music_path_label = QLabel("未选择音乐文件")
        self.music_path_label.setStyleSheet("color: #666; font-style: italic;")
        music_file_layout.addWidget(self.music_path_label)

        select_music_btn = QPushButton("选择音乐")
        select_music_btn.clicked.connect(self.select_background_music)
        music_file_layout.addWidget(select_music_btn)
        music_layout.addLayout(music_file_layout)

        # 音乐音量
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("音量:"))
        self.music_volume_slider = QSlider(Qt.Horizontal)
        self.music_volume_slider.setRange(0, 100)
        self.music_volume_slider.setValue(30)
        self.music_volume_slider.valueChanged.connect(self.update_volume_label)
        volume_layout.addWidget(self.music_volume_slider)
        self.volume_label = QLabel("30%")
        volume_layout.addWidget(self.volume_label)
        music_layout.addLayout(volume_layout)

        # 音乐选项
        self.loop_music_checkbox = QCheckBox("循环播放")
        self.loop_music_checkbox.setChecked(True)
        music_layout.addWidget(self.loop_music_checkbox)

        self.fade_in_checkbox = QCheckBox("淡入效果")
        self.fade_in_checkbox.setChecked(True)
        music_layout.addWidget(self.fade_in_checkbox)

        self.fade_out_checkbox = QCheckBox("淡出效果")
        self.fade_out_checkbox.setChecked(True)
        music_layout.addWidget(self.fade_out_checkbox)

        music_group.setLayout(music_layout)
        layout.addWidget(music_group)

        # 进度区域
        progress_group = QGroupBox("📊 合成进度")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        progress_layout.addWidget(self.progress_label)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("👁️ 预览合成")
        self.preview_btn.clicked.connect(self.preview_composition)
        control_layout.addWidget(self.preview_btn)
        
        self.compose_btn = QPushButton("🎬 开始合成")
        self.compose_btn.clicked.connect(self.start_composition)
        self.compose_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        control_layout.addWidget(self.compose_btn)
        
        self.cancel_btn = QPushButton("❌ 取消合成")
        self.cancel_btn.clicked.connect(self.cancel_composition)
        self.cancel_btn.setVisible(False)
        control_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(control_layout)
        
        # 输出信息
        output_group = QGroupBox("📁 输出")
        output_layout = QVBoxLayout()
        
        # 输出路径
        output_path_layout = QHBoxLayout()
        self.output_path_label = QLabel("输出路径将自动生成")
        self.output_path_label.setStyleSheet("color: #666; font-style: italic;")
        output_path_layout.addWidget(self.output_path_label)
        
        select_output_btn = QPushButton("选择路径")
        select_output_btn.clicked.connect(self.select_output_path)
        output_path_layout.addWidget(select_output_btn)
        
        output_layout.addLayout(output_path_layout)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def load_project_data(self):
        """加载项目数据"""
        try:
            if not self.project_manager:
                logger.warning("项目管理器未初始化")
                return

            # 🔧 修复：如果没有当前项目，显示提示
            if not self.project_manager.current_project:
                logger.warning("没有当前项目，无法加载视频合成数据")
                self.show_no_project_message()
                return

            project_data = self.project_manager.current_project
            project_dir = project_data.get('project_dir', '')

            if not project_dir:
                logger.warning("项目目录不存在")
                return

            logger.info(f"开始加载项目数据: {project_data.get('project_name', 'Unknown')}")

            # 加载视频片段
            self.load_video_segments(project_dir)

            # 更新预览信息 - 添加安全检查
            try:
                self.update_preview_info()
            except Exception as preview_error:
                logger.warning(f"更新预览信息失败，跳过: {preview_error}")

            logger.info("视频合成数据加载完成")

        except Exception as e:
            logger.error(f"加载视频合成数据失败: {e}")

    def show_no_project_message(self):
        """显示无项目提示"""
        try:
            # 清空表格
            self.segments_table.setRowCount(0)

            # 在状态标签中显示提示
            if hasattr(self, 'status_label'):
                self.status_label.setText("请先选择一个项目")

            logger.info("显示无项目提示")

        except Exception as e:
            logger.error(f"显示无项目提示失败: {e}")

    def showEvent(self, event):
        """页面显示时的事件处理"""
        super().showEvent(event)
        try:
            # 页面显示时重新加载项目数据
            logger.info("视频合成页面显示，重新加载项目数据")
            self.load_project_data()
        except Exception as e:
            logger.error(f"页面显示时加载数据失败: {e}")

    def load_video_segments(self, project_dir: str):
        """加载视频片段"""
        try:
            self.current_segments = []

            # 从项目数据中获取视频片段信息
            video_base_dir = os.path.join(project_dir, 'videos')
            audio_dir = os.path.join(project_dir, 'audio', 'edge_tts')

            if not os.path.exists(video_base_dir):
                logger.warning(f"视频目录不存在: {video_base_dir}")
                return

            logger.info(f"视频目录: {video_base_dir}")

            # 从项目数据中获取视频信息
            project_data = self.project_manager.current_project if self.project_manager else {}
            video_generation_data = project_data.get('video_generation', {})
            videos_list = video_generation_data.get('videos', [])

            logger.info(f"项目数据中的视频列表: {len(videos_list)} 个")

            # 使用视频列表创建视频片段对象，并按镜头顺序排序
            video_segments_dict = {}

            for i, video_data in enumerate(videos_list):
                if not isinstance(video_data, dict):
                    logger.warning(f"跳过非字典类型的视频数据: {type(video_data)}")
                    continue

                video_path = video_data.get('video_path', '')
                shot_id = video_data.get('shot_id', '')

                logger.info(f"处理视频 {i+1}/{len(videos_list)}: {shot_id} -> {video_path}")

                # 检查视频文件是否存在
                if not video_path or not os.path.exists(video_path):
                    logger.warning(f"视频文件不存在: {video_path}")
                    continue

                # 从shot_id中提取序号来匹配音频文件和排序
                # shot_id格式可能是 shot_X 或 text_segment_XXX
                segment_number = None

                # 尝试从 shot_X 格式提取
                if shot_id.startswith('shot_'):
                    try:
                        segment_number = int(shot_id.split('_')[-1])
                    except ValueError:
                        pass

                # 尝试从 text_segment_XXX 格式提取
                elif 'text_segment_' in shot_id:
                    try:
                        segment_number = int(shot_id.split('_')[-1])
                    except ValueError:
                        pass

                logger.debug(f"处理视频: {shot_id}, 提取的序号: {segment_number}")

                # 查找对应的音频文件
                audio_path = ""
                if segment_number:
                    # 尝试多种可能的音频文件命名格式
                    possible_audio_files = [
                        f"segment_{segment_number:03d}_text_segment_{segment_number:03d}.mp3",  # 标准格式
                        f"segment_{segment_number:03d}_{shot_id}.mp3",  # 备用格式1
                        f"{shot_id}.mp3",  # 简单格式
                        f"text_segment_{segment_number:03d}.mp3",  # 简化格式
                        f"shot_{segment_number}.mp3",  # shot格式
                        f"shot_{segment_number:03d}.mp3",  # shot格式（补零）
                    ]

                    # 在edge_tts子目录中查找
                    edge_tts_dir = os.path.join(audio_dir, "edge_tts")
                    if os.path.exists(edge_tts_dir):
                        for audio_file in possible_audio_files:
                            possible_path = os.path.join(edge_tts_dir, audio_file)
                            if os.path.exists(possible_path):
                                audio_path = possible_path
                                logger.info(f"找到音频文件: {possible_path}")
                                break

                    # 如果在edge_tts目录没找到，在主音频目录查找
                    if not audio_path:
                        for audio_file in possible_audio_files:
                            possible_path = os.path.join(audio_dir, audio_file)
                            if os.path.exists(possible_path):
                                audio_path = possible_path
                                logger.info(f"找到音频文件: {possible_path}")
                                break

                if not audio_path:
                    logger.warning(f"未找到 {shot_id} 对应的音频文件")

                # 获取配音时长（优先使用配音时长，而不是视频时长）
                duration = 5.0  # 默认时长

                # 方法1：从音频文件获取实际时长（最可靠的方法）
                if audio_path and os.path.exists(audio_path):
                    audio_duration = self.get_audio_duration(audio_path)
                    if audio_duration > 0:
                        duration = audio_duration
                        logger.info(f"✅ 从音频文件获取时长: {shot_id} -> {duration:.2f}s")
                    else:
                        logger.warning(f"⚠️ 音频文件存在但无法获取时长: {audio_path}")

                # 方法2：从项目数据中的配音信息获取（备用方案）
                if duration == 5.0 and hasattr(self, 'project_manager') and self.project_manager:
                    project_data = self.project_manager.current_project
                    if project_data:
                        voice_segments = project_data.get('voice_generation', {}).get('voice_segments', [])
                        for voice_seg in voice_segments:
                            # 匹配shot_id或segment_id
                            voice_shot_id = voice_seg.get('shot_id', '')
                            voice_segment_id = voice_seg.get('segment_id', '')

                            if voice_shot_id == shot_id or voice_segment_id == shot_id:
                                # 尝试从配音数据中获取时长
                                voice_duration = voice_seg.get('duration', 0.0)
                                if voice_duration > 0:
                                    duration = voice_duration
                                    logger.info(f"📊 从配音数据获取时长: {shot_id} -> {duration:.2f}s")
                                    break

                                # 如果配音数据中没有时长，尝试从音频文件路径获取
                                voice_audio_path = voice_seg.get('audio_path', '')
                                if voice_audio_path and os.path.exists(voice_audio_path):
                                    voice_audio_duration = self.get_audio_duration(voice_audio_path)
                                    if voice_audio_duration > 0:
                                        duration = voice_audio_duration
                                        logger.info(f"🎵 从配音数据中的音频文件获取时长: {shot_id} -> {duration:.2f}s")
                                        break

                # 方法3：最后备用方案，使用视频时长（不推荐，因为视频时长可能不准确）
                if duration == 5.0:
                    video_duration = video_data.get('duration', 0.0)
                    if video_duration > 0:
                        duration = video_duration
                        logger.warning(f"⚠️ 使用视频时长（可能不准确）: {shot_id} -> {duration:.2f}s")
                    else:
                        duration = self.get_video_duration(video_path)
                        logger.warning(f"⚠️ 从视频文件获取时长（可能不准确）: {shot_id} -> {duration:.2f}s")

                # 获取字幕文本（从字幕文件中获取）
                subtitle_text = ""
                if segment_number:
                    # 尝试从字幕文件中读取
                    subtitles_dir = os.path.join(os.path.dirname(video_base_dir), "subtitles")

                    # 查找对应的字幕文件，使用通配符匹配
                    import glob
                    pattern = os.path.join(subtitles_dir, f"*_text_segment_{segment_number:03d}_subtitle.srt")
                    subtitle_files = glob.glob(pattern)

                    if subtitle_files:
                        subtitle_file = subtitle_files[0]  # 使用第一个匹配的文件
                        try:
                            with open(subtitle_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                # 提取SRT文件中的文本内容
                                lines = content.split('\n')
                                text_lines = []
                                for line in lines:
                                    line = line.strip()
                                    if line and not line.isdigit() and '-->' not in line:
                                        text_lines.append(line)
                                subtitle_text = ' '.join(text_lines)
                                logger.info(f"加载字幕文件: {subtitle_file}")
                        except Exception as e:
                            logger.warning(f"读取字幕文件失败 {subtitle_file}: {e}")

                    # 如果字幕文件不存在，从配音数据中获取
                    if not subtitle_text and hasattr(self, 'project_manager') and self.project_manager:
                        project_data = self.project_manager.current_project
                        if project_data:
                            voice_segments = project_data.get('voice_generation', {}).get('voice_segments', [])
                            for voice_seg in voice_segments:
                                if voice_seg.get('segment_id') == f"text_segment_{segment_number:03d}":
                                    subtitle_text = voice_seg.get('narrator_text', '') or voice_seg.get('text', '')
                                    logger.info(f"从配音数据获取字幕文本: segment_{segment_number:03d}")
                                    break

                segment = VideoSegment(
                    id=f"shot_{segment_number}" if segment_number else shot_id,  # 使用shot_X格式
                    video_path=video_path,
                    audio_path=audio_path if audio_path and os.path.exists(audio_path) else "",
                    duration=duration,
                    subtitle_text=subtitle_text
                )

                # 使用segment_number作为排序键
                sort_key = segment_number if segment_number else 999
                video_segments_dict[sort_key] = segment

            # 按顺序添加到列表
            for key in sorted(video_segments_dict.keys()):
                segment = video_segments_dict[key]

                self.current_segments.append(segment)

            # 更新表格显示
            self.update_segments_table()

            logger.info(f"加载了 {len(self.current_segments)} 个视频片段")

        except Exception as e:
            logger.error(f"加载视频片段失败: {e}")

    def get_video_duration(self, video_path: str) -> float:
        """获取视频时长（秒）"""
        try:
            # 使用VideoProcessor来获取精确的视频时长
            service_manager = ServiceManager()
            video_processor = VideoProcessor(service_manager)
            video_info = video_processor.get_video_info(video_path)
            duration = video_info.get('duration', 5.0)
            return duration
        except Exception as e:
            logger.warning(f"使用VideoProcessor获取视频时长失败: {e}, 尝试备用方法")
            try:
                # 备用方法，使用VideoComposer
                composer = VideoComposer()
                video_info = composer.get_video_info(video_path)
                duration = video_info.get('duration', 5.0)
                composer.cleanup()
                return duration
            except Exception as e2:
                logger.error(f"备用方法获取视频时长也失败: {e2}")
                return 5.0

    def get_audio_duration(self, audio_path: str) -> float:
        """获取音频文件时长 - 使用多种方法确保准确性"""
        try:
            if not audio_path or not os.path.exists(audio_path):
                logger.warning(f"音频文件不存在: {audio_path}")
                return 0.0

            # 方法1：使用可靠的音频时长检测器
            try:
                from src.utils.reliable_audio_duration import get_audio_duration
                duration = get_audio_duration(audio_path)
                if duration > 0:
                    logger.debug(f"✅ 可靠音频检测器获取时长成功: {os.path.basename(audio_path)} -> {duration:.2f}s")
                    return duration
            except ImportError:
                logger.debug("可靠音频检测器未找到，尝试其他方法")
            except Exception as e:
                logger.debug(f"可靠音频检测器失败: {e}")

            # 方法2：尝试使用mutagen（最可靠的传统方法）
            try:
                from mutagen import File
                audio_file = File(audio_path)
                if audio_file and hasattr(audio_file, 'info') and hasattr(audio_file.info, 'length'):
                    duration = float(audio_file.info.length)
                    logger.debug(f"✅ mutagen获取音频时长成功: {os.path.basename(audio_path)} -> {duration:.2f}s")
                    return duration
            except ImportError:
                logger.debug("mutagen未安装，尝试其他方法")
            except Exception as e:
                logger.debug(f"mutagen获取音频时长失败: {e}")

            # 方法3：使用pydub（如果可用）
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(audio_path)
                duration = len(audio) / 1000.0  # 转换为秒
                logger.debug(f"✅ pydub获取音频时长成功: {os.path.basename(audio_path)} -> {duration:.2f}s")
                return duration
            except ImportError:
                logger.debug("pydub未安装，尝试其他方法")
            except Exception as e:
                logger.debug(f"pydub获取音频时长失败: {e}")

            # 方法4：使用文件大小估算（最后的备用方案）
            try:
                file_size = os.path.getsize(audio_path)
                # 根据文件扩展名调整比特率估算
                ext = os.path.splitext(audio_path)[1].lower()
                if ext == '.mp3':
                    # MP3通常128kbps
                    bitrate = 128 * 1024 / 8  # 字节/秒
                elif ext == '.wav':
                    # WAV通常1411kbps (44.1kHz, 16bit, stereo)
                    bitrate = 1411 * 1024 / 8
                else:
                    # 默认128kbps
                    bitrate = 128 * 1024 / 8

                estimated_duration = file_size / bitrate
                estimated_duration = max(1.0, min(estimated_duration, 60.0))  # 限制在1-60秒之间
                logger.debug(f"⚠️ 文件大小估算音频时长: {os.path.basename(audio_path)} -> {estimated_duration:.2f}s")
                return estimated_duration
            except Exception as e:
                logger.debug(f"文件大小估算失败: {e}")

            logger.warning(f"❌ 所有方法都无法获取音频时长: {os.path.basename(audio_path)}")
            return 0.0

        except Exception as e:
            logger.error(f"获取音频时长失败: {e}")
            return 0.0

    def update_segments_table(self):
        """更新视频片段表格"""
        try:
            self.segments_table.setRowCount(len(self.current_segments))

            for row, segment in enumerate(self.current_segments):
                # 片段名称
                name_item = QTableWidgetItem(segment.id)
                self.segments_table.setItem(row, 0, name_item)

                # 时长
                duration_item = QTableWidgetItem(f"{segment.duration:.1f}s")
                self.segments_table.setItem(row, 1, duration_item)

                # 配音状态
                audio_status = "✅" if segment.audio_path and os.path.exists(segment.audio_path) else "❌"
                audio_item = QTableWidgetItem(audio_status)
                self.segments_table.setItem(row, 2, audio_item)

                # 视频状态
                video_status = "✅" if os.path.exists(segment.video_path) else "❌"
                status_item = QTableWidgetItem(video_status)
                self.segments_table.setItem(row, 3, status_item)

                # 操作按钮
                action_widget = QWidget()
                action_layout = QHBoxLayout()
                action_layout.setContentsMargins(2, 2, 2, 2)

                preview_btn = QPushButton("预览")
                preview_btn.setMaximumSize(50, 25)
                preview_btn.clicked.connect(lambda checked=False, seg=segment: self.preview_segment(seg))
                action_layout.addWidget(preview_btn)

                action_widget.setLayout(action_layout)
                self.segments_table.setCellWidget(row, 4, action_widget)

        except Exception as e:
            logger.error(f"更新视频片段表格失败: {e}")

    def update_preview_info(self):
        """更新预览信息"""
        try:
            # 检查必要的UI组件是否已初始化
            if not hasattr(self, 'preview_info'):
                logger.debug("预览信息组件未初始化，跳过更新")
                return

            if not hasattr(self, 'current_segments'):
                self.preview_info.setText("正在初始化...")
                return

            if not self.current_segments:
                self.preview_info.setText("没有找到视频片段")
                return

            total_duration = sum(seg.duration for seg in self.current_segments)
            video_count = len([seg for seg in self.current_segments if os.path.exists(seg.video_path)])
            audio_count = len([seg for seg in self.current_segments if seg.audio_path and os.path.exists(seg.audio_path)])

            info_text = f"""
📊 合成预览信息:
• 总片段数: {len(self.current_segments)}
• 视频片段: {video_count} 个
• 配音片段: {audio_count} 个
• 预计总时长: {total_duration:.1f} 秒 ({total_duration/60:.1f} 分钟)
"""

            # 安全地获取UI组件的值
            try:
                if hasattr(self, 'output_format_combo'):
                    info_text += f"• 输出格式: {self.output_format_combo.currentText()}\n"
                if hasattr(self, 'quality_combo'):
                    info_text += f"• 视频质量: {self.quality_combo.currentText()}\n"
                if hasattr(self, 'resolution_combo'):
                    info_text += f"• 分辨率: {self.resolution_combo.currentText()}\n"
                if hasattr(self, 'fps_spinbox'):
                    info_text += f"• 帧率: {self.fps_spinbox.value()} fps\n"
            except Exception as ui_error:
                logger.debug(f"获取UI组件值时出错: {ui_error}")

            if self.background_music_path:
                info_text += f"• 背景音乐: {os.path.basename(self.background_music_path)}\n"
                try:
                    if hasattr(self, 'music_volume_slider'):
                        info_text += f"• 音乐音量: {self.music_volume_slider.value()}%\n"
                except Exception:
                    pass

            self.preview_info.setText(info_text.strip())

        except Exception as e:
            logger.error(f"更新预览信息失败: {e}")
            # 设置一个安全的默认文本
            if hasattr(self, 'preview_info'):
                self.preview_info.setText("预览信息更新失败")

    def select_background_music(self):
        """选择背景音乐"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择背景音乐",
                "",
                "音频文件 (*.mp3 *.wav *.aac *.m4a *.ogg);;所有文件 (*)"
            )

            if file_path:
                self.background_music_path = file_path
                self.music_path_label.setText(os.path.basename(file_path))
                self.music_path_label.setStyleSheet("color: #333;")
                self.update_preview_info()
                logger.info(f"选择背景音乐: {file_path}")

        except Exception as e:
            logger.error(f"选择背景音乐失败: {e}")

    def update_volume_label(self, value):
        """更新音量标签"""
        self.volume_label.setText(f"{value}%")

    def select_font_color(self):
        """选择字体颜色"""
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            self.font_color = color.name()
            color_name = self.get_color_name(self.font_color)
            self.font_color_button.setText(color_name)
            self.font_color_button.setStyleSheet(f"background-color: {self.font_color}; color: {'white' if self.is_dark_color(self.font_color) else 'black'}; padding: 5px;")

    def select_outline_color(self):
        """选择描边颜色"""
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            self.outline_color = color.name()
            color_name = self.get_color_name(self.outline_color)
            self.outline_color_button.setText(color_name)
            self.outline_color_button.setStyleSheet(f"background-color: {self.outline_color}; color: {'white' if self.is_dark_color(self.outline_color) else 'black'}; padding: 5px;")

    def get_color_name(self, hex_color):
        """获取颜色名称"""
        color_names = {
            "#ffffff": "白色", "#000000": "黑色", "#ff0000": "红色",
            "#00ff00": "绿色", "#0000ff": "蓝色", "#ffff00": "黄色",
            "#ff00ff": "紫色", "#00ffff": "青色", "#ffa500": "橙色"
        }
        return color_names.get(hex_color.lower(), hex_color)

    def is_dark_color(self, hex_color):
        """判断是否为深色"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return brightness < 128

    def on_transition_mode_changed(self, mode):
        """转场模式改变时的处理"""
        # 如果正在初始化，跳过处理
        if hasattr(self, '_initializing') and self._initializing:
            return

        try:
            if mode == "统一转场":
                # 显示统一转场选项
                if hasattr(self, 'uniform_transition_combo'):
                    self.uniform_transition_combo.setVisible(True)
                if hasattr(self, 'uniform_transition_layout'):
                    for i in range(self.uniform_transition_layout.count()):
                        item = self.uniform_transition_layout.itemAt(i)
                        if item and item.widget():
                            item.widget().setVisible(True)
            else:
                # 隐藏统一转场选项
                if hasattr(self, 'uniform_transition_combo'):
                    self.uniform_transition_combo.setVisible(False)
                if hasattr(self, 'uniform_transition_layout'):
                    for i in range(self.uniform_transition_layout.count()):
                        item = self.uniform_transition_layout.itemAt(i)
                        if item and item.widget():
                            item.widget().setVisible(False)

            # 只在初始化完成后更新预览信息
            if (hasattr(self, 'current_segments') and
                hasattr(self, '_initializing') and
                not self._initializing):
                self.update_preview_info()
        except Exception as e:
            logger.warning(f"转场模式切换处理失败: {e}")

    def select_output_path(self):
        """选择输出路径"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "选择输出路径",
                f"final_video.{self.output_format_combo.currentText().lower()}",
                f"{self.output_format_combo.currentText()} 文件 (*.{self.output_format_combo.currentText().lower()});;所有文件 (*)"
            )

            if file_path:
                self.output_path_label.setText(file_path)
                self.output_path_label.setStyleSheet("color: #333;")
                logger.info(f"选择输出路径: {file_path}")

        except Exception as e:
            logger.error(f"选择输出路径失败: {e}")

    def preview_segment(self, segment: VideoSegment):
        """预览单个视频片段"""
        try:
            if os.path.exists(segment.video_path):
                # 这里可以实现视频预览功能
                QMessageBox.information(self, "预览", f"预览片段: {segment.id}\n路径: {segment.video_path}")
            else:
                QMessageBox.warning(self, "警告", f"视频文件不存在: {segment.video_path}")
        except Exception as e:
            logger.error(f"预览视频片段失败: {e}")

    def preview_composition(self):
        """预览合成效果"""
        try:
            if not self.current_segments:
                QMessageBox.warning(self, "警告", "没有可合成的视频片段")
                return

            # 更新预览信息
            self.update_preview_info()

            QMessageBox.information(self, "预览", "合成预览已更新，请查看右侧预览信息")

        except Exception as e:
            logger.error(f"预览合成失败: {e}")

    def start_composition(self):
        """开始视频合成"""
        try:
            if not self.current_segments:
                QMessageBox.warning(self, "警告", "没有可合成的视频片段")
                return

            # 检查视频文件是否存在
            missing_videos = [seg for seg in self.current_segments if not os.path.exists(seg.video_path)]
            if missing_videos:
                QMessageBox.warning(
                    self,
                    "警告",
                    f"有 {len(missing_videos)} 个视频文件不存在，请先完成图转视频"
                )
                return

            # 生成输出路径
            if "输出路径将自动生成" in self.output_path_label.text():
                if self.project_manager and self.project_manager.current_project:
                    project_dir = self.project_manager.current_project.get('project_dir', '')
                    output_path = os.path.join(project_dir, f"final_video.{self.output_format_combo.currentText().lower()}")
                    self.output_path_label.setText(output_path)
                else:
                    QMessageBox.warning(self, "警告", "请先选择输出路径")
                    return

            output_path = self.output_path_label.text()

            # 准备合成配置
            config = {
                'output_format': self.output_format_combo.currentText(),
                'quality': self.quality_combo.currentText(),
                'fps': self.fps_spinbox.value(),
                'resolution': self.resolution_combo.currentText(),
                'background_music': self.background_music_path,
                'music_volume': self.music_volume_slider.value(),
                'loop_music': self.loop_music_checkbox.isChecked(),
                'fade_in': self.fade_in_checkbox.isChecked(),
                'fade_out': self.fade_out_checkbox.isChecked(),
                'subtitle_config': {
                    'font_size': self.font_size_spinbox.value(),
                    'font_color': self.font_color,
                    'outline_color': self.outline_color,
                    'outline_size': self.outline_size_spinbox.value(),
                    'position': self.subtitle_position_combo.currentText()
                },
                'transition_config': {
                    'mode': self.transition_mode_combo.currentText(),
                    'uniform_type': self.uniform_transition_combo.currentText(),
                    'duration': self.transition_duration_spinbox.value(),
                    'intensity': self.transition_intensity_slider.value()
                }
            }

            # 启动合成工作线程
            self.composition_worker = VideoCompositionWorker(
                self.current_segments,
                output_path,
                config
            )

            self.composition_worker.progress_updated.connect(self.on_progress_updated)
            self.composition_worker.composition_completed.connect(self.on_composition_completed)

            # 更新UI状态
            self.compose_btn.setVisible(False)
            self.cancel_btn.setVisible(True)
            self.progress_bar.setVisible(True)
            self.progress_label.setVisible(True)
            self.progress_bar.setValue(0)

            # 开始合成
            self.composition_worker.start()

            logger.info("开始视频合成")

        except Exception as e:
            logger.error(f"启动视频合成失败: {e}")
            QMessageBox.critical(self, "错误", f"启动合成失败: {str(e)}")

    def cancel_composition(self):
        """取消视频合成"""
        try:
            if self.composition_worker and self.composition_worker.isRunning():
                self.composition_worker.cancel()
                self.composition_worker.quit()
                self.composition_worker.wait(3000)

            # 恢复UI状态
            self.compose_btn.setVisible(True)
            self.cancel_btn.setVisible(False)
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)

            logger.info("视频合成已取消")

        except Exception as e:
            logger.error(f"取消视频合成失败: {e}")

    def on_progress_updated(self, progress: int, message: str):
        """合成进度更新"""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)

    def on_composition_completed(self, output_path: str, success: bool, message: str):
        """合成完成"""
        try:
            # 恢复UI状态
            self.compose_btn.setVisible(True)
            self.cancel_btn.setVisible(False)
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)

            if success:
                QMessageBox.information(
                    self,
                    "成功",
                    f"视频合成完成！\n输出文件: {output_path}"
                )
                logger.info(f"视频合成成功: {output_path}")
            else:
                QMessageBox.critical(self, "失败", f"视频合成失败: {message}")
                logger.error(f"视频合成失败: {message}")

        except Exception as e:
            logger.error(f"处理合成完成事件失败: {e}")
