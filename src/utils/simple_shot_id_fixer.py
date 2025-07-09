"""
简单的镜头ID修复工具
直接为每个配音段落创建对应的图像映射
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def fix_mars_project():
    """修复《在遥远的火星上》项目的ID不匹配问题"""
    project_path = Path("output/在遥远的火星上")
    project_json_path = project_path / "project.json"
    backup_path = project_path / "project.json.backup"
    
    try:
        # 恢复备份
        if backup_path.exists():
            import shutil
            shutil.copy2(backup_path, project_json_path)
            print("已恢复备份文件")
        
        # 读取项目数据
        with open(project_json_path, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        # 获取配音段落
        voice_segments = project_data.get('voice_generation', {}).get('voice_segments', [])
        print(f"配音段落数量: {len(voice_segments)}")
        
        # 清空现有图像映射
        project_data['shot_image_mappings'] = {}
        shot_image_mappings = project_data['shot_image_mappings']
        
        # 为每个配音段落创建对应的图像映射
        for i, segment in enumerate(voice_segments):
            global_index = i + 1
            
            # 计算场景和镜头编号
            scene_number = (i // 3) + 1  # 每3个镜头一个场景
            shot_number = (i % 3) + 1    # 场景内镜头编号
            
            # 更新配音段落的ID格式
            segment['scene_id'] = f"scene_{scene_number}"
            segment['shot_id'] = f"text_segment_{global_index:03d}"
            
            # 创建对应的图像映射
            unified_key = f"scene_{scene_number}_shot_{shot_number}"
            shot_image_mappings[unified_key] = {
                'scene_id': f"scene_{scene_number}",
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
            
            print(f"处理镜头 {global_index}: {segment['scene_id']}_{segment['shot_id']} -> {unified_key}")
        
        # 保存修复后的项目文件
        with open(project_json_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        
        print(f"修复完成！")
        print(f"配音段落数量: {len(voice_segments)}")
        print(f"图像映射数量: {len(shot_image_mappings)}")
        
        # 验证修复结果
        if len(voice_segments) == len(shot_image_mappings):
            print("✅ 配音段落和图像映射数量匹配")
            return True
        else:
            print("❌ 配音段落和图像映射数量不匹配")
            return False
            
    except Exception as e:
        print(f"修复失败: {e}")
        return False


def test_id_conversion():
    """测试ID转换逻辑"""
    print("测试ID转换逻辑:")
    
    # 模拟35个配音段落
    for i in range(35):
        global_index = i + 1
        scene_number = (i // 3) + 1
        shot_number = (i % 3) + 1
        
        voice_id = f"text_segment_{global_index:03d}"
        scene_id = f"scene_{scene_number}"
        unified_key = f"scene_{scene_number}_shot_{shot_number}"
        
        print(f"{global_index:2d}: {scene_id}_{voice_id} -> {unified_key}")


if __name__ == "__main__":
    # 先测试转换逻辑
    test_id_conversion()
    
    print("\n" + "="*50)
    print("开始修复项目...")
    
    # 执行修复
    success = fix_mars_project()
    
    if success:
        print("\n🎉 项目修复成功！现在配音段落和图像映射完全匹配。")
    else:
        print("\n❌ 项目修复失败。")
