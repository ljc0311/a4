#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
颜色优化工具
用于处理角色服装颜色，确保每个角色只保留一个主要颜色
"""

import re
from typing import List, Dict, Any, Optional
from .logger import logger

class ColorOptimizer:
    """颜色优化器 - 处理角色服装颜色一致性"""
    
    def __init__(self):
        # 定义颜色优先级（常见的主要颜色）
        self.color_priority = {
            # 基础颜色（高优先级）
            '黑色': 10, '白色': 9, '红色': 10, '蓝色': 9, '绿色': 8,
            '黄色': 8, '紫色': 7, '橙色': 7, '粉色': 6, '灰色': 6,
            '棕色': 5, '褐色': 5, '咖啡色': 5,

            # 深浅变化（中优先级）
            '深蓝': 8, '浅蓝': 7, '深红': 8, '浅红': 6,
            '深绿': 7, '浅绿': 6, '深灰': 6, '浅灰': 5,
            '深紫': 6, '浅紫': 5, '深黄': 7, '浅黄': 5,
            '深蓝色': 8, '浅蓝色': 7, '深红色': 8, '浅红色': 6,
            '深绿色': 7, '浅绿色': 6, '深灰色': 6, '浅灰色': 5,
            '深紫色': 6, '浅紫色': 5, '深黄色': 7, '浅黄色': 5,

            # 特殊颜色（低优先级）
            '金色': 4, '银色': 4, '米色': 3, '卡其色': 3,
            '青色': 3, '洋红': 3, '橄榄色': 2, '海军蓝': 4,
            '天蓝': 4, '草绿': 3, '玫瑰红': 3, '暗绿色': 3
        }
        
        # 颜色关键词模式
        self.color_patterns = [
            r'(深|浅|亮|暗)?(黑|白|红|蓝|绿|黄|紫|橙|粉|灰|棕|褐|咖啡)色?',
            r'(金|银|米|卡其|青|洋红|橄榄|海军蓝|天蓝|草绿|玫瑰红)色?',
            r'(navy|blue|red|green|yellow|purple|orange|pink|gray|brown|black|white|gold|silver)',
            r'颜色'  # 特殊处理"颜色"这个词
        ]
    
    def extract_primary_color(self, color_text: str) -> str:
        """从颜色文本中提取主要颜色
        
        Args:
            color_text: 包含颜色信息的文本
            
        Returns:
            str: 主要颜色
        """
        if not color_text or not isinstance(color_text, str):
            return ""
        
        # 如果是列表格式，先转换为字符串
        if color_text.startswith('[') and color_text.endswith(']'):
            try:
                import ast
                color_list = ast.literal_eval(color_text)
                if isinstance(color_list, list) and color_list:
                    color_text = ', '.join(str(c) for c in color_list)
            except:
                pass
        
        # 提取所有颜色
        colors = self._extract_colors_from_text(color_text)
        
        if not colors:
            return ""
        
        # 如果只有一个颜色，直接返回
        if len(colors) == 1:
            return colors[0]
        
        # 选择优先级最高的颜色
        primary_color = self._select_primary_color(colors)
        
        logger.info(f"从 '{color_text}' 中提取主要颜色: {primary_color}")
        return primary_color
    
    def _extract_colors_from_text(self, text: str) -> List[str]:
        """从文本中提取所有颜色"""
        colors = []

        # 先按逗号分割
        parts = [part.strip() for part in text.split(',')]

        for part in parts:
            # 特殊处理"颜色"这个词
            if part.strip() == '颜色':
                colors.append('颜色')
                continue

            # 使用正则表达式匹配颜色
            for pattern in self.color_patterns:
                matches = re.findall(pattern, part, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        # 处理分组匹配
                        color = ''.join(match).strip()
                    else:
                        color = match.strip()

                    if color and color not in colors:
                        # 标准化颜色名称
                        normalized_color = self._normalize_color_name(color)
                        if normalized_color:
                            colors.append(normalized_color)

        return colors
    
    def _normalize_color_name(self, color: str) -> str:
        """标准化颜色名称"""
        if not color:
            return ""

        color = color.lower().strip()

        # 移除"色"字
        if color.endswith('色'):
            color = color[:-1]

        # 颜色映射
        color_mapping = {
            'black': '黑色', 'white': '白色', 'red': '红色', 'blue': '蓝色',
            'green': '绿色', 'yellow': '黄色', 'purple': '紫色', 'orange': '橙色',
            'pink': '粉色', 'gray': '灰色', 'grey': '灰色', 'brown': '棕色',
            'gold': '金色', 'silver': '银色', 'navy': '海军蓝',
            '深蓝': '深蓝色', '浅蓝': '浅蓝色', '深红': '深红色', '浅红': '浅红色',
            '深绿': '深绿色', '浅绿': '浅绿色', '深灰': '深灰色', '浅灰': '浅灰色',
            '暗绿': '暗绿色'
        }

        # 查找映射
        for key, value in color_mapping.items():
            if key == color or color == key:
                return value

        # 特殊处理"颜色"这个词
        if color == '颜色':
            return '颜色'

        # 如果没有找到映射，检查是否在优先级列表中
        for priority_color in self.color_priority.keys():
            if color == priority_color.lower().replace('色', ''):
                return priority_color

        # 检查是否是有效的颜色词
        valid_color_chars = set('红橙黄绿青蓝紫黑白灰棕褐金银粉深浅亮暗')
        if any(char in valid_color_chars for char in color):
            # 如果包含颜色字符，返回加上"色"字的版本
            if not color.endswith('色'):
                return color + '色'
            return color

        # 如果都没找到且不是有效颜色，返回空字符串
        return ""
    
    def _select_primary_color(self, colors: List[str]) -> str:
        """从多个颜色中选择主要颜色"""
        if not colors:
            return ""
        
        if len(colors) == 1:
            return colors[0]
        
        # 按优先级排序
        color_scores = []
        for color in colors:
            score = self.color_priority.get(color, 1)
            color_scores.append((color, score))
        
        # 按分数降序排序
        color_scores.sort(key=lambda x: x[1], reverse=True)
        
        return color_scores[0][0]
    
    def optimize_character_colors(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """优化角色颜色数据
        
        Args:
            character_data: 角色数据字典
            
        Returns:
            Dict[str, Any]: 优化后的角色数据
        """
        try:
            # 复制数据以避免修改原始数据
            optimized_data = character_data.copy()
            
            # 处理服装颜色
            clothing = optimized_data.get('clothing', {})
            if isinstance(clothing, dict):
                colors = clothing.get('colors', [])
                
                # 如果colors是字符串，先转换
                if isinstance(colors, str):
                    primary_color = self.extract_primary_color(colors)
                    if primary_color:
                        clothing['colors'] = [primary_color]
                    else:
                        clothing['colors'] = []
                elif isinstance(colors, list) and len(colors) > 1:
                    # 如果有多个颜色，选择主要颜色
                    color_text = ', '.join(str(c) for c in colors)
                    primary_color = self.extract_primary_color(color_text)
                    if primary_color:
                        clothing['colors'] = [primary_color]
                    else:
                        clothing['colors'] = colors[:1]  # 保留第一个
                
                optimized_data['clothing'] = clothing
            
            return optimized_data
            
        except Exception as e:
            logger.error(f"优化角色颜色失败: {e}")
            return character_data
    
    def get_character_primary_color(self, character_data: Dict[str, Any]) -> str:
        """获取角色的主要服装颜色
        
        Args:
            character_data: 角色数据
            
        Returns:
            str: 主要颜色
        """
        try:
            clothing = character_data.get('clothing', {})
            if isinstance(clothing, dict):
                colors = clothing.get('colors', [])
                
                if isinstance(colors, str):
                    return self.extract_primary_color(colors)
                elif isinstance(colors, list) and colors:
                    return colors[0]  # 返回第一个颜色
            
            return ""
            
        except Exception as e:
            logger.error(f"获取角色主要颜色失败: {e}")
            return ""
    
    def apply_color_consistency_to_description(self, description: str,
                                             character_name: str,
                                             primary_color: str) -> str:
        """将颜色一致性应用到描述中

        Args:
            description: 原始描述
            character_name: 角色名称（用于日志记录）
            primary_color: 主要颜色

        Returns:
            str: 应用颜色一致性后的描述
        """
        if not description or not primary_color:
            return description

        try:
            enhanced_description = description
            original_description = description  # 保存原始描述用于比较

            # 确保主要颜色格式正确（以"色"结尾）
            if not primary_color.endswith('色'):
                primary_color = primary_color + '色'

            logger.debug(f"开始为角色 {character_name} 应用颜色一致性，主要颜色: {primary_color}")

            # 1. 处理"或"连接的多颜色表达（如"红色或白色的衬衫"）
            or_color_pattern = r'([^，。；！？\s]+色)或([^，。；！？\s]+色)的([^，。；！？\s]+)'
            def replace_or_colors(match):
                _, _, item = match.groups()  # 忽略原有颜色，直接使用主要颜色
                return f'{primary_color}的{item}'

            enhanced_description = re.sub(or_color_pattern, replace_or_colors, enhanced_description)

            # 2. 处理逗号分隔的多颜色表达（如"红色，白色的衬衫"）
            comma_color_pattern = r'([^，。；！？\s]+色)，([^，。；！？\s]+色)的([^，。；！？\s]+)'
            def replace_comma_colors(match):
                _, _, item = match.groups()  # 忽略原有颜色，直接使用主要颜色
                return f'{primary_color}的{item}'

            enhanced_description = re.sub(comma_color_pattern, replace_comma_colors, enhanced_description)
            
            # 3. 智能替换服装颜色描述
            # 定义服装相关词汇
            clothing_keywords = [
                '工作服', '服装', '服饰', '衣服', '袍', '衫', '裙', '裤', '套',
                '帽', '帽子', '鞋', '袜', '带', '巾', '围巾', '围脖', '斗篷', '披风',
                '盔甲', '铠甲', '护甲', '链', '镯', '环', '戒指', '项链', '耳环',
                '胸针', '腰带', '皮带', '手表', '眼镜', '头饰', '发饰', '外套',
                '夹克', '毛衣', '西装', '大衣', 'T恤', '连衣裙', '衬衫', '背心',
                '马甲', '风衣', '羽绒服', '棉衣', '皮衣', '制服', '礼服'
            ]

            # 简化的颜色替换逻辑
            # 1. 替换明确的颜色描述
            all_colors = list(self.color_priority.keys())
            for color in all_colors:
                if color != primary_color:
                    # 替换"颜色+服装"的模式
                    color_clothing_pattern = rf'{re.escape(color)}([^，。；！？\s]*(?:' + '|'.join(clothing_keywords) + r')[^，。；！？\s]*)'
                    enhanced_description = re.sub(color_clothing_pattern, rf'{primary_color}\1', enhanced_description)

                    # 替换"颜色的+服装"的模式
                    color_de_clothing_pattern = rf'{re.escape(color)}的([^，。；！？\s]*(?:' + '|'.join(clothing_keywords) + r')[^，。；！？\s]*)'
                    enhanced_description = re.sub(color_de_clothing_pattern, rf'{primary_color}的\1', enhanced_description)

                    # 替换"颜色的+任何物体"的模式（如"红色的蛇"）
                    color_de_object_pattern = rf'{re.escape(color)}的([^，。；！？\s]+)'
                    enhanced_description = re.sub(color_de_object_pattern, rf'{primary_color}的\1', enhanced_description)

            # 2. 为没有颜色的服装添加颜色（只处理一次）
            for keyword in clothing_keywords:
                # 匹配"动词+形容词+的+服装"模式（如"穿着破旧的工作服"）
                verb_pattern = rf'(穿着|戴着|佩戴着|披着|套着)([^，。；！？\s]*的)?({keyword}[^，。；！？\s]*)'
                def add_color_to_verb_clothing(match):
                    verb, adjective, clothing_item = match.groups()
                    if adjective:
                        return f'{verb}{adjective}{primary_color}{clothing_item}'
                    else:
                        return f'{verb}{primary_color}{clothing_item}'

                # 优先处理动词+服装的模式
                if re.search(verb_pattern, enhanced_description):
                    enhanced_description = re.sub(verb_pattern, add_color_to_verb_clothing, enhanced_description, count=1)
                    break

                # 如果没有动词模式，再处理一般的"形容词+的+服装"模式
                general_pattern = rf'(?<!色)(?<!色的)\b([^，。；！？\s]*的)?({keyword}[^，。；！？\s]*)'
                def add_color_to_general_clothing(match):
                    adjective, clothing_item = match.groups()
                    if adjective:
                        return f'{adjective}{primary_color}{clothing_item}'
                    else:
                        return f'{primary_color}{clothing_item}'

                # 只替换第一个匹配项
                if re.search(general_pattern, enhanced_description):
                    enhanced_description = re.sub(general_pattern, add_color_to_general_clothing, enhanced_description, count=1)
                    break  # 只处理第一个找到的服装
            
            # 4. 为没有颜色修饰的主要服装添加颜色（仅限明确的服装词汇）
            main_clothing_items = ['衬衫', '裙子', '裤子', '外套', '夹克', '毛衣', '西装', '大衣', 'T恤', '连衣裙']
            for item in main_clothing_items:
                # 检查是否已经有颜色修饰
                if not re.search(rf'[^，。；！？\s]*色[的]?{item}', enhanced_description):
                    # 为没有颜色的服装添加颜色，但要确保语法正确
                    no_color_pattern = rf'(?<!色)(?<!色的)\b({item})\b'
                    if re.search(no_color_pattern, enhanced_description):
                        enhanced_description = re.sub(
                            no_color_pattern, 
                            rf'{primary_color}\1', 
                            enhanced_description, 
                            count=1
                        )
                        break  # 只处理第一个找到的服装
            
            # 5. 清理可能的语法错误
            # 修复"颜色的色"这样的重复
            enhanced_description = re.sub(rf'{re.escape(primary_color)}的色', primary_color, enhanced_description)
            # 修复"颜色色"这样的重复
            enhanced_description = re.sub(rf'{re.escape(primary_color)}色', primary_color, enhanced_description)
            # 修复"颜色的颜色"这样的重复
            enhanced_description = re.sub(rf'{re.escape(primary_color)}的{re.escape(primary_color)}', primary_color, enhanced_description)

            # 6. 检查是否有实际变化
            if enhanced_description != original_description:
                logger.info(f"颜色一致性应用成功，主要颜色: {primary_color}")
                logger.debug(f"原始: {original_description}")
                logger.debug(f"优化: {enhanced_description}")
            else:
                logger.debug(f"描述中已经符合颜色一致性要求，无需修改")

            return enhanced_description
            
        except Exception as e:
            logger.error(f"应用颜色一致性失败: {e}")
            return description
    
    def apply_color_consistency(self, description: str, characters: List[str], 
                              character_scene_manager) -> str:
        """应用颜色一致性到场景描述中
        
        Args:
            description: 原始场景描述
            characters: 角色列表
            character_scene_manager: 角色场景管理器
            
        Returns:
            str: 应用颜色一致性后的描述
        """
        if not description or not characters:
            return description
        
        try:
            enhanced_description = description
            
            for character_name in characters:
                # 获取角色数据
                character_data = self._get_character_data_by_name(
                    character_name, character_scene_manager
                )
                
                if character_data:
                    # 获取主要颜色
                    primary_color = self.get_character_primary_color(character_data)
                    
                    if primary_color:
                        # 应用颜色一致性
                        enhanced_description = self.apply_color_consistency_to_description(
                            enhanced_description, character_name, primary_color
                        )
            
            return enhanced_description
            
        except Exception as e:
            logger.error(f"应用颜色一致性失败: {e}")
            return description
    
    def _get_character_data_by_name(self, character_name: str, 
                                   character_scene_manager) -> Optional[Dict[str, Any]]:
        """根据角色名称获取角色数据
        
        Args:
            character_name: 角色名称
            character_scene_manager: 角色场景管理器
            
        Returns:
            Optional[Dict[str, Any]]: 角色数据
        """
        try:
            characters_data = character_scene_manager._load_json(
                character_scene_manager.characters_file
            )
            
            # 查找角色数据
            for char_id, char_data in characters_data.get('characters', {}).items():
                if char_data.get('name') == character_name:
                    return char_data
            
            return None
            
        except Exception as e:
            logger.error(f"获取角色数据失败 {character_name}: {e}")
            return None