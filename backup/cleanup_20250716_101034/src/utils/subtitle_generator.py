"""
字幕生成工具
支持从配音生成字幕文件，包括SRT、VTT、JSON等格式
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SubtitleGenerator:
    """字幕生成器"""
    
    def __init__(self, project_root: str):
        """
        初始化字幕生成器
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root)
        self.subtitles_dir = self.project_root / "subtitles"
        self.subtitles_dir.mkdir(exist_ok=True)
        
    def generate_subtitle_from_voice_segment(self, 
                                           voice_segment: Dict[str, Any],
                                           subtitle_format: str = "srt") -> Optional[str]:
        """
        从配音段落生成字幕文件
        
        Args:
            voice_segment: 配音段落数据
            subtitle_format: 字幕格式 (srt/vtt/json)
            
        Returns:
            字幕文件路径，失败返回None
        """
        try:
            # 获取基本信息
            scene_id = voice_segment.get('scene_id', 'unknown_scene')
            shot_id = voice_segment.get('shot_id', 'unknown_shot')
            text = voice_segment.get('original_text', '') or voice_segment.get('dialogue_text', '')
            audio_path = voice_segment.get('audio_path', '')
            
            if not text.strip():
                logger.warning(f"配音段落 {scene_id}_{shot_id} 没有文本内容")
                return None
            
            # 获取音频时长
            duration = self._get_audio_duration(audio_path) if audio_path else 3.0
            
            # 生成字幕数据
            subtitle_data = self._create_subtitle_data(text, duration)
            
            # 生成文件名
            filename = f"{scene_id}_{shot_id}_subtitle.{subtitle_format}"
            subtitle_path = self.subtitles_dir / filename
            
            # 根据格式生成字幕文件
            if subtitle_format.lower() == "srt":
                success = self._generate_srt_file(subtitle_data, subtitle_path)
            elif subtitle_format.lower() == "vtt":
                success = self._generate_vtt_file(subtitle_data, subtitle_path)
            elif subtitle_format.lower() == "json":
                success = self._generate_json_file(subtitle_data, subtitle_path)
            else:
                logger.error(f"不支持的字幕格式: {subtitle_format}")
                return None
            
            if success:
                logger.info(f"字幕文件已生成: {subtitle_path}")
                return str(subtitle_path)
            else:
                return None
                
        except Exception as e:
            logger.error(f"生成字幕文件失败: {e}")
            return None
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频文件时长"""
        try:
            if not audio_path or not os.path.exists(audio_path):
                return 3.0  # 默认3秒
            
            # 尝试使用mutagen获取音频时长
            try:
                from mutagen import File
                audio_file = File(audio_path)
                if audio_file and hasattr(audio_file, 'info') and hasattr(audio_file.info, 'length'):
                    return float(audio_file.info.length)
            except ImportError:
                logger.debug("mutagen未安装，使用默认时长")
            except Exception as e:
                logger.debug(f"使用mutagen获取音频时长失败: {e}")
            
            # 备用方案：根据文件大小估算（粗略估算）
            file_size = os.path.getsize(audio_path)
            # 假设平均比特率为128kbps
            estimated_duration = file_size / (128 * 1024 / 8)  # 秒
            return max(1.0, min(estimated_duration, 30.0))  # 限制在1-30秒之间
            
        except Exception as e:
            logger.debug(f"获取音频时长失败: {e}")
            return 3.0
    
    def _create_subtitle_data(self, text: str, duration: float) -> List[Dict[str, Any]]:
        """创建字幕数据"""
        try:
            # 简单分句处理
            sentences = self._split_text_into_sentences(text)
            
            if not sentences:
                sentences = [text]
            
            subtitle_data = []
            sentence_duration = duration / len(sentences)
            
            for i, sentence in enumerate(sentences):
                start_time = i * sentence_duration
                end_time = (i + 1) * sentence_duration
                
                subtitle_data.append({
                    'index': i + 1,
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': sentence.strip(),
                    'start_time_str': self._seconds_to_timestamp(start_time),
                    'end_time_str': self._seconds_to_timestamp(end_time)
                })
            
            return subtitle_data
            
        except Exception as e:
            logger.error(f"创建字幕数据失败: {e}")
            return []
    
    def _split_text_into_sentences(self, text: str) -> List[str]:
        """将文本分割成句子"""
        try:
            # 中文句子分割
            sentences = re.split(r'[。！？；\n]', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # 如果句子太长，进一步分割
            final_sentences = []
            for sentence in sentences:
                if len(sentence) > 30:  # 超过30个字符的句子进一步分割
                    # 按逗号分割
                    sub_sentences = re.split(r'[，、]', sentence)
                    final_sentences.extend([s.strip() for s in sub_sentences if s.strip()])
                else:
                    final_sentences.append(sentence)
            
            return final_sentences
            
        except Exception as e:
            logger.error(f"分割句子失败: {e}")
            return [text]
    
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """将秒数转换为时间戳格式"""
        try:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            milliseconds = int((seconds % 1) * 1000)
            
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
            
        except Exception as e:
            logger.error(f"转换时间戳失败: {e}")
            return "00:00:00,000"
    
    def _generate_srt_file(self, subtitle_data: List[Dict[str, Any]], output_path: Path) -> bool:
        """生成SRT格式字幕文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for item in subtitle_data:
                    f.write(f"{item['index']}\n")
                    f.write(f"{item['start_time_str']} --> {item['end_time_str']}\n")
                    f.write(f"{item['text']}\n\n")
            
            return True
            
        except Exception as e:
            logger.error(f"生成SRT文件失败: {e}")
            return False
    
    def _generate_vtt_file(self, subtitle_data: List[Dict[str, Any]], output_path: Path) -> bool:
        """生成VTT格式字幕文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                
                for item in subtitle_data:
                    # VTT使用点号而不是逗号
                    start_time = item['start_time_str'].replace(',', '.')
                    end_time = item['end_time_str'].replace(',', '.')
                    
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{item['text']}\n\n")
            
            return True
            
        except Exception as e:
            logger.error(f"生成VTT文件失败: {e}")
            return False
    
    def _generate_json_file(self, subtitle_data: List[Dict[str, Any]], output_path: Path) -> bool:
        """生成JSON格式字幕文件"""
        try:
            json_data = {
                'format': 'json_subtitle',
                'version': '1.0',
                'created_at': datetime.now().isoformat(),
                'subtitles': subtitle_data
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"生成JSON文件失败: {e}")
            return False
    
    def batch_generate_subtitles(self, voice_segments: List[Dict[str, Any]], 
                                subtitle_format: str = "srt") -> Dict[str, Any]:
        """
        批量生成字幕文件
        
        Args:
            voice_segments: 配音段落列表
            subtitle_format: 字幕格式
            
        Returns:
            生成结果统计
        """
        try:
            results = {
                'success_count': 0,
                'failed_count': 0,
                'generated_files': [],
                'failed_segments': []
            }
            
            for segment in voice_segments:
                subtitle_path = self.generate_subtitle_from_voice_segment(segment, subtitle_format)
                
                if subtitle_path:
                    results['success_count'] += 1
                    results['generated_files'].append(subtitle_path)
                    
                    # 更新段落数据
                    segment['subtitle_path'] = subtitle_path
                    segment['subtitle_format'] = subtitle_format
                else:
                    results['failed_count'] += 1
                    results['failed_segments'].append(segment.get('shot_id', 'unknown'))
            
            logger.info(f"批量字幕生成完成: 成功 {results['success_count']} 个，失败 {results['failed_count']} 个")
            return results
            
        except Exception as e:
            logger.error(f"批量生成字幕失败: {e}")
            return {'success_count': 0, 'failed_count': len(voice_segments), 'generated_files': [], 'failed_segments': []}
    
    def cleanup_old_subtitles(self, days: int = 30) -> int:
        """清理旧的字幕文件"""
        try:
            if not self.subtitles_dir.exists():
                return 0
            
            cutoff_time = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            for subtitle_file in self.subtitles_dir.glob("*"):
                if subtitle_file.is_file():
                    file_time = datetime.fromtimestamp(subtitle_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        subtitle_file.unlink()
                        deleted_count += 1
                        logger.debug(f"已删除旧字幕文件: {subtitle_file}")
            
            logger.info(f"清理完成，删除了 {deleted_count} 个旧字幕文件")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理旧字幕文件失败: {e}")
            return 0
