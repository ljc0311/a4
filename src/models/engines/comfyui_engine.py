# -*- coding: utf-8 -*-
"""
ComfyUI 图像生成引擎实现
支持本地和云端ComfyUI服务
"""

import asyncio
import aiohttp
import os
import time
import uuid
from typing import List, Dict, Optional, Callable
from ..image_engine_base import (
    ImageGenerationEngine, EngineType, EngineStatus, 
    GenerationConfig, GenerationResult, EngineInfo, ConfigConverter
)
from ..workflow_manager import WorkflowManager
from src.utils.logger import logger


class ComfyUIBaseEngine(ImageGenerationEngine):
    """ComfyUI基础引擎类"""
    
    def __init__(self, engine_type: EngineType, config: Dict = None):
        super().__init__(engine_type)
        self.config = config or {}
        self.api_url = self.config.get('api_url', 'http://127.0.0.1:8188').rstrip('/')
        self.client_id = str(uuid.uuid4())
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 项目管理器（可选）
        self.project_manager = self.config.get('project_manager')
        self.current_project_name = None
        
        # 设置输出目录
        self.output_dir = self._get_output_dir()
        
        # 初始化工作流管理器
        workflows_dir = self.config.get('workflows_dir')
        if workflows_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            workflows_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(current_dir))), 
                'config', 'workflows'
            )
        
        self.workflow_manager = WorkflowManager(workflows_dir)
    
    def _get_output_dir(self, project_manager=None, current_project_name=None) -> str:
        """获取输出目录"""
        # 优先使用传入的项目管理器
        if project_manager and current_project_name:
            try:
                project_root = project_manager.get_project_root(current_project_name)
                if project_root:
                    output_dir = os.path.join(project_root, 'images', 'comfyui')
                    os.makedirs(output_dir, exist_ok=True)
                    logger.info(f"ComfyUI使用项目输出目录: {output_dir}")
                    return output_dir
            except Exception as e:
                logger.warning(f"ComfyUI获取项目路径失败: {e}，使用默认目录")
        
        # 如果有项目管理器，优先使用当前项目路径
        if self.project_manager:
            try:
                # 检查项目管理器是否有get_project_root方法
                if hasattr(self.project_manager, 'get_project_root'):
                    project_root = self.project_manager.get_project_root()
                elif hasattr(self.project_manager, 'get_current_project_path'):
                    project_root = self.project_manager.get_current_project_path()
                else:
                    logger.warning("项目管理器缺少获取项目路径的方法")
                    project_root = None

                if project_root:
                    output_dir = os.path.join(project_root, 'images', 'comfyui')
                    os.makedirs(output_dir, exist_ok=True)
                    logger.info(f"ComfyUI使用项目输出目录: {output_dir}")
                    return output_dir
                else:
                    logger.info("ComfyUI当前没有加载项目，使用默认目录")
            except Exception as e:
                logger.warning(f"ComfyUI获取项目路径失败: {e}，使用默认目录")
        
        # 无项目时使用配置中的目录或默认目录
        output_dir = self.config.get('output_dir', 'output/images')
        logger.info(f"ComfyUI使用默认输出目录: {output_dir}")
        return output_dir
        
    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            # 不在初始化时创建目录，只在实际生成图像时创建

            # 创建HTTP会话 - 配置代理绕过以确保本地连接正常
            connector = aiohttp.TCPConnector()
            self.session = aiohttp.ClientSession(
                connector=connector,
                trust_env=False  # 不使用环境变量中的代理设置
            )

            # 测试连接
            if await self.test_connection():
                self.status = EngineStatus.IDLE
                logger.info(f"ComfyUI引擎初始化成功: {self.api_url}")
                return True
            else:
                self.status = EngineStatus.ERROR
                logger.error(f"ComfyUI引擎连接测试失败: {self.api_url}")
                return False

        except Exception as e:
            self.status = EngineStatus.ERROR
            self.last_error = str(e)
            logger.error(f"ComfyUI引擎初始化失败: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            # 使用同步的代理绕过工具进行连接测试，确保一致性
            from src.utils.proxy_bypass import proxy_bypass

            response = proxy_bypass.requests_get(
                f"{self.api_url}/queue",
                bypass_proxy=True,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"ComfyUI连接测试成功: {self.api_url}")
                return True
            else:
                logger.error(f"ComfyUI连接测试失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"ComfyUI连接测试失败: {e}")
            return False

    async def _check_connection(self) -> bool:
        """检查ComfyUI服务连接"""
        try:
            # 使用代理绕过工具检查连接
            from src.utils.proxy_bypass import proxy_bypass

            response = proxy_bypass.requests_get(
                f"{self.api_url}/queue",
                bypass_proxy=True,
                timeout=10
            )

            if response.status_code == 200:
                logger.info("ComfyUI连接检查成功")
                return True
            elif response.status_code == 502:
                logger.error(f"ComfyUI服务返回502错误 - 服务可能未正常启动或配置错误")
                logger.error(f"请检查: 1) ComfyUI是否已启动 2) 端口8188是否正确 3) 服务配置是否正常")
                return False
            else:
                logger.error(f"ComfyUI服务响应异常: HTTP {response.status_code}")
                return False
        except Exception as e:
            error_str = str(e)
            if "ConnectionError" in error_str or "连接被拒绝" in error_str:
                logger.error(f"无法连接到ComfyUI服务 ({self.api_url}) - 连接被拒绝")
                logger.error("请检查: 1) ComfyUI服务是否已启动 2) 代理设置是否影响本地连接")
            elif "timeout" in error_str.lower():
                logger.error(f"ComfyUI服务连接超时 ({self.api_url})")
                logger.error("可能原因: 1) 服务响应缓慢 2) 代理设置导致超时")
            else:
                logger.error(f"ComfyUI连接检查失败: {e}")
            return False
        except Exception as e:
            logger.error(f"ComfyUI连接检查失败: {e}")
            return False

    async def _ensure_session_valid(self):
        """确保HTTP会话在当前事件循环中有效"""
        try:
            # 检查会话是否存在且未关闭
            if self.session and not self.session.closed:
                try:
                    # 尝试获取当前事件循环
                    current_loop = asyncio.get_running_loop()
                    # 检查会话是否在当前事件循环中
                    if hasattr(self.session, '_connector') and hasattr(self.session._connector, '_loop'):
                        session_loop = self.session._connector._loop
                        if session_loop != current_loop:
                            logger.info("检测到事件循环变化，重新创建ComfyUI HTTP会话")
                            await self.session.close()
                            self.session = None
                except RuntimeError:
                    # 没有运行中的事件循环，重新创建会话
                    logger.info("没有运行中的事件循环，重新创建ComfyUI HTTP会话")
                    if self.session:
                        await self.session.close()
                    self.session = None

            # 如果会话不存在或已关闭，重新创建
            if not self.session or self.session.closed:
                logger.info("重新创建ComfyUI HTTP会话")
                connector = aiohttp.TCPConnector()
                self.session = aiohttp.ClientSession(
                    connector=connector,
                    trust_env=False  # 不使用环境变量中的代理设置
                )

        except Exception as e:
            logger.warning(f"确保ComfyUI会话有效时出错: {e}")
            # 重新创建会话
            if self.session:
                try:
                    await self.session.close()
                except Exception:
                    pass

            connector = aiohttp.TCPConnector()
            self.session = aiohttp.ClientSession(
                connector=connector,
                trust_env=False  # 不使用环境变量中的代理设置
            )

    async def generate(self, config: GenerationConfig,
                      progress_callback: Optional[Callable] = None,
                      project_manager=None, current_project_name=None) -> GenerationResult:
        """生成图像"""
        start_time = time.time()
        self.status = EngineStatus.BUSY

        # 设置项目信息
        if project_manager and current_project_name:
            self.project_manager = project_manager
            self.current_project_name = current_project_name

        try:
            # 确保HTTP会话在当前事件循环中有效
            await self._ensure_session_valid()

            # 检查ComfyUI服务连接
            if not await self._check_connection():
                error_msg = f"无法连接到ComfyUI服务 ({self.api_url})，请确保ComfyUI正在运行"
                logger.error(error_msg)
                self.status = EngineStatus.ERROR
                return GenerationResult(
                    success=False,
                    error_message=error_msg,
                    engine_type=self.engine_type
                )

            # 动态更新输出目录（确保使用最新的项目路径）
            current_output_dir = self._get_output_dir(project_manager, current_project_name)
            if current_output_dir != self.output_dir:
                self.output_dir = current_output_dir
                os.makedirs(self.output_dir, exist_ok=True)
            
            if progress_callback:
                progress_callback("准备ComfyUI生成请求...")
            
            # 转换配置
            comfyui_config = ConfigConverter.to_comfyui(config)
            
            # 生成工作流JSON
            workflow_json = self.workflow_manager.generate_workflow_json(
                config.prompt, comfyui_config
            )
            
            if not workflow_json:
                raise Exception("工作流JSON生成失败")
            
            if progress_callback:
                progress_callback("执行ComfyUI工作流...")
            
            # 执行工作流
            image_paths = await self._execute_workflow(workflow_json, progress_callback)
            
            generation_time = time.time() - start_time
            success = len(image_paths) > 0 and not any(path.startswith('ERROR:') for path in image_paths)
            
            # 计算成本（如果是云端服务）
            cost = self._calculate_cost(config) if self.engine_type == EngineType.COMFYUI_CLOUD else 0.0
            
            # 更新统计
            error_msg = "" if success else "生成失败或部分失败"
            self.update_stats(success, cost, error_msg)
            
            result = GenerationResult(
                success=success,
                image_paths=image_paths if success else [],
                generation_time=generation_time,
                cost=cost,
                engine_type=self.engine_type,
                metadata={
                    'workflow_config': comfyui_config,
                    'client_id': self.client_id
                }
            )
            
            if not success:
                result.error_message = '; '.join([p for p in image_paths if p.startswith('ERROR:')])
            
            return result
            
        except Exception as e:
            error_msg = f"ComfyUI生成失败: {e}"
            logger.error(error_msg)
            self.update_stats(False, 0.0, error_msg)
            
            return GenerationResult(
                success=False,
                error_message=error_msg,
                engine_type=self.engine_type
            )
    
    async def _execute_workflow(self, workflow_json: Dict, 
                               progress_callback: Optional[Callable] = None) -> List[str]:
        """执行工作流并返回图片路径"""
        logger.info(f"开始执行ComfyUI工作流，客户端ID: {self.client_id}")
        
        request_payload = {
            "prompt": workflow_json, 
            "client_id": self.client_id
        }
        
        try:
            # 提交任务
            if progress_callback:
                progress_callback("提交任务到ComfyUI...")

            # 使用代理绕过工具发送请求
            from src.utils.proxy_bypass import proxy_bypass

            response = proxy_bypass.requests_post(
                f"{self.api_url}/prompt",
                bypass_proxy=True,
                json=request_payload,
                timeout=60
            )
            response.raise_for_status()
            prompt_response = response.json()

            if 'prompt_id' not in prompt_response:
                raise Exception(f"ComfyUI未返回prompt_id: {prompt_response}")

            prompt_id = prompt_response['prompt_id']
            logger.info(f"ComfyUI任务已提交，prompt_id: {prompt_id}")

            # 等待完成
            if progress_callback:
                progress_callback("等待ComfyUI处理...")

            return await self._wait_for_completion(prompt_id, workflow_json, progress_callback)
            
        except Exception as e:
            logger.error(f"执行ComfyUI工作流失败: {e}")
            return [f"ERROR: 执行工作流失败: {str(e)}"]
    
    async def _wait_for_completion(self, prompt_id: str, workflow_json: Dict,
                                  progress_callback: Optional[Callable] = None) -> List[str]:
        """等待任务完成并获取结果"""
        max_wait_time = 120  # 最大等待时间
        check_interval = 2   # 检查间隔
        waited_time = 0
        
        while waited_time < max_wait_time:
            try:
                if progress_callback:
                    progress_callback(f"等待处理中... ({waited_time}/{max_wait_time}s)")
                
                # 检查历史记录 - 使用代理绕过工具
                from src.utils.proxy_bypass import proxy_bypass

                response = proxy_bypass.requests_get(
                    f"{self.api_url}/history/{prompt_id}",
                    bypass_proxy=True,
                    timeout=30
                )
                response.raise_for_status()
                history_data = response.json()
                
                # 检查是否完成
                if prompt_id in history_data:
                    prompt_history = history_data[prompt_id]
                    if 'outputs' in prompt_history:
                        logger.info(f"任务 {prompt_id} 已完成")
                        if progress_callback:
                            progress_callback("处理输出结果...")
                        return await self._process_outputs(
                            prompt_history['outputs'], workflow_json
                        )
                
                # 等待 - 使用同步sleep
                import time
                time.sleep(check_interval)
                waited_time += check_interval
                
            except Exception as e:
                logger.error(f"检查任务状态时出错: {e}")
                return [f"ERROR: 检查状态失败: {str(e)}"]
        
        logger.error(f"任务 {prompt_id} 超时")
        return ["ERROR: 任务超时"]
    
    async def _process_outputs(self, outputs: Dict, workflow_json: Dict) -> List[str]:
        """处理ComfyUI输出"""
        logger.info("开始处理ComfyUI输出结果")
        
        # 查找SaveImage节点
        save_image_node_ids = []
        for node_id, node_details in workflow_json.items():
            if node_details.get("class_type") == "SaveImage":
                save_image_node_ids.append(str(node_id))
        
        if not save_image_node_ids:
            return ["ERROR: 工作流中没有SaveImage节点"]
        
        # 处理输出
        output_images = []
        for output_node_id, node_output_data in outputs.items():
            if str(output_node_id) in save_image_node_ids:
                if 'images' in node_output_data:
                    for image_info in node_output_data['images']:
                        if 'filename' in image_info:
                            subfolder = image_info.get('subfolder', '').strip('\\/')
                            filename = image_info['filename']
                            
                            if subfolder:
                                image_path = f"{subfolder}/{filename}"
                            else:
                                image_path = filename
                            
                            output_images.append(image_path)
        
        if not output_images:
            return ["ERROR: 未生成任何图片"]
        
        # 下载图片到本地
        downloaded_paths = []
        for image_path in output_images:
            downloaded_path = await self._download_image_to_local(image_path)
            if downloaded_path:
                downloaded_paths.append(downloaded_path)
            else:
                downloaded_paths.append(f"ERROR: 下载失败: {image_path}")
        
        return downloaded_paths
    
    async def _download_image_to_local(self, image_path: str) -> Optional[str]:
        """下载图片到本地"""
        try:
            # 构建下载URL
            download_url = f"{self.api_url}/view"
            params = {'filename': image_path}
            
            # 使用代理绕过工具下载
            from src.utils.proxy_bypass import proxy_bypass

            response = proxy_bypass.requests_get(
                download_url,
                bypass_proxy=True,
                params=params,
                timeout=60
            )
            if response.status_code == 200:
                # 生成本地文件名
                # 使用简洁的文件名，不包含时间戳
                filename = f"comfyui_{os.path.basename(image_path)}"
                # 使用当前的输出目录（可能已更新为项目目录）
                current_output_dir = self._get_output_dir(self.project_manager, self.current_project_name)
                local_path = os.path.join(current_output_dir, filename)

                # 保存文件
                with open(local_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"图片已下载: {local_path}")
                return local_path
            else:
                logger.error(f"下载图片失败: HTTP {response.status_code}")
                return None
                    
        except Exception as e:
            logger.error(f"下载图片异常: {e}")
            return None
    
    def _calculate_cost(self, config: GenerationConfig) -> float:
        """计算生成成本（云端服务）"""
        # 基础成本计算，可根据实际云服务定价调整
        base_cost = 0.05  # 每张图片基础成本
        size_multiplier = (config.width * config.height) / (1024 * 1024)  # 尺寸倍数
        steps_multiplier = config.steps / 20  # 步数倍数
        
        return base_cost * size_multiplier * steps_multiplier * config.batch_size
    
    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        # 这里应该从ComfyUI API获取，暂时返回常见模型
        return [
            'sd_xl_base_1.0.safetensors',
            'sd_xl_refiner_1.0.safetensors',
            'v1-5-pruned-emaonly.ckpt',
            'dreamshaper_8.safetensors'
        ]
    
    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()
            self.session = None
        
        self.status = EngineStatus.OFFLINE
        await super().cleanup()


class ComfyUILocalEngine(ComfyUIBaseEngine):
    """本地ComfyUI引擎"""
    
    def __init__(self, config: Dict = None):
        super().__init__(EngineType.COMFYUI_LOCAL, config)
        # 默认本地地址
        if 'api_url' not in self.config:
            self.api_url = 'http://127.0.0.1:8188'
    
    def get_engine_info(self) -> EngineInfo:
        """获取引擎信息"""
        return EngineInfo(
            name="ComfyUI Local",
            version="1.0",
            description="本地ComfyUI服务，支持自定义工作流和模型",
            is_free=True,
            supports_batch=True,
            supports_custom_models=True,
            max_batch_size=10,
            supported_sizes=[
                (512, 512), (768, 768), (1024, 1024),
                (1024, 768), (768, 1024),
                (1280, 720), (720, 1280),
                (1536, 1024), (1024, 1536)
            ],
            cost_per_image=0.0,
            rate_limit=0  # 本地无限制
        )


class ComfyUICloudEngine(ComfyUIBaseEngine):
    """云端ComfyUI引擎"""
    
    def __init__(self, config: Dict = None):
        super().__init__(EngineType.COMFYUI_CLOUD, config)
        # 云端服务需要API密钥
        self.api_key = self.config.get('api_key')
        if not self.api_key:
            logger.warning("ComfyUI云端服务未配置API密钥")
    
    async def initialize(self) -> bool:
        """初始化云端引擎"""
        if not self.api_key:
            self.status = EngineStatus.ERROR
            self.last_error = "缺少API密钥"
            return False
        
        return await super().initialize()
    
    def get_engine_info(self) -> EngineInfo:
        """获取引擎信息"""
        return EngineInfo(
            name="ComfyUI Cloud",
            version="1.0",
            description="云端ComfyUI服务，高性能GPU加速",
            is_free=False,
            supports_batch=True,
            supports_custom_models=True,
            max_batch_size=5,
            supported_sizes=[
                (512, 512), (768, 768), (1024, 1024),
                (1024, 768), (768, 1024),
                (1280, 720), (720, 1280),
                (1536, 1024), (1024, 1536)
            ],
            cost_per_image=0.05,
            rate_limit=100  # 每分钟100次
        )