"""
同步问题修复脚本
解决配音时长检测错误、段落数量变化、描述内容错误等问题
"""

import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from src.utils.logger import logger
from src.utils.audio_duration_analyzer import AudioDurationAnalyzer


class SyncIssuesFixer:
    """同步问题修复器"""
    
    def __init__(self, project_manager=None):
        self.project_manager = project_manager
        self.audio_analyzer = AudioDurationAnalyzer()
    
    def fix_audio_duration_detection(self, project_data: Dict[str, Any]) -> bool:
        """修复音频时长检测错误"""
        try:
            logger.info("开始修复音频时长检测问题...")
            
            voice_generation = project_data.get('voice_generation', {})
            generated_audio = voice_generation.get('generated_audio', [])
            voice_segments = voice_generation.get('voice_segments', [])
            
            # 修复生成的音频时长
            fixed_audio = []
            for audio_data in generated_audio:
                audio_path = audio_data.get('audio_path', '')
                if audio_path and os.path.exists(audio_path):
                    # 重新分析真实时长
                    real_duration = self._get_real_audio_duration(audio_path)
                    if real_duration > 0:
                        audio_data['duration'] = real_duration
                        logger.info(f"修复音频时长: {audio_path} -> {real_duration:.2f}秒")
                
                fixed_audio.append(audio_data)
            
            # 修复配音段落时长
            fixed_segments = []
            for segment in voice_segments:
                audio_path = segment.get('audio_path', '')
                if audio_path and os.path.exists(audio_path):
                    # 重新分析真实时长
                    real_duration = self._get_real_audio_duration(audio_path)
                    if real_duration > 0:
                        segment['duration'] = real_duration
                        logger.info(f"修复段落时长: {segment.get('shot_id', 'Unknown')} -> {real_duration:.2f}秒")
                
                fixed_segments.append(segment)
            
            # 更新项目数据
            voice_generation['generated_audio'] = fixed_audio
            voice_generation['voice_segments'] = fixed_segments
            project_data['voice_generation'] = voice_generation
            
            logger.info("音频时长检测修复完成")
            return True
            
        except Exception as e:
            logger.error(f"修复音频时长检测失败: {e}")
            return False
    
    def fix_segment_count_changes(self, project_data: Dict[str, Any]) -> bool:
        """修复配音段落数量变化问题"""
        try:
            logger.info("开始修复配音段落数量变化问题...")
            
            # 检查是否存在自动数量调整
            voice_generation = project_data.get('voice_generation', {})
            voice_segments = voice_generation.get('voice_segments', [])
            
            # 获取原始文本段落数量
            original_text = project_data.get('original_text', '')
            if original_text:
                original_paragraphs = self._split_text_to_paragraphs(original_text)
                original_count = len(original_paragraphs)
                current_count = len(voice_segments)
                
                logger.info(f"原始段落数: {original_count}, 当前段落数: {current_count}")
                
                if current_count != original_count:
                    # 恢复到原始段落数量
                    logger.info(f"检测到段落数量变化，恢复到原始数量: {original_count}")
                    restored_segments = self._restore_original_segments(
                        original_paragraphs, voice_segments
                    )
                    voice_generation['voice_segments'] = restored_segments
                    project_data['voice_generation'] = voice_generation
                    
                    # 添加标记，防止自动调整
                    voice_generation['preserve_segment_count'] = True
            
            logger.info("配音段落数量修复完成")
            return True
            
        except Exception as e:
            logger.error(f"修复配音段落数量失败: {e}")
            return False
    
    def fix_description_content_errors(self, project_data: Dict[str, Any]) -> bool:
        """修复描述内容错误"""
        try:
            logger.info("开始修复描述内容错误...")
            
            # 修复图像生成中的描述内容
            image_generation = project_data.get('image_generation', {})
            generated_images = image_generation.get('generated_images', [])
            
            # 获取配音内容作为参考
            voice_generation = project_data.get('voice_generation', {})
            voice_segments = voice_generation.get('voice_segments', [])
            
            # 创建配音内容映射
            voice_content_map = {}
            for segment in voice_segments:
                shot_id = segment.get('shot_id', '')
                content = segment.get('original_text', segment.get('dialogue_text', ''))
                if shot_id and content:
                    voice_content_map[shot_id] = content
            
            # 修复图像描述
            fixed_images = []
            for image_data in generated_images:
                shot_id = image_data.get('shot_id', '')
                if shot_id in voice_content_map:
                    voice_content = voice_content_map[shot_id]
                    
                    # 重新生成匹配的描述
                    new_description = self._generate_matched_description(voice_content)
                    if new_description:
                        image_data['consistency_description'] = new_description
                        image_data['enhanced_description'] = new_description
                        logger.info(f"修复描述内容: {shot_id}")
                
                fixed_images.append(image_data)
            
            image_generation['generated_images'] = fixed_images
            project_data['image_generation'] = image_generation
            
            logger.info("描述内容错误修复完成")
            return True
            
        except Exception as e:
            logger.error(f"修复描述内容错误失败: {e}")
            return False
    
    def fix_voice_time_image_generation(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """修复按配音时间生成图像功能"""
        try:
            logger.info("开始修复按配音时间生成图像功能...")
            
            voice_generation = project_data.get('voice_generation', {})
            voice_segments = voice_generation.get('voice_segments', [])
            
            if not voice_segments:
                logger.warning("没有配音段落数据")
                return {}
            
            # 分析每个配音段落的时长
            duration_analysis = {}
            total_duration = 0
            
            for i, segment in enumerate(voice_segments):
                audio_path = segment.get('audio_path', '')
                dialogue_text = segment.get('dialogue_text', segment.get('original_text', ''))
                
                # 获取真实时长
                if audio_path and os.path.exists(audio_path):
                    duration = self._get_real_audio_duration(audio_path)
                else:
                    # 根据文本估算时长
                    duration = self._estimate_duration_from_text(dialogue_text)
                
                duration_analysis[i] = {
                    'segment_index': i,
                    'shot_id': segment.get('shot_id', f'镜头{i+1}'),
                    'scene_id': segment.get('scene_id', f'场景{(i//3)+1}'),
                    'duration': duration,
                    'content': dialogue_text,
                    'audio_path': audio_path
                }
                
                total_duration += duration
            
            # 计算图像需求
            image_requirements = []
            total_images = 0
            
            for i, analysis in duration_analysis.items():
                duration = analysis['duration']
                
                # 根据时长计算图像数量
                if duration <= 3.0:
                    image_count = 1
                elif duration <= 6.0:
                    image_count = 2
                else:
                    image_count = max(2, int(duration / 3.0))
                
                # 生成图像需求
                for img_idx in range(image_count):
                    image_req = {
                        'segment_index': i,
                        'image_index': img_idx,
                        'shot_id': f"{analysis['shot_id']}_{img_idx+1}" if image_count > 1 else analysis['shot_id'],
                        'scene_id': analysis['scene_id'],
                        'content': analysis['content'],
                        'duration_start': img_idx * (duration / image_count),
                        'duration_end': (img_idx + 1) * (duration / image_count),
                        'description': self._generate_matched_description(analysis['content'])
                    }
                    image_requirements.append(image_req)
                    total_images += 1
            
            result = {
                'voice_segments_count': len(voice_segments),
                'total_voice_duration': total_duration,
                'recommended_images_count': total_images,
                'duration_analysis': duration_analysis,
                'image_requirements': image_requirements,
                'analysis_summary': {
                    'short_segments': len([d for d in duration_analysis.values() if d['duration'] <= 3.0]),
                    'medium_segments': len([d for d in duration_analysis.values() if 3.0 < d['duration'] <= 6.0]),
                    'long_segments': len([d for d in duration_analysis.values() if d['duration'] > 6.0]),
                    'average_duration': total_duration / len(voice_segments) if voice_segments else 0
                }
            }
            
            logger.info(f"按配音时间生成图像分析完成: {len(voice_segments)}段配音 -> {total_images}张图像")
            return result
            
        except Exception as e:
            logger.error(f"修复按配音时间生成图像功能失败: {e}")
            return {}
    
    def _get_real_audio_duration(self, audio_path: str) -> float:
        """获取真实音频时长"""
        try:
            if not audio_path or not os.path.exists(audio_path):
                return 0.0
            
            # 使用音频分析器获取精确时长
            duration = self.audio_analyzer.analyze_duration(audio_path)
            return duration
            
        except Exception as e:
            logger.error(f"获取音频时长失败: {e}")
            return 0.0
    
    def _estimate_duration_from_text(self, text: str) -> float:
        """根据文本估算时长"""
        if not text:
            return 3.0
        
        # 中文每秒4字，英文每秒2.5词
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        english_words = len([word for word in text.split() if word.isalpha()])
        
        if chinese_chars > english_words:
            duration = chinese_chars / 4.0
        else:
            duration = english_words / 2.5
        
        # 应用停顿因子和限制范围
        duration = duration * 1.2  # 停顿因子
        return max(1.0, min(duration, 30.0))
    
    def _split_text_to_paragraphs(self, text: str) -> List[str]:
        """将文本分割为段落"""
        if not text:
            return []
        
        # 按换行符分割
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        # 如果没有换行符，按句号分割
        if len(paragraphs) == 1:
            sentences = [s.strip() for s in text.split('。') if s.strip()]
            if len(sentences) > 1:
                paragraphs = [s + '。' if not s.endswith('。') else s for s in sentences]
        
        return paragraphs
    
    def _restore_original_segments(self, original_paragraphs: List[str], 
                                 current_segments: List[Dict]) -> List[Dict]:
        """恢复到原始段落数量"""
        restored_segments = []
        
        for i, paragraph in enumerate(original_paragraphs):
            # 尝试找到匹配的现有段落
            matched_segment = None
            for segment in current_segments:
                if paragraph in segment.get('original_text', '') or \
                   segment.get('original_text', '') in paragraph:
                    matched_segment = segment
                    break
            
            if matched_segment:
                # 使用匹配的段落
                segment = matched_segment.copy()
                segment['original_text'] = paragraph
                segment['dialogue_text'] = paragraph
            else:
                # 创建新段落
                segment = {
                    'index': i,
                    'scene_id': f'场景{(i//3)+1}',
                    'shot_id': f'镜头{i+1}',
                    'original_text': paragraph,
                    'dialogue_text': paragraph,
                    'sound_effect': '',
                    'status': '未生成',
                    'audio_path': ''
                }
            
            restored_segments.append(segment)
        
        return restored_segments
    
    def _generate_matched_description(self, content: str) -> str:
        """生成匹配的描述"""
        if not content:
            return "根据内容生成画面"
        
        # 简单的描述生成逻辑
        # 实际应该使用LLM或更复杂的算法
        return f"根据内容生成画面: {content[:50]}{'...' if len(content) > 50 else ''}, 高质量, 细节丰富"
