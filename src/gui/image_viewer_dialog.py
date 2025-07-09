from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QWidget, QApplication
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QPixmap, QFont
import os

class ImageViewerDialog(QDialog):
    """图片放大显示对话框"""
    
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setWindowTitle("图片预览")
        self.setModal(True)
        
        # 设置窗口大小为屏幕的80%
        screen = QApplication.desktop().screenGeometry()
        self.resize(int(screen.width() * 0.8), int(screen.height() * 0.8))
        
        # 设置窗口居中
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )
        
        self.init_ui()
        
        # 安装事件过滤器来处理点击关闭
        self.installEventFilter(self)
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignCenter)
        
        # 创建图片标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        
        # 加载并显示图片
        self.load_image()
        
        # 设置图片标签为滚动区域的widget
        scroll_area.setWidget(self.image_label)
        layout.addWidget(scroll_area)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFont(QFont("微软雅黑", 12))
        close_btn.clicked.connect(self.close)
        close_btn.setFixedSize(100, 35)
        
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def load_image(self):
        """加载图片"""
        if os.path.exists(self.image_path):
            pixmap = QPixmap(self.image_path)
            if not pixmap.isNull():
                # 获取窗口大小，留出边距
                max_width = self.width() - 100
                max_height = self.height() - 150
                
                # 按比例缩放图片，但不超过窗口大小
                scaled_pixmap = pixmap.scaled(
                    max_width, max_height, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                
                self.image_label.setPixmap(scaled_pixmap)
                
                # 设置图片标签的最小大小
                self.image_label.setMinimumSize(scaled_pixmap.size())
            else:
                self.image_label.setText("无法加载图片")
                self.image_label.setStyleSheet("color: white; font-size: 16px;")
        else:
            self.image_label.setText(f"图片文件不存在:\n{self.image_path}")
            self.image_label.setStyleSheet("color: white; font-size: 16px;")
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理点击图片区域外关闭对话框"""
        if event.type() == QEvent.MouseButtonPress:
            # 检查点击位置是否在图片区域外
            if obj == self:
                # 点击在对话框上，但不在图片上时关闭
                click_pos = event.pos()
                image_rect = self.image_label.geometry()
                
                # 如果点击位置不在图片标签区域内，关闭对话框
                if not image_rect.contains(click_pos):
                    self.close()
                    return True
        
        return super().eventFilter(obj, event)
    
    def resizeEvent(self, event):
        """窗口大小改变时重新加载图片"""
        super().resizeEvent(event)
        if hasattr(self, 'image_label'):
            self.load_image()