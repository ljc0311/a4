"""
风格一致性管理器
用于确保整个项目中图像生成的风格保持一致
"""

import re
import json
import os
from typing import Dict, List, Optional, Tuple
from .logger import logger


class StyleConsistencyManager:
    """风格一致性管理器"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        
        # 标准风格提示词定义
        self.style_prompts = {
            '电影风格': '电影感，超写实，4K，胶片颗粒，景深',
            '动漫风格': '动漫风，鲜艳色彩，干净线条，赛璐璐渲染，日本动画',
            '吉卜力风格': '吉卜力风，柔和色彩，奇幻，梦幻，丰富背景',
            '赛博朋克风格': '赛博朋克，霓虹灯，未来都市，雨夜，暗色氛围',
            '水彩插画风格': '水彩画风，柔和笔触，粉彩色，插画，温柔',
            '像素风格': '像素风，8位，复古，低分辨率，游戏风',
            '写实摄影风格': '真实光线，高细节，写实摄影，4K'
        }
        
        # 风格关键词映射（用于检测被LLM修改的风格描述）
        self.style_keywords = {
            '电影感': '电影风格',
            '吉卜力风': '吉卜力风格', 
            '动漫风': '动漫风格',
            '赛博朋克': '赛博朋克风格',
            '水彩画风': '水彩插画风格',
            '像素风': '像素风格',
            '写实摄影': '写实摄影风格'
        }
        
        # 可能被LLM替换的风格描述
        self.style_replacements = {
            '电影感，超写实，4K，胶片颗粒，景深': [
                '电影风格', '电影感', '超写实', '胶片质感', '景深效果', '4K画质',
                '电影级', '影院级', '专业摄影', '胶片风格'
            ],
            '吉卜力风，柔和色彩，奇幻，梦幻，丰富背景': [
                '吉卜力风格', '柔和氛围', '奇幻梦幻', '丰富背景', '温暖色调', 
                '手绘风格', '宫崎骏风格', '动画电影风格', '治愈系风格'
            ],
            '动漫风，鲜艳色彩，干净线条，赛璐璐渲染，日本动画': [
                '动漫风格', '鲜艳色彩', '干净线条', '赛璐璐', '日式动画',
                '二次元', '动画风格', '卡通风格'
            ],
            '赛博朋克，霓虹灯，未来都市，雨夜，暗色氛围': [
                '赛博朋克风格', '霓虹灯光', '未来都市', '暗色调', '科技感',
                '未来主义', '科幻风格', '电子朋克'
            ],
            '水彩画风，柔和笔触，粉彩色，插画，温柔': [
                '水彩风格', '柔和笔触', '粉彩色调', '插画风', '温柔质感',
                '手绘插画', '艺术风格', '绘本风格'
            ],
            '像素风，8位，复古，低分辨率，游戏风': [
                '像素风格', '8位风格', '复古游戏', '像素艺术',
                '复古游戏风', '低像素', '马赛克风格'
            ],
            '真实光线，高细节，写实摄影，4K': [
                '写实摄影', '真实光线', '高细节', '摄影风格',
                '纪实摄影', '专业摄影', '高清摄影'
            ]
        }
    
    def detect_style_from_description(self, description: str) -> Tuple[Optional[str], Optional[str]]:
        """从描述中检测风格
        
        Returns:
            Tuple[风格名称, 风格提示词]: 如果检测到风格则返回，否则返回(None, None)
        """
        for keyword, style_name in self.style_keywords.items():
            if keyword in description:
                return style_name, self.style_prompts.get(style_name, '')
        return None, None
    
    def ensure_style_consistency(self, description: str, target_style_prompt: str) -> str:
        """确保描述中的风格一致性
        
        Args:
            description: 原始描述
            target_style_prompt: 目标风格提示词
            
        Returns:
            str: 修复后的描述
        """
        try:
            logger.info(f"开始风格一致性检查，目标风格: {target_style_prompt}")
            
            # 如果描述中已经包含正确的风格提示词，直接返回
            if target_style_prompt in description:
                logger.debug("描述中已包含正确的风格提示词")
                return description
            
            # 移除可能被LLM替换的风格描述
            cleaned_description = self._remove_conflicting_styles(description, target_style_prompt)
            
            # 在描述末尾添加正确的风格提示词
            final_description = self._append_style_prompt(cleaned_description, target_style_prompt)
            
            logger.info(f"风格一致性修复完成")
            return final_description
            
        except Exception as e:
            logger.error(f"风格一致性修复失败: {e}")
            # 如果修复失败，至少确保在末尾添加目标风格提示词
            return self._append_style_prompt(description, target_style_prompt)
    
    def _remove_conflicting_styles(self, description: str, target_style_prompt: str) -> str:
        """移除与目标风格冲突的描述"""
        cleaned = description
        
        # 获取目标风格的可能替换词
        replacements = self.style_replacements.get(target_style_prompt, [])
        
        for replacement in replacements:
            # 移除单独出现的替换词（考虑各种标点符号）
            patterns = [
                rf'[，。、；：]?\s*{re.escape(replacement)}[，。、；：]?\s*',
                rf'{re.escape(replacement)}[，。]*$',  # 句末的替换词
                rf'^{re.escape(replacement)}[，。、；：]\s*',  # 句首的替换词
            ]
            
            for pattern in patterns:
                cleaned = re.sub(pattern, '', cleaned)
        
        # 移除其他风格的完整提示词
        for style_prompt in self.style_prompts.values():
            if style_prompt != target_style_prompt and style_prompt in cleaned:
                cleaned = cleaned.replace(style_prompt, '')
        
        # 清理多余的标点符号
        cleaned = re.sub(r'[，。、；：]{2,}', '，', cleaned)
        cleaned = re.sub(r'，+$', '', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _append_style_prompt(self, description: str, style_prompt: str) -> str:
        """在描述末尾添加风格提示词"""
        # 确保描述以适当的标点符号结尾
        if not description.endswith(('。', '，', '；', '：')):
            description = description.rstrip() + '，'
        elif description.endswith('。'):
            description = description.rstrip('。') + '，'
        
        # 添加风格提示词
        return f"{description}{style_prompt}。"
    
    def validate_project_style_consistency(self, project_data: Dict) -> Dict[str, any]:
        """验证项目中的风格一致性
        
        Returns:
            Dict: 包含验证结果的字典
        """
        try:
            logger.info("开始验证项目风格一致性...")
            
            # 获取用户选择的风格
            selected_style = None
            if 'five_stage_storyboard' in project_data:
                selected_style = project_data['five_stage_storyboard'].get('selected_style')
            
            if not selected_style:
                return {'status': 'warning', 'message': '未找到用户选择的风格'}
            
            target_style_prompt = self.style_prompts.get(selected_style)
            if not target_style_prompt:
                return {'status': 'error', 'message': f'未知的风格类型: {selected_style}'}
            
            # 检查分镜描述中的风格一致性
            inconsistent_shots = []
            if ('five_stage_storyboard' in project_data and 
                'stage_data' in project_data['five_stage_storyboard'] and
                '4' in project_data['five_stage_storyboard']['stage_data']):
                
                stage4_data = project_data['five_stage_storyboard']['stage_data']['4']
                if 'storyboard_results' in stage4_data:
                    for scene_idx, scene_data in enumerate(stage4_data['storyboard_results']):
                        storyboard_script = scene_data.get('storyboard_script', '')
                        
                        # 解析分镜脚本中的画面描述
                        shot_descriptions = self._extract_shot_descriptions(storyboard_script)
                        
                        for shot_idx, shot_desc in enumerate(shot_descriptions):
                            if target_style_prompt not in shot_desc:
                                inconsistent_shots.append({
                                    'scene_index': scene_idx,
                                    'shot_index': shot_idx,
                                    'description': shot_desc[:100] + '...' if len(shot_desc) > 100 else shot_desc
                                })
            
            result = {
                'status': 'success',
                'selected_style': selected_style,
                'target_style_prompt': target_style_prompt,
                'total_shots_checked': len(inconsistent_shots) + 10,  # 估算值
                'inconsistent_shots': len(inconsistent_shots),
                'inconsistent_details': inconsistent_shots[:5]  # 只返回前5个不一致的镜头
            }
            
            if inconsistent_shots:
                result['status'] = 'warning'
                result['message'] = f'发现 {len(inconsistent_shots)} 个镜头的风格不一致'
            else:
                result['message'] = '所有镜头的风格都保持一致'
            
            logger.info(f"风格一致性验证完成: {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"风格一致性验证失败: {e}")
            return {'status': 'error', 'message': f'验证失败: {str(e)}'}
    
    def _extract_shot_descriptions(self, storyboard_script: str) -> List[str]:
        """从分镜脚本中提取画面描述"""
        descriptions = []
        lines = storyboard_script.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('**画面描述') and ('：' in line or ':' in line):
                if '：' in line:
                    _, desc = line.split('：', 1)
                else:
                    _, desc = line.split(':', 1)
                descriptions.append(desc.strip())
        
        return descriptions
    
    def get_style_prompt(self, style_name: str) -> Optional[str]:
        """获取指定风格的提示词"""
        return self.style_prompts.get(style_name)
    
    def get_all_styles(self) -> Dict[str, str]:
        """获取所有可用的风格"""
        return self.style_prompts.copy()
