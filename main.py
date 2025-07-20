#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI视频生成器主程序
直接启动主窗口，无需登录验证
"""

import sys
import os
import atexit
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

# --- 优化: 将logger导入移至全局范围 ---
try:
    from src.utils.logger import logger
except ImportError:
    # 如果日志记录器无法导入，则创建一个备用记录器
    import logging
    import traceback
    logger = logging.getLogger("fallback_logger")
    logging.basicConfig(level=logging.INFO)

def exit_handler():
    """
    程序退出处理函数
    """
    logger.info("程序正在退出...")

if __name__ == "__main__":
    # 注册退出处理函数
    atexit.register(exit_handler)
    
    # 设置Qt属性以支持QtWebEngine
    try:
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)  # type: ignore
    except AttributeError:
        # 如果属性不存在，忽略错误
        pass
    
    app = QApplication(sys.argv)
    
    try:
        logger.info("🚀 正在启动现代化AI视频生成器...")

        # 初始化服务管理器（全局单例）
        from src.core.service_manager import ServiceManager
        from src.utils.config_manager import ConfigManager

        logger.info("⚙️ 正在初始化配置管理器...")
        config_manager = ConfigManager()
        logger.info("✅ 配置管理器初始化完成")

        logger.info("🔧 正在初始化服务管理器...")
        service_manager = ServiceManager(config_manager)
        logger.info("✅ 服务管理器初始化完成")

        # 导入并创建现代化卡片式主窗口
        from src.gui.modern_card_main_window import ModernCardMainWindow
        from src.core.app_initializer import AsyncInitializer

        logger.info("🎨 正在设置应用程序样式...")
        # 设置应用程序样式
        app.setStyle("Fusion")

        logger.info("🖥️ 正在创建主窗口...")
        main_window = ModernCardMainWindow()
        main_window.show()
        logger.info("✅ 现代化界面已启动")

        # --- 非阻塞式异步初始化 ---
        logger.info("🚀 启动后台异步初始化...")
        initializer = AsyncInitializer(service_manager)
        
        # 连接信号，以便在初始化完成时收到通知
        def on_init_finished(success, message):
            logger.info(f"🎉 异步初始化完成. 状态: {'成功' if success else '失败'}. 消息: {message}")
            # 可以在这里更新UI，例如状态栏
            status_message = f"服务初始化完成: {message}" if success else f"服务初始化失败: {message}"
            main_window.statusBar().showMessage(status_message, 10000) # 显示10秒

        initializer.initialization_finished.connect(on_init_finished)
        
        # 启动初始化
        initializer.run_initialization()
        # --------------------------

        logger.info("🔄 启动事件循环...")
        # 启动事件循环
        logger.info("--- Main thread entering Qt event loop ---")
        exit_code = app.exec_()
        logger.info(f"--- Qt event loop finished with exit code: {exit_code} ---")
        sys.exit(exit_code)
    except ImportError as e:
        tb_str = traceback.format_exc()
        logger.critical(f"导入主窗口失败: {e}\n{tb_str}")
        QMessageBox.critical(None, "错误", f"无法启动主程序: {e}")  # type: ignore
        sys.exit(1)
    except Exception as e:
        tb_str = traceback.format_exc()
        logger.critical(f"启动主程序时发生严重错误: {e}\n{tb_str}")
        QMessageBox.critical(None, "错误", f"启动主程序时发生错误: {e}")  # type: ignore
        sys.exit(1)
