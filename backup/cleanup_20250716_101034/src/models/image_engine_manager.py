# -*- coding: utf-8 -*-
"""
图像生成引擎管理器
负责引擎调度、负载均衡、重试机制和智能路由
"""

import asyncio
import time
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
from .image_engine_base import (
    ImageGenerationEngine, EngineType, EngineStatus, 
    GenerationConfig, GenerationResult
)
from .image_engine_factory import get_engine_factory
from src.utils.logger import logger


class RoutingStrategy(Enum):
    """路由策略"""
    FASTEST = "fastest"  # 选择最快的引擎
    CHEAPEST = "cheapest"  # 选择最便宜的引擎
    BEST_QUALITY = "best_quality"  # 选择质量最好的引擎
    LOAD_BALANCE = "load_balance"  # 负载均衡
    PRIORITY = "priority"  # 按优先级选择
    RANDOM = "random"  # 随机选择


@dataclass
class EnginePreference:
    """引擎偏好设置"""
    engine_type: EngineType
    priority: int = 1  # 优先级，数字越小优先级越高
    max_cost_per_image: float = float('inf')  # 最大单张成本
    max_wait_time: float = 60.0  # 最大等待时间（秒）
    enabled: bool = True
    

class ImageEngineManager:
    """图像生成引擎管理器"""
    
    def __init__(self):
        self.factory = get_engine_factory()
        self.routing_strategy = RoutingStrategy.PRIORITY
        self.engine_preferences: List[EnginePreference] = []
        self.retry_config = {
            'max_retries': 3,
            'retry_delay': 1.0,
            'backoff_factor': 2.0
        }
        self.concurrent_limit = 5
        self._active_tasks = 0
        self._task_queue = asyncio.Queue()
        self._processing_queue = False
        
        # 性能统计
        self.performance_stats: Dict[EngineType, Dict] = {}
        
        # 设置默认引擎偏好
        self._setup_default_preferences()
    
    def _setup_default_preferences(self):
        """设置默认引擎偏好"""
        default_preferences = [
            EnginePreference(EngineType.COMFYUI_LOCAL, priority=1, max_cost_per_image=0.0),
            EnginePreference(EngineType.POLLINATIONS, priority=2, max_cost_per_image=0.0),
            EnginePreference(EngineType.COGVIEW_3_FLASH, priority=3, max_cost_per_image=0.0),
            EnginePreference(EngineType.COMFYUI_CLOUD, priority=4, max_cost_per_image=0.1),
            EnginePreference(EngineType.OPENAI_DALLE, priority=5, max_cost_per_image=0.5),
            EnginePreference(EngineType.STABILITY_AI, priority=6, max_cost_per_image=0.3),
        ]
        self.engine_preferences = default_preferences
    
    async def initialize_engines(self, engine_configs: Dict[EngineType, Dict]):
        """初始化引擎"""
        logger.info("开始初始化图像生成引擎...")
        
        for engine_type, config in engine_configs.items():
            if config.get('enabled', False):
                engine = await self.factory.create_engine(engine_type, config)
                if engine:
                    # 初始化性能统计
                    self.performance_stats[engine_type] = {
                        'avg_generation_time': 0.0,
                        'success_rate': 100.0,
                        'last_used': 0.0,
                        'total_requests': 0
                    }
                    logger.info(f"引擎 {engine_type.value} 初始化成功")
                else:
                    logger.warning(f"引擎 {engine_type.value} 初始化失败")
    
    async def generate_image(self, config: GenerationConfig, 
                           preferred_engines: Optional[List[EngineType]] = None,
                           progress_callback: Optional[Callable] = None,
                           project_manager=None, current_project_name=None) -> GenerationResult:
        """生成图像（主要接口）"""
        start_time = time.time()
        
        # 如果并发任务过多，加入队列等待
        if self._active_tasks >= self.concurrent_limit:
            await self._task_queue.put((config, preferred_engines, progress_callback, project_manager, current_project_name))
            if not self._processing_queue:
                asyncio.create_task(self._process_queue())
            return GenerationResult(success=False, error_message="任务已加入队列等待处理")
        
        self._active_tasks += 1
        
        try:
            # 选择最佳引擎
            engine = await self._select_best_engine(config, preferred_engines)
            if not engine:
                return GenerationResult(
                    success=False, 
                    error_message="没有可用的图像生成引擎"
                )
            
            # 执行生成（带重试机制）
            result = await self._generate_with_retry(engine, config, progress_callback, project_manager, current_project_name)
            
            # 更新性能统计
            generation_time = time.time() - start_time
            self._update_performance_stats(engine.engine_type, result.success, generation_time)
            
            return result
            
        finally:
            self._active_tasks -= 1
    
    async def _select_best_engine(self, config: GenerationConfig, 
                                 preferred_engines: Optional[List[EngineType]] = None) -> Optional[ImageGenerationEngine]:
        """选择最佳引擎"""
        available_engines = self._get_available_engines(preferred_engines)
        
        if not available_engines:
            return None
        
        if self.routing_strategy == RoutingStrategy.PRIORITY:
            return self._select_by_priority(available_engines)
        elif self.routing_strategy == RoutingStrategy.FASTEST:
            return self._select_fastest(available_engines)
        elif self.routing_strategy == RoutingStrategy.CHEAPEST:
            return self._select_cheapest(available_engines, config)
        elif self.routing_strategy == RoutingStrategy.LOAD_BALANCE:
            return self._select_load_balanced(available_engines)
        else:
            return available_engines[0] if available_engines else None
    
    def _get_available_engines(self, preferred_engines: Optional[List[EngineType]] = None) -> List[ImageGenerationEngine]:
        """获取可用引擎列表"""
        available = []
        
        # 确定要检查的引擎类型
        engine_types = preferred_engines if preferred_engines else [pref.engine_type for pref in self.engine_preferences if pref.enabled]
        
        for engine_type in engine_types:
            engine = self.factory.get_engine(engine_type)
            if engine and engine.status in [EngineStatus.IDLE, EngineStatus.BUSY]:
                available.append(engine)
        
        return available
    
    def _select_by_priority(self, engines: List[ImageGenerationEngine]) -> Optional[ImageGenerationEngine]:
        """按优先级选择引擎"""
        # 按优先级排序
        priority_map = {pref.engine_type: pref.priority for pref in self.engine_preferences}
        engines.sort(key=lambda e: priority_map.get(e.engine_type, 999))
        return engines[0] if engines else None
    
    def _select_fastest(self, engines: List[ImageGenerationEngine]) -> Optional[ImageGenerationEngine]:
        """选择最快的引擎"""
        fastest_engine = None
        fastest_time = float('inf')
        
        for engine in engines:
            stats = self.performance_stats.get(engine.engine_type, {})
            avg_time = stats.get('avg_generation_time', float('inf'))
            if avg_time < fastest_time:
                fastest_time = avg_time
                fastest_engine = engine
        
        return fastest_engine or engines[0]
    
    def _select_cheapest(self, engines: List[ImageGenerationEngine], config: GenerationConfig) -> Optional[ImageGenerationEngine]:
        """选择最便宜的引擎"""
        cheapest_engine = None
        lowest_cost = float('inf')
        
        for engine in engines:
            engine_info = engine.get_engine_info()
            estimated_cost = engine_info.cost_per_image * config.batch_size
            if estimated_cost < lowest_cost:
                lowest_cost = estimated_cost
                cheapest_engine = engine
        
        return cheapest_engine or engines[0]
    
    def _select_load_balanced(self, engines: List[ImageGenerationEngine]) -> Optional[ImageGenerationEngine]:
        """负载均衡选择"""
        # 选择最近使用最少的引擎
        least_used_engine = None
        earliest_time = float('inf')
        
        for engine in engines:
            stats = self.performance_stats.get(engine.engine_type, {})
            last_used = stats.get('last_used', 0)
            if last_used < earliest_time:
                earliest_time = last_used
                least_used_engine = engine
        
        return least_used_engine or engines[0]
    
    async def _generate_with_retry(self, engine: ImageGenerationEngine, 
                                  config: GenerationConfig,
                                  progress_callback: Optional[Callable] = None,
                                  project_manager=None, current_project_name=None) -> GenerationResult:
        """带重试机制的生成"""
        max_retries = self.retry_config['max_retries']
        retry_delay = self.retry_config['retry_delay']
        backoff_factor = self.retry_config['backoff_factor']
        
        last_error = ""
        
        for attempt in range(max_retries + 1):
            try:
                if progress_callback:
                    progress_callback(f"尝试生成图像 (第 {attempt + 1} 次)...")
                
                # 传递项目信息给引擎的generate方法
                result = await engine.generate(config, progress_callback, project_manager, current_project_name)
                
                if result.success:
                    return result
                else:
                    last_error = result.error_message
                    logger.warning(f"引擎 {engine.engine_type.value} 生成失败 (第 {attempt + 1} 次): {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"引擎 {engine.engine_type.value} 生成异常 (第 {attempt + 1} 次): {e}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
                retry_delay *= backoff_factor
        
        return GenerationResult(
            success=False,
            error_message=f"生成失败，已重试 {max_retries} 次。最后错误: {last_error}"
        )
    
    def _update_performance_stats(self, engine_type: EngineType, success: bool, generation_time: float):
        """更新性能统计"""
        if engine_type not in self.performance_stats:
            self.performance_stats[engine_type] = {
                'avg_generation_time': 0.0,
                'success_rate': 100.0,
                'last_used': 0.0,
                'total_requests': 0
            }
        
        stats = self.performance_stats[engine_type]
        stats['total_requests'] += 1
        stats['last_used'] = time.time()
        
        # 更新平均生成时间（指数移动平均）
        if stats['avg_generation_time'] == 0:
            stats['avg_generation_time'] = generation_time
        else:
            alpha = 0.3  # 平滑因子
            stats['avg_generation_time'] = alpha * generation_time + (1 - alpha) * stats['avg_generation_time']
        
        # 更新成功率
        engine = self.factory.get_engine(engine_type)
        if engine:
            engine_status = engine.get_status()
            stats['success_rate'] = engine_status['success_rate']
    
    async def _process_queue(self):
        """处理任务队列"""
        self._processing_queue = True
        
        while not self._task_queue.empty() and self._active_tasks < self.concurrent_limit:
            try:
                config, preferred_engines, progress_callback = await asyncio.wait_for(
                    self._task_queue.get(), timeout=1.0
                )
                
                # 异步处理任务
                asyncio.create_task(
                    self.generate_image(config, preferred_engines, progress_callback)
                )
                
            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.error(f"处理队列任务时出错: {e}")
        
        self._processing_queue = False
    
    def set_routing_strategy(self, strategy: RoutingStrategy):
        """设置路由策略"""
        self.routing_strategy = strategy
        logger.info(f"路由策略已设置为: {strategy.value}")
    
    def update_engine_preferences(self, preferences: List[EnginePreference]):
        """更新引擎偏好"""
        self.engine_preferences = preferences
        logger.info("引擎偏好设置已更新")
    
    def get_manager_status(self) -> Dict:
        """获取管理器状态"""
        return {
            'routing_strategy': self.routing_strategy.value,
            'active_tasks': self._active_tasks,
            'queue_size': self._task_queue.qsize(),
            'concurrent_limit': self.concurrent_limit,
            'available_engines': len(self._get_available_engines()),
            'performance_stats': self.performance_stats,
            'engine_preferences': [
                {
                    'engine_type': pref.engine_type.value,
                    'priority': pref.priority,
                    'enabled': pref.enabled,
                    'max_cost': pref.max_cost_per_image
                }
                for pref in self.engine_preferences
            ]
        }
    
    async def test_all_connections(self) -> Dict[str, bool]:
        """测试所有引擎的连接"""
        results = {}

        for engine_type in self.factory.get_active_engines():
            engine = self.factory.get_engine(engine_type)
            if engine:
                try:
                    # 测试引擎连接
                    connection_result = await engine.test_connection()
                    results[engine_type.value] = connection_result
                    logger.info(f"引擎 {engine_type.value} 连接测试: {'成功' if connection_result else '失败'}")
                except Exception as e:
                    results[engine_type.value] = False
                    logger.error(f"引擎 {engine_type.value} 连接测试异常: {e}")
            else:
                results[engine_type.value] = False
                logger.warning(f"引擎 {engine_type.value} 未初始化")

        return results

    async def cleanup(self):
        """清理资源"""
        await self.factory.cleanup_all()
        logger.info("引擎管理器清理完成")