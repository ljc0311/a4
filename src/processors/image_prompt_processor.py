#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像提示词双语处理器
处理不同语言的图像描述，提供中英文提示词转换和优化功能
"""

import re
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from src.models.language_models import LanguageCode
from src.core.language_manager import LanguageManager
from src.core.language_detector import LanguageDetector
from src.utils.logger import logger


class PromptOptimizationLevel(Enum):
    """提示词优化级别"""
    BASIC = "basic"
    ENHANCED = "enhanced"
    PROFESSIONAL = "professional"


@dataclass
class ImagePromptResult:
    """图像提示词处理结果"""
    original_text: str
    processed_prompt: str
    language: LanguageCode
    optimization_level: PromptOptimizationLevel
    quality_score: float
    suggestions: List[str]
    metadata: Dict[str, Any]


@dataclass
class MatchingResult:
    """图像与文本匹配度结果"""
    match_score: float
    semantic_similarity: float
    keyword_overlap: float
    style_consistency: float
    issues: List[str]
    recommendations: List[str]


class ImagePromptProcessor:
    """图像提示词双语处理器"""
    
    def __init__(self, language_manager: Optional[LanguageManager] = None):
        self.language_manager = language_manager or LanguageManager()
        self.language_detector = LanguageDetector()
        
        # 中英文关键词映射表
        self.keyword_mapping = {
            # 基础描述词
            "美丽": "beautiful",
            "漂亮": "pretty",
            "可爱": "cute",
            "优雅": "elegant",
            "神秘": "mysterious",
            "梦幻": "dreamy",
            "浪漫": "romantic",
            "温暖": "warm",
            "清新": "fresh",
            "宁静": "peaceful",
            
            # 风格词汇
            "写实": "photorealistic",
            "动漫": "anime style",
            "卡通": "cartoon",
            "油画": "oil painting",
            "水彩": "watercolor",
            "素描": "sketch",
            "插画": "illustration",
            "概念艺术": "concept art",
            "数字艺术": "digital art",
            "传统艺术": "traditional art",
            
            # 光线效果
            "阳光": "sunlight",
            "月光": "moonlight",
            "霓虹灯": "neon light",
            "烛光": "candlelight",
            "自然光": "natural lighting",
            "戏剧性光线": "dramatic lighting",
            "柔和光线": "soft lighting",
            "背光": "backlight",
            "侧光": "side lighting",
            
            # 环境场景
            "森林": "forest",
            "海滩": "beach",
            "山脉": "mountains",
            "城市": "city",
            "乡村": "countryside",
            "花园": "garden",
            "房间": "room",
            "街道": "street",
            "公园": "park",
            "湖泊": "lake",
            
            # 情感表达
            "快乐": "happy",
            "悲伤": "sad",
            "愤怒": "angry",
            "惊讶": "surprised",
            "恐惧": "fearful",
            "平静": "calm",
            "兴奋": "excited",
            "沉思": "thoughtful",
            "专注": "focused",
            "放松": "relaxed",
            
            # 技术参数
            "高清": "high resolution",
            "4K": "4K",
            "8K": "8K",
            "超高清": "ultra high definition",
            "细节丰富": "highly detailed",
            "精细": "intricate",
            "锐利": "sharp",
            "清晰": "clear",
            "模糊": "blurred",
            "景深": "depth of field"
        }
        
        # 英文提示词优化模板
        self.english_optimization_templates = {
            PromptOptimizationLevel.BASIC: [
                "high quality",
                "detailed",
                "professional"
            ],
            PromptOptimizationLevel.ENHANCED: [
                "masterpiece",
                "best quality",
                "ultra detailed",
                "8k resolution",
                "professional photography",
                "perfect composition"
            ],
            PromptOptimizationLevel.PROFESSIONAL: [
                "award winning photography",
                "masterpiece",
                "ultra high resolution",
                "professional lighting",
                "perfect composition",
                "cinematic quality",
                "trending on artstation",
                "highly detailed",
                "photorealistic"
            ]
        }
        
        # 中文风格关键词
        self.chinese_style_keywords = {
            "古风": ["ancient chinese style", "traditional chinese", "classical"],
            "现代": ["modern", "contemporary", "urban"],
            "科幻": ["sci-fi", "futuristic", "cyberpunk"],
            "奇幻": ["fantasy", "magical", "mystical"],
            "自然": ["natural", "organic", "landscape"],
            "人物": ["portrait", "character", "person"],
            "建筑": ["architecture", "building", "structure"],
            "静物": ["still life", "object", "product"]
        }
        
        # 负面提示词
        self.negative_prompts = {
            LanguageCode.CHINESE: [
                "低质量", "模糊", "变形", "多余的手指", "错误的解剖结构"
            ],
            LanguageCode.ENGLISH: [
                "low quality", "blurry", "deformed", "extra fingers", 
                "bad anatomy", "worst quality", "low resolution", "distorted"
            ]
        }
        
        logger.info("图像提示词双语处理器初始化完成")
    
    async def process_prompt(self, text: str, target_language: Optional[LanguageCode] = None,
                           optimization_level: PromptOptimizationLevel = PromptOptimizationLevel.ENHANCED) -> ImagePromptResult:
        """
        处理图像提示词
        
        Args:
            text: 原始文本
            target_language: 目标语言，如果为None则自动检测
            optimization_level: 优化级别
            
        Returns:
            ImagePromptResult: 处理结果
        """
        try:
            # 检测原始语言
            detected_language = self.language_detector.detect_language(text)
            target_lang = target_language or detected_language
            
            logger.info(f"处理图像提示词: 检测语言={detected_language.value}, 目标语言={target_lang.value}")
            
            # 根据目标语言处理
            if target_lang == LanguageCode.ENGLISH:
                if detected_language == LanguageCode.CHINESE:
                    # 中文转英文
                    processed_prompt = await self._translate_chinese_to_english(text)
                else:
                    # 英文优化
                    processed_prompt = await self._optimize_english_prompt(text, optimization_level)
            else:
                # 保持中文或转换为中文
                processed_prompt = text
            
            # 应用优化
            if target_lang == LanguageCode.ENGLISH:
                processed_prompt = await self._apply_english_optimization(processed_prompt, optimization_level)
            
            # 计算质量分数
            quality_score = self._calculate_quality_score(processed_prompt, target_lang)
            
            # 生成建议
            suggestions = self._generate_suggestions(text, processed_prompt, target_lang)
            
            # 创建元数据
            metadata = {
                'detected_language': detected_language.value,
                'translation_applied': detected_language != target_lang,
                'optimization_applied': True,
                'processing_time': 0.1  # 模拟处理时间
            }
            
            return ImagePromptResult(
                original_text=text,
                processed_prompt=processed_prompt,
                language=target_lang,
                optimization_level=optimization_level,
                quality_score=quality_score,
                suggestions=suggestions,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"处理图像提示词失败: {e}")
            return ImagePromptResult(
                original_text=text,
                processed_prompt=text,
                language=detected_language,
                optimization_level=optimization_level,
                quality_score=0.5,
                suggestions=[f"处理失败: {str(e)}"],
                metadata={'error': str(e)}
            )
    
    async def _translate_chinese_to_english(self, chinese_text: str) -> str:
        """
        将中文提示词转换为英文
        
        Args:
            chinese_text: 中文文本
            
        Returns:
            str: 英文提示词
        """
        try:
            # 分词处理
            words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+|\d+', chinese_text)
            translated_parts = []
            
            for word in words:
                # 检查是否为中文词汇
                if re.match(r'[\u4e00-\u9fff]+', word):
                    # 查找映射表
                    if word in self.keyword_mapping:
                        translated_parts.append(self.keyword_mapping[word])
                    else:
                        # 尝试部分匹配
                        partial_match = self._find_partial_match(word)
                        if partial_match:
                            translated_parts.append(partial_match)
                        else:
                            # 保留原词并添加到建议中
                            translated_parts.append(word)
                else:
                    # 非中文词汇直接保留
                    translated_parts.append(word)
            
            # 组合结果
            result = ' '.join(translated_parts)
            
            # 后处理：移除重复词汇，调整语序
            result = self._post_process_translation(result)
            
            logger.debug(f"中文转英文: '{chinese_text}' -> '{result}'")
            return result
            
        except Exception as e:
            logger.error(f"中文转英文失败: {e}")
            return chinese_text
    
    def _find_partial_match(self, word: str) -> Optional[str]:
        """
        查找部分匹配的翻译
        
        Args:
            word: 中文词汇
            
        Returns:
            Optional[str]: 匹配的英文翻译
        """
        for chinese_key, english_value in self.keyword_mapping.items():
            if word in chinese_key or chinese_key in word:
                return english_value
        return None
    
    def _post_process_translation(self, text: str) -> str:
        """
        后处理翻译结果
        
        Args:
            text: 翻译后的文本
            
        Returns:
            str: 处理后的文本
        """
        # 移除重复词汇
        words = text.split()
        unique_words = []
        seen = set()
        
        for word in words:
            word_lower = word.lower()
            if word_lower not in seen:
                unique_words.append(word)
                seen.add(word_lower)
        
        # 重新组合
        result = ' '.join(unique_words)
        
        # 清理多余空格
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result
    
    async def _optimize_english_prompt(self, text: str, level: PromptOptimizationLevel) -> str:
        """
        优化英文提示词
        
        Args:
            text: 英文文本
            level: 优化级别
            
        Returns:
            str: 优化后的提示词
        """
        try:
            # 基础清理
            cleaned_text = re.sub(r'\s+', ' ', text).strip()
            
            # 根据级别应用不同的优化策略
            if level == PromptOptimizationLevel.BASIC:
                # 基础优化：添加质量关键词
                optimized = self._add_quality_keywords(cleaned_text, level)
            elif level == PromptOptimizationLevel.ENHANCED:
                # 增强优化：重构句式，添加技术参数
                optimized = self._enhance_prompt_structure(cleaned_text)
            else:  # PROFESSIONAL
                # 专业优化：全面重构，添加专业术语
                optimized = self._professional_optimization(cleaned_text)
            
            logger.debug(f"英文提示词优化: '{text}' -> '{optimized}'")
            return optimized
            
        except Exception as e:
            logger.error(f"英文提示词优化失败: {e}")
            return text
    
    def _add_quality_keywords(self, text: str, level: PromptOptimizationLevel) -> str:
        """添加质量关键词"""
        keywords = self.english_optimization_templates[level]
        
        # 检查是否已包含质量关键词
        text_lower = text.lower()
        missing_keywords = [kw for kw in keywords if kw.lower() not in text_lower]
        
        if missing_keywords:
            return f"{text}, {', '.join(missing_keywords)}"
        return text
    
    def _enhance_prompt_structure(self, text: str) -> str:
        """增强提示词结构"""
        # 分析文本结构
        parts = text.split(',')
        parts = [part.strip() for part in parts if part.strip()]
        
        # 重新组织结构：主题 + 风格 + 质量
        main_subject = parts[0] if parts else text
        style_parts = [p for p in parts[1:] if any(style in p.lower() for style in ['style', 'art', 'painting'])]
        other_parts = [p for p in parts[1:] if p not in style_parts]
        
        # 添加增强关键词
        enhanced_keywords = self.english_optimization_templates[PromptOptimizationLevel.ENHANCED]
        
        # 重新组合
        result_parts = [main_subject] + style_parts + other_parts + enhanced_keywords
        return ', '.join(result_parts)
    
    def _professional_optimization(self, text: str) -> str:
        """专业级优化"""
        # 应用专业模板
        professional_keywords = self.english_optimization_templates[PromptOptimizationLevel.PROFESSIONAL]
        
        # 分析并重构
        enhanced = self._enhance_prompt_structure(text)
        
        # 添加专业关键词
        return f"{enhanced}, {', '.join(professional_keywords)}"
    
    async def _apply_english_optimization(self, text: str, level: PromptOptimizationLevel) -> str:
        """应用英文优化"""
        return await self._optimize_english_prompt(text, level)
    
    def _calculate_quality_score(self, prompt: str, language: LanguageCode) -> float:
        """
        计算提示词质量分数
        
        Args:
            prompt: 提示词
            language: 语言
            
        Returns:
            float: 质量分数 (0-1)
        """
        try:
            score = 0.0
            factors = []
            
            # 长度评分 (0.2权重)
            length_score = min(len(prompt) / 100, 1.0)  # 100字符为满分
            factors.append(('length', length_score, 0.2))
            
            # 关键词丰富度评分 (0.3权重)
            if language == LanguageCode.ENGLISH:
                quality_keywords = ['detailed', 'high quality', 'professional', 'masterpiece']
                keyword_count = sum(1 for kw in quality_keywords if kw.lower() in prompt.lower())
                keyword_score = min(keyword_count / len(quality_keywords), 1.0)
            else:
                # 中文关键词评分
                keyword_score = 0.7  # 中文暂时给固定分数
            factors.append(('keywords', keyword_score, 0.3))
            
            # 结构完整性评分 (0.3权重)
            structure_score = self._evaluate_structure(prompt, language)
            factors.append(('structure', structure_score, 0.3))
            
            # 语言一致性评分 (0.2权重)
            consistency_score = self._evaluate_language_consistency(prompt, language)
            factors.append(('consistency', consistency_score, 0.2))
            
            # 计算加权平均分
            total_score = sum(score * weight for _, score, weight in factors)
            
            logger.debug(f"质量评分详情: {factors}, 总分: {total_score:.2f}")
            return round(total_score, 2)
            
        except Exception as e:
            logger.error(f"计算质量分数失败: {e}")
            return 0.5
    
    def _evaluate_structure(self, prompt: str, language: LanguageCode) -> float:
        """评估提示词结构"""
        # 检查是否有合理的分隔符
        separators = [',', '，', ';', '；']
        has_separators = any(sep in prompt for sep in separators)
        
        # 检查是否有重复内容
        words = prompt.lower().split()
        unique_ratio = len(set(words)) / len(words) if words else 0
        
        # 结构分数
        structure_score = 0.5
        if has_separators:
            structure_score += 0.3
        structure_score += unique_ratio * 0.2
        
        return min(structure_score, 1.0)
    
    def _evaluate_language_consistency(self, prompt: str, expected_language: LanguageCode) -> float:
        """评估语言一致性"""
        detected_language = self.language_detector.detect_language(prompt)
        
        if detected_language == expected_language:
            return 1.0
        else:
            # 检查混合程度
            stats = self.language_detector.get_language_statistics(prompt)
            if expected_language == LanguageCode.ENGLISH:
                return stats['english_ratio']
            else:
                return stats['chinese_ratio']
    
    def _generate_suggestions(self, original: str, processed: str, language: LanguageCode) -> List[str]:
        """
        生成改进建议
        
        Args:
            original: 原始文本
            processed: 处理后文本
            language: 目标语言
            
        Returns:
            List[str]: 建议列表
        """
        suggestions = []
        
        try:
            # 检查长度
            if len(processed) < 20:
                suggestions.append("建议增加更多描述细节以提高图像生成质量")
            
            # 检查质量关键词
            if language == LanguageCode.ENGLISH:
                quality_keywords = ['detailed', 'high quality', 'professional']
                missing_keywords = [kw for kw in quality_keywords if kw not in processed.lower()]
                if missing_keywords:
                    suggestions.append(f"建议添加质量关键词: {', '.join(missing_keywords)}")
            
            # 检查风格一致性
            if '风格' in original and 'style' not in processed.lower():
                suggestions.append("建议明确指定艺术风格")
            
            # 检查技术参数
            tech_keywords = ['4k', '8k', 'hd', 'resolution']
            if not any(kw in processed.lower() for kw in tech_keywords):
                suggestions.append("建议添加分辨率或质量参数")
            
            # 检查负面提示词建议
            if language in self.negative_prompts:
                suggestions.append(f"建议使用负面提示词避免: {', '.join(self.negative_prompts[language][:3])}")
            
        except Exception as e:
            logger.error(f"生成建议失败: {e}")
            suggestions.append("无法生成具体建议，请检查提示词格式")
        
        return suggestions
    
    async def validate_image_text_matching(self, image_prompt: str, text_content: str, 
                                         language: LanguageCode) -> MatchingResult:
        """
        验证图像提示词与文本内容的匹配度
        
        Args:
            image_prompt: 图像提示词
            text_content: 文本内容
            language: 语言
            
        Returns:
            MatchingResult: 匹配结果
        """
        try:
            logger.info(f"验证图像文本匹配度: 语言={language.value}")
            
            # 语义相似度分析
            semantic_similarity = await self._calculate_semantic_similarity(image_prompt, text_content, language)
            
            # 关键词重叠度分析
            keyword_overlap = self._calculate_keyword_overlap(image_prompt, text_content, language)
            
            # 风格一致性分析
            style_consistency = self._analyze_style_consistency(image_prompt, text_content, language)
            
            # 综合匹配分数
            match_score = (semantic_similarity * 0.4 + keyword_overlap * 0.4 + style_consistency * 0.2)
            
            # 生成问题和建议
            issues = []
            recommendations = []
            
            if match_score < 0.6:
                issues.append("图像提示词与文本内容匹配度较低")
                recommendations.append("建议调整图像提示词以更好地反映文本内容")
            
            if semantic_similarity < 0.5:
                issues.append("语义相似度不足")
                recommendations.append("建议增加与文本主题相关的关键词")
            
            if keyword_overlap < 0.3:
                issues.append("关键词重叠度较低")
                recommendations.append("建议在图像提示词中包含更多文本中的关键概念")
            
            return MatchingResult(
                match_score=round(match_score, 2),
                semantic_similarity=round(semantic_similarity, 2),
                keyword_overlap=round(keyword_overlap, 2),
                style_consistency=round(style_consistency, 2),
                issues=issues,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"验证图像文本匹配度失败: {e}")
            return MatchingResult(
                match_score=0.5,
                semantic_similarity=0.5,
                keyword_overlap=0.5,
                style_consistency=0.5,
                issues=[f"验证失败: {str(e)}"],
                recommendations=["请检查输入内容格式"]
            )
    
    async def _calculate_semantic_similarity(self, prompt: str, content: str, language: LanguageCode) -> float:
        """计算语义相似度"""
        try:
            # 简化的语义相似度计算
            # 提取关键词
            prompt_keywords = self._extract_keywords(prompt, language)
            content_keywords = self._extract_keywords(content, language)
            
            if not prompt_keywords or not content_keywords:
                return 0.3
            
            # 计算交集比例
            common_keywords = set(prompt_keywords) & set(content_keywords)
            similarity = len(common_keywords) / max(len(prompt_keywords), len(content_keywords))
            
            return min(similarity * 2, 1.0)  # 放大相似度
            
        except Exception as e:
            logger.error(f"计算语义相似度失败: {e}")
            return 0.3
    
    def _calculate_keyword_overlap(self, prompt: str, content: str, language: LanguageCode) -> float:
        """计算关键词重叠度"""
        try:
            # 提取关键词
            prompt_words = set(self._extract_keywords(prompt, language))
            content_words = set(self._extract_keywords(content, language))
            
            if not prompt_words or not content_words:
                return 0.2
            
            # 计算Jaccard相似度
            intersection = len(prompt_words & content_words)
            union = len(prompt_words | content_words)
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.error(f"计算关键词重叠度失败: {e}")
            return 0.2
    
    def _analyze_style_consistency(self, prompt: str, content: str, language: LanguageCode) -> float:
        """分析风格一致性"""
        try:
            # 检查风格关键词
            style_keywords = ['风格', 'style', '艺术', 'art', '画风', 'painting']
            
            prompt_has_style = any(kw in prompt.lower() for kw in style_keywords)
            content_has_style = any(kw in content.lower() for kw in style_keywords)
            
            if prompt_has_style and content_has_style:
                return 0.8
            elif prompt_has_style or content_has_style:
                return 0.6
            else:
                return 0.7  # 默认一致性
                
        except Exception as e:
            logger.error(f"分析风格一致性失败: {e}")
            return 0.5
    
    def _extract_keywords(self, text: str, language: LanguageCode) -> List[str]:
        """提取关键词"""
        try:
            if language == LanguageCode.CHINESE:
                # 中文关键词提取
                keywords = re.findall(r'[\u4e00-\u9fff]{2,}', text)
            else:
                # 英文关键词提取
                keywords = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            
            # 过滤常见停用词
            stop_words = {'的', '是', '在', '有', '和', 'the', 'is', 'in', 'and', 'or', 'but', 'with'}
            keywords = [kw for kw in keywords if kw not in stop_words]
            
            return keywords[:10]  # 返回前10个关键词
            
        except Exception as e:
            logger.error(f"提取关键词失败: {e}")
            return []
    
    def get_supported_languages(self) -> List[LanguageCode]:
        """获取支持的语言列表"""
        return [LanguageCode.CHINESE, LanguageCode.ENGLISH]
    
    def get_optimization_levels(self) -> List[PromptOptimizationLevel]:
        """获取支持的优化级别"""
        return list(PromptOptimizationLevel)
    
    def add_keyword_mapping(self, chinese: str, english: str):
        """添加关键词映射"""
        self.keyword_mapping[chinese] = english
        logger.info(f"添加关键词映射: {chinese} -> {english}")
    
    def get_keyword_mapping(self) -> Dict[str, str]:
        """获取关键词映射表"""
        return self.keyword_mapping.copy()
    
    def get_negative_prompts(self, language: LanguageCode) -> List[str]:
        """获取负面提示词"""
        return self.negative_prompts.get(language, [])