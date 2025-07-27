#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能基准测试
对比优化前后的性能差异
"""

import asyncio
import time
import sys
import os
import statistics
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.memory_optimizer import memory_manager, image_memory_manager
from src.utils.async_task_manager import task_manager, create_task
from src.utils.logger import logger

class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self):
        self.results = {}
    
    async def benchmark_memory_management(self, iterations: int = 5) -> Dict[str, Any]:
        """基准测试内存管理"""
        print(f"🧠 内存管理基准测试 ({iterations} 次迭代)...")
        
        memory_usage = []
        cleanup_times = []
        
        for i in range(iterations):
            # 创建测试对象
            class TestObject:
                def __init__(self, size):
                    self.data = bytearray(size)
            
            objects = []
            start_memory = memory_manager.get_memory_stats().rss_mb
            
            # 创建大量对象
            for j in range(200):
                obj = TestObject(1024 * 100)  # 100KB
                objects.append(obj)
                memory_manager.register_object("benchmark", obj)
            
            peak_memory = memory_manager.get_memory_stats().rss_mb
            memory_usage.append(peak_memory - start_memory)
            
            # 测试清理时间
            start_time = time.time()
            memory_manager.force_cleanup()
            objects.clear()
            cleanup_time = time.time() - start_time
            cleanup_times.append(cleanup_time)
            
            await asyncio.sleep(0.1)  # 短暂休息
        
        return {
            'avg_memory_usage_mb': statistics.mean(memory_usage),
            'max_memory_usage_mb': max(memory_usage),
            'avg_cleanup_time_s': statistics.mean(cleanup_times),
            'max_cleanup_time_s': max(cleanup_times)
        }
    
    async def benchmark_image_cache(self, iterations: int = 3) -> Dict[str, Any]:
        """基准测试图像缓存"""
        print(f"🖼️ 图像缓存基准测试 ({iterations} 次迭代)...")
        
        cache_times = []
        retrieval_times = []
        
        for i in range(iterations):
            # 测试缓存性能
            start_time = time.time()
            
            for j in range(50):
                image_data = b"test_image_data" * 1000 * (j + 1)
                key = f"benchmark_image_{i}_{j}"
                image_memory_manager.add_image_to_cache(key, image_data)
            
            cache_time = time.time() - start_time
            cache_times.append(cache_time)
            
            # 测试检索性能
            start_time = time.time()
            
            for j in range(50):
                key = f"benchmark_image_{i}_{j}"
                image_memory_manager.get_image_from_cache(key)
            
            retrieval_time = time.time() - start_time
            retrieval_times.append(retrieval_time)
            
            # 清理缓存
            image_memory_manager.clear_image_cache()
        
        avg_cache_time = statistics.mean(cache_times)
        avg_retrieval_time = statistics.mean(retrieval_times)
        
        return {
            'avg_cache_time_s': avg_cache_time,
            'avg_retrieval_time_s': avg_retrieval_time,
            'cache_throughput_items_per_s': 50 / avg_cache_time if avg_cache_time > 0 else 0,
            'retrieval_throughput_items_per_s': 50 / avg_retrieval_time if avg_retrieval_time > 0 else 0
        }
    
    async def benchmark_async_tasks(self, iterations: int = 3) -> Dict[str, Any]:
        """基准测试异步任务管理"""
        print(f"⚡ 异步任务管理基准测试 ({iterations} 次迭代)...")
        
        async def test_task(duration: float):
            await asyncio.sleep(duration)
            return f"Task completed in {duration}s"
        
        creation_times = []
        execution_times = []
        
        for i in range(iterations):
            # 测试任务创建性能
            start_time = time.time()
            
            task_ids = []
            for j in range(20):
                task_id = create_task(
                    test_task(0.1), 
                    name=f"BenchmarkTask_{i}_{j}"
                )
                task_ids.append(task_id)
            
            creation_time = time.time() - start_time
            creation_times.append(creation_time)
            
            # 测试任务执行性能
            start_time = time.time()
            
            for task_id in task_ids:
                await task_manager.wait_for_task(task_id)
            
            execution_time = time.time() - start_time
            execution_times.append(execution_time)
        
        avg_creation_time = statistics.mean(creation_times)
        avg_execution_time = statistics.mean(execution_times)
        
        return {
            'avg_creation_time_s': avg_creation_time,
            'avg_execution_time_s': avg_execution_time,
            'task_creation_rate_per_s': 20 / avg_creation_time if avg_creation_time > 0 else 0,
            'task_completion_rate_per_s': 20 / avg_execution_time if avg_execution_time > 0 else 0
        }
    
    async def benchmark_concurrent_processing(self) -> Dict[str, Any]:
        """基准测试并发处理"""
        print("🚀 并发处理基准测试...")
        
        async def cpu_task(n: int):
            """CPU密集型任务"""
            result = 0
            for i in range(n * 5000):
                result += i * i
            return result
        
        # 测试不同并发级别
        concurrency_levels = [1, 2, 5, 10]
        results = {}
        
        for concurrency in concurrency_levels:
            times = []
            
            for _ in range(3):  # 每个并发级别测试3次
                start_time = time.time()
                
                task_ids = []
                for i in range(concurrency):
                    task_id = create_task(
                        cpu_task(100), 
                        name=f"ConcurrentTask_{concurrency}_{i}"
                    )
                    task_ids.append(task_id)
                
                # 等待所有任务完成
                for task_id in task_ids:
                    await task_manager.wait_for_task(task_id)
                
                execution_time = time.time() - start_time
                times.append(execution_time)
            
            results[f'concurrency_{concurrency}'] = {
                'avg_time_s': statistics.mean(times),
                'min_time_s': min(times),
                'max_time_s': max(times)
            }
        
        return results
    
    async def run_full_benchmark(self) -> Dict[str, Any]:
        """运行完整基准测试"""
        print("🎯 开始完整性能基准测试\n")
        
        # 获取初始系统状态
        initial_stats = memory_manager.get_memory_stats()
        start_time = time.time()
        
        # 运行各项基准测试
        self.results['memory_management'] = await self.benchmark_memory_management()
        self.results['image_cache'] = await self.benchmark_image_cache()
        self.results['async_tasks'] = await self.benchmark_async_tasks()
        self.results['concurrent_processing'] = await self.benchmark_concurrent_processing()
        
        # 计算总体统计
        total_time = time.time() - start_time
        final_stats = memory_manager.get_memory_stats()
        
        self.results['overall'] = {
            'total_benchmark_time_s': total_time,
            'initial_memory_mb': initial_stats.rss_mb,
            'final_memory_mb': final_stats.rss_mb,
            'memory_delta_mb': final_stats.rss_mb - initial_stats.rss_mb,
            'task_stats': task_manager.get_task_stats()
        }
        
        return self.results
    
    def print_results(self):
        """打印基准测试结果"""
        print("\n" + "="*60)
        print("📊 性能基准测试结果")
        print("="*60)
        
        # 内存管理结果
        mem_results = self.results['memory_management']
        print(f"\n🧠 内存管理性能:")
        print(f"  平均内存使用: {mem_results['avg_memory_usage_mb']:.1f}MB")
        print(f"  峰值内存使用: {mem_results['max_memory_usage_mb']:.1f}MB")
        print(f"  平均清理时间: {mem_results['avg_cleanup_time_s']:.3f}s")
        print(f"  最大清理时间: {mem_results['max_cleanup_time_s']:.3f}s")
        
        # 图像缓存结果
        cache_results = self.results['image_cache']
        print(f"\n🖼️ 图像缓存性能:")
        print(f"  平均缓存时间: {cache_results['avg_cache_time_s']:.3f}s")
        print(f"  平均检索时间: {cache_results['avg_retrieval_time_s']:.3f}s")
        print(f"  缓存吞吐量: {cache_results['cache_throughput_items_per_s']:.1f} 项/秒")
        print(f"  检索吞吐量: {cache_results['retrieval_throughput_items_per_s']:.1f} 项/秒")
        
        # 异步任务结果
        task_results = self.results['async_tasks']
        print(f"\n⚡ 异步任务性能:")
        print(f"  平均创建时间: {task_results['avg_creation_time_s']:.3f}s")
        print(f"  平均执行时间: {task_results['avg_execution_time_s']:.3f}s")
        print(f"  任务创建速率: {task_results['task_creation_rate_per_s']:.1f} 任务/秒")
        print(f"  任务完成速率: {task_results['task_completion_rate_per_s']:.1f} 任务/秒")
        
        # 并发处理结果
        concurrent_results = self.results['concurrent_processing']
        print(f"\n🚀 并发处理性能:")
        for level, data in concurrent_results.items():
            concurrency = level.split('_')[1]
            print(f"  并发级别 {concurrency}: 平均 {data['avg_time_s']:.3f}s, "
                  f"最小 {data['min_time_s']:.3f}s, 最大 {data['max_time_s']:.3f}s")
        
        # 总体结果
        overall = self.results['overall']
        print(f"\n📈 总体统计:")
        print(f"  基准测试总时间: {overall['total_benchmark_time_s']:.2f}s")
        print(f"  初始内存: {overall['initial_memory_mb']:.1f}MB")
        print(f"  最终内存: {overall['final_memory_mb']:.1f}MB")
        print(f"  内存变化: {overall['memory_delta_mb']:+.1f}MB")
        print(f"  任务成功率: {overall['task_stats']['success_rate']:.1%}")
        
        print("\n" + "="*60)

async def main():
    """主函数"""
    benchmark = PerformanceBenchmark()
    
    try:
        await benchmark.run_full_benchmark()
        benchmark.print_results()
        
        print("\n🎉 基准测试完成！")
        
    except Exception as e:
        print(f"❌ 基准测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        task_manager.shutdown()
        memory_manager.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())