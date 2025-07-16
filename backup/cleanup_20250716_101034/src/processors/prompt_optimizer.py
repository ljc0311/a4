# -*- coding: utf-8 -*-
"""
提示词优化器
负责处理AI绘图提示词的优化和增强功能
"""

import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from src.utils.logger import logger
from src.utils.character_detection_config import CharacterDetectionConfig


class PromptOptimizer:
    """提示词优化器类"""
    
    def __init__(self, llm_api=None, cs_manager=None):
        """
        初始化提示词优化器
        
        Args:
            llm_api: LLM API实例，用于AI优化
            cs_manager: 角色场景管理器实例
        """
        self.llm_api = llm_api
        self.cs_manager = cs_manager
        
        # 基础的中英文映射词典
        self.translation_map = {
            '男性': 'male', '女性': 'female', '年轻': 'young', '中年': 'middle-aged',
            '老年': 'elderly', '高大': 'tall', '瘦小': 'slim', '强壮': 'strong',
            '美丽': 'beautiful', '英俊': 'handsome', '可爱': 'cute', '严肃': 'serious',
            '友善': 'friendly', '室内': 'indoor', '室外': 'outdoor', '白天': 'daytime',
            '夜晚': 'night', '阳光': 'sunlight', '月光': 'moonlight', '温暖': 'warm',
            '寒冷': 'cold', '明亮': 'bright', '昏暗': 'dim', '自然光': 'natural lighting',
            '人工光': 'artificial lighting', '柔和': 'soft', '强烈': 'intense',
            '平静': 'calm', '紧张': 'tense', '欢乐': 'joyful', '悲伤': 'sad',
            '神秘': 'mysterious', '浪漫': 'romantic', '火车站': 'train station',
            '站台': 'platform', '背包': 'backpack', '服装': 'clothing'
        }
    
    def generate_optimized_prompt(self, shot, all_characters: List[str], all_scenes: List[str]) -> Tuple[str, str]:
        """
        生成优化后的提示词（中英文对照）
        
        Args:
            shot: 镜头对象，包含image_prompt、characters、scene等属性
            all_characters: 所有角色列表
            all_scenes: 所有场景列表
            
        Returns:
            Tuple[str, str]: (优化后的中文提示词, 优化后的英文提示词)
        """
        try:
            # 获取角色和场景的详细信息
            character_details = self._get_character_details(shot.characters)
            scene_details = self._get_scene_details(all_scenes, shot.scene)
            
            # 构建整合后的画面描述
            enhanced_description = self._build_enhanced_description(
                shot.image_prompt, character_details, scene_details
            )
            
            # 使用AI模型生成优化的提示词
            optimized_cn, optimized_en = self._generate_ai_optimized_prompt(enhanced_description)
            
            return optimized_cn, optimized_en
            
        except Exception as e:
            logger.error(f"生成优化提示词失败: {e}")
            return shot.image_prompt, shot.image_prompt
    
    def _get_character_details(self, character_names: List[str]) -> Dict[str, Dict[str, str]]:
        """
        获取角色详细信息
        
        Args:
            character_names: 角色名称列表
            
        Returns:
            Dict[str, Dict[str, str]]: 角色详细信息字典
        """
        character_details = {}
        
        if self.cs_manager:
            all_char_data = self.cs_manager.get_all_characters()
            for char_name in character_names:
                if char_name in all_char_data:
                    char_info = all_char_data[char_name]
                    character_details[char_name] = {
                        'description': char_info.get('description', ''),
                        'appearance': char_info.get('appearance', ''),
                        'consistency_prompt': char_info.get('consistency_prompt', '')
                    }
        
        return character_details
    
    def _get_scene_details(self, all_scenes: List[str], target_scene: str) -> Dict[str, Dict[str, str]]:
        """
        获取场景详细信息
        
        Args:
            all_scenes: 所有场景列表
            target_scene: 目标场景名称
            
        Returns:
            Dict[str, Dict[str, str]]: 场景详细信息字典
        """
        scene_details = {}
        
        if self.cs_manager:
            all_scene_data = self.cs_manager.get_all_scenes()
            for scene_name in all_scenes:
                if scene_name in all_scene_data and scene_name == target_scene:
                    scene_info = all_scene_data[scene_name]
                    scene_details[scene_name] = {
                        'description': scene_info.get('description', ''),
                        'environment': scene_info.get('environment', ''),
                        'lighting': scene_info.get('lighting', ''),
                        'atmosphere': scene_info.get('atmosphere', ''),
                        'consistency_prompt': scene_info.get('consistency_prompt', '')
                    }
        
        return scene_details
    
    def _build_enhanced_description(self, original_prompt: str, character_details: Dict, scene_details: Dict) -> str:
        """
        构建整合后的画面描述
        
        Args:
            original_prompt: 原始提示词
            character_details: 角色详细信息
            scene_details: 场景详细信息
            
        Returns:
            str: 增强后的描述
        """
        enhanced_description = original_prompt
        
        # 整合角色一致性描述
        if character_details:
            # 按角色名长度降序排序，优先替换更长的角色名，避免"李静妈妈"被"李静"误匹配
            sorted_characters = sorted(character_details.items(), key=lambda x: len(x[0]), reverse=True)
            
            for char_name, details in sorted_characters:
                char_consistency_parts = []
                if details['appearance']:
                    char_consistency_parts.append(details['appearance'])
                if details['description']:
                    char_consistency_parts.append(details['description'])
                if details['consistency_prompt']:
                    char_consistency_parts.append(details['consistency_prompt'])
                
                if char_consistency_parts:
                    char_consistency = f"{char_name}（{', '.join(char_consistency_parts)}）"
                    # 在原始描述中查找角色名称并替换为详细描述
                    # 只有当角色名还没有被替换过时才进行替换（避免重复替换）
                    if char_name in enhanced_description and f"{char_name}（" not in enhanced_description:
                        # 检查当前角色名是否是其他更长角色名的一部分
                        is_part_of_longer_name = False
                        for other_char_name in character_details.keys():
                            if other_char_name != char_name and len(other_char_name) > len(char_name):
                                if char_name in other_char_name and other_char_name in enhanced_description:
                                    is_part_of_longer_name = True
                                    break
                        
                        # 只有当不是其他角色名的一部分时才进行替换
                        if not is_part_of_longer_name:
                            # 对于单字符角色名（如"我"），使用更精确的匹配
                             if len(char_name) == 1:
                                 import re
                                 # 查找所有匹配位置，手动检查边界
                                 matches = []
                                 start = 0
                                 while True:
                                     pos = enhanced_description.find(char_name, start)
                                     if pos == -1:
                                         break
                                     # 检查前后字符，确保这是一个独立的字符
                                     before_char = enhanced_description[pos-1] if pos > 0 else ''
                                     after_char = enhanced_description[pos+len(char_name)] if pos+len(char_name) < len(enhanced_description) else ''
                                     
                                     # 对于"我"，如果后面是"们"，则跳过
                                     if char_name == '我' and after_char == '们':
                                         start = pos + 1
                                         continue
                                     
                                     # 如果前后都不是字母数字或中文字符，则认为是独立的字符
                                     if (not before_char or not (before_char.isalnum() or '\u4e00' <= before_char <= '\u9fff')) and \
                                        (not after_char or not (after_char.isalnum() or '\u4e00' <= after_char <= '\u9fff')):
                                         matches.append(pos)
                                     start = pos + 1
                                 
                                 # 从后往前替换，避免位置偏移
                                 for pos in reversed(matches):
                                     enhanced_description = enhanced_description[:pos] + char_consistency + enhanced_description[pos+len(char_name):]
                             else:
                                 enhanced_description = enhanced_description.replace(char_name, char_consistency)
                             logger.info(f"角色描述嵌入: {char_name} -> {char_consistency[:50]}...")
                             break  # 只替换第一个匹配项
                    elif "主人公" in enhanced_description and f"主人公（" not in enhanced_description:
                        # 如果原描述中没有角色名称，则替换"主人公"
                        enhanced_description = enhanced_description.replace("主人公", char_consistency)
                        logger.info(f"主人公替换为: {char_consistency[:50]}...")
        
        # 整合场景一致性描述
        if scene_details:
            for scene_name, details in scene_details.items():
                scene_consistency_parts = []
                if details['description']:
                    scene_consistency_parts.append(details['description'])
                if details['environment']:
                    scene_consistency_parts.append(details['environment'])
                if details['consistency_prompt']:
                    scene_consistency_parts.append(details['consistency_prompt'])
                
                if scene_consistency_parts:
                    scene_consistency = f"{scene_name}（{', '.join(scene_consistency_parts)}）"
                    # 在原始描述中查找场景名称并替换为详细描述
                    if scene_name in enhanced_description:
                        enhanced_description = enhanced_description.replace(scene_name, scene_consistency)
        
        return enhanced_description
    
    def _generate_ai_optimized_prompt(self, enhanced_description: str) -> Tuple[str, str]:
        """
        使用AI模型生成优化的中英文提示词
        
        Args:
            enhanced_description: 增强后的描述
            
        Returns:
            Tuple[str, str]: (优化后的中文提示词, 优化后的英文提示词)
        """
        try:
            # 检查是否有LLM API可用
            if not self.llm_api:
                # 如果没有LLM API，返回基础的翻译结果
                return self._basic_translation(enhanced_description)
            
            # 构建AI优化提示词的prompt
            system_prompt = """你是一个专业的AI绘图提示词优化专家。你的任务是将用户提供的画面描述优化成高质量的文生图提示词。

优化要求：
1. 保持原始画面的核心内容和情感
2. 增加具体的视觉细节描述
3. 添加适当的艺术风格和技术参数
4. 确保提示词具有良好的可执行性
5. 中文版本要自然流畅，英文版本要专业准确

重要：请直接输出优化后的提示词内容，不要使用占位符如[优化后的中文提示词]等。

请严格按照以下格式输出：
中文版本：（这里直接写优化后的中文提示词）
英文版本：（这里直接写优化后的英文提示词）

示例格式：
中文版本：一位年轻女性站在繁忙的火车站台上，背着蓝色背包，穿着休闲服装，周围是匆忙的乘客和现代化的站台设施，自然光线透过玻璃屋顶洒下，营造出温暖而忙碌的氛围
英文版本：A young woman standing on a busy train platform, wearing a blue backpack and casual clothing, surrounded by hurried passengers and modern platform facilities, natural light streaming through the glass roof, creating a warm and bustling atmosphere"""
            
            user_prompt = f"""请根据以下画面描述生成优化的文生图提示词：

{enhanced_description}"""
            
            # 构建消息格式
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 调用LLM API生成优化提示词
            response = self.llm_api._make_api_call(
                model_name=self.llm_api.rewrite_model_name,
                messages=messages,
                task_name="optimize_prompt"
            )
            
            # 解析响应，提取中英文提示词
            optimized_cn, optimized_en = self._parse_ai_response(response)
            
            return optimized_cn, optimized_en
            
        except Exception as e:
            logger.error(f"AI优化提示词生成失败: {e}")
            return self._basic_translation(enhanced_description)
    
    def _parse_ai_response(self, response: str) -> Tuple[str, str]:
        """
        解析AI响应，提取中英文提示词
        
        Args:
            response: AI响应文本
            
        Returns:
            Tuple[str, str]: (中文提示词, 英文提示词)
        """
        try:
            logger.debug(f"正在解析AI响应: {response[:200]}...")  # 记录响应的前200个字符
            
            lines = response.strip().split('\n')
            optimized_cn = ""
            optimized_en = ""
            
            # 检查是否包含占位符格式
            placeholder_patterns = [
                '[优化后的中文提示词]', '[优化后的英文提示词]',
                '[中文提示词]', '[英文提示词]',
                '[中文版本]', '[英文版本]'
            ]
            
            has_placeholders = any(pattern in response for pattern in placeholder_patterns)
            
            if has_placeholders:
                logger.debug("检测到占位符格式，使用占位符解析逻辑")
                # 处理占位符格式，提取占位符后的实际内容
                optimized_cn, optimized_en = self._parse_placeholder_format(response)
            else:
                # 使用原有的标准格式解析逻辑
                for line in lines:
                    line = line.strip()
                    
                    # 匹配中文版本的多种格式
                    if any(pattern in line for pattern in ['中文版本：', '中文版本:', '中文：', '中文:', '中文提示词：', '中文提示词:']):
                        # 提取冒号后的内容
                        for separator in ['：', ':']:
                            if separator in line:
                                optimized_cn = line.split(separator, 1)[1].strip()
                                break
                    
                    # 匹配英文版本的多种格式
                    elif any(pattern in line for pattern in ['英文版本：', '英文版本:', '英文：', '英文:', '英文提示词：', '英文提示词:', 'English:', 'English：']):
                        # 提取冒号后的内容
                        for separator in ['：', ':']:
                            if separator in line:
                                optimized_en = line.split(separator, 1)[1].strip()
                                break
            
            # 清理提取的内容，移除可能的引号和多余空格
            if optimized_cn:
                optimized_cn = optimized_cn.strip('"\'"`"').strip()
            if optimized_en:
                optimized_en = optimized_en.strip('"\'"`"').strip()
            
            # 检查是否仍然包含占位符文本（质量检查）
            if self._contains_placeholder_text(optimized_cn) or self._contains_placeholder_text(optimized_en):
                logger.warning("提取的内容仍包含占位符，尝试进一步处理")
                optimized_cn = self._clean_placeholder_text(optimized_cn)
                optimized_en = self._clean_placeholder_text(optimized_en)
            
            logger.debug(f"解析结果 - 中文: {optimized_cn[:50]}..., 英文: {optimized_en[:50]}...")
            
            # 如果解析失败，尝试从整个响应中提取有用内容
            if not optimized_cn or not optimized_en or len(optimized_cn.strip()) < 5 or len(optimized_en.strip()) < 5:
                logger.warning(f"标准格式解析失败，尝试备用解析方法")
                
                # 如果响应内容看起来像是直接的提示词（没有格式标识）
                if response and len(response.strip()) > 10:
                    # 尝试将整个响应作为中文提示词，并生成英文版本
                    if not optimized_cn or len(optimized_cn.strip()) < 5:
                        optimized_cn = response.strip()
                    if not optimized_en or len(optimized_en.strip()) < 5:
                        optimized_en = self._basic_translation(response.strip())[1]
                    
                    logger.info(f"使用备用解析方法成功提取内容")
                    return optimized_cn, optimized_en
                
                # 最后的备用方案
                logger.warning(f"所有解析方法都失败，使用基础翻译")
                return self._basic_translation(response)
            
            return optimized_cn, optimized_en
            
        except Exception as e:
            logger.error(f"解析AI响应失败: {e}")
            logger.error(f"原始响应内容: {response}")
            return self._basic_translation(response)
    
    def _parse_placeholder_format(self, response: str) -> Tuple[str, str]:
        """
        解析包含占位符的AI响应格式
        
        Args:
            response: AI响应文本
            
        Returns:
            Tuple[str, str]: (中文提示词, 英文提示词)
        """
        try:
            optimized_cn = ""
            optimized_en = ""
            
            # 分割响应为行
            lines = response.strip().split('\n')
            
            # 查找占位符并提取后续内容
            cn_placeholder_found = False
            en_placeholder_found = False
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # 检查中文占位符
                if any(pattern in line for pattern in ['[优化后的中文提示词]', '[中文提示词]', '[中文版本]']):
                    cn_placeholder_found = True
                    # 尝试从同一行提取内容（占位符后面可能有内容）
                    for pattern in ['[优化后的中文提示词]', '[中文提示词]', '[中文版本]']:
                        if pattern in line:
                            after_placeholder = line.split(pattern, 1)[1].strip()
                            if after_placeholder and len(after_placeholder) > 5:
                                optimized_cn = after_placeholder
                                break
                    
                    # 如果同一行没有内容，查找下一行
                    if not optimized_cn and i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and len(next_line) > 5 and not any(p in next_line for p in ['[', ']', '占位符']):
                            optimized_cn = next_line
                
                # 检查英文占位符
                elif any(pattern in line for pattern in ['[优化后的英文提示词]', '[英文提示词]', '[英文版本]']):
                    en_placeholder_found = True
                    # 尝试从同一行提取内容
                    for pattern in ['[优化后的英文提示词]', '[英文提示词]', '[英文版本]']:
                        if pattern in line:
                            after_placeholder = line.split(pattern, 1)[1].strip()
                            if after_placeholder and len(after_placeholder) > 5:
                                optimized_en = after_placeholder
                                break
                    
                    # 如果同一行没有内容，查找下一行
                    if not optimized_en and i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and len(next_line) > 5 and not any(p in next_line for p in ['[', ']', '占位符']):
                            optimized_en = next_line
                
                # 如果没有找到占位符，但找到了有效内容行，尝试智能分配
                elif not cn_placeholder_found and not en_placeholder_found and line and len(line) > 10:
                    # 如果包含中文字符，可能是中文提示词
                    if any('\u4e00' <= char <= '\u9fff' for char in line) and not optimized_cn:
                        optimized_cn = line
                    # 如果主要是英文字符，可能是英文提示词
                    elif line.replace(' ', '').isascii() and not optimized_en:
                        optimized_en = line
            
            logger.debug(f"占位符解析结果 - 中文: {optimized_cn[:50]}..., 英文: {optimized_en[:50]}...")
            
            return optimized_cn, optimized_en
            
        except Exception as e:
            logger.error(f"占位符格式解析失败: {e}")
            return "", ""
    
    def _contains_placeholder_text(self, text: str) -> bool:
        """
        检查文本是否包含占位符
        
        Args:
            text: 待检查的文本
            
        Returns:
            bool: 是否包含占位符
        """
        if not text:
            return False
        
        placeholder_indicators = [
            '[优化后的', '[中文提示词]', '[英文提示词]', '[中文版本]', '[英文版本]',
            '占位符', 'placeholder', '待填充', '请填写'
        ]
        
        return any(indicator in text for indicator in placeholder_indicators)
    
    def _clean_placeholder_text(self, text: str) -> str:
        """
        清理文本中的占位符
        
        Args:
            text: 待清理的文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return text
        
        # 移除常见的占位符模式
        patterns_to_remove = [
            r'\[优化后的[^\]]*\]',
            r'\[中文[^\]]*\]',
            r'\[英文[^\]]*\]',
            r'\[[^\]]*提示词[^\]]*\]',
            r'\[[^\]]*版本[^\]]*\]'
        ]
        
        import re
        cleaned_text = text
        for pattern in patterns_to_remove:
            cleaned_text = re.sub(pattern, '', cleaned_text)
        
        return cleaned_text.strip()
    
    def _basic_translation(self, text: str) -> Tuple[str, str]:
        """
        基础的中英文翻译
        
        Args:
            text: 待翻译的文本
            
        Returns:
            Tuple[str, str]: (中文文本, 英文文本)
        """
        logger.debug(f"使用基础翻译处理: {text[:100]}...")
        
        # 清理输入文本
        cleaned_text = text.strip()
        
        # 如果文本为空或太短，返回默认值
        if not cleaned_text or len(cleaned_text) < 5:
            logger.warning(f"文本太短或为空，返回默认提示词")
            return "画面描述", "scene description"
        
        # 简单的翻译处理
        english_text = cleaned_text
        for cn, en in self.translation_map.items():
            english_text = english_text.replace(cn, en)
        
        # 如果翻译后的英文文本与原文相同（说明没有进行翻译），
        # 则假设原文是中文，尝试生成简单的英文描述
        if english_text == cleaned_text and any('\u4e00' <= char <= '\u9fff' for char in cleaned_text):
            # 包含中文字符，生成基础英文描述
            english_text = "A scene with " + english_text.replace('，', ', ').replace('。', '. ')
            logger.debug(f"检测到中文内容，生成基础英文描述")
        
        logger.debug(f"基础翻译结果 - 中文: {cleaned_text[:50]}..., 英文: {english_text[:50]}...")
        
        return cleaned_text, english_text
    
    def extract_shots_from_script(self, storyboard_script: str, scene_info: Optional[Dict] = None) -> List[Dict]:
        """
        从分镜脚本中提取镜头信息

        Args:
            storyboard_script: 分镜脚本文本
            scene_info: 场景信息（可选）

        Returns:
            List[Dict]: 镜头信息列表，每个元素包含镜头编号、画面描述和角色信息
        """
        try:
            shots_with_prompts = []
            lines = storyboard_script.split('\n')
            current_shot = None
            current_description = ""
            current_characters = ""
            
            for line in lines:
                line = line.strip()
                
                # 检测镜头标题
                if line.startswith('### 镜头') or line.startswith('##镜头') or '镜头' in line and line.endswith('###'):
                    # 保存上一个镜头的信息
                    if current_shot and current_description:
                        # 如果没有明确的镜头角色，从画面描述中提取
                        if not current_characters:
                            current_characters = self._extract_characters_from_description(current_description)
                        
                        shots_with_prompts.append({
                            'shot_number': current_shot,
                            'description': current_description.strip(),
                            'characters': current_characters
                        })
                    
                    # 提取镜头编号
                    import re
                    shot_match = re.search(r'镜头(\d+)', line)
                    if shot_match:
                        current_shot = shot_match.group(1)
                        current_description = ""
                        current_characters = ""
                
                # 检测镜头角色
                elif line.startswith('- **镜头角色**：') or line.startswith('**镜头角色**：'):
                    current_characters = line.replace('- **镜头角色**：', '').replace('**镜头角色**：', '').strip()
                elif line.startswith('- **镜头角色**:') or line.startswith('**镜头角色**:'):
                    current_characters = line.replace('- **镜头角色**:', '').replace('**镜头角色**:', '').strip()
                
                # 检测画面描述
                elif line.startswith('- **画面描述**：') or line.startswith('**画面描述**：'):
                    current_description = line.replace('- **画面描述**：', '').replace('**画面描述**：', '').strip()
                elif line.startswith('- **画面描述**:') or line.startswith('**画面描述**:'):
                    current_description = line.replace('- **画面描述**:', '').replace('**画面描述**:', '').strip()
            
            # 保存最后一个镜头的信息
            if current_shot and current_description:
                # 如果没有明确的镜头角色，从画面描述中提取
                if not current_characters:
                    current_characters = self._extract_characters_from_description(current_description)
                
                shots_with_prompts.append({
                    'shot_number': current_shot,
                    'description': current_description.strip(),
                    'characters': current_characters
                })
            
            logger.info(f"从分镜脚本中提取到 {len(shots_with_prompts)} 个镜头")
            return shots_with_prompts
            
        except Exception as e:
            logger.error(f"提取镜头信息失败: {e}")
            return []
    
    def _extract_characters_from_description(self, description: str) -> str:
        """
        从画面描述中提取角色信息
        
        Args:
            description: 画面描述文本
            
        Returns:
            str: 角色列表字符串，用逗号分隔
        """
        try:
            # 优先使用LLM智能提取角色
            if self.llm_api and self.llm_api.is_configured():
                return self._extract_characters_with_llm(description)
            else:
                # 如果LLM不可用，使用关键词匹配作为后备方案
                return self._extract_characters_fallback(description)
        except Exception as e:
            logger.error(f"角色提取失败: {e}")
            # 出错时使用后备方案
            return self._extract_characters_fallback(description)
    
    def _extract_characters_with_llm(self, description: str) -> str:
        """
        使用LLM智能提取角色信息
        
        Args:
            description: 画面描述文本
            
        Returns:
            str: 角色列表字符串，用逗号分隔
        """
        try:
            prompt = f"""请从以下画面描述中提取出现的所有角色/人物，包括但不限于：
- 具体的人物名称（如：张三、李四、小明等）
- 角色称谓（如：主人公、主角、男主、女主等）
- 人物特征描述（如：光头大叔、年轻女子、老奶奶等）
- 职业身份（如：医生、老师、警察、店主等）
- 关系称谓（如：父亲、母亲、朋友、同事等）
- 群体角色（如：路人、行人、顾客、学生等）

画面描述：{description}

请只返回角色名称，用中文顿号（、）分隔，不要包含其他解释文字。如果没有角色，请返回空字符串。

示例输出格式：主人公、光头大叔、年轻女子"""
            
            # 使用服务管理器获取LLM服务
            from src.core.service_manager import ServiceManager, ServiceType
            import asyncio

            service_manager = ServiceManager()
            llm_service = service_manager.get_service(ServiceType.LLM)

            if llm_service:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(llm_service.generate_text(prompt))
                    response = result.data.get('content', '') if result.success else ''
                finally:
                    loop.close()
            else:
                response = ''
            
            if response and response.strip():
                # 清理响应，去除可能的多余文字
                characters_text = response.strip()
                
                # 去除常见的前缀和后缀
                prefixes_to_remove = ['角色：', '人物：', '角色有：', '人物有：', '提取到的角色：', '提取的角色：']
                for prefix in prefixes_to_remove:
                    if characters_text.startswith(prefix):
                        characters_text = characters_text[len(prefix):].strip()
                
                # 分割角色并去重
                if '、' in characters_text:
                    characters = [char.strip() for char in characters_text.split('、') if char.strip()]
                elif '，' in characters_text:
                    characters = [char.strip() for char in characters_text.split('，') if char.strip()]
                elif ',' in characters_text:
                    characters = [char.strip() for char in characters_text.split(',') if char.strip()]
                else:
                    characters = [characters_text] if characters_text else []
                
                # 标准化角色名称并去重过滤空值
                normalized_characters = []
                for char in characters:
                    if char and len(char.strip()) > 0:
                        normalized_name = CharacterDetectionConfig.normalize_character_name(char.strip())
                        normalized_characters.append(normalized_name)
                
                unique_characters = list(dict.fromkeys(normalized_characters))
                
                result = '、'.join(unique_characters)
                logger.info(f"LLM提取角色成功: {result}")
                return result
            else:
                logger.warning("LLM返回空响应，使用后备方案")
                return self._extract_characters_fallback(description)
                
        except Exception as e:
            logger.error(f"LLM角色提取失败: {e}，使用后备方案")
            return self._extract_characters_fallback(description)
    
    def _extract_characters_fallback(self, description: str) -> str:
        """
        智能备用角色提取方法
        
        Args:
            description: 画面描述文本
            
        Returns:
            str: 角色列表字符串，用顿号分隔
        """
        characters = []
        
        # 使用多层次智能角色识别策略
        import re
        
        # 第一层：智能复合角色名称识别
        characters.extend(self._extract_compound_characters(description))
        
        # 第二层：语义角色关系识别
        characters.extend(self._extract_semantic_characters(description))
        
        # 第三层：传统关键词匹配（仅在前两层未找到时使用）
        if not characters:
            characters.extend(self._extract_keyword_characters(description))
        
        # 去重并保持顺序
        unique_characters = []
        seen = set()
        for char in characters:
            if char and char not in seen:
                unique_characters.append(char)
                seen.add(char)
        
        logger.debug(f"智能备用角色提取结果: {unique_characters}")
        return '、'.join(unique_characters) if unique_characters else ''
    
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
    
    def update_llm_api(self, llm_api):
        """
        更新LLM API实例
        
        Args:
            llm_api: 新的LLM API实例
        """
        self.llm_api = llm_api
    
    def update_cs_manager(self, cs_manager):
        """
        更新角色场景管理器实例
        
        Args:
            cs_manager: 新的角色场景管理器实例
        """
        self.cs_manager = cs_manager