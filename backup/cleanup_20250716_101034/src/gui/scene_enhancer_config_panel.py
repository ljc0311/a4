#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场景描述增强器配置面板

第三阶段UI集成组件，提供：
1. 智能融合策略配置
2. 质量控制参数调整
3. 实时预览和测试
4. 配置导入导出
5. 性能监控
"""

import os
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QGroupBox, QLabel, QLineEdit, QTextEdit, QPushButton, QSlider,
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QProgressBar,
    QScrollArea, QFrame, QSplitter, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QDialog, QDialogButtonBox, QApplication,
    QFormLayout, QSpacerItem, QSizePolicy, QPlainTextEdit,
    QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt5.QtGui import QFont, QPixmap, QIcon, QPalette, QColor, QTextCharFormat

from src.utils.logger import logger
from src.utils.enhancer_config_manager import EnhancerConfigManager
from src.utils.config_manager import ConfigManager
from src.processors.scene_description_enhancer import SceneDescriptionEnhancer
from src.utils.character_scene_manager import CharacterSceneManager


class EnhancerTestWorker(QObject):
    """增强器测试工作线程"""
    test_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    def __init__(self, enhancer, test_description, characters=None):
        super().__init__()
        self.enhancer = enhancer
        self.test_description = test_description
        self.characters = characters or []
    
    def run(self):
        try:
            self.progress_updated.emit("正在测试增强效果...")
            
            # 获取详细增强结果
            details = self.enhancer.enhance_description_with_details(
                self.test_description, 
                self.characters
            )
            
            self.test_completed.emit(details)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class SceneEnhancerConfigPanel(QDialog):
    """场景描述增强器配置面板"""
    
    # 信号定义
    config_changed = pyqtSignal(dict)  # 配置变更信号
    test_requested = pyqtSignal(str, list)  # 测试请求信号
    
    def __init__(self, project_root=None, parent=None):
        super().__init__(parent)
        
        # 初始化组件
        if not project_root:
            raise ValueError("必须提供有效的项目根目录")
        self.project_root = project_root
        self.config_manager = ConfigManager()
        self.enhancer_config_manager = EnhancerConfigManager()
        self.enhancer = None
        self.test_worker = None
        self.test_thread = None
        
        # 测试结果存储
        self.test_results = []
        
        # 中英文映射字典
        self.strategy_mapping = {
            '自然': 'natural',
            '结构化': 'structured', 
            '简约': 'minimal',
            '智能': 'intelligent'
        }
        self.strategy_reverse_mapping = {v: k for k, v in self.strategy_mapping.items()}
        
        self.level_mapping = {
            '低': 'low',
            '中': 'medium',
            '高': 'high'
        }
        self.level_reverse_mapping = {v: k for k, v in self.level_mapping.items()}
        
        self.performance_mapping = {
            '快速': 'fast',
            '平衡': 'balanced',
            '质量': 'quality'
        }
        self.performance_reverse_mapping = {v: k for k, v in self.performance_mapping.items()}
        
        # 配置数据
        self.current_config = {
            'fusion_strategy': 'intelligent',
            'quality_threshold': 0.6,
            'enhancement_level': 'medium',
            'enable_technical_details': True,
            'enable_consistency_injection': True,
            'cache_enabled': True,
            'performance_mode': 'balanced'
        }
        
        self.init_ui()
        self.load_config()
        self.init_enhancer()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("场景描述增强器配置")
        title_label.setObjectName("config-title")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 基础配置标签页
        self.basic_tab = self.create_basic_config_tab()
        self.tab_widget.addTab(self.basic_tab, "基础配置")
        
        # 高级配置标签页
        self.advanced_tab = self.create_advanced_config_tab()
        self.tab_widget.addTab(self.advanced_tab, "高级配置")
        
        # 测试预览标签页
        self.test_tab = self.create_test_preview_tab()
        self.tab_widget.addTab(self.test_tab, "测试预览")
        
        # 性能监控标签页
        self.performance_tab = self.create_performance_tab()
        self.tab_widget.addTab(self.performance_tab, "性能监控")
        
        layout.addWidget(self.tab_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.setObjectName("primary-button")
        self.save_config_btn.clicked.connect(self.save_config)
        
        self.load_config_btn = QPushButton("重新加载")
        self.load_config_btn.setObjectName("secondary-button")
        self.load_config_btn.clicked.connect(self.load_config)
        
        self.export_config_btn = QPushButton("导出配置")
        self.export_config_btn.setObjectName("secondary-button")
        self.export_config_btn.clicked.connect(self.export_config)
        
        self.import_config_btn = QPushButton("导入配置")
        self.import_config_btn.setObjectName("secondary-button")
        self.import_config_btn.clicked.connect(self.import_config)
        
        button_layout.addWidget(self.save_config_btn)
        button_layout.addWidget(self.load_config_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.export_config_btn)
        button_layout.addWidget(self.import_config_btn)
        
        layout.addLayout(button_layout)
        
    def create_basic_config_tab(self):
        """创建基础配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 融合策略配置
        strategy_group = QGroupBox("融合策略配置")
        strategy_layout = QFormLayout(strategy_group)
        
        # 融合策略选择
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(['自然', '结构化', '简约', '智能'])
        self.strategy_combo.setCurrentText('智能')
        self.strategy_combo.currentTextChanged.connect(self.on_config_changed)
        strategy_layout.addRow("融合策略:", self.strategy_combo)
        
        # 质量阈值
        self.quality_threshold_slider = QSlider(Qt.Horizontal)
        self.quality_threshold_slider.setRange(0, 100)
        self.quality_threshold_slider.setValue(60)
        self.quality_threshold_slider.valueChanged.connect(self.on_quality_threshold_changed)
        
        self.quality_threshold_label = QLabel("0.60")
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(self.quality_threshold_slider)
        quality_layout.addWidget(self.quality_threshold_label)
        strategy_layout.addRow("质量阈值:", quality_layout)
        
        # 增强级别
        self.enhancement_level_combo = QComboBox()
        self.enhancement_level_combo.addItems(['低', '中', '高'])
        self.enhancement_level_combo.setCurrentText('中')
        self.enhancement_level_combo.currentTextChanged.connect(self.on_config_changed)
        strategy_layout.addRow("增强级别:", self.enhancement_level_combo)
        
        layout.addWidget(strategy_group)
        
        # 功能开关配置
        features_group = QGroupBox("功能开关")
        features_layout = QVBoxLayout(features_group)
        
        self.technical_details_cb = QCheckBox("启用技术细节分析")
        self.technical_details_cb.setChecked(True)
        self.technical_details_cb.toggled.connect(self.on_config_changed)
        features_layout.addWidget(self.technical_details_cb)
        
        self.consistency_injection_cb = QCheckBox("启用一致性注入")
        self.consistency_injection_cb.setChecked(True)
        self.consistency_injection_cb.toggled.connect(self.on_config_changed)
        features_layout.addWidget(self.consistency_injection_cb)
        
        self.cache_enabled_cb = QCheckBox("启用缓存机制")
        self.cache_enabled_cb.setChecked(True)
        self.cache_enabled_cb.toggled.connect(self.on_config_changed)
        features_layout.addWidget(self.cache_enabled_cb)
        
        layout.addWidget(features_group)
        
        layout.addStretch()
        return tab
        
    def create_advanced_config_tab(self):
        """创建高级配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 性能配置
        performance_group = QGroupBox("性能配置")
        performance_layout = QFormLayout(performance_group)
        
        # 性能模式
        self.performance_mode_combo = QComboBox()
        self.performance_mode_combo.addItems(['快速', '平衡', '质量'])
        self.performance_mode_combo.setCurrentText('平衡')
        self.performance_mode_combo.currentTextChanged.connect(self.on_config_changed)
        performance_layout.addRow("性能模式:", self.performance_mode_combo)
        
        # 缓存大小限制
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(10, 1000)
        self.cache_size_spin.setValue(100)
        self.cache_size_spin.setSuffix(" MB")
        self.cache_size_spin.valueChanged.connect(self.on_config_changed)
        performance_layout.addRow("缓存大小限制:", self.cache_size_spin)
        
        # 并发处理数
        self.concurrent_processes_spin = QSpinBox()
        self.concurrent_processes_spin.setRange(1, 8)
        self.concurrent_processes_spin.setValue(2)
        self.concurrent_processes_spin.valueChanged.connect(self.on_config_changed)
        performance_layout.addRow("并发处理数:", self.concurrent_processes_spin)
        
        layout.addWidget(performance_group)
        
        # 自定义规则配置
        rules_group = QGroupBox("自定义规则")
        rules_layout = QVBoxLayout(rules_group)
        
        rules_label = QLabel("自定义增强规则 (JSON格式):")
        rules_layout.addWidget(rules_label)
        
        self.custom_rules_edit = QTextEdit()
        self.custom_rules_edit.setMaximumHeight(150)
        self.custom_rules_edit.setPlaceholderText('{\n  "custom_patterns": [],\n  "enhancement_rules": {},\n  "quality_weights": {}\n}')
        rules_layout.addWidget(self.custom_rules_edit)
        
        validate_rules_btn = QPushButton("验证规则")
        validate_rules_btn.clicked.connect(self.validate_custom_rules)
        rules_layout.addWidget(validate_rules_btn)
        
        layout.addWidget(rules_group)
        
        layout.addStretch()
        return tab
        
    def create_test_preview_tab(self):
        """创建测试预览标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 测试输入区域
        input_group = QGroupBox("测试输入")
        input_layout = QVBoxLayout(input_group)
        
        # 测试描述
        input_layout.addWidget(QLabel("测试描述:"))
        self.test_description_edit = QTextEdit()
        self.test_description_edit.setMaximumHeight(80)
        self.test_description_edit.setPlaceholderText("输入要测试的场景描述...")
        input_layout.addWidget(self.test_description_edit)
        
        # 角色列表
        characters_layout = QHBoxLayout()
        characters_layout.addWidget(QLabel("相关角色:"))
        self.test_characters_edit = QLineEdit()
        self.test_characters_edit.setPlaceholderText("输入角色名称，用逗号分隔")
        characters_layout.addWidget(self.test_characters_edit)
        input_layout.addLayout(characters_layout)
        
        # 测试按钮
        test_btn_layout = QHBoxLayout()
        self.run_test_btn = QPushButton("运行测试")
        self.run_test_btn.setObjectName("primary-button")
        self.run_test_btn.clicked.connect(self.run_test)
        
        self.clear_test_btn = QPushButton("清空结果")
        self.clear_test_btn.setObjectName("secondary-button")
        self.clear_test_btn.clicked.connect(self.clear_test_results)
        
        test_btn_layout.addWidget(self.run_test_btn)
        test_btn_layout.addWidget(self.clear_test_btn)
        test_btn_layout.addStretch()
        input_layout.addLayout(test_btn_layout)
        
        layout.addWidget(input_group)
        
        # 测试结果区域
        results_group = QGroupBox("测试结果")
        results_layout = QVBoxLayout(results_group)
        
        # 进度条
        self.test_progress = QProgressBar()
        self.test_progress.setVisible(False)
        results_layout.addWidget(self.test_progress)
        
        # 结果显示
        self.test_results_edit = QTextEdit()
        self.test_results_edit.setReadOnly(True)
        results_layout.addWidget(self.test_results_edit)
        
        layout.addWidget(results_group)
        
        return tab
        
    def create_performance_tab(self):
        """创建性能监控标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 性能统计
        stats_group = QGroupBox("性能统计")
        stats_layout = QGridLayout(stats_group)
        
        # 统计标签
        stats_layout.addWidget(QLabel("平均处理时间:"), 0, 0)
        self.avg_time_label = QLabel("-- ms")
        stats_layout.addWidget(self.avg_time_label, 0, 1)
        
        stats_layout.addWidget(QLabel("缓存命中率:"), 1, 0)
        self.cache_hit_rate_label = QLabel("-- %")
        stats_layout.addWidget(self.cache_hit_rate_label, 1, 1)
        
        stats_layout.addWidget(QLabel("总处理次数:"), 2, 0)
        self.total_processed_label = QLabel("0")
        stats_layout.addWidget(self.total_processed_label, 2, 1)
        
        stats_layout.addWidget(QLabel("平均质量评分:"), 3, 0)
        self.avg_quality_label = QLabel("-- ")
        stats_layout.addWidget(self.avg_quality_label, 3, 1)
        
        layout.addWidget(stats_group)
        
        # 性能控制
        control_group = QGroupBox("性能控制")
        control_layout = QVBoxLayout(control_group)
        
        # 控制按钮
        control_btn_layout = QHBoxLayout()
        
        self.refresh_stats_btn = QPushButton("刷新统计")
        self.refresh_stats_btn.clicked.connect(self.refresh_performance_stats)
        
        self.clear_cache_btn = QPushButton("清空缓存")
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        
        self.reset_stats_btn = QPushButton("重置统计")
        self.reset_stats_btn.clicked.connect(self.reset_performance_stats)
        
        control_btn_layout.addWidget(self.refresh_stats_btn)
        control_btn_layout.addWidget(self.clear_cache_btn)
        control_btn_layout.addWidget(self.reset_stats_btn)
        control_btn_layout.addStretch()
        
        control_layout.addLayout(control_btn_layout)
        layout.addWidget(control_group)
        
        # 性能日志
        log_group = QGroupBox("性能日志")
        log_layout = QVBoxLayout(log_group)
        
        self.performance_log_edit = QTextEdit()
        self.performance_log_edit.setReadOnly(True)
        self.performance_log_edit.setMaximumHeight(200)
        log_layout.addWidget(self.performance_log_edit)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
        return tab
        
    def init_enhancer(self):
        """初始化增强器"""
        try:
            # 初始化LLM API
            llm_api = self._init_llm_api()
            
            self.enhancer = SceneDescriptionEnhancer(self.project_root, llm_api=llm_api)
            # 设置输出目录，确保能正确找到project.json文件
            self.enhancer.output_dir = self.project_root
            self.apply_config_to_enhancer()
            logger.info("场景描述增强器初始化成功")
        except Exception as e:
            logger.error(f"初始化增强器失败: {e}")
            QMessageBox.warning(self, "警告", f"初始化增强器失败: {e}")
    
    def _init_llm_api(self):
        """初始化LLM服务"""
        try:
            from src.core.service_manager import ServiceManager, ServiceType

            service_manager = ServiceManager()
            llm_service = service_manager.get_service(ServiceType.LLM)

            if llm_service:
                logger.info("LLM服务初始化成功")
                return llm_service
            else:
                logger.warning("未找到LLM服务，场景增强器将使用传统方法")
                return None

        except Exception as e:
            logger.error(f"初始化LLM服务失败: {e}")
            return None
            
    def apply_config_to_enhancer(self):
        """将配置应用到增强器"""
        if self.enhancer:
            try:
                self.enhancer.update_config(**self.current_config)
                logger.info("配置已应用到增强器")
            except Exception as e:
                logger.error(f"应用配置失败: {e}")
                
    def on_config_changed(self):
        """配置变更处理"""
        self.update_current_config()
        self.apply_config_to_enhancer()
        self.config_changed.emit(self.current_config)
        
    def on_quality_threshold_changed(self, value):
        """质量阈值变更处理"""
        threshold = value / 100.0
        self.quality_threshold_label.setText(f"{threshold:.2f}")
        self.on_config_changed()
        
    def update_current_config(self):
        """更新当前配置"""
        # 将中文选项转换为英文配置值
        strategy_cn = self.strategy_combo.currentText()
        strategy_en = self.strategy_mapping.get(strategy_cn, 'intelligent')
        
        level_cn = self.enhancement_level_combo.currentText()
        level_en = self.level_mapping.get(level_cn, 'medium')
        
        performance_cn = self.performance_mode_combo.currentText()
        performance_en = self.performance_mapping.get(performance_cn, 'balanced')
        
        self.current_config.update({
            'fusion_strategy': strategy_en,
            'quality_threshold': self.quality_threshold_slider.value() / 100.0,
            'enhancement_level': level_en,
            'enable_technical_details': self.technical_details_cb.isChecked(),
            'enable_consistency_injection': self.consistency_injection_cb.isChecked(),
            'cache_enabled': self.cache_enabled_cb.isChecked(),
            'performance_mode': performance_en,
            'cache_size_limit': self.cache_size_spin.value(),
            'concurrent_processes': self.concurrent_processes_spin.value()
        })
        
    def load_config(self):
        """加载配置"""
        try:
            # 从增强器配置管理器加载配置
            enhancer_config = self.enhancer_config_manager.get_config()
            
            if enhancer_config:
                self.current_config.update(enhancer_config)
                
            # 更新UI控件 - 将英文配置值转换为中文显示
            strategy_en = self.current_config.get('fusion_strategy', 'intelligent')
            strategy_cn = self.strategy_reverse_mapping.get(strategy_en, '智能')
            self.strategy_combo.setCurrentText(strategy_cn)
            
            self.quality_threshold_slider.setValue(int(self.current_config.get('quality_threshold', 0.6) * 100))
            
            level_en = self.current_config.get('enhancement_level', 'medium')
            level_cn = self.level_reverse_mapping.get(level_en, '中')
            self.enhancement_level_combo.setCurrentText(level_cn)
            
            self.technical_details_cb.setChecked(self.current_config.get('enable_technical_details', True))
            self.consistency_injection_cb.setChecked(self.current_config.get('enable_consistency_injection', True))
            self.cache_enabled_cb.setChecked(self.current_config.get('cache_enabled', True))
            
            performance_en = self.current_config.get('performance_mode', 'balanced')
            performance_cn = self.performance_reverse_mapping.get(performance_en, '平衡')
            self.performance_mode_combo.setCurrentText(performance_cn)
            
            self.cache_size_spin.setValue(self.current_config.get('cache_size_limit', 100))
            self.concurrent_processes_spin.setValue(self.current_config.get('concurrent_processes', 2))
            
            # 加载自定义规则
            custom_rules = self.current_config.get('custom_rules', {})
            if custom_rules:
                self.custom_rules_edit.setPlainText(json.dumps(custom_rules, indent=2, ensure_ascii=False))
            
            # 应用配置到增强器
            self.apply_config_to_enhancer()
            
            logger.info("配置加载成功")
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            QMessageBox.warning(self, "警告", f"加载配置失败: {e}")
    
    def load_custom_rules(self, custom_rules):
        """加载自定义规则到界面"""
        try:
            if custom_rules and hasattr(self, 'custom_rules_edit'):
                import json
                rules_text = json.dumps(custom_rules, indent=2, ensure_ascii=False)
                self.custom_rules_edit.setPlainText(rules_text)
        except Exception as e:
            logger.error(f"加载自定义规则失败: {e}")
            
    def save_config(self):
        """保存配置"""
        try:
            self.update_current_config()
            
            # 保存自定义规则
            custom_rules_text = self.custom_rules_edit.toPlainText().strip()
            if custom_rules_text:
                try:
                    custom_rules = json.loads(custom_rules_text)
                    self.current_config['custom_rules'] = custom_rules
                except json.JSONDecodeError:
                    QMessageBox.warning(self, "警告", "自定义规则JSON格式错误，将忽略该部分")
            
            # 保存到增强器配置管理器
            self.enhancer_config_manager.update_config(self.current_config)
            self.enhancer_config_manager.save_config()
            
            logger.info("配置保存成功")
            QMessageBox.information(self, "成功", "配置已保存")
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            QMessageBox.warning(self, "错误", f"保存配置失败: {e}")
            
    def export_config(self):
        """导出配置"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出配置", "scene_enhancer_config.json", "JSON Files (*.json)"
            )
            
            if file_path:
                self.update_current_config()
                
                export_data = {
                    'config': self.current_config,
                    'export_time': datetime.now().isoformat(),
                    'version': '1.0'
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                    
                QMessageBox.information(self, "成功", f"配置已导出到: {file_path}")
                
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            QMessageBox.warning(self, "错误", f"导出配置失败: {e}")
            
    def import_config(self):
        """导入配置"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "导入配置", "", "JSON Files (*.json)"
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
                    
                if 'config' in import_data:
                    self.current_config.update(import_data['config'])
                    self.load_config()  # 重新加载UI
                    QMessageBox.information(self, "成功", "配置导入成功")
                else:
                    QMessageBox.warning(self, "错误", "无效的配置文件格式")
                    
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            QMessageBox.warning(self, "错误", f"导入配置失败: {e}")
            
    def validate_custom_rules(self):
        """验证自定义规则"""
        try:
            rules_text = self.custom_rules_edit.toPlainText().strip()
            if rules_text:
                json.loads(rules_text)  # 验证JSON格式
                QMessageBox.information(self, "验证成功", "自定义规则格式正确")
            else:
                QMessageBox.information(self, "提示", "自定义规则为空")
                
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "验证失败", f"JSON格式错误: {e}")
        except Exception as e:
            QMessageBox.warning(self, "验证失败", f"验证失败: {e}")
            
    def run_test(self):
        """运行测试"""
        if not self.enhancer:
            QMessageBox.warning(self, "错误", "增强器未初始化")
            return
            
        test_description = self.test_description_edit.toPlainText().strip()
        if not test_description:
            QMessageBox.warning(self, "错误", "请输入测试描述")
            return
            
        # 解析角色列表
        characters_text = self.test_characters_edit.text().strip()
        characters = [c.strip() for c in characters_text.split(',') if c.strip()] if characters_text else []
        
        # 显示进度条
        self.test_progress.setVisible(True)
        self.test_progress.setRange(0, 0)  # 无限进度条
        self.run_test_btn.setEnabled(False)
        
        # 创建工作线程
        self.test_worker = EnhancerTestWorker(self.enhancer, test_description, characters)
        self.test_thread = QThread()
        self.test_worker.moveToThread(self.test_thread)
        
        # 连接信号
        self.test_thread.started.connect(self.test_worker.run)
        self.test_worker.test_completed.connect(self.on_test_completed)
        self.test_worker.error_occurred.connect(self.on_test_error)
        self.test_worker.progress_updated.connect(self.on_test_progress)
        
        # 启动线程
        self.test_thread.start()
        
    def on_test_completed(self, details):
        """测试完成处理"""
        try:
            # 格式化结果显示
            result_text = f"""测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

原始描述:
{self.test_description_edit.toPlainText()}

增强描述:
{details['enhanced_description']}

融合策略: {details['fusion_strategy']}
质量评分: {details['fusion_quality_score']:.3f}

技术细节:
{json.dumps(details.get('technical_details', {}), indent=2, ensure_ascii=False)}

一致性信息:
{json.dumps(details.get('consistency_info', {}), indent=2, ensure_ascii=False)}

{'='*50}
"""
            
            # 追加到结果显示区域
            current_text = self.test_results_edit.toPlainText()
            self.test_results_edit.setPlainText(current_text + result_text)
            
            # 滚动到底部
            cursor = self.test_results_edit.textCursor()
            cursor.movePosition(cursor.End)
            self.test_results_edit.setTextCursor(cursor)
            
        except Exception as e:
            logger.error(f"处理测试结果失败: {e}")
            
        finally:
            self.cleanup_test_thread()
            
    def on_test_error(self, error_msg):
        """测试错误处理"""
        QMessageBox.warning(self, "测试失败", f"测试过程中发生错误: {error_msg}")
        self.cleanup_test_thread()
        
    def on_test_progress(self, message):
        """测试进度更新"""
        # 可以在这里显示进度信息
        pass
        
    def cleanup_test_thread(self):
        """清理测试线程"""
        self.test_progress.setVisible(False)
        self.run_test_btn.setEnabled(True)
        
        if self.test_thread:
            self.test_thread.quit()
            self.test_thread.wait()
            self.test_thread = None
            self.test_worker = None
            
    def clear_test_results(self):
        """清空测试结果"""
        self.test_results_edit.clear()
        
    def refresh_performance_stats(self):
        """刷新性能统计"""
        if self.enhancer:
            try:
                # 获取性能统计（如果增强器支持）
                stats = getattr(self.enhancer, 'get_performance_stats', lambda: {})() or {}
                
                self.avg_time_label.setText(f"{stats.get('avg_time', 0):.2f} ms")
                self.cache_hit_rate_label.setText(f"{stats.get('cache_hit_rate', 0):.1f} %")
                self.total_processed_label.setText(str(stats.get('total_processed', 0)))
                self.avg_quality_label.setText(f"{stats.get('avg_quality', 0):.3f}")
                
                # 更新性能日志
                log_text = f"[{datetime.now().strftime('%H:%M:%S')}] 性能统计已刷新\n"
                self.performance_log_edit.append(log_text)
                
            except Exception as e:
                logger.error(f"刷新性能统计失败: {e}")
                
    def clear_cache(self):
        """清空缓存"""
        if self.enhancer:
            try:
                # 清空缓存（如果增强器支持）
                if hasattr(self.enhancer, 'clear_cache'):
                    self.enhancer.clear_cache()
                    
                log_text = f"[{datetime.now().strftime('%H:%M:%S')}] 缓存已清空\n"
                self.performance_log_edit.append(log_text)
                
                QMessageBox.information(self, "成功", "缓存已清空")
                
            except Exception as e:
                logger.error(f"清空缓存失败: {e}")
                QMessageBox.warning(self, "错误", f"清空缓存失败: {e}")
                
    def reset_performance_stats(self):
        """重置性能统计"""
        if self.enhancer:
            try:
                # 重置统计（如果增强器支持）
                if hasattr(self.enhancer, 'reset_stats'):
                    self.enhancer.reset_stats()
                    
                # 清空显示
                self.avg_time_label.setText("-- ms")
                self.cache_hit_rate_label.setText("-- %")
                self.total_processed_label.setText("0")
                self.avg_quality_label.setText("-- ")
                
                log_text = f"[{datetime.now().strftime('%H:%M:%S')}] 性能统计已重置\n"
                self.performance_log_edit.append(log_text)
                
                QMessageBox.information(self, "成功", "性能统计已重置")
                
            except Exception as e:
                logger.error(f"重置性能统计失败: {e}")
                QMessageBox.warning(self, "错误", f"重置性能统计失败: {e}")
                
    def get_current_config(self):
        """获取当前配置"""
        self.update_current_config()
        return self.current_config.copy()
        
    def set_project_root(self, project_root):
        """设置项目根目录"""
        self.project_root = project_root
        self.init_enhancer()