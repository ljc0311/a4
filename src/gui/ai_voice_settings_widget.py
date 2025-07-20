#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI配音设置界面
支持多种配音引擎的配置和管理
"""

import os
import json
from typing import Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox,
    QLabel, QPushButton, QComboBox, QSlider, QSpinBox, QDoubleSpinBox,
    QLineEdit, QTextEdit, QCheckBox, QFormLayout, QMessageBox,
    QProgressBar, QFrame, QFileDialog, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon

from src.utils.logger import logger
from src.utils.config_manager import ConfigManager
from src.services.tts_engine_service import TTSEngineManager
from src.gui.styles.unified_theme_system import UnifiedThemeSystem
from src.gui.modern_ui_components import MaterialButton, MaterialCard


class VoiceTestThread(QThread):
    """语音测试线程"""
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, engine_manager, engine_name, settings):
        super().__init__()
        self.engine_manager = engine_manager
        self.engine_name = engine_name
        self.settings = settings
    
    def run(self):
        try:
            import tempfile
            import asyncio
            test_text = "这是一个配音测试。"

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name

            # 生成测试音频 - 使用异步调用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self.engine_manager.generate_speech(
                        self.engine_name,
                        test_text,
                        temp_path,
                        **self.settings
                    )
                )
            finally:
                loop.close()
            
            if result.get('success'):
                # 播放音频
                try:
                    import platform
                    import subprocess
                    
                    system = platform.system()
                    if system == "Windows":
                        os.startfile(temp_path)
                    elif system == "Darwin":  # macOS
                        subprocess.call(["open", temp_path])
                    else:  # Linux
                        subprocess.call(["xdg-open", temp_path])
                    
                    self.finished.emit(True, "测试成功！")
                except Exception as e:
                    self.finished.emit(True, f"音频生成成功，但播放失败: {e}")
            else:
                self.finished.emit(False, result.get('error', '测试失败'))
                
        except Exception as e:
            self.finished.emit(False, f"测试失败: {e}")


class AIVoiceSettingsWidget(QWidget):
    """AI配音设置界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.config_manager = ConfigManager()
        self.engine_manager = TTSEngineManager(self.config_manager)
        
        # 当前设置
        self.current_settings = {}
        self.test_thread = None
        
        self.init_ui()
        self.apply_styles()
        self.load_settings()
    
    def init_ui(self):
        """初始化UI界面"""
        main_layout = QVBoxLayout()
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel("🎵 AI配音设置")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)
        
        # 创建引擎标签页
        self.engine_tabs = QTabWidget()
        
        # 为每个引擎创建标签页
        engines = [
            ('edge_tts', '🔊 Edge-TTS (免费)', 'Microsoft免费TTS，支持多语言'),
            ('cosyvoice', '🏠 CosyVoice (本地)', '阿里开源本地TTS，高质量中文'),
            ('azure_speech', '🎤 Azure Speech (免费额度)', 'Microsoft高质量神经网络语音，支持情感'),
            ('google_tts', '🌍 Google Cloud TTS (免费额度)', 'Google WaveNet技术，自然度极高'),
            ('baidu_tts', '🇨🇳 百度智能云 (免费额度)', '中文语音合成专家，本土化优化')
        ]
        
        for engine_id, tab_name, description in engines:
            tab = self.create_engine_tab(engine_id, description)
            self.engine_tabs.addTab(tab, tab_name)
        
        main_layout.addWidget(self.engine_tabs)
        
        # 全局操作按钮
        self.create_global_controls(main_layout)
        
        self.setLayout(main_layout)

    def apply_styles(self):
        """应用现代化样式"""
        try:
            # 应用统一主题系统
            theme_system = UnifiedThemeSystem()
            theme_system.apply_to_widget(self)

            # 获取当前颜色配置
            colors = theme_system.current_colors

            # 设置组件样式
            self.setObjectName("ai_voice_settings_widget")

            # 应用自定义样式
            custom_style = f"""
                QTabWidget::pane {{
                    border: 2px solid {colors.get('outline_variant', '#E0E0E0')};
                    border-radius: 8px;
                    background-color: {colors.get('surface', '#FFFFFF')};
                }}

                QTabBar::tab {{
                    background-color: {colors.get('surface', '#FFFFFF')};
                    border: 1px solid {colors.get('outline_variant', '#E0E0E0')};
                    border-bottom: none;
                    border-radius: 6px 6px 0 0;
                    padding: 8px 16px;
                    margin-right: 2px;
                    color: {colors.get('on_surface', '#000000')};
                }}

                QTabBar::tab:selected {{
                    background-color: {colors.get('primary', '#1976D2')};
                    color: {colors.get('on_primary', '#FFFFFF')};
                }}

                QTabBar::tab:hover {{
                    background-color: {colors.get('surface_variant', '#F5F5F5')};
                }}

                QGroupBox {{
                    font-weight: bold;
                    border: 2px solid {colors.get('outline_variant', '#E0E0E0')};
                    border-radius: 8px;
                    margin-top: 1ex;
                    padding-top: 10px;
                    background-color: {colors.get('surface_container', '#FAFAFA')};
                }}

                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: {colors.get('primary', '#1976D2')};
                }}

                QSlider::groove:horizontal {{
                    border: 1px solid {colors.get('outline_variant', '#E0E0E0')};
                    height: 8px;
                    background: {colors.get('surface', '#FFFFFF')};
                    margin: 2px 0;
                    border-radius: 4px;
                }}

                QSlider::handle:horizontal {{
                    background: {colors.get('primary', '#1976D2')};
                    border: 1px solid {colors.get('outline', '#CCCCCC')};
                    width: 18px;
                    margin: -2px 0;
                    border-radius: 9px;
                }}

                QSlider::handle:horizontal:hover {{
                    background: {colors.get('primary_container', '#1565C0')};
                }}
            """

            current_style = self.styleSheet()
            self.setStyleSheet(current_style + custom_style)

            logger.info("AI配音设置界面样式应用完成")

        except Exception as e:
            logger.error(f"应用AI配音设置界面样式失败: {e}")

    def create_engine_tab(self, engine_id: str, description: str):
        """创建引擎配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 引擎描述
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # 连接状态
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_label = QLabel("连接状态:")
        self.status_indicator = QLabel("🔴 未连接")
        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(lambda: self.test_engine_connection(engine_id))
        
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(test_btn)
        status_layout.addStretch()
        layout.addWidget(status_frame)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 根据引擎类型创建不同的配置界面
        if engine_id == 'edge_tts':
            self.create_edge_tts_config(scroll_layout)
        elif engine_id == 'cosyvoice':
            self.create_cosyvoice_config(scroll_layout)
        elif engine_id == 'ttsmaker':
            self.create_ttsmaker_config(scroll_layout)
        elif engine_id == 'xunfei':
            self.create_xunfei_config(scroll_layout)
        elif engine_id == 'elevenlabs':
            self.create_elevenlabs_config(scroll_layout)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # 测试按钮
        test_voice_btn = QPushButton("🎵 测试配音")
        test_voice_btn.clicked.connect(lambda: self.test_voice_generation(engine_id))
        layout.addWidget(test_voice_btn)
        
        return tab
    
    def create_edge_tts_config(self, layout):
        """创建Edge-TTS配置界面"""
        # 音色选择
        voice_group = QGroupBox("音色设置")
        voice_layout = QFormLayout(voice_group)
        
        self.edge_voice_combo = QComboBox()
        voices = [
            ('zh-CN-YunxiNeural', '云希-男声'),
            ('zh-CN-XiaoxiaoNeural', '晓晓-女声'),
            ('zh-CN-YunyangNeural', '云扬-男声'),
            ('zh-CN-XiaoyiNeural', '晓伊-女声'),
            ('en-US-AriaNeural', 'Aria-Female'),
            ('en-US-GuyNeural', 'Guy-Male'),
        ]
        for voice_id, voice_name in voices:
            self.edge_voice_combo.addItem(voice_name, voice_id)
        voice_layout.addRow("音色:", self.edge_voice_combo)
        
        # 语速设置
        self.edge_speed_slider = QSlider(Qt.Horizontal)
        self.edge_speed_slider.setRange(50, 200)
        self.edge_speed_slider.setValue(100)
        self.edge_speed_label = QLabel("100%")
        self.edge_speed_slider.valueChanged.connect(
            lambda v: self.edge_speed_label.setText(f"{v}%")
        )
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(self.edge_speed_slider)
        speed_layout.addWidget(self.edge_speed_label)
        voice_layout.addRow("语速:", speed_layout)
        
        # 音调设置
        self.edge_pitch_slider = QSlider(Qt.Horizontal)
        self.edge_pitch_slider.setRange(-50, 50)
        self.edge_pitch_slider.setValue(0)
        self.edge_pitch_label = QLabel("0Hz")
        self.edge_pitch_slider.valueChanged.connect(
            lambda v: self.edge_pitch_label.setText(f"{v}Hz")
        )
        pitch_layout = QHBoxLayout()
        pitch_layout.addWidget(self.edge_pitch_slider)
        pitch_layout.addWidget(self.edge_pitch_label)
        voice_layout.addRow("音调:", pitch_layout)
        
        layout.addWidget(voice_group)
    
    def create_cosyvoice_config(self, layout):
        """创建CosyVoice配置界面"""
        # 模型路径设置
        path_group = QGroupBox("模型配置")
        path_layout = QFormLayout(path_group)
        
        self.cosyvoice_path_input = QLineEdit()
        self.cosyvoice_path_input.setPlaceholderText("请选择CosyVoice模型目录")
        path_btn = QPushButton("浏览...")
        path_btn.clicked.connect(self.browse_cosyvoice_path)
        
        path_widget_layout = QHBoxLayout()
        path_widget_layout.addWidget(self.cosyvoice_path_input)
        path_widget_layout.addWidget(path_btn)
        path_layout.addRow("模型路径:", path_widget_layout)
        
        # 音色选择
        self.cosyvoice_voice_combo = QComboBox()
        self.cosyvoice_voice_combo.addItems(['default', 'female', 'male'])
        path_layout.addRow("音色:", self.cosyvoice_voice_combo)
        
        # 语速设置
        self.cosyvoice_speed_spin = QDoubleSpinBox()
        self.cosyvoice_speed_spin.setRange(0.5, 2.0)
        self.cosyvoice_speed_spin.setValue(1.0)
        self.cosyvoice_speed_spin.setSingleStep(0.1)
        path_layout.addRow("语速:", self.cosyvoice_speed_spin)
        
        layout.addWidget(path_group)
    
    def create_ttsmaker_config(self, layout):
        """创建TTSMaker配置界面"""
        # API配置
        api_group = QGroupBox("API配置")
        api_layout = QFormLayout(api_group)
        
        self.ttsmaker_key_input = QLineEdit()
        self.ttsmaker_key_input.setPlaceholderText("请输入TTSMaker API Key")
        self.ttsmaker_key_input.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Key:", self.ttsmaker_key_input)
        
        # 音色选择
        self.ttsmaker_voice_combo = QComboBox()
        voices = [
            ('zh-CN-XiaoxiaoNeural', '晓晓-女声'),
            ('zh-CN-YunxiNeural', '云希-男声'),
            ('en-US-AriaNeural', 'Aria-Female'),
            ('en-US-GuyNeural', 'Guy-Male'),
        ]
        for voice_id, voice_name in voices:
            self.ttsmaker_voice_combo.addItem(voice_name, voice_id)
        api_layout.addRow("音色:", self.ttsmaker_voice_combo)
        
        layout.addWidget(api_group)
    
    def create_xunfei_config(self, layout):
        """创建科大讯飞配置界面"""
        # API配置
        api_group = QGroupBox("API配置")
        api_layout = QFormLayout(api_group)
        
        self.xunfei_app_id_input = QLineEdit()
        self.xunfei_app_id_input.setPlaceholderText("请输入App ID")
        api_layout.addRow("App ID:", self.xunfei_app_id_input)
        
        self.xunfei_api_key_input = QLineEdit()
        self.xunfei_api_key_input.setPlaceholderText("请输入API Key")
        self.xunfei_api_key_input.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Key:", self.xunfei_api_key_input)
        
        self.xunfei_api_secret_input = QLineEdit()
        self.xunfei_api_secret_input.setPlaceholderText("请输入API Secret")
        self.xunfei_api_secret_input.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Secret:", self.xunfei_api_secret_input)
        
        # 音色选择
        self.xunfei_voice_combo = QComboBox()
        voices = [
            ('xiaoyan', '小燕-女声'),
            ('xiaoyu', '小宇-男声'),
            ('xiaofeng', '小峰-男声'),
            ('xiaomei', '小美-女声'),
        ]
        for voice_id, voice_name in voices:
            self.xunfei_voice_combo.addItem(voice_name, voice_id)
        api_layout.addRow("音色:", self.xunfei_voice_combo)
        
        layout.addWidget(api_group)
    
    def create_elevenlabs_config(self, layout):
        """创建ElevenLabs配置界面"""
        # API配置
        api_group = QGroupBox("API配置")
        api_layout = QFormLayout(api_group)
        
        self.elevenlabs_key_input = QLineEdit()
        self.elevenlabs_key_input.setPlaceholderText("请输入ElevenLabs API Key")
        self.elevenlabs_key_input.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Key:", self.elevenlabs_key_input)
        
        # 音色选择
        self.elevenlabs_voice_combo = QComboBox()
        voices = [
            ('pNInz6obpgDQGcFmaJgB', 'Adam-Male'),
            ('EXAVITQu4vr4xnSDxMaL', 'Bella-Female'),
            ('VR6AewLTigWG4xSOukaG', 'Arnold-Male'),
            ('pqHfZKP75CvOlQylNhV4', 'Bill-Male'),
        ]
        for voice_id, voice_name in voices:
            self.elevenlabs_voice_combo.addItem(voice_name, voice_id)
        api_layout.addRow("音色:", self.elevenlabs_voice_combo)
        
        # 高级设置
        self.elevenlabs_stability_slider = QSlider(Qt.Horizontal)
        self.elevenlabs_stability_slider.setRange(0, 100)
        self.elevenlabs_stability_slider.setValue(50)
        api_layout.addRow("稳定性:", self.elevenlabs_stability_slider)
        
        self.elevenlabs_similarity_slider = QSlider(Qt.Horizontal)
        self.elevenlabs_similarity_slider.setRange(0, 100)
        self.elevenlabs_similarity_slider.setValue(50)
        api_layout.addRow("相似度:", self.elevenlabs_similarity_slider)
        
        layout.addWidget(api_group)
    
    def create_global_controls(self, layout):
        """创建全局控制按钮"""
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        
        save_btn = QPushButton("💾 保存设置")
        save_btn.clicked.connect(self.save_settings)
        controls_layout.addWidget(save_btn)
        
        reset_btn = QPushButton("🔄 重置设置")
        reset_btn.clicked.connect(self.reset_settings)
        controls_layout.addWidget(reset_btn)
        
        controls_layout.addStretch()
        
        layout.addWidget(controls_frame)
    
    def browse_cosyvoice_path(self):
        """浏览CosyVoice模型路径"""
        path = QFileDialog.getExistingDirectory(self, "选择CosyVoice模型目录")
        if path:
            self.cosyvoice_path_input.setText(path)
    
    def test_engine_connection(self, engine_id: str):
        """测试引擎连接"""
        try:
            engine = self.engine_manager.get_engine(engine_id)
            if engine:
                result = engine.test_connection()
                if result.get('success'):
                    self.status_indicator.setText("🟢 连接正常")
                    QMessageBox.information(self, "连接测试", result.get('message', '连接成功'))
                else:
                    self.status_indicator.setText("🔴 连接失败")
                    QMessageBox.warning(self, "连接测试", result.get('error', '连接失败'))
            else:
                QMessageBox.warning(self, "错误", f"引擎 {engine_id} 不存在")
        except Exception as e:
            logger.error(f"测试引擎连接失败: {e}")
            QMessageBox.critical(self, "错误", f"测试失败: {e}")
    
    def test_voice_generation(self, engine_id: str):
        """测试语音生成"""
        try:
            # 获取当前引擎的设置
            settings = self.get_engine_settings(engine_id)
            
            # 启动测试线程
            self.test_thread = VoiceTestThread(self.engine_manager, engine_id, settings)
            self.test_thread.finished.connect(self.on_test_finished)
            self.test_thread.start()
            
            QMessageBox.information(self, "测试", "正在生成测试音频，请稍候...")
            
        except Exception as e:
            logger.error(f"测试语音生成失败: {e}")
            QMessageBox.critical(self, "错误", f"测试失败: {e}")
    
    def on_test_finished(self, success: bool, message: str):
        """测试完成回调"""
        if success:
            QMessageBox.information(self, "测试结果", message)
        else:
            QMessageBox.warning(self, "测试结果", message)
    
    def get_engine_settings(self, engine_id: str) -> Dict[str, Any]:
        """获取引擎设置"""
        settings = {}

        try:
            if engine_id == 'edge_tts':
                if hasattr(self, 'edge_voice_combo'):
                    voice_data = self.edge_voice_combo.currentData()
                    if voice_data:
                        settings['voice'] = voice_data
                    else:
                        settings['voice'] = 'zh-CN-YunxiNeural'

                if hasattr(self, 'edge_speed_slider'):
                    settings['speed'] = self.edge_speed_slider.value() / 100.0
                else:
                    settings['speed'] = 1.0

                if hasattr(self, 'edge_pitch_slider'):
                    settings['pitch'] = self.edge_pitch_slider.value()
                else:
                    settings['pitch'] = 0

            elif engine_id == 'cosyvoice':
                if hasattr(self, 'cosyvoice_path_input'):
                    settings['model_path'] = self.cosyvoice_path_input.text()

                if hasattr(self, 'cosyvoice_voice_combo'):
                    settings['voice'] = self.cosyvoice_voice_combo.currentText()
                else:
                    settings['voice'] = 'default'

                if hasattr(self, 'cosyvoice_speed_spin'):
                    settings['speed'] = self.cosyvoice_speed_spin.value()
                else:
                    settings['speed'] = 1.0

            elif engine_id == 'ttsmaker':
                if hasattr(self, 'ttsmaker_key_input'):
                    settings['api_key'] = self.ttsmaker_key_input.text()

                if hasattr(self, 'ttsmaker_voice_combo'):
                    voice_data = self.ttsmaker_voice_combo.currentData()
                    if voice_data:
                        settings['voice'] = voice_data
                    else:
                        settings['voice'] = 'zh-CN-XiaoxiaoNeural'

            elif engine_id == 'xunfei':
                if hasattr(self, 'xunfei_app_id_input'):
                    settings['app_id'] = self.xunfei_app_id_input.text()

                if hasattr(self, 'xunfei_api_key_input'):
                    settings['api_key'] = self.xunfei_api_key_input.text()

                if hasattr(self, 'xunfei_api_secret_input'):
                    settings['api_secret'] = self.xunfei_api_secret_input.text()

                if hasattr(self, 'xunfei_voice_combo'):
                    voice_data = self.xunfei_voice_combo.currentData()
                    if voice_data:
                        settings['voice'] = voice_data
                    else:
                        settings['voice'] = 'xiaoyan'

            elif engine_id == 'elevenlabs':
                if hasattr(self, 'elevenlabs_key_input'):
                    settings['api_key'] = self.elevenlabs_key_input.text()

                if hasattr(self, 'elevenlabs_voice_combo'):
                    voice_data = self.elevenlabs_voice_combo.currentData()
                    if voice_data:
                        settings['voice'] = voice_data
                    else:
                        settings['voice'] = 'pNInz6obpgDQGcFmaJgB'

                if hasattr(self, 'elevenlabs_stability_slider'):
                    settings['stability'] = self.elevenlabs_stability_slider.value() / 100.0
                else:
                    settings['stability'] = 0.5

                if hasattr(self, 'elevenlabs_similarity_slider'):
                    settings['similarity'] = self.elevenlabs_similarity_slider.value() / 100.0
                else:
                    settings['similarity'] = 0.5

            logger.info(f"获取引擎 {engine_id} 设置: {settings}")
            return settings

        except Exception as e:
            logger.error(f"获取引擎 {engine_id} 设置失败: {e}")
            return {}
    
    def load_settings(self):
        """加载设置"""
        try:
            # 加载Edge-TTS设置
            edge_voice = self.config_manager.get_setting('edge_tts.voice', 'zh-CN-YunxiNeural')
            edge_speed = self.config_manager.get_setting('edge_tts.speed', 100)
            edge_pitch = self.config_manager.get_setting('edge_tts.pitch', 0)

            if hasattr(self, 'edge_voice_combo'):
                # 查找并设置音色
                index = self.edge_voice_combo.findText(edge_voice)
                if index >= 0:
                    self.edge_voice_combo.setCurrentIndex(index)

            if hasattr(self, 'edge_speed_slider'):
                self.edge_speed_slider.setValue(edge_speed)
                self.edge_speed_label.setText(f"{edge_speed}%")

            if hasattr(self, 'edge_pitch_slider'):
                self.edge_pitch_slider.setValue(edge_pitch)
                self.edge_pitch_label.setText(f"{edge_pitch}Hz")

            # 加载CosyVoice设置
            cosyvoice_path = self.config_manager.get_setting('cosyvoice.model_path', '')
            cosyvoice_voice = self.config_manager.get_setting('cosyvoice.voice', 'default')

            if hasattr(self, 'cosyvoice_path_input'):
                self.cosyvoice_path_input.setText(cosyvoice_path)

            if hasattr(self, 'cosyvoice_voice_combo'):
                index = self.cosyvoice_voice_combo.findText(cosyvoice_voice)
                if index >= 0:
                    self.cosyvoice_voice_combo.setCurrentIndex(index)

            # 加载TTSMaker设置
            ttsmaker_key = self.config_manager.get_setting('ttsmaker.api_key', '')
            ttsmaker_voice = self.config_manager.get_setting('ttsmaker.voice', 'zh-CN-YunxiNeural')

            if hasattr(self, 'ttsmaker_key_input'):
                self.ttsmaker_key_input.setText(ttsmaker_key)

            if hasattr(self, 'ttsmaker_voice_combo'):
                index = self.ttsmaker_voice_combo.findText(ttsmaker_voice)
                if index >= 0:
                    self.ttsmaker_voice_combo.setCurrentIndex(index)

            # 加载科大讯飞设置
            xunfei_app_id = self.config_manager.get_setting('xunfei.app_id', '')
            xunfei_api_key = self.config_manager.get_setting('xunfei.api_key', '')
            xunfei_api_secret = self.config_manager.get_setting('xunfei.api_secret', '')
            xunfei_voice = self.config_manager.get_setting('xunfei.voice', 'xiaoyan')

            if hasattr(self, 'xunfei_app_id_input'):
                self.xunfei_app_id_input.setText(xunfei_app_id)

            if hasattr(self, 'xunfei_api_key_input'):
                self.xunfei_api_key_input.setText(xunfei_api_key)

            if hasattr(self, 'xunfei_api_secret_input'):
                self.xunfei_api_secret_input.setText(xunfei_api_secret)

            if hasattr(self, 'xunfei_voice_combo'):
                index = self.xunfei_voice_combo.findText(xunfei_voice)
                if index >= 0:
                    self.xunfei_voice_combo.setCurrentIndex(index)

            # 加载ElevenLabs设置
            elevenlabs_key = self.config_manager.get_setting('elevenlabs.api_key', '')
            elevenlabs_voice = self.config_manager.get_setting('elevenlabs.voice', 'Rachel')
            elevenlabs_stability = self.config_manager.get_setting('elevenlabs.stability', 50)
            elevenlabs_similarity = self.config_manager.get_setting('elevenlabs.similarity', 50)

            if hasattr(self, 'elevenlabs_key_input'):
                self.elevenlabs_key_input.setText(elevenlabs_key)

            if hasattr(self, 'elevenlabs_voice_combo'):
                index = self.elevenlabs_voice_combo.findText(elevenlabs_voice)
                if index >= 0:
                    self.elevenlabs_voice_combo.setCurrentIndex(index)

            if hasattr(self, 'elevenlabs_stability_slider'):
                self.elevenlabs_stability_slider.setValue(elevenlabs_stability)

            if hasattr(self, 'elevenlabs_similarity_slider'):
                self.elevenlabs_similarity_slider.setValue(elevenlabs_similarity)

            logger.info("AI配音设置加载完成")

        except Exception as e:
            logger.error(f"加载配音设置失败: {e}")
            # 设置默认值以避免None错误
            self.load_default_settings()

    def load_default_settings(self):
        """加载默认设置"""
        try:
            # Edge-TTS默认设置
            if hasattr(self, 'edge_voice_combo') and self.edge_voice_combo.count() > 0:
                self.edge_voice_combo.setCurrentIndex(0)

            if hasattr(self, 'edge_speed_slider'):
                self.edge_speed_slider.setValue(100)
                self.edge_speed_label.setText("100%")

            if hasattr(self, 'edge_pitch_slider'):
                self.edge_pitch_slider.setValue(0)
                self.edge_pitch_label.setText("0Hz")

            # CosyVoice默认设置
            if hasattr(self, 'cosyvoice_voice_combo') and self.cosyvoice_voice_combo.count() > 0:
                self.cosyvoice_voice_combo.setCurrentIndex(0)

            # TTSMaker默认设置
            if hasattr(self, 'ttsmaker_voice_combo') and self.ttsmaker_voice_combo.count() > 0:
                self.ttsmaker_voice_combo.setCurrentIndex(0)

            # 科大讯飞默认设置
            if hasattr(self, 'xunfei_voice_combo') and self.xunfei_voice_combo.count() > 0:
                self.xunfei_voice_combo.setCurrentIndex(0)

            # ElevenLabs默认设置
            if hasattr(self, 'elevenlabs_voice_combo') and self.elevenlabs_voice_combo.count() > 0:
                self.elevenlabs_voice_combo.setCurrentIndex(0)

            if hasattr(self, 'elevenlabs_stability_slider'):
                self.elevenlabs_stability_slider.setValue(50)

            if hasattr(self, 'elevenlabs_similarity_slider'):
                self.elevenlabs_similarity_slider.setValue(50)

            logger.info("默认配音设置已加载")

        except Exception as e:
            logger.error(f"加载默认配音设置失败: {e}")

    def save_settings(self):
        """保存设置"""
        try:
            # 保存Edge-TTS设置
            if hasattr(self, 'edge_voice_combo'):
                self.config_manager.set_setting('edge_tts.voice', self.edge_voice_combo.currentText())

            if hasattr(self, 'edge_speed_slider'):
                self.config_manager.set_setting('edge_tts.speed', self.edge_speed_slider.value())

            if hasattr(self, 'edge_pitch_slider'):
                self.config_manager.set_setting('edge_tts.pitch', self.edge_pitch_slider.value())

            # 保存CosyVoice设置
            if hasattr(self, 'cosyvoice_path_input'):
                self.config_manager.set_setting('cosyvoice.model_path', self.cosyvoice_path_input.text())

            if hasattr(self, 'cosyvoice_voice_combo'):
                self.config_manager.set_setting('cosyvoice.voice', self.cosyvoice_voice_combo.currentText())

            # 保存TTSMaker设置
            if hasattr(self, 'ttsmaker_key_input'):
                self.config_manager.set_setting('ttsmaker.api_key', self.ttsmaker_key_input.text())

            if hasattr(self, 'ttsmaker_voice_combo'):
                self.config_manager.set_setting('ttsmaker.voice', self.ttsmaker_voice_combo.currentText())

            # 保存科大讯飞设置
            if hasattr(self, 'xunfei_app_id_input'):
                self.config_manager.set_setting('xunfei.app_id', self.xunfei_app_id_input.text())

            if hasattr(self, 'xunfei_api_key_input'):
                self.config_manager.set_setting('xunfei.api_key', self.xunfei_api_key_input.text())

            if hasattr(self, 'xunfei_api_secret_input'):
                self.config_manager.set_setting('xunfei.api_secret', self.xunfei_api_secret_input.text())

            if hasattr(self, 'xunfei_voice_combo'):
                self.config_manager.set_setting('xunfei.voice', self.xunfei_voice_combo.currentText())

            # 保存ElevenLabs设置
            if hasattr(self, 'elevenlabs_key_input'):
                self.config_manager.set_setting('elevenlabs.api_key', self.elevenlabs_key_input.text())

            if hasattr(self, 'elevenlabs_voice_combo'):
                self.config_manager.set_setting('elevenlabs.voice', self.elevenlabs_voice_combo.currentText())

            if hasattr(self, 'elevenlabs_stability_slider'):
                self.config_manager.set_setting('elevenlabs.stability', self.elevenlabs_stability_slider.value())

            if hasattr(self, 'elevenlabs_similarity_slider'):
                self.config_manager.set_setting('elevenlabs.similarity', self.elevenlabs_similarity_slider.value())

            # 保存配置到文件
            self.config_manager._save_config()

            QMessageBox.information(self, "保存", "设置已保存")
            logger.info("AI配音设置已保存")

        except Exception as e:
            logger.error(f"保存配音设置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存失败: {e}")
    
    def reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(
            self, "确认", "确定要重置所有配音设置吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.load_settings()
            QMessageBox.information(self, "重置", "设置已重置")
