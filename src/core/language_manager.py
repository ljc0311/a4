#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语言管理器
统一管理应用程序的语言设置、切换和配置
"""

import json
import os
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path

from src.models.language_models import (
    LanguageCode, LanguageConfig, ProjectLanguageSettings, 
    VoiceModel, DEFAULT_LANGUAGE_CONFIGS
)
from src.core.language_detector import LanguageDetector
from src.utils.logger import logger
from src.utils.config_manager import ConfigManager


class LanguageManager:
    """语言管理器类"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.language_detector = LanguageDetector()
        
        # 当前语言设置
        self._current_language = LanguageCode.CHINESE
        self._language_configs = DEFAULT_LANGUAGE_CONFIGS.copy()
        
        # 语言变更回调函数列表
        self._language_change_callbacks: List[Callable[[LanguageCode], None]] = []
        
        # 加载保存的语言设置
        self._load_language_settings()
        
        logger.info(f"语言管理器初始化完成，当前语言: {self._current_language.value}")
    
    @property
    def current_language(self) -> LanguageCode:
        """获取当前语言"""
        return self._current_language
    
    @property
    def supported_languages(self) -> List[LanguageCode]:
        """获取支持的语言列表"""
        return list(self._language_configs.keys())
    
    def set_language(self, language: LanguageCode, save_setting: bool = True) -> bool:
        """
        设置当前语言
        
        Args:
            language: 要设置的语言代码
            save_setting: 是否保存设置到配置文件
            
        Returns:
            bool: 设置是否成功
        """
        try:
            if not isinstance(language, LanguageCode) or not self.is_language_supported(language):
                logger.error(f"不支持的语言: {language}")
                return False
            
            old_language = self._current_language
            self._current_language = language
            
            logger.info(f"语言已切换: {old_language.value} -> {language.value}")
            
            # 保存设置
            if save_setting:
                self._save_language_settings()
            
            # 触发语言变更回调
            self._trigger_language_change_callbacks(language)
            
            return True
            
        except Exception as e:
            logger.error(f"设置语言失败: {e}")
            return False
    
    def get_language_config(self, language: Optional[LanguageCode] = None) -> LanguageConfig:
        """
        获取语言配置
        
        Args:
            language: 语言代码，如果为None则返回当前语言的配置
            
        Returns:
            LanguageConfig: 语言配置对象
        """
        target_language = language or self._current_language
        return self._language_configs.get(target_language, self._language_configs[LanguageCode.CHINESE])
    
    def is_language_supported(self, language: LanguageCode) -> bool:
        """
        检查是否支持指定语言
        
        Args:
            language: 要检查的语言代码
            
        Returns:
            bool: 是否支持
        """
        return language in self._language_configs
    
    def detect_content_language(self, content: str) -> LanguageCode:
        """
        检测内容的语言
        
        Args:
            content: 要检测的内容
            
        Returns:
            LanguageCode: 检测到的语言代码
        """
        return self.language_detector.detect_language(content)
    
    def validate_content_language(self, content: str, expected_language: Optional[LanguageCode] = None) -> Dict[str, Any]:
        """
        验证内容语言的一致性
        
        Args:
            content: 要验证的内容
            expected_language: 期望的语言，如果为None则使用当前语言
            
        Returns:
            Dict: 验证结果
        """
        target_language = expected_language or self._current_language
        is_consistent, issues = self.language_detector.validate_language_consistency(content, target_language)
        suggestions = self.language_detector.suggest_language_correction(content, target_language)
        
        return {
            'is_consistent': is_consistent,
            'detected_language': self.language_detector.detect_language(content).value,
            'expected_language': target_language.value,
            'issues': issues,
            'suggestions': suggestions,
            'statistics': self.language_detector.get_language_statistics(content)
        }
    
    def get_language_display_name(self, language: Optional[LanguageCode] = None) -> str:
        """
        获取语言的显示名称
        
        Args:
            language: 语言代码，如果为None则返回当前语言的显示名称
            
        Returns:
            str: 语言显示名称
        """
        config = self.get_language_config(language)
        return config.display_name
    
    def get_available_voices(self, language: Optional[LanguageCode] = None) -> List[str]:
        """
        获取指定语言的可用音色列表
        
        Args:
            language: 语言代码，如果为None则返回当前语言的音色
            
        Returns:
            List[str]: 音色ID列表
        """
        config = self.get_language_config(language)
        return config.voice_settings.supported_voices
    
    def get_default_voice(self, language: Optional[LanguageCode] = None) -> Dict[str, str]:
        """
        获取指定语言的默认音色
        
        Args:
            language: 语言代码，如果为None则返回当前语言的默认音色
            
        Returns:
            Dict: 包含音色ID和名称的字典
        """
        config = self.get_language_config(language)
        return {
            'id': config.voice_settings.default_voice_id,
            'name': config.voice_settings.default_voice_name
        }
    
    def get_subtitle_settings(self, language: Optional[LanguageCode] = None) -> Dict[str, Any]:
        """
        获取指定语言的字幕设置
        
        Args:
            language: 语言代码，如果为None则返回当前语言的字幕设置
            
        Returns:
            Dict: 字幕设置字典
        """
        config = self.get_language_config(language)
        return config.subtitle_settings.to_dict()
    
    def update_language_config(self, language: LanguageCode, config_updates: Dict[str, Any]) -> bool:
        """
        更新语言配置
        
        Args:
            language: 要更新的语言代码
            config_updates: 配置更新内容
            
        Returns:
            bool: 更新是否成功
        """
        try:
            if not self.is_language_supported(language):
                logger.error(f"不支持的语言: {language.value}")
                return False
            
            config = self._language_configs[language]
            
            # 更新字幕设置
            if 'subtitle_settings' in config_updates:
                subtitle_updates = config_updates['subtitle_settings']
                for key, value in subtitle_updates.items():
                    if hasattr(config.subtitle_settings, key):
                        setattr(config.subtitle_settings, key, value)
            
            # 更新语音设置
            if 'voice_settings' in config_updates:
                voice_updates = config_updates['voice_settings']
                for key, value in voice_updates.items():
                    if hasattr(config.voice_settings, key):
                        setattr(config.voice_settings, key, value)
            
            # 保存更新
            self._save_language_settings()
            
            logger.info(f"语言配置已更新: {language.value}")
            return True
            
        except Exception as e:
            logger.error(f"更新语言配置失败: {e}")
            return False
    
    def add_language_change_callback(self, callback: Callable[[LanguageCode], None]):
        """
        添加语言变更回调函数
        
        Args:
            callback: 回调函数，接收新语言代码作为参数
        """
        if callback not in self._language_change_callbacks:
            self._language_change_callbacks.append(callback)
            logger.debug(f"已添加语言变更回调函数: {callback.__name__}")
    
    def remove_language_change_callback(self, callback: Callable[[LanguageCode], None]):
        """
        移除语言变更回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self._language_change_callbacks:
            self._language_change_callbacks.remove(callback)
            logger.debug(f"已移除语言变更回调函数: {callback.__name__}")
    
    def create_project_language_settings(self, language: Optional[LanguageCode] = None) -> ProjectLanguageSettings:
        """
        创建项目语言设置
        
        Args:
            language: 项目语言，如果为None则使用当前语言
            
        Returns:
            ProjectLanguageSettings: 项目语言设置对象
        """
        target_language = language or self._current_language
        return ProjectLanguageSettings(
            primary_language=target_language,
            content_language=target_language,
            voice_language=target_language,
            subtitle_language=target_language
        )
    
    def get_language_specific_fonts(self, language: Optional[LanguageCode] = None) -> List[str]:
        """
        获取语言特定的字体列表
        
        Args:
            language: 语言代码，如果为None则返回当前语言的字体
            
        Returns:
            List[str]: 字体名称列表
        """
        target_language = language or self._current_language
        
        if target_language == LanguageCode.CHINESE:
            return [
                "Microsoft YaHei",
                "SimHei",
                "SimSun",
                "KaiTi",
                "FangSong",
                "Source Han Sans CN",
                "Noto Sans CJK SC"
            ]
        elif target_language == LanguageCode.ENGLISH:
            return [
                "Arial",
                "Helvetica",
                "Times New Roman",
                "Calibri",
                "Verdana",
                "Georgia",
                "Trebuchet MS"
            ]
        else:
            return ["Arial", "Microsoft YaHei"]
    
    def _trigger_language_change_callbacks(self, new_language: LanguageCode):
        """触发语言变更回调函数"""
        for callback in self._language_change_callbacks:
            try:
                callback(new_language)
            except Exception as e:
                logger.error(f"语言变更回调函数执行失败: {callback.__name__}, 错误: {e}")
    
    def _load_language_settings(self):
        """加载保存的语言设置"""
        try:
            # 从配置管理器加载当前语言设置
            saved_language = self.config_manager.get_setting('current_language', 'zh-CN')
            if isinstance(saved_language, str):
                try:
                    self._current_language = LanguageCode(saved_language)
                except ValueError:
                    logger.warning(f"无效的保存语言设置: {saved_language}，使用默认中文")
                    self._current_language = LanguageCode.CHINESE
            
            # 加载自定义语言配置
            custom_configs = self.config_manager.get_setting('language_configs', {})
            if isinstance(custom_configs, dict):
                for lang_code, config_data in custom_configs.items():
                    try:
                        language = LanguageCode(lang_code)
                        if language in self._language_configs:
                            # 更新现有配置
                            config = LanguageConfig.from_dict(config_data)
                            self._language_configs[language] = config
                    except (ValueError, KeyError) as e:
                        logger.warning(f"加载自定义语言配置失败: {lang_code}, 错误: {e}")
            
            logger.info(f"语言设置加载完成，当前语言: {self._current_language.value}")
            
        except Exception as e:
            logger.error(f"加载语言设置失败: {e}")
            self._current_language = LanguageCode.CHINESE
    
    def _save_language_settings(self):
        """保存语言设置"""
        try:
            # 保存当前语言
            self.config_manager.set_setting('current_language', self._current_language.value)
            
            # 保存自定义语言配置
            custom_configs = {}
            for language, config in self._language_configs.items():
                custom_configs[language.value] = config.to_dict()
            
            self.config_manager.set_setting('language_configs', custom_configs)
            
            logger.debug("语言设置已保存")
            
        except Exception as e:
            logger.error(f"保存语言设置失败: {e}")
    
    def get_debug_info(self) -> Dict[str, Any]:
        """获取调试信息"""
        return {
            'current_language': self._current_language.value,
            'supported_languages': [lang.value for lang in self.supported_languages],
            'callback_count': len(self._language_change_callbacks),
            'language_configs': {
                lang.value: config.to_dict() 
                for lang, config in self._language_configs.items()
            }
        }
