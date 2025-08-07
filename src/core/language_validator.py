#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语言验证器
提供内容语言质量检测和验证功能
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

from src.models.language_models import LanguageCode
from src.core.language_detector import LanguageDetector
from src.utils.logger import logger


class ValidationLevel(Enum):
    """验证级别枚举"""
    BASIC = "basic"      # 基础验证
    STANDARD = "standard"  # 标准验证
    STRICT = "strict"    # 严格验证


class IssueType(Enum):
    """问题类型枚举"""
    LANGUAGE_MISMATCH = "language_mismatch"      # 语言不匹配
    MIXED_LANGUAGE = "mixed_language"            # 混合语言
    ENCODING_ISSUE = "encoding_issue"            # 编码问题
    GRAMMAR_ERROR = "grammar_error"              # 语法错误
    SPELLING_ERROR = "spelling_error"            # 拼写错误
    PUNCTUATION_ERROR = "punctuation_error"      # 标点符号错误
    CHARACTER_ENCODING = "character_encoding"    # 字符编码问题


@dataclass
class ValidationIssue:
    """验证问题数据类"""
    type: IssueType
    severity: str  # "low", "medium", "high"
    message: str
    position: Optional[Tuple[int, int]] = None  # (start, end)
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'type': self.type.value,
            'severity': self.severity,
            'message': self.message,
            'position': self.position,
            'suggestion': self.suggestion
        }


@dataclass
class ValidationResult:
    """验证结果数据类"""
    is_valid: bool
    confidence: float  # 0.0 - 1.0
    detected_language: LanguageCode
    issues: List[ValidationIssue]
    suggestions: List[str]
    statistics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'is_valid': self.is_valid,
            'confidence': self.confidence,
            'detected_language': self.detected_language.value,
            'issues': [issue.to_dict() for issue in self.issues],
            'suggestions': self.suggestions,
            'statistics': self.statistics
        }


class LanguageValidator:
    """语言验证器类"""
    
    def __init__(self):
        self.language_detector = LanguageDetector()
        
        # 中文标点符号
        self.chinese_punctuation = set('，。！？；：""''（）【】《》、')
        # 英文标点符号
        self.english_punctuation = set(',.!?;:""\'()[]<>/')
        
        # 常见英文语法错误模式
        self.english_grammar_patterns = [
            (re.compile(r'\ba\s+[aeiouAEIOU]'), 'Use "an" before vowel sounds'),
            (re.compile(r'\ban\s+[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]'), 'Use "a" before consonant sounds'),
            (re.compile(r'\s{2,}'), 'Multiple spaces should be single space'),
            (re.compile(r'[.!?]{2,}'), 'Multiple punctuation marks'),
        ]
        
        # 常见英文拼写错误
        self.common_misspellings = {
            'recieve': 'receive',
            'seperate': 'separate',
            'definately': 'definitely',
            'occured': 'occurred',
            'begining': 'beginning',
            'writting': 'writing',
            'comming': 'coming',
            'runing': 'running',
        }
    
    def validate_content(self, content: str, expected_language: LanguageCode, 
                        validation_level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationResult:
        """
        验证内容的语言质量
        
        Args:
            content: 要验证的内容
            expected_language: 期望的语言
            validation_level: 验证级别
            
        Returns:
            ValidationResult: 验证结果
        """
        if not content or not content.strip():
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                detected_language=expected_language,
                issues=[ValidationIssue(
                    type=IssueType.LANGUAGE_MISMATCH,
                    severity="high",
                    message="内容为空"
                )],
                suggestions=["请输入有效的文本内容"],
                statistics={}
            )
        
        # 检测语言
        detected_language = self.language_detector.detect_language(content)
        statistics = self.language_detector.get_language_statistics(content)
        
        # 收集验证问题
        issues = []
        suggestions = []
        
        # 基础验证
        issues.extend(self._basic_validation(content, expected_language, detected_language))
        
        # 标准验证
        if validation_level in [ValidationLevel.STANDARD, ValidationLevel.STRICT]:
            issues.extend(self._standard_validation(content, expected_language))
        
        # 严格验证
        if validation_level == ValidationLevel.STRICT:
            issues.extend(self._strict_validation(content, expected_language))
        
        # 生成建议
        suggestions = self._generate_suggestions(issues, expected_language)
        
        # 计算置信度
        confidence = self._calculate_confidence(content, expected_language, detected_language, issues)
        
        # 判断是否有效
        is_valid = len([issue for issue in issues if issue.severity == "high"]) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            detected_language=detected_language,
            issues=issues,
            suggestions=suggestions,
            statistics=statistics
        )
    
    def _basic_validation(self, content: str, expected_language: LanguageCode, 
                         detected_language: LanguageCode) -> List[ValidationIssue]:
        """基础验证"""
        issues = []
        
        # 语言匹配检查
        if detected_language != expected_language:
            issues.append(ValidationIssue(
                type=IssueType.LANGUAGE_MISMATCH,
                severity="high",
                message=f"检测到的语言({detected_language.value})与期望语言({expected_language.value})不匹配"
            ))
        
        # 混合语言检查
        if self.language_detector.is_mixed_language(content):
            issues.append(ValidationIssue(
                type=IssueType.MIXED_LANGUAGE,
                severity="medium",
                message="内容包含混合语言"
            ))
        
        # 编码问题检查
        try:
            content.encode('utf-8')
        except UnicodeEncodeError as e:
            issues.append(ValidationIssue(
                type=IssueType.ENCODING_ISSUE,
                severity="high",
                message=f"字符编码错误: {str(e)}"
            ))
        
        return issues
    
    def _standard_validation(self, content: str, expected_language: LanguageCode) -> List[ValidationIssue]:
        """标准验证"""
        issues = []
        
        if expected_language == LanguageCode.CHINESE:
            issues.extend(self._validate_chinese_content(content))
        elif expected_language == LanguageCode.ENGLISH:
            issues.extend(self._validate_english_content(content))
        
        return issues
    
    def _strict_validation(self, content: str, expected_language: LanguageCode) -> List[ValidationIssue]:
        """严格验证"""
        issues = []
        
        # 严格的字符检查
        if expected_language == LanguageCode.CHINESE:
            # 检查是否有英文字母（除了必要的情况）
            english_chars = re.findall(r'[a-zA-Z]+', content)
            if english_chars:
                # 过滤掉可能的专有名词或缩写
                suspicious_english = [char for char in english_chars if len(char) > 2]
                if suspicious_english:
                    issues.append(ValidationIssue(
                        type=IssueType.MIXED_LANGUAGE,
                        severity="medium",
                        message=f"中文内容中包含英文单词: {', '.join(suspicious_english[:3])}"
                    ))
        
        elif expected_language == LanguageCode.ENGLISH:
            # 检查是否有中文字符
            chinese_chars = re.findall(r'[\u4e00-\u9fff]+', content)
            if chinese_chars:
                issues.append(ValidationIssue(
                    type=IssueType.MIXED_LANGUAGE,
                    severity="high",
                    message=f"英文内容中包含中文字符: {''.join(chinese_chars[:5])}"
                ))
        
        return issues
    
    def _validate_chinese_content(self, content: str) -> List[ValidationIssue]:
        """验证中文内容"""
        issues = []
        
        # 检查标点符号使用
        english_punct_in_chinese = re.findall(r'[,.!?;:()"\']', content)
        if english_punct_in_chinese:
            issues.append(ValidationIssue(
                type=IssueType.PUNCTUATION_ERROR,
                severity="low",
                message="建议使用中文标点符号",
                suggestion="将英文标点符号替换为中文标点符号"
            ))
        
        # 检查空格使用（中文通常不需要空格）
        excessive_spaces = re.findall(r'[\u4e00-\u9fff]\s+[\u4e00-\u9fff]', content)
        if excessive_spaces:
            issues.append(ValidationIssue(
                type=IssueType.PUNCTUATION_ERROR,
                severity="low",
                message="中文字符间不需要空格",
                suggestion="移除中文字符间的多余空格"
            ))
        
        return issues
    
    def _validate_english_content(self, content: str) -> List[ValidationIssue]:
        """验证英文内容"""
        issues = []
        
        # 语法检查
        for pattern, message in self.english_grammar_patterns:
            matches = pattern.finditer(content)
            for match in matches:
                issues.append(ValidationIssue(
                    type=IssueType.GRAMMAR_ERROR,
                    severity="medium",
                    message=f"语法问题: {message}",
                    position=(match.start(), match.end()),
                    suggestion=message
                ))
        
        # 拼写检查
        words = re.findall(r'\b[a-zA-Z]+\b', content.lower())
        for word in words:
            if word in self.common_misspellings:
                issues.append(ValidationIssue(
                    type=IssueType.SPELLING_ERROR,
                    severity="medium",
                    message=f"拼写错误: '{word}'",
                    suggestion=f"建议改为: '{self.common_misspellings[word]}'"
                ))
        
        # 检查句子首字母大写
        sentences = re.split(r'[.!?]+\s*', content)
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and sentence[0].islower():
                issues.append(ValidationIssue(
                    type=IssueType.GRAMMAR_ERROR,
                    severity="low",
                    message="句子首字母应该大写",
                    suggestion="将句子首字母改为大写"
                ))
        
        return issues
    
    def _generate_suggestions(self, issues: List[ValidationIssue], expected_language: LanguageCode) -> List[str]:
        """生成修正建议"""
        suggestions = []
        
        # 从问题中提取建议
        for issue in issues:
            if issue.suggestion:
                suggestions.append(issue.suggestion)
        
        # 根据语言添加通用建议
        if expected_language == LanguageCode.CHINESE:
            if any(issue.type == IssueType.MIXED_LANGUAGE for issue in issues):
                suggestions.append("建议移除英文内容或将其翻译为中文")
            if any(issue.type == IssueType.PUNCTUATION_ERROR for issue in issues):
                suggestions.append("使用中文标点符号（，。！？等）")
        
        elif expected_language == LanguageCode.ENGLISH:
            if any(issue.type == IssueType.MIXED_LANGUAGE for issue in issues):
                suggestions.append("建议移除中文内容或将其翻译为英文")
            if any(issue.type == IssueType.GRAMMAR_ERROR for issue in issues):
                suggestions.append("检查语法和句子结构")
            if any(issue.type == IssueType.SPELLING_ERROR for issue in issues):
                suggestions.append("使用拼写检查工具验证单词拼写")
        
        # 去重
        return list(set(suggestions))
    
    def _calculate_confidence(self, content: str, expected_language: LanguageCode, 
                            detected_language: LanguageCode, issues: List[ValidationIssue]) -> float:
        """计算验证置信度"""
        base_confidence = 1.0
        
        # 语言匹配度影响
        if detected_language != expected_language:
            base_confidence -= 0.3
        
        # 问题严重程度影响
        for issue in issues:
            if issue.severity == "high":
                base_confidence -= 0.2
            elif issue.severity == "medium":
                base_confidence -= 0.1
            elif issue.severity == "low":
                base_confidence -= 0.05
        
        # 内容长度影响（太短的内容置信度较低）
        if len(content.strip()) < 10:
            base_confidence -= 0.2
        
        # 混合语言影响
        if self.language_detector.is_mixed_language(content):
            base_confidence -= 0.15
        
        return max(0.0, min(1.0, base_confidence))
    
    def get_validation_summary(self, validation_result: ValidationResult) -> Dict[str, Any]:
        """获取验证摘要"""
        issue_counts = {}
        for issue in validation_result.issues:
            issue_type = issue.type.value
            severity = issue.severity
            key = f"{issue_type}_{severity}"
            issue_counts[key] = issue_counts.get(key, 0) + 1
        
        return {
            'total_issues': len(validation_result.issues),
            'high_severity_issues': len([i for i in validation_result.issues if i.severity == "high"]),
            'medium_severity_issues': len([i for i in validation_result.issues if i.severity == "medium"]),
            'low_severity_issues': len([i for i in validation_result.issues if i.severity == "low"]),
            'issue_counts': issue_counts,
            'confidence': validation_result.confidence,
            'is_valid': validation_result.is_valid,
            'detected_language': validation_result.detected_language.value
        }