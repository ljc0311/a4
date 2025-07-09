# -*- coding: utf-8 -*-
"""
日志对话框模块
用于显示系统日志的对话框组件
"""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton, 
    QLineEdit, QLabel, QCheckBox, QComboBox, QSplitter, QTextEdit,
    QGroupBox, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont

from src.utils.logger import logger


class LogDialog(QDialog):
    """增强版日志显示对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统日志管理")
        self.setModal(True)
        self.resize(1000, 700)
        
        # 日志文件路径
        self.log_file_path = self.get_log_file_path()
        
        # 自动刷新定时器
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh_log)
        
        self.init_ui()
        
        # 加载日志内容
        self.load_log()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        # 搜索功能
        search_group = QGroupBox("搜索过滤")
        search_layout = QHBoxLayout(search_group)
        
        search_layout.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索日志...")
        self.search_input.textChanged.connect(self.filter_log)
        search_layout.addWidget(self.search_input)
        
        # 日志级别过滤
        search_layout.addWidget(QLabel("级别:"))
        self.level_filter = QComboBox()
        self.level_filter.addItems(["全部", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_filter.currentTextChanged.connect(self.filter_log)
        search_layout.addWidget(self.level_filter)
        
        # 自动刷新
        self.auto_refresh_cb = QCheckBox("自动刷新(5秒)")
        self.auto_refresh_cb.stateChanged.connect(self.toggle_auto_refresh)
        search_layout.addWidget(self.auto_refresh_cb)
        
        toolbar_layout.addWidget(search_group)
        
        # 操作按钮
        button_group = QGroupBox("操作")
        button_layout = QHBoxLayout(button_group)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_log)
        button_layout.addWidget(self.refresh_btn)
        
        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.clicked.connect(self.clear_log)
        button_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("导出日志")
        self.export_btn.clicked.connect(self.export_log)
        button_layout.addWidget(self.export_btn)
        
        toolbar_layout.addWidget(button_group)
        
        layout.addLayout(toolbar_layout)
        
        # 分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 日志显示区域
        log_group = QGroupBox("日志内容")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        # 设置等宽字体
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        self.log_text.setFont(font)
        log_layout.addWidget(self.log_text)
        
        # 日志统计信息
        self.stats_label = QLabel("日志统计: 总行数: 0")
        log_layout.addWidget(self.stats_label)
        
        splitter.addWidget(log_group)
        
        # 过滤后的日志显示区域
        filtered_group = QGroupBox("过滤结果")
        filtered_layout = QVBoxLayout(filtered_group)
        
        self.filtered_log_text = QPlainTextEdit()
        self.filtered_log_text.setReadOnly(True)
        self.filtered_log_text.setFont(font)
        filtered_layout.addWidget(self.filtered_log_text)
        
        self.filtered_stats_label = QLabel("过滤结果: 0 条")
        filtered_layout.addWidget(self.filtered_stats_label)
        
        splitter.addWidget(filtered_group)
        
        # 设置分割比例
        splitter.setSizes([400, 300])
        layout.addWidget(splitter)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
    
    def get_log_file_path(self):
        """获取日志文件路径"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(project_root, "logs", "system.log")
    
    def load_log(self):
        """加载日志文件内容"""
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # 显示最后2000行，避免内容过多
                    if len(lines) > 2000:
                        lines = lines[-2000:]
                        content = '\n'.join(['... (显示最后2000行) ...'] + lines)
                    else:
                        content = '\n'.join(lines)
                    
                    self.log_text.setPlainText(content)
                    # 滚动到底部
                    self.log_text.moveCursor(self.log_text.textCursor().End)
                    
                    # 更新统计信息
                    total_lines = len([line for line in lines if line.strip()])
                    file_size = os.path.getsize(self.log_file_path)
                    self.stats_label.setText(
                        f"日志统计: 总行数: {total_lines}, 文件大小: {file_size/1024:.1f} KB, "
                        f"最后更新: {QDateTime.fromSecsSinceEpoch(int(os.path.getmtime(self.log_file_path))).toString('yyyy-MM-dd hh:mm:ss')}"
                    )
                    
                    # 应用当前过滤器
                    self.filter_log()
                    
            else:
                self.log_text.setPlainText("日志文件不存在。")
                self.stats_label.setText("日志统计: 文件不存在")
                
        except Exception as e:
            error_msg = f"日志读取失败: {e}"
            self.log_text.setPlainText(error_msg)
            self.stats_label.setText("日志统计: 读取失败")
            logger.error(f"加载日志文件失败: {e}")
    
    def refresh_log(self):
        """刷新日志内容"""
        self.load_log()
    
    def filter_log(self):
        """过滤日志内容"""
        try:
            search_text = self.search_input.text().lower()
            level_filter = self.level_filter.currentText()
            
            # 获取原始日志内容
            original_content = self.log_text.toPlainText()
            lines = original_content.split('\n')
            
            filtered_lines = []
            
            for line in lines:
                if not line.strip():
                    continue
                    
                # 搜索关键词过滤
                if search_text and search_text not in line.lower():
                    continue
                
                # 日志级别过滤
                if level_filter != "全部":
                    if level_filter not in line:
                        continue
                
                filtered_lines.append(line)
            
            # 显示过滤结果
            filtered_content = '\n'.join(filtered_lines)
            self.filtered_log_text.setPlainText(filtered_content)
            
            # 更新过滤统计
            self.filtered_stats_label.setText(f"过滤结果: {len(filtered_lines)} 条")
            
            # 滚动到底部
            self.filtered_log_text.moveCursor(self.filtered_log_text.textCursor().End)
            
        except Exception as e:
            logger.error(f"过滤日志失败: {e}")
    
    def toggle_auto_refresh(self, state):
        """切换自动刷新"""
        if state == Qt.Checked:
            self.refresh_timer.start(5000)  # 5秒刷新一次
        else:
            self.refresh_timer.stop()
    
    def auto_refresh_log(self):
        """自动刷新日志"""
        self.load_log()
    
    def clear_log(self):
        """清空日志文件"""
        reply = QMessageBox.question(
            self, "确认清空", 
            "确定要清空系统日志吗？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(self.log_file_path):
                    # 清空日志文件
                    with open(self.log_file_path, 'w', encoding='utf-8') as f:
                        f.write("")
                    
                    logger.info("系统日志已被用户清空")
                    QMessageBox.information(self, "成功", "日志已清空")
                    
                    # 刷新显示
                    self.load_log()
                else:
                    QMessageBox.information(self, "提示", "日志文件不存在")
                    
            except Exception as e:
                logger.error(f"清空日志失败: {e}")
                QMessageBox.warning(self, "错误", f"清空日志失败: {e}")
    
    def export_log(self):
        """导出日志文件"""
        try:
            if not os.path.exists(self.log_file_path):
                QMessageBox.information(self, "提示", "日志文件不存在")
                return
            
            # 选择保存位置
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出日志文件",
                f"system_log_{QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss')}.log",
                "日志文件 (*.log);;文本文件 (*.txt);;所有文件 (*.*)"
            )
            
            if save_path:
                # 检查是否导出过滤后的内容
                filtered_content = self.filtered_log_text.toPlainText()
                if filtered_content and filtered_content != self.log_text.toPlainText():
                    reply = QMessageBox.question(
                        self, "导出选择",
                        "是否导出过滤后的日志内容？\n\n是：导出过滤结果\n否：导出完整日志",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        # 导出过滤后的内容
                        with open(save_path, 'w', encoding='utf-8') as f:
                            f.write(filtered_content)
                    else:
                        # 复制完整日志文件
                        import shutil
                        shutil.copy2(self.log_file_path, save_path)
                else:
                    # 复制完整日志文件
                    import shutil
                    shutil.copy2(self.log_file_path, save_path)
                
                logger.info(f"日志已导出到: {save_path}")
                QMessageBox.information(self, "成功", f"日志已导出到:\n{save_path}")
                
        except Exception as e:
            logger.error(f"导出日志失败: {e}")
            QMessageBox.warning(self, "错误", f"导出日志失败: {e}")
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止自动刷新定时器
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        event.accept()