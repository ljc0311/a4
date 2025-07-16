# -*- coding: utf-8 -*-
"""
分镜脚本图像生成工作标签页
用于批量生成分镜脚本中的图像，支持场景分组和镜头管理
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QLabel, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QCheckBox, QProgressBar, QFrame, QScrollArea, QGridLayout,
    QSpacerItem, QSizePolicy, QMessageBox, QFileDialog,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QSlider,
    QLineEdit, QFormLayout, QProgressDialog, QInputDialog, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QIcon

from src.utils.logger import logger
from src.processors.image_processor import ImageGenerationConfig
from src.processors.consistency_enhanced_image_processor import ConsistencyEnhancedImageProcessor
from src.utils.shot_id_manager import ShotIDManager, ShotMapping

class StoryboardImageGenerationTab(QWidget):
    """
    分镜脚本图像生成工作标签页
    """
    
    # 信号定义
    image_generated = pyqtSignal(str, str)  # scene_id, shot_id
    batch_progress = pyqtSignal(int, int)   # current, total
    generation_finished = pyqtSignal()
    
    def __init__(self, app_controller=None, project_manager=None, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.project_manager = project_manager
        self.parent_window = parent

        # 数据存储
        self.storyboard_data = []
        self.selected_items = set()
        self.generation_queue = []
        self.is_generating = False

        # 🔧 新增：配音优先工作流程数据
        self.voice_data = []  # 存储来自配音模块的数据
        self.workflow_mode = "traditional"  # traditional | voice_first
        self.failed_generations = []  # 记录失败的图像生成

        # 🔧 新增：统一镜头ID管理器
        self.shot_id_manager = ShotIDManager()

        # 🔧 新增：工作流程状态管理
        self.workflow_status = {
            'voice_data_received': False,
            'enhanced_descriptions_applied': False,
            'current_mode': 'traditional'
        }
        
        # 初始化图像生成服务
        self.image_generation_service = None
        self._init_image_generation_service()
        
        # 初始化UI
        self.init_ui()
        self.load_storyboard_data()

        # 连接项目管理器信号（如果存在）
        if self.project_manager and hasattr(self.project_manager, 'project_loaded'):
            self.project_manager.project_loaded.connect(self.on_project_loaded)

        # 🔧 新增：检测并设置工作流程模式
        self._detect_and_set_workflow_mode()

        # 设置自动保存定时器
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.auto_save_settings)
        self.auto_save_delay = 2000  # 2秒延迟

        # 延迟加载项目设置，确保UI完全初始化后再加载
        QTimer.singleShot(100, self.load_all_settings_from_project)

    def get_selected_style(self):
        """获取用户选择的风格"""
        return self.style_combo.currentText() if hasattr(self, 'style_combo') else "电影风格"

    def load_all_settings_from_project(self):
        """从项目设置中加载所有设置"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                logger.info("无项目，使用默认设置")
                self.load_default_settings()
                return

            project_data = self.project_manager.current_project

            # 兼容不同的项目数据结构
            if hasattr(project_data, 'data'):
                data = project_data.data
            else:
                data = project_data.get("data", {})

            # 优先使用新的数据结构
            image_settings = data.get("image_generation", {}).get("settings", {})

            # 如果新结构不存在，尝试从旧结构加载
            if not image_settings:
                logger.info("新数据结构不存在，尝试从旧结构加载设置")
                old_settings = project_data.get("image_generation_settings", {})
                if old_settings:
                    # 转换旧设置到新格式
                    image_settings = self.migrate_old_settings(old_settings)
                    # 保存到新结构
                    self.save_migrated_settings(image_settings)
                    logger.info("已迁移旧设置到新数据结构")

            if not image_settings:
                logger.info("项目中无图像生成设置，使用默认设置")
                self.load_default_settings()
                return

            # 加载所有设置
            self.load_settings_from_dict(image_settings)
            logger.info("从项目设置加载所有图像生成设置")

        except Exception as e:
            logger.error(f"加载项目设置失败: {e}")
            self.load_default_settings()

    def load_settings_from_dict(self, settings: dict):
        """从设置字典加载UI设置"""
        try:
            # 阻止信号触发，避免在加载时保存设置
            self.block_signals(True)

            # 风格设置
            if hasattr(self, 'style_combo') and "style" in settings:
                style = settings["style"]
                for i in range(self.style_combo.count()):
                    if self.style_combo.itemText(i) == style:
                        self.style_combo.setCurrentText(style)
                        break

            # 引擎设置
            if hasattr(self, 'engine_combo') and "engine" in settings:
                engine = settings["engine"]
                logger.info(f"尝试加载引擎设置: {engine}")

                # 首先尝试通过itemData匹配（精确匹配）
                found = False
                for i in range(self.engine_combo.count()):
                    item_data = self.engine_combo.itemData(i)
                    if item_data == engine:
                        self.engine_combo.setCurrentIndex(i)
                        logger.info(f"通过itemData匹配到引擎: {self.engine_combo.itemText(i)}")
                        found = True
                        break

                # 如果精确匹配失败，尝试文本匹配（模糊匹配）
                if not found:
                    for i in range(self.engine_combo.count()):
                        item_text = self.engine_combo.itemText(i)
                        if engine in item_text or item_text in engine:
                            self.engine_combo.setCurrentIndex(i)
                            logger.info(f"通过文本匹配到引擎: {item_text}")
                            found = True
                            break

                if not found:
                    logger.warning(f"未找到匹配的引擎: {engine}")
                    # 列出所有可用引擎供调试
                    available_engines = []
                    for i in range(self.engine_combo.count()):
                        available_engines.append(f"{self.engine_combo.itemText(i)} ({self.engine_combo.itemData(i)})")
                    logger.info(f"可用引擎: {available_engines}")

            # 尺寸设置
            if hasattr(self, 'width_spin') and "width" in settings:
                self.width_spin.setValue(settings["width"])
            if hasattr(self, 'height_spin') and "height" in settings:
                self.height_spin.setValue(settings["height"])

            # 高级参数
            if hasattr(self, 'steps_spin') and "steps" in settings:
                self.steps_spin.setValue(settings["steps"])
            if hasattr(self, 'cfg_spin') and "cfg_scale" in settings:
                self.cfg_spin.setValue(settings["cfg_scale"])
            if hasattr(self, 'seed_combo') and "seed_mode" in settings:
                self.seed_combo.setCurrentText(settings["seed_mode"])
            if hasattr(self, 'sampler_combo') and "sampler" in settings:
                sampler = settings["sampler"]
                for i in range(self.sampler_combo.count()):
                    if self.sampler_combo.itemText(i) == sampler:
                        self.sampler_combo.setCurrentIndex(i)
                        break
            if hasattr(self, 'negative_prompt_text') and "negative_prompt" in settings:
                self.negative_prompt_text.setPlainText(settings["negative_prompt"])

            # 批处理设置
            if hasattr(self, 'batch_size_spin') and "batch_size" in settings:
                self.batch_size_spin.setValue(settings["batch_size"])
            if hasattr(self, 'retry_count_spin') and "retry_count" in settings:
                self.retry_count_spin.setValue(settings["retry_count"])
            if hasattr(self, 'delay_spin') and "delay" in settings:
                self.delay_spin.setValue(settings["delay"])
            if hasattr(self, 'concurrent_tasks_spin') and "concurrent_tasks" in settings:
                self.concurrent_tasks_spin.setValue(settings["concurrent_tasks"])

            # Pollinations特有设置
            if hasattr(self, 'pollinations_model_combo') and "model" in settings:
                model = settings["model"]
                for i in range(self.pollinations_model_combo.count()):
                    if self.pollinations_model_combo.itemText(i) == model:
                        self.pollinations_model_combo.setCurrentIndex(i)
                        break
            if hasattr(self, 'pollinations_enhance_check') and "enhance" in settings:
                self.pollinations_enhance_check.setChecked(settings["enhance"])
            if hasattr(self, 'pollinations_logo_check') and "logo" in settings:
                self.pollinations_logo_check.setChecked(settings["logo"])

            # 恢复信号
            self.block_signals(False)

            # 触发引擎切换事件以更新UI显示
            if hasattr(self, 'engine_combo'):
                self.on_engine_changed(self.engine_combo.currentText())

        except Exception as e:
            logger.error(f"从设置字典加载设置失败: {e}")
            self.block_signals(False)

    def load_default_settings(self):
        """加载默认设置"""
        try:
            self.block_signals(True)

            # 设置默认值
            if hasattr(self, 'style_combo'):
                self.style_combo.setCurrentText("电影风格")
            if hasattr(self, 'engine_combo'):
                self.engine_combo.setCurrentIndex(0)  # 第一个引擎
            if hasattr(self, 'width_spin'):
                self.width_spin.setValue(1024)
            if hasattr(self, 'height_spin'):
                self.height_spin.setValue(1024)
            if hasattr(self, 'steps_spin'):
                self.steps_spin.setValue(20)
            if hasattr(self, 'cfg_spin'):
                self.cfg_spin.setValue(7.5)
            if hasattr(self, 'seed_combo'):
                self.seed_combo.setCurrentText("随机")

            self.block_signals(False)
            logger.info("已加载默认设置")

        except Exception as e:
            logger.error(f"加载默认设置失败: {e}")
            self.block_signals(False)

    def block_signals(self, block: bool):
        """阻止或恢复UI组件信号"""
        components = [
            'style_combo', 'engine_combo', 'width_spin', 'height_spin',
            'steps_spin', 'cfg_spin', 'seed_combo', 'sampler_combo',
            'negative_prompt_text', 'batch_size_spin', 'retry_count_spin',
            'delay_spin', 'concurrent_tasks_spin', 'pollinations_model_combo',
            'pollinations_enhance_check', 'pollinations_logo_check'
        ]

        for component_name in components:
            if hasattr(self, component_name):
                component = getattr(self, component_name)
                if hasattr(component, 'blockSignals'):
                    component.blockSignals(block)

    def load_style_from_project(self):
        """从项目设置中加载风格（兼容性方法）"""
        try:
            if self.project_manager and self.project_manager.current_project:
                project_data = self.project_manager.current_project

                # 兼容不同的项目数据结构
                if hasattr(project_data, 'data'):
                    image_settings = project_data.data.get("image_generation", {}).get("settings", {})
                else:
                    data = project_data.get("data", project_data)
                    image_settings = data.get("image_generation", {}).get("settings", {})

                saved_style = image_settings.get("style", "电影风格")

                # 如果保存的风格在可选项中，则设置为当前选择
                if hasattr(self, 'style_combo'):
                    for i in range(self.style_combo.count()):
                        if self.style_combo.itemText(i) == saved_style:
                            self.style_combo.setCurrentText(saved_style)
                            logger.info(f"从项目设置加载风格: {saved_style}")
                            return

                # 如果没有找到匹配的风格，使用默认值
                if hasattr(self, 'style_combo'):
                    self.style_combo.setCurrentText("电影风格")
                    logger.info("使用默认风格: 电影风格")
            else:
                # 没有项目时使用默认风格
                if hasattr(self, 'style_combo'):
                    self.style_combo.setCurrentText("电影风格")
                    logger.info("无项目，使用默认风格: 电影风格")
        except Exception as e:
            logger.error(f"加载项目风格设置失败: {e}")
            if hasattr(self, 'style_combo'):
                self.style_combo.setCurrentText("电影风格")

    def save_all_settings_to_project(self):
        """保存所有设置到项目"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_data = self.project_manager.current_project

            # 兼容不同的项目数据结构
            if hasattr(project_data, 'data'):
                data = project_data.data
            else:
                if "data" not in project_data:
                    project_data["data"] = {}
                data = project_data["data"]

            # 确保图像生成设置结构存在
            if "image_generation" not in data:
                data["image_generation"] = {"images": [], "settings": {}}
            if "settings" not in data["image_generation"]:
                data["image_generation"]["settings"] = {}

            settings = data["image_generation"]["settings"]

            # 保存所有图像生成设置
            if hasattr(self, 'style_combo'):
                settings["style"] = self.style_combo.currentText()
            if hasattr(self, 'engine_combo'):
                # 保存引擎的实际标识符，而不是显示文本
                current_index = self.engine_combo.currentIndex()
                engine_data = self.engine_combo.itemData(current_index)
                if engine_data:
                    settings["engine"] = engine_data
                else:
                    # 如果没有itemData，回退到文本
                    settings["engine"] = self.engine_combo.currentText()
            if hasattr(self, 'width_spin'):
                settings["width"] = self.width_spin.value()
            if hasattr(self, 'height_spin'):
                settings["height"] = self.height_spin.value()
            if hasattr(self, 'steps_spin'):
                settings["steps"] = self.steps_spin.value()
            if hasattr(self, 'cfg_spin'):
                settings["cfg_scale"] = self.cfg_spin.value()
            if hasattr(self, 'seed_combo'):
                settings["seed_mode"] = self.seed_combo.currentText()
            if hasattr(self, 'sampler_combo'):
                settings["sampler"] = self.sampler_combo.currentText()
            if hasattr(self, 'negative_prompt_text'):
                settings["negative_prompt"] = self.negative_prompt_text.toPlainText()
            if hasattr(self, 'batch_size_spin'):
                settings["batch_size"] = self.batch_size_spin.value()
            if hasattr(self, 'retry_count_spin'):
                settings["retry_count"] = self.retry_count_spin.value()
            if hasattr(self, 'delay_spin'):
                settings["delay"] = self.delay_spin.value()
            if hasattr(self, 'concurrent_tasks_spin'):
                settings["concurrent_tasks"] = self.concurrent_tasks_spin.value()

            # Pollinations特有设置
            if hasattr(self, 'pollinations_model_combo'):
                settings["model"] = self.pollinations_model_combo.currentText()
            if hasattr(self, 'pollinations_enhance_check'):
                settings["enhance"] = self.pollinations_enhance_check.isChecked()
            if hasattr(self, 'pollinations_logo_check'):
                settings["logo"] = self.pollinations_logo_check.isChecked()

            # 标记项目已修改
            if hasattr(self.project_manager, 'mark_project_modified'):
                self.project_manager.mark_project_modified()

            logger.info("所有图像生成设置已保存到项目")
        except Exception as e:
            logger.error(f"保存设置到项目失败: {e}")

    def save_style_to_project(self, style: str):
        """保存风格到项目设置（兼容性方法）"""
        try:
            if self.project_manager and self.project_manager.current_project:
                project_data = self.project_manager.current_project

                # 兼容不同的项目数据结构
                if hasattr(project_data, 'data'):
                    data = project_data.data
                else:
                    if "data" not in project_data:
                        project_data["data"] = {}
                    data = project_data["data"]

                # 确保图像生成设置结构存在
                if "image_generation" not in data:
                    data["image_generation"] = {"images": [], "settings": {}}
                if "settings" not in data["image_generation"]:
                    data["image_generation"]["settings"] = {}

                # 保存风格设置
                data["image_generation"]["settings"]["style"] = style

                # 标记项目已修改
                if hasattr(self.project_manager, 'mark_project_modified'):
                    self.project_manager.mark_project_modified()

                logger.info(f"风格设置已保存到项目: {style}")
        except Exception as e:
            logger.error(f"保存风格设置到项目失败: {e}")

    def on_style_changed(self, style: str):
        """风格选择改变时的处理"""
        try:
            # 保存所有设置到项目
            self.save_all_settings_to_project()

            # 调用原有的参数改变处理
            self.on_parameter_changed()

            logger.info(f"用户选择风格: {style}")
        except Exception as e:
            logger.error(f"处理风格改变失败: {e}")

    def on_parameter_changed(self):
        """参数改变时的处理"""
        try:
            # 保存所有设置到项目
            self.save_all_settings_to_project()

            # 启动自动保存定时器
            if hasattr(self, 'auto_save_timer'):
                self.auto_save_timer.start(self.auto_save_delay)

        except Exception as e:
            logger.error(f"处理参数改变失败: {e}")

    def migrate_old_settings(self, old_settings: dict) -> dict:
        """迁移旧设置格式到新格式"""
        try:
            new_settings = {}

            # 引擎设置迁移
            if "engine" in old_settings:
                engine_display = old_settings["engine"]
                # 将显示名称转换为引擎标识符
                engine_mapping = {
                    "CogView-3 Flash (免费)": "cogview_3_flash",
                    "Pollinations AI (免费)": "pollinations",
                    "ComfyUI本地": "comfyui_local",
                    "ComfyUI云端": "comfyui_cloud"
                }
                new_settings["engine"] = engine_mapping.get(engine_display, "pollinations")

            # 直接映射的设置
            direct_mappings = [
                "width", "height", "steps", "cfg_scale", "seed_mode",
                "sampler", "negative_prompt", "retry_count", "delay"
            ]
            for key in direct_mappings:
                if key in old_settings:
                    new_settings[key] = old_settings[key]

            # 添加默认值
            if "style" not in new_settings:
                new_settings["style"] = "电影风格"  # 默认风格
            if "batch_size" not in new_settings:
                new_settings["batch_size"] = 1
            if "concurrent_tasks" not in new_settings:
                new_settings["concurrent_tasks"] = 3

            logger.info(f"迁移设置: {old_settings} -> {new_settings}")
            return new_settings

        except Exception as e:
            logger.error(f"迁移旧设置失败: {e}")
            return {}

    def save_migrated_settings(self, settings: dict):
        """保存迁移后的设置到新数据结构"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_data = self.project_manager.current_project

            # 确保新数据结构存在
            if hasattr(project_data, 'data'):
                data = project_data.data
            else:
                if "data" not in project_data:
                    project_data["data"] = {}
                data = project_data["data"]

            if "image_generation" not in data:
                data["image_generation"] = {"images": [], "settings": {}}
            if "settings" not in data["image_generation"]:
                data["image_generation"]["settings"] = {}

            # 保存迁移后的设置
            data["image_generation"]["settings"].update(settings)

            # 标记项目已修改
            if hasattr(self.project_manager, 'mark_project_modified'):
                self.project_manager.mark_project_modified()

            logger.info("迁移后的设置已保存到新数据结构")

        except Exception as e:
            logger.error(f"保存迁移设置失败: {e}")

    def on_project_loaded(self):
        """项目加载时的处理"""
        try:
            # 重新加载所有设置
            self.load_all_settings_from_project()

            # 重新加载分镜数据
            self.load_storyboard_data()

            logger.info("项目加载完成，已重新加载所有设置和数据")
        except Exception as e:
            logger.error(f"处理项目加载失败: {e}")

    def receive_voice_data(self, voice_data_list):
        """接收来自配音模块的数据（配音优先工作流程）"""
        try:
            logger.info(f"图像生成模块接收到 {len(voice_data_list)} 个配音数据")
            self.voice_data = voice_data_list
            self.workflow_mode = "voice_first"

            # 🔧 新增：使用配音优先工作流程处理数据
            self._process_voice_first_workflow(voice_data_list)

        except Exception as e:
            logger.error(f"接收配音数据失败: {e}")

    def _process_voice_first_workflow(self, voice_data_list):
        """处理配音优先工作流程"""
        try:
            # 导入配音-图像匹配器
            from src.core.voice_image_matcher import VoiceImageMatcher

            # 获取LLM API用于增强
            llm_api = None
            if hasattr(self, 'parent_window') and self.parent_window:
                if hasattr(self.parent_window, 'app_controller') and self.parent_window.app_controller:
                    try:
                        from src.models.llm_api import LLMApi
                        from src.utils.config_manager import ConfigManager

                        config_manager = ConfigManager()
                        llm_config = config_manager.get_llm_config()

                        if llm_config and llm_config.get('api_key'):
                            llm_api = LLMApi(
                                api_type=llm_config.get('api_type', 'tongyi'),
                                api_key=llm_config['api_key'],
                                api_url=llm_config.get('api_url', '')
                            )
                    except Exception as e:
                        logger.debug(f"获取LLM API失败: {e}")

            # 创建配音-图像匹配器
            matcher = VoiceImageMatcher(llm_api)

            # 批量生成匹配的图像提示词
            matched_storyboard_data = matcher.batch_generate_matched_prompts(voice_data_list)

            if not matched_storyboard_data:
                QMessageBox.warning(self, "警告", "生成匹配的图像提示词失败")
                return

            # 更新界面数据
            self.storyboard_data = matched_storyboard_data
            self.voice_data = voice_data_list
            self.workflow_mode = "voice_first"

            # 保存到项目数据
            if self.project_manager and self.project_manager.current_project:
                try:
                    from datetime import datetime
                    project_data = self.project_manager.get_project_data()
                    if not project_data:
                        project_data = {}

                    # 保存配音优先工作流程数据
                    project_data['voice_first_workflow'] = {
                        'storyboard_data': matched_storyboard_data,
                        'voice_data': voice_data_list,
                        'workflow_mode': 'voice_first',
                        'generated_at': str(datetime.now())
                    }

                    self.project_manager.save_project_data(project_data)
                    logger.info("配音优先工作流程数据已保存")
                except Exception as e:
                    logger.warning(f"保存工作流程数据失败: {e}")

            # 更新表格显示
            self.update_table()

            # 显示统计信息
            total_voice = len(voice_data_list)
            total_images = len(matched_storyboard_data)

            self.status_label.setText(
                f"配音优先模式：{total_voice}个配音段落 → {total_images}张图片"
            )

            # 询问是否立即开始生成
            reply = QMessageBox.question(
                self, "开始生成",
                f"已接收到 {len(voice_data_list)} 个配音段落的数据。\n\n"
                "系统已基于配音内容生成了匹配的图像提示词。\n"
                "是否立即开始批量生成图像？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 自动开始批量生成
                self.batch_generate_images()

        except Exception as e:
            logger.error(f"处理配音优先工作流程失败: {e}")
            QMessageBox.critical(self, "错误", f"处理配音数据失败: {str(e)}")

    def batch_generate_images(self):
        """批量生成图像（配音优先模式）"""
        try:
            if not self.storyboard_data:
                QMessageBox.warning(self, "警告", "没有可生成的图像数据")
                return

            # 自动选择所有项目
            for shot_data in self.storyboard_data:
                shot_data['selected'] = True

            # 更新表格显示
            self.update_table()

            # 开始批量生成
            self.generate_selected_images()

        except Exception as e:
            logger.error(f"批量生成图像失败: {e}")
            QMessageBox.critical(self, "错误", f"批量生成失败: {str(e)}")



    def _process_multi_image_positions(self, storyboard_data: List[Dict],
                                     image_requirements: Dict[int, Dict]) -> List[Dict]:
        """处理多张图像的正确显示位置"""
        try:
            processed_data = []

            for i, req in image_requirements.items():
                audio_duration = req['audio_duration']
                images = req['images']

                # 为每张图像创建单独的表格行
                for img_idx, image_info in enumerate(images):
                    # 查找对应的原始数据
                    original_data = None
                    if i < len(storyboard_data):
                        original_data = storyboard_data[i]

                    # 🔧 修复：创建图像数据，正确获取增强描述
                    # 优先从prompt.json获取真正的增强描述
                    enhanced_description = self._get_enhanced_description_for_voice_driven(original_data, i+1) if original_data else ''

                    image_data = {
                        'scene_id': original_data.get('scene_id', f'场景{(i//3)+1}') if original_data else f'场景{(i//3)+1}',
                        'scene_name': original_data.get('scene_name', f'场景{(i//3)+1}') if original_data else f'场景{(i//3)+1}',
                        'shot_id': f"{original_data.get('shot_id', f'镜头{i+1}')}_{img_idx+1}" if len(images) > 1 else original_data.get('shot_id', f'镜头{i+1}') if original_data else f'镜头{i+1}',
                        'shot_name': f"{original_data.get('shot_name', f'镜头{i+1}')}_{img_idx+1}" if len(images) > 1 else original_data.get('shot_name', f'镜头{i+1}') if original_data else f'镜头{i+1}',
                        'sequence': f"{i+1}_{img_idx+1}" if len(images) > 1 else f"{i+1}",
                        'original_description': original_data.get('original_description', '') if original_data else '',
                        'consistency_description': enhanced_description,  # 使用增强描述作为一致性描述
                        'enhanced_description': enhanced_description,  # 使用正确的增强描述
                        'status': '未生成',
                        'image_path': '',
                        'main_image_path': '',
                        'selected': True,
                        # 时间信息
                        'duration_start': image_info['start_time'],
                        'duration_end': image_info['end_time'],
                        'duration': image_info['duration'],
                        'audio_duration': audio_duration,
                        'image_index': img_idx,
                        'total_images': len(images),
                        # 配音相关信息
                        'voice_segment_index': i,
                        'voice_content': original_data.get('voice_content', '') if original_data else '',
                        'dialogue_content': original_data.get('dialogue_content', '') if original_data else '',
                        'audio_path': original_data.get('audio_path', '') if original_data else '',
                        'content_type': original_data.get('content_type', '旁白') if original_data else '旁白'
                    }

                    processed_data.append(image_data)

            logger.info(f"处理多张图像位置完成: {len(storyboard_data)}个配音段落 -> {len(processed_data)}张图像")
            return processed_data

        except Exception as e:
            logger.error(f"处理多张图像位置失败: {e}")
            return storyboard_data  # 返回原始数据作为降级方案

    def _generate_images_from_voice_data(self):
        """基于配音数据生成图像"""
        try:
            if not self.voice_data:
                logger.warning("没有配音数据可用于图像生成")
                return

            # 清空现有的分镜数据，准备基于配音数据重新生成
            self.storyboard_data = []

            # 为每个配音段落生成对应的图像数据
            for voice_segment in self.voice_data:
                # 生成基于配音内容的图像提示词
                image_prompt = self._generate_image_prompt_from_voice(voice_segment)

                # 创建图像生成数据
                shot_data = {
                    'scene_id': voice_segment.get('scene_id', ''),
                    'scene_name': voice_segment.get('scene_id', ''),
                    'shot_id': voice_segment.get('shot_id', ''),
                    'shot_name': voice_segment.get('shot_id', ''),
                    'sequence': f"{voice_segment.get('segment_index', 0) + 1}",
                    'original_description': voice_segment.get('voice_content', ''),
                    'consistency_description': '',
                    'enhanced_description': image_prompt,
                    'status': '未生成',
                    'image_path': '',
                    'main_image_path': '',
                    'selected': True,
                    # 🔧 新增：配音相关信息
                    'voice_content': voice_segment.get('voice_content', ''),
                    'dialogue_content': voice_segment.get('dialogue_content', ''),
                    'audio_path': voice_segment.get('audio_path', ''),
                    'content_type': voice_segment.get('content_type', '旁白')
                }

                self.storyboard_data.append(shot_data)

            # 更新UI显示
            self.update_table()

            # 显示提示信息
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "配音优先模式",
                f"已接收到 {len(self.voice_data)} 个配音段落的数据。\n\n"
                "系统已基于配音内容生成了匹配的图像提示词。\n"
                "是否立即开始批量生成图像？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                # 自动开始批量生成
                self.batch_generate_images()

            logger.info(f"基于配音数据生成了 {len(self.storyboard_data)} 个图像生成任务")

        except Exception as e:
            logger.error(f"基于配音数据生成图像失败: {e}")

    def _generate_image_prompt_from_voice(self, voice_segment):
        """基于配音内容生成图像提示词"""
        try:
            voice_content = voice_segment.get('voice_content', '')
            dialogue_content = voice_segment.get('dialogue_content', '')
            scene_id = voice_segment.get('scene_id', '')
            content_type = voice_segment.get('content_type', '旁白')

            # 选择主要内容
            main_content = dialogue_content if dialogue_content else voice_content

            if not main_content:
                return f"一个简单的场景, {self.get_selected_style()}, 高质量"

            # 创建简化的图像提示词
            return self._create_simple_image_prompt(main_content, scene_id)

        except Exception as e:
            logger.error(f"生成图像提示词失败: {e}")
            return f"一个简单的场景, {self.get_selected_style()}, 高质量"

    def _create_simple_image_prompt(self, content, scene_id):
        """创建简化的图像提示词"""
        try:
            # 基于内容关键词生成简单的图像描述
            content_lower = content.lower()

            # 场景关键词映射
            scene_keywords = {
                '家乡': '乡村, 农舍, 田野',
                '童年': '孩子, 温馨, 家庭',
                '梦想': '希望, 光明, 未来',
                '行动': '努力, 奋斗, 坚持',
                '努力': '学习, 工作, 专注',
                '挑战': '困难, 坚强, 克服',
                '书店': '书架, 书籍, 阅读',
                '食堂': '餐厅, 用餐, 食物',
                '学校': '教室, 学习, 校园'
            }

            # 动作关键词映射
            action_keywords = {
                '说话': '人物对话, 表情生动',
                '看书': '阅读, 书籍, 专注学习',
                '买书': '书店, 选择书籍, 购买',
                '吃饭': '用餐, 食物, 餐桌',
                '点菜': '餐厅, 菜单, 选择食物',
                '走路': '行走, 道路, 移动',
                '思考': '沉思, 表情深刻',
                '笑': '微笑, 开心, 愉快',
                '找': '寻找, 翻找, 搜索',
                '翻箱倒柜': '寻找物品, 整理房间'
            }

            # 构建基础描述
            base_description = "一个温馨的场景"

            # 添加场景关键词
            for keyword, description in scene_keywords.items():
                if keyword in content or keyword in scene_id:
                    base_description = f"{description}, {base_description}"
                    break

            # 添加动作关键词
            for keyword, description in action_keywords.items():
                if keyword in content:
                    base_description = f"{base_description}, {description}"
                    break

            # 添加风格描述
            style_suffix = f", {self.get_selected_style()}, 高质量, 细节丰富, 温暖的色调"

            return f"{base_description}{style_suffix}"

        except Exception as e:
            logger.error(f"创建简化图像提示词失败: {e}")
            return f"一个简单的温馨场景, {self.get_selected_style()}, 高质量"

    def _detect_and_set_workflow_mode(self):
        """检测并设置工作流程模式"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                self.workflow_status['current_mode'] = 'traditional'
                return

            project_data = self.project_manager.current_project
            workflow_settings = project_data.get('workflow_settings', {})

            # 检测工作流程模式
            if workflow_settings.get('mode') == 'voice_first':
                self.workflow_status['current_mode'] = 'voice_first'
                self.workflow_mode = 'voice_first'
                logger.info("检测到配音优先工作流程模式")
            else:
                self.workflow_status['current_mode'] = 'traditional'
                self.workflow_mode = 'traditional'
                logger.info("使用传统工作流程模式")

            # 检查是否已有配音数据
            voice_generation_data = project_data.get('voice_generation', {})
            if voice_generation_data.get('generated_audio'):
                self.workflow_status['voice_data_received'] = True
                logger.info("检测到已有配音数据")

        except Exception as e:
            logger.error(f"检测工作流程模式失败: {e}")
            self.workflow_status['current_mode'] = 'traditional'

    def _show_workflow_mode_warning(self):
        """显示工作流程模式警告"""
        try:
            if self.workflow_status['current_mode'] == 'voice_first':
                if not self.workflow_status['voice_data_received']:
                    from PyQt5.QtWidgets import QMessageBox
                    reply = QMessageBox.question(
                        self,
                        "配音优先模式提醒",
                        "当前项目使用配音优先工作流程。\n\n"
                        "建议您：\n"
                        "1. 先完成AI配音生成\n"
                        "2. 系统会自动基于配音内容生成匹配的图像提示词\n"
                        "3. 然后再进行图像生成\n\n"
                        "这样可以确保图像与配音内容完美匹配。\n\n"
                        "是否现在切换到AI配音界面？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        # 切换到AI配音标签页
                        self._switch_to_voice_tab()
                        return True

            return False

        except Exception as e:
            logger.error(f"显示工作流程模式警告失败: {e}")
            return False

    def _switch_to_voice_tab(self):
        """切换到AI配音标签页"""
        try:
            if self.parent_window and hasattr(self.parent_window, 'tab_widget'):
                for i in range(self.parent_window.tab_widget.count()):
                    if "AI配音" in self.parent_window.tab_widget.tabText(i):
                        self.parent_window.tab_widget.setCurrentIndex(i)
                        logger.info("已切换到AI配音标签页")
                        break
        except Exception as e:
            logger.error(f"切换到AI配音标签页失败: {e}")

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 创建全局控制区域
        self.create_global_controls(layout)
        
        # 创建主工作区域
        self.create_main_work_area(layout)
        
        # 创建状态栏
        self.create_status_bar(layout)
        
    def create_global_controls(self, parent_layout):
        """创建全局控制区域"""
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel)  # type: ignore
        controls_layout = QHBoxLayout(controls_frame)
        
        # 左侧：批量操作
        batch_group = QGroupBox("批量操作")
        batch_layout = QHBoxLayout(batch_group)
        
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_items)
        batch_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.clicked.connect(self.deselect_all_items)
        batch_layout.addWidget(self.deselect_all_btn)
        
        self.select_scene_btn = QPushButton("选择场景")
        self.select_scene_btn.clicked.connect(self.select_current_scene)
        batch_layout.addWidget(self.select_scene_btn)
        
        controls_layout.addWidget(batch_group)
        
        # 中间：生成控制
        generation_group = QGroupBox("生成控制")
        generation_layout = QVBoxLayout(generation_group)

        # 第一行：主要按钮
        main_buttons_layout = QHBoxLayout()

        self.generate_selected_btn = QPushButton("生成选中项")
        self.generate_selected_btn.clicked.connect(self.generate_selected_images)
        main_buttons_layout.addWidget(self.generate_selected_btn)

        self.generate_all_btn = QPushButton("生成全部")
        self.generate_all_btn.clicked.connect(self.generate_all_images)
        main_buttons_layout.addWidget(self.generate_all_btn)

        self.stop_generation_btn = QPushButton("停止生成")
        self.stop_generation_btn.clicked.connect(self.stop_generation)
        self.stop_generation_btn.setEnabled(False)
        main_buttons_layout.addWidget(self.stop_generation_btn)

        generation_layout.addLayout(main_buttons_layout)

        # 第二行：选项
        options_layout = QHBoxLayout()

        self.skip_existing_cb = QCheckBox("跳过已生成图片的镜头")
        self.skip_existing_cb.setChecked(True)
        self.skip_existing_cb.setToolTip("勾选后，批量生图时会自动跳过已有图片的镜头")
        options_layout.addWidget(self.skip_existing_cb)

        options_layout.addStretch()

        # 检测按钮
        self.detect_existing_btn = QPushButton("检测已生成")
        self.detect_existing_btn.clicked.connect(self.detect_existing_images)
        self.detect_existing_btn.setToolTip("检测哪些镜头已经生成了图片")
        options_layout.addWidget(self.detect_existing_btn)

        generation_layout.addLayout(options_layout)
        
        controls_layout.addWidget(generation_group)
        
        # 右侧：数据管理
        data_group = QGroupBox("数据管理")
        data_layout = QHBoxLayout(data_group)
        
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.load_storyboard_data)
        data_layout.addWidget(self.refresh_btn)
        
        self.export_btn = QPushButton("导出配置")
        self.export_btn.clicked.connect(self.export_configuration)
        data_layout.addWidget(self.export_btn)
        
        self.import_btn = QPushButton("导入配置")
        self.import_btn.clicked.connect(self.import_configuration)
        data_layout.addWidget(self.import_btn)
        
        controls_layout.addWidget(data_group)
        
        controls_layout.addStretch()
        parent_layout.addWidget(controls_frame)
        
    def create_main_work_area(self, parent_layout):
        """创建主工作区域"""
        # 创建水平分割器
        main_splitter = QSplitter(Qt.Horizontal)  # type: ignore
        
        # 左侧：分镜列表
        self.create_storyboard_list(main_splitter)
        
        # 右侧：详细面板
        self.create_detail_panels(main_splitter)
        
        # 设置分割器比例
        main_splitter.setSizes([600, 400])
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)
        
        parent_layout.addWidget(main_splitter)
        
    def create_storyboard_list(self, parent_splitter):
        """创建分镜列表"""
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        
        # 列表标题
        title_label = QLabel("分镜脚本列表")
        font = QFont("Microsoft YaHei", 12)
        font.setBold(True)
        title_label.setFont(font)
        list_layout.addWidget(title_label)
        
        # 创建表格
        self.storyboard_table = QTableWidget()
        self.setup_table_headers()
        self.storyboard_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.storyboard_table.cellClicked.connect(self.on_cell_clicked)
        list_layout.addWidget(self.storyboard_table)
        
        parent_splitter.addWidget(list_widget)
        
    def setup_table_headers(self):
        """设置表格标题"""
        # 🔧 修复：添加旁白栏，用于验证文图匹配
        headers = [
            "选择", "场景", "镜头", "旁白",
            "增强描述", "主图", "操作"
        ]

        self.storyboard_table.setColumnCount(len(headers))
        self.storyboard_table.setHorizontalHeaderLabels(headers)

        # 设置表格基本属性
        self.storyboard_table.setSelectionBehavior(QAbstractItemView.SelectRows)  # type: ignore
        self.storyboard_table.setAlternatingRowColors(True)
        self.storyboard_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # type: ignore
        self.storyboard_table.setCornerButtonEnabled(True)  # 启用角落按钮

        # 🔧 修复：设置列宽 - 允许用户自由调整所有列的大小
        header = self.storyboard_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # type: ignore  # 选择 - 保持固定
        header.setSectionResizeMode(1, QHeaderView.Interactive)  # type: ignore  # 场景 - 可调整
        header.setSectionResizeMode(2, QHeaderView.Interactive)  # type: ignore  # 镜头 - 可调整
        header.setSectionResizeMode(3, QHeaderView.Interactive)  # type: ignore  # 旁白 - 可调整
        header.setSectionResizeMode(4, QHeaderView.Interactive)  # type: ignore  # 增强描述 - 可调整
        header.setSectionResizeMode(5, QHeaderView.Interactive)  # type: ignore  # 主图 - 可调整
        header.setSectionResizeMode(6, QHeaderView.Interactive)  # type: ignore  # 操作 - 可调整

        # 连接列宽变化信号，用于动态调整图片大小
        header.sectionResized.connect(self.on_column_resized)

        # 🔧 修复：重新调整列宽，为旁白和主图列提供更多空间
        self.storyboard_table.setColumnWidth(0, 35)   # 选择 - 保持紧凑
        self.storyboard_table.setColumnWidth(1, 60)   # 场景 - 可调整
        self.storyboard_table.setColumnWidth(2, 60)   # 镜头 - 可调整
        self.storyboard_table.setColumnWidth(3, 200)  # 旁白 - 可调整
        self.storyboard_table.setColumnWidth(4, 250)  # 增强描述 - 可调整
        self.storyboard_table.setColumnWidth(5, 400)  # 主图 - 可调整，支持多张图片并排显示
        self.storyboard_table.setColumnWidth(6, 100)  # 操作 - 可调整

        # 🔧 修复：设置行高和文本换行 - 允许用户自由调整行高
        self.storyboard_table.setWordWrap(True)
        self.storyboard_table.verticalHeader().setDefaultSectionSize(180)  # 增加行高以适应多张图片并排显示
        self.storyboard_table.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)  # type: ignore  # 允许用户拖动调整行高
        self.storyboard_table.verticalHeader().setMinimumSectionSize(80)   # 设置最小行高
        self.storyboard_table.verticalHeader().setMaximumSectionSize(500)  # 设置最大行高
        
    def create_detail_panels(self, parent_splitter):
        """创建详细面板"""
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        
        # 创建标签页
        self.detail_tabs = QTabWidget()
        
        # 描述面板
        self.create_description_panel()
        
        # 参数面板
        self.create_parameters_panel()
        
        # 预览面板
        self.create_preview_panel()
        
        detail_layout.addWidget(self.detail_tabs)
        parent_splitter.addWidget(detail_widget)
        
    def create_description_panel(self):
        """创建描述面板"""
        desc_widget = QWidget()
        desc_layout = QVBoxLayout(desc_widget)
        
        # 一致性描述（现在用于显示增强后的描述）
        consistency_group = QGroupBox("一致性描述")
        consistency_layout = QVBoxLayout(consistency_group)
        
        self.consistency_desc_text = QTextEdit()
        self.consistency_desc_text.setMaximumHeight(120)
        self.consistency_desc_text.textChanged.connect(self.on_consistency_desc_changed)
        consistency_layout.addWidget(self.consistency_desc_text)
        
        # 一致性操作按钮
        consistency_btn_layout = QHBoxLayout()
        
        self.apply_consistency_btn = QPushButton("应用一致性")
        self.apply_consistency_btn.clicked.connect(self.apply_consistency)
        consistency_btn_layout.addWidget(self.apply_consistency_btn)
        
        self.reset_consistency_btn = QPushButton("重置")
        self.reset_consistency_btn.clicked.connect(self.reset_consistency)
        consistency_btn_layout.addWidget(self.reset_consistency_btn)
        
        consistency_btn_layout.addStretch()
        consistency_layout.addLayout(consistency_btn_layout)
        
        desc_layout.addWidget(consistency_group)
        
        # 增强描述
        enhanced_group = QGroupBox("增强描述")
        enhanced_layout = QVBoxLayout(enhanced_group)
        
        self.enhanced_desc_text = QTextEdit()
        self.enhanced_desc_text.setMaximumHeight(120)
        self.enhanced_desc_text.textChanged.connect(self.on_enhanced_desc_changed)
        enhanced_layout.addWidget(self.enhanced_desc_text)
        
        # 增强操作按钮
        enhanced_btn_layout = QHBoxLayout()
        
        self.enhance_desc_btn = QPushButton("智能增强")
        self.enhance_desc_btn.clicked.connect(self.enhance_description)
        enhanced_btn_layout.addWidget(self.enhance_desc_btn)
        
        self.reset_enhanced_btn = QPushButton("重置")
        self.reset_enhanced_btn.clicked.connect(self.reset_enhanced)
        enhanced_btn_layout.addWidget(self.reset_enhanced_btn)
        
        # 保存增强描述到一致性描述的按钮
        self.save_enhanced_to_consistency_btn = QPushButton("保存到一致性")
        self.save_enhanced_to_consistency_btn.clicked.connect(self.save_enhanced_to_consistency)
        enhanced_btn_layout.addWidget(self.save_enhanced_to_consistency_btn)
        
        enhanced_btn_layout.addStretch()
        enhanced_layout.addLayout(enhanced_btn_layout)
        
        desc_layout.addWidget(enhanced_group)
        
        self.detail_tabs.addTab(desc_widget, "描述编辑")
        
    def create_parameters_panel(self):
        """创建参数面板"""
        params_widget = QWidget()
        params_layout = QVBoxLayout(params_widget)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QFormLayout(scroll_widget)
        
        # 引擎选择
        engine_group = QGroupBox("图像生成引擎")
        engine_layout = QFormLayout(engine_group)
        
        self.engine_combo = QComboBox()
        self._populate_engine_list()
        self.engine_combo.currentTextChanged.connect(self.on_engine_changed)
        engine_layout.addRow("选择引擎:", self.engine_combo)
        
        # Pollinations特有设置（默认显示）
        self.pollinations_model_combo = QComboBox()
        self.pollinations_model_combo.addItems(["flux", "flux-turbo", "gptimage"])
        self.pollinations_model_combo.setCurrentText("flux")
        self.pollinations_model_combo.currentTextChanged.connect(self.on_parameter_changed)
        engine_layout.addRow("模型:", self.pollinations_model_combo)

        self.pollinations_enhance_check = QCheckBox("启用增强 (Enhance)")
        self.pollinations_enhance_check.stateChanged.connect(self.on_parameter_changed)
        engine_layout.addRow("", self.pollinations_enhance_check)

        self.pollinations_logo_check = QCheckBox("添加Logo水印")
        self.pollinations_logo_check.stateChanged.connect(self.on_parameter_changed)
        engine_layout.addRow("", self.pollinations_logo_check)

        # 引擎状态显示（仅非Pollinations引擎显示）
        self.engine_status_label = QLabel("状态: 未连接")
        self.engine_status_label.setStyleSheet("color: orange;")
        self.engine_status_label_text = QLabel("引擎状态:")
        engine_layout.addRow(self.engine_status_label_text, self.engine_status_label)

        # 连接测试按钮（仅ComfyUI显示）
        self.test_connection_btn = QPushButton("测试连接")
        self.test_connection_btn.clicked.connect(self.test_engine_connection)
        self.test_connection_btn.setVisible(False)  # 默认隐藏，仅ComfyUI显示
        self.test_connection_label_text = QLabel("连接测试:")
        self.test_connection_label_text.setVisible(False)  # 默认隐藏
        engine_layout.addRow(self.test_connection_label_text, self.test_connection_btn)
        
        scroll_layout.addRow(engine_group)
        
        # 基础参数
        basic_group = QGroupBox("基础参数")
        basic_layout = QFormLayout(basic_group)
        
        # 图像尺寸 - 支持手动输入和预设选择
        size_layout = QHBoxLayout()

        # 宽度输入框
        self.width_spin = QSpinBox()
        self.width_spin.setRange(256, 2048)
        self.width_spin.setValue(1024)
        self.width_spin.setSingleStep(64)
        self.width_spin.valueChanged.connect(self.on_parameter_changed)
        size_layout.addWidget(self.width_spin)

        size_layout.addWidget(QLabel("×"))

        # 高度输入框
        self.height_spin = QSpinBox()
        self.height_spin.setRange(256, 2048)
        self.height_spin.setValue(1024)
        self.height_spin.setSingleStep(64)
        self.height_spin.valueChanged.connect(self.on_parameter_changed)
        size_layout.addWidget(self.height_spin)

        # 预设尺寸下拉框
        self.size_preset_combo = QComboBox()
        self.size_preset_combo.addItems([
            "自定义",
            "1024×1024 (正方形)",
            "768×1344 (竖屏)",
            "864×1152 (竖屏)",
            "1344×768 (横屏)",
            "1152×864 (横屏)",
            "1440×720 (超宽)",
            "720×1440 (超高)"
        ])
        self.size_preset_combo.currentTextChanged.connect(self.on_size_preset_changed)
        size_layout.addWidget(self.size_preset_combo)

        basic_layout.addRow("尺寸:", size_layout)
        
        # 种子值设置 - 简化为只有下拉框
        self.seed_combo = QComboBox()
        self.seed_combo.addItems(["随机", "固定"])
        self.seed_combo.currentTextChanged.connect(self.on_parameter_changed)
        basic_layout.addRow("种子值:", self.seed_combo)

        # 风格选择
        self.style_combo = QComboBox()
        self.style_combo.addItems([
            "电影风格", "动漫风格", "吉卜力风格", "赛博朋克风格",
            "水彩插画风格", "像素风格", "写实摄影风格"
        ])
        # 从项目设置中加载风格，如果没有则使用默认值
        self.load_style_from_project()
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        basic_layout.addRow("生成风格:", self.style_combo)

        # 高级参数（默认隐藏，仅非Pollinations引擎显示）
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(10, 100)
        self.steps_spin.setValue(30)
        self.steps_label = QLabel("生成步数:")
        
        self.cfg_spin = QDoubleSpinBox()
        self.cfg_spin.setRange(1.0, 20.0)
        self.cfg_spin.setValue(7.5)
        self.cfg_spin.setSingleStep(0.5)
        self.cfg_label = QLabel("CFG Scale:")
        
        self.sampler_combo = QComboBox()
        self.sampler_combo.addItems([
            "DPM++ 2M Karras", "Euler a", "Euler", "LMS", 
            "Heun", "DPM2", "DPM2 a", "DPM++ SDE", "DPM++ 2M SDE"
        ])
        self.sampler_label = QLabel("采样器:")
        
        self.negative_prompt_text = QTextEdit()
        self.negative_prompt_text.setMaximumHeight(80)
        self.negative_prompt_text.setPlainText(
            "blurry, low quality, distorted, deformed, bad anatomy, "
            "bad proportions, extra limbs, cloned face, disfigured, "
            "gross proportions, malformed limbs, missing arms, missing legs"
        )
        self.negative_prompt_label = QLabel("负面描述:")
        
        # 添加到布局（默认隐藏）
        basic_layout.addRow(self.steps_label, self.steps_spin)
        basic_layout.addRow(self.cfg_label, self.cfg_spin)
        basic_layout.addRow(self.sampler_label, self.sampler_combo)
        basic_layout.addRow(self.negative_prompt_label, self.negative_prompt_text)
        
        # 默认隐藏高级参数
        self.steps_spin.setVisible(False)
        self.steps_label.setVisible(False)
        self.cfg_spin.setVisible(False)
        self.cfg_label.setVisible(False)
        self.sampler_combo.setVisible(False)
        self.sampler_label.setVisible(False)
        self.negative_prompt_text.setVisible(False)
        self.negative_prompt_label.setVisible(False)
        
        scroll_layout.addRow(basic_group)
        
        # 并发设置
        batch_group = QGroupBox("并发设置")
        batch_layout = QFormLayout(batch_group)
        
        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, 5)
        self.retry_count_spin.setValue(2)
        batch_layout.addRow("重试次数:", self.retry_count_spin)

        # 并发任务数
        self.concurrent_tasks_spin = QSpinBox()
        self.concurrent_tasks_spin.setRange(1, 10)
        self.concurrent_tasks_spin.setValue(3)
        batch_layout.addRow("并发任务数:", self.concurrent_tasks_spin)

        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 10.0)
        self.delay_spin.setValue(1.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setSuffix(" 秒")
        batch_layout.addRow("生成间隔:", self.delay_spin)
        
        scroll_layout.addRow(batch_group)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        params_layout.addWidget(scroll_area)
        
        # 参数操作按钮
        params_btn_layout = QHBoxLayout()
        
        self.save_preset_btn = QPushButton("保存设置")
        self.save_preset_btn.clicked.connect(self.save_generation_settings)
        params_btn_layout.addWidget(self.save_preset_btn)
        
        self.load_preset_btn = QPushButton("加载预设")
        self.load_preset_btn.clicked.connect(self.load_parameter_preset)
        params_btn_layout.addWidget(self.load_preset_btn)
        
        self.reset_params_btn = QPushButton("重置参数")
        self.reset_params_btn.clicked.connect(self.reset_parameters)
        params_btn_layout.addWidget(self.reset_params_btn)
        
        params_btn_layout.addStretch()
        params_layout.addLayout(params_btn_layout)
        
        self.detail_tabs.addTab(params_widget, "生成参数")

        # 初始化引擎状态显示
        self.on_engine_changed(self.engine_combo.currentText())


        
    def create_preview_panel(self):
        """创建预览面板"""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        
        # 预览图像
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)  # type: ignore
        self.preview_label.setMinimumSize(300, 300)
        self.preview_label.setStyleSheet(
            "QLabel { "
            "border: 2px dashed #ccc; "
            "background-color: #f9f9f9; "
            "color: #666; "
            "}"
        )
        self.preview_label.setText("暂无预览图像")
        preview_layout.addWidget(self.preview_label)

        # 翻页控件
        self.preview_nav_layout = QHBoxLayout()
        self.preview_nav_layout.addStretch()

        self.preview_prev_btn = QPushButton("◀ 上一张")
        self.preview_prev_btn.clicked.connect(self.preview_prev_image)
        self.preview_prev_btn.setVisible(False)
        self.preview_nav_layout.addWidget(self.preview_prev_btn)

        self.preview_page_label = QLabel("")
        self.preview_page_label.setAlignment(Qt.AlignCenter)  # type: ignore
        self.preview_page_label.setStyleSheet("font-size: 12px; margin: 0 10px;")
        self.preview_page_label.setVisible(False)
        self.preview_nav_layout.addWidget(self.preview_page_label)

        self.preview_next_btn = QPushButton("下一张 ▶")
        self.preview_next_btn.clicked.connect(self.preview_next_image)
        self.preview_next_btn.setVisible(False)
        self.preview_nav_layout.addWidget(self.preview_next_btn)

        self.preview_nav_layout.addStretch()
        preview_layout.addLayout(self.preview_nav_layout)
        
        # 预览说明
        preview_info = QLabel("预览功能：快速查看当前选中分镜的详细信息和图像，无需重新生成")
        preview_info.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        preview_info.setWordWrap(True)
        preview_layout.addWidget(preview_info)
        
        # 预览操作按钮
        preview_btn_layout = QHBoxLayout()

        # 添加左侧弹性空间，使按钮居中
        preview_btn_layout.addStretch()

        self.generate_preview_btn = QPushButton("生成预览")
        self.generate_preview_btn.clicked.connect(self.generate_preview)
        preview_btn_layout.addWidget(self.generate_preview_btn)

        self.set_main_image_btn = QPushButton("设为主图")
        self.set_main_image_btn.clicked.connect(self.set_as_main_image)
        self.set_main_image_btn.setEnabled(False)
        preview_btn_layout.addWidget(self.set_main_image_btn)

        self.delete_image_btn = QPushButton("删除图像")
        self.delete_image_btn.clicked.connect(self.delete_current_image)
        self.delete_image_btn.setEnabled(False)
        preview_btn_layout.addWidget(self.delete_image_btn)

        # 添加右侧弹性空间，使按钮居中
        preview_btn_layout.addStretch()
        preview_layout.addLayout(preview_btn_layout)
        
        self.detail_tabs.addTab(preview_widget, "图像预览")
        
    def create_status_bar(self, parent_layout):
        """创建状态栏"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)  # type: ignore
        status_layout = QHBoxLayout(status_frame)
        
        # 状态信息
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # 进度信息
        self.progress_label = QLabel("0/0")
        status_layout.addWidget(self.progress_label)
        
        # 进度条 - 现代化样式
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setVisible(False)
        # 应用现代化样式
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #f5f5f5;
                text-align: center;
                font-size: 12px;
                color: #666;
                font-weight: normal;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 #42a5f5, stop: 1 #1976d2);
                border-radius: 3px;
                margin: 0px;
            }
        """)
        status_layout.addWidget(self.progress_bar)
        
        parent_layout.addWidget(status_frame)
        
    def load_storyboard_data(self):
        """加载分镜数据"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                # 如果没有项目，显示空状态
                self.storyboard_data = []
                self.update_table()
                self.status_label.setText("请先创建或加载项目以获取分镜数据")
                return

            # 🔧 修复：在刷新前先保存当前的图像数据
            logger.info("开始刷新分镜数据，先保存现有图像数据...")
            existing_image_data = self._preserve_existing_image_data()

            # 重新加载项目数据
            if hasattr(self.project_manager, 'reload_current_project'):
                self.project_manager.reload_current_project()

            project_data = self.project_manager.get_project_data()
            if not project_data:
                # 如果项目数据为空，显示空状态
                self.storyboard_data = []
                self.update_table()
                self.status_label.setText("项目数据为空，请先生成分镜脚本")
                return

            # 🔧 修复：清空现有数据，重新解析
            self.storyboard_data = []

            # 🔧 新增：初始化ID管理器
            self.shot_id_manager.initialize_from_project_data(project_data)
            logger.info("图像生成界面：ID管理器初始化完成")

            # 解析分镜数据
            self.parse_storyboard_data(project_data)

            # 🔧 修复：在解析完成后立即恢复图像数据
            if existing_image_data:
                logger.info("恢复之前保存的图像数据...")
                self._restore_existing_image_data(existing_image_data)

            # 初始化图像处理器
            self.init_image_processor()

            # 🔧 修复：检测并设置工作流程模式
            self._detect_and_set_workflow_mode()

            # 🔧 修复：强制更新UI状态
            self._update_ui_state()

            # 更新表格
            self.update_table()

            # 🔧 新增：强制刷新图像映射和预览
            self._refresh_image_mappings()

            # 🔧 新增：如果有选中的行，刷新预览
            current_row = self.storyboard_table.currentRow()
            if current_row >= 0:
                self.on_selection_changed()

            logger.info(f"分镜数据刷新完成，共加载 {len(self.storyboard_data)} 个分镜")
            self.status_label.setText(f"已刷新加载 {len(self.storyboard_data)} 个分镜")

        except Exception as e:
            logger.error(f"加载分镜数据失败: {e}")
            # 出错时显示空状态
            self.storyboard_data = []
            self.update_table()
            self.status_label.setText(f"加载失败: {str(e)}")

    def _refresh_image_mappings(self):
        """刷新图像映射关系"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_data = self.project_manager.current_project
            shot_image_mappings = project_data.get('shot_image_mappings', {})

            # 更新每个分镜的图像路径
            for shot_data in self.storyboard_data:
                scene_id = shot_data.get('scene_id', 'scene_1')
                shot_id = shot_data.get('shot_id', '')

                # 构建映射键
                mapping_key = f"{scene_id}_{shot_id}"

                if mapping_key in shot_image_mappings:
                    mapping_info = shot_image_mappings[mapping_key]
                    main_image_path = mapping_info.get('main_image_path', '')

                    if main_image_path and os.path.exists(main_image_path):
                        shot_data['main_image_path'] = main_image_path
                        shot_data['image_path'] = main_image_path
                        shot_data['status'] = '已生成'

                        # 更新生成的图像列表
                        generated_images = mapping_info.get('generated_images', [])
                        shot_data['generated_images'] = [img for img in generated_images if os.path.exists(img)]
                        shot_data['current_image_index'] = mapping_info.get('current_image_index', 0)

                        logger.debug(f"刷新图像映射: {mapping_key} -> {main_image_path}")
                    else:
                        logger.warning(f"图像文件不存在: {main_image_path}")

            logger.info("图像映射关系刷新完成")

        except Exception as e:
            logger.error(f"刷新图像映射失败: {e}")

    def parse_storyboard_data(self, project_data):
        """解析分镜数据 - 统一使用prompt.json作为数据来源"""
        # 🔧 修复：统一数据来源，只使用prompt.json
        self.storyboard_data = []

        # 🔧 修复：统一从prompt.json文件加载数据
        if self.project_manager and self.project_manager.current_project:
            project_dir = Path(self.project_manager.current_project['project_dir'])
            prompt_file = project_dir / 'texts' / 'prompt.json'

            if prompt_file.exists():
                try:
                    self._load_from_prompt_json(prompt_file)
                    if self.storyboard_data:
                        logger.info(f"从prompt.json成功加载 {len(self.storyboard_data)} 个镜头数据")
                        # 🔧 修复：加载完成后，从项目数据中恢复图像信息
                        self._sync_image_data_from_project()
                        return
                except Exception as e:
                    logger.error(f"从prompt.json加载数据失败: {e}")
                    # 如果prompt.json加载失败，显示错误
                    self.storyboard_data = []
                    return
            else:
                # 🔧 修复：如果prompt.json文件不存在，尝试从project.json加载分镜数据
                logger.info("prompt.json文件不存在，尝试从project.json加载分镜数据")
                self._load_from_project_json()
                return

        # 备选1：从一致性描述文件加载
        if self.project_manager and self.project_manager.current_project:
            project_dir = Path(self.project_manager.current_project['project_dir'])
            consistency_file = self._find_consistency_file(project_dir)
            if consistency_file:
                try:
                    self._load_from_consistency_file(consistency_file)
                    if self.storyboard_data:
                        logger.info(f"从一致性描述文件加载 {len(self.storyboard_data)} 个镜头数据")
                        return
                except Exception as e:
                    logger.error(f"从一致性描述文件加载数据失败: {e}")
                    # 继续尝试其他方法

        # 备选2：从项目数据中提取分镜信息
        five_stage_data = project_data.get('five_stage_storyboard', {})
        stage_data = five_stage_data.get('stage_data', {})

        # 🔧 修复：优先从第5阶段获取完整的分镜数据
        stage_5_data = stage_data.get('5', {})
        final_storyboard = stage_5_data.get('final_storyboard', [])

        if final_storyboard:
            logger.info(f"从第5阶段加载 {len(final_storyboard)} 个分镜数据")
            self._load_from_stage_5_data(final_storyboard)
            return

        # 获取第4阶段的分镜结果
        stage_4_data = stage_data.get('4', {})
        storyboard_results = stage_4_data.get('storyboard_results', [])

        if not storyboard_results:
            logger.warning("项目中没有分镜数据")
            return

        # 尝试加载prompt.json文件获取增强描述
        prompt_data = {}
        try:
            if self.project_manager and self.project_manager.current_project:
                project_dir = Path(self.project_manager.current_project['project_dir'])
                prompt_file = project_dir / 'texts' / 'prompt.json'
                if prompt_file.exists():
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        prompt_data = json.load(f)
                        logger.info(f"成功加载prompt.json文件: {prompt_file}")
        except Exception as e:
            logger.warning(f"加载prompt.json文件失败: {e}")

        # 解析场景和镜头数据
        for scene_result in storyboard_results:
            scene_info = scene_result.get('scene_info', '')
            scene_index = scene_result.get('scene_index', 0)

            # 从prompt.json中获取对应场景的镜头数据
            scene_shots = []
            if prompt_data and 'scenes' in prompt_data:
                scene_shots = prompt_data['scenes'].get(scene_info, [])

            # 如果prompt.json中没有数据，尝试从storyboard_script中解析
            if not scene_shots:
                storyboard_script = scene_result.get('storyboard_script', '')
                # 这里可以添加解析storyboard_script的逻辑
                logger.warning(f"场景 {scene_info} 在prompt.json中没有找到镜头数据")
                continue

            # 处理每个镜头
            for shot_idx, shot in enumerate(scene_shots, 1):
                shot_data = {
                    'scene_id': f'scene_{scene_index + 1}',
                    'scene_name': scene_info,
                    'shot_id': f'shot_{shot_idx}',
                    'shot_name': shot.get('shot_number', f'镜头{shot_idx}'),
                    'sequence': f'{scene_index + 1}-{shot_idx}',
                    'original_description': shot.get('original_description', ''),
                    'consistency_description': '',  # 暂时为空，后续处理
                    'enhanced_description': shot.get('enhanced_prompt', ''),
                    'status': '未生成',
                    'image_path': '',
                    'main_image_path': '',
                    'selected': False
                }
                self.storyboard_data.append(shot_data)

        logger.info(f"从五阶段数据成功解析 {len(self.storyboard_data)} 个镜头数据")

    def _find_consistency_file(self, project_dir):
        """查找最新的一致性描述文件"""
        try:
            texts_dir = project_dir / 'texts'
            if not texts_dir.exists():
                return None

            # 查找所有original_descriptions_with_consistency文件
            pattern = "original_descriptions_with_consistency_*.json"
            files = list(texts_dir.glob(pattern))

            if files:
                # 返回最新的文件
                latest_file = max(files, key=lambda f: f.stat().st_mtime)
                logger.info(f"找到一致性描述文件: {latest_file}")
                return latest_file
            return None
        except Exception as e:
            logger.error(f"查找一致性描述文件失败: {e}")
            return None

    def _load_from_consistency_file(self, consistency_file):
        """从一致性描述文件加载数据"""
        try:
            with open(consistency_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.storyboard_data = []
            self.consistency_file_path = consistency_file  # 保存文件路径用于更新

            # 尝试加载prompt.json文件获取增强描述
            enhanced_prompts = self._load_enhanced_prompts_from_prompt_json()

            scenes = data.get('scenes', [])
            shot_counter = 1

            for scene in scenes:
                scene_name = scene.get('scene_name', f'场景{scene.get("scene_index", 1)}')
                shots = scene.get('shots', [])
                scene_index = scene.get('scene_index', 1)

                for shot in shots:
                    shot_number = shot.get('shot_number', shot_counter)

                    # 从prompt.json获取增强描述
                    enhanced_description = enhanced_prompts.get(shot_counter, '')

                    shot_data = {
                        'scene_id': f'scene_{scene_index}',
                        'scene_name': scene_name,
                        'shot_id': f'shot_{shot_number}',
                        'shot_name': f'镜头{shot_number}',
                        'sequence': f'{scene_index}-{shot_number}',
                        'original_description': shot.get('content', ''),
                        'consistency_description': shot.get('content', ''),  # 使用content字段作为一致性描述
                        'enhanced_description': enhanced_description,  # 从prompt.json加载的增强描述
                        'status': '未生成',
                        'image_path': '',
                        'main_image_path': '',
                        'selected': False,
                        'shot_number_in_scene': shot_number,
                        'scene_index': scene_index
                    }
                    self.storyboard_data.append(shot_data)
                    shot_counter += 1

            logger.info(f"从一致性描述文件成功加载{len(self.storyboard_data)}个分镜数据")

        except Exception as e:
            logger.error(f"从一致性描述文件加载数据失败: {e}")
            raise

    def _load_enhanced_prompts_from_prompt_json(self):
        """从prompt.json文件加载增强描述"""
        enhanced_prompts = {}
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return enhanced_prompts

            project_dir = Path(self.project_manager.current_project['project_dir'])
            prompt_file = project_dir / 'texts' / 'prompt.json'

            if not prompt_file.exists():
                logger.warning("prompt.json文件不存在")
                return enhanced_prompts

            with open(prompt_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 解析新格式的prompt.json文件
            scenes = data.get('scenes', {})
            shot_counter = 1

            for scene_name, shots in scenes.items():
                for shot in shots:
                    enhanced_prompt = shot.get('enhanced_prompt', '')
                    if enhanced_prompt:
                        enhanced_prompts[shot_counter] = enhanced_prompt
                    shot_counter += 1

            logger.info(f"从prompt.json成功加载{len(enhanced_prompts)}个增强描述")

        except Exception as e:
            logger.error(f"从prompt.json加载增强描述失败: {e}")

        return enhanced_prompts

    def _load_from_project_json(self):
        """🔧 新增：从project.json文件加载分镜数据"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有项目管理器或当前项目")
                return

            project_dir = Path(self.project_manager.current_project['project_dir'])
            project_file = project_dir / 'project.json'

            if not project_file.exists():
                logger.warning("project.json文件不存在")
                return

            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 从project.json中获取分镜数据
            storyboard_results = project_data.get('five_stage_storyboard', {}).get('4', {}).get('storyboard_results', [])

            if not storyboard_results:
                logger.warning("project.json中没有分镜数据")
                return

            self.storyboard_data = []
            global_shot_counter = 1

            for scene_result in storyboard_results:
                scene_info = scene_result.get('scene_info', {})
                scene_name = scene_info.get('scene_name', f'场景{len(self.storyboard_data)+1}')
                storyboard_script = scene_result.get('storyboard_script', '')

                # 解析分镜脚本，提取镜头信息
                shots = self._parse_shots_from_script(storyboard_script)

                for shot in shots:
                    shot_data = {
                        'scene_index': len(self.storyboard_data) + 1,
                        'scene_name': scene_name,
                        'shot_number': global_shot_counter,
                        'shot_number_in_scene': shot.get('shot_number_in_scene', 1),
                        'description': shot.get('description', ''),
                        'original_text': shot.get('original_text', ''),
                        'characters': shot.get('characters', ''),
                        'shot_type': shot.get('shot_type', ''),
                        'camera_angle': shot.get('camera_angle', ''),
                        'camera_movement': shot.get('camera_movement', ''),
                        'lighting': shot.get('lighting', ''),
                        'color_tone': shot.get('color_tone', ''),
                        'enhanced_prompt': shot.get('enhanced_prompt', ''),
                        'content': shot.get('description', ''),  # 用于一致性控制
                    }
                    self.storyboard_data.append(shot_data)
                    global_shot_counter += 1

            logger.info(f"从project.json成功加载 {len(self.storyboard_data)} 个镜头数据")

        except Exception as e:
            logger.error(f"从project.json加载分镜数据失败: {e}")
            self.storyboard_data = []

    def _parse_shots_from_script(self, script_text):
        """解析分镜脚本文本，提取镜头信息"""
        shots = []
        try:
            import re

            # 按镜头分割
            shot_blocks = re.split(r'### 镜头\d+', script_text)

            for i, block in enumerate(shot_blocks[1:], 1):  # 跳过第一个空块
                shot_info = {'shot_number_in_scene': i}

                # 提取各个字段
                fields = {
                    '镜头原文': 'original_text',
                    '镜头类型': 'shot_type',
                    '机位角度': 'camera_angle',
                    '镜头运动': 'camera_movement',
                    '光影设计': 'lighting',
                    '色彩基调': 'color_tone',
                    '镜头角色': 'characters',
                    '画面描述': 'description'
                }

                for field_name, key in fields.items():
                    pattern = rf'- \*\*{field_name}\*\*：([^\n]+)'
                    match = re.search(pattern, block)
                    if match:
                        shot_info[key] = match.group(1).strip()

                if shot_info.get('description'):  # 只有有描述的镜头才添加
                    shots.append(shot_info)

        except Exception as e:
            logger.error(f"解析分镜脚本失败: {e}")

        return shots

    def _load_from_prompt_json(self, prompt_file):
        """🔧 修复：从prompt.json文件加载完整的镜头数据，修复场景数据重复问题"""
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.storyboard_data = []

            # 解析新格式的prompt.json文件
            scenes = data.get('scenes', {})
            if not scenes:
                logger.warning("prompt.json文件中没有scenes数据")
                return

            scene_index = 1
            global_shot_counter = 1

            # 🔧 修复：正确遍历每个场景，避免数据重复
            for scene_name, shots in scenes.items():
                logger.info(f"加载场景{scene_index}: {scene_name[:50]}...")

                for shot_idx, shot in enumerate(shots, 1):
                    # 🔧 修复：从original_description提取画面描述作为一致性描述
                    original_desc = shot.get('original_description', '')
                    consistency_description = self._extract_picture_description(original_desc)
                    if not consistency_description:
                        consistency_description = original_desc

                    # 🔧 修复：增强描述直接使用enhanced_prompt字段
                    enhanced_description = shot.get('enhanced_prompt', '')

                    shot_data = {
                        'scene_id': f'scene_{scene_index}',
                        'scene_name': scene_name[:50] + '...' if len(scene_name) > 50 else scene_name,  # 🔧 修复：截断过长的场景名
                        'shot_id': f'shot_{global_shot_counter}',
                        'shot_name': shot.get('shot_number', f'镜头{shot_idx}'),
                        'sequence': f'{scene_index}-{shot_idx}',
                        'original_description': original_desc,
                        'consistency_description': consistency_description,  # 🔧 修复：使用画面描述部分
                        'enhanced_description': enhanced_description,  # 🔧 修复：使用enhanced_prompt字段
                        'status': '未生成',
                        'image_path': '',
                        'main_image_path': '',
                        'selected': False,
                        'shot_number_in_scene': shot_idx,
                        'scene_index': scene_index
                    }
                    self.storyboard_data.append(shot_data)
                    global_shot_counter += 1

                scene_index += 1

            logger.info(f"从prompt.json成功加载{len(self.storyboard_data)}个分镜数据，共{scene_index-1}个场景")

        except Exception as e:
            logger.error(f"从prompt.json加载数据失败: {e}")
            raise

    def _load_consistency_content_map(self):
        """🔧 修复：从一致性描述文件中加载content字段映射"""
        content_map = {}
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return content_map

            project_dir = Path(self.project_manager.current_project['project_dir'])

            # 🔧 修复：优先从一致性描述文件加载
            consistency_file = self._find_consistency_file(project_dir)
            if consistency_file:
                logger.info(f"从一致性描述文件加载content字段: {consistency_file}")
                with open(consistency_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 解析一致性描述文件格式
                scenes = data.get('scenes', [])
                shot_counter = 1

                for scene in scenes:
                    shots = scene.get('shots', [])
                    for shot in shots:
                        content = shot.get('content', '')
                        if content:  # 只有当content字段存在且不为空时才添加
                            content_map[shot_counter] = content
                        shot_counter += 1

                logger.info(f"从一致性描述文件成功加载{len(content_map)}个content字段")
                return content_map

            # 🔧 备选：从prompt.json文件加载
            texts_dir = project_dir / 'texts'
            prompt_file = texts_dir / 'prompt.json'

            if prompt_file.exists():
                logger.info("一致性描述文件不存在，尝试从prompt.json加载")
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 构建镜头编号到content的映射
                shot_counter = 1
                scenes_data = data.get('scenes', {})

                for scene_name, scene_shots in scenes_data.items():
                    for shot in scene_shots:
                        # 🔧 修复：尝试多个字段作为一致性描述
                        content = (shot.get('content', '') or
                                 shot.get('original_description', '') or
                                 shot.get('description', ''))
                        if content:  # 只有当content字段存在且不为空时才添加
                            content_map[shot_counter] = content
                        shot_counter += 1

                logger.info(f"从prompt.json成功加载{len(content_map)}个content字段")
            else:
                logger.warning("prompt.json文件也不存在，无法加载一致性描述")

        except Exception as e:
            logger.error(f"加载一致性描述失败: {e}")

        return content_map

    def _get_real_enhanced_description(self, shot_data: Dict[str, Any]) -> str:
        """🔧 修复：获取真正的增强描述，只显示enhanced_prompt字段"""
        try:
            # 🔧 修复：直接返回shot_data中的enhanced_description字段
            # 这个字段在加载时已经从prompt.json的enhanced_prompt字段获取
            enhanced_desc = shot_data.get('enhanced_description', '')
            if enhanced_desc and enhanced_desc.strip():
                return enhanced_desc

            # 🔧 修复：如果没有增强描述，从original_description提取画面描述部分
            original_desc = shot_data.get('original_description', '')
            if original_desc:
                # 提取画面描述部分
                picture_desc = self._extract_picture_description(original_desc)
                if picture_desc:
                    return picture_desc

            # 如果都没有，返回默认描述
            return f"一个场景，{self.get_selected_style()}，高质量"

        except Exception as e:
            logger.error(f"获取增强描述失败: {e}")
            return f"一个场景，{self.get_selected_style()}，高质量"

    def _extract_picture_description(self, original_description: str) -> str:
        """🔧 新增：从original_description中提取画面描述部分"""
        try:
            if not original_description:
                return ""

            # 查找画面描述部分
            lines = original_description.split('\n')
            picture_desc = ""

            for line in lines:
                line = line.strip()
                if line.startswith('- **画面描述**：'):
                    picture_desc = line.replace('- **画面描述**：', '').strip()
                    break
                elif '画面描述' in line and '：' in line:
                    # 处理其他格式的画面描述
                    parts = line.split('：', 1)
                    if len(parts) > 1:
                        picture_desc = parts[1].strip()
                        break

            return picture_desc

        except Exception as e:
            logger.error(f"提取画面描述失败: {e}")
            return ""

    def _get_narration_text_for_shot(self, shot_data: Dict[str, Any]) -> str:
        """🔧 修复：获取镜头的旁白文本，与AI配音界面保持一致，显示原文内容"""
        try:
            # 🔧 修复：优先从项目的配音数据中获取对应的原文内容（original_text）
            if self.project_manager and self.project_manager.current_project:
                project_data = self.project_manager.get_project_data()
                if project_data:
                    voice_data = project_data.get('voice_generation', {})
                    voice_segments = voice_data.get('voice_segments', [])

                    logger.debug(f"查找旁白：配音段落数={len(voice_segments)}")

                    # 🔧 修复：通过在storyboard_data中的索引来匹配配音段落
                    # 找到当前shot_data在storyboard_data中的索引
                    current_shot_index = -1
                    for i, storyboard_shot in enumerate(self.storyboard_data):
                        # 使用多个字段进行匹配，确保准确性
                        if (storyboard_shot.get('scene_id') == shot_data.get('scene_id') and
                            storyboard_shot.get('shot_name') == shot_data.get('shot_name')):
                            current_shot_index = i
                            break

                    logger.debug(f"当前镜头在storyboard_data中的索引：{current_shot_index}")

                    # 如果找到了索引，直接使用对应的配音段落的original_text
                    if 0 <= current_shot_index < len(voice_segments):
                        segment = voice_segments[current_shot_index]
                        # 🔧 关键修复：优先使用original_text（原文内容），这与AI配音界面一致
                        narration = segment.get('original_text', '')
                        if narration and narration.strip():
                            logger.debug(f"按索引匹配找到原文旁白：{narration[:30]}...")
                            if len(narration) > 50:
                                return narration[:47] + "..."
                            return narration

                        # 备用：如果没有original_text，使用dialogue_text
                        dialogue = segment.get('dialogue_text', '')
                        if dialogue and dialogue.strip():
                            logger.debug(f"使用台词作为备用旁白：{dialogue[:30]}...")
                            if len(dialogue) > 50:
                                return dialogue[:47] + "..."
                            return dialogue

            # 🔧 备用方案：从shot_data的voice_content获取
            voice_content = shot_data.get('voice_content', '')
            if voice_content and voice_content.strip():
                if len(voice_content) > 50:
                    return voice_content[:47] + "..."
                return voice_content

            # 如果都没有找到，返回默认提示
            logger.debug("未找到匹配的旁白内容")
            return "暂无旁白"

        except Exception as e:
            logger.error(f"获取镜头旁白文本失败: {e}")
            return "获取失败"

    def _get_enhanced_description_for_voice_driven(self, voice_data: Dict[str, Any], shot_number: int) -> str:
        """🔧 新增：为配音驱动分镜获取正确的增强描述"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return self._fallback_description_from_voice(voice_data)

            project_dir = Path(self.project_manager.current_project['project_dir'])
            prompt_file = project_dir / 'texts' / 'prompt.json'

            # 优先从prompt.json获取增强描述
            if prompt_file.exists():
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                scenes = data.get('scenes', {})
                shot_counter = 1

                # 遍历所有场景和镜头，按顺序查找
                for scene_name, scene_shots in scenes.items():
                    for shot in scene_shots:
                        if shot_counter == shot_number:
                            enhanced_prompt = shot.get('enhanced_prompt', '')
                            if enhanced_prompt and enhanced_prompt.strip():
                                logger.debug(f"配音驱动分镜：从prompt.json获取镜头{shot_number}的增强描述")
                                return enhanced_prompt
                        shot_counter += 1

            # 如果prompt.json中没有找到，使用配音内容生成描述
            return self._fallback_description_from_voice(voice_data)

        except Exception as e:
            logger.error(f"获取配音驱动分镜增强描述失败: {e}")
            return self._fallback_description_from_voice(voice_data)

    def _fallback_description_from_voice(self, voice_data: Dict[str, Any]) -> str:
        """🔧 新增：从配音数据生成备用描述"""
        try:
            if not voice_data:
                return f"一个场景，{self.get_selected_style()}，高质量"

            # 获取配音内容
            voice_content = voice_data.get('voice_content', '')
            dialogue_content = voice_data.get('dialogue_content', '')
            scene_id = voice_data.get('scene_id', '')

            # 选择主要内容
            main_content = dialogue_content if dialogue_content else voice_content

            if not main_content or len(main_content.strip()) < 5:
                return f"一个温馨的场景，{self.get_selected_style()}，高质量"

            # 基于内容生成简单描述
            if '雪' in main_content or '冬' in main_content or '冷' in main_content:
                base_desc = "雪地中的场景，寒冷的冬日"
            elif '家' in main_content or '房' in main_content:
                base_desc = "温馨的室内场景"
            elif '学校' in main_content or '教室' in main_content:
                base_desc = "学校场景，教育环境"
            elif '书' in main_content or '读' in main_content:
                base_desc = "阅读场景，书籍环境"
            else:
                base_desc = "日常生活场景"

            return f"{base_desc}，{main_content[:30]}，{self.get_selected_style()}，高质量，细节丰富"

        except Exception as e:
            logger.error(f"从配音数据生成备用描述失败: {e}")
            return f"一个场景，{self.get_selected_style()}，高质量"

    def _detect_and_set_workflow_mode(self):
        """🔧 新增：检测并设置工作流程模式"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_data = self.project_manager.get_project_data()
            if not project_data:
                return

            # 检测是否有配音数据
            voice_data = project_data.get('voice_generation', {})
            voice_segments = voice_data.get('voice_segments', [])

            # 检测是否有五阶段数据
            stage_5_data = project_data.get('storyboard_generation', {}).get('stage_5_final_storyboard', [])

            if voice_segments and len(voice_segments) > 0:
                logger.info("检测到配音数据，设置为配音驱动模式")
                # 可以在这里设置一些UI状态标志
            elif stage_5_data and len(stage_5_data) > 0:
                logger.info("检测到五阶段数据，设置为传统分镜模式")
            else:
                logger.info("未检测到特定工作流程数据，使用默认模式")

        except Exception as e:
            logger.error(f"检测工作流程模式失败: {e}")

    def _update_ui_state(self):
        """🔧 新增：更新UI状态"""
        try:
            # 更新按钮状态 - 已删除按配音时间生成按钮

            # 更新状态标签
            if hasattr(self, 'status_label'):
                current_text = self.status_label.text()
                if "已刷新" not in current_text:
                    self.status_label.setText(f"{current_text} (已刷新)")

        except Exception as e:
            logger.error(f"更新UI状态失败: {e}")

    def _load_from_stage_5_data(self, final_storyboard):
        """🔧 新增：从第5阶段数据加载分镜信息"""
        try:
            self.storyboard_data = []

            for shot_data in final_storyboard:
                # 解析镜头数据
                shot_info = {
                    'scene_id': shot_data.get('scene_id', ''),
                    'scene_name': shot_data.get('scene_name', ''),
                    'shot_id': shot_data.get('shot_id', ''),
                    'shot_name': shot_data.get('shot_name', ''),
                    'sequence': shot_data.get('sequence', ''),
                    'original_description': shot_data.get('original_description', ''),
                    'consistency_description': shot_data.get('consistency_description', ''),
                    'enhanced_description': shot_data.get('enhanced_description', ''),
                    'status': '未生成',
                    'image_path': '',
                    'main_image_path': '',
                    'selected': False
                }
                self.storyboard_data.append(shot_info)

            logger.info(f"从第5阶段数据成功加载 {len(self.storyboard_data)} 个分镜")

        except Exception as e:
            logger.error(f"从第5阶段数据加载失败: {e}")
            raise

    def init_image_processor(self):
        """初始化图像处理器"""
        try:
            if self.app_controller and hasattr(self.app_controller, 'image_processor'):
                self.image_processor = self.app_controller.image_processor
                logger.info("成功获取图像处理器")
            else:
                # 如果无法从app_controller获取，创建新的处理器
                from src.processors.image_processor import ImageProcessor
                # 创建一个基本的服务管理器实例
                try:
                    from src.models.service_manager import ServiceManager
                    service_manager = ServiceManager()
                    self.image_processor = ImageProcessor(service_manager)
                except ImportError:
                    # 如果无法导入ServiceManager，则跳过创建ImageProcessor
                    logger.warning("无法导入ServiceManager，跳过创建ImageProcessor")
                    self.image_processor = None
                logger.info("创建新的图像处理器")
        except Exception as e:
            logger.error(f"初始化图像处理器失败: {e}")
            self.image_processor = None
                
    def load_test_data(self):
        """加载测试数据（已清除，现在只使用项目数据）"""
        self.storyboard_data = []
        logger.info("测试数据已清除，请先创建或加载项目以获取分镜数据")

                
    def update_table(self):
        """更新表格显示"""
        # 按场景分组数据
        scene_groups = {}
        for shot_data in self.storyboard_data:
            scene_id = shot_data['scene_id']
            if scene_id not in scene_groups:
                scene_groups[scene_id] = []
            scene_groups[scene_id].append(shot_data)
        
        # 计算总行数（每个场景一行，加上该场景的镜头数）
        total_rows = 0
        for scene_shots in scene_groups.values():
            total_rows += len(scene_shots)
        
        self.storyboard_table.setRowCount(total_rows)
        
        # 定义场景颜色
        scene_colors = [
            QColor(255, 240, 240),  # 浅红色
            QColor(255, 255, 224),  # 浅黄色
            QColor(240, 255, 240),  # 浅绿色
            QColor(240, 248, 255),  # 浅蓝色
            QColor(248, 240, 255),  # 浅紫色
            QColor(255, 248, 240),  # 浅橙色
            QColor(240, 255, 255),  # 浅青色
            QColor(255, 240, 248),  # 浅粉色
        ]
        
        current_row = 0
        scene_index = 0
        for scene_id, scene_shots in scene_groups.items():
            scene_name = scene_shots[0]['scene_name']
            # 获取当前场景的颜色
            scene_color = scene_colors[scene_index % len(scene_colors)]
            
            for i, shot_data in enumerate(scene_shots):
                # 选择复选框
                checkbox = QCheckBox()
                checkbox.setChecked(shot_data['selected'])
                checkbox.stateChanged.connect(
                    lambda state, r=current_row: self.on_checkbox_changed_by_row(r, state)
                )
                self.storyboard_table.setCellWidget(current_row, 0, checkbox)
                
                # 场景列 - 只在第一行显示场景名
                if i == 0:
                    scene_item = QTableWidgetItem(scene_name)
                    scene_item.setData(Qt.ItemDataRole.UserRole, len(scene_shots))  # 存储跨行数
                    self.storyboard_table.setItem(current_row, 1, scene_item)
                    # 合并场景列的单元格
                    if len(scene_shots) > 1:
                        self.storyboard_table.setSpan(current_row, 1, len(scene_shots), 1)
                
                # 镜头列 - 移除###号
                shot_name = shot_data['shot_name'].replace('### ', '').replace('###', '')
                shot_item = QTableWidgetItem(shot_name)
                self.storyboard_table.setItem(current_row, 2, shot_item)

                # 🔧 新增：旁白列 - 显示与AI配音界面一致的原文内容
                narration_text = self._get_narration_text_for_shot(shot_data)
                narration_item = QTableWidgetItem(narration_text)
                narration_item.setFlags(narration_item.flags() | Qt.ItemFlag.ItemIsEnabled)
                narration_item.setToolTip(narration_text)  # 完整内容作为提示
                self.storyboard_table.setItem(current_row, 3, narration_item)

                # 🔧 修复：增强描述列索引调整为4
                # 从prompt.json的enhanced_prompt字段获取真正的增强描述
                enhanced_description = self._get_real_enhanced_description(shot_data)
                enhanced_item = QTableWidgetItem(enhanced_description)
                enhanced_item.setFlags(enhanced_item.flags() | Qt.ItemFlag.ItemIsEnabled)
                self.storyboard_table.setItem(current_row, 4, enhanced_item)  # 列索引改为4

                # 🔧 修复：使用简洁的主图显示
                self.create_main_image_widget(current_row, shot_data)

                # 操作按钮
                self.create_action_buttons(current_row)
                
                # 设置整行的背景色
                for col in range(self.storyboard_table.columnCount()):
                    item = self.storyboard_table.item(current_row, col)
                    if item:
                        item.setBackground(scene_color)
                
                current_row += 1
            
            scene_index += 1
        
        # 调整行高以适应内容
        self.storyboard_table.resizeRowsToContents()
            
    def create_action_buttons(self, row):
        """创建操作按钮 - 两行排列"""
        button_widget = QWidget()
        button_layout = QVBoxLayout(button_widget)  # 改为垂直布局
        button_layout.setContentsMargins(2, 2, 2, 2)
        button_layout.setSpacing(2)

        # 生成按钮
        generate_btn = QPushButton("生成")
        generate_btn.setMaximumWidth(70)  # 稍微增加宽度
        generate_btn.setMaximumHeight(22)  # 稍微减少高度
        generate_btn.clicked.connect(lambda: self.generate_single_image(row))
        button_layout.addWidget(generate_btn)

        # 预览按钮
        preview_btn = QPushButton("预览")
        preview_btn.setMaximumWidth(70)  # 稍微增加宽度
        preview_btn.setMaximumHeight(22)  # 稍微减少高度
        preview_btn.clicked.connect(lambda: self.preview_single_image(row))
        button_layout.addWidget(preview_btn)

        self.storyboard_table.setCellWidget(row, 6, button_widget)  # 🔧 修复：列索引改为6（操作列）



    def create_main_image_widget(self, row, shot_data):
        """创建主图显示组件 - 动态调整尺寸"""
        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        image_layout.setContentsMargins(2, 2, 2, 2)
        image_layout.setSpacing(2)

        # 图片显示标签 - 动态尺寸
        image_label = QLabel()
        # 🔧 修复：获取当前主图列的宽度（第5列）
        column_width = self.storyboard_table.columnWidth(5)
        # 计算合适的图片尺寸，留出边距
        image_width = max(column_width - 10, 100)  # 最小宽度100px
        image_height = int(image_width * 0.6)  # 保持16:10的宽高比

        # 设置图片标签的尺寸策略，让它能够自适应
        image_label.setMinimumSize(100, 60)  # 设置最小尺寸
        image_label.setMaximumSize(image_width, image_height)  # 设置最大尺寸
        image_label.resize(image_width, image_height)  # 设置当前尺寸
        image_label.setStyleSheet("border: 1px solid #ccc; background-color: #f5f5f5;")
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # type: ignore
        image_label.setScaledContents(False)  # 不自动缩放内容，我们手动控制

        # 存储行号，用于后续更新
        image_label.setProperty("row", row)

        # 🔧 修复：优先从项目数据获取图像信息
        shot_key = f"{shot_data.get('scene_id', '')}_{shot_data.get('shot_id', '')}"
        project_image_data = self._get_shot_image_from_project(shot_key)

        # 检查是否有主图
        main_image_path = shot_data.get('main_image_path')

        # 🔧 修复：如果当前数据没有图像，尝试从项目数据获取
        if not main_image_path and project_image_data:
            main_image_path = project_image_data.get('main_image_path', '')
            if main_image_path:
                shot_data['main_image_path'] = main_image_path
                shot_data['status'] = project_image_data.get('status', '已生成')
                if project_image_data.get('generated_images'):
                    shot_data['generated_images'] = project_image_data['generated_images']

        if main_image_path and os.path.exists(main_image_path):
            # 加载并缩放图片
            pixmap = QPixmap(main_image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(image_width - 2, image_height - 2, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)  # type: ignore
                image_label.setPixmap(scaled_pixmap)
            else:
                image_label.setText("无预览")
        else:
            # 🔧 修复：根据状态显示不同的占位符
            status = shot_data.get('status', '未生成')
            if status == '已生成' and main_image_path:
                # 状态是已生成但文件不存在
                image_label.setText("文件丢失")
                image_label.setStyleSheet("border: 1px solid #ff9999; background-color: #ffe6e6; color: #cc0000;")
            else:
                image_label.setText("暂无图片")

        image_layout.addWidget(image_label)

        # 设置容器widget的尺寸策略，让它能够响应列宽变化
        image_widget.setMinimumSize(100, 70)
        image_widget.setMaximumSize(column_width, image_height + 10)
        image_widget.resize(column_width, image_height + 10)

        # 删除翻页按钮，翻页功能已移至预览区域

        # 🔧 修复：主图应该显示在第5列
        self.storyboard_table.setCellWidget(row, 5, image_widget)

    def on_column_resized(self, logical_index, old_size, new_size):
        """处理列宽变化，动态调整图片大小"""
        # 🔧 修复：只处理主图列（第5列）的变化
        if logical_index == 5:
            self.update_all_image_sizes()

    def update_all_image_sizes(self):
        """更新所有图片的显示尺寸"""
        column_width = self.storyboard_table.columnWidth(5)  # 🔧 修复：主图列现在是第5列
        image_width = max(column_width - 10, 100)  # 最小宽度100px
        image_height = int(image_width * 0.6)  # 保持16:10的宽高比

        # 遍历所有行，更新图片尺寸
        for row in range(self.storyboard_table.rowCount()):
            image_widget = self.storyboard_table.cellWidget(row, 5)  # 🔧 修复：主图列现在是第5列
            if image_widget:
                # 更新容器widget的尺寸
                image_widget.setMinimumSize(100, 70)
                image_widget.setMaximumSize(column_width, image_height + 10)
                image_widget.resize(column_width, image_height + 10)

                # 找到图片标签
                image_label = image_widget.findChild(QLabel)
                if image_label:
                    # 更新标签尺寸
                    image_label.setMinimumSize(100, 60)
                    image_label.setMaximumSize(image_width, image_height)
                    image_label.resize(image_width, image_height)

                    # 重新加载并缩放图片
                    current_pixmap = image_label.pixmap()
                    if current_pixmap and not current_pixmap.isNull():
                        # 获取原始图片路径并重新加载
                        row_data_index = self.get_data_index_by_table_row(row)
                        if row_data_index >= 0:
                            shot_data = self.storyboard_data[row_data_index]
                            main_image_path = shot_data.get('main_image_path')
                            if main_image_path and os.path.exists(main_image_path):
                                pixmap = QPixmap(main_image_path)
                                if not pixmap.isNull():
                                    scaled_pixmap = pixmap.scaled(
                                        image_width - 2,
                                        image_height - 2,
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation
                                    )  # type: ignore
                                    image_label.setPixmap(scaled_pixmap)

                # 强制更新widget布局
                image_widget.updateGeometry()
                image_widget.update()

    # 事件处理方法
    def on_checkbox_changed(self, row, state):
        """复选框状态改变"""
        self.storyboard_data[row]['selected'] = state == Qt.CheckState.Checked
        
    def on_checkbox_changed_by_row(self, table_row, state):
        """根据表格行号处理复选框状态改变"""
        # 找到对应的数据索引
        data_index = self.get_data_index_by_table_row(table_row)
        if data_index >= 0:
            self.storyboard_data[data_index]['selected'] = state == Qt.CheckState.Checked
            
    def get_data_index_by_table_row(self, table_row):
        """根据表格行号获取数据索引"""
        current_row = 0
        for data_index, shot_data in enumerate(self.storyboard_data):
            if current_row == table_row:
                return data_index
            current_row += 1
        return -1
         
    def prev_image(self, table_row):
        """显示上一张图片"""
        data_index = self.get_data_index_by_table_row(table_row)
        if data_index >= 0:
            shot_data = self.storyboard_data[data_index]
            images = shot_data.get('generated_images', [])
            if len(images) > 1:
                current_index = shot_data.get('current_image_index', 0)
                new_index = (current_index - 1) % len(images)
                shot_data['current_image_index'] = new_index
                shot_data['main_image_path'] = images[new_index]
                self.create_main_image_widget(table_row, shot_data)
                
    def next_image(self, table_row):
        """显示下一张图片"""
        data_index = self.get_data_index_by_table_row(table_row)
        if data_index >= 0:
            shot_data = self.storyboard_data[data_index]
            images = shot_data.get('generated_images', [])
            if len(images) > 1:
                current_index = shot_data.get('current_image_index', 0)
                new_index = (current_index + 1) % len(images)
                shot_data['current_image_index'] = new_index
                shot_data['main_image_path'] = images[new_index]
                self.create_main_image_widget(table_row, shot_data)
                
    def on_selection_changed(self):
        """表格选择改变"""
        current_row = self.storyboard_table.currentRow()
        if 0 <= current_row < len(self.storyboard_data):
            self.load_shot_details(current_row)
            
    def on_cell_clicked(self, row, column):
        """单元格点击"""
        if 0 <= row < len(self.storyboard_data):
            self.load_shot_details(row)
            
    def load_shot_details(self, row):
        """🔧 修复：加载镜头详细信息，确保数据源正确"""
        data_index = self.get_data_index_by_table_row(row)
        if data_index < 0:
            return

        shot_data = self.storyboard_data[data_index]

        # 🔧 修复：一致性描述应该显示画面描述部分
        consistency_desc = shot_data.get('consistency_description', '')
        if not consistency_desc:
            # 如果没有一致性描述，从original_description提取画面描述
            original_desc = shot_data.get('original_description', '')
            consistency_desc = self._extract_picture_description(original_desc)

        # 🔧 修复：增强描述显示enhanced_description字段
        enhanced_desc = shot_data.get('enhanced_description', '')

        # 更新描述面板
        self.consistency_desc_text.setPlainText(consistency_desc)
        self.enhanced_desc_text.setPlainText(enhanced_desc)

        # 加载预览图像
        if shot_data['image_path'] and os.path.exists(shot_data['image_path']):
            self.load_preview_image(shot_data['image_path'])
            # 设置当前图像路径属性，供设为主图功能使用
            self.preview_label.setProperty('current_image_path', shot_data['image_path'])
        else:
            self.preview_label.setText("暂无预览图像")
            self.preview_label.setProperty('current_image_path', None)

        # 更新预览翻页控件和设为主图按钮状态
        self.update_preview_navigation(shot_data)
            
    def load_preview_image(self, image_path):
        """加载预览图像"""
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # 缩放图像以适应标签
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )  # type: ignore
                self.preview_label.setPixmap(scaled_pixmap)
            else:
                self.preview_label.setText("图像加载失败")
        except Exception as e:
            logger.error(f"加载预览图像失败: {e}")
            self.preview_label.setText("图像加载失败")
            
    # 批量操作方法
    def select_all_items(self):
        """全选"""
        for i in range(len(self.storyboard_data)):
            self.storyboard_data[i]['selected'] = True
            checkbox = self.storyboard_table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(True)
                
    def deselect_all_items(self):
        """取消全选"""
        for i in range(len(self.storyboard_data)):
            self.storyboard_data[i]['selected'] = False
            checkbox = self.storyboard_table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(False)
                
    def select_current_scene(self):
        """选择当前场景"""
        current_row = self.storyboard_table.currentRow()
        if current_row < 0:
            return
            
        current_scene = self.storyboard_data[current_row]['scene_id']
        
        for i, shot_data in enumerate(self.storyboard_data):
            if shot_data['scene_id'] == current_scene:
                shot_data['selected'] = True
                checkbox = self.storyboard_table.cellWidget(i, 0)
                if checkbox:
                    checkbox.setChecked(True)
                    
    # 生成相关方法
    def generate_selected_images(self):
        """生成选中的图像"""
        selected_items = [item for item in self.storyboard_data if item['selected']]
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要生成的项目")
            return
            
        self.start_batch_generation(selected_items)
        
    def generate_all_images(self):
        """生成全部图像"""
        if not self.storyboard_data:
            QMessageBox.warning(self, "警告", "没有可生成的项目")
            return
            
        self.start_batch_generation(self.storyboard_data)
        
    def start_batch_generation(self, items):
        """开始批量生成"""
        # 清空失败记录
        self.failed_generations = []

        # 如果启用了跳过已生成图片的选项，过滤掉已生成的项目
        if self.skip_existing_cb.isChecked():
            filtered_items = []
            skipped_count = 0

            for i, item in enumerate(items):
                # 找到原始索引
                original_index = self.storyboard_data.index(item) if item in self.storyboard_data else i

                if self._has_generated_image(original_index, item):
                    skipped_count += 1
                    logger.info(f"跳过已生成图片的镜头{original_index + 1}")
                else:
                    filtered_items.append(item)

            if skipped_count > 0:
                QMessageBox.information(
                    self,
                    "跳过提示",
                    f"已跳过{skipped_count}个已生成图片的镜头\n将生成{len(filtered_items)}个镜头的图片"
                )

            items = filtered_items

        if not items:
            QMessageBox.information(self, "提示", "没有需要生成的镜头")
            return

        self.generation_queue = items.copy()
        self.is_generating = True

        # 更新UI状态
        self.generate_selected_btn.setEnabled(False)
        self.generate_all_btn.setEnabled(False)
        self.stop_generation_btn.setEnabled(True)

        # 显示进度条
        self.progress_bar.setMaximum(len(items))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        # 开始生成
        self.process_generation_queue()
        
    def process_generation_queue(self):
        """处理生成队列"""
        if not self.generation_queue or not self.is_generating:
            self.finish_batch_generation()
            return
            
        # 获取下一个项目
        current_item = self.generation_queue.pop(0)
        
        # 更新状态
        current_progress = self.progress_bar.maximum() - len(self.generation_queue)
        self.progress_bar.setValue(current_progress)
        self.progress_label.setText(f"{current_progress}/{self.progress_bar.maximum()}")
        self.status_label.setText(f"正在生成: {current_item['sequence']}")
        
        # 开始生成图像
        self.generate_image_for_item(current_item)
        
    def generate_image_for_item(self, item):
        """为单个项目生成图像"""
        try:
            # 更新项目状态
            item['status'] = '生成中'
            self.update_item_status(item)
            
            # 获取生成参数
            config = self.get_generation_config(item)
            
            # 这里应该调用实际的图像生成服务
            # 暂时使用模拟生成
            self.simulate_image_generation(item, config)
            
        except Exception as e:
            logger.error(f"生成图像失败: {e}")
            item['status'] = '失败'
            self.update_item_status(item)
            
            # 继续处理下一个
            QTimer.singleShot(1000, self.process_generation_queue)
            
    def simulate_image_generation(self, item, config):
        """调用真实的图像生成服务"""
        try:
            # 获取项目目录
            project_dir = None
            if self.project_manager and self.project_manager.current_project:
                project_dir = self.project_manager.current_project['project_dir']

            if not project_dir:
                logger.error("无法获取项目目录")
                self.on_image_generated(item, False)
                return

            # 使用图像生成服务
            if hasattr(self, 'image_generation_service') and self.image_generation_service:
                # 🔧 修复：获取正确的增强描述内容
                # 优先从prompt.json的enhanced_prompt字段获取真正的增强描述
                original_prompt = self._get_real_enhanced_description(item)

                # 如果获取不到真正的增强描述，按优先级获取其他描述
                if not original_prompt or not original_prompt.strip():
                    original_prompt = item.get('enhanced_description', '')
                if not original_prompt or not original_prompt.strip():
                    original_prompt = item.get('consistency_description', '')
                if not original_prompt or not original_prompt.strip():
                    original_prompt = item.get('original_description', '')

                # 确保描述内容不是路径
                if original_prompt and ('\\' in original_prompt or '/' in original_prompt) and len(original_prompt) < 50:
                    logger.warning(f"检测到可能的路径而非描述内容: {original_prompt}")
                    # 尝试从其他字段获取描述
                    original_prompt = item.get('consistency_description', '')
                    if not original_prompt:
                        original_prompt = item.get('original_description', '')

                if not original_prompt.strip():
                    logger.error("没有可用的描述内容")
                    self.on_image_generated(item, False)
                    return

                logger.info(f"开始为镜头 {item.get('sequence', 'Unknown')} 生成图像")
                logger.info(f"原始描述: {original_prompt[:100]}...")

                # 根据引擎类型决定是否翻译
                current_engine = self.engine_combo.currentText()
                if "CogView-3 Flash" in current_engine:
                    # CogView-3 Flash支持中文，直接使用原始描述
                    translated_prompt = original_prompt
                    logger.info("CogView-3 Flash引擎支持中文，跳过翻译")
                else:
                    # 其他引擎需要翻译为英文
                    translated_prompt = self._translate_prompt_to_english(original_prompt, item)
                    if not translated_prompt:
                        logger.warning("翻译失败，使用原始描述")
                        translated_prompt = original_prompt

                logger.info(f"最终提示词: {translated_prompt[:100]}...")

                # 获取当前选择的引擎
                current_engine = self.engine_combo.currentText()
                engine_preference = "pollinations"  # 默认值
                provider = "pollinations"  # 默认值

                # 根据用户选择的引擎设置引擎偏好
                if "ComfyUI 本地" in current_engine:
                    engine_preference = "comfyui_local"
                    provider = "comfyui_local"
                elif "ComfyUI 云端" in current_engine:
                    engine_preference = "comfyui_cloud"
                    provider = "comfyui_cloud"
                elif "Pollinations" in current_engine:
                    engine_preference = "pollinations"
                    provider = "pollinations"
                elif "CogView-3 Flash" in current_engine:
                    engine_preference = "cogview_3_flash"
                    provider = "cogview_3_flash"
                elif "DALL-E" in current_engine:
                    engine_preference = "dalle"
                    provider = "dalle"
                elif "Stability" in current_engine:
                    engine_preference = "stability"
                    provider = "stability"
                elif "Imagen" in current_engine:
                    engine_preference = "imagen"
                    provider = "imagen"

                logger.info(f"使用引擎: {current_engine} -> {engine_preference}")

                # 创建正确的配置对象
                from src.processors.image_processor import ImageGenerationConfig

                # 构建正确的配置 - 根据ImageGenerationConfig的实际参数
                generation_config = ImageGenerationConfig(
                    provider=provider,  # 使用用户选择的引擎
                    style=self.get_selected_style(),  # 使用用户选择的风格
                    width=config.get('width', 1024),
                    height=config.get('height', 1024),
                    steps=config.get('steps', 20),
                    cfg_scale=config.get('cfg_scale', 7.5),
                    seed=config.get('seed', -1),
                    batch_size=1,  # 固定为1，每个镜头生成1张图像
                    negative_prompt=config.get('negative_prompt', '')
                )

                # 设置并发任务数限制
                if hasattr(self, 'concurrent_tasks_spin'):
                    concurrent_limit = self.concurrent_tasks_spin.value()
                    if hasattr(self.image_generation_service, 'engine_manager'):
                        self.image_generation_service.engine_manager.concurrent_limit = concurrent_limit
                        logger.info(f"设置并发任务数限制: {concurrent_limit}")

                # 启动异步生成任务
                from src.gui.image_generation_thread import ImageGenerationThread

                self.image_generation_thread = ImageGenerationThread(
                    image_generation_service=self.image_generation_service,
                    config=generation_config,  # 使用正确的配置对象
                    engine_preference=engine_preference,  # 使用用户选择的引擎偏好
                    prompt=translated_prompt,  # 使用翻译后的提示词
                    workflow_id=item['sequence'],  # 使用序列作为工作流ID
                    project_manager=self.project_manager,
                    current_project_name=self.project_manager.current_project['project_name'] if self.project_manager and self.project_manager.current_project else None
                )

                # 连接信号 - 修复lambda参数问题
                self.image_generation_thread.image_generated.connect(
                    lambda image_path: self.on_async_image_generated(item, True, image_path, None)
                )
                self.image_generation_thread.generation_failed.connect(
                    lambda error_msg: self.on_async_image_generated(item, False, None, error_msg)
                )

                # 启动线程
                self.image_generation_thread.start()
            else:
                logger.error("图像生成服务未初始化")
                self.on_image_generated(item, False)

        except Exception as e:
            logger.error(f"图像生成过程中发生错误: {e}")
            self.on_image_generated(item, False)

    def _translate_prompt_to_english(self, chinese_prompt, item):
        """将中文提示词翻译为英文，使用增强翻译服务

        Args:
            chinese_prompt: 中文提示词
            item: 镜头数据项

        Returns:
            str: 翻译后的英文提示词，失败时返回None
        """
        try:
            # 导入增强翻译模块
            from src.utils.enhanced_translator import translate_text_enhanced

            logger.info(f"开始翻译镜头 {item.get('sequence', 'Unknown')} 的描述")
            logger.debug(f"原始中文描述: {chinese_prompt}")

            # 获取LLM API实例用于翻译
            llm_api = None
            if hasattr(self, 'parent_window') and self.parent_window:
                if hasattr(self.parent_window, 'app_controller') and self.parent_window.app_controller:
                    try:
                        # 尝试获取LLM API
                        from src.models.llm_api import LLMApi
                        from src.utils.config_manager import ConfigManager

                        config_manager = ConfigManager()
                        llm_config = config_manager.get_llm_config()

                        if llm_config and llm_config.get('api_key'):
                            llm_api = LLMApi(
                                api_type=llm_config.get('api_type', 'tongyi'),
                                api_key=llm_config['api_key'],
                                api_url=llm_config.get('api_url', '')
                            )
                    except Exception as e:
                        logger.debug(f"获取LLM API失败: {e}")

            # 调用增强翻译服务
            translated_result = translate_text_enhanced(chinese_prompt, 'zh', 'en', llm_api)

            if translated_result and translated_result.strip():
                logger.info(f"翻译成功: {chinese_prompt[:50]}... -> {translated_result[:50]}...")
                logger.debug(f"完整翻译结果: {translated_result}")
                return translated_result
            else:
                logger.warning("翻译失败，使用原始描述")
                return None

        except ImportError as e:
            logger.error(f"导入增强翻译模块失败: {e}")
            return None
        except Exception as e:
            logger.error(f"翻译过程中发生错误: {e}")
            return None

    def _check_comfyui_service(self):
        """检查ComfyUI服务状态"""
        try:
            from src.utils.comfyui_helper import ComfyUIHelper

            # 创建ComfyUI助手
            comfyui_helper = ComfyUIHelper()

            # 检查服务状态
            status_result = comfyui_helper.check_service_status()

            if status_result['is_running']:
                logger.info("ComfyUI服务运行正常")
                return True
            else:
                # 显示友好的错误提示
                error_msg = status_result.get('error_message', 'ComfyUI服务未运行')
                suggestions = status_result.get('suggestions', [])

                # 构建详细的错误信息
                detailed_msg = f"{error_msg}\n\n建议解决方案：\n"
                for i, suggestion in enumerate(suggestions, 1):
                    detailed_msg += f"{i}. {suggestion}\n"

                # 显示错误对话框
                from PyQt5.QtWidgets import QMessageBox
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("ComfyUI服务未启动")
                msg_box.setText("无法连接到ComfyUI服务")
                msg_box.setDetailedText(detailed_msg)
                msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Help)

                result = msg_box.exec_()

                if result == QMessageBox.Help:
                    # 显示启动指导
                    startup_instructions = comfyui_helper.get_startup_instructions()
                    help_box = QMessageBox(self)
                    help_box.setIcon(QMessageBox.Information)
                    help_box.setWindowTitle("ComfyUI启动指导")
                    help_box.setText("ComfyUI启动指导")
                    help_box.setDetailedText(startup_instructions)
                    help_box.exec_()

                logger.warning(f"ComfyUI服务检查失败: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"检查ComfyUI服务状态时发生错误: {e}")
            # 显示简单的错误提示
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "服务检查失败",
                f"检查ComfyUI服务状态时发生错误：\n{str(e)}\n\n请确保ComfyUI服务正常运行。"
            )
            return False

    def _ensure_image_in_project_folder(self, image_path, item):
        """确保图像保存在项目的images文件夹中对应的生图引擎子文件夹

        Args:
            image_path: 原始图像路径
            item: 镜头数据项

        Returns:
            str: 项目内的最终图像路径
        """
        try:
            import shutil
            import time
            from pathlib import Path

            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有项目管理器，返回原始路径")
                return image_path

            project_dir = Path(self.project_manager.current_project['project_dir'])
            original_path = Path(image_path)

            # 检查图像是否已经在项目目录中
            try:
                # 如果图像已经在项目的images目录中，直接返回
                if project_dir in original_path.parents:
                    logger.info(f"图像已在项目目录中: {image_path}")
                    return image_path

                # 特别检查ComfyUI引擎是否已经保存到正确位置
                images_dir = project_dir / "images"
                if images_dir in original_path.parents:
                    logger.info(f"图像已在项目images目录中: {image_path}")
                    return image_path

            except Exception:
                pass  # 如果路径比较失败，继续执行复制逻辑

            # 获取当前使用的生图引擎名称
            engine_name = "pollinations"  # 默认使用pollinations
            if hasattr(self, 'engine_combo'):
                current_engine = self.engine_combo.currentText()
                if 'Pollinations' in current_engine:
                    engine_name = 'pollinations'
                elif 'CogView-3 Flash' in current_engine:
                    engine_name = 'cogview_3_flash'
                elif 'ComfyUI 本地' in current_engine:
                    engine_name = 'comfyui'  # 统一使用comfyui目录
                elif 'ComfyUI 云端' in current_engine:
                    engine_name = 'comfyui'  # 统一使用comfyui目录
                elif 'DALL-E' in current_engine:
                    engine_name = 'dalle'
                elif 'Stability' in current_engine:
                    engine_name = 'stability'
                elif 'Imagen' in current_engine:
                    engine_name = 'imagen'
            elif hasattr(self, 'image_generation_service'):
                # 尝试从服务中获取引擎名称
                service_name = self.image_generation_service.__class__.__name__.lower()
                if 'pollinations' in service_name:
                    engine_name = 'pollinations'
                elif 'comfyui' in service_name:
                    engine_name = 'comfyui'  # 统一使用comfyui目录
                elif 'stable' in service_name:
                    engine_name = 'stability'
                elif 'dalle' in service_name or 'openai' in service_name:
                    engine_name = 'dalle'

            # 检查图片是否已经在对应的引擎目录中
            expected_engine_dir = project_dir / "images" / engine_name
            if expected_engine_dir in original_path.parents:
                logger.info(f"图像已在对应引擎目录中: {image_path}")
                return image_path

            # 创建目标目录：project/images/[engine-name]/
            target_dir = project_dir / "images" / engine_name
            target_dir.mkdir(parents=True, exist_ok=True)

            # 生成目标文件名
            # 使用简洁的文件名，不包含时间戳
            sequence = item.get('sequence', 'unknown')
            target_filename = f"{sequence}{original_path.suffix}"
            target_path = target_dir / target_filename

            # 如果原始文件存在，复制到目标位置
            if original_path.exists():
                shutil.copy2(str(original_path), str(target_path))
                logger.info(f"图像已复制到项目文件夹: {target_path}")
                return str(target_path)
            else:
                logger.warning(f"原始图像文件不存在: {image_path}")
                return image_path

        except Exception as e:
            logger.error(f"移动图像到项目文件夹失败: {e}")
            return image_path

    def _update_table_main_image(self, item, image_path):
        """更新表格中的主图显示

        Args:
            item: 镜头数据项
            image_path: 图像路径
        """
        try:
            # 查找对应的表格行
            for row, shot_data in enumerate(self.storyboard_data):
                if (shot_data.get('scene_id') == item.get('scene_id') and
                    shot_data.get('shot_id') == item.get('shot_id')):

                    # 更新数据
                    shot_data['image_path'] = image_path
                    shot_data['main_image_path'] = image_path

                    # 重新创建主图显示组件
                    self.create_main_image_widget(row, shot_data)
                    break

        except Exception as e:
            logger.error(f"更新表格主图显示失败: {e}")

    def _refresh_preview_if_current_shot(self, item, image_path):
        """如果当前选中的镜头是刚生成图像的镜头，刷新预览区域"""
        try:
            current_row = self.storyboard_table.currentRow()
            if current_row < 0:
                return

            # 获取当前选中镜头的数据索引
            data_index = self.get_data_index_by_table_row(current_row)
            if data_index < 0:
                return

            current_shot_data = self.storyboard_data[data_index]

            # 检查是否是同一个镜头
            if (current_shot_data.get('scene_id') == item.get('scene_id') and
                current_shot_data.get('shot_id') == item.get('shot_id')):

                logger.info(f"刷新预览区域，显示新生成的图像: {image_path}")

                # 更新预览图像
                self.load_preview_image(image_path)
                # 设置当前图像路径属性
                self.preview_label.setProperty('current_image_path', image_path)

                # 更新预览翻页控件和按钮状态
                self.update_preview_navigation(current_shot_data)

                # 如果当前不在图像预览标签页，可以选择是否自动切换
                if hasattr(self, 'detail_tabs'):
                    current_tab_text = self.detail_tabs.tabText(self.detail_tabs.currentIndex())
                    if current_tab_text != "图像预览":
                        # 可以选择是否自动切换到预览标签页
                        # 这里暂时不自动切换，让用户手动切换
                        pass

        except Exception as e:
            logger.error(f"刷新预览区域失败: {e}")

    def on_async_image_generated(self, item, success, image_path, error_msg):
        """异步图像生成完成回调"""
        if success and image_path:
            # 确保图像路径正确保存到项目的images文件夹中
            final_image_path = self._ensure_image_in_project_folder(image_path, item)

            item['image_path'] = final_image_path
            item['main_image_path'] = final_image_path

            # 添加到生成的图像列表中
            if 'generated_images' not in item:
                item['generated_images'] = []
            if final_image_path not in item['generated_images']:
                item['generated_images'].append(final_image_path)

            # 更新表格中的主图显示
            self._update_table_main_image(item, final_image_path)

            # 如果当前选中的镜头就是刚生成图像的镜头，刷新预览区域
            self._refresh_preview_if_current_shot(item, final_image_path)

            logger.info(f"镜头 {item.get('sequence', 'Unknown')} 图像生成成功: {final_image_path}")
            self.on_image_generated(item, True)
        else:
            logger.error(f"镜头 {item.get('sequence', 'Unknown')} 图像生成失败: {error_msg}")

            # 如果是ComfyUI相关错误，提供详细的诊断信息
            if error_msg and ("ComfyUI" in error_msg or "502" in error_msg or "Bad Gateway" in error_msg):
                self._show_comfyui_diagnostic_dialog(error_msg)

            self.on_image_generated(item, False, error_msg)

    def _show_comfyui_diagnostic_dialog(self, error_msg):
        """显示ComfyUI诊断对话框"""
        try:
            from src.utils.comfyui_helper import comfyui_helper
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel
            from PyQt5.QtCore import Qt

            # 获取诊断信息
            diagnostic_report = comfyui_helper.format_diagnostic_report()

            # 创建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("ComfyUI连接问题诊断")
            dialog.setModal(True)
            dialog.resize(600, 500)

            layout = QVBoxLayout(dialog)

            # 错误信息
            error_label = QLabel(f"错误信息: {error_msg}")
            error_label.setWordWrap(True)
            error_label.setStyleSheet("color: red; font-weight: bold; padding: 10px;")
            layout.addWidget(error_label)

            # 诊断报告
            report_text = QTextEdit()
            report_text.setPlainText(diagnostic_report)
            report_text.setReadOnly(True)
            layout.addWidget(report_text)

            # 关闭按钮
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)

            dialog.exec_()

        except Exception as e:
            logger.error(f"显示ComfyUI诊断对话框失败: {e}")

    def on_image_generated(self, item, success, error_message=None):
        """图像生成完成回调"""
        if success:
            item['status'] = '已生成'
            # 不要重新设置图像路径，因为在on_async_image_generated中已经正确设置了

            # 保存镜头图片关联信息到项目配置
            try:
                if self.project_manager:
                    self._save_shot_image_mapping(item)
            except Exception as e:
                logger.error(f"保存镜头图片关联信息失败: {e}")
        else:
            item['status'] = '失败'

            # 检测是否为失败情况，如果是则记录
            if error_message and self._is_image_generation_failed(error_message):
                # 找到项目在原始数据中的索引
                try:
                    item_index = self.storyboard_data.index(item)
                except ValueError:
                    item_index = 0
                self._record_generation_failure(item_index, item, error_message)

        self.update_item_status(item)

        # 继续处理下一个
        QTimer.singleShot(int(self.delay_spin.value() * 1000), self.process_generation_queue)
        
    def update_item_status(self, item):
        """更新项目状态显示"""
        for row, shot_data in enumerate(self.storyboard_data):
            if (shot_data['scene_id'] == item['scene_id'] and 
                shot_data['shot_id'] == item['shot_id']):
                
                # 更新状态列
                status_item = QTableWidgetItem(item['status'])
                if item['status'] == '已生成':
                    status_item.setBackground(QColor(144, 238, 144))
                elif item['status'] == '生成中':
                    status_item.setBackground(QColor(255, 255, 0))
                elif item['status'] == '失败':
                    status_item.setBackground(QColor(255, 182, 193))
                    
                self.storyboard_table.setItem(row, 7, status_item)
                break
                
    def get_generation_config(self, item):
        """获取生成配置"""
        # 确定使用哪个描述
        description = item['enhanced_description']
        if not description:
            description = item['consistency_description']
        if not description:
            description = item['original_description']

        # 获取当前选择的引擎
        current_engine = self.engine_combo.currentText()

        # 基础配置
        config = {
            'prompt': description,
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
            'seed': self.get_seed_value(),
            'batch_size': 1,  # 固定为1，因为CogView-3 Flash不支持批量生成
            'style': self.get_selected_style()  # 添加风格参数
        }

        # 根据引擎类型添加特定参数
        if "Pollinations" in current_engine:
            # Pollinations AI - 只包含支持的参数
            config.update({
                'model': 'flux',  # 默认模型
                'nologo': True,   # 去除logo
                'enhance': False, # 不增强
                'safe': True      # 安全模式
            })
            # 移除不支持的参数
            logger.info(f"Pollinations配置: {config}")
        else:
            # 其他引擎 - 包含完整参数
            config.update({
                'negative_prompt': self.negative_prompt_text.toPlainText(),
                'steps': self.steps_spin.value(),
                'cfg_scale': self.cfg_spin.value(),
                'sampler': self.sampler_combo.currentText()
            })

        return config
        
    def stop_generation(self):
        """停止生成"""
        self.is_generating = False
        self.finish_batch_generation()
        
    def finish_batch_generation(self):
        """完成批量生成"""
        # 恢复UI状态
        self.generate_selected_btn.setEnabled(True)
        self.generate_all_btn.setEnabled(True)
        self.stop_generation_btn.setEnabled(False)

        # 隐藏进度条
        self.progress_bar.setVisible(False)
        self.progress_label.setText("0/0")

        self.status_label.setText("批量生成完成")
        self.generation_finished.emit()

        # 检查是否有失败的生成，如果有则显示失败检测对话框
        if self.failed_generations:
            self.show_generation_failure_dialog()
        
    # 其他功能方法
    def generate_single_image(self, row):
        """生成单个图像"""
        if 0 <= row < len(self.storyboard_data):
            # 检查ComfyUI服务状态（如果使用ComfyUI引擎）
            current_engine = self.engine_combo.currentText()
            if current_engine == "ComfyUI":
                if not self._check_comfyui_service():
                    return

            item = self.storyboard_data[row]
            self.start_batch_generation([item])
            
    def preview_single_image(self, row):
        """预览单个图像"""
        if 0 <= row < len(self.storyboard_data):
            # 选中对应的表格行
            self.storyboard_table.selectRow(row)
            # 加载镜头详情
            self.load_shot_details(row)
            # 自动切换到图像预览标签页
            if hasattr(self, 'detail_tabs'):
                for i in range(self.detail_tabs.count()):
                    if self.detail_tabs.tabText(i) == "图像预览":
                        self.detail_tabs.setCurrentIndex(i)
                        break

    def detect_existing_images(self):
        """检测已生成的图片"""
        if not self.storyboard_data:
            QMessageBox.information(self, "提示", "没有分镜数据可供检测")
            return

        existing_count = 0
        total_count = len(self.storyboard_data)

        for i, item in enumerate(self.storyboard_data):
            if self._has_generated_image(i, item):
                existing_count += 1

        QMessageBox.information(
            self,
            "检测结果",
            f"检测完成！\n总镜头数: {total_count}\n已生成图片: {existing_count}\n未生成图片: {total_count - existing_count}"
        )

        # 刷新表格显示
        self.update_table()

    def _has_generated_image(self, item_index, item_data):
        """检测某个镜头是否已生成图片"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return False

            # 优先使用项目数据中的shot_image_mappings
            current_project = self.project_manager.current_project
            shot_mappings = current_project.get('shot_image_mappings', {})

            # 构建镜头键值
            scene_id = item_data.get('scene_id', '')
            shot_id = item_data.get('shot_id', '')
            shot_key = f"{scene_id}_{shot_id}"

            # 检查项目数据中的映射
            if shot_key in shot_mappings:
                shot_mapping = shot_mappings[shot_key]
                # 检查状态
                if shot_mapping.get('status') == '已生成':
                    # 检查主图片路径是否存在
                    main_image_path = shot_mapping.get('main_image_path', '')
                    if main_image_path and Path(main_image_path).exists():
                        return True

                    # 检查生成的图片列表
                    generated_images = shot_mapping.get('generated_images', [])
                    for image_path in generated_images:
                        if image_path and Path(image_path).exists():
                            return True

            # 如果项目数据中没有找到，回退到文件系统检测
            project_dir = Path(current_project['project_dir'])
            images_dir = project_dir / "images"

            if not images_dir.exists():
                return False

            # 检查各种可能的图片文件名格式
            possible_names = [
                f"shot_{item_index + 1}",
                f"scene_{item_data.get('scene', 1)}_shot_{item_data.get('sequence', item_index + 1)}",
                f"{item_data.get('sequence', item_index + 1)}",
                f"image_{item_index + 1}",
            ]

            # 检查常见图片格式
            image_extensions = ['.png', '.jpg', '.jpeg', '.webp']

            for name in possible_names:
                for ext in image_extensions:
                    # 检查各个引擎目录
                    for engine_dir in ['pollinations', 'comfyui', 'stable_diffusion']:
                        image_path = images_dir / engine_dir / f"{name}{ext}"
                        if image_path.exists():
                            return True

                    # 检查根目录
                    image_path = images_dir / f"{name}{ext}"
                    if image_path.exists():
                        return True

            return False

        except Exception as e:
            logger.error(f"检测图片失败: {e}")
            return False
            
    def generate_preview(self):
        """生成预览"""
        current_row = self.storyboard_table.currentRow()
        if current_row >= 0:
            self.generate_single_image(current_row)
            
    def set_as_main_image(self):
        """设为主图"""
        try:
            current_row = self.storyboard_table.currentRow()
            if current_row < 0:
                return

            data_index = self.get_data_index_by_table_row(current_row)
            if data_index < 0:
                return

            shot_data = self.storyboard_data[data_index]
            current_image = self.preview_label.property('current_image_path')

            if not current_image or not os.path.exists(current_image):
                QMessageBox.warning(self, "警告", "没有可设置的图像")
                return

            # 🔧 修复：设置为主图时，同时更新main_image_path和image_path
            shot_data['main_image_path'] = current_image
            shot_data['image_path'] = current_image  # 确保视频生成能正确获取主图

            # 更新表格中的主图显示
            self.create_main_image_widget(current_row, shot_data)

            # 保存到项目数据
            self.save_main_image_to_project(shot_data)

            QMessageBox.information(self, "成功", "已设为主图")
            logger.info(f"主图设置成功: {shot_data.get('shot_id', '')} -> {current_image}")
        except Exception as e:
            logger.error(f"设置主图失败: {e}")
            QMessageBox.critical(self, "错误", f"设置主图失败: {str(e)}")

    def delete_current_image(self):
        """删除当前图像"""
        try:
            current_row = self.storyboard_table.currentRow()
            if current_row < 0:
                return

            data_index = self.get_data_index_by_table_row(current_row)
            if data_index < 0:
                return

            shot_data = self.storyboard_data[data_index]
            current_image = self.preview_label.property('current_image_path')

            if not current_image or not os.path.exists(current_image):
                QMessageBox.warning(self, "警告", "没有可删除的图像")
                return

            # 确认删除
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除当前图像吗？\n{os.path.basename(current_image)}\n\n此操作不可撤销！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # 从生成的图像列表中移除
            generated_images = shot_data.get('generated_images', [])
            if current_image in generated_images:
                generated_images.remove(current_image)
                shot_data['generated_images'] = generated_images

            # 如果删除的是主图，需要重新设置主图
            if shot_data.get('main_image_path') == current_image:
                if generated_images:
                    # 设置第一张图为新的主图
                    shot_data['main_image_path'] = generated_images[0]
                    shot_data['image_path'] = generated_images[0]
                    shot_data['current_image_index'] = 0
                else:
                    # 没有其他图片了
                    shot_data['main_image_path'] = ''
                    shot_data['image_path'] = ''
                    shot_data['current_image_index'] = 0

            # 删除实际文件
            try:
                os.remove(current_image)
                logger.info(f"已删除图像文件: {current_image}")
            except Exception as e:
                logger.error(f"删除图像文件失败: {e}")
                QMessageBox.warning(self, "警告", f"删除文件失败: {str(e)}")

            # 更新预览显示
            if shot_data.get('main_image_path'):
                self.load_preview_image(shot_data['main_image_path'])
                self.preview_label.setProperty('current_image_path', shot_data['main_image_path'])
            else:
                self.preview_label.setText("暂无预览图像")
                self.preview_label.setProperty('current_image_path', None)

            # 更新预览翻页控件和按钮状态
            self.update_preview_navigation(shot_data)

            # 更新表格中的主图显示
            self.create_main_image_widget(current_row, shot_data)

            # 🔧 修复：删除项目数据中的图像记录
            self._remove_image_from_project_data(current_image, shot_data)

            # 保存到项目数据
            self.save_main_image_to_project(shot_data)

            QMessageBox.information(self, "成功", "图像已删除")

        except Exception as e:
            logger.error(f"删除图像失败: {e}")
            QMessageBox.critical(self, "错误", f"删除图像失败: {str(e)}")

    def _remove_image_from_project_data(self, image_path: str, shot_data: Dict[str, Any]):
        """🔧 新增：从项目数据中删除图像记录"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_data = self.project_manager.get_project_data()
            if not project_data:
                return

            # 获取镜头标识
            scene_id = shot_data.get('scene_id', '')
            shot_id = shot_data.get('shot_id', '')
            shot_key = f"{scene_id}_{shot_id}"

            logger.info(f"从项目数据中删除图像: {image_path}, 镜头: {shot_key}")

            # 1. 从图像生成数据中删除
            image_generation = project_data.get('image_generation', {})
            shot_image_mappings = image_generation.get('shot_image_mappings', {})

            if shot_key in shot_image_mappings:
                shot_images = shot_image_mappings[shot_key]
                if isinstance(shot_images, dict):
                    generated_images = shot_images.get('generated_images', [])
                    if image_path in generated_images:
                        generated_images.remove(image_path)
                        logger.info(f"从shot_image_mappings中删除图像: {image_path}")

                    # 如果删除的是主图，更新主图路径
                    if shot_images.get('main_image_path') == image_path:
                        if generated_images:
                            shot_images['main_image_path'] = generated_images[0]
                        else:
                            shot_images['main_image_path'] = ''
                        logger.info(f"更新主图路径: {shot_images.get('main_image_path', '无')}")

            # 2. 从五阶段分镜数据中删除
            storyboard_data = project_data.get('storyboard_generation', {})
            stage_5_data = storyboard_data.get('stage_5_final_storyboard', [])

            for scene in stage_5_data:
                if isinstance(scene, dict) and scene.get('scene_id') == scene_id:
                    shots = scene.get('shots', [])
                    for shot in shots:
                        if isinstance(shot, dict) and shot.get('shot_id') == shot_id:
                            # 删除图像路径
                            if shot.get('image_path') == image_path:
                                shot['image_path'] = ''
                            if shot.get('main_image_path') == image_path:
                                shot['main_image_path'] = ''

                            # 从生成的图像列表中删除
                            generated_images = shot.get('generated_images', [])
                            if image_path in generated_images:
                                generated_images.remove(image_path)
                                shot['generated_images'] = generated_images

                            logger.info(f"从五阶段分镜数据中删除图像: {image_path}")
                            break

            # 3. 从文件路径映射中删除
            file_paths = project_data.get('file_paths', {})
            images_paths = file_paths.get('images', {})

            # 查找并删除对应的图像路径记录
            keys_to_remove = []
            for key, path in images_paths.items():
                if path == image_path:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del images_paths[key]
                logger.info(f"从文件路径映射中删除图像记录: {key} -> {image_path}")

            # 4. 保存更新后的项目数据
            self.project_manager.save_project_data(project_data)
            logger.info(f"项目数据已更新，图像 {image_path} 的所有记录已删除")

        except Exception as e:
            logger.error(f"从项目数据中删除图像记录失败: {e}")

    def _cleanup_orphaned_image_records(self):
        """🔧 新增：清理孤立的图像记录（文件已删除但数据库中仍有记录）"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return 0

            project_data = self.project_manager.get_project_data()
            if not project_data:
                return 0

            cleaned_count = 0

            # 清理shot_image_mappings中的孤立记录
            image_generation = project_data.get('image_generation', {})
            shot_image_mappings = image_generation.get('shot_image_mappings', {})

            for shot_key, shot_images in shot_image_mappings.items():
                if isinstance(shot_images, dict):
                    generated_images = shot_images.get('generated_images', [])
                    valid_images = []

                    for image_path in generated_images:
                        if os.path.exists(image_path):
                            valid_images.append(image_path)
                        else:
                            logger.info(f"清理孤立图像记录: {image_path}")
                            cleaned_count += 1

                    shot_images['generated_images'] = valid_images

                    # 检查主图是否仍然存在
                    main_image_path = shot_images.get('main_image_path', '')
                    if main_image_path and not os.path.exists(main_image_path):
                        if valid_images:
                            shot_images['main_image_path'] = valid_images[0]
                        else:
                            shot_images['main_image_path'] = ''
                        cleaned_count += 1

            # 清理文件路径映射中的孤立记录
            file_paths = project_data.get('file_paths', {})
            images_paths = file_paths.get('images', {})

            keys_to_remove = []
            for key, path in images_paths.items():
                if not os.path.exists(path):
                    keys_to_remove.append(key)
                    cleaned_count += 1

            for key in keys_to_remove:
                del images_paths[key]
                logger.info(f"清理孤立文件路径记录: {key}")

            if cleaned_count > 0:
                self.project_manager.save_project_data(project_data)
                logger.info(f"清理完成，共清理了 {cleaned_count} 个孤立的图像记录")

            return cleaned_count

        except Exception as e:
            logger.error(f"清理孤立图像记录失败: {e}")
            return 0
                
    def open_image_folder(self):
        """打开图像文件夹"""
        if self.project_manager and self.project_manager.current_project:
            project_path = Path(self.project_manager.current_project['project_dir'])
            images_path = project_path / "images"
            
            if images_path.exists():
                os.startfile(str(images_path))
            else:
                QMessageBox.information(self, "提示", "图像文件夹不存在，将在生成图像时自动创建")
        else:
            QMessageBox.warning(self, "警告", "请先打开项目")
            
    # 描述编辑相关方法
    def on_consistency_desc_changed(self):
        """一致性描述改变"""
        current_row = self.storyboard_table.currentRow()
        if current_row >= 0:
            self.storyboard_data[current_row]['consistency_description'] = \
                self.consistency_desc_text.toPlainText()
            self.storyboard_table.setItem(
                current_row, 3, 
                QTableWidgetItem(self.consistency_desc_text.toPlainText())
            )
            
    def on_enhanced_desc_changed(self):
        """增强描述改变"""
        current_row = self.storyboard_table.currentRow()
        if current_row >= 0:
            self.storyboard_data[current_row]['enhanced_description'] = \
                self.enhanced_desc_text.toPlainText()
            self.storyboard_table.setItem(
                current_row, 4, 
                QTableWidgetItem(self.enhanced_desc_text.toPlainText())
            )
            
    def save_enhanced_to_consistency(self):
        """🔧 修复：保存增强描述到一致性描述，并同步更新到JSON文件"""
        current_row = self.storyboard_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择一个镜头")
            return

        enhanced_text = self.enhanced_desc_text.toPlainText()
        if not enhanced_text.strip():
            QMessageBox.warning(self, "警告", "增强描述为空，无法保存")
            return

        try:
            # 获取当前镜头数据
            data_index = self.get_data_index_by_table_row(current_row)
            if data_index < 0:
                QMessageBox.warning(self, "警告", "无法获取镜头数据")
                return

            shot_data = self.storyboard_data[data_index]

            # 将增强描述复制到一致性描述
            self.consistency_desc_text.setPlainText(enhanced_text)
            shot_data['consistency_description'] = enhanced_text
            self.storyboard_table.setItem(
                current_row, 3,
                QTableWidgetItem(enhanced_text)
            )

            # 同步更新到一致性描述文件
            self._update_consistency_file(shot_data, enhanced_text)

            # 保存到项目数据
            self.save_project_data()

            QMessageBox.information(self, "成功", "增强描述已保存到一致性描述，并同步更新到JSON文件")

        except Exception as e:
            logger.error(f"保存增强描述到一致性失败: {e}")
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
        
    def save_project_data(self):
        """保存项目数据到文件"""
        try:
            if hasattr(self, 'project_manager') and self.project_manager:
                # 更新项目管理器中的数据
                for shot_data in self.storyboard_data:
                    scene_id = shot_data['scene_id']
                    shot_id = shot_data['shot_id']

                    # 更新场景数据中的一致性描述
                    if hasattr(self.project_manager, 'scenes') and scene_id in self.project_manager.scenes:
                        scene = self.project_manager.scenes[scene_id]
                        for shot in scene.get('shots', []):
                            if shot.get('shot_id') == shot_id:
                                shot['consistency_description'] = shot_data['consistency_description']
                                shot['enhanced_description'] = shot_data['enhanced_description']
                                break

                # 保存项目文件
                self.project_manager.save_project()
                logger.info("项目数据已保存")
            else:
                logger.warning("项目管理器未初始化，无法保存数据")
        except Exception as e:
            logger.error(f"保存项目数据失败: {e}")
            QMessageBox.warning(self, "错误", f"保存项目数据失败: {e}")

    def get_project_data(self) -> Dict[str, Any]:
        """获取项目数据（用于项目保存）"""
        try:
            # 收集分镜图像生成相关的数据
            image_generation_data = {}

            # 保存图像生成设置
            if hasattr(self, 'engine_combo'):
                image_generation_settings = {
                    'engine': self.engine_combo.currentText(),
                    'width': self.width_spin.value() if hasattr(self, 'width_spin') else 1024,
                    'height': self.height_spin.value() if hasattr(self, 'height_spin') else 1024,
                    'seed_mode': self.seed_combo.currentText() if hasattr(self, 'seed_combo') else 'random',
                    'delay': self.delay_spin.value() if hasattr(self, 'delay_spin') else 3.0,
                    'skip_existing': self.skip_existing_cb.isChecked() if hasattr(self, 'skip_existing_cb') else False
                }

                # 添加引擎特定设置
                if "Pollinations" in image_generation_settings['engine']:
                    if hasattr(self, 'pollinations_model_combo'):
                        image_generation_settings['pollinations_model'] = self.pollinations_model_combo.currentText()
                    if hasattr(self, 'pollinations_enhance_check'):
                        image_generation_settings['pollinations_enhance'] = self.pollinations_enhance_check.isChecked()
                    if hasattr(self, 'pollinations_logo_check'):
                        image_generation_settings['pollinations_nologo'] = not self.pollinations_logo_check.isChecked()
                else:
                    # 其他引擎的设置
                    if hasattr(self, 'steps_spin'):
                        image_generation_settings['steps'] = self.steps_spin.value()
                    if hasattr(self, 'cfg_spin'):
                        image_generation_settings['cfg_scale'] = self.cfg_spin.value()
                    if hasattr(self, 'sampler_combo'):
                        image_generation_settings['sampler'] = self.sampler_combo.currentText()
                    if hasattr(self, 'negative_prompt_text'):
                        image_generation_settings['negative_prompt'] = self.negative_prompt_text.toPlainText()

                image_generation_data['image_generation_settings'] = image_generation_settings

            # 保存分镜数据和图像关联信息
            if hasattr(self, 'storyboard_data') and self.storyboard_data:
                shots_data = []
                for shot_data in self.storyboard_data:
                    shot_info = {
                        'scene_id': shot_data.get('scene_id', ''),
                        'shot_id': shot_data.get('shot_id', ''),
                        'sequence': shot_data.get('sequence', ''),
                        'consistency_description': shot_data.get('consistency_description', ''),
                        'enhanced_description': shot_data.get('enhanced_description', ''),
                        'status': shot_data.get('status', '未生成'),
                        'image_path': shot_data.get('image_path', ''),
                        'main_image_path': shot_data.get('main_image_path', ''),
                        'generated_images': shot_data.get('generated_images', []),
                        'current_image_index': shot_data.get('current_image_index', 0)
                    }
                    shots_data.append(shot_info)

                image_generation_data['shots_data'] = shots_data

            return image_generation_data

        except Exception as e:
            logger.error(f"获取分镜图像生成数据失败: {e}")
            return {}
            
    def apply_consistency(self):
        """🔧 修复：应用一致性 - 从原始描述重新生成一致性描述"""
        current_row = self.storyboard_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择一个镜头")
            return

        try:
            # 获取当前镜头数据
            data_index = self.get_data_index_by_table_row(current_row)
            if data_index < 0:
                QMessageBox.warning(self, "警告", "无法获取镜头数据")
                return

            shot_data = self.storyboard_data[data_index]
            original_desc = shot_data.get('original_description', '')

            if not original_desc.strip():
                QMessageBox.warning(self, "警告", "原始描述为空，无法应用一致性")
                return

            # 显示进度对话框
            progress_dialog = QProgressDialog("正在应用一致性处理...", "取消", 0, 0, self)
            progress_dialog.setModal(True)
            progress_dialog.show()

            # 调用一致性处理器重新生成一致性描述
            consistency_desc = self._apply_consistency_processing(original_desc)

            progress_dialog.close()

            if consistency_desc and consistency_desc.strip():
                # 更新一致性描述
                self.consistency_desc_text.setPlainText(consistency_desc)
                shot_data['consistency_description'] = consistency_desc

                # 更新表格显示
                consistency_item = QTableWidgetItem(consistency_desc)
                self.storyboard_table.setItem(current_row, 3, consistency_item)

                # 保存到项目数据
                self.save_project_data()

                QMessageBox.information(self, "成功", "一致性处理完成！已重新生成一致性描述。")
            else:
                QMessageBox.warning(self, "警告", "一致性处理失败，请稍后重试")

        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.close()
            logger.error(f"应用一致性失败: {e}")
            QMessageBox.critical(self, "错误", f"应用一致性失败: {str(e)}")
        
    def reset_consistency(self):
        """重置一致性描述"""
        current_row = self.storyboard_table.currentRow()
        if current_row >= 0:
            # 重置为原始的一致性描述或原始描述
            original_consistency = self.storyboard_data[current_row].get('original_consistency_description', '')
            if not original_consistency:
                original_consistency = self.storyboard_data[current_row]['original_description']
            self.consistency_desc_text.setPlainText(original_consistency)
            
    def enhance_description(self):
        """智能增强描述 - 支持单个镜头和批量增强"""
        # 🔧 新增：检查工作流程模式
        if self.workflow_status['current_mode'] == 'voice_first':
            if not self.workflow_status['voice_data_received']:
                # 显示配音优先模式提醒
                if self._show_workflow_mode_warning():
                    return  # 用户选择切换到配音界面

                # 用户选择继续，显示额外警告
                reply = QMessageBox.warning(
                    self,
                    "配音优先模式警告",
                    "当前项目使用配音优先工作流程，但尚未完成配音生成。\n\n"
                    "如果您现在进行增强描述：\n"
                    "• 增强描述将基于原始分镜内容\n"
                    "• 后续配音生成会覆盖这些描述\n"
                    "• 可能导致图像与配音内容不匹配\n\n"
                    "建议：先完成配音生成，再进行图像生成。\n\n"
                    "是否仍要继续增强描述？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.No:
                    return
            else:
                # 已有配音数据，提醒可能的冲突
                reply = QMessageBox.question(
                    self,
                    "配音优先模式提醒",
                    "检测到您已完成配音生成。\n\n"
                    "在配音优先模式下：\n"
                    "• 图像提示词应基于配音内容生成\n"
                    "• 手动增强描述可能与配音内容不匹配\n\n"
                    "建议：使用基于配音内容的自动生成功能。\n\n"
                    "是否仍要手动增强描述？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.No:
                    return

        current_row = self.storyboard_table.currentRow()

        # 询问用户是否要批量增强所有镜头
        reply = QMessageBox.question(
            self,
            "智能增强选择",
            "请选择增强模式：\n\n"
            "• 是：增强所有镜头（推荐）\n"
            "• 否：仅增强当前选中的镜头\n"
            "• 取消：取消操作",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Cancel:
            return
        elif reply == QMessageBox.StandardButton.Yes:
            # 批量增强所有镜头
            self._enhance_all_descriptions()
        else:
            # 增强单个镜头
            self._enhance_single_description(current_row)

    def _enhance_all_descriptions(self):
        """批量增强所有镜头的描述"""
        if not self.storyboard_data:
            QMessageBox.warning(self, "警告", "没有可增强的镜头数据")
            return

        try:
            # 显示进度对话框
            progress_dialog = QProgressDialog("正在批量增强所有镜头描述...", "取消", 0, len(self.storyboard_data), self)
            progress_dialog.setModal(True)
            progress_dialog.show()

            enhanced_count = 0
            failed_count = 0

            for i, shot_data in enumerate(self.storyboard_data):
                if progress_dialog.wasCanceled():
                    break

                progress_dialog.setValue(i)
                progress_dialog.setLabelText(f"正在增强第 {i+1}/{len(self.storyboard_data)} 个镜头...")
                QApplication.processEvents()

                original_content = shot_data.get('consistency_description', '')
                if not original_content.strip():
                    logger.warning(f"镜头 {shot_data.get('sequence', i+1)} 的一致性描述为空，跳过")
                    failed_count += 1
                    continue

                try:
                    # 调用描述增强器
                    enhanced_content = self._call_description_enhancer(original_content)

                    if enhanced_content and enhanced_content.strip():
                        # 更新镜头数据
                        shot_data['enhanced_description'] = enhanced_content
                        enhanced_count += 1

                        # 更新表格显示（如果该行可见）
                        for row in range(self.storyboard_table.rowCount()):
                            if self.get_data_index_by_table_row(row) == i:
                                enhanced_item = QTableWidgetItem(enhanced_content)
                                self.storyboard_table.setItem(row, 4, enhanced_item)
                                break

                        # 同步更新到JSON文件
                        self._update_consistency_file(shot_data, enhanced_content)

                        # 同步更新到prompt.json文件
                        self._update_prompt_json_file(shot_data, enhanced_content)

                        logger.info(f"镜头 {shot_data.get('sequence', i+1)} 增强完成")
                    else:
                        logger.warning(f"镜头 {shot_data.get('sequence', i+1)} 增强失败")
                        failed_count += 1

                except Exception as e:
                    logger.error(f"镜头 {shot_data.get('sequence', i+1)} 增强异常: {e}")
                    failed_count += 1

            progress_dialog.close()

            # 显示结果
            if enhanced_count > 0:
                message = f"批量增强完成！\n\n成功增强: {enhanced_count} 个镜头"
                if failed_count > 0:
                    message += f"\n失败/跳过: {failed_count} 个镜头"
                QMessageBox.information(self, "批量增强完成", message)

                # 刷新当前选中镜头的显示
                current_row = self.storyboard_table.currentRow()
                if current_row >= 0:
                    self.load_shot_details(current_row)
            else:
                QMessageBox.warning(self, "批量增强失败", f"没有成功增强任何镜头\n失败/跳过: {failed_count} 个镜头")

        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.close()
            logger.error(f"批量增强失败: {e}")
            QMessageBox.critical(self, "错误", f"批量增强失败: {str(e)}")

    def _enhance_single_description(self, current_row):
        """增强单个镜头的描述"""
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择一个镜头")
            return

        # 获取当前镜头数据
        data_index = self.get_data_index_by_table_row(current_row)
        if data_index < 0:
            QMessageBox.warning(self, "警告", "无法获取镜头数据")
            return

        shot_data = self.storyboard_data[data_index]
        original_content = shot_data.get('consistency_description', '')

        if not original_content.strip():
            QMessageBox.warning(self, "警告", "一致性描述为空，无法增强")
            return

        try:
            # 显示进度对话框
            progress_dialog = QProgressDialog("正在增强描述...", "取消", 0, 0, self)
            progress_dialog.setModal(True)
            progress_dialog.show()

            # 调用描述增强器
            enhanced_content = self._call_description_enhancer(original_content)

            progress_dialog.close()

            if enhanced_content and enhanced_content.strip():
                # 更新增强描述
                self.enhanced_desc_text.setPlainText(enhanced_content)
                shot_data['enhanced_description'] = enhanced_content

                # 更新表格显示
                enhanced_item = QTableWidgetItem(enhanced_content)
                self.storyboard_table.setItem(current_row, 4, enhanced_item)

                # 同步更新到JSON文件
                self._update_consistency_file(shot_data, enhanced_content)

                # 同步更新到prompt.json文件
                self._update_prompt_json_file(shot_data, enhanced_content)

                QMessageBox.information(self, "成功", "描述增强完成！")
            else:
                QMessageBox.warning(self, "警告", "增强失败，请稍后重试")

        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.close()
            logger.error(f"描述增强失败: {e}")
            QMessageBox.critical(self, "错误", f"描述增强失败: {str(e)}")

    def _call_description_enhancer(self, original_content):
        """调用描述增强器"""
        try:
            # 导入场景描述增强器
            from src.processors.scene_description_enhancer import SceneDescriptionEnhancer

            # 获取项目根目录
            project_root = None
            if self.project_manager and self.project_manager.current_project:
                project_root = self.project_manager.current_project['project_dir']

            if not project_root:
                raise Exception("无法获取项目根目录，请确保已打开项目")

            # 🔧 修复：获取LLM API，使用与其他界面相同的方式
            llm_api = self._init_llm_api()

            # 创建增强器实例
            enhancer = SceneDescriptionEnhancer(
                project_root=str(project_root),
                llm_api=llm_api
            )

            # 🔧 修复：调用真正的LLM智能增强功能
            enhanced_result = enhancer.enhance_description_with_llm(original_content)

            return enhanced_result

        except Exception as e:
            logger.error(f"调用描述增强器失败: {e}")
            raise

    def _init_llm_api(self):
        """🔧 新增：初始化LLM服务，使用与其他界面相同的方式"""
        try:
            from src.core.service_manager import ServiceManager, ServiceType

            service_manager = ServiceManager()
            llm_service = service_manager.get_service(ServiceType.LLM)

            if llm_service:
                logger.info("LLM服务初始化成功")
                return llm_service
            else:
                logger.warning("未找到LLM服务，智能增强将使用传统方法")
                return None

        except Exception as e:
            logger.error(f"初始化LLM服务失败: {e}")
            return None

    def _apply_consistency_processing(self, original_description):
        """🔧 新增：应用一致性处理，重新生成一致性描述"""
        try:
            # 导入场景描述增强器
            from src.processors.scene_description_enhancer import SceneDescriptionEnhancer

            # 获取项目根目录
            project_root = None
            if self.project_manager and self.project_manager.current_project:
                project_root = self.project_manager.current_project['project_dir']

            if not project_root:
                raise Exception("无法获取项目根目录，请确保已打开项目")

            # 🔧 修复：获取LLM API，使用与其他界面相同的方式
            llm_api = self._init_llm_api()

            # 创建增强器实例
            enhancer = SceneDescriptionEnhancer(
                project_root=str(project_root),
                llm_api=llm_api
            )

            # 调用一致性处理功能（不使用LLM增强，只应用一致性）
            consistency_result = enhancer.enhance_description(original_description)

            return consistency_result

        except Exception as e:
            logger.error(f"一致性处理失败: {e}")
            raise

    def _update_consistency_file(self, shot_data, enhanced_content):
        """更新一致性描述文件"""
        try:
            if not hasattr(self, 'consistency_file_path') or not self.consistency_file_path:
                logger.warning("没有一致性文件路径，无法更新")
                return

            # 读取当前文件内容
            with open(self.consistency_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 查找并更新对应的镜头
            scenes = data.get('scenes', [])
            scene_index = shot_data.get('scene_index', 1)
            shot_number = shot_data.get('shot_number_in_scene', 1)

            for scene in scenes:
                if scene.get('scene_index') == scene_index:
                    shots = scene.get('shots', [])
                    for shot in shots:
                        if shot.get('shot_number') == shot_number:
                            # 更新content字段
                            shot['content'] = enhanced_content
                            logger.info(f"更新场景{scene_index}镜头{shot_number}的content字段")
                            break
                    break

            # 保存文件
            with open(self.consistency_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"成功更新一致性描述文件: {self.consistency_file_path}")

        except Exception as e:
            logger.error(f"更新一致性描述文件失败: {e}")
            # 不抛出异常，因为这不是关键功能

    def _update_prompt_json_file(self, shot_data, enhanced_content):
        """更新prompt.json文件中的增强描述"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有项目管理器或当前项目，无法更新prompt.json")
                return

            project_dir = Path(self.project_manager.current_project['project_dir'])
            prompt_file = project_dir / 'texts' / 'prompt.json'

            if not prompt_file.exists():
                logger.warning("prompt.json文件不存在，无法更新")
                return

            # 读取当前文件内容
            with open(prompt_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 查找并更新对应的镜头
            scenes = data.get('scenes', {})
            scene_index = shot_data.get('scene_index', 1)
            shot_number_in_scene = shot_data.get('shot_number_in_scene', 1)

            # 计算全局镜头编号
            global_shot_number = 1
            found = False

            for scene_name, shots in scenes.items():
                for shot in shots:
                    if global_shot_number == self._get_global_shot_number(shot_data):
                        # 更新enhanced_prompt字段
                        shot['enhanced_prompt'] = enhanced_content
                        logger.info(f"更新镜头{global_shot_number}的enhanced_prompt字段")
                        found = True
                        break
                    global_shot_number += 1
                if found:
                    break

            if found:
                # 保存文件
                with open(prompt_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"成功更新prompt.json文件: {prompt_file}")
            else:
                logger.warning(f"在prompt.json中未找到对应的镜头数据")

        except Exception as e:
            logger.error(f"更新prompt.json文件失败: {e}")
            # 不抛出异常，因为这不是关键功能

    def _get_global_shot_number(self, shot_data):
        """获取镜头的全局编号"""
        # 在storyboard_data中查找当前镜头的位置
        for i, data in enumerate(self.storyboard_data):
            if (data.get('scene_index') == shot_data.get('scene_index') and
                data.get('shot_number_in_scene') == shot_data.get('shot_number_in_scene')):
                return i + 1
        return 1
        
    def reset_enhanced(self):
        """重置增强描述"""
        current_row = self.storyboard_table.currentRow()
        if current_row >= 0:
            consistency_desc = self.storyboard_data[current_row]['consistency_description']
            if not consistency_desc:
                consistency_desc = self.storyboard_data[current_row]['original_description']
            self.enhanced_desc_text.setPlainText(consistency_desc)
            
    # 参数管理方法
    def on_parameter_changed(self):
        """参数改变时同步到AI绘图设置界面并触发自动保存"""
        try:
            # 同步到AI绘图设置界面
            self.sync_to_ai_drawing_settings()

            # 触发自动保存
            if hasattr(self, 'auto_save_timer'):
                self.auto_save_timer.stop()
                self.auto_save_timer.start(self.auto_save_delay)
        except Exception as e:
            logger.error(f"参数同步失败: {e}")

    def sync_to_ai_drawing_settings(self):
        """同步参数到AI绘图设置界面"""
        try:
            # 查找AI绘图设置界面
            ai_drawing_widget = self.find_ai_drawing_widget()
            if not ai_drawing_widget:
                return

            # 同步基础参数
            if hasattr(ai_drawing_widget, 'width_spin'):
                ai_drawing_widget.width_spin.setValue(self.width_spin.value())
            if hasattr(ai_drawing_widget, 'height_spin'):
                ai_drawing_widget.height_spin.setValue(self.height_spin.value())
            if hasattr(ai_drawing_widget, 'seed_combo'):
                ai_drawing_widget.seed_combo.setCurrentText(self.seed_combo.currentText())

            # 同步Pollinations特有参数
            if hasattr(ai_drawing_widget, 'pollinations_model_combo') and hasattr(self, 'pollinations_model_combo'):
                ai_drawing_widget.pollinations_model_combo.setCurrentText(self.pollinations_model_combo.currentText())
            if hasattr(ai_drawing_widget, 'pollinations_enhance_check') and hasattr(self, 'pollinations_enhance_check'):
                ai_drawing_widget.pollinations_enhance_check.setChecked(self.pollinations_enhance_check.isChecked())
            if hasattr(ai_drawing_widget, 'pollinations_logo_check') and hasattr(self, 'pollinations_logo_check'):
                ai_drawing_widget.pollinations_logo_check.setChecked(self.pollinations_logo_check.isChecked())

            logger.info("参数已同步到AI绘图设置界面")

        except Exception as e:
            logger.error(f"同步参数到AI绘图设置界面失败: {e}")

    def find_ai_drawing_widget(self):
        """查找AI绘图设置界面"""
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

            # 查找设置标签页
            tab_widget = main_window.tab_widget
            for i in range(tab_widget.count()):
                tab_text = tab_widget.tabText(i)
                if "设置" in tab_text:
                    settings_tab = tab_widget.widget(i)
                    # 在设置标签页中查找AI绘图子标签页
                    if hasattr(settings_tab, 'tab_widget'):
                        settings_tab_widget = settings_tab.tab_widget
                        for j in range(settings_tab_widget.count()):
                            sub_tab_text = settings_tab_widget.tabText(j)
                            if "AI绘图" in sub_tab_text:
                                ai_drawing_tab = settings_tab_widget.widget(j)
                                # 查找AI绘图设置组件
                                if hasattr(ai_drawing_tab, 'ai_drawing_widget'):
                                    return ai_drawing_tab.ai_drawing_widget
            return None

        except Exception as e:
            logger.error(f"查找AI绘图设置界面失败: {e}")
            return None
            
    def get_seed_value(self):
        """根据种子模式获取种子值"""
        import random
        if self.seed_combo.currentText() == "随机":
            return random.randint(0, 2147483647)
        else:  # 固定
            # 生成一个固定的种子值，基于当前时间戳
            import time
            return int(time.time()) % 2147483647
            
    def save_generation_settings(self):
        """保存生成设置到项目文件"""
        try:
            # 优先使用传入的项目管理器，然后尝试从应用控制器获取
            project_manager = self.project_manager
            if not project_manager:
                from src.core.app_controller import AppController
                app_controller = AppController.get_instance()
                if app_controller and hasattr(app_controller, 'project_manager'):
                    project_manager = app_controller.project_manager

            # 检查项目管理器和当前项目
            if not project_manager:
                QMessageBox.warning(self, "警告", "项目管理器未初始化，无法保存设置")
                return

            if not project_manager.current_project:
                QMessageBox.warning(self, "警告", "没有打开的项目，无法保存设置")
                return

            project_data = project_manager.current_project

            # 保存图像生成设置
            if 'image_generation_settings' not in project_data:
                project_data['image_generation_settings'] = {}

            # 获取当前引擎设置
            current_engine = self.engine_combo.currentText()

            # 收集所有参数
            settings = {
                'engine': current_engine,
                'width': self.width_spin.value(),
                'height': self.height_spin.value(),
                'seed_mode': self.seed_combo.currentText(),
                'seed_value': self.get_seed_value(),
                'retry_count': self.retry_count_spin.value(),
                'delay': self.delay_spin.value()
            }

            # 添加引擎特定参数
            if "Pollinations" in current_engine:
                if hasattr(self, 'pollinations_model_combo'):
                    settings.update({
                        'pollinations_model': self.pollinations_model_combo.currentText(),
                        'pollinations_enhance': self.pollinations_enhance_check.isChecked(),
                        'pollinations_logo': self.pollinations_logo_check.isChecked()
                    })
            else:
                # 其他引擎的参数
                settings.update({
                    'steps': self.steps_spin.value(),
                    'cfg_scale': self.cfg_spin.value(),
                    'sampler': self.sampler_combo.currentText(),
                    'negative_prompt': self.negative_prompt_text.toPlainText()
                })

            project_data['image_generation_settings'].update(settings)

            # 同步到AI绘图标签
            self.sync_to_ai_drawing_tab()

            # 保存项目 - 使用StoryboardProjectManager的save_project方法
            try:
                # 更新最后修改时间
                project_data['last_modified'] = datetime.now().isoformat()

                # 保存项目文件
                project_file = os.path.join(project_data['project_dir'], 'project.json')
                with open(project_file, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(self, "成功", "设置已保存到项目文件并同步到AI绘图标签")
                logger.info(f"图像生成设置已保存到项目: {project_data.get('project_name', 'Unknown')}")

            except Exception as save_error:
                logger.error(f"保存项目文件失败: {save_error}")
                QMessageBox.warning(self, "警告", f"保存设置失败: {str(save_error)}")

        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")



    def auto_save_settings(self):
        """自动保存设置（静默保存，不显示消息框）"""
        try:
            # 优先使用传入的项目管理器，然后尝试从应用控制器获取
            project_manager = self.project_manager
            if not project_manager:
                from src.core.app_controller import AppController
                app_controller = AppController.get_instance()
                if app_controller and hasattr(app_controller, 'project_manager'):
                    project_manager = app_controller.project_manager

            # 检查是否有项目管理器和当前项目
            if not project_manager or not project_manager.current_project:
                return  # 静默返回，不显示错误

            project_data = project_manager.current_project

            # 保存图像生成设置
            if 'image_generation_settings' not in project_data:
                project_data['image_generation_settings'] = {}

            # 获取当前引擎设置
            current_engine = self.engine_combo.currentText()

            # 收集所有参数
            settings = {
                'engine': current_engine,
                'width': self.width_spin.value(),
                'height': self.height_spin.value(),
                'seed_mode': self.seed_combo.currentText(),
                'seed_value': self.get_seed_value(),
                'retry_count': self.retry_count_spin.value(),
                'delay': self.delay_spin.value()
            }

            # 添加引擎特定参数
            if "Pollinations" in current_engine:
                if hasattr(self, 'pollinations_model_combo'):
                    settings.update({
                        'pollinations_model': self.pollinations_model_combo.currentText(),
                        'pollinations_enhance': self.pollinations_enhance_check.isChecked(),
                        'pollinations_logo': self.pollinations_logo_check.isChecked()
                    })
            else:
                # 其他引擎的参数
                settings.update({
                    'steps': self.steps_spin.value(),
                    'cfg_scale': self.cfg_spin.value(),
                    'sampler': self.sampler_combo.currentText(),
                    'negative_prompt': self.negative_prompt_text.toPlainText()
                })

            project_data['image_generation_settings'].update(settings)

            # 静默保存项目文件
            try:
                # 更新最后修改时间
                project_data['last_modified'] = datetime.now().isoformat()

                # 保存项目文件
                project_file = os.path.join(project_data['project_dir'], 'project.json')
                with open(project_file, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, ensure_ascii=False, indent=2)

                logger.debug(f"图像生成设置已自动保存到项目: {project_data.get('project_name', 'Unknown')}")

            except Exception as save_error:
                logger.error(f"自动保存项目文件失败: {save_error}")

        except Exception as e:
            logger.error(f"自动保存设置失败: {e}")
            
    def load_generation_settings(self):
        """从项目文件加载生成设置"""
        try:
            # 优先使用传入的项目管理器，然后尝试从应用控制器获取
            project_manager = self.project_manager
            if not project_manager:
                from src.core.app_controller import AppController
                app_controller = AppController.get_instance()
                if app_controller and hasattr(app_controller, 'project_manager'):
                    project_manager = app_controller.project_manager

            if project_manager and project_manager.current_project:
                project_data = project_manager.current_project
                settings = project_data.get('image_generation_settings', {})
                
                if settings:
                    # 加载引擎设置
                    engine = settings.get('engine', 'Pollinations AI')
                    for i in range(self.engine_combo.count()):
                        if engine in self.engine_combo.itemText(i):
                            self.engine_combo.setCurrentIndex(i)
                            break
                    
                    self.width_spin.setValue(settings.get('width', 1024))
                    self.height_spin.setValue(settings.get('height', 1024))
                    self.seed_combo.setCurrentText(settings.get('seed_mode', '随机'))
                    # 种子值现在通过下拉框控制，不需要设置具体数值
                    self.retry_count_spin.setValue(settings.get('retry_count', 2))
                    self.delay_spin.setValue(settings.get('delay', 1.0))
                    
                    # 触发引擎切换事件
                    self.on_engine_changed(self.engine_combo.currentText())

                # 加载所有设置
                self.load_all_settings_from_project()
        except Exception as e:
            logger.error(f"加载设置失败: {e}")
    
    def save_parameter_preset(self):
        """保存参数预设"""
        preset_name, ok = QInputDialog.getText(self, "保存预设", "请输入预设名称:")
        if ok and preset_name:
            # 实现参数预设保存逻辑
            QMessageBox.information(self, "成功", f"预设 '{preset_name}' 保存成功")
            
    def load_parameter_preset(self):
        """加载参数预设"""
        # 实现参数预设加载逻辑
        QMessageBox.information(self, "提示", "参数预设加载功能待实现")
        
    def reset_parameters(self):
        """重置参数"""
        self.width_spin.setValue(1024)
        self.height_spin.setValue(1024)
        self.seed_combo.setCurrentText("随机")
        # 种子值现在通过下拉框控制，重置为随机模式
        self.batch_size_spin.setValue(1)
        self.retry_count_spin.setValue(2)
        self.delay_spin.setValue(1.0)
        
    # 数据管理方法
    def export_configuration(self):
        """导出配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", "storyboard_config.json", 
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                config_data = {
                    'storyboard_data': self.storyboard_data,
                    'parameters': self.get_current_parameters()
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                    
                QMessageBox.information(self, "成功", "配置导出成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
                
    def import_configuration(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", "", 
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                # 导入数据
                if 'storyboard_data' in config_data:
                    self.storyboard_data = config_data['storyboard_data']
                    self.update_table()
                    
                if 'parameters' in config_data:
                    self.load_parameters(config_data['parameters'])
                    
                QMessageBox.information(self, "成功", "配置导入成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
                
    def get_current_parameters(self):
        """获取当前参数"""
        params = {
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
            'steps': self.steps_spin.value(),
            'cfg_scale': self.cfg_spin.value(),
            'seed': self.get_seed_value(),
            'sampler': self.sampler_combo.currentText(),
            'negative_prompt': self.negative_prompt_text.toPlainText(),
            'batch_size': self.batch_size_spin.value(),
            'retry_count': self.retry_count_spin.value(),
            'delay': self.delay_spin.value()
        }

        # 添加Pollinations特有参数
        if hasattr(self, 'pollinations_model_combo'):
            params.update({
                'model': self.pollinations_model_combo.currentText(),
                'enhance': self.pollinations_enhance_check.isChecked(),
                'nologo': not self.pollinations_logo_check.isChecked()
            })

        return params
        
    def load_parameters(self, params):
        """加载参数"""
        self.width_spin.setValue(params.get('width', 1024))
        self.height_spin.setValue(params.get('height', 1024))
        self.steps_spin.setValue(params.get('steps', 30))
        self.cfg_spin.setValue(params.get('cfg_scale', 7.5))
        # 种子值现在通过下拉框控制，不需要设置具体数值

        sampler = params.get('sampler', 'DPM++ 2M Karras')
        index = self.sampler_combo.findText(sampler)
        if index >= 0:
            self.sampler_combo.setCurrentIndex(index)

        self.negative_prompt_text.setPlainText(
            params.get('negative_prompt', '')
        )

        # 加载Pollinations特有参数
        if hasattr(self, 'pollinations_model_combo'):
            model = params.get('model', 'flux')
            model_index = self.pollinations_model_combo.findText(model)
            if model_index >= 0:
                self.pollinations_model_combo.setCurrentIndex(model_index)

            self.pollinations_enhance_check.setChecked(params.get('enhance', False))
            self.pollinations_logo_check.setChecked(not params.get('nologo', True))
    
    def sync_to_ai_drawing_tab(self):
        """同步设置到AI绘图标签页"""
        try:
            main_window = self.get_main_window()
            if not main_window:
                return
                
            ai_drawing_tab = self.find_ai_drawing_tab(main_window)
            if not ai_drawing_tab:
                return
                
            # 获取当前引擎
            current_engine = self.engine_combo.currentText()
            
            # 同步引擎选择
            if "Pollinations" in current_engine:
                ai_drawing_tab.engine_combo.setCurrentText("Pollinations AI")
            elif "CogView-3 Flash" in current_engine:
                ai_drawing_tab.engine_combo.setCurrentText("CogView-3 Flash")
            elif "ComfyUI 本地" in current_engine:
                ai_drawing_tab.engine_combo.setCurrentText("ComfyUI Local")
            elif "ComfyUI 云端" in current_engine:
                ai_drawing_tab.engine_combo.setCurrentText("ComfyUI Cloud")
                
            # 同步基础参数
            ai_drawing_tab.width_spin.setValue(self.width_spin.value())
            ai_drawing_tab.height_spin.setValue(self.height_spin.value())
            
            # 同步种子设置
            if hasattr(ai_drawing_tab, 'seed_combo'):
                ai_drawing_tab.seed_combo.setCurrentText(self.seed_combo.currentText())
                
            # 触发AI绘图标签页的引擎切换事件
            ai_drawing_tab.on_engine_changed(ai_drawing_tab.engine_combo.currentText())
            
            logger.info("设置已同步到AI绘图标签页")
            
        except Exception as e:
            logger.error(f"同步到AI绘图标签页失败: {e}")
    
    def sync_from_ai_drawing_tab(self):
        """从AI绘图标签页同步设置"""
        try:
            main_window = self.get_main_window()
            if not main_window:
                return
                
            ai_drawing_tab = self.find_ai_drawing_tab(main_window)
            if not ai_drawing_tab:
                return
                
            # 获取AI绘图标签页的引擎
            ai_engine = ai_drawing_tab.engine_combo.currentText()
            
            # 同步引擎选择
            if "Pollinations" in ai_engine:
                self.engine_combo.setCurrentText("Pollinations AI (免费)")
            elif "CogView-3 Flash" in ai_engine:
                self.engine_combo.setCurrentText("CogView-3 Flash (免费)")
            elif "ComfyUI Local" in ai_engine:
                self.engine_combo.setCurrentText("ComfyUI 本地")
            elif "ComfyUI Cloud" in ai_engine:
                self.engine_combo.setCurrentText("ComfyUI 云端")
                
            # 同步基础参数
            self.width_spin.setValue(ai_drawing_tab.width_spin.value())
            self.height_spin.setValue(ai_drawing_tab.height_spin.value())
            
            # 同步种子设置
            if hasattr(ai_drawing_tab, 'seed_combo'):
                self.seed_combo.setCurrentText(ai_drawing_tab.seed_combo.currentText())
                
            # 触发引擎切换事件
            self.on_engine_changed(self.engine_combo.currentText())
            
            logger.info("设置已从AI绘图标签页同步")
            
        except Exception as e:
            logger.error(f"从AI绘图标签页同步失败: {e}")
    
    def get_main_window(self):
        """获取主窗口"""
        widget = self
        while widget.parent():
            widget = widget.parent()
            if hasattr(widget, 'tab_widget'):
                return widget
        return None
    
    def find_ai_drawing_tab(self, main_window):
        """查找AI绘图标签页"""
        try:
            if not hasattr(main_window, 'tab_widget'):
                return None
                
            tab_widget = main_window.tab_widget
            for i in range(tab_widget.count()):
                tab_text = tab_widget.tabText(i)
                if "AI绘图" in tab_text or "绘图" in tab_text:
                    return tab_widget.widget(i)
            return None
        except Exception as e:
            logger.error(f"查找AI绘图标签页失败: {e}")
            return None

    def _init_image_generation_service(self):
        """初始化图像生成服务"""
        try:
            import asyncio
            from src.models.image_generation_service import ImageGenerationService
            from src.utils.config_manager import ConfigManager

            # 获取图像配置
            config_manager = ConfigManager()
            image_config = config_manager.get_image_config()

            # 创建图像生成服务，传递配置
            self.image_generation_service = ImageGenerationService(image_config)

            # 异步初始化
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.image_generation_service.initialize())
            logger.info("图像生成服务初始化成功")
        except Exception as e:
              logger.error(f"图像生成服务初始化失败: {e}")
              self.image_generation_service = None
    
    def test_engine_connection(self):
        """测试引擎连接"""
        try:
            engine_text = self.engine_combo.currentText()
            
            if "ComfyUI" in engine_text:
                self.test_connection_btn.setText("测试中...")
                self.test_connection_btn.setEnabled(False)
                
                # 测试ComfyUI连接
                if self.image_generation_service:
                    # 异步测试连接
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        # 获取服务状态
                        status = loop.run_until_complete(self.image_generation_service.get_service_status())
                        
                        if "本地" in engine_text:
                            # 测试本地ComfyUI
                            comfyui_status = status.get('engines', {}).get('comfyui_local', {})
                            if comfyui_status.get('status') == 'idle':
                                self.engine_status_label.setText("状态: 连接成功")
                                self.engine_status_label.setStyleSheet("color: green;")
                                QMessageBox.information(self, "连接测试", "ComfyUI本地服务连接成功！")
                            else:
                                error_msg = comfyui_status.get('last_error', '未知错误')
                                self.engine_status_label.setText("状态: 连接失败")
                                self.engine_status_label.setStyleSheet("color: red;")
                                QMessageBox.warning(self, "连接测试", f"ComfyUI本地服务连接失败，请检查服务是否启动。\n错误信息: {error_msg}")
                        else:
                            # 测试云端ComfyUI
                            comfyui_status = status.get('engines', {}).get('comfyui_cloud', {})
                            if comfyui_status.get('status') == 'idle':
                                self.engine_status_label.setText("状态: 连接成功")
                                self.engine_status_label.setStyleSheet("color: green;")
                                QMessageBox.information(self, "连接测试", "ComfyUI云端服务连接成功！")
                            else:
                                error_msg = comfyui_status.get('last_error', '未知错误')
                                self.engine_status_label.setText("状态: 连接失败")
                                self.engine_status_label.setStyleSheet("color: red;")
                                QMessageBox.warning(self, "连接测试", f"ComfyUI云端服务连接失败。\n错误信息: {error_msg}")
                            
                    except Exception as e:
                        self.engine_status_label.setText("状态: 连接失败")
                        self.engine_status_label.setStyleSheet("color: red;")
                        QMessageBox.critical(self, "连接测试", f"连接测试失败: {str(e)}")
                    finally:
                        loop.close()
                else:
                    QMessageBox.warning(self, "连接测试", "图像生成服务未初始化，无法测试连接。")
                
                self.test_connection_btn.setText("测试连接")
                self.test_connection_btn.setEnabled(True)
            
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            QMessageBox.critical(self, "错误", f"连接测试过程中发生错误: {str(e)}")
            self.test_connection_btn.setText("测试连接")
            self.test_connection_btn.setEnabled(True)
    
    def save_current_image(self):
        """保存当前预览图像"""
        try:
            # 获取当前选中的分镜数据
            current_row = self.storyboard_table.currentRow()
            if current_row < 0 or current_row >= len(self.storyboard_data):
                QMessageBox.warning(self, "警告", "请先选择一个分镜")
                return
                
            shot_data = self.storyboard_data[current_row]
            if not shot_data.get('image_path') or not os.path.exists(shot_data['image_path']):
                QMessageBox.warning(self, "警告", "当前分镜没有可保存的图像")
                return
                
            # 选择保存位置
            from PyQt5.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存图像",
                f"{shot_data['shot_id']}.png",
                "图像文件 (*.png *.jpg *.jpeg)"
            )
            
            if file_path:
                import shutil
                shutil.copy2(shot_data['image_path'], file_path)
                QMessageBox.information(self, "成功", f"图像已保存到: {file_path}")
                logger.info(f"图像已保存: {file_path}")
                
        except Exception as e:
            logger.error(f"保存图像失败: {e}")
            QMessageBox.critical(self, "错误", f"保存图像失败: {str(e)}")
    
    def on_engine_changed(self, engine_text):
        """引擎切换处理"""
        try:
            # 根据引擎显示/隐藏特有设置
            if "Pollinations" in engine_text:
                # Pollinations AI - 显示特有设置，隐藏状态和连接测试
                self.pollinations_model_combo.setVisible(True)
                self.pollinations_enhance_check.setVisible(True)
                self.pollinations_logo_check.setVisible(True)

                # 完全隐藏引擎状态行
                self.engine_status_label.setVisible(False)
                self.engine_status_label_text.setVisible(False)

                # 完全隐藏连接测试行
                self.test_connection_btn.setVisible(False)
                self.test_connection_label_text.setVisible(False)
            elif "CogView-3 Flash" in engine_text:
                # CogView-3 Flash - 智谱AI免费引擎，优化参数显示
                self.pollinations_model_combo.setVisible(False)
                self.pollinations_enhance_check.setVisible(False)
                self.pollinations_logo_check.setVisible(False)

                # 完全隐藏引擎状态行
                self.engine_status_label.setVisible(False)
                self.engine_status_label_text.setVisible(False)

                # 完全隐藏连接测试行
                self.test_connection_btn.setVisible(False)
                self.test_connection_label_text.setVisible(False)

                # 显示尺寸预设下拉框
                if hasattr(self, 'size_preset_combo'):
                    self.size_preset_combo.setVisible(True)

                # 设置CogView-3 Flash的并发任务数限制
                if hasattr(self, 'concurrent_tasks_spin'):
                    self.concurrent_tasks_spin.setMaximum(5)  # CogView-3 Flash最大5并发
                    self.concurrent_tasks_spin.setValue(3)    # 默认3并发

                # 隐藏高级参数
                self.steps_spin.setVisible(False)
                self.steps_label.setVisible(False)
                self.cfg_spin.setVisible(False)
                self.cfg_label.setVisible(False)
                self.sampler_combo.setVisible(False)
                self.sampler_label.setVisible(False)
                self.negative_prompt_text.setVisible(False)
                self.negative_prompt_label.setVisible(False)
            else:
                # 其他引擎 - 隐藏Pollinations特有设置，显示状态
                self.pollinations_model_combo.setVisible(False)
                self.pollinations_enhance_check.setVisible(False)
                self.pollinations_logo_check.setVisible(False)

                # 显示引擎状态行
                self.engine_status_label.setVisible(True)
                self.engine_status_label_text.setVisible(True)

                # 更新引擎状态
                if "免费" in engine_text:
                    self.engine_status_label.setText("状态: 免费服务")
                    self.engine_status_label.setStyleSheet("color: green;")
                elif "付费" in engine_text:
                    self.engine_status_label.setText("状态: 付费服务")
                    self.engine_status_label.setStyleSheet("color: blue;")
                else:
                    self.engine_status_label.setText("状态: 本地服务")
                    self.engine_status_label.setStyleSheet("color: purple;")

                # 根据引擎显示/隐藏连接测试按钮
                if "ComfyUI" in engine_text:
                    self.test_connection_btn.setVisible(True)
                    self.test_connection_label_text.setVisible(True)
                else:
                    self.test_connection_btn.setVisible(False)
                    self.test_connection_label_text.setVisible(False)
            
            if not "Pollinations" in engine_text:
                # 其他引擎 - 显示所有参数
                self.steps_spin.setVisible(True)
                self.steps_label.setVisible(True)
                self.cfg_spin.setVisible(True)
                self.cfg_label.setVisible(True)
                self.sampler_combo.setVisible(True)
                self.sampler_label.setVisible(True)
                self.negative_prompt_text.setVisible(True)
                self.negative_prompt_label.setVisible(True)
                
                # 重置所有控件为启用状态
                self.steps_spin.setEnabled(True)
                self.cfg_spin.setEnabled(True)
                self.sampler_combo.setEnabled(True)

                # 默认隐藏尺寸预设下拉框和重置并发任务数
                if hasattr(self, 'size_preset_combo'):
                    self.size_preset_combo.setVisible(False)
                if hasattr(self, 'concurrent_tasks_spin'):
                    self.concurrent_tasks_spin.setMaximum(10)
                
                if "ComfyUI" in engine_text:
                    # ComfyUI - 保持灵活性但简化范围
                    self.steps_spin.setRange(10, 50)
                    self.steps_spin.setValue(20)
                    self.cfg_spin.setRange(1.0, 15.0)
                    self.cfg_spin.setValue(7.0)
                    self.sampler_combo.setEnabled(True)
                elif "DALL-E" in engine_text:
                    # DALL-E - 无需复杂参数
                    self.steps_spin.setEnabled(False)
                    self.cfg_spin.setEnabled(False)
                    self.sampler_combo.setEnabled(False)
                    self.sampler_combo.setCurrentText("DALL-E")
                elif "Stability" in engine_text:
                    # Stability AI - 简化参数
                    self.steps_spin.setRange(20, 40)
                    self.steps_spin.setValue(30)
                    self.cfg_spin.setRange(5.0, 15.0)
                    self.cfg_spin.setValue(7.5)
                    self.sampler_combo.setEnabled(False)
                    self.sampler_combo.setCurrentText("自动")
                elif "Imagen" in engine_text:
                    # Google Imagen - 无需复杂参数
                    self.steps_spin.setEnabled(False)
                    self.cfg_spin.setRange(1.0, 10.0)
                    self.cfg_spin.setValue(8.0)
                    self.sampler_combo.setEnabled(False)
                    self.sampler_combo.setCurrentText("Imagen")
                elif "CogView-3 Flash" in engine_text:
                    # CogView-3 Flash - 智谱AI免费引擎，隐藏不支持的参数
                    self.steps_spin.setVisible(False)
                    self.steps_label.setVisible(False)
                    self.cfg_spin.setVisible(False)
                    self.cfg_label.setVisible(False)
                    self.sampler_combo.setVisible(False)
                    self.sampler_label.setVisible(False)
                    self.negative_prompt_text.setVisible(False)
                    self.negative_prompt_label.setVisible(False)

                    # 显示尺寸预设下拉框
                    if hasattr(self, 'size_preset_combo'):
                        self.size_preset_combo.setVisible(True)

                    # 设置并发任务数限制
                    if hasattr(self, 'concurrent_tasks_spin'):
                        self.concurrent_tasks_spin.setMaximum(5)
                        self.concurrent_tasks_spin.setValue(3)

            logger.info(f"切换到引擎: {engine_text}")
            
            # 同步设置到AI绘图标签页
            self.sync_to_ai_drawing_tab()
            
        except Exception as e:
            logger.error(f"引擎切换失败: {e}")
 
    def save_main_image_to_project(self, shot_data):
         """保存主图信息到项目数据"""
         try:
             if not self.project_manager or not self.project_manager.current_project:
                 return

             project_data = self.project_manager.get_project_data()
             if not project_data:
                 return

             # 保存镜头图片关联信息到项目配置
             self._save_shot_image_mapping(shot_data)

         except Exception as e:
             logger.error(f"保存主图到项目失败: {e}")

    def _save_shot_image_mapping(self, shot_data, project_data=None):
        """保存镜头图片关联信息到项目配置"""
        try:
            from datetime import datetime

            # 获取当前项目数据
            current_project = getattr(self.project_manager, 'current_project', None)
            if not current_project:
                logger.warning("没有当前项目，无法保存镜头图片关联信息")
                return

            # 确保项目数据中有shot_image_mappings字段
            if 'shot_image_mappings' not in current_project:
                current_project['shot_image_mappings'] = {}

            # 🔧 修复：使用统一的ID格式构建镜头标识
            scene_id = shot_data.get('scene_id', '')
            shot_id = shot_data.get('shot_id', '')

            # 尝试从ID管理器获取统一的键格式
            unified_key = None
            if hasattr(self, 'shot_id_manager') and self.shot_id_manager.shot_mappings:
                # 尝试转换为统一格式
                if shot_id.startswith('text_segment_'):
                    unified_key = self.shot_id_manager.convert_id(shot_id, "unified")
                elif scene_id and shot_id:
                    unified_key = f"{scene_id}_{shot_id}"

            # 如果没有统一键，使用原始格式
            if not unified_key:
                unified_key = f"{scene_id}_{shot_id}" if scene_id and shot_id else shot_data.get('sequence', 'unknown')

            # 🔧 修复：保存镜头图片映射信息，确保主图路径正确传递
            main_image_path = shot_data.get('main_image_path', '')
            image_path = shot_data.get('image_path', '')

            # 如果设置了主图，确保image_path也指向主图
            if main_image_path and not image_path:
                image_path = main_image_path
            elif main_image_path and image_path != main_image_path:
                # 如果主图和当前图片不一致，优先使用主图
                image_path = main_image_path

            current_project['shot_image_mappings'][unified_key] = {
                'scene_id': scene_id,
                'shot_id': shot_id,
                'scene_name': shot_data.get('scene_name', ''),
                'shot_name': shot_data.get('shot_name', ''),
                'sequence': shot_data.get('sequence', ''),
                'main_image_path': main_image_path,
                'image_path': image_path,  # 确保视频生成能正确获取主图
                'generated_images': shot_data.get('generated_images', []),
                'current_image_index': shot_data.get('current_image_index', 0),
                'status': shot_data.get('status', '未生成'),
                'updated_time': datetime.now().isoformat()
            }

            # 保存项目数据
            save_method = getattr(self.project_manager, 'save_project', None)
            if save_method:
                save_method()
                logger.info(f"镜头图片关联信息已保存: {unified_key} -> {shot_data.get('main_image_path', '')}")
            else:
                logger.warning("项目管理器没有save_project方法")

        except Exception as e:
            logger.error(f"保存镜头图片关联信息失败: {e}")

    def _preserve_existing_image_data(self):
        """保存现有的图像数据"""
        existing_data = {}
        try:
            # 🔧 修复：优先从当前storyboard_data中保存图像数据，确保不丢失
            if hasattr(self, 'storyboard_data') and self.storyboard_data:
                for shot_data in self.storyboard_data:
                    shot_key = f"{shot_data.get('scene_id', '')}_{shot_data.get('shot_id', '')}"
                    # 只保存有实际图像数据的镜头
                    if (shot_data.get('image_path') or
                        shot_data.get('main_image_path') or
                        shot_data.get('generated_images')):
                        existing_data[shot_key] = {
                            'image_path': shot_data.get('image_path', ''),
                            'main_image_path': shot_data.get('main_image_path', ''),
                            'generated_images': shot_data.get('generated_images', []).copy() if shot_data.get('generated_images') else [],
                            'current_image_index': shot_data.get('current_image_index', 0),
                            'status': shot_data.get('status', '未生成')
                        }
                logger.info(f"从当前storyboard_data中保存了 {len(existing_data)} 个镜头的图像数据")

            # 🔧 修复：同时从项目数据中获取图像信息作为补充
            if self.project_manager and self.project_manager.current_project:
                project_data = self.project_manager.current_project
                shot_image_mappings = project_data.get('shot_image_mappings', {})

                # 从shot_image_mappings中补充图像数据
                for shot_key, mapping_data in shot_image_mappings.items():
                    # 如果当前数据中没有这个镜头的图像数据，从项目数据中补充
                    if shot_key not in existing_data:
                        if (mapping_data.get('image_path') or
                            mapping_data.get('main_image_path') or
                            mapping_data.get('generated_images')):
                            existing_data[shot_key] = {
                                'image_path': mapping_data.get('image_path', ''),
                                'main_image_path': mapping_data.get('main_image_path', ''),
                                'generated_images': mapping_data.get('generated_images', []).copy() if mapping_data.get('generated_images') else [],
                                'current_image_index': mapping_data.get('current_image_index', 0),
                                'status': mapping_data.get('status', '未生成')
                            }

                logger.info(f"总共保存了 {len(existing_data)} 个镜头的图像数据")

        except Exception as e:
            logger.error(f"保存现有图像数据失败: {e}")
        return existing_data

    def _load_image_data_from_project(self):
        """从项目数据中加载图像信息"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_data = self.project_manager.current_project

            # 优先从镜头图片关联信息中恢复
            shot_image_mappings = project_data.get('shot_image_mappings', {})
            if shot_image_mappings and hasattr(self, 'storyboard_data'):
                restored_count = 0
                for shot_data in self.storyboard_data:
                    scene_id = shot_data.get('scene_id', '')
                    shot_id = shot_data.get('shot_id', '')
                    shot_key = f"{scene_id}_{shot_id}"

                    if shot_key in shot_image_mappings:
                        mapping_data = shot_image_mappings[shot_key]
                        # 恢复图像相关数据
                        shot_data['image_path'] = mapping_data.get('image_path', '')
                        shot_data['main_image_path'] = mapping_data.get('main_image_path', '')
                        shot_data['generated_images'] = mapping_data.get('generated_images', [])
                        shot_data['current_image_index'] = mapping_data.get('current_image_index', 0)
                        shot_data['status'] = mapping_data.get('status', '未生成')
                        restored_count += 1

                if restored_count > 0:
                    logger.info(f"从镜头图片关联信息中恢复了 {restored_count} 个镜头的图像数据")
                    return

            # 如果没有镜头图片关联信息，尝试从旧的图像生成数据中恢复
            image_generation_data = project_data.get('image_generation', {})
            generated_images = image_generation_data.get('generated_images', [])

            # 如果有生成的图像数据，尝试匹配到分镜
            if generated_images and hasattr(self, 'storyboard_data'):
                for shot_data in self.storyboard_data:
                    shot_id = shot_data.get('shot_id', '')
                    # 查找匹配的图像
                    for img_data in generated_images:
                        if isinstance(img_data, dict) and img_data.get('shot_id') == shot_id:
                            shot_data['image_path'] = img_data.get('path', '')
                            shot_data['status'] = '已生成' if img_data.get('path') else '未生成'
                            break

            logger.debug("从项目数据中加载图像信息完成")
        except Exception as e:
            logger.error(f"从项目数据中加载图像信息失败: {e}")

    def _restore_existing_image_data(self, existing_data):
        """恢复现有的图像数据"""
        try:
            restored_count = 0
            logger.info(f"开始恢复图像数据，保存的数据包含 {len(existing_data)} 个镜头")

            for shot_data in self.storyboard_data:
                shot_key = f"{shot_data.get('scene_id', '')}_{shot_data.get('shot_id', '')}"
                shot_id = shot_data.get('shot_id', 'unknown')

                if shot_key in existing_data:
                    saved_data = existing_data[shot_key]
                    logger.debug(f"恢复镜头 {shot_id} 的图像数据: {saved_data}")

                    # 🔧 修复：只恢复有实际数据的字段，避免覆盖空值
                    restored_fields = []
                    if saved_data.get('image_path'):
                        shot_data['image_path'] = saved_data['image_path']
                        restored_fields.append('image_path')
                    if saved_data.get('main_image_path'):
                        shot_data['main_image_path'] = saved_data['main_image_path']
                        restored_fields.append('main_image_path')
                    if saved_data.get('generated_images'):
                        shot_data['generated_images'] = saved_data['generated_images']
                        restored_fields.append(f'generated_images({len(saved_data["generated_images"])})')
                    if 'current_image_index' in saved_data:
                        shot_data['current_image_index'] = saved_data['current_image_index']
                        restored_fields.append('current_image_index')
                    if saved_data.get('status') and saved_data['status'] != '未生成':
                        shot_data['status'] = saved_data['status']
                        restored_fields.append('status')

                    # 🔧 修复：如果恢复了图像数据，同时保存到项目数据中
                    if (shot_data.get('image_path') or
                        shot_data.get('main_image_path') or
                        shot_data.get('generated_images')):
                        self._save_shot_image_mapping(shot_data)
                        restored_count += 1
                        logger.info(f"镜头 {shot_id} 恢复成功，字段: {', '.join(restored_fields)}")
                else:
                    logger.debug(f"镜头 {shot_id} 没有保存的图像数据")

            logger.info(f"恢复了 {restored_count} 个镜头的图像数据")

            # 🔧 修复：恢复完成后立即保存项目数据
            if restored_count > 0 and self.project_manager:
                try:
                    self.project_manager.save_project()
                    logger.info("图像数据恢复后已保存项目")
                except Exception as e:
                    logger.error(f"保存项目失败: {e}")

        except Exception as e:
            logger.error(f"恢复现有图像数据失败: {e}")

    def _get_shot_image_from_project(self, shot_key):
        """从项目数据中获取镜头的图像信息"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return None

            project_data = self.project_manager.get_project_data()
            if not project_data:
                return None

            shot_mappings = project_data.get('shot_image_mappings', {})
            return shot_mappings.get(shot_key, None)

        except Exception as e:
            logger.error(f"从项目数据获取镜头图像信息失败: {e}")
            return None

    def _sync_image_data_from_project(self):
        """从项目数据同步图像信息到当前分镜数据"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_data = self.project_manager.get_project_data()
            if not project_data:
                return

            shot_mappings = project_data.get('shot_image_mappings', {})
            if not shot_mappings:
                logger.info("项目数据中没有图像映射信息，尝试重建映射")
                # 尝试重建图像映射
                self._rebuild_image_mappings()
                return

            synced_count = 0
            for shot_data in self.storyboard_data:
                shot_key = f"{shot_data.get('scene_id', '')}_{shot_data.get('shot_id', '')}"

                if shot_key in shot_mappings:
                    mapping_data = shot_mappings[shot_key]

                    # 同步图像信息
                    if mapping_data.get('main_image_path'):
                        shot_data['main_image_path'] = mapping_data['main_image_path']
                    if mapping_data.get('generated_images'):
                        shot_data['generated_images'] = mapping_data['generated_images']
                    if mapping_data.get('status'):
                        shot_data['status'] = mapping_data['status']
                    if 'current_image_index' in mapping_data:
                        shot_data['current_image_index'] = mapping_data['current_image_index']

                    synced_count += 1

            logger.info(f"从项目数据同步了 {synced_count} 个镜头的图像信息")

        except Exception as e:
            logger.error(f"同步项目图像数据失败: {e}")

    def _rebuild_image_mappings(self):
        """重建图像映射关系"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_dir = Path(self.project_manager.current_project['project_dir'])
            images_dir = project_dir / 'images'

            if not images_dir.exists():
                logger.warning("项目图像目录不存在")
                return

            # 收集所有图像文件
            image_files = []
            for engine_dir in images_dir.iterdir():
                if engine_dir.is_dir():
                    for img_file in engine_dir.glob('*.png'):
                        image_files.append(img_file)
                    for img_file in engine_dir.glob('*.jpg'):
                        image_files.append(img_file)
                    for img_file in engine_dir.glob('*.jpeg'):
                        image_files.append(img_file)

            if not image_files:
                logger.info("未找到任何图像文件")
                return

            # 重建映射关系
            project_data = self.project_manager.get_project_data()
            if 'shot_image_mappings' not in project_data:
                project_data['shot_image_mappings'] = {}

            rebuilt_count = 0
            for shot_data in self.storyboard_data:
                scene_id = shot_data.get('scene_id', '')
                shot_id = shot_data.get('shot_id', '')
                shot_key = f"{scene_id}_{shot_id}"

                # 查找匹配的图像文件
                matching_images = []
                for img_file in image_files:
                    # 尝试多种匹配模式
                    filename = img_file.stem
                    if (shot_id in filename or
                        scene_id in filename or
                        shot_data.get('sequence', '') in filename):
                        matching_images.append(str(img_file))

                if matching_images:
                    # 使用第一个匹配的图像作为主图像
                    main_image = matching_images[0]

                    project_data['shot_image_mappings'][shot_key] = {
                        'scene_id': scene_id,
                        'shot_id': shot_id,
                        'scene_name': shot_data.get('scene_name', ''),
                        'shot_name': shot_data.get('shot_name', ''),
                        'sequence': shot_data.get('sequence', ''),
                        'main_image_path': main_image,
                        'image_path': main_image,
                        'generated_images': matching_images,
                        'current_image_index': 0,
                        'status': '已生成',
                        'updated_time': datetime.now().isoformat()
                    }

                    # 同步到当前数据
                    shot_data['main_image_path'] = main_image
                    shot_data['generated_images'] = matching_images
                    shot_data['status'] = '已生成'
                    shot_data['current_image_index'] = 0

                    rebuilt_count += 1

            # 保存项目数据
            self.project_manager.save_project_data(project_data)
            logger.info(f"重建了 {rebuilt_count} 个图像映射关系")

        except Exception as e:
            logger.error(f"重建图像映射失败: {e}")

    def preview_prev_image(self):
        """预览区域的上一张图片"""
        current_row = self.storyboard_table.currentRow()
        if current_row >= 0:
            data_index = self.get_data_index_by_table_row(current_row)
            if data_index >= 0:
                shot_data = self.storyboard_data[data_index]
                images = shot_data.get('generated_images', [])
                if len(images) > 1:
                    current_index = shot_data.get('current_image_index', 0)
                    new_index = (current_index - 1) % len(images)
                    shot_data['current_image_index'] = new_index
                    shot_data['main_image_path'] = images[new_index]

                    # 更新预览显示
                    self.load_preview_image(images[new_index])
                    # 更新当前图像路径属性
                    self.preview_label.setProperty('current_image_path', images[new_index])
                    self.update_preview_navigation(shot_data)

                    # 更新表格中的主图显示
                    self.create_main_image_widget(current_row, shot_data)

    def preview_next_image(self):
        """预览区域的下一张图片"""
        current_row = self.storyboard_table.currentRow()
        if current_row >= 0:
            data_index = self.get_data_index_by_table_row(current_row)
            if data_index >= 0:
                shot_data = self.storyboard_data[data_index]
                images = shot_data.get('generated_images', [])
                if len(images) > 1:
                    current_index = shot_data.get('current_image_index', 0)
                    new_index = (current_index + 1) % len(images)
                    shot_data['current_image_index'] = new_index
                    shot_data['main_image_path'] = images[new_index]

                    # 更新预览显示
                    self.load_preview_image(images[new_index])
                    # 更新当前图像路径属性
                    self.preview_label.setProperty('current_image_path', images[new_index])
                    self.update_preview_navigation(shot_data)

                    # 更新表格中的主图显示
                    self.create_main_image_widget(current_row, shot_data)

    def update_preview_navigation(self, shot_data):
        """更新预览区域的翻页控件"""
        images = shot_data.get('generated_images', [])
        if len(images) > 1:
            current_index = shot_data.get('current_image_index', 0)
            self.preview_page_label.setText(f"{current_index + 1}/{len(images)}")
            self.preview_prev_btn.setVisible(True)
            self.preview_next_btn.setVisible(True)
            self.preview_page_label.setVisible(True)
            # 启用设为主图按钮和删除图像按钮
            if hasattr(self, 'set_main_image_btn'):
                self.set_main_image_btn.setEnabled(True)
            if hasattr(self, 'delete_image_btn'):
                self.delete_image_btn.setEnabled(True)
        else:
            self.preview_prev_btn.setVisible(False)
            self.preview_next_btn.setVisible(False)
            self.preview_page_label.setVisible(False)
            # 如果只有一张图片或没有图片，也可以设为主图和删除图像（如果有图片的话）
            if hasattr(self, 'set_main_image_btn'):
                has_image = len(images) >= 1
                self.set_main_image_btn.setEnabled(has_image)
            if hasattr(self, 'delete_image_btn'):
                has_image = len(images) >= 1
                self.delete_image_btn.setEnabled(has_image)

    def _is_image_generation_failed(self, error_message):
        """检测图像生成是否失败"""
        if not error_message:
            return False

        # 检查常见的失败模式
        failure_patterns = [
            'http 502', 'http 503', 'http 500', 'http 404',
            'timeout', '超时', 'timed out',
            'connection', '连接', 'network error', '网络错误',
            'failed to generate', '生成失败',
            'api error', 'api错误', 'api调用失败',
            'invalid response', '无效响应',
            'server error', '服务器错误'
        ]

        error_lower = error_message.lower()
        return any(pattern in error_lower for pattern in failure_patterns)

    def _record_generation_failure(self, item_index, item_data, error_message):
        """记录生成失败"""
        import time
        failure_record = {
            "item_index": item_index,
            "item_data": item_data,
            "error": error_message,
            "timestamp": time.time()
        }
        self.failed_generations.append(failure_record)
        logger.error(f"记录图像生成失败: 镜头{item_index + 1}, 错误: {error_message}")

    def show_generation_failure_dialog(self):
        """显示生成失败对话框"""
        if not self.failed_generations:
            return

        from src.gui.image_generation_failure_dialog import ImageGenerationFailureDialog
        dialog = ImageGenerationFailureDialog(
            parent=self,
            failed_images=self.failed_generations
        )

        # 显示对话框
        result = dialog.exec_()

        # 清空失败记录（无论用户是否重试）
        self.failed_generations = []

    def _retry_single_image_generation(self, item_index, item_data):
        """重试单个图像生成"""
        try:
            logger.info(f"重试第{item_index + 1}个镜头的图像生成...")

            # 获取描述
            description = item_data.get('enhanced_description') or item_data.get('consistency_description', '')
            if not description:
                logger.error(f"第{item_index + 1}个镜头缺少描述信息")
                return False

            # 根据引擎类型决定是否翻译
            current_engine = self.engine_combo.currentText()
            if "CogView-3 Flash" in current_engine:
                # CogView-3 Flash支持中文，直接使用原始描述
                translated_prompt = description
                logger.info("CogView-3 Flash引擎支持中文，跳过翻译")
            else:
                # 其他引擎需要翻译为英文
                translated_prompt = self._translate_prompt_to_english(description, item_data)

            # 重新启动批量生成（只包含这一个项目）
            self.start_batch_generation([item_data])

            # 简化版：直接返回True，实际结果会在异步回调中处理
            return True

        except Exception as e:
            logger.error(f"重试第{item_index + 1}个镜头异常: {e}")
            return False

    def _populate_engine_list(self):
        """动态填充引擎列表"""
        try:
            from src.models.image_engine_factory import get_engine_factory
            from src.models.image_engine_base import EngineType

            # 获取引擎工厂
            factory = get_engine_factory()
            available_engines = factory.get_available_engines()

            # 引擎显示名称映射
            engine_display_names = {
                EngineType.POLLINATIONS: "Pollinations AI (免费)",
                EngineType.COGVIEW_3_FLASH: "CogView-3 Flash (免费)",
                EngineType.COMFYUI_LOCAL: "ComfyUI 本地",
                EngineType.COMFYUI_CLOUD: "ComfyUI 云端",
                EngineType.OPENAI_DALLE: "OpenAI DALL-E (付费)",
                EngineType.STABILITY_AI: "Stability AI (付费)",
                EngineType.GOOGLE_IMAGEN: "Google Imagen (付费)",
                EngineType.MIDJOURNEY: "Midjourney (付费)"
            }

            # 清空现有项目
            self.engine_combo.clear()

            # 添加可用引擎
            for engine_type in available_engines:
                display_name = engine_display_names.get(engine_type, engine_type.value)
                self.engine_combo.addItem(display_name, engine_type.value)

            logger.info(f"动态加载了 {len(available_engines)} 个图像生成引擎")

        except Exception as e:
            logger.error(f"动态加载引擎列表失败: {e}")
            # 回退到基本引擎列表
            self.engine_combo.addItems([
                "Pollinations AI (免费)",
                "CogView-3 Flash (免费)",
                "ComfyUI 本地"
            ])

    def on_size_preset_changed(self, preset_text):
        """处理尺寸预设变化"""
        try:
            if preset_text == "自定义":
                return

            # 解析预设尺寸
            size_mappings = {
                "1024×1024 (正方形)": (1024, 1024),
                "768×1344 (竖屏)": (768, 1344),
                "864×1152 (竖屏)": (864, 1152),
                "1344×768 (横屏)": (1344, 768),
                "1152×864 (横屏)": (1152, 864),
                "1440×720 (超宽)": (1440, 720),
                "720×1440 (超高)": (720, 1440)
            }

            if preset_text in size_mappings:
                width, height = size_mappings[preset_text]
                self.width_spin.setValue(width)
                self.height_spin.setValue(height)
                logger.info(f"设置预设尺寸: {width}×{height}")

        except Exception as e:
            logger.error(f"设置预设尺寸失败: {e}")
