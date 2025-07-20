"""
CogView-3 Flash 图像生成引擎实现
智谱AI的免费文本到图像生成模型
"""

import asyncio
import requests
import os
import time
import json
import base64
from typing import List, Dict, Optional, Callable
from ..image_engine_base import (
    ImageGenerationEngine, EngineType, EngineStatus, 
    GenerationConfig, GenerationResult, EngineInfo, ConfigConverter
)
from src.utils.logger import logger


class CogView3FlashEngine(ImageGenerationEngine):
    """CogView-3 Flash 引擎实现"""
    
    def __init__(self, config: Dict = None):
        super().__init__(EngineType.COGVIEW_3_FLASH)
        self.config = config or {}
        self.base_url = "https://open.bigmodel.cn/api/paas/v4/images/generations"

        # 优先使用配置中的API密钥，如果没有则自动获取智谱AI密钥
        self.api_key = self.config.get('api_key', '') or self._get_zhipu_api_key()

        # 默认输出目录，会在生成时动态更新
        self.output_dir = self.config.get('output_dir', 'temp/image_cache')
        self.session = None
        # 项目相关信息
        self.project_manager = None
        self.current_project_name = None

    def _get_zhipu_api_key(self) -> str:
        """获取智谱AI的API密钥"""
        try:
            # 方法1: 尝试从SecureConfigManager获取
            try:
                from src.utils.secure_config_manager import SecureConfigManager
                secure_manager = SecureConfigManager()
                api_key = secure_manager.get_api_key("zhipu", "智谱AI")
                if api_key:
                    logger.info("从SecureConfigManager获取到智谱AI密钥")
                    return api_key
            except Exception as e:
                logger.debug(f"从SecureConfigManager获取密钥失败: {e}")

            # 方法2: 尝试从ConfigManager获取
            try:
                from src.utils.config_manager import ConfigManager
                config_manager = ConfigManager()
                models = config_manager.get_models()
                for model in models:
                    if model.get('type') == 'zhipu' or model.get('name') == '智谱AI':
                        api_key = model.get('key', '')
                        if api_key:
                            logger.info("从ConfigManager获取到智谱AI密钥")
                            return api_key
            except Exception as e:
                logger.debug(f"从ConfigManager获取密钥失败: {e}")

            # 方法3: 尝试从环境变量获取
            import os
            api_key = os.getenv('ZHIPU_API_KEY')
            if api_key:
                logger.info("从环境变量获取到智谱AI密钥")
                return api_key

            logger.warning("未找到智谱AI API密钥，请在设置中配置")
            return ""

        except Exception as e:
            logger.error(f"获取智谱AI密钥时出错: {e}")
            return ""

    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            # 检查API密钥，如果没有则尝试重新获取
            if not self.api_key:
                self.api_key = self._get_zhipu_api_key()

            if not self.api_key:
                logger.error("CogView-3 Flash引擎缺少API密钥，请在设置中配置智谱AI密钥")
                self.status = EngineStatus.ERROR
                self.last_error = "缺少智谱AI API密钥"
                return False
            
            # 动态获取输出目录
            self.output_dir = self._get_output_dir()
            
            # 创建requests会话
            self.session = requests.Session()
            self.session.timeout = 120  # 设置超时
            
            # 设置请求头
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
            
            # 测试连接
            if await self.test_connection():
                self.status = EngineStatus.IDLE
                logger.info("CogView-3 Flash引擎初始化成功")
                return True
            else:
                self.status = EngineStatus.ERROR
                logger.error("CogView-3 Flash引擎连接测试失败")
                return False
                
        except Exception as e:
            self.status = EngineStatus.ERROR
            self.last_error = str(e)
            logger.error(f"CogView-3 Flash引擎初始化失败: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self.session or not self.api_key:
                return False
            
            # 发送简单的测试请求
            test_payload = {
                "model": "cogview-3-flash",
                "prompt": "test",
                "size": "1024x1024"
            }
            
            response = self.session.post(
                self.base_url, 
                json=test_payload, 
                timeout=30
            )
            
            # 检查响应状态
            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                logger.error("CogView-3 Flash API密钥无效")
                self.last_error = "API密钥无效"
                return False
            else:
                logger.warning(f"CogView-3 Flash连接测试返回状态码: {response.status_code}")
                return response.status_code < 500  # 4xx错误可能是参数问题，但连接正常
                
        except Exception as e:
            logger.error(f"CogView-3 Flash连接测试失败: {e}")
            return False
    
    def set_project_info(self, project_manager=None, current_project_name=None):
        """设置项目信息"""
        self.project_manager = project_manager
        self.current_project_name = current_project_name
        logger.info(f"CogView-3 Flash引擎设置项目信息: project_manager={project_manager is not None}, current_project_name={current_project_name}")
    
    def _get_output_dir(self, project_manager=None, current_project_name=None) -> str:
        """获取输出目录"""
        try:
            # 优先使用传入的项目管理器
            if project_manager and current_project_name:
                try:
                    project_root = project_manager.get_current_project_path()
                    if project_root:
                        output_dir = os.path.join(project_root, 'images', 'cogview_3_flash')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"使用项目输出目录: {output_dir}")
                        return output_dir
                except AttributeError:
                    if hasattr(project_manager, 'current_project') and project_manager.current_project:
                        project_root = project_manager.current_project.get('project_dir')
                        if project_root:
                            output_dir = os.path.join(project_root, 'images', 'cogview_3_flash')
                            os.makedirs(output_dir, exist_ok=True)
                            logger.info(f"使用项目输出目录: {output_dir}")
                            return output_dir

            # 尝试使用实例变量
            if self.project_manager:
                try:
                    project_root = self.project_manager.get_current_project_path()
                    if project_root:
                        output_dir = os.path.join(project_root, 'images', 'cogview_3_flash')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"使用项目输出目录: {output_dir}")
                        return output_dir
                    else:
                        logger.info("当前没有加载项目，使用默认目录")
                except AttributeError:
                    if hasattr(self.project_manager, 'current_project') and self.project_manager.current_project:
                        project_root = self.project_manager.current_project.get('project_dir')
                        if project_root:
                            output_dir = os.path.join(project_root, 'images', 'cogview_3_flash')
                            os.makedirs(output_dir, exist_ok=True)
                            logger.info(f"使用项目输出目录: {output_dir}")
                            return output_dir
                except Exception as e:
                    logger.warning(f"获取项目路径失败: {e}，使用默认目录")

        except Exception as e:
            logger.warning(f"无法获取项目目录: {e}")

        # 无项目时使用temp/image_cache
        output_dir = os.path.join(os.getcwd(), 'temp', 'image_cache', 'cogview_3_flash')
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
                progress_callback("准备CogView-3 Flash生成请求...")
            
            # 转换配置
            cogview_config = self._convert_config(config)

            # 生成单张图像 - CogView-3 Flash不支持批量生成
            if progress_callback:
                progress_callback("生成图像...")

            image_path = await self._generate_single_image(cogview_config, 0)
            image_paths = [image_path] if image_path else []
            
            generation_time = time.time() - start_time
            success = len(image_paths) > 0
            
            # 更新统计
            self.update_stats(success, 0.0, "" if success else "部分或全部图像生成失败")
            
            result = GenerationResult(
                success=success,
                image_paths=image_paths,
                generation_time=generation_time,
                cost=0.0,  # CogView-3 Flash免费
                engine_type=self.engine_type,
                metadata={
                    'total_requested': 1,  # 每次只生成1张图像
                    'total_generated': len(image_paths),
                    'config': cogview_config
                }
            )

            if not success:
                result.error_message = f"图像生成失败"
            
            return result
            
        except Exception as e:
            error_msg = f"CogView-3 Flash生成失败: {e}"
            logger.error(error_msg)
            self.update_stats(False, 0.0, error_msg)
            
            return GenerationResult(
                success=False,
                error_message=error_msg,
                engine_type=self.engine_type
            )
        finally:
            self.status = EngineStatus.IDLE
    
    def _convert_config(self, config: GenerationConfig) -> Dict:
        """转换配置为CogView-3 Flash格式"""
        # 支持的尺寸映射
        size_mapping = {
            (1024, 1024): "1024x1024",
            (768, 1344): "768x1344", 
            (864, 1152): "864x1152",
            (1344, 768): "1344x768",
            (1152, 864): "1152x864", 
            (1440, 720): "1440x720",
            (720, 1440): "720x1440"
        }
        
        # 找到最接近的支持尺寸
        target_size = (config.width, config.height)
        if target_size in size_mapping:
            size = size_mapping[target_size]
        else:
            # 默认使用1024x1024
            size = "1024x1024"
            logger.warning(f"不支持的尺寸 {target_size}，使用默认尺寸 1024x1024")
        
        cogview_config = {
            'model': 'cogview-3-flash',
            'prompt': config.prompt,
            'size': size,
            'n': 1  # 固定为1，因为CogView-3 Flash API不支持批量生成
            # 不指定response_format，使用默认的URL格式
        }
        
        # 添加自定义参数，但排除API不支持的参数
        if hasattr(config, 'custom_params') and config.custom_params:
            # 保存workflow_id用于文件命名
            workflow_id = config.custom_params.get('workflow_id')

            # 只添加API支持的参数
            api_supported_params = {}
            for key, value in config.custom_params.items():
                if key not in ['workflow_id']:  # 排除API不支持的参数
                    api_supported_params[key] = value

            cogview_config.update(api_supported_params)

            # 将workflow_id保存到配置中用于文件命名
            if workflow_id:
                cogview_config['_workflow_id'] = workflow_id

        return cogview_config



    async def _download_image(self, image_url: str, image_path: str) -> bool:
        """下载图像到本地"""
        try:
            # 使用requests下载图像
            response = self.session.get(image_url, timeout=60)

            if response.status_code == 200:
                # 确保输出目录存在
                os.makedirs(os.path.dirname(image_path), exist_ok=True)

                # 保存图像
                with open(image_path, 'wb') as f:
                    f.write(response.content)

                # 验证文件是否成功保存
                if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                    logger.info(f"图像下载成功: {image_path} ({os.path.getsize(image_path)} 字节)")
                    return True
                else:
                    logger.error(f"图像文件保存失败或为空: {image_path}")
                    return False
            else:
                logger.error(f"下载图像失败: HTTP {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return False

        except Exception as e:
            logger.error(f"下载图像时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _generate_single_image(self, config: Dict, index: int) -> Optional[str]:
        """生成单张图像"""
        try:
            # 记录请求参数
            logger.info(f"CogView-3 Flash API 请求参数: {config}")

            # 发送请求
            response = self.session.post(
                self.base_url,
                json=config,
                timeout=120
            )

            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"CogView-3 Flash API 响应: {response_data}")

                # 检查响应格式
                if 'data' in response_data and len(response_data['data']) > 0:
                    image_data = response_data['data'][0]
                    logger.info(f"图像数据结构: {list(image_data.keys())}")

                    if 'url' in image_data:
                        # 从URL下载图像
                        image_url = image_data['url']
                        logger.info(f"下载图像: {image_url}")

                        # 下载图像
                        image_response = self.session.get(image_url, timeout=60)
                        if image_response.status_code == 200:
                            # 动态获取输出目录
                            current_output_dir = self._get_output_dir()
                            os.makedirs(current_output_dir, exist_ok=True)

                            # 生成唯一文件名 - 添加时间戳避免覆盖
                            import time
                            timestamp = int(time.time() * 1000)  # 毫秒级时间戳
                            workflow_id = config.get('_workflow_id', f'shot_{index}')
                            if workflow_id:
                                filename = f"cogview_3_flash_{workflow_id}_{timestamp}.png"
                            else:
                                filename = f"cogview_3_flash_{index+1}_{timestamp}.png"
                            filepath = os.path.join(current_output_dir, filename)

                            # 保存图像
                            with open(filepath, 'wb') as f:
                                f.write(image_response.content)

                            logger.info(f"图像已保存: {filepath}")
                            return filepath
                        else:
                            logger.error(f"下载图像失败: HTTP {image_response.status_code}")
                            return None
                    elif 'b64_json' in image_data:
                        # 处理base64格式（备用）
                        image_base64 = image_data['b64_json']
                        image_bytes = base64.b64decode(image_base64)

                        # 动态获取输出目录
                        current_output_dir = self._get_output_dir()
                        os.makedirs(current_output_dir, exist_ok=True)

                        # 生成唯一文件名
                        workflow_id = config.get('workflow_id', f'shot_{index}')
                        safe_workflow_id = workflow_id.replace('-', '_').replace(':', '_')
                        filename = f"cogview3_flash_{safe_workflow_id}.png"
                        filepath = os.path.join(current_output_dir, filename)

                        # 保存图像
                        with open(filepath, 'wb') as f:
                            f.write(image_bytes)

                        logger.info(f"图像已保存: {filepath}")
                        return filepath
                    else:
                        logger.error("响应中没有找到url或b64_json数据")
                        return None
                else:
                    logger.error("响应格式错误，没有找到data字段")
                    return None
            else:
                logger.error(f"CogView-3 Flash请求失败: HTTP {response.status_code}")
                logger.error(f"响应内容: {response.text}")

                # 特殊处理常见错误
                if response.status_code == 401:
                    logger.error("API密钥无效或已过期，请检查智谱AI密钥配置")
                elif response.status_code == 429:
                    logger.error("API请求频率超限，请稍后重试")
                elif response.status_code == 500:
                    logger.error("CogView-3 Flash服务内部错误，建议切换到其他引擎")

                return None

        except Exception as e:
            logger.error(f"生成单张图像失败: {e}")
            return None

    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        return ['cogview-3-flash']

    def get_engine_info(self) -> EngineInfo:
        """获取引擎信息"""
        return EngineInfo(
            name="CogView-3 Flash",
            version="1.0",
            description="智谱AI的免费文本到图像生成模型，支持多种分辨率",
            is_free=True,
            supports_batch=True,
            supports_custom_models=False,
            max_batch_size=5,  # 限制批量大小以避免API限制
            supported_sizes=[
                (1024, 1024), (768, 1344), (864, 1152),
                (1344, 768), (1152, 864), (1440, 720), (720, 1440)
            ],
            cost_per_image=0.0,
            rate_limit=60  # 估计值，需要根据实际API限制调整
        )

    async def cleanup(self):
        """清理资源"""
        if self.session:
            self.session.close()
            self.session = None

        self.status = EngineStatus.OFFLINE
        await super().cleanup()
