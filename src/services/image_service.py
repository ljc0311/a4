#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像生成服务
统一的图像生成服务，支持ComfyUI、Pollinations等多种提供商
优化版本：支持异步处理、内存管理、连接池等
"""

import json
import aiohttp
import asyncio
import base64
import io
import time
from typing import Dict, List, Optional, Any, Union
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from src.utils.logger import logger
from src.core.service_base import ServiceBase, ServiceResult
from src.core.api_manager import APIManager, APIConfig, APIType
from src.utils.memory_optimizer import memory_manager, image_memory_manager, monitor_memory

class ImageService(ServiceBase):
    """图像生成服务类 - 优化版本"""
    
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
        
        # 异步处理优化
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(3)  # 限制并发请求数
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ImageService")
        
        # 请求队列和批处理
        self.request_queue = asyncio.Queue(maxsize=50)
        self.batch_size = 5
        self.batch_timeout = 2.0  # 批处理超时时间
        
        # 注册内存清理回调
        memory_manager.register_cleanup_callback(self._cleanup_resources)
        
        # 批处理任务将在需要时启动
        self._batch_processor_task = None
    
    def get_api_type(self) -> APIType:
        return APIType.IMAGE_GENERATION
    
    @asynccontextmanager
    async def get_session(self):
        """获取或创建HTTP会话的异步上下文管理器"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=20,  # 总连接池大小
                limit_per_host=5,  # 每个主机的连接数
                ttl_dns_cache=300,  # DNS缓存5分钟
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(
                total=120,  # 总超时时间
                connect=10,  # 连接超时
                sock_read=60  # 读取超时
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'AI-Video-Generator/2.0',
                    'Accept': 'application/json, image/*'
                }
            )
            
            logger.info("创建新的HTTP会话")
        
        try:
            yield self.session
        except Exception as e:
            logger.error(f"HTTP会话使用异常: {e}")
            # 如果会话出错，关闭并重置
            if self.session and not self.session.closed:
                await self.session.close()
            self.session = None
            raise
    
    def _ensure_batch_processor(self):
        """确保批处理器正在运行"""
        try:
            if self._batch_processor_task is None or self._batch_processor_task.done():
                self._batch_processor_task = asyncio.create_task(self._batch_processor())
        except RuntimeError:
            # 如果没有运行的事件循环，跳过批处理器启动
            logger.debug("没有运行的事件循环，跳过批处理器启动")
    
    async def _batch_processor(self):
        """批处理请求处理器"""
        batch = []
        last_batch_time = time.time()
        
        while True:
            try:
                # 等待新请求或超时
                try:
                    request = await asyncio.wait_for(
                        self.request_queue.get(), 
                        timeout=self.batch_timeout
                    )
                    batch.append(request)
                except asyncio.TimeoutError:
                    # 超时，处理当前批次
                    pass
                
                current_time = time.time()
                should_process = (
                    len(batch) >= self.batch_size or 
                    (batch and current_time - last_batch_time >= self.batch_timeout)
                )
                
                if should_process and batch:
                    await self._process_batch(batch)
                    batch.clear()
                    last_batch_time = current_time
                
            except Exception as e:
                logger.error(f"批处理器异常: {e}")
                await asyncio.sleep(1)
    
    async def _process_batch(self, batch: List[Dict]):
        """处理批次请求"""
        if not batch:
            return
        
        logger.info(f"处理批次请求: {len(batch)} 个")
        
        # 按提供商分组
        provider_groups = {}
        for request in batch:
            provider = request.get('provider', 'default')
            if provider not in provider_groups:
                provider_groups[provider] = []
            provider_groups[provider].append(request)
        
        # 并行处理不同提供商的请求
        tasks = []
        for provider, requests in provider_groups.items():
            task = asyncio.create_task(self._process_provider_batch(provider, requests))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_provider_batch(self, provider: str, requests: List[Dict]):
        """处理特定提供商的批次请求"""
        for request in requests:
            try:
                future = request['future']
                api_config = request['api_config']
                kwargs = request['kwargs']
                
                result = await self._execute_single_request(api_config, **kwargs)
                future.set_result(result)
                
            except Exception as e:
                logger.error(f"批处理请求失败: {e}")
                if not future.done():
                    future.set_exception(e)
    
    def _cleanup_resources(self):
        """清理资源的回调函数"""
        try:
            # 取消批处理任务
            if hasattr(self, '_batch_processor_task') and self._batch_processor_task and not self._batch_processor_task.done():
                self._batch_processor_task.cancel()
            
            # 清理HTTP会话
            if hasattr(self, 'session') and self.session and not self.session.closed:
                try:
                    asyncio.create_task(self.session.close())
                except RuntimeError:
                    # 如果没有运行的事件循环，直接设置为None
                    pass
                self.session = None
            
            # 清理线程池
            if hasattr(self, 'executor') and self.executor:
                self.executor.shutdown(wait=False)
            
            logger.info("图像服务资源清理完成")
            
        except Exception as e:
            logger.error(f"清理图像服务资源失败: {e}")
    
    def get_available_providers(self) -> List[str]:
        """获取可用的图像生成提供商"""
        if hasattr(self.api_manager, 'config_manager'):
            return self.api_manager.config_manager.get_image_providers()
        return ['pollinations']  # 默认提供商
    
    async def _execute_request(self, api_config: APIConfig, **kwargs) -> ServiceResult:
        """执行图像生成API请求 - 优化版本"""
        try:
            # 确保批处理器运行
            self._ensure_batch_processor()
            
            prompt = kwargs.get('prompt', '')
            negative_prompt = kwargs.get('negative_prompt', '')
            style = kwargs.get('style', '写实摄影风格')
            
            if not prompt:
                return ServiceResult(success=False, error="提示词不能为空")
            
            # 检查缓存
            cache_key = f"{hash(prompt)}_{style}_{api_config.provider}"
            cached_image = image_memory_manager.get_image_from_cache(cache_key)
            if cached_image:
                logger.info(f"使用缓存图像: {cache_key}")
                return ServiceResult(
                    success=True,
                    data={'image_data': cached_image, 'format': 'base64', 'cached': True},
                    metadata={'provider': api_config.provider, 'prompt': prompt, 'style': style}
                )
            
            # 应用风格预设 - 智能处理避免重复
            if style in self.style_presets:
                style_preset = self.style_presets[style]
                if not self._contains_style_keywords(prompt, style):
                    prompt = f"{prompt}, {style_preset}"
                    logger.debug(f"为提示词添加风格预设: {style}")
            
            # 使用优化的请求执行
            response = await self._execute_single_request(api_config, prompt=prompt, 
                                                        negative_prompt=negative_prompt, **kwargs)
            
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
    
    async def _execute_single_request(self, api_config: APIConfig, **kwargs) -> Dict:
        """执行单个API请求"""
        prompt = kwargs.get('prompt', '')
        negative_prompt = kwargs.get('negative_prompt', '')
        
        # 根据不同提供商生成图像
        if api_config.provider.lower() == 'comfyui':
            return await self._call_comfyui_api(api_config, prompt, negative_prompt, **kwargs)
        elif api_config.provider.lower() == 'pollinations':
            return await self._call_pollinations_api(api_config, prompt, **kwargs)
        elif api_config.provider.lower() == 'stability':
            return await self._call_stability_api(api_config, prompt, negative_prompt, **kwargs)
        elif api_config.provider.lower() == 'cogview_3_flash':
            return await self._call_cogview_api(api_config, prompt, **kwargs)
        elif api_config.provider.lower() == 'vheer':
            return await self._call_vheer_api(api_config, prompt, **kwargs)
        else:
            raise ValueError(f"不支持的提供商: {api_config.provider}")
    
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
        """调用Pollinations API - 优化版本"""
        params = {
            'prompt': prompt,
            'width': kwargs.get('width', 1024),
            'height': kwargs.get('height', 1024),
            'seed': kwargs.get('seed', -1),
            'model': kwargs.get('model_name', 'flux')
        }
        
        # 构建URL
        url = f"{api_config.api_url}/prompt/{prompt}"
        
        async with self.get_session() as session:
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        # 使用流式读取，避免大图像占用过多内存
                        image_data = bytearray()
                        async for chunk in response.content.iter_chunked(8192):
                            image_data.extend(chunk)
                            
                            # 检查内存压力
                            if len(image_data) > 50 * 1024 * 1024:  # 50MB限制
                                raise Exception("图像数据过大，超过50MB限制")
                        
                        # 将图像数据转换为base64
                        image_base64 = base64.b64encode(image_data).decode('utf-8')
                        
                        return {
                            'image_data': image_base64,
                            'image_url': str(response.url),
                            'format': 'base64',
                            'size_mb': len(image_data) / 1024 / 1024
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"Pollinations请求失败 (状态码: {response.status}): {error_text}")
                        
            except asyncio.TimeoutError:
                raise Exception("Pollinations API请求超时")
            except aiohttp.ClientError as e:
                raise Exception(f"Pollinations API网络错误: {e}")
    
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

    async def _call_vheer_api(self, api_config: APIConfig, prompt: str, **kwargs) -> Dict:
        """调用Vheer API"""
        try:
            # 使用图像生成引擎管理器
            from src.models.image_generation_service import ImageGenerationService
            from src.models.image_engine_base import GenerationConfig

            # 创建生成配置
            config = GenerationConfig(
                prompt=prompt,
                width=kwargs.get('width', 1024),
                height=kwargs.get('height', 1024),
                batch_size=1,
                workflow_id=kwargs.get('workflow_id', 'vheer_api_call')
            )

            # 创建图像生成服务
            image_service = ImageGenerationService()
            await image_service.initialize()

            # 生成图像
            result = await image_service.generate_image(
                prompt=prompt,
                config=config.__dict__,
                engine_preference='vheer'
            )

            if result.success and result.image_paths:
                # 读取生成的图像文件并转换为base64
                import base64
                with open(result.image_paths[0], 'rb') as f:
                    image_data = f.read()
                    b64_data = base64.b64encode(image_data).decode('utf-8')

                return {
                    'image_data': b64_data,
                    'format': 'base64',
                    'image_path': result.image_paths[0]
                }
            else:
                raise Exception(f"Vheer图像生成失败: {result.error_message}")

        except Exception as e:
            logger.error(f"Vheer API调用失败: {e}")
            raise Exception(f"Vheer API调用失败: {e}")

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
    
    @monitor_memory("批量图像生成")
    async def generate_batch_images(self, prompts: List[str], style: str = "写实摄影风格",
                                  negative_prompt: str = "", provider: str = None, 
                                  progress_callback=None, **kwargs) -> List[ServiceResult]:
        """优化的批量生成图像"""
        if not prompts:
            return []
        
        logger.info(f"开始批量生成 {len(prompts)} 张图像")
        
        # 检查内存压力
        if memory_manager.check_memory_pressure():
            logger.warning("内存压力过大，触发清理")
            memory_manager.force_cleanup()
        
        # 使用信号量限制并发数
        async def generate_with_semaphore(i, prompt):
            async with self.semaphore:
                try:
                    if progress_callback:
                        progress_callback(i / len(prompts), f"生成第 {i+1}/{len(prompts)} 张图像")
                    
                    result = await self.generate_image(
                        prompt=prompt,
                        style=style,
                        negative_prompt=negative_prompt,
                        provider=provider,
                        **kwargs
                    )
                    
                    # 检查结果中的图像数据并缓存
                    if result.success and 'image_data' in result.data:
                        cache_key = f"{hash(prompt)}_{style}_{provider}"
                        image_memory_manager.add_image_to_cache(cache_key, result.data['image_data'])
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"生成第 {i+1} 张图像失败: {e}")
                    return ServiceResult(
                        success=False,
                        error=str(e),
                        metadata={'prompt_index': i, 'prompt': prompt}
                    )
        
        # 分批处理，避免创建过多并发任务
        batch_size = 10
        all_results = []
        
        for batch_start in range(0, len(prompts), batch_size):
            batch_end = min(batch_start + batch_size, len(prompts))
            batch_prompts = prompts[batch_start:batch_end]
            
            # 创建当前批次的任务
            batch_tasks = [
                generate_with_semaphore(batch_start + i, prompt) 
                for i, prompt in enumerate(batch_prompts)
            ]
            
            # 等待当前批次完成
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 处理异常结果
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    all_results.append(ServiceResult(
                        success=False,
                        error=str(result),
                        metadata={'prompt_index': batch_start + i}
                    ))
                else:
                    all_results.append(result)
            
            # 批次间短暂休息，避免过载
            if batch_end < len(prompts):
                await asyncio.sleep(0.1)
        
        success_count = sum(1 for r in all_results if r.success)
        logger.info(f"批量图像生成完成: 成功 {success_count}/{len(prompts)}")
        
        if progress_callback:
            progress_callback(1.0, f"批量生成完成: {success_count}/{len(prompts)}")
        
        return all_results
    
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

    def _contains_style_keywords(self, prompt: str, style: str) -> bool:
        """检查提示词中是否已包含特定风格的关键词"""
        style_keywords = {
            '电影风格': ['电影', 'cinematic', '胶片', 'film', '写实', 'photorealistic'],
            '动漫风格': ['动漫', 'anime', '卡通', 'cartoon', '二次元'],
            '吉卜力风格': ['吉卜力', 'ghibli', '宫崎骏', 'miyazaki'],  # 移除'奇幻'避免误判
            '赛博朋克风格': ['赛博朋克', 'cyberpunk', '霓虹', 'neon', '未来'],
            '水彩插画风格': ['水彩', 'watercolor', '插画', 'illustration', '手绘'],
            '像素风格': ['像素', 'pixel', '8位', '8-bit', '复古'],
            '写实摄影风格': ['写实', 'photorealistic', '摄影', 'photography', '真实']
        }

        if style not in style_keywords:
            return False

        prompt_lower = prompt.lower()
        keywords = style_keywords[style]

        # 检查是否包含任何关键词
        for keyword in keywords:
            if keyword.lower() in prompt_lower:
                return True

        return False
    
    def add_style_preset(self, name: str, prompt_suffix: str):
        """添加风格预设"""
        self.style_presets[name] = prompt_suffix
        logger.info(f"已添加风格预设: {name}")
    
    def remove_style_preset(self, name: str):
        """移除风格预设"""
        if name in self.style_presets:
            del self.style_presets[name]
            logger.info(f"已移除风格预设: {name}")