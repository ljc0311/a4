import logging
import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
LOG_FILE = os.path.join(PROJECT_ROOT, 'logs', 'system.log')

class Logger:
    def __init__(self, name='AIVideoLogger', level=logging.INFO, fmt=None, remote_url=None, console_output=True):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 详细的日志格式，包含更多上下文信息
        log_format = fmt or '[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] [%(funcName)s] %(message)s'
        formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
        
        # 清除现有的处理器，避免重复
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 文件处理器 - 使用RotatingFileHandler避免日志文件过大
        try:
            # 确保日志目录存在
            log_dir = os.path.dirname(LOG_FILE)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 清空上一次的日志内容
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'w', encoding='utf-8') as f:
                    f.write('')  # 清空文件内容
                
            fh = RotatingFileHandler(
                LOG_FILE, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            fh.setLevel(level)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
        except Exception as e:
            print(f"创建文件日志处理器失败: {e}", file=sys.stderr)
        
        # 控制台处理器 - 用于实时查看详细工作进程
        if console_output:
            try:
                ch = logging.StreamHandler(sys.stdout)
                # 控制台显示INFO及以上级别的日志，显示详细工作进程
                ch.setLevel(logging.INFO)

                # 为控制台使用更简洁的格式
                console_format = '[%(asctime)s] [%(levelname)s] %(message)s'
                console_formatter = logging.Formatter(console_format, datefmt='%H:%M:%S')
                ch.setFormatter(console_formatter)

                self.logger.addHandler(ch)
            except Exception as e:
                print(f"创建控制台日志处理器失败: {e}", file=sys.stderr)

    def get_logger(self):
        return self.logger

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)

    def critical(self, msg):
        self.logger.critical(msg)

    def exception(self, msg):
        self.logger.exception(msg)

    def flush(self):
        """强制刷新日志到文件"""
        try:
            for handler in self.logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
        except Exception as e:
            # 如果flush失败，不要影响程序运行
            pass


class LoggerWrapper:
    """日志包装器，提供兼容的接口"""

    def __init__(self, logger_instance):
        self._logger_instance = logger_instance
        self._logger = logger_instance.logger

    def debug(self, msg):
        return self._logger.debug(msg)

    def info(self, msg):
        return self._logger.info(msg)

    def warning(self, msg):
        return self._logger.warning(msg)

    def error(self, msg):
        return self._logger.error(msg)

    def critical(self, msg):
        return self._logger.critical(msg)

    def exception(self, msg):
        return self._logger.exception(msg)

    def flush(self):
        """强制刷新日志到文件"""
        return self._logger_instance.flush()

    def __getattr__(self, name):
        """代理其他属性到原始logger"""
        return getattr(self._logger, name)


# 创建全局logger实例
_logger_instance = Logger()
logger = LoggerWrapper(_logger_instance)