#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语言检测器
提供文本内容的语言检测和验证功能
"""

import re
from typing import Dict, List, Optional, Tuple
from src.models.language_models import LanguageCode
from src.utils.logger import logger


class LanguageDetector:
    """语言检测器类"""
    
    def __init__(self, cache_size: int = 128):
        # 缓存
        self.cache: Dict[str, LanguageCode] = {}
        self.cache_size = cache_size

        # 中文字符正则表达式
        self.chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        # 英文字符正则表达式
        self.english_pattern = re.compile(r'[a-zA-Z]+')
        # 数字和标点符号
        self.number_pattern = re.compile(r'[0-9]+')
        self.punctuation_pattern = re.compile(r'[.,!?;:()"\'\-\s]+')
        
        # 常见英文单词列表（用于更准确的检测）
        self.common_english_words = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have',
            'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you',
            'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they',
            'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would',
            'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about',
            'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can',
            'like', 'time', 'no', 'just', 'him', 'know', 'take', 'people',
            'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see',
            'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its',
            'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how',
            'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want',
            'because', 'any', 'these', 'give', 'day', 'most', 'us'
        }
    
    def detect_language(self, text: str) -> LanguageCode:
        """
        检测文本的主要语言
        
        Args:
            text: 要检测的文本
            
        Returns:
            LanguageCode: 检测到的语言代码
        """
        if not text or not text.strip():
            logger.warning("空文本，默认返回中文")
            return LanguageCode.CHINESE
        
        # 清理文本，移除多余空格
        cleaned_text = text.strip()

        # 检查缓存
        if cleaned_text in self.cache:
            return self.cache[cleaned_text]
        
        # 统计各种字符的数量
        chinese_chars = len(self.chinese_pattern.findall(cleaned_text))
        english_chars = len(self.english_pattern.findall(cleaned_text))
        
        # 计算字符比例
        total_chars = len(cleaned_text)
        if total_chars == 0:
            return LanguageCode.CHINESE
        
        chinese_ratio = chinese_chars / total_chars
        english_ratio = english_chars / total_chars
        
        logger.debug(f"语言检测统计: 中文字符={chinese_chars}, 英文字符={english_chars}, "
                    f"中文比例={chinese_ratio:.2f}, 英文比例={english_ratio:.2f}")
        
        # 检测逻辑
        if chinese_ratio > 0.1:  # 如果中文字符超过10%，认为是中文
            result = LanguageCode.CHINESE
        elif english_ratio > 0.3:  # 如果英文字符超过30%，认为是英文
            result = LanguageCode.ENGLISH
        else:
            # 使用更精确的检测方法
            result = self._advanced_detection(cleaned_text)

        # 更新缓存
        if len(self.cache) >= self.cache_size:
            self.cache.pop(next(iter(self.cache)))  # 移除最早的条目
        self.cache[cleaned_text] = result
        
        return result
    
    def _advanced_detection(self, text: str) -> LanguageCode:
        """
        高级语言检测方法
        
        Args:
            text: 要检测的文本
            
        Returns:
            LanguageCode: 检测到的语言代码
        """
        # 分词并检查常见英文单词
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        english_word_count = sum(1 for word in words if word in self.common_english_words)
        
        if english_word_count > 0:
            return LanguageCode.ENGLISH
        
        # 检查是否包含中文标点符号
        chinese_punctuation = re.findall(r'[，。！？；：""''（）【】《》]', text)
        if chinese_punctuation:
            return LanguageCode.CHINESE
        
        # 默认返回中文
        return LanguageCode.CHINESE
    
    def get_language_statistics(self, text: str) -> Dict[str, any]:
        """
        获取文本的语言统计信息
        
        Args:
            text: 要分析的文本
            
        Returns:
            Dict: 包含各种语言统计信息的字典
        """
        if not text:
            return {
                'total_chars': 0,
                'chinese_chars': 0,
                'english_chars': 0,
                'numbers': 0,
                'punctuation': 0,
                'chinese_ratio': 0.0,
                'english_ratio': 0.0,
                'detected_language': LanguageCode.CHINESE.value
            }
        
        chinese_matches = self.chinese_pattern.findall(text)
        english_matches = self.english_pattern.findall(text)
        number_matches = self.number_pattern.findall(text)
        punctuation_matches = self.punctuation_pattern.findall(text)
        
        chinese_chars = sum(len(match) for match in chinese_matches)
        english_chars = sum(len(match) for match in english_matches)
        numbers = sum(len(match) for match in number_matches)
        punctuation = sum(len(match) for match in punctuation_matches)
        
        total_chars = len(text)
        chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
        english_ratio = english_chars / total_chars if total_chars > 0 else 0
        
        detected_language = self.detect_language(text)
        
        return {
            'total_chars': total_chars,
            'chinese_chars': chinese_chars,
            'english_chars': english_chars,
            'numbers': numbers,
            'punctuation': punctuation,
            'chinese_ratio': chinese_ratio,
            'english_ratio': english_ratio,
            'detected_language': detected_language.value
        }
    
    def is_mixed_language(self, text: str, threshold: float = 0.1) -> bool:
        """
        检测文本是否为混合语言
        
        Args:
            text: 要检测的文本
            threshold: 混合语言的阈值
            
        Returns:
            bool: 是否为混合语言
        """
        stats = self.get_language_statistics(text)
        chinese_ratio = stats['chinese_ratio']
        english_ratio = stats['english_ratio']
        
        # 如果中英文比例都超过阈值，认为是混合语言
        return chinese_ratio > threshold and english_ratio > threshold
    
    def validate_language_consistency(self, text: str, expected_language: LanguageCode) -> Tuple[bool, List[str]]:
        """
        验证文本语言的一致性
        
        Args:
            text: 要验证的文本
            expected_language: 期望的语言
            
        Returns:
            Tuple[bool, List[str]]: (是否一致, 问题列表)
        """
        issues = []
        detected_language = self.detect_language(text)
        
        if detected_language != expected_language:
            issues.append(f"检测到的语言({detected_language.value})与期望语言({expected_language.value})不匹配")
        
        # 检查混合语言问题
        if self.is_mixed_language(text):
            issues.append("文本包含混合语言内容")
        
        # 特定语言的验证
        if expected_language == LanguageCode.CHINESE:
            # 检查中文文本中是否有过多英文
            stats = self.get_language_statistics(text)
            if stats['english_ratio'] > 0.3:
                issues.append("中文文本中英文字符比例过高")
        
        elif expected_language == LanguageCode.ENGLISH:
            # 检查英文文本中是否有中文字符
            if self.chinese_pattern.search(text):
                issues.append("英文文本中包含中文字符")
        
        is_consistent = len(issues) == 0
        return is_consistent, issues
    
    def suggest_language_correction(self, text: str, expected_language: LanguageCode) -> List[str]:
        """
        提供语言纠正建议
        
        Args:
            text: 要纠正的文本
            expected_language: 期望的语言
            
        Returns:
            List[str]: 纠正建议列表
        """
        suggestions = []
        is_consistent, issues = self.validate_language_consistency(text, expected_language)
        
        if not is_consistent:
            if expected_language == LanguageCode.CHINESE:
                suggestions.extend([
                    "建议移除文本中的英文字符",
                    "使用中文标点符号替换英文标点符号",
                    "检查是否有英文单词需要翻译为中文"
                ])
            elif expected_language == LanguageCode.ENGLISH:
                suggestions.extend([
                    "建议移除文本中的中文字符",
                    "使用英文标点符号替换中文标点符号",
                    "检查是否有中文内容需要翻译为英文"
                ])
            
            if self.is_mixed_language(text):
                suggestions.append("建议将混合语言内容分离为单一语言")
        
        return suggestions
