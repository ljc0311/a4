# -*- coding: utf-8 -*-
"""
视频生成引擎管理器
负责引擎调度、负载均衡、重试机制和智能路由
"""

import asyncio
import time
import threading
from typing import List, Dict, Optional, Callable, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from .video_engine_base import (
    VideoGenerationEngine, VideoEngineType, VideoEngineStatus, 
    VideoGenerationConfig, VideoGenerationResult
)
from .video_engine_factory import get_video_engine_factory
from src.utils.logger import logger


class VideoRoutingStrategy(Enum):
    """视频路由策略"""
    FASTEST = "fastest"  # 选择最快的引擎
    CHEAPEST = "cheapest"  # 选择最便宜的引擎
    BEST_QUALITY = "best_quality"  # 选择质量最好的引擎
    LOAD_BALANCE = "load_balance"  # 负载均衡
    PRIORITY = "priority"  # 按优先级选择
    FREE_FIRST = "free_first"  # 优先使用免费引擎


class VideoEnginePreference(Enum):
    """视频引擎偏好"""
    FREE = "free"  # 偏好免费引擎
    QUALITY = "quality"  # 偏好高质量引擎
    SPEED = "speed"  # 偏好快速引擎
    LOCAL = "local"  # 偏好本地引擎


@dataclass
class VideoEnginePerformance:
    """视频引擎性能统计"""
    engine_type: VideoEngineType
    avg_generation_time: float = 0.0
    success_rate: float = 0.0
    avg_cost: float = 0.0
    last_used: float = 0.0
    total_requests: int = 0


class VideoEngineManager:
    """视频生成引擎管理器"""

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, config: Dict = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Dict = None):
        # 避免重复初始化
        if VideoEngineManager._initialized:
            return
        self.config = config or {}
        self.factory = get_video_engine_factory()
        
        # 路由配置
        self.routing_strategy = VideoRoutingStrategy(
            self.config.get('routing_strategy', 'priority')
        )
        self.engine_preferences = [
            VideoEnginePreference(pref) for pref in 
            self.config.get('engine_preferences', ['free', 'quality'])
        ]
        
        # 并发控制
        self.concurrent_limit = self.config.get('concurrent_limit', 3)
        self._active_tasks = 0
        
        # 性能统计
        self._performance_stats: Dict[VideoEngineType, VideoEnginePerformance] = {}
        
        # 引擎优先级（数字越小优先级越高）
        self.engine_priorities = {
            VideoEngineType.COGVIDEOX_FLASH: 1,  # 免费，优先级最高
            VideoEngineType.VHEER: 2,  # Vheer免费图生视频，优先级第二
            VideoEngineType.DOUBAO_SEEDANCE_PRO: 3,  # 豆包Pro，高质量付费引擎
            VideoEngineType.DOUBAO_SEEDANCE_LITE: 4,  # 豆包Lite，经济型付费引擎
            VideoEngineType.PIXVERSE: 5,
            VideoEngineType.REPLICATE_SVD: 6,
            VideoEngineType.HAIPER: 7,
            VideoEngineType.RUNWAY_ML: 8,
            VideoEngineType.PIKA_LABS: 9
        }
        
        VideoEngineManager._initialized = True
        logger.info(f"视频引擎管理器初始化完成，路由策略: {self.routing_strategy.value}")
    
    async def generate_video(self, config: VideoGenerationConfig,
                           preferred_engines: Optional[List[VideoEngineType]] = None,
                           progress_callback: Optional[Callable] = None,
                           project_manager=None, current_project_name=None) -> VideoGenerationResult:
        """生成视频（主要接口）"""
        # 🔧 修复：改进并发控制，等待而不是立即失败
        while self._active_tasks >= self.concurrent_limit:
            logger.debug(f"等待并发槽位释放，当前活跃任务: {self._active_tasks}/{self.concurrent_limit}")
            await asyncio.sleep(0.1)

        return await self._generate_video_internal(config, preferred_engines, progress_callback, project_manager, current_project_name)

    async def _generate_video_internal(self, config: VideoGenerationConfig,
                                     preferred_engines: Optional[List[VideoEngineType]] = None,
                                     progress_callback: Optional[Callable] = None,
                                     project_manager=None, current_project_name=None) -> VideoGenerationResult:
        """内部视频生成方法"""
        start_time = time.time()
        self._active_tasks += 1

        try:
            # 选择最佳引擎
            engine = await self._select_best_engine(config, preferred_engines)
            if not engine:
                return VideoGenerationResult(
                    success=False,
                    error_message="没有可用的视频生成引擎"
                )

            # 执行生成（带重试机制）
            result = await self._generate_with_retry(engine, config, progress_callback, project_manager, current_project_name)

            # 更新性能统计
            generation_time = time.time() - start_time
            self._update_performance_stats(engine.engine_type, result.success, generation_time)

            return result

        finally:
            self._active_tasks -= 1
    
    async def _select_best_engine(self, config: VideoGenerationConfig, 
                                 preferred_engines: Optional[List[VideoEngineType]] = None) -> Optional[VideoGenerationEngine]:
        """选择最佳引擎"""
        # 如果指定了偏好引擎，直接尝试使用，不检查available_engines
        if preferred_engines:
            for engine_type in preferred_engines:
                logger.info(f"尝试使用用户指定的引擎: {engine_type.value}")

                # 直接创建用户指定的引擎
                engine = await self.factory.create_engine(
                    engine_type,
                    self.config.get('engines', {}).get(engine_type.value, {})
                )

                if engine:
                    if engine.status == VideoEngineStatus.IDLE:
                        logger.info(f"用户指定的引擎 {engine_type.value} 初始化成功")
                        return engine
                    elif engine.status == VideoEngineStatus.ERROR:
                        logger.warning(f"用户指定的引擎 {engine_type.value} 初始化失败: {engine.last_error}")
                        # 对于用户明确选择的引擎，我们仍然尝试使用它
                        # 让具体的生成过程来处理错误
                        logger.info(f"仍然尝试使用用户指定的引擎 {engine_type.value}")
                        return engine
                    else:
                        logger.info(f"用户指定的引擎 {engine_type.value} 状态: {engine.status}")
                        return engine
                else:
                    logger.error(f"无法创建用户指定的引擎: {engine_type.value}")

            # 如果用户指定的引擎都无法使用，返回None而不是回退
            logger.error(f"用户指定的引擎都无法使用")
            return None

        # 只有在没有指定偏好引擎时，才获取available_engines
        available_engines = await self._get_available_engines()
        if not available_engines:
            logger.error("没有可用的视频生成引擎")
            return None
        
        # 根据路由策略选择引擎
        if self.routing_strategy == VideoRoutingStrategy.PRIORITY:
            return await self._select_by_priority(available_engines)
        elif self.routing_strategy == VideoRoutingStrategy.FREE_FIRST:
            return await self._select_free_first(available_engines)
        elif self.routing_strategy == VideoRoutingStrategy.FASTEST:
            return await self._select_fastest(available_engines)
        elif self.routing_strategy == VideoRoutingStrategy.CHEAPEST:
            return await self._select_cheapest(available_engines)
        elif self.routing_strategy == VideoRoutingStrategy.LOAD_BALANCE:
            return await self._select_load_balanced(available_engines)
        else:
            # 默认按优先级选择
            return await self._select_by_priority(available_engines)
    
    async def _get_available_engines(self) -> List[VideoEngineType]:
        """获取可用引擎列表"""
        available = []
        for engine_type in self.factory.get_available_engines():
            try:
                engine = await self.factory.create_engine(
                    engine_type,
                    self.config.get('engines', {}).get(engine_type.value, {})
                )
                # 🔧 修复：改进引擎可用性检查，ERROR状态的引擎也可以尝试重新初始化
                if engine:
                    if engine.status == VideoEngineStatus.OFFLINE:
                        # 尝试重新初始化离线引擎
                        try:
                            if await engine.initialize():
                                available.append(engine_type)
                                logger.info(f"引擎 {engine_type.value} 重新初始化成功")
                        except Exception as init_error:
                            logger.warning(f"引擎 {engine_type.value} 重新初始化失败: {init_error}")
                    elif engine.status in [VideoEngineStatus.IDLE, VideoEngineStatus.ERROR, VideoEngineStatus.BUSY]:
                        # 检查引擎是否还有并发容量
                        has_capacity = True
                        if hasattr(engine, 'current_tasks') and hasattr(engine, 'max_concurrent_tasks'):
                            has_capacity = engine.current_tasks < engine.max_concurrent_tasks

                        if has_capacity:
                            available.append(engine_type)
                            if engine.status == VideoEngineStatus.ERROR:
                                logger.info(f"引擎 {engine_type.value} 处于ERROR状态，但仍尝试使用（可能是临时问题）")
                            elif engine.status == VideoEngineStatus.BUSY:
                                logger.debug(f"引擎 {engine_type.value} 忙碌但仍有并发容量 ({engine.current_tasks}/{engine.max_concurrent_tasks})")
                        else:
                            logger.debug(f"引擎 {engine_type.value} 并发任务已满 ({engine.current_tasks}/{engine.max_concurrent_tasks})")
            except Exception as e:
                logger.warning(f"检查引擎 {engine_type.value} 可用性失败: {e}")

        return available

    def _is_engine_available(self, engine: VideoGenerationEngine) -> bool:
        """检查引擎是否可用（考虑并发容量）"""
        if engine.status == VideoEngineStatus.OFFLINE:
            return False
        elif engine.status in [VideoEngineStatus.IDLE, VideoEngineStatus.ERROR]:
            return True
        elif engine.status == VideoEngineStatus.BUSY:
            # 检查是否还有并发容量
            if hasattr(engine, 'current_tasks') and hasattr(engine, 'max_concurrent_tasks'):
                return engine.current_tasks < engine.max_concurrent_tasks
            return False
        return False

    async def _select_by_priority(self, available_engines: List[VideoEngineType]) -> Optional[VideoGenerationEngine]:
        """按优先级选择引擎"""
        # 按优先级排序
        sorted_engines = sorted(available_engines, key=lambda x: self.engine_priorities.get(x, 999))
        
        for engine_type in sorted_engines:
            engine = await self.factory.create_engine(
                engine_type,
                self.config.get('engines', {}).get(engine_type.value, {})
            )
            # 🔧 修复：检查引擎是否可用（包括BUSY但有并发容量的引擎）
            if engine and self._is_engine_available(engine):
                return engine
        
        return None
    
    async def _select_free_first(self, available_engines: List[VideoEngineType]) -> Optional[VideoGenerationEngine]:
        """优先选择免费引擎"""
        free_engines = []
        paid_engines = []
        
        for engine_type in available_engines:
            engine = await self.factory.create_engine(
                engine_type,
                self.config.get('engines', {}).get(engine_type.value, {})
            )
            if engine:
                engine_info = engine.get_engine_info()
                if engine_info.is_free:
                    free_engines.append(engine_type)
                else:
                    paid_engines.append(engine_type)
        
        # 先尝试免费引擎
        for engine_type in free_engines:
            engine = await self.factory.create_engine(
                engine_type,
                self.config.get('engines', {}).get(engine_type.value, {})
            )
            # 🔧 修复：使用统一的引擎可用性检查
            if engine and self._is_engine_available(engine):
                if engine.status == VideoEngineStatus.ERROR:
                    logger.info(f"尝试使用ERROR状态的免费引擎 {engine_type.value}（可能是临时问题）")
                return engine
        
        # 再尝试付费引擎
        for engine_type in paid_engines:
            engine = await self.factory.create_engine(
                engine_type,
                self.config.get('engines', {}).get(engine_type.value, {})
            )
            if engine and self._is_engine_available(engine):
                return engine
        
        return None

    async def _select_fastest(self, available_engines: List[VideoEngineType]) -> Optional[VideoGenerationEngine]:
        """选择最快的引擎"""
        fastest_engine = None
        fastest_time = float('inf')

        for engine_type in available_engines:
            stats = self._performance_stats.get(engine_type)
            if stats and stats.avg_generation_time < fastest_time:
                fastest_time = stats.avg_generation_time
                fastest_engine = engine_type

        if fastest_engine:
            return await self.factory.create_engine(
                fastest_engine,
                self.config.get('engines', {}).get(fastest_engine.value, {})
            )

        # 如果没有性能统计，按优先级选择
        return await self._select_by_priority(available_engines)

    async def _select_cheapest(self, available_engines: List[VideoEngineType]) -> Optional[VideoGenerationEngine]:
        """选择最便宜的引擎"""
        cheapest_engine = None
        lowest_cost = float('inf')

        for engine_type in available_engines:
            engine = await self.factory.create_engine(
                engine_type,
                self.config.get('engines', {}).get(engine_type.value, {})
            )
            if engine:
                engine_info = engine.get_engine_info()
                if engine_info.cost_per_second < lowest_cost:
                    lowest_cost = engine_info.cost_per_second
                    cheapest_engine = engine_type

        if cheapest_engine:
            return await self.factory.create_engine(
                cheapest_engine,
                self.config.get('engines', {}).get(cheapest_engine.value, {})
            )

        return None

    async def _select_load_balanced(self, available_engines: List[VideoEngineType]) -> Optional[VideoGenerationEngine]:
        """负载均衡选择引擎"""
        # 选择最近使用时间最早的引擎
        least_used_engine = None
        earliest_time = float('inf')

        for engine_type in available_engines:
            stats = self._performance_stats.get(engine_type)
            last_used = stats.last_used if stats else 0
            if last_used < earliest_time:
                earliest_time = last_used
                least_used_engine = engine_type

        if least_used_engine:
            return await self.factory.create_engine(
                least_used_engine,
                self.config.get('engines', {}).get(least_used_engine.value, {})
            )

        return None

    async def _generate_with_retry(self, engine: VideoGenerationEngine,
                                  config: VideoGenerationConfig,
                                  progress_callback: Optional[Callable] = None,
                                  project_manager=None, current_project_name=None,
                                  max_retries: int = 2) -> VideoGenerationResult:
        """带重试机制的生成"""
        last_error = ""
        retry_delay = 1.0
        backoff_factor = 2.0

        for attempt in range(max_retries + 1):
            try:
                if progress_callback:
                    progress_callback(f"尝试生成视频 (第 {attempt + 1} 次)...")

                # 传递项目信息给引擎的generate_video方法
                result = await engine.generate_video(config, progress_callback, project_manager, current_project_name)

                if result.success:
                    return result
                else:
                    last_error = result.error_message
                    logger.warning(f"引擎 {engine.engine_type.value} 生成失败 (第 {attempt + 1} 次): {last_error}")

            except asyncio.CancelledError:
                logger.warning(f"引擎 {engine.engine_type.value} 任务被取消")
                return VideoGenerationResult(
                    success=False,
                    error_message="视频生成任务被取消"
                )
            except Exception as e:
                last_error = str(e)
                logger.error(f"引擎 {engine.engine_type.value} 生成异常 (第 {attempt + 1} 次): {e}")

            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
                retry_delay *= backoff_factor

        return VideoGenerationResult(
            success=False,
            error_message=f"生成失败，已重试 {max_retries} 次。最后错误: {last_error}"
        )

    def _update_performance_stats(self, engine_type: VideoEngineType,
                                 success: bool, generation_time: float):
        """更新性能统计"""
        if engine_type not in self._performance_stats:
            self._performance_stats[engine_type] = VideoEnginePerformance(engine_type=engine_type)

        stats = self._performance_stats[engine_type]
        stats.total_requests += 1
        stats.last_used = time.time()

        if success:
            # 更新平均生成时间
            if stats.avg_generation_time == 0:
                stats.avg_generation_time = generation_time
            else:
                stats.avg_generation_time = (stats.avg_generation_time + generation_time) / 2

        # 更新成功率
        engine = self.factory.get_engine(engine_type)
        if engine:
            stats.success_rate = (engine.success_count / engine.request_count * 100) if engine.request_count > 0 else 0



    def get_engine_statistics(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        stats = {
            "active_tasks": self._active_tasks,
            "concurrent_limit": self.concurrent_limit,
            "routing_strategy": self.routing_strategy.value,
            "engine_preferences": [pref.value for pref in self.engine_preferences],
            "engines": {}
        }

        # 获取各引擎统计
        for engine_type, engine in self.factory._engines.items():
            stats["engines"][engine_type.value] = engine.get_statistics()

        # 添加性能统计
        stats["performance"] = {}
        for engine_type, perf in self._performance_stats.items():
            stats["performance"][engine_type.value] = {
                "avg_generation_time": perf.avg_generation_time,
                "success_rate": perf.success_rate,
                "total_requests": perf.total_requests,
                "last_used": perf.last_used
            }

        return stats

    async def test_all_engines(self) -> Dict[VideoEngineType, bool]:
        """测试所有引擎"""
        return await self.factory.test_all_engines()

    async def shutdown(self):
        """关闭管理器"""
        await self.factory.shutdown_all_engines()
        logger.info("视频引擎管理器已关闭")
