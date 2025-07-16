# Utils Package
from .logger import Logger
from .log_config_manager import log_config_manager

# 使用配置管理器的设置创建logger
logger = Logger(
    level=log_config_manager.get_file_level(),
    console_output=log_config_manager.config.get('enable_console', True)
).get_logger()