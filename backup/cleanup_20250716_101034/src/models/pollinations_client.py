# -*- coding: utf-8 -*-
"""
Pollinations AI 客户端
- 提供免费的文生图API接口
- 支持图像和视频生成
- 无需API密钥，完全免费使用
"""
import requests
from typing import List, Dict, Optional, Union
import uuid
import os
import time
from urllib.parse import quote
from src.utils.logger import logger

class PollinationsClient:
    """Pollinations AI 客户端类"""
    
    def __init__(self):
        self.base_url = "https://image.pollinations.ai"
        self.text_url = "https://text.pollinations.ai"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Video-Generator/1.0'
        })
        logger.info("Pollinations AI 客户端初始化完成")

    def __del__(self):
        """析构函数，确保会话正确关闭"""
        if hasattr(self, 'session'):
            self.session.close()

    def generate_image(self, prompt: str, **kwargs) -> List[str]:
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
        api_params_defaults = {
            'width': 512,
            'height': 1024,
            'nologo': True,
            'enhance': False,
            'safe': True
        }

        # Start with defaults
        params_dict = api_params_defaults.copy()

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
        unsupported_params = ['negative_prompt', 'steps', 'cfg_scale', 'sampler', 'batch_size', 'guidance_scale', 'api_key', 'base_url', 'workflow_id']
        for param in unsupported_params:
            if param in kwargs:
                logger.debug(f"移除不支持的参数: {param} = {kwargs[param]}")

        logger.debug(f"最终构建的API参数 (params_dict): {params_dict}")
        # --- MODIFIED PARAMETER PREPARATION BLOCK END ---

        try:
            # 构建API URL
            encoded_prompt = quote(prompt)
            api_url = f"{self.base_url}/prompt/{encoded_prompt}"
            
            # 添加参数 (The existing logic below should work with the refined params_dict)
            api_params_list = []

            url_params = []
            for key, value in params_dict.items():
                if value is not None: # 确保参数值不为None
                    # 对于布尔值，转换为小写字符串 'true' 或 'false'
                    if isinstance(value, bool):
                        url_params.append(f"{key}={str(value).lower()}")
                    else:
                        url_params.append(f"{key}={value}")
            
            if url_params:
                api_url += "?" + "&".join(url_params)
            
            logger.info(f"API请求URL: {api_url}")
            
            # 发送请求
            response = self.session.get(api_url, timeout=60)
            response.raise_for_status()
            
            # 保存图片
            output_dir = self._get_output_dir(project_manager, current_project_name)
            # 使用简洁的文件名，不包含时间戳
            filename = f"pollinations_{uuid.uuid4().hex[:8]}.png"
            output_path = os.path.join(output_dir, filename)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"图片生成成功: {output_path}")
            return [output_path]
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Pollinations API 请求失败: {str(e)}"
            logger.error(error_msg)
            return [f"ERROR: {error_msg}"]
        except Exception as e:
            error_msg = f"图片生成过程中发生错误: {str(e)}"
            logger.error(error_msg)
            return [f"ERROR: {error_msg}"]
    
    def generate_images(self, shots: List[dict], project_manager=None, current_project_name=None) -> List[str]:
        """批量生成图片
        
        Args:
            shots: 分镜列表，每个元素包含描述信息
            project_manager: 项目管理器
            current_project_name: 当前项目名称
        
        Returns:
            生成的图片路径列表
        """
        logger.info(f"开始批量生成 {len(shots)} 张图片")
        image_paths = []
        
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
                result = self.generate_image(prompt, project_manager, current_project_name)
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
    
    def generate_video_from_image(self, image_path: str, **kwargs) -> str:
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
            
            response = self.session.post(video_url, files=files, data=data, timeout=120)
            
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
        try:
            response = self.session.get(f"{self.base_url}/models", timeout=10)
            if response.status_code == 200:
                models = response.json()
                logger.info(f"获取到 {len(models)} 个可用模型")
                return models
            else:
                logger.warning("无法获取模型列表，使用默认模型")
                return ['flux', 'stable-diffusion', 'dall-e']
        except Exception as e:
            logger.error(f"获取模型列表失败: {str(e)}")
            return ['flux', 'stable-diffusion', 'dall-e']
    
    def _get_output_dir(self, project_manager=None, current_project_name=None) -> str:
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
            # 测试简单的图片生成
            test_url = f"{self.base_url}/prompt/test?width=64&height=64&nologo=true"
            response = self.session.get(test_url, timeout=10)
            success = response.status_code == 200
            logger.info(f"Pollinations AI 连接测试: {'成功' if success else '失败'}")
            return success
        except Exception as e:
            logger.error(f"连接测试失败: {str(e)}")
            return False