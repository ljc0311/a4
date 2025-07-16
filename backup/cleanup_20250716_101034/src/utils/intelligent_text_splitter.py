"""
智能文本分割器
根据目标时长智能分割文本，保持语义完整性和自然断句
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextSegment:
    """文本段落数据结构"""
    content: str
    estimated_duration: float
    start_index: int
    end_index: int
    segment_type: str  # 'paragraph', 'sentence_group', 'sentence', 'phrase'
    quality_score: float  # 语义完整性评分 (0-1)


@dataclass
class SplitConfig:
    """分割配置"""
    target_duration: float = 10.0  # 目标时长（秒）
    min_duration: float = 5.0      # 最小时长（秒）
    max_duration: float = 15.0     # 最大时长（秒）
    tolerance: float = 2.0         # 容忍范围（秒）
    chinese_chars_per_second: float = 4.0  # 中文每秒字数
    english_words_per_second: float = 2.5  # 英文每秒词数
    pause_factor: float = 1.2      # 停顿因子


class IntelligentTextSplitter:
    """智能文本分割器"""
    
    def __init__(self, config: Optional[SplitConfig] = None):
        self.config = config or SplitConfig()
        
        # 语言停顿点权重（数值越高，越适合作为分割点）
        self.punctuation_weights = {
            '。': 1.0,   # 句号 - 最佳分割点
            '！': 1.0,   # 感叹号
            '？': 1.0,   # 问号
            '；': 0.8,   # 分号
            '：': 0.6,   # 冒号
            '，': 0.4,   # 逗号
            '、': 0.3,   # 顿号
            '\n': 0.9,   # 换行
            '\n\n': 1.0, # 段落分隔
        }
    
    def split_text_by_duration(self, text: str) -> List[TextSegment]:
        """
        根据目标时长智能分割文本
        
        Args:
            text: 要分割的原文
            
        Returns:
            List[TextSegment]: 分割后的文本段落列表
        """
        try:
            if not text or not text.strip():
                return []
            
            logger.info(f"开始智能文本分割，原文长度: {len(text)}字符，目标时长: {self.config.target_duration}秒")
            
            # 1. 预处理文本
            processed_text = self._preprocess_text(text)
            
            # 2. 创建语言单元
            language_units = self._create_language_units(processed_text)
            
            # 3. 智能分组
            segments = self._intelligent_grouping(language_units)
            
            # 4. 优化分割结果
            optimized_segments = self._optimize_segments(segments)
            
            logger.info(f"文本分割完成，生成 {len(optimized_segments)} 个段落")
            self._log_segment_stats(optimized_segments)
            
            return optimized_segments
            
        except Exception as e:
            logger.error(f"智能文本分割失败: {e}")
            # 降级到简单分割
            return self._fallback_split(text)
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 标准化换行符
        text = re.sub(r'\r\n|\r', '\n', text)
        
        # 清理多余的空白字符
        text = re.sub(r'\n\s*\n', '\n\n', text)  # 标准化段落分隔
        text = re.sub(r'[ \t]+', ' ', text)      # 标准化空格
        
        return text.strip()
    
    def _create_language_units(self, text: str) -> List[Dict]:
        """创建语言单元（句子、短语等）"""
        units = []
        
        # 按段落分割
        paragraphs = text.split('\n\n')
        
        for para_idx, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue
            
            # 按句子分割段落
            sentences = self._split_into_sentences(paragraph)
            
            for sent_idx, sentence in enumerate(sentences):
                if not sentence.strip():
                    continue
                
                # 计算时长
                duration = self._estimate_duration(sentence)
                
                # 计算在原文中的位置
                start_pos = text.find(sentence)
                end_pos = start_pos + len(sentence)
                
                unit = {
                    'content': sentence.strip(),
                    'duration': duration,
                    'start_pos': start_pos,
                    'end_pos': end_pos,
                    'paragraph_idx': para_idx,
                    'sentence_idx': sent_idx,
                    'type': 'sentence'
                }
                units.append(unit)
        
        return units
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割为句子"""
        # 中文句子分割符
        sentence_pattern = r'([。！？；])'
        
        # 分割并保留分隔符
        parts = re.split(sentence_pattern, text)
        
        sentences = []
        current_sentence = ""
        
        for part in parts:
            current_sentence += part
            if part in ['。', '！', '？', '；']:
                if current_sentence.strip():
                    sentences.append(current_sentence.strip())
                current_sentence = ""
        
        # 处理最后一个句子（可能没有结束符）
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return sentences
    
    def _estimate_duration(self, text: str) -> float:
        """估算文本的配音时长"""
        if not text:
            return 0.0
        
        # 统计中文字符和英文单词
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        english_words = len([word for word in text.split() if word.isalpha()])
        
        # 计算基础时长
        if chinese_chars > english_words:
            # 主要是中文
            base_duration = chinese_chars / self.config.chinese_chars_per_second
        else:
            # 主要是英文
            base_duration = english_words / self.config.english_words_per_second
        
        # 应用停顿因子
        duration = base_duration * self.config.pause_factor
        
        # 限制范围
        return max(0.5, min(duration, 30.0))
    
    def _intelligent_grouping(self, units: List[Dict]) -> List[TextSegment]:
        """智能分组语言单元"""
        if not units:
            return []
        
        segments = []
        current_group = []
        current_duration = 0.0
        
        for unit in units:
            unit_duration = unit['duration']
            
            # 检查是否可以添加到当前组
            if self._can_add_to_group(current_duration, unit_duration):
                current_group.append(unit)
                current_duration += unit_duration
            else:
                # 完成当前组
                if current_group:
                    segment = self._create_segment_from_group(current_group)
                    segments.append(segment)
                
                # 开始新组
                current_group = [unit]
                current_duration = unit_duration
        
        # 处理最后一组
        if current_group:
            segment = self._create_segment_from_group(current_group)
            segments.append(segment)
        
        return segments
    
    def _can_add_to_group(self, current_duration: float, unit_duration: float) -> bool:
        """判断是否可以将单元添加到当前组"""
        total_duration = current_duration + unit_duration
        
        # 如果当前组为空，总是可以添加
        if current_duration == 0:
            return True
        
        # 如果添加后超过最大时长，不能添加
        if total_duration > self.config.max_duration:
            return False
        
        # 如果当前时长已经在目标范围内，且添加后会超出容忍范围，不添加
        if (self.config.target_duration - self.config.tolerance <= current_duration <= 
            self.config.target_duration + self.config.tolerance):
            if total_duration > self.config.target_duration + self.config.tolerance:
                return False
        
        return True
    
    def _create_segment_from_group(self, group: List[Dict]) -> TextSegment:
        """从语言单元组创建文本段落"""
        if not group:
            return None
        
        # 合并内容
        content = ' '.join(unit['content'] for unit in group)
        
        # 计算总时长
        total_duration = sum(unit['duration'] for unit in group)
        
        # 计算位置
        start_index = group[0]['start_pos']
        end_index = group[-1]['end_pos']
        
        # 确定段落类型
        if len(group) == 1:
            segment_type = 'sentence'
        elif all(unit['paragraph_idx'] == group[0]['paragraph_idx'] for unit in group):
            segment_type = 'paragraph'
        else:
            segment_type = 'sentence_group'
        
        # 计算质量评分
        quality_score = self._calculate_quality_score(group, total_duration)
        
        return TextSegment(
            content=content,
            estimated_duration=total_duration,
            start_index=start_index,
            end_index=end_index,
            segment_type=segment_type,
            quality_score=quality_score
        )
    
    def _calculate_quality_score(self, group: List[Dict], duration: float) -> float:
        """计算段落质量评分"""
        score = 1.0
        
        # 时长评分（越接近目标时长，评分越高）
        duration_diff = abs(duration - self.config.target_duration)
        duration_score = max(0, 1 - duration_diff / self.config.target_duration)
        
        # 语义完整性评分（同段落的句子评分更高）
        if len(group) > 1:
            same_paragraph = all(unit['paragraph_idx'] == group[0]['paragraph_idx'] for unit in group)
            semantic_score = 1.0 if same_paragraph else 0.7
        else:
            semantic_score = 1.0
        
        # 综合评分
        score = (duration_score * 0.6 + semantic_score * 0.4)
        
        return score
    
    def _optimize_segments(self, segments: List[TextSegment]) -> List[TextSegment]:
        """优化分割结果"""
        if not segments:
            return segments
        
        optimized = []
        
        for segment in segments:
            # 检查是否需要进一步分割
            if segment.estimated_duration > self.config.max_duration:
                # 分割过长的段落
                sub_segments = self._split_long_segment(segment)
                optimized.extend(sub_segments)
            elif segment.estimated_duration < self.config.min_duration and optimized:
                # 合并过短的段落
                last_segment = optimized[-1]
                if (last_segment.estimated_duration + segment.estimated_duration <= 
                    self.config.max_duration):
                    # 合并到上一个段落
                    merged_segment = self._merge_segments(last_segment, segment)
                    optimized[-1] = merged_segment
                else:
                    optimized.append(segment)
            else:
                optimized.append(segment)
        
        return optimized

    def _split_long_segment(self, segment: TextSegment) -> List[TextSegment]:
        """分割过长的段落"""
        # 简单按句子重新分割
        sentences = self._split_into_sentences(segment.content)

        sub_segments = []
        current_content = ""
        current_duration = 0.0

        for sentence in sentences:
            sentence_duration = self._estimate_duration(sentence)

            if (current_duration + sentence_duration <= self.config.max_duration and
                current_content):
                current_content += " " + sentence
                current_duration += sentence_duration
            else:
                # 完成当前段落
                if current_content:
                    sub_segment = TextSegment(
                        content=current_content,
                        estimated_duration=current_duration,
                        start_index=segment.start_index,
                        end_index=segment.end_index,
                        segment_type='sentence_group',
                        quality_score=0.8
                    )
                    sub_segments.append(sub_segment)

                # 开始新段落
                current_content = sentence
                current_duration = sentence_duration

        # 处理最后一个段落
        if current_content:
            sub_segment = TextSegment(
                content=current_content,
                estimated_duration=current_duration,
                start_index=segment.start_index,
                end_index=segment.end_index,
                segment_type='sentence_group',
                quality_score=0.8
            )
            sub_segments.append(sub_segment)

        return sub_segments if sub_segments else [segment]

    def _merge_segments(self, segment1: TextSegment, segment2: TextSegment) -> TextSegment:
        """合并两个段落"""
        merged_content = segment1.content + " " + segment2.content
        merged_duration = segment1.estimated_duration + segment2.estimated_duration

        return TextSegment(
            content=merged_content,
            estimated_duration=merged_duration,
            start_index=segment1.start_index,
            end_index=segment2.end_index,
            segment_type='merged',
            quality_score=min(segment1.quality_score, segment2.quality_score)
        )

    def _log_segment_stats(self, segments: List[TextSegment]) -> None:
        """记录分割统计信息"""
        if not segments:
            return

        total_duration = sum(seg.estimated_duration for seg in segments)
        avg_duration = total_duration / len(segments)

        duration_distribution = {
            'under_target': len([s for s in segments if s.estimated_duration < self.config.target_duration - self.config.tolerance]),
            'in_target': len([s for s in segments if self.config.target_duration - self.config.tolerance <= s.estimated_duration <= self.config.target_duration + self.config.tolerance]),
            'over_target': len([s for s in segments if s.estimated_duration > self.config.target_duration + self.config.tolerance])
        }

        logger.info(f"分割统计: 总段落数={len(segments)}, 平均时长={avg_duration:.1f}秒")
        logger.info(f"时长分布: 低于目标={duration_distribution['under_target']}, 符合目标={duration_distribution['in_target']}, 超过目标={duration_distribution['over_target']}")

    def _fallback_split(self, text: str) -> List[TextSegment]:
        """降级分割方法"""
        logger.warning("使用降级分割方法")

        # 简单按段落分割
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        segments = []
        for i, paragraph in enumerate(paragraphs):
            duration = self._estimate_duration(paragraph)

            segment = TextSegment(
                content=paragraph,
                estimated_duration=duration,
                start_index=0,
                end_index=len(paragraph),
                segment_type='paragraph',
                quality_score=0.5
            )
            segments.append(segment)

        return segments

    def get_optimal_segment_count(self, text: str) -> int:
        """计算最优的段落数量"""
        total_duration = self._estimate_duration(text)
        optimal_count = max(1, round(total_duration / self.config.target_duration))

        logger.info(f"文本总时长: {total_duration:.1f}秒, 建议段落数: {optimal_count}")
        return optimal_count

    def validate_segments(self, segments: List[TextSegment]) -> Dict[str, any]:
        """验证分割结果"""
        if not segments:
            return {'valid': False, 'issues': ['没有生成任何段落']}

        issues = []
        stats = {
            'total_segments': len(segments),
            'avg_duration': sum(s.estimated_duration for s in segments) / len(segments),
            'min_duration': min(s.estimated_duration for s in segments),
            'max_duration': max(s.estimated_duration for s in segments),
            'avg_quality': sum(s.quality_score for s in segments) / len(segments)
        }

        # 检查时长范围
        for i, segment in enumerate(segments):
            if segment.estimated_duration < self.config.min_duration:
                issues.append(f"段落{i+1}时长过短: {segment.estimated_duration:.1f}秒")
            elif segment.estimated_duration > self.config.max_duration:
                issues.append(f"段落{i+1}时长过长: {segment.estimated_duration:.1f}秒")

        # 检查内容完整性
        for i, segment in enumerate(segments):
            if not segment.content.strip():
                issues.append(f"段落{i+1}内容为空")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'stats': stats
        }


def create_voice_segments_with_duration_control(text: str, target_duration: float = 10.0) -> List[Dict]:
    """
    使用智能分割器创建配音段落

    Args:
        text: 原文
        target_duration: 目标时长（秒）

    Returns:
        List[Dict]: 配音段落列表
    """
    try:
        # 创建分割配置
        config = SplitConfig(target_duration=target_duration)

        # 创建分割器
        splitter = IntelligentTextSplitter(config)

        # 分割文本
        segments = splitter.split_text_by_duration(text)

        # 转换为配音段落格式
        voice_segments = []
        for i, segment in enumerate(segments):
            voice_segment = {
                'index': i,
                'scene_id': f'scene_{(i // 3) + 1}',  # 每3个镜头一个场景
                'shot_id': f'text_segment_{i+1:03d}',
                'original_text': segment.content,
                'dialogue_text': segment.content,
                'estimated_duration': segment.estimated_duration,
                'segment_type': segment.segment_type,
                'quality_score': segment.quality_score,
                'status': '未生成',
                'audio_path': '',
                'selected': True
            }
            voice_segments.append(voice_segment)

        logger.info(f"创建了 {len(voice_segments)} 个配音段落，平均时长: {sum(s['estimated_duration'] for s in voice_segments) / len(voice_segments):.1f}秒")

        return voice_segments

    except Exception as e:
        logger.error(f"创建配音段落失败: {e}")
        return []
