#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本处理器
基于新的服务架构重构的文本解析和分镜生成功能
"""

import json
import re
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

from src.utils.logger import logger
from src.utils.character_detection_config import CharacterDetectionConfig
from src.core.service_manager import ServiceManager, ServiceType
from src.core.service_base import ServiceResult

@dataclass
class Shot:
    """分镜数据类"""
    shot_id: int
    scene: str
    characters: List[str]
    action: str
    dialogue: str
    image_prompt: str
    duration: float = 3.0
    camera_angle: str = "中景"
    lighting: str = "自然光"
    mood: str = "平静"
    
@dataclass
class StoryboardResult:
    """分镜结果数据类"""
    shots: List[Shot]
    total_duration: float
    characters: List[str]
    scenes: List[str]
    style: str
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class TextProcessor:
    """文本处理器"""
    
    def __init__(self, service_manager: ServiceManager):
        self.service_manager = service_manager
        
        # 风格模板
        self.style_templates = {
            '电影风格': '{scene}，{characters}，电影感，戏剧性光影，超写实，4K，胶片颗粒，景深',
            '动漫风格': '{scene}，{characters}，动漫风，鲜艳色彩，干净线条，赛璐璐渲染，日本动画',
            '吉卜力风格': '{scene}，{characters}，吉卜力风，柔和色彩，奇幻，梦幻，丰富背景',
            '赛博朋克风格': '{scene}，{characters}，赛博朋克，霓虹灯，未来都市，雨夜，暗色氛围',
            '水彩插画风格': '{scene}，{characters}，水彩画风，柔和笔触，粉彩色，插画，温柔',
            '像素风格': '{scene}，{characters}，像素风，8位，复古，低分辨率，游戏风',
            '写实摄影风格': '{scene}，{characters}，真实光线，高细节，写实摄影，4K'
        }
        
        # 场景和角色关键词
        self.scene_keywords = [
            '市场', '夜晚', '白天', '街道', '网吧', '路边', '屋内', '房间', '大厅', '门口',
            '广场', '教室', '车站', '公园', '超市', '餐厅', '楼道', '走廊', '桥', '河边',
            '山', '树林', '田野', '村庄', '城市', '乡村', '办公室', '工地', '医院', '商场'
        ]
        
        self.character_keywords = [
            '主角', '保安', '警察', '老师', '学生', '父亲', '母亲', '小孩', '老人',
            '服务员', '售货员', '司机', '乘客', '医生', '护士', '病人', '顾客', '老板',
            '同事', '朋友', '陌生人', '路人', '小偷', '演员', '主持人', '观众', '记者'
        ]
        
        logger.info("文本处理器初始化完成")
    
    async def parse_text(self, text: str, style: Optional[str] = None,
                        provider: Optional[str] = None, progress_callback: Optional[Callable] = None) -> StoryboardResult:
        """解析文本生成分镜"""
        try:
            # 如果没有指定风格，从配置中获取默认风格
            if style is None:
                from src.utils.config_manager import ConfigManager
                config_manager = ConfigManager()
                style_setting = config_manager.get_setting("default_style", "电影风格")
                style = str(style_setting) if style_setting else "电影风格"
            
            logger.info(f"开始解析文本，风格: {style}")
            
            # 检查是否已经是分镜格式
            if self._is_storyboard_format(text):
                logger.info("检测到分镜格式，直接解析")
                return await self._parse_existing_storyboard(text, style)
            
            # 使用LLM生成分镜
            if progress_callback:
                progress_callback(0.1, "正在生成分镜...")
            
            result = await self.service_manager.generate_storyboard(
                text=text,
                style=style,
                provider=provider
            )
            
            if not result.success:
                raise Exception(f"分镜生成失败: {result.error}")
            
            if progress_callback:
                progress_callback(0.6, "正在解析分镜数据...")
            
            # 解析LLM返回的分镜数据
            storyboard = await self._parse_llm_response(result.data['content'], style)
            
            if progress_callback:
                progress_callback(0.8, "正在优化图像提示词...")
            
            # 优化图像提示词
            await self._optimize_image_prompts(storyboard, style, provider)
            
            if progress_callback:
                progress_callback(1.0, "分镜解析完成")
            
            logger.info(f"分镜解析完成，共生成 {len(storyboard.shots)} 个镜头")
            return storyboard
            
        except Exception as e:
            logger.error(f"文本解析失败: {e}")
            raise
    
    def _is_storyboard_format(self, text: str) -> bool:
        """检查文本是否已经是分镜格式"""
        # 检查是否包含分镜表格的特征
        indicators = [
            '镜头', '场景', '角色', '动作', '对话', '画面',
            'shot', 'scene', 'character', 'action', 'dialogue'
        ]
        
        # 检查JSON格式
        try:
            data = json.loads(text)
            if isinstance(data, dict) and 'shots' in data:
                return True
        except:
            pass
        
        # 检查表格格式
        lines = text.strip().split('\n')
        if len(lines) > 3:
            header_indicators = sum(1 for indicator in indicators if indicator in lines[0].lower())
            if header_indicators >= 3:
                return True
        
        return False
    
    async def _parse_existing_storyboard(self, text: str, style: str) -> StoryboardResult:
        """解析已有的分镜格式"""
        try:
            # 尝试解析JSON格式
            data = json.loads(text)
            if isinstance(data, dict) and 'shots' in data:
                return self._parse_json_storyboard(data, style)
        except:
            pass
        
        # 解析表格格式
        return self._parse_table_storyboard(text, style)
    
    def _parse_json_storyboard(self, data: Dict, style: str) -> StoryboardResult:
        """解析JSON格式的分镜"""
        shots = []
        characters = set()
        scenes = set()
        
        for i, shot_data in enumerate(data['shots']):
            shot_characters = shot_data.get('characters', [])
            if isinstance(shot_characters, str):
                shot_characters = [shot_characters]
            
            shot = Shot(
                shot_id=i + 1,
                scene=shot_data.get('scene', ''),
                characters=shot_characters,
                action=shot_data.get('action', ''),
                dialogue=shot_data.get('dialogue', ''),
                image_prompt=shot_data.get('image_prompt', ''),
                duration=shot_data.get('duration', 3.0),
                camera_angle=shot_data.get('camera_angle', '中景'),
                lighting=shot_data.get('lighting', '自然光'),
                mood=shot_data.get('mood', '平静')
            )
            
            shots.append(shot)
            characters.update(shot_characters)
            scenes.add(shot.scene)
        
        return StoryboardResult(
            shots=shots,
            total_duration=sum(shot.duration for shot in shots),
            characters=list(characters),
            scenes=list(scenes),
            style=style
        )
    
    def _parse_table_storyboard(self, text: str, style: str) -> StoryboardResult:
        """解析表格格式的分镜"""
        lines = text.strip().split('\n')
        shots = []
        characters = set()
        scenes = set()
        
        # 跳过表头
        data_lines = [line for line in lines[1:] if line.strip() and not line.startswith('|--')]
        
        for i, line in enumerate(data_lines):
            if '|' in line:
                parts = [part.strip() for part in line.split('|')[1:-1]]  # 去掉首尾空元素
                
                if len(parts) >= 4:
                    scene = parts[1] if len(parts) > 1 else ''
                    character_list = [parts[2]] if len(parts) > 2 and parts[2] else []
                    action = parts[3] if len(parts) > 3 else ''
                    dialogue = parts[4] if len(parts) > 4 else ''
                    
                    shot = Shot(
                        shot_id=i + 1,
                        scene=scene,
                        characters=character_list,
                        action=action,
                        dialogue=dialogue,
                        image_prompt=self._generate_image_prompt(scene, character_list, action, style)
                    )
                    
                    shots.append(shot)
                    characters.update(character_list)
                    scenes.add(scene)
        
        return StoryboardResult(
            shots=shots,
            total_duration=sum(shot.duration for shot in shots),
            characters=list(characters),
            scenes=list(scenes),
            style=style
        )
    
    async def _parse_llm_response(self, response: str, style: str) -> StoryboardResult:
        """解析LLM返回的分镜数据"""
        try:
            # 尝试提取JSON
            json_match = re.search(r'```json\s*({.*?})\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return self._parse_json_storyboard(data, style)
            
            # 尝试直接解析JSON
            try:
                data = json.loads(response)
                return self._parse_json_storyboard(data, style)
            except:
                pass
            
            # 解析文本格式
            return await self._parse_text_response(response, style)
            
        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}")
            raise
    
    async def _parse_text_response(self, response: str, style: str) -> StoryboardResult:
        """解析文本格式的LLM响应"""
        shots = []
        characters = set()
        scenes = set()
        
        # 按段落分割
        paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
        
        shot_id = 1
        for paragraph in paragraphs:
            if len(paragraph) > 20:  # 过滤太短的段落
                # 提取场景和角色
                scene = self._extract_scene(paragraph)
                character_list = self._extract_characters(paragraph)
                
                shot = Shot(
                    shot_id=shot_id,
                    scene=scene,
                    characters=character_list,
                    action=paragraph[:100] + "..." if len(paragraph) > 100 else paragraph,
                    dialogue="",
                    image_prompt=self._generate_image_prompt(scene, character_list, paragraph, style)
                )
                
                shots.append(shot)
                characters.update(character_list)
                scenes.add(scene)
                shot_id += 1
        
        return StoryboardResult(
            shots=shots,
            total_duration=sum(shot.duration for shot in shots),
            characters=list(characters),
            scenes=list(scenes),
            style=style
        )
    
    def _extract_scene(self, text: str) -> str:
        """从文本中提取场景"""
        for keyword in self.scene_keywords:
            if keyword in text:
                return keyword
        
        # 如果没有找到关键词，尝试提取位置信息
        location_patterns = [
            r'在(.{1,10}?)里',
            r'在(.{1,10}?)中',
            r'(.{1,10}?)内',
            r'(.{1,10}?)外'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return "未知场景"
    
    def _extract_characters(self, text: str) -> List[str]:
        """从文本中提取角色"""
        characters = []
        
        for keyword in self.character_keywords:
            if keyword in text:
                # 使用角色名称标准化
                normalized_name = CharacterDetectionConfig.normalize_character_name(keyword)
                characters.append(normalized_name)
        
        # 去重
        return list(set(characters)) if characters else ["主角"]
    
    def _generate_image_prompt(self, scene: str, characters: List[str], action: str, style: str) -> str:
        """生成图像提示词"""
        character_str = "，".join(characters) if characters else "人物"
        
        if style in self.style_templates:
            prompt = self.style_templates[style].format(
                scene=scene,
                characters=character_str
            )
        else:
            prompt = f"{scene}，{character_str}，{action[:50]}"
        
        return prompt
    
    async def _optimize_image_prompts(self, storyboard: StoryboardResult, style: str, provider: Optional[str] = None):
        """优化图像提示词"""
        try:
            for shot in storyboard.shots:
                if shot.image_prompt:
                    result = await self.service_manager.execute_service_method(
                        ServiceType.LLM,
                        "optimize_prompt",
                        prompt=shot.image_prompt,
                        style=style,
                        provider=provider
                    )
                    
                    if result.success:
                        shot.image_prompt = result.data['content'].strip()
                    
                    # 避免请求过于频繁
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            logger.warning(f"优化图像提示词失败: {e}")
    
    async def rewrite_text(self, text: str, provider: Optional[str] = None) -> ServiceResult:
        """改写文本"""
        return await self.service_manager.execute_service_method(
            ServiceType.LLM,
            "rewrite_text",
            text=text,
            provider=provider
        )

    async def create_story_from_theme(self, theme: str, provider: Optional[str] = None) -> ServiceResult:
        """根据主题创作故事"""
        return await self.service_manager.execute_service_method(
            ServiceType.LLM,
            "create_story_from_theme",
            theme=theme,
            provider=provider
        )

    def get_available_styles(self) -> List[str]:
        """获取可用的风格列表"""
        return list(self.style_templates.keys())
    
    def add_style_template(self, name: str, template: str):
        """添加风格模板"""
        self.style_templates[name] = template
        logger.info(f"已添加风格模板: {name}")
    
    def export_storyboard(self, storyboard: StoryboardResult, format: str = "json") -> str:
        """导出分镜数据"""
        if format.lower() == "json":
            data = {
                "shots": [
                    {
                        "shot_id": shot.shot_id,
                        "scene": shot.scene,
                        "characters": shot.characters,
                        "action": shot.action,
                        "dialogue": shot.dialogue,
                        "image_prompt": shot.image_prompt,
                        "duration": shot.duration,
                        "camera_angle": shot.camera_angle,
                        "lighting": shot.lighting,
                        "mood": shot.mood
                    }
                    for shot in storyboard.shots
                ],
                "total_duration": storyboard.total_duration,
                "characters": storyboard.characters,
                "scenes": storyboard.scenes,
                "style": storyboard.style,
                "metadata": storyboard.metadata
            }
            return json.dumps(data, ensure_ascii=False, indent=2)
        
        elif format.lower() == "markdown":
            lines = ["# 分镜表\n"]
            lines.append(f"**风格**: {storyboard.style}")
            lines.append(f"**总时长**: {storyboard.total_duration:.1f}秒")
            lines.append(f"**角色**: {', '.join(storyboard.characters)}")
            lines.append(f"**场景**: {', '.join(storyboard.scenes)}\n")
            
            lines.append("| 镜头 | 场景 | 角色 | 动作 | 对话 | 画面描述 |")
            lines.append("|------|------|------|------|------|----------|")
            
            for shot in storyboard.shots:
                characters_str = ", ".join(shot.characters)
                lines.append(
                    f"| {shot.shot_id} | {shot.scene} | {characters_str} | "
                    f"{shot.action} | {shot.dialogue} | {shot.image_prompt} |"
                )
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"不支持的导出格式: {format}")