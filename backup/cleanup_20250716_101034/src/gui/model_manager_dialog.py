#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QFormLayout, QGroupBox, QMessageBox, QListWidget, QListWidgetItem,
    QSplitter, QTextEdit, QCheckBox, QProgressDialog, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from src.utils.logger import logger
from src.utils.config_manager import ConfigManager


class ModelManagerDialog(QDialog):
    """大模型管理对话框"""
    
    # 信号：模型配置更新
    models_updated = pyqtSignal()
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("模型管理")
        self.setModal(True)
        self.resize(900, 700)
        self.setObjectName("model-dialog")
        
        self.init_ui()
        self.load_models()
        
    def init_ui(self):
        """初始化UI界面"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("大模型配置管理")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 主要内容区域
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：模型列表
        left_group = QGroupBox("模型列表")
        left_layout = QVBoxLayout(left_group)
        
        self.model_list = QListWidget()
        self.model_list.itemClicked.connect(self.on_model_selected)
        self.model_list.setMinimumWidth(250)
        left_layout.addWidget(self.model_list)
        
        # 模型操作按钮
        model_buttons_layout = QHBoxLayout()
        self.add_model_btn = QPushButton("添加模型")
        self.add_model_btn.setObjectName("primary-button")
        self.add_model_btn.clicked.connect(self.add_new_model)
        self.delete_model_btn = QPushButton("删除模型")
        self.delete_model_btn.setObjectName("danger-button")
        self.delete_model_btn.clicked.connect(self.delete_model)
        
        model_buttons_layout.addWidget(self.add_model_btn)
        model_buttons_layout.addWidget(self.delete_model_btn)
        left_layout.addLayout(model_buttons_layout)
        left_layout.setSpacing(12)
        
        left_widget = left_group
        splitter.addWidget(left_widget)
        
        # 右侧：模型配置
        right_group = QGroupBox("模型配置")
        right_layout = QVBoxLayout(right_group)
        
        # 模型配置表单
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setVerticalSpacing(16)
        
        self.model_name_edit = QLineEdit()
        self.model_name_edit.textChanged.connect(self.on_config_changed)
        self.model_name_edit.setPlaceholderText("请输入模型名称")
        form_layout.addRow("模型名称:", self.model_name_edit)
        
        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["OpenAI", "Claude", "Gemini", "Deepseek", "Qwen", "GLM", "Custom"])
        self.api_type_combo.currentTextChanged.connect(self.update_preset_info)
        self.api_type_combo.currentTextChanged.connect(self.on_config_changed)
        form_layout.addRow("API类型:", self.api_type_combo)
        
        self.api_url_edit = QLineEdit()
        self.api_url_edit.textChanged.connect(self.on_config_changed)
        self.api_url_edit.setPlaceholderText("请输入API地址")
        form_layout.addRow("API地址:", self.api_url_edit)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.textChanged.connect(self.on_config_changed)
        self.api_key_edit.setPlaceholderText("请输入API密钥")
        
        # API Key输入框和显示开关
        key_layout = QHBoxLayout()
        key_layout.addWidget(self.api_key_edit)
        
        self.show_key_checkbox = QCheckBox("显示API Key")
        self.show_key_checkbox.toggled.connect(self.toggle_key_visibility)
        key_layout.addWidget(self.show_key_checkbox)
        
        key_widget = QWidget()
        key_widget.setLayout(key_layout)
        form_layout.addRow("API Key:", key_widget)
        
        right_layout.addLayout(form_layout)
        
        # 预设配置说明
        info_label = QLabel("配置说明：")
        info_label.setStyleSheet("font-weight: bold; margin-top: 16px;")
        self.preset_info = QTextEdit()
        self.preset_info.setMaximumHeight(120)
        self.preset_info.setReadOnly(True)
        right_layout.addWidget(info_label)
        right_layout.addWidget(self.preset_info)
        
        # 配置操作按钮
        config_buttons_layout = QHBoxLayout()
        config_buttons_layout.setSpacing(12)
        
        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.setObjectName("primary-button")
        self.save_config_btn.clicked.connect(self.save_current_config)
        self.save_config_btn.setEnabled(False)
        
        self.test_config_btn = QPushButton("测试连接")
        self.test_config_btn.setObjectName("secondary-button")
        self.test_config_btn.clicked.connect(self.test_connection)
        self.test_config_btn.setEnabled(False)
        
        config_buttons_layout.addWidget(self.save_config_btn)
        config_buttons_layout.addWidget(self.test_config_btn)
        config_buttons_layout.addStretch()
        right_layout.addLayout(config_buttons_layout)
        right_layout.setSpacing(16)
        
        right_widget = right_group
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([300, 500])
        layout.addWidget(splitter)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(16, 16, 16, 16)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.setObjectName("secondary-button")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setMinimumWidth(100)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)
        layout.setSpacing(16)
        
        self.setLayout(layout)
        
        # 当前选中的模型
        self.current_model = None
        
    def load_models(self):
        """加载模型列表"""
        try:
            self.model_list.clear()
            models = self.config_manager.config.get("models", [])
            
            for model in models:
                item = QListWidgetItem(model.get("name", "未命名模型"))
                item.setData(Qt.UserRole, model)
                self.model_list.addItem(item)
                
            if models:
                self.model_list.setCurrentRow(0)
                self.on_model_selected(self.model_list.item(0))
                
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
            
        self.current_model = model_data
        
        # 填充配置信息
        self.model_name_edit.setText(model_data.get("name", ""))
        self.api_url_edit.setText(model_data.get("url", ""))
        self.api_key_edit.setText(model_data.get("key", ""))
        
        # 设置模型类型
        model_type = model_data.get("type", "OpenAI")
        index = self.api_type_combo.findText(model_type)
        if index >= 0:
            self.api_type_combo.setCurrentIndex(index)
        
        # 更新预设信息
        self.update_preset_info(model_type)
        
        # 启用按钮
        self.delete_model_btn.setEnabled(True)
        self.test_config_btn.setEnabled(True)
        
    def update_preset_info(self, model_type):
        """更新预设配置信息"""
        info_text = ""
        
        if model_type == "OpenAI":
            self.api_url_edit.setText("https://api.openai.com/v1/chat/completions")
            info_text = """OpenAI配置说明：
• API地址：https://api.openai.com/v1/chat/completions
• 需要OpenAI API Key
• 支持模型：gpt-3.5-turbo, gpt-4等
• 获取API Key：https://platform.openai.com/"""
        elif model_type == "Claude":
            self.api_url_edit.setText("https://api.anthropic.com/v1/messages")
            info_text = """Claude配置说明：
• API地址：https://api.anthropic.com/v1/messages
• 需要Anthropic API Key
• 支持模型：claude-3-sonnet, claude-3-haiku等
• 获取API Key：https://console.anthropic.com/"""
        elif model_type == "Gemini":
            self.api_url_edit.setText("https://generativelanguage.googleapis.com/v1beta/models")
            info_text = """Gemini配置说明：
• API地址：https://generativelanguage.googleapis.com/v1beta/models
• 需要Google API Key
• 支持模型：gemini-pro, gemini-pro-vision等
• 获取API Key：https://makersuite.google.com/"""
        elif model_type == "Deepseek":
            self.api_url_edit.setText("https://api.deepseek.com/v1/chat/completions")
            info_text = """DeepSeek配置说明：
• API地址：https://api.deepseek.com/v1/chat/completions
• 需要DeepSeek API Key
• 支持模型：deepseek-chat
• 获取API Key：https://platform.deepseek.com/"""
        elif model_type == "Qwen":
            self.api_url_edit.setText("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
            info_text = """通义千问配置说明：
• API地址：https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
• 需要阿里云API Key
• 支持模型：qwen-plus, qwen-turbo等
• 获取API Key：https://dashscope.console.aliyun.com/"""
        elif model_type == "GLM":
            self.api_url_edit.setText("https://open.bigmodel.cn/api/paas/v4/chat/completions")
            info_text = """智谱AI配置说明：
• API地址：https://open.bigmodel.cn/api/paas/v4/chat/completions
• 需要智谱AI API Key
• 支持模型：glm-4-flash（免费）, glm-4等
• 获取API Key：https://open.bigmodel.cn/
• GLM-4-Flash目前免费使用"""
        else:
            self.api_url_edit.setText("")
            info_text = """自定义模型配置说明：
• 请确保API地址格式正确
• API Key格式通常为：sk-xxxxxxxx
• 确保模型支持OpenAI兼容的API格式"""
        
        self.preset_info.setText(info_text)
    
    def on_config_changed(self):
        """配置改变事件"""
        # 检查是否有未保存的更改
        if self.current_model:
            name_changed = self.model_name_edit.text().strip() != self.current_model.get("name", "")
            url_changed = self.api_url_edit.text().strip() != self.current_model.get("url", "")
            key_changed = self.api_key_edit.text().strip() != self.current_model.get("key", "")
            type_changed = self.api_type_combo.currentText() != self.current_model.get("type", "")
            
            has_changes = name_changed or url_changed or key_changed or type_changed
            self.save_config_btn.setEnabled(has_changes and self.is_config_valid())
    
    def is_config_valid(self):
        """检查配置是否有效"""
        name = self.model_name_edit.text().strip()
        url = self.api_url_edit.text().strip()
        key = self.api_key_edit.text().strip()
        
        return bool(name and url and key)
    
    def toggle_key_visibility(self, checked):
        """切换API Key显示/隐藏"""
        if checked:
            self.api_key_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.api_key_edit.setEchoMode(QLineEdit.Password)
    
    def add_new_model(self):
        """添加新模型"""
        # 创建新模型配置
        new_model = {
            "name": "新模型",
            "type": "tongyi",
            "url": "",
            "key": ""
        }
        
        # 添加到配置
        models = self.config_manager.config.get("models", [])
        models.append(new_model)
        self.config_manager.config["models"] = models
        
        # 重新加载列表
        self.load_models()
        
        # 选中新添加的模型
        self.model_list.setCurrentRow(self.model_list.count() - 1)
        self.on_model_selected(self.model_list.item(self.model_list.count() - 1))
        
        # 聚焦到名称输入框
        self.model_name_edit.selectAll()
        self.model_name_edit.setFocus()
    
    def delete_model(self):
        """删除模型"""
        current_item = self.model_list.currentItem()
        if not current_item:
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
    
    def save_current_config(self):
        """保存当前配置"""
        if not self.current_model:
            return
            
        if not self.is_config_valid():
            QMessageBox.warning(self, "警告", "请填写完整的模型配置信息")
            return
            
        try:
            # 更新当前模型配置
            self.current_model["name"] = self.model_name_edit.text().strip()
            self.current_model["type"] = self.api_type_combo.currentText()
            self.current_model["url"] = self.api_url_edit.text().strip()
            self.current_model["key"] = self.api_key_edit.text().strip()
            
            # 保存到文件
            self.save_config_to_file()
            
            # 更新列表显示
            current_item = self.model_list.currentItem()
            if current_item:
                current_item.setText(self.current_model["name"])
                current_item.setData(Qt.UserRole, self.current_model)
            
            # 发送更新信号
            self.models_updated.emit()
            
            # 禁用保存按钮
            self.save_config_btn.setEnabled(False)
            
            QMessageBox.information(self, "成功", "模型配置已保存")
            
        except Exception as e:
            logger.error(f"保存模型配置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
    
    def save_config_to_file(self):
        """保存配置到文件"""
        config_file = os.path.join(self.config_manager.config_dir, 'llm_config.json')
        os.makedirs(self.config_manager.config_dir, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config_manager.config, f, indent=4, ensure_ascii=False)
    
    def test_connection(self):
        """测试连接"""
        if not self.is_config_valid():
            QMessageBox.warning(self, "警告", "请先填写完整的配置信息")
            return
            
        # 获取配置信息
        model_name = self.model_name_edit.text().strip()
        model_type = self.api_type_combo.currentText()
        model_url = self.api_url_edit.text().strip()
        model_key = self.api_key_edit.text().strip()
        
        # 创建进度对话框
        progress_dialog = QProgressDialog("正在测试连接...", "取消", 0, 0, self)
        progress_dialog.setWindowTitle("连接测试")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        try:
            # 导入必要的模块
            import requests
            import json
            
            # 设置请求头和数据
            headers = {
                "Authorization": f"Bearer {model_key}",
                "Content-Type": "application/json"
            }
            
            # 构建测试请求 - 如果URL已经包含endpoint则直接使用，否则添加
            if model_url.endswith('/chat/completions'):
                full_url = model_url
            else:
                endpoint = "/chat/completions"
                full_url = f"{model_url.rstrip('/')}{endpoint}"
            
            # 根据模型类型设置测试模型名称
            if model_type == "zhipu":
                test_model_name = "glm-4-flash"  # 智谱AI的免费模型
            elif model_type == "deepseek":
                test_model_name = "deepseek-chat"  # DeepSeek的主要模型
            elif model_type == "tongyi":
                test_model_name = "qwen-plus"  # 通义千问的标准模型
            else:
                test_model_name = model_name if model_name else "gpt-3.5-turbo"
            
            payload = {
                "model": test_model_name,
                "messages": [
                    {"role": "user", "content": "你好，这是一个连接测试。请简单回复'连接成功'。"}
                ],
                "max_tokens": 50
            }
            
            # 发送测试请求
            response = requests.post(
                full_url, 
                json=payload, 
                headers=headers, 
                timeout=30
            )
            
            progress_dialog.close()
            
            # 检查响应
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        content = response_data["choices"][0].get("message", {}).get("content", "")
                        QMessageBox.information(
                            self, "连接测试成功", 
                            f"✅ 连接测试成功！\n\n"
                            f"模型名称：{test_model_name}\n"
                            f"模型类型：{model_type}\n"
                            f"API地址：{model_url}\n\n"
                            f"测试响应：{content[:100]}{'...' if len(content) > 100 else ''}"
                        )
                        return
                    else:
                        QMessageBox.warning(
                            self, "连接测试失败", 
                            f"❌ API响应格式异常\n\n"
                            f"状态码：{response.status_code}\n"
                            f"响应内容：{response.text[:200]}{'...' if len(response.text) > 200 else ''}"
                        )
                except json.JSONDecodeError:
                    QMessageBox.warning(
                        self, "连接测试失败", 
                        f"❌ API响应不是有效的JSON格式\n\n"
                        f"状态码：{response.status_code}\n"
                        f"响应内容：{response.text[:200]}{'...' if len(response.text) > 200 else ''}"
                    )
            elif response.status_code == 401:
                QMessageBox.critical(
                    self, "连接测试失败", 
                    f"❌ API密钥验证失败\n\n"
                    f"请检查API Key是否正确。\n"
                    f"状态码：{response.status_code}\n"
                    f"错误信息：{response.text[:200]}{'...' if len(response.text) > 200 else ''}"
                )
            elif response.status_code == 404:
                QMessageBox.critical(
                    self, "连接测试失败", 
                    f"❌ API地址无效\n\n"
                    f"请检查API地址是否正确。\n"
                    f"当前地址：{full_url}\n"
                    f"状态码：{response.status_code}"
                )
            else:
                QMessageBox.critical(
                    self, "连接测试失败", 
                    f"❌ API调用失败\n\n"
                    f"状态码：{response.status_code}\n"
                    f"错误信息：{response.text[:200]}{'...' if len(response.text) > 200 else ''}"
                )
                
        except requests.exceptions.Timeout:
            progress_dialog.close()
            QMessageBox.critical(
                self, "连接测试失败", 
                "❌ 请求超时\n\n"
                "请检查网络连接和API地址是否正确。"
            )
        except requests.exceptions.ConnectionError:
            progress_dialog.close()
            QMessageBox.critical(
                self, "连接测试失败", 
                "❌ 网络连接错误\n\n"
                "请检查网络连接和API地址是否正确。"
            )
        except Exception as e:
            progress_dialog.close()
            logger.error(f"测试连接失败: {e}")
            QMessageBox.critical(
                self, "连接测试失败", 
                f"❌ 测试过程中发生错误\n\n"
                f"错误详情：{str(e)}"
            )