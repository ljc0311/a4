"""
图像生成失败检测对话框
用于显示图像生成失败的情况，并提供重试功能
"""

import logging
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, 
                             QTextEdit, QTabWidget, QWidget, QCheckBox,
                             QMessageBox, QProgressDialog, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

logger = logging.getLogger(__name__)

class ImageRetryThread(QThread):
    """图像重试线程"""
    progress_updated = pyqtSignal(str)
    retry_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, parent_tab, failed_items):
        super().__init__()
        self.parent_tab = parent_tab
        self.failed_items = failed_items
        self._is_cancelled = False
    
    def run(self):
        """执行重试操作"""
        try:
            self.progress_updated.emit("正在重试图像生成...")
            
            success_count = 0
            total_count = len(self.failed_items)
            
            for i, failed_item in enumerate(self.failed_items):
                if self._is_cancelled:
                    break
                    
                item_index = failed_item.get("item_index", 0)
                item_data = failed_item.get("item_data", {})
                
                self.progress_updated.emit(f"正在重试第{i+1}/{total_count}个失败的图像...")
                
                try:
                    # 重新生成图像
                    success = self.parent_tab._retry_single_image_generation(item_index, item_data)
                    if success:
                        success_count += 1
                        
                except Exception as e:
                    logger.error(f"重试第{item_index+1}个图像失败: {e}")
                    continue
            
            if success_count == total_count:
                self.retry_completed.emit(True, f"所有{total_count}个图像重试成功")
            elif success_count > 0:
                self.retry_completed.emit(True, f"{success_count}/{total_count}个图像重试成功")
            else:
                self.retry_completed.emit(False, "所有图像重试均失败")
                
        except Exception as e:
            logger.error(f"重试操作失败: {e}")
            self.retry_completed.emit(False, f"重试失败: {str(e)}")
    
    def cancel(self):
        """取消重试"""
        self._is_cancelled = True

class ImageGenerationFailureDialog(QDialog):
    """图像生成失败检测对话框"""
    
    def __init__(self, parent=None, failed_images=None):
        super().__init__(parent)
        self.parent_tab = parent
        self.failed_images = failed_images or []
        self.retry_thread = None
        
        self.setWindowTitle("检测到图像生成失败")
        self.setModal(True)
        self.resize(700, 600)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("检测到以下图像生成失败，请选择需要重试的项目：")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 失败统计信息
        stats_group = QGroupBox("失败统计")
        stats_layout = QVBoxLayout(stats_group)
        
        total_failed = len(self.failed_images)
        network_errors = len([item for item in self.failed_images if self._is_network_error(item.get("error", ""))])
        timeout_errors = len([item for item in self.failed_images if self._is_timeout_error(item.get("error", ""))])
        other_errors = total_failed - network_errors - timeout_errors
        
        stats_text = f"""
总失败数量: {total_failed}
网络错误: {network_errors} (HTTP 502, 连接失败等)
超时错误: {timeout_errors} (请求超时, 响应超时等)
其他错误: {other_errors}
        """.strip()
        
        stats_label = QLabel(stats_text)
        stats_layout.addWidget(stats_label)
        layout.addWidget(stats_group)
        
        # 失败列表
        list_group = QGroupBox("失败项目列表")
        list_layout = QVBoxLayout(list_group)
        
        self.failed_list = QListWidget()
        for failed_item in self.failed_images:
            item_index = failed_item.get("item_index", 0)
            item_data = failed_item.get("item_data", {})
            error = failed_item.get("error", "未知错误")
            
            # 获取镜头信息
            shot_info = item_data.get('consistency_description', item_data.get('description', ''))
            if len(shot_info) > 50:
                shot_info = shot_info[:50] + "..."
            
            item_text = f"镜头{item_index + 1}: {shot_info}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, failed_item)
            item.setCheckState(Qt.CheckState.Checked)
            
            # 添加错误信息到工具提示
            error_type = self._get_error_type(error)
            item.setToolTip(f"错误类型: {error_type}\n错误信息: {error}")
            
            self.failed_list.addItem(item)
        
        list_layout.addWidget(self.failed_list)
        
        # 全选/取消全选按钮
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(lambda: self.select_all_items(True))
        select_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(lambda: self.select_all_items(False))
        select_layout.addWidget(deselect_all_btn)
        
        select_layout.addStretch()
        list_layout.addLayout(select_layout)
        
        layout.addWidget(list_group)
        
        # 重试选项
        options_group = QGroupBox("重试选项")
        options_layout = QVBoxLayout(options_group)
        
        self.retry_with_delay_cb = QCheckBox("重试时增加延迟（减少网络压力）")
        self.retry_with_delay_cb.setChecked(True)
        options_layout.addWidget(self.retry_with_delay_cb)
        
        self.change_engine_cb = QCheckBox("尝试切换到备用引擎")
        self.change_engine_cb.setChecked(False)
        options_layout.addWidget(self.change_engine_cb)
        
        layout.addWidget(options_group)
        
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
    
    def _is_network_error(self, error):
        """判断是否为网络错误"""
        network_patterns = ['http 502', 'http 503', 'http 500', 'connection', '连接', 'network']
        return any(pattern in error.lower() for pattern in network_patterns)
    
    def _is_timeout_error(self, error):
        """判断是否为超时错误"""
        timeout_patterns = ['timeout', '超时', 'timed out']
        return any(pattern in error.lower() for pattern in timeout_patterns)
    
    def _get_error_type(self, error):
        """获取错误类型"""
        if self._is_network_error(error):
            return "网络错误"
        elif self._is_timeout_error(error):
            return "超时错误"
        else:
            return "其他错误"
    
    def select_all_items(self, checked):
        """全选或取消全选列表项"""
        for i in range(self.failed_list.count()):
            item = self.failed_list.item(i)
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
    
    def get_selected_items(self):
        """获取选中的项目"""
        selected_items = []
        for i in range(self.failed_list.count()):
            item = self.failed_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_items.append(item.data(Qt.ItemDataRole.UserRole))
        return selected_items
    
    def retry_selected_items(self):
        """重试选中的项目"""
        selected_items = self.get_selected_items()
        if selected_items:
            self.start_retry(selected_items)
        else:
            QMessageBox.warning(self, "警告", "请选择要重试的图像项目")
    
    def retry_all_items(self):
        """重试所有项目"""
        if self.failed_images:
            self.start_retry(self.failed_images)
    
    def start_retry(self, failed_items):
        """开始重试操作"""
        if not self.parent_tab:
            QMessageBox.warning(self, "错误", "无法获取父窗口引用")
            return
        
        # 显示进度对话框
        progress_dialog = QProgressDialog("正在重试图像生成...", "取消", 0, 0, self)
        progress_dialog.setModal(True)
        progress_dialog.show()
        
        # 创建重试线程
        self.retry_thread = ImageRetryThread(self.parent_tab, failed_items)
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
