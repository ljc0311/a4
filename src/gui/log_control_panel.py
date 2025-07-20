# -*- coding: utf-8 -*-
"""
日志控制面板
提供图形界面来调整日志设置
"""

import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QComboBox, QLabel, QPushButton, QTextEdit,
    QCheckBox, QSpinBox, QFormLayout, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

try:
    from src.utils.log_config_manager import (
        log_config_manager,
        enable_verbose_mode,
        enable_quiet_mode,
        enable_normal_mode,
        set_console_level,
        set_file_level,
        get_config_summary,
        reset_to_default
    )
except ImportError:
    # 如果导入失败，创建模拟对象
    class MockLogConfigManager:
        def get_config_summary(self):
            return "日志配置管理器未可用"
        
        def enable_normal_mode(self):
            pass
            
        def enable_quiet_mode(self):
            pass
            
        def enable_verbose_mode(self):
            pass
    
    log_config_manager = MockLogConfigManager()
    enable_verbose_mode = log_config_manager.enable_verbose_mode
    enable_quiet_mode = log_config_manager.enable_quiet_mode
    enable_normal_mode = log_config_manager.enable_normal_mode
    set_console_level = lambda x: None
    set_file_level = lambda x: None
    get_config_summary = log_config_manager.get_config_summary
    reset_to_default = lambda: None


class LogControlPanel(QWidget):
    """日志控制面板"""
    
    config_changed = pyqtSignal()  # 配置改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_current_config()
        
    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("日志输出控制")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 快速模式选择
        mode_group = QGroupBox("快速模式")
        mode_layout = QHBoxLayout(mode_group)
        
        self.normal_btn = QPushButton("正常模式")
        self.normal_btn.setToolTip("控制台显示警告及以上，文件记录所有日志（推荐）")
        self.normal_btn.clicked.connect(self.set_normal_mode)
        
        self.quiet_btn = QPushButton("安静模式")
        self.quiet_btn.setToolTip("控制台只显示错误，减少输出干扰")
        self.quiet_btn.clicked.connect(self.set_quiet_mode)
        
        self.verbose_btn = QPushButton("详细模式")
        self.verbose_btn.setToolTip("显示所有日志信息，用于调试")
        self.verbose_btn.clicked.connect(self.set_verbose_mode)
        
        mode_layout.addWidget(self.normal_btn)
        mode_layout.addWidget(self.quiet_btn)
        mode_layout.addWidget(self.verbose_btn)
        layout.addWidget(mode_group)
        
        # 详细设置
        detail_group = QGroupBox("详细设置")
        detail_layout = QFormLayout(detail_group)
        
        # 控制台日志级别
        self.console_level_combo = QComboBox()
        self.console_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.console_level_combo.currentTextChanged.connect(self.on_console_level_changed)
        detail_layout.addRow("控制台日志级别:", self.console_level_combo)
        
        # 文件日志级别
        self.file_level_combo = QComboBox()
        self.file_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.file_level_combo.currentTextChanged.connect(self.on_file_level_changed)
        detail_layout.addRow("文件日志级别:", self.file_level_combo)
        
        layout.addWidget(detail_group)
        
        # 当前配置显示
        config_group = QGroupBox("当前配置")
        config_layout = QVBoxLayout(config_group)
        
        self.config_text = QTextEdit()
        self.config_text.setMaximumHeight(150)
        self.config_text.setReadOnly(True)
        config_layout.addWidget(self.config_text)
        
        # 刷新和重置按钮
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新配置")
        self.refresh_btn.clicked.connect(self.refresh_config)
        
        self.reset_btn = QPushButton("重置默认")
        self.reset_btn.clicked.connect(self.reset_config)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.reset_btn)
        config_layout.addLayout(button_layout)
        
        layout.addWidget(config_group)
        
        # 说明文本
        help_text = QLabel(
            "说明:\n"
            "• 正常模式：推荐日常使用，减少终端输出但保留完整日志文件\n"
            "• 安静模式：最小化输出，只显示重要错误信息\n"
            "• 详细模式：显示所有日志，用于问题调试\n"
            "• 所有异常和错误信息都会被完整保留"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
        layout.addWidget(help_text)
        
    def load_current_config(self):
        """加载当前配置"""
        try:
            # 设置当前选择的级别
            console_level = log_config_manager.config.get('console_level', 'WARNING')
            file_level = log_config_manager.config.get('file_level', 'DEBUG')
            
            self.console_level_combo.setCurrentText(console_level)
            self.file_level_combo.setCurrentText(file_level)
            
            # 更新配置显示
            self.refresh_config()
        except Exception as e:
            self.config_text.setText(f"加载配置失败: {e}")
    
    def refresh_config(self):
        """刷新配置显示"""
        try:
            config_summary = get_config_summary()
            self.config_text.setText(config_summary)
        except Exception as e:
            self.config_text.setText(f"获取配置失败: {e}")
    
    def set_normal_mode(self):
        """设置正常模式"""
        try:
            enable_normal_mode()
            self.load_current_config()
            self.config_changed.emit()
            QMessageBox.information(self, "成功", "已切换到正常模式")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"设置失败: {e}")
    
    def set_quiet_mode(self):
        """设置安静模式"""
        try:
            enable_quiet_mode()
            self.load_current_config()
            self.config_changed.emit()
            QMessageBox.information(self, "成功", "已切换到安静模式")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"设置失败: {e}")
    
    def set_verbose_mode(self):
        """设置详细模式"""
        try:
            enable_verbose_mode()
            self.load_current_config()
            self.config_changed.emit()
            QMessageBox.information(self, "成功", "已切换到详细模式")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"设置失败: {e}")
    
    def on_console_level_changed(self, level):
        """控制台级别改变"""
        try:
            set_console_level(level)
            self.refresh_config()
            self.config_changed.emit()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"设置控制台级别失败: {e}")
    
    def on_file_level_changed(self, level):
        """文件级别改变"""
        try:
            set_file_level(level)
            self.refresh_config()
            self.config_changed.emit()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"设置文件级别失败: {e}")
    
    def reset_config(self):
        """重置配置"""
        reply = QMessageBox.question(
            self, "确认重置", 
            "确定要重置为默认日志配置吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                reset_to_default()
                self.load_current_config()
                self.config_changed.emit()
                QMessageBox.information(self, "成功", "已重置为默认配置")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"重置失败: {e}")


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    panel = LogControlPanel()
    panel.show()
    sys.exit(app.exec_())