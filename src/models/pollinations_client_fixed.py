# -*- coding: utf-8 -*-
"""
Pollinations AI 客户端 - 修复版
- 提供免费的文生图API接口
- 支持图像和视频生成
- 无需API密钥，完全免费使用
- 修复项目管理器依赖问题
"""
import requests
from typing import Any, List, Dict, Optional
import uuid
import os
import time
from urllib.parse import quote
from src.utils.logger import logger

class PollinationsClient:
    """Pollinations AI 客户端类 - 修复版"""
    
    def __init__(self) -> None:
        self.base_url = "https://image.pollinations.ai"
        self.text_url = "https://text.pollinations.ai"
        self.session = requests.Session()
        
        # 配置会话以处理SSL连接问题
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        import urllib3
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })
        
        # 禁用SSL警告（如果需要的话）
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        logger.info("Pollinations AI 客户端初始化完成")

    def __del__(self) -> None:
        """析构函数，确保会话正确关闭"""
        if hasattr(self, 'session'):
            self.session.close()

    def generate_image(self, prompt: str, **kwargs: Any) -> List[str]:
        """生成单张图片 - 修复版
        
        Args:
            prompt: 图片描述提示词
            **kwargs: 可选参数
                - width: 图片宽度 (默认: 1024)
                - height: 图片高度 (默认: 1024)
                - seed: 随机种子 (可选)
                - model: 模型名称 (可选)
                - nologo: 是否去除水印 (默认: True)
                - output_dir: 输出目录 (可选，如果不提供则使用临时目录)
        
        Returns:
            生成的图片路径列表
        """
        logger.info(f"=== Pollinations AI 图片生成开始 ===")
        logger.info(f"提示词: {prompt}")
        
        # 处理负面提示词
        if 'negative_prompt' in kwargs and kwargs['negative_prompt']:
            negative_prompt = kwargs['negative_prompt']
            prompt = f"{prompt}, avoid: {negative_prompt}"
            logger.info(f"合并负面提示词: {negative_prompt}")
        
        # 默认参数
        params_dict = {
            'width': kwargs.get('width', 1024),
            'height': kwargs.get('height', 1024),
            'nologo': str(kwargs.get('nologo', True)).lower(),
            'model': kwargs.get('model', 'flux'),
            'enhance': str(kwargs.get('enhance', False)).lower(),
            'safe': str(kwargs.get('safe', True)).lower()
        }
        
        # 添加seed参数（如果提供）
        if 'seed' in kwargs and kwargs['seed'] is not None:
            params_dict['seed'] = kwargs['seed']
        
        # 添加private参数（如果提供）
        if 'private' in kwargs and kwargs['private'] is not None:
            params_dict['private'] = str(kwargs['private']).lower()
        
        # 添加prompt到参数
        params_dict['prompt'] = prompt
        
        try:
            # 构建URL
            url_parts = []
            for key, value in params_dict.items():
                if value is not None:
                    encoded_value = quote(str(value), safe='')
                    url_parts.append(f"{key}={encoded_value}")
            
            api_url = f"{self.base_url}/prompt"
            if url_parts:
                api_url += "?" + "&".join(url_parts)
            
            logger.info(f"API请求URL: {api_url}")
            
            # 发送请求
