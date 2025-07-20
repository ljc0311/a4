#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台登录界面组件
提供用户友好的平台登录管理界面
"""

import webbrowser
from typing import Dict, Any, Optional, List
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QGroupBox, QScrollArea,
    QFrame, QMessageBox, QProgressBar, QTextEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor

from src.services.platform_publisher.login_manager import login_manager
from src.services.platform_publisher.integrated_browser_manager import IntegratedBrowserManager
from src.utils.logger import logger


class LoginStatusThread(QThread):
    """登录状态检查线程"""
    status_updated = pyqtSignal(dict)
    
    def run(self):
        try:
            status = login_manager.get_all_login_status()
            self.status_updated.emit(status)
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")


class PlatformLoginCard(QFrame):
    """平台登录卡片"""
    
    def __init__(self, platform_id: str, platform_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.platform_id = platform_id
        self.platform_info = platform_info
        self.parent_widget = parent
        
        self.init_ui()
        self.update_status()
        
    def init_ui(self):
        """初始化UI"""
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            PlatformLoginCard {
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: #f9f9f9;
                margin: 4px;
            }
            PlatformLoginCard:hover {
                border-color: #007acc;
                background-color: #f0f8ff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # 平台标题
        title_layout = QHBoxLayout()
        
        self.icon_label = QLabel(self.platform_info['icon'])
        self.icon_label.setFont(QFont("Segoe UI Emoji", 16))
        title_layout.addWidget(self.icon_label)
        
        self.name_label = QLabel(self.platform_info['name'])
        self.name_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        title_layout.addWidget(self.name_label)
        
        title_layout.addStretch()
        
        # 状态指示器
        self.status_label = QLabel("❌ 未登录")
        self.status_label.setFont(QFont("Microsoft YaHei", 10))
        title_layout.addWidget(self.status_label)
        
        layout.addLayout(title_layout)
        
        # 用户信息
        self.user_info_label = QLabel("请先登录")
        self.user_info_label.setFont(QFont("Microsoft YaHei", 9))
        self.user_info_label.setStyleSheet("color: #666;")
        layout.addWidget(self.user_info_label)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.login_btn = QPushButton("🌐 登录")
        self.login_btn.clicked.connect(self.open_login_page)
        self.login_btn.setMinimumHeight(32)
        button_layout.addWidget(self.login_btn)
        
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self.save_login_status)
        self.save_btn.setEnabled(False)
        self.save_btn.setMinimumHeight(32)
        button_layout.addWidget(self.save_btn)
        
        self.clear_btn = QPushButton("🗑️ 清除")
        self.clear_btn.clicked.connect(self.clear_login_info)
        self.clear_btn.setMinimumHeight(32)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
    def update_status(self):
        """更新登录状态"""
        try:
            status = login_manager.get_all_login_status().get(self.platform_id, {})
            
            if status.get('is_logged_in', False):
                self.status_label.setText("✅ 已登录")
                self.status_label.setStyleSheet("color: #28a745;")
                
                # 显示用户信息
                user_info = status.get('user_info', {})
                login_time = status.get('login_time', '')
                
                if login_time:
                    from datetime import datetime
                    try:
                        login_dt = datetime.fromisoformat(login_time.replace('Z', '+00:00'))
                        time_str = login_dt.strftime('%m-%d %H:%M')
                        self.user_info_label.setText(f"登录时间: {time_str}")
                    except:
                        self.user_info_label.setText("已登录")
                else:
                    self.user_info_label.setText("已登录")
                    
                self.login_btn.setText("🔄 重新登录")
                self.save_btn.setEnabled(False)
                self.clear_btn.setEnabled(True)
                
            else:
                self.status_label.setText("❌ 未登录")
                self.status_label.setStyleSheet("color: #dc3545;")
                self.user_info_label.setText("请先登录")
                
                self.login_btn.setText("🌐 登录")
                self.save_btn.setEnabled(True)
                self.clear_btn.setEnabled(False)
                
        except Exception as e:
            logger.error(f"更新{self.platform_id}状态失败: {e}")
            
    def open_login_page(self):
        """打开登录页面"""
        try:
            login_url = self.platform_info['url']
            webbrowser.open(login_url)
            
            # 启用保存按钮
            self.save_btn.setEnabled(True)
            
            # 显示提示
            QMessageBox.information(
                self,
                "登录提示",
                f"已在浏览器中打开{self.platform_info['name']}登录页面。\n\n"
                f"请在浏览器中完成登录，然后点击'保存'按钮保存登录状态。"
            )
            
        except Exception as e:
            logger.error(f"打开{self.platform_id}登录页面失败: {e}")
            QMessageBox.critical(self, "错误", f"打开登录页面失败：{e}")
            
    def save_login_status(self):
        """保存登录状态"""
        try:
            # 这里需要与浏览器管理器配合
            if hasattr(self.parent_widget, 'browser_manager') and self.parent_widget.browser_manager:
                browser_config = self.parent_widget.browser_manager.browser_config
                if browser_config and browser_config.get('success'):
                    # 模拟保存登录状态
                    user_info = {
                        'platform': self.platform_id,
                        'saved_at': str(datetime.now()),
                        'method': 'manual_save'
                    }
                    
                    success = login_manager.save_login_info(self.platform_id, user_info)
                    
                    if success:
                        QMessageBox.information(
                            self,
                            "保存成功",
                            f"{self.platform_info['name']}登录状态保存成功！\n\n"
                            f"下次使用时将自动登录。"
                        )
                        self.update_status()
                        
                        # 通知父组件更新
                        if hasattr(self.parent_widget, 'refresh_all_status'):
                            self.parent_widget.refresh_all_status()
                    else:
                        QMessageBox.warning(self, "保存失败", "登录状态保存失败，请重试。")
                else:
                    QMessageBox.warning(
                        self, 
                        "浏览器未就绪", 
                        "请先在主界面设置浏览器环境，然后再保存登录状态。"
                    )
            else:
                QMessageBox.warning(
                    self, 
                    "功能未就绪", 
                    "浏览器管理器未初始化，请先在主界面设置浏览器环境。"
                )
                
        except Exception as e:
            logger.error(f"保存{self.platform_id}登录状态失败: {e}")
            QMessageBox.critical(self, "错误", f"保存登录状态失败：{e}")
            
    def clear_login_info(self):
        """清除登录信息"""
        try:
            reply = QMessageBox.question(
                self,
                "确认清除",
                f"确定要清除{self.platform_info['name']}的登录信息吗？\n\n"
                f"清除后需要重新登录。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                login_manager.clear_login_info(self.platform_id)
                self.update_status()
                
                # 通知父组件更新
                if hasattr(self.parent_widget, 'refresh_all_status'):
                    self.parent_widget.refresh_all_status()
                    
                QMessageBox.information(
                    self,
                    "清除成功",
                    f"{self.platform_info['name']}登录信息已清除。"
                )
                
        except Exception as e:
            logger.error(f"清除{self.platform_id}登录信息失败: {e}")
            QMessageBox.critical(self, "错误", f"清除登录信息失败：{e}")


class PlatformLoginWidget(QWidget):
    """平台登录管理界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.browser_manager = None
        self.browser_config = None
        self.login_cards = {}
        
        self.init_ui()
        self.refresh_all_status()
        
        # 定期刷新状态
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_all_status)
        self.refresh_timer.start(30000)  # 30秒刷新一次
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("🔐 平台登录管理")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明文本
        info_text = QTextEdit()
        info_text.setPlainText(login_manager.get_login_guide_text())
        info_text.setMaximumHeight(120)
        info_text.setReadOnly(True)
        info_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        layout.addWidget(info_text)
        
        # 全局操作按钮
        global_actions_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 刷新状态")
        self.refresh_btn.clicked.connect(self.refresh_all_status)
        global_actions_layout.addWidget(self.refresh_btn)
        
        self.cleanup_btn = QPushButton("🧹 清理过期")
        self.cleanup_btn.clicked.connect(self.cleanup_expired)
        global_actions_layout.addWidget(self.cleanup_btn)
        
        global_actions_layout.addStretch()
        
        layout.addLayout(global_actions_layout)
        
        # 平台登录卡片区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.cards_layout = QGridLayout(scroll_widget)
        self.cards_layout.setSpacing(10)
        
        # 创建平台登录卡片
        self.create_login_cards()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(400)
        layout.addWidget(scroll_area)
        
    def create_login_cards(self):
        """创建登录卡片"""
        platforms = login_manager.get_platform_login_urls()
        
        row = 0
        col = 0
        max_cols = 2
        
        for platform_id, platform_info in platforms.items():
            card = PlatformLoginCard(platform_id, platform_info, self)
            self.login_cards[platform_id] = card
            
            self.cards_layout.addWidget(card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
                
    def set_browser_manager(self, browser_manager, browser_config):
        """设置浏览器管理器"""
        self.browser_manager = browser_manager
        self.browser_config = browser_config
        
    def refresh_all_status(self):
        """刷新所有平台状态"""
        try:
            for card in self.login_cards.values():
                card.update_status()
                
        except Exception as e:
            logger.error(f"刷新登录状态失败: {e}")
            
    def cleanup_expired(self):
        """清理过期登录"""
        try:
            login_manager.cleanup_expired_logins()
            self.refresh_all_status()
            
            QMessageBox.information(
                self,
                "清理完成",
                "过期的登录信息已清理完成。"
            )
            
        except Exception as e:
            logger.error(f"清理过期登录失败: {e}")
            QMessageBox.critical(self, "错误", f"清理过期登录失败：{e}")
            
    def get_logged_in_platforms(self) -> List[str]:
        """获取已登录的平台列表"""
        logged_in = []
        status = login_manager.get_all_login_status()
        
        for platform_id, info in status.items():
            if info.get('is_logged_in', False):
                logged_in.append(platform_id)
                
        return logged_in
