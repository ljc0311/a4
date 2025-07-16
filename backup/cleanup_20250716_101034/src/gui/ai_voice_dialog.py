#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI配音对话框
集成MoneyPrinterTurbo的TTS功能，支持Edge TTS和SiliconFlow语音合成
"""

import os
import asyncio
from typing import Union, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QSpinBox, QTextEdit, QGroupBox,
    QGridLayout, QProgressBar, QMessageBox, QFileDialog,
    QCheckBox, QDoubleSpinBox, QFrame, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.utils.config_manager import ConfigManager
from src.audio_processing.tts_engine import TTSEngine
from src.utils.logger import logger


class VoiceGenerationThread(QThread):
    """语音生成线程"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, text, voice_name, voice_rate, voice_volume, 
                 generate_subtitle, output_format, config_manager):
        super().__init__()
        self.text = text
        self.voice_name = voice_name
        self.voice_rate = voice_rate
        self.voice_volume = voice_volume
        self.generate_subtitle = generate_subtitle
        self.output_format = output_format
        self.config_manager = config_manager
        self.is_cancelled = False
        self.tts_engine = TTSEngine()
    
    def run(self):
        """执行语音生成"""
        try:
            self.status_updated.emit("正在初始化...")
            self.progress_updated.emit(5)
            
            if self.is_cancelled:
                return
            
            # 获取输出目录 - 优先使用项目音频目录
            from src.gui.main_window import MainWindow
            main_window = None
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, MainWindow):
                    main_window = widget
                    break
            
            if main_window and main_window.current_project_name:
                # 使用项目特定的音频目录
                project_root = main_window.project_manager.get_project_path(main_window.current_project_name)
                audio_dir = os.path.join(project_root, 'audio')
                os.makedirs(audio_dir, exist_ok=True)
            else:
                # 使用全局音频目录
                audio_dir = self.config_manager.get_audio_output_dir()
            
            # 生成输出文件名
            import time
            # 使用简洁的文件名，不包含时间戳
            audio_filename = f"voice.{self.output_format.lower()}"
            audio_file = os.path.join(audio_dir, audio_filename)
            
            self.status_updated.emit("正在生成语音...")
            self.progress_updated.emit(20)
            
            if self.is_cancelled:
                return
            
            # 解析语音名称
            actual_voice_name = self._parse_voice_name(self.voice_name)
            
            # 调用TTS引擎生成语音
            result = self.tts_engine.generate_speech(
                text=self.text,
                voice_name=actual_voice_name,
                voice_rate=self.voice_rate,
                voice_volume=self.voice_volume,
                output_file=audio_file
            )
            
            self.progress_updated.emit(80)
            
            if self.is_cancelled:
                return
            
            if result.get('success'):
                self.status_updated.emit("正在处理字幕...")
                self.progress_updated.emit(90)
                
                # 处理字幕
                subtitle_file = None
                if self.generate_subtitle and result.get('subtitle_data'):
                    subtitle_dir = self.config_manager.get_subtitle_output_dir()
                    # 使用简洁的文件名，不包含时间戳
                    subtitle_filename = f"subtitle.srt"
                    subtitle_file = os.path.join(subtitle_dir, subtitle_filename)
                    
                    try:
                        with open(subtitle_file, 'w', encoding='utf-8') as f:
                            f.write(result['subtitle_data'])
                    except Exception as e:
                        print(f"保存字幕文件失败: {e}")
                        subtitle_file = None
                
                self.progress_updated.emit(100)
                self.status_updated.emit("生成完成")
                
                # 返回成功结果
                final_result = {
                    'success': True,
                    'audio_file': result['audio_file'],
                    'subtitle_file': subtitle_file,
                    'engine': result.get('engine', 'unknown')
                }
                
                self.finished_signal.emit(final_result)
            else:
                # 返回失败结果
                self.finished_signal.emit(result)
                
        except Exception as e:
            result = {
                'success': False,
                'error': f"语音生成异常: {str(e)}"
            }
            self.finished_signal.emit(result)
    
    def _parse_voice_name(self, display_name):
        """从显示名称解析实际的语音名称"""
        # 移除显示用的描述信息
        if " (" in display_name:
            voice_name = display_name.split(" (")[0]
        else:
            voice_name = display_name
        
        # 如果是Edge TTS语音，需要添加性别后缀
        if not voice_name.startswith('siliconflow:'):
            if "(女声)" in display_name or "Female" in display_name:
                if not voice_name.endswith('-Female'):
                    voice_name += '-Female'
            elif "(男声)" in display_name or "Male" in display_name:
                if not voice_name.endswith('-Male'):
                    voice_name += '-Male'
        
        return voice_name
    
    def cancel(self):
        """取消生成"""
        self.is_cancelled = True


class AIVoiceDialog(QDialog):
    """AI配音对话框"""
    
    def __init__(self, parent=None, text="", row_index=0):
        super().__init__(parent)
        self.parent_window = parent
        self.original_text = text
        self.row_index = row_index
        self.config_manager = ConfigManager()
        self.tts_engine = TTSEngine()
        self.tts_config = self.config_manager.get_tts_config()
        
        # 语音生成相关
        self.generation_thread = None
        self.output_audio_file = None
        self.subtitle_data = None
        
        # 语音列表缓存
        self.edge_voices = []
        self.siliconflow_voices = []
        
        self.init_ui()
        self.load_voice_lists()
        self.load_default_settings()
        
    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle(f"AI配音 - 第{self.row_index + 1}行")
        self.setModal(True)
        self.resize(600, 700)
        
        layout = QVBoxLayout()
        
        # 原文显示区域
        text_group = QGroupBox("配音文本")
        text_layout = QVBoxLayout()
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.original_text)
        self.text_edit.setMaximumHeight(120)
        self.text_edit.setToolTip("可以编辑要配音的文本内容")
        text_layout.addWidget(self.text_edit)
        
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)
        
        # 语音引擎选择
        engine_group = QGroupBox("语音引擎")
        engine_layout = QVBoxLayout()
        
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Edge TTS (免费)", "SiliconFlow (需API Key)"])
        # 设置默认引擎
        default_engine = self.tts_config.get('default_engine', 'edge')
        if default_engine == 'edge':
            self.engine_combo.setCurrentText("Edge TTS (免费)")
        else:
            self.engine_combo.setCurrentText("SiliconFlow (需API Key)")
        self.engine_combo.currentTextChanged.connect(self.on_engine_changed)
        self.engine_combo.setToolTip("选择语音合成引擎")
        engine_layout.addWidget(self.engine_combo)
        
        engine_group.setLayout(engine_layout)
        layout.addWidget(engine_group)
        
        # 语音选择区域
        voice_group = QGroupBox("语音设置")
        voice_layout = QGridLayout()
        
        # 语音选择
        voice_layout.addWidget(QLabel("选择语音:"), 0, 0)
        self.voice_combo = QComboBox()
        self.voice_combo.setToolTip("选择具体的语音角色")
        voice_layout.addWidget(self.voice_combo, 0, 1, 1, 2)
        
        # 语音预览按钮
        self.preview_btn = QPushButton("试听")
        self.preview_btn.clicked.connect(self.preview_voice)
        self.preview_btn.setToolTip("试听选中的语音效果")
        voice_layout.addWidget(self.preview_btn, 0, 3)
        
        # 语速设置
        voice_layout.addWidget(QLabel("语速:"), 1, 0)
        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setRange(25, 400)  # 0.25x to 4.0x
        default_rate = int(self.tts_config.get('default_rate', 1.0) * 100)
        self.rate_slider.setValue(default_rate)
        self.rate_slider.valueChanged.connect(self.on_rate_changed)
        self.rate_slider.setToolTip("调整语音播放速度")
        voice_layout.addWidget(self.rate_slider, 1, 1)
        
        self.rate_spinbox = QDoubleSpinBox()
        self.rate_spinbox.setRange(0.25, 4.0)
        self.rate_spinbox.setValue(self.tts_config.get('default_rate', 1.0))
        self.rate_spinbox.setSingleStep(0.1)
        self.rate_spinbox.setSuffix("x")
        self.rate_spinbox.valueChanged.connect(self.on_rate_spinbox_changed)
        voice_layout.addWidget(self.rate_spinbox, 1, 2)
        
        # 音量设置
        voice_layout.addWidget(QLabel("音量:"), 2, 0)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(60, 500)  # 0.6x to 5.0x
        default_volume = int(self.tts_config.get('default_volume', 1.0) * 100)
        self.volume_slider.setValue(default_volume)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        self.volume_slider.setToolTip("调整语音音量大小")
        voice_layout.addWidget(self.volume_slider, 2, 1)
        
        self.volume_spinbox = QDoubleSpinBox()
        self.volume_spinbox.setRange(0.6, 5.0)
        self.volume_spinbox.setValue(self.tts_config.get('default_volume', 1.0))
        self.volume_spinbox.setSingleStep(0.1)
        self.volume_spinbox.setSuffix("x")
        self.volume_spinbox.valueChanged.connect(self.on_volume_spinbox_changed)
        voice_layout.addWidget(self.volume_spinbox, 2, 2)
        
        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)
        
        # 高级设置
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QGridLayout()
        
        # 生成字幕选项
        self.generate_subtitle_cb = QCheckBox("同时生成字幕文件")
        self.generate_subtitle_cb.setChecked(self.tts_config.get('generate_subtitle', True))
        self.generate_subtitle_cb.setToolTip("是否同时生成SRT字幕文件")
        advanced_layout.addWidget(self.generate_subtitle_cb, 0, 0, 1, 2)
        
        # 输出格式
        advanced_layout.addWidget(QLabel("输出格式:"), 1, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP3", "WAV"])
        default_format = self.tts_config.get('output_format', 'mp3').upper()
        self.format_combo.setCurrentText(default_format)
        self.format_combo.setToolTip("选择音频输出格式")
        advanced_layout.addWidget(self.format_combo, 1, 1)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("开始配音")
        self.generate_btn.clicked.connect(self.start_generation)
        self.generate_btn.setToolTip("开始生成语音文件")
        button_layout.addWidget(self.generate_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_generation)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("保存设置")
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setToolTip("保存当前配音参数为默认设置")
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def load_voice_lists(self):
        """加载语音列表"""
        try:
            # 加载Edge TTS语音列表
            from src.audio_processing.voice_lists import get_edge_voices, get_siliconflow_voices
            
            self.edge_voices = get_edge_voices()
            self.siliconflow_voices = get_siliconflow_voices()
            
            # 默认显示Edge TTS语音
            self.update_voice_list()
            
        except Exception as e:
            logger.error(f"加载语音列表失败: {e}")
            QMessageBox.warning(self, "警告", f"加载语音列表失败: {str(e)}")
    
    def update_voice_list(self):
        """更新语音列表"""
        self.voice_combo.clear()
        
        if self.engine_combo.currentIndex() == 0:  # Edge TTS
            for voice in self.edge_voices:
                self.voice_combo.addItem(voice)
        else:  # SiliconFlow
            for voice in self.siliconflow_voices:
                self.voice_combo.addItem(voice)
    
    def on_engine_changed(self):
        """引擎切换事件"""
        self.update_voice_list()
        
        # 根据引擎类型调整UI
        if self.engine_combo.currentIndex() == 1:  # SiliconFlow
            # 检查API Key配置
            api_key = self.config_manager.get_tts_setting('siliconflow.api_key', '')
            if not api_key:
                QMessageBox.warning(
                    self, "配置提醒", 
                    "使用SiliconFlow需要配置API Key\n请在设置中配置SiliconFlow API Key"
                )
        
        # 设置默认语音
        default_voice = self.tts_config.get('default_voice', '')
        if default_voice:
            index = self.voice_combo.findText(default_voice)
            if index >= 0:
                self.voice_combo.setCurrentIndex(index)
    
    def on_rate_changed(self, value):
        """语速滑块变化事件"""
        rate = value / 100.0
        self.rate_spinbox.blockSignals(True)
        self.rate_spinbox.setValue(rate)
        self.rate_spinbox.blockSignals(False)
    
    def on_rate_spinbox_changed(self, value):
        """语速输入框变化事件"""
        slider_value = int(value * 100)
        self.rate_slider.blockSignals(True)
        self.rate_slider.setValue(slider_value)
        self.rate_slider.blockSignals(False)
    
    def on_volume_changed(self, value):
        """音量滑块变化事件"""
        volume = value / 100.0
        self.volume_spinbox.blockSignals(True)
        self.volume_spinbox.setValue(volume)
        self.volume_spinbox.blockSignals(False)
    
    def on_volume_spinbox_changed(self, value):
        """音量输入框变化事件"""
        slider_value = int(value * 100)
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(slider_value)
        self.volume_slider.blockSignals(False)
    
    def preview_voice(self):
        """预览语音"""
        if not self.voice_combo.currentText():
            QMessageBox.warning(self, "警告", "请先选择语音")
            return
            
        # 使用简短的预览文本
        preview_text = "你好，这是语音预览效果。"
        
        try:
            # 创建临时预览文件
            import tempfile
            temp_dir = tempfile.gettempdir()
            preview_file = os.path.join(temp_dir, "voice_preview.mp3")
            
            # 获取当前配置
            voice_config = self.get_voice_config()
            
            # 启动预览生成线程
            self.preview_thread = VoiceGenerationThread(
                text=preview_text,
                voice_name=voice_config['voice_name'],
                voice_rate=voice_config['voice_rate'],
                voice_volume=voice_config['voice_volume'],
                generate_subtitle=False,  # 预览不需要字幕
                output_format=voice_config['output_format'],
                config_manager=self.config_manager
            )
            self.preview_thread.finished_signal.connect(self.on_preview_completed)
            self.preview_thread.status_updated.connect(lambda msg: self.status_label.setText(msg))
            
            self.preview_btn.setEnabled(False)
            self.preview_btn.setText("生成中...")
            self.status_label.setText("正在生成预览...")
            
            self.preview_thread.start()
            
        except Exception as e:
            logger.error(f"预览语音失败: {e}")
            QMessageBox.critical(self, "错误", f"预览语音失败: {str(e)}")
    
    def on_preview_completed(self, result):
        """预览完成"""
        self.preview_btn.setEnabled(True)
        self.preview_btn.setText("试听")
        
        if result.get('success'):
            audio_file = result.get('audio_file')
            self.status_label.setText("预览生成完成")
            
            # 播放预览音频
            try:
                import subprocess
                import platform
                
                system = platform.system()
                if system == "Windows":
                    os.startfile(audio_file)
                elif system == "Darwin":  # macOS
                    subprocess.run(["open", audio_file])
                else:  # Linux
                    subprocess.run(["xdg-open", audio_file])
                    
            except Exception as e:
                logger.error(f"播放预览音频失败: {e}")
                QMessageBox.information(self, "提示", f"预览文件已生成: {audio_file}")
        else:
            self.status_label.setText("预览失败")
            error_msg = result.get('error', '未知错误')
            QMessageBox.critical(self, "错误", f"预览失败: {error_msg}")
    
    def on_preview_failed(self, error_msg):
        """预览失败"""
        self.preview_btn.setEnabled(True)
        self.preview_btn.setText("试听")
        self.status_label.setText("预览失败")
        QMessageBox.critical(self, "错误", f"预览失败: {error_msg}")
    
    def get_voice_config(self):
        """获取当前语音配置"""
        return {
            'engine': 'edge' if self.engine_combo.currentIndex() == 0 else 'siliconflow',
            'voice_name': self.voice_combo.currentText(),
            'voice_rate': self.rate_spinbox.value(),
            'voice_volume': self.volume_spinbox.value(),
            'output_format': self.format_combo.currentText().lower()
        }
    
    def get_current_settings(self):
        """获取当前完整的配音设置"""
        try:
            settings = {
                'text': self.text_edit.toPlainText(),
                'voice_config': self.get_voice_config(),
                'generate_subtitle': self.generate_subtitle_cb.isChecked(),
                'output_audio_file': self.output_audio_file,
                'subtitle_data': self.subtitle_data
            }
            return settings
        except Exception as e:
            logger.error(f"获取配音设置失败: {e}")
            return {}
    
    def load_settings(self, settings):
        """加载配音设置"""
        try:
            if not settings:
                return
            
            # 加载文本
            if 'text' in settings:
                self.text_edit.setPlainText(settings['text'])
            
            # 加载语音配置
            voice_config = settings.get('voice_config', {})
            if voice_config:
                # 设置引擎
                engine = voice_config.get('engine', 'edge')
                if engine == 'siliconflow':
                    self.engine_combo.setCurrentIndex(1)
                else:
                    self.engine_combo.setCurrentIndex(0)
                
                # 触发引擎切换事件来更新语音列表
                self.on_engine_changed()
                
                # 设置语音
                voice_name = voice_config.get('voice_name', '')
                if voice_name:
                    index = self.voice_combo.findText(voice_name)
                    if index >= 0:
                        self.voice_combo.setCurrentIndex(index)
                
                # 设置语速和音量
                self.rate_spinbox.setValue(voice_config.get('voice_rate', 1.0))
                self.volume_spinbox.setValue(voice_config.get('voice_volume', 1.0))
                
                # 设置输出格式
                output_format = voice_config.get('output_format', 'mp3')
                index = self.format_combo.findText(output_format.upper())
                if index >= 0:
                    self.format_combo.setCurrentIndex(index)
            
            # 加载字幕生成选项
            if 'generate_subtitle' in settings:
                self.generate_subtitle_cb.setChecked(settings['generate_subtitle'])
            
            # 加载输出文件信息
            if 'output_audio_file' in settings:
                self.output_audio_file = settings['output_audio_file']
            
            if 'subtitle_data' in settings:
                self.subtitle_data = settings['subtitle_data']
            
            logger.info("配音设置已加载")
            
        except Exception as e:
            logger.error(f"加载配音设置失败: {e}")
    
    def start_generation(self):
        """开始生成语音"""
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入要配音的文本")
            return
            
        if not self.voice_combo.currentText():
            QMessageBox.warning(self, "警告", "请选择语音")
            return
        
        # 检查SiliconFlow配置
        if self.engine_combo.currentIndex() == 1:  # SiliconFlow
            api_key = self.config_manager.get_config().get('siliconflow', {}).get('api_key', '')
            if not api_key:
                QMessageBox.warning(self, "警告", 
                    "使用SiliconFlow需要配置API Key\n请在设置中配置SiliconFlow API Key")
                return
        
        # 创建并启动生成线程
        self.generation_thread = VoiceGenerationThread(
            text=text,
            voice_name=self.voice_combo.currentText(),
            voice_rate=self.rate_spinbox.value(),
            voice_volume=self.volume_spinbox.value(),
            generate_subtitle=self.generate_subtitle_cb.isChecked(),
            output_format=self.format_combo.currentText().lower(),
            config_manager=self.config_manager
        )
        
        # 连接信号
        self.generation_thread.progress_updated.connect(self.progress_bar.setValue)
        self.generation_thread.status_updated.connect(self.status_label.setText)
        self.generation_thread.finished_signal.connect(self.on_generation_finished)
        
        # 更新UI状态
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("生成中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("准备开始...")
        
        # 启动线程
        self.generation_thread.start()
    
    def on_generation_finished(self, result):
        """生成完成处理"""
        # 重置UI状态
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("开始配音")
        self.progress_bar.setVisible(False)
        
        if result.get('success'):
            # 生成成功
            audio_file = result.get('audio_file', '')
            subtitle_file = result.get('subtitle_file', '')
            engine = result.get('engine', 'unknown')
            
            self.output_audio_file = audio_file
            self.subtitle_data = result.get('subtitle_data', '')
            
            success_msg = f"配音生成完成！\n引擎: {engine}\n音频文件: {os.path.basename(audio_file)}"
            if subtitle_file:
                success_msg += f"\n字幕文件: {os.path.basename(subtitle_file)}"
            
            QMessageBox.information(self, "成功", success_msg)
            
            self.status_label.setText("配音生成完成")
            
            # 询问是否应用到分镜
            reply = QMessageBox.question(
                self, "应用配音", 
                "是否将生成的配音应用到分镜列表？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.apply_to_storyboard()
            
            # 自动保存配音设置到项目
            try:
                if hasattr(self.parent_window, 'save_current_project'):
                    self.parent_window.save_current_project()
                    logger.info("配音完成后已自动保存项目")
            except Exception as e:
                logger.error(f"自动保存项目失败: {e}")
            
            self.accept()
            
        else:
            # 生成失败
            error_msg = result.get('error', '未知错误')
            self.status_label.setText("配音生成失败")
            QMessageBox.critical(self, "错误", f"配音生成失败: {error_msg}")
    
    def cancel_generation(self):
        """取消生成"""
        if self.generation_thread and self.generation_thread.isRunning():
            self.generation_thread.cancel()
            self.generation_thread.wait()
            
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("开始配音")
            self.progress_bar.setVisible(False)
            self.status_label.setText("已取消")
        
        self.reject()
    
    def apply_to_storyboard(self):
        """应用配音到分镜列表"""
        try:
            if self.parent_window and hasattr(self.parent_window, 'shots_data'):
                # 直接更新分镜数据
                if self.parent_window.shots_data and self.row_index < len(self.parent_window.shots_data):
                    self.parent_window.shots_data[self.row_index]['voice_file'] = self.output_audio_file
                    # 如果有字幕数据，也保存字幕数据
                    if hasattr(self, 'subtitle_data') and self.subtitle_data:
                        self.parent_window.shots_data[self.row_index]['subtitle_data'] = self.subtitle_data
                    logger.info(f"已将配音应用到第{self.row_index + 1}行: {self.output_audio_file}")
                    
                    # 更新UI显示（如果有相关方法）
                    if hasattr(self.parent_window, 'update_shot_display'):
                        self.parent_window.update_shot_display(self.row_index)
                else:
                    logger.warning(f"无法应用配音：分镜索引 {self.row_index} 超出范围")
            else:
                logger.warning("无法应用配音：父窗口或分镜数据不存在")
        except Exception as e:
            logger.error(f"应用配音到分镜失败: {e}")
            QMessageBox.warning(self, "警告", f"应用配音到分镜失败: {str(e)}")
    
    def save_settings(self):
        """保存当前设置为默认值"""
        try:
            # 保存TTS设置
            engine = 'edge' if 'Edge' in self.engine_combo.currentText() else 'siliconflow'
            self.config_manager.set_tts_setting('default_engine', engine)
            self.config_manager.set_tts_setting('default_voice', self.voice_combo.currentText())
            self.config_manager.set_tts_setting('default_rate', self.rate_spinbox.value())
            self.config_manager.set_tts_setting('default_volume', self.volume_spinbox.value())
            self.config_manager.set_tts_setting('generate_subtitle', self.generate_subtitle_cb.isChecked())
            self.config_manager.set_tts_setting('output_format', self.format_combo.currentText().lower())
            
            QMessageBox.information(self, "成功", "配音设置已保存为默认值")
            
        except Exception as e:
            logger.error(f"保存配音设置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")
    
    def load_default_settings(self):
        """加载默认设置"""
        try:
            # 设置默认引擎
            default_engine = self.tts_config.get('default_engine', 'edge')
            if default_engine == 'siliconflow':
                self.engine_combo.setCurrentIndex(1)
            else:
                self.engine_combo.setCurrentIndex(0)
            
            # 触发引擎切换事件来更新语音列表
            self.on_engine_changed()
            
            # 设置默认语音
            default_voice = self.tts_config.get('default_voice', '')
            if default_voice:
                index = self.voice_combo.findText(default_voice)
                if index >= 0:
                    self.voice_combo.setCurrentIndex(index)
            
            # 设置默认语速
            default_rate = self.tts_config.get('default_rate', 1.0)
            self.rate_spinbox.setValue(default_rate)
            
            # 设置默认音量
            default_volume = self.tts_config.get('default_volume', 1.0)
            self.volume_spinbox.setValue(default_volume)
            
            # 设置默认格式
            default_format = self.tts_config.get('output_format', 'mp3')
            index = self.format_combo.findText(default_format.upper())
            if index >= 0:
                self.format_combo.setCurrentIndex(index)
            
            # 设置字幕生成选项
            generate_subtitle = self.tts_config.get('generate_subtitle', True)
            self.generate_subtitle_cb.setChecked(generate_subtitle)
            
        except Exception as e:
            logger.error(f"加载默认设置失败: {e}")
    
    def get_result(self):
        """获取生成结果"""
        return {
            'audio_file': self.output_audio_file,
            'subtitle_data': self.subtitle_data,
            'voice_config': self.get_voice_config()
        }
    
    def get_generation_result(self):
        """获取语音生成结果"""
        if self.output_audio_file and os.path.exists(self.output_audio_file):
            return {
                'success': True,
                'audio_file': self.output_audio_file,
                'subtitle_data': self.subtitle_data,
                'voice_config': self.get_voice_config()
            }
        else:
            return {
                'success': False,
                'error': '语音文件生成失败或不存在'
            }