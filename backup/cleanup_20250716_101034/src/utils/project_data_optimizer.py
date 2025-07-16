"""
项目数据结构优化器
清理重复数据，优化数据结构，提高数据一致性
"""

import json
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

class ProjectDataOptimizer:
    """项目数据结构优化器"""
    
    def __init__(self):
        self.optimization_rules = {
            'remove_duplicates': True,
            'consolidate_voice_data': True,
            'optimize_image_mappings': True,
            'clean_empty_fields': True,
            'standardize_structure': True
        }
    
    def optimize_project_data(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """优化项目数据结构"""
        try:
            logger.info("开始优化项目数据结构...")
            
            # 创建优化后的数据副本
            optimized_data = project_data.copy()
            
            # 1. 清理重复的配音数据
            optimized_data = self._consolidate_voice_data(optimized_data)
            
            # 2. 优化图像映射数据
            optimized_data = self._optimize_image_mappings(optimized_data)
            
            # 3. 清理空字段
            optimized_data = self._clean_empty_fields(optimized_data)
            
            # 4. 标准化数据结构
            optimized_data = self._standardize_structure(optimized_data)
            
            # 5. 生成优化报告
            report = self._generate_optimization_report(project_data, optimized_data)
            logger.info(f"数据优化完成: {report}")
            
            return optimized_data
            
        except Exception as e:
            logger.error(f"项目数据优化失败: {e}")
            return project_data
    
    def _consolidate_voice_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """整合配音数据，消除重复"""
        try:
            # 获取主要的配音数据源
            voice_generation = data.get('voice_generation', {})
            voice_segments = voice_generation.get('voice_segments', [])
            
            # 获取配音优先工作流程数据
            voice_first_workflow = data.get('voice_first_workflow', {})
            workflow_segments = voice_first_workflow.get('voice_segments', [])
            
            if voice_segments and workflow_segments:
                logger.info("发现重复的配音数据，开始整合...")
                
                # 以voice_generation中的数据为主，补充workflow中的信息
                consolidated_segments = []
                
                for i, main_segment in enumerate(voice_segments):
                    # 复制主要数据
                    consolidated_segment = main_segment.copy()
                    
                    # 从workflow数据中补充缺失信息
                    if i < len(workflow_segments):
                        workflow_segment = workflow_segments[i]
                        
                        # 补充content字段（如果为空）
                        if not consolidated_segment.get('content') and workflow_segment.get('content'):
                            consolidated_segment['content'] = workflow_segment['content']
                        
                        # 补充duration字段
                        if not consolidated_segment.get('duration') and workflow_segment.get('duration'):
                            consolidated_segment['duration'] = workflow_segment['duration']
                    
                    consolidated_segments.append(consolidated_segment)
                
                # 更新主要数据源
                data['voice_generation']['voice_segments'] = consolidated_segments
                
                # 更新workflow数据以保持一致性
                data['voice_first_workflow']['voice_segments'] = consolidated_segments
                
                logger.info(f"配音数据整合完成，共 {len(consolidated_segments)} 个段落")
            
            return data
            
        except Exception as e:
            logger.error(f"配音数据整合失败: {e}")
            return data
    
    def _optimize_image_mappings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """优化图像映射数据结构"""
        try:
            shot_mappings = data.get('shot_image_mappings', {})
            
            if shot_mappings:
                logger.info(f"开始优化 {len(shot_mappings)} 个图像映射...")
                
                optimized_mappings = {}
                
                for shot_key, mapping_data in shot_mappings.items():
                    # 清理和标准化映射数据
                    optimized_mapping = {
                        'scene_id': mapping_data.get('scene_id', ''),
                        'shot_id': mapping_data.get('shot_id', ''),
                        'scene_name': mapping_data.get('scene_name', ''),
                        'shot_name': mapping_data.get('shot_name', ''),
                        'sequence': mapping_data.get('sequence', ''),
                        'main_image_path': mapping_data.get('main_image_path', ''),
                        'generated_images': mapping_data.get('generated_images', []),
                        'current_image_index': mapping_data.get('current_image_index', 0),
                        'status': mapping_data.get('status', '未生成'),
                        'updated_time': mapping_data.get('updated_time', '')
                    }
                    
                    # 移除重复的image_path字段（与main_image_path重复）
                    # 保持向后兼容性
                    if not optimized_mapping['main_image_path'] and mapping_data.get('image_path'):
                        optimized_mapping['main_image_path'] = mapping_data['image_path']
                    
                    optimized_mappings[shot_key] = optimized_mapping
                
                data['shot_image_mappings'] = optimized_mappings
                logger.info("图像映射数据优化完成")
            
            return data
            
        except Exception as e:
            logger.error(f"图像映射优化失败: {e}")
            return data
    
    def _clean_empty_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理空字段和无用数据"""
        try:
            # 清理空的顶级字段
            empty_fields = []
            for key, value in data.items():
                if value == "" or value == [] or value == {}:
                    empty_fields.append(key)
            
            for field in empty_fields:
                if field not in ['original_text', 'rewritten_text']:  # 保留这些可能为空的重要字段
                    logger.debug(f"移除空字段: {field}")
                    data.pop(field, None)
            
            # 清理五阶段数据中的空阶段
            five_stage = data.get('five_stage_storyboard', {})
            stage_data = five_stage.get('stage_data', {})
            
            for stage_num, stage_content in list(stage_data.items()):
                if not stage_content or stage_content == {}:
                    logger.debug(f"移除空的阶段数据: 阶段{stage_num}")
                    stage_data.pop(stage_num, None)
            
            return data
            
        except Exception as e:
            logger.error(f"清理空字段失败: {e}")
            return data
    
    def _standardize_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化数据结构"""
        try:
            # 确保必要的顶级字段存在
            required_fields = {
                'project_name': '',
                'description': '',
                'created_time': '',
                'last_modified': '',
                'project_root': '',
                'project_dir': '',
                'progress_status': {},
                'voice_generation': {},
                'five_stage_storyboard': {},
                'shot_image_mappings': {},
                'workflow_settings': {
                    'mode': 'voice_first',
                    'voice_first_enabled': True,
                    'image_generation_source': 'voice_content'
                }
            }
            
            for field, default_value in required_fields.items():
                if field not in data:
                    data[field] = default_value
            
            # 标准化时间戳格式
            if 'last_modified' in data:
                from datetime import datetime
                data['last_modified'] = datetime.now().isoformat()
            
            return data
            
        except Exception as e:
            logger.error(f"数据结构标准化失败: {e}")
            return data
    
    def _generate_optimization_report(self, original_data: Dict[str, Any], 
                                    optimized_data: Dict[str, Any]) -> str:
        """生成优化报告"""
        try:
            original_size = len(json.dumps(original_data, ensure_ascii=False))
            optimized_size = len(json.dumps(optimized_data, ensure_ascii=False))
            
            size_reduction = original_size - optimized_size
            reduction_percent = (size_reduction / original_size) * 100 if original_size > 0 else 0
            
            # 统计字段数量变化
            original_fields = self._count_fields(original_data)
            optimized_fields = self._count_fields(optimized_data)
            
            report = f"数据大小: {original_size} → {optimized_size} 字节 " \
                    f"(减少 {size_reduction} 字节, {reduction_percent:.1f}%), " \
                    f"字段数量: {original_fields} → {optimized_fields}"
            
            return report
            
        except Exception as e:
            logger.error(f"生成优化报告失败: {e}")
            return "优化报告生成失败"
    
    def _count_fields(self, data: Any, count: int = 0) -> int:
        """递归计算字段数量"""
        if isinstance(data, dict):
            count += len(data)
            for value in data.values():
                count = self._count_fields(value, count)
        elif isinstance(data, list):
            for item in data:
                count = self._count_fields(item, count)
        return count
    
    def backup_original_data(self, project_path: str) -> bool:
        """备份原始项目数据"""
        try:
            project_file = Path(project_path)
            if not project_file.exists():
                return False
            
            # 使用简洁的备份文件名，不包含时间戳
            backup_file = project_file.parent / f"{project_file.stem}_backup.json"
            
            import shutil
            shutil.copy2(project_file, backup_file)
            
            logger.info(f"项目数据已备份到: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"备份项目数据失败: {e}")
            return False
    
    def optimize_project_file(self, project_path: str) -> bool:
        """优化项目文件"""
        try:
            # 备份原始数据
            if not self.backup_original_data(project_path):
                logger.warning("备份失败，继续优化...")
            
            # 读取项目数据
            with open(project_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # 优化数据
            optimized_data = self.optimize_project_data(project_data)
            
            # 保存优化后的数据
            with open(project_path, 'w', encoding='utf-8') as f:
                json.dump(optimized_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"项目文件优化完成: {project_path}")
            return True
            
        except Exception as e:
            logger.error(f"优化项目文件失败: {e}")
            return False

def optimize_project_data_file(project_path: str) -> bool:
    """优化指定的项目数据文件"""
    optimizer = ProjectDataOptimizer()
    return optimizer.optimize_project_file(project_path)
