#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文本与场景匹配优化器
解决原文内容与镜头画面的精确对应问题
"""

import os
import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class TextSceneOptimizer:
    """文本与场景匹配优化器"""
    
    def __init__(self, project_data: Dict[str, Any]):
        self.project_data = project_data
        self.original_text = self._extract_original_text()
        self.scenes_data = self._extract_scenes_data()
        self.storyboard_data = self._extract_storyboard_data()
    
    def _extract_original_text(self) -> str:
        """提取原始文本"""
        # 🔧 BUG修复：优先从project.json的article_text字段提取原文（用户直接粘贴的内容）

        # 方法1：优先从project.json根级别的article_text字段获取
        article_text = self.project_data.get('article_text', '')
        if article_text:
            logger.info(f"从project.json根级别article_text字段提取原文，长度: {len(article_text)}")
            return article_text

        # 方法2：从five_stage_storyboard根级别提取
        if 'five_stage_storyboard' in self.project_data:
            article_text = self.project_data['five_stage_storyboard'].get('article_text', '')
            if article_text:
                logger.info(f"从five_stage_storyboard根级别提取原文，长度: {len(article_text)}")
                return article_text

        # 方法3：从five_stage_storyboard.stage_data中提取
        if 'five_stage_storyboard' in self.project_data and 'stage_data' in self.project_data['five_stage_storyboard']:
            stage_data = self.project_data['five_stage_storyboard']['stage_data']
            for stage_key in ['3', '2', '1', '4', '5']:  # 检查各个阶段
                if stage_key in stage_data:
                    article_text = stage_data[stage_key].get('article_text', '')
                    if article_text:
                        logger.info(f"从five_stage_storyboard.stage_data.{stage_key}提取原文，长度: {len(article_text)}")
                        return article_text

        # 方法4：从five_stage_storyboard的各个阶段中提取
        if 'five_stage_storyboard' in self.project_data:
            stage_data = self.project_data['five_stage_storyboard']
            for stage_key in ['3', '4', '5', '1', '2']:  # 检查各个阶段
                if stage_key in stage_data:
                    article_text = stage_data[stage_key].get('article_text', '')
                    if article_text:
                        logger.info(f"从five_stage_storyboard.{stage_key}提取原文，长度: {len(article_text)}")
                        return article_text

        # 方法5：从其他可能的字段获取
        fallback_fields = ['rewritten_text', 'original_text', 'text_content']
        for field in fallback_fields:
            fallback_text = self.project_data.get(field, '')
            if fallback_text:
                logger.info(f"从备用字段{field}提取原文，长度: {len(fallback_text)}")
                return fallback_text

        # 方法6：从text_content子字段获取
        text_content = self.project_data.get('text_content', {})
        if isinstance(text_content, dict):
            for field in ['rewritten_text', 'original_text']:
                text = text_content.get(field, '')
                if text:
                    logger.info(f"从text_content.{field}提取原文，长度: {len(text)}")
                    return text

        logger.warning("未找到任何原文内容")
        return ""
    
    def _extract_scenes_data(self) -> List[Dict[str, Any]]:
        """提取场景数据"""
        scenes = []

        # 🔧 修复：从正确的数据结构中提取场景数据

        # 方法1：从five_stage_storyboard.stage_data中提取
        if 'five_stage_storyboard' in self.project_data and 'stage_data' in self.project_data['five_stage_storyboard']:
            stage_data = self.project_data['five_stage_storyboard']['stage_data']

            # 从第3阶段获取场景分析
            if '3' in stage_data:
                scenes_analysis = stage_data['3'].get('scenes_analysis', '')
                if scenes_analysis:
                    logger.info(f"从five_stage_storyboard.stage_data.3提取场景分析，长度: {len(scenes_analysis)}")
                    scenes.extend(self._parse_scenes_analysis(scenes_analysis))

            # 从第4阶段获取分镜结果
            if '4' in stage_data:
                storyboard_results = stage_data['4'].get('storyboard_results', [])
                logger.info(f"从five_stage_storyboard.stage_data.4提取分镜结果，数量: {len(storyboard_results)}")
                for result in storyboard_results:
                    scene_info = result.get('scene_info', '')
                    if scene_info and scene_info not in [s.get('scene_info', '') for s in scenes]:
                        scenes.append({
                            'scene_info': scene_info,
                            'storyboard_script': result.get('storyboard_script', '')
                        })

        # 方法2：从five_stage_storyboard中提取
        if not scenes and 'five_stage_storyboard' in self.project_data:
            stage_data = self.project_data['five_stage_storyboard']

            # 从第3阶段获取场景分析
            if '3' in stage_data:
                scenes_analysis = stage_data['3'].get('scenes_analysis', '')
                if scenes_analysis:
                    logger.info(f"从five_stage_storyboard.3提取场景分析，长度: {len(scenes_analysis)}")
                    scenes.extend(self._parse_scenes_analysis(scenes_analysis))

            # 从第4阶段获取分镜结果
            if '4' in stage_data:
                storyboard_results = stage_data['4'].get('storyboard_results', [])
                logger.info(f"从five_stage_storyboard.4提取分镜结果，数量: {len(storyboard_results)}")
                for result in storyboard_results:
                    scene_info = result.get('scene_info', '')
                    if scene_info and scene_info not in [s.get('scene_info', '') for s in scenes]:
                        scenes.append({
                            'scene_info': scene_info,
                            'storyboard_script': result.get('storyboard_script', '')
                        })

        logger.info(f"提取到 {len(scenes)} 个场景")
        return scenes
    
    def _extract_storyboard_data(self) -> List[Dict[str, Any]]:
        """提取分镜数据"""
        storyboard_results = []

        # 🔧 修复：从正确的数据结构中提取分镜数据

        # 方法1：从five_stage_storyboard.stage_data中提取
        if 'five_stage_storyboard' in self.project_data and 'stage_data' in self.project_data['five_stage_storyboard']:
            stage_data = self.project_data['five_stage_storyboard']['stage_data']

            # 从第4或第5阶段获取分镜结果
            for stage_key in ['5', '4']:
                if stage_key in stage_data:
                    results = stage_data[stage_key].get('storyboard_results', [])
                    if results:
                        logger.info(f"从five_stage_storyboard.stage_data.{stage_key}提取分镜数据，数量: {len(results)}")
                        storyboard_results = results
                        break

        # 方法2：从five_stage_storyboard中提取
        if not storyboard_results and 'five_stage_storyboard' in self.project_data:
            stage_data = self.project_data['five_stage_storyboard']

            # 从第4或第5阶段获取分镜结果
            for stage_key in ['5', '4']:
                if stage_key in stage_data:
                    results = stage_data[stage_key].get('storyboard_results', [])
                    if results:
                        logger.info(f"从five_stage_storyboard.{stage_key}提取分镜数据，数量: {len(results)}")
                        storyboard_results = results
                        break

        logger.info(f"提取到 {len(storyboard_results)} 个分镜结果")
        return storyboard_results
    
    def _parse_scenes_analysis(self, scenes_analysis: str) -> List[Dict[str, Any]]:
        """解析场景分析文本 - 简化版本，只解析场景标题"""
        scenes = []

        lines = scenes_analysis.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测场景标题
            if line.startswith('### 场景') or line.startswith('## 场景'):
                scene_title = line.replace('#', '').strip()
                scenes.append({
                    'scene_title': scene_title,
                    'scene_name': scene_title  # 兼容性字段
                })

        return scenes
    
    def create_smart_text_segments(self) -> List[Dict[str, Any]]:
        """创建智能文本分段"""
        if not self.original_text:
            return []
        
        # 计算总镜头数
        total_shots = 0
        for storyboard in self.storyboard_data:
            script = storyboard.get('storyboard_script', '')
            shots = self._parse_storyboard_script(script)
            total_shots += len(shots)
        
        logger.info(f"原文长度: {len(self.original_text)}, 总镜头数: {total_shots}")
        
        # 按自然段落分割
        paragraphs = [p.strip() for p in self.original_text.split('\n') if p.strip()]
        
        # 按句子进一步分割
        text_segments = []
        segment_index = 0
        
        for para_idx, paragraph in enumerate(paragraphs):
            # 按句号、感叹号、问号分割句子
            sentences = re.split(r'[。！？]', paragraph)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if not sentences:
                continue
            
            # 根据镜头数量决定分割策略
            if total_shots <= len(paragraphs):
                # 镜头数少于段落数：保持段落完整
                text_segments.append({
                    'index': segment_index,
                    'paragraph_index': para_idx,
                    'content': paragraph,
                    'type': 'paragraph',
                    'sentence_count': len(sentences)
                })
                segment_index += 1
            else:
                # 镜头数多于段落数：需要细分
                if len(sentences) <= 2:
                    # 短段落保持完整
                    text_segments.append({
                        'index': segment_index,
                        'paragraph_index': para_idx,
                        'content': paragraph,
                        'type': 'paragraph',
                        'sentence_count': len(sentences)
                    })
                    segment_index += 1
                else:
                    # 长段落按句子分组
                    sentences_per_segment = max(1, len(sentences) // min(3, len(sentences)))
                    
                    for i in range(0, len(sentences), sentences_per_segment):
                        segment_sentences = sentences[i:i + sentences_per_segment]
                        segment_content = ''.join(s + '。' for s in segment_sentences).rstrip('。')
                        
                        if segment_content:
                            text_segments.append({
                                'index': segment_index,
                                'paragraph_index': para_idx,
                                'content': segment_content,
                                'type': 'sentence_group',
                                'sentence_count': len(segment_sentences),
                                'sentence_range': (i, i + len(segment_sentences))
                            })
                            segment_index += 1
        
        # 如果文本片段仍然不够，进行进一步细分
        if len(text_segments) < total_shots and total_shots > 0:
            expanded_segments = []
            
            for segment in text_segments:
                content = segment['content']
                # 按逗号、分号进一步分割
                sub_parts = re.split(r'[，；]', content)
                sub_parts = [p.strip() for p in sub_parts if p.strip()]
                
                if len(sub_parts) > 1:
                    for i, part in enumerate(sub_parts):
                        expanded_segments.append({
                            'index': len(expanded_segments),
                            'paragraph_index': segment['paragraph_index'],
                            'content': part,
                            'type': 'sub_sentence',
                            'parent_segment': segment['index'],
                            'sub_index': i
                        })
                else:
                    segment['index'] = len(expanded_segments)
                    expanded_segments.append(segment)
            
            text_segments = expanded_segments
        
        logger.info(f"智能文本分段完成: {len(paragraphs)}个段落 -> {len(text_segments)}个文本片段")
        return text_segments
    
    def _parse_storyboard_script(self, script: str) -> List[Dict[str, Any]]:
        """解析分镜脚本"""
        shots = []
        current_shot = {}
        shot_id = 1
        
        lines = script.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测镜头开始
            if line.startswith('### 镜头') or line.startswith('## 镜头') or '镜头' in line:
                if current_shot:
                    shots.append(current_shot)
                current_shot = {'shot_id': f'镜头{shot_id}'}
                shot_id += 1
                continue
            
            # 解析字段
            if '：' in line or ':' in line:
                separator = '：' if '：' in line else ':'
                parts = line.split(separator, 1)
                if len(parts) == 2:
                    field_name = parts[0].strip().replace('**', '').replace('-', '').replace('*', '')
                    field_value = parts[1].strip()
                    
                    if '画面描述' in field_name:
                        current_shot['description'] = field_value
                        current_shot['action'] = field_value
                    elif '台词' in field_name or '对话' in field_name or '旁白' in field_name:
                        current_shot['dialogue'] = field_value
                    elif '音效' in field_name:
                        current_shot['sound_effect'] = field_value
        
        # 添加最后一个镜头
        if current_shot:
            shots.append(current_shot)
        
        return shots
    
    def optimize_scene_text_mapping(self) -> Dict[str, Any]:
        """优化场景与文本的映射关系"""
        text_segments = self.create_smart_text_segments()
        
        # 为每个场景分配对应的原文内容
        optimized_scenes = []
        segment_index = 0
        
        for scene_idx, scene in enumerate(self.scenes_data):
            scene_title = scene.get('scene_title', f'场景{scene_idx + 1}')
            
            # 计算该场景的镜头数
            storyboard_script = scene.get('storyboard_script', '')
            if not storyboard_script:
                # 从storyboard_data中查找
                for storyboard in self.storyboard_data:
                    if scene.get('scene_info', '') in storyboard.get('scene_info', ''):
                        storyboard_script = storyboard.get('storyboard_script', '')
                        break
            
            shots = self._parse_storyboard_script(storyboard_script)
            shot_count = len(shots)
            
            # 为该场景分配文本片段
            scene_text_segments = []
            for i in range(shot_count):
                if segment_index < len(text_segments):
                    scene_text_segments.append(text_segments[segment_index])
                    segment_index += 1
                else:
                    # 如果文本片段不够，重复使用最后一个
                    if text_segments:
                        scene_text_segments.append(text_segments[-1])
            
            # 生成场景的原文内容摘要
            scene_original_content = ' '.join([seg['content'] for seg in scene_text_segments])
            
            optimized_scene = {
                'scene_title': scene_title,
                'scene_info': scene.get('scene_info', ''),
                'original_text_segments': scene_text_segments,
                'original_content_summary': scene_original_content[:100] + '...' if len(scene_original_content) > 100 else scene_original_content,
                'shot_count': shot_count,
                'shots_with_text': []
            }
            
            # 为每个镜头分配具体的原文内容
            for shot_idx, shot in enumerate(shots):
                if shot_idx < len(scene_text_segments):
                    text_segment = scene_text_segments[shot_idx]
                    shot_with_text = {
                        'shot_id': shot.get('shot_id', f'镜头{shot_idx + 1}'),
                        'description': shot.get('description', ''),
                        'dialogue': shot.get('dialogue', ''),
                        'original_text': text_segment['content'],
                        'text_segment_info': text_segment
                    }
                    optimized_scene['shots_with_text'].append(shot_with_text)
            
            optimized_scenes.append(optimized_scene)
        
        return {
            'optimized_scenes': optimized_scenes,
            'text_segments': text_segments,
            'total_shots': sum(len(scene['shots_with_text']) for scene in optimized_scenes),
            'total_text_segments': len(text_segments)
        }
