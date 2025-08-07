#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕服务
提供字幕生成、管理和格式化功能
"""

from typing import List, Dict, Any, Optional
from datetime import timedelta
from pathlib import Path
import json

from src.core.error_handler import AppError, ErrorHandler
from src.models.language_models import LanguageCode, SubtitleSettings
from src.utils.logger import logger

class SubtitleService:
    """字幕服务类"""

    def __init__(self):
        # 翻译存储路径（与语音服务保持一致）
        self.translation_storage_path = Path("data/translations")
        self.translation_storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("字幕服务初始化")

    def generate_srt_from_data(
        self, 
        subtitle_data: List[Dict[str, Any]], 
        language_code: LanguageCode,
        subtitle_settings: Optional[SubtitleSettings] = None
    ) -> str:
        """
        从结构化数据生成SRT格式的字幕

        Args:
            subtitle_data: 包含字幕信息的列表，例如 [{'start': 0.0, 'end': 2.5, 'text': '你好'}]
            language_code: 语言代码
            subtitle_settings: 字幕样式设置

        Returns:
            SRT格式的字幕字符串
        """
        try:
            if not subtitle_data:
                raise AppError('subtitle_generation_failed', {'reason': '字幕数据为空'})

            srt_content = []
            for i, item in enumerate(subtitle_data):
                start_time = self._format_time(item.get('start', 0.0))
                end_time = self._format_time(item.get('end', 0.0))
                text = item.get('text', '')

                if not text:
                    continue

                # 应用样式（如果提供）
                if subtitle_settings:
                    text = self._apply_styling(text, subtitle_settings)

                srt_content.append(f"{i + 1}")
                srt_content.append(f"{start_time} --> {end_time}")
                srt_content.append(text)
                srt_content.append("")

            return "\n".join(srt_content)

        except AppError as e:
            ErrorHandler.report_error(e)
            raise
        except Exception as e:
            error = AppError('subtitle_generation_failed', {'reason': f'未知错误: {str(e)}'}, original_exception=e)
            ErrorHandler.report_error(error)
            raise error

    def _format_time(self, seconds: float) -> str:
        """将秒转换为SRT时间格式 (HH:MM:SS,ms)"""
        delta = timedelta(seconds=seconds)
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = delta.microseconds // 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def _apply_styling(self, text: str, settings: SubtitleSettings) -> str:
        """应用基本的HTML样式标签"""
        styled_text = text
        if settings.font_color:
            styled_text = f'<font color="{settings.font_color}">{styled_text}</font>'
        # SRT标准不直接支持字体大小和族系，但这是一种常见扩展
        # if settings.font_size:
        #     styled_text = f'<font size="{settings.font_size}">{styled_text}</font>'
        # if settings.font_family:
        #      styled_text = f'<font face="{settings.font_family}">{styled_text}</font>'
        return styled_text

    def parse_srt(self, srt_content: str) -> List[Dict[str, Any]]:
        """
        解析SRT内容为结构化数据
        
        Args:
            srt_content: SRT格式的字符串
            
        Returns:
            结构化字幕数据列表
        """
        try:
            from srt import parse
            parsed_srt = list(parse(srt_content))
            
            subtitle_data = []
            for sub in parsed_srt:
                subtitle_data.append({
                    'start': sub.start.total_seconds(),
                    'end': sub.end.total_seconds(),
                    'text': sub.content
                })
            return subtitle_data
        except ImportError:
            error = AppError('subtitle_generation_failed', {'reason': 'srt库未安装，请运行: pip install srt'})
            ErrorHandler.report_error(error)
            raise error
        except Exception as e:
            error = AppError('subtitle_generation_failed', {'reason': f'解析SRT文件失败: {str(e)}'}, original_exception=e)
            ErrorHandler.report_error(error)
            raise error
    
    def get_translated_text(self, original_text: str, source_language: LanguageCode, 
                          target_language: LanguageCode, project_id: Optional[str] = None) -> Optional[str]:
        """
        从数据库获取翻译文本
        
        Args:
            original_text: 原文
            source_language: 源语言
            target_language: 目标语言
            project_id: 项目ID
            
        Returns:
            Optional[str]: 翻译文本，如果不存在则返回None
        """
        try:
            # 首先尝试使用当前哈希值查找
            text_hash = hash(original_text)
            filename = f"translation_{abs(text_hash)}_{source_language.value}_{target_language.value}.json"
            file_path = self.translation_storage_path / filename
            
            if file_path.exists():
                result = self._load_and_validate_translation(file_path, original_text, source_language, target_language, project_id)
                if result:
                    return result
            
            # 如果直接查找失败，遍历所有匹配的翻译文件
            pattern = f"translation_*_{source_language.value}_{target_language.value}.json"
            for file_path in self.translation_storage_path.glob(pattern):
                result = self._load_and_validate_translation(file_path, original_text, source_language, target_language, project_id)
                if result:
                    logger.debug(f"通过遍历找到翻译文本: {file_path}")
                    return result
            
            logger.debug(f"未找到匹配的翻译文本: {original_text[:30]}...")
            return None
            
        except Exception as e:
            logger.error(f"获取翻译文本失败: {e}")
            return None
    
    def _load_and_validate_translation(self, file_path: Path, original_text: str, 
                                     source_language: LanguageCode, target_language: LanguageCode,
                                     project_id: Optional[str] = None) -> Optional[str]:
        """
        加载并验证翻译文件
        
        Args:
            file_path: 翻译文件路径
            original_text: 原文
            source_language: 源语言
            target_language: 目标语言
            project_id: 项目ID
            
        Returns:
            Optional[str]: 翻译文本，如果验证失败则返回None
        """
        try:
            # 从文件加载数据
            with open(file_path, 'r', encoding='utf-8') as f:
                translation_data = json.load(f)
            
            # 验证数据完整性
            if (translation_data.get('original_text') == original_text and
                translation_data.get('source_language') == source_language.value and
                translation_data.get('target_language') == target_language.value):
                
                # 如果指定了项目ID，进行额外验证
                if project_id and translation_data.get('project_id') != project_id:
                    logger.debug(f"项目ID不匹配: 期望 {project_id}, 实际 {translation_data.get('project_id')}")
                    return None
                
                logger.debug(f"成功验证翻译文本: {file_path}")
                return translation_data.get('translated_text')
            
            return None
            
        except Exception as e:
            logger.debug(f"加载翻译文件失败 {file_path}: {e}")
            return None
    
    def generate_srt_with_translation(self, subtitle_data: List[Dict[str, Any]], 
                                    source_language: LanguageCode, target_language: LanguageCode,
                                    project_id: Optional[str] = None,
                                    subtitle_settings: Optional[SubtitleSettings] = None) -> str:
        """
        生成带翻译的SRT字幕
        
        Args:
            subtitle_data: 包含字幕信息的列表
            source_language: 源语言
            target_language: 目标语言
            project_id: 项目ID
            subtitle_settings: 字幕样式设置
            
        Returns:
            SRT格式的字幕字符串
        """
        try:
            if not subtitle_data:
                raise AppError('subtitle_generation_failed', {'reason': '字幕数据为空'})

            logger.info(f"🎬 生成带翻译的字幕: {source_language.value} -> {target_language.value}")
            
            srt_content = []
            translation_cache = {}  # 缓存翻译结果以提高性能
            
            for i, item in enumerate(subtitle_data):
                start_time = self._format_time(item.get('start', 0.0))
                end_time = self._format_time(item.get('end', 0.0))
                original_text = item.get('text', '')

                if not original_text:
                    continue

                # 获取翻译文本
                translated_text = original_text
                
                if source_language != target_language:
                    # 检查缓存
                    cache_key = hash(original_text)
                    if cache_key in translation_cache:
                        translated_text = translation_cache[cache_key]
                        logger.debug(f"使用缓存翻译: {original_text[:20]}...")
                    else:
                        # 从数据库获取翻译
                        db_translation = self.get_translated_text(
                            original_text=original_text,
                            source_language=source_language,
                            target_language=target_language,
                            project_id=project_id
                        )
                        
                        if db_translation:
                            translated_text = db_translation
                            translation_cache[cache_key] = translated_text
                            logger.debug(f"使用数据库翻译: {original_text[:20]}... -> {translated_text[:20]}...")
                        else:
                            logger.warning(f"未找到翻译，使用原文: {original_text[:20]}...")
                            translation_cache[cache_key] = original_text

                # 应用样式（如果提供）
                if subtitle_settings:
                    translated_text = self._apply_styling(translated_text, subtitle_settings)

                srt_content.append(f"{i + 1}")
                srt_content.append(f"{start_time} --> {end_time}")
                srt_content.append(translated_text)
                srt_content.append("")

            result = "\n".join(srt_content)
            logger.info(f"✅ 字幕生成完成，共 {len(subtitle_data)} 条字幕")
            return result

        except AppError as e:
            ErrorHandler.report_error(e)
            raise
        except Exception as e:
            error = AppError('subtitle_generation_failed', {'reason': f'生成翻译字幕失败: {str(e)}'}, original_exception=e)
            ErrorHandler.report_error(error)
            raise error
    
    def create_subtitle_mapping(self, original_texts: List[str], translated_texts: List[str],
                              timings: List[Dict[str, float]]) -> List[Dict[str, Any]]:
        """
        创建原文和译文的对应关系映射
        
        Args:
            original_texts: 原文列表
            translated_texts: 译文列表
            timings: 时间轴信息列表，格式为 [{'start': 0.0, 'end': 2.5}, ...]
            
        Returns:
            List[Dict[str, Any]]: 包含对应关系的字幕数据
        """
        try:
            if len(original_texts) != len(translated_texts) or len(original_texts) != len(timings):
                raise AppError('subtitle_mapping_failed', {
                    'reason': f'文本和时间轴数量不匹配: 原文{len(original_texts)}, 译文{len(translated_texts)}, 时间轴{len(timings)}'
                })
            
            subtitle_mapping = []
            for i, (original, translated, timing) in enumerate(zip(original_texts, translated_texts, timings)):
                subtitle_mapping.append({
                    'index': i,
                    'start': timing.get('start', 0.0),
                    'end': timing.get('end', 0.0),
                    'original_text': original,
                    'translated_text': translated,
                    'text': translated  # 默认使用译文作为显示文本
                })
            
            logger.info(f"创建字幕映射完成，共 {len(subtitle_mapping)} 条记录")
            return subtitle_mapping
            
        except AppError as e:
            ErrorHandler.report_error(e)
            raise
        except Exception as e:
            error = AppError('subtitle_mapping_failed', {'reason': f'创建字幕映射失败: {str(e)}'}, original_exception=e)
            ErrorHandler.report_error(error)
            raise error
    
    def sync_subtitles_with_audio(self, subtitle_data: List[Dict[str, Any]], 
                                audio_duration: float, adjustment_factor: float = 1.0) -> List[Dict[str, Any]]:
        """
        同步字幕与音频时间轴
        
        Args:
            subtitle_data: 字幕数据
            audio_duration: 音频总时长（秒）
            adjustment_factor: 时间调整因子
            
        Returns:
            List[Dict[str, Any]]: 同步后的字幕数据
        """
        try:
            if not subtitle_data:
                return subtitle_data
            
            logger.info(f"🔄 同步字幕与音频时间轴，音频时长: {audio_duration:.2f}秒")
            
            # 计算原始字幕总时长
            original_duration = max(item.get('end', 0.0) for item in subtitle_data)
            
            if original_duration <= 0:
                logger.warning("字幕时长为0，跳过同步")
                return subtitle_data
            
            # 计算时间缩放比例
            time_scale = (audio_duration / original_duration) * adjustment_factor
            
            logger.info(f"时间缩放比例: {time_scale:.3f}")
            
            # 应用时间缩放
            synced_data = []
            for item in subtitle_data:
                synced_item = item.copy()
                synced_item['start'] = item.get('start', 0.0) * time_scale
                synced_item['end'] = item.get('end', 0.0) * time_scale
                synced_data.append(synced_item)
            
            logger.info("✅ 字幕时间轴同步完成")
            return synced_data
            
        except Exception as e:
            error = AppError('subtitle_sync_failed', {'reason': f'字幕同步失败: {str(e)}'}, original_exception=e)
            ErrorHandler.report_error(error)
            raise error
    
    def validate_subtitle_timing(self, subtitle_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证字幕时间轴的有效性
        
        Args:
            subtitle_data: 字幕数据
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            issues = []
            total_duration = 0.0
            
            for i, item in enumerate(subtitle_data):
                start = item.get('start', 0.0)
                end = item.get('end', 0.0)
                text = item.get('text', '')
                
                # 检查时间有效性
                if start < 0:
                    issues.append(f"字幕 {i+1}: 开始时间为负数 ({start})")
                
                if end <= start:
                    issues.append(f"字幕 {i+1}: 结束时间不大于开始时间 ({start} -> {end})")
                
                if not text.strip():
                    issues.append(f"字幕 {i+1}: 文本为空")
                
                # 检查与前一条字幕的重叠
                if i > 0:
                    prev_end = subtitle_data[i-1].get('end', 0.0)
                    if start < prev_end:
                        issues.append(f"字幕 {i+1}: 与前一条字幕时间重叠 ({prev_end} -> {start})")
                
                total_duration = max(total_duration, end)
            
            return {
                'is_valid': len(issues) == 0,
                'issues': issues,
                'total_duration': total_duration,
                'subtitle_count': len(subtitle_data)
            }
            
        except Exception as e:
            logger.error(f"字幕验证失败: {e}")
            return {
                'is_valid': False,
                'issues': [f"验证过程异常: {str(e)}"],
                'total_duration': 0.0,
                'subtitle_count': 0
            }
