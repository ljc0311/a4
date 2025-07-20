# -*- coding: utf-8 -*-
"""
场景描述智能增强器

实现对五阶段分镜脚本中画面描述的智能增强，包括：
1. 技术细节分析和补充
2. 角色场景一致性描述注入
3. 内容融合和优化
"""

import re
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from src.utils.logger import logger
from src.utils.character_scene_manager import CharacterSceneManager
from src.utils.color_optimizer import ColorOptimizer
from src.utils.character_detection_config import CharacterDetectionConfig
from src.utils.style_consistency_manager import StyleConsistencyManager


@dataclass
class TechnicalDetails:
    """技术细节数据结构"""
    shot_type: str = ""  # 镜头类型
    camera_angle: str = ""  # 机位角度
    camera_movement: str = ""  # 镜头运动
    depth_of_field: str = ""  # 景深
    lighting: str = ""  # 光线
    composition: str = ""  # 构图
    color_tone: str = ""  # 色调
    
    def to_description(self) -> str:
        """转换为描述文本"""
        parts = []
        if self.shot_type:
            parts.append(f"镜头类型：{self.shot_type}")
        if self.camera_angle:
            parts.append(f"机位角度：{self.camera_angle}")
        if self.camera_movement:
            parts.append(f"镜头运动：{self.camera_movement}")
        if self.depth_of_field:
            parts.append(f"景深：{self.depth_of_field}")
        if self.lighting:
            parts.append(f"光线：{self.lighting}")
        if self.composition:
            parts.append(f"构图：{self.composition}")
        if self.color_tone:
            parts.append(f"色调：{self.color_tone}")
        return "，".join(parts)


@dataclass
class ConsistencyInfo:
    """一致性信息数据结构"""
    characters: List[str] = field(default_factory=list)  # 角色一致性描述
    scenes: List[str] = field(default_factory=list)  # 场景一致性描述
    detected_characters: List[str] = field(default_factory=list)  # 检测到的角色名称
    detected_scenes: List[str] = field(default_factory=list)  # 检测到的场景名称
    
    def to_description(self) -> str:
        """转换为描述文本"""
        parts = []
        if self.characters:
            parts.extend([f"角色一致性：{char}" for char in self.characters])
        if self.scenes:
            parts.extend([f"场景一致性：{scene}" for scene in self.scenes])
        return "；".join(parts)


class TechnicalDetailsAnalyzer:
    """技术细节分析器"""
    
    def __init__(self):
        # 技术细节推理规则
        self.shot_type_rules = {
            r'(特写|close.?up|特写镜头)': '特写',
            r'(近景|medium.?shot|中景)': '近景',
            r'(中景|medium.?shot)': '中景',
            r'(远景|long.?shot|全景)': '远景',
            r'(全景|wide.?shot|大全景)': '全景',
            r'(大全景|extreme.?wide)': '大全景'
        }
        
        self.camera_angle_rules = {
            r'(俯视|俯拍|bird.?eye|从上往下)': '俯视角度',
            r'(仰视|仰拍|worm.?eye|从下往上)': '仰视角度',
            r'(平视|水平|eye.?level)': '平视角度',
            r'(侧面|侧视|profile)': '侧面角度'
        }
        
        self.camera_movement_rules = {
            r'(推进|推镜|dolly.?in|zoom.?in)': '推镜',
            r'(拉远|拉镜|dolly.?out|zoom.?out)': '拉镜',
            r'(摇镜|摇摆|pan)': '摇镜',
            r'(跟拍|跟随|follow)': '跟拍',
            r'(环绕|围绕|orbit)': '环绕拍摄',
            r'(手持|晃动|handheld)': '手持拍摄'
        }
        
        self.lighting_rules = {
            r'(自然光|阳光|日光|daylight)': '自然光',
            r'(室内光|灯光|artificial)': '人工光源',
            r'(柔光|soft.?light)': '柔光',
            r'(硬光|hard.?light)': '硬光',
            r'(逆光|backlight)': '逆光',
            r'(侧光|side.?light)': '侧光',
            r'(顶光|top.?light)': '顶光',
            r'(暖光|warm.?light)': '暖色调光线',
            r'(冷光|cool.?light)': '冷色调光线'
        }
        
        self.composition_rules = {
            r'(三分法|rule.?of.?thirds)': '三分法构图',
            r'(对称|symmetr)': '对称构图',
            r'(对角线|diagonal)': '对角线构图',
            r'(中心|center)': '中心构图',
            r'(框架|frame)': '框架构图',
            r'(引导线|leading.?line)': '引导线构图'
        }
        
        self.depth_rules = {
            r'(浅景深|shallow.?depth)': '浅景深',
            r'(深景深|deep.?depth)': '深景深',
            r'(背景虚化|blur|bokeh)': '背景虚化',
            r'(前景|foreground)': '前景突出',
            r'(背景|background)': '背景清晰'
        }
        
        self.color_tone_rules = {
            r'(暖色调|warm.?tone)': '暖色调',
            r'(冷色调|cool.?tone)': '冷色调',
            r'(高对比|high.?contrast)': '高对比度',
            r'(低对比|low.?contrast)': '低对比度',
            r'(饱和|saturated)': '高饱和度',
            r'(淡雅|desaturated)': '低饱和度',
            r'(黑白|monochrome)': '黑白色调'
        }
    
    def analyze_description(self, description: str) -> TechnicalDetails:
        """分析画面描述，推理技术细节
        
        Args:
            description: 原始画面描述
            
        Returns:
            TechnicalDetails: 推理出的技术细节
        """
        details = TechnicalDetails()
        
        try:
            # 分析镜头类型
            details.shot_type = self._analyze_with_rules(description, self.shot_type_rules)
            
            # 分析机位角度
            details.camera_angle = self._analyze_with_rules(description, self.camera_angle_rules)
            
            # 分析镜头运动
            details.camera_movement = self._analyze_with_rules(description, self.camera_movement_rules)
            
            # 分析光线
            details.lighting = self._analyze_with_rules(description, self.lighting_rules)
            
            # 分析构图
            details.composition = self._analyze_with_rules(description, self.composition_rules)
            
            # 分析景深
            details.depth_of_field = self._analyze_with_rules(description, self.depth_rules)
            
            # 分析色调
            details.color_tone = self._analyze_with_rules(description, self.color_tone_rules)
            
            # 智能推理补充
            self._intelligent_inference(description, details)
            
        except Exception as e:
            logger.error(f"技术细节分析失败: {e}")
        
        return details
    
    def _analyze_with_rules(self, text: str, rules: Dict[str, str]) -> str:
        """使用规则分析文本"""
        for pattern, result in rules.items():
            if re.search(pattern, text, re.IGNORECASE):
                return result
        return ""
    

    
    def _intelligent_inference(self, description: str, details: TechnicalDetails):
        """智能推理补充技术细节"""
        # 基于内容推理镜头类型
        if not details.shot_type:
            if any(word in description for word in ['脸部', '表情', '眼神', '面部']):
                details.shot_type = '特写'
            elif any(word in description for word in ['全身', '整个人', '站立', '走路']):
                details.shot_type = '全景'
            elif any(word in description for word in ['上半身', '胸部以上', '肩膀']):
                details.shot_type = '中景'
        
        # 基于场景推理光线
        if not details.lighting:
            if any(word in description for word in ['室外', '阳光', '白天', '户外']):
                details.lighting = '自然光'
            elif any(word in description for word in ['室内', '灯光', '夜晚']):
                details.lighting = '人工光源'
        
        # 基于动作推理镜头运动
        if not details.camera_movement:
            if any(word in description for word in ['走向', '靠近', '接近']):
                details.camera_movement = '推镜'
            elif any(word in description for word in ['远离', '后退', '离开']):
                details.camera_movement = '拉镜'
            elif any(word in description for word in ['转身', '环顾', '四周']):
                details.camera_movement = '摇镜'


class ConsistencyInjector:
    """一致性描述注入器 - 使用通用NLP技术动态识别角色和场景"""

    def __init__(self, character_scene_manager: CharacterSceneManager, service_manager=None):
        self.character_scene_manager = character_scene_manager
        self.service_manager = service_manager  # 添加service_manager属性

        # 缓存已加载的角色和场景数据
        self._characters_cache = None
        self._scenes_cache = None
        self._last_cache_update = 0

        # 通用场景类型关键词（不依赖特定小说）
        self.generic_scene_patterns = {
            '室内': ['室内', '房间', '屋内', '内部', '里面'],
            '室外': ['室外', '户外', '外面', '野外', '街道'],
            '办公场所': ['办公室', '会议室', '工作室', '书房'],
            '居住场所': ['家', '客厅', '卧室', '厨房', '浴室'],
            '教育场所': ['学校', '教室', '实验室', '图书馆', '校园'],
            '自然环境': ['山', '海', '森林', '草原', '沙漠', '河流'],
            '城市环境': ['城市', '街道', '广场', '公园', '商场']
        }
    
    def extract_consistency_info(self, description: str, characters: Optional[List[str]] = None) -> ConsistencyInfo:
        """从描述中提取一致性信息
        
        Args:
            description: 画面描述
            characters: 已知角色列表
            
        Returns:
            ConsistencyInfo: 一致性信息
        """
        consistency_info = ConsistencyInfo()
        
        try:
            # 识别角色
            detected_characters = self._detect_characters(description, characters)
            consistency_info.detected_characters = detected_characters
            
            # 记录角色检测详情
            logger.debug(f"角色检测结果: {detected_characters}")
            
            # 获取角色一致性描述
            for char_name in detected_characters:
                char_consistency = self._get_character_consistency(char_name)
                if char_consistency:
                    consistency_info.characters.append(char_consistency)
                    logger.debug(f"角色 '{char_name}' 一致性描述: {char_consistency[:50]}...")
                else:
                    logger.debug(f"角色 '{char_name}' 未找到一致性描述")
            
            # 识别场景
            detected_scenes = self._detect_scenes(description)
            consistency_info.detected_scenes = detected_scenes
            
            # 记录场景检测详情
            logger.debug(f"场景检测结果: {detected_scenes}")
            
            # 获取场景一致性描述
            for scene_name in detected_scenes:
                scene_consistency = self._get_scene_consistency(scene_name)
                if scene_consistency:
                    consistency_info.scenes.append(scene_consistency)
                    logger.debug(f"场景 '{scene_name}' 一致性描述: {scene_consistency[:50]}...")
                else:
                    logger.debug(f"场景 '{scene_name}' 未找到一致性描述")
                    
        except Exception as e:
            logger.error(f"一致性信息提取失败: {e}")
        
        return consistency_info
    
    def _detect_characters(self, description: str, known_characters: Optional[List[str]] = None) -> List[str]:
        """动态检测描述中的角色 - 改进版"""
        detected = []
        
        # 获取项目中的所有角色数据（包含别名和关键词）
        project_characters_data = self._get_all_project_characters_with_data()
        
        # 优先检测已知角色（从参数传入）
        if known_characters:
            for char in known_characters:
                if self._is_character_mentioned(char, description, project_characters_data):
                    if char not in detected:
                        detected.append(char)
        
        # 检测项目中的所有角色
        for char_name, char_data in project_characters_data.items():
            if self._is_character_mentioned(char_name, description, {char_name: char_data}):
                if char_name not in detected:
                    detected.append(char_name)
        
        return detected
    
    def _nlp_character_matching(self, char_name: str, description: str, char_data: dict) -> bool:
        """NLP角色匹配：使用自然语言处理技术处理各种复杂的角色称谓（不包含LLM）"""
        try:
            # 1. 基础同义词匹配（可扩展的映射表）
            if self._check_character_synonyms(char_name, description):
                return True
            
            # 2. 角色类型和特征匹配
            if self._check_character_type_matching(char_name, description, char_data):
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"NLP角色匹配失败: {e}")
            return False
    
    def _intelligent_character_matching(self, char_name: str, description: str, char_data: dict) -> bool:
        """智能角色匹配：优先使用LLM，然后使用NLP技术"""
        try:
            # 1. 优先使用LLM进行智能匹配
            if self._use_llm_for_character_matching(char_name, description, char_data):
                return True
            
            # 2. 如果LLM匹配失败，则使用NLP技术进行匹配
            if self._nlp_character_matching(char_name, description, char_data):
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"智能角色匹配失败: {e}")
            return False
    
    def _check_character_synonyms(self, char_name: str, description: str) -> bool:
        """检查角色同义词匹配"""
        from src.utils.character_detection_config import CharacterDetectionConfig
        
        # 获取所有同义词映射
        all_synonyms = CharacterDetectionConfig.get_all_synonyms()
        
        # 检查同义词匹配
        synonyms = all_synonyms.get(char_name, [])
        for synonym in synonyms:
            if synonym in description:
                return True
        
        # 反向检查：如果描述中的词是角色名的同义词
        for base_name, synonym_list in all_synonyms.items():
            if char_name in synonym_list:
                if base_name in description:
                    return True
        
        return False
    
    def _check_character_type_matching(self, char_name: str, description: str, char_data: dict) -> bool:
        """检查角色类型和特征匹配"""
        # 获取角色类型
        char_type = char_data.get('type', '').lower()
        
        # 动物角色特殊处理
        if char_type == 'animal' or self._is_animal_character(char_name):
            return self._match_animal_character(char_name, description, char_data)
        
        # 人类角色处理
        if char_type == 'human' or char_type == '':
            return self._match_human_character(char_name, description, char_data)
        
        # 其他类型角色（机器人、神话生物等）
        return self._match_other_character(char_name, description, char_data)
    
    def _is_animal_character(self, char_name: str) -> bool:
        """判断是否为动物角色"""
        from src.utils.character_detection_config import CharacterDetectionConfig
        
        animal_info = CharacterDetectionConfig.get_animal_info()
        animal_keywords = animal_info['keywords']
        return any(animal in char_name for animal in animal_keywords)
    
    def _match_animal_character(self, char_name: str, description: str, char_data: dict) -> bool:  # noqa: ARG002
        """匹配动物角色"""
        from src.utils.character_detection_config import CharacterDetectionConfig
        
        # 提取动物类型
        animal_type = self._extract_animal_type(char_name)
        if animal_type and animal_type in description:
            return True
        
        # 检查动物相关的描述词
        animal_info = CharacterDetectionConfig.get_animal_info()
        animal_descriptors = animal_info['descriptors']
        
        for animal, descriptors in animal_descriptors.items():
            if animal in char_name:
                if any(desc in description for desc in descriptors):
                    return True
        
        return False
    
    def _extract_animal_type(self, char_name: str) -> str:
        """从角色名中提取动物类型"""
        from src.utils.character_detection_config import CharacterDetectionConfig
        
        animal_info = CharacterDetectionConfig.get_animal_info()
        animal_map = animal_info['type_map']
        
        for key, value in animal_map.items():
            if key in char_name:
                return value
        return ''
    
    def _match_human_character(self, char_name: str, description: str, char_data: dict) -> bool:  # noqa: ARG002
        """匹配人类角色"""
        from src.utils.character_detection_config import CharacterDetectionConfig
        
        # 检查年龄相关描述
        age_keywords = CharacterDetectionConfig.AGE_KEYWORDS
        
        for age_indicator, keywords in age_keywords.items():
            if age_indicator in char_name:
                if any(keyword in description for keyword in keywords):
                    return True
        
        return False
    
    def _match_other_character(self, char_name: str, description: str, char_data: dict) -> bool:  # noqa: ARG002
        """匹配其他类型角色"""
        from src.utils.character_detection_config import CharacterDetectionConfig
        
        # 机器人、外星人、神话生物等的匹配逻辑
        special_info = CharacterDetectionConfig.get_special_type_info()
        special_descriptors = special_info['descriptors']
        
        for char_type, keywords in special_descriptors.items():
            if char_type in char_name:
                if any(keyword in description for keyword in keywords):
                    return True
        
        return False
    

    
    def _use_llm_for_character_matching(self, char_name: str, description: str, char_data: dict) -> bool:
        """使用LLM进行智能角色匹配（增强版）"""
        try:
            # 构建更全面的角色特征描述
            char_features = []
            
            # 基本信息
            char_type = char_data.get('type', 'human')
            char_features.append(f"类型：{char_type}")
            
            # 外貌特征 - 安全处理可能是字符串的情况
            appearance = char_data.get('appearance', {})
            if isinstance(appearance, dict):
                if appearance.get('gender'):
                    char_features.append(f"性别：{appearance['gender']}")
                if appearance.get('age_range'):
                    char_features.append(f"年龄：{appearance['age_range']}")
                if appearance.get('hair'):
                    char_features.append(f"头发：{appearance['hair']}")
                if appearance.get('build'):
                    char_features.append(f"体型：{appearance['build']}")
                if appearance.get('species'):
                    char_features.append(f"种族/物种：{appearance['species']}")
            elif isinstance(appearance, str) and appearance:
                char_features.append(f"外貌：{appearance}")
            
            # 🔧 修复：服装特征 - 安全处理可能是字符串的情况
            clothing = char_data.get('clothing', {})
            if isinstance(clothing, dict):
                if clothing.get('style'):
                    char_features.append(f"服装：{clothing['style']}")
            elif isinstance(clothing, str) and clothing:
                char_features.append(f"服装：{clothing}")

            # 🔧 修复：性格特征 - 安全处理可能是字符串的情况
            personality = char_data.get('personality', {})
            if isinstance(personality, dict):
                if personality.get('traits'):
                    char_features.append(f"性格：{personality['traits']}")
            elif isinstance(personality, str) and personality:
                char_features.append(f"性格：{personality}")
            
            # 别名
            aliases = char_data.get('aliases', [])
            if aliases:
                char_features.append(f"别名：{', '.join(aliases)}")
            
            # 如果没有足够的特征信息，不使用LLM
            if len(char_features) < 2:
                return False
            
            # 构建增强的LLM提示
            prompt = f"""请分析以下文本描述中是否提到了指定角色。

角色信息：
- 名称：{char_name}
- 特征：{'; '.join(char_features)}

文本描述：
{description}

分析要求：
1. 即使名称不完全匹配，但如果特征高度吻合，也应认为是同一角色
2. 对于动物角色，重点关注物种、行为特征
3. 对于人类角色，重点关注外貌、年龄、性别特征
4. 考虑同义词、昵称、称谓变化

请仅回答"是"或"否"。"""
            
            # 调用LLM服务
            if hasattr(self, 'service_manager') and self.service_manager:
                from src.core.service_manager import ServiceType
                llm_service = self.service_manager.get_service(ServiceType.LLM)
                if llm_service:
                    try:
                        # 使用异步调用并正确处理返回值
                        import asyncio
                        import concurrent.futures

                        def run_llm_call():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                result = loop.run_until_complete(
                                    llm_service.execute(prompt=prompt, max_tokens=20, temperature=0.3)
                                )
                                return result
                            finally:
                                loop.close()

                        # 在线程池中执行，避免阻塞
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(run_llm_call)
                            try:
                                result = future.result(timeout=30)  # 30秒超时
                                if result and result.success and result.data:
                                    response_text = result.data.get('content', '')
                                    if isinstance(response_text, str):
                                        return '是' in response_text or 'yes' in response_text.lower()
                            except concurrent.futures.TimeoutError:
                                logger.debug("LLM角色匹配调用超时")
                            except Exception as e:
                                logger.debug(f"LLM角色匹配调用失败: {e}")
                    except Exception as e:
                        logger.debug(f"LLM角色匹配服务调用异常: {e}")

            return False
            
        except Exception as e:
            logger.debug(f"LLM角色匹配失败: {e}")
            return False
    
    def _is_character_mentioned(self, char_name: str, description: str, characters_data: dict) -> bool:
        """检查角色是否在描述中被提及 - 改进版，优先使用LLM智能匹配"""
        # 直接名称匹配
        if char_name in description:
            return True

        # 检查角色数据中的别名和关键词
        char_data = characters_data.get(char_name, {})

        # 检查别名（使用智能匹配避免误匹配）
        aliases = char_data.get('aliases', [])
        if isinstance(aliases, list):
            for alias in aliases:
                if alias and self._smart_alias_matching(alias, description):
                    return True

        # 智能名称匹配：检查是否是角色名的一部分（如"李青山"和"青山"）
        if self._smart_name_matching(char_name, description):
            return True

        # 1. 优先使用LLM进行智能匹配
        if self._use_llm_for_character_matching(char_name, description, char_data):
            return True

        # 2. 如果LLM匹配失败，则使用NLP技术进行匹配
        # 智能匹配：使用更灵活的角色检测策略（不包含LLM）
        if self._nlp_character_matching(char_name, description, char_data):
            return True
        
        # 🔧 修复：检查外貌特征关键词 - 安全处理可能是字符串的情况
        appearance = char_data.get('appearance', {})
        if appearance:
            if isinstance(appearance, dict):
                # 检查头发特征
                hair = appearance.get('hair', '')
                if isinstance(hair, str) and hair:
                    if any(keyword in description for keyword in hair.split() if len(keyword) > 1):
                        return True

                # 检查性别和年龄
                gender = appearance.get('gender', '')
                age_range = appearance.get('age_range', '')
                if gender and gender in description:
                    return True
                if '大叔' in description and '40-50岁' in age_range:
                    return True
                if '光头' in description and '光头' in hair:
                    return True
            elif isinstance(appearance, str):
                # 如果appearance是字符串，直接在描述中查找关键词
                if any(keyword in description for keyword in appearance.split() if len(keyword) > 1):
                    return True

        # 🔧 修复：检查服装特征 - 安全处理可能是字符串的情况
        clothing = char_data.get('clothing', {})
        if clothing:
            if isinstance(clothing, dict):
                style = clothing.get('style', '')
                if isinstance(style, str) and style:
                    if any(keyword in description for keyword in style.split() if len(keyword) > 1):
                        return True
            elif isinstance(clothing, str):
                # 如果clothing是字符串，直接在描述中查找关键词
                if any(keyword in description for keyword in clothing.split() if len(keyword) > 1):
                    return True
        
        return False

    def _smart_name_matching(self, char_name: str, description: str) -> bool:
        """智能名称匹配：检查描述中是否包含角色名的一部分或变体

        Args:
            char_name: 完整角色名（如"李青山"）
            description: 描述文本（可能包含"青山"）

        Returns:
            bool: 是否匹配
        """
        if not char_name or not description:
            return False

        # 1. 检查是否是角色名的后缀（如"李青山" -> "青山"）
        if len(char_name) >= 3:  # 至少3个字符才考虑后缀匹配
            # 取后两个字符作为可能的昵称
            suffix_2 = char_name[-2:]
            if suffix_2 in description and len(suffix_2) >= 2:
                # 确保不是其他词的一部分，检查前后字符
                pattern = rf'(?<![a-zA-Z\u4e00-\u9fa5]){re.escape(suffix_2)}(?![a-zA-Z\u4e00-\u9fa5])'
                if re.search(pattern, description):
                    logger.debug(f"智能匹配成功: {char_name} -> {suffix_2}")
                    return True

            # 取后三个字符作为可能的昵称（如果角色名够长）
            if len(char_name) >= 4:
                suffix_3 = char_name[-3:]
                if suffix_3 in description and len(suffix_3) >= 3:
                    pattern = rf'(?<![a-zA-Z\u4e00-\u9fa5]){re.escape(suffix_3)}(?![a-zA-Z\u4e00-\u9fa5])'
                    if re.search(pattern, description):
                        logger.debug(f"智能匹配成功: {char_name} -> {suffix_3}")
                        return True

        # 2. 检查是否是角色名的前缀（如"李青山" -> "李青"）
        if len(char_name) >= 3:
            prefix_2 = char_name[:2]
            if prefix_2 in description and len(prefix_2) >= 2:
                pattern = rf'(?<![a-zA-Z\u4e00-\u9fa5]){re.escape(prefix_2)}(?![a-zA-Z\u4e00-\u9fa5])'
                if re.search(pattern, description):
                    logger.debug(f"智能匹配成功: {char_name} -> {prefix_2}")
                    return True

        # 3. 检查是否是角色名的中间部分（如"李青山" -> "青"，但这种情况要更谨慎）
        if len(char_name) >= 4:
            for i in range(1, len(char_name) - 1):
                for j in range(i + 2, len(char_name) + 1):  # 至少2个字符
                    middle_part = char_name[i:j]
                    if len(middle_part) >= 2 and middle_part in description:
                        pattern = rf'(?<![a-zA-Z\u4e00-\u9fa5]){re.escape(middle_part)}(?![a-zA-Z\u4e00-\u9fa5])'
                        if re.search(pattern, description):
                            logger.debug(f"智能匹配成功: {char_name} -> {middle_part}")
                            return True

        return False

    def _smart_alias_matching(self, alias: str, description: str) -> bool:
        """智能别名匹配：避免在地理名词等上下文中误匹配

        Args:
            alias: 角色别名（如"青山"）
            description: 描述文本

        Returns:
            bool: 是否匹配
        """
        if not alias or not description or alias not in description:
            return False

        # 地理名词黑名单检查（检查整个描述）
        geographic_patterns = [
            '青山绿水', '山清水秀', '青山如黛', '青山依旧',
            '小山村', '小山坡', '小山丘', '青山绿水的美景'
        ]

        # 如果匹配到地理名词模式，不匹配
        for geo_pattern in geographic_patterns:
            if geo_pattern in description:
                return False

        # 检查是否有人物动作或对话的上下文
        person_indicators = ['说', '道', '笑', '哭', '走', '跑', '站', '坐', '看', '听', '想', '感到', '觉得', '拔出', '准备', '微笑', '点头', '眺望']
        has_person_context = any(indicator in description for indicator in person_indicators)

        if has_person_context:
            return True

        # 检查是否在句子开头（简化版）
        if description.startswith(alias):
            return True

        return False

    def _detect_scenes(self, description: str) -> List[str]:
        """动态检测描述中的场景"""
        detected = []
        
        # 动态加载项目中的所有场景并进行匹配
        project_scenes = self._get_all_project_scenes()
        for scene_name, scene_keywords in project_scenes.items():
            # 检查场景名称直接匹配
            if scene_name in description:
                detected.append(scene_name)
                continue
            
            # 检查场景关键词匹配
            if scene_keywords and any(keyword in description for keyword in scene_keywords):
                detected.append(scene_name)
        
        # 如果没有匹配到具体场景，尝试匹配通用场景类型
        if not detected:
            for scene_type, keywords in self.generic_scene_patterns.items():
                if any(keyword in description for keyword in keywords):
                    detected.append(f"通用{scene_type}")
                    break
        
        return detected
    
    def _get_character_consistency(self, character_name: str) -> str:
        """获取角色一致性描述"""
        try:
            if not self.character_scene_manager:
                logger.warning("角色场景管理器未初始化")
                return ""

            characters_data = self.character_scene_manager._load_json(
                self.character_scene_manager.characters_file
            )

            # 查找角色数据
            for _char_id, char_data in characters_data.get('characters', {}).items():
                if char_data.get('name') == character_name or char_data.get('id') == character_name:
                    consistency_prompt = char_data.get('consistency_prompt', '')
                    if consistency_prompt:
                        logger.info(f"获取到角色'{character_name}'的一致性描述: {consistency_prompt}")
                        return consistency_prompt
                    else:
                        logger.warning(f"角色'{character_name}'没有一致性描述")
                        return ""

            logger.warning(f"未找到角色'{character_name}'的数据")
            return ""

        except Exception as e:
            logger.error(f"获取角色一致性描述失败 {character_name}: {e}")
            return ""
    
    def _get_scene_consistency(self, scene_name: str) -> str:
        """获取场景一致性描述"""
        try:
            scenes_data = self.character_scene_manager._load_json(
                self.character_scene_manager.scenes_file
            )
            
            # 查找场景数据
            for _scene_id, scene_data in scenes_data.get('scenes', {}).items():
                if scene_data.get('name') == scene_name or scene_data.get('id') == scene_name:
                    return scene_data.get('consistency_prompt', '')
            
        except Exception as e:
            logger.error(f"获取场景一致性描述失败 {scene_name}: {e}")
        
        return ""
    
    def _get_all_project_characters(self) -> List[str]:
        """获取项目中的所有角色名称"""
        try:
            # 检查缓存是否需要更新
            import time
            current_time = time.time()
            if (self._characters_cache is None or 
                current_time - self._last_cache_update > 60):  # 缓存60秒
                
                characters_data = self.character_scene_manager._load_json(
                    self.character_scene_manager.characters_file
                )
                
                character_names = []
                for char_data in characters_data.get('characters', {}).values():
                    char_name = char_data.get('name', '')
                    if char_name:
                        character_names.append(char_name)
                        
                        # 也添加角色的别名或昵称（如果有的话）
                        aliases = char_data.get('aliases', [])
                        if isinstance(aliases, list):
                            character_names.extend(aliases)
                
                self._characters_cache = character_names
                self._last_cache_update = current_time
            
            return self._characters_cache or []
            
        except Exception as e:
            logger.error(f"获取项目角色列表失败: {e}")
            return []
    
    def _get_all_project_characters_with_data(self) -> Dict[str, dict]:
        """获取项目中的所有角色及其完整数据"""
        try:
            characters_data = self.character_scene_manager._load_json(
                self.character_scene_manager.characters_file
            )
            
            character_dict = {}
            for char_data in characters_data.get('characters', {}).values():
                char_name = char_data.get('name', '')
                if char_name:
                    character_dict[char_name] = char_data
            
            return character_dict
            
        except Exception as e:
            logger.error(f"获取项目角色数据失败: {e}")
            return {}
    
    def _get_all_project_scenes(self) -> Dict[str, List[str]]:
        """获取项目中的所有场景及其关键词"""
        try:
            # 检查缓存是否需要更新
            import time
            current_time = time.time()
            if (self._scenes_cache is None or 
                current_time - self._last_cache_update > 60):  # 缓存60秒
                
                scenes_data = self.character_scene_manager._load_json(
                    self.character_scene_manager.scenes_file
                )
                
                scene_info = {}
                for scene_data in scenes_data.get('scenes', {}).values():
                    scene_name = scene_data.get('name', '')
                    if scene_name:
                        # 获取场景关键词
                        keywords = scene_data.get('keywords', [])
                        if not isinstance(keywords, list):
                            keywords = []
                        
                        # 添加场景描述中的关键词（简单提取）
                        description = scene_data.get('description', '')
                        if description:
                            # 简单的关键词提取：分割并过滤常见词汇
                            desc_words = [word.strip('，。！？；：') for word in description.split() 
                                        if len(word.strip('，。！？；：')) > 1]
                            keywords.extend(desc_words[:5])  # 只取前5个词避免过多
                        
                        scene_info[scene_name] = keywords
                
                self._scenes_cache = scene_info
                self._last_cache_update = current_time
            
            return self._scenes_cache or {}
            
        except Exception as e:
            logger.error(f"获取项目场景列表失败: {e}")
            return {}


@dataclass
class FusionResult:
    """内容融合结果数据结构"""
    enhanced_description: str = ""
    technical_additions: List[str] = field(default_factory=list)
    consistency_additions: List[str] = field(default_factory=list)
    fusion_quality_score: float = 0.0


class ContentFuser:
    """智能内容融合器 - 第二阶段核心组件"""
    
    def __init__(self, project_root=None, llm_api=None, character_scene_manager=None):
        # 初始化LLM API
        self.llm_api = llm_api
        self.project_root = project_root
        self.character_scene_manager = character_scene_manager
        self.style_manager = StyleConsistencyManager(project_root) if project_root else None
        # 初始化角色场景管理器
        if character_scene_manager is None and project_root:
            from src.utils.character_scene_manager import CharacterSceneManager
            self.character_scene_manager = CharacterSceneManager(project_root)
        else:
            self.character_scene_manager = character_scene_manager
        
        # 融合策略配置
        self.fusion_strategies = {
            'natural': self._natural_fusion,
            'structured': self._structured_fusion,
            'minimal': self._minimal_fusion,
            'intelligent': self._natural_fusion  # 新增智能融合策略
        }
        
        # 内容优先级权重
        self.priority_weights = {
            'original_description': 1.0,
            'character_consistency': 0.8,
            'scene_consistency': 0.7,
            'technical_details': 0.6
        }

        # 融合质量评估规则
        self.quality_rules = {
            'length_balance': 0.3,  # 长度平衡
            'content_coherence': 0.4,  # 内容连贯性
            'information_density': 0.3  # 信息密度
        }

    def _is_already_enhanced(self, description: str) -> bool:
        """检查描述是否已经增强过"""
        try:
            # 检查是否包含角色一致性描述的特征
            if "（中国人，" in description and "岁" in description and ("战袍" in description or "军装" in description):
                return True

            # 检查是否包含风格提示词
            if "水彩画风，柔和笔触，粉彩色，插画，温柔" in description:
                return True

            return False

        except Exception as e:
            logger.debug(f"检查增强状态失败: {e}")
            return False
    
    def _get_character_consistency(self, character_name: str) -> str:
        """获取角色一致性描述"""
        try:
            if not self.character_scene_manager:
                logger.warning("角色场景管理器未初始化")
                return ""

            characters_data = self.character_scene_manager._load_json(
                self.character_scene_manager.characters_file
            )

            # 查找角色数据
            for _char_id, char_data in characters_data.get('characters', {}).items():
                if char_data.get('name') == character_name or char_data.get('id') == character_name:
                    return char_data.get('consistency_prompt', '')

        except Exception as e:
            logger.error(f"获取角色一致性描述失败 {character_name}: {e}")

        return ""
    
    def _embed_character_descriptions(self, original_desc: str, detected_characters: List[str]) -> str:
        """将角色一致性描述直接嵌入到原始描述中"""
        if not detected_characters:
            return original_desc
        
        enhanced_desc = original_desc
        
        # 获取角色一致性信息
        character_descriptions = {}
        for character_name in detected_characters:
            # 直接使用_get_character_consistency方法获取角色一致性描述
            character_consistency = self._get_character_consistency(character_name)
            if character_consistency:
                character_descriptions[character_name] = character_consistency
        
        # 按角色名长度降序排序，优先替换更长的角色名，避免"李静妈妈"被"李静"误匹配
        sorted_characters = sorted(character_descriptions.items(), key=lambda x: len(x[0]), reverse=True)
        
        # 在原始描述中替换角色名称为详细描述
        for character_name, detailed_desc in sorted_characters:
            # 使用精确匹配进行角色替换，支持中文字符
            replacement = f"{character_name}（{detailed_desc}）"
            # 只有当角色名还没有被替换过时才进行替换（避免重复替换）
            if character_name in enhanced_desc and f"{character_name}（" not in enhanced_desc:
                # 检查当前角色名是否是其他更长角色名的一部分
                is_part_of_longer_name = False
                for other_char_name in character_descriptions.keys():
                    if other_char_name != character_name and len(other_char_name) > len(character_name):
                        if character_name in other_char_name and other_char_name in enhanced_desc:
                            is_part_of_longer_name = True
                            break
                
                # 只有当不是其他角色名的一部分时才进行替换
                if not is_part_of_longer_name:
                    # 对于单字符角色名（如"我"），使用更精确的匹配
                     if len(character_name) == 1:
                         # 查找所有匹配位置，手动检查边界
                         matches = []
                         start = 0
                         while True:
                             pos = enhanced_desc.find(character_name, start)
                             if pos == -1:
                                 break
                             # 检查前后字符，确保这是一个独立的字符
                             before_char = enhanced_desc[pos-1] if pos > 0 else ''
                             after_char = enhanced_desc[pos+len(character_name)] if pos+len(character_name) < len(enhanced_desc) else ''
                             
                             # 对于"我"，如果后面是"们"，则跳过
                             if character_name == '我' and after_char == '们':
                                 start = pos + 1
                                 continue
                             
                             # 如果前后都不是字母数字或中文字符，则认为是独立的字符
                             if (not before_char or not (before_char.isalnum() or '\u4e00' <= before_char <= '\u9fff')) and \
                                (not after_char or not (after_char.isalnum() or '\u4e00' <= after_char <= '\u9fff')):
                                 matches.append(pos)
                             start = pos + 1
                         
                         # 从后往前替换，避免位置偏移
                         for pos in reversed(matches):
                             enhanced_desc = enhanced_desc[:pos] + replacement + enhanced_desc[pos+len(character_name):]
                     else:
                         enhanced_desc = enhanced_desc.replace(character_name, replacement)
                     logger.info(f"角色描述嵌入: {character_name} -> {replacement[:50]}...")
        
        return enhanced_desc
    
    def fuse_content(self, original: str, technical: Optional[TechnicalDetails],
                    consistency: Optional[ConsistencyInfo], strategy: str = 'intelligent', style: Optional[str] = None) -> FusionResult:
        """智能融合内容
        
        Args:
            original: 原始描述
            technical: 技术细节
            consistency: 一致性信息
            strategy: 融合策略
            
        Returns:
            FusionResult: 融合结果
        """
        try:
            logger.info(f"开始内容融合，策略: {strategy}")
            
            # 预处理内容
            processed_content = self._preprocess_content(original, technical, consistency, style)
            
            # 执行融合策略
            fusion_func = self.fusion_strategies.get(strategy, self._natural_fusion)
            result = fusion_func(processed_content)
            
            # 后处理和质量评估
            result = self._postprocess_result(result)
            
            logger.info(f"内容融合完成，质量评分: {result.fusion_quality_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"内容融合失败: {e}")
            return FusionResult(enhanced_description=original)
    
    def _preprocess_content(self, original: str, technical: Optional[TechnicalDetails],
                          consistency: Optional[ConsistencyInfo], style: Optional[str] = None) -> Dict[str, Any]:
        """预处理内容"""
        return {
            'original': original.strip(),
            'technical_parts': self._extract_technical_parts(technical),
            'consistency_parts': self._extract_consistency_parts(consistency),
            'detected_characters': getattr(consistency, 'detected_characters', []) if consistency else [],
            'detected_scenes': getattr(consistency, 'detected_scenes', []) if consistency else [],
            'original_length': len(original),
            'has_punctuation': original.endswith(('。', '！', '？', '.', '!', '?')),
            'style': style  # 🔧 新增：传递风格参数
        }
    
    def _extract_technical_parts(self, technical: Optional[TechnicalDetails]) -> List[str]:
        """提取技术细节部分"""
        parts = []
        if technical:
            if technical.shot_type:
                parts.append(f"{technical.shot_type}镜头")
            if technical.camera_angle:
                parts.append(technical.camera_angle)
            if technical.lighting:
                parts.append(technical.lighting)
            if technical.camera_movement:
                parts.append(technical.camera_movement)
            if technical.composition:
                parts.append(technical.composition)
        return parts

    def _extract_consistency_parts(self, consistency: Optional[ConsistencyInfo]) -> List[str]:
        """提取一致性信息部分"""
        parts = []
        if consistency:
            # 处理角色一致性
            for char_desc in consistency.characters:
                if char_desc and len(char_desc.strip()) > 0:
                    # 提取关键特征描述
                    key_features = self._extract_key_features(char_desc)
                    parts.extend(key_features)

            # 处理场景一致性
            for scene_desc in consistency.scenes:
                if scene_desc and len(scene_desc.strip()) > 0:
                    # 提取关键环境描述
                    key_env = self._extract_key_environment(scene_desc)
                    parts.extend(key_env)
        return parts
    
    def _extract_key_features(self, description: str) -> List[str]:
        """从角色描述中提取关键特征"""
        # 简单的关键特征提取逻辑
        features = []
        
        # 外貌特征关键词
        appearance_keywords = ['头发', '眼睛', '身高', '体型', '服装', '穿着', '戴着']
        for keyword in appearance_keywords:
            if keyword in description:
                # 提取包含关键词的短语
                sentences = description.split('，')
                for sentence in sentences:
                    if keyword in sentence and len(sentence.strip()) < 20:
                        features.append(sentence.strip())
                        break
        
        return features[:2]  # 最多返回2个关键特征
    
    def _extract_key_environment(self, description: str) -> List[str]:
        """从场景描述中提取关键环境信息"""
        env_info = []
        
        # 环境特征关键词
        env_keywords = ['光线', '氛围', '背景', '环境', '设备', '装饰']
        for keyword in env_keywords:
            if keyword in description:
                sentences = description.split('，')
                for sentence in sentences:
                    if keyword in sentence and len(sentence.strip()) < 25:
                        env_info.append(sentence.strip())
                        break
        
        return env_info[:1]  # 最多返回1个环境信息
    
    def _natural_fusion_impl(self, content: Dict[str, Any]) -> FusionResult:
        """自然融合策略"""
        result = FusionResult()
        parts = [content['original']]
        
        # 自然地添加技术细节
        if content['technical_parts']:
            tech_text = "，".join(content['technical_parts'][:2])  # 限制技术细节数量
            if content['has_punctuation']:
                parts[0] = parts[0].rstrip('。！？.!?') + f"，{tech_text}。"
            else:
                parts[0] += f"，{tech_text}"
            result.technical_additions = content['technical_parts'][:2]
        
        # 🔧 修复：检查原始描述中是否已经包含角色一致性描述，避免重复添加
        if content['consistency_parts']:
            # 检查原始描述中是否已经包含角色描述（通过检查是否有"（"和"）"包围的描述）
            has_embedded_character_desc = "（" in content['original'] and "）" in content['original']

            if not has_embedded_character_desc:
                # 只有在没有嵌入角色描述时才添加一致性信息
                consistency_text = content['consistency_parts'][0] if content['consistency_parts'] else ""
                if consistency_text:
                    parts.append(f"（{consistency_text}）")
                    result.consistency_additions = content['consistency_parts'][:1]
            else:
                logger.debug("原始描述中已包含角色一致性描述，跳过重复添加")
        
        result.enhanced_description = "".join(parts)
        return result

    # _embed_character_descriptions方法已移动到SceneDescriptionEnhancer类中

    def _structured_fusion(self, content: Dict[str, Any]) -> FusionResult:
        """结构化融合策略"""
        result = FusionResult()
        parts = [content['original']]
        
        # 结构化添加技术规格
        if content['technical_parts']:
            tech_section = "\n技术规格：" + "，".join(content['technical_parts'])
            parts.append(tech_section)
            result.technical_additions = content['technical_parts']
        
        # 🔧 修复：结构化添加一致性要求，避免重复
        if content['consistency_parts']:
            has_embedded_character_desc = "（" in content['original'] and "）" in content['original']
            if not has_embedded_character_desc:
                consistency_section = "\n一致性要求：" + "，".join(content['consistency_parts'])
                parts.append(consistency_section)
                result.consistency_additions = content['consistency_parts']
            else:
                logger.debug("原始描述中已包含角色一致性描述，跳过结构化添加")
        
        result.enhanced_description = "".join(parts)
        return result
    
    def _minimal_fusion(self, content: Dict[str, Any]) -> FusionResult:
        """最小化融合策略"""
        result = FusionResult()
        parts = [content['original']]
        
        # 最小化添加关键信息
        additions = []
        if content['technical_parts']:
            additions.extend(content['technical_parts'][:1])  # 只取最重要的技术细节
            result.technical_additions = content['technical_parts'][:1]
        
        # 🔧 修复：最小化添加一致性信息，避免重复
        if content['consistency_parts']:
            has_embedded_character_desc = "（" in content['original'] and "）" in content['original']
            if not has_embedded_character_desc:
                additions.extend(content['consistency_parts'][:1])  # 只取最重要的一致性信息
                result.consistency_additions = content['consistency_parts'][:1]
            else:
                logger.debug("原始描述中已包含角色一致性描述，跳过最小化添加")
        
        if additions:
            parts.append(f" [{','.join(additions)}]")
        
        result.enhanced_description = "".join(parts)
        return result
    
    def _natural_fusion(self, content: Dict[str, Any]) -> FusionResult:
        """智能融合策略 - 根据内容特点自适应选择最佳融合方式"""
        result = FusionResult()
        
        # 🔧 新增：检查是否已经增强过，避免重复LLM调用
        original_desc = content.get('original_description', '')
        if self._is_already_enhanced(original_desc):
            logger.info("内容已经增强过，跳过LLM处理")
            # 直接返回原始描述
            result.enhanced_description = original_desc
            result.fusion_quality_score = 0.8  # 给已增强内容一个较高分数
            return result

        # 如果有LLM API可用，优先使用LLM进行智能融合
        if self.llm_api and self.llm_api.is_configured():
            try:
                return self._llm_enhanced_fusion(content)
            except Exception as e:
                logger.warning(f"LLM增强融合失败，回退到传统方法: {e}")
        
        # 分析原始描述特点
        original_length = content['original_length']
        tech_count = len(content['technical_parts'])
        consistency_count = len(content['consistency_parts'])
        
        # 根据内容长度和信息量选择策略
        if original_length < 20 and (tech_count + consistency_count) > 3:
            # 短描述 + 大量补充信息 -> 使用结构化
            return self._structured_fusion(content)
        elif original_length > 100:
            # 长描述 -> 使用最小化
            return self._minimal_fusion(content)
        else:
            # 中等长度 -> 使用自然融合
            return self._natural_fusion_impl(content)
    
    def _llm_enhanced_fusion(self, content: Dict[str, Any]) -> FusionResult:
        """使用LLM进行智能内容融合"""
        result = FusionResult()
        
        # 构建LLM提示词
        original_desc = content['original']
        technical_parts = content['technical_parts']
        consistency_parts = content['consistency_parts']
        detected_characters = content.get('detected_characters', [])
        detected_scenes = content.get('detected_scenes', [])
        
        logger.info("=== 场景增强器LLM辅助生成开始 ===")
        logger.info(f"原始场景描述: {original_desc[:100]}..." if len(original_desc) > 100 else f"原始场景描述: {original_desc}")
        logger.info(f"检测到的角色: {detected_characters if detected_characters else '无'}")
        logger.info(f"检测到的场景: {detected_scenes if detected_scenes else '无'}")
        
        # 🔧 修复：预处理原始描述，将角色一致性描述直接嵌入
        enhanced_original_desc = original_desc
        if self.character_scene_manager and detected_characters:
            # 简化的角色描述嵌入逻辑
            for character in detected_characters:
                character_desc = self._get_character_consistency_description(character)
                if character_desc and character in enhanced_original_desc:
                    # 在角色名称后添加一致性描述
                    enhanced_original_desc = enhanced_original_desc.replace(
                        character, f"{character}（{character_desc}）", 1
                    )
        logger.info(f"角色描述嵌入后: {enhanced_original_desc[:150]}..." if len(enhanced_original_desc) > 150 else f"角色描述嵌入后: {enhanced_original_desc}")
        
        # 🔧 修复：优先使用传入的风格参数，而不是从描述中检测
        detected_style = None
        original_style_prompt = ""

        # 1. 首先尝试从content中获取风格参数
        style = content.get('style', None)
        if style and self.style_manager:
            original_style_prompt = self.style_manager.style_prompts.get(style, "")
            if original_style_prompt:
                detected_style = style
                logger.info(f"使用传入的风格: {style}, 提示词: {original_style_prompt}")
            else:
                logger.warning(f"传入的风格 {style} 没有对应的提示词")

        # 2. 如果没有传入风格或风格无效，尝试从项目配置获取
        if not detected_style and self.style_manager:
            current_style = self._get_current_project_style()
            if current_style:
                original_style_prompt = self.style_manager.style_prompts.get(current_style, "")
                if original_style_prompt:
                    detected_style = current_style
                    logger.info(f"从项目配置获取风格: {current_style}, 提示词: {original_style_prompt}")

        # 3. 最后尝试从描述中检测风格
        if not detected_style and self.style_manager:
            detected_style, detected_prompt = self.style_manager.detect_style_from_description(enhanced_original_desc)
            if detected_style and detected_prompt:
                original_style_prompt = detected_prompt
                logger.info(f"从描述中检测到风格: {detected_style}, 提示词: {original_style_prompt}")

        # 4. 如果仍然没有风格，使用默认风格
        if not detected_style:
            logger.warning("未能获取有效风格，使用默认电影风格")
            detected_style = "电影风格"
            if self.style_manager:
                original_style_prompt = self.style_manager.style_prompts.get("电影风格", "")

        logger.info(f"最终使用风格: {detected_style}, 提示词: {original_style_prompt}")

        # 构建增强提示
        enhancement_prompt = f"""请对以下画面描述进行智能增强，要求：
1. 保持原始描述的核心内容和风格
2. 自然融入提供的技术细节
3. 确保描述流畅自然，避免生硬拼接
4. 控制总长度在150-200字之间（减少冗长描述）
5. 【重要】必须在涉及角色的描述中包含一致的服装描述，确保同一角色在不同场景中的服装保持一致性。
6. 【关键】如果原始描述中包含特定风格提示词（如"{original_style_prompt}"），必须在增强描述的结尾保持完全相同的风格提示词，不得修改、替换或省略。

原始描述：{enhanced_original_desc}

技术细节补充：{'; '.join(technical_parts) if technical_parts else '无'}

请输出增强后的画面描述（必须保持原始风格提示词不变）："""
        
        logger.info("正在调用LLM进行场景描述增强...")
        # 记录完整的提示词内容，不截断
        logger.debug(f"LLM增强提示词完整内容:\n{enhancement_prompt}")
        
        try:
            # 调用LLM进行增强
            if not self.llm_api:
                raise Exception("LLM API 未初始化")
            enhanced_text = self.llm_api.rewrite_text(enhancement_prompt)
            
            if enhanced_text and len(enhanced_text.strip()) > 0:
                enhanced_content = enhanced_text.strip()

                # 【关键】强制保持风格一致性 - 检查并修复风格提示词
                if original_style_prompt and self.style_manager:
                    enhanced_content = self.style_manager.ensure_style_consistency(enhanced_content, original_style_prompt)
                    logger.info(f"已强制保持风格一致性: {original_style_prompt}")

                logger.info(f"✓ LLM增强成功完成")
                logger.info(f"  - 原始描述长度: {len(original_desc)} 字符")
                logger.info(f"  - 增强后长度: {len(enhanced_content)} 字符")
                logger.info(f"  - 增强比例: {len(enhanced_content)/len(original_desc):.2f}x")
                logger.info(f"技术细节补充：{'; '.join(technical_parts) if technical_parts else '无'}")
                # 角色一致性信息已集成到增强描述中，无需单独显示
                logger.info(f"增强后场景描述: {enhanced_content[:200]}..." if len(enhanced_content) > 200 else f"增强后场景描述: {enhanced_content}")

                # 注意：文件保存已移至enhance_storyboard方法中统一处理

                result.enhanced_description = enhanced_content
                result.technical_additions = technical_parts
                result.consistency_additions = consistency_parts
                result.fusion_quality_score = 0.85  # LLM增强的质量评分较高
                
                logger.info("=== 场景增强器LLM辅助生成完成 ===")
                return result
            else:
                logger.warning("✗ LLM增强结果质量不佳，回退到自然融合")
                logger.info("=== 场景增强器LLM辅助生成失败，使用备选方案 ===")
                raise Exception("LLM返回空结果")
                
        except Exception as e:
            logger.error(f"✗ LLM增强融合失败: {e}")
            logger.info("=== 场景增强器LLM辅助生成异常，使用备选方案 ===")
            # 回退到自然融合
            return self._natural_fusion(content)
    
    def _postprocess_result(self, result: FusionResult) -> FusionResult:
        """后处理融合结果"""
        # 清理多余的标点符号
        result.enhanced_description = re.sub(r'[，。]{2,}', '，', result.enhanced_description)
        result.enhanced_description = re.sub(r'，+$', '。', result.enhanced_description)
        
        # 计算融合质量评分
        result.fusion_quality_score = self._calculate_quality_score(result)
        
        return result
    
    def _calculate_quality_score(self, result: FusionResult) -> float:
        """计算融合质量评分"""
        score = 0.0
        
        # 长度平衡评分
        length = len(result.enhanced_description)
        if 100 <= length <= 350:  # 理想长度范围
            length_score = 1.0
        elif length < 100:
            length_score = length / 100.0
        else:
            length_score = max(0.5, 400 / length)
        
        score += length_score * self.quality_rules['length_balance']
        
        # 信息密度评分
        info_count = len(result.technical_additions) + len(result.consistency_additions)
        density_score = min(1.0, info_count / 4.0)  # 最多4个补充信息为满分
        score += density_score * self.quality_rules['information_density']
        
        # 内容连贯性评分（简化版）
        coherence_score = 0.8  # 基础连贯性评分
        if '，，' in result.enhanced_description or '。。' in result.enhanced_description:
            coherence_score -= 0.2
        
        score += coherence_score * self.quality_rules['content_coherence']
        
        return min(1.0, score)

    def _get_character_consistency_description(self, character_name: str) -> str:
        """🔧 新增：获取角色一致性描述"""
        try:
            if not self.character_scene_manager:
                return ""

            # 从角色场景管理器获取角色描述
            characters_data = self.character_scene_manager.get_all_characters()
            for char_id, char_data in characters_data.items():
                if char_data.get('name') == character_name:
                    return char_data.get('consistency_prompt', '') or char_data.get('description', '')

            return ""
        except Exception as e:
            logger.error(f"获取角色一致性描述失败 {character_name}: {e}")
            return ""

    def _get_current_project_style(self) -> str:
        """从项目配置中获取当前风格

        Returns:
            str: 当前项目的风格设置
        """
        try:
            if not self.project_root:
                logger.warning("项目根目录未设置，使用默认风格")
                return "电影风格"

            import json
            import os
            project_json_path = os.path.join(self.project_root, "project.json")

            if not os.path.exists(project_json_path):
                logger.warning(f"项目配置文件不存在: {project_json_path}")
                return "电影风格"

            with open(project_json_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 🔧 修复：优先从五阶段分镜系统中获取风格
            current_style = None

            # 1. 首先尝试从五阶段分镜数据中获取
            if 'five_stage_storyboard' in project_data:
                five_stage_data = project_data['five_stage_storyboard']
                current_style = five_stage_data.get('selected_style')
                if current_style:
                    logger.info(f"从五阶段分镜系统获取当前风格: {current_style}")
                    return current_style

            # 2. 其次尝试从项目根级别获取
            current_style = project_data.get('selected_style') or project_data.get('style')
            if current_style:
                logger.info(f"从项目根级别获取当前风格: {current_style}")
                return current_style

            # 3. 最后使用默认风格
            logger.warning("未找到项目风格设置，使用默认风格")
            return "电影风格"

        except Exception as e:
            logger.error(f"获取项目风格失败: {e}")
            return "电影风格"


class SceneDescriptionEnhancer:
    """场景描述智能增强器 - 主类（第二阶段增强版）"""
    
    def __init__(self, project_root: str, character_scene_manager: Optional[CharacterSceneManager] = None, llm_api=None):
        self.project_root = project_root
        self.output_dir = project_root  # 添加 output_dir 属性

        # 初始化角色场景管理器
        if character_scene_manager:
            self.character_scene_manager = character_scene_manager
        else:
            self.character_scene_manager = CharacterSceneManager(project_root)

        # 初始化LLM API
        self.llm_api = llm_api

        # 🔧 修复：初始化风格一致性管理器
        from src.utils.style_consistency_manager import StyleConsistencyManager
        self.style_manager = StyleConsistencyManager(project_root) if project_root else None

        # 初始化组件
        self.technical_analyzer = TechnicalDetailsAnalyzer()
        self.consistency_injector = ConsistencyInjector(self.character_scene_manager, service_manager=None)
        self.content_fuser = ContentFuser(project_root=self.project_root, llm_api=llm_api, character_scene_manager=self.character_scene_manager)  # 传递LLM API和角色管理器给内容融合器
        self.color_optimizer = ColorOptimizer()  # 初始化颜色优化器
        
        # 配置选项
        self.config = {
            'enable_technical_details': True,
            'enable_consistency_injection': True,
            'enhancement_level': 'medium',  # low, medium, high
            'fusion_strategy': 'intelligent',  # natural, structured, minimal, intelligent
            'quality_threshold': 0.4,  # 🔧 修改：降低质量阈值，减少备用策略触发
            'enable_llm_enhancement': True  # 启用LLM增强
        }

        # 🔧 新增：增强缓存，避免重复处理
        self._enhancement_cache = {}

    def _is_already_enhanced(self, description: str) -> bool:
        """检查描述是否已经增强过"""
        try:
            # 检查是否包含角色一致性描述的特征
            if "（中国人，" in description and "岁" in description and ("战袍" in description or "军装" in description):
                return True

            # 检查是否包含风格提示词
            if "水彩画风，柔和笔触，粉彩色，插画，温柔" in description:
                return True

            # 检查缓存
            desc_hash = hash(description)
            return desc_hash in self._enhancement_cache

        except Exception as e:
            logger.debug(f"检查增强状态失败: {e}")
            return False
    
    def enhance_description(self, original_description: str, characters: Optional[List[str]] = None, style: Optional[str] = None) -> str:
        """增强画面描述（第二阶段增强版）

        Args:
            original_description: 原始画面描述
            characters: 相关角色列表
            style: 用户选择的风格（如电影风格、动漫风格等）

        Returns:
            str: 增强后的画面描述
        """
        try:
            # 🔧 新增：检查是否已经增强过（避免重复处理）
            if self._is_already_enhanced(original_description):
                logger.info("描述已经增强过，跳过重复处理")
                return original_description

            logger.info(f"开始增强画面描述: {original_description[:50]}...")

            # 🔧 修复：首先嵌入角色一致性描述
            enhanced_description_with_characters = original_description
            if characters:
                enhanced_description_with_characters = self._embed_character_descriptions(original_description, characters)
                logger.debug(f"角色一致性描述嵌入完成")

            # 1. 技术细节分析
            technical_details = None
            if self.config['enable_technical_details']:
                technical_details = self.technical_analyzer.analyze_description(enhanced_description_with_characters)
                logger.debug(f"技术细节分析完成: {technical_details.to_description()}")

            # 2. 一致性信息提取（使用嵌入角色描述后的文本）
            consistency_info = None
            if self.config['enable_consistency_injection']:
                try:
                    consistency_info = self.consistency_injector.extract_consistency_info(
                        enhanced_description_with_characters, characters
                    )
                    logger.debug(f"一致性信息提取完成: {consistency_info.to_description()}")
                except Exception as e:
                    logger.debug(f"一致性信息提取失败，跳过: {e}")
                    consistency_info = None

            # 2.5. 颜色一致性处理
            enhanced_description_with_colors = enhanced_description_with_characters
            if characters:
                enhanced_description_with_colors = self.color_optimizer.apply_color_consistency(
                    enhanced_description_with_characters, characters, self.character_scene_manager
                )
                logger.debug(f"颜色一致性处理完成")

            # 3. 智能内容融合（第二阶段核心功能）
            fusion_result = self.content_fuser.fuse_content(
                enhanced_description_with_colors,
                technical_details,
                consistency_info,
                self.config['fusion_strategy'],
                style  # 🔧 修复：传递风格参数
            )

            # 4. 质量控制
            if fusion_result.fusion_quality_score >= self.config['quality_threshold']:
                enhanced_description = fusion_result.enhanced_description
                logger.info(f"画面描述增强完成，质量评分: {fusion_result.fusion_quality_score:.2f}")
            else:
                # 质量不达标，使用备用策略
                logger.warning(f"融合质量不达标({fusion_result.fusion_quality_score:.2f})，使用备用策略")
                backup_result = self.content_fuser.fuse_content(
                    enhanced_description_with_colors, technical_details, consistency_info, 'natural'
                )
                enhanced_description = backup_result.enhanced_description

            return enhanced_description

        except Exception as e:
            logger.error(f"画面描述增强失败: {e}")
            return original_description

    def enhance_description_with_llm(self, original_description: str, characters: Optional[List[str]] = None) -> str:
        """🔧 新增：使用LLM进行真正的智能增强

        Args:
            original_description: 原始画面描述
            characters: 相关角色列表

        Returns:
            str: LLM增强后的画面描述
        """
        try:
            # 🔧 新增：检查是否已经增强过（避免重复处理）
            if self._is_already_enhanced(original_description):
                logger.info("描述已经增强过，跳过LLM重复处理")
                return original_description

            logger.info(f"开始LLM智能增强画面描述: {original_description[:50]}...")

            # 检查LLM API是否可用
            if not self.llm_api or not self.llm_api.is_configured():
                logger.warning("LLM API未配置，回退到普通增强")
                return self.enhance_description(original_description, characters)

            # 1. 技术细节分析
            technical_details = None
            if self.config['enable_technical_details']:
                technical_details = self.technical_analyzer.analyze_description(original_description)
                logger.debug(f"技术细节分析完成: {technical_details.to_description()}")

            # 2. 一致性信息提取
            consistency_info = None
            if self.config['enable_consistency_injection']:
                consistency_info = self.consistency_injector.extract_consistency_info(
                    original_description, characters
                )
                logger.debug(f"一致性信息提取完成: {consistency_info.to_description()}")

            # 3. 强制使用LLM增强融合
            fusion_result = self.content_fuser.fuse_content(
                original_description,
                technical_details,
                consistency_info,
                'intelligent'  # 强制使用intelligent策略触发LLM增强
            )

            logger.info(f"LLM智能增强完成，质量评分: {fusion_result.fusion_quality_score:.2f}")
            return fusion_result.enhanced_description

        except Exception as e:
            logger.error(f"LLM智能增强失败: {e}")
            # 回退到普通增强
            return self.enhance_description(original_description, characters)
    
    def enhance_description_with_details(self, original_description: str, characters: Optional[List[str]] = None) -> Dict[str, Any]:
        """增强画面描述并返回详细信息
        
        Args:
            original_description: 原始画面描述
            characters: 相关角色列表
            
        Returns:
            Dict: 包含增强结果和详细信息的字典
        """
        try:
            logger.info(f"开始详细增强画面描述: {original_description[:50]}...")
            
            # 1. 技术细节分析
            technical_details = None
            if self.config['enable_technical_details']:
                technical_details = self.technical_analyzer.analyze_description(original_description)
            
            # 2. 一致性信息提取
            consistency_info = None
            if self.config['enable_consistency_injection']:
                consistency_info = self.consistency_injector.extract_consistency_info(
                    original_description, characters
                )
            
            # 3. 智能内容融合
            fusion_result = self.content_fuser.fuse_content(
                original_description, 
                technical_details, 
                consistency_info, 
                self.config['fusion_strategy']
            )
            
            # 4. 组装详细结果
            result = {
                'original_description': original_description,
                'enhanced_description': fusion_result.enhanced_description,
                'technical_details': technical_details.to_description() if technical_details else "",
                'consistency_info': consistency_info.to_description() if consistency_info else "",
                'technical_additions': fusion_result.technical_additions,
                'consistency_additions': fusion_result.consistency_additions,
                'fusion_quality_score': fusion_result.fusion_quality_score,
                'fusion_strategy': self.config['fusion_strategy'],
                'enhancement_config': self.config.copy()
            }
            
            logger.info(f"详细增强完成，质量评分: {fusion_result.fusion_quality_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"详细增强失败: {e}")
            return {
                'original_description': original_description,
                'enhanced_description': original_description,
                'error': str(e)
            }
    
    def _fuse_content(self, original: str, technical: TechnicalDetails, consistency: ConsistencyInfo) -> str:
        """融合原始描述、技术细节和一致性信息"""
        parts = [original]
        
        # 添加技术细节
        if technical and self.config['enable_technical_details']:
            tech_desc = technical.to_description()
            if tech_desc:
                if self.config['fusion_strategy'] == 'natural':
                    parts.append(f"（{tech_desc}）")
                elif self.config['fusion_strategy'] == 'structured':
                    parts.append(f"\n技术规格：{tech_desc}")
                else:  # minimal
                    parts.append(f" [{tech_desc}]")
        
        # 添加一致性信息
        if consistency and self.config['enable_consistency_injection']:
            consistency_desc = consistency.to_description()
            if consistency_desc:
                if self.config['fusion_strategy'] == 'natural':
                    parts.append(f"（{consistency_desc}）")
                elif self.config['fusion_strategy'] == 'structured':
                    parts.append(f"\n一致性要求：{consistency_desc}")
                else:  # minimal
                    parts.append(f" [{consistency_desc}]")
        
        return "".join(parts)
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                logger.info(f"配置已更新: {key} = {value}")
    
    def reload_config(self):
        """重新加载配置"""
        try:
            # 重新初始化配置
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            
            # 获取增强器配置
            enhancer_config = config_manager.get_setting("scene_enhancer", {})

            # 更新配置对象
            if enhancer_config:
                for key, value in enhancer_config.items():
                    if key in self.config:
                        self.config[key] = value
            
            # 重新初始化内容融合器
            if hasattr(self, 'content_fuser'):
                self.content_fuser = ContentFuser(project_root=self.project_root, character_scene_manager=self.character_scene_manager)
            
            logger.info("场景描述增强器配置已重新加载")
            
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            raise
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self.config.copy()
    
    def _load_scene_mapping_from_project(self) -> Optional[List[Dict[str, Any]]]:
        """从project.json中加载场景映射信息
        
        Returns:
            List[Dict]: 包含场景映射信息的列表，每个元素包含scene_name和scene_index
        """
        try:
            # 获取当前项目的输出目录
            if hasattr(self, 'output_dir') and self.output_dir:
                project_file = os.path.join(self.output_dir, 'project.json')
            else:
                # 尝试从当前工作目录查找
                project_file = None
                current_dir = os.getcwd()
                for root, _, files in os.walk(current_dir):
                    if 'project.json' in files:
                        project_file = os.path.join(root, 'project.json')
                        break
            
            if not project_file or not os.path.exists(project_file):
                logger.warning("未找到project.json文件，将使用默认场景分组")
                return None
            
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # 从five_stage_storyboard.stage_data.4.storyboard_results中提取场景映射
            scene_mapping = []
            if ('five_stage_storyboard' in project_data and 
                'stage_data' in project_data['five_stage_storyboard'] and
                '4' in project_data['five_stage_storyboard']['stage_data'] and
                'storyboard_results' in project_data['five_stage_storyboard']['stage_data']['4']):
                storyboard_results = project_data['five_stage_storyboard']['stage_data']['4']['storyboard_results']
                for scene_data in storyboard_results:
                    scene_index = scene_data.get('scene_index', 0)
                    scene_info = scene_data.get('scene_info', '')
                    scene_name = scene_info if isinstance(scene_info, str) else f'## 场景{scene_index + 1}'
                    
                    # 从storyboard_script中计算镜头数量
                    storyboard_script = scene_data.get('storyboard_script', '')
                    shot_count = storyboard_script.count('### 镜头') if storyboard_script else 1
                    
                    # 为该场景的每个镜头创建映射
                    for shot_idx in range(shot_count):
                        scene_mapping.append({
                            'scene_name': scene_name,
                            'scene_index': scene_index,
                            'scene_description': scene_info
                        })
            
            logger.info(f"从project.json加载了{len(scene_mapping)}个镜头的场景映射信息")
            return scene_mapping
            
        except Exception as e:
            logger.error(f"加载project.json场景映射失败: {e}")
            return None
    
    def enhance_storyboard(self, storyboard_script: str, style: Optional[str] = None) -> Dict[str, Any]:
        """增强整个分镜脚本中的画面描述

        Args:
            storyboard_script: 完整的分镜脚本内容
            style: 用户选择的风格（如电影风格、动漫风格等）

        Returns:
            Dict: 包含增强结果和详细信息的字典
        """
        try:
            # 安全处理storyboard_script，确保它是字符串
            if not isinstance(storyboard_script, str):
                logger.error(f"storyboard_script应该是字符串，但得到: {type(storyboard_script)}")
                if isinstance(storyboard_script, dict):
                    # 如果是字典，尝试获取脚本内容
                    storyboard_script = storyboard_script.get('storyboard_script', '') or storyboard_script.get('content', '') or str(storyboard_script)
                else:
                    storyboard_script = str(storyboard_script) if storyboard_script else ""

            logger.info(f"开始增强分镜脚本，原始长度: {len(storyboard_script)}")

            # 尝试从project.json中读取场景信息
            scene_mapping = self._load_scene_mapping_from_project()

            # 解析分镜脚本，提取画面描述和技术细节
            enhanced_descriptions = []
            current_shot_info = {}

            lines = storyboard_script.split('\n')
            current_scene = None
            shot_counter = 0  # 用于映射到project.json中的场景
            global_shot_counter = 1  # 🔧 修复：全局镜头计数器，确保镜头编号唯一

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 检测场景标题 - 保留场景标题到输出结果中
                # 但不包括'## 场景分镜脚本'，这只是格式标记
                if ((line.startswith('# 场景') or 
                    (line.startswith('## 场景') and '分镜脚本' not in line) or 
                    line.startswith('### 场景') or 
                    (line.startswith('场景') and not line.startswith('场景分镜脚本')))):
                    current_scene = line
                    logger.info(f"[enhance_storyboard] 检测到场景标题: '{current_scene}'")
                    # 将场景标题添加到输出结果中
                    enhanced_descriptions.append({
                        'type': 'scene_title',
                        'content': line,
                        'scene': current_scene,
                        'enhanced': line,  # 场景标题不需要增强，直接使用原内容
                        'original': line
                    })
                    continue  # 继续处理下一行
                
                # 检测镜头开始
                if line.startswith('### 镜头') or line.startswith('## 镜头'):
                    # 如果有之前的镜头信息，处理它
                    if current_shot_info.get('画面描述'):
                        # 从project.json映射中获取场景信息，如果没有则使用检测到的场景
                        if scene_mapping and shot_counter < len(scene_mapping):
                            current_shot_info['scene'] = scene_mapping[shot_counter]['scene_name']
                            current_shot_info['scene_index'] = scene_mapping[shot_counter]['scene_index']
                            logger.info(f"[enhance_storyboard] 从project.json为镜头 {current_shot_info.get('镜头编号', 'Unknown')} 分配场景: '{scene_mapping[shot_counter]['scene_name']}'")
                        else:
                            current_shot_info['scene'] = current_scene or "未知场景"
                            logger.info(f"[enhance_storyboard] 为镜头 {current_shot_info.get('镜头编号', 'Unknown')} 添加场景信息: '{current_scene or '未知场景'}'")

                        # 🔧 修复：使用全局镜头编号，确保唯一性
                        original_shot_number = current_shot_info.get('镜头编号', '')
                        global_shot_number = f"### 镜头{global_shot_counter}"
                        current_shot_info['镜头编号'] = global_shot_number
                        logger.info(f"[enhance_storyboard] 将镜头编号从 '{original_shot_number}' 更新为 '{global_shot_number}'")

                        enhanced_desc = self._enhance_shot_description(current_shot_info, style)
                        enhanced_descriptions.append(enhanced_desc)
                        shot_counter += 1
                        global_shot_counter += 1

                    # 重置当前镜头信息
                    current_shot_info = {'镜头编号': line}
                    continue
                
                # 提取技术细节和画面描述
                if '**' in line and ('：' in line or ':' in line):
                    # 提取字段名和值
                    if '：' in line:
                        field_part, value_part = line.split('：', 1)
                    else:
                        field_part, value_part = line.split(':', 1)
                    
                    # 清理字段名
                    field_name = field_part.replace('**', '').replace('-', '').strip()
                    value = value_part.strip()
                    
                    # 存储信息
                    current_shot_info[field_name] = value
            
            # 处理最后一个镜头
            if current_shot_info.get('画面描述'):
                # 从project.json映射中获取场景信息，如果没有则使用检测到的场景
                if scene_mapping and shot_counter < len(scene_mapping):
                    current_shot_info['scene'] = scene_mapping[shot_counter]['scene_name']
                    current_shot_info['scene_index'] = scene_mapping[shot_counter]['scene_index']
                    logger.info(f"[enhance_storyboard] 从project.json为最后一个镜头 {current_shot_info.get('镜头编号', 'Unknown')} 分配场景: '{scene_mapping[shot_counter]['scene_name']}'")
                else:
                    current_shot_info['scene'] = current_scene or "未知场景"
                    logger.info(f"[enhance_storyboard] 为最后一个镜头 {current_shot_info.get('镜头编号', 'Unknown')} 添加场景信息: '{current_scene or '未知场景'}'")

                # 🔧 修复：使用全局镜头编号，确保唯一性
                original_shot_number = current_shot_info.get('镜头编号', '')
                global_shot_number = f"### 镜头{global_shot_counter}"
                current_shot_info['镜头编号'] = global_shot_number
                logger.info(f"[enhance_storyboard] 将最后一个镜头编号从 '{original_shot_number}' 更新为 '{global_shot_number}'")

                enhanced_desc = self._enhance_shot_description(current_shot_info, style)
                enhanced_descriptions.append(enhanced_desc)
            
            # 组合所有增强后的画面描述
            enhanced_content = '\n\n'.join([desc['enhanced'] for desc in enhanced_descriptions])
            
            # 计算质量评分
            quality_score = min(1.0, len(enhanced_descriptions) * 0.2) if enhanced_descriptions else 0.5
            
            result = {
                'enhanced_description': enhanced_content,
                'original_description': storyboard_script,
                'enhanced_count': len(enhanced_descriptions),
                'enhanced_details': enhanced_descriptions,
                'fusion_quality_score': quality_score,
                'config': self.config.copy(),
                'technical_details': {},
                'consistency_details': {}
            }
            
            # 保存增强结果到project.json文件
            self._save_enhanced_descriptions_to_project(enhanced_descriptions)
            logger.info("✓ 增强结果已保存到project.json文件")

            # 🔧 修改：移除单次场景增强时的一致性描述保存，改为在所有场景完成后统一处理
            
            logger.info(f"分镜脚本增强完成，增强了{len(enhanced_descriptions)}个画面描述")
            return result
            
        except Exception as e:
            logger.error(f"分镜脚本增强失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return {
                'enhanced_description': storyboard_script,
                'original_description': storyboard_script,
                'error': str(e),
                'fusion_quality_score': 0.0
            }
    
    def _enhance_shot_description(self, shot_info: Dict[str, str], style: Optional[str] = None) -> Dict[str, Any]:
        """增强单个镜头的画面描述

        Args:
            shot_info: 包含镜头信息的字典
            style: 用户选择的风格（如电影风格、动漫风格等）

        Returns:
            Dict: 包含原始和增强描述的字典
        """
        try:
            original_desc = shot_info.get('画面描述', '')
            if not original_desc:
                return {'original': '', 'enhanced': ''}

            # 🔧 修复：从项目配置中获取当前风格，而不是使用硬编码
            current_style = self._get_current_project_style()
            if style:
                # 如果传入了风格参数，使用传入的风格
                current_style = style
                logger.info(f"使用传入的风格参数: {style}")
            else:
                logger.info(f"从项目配置获取风格: {current_style}")

            # 🔧 修复：使用风格一致性管理器获取风格提示词，而不是硬编码
            style_prompt = ""
            if current_style and self.style_manager:
                style_prompt = self.style_manager.style_prompts.get(current_style, "")
                if style_prompt:
                    logger.info(f"为镜头描述添加{current_style}风格提示词: {style_prompt}")

            # 🔧 修复：不在这里添加风格提示词，保持原始描述的纯净性
            # 风格提示词应该在图像生成时添加，而不是在描述存储时添加
            enhanced_desc = original_desc
            
            # 提取技术细节
            technical_details = TechnicalDetails(
                shot_type=shot_info.get('镜头类型', ''),
                camera_angle=shot_info.get('机位角度', ''),
                camera_movement=shot_info.get('镜头运动', ''),
                depth_of_field=shot_info.get('景深效果', ''),
                lighting=shot_info.get('光影设计', ''),
                composition=shot_info.get('构图要点', ''),
                color_tone=shot_info.get('色彩基调', '')
            )
            
            # 提取角色信息（从画面描述中识别）
            characters = self._extract_characters_from_description(original_desc)
            
            # 嵌入角色一致性描述
            enhanced_original_desc = self._embed_character_descriptions(original_desc, characters)
            
            # 获取一致性信息
            consistency_info = None
            if self.config['enable_consistency_injection']:
                consistency_info = self.consistency_injector.extract_consistency_info(
                    enhanced_original_desc, characters
                )
            
            # 智能融合内容
            fusion_result = self.content_fuser.fuse_content(
                enhanced_desc,  # 使用带有风格提示词的描述
                technical_details,
                consistency_info,
                self.config['fusion_strategy'],
                style  # 🔧 新增：传递风格参数
            )
            
            return {
                'original': original_desc,  # 🔧 修复：返回纯净的原始描述，不包含风格提示词
                'enhanced': fusion_result.enhanced_description,
                'technical_details': technical_details.to_description(),
                'consistency_info': consistency_info.to_description() if consistency_info else '',
                'characters': characters,
                'fusion_quality_score': fusion_result.fusion_quality_score,
                'shot_info': shot_info,  # 保存原始的shot_info用于重建original_description
                '镜头编号': shot_info.get('镜头编号', '### 镜头1'),  # 确保镜头编号被传递
                'current_style': current_style,  # 🔧 新增：保存当前风格信息
                'style_prompt': style_prompt  # 🔧 新增：保存风格提示词（但不嵌入到描述中）
            }
            
        except Exception as e:
            logger.error(f"增强镜头描述失败: {e}")
            # 🔧 修复：即使出错也返回纯净的原始描述
            original_desc = shot_info.get('画面描述', '')
            current_style = self._get_current_project_style()
            if style:
                current_style = style

            return {
                'original': original_desc,  # 🔧 修复：返回纯净的原始描述
                'enhanced': original_desc,  # 出错时使用原始描述作为增强结果
                'error': str(e),
                'shot_info': shot_info,  # 即使出错也保存原始信息
                '镜头编号': shot_info.get('镜头编号', '### 镜头1'),  # 确保镜头编号被传递
                'current_style': current_style,  # 保存当前风格信息
                'style_prompt': ""  # 出错时风格提示词为空
            }
    
    def _extract_characters_from_description(self, description: str) -> List[str]:
        """智能角色提取方法

        Args:
            description: 画面描述文本

        Returns:
            List[str]: 识别出的角色列表
        """
        characters = []

        # 首先尝试简单的关键词匹配
        characters.extend(self._extract_simple_characters(description))

        # 如果没有找到，再使用复杂的智能识别
        if not characters:
            # 第一层：智能复合角色名称识别
            characters.extend(self._extract_compound_characters(description))

            # 第二层：语义角色关系识别
            characters.extend(self._extract_semantic_characters(description))

            # 第三层：传统关键词匹配
            characters.extend(self._extract_keyword_characters(description))

        # 去重并保持顺序
        unique_characters = []
        seen = set()
        for char in characters:
            if char and char not in seen:
                unique_characters.append(char)
                seen.add(char)

        logger.debug(f"智能角色提取结果: {unique_characters}")
        return unique_characters

    def _extract_simple_characters(self, description: str) -> List[str]:
        """简单的角色关键词匹配

        Args:
            description: 画面描述文本

        Returns:
            List[str]: 识别出的角色列表
        """
        characters = []

        # 🔧 修复：优先使用精确的项目角色数据匹配
        try:
            if hasattr(self, 'character_scene_manager') and self.character_scene_manager:
                project_characters = self.character_scene_manager.get_all_characters()

                # 按角色名称长度排序，优先匹配长名称（避免"赵"匹配到"赵括"的问题）
                sorted_characters = sorted(project_characters.items(),
                                         key=lambda x: len(x[1].get('name', '')), reverse=True)

                for char_id, char_data in sorted_characters:
                    char_name = char_data.get('name', '')
                    if char_name and char_name in description and char_name not in characters:
                        characters.append(char_name)
                        logger.info(f"从项目数据中识别到角色: {char_name}")

                    # 检查角色别名
                    aliases = char_data.get('aliases', [])
                    if aliases:
                        for alias in aliases:
                            if alias and alias in description and char_name not in characters:
                                characters.append(char_name)  # 使用主名称而不是别名
                                logger.info(f"通过别名'{alias}'识别到角色: {char_name}")
                                break

        except Exception as e:
            logger.warning(f"从项目数据匹配角色失败: {e}")

        # 🔧 修复：如果已经从项目数据中找到角色，直接返回，不再进行其他匹配
        if characters:
            return characters

        # 通用角色关键词列表（适用于各种文学作品）
        simple_character_keywords = [
            # 核心角色类型
            '主要角色', '主角', '主人公', '男主', '女主', '反派', '配角', '龙套',

            # 现代职业（现代题材）
            '科学家', '医生', '护士', '老师', '学生', '警察', '律师', '记者', '作家',
            '画家', '歌手', '演员', '导演', '厨师', '司机', '工人', '农民', '商人',
            '老板', '经理', '秘书', '程序员', '设计师', '工程师', '建筑师',

            # 历史古代职业（历史题材）
            '皇帝', '皇后', '太子', '公主', '大臣', '将军', '丞相', '太尉', '元帅',
            '推荐者', '使者', '谋士', '武将', '文官', '侍卫', '宫女', '太监',
            '书生', '商贾', '农夫', '工匠', '猎户', '渔夫', '樵夫',

            # 科幻奇幻角色（科幻奇幻题材）
            '机器人', 'AI', '人工智能', '外星人', '异族', '精灵', '矮人', '兽人',
            '龙族', '天使', '恶魔', '法师', '战士', '盗贼', '牧师', '骑士',
            '巫师', '术士', '德鲁伊', '游侠', '刺客', '圣骑士', '死灵法师',

            # 军事科幻（军事科幻题材）
            '舰长', '指挥官', '飞行员', '特工', '间谍', '探员', '士官', '列兵',
            '中尉', '上尉', '少校', '中校', '上校', '将军', '元帅',

            # 家庭关系（通用）
            '父亲', '母亲', '爸爸', '妈妈', '儿子', '女儿', '哥哥', '姐姐', '弟弟', '妹妹',
            '爷爷', '奶奶', '外公', '外婆', '叔叔', '阿姨', '舅舅', '姑姑',
            '丈夫', '妻子', '男友', '女友', '恋人', '伴侣',

            # 社会关系（通用）
            '朋友', '同事', '同学', '邻居', '陌生人', '路人', '客人', '访客',
            '敌人', '对手', '竞争者', '盟友', '伙伴', '队友',

            # 年龄性别描述（通用）
            '男子', '女子', '男人', '女人', '男孩', '女孩', '孩子', '小孩',
            '老人', '年轻人', '中年人', '青年', '少年', '少女', '青少年',
            '婴儿', '幼儿', '儿童', '成年人', '老年人'
        ]

        # 按长度降序排序，优先匹配更长的词汇
        simple_character_keywords.sort(key=len, reverse=True)

        for keyword in simple_character_keywords:
            if keyword in description:
                characters.append(keyword)

        # 使用正则表达式匹配可能的人名和角色
        import re
        # 通用的角色识别模式（适用于各种文学作品）
        name_patterns = [
            # 中文人名模式（2-4个汉字）
            r'([\u4e00-\u9fa5]{2,4}(?=[的|，|。|！|？|：|；|、|说|道|想|看|听|走|跑|站|坐|笑|哭|叫|喊]))',

            # 历史人物和古代称谓（历史题材）
            r'([廉颇|赵王|赵括|推荐者|秦王|白起|王翦|李牧|蒙恬])',
            r'([赵|秦|楚|齐|燕|韩|魏|吴|蜀|魏][王|侯|公|君|帝])',
            r'([\u4e00-\u9fa5]{2,3}[将军|大夫|丞相|太尉|司马|都尉|元帅|统领])',

            # 现代人名和称谓（现代题材）
            r'([张|李|王|刘|陈|杨|黄|赵|周|吴|徐|孙|胡|朱|高|林|何|郭|马|罗|梁|宋|郑|谢|韩|唐|冯|于|董|萧|程|曹|袁|邓|许|傅|沈|曾|彭|吕|苏|卢|蒋|蔡|贾|丁|魏|薛|叶|阎|余|潘|杜|戴|夏|钟|汪|田|任|姜|范|方|石|姚|谭|廖|邹|熊|金|陆|郝|孔|白|崔|康|毛|邱|秦|江|史|顾|侯|邵|孟|龙|万|段|漕|钱|汤|尹|黎|易|常|武|乔|贺|赖|龚|文][\u4e00-\u9fa5]{1,2})',

            # 科幻/奇幻角色（科幻奇幻题材）
            r'([机器人|AI|人工智能|外星人|异族|精灵|矮人|兽人|龙族|天使|恶魔|法师|战士|盗贼|牧师|骑士][\u4e00-\u9fa5]*)',
            r'([\u4e00-\u9fa5]*[博士|教授|队长|指挥官|舰长|飞行员|特工|间谍|探员])',

            # 职业和身份（通用）
            r'([医生|护士|老师|学生|警察|律师|记者|作家|画家|歌手|演员|导演|厨师|司机|工人|农民|商人|老板|经理|秘书][\u4e00-\u9fa5]*)',

            # 家庭关系（通用）
            r'([父亲|母亲|爸爸|妈妈|儿子|女儿|哥哥|姐姐|弟弟|妹妹|爷爷|奶奶|外公|外婆|叔叔|阿姨|舅舅|姑姑|丈夫|妻子|男友|女友])',
        ]

        for pattern in name_patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                if match and match not in characters:
                    characters.append(match)
                    logger.debug(f"通过正则匹配识别到角色: {match}")

        return characters

    def _extract_compound_characters(self, description: str) -> list:
        """
        提取复合角色名称（如：李静妈妈、张三师傅、小明的猫等）
        支持被括号或其他内容分隔的情况
        
        Args:
            description: 画面描述文本
            
        Returns:
            list: 提取到的复合角色名称列表
        """
        import re
        characters = []
        
        # 扩展的角色后缀词库
        role_suffixes = [
            # 家庭关系
            '妈妈', '爸爸', '母亲', '父亲', '爷爷', '奶奶', '外公', '外婆',
            '儿子', '女儿', '哥哥', '姐姐', '弟弟', '妹妹', '丈夫', '妻子',
            # 职业身份
            '老师', '医生', '护士', '警察', '司机', '老板', '经理', '秘书',
            '服务员', '店主', '厨师', '律师', '法官', '记者', '演员', '歌手',
            '教授', '学生', '军人', '士兵', '工人', '农民', '商人', '助理',
            # 师徒关系
            '师傅', '师父', '师兄', '师姐', '师弟', '师妹', '徒弟', '学徒',
            # 社会关系
            '朋友', '同事', '同学', '邻居', '室友', '伙伴', '搭档', '助手',
            # 特殊关系
            '保镖', '司机', '秘书', '管家', '保姆', '护工', '向导', '翻译',
            # 动物/宠物
            '的猫', '的狗', '的鸟', '的马', '的鱼', '的兔子', '的仓鼠',
            # 称谓
            '大叔', '大爷', '大妈', '阿姨', '叔叔', '婶婶', '舅舅', '姑姑'
        ]
        
        # 构建动态正则表达式
        suffix_pattern = '|'.join(re.escape(suffix) for suffix in role_suffixes)
        
        # 匹配模式：人名+角色后缀（支持被分隔的情况）
        patterns = [
            # 直接连接：李静妈妈
            rf'([\u4e00-\u9fa5]{{2,4}})({suffix_pattern})',
            # 带"的"：李静的猫
            rf'([\u4e00-\u9fa5]{{2,4}})的({suffix_pattern.replace("的", "")})',
            # 空格分隔：李静 妈妈
            rf'([\u4e00-\u9fa5]{{2,4}})\s+({suffix_pattern})',
            # 被括号内容分隔：李静（...）妈妈
            rf'([\u4e00-\u9fa5]{{2,4}})（[^）]*）({suffix_pattern})',
            # 被其他标点分隔：李静，妈妈 / 李静。妈妈
            rf'([\u4e00-\u9fa5]{{2,4}})[，。、；：！？]\s*({suffix_pattern})',
            # 被描述性内容分隔（更宽泛的匹配）：李静...妈妈
            rf'([\u4e00-\u9fa5]{{2,4}})[^\u4e00-\u9fa5]*?({suffix_pattern})(?=[，。！？；：、\s]|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                if len(match) == 2:  # 确保匹配到两个部分
                    name_part, role_part = match
                    
                    # 验证是否是有效的角色组合
                    if self._is_valid_character_combination(name_part, role_part, description):
                        # 重构完整角色名称
                        if '的' in pattern and not role_part.startswith('的'):
                            full_name = f"{name_part}的{role_part}"
                        else:
                            full_name = f"{name_part}{role_part}"
                        
                        if len(full_name) >= 3:  # 至少3个字符的复合名称
                            characters.append(full_name)
                            logger.debug(f"识别到复合角色: {full_name} (来源: {name_part} + {role_part})")
        
        return characters
    
    def _is_valid_character_combination(self, name_part: str, role_part: str, description: str) -> bool:
        """
        验证人名和角色部分的组合是否有效
        
        Args:
            name_part: 人名部分
            role_part: 角色部分
            description: 原始描述
            
        Returns:
            bool: 是否是有效的角色组合
        """
        # 排除明显不是人名的词汇
        invalid_names = [
            '一个', '这个', '那个', '某个', '每个', '所有', '全部',
            '年轻', '中年', '老年', '小小', '大大', '高高', '矮矮',
            '美丽', '漂亮', '英俊', '帅气', '可爱', '温柔', '善良'
        ]
        
        if name_part in invalid_names:
            return False
        
        # 检查上下文，确保这确实是一个角色关系
        # 例如："李静（描述）妈妈" 中，妈妈应该是在描述李静的妈妈
        context_indicators = [
            f"{name_part}.*{role_part}",  # 基本匹配
            f"{role_part}.*{name_part}",  # 反向匹配
        ]
        
        import re
        for indicator in context_indicators:
            if re.search(indicator, description):
                return True
        
        return True  # 默认认为有效
    
    def _extract_semantic_characters(self, description: str) -> list:
        """
        基于语义的角色识别（识别上下文中的角色关系）
        
        Args:
            description: 画面描述文本
            
        Returns:
            list: 提取到的语义角色列表
        """
        import re
        characters = []
        
        # 语义模式：动作+角色关系
        semantic_patterns = [
            # 所有格模式：XX的YY
            r'([\u4e00-\u9fa5]{2,4})的([\u4e00-\u9fa5]{2,4})',
            # 称呼模式：叫XX、名叫XX
            r'(?:叫|名叫|称为)([\u4e00-\u9fa5]{2,4})',
            # 介绍模式：这是XX、那是XX
            r'(?:这是|那是|就是)([\u4e00-\u9fa5]{2,4})',
            # 动作主语模式：XX做了什么
            r'([\u4e00-\u9fa5]{2,4})(?:正在|在|开始|继续|停止)([\u4e00-\u9fa5]+)',
        ]
        
        # 角色指示词
        role_indicators = [
            '人', '者', '员', '师', '生', '手', '工', '家', '长', '主', '客', '友'
        ]
        
        for pattern in semantic_patterns:
            matches = re.findall(pattern, description)
            for match in matches:
                if isinstance(match, tuple):
                    # 处理元组匹配
                    for part in match:
                        if self._is_likely_character_name(part, role_indicators):
                            characters.append(part)
                else:
                    # 处理单个匹配
                    if self._is_likely_character_name(match, role_indicators):
                        characters.append(match)
        
        return characters
    
    def _is_likely_character_name(self, text: str, role_indicators: list) -> bool:
        """
        判断文本是否可能是角色名称
        
        Args:
            text: 待判断的文本
            role_indicators: 角色指示词列表
            
        Returns:
            bool: 是否可能是角色名称
        """
        if not text or len(text) < 2:
            return False
        
        # 排除明显不是角色的词汇
        non_character_words = [
            '时候', '地方', '东西', '事情', '问题', '方法', '办法', '样子',
            '颜色', '声音', '味道', '感觉', '心情', '想法', '意思', '内容'
        ]
        
        if text in non_character_words:
            return False
        
        # 检查是否包含角色指示词
        for indicator in role_indicators:
            if text.endswith(indicator):
                return True
        
        # 检查是否是常见人名模式
        import re
        if re.match(r'^[\u4e00-\u9fa5]{2,4}$', text):
            return True
        
        return False
    
    def _extract_keyword_characters(self, description: str) -> list:
        """
        传统关键词匹配角色提取
        
        Args:
            description: 画面描述文本
            
        Returns:
            list: 提取到的角色列表
        """
        characters = []
        
        # 扩展的角色关键词库
        character_keywords = [
            # 主要角色
            '主人公', '主角', '男主', '女主', '主人翁',
            # 基本人物类型
            '男子', '女子', '男人', '女人', '男孩', '女孩', '孩子', '小孩',
            '老人', '老者', '长者', '年轻人', '青年', '中年人',
            # 家庭关系
            '父亲', '母亲', '爸爸', '妈妈', '爷爷', '奶奶', '外公', '外婆',
            '儿子', '女儿', '哥哥', '姐姐', '弟弟', '妹妹', '丈夫', '妻子',
            # 职业身份
            '医生', '护士', '老师', '教授', '学生', '警察', '军人', '士兵',
            '司机', '工人', '农民', '商人', '老板', '经理', '秘书', '助理',
            '服务员', '店主', '店员', '收银员', '保安', '门卫', '清洁工',
            '厨师', '律师', '法官', '记者', '演员', '歌手', '画家', '作家',
            # 特征描述
            '光头大叔', '大叔', '大爷', '大妈', '阿姨', '叔叔', '婶婶',
            '帅哥', '美女', '胖子', '瘦子', '高个子', '矮个子',
            # 群体角色
            '路人', '行人', '乘客', '顾客', '客人', '观众', '群众', '民众',
            '同事', '朋友', '同学', '邻居', '陌生人'
        ]
        
        for keyword in character_keywords:
            if keyword in description:
                # 使用角色名称标准化
                normalized_name = CharacterDetectionConfig.normalize_character_name(keyword)
                characters.append(normalized_name)
        
        return characters

    def _get_current_project_style(self) -> str:
        """从项目配置中获取当前风格

        Returns:
            str: 当前项目的风格设置
        """
        try:
            if not self.project_root:
                logger.warning("项目根目录未设置，使用默认风格")
                return "电影风格"

            import json
            import os
            project_json_path = os.path.join(self.project_root, "project.json")

            if not os.path.exists(project_json_path):
                logger.warning(f"项目配置文件不存在: {project_json_path}")
                return "电影风格"

            with open(project_json_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 🔧 修复：优先从五阶段分镜系统中获取风格
            current_style = None

            # 1. 首先尝试从五阶段分镜数据中获取
            if 'five_stage_storyboard' in project_data:
                five_stage_data = project_data['five_stage_storyboard']
                current_style = five_stage_data.get('selected_style')
                if current_style:
                    logger.info(f"从五阶段分镜系统获取当前风格: {current_style}")
                    return current_style

            # 2. 其次尝试从项目根级别获取
            current_style = project_data.get('selected_style') or project_data.get('style')
            if current_style:
                logger.info(f"从项目根级别获取当前风格: {current_style}")
                return current_style

            # 3. 最后使用默认风格
            logger.warning("未找到项目风格设置，使用默认风格")
            return "电影风格"

        except Exception as e:
            logger.error(f"获取项目风格失败: {e}")
            return "电影风格"

    def _remove_existing_style_prompts(self, description: str, style_prompts: dict) -> str:
        """移除描述中已存在的风格提示词

        Args:
            description: 原始描述
            style_prompts: 风格提示词字典

        Returns:
            str: 清理后的描述
        """
        import re

        cleaned_desc = description.strip()

        # 收集所有风格提示词
        all_style_keywords = []
        for style_prompt in style_prompts.values():
            # 分割风格提示词
            keywords = [kw.strip() for kw in style_prompt.split('，') if kw.strip()]
            all_style_keywords.extend(keywords)

        # 添加常见的风格关键词
        additional_keywords = [
            '电影感', '超写实', '4K', '胶片颗粒', '景深',
            '动漫风', '鲜艳色彩', '干净线条', '赛璐璐渲染', '日本动画',
            '吉卜力风', '柔和色彩', '奇幻', '梦幻', '丰富背景',
            '赛博朋克', '霓虹灯', '未来都市', '雨夜', '暗色氛围',
            '水彩画风', '柔和笔触', '粉彩色', '插画', '温柔',
            '像素风', '8位', '复古', '低分辨率', '游戏风',
            '真实光线', '高细节', '写实摄影'
        ]
        all_style_keywords.extend(additional_keywords)

        # 移除重复的关键词
        all_style_keywords = list(set(all_style_keywords))

        # 构建正则表达式模式，匹配风格提示词
        # 匹配模式：，风格词1，风格词2，风格词3 或者 风格词1，风格词2，风格词3
        for keyword in all_style_keywords:
            # 转义特殊字符
            escaped_keyword = re.escape(keyword)

            # 匹配模式：
            # 1. ，关键词（在句子中间）
            # 2. 关键词，（在句子开头）
            # 3. ，关键词（在句子结尾）
            patterns = [
                rf'，\s*{escaped_keyword}\s*(?=，|$)',  # ，关键词，或，关键词（结尾）
                rf'^{escaped_keyword}\s*，\s*',        # 关键词，（开头）
                rf'，\s*{escaped_keyword}$',           # ，关键词（结尾）
                rf'^{escaped_keyword}$'                # 单独的关键词
            ]

            for pattern in patterns:
                cleaned_desc = re.sub(pattern, '', cleaned_desc)

        # 清理多余的逗号和空格
        cleaned_desc = re.sub(r'，+', '，', cleaned_desc)  # 多个逗号合并为一个
        cleaned_desc = re.sub(r'^，+|，+$', '', cleaned_desc)  # 移除开头和结尾的逗号
        cleaned_desc = re.sub(r'\s+', ' ', cleaned_desc)  # 多个空格合并为一个
        cleaned_desc = cleaned_desc.strip()

        if cleaned_desc != description:
            logger.info(f"清理风格提示词: '{description}' -> '{cleaned_desc}'")

        return cleaned_desc

    def _save_generated_text_to_file(self, enhanced_descriptions):
        """保存生成的文本到项目texts文件夹的prompt文件"""
        try:
            import os
            import json
            from datetime import datetime
            
            # 获取项目根目录
            if hasattr(self, 'project_root') and self.project_root:
                project_root = self.project_root
            else:
                logger.error("未设置项目根目录，无法保存增强描述文件")
                return
                
            # 构建项目输出目录下的texts文件夹路径
            # 确保使用正确的项目目录结构：project_root/texts
            texts_dir = os.path.join(project_root, "texts")
            
            # 检查texts目录是否存在，如果不存在则创建
            # 注意：这里应该使用项目目录下的texts，而不是程序根目录下的texts
            if not os.path.exists(texts_dir):
                os.makedirs(texts_dir)
            
            # 按场景组织数据
            scenes_data = {}
            
            # 分离场景标题和镜头数据
            scene_titles = []
            shot_descriptions = []
            
            for desc in enhanced_descriptions:
                if desc.get('type') == 'scene_title':
                    scene_titles.append(desc)
                else:
                    shot_descriptions.append(desc)
            
            # 检查是否有有效的场景信息
            has_valid_scenes = len(scene_titles) > 0
            logger.info(f"[_save_generated_text_to_file] 发现 {len(scene_titles)} 个场景标题，{len(shot_descriptions)} 个镜头")
            
            if scene_titles:
                for scene_title_data in scene_titles:
                    scene_name = scene_title_data.get('content', '## 场景分镜脚本')
                    logger.info(f"[_save_generated_text_to_file] 处理场景: '{scene_name}'")
            
            # 如果没有场景标题，检查镜头中的场景信息
            if not has_valid_scenes:
                for i, desc in enumerate(shot_descriptions):
                    scene_info = desc.get('shot_info', {}).get('scene', '')
                    logger.info(f"[_save_generated_text_to_file] 镜头 {i+1} 的场景信息: '{scene_info}'")
                    if scene_info and scene_info.strip() and scene_info != 'None' and not scene_info.startswith('## 场景分镜脚本'):
                        has_valid_scenes = True
                        logger.info(f"[_save_generated_text_to_file] 发现有效场景信息: '{scene_info}'")
                        break
            logger.info(f"[_save_generated_text_to_file] 是否有有效场景信息: {has_valid_scenes}")
            
            if not has_valid_scenes:
                # 所有镜头都放在统一的场景分镜脚本下
                scene_name = "## 场景分镜脚本"
                scenes_data[scene_name] = []
                
                for i, desc in enumerate(shot_descriptions):
                    # 重新构建original_description，包含完整的分镜脚本格式
                    # 在统一场景下，镜头编号从1开始连续编号
                    shot_number = f"### 镜头{i+1}"
                    shot_info = desc.get('shot_info', {})
                    
                    # 构建完整的original_description，包含所有技术细节
                    original_parts = [shot_number]
                    
                    # 按照标准分镜脚本格式添加技术细节
                    technical_fields = [
                        '镜头类型', '机位角度', '镜头运动', '景深效果', '构图要点', 
                        '光影设计', '色彩基调', '时长', '镜头角色', '画面描述', 
                        '台词/旁白', '音效提示', '转场方式'
                    ]
                    
                    # 字段标准化：确保所有镜头都包含完整的技术字段
                    default_values = {
                        '镜头类型': '中景',
                        '机位角度': '平视',
                        '镜头运动': '静止',
                        '景深效果': '正常景深',
                        '构图要点': '居中构图',
                        '光影设计': '自然光',
                        '色彩基调': '自然色调',
                        # '时长': '3秒',  # 移除硬编码时长，应根据配音确定
                        '音效提示': '环境音',
                        '转场方式': '切换'
                    }
                    
                    for field in technical_fields:
                        if field in shot_info and shot_info[field]:
                            original_parts.append(f"- **{field}**：{shot_info[field]}")
                        elif field in default_values:
                            # 如果字段缺失，使用默认值
                            original_parts.append(f"- **{field}**：{default_values[field]}")
                            logger.debug(f"为镜头 {shot_number} 添加缺失字段 {field}: {default_values[field]}")
                    
                    original_description = '\n'.join(original_parts)
                    
                    # 从enhanced_descriptions中提取正确的字段
                    shot_data = {
                        "shot_number": shot_number,
                        "original_description": original_description,
                        "enhanced_prompt": desc.get('enhanced', '')
                    }
                    scenes_data[scene_name].append(shot_data)
            else:
                # 按实际场景分组，并在每个场景内重新编号
                # 如果有场景标题，根据镜头中的场景信息正确分组
                if scene_titles:
                    # 首先按镜头中的场景信息分组
                    scene_groups = {}
                    for desc in shot_descriptions:
                        # 从镜头的shot_info中获取场景信息
                        scene_info = desc.get('shot_info', {}).get('scene', '')
                        if not scene_info or scene_info.strip() == '' or scene_info == 'None':
                            scene_info = '未知场景'

                        if scene_info not in scene_groups:
                            scene_groups[scene_info] = []
                        scene_groups[scene_info].append(desc)

                    logger.info(f"按镜头场景信息分组结果: {list(scene_groups.keys())}")

                    # 如果场景分组失败（所有镜头都在同一个场景），则使用场景标题数量平均分配
                    if len(scene_groups) == 1 and '未知场景' in scene_groups:
                        logger.info("镜头场景信息不完整，使用场景标题数量平均分配")
                        # 重新按场景标题数量分配
                        scene_groups = {}
                        shots_per_scene = len(shot_descriptions) // len(scene_titles)
                        remaining_shots = len(shot_descriptions) % len(scene_titles)

                        shot_index = 0
                        for i, scene_title_data in enumerate(scene_titles):
                            scene_name = scene_title_data.get('content', f'## 场景{i + 1}')
                            scene_groups[scene_name] = []

                            # 计算当前场景的镜头数量
                            current_shots_count = shots_per_scene
                            if i == len(scene_titles) - 1:  # 最后一个场景包含剩余镜头
                                current_shots_count += remaining_shots

                            # 分配镜头到当前场景
                            for j in range(current_shots_count):
                                if shot_index < len(shot_descriptions):
                                    scene_groups[scene_name].append(shot_descriptions[shot_index])
                                    shot_index += 1

                    # 为每个场景内的镜头重新编号并保存
                    for scene_name, scene_shots in scene_groups.items():
                        # 清理场景名称，确保格式一致
                        if not scene_name.startswith('##'):
                            if scene_name.startswith('场景'):
                                scene_name = f"## {scene_name}"
                            else:
                                scene_name = f"## 场景：{scene_name}"

                        scenes_data[scene_name] = []

                        for i, desc in enumerate(scene_shots):
                            # 在每个场景内，镜头编号从1开始
                            shot_number = f"### 镜头{i+1}"
                            shot_info = desc.get('shot_info', {})

                            # 构建完整的original_description，包含所有技术细节
                            original_parts = [shot_number]

                            # 按照标准分镜脚本格式添加技术细节
                            technical_fields = [
                                '镜头类型', '机位角度', '镜头运动', '景深效果', '构图要点',
                                '光影设计', '色彩基调', '时长', '镜头角色', '画面描述',
                                '台词/旁白', '音效提示', '转场方式'
                            ]

                            # 字段标准化：确保所有镜头都包含完整的技术字段
                            default_values = {
                                '镜头类型': '中景',
                                '机位角度': '平视',
                                '镜头运动': '静止',
                                '景深效果': '正常景深',
                                '构图要点': '居中构图',
                                '光影设计': '自然光',
                                '色彩基调': '自然色调',
                                # '时长': '3秒',  # 移除硬编码时长，应根据配音确定
                                '音效提示': '环境音',
                                '转场方式': '切换'
                            }

                            for field in technical_fields:
                                if field in shot_info and shot_info[field]:
                                    original_parts.append(f"- **{field}**：{shot_info[field]}")
                                elif field in default_values:
                                    # 如果字段缺失，使用默认值
                                    original_parts.append(f"- **{field}**：{default_values[field]}")
                                    logger.debug(f"为镜头 {shot_number} 添加缺失字段 {field}: {default_values[field]}")

                            original_description = '\n'.join(original_parts)

                            shot_data = {
                                "shot_number": shot_number,
                                "original_description": original_description,
                                "enhanced_prompt": desc.get('enhanced', '')
                            }
                            scenes_data[scene_name].append(shot_data)

                        logger.info(f"场景 '{scene_name}' 包含 {len(scene_shots)} 个镜头")
                else:
                    # 使用镜头中的场景信息分组
                    scene_groups = {}
                    for desc in shot_descriptions:
                        scene_name = desc.get('shot_info', {}).get('scene', '## 场景一')
                        if not scene_name or scene_name.strip() == '' or scene_name == 'None':
                            scene_name = '## 场景一'
                        
                        if scene_name not in scene_groups:
                            scene_groups[scene_name] = []
                        scene_groups[scene_name].append(desc)
                    
                    # 为每个场景内的镜头重新编号
                    for scene_name, scene_shots in scene_groups.items():
                        scenes_data[scene_name] = []
                        
                        for i, desc in enumerate(scene_shots):
                            # 在每个场景内，镜头编号从1开始
                            shot_number = f"### 镜头{i+1}"
                            shot_info = desc.get('shot_info', {})
                            
                            # 构建完整的original_description，包含所有技术细节
                            original_parts = [shot_number]
                            
                            # 按照标准分镜脚本格式添加技术细节
                            technical_fields = [
                                '镜头类型', '机位角度', '镜头运动', '景深效果', '构图要点', 
                                '光影设计', '色彩基调', '时长', '镜头角色', '画面描述', 
                                '台词/旁白', '音效提示', '转场方式'
                            ]
                            
                            # 字段标准化：确保所有镜头都包含完整的技术字段
                            default_values = {
                                '镜头类型': '中景',
                                '机位角度': '平视',
                                '镜头运动': '静止',
                                '景深效果': '正常景深',
                                '构图要点': '居中构图',
                                '光影设计': '自然光',
                                '色彩基调': '自然色调',
                                # '时长': '3秒',  # 移除硬编码时长，应根据配音确定
                                '音效提示': '环境音',
                                '转场方式': '切换'
                            }
                            
                            for field in technical_fields:
                                if field in shot_info and shot_info[field]:
                                    original_parts.append(f"- **{field}**：{shot_info[field]}")
                                elif field in default_values:
                                    # 如果字段缺失，使用默认值
                                    original_parts.append(f"- **{field}**：{default_values[field]}")
                                    logger.debug(f"为镜头 {shot_number} 添加缺失字段 {field}: {default_values[field]}")
                            
                            original_description = '\n'.join(original_parts)
                            
                            shot_data = {
                                "shot_number": shot_number,
                                "original_description": original_description,
                                "enhanced_prompt": desc.get('enhanced', '')
                            }
                            scenes_data[scene_name].append(shot_data)
            
            # 准备保存的数据
            prompt_data = {
                "scenes": scenes_data,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "scene_description_enhancer",
                "version": "2.0"
            }
            
            # 保存到prompt文件
            prompt_file = os.path.join(texts_dir, "prompt.json")
            with open(prompt_file, 'w', encoding='utf-8') as f:
                json.dump(prompt_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"场景增强器生成的优化提示词已保存到: {prompt_file}")
                
        except Exception as e:
            logger.error(f"保存生成文本到文件失败: {e}")

    def _save_enhanced_descriptions_to_project(self, enhanced_descriptions: List[Dict[str, Any]]):
        """将增强描述保存到project.json文件中（完全重写，确保全局镜头编号）"""
        try:
            # 查找project.json文件
            project_file = None
            if self.project_root:
                project_file = os.path.join(self.project_root, "project.json")

            if not project_file or not os.path.exists(project_file):
                logger.warning("未找到project.json文件，无法保存增强描述")
                return

            # 读取现有的project.json数据
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 🔧 修复：完全重写enhanced_descriptions字段，确保全局镜头编号
            # 不再累积保存，而是完全替换，因为我们已经在enhance_storyboard中处理了全局编号
            enhanced_data = {}

            logger.info(f"🔧 开始保存{len(enhanced_descriptions)}个增强描述到project.json")

            for i, desc in enumerate(enhanced_descriptions):
                if desc.get('type') == 'scene_title':
                    continue  # 跳过场景标题

                shot_number = desc.get('镜头编号', '')
                scene = desc.get('scene', '')
                enhanced_prompt = desc.get('enhanced', '')
                original_prompt = desc.get('original', '')

                if shot_number and enhanced_prompt:
                    # 🔧 修复：直接使用已经处理过的全局镜头编号
                    # 不再重新处理，因为enhance_storyboard方法已经确保了全局唯一性
                    shot_key = shot_number  # 直接使用，应该已经是"### 镜头X"格式

                    enhanced_data[shot_key] = {
                        'shot_number': shot_key,
                        'scene': scene,
                        'original_prompt': original_prompt,
                        'enhanced_prompt': enhanced_prompt,
                        'technical_details': desc.get('technical_details', ''),
                        'consistency_info': desc.get('consistency_info', ''),
                        'characters': desc.get('characters', []),
                        'fusion_quality_score': desc.get('fusion_quality_score', 0.0)
                    }

                    logger.debug(f"保存镜头 {i+1}/{len(enhanced_descriptions)}: {shot_key}")

            # 🔧 修复：完全替换enhanced_descriptions字段
            project_data['enhanced_descriptions'] = enhanced_data

            # 保存更新后的project.json
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)

            total_shots = len(enhanced_data)
            logger.info(f"✅ 已将{total_shots}个增强描述完全保存到project.json")

            # 🔧 新增：验证保存结果
            if total_shots > 0:
                shot_numbers = list(enhanced_data.keys())
                logger.info(f"保存的镜头编号: {shot_numbers[:5]}{'...' if len(shot_numbers) > 5 else ''}")

                # 检查镜头编号是否连续
                import re
                numbers = []
                for shot_key in shot_numbers:
                    match = re.search(r'镜头(\d+)', shot_key)
                    if match:
                        numbers.append(int(match.group(1)))

                if numbers:
                    numbers.sort()
                    logger.info(f"镜头编号范围: {min(numbers)} - {max(numbers)}")
                    if numbers == list(range(min(numbers), max(numbers) + 1)):
                        logger.info("✅ 镜头编号连续，保存成功")
                    else:
                        logger.warning("⚠️ 镜头编号不连续，可能存在问题")

        except Exception as e:
            logger.error(f"保存增强描述到project.json失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    # 🔧 修改：移除save_original_descriptions_by_scene方法，改为在所有场景完成后统一处理一致性描述

    def _intelligent_character_embedding_filter(self, description: str, detected_characters: List[str]) -> List[str]:
        """智能过滤需要嵌入一致性描述的角色

        Args:
            description: 画面描述
            detected_characters: 检测到的角色列表

        Returns:
            List[str]: 需要嵌入一致性描述的角色列表
        """
        if not detected_characters:
            return []

        try:
            # 使用LLM智能判断
            if hasattr(self, 'llm_api') and self.llm_api and self.llm_api.is_configured():
                return self._llm_character_embedding_filter(description, detected_characters)
            else:
                # 如果LLM不可用，使用规则过滤
                return self._rule_based_character_embedding_filter(description, detected_characters)
        except Exception as e:
            logger.error(f"智能角色过滤失败: {e}")
            # 出错时返回所有角色
            return detected_characters

    def _llm_character_embedding_filter(self, description: str, detected_characters: List[str]) -> List[str]:
        """使用LLM智能判断哪些角色需要嵌入一致性描述"""
        try:
            characters_str = '、'.join(detected_characters)
            prompt = f"""请分析以下画面描述，判断哪些角色需要嵌入外貌一致性描述。

通用规则（适用于各种文学作品）：
1. 如果角色本人直接出现在画面中，需要嵌入一致性描述
   - 历史题材：如"赵括严肃的面孔"、"廉颇的表情"
   - 现代题材：如"张医生疲惫的神情"、"李老师温和的笑容"
   - 科幻题材：如"机器人X-01的金属外壳"、"外星人首领的触手"
   - 奇幻题材：如"精灵王子的尖耳朵"、"矮人战士的胡须"

2. 如果只是提到角色的物品、势力、影响等，不需要嵌入
   - 历史题材：如"赵括的军队"、"廉颇的战略"
   - 现代题材：如"张医生的诊所"、"李老师的课堂"
   - 科幻题材：如"机器人的工厂"、"外星人的飞船"
   - 奇幻题材：如"精灵的森林"、"矮人的矿山"

3. 群体场景中的个体角色，需要嵌入
4. 远景或全景中的小人物，可以不嵌入

画面描述：{description}

检测到的角色：{characters_str}

请只返回需要嵌入一致性描述的角色名称，用中文顿号（、）分隔。如果都不需要，返回"无"。

示例：
- "赵括严肃的面孔" → 赵括
- "赵括的军队溃散" → 无
- "张医生和李护士交谈" → 张医生、李护士
- "机器人X-01的红色眼睛闪烁" → 机器人X-01
- "精灵的魔法森林" → 无"""

            # 尝试调用LLM API
            try:
                if hasattr(self.llm_api, '_make_api_call'):
                    messages = [
                        {"role": "system", "content": "你是一个专业的角色分析师，擅长判断画面描述中哪些角色需要详细的外貌描述。"},
                        {"role": "user", "content": prompt}
                    ]
                    response = self.llm_api._make_api_call(
                        model_name=getattr(self.llm_api, 'rewrite_model_name', 'gpt-3.5-turbo'),
                        messages=messages,
                        task_name="character_embedding_filter"
                    )
                else:
                    # 如果没有_make_api_call方法，使用备用方案
                    response = None
            except Exception as api_error:
                logger.error(f"LLM API调用失败: {api_error}")
                response = None

            if response and response.strip() and response.strip() != "无":
                # 解析LLM返回的角色列表
                filtered_characters = []
                for char in response.strip().split('、'):
                    char = char.strip()
                    if char and char in detected_characters:
                        filtered_characters.append(char)

                logger.info(f"LLM智能过滤结果: {detected_characters} → {filtered_characters}")
                return filtered_characters
            else:
                logger.info("LLM判断无需嵌入任何角色一致性描述")
                return []

        except Exception as e:
            logger.error(f"LLM角色过滤失败: {e}")
            return self._rule_based_character_embedding_filter(description, detected_characters)

    def _rule_based_character_embedding_filter(self, description: str, detected_characters: List[str]) -> List[str]:
        """基于规则的角色过滤（通用版本，适用于各种文学作品）"""
        filtered_characters = []

        for character in detected_characters:
            # 检查是否是"XX的XX"格式（通常不需要嵌入）
            possession_patterns = [
                # 历史题材
                f"{character}的军队", f"{character}的部队", f"{character}的士兵",
                f"{character}的剑", f"{character}的武器", f"{character}的装备",
                f"{character}的王国", f"{character}的领土", f"{character}的宫殿",

                # 现代题材
                f"{character}的公司", f"{character}的办公室", f"{character}的车",
                f"{character}的房子", f"{character}的家", f"{character}的工作",
                f"{character}的电话", f"{character}的电脑", f"{character}的手机",

                # 科幻题材
                f"{character}的飞船", f"{character}的基地", f"{character}的实验室",
                f"{character}的机器人", f"{character}的AI", f"{character}的系统",

                # 奇幻题材
                f"{character}的魔法", f"{character}的法术", f"{character}的咒语",
                f"{character}的城堡", f"{character}的森林", f"{character}的龙",

                # 通用
                f"{character}的影响", f"{character}的声音", f"{character}的命令",
                f"{character}的想法", f"{character}的计划", f"{character}的策略"
            ]

            is_possession = any(pattern in description for pattern in possession_patterns)

            if not is_possession:
                # 检查是否直接描述角色本人
                direct_patterns = [
                    # 外貌描述
                    f"{character}的面孔", f"{character}的表情", f"{character}的眼神",
                    f"{character}的头发", f"{character}的皮肤", f"{character}的身材",

                    # 情绪状态
                    f"{character}严肃", f"{character}焦虑", f"{character}激动",
                    f"{character}愤怒", f"{character}高兴", f"{character}悲伤",
                    f"{character}微笑", f"{character}皱眉", f"{character}哭泣",

                    # 动作行为
                    f"{character}站", f"{character}坐", f"{character}走",
                    f"{character}跑", f"{character}跳", f"{character}飞",
                    f"{character}说", f"{character}喊", f"{character}叫",
                    f"{character}看", f"{character}听", f"{character}想",

                    # 穿着打扮
                    f"{character}穿着", f"{character}戴着", f"{character}拿着",
                    f"{character}身着", f"{character}手持", f"{character}佩戴"
                ]

                is_direct = any(pattern in description for pattern in direct_patterns)

                # 如果是直接描述或者角色名称直接出现在描述中（但不是所有格形式）
                if is_direct or (character in description and f"{character}的" not in description):
                    filtered_characters.append(character)

        logger.info(f"规则过滤结果: {detected_characters} → {filtered_characters}")
        return filtered_characters

    def _embed_character_descriptions(self, original_desc: str, detected_characters: List[str]) -> str:
        """将角色一致性描述智能嵌入到原始描述中"""
        if not detected_characters:
            return original_desc

        enhanced_desc = original_desc

        # 使用LLM智能判断哪些角色需要嵌入一致性描述
        characters_to_embed = self._intelligent_character_embedding_filter(original_desc, detected_characters)

        if not characters_to_embed:
            logger.info("经过智能分析，无需嵌入角色一致性描述")
            return original_desc

        # 获取角色一致性信息
        character_descriptions = {}
        for character_name in characters_to_embed:
            # 直接使用_get_character_consistency方法获取角色一致性描述
            character_consistency = self._get_character_consistency(character_name)
            if character_consistency:
                character_descriptions[character_name] = character_consistency
                logger.info(f"准备嵌入角色'{character_name}'的一致性描述: {character_consistency}")
            else:
                logger.warning(f"角色'{character_name}'没有可用的一致性描述")

        # 按角色名长度降序排序，优先替换更长的角色名，避免"李静妈妈"被"李静"误匹配
        sorted_characters = sorted(character_descriptions.items(), key=lambda x: len(x[0]), reverse=True)
        
        # 在原始描述中替换角色名称为详细描述
        for character_name, detailed_desc in sorted_characters:
            # 使用精确匹配进行角色替换，支持中文字符
            replacement = f"{character_name}（{detailed_desc}）"
            # 只有当角色名还没有被替换过时才进行替换（避免重复替换）
            if character_name in enhanced_desc and f"{character_name}（" not in enhanced_desc:
                # 检查当前角色名是否是其他更长角色名的一部分
                is_part_of_longer_name = False
                for other_char_name in character_descriptions.keys():
                    if other_char_name != character_name and len(other_char_name) > len(character_name):
                        if character_name in other_char_name and other_char_name in enhanced_desc:
                            is_part_of_longer_name = True
                            break

                if not is_part_of_longer_name:
                    # 🔧 修复：使用更精确的替换，避免重复嵌入
                    # 检查是否已经嵌入过该角色的描述
                    if f"{character_name}（" not in enhanced_desc:
                        # 只替换第一次出现的完整角色名称
                        import re
                        pattern = rf'\b{re.escape(character_name)}\b'
                        if re.search(pattern, enhanced_desc):
                            enhanced_desc = re.sub(pattern, replacement, enhanced_desc, count=1)
                            logger.info(f"成功嵌入角色一致性描述: {character_name} -> {replacement}")
                        else:
                            # 如果没有找到完整匹配，使用简单替换
                            enhanced_desc = enhanced_desc.replace(character_name, replacement, 1)
                            logger.info(f"成功嵌入角色一致性描述(简单替换): {character_name} -> {replacement}")
                        logger.info(f"角色描述嵌入: {character_name} -> {replacement[:50]}...")
                    else:
                        logger.debug(f"角色'{character_name}'已经嵌入过描述，跳过")
                else:
                    logger.debug(f"跳过角色'{character_name}'，因为它是更长角色名的一部分")
        
        return enhanced_desc
    
    def _get_character_consistency(self, character_name: str) -> str:
        """获取角色一致性描述"""
        try:
            if self.character_scene_manager:
                # 角色名称映射，将检测到的角色名称映射到数据库中的角色名称
                character_name_mapping = {
                    '主要角色': '主角',
                    '主人公': '主角',
                    '男主': '主角',
                    '女主': '主角',
                    '科学家': '科学家',
                    '军人': '军人',
                    '士兵': '军人',
                    '政治家': '政治家'
                }

                # 尝试映射角色名称
                mapped_name = character_name_mapping.get(character_name, character_name)

                # 通过角色名称查找角色（而不是通过ID）
                all_characters = self.character_scene_manager.get_all_characters()
                character_info = None

                for char_id, char_data in all_characters.items():
                    if char_data.get('name') == mapped_name:
                        character_info = char_data
                        break

                if character_info:
                    # 直接使用consistency_prompt字段
                    consistency_prompt = character_info.get('consistency_prompt', '')
                    if consistency_prompt:
                        return consistency_prompt

                    # 如果没有consistency_prompt，则构建角色一致性描述
                    consistency_parts = []

                    # 添加外貌描述
                    if character_info.get('appearance'):
                        consistency_parts.append(character_info['appearance'])

                    # 添加服装描述
                    if character_info.get('clothing'):
                        consistency_parts.append(character_info['clothing'])

                    # 添加特征描述
                    if character_info.get('features'):
                        consistency_parts.append(character_info['features'])

                    return '，'.join(consistency_parts) if consistency_parts else ''
            return ''
        except Exception as e:
            logger.error(f"获取角色一致性描述失败 {character_name}: {e}")
            return ''