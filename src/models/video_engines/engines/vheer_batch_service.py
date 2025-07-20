# -*- coding: utf-8 -*-
"""
Vheer.com 批量图生视频服务
提供批量处理和队列管理功能
"""

import os
import asyncio
import time
from typing import List, Dict, Optional, Callable, Union
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from .vheer_engine import VheerVideoEngine
from ..video_engine_base import VideoGenerationConfig, VideoGenerationResult
from src.utils.logger import logger


@dataclass
class BatchVideoTask:
    """批量视频生成任务"""
    task_id: str
    image_path: str
    prompt: str = ""
    duration: float = 5.0
    width: int = 1024
    height: int = 1024
    status: str = "pending"  # pending, processing, completed, failed
    result: Optional[VideoGenerationResult] = None
    error_message: str = ""
    start_time: Optional[float] = None
    end_time: Optional[float] = None


@dataclass
class BatchVideoResult:
    """批量视频生成结果"""
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    success_rate: float
    total_duration: float
    video_paths: List[str]
    failed_tasks_info: List[Dict]


class VheerBatchVideoService:
    """Vheer批量视频生成服务"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', 'output/videos/vheer_batch')
        self.max_concurrent = self.config.get('max_concurrent', 1)  # 默认单并发，避免被网站限制
        self.headless = self.config.get('headless', True)
        self.retry_count = self.config.get('retry_count', 2)
        self.retry_delay = self.config.get('retry_delay', 30)  # 重试间隔30秒
        
        # 任务队列
        self.task_queue: List[BatchVideoTask] = []
        self.processing_tasks: Dict[str, BatchVideoTask] = {}
        self.completed_tasks: Dict[str, BatchVideoTask] = {}
        
        # 统计信息
        self.total_processed = 0
        self.total_success = 0
        self.total_failed = 0
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"Vheer批量视频服务初始化完成")
        logger.info(f"输出目录: {self.output_dir}")
        logger.info(f"最大并发: {self.max_concurrent}")
        
    async def add_batch_tasks(self, image_paths: List[str], 
                            prompts: List[str] = None,
                            base_prompt: str = "",
                            duration: float = 5.0,
                            width: int = 1024,
                            height: int = 1024) -> List[str]:
        """添加批量任务"""
        
        if prompts is None:
            prompts = [""] * len(image_paths)
        elif len(prompts) != len(image_paths):
            # 如果提示词数量不匹配，用空字符串补齐或截断
            if len(prompts) < len(image_paths):
                prompts.extend([""] * (len(image_paths) - len(prompts)))
            else:
                prompts = prompts[:len(image_paths)]
                
        task_ids = []
        
        for i, image_path in enumerate(image_paths):
            # 验证图像文件存在
            if not os.path.exists(image_path):
                logger.warning(f"⚠️ 图像文件不存在，跳过: {image_path}")
                continue
                
            # 生成任务ID
            task_id = f"vheer_task_{int(time.time())}_{i}"
            
            # 组合提示词
            full_prompt = f"{base_prompt} {prompts[i]}".strip()
            
            # 创建任务
            task = BatchVideoTask(
                task_id=task_id,
                image_path=image_path,
                prompt=full_prompt,
                duration=duration,
                width=width,
                height=height
            )
            
            self.task_queue.append(task)
            task_ids.append(task_id)
            
            logger.info(f"📝 添加任务: {task_id} - {os.path.basename(image_path)}")
            
        logger.info(f"✅ 批量任务添加完成，共 {len(task_ids)} 个任务")
        return task_ids
        
    async def process_batch(self, progress_callback: Optional[Callable] = None) -> BatchVideoResult:
        """处理批量任务"""
        
        if not self.task_queue:
            logger.warning("⚠️ 任务队列为空")
            return BatchVideoResult(
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                success_rate=0.0,
                total_duration=0.0,
                video_paths=[],
                failed_tasks_info=[]
            )
            
        total_tasks = len(self.task_queue)
        start_time = time.time()
        
        logger.info(f"🚀 开始批量处理，共 {total_tasks} 个任务")
        logger.info(f"🔧 并发设置: {self.max_concurrent}")
        
        if progress_callback:
            progress_callback(0.0, f"开始批量处理 {total_tasks} 个任务...")
            
        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # 创建任务协程
        async def process_single_task(task: BatchVideoTask):
            async with semaphore:
                return await self._process_single_task(task, progress_callback)
                
        # 并发执行所有任务
        tasks = [process_single_task(task) for task in self.task_queue]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        completed_tasks = 0
        failed_tasks = 0
        video_paths = []
        failed_tasks_info = []
        
        for i, result in enumerate(results):
            task = self.task_queue[i]
            
            if isinstance(result, Exception):
                failed_tasks += 1
                failed_tasks_info.append({
                    'task_id': task.task_id,
                    'image_path': task.image_path,
                    'error': str(result)
                })
                logger.error(f"❌ 任务异常: {task.task_id} - {result}")
            elif result and result.success:
                completed_tasks += 1
                video_paths.append(result.video_path)
                logger.info(f"✅ 任务完成: {task.task_id}")
            else:
                failed_tasks += 1
                error_msg = result.error_message if result else "未知错误"
                failed_tasks_info.append({
                    'task_id': task.task_id,
                    'image_path': task.image_path,
                    'error': error_msg
                })
                logger.error(f"❌ 任务失败: {task.task_id} - {error_msg}")
                
        # 清空任务队列
        self.task_queue.clear()
        
        # 计算统计信息
        total_duration = time.time() - start_time
        success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0
        
        # 更新全局统计
        self.total_processed += total_tasks
        self.total_success += completed_tasks
        self.total_failed += failed_tasks
        
        # 创建结果对象
        batch_result = BatchVideoResult(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            success_rate=success_rate,
            total_duration=total_duration,
            video_paths=video_paths,
            failed_tasks_info=failed_tasks_info
        )
        
        # 打印总结
        logger.info("=" * 60)
        logger.info("📊 批量处理完成总结")
        logger.info(f"总任务数: {total_tasks}")
        logger.info(f"成功任务: {completed_tasks}")
        logger.info(f"失败任务: {failed_tasks}")
        logger.info(f"成功率: {success_rate:.1%}")
        logger.info(f"总耗时: {total_duration:.1f} 秒")
        logger.info(f"平均耗时: {total_duration/total_tasks:.1f} 秒/任务")
        
        if video_paths:
            logger.info("✅ 成功生成的视频:")
            for video_path in video_paths:
                logger.info(f"  - {video_path}")
                
        if failed_tasks_info:
            logger.info("❌ 失败的任务:")
            for failed_info in failed_tasks_info:
                logger.info(f"  - {failed_info['task_id']}: {failed_info['error']}")
                
        logger.info("=" * 60)
        
        if progress_callback:
            progress_callback(1.0, f"批量处理完成! 成功: {completed_tasks}/{total_tasks}")
            
        return batch_result
        
    async def _process_single_task(self, task: BatchVideoTask, 
                                 progress_callback: Optional[Callable] = None) -> Optional[VideoGenerationResult]:
        """处理单个任务"""
        
        task.status = "processing"
        task.start_time = time.time()
        self.processing_tasks[task.task_id] = task
        
        logger.info(f"🎬 开始处理任务: {task.task_id}")
        
        # 创建引擎配置
        engine_config = {
            'output_dir': self.output_dir,
            'headless': self.headless,
            'max_wait_time': 300,  # 5分钟超时
            'max_concurrent': 1
        }
        
        # 重试机制
        for attempt in range(self.retry_count + 1):
            try:
                # 创建引擎实例
                engine = VheerVideoEngine(engine_config)
                
                # 初始化引擎
                if not await engine.initialize():
                    raise Exception("引擎初始化失败")
                    
                # 创建生成配置
                config = VideoGenerationConfig(
                    input_prompt=task.prompt,
                    input_image_path=task.image_path,
                    duration=task.duration,
                    width=task.width,
                    height=task.height,
                    output_dir=self.output_dir
                )
                
                # 生成视频
                result = await engine.generate_video(
                    config=config,
                    progress_callback=lambda msg: logger.info(f"[{task.task_id}] {msg}")
                )
                
                if result.success:
                    task.status = "completed"
                    task.result = result
                    task.end_time = time.time()
                    
                    # 移动到完成队列
                    self.completed_tasks[task.task_id] = task
                    if task.task_id in self.processing_tasks:
                        del self.processing_tasks[task.task_id]
                        
                    logger.info(f"✅ 任务完成: {task.task_id} - {result.video_path}")
                    return result
                else:
                    if attempt < self.retry_count:
                        logger.warning(f"⚠️ 任务失败，准备重试 ({attempt + 1}/{self.retry_count}): {task.task_id}")
                        await asyncio.sleep(self.retry_delay)
                        continue
                    else:
                        raise Exception(result.error_message)
                        
            except Exception as e:
                if attempt < self.retry_count:
                    logger.warning(f"⚠️ 任务异常，准备重试 ({attempt + 1}/{self.retry_count}): {task.task_id} - {e}")
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    # 所有重试都失败了
                    task.status = "failed"
                    task.error_message = str(e)
                    task.end_time = time.time()
                    
                    if task.task_id in self.processing_tasks:
                        del self.processing_tasks[task.task_id]
                        
                    logger.error(f"❌ 任务最终失败: {task.task_id} - {e}")
                    return VideoGenerationResult(
                        success=False,
                        error_message=str(e)
                    )
                    
        return None
        
    def get_status(self) -> Dict:
        """获取服务状态"""
        return {
            'queue_size': len(self.task_queue),
            'processing_count': len(self.processing_tasks),
            'completed_count': len(self.completed_tasks),
            'total_processed': self.total_processed,
            'total_success': self.total_success,
            'total_failed': self.total_failed,
            'success_rate': self.total_success / self.total_processed if self.total_processed > 0 else 0.0
        }
        
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        cleared_count = len(self.completed_tasks)
        self.completed_tasks.clear()
        logger.info(f"🧹 清理了 {cleared_count} 个已完成的任务")


# 便捷函数
async def batch_generate_videos_from_images(image_paths: List[str],
                                          prompts: List[str] = None,
                                          base_prompt: str = "",
                                          duration: float = 5.0,
                                          width: int = 1024,
                                          height: int = 1024,
                                          max_concurrent: int = 1,
                                          output_dir: str = "output/videos/vheer_batch",
                                          progress_callback: Optional[Callable] = None) -> BatchVideoResult:
    """批量从图像生成视频的便捷函数"""
    
    config = {
        'output_dir': output_dir,
        'max_concurrent': max_concurrent,
        'headless': True,
        'retry_count': 2,
        'retry_delay': 30
    }
    
    service = VheerBatchVideoService(config)
    
    # 添加任务
    await service.add_batch_tasks(
        image_paths=image_paths,
        prompts=prompts,
        base_prompt=base_prompt,
        duration=duration,
        width=width,
        height=height
    )
    
    # 处理任务
    return await service.process_batch(progress_callback)
