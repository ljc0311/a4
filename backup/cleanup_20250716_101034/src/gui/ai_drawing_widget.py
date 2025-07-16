#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI绘图组件
重构后的AI绘图界面，采用清晰的分组布局
"""

import sys
import os
import json
import shutil
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QGridLayout, QMessageBox, QSizePolicy, QSpinBox, QComboBox, 
    QCheckBox, QGroupBox, QFormLayout, QDoubleSpinBox, QTextEdit, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont

from src.utils.logger import logger
from src.models.comfyui_client import ComfyUIClient
from src.gui.workflow_panel import WorkflowPanel


class AIDrawingWidget(QWidget):
    """AI绘图组件 - 重构后的清晰界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # 初始化组件
        self.comfyui_client = None
        self.generated_images = []  # 存储图片路径和相关信息
        self.selected_image_index = -1  # 当前选中的图片索引
        
        # 设置工作流目录
        self.workflows_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'config', 'workflows'
        )
        
        self.init_ui()
        
        # 初始化图像生成服务
        self.image_generation_service = None
        self._init_image_generation_service()
        
    def init_ui(self):
        """初始化UI界面"""
        main_layout = QVBoxLayout()
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel("🎨 AI图像生成")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)
        
        # 创建子标签页用于不同的引擎配置
        self.engine_tabs = QTabWidget()
        
        # Pollinations AI 标签页
        self.pollinations_tab = self.create_pollinations_tab()
        self.engine_tabs.addTab(self.pollinations_tab, "🌟 Pollinations AI (免费)")
        
        # ComfyUI 标签页
        self.comfyui_tab = self.create_comfyui_tab()
        self.engine_tabs.addTab(self.comfyui_tab, "🔧 ComfyUI (本地)")
        
        # API引擎标签页
        self.api_engines_tab = self.create_api_engines_tab()
        self.engine_tabs.addTab(self.api_engines_tab, "☁️ 云端API")
        
        main_layout.addWidget(self.engine_tabs)
        
        # 图片生成区域
        generation_group = QGroupBox("图片生成")
        generation_layout = QVBoxLayout(generation_group)
        
        # 提示词输入
        prompt_layout = QHBoxLayout()
        prompt_layout.addWidget(QLabel("图片描述:"))
        self.image_desc_input = QLineEdit()
        self.image_desc_input.setPlaceholderText("请输入图片描述（prompt）")
        prompt_layout.addWidget(self.image_desc_input)
        
        self.generate_image_btn = QPushButton("生成图片")
        self.generate_image_btn.clicked.connect(self.handle_generate_image_btn)
        prompt_layout.addWidget(self.generate_image_btn)
        generation_layout.addLayout(prompt_layout)
        
        # 状态显示
        self.generated_image_status_label = QLabel("准备就绪")
        generation_layout.addWidget(self.generated_image_status_label)
        
        main_layout.addWidget(generation_group)
        
        # 图片库区域
        gallery_group = QGroupBox("图片库")
        gallery_layout = QVBoxLayout(gallery_group)
        
        # 图片显示区域
        self.image_gallery_scroll = QScrollArea()
        self.image_gallery_widget = QWidget()
        self.image_gallery_layout = QGridLayout(self.image_gallery_widget)
        self.image_gallery_layout.setSpacing(10)
        self.image_gallery_scroll.setWidget(self.image_gallery_widget)
        self.image_gallery_scroll.setWidgetResizable(True)
        self.image_gallery_scroll.setMinimumHeight(300)
        gallery_layout.addWidget(self.image_gallery_scroll)
        
        # 图片库操作按钮
        gallery_btn_layout = QHBoxLayout()
        clear_gallery_btn = QPushButton("清空图片库")
        clear_gallery_btn.clicked.connect(self.clear_image_gallery)
        gallery_btn_layout.addWidget(clear_gallery_btn)
        gallery_btn_layout.addStretch()
        gallery_layout.addLayout(gallery_btn_layout)
        
        main_layout.addWidget(gallery_group)
        
        self.setLayout(main_layout)
        
    def create_pollinations_tab(self):
        """创建Pollinations AI配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 说明文本
        info_label = QLabel(
            "🌟 <b>Pollinations AI</b><br>"
            "免费的AI图像生成服务，无需API密钥，支持多种模型。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 参数设置 - 采用左右分栏布局
        params_main_layout = QHBoxLayout()

        # 左侧：基础参数
        basic_group = QGroupBox("基础参数")
        basic_layout = QFormLayout(basic_group)

        # 图像尺寸
        self.width_spin = QSpinBox()
        self.width_spin.setRange(256, 2048)
        self.width_spin.setValue(1024)
        self.width_spin.setSingleStep(64)
        self.width_spin.valueChanged.connect(self.on_parameter_changed)
        basic_layout.addRow("宽度:", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(256, 2048)
        self.height_spin.setValue(1024)
        self.height_spin.setSingleStep(64)
        self.height_spin.valueChanged.connect(self.on_parameter_changed)
        basic_layout.addRow("高度:", self.height_spin)

        # 种子设置 - 简化为只有下拉框
        self.seed_combo = QComboBox()
        self.seed_combo.addItems(["随机", "固定"])
        self.seed_combo.currentTextChanged.connect(self.on_parameter_changed)
        basic_layout.addRow("种子值:", self.seed_combo)

        # 右侧：Pollinations特有设置
        pollinations_group = QGroupBox("特有设置")
        pollinations_layout = QFormLayout(pollinations_group)

        # 模型选择
        self.pollinations_model_combo = QComboBox()
        self.pollinations_model_combo.addItems(["flux", "flux-turbo", "gptimage"])
        self.pollinations_model_combo.setCurrentText("flux")
        self.pollinations_model_combo.currentTextChanged.connect(self.on_parameter_changed)
        pollinations_layout.addRow("模型:", self.pollinations_model_combo)

        # 复选框选项
        self.pollinations_enhance_check = QCheckBox("启用增强 (Enhance)")
        self.pollinations_enhance_check.stateChanged.connect(self.on_parameter_changed)
        self.pollinations_logo_check = QCheckBox("添加Logo水印")
        self.pollinations_logo_check.stateChanged.connect(self.on_parameter_changed)
        pollinations_layout.addRow("", self.pollinations_enhance_check)
        pollinations_layout.addRow("", self.pollinations_logo_check)

        # 添加左右两个组到主布局
        params_main_layout.addWidget(basic_group)
        params_main_layout.addWidget(pollinations_group)

        # 创建参数容器并添加到主布局
        params_container = QWidget()
        params_container.setLayout(params_main_layout)
        layout.addWidget(params_container)
        layout.addStretch()
        
        return tab

    def get_seed_value(self):
        """根据种子模式获取种子值"""
        import random
        if self.seed_combo.currentText() == "随机":
            return random.randint(0, 2147483647)
        else:  # 固定
            # 生成一个固定的种子值，基于当前时间戳
            import time
            return int(time.time()) % 2147483647
        
    def create_comfyui_tab(self):
        """创建ComfyUI配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 说明文本
        info_label = QLabel(
            "🔧 <b>ComfyUI (本地)</b><br>"
            "使用本地ComfyUI服务进行图像生成，支持自定义工作流。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 连接设置
        connection_group = QGroupBox("连接设置")
        connection_layout = QVBoxLayout(connection_group)
        
        # ComfyUI地址
        url_layout = QHBoxLayout()
        self.comfyui_url_input = QLineEdit()
        self.comfyui_url_input.setPlaceholderText("请输入 ComfyUI 地址 (例如: http://127.0.0.1:8188)")
        self.comfyui_url_input.setText("http://127.0.0.1:8188")
        url_layout.addWidget(self.comfyui_url_input)
        
        self.connect_comfyui_btn = QPushButton("连接 ComfyUI")
        self.connect_comfyui_btn.clicked.connect(self.connect_to_comfyui)
        url_layout.addWidget(self.connect_comfyui_btn)
        
        connection_layout.addLayout(url_layout)
        layout.addWidget(connection_group)
        
        # 工作流配置
        workflow_group = QGroupBox("工作流配置")
        workflow_layout = QVBoxLayout(workflow_group)
        
        self.workflow_panel = WorkflowPanel()
        workflow_layout.addWidget(self.workflow_panel)
        
        layout.addWidget(workflow_group)
        layout.addStretch()
        
        return tab
        
    def create_api_engines_tab(self):
        """创建API引擎配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 说明文本
        info_label = QLabel(
            "☁️ <b>云端API服务</b><br>"
            "使用各种云端API服务进行图像生成，需要相应的API密钥。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # API配置
        api_group = QGroupBox("API配置")
        api_layout = QFormLayout(api_group)
        
        # OpenAI DALL-E
        self.dalle_api_key_input = QLineEdit()
        self.dalle_api_key_input.setPlaceholderText("输入OpenAI API密钥")
        self.dalle_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("DALL-E API Key:", self.dalle_api_key_input)
        
        # Stability AI
        self.stability_api_key_input = QLineEdit()
        self.stability_api_key_input.setPlaceholderText("输入Stability AI API密钥")
        self.stability_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("Stability API Key:", self.stability_api_key_input)
        
        # Google Imagen
        self.imagen_api_key_input = QLineEdit()
        self.imagen_api_key_input.setPlaceholderText("输入Google Cloud API密钥")
        self.imagen_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("Imagen API Key:", self.imagen_api_key_input)

        # ComfyUI云端
        self.comfyui_cloud_url_input = QLineEdit()
        self.comfyui_cloud_url_input.setPlaceholderText("输入ComfyUI云端服务地址")
        api_layout.addRow("ComfyUI云端地址:", self.comfyui_cloud_url_input)

        # CogView-3 Flash 配置说明
        cogview_info_label = QLabel("CogView-3 Flash: 自动使用智谱AI密钥")
        cogview_info_label.setStyleSheet("color: #666; font-style: italic;")
        api_layout.addRow("CogView-3 Flash:", cogview_info_label)

        # Vheer.com 配置说明
        vheer_info_label = QLabel("Vheer.com: 免费在线AI图像生成服务 (无需API密钥)")
        vheer_info_label.setStyleSheet("color: #2E8B57; font-weight: bold;")
        api_layout.addRow("Vheer.com:", vheer_info_label)

        layout.addWidget(api_group)

        # 引擎选择
        engine_group = QGroupBox("选择生成引擎")
        engine_layout = QFormLayout(engine_group)

        self.api_engine_combo = QComboBox()
        self.api_engine_combo.addItems([
            "DALL-E (OpenAI)",
            "Stability AI",
            "Google Imagen",
            "ComfyUI云端",
            "CogView-3 Flash",
            "Vheer.com (免费)"
        ])
        self.api_engine_combo.setCurrentText("Vheer.com (免费)")
        engine_layout.addRow("当前引擎:", self.api_engine_combo)

        layout.addWidget(engine_group)
        layout.addStretch()

        return tab

    def handle_generate_image_btn(self):
        """处理生成图片按钮点击"""
        try:
            # 检查图片描述
            prompt = self.image_desc_input.text().strip()
            if not prompt:
                QMessageBox.warning(self, "警告", "请输入图片描述")
                return

            # 获取当前选择的引擎标签页
            current_tab_index = self.engine_tabs.currentIndex()

            if current_tab_index == 0:  # Pollinations AI
                self._generate_with_pollinations(prompt)
            elif current_tab_index == 1:  # ComfyUI
                self._generate_with_comfyui(prompt)
            elif current_tab_index == 2:  # API引擎
                self._generate_with_api_engines(prompt)
            else:
                QMessageBox.warning(self, "错误", "未知的生成引擎")

        except Exception as e:
            logger.error(f"图片生成过程中发生错误: {e}")
            QMessageBox.critical(self, "错误", f"图片生成失败: {str(e)}")
            self._reset_ui_state()

    def _generate_with_pollinations(self, prompt):
        """使用 Pollinations AI 生成图片"""
        logger.info("使用 Pollinations AI 生成图片")

        # 初始化图像生成服务
        if not hasattr(self, 'image_generation_service') or not self.image_generation_service:
            self._init_image_generation_service()

        if not self.image_generation_service:
            QMessageBox.warning(self, "服务不可用", "图像生成服务初始化失败")
            return

        # 获取用户配置
        config = {
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
            'model': self.pollinations_model_combo.currentText(),
            'enhance': self.pollinations_enhance_check.isChecked(),
            'nologo': not self.pollinations_logo_check.isChecked(),
            'safe': True
        }

        # 处理种子设置
        config['seed'] = self.get_seed_value()

        logger.info(f"Pollinations配置: {config}")

        # 更新UI状态
        self.generate_image_btn.setEnabled(False)
        self.generate_image_btn.setText("生成中...")
        self.generated_image_status_label.setText("正在使用 Pollinations AI 生成图片...")

        # 在新线程中生成图片
        from src.gui.image_generation_thread import ImageGenerationThread

        # 获取项目管理器和当前项目名称
        project_manager = getattr(self.parent_window, 'project_manager', None)
        current_project_name = getattr(self.parent_window, 'current_project_name', None)

        self.image_generation_thread = ImageGenerationThread(
            image_generation_service=self.image_generation_service,
            prompt=prompt,
            config=config,
            engine_preference='pollinations',
            project_manager=project_manager,
            current_project_name=current_project_name
        )
        self.image_generation_thread.image_generated.connect(self.on_image_generated)
        self.image_generation_thread.error_occurred.connect(self.on_image_generation_error)
        self.image_generation_thread.start()

    def _generate_with_comfyui(self, prompt):
        """使用 ComfyUI 生成图片"""
        logger.info("使用 ComfyUI 生成图片")

        # 检查ComfyUI连接
        if not self.comfyui_client:
            QMessageBox.warning(self, "警告", "请先连接到ComfyUI")
            return

        # 检查工作流选择
        workflow_name = self.workflow_panel.get_current_workflow_name()
        if not workflow_name or workflow_name == "请选择工作流":
            QMessageBox.warning(self, "警告", "请选择一个工作流")
            return

        # 获取工作流参数
        try:
            workflow_params = self.workflow_panel.get_current_workflow_parameters()
        except Exception as e:
            logger.error(f"获取工作流参数失败: {e}")
            QMessageBox.warning(self, "错误", f"获取工作流参数失败: {str(e)}")
            return

        # 更新UI状态
        self.generate_image_btn.setEnabled(False)
        self.generate_image_btn.setText("生成中...")
        self.generated_image_status_label.setText("正在使用 ComfyUI 生成图片...")

        # 调用ComfyUI生成图片
        try:
            # 获取项目管理器和当前项目名称
            project_manager = getattr(self.parent_window, 'project_manager', None)
            current_project_name = getattr(self.parent_window, 'current_project_name', None)

            image_paths = self.comfyui_client.generate_image_with_workflow(
                prompt, workflow_name, workflow_params, project_manager, current_project_name
            )

            # 处理生成结果
            if image_paths and not image_paths[0].startswith("ERROR:"):
                self.add_images_to_gallery(image_paths)
                self.generated_image_status_label.setText(f"✅ 成功生成 {len(image_paths)} 张图片")
            else:
                error_message = image_paths[0] if image_paths else "未知错误"
                self.generated_image_status_label.setText(f"❌ 图片生成失败: {error_message}")
                QMessageBox.warning(self, "生成失败", f"图片生成失败: {error_message}")

        except Exception as e:
            logger.error(f"图片生成过程中发生错误: {e}")
            self.generated_image_status_label.setText("❌ 生成错误")
            QMessageBox.critical(self, "错误", f"图片生成过程中发生错误: {str(e)}")
        finally:
            self.generate_image_btn.setEnabled(True)
            self.generate_image_btn.setText("生成图片")

    def _generate_with_api_engines(self, prompt):
        """使用API引擎生成图片"""
        try:
            # 获取选择的引擎
            selected_engine = self.api_engine_combo.currentText()
            logger.info(f"使用API引擎生成图片: {selected_engine}")

            # 更新UI状态
            self.generate_image_btn.setText("生成中...")
            self.generate_image_btn.setEnabled(False)
            self.generated_image_status_label.setText("🔄 正在生成图片...")

            if "Vheer.com" in selected_engine:
                self._generate_with_vheer(prompt)
            elif "DALL-E" in selected_engine:
                self._generate_with_dalle(prompt)
            elif "Stability" in selected_engine:
                self._generate_with_stability(prompt)
            elif "Imagen" in selected_engine:
                self._generate_with_imagen(prompt)
            elif "CogView" in selected_engine:
                self._generate_with_cogview(prompt)
            elif "ComfyUI云端" in selected_engine:
                self._generate_with_comfyui_cloud(prompt)
            else:
                QMessageBox.warning(self, "错误", f"不支持的引擎: {selected_engine}")
                self._reset_ui_state()

        except Exception as e:
            logger.error(f"API引擎生成失败: {e}")
            QMessageBox.critical(self, "错误", f"API引擎生成失败: {str(e)}")
            self._reset_ui_state()

    def _generate_with_vheer(self, prompt):
        """使用Vheer.com生成图片"""
        try:
            logger.info("开始使用Vheer.com生成图片")

            # 使用图像生成服务
            if not self.image_generation_service:
                self._init_image_generation_service()

            # 创建生成配置
            from src.models.image_engine_base import GenerationConfig
            config = GenerationConfig(
                prompt=prompt,
                width=1024,
                height=1024,
                batch_size=1,
                workflow_id=f'vheer_gui_{int(time.time())}'
            )

            # 异步生成图像
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(
                    self.image_generation_service.generate_image(
                        prompt=prompt,
                        config=config.__dict__,
                        engine_preference='vheer'
                    )
                )

                if result.success and result.image_paths:
                    self.add_images_to_gallery(result.image_paths)
                    self.generated_image_status_label.setText(f"✅ Vheer成功生成 {len(result.image_paths)} 张图片")
                    logger.info(f"Vheer生成成功: {result.image_paths}")
                else:
                    error_msg = result.error_message or "未知错误"
                    self.generated_image_status_label.setText(f"❌ Vheer生成失败: {error_msg}")
                    QMessageBox.warning(self, "生成失败", f"Vheer生成失败: {error_msg}")

            finally:
                loop.close()
                self._reset_ui_state()

        except Exception as e:
            logger.error(f"Vheer生成过程中发生错误: {e}")
            self.generated_image_status_label.setText(f"❌ Vheer生成失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"Vheer生成失败: {str(e)}")
            self._reset_ui_state()

    def _generate_with_dalle(self, prompt):
        """使用DALL-E生成图片"""
        QMessageBox.information(self, "提示", "DALL-E功能正在开发中，敬请期待！")
        self._reset_ui_state()

    def _generate_with_stability(self, prompt):
        """使用Stability AI生成图片"""
        QMessageBox.information(self, "提示", "Stability AI功能正在开发中，敬请期待！")
        self._reset_ui_state()

    def _generate_with_imagen(self, prompt):
        """使用Google Imagen生成图片"""
        QMessageBox.information(self, "提示", "Google Imagen功能正在开发中，敬请期待！")
        self._reset_ui_state()

    def _generate_with_cogview(self, prompt):
        """使用CogView-3 Flash生成图片"""
        QMessageBox.information(self, "提示", "CogView-3 Flash功能正在开发中，敬请期待！")
        self._reset_ui_state()

    def _generate_with_comfyui_cloud(self, prompt):
        """使用ComfyUI云端生成图片"""
        QMessageBox.information(self, "提示", "ComfyUI云端功能正在开发中，敬请期待！")
        self._reset_ui_state()

    def connect_to_comfyui(self):
        """连接到ComfyUI"""
        try:
            comfyui_url = self.comfyui_url_input.text().strip()
            if not comfyui_url:
                QMessageBox.warning(self, "警告", "请输入ComfyUI地址")
                return

            # 验证URL格式
            if not (comfyui_url.startswith('http://') or comfyui_url.startswith('https://')):
                QMessageBox.warning(self, "警告", "请输入有效的URL地址（以http://或https://开头）")
                return

            self.connect_comfyui_btn.setEnabled(False)
            self.connect_comfyui_btn.setText("连接中...")

            # 初始化ComfyUI客户端
            self.comfyui_client = ComfyUIClient(comfyui_url)

            # 尝试获取工作流列表来测试连接
            try:
                self.comfyui_client.get_workflow_list()

                # 初始化工作流面板
                self.workflow_panel.set_workflows_directory(self.workflows_dir)
                self.workflow_panel.refresh_workflows()

                QMessageBox.information(self, "成功", "ComfyUI连接成功")
                logger.info(f"成功连接到ComfyUI: {comfyui_url}")
            except Exception as e:
                logger.error(f"连接ComfyUI时发生错误: {e}")
                self.comfyui_client = None
                QMessageBox.warning(self, "连接失败", "无法连接到ComfyUI，请检查地址和服务状态")
        finally:
            self.connect_comfyui_btn.setEnabled(True)
            self.connect_comfyui_btn.setText("连接 ComfyUI")

    def add_images_to_gallery(self, image_paths):
        """将图片添加到图片库"""
        try:
            for image_path in image_paths:
                # 构建完整的图片路径
                full_image_path = image_path

                if os.path.exists(full_image_path):
                    # 自动复制图片到当前项目文件夹
                    project_image_path = None
                    if hasattr(self.parent_window, 'current_project_name') and getattr(self.parent_window, 'current_project_name', None):
                        project_image_path = self._copy_image_to_project(full_image_path)

                    # 创建图片标签
                    image_label = QLabel()
                    pixmap = QPixmap(full_image_path)
                    if not pixmap.isNull():
                        # 缩放图片到合适大小
                        scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        image_label.setPixmap(scaled_pixmap)
                        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                        # 添加到网格布局
                        row = len(self.generated_images) // 3
                        col = len(self.generated_images) % 3
                        self.image_gallery_layout.addWidget(image_label, row, col)

                        # 保存图片信息
                        final_image_path = project_image_path if project_image_path else full_image_path
                        self.generated_images.append({
                            'path': final_image_path,
                            'label': image_label,
                            'prompt': self.image_desc_input.text()
                        })

                        logger.info(f"添加图片到图片库: {full_image_path}")
                    else:
                        logger.warning(f"无法加载图片: {full_image_path}")
                else:
                    logger.warning(f"图片文件不存在: {full_image_path}")

        except Exception as e:
            logger.error(f"添加图片到图片库时发生错误: {e}")

    def _copy_image_to_project(self, source_image_path):
        """将图片复制到当前项目的images文件夹中"""
        try:
            # 获取当前项目名称
            if not hasattr(self.parent_window, 'current_project_name') or not getattr(self.parent_window, 'current_project_name', None):
                return None

            current_project_name = getattr(self.parent_window, 'current_project_name', None)

            # 获取项目管理器
            if not hasattr(self.parent_window, 'project_manager'):
                return None

            project_manager = getattr(self.parent_window, 'project_manager', None)
            if not project_manager:
                return None
            project_root = project_manager.get_project_path(current_project_name)

            # 根据图片来源确定保存目录
            if 'pollinations' in source_image_path.lower():
                project_images_dir = os.path.join(project_root, 'images', 'pollinations')
            else:
                project_images_dir = os.path.join(project_root, 'images', 'comfyui')

            # 确保目标目录存在
            os.makedirs(project_images_dir, exist_ok=True)

            # 生成新的文件名（避免重复）
            # 使用简洁的文件名，不包含时间戳
            original_filename = os.path.basename(source_image_path)
            name, ext = os.path.splitext(original_filename)
            new_filename = f"{name}{ext}"

            # 目标路径
            target_path = os.path.join(project_images_dir, new_filename)

            # 复制文件
            shutil.copy2(source_image_path, target_path)

            logger.info(f"图片已复制到项目文件夹: {source_image_path} -> {target_path}")
            return target_path

        except Exception as e:
            logger.error(f"复制图片到项目文件夹时发生错误: {e}")
            return None

    def clear_image_gallery(self):
        """清空图片库"""
        try:
            # 清除所有图片标签
            while self.image_gallery_layout.count():
                child = self.image_gallery_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # 清空图片列表
            self.generated_images.clear()
            self.selected_image_index = -1

            self.generated_image_status_label.setText("图片库已清空")
            logger.info("图片库已清空")

        except Exception as e:
            logger.error(f"清空图片库时发生错误: {e}")

    def on_parameter_changed(self):
        """参数改变时同步到分镜图像生成界面"""
        try:
            self.sync_to_storyboard_tab()
        except Exception as e:
            logger.error(f"参数同步失败: {e}")

    def sync_to_storyboard_tab(self):
        """同步参数到分镜图像生成界面"""
        try:
            # 查找分镜图像生成标签页
            storyboard_tab = self.find_storyboard_image_generation_tab()
            if not storyboard_tab:
                return

            # 同步Pollinations参数
            if hasattr(storyboard_tab, 'width_spin'):
                storyboard_tab.width_spin.setValue(self.width_spin.value())
            if hasattr(storyboard_tab, 'height_spin'):
                storyboard_tab.height_spin.setValue(self.height_spin.value())
            if hasattr(storyboard_tab, 'seed_combo'):
                storyboard_tab.seed_combo.setCurrentText(self.seed_combo.currentText())
            if hasattr(storyboard_tab, 'pollinations_model_combo'):
                storyboard_tab.pollinations_model_combo.setCurrentText(self.pollinations_model_combo.currentText())
            if hasattr(storyboard_tab, 'pollinations_enhance_check'):
                storyboard_tab.pollinations_enhance_check.setChecked(self.pollinations_enhance_check.isChecked())
            if hasattr(storyboard_tab, 'pollinations_logo_check'):
                storyboard_tab.pollinations_logo_check.setChecked(self.pollinations_logo_check.isChecked())

            # 同步ComfyUI参数
            if hasattr(storyboard_tab, 'comfyui_url_input') and hasattr(self, 'comfyui_url_input'):
                # 这里可以添加ComfyUI参数同步逻辑
                pass

            logger.info("参数已同步到分镜图像生成界面")

        except Exception as e:
            logger.error(f"同步参数到分镜图像生成界面失败: {e}")

    def find_storyboard_image_generation_tab(self):
        """查找分镜图像生成标签页"""
        try:
            # 向上查找主窗口
            widget = self
            while widget.parent():
                widget = widget.parent()
                if hasattr(widget, 'tab_widget'):
                    main_window = widget
                    break
            else:
                return None

            # 查找分镜图像生成标签页
            tab_widget = getattr(main_window, 'tab_widget', None)
            if not tab_widget:
                return None
            for i in range(tab_widget.count()):
                tab_text = tab_widget.tabText(i)
                if "分镜图像生成" in tab_text or "图像生成" in tab_text:
                    return tab_widget.widget(i)
            return None

        except Exception as e:
            logger.error(f"查找分镜图像生成标签页失败: {e}")
            return None

    def _init_image_generation_service(self):
        """初始化图像生成服务"""
        try:
            import asyncio
            from src.models.image_generation_service import ImageGenerationService
            self.image_generation_service = ImageGenerationService()
            # 异步初始化
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.image_generation_service.initialize())
            logger.info("图像生成服务初始化成功")
        except Exception as e:
            logger.error(f"图像生成服务初始化失败: {e}")
            self.image_generation_service = None

    def on_image_generated(self, image_paths):
        """图片生成成功的回调"""
        try:
            self._reset_ui_state()

            # 确保image_paths是列表格式
            if isinstance(image_paths, str):
                image_paths = [image_paths]

            # 添加到图片库
            self.add_images_to_gallery(image_paths)

            # 更新状态
            self.generated_image_status_label.setText("✅ 图片生成成功")
            logger.info(f"图片生成成功: {image_paths}")

        except Exception as e:
            logger.error(f"处理生成的图片失败: {e}")
            self.generated_image_status_label.setText(f"❌ 处理图片失败: {e}")

    def on_image_generation_error(self, error_message):
        """图片生成失败的回调"""
        self._reset_ui_state()
        self.generated_image_status_label.setText(f"❌ 图片生成失败: {error_message}")
        logger.error(f"图片生成失败: {error_message}")

    def _reset_ui_state(self):
        """重置UI状态"""
        self.generate_image_btn.setEnabled(True)
        self.generate_image_btn.setText("生成图片")
