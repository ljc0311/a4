"""
Vheer.com 图像生成引擎实现
通过逆向工程 Vheer 网站的 API 调用来实现图像生成
"""

import asyncio
import aiohttp
import requests
import os
import time
import json
import base64
import uuid
from typing import List, Dict, Optional, Callable
from ..image_engine_base import (
    ImageGenerationEngine, EngineType, EngineStatus, 
    GenerationConfig, GenerationResult, EngineInfo, ConfigConverter
)
from src.utils.logger import logger


class VheerEngine(ImageGenerationEngine):
    """Vheer.com 引擎实现"""
    
    def __init__(self, config: Dict = None):
        super().__init__(EngineType.VHEER)
        self.config = config or {}
        self.base_url = "https://vheer.com"
        self.api_url = None  # 将在初始化时发现
        self.output_dir = self.config.get('output_dir', 'temp/image_cache')
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        # 项目相关信息
        self.project_manager = None
        self.current_project_name = None
        
    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            # 动态获取输出目录
            self.output_dir = self._get_output_dir()
            
            # 创建aiohttp会话
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=60)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            )
            
            # 发现API端点
            if await self._discover_api_endpoints():
                # 测试连接
                if await self.test_connection():
                    self.status = EngineStatus.IDLE
                    logger.info("Vheer引擎初始化成功")
                    return True
                else:
                    self.status = EngineStatus.ERROR
                    logger.error("Vheer引擎连接测试失败")
                    return False
            else:
                self.status = EngineStatus.ERROR
                logger.error("Vheer引擎API端点发现失败")
                return False
                
        except Exception as e:
            self.status = EngineStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Vheer引擎初始化失败: {e}")
            return False
    
    async def _discover_api_endpoints(self) -> bool:
        """发现API端点"""
        try:
            # 访问主页面获取可能的API端点信息
            async with self.session.get(f"{self.base_url}/app/text-to-image") as response:
                if response.status == 200:
                    # 这里需要分析页面内容或网络请求来发现实际的API端点
                    # 暂时使用推测的端点
                    self.api_url = f"{self.base_url}/api/generate"  # 推测的API端点
                    logger.info(f"发现API端点: {self.api_url}")
                    return True
                else:
                    logger.error(f"无法访问Vheer主页: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"发现API端点失败: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self.session:
                return False
                
            # 发送简单的测试请求到主页
            async with self.session.get(f"{self.base_url}") as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Vheer连接测试失败: {e}")
            return False
    
    def set_project_info(self, project_manager=None, current_project_name=None):
        """设置项目信息"""
        self.project_manager = project_manager
        self.current_project_name = current_project_name
        logger.info(f"Vheer引擎设置项目信息: project_manager={project_manager is not None}, current_project_name={current_project_name}")
    
    def _get_output_dir(self, project_manager=None, current_project_name=None) -> str:
        """获取输出目录"""
        try:
            # 优先使用传入的项目管理器
            if project_manager and current_project_name:
                try:
                    project_root = project_manager.get_current_project_path()
                    if project_root:
                        output_dir = os.path.join(project_root, 'images', 'vheer')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"使用项目输出目录: {output_dir}")
                        return output_dir
                except AttributeError:
                    if hasattr(project_manager, 'current_project') and project_manager.current_project:
                        project_root = project_manager.current_project.get('project_dir')
                        if project_root:
                            output_dir = os.path.join(project_root, 'images', 'vheer')
                            os.makedirs(output_dir, exist_ok=True)
                            logger.info(f"使用项目输出目录: {output_dir}")
                            return output_dir

            # 尝试使用实例变量
            if self.project_manager:
                try:
                    project_root = self.project_manager.get_current_project_path()
                    if project_root:
                        output_dir = os.path.join(project_root, 'images', 'vheer')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"使用项目输出目录: {output_dir}")
                        return output_dir
                    else:
                        logger.info("当前没有加载项目，使用默认目录")
                except AttributeError:
                    if hasattr(self.project_manager, 'current_project') and self.project_manager.current_project:
                        project_root = self.project_manager.current_project.get('project_dir')
                        if project_root:
                            output_dir = os.path.join(project_root, 'images', 'vheer')
                            os.makedirs(output_dir, exist_ok=True)
                            logger.info(f"使用项目输出目录: {output_dir}")
                            return output_dir
                except Exception as e:
                    logger.warning(f"获取项目路径失败: {e}，使用默认目录")

        except Exception as e:
            logger.warning(f"无法获取项目目录: {e}")

        # 无项目时使用temp/image_cache
        output_dir = os.path.join(os.getcwd(), 'temp', 'image_cache', 'vheer')
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"使用默认输出目录: {output_dir}")
        return output_dir

    async def generate(self, config: GenerationConfig,
                      progress_callback: Optional[Callable] = None,
                      project_manager=None, current_project_name=None) -> GenerationResult:
        """生成图像"""
        # 设置项目信息
        if project_manager and current_project_name:
            self.project_manager = project_manager
            self.current_project_name = current_project_name
            # 更新输出目录
            self.output_dir = self._get_output_dir()

        start_time = time.time()
        self.status = EngineStatus.BUSY

        try:
            if progress_callback:
                progress_callback("准备Vheer生成请求...")

            # 转换配置
            vheer_config = self._convert_config(config)

            # 生成图像
            image_paths = []
            for i in range(config.batch_size):
                if progress_callback:
                    progress_callback(f"生成第 {i+1}/{config.batch_size} 张图像...")

                image_path = await self._generate_single_image(vheer_config, i)
                if image_path:
                    image_paths.append(image_path)
                else:
                    logger.warning(f"第 {i+1} 张图像生成失败")

                # 添加延迟避免请求过于频繁
                if i < config.batch_size - 1:
                    await asyncio.sleep(2)

            generation_time = time.time() - start_time
            success = len(image_paths) > 0

            # 更新统计
            self.update_stats(success, 0.0, "" if success else "部分或全部图像生成失败")

            result = GenerationResult(
                success=success,
                image_paths=image_paths,
                generation_time=generation_time,
                cost=0.0,  # Vheer免费
                engine_type=self.engine_type,
                metadata={
                    'total_requested': config.batch_size,
                    'total_generated': len(image_paths),
                    'config': vheer_config
                }
            )

            if not success:
                result.error_message = f"仅生成了 {len(image_paths)}/{config.batch_size} 张图像"

            return result

        except Exception as e:
            error_msg = f"Vheer生成失败: {e}"
            logger.error(error_msg)
            self.update_stats(False, 0.0, error_msg)

            return GenerationResult(
                success=False,
                error_message=error_msg,
                engine_type=self.engine_type
            )
        finally:
            self.status = EngineStatus.IDLE

    def _convert_config(self, config: GenerationConfig) -> Dict:
        """转换配置为Vheer格式"""
        workflow_id = config.custom_params.get('workflow_id', f'vheer_{uuid.uuid4().hex[:8]}')
        return {
            'prompt': config.prompt,
            'width': config.width,
            'height': config.height,
            'aspect_ratio': self._get_aspect_ratio(config.width, config.height),
            'model': 'quality',  # Vheer的默认模型
            'workflow_id': workflow_id
        }

    def _get_aspect_ratio(self, width: int, height: int) -> str:
        """获取宽高比字符串"""
        ratio_map = {
            (1, 1): "1:1",
            (1, 2): "1:2",
            (2, 1): "2:1",
            (2, 3): "2:3",
            (3, 2): "3:2",
            (9, 16): "9:16",
            (16, 9): "16:9"
        }

        # 计算最接近的比例
        target_ratio = width / height
        best_match = "1:1"
        min_diff = float('inf')

        for (w, h), ratio_str in ratio_map.items():
            ratio = w / h
            diff = abs(ratio - target_ratio)
            if diff < min_diff:
                min_diff = diff
                best_match = ratio_str

        return best_match

    async def _generate_single_image(self, config: Dict, index: int) -> Optional[str]:
        """生成单张图像"""
        try:
            # 方法1: 尝试直接API调用
            image_path = await self._try_direct_api_call(config, index)
            if image_path:
                return image_path

            # 方法2: 尝试模拟浏览器请求
            image_path = await self._try_browser_simulation(config, index)
            if image_path:
                return image_path

            logger.error("所有生成方法都失败了")
            return None

        except Exception as e:
            logger.error(f"生成单张图像失败: {e}")
            return None

    async def _try_direct_api_call(self, config: Dict, index: int) -> Optional[str]:
        """尝试直接API调用"""
        try:
            # 构建请求数据
            request_data = {
                'prompt': config['prompt'],
                'aspect_ratio': config['aspect_ratio'],
                'model': config['model']
            }

            logger.info(f"尝试直接API调用: {request_data}")

            # 发送POST请求到推测的API端点
            async with self.session.post(
                self.api_url,
                json=request_data,
                headers={
                    **self.headers,
                    'Content-Type': 'application/json',
                    'Referer': f'{self.base_url}/app/text-to-image'
                }
            ) as response:

                if response.status == 200:
                    result = await response.json()

                    # 处理不同的响应格式
                    image_url = None
                    if 'image_url' in result:
                        image_url = result['image_url']
                    elif 'url' in result:
                        image_url = result['url']
                    elif 'data' in result and 'url' in result['data']:
                        image_url = result['data']['url']

                    if image_url:
                        return await self._download_image(image_url, config, index)
                    else:
                        logger.warning("API响应中未找到图像URL")
                        return None
                else:
                    logger.warning(f"API调用失败: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.warning(f"直接API调用失败: {e}")
            return None

    async def _try_browser_simulation(self, config: Dict, index: int) -> Optional[str]:
        """尝试模拟浏览器请求"""
        try:
            logger.info("尝试模拟浏览器请求")

            # 首先访问页面获取必要的token或session信息
            async with self.session.get(f"{self.base_url}/app/text-to-image") as response:
                if response.status != 200:
                    logger.error("无法访问Vheer页面")
                    return None

                # 这里可以解析页面获取CSRF token等信息
                page_content = await response.text()

            # 模拟表单提交
            form_data = aiohttp.FormData()
            form_data.add_field('prompt', config['prompt'])
            form_data.add_field('aspect_ratio', config['aspect_ratio'])
            form_data.add_field('model', config['model'])

            # 尝试不同的可能端点
            possible_endpoints = [
                f"{self.base_url}/api/generate",
                f"{self.base_url}/api/text-to-image",
                f"{self.base_url}/generate",
                f"{self.base_url}/api/v1/generate"
            ]

            for endpoint in possible_endpoints:
                try:
                    async with self.session.post(
                        endpoint,
                        data=form_data,
                        headers={
                            **self.headers,
                            'Referer': f'{self.base_url}/app/text-to-image',
                            'Origin': self.base_url
                        }
                    ) as response:

                        if response.status == 200:
                            content_type = response.headers.get('content-type', '')

                            if 'image' in content_type:
                                # 直接返回图像数据
                                return await self._save_image_data(await response.read(), config, index)
                            elif 'json' in content_type:
                                # JSON响应，可能包含图像URL
                                result = await response.json()
                                if 'image_url' in result or 'url' in result:
                                    image_url = result.get('image_url') or result.get('url')
                                    return await self._download_image(image_url, config, index)

                except Exception as e:
                    logger.debug(f"端点 {endpoint} 失败: {e}")
                    continue

            logger.warning("所有端点都失败了")
            return None

        except Exception as e:
            logger.warning(f"浏览器模拟失败: {e}")
            return None

    async def _download_image(self, image_url: str, config: Dict, index: int) -> Optional[str]:
        """下载图像"""
        try:
            # 确保URL是完整的
            if image_url.startswith('/'):
                image_url = self.base_url + image_url
            elif not image_url.startswith('http'):
                image_url = f"{self.base_url}/{image_url}"

            logger.info(f"下载图像: {image_url}")

            async with self.session.get(image_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    return await self._save_image_data(image_data, config, index)
                else:
                    logger.error(f"下载图像失败: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"下载图像失败: {e}")
            return None

    async def _save_image_data(self, image_data: bytes, config: Dict, index: int) -> Optional[str]:
        """保存图像数据"""
        try:
            # 动态获取输出目录
            current_output_dir = self._get_output_dir()
            os.makedirs(current_output_dir, exist_ok=True)

            # 生成文件名
            workflow_id = config.get('workflow_id', f'shot_{index}')
            safe_workflow_id = workflow_id.replace('-', '_').replace(':', '_')
            filename = f"vheer_{safe_workflow_id}.png"
            filepath = os.path.join(current_output_dir, filename)

            # 保存图像
            with open(filepath, 'wb') as f:
                f.write(image_data)

            logger.info(f"图像已保存: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"保存图像失败: {e}")
            return None

    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        return [
            'quality',  # Vheer的质量模型
            'speed',    # 可能的快速模型
            'artistic', # 可能的艺术模型
        ]

    def get_engine_info(self) -> EngineInfo:
        """获取引擎信息"""
        return EngineInfo(
            name="Vheer.com",
            version="1.0",
            description="Vheer.com AI图像生成服务，通过逆向工程实现",
            is_free=True,
            supports_batch=True,
            supports_custom_models=False,
            max_batch_size=5,  # 限制批量大小避免被封
            supported_sizes=[
                (512, 512), (768, 768), (1024, 1024),
                (1024, 768), (768, 1024),
                (1280, 720), (720, 1280),
                (512, 1024), (1024, 512)
            ],
            cost_per_image=0.0,
            rate_limit=30  # 保守的速率限制
        )

    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()
            self.session = None

        self.status = EngineStatus.OFFLINE
        await super().cleanup()
