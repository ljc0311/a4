# -*- coding: utf-8 -*-
"""
视频生成服务配置示例
复制此文件为 video_generation_config.py 并填入您的API密钥
"""

# 智谱AI CogVideoX-Flash 配置示例
COGVIDEOX_CONFIG = {
    'output_dir': 'output/videos',
    'routing_strategy': 'free_first',
    'engine_preferences': ['free', 'quality'],
    'concurrent_limit': 2,
    'engines': {
        'cogvideox_flash': {
            'enabled': True,
            'api_key': 'YOUR_ZHIPU_API_KEY_HERE',  # 在此填入您的智谱AI API密钥
            'base_url': 'https://open.bigmodel.cn/api/paas/v4',
            'model': 'cogvideox-flash',
            'timeout': 300,
            'max_retries': 3,
            'max_duration': 10.0,
            'supported_resolutions': [
                '720x480', '1024x1024', '1280x960', 
                '960x1280', '1920x1080', '1080x1920',
                '2048x1080', '3840x2160'
            ],
            'supported_fps': [30, 60],  # 移除不支持的24fps
            'cost_per_second': 0.0
        }
    }
}

# 如何获取智谱AI API密钥:
# 1. 访问 https://open.bigmodel.cn/
# 2. 注册并登录账号
# 3. 在控制台中创建API密钥
# 4. 将密钥填入上面的 'api_key' 字段

# 使用方法:
"""
from config.video_generation_config import COGVIDEOX_CONFIG
from src.models.video_engines.video_generation_service import VideoGenerationService

# 创建服务
service = VideoGenerationService(COGVIDEOX_CONFIG)

# 生成视频
result = await service.generate_video(
    prompt="一只可爱的小猫在花园里玩耍",
    duration=5.0
)
"""
