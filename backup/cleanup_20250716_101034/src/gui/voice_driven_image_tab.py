#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配音时长生图标签页
基于配音数据生成图像的专用界面
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QTextEdit, QSplitter, QHeaderView, QCheckBox,
    QMessageBox, QProgressBar, QFrame, QGroupBox, QComboBox, QSpinBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont

logger = logging.getLogger(__name__)

class VoiceDrivenImageTab(QWidget):
    """配音时长生图标签页"""
    
    # 信号定义
    image_generation_started = pyqtSignal()
    image_generation_completed = pyqtSignal(dict)
    image_generation_failed = pyqtSignal(str)
    
    def __init__(self, app_controller, project_manager, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.project_manager = project_manager
        self.parent_window = parent

        # 数据存储
        self.voice_segments_data = []
        self.generation_settings = {}

        # 🔧 新增：一致性数据管理
        self.character_scene_data = {}
        self.consistency_prompts = {}

        # 初始化界面
        self.init_ui()
        self.load_voice_data()

        # 🔧 新增：加载一致性数据
        self._load_consistency_data()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题和说明
        self.create_header(layout)
        
        # 主要内容区域
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：配音段落表格
        left_widget = self.create_voice_segments_table()
        splitter.addWidget(left_widget)
        
        # 右侧：详情和设置
        right_widget = self.create_details_panel()
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setSizes([600, 400])
        layout.addWidget(splitter)
        
        # 底部：操作按钮和状态
        self.create_bottom_panel(layout)
        
    def create_header(self, layout):
        """创建标题区域"""
        header_frame = QFrame()
        header_frame.setStyleSheet("QFrame { background-color: #f0f8ff; border: 1px solid #ddd; border-radius: 5px; }")
        header_layout = QVBoxLayout(header_frame)
        
        # 标题
        title_label = QLabel("🎵 配音时长生图")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # 说明文字
        desc_label = QLabel(
            "基于配音段落的时长和内容生成对应的图像。\n"
            "• 短配音（<3秒）：生成1张图像\n"
            "• 长配音（≥3秒）：生成2-3张图像\n"
            "• 图像内容与配音内容匹配"
        )
        desc_label.setStyleSheet("color: #666; margin: 5px 0;")
        header_layout.addWidget(desc_label)
        
        layout.addWidget(header_frame)
        
    def create_voice_segments_table(self):
        """创建配音段落表格"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 表格标题
        title_label = QLabel("📋 配音段落列表")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 创建表格
        self.voice_table = QTableWidget()
        self.voice_table.setColumnCount(6)
        self.voice_table.setHorizontalHeaderLabels([
            "选择", "场景", "段落", "配音内容", "时长(秒)", "图像数量"
        ])
        
        # 设置表格属性
        header = self.voice_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # 选择列
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 场景列
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 段落列
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # 配音内容列
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 时长列
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 图像数量列
        
        self.voice_table.setColumnWidth(0, 50)
        self.voice_table.setAlternatingRowColors(True)
        self.voice_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # 连接信号
        self.voice_table.cellClicked.connect(self.on_voice_segment_selected)
        
        layout.addWidget(self.voice_table)
        
        return widget
        
    def create_details_panel(self):
        """创建详情面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 当前段落详情
        details_group = QGroupBox("📝 段落详情")
        details_layout = QVBoxLayout(details_group)
        
        # 配音内容显示
        self.voice_content_text = QTextEdit()
        self.voice_content_text.setMaximumHeight(100)
        self.voice_content_text.setPlaceholderText("选择一个配音段落查看详情...")
        self.voice_content_text.setReadOnly(True)
        details_layout.addWidget(QLabel("配音内容:"))
        details_layout.addWidget(self.voice_content_text)
        
        # 生成的图像提示词
        self.image_prompts_text = QTextEdit()
        self.image_prompts_text.setMaximumHeight(120)
        self.image_prompts_text.setPlaceholderText("将根据配音内容自动生成图像提示词...")
        details_layout.addWidget(QLabel("图像提示词:"))
        details_layout.addWidget(self.image_prompts_text)
        
        layout.addWidget(details_group)
        
        # 生成设置
        settings_group = QGroupBox("⚙️ 生成设置")
        settings_layout = QVBoxLayout(settings_group)
        
        # 图像引擎选择
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("图像引擎:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["ComfyUI", "PollinationsAI", "StableDiffusion"])
        engine_layout.addWidget(self.engine_combo)
        engine_layout.addStretch()
        settings_layout.addLayout(engine_layout)
        
        # 图像质量设置
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("图像质量:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["标准", "高质量", "超高质量"])
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        settings_layout.addLayout(quality_layout)
        
        layout.addWidget(settings_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        return widget
        
    def create_bottom_panel(self, layout):
        """创建底部操作面板"""
        bottom_frame = QFrame()
        bottom_layout = QVBoxLayout(bottom_frame)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        # 刷新数据按钮
        self.refresh_btn = QPushButton("🔄 刷新配音数据")
        self.refresh_btn.clicked.connect(self.load_voice_data)
        button_layout.addWidget(self.refresh_btn)
        
        # 全选/取消全选
        self.select_all_btn = QPushButton("☑️ 全选")
        self.select_all_btn.clicked.connect(self.select_all_segments)
        button_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("☐ 取消全选")
        self.deselect_all_btn.clicked.connect(self.deselect_all_segments)
        button_layout.addWidget(self.deselect_all_btn)
        
        button_layout.addStretch()
        
        # 生成按钮
        self.generate_btn = QPushButton("🎨 生成选中图像")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_selected_images)
        button_layout.addWidget(self.generate_btn)
        
        bottom_layout.addLayout(button_layout)
        
        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; padding: 5px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        status_layout.addWidget(self.progress_bar)
        
        bottom_layout.addLayout(status_layout)
        
        layout.addWidget(bottom_frame)
        
    def load_voice_data(self, voice_data_list=None):
        """🔧 增强：加载配音数据，支持直接传入数据或从项目加载"""
        try:
            if voice_data_list:
                # 直接使用传入的配音数据（来自信号）
                self._process_voice_data_from_signal(voice_data_list)
                return

            if not self.project_manager or not self.project_manager.current_project:
                self.status_label.setText("请先加载项目")
                return

            project_data = self.project_manager.get_project_data()
            if not project_data:
                self.status_label.setText("项目数据为空")
                return

            # 🔧 优先使用专门为图像生成准备的配音数据
            voice_data = project_data.get('voice_generation', {})
            voice_segments = voice_data.get('voice_segments_for_image', [])

            # 如果没有专门的图像生成数据，使用普通配音数据
            if not voice_segments:
                voice_segments = voice_data.get('voice_segments', [])

            if not voice_segments:
                self.status_label.setText("未找到配音数据，请先生成配音")
                self.voice_segments_data = []
                self.update_voice_table()
                return

            # 处理配音数据
            self.voice_segments_data = []
            for i, segment in enumerate(voice_segments):
                # 🔧 增强：获取音频时长信息
                duration = segment.get('audio_duration', segment.get('duration', 0))
                if duration == 0 and segment.get('audio_path'):
                    duration = self._get_audio_duration(segment.get('audio_path'))

                # 🔧 增强：使用智能图像数量计算
                image_count = segment.get('suggested_image_count', self._calculate_image_count(duration))

                # 🔧 增强：提取配音内容
                voice_content = (segment.get('voice_content') or
                               segment.get('dialogue_content') or
                               segment.get('original_text') or
                               segment.get('text', ''))

                segment_data = {
                    'index': i,
                    'scene_id': segment.get('scene_id', f'场景{i+1}'),
                    'segment_id': segment.get('segment_id', f'段落{i+1}'),
                    'voice_content': voice_content,
                    'duration': duration,
                    'image_count': image_count,
                    'selected': False,
                    'image_prompts': [],
                    'generated_images': [],
                    'audio_path': segment.get('audio_path', ''),
                    'content_type': segment.get('content_type', '旁白')
                }
                self.voice_segments_data.append(segment_data)

            self.update_voice_table()
            self.status_label.setText(f"已加载 {len(self.voice_segments_data)} 个配音段落")

        except Exception as e:
            logger.error(f"加载配音数据失败: {e}")
            self.status_label.setText(f"加载失败: {str(e)}")

    def _process_voice_data_from_signal(self, voice_data_list):
        """🔧 新增：处理来自信号的配音数据"""
        try:
            logger.info(f"接收到配音数据信号，包含 {len(voice_data_list)} 个段落")

            self.voice_segments_data = []
            for i, segment in enumerate(voice_data_list):
                duration = segment.get('audio_duration', 3.0)
                image_count = segment.get('suggested_image_count', self._calculate_image_count(duration))

                segment_data = {
                    'index': i,
                    'scene_id': segment.get('scene_id', f'场景{i+1}'),
                    'segment_id': segment.get('shot_id', f'段落{i+1}'),
                    'voice_content': segment.get('voice_content', ''),
                    'duration': duration,
                    'image_count': image_count,
                    'selected': True,  # 默认选中
                    'image_prompts': [],
                    'generated_images': [],
                    'audio_path': segment.get('audio_path', ''),
                    'content_type': segment.get('content_type', '旁白')
                }
                self.voice_segments_data.append(segment_data)

            self.update_voice_table()
            self.status_label.setText(f"已接收配音数据：{len(self.voice_segments_data)} 个段落")

            # 🔧 新增：自动生成图像提示词
            self._auto_generate_all_prompts()

        except Exception as e:
            logger.error(f"处理配音数据信号失败: {e}")

    def _load_consistency_data(self):
        """🔧 新增：加载角色场景一致性数据"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有项目数据，无法加载一致性信息")
                return

            project_data = self.project_manager.get_project_data()
            if not project_data:
                return

            # 从五阶段数据中获取角色场景信息
            five_stage_data = project_data.get('five_stage_storyboard', {})
            stage_data = five_stage_data.get('stage_data', {})

            # 获取角色数据（阶段2）
            stage2_data = stage_data.get('2', {})
            character_scene_data = stage2_data.get('character_scene_data', {})

            if character_scene_data:
                self.character_scene_data = character_scene_data
                logger.info(f"加载角色场景数据：{len(character_scene_data.get('characters', {}))} 个角色")

            # 获取场景分析数据（阶段3）
            stage3_data = stage_data.get('3', {})
            scenes_analysis = stage3_data.get('scenes_analysis', '')

            if scenes_analysis:
                self._parse_scenes_consistency(scenes_analysis)

            # 获取增强描述数据
            enhanced_descriptions = project_data.get('enhanced_descriptions', {})
            if enhanced_descriptions:
                self._load_enhanced_descriptions(enhanced_descriptions)

            logger.info("一致性数据加载完成")

        except Exception as e:
            logger.error(f"加载一致性数据失败: {e}")

    def _parse_scenes_consistency(self, scenes_analysis: str):
        """解析场景一致性信息"""
        try:
            # 简单解析场景分析文本，提取关键信息
            lines = scenes_analysis.split('\n')
            current_scene = None

            for line in lines:
                line = line.strip()
                if '场景' in line and '：' in line:
                    current_scene = line.split('：')[0].strip()
                elif current_scene and ('环境' in line or '背景' in line or '设定' in line):
                    if current_scene not in self.consistency_prompts:
                        self.consistency_prompts[current_scene] = {}
                    self.consistency_prompts[current_scene]['scene_setting'] = line.strip()

        except Exception as e:
            logger.error(f"解析场景一致性失败: {e}")

    def _load_enhanced_descriptions(self, enhanced_descriptions: dict):
        """加载增强描述数据"""
        try:
            scenes = enhanced_descriptions.get('scenes', [])
            for scene in scenes:
                scene_name = scene.get('scene_name', '')
                if scene_name:
                    if scene_name not in self.consistency_prompts:
                        self.consistency_prompts[scene_name] = {}

                    # 提取角色一致性描述
                    shots = scene.get('shots', [])
                    for shot in shots:
                        content = shot.get('content', '')
                        if content and '角色' in content:
                            self.consistency_prompts[scene_name]['character_consistency'] = content
                            break

        except Exception as e:
            logger.error(f"加载增强描述失败: {e}")

    def _get_audio_duration(self, audio_path: str) -> float:
        """🔧 新增：获取音频文件时长"""
        try:
            if not audio_path or not os.path.exists(audio_path):
                return 3.0

            # 简单的文件大小估算
            file_size = os.path.getsize(audio_path)
            estimated_duration = file_size / (128 * 1024 / 8)  # 假设128kbps
            return max(1.0, float(estimated_duration))
        except:
            return 3.0

    def _calculate_image_count(self, duration: float) -> int:
        """🔧 新增：基于时长计算图像数量"""
        if duration < 3:
            return 1
        elif duration < 6:
            return 2
        else:
            return min(3, max(2, int(duration / 2)))

    def _auto_generate_all_prompts(self):
        """🔧 新增：自动为所有段落生成图像提示词"""
        try:
            for segment in self.voice_segments_data:
                self.generate_image_prompts_for_segment(segment)
            logger.info("已自动生成所有段落的图像提示词")
        except Exception as e:
            logger.error(f"自动生成图像提示词失败: {e}")
            
    def update_voice_table(self):
        """更新配音表格显示"""
        self.voice_table.setRowCount(len(self.voice_segments_data))
        
        for row, segment in enumerate(self.voice_segments_data):
            # 选择复选框
            checkbox = QCheckBox()
            checkbox.setChecked(segment['selected'])
            checkbox.stateChanged.connect(
                lambda state, r=row: self.on_checkbox_changed(r, state)
            )
            self.voice_table.setCellWidget(row, 0, checkbox)
            
            # 场景
            self.voice_table.setItem(row, 1, QTableWidgetItem(segment['scene_id']))
            
            # 段落
            self.voice_table.setItem(row, 2, QTableWidgetItem(segment['segment_id']))
            
            # 配音内容（截断显示）
            content = segment['voice_content']
            display_content = content[:50] + "..." if len(content) > 50 else content
            self.voice_table.setItem(row, 3, QTableWidgetItem(display_content))
            
            # 时长
            duration_item = QTableWidgetItem(f"{segment['duration']:.1f}")
            duration_item.setTextAlignment(Qt.AlignCenter)
            self.voice_table.setItem(row, 4, duration_item)
            
            # 图像数量
            count_item = QTableWidgetItem(str(segment['image_count']))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.voice_table.setItem(row, 5, count_item)
        
        # 调整行高
        self.voice_table.resizeRowsToContents()
        
    def on_checkbox_changed(self, row, state):
        """复选框状态改变"""
        if 0 <= row < len(self.voice_segments_data):
            self.voice_segments_data[row]['selected'] = state == Qt.Checked
            
    def on_voice_segment_selected(self, row, column):
        """配音段落被选中"""
        if 0 <= row < len(self.voice_segments_data):
            segment = self.voice_segments_data[row]
            
            # 显示配音内容
            self.voice_content_text.setPlainText(segment['voice_content'])
            
            # 生成并显示图像提示词
            self.generate_image_prompts_for_segment(segment)
            
    def generate_image_prompts_for_segment(self, segment):
        """为配音段落生成图像提示词 - 集成一致性信息"""
        try:
            voice_content = segment['voice_content']
            image_count = segment['image_count']
            scene_id = segment.get('scene_id', '')

            # 🔧 新增：获取一致性信息
            consistency_info = self._get_consistency_info_for_segment(segment)

            prompts = []
            for i in range(image_count):
                # 基础提示词
                if image_count == 1:
                    base_prompt = f"基于配音内容的场景：{voice_content}"
                else:
                    base_prompt = f"基于配音内容的场景（第{i+1}部分）：{voice_content}"

                # 🔧 新增：添加一致性信息
                enhanced_prompt = self._enhance_prompt_with_consistency(base_prompt, consistency_info)

                # 添加风格描述
                final_prompt = f"{enhanced_prompt}，动漫风格，高质量，细节丰富"

                prompts.append(final_prompt)

            segment['image_prompts'] = prompts
            segment['consistency_info'] = consistency_info  # 保存一致性信息

            # 显示提示词
            prompts_text = "\n\n".join([f"图像{i+1}:\n{prompt}" for i, prompt in enumerate(prompts)])

            # 🔧 新增：显示一致性信息
            if consistency_info:
                consistency_text = "\n🎨 一致性信息:\n"
                for key, value in consistency_info.items():
                    if value:
                        consistency_text += f"• {key}: {value}\n"
                prompts_text = consistency_text + "\n" + prompts_text

            self.image_prompts_text.setPlainText(prompts_text)

        except Exception as e:
            logger.error(f"生成图像提示词失败: {e}")
            self.image_prompts_text.setPlainText(f"生成提示词失败: {str(e)}")

    def _get_consistency_info_for_segment(self, segment):
        """获取配音段落的一致性信息"""
        try:
            consistency_info = {}
            scene_id = segment.get('scene_id', '')
            voice_content = segment.get('voice_content', '')

            # 获取场景一致性信息
            if scene_id and scene_id in self.consistency_prompts:
                scene_info = self.consistency_prompts[scene_id]
                consistency_info['场景设定'] = scene_info.get('scene_setting', '')
                consistency_info['角色一致性'] = scene_info.get('character_consistency', '')

            # 从角色场景数据中匹配角色
            if self.character_scene_data:
                characters = self.character_scene_data.get('characters', {})
                matched_characters = []

                for char_name, char_info in characters.items():
                    if char_name in voice_content:
                        appearance = char_info.get('appearance', '')
                        if appearance:
                            matched_characters.append(f"{char_name}：{appearance}")

                if matched_characters:
                    consistency_info['角色外观'] = '；'.join(matched_characters)

            return consistency_info

        except Exception as e:
            logger.error(f"获取一致性信息失败: {e}")
            return {}

    def _enhance_prompt_with_consistency(self, base_prompt, consistency_info):
        """使用一致性信息增强提示词"""
        try:
            enhanced_parts = [base_prompt]

            # 添加角色外观描述
            if consistency_info.get('角色外观'):
                enhanced_parts.append(f"角色外观：{consistency_info['角色外观']}")

            # 添加场景设定
            if consistency_info.get('场景设定'):
                enhanced_parts.append(f"场景环境：{consistency_info['场景设定']}")

            # 添加角色一致性描述
            if consistency_info.get('角色一致性'):
                enhanced_parts.append(f"一致性要求：{consistency_info['角色一致性']}")

            return '，'.join(enhanced_parts)

        except Exception as e:
            logger.error(f"增强提示词失败: {e}")
            return base_prompt
            
    def select_all_segments(self):
        """全选配音段落"""
        for i in range(len(self.voice_segments_data)):
            self.voice_segments_data[i]['selected'] = True
            checkbox = self.voice_table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(True)
                
    def deselect_all_segments(self):
        """取消全选配音段落"""
        for i in range(len(self.voice_segments_data)):
            self.voice_segments_data[i]['selected'] = False
            checkbox = self.voice_table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(False)
                
    def generate_selected_images(self):
        """生成选中的图像"""
        selected_segments = [s for s in self.voice_segments_data if s['selected']]
        
        if not selected_segments:
            QMessageBox.warning(self, "警告", "请先选择要生成图像的配音段落")
            return
        
        # 显示确认对话框
        total_images = sum(s['image_count'] for s in selected_segments)
        reply = QMessageBox.question(
            self, "确认生成",
            f"将为 {len(selected_segments)} 个配音段落生成 {total_images} 张图像。\n\n是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.start_image_generation(selected_segments)
            
    def start_image_generation(self, segments):
        """开始图像生成"""
        try:
            # 显示进度
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 不确定进度
            self.generate_btn.setEnabled(False)
            self.status_label.setText("正在生成图像...")
            
            # 发送信号
            self.image_generation_started.emit()
            
            # 这里应该调用实际的图像生成逻辑
            # 暂时模拟生成过程
            QTimer.singleShot(2000, lambda: self.on_generation_completed(segments))
            
        except Exception as e:
            logger.error(f"开始图像生成失败: {e}")
            self.on_generation_failed(str(e))
            
    def on_generation_completed(self, segments):
        """图像生成完成"""
        try:
            # 隐藏进度
            self.progress_bar.setVisible(False)
            self.generate_btn.setEnabled(True)
            
            total_images = sum(s['image_count'] for s in segments)
            self.status_label.setText(f"图像生成完成！共生成 {total_images} 张图像")
            
            # 发送信号
            result = {
                'segments': segments,
                'total_images': total_images,
                'success': True
            }
            self.image_generation_completed.emit(result)
            
        except Exception as e:
            logger.error(f"处理图像生成完成失败: {e}")
            
    def on_generation_failed(self, error):
        """图像生成失败"""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.status_label.setText(f"图像生成失败: {error}")
        self.image_generation_failed.emit(error)
