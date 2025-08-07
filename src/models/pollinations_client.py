# -*- coding: utf-8 -*-
"""
Pollinations AI 客户端
- 提供免费的文生图API接口
- 支持图像和视频生成
- 无需API密钥，完全免费使用
"""
import requests
from typing import Any, List, Dict, Optional
import uuid
import os
import time
from urllib.parse import quote
from src.utils.logger import logger
from src.core.project_manager import ProjectManager

class PollinationsClient:
    """Pollinations AI 客户端类"""
    
    def __init__(self) -> None:
        self.base_url = "https://image.pollinations.ai"
        self.text_url = "https://text.pollinations.ai"
        self.session = requests.Session()
        
        # 配置会话以处理SSL连接问题
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        import urllib3
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
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
            'Connection': 'keep-alive',
        })
        
        # 禁用SSL警告（如果需要的话）
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        logger.info("Pollinations AI 客户端初始化完成")

    def __del__(self) -> None:
        """析构函数，确保会话正确关闭"""
        if hasattr(self, 'session'):
            self.session.close()

    def generate_image(self, prompt: str, **kwargs: Any) -> List[str]:
        """生成单张图片
        
        Args:
            prompt: 图片描述提示词
            **kwargs: 可选参数
                - width: 图片宽度 (默认: 512)
                - height: 图片高度 (默认: 1024)
                - seed: 随机种子 (可选)
                - model: 模型名称 (可选)
                - nologo: 是否去除水印 (默认: True)
                - project_manager: 项目管理器实例 (可选, 从kwargs获取)
                - current_project_name: 当前项目名称 (可选, 从kwargs获取)
        
        Returns:
            生成的图片路径列表
        """
        logger.info(f"=== Pollinations AI 图片生成开始 ===")
        logger.info(f"提示词: {prompt}")
        logger.info(f"原始传入参数 (kwargs): {kwargs}") # MODIFIED Log

        project_manager = kwargs.pop('project_manager', None)
        current_project_name = kwargs.pop('current_project_name', None)
        logger.info(f"API相关参数 (kwargs after pop): {kwargs}") # ADDED Log
        
        # --- MODIFIED PARAMETER PREPARATION BLOCK START ---
        # Define application-level defaults for API parameters (only Pollinations supported params)
        api_params_defaults: Dict[str, Any] = {
            'width': 512,
            'height': 1024,
            'nologo': True,
            'enhance': False,
            'safe': True
        }

        # Start with defaults
        params_dict: Dict[str, Any] = api_params_defaults.copy()

        # Override defaults with any relevant parameters from kwargs (which are after pop)
        # Only include parameters that Pollinations API actually supports
        supported_params = ['width', 'height', 'seed', 'model', 'nologo', 'enhance', 'safe', 'private']

        for key_from_ui in supported_params:
            if key_from_ui in kwargs: # Check if the key exists in UI-provided params
                if kwargs[key_from_ui] is not None:
                    params_dict[key_from_ui] = kwargs[key_from_ui]
                else:
                    # If UI sends None for a parameter, remove it from params_dict
                    # so it's not sent to the API if it was a default.
                    if key_from_ui in params_dict:
                        del params_dict[key_from_ui]

        # Ensure boolean values are lowercase strings for the API URL
        for bool_key in ['nologo', 'enhance', 'safe', 'private']:
            if bool_key in params_dict and isinstance(params_dict[bool_key], bool):
                params_dict[bool_key] = str(params_dict[bool_key]).lower()

        # Remove any remaining None values from params_dict before sending to API
        params_dict = {k: v for k, v in params_dict.items() if v is not None}

        # 过滤掉不支持的参数（如果有的话）
        unsupported_params: List[str] = ['negative_prompt', 'steps', 'cfg_scale', 'sampler', 'batch_size', 'guidance_scale', 'api_key', 'base_url', 'workflow_id']
        for param in unsupported_params:
            if param in kwargs:
                logger.debug(f"移除不支持的参数: {param} = {kwargs[param]}")

        logger.debug(f"最终构建的API参数 (params_dict): {params_dict}")
        # --- MODIFIED PARAMETER PREPARATION BLOCK END ---

        try:
            # --- URL Construction Block ---
            # 将prompt添加到参数字典中，以便统一处理
            params_dict['prompt'] = prompt
            
            # 构建基础URL
            api_url = f"{self.base_url}/prompt"
            
            # 构建URL参数
            url_params: List[str] = []
            for key, value in params_dict.items():
                if value is not None:
                    encoded_value = quote(str(value), safe='')
                    url_params.append(f"{key}={encoded_value}")

            if url_params:
                api_url += "?" + "&".join(url_params)
            # --- End of URL Construction Block ---
            
            logger.info(f"API请求URL: {api_url}")
            
            # 发送请求
            response = self.session.get(api_url, timeout=60)
            
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应头: {dict(response.headers)}")
            
            if response.status_code != 200:
                logger.error(f"API请求失败: HTTP {response.status_code}")
                try:
                    error_content = response.text[:500]
                    logger.error(f"错误响应: {error_content}")
                except:
                    pass
                return [f"ERROR: HTTP {response.status_code}"]
            
            # 检查响应内容类型
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"响应内容类型不是图像: {content_type}")
                try:
                    error_text = response.text[:500]
                    logger.error(f"响应内容: {error_text}")
                except:
                    pass
                return [f"ERROR: 响应不是图像格式"]
            
            # 保存图片
            output_dir = self._get_output_dir(project_manager, current_project_name)
            # 使用时间戳确保文件名唯一
            timestamp = int(time.time())
            filename = f"pollinations_{uuid.uuid4().hex[:8]}_{timestamp}.png"
            output_path = os.path.join(output_dir, filename)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            # 验证文件是否成功保存
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"图片生成成功: {output_path} (大小: {os.path.getsize(output_path)} 字节)")
                return [output_path]
            else:
                logger.error(f"图片文件保存失败或文件为空: {output_path}")
                return [f"ERROR: 文件保存失败"]
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Pollinations API 请求失败: {str(e)}"
            logger.error(error_msg)
            return [f"ERROR: {error_msg}"]
        except Exception as e:
            error_msg = f"图片生成过程中发生错误: {str(e)}"
            logger.error(error_msg)
            return [f"ERROR: {error_msg}"]
    
    def generate_images(self, shots: List[Dict[str, Any]], project_manager: Optional[ProjectManager] = None, current_project_name: Optional[str] = None) -> List[str]:
        """批量生成图片
        
        Args:
            shots: 分镜列表，每个元素包含描述信息
            project_manager: 项目管理器
            current_project_name: 当前项目名称
        
        Returns:
            生成的图片路径列表
        """
        logger.info(f"开始批量生成 {len(shots)} 张图片")
        image_paths: List[str] = []
        
        for i, shot in enumerate(shots):
            try:
                # 获取分镜描述
                prompt = shot.get('description', shot.get('prompt', ''))
                if not prompt:
                    logger.warning(f"第 {i+1} 个分镜缺少描述信息")
                    image_paths.append("ERROR: 缺少描述信息")
                    continue
                
                logger.info(f"生成第 {i+1}/{len(shots)} 张图片")
                
                # 生成图片
                result = self.generate_image(prompt, project_manager=project_manager, current_project_name=current_project_name)
                image_paths.extend(result)
                
                # 添加延迟避免请求过快
                if i < len(shots) - 1:
                    time.sleep(1)
                    
            except Exception as e:
                error_msg = f"生成第 {i+1} 张图片时发生错误: {str(e)}"
                logger.error(error_msg)
                image_paths.append(f"ERROR: {error_msg}")
        
        logger.info(f"批量生成完成，成功: {len([p for p in image_paths if not p.startswith('ERROR')])}/{len(shots)}")
        return image_paths
    
    def generate_video_from_image(self, image_path: str, **kwargs: Any) -> str:
        """从图片生成视频（图生视频）
        
        Args:
            image_path: 输入图片路径
            **kwargs: 可选参数
                - model: 视频生成模型 (stable-diffusion-animation 或 photo3d)
                - frames: 帧数 (默认: 16)
                - fps: 帧率 (默认: 8)
        
        Returns:
            生成的视频路径
        """
        logger.info(f"=== Pollinations AI 图生视频开始 ===")
        logger.info(f"输入图片: {image_path}")
        logger.info(f"参数: {kwargs}")
        
        try:
            # 注意：Pollinations AI 的视频生成功能可能需要特殊的API端点
            # 这里提供基础框架，具体实现需要根据官方文档调整
            model = kwargs.get('model', 'stable-diffusion-animation')
            frames = kwargs.get('frames', 16)
            fps = kwargs.get('fps', 8)
            
            # 读取图片文件
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 构建视频生成请求
            # 注意：这是示例代码，实际API可能不同
            video_url = f"{self.base_url}/video"
            
            files = {'image': image_data}
            data = {
                'model': model,
                'frames': frames,
                'fps': fps
            }
            
            response: requests.Response = self.session.post(video_url, files=files, data=data, timeout=120)
            
            if response.status_code == 200:
                # 保存视频
                output_dir = self._get_output_dir()
                # 使用简洁的文件名，不包含时间戳
                filename = f"pollinations_video_{uuid.uuid4().hex[:8]}.mp4"
                output_path = os.path.join(output_dir, filename)
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"视频生成成功: {output_path}")
                return output_path
            else:
                error_msg = f"视频生成失败: HTTP {response.status_code}"
                logger.error(error_msg)
                return f"ERROR: {error_msg}"
                
        except Exception as e:
            error_msg = f"图生视频过程中发生错误: {str(e)}"
            logger.error(error_msg)
            return f"ERROR: {error_msg}"
    
    def get_available_models(self) -> List[str]:
        """获取可用的模型列表
        
        Returns:
            模型名称列表
        """
        # 根据Pollinations官网实际可用模型更新
        return [
            'flux',           # 默认模型，高质量
            'turbo',          # 快速生成
            'flux-realism'    # 写实风格
        ]
    
    def _get_output_dir(self, project_manager: Optional[ProjectManager] = None, current_project_name: Optional[str] = None) -> str:
        """获取输出目录"""
        # 如果有项目管理器和当前项目，保存到项目的images/pollinations文件夹
        if project_manager and current_project_name:
            try:
                project_root = project_manager.get_project_path(current_project_name)
                output_dir = os.path.join(project_root, 'images', 'pollinations')
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"使用项目图片目录: {output_dir}")
                return output_dir
            except Exception as e:
                logger.warning(f"无法使用项目目录: {e}")
        
        # 如果没有项目管理器或项目名称，抛出异常
        raise ValueError("必须提供项目管理器和项目名称才能生成图片")
    
    def test_connection(self) -> bool:
        """测试连接
        
        Returns:
            连接是否成功
        """
        try:
            # 测试简单的图片生成 - 使用正确的API格式
            test_prompt = "test"
            test_url = f"{self.base_url}/prompt/{test_prompt}?width=64&height=64&nologo=true"
            
            logger.info(f"测试连接URL: {test_url}")
            
            # 尝试多种方式连接
            response: Optional[requests.Response] = None
            
            # 方法1：正常连接
            try:
                response = self.session.get(test_url, timeout=15, verify=True)
            except Exception as ssl_error:
                logger.warning(f"SSL连接失败，尝试不验证SSL: {ssl_error}")
                # 方法2：不验证SSL证书
                try:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    response = self.session.get(test_url, timeout=15, verify=False)
                    # 如果成功，更新会话配置
                    self.session.verify = False
                    logger.info("使用不验证SSL的方式连接成功")
                except Exception as e2:
                    logger.error(f"不验证SSL也失败: {e2}")
                    return False
            
            if response:
                logger.info(f"连接测试响应: {response.status_code}")
                
                if response.status_code == 200:
                    # 检查响应内容类型
                    content_type = response.headers.get('content-type', '')
                    is_image = content_type.startswith('image/')
                    logger.info(f"Pollinations AI 连接测试: {'成功' if is_image else '失败'} (内容类型: {content_type})")
                    return is_image
                else:
                    logger.warning(f"Pollinations AI 连接测试失败: HTTP {response.status_code}")
                    return False
            else:
                logger.error("无法获取响应")
                return False
                
        except Exception as e:
            logger.error(f"连接测试失败: {str(e)}")
            return False
