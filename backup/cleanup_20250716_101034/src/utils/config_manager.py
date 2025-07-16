import os
import json
import threading
# 类型注解暂时不使用，避免IDE警告
from src.utils.logger import logger

class ConfigManager:
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, config_dir=None):  # noqa: ARG003
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_dir=None):
        # 避免重复初始化
        if self._initialized:
            return

        if config_dir is None:
            # 动态获取配置目录路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_dir = os.path.join(project_root, 'config')
        self.config_dir = config_dir
        self.config_file = os.path.join(self.config_dir, 'llm_config.json')
        self.config_json_dir = os.path.join(self.config_dir, 'config.json')

        # 使用缓存加载配置
        self.config = self._load_config()
        self.image_config = self._load_image_config()
        self.voice_config = self._load_voice_config()
        self.app_config = self._load_app_config()

        ConfigManager._initialized = True
        logger.info("配置管理器初始化完成")

    def _load_config(self):
        all_models = []
        # 只加载主配置文件，避免重复加载
        main_config_path = os.path.join(self.config_dir, 'llm_config.json')
        
        if os.path.exists(main_config_path):
            try:
                with open(main_config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Check if the file contains a list of models under the 'models' key
                    if isinstance(data, dict) and "models" in data and isinstance(data["models"], list):
                        # 去重处理：基于模型名称和类型去重
                        seen_models = set()
                        for model in data["models"]:
                            model_key = (model.get("name", ""), model.get("type", ""))
                            if model_key not in seen_models and model.get("name"):
                                all_models.append(model)
                                seen_models.add(model_key)
                        if len(all_models) > 0:
                            logger.info(f"Loaded {len(all_models)} unique models from main config")
                        else:
                            logger.debug("No models found in main config")
                    else:
                        logger.warning("Main config file does not contain a valid models list.")
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from main config: {e}")
            except Exception as e:
                logger.error(f"Error reading main config file: {e}")

        # If no config files are found, create a default one
        if not all_models:
             default_config_path = os.path.join(self.config_dir, 'llm_config.json')
             if not os.path.exists(default_config_path):
                default_config = {
                    "models": [
                        {
                            "name": "DefaultModel",
                            "type": "tongyi",
                            "key": "YOUR_API_KEY",
                            "url": "YOUR_API_URL"
                        }
                    ]
                }
                os.makedirs(self.config_dir, exist_ok=True)
                with open(default_config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4)
                all_models.extend(default_config["models"])
                logger.info(f"Created and loaded default config file: {default_config_path}")
             else:
                 # If default exists but no other models, load default
                 try:
                     with open(default_config_path, 'r', encoding='utf-8') as f:
                         default_config = json.load(f)
                         if isinstance(default_config, dict) and "models" in default_config and isinstance(default_config["models"], list):
                             all_models.extend(default_config["models"])
                             logger.debug(f"Loaded existing default config file: {default_config_path}")
                         elif isinstance(default_config, dict) and "name" in default_config:
                              all_models.append(default_config)
                              logger.debug(f"Loaded existing default config file (single model format): {default_config_path}")
                         else:
                             logger.warning(f"Existing default config file {default_config_path} does not contain a valid model configuration.")
                 except Exception as e:
                     logger.error(f"Error reading default config {default_config_path}: {e}")

        return {"models": all_models}
    
    def _load_image_config(self):
        """加载图像生成配置"""
        image_config_path = os.path.join(self.config_json_dir, 'image_config.json')
        if os.path.exists(image_config_path):
            try:
                with open(image_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading image config: {e}")
        return {"image_generation": {"default_engine": "pollinations", "pollinations": {"enabled": True}}}

    def _load_voice_config(self):
        """加载语音配置"""
        voice_config_path = os.path.join(self.config_json_dir, 'voice_config.json')
        if os.path.exists(voice_config_path):
            try:
                with open(voice_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading voice config: {e}")
        return {"voice_generation": {"default_engine": "edge", "engines": {"edge_tts": {"enabled": True}}}}

    def _load_app_config(self):
        """加载应用配置"""
        app_config_path = os.path.join(self.config_json_dir, 'app_config.json')
        if os.path.exists(app_config_path):
            try:
                with open(app_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading app config: {e}")
        return {"app_settings": {"version": "2.0.0", "debug_mode": False}}

    def get_model_config(self, model_name):
        # This method remains the same, as it iterates through the 'models' list
        for model in self.config.get("models", []):
            if model.get("name") == model_name:
                return model
        return None

    def save_model_config(self, model_name, model_type, api_key, api_url):
        # Simple implementation: find and update, or add if not found
        models = self.config.get("models", [])
        found = False
        for model in models:
            if model.get("name") == model_name:
                model["type"] = model_type
                model["key"] = api_key
                model["url"] = api_url
                found = True
                break
        if not found:
            models.append({
                "name": model_name,
                "type": model_type,
                "key": api_key,
                "url": api_url
            })
        self.config["models"] = models
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config to {self.config_file}: {e}")
    
    def save_app_settings(self, app_config):
        """保存应用设置到app_settings.json文件"""
        try:
            app_settings_file = os.path.join(self.config_dir, 'app_settings.json')
            
            # 如果文件存在，先读取现有设置
            existing_settings = {}
            if os.path.exists(app_settings_file):
                try:
                    with open(app_settings_file, 'r', encoding='utf-8') as f:
                        existing_settings = json.load(f)
                except Exception as e:
                    print(f"Warning: Could not read existing app settings: {e}")
            
            # 更新设置
            existing_settings.update(app_config)
            
            # 确保目录存在
            os.makedirs(self.config_dir, exist_ok=True)
            
            # 保存设置
            with open(app_settings_file, 'w', encoding='utf-8') as f:
                json.dump(existing_settings, f, indent=4, ensure_ascii=False)
            
            print(f"App settings saved to {app_settings_file}")
            return True
            
        except Exception as e:
            print(f"Error saving app settings: {e}")
            return False

    def save_config(self, config_data):
        """保存配置数据到 app_settings.json 文件。"""
        return self.save_app_settings(config_data)

    def get_models(self):
        return self.config.get("models", [])
    
    def get_image_config(self):
        """获取图像生成配置"""
        return self.image_config
    
    def get_voice_config(self):
        """获取语音配置"""
        return self.voice_config
    
    def get_app_config(self):
        """获取应用配置"""
        return self.app_config
    
    def get_llm_config(self):
        """获取LLM配置"""
        # 获取第一个启用的模型作为默认LLM配置
        for model in self.config.get("models", []):
            if model.get("enabled", True):  # 默认启用
                return {
                    "api_type": model.get("type"),
                    "api_key": model.get("key"),
                    "api_url": model.get("url"),
                    "model_name": model.get("model", model.get("name"))
                }
        return None
    
    def get_image_providers(self):
        """获取可用的图像生成提供商"""
        image_gen = self.image_config.get('image_generation', {})
        providers = []

        if image_gen.get('pollinations', {}).get('enabled', False):
            providers.append('pollinations')
        if image_gen.get('comfyui', {}).get('enabled', False):
            providers.append('comfyui')
        if image_gen.get('stability', {}).get('enabled', False):
            providers.append('stability')
        if image_gen.get('dalle', {}).get('enabled', False):
            providers.append('dalle')
        if image_gen.get('cogview_3_flash', {}).get('enabled', False):
            providers.append('cogview_3_flash')

        return providers
    
    def get_voice_providers(self):
        """获取可用的语音提供商"""
        engines = self.voice_config.get('voice_generation', {}).get('engines', {})
        providers = []
        
        if engines.get('edge_tts', {}).get('enabled', False):
            providers.append('edge_tts')
        if engines.get('siliconflow', {}).get('enabled', False):
            providers.append('siliconflow')
        if engines.get('openai_tts', {}).get('enabled', False):
            providers.append('openai_tts')
            
        return providers

    def get_model_by_name(self, name):
        for model in self.config.get("models", []):
            if model['name'] == name:
                return model
        return None

    def add_model(self, model):
        if "models" not in self.config:
            self.config["models"] = []
        self.config["models"].append(model)
        self._save_config()

    def remove_model(self, name):
        if "models" in self.config:
            self.config["models"] = [model for model in self.config["models"] if model['name'] != name]
            self._save_config()

    def update_model(self, name, updated_model):
        if "models" in self.config:
            for i, model in enumerate(self.config["models"]):
                if model['name'] == name:
                    self.config["models"][i] = updated_model
                    break
            self._save_config()

    def _save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)
    
    # TTS相关配置管理
    def get_tts_config(self):
        """获取TTS配置"""
        tts_config_file = os.path.join(self.config_dir, 'tts_config.json')
        if os.path.exists(tts_config_file):
            try:
                with open(tts_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载TTS配置失败: {e}")
        
        # 返回默认TTS配置
        return self._get_default_tts_config()
    
    def _get_default_tts_config(self):
        """获取默认TTS配置"""
        return {
            'default_engine': 'edge',
            'default_voice': 'zh-CN-XiaoxiaoNeural-Female',
            'default_rate': 1.0,
            'default_volume': 1.0,
            'generate_subtitle': True,
            'output_format': 'mp3',
            'edge_tts': {
                'enabled': True
            },
            'siliconflow': {
                'enabled': False,
                'api_key': '',
                'base_url': 'https://api.siliconflow.cn/v1'
            },
            'audio': {
                'output_dir': 'audio',
                'subtitle_dir': 'subtitles'
            }
        }
    
    def save_tts_config(self, config):
        """保存TTS配置"""
        tts_config_file = os.path.join(self.config_dir, 'tts_config.json')
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(tts_config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存TTS配置失败: {e}")
    
    def save_llm_config(self, config):
        """保存LLM配置"""
        try:
            # 确保配置目录存在
            os.makedirs(self.config_dir, exist_ok=True)
            
            # 更新内存中的配置
            if 'models' in config:
                if 'models' not in self.config:
                    self.config['models'] = []
                
                # 合并新的模型配置
                for model_name, model_info in config['models'].items():
                    # 查找是否已存在同名模型（包括占位符版本）
                    existing_indices = []
                    for i, model in enumerate(self.config['models']):
                        if model.get('name') == model_name:
                            existing_indices.append(i)
                    
                    # 构建模型配置
                    model_config = {
                        'name': model_name,
                        'type': model_info.get('type', 'openai'),
                        'key': model_info.get('api_key', ''),
                        'url': model_info.get('base_url', '')
                    }
                    
                    # 删除所有同名的现有模型（包括占位符版本）
                    for i in reversed(existing_indices):
                        del self.config['models'][i]
                    
                    # 只有当API密钥不是占位符时才添加新配置
                    api_key = model_config.get('key', '')
                    if api_key and not api_key.startswith('YOUR_') and not api_key.endswith('_HERE'):
                        self.config['models'].append(model_config)
                    else:
                        logger.warning(f"跳过保存模型 {model_name}：API密钥为空或为占位符")
            
            # 保存到文件
            self._save_config()
            return True
            
        except Exception as e:
            print(f"保存LLM配置失败: {e}")
            return False
    
    def get_tts_setting(self, key, default=None):
        """获取TTS配置项"""
        config = self.get_tts_config()
        keys = key.split('.')
        value = config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_tts_setting(self, key, value):
        """设置TTS配置项"""
        config = self.get_tts_config()
        keys = key.split('.')
        
        # 导航到目标位置
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # 设置值
        current[keys[-1]] = value
        
        # 保存配置
        self.save_tts_config(config)
    
    def get_audio_output_dir(self):
        """获取音频输出目录"""
        output_dir = self.get_tts_setting('audio.output_dir', 'audio')
        # 确保output_dir是字符串
        if not isinstance(output_dir, str):
            output_dir = str(output_dir) if output_dir else 'audio'

        # 转换为绝对路径
        if not os.path.isabs(output_dir):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            output_dir = os.path.join(base_dir, output_dir)

        # 确保目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        return output_dir
    
    def get_subtitle_output_dir(self):
        """获取字幕输出目录"""
        output_dir = self.get_tts_setting('audio.subtitle_dir', 'subtitles')
        # 确保output_dir是字符串
        if not isinstance(output_dir, str):
            output_dir = str(output_dir) if output_dir else 'subtitles'

        # 转换为绝对路径
        if not os.path.isabs(output_dir):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            output_dir = os.path.join(base_dir, output_dir)

        # 确保目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        return output_dir
    
    def get_setting(self, key, default=None):
        """获取应用配置项"""
        config = self.get_app_config()
        keys = key.split('.')
        value = config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_setting(self, key, value):
        """设置应用配置项"""
        config = self.get_app_config()
        keys = key.split('.')
        
        # 导航到目标位置
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # 设置值
        current[keys[-1]] = value
        
        # 保存配置
        self.app_config = config
        app_config_path = os.path.join(self.config_json_dir, 'app_config.json')
        try:
            os.makedirs(os.path.dirname(app_config_path), exist_ok=True)
            with open(app_config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving app config: {e}")