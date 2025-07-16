"""
配音优先工作流程核心模块
实现基于配音内容和时长的图像生成工作流程
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class VoiceSegment:
    """配音段落数据结构"""
    index: int
    scene_id: str
    shot_id: str
    content: str  # 配音文本内容
    audio_path: str  # 音频文件路径
    duration: float  # 音频时长（秒）
    content_type: str  # 内容类型：台词/旁白
    sound_effect: str  # 音效描述
    status: str  # 生成状态

@dataclass
class ImageRequirement:
    """图像生成需求数据结构"""
    voice_segment_index: int
    scene_id: str
    shot_id: str
    image_index: int  # 在该镜头中的图像序号
    prompt: str  # 图像生成提示词
    consistency_prompt: str  # 一致性描述
    enhanced_prompt: str  # 增强后的提示词
    duration_coverage: Tuple[float, float]  # 覆盖的时间范围 (start, end)
    priority: int  # 生成优先级

class VoiceFirstWorkflow:
    """配音优先工作流程管理器"""
    
    def __init__(self, project_manager=None):
        self.project_manager = project_manager
        self.voice_segments: List[VoiceSegment] = []
        self.image_requirements: List[ImageRequirement] = []
        
        # 配置参数
        self.config = {
            'min_duration_for_single_image': 3.0,  # 3秒以内生成1张图
            'max_duration_for_single_image': 6.0,  # 6秒以内生成2张图
            'images_per_6_seconds': 2,  # 每6秒生成2张图
            'min_image_duration': 1.5,  # 每张图最少覆盖1.5秒
            'max_image_duration': 4.0,  # 每张图最多覆盖4秒
        }
    
    def load_voice_data(self, voice_data_list: List[Dict]) -> bool:
        """加载配音数据"""
        try:
            self.voice_segments = []
            
            for i, voice_data in enumerate(voice_data_list):
                # 分析音频时长
                duration = self._analyze_audio_duration(voice_data.get('audio_path', ''))
                
                segment = VoiceSegment(
                    index=i,
                    scene_id=voice_data.get('scene_id', ''),
                    shot_id=voice_data.get('shot_id', ''),
                    content=voice_data.get('dialogue_text', ''),
                    audio_path=voice_data.get('audio_path', ''),
                    duration=duration,
                    content_type=voice_data.get('content_type', '旁白'),
                    sound_effect=voice_data.get('sound_effect', ''),
                    status=voice_data.get('status', '已生成')
                )
                self.voice_segments.append(segment)
            
            logger.info(f"成功加载 {len(self.voice_segments)} 个配音段落")
            return True
            
        except Exception as e:
            logger.error(f"加载配音数据失败: {e}")
            return False
    
    def _analyze_audio_duration(self, audio_path: str) -> float:
        """分析音频文件时长"""
        if not audio_path or not os.path.exists(audio_path):
            # 如果没有音频文件，根据文本长度估算时长
            return 3.0  # 默认3秒
        
        try:
            # 尝试使用mutagen获取音频时长
            from mutagen import File
            audio_file = File(audio_path)
            if audio_file and audio_file.info:
                duration = audio_file.info.length
                logger.debug(f"音频时长: {duration:.2f}秒 - {audio_path}")
                return duration
        except ImportError:
            logger.warning("mutagen库未安装，无法获取精确音频时长")
        except Exception as e:
            logger.warning(f"获取音频时长失败: {e}")
        
        # 降级方案：根据文本长度估算
        return self._estimate_duration_from_text("")
    
    def _estimate_duration_from_text(self, text: str) -> float:
        """根据文本长度估算配音时长"""
        if not text:
            return 3.0
        
        # 中文：平均每分钟200-250字
        # 估算公式：字数 / 4 = 秒数（按每秒4字计算）
        char_count = len(text)
        estimated_duration = max(char_count / 4.0, 1.0)  # 最少1秒
        
        logger.debug(f"文本长度: {char_count}字，估算时长: {estimated_duration:.2f}秒")
        return estimated_duration
    
    def calculate_image_requirements(self) -> List[ImageRequirement]:
        """计算图像生成需求"""
        try:
            self.image_requirements = []
            
            for segment in self.voice_segments:
                # 根据时长计算需要的图片数量
                image_count = self._calculate_image_count(segment.duration)
                
                logger.info(f"镜头 {segment.shot_id}: 时长{segment.duration:.2f}秒，需要{image_count}张图片")
                
                # 为每张图片创建生成需求
                for img_idx in range(image_count):
                    # 计算时间覆盖范围
                    time_per_image = segment.duration / image_count
                    start_time = img_idx * time_per_image
                    end_time = (img_idx + 1) * time_per_image
                    
                    # 生成基础提示词
                    base_prompt = self._generate_base_prompt(segment, img_idx, image_count)
                    
                    requirement = ImageRequirement(
                        voice_segment_index=segment.index,
                        scene_id=segment.scene_id,
                        shot_id=segment.shot_id,
                        image_index=img_idx,
                        prompt=base_prompt,
                        consistency_prompt="",  # 待后续填充
                        enhanced_prompt="",  # 待后续填充
                        duration_coverage=(start_time, end_time),
                        priority=1  # 默认优先级
                    )
                    
                    self.image_requirements.append(requirement)
            
            logger.info(f"计算完成，共需生成 {len(self.image_requirements)} 张图片")
            return self.image_requirements
            
        except Exception as e:
            logger.error(f"计算图像需求失败: {e}")
            return []
    
    def _calculate_image_count(self, duration: float) -> int:
        """根据时长计算图片数量"""
        if duration <= self.config['min_duration_for_single_image']:
            return 1
        elif duration <= self.config['max_duration_for_single_image']:
            return 2
        else:
            # 超过6秒，按比例计算
            return max(2, int(duration / 3.0))  # 每3秒1张图，最少2张
    
    def _generate_base_prompt(self, segment: VoiceSegment, img_index: int, total_images: int) -> str:
        """生成基础图像提示词"""
        content = segment.content
        
        if total_images == 1:
            # 单张图片，使用完整内容
            return f"根据以下内容生成画面：{content}"
        else:
            # 多张图片，根据序号生成不同角度的描述
            if img_index == 0:
                return f"开始场景，根据内容：{content[:len(content)//2]}"
            else:
                return f"后续场景，根据内容：{content[len(content)//2:]}"
    
    def enhance_image_prompts(self) -> bool:
        """增强图像提示词（添加一致性描述和LLM增强）"""
        try:
            # 这里将调用一致性描述增强器和LLM增强器
            # 为每个ImageRequirement填充consistency_prompt和enhanced_prompt
            
            for requirement in self.image_requirements:
                # 获取对应的配音段落
                segment = self.voice_segments[requirement.voice_segment_index]
                
                # 生成一致性描述（这里需要调用现有的一致性系统）
                requirement.consistency_prompt = self._generate_consistency_prompt(segment)
                
                # LLM增强（这里需要调用现有的增强系统）
                requirement.enhanced_prompt = self._enhance_prompt_with_llm(
                    requirement.prompt, 
                    requirement.consistency_prompt
                )
            
            logger.info("图像提示词增强完成")
            return True
            
        except Exception as e:
            logger.error(f"增强图像提示词失败: {e}")
            return False
    
    def _generate_consistency_prompt(self, segment: VoiceSegment) -> str:
        """生成一致性描述"""
        try:
            # 🔧 集成现有的一致性描述系统
            if not self.project_manager:
                return f"保持{segment.scene_id}的场景一致性"

            # 尝试从项目中加载角色和场景一致性信息
            project_data = self.project_manager.get_project_data()

            # 获取角色一致性信息
            character_consistency = self._extract_character_consistency(project_data, segment.content)

            # 获取场景一致性信息
            scene_consistency = self._extract_scene_consistency(project_data, segment.scene_id)

            # 组合一致性描述
            consistency_parts = []
            if character_consistency:
                consistency_parts.append(f"角色一致性：{character_consistency}")
            if scene_consistency:
                consistency_parts.append(f"场景一致性：{scene_consistency}")

            if consistency_parts:
                return "；".join(consistency_parts)
            else:
                return f"保持{segment.scene_id}的场景一致性"

        except Exception as e:
            logger.warning(f"生成一致性描述失败: {e}")
            return f"保持{segment.scene_id}的场景一致性"

    def _extract_character_consistency(self, project_data: dict, content: str) -> str:
        """从项目数据中提取角色一致性信息"""
        try:
            # 从五阶段数据中获取角色信息
            five_stage_data = project_data.get('five_stage_storyboard', {})
            stage_data = five_stage_data.get('stage_data', {})

            # 尝试从阶段2获取角色信息
            stage2_data = stage_data.get('2', {})
            character_scene_data = stage2_data.get('character_scene_data', {})

            if character_scene_data:
                characters = character_scene_data.get('characters', {})
                # 简单的角色匹配逻辑
                for char_name, char_info in characters.items():
                    if char_name in content:
                        appearance = char_info.get('appearance', '')
                        if appearance:
                            return f"{char_name}：{appearance}"

            return ""

        except Exception as e:
            logger.warning(f"提取角色一致性失败: {e}")
            return ""

    def _extract_scene_consistency(self, project_data: dict, scene_id: str) -> str:
        """从项目数据中提取场景一致性信息"""
        try:
            # 从五阶段数据中获取场景信息
            five_stage_data = project_data.get('five_stage_storyboard', {})
            stage_data = five_stage_data.get('stage_data', {})

            # 尝试从阶段3获取场景信息
            stage3_data = stage_data.get('3', {})
            scenes_analysis = stage3_data.get('scenes_analysis', '')

            if scenes_analysis and scene_id in scenes_analysis:
                # 简单提取场景描述
                lines = scenes_analysis.split('\n')
                for line in lines:
                    if scene_id in line and ('环境' in line or '背景' in line or '场景' in line):
                        return line.strip()

            return f"{scene_id}的环境设定"

        except Exception as e:
            logger.warning(f"提取场景一致性失败: {e}")
            return f"{scene_id}的环境设定"

    def _enhance_prompt_with_llm(self, base_prompt: str, consistency_prompt: str) -> str:
        """使用LLM增强提示词"""
        try:
            # 🔧 集成现有的LLM增强系统
            if not self.project_manager:
                return f"{base_prompt}。{consistency_prompt}"

            # 尝试调用现有的描述增强器
            try:
                from src.processors.scene_description_enhancer import SceneDescriptionEnhancer

                # 获取项目根目录
                project_data = self.project_manager.get_project_data()
                project_root = project_data.get('project_dir') or project_data.get('project_root')

                if project_root:
                    # 创建增强器实例（需要LLM API）
                    enhancer = SceneDescriptionEnhancer(project_root=str(project_root))

                    # 组合输入文本
                    input_text = f"{base_prompt}。{consistency_prompt}"

                    # 调用增强功能
                    enhanced_result = enhancer.enhance_description_with_llm(input_text)

                    if enhanced_result and enhanced_result.strip():
                        return enhanced_result

            except Exception as e:
                logger.warning(f"LLM增强失败: {e}")

            # 降级方案：简单组合
            return f"{base_prompt}。{consistency_prompt}"

        except Exception as e:
            logger.warning(f"增强提示词失败: {e}")
            return f"{base_prompt}。{consistency_prompt}"
    
    def export_to_image_generation_format(self) -> Dict[str, Any]:
        """导出为图像生成界面可用的格式"""
        try:
            storyboard_data = []
            
            for requirement in self.image_requirements:
                segment = self.voice_segments[requirement.voice_segment_index]
                
                shot_data = {
                    'scene_id': requirement.scene_id,
                    'scene_name': requirement.scene_id,  # 可以后续优化
                    'shot_id': f"{requirement.shot_id}_img_{requirement.image_index}",
                    'shot_name': f"镜头{requirement.voice_segment_index + 1}-图{requirement.image_index + 1}",
                    'sequence': f"{requirement.voice_segment_index + 1}-{requirement.image_index + 1}",
                    'original_description': requirement.prompt,
                    'consistency_description': requirement.consistency_prompt,
                    'enhanced_description': requirement.enhanced_prompt,
                    'status': '未生成',
                    'image_path': '',
                    'main_image_path': '',
                    'selected': False,
                    'voice_segment_index': requirement.voice_segment_index,
                    'duration_coverage': requirement.duration_coverage,
                    'audio_path': segment.audio_path,
                    'voice_content': segment.content
                }
                
                storyboard_data.append(shot_data)
            
            return {
                'storyboard_data': storyboard_data,
                'workflow_mode': 'voice_first',
                'total_voice_segments': len(self.voice_segments),
                'total_image_requirements': len(self.image_requirements)
            }
            
        except Exception as e:
            logger.error(f"导出图像生成格式失败: {e}")
            return {}
    
    def save_workflow_data(self) -> bool:
        """保存工作流程数据到项目"""
        try:
            if not self.project_manager:
                logger.warning("没有项目管理器，无法保存数据")
                return False
            
            workflow_data = {
                'voice_segments': [
                    {
                        'index': seg.index,
                        'scene_id': seg.scene_id,
                        'shot_id': seg.shot_id,
                        'content': seg.content,
                        'audio_path': seg.audio_path,
                        'duration': seg.duration,
                        'content_type': seg.content_type,
                        'sound_effect': seg.sound_effect,
                        'status': seg.status
                    }
                    for seg in self.voice_segments
                ],
                'image_requirements': [
                    {
                        'voice_segment_index': req.voice_segment_index,
                        'scene_id': req.scene_id,
                        'shot_id': req.shot_id,
                        'image_index': req.image_index,
                        'prompt': req.prompt,
                        'consistency_prompt': req.consistency_prompt,
                        'enhanced_prompt': req.enhanced_prompt,
                        'duration_coverage': req.duration_coverage,
                        'priority': req.priority
                    }
                    for req in self.image_requirements
                ],
                'config': self.config
            }
            
            # 保存到项目数据
            project_data = self.project_manager.get_project_data()
            project_data['voice_first_workflow'] = workflow_data
            self.project_manager.save_project_data(project_data)
            
            logger.info("配音优先工作流程数据已保存")
            return True
            
        except Exception as e:
            logger.error(f"保存工作流程数据失败: {e}")
            return False
