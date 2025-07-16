"""
配音-图像同步机制
确保生成的图像与对应的配音内容在时间轴上完美匹配
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SyncPoint:
    """同步点数据结构"""
    voice_segment_index: int
    image_index: int
    start_time: float  # 在配音中的开始时间
    end_time: float    # 在配音中的结束时间
    image_path: str    # 对应的图像路径
    sync_quality: float  # 同步质量评分 (0-1)

@dataclass
class TimelineSegment:
    """时间轴段落"""
    start_time: float
    end_time: float
    voice_content: str
    image_path: str
    scene_id: str
    shot_id: str
    transition_type: str = "cut"  # 转场类型：cut, fade, dissolve

class VoiceImageSyncManager:
    """配音-图像同步管理器"""
    
    def __init__(self, project_manager=None):
        self.project_manager = project_manager
        self.sync_points: List[SyncPoint] = []
        self.timeline_segments: List[TimelineSegment] = []
        
        # 同步配置
        self.sync_config = {
            'min_image_duration': 1.5,  # 最短图像显示时间
            'max_image_duration': 4.0,  # 最长图像显示时间
            'transition_duration': 0.3,  # 转场时间
            'sync_tolerance': 0.1,  # 同步容差
            'quality_threshold': 0.8,  # 质量阈值
        }
    
    def create_sync_timeline(self, voice_segments: List[Dict], image_requirements: List[Dict]) -> bool:
        """创建同步时间轴"""
        try:
            self.sync_points = []
            self.timeline_segments = []
            
            logger.info(f"开始创建同步时间轴：{len(voice_segments)}个配音段落，{len(image_requirements)}个图像需求")
            
            # 按配音段落组织图像需求
            voice_to_images = self._group_images_by_voice(voice_segments, image_requirements)
            
            current_time = 0.0
            
            for voice_idx, voice_segment in enumerate(voice_segments):
                voice_duration = voice_segment.get('duration', 3.0)
                images = voice_to_images.get(voice_idx, [])
                
                if not images:
                    logger.warning(f"配音段落 {voice_idx} 没有对应的图像")
                    current_time += voice_duration
                    continue
                
                # 为当前配音段落创建图像时间轴
                segment_timeline = self._create_segment_timeline(
                    voice_segment, images, current_time, voice_duration
                )
                
                self.timeline_segments.extend(segment_timeline)
                current_time += voice_duration
            
            # 验证时间轴完整性
            if self._validate_timeline():
                logger.info(f"同步时间轴创建完成，共 {len(self.timeline_segments)} 个时间段")
                return True
            else:
                logger.error("时间轴验证失败")
                return False
                
        except Exception as e:
            logger.error(f"创建同步时间轴失败: {e}")
            return False
    
    def _group_images_by_voice(self, voice_segments: List[Dict], 
                              image_requirements: List[Dict]) -> Dict[int, List[Dict]]:
        """按配音段落组织图像需求"""
        voice_to_images = {}
        
        for image_req in image_requirements:
            voice_idx = image_req.get('voice_segment_index', 0)
            if voice_idx not in voice_to_images:
                voice_to_images[voice_idx] = []
            voice_to_images[voice_idx].append(image_req)
        
        # 按图像索引排序
        for voice_idx in voice_to_images:
            voice_to_images[voice_idx].sort(key=lambda x: x.get('image_index', 0))
        
        return voice_to_images
    
    def _create_segment_timeline(self, voice_segment: Dict, images: List[Dict], 
                               start_time: float, total_duration: float) -> List[TimelineSegment]:
        """为单个配音段落创建图像时间轴"""
        timeline = []
        
        if not images:
            return timeline
        
        image_count = len(images)
        
        # 计算每张图像的显示时间
        if image_count == 1:
            # 单张图像覆盖整个配音时长
            image_duration = total_duration
            timeline.append(TimelineSegment(
                start_time=start_time,
                end_time=start_time + total_duration,
                voice_content=voice_segment.get('dialogue_text', ''),
                image_path=images[0].get('image_path', ''),
                scene_id=voice_segment.get('scene_id', ''),
                shot_id=voice_segment.get('shot_id', ''),
                transition_type="cut"
            ))
        else:
            # 多张图像平均分配时间
            time_per_image = total_duration / image_count
            
            for i, image in enumerate(images):
                segment_start = start_time + i * time_per_image
                segment_end = start_time + (i + 1) * time_per_image
                
                # 确保图像显示时间在合理范围内
                actual_duration = segment_end - segment_start
                if actual_duration < self.sync_config['min_image_duration']:
                    # 如果时间太短，延长到最小时长
                    segment_end = segment_start + self.sync_config['min_image_duration']
                elif actual_duration > self.sync_config['max_image_duration']:
                    # 如果时间太长，缩短到最大时长
                    segment_end = segment_start + self.sync_config['max_image_duration']
                
                # 确定转场类型
                transition = "fade" if i > 0 else "cut"
                
                timeline.append(TimelineSegment(
                    start_time=segment_start,
                    end_time=segment_end,
                    voice_content=voice_segment.get('dialogue_text', ''),
                    image_path=image.get('image_path', ''),
                    scene_id=voice_segment.get('scene_id', ''),
                    shot_id=voice_segment.get('shot_id', ''),
                    transition_type=transition
                ))
        
        return timeline
    
    def _validate_timeline(self) -> bool:
        """验证时间轴的完整性和一致性"""
        try:
            if not self.timeline_segments:
                logger.warning("时间轴为空")
                return False
            
            # 检查时间连续性
            sorted_segments = sorted(self.timeline_segments, key=lambda x: x.start_time)
            
            for i in range(len(sorted_segments) - 1):
                current_end = sorted_segments[i].end_time
                next_start = sorted_segments[i + 1].start_time
                
                # 检查时间间隙
                gap = next_start - current_end
                if abs(gap) > self.sync_config['sync_tolerance']:
                    logger.warning(f"时间轴存在间隙: {gap:.2f}秒 在 {current_end:.2f}s 和 {next_start:.2f}s 之间")
            
            # 检查图像文件存在性
            missing_images = []
            for segment in self.timeline_segments:
                if segment.image_path and not os.path.exists(segment.image_path):
                    missing_images.append(segment.image_path)
            
            if missing_images:
                logger.warning(f"发现 {len(missing_images)} 个缺失的图像文件")
            
            logger.info("时间轴验证完成")
            return True
            
        except Exception as e:
            logger.error(f"时间轴验证失败: {e}")
            return False
    
    def optimize_timeline(self) -> bool:
        """优化时间轴，提高同步质量"""
        try:
            if not self.timeline_segments:
                return False
            
            logger.info("开始优化时间轴")
            
            # 优化1：调整重叠的时间段
            self._resolve_time_overlaps()
            
            # 优化2：平滑转场时间
            self._smooth_transitions()
            
            # 优化3：调整过短或过长的段落
            self._adjust_segment_durations()
            
            logger.info("时间轴优化完成")
            return True
            
        except Exception as e:
            logger.error(f"时间轴优化失败: {e}")
            return False
    
    def _resolve_time_overlaps(self):
        """解决时间重叠问题"""
        sorted_segments = sorted(self.timeline_segments, key=lambda x: x.start_time)
        
        for i in range(len(sorted_segments) - 1):
            current = sorted_segments[i]
            next_segment = sorted_segments[i + 1]
            
            if current.end_time > next_segment.start_time:
                # 存在重叠，调整当前段落的结束时间
                overlap = current.end_time - next_segment.start_time
                current.end_time = next_segment.start_time - self.sync_config['transition_duration']
                logger.debug(f"解决重叠: 调整段落结束时间 -{overlap:.2f}秒")
    
    def _smooth_transitions(self):
        """平滑转场时间"""
        for i in range(len(self.timeline_segments) - 1):
            current = self.timeline_segments[i]
            next_segment = self.timeline_segments[i + 1]
            
            # 为fade转场预留时间
            if next_segment.transition_type == "fade":
                gap = next_segment.start_time - current.end_time
                if gap < self.sync_config['transition_duration']:
                    # 调整时间以适应转场
                    adjustment = (self.sync_config['transition_duration'] - gap) / 2
                    current.end_time -= adjustment
                    next_segment.start_time += adjustment
    
    def _adjust_segment_durations(self):
        """调整段落时长"""
        for segment in self.timeline_segments:
            duration = segment.end_time - segment.start_time
            
            if duration < self.sync_config['min_image_duration']:
                # 延长过短的段落
                extension = self.sync_config['min_image_duration'] - duration
                segment.end_time += extension
                logger.debug(f"延长段落: +{extension:.2f}秒")
            elif duration > self.sync_config['max_image_duration']:
                # 缩短过长的段落
                reduction = duration - self.sync_config['max_image_duration']
                segment.end_time -= reduction
                logger.debug(f"缩短段落: -{reduction:.2f}秒")
    
    def export_timeline_data(self) -> Dict[str, Any]:
        """导出时间轴数据"""
        try:
            timeline_data = {
                'total_duration': max(seg.end_time for seg in self.timeline_segments) if self.timeline_segments else 0,
                'segment_count': len(self.timeline_segments),
                'segments': [
                    {
                        'start_time': seg.start_time,
                        'end_time': seg.end_time,
                        'duration': seg.end_time - seg.start_time,
                        'voice_content': seg.voice_content,
                        'image_path': seg.image_path,
                        'scene_id': seg.scene_id,
                        'shot_id': seg.shot_id,
                        'transition_type': seg.transition_type
                    }
                    for seg in self.timeline_segments
                ],
                'sync_config': self.sync_config,
                'quality_metrics': self._calculate_quality_metrics()
            }
            
            return timeline_data
            
        except Exception as e:
            logger.error(f"导出时间轴数据失败: {e}")
            return {}
    
    def _calculate_quality_metrics(self) -> Dict[str, float]:
        """计算同步质量指标"""
        if not self.timeline_segments:
            return {}
        
        # 计算平均段落时长
        durations = [seg.end_time - seg.start_time for seg in self.timeline_segments]
        avg_duration = sum(durations) / len(durations)
        
        # 计算时长标准差
        variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
        std_deviation = variance ** 0.5
        
        # 计算覆盖率（有图像的时间比例）
        total_time = max(seg.end_time for seg in self.timeline_segments)
        covered_time = sum(seg.end_time - seg.start_time for seg in self.timeline_segments)
        coverage_ratio = covered_time / total_time if total_time > 0 else 0
        
        return {
            'average_duration': avg_duration,
            'duration_std_dev': std_deviation,
            'coverage_ratio': coverage_ratio,
            'segment_count': len(self.timeline_segments),
            'total_duration': total_time
        }
    
    def save_sync_data(self) -> bool:
        """保存同步数据到项目"""
        try:
            if not self.project_manager:
                logger.warning("没有项目管理器，无法保存同步数据")
                return False
            
            sync_data = self.export_timeline_data()
            
            # 保存到项目数据
            project_data = self.project_manager.get_project_data()
            project_data['voice_image_sync'] = sync_data
            self.project_manager.save_project_data(project_data)
            
            logger.info("配音-图像同步数据已保存")
            return True
            
        except Exception as e:
            logger.error(f"保存同步数据失败: {e}")
            return False
