#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vheer.com 代理捕获方案
使用 mitmproxy 捕获真实的 API 调用
"""

import asyncio
import json
import time
import os
from typing import Dict, List, Optional
from mitmproxy import http, options
from mitmproxy.tools.dump import DumpMaster
import threading
import queue
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VheerProxyCapture:
    """Vheer 代理捕获器"""
    
    def __init__(self):
        self.captured_requests = queue.Queue()
        self.api_calls = []
        self.proxy_thread = None
        self.master = None
        
    def request(self, flow: http.HTTPFlow) -> None:
        """处理HTTP请求"""
        try:
            # 只关注 vheer.com 的请求
            if "vheer.com" in flow.request.pretty_host:
                request_info = {
                    'method': flow.request.method,
                    'url': flow.request.pretty_url,
                    'headers': dict(flow.request.headers),
                    'content': flow.request.content.decode('utf-8', errors='ignore') if flow.request.content else '',
                    'timestamp': time.time()
                }
                
                # 检查是否是可能的API调用
                if any(keyword in flow.request.pretty_url.lower() for keyword in ['api', 'generate', 'create', 'submit']):
                    logger.info(f"捕获到API请求: {flow.request.method} {flow.request.pretty_url}")
                    self.captured_requests.put(request_info)
                    
        except Exception as e:
            logger.debug(f"处理请求时出错: {e}")
            
    def response(self, flow: http.HTTPFlow) -> None:
        """处理HTTP响应"""
        try:
            if "vheer.com" in flow.request.pretty_host:
                # 检查响应是否包含图像数据
                content_type = flow.response.headers.get('content-type', '')
                
                if 'image' in content_type or 'json' in content_type:
                    response_info = {
                        'status_code': flow.response.status_code,
                        'headers': dict(flow.response.headers),
                        'content_type': content_type,
                        'content_length': len(flow.response.content) if flow.response.content else 0,
                        'url': flow.request.pretty_url,
                        'timestamp': time.time()
                    }
                    
                    if 'json' in content_type:
                        try:
                            response_info['json_content'] = json.loads(flow.response.content.decode('utf-8'))
                        except:
                            pass
                            
                    logger.info(f"捕获到响应: {flow.response.status_code} {content_type}")
                    self.captured_requests.put(response_info)
                    
        except Exception as e:
            logger.debug(f"处理响应时出错: {e}")
            
    def start_proxy(self, port: int = 8080):
        """启动代理服务器"""
        try:
            opts = options.Options(listen_port=port)
            self.master = DumpMaster(opts)
            
            # 添加请求和响应处理器
            self.master.addons.add(self)
            
            logger.info(f"代理服务器启动在端口 {port}")
            
            # 在单独线程中运行代理
            def run_proxy():
                asyncio.run(self.master.run())
                
            self.proxy_thread = threading.Thread(target=run_proxy, daemon=True)
            self.proxy_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"启动代理服务器失败: {e}")
            return False
            
    def stop_proxy(self):
        """停止代理服务器"""
        if self.master:
            self.master.shutdown()
            
    def get_captured_data(self) -> List[Dict]:
        """获取捕获的数据"""
        captured_data = []
        
        while not self.captured_requests.empty():
            try:
                data = self.captured_requests.get_nowait()
                captured_data.append(data)
            except queue.Empty:
                break
                
        return captured_data
        
    def save_captured_data(self, filename: str = "vheer_captured_data.json"):
        """保存捕获的数据"""
        captured_data = self.get_captured_data()
        
        if captured_data:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(captured_data, f, indent=2, ensure_ascii=False, default=str)
                
            logger.info(f"保存了 {len(captured_data)} 条捕获数据到 {filename}")
            return True
        else:
            logger.warning("没有捕获到数据")
            return False

class VheerAPIReplicator:
    """Vheer API 复制器 - 基于捕获的数据复制API调用"""
    
    def __init__(self, captured_data_file: str):
        self.captured_data_file = captured_data_file
        self.api_template = None
        self.session = None
        
    async def load_captured_data(self):
        """加载捕获的数据"""
        try:
            with open(self.captured_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 分析数据，找到API调用模式
            api_requests = [item for item in data if item.get('method') in ['POST', 'PUT']]
            
            if api_requests:
                # 使用第一个POST请求作为模板
                self.api_template = api_requests[0]
                logger.info(f"找到API模板: {self.api_template['method']} {self.api_template['url']}")
                return True
            else:
                logger.warning("未找到API请求模板")
                return False
                
        except Exception as e:
            logger.error(f"加载捕获数据失败: {e}")
            return False
            
    async def replicate_api_call(self, prompt: str) -> Optional[str]:
        """复制API调用"""
        if not self.api_template:
            logger.error("没有API模板")
            return None
            
        try:
            import aiohttp
            
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            # 构建请求数据
            headers = self.api_template.get('headers', {})
            
            # 尝试解析原始请求内容
            original_content = self.api_template.get('content', '')
            
            if original_content:
                try:
                    # 尝试作为JSON解析
                    request_data = json.loads(original_content)
                    
                    # 替换提示词
                    for key in ['prompt', 'text', 'input', 'description']:
                        if key in request_data:
                            request_data[key] = prompt
                            break
                    else:
                        # 如果没找到已知字段，添加prompt字段
                        request_data['prompt'] = prompt
                        
                except json.JSONDecodeError:
                    # 如果不是JSON，尝试作为表单数据处理
                    request_data = {'prompt': prompt}
                    
            else:
                request_data = {'prompt': prompt}
                
            logger.info(f"复制API调用: {self.api_template['url']}")
            logger.info(f"请求数据: {request_data}")
            
            # 发送请求
            async with self.session.request(
                method=self.api_template['method'],
                url=self.api_template['url'],
                json=request_data,
                headers=headers
            ) as response:
                
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    
                    if 'image' in content_type:
                        # 直接返回图像数据
                        image_data = await response.read()
                        return self._save_image_data(image_data, prompt)
                    elif 'json' in content_type:
                        # 解析JSON响应
                        result = await response.json()
                        return self._extract_image_from_json(result, prompt)
                    else:
                        logger.warning(f"未知的响应类型: {content_type}")
                        
                else:
                    logger.warning(f"API调用失败: {response.status}")
                    
        except Exception as e:
            logger.error(f"复制API调用失败: {e}")
            
        return None
        
    def _save_image_data(self, image_data: bytes, prompt: str) -> str:
        """保存图像数据"""
        try:
            os.makedirs("temp/vheer_replicated", exist_ok=True)
            
            timestamp = int(time.time())
            filename = f"vheer_replicated_{timestamp}.png"
            filepath = os.path.join("temp/vheer_replicated", filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_data)
                
            logger.info(f"图像保存成功: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存图像失败: {e}")
            return None
            
    def _extract_image_from_json(self, json_data: Dict, prompt: str) -> Optional[str]:
        """从JSON响应中提取图像"""
        try:
            # 尝试不同的字段名
            url_fields = ['image_url', 'url', 'imageUrl', 'src', 'data.url', 'result.url']
            
            for field in url_fields:
                if '.' in field:
                    # 处理嵌套字段
                    parts = field.split('.')
                    value = json_data
                    for part in parts:
                        value = value.get(part)
                        if not value:
                            break
                else:
                    value = json_data.get(field)
                    
                if value and isinstance(value, str):
                    # 下载图像
                    return self._download_image_from_url(value, prompt)
                    
        except Exception as e:
            logger.error(f"从JSON提取图像失败: {e}")
            
        return None
        
    def _download_image_from_url(self, url: str, prompt: str) -> Optional[str]:
        """从URL下载图像"""
        try:
            import requests
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            return self._save_image_data(response.content, prompt)
            
        except Exception as e:
            logger.error(f"从URL下载图像失败: {e}")
            return None
            
    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()

def print_usage_instructions():
    """打印使用说明"""
    print("""
=== Vheer.com 高级集成方案使用说明 ===

方案1: 浏览器自动化 (推荐)
1. 运行: python vheer_advanced_integration.py
2. 程序会自动打开浏览器，访问 Vheer 网站
3. 自动输入提示词并点击生成按钮
4. 自动提取和下载生成的图像

方案2: 代理捕获 (高级用户)
1. 首先运行代理捕获器
2. 配置浏览器使用代理 (127.0.0.1:8080)
3. 手动在浏览器中操作 Vheer 网站生成图像
4. 代理会捕获所有网络请求
5. 基于捕获的数据复制API调用

安装依赖:
pip install selenium requests mitmproxy aiohttp

注意事项:
- 需要安装 Chrome 浏览器和 ChromeDriver
- 浏览器自动化方案更稳定，推荐使用
- 代理方案需要手动配置，但能获得真实的API调用数据
- 请遵守网站的使用条款和速率限制

开始测试:
python vheer_advanced_integration.py
""")

if __name__ == "__main__":
    print_usage_instructions()
