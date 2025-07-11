#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CogVideoX专用提示词优化器
基于官方最佳实践优化视频生成提示词
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from src.utils.logger import logger

class CogVideoXPromptOptimizer:
    """CogVideoX提示词优化器"""
    
    def __init__(self):
        # CogVideoX最佳实践模板
        self.video_templates = {
            'character_action': "{character} {action_verb} {action_detail} in {scene}. {camera_movement} {lighting} {mood}",
            'scene_description': "A {shot_type} shot of {scene} where {main_action}. {visual_details} {atmosphere}",
            'motion_focused': "{subject} {motion_verb} {motion_detail}. The camera {camera_action} to capture {visual_focus}",
        }
        
        # 动作动词库（适合视频生成）
        self.action_verbs = {
            '坐着': 'sits peacefully',
            '站立': 'stands gracefully', 
            '走路': 'walks slowly',
            '抚摸': 'gently strokes',
            '看着': 'gazes at',
            '微笑': 'smiles warmly',
            '准备': 'carefully prepares',
            '搅拌': 'stirs gently',
            '交谈': 'converses quietly',
            '离开': 'walks away slowly',
            '回来': 'returns home',
            '拿着': 'holds carefully',
            '翻开': 'opens slowly',
            '依偎': 'snuggles close',
            '期待': 'looks expectantly'
        }
        
        # 运动描述
        self.motion_descriptions = {
            'gentle': 'with gentle, flowing movements',
            'peaceful': 'in a calm, peaceful manner',
            'warm': 'with warm, caring gestures',
            'slow': 'with slow, deliberate motions',
            'natural': 'with natural, lifelike movements',
            'subtle': 'with subtle, nuanced expressions'
        }
        
        # 摄像机运动
        self.camera_movements = {
            'static': 'The camera remains steady',
            'slow_zoom': 'The camera slowly zooms in',
            'pan': 'The camera gently pans',
            'tilt': 'The camera tilts slightly',
            'dolly': 'The camera moves smoothly forward'
        }
        
        # 光照和氛围
        self.lighting_moods = {
            'warm_natural': 'Warm natural lighting creates a cozy atmosphere',
            'soft_golden': 'Soft golden hour light bathes the scene',
            'gentle_indoor': 'Gentle indoor lighting provides warmth',
            'morning_light': 'Fresh morning light illuminates the scene',
            'peaceful_shade': 'Peaceful shade creates a serene mood'
        }
        
        # 视觉质量描述符
        self.quality_descriptors = [
            "cinematic quality",
            "highly detailed",
            "photorealistic",
            "professional cinematography",
            "film grain texture",
            "depth of field",
            "4K resolution"
        ]
    
    def optimize_prompt(self, original_prompt: str, shot_info: Dict = None) -> str:
        """
        优化提示词以适合CogVideoX

        Args:
            original_prompt: 原始提示词
            shot_info: 镜头信息字典

        Returns:
            优化后的英文提示词
        """
        try:
            # 清理原始提示词
            cleaned_prompt = self._clean_original_prompt(original_prompt)

            # 提取关键信息
            scene_info = self._extract_scene_info(cleaned_prompt, shot_info)

            # 构建优化的提示词
            optimized_prompt = self._build_optimized_prompt(scene_info)

            # 添加技术质量描述
            final_prompt = self._add_quality_descriptors(optimized_prompt)

            logger.info(f"提示词优化完成: {len(original_prompt)} -> {len(final_prompt)} 字符")
            return final_prompt

        except Exception as e:
            logger.error(f"提示词优化失败: {e}")
            # 返回基础优化版本
            return self._basic_optimization(original_prompt)

    def optimize_for_video(self, image_prompt: str, shot_info: Dict = None, duration: float = 5.0) -> str:
        """
        专门为视频生成优化提示词

        Args:
            image_prompt: 图像生成的提示词
            shot_info: 镜头信息字典
            duration: 视频时长

        Returns:
            优化后的视频生成提示词
        """
        try:
            # 清理图像提示词，移除静态描述但保留核心内容
            cleaned_prompt = self._clean_for_video(image_prompt)

            # 提取关键信息
            scene_info = self._extract_scene_info(cleaned_prompt, shot_info)

            # 构建视频专用提示词，传递清理后的内容
            video_prompt = self._build_video_prompt(scene_info, duration, cleaned_prompt)

            # 添加视频质量描述
            final_prompt = self._add_video_quality_descriptors(video_prompt)

            logger.info(f"视频提示词优化完成: {len(image_prompt)} -> {len(final_prompt)} 字符")
            logger.debug(f"原始: {image_prompt}")
            logger.debug(f"清理后: {cleaned_prompt}")
            logger.debug(f"最终: {final_prompt}")
            return final_prompt

        except Exception as e:
            logger.error(f"视频提示词优化失败: {e}")
            # 返回基础视频优化版本
            return self._basic_video_optimization(image_prompt)
    
    def _clean_original_prompt(self, prompt: str) -> str:
        """清理原始提示词"""
        # 移除重复的技术参数
        technical_terms = [
            '电影感', '超写实', '4K', '胶片颗粒', '景深',
            '技术细节补充', '全景', '中景', '特写', '平视', '俯视', '侧面',
            '静止', '自然光', '三分法', '对称', '对角线'
        ]
        
        cleaned = prompt
        for term in technical_terms:
            cleaned = re.sub(f'{term}[；;，,。.]*', '', cleaned)
        
        # 移除多余的标点和空格
        cleaned = re.sub(r'[，。；;]+', ', ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _extract_scene_info(self, prompt: str, shot_info: Dict = None) -> Dict:
        """提取场景信息"""
        info = {
            'characters': [],
            'actions': [],
            'scene': '',
            'objects': [],
            'mood': 'peaceful',
            'shot_type': 'medium shot'
        }

        # 提取角色（扩展识别）
        if '阿福' in prompt:
            info['characters'].append('an elderly Chinese man named Afu')
        if '小咪' in prompt:
            info['characters'].append('a black and white cat named Xiaomi')
        if '林海' in prompt:
            info['characters'].append('an elderly sailor named Lin Hai')
        if '小雨' in prompt:
            info['characters'].append('a young girl named Xiao Yu')
        if '老水手' in prompt or '水手' in prompt:
            info['characters'].append('an elderly sailor')
        if '老人' in prompt:
            info['characters'].append('an elderly man')

        # 提取场景（扩展识别）
        if '小院' in prompt or '院子' in prompt:
            info['scene'] = 'in a quiet traditional Chinese courtyard'
        elif '厨房' in prompt:
            info['scene'] = 'in a warm traditional kitchen'
        elif '市场' in prompt:
            info['scene'] = 'in a bustling traditional market'
        elif '海面' in prompt or '海洋' in prompt or '大海' in prompt:
            info['scene'] = 'on the vast ocean'
        elif '船' in prompt or '渔船' in prompt:
            info['scene'] = 'on a fishing boat'
        elif '海底' in prompt:
            info['scene'] = 'in the underwater world'
        elif '城市' in prompt:
            info['scene'] = 'in an ancient city'

        # 提取动作（扩展识别）
        action_mappings = {
            '坐着': 'sitting peacefully',
            '站着': 'standing calmly',
            '抚摸': 'gently stroking',
            '看着': 'looking at',
            '微笑': 'smiling warmly',
            '紧握': 'gripping tightly',
            '望向': 'gazing towards',
            '回想': 'reminiscing about',
            '摇晃': 'swaying gently',
            '升起': 'rising slowly',
            '闪烁': 'flickering softly',
            '流露': 'showing expression',
            '牵起': 'holding hands'
        }

        for chinese, english in action_mappings.items():
            if chinese in prompt:
                info['actions'].append(english)

        # 从shot_info获取技术信息
        if shot_info:
            info['shot_type'] = shot_info.get('shot_type', 'medium shot')
            info['camera_angle'] = shot_info.get('camera_angle', 'eye level')

        return info
    
    def _build_optimized_prompt(self, scene_info: Dict) -> str:
        """构建优化的提示词"""
        parts = []
        
        # 主要描述
        if scene_info['characters'] and scene_info['actions']:
            character = scene_info['characters'][0]
            action = scene_info['actions'][0] if scene_info['actions'] else 'sits peacefully'
            scene = scene_info['scene'] or 'a serene environment'
            
            main_desc = f"{character} {action} in {scene}"
            parts.append(main_desc)
        
        # 添加运动描述
        motion = self.motion_descriptions.get('gentle', 'with gentle movements')
        parts.append(motion)
        
        # 添加摄像机运动
        camera = self.camera_movements.get('static', 'The camera remains steady')
        parts.append(camera)
        
        # 添加光照氛围
        lighting = self.lighting_moods.get('warm_natural', 'Warm natural lighting')
        parts.append(lighting)
        
        return '. '.join(parts)
    
    def _add_quality_descriptors(self, prompt: str) -> str:
        """添加质量描述符"""
        # 选择适合的质量描述符
        quality_parts = [
            "cinematic quality",
            "highly detailed", 
            "photorealistic",
            "film grain texture",
            "depth of field"
        ]
        
        quality_str = ', '.join(quality_parts)
        return f"{prompt}. {quality_str}"
    
    def _basic_optimization(self, prompt: str) -> str:
        """基础优化（备用方案）"""
        # 简单的中英文转换和优化
        basic_translations = {
            '阿福': 'an elderly Chinese man',
            '小咪': 'a black and white cat',
            '小院': 'a traditional courtyard',
            '厨房': 'a warm kitchen',
            '市场': 'a bustling market',
            '坐着': 'sitting peacefully',
            '抚摸': 'gently stroking',
            '看着': 'looking at',
            '微笑': 'smiling warmly'
        }
        
        result = prompt
        for chinese, english in basic_translations.items():
            result = result.replace(chinese, english)
        
        # 添加基础质量描述
        result += ". cinematic quality, highly detailed, photorealistic"
        
        return result

    def _clean_for_video(self, image_prompt: str) -> str:
        """清理图像提示词以适合视频生成，保留核心内容"""
        # 移除静态描述词和技术参数
        static_terms = [
            '静止的画面中', '画面静止', '静谧', '静态构图', 'static composition',
            '水彩画风', '柔和笔触', '粉彩色调', '插画风格', '温柔的氛围',
            '三分法构图', '对称构图', '对角线构图', '构图更显',
            '电影感', '超写实', '4K画质', '胶片颗粒感', '景深效果',
            '技术细节补充', '画面遵循', '静止'
        ]

        cleaned = image_prompt

        # 移除技术参数部分（如：：中景; 平视; 静止; 人工光; 对称）
        cleaned = re.sub(r'：[^，。；;]*?[;；][^，。；;]*?[;；][^，。；;]*?[;；][^，。；;]*?[;；][^，。；;]*', '', cleaned)
        cleaned = re.sub(r'：[^，。；;]*', '', cleaned)  # 移除剩余的技术参数

        # 移除静态描述词
        for term in static_terms:
            cleaned = re.sub(f'{re.escape(term)}[，。；;]*', '', cleaned)

        # 移除多余的标点和空格，但保持基本结构
        cleaned = re.sub(r'[，。；;]{2,}', '，', cleaned)  # 多个标点符号合并为一个
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'^[，。；;]+|[，。；;]+$', '', cleaned)  # 移除开头结尾的标点

        return cleaned

    def _build_video_prompt(self, scene_info: Dict, duration: float, cleaned_content: str = "") -> str:
        """构建视频专用提示词，保留原始内容"""
        parts = []

        # 如果有清理后的内容，优先使用
        if cleaned_content and cleaned_content.strip():
            # 保留原始内容作为基础
            base_content = cleaned_content.strip()

            # 根据时长添加运动描述（避免重复）
            if duration <= 3:
                motion_desc = "subtle natural movements"
            elif duration <= 6:
                motion_desc = "gentle flowing motion"
            else:
                motion_desc = "smooth continuous motion"

            # 将运动描述融入原始内容
            main_desc = f"{base_content}, {motion_desc}"
            parts.append(main_desc)

        elif scene_info['characters'] or scene_info['scene'] or scene_info['actions']:
            # 如果没有原始内容，但有提取的场景信息，构建描述
            scene_elements = []

            if scene_info['characters']:
                scene_elements.append(scene_info['characters'][0])

            if scene_info['actions']:
                action = scene_info['actions'][0]
            else:
                action = 'moves naturally'

            if scene_info['scene']:
                scene_location = scene_info['scene']
            else:
                scene_location = 'in a peaceful environment'

            # 根据时长调整动作描述
            if duration <= 3:
                motion_desc = "with subtle movements"
            elif duration <= 6:
                motion_desc = "with gentle, flowing movements"
            else:
                motion_desc = "with smooth, continuous movements"

            # 组合场景描述
            if scene_elements:
                main_desc = f"{' '.join(scene_elements)} {action} {scene_location} {motion_desc}"
            else:
                main_desc = f"A scene {scene_location} with natural {action} {motion_desc}"

            parts.append(main_desc)
        else:
            # 最后的备用方案
            if duration <= 3:
                motion_desc = "subtle movements"
            elif duration <= 6:
                motion_desc = "gentle, flowing movements"
            else:
                motion_desc = "smooth, continuous movements"

            parts.append(f"A peaceful scene with {motion_desc}")

        # 添加摄像机运动（根据时长选择）
        if duration <= 3:
            camera_desc = "steady camera"
        elif duration <= 6:
            camera_desc = "gentle camera panning"
        else:
            camera_desc = "dynamic camera movement"

        parts.append(camera_desc)

        # 添加基础视频质量描述（避免重复）
        parts.append("cinematic quality")

        return '. '.join(parts)

    def _add_video_quality_descriptors(self, prompt: str) -> str:
        """添加视频质量描述符，避免重复"""
        # 检查已有的关键词，避免重复
        existing_keywords = prompt.lower()

        # 视频专用质量描述符
        video_quality_parts = []

        # 只添加不重复的描述符
        if 'motion' not in existing_keywords and 'movement' not in existing_keywords:
            video_quality_parts.append("fluid motion")

        if 'cinematic' not in existing_keywords:
            video_quality_parts.append("cinematic flow")

        if 'quality' not in existing_keywords:
            video_quality_parts.append("high quality video")

        # 总是添加的专业描述符
        video_quality_parts.extend(["stable footage", "professional grade"])

        # 限制长度，选择最重要的3-4个
        quality_str = ', '.join(video_quality_parts[:4])
        return f"{prompt}. {quality_str}" if quality_str else prompt

    def _basic_video_optimization(self, image_prompt: str) -> str:
        """基础视频优化（备用方案）"""
        # 简单清理静态描述
        cleaned = self._clean_for_video(image_prompt)

        # 添加基础动作描述
        if not any(word in cleaned.lower() for word in ['move', 'motion', 'flow', 'gentle']):
            cleaned += ", with gentle natural movements"

        # 添加基础视频质量描述
        cleaned += ". smooth motion, cinematic flow, high quality video"

        return cleaned

    def batch_optimize_prompts(self, prompt_file_path: str) -> bool:
        """批量优化prompt.json文件中的提示词"""
        try:
            # 读取prompt.json
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            optimized_count = 0
            
            # 遍历所有场景和镜头
            for scene_name, shots in data.get('scenes', {}).items():
                for shot in shots:
                    if 'content' in shot:
                        original = shot['content']
                        
                        # 提取镜头信息
                        shot_info = self._extract_shot_info_from_description(
                            shot.get('original_description', '')
                        )
                        
                        # 优化提示词
                        optimized = self.optimize_prompt(original, shot_info)
                        
                        # 保存优化结果
                        shot['optimized_content'] = optimized
                        optimized_count += 1
                        
                        logger.info(f"优化镜头提示词: {shot.get('shot_number', 'Unknown')}")
            
            # 保存优化后的文件
            backup_path = prompt_file_path + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            with open(prompt_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"批量优化完成: {optimized_count} 个提示词已优化")
            return True
            
        except Exception as e:
            logger.error(f"批量优化失败: {e}")
            return False
    
    def _extract_shot_info_from_description(self, description: str) -> Dict:
        """从原始描述中提取镜头信息"""
        info = {}
        
        # 提取镜头类型
        if '全景' in description:
            info['shot_type'] = 'wide shot'
        elif '中景' in description:
            info['shot_type'] = 'medium shot'
        elif '特写' in description:
            info['shot_type'] = 'close-up shot'
        
        # 提取机位角度
        if '平视' in description:
            info['camera_angle'] = 'eye level'
        elif '俯视' in description:
            info['camera_angle'] = 'high angle'
        elif '仰视' in description:
            info['camera_angle'] = 'low angle'
        
        return info
