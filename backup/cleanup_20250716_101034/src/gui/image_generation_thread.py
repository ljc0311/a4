# -*- coding: utf-8 -*-
"""
图像生成线程 - 重写版本
- 简化异常处理，移除SystemExit相关代码
- 使用直接错误返回机制
- 减少复杂依赖
"""
from PyQt5.QtCore import QThread, pyqtSignal
from src.utils.logger import logger
from src.models.image_generation_service import ImageGenerationService
import traceback

class ImageGenerationThread(QThread):
    """图像生成线程类"""
    
    # 信号定义
    image_generated = pyqtSignal(str)  # 图像生成成功信号，传递图像路径
    generation_failed = pyqtSignal(str)  # 图像生成失败信号，传递错误信息
    progress_updated = pyqtSignal(str)  # 进度更新信号，传递状态信息
    error_occurred = pyqtSignal(str)  # 错误信号，传递错误信息
    
    def __init__(self, image_generation_service=None, config=None, engine_preference=None, prompt=None, workflow_id=None, parameters=None, project_manager=None, current_project_name=None, generation_params=None, parent=None):
        super().__init__(parent)
        
        # 新的多引擎架构参数
        self.image_generation_service = image_generation_service
        self.config = config
        self.engine_preference = engine_preference
        
        # 兼容旧的参数
        self.prompt = prompt or (config.prompt if config else None)
        self.workflow_id = workflow_id
        self.parameters = generation_params or parameters or {}
        self.project_manager = project_manager
        self.current_project_name = current_project_name
        self.image_service = None  # 保持向后兼容
        self._is_cancelled = False
        
        logger.info(f"图像生成线程初始化完成")
        logger.info(f"提示词: {self.prompt}")
        logger.info(f"工作流ID: {workflow_id}")
        logger.info(f"引擎偏好: {engine_preference}")
        logger.info(f"参数: {parameters}")
    
    def set_image_service(self, image_service: ImageGenerationService):
        """设置图像生成服务"""
        self.image_service = image_service
        logger.info("已设置图像生成服务")
    
    def cancel(self):
        """取消图像生成"""
        self._is_cancelled = True
        logger.info("图像生成已被取消")
    
    def run(self):
        """线程主执行方法"""
        logger.info("=== 图像生成线程开始执行 ===")
        
        try:
            # 检查是否已取消
            if self._is_cancelled:
                logger.info("图像生成已取消")
                self.generation_failed.emit("图像生成已取消")
                return
            
            # 发送进度更新
            self.progress_updated.emit("正在初始化图像生成服务...")
            
            # 检查图像生成服务（优先使用新架构）
            service = self.image_generation_service or self.image_service
            if not service:
                error_msg = "图像生成服务未初始化"
                logger.error(error_msg)
                self.generation_failed.emit(error_msg)
                return
            
            # 检查是否已取消
            if self._is_cancelled:
                logger.info("图像生成已取消")
                self.generation_failed.emit("图像生成已取消")
                return
            
            # 发送进度更新
            self.progress_updated.emit("正在生成图像...")
            
            # 调用图像生成服务
            logger.info("开始调用图像生成服务")
            
            # 使用新的多引擎架构
            if self.image_generation_service and hasattr(self.image_generation_service, 'generate_image'):
                logger.info(f"使用多引擎架构生成图像，引擎偏好: {self.engine_preference}")
                
                # 构建配置字典
                config_dict = {
                    'prompt': self.prompt,
                    'negative_prompt': '',
                    'width': 512,
                    'height': 512,
                    'steps': 20,
                    'cfg_scale': 7.5,
                    'seed': None,
                    'sampler': 'DPM++ 2M Karras',
                    'batch_size': getattr(self.config, 'batch_size', 1) if self.config else 1
                }
                
                # 从self.config获取配置
                if self.config:
                    if hasattr(self.config, '__dict__'):
                        # 是GenerationConfig对象，转换为字典
                        config_dict.update({
                            'width': getattr(self.config, 'width', 512),
                            'height': getattr(self.config, 'height', 512),
                            'steps': getattr(self.config, 'steps', 20),
                            'guidance_scale': getattr(self.config, 'cfg_scale', 7.5),
                            'seed': getattr(self.config, 'seed', None),
                            'negative_prompt': getattr(self.config, 'negative_prompt', ''),
                            'batch_size': getattr(self.config, 'batch_size', 1),
                            'model': getattr(self.config, 'model', None),
                            'style': getattr(self.config, 'style', None),
                            'api_key': getattr(self.config, 'api_key', None),
                            'base_url': getattr(self.config, 'base_url', None)
                        })
                    elif isinstance(self.config, dict):
                        # 已经是字典，直接更新
                        config_dict.update(self.config)
                    else:
                        # 其他类型，尝试转换为字典
                        logger.warning(f"未知的config类型: {type(self.config)}，尝试转换")
                        try:
                            if hasattr(self.config, 'items'):
                                config_dict.update(dict(self.config.items()))
                        except Exception as e:
                            logger.error(f"转换config失败: {e}")
                
                # 从self.parameters获取额外配置
                if self.parameters:
                    config_dict.update(self.parameters)
                
                # 添加workflow_id
                if self.workflow_id:
                    config_dict['workflow_id'] = self.workflow_id
                
                # 确保基本配置存在
                config_dict.setdefault('width', 512)
                config_dict.setdefault('height', 512)
                config_dict.setdefault('steps', 20)
                config_dict.setdefault('guidance_scale', 7.5)
                
                # 异步调用图像生成服务 - 使用更安全的方式
                import asyncio
                try:
                    # 尝试获取当前事件循环
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Event loop is closed")
                except RuntimeError:
                    # 如果没有当前循环或循环已关闭，创建新的
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                try:
                    result = loop.run_until_complete(self.image_generation_service.generate_image(
                        prompt=self.prompt,
                        config=config_dict,
                        engine_preference=self.engine_preference,
                        project_manager=self.project_manager,
                        current_project_name=self.current_project_name
                    ))
                finally:
                    # 确保循环状态正确
                    if loop.is_running():
                        pass  # 如果循环正在运行，不要关闭
                    else:
                        # 只有当循环不在运行时才关闭
                        try:
                            loop.close()
                        except:
                            pass
            else:
                # 兼容旧的接口
                logger.info("使用兼容模式生成图像")
                # 构建配置参数
                config_dict = self.parameters or {}
                if self.workflow_id:
                    config_dict['workflow_id'] = self.workflow_id
                
                # 异步调用图像生成服务 - 使用更安全的方式
                import asyncio
                import concurrent.futures

                # 在新线程中运行异步代码，避免事件循环冲突
                def run_async_generation():
                    """在新线程中运行异步图像生成"""
                    try:
                        # 创建新的事件循环
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        try:
                            # 确保参数类型正确
                            prompt = self.prompt if self.prompt else ""
                            config = config_dict if config_dict else {}

                            # 运行异步生成
                            return loop.run_until_complete(service.generate_image(
                                prompt=prompt,
                                config=config
                            ))
                        finally:
                            # 清理事件循环
                            loop.close()
                    except Exception as e:
                        logger.error(f"异步图像生成失败: {e}")
                        return None

                # 使用线程池执行异步任务
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_async_generation)
                    try:
                        result = future.result(timeout=300)  # 5分钟超时
                    except concurrent.futures.TimeoutError:
                        logger.error("图像生成超时")
                        result = None
                    except Exception as e:
                        logger.error(f"图像生成执行失败: {e}")
                        result = None
            
            # 检查是否已取消
            if self._is_cancelled:
                logger.info("图像生成已取消")
                self.generation_failed.emit("图像生成已取消")
                return
            
            # 处理结果
            if result and hasattr(result, 'success'):
                # 处理GenerationResult对象
                if result.success and result.image_paths:
                    # 生成成功
                    first_image_path = result.image_paths[0]
                    logger.info(f"图像生成成功: {first_image_path}")
                    self.progress_updated.emit("图像生成完成")
                    self.image_generated.emit(first_image_path)
                else:
                    # 生成失败
                    error_msg = result.error_message or "图像生成失败：未知错误"
                    logger.error(f"图像生成失败: {error_msg}")
                    self.generation_failed.emit(error_msg)
            elif result and isinstance(result, list) and len(result) > 0:
                # 兼容旧的列表格式
                first_result = result[0]
                
                # 检查是否为错误信息
                if first_result.startswith("ERROR:"):
                    error_msg = first_result[6:].strip()  # 移除"ERROR:"前缀
                    logger.error(f"图像生成失败: {error_msg}")
                    self.generation_failed.emit(error_msg)
                else:
                    # 生成成功
                    logger.info(f"图像生成成功: {first_result}")
                    self.progress_updated.emit("图像生成完成")
                    self.image_generated.emit(first_result)
            else:
                error_msg = "图像生成失败：未返回有效结果"
                logger.error(error_msg)
                self.generation_failed.emit(error_msg)
                
        except Exception as e:
            # 统一异常处理，不使用SystemExit
            error_msg = f"图像生成过程中发生错误: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            
            # 发送错误信号
            self.generation_failed.emit(error_msg)
            self.error_occurred.emit(error_msg)
            
        finally:
            logger.info("=== 图像生成线程执行结束 ===")
    
    def get_status_info(self):
        """获取状态信息"""
        return {
            'prompt': self.prompt,
            'workflow_id': self.workflow_id,
            'parameters': self.parameters,
            'is_cancelled': self._is_cancelled,
            'is_running': self.isRunning(),
            'is_finished': self.isFinished()
        }