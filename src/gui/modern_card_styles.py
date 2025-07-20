#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化卡片式界面样式定义
专为Qt优化的样式表，避免不支持的CSS属性
"""

def get_modern_card_styles():
    """获取现代化卡片式界面样式"""
    return """
    /* 主窗口样式 */
    QMainWindow {
        background-color: #F5F5F5;
        color: #333333;
    }
    
    /* 现代化按钮样式 */
    QPushButton[class="modern-card-button"] {
        background-color: #2196F3;
        color: white;
        border: none;
        border-radius: 25px;
        padding: 12px 20px;
        font-weight: 500;
        font-size: 10pt;
        min-height: 26px;
        min-width: 120px;
    }
    
    QPushButton[class="modern-card-button"]:hover {
        background-color: #1976D2;
    }
    
    QPushButton[class="modern-card-button"]:pressed {
        background-color: #0D47A1;
    }
    
    QPushButton[class="modern-card-button"]:checked {
        background-color: #1565C0;
        border: 2px solid #0D47A1;
    }
    
    /* 现代化卡片样式 */
    QFrame[class="modern-card"] {
        background-color: white;
        border: 1px solid #E0E0E0;
        border-radius: 12px;
        margin: 4px;
        padding: 8px;
    }
    
    QFrame[class="modern-card"]:hover {
        border-color: #BDBDBD;
    }
    
    /* 工具栏按钮样式 */
    QPushButton[class="toolbar-button"] {
        border: none;
        border-radius: 18px;
        padding: 8px 16px;
        font-weight: 500;
        font-size: 9pt;
        min-height: 20px;
        color: white;
    }
    
    QPushButton[class="toolbar-button-green"] {
        background-color: #4CAF50;
    }
    
    QPushButton[class="toolbar-button-green"]:hover {
        background-color: #45A049;
    }
    
    QPushButton[class="toolbar-button-blue"] {
        background-color: #2196F3;
    }
    
    QPushButton[class="toolbar-button-blue"]:hover {
        background-color: #1976D2;
    }
    
    QPushButton[class="toolbar-button-orange"] {
        background-color: #FF9800;
    }
    
    QPushButton[class="toolbar-button-orange"]:hover {
        background-color: #F57C00;
    }
    
    QPushButton[class="toolbar-button-purple"] {
        background-color: #9C27B0;
    }
    
    QPushButton[class="toolbar-button-purple"]:hover {
        background-color: #7B1FA2;
    }
    
    /* 快捷操作按钮样式 */
    QPushButton[class="quick-action-button"] {
        background-color: #E3F2FD;
        color: #1976D2;
        border: 2px solid #BBDEFB;
        border-radius: 12px;
        padding: 16px;
        font-weight: 500;
        font-size: 10pt;
        min-height: 28px;
    }
    
    QPushButton[class="quick-action-button"]:hover {
        background-color: #BBDEFB;
        border-color: #90CAF9;
    }
    
    QPushButton[class="quick-action-button"]:pressed {
        background-color: #90CAF9;
    }
    
    /* 文件按钮样式 */
    QPushButton[class="file-button"] {
        border: 1px solid rgba(76, 175, 80, 0.4);
        border-radius: 8px;
        padding: 8px 12px;
        text-align: left;
        font-size: 9pt;
        min-height: 24px;
    }
    
    QPushButton[class="file-button-green"] {
        background-color: rgba(76, 175, 80, 0.2);
        color: #4CAF50;
    }
    
    QPushButton[class="file-button-green"]:hover {
        background-color: rgba(76, 175, 80, 0.3);
    }
    
    QPushButton[class="file-button-blue"] {
        background-color: rgba(33, 150, 243, 0.2);
        color: #2196F3;
        border-color: rgba(33, 150, 243, 0.4);
    }
    
    QPushButton[class="file-button-blue"]:hover {
        background-color: rgba(33, 150, 243, 0.3);
    }
    
    QPushButton[class="file-button-orange"] {
        background-color: rgba(255, 152, 0, 0.2);
        color: #FF9800;
        border-color: rgba(255, 152, 0, 0.4);
    }
    
    QPushButton[class="file-button-orange"]:hover {
        background-color: rgba(255, 152, 0, 0.3);
    }
    
    QPushButton[class="file-button-purple"] {
        background-color: rgba(156, 39, 176, 0.2);
        color: #9C27B0;
        border-color: rgba(156, 39, 176, 0.4);
    }
    
    QPushButton[class="file-button-purple"]:hover {
        background-color: rgba(156, 39, 176, 0.3);
    }
    
    /* 进度条样式 */
    QProgressBar[class="modern-progress"] {
        border: none;
        border-radius: 3px;
        background-color: #E3F2FD;
        max-height: 6px;
    }
    
    QProgressBar[class="modern-progress"]::chunk {
        background-color: #2196F3;
        border-radius: 3px;
    }
    
    /* 标签样式 */
    QLabel[class="card-title"] {
        color: #333333;
        font-weight: bold;
        font-size: 12pt;
        margin-bottom: 8px;
    }
    
    QLabel[class="nav-title"] {
        color: #333333;
        font-weight: bold;
        font-size: 12pt;
        margin-bottom: 8px;
    }
    
    QLabel[class="info-title"] {
        color: #333333;
        font-weight: bold;
        font-size: 12pt;
        margin-bottom: 8px;
    }
    
    QLabel[class="help-item"] {
        color: #555555;
        padding: 4px 0px;
        font-size: 9pt;
    }
    
    QLabel[class="status-label"] {
        font-size: 9pt;
    }
    
    QLabel[class="status-indicator"] {
        font-size: 16px;
    }
    
    QLabel[class="progress-name"] {
        font-size: 9pt;
    }
    
    QLabel[class="progress-value"] {
        font-size: 9pt;
        font-weight: bold;
        color: #2196F3;
    }
    
    QLabel[class="version-label"] {
        color: #666666;
        font-size: 8pt;
    }
    
    /* 分割器样式 */
    QSplitter::handle {
        background-color: #E0E0E0;
        width: 2px;
        height: 2px;
    }
    
    QSplitter::handle:hover {
        background-color: #BDBDBD;
    }
    
    /* 滚动条样式 */
    QScrollBar:vertical {
        background-color: #F5F5F5;
        width: 12px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #BDBDBD;
        border-radius: 6px;
        min-height: 20px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #9E9E9E;
    }
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
    """


def apply_modern_card_styles(widget):
    """应用现代化卡片样式到控件"""
    try:
        styles = get_modern_card_styles()
        widget.setStyleSheet(styles)
    except Exception as e:
        print(f"应用样式失败: {e}")
