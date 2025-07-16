# -*- coding: utf-8 -*-
"""
豆包视频生成引擎实现 (Doubao Seedance Pro)
火山引擎的视频生成模型，支持图生视频
"""

import asyncio
import aiohttp
import os
import time
import json
import base64
from typing import List, Dict, Optional, Callable
from ..video_engine_base import (
    VideoGenerationEngine, VideoEngineType, VideoEngineStatus, 
    VideoGenerationConfig, VideoGenerationResult, VideoEngineInfo, ConfigConverter
)
from src.utils.logger import logger


class DoubaoEngine(VideoGenerationEngine):
    """豆包视频生成引擎实现"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(VideoEngineType.DOUBAO_SEEDANCE_PRO)
        # 如果传入的是VideoEngineType，则使用默认配置
        if isinstance(config, VideoEngineType):
            self.config = {}
        else:
            self.config = config or {}
        
        # API配置
        self.api_key = self.config.get('api_key', '')
        self.base_url = self.config.get('base_url', 'https://ark.cn-beijing.volces.com/api/v3')
        self.model = self.config.get('model', 'doubao-seedance-pro')

        # 请求配置
        self.timeout = self.config.get('timeout', 600)  # 10分钟超时
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 30)

        # 生成参数 - 根据实际API文档
        self.max_duration = self.config.get('max_duration', 10.0)  # 豆包支持5秒和10秒
        self.supported_resolutions = self.config.get('supported_resolutions', [
            '480p', '720p', '1080p'  # 实际支持的分辨率
        ])
        self.supported_ratios = self.config.get('supported_ratios', [
            '21:9', '16:9', '4:3', '1:1', '3:4', '9:16', '9:21', 'keep_ratio', 'adaptive'
        ])
        self.supported_durations = [5, 10]  # 豆包支持5秒和10秒
        
        # 并发控制
        self.max_concurrent_tasks = self.config.get('max_concurrent', 10)
        self.rpm_limit = config.get('rpm_limit', 600)
        self.fps = config.get('fps', 24)
        self.cost_per_million_tokens = config.get('cost_per_million_tokens', 15.0)
        self.estimated_tokens_per_second = config.get('estimated_tokens_per_second', 50000)
        self.current_tasks = 0
        self._task_lock = asyncio.Lock()
        
        # HTTP会话和请求头
        self.session = None
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        # 输出目录将由_get_output_dir()动态确定
        self.project_manager = None
        self.current_project_name = None

        logger.info(f"豆包视频引擎初始化完成，模型: {self.model}")
        logger.info(f"豆包引擎配置 - 并发: {self.max_concurrent_tasks}, RPM限制: {self.rpm_limit}, 帧率: {self.fps}fps")
        logger.info(f"豆包计费 - 收费: {self.cost_per_million_tokens}元/百万token")



    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            if not self.api_key:
                logger.error("豆包API密钥未配置")
                self.status = VideoEngineStatus.ERROR
                self.last_error = "API密钥未配置"
                return False
            
            # 创建HTTP会话
            await self._create_new_session()
            
            # 测试连接
            if await self.test_connection():
                self.status = VideoEngineStatus.IDLE
                logger.info("豆包视频引擎初始化成功")
                return True
            else:
                self.status = VideoEngineStatus.ERROR
                logger.error("豆包视频引擎连接测试失败")
                return False
                
        except Exception as e:
            logger.error(f"豆包视频引擎初始化失败: {e}")
            self.status = VideoEngineStatus.ERROR
            self.last_error = str(e)
            return False
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self.session:
                return False

            # 检查API密钥是否存在
            if not self.api_key:
                logger.error("豆包API密钥未配置")
                return False

            # 发送一个简单的测试请求来验证连接和模型可用性
            url = f"{self.base_url}/contents/generations/tasks"

            test_data = {
                "model": self.model,
                "content": [
                    {
                        "type": "text",
                        "text": "test connection --resolution 720p --duration 5"
                    }
                ]
            }

            # 创建测试连接的timeout
            timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
            async with self.session.post(url, json=test_data, headers=self.headers, timeout=timeout) as response:
                if response.status == 200:
                    logger.info("豆包API连接测试成功")
                    return True
                elif response.status == 401:
                    logger.error("豆包API密钥无效")
                    return False
                elif response.status == 404:
                    error_text = await response.text()
                    logger.error(f"豆包模型或端点不存在: {error_text}")
                    return False
                else:
                    error_text = await response.text()
                    logger.warning(f"豆包API连接测试返回状态码 {response.status}: {error_text}")
                    # 对于其他状态码，我们仍然认为连接是可用的
                    return True

        except Exception as e:
            logger.error(f"豆包连接测试异常: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        return [self.model]
    
    def get_engine_info(self) -> VideoEngineInfo:
        """获取引擎信息"""
        return VideoEngineInfo(
            name="豆包视频生成 (Doubao Seedance Pro)",
            version="1.0",
            description="火山引擎的图生视频模型，支持首帧图片+文本提示词生成视频",
            is_free=False,  # 豆包是付费服务
            supports_image_to_video=True,
            supports_text_to_video=False,  # 豆包主要支持图生视频
            max_duration=self.max_duration,
            supported_resolutions=[(480, 480), (720, 720), (1080, 1080)],  # 根据分辨率参数
            supported_fps=[30],  # 豆包的默认帧率
            cost_per_second=0.02,  # 估算成本
            rate_limit=60,  # 每分钟请求限制
            max_concurrent_tasks=self.max_concurrent_tasks
        )
    
    def _get_output_dir(self) -> str:
        """获取输出目录"""
        try:
            # 如果有项目管理器，使用项目目录
            if self.project_manager:
                try:
                    project_data = self.project_manager.get_project_data()
                    if project_data and 'project_dir' in project_data:
                        project_dir = project_data['project_dir']
                        output_dir = os.path.join(project_dir, 'videos', 'doubao')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"豆包引擎使用项目输出目录: {output_dir}")
                        return output_dir
                    elif project_data and 'project_path' in project_data:
                        project_dir = project_data['project_path']
                        output_dir = os.path.join(project_dir, 'videos', 'doubao')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"豆包引擎使用项目输出目录: {output_dir}")
                        return output_dir
                except Exception as e:
                    logger.warning(f"豆包引擎获取项目路径失败: {e}，使用默认目录")

        except Exception as e:
            logger.warning(f"豆包引擎无法获取项目目录: {e}")

        # 无项目时使用temp/video_cache
        output_dir = os.path.join(os.getcwd(), 'temp', 'video_cache', 'doubao')
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"豆包引擎使用默认输出目录: {output_dir}")
        return output_dir
    
    async def _ensure_session_valid(self):
        """确保HTTP会话有效"""
        try:
            # 总是重新创建session以避免事件循环冲突
            if self.session and not self.session.closed:
                try:
                    await self.session.close()
                except Exception as e:
                    logger.debug(f"关闭旧session时出错: {e}")

            # 创建新session
            await self._create_new_session()
            logger.debug("豆包引擎: HTTP会话已重新创建")

        except Exception as e:
            logger.warning(f"确保session有效性失败: {e}")
            await self._create_new_session()

    async def _create_new_session(self):
        """创建新的HTTP会话"""
        try:
            # 创建连接器
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )

            # 不设置全局timeout，在每个请求中单独设置
            self.session = aiohttp.ClientSession(
                connector=connector,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
            )
            logger.debug("豆包引擎: HTTP会话创建成功")

        except Exception as e:
            logger.error(f"创建HTTP会话失败: {e}")
            raise
    
    def _encode_image_to_base64(self, image_path: str) -> str:
        """将图像编码为base64"""
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                return base64_data
        except Exception as e:
            logger.error(f"图像编码失败: {e}")
            raise

    def _validate_image(self, image_path: str) -> bool:
        """验证图片是否符合豆包API要求"""
        try:
            from PIL import Image

            # 检查文件大小 (小于30MB)
            file_size = os.path.getsize(image_path)
            if file_size > 30 * 1024 * 1024:  # 30MB
                logger.error(f"豆包引擎: 图片文件过大 ({file_size / 1024 / 1024:.1f}MB > 30MB): {image_path}")
                return False

            # 检查图片格式和尺寸
            with Image.open(image_path) as img:
                # 检查格式
                format_lower = img.format.lower() if img.format else ''
                supported_formats = ['jpeg', 'jpg', 'png', 'webp', 'bmp', 'tiff', 'gif']
                if format_lower not in supported_formats:
                    logger.error(f"豆包引擎: 不支持的图片格式 ({img.format}): {image_path}")
                    return False

                # 检查尺寸
                width, height = img.size

                # 宽高长度：(300, 6000)
                if width < 300 or width > 6000 or height < 300 or height > 6000:
                    logger.error(f"豆包引擎: 图片尺寸不符合要求 ({width}x{height}，要求300-6000px): {image_path}")
                    return False

                # 宽高比：(0.4, 2.5)
                aspect_ratio = width / height
                if aspect_ratio <= 0.4 or aspect_ratio >= 2.5:
                    logger.error(f"豆包引擎: 图片宽高比不符合要求 ({aspect_ratio:.2f}，要求0.4-2.5): {image_path}")
                    return False

                logger.info(f"豆包引擎: 图片验证通过 - 格式:{img.format}, 尺寸:{width}x{height}, 宽高比:{aspect_ratio:.2f}, 大小:{file_size/1024:.1f}KB")
                return True

        except Exception as e:
            logger.error(f"豆包引擎: 图片验证失败: {e}")
            return False

    def _get_image_format(self, image_path: str) -> str:
        """获取图片格式（小写）"""
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                format_name = img.format.lower() if img.format else 'jpeg'
                # 统一JPEG格式名称
                if format_name == 'jpg':
                    format_name = 'jpeg'
                return format_name
        except Exception as e:
            logger.error(f"获取图片格式失败: {e}")
            # 根据文件扩展名推断
            ext = os.path.splitext(image_path)[1].lower()
            format_map = {
                '.jpg': 'jpeg',
                '.jpeg': 'jpeg',
                '.png': 'png',
                '.webp': 'webp',
                '.bmp': 'bmp',
                '.tiff': 'tiff',
                '.gif': 'gif'
            }
            return format_map.get(ext, 'jpeg')

    def _prepare_image_url(self, image_path: str) -> Optional[str]:
        """准备图片URL - 支持网络URL和本地文件(转Base64)"""
        try:
            # 如果已经是URL，直接返回
            if image_path.startswith(('http://', 'https://')):
                logger.info(f"豆包引擎: 使用网络图片URL: {image_path}")
                return image_path

            # 如果已经是Base64格式，直接返回
            if image_path.startswith('data:image/'):
                logger.info(f"豆包引擎: 使用Base64图片数据")
                return image_path

            # 本地文件，转换为Base64格式
            if not os.path.exists(image_path):
                logger.error(f"豆包引擎: 图片文件不存在: {image_path}")
                return None

            # 验证图片格式和大小
            if not self._validate_image(image_path):
                return None

            # 转换为Base64
            base64_data = self._encode_image_to_base64(image_path)
            if base64_data:
                # 获取图片格式
                image_format = self._get_image_format(image_path)
                data_url = f"data:image/{image_format};base64,{base64_data}"
                logger.info(f"豆包引擎: 本地图片转换为Base64成功: {os.path.basename(image_path)} (格式:{image_format}, 大小:{len(data_url)}字符)")
                return data_url
            else:
                logger.error(f"豆包引擎: 图片Base64编码失败: {image_path}")
                return None

        except Exception as e:
            logger.error(f"豆包引擎: 准备图片URL失败: {e}")
            return None
    
    def _prepare_request_data(self, config: VideoGenerationConfig) -> Dict:
        """准备请求数据 - 根据豆包视频生成API文档格式"""
        try:
            # 豆包只支持5秒和10秒，使用用户指定的时长（必须是5或10）
            if config.duration not in [5, 10]:
                logger.warning(f"豆包引擎只支持5秒或10秒，用户指定: {config.duration}秒，将使用最接近的时长")
                duration = 5 if config.duration <= 7.5 else 10
            else:
                duration = int(config.duration)

            logger.info(f"豆包视频时长设置: 用户指定{config.duration}秒 → 实际使用{duration}秒")

            # 确定分辨率和宽高比
            resolution = self._determine_resolution(config.width, config.height)
            ratio = self._determine_ratio(config.width, config.height)

            # 构建content数组 - 豆包视频生成API格式
            content = []

            # 如果有输入图像，添加到content中
            if config.input_image_path:
                image_url = self._prepare_image_url(config.input_image_path)
                if image_url:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    })
                    # 简化日志显示
                    if image_url.startswith('data:image/'):
                        format_part = image_url.split(';')[0].split('/')[-1]
                        data_length = len(image_url)
                        logger.info(f"豆包图生视频: 使用Base64图片 (格式:{format_part}, 大小:{data_length}字符)")
                    else:
                        logger.info(f"豆包图生视频: 使用网络图片 {image_url}")
                else:
                    logger.error(f"无法处理图片文件: {config.input_image_path}")
                    raise Exception(f"无法处理图片文件，请检查文件路径或网络连接: {config.input_image_path}")

            # 如果有文本提示词，添加到content中
            if config.input_prompt:
                # 构建带参数的提示词
                prompt_with_params = self._build_prompt_with_params(
                    config.input_prompt, resolution, ratio, duration
                )
                content.insert(0, {
                    "type": "text",
                    "text": prompt_with_params
                })

            # 构建请求数据 - 根据官方文档使用content格式
            request_data = {
                "model": self.model,
                "content": content
            }

            # 添加回调URL（可选）
            # if callback_url:
            #     request_data["callback_url"] = callback_url

            return request_data

        except Exception as e:
            logger.error(f"准备豆包请求数据失败: {e}")
            raise

    def _determine_resolution(self, width: int, height: int) -> str:
        """根据宽高确定分辨率参数"""
        # 取较小的边作为分辨率基准
        min_dimension = min(width, height)

        if min_dimension <= 480:
            return "480p"
        elif min_dimension <= 720:
            return "720p"
        else:
            return "1080p"

    def _determine_ratio(self, width: int, height: int) -> str:
        """根据宽高确定宽高比参数"""
        ratio = width / height

        # 根据比例确定最接近的标准宽高比
        if abs(ratio - 21/9) < 0.1:
            return "21:9"
        elif abs(ratio - 16/9) < 0.1:
            return "16:9"
        elif abs(ratio - 4/3) < 0.1:
            return "4:3"
        elif abs(ratio - 1) < 0.1:
            return "1:1"
        elif abs(ratio - 3/4) < 0.1:
            return "3:4"
        elif abs(ratio - 9/16) < 0.1:
            return "9:16"
        elif abs(ratio - 9/21) < 0.1:
            return "9:21"
        else:
            return "adaptive"  # 自动选择最合适的宽高比

    def _build_prompt_with_params(self, prompt: str, resolution: str, ratio: str, duration: int) -> str:
        """构建带参数的提示词"""
        # 根据豆包API文档和错误信息，豆包模型只支持特定参数格式
        # 注意：resolution和ratio参数被忽略，因为豆包模型有固定要求
        _ = resolution  # 忽略分辨率参数
        _ = ratio      # 忽略比例参数

        params = []

        # 豆包模型只支持 --ratio adaptive
        params.append("--ratio adaptive")
        params.append(f"--dur {duration}")

        return f"{prompt} {' '.join(params)}"

    def estimate_cost(self, duration: float) -> dict:
        """估算视频生成成本"""
        estimated_tokens = int(duration * self.estimated_tokens_per_second)

        # 计算成本（移除免费额度概念，直接按token计费）
        cost_yuan = (estimated_tokens / 1000000) * self.cost_per_million_tokens

        return {
            'estimated_tokens': estimated_tokens,
            'cost_yuan': cost_yuan,
            'cost_usd': cost_yuan / 7.2,  # 估算美元价格
        }
    
    async def _submit_generation_task(self, request_data: Dict) -> str:
        """提交生成任务 - 根据豆包视频生成API格式"""
        try:
            # 豆包视频生成API的正确端点（根据官方文档）
            url = f"{self.base_url}/contents/generations/tasks"

            # 创建请求特定的timeout
            timeout = aiohttp.ClientTimeout(total=60)  # 60秒超时
            async with self.session.post(url, json=request_data, headers=self.headers, timeout=timeout) as response:
                if response.status == 200:
                    result = await response.json()
                    # 根据豆包API文档，返回的是任务ID
                    task_id = result.get('id')
                    if task_id:
                        logger.info(f"豆包视频生成任务提交成功，任务ID: {task_id}")
                        return task_id
                    else:
                        raise Exception(f"任务提交成功但未返回任务ID: {result}")
                else:
                    error_text = await response.text()
                    raise Exception(f"任务提交失败，状态码: {response.status}, 错误: {error_text}")

        except Exception as e:
            logger.error(f"提交豆包生成任务失败: {e}")
            raise
    
    async def _poll_task_status(self, task_id: str, progress_callback: Optional[Callable] = None) -> str:
        """轮询任务状态 - 根据豆包视频生成API格式"""
        try:
            # 豆包视频生成API的查询端点（根据官方文档）
            url = f"{self.base_url}/contents/generations/tasks/{task_id}"
            start_time = time.time()

            while True:
                # 检查超时
                if time.time() - start_time > self.timeout:
                    raise Exception("任务超时")

                # 创建请求特定的timeout
                timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
                async with self.session.get(url, headers=self.headers, timeout=timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        status = result.get('status')

                        # 调试：打印完整的响应数据
                        logger.info(f"豆包API响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

                        if status == 'succeeded':
                            # 根据实际API响应，视频URL在content字段中
                            video_url = (result.get('content', {}).get('video_url') or
                                       result.get('video_url') or
                                       result.get('output_url') or
                                       result.get('result', {}).get('video_url') or
                                       result.get('data', {}).get('video_url'))

                            if video_url:
                                logger.info(f"豆包视频生成完成: {video_url}")
                                return video_url
                            else:
                                logger.error(f"任务完成但未找到视频URL，完整响应: {result}")
                                raise Exception("任务完成但未返回视频URL")
                        elif status == 'failed':
                            error_msg = result.get('error', '未知错误')
                            raise Exception(f"视频生成失败: {error_msg}")
                        elif status in ['queued', 'running']:
                            if progress_callback:
                                progress_callback(f"豆包正在生成视频... (状态: {status})")
                            await asyncio.sleep(5)  # 等待5秒后重试
                        else:
                            logger.warning(f"未知任务状态: {status}")
                            await asyncio.sleep(5)
                    else:
                        error_text = await response.text()
                        logger.error(f"查询任务状态失败，状态码: {response.status}, 错误: {error_text}")
                        await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"轮询豆包任务状态失败: {e}")
            raise

    def _extract_video_url_from_content(self, content: str) -> Optional[str]:
        """从响应内容中提取视频URL"""
        try:
            # 豆包API可能返回JSON格式的内容，包含视频URL
            import json
            if isinstance(content, str):
                try:
                    content_data = json.loads(content)
                    return content_data.get('video_url')
                except json.JSONDecodeError:
                    # 如果不是JSON，可能直接是URL
                    if content.startswith('http'):
                        return content
            return None
        except Exception as e:
            logger.warning(f"提取视频URL失败: {e}")
            return None
    
    async def _download_video(self, video_url: str, output_path: str) -> str:
        """下载生成的视频"""
        try:
            # 创建下载特定的timeout（更长时间用于下载大文件）
            timeout = aiohttp.ClientTimeout(total=300)  # 5分钟超时
            async with self.session.get(video_url, timeout=timeout) as response:
                if response.status == 200:
                    # 确保输出目录存在
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # 下载视频文件
                    with open(output_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    
                    logger.info(f"豆包视频下载完成: {output_path}")
                    return output_path
                else:
                    raise Exception(f"下载视频失败，状态码: {response.status}")
                    
        except Exception as e:
            logger.error(f"下载豆包视频失败: {e}")
            raise

    async def generate_video(self, config: VideoGenerationConfig,
                           progress_callback: Optional[Callable] = None,
                           project_manager=None, current_project_name=None) -> VideoGenerationResult:
        """生成视频"""
        # 设置项目信息
        if project_manager and current_project_name:
            self.project_manager = project_manager
            self.current_project_name = current_project_name

        start_time = time.time()

        # 检查并发任务限制
        async with self._task_lock:
            if self.current_tasks >= self.max_concurrent_tasks:
                return VideoGenerationResult(
                    success=False,
                    error_message=f"引擎并发任务已满 ({self.current_tasks}/{self.max_concurrent_tasks})"
                )
            self.current_tasks += 1
            # 只有在有任务运行时才设置为BUSY
            if self.current_tasks == 1:
                self.status = VideoEngineStatus.BUSY

        self.request_count += 1

        try:
            # 确保HTTP会话在当前事件循环中有效
            await self._ensure_session_valid()

            # 估算成本
            cost_info = self.estimate_cost(config.duration)
            logger.info(f"豆包视频生成开始，时长: {config.duration}秒")
            logger.info(f"预估成本: {cost_info['cost_yuan']:.4f}元 ({cost_info['estimated_tokens']}token)")

            if progress_callback:
                progress_callback(f"开始豆包视频生成... (预估: {cost_info['cost_yuan']:.4f}元)")

            # 验证输入（图像是可选的，支持纯文生视频）
            if config.input_image_path:
                # 如果是URL，不需要验证文件存在
                if not config.input_image_path.startswith(('http://', 'https://')):
                    # 如果是本地文件路径，验证文件存在
                    if not os.path.exists(config.input_image_path):
                        raise Exception(f"输入图像不存在: {config.input_image_path}")

            # 验证必须有提示词
            if not config.input_prompt or not config.input_prompt.strip():
                raise Exception("必须提供文本提示词")

            # 准备请求数据
            request_data = self._prepare_request_data(config)

            if progress_callback:
                progress_callback("发送豆包视频生成请求...")

            # 发送异步生成请求
            task_id = await self._submit_generation_task(request_data)

            if progress_callback:
                progress_callback("等待豆包视频生成完成...")

            # 轮询任务状态
            video_url = await self._poll_task_status(task_id, progress_callback)

            if progress_callback:
                progress_callback("下载生成的视频...")

            # 生成输出文件名
            timestamp = int(time.time())
            filename = f"doubao_video_{timestamp}.mp4"
            output_dir = self._get_output_dir()
            output_path = os.path.join(output_dir, filename)

            # 下载视频
            final_path = await self._download_video(video_url, output_path)

            # 计算生成时间和成本
            generation_time = time.time() - start_time
            cost = config.duration * 0.02  # 估算成本

            # 获取视频信息
            file_size = os.path.getsize(final_path) if os.path.exists(final_path) else 0

            self.success_count += 1
            self.total_cost += cost

            if progress_callback:
                progress_callback("豆包视频生成完成！")

            return VideoGenerationResult(
                success=True,
                video_path=final_path,
                generation_time=generation_time,
                cost=cost,
                engine_type=self.engine_type,
                duration=config.duration,
                fps=16,  # 豆包固定16fps
                resolution=(config.width, config.height),
                file_size=file_size,
                metadata={
                    'task_id': task_id,
                    'video_url': video_url,
                    'model': self.model,
                    'prompt': config.input_prompt
                }
            )

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"豆包视频生成失败: {e}")

            return VideoGenerationResult(
                success=False,
                error_message=str(e),
                generation_time=time.time() - start_time,
                engine_type=self.engine_type
            )

        finally:
            # 减少当前任务计数
            async with self._task_lock:
                self.current_tasks -= 1
                # 如果没有任务在运行，设置为IDLE
                if self.current_tasks == 0:
                    self.status = VideoEngineStatus.IDLE

    async def shutdown(self):
        """关闭引擎"""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
                logger.info("豆包视频引擎已关闭")
        except Exception as e:
            logger.error(f"关闭豆包视频引擎失败: {e}")

    def __del__(self):
        """析构函数"""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            # 安全地关闭会话，避免事件循环问题
            try:
                # 检查是否有运行中的事件循环
                try:
                    loop = asyncio.get_running_loop()
                    # 如果有运行中的循环，创建任务关闭session
                    if loop and not loop.is_closed():
                        loop.create_task(self._safe_close_session())
                except RuntimeError:
                    # 没有运行中的事件循环，尝试创建新的循环
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.session.close())
                        loop.close()
                    except Exception:
                        # 如果所有方法都失败，直接忽略
                        pass
            except Exception:
                # 忽略所有析构函数中的异常
                pass

    async def _safe_close_session(self):
        """安全关闭session"""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
        except Exception:
            pass
