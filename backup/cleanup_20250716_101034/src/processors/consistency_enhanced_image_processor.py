# -*- coding: utf-8 -*-
"""
一致性增强图像处理器
基于现有ImageProcessor扩展，集成角色场景一致性功能
"""

import os
import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

from src.utils.logger import logger
from src.processors.image_processor import ImageProcessor, ImageGenerationConfig, ImageResult, BatchImageResult
from src.processors.text_processor import Shot, StoryboardResult
from src.utils.character_scene_manager import CharacterSceneManager
from src.core.service_manager import ServiceManager, ServiceType

@dataclass
class ConsistencyConfig:
    """一致性配置"""
    enable_character_consistency: bool = True
    enable_scene_consistency: bool = True
    consistency_strength: float = 0.7  # 0-1之间
    auto_extract_new_elements: bool = True
    use_llm_enhancement: bool = True
    preview_mode: bool = False
    character_weight: float = 0.4  # 角色一致性权重
    scene_weight: float = 0.3      # 场景一致性权重
    style_weight: float = 0.3      # 风格权重

@dataclass
class ConsistencyData:
    """一致性数据"""
    characters: Dict[str, Dict[str, Any]] = None
    scenes: Dict[str, Dict[str, Any]] = None
    character_mappings: Dict[int, List[str]] = None  # shot_id -> character_ids
    scene_mappings: Dict[int, str] = None            # shot_id -> scene_id
    
    def __post_init__(self):
        if self.characters is None:
            self.characters = {}
        if self.scenes is None:
            self.scenes = {}
        if self.character_mappings is None:
            self.character_mappings = {}
        if self.scene_mappings is None:
            self.scene_mappings = {}

@dataclass
class EnhancedShot(Shot):
    """增强的分镜数据"""
    enhanced_prompt: str = ""
    consistency_elements: List[str] = None
    character_consistency_prompt: str = ""
    scene_consistency_prompt: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        if self.consistency_elements is None:
            self.consistency_elements = []

class ConsistencyAnalyzer:
    """一致性分析器"""
    
    def __init__(self, service_manager: ServiceManager):
        self.service_manager = service_manager
        
    async def analyze_storyboard_consistency(self, storyboard: StoryboardResult) -> Dict[str, Any]:
        """分析分镜的一致性需求"""
        try:
            logger.info("开始分析分镜一致性...")
            
            # 构建分析提示词
            prompt = self._build_analysis_prompt(storyboard)
            
            # 调用LLM服务
            llm_service = self.service_manager.get_service(ServiceType.LLM)
            if llm_service:
                result = await llm_service.execute(
                    prompt=prompt,
                    max_tokens=2000,
                    temperature=0.3
                )
                
                if result.success:
                    return self._parse_analysis_result(result.data['content'])
            
            logger.warning("LLM服务不可用，使用基础分析")
            return self._basic_analysis(storyboard)
            
        except Exception as e:
            logger.error(f"一致性分析失败: {e}")
            return self._basic_analysis(storyboard)
    
    def _build_analysis_prompt(self, storyboard: StoryboardResult) -> str:
        """构建分析提示词"""
        shots_info = []
        for shot in storyboard.shots:
            shots_info.append(f"分镜{shot.shot_id}: 场景={shot.scene}, 角色={shot.characters}, 动作={shot.action}")
        
        prompt = f"""
请分析以下分镜序列的角色和场景一致性需求：

分镜信息：
{"".join(shots_info)}

请分析：
1. 识别所有出现的角色，分析每个角色在不同分镜中的一致性要求
2. 识别所有场景，分析场景的环境特征和氛围
3. 分析角色在不同场景中的表现和状态变化
4. 为每个角色和场景生成详细的一致性描述

请以JSON格式返回分析结果：
{{
  "characters": {{
    "角色名": {{
      "description": "角色基本描述",
      "appearance": "外貌特征",
      "clothing": "服装描述",
      "personality_traits": "性格特征",
      "consistency_prompt": "一致性提示词"
    }}
  }},
  "scenes": {{
    "场景名": {{
      "description": "场景描述",
      "environment": "环境特征",
      "lighting": "光线描述",
      "atmosphere": "氛围描述",
      "consistency_prompt": "一致性提示词"
    }}
  }},
  "relationships": {{
    "character_scene_interactions": "角色场景互动分析",
    "consistency_strategy": "一致性策略建议"
  }}
}}
"""
        return prompt
    
    def _parse_analysis_result(self, content: str) -> Dict[str, Any]:
        """解析LLM分析结果"""
        try:
            # 尝试提取JSON部分
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"解析LLM结果失败: {e}")
        
        return {"characters": {}, "scenes": {}, "relationships": {}}
    
    def _basic_analysis(self, storyboard: StoryboardResult) -> Dict[str, Any]:
        """基础分析（备用方案）"""
        characters = {}
        scenes = {}
        
        # 提取角色信息
        for char in storyboard.characters:
            characters[char] = {
                "description": f"角色{char}",
                "appearance": "待定义",
                "clothing": "待定义",
                "personality_traits": "待定义",
                "consistency_prompt": f"{char}, 保持角色一致性"
            }
        
        # 提取场景信息
        for scene in storyboard.scenes:
            scenes[scene] = {
                "description": f"场景{scene}",
                "environment": "待定义",
                "lighting": "自然光",
                "atmosphere": "平静",
                "consistency_prompt": f"{scene}, 保持场景一致性"
            }
        
        return {
            "characters": characters,
            "scenes": scenes,
            "relationships": {
                "character_scene_interactions": "基础分析",
                "consistency_strategy": "使用基础一致性策略"
            }
        }

class PromptEnhancer:
    """提示词增强器"""
    
    def __init__(self, consistency_config: ConsistencyConfig):
        self.config = consistency_config
    
    def enhance_shot_prompt(self, shot: Shot, consistency_data: ConsistencyData, 
                          analysis_result: Dict[str, Any]) -> EnhancedShot:
        """增强单个分镜的提示词"""
        enhanced_shot = EnhancedShot(**asdict(shot))
        
        # 构建一致性元素
        consistency_elements = []
        
        # 添加角色一致性
        if self.config.enable_character_consistency:
            char_prompt = self._build_character_consistency_prompt(
                shot, consistency_data, analysis_result
            )
            if char_prompt:
                enhanced_shot.character_consistency_prompt = char_prompt
                consistency_elements.append(char_prompt)
        
        # 添加场景一致性
        if self.config.enable_scene_consistency:
            scene_prompt = self._build_scene_consistency_prompt(
                shot, consistency_data, analysis_result
            )
            if scene_prompt:
                enhanced_shot.scene_consistency_prompt = scene_prompt
                consistency_elements.append(scene_prompt)
        
        # 合并提示词
        enhanced_shot.enhanced_prompt = self._merge_prompts(
            shot.image_prompt, consistency_elements
        )
        enhanced_shot.consistency_elements = consistency_elements
        
        return enhanced_shot
    
    def _build_character_consistency_prompt(self, shot: Shot, consistency_data: ConsistencyData,
                                          analysis_result: Dict[str, Any]) -> str:
        """构建角色一致性提示词"""
        char_prompts = []
        
        for char_name in shot.characters:
            # 从分析结果获取角色信息
            if char_name in analysis_result.get("characters", {}):
                char_info = analysis_result["characters"][char_name]
                prompt_parts = []
                
                if char_info.get("appearance"):
                    prompt_parts.append(char_info["appearance"])
                if char_info.get("clothing"):
                    prompt_parts.append(char_info["clothing"])
                
                if prompt_parts:
                    char_prompts.append(f"{char_name}: {', '.join(prompt_parts)}")
            else:
                # 使用基础描述
                char_prompts.append(f"{char_name}, 保持角色一致性")
        
        return "; ".join(char_prompts)
    
    def _build_scene_consistency_prompt(self, shot: Shot, consistency_data: ConsistencyData,
                                      analysis_result: Dict[str, Any]) -> str:
        """构建场景一致性提示词"""
        scene_name = shot.scene
        
        # 从分析结果获取场景信息
        if scene_name in analysis_result.get("scenes", {}):
            scene_info = analysis_result["scenes"][scene_name]
            prompt_parts = []
            
            if scene_info.get("environment"):
                prompt_parts.append(scene_info["environment"])
            if scene_info.get("lighting"):
                prompt_parts.append(scene_info["lighting"])
            if scene_info.get("atmosphere"):
                prompt_parts.append(scene_info["atmosphere"])
            
            if prompt_parts:
                return f"{scene_name}: {', '.join(prompt_parts)}"
        
        return f"{scene_name}, 保持场景一致性"
    
    def _merge_prompts(self, base_prompt: str, consistency_elements: List[str]) -> str:
        """合并基础提示词和一致性元素"""
        if not consistency_elements:
            return base_prompt
        
        # 应用一致性强度
        if self.config.consistency_strength < 1.0:
            # 降低一致性元素的权重
            consistency_part = ", ".join(consistency_elements)
            return f"{base_prompt}, ({consistency_part}:{self.config.consistency_strength})"
        else:
            # 完全应用一致性
            consistency_part = ", ".join(consistency_elements)
            return f"{base_prompt}, {consistency_part}"

class ConsistencyEnhancedImageProcessor(ImageProcessor):
    """一致性增强图像处理器"""
    
    def __init__(self, service_manager: ServiceManager, character_scene_manager: CharacterSceneManager,
                 output_dir: str = "output/images"):
        super().__init__(service_manager, output_dir)
        self.cs_manager = character_scene_manager
        self.consistency_analyzer = ConsistencyAnalyzer(service_manager)
        self.consistency_cache = {}
        
    async def generate_consistent_storyboard_images(self, storyboard: StoryboardResult,
                                                   config: ImageGenerationConfig = None,
                                                   consistency_config: ConsistencyConfig = None,
                                                   progress_callback: Callable = None) -> BatchImageResult:
        """生成具有一致性的分镜图像"""
        try:
            if config is None:
                config = self.default_config
            if consistency_config is None:
                consistency_config = ConsistencyConfig()
            
            logger.info(f"开始生成一致性增强的分镜图像，共 {len(storyboard.shots)} 个镜头")
            
            # 第一阶段：准备一致性数据
            if progress_callback:
                progress_callback(0.1, "准备一致性数据...")
            
            consistency_data = await self._prepare_consistency_data(storyboard, consistency_config)
            
            # 第二阶段：分析一致性需求
            if progress_callback:
                progress_callback(0.2, "分析一致性需求...")
            
            analysis_result = await self.consistency_analyzer.analyze_storyboard_consistency(storyboard)
            
            # 第三阶段：增强分镜提示词
            if progress_callback:
                progress_callback(0.3, "增强分镜提示词...")
            
            enhanced_shots = self._enhance_shots_with_consistency(
                storyboard.shots, consistency_data, analysis_result, consistency_config
            )
            
            # 第四阶段：生成图像
            if progress_callback:
                progress_callback(0.4, "开始生成图像...")
            
            # 创建增强的分镜结果
            enhanced_storyboard = StoryboardResult(
                shots=enhanced_shots,
                total_duration=storyboard.total_duration,
                characters=storyboard.characters,
                scenes=storyboard.scenes,
                style=storyboard.style,
                metadata=storyboard.metadata
            )
            
            # 调用原有的图像生成逻辑
            result = await self.generate_storyboard_images(
                enhanced_storyboard, config, 
                lambda p, msg: progress_callback(0.4 + p * 0.6, msg) if progress_callback else None
            )
            
            # 保存一致性信息
            await self._save_consistency_metadata(result, consistency_data, analysis_result)
            
            logger.info("一致性增强图像生成完成")
            return result
            
        except Exception as e:
            logger.error(f"一致性增强图像生成失败: {e}")
            raise
    
    async def _prepare_consistency_data(self, storyboard: StoryboardResult, 
                                      consistency_config: ConsistencyConfig) -> ConsistencyData:
        """准备一致性数据"""
        consistency_data = ConsistencyData()
        
        try:
            # 自动提取新的角色和场景信息
            if consistency_config.auto_extract_new_elements:
                # 构建完整文本用于提取
                full_text = self._build_full_text_from_storyboard(storyboard)
                
                # 提取并保存角色场景信息
                extract_result = self.cs_manager.auto_extract_and_save(full_text)
                logger.info(f"自动提取结果: {extract_result['message']}")
            
            # 获取现有的角色和场景数据
            all_characters = self.cs_manager.get_all_characters()
            all_scenes = self.cs_manager.get_all_scenes()
            
            # 匹配分镜中的角色和场景
            for shot in storyboard.shots:
                # 匹配角色
                matched_chars = []
                for char_name in shot.characters:
                    for char_id, char_data in all_characters.items():
                        if char_data.get('name', '').lower() == char_name.lower():
                            matched_chars.append(char_id)
                            consistency_data.characters[char_id] = char_data
                            break
                
                consistency_data.character_mappings[shot.shot_id] = matched_chars
                
                # 匹配场景
                scene_name = shot.scene
                for scene_id, scene_data in all_scenes.items():
                    if scene_data.get('name', '').lower() == scene_name.lower():
                        consistency_data.scene_mappings[shot.shot_id] = scene_id
                        consistency_data.scenes[scene_id] = scene_data
                        break
            
            logger.info(f"匹配到 {len(consistency_data.characters)} 个角色，{len(consistency_data.scenes)} 个场景")
            
        except Exception as e:
            logger.error(f"准备一致性数据失败: {e}")
        
        return consistency_data
    
    def _build_full_text_from_storyboard(self, storyboard: StoryboardResult) -> str:
        """从分镜构建完整文本"""
        text_parts = []
        for shot in storyboard.shots:
            text_parts.append(f"场景：{shot.scene}")
            text_parts.append(f"角色：{', '.join(shot.characters)}")
            text_parts.append(f"动作：{shot.action}")
            if shot.dialogue:
                text_parts.append(f"对话：{shot.dialogue}")
            text_parts.append("---")
        
        return "\n".join(text_parts)
    
    def _enhance_shots_with_consistency(self, shots: List[Shot], consistency_data: ConsistencyData,
                                      analysis_result: Dict[str, Any], 
                                      consistency_config: ConsistencyConfig) -> List[EnhancedShot]:
        """使用一致性数据增强分镜"""
        prompt_enhancer = PromptEnhancer(consistency_config)
        enhanced_shots = []
        
        for shot in shots:
            enhanced_shot = prompt_enhancer.enhance_shot_prompt(
                shot, consistency_data, analysis_result
            )
            enhanced_shots.append(enhanced_shot)
        
        return enhanced_shots
    
    async def _save_consistency_metadata(self, result: BatchImageResult, 
                                       consistency_data: ConsistencyData,
                                       analysis_result: Dict[str, Any]):
        """保存一致性元数据"""
        try:
            metadata_file = Path(result.output_directory) / "consistency_metadata.json"
            
            metadata = {
                "consistency_data": {
                    "characters": consistency_data.characters,
                    "scenes": consistency_data.scenes,
                    "character_mappings": consistency_data.character_mappings,
                    "scene_mappings": consistency_data.scene_mappings
                },
                "analysis_result": analysis_result,
                "generation_info": {
                    "total_images": len(result.results),
                    "success_count": result.success_count,
                    "failed_count": result.failed_count,
                    "total_time": result.total_time
                }
            }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"一致性元数据已保存到: {metadata_file}")
            
        except Exception as e:
            logger.error(f"保存一致性元数据失败: {e}")
    
    def get_consistency_preview(self, storyboard: StoryboardResult, 
                              consistency_config: ConsistencyConfig = None) -> Dict[str, Any]:
        """获取一致性预览信息（同步方法）"""
        if consistency_config is None:
            consistency_config = ConsistencyConfig()
        
        try:
            # 简化的预览逻辑
            preview_data = {
                "shots_preview": [],
                "characters_found": list(storyboard.characters),
                "scenes_found": list(storyboard.scenes),
                "consistency_config": asdict(consistency_config)
            }
            
            # 为每个分镜生成预览信息
            for shot in storyboard.shots:
                shot_preview = {
                    "shot_id": shot.shot_id,
                    "original_prompt": shot.image_prompt,
                    "characters": shot.characters,
                    "scene": shot.scene,
                    "estimated_enhanced_prompt": f"{shot.image_prompt}, [一致性增强]"  # 简化预览
                }
                preview_data["shots_preview"].append(shot_preview)
            
            return preview_data
            
        except Exception as e:
            logger.error(f"生成一致性预览失败: {e}")
            return {"error": str(e)}