"""
Pollinations AI 图像生成引擎实现
"""

import asyncio
import requests
import os
import time
import urllib.parse
from typing import List, Dict, Optional, Callable
from src.models.image_engine_base import (
    ImageGenerationEngine, EngineType, EngineStatus, 
    GenerationConfig, GenerationResult, EngineInfo, ConfigConverter
)
from src.utils.logger import logger


class PollinationsEngine(ImageGenerationEngine):
    """Pollinations AI 引擎实现"""
    
    def __init__(self, config: Dict = None):
        super().__init__(EngineType.POLLINATIONS)
        self.config = config or {}
        self.base_url = "https://image.pollinations.ai"
        # 默认输出目录，会在生成时动态更新
        self.output_dir = self.config.get('output_dir', 'temp/image_cache')
        self.session = None
        # 项目相关信息
        self.project_manager = None
        self.current_project_name = None
        
    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            # 动态获取输出目录
            self.output_dir = self._get_output_dir()
            # 不在初始化时创建目录，只在实际生成图像时创建
            
            # 创建requests会话，配置SSL和连接参数
            self.session = requests.Session()
            self.session.timeout = 30  # 设置超时
            
            # 配置SSL和连接参数以解决连接问题
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            import urllib3
            
            # 禁用SSL警告（仅用于解决连接问题）
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # 配置重试策略
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            # 设置请求头
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            # 测试连接
            if await self.test_connection():
                self.status = EngineStatus.IDLE
                logger.info("Pollinations引擎初始化成功")
                return True
            else:
                self.status = EngineStatus.ERROR
                logger.error("Pollinations引擎连接测试失败")
                return False
                
        except Exception as e:
            self.status = EngineStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Pollinations引擎初始化失败: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self.session:
                return False
            
            # 配置会话以处理SSL问题
            import ssl
            import urllib3
            
            # 创建一个新的会话用于测试，配置更宽松的SSL设置
            test_session = requests.Session()
            
            # 配置适配器和重试策略
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            retry_strategy = Retry(
                total=2,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            test_session.mount("http://", adapter)
            test_session.mount("https://", adapter)
            
            # 设置更友好的请求头
            test_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'image/*,*/*;q=0.8',
                'Connection': 'keep-alive',
            })
                
            # 发送简单的测试请求 - 使用正确的API格式
            test_prompt = "test"
            test_url = f"{self.base_url}/prompt/{test_prompt}?width=64&height=64&nologo=true"
            
            logger.info(f"测试连接URL: {test_url}")
            
            # 尝试多种方式连接
            response = None
            
            # 方法1：正常连接
            try:
                response = test_session.get(test_url, timeout=15, verify=True)
            except (ssl.SSLError, urllib3.exceptions.SSLError) as ssl_error:
                logger.warning(f"SSL连接失败，尝试不验证SSL: {ssl_error}")
                # 方法2：不验证SSL证书（仅用于测试）
                try:
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    response = test_session.get(test_url, timeout=15, verify=False)
                except Exception as e2:
                    logger.error(f"不验证SSL也失败: {e2}")
                    return False
            except Exception as e:
                logger.error(f"连接测试异常: {e}")
                return False
            
            if response:
                logger.info(f"连接测试响应: {response.status_code}")
                
                # 检查是否返回图像
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    is_image = content_type.startswith('image/')
                    logger.info(f"连接测试成功，内容类型: {content_type}")
                    
                    # 如果测试成功，更新主会话的配置
                    if is_image:
                        self.session.headers.update(test_session.headers)
                        # 如果需要不验证SSL，也更新主会话
                        if not test_session.verify:
                            self.session.verify = False
                            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    
                    return is_image
                else:
                    logger.warning(f"连接测试失败: HTTP {response.status_code}")
                    return False
            else:
                logger.error("无法获取响应")
                return False
                
        except Exception as e:
            logger.error(f"Pollinations连接测试失败: {e}")
            return False
    
    def set_project_info(self, project_manager=None, current_project_name=None):
        """设置项目信息"""
        self.project_manager = project_manager
        self.current_project_name = current_project_name
        logger.info(f"Pollinations引擎设置项目信息: project_manager={project_manager is not None}, current_project_name={current_project_name}")
    
    def _get_output_dir(self, project_manager=None, current_project_name=None) -> str:
        """获取输出目录"""
        try:
            # 优先使用传入的项目管理器
            if project_manager and current_project_name:
                try:
                    # 尝试使用get_current_project_path方法
                    project_root = project_manager.get_current_project_path()
                    if project_root:
                        output_dir = os.path.join(project_root, 'images', 'pollinations')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"使用项目输出目录: {output_dir}")
                        return output_dir
                except AttributeError:
                    # 如果没有get_current_project_path方法，尝试其他方法
                    if hasattr(project_manager, 'current_project') and project_manager.current_project:
                        project_root = project_manager.current_project.get('project_dir')
                        if project_root:
                            output_dir = os.path.join(project_root, 'images', 'pollinations')
                            os.makedirs(output_dir, exist_ok=True)
                            logger.info(f"使用项目输出目录: {output_dir}")
                            return output_dir

            # 尝试使用实例变量
            if self.project_manager:
                try:
                    # 使用get_current_project_path方法获取当前项目路径
                    project_root = self.project_manager.get_current_project_path()
                    if project_root:
                        output_dir = os.path.join(project_root, 'images', 'pollinations')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"使用项目输出目录: {output_dir}")
                        return output_dir
                    else:
                        logger.info("当前没有加载项目，使用默认目录")
                except AttributeError:
                    # 如果没有get_current_project_path方法，尝试其他方法
                    if hasattr(self.project_manager, 'current_project') and self.project_manager.current_project:
                        project_root = self.project_manager.current_project.get('project_dir')
                        if project_root:
                            output_dir = os.path.join(project_root, 'images', 'pollinations')
                            os.makedirs(output_dir, exist_ok=True)
                            logger.info(f"使用项目输出目录: {output_dir}")
                            return output_dir
                except Exception as e:
                    logger.warning(f"获取项目路径失败: {e}，使用默认目录")

        except Exception as e:
            logger.warning(f"无法获取项目目录: {e}")

        # 无项目时使用temp/image_cache
        output_dir = os.path.join(os.getcwd(), 'temp', 'image_cache', 'pollinations')
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"使用默认输出目录: {output_dir}")
        return output_dir
    
    async def generate(self, config: GenerationConfig, 
                      progress_callback: Optional[Callable] = None,
                      project_manager=None, current_project_name=None) -> GenerationResult:
        """生成图像"""
        # 设置项目信息
        if project_manager and current_project_name:
            self.project_manager = project_manager
            self.current_project_name = current_project_name
            # 更新输出目录
            self.output_dir = self._get_output_dir()
        
        start_time = time.time()
        self.status = EngineStatus.BUSY
        
        try:
            if progress_callback:
                progress_callback("准备Pollinations生成请求...")
            
            # 转换配置
            pollinations_config = ConfigConverter.to_pollinations(config)
            
            # 生成图像
            image_paths = []
            for i in range(config.batch_size):
                if progress_callback:
                    progress_callback(f"生成第 {i+1}/{config.batch_size} 张图像...")
                
                image_path = await self._generate_single_image(pollinations_config, i)
                if image_path:
                    image_paths.append(image_path)
                else:
                    # 单张失败不影响其他图像生成
                    logger.warning(f"第 {i+1} 张图像生成失败")
            
            generation_time = time.time() - start_time
            success = len(image_paths) > 0
            
            # 更新统计
            self.update_stats(success, 0.0, "" if success else "部分或全部图像生成失败")
            
            result = GenerationResult(
                success=success,
                image_paths=image_paths,
                generation_time=generation_time,
                cost=0.0,  # Pollinations免费
                engine_type=self.engine_type,
                metadata={
                    'total_requested': config.batch_size,
                    'total_generated': len(image_paths),
                    'config': pollinations_config
                }
            )
            
            if not success:
                result.error_message = f"仅生成了 {len(image_paths)}/{config.batch_size} 张图像"
            
            return result
            
        except Exception as e:
            error_msg = f"Pollinations生成失败: {e}"
            logger.error(error_msg)
            self.update_stats(False, 0.0, error_msg)
            
            return GenerationResult(
                success=False,
                error_message=error_msg,
                engine_type=self.engine_type
            )
        finally:
            self.status = EngineStatus.IDLE
    
    async def _generate_single_image(self, config: Dict, index: int) -> Optional[str]:
        """生成单张图像"""
        try:
            # 构建请求参数 - 根据最新API文档更新
            params = {
                'width': config['width'],
                'height': config['height'],
                'model': config.get('model', 'flux'),
                'nologo': str(config.get('nologo', True)).lower(),
                'enhance': str(config.get('enhance', False)).lower(),
                'safe': str(config.get('safe', True)).lower()
            }

            # 添加seed参数（如果存在且不为-1）
            if config.get('seed') is not None and config.get('seed') != -1:
                params['seed'] = config['seed'] + index  # 为每张图像使用不同种子

            # 添加private参数（如果存在）
            if config.get('private') is not None:
                params['private'] = str(config.get('private', False)).lower()

            # 记录实际发送的参数
            logger.info(f"Pollinations API 请求参数: {params}")

            # URL编码提示词 - 使用更安全的编码方式
            prompt = config['prompt']
            encoded_prompt = urllib.parse.quote(prompt, safe='')
            
            # 构建完整URL - 使用正确的API格式
            url = f"{self.base_url}/prompt/{encoded_prompt}"

            # 发送请求 - 使用requests而不是aiohttp
            logger.info(f"发送请求到: {url}")
            logger.info(f"请求参数: {params}")
            
            response = self.session.get(url, params=params, timeout=60)
            
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应头: {dict(response.headers)}")

            if response.status_code == 200:
                # 检查响应内容类型
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"响应内容类型不是图像: {content_type}")
                    # 尝试读取响应内容作为文本查看错误信息
                    try:
                        error_text = response.text[:500]  # 只读取前500字符
                        logger.error(f"响应内容: {error_text}")
                    except:
                        pass
                    return None

                # 动态获取输出目录
                current_output_dir = self._get_output_dir()
                os.makedirs(current_output_dir, exist_ok=True)

                # 生成唯一文件名
                workflow_id = config.get('workflow_id', f'shot_{index}')
                # 将workflow_id中的特殊字符替换为下划线，确保文件名安全
                safe_workflow_id = workflow_id.replace('-', '_').replace(':', '_').replace(' ', '_')
                timestamp = int(time.time())
                filename = f"pollinations_{safe_workflow_id}_{timestamp}.png"
                filepath = os.path.join(current_output_dir, filename)

                # 保存图像文件
                with open(filepath, 'wb') as f:
                    f.write(response.content)

                # 验证文件是否成功保存
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    logger.info(f"图像已保存: {filepath} (大小: {os.path.getsize(filepath)} 字节)")
                    return filepath
                else:
                    logger.error(f"图像文件保存失败或文件为空: {filepath}")
                    return None
            else:
                logger.error(f"Pollinations请求失败: HTTP {response.status_code}")
                logger.error(f"请求URL: {url}")
                logger.error(f"请求参数: {params}")
                
                # 尝试读取错误响应内容
                try:
                    error_content = response.text[:1000]  # 读取前1000字符
                    logger.error(f"错误响应内容: {error_content}")
                except:
                    logger.error("无法读取错误响应内容")
                
                return None

        except Exception as e:
            logger.error(f"生成单张图像失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return None
    
    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        return [
            'flux',
            'turbo', 
            'flux-realism'
        ]
    
    def get_engine_info(self) -> EngineInfo:
        """获取引擎信息"""
        return EngineInfo(
            name="Pollinations AI",
            version="1.0",
            description="免费的AI图像生成服务，支持多种模型",
            is_free=True,
            supports_batch=True,
            supports_custom_models=False,
            max_batch_size=10,
            supported_sizes=[
                (512, 512), (768, 768), (1024, 1024),
                (1024, 768), (768, 1024),
                (1280, 720), (720, 1280)
            ],
            cost_per_image=0.0,
            rate_limit=60  # 估计值
        )
    
    async def cleanup(self):
        """清理资源"""
        if self.session:
            self.session.close()
            self.session = None
        
        self.status = EngineStatus.OFFLINE
        await super().cleanup()