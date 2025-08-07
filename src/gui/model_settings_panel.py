#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型设置面板
提供更简洁的模型管理界面，作为现有ModelManagerDialog的补充
"""

import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QFormLayout, QGroupBox, QMessageBox, QListWidget, QListWidgetItem,
    QSplitter, QTextEdit, QCheckBox, QProgressDialog, QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from src.utils.logger import logger
from src.utils.config_manager import ConfigManager
from src.gui.model_manager_dialog import ModelManagerDialog


class ModelSettingsPanel(QWidget):
    """模型设置面板"""
    
    # 信号：模型配置更新
    models_updated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = ConfigManager()
        self.init_ui()
        self.load_models()
    
    def init_ui(self):
        """初始化UI界面"""
        main_layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("模型配置管理")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 模型列表区域
        models_group = QGroupBox("已配置模型")
        models_layout = QVBoxLayout(models_group)
        
        self.models_list = QListWidget()
        self.models_list.setMinimumHeight(200)
        models_layout.addWidget(self.models_list)
        
        # 按钮区域
        buttons_layout = QHBoxLayout()
        
        self.add_model_btn = QPushButton("添加模型")
        self.add_model_btn.setObjectName("primary-button")
        self.add_model_btn.clicked.connect(self.add_model)
        
        self.edit_model_btn = QPushButton("编辑模型")
        self.edit_model_btn.setObjectName("secondary-button")
        self.edit_model_btn.clicked.connect(self.edit_model)
        
        self.delete_model_btn = QPushButton("删除模型")
        self.delete_model_btn.setObjectName("danger-button")
        self.delete_model_btn.clicked.connect(self.delete_model)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_models)
        
        buttons_layout.addWidget(self.add_model_btn)
        buttons_layout.addWidget(self.edit_model_btn)
        buttons_layout.addWidget(self.delete_model_btn)
        buttons_layout.addWidget(self.refresh_btn)
        buttons_layout.addStretch()
        
        models_layout.addLayout(buttons_layout)
        main_layout.addWidget(models_group)
        
        # 模型详情区域
        details_group = QGroupBox("模型详情")
        details_layout = QFormLayout(details_group)
        
        self.model_name_label = QLabel("-")
        self.model_type_label = QLabel("-")
        self.model_url_label = QLabel("-")
        
        details_layout.addRow("模型名称:", self.model_name_label)
        details_layout.addRow("模型类型:", self.model_type_label)
        details_layout.addRow("API地址:", self.model_url_label)
        
        main_layout.addWidget(details_group)
        
        # 高级管理按钮
        advanced_layout = QHBoxLayout()
        self.advanced_btn = QPushButton("高级模型管理")
        self.advanced_btn.setObjectName("primary-button")
        self.advanced_btn.clicked.connect(self.open_advanced_manager)
        advanced_layout.addStretch()
        advanced_layout.addWidget(self.advanced_btn)
        
        main_layout.addLayout(advanced_layout)
        main_layout.addStretch()
        
        # 初始状态
        self.edit_model_btn.setEnabled(False)
        self.delete_model_btn.setEnabled(False)
        
        # 连接信号
        self.models_list.itemClicked.connect(self.on_model_selected)
    
    def load_models(self):
        """加载模型列表"""
        try:
            self.models_list.clear()
            models = self.config_manager.get_models()
            
            for model in models:
                item = QListWidgetItem(model.get("name", "未命名模型"))
                item.setData(Qt.UserRole, model)
                self.models_list.addItem(item)
            
            # 重置详情显示
            self.model_name_label.setText("-")
            self.model_type_label.setText("-")
            self.model_url_label.setText("-")
            
            # 禁用编辑和删除按钮
            self.edit_model_btn.setEnabled(False)
            self.delete_model_btn.setEnabled(False)
            
        except Exception as e:
            logger.error(f"加载模型列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载模型列表失败: {str(e)}")
    
    def on_model_selected(self, item):
        """模型选中事件"""
        if not item:
            return
            
        model_data = item.data(Qt.UserRole)
        if not model_data:
            return
        
        # 更新详情显示
        self.model_name_label.setText(model_data.get("name", "-"))
        self.model_type_label.setText(model_data.get("type", "-"))
        self.model_url_label.setText(model_data.get("url", "-"))
        
        # 启用编辑和删除按钮
        self.edit_model_btn.setEnabled(True)
        self.delete_model_btn.setEnabled(True)
    
    def add_model(self):
        """添加新模型"""
        try:
            dialog = ModelManagerDialog(self.config_manager, self)
            # 连接模型更新信号
            dialog.models_updated.connect(self.on_models_updated)
            dialog.exec_()
        except Exception as e:
            logger.error(f"打开模型管理对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"打开模型管理对话框失败: {e}")
    
    def edit_model(self):
        """编辑选中的模型"""
        current_item = self.models_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个模型")
            return
        
        try:
            dialog = ModelManagerDialog(self.config_manager, self)
            # 连接模型更新信号
            dialog.models_updated.connect(self.on_models_updated)
            dialog.exec_()
            
            # 选择当前编辑的模型
            for i in range(dialog.model_list.count()):
                if dialog.model_list.item(i).text() == current_item.text():
                    dialog.model_list.setCurrentRow(i)
                    dialog.on_model_selected(dialog.model_list.item(i))
                    break
            
        except Exception as e:
            logger.error(f"打开模型管理对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"打开模型管理对话框失败: {e}")
    
    def delete_model(self):
        """删除选中的模型"""
        current_item = self.models_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个模型")
            return
        
        model_name = current_item.text()
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除模型 '{model_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 从配置中删除
                models = self.config_manager.config.get("models", [])
                model_data = current_item.data(Qt.UserRole)
                
                if model_data in models:
                    models.remove(model_data)
                    self.config_manager.config["models"] = models
                    
                    # 保存配置
                    self.save_config_to_file()
                    
                    # 重新加载列表
                    self.load_models()
                    
                    # 发送更新信号
                    self.models_updated.emit()
                    
                    QMessageBox.information(self, "成功", f"模型 '{model_name}' 已删除")
                
            except Exception as e:
                logger.error(f"删除模型失败: {e}")
                QMessageBox.critical(self, "错误", f"删除模型失败: {str(e)}")
    
    def save_config_to_file(self):
        """保存配置到文件"""
        config_file = os.path.join(self.config_manager.config_dir, 'llm_config.json')
        os.makedirs(self.config_manager.config_dir, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config_manager.config, f, indent=4, ensure_ascii=False)
    
    def open_advanced_manager(self):
        """打开高级模型管理对话框"""
        try:
            dialog = ModelManagerDialog(self.config_manager, self)
            # 连接模型更新信号
            dialog.models_updated.connect(self.on_models_updated)
            dialog.exec_()
        except Exception as e:
            logger.error(f"打开模型管理对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"打开模型管理对话框失败: {e}")
    
    def on_models_updated(self):
        """模型更新事件"""
        self.load_models()
        # 发送更新信号
        self.models_updated.emit()