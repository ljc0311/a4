#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双语LLM服务
扩展LLM服务以支持中英双语模板和语言特定的文本处理
"""

import asyncio
from typing import Optional, Dict, Any

from src.services.llm_service import LLMService
from src.services.bilingual_template_manager import BilingualTemplateManager, TemplateType
from src.core.language_manager import LanguageManager
from src.models.language_models import LanguageCode
from src.core.service_base import ServiceResult
from src.core.api_manager import APIManager
from src.utils.logger import logger


class BilingualLLMService(LLMService):
    """双语LLM服务类"""
    
    def __init__(self, api_manager: APIManager, language_manager: Optional[LanguageManager] = None):
        super().__init__(api_manager)
        self.language_manager = language_manager
        self.template_manager = BilingualTemplateManager()
        
        # 如果提供了语言管理器，注册语言变更回调
        if self.language_manager:
            self.language_manager.add_language_change_callback(self._on_language_changed)
        
        logger.info("双语LLM服务初始化完成")
    
    def _on_language_changed(self, new_language: LanguageCode):
        """语言变更回调处理"""
        logger.info(f"LLM服务检测到语言变更: {new_language.value}")
    
    def _get_current_language(self) -> LanguageCode:
        """获取当前语言，如果没有语言管理器则默认使用中文"""
        if self.language_manager:
            return self.language_manager.current_language
        return LanguageCode.CHINESE
    
    async def create_story_bilingual(self, theme: str, language: Optional[LanguageCode] = None, provider: Optional[str] = None) -> ServiceResult:
        """
        根据主题创作双语故事
        
        Args:
            theme: 故事主题
            language: 目标语言，如果为None则使用当前语言
            provider: LLM提供商
            
        Returns:
            ServiceResult: 服务执行结果
        """
        try:
            target_language = language or self._get_current_language()
            
            logger.info(f"📚 双语LLM服务：开始故事创作")
            logger.info(f"  🎭 主题: {theme}")
            logger.info(f"  🌐 语言: {target_language.value}")
            logger.info(f"  🤖 提供商: {provider or '默认'}")
            
            # 获取语言特定的模板
            prompt = self.template_manager.format_template(
                TemplateType.STORY_CREATION,
                target_language,
                theme=theme
            )
            
            if prompt is None:
                error_msg = f"未找到 {target_language.value} 的故事创作模板"
                logger.error(f"  ❌ {error_msg}")
                return ServiceResult(success=False, error=error_msg)
            
            logger.info(f"  📝 提示词长度: {len(prompt)} 字符")
            
            # 根据语言调整参数
            max_tokens, temperature = self._get_language_specific_parameters(target_language, 'story_creation')
            logger.info(f"  ⚙️ 参数设置: max_tokens={max_tokens}, temperature={temperature}")
            
            # 调用LLM API
            result = await self.execute(
                provider=provider,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if result.success:
                content_length = len(result.data.get('content', ''))
                logger.info(f"  ✅ 故事创作完成，内容长度: {content_length} 字符")
                
                # 添加语言信息到结果元数据
                if result.metadata is None:
                    result.metadata = {}
                result.metadata['language'] = target_language.value
                result.metadata['template_type'] = TemplateType.STORY_CREATION.value
            else:
                logger.error(f"  ❌ 故事创作失败: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"双语故事创作失败: {e}")
            return ServiceResult(success=False, error=str(e))
    
    async def rewrite_text_bilingual(self, text: str, language: Optional[LanguageCode] = None, provider: Optional[str] = None) -> ServiceResult:
        """
        双语文本改写
        
        Args:
            text: 要改写的文本
            language: 目标语言，如果为None则使用当前语言
            provider: LLM提供商
            
        Returns:
            ServiceResult: 服务执行结果
        """
        try:
            target_language = language or self._get_current_language()
            
            logger.info(f"✏️ 双语LLM服务：开始文本改写")
            logger.info(f"  📝 原文长度: {len(text)} 字符")
            logger.info(f"  📄 原文预览: {text[:50]}...")
            logger.info(f"  🌐 语言: {target_language.value}")
            logger.info(f"  🤖 提供商: {provider or '默认'}")
            
            # 获取语言特定的模板
            prompt = self.template_manager.format_template(
                TemplateType.TEXT_REWRITE,
                target_language,
                text=text
            )
            
            if prompt is None:
                error_msg = f"未找到 {target_language.value} 的文本改写模板"
                logger.error(f"  ❌ {error_msg}")
                return ServiceResult(success=False, error=error_msg)
            
            logger.info(f"  📝 提示词长度: {len(prompt)} 字符")
            
            # 根据语言调整参数
            max_tokens, temperature = self._get_language_specific_parameters(target_language, 'text_rewrite')
            logger.info(f"  ⚙️ 参数设置: max_tokens={max_tokens}, temperature={temperature}")
            
            # 调用LLM API
            result = await self.execute(
                provider=provider,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if result.success:
                content_length = len(result.data.get('content', ''))
                logger.info(f"  ✅ 文本改写完成，内容长度: {content_length} 字符")
                
                # 添加语言信息到结果元数据
                if result.metadata is None:
                    result.metadata = {}
                result.metadata['language'] = target_language.value
                result.metadata['template_type'] = TemplateType.TEXT_REWRITE.value
            else:
                logger.error(f"  ❌ 文本改写失败: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"双语文本改写失败: {e}")
            return ServiceResult(success=False, error=str(e))
    
    async def generate_storyboard_bilingual(self, text: str, style: Optional[str] = None, language: Optional[LanguageCode] = None, provider: Optional[str] = None) -> ServiceResult:
        """
        双语分镜脚本生成
        
        Args:
            text: 文本内容
            style: 风格要求
            language: 目标语言，如果为None则使用当前语言
            provider: LLM提供商
            
        Returns:
            ServiceResult: 服务执行结果
        """
        try:
            target_language = language or self._get_current_language()
            
            # 如果没有指定风格，使用语言特定的默认风格
            if style is None:
                style = "电影风格" if target_language == LanguageCode.CHINESE else "Cinematic Style"
            
            logger.info(f"🎬 双语LLM服务：开始分镜脚本生成")
            logger.info(f"  📝 文本长度: {len(text)} 字符")
            logger.info(f"  🎨 风格: {style}")
            logger.info(f"  🌐 语言: {target_language.value}")
            logger.info(f"  🤖 提供商: {provider or '默认'}")
            
            # 获取语言特定的模板
            prompt = self.template_manager.format_template(
                TemplateType.STORYBOARD_GENERATION,
                target_language,
                text=text,
                style=style
            )
            
            if prompt is None:
                error_msg = f"未找到 {target_language.value} 的分镜生成模板"
                logger.error(f"  ❌ {error_msg}")
                return ServiceResult(success=False, error=error_msg)
            
            logger.info(f"  📝 提示词长度: {len(prompt)} 字符")
            
            # 根据语言调整参数
            max_tokens, temperature = self._get_language_specific_parameters(target_language, 'storyboard_generation')
            logger.info(f"  ⚙️ 参数设置: max_tokens={max_tokens}, temperature={temperature}")
            
            # 调用LLM API
            result = await self.execute(
                provider=provider,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if result.success:
                content_length = len(result.data.get('content', ''))
                logger.info(f"  ✅ 分镜脚本生成完成，内容长度: {content_length} 字符")
                
                # 添加语言信息到结果元数据
                if result.metadata is None:
                    result.metadata = {}
                result.metadata['language'] = target_language.value
                result.metadata['template_type'] = TemplateType.STORYBOARD_GENERATION.value
                result.metadata['style'] = style
            else:
                logger.error(f"  ❌ 分镜脚本生成失败: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"双语分镜脚本生成失败: {e}")
            return ServiceResult(success=False, error=str(e))
    
    async def translate_text(self, source_text: str, source_language: LanguageCode, target_language: LanguageCode, provider: Optional[str] = None) -> ServiceResult:
        """
        文本翻译功能
        
        Args:
            source_text: 源文本
            source_language: 源语言
            target_language: 目标语言
            provider: LLM提供商
            
        Returns:
            ServiceResult: 服务执行结果
        """
        try:
            logger.info(f"🌐 双语LLM服务：开始文本翻译")
            logger.info(f"  📝 源文本长度: {len(source_text)} 字符")
            logger.info(f"  📄 源文本预览: {source_text[:50]}...")
            logger.info(f"  🔄 翻译方向: {source_language.value} -> {target_language.value}")
            logger.info(f"  🤖 提供商: {provider or '默认'}")
            
            # 验证翻译方向
            if source_language == target_language:
                error_msg = "源语言和目标语言不能相同"
                logger.error(f"  ❌ {error_msg}")
                return ServiceResult(success=False, error=error_msg)
            
            # 检查是否支持该翻译方向
            supported_pairs = [
                (LanguageCode.CHINESE, LanguageCode.ENGLISH),
                (LanguageCode.ENGLISH, LanguageCode.CHINESE)
            ]
            
            if (source_language, target_language) not in supported_pairs:
                error_msg = f"不支持的翻译方向: {source_language.value} -> {target_language.value}"
                logger.error(f"  ❌ {error_msg}")
                return ServiceResult(success=False, error=error_msg)
            
            # 获取翻译模板（使用目标语言的模板）
            prompt = self.template_manager.format_template(
                TemplateType.TEXT_TRANSLATION,
                target_language,
                source_text=source_text
            )
            
            if prompt is None:
                error_msg = f"未找到 {target_language.value} 的翻译模板"
                logger.error(f"  ❌ {error_msg}")
                return ServiceResult(success=False, error=error_msg)
            
            logger.info(f"  📝 提示词长度: {len(prompt)} 字符")
            
            # 根据语言调整参数
            max_tokens, temperature = self._get_language_specific_parameters(target_language, 'text_translation')
            logger.info(f"  ⚙️ 参数设置: max_tokens={max_tokens}, temperature={temperature}")
            
            # 调用LLM API，带重试机制
            max_retries = 3
            retry_count = 0
            result = None
            
            while retry_count < max_retries:
                try:
                    result = await self.execute(
                        provider=provider,
                        prompt=prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    
                    if result.success:
                        break
                    else:
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.warning(f"  ⚠️ 翻译失败，进行第 {retry_count} 次重试: {result.error}")
                            await asyncio.sleep(1)  # 等待1秒后重试
                        else:
                            logger.error(f"  ❌ 翻译失败，已达到最大重试次数: {result.error}")
                            
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"  ⚠️ 翻译异常，进行第 {retry_count} 次重试: {e}")
                        await asyncio.sleep(1)
                    else:
                        logger.error(f"  ❌ 翻译异常，已达到最大重试次数: {e}")
                        result = ServiceResult(success=False, error=str(e))
            
            if result and result.success:
                translated_text = result.data.get('content', '').strip()
                content_length = len(translated_text)
                logger.info(f"  ✅ 文本翻译完成，译文长度: {content_length} 字符")
                logger.info(f"  📄 译文预览: {translated_text[:50]}...")
                
                # 添加翻译信息到结果元数据
                if result.metadata is None:
                    result.metadata = {}
                result.metadata.update({
                    'source_language': source_language.value,
                    'target_language': target_language.value,
                    'template_type': TemplateType.TEXT_TRANSLATION.value,
                    'source_text_length': len(source_text),
                    'translated_text_length': content_length
                })
                
                # 进行基本的翻译质量检测
                quality_check = self._validate_translation_quality(source_text, translated_text, source_language, target_language)
                result.metadata['quality_check'] = quality_check
                
                if not quality_check['is_valid']:
                    logger.warning(f"  ⚠️ 翻译质量检测发现问题: {quality_check['issues']}")
            else:
                logger.error(f"  ❌ 文本翻译失败: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"文本翻译失败: {e}")
            return ServiceResult(success=False, error=str(e))

    async def optimize_prompt_bilingual(self, prompt: str, style: str = None, language: Optional[LanguageCode] = None, provider: Optional[str] = None) -> ServiceResult:
        """
        双语提示词优化
        
        Args:
            prompt: 原始提示词
            style: 风格要求
            language: 目标语言，如果为None则使用当前语言
            provider: LLM提供商
            
        Returns:
            ServiceResult: 服务执行结果
        """
        try:
            target_language = language or self._get_current_language()
            
            # 如果没有指定风格，使用语言特定的默认风格
            if style is None:
                style = "写实风格" if target_language == LanguageCode.CHINESE else "Realistic Style"
            
            logger.info(f"🎨 双语LLM服务：开始提示词优化")
            logger.info(f"  📝 原始提示词长度: {len(prompt)} 字符")
            logger.info(f"  🎨 风格: {style}")
            logger.info(f"  🌐 语言: {target_language.value}")
            logger.info(f"  🤖 提供商: {provider or '默认'}")
            
            # 获取语言特定的模板
            optimization_prompt = self.template_manager.format_template(
                TemplateType.PROMPT_OPTIMIZATION,
                target_language,
                prompt=prompt,
                style=style
            )
            
            if optimization_prompt is None:
                error_msg = f"未找到 {target_language.value} 的提示词优化模板"
                logger.error(f"  ❌ {error_msg}")
                return ServiceResult(success=False, error=error_msg)
            
            logger.info(f"  📝 优化提示词长度: {len(optimization_prompt)} 字符")
            
            # 根据语言调整参数
            max_tokens, temperature = self._get_language_specific_parameters(target_language, 'prompt_optimization')
            logger.info(f"  ⚙️ 参数设置: max_tokens={max_tokens}, temperature={temperature}")
            
            # 调用LLM API
            result = await self.execute(
                provider=provider,
                prompt=optimization_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if result.success:
                content_length = len(result.data.get('content', ''))
                logger.info(f"  ✅ 提示词优化完成，内容长度: {content_length} 字符")
                
                # 添加语言信息到结果元数据
                if result.metadata is None:
                    result.metadata = {}
                result.metadata['language'] = target_language.value
                result.metadata['template_type'] = TemplateType.PROMPT_OPTIMIZATION.value
                result.metadata['style'] = style
            else:
                logger.error(f"  ❌ 提示词优化失败: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"双语提示词优化失败: {e}")
            return ServiceResult(success=False, error=str(e))
    
    def _get_language_specific_parameters(self, language: LanguageCode, task_type: str) -> tuple[int, float]:
        """
        获取语言特定的参数设置
        
        Args:
            language: 语言代码
            task_type: 任务类型
            
        Returns:
            tuple[int, float]: (max_tokens, temperature)
        """
        # 基础参数设置
        base_params = {
            'story_creation': (2500, 0.9),
            'text_rewrite': (1500, 0.8),
            'storyboard_generation': (2000, 0.7),
            'prompt_optimization': (1000, 0.6),
            'text_translation': (2000, 0.3)  # 翻译需要更低的温度以确保准确性
        }
        
        max_tokens, temperature = base_params.get(task_type, (2000, 0.7))
        
        # 根据语言调整参数
        if language == LanguageCode.ENGLISH:
            # 英文通常需要更多token，因为英文单词平均长度较长
            max_tokens = int(max_tokens * 1.2)
        elif language == LanguageCode.CHINESE:
            # 中文字符密度较高，可以适当减少token数
            max_tokens = int(max_tokens * 0.9)
        
        return max_tokens, temperature
    
    def _validate_translation_quality(self, source_text: str, translated_text: str, source_language: LanguageCode, target_language: LanguageCode) -> Dict[str, Any]:
        """
        验证翻译质量
        
        Args:
            source_text: 源文本
            translated_text: 译文
            source_language: 源语言
            target_language: 目标语言
            
        Returns:
            Dict[str, Any]: 质量检测结果
        """
        issues = []
        
        try:
            # 基本检查
            if not translated_text or translated_text.strip() == "":
                issues.append("译文为空")
                return {'is_valid': False, 'issues': issues, 'score': 0.0}
            
            # 长度检查 - 译文长度不应该与原文相差过大
            source_len = len(source_text.strip())
            translated_len = len(translated_text.strip())
            
            if source_len > 0:
                length_ratio = translated_len / source_len
                if length_ratio < 0.3:
                    issues.append("译文过短，可能存在内容丢失")
                elif length_ratio > 3.0:
                    issues.append("译文过长，可能存在冗余内容")
            
            # 语言检查
            if target_language == LanguageCode.ENGLISH:
                # 检查是否包含中文字符
                chinese_chars = sum(1 for char in translated_text if '\u4e00' <= char <= '\u9fff')
                if chinese_chars > len(translated_text) * 0.1:  # 如果中文字符超过10%
                    issues.append("英文译文中包含过多中文字符")
            elif target_language == LanguageCode.CHINESE:
                # 检查是否主要是英文
                english_chars = sum(1 for char in translated_text if char.isascii() and char.isalpha())
                if english_chars > len(translated_text) * 0.5:  # 如果英文字符超过50%
                    issues.append("中文译文中包含过多英文字符")
            
            # 格式检查 - 检查是否保持了原文的段落结构
            source_paragraphs = len(source_text.split('\n\n'))
            translated_paragraphs = len(translated_text.split('\n\n'))
            if abs(source_paragraphs - translated_paragraphs) > 1:
                issues.append("译文段落结构与原文差异较大")
            
            # 计算质量分数
            score = 1.0
            if issues:
                score = max(0.0, 1.0 - len(issues) * 0.2)
            
            return {
                'is_valid': len(issues) == 0,
                'issues': issues,
                'score': score,
                'length_ratio': length_ratio if source_len > 0 else 1.0,
                'source_length': source_len,
                'translated_length': translated_len
            }
            
        except Exception as e:
            logger.error(f"翻译质量检测失败: {e}")
            return {
                'is_valid': False,
                'issues': [f"质量检测失败: {str(e)}"],
                'score': 0.0
            }
    
    def get_supported_languages(self) -> list[LanguageCode]:
        """获取支持的语言列表"""
        return [LanguageCode.CHINESE, LanguageCode.ENGLISH]
    
    def get_available_templates(self, language: Optional[LanguageCode] = None) -> Dict[str, bool]:
        """
        获取可用的模板列表
        
        Args:
            language: 语言代码，如果为None则使用当前语言
            
        Returns:
            Dict[str, bool]: 模板类型和可用性的映射
        """
        target_language = language or self._get_current_language()
        
        templates = {}
        for template_type in self.template_manager.get_available_template_types():
            template = self.template_manager.get_template(template_type, target_language)
            templates[template_type.value] = template is not None
        
        return templates
    
    def validate_language_support(self, language: LanguageCode) -> Dict[str, Any]:
        """
        验证语言支持情况
        
        Args:
            language: 要验证的语言代码
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        supported_languages = self.get_supported_languages()
        is_supported = language in supported_languages
        
        available_templates = {}
        if is_supported:
            for template_type in self.template_manager.get_available_template_types():
                template = self.template_manager.get_template(template_type, language)
                available_templates[template_type.value] = template is not None
        
        return {
            'is_supported': is_supported,
            'language': language.value,
            'supported_languages': [lang.value for lang in supported_languages],
            'available_templates': available_templates
        }
    
    def get_debug_info(self) -> Dict[str, Any]:
        """获取调试信息"""
        current_language = self._get_current_language()
        
        return {
            'service_type': 'BilingualLLMService',
            'current_language': current_language.value,
            'has_language_manager': self.language_manager is not None,
            'supported_languages': [lang.value for lang in self.get_supported_languages()],
            'available_templates': self.get_available_templates(current_language),
            'template_manager_info': self.template_manager.get_debug_info()
        }