#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能错误处理中心
提供网络检测、自动恢复机制、用户友好的错误提示等功能
"""

import sys
import time
import json
import traceback
import threading
import functools
import requests
from typing import Dict, Optional, Any, Callable, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
import socket
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt5.QtWidgets import QMessageBox, QWidget

from src.utils.logger import logger
from src.gui.notification_system import show_error, show_warning, show_info

class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"           # 低级错误，可以忽略
    MEDIUM = "medium"     # 中级错误，需要用户注意
    HIGH = "high"         # 高级错误，影响功能使用
    CRITICAL = "critical" # 严重错误，可能导致崩溃

class ErrorCategory(Enum):
    """错误类别"""
    NETWORK = "network"           # 网络相关错误
    FILE_IO = "file_io"          # 文件IO错误
    API = "api"                   # API调用错误
    MEMORY = "memory"             # 内存相关错误
    PERMISSION = "permission"     # 权限错误
    VALIDATION = "validation"     # 数据验证错误
    SYSTEM = "system"             # 系统错误
    UI = "ui"                     # 界面错误
    UNKNOWN = "unknown"           # 未知错误

@dataclass
class ErrorInfo:
    """错误信息数据类"""
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    exception: Optional[Exception] = None
    traceback_str: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: float = 0.0
    user_message: Optional[str] = None  # 用户友好的错误信息
    solutions: Optional[List[str]] = None  # 建议的解决方案
    retry_count: int = 0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        
        if self.traceback_str is None and self.exception:
            self.traceback_str = ''.join(traceback.format_exception(
                type(self.exception), self.exception, self.exception.__traceback__
            ))

class NetworkChecker(QObject):
    """网络连接检查器"""
    
    # 信号
    connection_restored = pyqtSignal()
    connection_lost = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.is_connected = True
        self.check_interval = 30  # 30秒检查一次
        self.timeout = 5  # 5秒超时
        
        # 检查的服务列表
        self.check_urls = [
            "https://www.baidu.com",
            "https://www.google.com",
            "https://httpbin.org/get"
        ]
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_connection)
        self.timer.start(self.check_interval * 1000)
    
    def check_connection(self) -> bool:
        """检查网络连接"""
        try:
            # 快速检查：尝试连接DNS服务器
            socket.create_connection(("8.8.8.8", 53), timeout=self.timeout)
            
            # 详细检查：HTTP请求
            for url in self.check_urls:
                try:
                    response = requests.get(url, timeout=self.timeout)
                    if response.status_code == 200:
                        if not self.is_connected:
                            self.is_connected = True
                            self.connection_restored.emit()
                            logger.info("网络连接已恢复")
                        return True
                except:
                    continue
            
            # 所有检查都失败
            if self.is_connected:
                self.is_connected = False
                self.connection_lost.emit()
                logger.warning("网络连接丢失")
            return False
            
        except Exception as e:
            if self.is_connected:
                self.is_connected = False
                self.connection_lost.emit()
                logger.warning(f"网络连接检查失败: {e}")
            return False
    
    def force_check(self) -> bool:
        """强制检查网络连接"""
        return self.check_connection()

class RetryMechanism:
    """重试机制"""
    
    def __init__(self, max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
    
    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """执行重试"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.delay * (self.backoff ** attempt)
                    logger.warning(f"函数 {func.__name__} 第{attempt + 1}次尝试失败，{wait_time:.1f}秒后重试: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"函数 {func.__name__} 重试{self.max_retries}次后仍然失败")
        
        raise last_exception
    
    def retry_decorator(self, exceptions: Union[Exception, tuple] = Exception):
        """重试装饰器"""
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(self.max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        if attempt < self.max_retries:
                            wait_time = self.delay * (self.backoff ** attempt)
                            logger.warning(f"函数 {func.__name__} 第{attempt + 1}次尝试失败，{wait_time:.1f}秒后重试: {e}")
                            time.sleep(wait_time)
                        else:
                            raise e
            return wrapper
        return decorator

class ErrorClassifier:
    """错误分类器"""
    
    def __init__(self):
        # 错误模式匹配规则
        self.patterns = {
            ErrorCategory.NETWORK: [
                "connection", "timeout", "network", "urllib", "requests",
                "ConnectionError", "TimeoutError", "URLError"
            ],
            ErrorCategory.FILE_IO: [
                "FileNotFoundError", "PermissionError", "IOError", "OSError",
                "file", "directory", "path", "permission denied"
            ],
            ErrorCategory.API: [
                "API", "HTTP", "401", "403", "404", "500", "502", "503",
                "Unauthorized", "Forbidden", "BadRequest"
            ],
            ErrorCategory.MEMORY: [
                "MemoryError", "OutOfMemoryError", "memory", "heap",
                "allocation failed"
            ],
            ErrorCategory.PERMISSION: [
                "PermissionError", "AccessDenied", "permission denied",
                "access denied", "unauthorized"
            ],
            ErrorCategory.VALIDATION: [
                "ValueError", "TypeError", "validation", "invalid",
                "format", "parse"
            ],
            ErrorCategory.UI: [
                "Qt", "QWidget", "GUI", "window", "dialog", "paint"
            ]
        }
    
    def classify_error(self, exception: Exception, message: str = None) -> ErrorCategory:
        """分类错误"""
        error_text = str(exception).lower()
        exception_name = type(exception).__name__
        full_text = f"{exception_name} {error_text} {message or ''}".lower()
        
        # 计算每个类别的匹配得分
        scores = {}
        for category, patterns in self.patterns.items():
            score = sum(1 for pattern in patterns if pattern.lower() in full_text)
            if score > 0:
                scores[category] = score
        
        # 返回得分最高的类别
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return ErrorCategory.UNKNOWN
    
    def determine_severity(self, exception: Exception, category: ErrorCategory) -> ErrorSeverity:
        """确定错误严重程度"""
        exception_name = type(exception).__name__
        
        # 根据异常类型确定严重程度
        critical_exceptions = [
            "SystemExit", "KeyboardInterrupt", "MemoryError",
            "RecursionError", "SystemError"
        ]
        
        high_exceptions = [
            "ConnectionError", "TimeoutError", "PermissionError",
            "FileNotFoundError", "ImportError"
        ]
        
        medium_exceptions = [
            "ValueError", "TypeError", "AttributeError",
            "KeyError", "IndexError"
        ]
        
        if exception_name in critical_exceptions:
            return ErrorSeverity.CRITICAL
        elif exception_name in high_exceptions:
            return ErrorSeverity.HIGH
        elif exception_name in medium_exceptions:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

class SolutionProvider:
    """解决方案提供器"""
    
    def __init__(self):
        # 常见错误的解决方案
        self.solutions = {
            ErrorCategory.NETWORK: [
                "检查网络连接是否正常",
                "尝试重新连接WiFi或有线网络",
                "检查防火墙设置是否阻止了程序",
                "稍后重试，可能是服务器临时不可用",
                "联系网络管理员检查网络配置"
            ],
            ErrorCategory.FILE_IO: [
                "检查文件路径是否正确",
                "确认文件存在且未被其他程序占用",
                "检查磁盘空间是否充足",
                "确认有足够的文件访问权限",
                "尝试以管理员身份运行程序"
            ],
            ErrorCategory.API: [
                "检查API密钥是否正确配置",
                "确认API服务可用性",
                "检查请求参数是否符合API要求",
                "稍后重试，可能是服务器繁忙",
                "联系API服务提供商获取支持"
            ],
            ErrorCategory.MEMORY: [
                "关闭一些不必要的程序释放内存",
                "重启应用程序",
                "检查是否有内存泄漏",
                "考虑增加系统内存",
                "分批处理大量数据"
            ],
            ErrorCategory.PERMISSION: [
                "以管理员身份运行程序",
                "检查文件夹权限设置",
                "确认当前用户有足够权限",
                "联系系统管理员获取权限",
                "更改文件保存位置"
            ],
            ErrorCategory.VALIDATION: [
                "检查输入数据的格式是否正确",
                "确认所有必填字段都已填写",
                "验证数据类型是否匹配",
                "检查数据范围是否在允许范围内",
                "参考帮助文档了解正确格式"
            ]
        }
    
    def get_solutions(self, category: ErrorCategory, context: Dict[str, Any] = None) -> List[str]:
        """获取解决方案"""
        base_solutions = self.solutions.get(category, ["请查看详细错误信息或联系技术支持"])
        
        # 根据上下文定制解决方案
        if context:
            customized = self._customize_solutions(base_solutions, context)
            return customized
        
        return base_solutions
    
    def _customize_solutions(self, solutions: List[str], context: Dict[str, Any]) -> List[str]:
        """根据上下文定制解决方案"""
        # 这里可以根据具体的上下文信息提供更精确的解决方案
        return solutions

class UserMessageGenerator:
    """用户友好信息生成器"""
    
    def __init__(self):
        self.friendly_messages = {
            ErrorCategory.NETWORK: "网络连接出现问题，请检查您的网络设置",
            ErrorCategory.FILE_IO: "文件操作失败，请检查文件路径和权限",
            ErrorCategory.API: "服务连接失败，请稍后重试",
            ErrorCategory.MEMORY: "系统内存不足，请关闭一些程序后重试",
            ErrorCategory.PERMISSION: "权限不足，请以管理员身份运行",
            ErrorCategory.VALIDATION: "输入数据格式有误，请检查输入内容",
            ErrorCategory.UI: "界面显示出现问题，请尝试重启程序",
            ErrorCategory.SYSTEM: "系统出现错误，请重启程序",
            ErrorCategory.UNKNOWN: "发生了未知错误，请查看详细信息"
        }
    
    def generate_message(self, error_info: ErrorInfo) -> str:
        """生成用户友好的错误信息"""
        base_message = self.friendly_messages.get(
            error_info.category, 
            "发生了错误，请查看详细信息"
        )
        
        # 根据严重程度调整语气
        if error_info.severity == ErrorSeverity.CRITICAL:
            return f"严重错误：{base_message}"
        elif error_info.severity == ErrorSeverity.HIGH:
            return f"重要错误：{base_message}"
        elif error_info.severity == ErrorSeverity.MEDIUM:
            return f"错误：{base_message}"
        else:
            return f"提示：{base_message}"

class ErrorHandler(QObject):
    """智能错误处理器"""
    
    # 信号
    error_occurred = pyqtSignal(ErrorInfo)
    error_resolved = pyqtSignal(str)  # error_id
    
    def __init__(self):
        super().__init__()
        
        # 组件初始化
        self.network_checker = NetworkChecker()
        self.retry_mechanism = RetryMechanism()
        self.classifier = ErrorClassifier()
        self.solution_provider = SolutionProvider()
        self.message_generator = UserMessageGenerator()
        
        # 错误记录
        self.error_history: List[ErrorInfo] = []
        self.error_counts: Dict[str, int] = {}
        self.suppressed_errors: set = set()
        
        # 连接网络信号
        self.network_checker.connection_restored.connect(self._on_network_restored)
        self.network_checker.connection_lost.connect(self._on_network_lost)
        
        # 配置
        self.max_history = 100
        self.suppress_threshold = 5  # 同一错误出现5次后开始抑制
    
    def handle_exception(self, exception: Exception, context: Dict[str, Any] = None, 
                        show_to_user: bool = True) -> ErrorInfo:
        """处理异常"""
        try:
            # 分类错误
            category = self.classifier.classify_error(exception, context.get('message') if context else None)
            severity = self.classifier.determine_severity(exception, category)
            
            # 创建错误信息
            error_info = ErrorInfo(
                message=str(exception),
                category=category,
                severity=severity,
                exception=exception,
                context=context
            )
            
            # 生成用户友好信息和解决方案
            error_info.user_message = self.message_generator.generate_message(error_info)
            error_info.solutions = self.solution_provider.get_solutions(category, context)
            
            # 检查是否需要抑制
            error_signature = f"{type(exception).__name__}:{str(exception)[:100]}"
            self.error_counts[error_signature] = self.error_counts.get(error_signature, 0) + 1
            
            if self.error_counts[error_signature] > self.suppress_threshold:
                if error_signature not in self.suppressed_errors:
                    self.suppressed_errors.add(error_signature)
                    logger.warning(f"错误 {error_signature} 出现次数过多，开始抑制显示")
                show_to_user = False
            
            # 记录错误
            self._record_error(error_info)
            
            # 显示给用户
            if show_to_user:
                self._show_error_to_user(error_info)
            
            # 发送信号
            self.error_occurred.emit(error_info)
            
            # 尝试自动恢复
            self._try_auto_recovery(error_info)
            
            return error_info
            
        except Exception as handling_error:
            # 处理异常时出错，记录但不递归
            logger.critical(f"错误处理器自身出错: {handling_error}")
            return ErrorInfo(
                message=str(exception),
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.HIGH,
                exception=exception
            )
    
    def _record_error(self, error_info: ErrorInfo):
        """记录错误"""
        self.error_history.append(error_info)
        
        # 限制历史记录大小
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
        
        # 记录到日志
        logger.error(f"[{error_info.category.value}] {error_info.message}")
        if error_info.traceback_str:
            logger.debug(f"错误堆栈:\n{error_info.traceback_str}")
    
    def _show_error_to_user(self, error_info: ErrorInfo):
        """向用户显示错误"""
        try:
            message = error_info.user_message or error_info.message
            
            if error_info.severity == ErrorSeverity.CRITICAL:
                # 关键错误使用弹窗
                QMessageBox.critical(None, "严重错误", f"{message}\n\n建议解决方案:\n" + 
                                   "\n".join(f"• {s}" for s in error_info.solutions[:3]))
            elif error_info.severity == ErrorSeverity.HIGH:
                # 高级错误使用通知
                show_error(f"{message}\n解决方案: {error_info.solutions[0] if error_info.solutions else '请查看帮助'}")
            elif error_info.severity == ErrorSeverity.MEDIUM:
                # 中级错误使用警告通知
                show_warning(message)
            else:
                # 低级错误记录到日志即可
                logger.info(f"低级错误: {message}")
                
        except Exception as e:
            logger.error(f"显示错误信息失败: {e}")
    
    def _try_auto_recovery(self, error_info: ErrorInfo):
        """尝试自动恢复"""
        try:
            if error_info.category == ErrorCategory.NETWORK:
                # 网络错误：检查连接并可能重试
                if not self.network_checker.is_connected:
                    self.network_checker.force_check()
            
            elif error_info.category == ErrorCategory.MEMORY:
                # 内存错误：强制垃圾回收
                import gc
                gc.collect()
                logger.info("执行内存清理以恢复内存错误")
            
            elif error_info.category == ErrorCategory.FILE_IO:
                # 文件错误：检查路径是否存在
                if error_info.context and 'file_path' in error_info.context:
                    file_path = Path(error_info.context['file_path'])
                    if not file_path.parent.exists():
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        logger.info(f"自动创建目录: {file_path.parent}")
                        
        except Exception as e:
            logger.warning(f"自动恢复失败: {e}")
    
    def _on_network_restored(self):
        """网络恢复处理"""
        show_info("网络连接已恢复")
        # 清除网络相关的错误抑制
        network_errors = [key for key in self.suppressed_errors if 'connection' in key.lower()]
        for key in network_errors:
            self.suppressed_errors.discard(key)
            self.error_counts[key] = 0
    
    def _on_network_lost(self):
        """网络丢失处理"""
        show_warning("网络连接已断开，部分功能可能无法使用")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计"""
        if not self.error_history:
            return {}
        
        # 按类别统计
        category_counts = {}
        severity_counts = {}
        
        for error in self.error_history:
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
        
        return {
            'total_errors': len(self.error_history),
            'by_category': category_counts,
            'by_severity': severity_counts,
            'suppressed_count': len(self.suppressed_errors),
            'recent_errors': [asdict(error) for error in self.error_history[-5:]]
        }
    
    def clear_error_history(self):
        """清除错误历史"""
        self.error_history.clear()
        self.error_counts.clear()
        self.suppressed_errors.clear()

# 全局错误处理器实例
error_handler = ErrorHandler()

def handle_exception_decorator(show_to_user: bool = True, context: Dict[str, Any] = None):
    """异常处理装饰器"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = context or {}
                error_context.update({
                    'function': func.__name__,
                    'module': func.__module__,
                    'args': str(args)[:200],  # 限制长度
                    'kwargs': str(kwargs)[:200]
                })
                
                error_handler.handle_exception(e, error_context, show_to_user)
                return None
        return wrapper
    return decorator

def safe_execute(func: Callable, *args, default_return=None, 
                show_error: bool = True, **kwargs) -> Any:
    """安全执行函数"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_handler.handle_exception(e, {
            'function': func.__name__ if hasattr(func, '__name__') else str(func),
            'args': str(args)[:200],
            'kwargs': str(kwargs)[:200]
        }, show_error)
        return default_return

# 便捷函数
def handle_error(exception: Exception, context: Dict[str, Any] = None, 
                show_to_user: bool = True) -> ErrorInfo:
    """处理错误"""
    return error_handler.handle_exception(exception, context, show_to_user)

def check_network() -> bool:
    """检查网络连接"""
    return error_handler.network_checker.force_check()

def get_error_stats() -> Dict[str, Any]:
    """获取错误统计"""
    return error_handler.get_error_statistics()

def clear_errors():
    """清除错误历史"""
    error_handler.clear_error_history() 