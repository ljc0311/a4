#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版主窗口
集成现代化通知系统、加载管理器、性能优化、错误处理等功能
"""

import sys
import os
import traceback
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTextEdit, QProgressBar, QMenuBar, QMenu, QAction,
    QStatusBar, QSplitter, QTabWidget, QFrame, QApplication,
    QMessageBox, QFileDialog, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QIcon, QFont, QPixmap

# 导入所有优化组件
from src.gui.notification_system import (
    show_success, show_warning, show_error, show_info, show_loading,
    clear_all as clear_notifications
)
from src.gui.loading_manager import (
    LoadingType, start_loading, update_loading, finish_loading,
    loading_manager
)
from src.gui.styles.unified_theme_system import UnifiedThemeSystem
from src.gui.modern_ui_components import MaterialButton, MaterialCard
from src.utils.performance_optimizer import (
    get_cached_image, preload_images, profile_function,
    submit_async_task, force_cleanup, get_performance_stats,
    performance_optimizer
)
from src.utils.error_handler import (
    handle_error, handle_exception_decorator, safe_execute,
    check_network, get_error_stats, error_handler
)
from src.utils.logger import logger

class EnhancedMainWindow(QMainWindow):
    """增强版主窗口
    
    展示如何集成所有用户体验和性能优化组件
    """
    
    def __init__(self):
        super().__init__()
        
        # 窗口设置
        self.setWindowTitle("AI视频生成系统 - 增强版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化组件
        self.current_loading_task = None
        self.demo_thread = None
        
        # 设置界面
        self.setup_ui()
        
        # 应用现代化样式
        self.apply_enhanced_styling()
        
        # 连接信号
        self.connect_signals()
        
        # 启动后台监控
        self.start_monitoring()
        
        logger.info("增强版主窗口初始化完成")
    
    def setup_ui(self):
        """设置用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_toolbar(main_layout)
        
        # 创建主要内容区域
        self.create_main_content(main_layout)
        
        # 创建状态栏
        self.create_status_bar()
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 主题菜单
        theme_menu = menubar.addMenu("主题")
        
        light_action = QAction("浅色主题", self)
        light_action.triggered.connect(lambda: self.switch_theme(ThemeType.LIGHT))
        theme_menu.addAction(light_action)
        
        dark_action = QAction("深色主题", self)
        dark_action.triggered.connect(lambda: self.switch_theme(ThemeType.DARK))
        theme_menu.addAction(dark_action)
        
        auto_action = QAction("自动主题", self)
        auto_action.triggered.connect(lambda: self.switch_theme(ThemeType.AUTO))
        theme_menu.addAction(auto_action)
        
        theme_menu.addSeparator()
        toggle_action = QAction("切换主题", self)
        toggle_action.triggered.connect(toggle_theme)
        theme_menu.addAction(toggle_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        stats_action = QAction("性能统计", self)
        stats_action.triggered.connect(self.show_performance_stats)
        tools_menu.addAction(stats_action)
        
        cleanup_action = QAction("清理缓存", self)
        cleanup_action.triggered.connect(self.cleanup_cache)
        tools_menu.addAction(cleanup_action)
        
        network_action = QAction("网络检测", self)
        network_action.triggered.connect(self.check_network_status)
        tools_menu.addAction(network_action)
        
        clear_errors_action = QAction("清除错误", self)
        clear_errors_action.triggered.connect(self.clear_error_history)
        tools_menu.addAction(clear_errors_action)
    
    def create_toolbar(self, parent_layout):
        """创建工具栏"""
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("toolbar")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        
        # 主要功能按钮
        self.create_demo_button = QPushButton("创建演示")
        self.create_demo_button.clicked.connect(self.start_demo_creation)
        apply_button_style(self.create_demo_button, "primary")
        toolbar_layout.addWidget(self.create_demo_button)
        
        self.show_loading_btn = QPushButton("显示加载")
        self.show_loading_btn.clicked.connect(self.demo_loading)
        apply_button_style(self.show_loading_btn, "flat")
        toolbar_layout.addWidget(self.show_loading_btn)
        
        self.test_error_btn = QPushButton("测试错误")
        self.test_error_btn.clicked.connect(self.demo_error_handling)
        apply_button_style(self.test_error_btn, "danger")
        toolbar_layout.addWidget(self.test_error_btn)
        
        self.test_notification_btn = QPushButton("测试通知")
        self.test_notification_btn.clicked.connect(self.demo_notifications)
        apply_button_style(self.test_notification_btn, "success")
        toolbar_layout.addWidget(self.test_notification_btn)
        
        toolbar_layout.addStretch()
        
        # 主题切换按钮
        self.theme_toggle_btn = QPushButton("🌙")
        self.theme_toggle_btn.clicked.connect(toggle_theme)
        self.theme_toggle_btn.setMaximumWidth(40)
        toolbar_layout.addWidget(self.theme_toggle_btn)
        
        parent_layout.addWidget(toolbar_frame)
    
    def create_main_content(self, parent_layout):
        """创建主要内容区域"""
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：控制面板
        self.create_control_panel(splitter)
        
        # 右侧：内容区域
        self.create_content_area(splitter)
        
        # 设置分割比例
        splitter.setSizes([300, 1100])
        
        parent_layout.addWidget(splitter)
    
    def create_control_panel(self, parent):
        """创建控制面板"""
        control_frame = QFrame()
        control_frame.setObjectName("control_panel")
        control_layout = QVBoxLayout(control_frame)
        
        # 标题
        title_label = QLabel("增强功能演示")
        title_label.setObjectName("panel_title")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title_label.setFont(font)
        control_layout.addWidget(title_label)
        
        # 功能按钮组
        buttons_data = [
            ("📢 通知系统", self.demo_notifications),
            ("⏳ 加载管理", self.demo_loading),
            ("❌ 错误处理", self.demo_error_handling),
            ("🎨 样式切换", toggle_theme),
            ("🚀 性能测试", self.demo_performance),
            ("📊 统计信息", self.show_performance_stats),
            ("🧹 清理缓存", self.cleanup_cache),
            ("🌐 网络检测", self.check_network_status),
        ]
        
        for text, callback in buttons_data:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            apply_button_style(btn, "flat")
            control_layout.addWidget(btn)
        
        control_layout.addStretch()
        
        parent.addWidget(control_frame)
    
    def create_content_area(self, parent):
        """创建内容区域"""
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 演示标签页
        self.create_demo_tab()
        
        # 日志标签页
        self.create_log_tab()
        
        # 统计标签页
        self.create_stats_tab()
        
        parent.addWidget(self.tab_widget)
    
    def create_demo_tab(self):
        """创建演示标签页"""
        demo_tab = QWidget()
        layout = QVBoxLayout(demo_tab)
        
        # 演示内容
        demo_label = QLabel("演示内容区域")
        demo_label.setAlignment(Qt.AlignCenter)
        demo_label.setObjectName("demo_content")
        
        # 设置样式
        demo_label.setStyleSheet(f"""
            QLabel#demo_content {{
                font-size: 24px;
                font-weight: bold;
                padding: 40px;
                border: 2px dashed var(--md-sys-color-outline-variant);
                border-radius: 10px;
                background-color: var(--md-sys-color-surface);
                color: var(--md-sys-color-on-surface-variant);
            }}
        """)
        
        layout.addWidget(demo_label)
        
        # 图片展示区域
        self.image_display = QLabel("图片将在这里显示")
        self.image_display.setAlignment(Qt.AlignCenter)
        self.image_display.setMinimumHeight(200)
        self.image_display.setStyleSheet(f"""
            QLabel {{
                border: 1px solid var(--md-sys-color-outline-variant);
                border-radius: 6px;
                background-color: var(--md-sys-color-surface-container);
            }}
        """)
        layout.addWidget(self.image_display)
        
        self.tab_widget.addTab(demo_tab, "演示")
    
    def create_log_tab(self):
        """创建日志标签页"""
        log_tab = QWidget()
        layout = QVBoxLayout(log_tab)
        
        # 日志显示区域
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumBlockCount(1000)  # 限制最大行数
        layout.addWidget(self.log_display)
        
        # 日志控制按钮
        log_controls = QHBoxLayout()
        
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.log_display.clear)
        apply_button_style(clear_log_btn, "flat")
        log_controls.addWidget(clear_log_btn)
        
        log_controls.addStretch()
        layout.addLayout(log_controls)
        
        self.tab_widget.addTab(log_tab, "日志")
    
    def create_stats_tab(self):
        """创建统计标签页"""
        stats_tab = QWidget()
        layout = QVBoxLayout(stats_tab)
        
        # 统计信息显示
        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        layout.addWidget(self.stats_display)
        
        # 刷新按钮
        refresh_stats_btn = QPushButton("刷新统计")
        refresh_stats_btn.clicked.connect(self.update_stats_display)
        apply_button_style(refresh_stats_btn, "primary")
        layout.addWidget(refresh_stats_btn)
        
        self.tab_widget.addTab(stats_tab, "统计")
    
    def create_status_bar(self):
        """创建状态栏"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        status_bar.addWidget(self.status_label)
        
        status_bar.addPermanentWidget(QLabel("  |  "))
        
        # 网络状态
        self.network_status_label = QLabel("🌐 检查中...")
        status_bar.addPermanentWidget(self.network_status_label)
        
        status_bar.addPermanentWidget(QLabel("  |  "))
        
        # 内存状态
        self.memory_status_label = QLabel("💾 正常")
        status_bar.addPermanentWidget(self.memory_status_label)
    
    def apply_enhanced_styling(self):
        """应用增强样式"""
        # 应用统一主题系统
        from src.gui.styles.unified_theme_system import get_theme_system
        theme_system = get_theme_system()
        theme_system.apply_to_widget(self)
        
        # 自定义样式补充
        additional_styles = """
            QFrame#toolbar {
                background-color: var(--md-sys-color-surface-container);
                border: 1px solid var(--md-sys-color-outline-variant);
                border-radius: 6px;
                padding: 8px;
            }
            
            QFrame#control_panel {
                background-color: var(--md-sys-color-surface);
                border: 1px solid var(--md-sys-color-outline-variant);
                border-radius: 6px;
                padding: 10px;
            }
            
            QLabel#panel_title {
                color: var(--md-sys-color-on-surface);
                padding: 10px 0px;
                border-bottom: 2px solid var(--md-sys-color-primary);
                margin-bottom: 10px;
            }
        """
        
        current_style = self.styleSheet()
        self.setStyleSheet(current_style + additional_styles)
    
    def connect_signals(self):
        """连接信号"""
        # 主题系统信号连接
        try:
            from src.gui.styles.unified_theme_system import get_theme_system
            theme_system = get_theme_system()
            if hasattr(theme_system, 'theme_changed'):
                theme_system.theme_changed.connect(self.on_theme_changed)
        except Exception as e:
            print(f"主题信号连接失败: {e}")
        
        # 加载管理器信号
        loading_manager.loading_started.connect(self.on_loading_started)
        loading_manager.loading_finished.connect(self.on_loading_finished)
        
        # 错误处理器信号
        error_handler.error_occurred.connect(self.on_error_occurred)
        
        # 性能监控信号
        performance_optimizer.memory_monitor.memory_warning.connect(self.on_memory_warning)
        performance_optimizer.memory_monitor.memory_critical.connect(self.on_memory_critical)
    
    def start_monitoring(self):
        """启动监控"""
        # 定期更新状态
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # 每5秒更新一次
        
        # 初始状态检查
        self.update_status()
    
    # 槽函数
    def on_theme_changed(self, theme_name: str):
        """主题变更响应"""
        self.log_message(f"主题已切换到: {theme_name}")
        self.status_label.setText(f"主题: {theme_name}")
        
        # 更新主题切换按钮图标
        if theme_name == "Dark":
            self.theme_toggle_btn.setText("☀️")
        else:
            self.theme_toggle_btn.setText("🌙")
        
        # 重新应用样式
        self.apply_enhanced_styling()
    
    def on_loading_started(self, task_id: str, message: str):
        """加载开始响应"""
        self.log_message(f"开始加载任务: {task_id} - {message}")
        self.status_label.setText(f"加载中: {message}")
    
    def on_loading_finished(self, task_id: str):
        """加载完成响应"""
        self.log_message(f"加载任务完成: {task_id}")
        self.status_label.setText("就绪")
    
    def on_error_occurred(self, error_info):
        """错误发生响应"""
        self.log_message(f"错误: [{error_info.category.value}] {error_info.message}")
    
    def on_memory_warning(self, usage: float):
        """内存警告响应"""
        self.memory_status_label.setText(f"💾 警告 {usage:.1%}")
        self.log_message(f"内存使用率警告: {usage:.1%}")
    
    def on_memory_critical(self, usage: float):
        """内存危险响应"""
        self.memory_status_label.setText(f"💾 危险 {usage:.1%}")
        self.log_message(f"内存使用率危险: {usage:.1%}")
    
    # 演示功能
    @handle_exception_decorator(show_to_user=True)
    def demo_notifications(self):
        """演示通知系统"""
        show_success("这是一个成功通知！")
        show_info("这是一个信息通知。")
        show_warning("这是一个警告通知。")
        show_error("这是一个错误通知。")
        
        # 显示加载通知（3秒后自动关闭）
        loading_notification = show_loading("正在处理数据...")
        QTimer.singleShot(3000, loading_notification.start_close_animation)
        
        self.log_message("演示了各种类型的通知")
    
    @handle_exception_decorator(show_to_user=True)
    def demo_loading(self):
        """演示加载管理器"""
        if self.current_loading_task:
            # 停止当前任务
            finish_loading(self.current_loading_task)
            self.current_loading_task = None
            return
        
        # 开始新的加载任务
        task_id = "demo_loading"
        self.current_loading_task = task_id
        
        # 开始加载（带进度）
        start_loading(task_id, "正在处理演示数据...", LoadingType.PROGRESS_BAR, True, self)
        
        # 模拟进度更新
        self.demo_progress_timer = QTimer()
        self.demo_progress_value = 0
        
        def update_progress():
            self.demo_progress_value += 10
            update_loading(task_id, self.demo_progress_value, f"进度: {self.demo_progress_value}%")
            
            if self.demo_progress_value >= 100:
                self.demo_progress_timer.stop()
                finish_loading(task_id)
                self.current_loading_task = None
                show_success("演示加载完成！")
        
        self.demo_progress_timer.timeout.connect(update_progress)
        self.demo_progress_timer.start(500)  # 每500ms更新一次
    
    @handle_exception_decorator(show_to_user=True)
    def demo_error_handling(self):
        """演示错误处理"""
        # 故意制造不同类型的错误
        import random
        
        error_types = [
            lambda: 1 / 0,  # ZeroDivisionError
            lambda: [][0],  # IndexError
            lambda: open("/nonexistent/file.txt"),  # FileNotFoundError
            lambda: int("not_a_number"),  # ValueError
        ]
        
        try:
            random.choice(error_types)()
        except Exception as e:
            handle_error(e, {
                'function': 'demo_error_handling',
                'context': 'This is a demonstration error'
            })
    
    @profile_function("demo_performance")
    def demo_performance(self):
        """演示性能优化"""
        # 演示图片缓存
        if hasattr(self, 'demo_images'):
            # 预加载图片
            preload_images(self.demo_images, (200, 150))
            
            # 显示缓存的图片
            if self.demo_images:
                pixmap = get_cached_image(self.demo_images[0], (200, 150))
                if pixmap:
                    self.image_display.setPixmap(pixmap)
                    self.log_message("显示了缓存的图片")
        
        # 演示异步任务
        def long_running_task():
            import time
            time.sleep(2)  # 模拟耗时操作
            return "异步任务完成！"
        
        def on_task_complete(result):
            if result:
                show_success(result)
                self.log_message("异步任务执行完成")
        
        submit_async_task(long_running_task, callback=on_task_complete)
        show_info("已提交异步任务")
    
    def start_demo_creation(self):
        """开始演示创建"""
        # 创建一个综合演示线程
        self.demo_thread = DemoCreationThread()
        self.demo_thread.progress_updated.connect(self.on_demo_progress)
        self.demo_thread.demo_completed.connect(self.on_demo_completed)
        self.demo_thread.start()
        
        # 禁用按钮
        self.create_demo_button.setEnabled(False)
        self.create_demo_button.setText("创建中...")
    
    def on_demo_progress(self, step: str, progress: int):
        """演示进度更新"""
        self.log_message(f"演示进度: {step} ({progress}%)")
        self.status_label.setText(f"演示: {step}")
    
    def on_demo_completed(self, success: bool, message: str):
        """演示完成"""
        self.create_demo_button.setEnabled(True)
        self.create_demo_button.setText("创建演示")
        
        if success:
            show_success("演示创建完成！")
        else:
            show_error(f"演示创建失败: {message}")
        
        self.log_message(f"演示完成: {message}")
    
    # 工具函数
    def switch_theme(self, theme_type: ThemeType):
        """切换主题"""
        set_theme(theme_type)
        self.log_message(f"切换到主题: {theme_type.value}")
    
    def show_performance_stats(self):
        """显示性能统计"""
        stats = get_performance_stats()
        
        stats_text = "=== 性能统计 ===\n\n"
        
        # 图片缓存统计
        if 'image_cache' in stats:
            cache_stats = stats['image_cache']
            stats_text += f"图片缓存:\n"
            stats_text += f"  内存: {cache_stats['memory']['size']} 项 ({cache_stats['memory']['memory_usage_mb']:.1f} MB)\n"
            stats_text += f"  磁盘: {cache_stats['disk']['files']} 文件 ({cache_stats['disk']['size_mb']:.1f} MB)\n"
            stats_text += f"  命中率: {cache_stats['memory']['hit_rate']:.1f}%\n\n"
        
        # 性能分析统计
        if 'profiler' in stats:
            profiler_stats = stats['profiler']
            if profiler_stats:
                stats_text += "性能分析:\n"
                for func_name, func_stats in profiler_stats.items():
                    stats_text += f"  {func_name}: {func_stats['count']}次, 平均{func_stats['average']:.3f}秒\n"
                stats_text += "\n"
        
        # 异步任务统计
        if 'async_tasks' in stats:
            task_stats = stats['async_tasks']
            stats_text += f"异步任务:\n"
            stats_text += f"  活跃: {task_stats['active']}, 排队: {task_stats['queued']}\n"
            stats_text += f"  最大工作线程: {task_stats['max_workers']}\n\n"
        
        # 错误统计
        error_stats = get_error_stats()
        if error_stats:
            stats_text += f"错误统计:\n"
            stats_text += f"  总错误数: {error_stats.get('total_errors', 0)}\n"
            if 'by_category' in error_stats:
                for category, count in error_stats['by_category'].items():
                    stats_text += f"  {category}: {count}\n"
        
        self.stats_display.setText(stats_text)
        self.tab_widget.setCurrentIndex(2)  # 切换到统计标签页
    
    def update_stats_display(self):
        """更新统计显示"""
        self.show_performance_stats()
        self.log_message("统计信息已刷新")
    
    def cleanup_cache(self):
        """清理缓存"""
        force_cleanup()
        clear_notifications()
        show_success("缓存清理完成")
        self.log_message("执行了缓存清理")
    
    def check_network_status(self):
        """检查网络状态"""
        is_connected = check_network()
        if is_connected:
            self.network_status_label.setText("🌐 已连接")
            show_success("网络连接正常")
        else:
            self.network_status_label.setText("🌐 断开")
            show_warning("网络连接异常")
        
        self.log_message(f"网络状态: {'连接正常' if is_connected else '连接异常'}")
    
    def clear_error_history(self):
        """清除错误历史"""
        from src.utils.error_handler import clear_errors
        clear_errors()
        show_info("错误历史已清除")
        self.log_message("错误历史已清除")
    
    def update_status(self):
        """更新状态"""
        # 更新网络状态
        is_connected = check_network()
        if is_connected:
            self.network_status_label.setText("🌐 已连接")
        else:
            self.network_status_label.setText("🌐 断开")
        
        # 更新内存状态（如果有内存监控）
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent / 100.0
            if memory_percent > 0.9:
                self.memory_status_label.setText(f"💾 危险 {memory_percent:.1%}")
            elif memory_percent > 0.8:
                self.memory_status_label.setText(f"💾 警告 {memory_percent:.1%}")
            else:
                self.memory_status_label.setText(f"💾 正常 {memory_percent:.1%}")
        except ImportError:
            self.memory_status_label.setText("💾 未知")
    
    def log_message(self, message: str):
        """记录消息到日志显示"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.log_display.append(formatted_message)
        logger.info(message)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 清理资源
        if self.current_loading_task:
            finish_loading(self.current_loading_task)
        
        if hasattr(self, 'demo_thread') and self.demo_thread:
            self.demo_thread.wait(3000)  # 等待线程结束
        
        # 清理通知
        clear_notifications()
        
        logger.info("增强版主窗口已关闭")
        event.accept()

class DemoCreationThread(QThread):
    """演示创建线程"""
    
    progress_updated = pyqtSignal(str, int)
    demo_completed = pyqtSignal(bool, str)
    
    def run(self):
        """运行演示创建"""
        try:
            steps = [
                ("初始化演示环境", 20),
                ("加载演示数据", 40),
                ("生成演示内容", 60),
                ("应用优化效果", 80),
                ("完成演示创建", 100),
            ]
            
            for step, progress in steps:
                self.progress_updated.emit(step, progress)
                self.msleep(1000)  # 模拟耗时操作
            
            self.demo_completed.emit(True, "演示创建成功")
            
        except Exception as e:
            self.demo_completed.emit(False, str(e))

# 测试运行
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 创建增强版主窗口
    window = EnhancedMainWindow()
    window.show()
    
    sys.exit(app.exec_())