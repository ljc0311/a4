# -*- coding: utf-8 -*-
"""
配音-图像内容匹配器
解决配音内容与生成图像不匹配的问题
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ContentAnalysis:
    """内容分析结果"""
    main_subject: str  # 主要主体
    action: str        # 动作描述
    scene: str         # 场景描述
    emotion: str       # 情感色彩
    keywords: List[str]  # 关键词
    time_context: str  # 时间背景
    
class VoiceImageMatcher:
    """配音-图像内容匹配器"""
    
    def __init__(self, llm_api=None):
        self.llm_api = llm_api
        
        # 内容分析关键词库
        self.subject_keywords = {
            '人物': ['我', '他', '她', '大家', '朋友', '同学', '老师', '父母', '孩子'],
            '地点': ['家', '学校', '公园', '商店', '医院', '办公室', '餐厅', '图书馆'],
            '物品': ['书', '电脑', '手机', '汽车', '食物', '衣服', '玩具', '工具'],
            '动物': ['狗', '猫', '鸟', '鱼', '马', '牛', '羊', '兔子']
        }
        
        self.action_keywords = {
            '移动': ['走', '跑', '飞', '游', '爬', '跳', '开车', '骑车'],
            '交流': ['说', '讲', '聊', '谈', '问', '答', '笑', '哭'],
            '工作': ['写', '读', '学', '教', '做', '修', '建', '画'],
            '生活': ['吃', '喝', '睡', '洗', '穿', '买', '玩', '看']
        }
        
        self.scene_keywords = {
            '室内': ['房间', '客厅', '卧室', '厨房', '办公室', '教室', '商店'],
            '室外': ['街道', '公园', '山', '海', '田野', '花园', '广场'],
            '自然': ['森林', '河流', '湖泊', '草原', '沙漠', '雪山', '海滩'],
            '城市': ['大楼', '马路', '桥梁', '车站', '机场', '商场', '医院']
        }
        
        self.emotion_keywords = {
            '积极': ['开心', '快乐', '兴奋', '满意', '骄傲', '感动', '温暖'],
            '消极': ['难过', '生气', '害怕', '担心', '失望', '孤独', '冷漠'],
            '中性': ['平静', '思考', '专注', '认真', '普通', '日常', '简单']
        }
    
    def analyze_voice_content(self, voice_content: str) -> ContentAnalysis:
        """分析配音内容，提取关键信息"""
        try:
            # 清理文本
            content = self._clean_text(voice_content)
            
            # 提取各类信息
            main_subject = self._extract_main_subject(content)
            action = self._extract_action(content)
            scene = self._extract_scene(content)
            emotion = self._extract_emotion(content)
            keywords = self._extract_keywords(content)
            time_context = self._extract_time_context(content)
            
            return ContentAnalysis(
                main_subject=main_subject,
                action=action,
                scene=scene,
                emotion=emotion,
                keywords=keywords,
                time_context=time_context
            )
            
        except Exception as e:
            logger.error(f"分析配音内容失败: {e}")
            return ContentAnalysis(
                main_subject="人物",
                action="日常活动",
                scene="室内场景",
                emotion="中性",
                keywords=[],
                time_context="现在"
            )
    
    def generate_matched_image_prompt(self, voice_content: str, image_index: int = 0, total_images: int = 1) -> str:
        """基于配音内容生成匹配的图像提示词"""
        try:
            # 分析配音内容
            analysis = self.analyze_voice_content(voice_content)
            
            # 根据图像索引调整焦点
            if total_images > 1:
                focus = self._determine_image_focus(voice_content, image_index, total_images)
            else:
                focus = "complete_scene"
            
            # 构建图像提示词
            prompt = self._build_image_prompt(analysis, focus)
            
            # 使用LLM增强（如果可用）
            if self.llm_api:
                enhanced_prompt = self._enhance_with_llm(prompt, voice_content)
                if enhanced_prompt:
                    prompt = enhanced_prompt
            
            logger.info(f"生成匹配图像提示词: {prompt[:50]}...")
            return prompt
            
        except Exception as e:
            logger.error(f"生成匹配图像提示词失败: {e}")
            return f"根据内容生成画面: {voice_content[:30]}..., 高质量, 细节丰富"
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除标点符号和多余空格
        text = re.sub(r'[，。！？；：""''（）【】]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _extract_main_subject(self, content: str) -> str:
        """提取主要主体"""
        for category, keywords in self.subject_keywords.items():
            for keyword in keywords:
                if keyword in content:
                    return f"{category}({keyword})"
        return "人物"
    
    def _extract_action(self, content: str) -> str:
        """提取动作描述"""
        for category, keywords in self.action_keywords.items():
            for keyword in keywords:
                if keyword in content:
                    return f"{category}({keyword})"
        return "日常活动"
    
    def _extract_scene(self, content: str) -> str:
        """提取场景描述"""
        for category, keywords in self.scene_keywords.items():
            for keyword in keywords:
                if keyword in content:
                    return f"{category}({keyword})"
        return "室内场景"
    
    def _extract_emotion(self, content: str) -> str:
        """提取情感色彩"""
        for category, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                if keyword in content:
                    return category
        return "中性"
    
    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        keywords = []
        # 提取所有匹配的关键词
        for category_dict in [self.subject_keywords, self.action_keywords, 
                             self.scene_keywords, self.emotion_keywords]:
            for category, word_list in category_dict.items():
                for word in word_list:
                    if word in content:
                        keywords.append(word)
        return list(set(keywords))
    
    def _extract_time_context(self, content: str) -> str:
        """提取时间背景"""
        time_keywords = {
            '早晨': ['早上', '清晨', '黎明', '日出'],
            '白天': ['白天', '中午', '下午', '阳光'],
            '傍晚': ['傍晚', '黄昏', '日落', '夕阳'],
            '夜晚': ['晚上', '夜里', '深夜', '月亮', '星星'],
            '季节': ['春天', '夏天', '秋天', '冬天', '雪', '花']
        }
        
        for time_type, keywords in time_keywords.items():
            for keyword in keywords:
                if keyword in content:
                    return f"{time_type}({keyword})"
        return "现在"
    
    def _determine_image_focus(self, content: str, image_index: int, total_images: int) -> str:
        """确定图像焦点"""
        if total_images == 1:
            return "complete_scene"
        elif image_index == 0:
            return "opening_scene"  # 开场场景
        elif image_index == total_images - 1:
            return "closing_scene"  # 结尾场景
        else:
            return "middle_scene"   # 中间场景
    
    def _build_image_prompt(self, analysis: ContentAnalysis, focus: str) -> str:
        """构建图像提示词"""
        try:
            # 基础描述
            base_parts = []
            
            # 添加主体
            if analysis.main_subject:
                base_parts.append(analysis.main_subject)
            
            # 添加动作（根据焦点调整）
            if analysis.action:
                if focus == "opening_scene":
                    base_parts.append(f"开始{analysis.action}")
                elif focus == "closing_scene":
                    base_parts.append(f"结束{analysis.action}")
                else:
                    base_parts.append(analysis.action)
            
            # 添加场景
            if analysis.scene:
                base_parts.append(f"在{analysis.scene}")
            
            # 添加时间背景
            if analysis.time_context and analysis.time_context != "现在":
                base_parts.append(analysis.time_context)
            
            # 组合基础描述
            base_description = "，".join(base_parts)
            
            # 添加情感和风格
            emotion_style = self._get_emotion_style(analysis.emotion)
            style_suffix = "，高质量，细节丰富，专业摄影"
            
            return f"{base_description}，{emotion_style}{style_suffix}"
            
        except Exception as e:
            logger.error(f"构建图像提示词失败: {e}")
            return "温馨的日常场景，高质量，细节丰富"
    
    def _get_emotion_style(self, emotion: str) -> str:
        """根据情感获取风格描述"""
        emotion_styles = {
            '积极': "温暖明亮的色调，充满活力",
            '消极': "柔和暗淡的色调，情感深沉",
            '中性': "自然平衡的色调，真实感"
        }
        return emotion_styles.get(emotion, "自然的色调")
    
    def _enhance_with_llm(self, base_prompt: str, voice_content: str) -> Optional[str]:
        """使用LLM增强提示词"""
        try:
            if not self.llm_api:
                return None
            
            enhancement_prompt = f"""
请根据以下配音内容，优化图像生成提示词，确保图像内容与配音内容高度匹配：

配音内容：{voice_content}

当前提示词：{base_prompt}

要求：
1. 图像内容必须与配音内容直接相关
2. 保持提示词的专业性和准确性
3. 添加适当的视觉细节
4. 确保风格统一
5. 只输出优化后的提示词，不要其他说明

优化后的提示词："""
            
            enhanced = self.llm_api.rewrite_text(enhancement_prompt)
            if enhanced and len(enhanced.strip()) > 10:
                return enhanced.strip()
            
        except Exception as e:
            logger.debug(f"LLM增强失败: {e}")
        
        return None
    
    def batch_generate_matched_prompts(self, voice_segments: List[Dict]) -> List[Dict]:
        """批量生成匹配的图像提示词"""
        try:
            results = []
            
            for i, segment in enumerate(voice_segments):
                voice_content = segment.get('dialogue_text', segment.get('voice_content', ''))
                
                # 计算该段落需要的图像数量（基于时长）
                duration = segment.get('duration', 3.0)
                image_count = self._calculate_image_count(duration)
                
                # 为每张图像生成提示词
                segment_images = []
                for img_idx in range(image_count):
                    prompt = self.generate_matched_image_prompt(
                        voice_content, img_idx, image_count
                    )
                    
                    segment_images.append({
                        'sequence': f"{segment.get('scene_id', 'S1')}_{segment.get('shot_id', f'P{i+1}')}_{img_idx+1}",
                        'scene_id': segment.get('scene_id', 'S1'),
                        'shot_id': segment.get('shot_id', f'P{i+1}'),
                        'image_index': img_idx,
                        'description': prompt,
                        'enhanced_description': prompt,
                        'voice_content': voice_content,
                        'duration_start': img_idx * (duration / image_count),
                        'duration_end': (img_idx + 1) * (duration / image_count),
                        'status': '待生成'
                    })
                
                results.extend(segment_images)
            
            logger.info(f"批量生成完成，共 {len(results)} 个图像提示词")
            return results
            
        except Exception as e:
            logger.error(f"批量生成匹配提示词失败: {e}")
            return []
    
    def _calculate_image_count(self, duration: float) -> int:
        """🔧 修改：每个配音段落只生成1张图片，确保配音数量与图片数量一致"""
        return 1
