#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务管理器
统一管理所有AI服务的生命周期、协调服务间的交互
"""

import asyncio
import threading
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass
from enum import Enum

from src.utils.logger import logger
from .api_manager import APIManager
from .service_base import ServiceBase, ServiceResult
from src.services.llm_service import LLMService
from src.services.image_service import ImageService
from src.services.voice_service import VoiceService
from src.utils.memory_optimizer import memory_manager, monitor_memory
from src.utils.async_task_manager import task_manager, create_task

class ServiceType(Enum):
    """服务类型枚举"""
    LLM = "llm"
    IMAGE = "image"
    VOICE = "voice"
    TRANSLATION = "translation"
    VIDEO = "video"

@dataclass
class WorkflowStep:
    """工作流步骤"""
    service_type: ServiceType
    method: str
    params: Dict[str, Any]
    depends_on: List[str] = None  # 依赖的步骤ID
    step_id: str = ""
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []
        if not self.step_id:
            self.step_id = f"{self.service_type.value}_{self.method}"

class ServiceManager:
    """服务管理器"""

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, config_manager=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_manager=None):
        # 避免重复初始化
        if ServiceManager._initialized:
            return

        self.api_manager = APIManager(config_manager)
        self.services: Dict[ServiceType, ServiceBase] = {}
        self.workflows: Dict[str, List[WorkflowStep]] = {}
        
        # 使用新的任务管理器替代直接管理任务
        self.task_manager = task_manager

        # 初始化服务
        self._initialize_services()
        
        # 注册内存清理回调
        memory_manager.register_cleanup_callback(self._cleanup_services)

        ServiceManager._initialized = True
        logger.info("服务管理器初始化完成")
    
    def _cleanup_services(self):
        """清理服务资源"""
        try:
            for service in self.services.values():
                if hasattr(service, 'cleanup_resources'):
                    service.cleanup_resources()
            logger.info("服务资源清理完成")
        except Exception as e:
            logger.error(f"清理服务资源失败: {e}")
    
    async def initialize(self):
        """异步初始化方法"""
        try:
            # 初始化API管理器
            await self.api_manager.initialize()
            
            # 初始化所有服务
            for service in self.services.values():
                if hasattr(service, 'initialize'):
                    await service.initialize()
            
            logger.info("服务管理器异步初始化完成")
            
        except Exception as e:
            logger.error(f"服务管理器异步初始化失败: {e}")
            raise
    
    def _initialize_services(self):
        """初始化所有服务"""
        try:
            # 初始化LLM服务
            self.services[ServiceType.LLM] = LLMService(self.api_manager)
            logger.info("LLM服务初始化完成")
            
            # 初始化图像服务
            self.services[ServiceType.IMAGE] = ImageService(self.api_manager)
            logger.info("图像服务初始化完成")
            
            # 初始化语音服务
            self.services[ServiceType.VOICE] = VoiceService(self.api_manager)
            logger.info("语音服务初始化完成")
            
            # TODO: 初始化其他服务
            # self.services[ServiceType.TRANSLATION] = TranslationService(self.api_manager)
            # self.services[ServiceType.VIDEO] = VideoService(self.api_manager)
            
        except Exception as e:
            logger.error(f"服务初始化失败: {e}")
            raise
    
    def get_service(self, service_type: ServiceType) -> Optional[ServiceBase]:
        """获取指定类型的服务"""
        return self.services.get(service_type)
    
    @monitor_memory("服务方法执行")
    async def execute_service_method(self, service_type: ServiceType, method: str, **kwargs) -> ServiceResult:
        """执行服务方法 - 优化版本"""
        service = self.get_service(service_type)
        if not service:
            return ServiceResult(
                success=False,
                error=f"服务类型 {service_type.value} 不存在"
            )
        
        if not hasattr(service, method):
            return ServiceResult(
                success=False,
                error=f"服务 {service_type.value} 没有方法 {method}"
            )
        
        try:
            method_func = getattr(service, method)
            
            # 创建任务名称
            task_name = f"{service_type.value}.{method}"
            
            if asyncio.iscoroutinefunction(method_func):
                # 对于异步方法，使用任务管理器
                coro = method_func(**kwargs)
                task_id = create_task(coro, name=task_name)
                
                # 等待任务完成
                return await self.task_manager.wait_for_task(task_id)
            else:
                # 对于同步方法，直接执行
                return method_func(**kwargs)
                
        except Exception as e:
            logger.error(f"执行服务方法失败: {service_type.value}.{method} - {e}")
            return ServiceResult(
                success=False,
                error=str(e)
            )
    
    def register_workflow(self, workflow_name: str, steps: List[WorkflowStep]):
        """注册工作流"""
        self.workflows[workflow_name] = steps
        logger.info(f"已注册工作流: {workflow_name}，包含 {len(steps)} 个步骤")
    
    async def execute_workflow(self, workflow_name: str, initial_data: Dict[str, Any] = None, 
                             progress_callback=None) -> Dict[str, ServiceResult]:
        """执行工作流"""
        if workflow_name not in self.workflows:
            raise ValueError(f"工作流 {workflow_name} 不存在")
        
        steps = self.workflows[workflow_name]
        results: Dict[str, ServiceResult] = {}
        step_data = initial_data or {}
        
        logger.info(f"开始执行工作流: {workflow_name}")
        
        # 构建依赖图
        dependency_graph = self._build_dependency_graph(steps)
        
        # 按依赖顺序执行步骤
        executed_steps = set()
        
        while len(executed_steps) < len(steps):
            # 找到可以执行的步骤（所有依赖都已完成）
            ready_steps = []
            for step in steps:
                if step.step_id not in executed_steps:
                    if all(dep in executed_steps for dep in step.depends_on):
                        ready_steps.append(step)
            
            if not ready_steps:
                # 检查是否有循环依赖
                remaining_steps = [s for s in steps if s.step_id not in executed_steps]
                raise RuntimeError(f"检测到循环依赖或无法满足的依赖: {[s.step_id for s in remaining_steps]}")
            
            # 并行执行准备好的步骤
            tasks = []
            for step in ready_steps:
                # 准备步骤参数
                step_params = step.params.copy()
                
                # 从之前的结果中获取依赖数据
                for dep_id in step.depends_on:
                    if dep_id in results and results[dep_id].success:
                        step_params[f"{dep_id}_result"] = results[dep_id].data
                
                # 添加全局数据
                step_params.update(step_data)
                
                task = self._execute_workflow_step(step, step_params)
                tasks.append((step.step_id, task))
            
            # 等待所有任务完成
            for step_id, task in tasks:
                try:
                    result = await task
                    results[step_id] = result
                    executed_steps.add(step_id)
                    
                    if progress_callback:
                        progress = len(executed_steps) / len(steps)
                        progress_callback(progress, f"完成步骤: {step_id}")
                    
                    logger.info(f"工作流步骤完成: {step_id} - 成功: {result.success}")
                    
                except Exception as e:
                    logger.error(f"工作流步骤失败: {step_id} - {e}")
                    results[step_id] = ServiceResult(
                        success=False,
                        error=str(e)
                    )
                    executed_steps.add(step_id)
        
        logger.info(f"工作流执行完成: {workflow_name}")
        return results
    
    def _build_dependency_graph(self, steps: List[WorkflowStep]) -> Dict[str, List[str]]:
        """构建依赖图"""
        graph = {}
        for step in steps:
            graph[step.step_id] = step.depends_on.copy()
        return graph
    
    async def _execute_workflow_step(self, step: WorkflowStep, params: Dict[str, Any]) -> ServiceResult:
        """执行工作流步骤"""
        return await self.execute_service_method(
            service_type=step.service_type,
            method=step.method,
            **params
        )
    
    def create_video_generation_workflow(self, text: str, style: str = None) -> str:
        """创建视频生成工作流"""
        # 如果没有指定风格，从配置中获取默认风格
        if style is None:
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            style = config_manager.get_setting("default_style", "电影风格")
        
        workflow_name = f"video_generation_{int(asyncio.get_event_loop().time())}"
        
        steps = [
            # 步骤1: 生成分镜
            WorkflowStep(
                service_type=ServiceType.LLM,
                method="generate_storyboard",
                params={"text": text, "style": style},
                step_id="generate_storyboard"
            ),
            
            # 步骤2: 优化提示词（依赖分镜生成）
            WorkflowStep(
                service_type=ServiceType.LLM,
                method="optimize_prompt",
                params={"style": style},
                depends_on=["generate_storyboard"],
                step_id="optimize_prompts"
            ),
            
            # 步骤3: 生成图像（依赖提示词优化）
            WorkflowStep(
                service_type=ServiceType.IMAGE,
                method="generate_batch_images",
                params={"style": style},
                depends_on=["optimize_prompts"],
                step_id="generate_images"
            ),
            
            # 步骤4: 生成语音（依赖分镜生成）
            WorkflowStep(
                service_type=ServiceType.VOICE,
                method="batch_text_to_speech",
                params={"voice": "中文女声"},
                depends_on=["generate_storyboard"],
                step_id="generate_voice"
            )
        ]
        
        self.register_workflow(workflow_name, steps)
        return workflow_name
    
    async def check_all_services(self) -> Dict[str, Any]:
        """检查所有服务的状态"""
        try:
            status = {
                'api_manager': 'running',
                'services': {},
                'all_healthy': True
            }
            
            # 检查每个服务的状态
            for service_type, service in self.services.items():
                try:
                    service_status = service.get_status()
                    status['services'][service_type.value] = service_status
                    if service_status.get('status') != 'running':
                        status['all_healthy'] = False
                except Exception as e:
                    logger.error(f"检查服务 {service_type.value} 状态失败: {e}")
                    status['services'][service_type.value] = {'status': 'error', 'error': str(e)}
                    status['all_healthy'] = False
            
            return status
            
        except Exception as e:
            logger.error(f"检查服务状态失败: {e}")
            return {'all_healthy': False, 'error': str(e)}
    
    def get_available_providers(self, service_type: ServiceType) -> List[str]:
        """获取指定服务类型的可用提供商"""
        try:
            # 优先使用服务自己的get_available_providers方法
            if service_type in self.services:
                service = self.services[service_type]
                if hasattr(service, 'get_available_providers'):
                    return service.get_available_providers()
            
            # 回退到API管理器方式
            from .api_manager import APIType
            
            if service_type == ServiceType.LLM:
                api_type = APIType.LLM
            elif service_type == ServiceType.IMAGE:
                api_type = APIType.IMAGE_GENERATION
            elif service_type == ServiceType.VOICE:
                api_type = APIType.TEXT_TO_SPEECH
            else:
                return []
            
            apis = self.api_manager.get_available_apis(api_type)
            providers = list(set([api.provider for api in apis]))
            return providers
            
        except Exception as e:
            logger.error(f"获取 {service_type.value} 可用提供商失败: {e}")
            return []
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取所有服务的状态"""
        status = {
            'api_manager': self.api_manager.get_api_status(),
            'services': {},
            'workflows': list(self.workflows.keys()),
            'running_tasks': list(self.running_tasks.keys())
        }
        
        for service_type, service in self.services.items():
            status['services'][service_type.value] = service.get_status()
        
        return status
    
    def reload_configs(self):
        """重新加载配置"""
        self.api_manager.reload_configs()
        logger.info("服务管理器配置已重新加载")
    
    async def shutdown(self):
        """关闭服务管理器"""
        # 取消所有运行中的任务
        for task_name, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"已取消任务: {task_name}")
        
        # 等待所有任务完成
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
        
        # 停止所有服务
        for service in self.services.values():
            service.stop()
        
        # 关闭API管理器
        self.api_manager.shutdown()
        
        logger.info("服务管理器已关闭")
    
    # 便捷方法
    async def generate_storyboard(self, text: str, style: str = None, provider: str = None) -> ServiceResult:
        """生成分镜（便捷方法）"""
        # 如果没有指定风格，从配置中获取默认风格
        if style is None:
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            style = config_manager.get_setting("default_style", "电影风格")
        
        return await self.execute_service_method(
            ServiceType.LLM, "generate_storyboard",
            text=text, style=style, provider=provider
        )
    
    async def generate_image(self, prompt: str, style: str = "写实摄影风格", provider: str = None, **kwargs) -> ServiceResult:
        """生成图像（便捷方法）"""
        return await self.execute_service_method(
            ServiceType.IMAGE, "generate_image",
            prompt=prompt, style=style, provider=provider, **kwargs
        )
    
    async def text_to_speech(self, text: str, voice: str = "中文女声", provider: str = None, **kwargs) -> ServiceResult:
        """文本转语音（便捷方法）"""
        return await self.execute_service_method(
            ServiceType.VOICE, "text_to_speech",
            text=text, voice=voice, provider=provider, **kwargs
        )