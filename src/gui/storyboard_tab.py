import sys
import os
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QPushButton,
    QPlainTextEdit, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QScrollArea, QGridLayout, QFrame, QSpacerItem,
    QSizePolicy, QMessageBox, QDialog, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from .text_processing_threads import TextRewriteThread, ShotsGenerationThread

from src.utils.logger import logger
from src.models.llm_api import LLMApi
from src.models.text_parser import TextParser
from src.utils.config_manager import ConfigManager
from src.gui.shots_window import ShotsWindow
from src.gui.ui_components import ImageDelegate
from src.gui.project_name_dialog import ProjectNameDialog
from src.utils.project_manager import StoryboardProjectManager
from src.models.language_models import LanguageCode
from src.core.language_manager import LanguageManager
from src.gui.language_switch_dialog import LanguageSwitchDialog

# 添加双语文本展示对话框
class BilingualTextDialog(QDialog):
    """双语文本展示对话框"""
    
    def __init__(self, chinese_text: str, english_text: str, title: str = "双语文本对照", parent=None):
        super().__init__(parent)
        self.chinese_text = chinese_text
        self.english_text = english_text
        self.setWindowTitle(title)
        self.resize(800, 600)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建分栏显示
        splitter = QSplitter(Qt.Horizontal)
        
        # 中文内容
        chinese_widget = QWidget()
        chinese_layout = QVBoxLayout()
        chinese_label = QLabel("中文内容")
        chinese_label.setAlignment(Qt.AlignCenter)
        chinese_layout.addWidget(chinese_label)
        self.chinese_text_edit = QTextEdit()
        self.chinese_text_edit.setPlainText(self.chinese_text)
        self.chinese_text_edit.setReadOnly(True)
        chinese_layout.addWidget(self.chinese_text_edit)
        chinese_widget.setLayout(chinese_layout)
        
        # 英文内容
        english_widget = QWidget()
        english_layout = QVBoxLayout()
        english_label = QLabel("English Content")
        english_label.setAlignment(Qt.AlignCenter)
        english_layout.addWidget(english_label)
        self.english_text_edit = QTextEdit()
        self.english_text_edit.setPlainText(self.english_text)
        self.english_text_edit.setReadOnly(True)
        english_layout.addWidget(self.english_text_edit)
        english_widget.setLayout(english_layout)
        
        splitter.addWidget(chinese_widget)
        splitter.addWidget(english_widget)
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)


class StoryboardTab(QWidget):
    """文本转分镜标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # 初始化组件
        self.llm_api = None
        self.text_parser = None
        self.config_manager = ConfigManager()
        self.project_manager = StoryboardProjectManager(self.config_manager.config_dir)
        
        # 初始化语言管理器
        self.language_manager = LanguageManager(self.config_manager)
        
        # 当前项目信息
        self.current_project_name = None
        self.current_project_root = None
        
        # 界面状态管理
        self.current_view_state = "default"  # "default" 或 "shots_list"
        self.is_generating = False  # 是否正在生成分镜
        self.stop_generation = False  # 停止生成标志
        
        # 语言切换状态管理
        self.language_switch_in_progress = False
        self.skip_language_confirmation = False
        
        # 线程相关
        self.rewrite_thread = None
        self.shots_thread = None
        
        # 分镜表格相关组件
        self.shots_table_widget = None
        self.shots_display_widget = None
        self.compact_output_text = None
        self.back_to_edit_btn = None
        self.fullscreen_shots_widget = None
        
        # 双语内容存储
        self.chinese_content = ""
        self.english_content = ""
        
        self.init_ui()
        
        # 注册语言变更回调
        self.language_manager.add_language_change_callback(self.on_language_manager_changed)
        
        # 连接文本变化信号，自动从主窗口同步已改写的文本
        if self.parent_window:
            self.load_rewritten_text_from_main()
    
    def load_models(self):
        """加载大模型列表"""
        try:
            # 使用 ConfigManager 实例获取模型列表
            all_model_configs = self.config_manager.config.get("models", [])
            model_names = [cfg.get("name") for cfg in all_model_configs if cfg.get("name")]
            
            self.model_combo.clear()
            if model_names:
                self.model_combo.addItems(model_names)
                logger.debug(f"加载模型列表成功: {model_names}")
            else:
                self.model_combo.addItem("未配置模型")
                logger.warning("未找到模型配置")
        except Exception as e:
            logger.error(f"加载模型列表失败: {e}")
            self.model_combo.addItem("加载失败")
    
    def get_current_model(self):
        """获取当前选择的模型"""
        if hasattr(self, 'model_combo') and self.model_combo:
            return self.model_combo.currentText()
        return None
    
    def on_model_changed(self, model_name):
        """模型选择变化时的处理"""
        try:
            logger.debug(f"模型选择变化: {model_name}")
            # 重置LLM API对象，强制重新初始化
            self.llm_api = None
            logger.info(f"已重置LLM API，将在下次分镜生成时使用模型: {model_name}")
        except Exception as e:
            logger.error(f"处理模型选择变化时出错: {e}")
    
    def on_language_changed(self, index):
        """语言选择变化时的处理"""
        try:
            if self.language_switch_in_progress:
                return
                
            new_language = self.language_combo.itemData(index)
            current_language = self.language_manager.current_language
            
            # 如果语言没有变化，直接返回
            if new_language == current_language:
                return
                
            logger.debug(f"语言选择变化: {current_language.value} -> {new_language.value}")
            
            # 检查是否需要显示确认对话框
            has_unsaved_content = self._has_unsaved_content()
            
            if not self.skip_language_confirmation and (has_unsaved_content or not self._get_skip_confirmation_setting()):
                # 显示确认对话框
                confirmed, dont_ask_again = LanguageSwitchDialog.show_confirmation(
                    current_language, new_language, has_unsaved_content, self
                )
                
                if not confirmed:
                    # 用户取消，恢复原来的选择
                    self.language_switch_in_progress = True
                    self._set_language_combo_value(current_language)
                    self.language_switch_in_progress = False
                    return
                
                # 保存用户的"不再询问"选择
                if dont_ask_again:
                    self._set_skip_confirmation_setting(True)
            
            # 执行语言切换
            self._perform_language_switch(new_language)
            
        except Exception as e:
            logger.error(f"处理语言选择变化时出错: {e}")
            # 发生错误时恢复原来的选择
            self.language_switch_in_progress = True
            self._set_language_combo_value(self.language_manager.current_language)
            self.language_switch_in_progress = False
    
    def _auto_save_project(self):
        """自动保存项目状态"""
        if self.current_project_name and self.parent_window:
            try:
                # 获取当前项目数据
                project_data = self.parent_window.get_current_project_data()
                
                # 保存项目
                success = self.project_manager.save_project(self.current_project_name, project_data)
                if success:
                    logger.info(f"项目已自动保存: {self.current_project_name}")
                else:
                    logger.error(f"项目自动保存失败: {self.current_project_name}")
            except Exception as e:
                logger.error(f"自动保存项目时发生错误: {e}")
        
    def init_ui(self):
        """初始化UI界面"""
        # 创建主分割器
        storyboard_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：原文输入
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("请输入小说原文或内容文本（支持 Markdown/TXT）："))
        
        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText("此处将自动显示第一个标签页改写后的文本内容，\n您也可以在此输入或编辑自定义文本...")
        self.text_input.setToolTip("显示第一个标签页改写后的文本内容，或输入自定义文本进行分镜生成")
        left_layout.addWidget(self.text_input)

        # --- 创作配置 ---
        config_layout = QVBoxLayout()
        config_layout.setSpacing(10)

        # 第一行：创作风格和AI模型
        row1_layout = QHBoxLayout()
        
        # 创作风格
        row1_layout.addWidget(QLabel("创作风格:"))
        self.style_combo = QComboBox()
        self.style_combo.addItems([
            "电影风格", "动漫风格", "吉卜力风格", "赛博朋克风格", "水彩插画风格", "像素风格", "写实摄影风格"
        ])
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        self.style_combo.setToolTip("选择分镜和生图的风格模板")
        row1_layout.addWidget(self.style_combo)
        
        row1_layout.addSpacing(20)

        # AI模型
        row1_layout.addWidget(QLabel("AI模型:"))
        self.model_combo = QComboBox()
        self.model_combo.setToolTip("选择用于分镜生成的大模型")
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        row1_layout.addWidget(self.model_combo)
        row1_layout.addStretch()
        
        config_layout.addLayout(row1_layout)

        # 第二行：内容语言
        row2_layout = QHBoxLayout()
        
        row2_layout.addWidget(QLabel("内容语言:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("中文", LanguageCode.CHINESE)
        self.language_combo.addItem("English", LanguageCode.ENGLISH)
        self.language_combo.setToolTip("选择内容语言")
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        row2_layout.addWidget(self.language_combo)
        row2_layout.addStretch()

        config_layout.addLayout(row2_layout)
        
        left_layout.addLayout(config_layout)
        
        # 恢复上次选择的风格
        self.restore_style_selection()
        
        # 加载模型列表
        self.load_models()
        
        left_widget.setLayout(left_layout)

        # 右侧：分镜/脚本/生图描述展示
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("分镜/脚本/生图描述（大模型输出）："))
        
        self.output_text = QPlainTextEdit()
        self.output_text.setToolTip("显示大模型输出的分镜/脚本/描述")
        right_layout.addWidget(self.output_text)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        self.generate_shots_btn = QPushButton("生成分镜")
        self.generate_shots_btn.clicked.connect(self.handle_generate_shots_btn)
        self.generate_shots_btn.setToolTip("根据大模型输出生成分镜表")
        button_layout.addWidget(self.generate_shots_btn)
        
        self.stop_generate_btn = QPushButton("停止生成")
        self.stop_generate_btn.clicked.connect(self.handle_stop_generate_btn)
        self.stop_generate_btn.setToolTip("停止当前的分镜生成任务")
        self.stop_generate_btn.setEnabled(False)  # 初始状态为禁用
        button_layout.addWidget(self.stop_generate_btn)
        
        # 添加双语对照按钮
        self.bilingual_btn = QPushButton("查看双语对照")
        self.bilingual_btn.clicked.connect(self.show_bilingual_content)
        self.bilingual_btn.setToolTip("查看中英文内容对照")
        self.bilingual_btn.setEnabled(False)  # 初始状态为禁用
        button_layout.addWidget(self.bilingual_btn)
        
        right_layout.addLayout(button_layout)
        
        # 添加改写文章专用进度条
        from PyQt5.QtWidgets import QProgressBar
        self.rewrite_progress = QProgressBar()
        self.rewrite_progress.setVisible(False)  # 初始时隐藏
        self.rewrite_progress.setFixedHeight(20)
        self.rewrite_progress.setMinimumWidth(200)
        # 设置改写进度条样式 - 现代化设计
        self.rewrite_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                text-align: center;
                background-color: #f5f5f5;
                height: 8px;
                font-size: 12px;
                color: #666;
                font-weight: normal;
                padding: 0px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 #ffb74d, stop: 1 #ff9800);
                border-radius: 3px;
                margin: 0px;
            }
            QProgressBar:indeterminate {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 #fff3e0, stop: 0.5 #ffb74d, stop: 1 #fff3e0);
                border-radius: 3px;
            }
        """)
        right_layout.addWidget(self.rewrite_progress)
        
        # 添加分镜生成专用进度条
        self.storyboard_progress = QProgressBar()
        self.storyboard_progress.setVisible(False)  # 初始时隐藏
        self.storyboard_progress.setFixedHeight(20)
        self.storyboard_progress.setMinimumWidth(200)
        # 设置分镜进度条样式 - 现代化设计
        self.storyboard_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                text-align: center;
                background-color: #f5f5f5;
                height: 8px;
                font-size: 12px;
                color: #666;
                font-weight: normal;
                padding: 0px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 #42a5f5, stop: 1 #1976d2);
                border-radius: 3px;
                margin: 0px;
            }
            QProgressBar:indeterminate {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 #e3f2fd, stop: 0.5 #42a5f5, stop: 1 #e3f2fd);
                border-radius: 3px;
            }
        """)
        right_layout.addWidget(self.storyboard_progress)
        
        right_widget.setLayout(right_layout)

        # 创建可切换的右侧区域
        self.right_stack_widget = QWidget()
        right_stack_layout = QVBoxLayout()
        
        # 默认显示的右侧区域
        self.default_right_widget = right_widget
        right_stack_layout.addWidget(self.default_right_widget)
        self.right_stack_widget.setLayout(right_stack_layout)
        
        # 设置分割器
        storyboard_splitter.addWidget(left_widget)
        storyboard_splitter.addWidget(self.right_stack_widget)
        storyboard_splitter.setStretchFactor(0, 1)  # 左侧输入区域
        storyboard_splitter.setStretchFactor(1, 3)  # 右侧区域占更大空间
        
        # 主布局
        layout = QVBoxLayout()
        layout.addWidget(storyboard_splitter)
        self.setLayout(layout)
        
    def show_bilingual_content(self):
        """显示双语内容对照"""
        if self.chinese_content or self.english_content:
            dialog = BilingualTextDialog(
                self.chinese_content, 
                self.english_content, 
                "双语内容对照",
                self
            )
            dialog.exec_()
    
    def load_rewritten_text_from_main(self):
        """从主窗口加载已改写的文本"""
        try:
            if hasattr(self.parent_window, 'rewritten_text') and self.parent_window.rewritten_text:
                rewritten_text = self.parent_window.rewritten_text.toPlainText().strip()
                if rewritten_text:
                    self.text_input.setPlainText(rewritten_text)
                    logger.info("已从主窗口加载改写文本到分镜生成标签页")
                    return True
            
            # 如果主窗口没有改写文本，从项目管理器加载
            if hasattr(self.parent_window, 'project_manager') and self.parent_window.project_manager.current_project:
                rewritten_text = self.parent_window.project_manager.load_text_content("rewritten_text")
                if rewritten_text:
                    self.text_input.setPlainText(rewritten_text)
                    logger.info("已从项目文件加载改写文本到分镜生成标签页")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"加载改写文本失败: {e}")
            return False
    
    def _has_unsaved_content(self) -> bool:
        """检查是否有未保存的内容"""
        try:
            # 检查文本输入框是否有内容
            if self.text_input.toPlainText().strip():
                return True
            
            # 检查输出文本框是否有内容
            if self.output_text.toPlainText().strip():
                return True
            
            # 检查是否有正在进行的生成任务
            if self.is_generating:
                return True
                
            return False
        except Exception as e:
            logger.error(f"检查未保存内容时出错: {e}")
            return False
    
    def _get_skip_confirmation_setting(self) -> bool:
        """获取跳过确认对话框的设置"""
        try:
            return self.config_manager.get_setting('language_switch_skip_confirmation', False)
        except Exception as e:
            logger.error(f"获取跳过确认设置时出错: {e}")
            return False
    
    def _set_skip_confirmation_setting(self, skip: bool):
        """设置跳过确认对话框的选项"""
        try:
            self.config_manager.set_setting('language_switch_skip_confirmation', skip)
            logger.info(f"语言切换确认设置已更新: skip={skip}")
        except Exception as e:
            logger.error(f"设置跳过确认选项时出错: {e}")
    
    def _set_language_combo_value(self, language: LanguageCode):
        """设置语言下拉框的值"""
        try:
            for i in range(self.language_combo.count()):
                if self.language_combo.itemData(i) == language:
                    self.language_combo.setCurrentIndex(i)
                    break
        except Exception as e:
            logger.error(f"设置语言下拉框值时出错: {e}")
    
    def _perform_language_switch(self, new_language: LanguageCode):
        """执行语言切换"""
        try:
            self.language_switch_in_progress = True
            
            # 更新语言管理器
            success = self.language_manager.set_language(new_language)
            if not success:
                logger.error(f"语言管理器切换失败: {new_language.value}")
                self._set_language_combo_value(self.language_manager.current_language)
                return
            
            # 更新项目语言设置
            self._update_project_language_settings(new_language)
            
            # 更新界面提示信息
            self._update_ui_language_hints(new_language)
            
            # 清空双语内容缓存（因为语言已切换）
            self.chinese_content = ""
            self.english_content = ""
            self.bilingual_btn.setEnabled(False)
            
            # 重置LLM API（因为可能需要不同的提示词模板）
            self.llm_api = None
            
            logger.info(f"语言切换完成: {new_language.value}")
            
        except Exception as e:
            logger.error(f"执行语言切换时出错: {e}")
        finally:
            self.language_switch_in_progress = False
    
    def _update_project_language_settings(self, language: LanguageCode):
        """更新项目语言设置"""
        try:
            if self.project_manager and self.project_manager.current_project:
                project_data = self.project_manager.current_project
                if 'language_settings' not in project_data:
                    from src.models.language_models import ProjectLanguageSettings
                    default_settings = ProjectLanguageSettings(
                        primary_language=LanguageCode.CHINESE,
                        content_language=LanguageCode.CHINESE,
                        voice_language=LanguageCode.CHINESE,
                        subtitle_language=LanguageCode.CHINESE
                    )
                    project_data['language_settings'] = default_settings.to_dict()
                
                # 更新内容语言
                project_data['language_settings']['content_language'] = language.value
                project_data['language_settings']['updated_at'] = datetime.now().isoformat()
                
                # 保存项目
                if self.current_project_name:
                    self.project_manager.save_project(self.current_project_name, project_data)
                    logger.debug(f"项目语言设置已更新: {language.value}")
        except Exception as e:
            logger.error(f"更新项目语言设置时出错: {e}")
    
    def _update_ui_language_hints(self, language: LanguageCode):
        """更新界面提示信息"""
        try:
            if language == LanguageCode.CHINESE:
                # 中文提示
                self.text_input.setPlaceholderText(
                    "此处将自动显示第一个标签页改写后的文本内容，\n您也可以在此输入或编辑自定义文本..."
                )
                self.output_text.setPlaceholderText("显示大模型输出的分镜/脚本/描述")
                self.generate_shots_btn.setText("生成分镜")
                self.stop_generate_btn.setText("停止生成")
                self.bilingual_btn.setText("查看双语对照")
                
                # 更新工具提示
                self.text_input.setToolTip("显示第一个标签页改写后的文本内容，或输入自定义文本进行分镜生成")
                self.output_text.setToolTip("显示大模型输出的分镜/脚本/描述")
                self.generate_shots_btn.setToolTip("根据大模型输出生成分镜表")
                self.stop_generate_btn.setToolTip("停止当前的分镜生成任务")
                self.bilingual_btn.setToolTip("查看中英文内容对照")
                
            elif language == LanguageCode.ENGLISH:
                # 英文提示
                self.text_input.setPlaceholderText(
                    "The rewritten text from the first tab will be displayed here automatically,\n"
                    "or you can input/edit custom text..."
                )
                self.output_text.setPlaceholderText("Display storyboard/script/description output from LLM")
                self.generate_shots_btn.setText("Generate Storyboard")
                self.stop_generate_btn.setText("Stop Generation")
                self.bilingual_btn.setText("View Bilingual Content")
                
                # 更新工具提示
                self.text_input.setToolTip("Display rewritten text from the first tab, or input custom text for storyboard generation")
                self.output_text.setToolTip("Display storyboard/script/description output from LLM")
                self.generate_shots_btn.setToolTip("Generate storyboard table based on LLM output")
                self.stop_generate_btn.setToolTip("Stop current storyboard generation task")
                self.bilingual_btn.setToolTip("View Chinese-English content comparison")
                
        except Exception as e:
            logger.error(f"更新界面提示信息时出错: {e}")
    
    def on_language_manager_changed(self, new_language: LanguageCode):
        """语言管理器语言变更回调"""
        try:
            if not self.language_switch_in_progress:
                # 同步更新下拉框选择
                self.language_switch_in_progress = True
                self._set_language_combo_value(new_language)
                self.language_switch_in_progress = False
                
                # 更新界面提示
                self._update_ui_language_hints(new_language)
                
            logger.debug(f"语言管理器回调: {new_language.value}")
        except Exception as e:
            logger.error(f"处理语言管理器变更回调时出错: {e}")
    

    
    def handle_generate_shots_btn(self):
        """处理生成分镜按钮点击"""
        try:
            # 检查是否有项目，如果没有则强制创建
            if not self.parent_window or not hasattr(self.parent_window, 'project_manager') or not self.parent_window.project_manager.current_project:
                QMessageBox.information(
                    self, 
                    "需要创建项目", 
                    "生成分镜需要先创建一个项目。\n请返回第一个标签页创建项目。"
                )
                # 自动切换到第一个标签页
                if self.parent_window and hasattr(self.parent_window, 'tab_widget'):
                    self.parent_window.tab_widget.setCurrentIndex(0)
                return
            
            # 获取输入文本（左侧的文本输入框）
            input_text = self.text_input.toPlainText().strip()
            if not input_text:
                # 尝试从主窗口加载改写文本
                if not self.load_rewritten_text_from_main():
                    QMessageBox.warning(self, "警告", "请先输入文本内容或在第一个标签页完成文本改写")
                    return
                input_text = self.text_input.toPlainText().strip()
            
            # 获取当前选择的语言
            current_language = self.language_combo.itemData(self.language_combo.currentIndex())
            
            # 如果是英文，尝试生成对应的中文内容用于对照
            if current_language == LanguageCode.ENGLISH:
                # 这里应该调用翻译服务生成中文对照内容
                # 为简化演示，我们只是简单地保存内容
                self.english_content = input_text
                self.chinese_content = "（需要翻译服务将英文内容翻译为中文）"
            else:
                # 中文内容，可以尝试生成英文翻译
                self.chinese_content = input_text
                self.english_content = "（需要翻译服务将中文内容翻译为英文）"
            
            # 启用双语对照按钮
            self.bilingual_btn.setEnabled(True)
            
            # 设置生成状态
            self.is_generating = True
            self.stop_generation = False
            
            # 从主窗口获取LLM配置
            if not self.llm_api:
                if self.parent_window and hasattr(self.parent_window, 'app_controller'):
                    # 使用选择的大模型配置
                    try:
                        selected_model = self.get_current_model()
                        if selected_model in ["未配置模型", "加载失败", None]:
                            QMessageBox.warning(self, "错误", "请选择一个有效的大模型")
                            self.is_generating = False
                            return
                        
                        # 获取选择的模型配置
                        all_model_configs = self.config_manager.config.get("models", [])
                        model_config = None
                        for cfg in all_model_configs:
                            if cfg.get("name") == selected_model:
                                model_config = cfg
                                break
                        
                        if not model_config:
                            QMessageBox.warning(self, "错误", f"未找到模型 '{selected_model}' 的配置")
                            self.is_generating = False
                            return
                        
                        # 初始化LLM API
                        self.llm_api = LLMApi(
                            api_type=model_config.get('type', 'deepseek'),
                            api_key=model_config.get('key', ''),
                            api_url=model_config.get('url', '')
                        )
                        logger.info(f"使用选择的模型配置: {model_config.get('name', 'unknown')}")
                    except Exception as e:
                        QMessageBox.warning(self, "错误", f"初始化LLM API失败: {e}")
                        self.is_generating = False
                        return
                else:
                    QMessageBox.warning(self, "错误", "无法获取LLM配置")
                    self.is_generating = False
                    return
            
            # 创建文本解析器
            selected_style = self.style_combo.currentText()
            self.text_parser = TextParser(llm_api=self.llm_api, style=selected_style)
            
            # 显示分镜进度条
            self.show_progress("🎬 正在生成分镜，请稍候...", "storyboard")
            
            # 更新按钮状态
            self.generate_shots_btn.setEnabled(False)
            self.generate_shots_btn.setText("🎬 生成中...")
            self.stop_generate_btn.setEnabled(True)
            
            # 检查是否被停止
            if self.stop_generation:
                logger.info("分镜生成被用户停止")
                return
            
            # 检查是否已有线程在运行
            if self.shots_thread and self.shots_thread.isRunning():
                QMessageBox.warning(self, "警告", "分镜生成正在进行中，请稍候...")
                return
            
            # 创建并启动分镜生成线程
            self.shots_thread = ShotsGenerationThread(self.text_parser, input_text)
            self.shots_thread.progress_updated.connect(self.show_progress)
            self.shots_thread.shots_generated.connect(self._on_shots_generated)
            self.shots_thread.error_occurred.connect(self._on_shots_error)
            self.shots_thread.finished.connect(self._on_shots_finished)
            self.shots_thread.start()
                
        except Exception as e:
            logger.error(f"启动分镜生成线程时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"启动分镜生成失败: {str(e)}")
            self._reset_shots_ui()
    
    def handle_stop_generate_btn(self):
        """处理停止生成按钮点击"""
        if self.is_generating:
            self.stop_generation = True
            logger.info("用户请求停止分镜生成")
            
            # 停止正在运行的线程
            if hasattr(self, 'shots_thread') and self.shots_thread and self.shots_thread.isRunning():
                logger.info("正在停止分镜生成线程")
                self.shots_thread.cancel()  # 调用线程的取消方法
                self.shots_thread.wait(3000)  # 等待最多3秒让线程正常结束
                if self.shots_thread.isRunning():
                    logger.warning("线程未能正常停止，强制终止")
                    self.shots_thread.terminate()
                    self.shots_thread.wait(1000)
            
            # 立即更新按钮状态
            self.stop_generate_btn.setEnabled(False)
            self.stop_generate_btn.setText("正在停止...")
            # 显示停止消息
            self.show_progress("⏹️ 正在停止生成...")
            
            # 重置UI状态
            self._reset_shots_ui()
    
    def show_progress(self, message="⏳ 处理中，请稍候...", progress_type="storyboard"):
        """显示进度条
        Args:
            message: 进度消息
            progress_type: 进度条类型，'rewrite' 或 'storyboard'
        """
        try:
            if progress_type == "rewrite":
                # 使用改写文章专用的进度条
                if hasattr(self, 'rewrite_progress'):
                    # 设置进度条属性
                    self.rewrite_progress.setVisible(True)
                    self.rewrite_progress.setRange(0, 0)  # 设置为不确定进度条
                    self.rewrite_progress.setFormat(message)  # 设置显示文本
                    self.rewrite_progress.setTextVisible(True)  # 确保文本可见
                    
                    # 强制刷新界面
                    self.rewrite_progress.update()
                    from PyQt5.QtWidgets import QApplication
                    QApplication.instance().processEvents()
                    
                    # 在日志中显示消息
                    if self.parent_window and hasattr(self.parent_window, 'log_output_bottom'):
                        self.parent_window.log_output_bottom.appendPlainText(f"[改写进度] {message}")
                    logger.info(f"改写进度条已显示: {message}, 可见性: {self.rewrite_progress.isVisible()}")
                else:
                    logger.warning("未找到改写进度条组件")
            else:
                # 使用分镜界面专用的进度条
                if hasattr(self, 'storyboard_progress'):
                    # 设置进度条属性
                    self.storyboard_progress.setVisible(True)
                    self.storyboard_progress.setRange(0, 0)  # 设置为不确定进度条
                    self.storyboard_progress.setFormat(message)  # 设置显示文本
                    self.storyboard_progress.setTextVisible(True)  # 确保文本可见
                    
                    # 强制刷新界面
                    self.storyboard_progress.update()
                    from PyQt5.QtWidgets import QApplication
                    QApplication.instance().processEvents()
                    
                    # 在日志中显示消息
                    if self.parent_window and hasattr(self.parent_window, 'log_output_bottom'):
                        self.parent_window.log_output_bottom.appendPlainText(f"[分镜进度] {message}")
                    logger.info(f"分镜进度条已显示: {message}, 可见性: {self.storyboard_progress.isVisible()}")
                else:
                    logger.warning("未找到分镜进度条组件")
        except Exception as e:
            logger.error(f"显示进度条时发生错误: {e}")
    
    def hide_progress(self, progress_type="storyboard"):
        """隐藏进度条
        Args:
            progress_type: 进度条类型，'rewrite' 或 'storyboard'
        """
        try:
            if progress_type == "rewrite":
                # 隐藏改写文章专用的进度条
                if hasattr(self, 'rewrite_progress'):
                    self.rewrite_progress.setVisible(False)
                    self.rewrite_progress.setFormat("")  # 清空显示文本
                    self.rewrite_progress.setTextVisible(False)  # 隐藏文本
                    
                    # 强制刷新界面
                    self.rewrite_progress.update()
                    from PyQt5.QtWidgets import QApplication
                    QApplication.instance().processEvents()
                    
                    # 在日志中显示消息
                    if self.parent_window and hasattr(self.parent_window, 'log_output_bottom'):
                        self.parent_window.log_output_bottom.appendPlainText("✅ 改写操作完成")
                    logger.info(f"改写进度条已隐藏，可见性: {self.rewrite_progress.isVisible()}")
                else:
                    logger.warning("未找到改写进度条组件")
            else:
                # 隐藏分镜界面专用的进度条
                if hasattr(self, 'storyboard_progress'):
                    self.storyboard_progress.setVisible(False)
                    self.storyboard_progress.setFormat("")  # 清空显示文本
                    self.storyboard_progress.setTextVisible(False)  # 隐藏文本
                    
                    # 强制刷新界面
                    self.storyboard_progress.update()
                    from PyQt5.QtWidgets import QApplication
                    QApplication.instance().processEvents()
                    
                    # 在日志中显示消息
                    if self.parent_window and hasattr(self.parent_window, 'log_output_bottom'):
                        self.parent_window.log_output_bottom.appendPlainText("✅ 分镜操作完成")
                    logger.info(f"分镜进度条已隐藏，可见性: {self.storyboard_progress.isVisible()}")
                else:
                    logger.warning("未找到分镜进度条组件")
        except Exception as e:
            logger.error(f"隐藏进度条时发生错误: {e}")
    
    def show_shots_table(self, shots_data):
        print(f"[DEBUG] storyboard_tab.show_shots_table - shots_data: {shots_data}")
        print(f"[DEBUG] storyboard_tab.show_shots_table - len(shots_data): {len(shots_data) if shots_data else 0}")
        """显示分镜表格"""
        try:
            # 将分镜表格显示在分镜设置标签页中，而不是弹出新窗口
            if hasattr(self, 'parent_window') and self.parent_window:
                self.parent_window.show_shots_in_settings_tab(shots_data)
                # 切换到分镜设置标签页
                self.parent_window.tabs.setCurrentIndex(1)  # 1是分镜设置标签页的索引
            else:
                # 如果没有父窗口，尝试获取主窗口引用
                main_window = self.parent_window if hasattr(self, 'parent_window') and self.parent_window else self.get_main_window()
                shots_window = ShotsWindow(main_window, shots_data)
                shots_window.show()
            
        except Exception as e:
            logger.error(f"显示分镜表格时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"显示分镜表格失败: {str(e)}")
    
    def get_main_window(self):
        """获取主窗口引用"""
        widget = self
        while widget.parent():
            widget = widget.parent()
            if hasattr(widget, 'on_shots_alternative_image_selected'):
                return widget
        return None
    
    def get_current_style(self):
        """获取当前选择的风格"""
        current_style = self.style_combo.currentText()
        logger.debug(f"获取当前选择的风格: {current_style}")
        return current_style
    
    def on_style_changed(self, style_text):
        """风格选择变化时的处理"""
        logger.info(f"用户选择了新风格: {style_text}")
        self.save_style_selection(style_text)
    
    def save_style_selection(self, style_text):
        """保存风格选择到配置文件"""
        try:
            if hasattr(self.parent_window, 'config_manager'):
                config = self.parent_window.config_manager.config
                if 'ui_settings' not in config:
                    config['ui_settings'] = {}
                config['ui_settings']['selected_style'] = style_text
                self.parent_window.config_manager.save_config(config) # 传递config数据
                logger.debug(f"风格选择已保存: {style_text}")
        except Exception as e:
            logger.error(f"保存风格选择失败: {e}")
    
    def restore_style_selection(self):
        """恢复上次选择的风格"""
        try:
            if hasattr(self.parent_window, 'config_manager'):
                config = self.parent_window.config_manager.config
                saved_style = config.get('ui_settings', {}).get('selected_style', '吉卜力风格')
                
                # 查找并设置保存的风格
                for i in range(self.style_combo.count()):
                    if self.style_combo.itemText(i) == saved_style:
                        self.style_combo.setCurrentIndex(i)
                        logger.info(f"恢复风格选择: {saved_style}")
                        break
                else:
                    # 如果没找到保存的风格，默认选择吉卜力风格
                    for i in range(self.style_combo.count()):
                        if self.style_combo.itemText(i) == '吉卜力风格':
                            self.style_combo.setCurrentIndex(i)
                            logger.info("使用默认风格: 吉卜力风格")
                            break
        except Exception as e:
            logger.error(f"恢复风格选择失败: {e}")
            # 出错时默认选择吉卜力风格
            for i in range(self.style_combo.count()):
                if self.style_combo.itemText(i) == '吉卜力风格':
                    self.style_combo.setCurrentIndex(i)
                    break
    
    def get_input_text(self):
        """获取输入文本"""
        return self.text_input.toPlainText()
    
    def get_output_text(self):
        """获取输出文本"""
        return self.output_text.toPlainText()
    
    def set_output_text(self, text):
        """设置输出文本"""
        self.output_text.setPlainText(text)
    
    def create_operation_buttons(self, row_index):
        """为指定行创建操作按钮组件"""
        from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
        
        # 创建按钮容器
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(5, 2, 5, 2)
        button_layout.setSpacing(3)
        
        # 绘图按钮
        draw_btn = QPushButton("绘图")
        draw_btn.setProperty("class", "draw-button")
        draw_btn.clicked.connect(lambda: self.handle_draw_btn(row_index))
        button_layout.addWidget(draw_btn)
        
        # 配音按钮
        voice_btn = QPushButton("配音")
        voice_btn.setProperty("class", "voice-button")
        voice_btn.clicked.connect(lambda: self.handle_voice_btn(row_index))
        button_layout.addWidget(voice_btn)
        
        # 试听按钮（初始隐藏）
        preview_btn = QPushButton("试听")
        preview_btn.setProperty("class", "preview-button")
        preview_btn.clicked.connect(lambda: self.handle_preview_btn(row_index))
        preview_btn.setVisible(False)  # 初始隐藏
        button_layout.addWidget(preview_btn)
        
        # 存储试听按钮引用，用于后续显示/隐藏
        if not hasattr(self, 'preview_buttons'):
            self.preview_buttons = {}
        self.preview_buttons[row_index] = preview_btn
        
        # 检查是否已有配音文件，如果有则显示试听按钮
        self._check_and_show_preview_button(row_index, preview_btn)
        
        # 分镜设置按钮
        setting_btn = QPushButton("分镜设置")
        setting_btn.setProperty("class", "setting-button")
        setting_btn.clicked.connect(lambda: self.handle_shot_setting_btn(row_index))
        button_layout.addWidget(setting_btn)
        
        return button_widget
    
    def handle_draw_btn(self, row_index):
        """处理绘图按钮点击事件"""
        try:
            logger.info(f"用户点击第{row_index+1}行的绘图按钮")
            
            # 获取该行的提示词
            prompt = self.get_prompt_for_row(row_index)
            logger.debug(f"第{row_index+1}行原始提示词: {prompt}")
            
            if not prompt:
                logger.warning(f"第{row_index+1}行没有提示词内容，无法生成图片")
                QMessageBox.warning(self, "警告", f"第{row_index+1}行没有提示词内容")
                return

            # 获取当前选择的风格
            current_style = self.get_current_style()
            logger.info(f"当前选择的风格: {current_style}")

            # 显示进度提示
            logger.debug(f"显示第{row_index+1}行图片生成进度提示")
            self.show_progress(f"正在为第{row_index+1}行生成图片...")
            
            # 在底部状态栏立即显示"正在生图"状态
            if self.parent_window and hasattr(self.parent_window, 'log_output_bottom'):
                status_message = f"🎨 正在生图 | 第{row_index+1}行 | 提示词: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
                self.parent_window.log_output_bottom.appendPlainText(status_message)
                # 滚动到底部显示最新信息
                self.parent_window.log_output_bottom.verticalScrollBar().setValue(
                    self.parent_window.log_output_bottom.verticalScrollBar().maximum()
                )

            # 调用父窗口的绘图处理方法，传递行索引和提示词
            if self.parent_window and hasattr(self.parent_window, 'process_draw_request'):
                logger.info(f"开始处理第{row_index+1}行的绘图请求，提示词: {prompt}")
                self.parent_window.process_draw_request(row_index, prompt)
            else:
                logger.error("无法找到绘图处理方法，父窗口或process_draw_request方法不存在")
                self.hide_progress()
                QMessageBox.warning(self, "错误", "无法找到绘图处理方法")
                
        except Exception as e:
            self.hide_progress()
            logger.error(f"处理绘图按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"绘图功能出错: {str(e)}")
    
    def handle_voice_btn(self, row_index):
        """处理配音按钮点击事件"""
        try:
            # 获取当前行的文案内容
            text_item = self.table_widget.item(row_index, 0)  # 文案列
            if not text_item or not text_item.text().strip():
                QMessageBox.warning(self, "警告", "当前分镜没有文案内容，无法进行配音")
                return
            
            text_content = text_item.text().strip()
            
            # 导入AI配音对话框
            from src.gui.ai_voice_dialog import AIVoiceDialog
            
            # 创建并显示AI配音对话框
            dialog = AIVoiceDialog(self, text_content, row_index)
            if dialog.exec_() == QDialog.Accepted:
                # 用户确认生成，获取生成结果
                result = dialog.get_generation_result()
                if result and result.get('success'):
                    # 更新表格中的语音列信息
                     voice_item = self.table_widget.item(row_index, 6)  # 语音列
                     if voice_item:
                         voice_item.setText(f"已生成: {os.path.basename(result['audio_file'])}")
                     else:
                         voice_item = QTableWidgetItem(f"已生成: {os.path.basename(result['audio_file'])}")
                         self.table_widget.setItem(row_index, 6, voice_item)
                     
                     # 更新分镜数据中的语音文件路径
                     if hasattr(self.parent_window, 'shots_data') and self.parent_window.shots_data and row_index < len(self.parent_window.shots_data):
                         self.parent_window.shots_data[row_index]['voice_file'] = result['audio_file']
                         # 自动保存项目
                         self.parent_window.save_current_project()
                         logger.info(f"已更新第{row_index+1}行分镜的语音文件: {result['audio_file']}")
                     
                     # 显示试听按钮
                     if hasattr(self, 'preview_buttons') and row_index in self.preview_buttons:
                         self.preview_buttons[row_index].setVisible(True)
                         logger.info(f"第{row_index+1}行试听按钮已显示")
                     
                     QMessageBox.information(self, "成功", "语音生成完成！")
                elif result:
                    QMessageBox.warning(self, "错误", f"语音生成失败: {result.get('error', '未知错误')}")
                    
        except ImportError as e:
            QMessageBox.critical(self, "错误", f"无法加载AI配音模块: {str(e)}")
        except Exception as e:
            logger.error(f"处理配音按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"配音功能出错: {str(e)}")
    
    def handle_preview_btn(self, row_index):
        """处理试听按钮点击事件"""
        try:
            # 获取配音文件路径
            voice_file = None
            
            # 从分镜数据中获取语音文件路径
            if hasattr(self.parent_window, 'shots_data') and self.parent_window.shots_data and row_index < len(self.parent_window.shots_data):
                voice_file = self.parent_window.shots_data[row_index].get('voice_file')
            
            if not voice_file or not os.path.exists(voice_file):
                QMessageBox.warning(self, "警告", "未找到配音文件，请先生成配音")
                return
            
            # 播放音频文件
            self._play_audio_file(voice_file)
            logger.info(f"开始播放第{row_index+1}行的配音文件: {voice_file}")
            
        except Exception as e:
            logger.error(f"处理试听按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"试听功能出错: {str(e)}")
    
    def _play_audio_file(self, file_path: str):
        """播放音频文件
        
        Args:
            file_path: 音频文件路径
        """
        try:
            import platform
            import subprocess
            
            system = platform.system()
            logger.debug(f"尝试播放音频文件: {file_path}, 系统: {system}")
            
            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":  # macOS
                subprocess.call(["open", file_path])
            else:  # Linux
                subprocess.call(["xdg-open", file_path])
                
        except Exception as e:
            logger.warning(f"播放音频文件失败: {e}")
            QMessageBox.warning(self, "警告", f"无法播放音频文件: {str(e)}")
    
    def _check_and_show_preview_button(self, row_index, preview_btn):
        """检查是否已有配音文件，如果有则显示试听按钮
        
        Args:
            row_index: 行索引
            preview_btn: 试听按钮对象
        """
        try:
            # 从分镜数据中获取语音文件路径
            if hasattr(self.parent_window, 'shots_data') and self.parent_window.shots_data and row_index < len(self.parent_window.shots_data):
                voice_file = self.parent_window.shots_data[row_index].get('voice_file')
                if voice_file and os.path.exists(voice_file):
                    preview_btn.setVisible(True)
                    logger.debug(f"第{row_index+1}行已有配音文件，显示试听按钮: {voice_file}")
                else:
                    preview_btn.setVisible(False)
            else:
                preview_btn.setVisible(False)
        except Exception as e:
            logger.warning(f"检查配音文件时发生错误: {e}")
            preview_btn.setVisible(False)
    
    def handle_shot_setting_btn(self, row_index):
        """处理分镜设置按钮点击事件"""
        try:
            # 这里将实现分镜设置功能
            QMessageBox.information(self, "提示", f"分镜设置功能 - 第{row_index+1}行\n\n此功能正在开发中，敬请期待！")
        except Exception as e:
            logger.error(f"处理分镜设置按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"分镜设置功能出错: {str(e)}")
    
    def update_shot_image(self, row_index, image_path):
        """更新分镜表格中指定行的图片"""
        try:
            logger.info(f"更新第{row_index+1}行的分镜图片: {image_path}")
            
            # 如果父窗口有分镜表格，更新表格中的图片
            if (self.parent_window and 
                hasattr(self.parent_window, 'shots_table') and 
                self.parent_window.shots_table is not None):
                
                table = self.parent_window.shots_table
                
                # 检查表格行数与数据是否同步
                if (hasattr(self.parent_window, 'shots_data') and 
                    self.parent_window.shots_data and 
                    table.rowCount() != len(self.parent_window.shots_data)):
                    
                    logger.warning(f"表格行数不匹配，开始同步: {table.rowCount()} -> {len(self.parent_window.shots_data)}")
                    try:
                        self.parent_window.populate_shots_table_data(self.parent_window.shots_data)
                        logger.info(f"表格同步完成，新行数: {table.rowCount()}")
                    except Exception as sync_error:
                        logger.error(f"表格同步失败: {sync_error}")
                        return False
                
                if 0 <= row_index < table.rowCount():
                    # 图片列是第4列（索引为4）
                    from PyQt5.QtWidgets import QTableWidgetItem
                    from PyQt5.QtGui import QPixmap
                    from PyQt5.QtCore import Qt
                    
                    # 创建图片项
                    item = QTableWidgetItem(image_path)  # 设置DisplayRole数据为图片路径
                    if os.path.exists(image_path):
                        # 加载图片并设置为缩略图
                        pixmap = QPixmap(image_path)
                        if not pixmap.isNull():
                            # 缩放图片到合适大小
                            scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            item.setData(Qt.DecorationRole, scaled_pixmap)  # 设置DecorationRole数据为图片对象
                            item.setToolTip(f"图片路径: {image_path}")
                            logger.info(f"成功设置第{row_index+1}行的图片")
                        else:
                            logger.warning(f"第{row_index+1}行图片加载失败: {image_path}")
                    else:
                        logger.warning(f"第{row_index+1}行图片文件不存在: {image_path}")
                    
                    # 设置到表格中
                    table.setItem(row_index, 4, item)
                    
                    # 调整行高以适应图片
                    table.setRowHeight(row_index, 120)
                    
                    logger.info(f"第{row_index+1}行分镜图片更新完成")
                    return True
                else:
                    logger.debug(f"行索引超出范围: {row_index}, 表格行数: {table.rowCount()}")
                    return False
            else:
                logger.debug("未找到分镜表格，无法更新图片")
                return False
                
        except Exception as e:
            logger.error(f"更新分镜图片时发生错误: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False
    

    
    def get_prompt_for_row(self, row_index):
        """获取指定行的提示词内容"""
        try:
            # 如果当前在分镜表格视图中，从父窗口的分镜表格获取数据
            if (self.parent_window and 
                hasattr(self.parent_window, 'shots_table') and 
                self.parent_window.shots_table is not None):
                
                table = self.parent_window.shots_table
                if 0 <= row_index < table.rowCount():
                    # 提示词列是第3列（索引为3）
                    item = table.item(row_index, 3)
                    if item and item.text().strip():
                        return item.text().strip()
            
            # 如果没有找到提示词，返回空字符串
            return ""
        except Exception as e:
            logger.error(f"获取提示词时发生错误: {e}")
            return ""
    
    def get_current_style(self):
        """获取当前选择的风格"""
        try:
            if hasattr(self, 'style_combo') and self.style_combo:
                return self.style_combo.currentText()
            return "默认"
        except Exception as e:
            logger.error(f"获取当前风格时发生错误: {e}")
            return "默认"
    
    def on_style_changed(self, style_text):
        """风格选择变化时的处理"""
        logger.info(f"用户选择了新风格: {style_text}")
        self.save_style_selection(style_text)
    
    def save_style_selection(self, style_text):
        """保存风格选择到配置文件"""
        try:
            if hasattr(self.parent_window, 'config_manager'):
                config = self.parent_window.config_manager.config
                if 'ui_settings' not in config:
                    config['ui_settings'] = {}
                config['ui_settings']['selected_style'] = style_text
                self.parent_window.config_manager.save_config(config) # 传递config数据
                logger.debug(f"风格选择已保存: {style_text}")
        except Exception as e:
            logger.error(f"保存风格选择失败: {e}")
    
    def restore_style_selection(self):
        """恢复上次选择的风格"""
        try:
            if hasattr(self.parent_window, 'config_manager'):
                config = self.parent_window.config_manager.config
                saved_style = config.get('ui_settings', {}).get('selected_style', '吉卜力风格')
                
                # 查找并设置保存的风格
                for i in range(self.style_combo.count()):
                    if self.style_combo.itemText(i) == saved_style:
                        self.style_combo.setCurrentIndex(i)
                        logger.info(f"恢复风格选择: {saved_style}")
                        break
                else:
                    # 如果没找到保存的风格，默认选择吉卜力风格
                    for i in range(self.style_combo.count()):
                        if self.style_combo.itemText(i) == '吉卜力风格':
                            self.style_combo.setCurrentIndex(i)
                            logger.info("使用默认风格: 吉卜力风格")
                            break
        except Exception as e:
            logger.error(f"恢复风格选择失败: {e}")
            # 出错时默认选择吉卜力风格
            for i in range(self.style_combo.count()):
                if self.style_combo.itemText(i) == '吉卜力风格':
                    self.style_combo.setCurrentIndex(i)
                    break
    
    def get_input_text(self):
        """获取输入文本"""
        return self.text_input.toPlainText()
    
    def get_output_text(self):
        """获取输出文本"""
        return self.output_text.toPlainText()
    
    def set_output_text(self, text):
        """设置输出文本"""
        self.output_text.setPlainText(text)
    
    def create_operation_buttons(self, row_index):
        """为指定行创建操作按钮组件"""
        from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
        
        # 创建按钮容器
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(5, 2, 5, 2)
        button_layout.setSpacing(3)
        
        # 绘图按钮
        draw_btn = QPushButton("绘图")
        draw_btn.setProperty("class", "draw-button")
        draw_btn.clicked.connect(lambda: self.handle_draw_btn(row_index))
        button_layout.addWidget(draw_btn)
        
        # 配音按钮
        voice_btn = QPushButton("配音")
        voice_btn.setProperty("class", "voice-button")
        voice_btn.clicked.connect(lambda: self.handle_voice_btn(row_index))
        button_layout.addWidget(voice_btn)
        
        # 试听按钮（初始隐藏）
        preview_btn = QPushButton("试听")
        preview_btn.setProperty("class", "preview-button")
        preview_btn.clicked.connect(lambda: self.handle_preview_btn(row_index))
        preview_btn.setVisible(False)  # 初始隐藏
        button_layout.addWidget(preview_btn)
        
        # 存储试听按钮引用，用于后续显示/隐藏
        if not hasattr(self, 'preview_buttons'):
            self.preview_buttons = {}
        self.preview_buttons[row_index] = preview_btn
        
        # 检查是否已有配音文件，如果有则显示试听按钮
        self._check_and_show_preview_button(row_index, preview_btn)
        
        # 分镜设置按钮
        setting_btn = QPushButton("分镜设置")
        setting_btn.setProperty("class", "setting-button")
        setting_btn.clicked.connect(lambda: self.handle_shot_setting_btn(row_index))
        button_layout.addWidget(setting_btn)
        
        return button_widget
    
    def handle_draw_btn(self, row_index):
        """处理绘图按钮点击事件"""
        try:
            logger.info(f"用户点击第{row_index+1}行的绘图按钮")
            
            # 获取该行的提示词
            prompt = self.get_prompt_for_row(row_index)
            logger.debug(f"第{row_index+1}行原始提示词: {prompt}")
            
            if not prompt:
                logger.warning(f"第{row_index+1}行没有提示词内容，无法生成图片")
                QMessageBox.warning(self, "警告", f"第{row_index+1}行没有提示词内容")
                return

            # 获取当前选择的风格
            current_style = self.get_current_style()
            logger.info(f"当前选择的风格: {current_style}")

            # 显示进度提示
            logger.debug(f"显示第{row_index+1}行图片生成进度提示")
            self.show_progress(f"正在为第{row_index+1}行生成图片...")
            
            # 在底部状态栏立即显示"正在生图"状态
            if self.parent_window and hasattr(self.parent_window, 'log_output_bottom'):
                status_message = f"🎨 正在生图 | 第{row_index+1}行 | 提示词: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
                self.parent_window.log_output_bottom.appendPlainText(status_message)
                # 滚动到底部显示最新信息
                self.parent_window.log_output_bottom.verticalScrollBar().setValue(
                    self.parent_window.log_output_bottom.verticalScrollBar().maximum()
                )

            # 调用父窗口的绘图处理方法，传递行索引和提示词
            if self.parent_window and hasattr(self.parent_window, 'process_draw_request'):
                logger.info(f"开始处理第{row_index+1}行的绘图请求，提示词: {prompt}")
                self.parent_window.process_draw_request(row_index, prompt)
            else:
                logger.error("无法找到绘图处理方法，父窗口或process_draw_request方法不存在")
                self.hide_progress()
                QMessageBox.warning(self, "错误", "无法找到绘图处理方法")
                
        except Exception as e:
            self.hide_progress()
            logger.error(f"处理绘图按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"绘图功能出错: {str(e)}")
    
    def handle_voice_btn(self, row_index):
        """处理配音按钮点击事件"""
        try:
            # 获取当前行的文案内容
            text_item = self.table_widget.item(row_index, 0)  # 文案列
            if not text_item or not text_item.text().strip():
                QMessageBox.warning(self, "警告", "当前分镜没有文案内容，无法进行配音")
                return
            
            text_content = text_item.text().strip()
            
            # 导入AI配音对话框
            from src.gui.ai_voice_dialog import AIVoiceDialog
            
            # 创建并显示AI配音对话框
            dialog = AIVoiceDialog(self, text_content, row_index)
            if dialog.exec_() == QDialog.Accepted:
                # 用户确认生成，获取生成结果
                result = dialog.get_generation_result()
                if result and result.get('success'):
                    # 更新表格中的语音列信息
                     voice_item = self.table_widget.item(row_index, 6)  # 语音列
                     if voice_item:
                         voice_item.setText(f"已生成: {os.path.basename(result['audio_file'])}")
                     else:
                         voice_item = QTableWidgetItem(f"已生成: {os.path.basename(result['audio_file'])}")
                         self.table_widget.setItem(row_index, 6, voice_item)
                     
                     # 更新分镜数据中的语音文件路径
                     if hasattr(self.parent_window, 'shots_data') and self.parent_window.shots_data and row_index < len(self.parent_window.shots_data):
                         self.parent_window.shots_data[row_index]['voice_file'] = result['audio_file']
                         # 自动保存项目
                         self.parent_window.save_current_project()
                         logger.info(f"已更新第{row_index+1}行分镜的语音文件: {result['audio_file']}")
                     
                     # 显示试听按钮
                     if hasattr(self, 'preview_buttons') and row_index in self.preview_buttons:
                         self.preview_buttons[row_index].setVisible(True)
                         logger.info(f"第{row_index+1}行试听按钮已显示")
                     
                     QMessageBox.information(self, "成功", "语音生成完成！")
                elif result:
                    QMessageBox.warning(self, "错误", f"语音生成失败: {result.get('error', '未知错误')}")
                    
        except ImportError as e:
            QMessageBox.critical(self, "错误", f"无法加载AI配音模块: {str(e)}")
        except Exception as e:
            logger.error(f"处理配音按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"配音功能出错: {str(e)}")
    
    def handle_preview_btn(self, row_index):
        """处理试听按钮点击事件"""
        try:
            # 获取配音文件路径
            voice_file = None
            
            # 从分镜数据中获取语音文件路径
            if hasattr(self.parent_window, 'shots_data') and self.parent_window.shots_data and row_index < len(self.parent_window.shots_data):
                voice_file = self.parent_window.shots_data[row_index].get('voice_file')
            
            if not voice_file or not os.path.exists(voice_file):
                QMessageBox.warning(self, "警告", "未找到配音文件，请先生成配音")
                return
            
            # 播放音频文件
            self._play_audio_file(voice_file)
            logger.info(f"开始播放第{row_index+1}行的配音文件: {voice_file}")
            
        except Exception as e:
            logger.error(f"处理试听按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"试听功能出错: {str(e)}")
    
    def _play_audio_file(self, file_path: str):
        """播放音频文件
        
        Args:
            file_path: 音频文件路径
        """
        try:
            import platform
            import subprocess
            
            system = platform.system()
            logger.debug(f"尝试播放音频文件: {file_path}, 系统: {system}")
            
            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":  # macOS
                subprocess.call(["open", file_path])
            else:  # Linux
                subprocess.call(["xdg-open", file_path])
                
        except Exception as e:
            logger.warning(f"播放音频文件失败: {e}")
            QMessageBox.warning(self, "警告", f"无法播放音频文件: {str(e)}")
    
    def _check_and_show_preview_button(self, row_index, preview_btn):
        """检查是否已有配音文件，如果有则显示试听按钮
        
        Args:
            row_index: 行索引
            preview_btn: 试听按钮对象
        """
        try:
            # 从分镜数据中获取语音文件路径
            if hasattr(self.parent_window, 'shots_data') and self.parent_window.shots_data and row_index < len(self.parent_window.shots_data):
                voice_file = self.parent_window.shots_data[row_index].get('voice_file')
                if voice_file and os.path.exists(voice_file):
                    preview_btn.setVisible(True)
                    logger.debug(f"第{row_index+1}行已有配音文件，显示试听按钮: {voice_file}")
                else:
                    preview_btn.setVisible(False)
            else:
                preview_btn.setVisible(False)
        except Exception as e:
            logger.warning(f"检查配音文件时发生错误: {e}")
            preview_btn.setVisible(False)
    
    def handle_shot_setting_btn(self, row_index):
        """处理分镜设置按钮点击事件"""
        try:
            # 这里将实现分镜设置功能
            QMessageBox.information(self, "提示", f"分镜设置功能 - 第{row_index+1}行\n\n此功能正在开发中，敬请期待！")
        except Exception as e:
            logger.error(f"处理分镜设置按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"分镜设置功能出错: {str(e)}")
    
    def update_shot_image(self, row_index, image_path):
        """更新分镜表格中指定行的图片"""
        try:
            logger.info(f"更新第{row_index+1}行的分镜图片: {image_path}")
            
            # 如果父窗口有分镜表格，更新表格中的图片
            if (self.parent_window and 
                hasattr(self.parent_window, 'shots_table') and 
                self.parent_window.shots_table is not None):
                
                table = self.parent_window.shots_table
                
                # 检查表格行数与数据是否同步
                if (hasattr(self.parent_window, 'shots_data') and 
                    self.parent_window.shots_data and 
                    table.rowCount() != len(self.parent_window.shots_data)):
                    
                    logger.warning(f"表格行数不匹配，开始同步: {table.rowCount()} -> {len(self.parent_window.shots_data)}")
                    try:
                        self.parent_window.populate_shots_table_data(self.parent_window.shots_data)
                        logger.info(f"表格同步完成，新行数: {table.rowCount()}")
                    except Exception as sync_error:
                        logger.error(f"表格同步失败: {sync_error}")
                        return False
                
                if 0 <= row_index < table.rowCount():
                    # 图片列是第4列（索引为4）
                    from PyQt5.QtWidgets import QTableWidgetItem
                    from PyQt5.QtGui import QPixmap
                    from PyQt5.QtCore import Qt
                    
                    # 创建图片项
                    item = QTableWidgetItem(image_path)  # 设置DisplayRole数据为图片路径
                    if os.path.exists(image_path):
                        # 加载图片并设置为缩略图
                        pixmap = QPixmap(image_path)
                        if not pixmap.isNull():
                            # 缩放图片到合适大小
                            scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            item.setData(Qt.DecorationRole, scaled_pixmap)  # 设置DecorationRole数据为图片对象
                            item.setToolTip(f"图片路径: {image_path}")
                            logger.info(f"成功设置第{row_index+1}行的图片")
                        else:
                            logger.warning(f"第{row_index+1}行图片加载失败: {image_path}")
                    else:
                        logger.warning(f"第{row_index+1}行图片文件不存在: {image_path}")
                    
                    # 设置到表格中
                    table.setItem(row_index, 4, item)
                    
                    # 调整行高以适应图片
                    table.setRowHeight(row_index, 120)
                    
                    logger.info(f"第{row_index+1}行分镜图片更新完成")
                    return True
                else:
                    logger.debug(f"行索引超出范围: {row_index}, 表格行数: {table.rowCount()}")
                    return False
            else:
                logger.debug("未找到分镜表格，无法更新图片")
                return False
                
        except Exception as e:
            logger.error(f"更新分镜图片时发生错误: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False
    

    
    def get_prompt_for_row(self, row_index):
        """获取指定行的提示词内容"""
        try:
            # 如果当前在分镜表格视图中，从父窗口的分镜表格获取数据
            if (self.parent_window and 
                hasattr(self.parent_window, 'shots_table') and 
                self.parent_window.shots_table is not None):
                
                table = self.parent_window.shots_table
                if 0 <= row_index < table.rowCount():
                    # 提示词列是第3列（索引为3）
                    item = table.item(row_index, 3)
                    if item and item.text().strip():
                        return item.text().strip()
            
            # 如果没有找到提示词，返回空字符串
            return ""
        except Exception as e:
            logger.error(f"获取提示词时发生错误: {e}")
            return ""
    
    def get_current_style(self):
        """获取当前选择的风格"""
        try:
            if hasattr(self, 'style_combo') and self.style_combo:
                return self.style_combo.currentText()
            return "默认"
        except Exception as e:
            logger.error(f"获取当前风格时发生错误: {e}")
            return "默认"
    
    def on_style_changed(self, style_text):
        """风格选择变化时的处理"""
        logger.info(f"用户选择了新风格: {style_text}")
        self.save_style_selection(style_text)
    
    def save_style_selection(self, style_text):
        """保存风格选择到配置文件"""
        try:
            if hasattr(self.parent_window, 'config_manager'):
                config = self.parent_window.config_manager.config
                if 'ui_settings' not in config:
                    config['ui_settings'] = {}
                config['ui_settings']['selected_style'] = style_text
                self.parent_window.config_manager.save_config(config) # 传递config数据
                logger.debug(f"风格选择已保存: {style_text}")
        except Exception as e:
            logger.error(f"保存风格选择失败: {e}")
    
    def restore_style_selection(self):
        """恢复上次选择的风格"""
        try:
            if hasattr(self.parent_window, 'config_manager'):
                config = self.parent_window.config_manager.config
                saved_style = config.get('ui_settings', {}).get('selected_style', '吉卜力风格')
                
                # 查找并设置保存的风格
                for i in range(self.style_combo.count()):
                    if self.style_combo.itemText(i) == saved_style:
                        self.style_combo.setCurrentIndex(i)
                        logger.info(f"恢复风格选择: {saved_style}")
                        break
                else:
                    # 如果没找到保存的风格，默认选择吉卜力风格
                    for i in range(self.style_combo.count()):
                        if self.style_combo.itemText(i) == '吉卜力风格':
                            self.style_combo.setCurrentIndex(i)
                            logger.info("使用默认风格: 吉卜力风格")
                            break
        except Exception as e:
            logger.error(f"恢复风格选择失败: {e}")
            # 出错时默认选择吉卜力风格
            for i in range(self.style_combo.count()):
                if self.style_combo.itemText(i) == '吉卜力风格':
                    self.style_combo.setCurrentIndex(i)
                    break
    
    def get_input_text(self):
        """获取输入文本"""
        return self.text_input.toPlainText()
    
    def get_output_text(self):
        """获取输出文本"""
        return self.output_text.toPlainText()
    
    def set_output_text(self, text):
        """设置输出文本"""
        self.output_text.setPlainText(text)
    
    def create_operation_buttons(self, row_index):
        """为指定行创建操作按钮组件"""
        from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
        
        # 创建按钮容器
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(5, 2, 5, 2)
        button_layout.setSpacing(3)
        
        # 绘图按钮
        draw_btn = QPushButton("绘图")
        draw_btn.setProperty("class", "draw-button")
        draw_btn.clicked.connect(lambda: self.handle_draw_btn(row_index))
        button_layout.addWidget(draw_btn)
        
        # 配音按钮
        voice_btn = QPushButton("配音")
        voice_btn.setProperty("class", "voice-button")
        voice_btn.clicked.connect(lambda: self.handle_voice_btn(row_index))
        button_layout.addWidget(voice_btn)
        
        # 试听按钮（初始隐藏）
        preview_btn = QPushButton("试听")
        preview_btn.setProperty("class", "preview-button")
        preview_btn.clicked.connect(lambda: self.handle_preview_btn(row_index))
        preview_btn.setVisible(False)  # 初始隐藏
        button_layout.addWidget(preview_btn)
        
        # 存储试听按钮引用，用于后续显示/隐藏
        if not hasattr(self, 'preview_buttons'):
            self.preview_buttons = {}
        self.preview_buttons[row_index] = preview_btn
        
        # 检查是否已有配音文件，如果有则显示试听按钮
        self._check_and_show_preview_button(row_index, preview_btn)
        
        # 分镜设置按钮
        setting_btn = QPushButton("分镜设置")
        setting_btn.setProperty("class", "setting-button")
        setting_btn.clicked.connect(lambda: self.handle_shot_setting_btn(row_index))
        button_layout.addWidget(setting_btn)
        
        return button_widget
    
    def handle_draw_btn(self, row_index):
        """处理绘图按钮点击事件"""
        try:
            logger.info(f"用户点击第{row_index+1}行的绘图按钮")
            
            # 获取该行的提示词
            prompt = self.get_prompt_for_row(row_index)
            logger.debug(f"第{row_index+1}行原始提示词: {prompt}")
            
            if not prompt:
                logger.warning(f"第{row_index+1}行没有提示词内容，无法生成图片")
                QMessageBox.warning(self, "警告", f"第{row_index+1}行没有提示词内容")
                return

            # 获取当前选择的风格
            current_style = self.get_current_style()
            logger.info(f"当前选择的风格: {current_style}")

            # 显示进度提示
            logger.debug(f"显示第{row_index+1}行图片生成进度提示")
            self.show_progress(f"正在为第{row_index+1}行生成图片...")
            
            # 在底部状态栏立即显示"正在生图"状态
            if self.parent_window and hasattr(self.parent_window, 'log_output_bottom'):
                status_message = f"🎨 正在生图 | 第{row_index+1}行 | 提示词: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
                self.parent_window.log_output_bottom.appendPlainText(status_message)
                # 滚动到底部显示最新信息
                self.parent_window.log_output_bottom.verticalScrollBar().setValue(
                    self.parent_window.log_output_bottom.verticalScrollBar().maximum()
                )

            # 调用父窗口的绘图处理方法，传递行索引和提示词
            if self.parent_window and hasattr(self.parent_window, 'process_draw_request'):
                logger.info(f"开始处理第{row_index+1}行的绘图请求，提示词: {prompt}")
                self.parent_window.process_draw_request(row_index, prompt)
            else:
                logger.error("无法找到绘图处理方法，父窗口或process_draw_request方法不存在")
                self.hide_progress()
                QMessageBox.warning(self, "错误", "无法找到绘图处理方法")
                
        except Exception as e:
            self.hide_progress()
            logger.error(f"处理绘图按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"绘图功能出错: {str(e)}")
    
    def handle_voice_btn(self, row_index):
        """处理配音按钮点击事件"""
        try:
            # 获取当前行的文案内容
            text_item = self.table_widget.item(row_index, 0)  # 文案列
            if not text_item or not text_item.text().strip():
                QMessageBox.warning(self, "警告", "当前分镜没有文案内容，无法进行配音")
                return
            
            text_content = text_item.text().strip()
            
            # 导入AI配音对话框
            from src.gui.ai_voice_dialog import AIVoiceDialog
            
            # 创建并显示AI配音对话框
            dialog = AIVoiceDialog(self, text_content, row_index)
            if dialog.exec_() == QDialog.Accepted:
                # 用户确认生成，获取生成结果
                result = dialog.get_generation_result()
                if result and result.get('success'):
                    # 更新表格中的语音列信息
                     voice_item = self.table_widget.item(row_index, 6)  # 语音列
                     if voice_item:
                         voice_item.setText(f"已生成: {os.path.basename(result['audio_file'])}")
                     else:
                         voice_item = QTableWidgetItem(f"已生成: {os.path.basename(result['audio_file'])}")
                         self.table_widget.setItem(row_index, 6, voice_item)
                     
                     # 更新分镜数据中的语音文件路径
                     if hasattr(self.parent_window, 'shots_data') and self.parent_window.shots_data and row_index < len(self.parent_window.shots_data):
                         self.parent_window.shots_data[row_index]['voice_file'] = result['audio_file']
                         # 自动保存项目
                         self.parent_window.save_current_project()
                         logger.info(f"已更新第{row_index+1}行分镜的语音文件: {result['audio_file']}")
                     
                     # 显示试听按钮
                     if hasattr(self, 'preview_buttons') and row_index in self.preview_buttons:
                         self.preview_buttons[row_index].setVisible(True)
                         logger.info(f"第{row_index+1}行试听按钮已显示")
                     
                     QMessageBox.information(self, "成功", "语音生成完成！")
                elif result:
                    QMessageBox.warning(self, "错误", f"语音生成失败: {result.get('error', '未知错误')}")
                    
        except ImportError as e:
            QMessageBox.critical(self, "错误", f"无法加载AI配音模块: {str(e)}")
        except Exception as e:
            logger.error(f"处理配音按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"配音功能出错: {str(e)}")
    
    def handle_preview_btn(self, row_index):
        """处理试听按钮点击事件"""
        try:
            # 获取配音文件路径
            voice_file = None
            
            # 从分镜数据中获取语音文件路径
            if hasattr(self.parent_window, 'shots_data') and self.parent_window.shots_data and row_index < len(self.parent_window.shots_data):
                voice_file = self.parent_window.shots_data[row_index].get('voice_file')
            
            if not voice_file or not os.path.exists(voice_file):
                QMessageBox.warning(self, "警告", "未找到配音文件，请先生成配音")
                return
            
            # 播放音频文件
            self._play_audio_file(voice_file)
            logger.info(f"开始播放第{row_index+1}行的配音文件: {voice_file}")
            
        except Exception as e:
            logger.error(f"处理试听按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"试听功能出错: {str(e)}")
    
    def _play_audio_file(self, file_path: str):
        """播放音频文件
        
        Args:
            file_path: 音频文件路径
        """
        try:
            import platform
            import subprocess
            
            system = platform.system()
            logger.debug(f"尝试播放音频文件: {file_path}, 系统: {system}")
            
            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":  # macOS
                subprocess.call(["open", file_path])
            else:  # Linux
                subprocess.call(["xdg-open", file_path])
                
        except Exception as e:
            logger.warning(f"播放音频文件失败: {e}")
            QMessageBox.warning(self, "警告", f"无法播放音频文件: {str(e)}")
    
    def _check_and_show_preview_button(self, row_index, preview_btn):
        """检查是否已有配音文件，如果有则显示试听按钮
        
        Args:
            row_index: 行索引
            preview_btn: 试听按钮对象
        """
        try:
            # 从分镜数据中获取语音文件路径
            if hasattr(self.parent_window, 'shots_data') and self.parent_window.shots_data and row_index < len(self.parent_window.shots_data):
                voice_file = self.parent_window.shots_data[row_index].get('voice_file')
                if voice_file and os.path.exists(voice_file):
                    preview_btn.setVisible(True)
                    logger.debug(f"第{row_index+1}行已有配音文件，显示试听按钮: {voice_file}")
                else:
                    preview_btn.setVisible(False)
            else:
                preview_btn.setVisible(False)
        except Exception as e:
            logger.warning(f"检查配音文件时发生错误: {e}")
            preview_btn.setVisible(False)
    
    def handle_shot_setting_btn(self, row_index):
        """处理分镜设置按钮点击事件"""
        try:
            # 这里将实现分镜设置功能
            QMessageBox.information(self, "提示", f"分镜设置功能 - 第{row_index+1}行\n\n此功能正在开发中，敬请期待！")
        except Exception as e:
            logger.error(f"处理分镜设置按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"分镜设置功能出错: {str(e)}")
    
    def update_shot_image(self, row_index, image_path):
        """更新分镜表格中指定行的图片"""
        try:
            logger.info(f"更新第{row_index+1}行的分镜图片: {image_path}")
            
            # 如果父窗口有分镜表格，更新表格中的图片
            if (self.parent_window and 
                hasattr(self.parent_window, 'shots_table') and 
                self.parent_window.shots_table is not None):
                
                table = self.parent_window.shots_table
                
                # 检查表格行数与数据是否同步
                if (hasattr(self.parent_window, 'shots_data') and 
                    self.parent_window.shots_data and 
                    table.rowCount() != len(self.parent_window.shots_data)):
                    
                    logger.warning(f"表格行数不匹配，开始同步: {table.rowCount()} -> {len(self.parent_window.shots_data)}")
                    try:
                        self.parent_window.populate_shots_table_data(self.parent_window.shots_data)
                        logger.info(f"表格同步完成，新行数: {table.rowCount()}")
                    except Exception as sync_error:
                        logger.error(f"表格同步失败: {sync_error}")
                        return False
                
                if 0 <= row_index < table.rowCount():
                    # 图片列是第4列（索引为4）
                    from PyQt5.QtWidgets import QTableWidgetItem
                    from PyQt5.QtGui import QPixmap
                    from PyQt5.QtCore import Qt
                    
                    # 创建图片项
                    item = QTableWidgetItem(image_path)  # 设置DisplayRole数据为图片路径
                    if os.path.exists(image_path):
                        # 加载图片并设置为缩略图
                        pixmap = QPixmap(image_path)
                        if not pixmap.isNull():
                            # 缩放图片到合适大小
                            scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            item.setData(Qt.DecorationRole, scaled_pixmap)  # 设置DecorationRole数据为图片对象
                            item.setToolTip(f"图片路径: {image_path}")
                            logger.info(f"成功设置第{row_index+1}行的图片")
                        else:
                            logger.warning(f"第{row_index+1}行图片加载失败: {image_path}")
                    else:
                        logger.warning(f"第{row_index+1}行图片文件不存在: {image_path}")
                    
                    # 设置到表格中
                    table.setItem(row_index, 4, item)
                    
                    # 调整行高以适应图片
                    table.setRowHeight(row_index, 120)
                    
                    logger.info(f"第{row_index+1}行分镜图片更新完成")
                    return True
                else:
                    logger.debug(f"行索引超出范围: {row_index}, 表格行数: {table.rowCount()}")
                    return False
            else:
                logger.debug("未找到分镜表格，无法更新图片")
                return False
                
        except Exception as e:
            logger.error(f"更新分镜图片时发生错误: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False
    

    
    def get_prompt_for_row(self, row_index):
        """获取指定行的提示词内容"""
        try:
            # 如果当前在分镜表格视图中，从父窗口的分镜表格获取数据
            if (self.parent_window and 
                hasattr(self.parent_window, 'shots_table') and 
                self.parent_window.shots_table is not None):
                
                table = self.parent_window.shots_table
                if 0 <= row_index < table.rowCount():
                    # 提示词列是第3列（索引为3）
                    item = table.item(row_index, 3)
                    if item and item.text().strip():
                        return item.text().strip()
            
            # 如果没有找到提示词，返回空字符串
            return ""
        except Exception as e:
            logger.error(f"获取提示词时发生错误: {e}")
            return ""
    
    def get_current_style(self):
        """获取当前选择的风格"""
        try:
            if hasattr(self, 'style_combo') and self.style_combo:
                return self.style_combo.currentText()
            return "默认"
        except Exception as e:
            logger.error(f"获取当前风格时发生错误: {e}")
            return "默认"
    
    def on_style_changed(self, style_text):
        """风格选择变化时的处理"""
        logger.info(f"用户选择了新风格: {style_text}")
        self.save_style_selection(style_text)
    
    def save_style_selection(self, style_text):
        """保存风格选择到配置文件"""
        try:
            if hasattr(self.parent_window, 'config_manager'):
                config = self.parent_window.config_manager.config
                if 'ui_settings' not in config:
                    config['ui_settings'] = {}
                config['ui_settings']['selected_style'] = style_text
                self.parent_window.config_manager.save_config(config) # 传递config数据
                logger.debug(f"风格选择已保存: {style_text}")
        except Exception as e:
            logger.error(f"保存风格选择失败: {e}")
    
    def restore_style_selection(self):
        """恢复上次选择的风格"""
        try:
            if hasattr(self.parent_window, 'config_manager'):
                config = self.parent_window.config_manager.config
                saved_style = config.get('ui_settings', {}).get('selected_style', '吉卜力风格')
                
                # 查找并设置保存的风格
                for i in range(self.style_combo.count()):
                    if self.style_combo.itemText(i) == saved_style:
                        self.style_combo.setCurrentIndex(i)
                        logger.info(f"恢复风格选择: {saved_style}")
                        break
                else:
                    # 如果没找到保存的风格，默认选择吉卜力风格
                    for i in range(self.style_combo.count()):
                        if self.style_combo.itemText(i) == '吉卜力风格':
                            self.style_combo.setCurrentIndex(i)
                            logger.info("使用默认风格: 吉卜力风格")
                            break
        except Exception as e:
            logger.error(f"恢复风格选择失败: {e}")
            # 出错时默认选择吉卜力风格
            for i in range(self.style_combo.count()):
                if self.style_combo.itemText(i) == '吉卜力风格':
                    self.style_combo.setCurrentIndex(i)
                    break
    
    def get_input_text(self):
        """获取输入文本"""
        return self.text_input.toPlainText()
    
    def get_output_text(self):
        """获取输出文本"""
        return self.output_text.toPlainText()
    
    def set_output_text(self, text):
        """设置输出文本"""
        self.output_text.setPlainText(text)
    
    def create_operation_buttons(self, row_index):
        """为指定行创建操作按钮组件"""
        from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
        
        # 创建按钮容器
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(5, 2, 5, 2)
        button_layout.setSpacing(3)
        
        # 绘图按钮
        draw_btn = QPushButton("绘图")
        draw_btn.setProperty("class", "draw-button")
        draw_btn.clicked.connect(lambda: self.handle_draw_btn(row_index))
        button_layout.addWidget(draw_btn)
        
        # 配音按钮
        voice_btn = QPushButton("配音")
        voice_btn.setProperty("class", "voice-button")
        voice_btn.clicked.connect(lambda: self.handle_voice_btn(row_index))
        button_layout.addWidget(voice_btn)
        
        # 试听按钮（初始隐藏）
        preview_btn = QPushButton("试听")
        preview_btn.setProperty("class", "preview-button")
        preview_btn.clicked.connect(lambda: self.handle_preview_btn(row_index))
        preview_btn.setVisible(False)  # 初始隐藏
        button_layout.addWidget(preview_btn)
        
        # 存储试听按钮引用，用于后续显示/隐藏
        if not hasattr(self, 'preview_buttons'):
            self.preview_buttons = {}
        self.preview_buttons[row_index] = preview_btn
        
        # 检查是否已有配音文件，如果有则显示试听按钮
        self._check_and_show_preview_button(row_index, preview_btn)
        
        # 分镜设置按钮
        setting_btn = QPushButton("分镜设置")
        setting_btn.setProperty("class", "setting-button")
        setting_btn.clicked.connect(lambda: self.handle_shot_setting_btn(row_index))
        button_layout.addWidget(setting_btn)
        
        return button_widget
    
    def handle_draw_btn(self, row_index):
        """处理绘图按钮点击事件"""
        try:
            logger.info(f"用户点击第{row_index+1}行的绘图按钮")
            
            # 获取该行的提示词
            prompt = self.get_prompt_for_row(row_index)
            logger.debug(f"第{row_index+1}行原始提示词: {prompt}")
            
            if not prompt:
                logger.warning(f"第{row_index+1}行没有提示词内容，无法生成图片")
                QMessageBox.warning(self, "警告", f"第{row_index+1}行没有提示词内容")
                return

            # 获取当前选择的风格
            current_style = self.get_current_style()
            logger.info(f"当前选择的风格: {current_style}")

            # 显示进度提示
            logger.debug(f"显示第{row_index+1}行图片生成进度提示")
            self.show_progress(f"正在为第{row_index+1}行生成图片...")
            
            # 在底部状态栏立即显示"正在生图"状态
            if self.parent_window and hasattr(self.parent_window, 'log_output_bottom'):
                status_message = f"🎨 正在生图 | 第{row_index+1}行 | 提示词: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
                self.parent_window.log_output_bottom.appendPlainText(status_message)
                # 滚动到底部显示最新信息
                self.parent_window.log_output_bottom.verticalScrollBar().setValue(
                    self.parent_window.log_output_bottom.verticalScrollBar().maximum()
                )

            # 调用父窗口的绘图处理方法，传递行索引和提示词
            if self.parent_window and hasattr(self.parent_window, 'process_draw_request'):
                logger.info(f"开始处理第{row_index+1}行的绘图请求，提示词: {prompt}")
                self.parent_window.process_draw_request(row_index, prompt)
            else:
                logger.error("无法找到绘图处理方法，父窗口或process_draw_request方法不存在")
                self.hide_progress()
                QMessageBox.warning(self, "错误", "无法找到绘图处理方法")
                
        except Exception as e:
            self.hide_progress()
            logger.error(f"处理绘图按钮点击时发生错误: {e}")
            QMessageBox.critical(self, "错误", f"绘图功能出错: {str(e)}")
    
    # 线程回调方法
    
    def _on_shots_generated(self, shots_data):
        """分镜生成完成回调"""
        try:
            # 保存分镜数据到主窗口
            if hasattr(self, 'parent_window') and self.parent_window:
                self.parent_window.shots_data = shots_data
                logger.debug(f"分镜数据已保存到主窗口，共 {len(shots_data)} 个分镜")
            
            # 保存分镜数据到项目文件夹
            if self.current_project_root and shots_data:
                try:
                    shots_dir = os.path.join(self.current_project_root, 'shots')
                    os.makedirs(shots_dir, exist_ok=True)
                    shots_file = os.path.join(shots_dir, 'shots.json')
                    
                    with open(shots_file, 'w', encoding='utf-8') as f:
                        json.dump(shots_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"分镜数据已保存到: {shots_file}")
                except Exception as e:
                    logger.error(f"保存分镜数据失败: {e}")
            
            # 自动保存项目状态
            self._auto_save_project()
            
            self.show_shots_table(shots_data)
            logger.info(f"成功生成 {len(shots_data)} 个分镜并已自动保存项目")
        except Exception as e:
            logger.error(f"处理分镜生成完成回调时发生错误: {e}")
    
    def _on_shots_error(self, error_msg):
        """分镜生成错误回调"""
        QMessageBox.critical(self, "错误", error_msg)
    
    def _on_shots_finished(self):
        """分镜生成线程结束回调"""
        self._reset_shots_ui()
    
    def _reset_shots_ui(self):
        """重置分镜生成UI状态"""
        self.is_generating = False
        self.stop_generation = False
        self.generate_shots_btn.setEnabled(True)
        self.generate_shots_btn.setText("生成分镜")
        self.stop_generate_btn.setEnabled(False)
        self.hide_progress("storyboard")
    
    def get_current_settings(self):
        """获取当前文本转镜头设置"""
        try:
            settings = {
                'llm_enabled': hasattr(self, 'llm_api') and self.llm_api is not None,
                'current_project': self.current_project_name,
                'generation_status': self.is_generating
            }
            return settings
        except Exception as e:
            logger.error(f"获取文本转镜头设置失败: {e}")
            return {}
