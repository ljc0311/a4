from PyQt5.QtCore import QThread, pyqtSignal
from src.utils.logger import logger
from src.models.pollinations_client import PollinationsClient

class PollinationsGenerationThread(QThread):
    """Pollinations图像生成线程"""
    
    # 信号定义
    image_generated = pyqtSignal(list)  # 生成成功信号，传递图片路径列表
    error_occurred = pyqtSignal(str)  # 生成失败信号，传递错误信息
    progress_updated = pyqtSignal(str)  # 进度更新信号
    
    def __init__(self, prompt, parameters, project_manager=None, current_project_name=None):
        """初始化Pollinations生成线程
        
        Args:
            prompt: 图像描述提示词
            parameters: Pollinations参数字典
            project_manager: 项目管理器
            current_project_name: 当前项目名称
        """
        super().__init__()
        self.prompt = prompt
        self.parameters = parameters or {}
        self.project_manager = project_manager
        self.current_project_name = current_project_name
        self._is_cancelled = False
        
        # 初始化Pollinations客户端
        self.pollinations_client = PollinationsClient()
        
        logger.info(f"PollinationsGenerationThread初始化完成")
        logger.info(f"提示词: {prompt}")
        logger.info(f"参数: {parameters}")
    
    def cancel(self):
        """取消图像生成"""
        self._is_cancelled = True
        logger.info("Pollinations图像生成已被取消")
    
    def run(self):
        """线程主执行方法"""
        logger.info("=== Pollinations图像生成线程开始执行 ===")
        
        try:
            # 检查是否已取消
            if self._is_cancelled:
                logger.info("Pollinations图像生成已取消")
                self.error_occurred.emit("图像生成已取消")
                return
            
            # 发送进度更新
            self.progress_updated.emit("正在使用Pollinations AI生成图像...")
            
            # 检查是否已取消
            if self._is_cancelled:
                logger.info("Pollinations图像生成已取消")
                self.error_occurred.emit("图像生成已取消")
                return
            
            # 调用Pollinations客户端生成图像
            logger.info("开始调用Pollinations客户端")

            # 将 project_manager 和 current_project_name 添加到参数字典中
            current_params = self.parameters.copy()
            if self.project_manager:
                current_params['project_manager'] = self.project_manager
            if self.current_project_name:
                current_params['current_project_name'] = self.current_project_name

            result = self.pollinations_client.generate_image(
                prompt=self.prompt,
                **current_params
            )
            
            # 检查是否已取消
            if self._is_cancelled:
                logger.info("Pollinations图像生成已取消")
                self.error_occurred.emit("图像生成已取消")
                return
            
            # 处理结果
            if result and isinstance(result, list):
                if len(result) > 0 and not str(result[0]).startswith("ERROR"):
                    logger.info(f"Pollinations图像生成成功，共 {len(result)} 张图片")
                    logger.info(f"生成的图片路径: {result}")
                    self.image_generated.emit(result)
                else:
                    error_msg = str(result[0]) if result else "未知错误"
                    logger.error(f"Pollinations图像生成失败: {error_msg}")
                    self.error_occurred.emit(error_msg)
            else:
                error_msg = "Pollinations返回无效结果"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                
        except Exception as e:
            error_msg = f"Pollinations图像生成过程中发生异常: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常类型: {type(e).__name__}")
            self.error_occurred.emit(error_msg)
        
        finally:
            logger.info("=== Pollinations图像生成线程执行完成 ===")