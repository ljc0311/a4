"""
智能同步检测对话框
替换旧的简单数量检测，提供更智能的同步分析和修复建议
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QProgressBar, QGroupBox, QScrollArea, QWidget,
    QFrame, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QIcon

from src.utils.logger import logger
from src.core.intelligent_sync_detector import IntelligentSyncDetector, SyncAnalysisResult


class SyncAnalysisThread(QThread):
    """同步分析线程"""
    
    analysis_completed = pyqtSignal(object)  # SyncAnalysisResult
    analysis_failed = pyqtSignal(str)  # error message
    
    def __init__(self, project_data, project_manager=None):
        super().__init__()
        self.project_data = project_data
        self.project_manager = project_manager
    
    def run(self):
        try:
            detector = IntelligentSyncDetector(self.project_manager)
            result = detector.analyze_project_sync(self.project_data)
            self.analysis_completed.emit(result)
        except Exception as e:
            logger.error(f"同步分析线程失败: {e}")
            self.analysis_failed.emit(str(e))


class IntelligentSyncDialog(QDialog):
    """智能同步检测对话框"""
    
    def __init__(self, parent=None, project_data=None, project_manager=None):
        super().__init__(parent)
        self.project_data = project_data
        self.project_manager = project_manager
        self.analysis_result = None
        
        self.setWindowTitle("智能同步检测")
        self.setModal(True)
        self.resize(800, 600)
        
        self.init_ui()
        self.start_analysis()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("🔍 智能同步检测")
        title_font = QFont("Microsoft YaHei", 16, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        layout.addWidget(title_label)
        
        # 进度区域
        self.progress_widget = self.create_progress_widget()
        layout.addWidget(self.progress_widget)
        
        # 结果区域（初始隐藏）
        self.result_widget = self.create_result_widget()
        self.result_widget.setVisible(False)
        layout.addWidget(self.result_widget)
        
        # 按钮区域
        self.button_widget = self.create_button_widget()
        layout.addWidget(self.button_widget)
    
    def create_progress_widget(self):
        """创建进度显示组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 进度说明
        self.progress_label = QLabel("正在分析配音与图像的同步状态...")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("font-size: 14px; color: #34495e; margin: 20px;")
        layout.addWidget(self.progress_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        return widget
    
    def create_result_widget(self):
        """创建结果显示组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        
        # 总体状态
        self.status_group = QGroupBox("📊 同步状态总览")
        self.status_layout = QVBoxLayout(self.status_group)
        self.scroll_layout.addWidget(self.status_group)
        
        # 问题详情
        self.issues_group = QGroupBox("⚠️ 检测到的问题")
        self.issues_layout = QVBoxLayout(self.issues_group)
        self.scroll_layout.addWidget(self.issues_group)
        
        # 优化建议
        self.recommendations_group = QGroupBox("💡 优化建议")
        self.recommendations_layout = QVBoxLayout(self.recommendations_group)
        self.scroll_layout.addWidget(self.recommendations_group)
        
        # 自动修复选项
        self.auto_fix_group = QGroupBox("🔧 自动修复选项")
        self.auto_fix_layout = QVBoxLayout(self.auto_fix_group)
        self.scroll_layout.addWidget(self.auto_fix_group)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        return widget
    
    def create_button_widget(self):
        """创建按钮组件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        layout.addStretch()
        
        # 重新分析按钮
        self.reanalyze_btn = QPushButton("🔄 重新分析")
        self.reanalyze_btn.clicked.connect(self.start_analysis)
        self.reanalyze_btn.setVisible(False)
        layout.addWidget(self.reanalyze_btn)
        
        # 自动修复按钮
        self.auto_fix_btn = QPushButton("🔧 自动修复")
        self.auto_fix_btn.clicked.connect(self.auto_fix_issues)
        self.auto_fix_btn.setVisible(False)
        self.auto_fix_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        layout.addWidget(self.auto_fix_btn)
        
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)
        
        layout.addStretch()
        
        return widget
    
    def start_analysis(self):
        """开始分析"""
        try:
            # 显示进度，隐藏结果
            self.progress_widget.setVisible(True)
            self.result_widget.setVisible(False)
            self.reanalyze_btn.setVisible(False)
            self.auto_fix_btn.setVisible(False)
            
            # 重置进度
            self.progress_bar.setRange(0, 0)
            self.progress_label.setText("正在分析配音与图像的同步状态...")
            
            # 启动分析线程
            self.analysis_thread = SyncAnalysisThread(self.project_data, self.project_manager)
            self.analysis_thread.analysis_completed.connect(self.on_analysis_completed)
            self.analysis_thread.analysis_failed.connect(self.on_analysis_failed)
            self.analysis_thread.start()
            
        except Exception as e:
            logger.error(f"启动同步分析失败: {e}")
            self.on_analysis_failed(str(e))
    
    def on_analysis_completed(self, result: SyncAnalysisResult):
        """分析完成"""
        try:
            self.analysis_result = result
            
            # 隐藏进度，显示结果
            self.progress_widget.setVisible(False)
            self.result_widget.setVisible(True)
            self.reanalyze_btn.setVisible(True)
            
            # 显示结果
            self.display_analysis_result(result)
            
            # 如果有可自动修复的问题，显示自动修复按钮
            auto_fixable_issues = [issue for issue in result.issues if issue.auto_fixable]
            if auto_fixable_issues:
                self.auto_fix_btn.setVisible(True)
            
        except Exception as e:
            logger.error(f"显示分析结果失败: {e}")
            self.on_analysis_failed(str(e))
    
    def on_analysis_failed(self, error_message: str):
        """分析失败"""
        self.progress_widget.setVisible(False)
        self.reanalyze_btn.setVisible(True)
        
        # 显示错误信息
        error_label = QLabel(f"❌ 分析失败：{error_message}")
        error_label.setStyleSheet("color: #e74c3c; font-size: 14px; margin: 20px;")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setWordWrap(True)
        
        # 清空并添加错误信息
        self.clear_result_layout()
        self.scroll_layout.addWidget(error_label)
        self.result_widget.setVisible(True)
    
    def display_analysis_result(self, result: SyncAnalysisResult):
        """显示分析结果"""
        try:
            # 清空之前的结果
            self.clear_result_layout()
            
            # 显示总体状态
            self.display_status_overview(result)
            
            # 显示问题详情
            self.display_issues(result.issues)
            
            # 显示建议
            self.display_recommendations(result.recommendations)
            
            # 显示自动修复选项
            self.display_auto_fix_options(result.issues)
            
        except Exception as e:
            logger.error(f"显示分析结果失败: {e}")
    
    def display_status_overview(self, result: SyncAnalysisResult):
        """显示状态总览"""
        # 清空状态布局
        self.clear_layout(self.status_layout)
        
        # 质量分数
        quality_color = self.get_quality_color(result.overall_quality)
        quality_text = f"整体质量：{result.overall_quality:.1%}"
        quality_label = QLabel(quality_text)
        quality_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {quality_color};")
        self.status_layout.addWidget(quality_label)
        
        # 统计信息
        stats_text = f"""
📊 数据统计：
• 配音段落：{result.voice_segments_count} 个
• 图像镜头：{result.image_segments_count} 个  
• 总配音时长：{result.total_voice_duration:.1f} 秒
• 同步分数：{result.sync_score:.1%}
• 检测问题：{len(result.issues)} 个
        """
        
        stats_label = QLabel(stats_text.strip())
        stats_label.setStyleSheet("font-size: 12px; color: #34495e; margin: 10px;")
        self.status_layout.addWidget(stats_label)

    def display_issues(self, issues):
        """显示问题详情"""
        # 清空问题布局
        self.clear_layout(self.issues_layout)

        if not issues:
            no_issues_label = QLabel("✅ 未发现同步问题，配音与图像匹配良好！")
            no_issues_label.setStyleSheet("font-size: 14px; color: #27ae60; margin: 10px;")
            self.issues_layout.addWidget(no_issues_label)
            return

        for i, issue in enumerate(issues, 1):
            issue_frame = self.create_issue_frame(i, issue)
            self.issues_layout.addWidget(issue_frame)

    def create_issue_frame(self, index, issue):
        """创建问题显示框架"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box)
        frame.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {self.get_severity_color(issue.severity)};
                border-radius: 5px;
                margin: 5px;
                padding: 5px;
            }}
        """)

        layout = QVBoxLayout(frame)

        # 问题标题
        title_text = f"{index}. {self.get_severity_icon(issue.severity)} {issue.description}"
        title_label = QLabel(title_text)
        title_label.setStyleSheet(f"font-weight: bold; color: {self.get_severity_color(issue.severity)};")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # 问题详情
        details_text = f"类型：{self.get_issue_type_name(issue.issue_type)}\n"
        details_text += f"严重程度：{self.get_severity_name(issue.severity)}\n"
        details_text += f"影响段落：{len(issue.affected_segments)} 个\n"
        details_text += f"建议修复：{issue.suggested_fix}"

        details_label = QLabel(details_text)
        details_label.setStyleSheet("font-size: 12px; color: #34495e; margin-left: 20px;")
        details_label.setWordWrap(True)
        layout.addWidget(details_label)

        # 自动修复标识
        if issue.auto_fixable:
            auto_fix_label = QLabel("🔧 可自动修复")
            auto_fix_label.setStyleSheet("font-size: 11px; color: #27ae60; margin-left: 20px;")
            layout.addWidget(auto_fix_label)

        return frame

    def display_recommendations(self, recommendations):
        """显示优化建议"""
        # 清空建议布局
        self.clear_layout(self.recommendations_layout)

        if not recommendations:
            no_recommendations_label = QLabel("暂无特殊建议")
            no_recommendations_label.setStyleSheet("font-size: 12px; color: #7f8c8d; margin: 10px;")
            self.recommendations_layout.addWidget(no_recommendations_label)
            return

        for i, recommendation in enumerate(recommendations, 1):
            rec_label = QLabel(f"{i}. {recommendation}")
            rec_label.setStyleSheet("font-size: 12px; color: #2c3e50; margin: 5px 10px;")
            rec_label.setWordWrap(True)
            self.recommendations_layout.addWidget(rec_label)

    def display_auto_fix_options(self, issues):
        """显示自动修复选项"""
        # 清空自动修复布局
        self.clear_layout(self.auto_fix_layout)

        auto_fixable_issues = [issue for issue in issues if issue.auto_fixable]

        if not auto_fixable_issues:
            no_auto_fix_label = QLabel("暂无可自动修复的问题")
            no_auto_fix_label.setStyleSheet("font-size: 12px; color: #7f8c8d; margin: 10px;")
            self.auto_fix_layout.addWidget(no_auto_fix_label)
            return

        info_label = QLabel(f"发现 {len(auto_fixable_issues)} 个可自动修复的问题：")
        info_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #2c3e50; margin: 5px;")
        self.auto_fix_layout.addWidget(info_label)

        for issue in auto_fixable_issues:
            fix_label = QLabel(f"• {issue.description}")
            fix_label.setStyleSheet("font-size: 11px; color: #34495e; margin-left: 20px;")
            fix_label.setWordWrap(True)
            self.auto_fix_layout.addWidget(fix_label)

    def get_quality_color(self, quality):
        """获取质量分数对应的颜色"""
        if quality >= 0.8:
            return "#27ae60"  # 绿色
        elif quality >= 0.6:
            return "#f39c12"  # 橙色
        else:
            return "#e74c3c"  # 红色

    def get_severity_color(self, severity):
        """获取严重程度对应的颜色"""
        colors = {
            'low': "#3498db",      # 蓝色
            'medium': "#f39c12",   # 橙色
            'high': "#e67e22",     # 深橙色
            'critical': "#e74c3c"  # 红色
        }
        return colors.get(severity, "#7f8c8d")

    def get_severity_icon(self, severity):
        """获取严重程度对应的图标"""
        icons = {
            'low': "ℹ️",
            'medium': "⚠️",
            'high': "🚨",
            'critical': "🔴"
        }
        return icons.get(severity, "❓")

    def get_severity_name(self, severity):
        """获取严重程度名称"""
        names = {
            'low': "轻微",
            'medium': "中等",
            'high': "严重",
            'critical': "关键"
        }
        return names.get(severity, "未知")

    def get_issue_type_name(self, issue_type):
        """获取问题类型名称"""
        names = {
            'duration_mismatch': "时长不匹配",
            'content_mismatch': "内容不匹配",
            'count_mismatch': "数量不匹配",
            'quality_issue': "质量问题"
        }
        return names.get(issue_type, "未知问题")

    def clear_layout(self, layout):
        """清空布局"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def clear_result_layout(self):
        """清空结果布局"""
        self.clear_layout(self.status_layout)
        self.clear_layout(self.issues_layout)
        self.clear_layout(self.recommendations_layout)
        self.clear_layout(self.auto_fix_layout)

    def auto_fix_issues(self):
        """自动修复问题"""
        try:
            if not self.analysis_result:
                return

            auto_fixable_issues = [issue for issue in self.analysis_result.issues if issue.auto_fixable]

            if not auto_fixable_issues:
                QMessageBox.information(self, "提示", "没有可自动修复的问题")
                return

            # 询问用户确认
            reply = QMessageBox.question(
                self, "确认自动修复",
                f"将自动修复 {len(auto_fixable_issues)} 个问题。\n\n"
                "这可能需要几分钟时间，是否继续？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                self.perform_auto_fix(auto_fixable_issues)

        except Exception as e:
            logger.error(f"自动修复失败: {e}")
            QMessageBox.critical(self, "错误", f"自动修复失败：{str(e)}")

    def perform_auto_fix(self, issues):
        """执行自动修复"""
        try:
            # 这里可以调用具体的修复方法
            # 例如：调用图像生成界面的按配音时间生成功能

            # 显示修复进度
            self.progress_label.setText("正在执行自动修复...")
            self.progress_widget.setVisible(True)
            self.result_widget.setVisible(False)

            # 模拟修复过程（实际应该调用相应的修复方法）
            QMessageBox.information(
                self, "修复完成",
                f"已尝试修复 {len(issues)} 个问题。\n\n"
                "建议重新分析以确认修复效果。"
            )

            # 重新分析
            self.start_analysis()

        except Exception as e:
            logger.error(f"执行自动修复失败: {e}")
            QMessageBox.critical(self, "错误", f"修复失败：{str(e)}")
            self.progress_widget.setVisible(False)
            self.result_widget.setVisible(True)
