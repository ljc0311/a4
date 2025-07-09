"""ComfyUI 客户端模块
- 接收分镜描述，调用 ComfyUI API 生成图片
- 支持多种工作流配置
"""
import requests
from typing import List, Dict, Optional
import uuid
from src.utils.logger import logger
from src.models.llm_api import LLMApi
from src.models.workflow_manager import WorkflowManager
from src.utils.baidu_translator import translate_text, is_configured as is_baidu_configured
import json
import time
import random
import os

class ComfyUIClient:
    def __init__(self, api_url: str, llm_api: LLMApi = None, workflows_dir: str = None):
        self.api_url = api_url.rstrip('/')
        self.client_id = str(uuid.uuid4()) # Initialize client_id
        self.llm_api = llm_api
        self.project_manager = None
        self.current_project_name = None
        
        # 初始化工作流管理器
        if workflows_dir is None:
            # 默认工作流目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            workflows_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'config', 'workflows')
        
        self.workflow_manager = WorkflowManager(workflows_dir)
        logger.info(f"ComfyUI客户端初始化完成，工作流目录: {workflows_dir}")
    
    def generate_image_with_workflow(self, prompt: str, workflow_id: str = None, parameters: Dict = None, project_manager=None, current_project_name=None) -> List[str]:
        """使用指定工作流生成单张图片
        
        Args:
            prompt: 图片描述提示词
            workflow_id: 工作流ID，如果为None则使用当前工作流
            parameters: 工作流参数，如steps、cfg等
        
        Returns:
            生成的图片路径列表
        """
        import traceback
        
        logger.info(f"=== ComfyUI图片生成开始 ===")
        logger.info(f"工作流ID: {workflow_id}")
        logger.info(f"原始提示词: {prompt}")
        logger.info(f"参数: {parameters}")
        
        # 设置项目管理器参数
        self.project_manager = project_manager
        self.current_project_name = current_project_name
        
        try:
            # 设置工作流
            if workflow_id:
                logger.debug(f"设置工作流: {workflow_id}")
                try:
                    if not self.workflow_manager.set_current_workflow(workflow_id):
                        logger.error(f"工作流不存在: {workflow_id}")
                        return ["ERROR: 工作流不存在"]
                    logger.debug(f"工作流设置成功: {workflow_id}")
                except Exception as e:
                    logger.error(f"设置工作流时发生异常: {e}")
                    logger.error(f"设置工作流异常堆栈: {traceback.format_exc()}")
                    return [f"ERROR: 设置工作流失败: {str(e)}"]
            else:
                logger.debug("使用当前工作流")
            
            # 翻译提示词（如果需要）
            logger.debug("开始翻译提示词")
            try:
                translated_prompt = self._translate_prompt(prompt)
                logger.info(f"提示词翻译完成: {translated_prompt}")
            except Exception as e:
                logger.error(f"翻译提示词时发生异常: {e}")
                logger.error(f"翻译提示词异常堆栈: {traceback.format_exc()}")
                # 翻译失败时使用原始提示词
                translated_prompt = prompt
                logger.warning(f"翻译失败，使用原始提示词: {translated_prompt}")
            
            # 生成工作流JSON
            logger.debug("开始生成工作流JSON")
            try:
                workflow_json = self.workflow_manager.generate_workflow_json(translated_prompt, parameters)
                logger.debug(f"工作流JSON生成完成，节点数量: {len(workflow_json) if workflow_json else 0}")
                if not workflow_json:
                    logger.error("工作流JSON生成失败，返回空结果")
                    return ["ERROR: 工作流JSON生成失败"]
            except Exception as e:
                logger.error(f"生成工作流JSON时发生异常: {e}")
                logger.error(f"生成工作流JSON异常堆栈: {traceback.format_exc()}")
                return [f"ERROR: 生成工作流JSON失败: {str(e)}"]
            
            # 调用ComfyUI API
            logger.info("开始执行ComfyUI工作流")
            try:
                result = self._execute_workflow(workflow_json)
                logger.info(f"ComfyUI工作流执行完成，结果数量: {len(result) if isinstance(result, list) else 'N/A'}")
                logger.debug(f"ComfyUI工作流执行结果详情: {result}")
                return result
            except Exception as e:
                logger.error(f"执行ComfyUI工作流时发生异常: {e}")
                logger.error(f"执行工作流异常堆栈: {traceback.format_exc()}")
                return [f"ERROR: 执行工作流失败: {str(e)}"]
            
        except Exception as e:
            logger.critical(f"ComfyUI图片生成过程中发生严重错误: {e}")
            logger.critical(f"错误类型: {type(e).__name__}")
            logger.critical(f"错误堆栈: {traceback.format_exc()}")
            return [f"ERROR: 严重错误: {str(e)}"]
        finally:
            logger.info(f"=== ComfyUI图片生成结束 ===")
            # 强制刷新日志
            logger.flush()
    
    def get_workflow_list(self):
        """获取可用的工作流列表"""
        return self.workflow_manager.get_workflow_list()
    
    def get_workflow_parameters(self, workflow_id: str = None):
        """获取工作流参数配置"""
        return self.workflow_manager.get_workflow_parameters(workflow_id)
    
    def set_current_workflow(self, workflow_id: str):
        """设置当前工作流"""
        return self.workflow_manager.set_current_workflow(workflow_id)
    
    def _execute_workflow(self, workflow_json: Dict) -> List[str]:
        """执行工作流并返回图片路径"""
        logger.info(f"开始执行工作流，客户端ID: {self.client_id}")
        request_payload = {"prompt": workflow_json, "client_id": self.client_id}
        
        # Step 1: Submit the prompt to ComfyUI and get prompt_id
        logger.debug(f"向ComfyUI提交任务: {self.api_url}/prompt")
        try:
            resp = requests.post(f"{self.api_url}/prompt", json=request_payload, timeout=60, proxies={"http": None, "https": None})
            logger.debug(f"ComfyUI响应状态码: {resp.status_code}")
            resp.raise_for_status()
            prompt_response = resp.json()
            logger.debug(f"ComfyUI任务提交响应: {prompt_response}")
        except requests.exceptions.RequestException as e:
            logger.error(f"向ComfyUI提交任务失败: {e}")
            return [f"ERROR: 提交任务失败: {str(e)}"]
        
        if 'prompt_id' not in prompt_response:
            logger.error(f"ComfyUI响应中没有prompt_id: {prompt_response}")
            return ["ERROR: ComfyUI未返回prompt_id"]
            
        prompt_id = prompt_response['prompt_id']
        logger.info(f"ComfyUI任务已加入队列，prompt_id: {prompt_id}")
        
        # Step 2: Wait for the task to complete and get results from history
        logger.debug(f"开始等待任务完成: {prompt_id}")
        return self._wait_for_completion(prompt_id, workflow_json)
    
    def _wait_for_completion(self, prompt_id: str, workflow_json: Dict) -> List[str]:
        """等待任务完成并获取结果"""
        max_wait_time = 120  # Maximum wait time in seconds
        check_interval = 2   # Check every 2 seconds
        waited_time = 0
        
        logger.info(f"开始等待任务完成，最大等待时间: {max_wait_time}秒")
        
        while waited_time < max_wait_time:
            try:
                # Get history for this prompt_id
                logger.debug(f"检查任务状态，已等待: {waited_time}秒")
                history_resp = requests.get(f"{self.api_url}/history/{prompt_id}", timeout=30, proxies={"http": None, "https": None})
                history_resp.raise_for_status()
                history_data = history_resp.json()
                logger.debug(f"获取到历史记录，prompt_id: {prompt_id}")
                
                # Check if our prompt_id exists in history and has outputs
                if prompt_id in history_data:
                    logger.debug(f"找到任务记录: {prompt_id}")
                    prompt_history = history_data[prompt_id]
                    if 'outputs' in prompt_history:
                        logger.info(f"任务 {prompt_id} 已完成，开始处理输出结果")
                        outputs = prompt_history['outputs']
                        logger.debug(f"输出节点数量: {len(outputs)}")
                        return self._process_outputs(outputs, workflow_json)
                    else:
                        logger.debug(f"任务 {prompt_id} 还在执行中，未找到输出结果")
                else:
                    logger.debug(f"任务 {prompt_id} 尚未在历史记录中找到")
                
                # Wait before next check
                time.sleep(check_interval)
                waited_time += check_interval
                logger.debug(f"等待任务完成中... {waited_time}/{max_wait_time}秒")
                
            except Exception as e:
                logger.error(f"检查任务状态时出错: {e}")
                return [f"ERROR: {str(e)}"]
        
        logger.error(f"任务 {prompt_id} 在 {max_wait_time} 秒后超时")
        return ["ERROR: 任务超时"]
    
    def _process_outputs(self, outputs: Dict, workflow_json: Dict) -> List[str]:
        """处理ComfyUI输出，提取图片路径并下载到本地"""
        logger.info("开始处理ComfyUI输出结果")
        
        # Dynamically find SaveImage node IDs from the workflow_json we sent
        save_image_node_ids_from_workflow = []
        for node_id_in_workflow, node_details_in_workflow in workflow_json.items():
            if node_details_in_workflow.get("class_type") == "SaveImage":
                save_image_node_ids_from_workflow.append(str(node_id_in_workflow))
        
        logger.debug(f"工作流中的SaveImage节点ID: {save_image_node_ids_from_workflow}")
        
        if not save_image_node_ids_from_workflow:
            logger.error("工作流定义中未找到SaveImage节点")
            return ["ERROR: 工作流定义中没有SaveImage节点"]
        
        # Process outputs to find images
        output_images = []
        logger.debug(f"ComfyUI完整输出数据: {outputs}")
        logger.debug(f"输出节点数量: {len(outputs)}")
        
        for output_node_id, node_output_data in outputs.items():
            logger.debug(f"检查输出节点 {output_node_id}")
            if str(output_node_id) in save_image_node_ids_from_workflow:
                logger.info(f"处理SaveImage节点输出，节点ID: {output_node_id}")
                logger.debug(f"节点输出数据: {node_output_data}")
                if 'images' in node_output_data:
                    images_count = len(node_output_data['images'])
                    logger.debug(f"节点 {output_node_id} 包含 {images_count} 张图片")
                    for i, image_info in enumerate(node_output_data['images']):
                        logger.debug(f"处理第 {i+1} 张图片信息: {image_info}")
                        if 'filename' in image_info:
                            subfolder = image_info.get('subfolder', '').strip('\\/')
                            filename = image_info['filename']
                            logger.debug(f"图片文件名: {filename}, 子文件夹: {subfolder}")
                            
                            # 构建完整的图片路径
                            if subfolder:
                                image_path = f"{subfolder}/{filename}"
                            else:
                                image_path = filename
                            
                            output_images.append(image_path)
                            logger.info(f"找到生成的图片: {image_path}")
                        else:
                            logger.warning(f"图片信息中缺少filename字段: {image_info}")
                else:
                    logger.warning(f"SaveImage节点 {output_node_id} 输出中没有images字段")
            else:
                logger.debug(f"跳过非SaveImage节点: {output_node_id}")
        
        logger.info(f"总共找到 {len(output_images)} 张生成的图片")
        
        if not output_images:
            logger.warning("ComfyUI输出中未找到任何图片")
            return ["ERROR: 未生成任何图片"]
        
        # 下载图片到本地项目目录
        downloaded_paths = []
        for image_path in output_images:
            downloaded_path = self._download_image_to_local(image_path)
            if downloaded_path:
                downloaded_paths.append(downloaded_path)
                logger.info(f"图片已下载到本地: {downloaded_path}")
            else:
                # 如果下载失败，返回错误信息
                logger.error(f"图片下载失败: {image_path}")
                downloaded_paths.append(f"ERROR: 下载失败: {image_path}")
        
        logger.info(f"返回本地图片路径列表: {downloaded_paths}")
        return downloaded_paths

    def generate_images(self, shots: List[dict], project_manager=None, current_project_name=None) -> List[str]:
        """
        输入分镜描述列表，返回图片路径列表
        shots: [{ 'scene': str, 'description': str, ... }, ...]
        project_manager: 项目管理器
        current_project_name: 当前项目名称
        """
        image_paths = []
        for shot in shots:
            try:
                # 默认的 ComfyUI 工作流 JSON 模板
                # 这是一个非常简化的示例，实际应用中需要根据 ComfyUI 导出的 API JSON 进行调整
                # 假设你的 ComfyUI 工作流中有一个名为 "CLIP_Text_Encode" 的节点，其输入是 "text"
                # 并且有一个名为 "KSampler" 的节点，其输入是 "positive" 和 "negative"
                # 实际的 node_id 和 input_name 需要根据你的 ComfyUI 工作流来确定
                workflow_json = {
                    "3": {
                        "inputs": {
                            "seed": random.randint(1, 2**32 - 1),
                            "steps": 20,
                            "cfg": 8,
                            "sampler_name": "euler",
                            "scheduler": "normal",
                            "denoise": 1,
                            "model": [
                                "4",
                                0
                            ],
                            "positive": [
                                "6",
                                0
                            ],
                            "negative": [
                                "7",
                                0
                            ],
                            "latent_image": [
                                "5",
                                0
                            ]
                        },
                        "class_type": "KSampler",
                        "_meta": {
                            "title": "K采样器"
                        }
                    },
                    "4": {
                        "inputs": {
                            "ckpt_name": "SD1.5\\SD1.5克隆万能大模型.safetensors"
                        },
                        "class_type": "CheckpointLoaderSimple",
                        "_meta": {
                            "title": "Checkpoint加载器(简易)"
                        }
                    },
                    "5": {
                        "inputs": {
                            "width": 512,
                            "height": 512,
                            "batch_size": 1
                        },
                        "class_type": "EmptyLatentImage",
                        "_meta": {
                            "title": "空Latent"
                        }
                    },
                    "6": {
                        "inputs": {
                            "text": self._translate_prompt(shot['description']),  # Translate prompt to English
                            "clip": [
                                "4",
                                1
                            ]
                        },
                        "class_type": "CLIPTextEncode",
                        "_meta": {
                            "title": "CLIP文本编码（提示词）"
                        }
                    },
                    "7": {
                        "inputs": {
                            "text": "text, watermark", # 设置一个通用的负面提示
                            "clip": [
                                "4",
                                1
                            ]
                        },
                        "class_type": "CLIPTextEncode",
                        "_meta": {
                            "title": "CLIP文本编码器"
                        }
                    },
                    "8": {
                        "inputs": {
                            "samples": [
                                "3",
                                0
                            ],
                            "vae": [
                                "4",
                                2
                            ]
                        },
                        "class_type": "VAEDecode",
                        "_meta": {
                            "title": "VAE解码"
                        }
                    },
                    "9": {
                        "inputs": {
                            "filename_prefix": "ComfyUI",
                            "images": [
                                "8",
                                0
                            ]
                        },
                        "class_type": "SaveImage",
                        "_meta": {
                            "title": "保存图像"
                        }
                    }
                }
                # 将整个 workflow_json 作为 'prompt' 键的值
                request_payload = {"prompt": workflow_json, "client_id": self.client_id}
                # Step 1: Submit the prompt to ComfyUI and get prompt_id
                logger.debug(f"Sending prompt to ComfyUI: {self.api_url}/prompt")
                resp = requests.post(f"{self.api_url}/prompt", json=request_payload, timeout=60, proxies={"http": None, "https": None})
                logger.debug(f"ComfyUI response status: {resp.status_code}")
                resp.raise_for_status()
                prompt_response = resp.json()
                logger.debug(f"ComfyUI prompt response: {prompt_response}")
                
                if 'prompt_id' not in prompt_response:
                    logger.error(f"No prompt_id in ComfyUI response: {prompt_response}")
                    image_paths.append("ERROR: No prompt_id returned from ComfyUI")
                    continue
                    
                prompt_id = prompt_response['prompt_id']
                logger.info(f"ComfyUI task queued with prompt_id: {prompt_id}")
                
                # Step 2: Wait for the task to complete and get results from history
                max_wait_time = 120  # Maximum wait time in seconds
                check_interval = 2   # Check every 2 seconds
                waited_time = 0
                
                while waited_time < max_wait_time:
                    try:
                        # Get history for this prompt_id
                        history_resp = requests.get(f"{self.api_url}/history/{prompt_id}", timeout=30, proxies={"http": None, "https": None})
                        history_resp.raise_for_status()
                        history_data = history_resp.json()
                        logger.debug(f"History response for {prompt_id}: {history_data}")
                        
                        # Check if our prompt_id exists in history and has outputs
                        if prompt_id in history_data:
                            prompt_history = history_data[prompt_id]
                            if 'outputs' in prompt_history:
                                logger.info(f"Task {prompt_id} completed, processing outputs")
                                
                                # Dynamically find SaveImage node IDs from the workflow_json we sent
                                save_image_node_ids_from_workflow = []
                                for node_id_in_workflow, node_details_in_workflow in workflow_json.items():
                                    if node_details_in_workflow.get("class_type") == "SaveImage":
                                        save_image_node_ids_from_workflow.append(str(node_id_in_workflow))
                                
                                if not save_image_node_ids_from_workflow:
                                    logger.error("No SaveImage node found in the defined workflow_json.")
                                    image_paths.append("ERROR: Workflow definition has no SaveImage node.")
                                    break
                                
                                # Process outputs to find images
                                output_images = []
                                outputs = prompt_history['outputs']
                                logger.debug(f"Full ComfyUI outputs data: {outputs}")
                                
                                for output_node_id, node_output_data in outputs.items():
                                    if str(output_node_id) in save_image_node_ids_from_workflow:
                                        logger.info(f"Processing SaveImage node output for ID {output_node_id}: {node_output_data}")
                                        if 'images' in node_output_data:
                                            for image_info in node_output_data['images']:
                                                if 'filename' in image_info:
                                                    subfolder = image_info.get('subfolder', '').strip('\/')
                                                    filename = image_info['filename']
                                                    # ComfyUI usually returns paths relative to its own output directory
                                                    # 使用os.path.join确保路径分隔符正确
                                                    constructed_path = os.path.join(subfolder, filename) if subfolder else filename
                                                    output_images.append(constructed_path)
                                                    logger.info(f"Found image path: {constructed_path} from node {output_node_id}")
                                                else:
                                                    logger.warning(f"Image info from node {output_node_id} missing 'filename': {image_info}")
                                        else:
                                            logger.warning(f"SaveImage node {output_node_id} output does not contain 'images' key: {node_output_data}")
                                    else:
                                        logger.debug(f"Skipping non-SaveImage or non-matching node ID {output_node_id}. Expected SaveImage IDs: {save_image_node_ids_from_workflow}")
                                
                                if output_images:
                                    # 下载图片到本地项目目录
                                    downloaded_path = self._download_image_to_local(output_images[0])
                                    if downloaded_path:
                                        image_paths.append(downloaded_path)
                                        logger.info(f"图片已下载到本地: {downloaded_path}")
                                    else:
                                        # 如果下载失败，返回原始路径
                                        image_paths.append(output_images[0])
                                        logger.warning(f"图片下载失败，返回原始路径: {output_images[0]}")
                                else:
                                    logger.warning("No output images successfully extracted from SaveImage nodes in ComfyUI response.")
                                    image_paths.append('')
                                break  # Task completed, exit the waiting loop
                            else:
                                logger.debug(f"Task {prompt_id} not yet completed, waiting...")
                        else:
                            logger.debug(f"Prompt {prompt_id} not found in history yet, waiting...")
                        
                        # Wait before next check
                        import time
                        time.sleep(check_interval)
                        waited_time += check_interval
                        
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Error checking history for {prompt_id}: {e}")
                        time.sleep(check_interval)
                        waited_time += check_interval
                
                if waited_time >= max_wait_time:
                    logger.error(f"Timeout waiting for ComfyUI task {prompt_id} to complete")
                    image_paths.append(f"ERROR: Timeout waiting for task {prompt_id}")

            except requests.exceptions.RequestException as e:
                logger.error(f"API Request failed: {e}")
                image_paths.append(f"ERROR: API Request failed: {e}")
            except KeyError as e:
                logger.error(f"Invalid API response structure. Missing key: {e}. Response: {data if 'data' in locals() else 'N/A'}")
                image_paths.append(f"ERROR: Invalid API response structure. Missing key: {e}.")
            except Exception as e:
                logger.error(f"An unexpected error occurred in generate_images: {e}", exc_info=True)
                image_paths.append(f"ERROR: {e}")
        return image_paths

    def _translate_prompt(self, chinese_prompt: str) -> str:
        """
        将中文提示词翻译为英文
        优先使用百度翻译，如果未配置或失败则使用LLM翻译，最后返回原始提示词
        """
        logger.debug(f"开始翻译提示词，原始长度: {len(chinese_prompt)}")
        logger.debug(f"原始提示词: {chinese_prompt}")
        
        # 优先使用百度翻译
        if is_baidu_configured():
            try:
                logger.debug("使用百度翻译API进行翻译")
                translated_result = translate_text(chinese_prompt, 'zh', 'en')
                
                if translated_result and translated_result.strip():
                    logger.info(f"百度翻译成功: {chinese_prompt[:50]}... -> {translated_result[:50]}...")
                    logger.debug(f"翻译后完整提示词: {translated_result}")
                    return translated_result
                else:
                    logger.warning("百度翻译返回空结果，尝试使用LLM翻译")
            except Exception as e:
                logger.error(f"百度翻译失败: {e}，尝试使用LLM翻译")
        else:
            logger.debug("百度翻译未配置，尝试使用LLM翻译")
        
        # 如果百度翻译失败或未配置，尝试使用LLM翻译
        if not self.llm_api:
            logger.warning("未配置LLM API，无法翻译提示词，使用原始中文提示词")
            return chinese_prompt
            
        try:
            logger.debug("构建LLM翻译提示")
            # 构建翻译提示
            translation_prompt = f"""
请将以下中文图像生成提示词翻译成英文，保持原意和细节描述：

{chinese_prompt}

要求：
1. 翻译要准确，保持原有的视觉描述细节
2. 适合用于AI图像生成（如Stable Diffusion）
3. 只返回翻译后的英文提示词，不要包含其他解释
4. 保持专业的图像生成提示词格式
5. 不要返回与提示词翻译无关的任何内容
"""
            
            messages = [
                {"role": "system", "content": "你是一个专业的翻译专家，擅长将中文图像生成提示词翻译成适合AI图像生成的英文提示词。请严格按照用户要求，只返回翻译后的英文提示词，不要添加任何解释或其他内容。"},
                {"role": "user", "content": translation_prompt}
            ]
            
            logger.debug(f"准备调用LLM API进行翻译，模型: {self.llm_api.rewrite_model_name}")
            
            # 调用LLM API进行翻译
            translated_result = self.llm_api._make_api_call(
                self.llm_api.rewrite_model_name, 
                messages, 
                "translate_prompt"
            )
            
            logger.debug(f"LLM API翻译响应: {translated_result}")
            
            if isinstance(translated_result, str) and translated_result.strip():
                # 清理翻译结果，移除可能的引号和多余空白
                translated_prompt = translated_result.strip().strip('"').strip("'")
                logger.info(f"LLM翻译成功: {chinese_prompt[:50]}... -> {translated_prompt[:50]}...")
                logger.debug(f"翻译后完整提示词: {translated_prompt}")
                return translated_prompt
            else:
                logger.warning(f"LLM翻译失败，返回无效结果: {translated_result}")
                logger.info("尝试使用百度翻译作为备用方案")
                
                # 尝试使用百度翻译
                if is_baidu_configured():
                    try:
                        baidu_result = translate_text(chinese_prompt, 'zh', 'en')
                        if baidu_result and baidu_result.strip():
                            logger.info(f"百度翻译成功: {chinese_prompt[:50]}... -> {baidu_result[:50]}...")
                            logger.debug(f"百度翻译完整提示词: {baidu_result}")
                            return baidu_result
                        else:
                            logger.warning("百度翻译也失败了")
                    except Exception as baidu_e:
                        logger.error(f"百度翻译出错: {baidu_e}")
                else:
                    logger.warning("百度翻译未配置")
                
                logger.warning("所有翻译方案都失败，使用原始中文提示词")
                return chinese_prompt
                
        except Exception as e:
            logger.error(f"LLM翻译提示词时发生错误: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误详情: {str(e)}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            logger.info("LLM翻译异常，尝试使用百度翻译作为备用方案")
            
            # 尝试使用百度翻译
            if is_baidu_configured():
                try:
                    baidu_result = translate_text(chinese_prompt, 'zh', 'en')
                    if baidu_result and baidu_result.strip():
                        logger.info(f"百度翻译成功: {chinese_prompt[:50]}... -> {baidu_result[:50]}...")
                        logger.debug(f"百度翻译完整提示词: {baidu_result}")
                        return baidu_result
                    else:
                        logger.warning("百度翻译也失败了")
                except Exception as baidu_e:
                    logger.error(f"百度翻译出错: {baidu_e}")
            else:
                logger.warning("百度翻译未配置")
            
            logger.warning("所有翻译方案都失败，使用原始中文提示词")
            return chinese_prompt
    
    def _get_output_dir(self, project_manager=None, current_project_name=None) -> str:
        """获取输出目录"""
        # 如果有项目管理器和当前项目，保存到项目的images/comfyui文件夹
        if project_manager and current_project_name:
            try:
                project_root = project_manager.get_project_path(current_project_name)
                output_dir = os.path.join(project_root, 'images', 'comfyui')
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"使用项目图片目录: {output_dir}")
                return output_dir
            except Exception as e:
                logger.warning(f"无法使用项目目录: {e}")
        
        # 如果没有项目管理器或项目名称，使用默认的临时目录
        logger.warning("没有项目管理器或项目名称，使用默认临时目录")
        import tempfile
        default_dir = os.path.join(tempfile.gettempdir(), 'comfyui_images')
        os.makedirs(default_dir, exist_ok=True)
        logger.info(f"使用默认图片目录: {default_dir}")
        return default_dir
    
    def _download_image_to_local(self, image_path: str) -> str:
        """从ComfyUI服务器下载图片到本地项目目录"""
        try:
            # 构建完整的下载URL
            download_url = f"{self.api_url}/view"
            
            # 解析图片路径
            if '/' in image_path:
                # 如果有子文件夹
                parts = image_path.split('/')
                filename = parts[-1]
                subfolder = '/'.join(parts[:-1])
                params = {'filename': filename, 'subfolder': subfolder, 'type': 'output'}
            else:
                # 没有子文件夹
                params = {'filename': image_path, 'type': 'output'}
            
            logger.info(f"正在从ComfyUI下载图片: {download_url} with params: {params}")
            
            # 添加调试日志
            logger.info(f"下载图片时的项目管理器状态: project_manager={self.project_manager}, current_project_name={self.current_project_name}")
            
            # 下载图片
            response = requests.get(download_url, params=params, timeout=30, proxies={"http": None, "https": None})
            response.raise_for_status()
            
            # 获取输出目录
            output_dir = self._get_output_dir(self.project_manager, self.current_project_name)
            
            # 生成本地文件名
            filename = params['filename']
            # 使用简洁的文件名，不包含时间戳
            name, ext = os.path.splitext(filename)
            local_filename = f"ComfyUI_{name}{ext}"
            local_path = os.path.join(output_dir, local_filename)
            
            # 保存图片
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"图片已保存到: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
            return None

# 用法示例：
# client = ComfyUIClient(api_url="http://localhost:8188", llm_api=llm_api_instance)
# images = client.generate_images(shots)