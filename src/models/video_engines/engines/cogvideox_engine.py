# -*- coding: utf-8 -*-
"""
CogVideoX-Flash 视频生成引擎实现
智谱AI的免费视频生成模型，支持图生视频和文生视频
"""

import asyncio
import aiohttp
import os
import time
import json
from typing import List, Dict, Optional, Callable
from ..video_engine_base import (
    VideoGenerationEngine, VideoEngineType, VideoEngineStatus, 
    VideoGenerationConfig, VideoGenerationResult, VideoEngineInfo, ConfigConverter
)
from src.utils.logger import logger


class CogVideoXEngine(VideoGenerationEngine):
    """CogVideoX-Flash 引擎实现"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(VideoEngineType.COGVIDEOX_FLASH)
        # 如果传入的是VideoEngineType，则使用默认配置
        if isinstance(config, VideoEngineType):
            self.config = {}
        else:
            self.config = config or {}
        
        # API配置 - 使用智谱AI密钥
        self.api_key = self._get_api_key()
        self.base_url = self.config.get('base_url', 'https://open.bigmodel.cn/api/paas/v4')
        self.model = self.config.get('model', 'cogvideox-flash')
        
        # 请求配置
        self.timeout = self.config.get('timeout', 900)  # 15分钟超时
        self.max_retries = self.config.get('max_retries', 8)  # 增加重试次数
        self.retry_delay = self.config.get('retry_delay', 30)  # 重试延迟30秒
        self.max_concurrent = self.config.get('max_concurrent', 3)  # 最大并发数，用户可调整
        
        # 输出配置
        self.output_dir = self.config.get('output_dir', 'output/videos')
        
        # HTTP会话
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 项目相关信息
        self.project_manager = None
        self.current_project_name = None

        # 🔧 修复：添加并发任务跟踪
        self.max_concurrent_tasks = 3
        self.current_tasks = 0
        self._task_lock = asyncio.Lock()

        if not self.api_key:
            logger.warning("CogVideoX-Flash引擎未配置API密钥")

    def _get_api_key(self) -> str:
        """获取API密钥"""
        try:
            # 优先从配置中获取
            if self.config.get('api_key'):
                return self.config['api_key']

            # 统一从ConfigManager获取智谱AI密钥
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            models = config_manager.get_models()
            for model in models:
                if model.get('type') == 'zhipu' or model.get('name') == '智谱AI':
                    api_key = model.get('key', '')
                    if api_key:
                        logger.info("从ConfigManager获取到智谱AI密钥")
                        return api_key

            # 备用方案：从环境变量获取
            import os
            api_key = os.getenv('ZHIPU_API_KEY')
            if api_key:
                logger.info("从环境变量获取到智谱AI密钥")
                return api_key

            logger.warning("未找到智谱AI API密钥，请在设置中配置")

            return ''

        except Exception as e:
            logger.warning(f"获取API密钥失败: {e}")
            return ''
    
    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            if not self.api_key:
                logger.error("CogVideoX-Flash引擎缺少API密钥")
                self.status = VideoEngineStatus.ERROR
                return False
            
            # 创建HTTP会话
            connector = aiohttp.TCPConnector(
                limit=5,
                limit_per_host=2,
                enable_cleanup_closed=True,
                force_close=False,  # 修复：不能与keepalive_timeout同时为True
                keepalive_timeout=10,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            # 不设置全局timeout，在每个请求中单独设置
            self.session = aiohttp.ClientSession(
                connector=connector,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                raise_for_status=False
            )
            
            # 测试连接
            if await self.test_connection():
                self.status = VideoEngineStatus.IDLE
                logger.info("CogVideoX-Flash引擎初始化成功")
                return True
            else:
                self.status = VideoEngineStatus.ERROR
                logger.error("CogVideoX-Flash引擎连接测试失败")
                return False
                
        except Exception as e:
            logger.error(f"CogVideoX-Flash引擎初始化失败: {e}")
            self.status = VideoEngineStatus.ERROR
            return False
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self.session:
                return False

            # 测试视频生成端点是否可访问
            # 使用一个简单的请求来验证API密钥和端点
            test_url = f"{self.base_url}/videos/generations"
            test_data = {
                "model": self.model,
                "prompt": "test"
            }

            # 创建测试连接的timeout
            timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
            async with self.session.post(test_url, json=test_data, timeout=timeout) as response:
                # 如果返回401，说明API密钥问题
                # 如果返回400，可能是参数问题，但端点是对的
                # 如果返回200或202，说明连接正常
                if response.status in [200, 202]:
                    return True
                elif response.status == 401:
                    logger.error("API密钥无效或已过期")
                    return False
                elif response.status == 400:
                    # 参数错误但API可访问，认为连接正常
                    logger.info("API端点可访问（参数测试返回400）")
                    return True
                elif response.status == 429:
                    # 请求频率限制，但API可访问，认为连接正常
                    logger.warning("API请求频率受限(429)，但端点可访问，允许引擎初始化")
                    return True
                else:
                    logger.warning(f"API测试返回状态码: {response.status}")
                    # 对于其他状态码，也允许引擎初始化，避免因为临时问题导致引擎不可用
                    return True

        except Exception as e:
            logger.error(f"CogVideoX-Flash连接测试失败: {e}")
            # 网络连接失败时，仍然允许引擎初始化，可能是暂时的网络问题
            logger.warning("网络连接测试失败，但允许引擎继续初始化")
            return True
    
    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        return ['cogvideox-flash']
    
    def get_engine_info(self) -> VideoEngineInfo:
        """获取引擎信息"""
        return VideoEngineInfo(
            name="CogVideoX-Flash",
            version="1.0",
            description="智谱AI免费视频生成模型，支持图生视频和文生视频",
            is_free=True,
            supports_image_to_video=True,
            supports_text_to_video=True,
            max_duration=10.0,  # 最大10秒
            supported_resolutions=[
                # 官方支持的完整分辨率列表
                (720, 480),     # 标准清晰度
                (1024, 1024),   # 正方形
                (1280, 960),    # 4:3 横屏
                (960, 1280),    # 3:4 竖屏
                (1920, 1080),   # Full HD 横屏
                (1080, 1920),   # Full HD 竖屏
                (2048, 1080),   # 超宽屏
                (3840, 2160),   # 4K
            ],
            supported_fps=[30, 60],
            cost_per_second=0.0,  # 免费
            rate_limit=60,  # 每分钟60次请求（估计值）
            max_concurrent_tasks=3  # 支持3个并发任务
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
                        output_dir = os.path.join(project_dir, 'videos', 'cogvideox')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"使用项目输出目录: {output_dir}")
                        return output_dir
                    elif project_data and 'project_path' in project_data:
                        project_dir = project_data['project_path']
                        output_dir = os.path.join(project_dir, 'videos', 'cogvideox')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"使用项目输出目录: {output_dir}")
                        return output_dir
                except Exception as e:
                    logger.warning(f"获取项目路径失败: {e}，使用默认目录")

        except Exception as e:
            logger.warning(f"无法获取项目目录: {e}")

        # 无项目时使用temp/video_cache
        output_dir = os.path.join(os.getcwd(), 'temp', 'video_cache', 'cogvideox')
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"使用默认输出目录: {output_dir}")
        return output_dir

    async def _ensure_session_valid(self):
        """确保HTTP会话在当前事件循环中有效"""
        try:
            # 检查会话是否存在且未关闭
            if self.session and not self.session.closed:
                # 检查会话是否在当前事件循环中
                try:
                    # 尝试获取当前事件循环
                    current_loop = asyncio.get_running_loop()
                    # 如果会话的连接器有事件循环引用，检查是否匹配
                    if hasattr(self.session, '_connector') and hasattr(self.session._connector, '_loop'):
                        session_loop = self.session._connector._loop
                        if session_loop != current_loop:
                            logger.info("检测到事件循环变化，重新创建HTTP会话")
                            await self.session.close()
                            self.session = None
                    else:
                        # 如果无法检查循环，跳过连接测试，直接使用现有会话
                        # 避免在非任务上下文中使用超时管理器
                        pass
                except RuntimeError:
                    # 没有运行中的事件循环，这种情况下重新创建会话
                    logger.info("没有运行中的事件循环，重新创建HTTP会话")
                    if self.session:
                        await self.session.close()
                    self.session = None

            # 如果会话不存在或已关闭，重新创建
            if not self.session or self.session.closed:
                logger.info("重新创建HTTP会话")
                connector = aiohttp.TCPConnector(
                    limit=5,
                    limit_per_host=2,
                    enable_cleanup_closed=True,
                    force_close=False,  # 修复：不能与keepalive_timeout同时为True
                    keepalive_timeout=10,
                    ttl_dns_cache=300,
                    use_dns_cache=True
                )
                # 不设置全局timeout，在每个请求中单独设置
                self.session = aiohttp.ClientSession(
                    connector=connector,
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json'
                    },
                    raise_for_status=False
                )

        except Exception as e:
            logger.warning(f"确保会话有效时出错: {e}")
            # 如果出现任何错误，重新创建会话
            if self.session:
                try:
                    await self.session.close()
                except Exception:
                    pass
            self.session = None

            # 重新创建会话
            connector = aiohttp.TCPConnector(
                limit=5,
                limit_per_host=2,
                enable_cleanup_closed=True,
                force_close=False,  # 修复：不能与keepalive_timeout同时为True
                keepalive_timeout=10,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            # 不设置全局timeout，在每个请求中单独设置
            self.session = aiohttp.ClientSession(
                connector=connector,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                raise_for_status=False
            )

    async def generate_video(self, config: VideoGenerationConfig,
                           progress_callback: Optional[Callable] = None,
                           project_manager=None, current_project_name=None) -> VideoGenerationResult:
        """生成视频"""
        # 设置项目信息
        if project_manager and current_project_name:
            self.project_manager = project_manager
            self.current_project_name = current_project_name
            # 更新输出目录
            self.output_dir = self._get_output_dir()
        
        start_time = time.time()

        # 🔧 修复：检查并发任务限制
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

            if progress_callback:
                progress_callback("开始CogVideoX-Flash视频生成...")

            # 准备请求数据
            request_data = self._prepare_request_data(config)
            
            if progress_callback:
                progress_callback("发送视频生成请求...")
            
            # 发送异步生成请求
            task_id = await self._submit_generation_task(request_data)
            
            if progress_callback:
                progress_callback("等待视频生成完成...")
            
            # 轮询任务状态
            video_url = await self._poll_task_status(task_id, progress_callback)
            
            if progress_callback:
                progress_callback("下载生成的视频...")
            
            # 下载视频文件
            video_path = await self._download_video(video_url, config)
            
            # 获取视频信息
            video_info = await self._get_video_info(video_path)
            
            generation_time = time.time() - start_time
            self.success_count += 1

            # 🔧 修复：更新并发任务计数和状态
            async with self._task_lock:
                self.current_tasks -= 1
                # 只有在没有任务运行时才设置为IDLE
                if self.current_tasks == 0:
                    self.status = VideoEngineStatus.IDLE
            
            if progress_callback:
                progress_callback("视频生成完成!")
            
            return VideoGenerationResult(
                success=True,
                video_path=video_path,
                generation_time=generation_time,
                engine_type=self.engine_type,
                duration=video_info.get('duration', config.duration),
                fps=video_info.get('fps', config.fps),
                resolution=video_info.get('resolution', (config.width, config.height)),
                file_size=video_info.get('file_size', 0),
                metadata={
                    'model': self.model,
                    'prompt': config.input_prompt,
                    'input_image': config.input_image_path,
                    'motion_intensity': config.motion_intensity
                }
            )
            
        except asyncio.CancelledError:
            # 🔧 新增：专门处理任务取消错误
            logger.warning("CogVideoX-Flash任务被取消")
            async with self._task_lock:
                self.current_tasks -= 1
                if self.current_tasks == 0:
                    self.status = VideoEngineStatus.IDLE

            # 安全清理HTTP会话
            await self._safe_cleanup_session("任务取消后")

            return VideoGenerationResult(
                success=False,
                error_message="视频生成任务被取消，请重试",
                generation_time=time.time() - start_time,
                engine_type=self.engine_type
            )

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)

            # 🔧 修复：更新并发任务计数
            async with self._task_lock:
                self.current_tasks -= 1

                # 🔧 修复：网络错误后不要将状态设为ERROR，而是保持IDLE以便重试
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ['timeout', '超时', 'connection', 'network', '网络', 'cancelled']):
                    logger.warning(f"CogVideoX-Flash网络错误，保持引擎可用状态: {e}")
                    if self.current_tasks == 0:
                        self.status = VideoEngineStatus.IDLE

                    # 安全清理HTTP会话以避免连接池问题
                    await self._safe_cleanup_session("网络错误后")
                else:
                    # 非网络错误才设为ERROR状态
                    if self.current_tasks == 0:
                        self.status = VideoEngineStatus.ERROR
                    logger.error(f"CogVideoX-Flash引擎错误: {e}")

            return VideoGenerationResult(
                success=False,
                error_message=f"CogVideoX-Flash生成失败: {e}",
                generation_time=time.time() - start_time,
                engine_type=self.engine_type
            )

    def _prepare_request_data(self, config: VideoGenerationConfig) -> Dict:
        """准备请求数据"""
        # 构建完整的prompt，包含音效提示
        full_prompt = config.input_prompt

        # 如果有音效提示，添加到prompt中
        if config.audio_hint:
            full_prompt = f"{config.input_prompt}。音效: {config.audio_hint}"
            logger.info(f"添加音效提示: {config.audio_hint}")

        request_data = {
            "model": self.model,
            "prompt": full_prompt
        }

        # 检查是否是图生视频模式
        is_image_to_video = config.input_image_path and os.path.exists(config.input_image_path)

        if is_image_to_video:
            # 图生视频模式 - 将图像转换为base64格式
            image_base64 = self._encode_image_to_base64(config.input_image_path)
            if image_base64:
                request_data["image_url"] = image_base64
            else:
                raise Exception(f"无法编码图像文件: {config.input_image_path}")

        # 无论是图生视频还是文生视频，都添加完整参数
        if config.duration > 0:
            # 🔧 修复：允许API自由调整时长，不强制验证
            # CogVideoX-Flash API可能会根据模型特性调整实际时长
            request_data["duration"] = config.duration
            logger.debug(f"请求时长: {config.duration}s（API可能会自动调整）")

        if config.fps in [30, 60]:
            request_data["fps"] = config.fps
        else:
            # 如果不支持，使用默认帧率30
            logger.warning(f"帧率 {config.fps} 不被支持，使用默认帧率 30")
            request_data["fps"] = 30

        if config.width and config.height:
            # 验证分辨率是否支持
            resolution = (config.width, config.height)
            logger.info(f"CogVideoX引擎接收到分辨率配置: {config.width}x{config.height}")

            supported_resolutions = [
                # 官方支持的完整分辨率列表
                (720, 480),     # 标准清晰度
                (1024, 1024),   # 正方形
                (1280, 960),    # 4:3 横屏
                (960, 1280),    # 3:4 竖屏
                (1920, 1080),   # Full HD 横屏
                (1080, 1920),   # Full HD 竖屏
                (2048, 1080),   # 超宽屏
                (3840, 2160),   # 4K
            ]

            if resolution not in supported_resolutions:
                # 找到最接近的支持分辨率
                closest_resolution = self._find_closest_resolution(config.width, config.height, supported_resolutions)
                logger.warning(f"分辨率 {config.width}x{config.height} 不被支持，使用最接近的分辨率 {closest_resolution[0]}x{closest_resolution[1]}")
                request_data["size"] = f"{closest_resolution[0]}x{closest_resolution[1]}"
            else:
                logger.info(f"分辨率 {config.width}x{config.height} 被支持，直接使用")
                request_data["size"] = f"{config.width}x{config.height}"

            logger.info(f"最终发送给API的分辨率: {request_data['size']}")

        # 运动强度
        if config.motion_intensity is not None:
            request_data["motion_intensity"] = config.motion_intensity

        # 随机种子
        if config.seed is not None:
            request_data["seed"] = config.seed

        return request_data

    def _find_closest_resolution(self, width, height, supported_resolutions):
        """找到最接近的支持分辨率，优先保持宽高比"""
        target_ratio = width / height

        # 首先按照图像方向分类
        if target_ratio > 1.2:
            # 横屏图像 (宽 > 高)
            candidate_resolutions = [(w, h) for w, h in supported_resolutions if w > h]
        elif target_ratio < 0.8:
            # 竖屏图像 (高 > 宽)
            candidate_resolutions = [(w, h) for w, h in supported_resolutions if h > w]
        else:
            # 接近正方形的图像
            candidate_resolutions = [(w, h) for w, h in supported_resolutions if 0.8 <= w/h <= 1.2]

        # 如果没有找到同方向的分辨率，使用所有分辨率
        if not candidate_resolutions:
            candidate_resolutions = supported_resolutions

        # 在候选分辨率中找到最佳匹配
        best_resolution = candidate_resolutions[0]
        best_score = float('inf')

        for res_width, res_height in candidate_resolutions:
            res_ratio = res_width / res_height

            # 计算比例差异（权重最高）
            ratio_diff = abs(target_ratio - res_ratio) / max(target_ratio, res_ratio)

            # 计算面积差异
            target_area = width * height
            res_area = res_width * res_height
            area_diff = abs(target_area - res_area) / max(target_area, res_area)

            # 综合评分（比例权重0.8，面积权重0.2）
            score = ratio_diff * 0.8 + area_diff * 0.2

            if score < best_score:
                best_score = score
                best_resolution = (res_width, res_height)

        return best_resolution

    def _encode_image_to_base64(self, image_path):
        """将图像文件编码为base64格式"""
        try:
            import base64
            from PIL import Image
            import io

            # 读取并处理图像
            with Image.open(image_path) as img:
                # 转换为RGB格式（如果需要）
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # 将图像保存到内存中的字节流
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG', quality=95)
                img_buffer.seek(0)

                # 编码为base64
                img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')

                # 返回data URL格式
                return f"data:image/jpeg;base64,{img_base64}"

        except Exception as e:
            logger.error(f"图像base64编码失败: {e}")
            return None

    async def _submit_generation_task(self, request_data: Dict) -> str:
        """提交生成任务"""
        if not self.session:
            raise Exception("HTTP会话未初始化")

        url = f"{self.base_url}/videos/generations"

        # 记录关键参数（调试用）
        logger.debug(f"发送给CogVideoX API的参数: {request_data}")

        # 添加重试机制处理429错误
        max_retries = 3
        base_delay = 5  # 基础延迟5秒
        
        for attempt in range(max_retries):
            try:
                # 创建提交任务的timeout
                timeout = aiohttp.ClientTimeout(total=60)  # 60秒超时
                async with self.session.post(url, json=request_data, timeout=timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        if 'id' not in result:
                            raise Exception(f"API响应格式错误: {result}")
                        return result['id']
                    elif response.status == 429:
                        # 请求频率限制，需要等待后重试
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)  # 指数退避
                            logger.warning(f"API请求频率受限(429)，等待{delay}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            error_text = await response.text()
                            raise Exception(f"API请求频率受限，已重试{max_retries}次仍失败: {error_text}")
                    else:
                        error_text = await response.text()
                        raise Exception(f"API请求失败 (状态码: {response.status}): {error_text}")

            except asyncio.CancelledError:
                logger.warning("提交生成任务被取消")
                raise
            except Exception as e:
                if "API请求频率受限" in str(e):
                    raise  # 重新抛出频率限制错误
                logger.error(f"提交生成任务失败: {e}")
                raise

    async def _poll_task_status(self, task_id: str, progress_callback: Optional[Callable] = None) -> str:
        """轮询任务状态"""
        if not self.session:
            raise Exception("HTTP会话未初始化")

        url = f"{self.base_url}/async-result/{task_id}"
        max_wait_time = 1800  # 增加到30分钟最大等待时间
        poll_interval = 15  # 增加到15秒轮询间隔，进一步减少服务器压力
        start_time = time.time()
        consecutive_errors = 0  # 连续错误计数
        max_consecutive_errors = 8  # 增加最大连续错误次数
        backoff_multiplier = 1.5  # 退避乘数

        while time.time() - start_time < max_wait_time:
            try:
                # 🔧 修复：检查事件循环状态，避免在已关闭的循环中继续轮询
                try:
                    current_loop = asyncio.get_running_loop()
                    if current_loop.is_closed():
                        logger.warning("事件循环已关闭，停止轮询任务状态")
                        raise asyncio.CancelledError("事件循环已关闭")
                except RuntimeError:
                    logger.warning("没有运行中的事件循环，停止轮询任务状态")
                    raise asyncio.CancelledError("没有运行中的事件循环")

                # 检查会话状态
                if self.session.closed:
                    logger.warning("HTTP会话已关闭，停止轮询任务状态")
                    raise asyncio.CancelledError("HTTP会话已关闭")

                # 创建轮询状态的timeout
                timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
                async with self.session.get(url, timeout=timeout) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        consecutive_errors += 1

                        # 如果是504错误，记录但继续重试
                        if response.status == 504:
                            logger.warning(f"服务器网关超时 (504)，继续重试... (连续错误: {consecutive_errors}/{max_consecutive_errors})")
                            if consecutive_errors >= max_consecutive_errors:
                                raise Exception(f"连续{max_consecutive_errors}次网关超时，任务可能失败")
                            await asyncio.sleep(poll_interval * 2)  # 网关超时时等待更长时间
                            continue
                        else:
                            raise Exception(f"查询任务状态失败 (状态码: {response.status}): {error_text}")

                    # 重置错误计数
                    consecutive_errors = 0
                    result = await response.json()
                    status = result.get('task_status', 'PROCESSING')

                    if status == 'SUCCESS':
                        video_result = result.get('video_result', [])

                        # video_result是一个列表，取第一个元素
                        if isinstance(video_result, list) and len(video_result) > 0:
                            video_info = video_result[0]
                            video_url = video_info.get('url')
                        else:
                            video_url = None

                        if not video_url:
                            raise Exception("API响应中没有视频URL")
                        return video_url

                    elif status == 'FAIL':
                        error_msg = result.get('error', {}).get('message', '未知错误')
                        raise Exception(f"视频生成失败: {error_msg}")

                    elif status in ['PROCESSING', 'SUBMITTED']:
                        if progress_callback:
                            elapsed = int(time.time() - start_time)
                            progress_callback(f"视频生成中... ({elapsed}s)")
                        await asyncio.sleep(poll_interval)

                    else:
                        logger.warning(f"未知任务状态: {status}")
                        await asyncio.sleep(poll_interval)

            except asyncio.CancelledError:
                logger.warning("轮询任务状态被取消")
                raise

            except Exception as e:
                if "查询任务状态失败" in str(e) and "504" not in str(e):
                    raise e

                # 🔧 修复：检查是否是事件循环相关错误
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ['event loop is closed', 'loop is closed', 'no running loop']):
                    logger.warning(f"事件循环错误，停止轮询: {e}")
                    raise asyncio.CancelledError("事件循环已关闭或不可用")

                # 处理网络相关错误
                if any(keyword in error_str for keyword in ['timeout', '超时', 'connection', 'network', '网络', '504', 'cancelled', 'disconnected', 'server']):
                    consecutive_errors += 1
                    logger.warning(f"网络相关错误: {e} (连续错误: {consecutive_errors}/{max_consecutive_errors})")

                    if consecutive_errors >= max_consecutive_errors:
                        raise Exception(f"连续{max_consecutive_errors}次网络错误，请检查网络连接或稍后重试")

                    # 智能退避：错误越多，等待时间越长
                    backoff_delay = poll_interval * (backoff_multiplier ** consecutive_errors)
                    backoff_delay = min(backoff_delay, 120)  # 最大等待2分钟
                    logger.info(f"网络错误后等待 {backoff_delay:.1f} 秒再重试...")

                    # 🔧 修复：在sleep前再次检查事件循环状态
                    try:
                        current_loop = asyncio.get_running_loop()
                        if current_loop.is_closed():
                            logger.warning("事件循环已关闭，停止重试")
                            raise asyncio.CancelledError("事件循环已关闭")
                        await asyncio.sleep(backoff_delay)
                    except RuntimeError:
                        logger.warning("没有运行中的事件循环，停止重试")
                        raise asyncio.CancelledError("没有运行中的事件循环")
                else:
                    logger.warning(f"查询任务状态时出错: {e}")
                    # 🔧 修复：在sleep前检查事件循环状态
                    try:
                        current_loop = asyncio.get_running_loop()
                        if current_loop.is_closed():
                            logger.warning("事件循环已关闭，停止轮询")
                            raise asyncio.CancelledError("事件循环已关闭")
                        await asyncio.sleep(poll_interval)
                    except RuntimeError:
                        logger.warning("没有运行中的事件循环，停止轮询")
                        raise asyncio.CancelledError("没有运行中的事件循环")

        # 提供更详细的超时错误信息
        elapsed_minutes = max_wait_time // 60
        raise Exception(
            f"视频生成超时 (超过 {elapsed_minutes} 分钟)。\n"
            f"💡 建议解决方案:\n"
            f"1. 视频生成是计算密集型任务，请耐心等待\n"
            f"2. 检查网络连接是否稳定\n"
            f"3. 尝试减少视频时长或降低分辨率\n"
            f"4. 稍后重试，服务器可能正在处理大量请求\n"
            f"5. 如果问题持续，请联系技术支持"
        )

    async def _download_video(self, video_url: str, config: VideoGenerationConfig) -> str:
        """下载视频文件"""
        if not self.session:
            raise Exception("HTTP会话未初始化")

        # 生成唯一的输出文件名，避免覆盖
        import time
        timestamp = int(time.time() * 1000)  # 毫秒级时间戳
        filename = f"cogvideox_{timestamp}.{config.output_format}"
        output_path = os.path.join(self.output_dir, filename)

        # 如果文件已存在，添加序号
        counter = 1
        while os.path.exists(output_path):
            filename = f"cogvideox_{timestamp}_{counter}.{config.output_format}"
            output_path = os.path.join(self.output_dir, filename)
            counter += 1

        # 下载视频
        timeout = aiohttp.ClientTimeout(total=300)  # 5分钟超时
        async with self.session.get(video_url, timeout=timeout) as response:
            if response.status != 200:
                raise Exception(f"下载视频失败 (状态码: {response.status})")

            with open(output_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)

        logger.info(f"视频已保存到: {output_path}")
        return output_path

    async def _get_video_info(self, video_path: str) -> Dict:
        """获取视频信息"""
        try:
            import cv2

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {}

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0

            cap.release()

            file_size = os.path.getsize(video_path)

            return {
                'duration': duration,
                'fps': int(fps),
                'resolution': (width, height),
                'file_size': file_size
            }

        except ImportError:
            logger.warning("OpenCV未安装，无法获取视频详细信息")
            return {'file_size': os.path.getsize(video_path)}
        except Exception as e:
            logger.warning(f"获取视频信息失败: {e}")
            return {'file_size': os.path.getsize(video_path)}

    async def shutdown(self):
        """关闭引擎"""
        await self._safe_cleanup_session("引擎关闭时")
        self.status = VideoEngineStatus.OFFLINE
        logger.info("CogVideoX-Flash引擎已关闭")

    def __del__(self):
        """析构函数，确保会话被清理"""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            logger.warning("引擎析构时发现未关闭的HTTP会话，强制清理")
            # 注意：在析构函数中不能使用await，所以只能记录警告

    async def _safe_cleanup_session(self, context: str = ""):
        """安全清理HTTP会话，避免事件循环冲突"""
        if not self.session:
            return

        try:
            # 检查当前事件循环
            try:
                current_loop = asyncio.get_running_loop()

                # 检查会话的连接器是否绑定到不同的事件循环
                if hasattr(self.session, '_connector') and hasattr(self.session._connector, '_loop'):
                    session_loop = self.session._connector._loop
                    if session_loop and session_loop != current_loop:
                        logger.warning(f"{context}检测到事件循环不匹配，直接清理会话引用")
                        self.session = None
                        return

            except RuntimeError:
                # 没有运行中的事件循环，直接清理
                logger.warning(f"{context}没有运行中的事件循环，直接清理会话引用")
                self.session = None
                return

            # 正常情况下关闭会话，不使用超时
            if not self.session.closed:
                try:
                    await self.session.close()
                    logger.info(f"{context}已安全清理HTTP会话")
                except Exception as close_error:
                    logger.warning(f"{context}关闭HTTP会话时出错: {close_error}")
                    # 即使关闭失败，也要设为None
                    self.session = None
                    return

        except Exception as e:
            logger.warning(f"{context}清理HTTP会话时出错: {e}")
        finally:
            # 确保会话引用被清理
            self.session = None
