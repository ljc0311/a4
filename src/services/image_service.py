#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像生成服务
统一的图像生成服务，支持ComfyUI、Pollinations等多种提供商
"""

import json
import aiohttp
import asyncio
import base64
import io
from typing import Dict, List, Optional, Any, Union
from PIL import Image

from src.utils.logger import logger
from src.core.service_base import ServiceBase, ServiceResult
from src.core.api_manager import APIManager, APIConfig, APIType

class ImageService(ServiceBase):
    """图像生成服务类"""
    
    def __init__(self, api_manager: APIManager):
        super().__init__(api_manager, "图像生成服务")
        
        # 从配置管理器获取图像配置
        self.image_config = api_manager.config_manager.get_image_config() if hasattr(api_manager, 'config_manager') else {}
        
        # 默认参数
        self.default_params = {
            'width': 1024,
            'height': 1024,
            'steps': 20,
            'cfg_scale': 7.0,
            'sampler': 'DPM++ 2M Karras',
            'seed': -1
        }
        
        # 风格预设
        self.style_presets = {
            '电影风格': 'cinematic, dramatic lighting, film grain, 4k, photorealistic',
            '动漫风格': 'anime style, cel shading, vibrant colors, clean lines',
            '吉卜力风格': 'studio ghibli style, soft colors, whimsical, detailed background',
            '赛博朋克风格': 'cyberpunk, neon lights, futuristic city, dark atmosphere',
            '水彩插画风格': 'watercolor painting, soft brush strokes, pastel colors',
            '像素风格': 'pixel art, 8-bit, retro gaming style, low resolution',
            '写实摄影风格': 'photorealistic, natural lighting, high detail, 4k photography'
        }
    
    def get_api_type(self) -> APIType:
        return APIType.IMAGE_GENERATION
    
    def get_available_providers(self) -> List[str]:
        """获取可用的图像生成提供商"""
        if hasattr(self.api_manager, 'config_manager'):
            return self.api_manager.config_manager.get_image_providers()
        return ['pollinations']  # 默认提供商
    
    async def _execute_request(self, api_config: APIConfig, **kwargs) -> ServiceResult:
        """执行图像生成API请求"""
        try:
            prompt = kwargs.get('prompt', '')
            negative_prompt = kwargs.get('negative_prompt', '')
            style = kwargs.get('style', '写实摄影风格')
            
            if not prompt:
                return ServiceResult(success=False, error="提示词不能为空")
            
            # 应用风格预设
            if style in self.style_presets:
                prompt = f"{prompt}, {self.style_presets[style]}"
            
            # 根据不同提供商生成图像
            if api_config.provider.lower() == 'comfyui':
                response = await self._call_comfyui_api(api_config, prompt, negative_prompt, **kwargs)
            elif api_config.provider.lower() == 'pollinations':
                response = await self._call_pollinations_api(api_config, prompt, **kwargs)
            elif api_config.provider.lower() == 'stability':
                response = await self._call_stability_api(api_config, prompt, negative_prompt, **kwargs)
            elif api_config.provider.lower() == 'cogview_3_flash':
                response = await self._call_cogview_api(api_config, prompt, **kwargs)
            else:
                return ServiceResult(success=False, error=f"不支持的提供商: {api_config.provider}")
            
            return ServiceResult(
                success=True,
                data=response,
                metadata={
                    'provider': api_config.provider,
                    'prompt': prompt,
                    'style': style
                }
            )
            
        except Exception as e:
            logger.error(f"图像生成API请求失败: {e}")
            return ServiceResult(success=False, error=str(e))
    
    async def _call_comfyui_api(self, api_config: APIConfig, prompt: str, negative_prompt: str, **kwargs) -> Dict:
        """调用ComfyUI API"""
        # 合并默认参数和用户参数
        params = {**self.default_params, **kwargs}
        
        # 构建ComfyUI工作流
        workflow = {
            "3": {
                "inputs": {
                    "seed": params.get('seed', -1),
                    "steps": params.get('steps', 20),
                    "cfg": params.get('cfg_scale', 7.0),
                    "sampler_name": params.get('sampler', 'DPM++ 2M Karras'),
                    "scheduler": "karras",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "4": {
                "inputs": {
                    "ckpt_name": params.get('model_name', 'sd_xl_base_1.0.safetensors')
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "5": {
                "inputs": {
                    "width": params.get('width', 1024),
                    "height": params.get('height', 1024),
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        }
        
        # 发送请求到ComfyUI
        async with aiohttp.ClientSession() as session:
            # 提交工作流
            async with session.post(
                f"{api_config.api_url}/prompt",
                json={"prompt": workflow},
                timeout=aiohttp.ClientTimeout(total=300)  # 5分钟超时
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"ComfyUI请求失败 (状态码: {response.status}): {error_text}")
                
                result = await response.json()
                prompt_id = result['prompt_id']
            
            # 轮询结果
            for _ in range(60):  # 最多等待5分钟
                await asyncio.sleep(5)
                
                async with session.get(f"{api_config.api_url}/history/{prompt_id}") as response:
                    if response.status == 200:
                        history = await response.json()
                        if prompt_id in history and history[prompt_id].get('status', {}).get('completed', False):
                            # 获取生成的图像
                            outputs = history[prompt_id]['outputs']
                            if '9' in outputs and 'images' in outputs['9']:
                                image_info = outputs['9']['images'][0]
                                image_url = f"{api_config.api_url}/view?filename={image_info['filename']}&subfolder={image_info.get('subfolder', '')}&type={image_info.get('type', 'output')}"
                                
                                return {
                                    'image_url': image_url,
                                    'filename': image_info['filename'],
                                    'prompt_id': prompt_id
                                }
            
            raise Exception("ComfyUI生成超时")
    
    async def _call_pollinations_api(self, api_config: APIConfig, prompt: str, **kwargs) -> Dict:
        """调用Pollinations API"""
        params = {
            'prompt': prompt,
            'width': kwargs.get('width', 1024),
            'height': kwargs.get('height', 1024),
            'seed': kwargs.get('seed', -1),
            'model': kwargs.get('model_name', 'flux')
        }
        
        # 构建URL
        url = f"{api_config.api_url}/prompt/{prompt}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    image_data = await response.read()
                    
                    # 将图像数据转换为base64
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    
                    return {
                        'image_data': image_base64,
                        'image_url': str(response.url),
                        'format': 'base64'
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Pollinations请求失败 (状态码: {response.status}): {error_text}")
    
    async def _call_stability_api(self, api_config: APIConfig, prompt: str, negative_prompt: str, **kwargs) -> Dict:
        """调用Stability AI API"""
        headers = {
            'Authorization': f'Bearer {api_config.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'text_prompts': [
                {'text': prompt, 'weight': 1.0}
            ],
            'cfg_scale': kwargs.get('cfg_scale', 7.0),
            'height': kwargs.get('height', 1024),
            'width': kwargs.get('width', 1024),
            'samples': 1,
            'steps': kwargs.get('steps', 20)
        }
        
        if negative_prompt:
            data['text_prompts'].append({'text': negative_prompt, 'weight': -1.0})
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_config.api_url}/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    image_base64 = result['artifacts'][0]['base64']
                    
                    return {
                        'image_data': image_base64,
                        'format': 'base64',
                        'seed': result['artifacts'][0].get('seed')
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Stability AI请求失败 (状态码: {response.status}): {error_text}")

    async def _call_cogview_api(self, api_config: APIConfig, prompt: str, **kwargs) -> Dict:
        """调用CogView-3 Flash API"""
        headers = {
            'Authorization': f'Bearer {api_config.api_key}',
            'Content-Type': 'application/json'
        }

        # 支持的尺寸映射
        width = kwargs.get('width', 1024)
        height = kwargs.get('height', 1024)
        size_mapping = {
            (1024, 1024): "1024x1024",
            (768, 1344): "768x1344",
            (864, 1152): "864x1152",
            (1344, 768): "1344x768",
            (1152, 864): "1152x864",
            (1440, 720): "1440x720",
            (720, 1440): "720x1440"
        }

        target_size = (width, height)
        if target_size in size_mapping:
            size = size_mapping[target_size]
        else:
            size = "1024x1024"
            logger.warning(f"不支持的尺寸 {target_size}，使用默认尺寸 1024x1024")

        data = {
            'model': 'cogview-3-flash',
            'prompt': prompt,
            'size': size,
            'n': 1,
            'response_format': 'b64_json'
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://open.bigmodel.cn/api/paas/v4/images/generations",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if 'data' in result and len(result['data']) > 0:
                        image_data = result['data'][0]
                        if 'b64_json' in image_data:
                            return {
                                'image_data': image_data['b64_json'],
                                'format': 'base64'
                            }
                        else:
                            raise Exception("响应中没有找到b64_json数据")
                    else:
                        raise Exception("响应格式错误，没有找到data字段")
                else:
                    error_text = await response.text()
                    raise Exception(f"CogView-3 Flash请求失败 (状态码: {response.status}): {error_text}")

    async def generate_image(self, prompt: str, style: str = "写实摄影风格",
                           negative_prompt: str = "", provider: str = None, **kwargs) -> ServiceResult:
        """生成单张图像"""
        return await self.execute(
            provider=provider,
            prompt=prompt,
            negative_prompt=negative_prompt,
            style=style,
            **kwargs
        )
    
    async def generate_batch_images(self, prompts: List[str], style: str = "写实摄影风格",
                                  negative_prompt: str = "", provider: str = None, **kwargs) -> List[ServiceResult]:
        """批量生成图像"""
        tasks = []
        for prompt in prompts:
            task = self.generate_image(
                prompt=prompt,
                style=style,
                negative_prompt=negative_prompt,
                provider=provider,
                **kwargs
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ServiceResult(
                    success=False,
                    error=str(result),
                    metadata={'prompt_index': i}
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def image_to_image(self, prompt: str, init_image: Union[str, bytes], 
                           strength: float = 0.7, style: str = "写实摄影风格",
                           provider: str = None, **kwargs) -> ServiceResult:
        """图像到图像生成"""
        # 处理输入图像
        if isinstance(init_image, str):
            # 如果是文件路径，读取图像
            with open(init_image, 'rb') as f:
                image_data = f.read()
        else:
            image_data = init_image
        
        # 转换为base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        return await self.execute(
            provider=provider,
            prompt=prompt,
            init_image=image_base64,
            strength=strength,
            style=style,
            **kwargs
        )
    
    def get_available_styles(self) -> List[str]:
        """获取可用的风格列表"""
        return list(self.style_presets.keys())
    
    def add_style_preset(self, name: str, prompt_suffix: str):
        """添加风格预设"""
        self.style_presets[name] = prompt_suffix
        logger.info(f"已添加风格预设: {name}")
    
    def remove_style_preset(self, name: str):
        """移除风格预设"""
        if name in self.style_presets:
            del self.style_presets[name]
            logger.info(f"已移除风格预设: {name}")