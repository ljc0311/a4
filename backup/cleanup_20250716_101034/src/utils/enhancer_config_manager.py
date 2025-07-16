#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场景描述增强器配置管理器
负责管理场景描述增强器的各种配置参数
"""

import json
import os
from typing import Dict, Any, Optional
from src.utils.logger import logger


class EnhancerConfigManager:
    """场景描述增强器配置管理器"""
    
    def __init__(self, config_file: str = None):
        """初始化配置管理器"""
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'enhancer_config.json')
        
        self.config_file = config_file
        self.config = self._load_default_config()
        self._load_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            # 基础配置
            "enable_technical_details": True,
            "enable_consistency_injection": True,
            "enhancement_level": "medium",
            "fusion_strategy": "intelligent",
            
            # 质量控制
            "quality_threshold": 0.3,
            "max_enhancement_length": 500,
            "min_enhancement_length": 50,
            
            # 性能配置
            "cache_enabled": True,
            "cache_size": 1000,
            "batch_processing": False,
            "max_batch_size": 10,
            
            # 融合策略权重
            "strategy_weights": {
                "natural": 1.0,
                "structured": 0.8,
                "minimal": 0.6,
                "intelligent": 1.2
            },
            
            # 自定义规则
            "custom_rules": {
                "technical_keywords": [
                    "镜头语言", "构图", "光影", "色彩", "景深",
                    "角度", "运动", "节奏", "氛围", "质感"
                ],
                "consistency_keywords": [
                    "角色外貌", "服装", "道具", "场景", "风格",
                    "色调", "时间", "天气", "情绪", "主题"
                ],
                "enhancement_templates": {
                    "technical": "[技术细节] {content}",
                    "consistency": "[一致性要求] {content}",
                    "atmosphere": "[氛围营造] {content}"
                }
            },
            
            # 调试配置
            "debug_mode": False,
            "log_level": "INFO",
            "performance_monitoring": True
        }
    
    def _load_config(self):
        """从文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
                    logger.info(f"已加载增强器配置: {self.config_file}")
            else:
                # 创建配置目录
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                self.save_config()
                logger.info(f"已创建默认增强器配置: {self.config_file}")
        except Exception as e:
            logger.error(f"加载增强器配置失败: {e}")
    
    def save_config(self):
        """保存配置到文件"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"增强器配置已保存: {self.config_file}")
        except Exception as e:
            logger.error(f"保存增强器配置失败: {e}")
            raise
    
    def get_config(self, key: str = None, default: Any = None) -> Any:
        """获取配置值"""
        if key is None:
            return self.config.copy()
        return self.config.get(key, default)
    
    def set_config(self, key: str, value: Any):
        """设置配置值"""
        self.config[key] = value
        logger.debug(f"配置已更新: {key} = {value}")
    
    def update_config(self, updates: Dict[str, Any]):
        """批量更新配置"""
        self.config.update(updates)
        logger.info(f"批量更新配置: {list(updates.keys())}")
    
    def reset_to_default(self):
        """重置为默认配置"""
        self.config = self._load_default_config()
        logger.info("配置已重置为默认值")
    
    def validate_config(self) -> bool:
        """验证配置的有效性"""
        try:
            # 检查必需的配置项
            required_keys = [
                "enable_technical_details", "enable_consistency_injection",
                "enhancement_level", "fusion_strategy", "quality_threshold"
            ]
            
            for key in required_keys:
                if key not in self.config:
                    logger.error(f"缺少必需的配置项: {key}")
                    return False
            
            # 检查数值范围
            if not 0 <= self.config.get("quality_threshold", 0) <= 1:
                logger.error("quality_threshold 必须在 0-1 之间")
                return False
            
            if self.config.get("max_enhancement_length", 0) <= 0:
                logger.error("max_enhancement_length 必须大于 0")
                return False
            
            # 检查枚举值
            valid_levels = ["low", "medium", "high"]
            if self.config.get("enhancement_level") not in valid_levels:
                logger.error(f"enhancement_level 必须是 {valid_levels} 之一")
                return False
            
            valid_strategies = ["natural", "structured", "minimal", "intelligent"]
            if self.config.get("fusion_strategy") not in valid_strategies:
                logger.error(f"fusion_strategy 必须是 {valid_strategies} 之一")
                return False
            
            logger.info("配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False
    
    def get_performance_config(self) -> Dict[str, Any]:
        """获取性能相关配置"""
        return {
            "cache_enabled": self.config.get("cache_enabled", True),
            "cache_size": self.config.get("cache_size", 1000),
            "batch_processing": self.config.get("batch_processing", False),
            "max_batch_size": self.config.get("max_batch_size", 10),
            "performance_monitoring": self.config.get("performance_monitoring", True)
        }
    
    def get_quality_config(self) -> Dict[str, Any]:
        """获取质量控制配置"""
        return {
            "quality_threshold": self.config.get("quality_threshold", 0.3),
            "max_enhancement_length": self.config.get("max_enhancement_length", 500),
            "min_enhancement_length": self.config.get("min_enhancement_length", 50)
        }
    
    def get_fusion_config(self) -> Dict[str, Any]:
        """获取融合策略配置"""
        return {
            "fusion_strategy": self.config.get("fusion_strategy", "intelligent"),
            "strategy_weights": self.config.get("strategy_weights", {})
        }
    
    def get_custom_rules(self) -> Dict[str, Any]:
        """获取自定义规则"""
        return self.config.get("custom_rules", {})
    
    def export_config(self, export_path: str):
        """导出配置到指定路径"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"配置已导出到: {export_path}")
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            raise
    
    def import_config(self, import_path: str):
        """从指定路径导入配置"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 验证导入的配置
            temp_config = self.config.copy()
            self.config.update(imported_config)
            
            if self.validate_config():
                logger.info(f"配置已从 {import_path} 导入")
            else:
                self.config = temp_config
                raise ValueError("导入的配置无效")
                
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            raise