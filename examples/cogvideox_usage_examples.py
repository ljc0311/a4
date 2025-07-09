#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CogVideoX-Flash 使用示例
展示如何使用智谱AI视频生成引擎
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.video_engines.video_generation_service import VideoGenerationService, generate_video_simple
from src.models.video_engines.video_engine_base import VideoGenerationConfig
from config.video_generation_config import get_config
from src.utils.logger import logger


async def example_1_simple_text_to_video():
    """示例1: 简单的文生视频"""
    print("📝 示例1: 简单的文生视频")
    print("-" * 40)
    
    # 最简单的使用方式
    result = await generate_video_simple(
        prompt="一只可爱的小猫在阳光下打盹",
        duration=5.0,
        api_key="your-zhipu-api-key"  # 替换为您的API密钥
    )
    
    if result.success:
        print(f"✅ 视频生成成功: {result.video_path}")
        print(f"   生成时间: {result.generation_time:.1f}秒")
        print(f"   视频时长: {result.duration:.1f}秒")
    else:
        print(f"❌ 生成失败: {result.error_message}")


async def example_2_image_to_video():
    """示例2: 图生视频"""
    print("\n🖼️ 示例2: 图生视频")
    print("-" * 40)
    
    # 从图像生成视频
    image_path = "path/to/your/image.jpg"  # 替换为您的图像路径
    
    if os.path.exists(image_path):
        result = await generate_video_simple(
            prompt="图像中的场景开始动起来，微风轻拂",
            image_path=image_path,
            duration=6.0,
            api_key="your-zhipu-api-key"
        )
        
        if result.success:
            print(f"✅ 图生视频成功: {result.video_path}")
        else:
            print(f"❌ 生成失败: {result.error_message}")
    else:
        print(f"⚠️ 图像文件不存在: {image_path}")


async def example_3_advanced_configuration():
    """示例3: 高级配置"""
    print("\n⚙️ 示例3: 高级配置")
    print("-" * 40)
    
    # 创建详细配置
    config = VideoGenerationConfig(
        input_prompt="一个美丽的日落场景，海浪轻拍海岸",
        duration=8.0,
        fps=30,
        width=1920,
        height=1080,
        motion_intensity=0.7,
        seed=12345,
        output_format="mp4"
    )
    
    # 创建服务
    video_config = get_config('production')  # 使用生产环境配置
    service = VideoGenerationService(video_config)
    
    try:
        result = await service.generate_video_from_config(
            config=config,
            progress_callback=lambda msg: print(f"  进度: {msg}")
        )
        
        if result.success:
            print(f"✅ 高级配置生成成功: {result.video_path}")
            print(f"   分辨率: {result.resolution}")
            print(f"   帧率: {result.fps}")
            print(f"   文件大小: {result.file_size / 1024 / 1024:.2f}MB")
        else:
            print(f"❌ 生成失败: {result.error_message}")
    
    finally:
        await service.shutdown()


async def example_4_batch_generation():
    """示例4: 批量生成"""
    print("\n📦 示例4: 批量生成")
    print("-" * 40)
    
    # 创建多个配置
    configs = []
    
    prompts = [
        "春天的樱花飘落",
        "夏日的海浪拍岸", 
        "秋天的落叶飞舞",
        "冬日的雪花纷飞"
    ]
    
    for i, prompt in enumerate(prompts):
        config = VideoGenerationConfig(
            input_prompt=prompt,
            duration=4.0,
            fps=24,
            width=1024,
            height=1024,
            seed=1000 + i  # 不同的随机种子
        )
        configs.append(config)
    
    # 批量生成
    video_config = get_config('development')
    service = VideoGenerationService(video_config)
    
    try:
        results = await service.batch_generate_videos(
            configs=configs,
            progress_callback=lambda msg: print(f"  {msg}")
        )
        
        success_count = sum(1 for r in results if r.success)
        print(f"✅ 批量生成完成: {success_count}/{len(results)} 成功")
        
        for i, result in enumerate(results):
            if result.success:
                print(f"  视频{i+1}: {result.video_path}")
            else:
                print(f"  视频{i+1}: 失败 - {result.error_message}")
    
    finally:
        await service.shutdown()


async def example_5_engine_management():
    """示例5: 引擎管理"""
    print("\n🔧 示例5: 引擎管理")
    print("-" * 40)
    
    video_config = get_config('development')
    service = VideoGenerationService(video_config)
    
    try:
        # 获取可用引擎
        engines = service.get_available_engines()
        print(f"可用引擎: {engines}")
        
        # 测试引擎连接
        for engine in engines:
            result = await service.test_engine(engine)
            status = "✅ 可用" if result else "❌ 不可用"
            print(f"  {engine}: {status}")
        
        # 获取引擎信息
        if 'cogvideox_flash' in engines:
            info = service.get_engine_info('cogvideox_flash')
            print(f"\nCogVideoX-Flash 详细信息:")
            print(f"  免费: {info['is_free']}")
            print(f"  最大时长: {info['max_duration']}秒")
            print(f"  支持分辨率: {len(info['supported_resolutions'])}种")
        
        # 设置路由策略
        service.set_routing_strategy('free_first')
        print(f"\n路由策略已设置为: free_first")
        
        # 设置引擎偏好
        service.set_engine_preferences(['free', 'quality'])
        print(f"引擎偏好已设置为: ['free', 'quality']")
        
        # 获取统计信息
        stats = service.get_service_statistics()
        print(f"\n服务统计:")
        print(f"  活跃任务: {stats.get('active_tasks', 0)}")
        print(f"  路由策略: {stats.get('routing_strategy', 'unknown')}")
    
    finally:
        await service.shutdown()


async def example_6_error_handling():
    """示例6: 错误处理"""
    print("\n🚨 示例6: 错误处理")
    print("-" * 40)
    
    try:
        # 故意使用错误的配置来演示错误处理
        result = await generate_video_simple(
            prompt="测试错误处理",
            duration=5.0,
            api_key=""  # 空的API密钥
        )
        
        if not result.success:
            print(f"预期的错误: {result.error_message}")
            
            # 根据错误类型进行处理
            if "API密钥" in result.error_message:
                print("💡 解决方案: 请配置正确的智谱AI API密钥")
            elif "网络" in result.error_message:
                print("💡 解决方案: 请检查网络连接")
            elif "超时" in result.error_message:
                print("💡 解决方案: 请稍后重试或增加超时时间")
            else:
                print("💡 解决方案: 请查看详细错误信息并联系技术支持")
    
    except Exception as e:
        print(f"异常处理: {e}")
        print("💡 建议: 检查配置文件和依赖项")


async def example_7_integration_with_processor():
    """示例7: 与视频处理器集成"""
    print("\n🔗 示例7: 与视频处理器集成")
    print("-" * 40)
    
    try:
        from src.processors.video_processor import VideoProcessor
        from src.core.service_manager import ServiceManager
        
        # 创建服务管理器和视频处理器
        service_manager = ServiceManager()
        processor = VideoProcessor(service_manager)
        
        # 检查视频生成引擎是否可用
        engines = processor.get_available_video_engines()
        print(f"处理器中可用的视频引擎: {engines}")
        
        if engines:
            # 测试引擎
            for engine in engines[:1]:  # 只测试第一个
                result = await processor.test_video_engine(engine)
                print(f"  {engine}: {'✅ 可用' if result else '❌ 不可用'}")
            
            # 如果有测试图像，可以生成视频
            test_image = "path/to/test/image.jpg"
            if os.path.exists(test_image):
                video_path = await processor.generate_video_from_image(
                    image_path=test_image,
                    prompt="测试图像动画化",
                    duration=3.0,
                    progress_callback=lambda p, msg: print(f"  进度: {msg}")
                )
                print(f"✅ 集成测试成功: {video_path}")
            else:
                print("⚠️ 需要测试图像来完成集成测试")
        
        # 关闭引擎
        await processor.shutdown_video_engines()
        
    except ImportError as e:
        print(f"⚠️ 导入失败: {e}")
        print("请确保所有依赖项已正确安装")


async def main():
    """运行所有示例"""
    print("🎬 CogVideoX-Flash 使用示例")
    print("=" * 50)
    
    examples = [
        example_1_simple_text_to_video,
        example_2_image_to_video,
        example_3_advanced_configuration,
        example_4_batch_generation,
        example_5_engine_management,
        example_6_error_handling,
        example_7_integration_with_processor,
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"❌ 示例执行失败: {e}")
        
        print()  # 空行分隔
    
    print("🎉 所有示例执行完成！")
    print("\n💡 使用提示:")
    print("1. 请替换示例中的 'your-zhipu-api-key' 为您的实际API密钥")
    print("2. 请替换示例中的图像路径为实际存在的文件")
    print("3. 根据需要调整视频参数（时长、分辨率等）")
    print("4. 生产环境中建议使用配置文件管理API密钥")


if __name__ == "__main__":
    asyncio.run(main())
