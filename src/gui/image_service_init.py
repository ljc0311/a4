# 图像生成服务初始化方法
# 这个文件包含了主窗口中图像生成服务的初始化逻辑

def _init_image_generation_service(self):
    """初始化图像生成服务"""
    try:
        from src.models.image_generation_service import ImageGenerationService
        
        # 创建图像生成服务实例
        self.image_generation_service = ImageGenerationService()
        
        # 设置输出目录
        output_dir = self.app_settings.get('comfyui_output_dir', '')
        if output_dir and os.path.exists(output_dir):
            self.image_generation_service.set_output_directory(output_dir)
        
        # 如果有ComfyUI客户端，设置为备用引擎
        if hasattr(self, 'comfyui_client') and self.comfyui_client:
            self.image_generation_service.set_comfyui_client(self.comfyui_client)
        
        logger.info(f"图像生成服务初始化成功，当前引擎: {self.image_generation_service.current_engine.value}")
        
    except Exception as e:
        logger.error(f"图像生成服务初始化失败: {e}")
        self.image_generation_service = None