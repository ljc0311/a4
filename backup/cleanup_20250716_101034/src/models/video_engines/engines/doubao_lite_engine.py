# -*- coding: utf-8 -*-
"""
豆包视频生成引擎 - Lite版
更便宜的豆包视频生成选择，价格比Pro版便宜33%
"""

import os
import time
import json
import asyncio
import aiohttp
import base64
from typing import Optional, Callable, Dict, Any, List
from pathlib import Path

from ..video_engine_base import VideoGenerationEngine, VideoGenerationConfig, VideoGenerationResult, VideoEngineStatus, VideoEngineType, VideoEngineInfo
from ....utils.logger import logger


class DoubaoLiteEngine(VideoGenerationEngine):
    """豆包视频生成引擎 - Lite版"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(VideoEngineType.DOUBAO_SEEDANCE_LITE)
        self.config = config
        self.api_key = self._get_api_key(config)
        self.base_url = config.get('base_url', 'https://ark.cn-beijing.volces.com/api/v3')
        self.model = config.get('model', 'doubao-seedance-1-0-lite-i2v-250428')
        self.timeout = config.get('timeout', 600)
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 30)
        
        # 会话管理
        self.session = None
        self.request_count = 0
        self.current_tasks = 0
        self._task_lock = asyncio.Lock()
        
        # 并发控制
        self.max_concurrent_tasks = config.get('max_concurrent', 5)
        self.rpm_limit = config.get('rpm_limit', 600)
        self.fps = config.get('fps', 24)
        self.cost_per_million_tokens = config.get('cost_per_million_tokens', 10.0)  # Lite版10元/百万token
        self.estimated_tokens_per_second = config.get('estimated_tokens_per_second', 50000)
        
        # HTTP请求头
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        # 输出目录将由_get_output_dir()动态确定
        self.project_manager = None
        self.current_project_name = None

        logger.info(f"豆包Lite视频引擎初始化完成，模型: {self.model}")
        logger.info(f"豆包Lite引擎配置 - 并发: {self.max_concurrent_tasks}, RPM限制: {self.rpm_limit}, 帧率: {self.fps}fps")
        logger.info(f"豆包Lite计费 - 收费: {self.cost_per_million_tokens}元/百万token (比Pro版便宜33%)")

    def _get_api_key(self, config: Dict[str, Any]) -> str:
        """获取API密钥"""
        try:
            # 优先从配置中获取
            if config.get('api_key'):
                return config['api_key']

            # 从环境变量获取ARK_API_KEY
            import os
            api_key = os.getenv('ARK_API_KEY')
            if api_key:
                logger.info("从环境变量ARK_API_KEY获取到豆包API密钥")
                return api_key

            logger.warning("未找到豆包API密钥，请在配置中设置或设置ARK_API_KEY环境变量")
            return ''

        except Exception as e:
            logger.warning(f"获取豆包API密钥失败: {e}")
            return ''
    
    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            # 检查API密钥
            if not self.api_key:
                logger.error("豆包Lite API密钥未配置，请在配置中设置或设置ARK_API_KEY环境变量")
                self.status = VideoEngineStatus.ERROR
                return False

            # 创建HTTP会话
            await self._create_new_session()
            
            # 测试API连接
            if await self.test_connection():
                self.status = VideoEngineStatus.IDLE
                logger.info("豆包Lite视频引擎初始化成功")
                return True
            else:
                self.status = VideoEngineStatus.ERROR
                logger.error("豆包Lite视频引擎初始化失败")
                # 清理会话
                if self.session and not self.session.closed:
                    await self.session.close()
                    self.session = None
                return False

        except Exception as e:
            logger.error(f"豆包Lite视频引擎初始化异常: {e}")
            self.status = VideoEngineStatus.ERROR
            # 清理会话
            if self.session and not self.session.closed:
                await self.session.close()
                self.session = None
            return False
    
    async def test_connection(self) -> bool:
        """测试API连接"""
        try:
            url = f"{self.base_url}/contents/generations/tasks"

            # 创建测试请求数据（使用豆包API的正确格式）
            test_data = {
                "model": self.model,
                "content": [
                    {
                        "type": "text",
                        "text": "测试连接 --ratio adaptive --dur 5"
                    }
                ]
            }

            # 创建测试连接的timeout
            timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
            async with self.session.post(url, json=test_data, headers=self.headers, timeout=timeout) as response:
                if response.status in [200, 400]:  # 400也算连接成功，只是参数问题
                    logger.info("豆包Lite API连接测试成功")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"豆包Lite API连接测试失败，状态码: {response.status}, 响应: {error_text}")
                    return False

        except Exception as e:
            logger.error(f"豆包Lite API连接测试异常: {e}")
            return False
    
    async def shutdown(self):
        """关闭引擎"""
        if self.session and not self.session.closed:
            await self.session.close()
        self.status = VideoEngineStatus.IDLE
        logger.info("豆包Lite视频引擎已关闭")

    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        return [self.model]

    def get_engine_info(self) -> VideoEngineInfo:
        """获取引擎信息"""
        return VideoEngineInfo(
            name='Doubao Seedance Lite',
            version='1.0',
            description='豆包视频生成引擎Lite版 - 成本效益优化版本，比Pro版便宜33%',
            is_free=False,
            supports_image_to_video=True,
            supports_text_to_video=True,
            max_duration=10.0,
            supported_resolutions=[(480, 480), (1080, 1080), (720, 720)],
            supported_fps=[24],
            cost_per_second=0.013,  # Lite版更便宜
            rate_limit=600,
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
                        output_dir = os.path.join(project_dir, 'videos', 'doubao_lite')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"豆包Lite引擎使用项目输出目录: {output_dir}")
                        return output_dir
                    elif project_data and 'project_path' in project_data:
                        project_dir = project_data['project_path']
                        output_dir = os.path.join(project_dir, 'videos', 'doubao_lite')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"豆包Lite引擎使用项目输出目录: {output_dir}")
                        return output_dir
                except Exception as e:
                    logger.warning(f"豆包Lite引擎获取项目路径失败: {e}，使用默认目录")

        except Exception as e:
            logger.warning(f"豆包Lite引擎无法获取项目目录: {e}")

        # 无项目时使用temp/video_cache
        output_dir = os.path.join(os.getcwd(), 'temp', 'video_cache', 'doubao_lite')
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"豆包Lite引擎使用默认输出目录: {output_dir}")
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
            logger.debug("豆包Lite引擎: HTTP会话已重新创建")

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
            logger.debug("豆包Lite引擎: HTTP会话创建成功")

        except Exception as e:
            logger.error(f"创建HTTP会话失败: {e}")
            raise
    
    def estimate_cost(self, duration: float) -> dict:
        """估算视频生成成本"""
        estimated_tokens = int(duration * self.estimated_tokens_per_second)

        # 计算成本（移除免费额度概念，直接按token计费）
        cost_yuan = (estimated_tokens / 1000000) * self.cost_per_million_tokens

        # 计算相比Pro版的节省（Pro版15元/百万token）
        pro_cost = (estimated_tokens / 1000000) * 15.0
        savings = pro_cost - cost_yuan

        return {
            'estimated_tokens': estimated_tokens,
            'cost_yuan': cost_yuan,
            'cost_usd': cost_yuan / 7.2,  # 估算美元价格
            'model_type': 'lite',
            'savings_vs_pro': savings  # 相比Pro版节省的金额
        }

    def _encode_image_to_base64(self, image_path: str) -> str:
        """将图像编码为base64"""
        try:
            with open(image_path, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded_string
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
                logger.error(f"豆包Lite引擎: 图片文件过大 ({file_size / 1024 / 1024:.1f}MB > 30MB): {image_path}")
                return False

            # 检查图片格式和尺寸
            with Image.open(image_path) as img:
                # 检查格式
                format_lower = img.format.lower() if img.format else ''
                supported_formats = ['jpeg', 'jpg', 'png', 'webp', 'bmp', 'tiff', 'gif']
                if format_lower not in supported_formats:
                    logger.error(f"豆包Lite引擎: 不支持的图片格式 ({img.format}): {image_path}")
                    return False

                # 检查尺寸
                width, height = img.size

                # 宽高长度：(300, 6000)
                if width < 300 or width > 6000 or height < 300 or height > 6000:
                    logger.error(f"豆包Lite引擎: 图片尺寸不符合要求 ({width}x{height}，要求300-6000px): {image_path}")
                    return False

                # 宽高比：(0.4, 2.5)
                aspect_ratio = width / height
                if aspect_ratio <= 0.4 or aspect_ratio >= 2.5:
                    logger.error(f"豆包Lite引擎: 图片宽高比不符合要求 ({aspect_ratio:.2f}，要求0.4-2.5): {image_path}")
                    return False

                logger.info(f"豆包Lite引擎: 图片验证通过 - 格式:{img.format}, 尺寸:{width}x{height}, 宽高比:{aspect_ratio:.2f}, 大小:{file_size/1024:.1f}KB")
                return True

        except Exception as e:
            logger.error(f"豆包Lite引擎: 图片验证失败: {e}")
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
                logger.info(f"豆包Lite引擎: 使用网络图片URL: {image_path}")
                return image_path

            # 如果已经是Base64格式，直接返回
            if image_path.startswith('data:image/'):
                logger.info(f"豆包Lite引擎: 使用Base64图片数据")
                return image_path

            # 本地文件，转换为Base64格式
            if not os.path.exists(image_path):
                logger.error(f"豆包Lite引擎: 图片文件不存在: {image_path}")
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
                logger.info(f"豆包Lite引擎: 本地图片转换为Base64成功: {os.path.basename(image_path)} (格式:{image_format}, 大小:{len(data_url)}字符)")
                return data_url
            else:
                logger.error(f"豆包Lite引擎: 图片Base64编码失败: {image_path}")
                return None

        except Exception as e:
            logger.error(f"豆包Lite引擎: 准备图片URL失败: {e}")
            return None

    async def generate_video(self, config: VideoGenerationConfig,
                           progress_callback: Optional[Callable] = None,
                           project_manager=None, current_project_name: str = None) -> VideoGenerationResult:
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
                    video_path="",
                    generation_time=0,
                    engine_type=VideoEngineType.DOUBAO_SEEDANCE_LITE,
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
            logger.info(f"豆包Lite视频生成开始，时长: {config.duration}秒")
            logger.info(f"预估成本: {cost_info['cost_yuan']:.4f}元 ({cost_info['estimated_tokens']}token)")
            logger.info(f"💰 相比Pro版节省: {cost_info['savings_vs_pro']:.4f}元")

            if progress_callback:
                progress_callback(f"开始豆包Lite视频生成... (预估: {cost_info['cost_yuan']:.4f}元, 节省33%)")

            # 验证输入（图像是可选的，支持纯文生视频）
            if config.input_image_path:
                # 准备图片URL（支持本地文件转换）
                image_url = self._prepare_image_url(config.input_image_path)
                if not image_url:
                    logger.error(f"豆包Lite引擎无法处理图片文件: {config.input_image_path}")
                    raise Exception(f"无法处理图片文件，请检查文件路径或网络连接: {config.input_image_path}")

            # 验证必须有提示词
            if not config.input_prompt or not config.input_prompt.strip():
                raise Exception("必须提供文本提示词")

            # 提交生成任务
            task_id = await self._submit_generation_task(config, progress_callback)
            if not task_id:
                raise Exception("任务提交失败")

            # 等待任务完成
            video_url = await self._wait_for_completion(task_id, progress_callback)
            if not video_url:
                raise Exception("视频生成失败")

            if progress_callback:
                progress_callback("下载生成的视频...")

            # 生成输出文件名
            timestamp = int(time.time())
            filename = f"doubao_lite_video_{timestamp}.mp4"
            output_dir = self._get_output_dir()
            output_path = os.path.join(output_dir, filename)

            # 下载视频
            final_path = await self._download_video(video_url, output_path)

            # 计算生成时间和成本
            generation_time = time.time() - start_time
            cost = config.duration * 0.013  # Lite版估算成本

            if progress_callback:
                progress_callback("豆包Lite视频生成完成！")

            return VideoGenerationResult(
                success=True,
                video_path=final_path,
                generation_time=generation_time,
                engine_type=VideoEngineType.DOUBAO_SEEDANCE_LITE,
                cost=cost,
                metadata={
                    'model': self.model,
                    'duration': config.duration,
                    'prompt': config.input_prompt,
                    'task_id': task_id,
                    'estimated_cost': cost_info,
                    'model_type': 'lite'
                }
            )

        except Exception as e:
            logger.error(f"豆包Lite视频生成失败: {e}")
            return VideoGenerationResult(
                success=False,
                video_path="",
                generation_time=time.time() - start_time,
                engine_type=VideoEngineType.DOUBAO_SEEDANCE_LITE,
                error_message=str(e)
            )

        finally:
            # 减少当前任务计数
            async with self._task_lock:
                self.current_tasks -= 1
                if self.current_tasks == 0:
                    self.status = VideoEngineStatus.READY

    async def _submit_generation_task(self, config: VideoGenerationConfig, progress_callback: Optional[Callable] = None) -> Optional[str]:
        """提交视频生成任务"""
        try:
            url = f"{self.base_url}/contents/generations/tasks"

            # 构建消息内容
            content = []

            # 添加文本提示词
            optimized_prompt = self._build_prompt_with_params(
                config.input_prompt,
                "1080p",  # 默认分辨率
                "adaptive",  # 豆包只支持adaptive
                int(config.duration)
            )

            content.append({
                "type": "text",
                "text": optimized_prompt
            })

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
                        logger.info(f"豆包Lite图生视频: 使用Base64图片 (格式:{format_part}, 大小:{data_length}字符)")
                    else:
                        logger.info(f"豆包Lite图生视频: 使用网络图片 {image_url}")
                else:
                    logger.error(f"豆包Lite引擎无法处理图片文件: {config.input_image_path}")
                    raise Exception(f"无法处理图片文件，请检查文件路径或网络连接: {config.input_image_path}")

            # 构建请求数据
            request_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            }

            if progress_callback:
                progress_callback("发送豆包Lite视频生成请求...")

            # 发送请求
            timeout = aiohttp.ClientTimeout(total=60)  # 60秒超时
            async with self.session.post(url, json=request_data, headers=self.headers, timeout=timeout) as response:
                response_text = await response.text()

                if response.status == 200:
                    result = json.loads(response_text)
                    task_id = result.get('id')
                    if task_id:
                        logger.info(f"豆包Lite视频生成任务提交成功，任务ID: {task_id}")
                        return task_id
                    else:
                        logger.error(f"豆包Lite任务提交响应中没有任务ID: {response_text}")
                        return None
                else:
                    logger.error(f"提交豆包Lite生成任务失败，状态码: {response.status}, 错误: {response_text}")
                    return None

        except Exception as e:
            logger.error(f"豆包Lite任务提交异常: {e}")
            return None

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

    async def _wait_for_completion(self, task_id: str, progress_callback: Optional[Callable] = None) -> Optional[str]:
        """等待任务完成并获取视频URL"""
        try:
            url = f"{self.base_url}/contents/generations/tasks/{task_id}"
            max_wait_time = 600  # 最大等待10分钟
            check_interval = 5   # 每5秒检查一次
            elapsed_time = 0

            if progress_callback:
                progress_callback("等待豆包Lite视频生成完成...")

            while elapsed_time < max_wait_time:
                # 创建轮询特定的timeout
                timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
                async with self.session.get(url, headers=self.headers, timeout=timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"豆包Lite API响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

                        status = result.get('status', '')

                        if status == 'succeeded':
                            # 任务完成，提取视频URL
                            video_url = self._extract_video_url(result)
                            if video_url:
                                logger.info(f"豆包Lite视频生成完成: {video_url}")
                                return video_url
                            else:
                                logger.error("豆包Lite任务完成但未找到视频URL")
                                return None

                        elif status == 'failed':
                            error_msg = result.get('error', '未知错误')
                            logger.error(f"豆包Lite视频生成失败: {error_msg}")
                            return None

                        elif status in ['queued', 'running']:
                            if progress_callback:
                                progress_callback(f"豆包Lite正在生成视频... (状态: {status})")

                            # 继续等待
                            await asyncio.sleep(check_interval)
                            elapsed_time += check_interval
                            continue
                        else:
                            logger.warning(f"豆包Lite未知状态: {status}")
                            await asyncio.sleep(check_interval)
                            elapsed_time += check_interval
                            continue
                    else:
                        logger.error(f"豆包Lite查询任务状态失败，状态码: {response.status}")
                        return None

            logger.error(f"豆包Lite视频生成超时 ({max_wait_time}秒)")
            return None

        except Exception as e:
            logger.error(f"豆包Lite等待任务完成异常: {e}")
            return None

    def _extract_video_url(self, result: dict) -> Optional[str]:
        """从API响应中提取视频URL"""
        try:
            # 豆包API响应格式
            content = result.get('content', {})
            if isinstance(content, dict):
                video_url = content.get('video_url')
                if video_url:
                    return video_url

            # 备用提取方法
            if 'choices' in result:
                choices = result['choices']
                if choices and len(choices) > 0:
                    choice = choices[0]
                    if 'message' in choice and 'content' in choice['message']:
                        content = choice['message']['content']
                        if isinstance(content, str) and content.startswith('http'):
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

                    logger.info(f"豆包Lite视频下载完成: {output_path}")
                    return output_path
                else:
                    logger.error(f"豆包Lite视频下载失败，状态码: {response.status}")
                    return ""
        except Exception as e:
            logger.error(f"豆包Lite视频下载异常: {e}")
            return ""
