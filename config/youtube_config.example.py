#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube发布配置示例
复制此文件为 youtube_config.py 并填入您的配置
"""

# YouTube API配置（推荐方案）
YOUTUBE_API_CONFIG = {
    'enabled': True,
    'credentials_file': 'config/youtube_credentials.json',  # OAuth 2.0凭据文件
    'token_file': 'config/youtube_token.pickle',  # 访问令牌文件
    'application_name': 'AI Video Publisher',
    'api_version': 'v3',
    'scopes': ['https://www.googleapis.com/auth/youtube.upload'],
    
    # 上传配置
    'chunk_size': 1024 * 1024,  # 1MB chunks
    'max_retries': 3,
    'retry_delay': 2,
    'timeout': 300,
    
    # 默认视频设置
    'default_privacy': 'public',  # public, unlisted, private
    'default_category': '22',  # People & Blogs
    'auto_shorts_detection': True,  # 自动检测并标记Shorts
    'shorts_max_duration': 60,  # Shorts最大时长（秒）
}

# Selenium配置（备用方案）
YOUTUBE_SELENIUM_CONFIG = {
    'enabled': True,
    'driver_type': 'chrome',
    'headless': False,
    'stealth_mode': True,  # 启用反检测
    'disable_images': False,  # 禁用图片加载以提高速度
    
    # 反检测配置
    'random_user_agent': True,
    'random_window_size': True,
    'inject_stealth_scripts': True,
    
    # 调试模式配置
    'use_debug_mode': True,
    'debug_port': 9222,
    'debugger_address': '127.0.0.1:9222',
    
    # 超时配置
    'page_load_timeout': 60,
    'implicit_wait': 10,
    'upload_timeout': 600,  # 10分钟上传超时
    
    # 人性化操作
    'human_like_delays': True,
    'min_delay': 1,
    'max_delay': 3,
}

# 内容配置
YOUTUBE_CONTENT_CONFIG = {
    'title_max_length': 100,
    'description_max_length': 5000,
    'tags_max_count': 15,
    
    # Shorts配置
    'shorts_title_suffix': ' #Shorts',
    'shorts_description_suffix': '\n\n#Shorts',
    'shorts_tags': ['Shorts', 'Short', 'Viral'],
    
    # 默认标签
    'default_tags': ['Video', 'Content', 'Creative'],

    # 描述模板
    'description_template': '''
{description}

🔔 订阅频道获取更多内容
👍 点赞支持创作
💬 评论分享您的想法

#Video #Content #Creative
''',
    
    # 分类映射
    'categories': {
        'entertainment': '24',
        'education': '27',
        'science_technology': '28',
        'people_blogs': '22',
        'gaming': '20',
        'music': '10',
        'news_politics': '25'
    }
}

# 错误处理配置
YOUTUBE_ERROR_CONFIG = {
    'max_retries': 3,
    'retry_delay': 5,
    'exponential_backoff': True,
    
    # 常见错误处理
    'handle_quota_exceeded': True,
    'handle_upload_failed': True,
    'handle_authentication_failed': True,
    
    # 错误恢复策略
    'auto_retry_on_network_error': True,
    'auto_retry_on_server_error': True,
    'fallback_to_selenium': True,  # API失败时回退到Selenium
}

# 监控配置
YOUTUBE_MONITORING_CONFIG = {
    'enable_logging': True,
    'log_level': 'INFO',
    'log_file': 'logs/youtube_publisher.log',
    
    # 性能监控
    'track_upload_time': True,
    'track_success_rate': True,
    'track_error_types': True,
    
    # 通知配置
    'notify_on_success': False,
    'notify_on_failure': True,
    'notification_webhook': None,  # 可选的Webhook URL
}

# 完整配置
YOUTUBE_CONFIG = {
    'api': YOUTUBE_API_CONFIG,
    'selenium': YOUTUBE_SELENIUM_CONFIG,
    'content': YOUTUBE_CONTENT_CONFIG,
    'error_handling': YOUTUBE_ERROR_CONFIG,
    'monitoring': YOUTUBE_MONITORING_CONFIG
}

def get_youtube_config():
    """获取YouTube配置"""
    return YOUTUBE_CONFIG

# 设置指南
"""
YouTube发布器设置指南：

方案1: YouTube API（推荐）
1. 访问 https://console.developers.google.com/
2. 创建新项目或选择现有项目
3. 启用 YouTube Data API v3
4. 创建 OAuth 2.0 客户端ID凭据
5. 下载凭据JSON文件，保存为 config/youtube_credentials.json
6. 首次运行时会打开浏览器进行授权

方案2: Selenium（备用）
1. 安装Chrome浏览器
2. 启动Chrome调试模式:
   chrome.exe --remote-debugging-port=9222 --user-data-dir=youtube_selenium
3. 手动登录YouTube Studio
4. 运行发布程序

推荐使用方案1（API），更稳定可靠。
方案2作为备用，当API配额用完或出现问题时自动切换。
"""

# 使用示例
if __name__ == "__main__":
    config = get_youtube_config()
    print("YouTube配置加载成功:")
    print(f"- API启用: {config['api']['enabled']}")
    print(f"- Selenium启用: {config['selenium']['enabled']}")
    print(f"- 反检测模式: {config['selenium']['stealth_mode']}")
    print(f"- 最大重试次数: {config['error_handling']['max_retries']}")

    print("\n📋 设置步骤:")
    print("1. 复制此文件为 config/youtube_config.py")
    print("2. 按照上述指南配置YouTube API或Selenium")
    print("3. 运行测试脚本验证配置")
