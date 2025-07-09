# -*- coding: utf-8 -*-
"""
工作流配置面板模块
用于管理ComfyUI工作流的配置界面
"""

import os
import json
import random
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QSpinBox, QDoubleSpinBox, QLineEdit, QPushButton,
    QScrollArea, QFrame
)
from PyQt5.QtCore import pyqtSignal

from src.utils.logger import logger


class WorkflowPanel(QWidget):
    """工作流配置面板"""
    
    # 信号定义
    workflow_changed = pyqtSignal(str)  # 工作流变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.workflows_dir = ""
        self.workflow_param_widgets = {}  # 存储参数控件的字典
        
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 工作流选择
        workflow_layout = QHBoxLayout()
        workflow_layout.addWidget(QLabel("选择工作流:"))
        
        self.workflow_combo = QComboBox()
        self.workflow_combo.currentTextChanged.connect(self.on_workflow_changed)
        workflow_layout.addWidget(self.workflow_combo)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setMaximumWidth(60)
        refresh_btn.clicked.connect(self.refresh_workflows)
        workflow_layout.addWidget(refresh_btn)
        
        layout.addLayout(workflow_layout)
        
        # 工作流参数配置区域
        params_label = QLabel("工作流参数:")
        layout.addWidget(params_label)
        
        # 创建滚动区域用于参数配置
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(300)
        
        self.params_widget = QWidget()
        self.workflow_params_layout = QVBoxLayout(self.params_widget)
        
        scroll_area.setWidget(self.params_widget)
        layout.addWidget(scroll_area)
        
        # 样式已在CSS文件中定义
    
    def set_workflows_directory(self, workflows_dir):
        """设置工作流目录"""
        self.workflows_dir = workflows_dir
        self.refresh_workflows()
    
    def refresh_workflows(self):
        """刷新工作流列表"""
        try:
            # 临时阻塞信号，防止在刷新过程中触发on_workflow_changed
            self.workflow_combo.blockSignals(True)
            
            self.workflow_combo.clear()
            
            if not self.workflows_dir or not os.path.exists(self.workflows_dir):
                self.workflow_combo.addItem("无工作流目录")
                self.workflow_combo.blockSignals(False)
                return
            
            # 扫描工作流文件
            workflow_files = [f for f in os.listdir(self.workflows_dir) if f.endswith('.json')]
            
            if not workflow_files:
                self.workflow_combo.addItem("无可用工作流")
                self.workflow_combo.blockSignals(False)
                return
            
            for workflow_file in workflow_files:
                workflow_name = os.path.splitext(workflow_file)[0]
                self.workflow_combo.addItem(workflow_name)
            
            # 恢复信号
            self.workflow_combo.blockSignals(False)
            
            # 尝试恢复上次选择的工作流，如果失败则选择第一个工作流
            if workflow_files:
                if not self.restore_workflow_selection():
                    # 如果没有保存的选择或恢复失败，默认选择第一个工作流但不保存
                    workflow_name = self.workflow_combo.currentText()
                    self._load_workflow_without_save(workflow_name)
                
            logger.info(f"已加载 {len(workflow_files)} 个工作流")
            
        except Exception as e:
            logger.error(f"刷新工作流列表失败: {e}")
            # 确保在异常情况下也恢复信号
            self.workflow_combo.blockSignals(False)
            self.workflow_combo.addItem("加载失败")
    
    def on_workflow_changed(self, workflow_name):
        """工作流选择变更处理"""
        if workflow_name in ["无可用工作流", "加载失败", "", "无工作流目录"]:
            self.clear_workflow_params()
            return
            
        try:
            # 加载工作流配置
            workflow_path = os.path.join(self.workflows_dir, f"{workflow_name}.json")
            
            if not os.path.exists(workflow_path):
                logger.error(f"工作流文件不存在: {workflow_path}")
                return
            
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow_config = json.load(f)
            
            # 生成参数配置界面
            self.generate_workflow_params_ui(workflow_config.get('parameters', {}))
            
            # 保存工作流选择到应用设置
            self.save_workflow_selection(workflow_name)
            
            # 发射工作流变更信号
            self.workflow_changed.emit(workflow_name)
            
            logger.info(f"已切换到工作流: {workflow_name}")
            
        except Exception as e:
            logger.error(f"切换工作流失败: {e}")
            self.clear_workflow_params()
    
    def _load_workflow_without_save(self, workflow_name):
        """加载工作流但不保存选择（用于初始化）"""
        if workflow_name in ["无可用工作流", "加载失败", "", "无工作流目录"]:
            self.clear_workflow_params()
            return
            
        try:
            # 加载工作流配置
            workflow_path = os.path.join(self.workflows_dir, f"{workflow_name}.json")
            
            if not os.path.exists(workflow_path):
                logger.error(f"工作流文件不存在: {workflow_path}")
                return
            
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow_config = json.load(f)
            
            # 生成参数配置界面
            self.generate_workflow_params_ui(workflow_config.get('parameters', {}))
            
            # 发射工作流变更信号
            self.workflow_changed.emit(workflow_name)
            
            logger.info(f"已加载工作流（初始化）: {workflow_name}")
            
        except Exception as e:
            logger.error(f"加载工作流失败: {e}")
            self.clear_workflow_params()
    
    def generate_workflow_params_ui(self, parameters):
        """生成工作流参数配置界面"""
        # 清空现有参数控件
        self.clear_workflow_params()
        
        # 添加种子值设置
        self.add_seed_controls()
        
        if not parameters:
            no_params_label = QLabel("此工作流无可配置参数")
            no_params_label.setProperty("class", "no-params-label")
            self.workflow_params_layout.addWidget(no_params_label)
            return
        
        # 过滤掉prompt和guidance参数，为其他参数创建控件
        filtered_params = {k: v for k, v in parameters.items() 
                          if k not in ['prompt', 'guidance']}
        
        for param_name, param_config in filtered_params.items():
            param_layout = QHBoxLayout()
            
            # 参数标签
            label = QLabel(f"{param_config.get('display_name', param_name)}:")
            label.setMinimumWidth(80)
            param_layout.addWidget(label)
            
            # 根据参数类型创建对应控件
            param_type = param_config.get('type', 'text')
            default_value = param_config.get('default', '')
            
            if param_type == 'int':
                widget = QSpinBox()
                widget.setRange(param_config.get('min', 1), param_config.get('max', 100))
                widget.setValue(default_value)
            elif param_type == 'float':
                widget = QDoubleSpinBox()
                widget.setRange(param_config.get('min', 0.1), param_config.get('max', 10.0))
                widget.setSingleStep(0.1)
                widget.setValue(default_value)
            elif param_type == 'choice':
                widget = QComboBox()
                choices = param_config.get('choices', [])
                widget.addItems(choices)
                if default_value in choices:
                    widget.setCurrentText(default_value)
            else:  # text
                widget = QLineEdit()
                widget.setText(str(default_value))
            
            # 设置工具提示
            if 'description' in param_config:
                widget.setToolTip(param_config['description'])
            
            param_layout.addWidget(widget)
            
            # 保存控件引用
            self.workflow_param_widgets[param_name] = widget
            
            # 添加到布局
            param_widget = QWidget()
            param_widget.setLayout(param_layout)
            self.workflow_params_layout.addWidget(param_widget)
    
    def add_seed_controls(self):
        """添加种子值设置控件"""
        # 种子值设置
        seed_layout = QHBoxLayout()
        seed_label = QLabel("种子值:")
        seed_label.setMinimumWidth(80)
        seed_layout.addWidget(seed_label)
        
        self.seed_input = QSpinBox()
        self.seed_input.setRange(-1, 2147483647)  # -1表示随机种子
        self.seed_input.setValue(-1)
        self.seed_input.setSpecialValueText("随机")
        seed_layout.addWidget(self.seed_input)
        
        # 随机种子按钮
        random_seed_btn = QPushButton("随机")
        random_seed_btn.setMaximumWidth(60)
        random_seed_btn.clicked.connect(self.generate_random_seed)
        seed_layout.addWidget(random_seed_btn)
        
        seed_widget = QWidget()
        seed_widget.setLayout(seed_layout)
        self.workflow_params_layout.addWidget(seed_widget)
        
        # 保存种子值控件引用
        self.workflow_param_widgets['seed'] = self.seed_input
        
        # 添加图片尺寸设置
        self.add_image_size_controls()
        
        # 添加生图步数设置
        self.add_steps_controls()
    
    def add_image_size_controls(self):
        """添加图片尺寸设置控件"""
        # 图片宽度设置
        width_layout = QHBoxLayout()
        width_label = QLabel("图片宽度:")
        width_label.setMinimumWidth(80)
        width_layout.addWidget(width_label)
        
        self.width_input = QSpinBox()
        self.width_input.setRange(256, 4096)
        self.width_input.setSingleStep(64)
        self.width_input.setValue(1024)
        self.width_input.setToolTip("设置生成图片的宽度（像素）")
        width_layout.addWidget(self.width_input)
        
        width_widget = QWidget()
        width_widget.setLayout(width_layout)
        self.workflow_params_layout.addWidget(width_widget)
        
        # 图片高度设置
        height_layout = QHBoxLayout()
        height_label = QLabel("图片高度:")
        height_label.setMinimumWidth(80)
        height_layout.addWidget(height_label)
        
        self.height_input = QSpinBox()
        self.height_input.setRange(256, 4096)
        self.height_input.setSingleStep(64)
        self.height_input.setValue(1024)
        self.height_input.setToolTip("设置生成图片的高度（像素）")
        height_layout.addWidget(self.height_input)
        
        height_widget = QWidget()
        height_widget.setLayout(height_layout)
        self.workflow_params_layout.addWidget(height_widget)
        
        # 保存尺寸控件引用
        self.workflow_param_widgets['width'] = self.width_input
        self.workflow_param_widgets['height'] = self.height_input
    
    def add_steps_controls(self):
        """添加生图步数设置控件"""
        # 生图步数设置
        steps_layout = QHBoxLayout()
        steps_label = QLabel("生图步数:")
        steps_label.setMinimumWidth(80)
        steps_layout.addWidget(steps_label)
        
        self.steps_input = QSpinBox()
        self.steps_input.setRange(1, 150)
        self.steps_input.setValue(25)
        self.steps_input.setToolTip("设置图像生成的采样步数，步数越高质量越好但生成时间越长")
        steps_layout.addWidget(self.steps_input)
        
        steps_widget = QWidget()
        steps_widget.setLayout(steps_layout)
        self.workflow_params_layout.addWidget(steps_widget)
        
        # 保存步数控件引用
        self.workflow_param_widgets['steps'] = self.steps_input
    
    def generate_random_seed(self):
        """生成随机种子值"""
        random_seed = random.randint(0, 2147483647)
        self.seed_input.setValue(random_seed)
    
    def clear_workflow_params(self):
        """清空工作流参数控件"""
        # 清空控件字典
        self.workflow_param_widgets.clear()
        
        # 移除所有子控件
        while self.workflow_params_layout.count():
            child = self.workflow_params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def get_current_workflow_parameters(self):
        """获取当前工作流参数值"""
        parameters = {}
        
        for param_name, widget in self.workflow_param_widgets.items():
            if isinstance(widget, QSpinBox):
                value = widget.value()
                # 处理种子值：-1表示随机种子，需要生成实际的随机数
                if param_name == 'seed' and value == -1:
                    value = random.randint(0, 2147483647)
                parameters[param_name] = value
            elif isinstance(widget, QDoubleSpinBox):
                parameters[param_name] = widget.value()
            elif isinstance(widget, QComboBox):
                parameters[param_name] = widget.currentText()
            elif isinstance(widget, QLineEdit):
                parameters[param_name] = widget.text()
        
        return parameters
    
    def get_current_workflow_name(self):
        """获取当前选择的工作流名称"""
        return self.workflow_combo.currentText()
    
    def save_workflow_selection(self, workflow_name):
        """保存工作流选择到应用设置"""
        try:
            # 获取父窗口的应用设置
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'app_settings'):
                parent_window = parent_window.parent()
            
            if parent_window and hasattr(parent_window, 'app_settings'):
                parent_window.app_settings['selected_workflow'] = workflow_name
                parent_window._save_app_settings()
                logger.debug(f"已保存工作流选择: {workflow_name}")
            else:
                logger.warning("未找到具有app_settings属性的父窗口")
        except Exception as e:
            logger.error(f"保存工作流选择失败: {e}")
    
    def restore_workflow_selection(self):
        """恢复上次选择的工作流"""
        try:
            # 获取父窗口的应用设置
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'app_settings'):
                parent_window = parent_window.parent()
            
            if parent_window and hasattr(parent_window, 'app_settings'):
                selected_workflow = parent_window.app_settings.get('selected_workflow', '')
                if selected_workflow:
                    # 调试：打印下拉框中的所有工作流
                    all_workflows = [self.workflow_combo.itemText(i) for i in range(self.workflow_combo.count())]
                    logger.debug(f"下拉框中的工作流: {all_workflows}")
                    logger.debug(f"尝试恢复的工作流: {selected_workflow}")
                    
                    # 查找并设置工作流
                    index = self.workflow_combo.findText(selected_workflow)
                    logger.debug(f"查找结果索引: {index}")
                    
                    if index >= 0:
                        # 阻止信号触发，避免重复保存
                        self.workflow_combo.blockSignals(True)
                        self.workflow_combo.setCurrentIndex(index)
                        self.workflow_combo.blockSignals(False)
                        
                        # 加载工作流但不保存
                        self._load_workflow_without_save(selected_workflow)
                        logger.info(f"已恢复工作流选择: {selected_workflow}")
                        return True
                    else:
                        logger.warning(f"未找到保存的工作流: {selected_workflow}")
                        logger.warning(f"可用的工作流: {all_workflows}")
        except Exception as e:
            logger.error(f"随机化参数失败: {e}")
            return False
    
    def get_current_settings(self):
        """获取当前工作流设置"""
        try:
            settings = {
                'selected_workflow': self.workflow_combo.currentText(),
                'parameters': {}
            }
            
            # 获取所有参数控件的值
            for param_name, widget in self.workflow_param_widgets.items():
                try:
                    if hasattr(widget, 'value'):
                        settings['parameters'][param_name] = widget.value()
                    elif hasattr(widget, 'text'):
                        settings['parameters'][param_name] = widget.text()
                    elif hasattr(widget, 'currentText'):
                        settings['parameters'][param_name] = widget.currentText()
                    elif hasattr(widget, 'isChecked'):
                        settings['parameters'][param_name] = widget.isChecked()
                except Exception as e:
                    logger.warning(f"获取参数 {param_name} 的值失败: {e}")
                    continue
            
            return settings
            
        except Exception as e:
            logger.error(f"获取工作流设置失败: {e}")
            return {}
    
    def load_settings(self, settings):
        """加载工作流设置"""
        try:
            if not settings:
                return
            
            # 加载选中的工作流
            if 'selected_workflow' in settings:
                workflow_name = settings['selected_workflow']
                index = self.workflow_combo.findText(workflow_name)
                if index >= 0:
                    self.workflow_combo.setCurrentIndex(index)
            
            # 加载参数值
            if 'parameters' in settings:
                for param_name, value in settings['parameters'].items():
                    if param_name in self.workflow_param_widgets:
                        widget = self.workflow_param_widgets[param_name]
                        try:
                            if hasattr(widget, 'setValue'):
                                widget.setValue(value)
                            elif hasattr(widget, 'setText'):
                                widget.setText(str(value))
                            elif hasattr(widget, 'setCurrentText'):
                                widget.setCurrentText(str(value))
                            elif hasattr(widget, 'setChecked'):
                                widget.setChecked(bool(value))
                        except Exception as e:
                            logger.warning(f"设置参数 {param_name} 的值失败: {e}")
                            continue
            
            logger.info("工作流设置已加载")
            
        except Exception as e:
            logger.error(f"加载工作流设置失败: {e}")
    
    def reset_to_default(self):
        """重置到默认设置"""
        try:
            # 重置工作流选择
            if self.workflow_combo.count() > 0:
                self.workflow_combo.setCurrentIndex(0)
            
            # 重置所有参数到默认值
            for param_name, widget in self.workflow_param_widgets.items():
                try:
                    if hasattr(widget, 'setValue'):
                        if hasattr(widget, 'minimum'):
                            widget.setValue(widget.minimum())
                        else:
                            widget.setValue(0)
                    elif hasattr(widget, 'setText'):
                        widget.setText('')
                    elif hasattr(widget, 'setCurrentIndex'):
                        widget.setCurrentIndex(0)
                    elif hasattr(widget, 'setChecked'):
                        widget.setChecked(False)
                except Exception as e:
                    logger.warning(f"重置参数 {param_name} 失败: {e}")
                    continue
            
            logger.info("工作流设置已重置为默认值")
            
        except Exception as e:
            logger.error(f"重置工作流设置失败: {e}")