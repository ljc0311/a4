#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的日志系统
减少冗余日志，提高性能，支持结构化日志
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class StructuredFormatter(logging.Formatter):
    """结构化日志格式器"""
    
    def format(self, record):
        # 基础日志信息
        log_entry = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created)),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # 添加自定义字段
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        
        return json.dumps(log_entry, ensure_ascii=False)


class OptimizedLogger:
    """优化的日志管理器"""
    
    def __init__(self, name: str = "AIVideoGenerator"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.WARNING)
        
        # 防止重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
        
        # 日志频率控制
        self._log_counts = {}
        self._last_log_time = {}
        self._suppress_threshold = 10  # 相同日志10次后开始抑制
        self._suppress_interval = 60   # 抑制间隔60秒
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 控制台处理器（简化格式，只显示警告及以上级别）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] [%(module)s:%(lineno)d] [%(funcName)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器（结构化格式）
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 按大小轮转的文件处理器
        file_handler = RotatingFileHandler(
            log_dir / "system.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(file_handler)
        
        # 错误日志单独文件
        error_handler = RotatingFileHandler(
            log_dir / "errors.log",
            maxBytes=5*1024*1024,   # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(error_handler)
    
    def _should_suppress_log(self, message: str, level: str) -> bool:
        """检查是否应该抑制重复日志"""
        if level in ['ERROR', 'CRITICAL']:
            return False  # 错误日志不抑制
        
        log_key = f"{level}:{message[:100]}"  # 使用前100个字符作为键
        current_time = time.time()
        
        # 更新计数
        self._log_counts[log_key] = self._log_counts.get(log_key, 0) + 1
        
        # 检查是否需要抑制
        if self._log_counts[log_key] > self._suppress_threshold:
            last_time = self._last_log_time.get(log_key, 0)
            if current_time - last_time < self._suppress_interval:
                return True
        
        # 更新最后记录时间
        self._last_log_time[log_key] = current_time
        return False
    
    def _log_with_suppression(self, level: str, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """带抑制功能的日志记录"""
        if self._should_suppress_log(message, level):
            return
        
        # 创建日志记录
        log_func = getattr(self.logger, level.lower())
        
        if extra_data:
            # 创建带额外数据的日志记录
            old_factory = logging.getLogRecordFactory()
            
            def record_factory(*args, **kwargs):
                record = old_factory(*args, **kwargs)
                record.extra_data = extra_data
                return record
            
            logging.setLogRecordFactory(record_factory)
            try:
                log_func(message, **kwargs)
            finally:
                logging.setLogRecordFactory(old_factory)
        else:
            log_func(message, **kwargs)
    
    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """调试日志"""
        self._log_with_suppression('DEBUG', message, extra_data, **kwargs)
    
    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """信息日志"""
        self._log_with_suppression('INFO', message, extra_data, **kwargs)
    
    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """警告日志"""
        self._log_with_suppression('WARNING', message, extra_data, **kwargs)
    
    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """错误日志（不抑制）"""
        log_func = getattr(self.logger, 'error')
        
        if extra_data:
            old_factory = logging.getLogRecordFactory()
            
            def record_factory(*args, **kwargs):
                record = old_factory(*args, **kwargs)
                record.extra_data = extra_data
                return record
            
            logging.setLogRecordFactory(record_factory)
            try:
                log_func(message, **kwargs)
            finally:
                logging.setLogRecordFactory(old_factory)
        else:
            log_func(message, **kwargs)
    
    def critical(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """严重错误日志（不抑制）"""
        log_func = getattr(self.logger, 'critical')
        
        if extra_data:
            old_factory = logging.getLogRecordFactory()
            
            def record_factory(*args, **kwargs):
                record = old_factory(*args, **kwargs)
                record.extra_data = extra_data
                return record
            
            logging.setLogRecordFactory(record_factory)
            try:
                log_func(message, **kwargs)
            finally:
                logging.setLogRecordFactory(old_factory)
        else:
            log_func(message, **kwargs)
    
    def log_performance(self, operation: str, duration: float, extra_data: Optional[Dict[str, Any]] = None):
        """性能日志"""
        perf_data = {
            'operation': operation,
            'duration_seconds': duration,
            'performance_log': True
        }
        if extra_data:
            perf_data.update(extra_data)
        
        if duration > 5.0:  # 超过5秒记录为警告
            self.warning(f"性能警告: {operation} 耗时 {duration:.3f}秒", perf_data)
        elif duration > 1.0:  # 超过1秒记录为信息
            self.info(f"性能监控: {operation} 耗时 {duration:.3f}秒", perf_data)
        else:  # 正常情况记录为调试
            self.debug(f"性能监控: {operation} 耗时 {duration:.3f}秒", perf_data)
    
    def log_api_call(self, api_name: str, status: str, duration: float, extra_data: Optional[Dict[str, Any]] = None):
        """API调用日志"""
        api_data = {
            'api_name': api_name,
            'status': status,
            'duration_seconds': duration,
            'api_log': True
        }
        if extra_data:
            api_data.update(extra_data)
        
        if status == 'success':
            self.info(f"API调用成功: {api_name} ({duration:.3f}s)", api_data)
        else:
            self.error(f"API调用失败: {api_name} - {status} ({duration:.3f}s)", api_data)
    
    def log_user_action(self, action: str, user_id: Optional[str] = None, extra_data: Optional[Dict[str, Any]] = None):
        """用户行为日志"""
        action_data = {
            'action': action,
            'user_id': user_id or 'anonymous',
            'user_action': True,
            'timestamp': time.time()
        }
        if extra_data:
            action_data.update(extra_data)
        
        self.info(f"用户操作: {action}", action_data)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        return {
            'total_log_types': len(self._log_counts),
            'suppressed_logs': sum(1 for count in self._log_counts.values() if count > self._suppress_threshold),
            'log_counts': dict(self._log_counts),
            'suppress_threshold': self._suppress_threshold,
            'suppress_interval': self._suppress_interval
        }
    
    def reset_suppression(self):
        """重置日志抑制状态"""
        self._log_counts.clear()
        self._last_log_time.clear()
        self.info("日志抑制状态已重置")


# 全局优化日志实例
optimized_logger = OptimizedLogger()

# 便捷函数
def debug(message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
    optimized_logger.debug(message, extra_data, **kwargs)

def info(message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
    optimized_logger.info(message, extra_data, **kwargs)

def warning(message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
    optimized_logger.warning(message, extra_data, **kwargs)

def error(message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
    optimized_logger.error(message, extra_data, **kwargs)

def critical(message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
    optimized_logger.critical(message, extra_data, **kwargs)

def log_performance(operation: str, duration: float, extra_data: Optional[Dict[str, Any]] = None):
    optimized_logger.log_performance(operation, duration, extra_data)

def log_api_call(api_name: str, status: str, duration: float, extra_data: Optional[Dict[str, Any]] = None):
    optimized_logger.log_api_call(api_name, status, duration, extra_data)

def log_user_action(action: str, user_id: Optional[str] = None, extra_data: Optional[Dict[str, Any]] = None):
    optimized_logger.log_user_action(action, user_id, extra_data)
