#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI工具函数
提取的公共GUI工具函数
"""

import random
from PyQt5.QtWidgets import QApplication

def get_seed_value_from_combo(seed_combo_widget) -> int:
    """从组合框获取种子值的统一实现"""
    import time
    if seed_combo_widget.currentText() == "随机":
        return random.randint(0, 2147483647)
    else:  # 固定
        # 生成一个固定的种子值，基于当前时间戳
        return int(time.time()) % 2147483647

def get_seed_value_from_input(seed_input_widget) -> int:
    """从输入框获取种子值的统一实现"""
    try:
        seed_text = seed_input_widget.text().strip()
        if seed_text == "" or seed_text == "随机":
            return random.randint(1, 2147483647)
        else:
            return int(seed_text)
    except ValueError:
        return random.randint(1, 2147483647)

def get_main_window_from_widget(widget):
    """从子组件获取主窗口的统一实现"""
    while widget.parent():
        widget = widget.parent()
        if hasattr(widget, 'tab_widget'):
            return widget
    return None

def get_main_window():
    """获取主窗口的统一实现（通过QApplication）"""
    app = QApplication.instance()
    if app:
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'isMainWindow') and widget.isMainWindow():
                return widget
    return None
