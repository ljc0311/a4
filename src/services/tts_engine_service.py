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
            output_dir = os.path.dirname(output_path)
            if output_dir:  # 只有当目录不为空时才创建
                os.makedirs(output_dir, exist_ok=True)

            # 🔧 修复：简化Edge-TTS调用，避免SubMaker兼容性问题
            communicate = edge_tts.Communicate(text, voice, rate=rate_str, pitch=pitch_str)
            
            # 只生成音频，暂时跳过字幕生成以避免兼容性问题
            with open(output_path, "wb") as file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio" and "data" in chunk:
                        file.write(chunk["data"])
            
            # 检查文件是否成功生成
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise Exception("音频文件生成失败或为空")
            
            return {
                'success': True,
                'audio_file': output_path,
                'subtitle_data': [],  # 暂时返回空字幕数据
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


class AzureSpeechEngine(TTSEngineBase):
    """Azure Cognitive Services Speech引擎"""

    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self.api_key = self.config_manager.get_setting('azure_speech.api_key', '')
        self.region = self.config_manager.get_setting('azure_speech.region', 'eastus')
        self.api_url = f'https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1'

    async def generate_speech(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """使用Azure Speech生成语音"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'Azure Speech API Key未配置'
                }

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 构建SSML
            voice = kwargs.get('voice', 'zh-CN-XiaoxiaoNeural')
            speed = kwargs.get('speed', 1.0)
            pitch = kwargs.get('pitch', 0)
            volume = kwargs.get('volume', 1.0)
            emotion = kwargs.get('emotion', 'neutral')

            # 构建SSML文档
            ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
                       xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN">
                <voice name="{voice}">
                    <mstts:express-as style="{emotion}">
                        <prosody rate="{speed}" pitch="{pitch:+.0f}%" volume="{volume}">
                            {text}
                        </prosody>
                    </mstts:express-as>
                </voice>
            </speak>'''

            headers = {
                'Ocp-Apim-Subscription-Key': self.api_key,
                'Content-Type': 'application/ssml+xml',
                'X-Microsoft-OutputFormat': 'audio-16khz-128kbitrate-mono-mp3',
                'User-Agent': 'VideoCreator'
            }

            # 发送请求
            response = requests.post(self.api_url, data=ssml.encode('utf-8'), headers=headers, timeout=30)

            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"Azure Speech语音生成成功: {output_path}")
                return {
                    'success': True,
                    'audio_file': output_path,
                    'engine': 'azure_speech',
                    'voice': voice
                }
            else:
                return {
                    'success': False,
                    'error': f'Azure Speech API请求失败: {response.status_code} - {response.text}'
                }

        except Exception as e:
            logger.error(f"Azure Speech语音生成失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取可用音色列表"""
        return [
            # 中文神经网络语音
            {'id': 'zh-CN-XiaoxiaoNeural', 'name': '晓晓 (温柔女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-XiaohanNeural', 'name': '晓涵 (温暖女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-XiaomengNeural', 'name': '晓梦 (甜美女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-XiaomoNeural', 'name': '晓墨 (成熟女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-XiaoqiuNeural', 'name': '晓秋 (知性女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-XiaoruiNeural', 'name': '晓睿 (活泼女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-XiaoshuangNeural', 'name': '晓双 (清脆女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-XiaoxuanNeural', 'name': '晓萱 (优雅女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-XiaoyanNeural', 'name': '晓颜 (亲切女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-XiaoyouNeural', 'name': '晓悠 (舒缓女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-XiaozhenNeural', 'name': '晓甄 (专业女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-YunxiNeural', 'name': '云希 (阳光男声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-YunyangNeural', 'name': '云扬 (成熟男声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-YunjianNeural', 'name': '云健 (稳重男声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-YunxiaNeural', 'name': '云夏 (清朗男声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-YunyeNeural', 'name': '云野 (磁性男声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-YunzeNeural', 'name': '云泽 (温和男声)', 'language': 'zh-CN'},
            # 英文神经网络语音
            {'id': 'en-US-AriaNeural', 'name': 'Aria (美式女声)', 'language': 'en-US'},
            {'id': 'en-US-JennyNeural', 'name': 'Jenny (美式女声)', 'language': 'en-US'},
            {'id': 'en-US-GuyNeural', 'name': 'Guy (美式男声)', 'language': 'en-US'},
            {'id': 'en-US-DavisNeural', 'name': 'Davis (美式男声)', 'language': 'en-US'}
        ]

    def test_connection(self) -> Dict[str, Any]:
        """测试Azure Speech连接"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'Azure Speech API Key未配置'
                }

            # 发送测试请求
            test_ssml = '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
                <voice name="zh-CN-XiaoxiaoNeural">测试</voice>
            </speak>'''

            headers = {
                'Ocp-Apim-Subscription-Key': self.api_key,
                'Content-Type': 'application/ssml+xml',
                'X-Microsoft-OutputFormat': 'audio-16khz-128kbitrate-mono-mp3',
                'User-Agent': 'VideoCreator'
            }

            response = requests.post(self.api_url, data=test_ssml.encode('utf-8'), headers=headers, timeout=10)

            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Azure Speech连接正常'
                }
            else:
                return {
                    'success': False,
                    'error': f'Azure Speech连接失败: {response.status_code}'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_default_settings(self) -> Dict[str, Any]:
        """获取Azure Speech默认设置"""
        return {
            'voice': 'zh-CN-XiaoxiaoNeural',
            'speed': 1.0,
            'pitch': 0,
            'volume': 1.0,
            'emotion': 'neutral',
            'language': 'zh-CN',
            'api_key': self.api_key,
            'region': self.region
        }


class GoogleTTSEngine(TTSEngineBase):
    """Google Cloud Text-to-Speech引擎"""

    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self.api_key = self.config_manager.get_setting('google_tts.api_key', '')
        self.api_url = 'https://texttospeech.googleapis.com/v1/text:synthesize'

    async def generate_speech(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """使用Google Cloud TTS生成语音"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'Google Cloud TTS API Key未配置'
                }

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 构建请求数据
            voice = kwargs.get('voice', 'cmn-CN-Wavenet-A')
            speed = kwargs.get('speed', 1.0)
            pitch = kwargs.get('pitch', 0)
            volume = kwargs.get('volume', 1.0)

            # 解析语音ID获取语言和性别
            if 'cmn-CN' in voice:
                language_code = 'cmn-CN'
            elif 'zh-CN' in voice:
                language_code = 'zh-CN'
            elif 'en-US' in voice:
                language_code = 'en-US'
            else:
                language_code = 'zh-CN'

            data = {
                'input': {
                    'ssml': f'''<speak>
                        <prosody rate="{speed}" pitch="{pitch:+.0f}%" volume="{volume}">
                            {text}
                        </prosody>
                    </speak>'''
                },
                'voice': {
                    'languageCode': language_code,
                    'name': voice
                },
                'audioConfig': {
                    'audioEncoding': 'MP3',
                    'speakingRate': speed,
                    'pitch': pitch,
                    'volumeGainDb': volume * 6 - 6  # 转换为dB
                }
            }

            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': self.api_key
            }

            # 发送请求
            response = requests.post(self.api_url, json=data, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()

                # 解码音频数据
                import base64
                audio_data = base64.b64decode(result['audioContent'])

                with open(output_path, 'wb') as f:
                    f.write(audio_data)

                logger.info(f"Google TTS语音生成成功: {output_path}")
                return {
                    'success': True,
                    'audio_file': output_path,
                    'engine': 'google_tts',
                    'voice': voice
                }
            else:
                return {
                    'success': False,
                    'error': f'Google TTS API请求失败: {response.status_code} - {response.text}'
                }

        except Exception as e:
            logger.error(f"Google TTS语音生成失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取可用音色列表"""
        return [
            # 中文WaveNet语音
            {'id': 'cmn-CN-Wavenet-A', 'name': '中文女声A (WaveNet)', 'language': 'cmn-CN'},
            {'id': 'cmn-CN-Wavenet-B', 'name': '中文男声B (WaveNet)', 'language': 'cmn-CN'},
            {'id': 'cmn-CN-Wavenet-C', 'name': '中文男声C (WaveNet)', 'language': 'cmn-CN'},
            {'id': 'cmn-CN-Wavenet-D', 'name': '中文女声D (WaveNet)', 'language': 'cmn-CN'},
            # 中文标准语音
            {'id': 'cmn-CN-Standard-A', 'name': '中文女声A (标准)', 'language': 'cmn-CN'},
            {'id': 'cmn-CN-Standard-B', 'name': '中文男声B (标准)', 'language': 'cmn-CN'},
            {'id': 'cmn-CN-Standard-C', 'name': '中文男声C (标准)', 'language': 'cmn-CN'},
            {'id': 'cmn-CN-Standard-D', 'name': '中文女声D (标准)', 'language': 'cmn-CN'},
            # 英文Neural2语音
            {'id': 'en-US-Neural2-A', 'name': '英文女声A (Neural2)', 'language': 'en-US'},
            {'id': 'en-US-Neural2-C', 'name': '英文女声C (Neural2)', 'language': 'en-US'},
            {'id': 'en-US-Neural2-D', 'name': '英文男声D (Neural2)', 'language': 'en-US'},
            {'id': 'en-US-Neural2-E', 'name': '英文女声E (Neural2)', 'language': 'en-US'},
            {'id': 'en-US-Neural2-F', 'name': '英文女声F (Neural2)', 'language': 'en-US'},
            {'id': 'en-US-Neural2-G', 'name': '英文女声G (Neural2)', 'language': 'en-US'},
            {'id': 'en-US-Neural2-H', 'name': '英文女声H (Neural2)', 'language': 'en-US'},
            {'id': 'en-US-Neural2-I', 'name': '英文男声I (Neural2)', 'language': 'en-US'},
            {'id': 'en-US-Neural2-J', 'name': '英文男声J (Neural2)', 'language': 'en-US'}
        ]

    def test_connection(self) -> Dict[str, Any]:
        """测试Google TTS连接"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'Google Cloud TTS API Key未配置'
                }

            # 发送测试请求
            test_data = {
                'input': {'text': '测试'},
                'voice': {
                    'languageCode': 'cmn-CN',
                    'name': 'cmn-CN-Wavenet-A'
                },
                'audioConfig': {
                    'audioEncoding': 'MP3'
                }
            }

            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': self.api_key
            }

            response = requests.post(self.api_url, json=test_data, headers=headers, timeout=10)

            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Google TTS连接正常'
                }
            else:
                return {
                    'success': False,
                    'error': f'Google TTS连接失败: {response.status_code}'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_default_settings(self) -> Dict[str, Any]:
        """获取Google TTS默认设置"""
        return {
            'voice': 'cmn-CN-Wavenet-A',
            'speed': 1.0,
            'pitch': 0,
            'volume': 1.0,
            'language': 'cmn-CN',
            'api_key': self.api_key
        }


class BaiduTTSEngine(TTSEngineBase):
    """百度智能云语音合成引擎"""

    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self.api_key = self.config_manager.get_setting('baidu_tts.api_key', '')
        self.secret_key = self.config_manager.get_setting('baidu_tts.secret_key', '')
        self.api_url = 'https://tsn.baidu.com/text2audio'
        self.token_url = 'https://aip.baidubce.com/oauth/2.0/token'
        self.access_token = None

    async def _get_access_token(self) -> Optional[str]:
        """获取百度API访问令牌"""
        try:
            if not all([self.api_key, self.secret_key]):
                return None

            params = {
                'grant_type': 'client_credentials',
                'client_id': self.api_key,
                'client_secret': self.secret_key
            }

            response = requests.post(self.token_url, params=params, timeout=10)

            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')
                return self.access_token
            else:
                logger.error(f"获取百度访问令牌失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"获取百度访问令牌异常: {e}")
            return None

    async def generate_speech(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """使用百度智能云生成语音"""
        try:
            if not all([self.api_key, self.secret_key]):
                return {
                    'success': False,
                    'error': '百度智能云API配置不完整'
                }

            # 获取访问令牌
            if not self.access_token:
                self.access_token = await self._get_access_token()

            if not self.access_token:
                return {
                    'success': False,
                    'error': '无法获取百度API访问令牌'
                }

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 构建请求数据
            voice = kwargs.get('voice', '4')  # 默认度丫丫
            speed = kwargs.get('speed', 1.0)
            pitch = kwargs.get('pitch', 0)
            volume = kwargs.get('volume', 1.0)
            emotion = kwargs.get('emotion', 'neutral')

            # 百度TTS参数映射
            per_map = {
                '0': '度小美-女声',
                '1': '度小宇-男声',
                '3': '度逍遥-男声',
                '4': '度丫丫-女声',
                '103': '度米朵-女声',
                '106': '度博文-男声',
                '110': '度小娇-女声',
                '111': '度小萌-女声'
            }

            data = {
                'tex': text,
                'tok': self.access_token,
                'cuid': 'video_creator',
                'ctp': '1',
                'lan': 'zh',
                'per': voice,
                'spd': int(speed * 5),  # 语速1-15
                'pit': int(pitch + 5),  # 音调0-15
                'vol': int(volume * 15),  # 音量0-15
                'aue': '3'  # MP3格式
            }

            # 发送请求
            response = requests.post(self.api_url, data=data, timeout=30)

            if response.status_code == 200:
                # 检查响应是否为音频数据
                content_type = response.headers.get('Content-Type', '')
                if 'audio' in content_type:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)

                    logger.info(f"百度TTS语音生成成功: {output_path}")
                    return {
                        'success': True,
                        'audio_file': output_path,
                        'engine': 'baidu_tts',
                        'voice': voice
                    }
                else:
                    # 可能是错误响应
                    try:
                        error_result = response.json()
                        return {
                            'success': False,
                            'error': f'百度TTS错误: {error_result.get("err_msg", "未知错误")}'
                        }
                    except:
                        return {
                            'success': False,
                            'error': '百度TTS返回非音频数据'
                        }
            else:
                return {
                    'success': False,
                    'error': f'百度TTS API请求失败: {response.status_code}'
                }

        except Exception as e:
            logger.error(f"百度TTS语音生成失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取可用音色列表"""
        return [
            # 基础音库
            {'id': '0', 'name': '度小美 (温柔女声)', 'language': 'zh-CN'},
            {'id': '1', 'name': '度小宇 (亲切男声)', 'language': 'zh-CN'},
            {'id': '3', 'name': '度逍遥 (磁性男声)', 'language': 'zh-CN'},
            {'id': '4', 'name': '度丫丫 (萌萌女声)', 'language': 'zh-CN'},
            # 精品音库
            {'id': '103', 'name': '度米朵 (温暖女声)', 'language': 'zh-CN'},
            {'id': '106', 'name': '度博文 (知性男声)', 'language': 'zh-CN'},
            {'id': '110', 'name': '度小娇 (甜美女声)', 'language': 'zh-CN'},
            {'id': '111', 'name': '度小萌 (萝莉女声)', 'language': 'zh-CN'},
            {'id': '5003', 'name': '度小鹿 (温柔女声)', 'language': 'zh-CN'},
            {'id': '5118', 'name': '度小雯 (知性女声)', 'language': 'zh-CN'}
        ]

    def test_connection(self) -> Dict[str, Any]:
        """测试百度TTS连接"""
        try:
            if not all([self.api_key, self.secret_key]):
                return {
                    'success': False,
                    'error': '百度智能云API配置不完整'
                }

            # 测试获取访问令牌
            import asyncio
            token = asyncio.run(self._get_access_token())

            if token:
                return {
                    'success': True,
                    'message': '百度TTS连接正常'
                }
            else:
                return {
                    'success': False,
                    'error': '百度TTS连接失败'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_default_settings(self) -> Dict[str, Any]:
        """获取百度TTS默认设置"""
        return {
            'voice': '4',
            'speed': 1.0,
            'pitch': 0,
            'volume': 1.0,
            'emotion': 'neutral',
            'language': 'zh-CN',
            'api_key': self.api_key,
            'secret_key': self.secret_key
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
            'azure_speech': AzureSpeechEngine(self.config_manager),
            'google_tts': GoogleTTSEngine(self.config_manager),
            'baidu_tts': BaiduTTSEngine(self.config_manager)
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
