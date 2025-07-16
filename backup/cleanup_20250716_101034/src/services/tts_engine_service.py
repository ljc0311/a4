#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS引擎服务层
支持多种配音引擎：Edge-TTS、CosyVoice、TTSMaker、科大讯飞、ElevenLabs
"""

import os
import asyncio
import json
import requests
import subprocess
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from abc import ABC, abstractmethod

from src.utils.logger import logger
from src.utils.config_manager import ConfigManager

# 尝试导入Edge TTS
try:
    import edge_tts
    from edge_tts import SubMaker
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    edge_tts = None
    SubMaker = None


class TTSEngineBase(ABC):
    """TTS引擎基类"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.engine_name = self.__class__.__name__.replace('Engine', '').lower()
    
    @abstractmethod
    async def generate_speech(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """生成语音
        
        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            **kwargs: 引擎特定参数
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        pass
    
    @abstractmethod
    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取可用音色列表"""
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """测试引擎连接"""
        pass
    
    def get_default_settings(self) -> Dict[str, Any]:
        """获取默认设置"""
        return {
            'voice': '',
            'speed': 1.0,
            'pitch': 0,
            'volume': 1.0,
            'language': 'zh-CN'
        }


class EdgeTTSEngine(TTSEngineBase):
    """Edge-TTS引擎"""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self.voices_cache = None
    
    async def generate_speech(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """使用Edge-TTS生成语音"""
        try:
            if not EDGE_TTS_AVAILABLE or edge_tts is None:
                return {
                    'success': False,
                    'error': 'Edge-TTS未安装，请运行: pip install edge-tts'
                }

            voice = kwargs.get('voice', 'zh-CN-YunxiNeural')
            speed = kwargs.get('speed', 1.0)
            pitch = kwargs.get('pitch', 0)

            # 转换参数格式
            rate_str = f"{int((speed - 1) * 100):+d}%"
            pitch_str = f"{int(pitch):+d}Hz"

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 生成语音
            communicate = edge_tts.Communicate(text, voice, rate=rate_str, pitch=pitch_str)
            sub_maker = edge_tts.SubMaker()

            with open(output_path, "wb") as file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio" and "data" in chunk:
                        file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        sub_maker.feed(chunk)

            # Edge-TTS 7.0+ 需要调用merge_cues()来完成字幕生成
            # merge_cues()参数指定要合并的单词数量，1表示不合并
            if hasattr(sub_maker, 'merge_cues'):
                sub_maker.merge_cues(1)

            # 生成字幕数据
            subtitle_data = []
            if hasattr(sub_maker, 'cues') and len(sub_maker.cues) > 0:
                for cue in sub_maker.cues:
                    # Edge-TTS 7.x版本使用content属性
                    cue_text = getattr(cue, 'content', '') or getattr(cue, 'text', '') or str(cue)
                    subtitle_data.append({
                        'start': cue.start,
                        'end': cue.end,
                        'text': cue_text
                    })
            
            return {
                'success': True,
                'audio_file': output_path,
                'subtitle_data': subtitle_data,
                'engine': 'edge_tts',
                'voice': voice
            }
            
        except Exception as e:
            logger.error(f"Edge-TTS生成失败: {e}")
            return {
                'success': False,
                'error': f'Edge-TTS生成失败: {str(e)}'
            }
    
    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取Edge-TTS可用音色"""
        if self.voices_cache is None:
            try:
                # 这里可以从配置文件或API获取音色列表
                self.voices_cache = [
                    {'id': 'zh-CN-YunxiNeural', 'name': '云希-男声', 'language': 'zh-CN'},
                    {'id': 'zh-CN-XiaoxiaoNeural', 'name': '晓晓-女声', 'language': 'zh-CN'},
                    {'id': 'zh-CN-YunyangNeural', 'name': '云扬-男声', 'language': 'zh-CN'},
                    {'id': 'zh-CN-XiaoyiNeural', 'name': '晓伊-女声', 'language': 'zh-CN'},
                    {'id': 'en-US-AriaNeural', 'name': 'Aria-Female', 'language': 'en-US'},
                    {'id': 'en-US-GuyNeural', 'name': 'Guy-Male', 'language': 'en-US'},
                ]
            except Exception as e:
                logger.error(f"获取Edge-TTS音色列表失败: {e}")
                self.voices_cache = []
        
        return self.voices_cache
    
    def test_connection(self) -> Dict[str, Any]:
        """测试Edge-TTS连接"""
        try:
            if not EDGE_TTS_AVAILABLE:
                return {
                    'success': False,
                    'error': 'Edge-TTS未安装，请运行: pip install edge-tts'
                }
            return {
                'success': True,
                'message': 'Edge-TTS可用'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_default_settings(self) -> Dict[str, Any]:
        """获取Edge-TTS默认设置"""
        return {
            'voice': 'zh-CN-YunxiNeural',
            'speed': 1.0,
            'pitch': 0,
            'volume': 1.0,
            'language': 'zh-CN'
        }


class CosyVoiceEngine(TTSEngineBase):
    """CosyVoice本地引擎"""

    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        model_path_setting = self.config_manager.get_setting('cosyvoice.model_path', '')
        self.model_path: str = str(model_path_setting) if model_path_setting else ''
    
    async def generate_speech(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """使用CosyVoice生成语音"""
        try:
            if not self.model_path or not os.path.exists(self.model_path):
                return {
                    'success': False,
                    'error': 'CosyVoice模型路径未配置或不存在'
                }
            
            voice = kwargs.get('voice', 'default')
            speed = kwargs.get('speed', 1.0)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 构建CosyVoice命令
            cmd = [
                'python', 
                os.path.join(self.model_path, 'inference.py'),
                '--text', text,
                '--output', output_path,
                '--voice', voice,
                '--speed', str(speed)
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'audio_file': output_path,
                    'engine': 'cosyvoice',
                    'voice': voice
                }
            else:
                return {
                    'success': False,
                    'error': f'CosyVoice生成失败: {result.stderr}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'CosyVoice生成超时'
            }
        except Exception as e:
            logger.error(f"CosyVoice生成失败: {e}")
            return {
                'success': False,
                'error': f'CosyVoice生成失败: {str(e)}'
            }
    
    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取CosyVoice可用音色"""
        return [
            {'id': 'default', 'name': '默认音色', 'language': 'zh-CN'},
            {'id': 'female', 'name': '女声', 'language': 'zh-CN'},
            {'id': 'male', 'name': '男声', 'language': 'zh-CN'},
        ]
    
    def test_connection(self) -> Dict[str, Any]:
        """测试CosyVoice连接"""
        try:
            if not self.model_path:
                return {
                    'success': False,
                    'error': 'CosyVoice模型路径未配置'
                }
            
            if not os.path.exists(self.model_path):
                return {
                    'success': False,
                    'error': f'CosyVoice模型路径不存在: {self.model_path}'
                }
            
            # 检查inference.py是否存在
            inference_path = os.path.join(self.model_path, 'inference.py')
            if not os.path.exists(inference_path):
                return {
                    'success': False,
                    'error': f'CosyVoice推理脚本不存在: {inference_path}'
                }
            
            return {
                'success': True,
                'message': 'CosyVoice模型可用'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_default_settings(self) -> Dict[str, Any]:
        """获取CosyVoice默认设置"""
        return {
            'voice': 'default',
            'speed': 1.0,
            'pitch': 0,
            'volume': 1.0,
            'language': 'zh-CN',
            'model_path': self.model_path
        }


class TTSMakerEngine(TTSEngineBase):
    """TTSMaker引擎"""

    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self.api_url = 'https://api.ttsmaker.com/v1/create-speech'
        self.api_key = self.config_manager.get_setting('ttsmaker.api_key', '')

    async def generate_speech(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """使用TTSMaker生成语音"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'TTSMaker API Key未配置'
                }

            voice = kwargs.get('voice', 'zh-CN-XiaoxiaoNeural')
            speed = kwargs.get('speed', 1.0)

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 构建请求数据
            data = {
                'text': text,
                'voice_id': voice,
                'audio_format': 'mp3',
                'speed': speed,
                'volume': kwargs.get('volume', 1.0),
                'pitch': kwargs.get('pitch', 0)
            }

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            # 发送请求
            response = requests.post(self.api_url, json=data, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # 下载音频文件
                    audio_url = result.get('audio_url')
                    if audio_url:
                        audio_response = requests.get(audio_url, timeout=30)
                        if audio_response.status_code == 200:
                            with open(output_path, 'wb') as f:
                                f.write(audio_response.content)

                            return {
                                'success': True,
                                'audio_file': output_path,
                                'engine': 'ttsmaker',
                                'voice': voice
                            }
                        else:
                            return {
                                'success': False,
                                'error': '下载音频文件失败'
                            }
                    else:
                        return {
                            'success': False,
                            'error': '未获取到音频URL'
                        }
                else:
                    return {
                        'success': False,
                        'error': result.get('message', '生成失败')
                    }
            else:
                return {
                    'success': False,
                    'error': f'TTSMaker API请求失败: {response.status_code}'
                }

        except Exception as e:
            logger.error(f"TTSMaker生成失败: {e}")
            return {
                'success': False,
                'error': f'TTSMaker生成失败: {str(e)}'
            }

    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取TTSMaker可用音色"""
        return [
            {'id': 'zh-CN-XiaoxiaoNeural', 'name': '晓晓-女声', 'language': 'zh-CN'},
            {'id': 'zh-CN-YunxiNeural', 'name': '云希-男声', 'language': 'zh-CN'},
            {'id': 'en-US-AriaNeural', 'name': 'Aria-Female', 'language': 'en-US'},
            {'id': 'en-US-GuyNeural', 'name': 'Guy-Male', 'language': 'en-US'},
        ]

    def test_connection(self) -> Dict[str, Any]:
        """测试TTSMaker连接"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'TTSMaker API Key未配置'
                }

            # 发送测试请求
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            test_data = {
                'text': '测试',
                'voice_id': 'zh-CN-XiaoxiaoNeural',
                'audio_format': 'mp3'
            }

            response = requests.post(self.api_url, json=test_data, headers=headers, timeout=10)

            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'TTSMaker连接正常'
                }
            else:
                return {
                    'success': False,
                    'error': f'TTSMaker连接失败: {response.status_code}'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_default_settings(self) -> Dict[str, Any]:
        """获取TTSMaker默认设置"""
        return {
            'voice': 'zh-CN-XiaoxiaoNeural',
            'speed': 1.0,
            'pitch': 0,
            'volume': 1.0,
            'language': 'zh-CN',
            'api_key': self.api_key
        }


class XunfeiEngine(TTSEngineBase):
    """科大讯飞引擎"""

    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self.app_id = self.config_manager.get_setting('xunfei.app_id', '')
        self.api_key = self.config_manager.get_setting('xunfei.api_key', '')
        self.api_secret = self.config_manager.get_setting('xunfei.api_secret', '')
        self.api_url = 'https://tts-api.xfyun.cn/v2/tts'

    async def generate_speech(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """使用科大讯飞生成语音"""
        try:
            if not all([self.app_id, self.api_key, self.api_secret]):
                return {
                    'success': False,
                    'error': '科大讯飞API配置不完整'
                }

            voice = kwargs.get('voice', 'xiaoyan')
            speed = kwargs.get('speed', 1.0)

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 构建请求参数
            import time
            import hashlib
            import hmac
            import base64

            # 生成时间戳
            ts = str(int(time.time()))

            # 构建签名
            signature_origin = f"host: tts-api.xfyun.cn\ndate: {ts}\nGET /v2/tts HTTP/1.1"
            signature_sha = hmac.new(
                str(self.api_secret).encode('utf-8'),
                signature_origin.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            signature = base64.b64encode(signature_sha).decode()

            # 构建authorization
            authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
            authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode()

            # 构建请求头
            headers = {
                'Authorization': authorization,
                'Date': ts,
                'Host': 'tts-api.xfyun.cn'
            }

            # 构建请求数据
            data = {
                'common': {
                    'app_id': self.app_id
                },
                'business': {
                    'aue': 'mp3',
                    'vcn': voice,
                    'speed': int(speed * 50),
                    'volume': int(kwargs.get('volume', 1.0) * 50),
                    'pitch': int(kwargs.get('pitch', 0) + 50),
                    'bgs': 0
                },
                'data': {
                    'status': 2,
                    'text': base64.b64encode(text.encode('utf-8')).decode()
                }
            }

            # 发送请求
            response = requests.post(self.api_url, json=data, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()

                if result.get('code') == 0:
                    # 解码音频数据
                    audio_data = base64.b64decode(result['data']['audio'])

                    with open(output_path, 'wb') as f:
                        f.write(audio_data)

                    return {
                        'success': True,
                        'audio_file': output_path,
                        'engine': 'xunfei',
                        'voice': voice
                    }
                else:
                    return {
                        'success': False,
                        'error': f'科大讯飞API错误: {result.get("message", "未知错误")}'
                    }
            else:
                return {
                    'success': False,
                    'error': f'科大讯飞API请求失败: {response.status_code}'
                }

        except Exception as e:
            logger.error(f"科大讯飞生成失败: {e}")
            return {
                'success': False,
                'error': f'科大讯飞生成失败: {str(e)}'
            }

    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取科大讯飞可用音色"""
        return [
            {'id': 'xiaoyan', 'name': '小燕-女声', 'language': 'zh-CN'},
            {'id': 'xiaoyu', 'name': '小宇-男声', 'language': 'zh-CN'},
            {'id': 'xiaofeng', 'name': '小峰-男声', 'language': 'zh-CN'},
            {'id': 'xiaomei', 'name': '小美-女声', 'language': 'zh-CN'},
        ]

    def test_connection(self) -> Dict[str, Any]:
        """测试科大讯飞连接"""
        try:
            if not all([self.app_id, self.api_key, self.api_secret]):
                return {
                    'success': False,
                    'error': '科大讯飞API配置不完整'
                }

            return {
                'success': True,
                'message': '科大讯飞配置正常'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_default_settings(self) -> Dict[str, Any]:
        """获取科大讯飞默认设置"""
        return {
            'voice': 'xiaoyan',
            'speed': 1.0,
            'pitch': 0,
            'volume': 1.0,
            'language': 'zh-CN',
            'app_id': self.app_id,
            'api_key': self.api_key,
            'api_secret': self.api_secret
        }


class ElevenLabsEngine(TTSEngineBase):
    """ElevenLabs引擎"""

    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self.api_key = self.config_manager.get_setting('elevenlabs.api_key', '')
        self.api_url = 'https://api.elevenlabs.io/v1/text-to-speech'

    async def generate_speech(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """使用ElevenLabs生成语音"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'ElevenLabs API Key未配置'
                }

            voice_id = kwargs.get('voice', 'pNInz6obpgDQGcFmaJgB')  # Adam voice

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 构建请求数据
            data = {
                'text': text,
                'voice_settings': {
                    'stability': kwargs.get('stability', 0.5),
                    'similarity_boost': kwargs.get('similarity_boost', 0.5),
                    'style': kwargs.get('style', 0.0),
                    'use_speaker_boost': kwargs.get('use_speaker_boost', True)
                }
            }

            headers = {
                'xi-api-key': self.api_key,
                'Content-Type': 'application/json'
            }

            # 发送请求
            response = requests.post(
                f"{self.api_url}/{voice_id}",
                json=data,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)

                return {
                    'success': True,
                    'audio_file': output_path,
                    'engine': 'elevenlabs',
                    'voice': voice_id
                }
            else:
                return {
                    'success': False,
                    'error': f'ElevenLabs API请求失败: {response.status_code}'
                }

        except Exception as e:
            logger.error(f"ElevenLabs生成失败: {e}")
            return {
                'success': False,
                'error': f'ElevenLabs生成失败: {str(e)}'
            }

    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取ElevenLabs可用音色"""
        return [
            {'id': 'pNInz6obpgDQGcFmaJgB', 'name': 'Adam-Male', 'language': 'en-US'},
            {'id': 'EXAVITQu4vr4xnSDxMaL', 'name': 'Bella-Female', 'language': 'en-US'},
            {'id': 'VR6AewLTigWG4xSOukaG', 'name': 'Arnold-Male', 'language': 'en-US'},
            {'id': 'pqHfZKP75CvOlQylNhV4', 'name': 'Bill-Male', 'language': 'en-US'},
        ]

    def test_connection(self) -> Dict[str, Any]:
        """测试ElevenLabs连接"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'ElevenLabs API Key未配置'
                }

            # 测试API连接
            headers = {
                'xi-api-key': str(self.api_key)
            }

            response = requests.get(
                'https://api.elevenlabs.io/v1/voices',
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'ElevenLabs连接正常'
                }
            else:
                return {
                    'success': False,
                    'error': f'ElevenLabs连接失败: {response.status_code}'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_default_settings(self) -> Dict[str, Any]:
        """获取ElevenLabs默认设置"""
        return {
            'voice': 'pNInz6obpgDQGcFmaJgB',
            'stability': 0.5,
            'similarity_boost': 0.5,
            'style': 0.0,
            'use_speaker_boost': True,
            'language': 'en-US',
            'api_key': self.api_key
        }


class TTSEngineManager:
    """TTS引擎管理器"""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.engines = {}
        self._init_engines()

    def _init_engines(self):
        """初始化所有引擎"""
        self.engines = {
            'edge_tts': EdgeTTSEngine(self.config_manager),
            'cosyvoice': CosyVoiceEngine(self.config_manager),
            'ttsmaker': TTSMakerEngine(self.config_manager),
            'xunfei': XunfeiEngine(self.config_manager),
            'elevenlabs': ElevenLabsEngine(self.config_manager)
        }

    def get_engine(self, engine_name: str) -> Optional[TTSEngineBase]:
        """获取指定引擎"""
        return self.engines.get(engine_name)

    def get_available_engines(self) -> List[str]:
        """获取可用引擎列表"""
        return list(self.engines.keys())

    def get_engine_info(self, engine_name: str) -> Dict[str, Any]:
        """获取引擎信息"""
        engine = self.get_engine(engine_name)
        if not engine:
            return {'error': f'引擎 {engine_name} 不存在'}

        return {
            'name': engine_name,
            'voices': engine.get_available_voices(),
            'default_settings': engine.get_default_settings(),
            'connection_status': engine.test_connection()
        }

    async def generate_speech(self, engine_name: str, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """使用指定引擎生成语音"""
        engine = self.get_engine(engine_name)
        if not engine:
            return {
                'success': False,
                'error': f'引擎 {engine_name} 不存在'
            }

        return await engine.generate_speech(text, output_path, **kwargs)

    def test_all_engines(self) -> Dict[str, Dict[str, Any]]:
        """测试所有引擎连接"""
        results = {}
        for engine_name, engine in self.engines.items():
            results[engine_name] = engine.test_connection()
        return results

    def get_voices_by_language(self, language: str = 'zh-CN') -> Dict[str, List[Dict[str, str]]]:
        """按语言获取所有引擎的音色"""
        voices_by_engine = {}
        for engine_name, engine in self.engines.items():
            voices = engine.get_available_voices()
            filtered_voices = [v for v in voices if v.get('language', '').startswith(language[:2])]
            if filtered_voices:
                voices_by_engine[engine_name] = filtered_voices
        return voices_by_engine
