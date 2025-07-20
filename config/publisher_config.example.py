# -*- coding: utf-8 -*-
"""
一键发布功能配置示例
复制此文件为 publisher_config.py 并填入您的配置
"""

# 数据库配置
DATABASE_CONFIG = {
    'url': 'sqlite:///data/publisher/publisher.db',  # 数据库连接URL
    'echo': False,  # 是否显示SQL语句
    'pool_size': 5,  # 连接池大小
    'max_overflow': 10  # 最大溢出连接数
}

# Redis配置（用于任务队列）
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'password': None,  # 如果Redis设置了密码，请在此填入
    'decode_responses': True
}

# Celery配置（任务队列）
CELERY_CONFIG = {
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/0',
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'Asia/Shanghai',
    'enable_utc': True
}

# 平台配置
PLATFORM_CONFIG = {
    'bilibili': {
        'enabled': True,
        'api_base': 'https://api.bilibili.com',
        'upload_base': 'https://upos-sz-upcdn.bilivideo.com',
        'member_base': 'https://member.bilibili.com',
        'timeout': 300,  # 请求超时时间（秒）
        'max_retries': 3,  # 最大重试次数
        'retry_delay': 5,  # 重试延迟（秒）
    },
    'douyin': {
        'enabled': False,  # 暂未实现
        'base_url': 'https://www.douyin.com',
        'timeout': 300,
        'max_retries': 3,
        'retry_delay': 5,
    },
    'kuaishou': {
        'enabled': False,  # 暂未实现
        'base_url': 'https://www.kuaishou.com',
        'timeout': 300,
        'max_retries': 3,
        'retry_delay': 5,
    },
    'xiaohongshu': {
        'enabled': False,  # 暂未实现
        'base_url': 'https://www.xiaohongshu.com',
        'timeout': 300,
        'max_retries': 3,
        'retry_delay': 5,
    },
    'wechat_channels': {
        'enabled': False,  # 暂未实现
        'base_url': 'https://channels.weixin.qq.com',
        'timeout': 300,
        'max_retries': 3,
        'retry_delay': 5,
    },
    'youtube': {
        'enabled': False,  # 暂未实现
        'api_base': 'https://www.googleapis.com/youtube/v3',
        'timeout': 300,
        'max_retries': 3,
        'retry_delay': 5,
    }
}

# 视频转换配置
VIDEO_CONVERSION_CONFIG = {
    'ffmpeg_path': 'ffmpeg',  # FFmpeg可执行文件路径
    'temp_dir': 'temp/video_conversion',  # 临时文件目录
    'output_dir': 'output/published_videos',  # 输出文件目录
    'max_concurrent_conversions': 3,  # 最大并发转换数
    'quality_preset': 'medium',  # 质量预设：fast, medium, slow
    'cleanup_temp_files': True,  # 是否清理临时文件
}

# 安全配置
SECURITY_CONFIG = {
    'encryption_key_file': 'config/publisher_encryption.key',  # 加密密钥文件路径
    'credential_timeout': 86400,  # 凭证超时时间（秒），24小时
    'max_login_attempts': 3,  # 最大登录尝试次数
    'login_retry_delay': 300,  # 登录重试延迟（秒），5分钟
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',  # 日志级别：DEBUG, INFO, WARNING, ERROR
    'file_path': 'logs/publisher.log',  # 日志文件路径
    'max_file_size': 10 * 1024 * 1024,  # 最大文件大小（字节），10MB
    'backup_count': 5,  # 备份文件数量
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}

# 任务配置
TASK_CONFIG = {
    'max_concurrent_tasks': 5,  # 最大并发任务数
    'task_timeout': 1800,  # 任务超时时间（秒），30分钟
    'retry_delays': [60, 300, 900],  # 重试延迟序列（秒）
    'cleanup_completed_tasks_after': 7,  # 清理已完成任务的天数
    'cleanup_failed_tasks_after': 30,  # 清理失败任务的天数
}

# 监控配置
MONITORING_CONFIG = {
    'enable_metrics': True,  # 是否启用指标收集
    'metrics_interval': 60,  # 指标收集间隔（秒）
    'health_check_interval': 300,  # 健康检查间隔（秒）
    'alert_on_failure_rate': 0.5,  # 失败率告警阈值
    'alert_email': None,  # 告警邮箱（可选）
}

# 内容优化配置
CONTENT_OPTIMIZATION_CONFIG = {
    'enable_ai_optimization': True,  # 是否启用AI内容优化
    'title_max_length': {
        'bilibili': 80,
        'douyin': 55,
        'kuaishou': 50,
        'xiaohongshu': 20,
        'wechat_channels': 30,
        'youtube': 100
    },
    'description_max_length': {
        'bilibili': 2000,
        'douyin': 2200,
        'kuaishou': 2200,
        'xiaohongshu': 1000,
        'wechat_channels': 600,
        'youtube': 5000
    },
    'max_tags': {
        'bilibili': 12,
        'douyin': 10,
        'kuaishou': 10,
        'xiaohongshu': 10,
        'wechat_channels': 5,
        'youtube': 15
    }
}

# 默认发布模板
DEFAULT_TEMPLATES = {
    'bilibili': {
        'title_template': '{title}',
        'description_template': '{description}\n\n#视频创作 #内容分享',
        'default_tags': ['视频创作', '内容分享', '创意'],
        'category': '生活',
        'privacy': 'public'
    },
    'douyin': {
        'title_template': '{title}',
        'description_template': '{description} #视频创作 #内容分享',
        'default_tags': ['视频创作', '内容分享', '创意'],
        'privacy': 'public'
    },
    'kuaishou': {
        'title_template': '{title}',
        'description_template': '{description} #视频创作 #内容分享',
        'default_tags': ['视频创作', '内容分享', '创意'],
        'privacy': 'public'
    },
    'xiaohongshu': {
        'title_template': '{title}',
        'description_template': '{description}\n\n#视频创作 #内容分享',
        'default_tags': ['视频创作', '内容分享', '创意'],
        'privacy': 'public'
    },
    'wechat_channels': {
        'title_template': '{title}',
        'description_template': '{description}',
        'default_tags': ['视频创作', '内容分享'],
        'privacy': 'public'
    },
    'youtube': {
        'title_template': '{title}',
        'description_template': '{description}\n\n#Video #Content #Creative',
        'default_tags': ['Video', 'Content', 'Creative'],
        'category': 'People & Blogs',
        'privacy': 'public'
    }
}

# 开发配置
DEVELOPMENT_CONFIG = {
    'debug_mode': False,  # 是否启用调试模式
    'mock_api_calls': False,  # 是否模拟API调用（用于测试）
    'test_mode': False,  # 是否启用测试模式
    'verbose_logging': False,  # 是否启用详细日志
}
