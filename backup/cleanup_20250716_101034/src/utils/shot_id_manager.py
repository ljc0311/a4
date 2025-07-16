"""
统一镜头ID管理器
解决配音段落ID和图像镜头ID不匹配的问题
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ShotMapping:
    """镜头映射数据结构"""
    global_index: int  # 全局镜头索引 (1, 2, 3, ...)
    scene_id: str      # 场景ID (scene_1, scene_2, ...)
    shot_id: str       # 镜头ID (shot_1, shot_2, ...)
    text_segment_id: str  # 文本段落ID (text_segment_001, text_segment_002, ...)
    unified_key: str   # 统一键 (scene_1_shot_1)
    original_text: str # 对应的原文内容
    scene_index: int   # 场景内镜头索引 (1, 2, 3, ...)


class ShotIDManager:
    """统一镜头ID管理器"""
    
    def __init__(self):
        self.shot_mappings: List[ShotMapping] = []
        self.id_conversion_cache: Dict[str, str] = {}
        self.reverse_conversion_cache: Dict[str, str] = {}
    
    def initialize_from_project_data(self, project_data: Dict[str, Any]) -> bool:
        """从项目数据初始化镜头映射"""
        try:
            self.shot_mappings.clear()
            self.id_conversion_cache.clear()
            self.reverse_conversion_cache.clear()
            
            # 获取配音段落数据
            voice_segments = project_data.get('voice_generation', {}).get('voice_segments', [])
            
            # 获取图像映射数据
            shot_image_mappings = project_data.get('shot_image_mappings', {})
            
            # 获取分镜数据
            storyboard_data = project_data.get('five_stage_storyboard', {})
            
            logger.info(f"初始化镜头映射: {len(voice_segments)}个配音段落, {len(shot_image_mappings)}个图像映射")
            
            # 创建统一的镜头映射
            self._create_unified_mappings(voice_segments, shot_image_mappings, storyboard_data)
            
            logger.info(f"镜头映射初始化完成，共 {len(self.shot_mappings)} 个映射")
            return True
            
        except Exception as e:
            logger.error(f"初始化镜头映射失败: {e}")
            return False
    
    def _create_unified_mappings(self, voice_segments: List[Dict],
                               shot_image_mappings: Dict[str, Any],
                               storyboard_data: Dict[str, Any]) -> None:
        """创建统一的镜头映射"""

        # 🔧 修复：只基于配音段落创建映射，不补充额外的映射
        # 统计每个场景的镜头数量
        scene_shot_counts = {}
        for segment in voice_segments:
            scene_id = segment.get('scene_id', 'scene_1')
            scene_id = self._normalize_scene_id(scene_id)
            if scene_id not in scene_shot_counts:
                scene_shot_counts[scene_id] = 0
            scene_shot_counts[scene_id] += 1

        # 为每个配音段落创建映射
        scene_shot_indices = {}  # 记录每个场景当前的镜头索引

        for i, segment in enumerate(voice_segments):
            global_index = i + 1
            scene_id = segment.get('scene_id', f'scene_{(i // 3) + 1}')
            scene_id = self._normalize_scene_id(scene_id)

            # 计算场景内的镜头编号
            if scene_id not in scene_shot_indices:
                scene_shot_indices[scene_id] = 0
            scene_shot_indices[scene_id] += 1
            shot_index_in_scene = scene_shot_indices[scene_id]

            shot_mapping = ShotMapping(
                global_index=global_index,
                scene_id=scene_id,
                shot_id=f"shot_{shot_index_in_scene}",
                text_segment_id=f"text_segment_{global_index:03d}",
                unified_key=f"{scene_id}_shot_{shot_index_in_scene}",
                original_text=segment.get('original_text', ''),
                scene_index=shot_index_in_scene
            )

            self.shot_mappings.append(shot_mapping)

            # 建立转换缓存
            self._update_conversion_cache(shot_mapping)

        # 排序确保一致性
        self.shot_mappings.sort(key=lambda x: x.global_index)
    
    def _normalize_scene_id(self, scene_id: str) -> str:
        """标准化场景ID格式"""
        if not scene_id:
            return "scene_1"
        
        # 如果已经是标准格式，直接返回
        if re.match(r'^scene_\d+$', scene_id):
            return scene_id
        
        # 提取数字
        numbers = re.findall(r'\d+', scene_id)
        if numbers:
            return f"scene_{numbers[0]}"
        
        return "scene_1"
    
    def _extract_scene_number(self, scene_id: str) -> int:
        """从场景ID中提取数字"""
        numbers = re.findall(r'\d+', scene_id)
        return int(numbers[0]) if numbers else 1
    

    
    def _update_conversion_cache(self, shot_mapping: ShotMapping) -> None:
        """更新ID转换缓存"""
        # text_segment_XXX -> scene_X_shot_Y
        self.id_conversion_cache[shot_mapping.text_segment_id] = shot_mapping.unified_key
        
        # scene_X_shot_Y -> text_segment_XXX
        self.reverse_conversion_cache[shot_mapping.unified_key] = shot_mapping.text_segment_id
        
        # 其他可能的格式
        self.id_conversion_cache[f"镜头{shot_mapping.global_index}"] = shot_mapping.unified_key
        self.id_conversion_cache[str(shot_mapping.global_index)] = shot_mapping.unified_key
    
    def convert_id(self, source_id: str, target_format: str = "unified") -> Optional[str]:
        """
        转换ID格式
        
        Args:
            source_id: 源ID
            target_format: 目标格式 ("unified", "text_segment", "shot_only")
        
        Returns:
            转换后的ID，失败返回None
        """
        try:
            # 直接查找缓存
            if target_format == "unified" and source_id in self.id_conversion_cache:
                return self.id_conversion_cache[source_id]
            
            if target_format == "text_segment" and source_id in self.reverse_conversion_cache:
                return self.reverse_conversion_cache[source_id]
            
            # 查找映射
            for mapping in self.shot_mappings:
                if (source_id == mapping.text_segment_id or 
                    source_id == mapping.unified_key or
                    source_id == f"镜头{mapping.global_index}" or
                    source_id == str(mapping.global_index)):
                    
                    if target_format == "unified":
                        return mapping.unified_key
                    elif target_format == "text_segment":
                        return mapping.text_segment_id
                    elif target_format == "shot_only":
                        return mapping.shot_id
            
            logger.warning(f"无法转换ID: {source_id} -> {target_format}")
            return None
            
        except Exception as e:
            logger.error(f"ID转换失败: {source_id} -> {target_format}, 错误: {e}")
            return None
    
    def get_mapping_by_id(self, shot_id: str) -> Optional[ShotMapping]:
        """根据任意格式的ID获取映射"""
        for mapping in self.shot_mappings:
            if (shot_id == mapping.text_segment_id or 
                shot_id == mapping.unified_key or
                shot_id == mapping.shot_id or
                shot_id == f"镜头{mapping.global_index}" or
                shot_id == str(mapping.global_index)):
                return mapping
        return None
    
    def get_all_mappings(self) -> List[ShotMapping]:
        """获取所有镜头映射"""
        return self.shot_mappings.copy()
    
    def get_mappings_by_scene(self, scene_id: str) -> List[ShotMapping]:
        """获取指定场景的所有镜头映射"""
        normalized_scene_id = self._normalize_scene_id(scene_id)
        return [mapping for mapping in self.shot_mappings if mapping.scene_id == normalized_scene_id]
    
    def validate_consistency(self) -> Tuple[bool, List[str]]:
        """验证映射一致性"""
        issues = []
        
        # 检查全局索引连续性
        global_indices = [mapping.global_index for mapping in self.shot_mappings]
        global_indices.sort()
        
        for i, index in enumerate(global_indices):
            if i > 0 and index != global_indices[i-1] + 1:
                issues.append(f"全局索引不连续: {global_indices[i-1]} -> {index}")
        
        # 检查重复的unified_key
        unified_keys = [mapping.unified_key for mapping in self.shot_mappings]
        if len(unified_keys) != len(set(unified_keys)):
            issues.append("存在重复的unified_key")
        
        # 检查重复的text_segment_id
        text_segment_ids = [mapping.text_segment_id for mapping in self.shot_mappings]
        if len(text_segment_ids) != len(set(text_segment_ids)):
            issues.append("存在重复的text_segment_id")
        
        return len(issues) == 0, issues

    def sync_with_project_data(self, project_data: Dict[str, Any]) -> bool:
        """将映射同步到项目数据"""
        try:
            # 确保voice_generation结构存在
            if 'voice_generation' not in project_data:
                project_data['voice_generation'] = {'voice_segments': []}

            # 确保shot_image_mappings结构存在
            if 'shot_image_mappings' not in project_data:
                project_data['shot_image_mappings'] = {}

            # 同步配音段落的ID格式
            voice_segments = project_data['voice_generation']['voice_segments']
            for i, segment in enumerate(voice_segments):
                if i < len(self.shot_mappings):
                    mapping = self.shot_mappings[i]
                    # 更新ID字段但保留其他数据
                    segment['shot_id'] = mapping.text_segment_id
                    segment['scene_id'] = mapping.scene_id

            # 同步图像映射的键格式
            shot_image_mappings = project_data['shot_image_mappings']
            updated_mappings = {}

            for mapping in self.shot_mappings:
                # 查找对应的图像映射数据
                old_data = None
                for key, data in shot_image_mappings.items():
                    if (key == mapping.unified_key or
                        key == mapping.text_segment_id or
                        self._keys_match(key, mapping)):
                        old_data = data
                        break

                if old_data:
                    # 使用统一键格式保存
                    updated_mappings[mapping.unified_key] = old_data
                    # 确保数据中的ID字段正确
                    updated_mappings[mapping.unified_key]['scene_id'] = mapping.scene_id
                    updated_mappings[mapping.unified_key]['shot_id'] = mapping.shot_id

            project_data['shot_image_mappings'] = updated_mappings

            logger.info(f"项目数据同步完成，{len(voice_segments)}个配音段落，{len(updated_mappings)}个图像映射")
            return True

        except Exception as e:
            logger.error(f"项目数据同步失败: {e}")
            return False

    def _keys_match(self, key: str, mapping: ShotMapping) -> bool:
        """检查键是否匹配映射"""
        # 尝试各种可能的匹配方式
        possible_matches = [
            mapping.unified_key,
            mapping.text_segment_id,
            f"scene_1_{mapping.shot_id}",
            f"scene_1_shot_{mapping.global_index}",
            str(mapping.global_index)
        ]

        return key in possible_matches

    def create_missing_mappings(self, target_count: int) -> List[ShotMapping]:
        """创建缺失的镜头映射"""
        current_count = len(self.shot_mappings)
        new_mappings = []

        for i in range(current_count, target_count):
            global_index = i + 1
            scene_number = (i // 5) + 1  # 每5个镜头一个场景
            shot_index_in_scene = (i % 5) + 1

            shot_mapping = ShotMapping(
                global_index=global_index,
                scene_id=f"scene_{scene_number}",
                shot_id=f"shot_{shot_index_in_scene}",
                text_segment_id=f"text_segment_{global_index:03d}",
                unified_key=f"scene_{scene_number}_shot_{shot_index_in_scene}",
                original_text="",
                scene_index=shot_index_in_scene
            )

            new_mappings.append(shot_mapping)
            self.shot_mappings.append(shot_mapping)
            self._update_conversion_cache(shot_mapping)

        return new_mappings

    def get_statistics(self) -> Dict[str, Any]:
        """获取映射统计信息"""
        scene_counts = {}
        for mapping in self.shot_mappings:
            scene_counts[mapping.scene_id] = scene_counts.get(mapping.scene_id, 0) + 1

        return {
            'total_shots': len(self.shot_mappings),
            'total_scenes': len(scene_counts),
            'shots_per_scene': scene_counts,
            'max_global_index': max([m.global_index for m in self.shot_mappings]) if self.shot_mappings else 0
        }
