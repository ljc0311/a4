"""
配音驱动工作流程指导界面
帮助用户理解和使用新的配音驱动工作流程
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QScrollArea, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QPen

logger = logging.getLogger(__name__)

class WorkflowStepWidget(QFrame):
    """工作流程步骤组件"""
    
    step_clicked = pyqtSignal(int)  # 步骤点击信号
    
    def __init__(self, step_number, title, description, status="pending", parent=None):
        super().__init__(parent)
        self.step_number = step_number
        self.title = title
        self.description = description
        self.status = status  # pending, active, completed
        
        self.setup_ui()
        self.update_style()
    
    def setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # 步骤编号圆圈
        self.step_circle = QLabel(str(self.step_number))
        self.step_circle.setFixedSize(40, 40)
        self.step_circle.setAlignment(Qt.AlignCenter)
        self.step_circle.setStyleSheet("""
            QLabel {
                border-radius: 20px;
                font-weight: bold;
                font-size: 16px;
            }
        """)
        layout.addWidget(self.step_circle)
        
        # 步骤内容
        content_layout = QVBoxLayout()
        
        # 标题
        self.title_label = QLabel(self.title)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        content_layout.addWidget(self.title_label)
        
        # 描述
        self.desc_label = QLabel(self.description)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #666; margin-top: 5px;")
        content_layout.addWidget(self.desc_label)
        
        layout.addLayout(content_layout, 1)
        
        # 操作按钮
        self.action_btn = QPushButton("开始")
        self.action_btn.setFixedSize(80, 30)
        self.action_btn.clicked.connect(lambda: self.step_clicked.emit(self.step_number))
        layout.addWidget(self.action_btn)
        
        # 设置鼠标悬停效果
        self.setMouseTracking(True)
    
    def update_style(self):
        """更新样式"""
        if self.status == "completed":
            # 已完成
            self.step_circle.setStyleSheet("""
                QLabel {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 16px;
                }
            """)
            self.action_btn.setText("✓ 完成")
            self.action_btn.setEnabled(False)
            self.setStyleSheet("""
                QFrame {
                    background-color: #f8fff8;
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                }
            """)
        elif self.status == "active":
            # 当前活动
            self.step_circle.setStyleSheet("""
                QLabel {
                    background-color: #2196F3;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 16px;
                }
            """)
            self.action_btn.setText("进入")
            self.action_btn.setEnabled(True)
            self.setStyleSheet("""
                QFrame {
                    background-color: #f0f8ff;
                    border: 2px solid #2196F3;
                    border-radius: 8px;
                }
            """)
        else:
            # 待处理
            self.step_circle.setStyleSheet("""
                QLabel {
                    background-color: #e0e0e0;
                    color: #666;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 16px;
                }
            """)
            self.action_btn.setText("等待")
            self.action_btn.setEnabled(False)
            self.setStyleSheet("""
                QFrame {
                    background-color: #fafafa;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }
            """)
    
    def set_status(self, status):
        """设置状态"""
        self.status = status
        self.update_style()

class WorkflowGuideWidget(QWidget):
    """配音驱动工作流程指导界面"""
    
    switch_to_tab = pyqtSignal(str)  # 切换标签页信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_step = 1
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("🎭 配音驱动工作流程指南")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2196F3; margin-bottom: 20px;")
        layout.addWidget(title_label)
        
        # 工作流程说明
        intro_group = QGroupBox("💡 新工作流程优势")
        intro_layout = QVBoxLayout(intro_group)
        
        intro_text = QLabel("""
<div style='line-height: 1.6;'>
<b>🎯 配音优先工作流程的核心优势：</b><br><br>
• <b>完美内容匹配</b>：图像内容与配音叙述完全一致<br>
• <b>智能时长计算</b>：根据配音时长自动确定图像数量<br>
• <b>自然节奏感</b>：视觉节奏与听觉节奏完美同步<br>
• <b>双模式生图</b>：传统分镜生图 + 配音时长生图<br>
• <b>高效制作流程</b>：配音完成后自动切换到图像生成
</div>
        """)
        intro_text.setWordWrap(True)
        intro_text.setStyleSheet("""
            QLabel {
                background-color: #f0f8ff;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #d0e7ff;
            }
        """)
        intro_layout.addWidget(intro_text)
        layout.addWidget(intro_group)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 工作流程步骤
        steps_widget = QWidget()
        steps_layout = QVBoxLayout(steps_widget)
        
        # 🔧 优化：定义配音优先工作流程步骤
        self.workflow_steps = [
            {
                "title": "📝 文本创作",
                "description": "使用AI创作故事或改写现有文本，为后续分镜和配音提供高质量的文本内容。",
                "tab_name": "📝 文本创作"
            },
            {
                "title": "🎬 五阶段分镜",
                "description": "基于文本内容生成详细的五阶段分镜脚本，为配音提供结构化的内容基础。",
                "tab_name": "🎬 五阶段分镜"
            },
            {
                "title": "🎵 AI配音生成",
                "description": "基于分镜脚本生成配音，这是配音优先工作流程的核心步骤。配音完成后将驱动后续的图像生成。",
                "tab_name": "🎵 AI配音生成"
            },
            {
                "title": "🖼️ 图像生成",
                "description": "基于配音内容和时长生成完全匹配的图像。支持传统分镜生图和配音时长生图两种模式。",
                "tab_name": "🖼️ 图像生成"
            },
            {
                "title": "🎨 一致性控制",
                "description": "优化已生成的图像，管理角色和场景的一致性，确保视觉风格统一。",
                "tab_name": "🎨 一致性控制"
            },
            {
                "title": "🎬 视频合成",
                "description": "将配音、图像和音效合成为最终的视频作品。",
                "tab_name": "🎬 视频合成"
            }
        ]
        
        # 创建步骤组件
        self.step_widgets = []
        for i, step_info in enumerate(self.workflow_steps, 1):
            step_widget = WorkflowStepWidget(
                i, 
                step_info["title"], 
                step_info["description"],
                "active" if i == 1 else "pending"
            )
            step_widget.step_clicked.connect(self.on_step_clicked)
            self.step_widgets.append(step_widget)
            steps_layout.addWidget(step_widget)
            
            # 添加连接线（除了最后一个步骤）
            if i < len(self.workflow_steps):
                line = QFrame()
                line.setFrameShape(QFrame.VLine)
                line.setFrameShadow(QFrame.Sunken)
                line.setFixedHeight(20)
                line.setStyleSheet("color: #e0e0e0; margin-left: 35px;")
                steps_layout.addWidget(line)
        
        scroll_area.setWidget(steps_widget)
        layout.addWidget(scroll_area)
        
        # 底部提示
        tip_label = QLabel("💡 提示：按照步骤顺序操作，每完成一步后会自动激活下一步")
        tip_label.setStyleSheet("""
            QLabel {
                background-color: #fff3cd;
                color: #856404;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #ffeaa7;
                margin-top: 10px;
            }
        """)
        tip_label.setWordWrap(True)
        layout.addWidget(tip_label)
    
    def on_step_clicked(self, step_number):
        """步骤点击处理"""
        try:
            if step_number <= len(self.workflow_steps):
                step_info = self.workflow_steps[step_number - 1]
                tab_name = step_info["tab_name"]
                
                # 发送切换标签页信号
                self.switch_to_tab.emit(tab_name)
                
                logger.info(f"用户点击工作流程步骤 {step_number}: {step_info['title']}")
                
        except Exception as e:
            logger.error(f"处理步骤点击失败: {e}")
    
    def update_step_status(self, step_number, status):
        """更新步骤状态"""
        try:
            if 1 <= step_number <= len(self.step_widgets):
                self.step_widgets[step_number - 1].set_status(status)
                
                # 如果步骤完成，激活下一步
                if status == "completed" and step_number < len(self.step_widgets):
                    self.step_widgets[step_number].set_status("active")
                    self.current_step = step_number + 1
                
                logger.info(f"步骤 {step_number} 状态更新为: {status}")
                
        except Exception as e:
            logger.error(f"更新步骤状态失败: {e}")
    
    def reset_workflow(self):
        """重置工作流程"""
        try:
            for i, widget in enumerate(self.step_widgets):
                if i == 0:
                    widget.set_status("active")
                else:
                    widget.set_status("pending")
            
            self.current_step = 1
            logger.info("工作流程已重置")
            
        except Exception as e:
            logger.error(f"重置工作流程失败: {e}")
    
    def get_current_step(self):
        """获取当前步骤"""
        return self.current_step
