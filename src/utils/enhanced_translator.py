# -*- coding: utf-8 -*-
"""
增强翻译服务模块
支持多种翻译服务的级联调用：百度翻译 → Google翻译 → LLM翻译
"""

import logging
import requests
import time
from typing import Optional, Dict, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

class EnhancedTranslator:
    """增强翻译器，支持多种翻译服务的级联调用"""
    
    def __init__(self, llm_api=None):
        """
        初始化增强翻译器
        
        Args:
            llm_api: LLM API实例，用于LLM翻译
        """
        self.llm_api = llm_api
        self._init_baidu_translator()
        
    def _init_baidu_translator(self):
        """初始化百度翻译"""
        try:
            from src.utils.baidu_translator import translate_text, is_configured as is_baidu_configured
            self.baidu_translate = translate_text
            self.is_baidu_configured = is_baidu_configured
            logger.info("百度翻译服务初始化成功")
        except ImportError as e:
            logger.warning(f"百度翻译模块导入失败: {e}")
            self.baidu_translate = None
            self.is_baidu_configured = lambda: False
    
    def translate_text(self, text: str, from_lang: str = 'zh', to_lang: str = 'en') -> Optional[str]:
        """
        翻译文本，使用级联翻译策略：百度 → Google → LLM
        
        Args:
            text: 待翻译的文本
            from_lang: 源语言，默认为中文(zh)
            to_lang: 目标语言，默认为英文(en)
            
        Returns:
            翻译结果，失败时返回None
        """
        if not text or not text.strip():
            logger.warning("翻译文本为空")
            return None
        
        text = text.strip()
        logger.info(f"开始翻译文本: {text[:50]}...")
        
        # 1. 尝试百度翻译
        result = self._try_baidu_translate(text, from_lang, to_lang)
        if result:
            logger.info("百度翻译成功")
            return result
        
        # 2. 尝试Google翻译
        result = self._try_google_translate(text, from_lang, to_lang)
        if result:
            logger.info("Google翻译成功")
            return result
        
        # 3. 尝试LLM翻译
        result = self._try_llm_translate(text, from_lang, to_lang)
        if result:
            logger.info("LLM翻译成功")
            return result
        
        logger.warning("所有翻译方法都失败了")
        return None
    
    def _try_baidu_translate(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        """尝试百度翻译"""
        if not self.baidu_translate or not self.is_baidu_configured():
            logger.debug("百度翻译未配置，跳过")
            return None
        
        try:
            logger.debug("尝试百度翻译")
            result = self.baidu_translate(text, from_lang, to_lang)
            if result and result.strip():
                logger.debug(f"百度翻译结果: {result[:50]}...")
                return result.strip()
            else:
                logger.warning("百度翻译返回空结果")
                return None
        except Exception as e:
            logger.warning(f"百度翻译失败: {e}")
            return None
    
    def _try_google_translate(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        """尝试Google翻译（使用免费API）"""
        try:
            logger.debug("尝试Google翻译")
            
            # 使用Google翻译的免费API
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                'client': 'gtx',
                'sl': from_lang,
                'tl': to_lang,
                'dt': 't',
                'q': text
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            # 解析Google翻译结果
            if result and len(result) > 0 and result[0]:
                translated_text = ""
                for item in result[0]:
                    if item and len(item) > 0:
                        translated_text += item[0]
                
                if translated_text.strip():
                    logger.debug(f"Google翻译结果: {translated_text[:50]}...")
                    return translated_text.strip()
            
            logger.warning("Google翻译返回空结果")
            return None
            
        except requests.exceptions.Timeout:
            logger.warning("Google翻译请求超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Google翻译请求异常: {e}")
            return None
        except Exception as e:
            logger.warning(f"Google翻译异常: {e}")
            return None
    
    def _try_llm_translate(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        """尝试LLM翻译"""
        if not self.llm_api:
            logger.debug("LLM API未配置，跳过")
            return None
        
        try:
            logger.debug("尝试LLM翻译")
            
            # 构建翻译提示词
            if from_lang == 'zh' and to_lang == 'en':
                prompt = f"""请将以下中文文本翻译成英文。要求：
1. 翻译要准确、自然、流畅
2. 保持原文的语义和语调
3. 只输出英文翻译结果，不要包含任何中文或其他说明
4. 如果是图像描述，请保持专业的描述性语言

原文：{text}

英文翻译："""
            else:
                prompt = f"Please translate the following text from {from_lang} to {to_lang}. Only output the translation result:\n\n{text}"
            
            result = self.llm_api.rewrite_text(prompt)
            
            if result and result.strip():
                # 清理LLM返回的结果
                cleaned_result = self._clean_llm_result(result.strip())
                if cleaned_result:
                    logger.debug(f"LLM翻译结果: {cleaned_result[:50]}...")
                    return cleaned_result
            
            logger.warning("LLM翻译返回空结果")
            return None
            
        except Exception as e:
            logger.warning(f"LLM翻译失败: {e}")
            return None
    
    def _clean_llm_result(self, result: str) -> str:
        """清理LLM翻译结果"""
        # 移除常见的LLM回复前缀
        prefixes_to_remove = [
            "英文翻译：",
            "翻译结果：",
            "Translation:",
            "English:",
            "Result:",
        ]
        
        for prefix in prefixes_to_remove:
            if result.startswith(prefix):
                result = result[len(prefix):].strip()
        
        # 移除引号
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        if result.startswith("'") and result.endswith("'"):
            result = result[1:-1]
        
        return result.strip()
    
    def is_available(self) -> bool:
        """检查翻译服务是否可用"""
        return (self.is_baidu_configured() or 
                self._test_google_translate() or 
                (self.llm_api is not None))
    
    def _test_google_translate(self) -> bool:
        """测试Google翻译是否可用"""
        try:
            test_result = self._try_google_translate("测试", "zh", "en")
            return test_result is not None
        except:
            return False
    
    def get_available_services(self) -> list:
        """获取可用的翻译服务列表"""
        services = []
        
        if self.is_baidu_configured():
            services.append("百度翻译")
        
        if self._test_google_translate():
            services.append("Google翻译")
        
        if self.llm_api:
            services.append("LLM翻译")
        
        return services


# 全局翻译器实例
_global_translator = None

def get_translator(llm_api=None) -> EnhancedTranslator:
    """获取全局翻译器实例"""
    global _global_translator
    if _global_translator is None:
        _global_translator = EnhancedTranslator(llm_api)
    elif llm_api and not _global_translator.llm_api:
        _global_translator.llm_api = llm_api
    return _global_translator

def translate_text_enhanced(text: str, from_lang: str = 'zh', to_lang: str = 'en', llm_api=None) -> Optional[str]:
    """
    增强翻译函数，支持多种翻译服务
    
    Args:
        text: 待翻译的文本
        from_lang: 源语言，默认为中文(zh)
        to_lang: 目标语言，默认为英文(en)
        llm_api: LLM API实例
        
    Returns:
        翻译结果，失败时返回None
    """
    translator = get_translator(llm_api)
    return translator.translate_text(text, from_lang, to_lang)
