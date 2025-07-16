#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS引擎模块
集成MoneyPrinterTurbo的语音合成功能，支持Edge TTS和SiliconFlow
"""

import os
import asyncio
import requests
from typing import Union, Optional, Dict, Any
from xml.sax.saxutils import unescape

try:
    import edge_tts
    from edge_tts import SubMaker
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    edge_tts = None
    SubMaker = None

from src.utils.logger import logger
from src.utils.config_manager import ConfigManager


class TTSEngine:
    """TTS语音合成引擎"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_tts_config()
    
    def generate_speech(
        self, 
        text: str, 
        voice_name: str, 
        voice_rate: float = 1.0,
        voice_volume: float = 1.0,
        voice_pitch: float = 0.0,
        output_file: str = None
    ) -> Dict[str, Any]:
        """
        生成语音
        
        Args:
            text: 要转换的文本
            voice_name: 语音名称
            voice_rate: 语速 (0.25-4.0)
            voice_volume: 音量 (0.6-5.0)
            voice_pitch: 音调 (-50 到 +50)
            output_file: 输出文件路径
            
        Returns:
            包含生成结果的字典
        """
        try:
            if not text or not text.strip():
                return {'success': False, 'error': '文本内容为空'}
            
            if not voice_name:
                return {'success': False, 'error': '未指定语音'}
            
            if not output_file:
                return {'success': False, 'error': '未指定输出文件'}
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 判断语音类型并调用相应的TTS引擎
            if self._is_siliconflow_voice(voice_name):
                return self._siliconflow_tts(
                    text, voice_name, voice_rate, voice_volume, voice_pitch, output_file
                )
            else:
                return self._edge_tts(
                    text, voice_name, voice_rate, voice_volume, voice_pitch, output_file
                )
                
        except Exception as e:
            logger.error(f"语音生成失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _is_siliconflow_voice(self, voice_name: str) -> bool:
        """判断是否为SiliconFlow语音"""
        return voice_name.startswith('siliconflow:')
    
    def _edge_tts(
        self, 
        text: str, 
        voice_name: str, 
        voice_rate: float,
        voice_volume: float,
        voice_pitch: float,
        output_file: str
    ) -> Dict[str, Any]:
        """Edge TTS语音合成"""
        if not EDGE_TTS_AVAILABLE:
            return {
                'success': False, 
                'error': 'Edge TTS未安装，请运行: pip install edge-tts'
            }
        
        try:
            # 解析语音名称
            parsed_voice = self._parse_voice_name(voice_name)
            
            # 转换语速为百分比格式
            rate_str = self._convert_rate_to_percent(voice_rate)
            # 转换音调为百分比格式
            pitch_str = self._convert_pitch_to_percent(voice_pitch)
            
            # 异步生成语音
            sub_maker = asyncio.run(self._edge_tts_async(
                text, parsed_voice, rate_str, pitch_str, output_file
            ))
            
            if not sub_maker:
                return {'success': False, 'error': 'Edge TTS生成失败'}
            
            # 生成字幕数据
            subtitle_data = self._generate_subtitle_from_submaker(sub_maker)
            
            return {
                'success': True,
                'audio_file': output_file,
                'subtitle_data': subtitle_data,
                'engine': 'edge_tts'
            }
            
        except Exception as e:
            logger.error(f"Edge TTS生成失败: {e}")
            return {'success': False, 'error': f'Edge TTS生成失败: {str(e)}'}
    
    async def _edge_tts_async(
        self,
        text: str,
        voice_name: str,
        rate_str: str,
        pitch_str: str,
        output_file: str
    ) -> Optional[SubMaker]:
        """异步Edge TTS生成"""
        try:
            communicate = edge_tts.Communicate(text, voice_name, rate=rate_str, pitch=pitch_str)
            sub_maker = edge_tts.SubMaker()

            with open(output_file, "wb") as file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        # Edge-TTS 7.0+ 使用新的API
                        sub_maker.feed(chunk)

            # Edge-TTS 7.0+ 需要调用merge_cues()来完成字幕生成
            # merge_cues()参数指定要合并的单词数量，1表示不合并
            if hasattr(sub_maker, 'merge_cues'):
                sub_maker.merge_cues(1)

            return sub_maker if (hasattr(sub_maker, 'cues') and len(sub_maker.cues) > 0) else None

        except Exception as e:
            logger.error(f"Edge TTS异步生成失败: {e}")
            return None
    
    def _siliconflow_tts(
        self, 
        text: str, 
        voice_name: str, 
        voice_rate: float,
        voice_volume: float,
        voice_pitch: float,
        output_file: str
    ) -> Dict[str, Any]:
        """SiliconFlow TTS语音合成"""
        try:
            # 获取API Key
            api_key = self.config_manager.get_tts_setting('siliconflow.api_key', '')
            if not api_key:
                return {
                    'success': False, 
                    'error': 'SiliconFlow API Key未配置，请在设置中配置'
                }
            
            # 解析语音参数
            model, voice = self._parse_siliconflow_voice(voice_name)
            if not model or not voice:
                return {
                    'success': False, 
                    'error': f'无效的SiliconFlow语音格式: {voice_name}'
                }
            
            # 转换音量为增益值
            gain = voice_volume - 1.0
            gain = max(-10, min(10, gain))
            
            # 构建请求
            url = "https://api.siliconflow.cn/v1/audio/speech"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "input": text,
                "voice": voice,
                "response_format": "mp3",
                "sample_rate": 32000,
                "stream": False,
                "speed": voice_rate,
                "gain": gain,
            }
            
            # 发送请求
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                # 保存音频文件
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                
                # SiliconFlow不提供字幕数据，生成简单的字幕
                subtitle_data = self._generate_simple_subtitle(text)
                
                return {
                    'success': True,
                    'audio_file': output_file,
                    'subtitle_data': subtitle_data,
                    'engine': 'siliconflow'
                }
            else:
                error_msg = f"SiliconFlow API错误: {response.status_code}"
                try:
                    error_detail = response.json().get('error', {}).get('message', '')
                    if error_detail:
                        error_msg += f" - {error_detail}"
                except:
                    pass
                
                return {'success': False, 'error': error_msg}
                
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'SiliconFlow API请求超时'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'SiliconFlow API请求失败: {str(e)}'}
        except Exception as e:
            logger.error(f"SiliconFlow TTS生成失败: {e}")
            return {'success': False, 'error': f'SiliconFlow TTS生成失败: {str(e)}'}
    
    def _parse_voice_name(self, voice_name: str) -> str:
        """解析语音名称"""
        # 移除可能的性别后缀
        if '-Female' in voice_name:
            return voice_name.replace('-Female', '')
        elif '-Male' in voice_name:
            return voice_name.replace('-Male', '')
        return voice_name
    
    def _parse_siliconflow_voice(self, voice_name: str) -> tuple:
        """解析SiliconFlow语音名称"""
        # 格式: siliconflow:model:voice-Gender
        try:
            parts = voice_name.split(':')
            if len(parts) >= 3:
                model = parts[1]
                voice_with_gender = parts[2]
                voice = voice_with_gender.split('-')[0]
                return model, f"{model}:{voice}"
            return None, None
        except Exception:
            return None, None
    
    def _convert_rate_to_percent(self, rate: float) -> str:
        """将语速转换为百分比格式"""
        if rate == 1.0:
            return "+0%"
        percent = round((rate - 1.0) * 100)
        if percent > 0:
            return f"+{percent}%"
        else:
            return f"{percent}%"
    
    def _convert_pitch_to_percent(self, pitch: float) -> str:
        """将音调转换为百分比格式"""
        if pitch == 0.0:
            return "+0Hz"
        # Edge TTS的pitch参数使用Hz单位，范围大约是-200Hz到+200Hz
        # 我们将-50到+50的范围映射到-200Hz到+200Hz
        hz_value = round(pitch * 4)  # 将-50到+50映射到-200到+200
        if hz_value > 0:
            return f"+{hz_value}Hz"
        else:
            return f"{hz_value}Hz"
    
    def _generate_subtitle_from_submaker(self, sub_maker) -> str:
        """从SubMaker生成SRT字幕"""
        try:
            if not sub_maker:
                return ""

            # Edge-TTS 7.0+ 版本的SubMaker可以直接转换为字符串格式的SRT
            if hasattr(sub_maker, 'cues') and len(sub_maker.cues) > 0:
                return str(sub_maker)
            else:
                return ""

        except Exception as e:
            logger.error(f"生成字幕失败: {e}")
            return ""
    
    def _generate_simple_subtitle(self, text: str) -> str:
        """生成简单的字幕（用于SiliconFlow）"""
        try:
            # 简单地将整个文本作为一个字幕条目
            return f"1\n00:00:00,000 --> 00:00:10,000\n{text}\n"
        except Exception:
            return ""
    
    def _format_timestamp(self, offset: int) -> str:
        """格式化时间戳为SRT格式"""
        try:
            # offset是以100纳秒为单位
            total_ms = offset // 10000
            hours = total_ms // 3600000
            minutes = (total_ms % 3600000) // 60000
            seconds = (total_ms % 60000) // 1000
            milliseconds = total_ms % 1000
            
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
        except Exception:
            return "00:00:00,000"
    
    def get_available_voices(self, engine: str = 'edge') -> list:
        """获取可用的语音列表"""
        try:
            if engine == 'edge':
                return self._get_edge_voices()
            elif engine == 'siliconflow':
                return self._get_siliconflow_voices()
            else:
                return []
        except Exception as e:
            logger.error(f"获取语音列表失败: {e}")
            return []
    
    def _get_edge_voices(self) -> list:
        """获取Edge TTS语音列表"""
        # 常用中文语音列表
        return [
            "zh-CN-XiaoxiaoNeural-Female",
            "zh-CN-YunxiNeural-Male", 
            "zh-CN-YunyangNeural-Male",
            "zh-CN-XiaoyiNeural-Female",
            "zh-CN-YunjianNeural-Male",
            "zh-CN-XiaochenNeural-Female",
            "zh-CN-XiaohanNeural-Female",
            "zh-CN-XiaomengNeural-Female",
            "zh-CN-XiaomoNeural-Female",
            "zh-CN-XiaoqiuNeural-Female",
            "zh-CN-XiaoruiNeural-Female",
            "zh-CN-XiaoshuangNeural-Female",
            "zh-CN-XiaoxuanNeural-Female",
            "zh-CN-XiaoyanNeural-Female",
            "zh-CN-XiaoyouNeural-Female",
            "zh-CN-XiaozhenNeural-Female",
            "zh-CN-YunfengNeural-Male",
            "zh-CN-YunhaoNeural-Male",
            "zh-CN-YunjieNeural-Male",
            "zh-CN-YunxiaNeural-Male",
            "zh-CN-YunyeNeural-Male",
            "zh-CN-YunzeNeural-Male"
        ]
    
    def _get_siliconflow_voices(self) -> list:
        """获取SiliconFlow语音列表"""
        return [
            "siliconflow:FunAudioLLM/CosyVoice2-0.5B:alex-Male",
            "siliconflow:FunAudioLLM/CosyVoice2-0.5B:anna-Female",
            "siliconflow:FunAudioLLM/CosyVoice2-0.5B:bella-Female",
            "siliconflow:FunAudioLLM/CosyVoice2-0.5B:benjamin-Male",
            "siliconflow:FunAudioLLM/CosyVoice2-0.5B:charles-Male",
            "siliconflow:FunAudioLLM/CosyVoice2-0.5B:claire-Female",
            "siliconflow:FunAudioLLM/CosyVoice2-0.5B:david-Male",
            "siliconflow:FunAudioLLM/CosyVoice2-0.5B:diana-Female",
        ]
    
    def test_engine(self, engine: str = 'edge') -> Dict[str, Any]:
        """测试TTS引擎"""
        try:
            if engine == 'edge':
                if not EDGE_TTS_AVAILABLE:
                    return {
                        'success': False, 
                        'error': 'Edge TTS未安装，请运行: pip install edge-tts'
                    }
                return {'success': True, 'message': 'Edge TTS可用'}
                
            elif engine == 'siliconflow':
                api_key = self.config_manager.get_tts_setting('siliconflow.api_key', '')
                if not api_key:
                    return {
                        'success': False, 
                        'error': 'SiliconFlow API Key未配置'
                    }
                return {'success': True, 'message': 'SiliconFlow配置正常'}
                
            else:
                return {'success': False, 'error': f'未知引擎: {engine}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}