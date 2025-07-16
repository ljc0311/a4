"""
配音驱动的五阶段分镜系统
基于配音内容重新构建五阶段分镜工作流程
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class VoiceSegment:
    """配音段落数据结构"""
    index: int
    content: str
    audio_path: str
    duration: float
    content_type: str  # 旁白/台词
    sound_effect: str
    start_time: float = 0.0
    end_time: float = 0.0

@dataclass
class VoiceDrivenScene:
    """基于配音的场景数据"""
    scene_id: str
    scene_name: str
    voice_segments: List[VoiceSegment]
    total_duration: float
    scene_description: str
    emotional_tone: str

class VoiceDrivenStoryboardSystem:
    """配音驱动的分镜系统"""
    
    def __init__(self, project_manager=None):
        self.project_manager = project_manager
        self.voice_segments: List[VoiceSegment] = []
        self.voice_driven_scenes: List[VoiceDrivenScene] = []
        self.storyboard_data = {}
        
        # 配音驱动的配置
        self.config = {
            'min_scene_duration': 5.0,  # 最短场景时长
            'max_scene_duration': 30.0,  # 最长场景时长
            'scene_break_keywords': ['然后', '接下来', '后来', '突然', '这时候', '于是'],
            'emotional_keywords': {
                '开心': ['高兴', '快乐', '兴奋', '开心'],
                '伤感': ['难过', '伤心', '痛苦', '失落'],
                '紧张': ['紧张', '害怕', '担心', '焦虑'],
                '平静': ['平静', '安静', '淡然', '冷静']
            }
        }
    
    def load_voice_data(self, voice_data_list: List[Dict]) -> bool:
        """加载配音数据"""
        try:
            self.voice_segments = []
            current_time = 0.0
            
            for voice_data in voice_data_list:
                segment = VoiceSegment(
                    index=voice_data.get('index', 0),
                    content=voice_data.get('dialogue_text', '') or voice_data.get('original_text', ''),
                    audio_path=voice_data.get('audio_path', ''),
                    duration=voice_data.get('duration', 3.0),
                    content_type=voice_data.get('content_type', '旁白'),
                    sound_effect=voice_data.get('sound_effect', ''),
                    start_time=current_time,
                    end_time=current_time + voice_data.get('duration', 3.0)
                )
                self.voice_segments.append(segment)
                current_time = segment.end_time
            
            logger.info(f"成功加载 {len(self.voice_segments)} 个配音段落")
            return True
            
        except Exception as e:
            logger.error(f"加载配音数据失败: {e}")
            return False
    
    def analyze_voice_driven_scenes(self) -> bool:
        """基于配音内容分析场景"""
        try:
            if not self.voice_segments:
                logger.warning("没有配音数据可分析")
                return False
            
            logger.info("开始基于配音内容分析场景...")
            
            # 第一步：智能场景分割
            scene_groups = self._intelligent_scene_segmentation()
            
            # 第二步：为每个场景组创建场景数据
            self.voice_driven_scenes = []
            for i, group in enumerate(scene_groups):
                scene = self._create_scene_from_voice_group(i + 1, group)
                self.voice_driven_scenes.append(scene)
            
            logger.info(f"基于配音分析完成，共识别 {len(self.voice_driven_scenes)} 个场景")
            return True
            
        except Exception as e:
            logger.error(f"配音场景分析失败: {e}")
            return False
    
    def _intelligent_scene_segmentation(self) -> List[List[VoiceSegment]]:
        """智能场景分割算法"""
        try:
            scene_groups = []
            current_group = []
            current_duration = 0.0
            
            for segment in self.voice_segments:
                # 检查是否需要开始新场景
                should_break = self._should_break_scene(segment, current_duration)
                
                if should_break and current_group:
                    # 结束当前场景，开始新场景
                    scene_groups.append(current_group)
                    current_group = [segment]
                    current_duration = segment.duration
                else:
                    # 继续当前场景
                    current_group.append(segment)
                    current_duration += segment.duration
            
            # 添加最后一个场景组
            if current_group:
                scene_groups.append(current_group)
            
            return scene_groups
            
        except Exception as e:
            logger.error(f"场景分割失败: {e}")
            return [[segment] for segment in self.voice_segments]  # 降级方案
    
    def _should_break_scene(self, segment: VoiceSegment, current_duration: float) -> bool:
        """判断是否应该分割场景"""
        try:
            # 规则1：时长限制
            if current_duration >= self.config['max_scene_duration']:
                return True
            
            # 规则2：关键词检测
            content = segment.content.lower()
            for keyword in self.config['scene_break_keywords']:
                if keyword in content:
                    return True
            
            # 规则3：内容类型变化（旁白→台词或台词→旁白）
            if len(self.voice_segments) > segment.index > 0:
                prev_segment = self.voice_segments[segment.index - 1]
                if prev_segment.content_type != segment.content_type:
                    return True
            
            # 规则4：情感基调变化
            if self._detect_emotional_change(segment):
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"场景分割判断失败: {e}")
            return False
    
    def _detect_emotional_change(self, segment: VoiceSegment) -> bool:
        """检测情感基调变化"""
        try:
            current_emotion = self._analyze_emotion(segment.content)
            
            if segment.index > 0:
                prev_segment = self.voice_segments[segment.index - 1]
                prev_emotion = self._analyze_emotion(prev_segment.content)
                
                return current_emotion != prev_emotion and current_emotion != '平静'
            
            return False
            
        except Exception as e:
            logger.warning(f"情感变化检测失败: {e}")
            return False
    
    def _analyze_emotion(self, content: str) -> str:
        """分析文本情感"""
        try:
            content_lower = content.lower()
            
            for emotion, keywords in self.config['emotional_keywords'].items():
                for keyword in keywords:
                    if keyword in content_lower:
                        return emotion
            
            return '平静'
            
        except Exception as e:
            logger.warning(f"情感分析失败: {e}")
            return '平静'
    
    def _create_scene_from_voice_group(self, scene_index: int, voice_group: List[VoiceSegment]) -> VoiceDrivenScene:
        """从配音组创建场景数据"""
        try:
            # 计算场景总时长
            total_duration = sum(segment.duration for segment in voice_group)
            
            # 生成场景描述
            scene_description = self._generate_scene_description(voice_group)
            
            # 分析情感基调
            emotional_tone = self._analyze_scene_emotion(voice_group)
            
            # 创建场景
            scene = VoiceDrivenScene(
                scene_id=f"配音场景{scene_index}",
                scene_name=f"场景{scene_index}：{scene_description[:20]}...",
                voice_segments=voice_group,
                total_duration=total_duration,
                scene_description=scene_description,
                emotional_tone=emotional_tone
            )
            
            return scene
            
        except Exception as e:
            logger.error(f"创建场景数据失败: {e}")
            # 返回默认场景
            return VoiceDrivenScene(
                scene_id=f"配音场景{scene_index}",
                scene_name=f"场景{scene_index}",
                voice_segments=voice_group,
                total_duration=sum(segment.duration for segment in voice_group),
                scene_description="基于配音内容的场景",
                emotional_tone="平静"
            )
    
    def _generate_scene_description(self, voice_group: List[VoiceSegment]) -> str:
        """生成场景描述"""
        try:
            # 提取关键内容
            contents = [segment.content for segment in voice_group]
            combined_content = " ".join(contents)
            
            # 简单的关键词提取
            if "故事" in combined_content or "聊聊" in combined_content:
                return "故事开始与背景介绍"
            elif "七年" in combined_content or "困在" in combined_content:
                return "七年经历的回顾"
            elif "老板" in combined_content or "工作" in combined_content:
                return "工作机会与选择"
            else:
                # 使用第一个段落的前20个字符作为描述
                return contents[0][:20] if contents else "未知场景"
                
        except Exception as e:
            logger.warning(f"生成场景描述失败: {e}")
            return "基于配音的场景"
    
    def _analyze_scene_emotion(self, voice_group: List[VoiceSegment]) -> str:
        """分析场景整体情感"""
        try:
            emotions = [self._analyze_emotion(segment.content) for segment in voice_group]
            
            # 统计情感出现频率
            emotion_count = {}
            for emotion in emotions:
                emotion_count[emotion] = emotion_count.get(emotion, 0) + 1
            
            # 返回出现最多的情感
            return max(emotion_count.items(), key=lambda x: x[1])[0]
            
        except Exception as e:
            logger.warning(f"场景情感分析失败: {e}")
            return "平静"
    
    def generate_voice_driven_storyboard(self) -> bool:
        """生成基于配音的五阶段分镜数据"""
        try:
            if not self.voice_driven_scenes:
                logger.warning("没有场景数据可生成分镜")
                return False
            
            logger.info("开始生成基于配音的五阶段分镜数据...")
            
            # 生成五阶段数据结构
            self.storyboard_data = {
                'stage_data': {
                    '1': self._generate_stage_1_data(),
                    '2': self._generate_stage_2_data(),
                    '3': self._generate_stage_3_data(),
                    '4': self._generate_stage_4_data(),
                    '5': self._generate_stage_5_data()
                },
                'current_stage': 5,
                'voice_driven': True,
                'voice_segments_count': len(self.voice_segments),
                'scenes_count': len(self.voice_driven_scenes),
                'total_duration': sum(scene.total_duration for scene in self.voice_driven_scenes)
            }
            
            logger.info("基于配音的五阶段分镜数据生成完成")
            return True
            
        except Exception as e:
            logger.error(f"生成配音驱动分镜失败: {e}")
            return False
    
    def _generate_stage_1_data(self) -> Dict[str, Any]:
        """生成第1阶段数据（世界观圣经）"""
        try:
            # 基于配音内容分析主题
            all_content = " ".join([segment.content for segment in self.voice_segments])
            
            return {
                'world_bible': f"基于配音内容的世界观设定\n\n主要内容：{all_content[:200]}...",
                'article_text': all_content,
                'style': '真实风格',
                'voice_driven': True
            }
            
        except Exception as e:
            logger.error(f"生成第1阶段数据失败: {e}")
            return {}
    
    def _generate_stage_2_data(self) -> Dict[str, Any]:
        """生成第2阶段数据（角色场景）"""
        try:
            # 从配音内容中提取角色信息
            characters = self._extract_characters_from_voice()
            scenes = self._extract_scenes_from_voice()
            
            return {
                'character_scene_data': {
                    'characters': characters,
                    'scenes': scenes
                },
                'voice_driven': True,
                'completed': True
            }
            
        except Exception as e:
            logger.error(f"生成第2阶段数据失败: {e}")
            return {}
    
    def _generate_stage_3_data(self) -> Dict[str, Any]:
        """生成第3阶段数据（场景分析）- 简化版本，只生成场景标题"""
        try:
            scenes_analysis = ""
            for scene in self.voice_driven_scenes:
                scenes_analysis += f"### {scene.scene_name}\n"

            return {
                'scenes_analysis': scenes_analysis,
                'voice_driven': True,
                'scenes_count': len(self.voice_driven_scenes)
            }

        except Exception as e:
            logger.error(f"生成第3阶段数据失败: {e}")
            return {}
    
    def _generate_stage_4_data(self) -> Dict[str, Any]:
        """生成第4阶段数据（分镜脚本）"""
        try:
            storyboard_results = []
            
            for scene_index, scene in enumerate(self.voice_driven_scenes):
                scene_result = {
                    'scene_index': scene_index,
                    'scene_info': scene.scene_name,
                    'voice_segments': [
                        {
                            'index': seg.index,
                            'content': seg.content,
                            'duration': seg.duration,
                            'content_type': seg.content_type,
                            'sound_effect': seg.sound_effect
                        }
                        for seg in scene.voice_segments
                    ],
                    'storyboard_script': self._generate_scene_storyboard_script(scene)
                }
                storyboard_results.append(scene_result)
            
            return {
                'storyboard_results': storyboard_results,
                'voice_driven': True
            }
            
        except Exception as e:
            logger.error(f"生成第4阶段数据失败: {e}")
            return {}
    
    def _generate_stage_5_data(self) -> Dict[str, Any]:
        """生成第5阶段数据（最终分镜）"""
        try:
            final_storyboard = []
            
            for scene in self.voice_driven_scenes:
                for segment in scene.voice_segments:
                    shot_data = {
                        'scene_id': scene.scene_id,
                        'scene_name': scene.scene_name,
                        'shot_id': f"镜头{segment.index + 1}",
                        'shot_name': f"镜头{segment.index + 1}",
                        'sequence': str(segment.index + 1),
                        'original_description': segment.content,
                        'consistency_description': f"基于配音内容：{segment.content[:50]}...",
                        'enhanced_description': f"增强描述：{segment.content}",
                        'voice_content': segment.content,
                        'voice_duration': segment.duration,
                        'content_type': segment.content_type,
                        'sound_effect': segment.sound_effect,
                        'audio_path': segment.audio_path
                    }
                    final_storyboard.append(shot_data)
            
            return {
                'final_storyboard': final_storyboard,
                'voice_driven': True,
                'total_shots': len(final_storyboard)
            }
            
        except Exception as e:
            logger.error(f"生成第5阶段数据失败: {e}")
            return {}
    
    def save_voice_driven_storyboard(self) -> bool:
        """保存配音驱动的分镜数据"""
        try:
            if not self.project_manager or not self.storyboard_data:
                logger.warning("无法保存：缺少项目管理器或分镜数据")
                return False
            
            # 获取项目数据
            project_data = self.project_manager.get_project_data()
            
            # 更新五阶段数据
            project_data['five_stage_storyboard'] = self.storyboard_data
            
            # 添加配音驱动标记
            project_data['workflow_settings'] = {
                'mode': 'voice_driven',
                'voice_driven_enabled': True,
                'storyboard_source': 'voice_content'
            }
            
            # 保存项目数据
            self.project_manager.save_project_data(project_data)
            
            logger.info("配音驱动的分镜数据已保存")
            return True
            
        except Exception as e:
            logger.error(f"保存配音驱动分镜数据失败: {e}")
            return False
    
    def _extract_characters_from_voice(self) -> Dict[str, Any]:
        """从配音内容中提取角色信息"""
        # 简化实现，实际可以使用NLP技术
        return {
            '主角': {
                'appearance': '基于配音内容推断的主角形象',
                'personality': '从配音语调和内容分析的性格特点'
            }
        }
    
    def _extract_scenes_from_voice(self) -> Dict[str, Any]:
        """从配音内容中提取场景信息"""
        scenes = {}
        for scene in self.voice_driven_scenes:
            scenes[scene.scene_id] = {
                'description': scene.scene_description,
                'duration': scene.total_duration,
                'emotional_tone': scene.emotional_tone
            }
        return scenes
    
    def _generate_scene_storyboard_script(self, scene: VoiceDrivenScene) -> str:
        """为场景生成分镜脚本"""
        script = f"## {scene.scene_name} 分镜脚本\n\n"
        
        for i, segment in enumerate(scene.voice_segments):
            script += f"### 镜头{segment.index + 1}\n"
            script += f"- **时长**: {segment.duration}秒\n"
            script += f"- **内容**: {segment.content}\n"
            script += f"- **类型**: {segment.content_type}\n"
            script += f"- **音效**: {segment.sound_effect}\n\n"
        
        return script
