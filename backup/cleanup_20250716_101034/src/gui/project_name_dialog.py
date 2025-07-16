import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QTextEdit
)
from PyQt5.QtCore import Qt
from src.utils.logger import logger

class ProjectNameDialog(QDialog):
    """项目命名对话框"""
    
    def __init__(self, parent=None, existing_projects=None):
        super().__init__(parent)
        self.existing_projects = existing_projects or []
        self.project_name = ""
        self.project_description = ""
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("新建项目")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("创建新项目")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 项目名称输入
        name_label = QLabel("项目名称:")
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入项目名称（必填）")
        self.name_input.textChanged.connect(self.validate_input)
        layout.addWidget(self.name_input)
        
        # 项目描述输入
        desc_label = QLabel("项目描述:")
        layout.addWidget(desc_label)
        
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("请输入项目描述（可选）")
        self.desc_input.setMaximumHeight(80)
        layout.addWidget(self.desc_input)
        
        # 提示信息
        tip_label = QLabel("提示：项目名称将用作文件夹名称，请避免使用特殊字符")
        tip_label.setStyleSheet("color: #666; font-size: 12px; margin-top: 10px;")
        layout.addWidget(tip_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.create_btn = QPushButton("创建项目")
        self.create_btn.clicked.connect(self.create_project)
        self.create_btn.setEnabled(False)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """)
        button_layout.addWidget(self.create_btn)
        
        layout.addLayout(button_layout)
        
        # 设置焦点
        self.name_input.setFocus()
        
    def validate_input(self):
        """验证输入"""
        name = self.name_input.text().strip()
        
        # 检查是否为空
        if not name:
            self.create_btn.setEnabled(False)
            return
        
        # 检查是否包含非法字符
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        if any(char in name for char in invalid_chars):
            self.create_btn.setEnabled(False)
            return
        
        # 检查是否已存在
        if name in self.existing_projects:
            self.create_btn.setEnabled(False)
            return
        
        self.create_btn.setEnabled(True)
        
    def create_project(self):
        """创建项目"""
        name = self.name_input.text().strip()
        description = self.desc_input.toPlainText().strip()
        
        # 最终验证
        if not name:
            QMessageBox.warning(self, "错误", "项目名称不能为空")
            return
        
        # 检查非法字符
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        if any(char in name for char in invalid_chars):
            QMessageBox.warning(self, "错误", "项目名称包含非法字符，请使用字母、数字、下划线或中文")
            return
        
        # 检查是否已存在
        if name in self.existing_projects:
            QMessageBox.warning(self, "错误", "项目名称已存在，请使用其他名称")
            return
        
        self.project_name = name
        self.project_description = description
        
        logger.info(f"创建新项目: {name}")
        self.accept()
        
    def get_project_info(self):
        """获取项目信息"""
        return {
            'name': self.project_name,
            'description': self.project_description
        }