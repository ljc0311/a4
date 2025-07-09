#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理视频数据 - 移除重复的视频记录，只保留最新的
"""

import json
import os
from datetime import datetime

def clean_video_data(project_path):
    """清理项目中的重复视频数据"""
    project_file = os.path.join(project_path, "project.json")
    
    if not os.path.exists(project_file):
        print(f"❌ 项目文件不存在: {project_file}")
        return False
    
    # 备份原文件
    backup_file = project_file + ".backup_before_clean"
    with open(project_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 已创建备份: {backup_file}")
    
    # 加载项目数据
    with open(project_file, 'r', encoding='utf-8') as f:
        project_data = json.load(f)
    
    # 获取视频数据
    video_generation = project_data.get('video_generation', {})
    videos = video_generation.get('videos', [])
    
    print(f"📊 原始视频记录数: {len(videos)}")
    
    # 按shot_id分组，保留最新的
    shot_groups = {}
    for video in videos:
        shot_id = video.get('shot_id', '')
        if not shot_id:
            continue
        
        if shot_id not in shot_groups:
            shot_groups[shot_id] = []
        
        shot_groups[shot_id].append(video)
    
    print(f"📊 唯一镜头数: {len(shot_groups)}")
    
    # 为每个镜头保留最新的视频
    cleaned_videos = []
    removed_count = 0
    
    for shot_id, video_list in shot_groups.items():
        if len(video_list) == 1:
            # 只有一个视频，直接保留
            cleaned_videos.append(video_list[0])
        else:
            # 有多个视频，按创建时间排序，保留最新的
            video_list.sort(key=lambda x: x.get('created_time', ''), reverse=True)
            latest_video = video_list[0]
            cleaned_videos.append(latest_video)
            
            removed_count += len(video_list) - 1
            
            print(f"🔧 镜头 {shot_id}: 移除 {len(video_list) - 1} 个重复视频，保留最新的")
            for i, video in enumerate(video_list):
                status = "✅ 保留" if i == 0 else "❌ 移除"
                print(f"   {status}: {video.get('video_path', 'N/A')} ({video.get('created_time', 'N/A')})")
    
    # 按shot_id排序
    cleaned_videos.sort(key=lambda x: x.get('shot_id', ''))
    
    # 更新项目数据
    video_generation['videos'] = cleaned_videos
    project_data['video_generation'] = video_generation
    
    # 保存清理后的数据
    with open(project_file, 'w', encoding='utf-8') as f:
        json.dump(project_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 数据清理完成!")
    print(f"📊 清理前: {len(videos)} 个视频记录")
    print(f"📊 清理后: {len(cleaned_videos)} 个视频记录")
    print(f"🗑️ 移除了: {removed_count} 个重复记录")
    
    return True

def main():
    """主函数"""
    project_path = "F:/ai4/output/小猫吃饭"
    
    print("🧹 视频数据清理工具")
    print("=" * 50)
    
    if clean_video_data(project_path):
        print("\n✅ 清理成功！现在视频合成应该只会使用25个镜头的视频。")
    else:
        print("\n❌ 清理失败！")

if __name__ == "__main__":
    main()
