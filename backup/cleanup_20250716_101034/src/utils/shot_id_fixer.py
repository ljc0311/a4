"""
镜头ID修复工具
用于修复现有项目中配音段落和图像映射ID不匹配的问题
"""

import json
import logging
import os
from typing import Dict, List, Any, Tuple
from pathlib import Path

from src.utils.shot_id_manager import ShotIDManager, ShotMapping

logger = logging.getLogger(__name__)


class ShotIDFixer:
    """镜头ID修复器"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.project_json_path = self.project_path / 'project.json'
        self.backup_path = self.project_path / 'project.json.backup'
        self.shot_id_manager = ShotIDManager()
    
    def analyze_project(self) -> Dict[str, Any]:
        """分析项目中的ID不匹配问题"""
        try:
            if not self.project_json_path.exists():
                raise FileNotFoundError(f"项目文件不存在: {self.project_json_path}")
            
            with open(self.project_json_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # 获取配音段落
            voice_segments = project_data.get('voice_generation', {}).get('voice_segments', [])
            
            # 获取图像映射
            shot_image_mappings = project_data.get('shot_image_mappings', {})
            
            # 分析问题
            analysis = {
                'voice_segments_count': len(voice_segments),
                'image_mappings_count': len(shot_image_mappings),
                'voice_segment_ids': [],
                'image_mapping_keys': list(shot_image_mappings.keys()),
                'missing_in_images': [],
                'missing_in_voice': [],
                'id_format_issues': []
            }
            
            # 收集配音段落ID
            voice_ids = set()
            for segment in voice_segments:
                shot_id = segment.get('shot_id', '')
                scene_id = segment.get('scene_id', '')
                analysis['voice_segment_ids'].append(f"{scene_id}_{shot_id}")
                voice_ids.add(f"{scene_id}_{shot_id}")
            
            # 收集图像映射键
            image_keys = set(shot_image_mappings.keys())
            
            # 找出缺失的映射
            analysis['missing_in_images'] = list(voice_ids - image_keys)
            analysis['missing_in_voice'] = list(image_keys - voice_ids)
            
            # 检查ID格式问题
            for segment in voice_segments:
                shot_id = segment.get('shot_id', '')
                if shot_id.startswith('text_segment_'):
                    analysis['id_format_issues'].append({
                        'type': 'voice_segment_wrong_format',
                        'current_id': shot_id,
                        'scene_id': segment.get('scene_id', '')
                    })
            
            logger.info(f"项目分析完成: {analysis['voice_segments_count']}个配音段落, {analysis['image_mappings_count']}个图像映射")
            return analysis
            
        except Exception as e:
            logger.error(f"分析项目失败: {e}")
            raise
    
    def create_backup(self) -> bool:
        """创建项目文件备份"""
        try:
            if self.project_json_path.exists():
                import shutil
                shutil.copy2(self.project_json_path, self.backup_path)
                logger.info(f"项目备份已创建: {self.backup_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return False
    
    def fix_project_ids(self) -> bool:
        """修复项目中的ID不匹配问题"""
        try:
            # 创建备份
            if not self.create_backup():
                logger.warning("无法创建备份，继续修复...")
            
            # 加载项目数据
            with open(self.project_json_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # 初始化ID管理器
            self.shot_id_manager.initialize_from_project_data(project_data)
            
            # 修复配音段落ID格式
            self._fix_voice_segments(project_data)
            
            # 创建缺失的图像映射
            self._create_missing_image_mappings(project_data)
            
            # 同步ID管理器数据
            self.shot_id_manager.sync_with_project_data(project_data)
            
            # 保存修复后的项目文件
            with open(self.project_json_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            logger.info("项目ID修复完成")
            return True
            
        except Exception as e:
            logger.error(f"修复项目ID失败: {e}")
            return False
    
    def _fix_voice_segments(self, project_data: Dict[str, Any]) -> None:
        """修复配音段落的ID格式，保持原有场景分配"""
        voice_segments = project_data.get('voice_generation', {}).get('voice_segments', [])

        for i, segment in enumerate(voice_segments):
            # 保持原有的scene_id，只修复shot_id格式
            global_index = i + 1
            segment['shot_id'] = f"text_segment_{global_index:03d}"

            logger.debug(f"修复配音段落 {i+1}: {segment.get('scene_id')}_{segment['shot_id']}")

    def _create_missing_image_mappings(self, project_data: Dict[str, Any]) -> None:
        """为每个配音段落创建对应的图像映射"""
        voice_segments = project_data.get('voice_generation', {}).get('voice_segments', [])

        # 清空现有的图像映射，重新创建
        project_data['shot_image_mappings'] = {}
        shot_image_mappings = project_data['shot_image_mappings']

        # 统计每个场景的镜头数量
        scene_shot_counts = {}
        for segment in voice_segments:
            scene_id = segment.get('scene_id', 'scene_1')
            if scene_id not in scene_shot_counts:
                scene_shot_counts[scene_id] = 0
            scene_shot_counts[scene_id] += 1

        # 为每个配音段落创建图像映射
        scene_shot_indices = {}  # 记录每个场景当前的镜头索引
        created_count = 0

        for i, segment in enumerate(voice_segments):
            scene_id = segment.get('scene_id', 'scene_1')

            # 计算场景内的镜头编号
            if scene_id not in scene_shot_indices:
                scene_shot_indices[scene_id] = 0
            scene_shot_indices[scene_id] += 1
            shot_number = scene_shot_indices[scene_id]

            # 从scene_id中提取场景编号
            try:
                scene_number = int(scene_id.split('_')[1])
            except (IndexError, ValueError):
                scene_number = 1

            # 创建统一键格式
            unified_key = f"scene_{scene_number}_shot_{shot_number}"

            # 创建图像映射
            shot_image_mappings[unified_key] = {
                'scene_id': scene_id,
                'shot_id': f"shot_{shot_number}",
                'scene_name': f"场景{scene_number}",
                'shot_name': f"镜头{shot_number}",
                'sequence': f"{scene_number}-{shot_number}",
                'main_image_path': '',
                'image_path': '',
                'generated_images': [],
                'current_image_index': 0,
                'status': '未生成',
                'updated_time': '2025-07-08T17:00:00.000000'
            }
            created_count += 1
            logger.debug(f"创建图像映射: {unified_key} (场景{scene_number}第{shot_number}个镜头)")

        logger.info(f"重建了 {created_count} 个图像映射")
    
    def validate_fix(self) -> Tuple[bool, Dict[str, Any]]:
        """验证修复结果"""
        try:
            with open(self.project_json_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            voice_segments = project_data.get('voice_generation', {}).get('voice_segments', [])
            shot_image_mappings = project_data.get('shot_image_mappings', {})
            
            validation_result = {
                'voice_segments_count': len(voice_segments),
                'image_mappings_count': len(shot_image_mappings),
                'all_voice_have_images': True,
                'id_format_correct': True,
                'missing_mappings': []
            }
            
            # 检查每个配音段落是否有对应的图像映射
            # 重新计算每个场景的镜头编号
            scene_shot_indices = {}
            for i, segment in enumerate(voice_segments):
                scene_id = segment.get('scene_id', 'scene_1')

                # 计算场景内的镜头编号
                if scene_id not in scene_shot_indices:
                    scene_shot_indices[scene_id] = 0
                scene_shot_indices[scene_id] += 1
                shot_number = scene_shot_indices[scene_id]

                # 从scene_id中提取场景编号
                try:
                    scene_number = int(scene_id.split('_')[1])
                except (IndexError, ValueError):
                    scene_number = 1

                expected_key = f"scene_{scene_number}_shot_{shot_number}"

                if expected_key not in shot_image_mappings:
                    validation_result['all_voice_have_images'] = False
                    validation_result['missing_mappings'].append(expected_key)
                
                # 检查ID格式
                shot_id = segment.get('shot_id', '')
                if not shot_id.startswith('text_segment_'):
                    validation_result['id_format_correct'] = False
            
            is_valid = (validation_result['all_voice_have_images'] and 
                       validation_result['id_format_correct'])
            
            logger.info(f"验证结果: {'通过' if is_valid else '失败'}")
            return is_valid, validation_result
            
        except Exception as e:
            logger.error(f"验证修复结果失败: {e}")
            return False, {}


def fix_project_shot_ids(project_path: str) -> bool:
    """修复项目中的镜头ID不匹配问题"""
    try:
        fixer = ShotIDFixer(project_path)
        
        # 分析问题
        analysis = fixer.analyze_project()
        print(f"分析结果:")
        print(f"  配音段落数量: {analysis['voice_segments_count']}")
        print(f"  图像映射数量: {analysis['image_mappings_count']}")
        print(f"  缺失的图像映射: {len(analysis['missing_in_images'])}")
        print(f"  ID格式问题: {len(analysis['id_format_issues'])}")
        
        if analysis['voice_segments_count'] == analysis['image_mappings_count']:
            print("配音段落和图像映射数量已匹配，无需修复")
            return True
        
        # 执行修复
        print("开始修复...")
        if fixer.fix_project_ids():
            # 验证修复结果
            is_valid, validation = fixer.validate_fix()
            if is_valid:
                print("修复成功！配音段落和图像映射现在完全匹配")
                return True
            else:
                print(f"修复后验证失败: {validation}")
                return False
        else:
            print("修复失败")
            return False
            
    except Exception as e:
        print(f"修复过程中发生错误: {e}")
        return False


if __name__ == "__main__":
    # 测试修复《在遥远的火星上》项目
    project_path = "output/在遥远的火星上"
    fix_project_shot_ids(project_path)
