# -*- coding: utf-8 -*-
"""
工作流管理器 - 重写版本
- 简化异常处理，移除SystemExit相关代码
- 简化工作流加载和管理逻辑
- 使用直接错误返回机制
"""
import os
import json
import copy
import traceback
from typing import Dict, List, Optional
from src.utils.logger import logger

class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self, workflows_dir: str = None):
        """初始化工作流管理器
        
        Args:
            workflows_dir: 工作流目录路径
        """
        # 设置默认工作流目录
        if workflows_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            workflows_dir = os.path.join(
                os.path.dirname(os.path.dirname(current_dir)), 
                'config', 
                'workflows'
            )
        
        self.workflows_dir = workflows_dir
        self.workflows = {}
        self.current_workflow_id = None
        
        # 确保工作流目录存在
        self._ensure_workflows_directory()
        
        # 加载工作流
        self.load_workflows()
        
        logger.info(f"工作流管理器初始化完成，工作流目录: {self.workflows_dir}")
    
    def _ensure_workflows_directory(self):
        """确保工作流目录存在"""
        try:
            if not os.path.exists(self.workflows_dir):
                os.makedirs(self.workflows_dir, exist_ok=True)
                logger.info(f"创建工作流目录: {self.workflows_dir}")
            
            # 检查是否有工作流文件，如果没有则创建默认工作流
            workflow_files = [f for f in os.listdir(self.workflows_dir) if f.endswith('.json')]
            if not workflow_files:
                self._create_default_workflow()
                
        except Exception as e:
            logger.error(f"创建工作流目录失败: {str(e)}")
    
    def _create_default_workflow(self):
        """创建默认工作流"""
        try:
            default_workflow = {
                "id": "default",
                "name": "默认工作流",
                "description": "基础的文生图工作流",
                "version": "1.0",
                "workflow": {
                    "1": {
                        "inputs": {
                            "text": "beautiful landscape, high quality, detailed",
                            "clip": ["2", 1]
                        },
                        "class_type": "CLIPTextEncode",
                        "_meta": {
                            "title": "CLIP Text Encode (Prompt)"
                        }
                    },
                    "2": {
                        "inputs": {
                            "ckpt_name": "sd_xl_base_1.0.safetensors"
                        },
                        "class_type": "CheckpointLoaderSimple",
                        "_meta": {
                            "title": "Load Checkpoint"
                        }
                    },
                    "3": {
                        "inputs": {
                            "text": "nsfw, low quality, blurry",
                            "clip": ["2", 1]
                        },
                        "class_type": "CLIPTextEncode",
                        "_meta": {
                            "title": "CLIP Text Encode (Negative)"
                        }
                    },
                    "4": {
                        "inputs": {
                            "width": 1024,
                            "height": 1024,
                            "batch_size": 1
                        },
                        "class_type": "EmptyLatentImage",
                        "_meta": {
                            "title": "Empty Latent Image"
                        }
                    },
                    "5": {
                        "inputs": {
                            "seed": 42,
                            "steps": 20,
                            "cfg": 7.0,
                            "sampler_name": "euler",
                            "scheduler": "normal",
                            "denoise": 1.0,
                            "model": ["2", 0],
                            "positive": ["1", 0],
                            "negative": ["3", 0],
                            "latent_image": ["4", 0]
                        },
                        "class_type": "KSampler",
                        "_meta": {
                            "title": "KSampler"
                        }
                    },
                    "6": {
                        "inputs": {
                            "samples": ["5", 0],
                            "vae": ["2", 2]
                        },
                        "class_type": "VAEDecode",
                        "_meta": {
                            "title": "VAE Decode"
                        }
                    },
                    "7": {
                        "inputs": {
                            "filename_prefix": "ComfyUI",
                            "images": ["6", 0]
                        },
                        "class_type": "SaveImage",
                        "_meta": {
                            "title": "Save Image"
                        }
                    }
                },
                "parameters": {
                    "prompt_node": "1",
                    "negative_prompt_node": "3",
                    "width_node": "4",
                    "height_node": "4",
                    "steps_node": "5",
                    "cfg_node": "5",
                    "seed_node": "5",
                    "sampler_node": "5",
                    "scheduler_node": "5",
                    "model_node": "2"
                }
            }
            
            default_file = os.path.join(self.workflows_dir, 'default.json')
            with open(default_file, 'w', encoding='utf-8') as f:
                json.dump(default_workflow, f, indent=2, ensure_ascii=False)
            
            logger.info(f"创建默认工作流: {default_file}")
            
        except Exception as e:
            logger.error(f"创建默认工作流失败: {str(e)}")
    
    def load_workflows(self):
        """加载所有工作流"""
        logger.info(f"开始加载工作流，目录: {self.workflows_dir}")
        
        self.workflows = {}
        loaded_count = 0
        
        try:
            if not os.path.exists(self.workflows_dir):
                logger.warning(f"工作流目录不存在: {self.workflows_dir}")
                return
            
            # 遍历工作流目录
            for filename in os.listdir(self.workflows_dir):
                if not filename.endswith('.json'):
                    continue
                
                file_path = os.path.join(self.workflows_dir, filename)
                workflow = self._load_workflow_file(file_path)
                
                if workflow:
                    workflow_id = workflow.get('id', os.path.splitext(filename)[0])
                    self.workflows[workflow_id] = workflow
                    loaded_count += 1
                    logger.info(f"加载工作流: {workflow_id} ({filename})")
            
            # 设置默认工作流
            if self.workflows and not self.current_workflow_id:
                if 'default' in self.workflows:
                    self.current_workflow_id = 'default'
                else:
                    self.current_workflow_id = list(self.workflows.keys())[0]
                logger.info(f"设置默认工作流: {self.current_workflow_id}")
            
            logger.info(f"工作流加载完成，共加载 {loaded_count} 个工作流")
            
        except Exception as e:
            logger.error(f"加载工作流时发生异常: {str(e)}")
    
    def _load_workflow_file(self, file_path: str) -> Optional[Dict]:
        """加载单个工作流文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否是ComfyUI原始格式
            if self._is_comfyui_raw_format(data):
                logger.info(f"检测到ComfyUI原始格式，正在转换: {file_path}")
                data = self._convert_comfyui_raw_format(data, file_path)
            
            # 验证工作流格式
            if self._validate_workflow(data):
                return data
            else:
                logger.error(f"工作流格式验证失败: {file_path}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 {file_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"加载工作流文件失败 {file_path}: {str(e)}")
            return None
    
    def _is_comfyui_raw_format(self, data: Dict) -> bool:
        """检查是否是ComfyUI原始格式"""
        # ComfyUI原始格式通常直接包含节点ID作为键
        if not isinstance(data, dict):
            return False
        
        # 检查是否包含我们的标准字段
        if 'id' in data and 'workflow' in data:
            return False
        
        # 检查是否所有键都是数字字符串（ComfyUI节点ID）
        for key in data.keys():
            if not (isinstance(key, str) and key.isdigit()):
                return False
        
        return True
    
    def _convert_comfyui_raw_format(self, raw_data: Dict, file_path: str) -> Dict:
        """转换ComfyUI原始格式为标准格式"""
        filename = os.path.splitext(os.path.basename(file_path))[0]
        
        converted = {
            "id": filename,
            "name": filename.replace('_', ' ').title(),
            "description": f"从ComfyUI原始格式转换: {filename}",
            "version": "1.0",
            "workflow": raw_data,
            "parameters": self._extract_parameters_from_raw(raw_data)
        }
        
        logger.info(f"ComfyUI原始格式转换完成: {filename}")
        return converted
    
    def _extract_parameters_from_raw(self, raw_data: Dict) -> Dict:
        """从原始工作流中提取参数映射"""
        parameters = {}
        
        try:
            for node_id, node_data in raw_data.items():
                if not isinstance(node_data, dict):
                    continue
                
                class_type = node_data.get('class_type', '')
                inputs = node_data.get('inputs', {})
                
                # 根据节点类型提取参数
                if class_type == 'CLIPTextEncode':
                    if 'text' in inputs:
                        if 'prompt_node' not in parameters:
                            parameters['prompt_node'] = node_id
                        else:
                            parameters['negative_prompt_node'] = node_id
                
                elif class_type in ['EmptyLatentImage', 'EmptySD3LatentImage']:
                    if 'width' in inputs:
                        parameters['width_node'] = node_id
                    if 'height' in inputs:
                        parameters['height_node'] = node_id
                
                elif class_type in ['KSampler', 'SamplerCustomAdvanced']:
                    if 'steps' in inputs:
                        parameters['steps_node'] = node_id
                    if 'cfg' in inputs:
                        parameters['cfg_node'] = node_id
                    if 'seed' in inputs:
                        parameters['seed_node'] = node_id
                    if 'sampler_name' in inputs:
                        parameters['sampler_node'] = node_id
                    if 'scheduler' in inputs:
                        parameters['scheduler_node'] = node_id
                
                elif class_type == 'BasicScheduler':
                    if 'steps' in inputs:
                        parameters['steps_node'] = node_id
                    if 'denoise' in inputs:
                        parameters['denoise_node'] = node_id
                
                elif class_type == 'ModelSamplingFlux':
                    # ModelSamplingFlux的width和height参数只有在没有EmptySD3LatentImage节点时才映射
                    # 因为EmptySD3LatentImage是真正控制生成图片尺寸的节点
                    if 'width' in inputs and 'width_node' not in parameters:
                        parameters['width_node'] = node_id
                    if 'height' in inputs and 'height_node' not in parameters:
                        parameters['height_node'] = node_id
                
                elif class_type == 'RandomNoise':
                    if 'noise_seed' in inputs:
                        parameters['seed_node'] = node_id
                
                elif class_type == 'CheckpointLoaderSimple':
                    if 'ckpt_name' in inputs:
                        parameters['model_node'] = node_id
        
        except Exception as e:
            logger.error(f"提取参数映射时发生异常: {str(e)}")
        
        return parameters
    
    def _validate_workflow(self, workflow: Dict) -> bool:
        """验证工作流格式"""
        try:
            # 检查必需字段
            required_fields = ['id', 'workflow']
            for field in required_fields:
                if field not in workflow:
                    logger.error(f"工作流缺少必需字段: {field}")
                    return False
            
            # 检查workflow字段是否为字典
            if not isinstance(workflow['workflow'], dict):
                logger.error("workflow字段必须是字典类型")
                return False
            
            # 检查是否有节点
            if not workflow['workflow']:
                logger.error("工作流不能为空")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证工作流时发生异常: {str(e)}")
            return False
    
    def get_workflow(self, workflow_id: str = None) -> Optional[Dict]:
        """获取工作流
        
        Args:
            workflow_id: 工作流ID，如果为None则返回当前工作流
        
        Returns:
            工作流字典，如果不存在返回None
        """
        if workflow_id is None:
            workflow_id = self.current_workflow_id
        
        if workflow_id and workflow_id in self.workflows:
            return self.workflows[workflow_id]
        
        logger.warning(f"工作流不存在: {workflow_id}")
        return None
    
    def set_current_workflow(self, workflow_id: str) -> bool:
        """设置当前工作流
        
        Args:
            workflow_id: 工作流ID
        
        Returns:
            设置是否成功
        """
        if workflow_id in self.workflows:
            self.current_workflow_id = workflow_id
            logger.info(f"设置当前工作流: {workflow_id}")
            return True
        else:
            logger.error(f"工作流不存在: {workflow_id}")
            return False
    
    def get_current_workflow_id(self) -> Optional[str]:
        """获取当前工作流ID"""
        return self.current_workflow_id
    
    def get_available_workflows(self) -> List[Dict[str, str]]:
        """获取可用工作流列表
        
        Returns:
            工作流信息列表，每个元素包含id和name
        """
        workflows = []
        
        for workflow_id, workflow_data in self.workflows.items():
            workflows.append({
                'id': workflow_id,
                'name': workflow_data.get('name', workflow_id),
                'description': workflow_data.get('description', '')
            })
        
        return workflows
    
    def get_workflow_parameters(self, workflow_id: str = None) -> Dict:
        """获取工作流参数映射
        
        Args:
            workflow_id: 工作流ID，如果为None则使用当前工作流
        
        Returns:
            参数映射字典
        """
        workflow = self.get_workflow(workflow_id)
        if workflow:
            return workflow.get('parameters', {})
        return {}
    
    def update_workflow_parameter(self, node_id: str, parameter: str, value, workflow_id: str = None) -> bool:
        """更新工作流参数
        
        Args:
            node_id: 节点ID
            parameter: 参数名
            value: 参数值
            workflow_id: 工作流ID，如果为None则使用当前工作流
        
        Returns:
            更新是否成功
        """
        try:
            workflow = self.get_workflow(workflow_id)
            if not workflow:
                return False
            
            if node_id not in workflow['workflow']:
                logger.error(f"节点不存在: {node_id}")
                return False
            
            if 'inputs' not in workflow['workflow'][node_id]:
                workflow['workflow'][node_id]['inputs'] = {}
            
            workflow['workflow'][node_id]['inputs'][parameter] = value
            logger.info(f"更新工作流参数: {node_id}.{parameter} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"更新工作流参数失败: {str(e)}")
            return False
    
    def get_workflow_count(self) -> int:
        """获取工作流数量"""
        return len(self.workflows)
    
    def reload_workflows(self):
        """重新加载工作流"""
        logger.info("重新加载工作流")
        self.load_workflows()
    
    def get_workflows_directory(self) -> str:
        """获取工作流目录路径"""
        return self.workflows_dir
    
    def get_workflow_list(self) -> List[Dict[str, str]]:
        """获取工作流列表（兼容性方法）
        
        Returns:
            工作流信息列表，每个元素包含id和name
        """
        return self.get_available_workflows()
    
    def generate_workflow_json(self, prompt: str, parameters: Dict = None) -> Dict:
        """生成工作流JSON
        
        Args:
            prompt: 提示词
            parameters: 参数字典
        
        Returns:
            工作流JSON字典
        """
        try:
            # 获取当前工作流
            workflow = self.get_workflow(self.current_workflow_id)
            if not workflow:
                logger.error(f"当前工作流不存在: {self.current_workflow_id}")
                return None
            
            # 复制工作流JSON
            workflow_json = copy.deepcopy(workflow['workflow'])
            
            # 获取参数映射
            param_mapping = workflow.get('parameters', {})
            
            # 应用提示词
            if 'prompt_node' in param_mapping:
                prompt_node_id = param_mapping['prompt_node']
                if prompt_node_id in workflow_json:
                    if 'inputs' not in workflow_json[prompt_node_id]:
                        workflow_json[prompt_node_id]['inputs'] = {}
                    workflow_json[prompt_node_id]['inputs']['text'] = prompt
                    logger.debug(f"设置提示词到节点 {prompt_node_id}: {prompt[:50]}...")
            
            # 应用其他参数
            if parameters:
                for param_name, param_value in parameters.items():
                    # 查找对应的节点映射
                    node_mapping_key = f"{param_name}_node"
                    if node_mapping_key in param_mapping:
                        node_id = param_mapping[node_mapping_key]
                        if node_id in workflow_json:
                            if 'inputs' not in workflow_json[node_id]:
                                workflow_json[node_id]['inputs'] = {}
                            
                            # 特殊处理种子值参数
                            if param_name == 'seed':
                                # 检查节点类型，决定使用哪个字段名
                                node_class_type = workflow_json[node_id].get('class_type', '')
                                if node_class_type == 'RandomNoise':
                                    workflow_json[node_id]['inputs']['noise_seed'] = param_value
                                    logger.debug(f"设置种子值到RandomNoise节点 {node_id}.noise_seed: {param_value}")
                                else:
                                    workflow_json[node_id]['inputs']['seed'] = param_value
                                    logger.debug(f"设置种子值到节点 {node_id}.seed: {param_value}")
                            # 特殊处理宽高参数：需要同时更新ModelSamplingFlux节点
                            elif param_name in ['width', 'height']:
                                workflow_json[node_id]['inputs'][param_name] = param_value
                                logger.debug(f"设置参数 {param_name} 到节点 {node_id}: {param_value}")
                                
                                # 查找并同步更新ModelSamplingFlux节点的对应参数
                                for other_node_id, other_node_data in workflow_json.items():
                                    if (other_node_data.get('class_type') == 'ModelSamplingFlux' and 
                                        other_node_id != node_id and
                                        'inputs' in other_node_data and
                                        param_name in other_node_data['inputs']):
                                        workflow_json[other_node_id]['inputs'][param_name] = param_value
                                        logger.debug(f"同步设置参数 {param_name} 到ModelSamplingFlux节点 {other_node_id}: {param_value}")
                            else:
                                workflow_json[node_id]['inputs'][param_name] = param_value
                                logger.debug(f"设置参数 {param_name} 到节点 {node_id}: {param_value}")
                    else:
                        # 直接查找参数名对应的节点
                        if param_name in param_mapping:
                            node_id = param_mapping[param_name]
                            if node_id in workflow_json:
                                if 'inputs' not in workflow_json[node_id]:
                                    workflow_json[node_id]['inputs'] = {}
                                # 根据参数名推断输入字段名
                                input_field = self._get_input_field_name(param_name)
                                workflow_json[node_id]['inputs'][input_field] = param_value
                                logger.debug(f"设置参数 {param_name} 到节点 {node_id}.{input_field}: {param_value}")
            
            logger.info(f"工作流JSON生成完成，节点数量: {len(workflow_json)}")
            return workflow_json
            
        except Exception as e:
            logger.error(f"生成工作流JSON时发生异常: {str(e)}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            return None
    
    def _get_input_field_name(self, param_name: str) -> str:
        """根据参数名推断输入字段名
        
        Args:
            param_name: 参数名
        
        Returns:
            输入字段名
        """
        # 常见参数名映射
        field_mapping = {
            'width': 'width',
            'height': 'height',
            'steps': 'steps',
            'cfg': 'cfg',
            'seed': 'seed',
            'noise_seed': 'noise_seed',
            'sampler': 'sampler_name',
            'scheduler': 'scheduler',
            'denoise': 'denoise',
            'batch_size': 'batch_size'
        }
        
        return field_mapping.get(param_name, param_name)