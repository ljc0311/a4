# 🔧 视频合成页面数据加载问题修复

## 📋 问题描述

用户反映视频合成页面只显示一个镜头，而不是像之前那样显示全部已生成的镜头。

### 🔍 问题现象
- 视频合成页面只显示 1 个镜头（shot_7）
- 实际项目中有 36 个已生成的视频文件
- 项目数据中记录了 36 个视频条目

## 🛠️ 问题分析

### 根本原因
1. **页面初始化时无当前项目**：程序启动时视频合成页面没有当前项目，导致数据加载失败
2. **shot_id格式识别问题**：代码只识别 `text_segment_XXX` 格式，不识别 `shot_X` 格式
3. **页面切换时不重新加载**：用户切换到视频合成页面时，没有重新加载项目数据

### 测试验证结果
```
✅ 成功加载项目数据: 成语故事
📹 视频生成数据:
   - 视频总数: 36
   - 前5个视频的shot_id:
     1. shot_1 -> 文件存在: True
     2. shot_2 -> 文件存在: True
     3. shot_5 -> 文件存在: True
     4. shot_6 -> 文件存在: True
     5. shot_7 -> 文件存在: True

📁 视频文件目录:
   - 实际视频文件数: 36
   - 项目数据记录数: 36
```

## 🔧 修复方案

### 1. **增强项目数据加载逻辑**

#### A. 添加项目状态检查和重新获取
```python
def load_project_data(self):
    """加载项目数据"""
    if not self.project_manager:
        logger.warning("项目管理器未初始化")
        return
    
    # 🔧 修复：如果没有当前项目，尝试重新获取
    if not self.project_manager.current_project:
        logger.info("没有当前项目，尝试重新获取项目列表")
        self.project_manager.refresh_project_list()
        
        if not self.project_manager.current_project:
            logger.warning("没有当前项目，无法加载视频合成数据")
            self.show_no_project_message()
            return
```

#### B. 添加无项目状态处理
```python
def show_no_project_message(self):
    """显示无项目提示"""
    # 清空表格
    self.segments_table.setRowCount(0)
    
    # 在状态标签中显示提示
    if hasattr(self, 'status_label'):
        self.status_label.setText("请先选择一个项目")
```

### 2. **修复shot_id格式识别**

#### A. 支持多种shot_id格式
```python
# 从shot_id中提取序号来匹配音频文件和排序
# shot_id格式可能是 shot_X 或 text_segment_XXX
segment_number = None

# 尝试从 shot_X 格式提取
if shot_id.startswith('shot_'):
    try:
        segment_number = int(shot_id.split('_')[-1])
    except ValueError:
        pass

# 尝试从 text_segment_XXX 格式提取
elif 'text_segment_' in shot_id:
    try:
        segment_number = int(shot_id.split('_')[-1])
    except ValueError:
        pass
```

#### B. 扩展音频文件匹配格式
```python
possible_audio_files = [
    f"segment_{segment_number:03d}_text_segment_{segment_number:03d}.mp3",  # 标准格式
    f"segment_{segment_number:03d}_{shot_id}.mp3",  # 备用格式1
    f"{shot_id}.mp3",  # 简单格式
    f"text_segment_{segment_number:03d}.mp3",  # 简化格式
    f"shot_{segment_number}.mp3",  # shot格式
    f"shot_{segment_number:03d}.mp3",  # shot格式（补零）
]
```

### 3. **添加页面显示时重新加载**

```python
def showEvent(self, event):
    """页面显示时的事件处理"""
    super().showEvent(event)
    try:
        # 页面显示时重新加载项目数据
        logger.info("视频合成页面显示，重新加载项目数据")
        self.load_project_data()
    except Exception as e:
        logger.error(f"页面显示时加载数据失败: {e}")
```

### 4. **增强调试日志**

```python
for i, video_data in enumerate(videos_list):
    video_path = video_data.get('video_path', '')
    shot_id = video_data.get('shot_id', '')
    
    logger.info(f"处理视频 {i+1}/{len(videos_list)}: {shot_id} -> {video_path}")
    
    # 检查视频文件是否存在
    if not video_path or not os.path.exists(video_path):
        logger.warning(f"视频文件不存在: {video_path}")
        continue
```

## ✅ 修复效果

### 测试结果验证
```
=== 测试shot_id解析逻辑 ===

shot_id: shot_1               -> segment_number: 1
shot_id: shot_7               -> segment_number: 7
shot_id: shot_15              -> segment_number: 15
shot_id: text_segment_001     -> segment_number: 1
shot_id: text_segment_007     -> segment_number: 7

=== 测试音频文件匹配逻辑 ===

shot_1 (segment_number: 1) 可能的音频文件:
  - segment_001_text_segment_001.mp3                   -> 存在: True
  - segment_001_shot_1.mp3                             -> 存在: False
  - shot_1.mp3                                         -> 存在: False
  - text_segment_001.mp3                               -> 存在: False
  - shot_001.mp3                                       -> 存在: False
```

### 预期改进效果

1. **✅ 完整数据加载**：视频合成页面现在应该显示所有36个视频镜头
2. **✅ 格式兼容性**：支持 `shot_X` 和 `text_segment_XXX` 两种格式
3. **✅ 自动重新加载**：页面切换时自动重新加载项目数据
4. **✅ 错误处理**：无项目时显示友好提示
5. **✅ 调试信息**：详细的日志帮助排查问题

## 🎯 使用方法

### 验证修复效果
1. **启动程序**
2. **选择成语故事项目**
3. **切换到视频合成页面**
4. **检查镜头列表**：应该显示所有已生成的视频镜头

### 预期显示内容
- **片段列表**：显示 shot_1, shot_2, shot_5, shot_6, shot_7 等所有镜头
- **时长信息**：显示每个镜头的实际时长（从音频文件获取）
- **配音状态**：显示是否有对应的音频文件
- **操作按钮**：预览、删除等操作按钮

## 📝 技术要点

### 关键修复点
1. **项目状态管理**：确保页面显示时有有效的当前项目
2. **数据格式兼容**：支持不同的shot_id命名格式
3. **文件路径匹配**：正确匹配视频文件和音频文件
4. **错误处理**：优雅处理各种异常情况

### 代码改进
- 增加了详细的调试日志
- 改进了错误处理机制
- 增强了数据验证逻辑
- 添加了用户友好的提示信息

这个修复确保了视频合成页面能够正确加载和显示所有已生成的视频镜头，解决了用户反映的问题。
