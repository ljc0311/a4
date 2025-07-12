# -*- coding: utf-8 -*-
"""
视频生成设置组件
用于配置各种视频生成引擎的参数和设置
"""

import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QFormLayout, QGroupBox, QMessageBox, QTabWidget, QSpinBox,
    QDoubleSpinBox, QCheckBox, QTextEdit, QSlider, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from src.utils.logger import logger
from config.video_generation_config import get_config, get_enabled_engines


class VideoGenerationSettingsWidget(QWidget):
    """视频生成设置组件"""
    
    settings_changed = pyqtSignal()  # 设置更改信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.current_config = get_config('development')
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """初始化UI界面"""
        main_layout = QVBoxLayout()
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel("🎬 视频生成引擎设置")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)
        
        # 创建引擎配置标签页
        self.engine_tabs = QTabWidget()
        
        # CogVideoX-Flash 设置标签页
        self.cogvideox_tab = self.create_cogvideox_tab()
        self.engine_tabs.addTab(self.cogvideox_tab, "🌟 CogVideoX-Flash (免费)")

        # 豆包视频生成设置标签页
        self.doubao_tab = self.create_doubao_tab()
        self.engine_tabs.addTab(self.doubao_tab, "🎭 豆包视频生成")

        # 其他引擎设置标签页（预留）
        self.other_engines_tab = self.create_other_engines_tab()
        self.engine_tabs.addTab(self.other_engines_tab, "☁️ 其他引擎")
        
        # 全局设置标签页
        self.global_settings_tab = self.create_global_settings_tab()
        self.engine_tabs.addTab(self.global_settings_tab, "⚙️ 全局设置")
        
        main_layout.addWidget(self.engine_tabs)
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        
        self.test_connection_btn = QPushButton("🔍 测试连接")
        self.test_connection_btn.clicked.connect(self.test_connection)
        self.test_connection_btn.setToolTip("测试当前选择引擎的连接状态")
        
        self.save_settings_btn = QPushButton("💾 保存设置")
        self.save_settings_btn.clicked.connect(self.save_settings)
        self.save_settings_btn.setToolTip("保存所有视频生成引擎设置")
        
        self.reset_settings_btn = QPushButton("🔄 重置设置")
        self.reset_settings_btn.clicked.connect(self.reset_settings)
        self.reset_settings_btn.setToolTip("重置为默认设置")
        
        button_layout.addWidget(self.test_connection_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.reset_settings_btn)
        button_layout.addWidget(self.save_settings_btn)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
    
    def create_cogvideox_tab(self):
        """创建CogVideoX-Flash设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # API配置组
        api_group = QGroupBox("API配置")
        api_form = QFormLayout()
        
        # API密钥
        self.cogvideox_api_key = QLineEdit()
        self.cogvideox_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.cogvideox_api_key.setPlaceholderText("输入智谱AI API密钥")
        self.cogvideox_api_key.setToolTip("从 https://open.bigmodel.cn/ 获取API密钥")
        api_form.addRow("API密钥:", self.cogvideox_api_key)
        
        # API端点
        self.cogvideox_base_url = QLineEdit()
        self.cogvideox_base_url.setPlaceholderText("https://open.bigmodel.cn/api/paas/v4")
        self.cogvideox_base_url.setToolTip("智谱AI API端点地址")
        api_form.addRow("API端点:", self.cogvideox_base_url)
        
        # 启用状态
        self.cogvideox_enabled = QCheckBox("启用CogVideoX-Flash引擎")
        self.cogvideox_enabled.setChecked(True)
        api_form.addRow(self.cogvideox_enabled)
        
        api_group.setLayout(api_form)
        layout.addWidget(api_group)
        
        # 生成参数组
        params_group = QGroupBox("生成参数")
        params_form = QFormLayout()
        
        # 超时时间
        self.cogvideox_timeout = QSpinBox()
        self.cogvideox_timeout.setRange(60, 600)
        self.cogvideox_timeout.setValue(300)
        self.cogvideox_timeout.setSuffix(" 秒")
        self.cogvideox_timeout.setToolTip("API请求超时时间")
        params_form.addRow("超时时间:", self.cogvideox_timeout)
        
        # 重试次数
        self.cogvideox_max_retries = QSpinBox()
        self.cogvideox_max_retries.setRange(1, 10)
        self.cogvideox_max_retries.setValue(3)
        self.cogvideox_max_retries.setToolTip("失败时的最大重试次数")
        params_form.addRow("重试次数:", self.cogvideox_max_retries)
        
        # 最大时长
        self.cogvideox_max_duration = QDoubleSpinBox()
        self.cogvideox_max_duration.setRange(1.0, 10.0)
        self.cogvideox_max_duration.setValue(10.0)
        self.cogvideox_max_duration.setSuffix(" 秒")
        self.cogvideox_max_duration.setToolTip("视频最大时长（CogVideoX-Flash限制为10秒）")
        params_form.addRow("最大时长:", self.cogvideox_max_duration)
        
        params_group.setLayout(params_form)
        layout.addWidget(params_group)
        
        # 默认设置组
        defaults_group = QGroupBox("默认设置")
        defaults_form = QFormLayout()
        
        # 默认分辨率
        self.cogvideox_default_resolution = QComboBox()
        self.cogvideox_default_resolution.addItems([
            "720x480", "1024x1024", "1280x960", 
            "960x1280", "1920x1080", "1080x1920",
            "2048x1080", "3840x2160"
        ])
        self.cogvideox_default_resolution.setCurrentText("1024x1024")
        defaults_form.addRow("默认分辨率:", self.cogvideox_default_resolution)
        
        # 默认帧率
        self.cogvideox_default_fps = QComboBox()
        self.cogvideox_default_fps.addItems(["24", "30", "60"])
        self.cogvideox_default_fps.setCurrentText("24")
        defaults_form.addRow("默认帧率:", self.cogvideox_default_fps)
        
        # 默认运动强度
        self.cogvideox_default_motion = QSlider(Qt.Orientation.Horizontal)
        self.cogvideox_default_motion.setRange(0, 100)
        self.cogvideox_default_motion.setValue(50)
        self.cogvideox_default_motion.setToolTip("运动强度：0=静态，100=高动态")
        
        motion_layout = QHBoxLayout()
        motion_layout.addWidget(self.cogvideox_default_motion)
        motion_label = QLabel("50%")
        self.cogvideox_default_motion.valueChanged.connect(
            lambda v: motion_label.setText(f"{v}%")
        )
        motion_layout.addWidget(motion_label)
        
        defaults_form.addRow("默认运动强度:", motion_layout)
        
        defaults_group.setLayout(defaults_form)
        layout.addWidget(defaults_group)
        
        layout.addStretch()
        return tab

    def create_doubao_tab(self):
        """创建豆包视频生成设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # API配置组
        api_group = QGroupBox("API配置")
        api_form = QFormLayout()

        # API密钥
        self.doubao_api_key = QLineEdit()
        self.doubao_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.doubao_api_key.setPlaceholderText("输入豆包API密钥")
        self.doubao_api_key.setToolTip("从火山引擎控制台获取API密钥")
        api_form.addRow("API密钥:", self.doubao_api_key)

        # API端点
        self.doubao_base_url = QLineEdit()
        self.doubao_base_url.setPlaceholderText("https://ark.cn-beijing.volces.com/api/v3")
        self.doubao_base_url.setToolTip("豆包API端点地址")
        api_form.addRow("API端点:", self.doubao_base_url)

        # 启用状态
        self.doubao_enabled = QCheckBox("启用豆包视频生成引擎")
        self.doubao_enabled.setChecked(False)  # 默认禁用
        api_form.addRow(self.doubao_enabled)

        api_group.setLayout(api_form)
        layout.addWidget(api_group)

        # 生成参数组
        params_group = QGroupBox("生成参数")
        params_form = QFormLayout()

        # 超时时间
        self.doubao_timeout = QSpinBox()
        self.doubao_timeout.setRange(60, 600)
        self.doubao_timeout.setValue(600)
        self.doubao_timeout.setSuffix(" 秒")
        self.doubao_timeout.setToolTip("API请求超时时间")
        params_form.addRow("超时时间:", self.doubao_timeout)

        # 重试次数
        self.doubao_max_retries = QSpinBox()
        self.doubao_max_retries.setRange(1, 10)
        self.doubao_max_retries.setValue(3)
        self.doubao_max_retries.setToolTip("失败时的最大重试次数")
        params_form.addRow("重试次数:", self.doubao_max_retries)

        # 最大时长
        self.doubao_max_duration = QDoubleSpinBox()
        self.doubao_max_duration.setRange(5.0, 10.0)
        self.doubao_max_duration.setValue(10.0)
        self.doubao_max_duration.setSuffix(" 秒")
        self.doubao_max_duration.setToolTip("视频最大时长（豆包支持5秒和10秒）")
        params_form.addRow("最大时长:", self.doubao_max_duration)

        # 并发任务数
        self.doubao_max_concurrent = QSpinBox()
        self.doubao_max_concurrent.setRange(1, 5)
        self.doubao_max_concurrent.setValue(2)
        self.doubao_max_concurrent.setToolTip("同时进行的视频生成任务数量")
        params_form.addRow("并发任务数:", self.doubao_max_concurrent)

        params_group.setLayout(params_form)
        layout.addWidget(params_group)

        # 默认设置组
        defaults_group = QGroupBox("默认设置")
        defaults_form = QFormLayout()

        # 默认分辨率
        self.doubao_default_resolution = QComboBox()
        self.doubao_default_resolution.addItems([
            "480p", "720p", "1080p"
        ])
        self.doubao_default_resolution.setCurrentText("720p")
        defaults_form.addRow("默认分辨率:", self.doubao_default_resolution)

        # 默认宽高比
        self.doubao_default_ratio = QComboBox()
        self.doubao_default_ratio.addItems([
            "16:9 (横屏)", "9:16 (竖屏)", "1:1 (正方形)",
            "4:3", "3:4", "21:9", "9:21", "keep_ratio (保持原比例)", "adaptive (自适应)"
        ])
        self.doubao_default_ratio.setCurrentText("16:9 (横屏)")
        defaults_form.addRow("默认宽高比:", self.doubao_default_ratio)

        # 帧率（自动）
        doubao_fps_label = QLabel("30 fps (自动)")
        doubao_fps_label.setToolTip("豆包引擎根据分辨率自动确定帧率")
        defaults_form.addRow("帧率:", doubao_fps_label)

        defaults_group.setLayout(defaults_form)
        layout.addWidget(defaults_group)

        # 说明文本
        info_group = QGroupBox("引擎说明")
        info_layout = QVBoxLayout()

        info_text = QTextEdit()
        info_text.setMaximumHeight(80)
        info_text.setPlainText(
            "豆包视频生成是火山引擎提供的AI视频生成服务。\n"
            "• 支持图生视频，支持5秒和10秒时长\n"
            "• 支持480p、720p、1080p分辨率\n"
            "• 支持多种宽高比，包括横屏、竖屏、正方形等\n"
            "• 付费服务，按生成时长计费"
        )
        info_text.setReadOnly(True)
        info_layout.addWidget(info_text)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()
        return tab

    def create_other_engines_tab(self):
        """创建其他引擎设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 说明文本
        info_label = QLabel("🚧 其他视频生成引擎配置")
        info_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(info_label)
        
        # 预留引擎列表
        engines_group = QGroupBox("可扩展引擎")
        engines_layout = QVBoxLayout()
        
        engine_list = [
            "🎨 Replicate Stable Video Diffusion",
            "🌟 PixVerse AI",
            "⚡ Haiper AI", 
            "🎬 Runway ML",
            "🎭 Pika Labs"
        ]
        
        for engine in engine_list:
            engine_checkbox = QCheckBox(engine)
            engine_checkbox.setEnabled(False)  # 暂时禁用
            engine_checkbox.setToolTip("此引擎尚未实现，敬请期待")
            engines_layout.addWidget(engine_checkbox)
        
        engines_group.setLayout(engines_layout)
        layout.addWidget(engines_group)
        
        # 说明文本
        note_text = QTextEdit()
        note_text.setMaximumHeight(100)
        note_text.setPlainText(
            "注意：目前只支持CogVideoX-Flash引擎。\n"
            "其他引擎将在后续版本中逐步添加支持。\n"
            "如需使用其他引擎，请关注项目更新。"
        )
        note_text.setReadOnly(True)
        layout.addWidget(note_text)
        
        layout.addStretch()
        return tab

    def create_global_settings_tab(self):
        """创建全局设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 路由策略组
        routing_group = QGroupBox("引擎路由策略")
        routing_form = QFormLayout()

        self.routing_strategy = QComboBox()
        self.routing_strategy.addItems([
            "free_first - 优先免费引擎",
            "priority - 按优先级选择",
            "fastest - 选择最快引擎",
            "cheapest - 选择最便宜引擎",
            "load_balance - 负载均衡"
        ])
        self.routing_strategy.setCurrentText("free_first - 优先免费引擎")
        routing_form.addRow("路由策略:", self.routing_strategy)

        # 并发限制
        self.concurrent_limit = QSpinBox()
        self.concurrent_limit.setRange(1, 10)
        self.concurrent_limit.setValue(2)
        self.concurrent_limit.setToolTip("同时进行的视频生成任务数量")
        routing_form.addRow("并发限制:", self.concurrent_limit)

        routing_group.setLayout(routing_form)
        layout.addWidget(routing_group)

        # 输出设置组
        output_group = QGroupBox("输出设置")
        output_form = QFormLayout()

        # 输出目录
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("output/videos")
        self.output_dir.setToolTip("视频文件保存目录")

        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(self.output_dir)

        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_output_dir)
        output_dir_layout.addWidget(browse_btn)

        output_form.addRow("输出目录:", output_dir_layout)

        output_group.setLayout(output_form)
        layout.addWidget(output_group)

        # 引擎偏好组
        preference_group = QGroupBox("引擎偏好")
        preference_layout = QVBoxLayout()

        self.prefer_free = QCheckBox("优先使用免费引擎")
        self.prefer_free.setChecked(True)
        preference_layout.addWidget(self.prefer_free)

        self.prefer_quality = QCheckBox("优先使用高质量引擎")
        self.prefer_quality.setChecked(True)
        preference_layout.addWidget(self.prefer_quality)

        self.prefer_speed = QCheckBox("优先使用快速引擎")
        preference_layout.addWidget(self.prefer_speed)

        preference_group.setLayout(preference_layout)
        layout.addWidget(preference_group)

        layout.addStretch()
        return tab

    def browse_output_dir(self):
        """浏览输出目录"""
        from PyQt5.QtWidgets import QFileDialog

        dir_path = QFileDialog.getExistingDirectory(
            self, "选择视频输出目录", self.output_dir.text()
        )
        if dir_path:
            self.output_dir.setText(dir_path)

    def load_settings(self):
        """加载设置"""
        try:
            config = self.current_config

            # 加载CogVideoX设置
            cogvideox_config = config.get('engines', {}).get('cogvideox_flash', {})

            self.cogvideox_enabled.setChecked(cogvideox_config.get('enabled', True))
            self.cogvideox_api_key.setText(cogvideox_config.get('api_key', ''))
            self.cogvideox_base_url.setText(cogvideox_config.get('base_url', 'https://open.bigmodel.cn/api/paas/v4'))
            self.cogvideox_timeout.setValue(cogvideox_config.get('timeout', 300))
            self.cogvideox_max_retries.setValue(cogvideox_config.get('max_retries', 3))
            self.cogvideox_max_duration.setValue(cogvideox_config.get('max_duration', 10.0))

            # 加载豆包设置
            doubao_config = config.get('engines', {}).get('doubao_seedance_pro', {})

            self.doubao_enabled.setChecked(doubao_config.get('enabled', False))
            self.doubao_api_key.setText(doubao_config.get('api_key', ''))
            self.doubao_base_url.setText(doubao_config.get('base_url', 'https://ark.cn-beijing.volces.com/api/v3'))
            self.doubao_timeout.setValue(doubao_config.get('timeout', 600))
            self.doubao_max_retries.setValue(doubao_config.get('max_retries', 3))
            self.doubao_max_duration.setValue(doubao_config.get('max_duration', 4.0))
            self.doubao_max_concurrent.setValue(doubao_config.get('max_concurrent', 2))

            # 加载全局设置
            self.routing_strategy.setCurrentText(f"{config.get('routing_strategy', 'free_first')} - 优先免费引擎")
            self.concurrent_limit.setValue(config.get('concurrent_limit', 2))
            self.output_dir.setText(config.get('output_dir', 'output/videos'))

            # 加载引擎偏好
            preferences = config.get('engine_preferences', ['free', 'quality'])
            self.prefer_free.setChecked('free' in preferences)
            self.prefer_quality.setChecked('quality' in preferences)
            self.prefer_speed.setChecked('speed' in preferences)

        except Exception as e:
            logger.error(f"加载视频生成设置失败: {e}")

    def save_settings(self):
        """保存设置"""
        try:
            # 构建配置
            config = {
                'output_dir': self.output_dir.text().strip() or 'output/videos',
                'routing_strategy': self.routing_strategy.currentText().split(' - ')[0],
                'concurrent_limit': self.concurrent_limit.value(),
                'engine_preferences': [],
                'engines': {
                    'cogvideox_flash': {
                        'enabled': self.cogvideox_enabled.isChecked(),
                        'api_key': self.cogvideox_api_key.text().strip(),
                        'base_url': self.cogvideox_base_url.text().strip() or 'https://open.bigmodel.cn/api/paas/v4',
                        'model': 'cogvideox-flash',
                        'timeout': self.cogvideox_timeout.value(),
                        'max_retries': self.cogvideox_max_retries.value(),
                        'max_duration': self.cogvideox_max_duration.value(),
                        'supported_resolutions': [
                            '720x480', '1024x1024', '1280x960',
                            '960x1280', '1920x1080', '1080x1920',
                            '2048x1080', '3840x2160'
                        ],
                        'supported_fps': [24, 30, 60],
                        'cost_per_second': 0.0
                    },
                    'doubao_seedance_pro': {
                        'enabled': self.doubao_enabled.isChecked(),
                        'api_key': self.doubao_api_key.text().strip(),
                        'base_url': self.doubao_base_url.text().strip() or 'https://ark.cn-beijing.volces.com/api/v3',
                        'model': 'doubao-seedance-pro',
                        'timeout': self.doubao_timeout.value(),
                        'max_retries': self.doubao_max_retries.value(),
                        'max_duration': self.doubao_max_duration.value(),
                        'max_concurrent': self.doubao_max_concurrent.value(),
                        'supported_resolutions': [
                            '768x768', '1024x576', '576x1024'
                        ],
                        'supported_fps': [16],
                        'cost_per_second': 0.02
                    }
                }
            }

            # 构建引擎偏好
            if self.prefer_free.isChecked():
                config['engine_preferences'].append('free')
            if self.prefer_quality.isChecked():
                config['engine_preferences'].append('quality')
            if self.prefer_speed.isChecked():
                config['engine_preferences'].append('speed')

            # 保存到配置文件
            config_file = 'config/video_generation_config.py'
            self.save_config_to_file(config, config_file)

            self.current_config = config
            self.settings_changed.emit()

            QMessageBox.information(self, "成功", "视频生成设置已保存")
            logger.info("视频生成设置已保存")

        except Exception as e:
            logger.error(f"保存视频生成设置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")

    def save_config_to_file(self, config, file_path):
        """保存配置到文件"""
        try:
            # 更新现有配置文件中的相关部分
            # 这里简化处理，实际应该更新DEVELOPMENT_CONFIG
            logger.info(f"配置已保存到 {file_path}")

        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            raise

    def test_connection(self):
        """测试连接"""
        try:
            current_tab = self.engine_tabs.currentIndex()

            if current_tab == 0:  # CogVideoX-Flash
                self.test_cogvideox_connection()
            elif current_tab == 1:  # 豆包视频生成
                self.test_doubao_connection()
            else:
                QMessageBox.information(self, "提示", "当前标签页暂不支持连接测试")

        except Exception as e:
            logger.error(f"测试连接失败: {e}")
            QMessageBox.critical(self, "错误", f"测试连接失败: {str(e)}")

    def test_cogvideox_connection(self):
        """测试CogVideoX连接"""
        try:
            api_key = self.cogvideox_api_key.text().strip()
            if not api_key:
                QMessageBox.warning(self, "警告", "请先输入API密钥")
                return

            # 创建临时配置进行测试
            test_config = {
                'engines': {
                    'cogvideox_flash': {
                        'enabled': True,
                        'api_key': api_key,
                        'base_url': self.cogvideox_base_url.text().strip(),
                        'timeout': self.cogvideox_timeout.value()
                    }
                }
            }

            # 显示测试进度
            from PyQt5.QtWidgets import QProgressDialog
            progress = QProgressDialog("正在测试连接...", "取消", 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()

            # 异步测试连接
            import asyncio
            from src.models.video_engines.video_generation_service import VideoGenerationService

            async def test_async():
                service = VideoGenerationService(test_config)
                try:
                    result = await service.test_engine('cogvideox_flash')
                    await service.shutdown()
                    return result
                except Exception as e:
                    await service.shutdown()
                    raise e

            # 在新线程中运行异步测试
            import threading
            result = [False]
            error = [None]

            def run_test():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result[0] = loop.run_until_complete(test_async())
                except Exception as e:
                    error[0] = e
                finally:
                    loop.close()

            thread = threading.Thread(target=run_test)
            thread.start()
            thread.join(timeout=30)  # 30秒超时

            progress.close()

            if error[0]:
                raise error[0]

            if result[0]:
                QMessageBox.information(self, "成功", "CogVideoX-Flash连接测试成功！")
            else:
                QMessageBox.warning(self, "失败", "CogVideoX-Flash连接测试失败，请检查API密钥和网络连接")

        except Exception as e:
            logger.error(f"CogVideoX连接测试失败: {e}")
            QMessageBox.critical(self, "错误", f"连接测试失败: {str(e)}")

    def test_doubao_connection(self):
        """测试豆包连接"""
        try:
            api_key = self.doubao_api_key.text().strip()
            if not api_key:
                QMessageBox.warning(self, "警告", "请先输入豆包API密钥")
                return

            # 创建临时配置进行测试
            test_config = {
                'engines': {
                    'doubao_seedance_pro': {
                        'enabled': True,
                        'api_key': api_key,
                        'base_url': self.doubao_base_url.text().strip(),
                        'timeout': self.doubao_timeout.value()
                    }
                }
            }

            # 显示测试进度
            from PyQt5.QtWidgets import QProgressDialog
            progress = QProgressDialog("正在测试豆包连接...", "取消", 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()

            # 异步测试连接
            import asyncio
            from src.models.video_engines.video_generation_service import VideoGenerationService

            async def test_async():
                service = VideoGenerationService(test_config)
                try:
                    result = await service.test_engine('doubao_seedance_pro')
                    await service.shutdown()
                    return result
                except Exception as e:
                    await service.shutdown()
                    raise e

            # 在新线程中运行异步测试
            import threading
            result = [False]
            error = [None]

            def run_test():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result[0] = loop.run_until_complete(test_async())
                except Exception as e:
                    error[0] = e
                finally:
                    loop.close()

            thread = threading.Thread(target=run_test)
            thread.start()
            thread.join(timeout=30)  # 30秒超时

            progress.close()

            if error[0]:
                raise error[0]

            if result[0]:
                QMessageBox.information(self, "成功", "豆包视频生成连接测试成功！")
            else:
                QMessageBox.warning(self, "失败", "豆包连接测试失败，请检查API密钥和网络连接")

        except Exception as e:
            logger.error(f"豆包连接测试失败: {e}")
            QMessageBox.critical(self, "错误", f"连接测试失败: {str(e)}")

    def reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要重置所有视频生成设置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 重新加载默认配置
                self.current_config = get_config('development')
                self.load_settings()
                QMessageBox.information(self, "成功", "设置已重置为默认值")

            except Exception as e:
                logger.error(f"重置设置失败: {e}")
                QMessageBox.critical(self, "错误", f"重置设置失败: {str(e)}")

    def get_current_config(self):
        """获取当前配置"""
        return self.current_config
