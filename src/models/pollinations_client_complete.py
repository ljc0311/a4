# -*- coding: utf-8 -*-
"""
Pollinations AI 客户端 - 完整修复版
- 修复提示词传递问题
- 移除项目管理器依赖
- 支持负面提示词合并
"""

import requests
import uuid
import os
import time
import tempfile
from urllib.parse import quote

class PollinationsClient:
    """Pollinations AI 客户端"""
    
    def __init__(self):
        self.base_url = "https://image.pollinations.ai"
        self.session = requests.Session()
        
        # 配置重试
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        adapter = HTTPAdapter(max_retries=Retry(total=3, backoff_factor=0.5))
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def generate_image(self, prompt: str, **kwargs):
        """生成单张图片
        
        Args:
            prompt: 图片描述提示词
            **kwargs: 可选参数
                - width: 图片宽度 (默认: 1024)
                - height: 图片高度 (默认: 1024)
                - model: 模型名称 (默认: flux)
                - negative_prompt: 负面提示词
                - output_dir: 输出目录
        
        Returns:
            生成的图片路径列表
        """
        print(f"=== 开始生成图片 ===")
        print(f"提示词: {prompt}")
        
        # 处理负面提示词
        if 'negative_prompt' in kwargs and kwargs['negative_prompt']:
            negative_prompt = kwargs['negative_prompt']
            prompt = f"{prompt}, avoid: {negative_prompt}"
            print(f"合并负面提示词: {negative_prompt}")
        
        # 构建参数
        params = {
            'prompt': prompt,
            'width': kwargs.get('width', 1024),
            'height': kwargs.get('height', 1024),
            'model': kwargs.get('model', 'flux'),
            'nologo': 'true'
        }
        
        # 构建URL
        url_parts = []
        # 构建URL
        prompt_encoded = quote(prompt, safe='')
        url = f"{self.base_url}/prompt/{prompt_encoded}"
        
        # 添加其他参数
        query_params = []
        for key, value in params.items():
            if key != 'prompt' and value is not None:
                encoded_value = quote(str(value), safe='')
                query_params.append(f"{key}={encoded_value}")
        
        if query_params:
            url += "?" + "&".join(query_params)
        
        print(f"请求URL: {url}")
        
        try:
            # 发送请求
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                print(f"请求失败: HTTP {response.status_code}")
                return [f"ERROR: HTTP {response.status_code}"]
            
            # 保存图片
            output_dir = kwargs.get('output_dir', tempfile.gettempdir())
            os.makedirs(output_dir, exist_ok=True)
            
            filename = f"pollinations_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"生成成功: {filepath}")
            return [filepath]
            
        except Exception as e:
            print(f"生成失败: {str(e)}")
            return [f"ERROR: {str(e)}"]

    def test_connection(self):
        """测试连接"""
        try:
            url = f"{self.base_url}/prompt/test?width=64&height=64"
            response = self.session.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False

if __name__ == "__main__":
    # 测试代码
    client = PollinationsClient()
    
    test_prompts = [
        "一只橘猫坐在窗台上，阳光温暖",
        "a cute orange cat on windowsill, warm sunlight",
        "现代办公室，程序员工作，自然光"
    ]
    
    print("开始测试Pollinations引擎...")
    
    for prompt in test_prompts:
        print(f"\n测试提示词: {prompt}")
        result = client.generate_image(prompt)
        print(f"结果: {result}")
