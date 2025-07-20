"""
失败检测对话框
用于显示分镜生成和增强描述失败的情况，并提供重试功能
"""

import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, 
                             QTextEdit, QTabWidget, QWidget, QCheckBox,
                             QMessageBox, QProgressDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

logger = logging.getLogger(__name__)

class RetryThread(QThread):
    """重试线程"""
    progress_updated = pyqtSignal(str)
    retry_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, parent_tab, retry_type, failed_items):
        super().__init__()
        self.parent_tab = parent_tab
        self.retry_type = retry_type  # 'storyboard' 或 'enhancement'
        self.failed_items = failed_items
        self._is_cancelled = False
    
    def run(self):
        """执行重试操作"""
        try:
            if self.retry_type == 'storyboard':
                self._retry_storyboard_generation()
            elif self.retry_type == 'enhancement':
                self._retry_enhancement()
            else:
                raise ValueError(f"未知的重试类型: {self.retry_type}")
                
        except Exception as e:
            logger.error(f"重试操作失败: {e}")
            self.retry_completed.emit(False, f"重试失败: {str(e)}")
    
    def _retry_storyboard_generation(self):
        """重试分镜生成"""
        self.progress_updated.emit("正在重试分镜生成...")
        
        # 获取必要的数据
        world_bible = self.parent_tab.stage_data.get(1, {}).get("world_bible", "")
        scenes_analysis = self.parent_tab.stage_data.get(3, {}).get("scenes_analysis", "")
        
        success_count = 0
        total_count = len(self.failed_items)
        
        for i, failed_item in enumerate(self.failed_items):
            if self._is_cancelled:
                break
                
            scene_index = failed_item.get("scene_index", 0)
            scene_info = failed_item.get("scene_info", "")
            
            self.progress_updated.emit(f"正在重试第{i+1}/{total_count}个失败的分镜...")
            
            try:
                # 重新生成分镜
                success = self.parent_tab._retry_single_storyboard(
                    scene_index, scene_info, world_bible, scenes_analysis
                )
                if success:
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"重试第{scene_index+1}个场景分镜失败: {e}")
                continue
        
        if success_count == total_count:
            self.retry_completed.emit(True, f"所有{total_count}个分镜重试成功")
        elif success_count > 0:
            self.retry_completed.emit(True, f"{success_count}/{total_count}个分镜重试成功")
        else:
            self.retry_completed.emit(False, "所有分镜重试均失败")
    
    def _retry_enhancement(self):
        """重试增强描述"""
        self.progress_updated.emit("正在重试增强描述...")
        
        success_count = 0
        total_count = len(self.failed_items)
        
        for i, failed_item in enumerate(self.failed_items):
            if self._is_cancelled:
                break
                
            scene_index = failed_item.get("scene_index", 0)
            scene_info = failed_item.get("scene_info", "")
            
            self.progress_updated.emit(f"正在重试第{i+1}/{total_count}个失败的增强描述...")
            
            try:
                # 重新生成增强描述
                success = self.parent_tab._retry_single_enhancement(scene_index, scene_info)
                if success:
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"重试第{scene_index+1}个场景增强描述失败: {e}")
                continue
        
        if success_count == total_count:
            self.retry_completed.emit(True, f"所有{total_count}个增强描述重试成功")
        elif success_count > 0:
            self.retry_completed.emit(True, f"{success_count}/{total_count}个增强描述重试成功")
        else:
            self.retry_completed.emit(False, "所有增强描述重试均失败")
    
    def cancel(self):
        """取消重试"""
        self._is_cancelled = True

class FailureDetectionDialog(QDialog):
    """失败检测对话框"""
    
    def __init__(self, parent=None, failed_storyboards=None, failed_enhancements=None):
        super().__init__(parent)
        self.parent_tab = parent
        self.failed_storyboards = failed_storyboards or []
        self.failed_enhancements = failed_enhancements or []
        self.retry_thread = None
        
        self.setWindowTitle("检测到失败项目")
        self.setModal(True)
        self.resize(600, 500)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("检测到以下项目生成失败，请选择需要重试的项目：")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 分镜失败标签页
        if self.failed_storyboards:
            self.create_storyboard_tab()
        
        # 增强描述失败标签页
        if self.failed_enhancements:
            self.create_enhancement_tab()
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.retry_selected_btn = QPushButton("重试选中项目")
        self.retry_selected_btn.clicked.connect(self.retry_selected_items)
        button_layout.addWidget(self.retry_selected_btn)
        
        self.retry_all_btn = QPushButton("重试全部")
        self.retry_all_btn.clicked.connect(self.retry_all_items)
        button_layout.addWidget(self.retry_all_btn)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def create_storyboard_tab(self):
        """创建分镜失败标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 说明文字
        info_label = QLabel(f"检测到{len(self.failed_storyboards)}个分镜生成失败：")
        layout.addWidget(info_label)
        
        # 失败列表
        self.storyboard_list = QListWidget()
        for failed_item in self.failed_storyboards:
            scene_index = failed_item.get("scene_index", 0)
            scene_info = failed_item.get("scene_info", "")
            error = failed_item.get("error", "未知错误")

            # 安全处理scene_info，确保它是字符串
            if isinstance(scene_info, dict):
                # 如果是字典，尝试获取描述信息
                scene_info_str = scene_info.get('description', '') or scene_info.get('name', '') or str(scene_info)
            else:
                scene_info_str = str(scene_info) if scene_info else ""

            # 安全进行字符串切片
            if len(scene_info_str) > 50:
                scene_info_display = scene_info_str[:50] + "..."
            else:
                scene_info_display = scene_info_str

            item_text = f"场景{scene_index + 1}: {scene_info_display}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, failed_item)
            item.setCheckState(Qt.CheckState.Checked)
            
            # 添加错误信息到工具提示
            item.setToolTip(f"错误信息: {error}")
            
            self.storyboard_list.addItem(item)
        
        layout.addWidget(self.storyboard_list)
        
        # 全选/取消全选按钮
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(lambda: self.select_all_items(self.storyboard_list, True))
        select_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(lambda: self.select_all_items(self.storyboard_list, False))
        select_layout.addWidget(deselect_all_btn)
        
        select_layout.addStretch()
        layout.addLayout(select_layout)
        
        self.tab_widget.addTab(tab, f"分镜失败 ({len(self.failed_storyboards)})")
    
    def create_enhancement_tab(self):
        """创建增强描述失败标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 说明文字
        info_label = QLabel(f"检测到{len(self.failed_enhancements)}个增强描述生成失败：")
        layout.addWidget(info_label)
        
        # 失败列表
        self.enhancement_list = QListWidget()
        for failed_item in self.failed_enhancements:
            scene_index = failed_item.get("scene_index", 0)
            scene_info = failed_item.get("scene_info", "")
            error = failed_item.get("error", "未知错误")

            # 安全处理scene_info，确保它是字符串
            if isinstance(scene_info, dict):
                # 如果是字典，尝试获取描述信息
                scene_info_str = scene_info.get('description', '') or scene_info.get('name', '') or str(scene_info)
            else:
                scene_info_str = str(scene_info) if scene_info else ""

            # 安全进行字符串切片
            if len(scene_info_str) > 50:
                scene_info_display = scene_info_str[:50] + "..."
            else:
                scene_info_display = scene_info_str

            item_text = f"场景{scene_index + 1}: {scene_info_display}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, failed_item)
            item.setCheckState(Qt.CheckState.Checked)
            
            # 添加错误信息到工具提示
            item.setToolTip(f"错误信息: {error}")
            
            self.enhancement_list.addItem(item)
        
        layout.addWidget(self.enhancement_list)
        
        # 全选/取消全选按钮
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(lambda: self.select_all_items(self.enhancement_list, True))
        select_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(lambda: self.select_all_items(self.enhancement_list, False))
        select_layout.addWidget(deselect_all_btn)
        
        select_layout.addStretch()
        layout.addLayout(select_layout)
        
        self.tab_widget.addTab(tab, f"增强描述失败 ({len(self.failed_enhancements)})")
    
    def select_all_items(self, list_widget, checked):
        """全选或取消全选列表项"""
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
    
    def get_selected_items(self, list_widget):
        """获取选中的项目"""
        selected_items = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_items.append(item.data(Qt.ItemDataRole.UserRole))
        return selected_items
    
    def retry_selected_items(self):
        """重试选中的项目"""
        current_tab_index = self.tab_widget.currentIndex()
        
        if current_tab_index == 0 and hasattr(self, 'storyboard_list'):
            # 分镜失败标签页
            selected_items = self.get_selected_items(self.storyboard_list)
            if selected_items:
                self.start_retry('storyboard', selected_items)
            else:
                QMessageBox.warning(self, "警告", "请选择要重试的分镜项目")
                
        elif hasattr(self, 'enhancement_list'):
            # 增强描述失败标签页
            selected_items = self.get_selected_items(self.enhancement_list)
            if selected_items:
                self.start_retry('enhancement', selected_items)
            else:
                QMessageBox.warning(self, "警告", "请选择要重试的增强描述项目")
    
    def retry_all_items(self):
        """重试所有项目"""
        current_tab_index = self.tab_widget.currentIndex()
        
        if current_tab_index == 0 and self.failed_storyboards:
            # 分镜失败标签页
            self.start_retry('storyboard', self.failed_storyboards)
        elif hasattr(self, 'enhancement_list') and self.failed_enhancements:
            # 增强描述失败标签页
            self.start_retry('enhancement', self.failed_enhancements)
    
    def start_retry(self, retry_type, failed_items):
        """开始重试操作"""
        if not self.parent_tab:
            QMessageBox.warning(self, "错误", "无法获取父窗口引用")
            return
        
        # 显示进度对话框
        progress_dialog = QProgressDialog("正在重试...", "取消", 0, 0, self)
        progress_dialog.setModal(True)
        progress_dialog.show()
        
        # 创建重试线程
        self.retry_thread = RetryThread(self.parent_tab, retry_type, failed_items)
        self.retry_thread.progress_updated.connect(progress_dialog.setLabelText)
        self.retry_thread.retry_completed.connect(self.on_retry_completed)
        self.retry_thread.retry_completed.connect(progress_dialog.close)
        
        # 连接取消信号
        progress_dialog.canceled.connect(self.retry_thread.cancel)
        
        self.retry_thread.start()
    
    def on_retry_completed(self, success, message):
        """重试完成回调"""
        if success:
            QMessageBox.information(self, "重试完成", message)
            self.accept()  # 关闭对话框
        else:
            QMessageBox.warning(self, "重试失败", message)
