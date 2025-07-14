# -*- coding: utf-8 -*-
"""
账号配置对话框
用于添加和配置平台账号
"""

import json
from typing import Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox,
    QMessageBox, QTabWidget, QWidget, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from src.services.platform_publisher.publisher_factory import PublisherFactory
from src.utils.logger import logger

class AccountConfigDialog(QDialog):
    """账号配置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加平台账号")
        self.setModal(True)
        self.resize(500, 400)
        
        self.publisher_factory = PublisherFactory()
        self.account_data = {}
        
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 平台选择
        platform_group = QGroupBox("选择平台")
        platform_layout = QGridLayout(platform_group)
        
        platform_layout.addWidget(QLabel("平台:"), 0, 0)
        self.platform_combo = QComboBox()
        
        # 添加支持的平台
        supported_platforms = self.publisher_factory.get_supported_platforms()
        platform_display_names = {
            'bilibili': 'B站 (bilibili.com)',
            'douyin': '抖音',
            'kuaishou': '快手',
            'xiaohongshu': '小红书',
            'wechat_channels': '微信视频号',
            'youtube': 'YouTube'
        }
        
        for platform in supported_platforms:
            display_name = platform_display_names.get(platform, platform.upper())
            self.platform_combo.addItem(display_name, platform)
            
        self.platform_combo.currentTextChanged.connect(self.on_platform_changed)
        platform_layout.addWidget(self.platform_combo, 0, 1)
        
        platform_layout.addWidget(QLabel("账号名称:"), 1, 0)
        self.account_name_edit = QLineEdit()
        self.account_name_edit.setPlaceholderText("输入账号显示名称...")
        platform_layout.addWidget(self.account_name_edit, 1, 1)
        
        layout.addWidget(platform_group)
        
        # 认证配置
        auth_group = QGroupBox("认证配置")
        auth_layout = QVBoxLayout(auth_group)
        
        # 创建标签页用于不同的认证方式
        self.auth_tabs = QTabWidget()
        
        # Cookie认证标签页
        cookie_tab = QWidget()
        cookie_layout = QVBoxLayout(cookie_tab)
        
        cookie_layout.addWidget(QLabel("Cookie信息:"))
        self.cookie_text = QTextEdit()
        self.cookie_text.setPlaceholderText("""
请输入从浏览器复制的Cookie信息，格式如下：
SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx; ...

或者JSON格式：
{
    "SESSDATA": "xxx",
    "bili_jct": "xxx",
    "DedeUserID": "xxx"
}
        """.strip())
        self.cookie_text.setMaximumHeight(150)
        cookie_layout.addWidget(self.cookie_text)
        
        # Cookie获取说明
        cookie_help = QLabel("""
        <b>Cookie获取方法：</b><br>
        1. 在浏览器中登录对应平台<br>
        2. 按F12打开开发者工具<br>
        3. 切换到Network标签页<br>
        4. 刷新页面，找到主页面请求<br>
        5. 在Request Headers中找到Cookie字段<br>
        6. 复制Cookie值到上方文本框
        """)
        cookie_help.setWordWrap(True)
        cookie_help.setStyleSheet("color: #666; font-size: 12px;")
        cookie_layout.addWidget(cookie_help)
        
        self.auth_tabs.addTab(cookie_tab, "Cookie认证")
        
        # API密钥认证标签页（为将来扩展准备）
        api_tab = QWidget()
        api_layout = QVBoxLayout(api_tab)
        
        api_layout.addWidget(QLabel("API密钥:"))
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("输入API密钥...")
        api_layout.addWidget(self.api_key_edit)
        
        api_layout.addWidget(QLabel("API密钥ID:"))
        self.api_key_id_edit = QLineEdit()
        self.api_key_id_edit.setPlaceholderText("输入API密钥ID（如果需要）...")
        api_layout.addWidget(self.api_key_id_edit)
        
        api_help = QLabel("API认证方式适用于支持官方API的平台")
        api_help.setStyleSheet("color: #666; font-size: 12px;")
        api_layout.addWidget(api_help)
        
        api_layout.addStretch()
        
        self.auth_tabs.addTab(api_tab, "API认证")
        
        auth_layout.addWidget(self.auth_tabs)
        layout.addWidget(auth_group)
        
        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QGridLayout(advanced_group)
        
        self.auto_login_check = QCheckBox("自动登录验证")
        self.auto_login_check.setChecked(True)
        advanced_layout.addWidget(self.auto_login_check, 0, 0)
        
        self.save_credentials_check = QCheckBox("保存认证信息")
        self.save_credentials_check.setChecked(True)
        advanced_layout.addWidget(self.save_credentials_check, 0, 1)
        
        layout.addWidget(advanced_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.test_connection)
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept_config)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.test_button)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 初始化界面状态
        self.on_platform_changed()
        
    def on_platform_changed(self):
        """平台改变时的处理"""
        current_platform = self.platform_combo.currentData()
        
        # 根据平台调整界面
        if current_platform == 'bilibili':
            self.auth_tabs.setCurrentIndex(0)  # Cookie认证
            self.auth_tabs.setTabEnabled(1, False)  # 禁用API认证
        else:
            # 其他平台暂时只支持Cookie认证
            self.auth_tabs.setCurrentIndex(0)
            self.auth_tabs.setTabEnabled(1, False)
            
    def test_connection(self):
        """测试连接"""
        try:
            if not self.validate_input():
                return
                
            platform = self.platform_combo.currentData()
            credentials = self.get_credentials()
            
            # 创建发布器并测试认证
            publisher = self.publisher_factory.create_publisher(platform)
            if not publisher:
                QMessageBox.warning(self, "警告", f"不支持的平台: {platform}")
                return
                
            # 这里应该异步测试认证，但为了简化，暂时显示提示
            QMessageBox.information(self, "提示", "连接测试功能将在后续版本中实现")
            
        except Exception as e:
            logger.error(f"测试连接失败: {e}")
            QMessageBox.critical(self, "错误", f"测试连接失败: {e}")
            
    def validate_input(self) -> bool:
        """验证输入"""
        if not self.account_name_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入账号名称")
            return False
            
        current_tab = self.auth_tabs.currentIndex()
        
        if current_tab == 0:  # Cookie认证
            if not self.cookie_text.toPlainText().strip():
                QMessageBox.warning(self, "警告", "请输入Cookie信息")
                return False
        elif current_tab == 1:  # API认证
            if not self.api_key_edit.text().strip():
                QMessageBox.warning(self, "警告", "请输入API密钥")
                return False
                
        return True
        
    def get_credentials(self) -> Dict[str, Any]:
        """获取认证凭据"""
        current_tab = self.auth_tabs.currentIndex()
        
        if current_tab == 0:  # Cookie认证
            cookie_text = self.cookie_text.toPlainText().strip()
            
            # 尝试解析JSON格式
            try:
                cookies = json.loads(cookie_text)
                if isinstance(cookies, dict):
                    return {'cookies': cookies}
            except:
                pass
                
            # 解析字符串格式的Cookie
            cookies = {}
            for item in cookie_text.split(';'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies[key.strip()] = value.strip()
                    
            return {'cookies': cookies}
            
        elif current_tab == 1:  # API认证
            return {
                'api_key': self.api_key_edit.text().strip(),
                'api_key_id': self.api_key_id_edit.text().strip()
            }
            
        return {}
        
    def accept_config(self):
        """确认配置"""
        try:
            if not self.validate_input():
                return
                
            self.account_data = {
                'platform': self.platform_combo.currentData(),
                'account_name': self.account_name_edit.text().strip(),
                'credentials': self.get_credentials(),
                'auto_login': self.auto_login_check.isChecked(),
                'save_credentials': self.save_credentials_check.isChecked()
            }
            
            self.accept()
            
        except Exception as e:
            logger.error(f"配置账号失败: {e}")
            QMessageBox.critical(self, "错误", f"配置失败: {e}")
            
    def get_account_data(self) -> Dict[str, Any]:
        """获取账号数据"""
        return self.account_data
