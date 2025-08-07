#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一错误处理和用户反馈模块
"""

import traceback
from typing import Dict, Optional, Any

from src.core.language_manager import LanguageManager
from src.utils.logger import logger

class AppError(Exception):
    """应用程序自定义异常基类"""
    def __init__(self, message_key: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        self.message_key = message_key
        self.context = context or {}
        self.original_exception = original_exception
        
        # 获取本地化消息
        self.localized_message = ErrorHandler.get_message(message_key, self.context)
        
        super().__init__(self.localized_message)

    def __str__(self):
        return f"AppError: [{self.message_key}] {self.localized_message}"

class ErrorHandler:
    """
    错误处理和本地化消息系统
    """
    _messages: Dict[str, Dict[str, str]] = {
        'zh': {
            'unknown_error': '发生未知错误: {error}',
            'file_not_found': '文件未找到: {path}',
            'voice_generation_failed': '语音生成失败。原因: {reason}',
            'voice_generation_retry': '语音生成失败，正在尝试第 {attempt}/{max_attempts} 次重试...',
            'subtitle_generation_failed': '字幕生成失败: {reason}',
            'video_composition_failed': '视频合成失败: {reason}',
            'language_detection_failed': '语言检测失败: {reason}',
            'config_load_error': '加载配置文件失败: {path}',
            'service_initialization_failed': '服务初始化失败: {service_name}',
        },
        'en': {
            'unknown_error': 'An unknown error occurred: {error}',
            'file_not_found': 'File not found: {path}',
            'voice_generation_failed': 'Voice generation failed. Reason: {reason}',
            'voice_generation_retry': 'Voice generation failed. Retrying attempt {attempt}/{max_attempts}...',
            'subtitle_generation_failed': 'Subtitle generation failed: {reason}',
            'video_composition_failed': 'Video composition failed: {reason}',
            'language_detection_failed': 'Language detection failed: {reason}',
            'config_load_error': 'Failed to load configuration file: {path}',
            'service_initialization_failed': 'Service initialization failed: {service_name}',
        }
    }

    @staticmethod
    def get_message(key: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        获取本地化的错误消息
        
        Args:
            key: 消息键
            context: 格式化消息的上下文变量
            
        Returns:
            本地化的消息字符串
        """
        context = context or {}
        try:
            lang_manager = LanguageManager()
            language_code = lang_manager.current_language.value
            
            message_template = ErrorHandler._messages.get(language_code, ErrorHandler._messages['en']).get(key, key)
            return message_template.format(**context)
        except Exception:
            # 降级到默认语言
            message_template = ErrorHandler._messages['en'].get(key, key)
            return message_template.format(**context)

    @staticmethod
    def report_error(error: Exception, message_key: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        """
        报告和记录错误
        
        Args:
            error: 异常对象
            message_key: 用于用户显示的消息键
            context: 消息上下文
        """
        if isinstance(error, AppError):
            logger.error(f"Application Error [{error.message_key}]: {error.localized_message}")
            if error.original_exception:
                logger.debug(f"Original Exception: {traceback.format_exc()}")
            # 在这里可以添加UI通知逻辑
            # from src.gui.notification_system import NotificationSystem
            # NotificationSystem.show_error(error.localized_message)

        else:
            logger.error(f"Unhandled Exception: {str(error)}")
            logger.debug(traceback.format_exc())
            
            user_message = ErrorHandler.get_message(
                message_key or 'unknown_error',
                context or {'error': str(error)}
            )
            # 在这里可以添加UI通知逻辑
            # from src.gui.notification_system import NotificationSystem
            # NotificationSystem.show_error(user_message)

def get_error_message(key: str, context: Optional[Dict[str, Any]] = None) -> str:
    """便捷函数，用于获取错误消息"""
    return ErrorHandler.get_message(key, context)
