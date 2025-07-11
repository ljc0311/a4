#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像生成服务调试脚本
用于调试图像生成服务的初始化过程
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.image_generation_service import ImageGenerationService
from src.utils.config_manager import ConfigManager
from src.utils.logger import logger


async def debug_config_loading():
    """调试配置加载"""
    print("🔧 调试配置加载...")
    
    try:
        config_manager = ConfigManager()
        image_config = config_manager.get_image_config()
        
        print(f"📋 图像配置: {image_config}")
        
        # 检查CogView-3 Flash配置
        image_gen_config = image_config.get('image_generation', {})
        cogview_config = image_gen_config.get('cogview_3_flash', {})
        
        print(f"🎯 CogView-3 Flash配置: {cogview_config}")
        print(f"✅ CogView-3 Flash启用状态: {cogview_config.get('enabled', False)}")
        
        return image_config
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return None


async def debug_service_initialization():
    """调试服务初始化"""
    print("\n🚀 调试服务初始化...")
    
    try:
        # 获取配置
        config_manager = ConfigManager()
        image_config = config_manager.get_image_config()
        
        # 创建服务
        service = ImageGenerationService(image_config)
        
        print("📋 服务创建成功")
        
        # 初始化服务
        success = await service.initialize()
        
        if success:
            print("✅ 服务初始化成功")
            
            # 检查引擎管理器状态
            manager_status = service.engine_manager.get_manager_status()
            print(f"📊 引擎管理器状态: {manager_status}")
            
            # 检查可用引擎
            available_engines = service.engine_manager._get_available_engines()
            print(f"🔧 可用引擎: {[engine.value for engine in available_engines]}")
            
            # 检查CogView-3 Flash引擎
            cogview_engine = service.engine_manager.factory.get_engine(
                service.engine_manager.factory._engine_classes.get(
                    service.engine_manager.factory.EngineType.COGVIEW_3_FLASH
                )
            )
            
            if cogview_engine:
                print(f"✅ CogView-3 Flash引擎已创建，状态: {cogview_engine.status}")
            else:
                print("❌ CogView-3 Flash引擎未创建")
            
            return service
        else:
            print("❌ 服务初始化失败")
            return None
            
    except Exception as e:
        print(f"❌ 服务初始化异常: {e}")
        import traceback
        traceback.print_exc()
        return None


async def debug_engine_creation():
    """调试引擎创建过程"""
    print("\n🔧 调试引擎创建过程...")
    
    try:
        from src.models.image_engine_factory import EngineFactory
        from src.models.image_engine_base import EngineType
        
        factory = EngineFactory()
        
        # 检查引擎类注册
        print(f"📋 已注册的引擎类: {list(factory._engine_classes.keys())}")
        
        # 尝试创建CogView-3 Flash引擎
        cogview_config = {
            'enabled': True,
            'api_key': '',  # 让引擎自动获取
            'timeout': 120
        }
        
        print(f"🎯 尝试创建CogView-3 Flash引擎，配置: {cogview_config}")
        
        engine = await factory.create_engine(EngineType.COGVIEW_3_FLASH, cogview_config)
        
        if engine:
            print(f"✅ CogView-3 Flash引擎创建成功，状态: {engine.status}")
            print(f"🔑 API密钥: {engine.api_key[:10] if engine.api_key else 'None'}...")
            return engine
        else:
            print("❌ CogView-3 Flash引擎创建失败")
            return None
            
    except Exception as e:
        print(f"❌ 引擎创建异常: {e}")
        import traceback
        traceback.print_exc()
        return None


async def debug_image_generation(service):
    """调试图像生成"""
    print("\n🎨 调试图像生成...")
    
    if not service:
        print("❌ 服务未初始化，跳过测试")
        return False
    
    try:
        # 测试配置
        config = {
            'prompt': '一个简单的测试图像',
            'width': 768,
            'height': 768,
            'batch_size': 1
        }
        
        print(f"📝 测试配置: {config}")
        
        # 尝试生成图像
        result = await service.generate_image(
            prompt=config['prompt'],
            config=config,
            engine_preference='cogview_3_flash'
        )
        
        if result.success:
            print("✅ 图像生成成功!")
            print(f"📁 图像路径: {result.image_paths}")
            return True
        else:
            print("❌ 图像生成失败")
            print(f"🔍 错误信息: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ 图像生成异常: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主调试函数"""
    print("🐛 图像生成服务调试")
    print("=" * 50)
    
    # 步骤1: 调试配置加载
    config = await debug_config_loading()
    
    # 步骤2: 调试引擎创建
    engine = await debug_engine_creation()
    
    # 步骤3: 调试服务初始化
    service = await debug_service_initialization()
    
    # 步骤4: 调试图像生成
    if service:
        generation_success = await debug_image_generation(service)
        await service.cleanup()
    else:
        generation_success = False
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 调试结果总结:")
    print("=" * 50)
    print(f"配置加载:        {'✅' if config else '❌'}")
    print(f"引擎创建:        {'✅' if engine else '❌'}")
    print(f"服务初始化:      {'✅' if service else '❌'}")
    print(f"图像生成:        {'✅' if generation_success else '❌'}")
    
    if engine:
        await engine.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
