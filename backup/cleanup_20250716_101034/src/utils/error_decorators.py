#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的错误处理装饰器
简化重复的错误处理模式
"""

import functools
import asyncio
from typing import Any, Callable, Optional, Union, Dict
from src.utils.logger import logger


def handle_exceptions(
    default_return: Any = None,
    log_level: str = "error",
    reraise: bool = False,
    custom_message: Optional[str] = None
):
    """通用异常处理装饰器
    
    Args:
        default_return: 异常时的默认返回值
        log_level: 日志级别 ('debug', 'info', 'warning', 'error', 'critical')
        reraise: 是否重新抛出异常
        custom_message: 自定义错误消息
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 构建错误消息
                func_name = f"{func.__module__}.{func.__qualname__}"
                message = custom_message or f"函数 {func_name} 执行失败"
                full_message = f"{message}: {e}"
                
                # 记录日志
                log_func = getattr(logger, log_level, logger.error)
                log_func(full_message, exc_info=True)
                
                # 是否重新抛出异常
                if reraise:
                    raise
                
                return default_return
        
        return wrapper
    return decorator


def handle_async_exceptions(
    default_return: Any = None,
    log_level: str = "error",
    reraise: bool = False,
    custom_message: Optional[str] = None
):
    """异步函数异常处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # 构建错误消息
                func_name = f"{func.__module__}.{func.__qualname__}"
                message = custom_message or f"异步函数 {func_name} 执行失败"
                full_message = f"{message}: {e}"
                
                # 记录日志
                log_func = getattr(logger, log_level, logger.error)
                log_func(full_message, exc_info=True)
                
                # 是否重新抛出异常
                if reraise:
                    raise
                
                return default_return
        
        return wrapper
    return decorator


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    default_return: Any = None
):
    """重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff_factor: 延迟递增因子
        exceptions: 需要重试的异常类型
        default_return: 最终失败时的默认返回值
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    func_name = f"{func.__module__}.{func.__qualname__}"
                    
                    if attempt < max_retries:
                        logger.warning(f"函数 {func_name} 第 {attempt + 1} 次尝试失败: {e}，"
                                     f"{current_delay:.1f}秒后重试")
                        import time
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"函数 {func_name} 在 {max_retries} 次重试后仍然失败: {e}")
                        break
            
            return default_return
        
        return wrapper
    return decorator


def retry_async_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    default_return: Any = None
):
    """异步重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    func_name = f"{func.__module__}.{func.__qualname__}"
                    
                    if attempt < max_retries:
                        logger.warning(f"异步函数 {func_name} 第 {attempt + 1} 次尝试失败: {e}，"
                                     f"{current_delay:.1f}秒后重试")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"异步函数 {func_name} 在 {max_retries} 次重试后仍然失败: {e}")
                        break
            
            return default_return
        
        return wrapper
    return decorator


def validate_inputs(**validators):
    """输入验证装饰器
    
    Args:
        **validators: 参数名到验证函数的映射
    
    Example:
        @validate_inputs(
            text=lambda x: isinstance(x, str) and len(x) > 0,
            count=lambda x: isinstance(x, int) and x > 0
        )
        def process_text(text, count):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数签名
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # 验证参数
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if not validator(value):
                        func_name = f"{func.__module__}.{func.__qualname__}"
                        raise ValueError(f"函数 {func_name} 的参数 {param_name} 验证失败: {value}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def log_execution_time(log_level: str = "info", threshold_seconds: float = 0.0):
    """执行时间记录装饰器
    
    Args:
        log_level: 日志级别
        threshold_seconds: 只记录超过此阈值的执行时间
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                if execution_time >= threshold_seconds:
                    func_name = f"{func.__module__}.{func.__qualname__}"
                    log_func = getattr(logger, log_level, logger.info)
                    log_func(f"函数 {func_name} 执行时间: {execution_time:.3f}秒")
        
        return wrapper
    return decorator


def log_async_execution_time(log_level: str = "info", threshold_seconds: float = 0.0):
    """异步执行时间记录装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                if execution_time >= threshold_seconds:
                    func_name = f"{func.__module__}.{func.__qualname__}"
                    log_func = getattr(logger, log_level, logger.info)
                    log_func(f"异步函数 {func_name} 执行时间: {execution_time:.3f}秒")
        
        return wrapper
    return decorator


# 常用的组合装饰器
def safe_execute(default_return: Any = None, log_errors: bool = True):
    """安全执行装饰器（异常处理 + 执行时间记录）"""
    def decorator(func: Callable) -> Callable:
        @log_execution_time(threshold_seconds=1.0)
        @handle_exceptions(default_return=default_return, log_level="error" if log_errors else "debug")
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def safe_async_execute(default_return: Any = None, log_errors: bool = True):
    """安全异步执行装饰器"""
    def decorator(func: Callable) -> Callable:
        @log_async_execution_time(threshold_seconds=1.0)
        @handle_async_exceptions(default_return=default_return, log_level="error" if log_errors else "debug")
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator
