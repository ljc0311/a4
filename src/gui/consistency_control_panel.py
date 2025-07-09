# -*- coding: utf-8 -*-
"""
一致性控制面板
提供可视化的角色场景一致性管理界面
"""

import json
import os
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QGroupBox, QLabel, QLineEdit, QTextEdit, QPushButton, QSlider,
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QProgressBar,
    QScrollArea, QFrame, QSplitter, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QDialog, QDialogButtonBox, QApplication
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt5.QtGui import QFont, QPixmap, QIcon, QPalette, QColor

from src.utils.logger import logger
from src.processors.consistency_enhanced_image_processor import ConsistencyConfig, ConsistencyData
from src.processors.text_processor import StoryboardResult
from src.utils.character_scene_manager import CharacterSceneManager
from src.utils.character_scene_sync import register_consistency_panel, notify_character_changed, notify_scene_changed
from src.processors.prompt_optimizer import PromptOptimizer
from src.utils.character_detection_config import CharacterDetectionConfig
from src.utils.baidu_translator import translate_text, is_configured as is_baidu_configured

class ConsistencyPreviewWorker(QObject):
    """一致性预览工作线程"""
    preview_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, processor, storyboard, config):
        super().__init__()
        self.processor = processor
        self.storyboard = storyboard
        self.config = config
    
    def run(self):
        try:
            preview_data = self.processor.get_consistency_preview(self.storyboard, self.config)
            self.preview_ready.emit(preview_data)
        except Exception as e:
            self.error_occurred.emit(str(e))

class CharacterEditor(QDialog):
    """角色编辑器对话框"""
    
    def __init__(self, character_data: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        self.character_data = character_data or {}
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        self.setWindowTitle("角色编辑器")
        self.setModal(True)
        self.resize(500, 600)
        
        layout = QVBoxLayout(self)
        
        # 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QGridLayout(basic_group)
        
        basic_layout.addWidget(QLabel("角色名称:"), 0, 0)
        self.name_edit = QLineEdit()
        basic_layout.addWidget(self.name_edit, 0, 1)

        basic_layout.addWidget(QLabel("别名/昵称:"), 1, 0)
        self.aliases_edit = QLineEdit()
        self.aliases_edit.setPlaceholderText("输入角色的别名或昵称，多个别名用逗号分隔（如：青山,小山）")
        basic_layout.addWidget(self.aliases_edit, 1, 1)

        basic_layout.addWidget(QLabel("角色描述:"), 2, 0)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        basic_layout.addWidget(self.description_edit, 2, 1)
        
        layout.addWidget(basic_group)
        
        # 外貌特征
        appearance_group = QGroupBox("外貌特征")
        appearance_layout = QGridLayout(appearance_group)
        
        appearance_layout.addWidget(QLabel("外貌描述:"), 0, 0)
        self.appearance_edit = QTextEdit()
        self.appearance_edit.setMaximumHeight(80)
        appearance_layout.addWidget(self.appearance_edit, 0, 1)
        
        appearance_layout.addWidget(QLabel("服装描述:"), 1, 0)
        self.clothing_edit = QTextEdit()
        self.clothing_edit.setMaximumHeight(80)
        appearance_layout.addWidget(self.clothing_edit, 1, 1)
        
        layout.addWidget(appearance_group)
        
        # 一致性提示词
        consistency_group = QGroupBox("一致性提示词")
        consistency_layout = QVBoxLayout(consistency_group)
        
        self.consistency_edit = QTextEdit()
        self.consistency_edit.setMaximumHeight(100)
        self.consistency_edit.setPlaceholderText("输入用于保持角色一致性的提示词...")
        consistency_layout.addWidget(self.consistency_edit)
        
        layout.addWidget(consistency_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_data(self):
        """加载角色数据"""
        if self.character_data:
            self.name_edit.setText(self.character_data.get('name', ''))
            # 加载别名
            aliases = self.character_data.get('aliases', [])
            if isinstance(aliases, list):
                self.aliases_edit.setText(', '.join(aliases))
            else:
                self.aliases_edit.setText('')
            self.description_edit.setPlainText(self.character_data.get('description', ''))
            
            # 处理外貌信息（可能是字符串或字典）
            appearance = self.character_data.get('appearance', '')
            if isinstance(appearance, dict):
                # 如果是字典，提取主要信息
                appearance_parts = []
                for key, value in appearance.items():
                    if value and isinstance(value, str):
                        appearance_parts.append(f"{key}: {value}")
                appearance = "; ".join(appearance_parts)
            elif not isinstance(appearance, str):
                appearance = str(appearance)
            self.appearance_edit.setPlainText(appearance)
            
            # 处理服装信息（可能是字符串或字典）
            clothing = self.character_data.get('clothing', '')
            if isinstance(clothing, dict):
                # 如果是字典，提取主要信息
                clothing_parts = []
                for key, value in clothing.items():
                    if value and isinstance(value, str):
                        clothing_parts.append(f"{key}: {value}")
                clothing = "; ".join(clothing_parts)
            elif not isinstance(clothing, str):
                clothing = str(clothing)
            self.clothing_edit.setPlainText(clothing)
            
            self.consistency_edit.setPlainText(self.character_data.get('consistency_prompt', ''))
    
    def get_data(self) -> Dict[str, Any]:
        """获取编辑后的数据"""
        return {
            'name': self.name_edit.text().strip(),
            'aliases': [a.strip() for a in self.aliases_edit.text().split(',') if a.strip()],
            'description': self.description_edit.toPlainText().strip(),
            'appearance': self.appearance_edit.toPlainText().strip(),
            'clothing': self.clothing_edit.toPlainText().strip(),
            'consistency_prompt': self.consistency_edit.toPlainText().strip()
        }

class SceneEditor(QDialog):
    """场景编辑器对话框"""
    
    def __init__(self, scene_data: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        self.scene_data = scene_data or {}
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        self.setWindowTitle("场景编辑器")
        self.setModal(True)
        self.resize(500, 600)
        
        layout = QVBoxLayout(self)
        
        # 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QGridLayout(basic_group)
        
        basic_layout.addWidget(QLabel("场景名称:"), 0, 0)
        self.name_edit = QLineEdit()
        basic_layout.addWidget(self.name_edit, 0, 1)
        
        basic_layout.addWidget(QLabel("场景描述:"), 1, 0)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        basic_layout.addWidget(self.description_edit, 1, 1)
        
        layout.addWidget(basic_group)
        
        # 环境特征
        environment_group = QGroupBox("环境特征")
        environment_layout = QGridLayout(environment_group)
        
        environment_layout.addWidget(QLabel("环境描述:"), 0, 0)
        self.environment_edit = QTextEdit()
        self.environment_edit.setMaximumHeight(80)
        environment_layout.addWidget(self.environment_edit, 0, 1)
        
        environment_layout.addWidget(QLabel("光线描述:"), 1, 0)
        self.lighting_edit = QTextEdit()
        self.lighting_edit.setMaximumHeight(60)
        environment_layout.addWidget(self.lighting_edit, 1, 1)
        
        environment_layout.addWidget(QLabel("氛围描述:"), 2, 0)
        self.atmosphere_edit = QTextEdit()
        self.atmosphere_edit.setMaximumHeight(60)
        environment_layout.addWidget(self.atmosphere_edit, 2, 1)
        
        layout.addWidget(environment_group)
        
        # 一致性提示词
        consistency_group = QGroupBox("一致性提示词")
        consistency_layout = QVBoxLayout(consistency_group)
        
        self.consistency_edit = QTextEdit()
        self.consistency_edit.setMaximumHeight(100)
        self.consistency_edit.setPlaceholderText("输入用于保持场景一致性的提示词...")
        consistency_layout.addWidget(self.consistency_edit)
        
        layout.addWidget(consistency_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_data(self):
        """加载场景数据"""
        if self.scene_data:
            self.name_edit.setText(self.scene_data.get('name', ''))
            self.description_edit.setPlainText(self.scene_data.get('description', ''))
            
            # 处理环境信息（可能是字符串或字典）
            environment = self.scene_data.get('environment', '')
            if isinstance(environment, dict):
                # 如果是字典，提取主要信息
                env_parts = []
                for key, value in environment.items():
                    if value and isinstance(value, (str, list)):
                        if isinstance(value, list):
                            value = ", ".join(str(v) for v in value)
                        env_parts.append(f"{key}: {value}")
                environment = "; ".join(env_parts)
            elif not isinstance(environment, str):
                environment = str(environment)
            self.environment_edit.setPlainText(environment)
            
            # 处理光线信息（可能是字符串或字典）
            lighting = self.scene_data.get('lighting', '')
            if isinstance(lighting, dict):
                # 如果是字典，提取主要信息
                lighting_parts = []
                for key, value in lighting.items():
                    if value and isinstance(value, (str, list)):
                        if isinstance(value, list):
                            value = ", ".join(str(v) for v in value)
                        lighting_parts.append(f"{key}: {value}")
                lighting = "; ".join(lighting_parts)
            elif not isinstance(lighting, str):
                lighting = str(lighting)
            self.lighting_edit.setPlainText(lighting)
            
            # 处理氛围信息（可能是字符串或字典）
            atmosphere = self.scene_data.get('atmosphere', '')
            if isinstance(atmosphere, dict):
                # 如果是字典，提取主要信息
                atmosphere_parts = []
                for key, value in atmosphere.items():
                    if value and isinstance(value, (str, list)):
                        if isinstance(value, list):
                            value = ", ".join(str(v) for v in value)
                        atmosphere_parts.append(f"{key}: {value}")
                atmosphere = "; ".join(atmosphere_parts)
            elif not isinstance(atmosphere, str):
                atmosphere = str(atmosphere)
            self.atmosphere_edit.setPlainText(atmosphere)
            
            self.consistency_edit.setPlainText(self.scene_data.get('consistency_prompt', ''))
    
    def get_data(self) -> Dict[str, Any]:
        """获取编辑后的数据"""
        return {
            'name': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'environment': self.environment_edit.toPlainText().strip(),
            'lighting': self.lighting_edit.toPlainText().strip(),
            'atmosphere': self.atmosphere_edit.toPlainText().strip(),
            'consistency_prompt': self.consistency_edit.toPlainText().strip()
        }

class ConsistencyControlPanel(QWidget):
    """一致性控制面板"""
    
    # 信号定义
    config_changed = pyqtSignal(object)  # ConsistencyConfig
    preview_requested = pyqtSignal()
    generate_requested = pyqtSignal(object, object)  # storyboard, config
    
    def __init__(self, image_processor, project_manager, parent=None):
        super().__init__(parent)
        self.image_processor = image_processor
        self.project_manager = project_manager
        self.parent_window = parent  # 添加parent_window属性
        self.cs_manager = None  # 将在image_processor可用时初始化
        self.current_storyboard = None
        self.current_config = ConsistencyConfig()
        self.preview_worker = None
        self.preview_thread = None
        self.llm_api = None
        
        # 初始化LLM API
        self._init_llm_api()
        
        # 初始化提示词优化器（延迟初始化，等待cs_manager可用）
        self.prompt_optimizer = None
        
        self.init_ui()
        self.setup_connections()

        # 注册到同步管理器
        register_consistency_panel(self)

        # 延迟加载数据，确保所有组件都已初始化
        QTimer.singleShot(100, self.load_character_scene_data)
    
    def _init_llm_api(self):
        """初始化LLM服务"""
        try:
            from src.core.service_manager import ServiceManager, ServiceType

            service_manager = ServiceManager()
            llm_service = service_manager.get_service(ServiceType.LLM)

            if llm_service:
                self.llm_service = llm_service
                logger.info("LLM服务初始化成功")
            else:
                logger.warning("LLM服务未找到")
                self.llm_service = None
        except Exception as e:
            logger.warning(f"LLM服务初始化失败: {e}")
            self.llm_service = None
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 配置选项卡
        self.config_tab = self.create_config_tab()
        self.tab_widget.addTab(self.config_tab, "一致性配置")
        
        # 角色管理选项卡
        self.character_tab = self.create_character_tab()
        self.tab_widget.addTab(self.character_tab, "角色管理")
        
        # 场景管理选项卡
        self.scene_tab = self.create_scene_tab()
        self.tab_widget.addTab(self.scene_tab, "场景管理")
        
        # 高级优化选项卡
        self.advanced_tab = self.create_advanced_tab()
        self.tab_widget.addTab(self.advanced_tab, "高级优化")
        
        # 预览选项卡
        self.preview_tab = self.create_preview_tab()
        self.tab_widget.addTab(self.preview_tab, "一致性预览")
        
        layout.addWidget(self.tab_widget)
        
        # 底部控制按钮（移除生成预览和开始生成按钮）
        button_layout = QHBoxLayout()

        button_layout.addStretch()

        self.export_config_btn = QPushButton("导出配置")
        button_layout.addWidget(self.export_config_btn)

        self.import_config_btn = QPushButton("导入配置")
        button_layout.addWidget(self.import_config_btn)

        layout.addLayout(button_layout)
    
    def create_config_tab(self) -> QWidget:
        """创建配置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 基本设置
        basic_group = QGroupBox("基本设置")
        basic_layout = QGridLayout(basic_group)
        
        # 启用角色一致性
        self.enable_char_cb = QCheckBox("启用角色一致性")
        self.enable_char_cb.setChecked(True)
        basic_layout.addWidget(self.enable_char_cb, 0, 0)
        
        # 启用场景一致性
        self.enable_scene_cb = QCheckBox("启用场景一致性")
        self.enable_scene_cb.setChecked(True)
        basic_layout.addWidget(self.enable_scene_cb, 0, 1)
        
        # 自动提取新元素
        self.auto_extract_cb = QCheckBox("自动提取新角色和场景")
        self.auto_extract_cb.setChecked(True)
        basic_layout.addWidget(self.auto_extract_cb, 1, 0)
        
        # 预留位置
        basic_layout.addWidget(QLabel(""), 1, 1)
        
        layout.addWidget(basic_group)
        
        # 权重设置
        weight_group = QGroupBox("权重设置")
        weight_layout = QGridLayout(weight_group)
        
        # 一致性强度
        weight_layout.addWidget(QLabel("一致性强度:"), 0, 0)
        self.consistency_strength_slider = QSlider(Qt.Horizontal)
        self.consistency_strength_slider.setRange(0, 100)
        self.consistency_strength_slider.setValue(70)
        self.consistency_strength_label = QLabel("0.7")
        weight_layout.addWidget(self.consistency_strength_slider, 0, 1)
        weight_layout.addWidget(self.consistency_strength_label, 0, 2)
        
        # 角色权重
        weight_layout.addWidget(QLabel("角色权重:"), 1, 0)
        self.character_weight_slider = QSlider(Qt.Horizontal)
        self.character_weight_slider.setRange(0, 100)
        self.character_weight_slider.setValue(40)
        self.character_weight_label = QLabel("0.4")
        weight_layout.addWidget(self.character_weight_slider, 1, 1)
        weight_layout.addWidget(self.character_weight_label, 1, 2)
        
        # 场景权重
        weight_layout.addWidget(QLabel("场景权重:"), 2, 0)
        self.scene_weight_slider = QSlider(Qt.Horizontal)
        self.scene_weight_slider.setRange(0, 100)
        self.scene_weight_slider.setValue(30)
        self.scene_weight_label = QLabel("0.3")
        weight_layout.addWidget(self.scene_weight_slider, 2, 1)
        weight_layout.addWidget(self.scene_weight_label, 2, 2)
        
        # 风格权重
        weight_layout.addWidget(QLabel("风格权重:"), 3, 0)
        self.style_weight_slider = QSlider(Qt.Horizontal)
        self.style_weight_slider.setRange(0, 100)
        self.style_weight_slider.setValue(30)
        self.style_weight_label = QLabel("0.3")
        weight_layout.addWidget(self.style_weight_slider, 3, 1)
        weight_layout.addWidget(self.style_weight_label, 3, 2)
        
        layout.addWidget(weight_group)
        
        layout.addStretch()
        return widget
    
    def create_character_tab(self) -> QWidget:
        """创建角色管理选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.add_character_btn = QPushButton("添加角色")
        toolbar_layout.addWidget(self.add_character_btn)
        
        self.edit_character_btn = QPushButton("编辑角色")
        self.edit_character_btn.setEnabled(False)
        toolbar_layout.addWidget(self.edit_character_btn)
        
        self.delete_character_btn = QPushButton("删除角色")
        self.delete_character_btn.setEnabled(False)
        toolbar_layout.addWidget(self.delete_character_btn)
        
        toolbar_layout.addStretch()
        
        self.refresh_character_btn = QPushButton("刷新角色")
        toolbar_layout.addWidget(self.refresh_character_btn)
        
        layout.addLayout(toolbar_layout)
        
        # 角色列表
        self.character_table = QTableWidget()
        self.character_table.setColumnCount(4)
        self.character_table.setHorizontalHeaderLabels(["角色名称", "描述", "外貌", "一致性提示词"])
        self.character_table.horizontalHeader().setStretchLastSection(True)
        self.character_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.character_table)
        
        return widget
    
    def create_scene_tab(self) -> QWidget:
        """创建场景管理选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.add_scene_btn = QPushButton("添加场景")
        toolbar_layout.addWidget(self.add_scene_btn)
        
        self.edit_scene_btn = QPushButton("编辑场景")
        self.edit_scene_btn.setEnabled(False)
        toolbar_layout.addWidget(self.edit_scene_btn)
        
        self.delete_scene_btn = QPushButton("删除场景")
        self.delete_scene_btn.setEnabled(False)
        toolbar_layout.addWidget(self.delete_scene_btn)
        
        toolbar_layout.addStretch()
        
        self.refresh_scene_btn = QPushButton("刷新场景")
        toolbar_layout.addWidget(self.refresh_scene_btn)
        
        layout.addLayout(toolbar_layout)
        
        # 场景列表
        self.scene_table = QTableWidget()
        self.scene_table.setColumnCount(5)
        self.scene_table.setHorizontalHeaderLabels(["场景名称", "描述", "环境", "光线", "一致性提示词"])
        self.scene_table.horizontalHeader().setStretchLastSection(True)
        self.scene_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.scene_table)
        
        return widget
    
    def create_advanced_tab(self) -> QWidget:
        """创建高级优化选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # LLM优化设置
        llm_group = QGroupBox("LLM智能优化")
        llm_layout = QVBoxLayout(llm_group)
        
        # 启用LLM优化
        self.use_llm_cb = QCheckBox("启用LLM提示词优化")
        self.use_llm_cb.setChecked(False)  # 默认关闭
        llm_layout.addWidget(self.use_llm_cb)
        
        # 优化说明
        info_label = QLabel("注意：LLM优化功能需要配置有效的LLM API，\n可能会增加处理时间和API调用成本。")
        info_label.setStyleSheet("color: #666; font-size: 12px; padding: 10px;")
        info_label.setWordWrap(True)
        llm_layout.addWidget(info_label)
        
        # 优化选项
        options_layout = QGridLayout()
        
        # 优化强度
        options_layout.addWidget(QLabel("优化强度:"), 0, 0)
        self.llm_strength_slider = QSlider(Qt.Horizontal)
        self.llm_strength_slider.setRange(1, 10)
        self.llm_strength_slider.setValue(5)
        self.llm_strength_label = QLabel("5")
        options_layout.addWidget(self.llm_strength_slider, 0, 1)
        options_layout.addWidget(self.llm_strength_label, 0, 2)
        
        # 优化模式
        options_layout.addWidget(QLabel("优化模式:"), 1, 0)
        self.llm_mode_combo = QComboBox()
        self.llm_mode_combo.addItems(["快速优化", "标准优化", "深度优化"])
        self.llm_mode_combo.setCurrentIndex(1)
        options_layout.addWidget(self.llm_mode_combo, 1, 1, 1, 2)
        
        llm_layout.addLayout(options_layout)
        
        # 启用状态控制
        self.use_llm_cb.toggled.connect(self.on_llm_toggle)
        self.llm_strength_slider.setEnabled(False)
        self.llm_mode_combo.setEnabled(False)
        
        layout.addWidget(llm_group)
        
        # 翻译设置
        translate_group = QGroupBox("双语翻译")
        translate_layout = QVBoxLayout(translate_group)
        
        self.enable_translation_cb = QCheckBox("启用中英文双语提示词生成")
        self.enable_translation_cb.setChecked(False)  # 默认关闭，用户需要手动启用
        translate_layout.addWidget(self.enable_translation_cb)
        
        translate_info = QLabel("将增强后的提示词翻译为中英文对照格式，\n便于不同AI绘图工具使用。")
        translate_info.setStyleSheet("color: #666; font-size: 12px; padding: 10px;")
        translate_info.setWordWrap(True)
        translate_layout.addWidget(translate_info)
        
        layout.addWidget(translate_group)
        
        layout.addStretch()
        
        return widget
    
    def on_llm_toggle(self, enabled):
        """LLM优化开关切换"""
        self.llm_strength_slider.setEnabled(enabled)
        self.llm_mode_combo.setEnabled(enabled)
        self.on_config_changed()
    
    def create_preview_tab(self) -> QWidget:
        """创建预览选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 预览信息
        info_layout = QHBoxLayout()
        
        self.preview_status_label = QLabel("状态: 等待分镜数据")
        info_layout.addWidget(self.preview_status_label)
        
        info_layout.addStretch()
        
        self.update_preview_btn = QPushButton("更新预览")
        self.update_preview_btn.setEnabled(False)
        info_layout.addWidget(self.update_preview_btn)
        
        layout.addLayout(info_layout)
        
        # 预览内容
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("一致性预览信息将在这里显示...")
        
        layout.addWidget(self.preview_text)
        
        return widget
    
    def setup_connections(self):
        """设置信号连接"""
        # 配置变化信号
        self.enable_char_cb.toggled.connect(self.on_config_changed)
        self.enable_scene_cb.toggled.connect(self.on_config_changed)
        self.auto_extract_cb.toggled.connect(self.on_config_changed)
        self.use_llm_cb.toggled.connect(self.on_config_changed)
        self.enable_translation_cb.toggled.connect(self.on_config_changed)
        
        # 高级优化信号
        self.llm_strength_slider.valueChanged.connect(self.on_llm_strength_changed)
        self.llm_mode_combo.currentTextChanged.connect(self.on_config_changed)
        
        # 滑块变化信号
        self.consistency_strength_slider.valueChanged.connect(self.on_strength_changed)
        self.character_weight_slider.valueChanged.connect(self.on_char_weight_changed)
        self.scene_weight_slider.valueChanged.connect(self.on_scene_weight_changed)
        self.style_weight_slider.valueChanged.connect(self.on_style_weight_changed)
        
        # 角色管理信号
        self.add_character_btn.clicked.connect(self.add_character)
        self.edit_character_btn.clicked.connect(self.edit_character)
        self.delete_character_btn.clicked.connect(self.delete_character)
        self.refresh_character_btn.clicked.connect(self.refresh_characters)
        self.character_table.itemSelectionChanged.connect(self.on_character_selection_changed)
        
        # 场景管理信号
        self.add_scene_btn.clicked.connect(self.add_scene)
        self.edit_scene_btn.clicked.connect(self.edit_scene)
        self.delete_scene_btn.clicked.connect(self.delete_scene)
        self.refresh_scene_btn.clicked.connect(self.refresh_scenes)
        self.scene_table.itemSelectionChanged.connect(self.on_scene_selection_changed)
        
        # 按钮信号（移除生成预览和开始生成按钮的信号连接）
        self.update_preview_btn.clicked.connect(self.update_preview)
        self.export_config_btn.clicked.connect(self.export_config)
        self.import_config_btn.clicked.connect(self.import_config)
    
    def on_config_changed(self):
        """配置变化处理"""
        self.update_config()
        self.config_changed.emit(self.current_config)
    
    def on_strength_changed(self, value):
        """一致性强度变化"""
        strength = value / 100.0
        self.consistency_strength_label.setText(f"{strength:.1f}")
        self.on_config_changed()
    
    def on_char_weight_changed(self, value):
        """角色权重变化"""
        weight = value / 100.0
        self.character_weight_label.setText(f"{weight:.1f}")
        self.on_config_changed()
    
    def on_scene_weight_changed(self, value):
        """场景权重变化"""
        weight = value / 100.0
        self.scene_weight_label.setText(f"{weight:.1f}")
        self.on_config_changed()
    
    def on_style_weight_changed(self, value):
        """风格权重变化"""
        weight = value / 100.0
        self.style_weight_label.setText(f"{weight:.1f}")
        self.on_config_changed()
    
    def on_llm_strength_changed(self, value):
        """LLM优化强度变化"""
        self.llm_strength_label.setText(str(value))
        self.on_config_changed()
    
    def update_config(self):
        """更新配置对象"""
        self.current_config = ConsistencyConfig(
            enable_character_consistency=self.enable_char_cb.isChecked(),
            enable_scene_consistency=self.enable_scene_cb.isChecked(),
            consistency_strength=self.consistency_strength_slider.value() / 100.0,
            auto_extract_new_elements=self.auto_extract_cb.isChecked(),
            use_llm_enhancement=False,  # LLM功能已移到高级优化
            character_weight=self.character_weight_slider.value() / 100.0,
            scene_weight=self.scene_weight_slider.value() / 100.0,
            style_weight=self.style_weight_slider.value() / 100.0
        )
    
    def set_storyboard(self, storyboard: StoryboardResult):
        """设置分镜数据"""
        self.current_storyboard = storyboard
        self.update_preview_btn.setEnabled(True)

        self.preview_status_label.setText(f"状态: 已加载 {len(storyboard.shots)} 个分镜，点击'更新预览'按钮查看详细信息")

        # 🔧 修复：禁用自动提取功能，避免生成无用的"镜头场景_"数据
        # 用户反馈这些自动生成的场景数据是无用的，因此禁用此功能
        # self._extract_and_save_storyboard_data(storyboard)
        logger.info("已禁用自动提取分镜数据功能，避免生成无用的临时场景数据")

        # 移除自动更新预览，改为用户手动点击按钮触发
        # self.update_preview()
    
    def update_button_states(self):
        """更新按钮状态"""
        try:
            # 检查是否有角色或场景数据
            has_character_data = False
            has_scene_data = False
            
            if self.cs_manager:
                characters = self.cs_manager.get_all_characters()
                scenes = self.cs_manager.get_all_scenes()
                has_character_data = len(characters) > 0
                has_scene_data = len(scenes) > 0
            
            # 如果有分镜数据或者有角色/场景数据，则启用按钮
            has_data = self.current_storyboard is not None or has_character_data or has_scene_data

            self.update_preview_btn.setEnabled(has_data)
            
            # 更新状态标签
            if self.current_storyboard:
                self.preview_status_label.setText(f"状态: 已加载 {len(self.current_storyboard.shots)} 个分镜")
            elif has_character_data or has_scene_data:
                char_count = len(self.cs_manager.get_all_characters()) if self.cs_manager else 0
                scene_count = len(self.cs_manager.get_all_scenes()) if self.cs_manager else 0
                self.preview_status_label.setText(f"状态: 已加载 {char_count} 个角色, {scene_count} 个场景")
            else:
                self.preview_status_label.setText("状态: 无数据")
                
        except Exception as e:
            logger.error(f"更新按钮状态失败: {e}")
    
    def load_character_scene_data(self):
        """加载角色场景数据"""
        import re  # 添加re模块导入
        try:
            # 检查cs_manager是否可用，如果不可用尝试重新初始化
            if not self.cs_manager:
                logger.warning("角色场景管理器未初始化，尝试重新初始化")
                self._try_reinit_cs_manager()
                
                # 如果仍然不可用，跳过数据加载
                if not self.cs_manager:
                    logger.warning("角色场景管理器重新初始化失败，跳过数据加载")
                    self.update_button_states()  # 仍然更新按钮状态
                    return
                
            # 初始化提示词优化器（如果还没有初始化）
            if not self.prompt_optimizer and self.cs_manager:
                from src.processors.prompt_optimizer import PromptOptimizer
                self.prompt_optimizer = PromptOptimizer(self.llm_api, self.cs_manager)
                logger.info("提示词优化器初始化完成")
                
            # 加载角色数据
            characters = self.cs_manager.get_all_characters()
            self.character_table.setRowCount(len(characters))
            
            for row, (char_id, char_data) in enumerate(characters.items()):
                # 处理不同的数据格式
                name = char_data.get('name', '')
                description = char_data.get('description', '')
                
                # 处理外貌信息（可能是字符串或字典）
                appearance = char_data.get('appearance', '')
                if isinstance(appearance, dict):
                    # 如果是字典，提取主要信息
                    appearance_parts = []
                    for key, value in appearance.items():
                        if value and isinstance(value, str):
                            appearance_parts.append(f"{key}: {value}")
                    appearance = "; ".join(appearance_parts)
                elif not isinstance(appearance, str):
                    appearance = str(appearance)
                
                consistency_prompt = char_data.get('consistency_prompt', '')
                
                self.character_table.setItem(row, 0, QTableWidgetItem(name))
                self.character_table.setItem(row, 1, QTableWidgetItem(description))
                self.character_table.setItem(row, 2, QTableWidgetItem(appearance))
                self.character_table.setItem(row, 3, QTableWidgetItem(consistency_prompt))
                
                # 存储ID
                self.character_table.item(row, 0).setData(Qt.UserRole, char_id)
            
            # 加载场景数据
            all_scenes = self.cs_manager.get_all_scenes()
            
            # 直接使用所有场景数据（源头已过滤）
            filtered_scenes = all_scenes
            
            self.scene_table.setRowCount(len(filtered_scenes))
            
            # 对过滤后的场景进行自然排序
            def natural_sort_key(item):
                scene_id, scene_data = item
                scene_name = scene_data.get('name', '')
                # 提取场景名称中的数字进行排序
                numbers = re.findall(r'\d+', scene_name)
                if numbers:
                    return (0, int(numbers[0]), scene_name)  # 优先按数字排序
                else:
                    return (1, 0, scene_name)  # 非数字场景排在后面
            
            sorted_scenes = sorted(filtered_scenes.items(), key=natural_sort_key)
            
            for row, (scene_id, scene_data) in enumerate(sorted_scenes):
                name = scene_data.get('name', '')
                description = scene_data.get('description', '')
                
                # 处理环境信息（可能是字符串或字典）
                environment = scene_data.get('environment', '')
                if isinstance(environment, dict):
                    # 如果是字典，提取主要信息
                    env_parts = []
                    for key, value in environment.items():
                        if value and isinstance(value, (str, list)):
                            if isinstance(value, list):
                                value = ", ".join(str(v) for v in value)
                            env_parts.append(f"{key}: {value}")
                    environment = "; ".join(env_parts)
                elif not isinstance(environment, str):
                    environment = str(environment)
                
                # 处理光线信息（可能是字符串或字典）
                lighting = scene_data.get('lighting', '')
                if isinstance(lighting, dict):
                    lighting_parts = []
                    for key, value in lighting.items():
                        if value and isinstance(value, str):
                            lighting_parts.append(f"{key}: {value}")
                    lighting = "; ".join(lighting_parts)
                elif not isinstance(lighting, str):
                    lighting = str(lighting)
                
                consistency_prompt = scene_data.get('consistency_prompt', '')
                
                self.scene_table.setItem(row, 0, QTableWidgetItem(name))
                self.scene_table.setItem(row, 1, QTableWidgetItem(description))
                self.scene_table.setItem(row, 2, QTableWidgetItem(environment))
                self.scene_table.setItem(row, 3, QTableWidgetItem(lighting))
                self.scene_table.setItem(row, 4, QTableWidgetItem(consistency_prompt))
                
                # 存储ID
                self.scene_table.item(row, 0).setData(Qt.UserRole, scene_id)
            
            logger.info(f"加载了 {len(characters)} 个角色和 {len(filtered_scenes)} 个用户创建的场景（已过滤分镜生成的场景）")
            
            # 更新按钮状态
            self.update_button_states()
        except Exception as e:
            logger.error(f"加载角色场景数据失败: {e}")
    
    def _read_enhanced_prompts_by_shot(self):
        """从项目texts文件夹中读取每个镜头的enhanced_prompt"""
        try:
            if not hasattr(self, 'project_manager') or not self.project_manager:
                return {}
                
            if not self.project_manager.current_project:
                return {}
            project_name = self.project_manager.current_project.get('project_name')
            if not project_name:
                return {}
                
            # 构建prompt.json文件路径
            if hasattr(self.parent_window, 'project_manager') and self.parent_window.project_manager.current_project:
                project_dir = self.parent_window.project_manager.get_current_project_path()
                if project_dir:
                    prompt_file_path = os.path.join(project_dir, 'texts', 'prompt.json')
                else:
                    return {}
            else:
                return {}
            
            if not os.path.exists(prompt_file_path):
                logger.debug(f"prompt.json文件不存在: {prompt_file_path}")
                return {}
                
            # 读取文件内容
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 获取每个镜头的enhanced_prompt（适配当前prompt.json格式）
            shot_prompts = {}
            
            # 新格式：包含scenes字段的结构化数据
            if 'scenes' in data:
                scenes = data['scenes']
                shot_counter = 1
                
                for scene_name, shots in scenes.items():
                    for shot in shots:
                        if 'enhanced_prompt' in shot and shot['enhanced_prompt']:
                            shot_prompts[shot_counter] = shot['enhanced_prompt']
                        elif 'original_description' in shot and shot['original_description']:
                            shot_prompts[shot_counter] = shot['original_description']
                        shot_counter += 1
                
                if shot_prompts:
                    logger.info(f"成功读取prompt.json中{len(shot_prompts)}个镜头的enhanced_prompt")
                    return shot_prompts
                else:
                    logger.warning("prompt.json中的scenes数据为空")
                    return {}
            
            # 兼容旧格式：直接包含enhanced_prompt字段（作为第一个镜头）
            elif 'enhanced_prompt' in data:
                enhanced_content = data['enhanced_prompt']
                logger.info(f"成功读取prompt.json中的增强内容作为第一个镜头: {len(enhanced_content)}字符")
                return {1: enhanced_content}
            
            # 如果都没有找到，返回空字典
            return {}
                
        except Exception as e:
            logger.error(f"读取enhanced_prompts失败: {e}")
            return {}
    
    def _read_generated_text_from_file(self):
        """从项目texts文件夹中读取generate_text文件内容（已废弃，保留兼容性）"""
        try:
            if not hasattr(self, 'project_manager') or not self.project_manager:
                return None
                
            if not self.project_manager.current_project:
                return None
            project_name = self.project_manager.current_project.get('project_name')
            if not project_name:
                return None
                
            # 构建prompt.json文件路径（替代废弃的generate_text.json）
            if hasattr(self.parent_window, 'project_manager') and self.parent_window.project_manager.current_project:
                project_dir = self.parent_window.project_manager.get_current_project_path()
                if project_dir:
                    prompt_file_path = os.path.join(project_dir, 'texts', 'prompt.json')
                else:
                    return None
            else:
                return None
            
            if not os.path.exists(prompt_file_path):
                logger.debug(f"prompt.json文件不存在: {prompt_file_path}")
                return None
                
            # 读取文件内容
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 获取增强后的提示词内容（适配当前prompt.json格式）
            # 新格式：包含scenes字段的结构化数据
            if 'scenes' in data:
                # 提取所有场景的增强描述
                enhanced_parts = []
                scenes = data['scenes']
                
                for scene_name, shots in scenes.items():
                    enhanced_parts.append(scene_name)
                    for shot in shots:
                        if 'enhanced_prompt' in shot and shot['enhanced_prompt']:
                            enhanced_parts.append(shot['enhanced_prompt'])
                        elif 'original_description' in shot and shot['original_description']:
                            enhanced_parts.append(shot['original_description'])
                
                if enhanced_parts:
                    enhanced_content = '\n\n'.join(enhanced_parts)
                    logger.info(f"成功读取prompt.json中的场景化增强内容: {len(enhanced_content)}字符")
                    return enhanced_content
                else:
                    logger.warning("prompt.json中的scenes数据为空")
                    return None
            
            # 兼容旧格式：直接包含enhanced_prompt或original_description字段
            elif 'enhanced_prompt' in data:
                enhanced_content = data['enhanced_prompt']
                logger.info(f"成功读取prompt.json中的增强内容: {len(enhanced_content)}字符")
                return enhanced_content
            elif 'original_description' in data:
                original_content = data['original_description']
                logger.info(f"使用prompt.json中的原始内容作为备选: {len(original_content)}字符")
                return original_content
            else:
                logger.warning("prompt.json文件格式不正确，缺少scenes、enhanced_prompt或original_description字段")
                return None
                
        except Exception as e:
            logger.error(f"读取prompt.json文件失败: {e}")
            return None
    
    def _generate_simple_bilingual_prompt(self, description):
        """生成简单的双语提示词（中文原文 + 英文翻译）"""
        try:
            # 如果有翻译API，使用翻译API
            if hasattr(self, 'llm_api') and self.llm_api and self.llm_api.is_configured():
                try:
                    # 使用LLM进行翻译
                    translation_prompt = f"Please translate the following Chinese prompt into pure English. Only output the English translation, do not include any Chinese characters or mixed language content. Maintain professionalism and accuracy:\n\n{description}"
                    response = self.llm_api.rewrite_text(translation_prompt)
                    if response and len(response.strip()) > 0:
                        return (description, response.strip())
                except Exception as e:
                    logger.warning(f"LLM翻译失败: {e}")
            
            # 如果没有LLM或翻译失败，使用带备用方案的翻译
            english_translation = self._translate_with_fallback(description)
            return (description, english_translation)
            
        except Exception as e:
            logger.warning(f"生成简单双语提示词失败: {e}")
            return (description, description)
            
            # 尝试加载保存的预览数据
            self._load_preview_data()
            
        except Exception as e:
            logger.error(f"加载角色场景数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.warning(self, "错误", f"加载数据失败: {e}")
            # 即使出错也要更新按钮状态
            self.update_button_states()
    
    def on_character_selection_changed(self):
        """角色选择变化"""
        has_selection = len(self.character_table.selectedItems()) > 0
        self.edit_character_btn.setEnabled(has_selection)
        self.delete_character_btn.setEnabled(has_selection)
    
    def on_scene_selection_changed(self):
        """场景选择变化"""
        has_selection = len(self.scene_table.selectedItems()) > 0
        self.edit_scene_btn.setEnabled(has_selection)
        self.delete_scene_btn.setEnabled(has_selection)
    
    def add_character(self):
        """添加角色"""
        editor = CharacterEditor(parent=self)
        if editor.exec_() == QDialog.Accepted:
            char_data = editor.get_data()
            if char_data['name']:
                try:
                    if self.cs_manager:
                        char_id = self.cs_manager.save_character(char_data)
                        self.load_character_scene_data()
                        # 触发同步通知
                        notify_character_changed(char_id, char_data, 'add')
                        logger.info(f"添加角色成功: {char_data['name']}")
                    else:
                        QMessageBox.warning(self, "错误", "角色场景管理器未初始化")
                except Exception as e:
                    logger.error(f"添加角色失败: {e}")
                    QMessageBox.warning(self, "错误", f"添加角色失败: {e}")
    
    def edit_character(self):
        """编辑角色"""
        current_row = self.character_table.currentRow()
        if current_row >= 0 and self.cs_manager:
            char_id = self.character_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
            char_data = self.cs_manager.get_character(char_id)

            if char_data:
                editor = CharacterEditor(char_data, parent=self)
                if editor.exec_() == QDialog.Accepted:
                    updated_data = editor.get_data()
                    try:
                        self.cs_manager.save_character(char_id, updated_data)
                        self.load_character_scene_data()
                        # 触发同步通知
                        notify_character_changed(char_id, updated_data, 'update')
                        logger.info(f"编辑角色成功: {updated_data['name']}")
                    except Exception as e:
                        logger.error(f"编辑角色失败: {e}")
                        QMessageBox.warning(self, "错误", f"编辑角色失败: {e}")
    
    def delete_character(self):
        """删除角色"""
        current_row = self.character_table.currentRow()
        if current_row >= 0 and self.cs_manager:
            char_name = self.character_table.item(current_row, 0).text()
            char_id = self.character_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)

            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除角色 '{char_name}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self.cs_manager.delete_character(char_id)
                    self.load_character_scene_data()
                    # 触发同步通知
                    notify_character_changed(char_id, {'name': char_name}, 'delete')
                    logger.info(f"删除角色成功: {char_name}")
                except Exception as e:
                    logger.error(f"删除角色失败: {e}")
                    QMessageBox.warning(self, "错误", f"删除角色失败: {e}")
    
    def add_scene(self):
        """添加场景"""
        editor = SceneEditor(parent=self)
        if editor.exec_() == QDialog.DialogCode.Accepted:
            scene_data = editor.get_data()
            if scene_data['name']:
                try:
                    if self.cs_manager:
                        scene_id = self.cs_manager.save_scene(scene_data)
                        self.load_character_scene_data()
                        # 触发同步通知
                        notify_scene_changed(scene_id, scene_data, 'add')
                        logger.info(f"添加场景成功: {scene_data['name']}")
                    else:
                        QMessageBox.warning(self, "错误", "角色场景管理器未初始化")
                except Exception as e:
                    logger.error(f"添加场景失败: {e}")
                    QMessageBox.warning(self, "错误", f"添加场景失败: {e}")
    
    def edit_scene(self):
        """编辑场景"""
        current_row = self.scene_table.currentRow()
        if current_row >= 0 and self.cs_manager:
            scene_id = self.scene_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
            scene_data = self.cs_manager.get_scene(scene_id)

            if scene_data:
                editor = SceneEditor(scene_data, parent=self)
                if editor.exec_() == QDialog.DialogCode.Accepted:
                    updated_data = editor.get_data()
                    try:
                        self.cs_manager.save_scene(scene_id, updated_data)
                        self.load_character_scene_data()
                        # 触发同步通知
                        notify_scene_changed(scene_id, updated_data, 'update')
                        logger.info(f"编辑场景成功: {updated_data['name']}")
                    except Exception as e:
                        logger.error(f"编辑场景失败: {e}")
                        QMessageBox.warning(self, "错误", f"编辑场景失败: {e}")

    def delete_scene(self):
        """删除场景"""
        current_row = self.scene_table.currentRow()
        if current_row >= 0 and self.cs_manager:
            scene_name = self.scene_table.item(current_row, 0).text()
            scene_id = self.scene_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)

            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除场景 '{scene_name}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self.cs_manager.delete_scene(scene_id)
                    self.load_character_scene_data()
                    # 触发同步通知
                    notify_scene_changed(scene_id, {'name': scene_name}, 'delete')
                    logger.info(f"删除场景成功: {scene_name}")
                except Exception as e:
                    logger.error(f"删除场景失败: {e}")
                    QMessageBox.warning(self, "错误", f"删除场景失败: {e}")
    
    def update_preview(self):
        """更新预览"""
        if not self.current_storyboard:
            return
        
        try:
            # 获取数据库中的角色和场景信息
            db_characters = []
            db_scenes = []
            
            if self.cs_manager:
                try:
                    all_characters = self.cs_manager.get_all_characters()
                    db_characters = [char_data.get('name', '') for char_data in all_characters.values() if char_data.get('name')]
                    
                    all_scenes = self.cs_manager.get_all_scenes()
                    db_scenes = [scene_data.get('name', '') for scene_data in all_scenes.values() if scene_data.get('name')]
                except Exception as e:
                    logger.warning(f"获取数据库角色场景信息失败: {e}")
            
            # 合并分镜中的角色和数据库中的角色
            storyboard_characters = list(set(self.current_storyboard.characters))
            all_characters_list = list(set(storyboard_characters + db_characters))
            
            # 合并分镜中的场景和数据库中的场景
            storyboard_scenes = list(set(self.current_storyboard.scenes))
            all_scenes_list = list(set(storyboard_scenes + db_scenes))
            
            # 生成详细的预览信息
            preview_text = "=== 一致性预览 ===\n\n"
            
            preview_text += f"分镜总数: {len(self.current_storyboard.shots)}\n"
            preview_text += f"角色数量: {len(all_characters_list)}\n"
            preview_text += f"场景数量: {len(all_scenes_list)}\n\n"
            
            preview_text += "=== 配置信息 ===\n"
            preview_text += f"角色一致性: {'启用' if self.current_config.enable_character_consistency else '禁用'}\n"
            preview_text += f"场景一致性: {'启用' if self.current_config.enable_scene_consistency else '禁用'}\n"
            preview_text += f"一致性强度: {self.current_config.consistency_strength:.1f}\n"
            preview_text += f"LLM增强: {'启用' if self.current_config.use_llm_enhancement else '禁用'}\n\n"
            
            # 显示角色信息
            if all_characters_list:
                preview_text += "=== 角色信息 ===\n"
                for char_name in sorted(all_characters_list):
                    preview_text += f"• {char_name}\n"
                preview_text += "\n"
            
            # 显示场景信息
            if all_scenes_list:
                preview_text += "=== 场景信息 ===\n"
                for scene_name in sorted(all_scenes_list):
                    preview_text += f"• {scene_name}\n"
                preview_text += "\n"
            
            preview_text += "=== 分镜预览 ===\n"
            
            # 尝试从五阶段分镜获取详细数据
            detailed_storyboard_data = self._get_five_stage_storyboard_data()
            
            if detailed_storyboard_data:
                # 🔧 修复：简化显示，删除无用的场景信息
                preview_text += "=== 分镜预览 ===\n"

                for i, scene_data in enumerate(detailed_storyboard_data):
                    storyboard_script = scene_data.get("storyboard_script", "")

                    preview_text += f"\n场景 {i+1}:\n"
                    
                    # 解析分镜脚本中的镜头信息
                    if storyboard_script:
                        # 🔧 修复：简化处理，只显示基本的镜头信息
                        shots_with_prompts = self._extract_shots_from_script(storyboard_script, "")

                        # 🔧 修复：简化预览，只显示基本的镜头信息，不进行复杂的增强处理
                        for shot_info in shots_with_prompts:
                            shot_num = shot_info['shot_number']
                            shot_description = shot_info['description']
                            shot_characters = shot_info.get('characters', '')

                            preview_text += f"镜头{shot_num}: {shot_description[:100]}{'...' if len(shot_description) > 100 else ''}\n"
                            if shot_characters:
                                preview_text += f"角色: {shot_characters}\n"
                            preview_text += "\n"
                    
                    preview_text += "\n"
            else:
                # 回退到简化显示
                for i, shot in enumerate(self.current_storyboard.shots[:5]):  # 只显示前5个
                    preview_text += f"\n分镜 {shot.shot_id}:\n"
                    preview_text += f"场景: {shot.scene}\n"
                    preview_text += f"角色: {', '.join(shot.characters) if shot.characters else '无'}\n"
                    preview_text += f"原始提示词: {shot.image_prompt}\n"
                    preview_text += "-" * 50 + "\n"
                
                if len(self.current_storyboard.shots) > 5:
                    preview_text += f"\n... 还有 {len(self.current_storyboard.shots) - 5} 个分镜\n"
            
            self.preview_text.setPlainText(preview_text)
            self.preview_status_label.setText("状态: 预览已更新")
            
            # 保存预览数据到项目
            self._save_preview_data(preview_text)
            
        except Exception as e:
            logger.error(f"更新预览失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.preview_text.setPlainText(f"预览生成失败: {e}")
    
    def _save_preview_data(self, preview_text):
        """保存预览数据到项目"""
        try:
            if hasattr(self.parent_window, 'project_manager') and self.parent_window.project_manager.current_project:
                # 获取项目管理器
                project_manager = self.parent_window.project_manager
                
                # 保存预览数据到项目配置中
                if 'consistency_preview' not in project_manager.current_project:
                    project_manager.current_project['consistency_preview'] = {}
                
                project_manager.current_project['consistency_preview'] = {
                    'preview_text': preview_text,
                    'last_updated': datetime.now().isoformat(),
                    'config': {
                        'enable_character_consistency': self.current_config.enable_character_consistency,
                        'enable_scene_consistency': self.current_config.enable_scene_consistency,
                        'consistency_strength': self.current_config.consistency_strength
                    }
                }
                
                # 保存项目
                project_manager.save_project()
                logger.info("一致性预览数据已保存到项目")
                
        except Exception as e:
            logger.error(f"保存预览数据失败: {e}")
    
    def _load_preview_data(self):
        """从项目加载预览数据"""
        try:
            if hasattr(self.parent_window, 'project_manager') and self.parent_window.project_manager.current_project:
                project_config = self.parent_window.project_manager.current_project
                
                # 检查是否有保存的预览数据
                if 'consistency_preview' in project_config:
                    preview_data = project_config['consistency_preview']
                    preview_text = preview_data.get('preview_text', '')
                    
                    if preview_text:
                        self.preview_text.setPlainText(preview_text)
                        last_updated = preview_data.get('last_updated', '')
                        if last_updated:
                            try:
                                update_time = datetime.fromisoformat(last_updated)
                                time_str = update_time.strftime('%Y-%m-%d %H:%M:%S')
                                self.preview_status_label.setText(f"状态: 已加载上次预览 (更新于 {time_str})")
                            except:
                                self.preview_status_label.setText("状态: 已加载上次预览")
                        else:
                            self.preview_status_label.setText("状态: 已加载上次预览")
                        
                        logger.info("一致性预览数据已从项目加载")
                        return True
                        
        except Exception as e:
            logger.error(f"加载预览数据失败: {e}")
        
        return False
    
    def _get_five_stage_storyboard_data(self):
        """获取五阶段分镜的详细数据"""
        try:
            # 检查主窗口是否有五阶段分镜标签页
            if not hasattr(self.parent_window, 'five_stage_storyboard_tab'):
                logger.debug("主窗口没有五阶段分镜标签页")
                return None
            
            five_stage_tab = self.parent_window.five_stage_storyboard_tab
            
            # 检查是否有第四阶段的数据
            if not hasattr(five_stage_tab, 'stage_data') or not five_stage_tab.stage_data.get(4):
                logger.debug("五阶段分镜没有第四阶段数据")
                return None
            
            # 获取第四阶段的分镜结果
            stage4_data = five_stage_tab.stage_data[4]
            storyboard_results = stage4_data.get('storyboard_results', [])
            
            if not storyboard_results:
                logger.debug("第四阶段没有分镜结果数据")
                return None
            
            logger.info(f"成功获取到 {len(storyboard_results)} 个场景的详细分镜数据")
            return storyboard_results
            
        except Exception as e:
            logger.error(f"获取五阶段分镜数据失败: {e}")
            return None
    
    
    def _extract_shots_from_script(self, storyboard_script, scene_info=""):
        """从分镜脚本中提取镜头信息（scene_info参数已废弃）"""
        try:
            shots_with_prompts = []
            lines = storyboard_script.split('\n')
            current_shot = None
            current_description = ""
            current_characters = ""
            
            for line in lines:
                line = line.strip()
                
                # 检测镜头标题
                if line.startswith('### 镜头') or line.startswith('##镜头') or '镜头' in line and line.endswith('###'):
                    # 保存上一个镜头的信息
                    if current_shot and current_description:
                        # 如果没有明确的镜头角色，从画面描述中提取
                        if not current_characters:
                            current_characters = self._extract_characters_from_description(current_description)
                        
                        shots_with_prompts.append({
                            'shot_number': current_shot,
                            'description': current_description.strip(),
                            'characters': current_characters
                        })
                    
                    # 提取镜头编号
                    import re
                    shot_match = re.search(r'镜头(\d+)', line)
                    if shot_match:
                        current_shot = shot_match.group(1)
                        current_description = ""
                        current_characters = ""
                
                # 检测镜头角色
                elif line.startswith('- **镜头角色**：') or line.startswith('**镜头角色**：'):
                    current_characters = line.replace('- **镜头角色**：', '').replace('**镜头角色**：', '').strip()
                elif line.startswith('- **镜头角色**:') or line.startswith('**镜头角色**:'):
                    current_characters = line.replace('- **镜头角色**:', '').replace('**镜头角色**:', '').strip()
                
                # 检测画面描述
                elif line.startswith('- **画面描述**：') or line.startswith('**画面描述**：'):
                    current_description = line.replace('- **画面描述**：', '').replace('**画面描述**：', '').strip()
                elif line.startswith('- **画面描述**:') or line.startswith('**画面描述**:'):
                    current_description = line.replace('- **画面描述**:', '').replace('**画面描述**:', '').strip()
            
            # 保存最后一个镜头的信息
            if current_shot and current_description:
                # 如果没有明确的镜头角色，从画面描述中提取
                if not current_characters:
                    current_characters = self._extract_characters_from_description(current_description)
                
                shots_with_prompts.append({
                    'shot_number': current_shot,
                    'description': current_description.strip(),
                    'characters': current_characters
                })
            
            logger.info(f"从分镜脚本中提取到 {len(shots_with_prompts)} 个镜头")
            return shots_with_prompts
            
        except Exception as e:
            logger.error(f"提取镜头信息失败: {e}")
            return []
    
    def _extract_characters_from_description(self, description: str) -> str:
        """
        从画面描述中提取角色信息
        
        Args:
            description: 画面描述文本
            
        Returns:
            str: 角色列表字符串，用逗号分隔
        """
        try:
            # 优先使用LLM智能提取角色
            if hasattr(self, 'llm_api') and self.llm_api and self.llm_api.is_configured():
                return self._extract_characters_with_llm(description)
            else:
                # 如果LLM不可用，使用关键词匹配作为后备方案
                return self._extract_characters_fallback(description)
        except Exception as e:
            logger.error(f"角色提取失败: {e}")
            # 出错时使用后备方案
            return self._extract_characters_fallback(description)
    
    def _extract_characters_with_llm(self, description: str) -> str:
        """
        使用LLM智能提取角色信息
        
        Args:
            description: 画面描述文本
            
        Returns:
            str: 角色列表字符串，用逗号分隔
        """
        try:
            prompt = f"""请从以下画面描述中提取出现的所有角色/人物，包括但不限于：
- 具体的人物名称（如：张三、李四、小明等）
- 角色称谓（如：主人公、主角、男主、女主等）
- 人物特征描述（如：光头大叔、年轻女子、老奶奶等）
- 职业身份（如：医生、老师、警察、店主等）
- 关系称谓（如：父亲、母亲、朋友、同事等）
- 群体角色（如：路人、行人、顾客、学生等）

画面描述：{description}

请只返回角色名称，用中文顿号（、）分隔，不要包含其他解释文字。如果没有角色，请返回空字符串。

示例输出格式：主人公、光头大叔、年轻女子"""
            
            # 使用服务管理器获取LLM服务
            from src.core.service_manager import ServiceManager, ServiceType
            import asyncio

            service_manager = ServiceManager()
            llm_service = service_manager.get_service(ServiceType.LLM)

            if llm_service:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(llm_service.generate_text(prompt))
                    response = result.data.get('content', '') if result.success else ''
                finally:
                    loop.close()
            else:
                response = ''
            
            if response and response.strip():
                # 清理响应，去除可能的多余文字
                characters_text = response.strip()
                
                # 去除常见的前缀和后缀
                prefixes_to_remove = ['角色：', '人物：', '角色有：', '人物有：', '提取到的角色：', '提取的角色：']
                for prefix in prefixes_to_remove:
                    if characters_text.startswith(prefix):
                        characters_text = characters_text[len(prefix):].strip()
                
                # 分割角色并去重
                if '、' in characters_text:
                    characters = [char.strip() for char in characters_text.split('、') if char.strip()]
                elif '，' in characters_text:
                    characters = [char.strip() for char in characters_text.split('，') if char.strip()]
                elif ',' in characters_text:
                    characters = [char.strip() for char in characters_text.split(',') if char.strip()]
                else:
                    characters = [characters_text] if characters_text else []
                
                # 标准化角色名称并去重过滤空值
                normalized_characters = []
                for char in characters:
                    if char and len(char.strip()) > 0:
                        normalized_name = CharacterDetectionConfig.normalize_character_name(char.strip())
                        normalized_characters.append(normalized_name)
                
                unique_characters = list(dict.fromkeys(normalized_characters))
                
                result = '、'.join(unique_characters)
                logger.info(f"LLM提取角色成功: {result}")
                return result
            else:
                logger.warning("LLM返回空响应，使用后备方案")
                return self._extract_characters_fallback(description)
                
        except Exception as e:
            logger.error(f"LLM角色提取失败: {e}，使用后备方案")
            return self._extract_characters_fallback(description)
    
    def _extract_characters_fallback(self, description: str) -> str:
        """
        智能角色提取的后备方案
        
        Args:
            description: 画面描述文本
            
        Returns:
            str: 角色列表字符串，用逗号分隔
        """
        characters = []
        
        # 使用多层次智能角色识别策略
        import re
        
        # 第一层：智能复合角色名称识别
        characters.extend(self._extract_compound_characters(description))
        
        # 第二层：语义角色关系识别
        characters.extend(self._extract_semantic_characters(description))
        
        # 第三层：传统关键词匹配（仅在前两层未找到时使用）
        if not characters:
            characters.extend(self._extract_keyword_characters(description))
        
        # 去重并保持顺序
        unique_characters = []
        seen = set()
        for char in characters:
            if char and char not in seen:
                unique_characters.append(char)
                seen.add(char)
        
        logger.debug(f"智能角色提取结果: {unique_characters}")
        return '、'.join(unique_characters) if unique_characters else ''
    
    def _extract_compound_characters(self, description: str) -> list:
        """
        提取复合角色名称（如：李静妈妈、张三师傅、小明的猫等）
        支持被括号或其他内容分隔的情况
        
        Args:
            description: 画面描述文本
            
        Returns:
            list: 提取到的复合角色名称列表
        """
        import re
        characters = []
        
        # 扩展的角色后缀词库
        role_suffixes = [
            # 家庭关系
            '妈妈', '爸爸', '母亲', '父亲', '爷爷', '奶奶', '外公', '外婆',
            '儿子', '女儿', '哥哥', '姐姐', '弟弟', '妹妹', '丈夫', '妻子',
            # 职业身份
            '老师', '医生', '护士', '警察', '司机', '老板', '经理', '秘书',
            '服务员', '店主', '厨师', '律师', '法官', '记者', '演员', '歌手',
            '教授', '学生', '军人', '士兵', '工人', '农民', '商人', '助理',
            # 师徒关系
            '师傅', '师父', '师兄', '师姐', '师弟', '师妹', '徒弟', '学徒',
            # 社会关系
            '朋友', '同事', '同学', '邻居', '室友', '伙伴', '搭档', '助手',
            # 特殊关系
            '保镖', '司机', '秘书', '管家', '保姆', '护工', '向导', '翻译',
            # 动物/宠物
            '的猫', '的狗', '的鸟', '的马', '的鱼', '的兔子', '的仓鼠',
            # 称谓
            '大叔', '大爷', '大妈', '阿姨', '叔叔', '婶婶', '舅舅', '姑姑'
        ]
        
        # 构建动态正则表达式
        suffix_pattern = '|'.join(re.escape(suffix) for suffix in role_suffixes)
        
        # 匹配模式：人名+角色后缀（支持被分隔的情况）
        patterns = [
            # 直接连接：李静妈妈
            rf'([\u4e00-\u9fa5]{{2,4}})({suffix_pattern})',
            # 带"的"：李静的猫
            rf'([\u4e00-\u9fa5]{{2,4}})的({suffix_pattern.replace("的", "")})',
            # 空格分隔：李静 妈妈
            rf'([\u4e00-\u9fa5]{{2,4}})\s+({suffix_pattern})',
            # 被括号内容分隔：李静（...）妈妈
            rf'([\u4e00-\u9fa5]{{2,4}})（[^）]*）({suffix_pattern})',
            # 被其他标点分隔：李静，妈妈 / 李静。妈妈
            rf'([\u4e00-\u9fa5]{{2,4}})[，。、；：！？]\s*({suffix_pattern})',
            # 被描述性内容分隔（更宽泛的匹配）：李静...妈妈
            rf'([\u4e00-\u9fa5]{{2,4}})[^\u4e00-\u9fa5]*?({suffix_pattern})(?=[，。！？；：、\s]|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                if len(match) == 2:  # 确保匹配到两个部分
                    name_part, role_part = match
                    
                    # 验证是否是有效的角色组合
                    if self._is_valid_character_combination(name_part, role_part, description):
                        # 重构完整角色名称
                        if '的' in pattern and not role_part.startswith('的'):
                            full_name = f"{name_part}的{role_part}"
                        else:
                            full_name = f"{name_part}{role_part}"
                        
                        if len(full_name) >= 3:  # 至少3个字符的复合名称
                            characters.append(full_name)
                            logger.debug(f"识别到复合角色: {full_name} (来源: {name_part} + {role_part})")
        
        return characters
    
    def _is_valid_character_combination(self, name_part: str, role_part: str, description: str) -> bool:
        """
        验证人名和角色部分的组合是否有效
        
        Args:
            name_part: 人名部分
            role_part: 角色部分
            description: 原始描述
            
        Returns:
            bool: 是否是有效的角色组合
        """
        # 排除明显不是人名的词汇
        invalid_names = [
            '一个', '这个', '那个', '某个', '每个', '所有', '全部',
            '年轻', '中年', '老年', '小小', '大大', '高高', '矮矮',
            '美丽', '漂亮', '英俊', '帅气', '可爱', '温柔', '善良'
        ]
        
        if name_part in invalid_names:
            return False
        
        # 检查上下文，确保这确实是一个角色关系
        # 例如："李静（描述）妈妈" 中，妈妈应该是在描述李静的妈妈
        context_indicators = [
            f"{name_part}.*{role_part}",  # 基本匹配
            f"{role_part}.*{name_part}",  # 反向匹配
        ]
        
        import re
        for indicator in context_indicators:
            if re.search(indicator, description):
                return True
        
        return True  # 默认认为有效
    
    def _extract_semantic_characters(self, description: str) -> list:
        """
        基于语义的角色识别（识别上下文中的角色关系）
        
        Args:
            description: 画面描述文本
            
        Returns:
            list: 提取到的语义角色列表
        """
        import re
        characters = []
        
        # 语义模式：动作+角色关系
        semantic_patterns = [
            # 所有格模式：XX的YY
            r'([\u4e00-\u9fa5]{2,4})的([\u4e00-\u9fa5]{2,4})',
            # 称呼模式：叫XX、名叫XX
            r'(?:叫|名叫|称为)([\u4e00-\u9fa5]{2,4})',
            # 介绍模式：这是XX、那是XX
            r'(?:这是|那是|就是)([\u4e00-\u9fa5]{2,4})',
            # 动作主语模式：XX做了什么
            r'([\u4e00-\u9fa5]{2,4})(?:正在|在|开始|继续|停止)([\u4e00-\u9fa5]+)',
        ]
        
        # 角色指示词
        role_indicators = [
            '人', '者', '员', '师', '生', '手', '工', '家', '长', '主', '客', '友'
        ]
        
        for pattern in semantic_patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                if isinstance(match, tuple):
                    # 处理元组匹配
                    for part in match:
                        if self._is_likely_character_name(part, role_indicators):
                            characters.append(part)
                else:
                    # 处理单个匹配
                    if self._is_likely_character_name(match, role_indicators):
                        characters.append(match)
        
        return characters
    
    def _is_likely_character_name(self, text: str, role_indicators: list) -> bool:
        """
        判断文本是否可能是角色名称
        
        Args:
            text: 待判断的文本
            role_indicators: 角色指示词列表
            
        Returns:
            bool: 是否可能是角色名称
        """
        if not text or len(text) < 2:
            return False
        
        # 排除明显不是角色的词汇
        non_character_words = [
            '时候', '地方', '东西', '事情', '问题', '方法', '办法', '样子',
            '颜色', '声音', '味道', '感觉', '心情', '想法', '意思', '内容'
        ]
        
        if text in non_character_words:
            return False
        
        # 检查是否包含角色指示词
        for indicator in role_indicators:
            if text.endswith(indicator):
                return True
        
        # 检查是否是常见人名模式
        import re
        if re.match(r'^[\u4e00-\u9fa5]{2,4}$', text):
            return True
        
        return False
    
    def _extract_keyword_characters(self, description: str) -> list:
        """
        传统关键词匹配角色提取
        
        Args:
            description: 画面描述文本
            
        Returns:
            list: 提取到的角色列表
        """
        characters = []
        
        # 扩展的角色关键词库
        character_keywords = [
            # 主要角色
            '主人公', '主角', '男主', '女主', '主人翁',
            # 基本人物类型
            '男子', '女子', '男人', '女人', '男孩', '女孩', '孩子', '小孩',
            '老人', '老者', '长者', '年轻人', '青年', '中年人',
            # 家庭关系
            '父亲', '母亲', '爸爸', '妈妈', '爷爷', '奶奶', '外公', '外婆',
            '儿子', '女儿', '哥哥', '姐姐', '弟弟', '妹妹', '丈夫', '妻子',
            # 职业身份
            '医生', '护士', '老师', '教授', '学生', '警察', '军人', '士兵',
            '司机', '工人', '农民', '商人', '老板', '经理', '秘书', '助理',
            '服务员', '店主', '店员', '收银员', '保安', '门卫', '清洁工',
            '厨师', '律师', '法官', '记者', '演员', '歌手', '画家', '作家',
            # 特征描述
            '光头大叔', '大叔', '大爷', '大妈', '阿姨', '叔叔', '婶婶',
            '帅哥', '美女', '胖子', '瘦子', '高个子', '矮个子',
            # 群体角色
            '路人', '行人', '乘客', '顾客', '客人', '观众', '群众', '民众',
            '同事', '朋友', '同学', '邻居', '陌生人'
        ]
        
        for keyword in character_keywords:
            if keyword in description:
                # 使用角色名称标准化
                normalized_name = CharacterDetectionConfig.normalize_character_name(keyword)
                characters.append(normalized_name)
        
        return characters
    
    def _build_enhanced_description_for_scene(self, shot_description, scene_info, all_characters, all_scenes):
        """为场景构建增强的画面描述"""
        try:
            # 使用PromptOptimizer构建增强描述
            character_details = self.prompt_optimizer._get_character_details(all_characters)
            
            # 处理scene_info可能是字符串或字典的情况
            if isinstance(scene_info, dict):
                scene_name = scene_info.get('name', '')
            elif isinstance(scene_info, str):
                scene_name = scene_info
            else:
                scene_name = ''
                
            scene_details = self.prompt_optimizer._get_scene_details(all_scenes, scene_name)
            
            enhanced_description = self.prompt_optimizer._build_enhanced_description(
                shot_description, character_details, scene_details
            )
            
            return enhanced_description
            
        except Exception as e:
            logger.error(f"构建场景增强描述失败: {e}")
            return shot_description
    
    def _get_prompts_from_json(self, shot_num):
        """从prompt.json文件读取对应镜头的提示词
        
        Args:
            shot_num (str): 镜头编号
            
        Returns:
            tuple: (中文提示词, 英文提示词) 或 (None, None)
        """
        try:
            # 获取项目输出目录
            if hasattr(self.parent_window, 'project_manager') and self.parent_window.project_manager.current_project:
                project_name = self.parent_window.project_manager.current_project.get('project_name')
                project_dir = self.parent_window.project_manager.get_current_project_path()
                if project_dir:
                    prompt_file_path = os.path.join(project_dir, 'texts', 'prompt.json')
                else:
                    return None, None
                
                if os.path.exists(prompt_file_path):
                    with open(prompt_file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 新的JSON格式：{"scenes": {"场景名": [{"shot_number": "镜头1", "enhanced_prompt": "..."}]}}
                    scenes = data.get('scenes', {})
                    if scenes:
                        # 遍历所有场景和镜头，查找对应的镜头编号
                        target_shot = f"### 镜头{shot_num}"
                        for scene_name, shots in scenes.items():
                            for shot in shots:
                                if shot.get('shot_number', '') == target_shot:
                                    enhanced_prompt = shot.get('enhanced_prompt', '')
                                    original_description = shot.get('original_description', '')
                                    saved_english_prompt = shot.get('english_prompt', '')
                                    
                                    if enhanced_prompt:
                                        # 中文提示词使用增强后的内容
                                        chinese_prompt = enhanced_prompt
                                        
                                        # 优先使用已保存的英文翻译
                                        if saved_english_prompt:
                                            english_prompt = saved_english_prompt
                                            logger.info(f"镜头{shot_num}使用已保存的英文翻译")
                                        else:
                                            # 检测是否已经是英文
                                            if self._is_english_text(enhanced_prompt):
                                                english_prompt = enhanced_prompt
                                                logger.info(f"镜头{shot_num}的enhanced_prompt已经是英文，无需翻译")
                                            else:
                                                # 生成英文提示词（优先使用LLM翻译）
                                                if (hasattr(self, 'enable_translation_cb') and self.enable_translation_cb.isChecked() and 
                                                    hasattr(self, 'use_llm_cb') and self.use_llm_cb.isChecked() and 
                                                    self.llm_api and self.llm_api.is_configured()):
                                                    # 使用LLM翻译
                                                    translation_prompt = f"Please translate the following Chinese prompt into pure English. Only output the English translation, do not include any Chinese characters or mixed language content. Maintain professionalism and accuracy:\n\n{enhanced_prompt}"
                                                    english_translation = self.llm_api.rewrite_text(translation_prompt)
                                                    if english_translation and len(english_translation.strip()) > 10:
                                                        english_prompt = english_translation.strip()
                                                        # 不再保存英文翻译到prompt.json文件
                                                        # self._save_english_translation_to_json(shot_num, english_prompt)
                                                    else:
                                                        # LLM翻译失败，尝试百度翻译
                                                        english_prompt = self._translate_with_fallback(enhanced_prompt)
                                                        # 不再保存英文翻译到prompt.json文件
                                                        # self._save_english_translation_to_json(shot_num, english_prompt)
                                                else:
                                                    # 使用简单翻译
                                                    english_prompt = self._simple_translate_to_english(enhanced_prompt)
                                            # 不再保存英文翻译到prompt.json文件（如果不是已存在的英文）
                                            # if not self._is_english_text(enhanced_prompt):
                                            #     self._save_english_translation_to_json(shot_num, english_prompt)
                                        
                                        return chinese_prompt, english_prompt
                                    elif original_description:
                                        # 如果没有增强内容，使用原始描述
                                        chinese_prompt = original_description
                                        
                                        # 优先使用已保存的英文翻译
                                        if saved_english_prompt:
                                            english_prompt = saved_english_prompt
                                            logger.info(f"镜头{shot_num}使用已保存的英文翻译")
                                        else:
                                            # 检测是否已经是英文
                                            if self._is_english_text(original_description):
                                                english_prompt = original_description
                                                logger.info(f"镜头{shot_num}的original_description已经是英文，无需翻译")
                                            else:
                                                # 生成英文提示词（优先使用LLM翻译）
                                                if (hasattr(self, 'enable_translation_cb') and self.enable_translation_cb.isChecked() and 
                                                    hasattr(self, 'use_llm_cb') and self.use_llm_cb.isChecked() and 
                                                    self.llm_api and self.llm_api.is_configured()):
                                                    # 使用LLM翻译
                                                    translation_prompt = f"Please translate the following Chinese prompt into pure English. Only output the English translation, do not include any Chinese characters or mixed language content. Maintain professionalism and accuracy:\n\n{original_description}"
                                                    english_translation = self.llm_api.rewrite_text(translation_prompt)
                                                    if english_translation and len(english_translation.strip()) > 10:
                                                        english_prompt = english_translation.strip()
                                                        # 不再保存英文翻译到prompt.json文件
                                                        # self._save_english_translation_to_json(shot_num, english_prompt)
                                                    else:
                                                        # LLM翻译失败，尝试百度翻译
                                                        english_prompt = self._translate_with_fallback(original_description)
                                                        # 不再保存英文翻译到prompt.json文件
                                                        # self._save_english_translation_to_json(shot_num, english_prompt)
                                                else:
                                                    # 使用简单翻译
                                                    english_prompt = self._simple_translate_to_english(original_description)
                                            # 不再保存英文翻译到prompt.json文件（如果不是已存在的英文）
                                            # if not self._is_english_text(original_description):
                                            #     self._save_english_translation_to_json(shot_num, english_prompt)
                                        
                                        return chinese_prompt, english_prompt
                    
                    # 兼容旧格式：enhanced_prompt字段
                    enhanced_prompt = data.get('enhanced_prompt', '')
                    if enhanced_prompt:
                        # enhanced_prompt是一个长字符串，包含所有镜头的提示词，用双换行符分隔
                        prompts = enhanced_prompt.split('\n\n')
                        
                        # 查找对应镜头的提示词
                        shot_index = int(shot_num) - 1
                        if 0 <= shot_index < len(prompts):
                            prompt_text = prompts[shot_index].strip()
                            if prompt_text:
                                # 中文提示词就是原始内容
                                chinese_prompt = prompt_text
                                
                                # 生成英文提示词（优先使用LLM翻译）
                                if (hasattr(self, 'enable_translation_cb') and self.enable_translation_cb.isChecked() and 
                                    hasattr(self, 'use_llm_cb') and self.use_llm_cb.isChecked() and 
                                    self.llm_api and self.llm_api.is_configured()):
                                    # 使用LLM翻译
                                    translation_prompt = f"Please translate the following Chinese prompt into pure English. Only output the English translation, do not include any Chinese characters or mixed language content. Maintain professionalism and accuracy:\n\n{prompt_text}"
                                    english_translation = self.llm_api.rewrite_text(translation_prompt)
                                    if english_translation and len(english_translation.strip()) > 10:
                                        english_prompt = english_translation.strip()
                                    else:
                                        # LLM翻译失败，使用简单翻译
                                        english_prompt = self._simple_translate_to_english(prompt_text)
                                else:
                                    # 使用简单翻译
                                    english_prompt = self._simple_translate_to_english(prompt_text)
                                
                                return chinese_prompt, english_prompt
                    
                    # 如果enhanced_prompt不能按双换行符分割，尝试按镜头描述分割
                    original_description = data.get('original_description', '')
                    if original_description:
                        # 按镜头编号分割原始描述
                        import re
                        shot_pattern = r'### 镜头(\d+)'
                        shot_matches = list(re.finditer(shot_pattern, original_description))
                        
                        target_shot_num = int(shot_num)
                        for i, match in enumerate(shot_matches):
                            current_shot_num = int(match.group(1))
                            if current_shot_num == target_shot_num:
                                # 找到目标镜头的开始位置
                                start_pos = match.start()
                                # 找到下一个镜头的开始位置（如果存在）
                                if i + 1 < len(shot_matches):
                                    end_pos = shot_matches[i + 1].start()
                                else:
                                    end_pos = len(original_description)
                                
                                # 提取该镜头的描述
                                shot_description = original_description[start_pos:end_pos].strip()
                                
                                # 提取画面描述部分
                                desc_match = re.search(r'- \*\*画面描述\*\*：(.+?)(?=\n- \*\*|$)', shot_description, re.DOTALL)
                                if desc_match:
                                    chinese_prompt = desc_match.group(1).strip()
                                    english_prompt = self._simple_translate_to_english(chinese_prompt)
                                    return chinese_prompt, english_prompt
                                break
                        
            return None, None
            
        except Exception as e:
            logger.error(f"从prompt.json读取镜头{shot_num}提示词失败: {e}")
            return None, None
    
    def _is_english_text(self, text):
        """检测文本是否主要为英文
        
        Args:
            text (str): 待检测的文本
            
        Returns:
            bool: 如果文本主要为英文返回True，否则返回False
        """
        try:
            import re
            # 移除标点符号和数字
            clean_text = re.sub(r'[^\w\s]', '', text)
            clean_text = re.sub(r'\d+', '', clean_text)
            
            if not clean_text.strip():
                return False
            
            # 统计英文字符和中文字符
            english_chars = len(re.findall(r'[a-zA-Z]', clean_text))
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', clean_text))
            
            # 如果包含中文字符，则不认为是纯英文文本
            if chinese_chars > 0:
                return False
            
            # 如果英文字符占比超过90%，认为是英文文本
            total_chars = english_chars + chinese_chars
            if total_chars == 0:
                return False
            
            english_ratio = english_chars / total_chars
            return english_ratio > 0.9
            
        except Exception as e:
            logger.warning(f"检测文本语言失败: {e}")
            return False
    
    def _translate_with_fallback(self, chinese_text):
        """带备用方案的翻译方法
        
        Args:
            chinese_text (str): 中文文本
            
        Returns:
            str: 英文文本
        """
        try:
            # 首先尝试百度翻译
            if is_baidu_configured():
                try:
                    logger.info("尝试使用百度翻译")
                    baidu_result = translate_text(chinese_text, 'zh', 'en')
                    if baidu_result and baidu_result.strip() and len(baidu_result.strip()) > 5:
                        logger.info("百度翻译成功")
                        return baidu_result.strip()
                    else:
                        logger.warning("百度翻译返回结果为空或过短")
                except Exception as e:
                    logger.warning(f"百度翻译失败: {e}")
            else:
                logger.info("百度翻译未配置，跳过")
            
            # 百度翻译失败或未配置，使用简单翻译
            logger.info("使用简单关键词翻译")
            return self._simple_translate_to_english(chinese_text)
            
        except Exception as e:
            logger.error(f"翻译过程出错: {e}")
            return self._simple_translate_to_english(chinese_text)
    
    def _simple_translate_to_english(self, chinese_text):
        """简单的中文到英文翻译（关键词替换）
        
        Args:
            chinese_text (str): 中文文本
            
        Returns:
            str: 英文文本
        """
        try:
            # 简单的关键词映射
            translation_map = {
                '动漫风格': 'anime style',
                '特写镜头': 'close-up shot',
                '中景镜头': 'medium shot', 
                '全景镜头': 'wide shot',
                '平视': 'eye level',
                '俯视': 'high angle',
                '仰视': 'low angle',
                '静止': 'static',
                '推拉': 'push pull',
                '摇移': 'pan tilt',
                '跟随': 'follow',
                '浅景深': 'shallow depth of field',
                '深景深': 'deep depth of field',
                '三分法': 'rule of thirds',
                '对称': 'symmetrical',
                '对角线': 'diagonal',
                '自然光': 'natural lighting',
                '人工光': 'artificial lighting',
                '逆光': 'backlight',
                '低光照': 'low light',
                '冷色调': 'cool tone',
                '暖色调': 'warm tone',
                '年轻男子': 'young man',
                '面容憔悴': 'haggard face',
                '眼神焦虑': 'anxious eyes',
                '绝望': 'despair',
                '黑色休闲装': 'black casual wear',
                '头发凌乱': 'messy hair',
                '钥匙扣': 'keychain',
                '昏暗的城市街道': 'dim city street',
                '赛璐璐渲染': 'cel shading',
                '鲜艳色彩': 'vibrant colors',
                '干净线条': 'clean lines',
                '日本动画': 'Japanese animation'
            }
            
            english_text = chinese_text
            for chinese, english in translation_map.items():
                english_text = english_text.replace(chinese, english)
            
            return english_text
            
        except Exception as e:
            logger.error(f"简单翻译失败: {e}")
            return chinese_text  # 翻译失败时返回原文
    
    def _get_enhanced_description_from_json(self, shot_num):
        """从prompt.json文件中获取指定镜头的增强描述
        
        Args:
            shot_num (str): 镜头编号
            
        Returns:
            str: 增强描述内容，如果没有则返回None
        """
        try:
            if not self.project_manager:
                return None
                
            project_dir = self.project_manager.get_current_project_path()
            if project_dir:
                prompt_file_path = os.path.join(project_dir, 'texts', 'prompt.json')
            else:
                return None
                
            if os.path.exists(prompt_file_path):
                with open(prompt_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 新的JSON格式：{"scenes": {"场景名": [{"shot_number": "镜头1", "enhanced_description": "..."}]}}
                scenes = data.get('scenes', {})
                if scenes:
                    # 遍历所有场景和镜头，查找对应的镜头编号
                    target_shot = f"### 镜头{shot_num}"
                    for scene_name, shots in scenes.items():
                        for shot in shots:
                            if shot.get('shot_number', '') == target_shot:
                                enhanced_prompt = shot.get('enhanced_prompt', '')
                                if enhanced_prompt:
                                    return enhanced_prompt
                                    
            return None
            
        except Exception as e:
            logger.error(f"从prompt.json读取镜头{shot_num}增强描述失败: {e}")
            return None
    
    def _insert_bilingual_prompts_into_script(self, storyboard_script, shot_bilingual_prompts):
        """在分镜脚本中插入文生图中英对照内容，确保每个镜头只插入一次"""
        try:
            lines = storyboard_script.split('\n')
            enhanced_lines = []
            current_shot = None
            shot_prompt_inserted = False  # 标记当前镜头是否已插入文生图中文
            
            for line in lines:
                enhanced_lines.append(line)
                
                # 检测镜头标题
                if line.strip().startswith('### 镜头') or line.strip().startswith('##镜头') or ('镜头' in line and line.strip().endswith('###')):
                    import re
                    shot_match = re.search(r'镜头(\d+)', line)
                    if shot_match:
                        current_shot = shot_match.group(1)
                        shot_prompt_inserted = False  # 重置标记
                
                # 检测画面描述行（不再插入增强描述）
                elif line.strip().startswith('- **画面描述**：') or line.strip().startswith('**画面描述**：'):
                    pass  # 不再插入增强描述
                
                # 检测音效提示行，在其后插入文生图中英对照（如果还没有插入）
                elif line.strip().startswith('- **音效提示**：') or line.strip().startswith('**音效提示**：'):
                    if current_shot and not shot_prompt_inserted:
                        # 首先尝试从prompt.json获取提示词
                        prompt_cn, prompt_en = self._get_prompts_from_json(current_shot)
                        
                        if prompt_cn:
                            # 使用从prompt.json读取的提示词
                            enhanced_lines.append(f"- **文生图中文**：{prompt_cn}")
                        elif current_shot in shot_bilingual_prompts:
                            # 使用生成的双语提示词
                            prompt_cn, prompt_en = shot_bilingual_prompts[current_shot]
                            enhanced_lines.append(f"- **文生图中文**：{prompt_cn}")
                        else:
                            # 添加空的占位符
                            enhanced_lines.append("- **文生图中文**：")
                        
                        shot_prompt_inserted = True  # 标记已插入
                
                # 检测转场方式行，在其后插入文生图中英对照（如果还没有插入）
                elif line.strip().startswith('- **转场方式**：') or line.strip().startswith('**转场方式**：'):
                    if current_shot and not shot_prompt_inserted:
                        # 首先尝试从prompt.json获取提示词
                        prompt_cn, prompt_en = self._get_prompts_from_json(current_shot)
                        
                        if prompt_cn:
                            # 使用从prompt.json读取的提示词
                            enhanced_lines.append(f"- **文生图中文**：{prompt_cn}")
                        elif current_shot in shot_bilingual_prompts:
                            # 使用生成的双语提示词
                            prompt_cn, prompt_en = shot_bilingual_prompts[current_shot]
                            enhanced_lines.append(f"- **文生图中文**：{prompt_cn}")
                        else:
                            # 添加空的占位符
                            enhanced_lines.append("- **文生图中文**：")
                        
                        shot_prompt_inserted = True  # 标记已插入
                
                # 检测画面描述行（冒号格式，不再插入增强描述）
                elif line.strip().startswith('- **画面描述**:') or line.strip().startswith('**画面描述**:'):
                    pass  # 不再插入增强描述
                
                # 检测音效提示行（英文冒号格式）
                elif line.strip().startswith('- **音效提示**:') or line.strip().startswith('**音效提示**:'):
                    if current_shot and not shot_prompt_inserted:
                        # 首先尝试从prompt.json获取提示词
                        prompt_cn, prompt_en = self._get_prompts_from_json(current_shot)
                        
                        if prompt_cn:
                            # 使用从prompt.json读取的提示词
                            enhanced_lines.append(f"- **文生图中文**：{prompt_cn}")
                        elif current_shot in shot_bilingual_prompts:
                            # 使用生成的双语提示词
                            prompt_cn, prompt_en = shot_bilingual_prompts[current_shot]
                            enhanced_lines.append(f"- **文生图中文**：{prompt_cn}")
                        else:
                            # 添加空的占位符
                            enhanced_lines.append("- **文生图中文**：")
                        
                        shot_prompt_inserted = True  # 标记已插入
                
                elif line.strip().startswith('- **转场方式**:') or line.strip().startswith('**转场方式**:'):
                    if current_shot and not shot_prompt_inserted:
                        # 首先尝试从prompt.json获取提示词
                        prompt_cn, prompt_en = self._get_prompts_from_json(current_shot)
                        
                        if prompt_cn:
                            # 使用从prompt.json读取的提示词
                            enhanced_lines.append(f"- **文生图中文**：{prompt_cn}")
                        elif current_shot in shot_bilingual_prompts:
                            # 使用生成的双语提示词
                            prompt_cn, prompt_en = shot_bilingual_prompts[current_shot]
                            enhanced_lines.append(f"- **文生图中文**：{prompt_cn}")
                        else:
                            # 添加空的占位符
                            enhanced_lines.append("- **文生图中文**：")
                        
                        shot_prompt_inserted = True  # 标记已插入
            
            return '\n'.join(enhanced_lines)
            
        except Exception as e:
            logger.error(f"插入双语提示词失败: {e}")
            return storyboard_script  # 返回原始脚本
    
    def _save_english_translation_to_json(self, shot_num, english_translation):
        """保存英文翻译到prompt.json文件"""
        try:
            project_dir = self.parent_window.project_manager.get_current_project_path()
            if not project_dir:
                logger.warning("无法获取项目路径，无法保存英文翻译")
                return
            
            prompt_file_path = os.path.join(project_dir, 'texts', 'prompt.json')
            
            # 确保目录存在
            os.makedirs(os.path.dirname(prompt_file_path), exist_ok=True)
            
            # 读取现有数据
            data = {}
            if os.path.exists(prompt_file_path):
                try:
                    with open(prompt_file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception as e:
                    logger.warning(f"读取现有prompt.json失败，将创建新文件: {e}")
                    data = {}
            
            # 确保scenes结构存在
            if 'scenes' not in data:
                data['scenes'] = {}
            
            # 查找对应的镜头并添加英文翻译
            target_shot = f"### 镜头{shot_num}"
            shot_found = False
            
            for scene_name, shots in data['scenes'].items():
                for shot in shots:
                    if shot.get('shot_number', '') == target_shot:
                        shot['english_prompt'] = english_translation
                        shot_found = True
                        logger.info(f"为镜头{shot_num}保存英文翻译到prompt.json")
                        break
                if shot_found:
                    break
            
            # 如果没有找到对应镜头，创建一个新的场景和镜头条目
            if not shot_found:
                scene_name = "默认场景"
                if scene_name not in data['scenes']:
                    data['scenes'][scene_name] = []
                
                new_shot = {
                    "shot_number": target_shot,
                    "english_prompt": english_translation
                }
                data['scenes'][scene_name].append(new_shot)
                logger.info(f"为镜头{shot_num}创建新条目并保存英文翻译到prompt.json")
            
            # 保存文件
            with open(prompt_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"英文翻译已保存到 {prompt_file_path}")
            
        except Exception as e:
            logger.error(f"保存英文翻译到prompt.json失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # 已移除 request_preview 和 request_generation 方法，因为对应的按钮已被删除
    
    def export_config(self):
        """导出配置"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出一致性配置", "", "JSON文件 (*.json)"
            )
            
            if file_path:
                config_data = {
                    'consistency_config': {
                        'enable_character_consistency': self.current_config.enable_character_consistency,
                        'enable_scene_consistency': self.current_config.enable_scene_consistency,
                        'consistency_strength': self.current_config.consistency_strength,
                        'auto_extract_new_elements': self.current_config.auto_extract_new_elements,
                        'use_llm_enhancement': self.current_config.use_llm_enhancement,
                        'character_weight': self.current_config.character_weight,
                        'scene_weight': self.current_config.scene_weight,
                        'style_weight': self.current_config.style_weight
                    }
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, "成功", "配置导出成功！")
                logger.info(f"配置导出到: {file_path}")
                
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            QMessageBox.warning(self, "错误", f"导出配置失败: {e}")
    
    def import_config(self):
        """导入配置"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "导入一致性配置", "", "JSON文件 (*.json)"
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                if 'consistency_config' in config_data:
                    config = config_data['consistency_config']
                    
                    # 更新UI控件
                    self.enable_char_cb.setChecked(config.get('enable_character_consistency', True))
                    self.enable_scene_cb.setChecked(config.get('enable_scene_consistency', True))
                    self.auto_extract_cb.setChecked(config.get('auto_extract_new_elements', True))
                    # use_llm_enhancement已移到高级优化功能中
                    
                    self.consistency_strength_slider.setValue(int(config.get('consistency_strength', 0.7) * 100))
                    self.character_weight_slider.setValue(int(config.get('character_weight', 0.4) * 100))
                    self.scene_weight_slider.setValue(int(config.get('scene_weight', 0.3) * 100))
                    self.style_weight_slider.setValue(int(config.get('style_weight', 0.3) * 100))
                    
                    # 更新配置对象
                    self.update_config()
                    
                    QMessageBox.information(self, "成功", "配置导入成功！")
                    logger.info(f"配置从 {file_path} 导入成功")
                else:
                    QMessageBox.warning(self, "错误", "配置文件格式不正确")
                
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            QMessageBox.warning(self, "错误", f"导入配置失败: {e}")
    
    def _extract_and_save_storyboard_data(self, storyboard: StoryboardResult):
        """从分镜数据中提取并保存角色和场景信息"""
        try:
            if not self.cs_manager:
                logger.warning("角色场景管理器未初始化，尝试重新初始化")
                self._try_reinit_cs_manager()
                
                if not self.cs_manager:
                    logger.warning("无法初始化角色场景管理器，跳过数据保存")
                    return
            
            # 提取并保存角色数据
            characters_saved = 0
            for character_name in storyboard.characters:
                if character_name and character_name.strip():
                    character_name = character_name.strip()
                    
                    # 检查角色是否已存在
                    existing_characters = self.cs_manager.get_all_characters()
                    char_exists = any(data.get('name') == char_name for data in existing_characters.values())

                    if not char_exists:
                        # 创建角色数据
                        character_data = {
                            'name': char_name,
                            'description': f'从分镜中提取的角色: {char_name}',
                            'appearance': {
                                'gender': '', 'age_range': '', 'hair': '', 'eyes': '', 'skin': '', 'build': ''
                            },
                            'clothing': {
                                'style': '', 'colors': [], 'accessories': []
                            },
                            'personality': {
                                'traits': [], 'expressions': [], 'mannerisms': []
                            },
                            'consistency_prompt': f'{char_name}, 保持角色一致性',
                            'source': 'storyboard_extraction'
                        }
                        
                        # 生成唯一ID
                        char_id = f"分镜角色_{char_name}" # 简化ID，如果需要更强的唯一性，可以考虑其他策略

                        if self.current_config.use_llm_enhancement and self.current_config.auto_extract_new_elements:
                            if self.cs_manager and hasattr(self.cs_manager, '_extract_characters_with_llm'):
                                try:
                                    llm_input_text = f"角色名称: {char_name}. 现有描述: {character_data.get('description', '')}"
                                    enhanced_characters_list = self.cs_manager._extract_characters_with_llm(llm_input_text)
                                    
                                    if enhanced_characters_list and isinstance(enhanced_characters_list, list) and len(enhanced_characters_list) > 0:
                                        enhanced_data_from_llm = enhanced_characters_list[0]
                                        
                                        original_name = character_data['name']
                                        original_source = character_data['source']
                                        
                                        character_data.update(enhanced_data_from_llm)
                                        
                                        character_data['name'] = original_name
                                        character_data['source'] = original_source
                                        if not character_data.get('consistency_prompt') or not character_data['consistency_prompt'].strip():
                                            character_data['consistency_prompt'] = f'{char_name}, 保持角色一致性'
                                            
                                        logger.info(f"LLM增强角色数据: {char_name}")
                                    else:
                                        logger.info(f"LLM未对角色 {char_name} 提供增强信息或返回格式不符.")
                                except Exception as e:
                                    logger.error(f"LLM增强角色 {char_name} 失败: {e}")
                            else:
                                logger.warning(f"LLM增强角色 {char_name} 跳过: cs_manager 或 _extract_characters_with_llm 方法不可用.")
                        
                        # 保存角色
                        self.cs_manager.save_character(char_id, character_data)
                        characters_saved += 1
                        logger.info(f"保存新角色: {char_name}")
            
            # 提取并保存场景数据
            scenes_saved = 0
            for scene_name in storyboard.scenes:
                if scene_name and scene_name.strip():
                    scene_name = scene_name.strip()
                    
                    # 检查场景是否已存在
                    existing_scenes = self.cs_manager.get_all_scenes()
                    scene_exists = any(data.get('name') == scene_name for data in existing_scenes.values())

                    if not scene_exists:
                        # 创建场景数据
                        scene_data = {
                            'name': scene_name,
                            'description': f'从分镜中提取的场景: {scene_name}',
                            'environment': {
                                'location_type': '',
                                'setting': '',
                                'props': [],
                                'atmosphere': ''
                            },
                            'lighting': {
                                'time_of_day': '',
                                'weather': '',
                                'light_source': '',
                                'mood': ''
                            },
                            'consistency_prompt': f'{scene_name}, 保持场景一致性',
                            'source': 'storyboard_extraction'
                        }
                        
                        # 🔧 修复：使用"镜头场景_"而不是"分镜场景_"
                        scene_id = f"镜头场景_{scene_name}" # 简化ID

                        # 🔧 删除场景LLM增强功能，只针对镜头进行增强
                        # 场景增强功能已被删除，因为增强描述只应该针对镜头，不需要对场景进行增强
                        
                        # 保存场景
                        self.cs_manager.save_scene(scene_id, scene_data)
                        scenes_saved += 1
                        logger.info(f"保存新场景: {scene_name}")
            
            if characters_saved > 0 or scenes_saved > 0:
                logger.info(f"从分镜数据中提取并保存了 {characters_saved} 个角色和 {scenes_saved} 个场景")
                # 重新加载数据到表格
                self.load_character_scene_data()
            else:
                logger.info("分镜数据中的角色和场景都已存在，无需重复保存")
                
        except Exception as e:
            logger.error(f"提取和保存分镜数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _try_reinit_cs_manager(self):
        """尝试重新初始化角色场景管理器"""
        try:
            # 检查是否有项目管理器和当前项目
            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有当前项目，无法初始化角色场景管理器")
                return
            
            # 获取项目目录
            project_dir = self.project_manager.current_project.get("project_dir")
            if not project_dir:
                logger.warning("项目目录不存在，无法初始化角色场景管理器")
                return
            
            # 创建角色场景管理器
            from src.utils.character_scene_manager import CharacterSceneManager
            service_manager = getattr(self.project_manager, 'service_manager', None)
            if hasattr(self.project_manager, 'app_controller'):
                service_manager = self.project_manager.app_controller.service_manager
            
            self.cs_manager = CharacterSceneManager(project_dir, service_manager)
            logger.info(f"角色场景管理器重新初始化成功，项目目录: {project_dir}")
            
            # 初始化提示词优化器
            if not self.prompt_optimizer and self.llm_api:
                from src.processors.prompt_optimizer import PromptOptimizer
                self.prompt_optimizer = PromptOptimizer(self.llm_api, self.cs_manager)
                logger.info("提示词优化器初始化完成")
            
        except Exception as e:
            logger.error(f"重新初始化角色场景管理器失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def get_current_config(self) -> ConsistencyConfig:
        """获取当前配置"""
        return self.current_config

    def get_project_data(self) -> Dict[str, Any]:
        """获取项目数据（用于项目保存）"""
        try:
            # 收集一致性控制面板的数据
            consistency_data = {}

            # 保存当前配置
            if self.current_config:
                consistency_data['consistency_config'] = {
                    'enable_character_consistency': self.current_config.enable_character_consistency,
                    'enable_scene_consistency': self.current_config.enable_scene_consistency,
                    'consistency_strength': self.current_config.consistency_strength,
                    'auto_extract_new_elements': self.current_config.auto_extract_new_elements,
                    'use_llm_enhancement': self.current_config.use_llm_enhancement,
                    'character_weight': self.current_config.character_weight,
                    'scene_weight': self.current_config.scene_weight,
                    'style_weight': self.current_config.style_weight
                }

            # 保存预览数据
            if hasattr(self, 'preview_text') and self.preview_text:
                preview_content = self.preview_text.toPlainText().strip()
                if preview_content:
                    consistency_data['consistency_preview'] = preview_content

            # 保存角色和场景数据
            if self.cs_manager:
                try:
                    characters = self.cs_manager.get_all_characters()
                    scenes = self.cs_manager.get_all_scenes()
                    if characters:
                        consistency_data['characters_data'] = characters
                    if scenes:
                        consistency_data['scenes_data'] = scenes
                except Exception as e:
                    logger.warning(f"获取角色场景数据失败: {e}")

            return consistency_data

        except Exception as e:
            logger.error(f"获取一致性控制数据失败: {e}")
            return {}
    
    def refresh_characters(self):
        """刷新角色数据"""
        try:
            logger.info("开始刷新角色数据...")
            
            # 检查cs_manager是否可用
            if not self.cs_manager:
                logger.warning("角色场景管理器未初始化，尝试重新初始化")
                self._try_reinit_cs_manager()
                
                if not self.cs_manager:
                    QMessageBox.warning(self, "警告", "角色场景管理器未初始化，无法刷新角色数据")
                    return
            
            # 重新加载角色数据
            characters = self.cs_manager.get_all_characters()
            self.character_table.setRowCount(len(characters))
            
            for row, (char_id, char_data) in enumerate(characters.items()):
                # 处理不同的数据格式
                name = char_data.get('name', '')
                description = char_data.get('description', '')
                
                # 处理外貌信息（可能是字符串或字典）
                appearance = char_data.get('appearance', '')
                if isinstance(appearance, dict):
                    # 如果是字典，提取主要信息
                    appearance_parts = []
                    for key, value in appearance.items():
                        if value and isinstance(value, str):
                            appearance_parts.append(f"{key}: {value}")
                    appearance = "; ".join(appearance_parts)
                elif not isinstance(appearance, str):
                    appearance = str(appearance)
                
                consistency_prompt = char_data.get('consistency_prompt', '')
                
                self.character_table.setItem(row, 0, QTableWidgetItem(name))
                self.character_table.setItem(row, 1, QTableWidgetItem(description))
                self.character_table.setItem(row, 2, QTableWidgetItem(appearance))
                self.character_table.setItem(row, 3, QTableWidgetItem(consistency_prompt))
                
                # 存储ID
                self.character_table.item(row, 0).setData(Qt.UserRole, char_id)
            
            # 更新按钮状态
            self.update_button_states()
            
            logger.info(f"角色数据刷新完成，共加载 {len(characters)} 个角色")
            QMessageBox.information(self, "提示", f"角色数据已刷新\n共加载 {len(characters)} 个角色")
            
        except Exception as e:
            logger.error(f"刷新角色数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"刷新角色数据失败: {str(e)}")
    
    def refresh_scenes(self):
        """刷新场景数据"""
        try:
            import re
            logger.info("开始刷新场景数据...")
            
            # 检查cs_manager是否可用
            if not self.cs_manager:
                logger.warning("角色场景管理器未初始化，尝试重新初始化")
                self._try_reinit_cs_manager()
                
                if not self.cs_manager:
                    QMessageBox.warning(self, "警告", "角色场景管理器未初始化，无法刷新场景数据")
                    return
            
            # 重新加载场景数据
            all_scenes = self.cs_manager.get_all_scenes()
            
            # 直接使用所有场景数据（源头已过滤）
            filtered_scenes = all_scenes
            
            self.scene_table.setRowCount(len(filtered_scenes))
            
            # 对过滤后的场景进行自然排序
            def natural_sort_key(item):
                scene_id, scene_data = item
                scene_name = scene_data.get('name', '')
                numbers = re.findall(r'\d+', scene_name)
                if numbers:
                    return (0, int(numbers[0]), scene_name)
                else:
                    return (1, 0, scene_name)
            
            sorted_scenes = sorted(filtered_scenes.items(), key=natural_sort_key)
            
            for row, (scene_id, scene_data) in enumerate(sorted_scenes):
                name = scene_data.get('name', '')
                description = scene_data.get('description', '')
                
                # 处理环境信息（可能是字符串或字典）
                environment = scene_data.get('environment', '')
                if isinstance(environment, dict):
                    env_parts = []
                    for key, value in environment.items():
                        if value and isinstance(value, (str, list)):
                            if isinstance(value, list):
                                value = ", ".join(str(v) for v in value)
                            env_parts.append(f"{key}: {value}")
                    environment = "; ".join(env_parts)
                elif not isinstance(environment, str):
                    environment = str(environment)
                
                # 处理光线信息（可能是字符串或字典）
                lighting = scene_data.get('lighting', '')
                if isinstance(lighting, dict):
                    lighting_parts = []
                    for key, value in lighting.items():
                        if value and isinstance(value, str):
                            lighting_parts.append(f"{key}: {value}")
                    lighting = "; ".join(lighting_parts)
                elif not isinstance(lighting, str):
                    lighting = str(lighting)
                
                consistency_prompt = scene_data.get('consistency_prompt', '')
                
                self.scene_table.setItem(row, 0, QTableWidgetItem(name))
                self.scene_table.setItem(row, 1, QTableWidgetItem(description))
                self.scene_table.setItem(row, 2, QTableWidgetItem(environment))
                self.scene_table.setItem(row, 3, QTableWidgetItem(lighting))
                self.scene_table.setItem(row, 4, QTableWidgetItem(consistency_prompt))
                
                # 存储ID
                self.scene_table.item(row, 0).setData(Qt.UserRole, scene_id)
            
            # 更新按钮状态
            self.update_button_states()
            
            logger.info(f"场景数据刷新完成，共加载 {len(filtered_scenes)} 个用户创建的场景（已过滤分镜生成的场景）")
            QMessageBox.information(self, "提示", f"场景数据已刷新\n共加载 {len(filtered_scenes)} 个用户创建的场景")
            
        except Exception as e:
            logger.error(f"刷新场景数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"刷新场景数据失败: {str(e)}")