#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化功能使用示例
展示如何在实际代码中使用内存管理和异步处理优化
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.memory_optimizer import memory_manager, image_memory_manager, monitor_memory
from src.utils.async_task_manager import task_manager, create_task
from src.utils.logger import logger

class OptimizedImageProcessor:
    """优化的图像处理器示例"""
    
    def __init__(self):
        # 注册清理回调
        memory_manager.register_cleanup_callback(self.cleanup_resources)
    
    @monitor_memory("图像处理")
    async def process_images(self, image_paths: list, progress_callback=None):
        """处理图像列表 - 使用内存监控装饰器"""
        results = []
        
        # 使用内存上下文管理器
        with memory_manager.memory_context("批量图像处理"):
            for i, path in enumerate(image_paths):
                if progress_callback:
                    progress_callback(i / len(image_paths), f"处理图像 {i+1}/{len(image_paths)}")
                
                # 模拟图像处理
                processed_image = await self.process_single_image(path)
                results.append(processed_image)
                
                # 检查内存压力
                if memory_manager.check_memory_pressure():
                    logger.warning("内存压力过大，执行清理")
                    memory_manager.force_cleanup()
        
        return results
    
    async def process_single_image(self, image_path: str):
        """处理单张图像"""
        # 检查缓存
        cache_key = f"processed_{hash(image_path)}"
        cached_result = image_memory_manager.get_image_from_cache(cache_key)
        
        if cached_result:
            logger.info(f"使用缓存结果: {image_path}")
            return cached_result
        
        # 模拟图像处理
        await asyncio.sleep(0.1)  # 模拟处理时间
        processed_data = f"processed_{image_path}".encode()
        
        # 缓存结果
        image_memory_manager.add_image_to_cache(cache_key, processed_data)
        
        return processed_data
    
    def cleanup_resources(self):
        """清理资源回调"""
        logger.info("清理图像处理器资源")
        # 清理临时文件、关闭连接等

class OptimizedVideoGenerator:
    """优化的视频生成器示例"""
    
    async def generate_video_from_text(self, text: str, progress_callback=None):
        """从文本生成视频 - 使用异步任务管理"""
        
        # 步骤1: 生成分镜
        storyboard_task = create_task(
            self.generate_storyboard(text),
            name="生成分镜",
            callback=self.on_task_complete
        )
        
        # 步骤2: 生成图像（依赖分镜）
        storyboard = await task_manager.wait_for_task(storyboard_task)
        
        if not storyboard:
            raise ValueError("分镜生成失败")
        
        image_tasks = []
        for i, shot in enumerate(storyboard):
            task_id = create_task(
                self.generate_image(shot),
                name=f"生成图像_{i}",
                metadata={'shot_index': i}
            )
            image_tasks.append(task_id)
        
        # 等待所有图像生成完成
        images = []
        for i, task_id in enumerate(image_tasks):
            if progress_callback:
                progress_callback(i / len(image_tasks), f"生成图像 {i+1}/{len(image_tasks)}")
            
            image = await task_manager.wait_for_task(task_id)
            images.append(image)
        
        # 步骤3: 合成视频
        video_task = create_task(
            self.compose_video(images),
            name="合成视频"
        )
        
        final_video = await task_manager.wait_for_task(video_task)
        
        if progress_callback:
            progress_callback(1.0, "视频生成完成")
        
        return final_video
    
    async def generate_storyboard(self, text: str):
        """生成分镜"""
        logger.info("开始生成分镜")
        await asyncio.sleep(0.5)  # 模拟处理时间
        
        # 模拟分镜数据
        shots = [f"镜头_{i}: {text[:20]}..." for i in range(5)]
        logger.info(f"分镜生成完成，共 {len(shots)} 个镜头")
        return shots
    
    async def generate_image(self, shot: str):
        """生成单张图像"""
        logger.info(f"生成图像: {shot}")
        await asyncio.sleep(0.3)  # 模拟处理时间
        
        # 模拟图像数据
        image_data = f"image_data_for_{shot}".encode()
        return image_data
    
    async def compose_video(self, images: list):
        """合成视频"""
        logger.info(f"开始合成视频，共 {len(images)} 张图像")
        await asyncio.sleep(1.0)  # 模拟处理时间
        
        video_data = f"video_composed_from_{len(images)}_images".encode()
        logger.info("视频合成完成")
        return video_data
    
    def on_task_complete(self, task_id: str, result, error):
        """任务完成回调"""
        if error:
            logger.error(f"任务 {task_id} 失败: {error}")
        else:
            logger.info(f"任务 {task_id} 完成")

async def example_usage():
    """使用示例"""
    print("🎬 优化功能使用示例\n")
    
    # 示例1: 优化的图像处理
    print("📸 示例1: 批量图像处理")
    processor = OptimizedImageProcessor()
    
    image_paths = [f"image_{i}.jpg" for i in range(10)]
    
    def progress_callback(progress, message):
        print(f"进度: {progress:.1%} - {message}")
    
    results = await processor.process_images(image_paths, progress_callback)
    print(f"处理完成，共 {len(results)} 张图像\n")
    
    # 示例2: 优化的视频生成
    print("🎥 示例2: 视频生成")
    generator = OptimizedVideoGenerator()
    
    text = "这是一个关于AI视频生成的故事，展示了如何使用优化的异步处理来提升性能。"
    
    video = await generator.generate_video_from_text(text, progress_callback)
    print(f"视频生成完成: {len(video)} 字节\n")
    
    # 示例3: 内存状态监控
    print("💾 示例3: 内存状态监控")
    memory_summary = memory_manager.get_memory_summary()
    
    print("内存摘要:")
    print(f"  物理内存使用: {memory_summary['memory_stats']['rss_mb']:.1f}MB")
    print(f"  注册对象数量: {memory_summary['total_registered_objects']}")
    print(f"  图像缓存大小: {memory_summary['cache_info']['image_cache_size_mb']:.2f}MB")
    print(f"  内存压力状态: {'高' if memory_summary['memory_pressure'] else '正常'}")
    
    # 示例4: 任务统计
    print("\n⚡ 示例4: 任务统计")
    task_stats = task_manager.get_task_stats()
    
    print("任务统计:")
    print(f"  总任务数: {task_stats['total_tasks']}")
    print(f"  运行中任务: {task_stats['running_tasks']}")
    print(f"  已完成任务: {task_stats['completed_tasks']}")
    print(f"  成功率: {task_stats['success_rate']:.1%}")

async def main():
    """主函数"""
    try:
        await example_usage()
        
        print("\n🎉 示例运行完成！")
        
        # 显示最终状态
        final_stats = memory_manager.get_memory_stats()
        print(f"最终内存使用: {final_stats.rss_mb:.1f}MB")
        
    except Exception as e:
        print(f"❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        task_manager.shutdown()
        memory_manager.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())