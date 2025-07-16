#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版视频合成标签页 - 解决启动问题
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox, QSlider,
    QCheckBox, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from src.utils.logger import logger


class SimpleVideoCompositionTab(QWidget):
    """简化版视频合成标签页"""
    
    def __init__(self, project_manager=None):
        super().__init__()
        self.project_manager = project_manager
        self.current_segments = []
        self.background_music_path = ""
        
        # 简化初始化
        self.init_simple_ui()
        logger.info("简化版视频合成页面初始化完成")
    
    def init_simple_ui(self):
        """初始化简化UI界面"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("🎬 视频合成")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 基本设置组
        settings_group = QGroupBox("⚙️ 基本设置")
        settings_layout = QVBoxLayout()
        
        # 输出格式
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("输出格式:"))
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(["MP4", "AVI", "MOV"])
        self.output_format_combo.setCurrentText("MP4")
        format_layout.addWidget(self.output_format_combo)
        settings_layout.addLayout(format_layout)
        
        # 视频质量
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("视频质量:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高质量", "中等质量", "低质量"])
        self.quality_combo.setCurrentText("高质量")
        quality_layout.addWidget(self.quality_combo)
        settings_layout.addLayout(quality_layout)
        
        # 分辨率
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("分辨率:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["1920x1080", "1280x720", "854x480"])
        self.resolution_combo.setCurrentText("1920x1080")
        resolution_layout.addWidget(self.resolution_combo)
        settings_layout.addLayout(resolution_layout)
        
        # 帧率
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("帧率:"))
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setRange(15, 60)
        self.fps_spinbox.setValue(30)
        self.fps_spinbox.setSuffix(" fps")
        fps_layout.addWidget(self.fps_spinbox)
        settings_layout.addLayout(fps_layout)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 转场效果组（简化版）
        transition_group = QGroupBox("🎞️ 转场效果")
        transition_layout = QVBoxLayout()
        
        # 转场模式
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("转场模式:"))
        self.transition_mode_combo = QComboBox()
        self.transition_mode_combo.addItems(["随机转场", "统一转场", "无转场"])
        self.transition_mode_combo.setCurrentText("随机转场")
        mode_layout.addWidget(self.transition_mode_combo)
        transition_layout.addLayout(mode_layout)
        
        # 转场时长
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("转场时长:"))
        self.transition_duration_spinbox = QDoubleSpinBox()
        self.transition_duration_spinbox.setRange(0.1, 3.0)
        self.transition_duration_spinbox.setValue(0.5)
        self.transition_duration_spinbox.setSuffix(" 秒")
        duration_layout.addWidget(self.transition_duration_spinbox)
        transition_layout.addLayout(duration_layout)
        
        transition_group.setLayout(transition_layout)
        layout.addWidget(transition_group)
        
        # 音乐设置组
        music_group = QGroupBox("🎵 背景音乐")
        music_layout = QVBoxLayout()
        
        # 音乐文件
        music_file_layout = QHBoxLayout()
        self.music_path_label = QLabel("未选择音乐文件")
        music_file_layout.addWidget(self.music_path_label)
        
        select_music_btn = QPushButton("选择音乐")
        select_music_btn.clicked.connect(self.select_background_music)
        music_file_layout.addWidget(select_music_btn)
        music_layout.addLayout(music_file_layout)
        
        # 音量控制
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("音量:"))
        self.music_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.music_volume_slider.setRange(0, 100)
        self.music_volume_slider.setValue(30)
        volume_layout.addWidget(self.music_volume_slider)
        
        self.volume_label = QLabel("30%")
        self.music_volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v}%")
        )
        volume_layout.addWidget(self.volume_label)
        music_layout.addLayout(volume_layout)
        
        # 循环播放
        self.loop_music_checkbox = QCheckBox("循环播放")
        self.loop_music_checkbox.setChecked(True)
        music_layout.addWidget(self.loop_music_checkbox)
        
        music_group.setLayout(music_layout)
        layout.addWidget(music_group)
        
        # 预览信息
        preview_group = QGroupBox("📊 预览信息")
        preview_layout = QVBoxLayout()
        
        self.preview_info = QTextEdit()
        self.preview_info.setMaximumHeight(100)
        self.preview_info.setReadOnly(True)
        self.preview_info.setText("请先加载项目数据")
        preview_layout.addWidget(self.preview_info)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 刷新数据")
        refresh_btn.clicked.connect(self.load_project_data)
        button_layout.addWidget(refresh_btn)
        
        compose_btn = QPushButton("🎬 开始合成")
        compose_btn.clicked.connect(self.start_composition)
        button_layout.addWidget(compose_btn)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def select_background_music(self):
        """选择背景音乐"""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择背景音乐", "", "音频文件 (*.mp3 *.wav *.aac *.m4a)"
        )
        if file_path:
            self.background_music_path = file_path
            self.music_path_label.setText(os.path.basename(file_path))
    
    def load_project_data(self):
        """加载项目数据"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                self.preview_info.setText("没有当前项目")
                return
            
            # 简化的数据加载
            project_data = self.project_manager.current_project
            project_name = project_data.get('name', '未知项目')
            
            info_text = f"""
项目: {project_name}
状态: 已加载
输出格式: {self.output_format_combo.currentText()}
视频质量: {self.quality_combo.currentText()}
分辨率: {self.resolution_combo.currentText()}
帧率: {self.fps_spinbox.value()} fps
转场模式: {self.transition_mode_combo.currentText()}
"""
            
            if self.background_music_path:
                info_text += f"背景音乐: {os.path.basename(self.background_music_path)}\n"
            
            self.preview_info.setText(info_text.strip())
            logger.info("项目数据加载完成")
            
        except Exception as e:
            logger.error(f"加载项目数据失败: {e}")
            self.preview_info.setText(f"加载失败: {e}")
    
    def start_composition(self):
        """开始视频合成"""
        from PyQt5.QtWidgets import QMessageBox
        
        if not self.project_manager or not self.project_manager.current_project:
            QMessageBox.warning(self, "警告", "请先加载项目")
            return
        
        # 获取配置
        config = {
            'output_format': self.output_format_combo.currentText(),
            'quality': self.quality_combo.currentText(),
            'resolution': self.resolution_combo.currentText(),
            'fps': self.fps_spinbox.value(),
            'background_music': self.background_music_path,
            'music_volume': self.music_volume_slider.value(),
            'loop_music': self.loop_music_checkbox.isChecked(),
            'transition_config': {
                'mode': self.transition_mode_combo.currentText(),
                'duration': self.transition_duration_spinbox.value(),
                'intensity': 5
            }
        }
        
        QMessageBox.information(
            self, "提示", 
            f"视频合成功能正在开发中\n配置已保存: {config['output_format']}, {config['quality']}"
        )
        logger.info(f"视频合成配置: {config}")
