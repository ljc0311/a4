#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目对话框
新建项目、打开项目等对话框界面
"""

import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QPushButton, QFormLayout, QGroupBox, QListWidget,
    QListWidgetItem, QMessageBox, QFileDialog, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

try:
    from src.utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class NewProjectDialog(QDialog):
    """新建项目对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_name = ""
        self.project_description = ""
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("新建项目")
        self.setFixedSize(450, 300)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("创建新的AI视频项目")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 表单区域
        form_group = QGroupBox("项目信息")
        form_layout = QFormLayout(form_group)
        
        # 项目名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入项目名称...")
        self.name_edit.textChanged.connect(self.validate_input)
        form_layout.addRow("项目名称 *:", self.name_edit)
        
        # 项目描述
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("请输入项目描述（可选）...")
        self.description_edit.setMaximumHeight(80)
        form_layout.addRow("项目描述:", self.description_edit)
        
        layout.addWidget(form_group)
        
        # 提示信息
        info_label = QLabel("• 项目名称不能为空\n• 将在output文件夹中创建同名子文件夹\n• 所有生成的内容都将保存在项目文件夹中")
        info_label.setStyleSheet("color: #666666; font-size: 12px;")
        layout.addWidget(info_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.create_btn = QPushButton("创建项目")
        self.create_btn.clicked.connect(self.accept)
        self.create_btn.setEnabled(False)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005999;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        button_layout.addWidget(self.create_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # 设置焦点
        self.name_edit.setFocus()
    
    def validate_input(self):
        """验证输入"""
        name = self.name_edit.text().strip()
        self.create_btn.setEnabled(len(name) > 0)
    
    def accept(self):
        """确认创建"""
        self.project_name = self.name_edit.text().strip()
        self.project_description = self.description_edit.toPlainText().strip()
        
        if not self.project_name:
            QMessageBox.warning(self, "警告", "项目名称不能为空！")
            return
        
        super().accept()
    
    def get_project_info(self):
        """获取项目信息"""
        return {
            "name": self.project_name,
            "description": self.project_description
        }

class OpenProjectDialog(QDialog):
    """打开项目对话框"""
    
    def __init__(self, project_list, parent=None):
        super().__init__(parent)
        self.project_list = project_list
        self.selected_project = None
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("打开项目")
        self.setFixedSize(600, 400)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("选择要打开的项目")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 项目列表
        self.project_list_widget = QListWidget()
        self.project_list_widget.itemDoubleClicked.connect(self.accept)
        self.project_list_widget.itemClicked.connect(self.on_item_selected)
        
        for project in self.project_list:
            item = QListWidgetItem()
            item_text = f"📁 {project['name']}\n"
            item_text += f"   创建时间: {project['created_time'][:19].replace('T', ' ')}\n"
            item_text += f"   修改时间: {project['last_modified'][:19].replace('T', ' ')}\n"
            item_text += f"   路径: {project['path']}"
            item.setText(item_text)
            item.setData(Qt.UserRole, project)
            self.project_list_widget.addItem(item)
        
        layout.addWidget(self.project_list_widget)
        
        # 操作区域
        actions_layout = QHBoxLayout()

        self.browse_btn = QPushButton("浏览文件夹...")
        self.browse_btn.clicked.connect(self.browse_project)
        actions_layout.addWidget(self.browse_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.open_btn = QPushButton("打开项目")
        self.open_btn.clicked.connect(self.accept)
        self.open_btn.setEnabled(False)
        self.open_btn.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005999;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        button_layout.addWidget(self.open_btn)

        # 删除按钮放在打开按钮右侧
        self.delete_btn = QPushButton("删除项目")
        self.delete_btn.clicked.connect(self.delete_project)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #C82333;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        button_layout.addWidget(self.delete_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def on_item_selected(self, item):
        """项目选中事件"""
        self.selected_project = item.data(Qt.UserRole)
        self.open_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
    
    def browse_project(self):
        """浏览项目文件夹"""
        project_dir = QFileDialog.getExistingDirectory(
            self, "选择项目文件夹", "output"
        )
        if project_dir:
            project_file = Path(project_dir) / "project.json"
            if project_file.exists():
                self.selected_project = {"path": project_dir}
                self.accept()
            else:
                QMessageBox.warning(self, "警告", "选择的文件夹不是有效的项目目录！")
    
    def delete_project(self):
        """删除项目"""
        if not self.selected_project:
            return

        project_name = self.selected_project.get('name', '未知项目')
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除项目 '{project_name}' 吗？\n\n此操作将永久删除项目文件夹及其所有内容，不可撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                project_path = self.selected_project['path']

                # 尝试使用项目管理器删除项目
                try:
                    from src.core.project_manager import ProjectManager
                    project_manager = ProjectManager()
                    success = project_manager.delete_project(project_path)
                    if not success:
                        # 如果项目管理器删除失败，直接删除文件夹
                        import shutil
                        shutil.rmtree(project_path)
                except ImportError:
                    # 如果无法导入项目管理器，直接删除文件夹
                    import shutil
                    shutil.rmtree(project_path)

                # 从列表中移除
                current_row = self.project_list_widget.currentRow()
                if current_row >= 0:
                    self.project_list_widget.takeItem(current_row)

                # 重置选择状态
                self.selected_project = None
                self.open_btn.setEnabled(False)
                self.delete_btn.setEnabled(False)

                QMessageBox.information(self, "成功", f"项目 '{project_name}' 已删除！")
                logger.info(f"项目已删除: {project_name} -> {project_path}")

            except Exception as e:
                error_msg = f"删除项目失败：{str(e)}"
                logger.error(error_msg)
                QMessageBox.critical(self, "错误", error_msg)
    
    def accept(self):
        """确认打开"""
        if not self.selected_project:
            QMessageBox.warning(self, "警告", "请选择一个项目！")
            return
        
        super().accept()
    
    def get_selected_project(self):
        """获取选中的项目"""
        return self.selected_project