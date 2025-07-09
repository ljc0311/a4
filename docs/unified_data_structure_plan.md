# 统一数据管理结构规划

## 设计原则

1. **单一数据源**：所有功能数据都保存在 `project.json` 文件中
2. **结构化存储**：每个功能模块有独立的数据字段
3. **关联性管理**：不同功能间的数据通过ID进行关联
4. **版本兼容**：新功能不破坏现有数据结构
5. **易于扩展**：为未来功能预留扩展空间

## 当前已实现的数据结构

```json
{
  "project_name": "项目名称",
  "created_time": "创建时间",
  "last_modified": "最后修改时间",
  "project_root": "项目根目录",
  "project_dir": "项目目录",
  
  // 文本内容
  "original_text": "原始文本",
  "rewritten_text": "改写文本",
  
  // 五阶段分镜系统
  "five_stage_storyboard": {
    "stage_data": {
      "1": { "world_bible": "世界观圣经" },
      "2": { "scenes_analysis": "场景分析" },
      "3": { "character_scene_data": "角色场景数据" },
      "4": { "storyboard_results": "分镜结果" },
      "5": { "optimization_suggestions": "优化建议" }
    }
  },
  
  // 镜头图片关联
  "shot_image_mappings": {
    "scene_1_shot_1": {
      "scene_id": "场景ID",
      "shot_id": "镜头ID",
      "main_image_path": "主图路径",
      "generated_images": ["图片列表"],
      "status": "生成状态"
    }
  }
}
```

## 🔧 配音优先工作流程数据结构 (已实现)

### 1. 配音优先工作流程数据
```json
{
  "voice_first_workflow": {
    "voice_segments": [
      {
        "index": 0,
        "scene_id": "场景ID",
        "shot_id": "镜头ID",
        "content": "配音文本内容",
        "audio_path": "音频文件路径",
        "duration": 6.0,
        "content_type": "台词/旁白",
        "sound_effect": "音效描述",
        "status": "已生成"
      }
    ],
    "image_requirements": [
      {
        "voice_segment_index": 0,
        "scene_id": "场景ID",
        "shot_id": "镜头ID",
        "image_index": 0,
        "prompt": "基础图像提示词",
        "consistency_prompt": "一致性描述",
        "enhanced_prompt": "LLM增强后提示词",
        "duration_coverage": [0.0, 3.0],
        "priority": 1
      }
    ],
    "config": {
      "min_duration_for_single_image": 3.0,
      "max_duration_for_single_image": 6.0,
      "images_per_6_seconds": 2
    }
  }
}
```

### 2. 配音-图像同步数据
```json
{
  "voice_image_sync": {
    "total_duration": 180.0,
    "segment_count": 25,
    "segments": [
      {
        "start_time": 0.0,
        "end_time": 3.0,
        "duration": 3.0,
        "voice_content": "配音内容",
        "image_path": "对应图像路径",
        "scene_id": "场景ID",
        "shot_id": "镜头ID",
        "transition_type": "cut/fade/dissolve"
      }
    ],
    "sync_config": {
      "min_image_duration": 1.5,
      "max_image_duration": 4.0,
      "transition_duration": 0.3
    },
    "quality_metrics": {
      "average_duration": 2.5,
      "coverage_ratio": 0.95,
      "segment_count": 25
    }
  }
}
```

## 后续功能数据结构规划

### 1. 传统配音功能 (Voice Generation)

```json
{
  "voice_generation": {
    "settings": {
      "default_voice_engine": "配音引擎",
      "voice_speed": 1.0,
      "voice_volume": 1.0,
      "output_format": "wav"
    },
    "character_voices": {
      "花铃": {
        "voice_id": "voice_001",
        "voice_name": "甜美女声",
        "voice_engine": "Azure TTS",
        "voice_settings": {
          "pitch": 1.2,
          "speed": 1.0,
          "volume": 0.8
        }
      },
      "大雷": {
        "voice_id": "voice_002",
        "voice_name": "温和男声",
        "voice_engine": "Azure TTS",
        "voice_settings": {
          "pitch": 0.8,
          "speed": 0.9,
          "volume": 1.0
        }
      }
    },
    "shot_voice_mappings": {
      "scene_1_shot_1": {
        "dialogue_segments": [
          {
            "character": "大雷",
            "text": "快吃吧。",
            "voice_file": "output/AI的作品/audio/scene_1_shot_1_dalei.wav",
            "duration": 2.5,
            "start_time": 0.0,
            "end_time": 2.5,
            "status": "已生成"
          }
        ],
        "narration_segments": [
          {
            "text": "旁白内容",
            "voice_file": "output/AI的作品/audio/scene_1_shot_1_narration.wav",
            "duration": 3.0,
            "start_time": 0.0,
            "end_time": 3.0,
            "status": "已生成"
          }
        ]
      }
    }
  }
}
```

### 2. 字幕功能 (Subtitle Generation)

```json
{
  "subtitle_generation": {
    "settings": {
      "font_family": "微软雅黑",
      "font_size": 24,
      "font_color": "#FFFFFF",
      "background_color": "#000000",
      "background_opacity": 0.7,
      "position": "bottom",
      "margin": 50
    },
    "shot_subtitle_mappings": {
      "scene_1_shot_1": {
        "subtitle_segments": [
          {
            "text": "快吃吧。",
            "start_time": 0.0,
            "end_time": 2.5,
            "character": "大雷",
            "style": {
              "font_color": "#FFD700",
              "position": "bottom"
            }
          }
        ],
        "subtitle_file": "output/AI的作品/subtitles/scene_1_shot_1.srt",
        "status": "已生成"
      }
    }
  }
}
```

### 3. 图生视频功能 (Image to Video)

```json
{
  "image_to_video": {
    "settings": {
      "default_engine": "Runway ML",
      "video_duration": 5.0,
      "video_fps": 24,
      "video_resolution": "1920x1080",
      "motion_intensity": 0.5
    },
    "shot_video_mappings": {
      "scene_1_shot_1": {
        "source_image": "output/AI的作品/images/pollinations/pollinations_1750226675218_0.png",
        "video_file": "output/AI的作品/videos/scene_1_shot_1.mp4",
        "duration": 5.0,
        "motion_prompt": "缓慢的镜头推拉，展示废墟全景",
        "generation_settings": {
          "engine": "Runway ML",
          "motion_intensity": 0.3,
          "camera_movement": "push_in"
        },
        "status": "已生成",
        "generated_time": "2025-06-18T15:00:00"
      }
    }
  }
}
```

### 4. 视频合成输出功能 (Video Composition)

```json
{
  "video_composition": {
    "settings": {
      "output_resolution": "1920x1080",
      "output_fps": 24,
      "output_format": "mp4",
      "video_codec": "h264",
      "audio_codec": "aac",
      "bitrate": "5000k"
    },
    "composition_timeline": {
      "total_duration": 120.0,
      "scenes": [
        {
          "scene_id": "scene_1",
          "scene_name": "场景1：废墟初现",
          "start_time": 0.0,
          "end_time": 20.0,
          "shots": [
            {
              "shot_id": "scene_1_shot_1",
              "video_file": "output/AI的作品/videos/scene_1_shot_1.mp4",
              "audio_file": "output/AI的作品/audio/scene_1_shot_1_combined.wav",
              "subtitle_file": "output/AI的作品/subtitles/scene_1_shot_1.srt",
              "start_time": 0.0,
              "end_time": 5.0,
              "transition": "fade_in"
            }
          ]
        }
      ]
    },
    "output_files": {
      "final_video": "output/AI的作品/final_output/猫与狗的流浪_final.mp4",
      "preview_video": "output/AI的作品/preview/猫与狗的流浪_preview.mp4",
      "audio_track": "output/AI的作品/final_output/猫与狗的流浪_audio.wav"
    },
    "composition_history": [
      {
        "version": "v1.0",
        "created_time": "2025-06-18T15:30:00",
        "file_path": "output/AI的作品/final_output/猫与狗的流浪_v1.0.mp4",
        "settings_snapshot": {}
      }
    ]
  }
}
```

### 5. 项目管理和状态跟踪

```json
{
  "project_status": {
    "workflow_progress": {
      "text_creation": "completed",
      "storyboard_generation": "completed", 
      "image_generation": "in_progress",
      "voice_generation": "not_started",
      "subtitle_generation": "not_started",
      "video_generation": "not_started",
      "final_composition": "not_started"
    },
    "statistics": {
      "total_scenes": 5,
      "total_shots": 27,
      "generated_images": 1,
      "generated_voices": 0,
      "generated_videos": 0,
      "completion_percentage": 15.5
    }
  }
}
```

## 实施计划

### 阶段1：配音功能
- 在 `project.json` 中添加 `voice_generation` 字段
- 实现角色配音设置和语音文件关联
- 确保配音数据与分镜数据的关联

### 阶段2：字幕功能  
- 添加 `subtitle_generation` 字段
- 实现字幕样式设置和时间轴管理
- 支持多语言字幕

### 阶段3：图生视频功能
- 添加 `image_to_video` 字段
- 实现图片到视频的转换和参数管理
- 支持多种视频生成引擎

### 阶段4：视频合成功能
- 添加 `video_composition` 字段
- 实现完整的视频合成流水线
- 支持预览和最终输出

### 阶段5：项目状态管理
- 添加 `project_status` 字段
- 实现进度跟踪和统计功能
- 提供项目完成度可视化

## 数据一致性保证

1. **原子性操作**：每次数据更新都是完整的事务
2. **备份机制**：重要操作前自动创建备份
3. **版本控制**：记录数据结构的版本变化
4. **错误恢复**：提供数据恢复和修复功能
5. **数据验证**：确保数据完整性和一致性

## 总结

通过这个统一的数据结构设计，所有后续功能都将：
- ✅ 使用单一的 `project.json` 文件
- ✅ 保持数据的关联性和一致性  
- ✅ 支持功能间的无缝协作
- ✅ 便于项目的备份和迁移
- ✅ 提供完整的项目状态跟踪
