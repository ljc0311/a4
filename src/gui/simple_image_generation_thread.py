#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的图像生成线程
避免复杂的异步处理，使用同步方式调用图像生成服务
"""

import asyncio
from PyQt5.QtCore import QThread, pyqtSignal
from src.utils.logger import logger


class SimpleImageGenerationThread(QThread):
    """简化的图像生成线程"""
    
    # 信号定义
    image_generated = pyqtSignal(str)  # 图像生成成功信号，传递图像路径
    generation_failed = pyqtSignal(str)  # 图像生成失败信号，传递错误信息
    progress_updated = pyqtSignal(str)  # 进度更新信号，传递状态信息
    
    def __init__(self, image_service, prompt, config, parent=None):
        super().__init__(parent)
        self.image_service = image_service
        self.prompt = prompt
        self.config = config
        self._is_cancelled = False
        
    def cancel(self):
        """取消图像生成"""
        self._is_cancelled = True
        
    def run(self):
        """线程主执行方法"""
        try:
            if self._is_cancelled:
                self.generation_failed.emit("图像生成已取消")
                return
                
            self.progress_updated.emit("正在生成图像...")
            logger.info(f"开始生成图像: {self.prompt[:50]}...")
            
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 调用图像生成服务
                result = loop.run_until_complete(
                    self.image_service.generate_image(
                        prompt=self.prompt,
                        negative_prompt=self.config.get('negative_prompt', ''),
                        width=self.config.get('width', 1024),
                        height=self.config.get('height', 1024),
                        provider=self.config.get('provider', 'pollinations')
                    )
                )
                
                if self._is_cancelled:
                    self.generation_failed.emit("图像生成已取消")
                    return
                
                # 处理结果
                if result.success and result.data:
                    image_path = result.data.get('image_path', '')
                    if image_path:
                        logger.info(f"图像生成成功: {image_path}")
                        self.progress_updated.emit("图像生成完成")
                        self.image_generated.emit(image_path)
                    else:
                        error_msg = "图像生成失败: 未返回图像路径"
                        logger.error(error_msg)
                        self.generation_failed.emit(error_msg)
                else:
                    error_msg = f"图像生成失败: {result.error}"
                    logger.error(error_msg)
                    self.generation_failed.emit(error_msg)
                    
            finally:
                # 关闭事件循环
                try:
                    loop.close()
                except Exception as e:
                    logger.warning(f"关闭事件循环时出现警告: {e}")
                    
        except Exception as e:
            error_msg = f"图像生成异常: {e}"
            logger.error(error_msg)
            self.generation_failed.emit(error_msg)