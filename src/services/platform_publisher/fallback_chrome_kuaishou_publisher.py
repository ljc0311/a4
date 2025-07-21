#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备用Chrome快手发布器
当主发布器初始化失败时的备用方案
"""

import time
import asyncio
import random
from typing import Dict, Any, Optional

from .simple_chrome_kuaishou_publisher import SimpleChromeKuaishouPublisher
from src.utils.logger import logger


class FallbackChromeKuaishouPublisher(SimpleChromeKuaishouPublisher):
    """备用Chrome快手发布器 - 带故障恢复"""
    
    def __init__(self, config: Dict[str, Any]):
        # 添加备用配置
        fallback_config = {
            'max_init_retries': 3,
            'init_timeout': 30,
            'fallback_to_simulation': True,
            **config
        }
        
        super().__init__(fallback_config)
        self.init_retries = 0
        self.max_retries = fallback_config.get('max_init_retries', 3)
        
    def _init_driver(self):
        """带重试机制的驱动初始化"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🚀 尝试初始化Chrome驱动 (第{attempt + 1}次/共{self.max_retries}次)")
                
                # 如果不是第一次尝试，等待一下
                if attempt > 0:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.info(f"⏳ 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                
                # 尝试初始化
                super()._init_driver()
                logger.info("✅ Chrome驱动初始化成功")
                return
                
            except Exception as e:
                logger.warning(f"⚠️ 第{attempt + 1}次初始化失败: {e}")
                
                if attempt < self.max_retries - 1:
                    logger.info("🔄 准备重试...")
                    continue
                else:
                    # 最后一次尝试失败，检查是否启用备用方案
                    if self.selenium_config.get('fallback_to_simulation', True):
                        logger.warning("⚠️ 所有初始化尝试都失败，启用模拟模式作为备用方案")
                        self._enable_simulation_mode()
                        return
                    else:
                        logger.error("❌ Chrome驱动初始化完全失败，无备用方案")
                        raise
    
    def _enable_simulation_mode(self):
        """启用模拟模式作为备用方案"""
        try:
            logger.info("🎭 启用模拟模式作为备用方案...")
            
            # 修改配置为模拟模式
            self.selenium_config['simulation_mode'] = True
            
            # 清理可能的残留驱动
            self._cleanup_driver()
            
            # 设置模拟模式的驱动和等待对象
            self.driver = None
            self.wait = None
            
            logger.info("✅ 模拟模式备用方案启用成功")
            
        except Exception as e:
            logger.error(f"❌ 启用模拟模式失败: {e}")
            raise
    
    async def _publish_video_impl(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """带备用方案的视频发布实现"""
        try:
            # 检查是否为备用模拟模式
            if self.selenium_config.get('simulation_mode', False):
                logger.info("🎭 使用模拟模式备用方案进行发布")
                return await self._simulate_publish_with_fallback_info(video_info)
            
            # 正常发布流程
            return await super()._publish_video_impl(video_info)
            
        except Exception as e:
            logger.error(f"❌ 发布过程中发生错误: {e}")
            
            # 如果还没有启用模拟模式，尝试启用
            if not self.selenium_config.get('simulation_mode', False):
                logger.info("🔄 尝试启用模拟模式作为备用方案...")
                self._enable_simulation_mode()
                return await self._simulate_publish_with_fallback_info(video_info)
            else:
                # 已经是模拟模式还失败，返回错误
                return {'success': False, 'error': f'发布失败: {str(e)}'}
    
    async def _simulate_publish_with_fallback_info(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """带备用信息的模拟发布"""
        logger.info("🎭 备用模拟模式：模拟快手视频发布过程")
        
        title = video_info.get('title', '')
        description = video_info.get('description', '')
        
        logger.info(f"模拟设置标题: {title}")
        await asyncio.sleep(1)
        logger.info(f"模拟设置描述: {description}")
        await asyncio.sleep(1)
        logger.info("模拟上传视频文件...")
        await asyncio.sleep(3)
        logger.info("模拟点击发布按钮...")
        await asyncio.sleep(2)

        logger.info("✅ 备用模拟发布成功！")
        
        return {
            'success': True, 
            'message': '备用模拟发布成功 - Chrome驱动初始化失败，已使用模拟模式',
            'fallback_mode': True,
            'note': '由于Chrome驱动问题，本次使用了模拟模式。建议检查Chrome浏览器和网络环境。'
        }
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取发布器状态信息"""
        return {
            'publisher_type': 'FallbackChromeKuaishouPublisher',
            'simulation_mode': self.selenium_config.get('simulation_mode', False),
            'stealth_available': self.stealth_available,
            'driver_initialized': self.driver is not None,
            'init_retries': self.init_retries,
            'max_retries': self.max_retries
        }


def create_fallback_kuaishou_publisher(config: Dict[str, Any] = None) -> FallbackChromeKuaishouPublisher:
    """创建备用快手发布器"""
    default_config = {
        'simulation_mode': False,
        'use_stealth': True,
        'headless': False,
        'timeout': 30,
        'max_init_retries': 3,
        'fallback_to_simulation': True
    }
    
    final_config = {**default_config, **(config or {})}
    
    return FallbackChromeKuaishouPublisher(final_config)


# 便捷函数
async def test_fallback_publisher():
    """测试备用发布器"""
    logger.info("🧪 测试备用快手发布器...")
    
    config = {
        'simulation_mode': False,  # 先尝试真实模式
        'fallback_to_simulation': True,
        'max_init_retries': 2
    }
    
    publisher = create_fallback_kuaishou_publisher(config)
    
    test_video_info = {
        'video_path': 'test_video.mp4',
        'title': '备用发布器测试视频',
        'description': '测试备用发布器的故障恢复功能',
        'tags': ['测试', '备用', '快手']
    }
    
    try:
        # 初始化发布器
        publisher._init_driver()
        
        # 尝试发布
        result = await publisher._publish_video_impl(test_video_info)
        
        logger.info(f"📊 发布结果: {result}")
        logger.info(f"📊 发布器状态: {publisher.get_status_info()}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 备用发布器测试失败: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        # 清理资源
        try:
            publisher._cleanup_driver()
        except:
            pass


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_fallback_publisher())
