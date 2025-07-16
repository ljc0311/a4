from PyQt5.QtCore import QThread, pyqtSignal
import logging

logger = logging.getLogger(__name__)

class TextRewriteThread(QThread):
    """文本改写线程"""
    progress_updated = pyqtSignal(str)  # 进度更新信号
    rewrite_completed = pyqtSignal(str)  # 改写完成信号，传递改写后的文本
    error_occurred = pyqtSignal(str)     # 错误信号，传递错误信息
    
    def __init__(self, llm_api, input_text):
        super().__init__()
        self.llm_api = llm_api
        self.input_text = input_text
        self.is_cancelled = False
    
    def run(self):
        """在新线程中执行文本改写"""
        try:
            self.progress_updated.emit("正在连接大模型...")
            
            if self.is_cancelled:
                return
            
            self.progress_updated.emit("正在改写文本，请稍候...")
            
            # 调用大模型进行改写
            response = self.llm_api.rewrite_text(self.input_text)
            
            if self.is_cancelled:
                return
            
            if response:
                self.rewrite_completed.emit(response)
                logger.info("文本改写完成")
            else:
                self.error_occurred.emit("改写失败，请检查网络连接和模型配置")
                
        except Exception as e:
            if not self.is_cancelled:
                error_msg = f"改写文本时发生错误: {str(e)}"
                self.error_occurred.emit(error_msg)
                logger.exception("文本改写线程异常")
    
    def cancel(self):
        """取消操作"""
        self.is_cancelled = True

class ShotsGenerationThread(QThread):
    """分镜生成线程"""
    progress_updated = pyqtSignal(str)   # 进度更新信号
    shots_generated = pyqtSignal(list)   # 分镜生成完成信号，传递分镜数据
    error_occurred = pyqtSignal(str)     # 错误信号，传递错误信息
    
    def __init__(self, text_parser, output_text):
        super().__init__()
        self.text_parser = text_parser
        self.output_text = output_text
        self.is_cancelled = False
    
    def run(self):
        """在新线程中执行分镜生成"""
        try:
            self.progress_updated.emit("正在连接大模型...")
            
            if self.is_cancelled:
                return
            
            self.progress_updated.emit("正在生成分镜，请稍候...")
            
            # 创建进度回调函数，用于检查取消状态
            def progress_callback(message):
                if self.is_cancelled:
                    raise InterruptedError("用户取消了分镜生成")
                self.progress_updated.emit(message)
            
            # 解析文本生成分镜，传递进度回调
            result = self.text_parser.parse_text(self.output_text, progress_callback=progress_callback)
            
            if self.is_cancelled:
                return
            
            if result.get('error'):
                self.error_occurred.emit(f"解析分镜失败: {result['error']}")
            elif result.get('shots'):
                shots_data = result['shots']
                if shots_data:  # 检查shots_data是否为空
                    self.shots_generated.emit(shots_data)
                    logger.info(f"成功生成 {len(shots_data)} 个分镜")
                else:
                    self.error_occurred.emit("未能从文本中解析出有效分镜，请检查输入或大模型输出。")
            else:
                self.error_occurred.emit("未能从文本中解析出分镜信息，请检查输入或大模型输出。")
                
        except InterruptedError as e:
            logger.info(f"分镜生成被用户取消: {str(e)}")
            self.progress_updated.emit("⏹️ 分镜生成已取消")
        except Exception as e:
            if not self.is_cancelled:
                error_msg = f"生成分镜时发生错误: {str(e)}"
                self.error_occurred.emit(error_msg)
                logger.exception("分镜生成线程异常")
    
    def cancel(self):
        """取消操作"""
        self.is_cancelled = True