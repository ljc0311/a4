import sys
import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QFormLayout, QGroupBox, QMessageBox, QTabWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from src.utils.logger import logger
from src.utils.config_manager import ConfigManager
from src.gui.log_dialog import LogDialog
from src.gui.model_manager_dialog import ModelManagerDialog


class SettingsTab(QWidget):
    """设置标签页 - 包含服务配置和AI绘图两个子标签页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        # 初始化配置管理器
        self.config_manager = ConfigManager()

        # 默认ComfyUI输出目录
        self.comfyui_output_dir = ""

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """初始化UI界面"""
        main_layout = QVBoxLayout()

        # 创建子标签页
        self.tab_widget = QTabWidget()

        # 服务配置标签页
        self.service_config_tab = self.create_service_config_tab()
        self.tab_widget.addTab(self.service_config_tab, "🔧 服务配置")

        # AI绘图标签页
        self.ai_drawing_tab = self.create_ai_drawing_tab()
        self.tab_widget.addTab(self.ai_drawing_tab, "🎨 AI绘图")

        # AI配音标签页
        self.ai_voice_tab = self.create_ai_voice_tab()
        self.tab_widget.addTab(self.ai_voice_tab, "🎵 AI配音")

        # 视频生成标签页
        self.video_generation_tab = self.create_video_generation_tab()
        self.tab_widget.addTab(self.video_generation_tab, "🎬 视频生成")

        # 显示设置标签页
        self.display_settings_tab = self.create_display_settings_tab()
        self.tab_widget.addTab(self.display_settings_tab, "🖥️ 显示设置")

        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

    def create_service_config_tab(self):
        """创建服务配置标签页"""
        tab = QWidget()
        settings_layout = QVBoxLayout(tab)

        # 大模型配置区域
        llm_group = QGroupBox("大模型配置")
        llm_group.setObjectName("settings-group")
        llm_layout = QVBoxLayout(llm_group)

        # 标题
        models_label = QLabel("当前已配置模型")
        models_label.setObjectName("settings-title")

        # 当前已配置模型显示
        self.models_display = QLabel("正在加载模型配置...")
        self.models_display.setWordWrap(True)
        self.models_display.setObjectName("models-display")
        self.models_display.setMinimumHeight(100)

        # 按钮布局
        button_layout = QHBoxLayout()
        self.manage_models_btn = QPushButton("管理模型")
        self.manage_models_btn.setObjectName("primary-button")
        self.manage_models_btn.clicked.connect(self.open_model_manager)
        self.manage_models_btn.setToolTip("打开模型管理界面，可添加、编辑、删除多个大模型")
        self.refresh_models_btn = QPushButton("刷新显示")
        self.refresh_models_btn.setObjectName("secondary-button")
        self.refresh_models_btn.clicked.connect(self.refresh_models_display)
        self.refresh_models_btn.setToolTip("刷新模型显示")

        button_layout.addWidget(self.manage_models_btn)
        button_layout.addWidget(self.refresh_models_btn)
        button_layout.addStretch()

        llm_layout.addWidget(models_label)
        llm_layout.addWidget(self.models_display)
        llm_layout.addLayout(button_layout)
        llm_layout.setSpacing(12)

        settings_layout.addWidget(llm_group)

        # General Settings
        general_settings_group = QGroupBox("通用设置")
        general_form = QFormLayout()

        self.comfyui_output_dir_input = QLineEdit(self.comfyui_output_dir)
        self.comfyui_output_dir_input.setPlaceholderText("例如: D:\\ComfyUI\\output 或 /path/to/ComfyUI/output")
        self.comfyui_output_dir_input.setToolTip("请输入 ComfyUI 的 output 文件夹的绝对路径")
        general_form.addRow("ComfyUI 输出目录:", self.comfyui_output_dir_input)

        self.save_general_settings_btn = QPushButton("保存通用设置")
        self.save_general_settings_btn.clicked.connect(self.save_general_settings)
        self.save_general_settings_btn.setToolTip("保存通用应用设置")
        general_form.addRow(self.save_general_settings_btn)

        general_settings_group.setLayout(general_form)
        settings_layout.addWidget(general_settings_group)

        # 系统日志按钮
        self.log_btn = QPushButton("查看系统日志")
        self.log_btn.clicked.connect(self.show_log_dialog)
        self.log_btn.setToolTip("查看系统日志")
        settings_layout.addWidget(self.log_btn)

        settings_layout.addStretch()
        return tab

    def create_ai_drawing_tab(self):
        """创建AI绘图标签页"""
        from src.gui.ai_drawing_widget import AIDrawingWidget
        return AIDrawingWidget(self.parent_window)

    def create_ai_voice_tab(self):
        """创建AI配音标签页"""
        from src.gui.ai_voice_settings_widget import AIVoiceSettingsWidget
        return AIVoiceSettingsWidget(self.parent_window)

    def create_video_generation_tab(self):
        """创建视频生成标签页"""
        from src.gui.video_generation_settings_widget import VideoGenerationSettingsWidget
        return VideoGenerationSettingsWidget(self.parent_window)
        
    def load_settings(self):
        """加载设置"""
        try:
            # 刷新模型显示
            self.refresh_models_display()
            
            # 加载应用设置
            app_config = self.config_manager.config.get('app_settings', {})
            if app_config:
                self.comfyui_output_dir = app_config.get('comfyui_output_dir', '')
                self.comfyui_output_dir_input.setText(self.comfyui_output_dir)
                
        except Exception as e:
            logger.error(f"加载设置时发生错误: {e}")
    
    def refresh_models_display(self):
        """刷新模型显示"""
        try:
            models = self.config_manager.config.get("models", [])
            if models:
                model_info_list = []
                for i, model in enumerate(models, 1):
                    name = model.get("name", "未知模型")
                    model_type = model.get("type", "未知类型")
                    url = model.get("url", "")
                    key = model.get("key", "")
                    
                    # 隐藏API密钥，只显示前几位和后几位
                    if key:
                        if len(key) > 10:
                            masked_key = key[:6] + "***" + key[-4:]
                        else:
                            masked_key = "***"
                    else:
                        masked_key = "未配置"
                    
                    model_info = f"{i}. {name} ({model_type})\n   API地址: {url}\n   API密钥: {masked_key}"
                    model_info_list.append(model_info)
                
                display_text = "\n\n".join(model_info_list)
                self.models_display.setText(display_text)
            else:
                self.models_display.setText("暂无已配置的模型\n\n点击'管理模型'按钮添加新的大模型配置")
        except Exception as e:
            logger.error(f"刷新模型显示失败: {e}")
            self.models_display.setText(f"加载模型信息失败: {e}")
    

    
    def save_general_settings(self):
        """保存通用设置"""
        try:
            comfyui_output_dir = self.comfyui_output_dir_input.text().strip()
            
            # 验证目录路径
            if comfyui_output_dir and not os.path.exists(comfyui_output_dir):
                reply = QMessageBox.question(
                    self, "确认", 
                    f"目录 {comfyui_output_dir} 不存在，是否仍要保存？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            # 构建应用配置
            app_config = {
                'comfyui_output_dir': comfyui_output_dir
            }
            
            # 保存配置
            success = self.config_manager.save_app_settings(app_config)
            
            if success:
                self.comfyui_output_dir = comfyui_output_dir
                QMessageBox.information(self, "成功", "通用设置已保存")
                logger.info("通用设置已保存")
            else:
                QMessageBox.warning(self, "错误", "保存通用设置失败")
                
        except Exception as e:
            logger.error(f"保存通用设置时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def show_log_dialog(self):
        """显示系统日志对话框"""
        try:
            logger.info("用户打开系统日志弹窗")
            dlg = LogDialog(self)
            dlg.exec_()
        except Exception as e:
            logger.error(f"显示日志对话框时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"无法打开日志对话框: {str(e)}")
    
    def get_comfyui_output_dir(self):
        """获取ComfyUI输出目录"""
        return self.comfyui_output_dir

    def create_display_settings_tab(self):
        """创建显示设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # 标题
        title_label = QLabel("🖥️ 显示设置")
        title_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        title_label.setStyleSheet("color: #333; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # 快速字体调整区域
        font_group = QGroupBox("快速字体调整")
        font_layout = QVBoxLayout(font_group)

        # 添加快速字体调整器
        try:
            from src.gui.quick_font_adjuster import QuickFontAdjuster
            self.quick_font_adjuster = QuickFontAdjuster()
            self.quick_font_adjuster.font_size_changed.connect(self.on_font_size_changed)

            # 创建包装器布局
            adjuster_layout = QHBoxLayout()
            adjuster_layout.addWidget(QLabel("字体大小:"))
            adjuster_layout.addWidget(self.quick_font_adjuster)
            adjuster_layout.addStretch()

            font_layout.addLayout(adjuster_layout)

        except Exception as e:
            error_label = QLabel(f"快速字体调整器加载失败: {e}")
            error_label.setStyleSheet("color: red;")
            font_layout.addWidget(error_label)

        layout.addWidget(font_group)

        # 显示信息区域
        info_group = QGroupBox("显示信息")
        info_layout = QFormLayout(info_group)

        try:
            from src.utils.dpi_adapter import get_dpi_adapter
            dpi_adapter = get_dpi_adapter()
            dpi_info = dpi_adapter.get_dpi_info()

            # 显示DPI信息
            self.dpi_label = QLabel(f"{dpi_info['current_dpi']:.0f}")
            info_layout.addRow("当前DPI:", self.dpi_label)

            self.scale_label = QLabel(f"{dpi_info['scale_factor']:.2f}")
            info_layout.addRow("缩放因子:", self.scale_label)

            self.screen_size_label = QLabel(f"{dpi_info['screen_width']}x{dpi_info['screen_height']}")
            info_layout.addRow("屏幕分辨率:", self.screen_size_label)

            self.font_size_label = QLabel(f"{dpi_info['recommended_font_size']}pt")
            info_layout.addRow("推荐字体大小:", self.font_size_label)

        except Exception as e:
            error_label = QLabel(f"显示信息加载失败: {e}")
            error_label.setStyleSheet("color: red;")
            info_layout.addRow("错误:", error_label)

        layout.addWidget(info_group)

        # 操作按钮区域
        button_group = QGroupBox("操作")
        button_layout = QHBoxLayout(button_group)

        # 打开显示设置对话框按钮
        settings_btn = QPushButton("🔧 高级显示设置")
        settings_btn.setToolTip("打开完整的显示设置对话框")
        settings_btn.clicked.connect(self.open_display_settings_dialog)
        button_layout.addWidget(settings_btn)

        # 重置为默认设置按钮
        reset_btn = QPushButton("🔄 重置为默认")
        reset_btn.setToolTip("重置所有显示设置为默认值")
        reset_btn.clicked.connect(self.reset_display_settings)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        layout.addWidget(button_group)

        # 添加弹性空间
        layout.addStretch()

        return tab

    def on_font_size_changed(self, size):
        """字体大小改变处理"""
        try:
            # 更新字体大小标签
            if hasattr(self, 'font_size_label'):
                self.font_size_label.setText(f"{size}pt")

            logger.info(f"字体大小已改变为: {size}pt")

        except Exception as e:
            logger.error(f"处理字体大小改变失败: {e}")

    def open_display_settings_dialog(self):
        """打开显示设置对话框"""
        try:
            from src.gui.display_settings_dialog import DisplaySettingsDialog

            dialog = DisplaySettingsDialog(self)
            dialog.settings_changed.connect(self.on_display_settings_changed)
            dialog.exec_()

        except Exception as e:
            logger.error(f"打开显示设置对话框失败: {e}")
            QMessageBox.warning(self, "错误", f"无法打开显示设置对话框: {e}")

    def reset_display_settings(self):
        """重置显示设置"""
        try:
            from src.utils.display_config import get_display_config
            from src.utils.dpi_adapter import get_dpi_adapter

            # 确认重置
            reply = QMessageBox.question(
                self, "确认重置",
                "确定要重置所有显示设置为默认值吗？\n这将重置字体大小、DPI缩放等设置。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 重置配置
                config = get_display_config()
                config.reset_to_default()
                config.save_config()

                # 重置DPI适配器
                dpi_adapter = get_dpi_adapter()
                default_size = dpi_adapter.get_recommended_font_size()

                # 更新快速字体调整器
                if hasattr(self, 'quick_font_adjuster'):
                    self.quick_font_adjuster.set_font_size(default_size)

                QMessageBox.information(self, "重置完成", "显示设置已重置为默认值")
                logger.info("显示设置已重置为默认值")

        except Exception as e:
            logger.error(f"重置显示设置失败: {e}")
            QMessageBox.warning(self, "错误", f"重置显示设置失败: {e}")

    def on_display_settings_changed(self):
        """显示设置改变处理"""
        try:
            # 刷新显示信息
            if hasattr(self, 'dpi_label'):
                from src.utils.dpi_adapter import get_dpi_adapter
                dpi_adapter = get_dpi_adapter()
                dpi_info = dpi_adapter.get_dpi_info()

                self.dpi_label.setText(f"{dpi_info['current_dpi']:.0f}")
                self.scale_label.setText(f"{dpi_info['scale_factor']:.2f}")
                self.screen_size_label.setText(f"{dpi_info['screen_width']}x{dpi_info['screen_height']}")
                self.font_size_label.setText(f"{dpi_info['recommended_font_size']}pt")

            logger.info("显示设置已更新")

        except Exception as e:
            logger.error(f"处理显示设置改变失败: {e}")
    
    def open_model_manager(self):
        """打开模型管理对话框"""
        try:
            dialog = ModelManagerDialog(self.config_manager, self)
            # 连接模型更新信号
            dialog.models_updated.connect(self.refresh_models_display)
            dialog.exec_()
        except Exception as e:
            logger.error(f"打开模型管理对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"打开模型管理对话框失败: {e}")
    

    
    def get_current_model_config(self):
        """获取当前模型配置（已废弃，现在通过模型管理对话框管理）"""
        # 返回第一个配置的模型，如果有的话
        models = self.config_manager.config.get("models", [])
        if models:
            return models[0]
        return None