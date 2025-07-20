"""
智能同步检测器
替换旧的简单数量检测，提供更智能的配音-图像同步分析
"""

import os
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from src.utils.logger import logger
from src.utils.audio_duration_analyzer import AudioDurationAnalyzer
from src.core.voice_image_matcher import VoiceImageMatcher


@dataclass
class SyncIssue:
    """同步问题数据结构"""
    issue_type: str  # 'duration_mismatch', 'content_mismatch', 'count_mismatch', 'quality_issue'
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    affected_segments: List[int]
    suggested_fix: str
    auto_fixable: bool = False


@dataclass
class SyncAnalysisResult:
    """同步分析结果"""
    overall_quality: float  # 0.0-1.0
    issues: List[SyncIssue]
    recommendations: List[str]
    voice_segments_count: int
    image_segments_count: int
    total_voice_duration: float
    estimated_video_duration: float
    sync_score: float  # 0.0-1.0


class IntelligentSyncDetector:
    """智能同步检测器"""
    
    def __init__(self, project_manager=None):
        self.project_manager = project_manager
        self.audio_analyzer = AudioDurationAnalyzer()
        self.voice_matcher = VoiceImageMatcher()
        
        # 检测阈值配置
        self.thresholds = {
            'min_segment_duration': 1.0,  # 最短段落时长
            'max_segment_duration': 15.0,  # 最长段落时长
            'ideal_segment_duration': 5.0,  # 理想段落时长
            'duration_variance_threshold': 0.3,  # 时长方差阈值
            'content_similarity_threshold': 0.7,  # 内容相似度阈值
            'sync_quality_threshold': 0.8,  # 同步质量阈值
        }
    
    def analyze_project_sync(self, project_data: Dict[str, Any]) -> SyncAnalysisResult:
        """分析项目的配音-图像同步状态"""
        try:
            logger.info("开始智能同步分析...")
            
            # 提取配音数据
            voice_data = self._extract_voice_data(project_data)
            
            # 提取图像数据
            image_data = self._extract_image_data(project_data)
            
            # 分析时长匹配
            duration_issues = self._analyze_duration_sync(voice_data, image_data)
            
            # 分析内容匹配
            content_issues = self._analyze_content_sync(voice_data, image_data)
            
            # 分析数量匹配
            count_issues = self._analyze_count_sync(voice_data, image_data)
            
            # 分析质量问题
            quality_issues = self._analyze_quality_issues(voice_data, image_data)
            
            # 汇总所有问题
            all_issues = duration_issues + content_issues + count_issues + quality_issues
            
            # 计算整体质量分数
            overall_quality = self._calculate_overall_quality(all_issues, voice_data, image_data)
            
            # 生成建议
            recommendations = self._generate_recommendations(all_issues, voice_data, image_data)
            
            # 计算统计信息
            voice_count = len(voice_data)
            image_count = len(image_data)
            total_duration = sum(self.audio_analyzer.analyze_duration(
                v.get('audio_path', ''), v.get('dialogue_text', '')
            ) for v in voice_data)
            
            result = SyncAnalysisResult(
                overall_quality=overall_quality,
                issues=all_issues,
                recommendations=recommendations,
                voice_segments_count=voice_count,
                image_segments_count=image_count,
                total_voice_duration=total_duration,
                estimated_video_duration=total_duration,
                sync_score=self._calculate_sync_score(all_issues)
            )
            
            logger.info(f"同步分析完成，质量分数: {overall_quality:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"智能同步分析失败: {e}")
            # 返回默认结果
            return SyncAnalysisResult(
                overall_quality=0.5,
                issues=[],
                recommendations=["分析失败，请检查项目数据"],
                voice_segments_count=0,
                image_segments_count=0,
                total_voice_duration=0.0,
                estimated_video_duration=0.0,
                sync_score=0.5
            )
    
    def _extract_voice_data(self, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取配音数据"""
        voice_data = []
        
        # 从配音生成模块获取数据
        voice_generation = project_data.get('voice_generation', {})
        
        # 优先使用已生成的音频
        generated_audio = voice_generation.get('generated_audio', [])
        if generated_audio:
            voice_data.extend(generated_audio)
        
        # 备选：使用配音段落
        voice_segments = voice_generation.get('voice_segments', [])
        if voice_segments and not generated_audio:
            voice_data.extend(voice_segments)
        
        return voice_data
    
    def _extract_image_data(self, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取图像数据"""
        image_data = []
        
        # 从图像生成模块获取数据
        image_generation = project_data.get('image_generation', {})
        generated_images = image_generation.get('generated_images', [])
        
        if generated_images:
            image_data.extend(generated_images)
        
        # 备选：从分镜数据获取
        storyboard_data = project_data.get('storyboard_data', [])
        if storyboard_data and not generated_images:
            image_data.extend(storyboard_data)
        
        return image_data
    
    def _analyze_duration_sync(self, voice_data: List[Dict], image_data: List[Dict]) -> List[SyncIssue]:
        """分析时长同步问题"""
        issues = []
        
        try:
            # 分析配音时长分布
            durations = []
            for voice_segment in voice_data:
                duration = self.audio_analyzer.analyze_duration(
                    voice_segment.get('audio_path', ''),
                    voice_segment.get('dialogue_text', '')
                )
                durations.append(duration)
            
            if not durations:
                return issues
            
            # 检查过短的段落
            short_segments = [i for i, d in enumerate(durations) 
                            if d < self.thresholds['min_segment_duration']]
            if short_segments:
                issues.append(SyncIssue(
                    issue_type='duration_mismatch',
                    severity='medium',
                    description=f"发现 {len(short_segments)} 个过短的配音段落（<{self.thresholds['min_segment_duration']}秒）",
                    affected_segments=short_segments,
                    suggested_fix="建议合并相邻的短段落或增加配音内容",
                    auto_fixable=True
                ))
            
            # 检查过长的段落
            long_segments = [i for i, d in enumerate(durations) 
                           if d > self.thresholds['max_segment_duration']]
            if long_segments:
                issues.append(SyncIssue(
                    issue_type='duration_mismatch',
                    severity='medium',
                    description=f"发现 {len(long_segments)} 个过长的配音段落（>{self.thresholds['max_segment_duration']}秒）",
                    affected_segments=long_segments,
                    suggested_fix="建议分割长段落或增加更多图像变化",
                    auto_fixable=True
                ))
            
            # 检查时长方差
            if len(durations) > 1:
                avg_duration = sum(durations) / len(durations)
                variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
                if variance > self.thresholds['duration_variance_threshold'] * avg_duration:
                    issues.append(SyncIssue(
                        issue_type='duration_mismatch',
                        severity='low',
                        description=f"配音段落时长差异较大（方差: {variance:.2f}）",
                        affected_segments=list(range(len(durations))),
                        suggested_fix="建议调整配音段落长度，使其更加均匀",
                        auto_fixable=False
                    ))
            
        except Exception as e:
            logger.error(f"时长同步分析失败: {e}")
        
        return issues
    
    def _analyze_content_sync(self, voice_data: List[Dict], image_data: List[Dict]) -> List[SyncIssue]:
        """分析内容同步问题"""
        issues = []
        
        try:
            # 检查配音与图像内容的匹配度
            mismatched_segments = []
            
            min_count = min(len(voice_data), len(image_data))
            for i in range(min_count):
                voice_content = voice_data[i].get('dialogue_text', '')
                image_description = image_data[i].get('enhanced_description', 
                                                    image_data[i].get('consistency_description', ''))
                
                if voice_content and image_description:
                    # 简单的内容匹配检查（可以后续用LLM增强）
                    similarity = self._calculate_content_similarity(voice_content, image_description)
                    if similarity < self.thresholds['content_similarity_threshold']:
                        mismatched_segments.append(i)
            
            if mismatched_segments:
                issues.append(SyncIssue(
                    issue_type='content_mismatch',
                    severity='high',
                    description=f"发现 {len(mismatched_segments)} 个配音与图像内容不匹配的段落",
                    affected_segments=mismatched_segments,
                    suggested_fix="建议使用'按配音时间生成图像'功能重新生成匹配的图像",
                    auto_fixable=True
                ))
            
        except Exception as e:
            logger.error(f"内容同步分析失败: {e}")
        
        return issues
    
    def _analyze_count_sync(self, voice_data: List[Dict], image_data: List[Dict]) -> List[SyncIssue]:
        """分析数量同步问题"""
        issues = []
        
        voice_count = len(voice_data)
        image_count = len(image_data)
        
        if voice_count != image_count:
            severity = 'high' if abs(voice_count - image_count) > 2 else 'medium'
            issues.append(SyncIssue(
                issue_type='count_mismatch',
                severity=severity,
                description=f"配音段落数量（{voice_count}）与图像数量（{image_count}）不匹配",
                affected_segments=list(range(max(voice_count, image_count))),
                suggested_fix="建议使用'按配音时间生成图像'功能自动匹配数量",
                auto_fixable=True
            ))
        
        return issues
    
    def _analyze_quality_issues(self, voice_data: List[Dict], image_data: List[Dict]) -> List[SyncIssue]:
        """分析质量问题"""
        issues = []
        
        # 检查缺失的音频文件
        missing_audio = []
        for i, voice_segment in enumerate(voice_data):
            audio_path = voice_segment.get('audio_path', '')
            if not audio_path or not os.path.exists(audio_path):
                missing_audio.append(i)
        
        if missing_audio:
            issues.append(SyncIssue(
                issue_type='quality_issue',
                severity='critical',
                description=f"发现 {len(missing_audio)} 个缺失的音频文件",
                affected_segments=missing_audio,
                suggested_fix="请重新生成缺失的配音文件",
                auto_fixable=False
            ))
        
        # 检查缺失的图像文件
        missing_images = []
        for i, image_segment in enumerate(image_data):
            image_path = image_segment.get('image_path', image_segment.get('main_image_path', ''))
            if not image_path or not os.path.exists(image_path):
                missing_images.append(i)
        
        if missing_images:
            issues.append(SyncIssue(
                issue_type='quality_issue',
                severity='critical',
                description=f"发现 {len(missing_images)} 个缺失的图像文件",
                affected_segments=missing_images,
                suggested_fix="请重新生成缺失的图像文件",
                auto_fixable=False
            ))
        
        return issues

    def _calculate_content_similarity(self, voice_content: str, image_description: str) -> float:
        """计算配音内容与图像描述的相似度"""
        try:
            # 简单的关键词匹配算法（可以后续用更高级的NLP方法）
            voice_keywords = set(voice_content.lower().split())
            image_keywords = set(image_description.lower().split())

            if not voice_keywords or not image_keywords:
                return 0.0

            # 计算交集比例
            intersection = voice_keywords.intersection(image_keywords)
            union = voice_keywords.union(image_keywords)

            return len(intersection) / len(union) if union else 0.0

        except Exception as e:
            logger.error(f"计算内容相似度失败: {e}")
            return 0.5  # 默认中等相似度

    def _calculate_overall_quality(self, issues: List[SyncIssue], voice_data: List[Dict], image_data: List[Dict]) -> float:
        """计算整体质量分数"""
        try:
            if not voice_data and not image_data:
                return 0.0

            # 基础分数
            base_score = 1.0

            # 根据问题严重程度扣分
            for issue in issues:
                if issue.severity == 'critical':
                    base_score -= 0.3
                elif issue.severity == 'high':
                    base_score -= 0.2
                elif issue.severity == 'medium':
                    base_score -= 0.1
                elif issue.severity == 'low':
                    base_score -= 0.05

            # 确保分数在0-1范围内
            return max(0.0, min(1.0, base_score))

        except Exception as e:
            logger.error(f"计算整体质量失败: {e}")
            return 0.5

    def _calculate_sync_score(self, issues: List[SyncIssue]) -> float:
        """计算同步分数"""
        try:
            # 如果没有问题，同步分数为1.0
            if not issues:
                return 1.0

            # 根据可自动修复的问题比例计算分数
            auto_fixable_count = sum(1 for issue in issues if issue.auto_fixable)
            total_count = len(issues)

            # 可自动修复的问题影响较小
            auto_fixable_penalty = auto_fixable_count * 0.1
            manual_fix_penalty = (total_count - auto_fixable_count) * 0.3

            score = 1.0 - (auto_fixable_penalty + manual_fix_penalty)
            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.error(f"计算同步分数失败: {e}")
            return 0.5

    def _generate_recommendations(self, issues: List[SyncIssue], voice_data: List[Dict], image_data: List[Dict]) -> List[str]:
        """生成优化建议"""
        recommendations = []

        try:
            # 根据问题类型生成建议
            issue_types = set(issue.issue_type for issue in issues)

            if 'count_mismatch' in issue_types:
                recommendations.append("🎵 使用'按配音时间生成图像'功能自动匹配配音与图像数量")

            if 'content_mismatch' in issue_types:
                recommendations.append("🎯 使用配音优先工作流程重新生成匹配的图像内容")

            if 'duration_mismatch' in issue_types:
                recommendations.append("⏱️ 调整配音段落时长，建议每段3-8秒为最佳")

            if 'quality_issue' in issue_types:
                recommendations.append("🔧 修复缺失的音频或图像文件")

            # 根据数据状态生成通用建议
            voice_count = len(voice_data)
            image_count = len(image_data)

            if voice_count > 0 and image_count == 0:
                recommendations.append("📸 建议先生成图像，然后使用智能同步功能")
            elif voice_count == 0 and image_count > 0:
                recommendations.append("🎤 建议先生成配音，然后使用智能同步功能")
            elif voice_count > 0 and image_count > 0:
                # 计算总时长
                total_duration = sum(self.audio_analyzer.analyze_duration(
                    v.get('audio_path', ''), v.get('dialogue_text', '')
                ) for v in voice_data)

                if total_duration > 60:  # 超过1分钟
                    recommendations.append("🎬 视频较长，建议分段处理以提高质量")

                # 检查图像密度
                if image_count < voice_count * 0.8:
                    recommendations.append("🖼️ 图像数量偏少，建议增加图像以丰富视觉效果")

            # 如果没有问题，给出优化建议
            if not issues:
                recommendations.append("✅ 配音与图像同步良好，可以开始视频合成")
                recommendations.append("💡 建议预览效果，确认满意后再进行最终渲染")

        except Exception as e:
            logger.error(f"生成建议失败: {e}")
            recommendations.append("❌ 分析过程中出现错误，请检查项目数据")

        return recommendations

    def get_auto_fix_suggestions(self, issues: List[SyncIssue]) -> List[Dict[str, Any]]:
        """获取自动修复建议"""
        suggestions = []

        for issue in issues:
            if issue.auto_fixable:
                suggestion = {
                    'issue_type': issue.issue_type,
                    'description': issue.description,
                    'fix_action': self._get_fix_action(issue),
                    'affected_segments': issue.affected_segments,
                    'estimated_time': self._estimate_fix_time(issue)
                }
                suggestions.append(suggestion)

        return suggestions

    def _get_fix_action(self, issue: SyncIssue) -> str:
        """获取修复动作"""
        if issue.issue_type == 'count_mismatch':
            return 'regenerate_images_by_voice_time'
        elif issue.issue_type == 'content_mismatch':
            return 'regenerate_matched_images'
        elif issue.issue_type == 'duration_mismatch':
            if 'short' in issue.description.lower():
                return 'merge_short_segments'
            elif 'long' in issue.description.lower():
                return 'split_long_segments'
            else:
                return 'adjust_segment_durations'
        else:
            return 'manual_fix_required'

    def _estimate_fix_time(self, issue: SyncIssue) -> str:
        """估算修复时间"""
        if issue.issue_type == 'count_mismatch':
            return "2-5分钟"
        elif issue.issue_type == 'content_mismatch':
            return "5-10分钟"
        elif issue.issue_type == 'duration_mismatch':
            return "1-3分钟"
        else:
            return "需要手动处理"
