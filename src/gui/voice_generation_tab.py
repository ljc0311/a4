#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配音生成工作界面
与分镜图像生成标签并列的配音工作标签页
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QLabel, QPushButton, QComboBox, QSlider, QSpinBox, QDoubleSpinBox,
    QLineEdit, QTextEdit, QPlainTextEdit, QCheckBox, QFormLayout,
    QMessageBox, QProgressBar, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QScrollArea, QTabWidget, QProgressDialog,
    QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap

from src.utils.logger import logger
from src.utils.config_manager import ConfigManager
from src.utils.audio_file_manager import AudioFileManager
from src.utils.pixabay_sound_downloader import PixabaySoundDownloader
from src.services.tts_engine_service import TTSEngineManager
from src.gui.styles.unified_theme_system import UnifiedThemeSystem
from src.gui.modern_ui_components import MaterialButton, MaterialCard
from src.utils.shot_id_manager import ShotIDManager, ShotMapping
from src.utils.intelligent_text_splitter import IntelligentTextSplitter, SplitConfig, create_voice_segments_with_duration_control


class VoiceGenerationThread(QThread):
    """配音生成线程"""
    progress_updated = pyqtSignal(int, str)  # progress, message
    voice_generated = pyqtSignal(dict)  # result
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self, engine_manager, engine_name, text_segments, output_dir, settings):
        super().__init__()
        self.engine_manager = engine_manager
        self.engine_name = engine_name
        self.text_segments = text_segments
        self.output_dir = output_dir
        self.settings = settings
        self.results = []
    
    def run(self):
        try:
            total_segments = len(self.text_segments)
            
            for i, segment in enumerate(self.text_segments):
                if self.isInterruptionRequested():
                    break
                
                # 更新进度
                progress = int((i / total_segments) * 100)
                self.progress_updated.emit(progress, f"正在生成第 {i+1}/{total_segments} 段配音...")
                
                # 生成音频文件名
                audio_filename = f"segment_{i+1:03d}_{segment.get('shot_id', 'unknown')}.mp3"
                audio_path = os.path.join(self.output_dir, audio_filename)
                
                # 🔧 修复：生成配音（优先使用原文，如果没有则使用台词）
                text_to_generate = segment.get('original_text', segment.get('dialogue_text', segment.get('text', '')))

                # 检查是否有有效的文本内容
                if not text_to_generate or not text_to_generate.strip():
                    error_msg = f"第 {i+1} 段没有有效的文本内容"
                    logger.error(f"配音生成错误: {error_msg}")
                    self.error_occurred.emit(error_msg)
                    continue

                result = asyncio.run(self.engine_manager.generate_speech(
                    self.engine_name,
                    text_to_generate,
                    audio_path,
                    **self.settings
                ))

                if result.get('success'):
                    segment_result = {
                        'segment_index': i,
                        'shot_id': segment.get('shot_id'),
                        'scene_id': segment.get('scene_id'),  # 🔧 修复：添加scene_id信息
                        'text': text_to_generate,  # 🔧 修复：使用实际生成的文本
                        'audio_path': audio_path,
                        'duration': 0,  # 可以后续添加音频时长检测
                        'status': 'success'
                    }
                    self.results.append(segment_result)
                    self.voice_generated.emit(segment_result)
                else:
                    error_msg = result.get('error', '生成失败')
                    full_error_msg = f"第 {i+1} 段生成失败: {error_msg}"
                    logger.error(f"配音生成错误: {full_error_msg}")
                    self.error_occurred.emit(full_error_msg)
            
            # 完成
            self.progress_updated.emit(100, "配音生成完成")
            
        except Exception as e:
            self.error_occurred.emit(f"配音生成过程中发生错误: {str(e)}")


class SoundEffectGenerationThread(QThread):
    """音效生成线程"""
    progress_updated = pyqtSignal(int, str)  # progress, message
    sound_effect_generated = pyqtSignal(dict)  # result
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self, sound_segments, output_dir):
        super().__init__()
        self.sound_segments = sound_segments
        self.output_dir = output_dir
        self.results = []
        self.downloader = None

    def run(self):
        try:
            # 初始化下载器
            self.downloader = PixabaySoundDownloader(self.output_dir)

            total_segments = len(self.sound_segments)

            for i, segment in enumerate(self.sound_segments):
                if self.isInterruptionRequested():
                    break

                # 更新进度
                progress = int((i / total_segments) * 100)
                self.progress_updated.emit(progress, f"正在生成第 {i+1}/{total_segments} 个音效...")

                # 获取音效描述
                sound_effect_text = segment.get('sound_effect', '').strip()
                if not sound_effect_text:
                    logger.warning(f"第 {i+1} 段没有音效描述，跳过")
                    continue

                # 生成音效文件名
                shot_id = segment.get('shot_id', f'shot_{i+1}')
                filename = f"{shot_id}_sound_effect.mp3"

                try:
                    # 搜索并下载音效
                    logger.info(f"开始为镜头 {shot_id} 搜索音效: {sound_effect_text}")
                    audio_path = self.downloader.search_and_download_shortest(
                        sound_effect_text,
                        filename
                    )

                    if audio_path:
                        # 🔧 修复：使用original_index而不是循环索引i
                        original_index = segment.get('original_index', i)
                        segment_result = {
                            'segment_index': original_index,  # 使用原始索引
                            'shot_id': shot_id,
                            'scene_id': segment.get('scene_id'),  # 🔧 修复：添加scene_id信息
                            'sound_effect_text': sound_effect_text,
                            'audio_path': audio_path,
                            'status': 'success'
                        }
                        self.results.append(segment_result)
                        self.sound_effect_generated.emit(segment_result)
                        logger.info(f"音效生成成功: scene_id='{segment.get('scene_id')}', shot_id='{shot_id}' (原始索引{original_index}) -> {audio_path}")
                    else:
                        error_msg = f"未找到合适的音效: {sound_effect_text}"
                        logger.error(error_msg)
                        self.error_occurred.emit(f"第 {i+1} 段音效生成失败: {error_msg}")

                except Exception as e:
                    error_msg = f"音效生成异常: {str(e)}"
                    logger.error(f"第 {i+1} 段音效生成失败: {error_msg}")
                    self.error_occurred.emit(f"第 {i+1} 段音效生成失败: {error_msg}")

            # 完成
            self.progress_updated.emit(100, "音效生成完成")

        except Exception as e:
            error_msg = f"音效生成过程中发生错误: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)


class VoiceGenerationTab(QWidget):
    """配音生成工作界面"""

    # 🔧 新增：配音优先工作流程信号
    voice_data_ready = pyqtSignal(list)  # 配音数据准备完成，可以开始图像生成
    voice_batch_completed = pyqtSignal(list)  # 批量配音生成完成

    def __init__(self, app_controller, project_manager, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.project_manager = project_manager
        self.parent_window = parent

        # 初始化组件
        self.config_manager = ConfigManager()
        self.engine_manager = TTSEngineManager(self.config_manager)
        self.audio_file_manager = None

        # 🔧 新增：统一镜头ID管理器
        self.shot_id_manager = ShotIDManager()

        # 🔧 新增：智能文本分割器
        self.text_splitter = IntelligentTextSplitter()
        self.target_duration = 10.0  # 默认目标时长10秒

        # 数据
        self.storyboard_data = []
        self.voice_segments = []
        self.generated_audio = []
        self.generation_thread = None
        self.sound_effect_thread = None  # 🔧 新增：音效生成线程
        
        self.init_ui()
        self.apply_styles()

        # 加载项目设置
        self.load_voice_settings_from_project()

        # 连接项目管理器信号（如果存在）
        if self.project_manager and hasattr(self.project_manager, 'project_loaded'):
            self.project_manager.project_loaded.connect(self.on_project_loaded)
        # 延迟加载项目数据，避免初始化时卡住
        QTimer.singleShot(100, self.load_project_data)
    
    def init_ui(self):
        """初始化UI界面"""
        main_layout = QVBoxLayout()
        
        # 标题和状态栏
        self.create_header(main_layout)
        
        # 主工作区域
        self.create_main_work_area(main_layout)
        
        # 底部控制栏
        self.create_control_bar(main_layout)
        
        self.setLayout(main_layout)

    def apply_styles(self):
        """应用简洁现代化样式"""
        try:
            # 应用简洁的样式，参考第二个图片的设计风格
            simple_style = """
                /* 主容器样式 */
                QWidget {
                    background-color: #F5F5F5;
                    color: #333333;
                    font-family: "Microsoft YaHei UI", Arial, sans-serif;
                    font-size: 12px;
                }

                /* 分组框样式 - 简洁边框 */
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #CCCCCC;
                    border-radius: 4px;
                    margin-top: 8px;
                    padding-top: 12px;
                    background-color: white;
                }

                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 8px;
                    padding: 0 4px 0 4px;
                    color: #333333;
                    background-color: white;
                }

                /* 按钮样式 - 简洁设计 */
                QPushButton {
                    background-color: white;
                    border: 1px solid #CCCCCC;
                    border-radius: 3px;
                    padding: 6px 12px;
                    color: #333333;
                    font-size: 12px;
                    min-height: 24px;
                }

                QPushButton:hover {
                    background-color: #F0F0F0;
                    border-color: #999999;
                }

                QPushButton:pressed {
                    background-color: #E0E0E0;
                }

                QPushButton:disabled {
                    background-color: #F8F8F8;
                    color: #AAAAAA;
                    border-color: #E0E0E0;
                }

                /* 表格样式 */
                QTableWidget {
                    background-color: white;
                    border: 1px solid #CCCCCC;
                    gridline-color: #E0E0E0;
                    selection-background-color: #E3F2FD;
                }

                QTableWidget::item {
                    padding: 4px;
                    border-bottom: 1px solid #E0E0E0;
                }

                QHeaderView::section {
                    background-color: #F5F5F5;
                    border: 1px solid #CCCCCC;
                    padding: 4px 8px;
                    font-weight: bold;
                }

                /* 输入框样式 */
                QLineEdit, QTextEdit, QPlainTextEdit {
                    background-color: white;
                    border: 1px solid #CCCCCC;
                    border-radius: 3px;
                    padding: 4px;
                    selection-background-color: #E3F2FD;
                }

                QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
                    border-color: #2196F3;
                }

                /* 下拉框样式 */
                QComboBox {
                    background-color: white;
                    border: 1px solid #CCCCCC;
                    border-radius: 3px;
                    padding: 4px 8px;
                    min-height: 20px;
                }

                QComboBox:hover {
                    border-color: #999999;
                }

                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }

                QComboBox::down-arrow {
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 4px solid #666666;
                    margin-right: 4px;
                }

                /* 进度条样式 */
                QProgressBar {
                    border: 1px solid #CCCCCC;
                    border-radius: 3px;
                    text-align: center;
                    background-color: white;
                    height: 20px;
                }

                QProgressBar::chunk {
                    background-color: #2196F3;
                    border-radius: 2px;
                }

                /* 滑块样式 */
                QSlider::groove:horizontal {
                    border: 1px solid #CCCCCC;
                    height: 6px;
                    background: white;
                    margin: 2px 0;
                    border-radius: 3px;
                }

                QSlider::handle:horizontal {
                    background: #2196F3;
                    border: 1px solid #1976D2;
                    width: 16px;
                    margin: -5px 0;
                    border-radius: 8px;
                }

                QSlider::handle:horizontal:hover {
                    background: #1976D2;
                }

                /* 标签样式 */
                QLabel {
                    color: #333333;
                    background: transparent;
                }

                /* 复选框样式 */
                QCheckBox {
                    color: #333333;
                    spacing: 4px;
                }

                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 1px solid #CCCCCC;
                    border-radius: 2px;
                    background-color: white;
                }

                QCheckBox::indicator:checked {
                    background-color: #2196F3;
                    border-color: #1976D2;
                }

                /* 分割器样式 */
                QSplitter::handle {
                    background-color: #E0E0E0;
                    width: 2px;
                    height: 2px;
                }

                QSplitter::handle:hover {
                    background-color: #CCCCCC;
                }
            """

            self.setStyleSheet(simple_style)
            logger.info("配音界面简洁样式应用完成")

        except Exception as e:
            logger.error(f"应用配音界面样式失败: {e}")

    def create_header(self, parent_layout):
        """创建简洁的标题和状态栏"""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(8)

        # 标题行
        title_layout = QHBoxLayout()
        title_label = QLabel("AI配音生成")
        title_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        title_label.setStyleSheet("color: #333333; font-weight: bold;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 状态标签
        self.status_label = QLabel("请先加载项目数据")
        self.status_label.setStyleSheet("color: #666666; font-size: 11px;")
        title_layout.addWidget(self.status_label)

        header_layout.addLayout(title_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(6)
        header_layout.addWidget(self.progress_bar)

        parent_layout.addWidget(header_frame)
    
    def create_main_work_area(self, parent_layout):
        """创建主工作区域"""
        # 创建水平分割器
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：文本管理和配音列表
        self.create_text_management_panel(main_splitter)
        
        # 右侧：配音设置和控制面板
        self.create_voice_control_panel(main_splitter)
        
        # 设置分割器比例
        main_splitter.setSizes([600, 400])
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)
        
        parent_layout.addWidget(main_splitter)
    
    def create_text_management_panel(self, parent_splitter):
        """创建文本管理面板"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 文本来源选择
        source_group = QGroupBox("配音文本来源")
        source_layout = QVBoxLayout(source_group)
        source_layout.setContentsMargins(12, 16, 12, 12)
        source_layout.setSpacing(8)

        source_btn_layout = QHBoxLayout()
        source_btn_layout.setSpacing(8)

        # 从文本创作导入按钮
        self.import_from_text_btn = QPushButton("从文本创作导入")
        self.import_from_text_btn.clicked.connect(self.import_from_text_creation)
        source_btn_layout.addWidget(self.import_from_text_btn)

        self.manual_input_btn = QPushButton("手动输入文本")
        self.manual_input_btn.clicked.connect(self.show_manual_input)
        source_btn_layout.addWidget(self.manual_input_btn)

        # AI智能分析按钮
        self.ai_analyze_btn = QPushButton("AI智能分析")
        self.ai_analyze_btn.setToolTip("使用AI智能分析旁白内容，自动填充台词和音效")
        self.ai_analyze_btn.clicked.connect(self.ai_analyze_content)
        source_btn_layout.addWidget(self.ai_analyze_btn)

        source_btn_layout.addStretch()
        source_layout.addLayout(source_btn_layout)
        
        left_layout.addWidget(source_group)
        
        # 配音文本列表
        text_group = QGroupBox("配音文本列表")
        text_layout = QVBoxLayout(text_group)
        text_layout.setContentsMargins(12, 16, 12, 12)
        text_layout.setSpacing(8)

        # 添加说明文字
        info_label = QLabel("说明：当前配音功能主要针对原文（旁白）内容。台词和音效功能将在后续版本中完善。")
        info_label.setStyleSheet("""
            color: #666666;
            font-size: 11px;
            padding: 6px;
            background-color: #F8F8F8;
            border: 1px solid #E0E0E0;
            border-radius: 3px;
        """)
        info_label.setWordWrap(True)
        text_layout.addWidget(info_label)

        # 创建表格
        self.text_table = QTableWidget()
        self.setup_text_table()
        text_layout.addWidget(self.text_table)
        
        # 文本操作按钮
        text_btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("☑️ 全选")
        self.select_all_btn.clicked.connect(self.select_all_rows)
        text_btn_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("☐ 取消全选")
        self.deselect_all_btn.clicked.connect(self.deselect_all_rows)
        text_btn_layout.addWidget(self.deselect_all_btn)

        text_btn_layout.addStretch()
        text_layout.addLayout(text_btn_layout)
        
        left_layout.addWidget(text_group)
        
        parent_splitter.addWidget(left_widget)
    
    def create_voice_control_panel(self, parent_splitter):
        """创建配音控制面板"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(12)

        # 配音引擎设置
        engine_group = QGroupBox("配音引擎设置")
        engine_layout = QFormLayout(engine_group)
        engine_layout.setContentsMargins(12, 16, 12, 12)
        engine_layout.setVerticalSpacing(8)
        engine_layout.setHorizontalSpacing(12)

        # 引擎选择
        self.engine_combo = QComboBox()
        engines = [
            ('edge_tts', 'Edge-TTS (免费)'),
            ('cosyvoice', 'CosyVoice (本地)'),
            ('azure_speech', 'Azure Speech (免费额度)'),
            ('google_tts', 'Google Cloud TTS (免费额度)'),
            ('baidu_tts', '百度智能云 (免费额度)')
        ]
        for engine_id, engine_name in engines:
            self.engine_combo.addItem(engine_name, engine_id)
        self.engine_combo.currentTextChanged.connect(self.on_engine_changed)
        self.engine_combo.currentTextChanged.connect(self.on_voice_settings_changed)
        engine_layout.addRow("配音引擎:", self.engine_combo)

        # 初始化时触发引擎改变事件，加载音色列表
        QTimer.singleShot(100, self.on_engine_changed)

        # 音色选择
        self.voice_combo = QComboBox()
        self.voice_combo.currentTextChanged.connect(self.on_voice_settings_changed)
        engine_layout.addRow("音色:", self.voice_combo)

        # 语速设置
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_label = QLabel("100%")
        self.speed_label.setMinimumWidth(40)
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(f"{v}%")
        )
        self.speed_slider.valueChanged.connect(self.on_voice_settings_changed)
        speed_layout = QHBoxLayout()
        speed_layout.setSpacing(8)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_label)
        engine_layout.addRow("语速:", speed_layout)

        right_layout.addWidget(engine_group)
        
        # 配音预览
        preview_group = QGroupBox("配音预览")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(12, 16, 12, 12)
        preview_layout.setSpacing(8)

        self.preview_text = QPlainTextEdit()
        self.preview_text.setPlaceholderText("选择文本段落查看预览...")
        self.preview_text.setMaximumHeight(100)
        preview_layout.addWidget(self.preview_text)

        preview_btn_layout = QHBoxLayout()
        preview_btn_layout.setSpacing(8)

        self.test_voice_btn = QPushButton("测试配音")
        self.test_voice_btn.clicked.connect(self.test_voice)
        preview_btn_layout.addWidget(self.test_voice_btn)

        self.play_audio_btn = QPushButton("播放音频")
        self.play_audio_btn.clicked.connect(self.play_audio)
        self.play_audio_btn.setEnabled(False)
        preview_btn_layout.addWidget(self.play_audio_btn)

        preview_btn_layout.addStretch()
        preview_layout.addLayout(preview_btn_layout)

        right_layout.addWidget(preview_group)

        # 生成的音频列表
        audio_group = QGroupBox("生成的音频")
        audio_layout = QVBoxLayout(audio_group)
        audio_layout.setContentsMargins(12, 16, 12, 12)
        audio_layout.setSpacing(8)

        self.audio_list = QTableWidget()
        self.setup_audio_table()
        audio_layout.addWidget(self.audio_list)

        # 音频操作按钮
        audio_btn_layout = QHBoxLayout()
        audio_btn_layout.setSpacing(8)

        self.export_audio_btn = QPushButton("导出音频")
        self.export_audio_btn.clicked.connect(self.export_audio)
        audio_btn_layout.addWidget(self.export_audio_btn)

        self.clear_audio_btn = QPushButton("清空音频")
        self.clear_audio_btn.clicked.connect(self.clear_audio)
        audio_btn_layout.addWidget(self.clear_audio_btn)

        audio_btn_layout.addStretch()
        audio_layout.addLayout(audio_btn_layout)
        
        right_layout.addWidget(audio_group)
        
        parent_splitter.addWidget(right_widget)
    
    def create_control_bar(self, parent_layout):
        """创建底部控制栏"""
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(12, 8, 12, 8)
        control_layout.setSpacing(8)

        # 批量操作分组
        batch_group = QGroupBox("批量操作")
        batch_layout = QHBoxLayout(batch_group)
        batch_layout.setContentsMargins(8, 12, 8, 8)
        batch_layout.setSpacing(6)

        self.generate_all_btn = QPushButton("批量生成配音")
        self.generate_all_btn.clicked.connect(self.generate_all_voice)
        batch_layout.addWidget(self.generate_all_btn)

        self.generate_selected_btn = QPushButton("生成选中配音")
        self.generate_selected_btn.clicked.connect(self.generate_selected_voice)
        batch_layout.addWidget(self.generate_selected_btn)

        self.generate_sound_effects_btn = QPushButton("批量生成音效")
        self.generate_sound_effects_btn.clicked.connect(self.generate_selected_sound_effects)
        batch_layout.addWidget(self.generate_sound_effects_btn)

        control_layout.addWidget(batch_group)

        # 🔧 新增：时长控制分组
        duration_group = QGroupBox("时长控制")
        duration_layout = QHBoxLayout(duration_group)
        duration_layout.setContentsMargins(8, 12, 8, 8)
        duration_layout.setSpacing(6)

        duration_layout.addWidget(QLabel("目标时长:"))
        self.duration_spinbox = QDoubleSpinBox()
        self.duration_spinbox.setRange(5.0, 30.0)
        self.duration_spinbox.setValue(self.target_duration)
        self.duration_spinbox.setSuffix(" 秒")
        self.duration_spinbox.setDecimals(1)
        self.duration_spinbox.valueChanged.connect(self.on_target_duration_changed)
        duration_layout.addWidget(self.duration_spinbox)

        self.smart_split_btn = QPushButton("智能重新分割")
        self.smart_split_btn.clicked.connect(self.smart_resplit_text)
        duration_layout.addWidget(self.smart_split_btn)

        control_layout.addWidget(duration_group)

        # 高级功能分组
        advanced_group = QGroupBox("高级功能")
        advanced_layout = QHBoxLayout(advanced_group)
        advanced_layout.setContentsMargins(8, 12, 8, 8)
        advanced_layout.setSpacing(6)

        self.voice_driven_storyboard_btn = QPushButton("生成配音驱动分镜")
        self.voice_driven_storyboard_btn.clicked.connect(self.generate_voice_driven_storyboard)
        advanced_layout.addWidget(self.voice_driven_storyboard_btn)

        self.save_project_btn = QPushButton("保存到项目")
        self.save_project_btn.clicked.connect(self.save_to_project)
        advanced_layout.addWidget(self.save_project_btn)

        control_layout.addWidget(advanced_group)
        control_layout.addStretch()

        parent_layout.addWidget(control_frame)

    def on_target_duration_changed(self, value):
        """目标时长改变回调"""
        self.target_duration = value
        # 更新分割器配置
        self.text_splitter.config.target_duration = value
        logger.info(f"目标时长已更新为: {value}秒")

    def smart_resplit_text(self):
        """智能重新分割文本"""
        try:
            # 获取当前项目的原文
            project_data = self.project_manager.get_project_data()
            if not project_data:
                QMessageBox.warning(self, "警告", "没有加载项目数据")
                return

            # 从文本创作模块获取原文
            created_text = project_data.get('text_creation', {}).get('created_text', '')
            if not created_text:
                QMessageBox.warning(self, "警告", "没有找到原文，请先在文本创作模块中创建文本")
                return

            # 使用智能分割器重新分割
            logger.info(f"开始智能重新分割，目标时长: {self.target_duration}秒")
            voice_segments = create_voice_segments_with_duration_control(created_text, self.target_duration)

            if not voice_segments:
                QMessageBox.warning(self, "警告", "文本分割失败")
                return

            # 更新配音段落
            self.voice_segments = voice_segments

            # 更新表格显示
            self.update_text_table()

            # 显示分割结果
            avg_duration = sum(s['estimated_duration'] for s in voice_segments) / len(voice_segments)
            QMessageBox.information(
                self,
                "分割完成",
                f"智能分割完成！\n\n"
                f"生成段落数: {len(voice_segments)}\n"
                f"平均时长: {avg_duration:.1f}秒\n"
                f"目标时长: {self.target_duration}秒"
            )

        except Exception as e:
            logger.error(f"智能重新分割失败: {e}")
            QMessageBox.critical(self, "错误", f"智能重新分割失败: {str(e)}")
    
    def setup_text_table(self):
        """设置文本表格"""
        # 🔧 优化：移除不必要的列，专注于配音驱动工作流程
        headers = ["选择", "旁白", "台词", "音效", "状态", "操作"]
        self.text_table.setColumnCount(len(headers))
        self.text_table.setHorizontalHeaderLabels(headers)

        # 设置表格属性
        self.text_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.text_table.setAlternatingRowColors(True)

        # 🔧 设置行高 - 适合文本内容显示
        self.text_table.verticalHeader().setDefaultSectionSize(80)  # 减少行高，专注文本内容
        self.text_table.verticalHeader().setMinimumSectionSize(60)  # 设置最小行高

        # 设置列宽 - 允许用户拖动调整所有列的大小
        header = self.text_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)      # 选择 - 固定宽度
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # 旁白 - 可调整
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # 台词 - 可调整
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # 音效 - 可调整
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)      # 状态 - 固定宽度
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)      # 操作 - 固定宽度

        # 🔧 设置初始列宽 - 优化配音驱动界面布局
        self.text_table.setColumnWidth(0, 50)   # 选择
        self.text_table.setColumnWidth(1, 300)  # 旁白 - 加宽以显示更多内容
        self.text_table.setColumnWidth(2, 200)  # 台词 - 适中宽度
        self.text_table.setColumnWidth(3, 150)  # 音效 - 适中宽度
        self.text_table.setColumnWidth(4, 80)   # 状态 - 固定宽度
        self.text_table.setColumnWidth(5, 120)  # 操作 - 固定宽度

        # 连接信号
        self.text_table.itemSelectionChanged.connect(self.on_text_selection_changed)
        # 🔧 连接单元格编辑信号
        self.text_table.itemChanged.connect(self.on_table_item_changed)

    def _create_image_preview_widget(self, segment, segment_index):
        """创建图片预览组件"""
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(2, 2, 2, 2)
            layout.setSpacing(2)

            # 创建图片标签
            image_label = QLabel()
            image_label.setFixedSize(90, 90)
            image_label.setScaledContents(True)
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background-color: #f5f5f5;
                }
            """)

            # 查找对应的图片
            image_path = self._find_image_for_segment(segment, segment_index)
            logger.debug(f"图片查找结果: segment_index={segment_index}, scene_id='{segment.get('scene_id')}', shot_id='{segment.get('shot_id')}', image_path='{image_path}'")

            if image_path and os.path.exists(image_path):
                # 加载并显示图片
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(88, 88, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    image_label.setPixmap(scaled_pixmap)
                    image_label.setToolTip(f"镜头图片: {os.path.basename(image_path)}")
                    logger.debug(f"成功加载图片: {image_path}")
                else:
                    image_label.setText("图片\n加载失败")
                    image_label.setToolTip("图片加载失败")
                    logger.warning(f"图片加载失败: {image_path}")
            else:
                image_label.setText("暂无\n图片")
                image_label.setToolTip("暂无对应图片")
                logger.debug(f"未找到图片: segment_index={segment_index}, scene_id='{segment.get('scene_id')}', shot_id='{segment.get('shot_id')}')")

            layout.addWidget(image_label)
            return widget

        except Exception as e:
            logger.error(f"创建图片预览组件失败: {e}")
            # 返回空白组件
            widget = QWidget()
            label = QLabel("图片\n错误")
            label.setFixedSize(90, 90)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout = QVBoxLayout(widget)
            layout.addWidget(label)
            return widget

    def _find_image_for_segment(self, segment, segment_index):
        """查找段落对应的图片"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return None

            project_root = self.project_manager.current_project.get('project_dir') or self.project_manager.current_project.get('project_root')
            if not project_root:
                return None

            # 获取镜头信息
            scene_id = segment.get('scene_id', '')
            shot_id = segment.get('shot_id', '')

            # 方法1：从项目数据中查找图片映射
            project_data = self.project_manager.get_project_data()
            if project_data:
                shot_mappings = project_data.get('shot_image_mappings', {})

                # 🔧 修复：正确映射scene_id和shot_id到图片映射键
                # 将"场景1：小北的家乡与童年"转换为"scene_1"
                scene_number = self._extract_scene_number(scene_id)
                # 将"镜头1"转换为"shot_1"
                shot_number = self._extract_shot_number(shot_id)

                # 🔧 修复：计算全局镜头索引
                # 场景1有7个镜头，场景2从第8个镜头开始，场景3从第12个镜头开始
                global_shot_index = segment_index + 1  # 基于segment_index计算全局索引

                # 尝试不同的键格式
                possible_keys = [
                    f"scene_{scene_number}_shot_{global_shot_index}",  # 全局索引格式
                    f"scene_{scene_number}_shot_{shot_number}",  # 场景内索引格式
                    f"{scene_id}_{shot_id}",  # 原始格式
                    shot_id,
                    f"镜头{global_shot_index}",
                    f"镜头{shot_number}",
                    str(global_shot_index)
                ]

                logger.debug(f"查找图片映射: scene_id='{scene_id}', shot_id='{shot_id}', 尝试键: {possible_keys}")

                for key in possible_keys:
                    if key in shot_mappings:
                        mapping = shot_mappings[key]
                        if isinstance(mapping, dict):
                            # 尝试不同的图片路径字段
                            image_path = (mapping.get('main_image_path') or
                                        mapping.get('image_path') or
                                        mapping.get('main_image'))

                            if image_path and os.path.exists(image_path):
                                logger.debug(f"找到图片: {key} -> {image_path}")
                                return image_path

            # 方法2：从图片目录中查找
            images_dir = os.path.join(project_root, 'images')
            if os.path.exists(images_dir):
                # 查找可能的图片文件名
                possible_names = [
                    f"{shot_id}.png",
                    f"{shot_id}.jpg",
                    f"{scene_id}_{shot_id}.png",
                    f"{scene_id}_{shot_id}.jpg",
                    f"shot_{segment_index + 1:03d}.png",
                    f"shot_{segment_index + 1:03d}.jpg"
                ]

                for engine_dir in os.listdir(images_dir):
                    engine_path = os.path.join(images_dir, engine_dir)
                    if os.path.isdir(engine_path):
                        for name in possible_names:
                            image_path = os.path.join(engine_path, name)
                            if os.path.exists(image_path):
                                return image_path

            return None

        except Exception as e:
            logger.error(f"查找段落图片失败: {e}")
            return None

    def _extract_scene_number(self, scene_id):
        """从场景ID中提取场景编号"""
        try:
            import re
            # 从"场景1：小北的家乡与童年"中提取"1"
            match = re.search(r'场景(\d+)', scene_id)
            if match:
                return match.group(1)
            return "1"  # 默认返回1
        except Exception:
            return "1"

    def _extract_shot_number(self, shot_id):
        """从镜头ID中提取镜头编号"""
        try:
            import re
            # 从"镜头1"中提取"1"
            match = re.search(r'镜头(\d+)', shot_id)
            if match:
                return match.group(1)
            return "1"  # 默认返回1
        except Exception:
            return "1"

    def on_table_item_changed(self, item):
        """处理表格单元格编辑"""
        try:
            row = item.row()
            col = item.column()

            if row >= len(self.voice_segments):
                return

            # 🔧 修复：更新列索引 - 旁白(1)、台词(2)、音效(3)
            if col == 1:  # 旁白列（原文）
                self.voice_segments[row]['original_text'] = item.text()
                logger.info(f"更新镜头{row+1}旁白: {item.text()[:30]}...")
            elif col == 2:  # 台词列
                self.voice_segments[row]['dialogue_text'] = item.text()
                # 如果用户输入了台词内容，标记为台词类型
                if item.text().strip():
                    self.voice_segments[row]['content_type'] = '台词'
                else:
                    # 如果清空了台词，恢复为旁白类型
                    self.voice_segments[row]['content_type'] = '旁白'
                logger.info(f"更新镜头{row+1}台词: {item.text()[:30]}...")
            elif col == 3:  # 音效列
                self.voice_segments[row]['sound_effect'] = item.text()
                logger.info(f"更新镜头{row+1}音效: {item.text()[:30]}...")

        except Exception as e:
            logger.error(f"处理表格编辑失败: {e}")
    
    def setup_audio_table(self):
        """设置音频表格"""
        # 🔧 修复：删除操作列，只保留旁白、音效、时长
        headers = ["旁白", "音效", "时长"]
        self.audio_list.setColumnCount(len(headers))
        self.audio_list.setHorizontalHeaderLabels(headers)

        # 设置表格属性
        self.audio_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.audio_list.setAlternatingRowColors(True)

        # 设置列宽
        header = self.audio_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 旁白
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 音效
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # 时长

        self.audio_list.setColumnWidth(2, 100)  # 时长列宽度增加
    
    def load_project_data(self):
        """加载项目数据"""
        try:
            logger.info("开始加载配音界面项目数据...")

            if not self.project_manager or not self.project_manager.current_project:
                self.status_label.setText("请先创建或加载项目")
                logger.info("配音界面：没有当前项目，跳过数据加载")
                return

            # 初始化音频文件管理器
            project_root = self.project_manager.current_project.get('project_dir') or self.project_manager.current_project.get('project_root')
            if project_root:
                self.audio_file_manager = AudioFileManager(project_root)
                logger.info(f"配音界面：音频文件管理器初始化完成，项目根目录: {project_root}")

            # 从项目中加载配音数据
            project_data = self.project_manager.get_project_data()
            if project_data:
                # 🔧 新增：初始化ID管理器
                self.shot_id_manager.initialize_from_project_data(project_data)
                logger.info("配音界面：ID管理器初始化完成")

                voice_data = project_data.get('voice_generation', {})
                if voice_data:
                    self.load_voice_data(voice_data)
                    logger.info("配音界面：已加载现有配音数据")

                # 自动从分镜数据加载文本（静默模式）- 添加超时保护
                try:
                    logger.info("配音界面：开始解析分镜数据...")
                    self.parse_storyboard_data(project_data)
                    self.update_text_table()
                    logger.info("配音界面：分镜数据解析完成")
                except Exception as parse_error:
                    logger.warning(f"配音界面：解析分镜数据时出错，跳过: {parse_error}")

            self.status_label.setText("项目数据加载完成")
            logger.info("配音界面：项目数据加载完成")

        except Exception as e:
            logger.error(f"配音界面：加载项目数据失败: {e}")
            self.status_label.setText(f"加载失败: {e}")

    def manual_load_from_storyboard(self):
        """手动从分镜脚本加载文本（显示消息）"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                QMessageBox.warning(self, "警告", "请先加载项目")
                return

            # 获取分镜数据
            project_data = self.project_manager.get_project_data()
            if not project_data:
                QMessageBox.warning(self, "警告", "项目数据为空")
                return

            # 解析分镜数据
            self.parse_storyboard_data(project_data)
            self.update_text_table()

            if len(self.voice_segments) > 0:
                self.status_label.setText(f"已从分镜脚本加载 {len(self.voice_segments)} 个文本段落")
                QMessageBox.information(self, "加载成功", f"成功加载 {len(self.voice_segments)} 个配音段落")
            else:
                self.status_label.setText("未找到可用的分镜数据")
                QMessageBox.warning(self, "提示", "未找到可用的分镜数据，请检查项目是否包含五阶段分镜内容")

        except Exception as e:
            logger.error(f"手动加载分镜脚本失败: {e}")
            QMessageBox.critical(self, "错误", f"加载失败: {e}")

    def load_from_storyboard(self):
        """从分镜脚本加载文本"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                QMessageBox.warning(self, "警告", "请先加载项目")
                return
            
            # 获取分镜数据
            project_data = self.project_manager.get_project_data()
            if not project_data:
                QMessageBox.warning(self, "警告", "项目数据为空")
                return
            
            # 解析分镜数据
            self.parse_storyboard_data(project_data)
            self.update_text_table()
            
            self.status_label.setText(f"已从分镜脚本加载 {len(self.voice_segments)} 个文本段落")
            
        except Exception as e:
            logger.error(f"从分镜脚本加载文本失败: {e}")
            QMessageBox.critical(self, "错误", f"加载失败: {e}")
    
    def parse_storyboard_data(self, project_data):
        """智能解析分镜数据 - 增强版本，确保与图像数量一致"""
        self.voice_segments = []

        logger.info(f"开始解析项目数据，项目数据键: {list(project_data.keys())}")

        # 🔧 新增：首先获取已生成图像的数量作为基准 - 添加安全检查
        try:
            expected_shot_count = self._get_expected_shot_count(project_data)
            logger.info(f"预期镜头数量（基于图像生成数据）: {expected_shot_count}")
        except Exception as e:
            logger.warning(f"获取预期镜头数量失败: {e}，使用默认值")
            expected_shot_count = 0

        # 从五阶段分镜数据中提取
        five_stage_data = project_data.get('five_stage_storyboard', {})
        logger.info(f"五阶段数据: {list(five_stage_data.keys()) if five_stage_data else '无数据'}")

        stage_data = five_stage_data.get('stage_data', {})
        logger.info(f"阶段数据: {list(stage_data.keys()) if stage_data else '无数据'}")

        # 优先从阶段5获取优化后的分镜数据
        stage5_data = stage_data.get('5', {})
        storyboard_results = stage5_data.get('storyboard_results', [])
        logger.info(f"阶段5分镜结果数量: {len(storyboard_results) if storyboard_results else 0}")

        # 如果阶段5没有数据，尝试从阶段4获取
        if not storyboard_results:
            stage4_data = stage_data.get('4', {})
            storyboard_results = stage4_data.get('storyboard_results', [])
            logger.info(f"阶段4分镜结果数量: {len(storyboard_results) if storyboard_results else 0}")

        # 获取场景分割数据（阶段3）
        stage3_data = stage_data.get('3', {})
        scenes_analysis = stage3_data.get('scenes_analysis', '')
        scenes_data = []

        # 尝试从scenes_analysis中解析场景信息
        if scenes_analysis:
            # 简单解析场景分析文本，提取场景信息
            scenes_data = self._parse_scenes_from_analysis(scenes_analysis)

        logger.info(f"阶段3场景数据: {len(scenes_data) if scenes_data else 0} 个场景")

        if storyboard_results:
            logger.info("使用分镜数据进行解析")
            # 🔧 修改：传入预期镜头数量
            self.extract_voice_from_storyboard_results(storyboard_results, scenes_data, expected_shot_count)
        elif scenes_data:
            logger.info("使用场景数据进行解析")
            # 如果没有分镜数据，但有场景数据，从场景数据生成基础配音段落
            self.extract_voice_from_scenes_data(scenes_data)
        else:
            # 如果都没有数据，尝试从原始文本生成
            original_text = project_data.get('original_text', '')
            logger.info(f"使用原始文本进行解析，文本长度: {len(original_text) if original_text else 0}")
            if original_text:
                self.extract_voice_from_original_text(original_text)
            else:
                logger.warning("没有找到任何可用的分镜或文本数据")

        # 🔧 升级：使用智能同步检测替换简单数量检测
        actual_voice_count = len(self.voice_segments)
        logger.info(f"解析完成，共生成 {actual_voice_count} 个配音段落")

        # 启动智能同步检测（异步，不阻塞用户操作）
        self._trigger_intelligent_sync_check(project_data)

    def _trigger_intelligent_sync_check(self, project_data):
        """触发智能同步检测"""
        try:
            # 检查是否有足够的数据进行同步检测
            voice_generation_data = project_data.get('voice_generation', {})
            voice_segments = voice_generation_data.get('voice_segments', [])
            generated_audio = voice_generation_data.get('generated_audio', [])

            # 如果没有配音数据，跳过检测
            if not voice_segments and not generated_audio:
                logger.info("没有配音数据，跳过智能同步检测")
                return

            # 检查是否有图像数据
            image_generation_data = project_data.get('image_generation', {})
            storyboard_data = project_data.get('storyboard_data', [])

            if not image_generation_data and not storyboard_data:
                logger.info("没有图像数据，跳过智能同步检测")
                return

            # 延迟显示同步检测对话框，避免阻塞当前操作
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1000, lambda: self._show_intelligent_sync_dialog(project_data))

        except Exception as e:
            logger.error(f"触发智能同步检测失败: {e}")

    def _show_intelligent_sync_dialog(self, project_data):
        """显示智能同步检测对话框"""
        try:
            from src.gui.intelligent_sync_dialog import IntelligentSyncDialog

            dialog = IntelligentSyncDialog(
                parent=self,
                project_data=project_data,
                project_manager=self.project_manager
            )

            # 非模态显示，不阻塞用户操作
            dialog.show()

        except Exception as e:
            logger.error(f"显示智能同步检测对话框失败: {e}")
            # 降级处理：显示简单提示
            QMessageBox.information(
                self, "同步检测",
                "配音生成完成！\n\n"
                "建议检查配音与图像的同步状态，\n"
                "可使用图像生成界面的'按配音时间生成'功能。"
            )

    def _get_expected_shot_count(self, project_data):
        """获取预期的镜头数量（基于图像生成数据）"""
        try:
            expected_count = 0

            # 方法1：从shot_image_mappings获取
            shot_mappings = project_data.get('shot_image_mappings', {})
            if shot_mappings:
                expected_count = len(shot_mappings)
                logger.info(f"从shot_image_mappings获取镜头数量: {expected_count}")
                return expected_count

            # 方法2：从五阶段分镜数据计算
            five_stage_data = project_data.get('five_stage_storyboard', {})
            stage_data = five_stage_data.get('stage_data', {})

            # 尝试从阶段5获取
            stage5_data = stage_data.get('5', {})
            storyboard_results = stage5_data.get('storyboard_results', [])

            if not storyboard_results:
                # 尝试从阶段4获取
                stage4_data = stage_data.get('4', {})
                storyboard_results = stage4_data.get('storyboard_results', [])

            if storyboard_results:
                # 计算总镜头数
                for result in storyboard_results:
                    storyboard_script = result.get('storyboard_script', '')
                    shots = self._parse_storyboard_text(storyboard_script)
                    expected_count += len(shots)

                logger.info(f"从分镜脚本计算镜头数量: {expected_count}")
                return expected_count

            # 方法3：从真实场景文件计算
            if self.project_manager and self.project_manager.current_project:
                project_root = self.project_manager.current_project.get('project_dir') or self.project_manager.current_project.get('project_root')
                if project_root:
                    real_shots_data = self._load_real_storyboard_files()
                    if real_shots_data:
                        expected_count = sum(len(scene['shots']) for scene in real_shots_data)
                        logger.info(f"从真实场景文件计算镜头数量: {expected_count}")
                        return expected_count

            logger.warning("无法确定预期镜头数量，返回0")
            return 0

        except Exception as e:
            logger.error(f"获取预期镜头数量失败: {e}")
            return 0

    def _fix_voice_image_count_mismatch(self, expected_count, project_data):
        """修复配音段落与图像数量不匹配的问题"""
        try:
            current_count = len(self.voice_segments)
            logger.info(f"开始修复数量不匹配：当前{current_count}个，预期{expected_count}个")

            if current_count < expected_count:
                # 配音段落少于图像数量：需要增加配音段落
                self._expand_voice_segments(expected_count, project_data)
            elif current_count > expected_count:
                # 配音段落多于图像数量：需要合并或删除配音段落
                self._reduce_voice_segments(expected_count)

        except Exception as e:
            logger.error(f"修复数量不匹配失败: {e}")

    def _parse_scenes_from_analysis(self, scenes_analysis):
        """从场景分析文本中解析场景信息 - 简化版本，只解析场景标题"""
        scenes = []
        try:
            lines = scenes_analysis.split('\n')

            for line in lines:
                line = line.strip()
                # 检测场景标题
                if line.startswith('### 场景') or line.startswith('## 场景'):
                    scene_title = line.replace('#', '').strip()
                    scenes.append({
                        'title': scene_title,
                        'description': ''  # 保持兼容性，但不再填充详细描述
                    })

        except Exception as e:
            logger.error(f"解析场景分析失败: {e}")

        return scenes

    def extract_voice_from_storyboard_results(self, storyboard_results, scenes_data=None, expected_shot_count=None):
        """从分镜结果列表中提取配音内容 - 完全修复版本"""
        try:
            # 🔧 修复：读取真实的原始文本
            original_text_content = self._load_original_text()
            if not original_text_content:
                logger.warning("未找到原始文本内容")
                return

            # 🔧 修复：首先尝试从真实的场景文件读取镜头数据
            real_shots_data = self._load_real_storyboard_files()

            if real_shots_data:
                logger.info(f"从真实场景文件加载了 {len(real_shots_data)} 个场景的镜头数据")
                self._process_real_storyboard_data(real_shots_data, original_text_content)
            else:
                # 降级：使用project.json中的分镜数据
                logger.warning("未找到真实场景文件，使用project.json中的分镜数据")
                self._process_project_storyboard_data(storyboard_results, original_text_content)

            logger.info(f"配音内容提取完成，共生成 {len(self.voice_segments)} 个配音段落")

        except Exception as e:
            logger.error(f"解析分镜结果列表失败: {e}")
            import traceback
            traceback.print_exc()
            # 降级处理：尝试从第一个场景的脚本中提取
            if storyboard_results and len(storyboard_results) > 0:
                first_script = storyboard_results[0].get('storyboard_script', '')
                if first_script:
                    self._fallback_text_extraction(first_script)

    def _load_real_storyboard_files(self):
        """加载真实的场景文件数据"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return None

            project_root = self.project_manager.current_project.get('project_dir') or self.project_manager.current_project.get('project_root')
            if not project_root:
                return None

            storyboard_dir = os.path.join(project_root, 'storyboard')
            if not os.path.exists(storyboard_dir):
                logger.warning(f"分镜目录不存在: {storyboard_dir}")
                return None

            scenes_data = []

            # 查找所有场景文件
            scene_files = []
            for file in os.listdir(storyboard_dir):
                if file.startswith('scene_') and file.endswith('_storyboard.txt'):
                    scene_files.append(file)

            # 按场景编号排序
            scene_files.sort(key=lambda x: int(x.split('_')[1]))

            for scene_file in scene_files:
                scene_path = os.path.join(storyboard_dir, scene_file)
                scene_number = int(scene_file.split('_')[1])

                with open(scene_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 解析场景文件
                scene_data = self._parse_scene_file(content, scene_number)
                if scene_data:
                    scenes_data.append(scene_data)
                    logger.info(f"加载场景{scene_number}: {len(scene_data['shots'])} 个镜头")

            return scenes_data if scenes_data else None

        except Exception as e:
            logger.error(f"加载真实场景文件失败: {e}")
            return None

    def _parse_scene_file(self, content, scene_number):
        """解析单个场景文件"""
        try:
            lines = content.split('\n')
            scene_title = f"场景{scene_number}"
            shots = []
            current_shot = None

            for line in lines:
                line = line.strip()

                # 检测场景标题
                if line.startswith('# 场景'):
                    scene_title = line[2:].strip()

                # 检测镜头开始
                elif line.startswith('### 镜头'):
                    if current_shot:
                        shots.append(current_shot)

                    shot_number = line.replace('### 镜头', '').strip()
                    current_shot = {
                        'shot_number': shot_number,
                        '画面描述': '',
                        '台词/旁白': '',
                        '音效提示': ''
                    }

                # 解析镜头属性
                elif current_shot and line.startswith('- **') and '**：' in line:
                    key = line.split('**：')[0].replace('- **', '')
                    value = line.split('**：')[1].strip()
                    current_shot[key] = value

                    # 🔧 修复：特别处理镜头原文字段，用于AI配音
                    if key == '镜头原文':
                        current_shot['original_text'] = value

            # 添加最后一个镜头
            if current_shot:
                shots.append(current_shot)

            return {
                'scene_title': scene_title,
                'scene_number': scene_number,
                'shots': shots
            }

        except Exception as e:
            logger.error(f"解析场景文件失败: {e}")
            return None

    def _process_real_storyboard_data(self, scenes_data, original_text_content):
        """处理真实的场景文件数据 - 修复重复内容问题"""
        try:
            # 计算总镜头数
            total_shots = sum(len(scene['shots']) for scene in scenes_data)
            logger.info(f"总镜头数: {total_shots}")
            logger.info(f"原文长度: {len(original_text_content)} 字符")

            # 创建精确的文本分段
            text_segments = self._create_precise_text_segments(original_text_content, total_shots)

            # 🔧 新增：初始化ID管理器
            self.shot_id_manager = ShotIDManager()

            segment_index = 0
            # 🔧 修复：添加去重机制，防止重复内容
            processed_shots = set()

            for scene_idx, scene_data in enumerate(scenes_data):
                scene_title = scene_data['scene_title']
                shots = scene_data['shots']

                logger.info(f"{scene_title} 包含 {len(shots)} 个镜头")

                for shot_idx, shot in enumerate(shots):
                    shot_number = shot['shot_number']

                    # 🔧 修复：使用统一的ID格式
                    global_index = segment_index + 1
                    scene_id = f"scene_{scene_idx + 1}"
                    shot_id = f"shot_{shot_idx + 1}"
                    text_segment_id = f"text_segment_{global_index:03d}"

                    # 🔧 修复：创建唯一标识符防止重复
                    unique_shot_key = f"{scene_title}_{shot_number}"
                    if unique_shot_key in processed_shots:
                        logger.warning(f"跳过重复镜头: {unique_shot_key}")
                        continue
                    processed_shots.add(unique_shot_key)

                    # 🔧 修复：优先提取镜头原文字段
                    original_text_from_shot = shot.get('镜头原文', '') or shot.get('original_text', '')

                    # 提取画面描述
                    storyboard_description = shot.get('画面描述', '')

                    # 提取台词/旁白
                    dialogue_from_script = shot.get('台词/旁白', '')

                    # 🔧 修复：提取音效（优先使用专门的音效字段）
                    sound_effect = shot.get('音效提示', '')
                    if not sound_effect:
                        # 如果没有专门的音效字段，从画面描述中智能提取
                        sound_effect = self._extract_sound_effects(storyboard_description)

                    # 🔧 修复：配音内容优先级 - 优先使用镜头原文
                    voice_content = ''
                    content_type = ''
                    original_text_content = ''

                    if original_text_from_shot and original_text_from_shot != '无':
                        # 优先使用镜头原文作为旁白内容
                        voice_content = original_text_from_shot
                        original_text_content = original_text_from_shot
                        content_type = '旁白'
                    elif dialogue_from_script and dialogue_from_script != '无':
                        voice_content = dialogue_from_script
                        content_type = '台词'
                        # 如果没有镜头原文，尝试从文本分段中获取
                        if segment_index < len(text_segments):
                            matched_text_segment = text_segments[segment_index]
                            original_text_content = matched_text_segment.get('content', '')
                    else:
                        # 最后使用文本分段作为备选
                        if segment_index < len(text_segments):
                            matched_text_segment = text_segments[segment_index]
                            voice_content = matched_text_segment.get('content', '')
                            original_text_content = voice_content
                            content_type = '旁白'

                    if voice_content:  # 只有有配音内容的才添加
                        # 🔧 修复：使用统一的ID格式创建配音段落
                        voice_segment = {
                            'index': segment_index,
                            'scene_id': scene_id,  # 使用标准化的scene_id
                            'shot_id': text_segment_id,  # 使用text_segment_XXX格式
                            'original_text': original_text_content,
                            'storyboard_description': storyboard_description,
                            'dialogue_text': voice_content,
                            'content_type': content_type,
                            'sound_effect': sound_effect,
                            'status': '未生成',
                            'audio_path': '',
                            'selected': True
                        }

                        self.voice_segments.append(voice_segment)

                        # 🔧 新增：创建镜头映射
                        shot_mapping = ShotMapping(
                            global_index=global_index,
                            scene_id=scene_id,
                            shot_id=shot_id,
                            text_segment_id=text_segment_id,
                            unified_key=f"{scene_id}_{shot_id}",
                            original_text=original_text_content,
                            scene_index=shot_idx + 1
                        )
                        self.shot_id_manager.shot_mappings.append(shot_mapping)
                        self.shot_id_manager._update_conversion_cache(shot_mapping)

                        logger.info(f"{text_segment_id} ({scene_id}_{shot_id}) - {content_type}: {voice_content[:30]}...")
                        segment_index += 1
                    else:
                        logger.warning(f"{text_segment_id} 没有找到配音内容")

        except Exception as e:
            logger.error(f"处理真实场景数据失败: {e}")

    def _process_project_storyboard_data(self, storyboard_results, original_text_content):
        """处理project.json中的分镜数据（降级方案） - 修复重复内容问题"""
        try:
            # 按实际镜头数量创建文本分段
            total_shots = sum(len(self._parse_storyboard_text(result.get('storyboard_script', '')))
                            for result in storyboard_results)

            logger.info(f"开始处理 {len(storyboard_results)} 个场景的分镜脚本")
            logger.info(f"总镜头数: {total_shots}")
            logger.info(f"原文长度: {len(original_text_content)} 字符")

            # 创建精确的文本分段
            text_segments = self._create_precise_text_segments(original_text_content, total_shots)

            segment_index = 0
            # 🔧 修复：添加去重机制，防止重复内容
            processed_shots = set()

            for scene_idx, scene_result in enumerate(storyboard_results):
                scene_info = scene_result.get('scene_info', f'场景{scene_idx + 1}')
                storyboard_script = scene_result.get('storyboard_script', '')

                if storyboard_script:
                    logger.info(f"处理 {scene_info}，脚本长度: {len(storyboard_script)}")

                    # 解析单个场景的分镜脚本
                    shots_data = self._parse_storyboard_text(storyboard_script)
                    logger.info(f"{scene_info} 包含 {len(shots_data)} 个镜头")

                    # 为每个场景的镜头重新编号（从1开始）
                    scene_shot_index = 1

                    for shot in shots_data:
                        # 使用连续的镜头编号
                        shot_id = f'镜头{scene_shot_index}'

                        # 🔧 修复：创建唯一标识符防止重复
                        unique_shot_key = f"{scene_info}_{scene_shot_index}"
                        if unique_shot_key in processed_shots:
                            logger.warning(f"跳过重复镜头: {unique_shot_key}")
                            scene_shot_index += 1
                            continue
                        processed_shots.add(unique_shot_key)

                        # 提取画面描述
                        storyboard_description = (
                            shot.get('画面描述') or
                            shot.get('action') or
                            shot.get('description') or
                            shot.get('content') or
                            ''
                        )

                        # 提取台词/旁白（如果有的话）
                        dialogue_from_script = shot.get('台词/旁白', '') or shot.get('dialogue', '')

                        # 匹配对应的原文片段
                        matched_text_segment = None
                        if segment_index < len(text_segments):
                            matched_text_segment = text_segments[segment_index]

                        # 配音内容优先级
                        voice_content = ''
                        content_type = ''

                        if dialogue_from_script and dialogue_from_script != '无':
                            voice_content = dialogue_from_script
                            content_type = '台词'
                        elif matched_text_segment:
                            voice_content = matched_text_segment.get('content', '')
                            content_type = '旁白'

                        # 提取音效（从描述中智能识别）
                        sound_effect = self._extract_sound_effects(storyboard_description)

                        if voice_content:  # 只有有配音内容的才添加
                            self.voice_segments.append({
                                'index': segment_index,
                                'scene_id': scene_info,
                                'shot_id': shot_id,
                                'original_text': matched_text_segment.get('content', '') if matched_text_segment else '',
                                'storyboard_description': storyboard_description,
                                'dialogue_text': voice_content,
                                'content_type': content_type,
                                'sound_effect': sound_effect,
                                'status': '未生成',
                                'audio_path': '',
                                'selected': True
                            })

                            logger.info(f"{shot_id} - {content_type}: {voice_content[:30]}...")
                            segment_index += 1
                        else:
                            logger.warning(f"{shot_id} 没有找到配音内容")

                        scene_shot_index += 1

        except Exception as e:
            logger.error(f"处理project.json分镜数据失败: {e}")

    def extract_voice_text_from_storyboard(self, storyboard_text, scenes_data=None):
        """智能从分镜文本中提取配音内容"""
        try:
            # 解析分镜文本，支持多种格式
            shots_data = self._parse_storyboard_text(storyboard_text)

            # 如果有场景数据，用于映射场景信息
            scene_mapping = {}
            if scenes_data:
                for i, scene in enumerate(scenes_data):
                    scene_name = scene.get('scene_name', f'场景{i+1}')
                    scene_mapping[i] = scene_name

            segment_index = 0
            for shot in shots_data:
                # 提取场景信息
                scene_id = shot.get('scene', '未知场景')
                # 🔧 修复：使用更准确的场景映射逻辑，而不是固定的3个镜头估算
                if scene_mapping and segment_index < len(scene_mapping):
                    # 使用简单的线性映射，避免固定的镜头数量假设
                    scene_index = min(segment_index * len(scene_mapping) // len(shots_data), len(scene_mapping) - 1)
                    scene_id = scene_mapping[scene_index]

                # 提取镜头信息
                shot_id = shot.get('shot_id', f'镜头{segment_index + 1}')

                # 提取原文（画面描述或动作描述）
                original_text = shot.get('action', shot.get('description', ''))

                # 提取台词
                dialogue_text = shot.get('dialogue', '')

                # 如果没有明确的台词，尝试从原文中智能提取
                if not dialogue_text and original_text:
                    extracted_dialogue = self._extract_dialogue(original_text)
                    dialogue_text = extracted_dialogue if extracted_dialogue else original_text

                # 提取音效（从描述中智能识别）
                sound_effect = self._extract_sound_effects(original_text)

                if original_text or dialogue_text:  # 只有有内容的才添加
                    self.voice_segments.append({
                        'index': segment_index,
                        'scene_id': scene_id,
                        'shot_id': shot_id,
                        'original_text': original_text,
                        'dialogue_text': dialogue_text,
                        'sound_effect': sound_effect,
                        'status': '未生成',
                        'audio_path': '',
                        'selected': True
                    })
                    segment_index += 1

        except Exception as e:
            logger.error(f"解析分镜文本失败: {e}")
            # 降级处理：简单按行分割
            self._fallback_text_extraction(storyboard_text)

    def _parse_storyboard_text(self, storyboard_text):
        """解析分镜文本，支持多种格式"""
        shots_data = []

        # 尝试解析JSON格式
        try:
            import json
            data = json.loads(storyboard_text)
            if isinstance(data, dict) and 'shots' in data:
                return data['shots']
            elif isinstance(data, list):
                return data
        except:
            pass

        # 解析Markdown表格格式
        lines = storyboard_text.split('\n')
        current_shot = {}
        shot_id = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测镜头开始
            if line.startswith('### 镜头') or line.startswith('## 镜头') or '镜头' in line:
                if current_shot:
                    shots_data.append(current_shot)
                current_shot = {'shot_id': f'镜头{shot_id}'}
                shot_id += 1
                continue

            # 解析字段
            if '：' in line or ':' in line:
                separator = '：' if '：' in line else ':'
                parts = line.split(separator, 1)
                if len(parts) == 2:
                    field_name = parts[0].strip().replace('**', '').replace('-', '').replace('*', '')
                    field_value = parts[1].strip()

                    # 🔧 优化：更精确的字段映射，特别处理镜头原文
                    if '镜头原文' in field_name:
                        current_shot['original_text'] = field_value
                        current_shot['镜头原文'] = field_value  # 保留原始字段名
                    elif '画面描述' in field_name:
                        current_shot['action'] = field_value
                        current_shot['description'] = field_value  # 添加备用字段
                    elif '描述' in field_name and '画面' not in field_name:
                        # 避免与"画面描述"冲突
                        if 'action' not in current_shot:
                            current_shot['action'] = field_value
                            current_shot['description'] = field_value
                    elif '对话' in field_name or '台词' in field_name or '旁白' in field_name:
                        current_shot['dialogue'] = field_value
                    elif '场景' in field_name:
                        current_shot['scene'] = field_value
                    elif '角色' in field_name or '人物' in field_name or '镜头角色' in field_name:
                        current_shot['characters'] = field_value
                    elif '音效' in field_name:
                        current_shot['sound_effect'] = field_value
                    elif '时长' in field_name:
                        current_shot['duration'] = field_value
                    elif '镜头类型' in field_name:
                        current_shot['shot_type'] = field_value

                    # 🔧 调试：记录解析的字段
                    logger.debug(f"解析字段: {field_name} -> {field_value[:50]}...")

        # 添加最后一个镜头
        if current_shot:
            shots_data.append(current_shot)

        return shots_data

    def _extract_sound_effects(self, text):
        """从文本中智能提取音效 - 增强版本"""
        if not text:
            return ''

        # 🔧 修复：增强音效关键词映射，添加上下文判断
        sound_keywords = {
            # 自然环境音效
            '风': '风声', '雨': '雨声', '雷': '雷声', '海': '海浪声', '水': '流水声',
            '鸟': '鸟叫声', '虫': '虫鸣声', '狗': '狗叫声', '猫': '猫叫声',

            # 人为音效 - 增强电话相关
            '脚步': '脚步声', '敲门': '敲门声', '开门': '开门声', '关门': '关门声',
            '电话铃': '电话铃声', '电话响': '电话铃声', '铃声': '电话铃声',
            '挂断': '电话挂断声', '嘟嘟': '电话挂断声', '忙音': '电话挂断声',
            '汽车': '汽车声', '飞机': '飞机声', '火车': '火车声',

            # 动作音效
            '爆炸': '爆炸声', '枪': '枪声', '打击': '撞击声', '碰撞': '碰撞声',
            '破碎': '破碎声', '摔': '摔落声', '撕': '撕裂声',

            # 情感音效
            '哭': '哭声', '笑': '笑声', '叹': '叹息声', '呼吸': '呼吸声',

            # 背景音乐
            '音乐': '背景音乐', 'BGM': '背景音乐', '旋律': '背景音乐',
            '悲伤': '悲伤音乐', '欢快': '欢快音乐', '紧张': '紧张音乐'
        }

        # 🔧 新增：优先级音效判断
        priority_sound_patterns = {
            # 电话相关场景 - 高优先级
            r'电话.*?(炸|响|铃)': '电话铃声',
            r'(炸|响|铃).*?电话': '电话铃声',
            r'电话.*?挂断': '电话挂断声',
            r'挂断.*?电话': '电话挂断声',

            # 背景环境 - 中优先级
            r'(街道|马路|车流|城市)': '城市环境音',
            r'(办公室|会议|谈判)': '办公室环境音',
        }

        # 明确不需要音效的场景
        no_sound_patterns = [
            r'(大家好|我是|曾经|误入歧途|家伙)',  # 自我介绍
            r'(开价|许诺|股份|分红|豪车)',  # 商务谈话
            r'(一个月|二十万|十万)',  # 金钱数字
        ]

        detected_effects = []
        text_lower = text.lower()

        # 🔧 修复：先检查是否明确不需要音效
        import re
        for pattern in no_sound_patterns:
            if re.search(pattern, text):
                logger.debug(f"检测到不需要音效的场景: {pattern}")
                return ''

        # 🔧 修复：检查优先级音效
        priority_matched = False
        for pattern, effect_name in priority_sound_patterns.items():
            if re.search(pattern, text):
                priority_matched = True
                if effect_name and effect_name not in detected_effects:
                    detected_effects.append(effect_name)
                    logger.debug(f"优先级音效匹配: {pattern} -> {effect_name}")

        # 🔧 修复：如果没有优先级匹配，进行关键词匹配
        if not priority_matched:
            for keyword, effect_name in sound_keywords.items():
                if keyword in text or keyword.lower() in text_lower:
                    if effect_name not in detected_effects:
                        detected_effects.append(effect_name)

        # 🔧 新增：智能过滤不合适的音效
        filtered_effects = self._filter_inappropriate_effects(text, detected_effects)

        return ', '.join(filtered_effects) if filtered_effects else ''

    def _filter_inappropriate_effects(self, text, effects):
        """过滤不合适的音效 - 只进行基本过滤"""
        if not effects:
            return effects

        # 🔧 修复：简化过滤逻辑，只过滤明显不匹配的音效
        filtered = []
        for effect in effects:
            if self._is_effect_appropriate(text, effect):
                filtered.append(effect)
            else:
                logger.debug(f"过滤不合适的音效: {effect}")

        return filtered

    def _is_effect_appropriate(self, text, effect):
        """判断音效是否适合文本内容"""
        # 🔧 修复：放宽电话音效的判断条件
        if '电话' in effect:
            # 电话相关的关键词
            phone_keywords = ['电话', '铃', '响', '炸', '接', '打', '挂', '嘟']
            return any(keyword in text for keyword in phone_keywords)

        # 其他音效的通用判断
        return True

    def _create_smart_text_segments(self, original_text_content, storyboard_results):
        """创建智能文本分段，确保原文与镜头的合理对应"""
        if not original_text_content:
            return []

        try:
            # 计算总镜头数
            total_shots = sum(len(self._parse_storyboard_text(result.get('storyboard_script', '')))
                            for result in storyboard_results)

            # 按自然段落分割原文
            natural_paragraphs = [p.strip() for p in original_text_content.split('\n') if p.strip()]

            # 按句子进一步分割，创建更细粒度的文本片段
            text_segments = []
            segment_index = 0

            for para_idx, paragraph in enumerate(natural_paragraphs):
                # 按句号、感叹号、问号分割句子
                import re
                sentences = re.split(r'[。！？]', paragraph)
                sentences = [s.strip() for s in sentences if s.strip()]

                if not sentences:
                    continue

                # 如果句子太少，保持段落完整
                if len(sentences) <= 2:
                    text_segments.append({
                        'index': segment_index,
                        'paragraph_index': para_idx,
                        'content': paragraph,
                        'type': 'paragraph',
                        'sentence_count': len(sentences)
                    })
                    segment_index += 1
                else:
                    # 将长段落分割为多个片段
                    # 计算每个片段应包含的句子数
                    sentences_per_segment = max(1, len(sentences) // min(3, len(sentences)))

                    for i in range(0, len(sentences), sentences_per_segment):
                        segment_sentences = sentences[i:i + sentences_per_segment]
                        segment_content = ''.join(s + '。' for s in segment_sentences).rstrip('。')

                        if segment_content:
                            text_segments.append({
                                'index': segment_index,
                                'paragraph_index': para_idx,
                                'content': segment_content,
                                'type': 'sentence_group',
                                'sentence_count': len(segment_sentences),
                                'sentence_range': (i, i + len(segment_sentences))
                            })
                            segment_index += 1

            # 如果文本片段数量仍然少于镜头数量，进行进一步细分
            if len(text_segments) < total_shots and total_shots > 0:
                expanded_segments = []
                expansion_factor = max(1, total_shots // len(text_segments))

                for segment in text_segments:
                    content = segment['content']
                    # 尝试按逗号、分号进一步分割
                    sub_parts = re.split(r'[，；]', content)
                    sub_parts = [p.strip() for p in sub_parts if p.strip()]

                    if len(sub_parts) > 1 and expansion_factor > 1:
                        for i, part in enumerate(sub_parts):
                            expanded_segments.append({
                                'index': len(expanded_segments),
                                'paragraph_index': segment['paragraph_index'],
                                'content': part,
                                'type': 'sub_sentence',
                                'parent_segment': segment['index'],
                                'sub_index': i
                            })
                    else:
                        segment['index'] = len(expanded_segments)
                        expanded_segments.append(segment)

                text_segments = expanded_segments

            logger.info(f"智能文本分段完成: {len(natural_paragraphs)}个段落 -> {len(text_segments)}个文本片段")
            logger.info(f"总镜头数: {total_shots}, 文本片段数: {len(text_segments)}")

            return text_segments

        except Exception as e:
            logger.error(f"创建智能文本分段失败: {e}")
            # 降级处理：简单按段落分割
            paragraphs = [p.strip() for p in original_text_content.split('\n') if p.strip()]
            return [{'index': i, 'content': p, 'type': 'paragraph'} for i, p in enumerate(paragraphs)]

    def _create_precise_text_segments(self, original_text_content, total_shots):
        """创建精确的文本分段，根据实际镜头数量进行分段"""
        if not original_text_content:
            return []

        try:
            logger.info(f"创建文本分段: 总镜头数={total_shots}, 原文长度={len(original_text_content)}")

            if total_shots <= 1:
                # 单镜头：整个文本作为一段
                return [{'index': 0, 'content': original_text_content, 'type': 'full_text'}]

            # 🔧 修复：按句子分段，然后平均分配给镜头
            sentences = self._split_into_sentences(original_text_content)
            logger.info(f"原文分解为 {len(sentences)} 个句子")

            if len(sentences) <= total_shots:
                # 句子数少于或等于镜头数：每句一段，不足的用空段补充
                segments = []
                for i in range(total_shots):
                    if i < len(sentences):
                        segments.append({
                            'index': i,
                            'content': sentences[i],
                            'type': 'sentence'
                        })
                    else:
                        segments.append({
                            'index': i,
                            'content': '',
                            'type': 'empty'
                        })
                return segments
            else:
                # 句子数多于镜头数：平均分配句子到镜头
                segments = []
                sentences_per_shot = len(sentences) // total_shots
                remainder = len(sentences) % total_shots

                start_idx = 0
                for i in range(total_shots):
                    # 计算当前镜头应该分配的句子数
                    current_shot_sentences = sentences_per_shot + (1 if i < remainder else 0)
                    end_idx = start_idx + current_shot_sentences

                    # 合并句子
                    segment_content = ''.join(sentences[start_idx:end_idx])
                    segments.append({
                        'index': i,
                        'content': segment_content,
                        'type': 'merged_sentences',
                        'sentence_count': current_shot_sentences,
                        'sentence_range': (start_idx, end_idx)
                    })

                    start_idx = end_idx

                return segments

        except Exception as e:
            logger.error(f"精确文本分段失败: {e}")
            # 降级：简单平均分段
            text_length = len(original_text_content)
            segment_length = text_length // total_shots

            segments = []
            for i in range(total_shots):
                start = i * segment_length
                end = start + segment_length if i < total_shots - 1 else text_length
                segments.append({
                    'index': i,
                    'content': original_text_content[start:end],
                    'type': 'character_split'
                })

            return segments

    def _split_into_sentences(self, text):
        """将文本分割为句子"""
        if not text:
            return []

        import re

        # 中文句子分割符
        sentence_endings = r'[。！？；\n]'

        # 分割句子
        sentences = re.split(sentence_endings, text)

        # 清理空句子和过短的句子
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 3:  # 过滤太短的句子
                cleaned_sentences.append(sentence)

        return cleaned_sentences

    def _match_text_segment(self, shot_index, text_segments, storyboard_description=None, scene_index=None):
        """将镜头与文本片段进行智能匹配"""
        if not text_segments:
            return None

        try:
            total_segments = len(text_segments)

            # 🔧 策略1：均匀分布匹配
            if shot_index < total_segments:
                # 直接对应
                matched_segment = text_segments[shot_index]
                logger.debug(f"直接匹配: 镜头{shot_index + 1} -> 文本片段{matched_segment['index'] + 1}")
                return matched_segment
            else:
                # 循环匹配或比例匹配
                segment_index = shot_index % total_segments
                matched_segment = text_segments[segment_index]
                logger.debug(f"循环匹配: 镜头{shot_index + 1} -> 文本片段{matched_segment['index'] + 1}")
                return matched_segment

        except Exception as e:
            logger.error(f"文本片段匹配失败: {e}")
            # 降级处理：返回第一个片段
            return text_segments[0] if text_segments else None

    def _load_original_text(self):
        """加载原始文本内容"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return None

            project_root = self.project_manager.current_project.get('project_dir') or self.project_manager.current_project.get('project_root')
            if not project_root:
                return None

            # 尝试从rewritten_text.txt加载
            rewritten_text_path = os.path.join(project_root, 'texts', 'rewritten_text.txt')
            if os.path.exists(rewritten_text_path):
                with open(rewritten_text_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    logger.info(f"成功加载改写文本，长度: {len(content)}")
                    return content

            # 如果没有改写文本，尝试从项目数据中获取原始文本
            project_data = self.project_manager.get_project_data()
            if project_data:
                original_text = project_data.get('original_text', '') or project_data.get('rewritten_text', '')
                if original_text:
                    logger.info(f"从项目数据加载原始文本，长度: {len(original_text)}")
                    return original_text

            logger.warning("未找到原始文本内容")
            return None

        except Exception as e:
            logger.error(f"加载原始文本失败: {e}")
            return None

    def _match_original_text(self, storyboard_description, original_text_content, segment_index):
        """智能匹配原始文本内容 - 优化版本"""
        if not original_text_content or not storyboard_description:
            return None

        try:
            # 将原始文本按段落分割
            paragraphs = [p.strip() for p in original_text_content.split('\n') if p.strip()]
            total_paragraphs = len(paragraphs)

            logger.debug(f"原文共{total_paragraphs}个段落，当前处理镜头{segment_index + 1}")

            # 🔧 优化1：智能段落映射策略
            # 根据镜头总数和段落总数的比例，智能分配段落
            if hasattr(self, 'voice_segments') and self.voice_segments:
                total_segments = len(self.voice_segments)

                # 计算段落到镜头的映射比例
                if total_segments <= total_paragraphs:
                    # 镜头数少于或等于段落数：直接映射或合并段落
                    paragraph_index = min(segment_index, total_paragraphs - 1)
                    matched_paragraph = paragraphs[paragraph_index]
                    logger.debug(f"直接映射：镜头{segment_index + 1} -> 段落{paragraph_index + 1}")
                    return matched_paragraph
                else:
                    # 镜头数多于段落数：需要智能分配
                    # 计算每个段落应该对应多少个镜头
                    segments_per_paragraph = total_segments / total_paragraphs
                    paragraph_index = min(int(segment_index / segments_per_paragraph), total_paragraphs - 1)
                    matched_paragraph = paragraphs[paragraph_index]
                    logger.debug(f"智能分配：镜头{segment_index + 1} -> 段落{paragraph_index + 1} (比例: {segments_per_paragraph:.2f})")
                    return matched_paragraph

            # 🔧 优化2：语义相似度匹配
            # 如果简单映射失败，使用语义匹配
            best_match = None
            best_score = 0

            # 提取分镜描述中的关键信息
            import re

            # 提取中文关键词（2个字符以上）
            chinese_keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', storyboard_description)

            # 提取动作词汇
            action_patterns = [
                r'(拖着|背着|坐|站|走|看|说|买|吃|喝)',
                r'(火车|车站|行李|背包|票|钱|水|麻花)',
                r'(焦虑|担心|饿|渴|疲惫|希望)'
            ]

            action_keywords = []
            for pattern in action_patterns:
                action_keywords.extend(re.findall(pattern, storyboard_description))

            all_keywords = chinese_keywords + action_keywords

            if all_keywords:
                for i, paragraph in enumerate(paragraphs):
                    # 计算关键词匹配分数
                    keyword_score = sum(1 for keyword in all_keywords if keyword in paragraph)

                    # 计算长度相似度分数（避免过短或过长的段落）
                    length_score = 1.0 / (1.0 + abs(len(paragraph) - len(storyboard_description)) / 100.0)

                    # 综合分数
                    total_score = keyword_score * 2 + length_score

                    if total_score > best_score:
                        best_score = total_score
                        best_match = paragraph
                        logger.debug(f"段落{i + 1}匹配分数: {total_score:.2f} (关键词:{keyword_score}, 长度:{length_score:.2f})")

                if best_match and best_score > 0.5:  # 设置最低匹配阈值
                    logger.debug(f"语义匹配成功，最佳分数: {best_score:.2f}")
                    return best_match

            # 🔧 优化3：位置回退策略
            # 如果所有匹配都失败，根据位置选择最合适的段落
            if segment_index < total_paragraphs:
                fallback_paragraph = paragraphs[segment_index]
                logger.debug(f"使用位置回退策略：镜头{segment_index + 1} -> 段落{segment_index + 1}")
                return fallback_paragraph
            else:
                # 如果镜头索引超出段落范围，选择最后一个段落
                fallback_paragraph = paragraphs[-1]
                logger.debug(f"使用最后段落作为回退：镜头{segment_index + 1} -> 段落{total_paragraphs}")
                return fallback_paragraph

        except Exception as e:
            logger.error(f"智能匹配原始文本失败: {e}")
            return None

    def _extract_dialogue(self, text):
        """智能提取台词"""
        if not text:
            return ''

        # 台词标识符
        dialogue_patterns = [
            r'"([^"]+)"',  # 双引号
            r'"([^"]+)"',  # 中文双引号
            r"'([^']+)'",  # 中文单引号
            r'说[：:]"?([^"。！？]+)[。！？"]?',  # "说："后的内容
            r'道[：:]"?([^"。！？]+)[。！？"]?',  # "道："后的内容
            r'喊[：:]"?([^"。！？]+)[。！？"]?',  # "喊："后的内容
            r'叫[：:]"?([^"。！？]+)[。！？"]?',  # "叫："后的内容
        ]

        import re
        dialogues = []

        for pattern in dialogue_patterns:
            matches = re.findall(pattern, text)
            dialogues.extend(matches)

        # 去重并过滤太短的台词
        unique_dialogues = []
        for dialogue in dialogues:
            dialogue = dialogue.strip()
            if len(dialogue) > 2 and dialogue not in unique_dialogues:
                unique_dialogues.append(dialogue)

        return ' | '.join(unique_dialogues) if unique_dialogues else ''

    def _fallback_text_extraction(self, storyboard_text):
        """降级文本提取方法"""
        lines = storyboard_text.split('\n')
        segment_index = 0
        current_scene = 1
        current_shot = 1

        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 10:
                # 检测场景分割
                if '场景' in line or 'Scene' in line:
                    current_scene += 1
                    current_shot = 1

                self.voice_segments.append({
                    'index': segment_index,
                    'scene_id': f"场景{current_scene}",
                    'shot_id': f"镜头{current_shot}",
                    'original_text': line,
                    'dialogue_text': '',
                    'sound_effect': self._extract_sound_effects(line),
                    'status': '未生成',
                    'audio_path': '',
                    'selected': True
                })
                segment_index += 1
                current_shot += 1

    def extract_voice_from_scenes_data(self, scenes_data):
        """从场景数据中提取配音内容"""
        segment_index = 0

        for scene_idx, scene in enumerate(scenes_data):
            scene_name = scene.get('scene_name', f'场景{scene_idx + 1}')
            scene_description = scene.get('description', scene.get('content', ''))

            if scene_description:
                self.voice_segments.append({
                    'index': segment_index,
                    'scene_id': scene_name,
                    'shot_id': f'镜头1',
                    'original_text': scene_description,
                    'dialogue_text': scene_description,
                    'sound_effect': self._extract_sound_effects(scene_description),
                    'status': '未生成',
                    'audio_path': '',
                    'selected': True
                })
                segment_index += 1

    def extract_voice_from_original_text(self, original_text):
        """从原始文本中提取配音内容"""
        # 按段落分割
        paragraphs = [p.strip() for p in original_text.split('\n\n') if p.strip() and len(p.strip()) > 20]

        for idx, paragraph in enumerate(paragraphs):
            self.voice_segments.append({
                'index': idx,
                'scene_id': f'场景{(idx // 3) + 1}',  # 每3段为一个场景
                'shot_id': f'镜头{(idx % 3) + 1}',
                'original_text': paragraph,
                'dialogue_text': paragraph,
                'sound_effect': self._extract_sound_effects(paragraph),
                'status': '未生成',
                'audio_path': '',
                'selected': True
            })

    def update_text_table(self):
        """更新文本表格"""
        self.text_table.setRowCount(len(self.voice_segments))

        for i, segment in enumerate(self.voice_segments):
            # 选择复选框
            checkbox = QCheckBox()
            checkbox.setChecked(segment.get('selected', True))
            self.text_table.setCellWidget(i, 0, checkbox)

            # 🔧 旁白 - 可编辑（原文内容）
            original_text = segment.get('original_text', segment.get('text', ''))
            original_item = QTableWidgetItem(original_text)
            original_item.setToolTip(original_text)
            # 设置为可编辑
            original_item.setFlags(original_item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.text_table.setItem(i, 1, original_item)

            # 🔧 台词 - 可编辑，显示完整台词内容
            dialogue_text = segment.get('dialogue_text', '') if segment.get('content_type') == '台词' else ''
            dialogue_item = QTableWidgetItem(dialogue_text)
            dialogue_item.setToolTip(dialogue_text if dialogue_text else "双击编辑台词内容")
            # 设置为可编辑
            dialogue_item.setFlags(dialogue_item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.text_table.setItem(i, 2, dialogue_item)

            # 🔧 音效 - 可编辑
            sound_effect = segment.get('sound_effect', '')
            sound_effect_item = QTableWidgetItem(sound_effect)
            sound_effect_item.setToolTip(sound_effect if sound_effect else "双击编辑音效描述")
            # 设置为可编辑
            sound_effect_item.setFlags(sound_effect_item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.text_table.setItem(i, 3, sound_effect_item)

            # 状态
            status_item = QTableWidgetItem(segment.get('status', '未生成'))
            self.text_table.setItem(i, 4, status_item)

            # 操作按钮 - 改为竖排布局
            btn_widget = QWidget()
            btn_layout = QVBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(2)

            # 根据状态显示不同按钮
            status = segment.get('status', '未生成')
            audio_path = segment.get('audio_path', '')
            sound_effect_path = segment.get('sound_effect_path', '')

            # 🔧 修复：更严格的文件存在检查
            has_voice_audio = bool(audio_path and audio_path.strip() and os.path.exists(audio_path))
            has_sound_effect = bool(sound_effect_path and sound_effect_path.strip() and os.path.exists(sound_effect_path))

            # 🔧 调试信息
            logger.debug(f"镜头{i+1} 状态检查: audio_path='{audio_path}', sound_effect_path='{sound_effect_path}', has_voice={has_voice_audio}, has_effect={has_sound_effect}")

            if has_voice_audio:
                # 试听配音按钮
                play_voice_btn = QPushButton("🎵 试听配音")
                play_voice_btn.setToolTip("试听配音")
                play_voice_btn.setMinimumWidth(80)
                play_voice_btn.setMinimumHeight(32)
                play_voice_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #27ae60;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #2ecc71;
                    }
                    QPushButton:pressed {
                        background-color: #229954;
                    }
                """)
                # 🔧 修复：传递场景和镜头信息而不是简单的行索引
                segment = self.voice_segments[i]
                scene_id = segment.get('scene_id', '')
                shot_id = segment.get('shot_id', '')
                play_voice_btn.clicked.connect(lambda _, s_id=scene_id, sh_id=shot_id, idx=i: self.play_segment_audio_with_fallback(s_id, sh_id, idx))
                btn_layout.addWidget(play_voice_btn)
            else:
                # 生成配音按钮
                voice_btn = QPushButton("🎤 生成配音")
                voice_btn.setToolTip("生成配音")
                voice_btn.setMinimumWidth(80)
                voice_btn.setMinimumHeight(32)
                voice_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3498db;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #5dade2;
                    }
                    QPushButton:pressed {
                        background-color: #2980b9;
                    }
                """)
                voice_btn.clicked.connect(lambda _, idx=i: self.generate_single_voice(idx))
                btn_layout.addWidget(voice_btn)

            # 音效相关按钮
            if has_sound_effect:
                # 试听音效按钮
                play_effect_btn = QPushButton("🔉 试听音效")
                play_effect_btn.setToolTip("试听音效")
                play_effect_btn.setMinimumWidth(80)
                play_effect_btn.setMinimumHeight(32)
                play_effect_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e67e22;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #f39c12;
                    }
                    QPushButton:pressed {
                        background-color: #d35400;
                    }
                """)
                # 🔧 修复：传递场景和镜头信息而不是简单的行索引
                segment = self.voice_segments[i]
                scene_id = segment.get('scene_id', '')
                shot_id = segment.get('shot_id', '')
                play_effect_btn.clicked.connect(lambda _, s_id=scene_id, sh_id=shot_id, idx=i: self.play_segment_sound_effect_with_fallback(s_id, sh_id, idx))
                btn_layout.addWidget(play_effect_btn)
            else:
                # 生成音效按钮
                effect_btn = QPushButton("🔊 生成音效")
                effect_btn.setToolTip("生成音效")
                effect_btn.setMinimumWidth(80)
                effect_btn.setMinimumHeight(32)
                effect_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #9b59b6;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #af7ac5;
                    }
                    QPushButton:pressed {
                        background-color: #8e44ad;
                    }
                """)
                effect_btn.clicked.connect(lambda _, idx=i: self.generate_sound_effect(idx))
                btn_layout.addWidget(effect_btn)

            self.text_table.setCellWidget(i, 5, btn_widget)

        # 🔧 新增：恢复配音和音效状态
        self.restore_audio_states()

    def restore_audio_states(self):
        """恢复配音和音效状态"""
        try:
            logger.info("开始恢复配音和音效状态...")

            # 确保音频文件管理器已初始化
            if not self.audio_file_manager:
                self._ensure_audio_file_manager()

            if not self.audio_file_manager:
                logger.warning("音频文件管理器未初始化，跳过状态恢复")
                return

            restored_voice_count = 0
            restored_effect_count = 0

            for i, segment in enumerate(self.voice_segments):
                # 恢复配音状态
                voice_restored = self._restore_voice_state(segment, i)
                if voice_restored:
                    restored_voice_count += 1

                # 恢复音效状态
                effect_restored = self._restore_sound_effect_state(segment, i)
                if effect_restored:
                    restored_effect_count += 1

                # 🔧 修复：恢复状态后更新按钮
                self._update_row_buttons(i)

            logger.info(f"状态恢复完成: 配音 {restored_voice_count} 个, 音效 {restored_effect_count} 个")

        except Exception as e:
            logger.error(f"恢复配音和音效状态失败: {e}")

    def _restore_voice_state(self, segment, segment_index):
        """恢复单个段落的配音状态"""
        try:
            shot_id = segment.get('shot_id', f'镜头{segment_index + 1}')

            # 检查项目数据中是否有保存的音频路径
            if segment.get('audio_path'):
                audio_path = segment['audio_path']
                if os.path.exists(audio_path):
                    segment['status'] = '已生成'
                    # 更新表格状态
                    status_item = QTableWidgetItem('已生成')
                    self.text_table.setItem(segment_index, 4, status_item)
                    logger.debug(f"恢复配音状态: {shot_id} -> {audio_path}")
                    return True
                else:
                    # 文件不存在，清除路径
                    segment['audio_path'] = ''
                    segment['status'] = '未生成'

            # 如果项目数据中没有路径，尝试从文件系统查找
            audio_files = self._find_audio_files_for_segment(segment, segment_index)
            if audio_files:
                # 使用找到的第一个音频文件
                audio_path = audio_files[0]
                segment['audio_path'] = audio_path
                segment['status'] = '已生成'
                # 更新表格状态
                status_item = QTableWidgetItem('已生成')
                self.text_table.setItem(segment_index, 4, status_item)
                logger.info(f"从文件系统恢复配音状态: {shot_id} -> {audio_path}")
                return True

            return False

        except Exception as e:
            logger.error(f"恢复配音状态失败: {e}")
            return False

    def _restore_sound_effect_state(self, segment, segment_index):
        """恢复单个段落的音效状态"""
        try:
            shot_id = segment.get('shot_id', f'镜头{segment_index + 1}')

            # 检查项目数据中是否有保存的音效路径
            if segment.get('sound_effect_path'):
                sound_effect_path = segment['sound_effect_path']
                if os.path.exists(sound_effect_path):
                    logger.debug(f"恢复音效状态: {shot_id} -> {sound_effect_path}")
                    return True
                else:
                    # 文件不存在，清除路径
                    segment['sound_effect_path'] = ''

            # 如果项目数据中没有路径，尝试从文件系统查找
            sound_effect_files = self._find_sound_effect_files_for_segment(segment, segment_index)
            if sound_effect_files:
                # 使用找到的第一个音效文件
                sound_effect_path = sound_effect_files[0]
                segment['sound_effect_path'] = sound_effect_path
                logger.info(f"从文件系统恢复音效状态: {shot_id} -> {sound_effect_path}")
                return True

            return False

        except Exception as e:
            logger.error(f"恢复音效状态失败: {e}")
            return False

    def _find_audio_files_for_segment(self, segment, segment_index):
        """为段落查找音频文件"""
        try:
            shot_id = segment.get('shot_id', f'镜头{segment_index + 1}')
            audio_files = []

            # 遍历所有引擎目录
            engines = ['edge_tts', 'cosyvoice', 'ttsmaker', 'xunfei', 'elevenlabs']
            for engine in engines:
                if self.audio_file_manager:
                    engine_dir = self.audio_file_manager.get_engine_audio_dir(engine)
                    if engine_dir.exists():
                        # 查找包含镜头ID的音频文件
                        for audio_file in engine_dir.glob("*.mp3"):
                            if shot_id in audio_file.name or f"segment_{segment_index+1:03d}" in audio_file.name:
                                audio_files.append(str(audio_file))

            return audio_files

        except Exception as e:
            logger.error(f"查找音频文件失败: {e}")
            return []

    def _find_sound_effect_files_for_segment(self, segment, segment_index):
        """为段落查找音效文件"""
        try:
            shot_id = segment.get('shot_id', f'镜头{segment_index + 1}')
            sound_effect_files = []

            # 查找音效目录
            if self.audio_file_manager:
                sound_effects_dir = self.audio_file_manager.audio_root / "sound_effects"
                if sound_effects_dir.exists():
                    # 查找包含镜头ID的音效文件
                    for effect_file in sound_effects_dir.glob("*"):
                        if effect_file.is_file() and (shot_id in effect_file.name or f"segment_{segment_index+1:03d}" in effect_file.name):
                            # 只接受音频文件，跳过txt等占位文件
                            if effect_file.suffix.lower() in ['.mp3', '.wav', '.m4a', '.aac']:
                                sound_effect_files.append(str(effect_file))

            return sound_effect_files

        except Exception as e:
            logger.error(f"查找音效文件失败: {e}")
            return []

    def _update_row_buttons(self, row_index):
        """更新指定行的操作按钮"""
        try:
            if 0 <= row_index < len(self.voice_segments):
                segment = self.voice_segments[row_index]

                # 创建新的按钮组件
                btn_widget = QWidget()
                btn_layout = QVBoxLayout(btn_widget)
                btn_layout.setContentsMargins(2, 2, 2, 2)
                btn_layout.setSpacing(2)

                # 根据状态显示不同按钮
                audio_path = segment.get('audio_path', '')
                sound_effect_path = segment.get('sound_effect_path', '')

                # 🔧 修复：更严格的文件存在检查
                has_voice_audio = bool(audio_path and audio_path.strip() and os.path.exists(audio_path))
                has_sound_effect = bool(sound_effect_path and sound_effect_path.strip() and os.path.exists(sound_effect_path))

                # 🔧 调试信息
                logger.debug(f"更新镜头{row_index+1} 按钮: audio_path='{audio_path}', sound_effect_path='{sound_effect_path}', has_voice={has_voice_audio}, has_effect={has_sound_effect}")

                if has_voice_audio:
                    # 试听配音按钮
                    play_voice_btn = QPushButton("🎵 试听配音")
                    play_voice_btn.setToolTip("试听配音")
                    play_voice_btn.setMinimumWidth(80)
                    play_voice_btn.setMinimumHeight(32)
                    play_voice_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #27ae60;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            font-weight: bold;
                            font-size: 12px;
                        }
                        QPushButton:hover {
                            background-color: #2ecc71;
                        }
                        QPushButton:pressed {
                            background-color: #229954;
                        }
                    """)
                    # 🔧 修复：传递场景和镜头信息而不是简单的行索引
                    segment = self.voice_segments[row_index]
                    scene_id = segment.get('scene_id', '')
                    shot_id = segment.get('shot_id', '')
                    play_voice_btn.clicked.connect(lambda _, s_id=scene_id, sh_id=shot_id, idx=row_index: self.play_segment_audio_with_fallback(s_id, sh_id, idx))
                    btn_layout.addWidget(play_voice_btn)
                else:
                    # 生成配音按钮
                    voice_btn = QPushButton("🎤 生成配音")
                    voice_btn.setToolTip("生成配音")
                    voice_btn.setMinimumWidth(80)
                    voice_btn.setMinimumHeight(32)
                    voice_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #3498db;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            font-weight: bold;
                            font-size: 12px;
                        }
                        QPushButton:hover {
                            background-color: #5dade2;
                        }
                        QPushButton:pressed {
                            background-color: #2980b9;
                        }
                    """)
                    voice_btn.clicked.connect(lambda _, idx=row_index: self.generate_single_voice(idx))
                    btn_layout.addWidget(voice_btn)

                # 音效相关按钮
                if has_sound_effect:
                    # 试听音效按钮
                    play_effect_btn = QPushButton("🔉 试听音效")
                    play_effect_btn.setToolTip("试听音效")
                    play_effect_btn.setMinimumWidth(80)
                    play_effect_btn.setMinimumHeight(32)
                    play_effect_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #e67e22;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            font-weight: bold;
                            font-size: 12px;
                        }
                        QPushButton:hover {
                            background-color: #f39c12;
                        }
                        QPushButton:pressed {
                            background-color: #d35400;
                        }
                    """)
                    # 🔧 修复：传递场景和镜头信息而不是简单的行索引
                    segment = self.voice_segments[row_index]
                    scene_id = segment.get('scene_id', '')
                    shot_id = segment.get('shot_id', '')
                    play_effect_btn.clicked.connect(lambda _, s_id=scene_id, sh_id=shot_id, idx=row_index: self.play_segment_sound_effect_with_fallback(s_id, sh_id, idx))
                    btn_layout.addWidget(play_effect_btn)
                else:
                    # 生成音效按钮
                    effect_btn = QPushButton("🔊 生成音效")
                    effect_btn.setToolTip("生成音效")
                    effect_btn.setMinimumWidth(80)
                    effect_btn.setMinimumHeight(32)
                    effect_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #9b59b6;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            font-weight: bold;
                            font-size: 12px;
                        }
                        QPushButton:hover {
                            background-color: #af7ac5;
                        }
                        QPushButton:pressed {
                            background-color: #8e44ad;
                        }
                    """)
                    effect_btn.clicked.connect(lambda _, idx=row_index: self.generate_sound_effect(idx))
                    btn_layout.addWidget(effect_btn)

                # 更新表格中的按钮组件
                self.text_table.setCellWidget(row_index, 5, btn_widget)

        except Exception as e:
            logger.error(f"更新行按钮失败: {e}")
    
    def on_engine_changed(self):
        """引擎改变时更新音色列表"""
        try:
            engine_id = self.engine_combo.currentData()
            if engine_id:
                engine = self.engine_manager.get_engine(engine_id)
                if engine:
                    voices = engine.get_available_voices()
                    self.voice_combo.clear()
                    for voice in voices:
                        self.voice_combo.addItem(voice['name'], voice['id'])
        except Exception as e:
            logger.error(f"更新音色列表失败: {e}")

    def on_text_selection_changed(self):
        """文本选择改变时更新预览"""
        try:
            current_row = self.text_table.currentRow()
            if 0 <= current_row < len(self.voice_segments):
                segment = self.voice_segments[current_row]
                # 🔧 修复：优先显示原文（旁白）内容，而不是台词
                preview_text = segment.get('original_text', segment.get('dialogue_text', segment.get('text', '')))
                self.preview_text.setPlainText(preview_text)

                # 检查是否有对应的音频文件
                if segment.get('audio_path') and os.path.exists(segment['audio_path']):
                    self.play_audio_btn.setEnabled(True)
                else:
                    self.play_audio_btn.setEnabled(False)
        except Exception as e:
            logger.error(f"更新预览失败: {e}")

    def select_all_rows(self):
        """全选所有行"""
        try:
            for i in range(self.text_table.rowCount()):
                checkbox = self.text_table.cellWidget(i, 0)
                if checkbox and isinstance(checkbox, QCheckBox):
                    checkbox.setChecked(True)
            logger.info("已全选所有配音行")
        except Exception as e:
            logger.error(f"全选失败: {e}")

    def deselect_all_rows(self):
        """取消全选所有行"""
        try:
            for i in range(self.text_table.rowCount()):
                checkbox = self.text_table.cellWidget(i, 0)
                if checkbox and isinstance(checkbox, QCheckBox):
                    checkbox.setChecked(False)
            logger.info("已取消全选所有配音行")
        except Exception as e:
            logger.error(f"取消全选失败: {e}")

    def test_voice(self):
        """测试配音"""
        try:
            text = self.preview_text.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, "警告", "请先选择要测试的文本")
                return

            engine_id = self.engine_combo.currentData()
            if not engine_id:
                QMessageBox.warning(self, "警告", "请选择配音引擎")
                return

            # 获取配音设置
            settings = self.get_current_voice_settings()

            # 生成测试音频
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name

            # 启动生成线程
            self.test_thread = VoiceGenerationThread(
                self.engine_manager, engine_id,
                [{'text': text, 'shot_id': 'test'}],
                os.path.dirname(temp_path), settings
            )
            self.test_thread.voice_generated.connect(self.on_test_voice_generated)
            self.test_thread.error_occurred.connect(self.on_test_voice_error)
            self.test_thread.start()

            self.test_voice_btn.setEnabled(False)
            self.test_voice_btn.setText("生成中...")

        except Exception as e:
            logger.error(f"测试配音失败: {e}")
            QMessageBox.critical(self, "错误", f"测试失败: {e}")

    def on_test_voice_generated(self, result):
        """测试配音生成完成"""
        self.test_voice_btn.setEnabled(True)
        self.test_voice_btn.setText("🎵 测试配音")

        if result.get('status') == 'success':
            # 播放测试音频
            audio_path = result.get('audio_path')
            if audio_path and os.path.exists(audio_path):
                self.play_audio_file(audio_path)

    def on_test_voice_error(self, error_msg):
        """测试配音生成失败"""
        self.test_voice_btn.setEnabled(True)
        self.test_voice_btn.setText("🎵 测试配音")
        QMessageBox.warning(self, "测试失败", error_msg)

    def play_audio(self):
        """播放当前选中的音频"""
        try:
            current_row = self.text_table.currentRow()
            if 0 <= current_row < len(self.voice_segments):
                segment = self.voice_segments[current_row]
                audio_path = segment.get('audio_path')
                if audio_path and os.path.exists(audio_path):
                    self.play_audio_file(audio_path)
                else:
                    QMessageBox.warning(self, "警告", "音频文件不存在")
        except Exception as e:
            logger.error(f"播放音频失败: {e}")
            QMessageBox.critical(self, "错误", f"播放失败: {e}")

    def play_audio_file(self, audio_path):
        """播放音频文件"""
        try:
            import platform
            import subprocess

            system = platform.system()
            if system == "Windows":
                os.startfile(audio_path)
            elif system == "Darwin":  # macOS
                subprocess.call(["open", audio_path])
            else:  # Linux
                subprocess.call(["xdg-open", audio_path])

        except Exception as e:
            logger.error(f"播放音频文件失败: {e}")
            QMessageBox.warning(self, "播放失败", f"无法播放音频: {e}")

    def play_segment_audio(self, segment_index):
        """播放指定段落的音频 - 🔧 修复：支持场景和镜头匹配"""
        try:
            if 0 <= segment_index < len(self.voice_segments):
                segment = self.voice_segments[segment_index]
                audio_path = segment.get('audio_path')

                # 🔧 调试信息：显示正在播放的段落信息
                scene_id = segment.get('scene_id', '未知场景')
                shot_id = segment.get('shot_id', '未知镜头')
                logger.info(f"播放配音：段落索引={segment_index}, 场景={scene_id}, 镜头={shot_id}, 音频路径={audio_path}")

                if audio_path and os.path.exists(audio_path):
                    self.play_audio_file(audio_path)
                else:
                    QMessageBox.information(self, "提示", f"该段落（{scene_id} - {shot_id}）还没有生成音频")
        except Exception as e:
            logger.error(f"播放段落音频失败: {e}")

    def play_segment_audio_by_scene_shot(self, scene_id, shot_id):
        """🔧 新增：根据场景ID和镜头ID播放音频"""
        try:
            # 查找匹配的段落
            target_segment_index = -1
            for i, segment in enumerate(self.voice_segments):
                if (segment.get('scene_id') == scene_id and
                    segment.get('shot_id') == shot_id):
                    target_segment_index = i
                    break

            if target_segment_index >= 0:
                logger.info(f"根据场景镜头匹配播放：{scene_id} - {shot_id} -> 段落索引{target_segment_index}")
                self.play_segment_audio(target_segment_index)
            else:
                logger.warning(f"未找到匹配的配音段落：{scene_id} - {shot_id}")
                QMessageBox.information(self, "提示", f"未找到场景「{scene_id}」镜头「{shot_id}」的配音")

        except Exception as e:
            logger.error(f"根据场景镜头播放音频失败: {e}")

    def play_segment_audio_with_fallback(self, scene_id, shot_id, fallback_index):
        """🔧 新增：优先根据场景镜头匹配播放音频，失败时使用备用索引"""
        try:
            # 首先尝试根据场景和镜头匹配
            target_segment_index = -1
            for i, segment in enumerate(self.voice_segments):
                if (segment.get('scene_id') == scene_id and
                    segment.get('shot_id') == shot_id):
                    target_segment_index = i
                    break

            if target_segment_index >= 0:
                logger.info(f"场景镜头匹配成功：{scene_id} - {shot_id} -> 段落索引{target_segment_index}")
                self.play_segment_audio(target_segment_index)
            else:
                # 如果场景镜头匹配失败，使用备用索引
                logger.warning(f"场景镜头匹配失败：{scene_id} - {shot_id}，使用备用索引{fallback_index}")
                if 0 <= fallback_index < len(self.voice_segments):
                    self.play_segment_audio(fallback_index)
                else:
                    QMessageBox.information(self, "提示", f"无法播放配音：场景「{scene_id}」镜头「{shot_id}」")

        except Exception as e:
            logger.error(f"播放配音失败: {e}")

    def play_segment_sound_effect_with_fallback(self, scene_id, shot_id, fallback_index):
        """🔧 新增：优先根据场景镜头匹配播放音效，失败时使用备用索引"""
        try:
            # 首先尝试根据场景和镜头匹配
            target_segment_index = -1
            for i, segment in enumerate(self.voice_segments):
                if (segment.get('scene_id') == scene_id and
                    segment.get('shot_id') == shot_id):
                    target_segment_index = i
                    break

            if target_segment_index >= 0:
                logger.info(f"音效场景镜头匹配成功：{scene_id} - {shot_id} -> 段落索引{target_segment_index}")
                self.play_segment_sound_effect(target_segment_index)
            else:
                # 如果场景镜头匹配失败，使用备用索引
                logger.warning(f"音效场景镜头匹配失败：{scene_id} - {shot_id}，使用备用索引{fallback_index}")
                if 0 <= fallback_index < len(self.voice_segments):
                    self.play_segment_sound_effect(fallback_index)
                else:
                    QMessageBox.information(self, "提示", f"无法播放音效：场景「{scene_id}」镜头「{shot_id}」")

        except Exception as e:
            logger.error(f"播放音效失败: {e}")

    def play_segment_sound_effect(self, segment_index):
        """播放指定段落的音效"""
        try:
            if 0 <= segment_index < len(self.voice_segments):
                segment = self.voice_segments[segment_index]
                sound_effect_path = segment.get('sound_effect_path')
                if sound_effect_path and os.path.exists(sound_effect_path):
                    self.play_audio_file(sound_effect_path)
                else:
                    QMessageBox.information(self, "提示", "该段落还没有生成音效")
        except Exception as e:
            logger.error(f"播放段落音效失败: {e}")

    def generate_single_voice(self, segment_index):
        """生成单个镜头的配音"""
        try:
            if 0 <= segment_index < len(self.voice_segments):
                segment = self.voice_segments[segment_index]
                self.start_voice_generation([segment])
            else:
                QMessageBox.warning(self, "警告", "无效的镜头索引")
        except Exception as e:
            logger.error(f"生成单个配音失败: {e}")
            QMessageBox.critical(self, "错误", f"生成失败: {e}")

    def generate_sound_effect(self, segment_index):
        """生成单个镜头的音效"""
        try:
            if 0 <= segment_index < len(self.voice_segments):
                segment = self.voice_segments[segment_index]
                sound_effect = segment.get('sound_effect', '').strip()
                shot_id = segment.get('shot_id', f'镜头{segment_index + 1}')
                original_text = segment.get('original_text', '')

                if sound_effect:
                    # 🔧 新增：智能判断音效是否合适
                    if self._should_generate_sound_effect(original_text, sound_effect):
                        # 调用单个音效生成
                        self.generate_single_sound_effect(segment_index)
                    else:
                        # 显示确认对话框
                        msg_box = QMessageBox(self)
                        msg_box.setWindowTitle("音效生成确认")
                        msg_box.setText(f"检测到{shot_id}的音效可能与内容不匹配：\n\n"
                                      f"镜头内容：{original_text[:100]}{'...' if len(original_text) > 100 else ''}\n\n"
                                      f"建议音效：{sound_effect}\n\n"
                                      f"是否仍要生成此音效？")
                        msg_box.setIcon(QMessageBox.Icon.Question)

                        # 添加自定义按钮
                        yes_btn = msg_box.addButton("Yes 生成音效", QMessageBox.ButtonRole.YesRole)
                        no_btn = msg_box.addButton("No 跳过", QMessageBox.ButtonRole.NoRole)
                        cancel_btn = msg_box.addButton("Cancel 编辑音效描述", QMessageBox.ButtonRole.RejectRole)

                        msg_box.exec()
                        clicked_button = msg_box.clickedButton()

                        if clicked_button == yes_btn:
                            self.generate_single_sound_effect(segment_index)
                        elif clicked_button == cancel_btn:
                            # 允许用户手动编辑音效描述
                            self._edit_sound_effect_description(segment_index)
                        # No按钮或其他情况：跳过，不做任何操作
                else:
                    # 🔧 修复：提供更智能的提示
                    reply = QMessageBox.question(
                        self, "音效生成",
                        f"{shot_id}未检测到音效需求。\n\n"
                        f"镜头内容：{original_text[:100]}{'...' if len(original_text) > 100 else ''}\n\n"
                        f"是否需要手动添加音效描述？"
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        self._edit_sound_effect_description(segment_index)
            else:
                QMessageBox.warning(self, "警告", "无效的镜头索引")
        except Exception as e:
            logger.error(f"生成音效失败: {e}")
            QMessageBox.critical(self, "错误", f"音效生成失败: {e}")

    def _should_generate_sound_effect(self, text, sound_effect):
        """判断是否应该生成音效"""
        if not text or not sound_effect:
            return False

        # 检查文本内容是否真的需要这个音效
        text_lower = text.lower()
        effect_lower = sound_effect.lower()

        # 电话音效的特殊判断
        if '电话' in effect_lower:
            phone_keywords = ['电话', '铃声', '响', '接', '打', '挂', '嘟']
            has_phone_context = any(keyword in text_lower for keyword in phone_keywords)
            if not has_phone_context:
                logger.debug(f"电话音效与文本内容不匹配: {text[:50]}... -> {sound_effect}")
                return False

        # 检查是否是纯对话或介绍性文本（通常不需要音效）
        intro_keywords = ['大家好', '我是', '曾经', '那个', '家伙']
        business_keywords = ['开价', '许诺', '股份', '分红', '豪车', '一个月', '万']

        if any(keyword in text_lower for keyword in intro_keywords + business_keywords):
            logger.debug(f"检测到不需要音效的文本类型: {text[:50]}...")
            return False

        return True

    def _edit_sound_effect_description(self, segment_index):
        """编辑音效描述"""
        try:
            if 0 <= segment_index < len(self.voice_segments):
                segment = self.voice_segments[segment_index]
                current_effect = segment.get('sound_effect', '')
                shot_id = segment.get('shot_id', f'镜头{segment_index + 1}')

                from PyQt5.QtWidgets import QInputDialog

                new_effect, ok = QInputDialog.getText(
                    self, f"编辑{shot_id}音效",
                    "请输入音效描述（留空表示不需要音效）：",
                    text=current_effect
                )

                if ok:
                    # 更新音效描述
                    segment['sound_effect'] = new_effect.strip()

                    # 更新表格显示
                    sound_effect_item = self.text_table.item(segment_index, 5)
                    if sound_effect_item:
                        sound_effect_item.setText(new_effect.strip())

                    # 如果有音效描述，询问是否立即生成
                    if new_effect.strip():
                        reply = QMessageBox.question(
                            self, "生成音效",
                            f"是否立即生成音效：{new_effect.strip()}？"
                        )

                        if reply == QMessageBox.StandardButton.Yes:
                            self.generate_single_sound_effect(segment_index)

                    logger.info(f"更新{shot_id}音效描述: {new_effect.strip()}")

        except Exception as e:
            logger.error(f"编辑音效描述失败: {e}")
            QMessageBox.critical(self, "错误", f"编辑失败: {e}")

    def generate_all_voice(self):
        """批量生成所有配音"""
        try:
            # 获取所有选中的文本段落
            selected_segments = []
            for i in range(self.text_table.rowCount()):
                checkbox = self.text_table.cellWidget(i, 0)
                if checkbox and isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                    selected_segments.append(self.voice_segments[i])

            if not selected_segments:
                QMessageBox.warning(self, "警告", "请至少选择一个文本段落")
                return

            self.start_voice_generation(selected_segments)

        except Exception as e:
            logger.error(f"批量生成配音失败: {e}")
            QMessageBox.critical(self, "错误", f"生成失败: {e}")

    def generate_selected_voice(self):
        """生成选中的配音"""
        try:
            current_row = self.text_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "警告", "请先选择一个文本段落")
                return

            segment = self.voice_segments[current_row]
            self.start_voice_generation([segment])

        except Exception as e:
            logger.error(f"生成选中配音失败: {e}")
            QMessageBox.critical(self, "错误", f"生成失败: {e}")

    def start_voice_generation(self, segments):
        """开始配音生成"""
        try:
            engine_id = self.engine_combo.currentData()
            if not engine_id:
                QMessageBox.warning(self, "警告", "请选择配音引擎")
                return

            # 获取输出目录
            output_dir = self.get_audio_output_dir()
            if not output_dir:
                return

            # 获取配音设置
            settings = self.get_current_voice_settings()

            # 启动生成线程
            self.generation_thread = VoiceGenerationThread(
                self.engine_manager, engine_id, segments, output_dir, settings
            )
            self.generation_thread.progress_updated.connect(self.on_generation_progress)
            self.generation_thread.voice_generated.connect(self.on_voice_generated)
            self.generation_thread.error_occurred.connect(self.on_generation_error)
            self.generation_thread.finished.connect(self.on_generation_finished)
            self.generation_thread.start()

            # 更新UI状态
            self.progress_bar.setVisible(True)
            self.generate_all_btn.setEnabled(False)
            self.generate_selected_btn.setEnabled(False)

        except Exception as e:
            logger.error(f"启动配音生成失败: {e}")
            QMessageBox.critical(self, "错误", f"启动失败: {e}")

    def get_audio_output_dir(self):
        """获取音频输出目录"""
        try:
            # 确保音频文件管理器已初始化
            if not self.audio_file_manager:
                self._ensure_audio_file_manager()

            if not self.audio_file_manager:
                QMessageBox.warning(self, "警告", "无法初始化音频文件管理器，请检查项目是否已加载")
                return None

            engine_id = self.engine_combo.currentData()
            if not engine_id:
                QMessageBox.warning(self, "警告", "请选择配音引擎")
                return None

            # 使用音频文件管理器获取引擎目录
            output_dir = self.audio_file_manager.get_engine_audio_dir(engine_id)

            return str(output_dir)

        except Exception as e:
            logger.error(f"获取音频输出目录失败: {e}")
            QMessageBox.critical(self, "错误", f"获取输出目录失败: {e}")
            return None

    def _ensure_audio_file_manager(self):
        """确保音频文件管理器已初始化"""
        try:
            if self.audio_file_manager:
                return True

            # 尝试从项目管理器获取项目根目录
            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("项目管理器或当前项目未初始化")
                return False

            project_root = self.project_manager.current_project.get('project_dir') or self.project_manager.current_project.get('project_root')
            if not project_root:
                logger.warning("无法获取项目根目录")
                return False

            # 初始化音频文件管理器
            self.audio_file_manager = AudioFileManager(project_root)
            logger.info(f"音频文件管理器初始化成功: {project_root}")
            return True

        except Exception as e:
            logger.error(f"初始化音频文件管理器失败: {e}")
            return False

    def get_current_voice_settings(self):
        """获取当前配音设置"""
        settings = {}

        # 音色
        voice_id = self.voice_combo.currentData()
        if voice_id:
            settings['voice'] = voice_id

        # 语速
        speed = self.speed_slider.value() / 100.0
        settings['speed'] = speed

        # 其他引擎特定设置可以在这里添加

        return settings

    def on_generation_progress(self, progress, message):
        """生成进度更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def on_voice_generated(self, result):
        """单个配音生成完成"""
        try:
            # 🔧 修复：通过scene_id和shot_id的组合精确找到正确的段落索引
            shot_id = result.get('shot_id')
            audio_path = result.get('audio_path')

            # 从result中获取scene_id，如果没有则尝试从segment_index推断
            scene_id = result.get('scene_id')
            segment_index = result.get('segment_index')

            # 查找匹配的段落
            target_segment_index = None

            # 方法1：通过scene_id和shot_id精确匹配
            if scene_id and shot_id:
                for i, segment in enumerate(self.voice_segments):
                    if (segment.get('scene_id') == scene_id and
                        segment.get('shot_id') == shot_id):
                        target_segment_index = i
                        logger.info(f"精确匹配找到段落: scene_id='{scene_id}', shot_id='{shot_id}', 索引={i}")
                        break

            # 方法2：如果精确匹配失败，使用segment_index作为备用
            if target_segment_index is None and segment_index is not None:
                if 0 <= segment_index < len(self.voice_segments):
                    target_segment_index = segment_index
                    segment = self.voice_segments[segment_index]
                    logger.warning(f"使用segment_index备用匹配: 索引={segment_index}, scene_id='{segment.get('scene_id')}', shot_id='{segment.get('shot_id')}'")
                else:
                    logger.error(f"segment_index超出范围: {segment_index}, 总段落数: {len(self.voice_segments)}")
                    return

            # 方法3：如果都失败，尝试只通过shot_id匹配（可能不准确）
            if target_segment_index is None:
                for i, segment in enumerate(self.voice_segments):
                    if segment.get('shot_id') == shot_id:
                        target_segment_index = i
                        logger.warning(f"仅通过shot_id匹配（可能不准确）: shot_id='{shot_id}', 索引={i}")
                        break

            if target_segment_index is None:
                logger.error(f"无法找到匹配的段落: scene_id='{scene_id}', shot_id='{shot_id}', segment_index={segment_index}")
                return

            # 更新段落状态
            self.voice_segments[target_segment_index]['status'] = '已生成'
            self.voice_segments[target_segment_index]['audio_path'] = audio_path

            # 更新表格显示（状态列现在是第4列，索引为4）
            status_item = QTableWidgetItem('已生成')
            self.text_table.setItem(target_segment_index, 4, status_item)

            # 🔧 重新创建操作按钮以反映新状态
            self._update_row_buttons(target_segment_index)

            # 添加到音频列表
            self.add_to_audio_list(result)

            logger.info(f"配音生成完成: scene_id='{scene_id}', shot_id='{shot_id}' (索引{target_segment_index}) -> {audio_path}")

        except Exception as e:
            logger.error(f"处理配音生成结果失败: {e}")

    def on_generation_error(self, error_msg):
        """配音生成错误"""
        logger.error(f"配音生成错误: {error_msg}")
        self.status_label.setText(f"生成错误: {error_msg}")

    def on_generation_finished(self):
        """配音生成完成"""
        self.progress_bar.setVisible(False)
        self.generate_all_btn.setEnabled(True)
        self.generate_selected_btn.setEnabled(True)
        self.status_label.setText("配音生成完成")

        # 保存到项目
        self.save_to_project()

        # 🔧 新增：配音优先工作流程 - 发送配音数据准备完成信号
        self._emit_voice_data_ready()

    def _emit_voice_data_ready(self):
        """🔧 增强：发送配音数据准备完成信号，包含音频时长信息"""
        try:
            # 检查是否启用配音优先工作流程
            if not self._is_voice_first_workflow_enabled():
                return

            # 准备配音数据，包含音频时长信息
            voice_data_for_image_generation = []
            for segment in self.voice_segments:
                if segment.get('audio_path') and os.path.exists(segment.get('audio_path', '')):
                    # 🔧 新增：获取音频时长
                    audio_duration = self._get_audio_duration(segment.get('audio_path', ''))

                    # 🔧 新增：基于时长计算建议的图像数量
                    suggested_image_count = self._calculate_image_count_by_duration(audio_duration)

                    voice_data_for_image_generation.append({
                        'segment_index': segment.get('index', 0),
                        'scene_id': segment.get('scene_id', ''),
                        'shot_id': segment.get('shot_id', ''),
                        'voice_content': segment.get('original_text', ''),
                        'dialogue_content': segment.get('dialogue_text', ''),
                        'audio_path': segment.get('audio_path', ''),
                        'audio_duration': audio_duration,  # 🔧 新增：音频时长
                        'suggested_image_count': suggested_image_count,  # 🔧 新增：建议图像数量
                        'sound_effect': segment.get('sound_effect', ''),
                        'content_type': '台词' if segment.get('dialogue_text') else '旁白'
                    })

            if voice_data_for_image_generation:
                logger.info(f"配音数据准备完成，发送 {len(voice_data_for_image_generation)} 个配音段落给图像生成模块")
                # 🔧 新增：保存配音数据到项目，供图像生成使用
                self._save_voice_data_for_image_generation(voice_data_for_image_generation)

                self.voice_data_ready.emit(voice_data_for_image_generation)
                self.voice_batch_completed.emit(voice_data_for_image_generation)
            else:
                logger.warning("没有成功生成的配音数据可以传递给图像生成模块")

        except Exception as e:
            logger.error(f"发送配音数据准备完成信号失败: {e}")

    def _get_audio_duration(self, audio_path: str) -> float:
        """🔧 新增：获取音频文件时长"""
        try:
            if not audio_path or not os.path.exists(audio_path):
                return 3.0  # 默认3秒

            # 方法1：尝试使用librosa
            try:
                import librosa
                duration = librosa.get_duration(filename=audio_path)
                return float(duration)
            except ImportError:
                pass

            # 方法2：尝试使用mutagen
            try:
                from mutagen import File
                audio_file = File(audio_path)
                if audio_file and hasattr(audio_file, 'info') and hasattr(audio_file.info, 'length'):
                    return float(audio_file.info.length)
            except ImportError:
                pass

            # 方法3：简单的文件大小估算
            try:
                file_size = os.path.getsize(audio_path)
                # 简单估算：假设平均比特率为128kbps
                estimated_duration = file_size / (128 * 1024 / 8)
                return max(1.0, float(estimated_duration))  # 最少1秒
            except:
                pass

            return 3.0  # 默认3秒

        except Exception as e:
            logger.warning(f"获取音频时长失败: {e}")
            return 3.0  # 默认3秒

    def _calculate_image_count_by_duration(self, duration: float) -> int:
        """🔧 修改：每个配音段落只生成1张图片，确保配音数量与图片数量一致"""
        return 1

    def _save_voice_data_for_image_generation(self, voice_data: list):
        """🔧 新增：保存配音数据到项目，供图像生成使用"""
        try:
            if self.project_manager and self.project_manager.current_project:
                project_data = self.project_manager.get_project_data()
                if not project_data.get('voice_generation'):
                    project_data['voice_generation'] = {}

                project_data['voice_generation']['voice_segments_for_image'] = voice_data
                project_data['voice_generation']['voice_first_workflow_enabled'] = True
                project_data['voice_generation']['last_voice_generation_time'] = datetime.now().isoformat()

                self.project_manager.save_project_data(project_data)
                logger.info("配音数据已保存到项目，供图像生成使用")
        except Exception as e:
            logger.error(f"保存配音数据到项目失败: {e}")

    def _is_voice_first_workflow_enabled(self):
        """检查是否启用配音优先工作流程"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return False

            workflow_settings = self.project_manager.current_project.get('workflow_settings', {})
            return workflow_settings.get('mode') == 'voice_first' and workflow_settings.get('voice_first_enabled', False)
        except Exception as e:
            logger.error(f"检查配音优先工作流程状态失败: {e}")
            return False

    def add_to_audio_list(self, result):
        """添加到音频列表"""
        try:
            row = self.audio_list.rowCount()
            self.audio_list.insertRow(row)

            # 🔧 修复：更新列结构 - 旁白、音效、时长、操作

            # 旁白内容
            text = result.get('text', '')
            text_item = QTableWidgetItem(text[:50] + "..." if len(text) > 50 else text)
            text_item.setToolTip(text)
            self.audio_list.setItem(row, 0, text_item)

            # 音效内容（从segment中获取）
            sound_effect_text = result.get('sound_effect_text', '暂无音效')
            sound_effect_item = QTableWidgetItem(sound_effect_text[:30] + "..." if len(sound_effect_text) > 30 else sound_effect_text)
            sound_effect_item.setToolTip(sound_effect_text)
            self.audio_list.setItem(row, 1, sound_effect_item)

            # 时长（尝试获取真实时长）
            audio_path = result.get('audio_path', '')
            duration_text = self._get_audio_duration(audio_path) if audio_path else "--:--"
            self.audio_list.setItem(row, 2, QTableWidgetItem(duration_text))

        except Exception as e:
            logger.error(f"添加到音频列表失败: {e}")

    def _get_audio_duration(self, audio_path):
        """获取音频文件时长"""
        try:
            if not audio_path or not os.path.exists(audio_path):
                return "--:--"

            # 🔧 修复：使用新的可靠音频时长检测器
            from src.utils.reliable_audio_duration import get_audio_duration_string
            duration_str = get_audio_duration_string(audio_path)

            if duration_str != "00:00":
                logger.info(f"✅ 成功获取音频时长: {duration_str} - {os.path.basename(audio_path)}")
                return duration_str
            else:
                logger.warning(f"⚠️ 无法获取音频时长: {os.path.basename(audio_path)}")
                return "--:--"

        except Exception as e:
            logger.error(f"获取音频时长失败: {e}")
            return "--:--"

    def import_from_text_creation(self):
        """从文本创作导入文本 - 智能匹配五阶段分镜"""
        try:
            # 🔧 优化：首先检查是否有五阶段分镜数据
            storyboard_data = self._get_five_stage_storyboard_data()

            # 🔧 修复：更全面的文本创作标签页访问方式
            created_text = ""

            # 方法1：直接从主窗口获取文本创作内容
            main_window = self.parent_window
            if main_window:
                # 优先获取改写文本
                if hasattr(main_window, 'rewritten_text'):
                    rewrite_content = main_window.rewritten_text.toPlainText().strip()
                    if rewrite_content:
                        created_text = rewrite_content
                        logger.info(f"从主窗口获取到改写文本，长度: {len(created_text)}")

                # 如果没有改写文本，获取原始文本
                if not created_text and hasattr(main_window, 'text_input'):
                    original_content = main_window.text_input.toPlainText().strip()
                    if original_content:
                        created_text = original_content
                        logger.info(f"从主窗口获取到原始文本，长度: {len(created_text)}")

            # 方法2：通过标签页查找文本创作内容
            if not created_text and main_window and hasattr(main_window, 'tab_widget'):
                tab_widget = main_window.tab_widget
                for i in range(tab_widget.count()):
                    tab = tab_widget.widget(i)
                    # 检查是否是文本创作标签页
                    if hasattr(tab, 'rewritten_text') or hasattr(tab, 'text_input'):
                        logger.info(f"找到文本创作标签页，索引: {i}")

                        # 优先获取改写结果
                        if hasattr(tab, 'rewritten_text'):
                            rewrite_content = tab.rewritten_text.toPlainText().strip()
                            if rewrite_content:
                                created_text = rewrite_content
                                logger.info(f"获取到改写文本，长度: {len(created_text)}")
                                break

                        # 如果没有改写内容，获取原始文本
                        if not created_text and hasattr(tab, 'text_input'):
                            original_content = tab.text_input.toPlainText().strip()
                            if original_content:
                                created_text = original_content
                                logger.info(f"获取到原始文本，长度: {len(created_text)}")
                                break

            # 方法2：如果方法1失败，尝试通过标签页名称查找
            if not created_text and main_window and hasattr(main_window, 'tab_widget'):
                tab_widget = main_window.tab_widget
                for i in range(tab_widget.count()):
                    tab_text = tab_widget.tabText(i)
                    if "文本创作" in tab_text or "文本" in tab_text:
                        tab = tab_widget.widget(i)
                        logger.info(f"通过标签名找到文本创作标签页: {tab_text}")

                        # 尝试获取文本内容
                        for attr_name in ['rewrite_text', 'result_text', 'text_edit', 'content_text']:
                            if hasattr(tab, attr_name):
                                text_widget = getattr(tab, attr_name)
                                if hasattr(text_widget, 'toPlainText'):
                                    content = text_widget.toPlainText().strip()
                                    if content:
                                        created_text = content
                                        logger.info(f"从 {attr_name} 获取到文本，长度: {len(created_text)}")
                                        break
                        if created_text:
                            break

            if not created_text or not created_text.strip():
                QMessageBox.warning(self, "警告", "文本创作标签页中没有可导入的内容！\n\n请先在'📝 文本创作'标签页中创作或改写文本。")
                return

            # 🔧 优化：智能分段处理 - 优先使用时长控制分割
            if storyboard_data:
                logger.info("检测到五阶段分镜数据，使用智能匹配算法")
                segments = self._intelligent_text_scene_matching(created_text, storyboard_data)
                match_type = "智能匹配"
                # 转换为配音段落格式
                voice_segments = []
                for i, segment_text in enumerate(segments):
                    voice_segment = {
                        'index': i,
                        'shot_id': f'text_segment_{i+1:03d}',
                        'scene_id': f'scene_{(i//3)+1}',
                        'original_text': segment_text.strip(),
                        'dialogue_text': '',
                        'sound_effect': '',
                        'status': '未生成',
                        'audio_path': '',
                        'selected': True
                    }
                    voice_segments.append(voice_segment)
            else:
                logger.info(f"使用智能时长控制分割，目标时长: {self.target_duration}秒")
                # 🔧 新增：使用智能分割器创建配音段落
                voice_segments = create_voice_segments_with_duration_control(created_text, self.target_duration)
                match_type = f"智能时长控制({self.target_duration}秒)"

            if not voice_segments:
                QMessageBox.warning(self, "警告", "文本分段失败，请检查文本内容！")
                return

            # 清空现有数据
            self.voice_segments.clear()
            self.text_table.setRowCount(0)

            # 设置配音段落
            self.voice_segments = voice_segments

            # 更新表格显示
            self.update_text_table()

            # 更新状态
            self.status_label.setText(f"已导入 {len(voice_segments)} 个文本段落（{match_type}）")

            # 显示成功消息，包含匹配类型和时长信息
            success_message = f"成功从文本创作导入 {len(voice_segments)} 个段落！\n\n"
            if match_type == "智能匹配":
                success_message += "✅ 使用了智能匹配算法，文本已与五阶段分镜内容对应\n"
                success_message += "📝 导入的内容将与现有场景和镜头保持一致\n\n"
            else:
                # 计算平均时长
                avg_duration = sum(s.get('estimated_duration', 0) for s in voice_segments) / len(voice_segments)
                success_message += f"🎯 使用了智能时长控制分割\n"
                success_message += f"⏱️ 目标时长: {self.target_duration}秒，平均时长: {avg_duration:.1f}秒\n"
                success_message += f"🎬 每个镜头的配音时长已优化控制\n\n"

            success_message += "现在可以选择配音引擎和音色，然后生成配音。"

            QMessageBox.information(self, "导入成功", success_message)

            logger.info(f"从文本创作导入了 {len(voice_segments)} 个文本段落，使用{match_type}算法")

        except Exception as e:
            logger.error(f"从文本创作导入失败: {e}")
            QMessageBox.critical(self, "错误", f"导入失败：{str(e)}")

    def _get_five_stage_storyboard_data(self):
        """获取五阶段分镜数据"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return None

            project_data = self.project_manager.get_project_data()
            if not project_data:
                return None

            return project_data.get('five_stage_storyboard', {})
        except Exception as e:
            logger.error(f"获取五阶段分镜数据失败: {e}")
            return None

    def _intelligent_text_scene_matching(self, created_text, storyboard_data):
        """智能文本与场景匹配算法"""
        try:
            # 获取场景数据
            stage_data = storyboard_data.get('stage_data', {})
            scenes_data = stage_data.get('3', {}).get('scenes_data', [])
            storyboard_results = stage_data.get('4', {}).get('storyboard_results', [])

            if not scenes_data and not storyboard_results:
                logger.warning("没有找到场景或分镜数据，使用简单分段")
                return self.smart_text_segmentation(created_text)

            # 🔧 智能匹配：基于场景的原文内容进行匹配
            matched_segments = []

            # 优先使用场景数据进行匹配
            if scenes_data:
                for scene in scenes_data:
                    scene_original_text = scene.get('对应原文段落', '')
                    if scene_original_text and scene_original_text.strip():
                        # 在创作文本中查找匹配的内容
                        matched_text = self._find_matching_text_segment(created_text, scene_original_text)
                        if matched_text:
                            matched_segments.append(matched_text)

            # 🔧 修复：始终使用分镜数据提取所有镜头原文，不限制数量
            if storyboard_results:
                for result in storyboard_results:
                    storyboard_script = result.get('storyboard_script', '')
                    if storyboard_script:
                        # 🔧 修复：从分镜脚本中提取镜头原文而不是台词/旁白
                        extracted_texts = self._extract_shot_original_text_from_storyboard(storyboard_script)
                        for extracted_text in extracted_texts:
                            if extracted_text and extracted_text not in matched_segments:
                                matched_segments.append(extracted_text)

            # 如果匹配的段落太少，补充原始分段
            if len(matched_segments) < 3:
                simple_segments = self.smart_text_segmentation(created_text)
                for segment in simple_segments:
                    if segment not in matched_segments:
                        matched_segments.append(segment)

            logger.info(f"智能匹配完成，生成 {len(matched_segments)} 个段落")
            return matched_segments  # 🔧 修复：移除15个段落的限制，返回所有匹配的段落

        except Exception as e:
            logger.error(f"智能匹配失败: {e}")
            return self.smart_text_segmentation(created_text)

    def _find_matching_text_segment(self, full_text, target_text):
        """在完整文本中查找匹配的文本段落"""
        try:
            # 简单的文本匹配算法
            target_words = target_text.strip()[:50]  # 取前50字作为匹配关键词

            # 按段落分割完整文本
            paragraphs = [p.strip() for p in full_text.split('\n') if p.strip()]

            for paragraph in paragraphs:
                if len(paragraph) > 20 and target_words in paragraph:
                    return paragraph

            return None
        except Exception as e:
            logger.error(f"文本匹配失败: {e}")
            return None

    def _extract_dialogue_from_storyboard(self, storyboard_script):
        """从分镜脚本中提取台词/旁白"""
        try:
            lines = storyboard_script.split('\n')
            dialogue_lines = []

            for line in lines:
                line = line.strip()
                if '台词/旁白' in line and '：' in line:
                    dialogue = line.split('：', 1)[1].strip()
                    if dialogue and dialogue != '无' and len(dialogue) > 5:
                        dialogue_lines.append(dialogue)

            return ' '.join(dialogue_lines) if dialogue_lines else None
        except Exception as e:
            logger.error(f"提取台词失败: {e}")
            return None

    def _extract_shot_original_text_from_storyboard(self, storyboard_script):
        """从分镜脚本中提取镜头原文"""
        try:
            lines = storyboard_script.split('\n')
            original_texts = []

            for line in lines:
                line = line.strip()
                if '镜头原文' in line and '：' in line:
                    original_text = line.split('：', 1)[1].strip()
                    if original_text and original_text != '无' and len(original_text) > 5:
                        original_texts.append(original_text)

            logger.info(f"从分镜脚本中提取到 {len(original_texts)} 个镜头原文")
            return original_texts
        except Exception as e:
            logger.error(f"提取镜头原文失败: {e}")
            return []

    def smart_text_segmentation(self, text):
        """智能文本分段 - 使用新的时长控制分割器"""
        try:
            # 清理文本
            text = text.strip()
            if not text:
                return []

            logger.info(f"开始智能文本分段，目标时长: {self.target_duration}秒")

            # 🔧 新增：使用智能分割器
            voice_segments = create_voice_segments_with_duration_control(text, self.target_duration)

            if voice_segments:
                # 转换为简单的文本段落格式（兼容现有代码）
                text_segments = []
                for segment in voice_segments:
                    text_segments.append(segment['original_text'])

                logger.info(f"智能分段完成，生成 {len(text_segments)} 个段落")
                return text_segments
            else:
                # 降级到原有方法
                logger.warning("智能分割失败，使用降级方法")
                return self._fallback_text_segmentation(text)

        except Exception as e:
            logger.error(f"智能文本分段失败: {e}")
            return self._fallback_text_segmentation(text)

    def _fallback_text_segmentation(self, text):
        """降级文本分段方法"""
        try:
            # 按段落分割
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

            segments = []
            for paragraph in paragraphs:
                # 如果段落太长，按句子分割
                if len(paragraph) > 200:
                    # 按句号、问号、感叹号分割
                    sentences = []
                    current_sentence = ""

                    for char in paragraph:
                        current_sentence += char
                        if char in '。！？.!?':
                            if current_sentence.strip():
                                sentences.append(current_sentence.strip())
                                current_sentence = ""

                    # 添加剩余内容
                    if current_sentence.strip():
                        sentences.append(current_sentence.strip())

                    # 合并短句子
                    merged_segments = []
                    current_segment = ""

                    for sentence in sentences:
                        if len(current_segment + sentence) <= 150:
                            current_segment += sentence
                        else:
                            if current_segment:
                                merged_segments.append(current_segment)
                            current_segment = sentence

                    if current_segment:
                        merged_segments.append(current_segment)

                    segments.extend(merged_segments)
                else:
                    segments.append(paragraph)

            return segments

        except Exception as e:
            logger.error(f"降级文本分段失败: {e}")
            # 最简单的分割方法
            return [p.strip() for p in text.split('\n') if p.strip()]

    def show_manual_input(self):
        """显示手动输入对话框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("手动输入配音文本")
        dialog.setModal(True)
        dialog.resize(600, 400)

        layout = QVBoxLayout(dialog)

        # 说明标签
        info_label = QLabel("请输入要配音的文本内容，系统会自动进行智能分段：")
        layout.addWidget(info_label)

        # 文本输入框
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("请在此输入要配音的文本内容...\n\n提示：\n- 每个段落会自动分为一个配音段落\n- 过长的段落会自动按句子分割\n- 建议每段控制在100-200字以内")
        layout.addWidget(text_edit)

        # 按钮
        from PyQt5.QtWidgets import QHBoxLayout, QPushButton
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_button = QPushButton("确定")
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        if dialog.exec() == 1:  # QDialog.Accepted = 1
            input_text = text_edit.toPlainText().strip()
            if input_text:
                # 使用相同的分段逻辑
                segments = self.smart_text_segmentation(input_text)

                if segments:
                    # 清空现有数据
                    self.voice_segments.clear()
                    self.text_table.setRowCount(0)

                    # 添加分段到配音列表
                    for i, segment_text in enumerate(segments):
                        segment_data = {
                            'shot_id': f'manual_segment_{i+1:03d}',
                            'scene_id': f'scene_{(i//3)+1}',
                            'original_text': segment_text.strip(),
                            'dialogue_text': '',
                            'sound_effect': '',
                            'status': '未生成'
                        }
                        self.voice_segments.append(segment_data)

                    # 更新表格显示
                    self.update_text_table()

                    # 更新状态
                    self.status_label.setText(f"已手动输入 {len(segments)} 个文本段落")

                    QMessageBox.information(self, "成功", f"成功添加 {len(segments)} 个文本段落！")

                    logger.info(f"手动输入了 {len(segments)} 个文本段落")
                else:
                    QMessageBox.warning(self, "警告", "文本分段失败，请检查输入内容！")
            else:
                QMessageBox.warning(self, "警告", "请输入有效的文本内容！")

    def edit_selected_text(self):
        """编辑选中的文本"""
        # 这里可以实现文本编辑功能
        QMessageBox.information(self, "提示", "文本编辑功能将在后续版本中实现")

    def delete_selected_text(self):
        """删除选中的文本"""
        # 这里可以实现文本删除功能
        QMessageBox.information(self, "提示", "文本删除功能将在后续版本中实现")

    def export_audio(self):
        """导出音频"""
        # 这里可以实现音频导出功能
        QMessageBox.information(self, "提示", "音频导出功能将在后续版本中实现")

    def clear_audio(self):
        """清空音频"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有生成的音频吗？"
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.audio_list.setRowCount(0)
            self.generated_audio.clear()

    def load_voice_data(self, voice_data):
        """加载配音数据"""
        try:
            # 从项目数据中恢复配音设置和生成的音频
            settings = voice_data.get('settings', {})
            generated_audio = voice_data.get('generated_audio', [])
            voice_segments = voice_data.get('voice_segments', [])

            # 恢复设置
            if 'provider' in settings:
                engine_id = settings['provider']
                for i in range(self.engine_combo.count()):
                    if self.engine_combo.itemData(i) == engine_id:
                        self.engine_combo.setCurrentIndex(i)
                        break

            # 🔧 修复：恢复voice_segments数据
            if voice_segments:
                self.voice_segments = voice_segments
                logger.info(f"恢复了 {len(voice_segments)} 个配音段落")

                # 更新表格显示
                self.update_text_table()

                # 🔧 修复：恢复配音和音效状态
                self.restore_audio_states()

                # 🔧 修复：更新所有行的按钮状态
                for i in range(len(self.voice_segments)):
                    self._update_row_buttons(i)

            # 🔧 修复：清空并重新构建音频列表
            self.audio_list.setRowCount(0)
            self.generated_audio.clear()

            # 🔧 修复：从voice_segments重新构建音频列表
            for i, segment in enumerate(self.voice_segments):
                audio_path = segment.get('audio_path', '')
                if audio_path and os.path.exists(audio_path):
                    # 构建音频数据
                    audio_data = {
                        'text': segment.get('original_text', ''),
                        'audio_path': audio_path,
                        'sound_effect_text': segment.get('sound_effect', '暂无音效'),
                        'shot_id': segment.get('shot_id', f'镜头{i+1}'),
                        'scene_id': segment.get('scene_id', f'场景{(i//3)+1}')
                    }
                    self.generated_audio.append(audio_data)
                    self.add_to_audio_list(audio_data)

            logger.info(f"配音数据加载完成: {len(voice_segments)} 个段落, {len(self.generated_audio)} 个音频")

        except Exception as e:
            logger.error(f"加载配音数据失败: {e}")

    def save_to_project(self):
        """保存到项目"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                QMessageBox.warning(self, "警告", "请先加载项目")
                return

            # 🔧 新增：生成字幕文件
            self._generate_subtitles_for_segments()

            # 构建配音数据
            voice_data = {
                'provider': self.engine_combo.currentData(),
                'settings': self.get_current_voice_settings(),
                'generated_audio': self.generated_audio,
                'voice_segments': self.voice_segments,
                'progress': {
                    'total_segments': len(self.voice_segments),
                    'completed_segments': len([s for s in self.voice_segments if s.get('status') == '已生成']),
                    'status': 'completed' if all(s.get('status') == '已生成' for s in self.voice_segments) else 'in_progress'
                },
                'updated_time': datetime.now().isoformat()
            }

            # 🔧 新增：同步ID管理器数据到项目
            if hasattr(self, 'shot_id_manager') and self.shot_id_manager.shot_mappings:
                project_data = self.project_manager.get_project_data()
                if project_data:
                    self.shot_id_manager.sync_with_project_data(project_data)
                    logger.info("ID管理器数据已同步到项目")

            # 保存到项目
            self.project_manager.current_project['voice_generation'] = voice_data
            self.project_manager.save_project()

            QMessageBox.information(self, "保存", "配音数据已保存到项目")

        except Exception as e:
            logger.error(f"保存配音数据到项目失败: {e}")
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def get_project_data(self):
        """获取项目数据（供主窗口调用）"""
        try:
            return {
                'voice_generation': {
                    'provider': self.engine_combo.currentData(),
                    'settings': self.get_current_voice_settings(),
                    'generated_audio': self.generated_audio,
                    'voice_segments': self.voice_segments
                }
            }
        except Exception as e:
            logger.error(f"获取配音项目数据失败: {e}")
            return {}

    def _expand_voice_segments(self, target_count, project_data):
        """扩展配音段落数量"""
        try:
            current_count = len(self.voice_segments)
            needed_count = target_count - current_count

            logger.info(f"需要增加 {needed_count} 个配音段落")

            # 获取原始文本用于分段
            original_text = project_data.get('original_text', '')
            if not original_text:
                # 如果没有原始文本，从现有段落复制
                self._duplicate_existing_segments(needed_count)
                return

            # 重新进行精确分段
            text_segments = self._create_precise_text_segments(original_text, target_count)

            # 重建配音段落列表
            new_voice_segments = []
            for i in range(target_count):
                if i < current_count:
                    # 保留现有段落的基本信息
                    existing_segment = self.voice_segments[i].copy()
                    if i < len(text_segments):
                        # 更新文本内容
                        existing_segment['original_text'] = text_segments[i].get('content', '')
                    new_voice_segments.append(existing_segment)
                else:
                    # 创建新段落
                    text_content = text_segments[i].get('content', '') if i < len(text_segments) else ''
                    scene_num = (i // 3) + 1  # 假设每3个镜头为一个场景
                    shot_num = (i % 3) + 1

                    new_voice_segments.append({
                        'index': i,
                        'scene_id': f'场景{scene_num}',
                        'shot_id': f'镜头{shot_num}',
                        'original_text': text_content,
                        'dialogue_text': '',
                        'content_type': '旁白',
                        'sound_effect': '',
                        'status': '未生成',
                        'audio_path': '',
                        'selected': True
                    })

            self.voice_segments = new_voice_segments
            logger.info(f"成功扩展到 {len(self.voice_segments)} 个配音段落")

        except Exception as e:
            logger.error(f"扩展配音段落失败: {e}")

    def _reduce_voice_segments(self, target_count):
        """减少配音段落数量"""
        try:
            current_count = len(self.voice_segments)
            logger.info(f"需要减少到 {target_count} 个配音段落")

            if target_count <= 0:
                self.voice_segments = []
                return

            # 策略：保留前target_count个段落，合并剩余内容
            if target_count < current_count:
                # 将多余段落的内容合并到最后一个保留的段落中
                kept_segments = self.voice_segments[:target_count]
                excess_segments = self.voice_segments[target_count:]

                if excess_segments and kept_segments:
                    # 合并多余段落的文本到最后一个保留段落
                    last_segment = kept_segments[-1]
                    additional_text = []

                    for segment in excess_segments:
                        text = segment.get('original_text', '').strip()
                        if text:
                            additional_text.append(text)

                    if additional_text:
                        current_text = last_segment.get('original_text', '').strip()
                        combined_text = current_text + ' ' + ' '.join(additional_text)
                        last_segment['original_text'] = combined_text

                self.voice_segments = kept_segments
                logger.info(f"成功减少到 {len(self.voice_segments)} 个配音段落")

        except Exception as e:
            logger.error(f"减少配音段落失败: {e}")

    def _duplicate_existing_segments(self, needed_count):
        """复制现有段落来填充不足的数量"""
        try:
            if not self.voice_segments:
                return

            current_count = len(self.voice_segments)
            for i in range(needed_count):
                # 循环复制现有段落
                source_index = i % current_count
                source_segment = self.voice_segments[source_index].copy()

                # 更新索引和ID
                new_index = current_count + i
                scene_num = (new_index // 3) + 1
                shot_num = (new_index % 3) + 1

                source_segment.update({
                    'index': new_index,
                    'scene_id': f'场景{scene_num}',
                    'shot_id': f'镜头{shot_num}',
                    'status': '未生成',
                    'audio_path': ''
                })

                self.voice_segments.append(source_segment)

            logger.info(f"通过复制现有段落增加了 {needed_count} 个配音段落")

        except Exception as e:
            logger.error(f"复制现有段落失败: {e}")

    # 🔧 已移除：旧的数量不匹配检测对话框，已升级为智能同步检测
    # 新的智能同步检测功能在 _trigger_intelligent_sync_check 方法中实现

    # 🔧 新增：音效生成相关方法
    def generate_selected_sound_effects(self):
        """批量生成选中镜头的音效"""
        try:
            # 获取所有选中的文本段落
            selected_segments = []
            for i in range(self.text_table.rowCount()):
                checkbox = self.text_table.cellWidget(i, 0)
                if checkbox and isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                    segment = self.voice_segments[i].copy()  # 复制segment避免修改原数据
                    # 只处理有音效描述的段落
                    if segment.get('sound_effect', '').strip():
                        # 🔧 修复：保存原始索引信息
                        segment['original_index'] = i
                        selected_segments.append(segment)

            if not selected_segments:
                QMessageBox.warning(self, "警告", "请至少选择一个有音效描述的文本段落")
                return

            logger.info(f"开始批量生成音效，共{len(selected_segments)}个镜头")
            self.start_sound_effect_generation(selected_segments)

        except Exception as e:
            logger.error(f"批量生成音效失败: {e}")
            QMessageBox.critical(self, "错误", f"生成失败: {e}")

    def generate_single_sound_effect(self, segment_index):
        """生成单个镜头的音效"""
        try:
            if 0 <= segment_index < len(self.voice_segments):
                segment = self.voice_segments[segment_index].copy()  # 复制segment避免修改原数据
                sound_effect = segment.get('sound_effect', '').strip()

                if not sound_effect:
                    QMessageBox.warning(self, "警告", "该镜头没有音效描述")
                    return

                # 🔧 修复：在segment中保存原始索引信息
                segment['original_index'] = segment_index
                logger.info(f"开始生成音效: 镜头索引{segment_index}, shot_id={segment.get('shot_id')}")

                self.start_sound_effect_generation([segment])
            else:
                QMessageBox.warning(self, "警告", "无效的镜头索引")
        except Exception as e:
            logger.error(f"生成单个音效失败: {e}")
            QMessageBox.critical(self, "错误", f"生成失败: {e}")

    def start_sound_effect_generation(self, segments):
        """开始音效生成"""
        try:
            # 获取输出目录
            output_dir = self.get_sound_effect_output_dir()
            if not output_dir:
                return

            # 启动音效生成线程
            self.sound_effect_thread = SoundEffectGenerationThread(segments, output_dir)
            self.sound_effect_thread.progress_updated.connect(self.on_sound_effect_progress)
            self.sound_effect_thread.sound_effect_generated.connect(self.on_sound_effect_generated)
            self.sound_effect_thread.error_occurred.connect(self.on_sound_effect_error)
            self.sound_effect_thread.finished.connect(self.on_sound_effect_finished)
            self.sound_effect_thread.start()

            # 更新UI状态
            self.progress_bar.setVisible(True)
            self.generate_sound_effects_btn.setEnabled(False)

        except Exception as e:
            logger.error(f"启动音效生成失败: {e}")
            QMessageBox.critical(self, "错误", f"启动失败: {e}")

    def get_sound_effect_output_dir(self):
        """获取音效输出目录"""
        try:
            # 确保音频文件管理器已初始化
            if not self.audio_file_manager:
                self._ensure_audio_file_manager()

            if not self.audio_file_manager:
                QMessageBox.warning(self, "警告", "无法初始化音频文件管理器，请检查项目是否已加载")
                return None

            # 获取项目根目录
            project_root = self.project_manager.current_project.get('project_dir') or self.project_manager.current_project.get('project_root')
            if not project_root:
                QMessageBox.warning(self, "警告", "无法获取项目根目录")
                return None

            # 🔧 修复：正确的音效输出目录路径，直接在项目根目录下的audio文件夹
            # 因为project_root已经是 output/项目名/ 这个路径了
            output_dir = os.path.join(project_root, "audio")
            os.makedirs(output_dir, exist_ok=True)

            return output_dir

        except Exception as e:
            logger.error(f"获取音效输出目录失败: {e}")
            QMessageBox.critical(self, "错误", f"获取输出目录失败: {e}")
            return None

    def on_sound_effect_progress(self, progress, message):
        """音效生成进度更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def on_sound_effect_generated(self, result):
        """单个音效生成完成"""
        try:
            # 🔧 修复：通过scene_id和shot_id的组合精确找到正确的段落索引
            shot_id = result.get('shot_id')
            audio_path = result.get('audio_path')

            # 从result中获取scene_id，如果没有则尝试从segment_index推断
            scene_id = result.get('scene_id')
            segment_index = result.get('segment_index')

            # 查找匹配的段落
            target_segment_index = None

            # 方法1：通过scene_id和shot_id精确匹配
            if scene_id and shot_id:
                for i, segment in enumerate(self.voice_segments):
                    if (segment.get('scene_id') == scene_id and
                        segment.get('shot_id') == shot_id):
                        target_segment_index = i
                        logger.info(f"音效精确匹配找到段落: scene_id='{scene_id}', shot_id='{shot_id}', 索引={i}")
                        break

            # 方法2：如果精确匹配失败，使用segment_index作为备用
            if target_segment_index is None and segment_index is not None:
                if 0 <= segment_index < len(self.voice_segments):
                    target_segment_index = segment_index
                    segment = self.voice_segments[segment_index]
                    logger.warning(f"音效使用segment_index备用匹配: 索引={segment_index}, scene_id='{segment.get('scene_id')}', shot_id='{segment.get('shot_id')}'")
                else:
                    logger.error(f"音效segment_index超出范围: {segment_index}, 总段落数: {len(self.voice_segments)}")
                    return

            # 方法3：如果都失败，尝试只通过shot_id匹配（可能不准确）
            if target_segment_index is None:
                for i, segment in enumerate(self.voice_segments):
                    if segment.get('shot_id') == shot_id:
                        target_segment_index = i
                        logger.warning(f"音效仅通过shot_id匹配（可能不准确）: shot_id='{shot_id}', 索引={i}")
                        break

            if target_segment_index is None:
                logger.error(f"无法找到匹配的音效段落: scene_id='{scene_id}', shot_id='{shot_id}', segment_index={segment_index}")
                return

            # 更新段落状态
            self.voice_segments[target_segment_index]['sound_effect_path'] = audio_path

            # 更新表格显示 - 在状态列显示音效状态
            current_status = self.text_table.item(target_segment_index, 7)
            if current_status:
                status_text = current_status.text()
                if '音效已生成' not in status_text:
                    new_status = status_text + ' | 音效已生成' if status_text != '未生成' else '音效已生成'
                    current_status.setText(new_status)

            # 🔧 重新创建操作按钮以反映新状态
            self._update_row_buttons(target_segment_index)

            logger.info(f"音效生成完成: scene_id='{scene_id}', shot_id='{shot_id}' (索引{target_segment_index}) -> {audio_path}")

        except Exception as e:
            logger.error(f"处理音效生成结果失败: {e}")

    def on_sound_effect_error(self, error_msg):
        """音效生成错误"""
        logger.error(f"音效生成错误: {error_msg}")
        self.status_label.setText(f"音效生成错误: {error_msg}")

    def on_sound_effect_finished(self):
        """音效生成完成"""
        self.progress_bar.setVisible(False)
        self.generate_sound_effects_btn.setEnabled(True)
        self.status_label.setText("音效生成完成")

        # 保存到项目
        self.save_to_project()

    def send_to_image_generation(self):
        """发送配音数据到图像生成界面（配音优先工作流程）"""
        try:
            # 检查是否有已生成的配音
            generated_segments = [seg for seg in self.voice_segments if seg.get('status') == '已生成']

            if not generated_segments:
                QMessageBox.warning(self, "警告", "没有已生成的配音数据可以发送")
                return

            # 确认发送
            reply = QMessageBox.question(
                self, "确认发送",
                f"即将发送 {len(generated_segments)} 个配音段落到图像生成界面。\n\n"
                "这将启动配音优先工作流程，根据配音内容和时长\n"
                "自动计算图像生成需求。\n\n"
                "是否继续？"
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # 准备发送的数据
            voice_data_for_image = []
            for segment in generated_segments:
                voice_data = {
                    'index': segment.get('index', 0),
                    'scene_id': segment.get('scene_id', ''),
                    'shot_id': segment.get('shot_id', ''),
                    'dialogue_text': segment.get('dialogue_text', ''),
                    'audio_path': segment.get('audio_path', ''),
                    'content_type': segment.get('content_type', '旁白'),
                    'sound_effect': segment.get('sound_effect', ''),
                    'status': segment.get('status', ''),
                    'storyboard_description': segment.get('storyboard_description', ''),
                    'original_text': segment.get('original_text', '')
                }
                voice_data_for_image.append(voice_data)

            # 发送信号到主界面，切换到图像生成标签页
            if hasattr(self.parent(), 'switch_to_image_generation_with_voice_data'):
                self.parent().switch_to_image_generation_with_voice_data(voice_data_for_image)

                # 显示成功消息
                QMessageBox.information(
                    self, "发送成功",
                    f"已成功发送 {len(voice_data_for_image)} 个配音段落到图像生成界面。\n\n"
                    "程序已切换到图像生成界面，请查看配音优先模式的图像生成设置。"
                )
            else:
                # 降级方案：直接调用图像生成界面
                logger.warning("主界面不支持配音优先切换，尝试直接调用")
                QMessageBox.information(
                    self, "数据已准备",
                    f"配音数据已准备完成（{len(voice_data_for_image)} 个段落）。\n\n"
                    "请手动切换到图像生成界面查看。"
                )

            logger.info(f"成功发送 {len(voice_data_for_image)} 个配音段落到图像生成")

        except Exception as e:
            logger.error(f"发送配音数据到图像生成失败: {e}")
            QMessageBox.critical(self, "错误", f"发送失败: {str(e)}")

    def generate_voice_driven_storyboard(self):
        """生成配音驱动的五阶段分镜"""
        try:
            # 检查是否有已生成的配音
            generated_segments = [seg for seg in self.voice_segments if seg.get('status') == '已生成']

            if not generated_segments:
                QMessageBox.warning(self, "警告", "没有已生成的配音数据可用于分镜生成")
                return

            # 确认操作
            reply = QMessageBox.question(
                self, "确认生成",
                f"即将基于 {len(generated_segments)} 个配音段落生成全新的五阶段分镜。\n\n"
                "这将：\n"
                "1. 分析配音内容，智能分割场景\n"
                "2. 重新生成五阶段分镜数据\n"
                "3. 确保分镜与配音内容完全一致\n\n"
                "注意：这将覆盖现有的五阶段分镜数据！\n\n"
                "是否继续？"
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # 显示进度
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 不确定进度
            self.voice_driven_storyboard_btn.setEnabled(False)
            self.status_label.setText("正在生成配音驱动分镜...")

            # 导入配音驱动分镜系统
            from src.core.voice_driven_storyboard import VoiceDrivenStoryboardSystem

            # 创建配音驱动分镜系统
            voice_driven_system = VoiceDrivenStoryboardSystem(self.project_manager)

            # 加载配音数据
            if not voice_driven_system.load_voice_data(generated_segments):
                QMessageBox.critical(self, "错误", "加载配音数据失败")
                return

            self.status_label.setText("正在分析配音内容...")

            # 分析配音驱动的场景
            if not voice_driven_system.analyze_voice_driven_scenes():
                QMessageBox.critical(self, "错误", "配音场景分析失败")
                return

            self.status_label.setText("正在生成五阶段分镜数据...")

            # 生成配音驱动的分镜数据
            if not voice_driven_system.generate_voice_driven_storyboard():
                QMessageBox.critical(self, "错误", "生成配音驱动分镜失败")
                return

            self.status_label.setText("正在保存分镜数据...")

            # 保存配音驱动的分镜数据
            if not voice_driven_system.save_voice_driven_storyboard():
                QMessageBox.critical(self, "错误", "保存配音驱动分镜失败")
                return

            # 完成
            self.progress_bar.setVisible(False)
            self.voice_driven_storyboard_btn.setEnabled(True)

            # 显示成功信息
            scenes_count = len(voice_driven_system.voice_driven_scenes)
            total_duration = sum(scene.total_duration for scene in voice_driven_system.voice_driven_scenes)

            QMessageBox.information(
                self, "生成成功",
                f"配音驱动的五阶段分镜生成完成！\n\n"
                f"📊 统计信息：\n"
                f"• 配音段落：{len(generated_segments)} 个\n"
                f"• 智能场景：{scenes_count} 个\n"
                f"• 总时长：{total_duration:.1f} 秒\n\n"
                f"现在可以切换到五阶段分镜界面查看结果，\n"
                f"或直接进行图像生成。"
            )

            self.status_label.setText(f"配音驱动分镜生成完成：{scenes_count}个场景，{len(generated_segments)}个段落")

            # 通知主界面更新
            if hasattr(self.parent(), 'refresh_five_stage_storyboard'):
                self.parent().refresh_five_stage_storyboard()

            logger.info(f"配音驱动分镜生成成功：{scenes_count}个场景，{len(generated_segments)}个段落")

        except Exception as e:
            # 恢复界面状态
            self.progress_bar.setVisible(False)
            self.voice_driven_storyboard_btn.setEnabled(True)
            self.status_label.setText("配音驱动分镜生成失败")

            logger.error(f"生成配音驱动分镜失败: {e}")
            QMessageBox.critical(self, "错误", f"生成失败: {str(e)}")

    def update_status_label(self):
        """更新状态标签"""
        try:
            total_segments = len(self.voice_segments)
            generated_count = len([seg for seg in self.voice_segments if seg.get('status') == '已生成'])

            self.status_label.setText(f"配音状态: {generated_count}/{total_segments} 已生成")

            # 🔧 更新按钮状态
            self.voice_driven_storyboard_btn.setEnabled(generated_count > 0)

        except Exception as e:
            logger.error(f"更新状态标签失败: {e}")
            self.status_label.setText("状态更新失败")

    def _generate_subtitles_for_segments(self):
        """🔧 新增：为配音段落生成字幕文件"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_root = self.project_manager.current_project.get('project_dir')
            if not project_root:
                return

            # 导入字幕生成器
            from src.utils.subtitle_generator import SubtitleGenerator
            subtitle_generator = SubtitleGenerator(project_root)

            # 只为已生成配音的段落生成字幕
            segments_with_audio = [s for s in self.voice_segments
                                 if s.get('status') == '已生成' and s.get('audio_path')]

            if not segments_with_audio:
                logger.info("没有已生成配音的段落，跳过字幕生成")
                return

            logger.info(f"开始为 {len(segments_with_audio)} 个配音段落生成字幕")

            # 批量生成字幕
            results = subtitle_generator.batch_generate_subtitles(segments_with_audio, "srt")

            if results['success_count'] > 0:
                logger.info(f"字幕生成完成: 成功 {results['success_count']} 个，失败 {results['failed_count']} 个")

                # 更新voice_segments中的字幕信息
                for segment in segments_with_audio:
                    if segment.get('subtitle_path'):
                        # 同时生成JSON格式的字幕数据用于项目数据存储
                        json_subtitle_path = subtitle_generator.generate_subtitle_from_voice_segment(segment, "json")
                        if json_subtitle_path:
                            segment['subtitle_data_path'] = json_subtitle_path
                            self._update_segment_subtitle_info(segment, segment['subtitle_path'])
            else:
                logger.warning("字幕生成失败")

        except Exception as e:
            logger.error(f"生成字幕失败: {e}")

    def _update_segment_subtitle_info(self, segment: Dict[str, Any], subtitle_path: str):
        """🔧 新增：更新段落的字幕信息"""
        try:
            segment['subtitle_path'] = subtitle_path
            segment['subtitle_format'] = 'srt'

            # 尝试读取字幕数据
            if subtitle_path and os.path.exists(subtitle_path):
                try:
                    # 如果是JSON格式，直接读取
                    if subtitle_path.endswith('.json'):
                        with open(subtitle_path, 'r', encoding='utf-8') as f:
                            subtitle_json = json.load(f)
                            segment['subtitle_data'] = subtitle_json.get('subtitles', [])
                    else:
                        # 对于SRT格式，生成简单的时间轴数据
                        segment['subtitle_data'] = self._parse_srt_to_data(subtitle_path)

                except Exception as e:
                    logger.debug(f"读取字幕数据失败: {e}")

        except Exception as e:
            logger.error(f"更新段落字幕信息失败: {e}")

    def _parse_srt_to_data(self, srt_path: str) -> List[Dict[str, Any]]:
        """🔧 新增：解析SRT文件为数据格式"""
        try:
            subtitle_data = []

            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # 简单的SRT解析
            blocks = content.split('\n\n')

            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    index = lines[0]
                    time_line = lines[1]
                    text = '\n'.join(lines[2:])

                    # 解析时间
                    if ' --> ' in time_line:
                        start_str, end_str = time_line.split(' --> ')
                        subtitle_data.append({
                            'index': int(index) if index.isdigit() else len(subtitle_data) + 1,
                            'start_time_str': start_str.strip(),
                            'end_time_str': end_str.strip(),
                            'text': text.strip()
                        })

            return subtitle_data

        except Exception as e:
            logger.error(f"解析SRT文件失败: {e}")
            return []

    def ai_analyze_content(self):
        """AI智能分析旁白内容，自动填充台词和音效"""
        try:
            if not self.voice_segments:
                QMessageBox.warning(self, "警告", "请先导入或输入文本内容！")
                return

            # 检查是否有LLM配置
            if not hasattr(self, 'project_manager') or not self.project_manager:
                QMessageBox.warning(self, "警告", "项目管理器未初始化！")
                return

            # 确认对话框
            reply = QMessageBox.question(
                self, "AI智能分析",
                "AI将分析旁白内容，自动识别台词和音效。\n\n"
                "这将覆盖现有的台词和音效内容，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # 显示进度对话框
            progress_dialog = QProgressDialog("AI正在分析内容...", "取消", 0, len(self.voice_segments), self)
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.show()

            analyzed_count = 0

            for i, segment in enumerate(self.voice_segments):
                if progress_dialog.wasCanceled():
                    break

                progress_dialog.setValue(i)
                progress_dialog.setLabelText(f"正在分析第 {i+1}/{len(self.voice_segments)} 个段落...")
                QApplication.processEvents()

                # 获取旁白内容
                narration_text = segment.get('original_text', segment.get('text', ''))
                if not narration_text.strip():
                    continue

                # AI分析
                analysis_result = self._ai_analyze_single_segment(narration_text)
                if analysis_result:
                    # 更新段落数据
                    if analysis_result.get('dialogue'):
                        segment['dialogue_text'] = analysis_result['dialogue']
                        segment['content_type'] = '台词'
                    else:
                        segment['content_type'] = '旁白'

                    if analysis_result.get('sound_effect'):
                        segment['sound_effect'] = analysis_result['sound_effect']

                    analyzed_count += 1

            progress_dialog.close()

            # 更新表格显示
            self.update_text_table()

            # 显示结果
            QMessageBox.information(
                self, "分析完成",
                f"AI智能分析完成！\n\n"
                f"成功分析 {analyzed_count} 个段落\n"
                f"已自动填充台词和音效内容"
            )

            logger.info(f"AI智能分析完成，分析了 {analyzed_count} 个段落")

        except Exception as e:
            logger.error(f"AI智能分析失败: {e}")
            QMessageBox.critical(self, "错误", f"AI分析失败: {e}")

    def _ai_analyze_single_segment(self, narration_text):
        """AI分析单个段落"""
        try:
            # 构建分析提示词
            prompt = f"""
请分析以下旁白内容，识别其中的台词和音效：

旁白内容：
{narration_text}

请按照以下格式返回JSON：
{{
    "dialogue": "如果有台词，提取完整的对话内容；如果没有台词，返回空字符串",
    "sound_effect": "描述适合的音效，如：脚步声、开门声、背景音乐等；如果不需要音效，返回空字符串"
}}

分析要求：
1. 台词：提取直接引语或对话内容
2. 音效：根据场景描述推荐合适的音效
3. 返回标准JSON格式
"""

            # 调用LLM
            if hasattr(self.project_manager, 'llm_manager') and self.project_manager.llm_manager:
                response = self.project_manager.llm_manager.generate_response(prompt)

                # 解析JSON响应
                import json
                try:
                    # 提取JSON部分
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response[json_start:json_end]
                        result = json.loads(json_str)
                        return result
                except json.JSONDecodeError:
                    logger.warning(f"AI响应JSON解析失败: {response}")
                    return None
        except Exception as e:
            logger.error(f"智能分割失败: {e}")
            return None

    def save_voice_settings_to_project(self):
        """保存配音设置到项目"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_data = self.project_manager.current_project

            # 兼容不同的项目数据结构
            if hasattr(project_data, 'data'):
                data = project_data.data
            else:
                if "data" not in project_data:
                    project_data["data"] = {}
                data = project_data["data"]

            # 确保配音设置结构存在
            if "voice_generation" not in data:
                data["voice_generation"] = {"segments": [], "settings": {}}
            if "settings" not in data["voice_generation"]:
                data["voice_generation"]["settings"] = {}

            settings = data["voice_generation"]["settings"]

            # 保存所有配音设置
            if hasattr(self, 'engine_combo'):
                current_engine_data = self.engine_combo.currentData()
                if current_engine_data:
                    settings["engine"] = current_engine_data
                else:
                    settings["engine"] = "edge_tts"

            if hasattr(self, 'voice_combo'):
                settings["voice"] = self.voice_combo.currentText()

            if hasattr(self, 'speed_slider'):
                settings["speed"] = self.speed_slider.value() / 100.0  # 转换为倍数

            if hasattr(self, 'pitch_slider'):
                settings["pitch"] = self.pitch_slider.value() / 100.0

            if hasattr(self, 'volume_slider'):
                settings["volume"] = self.volume_slider.value() / 100.0

            if hasattr(self, 'target_duration'):
                settings["segment_duration"] = self.target_duration

            # 标记项目已修改
            if hasattr(self.project_manager, 'mark_project_modified'):
                self.project_manager.mark_project_modified()

            logger.info("配音设置已保存到项目")
        except Exception as e:
            logger.error(f"保存配音设置到项目失败: {e}")

    def load_voice_settings_from_project(self):
        """从项目设置中加载配音设置"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                logger.info("无项目，使用默认配音设置")
                return

            project_data = self.project_manager.current_project

            # 兼容不同的项目数据结构
            if hasattr(project_data, 'data'):
                data = project_data.data
            else:
                data = project_data.get("data", project_data)

            voice_settings = data.get("voice_generation", {}).get("settings", {})

            if not voice_settings:
                logger.info("项目中无配音设置，使用默认设置")
                return

            # 阻止信号触发，避免在加载时保存设置
            self.block_voice_signals(True)

            # 加载引擎设置
            if hasattr(self, 'engine_combo') and "engine" in voice_settings:
                engine = voice_settings["engine"]
                for i in range(self.engine_combo.count()):
                    if self.engine_combo.itemData(i) == engine:
                        self.engine_combo.setCurrentIndex(i)
                        break

            # 加载音色设置
            if hasattr(self, 'voice_combo') and "voice" in voice_settings:
                voice = voice_settings["voice"]
                # 先触发引擎改变以加载音色列表
                self.on_engine_changed()
                # 然后设置音色
                for i in range(self.voice_combo.count()):
                    if self.voice_combo.itemText(i) == voice:
                        self.voice_combo.setCurrentIndex(i)
                        break

            # 加载语速设置
            if hasattr(self, 'speed_slider') and "speed" in voice_settings:
                speed_value = int(voice_settings["speed"] * 100)  # 转换为百分比
                self.speed_slider.setValue(speed_value)
                if hasattr(self, 'speed_label'):
                    self.speed_label.setText(f"{speed_value}%")

            # 加载音调设置
            if hasattr(self, 'pitch_slider') and "pitch" in voice_settings:
                pitch_value = int(voice_settings["pitch"] * 100)
                self.pitch_slider.setValue(pitch_value)

            # 加载音量设置
            if hasattr(self, 'volume_slider') and "volume" in voice_settings:
                volume_value = int(voice_settings["volume"] * 100)
                self.volume_slider.setValue(volume_value)

            # 加载段落时长设置
            if "segment_duration" in voice_settings:
                self.target_duration = voice_settings["segment_duration"]

            # 恢复信号
            self.block_voice_signals(False)

            logger.info("从项目设置加载配音设置")

        except Exception as e:
            logger.error(f"加载项目配音设置失败: {e}")
            self.block_voice_signals(False)

    def block_voice_signals(self, block: bool):
        """阻止或恢复配音UI组件信号"""
        components = [
            'engine_combo', 'voice_combo', 'speed_slider',
            'pitch_slider', 'volume_slider'
        ]

        for component_name in components:
            if hasattr(self, component_name):
                component = getattr(self, component_name)
                if hasattr(component, 'blockSignals'):
                    component.blockSignals(block)

    def on_voice_settings_changed(self):
        """配音设置改变时的处理"""
        try:
            # 保存设置到项目
            self.save_voice_settings_to_project()
        except Exception as e:
            logger.error(f"处理配音设置改变失败: {e}")

    def on_project_loaded(self):
        """项目加载时的处理"""
        try:
            # 重新加载配音设置
            self.load_voice_settings_from_project()

            logger.info("项目加载完成，已重新加载配音设置")
        except Exception as e:
            logger.error(f"处理项目加载失败: {e}")

            return None

        except Exception as e:
            logger.error(f"AI分析单个段落失败: {e}")
            return None
