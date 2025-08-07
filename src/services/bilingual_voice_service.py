#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双语语音服务
扩展VoiceService类，添加语言特定的音色管理和自动降级机制
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from src.services.voice_service import VoiceService
from src.core.language_manager import LanguageManager
from src.models.language_models import LanguageCode, VoiceModel
from src.core.service_base import ServiceResult
from src.core.api_manager import APIManager, APIType
from src.models.llm_api import LLMApi
from src.utils.logger import logger


class VoiceModelManager:
    """语音模型管理器"""
    
    def __init__(self):
        # 预定义的语音模型配置
        self.voice_models = {
            # Azure Edge TTS 中文音色
            "zh-CN-YunxiNeural": VoiceModel(
                id="zh-CN-YunxiNeural",
                name="云希-男声",
                language=LanguageCode.CHINESE,
                gender="male",
                style="natural",
                provider="azure"
            ),
            "zh-CN-XiaoxiaoNeural": VoiceModel(
                id="zh-CN-XiaoxiaoNeural",
                name="晓晓-女声",
                language=LanguageCode.CHINESE,
                gender="female",
                style="natural",
                provider="azure"
            ),
            "zh-CN-YunyangNeural": VoiceModel(
                id="zh-CN-YunyangNeural",
                name="云扬-男声",
                language=LanguageCode.CHINESE,
                gender="male",
                style="energetic",
                provider="azure"
            ),
            "zh-CN-XiaoyiNeural": VoiceModel(
                id="zh-CN-XiaoyiNeural",
                name="晓伊-女声",
                language=LanguageCode.CHINESE,
                gender="female",
                style="gentle",
                provider="azure"
            ),
            
            # Azure Edge TTS 英文音色（更新为实际可用的音色）
            "en-US-AvaNeural": VoiceModel(
                id="en-US-AvaNeural",
                name="Ava-Female",
                language=LanguageCode.ENGLISH,
                gender="female",
                style="natural",
                provider="azure"
            ),
            "en-US-AndrewNeural": VoiceModel(
                id="en-US-AndrewNeural",
                name="Andrew-Male",
                language=LanguageCode.ENGLISH,
                gender="male",
                style="natural",
                provider="azure"
            ),
            "en-US-EmmaNeural": VoiceModel(
                id="en-US-EmmaNeural",
                name="Emma-Female",
                language=LanguageCode.ENGLISH,
                gender="female",
                style="friendly",
                provider="azure"
            ),
            "en-US-BrianNeural": VoiceModel(
                id="en-US-BrianNeural",
                name="Brian-Male",
                language=LanguageCode.ENGLISH,
                gender="male",
                style="professional",
                provider="azure"
            ),
            "en-US-AnaNeural": VoiceModel(
                id="en-US-AnaNeural",
                name="Ana-Female",
                language=LanguageCode.ENGLISH,
                gender="female",
                style="warm",
                provider="azure"
            ),
            
            # OpenAI TTS 音色（多语言支持）
            "alloy": VoiceModel(
                id="alloy",
                name="Alloy-Neutral",
                language=LanguageCode.ENGLISH,
                gender="neutral",
                style="balanced",
                provider="openai"
            ),
            "echo": VoiceModel(
                id="echo",
                name="Echo-Male",
                language=LanguageCode.ENGLISH,
                gender="male",
                style="deep",
                provider="openai"
            ),
            "nova": VoiceModel(
                id="nova",
                name="Nova-Female",
                language=LanguageCode.ENGLISH,
                gender="female",
                style="bright",
                provider="openai"
            ),
            "onyx": VoiceModel(
                id="onyx",
                name="Onyx-Male",
                language=LanguageCode.ENGLISH,
                gender="male",
                style="warm",
                provider="openai"
            )
        }
        
        # 语音引擎优先级配置（只使用免费的Edge-TTS）
        self.provider_priority = {
            LanguageCode.CHINESE: ["azure"],
            LanguageCode.ENGLISH: ["azure"]
        }
        
        # 备用音色配置
        self.fallback_voices = {
            LanguageCode.CHINESE: [
                "zh-CN-XiaoxiaoNeural",
                "zh-CN-YunxiNeural",
                "zh-CN-YunyangNeural"
            ],
            LanguageCode.ENGLISH: [
                "en-US-AvaNeural",
                "en-US-AndrewNeural",
                "en-US-EmmaNeural"
            ]
        }
    
    def get_voices_for_language(self, language: LanguageCode) -> List[VoiceModel]:
        """
        获取指定语言的所有可用音色
        
        Args:
            language: 语言代码
            
        Returns:
            List[VoiceModel]: 音色模型列表
        """
        return [
            voice for voice in self.voice_models.values()
            if voice.language == language
        ]
    
    def get_voice_by_id(self, voice_id: str) -> Optional[VoiceModel]:
        """
        根据ID获取音色模型
        
        Args:
            voice_id: 音色ID
            
        Returns:
            Optional[VoiceModel]: 音色模型，如果不存在则返回None
        """
        return self.voice_models.get(voice_id)
    
    def get_voices_by_provider(self, provider: str, language: Optional[LanguageCode] = None) -> List[VoiceModel]:
        """
        获取指定提供商的音色列表
        
        Args:
            provider: 提供商名称
            language: 可选的语言过滤
            
        Returns:
            List[VoiceModel]: 音色模型列表
        """
        voices = [
            voice for voice in self.voice_models.values()
            if voice.provider.lower() == provider.lower()
        ]
        
        if language:
            voices = [voice for voice in voices if voice.language == language]
        
        return voices
    
    def get_fallback_voices(self, language: LanguageCode) -> List[str]:
        """
        获取指定语言的备用音色列表
        
        Args:
            language: 语言代码
            
        Returns:
            List[str]: 备用音色ID列表
        """
        return self.fallback_voices.get(language, [])
    
    def get_provider_priority(self, language: LanguageCode) -> List[str]:
        """
        获取指定语言的提供商优先级
        
        Args:
            language: 语言代码
            
        Returns:
            List[str]: 提供商优先级列表
        """
        return self.provider_priority.get(language, ["azure", "openai", "local"])
    
    def add_voice_model(self, voice_model: VoiceModel):
        """
        添加新的音色模型
        
        Args:
            voice_model: 音色模型
        """
        self.voice_models[voice_model.id] = voice_model
        logger.info(f"已添加音色模型: {voice_model.name} ({voice_model.id})")
    
    def remove_voice_model(self, voice_id: str) -> bool:
        """
        移除音色模型
        
        Args:
            voice_id: 音色ID
            
        Returns:
            bool: 是否成功移除
        """
        if voice_id in self.voice_models:
            removed_voice = self.voice_models.pop(voice_id)
            logger.info(f"已移除音色模型: {removed_voice.name} ({voice_id})")
            return True
        return False


class BilingualVoiceService(VoiceService):
    """双语语音服务类"""
    
    def __init__(self, api_manager: Optional[APIManager], language_manager: Optional[LanguageManager] = None):
        super().__init__(api_manager)
        self.language_manager = language_manager or LanguageManager()
        self.voice_model_manager = VoiceModelManager()
        self.api_manager = api_manager
        
        # 初始化双语LLM服务用于翻译
        self.llm_service = None
        if api_manager:
            from src.services.bilingual_llm_service import BilingualLLMService
            self.llm_service = BilingualLLMService(api_manager, self.language_manager)
        
        # 翻译文本缓存，用于避免重复翻译
        self.translation_cache = {}
        
        # 数据库存储配置（这里使用简单的文件存储作为示例）
        self.translation_storage_path = Path("data/translations")
        
        # 语言特定的语音参数配置
        self.language_voice_params = {
            LanguageCode.CHINESE: {
                'speed': 1.0,
                'pitch': 0,
                'volume': 1.0,
                'pause_duration': 0.3,  # 中文语音停顿时间
                'sentence_break': 0.5   # 句子间停顿
            },
            LanguageCode.ENGLISH: {
                'speed': 0.9,
                'pitch': 2,
                'volume': 1.0,
                'pause_duration': 0.2,  # 英文语音停顿时间
                'sentence_break': 0.4   # 句子间停顿
            }
        }
        
        # 注册语言变更回调
        self.language_manager.add_language_change_callback(self._on_language_changed)
        
        # 确保翻译存储目录存在
        self.translation_storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("双语语音服务初始化完成")

    async def translate_text_for_voice(self, text: str, source_language: LanguageCode, target_language: LanguageCode, project_id: Optional[str] = None) -> Optional[str]:
        """
        为配音翻译文本，支持缓存和数据库存储
        
        Args:
            text: 要翻译的文本
            source_language: 源语言
            target_language: 目标语言
            project_id: 项目ID，用于数据库存储
            
        Returns:
            Optional[str]: 翻译后的文本，如果失败则返回None
        """
        if not self.llm_service:
            logger.error("双语LLM服务未初始化，无法进行翻译")
            return None

        try:
            # 生成缓存键
            cache_key = f"{hash(text)}_{source_language.value}_{target_language.value}"
            
            # 检查缓存
            if cache_key in self.translation_cache:
                logger.info(f"使用缓存的翻译结果: {text[:20]}...")
                return self.translation_cache[cache_key]
            
            # 检查数据库存储
            stored_translation = self._load_translation_from_storage(text, source_language, target_language, project_id)
            if stored_translation:
                logger.info(f"从存储中加载翻译结果: {text[:20]}...")
                self.translation_cache[cache_key] = stored_translation
                return stored_translation
            
            logger.info(f"🌐 开始翻译文本用于配音: {text[:50]}...")
            
            # 使用双语LLM服务进行翻译
            result = await self.llm_service.translate_text(
                source_text=text,
                source_language=source_language,
                target_language=target_language
            )
            
            if result.success:
                translated_text = result.data.get('content', '').strip()
                
                if translated_text:
                    # 缓存翻译结果
                    self.translation_cache[cache_key] = translated_text
                    
                    # 保存到数据库
                    self._save_translation_to_storage(
                        original_text=text,
                        translated_text=translated_text,
                        source_language=source_language,
                        target_language=target_language,
                        project_id=project_id,
                        quality_score=result.metadata.get('quality_check', {}).get('score', 1.0)
                    )
                    
                    logger.info(f"✅ 文本翻译成功: {text[:20]}... -> {translated_text[:20]}...")
                    return translated_text
                else:
                    logger.error("翻译结果为空")
                    return None
            else:
                logger.error(f"翻译失败: {result.error}")
                return None

        except Exception as e:
            logger.error(f"文本翻译异常: {e}")
            return None
    
    def _save_translation_to_storage(self, original_text: str, translated_text: str, 
                                   source_language: LanguageCode, target_language: LanguageCode,
                                   project_id: Optional[str] = None, quality_score: float = 1.0):
        """
        保存翻译结果到存储
        
        Args:
            original_text: 原文
            translated_text: 译文
            source_language: 源语言
            target_language: 目标语言
            project_id: 项目ID
            quality_score: 翻译质量分数
        """
        try:
            import json
            from datetime import datetime
            
            # 生成存储文件名
            text_hash = hash(original_text)
            filename = f"translation_{abs(text_hash)}_{source_language.value}_{target_language.value}.json"
            file_path = self.translation_storage_path / filename
            
            # 准备存储数据
            translation_data = {
                'original_text': original_text,
                'translated_text': translated_text,
                'source_language': source_language.value,
                'target_language': target_language.value,
                'project_id': project_id,
                'quality_score': quality_score,
                'created_at': datetime.now().isoformat(),
                'text_hash': text_hash
            }
            
            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(translation_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"翻译结果已保存到: {file_path}")
            
        except Exception as e:
            logger.error(f"保存翻译结果失败: {e}")
    
    def _load_translation_from_storage(self, text: str, source_language: LanguageCode, 
                                     target_language: LanguageCode, project_id: Optional[str] = None) -> Optional[str]:
        """
        从存储中加载翻译结果
        
        Args:
            text: 原文
            source_language: 源语言
            target_language: 目标语言
            project_id: 项目ID
            
        Returns:
            Optional[str]: 翻译结果，如果不存在则返回None
        """
        try:
            import json
            
            # 生成存储文件名
            text_hash = hash(text)
            filename = f"translation_{abs(text_hash)}_{source_language.value}_{target_language.value}.json"
            file_path = self.translation_storage_path / filename
            
            if not file_path.exists():
                return None
            
            # 从文件加载数据
            with open(file_path, 'r', encoding='utf-8') as f:
                translation_data = json.load(f)
            
            # 验证数据完整性
            if (translation_data.get('original_text') == text and
                translation_data.get('source_language') == source_language.value and
                translation_data.get('target_language') == target_language.value):
                
                logger.debug(f"从存储加载翻译结果: {file_path}")
                return translation_data.get('translated_text')
            
            return None
            
        except Exception as e:
            logger.error(f"加载翻译结果失败: {e}")
            return None
    
    def get_translation_history(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取翻译历史记录
        
        Args:
            project_id: 项目ID，如果为None则返回所有记录
            
        Returns:
            List[Dict[str, Any]]: 翻译历史记录列表
        """
        try:
            import json
            from pathlib import Path
            
            history = []
            
            # 遍历存储目录中的所有翻译文件
            for file_path in self.translation_storage_path.glob("translation_*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        translation_data = json.load(f)
                    
                    # 如果指定了项目ID，则过滤
                    if project_id and translation_data.get('project_id') != project_id:
                        continue
                    
                    history.append(translation_data)
                    
                except Exception as e:
                    logger.warning(f"读取翻译文件失败 {file_path}: {e}")
                    continue
            
            # 按创建时间排序
            history.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return history
            
        except Exception as e:
            logger.error(f"获取翻译历史失败: {e}")
            return []
    
    def clear_translation_cache(self):
        """清空翻译缓存"""
        self.translation_cache.clear()
        logger.info("翻译缓存已清空")
    
    def _detect_text_language(self, text: str) -> LanguageCode:
        """
        简单的文本语言检测
        
        Args:
            text: 要检测的文本
            
        Returns:
            LanguageCode: 检测到的语言代码
        """
        try:
            # 统计中文字符数量
            chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
            total_chars = len(text.strip())
            
            if total_chars == 0:
                return self.language_manager.current_language
            
            # 如果中文字符占比超过30%，认为是中文
            chinese_ratio = chinese_chars / total_chars
            
            if chinese_ratio > 0.3:
                return LanguageCode.CHINESE
            else:
                return LanguageCode.ENGLISH
                
        except Exception as e:
            logger.warning(f"语言检测失败，使用当前语言: {e}")
            return self.language_manager.current_language
    
    def get_voices_for_language(self, language: Optional[LanguageCode] = None) -> List[VoiceModel]:
        """
        根据语言筛选可用音色
        
        Args:
            language: 语言代码，如果为None则使用当前语言
            
        Returns:
            List[VoiceModel]: 可用音色列表
        """
        target_language = language or self.language_manager.current_language
        return self.voice_model_manager.get_voices_for_language(target_language)
    
    def get_optimal_voice_settings(self, language: Optional[LanguageCode] = None) -> Dict[str, Any]:
        """
        获取语言特定的最优语音设置
        
        Args:
            language: 语言代码，如果为None则使用当前语言
            
        Returns:
            Dict[str, Any]: 语音参数设置
        """
        target_language = language or self.language_manager.current_language
        base_params = self.language_voice_params.get(target_language, {})
        
        # 从语言管理器获取用户自定义设置
        language_config = self.language_manager.get_language_config(target_language)
        voice_settings = language_config.voice_settings
        
        # 合并设置
        optimal_settings = base_params.copy()
        optimal_settings.update({
            'speed': voice_settings.default_speed,
            'pitch': voice_settings.default_pitch,
            'volume': voice_settings.default_volume,
            'voice': voice_settings.default_voice_id
        })
        
        return optimal_settings
    
    async def text_to_speech_bilingual(self, text: str, language: Optional[LanguageCode] = None, 
                                     voice_id: Optional[str] = None, project_id: Optional[str] = None, 
                                     auto_translate: bool = True, **kwargs) -> ServiceResult:
        """
        双语文本转语音，支持自动翻译、降级和备用机制
        
        Args:
            text: 要转换的文本
            language: 语言代码，如果为None则使用当前语言
            voice_id: 指定的音色ID，如果为None则使用默认音色
            project_id: 项目ID，用于翻译结果存储
            auto_translate: 是否自动翻译文本以匹配目标语言
            **kwargs: 其他语音参数
            
        Returns:
            ServiceResult: 语音合成结果
        """
        target_language = language or self.language_manager.current_language
        
        # 检测文本语言并进行翻译（如果需要）
        processed_text = text
        translation_used = False
        
        if auto_translate and self.llm_service:
            # 简单的语言检测（基于字符特征）
            detected_language = self._detect_text_language(text)
            
            if detected_language != target_language:
                logger.info(f"检测到文本语言 {detected_language.value}，目标语言 {target_language.value}，开始翻译")
                
                translated_text = await self.translate_text_for_voice(
                    text=text,
                    source_language=detected_language,
                    target_language=target_language,
                    project_id=project_id
                )
                
                if translated_text:
                    processed_text = translated_text
                    translation_used = True
                    logger.info(f"使用翻译后的文本进行语音合成: {processed_text[:50]}...")
                else:
                    logger.warning("翻译失败，使用原文进行语音合成")
        
        # 获取语言特定的最优设置
        optimal_settings = self.get_optimal_voice_settings(target_language)
        
        # 合并用户提供的参数
        voice_params = optimal_settings.copy()
        voice_params.update(kwargs)
        
        # 确定使用的音色
        if voice_id:
            voice_model = self.voice_model_manager.get_voice_by_id(voice_id)
            if not voice_model or voice_model.language != target_language:
                logger.warning(f"指定的音色 {voice_id} 不适用于语言 {target_language.value}，使用默认音色")
                voice_id = None
        
        if not voice_id:
            language_config = self.language_manager.get_language_config(target_language)
            voice_id = language_config.voice_settings.default_voice_id
        
        # 尝试使用不同的提供商进行语音合成
        providers = self.voice_model_manager.get_provider_priority(target_language)
        last_error = None
        
        for provider in providers:
            try:
                # 获取该提供商支持的音色
                provider_voices = self.voice_model_manager.get_voices_by_provider(provider, target_language)
                if not provider_voices:
                    continue
                
                # 查找匹配的音色或使用第一个可用音色
                selected_voice = voice_id
                if not any(v.id == voice_id for v in provider_voices):
                    selected_voice = provider_voices[0].id
                    logger.info(f"音色 {voice_id} 在提供商 {provider} 中不可用，使用 {selected_voice}")
                
                # 从voice_params中移除voice参数以避免冲突
                voice_params_clean = voice_params.copy()
                voice_params_clean.pop('voice', None)
                
                # 调用父类的文本转语音方法
                result = await super().text_to_speech(
                    text=processed_text,
                    voice=selected_voice,
                    provider=provider,
                    **voice_params_clean
                )
                
                if result.success:
                    # 添加语言信息到元数据
                    if result.metadata is None:
                        result.metadata = {}
                    result.metadata.update({
                        'language': target_language.value,
                        'voice_model': selected_voice,
                        'provider_used': provider,
                        'fallback_used': provider != providers[0] if len(providers) > 1 else False,
                        'translation_used': translation_used,
                        'original_text': text if translation_used else None,
                        'processed_text': processed_text,
                        'project_id': project_id
                    })
                    
                    logger.info(f"语音合成成功: 语言={target_language.value}, 音色={selected_voice}, 提供商={provider}")
                    return result
                else:
                    last_error = result.error
                    logger.warning(f"提供商 {provider} 语音合成失败: {result.error}")
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"提供商 {provider} 语音合成异常: {e}")
                continue
        
        # 所有提供商都失败，尝试备用音色
        return await self._try_fallback_voices(processed_text, target_language, voice_params, last_error)
    
    async def _try_fallback_voices(self, text: str, language: LanguageCode, 
                                 voice_params: Dict[str, Any], last_error: str) -> ServiceResult:
        """
        尝试使用备用音色进行语音合成
        
        Args:
            text: 要转换的文本
            language: 语言代码
            voice_params: 语音参数
            last_error: 上次的错误信息
            
        Returns:
            ServiceResult: 语音合成结果
        """
        fallback_voices = self.voice_model_manager.get_fallback_voices(language)
        
        for fallback_voice in fallback_voices:
            try:
                voice_model = self.voice_model_manager.get_voice_by_id(fallback_voice)
                if not voice_model:
                    continue
                
                logger.info(f"尝试备用音色: {fallback_voice}")
                
                # 从voice_params中移除voice参数以避免冲突
                voice_params_clean = voice_params.copy()
                voice_params_clean.pop('voice', None)
                
                result = await super().text_to_speech(
                    text=text,
                    voice=fallback_voice,
                    provider=voice_model.provider,
                    **voice_params_clean
                )
                
                if result.success:
                    if result.metadata is None:
                        result.metadata = {}
                    result.metadata.update({
                        'language': language.value,
                        'voice_model': fallback_voice,
                        'provider_used': voice_model.provider,
                        'fallback_used': True,
                        'is_emergency_fallback': True
                    })
                    
                    logger.info(f"备用音色合成成功: {fallback_voice}")
                    return result
                    
            except Exception as e:
                logger.error(f"备用音色 {fallback_voice} 合成失败: {e}")
                continue
        
        # 所有备用方案都失败
        return ServiceResult(
            success=False,
            error=f"所有语音合成方案都失败，最后错误: {last_error}",
            metadata={'language': language.value, 'error_type': 'all_fallbacks_failed'}
        )
    
    async def batch_text_to_speech_bilingual(self, texts: List[str], language: Optional[LanguageCode] = None,
                                           voice_id: Optional[str] = None, **kwargs) -> List[ServiceResult]:
        """
        批量双语文本转语音
        
        Args:
            texts: 文本列表
            language: 语言代码
            voice_id: 音色ID
            **kwargs: 其他参数
            
        Returns:
            List[ServiceResult]: 结果列表
        """
        tasks = []
        for i, text in enumerate(texts):
            task = self.text_to_speech_bilingual(
                text=text,
                language=language,
                voice_id=voice_id,
                **kwargs
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ServiceResult(
                    success=False,
                    error=str(result),
                    metadata={'text_index': i, 'text': texts[i]}
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_voice_details(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """
        获取音色的详细信息
        
        Args:
            voice_id: 音色ID
            
        Returns:
            Optional[Dict[str, Any]]: 音色详细信息
        """
        voice_model = self.voice_model_manager.get_voice_by_id(voice_id)
        if voice_model:
            return {
                'id': voice_model.id,
                'name': voice_model.name,
                'language': voice_model.language.value,
                'gender': voice_model.gender,
                'style': voice_model.style,
                'provider': voice_model.provider,
                'sample_rate': voice_model.sample_rate,
                'supported_formats': voice_model.supported_formats
            }
        return None
    
    def get_available_providers_for_language(self, language: Optional[LanguageCode] = None) -> List[str]:
        """
        获取指定语言的可用提供商列表
        
        Args:
            language: 语言代码
            
        Returns:
            List[str]: 提供商列表
        """
        target_language = language or self.language_manager.current_language
        voices = self.get_voices_for_language(target_language)
        providers = list(set(voice.provider for voice in voices))
        
        # 按优先级排序
        priority = self.voice_model_manager.get_provider_priority(target_language)
        sorted_providers = []
        
        for p in priority:
            if p in providers:
                sorted_providers.append(p)
        
        # 添加其他未在优先级中的提供商
        for p in providers:
            if p not in sorted_providers:
                sorted_providers.append(p)
        
        return sorted_providers
    
    def _on_language_changed(self, new_language: LanguageCode):
        """
        语言变更回调函数
        
        Args:
            new_language: 新的语言代码
        """
        logger.info(f"语音服务检测到语言变更: {new_language.value}")
        # 可以在这里执行语言变更后的清理工作
    
    def get_debug_info(self) -> Dict[str, Any]:
        """
        获取调试信息
        
        Returns:
            Dict[str, Any]: 调试信息字典
        """
        current_language = self.language_manager.current_language
        available_voices = self.get_voices_for_language(current_language)
        
        return {
            'current_language': current_language.value,
            'available_voices': len(available_voices),
            'total_voice_models': len(self.voice_model_manager.voice_models),
            'available_providers': self.get_available_providers_for_language(current_language),
            'optimal_settings': self.get_optimal_voice_settings(current_language),
            'fallback_voices': self.voice_model_manager.get_fallback_voices(current_language),
            'translation_cache_size': len(self.translation_cache),
            'llm_service_available': self.llm_service is not None
        }
