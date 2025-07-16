"""
音频时长分析器
支持多种音频格式的时长检测和智能估算
"""

import os
import logging
import wave
import struct
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

class AudioDurationAnalyzer:
    """音频时长分析器"""
    
    def __init__(self):
        self.supported_formats = ['.wav', '.mp3', '.m4a', '.ogg', '.flac']
        self.text_speed_config = {
            'chinese_chars_per_second': 4.0,  # 中文每秒4字
            'english_words_per_second': 2.5,  # 英文每秒2.5词
            'min_duration': 1.0,  # 最短时长1秒
            'max_duration': 30.0,  # 最长时长30秒
            'pause_factor': 1.2,  # 停顿因子，实际时长会比理论时长长20%
        }
    
    def analyze_duration(self, audio_path: str, fallback_text: str = "") -> float:
        """
        分析音频时长
        
        Args:
            audio_path: 音频文件路径
            fallback_text: 备用文本，用于估算时长
            
        Returns:
            float: 音频时长（秒）
        """
        try:
            # 方法1：直接分析音频文件
            if audio_path and os.path.exists(audio_path):
                duration = self._analyze_audio_file(audio_path)
                if duration > 0:
                    logger.debug(f"从音频文件获取时长: {duration:.2f}秒 - {audio_path}")
                    return duration
            
            # 方法2：使用文本估算
            if fallback_text:
                duration = self._estimate_from_text(fallback_text)
                logger.debug(f"从文本估算时长: {duration:.2f}秒 - 文本长度: {len(fallback_text)}")
                return duration
            
            # 方法3：默认时长
            default_duration = 3.0
            logger.warning(f"无法分析时长，使用默认值: {default_duration}秒")
            return default_duration
            
        except Exception as e:
            logger.error(f"分析音频时长失败: {e}")
            return 3.0  # 默认3秒
    
    def _analyze_audio_file(self, audio_path: str) -> float:
        """分析音频文件获取精确时长"""
        try:
            file_ext = Path(audio_path).suffix.lower()
            
            if file_ext == '.wav':
                return self._analyze_wav_file(audio_path)
            elif file_ext == '.mp3':
                return self._analyze_mp3_file(audio_path)
            else:
                # 尝试使用通用方法
                return self._analyze_with_mutagen(audio_path)
                
        except Exception as e:
            logger.warning(f"分析音频文件失败: {e}")
            return 0.0
    
    def _analyze_wav_file(self, wav_path: str) -> float:
        """分析WAV文件时长"""
        try:
            with wave.open(wav_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration = frames / float(sample_rate)
                return duration
        except Exception as e:
            logger.warning(f"分析WAV文件失败: {e}")
            return 0.0
    
    def _analyze_mp3_file(self, mp3_path: str) -> float:
        """分析MP3文件时长（优先使用mutagen）"""
        try:
            # 优先使用mutagen获取精确时长
            duration = self._analyze_with_mutagen(mp3_path)
            if duration > 0:
                return duration

            # 降级方案：读取文件大小估算时长
            file_size = os.path.getsize(mp3_path)
            # 假设128kbps的MP3，1MB约为64秒
            estimated_duration = file_size / (128 * 1024 / 8)  # 转换为秒
            return min(estimated_duration, 60.0)  # 最多60秒
        except Exception as e:
            logger.warning(f"分析MP3文件失败: {e}")
            return 0.0
    
    def _analyze_with_mutagen(self, audio_path: str) -> float:
        """使用mutagen库分析音频时长"""
        try:
            from mutagen import File
            audio_file = File(audio_path)
            if audio_file and audio_file.info:
                return audio_file.info.length
        except ImportError:
            logger.debug("mutagen库未安装，跳过精确时长分析")
        except Exception as e:
            logger.warning(f"mutagen分析失败: {e}")
        return 0.0
    
    def _estimate_from_text(self, text: str) -> float:
        """根据文本内容估算配音时长"""
        if not text or not text.strip():
            return self.text_speed_config['min_duration']
        
        # 清理文本
        clean_text = text.strip()
        
        # 检测语言类型
        chinese_chars = sum(1 for char in clean_text if '\u4e00' <= char <= '\u9fff')
        english_words = len([word for word in clean_text.split() if word.isalpha()])
        
        # 计算基础时长
        if chinese_chars > english_words:
            # 主要是中文
            base_duration = chinese_chars / self.text_speed_config['chinese_chars_per_second']
        else:
            # 主要是英文
            base_duration = english_words / self.text_speed_config['english_words_per_second']
        
        # 应用停顿因子
        estimated_duration = base_duration * self.text_speed_config['pause_factor']
        
        # 限制在合理范围内
        estimated_duration = max(
            self.text_speed_config['min_duration'],
            min(estimated_duration, self.text_speed_config['max_duration'])
        )
        
        return estimated_duration
    
    def batch_analyze(self, audio_data_list: list) -> Dict[int, float]:
        """
        批量分析音频时长
        
        Args:
            audio_data_list: 音频数据列表，每个元素包含audio_path和text字段
            
        Returns:
            Dict[int, float]: 索引到时长的映射
        """
        results = {}
        
        for i, audio_data in enumerate(audio_data_list):
            audio_path = audio_data.get('audio_path', '')
            text = audio_data.get('dialogue_text', '') or audio_data.get('text', '')
            
            duration = self.analyze_duration(audio_path, text)
            results[i] = duration
            
            logger.debug(f"音频 {i}: {duration:.2f}秒")
        
        total_duration = sum(results.values())
        logger.info(f"批量分析完成，共 {len(results)} 个音频，总时长: {total_duration:.2f}秒")
        
        return results
    
    def calculate_image_requirements(self, duration_map: Dict[int, float]) -> Dict[int, Dict[str, Any]]:
        """
        根据时长计算图像生成需求
        
        Args:
            duration_map: 音频索引到时长的映射
            
        Returns:
            Dict[int, Dict]: 音频索引到图像需求的映射
        """
        image_requirements = {}
        
        for audio_index, duration in duration_map.items():
            # 计算需要的图片数量
            if duration <= 3.0:
                image_count = 1
            elif duration <= 6.0:
                image_count = 2
            else:
                # 每3秒1张图，最少2张
                image_count = max(2, int(duration / 3.0))
            
            # 计算每张图的时间覆盖
            time_per_image = duration / image_count
            images = []
            
            for img_idx in range(image_count):
                start_time = img_idx * time_per_image
                end_time = (img_idx + 1) * time_per_image
                
                images.append({
                    'image_index': img_idx,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': time_per_image
                })
            
            image_requirements[audio_index] = {
                'audio_duration': duration,
                'image_count': image_count,
                'images': images
            }
            
            logger.debug(f"音频 {audio_index}: {duration:.2f}秒 -> {image_count}张图片")
        
        total_images = sum(req['image_count'] for req in image_requirements.values())
        logger.info(f"图像需求计算完成，共需生成 {total_images} 张图片")
        
        return image_requirements
    
    def export_analysis_report(self, duration_map: Dict[int, float], 
                             image_requirements: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """导出分析报告"""
        total_duration = sum(duration_map.values())
        total_images = sum(req['image_count'] for req in image_requirements.values())
        
        # 统计时长分布
        duration_distribution = {
            'short_segments': len([d for d in duration_map.values() if d <= 3.0]),
            'medium_segments': len([d for d in duration_map.values() if 3.0 < d <= 6.0]),
            'long_segments': len([d for d in duration_map.values() if d > 6.0])
        }
        
        report = {
            'summary': {
                'total_segments': len(duration_map),
                'total_duration': total_duration,
                'average_duration': total_duration / len(duration_map) if duration_map else 0,
                'total_images_required': total_images,
                'images_per_segment_ratio': total_images / len(duration_map) if duration_map else 0
            },
            'duration_distribution': duration_distribution,
            'detailed_requirements': image_requirements,
            'recommendations': self._generate_recommendations(duration_map, image_requirements)
        }
        
        return report
    
    def _generate_recommendations(self, duration_map: Dict[int, float], 
                                image_requirements: Dict[int, Dict[str, Any]]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 检查时长分布
        short_count = len([d for d in duration_map.values() if d <= 2.0])
        long_count = len([d for d in duration_map.values() if d > 10.0])
        
        if short_count > len(duration_map) * 0.3:
            recommendations.append("建议合并过短的配音段落以提高视觉连贯性")
        
        if long_count > 0:
            recommendations.append("建议为较长的配音段落增加更多图片变化以保持观众注意力")
        
        # 检查图片数量
        total_images = sum(req['image_count'] for req in image_requirements.values())
        if total_images > 50:
            recommendations.append("图片数量较多，建议考虑生成时间和存储空间")
        
        return recommendations
