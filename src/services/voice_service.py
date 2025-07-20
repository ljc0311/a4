#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音服务
统一的语音合成和识别服务，支持多种提供商
"""

import json
import aiohttp
import asyncio
import base64
import io
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from src.utils.logger import logger
from src.core.service_base import ServiceBase, ServiceResult
from src.core.api_manager import APIManager, APIConfig, APIType

class VoiceService(ServiceBase):
    """语音服务类"""
    
    def __init__(self, api_manager: APIManager):
        super().__init__(api_manager, "语音服务")
        
        # 从配置管理器获取语音配置
        self.voice_config = api_manager.config_manager.get_voice_config() if hasattr(api_manager, 'config_manager') else {}
        
        # 支持的音色配置
        self.voice_configs = {
            'azure': {
                '中文女声': 'zh-CN-XiaoxiaoNeural',
                '中文男声': 'zh-CN-YunxiNeural',
                '英文女声': 'en-US-AriaNeural',
                '英文男声': 'en-US-GuyNeural'
            },
            'elevenlabs': {
                '中文女声': 'zh-CN-female-1',
                '中文男声': 'zh-CN-male-1',
                '英文女声': 'en-US-female-1',
                '英文男声': 'en-US-male-1'
            },
            'openai': {
                '女声1': 'alloy',
                '女声2': 'nova',
                '男声1': 'echo',
                '男声2': 'onyx'
            }
        }
        
        # 默认参数
        self.default_tts_params = {
            'speed': 1.0,
            'pitch': 0,
            'volume': 1.0,
            'format': 'mp3'
        }
    
    def get_api_type(self) -> APIType:
        return APIType.TEXT_TO_SPEECH
    
    def get_available_providers(self) -> List[str]:
        """获取可用的语音提供商"""
        if hasattr(self.api_manager, 'config_manager'):
            return self.api_manager.config_manager.get_voice_providers()
        return ['edge_tts']  # 默认提供商
    
    async def _execute_request(self, api_config: APIConfig, **kwargs) -> ServiceResult:
        """执行语音API请求"""
        try:
            task_type = kwargs.get('task_type', 'tts')  # tts 或 stt
            
            if task_type == 'tts':
                return await self._execute_tts_request(api_config, **kwargs)
            elif task_type == 'stt':
                return await self._execute_stt_request(api_config, **kwargs)
            else:
                return ServiceResult(success=False, error=f"不支持的任务类型: {task_type}")
                
        except Exception as e:
            logger.error(f"语音API请求失败: {e}")
            return ServiceResult(success=False, error=str(e))
    
    async def _execute_tts_request(self, api_config: APIConfig, **kwargs) -> ServiceResult:
        """执行TTS请求"""
        text = kwargs.get('text', '')
        voice = kwargs.get('voice', '中文女声')
        
        if not text:
            return ServiceResult(success=False, error="文本不能为空")
        
        # 根据不同提供商调用TTS API
        if api_config.provider.lower() == 'azure':
            response = await self._call_azure_tts(api_config, text, voice, **kwargs)
        elif api_config.provider.lower() == 'elevenlabs':
            response = await self._call_elevenlabs_tts(api_config, text, voice, **kwargs)
        elif api_config.provider.lower() == 'openai':
            response = await self._call_openai_tts(api_config, text, voice, **kwargs)
        elif api_config.provider.lower() == 'local':
            response = await self._call_local_tts(api_config, text, voice, **kwargs)
        else:
            return ServiceResult(success=False, error=f"不支持的TTS提供商: {api_config.provider}")
        
        return ServiceResult(
            success=True,
            data=response,
            metadata={
                'provider': api_config.provider,
                'voice': voice,
                'text_length': len(text)
            }
        )
    
    async def _execute_stt_request(self, api_config: APIConfig, **kwargs) -> ServiceResult:
        """执行STT请求"""
        audio_data = kwargs.get('audio_data')
        language = kwargs.get('language', 'zh-CN')
        
        if not audio_data:
            return ServiceResult(success=False, error="音频数据不能为空")
        
        # 根据不同提供商调用STT API
        if api_config.provider.lower() == 'azure':
            response = await self._call_azure_stt(api_config, audio_data, language, **kwargs)
        elif api_config.provider.lower() == 'openai':
            response = await self._call_openai_stt(api_config, audio_data, language, **kwargs)
        else:
            return ServiceResult(success=False, error=f"不支持的STT提供商: {api_config.provider}")
        
        return ServiceResult(
            success=True,
            data=response,
            metadata={
                'provider': api_config.provider,
                'language': language
            }
        )
    
    async def _call_azure_tts(self, api_config: APIConfig, text: str, voice: str, **kwargs) -> Dict:
        """调用Azure TTS API"""
        # 获取Azure音色名称
        voice_name = self.voice_configs.get('azure', {}).get(voice, 'zh-CN-XiaoxiaoNeural')
        
        # 构建SSML
        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='zh-CN'>
            <voice name='{voice_name}'>
                <prosody rate='{kwargs.get("speed", 1.0)}' pitch='{kwargs.get("pitch", 0)}%'>
                    {text}
                </prosody>
            </voice>
        </speak>
        """
        
        headers = {
            'Ocp-Apim-Subscription-Key': api_config.api_key,
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'audio-16khz-128kbitrate-mono-mp3'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_config.api_url}/cognitiveservices/v1",
                headers=headers,
                data=ssml.encode('utf-8'),
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    
                    return {
                        'audio_data': audio_base64,
                        'format': 'mp3',
                        'voice': voice_name
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Azure TTS请求失败 (状态码: {response.status}): {error_text}")
    
    async def _call_elevenlabs_tts(self, api_config: APIConfig, text: str, voice: str, **kwargs) -> Dict:
        """调用ElevenLabs TTS API"""
        voice_id = self.voice_configs.get('elevenlabs', {}).get(voice, 'zh-CN-female-1')
        
        headers = {
            'xi-api-key': api_config.api_key,
            'Content-Type': 'application/json'
        }
        
        data = {
            'text': text,
            'voice_settings': {
                'stability': 0.5,
                'similarity_boost': 0.5,
                'style': kwargs.get('style', 0.0),
                'use_speaker_boost': True
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_config.api_url}/v1/text-to-speech/{voice_id}",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    
                    return {
                        'audio_data': audio_base64,
                        'format': 'mp3',
                        'voice': voice_id
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"ElevenLabs TTS请求失败 (状态码: {response.status}): {error_text}")
    
    async def _call_openai_tts(self, api_config: APIConfig, text: str, voice: str, **kwargs) -> Dict:
        """调用OpenAI TTS API"""
        voice_name = self.voice_configs.get('openai', {}).get(voice, 'alloy')
        
        headers = {
            'Authorization': f'Bearer {api_config.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'tts-1',
            'input': text,
            'voice': voice_name,
            'speed': kwargs.get('speed', 1.0)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_config.api_url}/v1/audio/speech",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    
                    return {
                        'audio_data': audio_base64,
                        'format': 'mp3',
                        'voice': voice_name
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI TTS请求失败 (状态码: {response.status}): {error_text}")
    
    async def _call_local_tts(self, api_config: APIConfig, text: str, voice: str, **kwargs) -> Dict:
        """调用本地TTS（如pyttsx3）"""
        try:
            import pyttsx3
            import tempfile
            import os
            
            # 创建TTS引擎
            engine = pyttsx3.init()
            
            # 设置语音参数
            voices = engine.getProperty('voices')
            if voices:
                # 根据voice参数选择合适的语音
                if '女声' in voice and len(voices) > 1:
                    engine.setProperty('voice', voices[1].id)
                else:
                    engine.setProperty('voice', voices[0].id)
            
            engine.setProperty('rate', int(200 * kwargs.get('speed', 1.0)))
            engine.setProperty('volume', kwargs.get('volume', 1.0))
            
            # 生成音频文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            engine.save_to_file(text, temp_path)
            engine.runAndWait()
            
            # 读取音频数据
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            # 清理临时文件
            os.unlink(temp_path)
            
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return {
                'audio_data': audio_base64,
                'format': 'wav',
                'voice': voice
            }
            
        except ImportError:
            raise Exception("本地TTS需要安装pyttsx3库")
        except Exception as e:
            raise Exception(f"本地TTS生成失败: {e}")
    
    async def _call_azure_stt(self, api_config: APIConfig, audio_data: bytes, language: str, **kwargs) -> Dict:
        """调用Azure STT API"""
        headers = {
            'Ocp-Apim-Subscription-Key': api_config.api_key,
            'Content-Type': 'audio/wav'
        }
        
        params = {
            'language': language,
            'format': 'simple'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_config.api_url}/speechtotext/v3.0/transcriptions:transcribe",
                headers=headers,
                params=params,
                data=audio_data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        'text': result.get('DisplayText', ''),
                        'confidence': result.get('Confidence', 0.0)
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Azure STT请求失败 (状态码: {response.status}): {error_text}")
    
    async def _call_openai_stt(self, api_config: APIConfig, audio_data: bytes, language: str, **kwargs) -> Dict:
        """调用OpenAI Whisper API"""
        headers = {
            'Authorization': f'Bearer {api_config.api_key}'
        }
        
        # 创建multipart form data
        data = aiohttp.FormData()
        data.add_field('file', audio_data, filename='audio.wav', content_type='audio/wav')
        data.add_field('model', 'whisper-1')
        data.add_field('language', language[:2])  # 只取前两位语言代码
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_config.api_url}/v1/audio/transcriptions",
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        'text': result.get('text', ''),
                        'confidence': 1.0  # Whisper不返回置信度
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI STT请求失败 (状态码: {response.status}): {error_text}")
    
    async def text_to_speech(self, text: str, voice: str = "中文女声", provider: str = None, **kwargs) -> ServiceResult:
        """文本转语音"""
        return await self.execute(
            provider=provider,
            task_type='tts',
            text=text,
            voice=voice,
            **kwargs
        )
    
    async def speech_to_text(self, audio_data: bytes, language: str = None, provider: str = None, **kwargs) -> ServiceResult:
        """语音转文字"""
        try:
            # 如果没有指定语言，从配置中获取默认语言
            if language is None:
                from src.utils.config_manager import ConfigManager
                config_manager = ConfigManager()
                language = config_manager.get_setting("default_language", "zh-CN")
            
            return await self.execute(
                provider=provider,
                task_type='stt',
                audio_data=audio_data,
                language=language,
                **kwargs
            )
                
        except Exception as e:
            logger.error(f"语音转文字失败: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="语音转文字失败"
            )
    
    async def batch_text_to_speech(self, texts: List[str], voice: str = "中文女声", 
                                 provider: str = None, **kwargs) -> List[ServiceResult]:
        """批量文本转语音"""
        tasks = []
        for text in texts:
            task = self.text_to_speech(
                text=text,
                voice=voice,
                provider=provider,
                **kwargs
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ServiceResult(
                    success=False,
                    error=str(result),
                    metadata={'text_index': i}
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_available_voices(self, provider: str = None) -> Dict[str, List[str]]:
        """获取可用的音色列表"""
        if provider:
            return {provider: list(self.voice_configs.get(provider, {}).keys())}
        else:
            return {p: list(voices.keys()) for p, voices in self.voice_configs.items()}
    
    def add_voice_config(self, provider: str, voice_name: str, voice_id: str):
        """添加音色配置"""
        if provider not in self.voice_configs:
            self.voice_configs[provider] = {}
        
        self.voice_configs[provider][voice_name] = voice_id
        logger.info(f"已添加音色配置: {provider} - {voice_name}")