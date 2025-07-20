# -*- coding: utf-8 -*-
"""
配音管理模块
负责处理AI配音相关的功能，包括语音生成、测试、批量处理等
"""

import os
import tempfile
import time
import platform
import subprocess
from typing import Dict, List, Any, Optional
from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5.QtCore import QObject, pyqtSignal

from src.utils.logger import logger
from src.utils.config_manager import ConfigManager
from src.audio_processing.tts_engine import TTSEngine


class VoiceManager(QObject):
    """配音管理器"""
    
    # 信号定义
    progress_updated = pyqtSignal(int)  # 进度更新
    status_updated = pyqtSignal(str)    # 状态更新
    voice_generated = pyqtSignal(dict)  # 配音生成完成
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.config_manager = ConfigManager()
        self.tts_engine = TTSEngine()
        
        # 语音列表缓存
        self.edge_voices = []
        self.siliconflow_voices = []
        
        # 加载语音模型列表
        self.load_voice_models()
        
        logger.info("配音管理器初始化完成")
    
    def load_voice_models(self) -> bool:
        """加载语音模型列表
        
        Returns:
            bool: 是否加载成功
        """
        try:
            logger.info("开始加载语音模型列表")
            
            from src.audio_processing.voice_lists import get_edge_voices, get_siliconflow_voices
            
            self.edge_voices = get_edge_voices()
            self.siliconflow_voices = get_siliconflow_voices()
            
            logger.info(f"语音模型加载成功 - Edge TTS: {len(self.edge_voices)}个, SiliconFlow: {len(self.siliconflow_voices)}个")
            return True
            
        except Exception as e:
            logger.error(f"加载语音模型列表失败: {e}")
            # 如果加载失败，使用默认列表
            self.edge_voices = ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-YunyangNeural"]
            self.siliconflow_voices = ["siliconflow:FunAudioLLM/CosyVoice2-0.5B:alex-Male"]
            logger.warning("使用默认语音模型列表")
            return False
    
    def get_voice_list(self, engine: str) -> List[str]:
        """获取指定引擎的语音列表
        
        Args:
            engine: TTS引擎名称 ("Edge TTS" 或 "SiliconFlow")
            
        Returns:
            List[str]: 语音列表
        """
        if engine == "Edge TTS":
            return self.edge_voices
        elif engine == "SiliconFlow":
            return self.siliconflow_voices
        else:
            logger.warning(f"未知的TTS引擎: {engine}")
            return []
    
    def test_voice_generation(self, engine: str, voice_model: str, voice_display: str, 
                            rate: int, pitch: int, test_text: str = None) -> Dict[str, Any]:
        """测试配音生成
        
        Args:
            engine: TTS引擎
            voice_model: 语音模型实际名称
            voice_display: 语音模型显示名称
            rate: 语速百分比
            pitch: 音调百分比
            test_text: 测试文本，如果为None则使用默认文本
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            if not test_text:
                test_text = "这是一个配音测试，用于验证当前配音设置是否正常工作。"
            
            logger.info(f"开始配音测试 - 引擎: {engine}, 模型: {voice_display}, 语速: {rate}%, 音调: {pitch}%")
            logger.debug(f"测试文本: {test_text}")
            
            if not voice_model:
                error_msg = "请先选择语音模型"
                logger.warning(error_msg)
                return {'success': False, 'error': error_msg}
            
            self.status_updated.emit(f"正在测试配音... 引擎: {engine}, 模型: {voice_display}")
            self.progress_updated.emit(10)
            
            # 生成临时音频文件
            # 使用简洁的文件名，不包含时间戳
            temp_dir = self.config_manager.get_temp_dir()
            output_file = os.path.join(temp_dir, f"voice_test.wav")
            
            logger.debug(f"临时音频文件路径: {output_file}")
            self.progress_updated.emit(30)
            
            # 转换语速和音调参数
            voice_rate = rate / 100.0  # 转换为0.25-4.0范围
            voice_volume = 1.0  # 默认音量
            
            logger.debug(f"TTS参数 - 语速: {voice_rate}, 音量: {voice_volume}")
            self.progress_updated.emit(50)
            
            # 调用TTS引擎生成语音
            result = self.tts_engine.generate_speech(
                text=test_text,
                voice_name=voice_model,
                voice_rate=voice_rate,
                voice_volume=voice_volume,
                voice_pitch=pitch,
                output_file=output_file
            )
            
            self.progress_updated.emit(80)
            
            if result.get('success'):
                self.progress_updated.emit(100)
                self.status_updated.emit("配音测试完成")
                
                # 检查文件是否生成成功
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    logger.info(f"配音测试成功 - 文件: {output_file}, 大小: {file_size} 字节")
                    
                    success_result = {
                        'success': True,
                        'output_file': output_file,
                        'file_size': file_size,
                        'engine': engine,
                        'voice_display': voice_display,
                        'voice_model': voice_model,
                        'rate': rate,
                        'pitch': pitch,
                        'test_text': test_text
                    }
                    
                    # 尝试播放音频文件
                    try:
                        self._play_audio_file(output_file)
                        logger.info("音频文件播放成功")
                    except Exception as play_error:
                        logger.warning(f"无法播放音频文件: {play_error}")
                    
                    return success_result
                else:
                    error_msg = "配音文件生成失败，请检查设置"
                    logger.error(error_msg)
                    self.status_updated.emit("配音文件生成失败")
                    return {'success': False, 'error': error_msg}
            else:
                error_msg = result.get('error', '未知错误')
                logger.error(f"配音测试失败: {error_msg}")
                self.progress_updated.emit(0)
                self.status_updated.emit(f"配音测试失败: {error_msg}")
                return {'success': False, 'error': error_msg}
            
        except Exception as e:
            error_msg = f"配音测试异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.progress_updated.emit(0)
            self.status_updated.emit("配音测试失败")
            return {'success': False, 'error': error_msg}
    
    def _play_audio_file(self, file_path: str):
        """播放音频文件
        
        Args:
            file_path: 音频文件路径
        """
        try:
            system = platform.system()
            logger.debug(f"尝试播放音频文件: {file_path}, 系统: {system}")
            
            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":  # macOS
                subprocess.call(["open", file_path])
            else:  # Linux
                subprocess.call(["xdg-open", file_path])
                
        except Exception as e:
            logger.warning(f"播放音频文件失败: {e}")
            raise
    
    def generate_voice_for_shot(self, text: str, voice_model: str, voice_display: str,
                               rate: int, pitch: int, output_dir: str, 
                               shot_index: int = None) -> Dict[str, Any]:
        """为单个分镜生成配音
        
        Args:
            text: 配音文本
            voice_model: 语音模型实际名称
            voice_display: 语音模型显示名称
            rate: 语速百分比
            pitch: 音调百分比
            output_dir: 输出目录
            shot_index: 分镜索引（可选）
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            if not text or not text.strip():
                error_msg = "配音文本为空"
                logger.warning(error_msg)
                return {'success': False, 'error': error_msg}
            
            if not voice_model:
                error_msg = "未指定语音模型"
                logger.warning(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 记录配音开始
            shot_info = f"第{shot_index + 1}行" if shot_index is not None else "单独"
            logger.info(f"开始为{shot_info}分镜生成配音")
            logger.info(f"配音参数 - 模型: {voice_display}, 语速: {rate}%, 音调: {pitch}%")
            logger.debug(f"配音文本: {text[:100]}{'...' if len(text) > 100 else ''}")
            
            # 确保输出目录存在
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                logger.debug(f"创建输出目录: {output_dir}")
            
            # 生成输出文件名
            # 使用简洁的文件名，不包含时间戳
            if shot_index is not None:
                audio_filename = f"voice_shot_{shot_index + 1}.wav"
            else:
                audio_filename = f"voice.wav"
            
            output_file = os.path.join(output_dir, audio_filename)
            logger.debug(f"输出文件路径: {output_file}")
            
            # 转换参数
            voice_rate = rate / 100.0
            voice_volume = 1.0
            
            # 调用TTS引擎生成语音
            result = self.tts_engine.generate_speech(
                text=text,
                voice_name=voice_model,
                voice_rate=voice_rate,
                voice_volume=voice_volume,
                voice_pitch=pitch,
                output_file=output_file
            )
            
            if result.get('success'):
                file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
                logger.info(f"{shot_info}分镜配音生成成功 - 文件: {output_file}, 大小: {file_size} 字节")
                
                return {
                    'success': True,
                    'audio_file': output_file,
                    'subtitle_file': result.get('subtitle_file'),
                    'engine': result.get('engine', 'unknown'),
                    'file_size': file_size,
                    'shot_index': shot_index
                }
            else:
                error_msg = result.get('error', '未知错误')
                logger.error(f"{shot_info}分镜配音生成失败: {error_msg}")
                return {'success': False, 'error': error_msg, 'shot_index': shot_index}
                
        except Exception as e:
            error_msg = f"配音生成异常: {str(e)}"
            shot_info = f"第{shot_index + 1}行" if shot_index is not None else "单独"
            logger.error(f"{shot_info}分镜{error_msg}", exc_info=True)
            return {'success': False, 'error': error_msg, 'shot_index': shot_index}
    
    def batch_generate_voices(self, shots_data: List[Dict], voice_model: str, 
                            voice_display: str, rate: int, pitch: int, 
                            output_dir: str) -> Dict[str, Any]:
        """批量生成配音
        
        Args:
            shots_data: 分镜数据列表
            voice_model: 语音模型实际名称
            voice_display: 语音模型显示名称
            rate: 语速百分比
            pitch: 音调百分比
            output_dir: 输出目录
            
        Returns:
            Dict[str, Any]: 批量生成结果
        """
        try:
            if not shots_data:
                error_msg = "没有分镜数据"
                logger.warning(error_msg)
                return {'success': False, 'error': error_msg}
            
            # 筛选有文本内容的分镜
            text_shots = [(i, shot) for i, shot in enumerate(shots_data) 
                         if shot.get('text', '').strip()]
            
            if not text_shots:
                error_msg = "没有找到需要配音的文本内容"
                logger.warning(error_msg)
                return {'success': False, 'error': error_msg}
            
            logger.info(f"开始批量配音 - 共{len(text_shots)}个分镜需要配音")
            logger.info(f"批量配音参数 - 模型: {voice_display}, 语速: {rate}%, 音调: {pitch}%")
            
            # 初始化结果统计
            total_count = len(text_shots)
            success_count = 0
            failed_count = 0
            results = []
            
            self.status_updated.emit(f"开始批量配音，共 {total_count} 个分镜...")
            
            # 逐个生成配音
            for i, (shot_index, shot) in enumerate(text_shots):
                try:
                    text = shot.get('text', '').strip()
                    
                    # 更新进度
                    progress = int((i / total_count) * 100)
                    self.progress_updated.emit(progress)
                    self.status_updated.emit(f"正在为第{shot_index + 1}行分镜生成配音... ({i + 1}/{total_count})")
                    
                    # 生成配音
                    result = self.generate_voice_for_shot(
                        text=text,
                        voice_model=voice_model,
                        voice_display=voice_display,
                        rate=rate,
                        pitch=pitch,
                        output_dir=output_dir,
                        shot_index=shot_index
                    )
                    
                    results.append(result)
                    
                    if result.get('success'):
                        success_count += 1
                        # 更新分镜数据中的配音文件路径
                        shot['voice_file'] = result['audio_file']
                        if result.get('subtitle_file'):
                            shot['subtitle_file'] = result['subtitle_file']
                    else:
                        failed_count += 1
                        logger.warning(f"第{shot_index + 1}行分镜配音失败: {result.get('error')}")
                    
                except Exception as e:
                    failed_count += 1
                    error_msg = f"第{shot_index + 1}行分镜配音异常: {str(e)}"
                    logger.error(error_msg)
                    results.append({
                        'success': False, 
                        'error': error_msg, 
                        'shot_index': shot_index
                    })
            
            # 完成批量配音
            self.progress_updated.emit(100)
            
            final_result = {
                'success': success_count > 0,
                'total_count': total_count,
                'success_count': success_count,
                'failed_count': failed_count,
                'results': results
            }
            
            if success_count > 0:
                status_msg = f"批量配音完成 - 成功: {success_count}, 失败: {failed_count}"
                logger.info(status_msg)
                self.status_updated.emit(status_msg)
            else:
                status_msg = "批量配音失败 - 所有分镜配音都失败了"
                logger.error(status_msg)
                self.status_updated.emit(status_msg)
            
            return final_result
            
        except Exception as e:
            error_msg = f"批量配音异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.status_updated.emit("批量配音失败")
            return {'success': False, 'error': error_msg}
    
    def clear_all_voices(self, shots_data: List[Dict]) -> bool:
        """清除所有配音
        
        Args:
            shots_data: 分镜数据列表
            
        Returns:
            bool: 是否清除成功
        """
        try:
            if not shots_data:
                logger.warning("没有分镜数据")
                return False
            
            logger.info("开始清除所有配音文件路径")
            
            # 清除配音文件路径
            cleared_count = 0
            for i, shot in enumerate(shots_data):
                if 'voice_file' in shot and shot['voice_file']:
                    shot['voice_file'] = ''
                    cleared_count += 1
                if 'subtitle_file' in shot and shot['subtitle_file']:
                    shot['subtitle_file'] = ''
            
            logger.info(f"已清除 {cleared_count} 个分镜的配音文件路径")
            self.status_updated.emit("已清除所有配音")
            
            return True
            
        except Exception as e:
            error_msg = f"清除配音失败: {str(e)}"
            logger.error(error_msg)
            return False
    
    def check_siliconflow_config(self) -> bool:
        """检查SiliconFlow配置
        
        Returns:
            bool: 配置是否完整
        """
        try:
            api_key = self.config_manager.get_tts_setting('siliconflow.api_key', '')
            if not api_key:
                logger.warning("SiliconFlow API Key未配置")
                return False
            
            logger.debug("SiliconFlow配置检查通过")
            return True
            
        except Exception as e:
            logger.error(f"检查SiliconFlow配置失败: {e}")
            return False