# 统一数据管理开发指南

## 📋 概述

本指南确保所有后续功能开发都遵循统一数据管理原则，将所有项目数据保存在单一的 `project.json` 文件中，避免分散保存。

## 🎯 核心原则

### ✅ 必须遵循
- **单一数据源**：所有功能数据都保存在 `project.json` 文件中
- **结构化存储**：每个功能模块有独立的数据字段
- **关联性管理**：不同功能间通过 `scene_id` 和 `shot_id` 进行关联
- **统一接口**：使用 `UnifiedDataManager` 类进行数据操作

### ❌ 禁止行为
- 创建独立的配置文件或数据文件
- 将数据分散保存在多个位置
- 直接操作文件系统进行数据持久化
- 绕过统一数据管理器直接修改 `project.json`

## 🏗️ 数据结构规范

### 当前已实现的功能模块

```json
{
  // 基础项目信息
  "project_name": "项目名称",
  "created_time": "创建时间",
  "last_modified": "最后修改时间",
  
  // 文本内容
  "original_text": "原始文本",
  "rewritten_text": "改写文本",
  
  // 五阶段分镜系统
  "five_stage_storyboard": { ... },
  
  // 图像生成
  "shot_image_mappings": { ... },
  
  // 配音功能 ✅ 已实现
  "voice_generation": {
    "settings": { ... },
    "character_voices": { ... },
    "shot_voice_mappings": { ... }
  },
  
  // 字幕功能 ✅ 已实现
  "subtitle_generation": {
    "settings": { ... },
    "shot_subtitle_mappings": { ... }
  },
  
  // 图生视频功能 ✅ 已实现
  "image_to_video": {
    "settings": { ... },
    "shot_video_mappings": { ... }
  },
  
  // 视频合成功能 ✅ 已实现
  "video_composition": {
    "settings": { ... },
    "composition_timeline": { ... },
    "output_files": { ... },
    "composition_history": [ ... ]
  },
  
  // 项目状态管理 ✅ 已实现
  "project_status": {
    "workflow_progress": { ... },
    "statistics": { ... }
  }
}
```

## 🛠️ 开发规范

### 1. 使用统一数据管理器

```python
from src.utils.unified_data_manager import UnifiedDataManager

# 初始化数据管理器
data_manager = UnifiedDataManager(project_path)

# 获取数据
voice_settings = data_manager.get_data("voice_generation.settings")

# 设置数据
data_manager.set_data("voice_generation.settings.voice_speed", 1.2)

# 更新镜头映射
data_manager.update_voice_mapping("scene_1", "shot_1", voice_data)
```

### 2. 镜头数据关联规范

所有镜头相关数据都使用统一的键格式：`{scene_id}_{shot_id}`

```python
# 正确的镜头键格式
shot_key = f"scene_{scene_index}_shot_{shot_index}"

# 示例：scene_1_shot_1, scene_2_shot_3
```

### 3. 数据更新流程

```python
def update_feature_data(scene_id, shot_id, feature_data):
    """更新功能数据的标准流程"""
    
    # 1. 获取数据管理器
    data_manager = UnifiedDataManager(project_path)
    
    # 2. 验证数据结构
    data_manager.ensure_data_structure()
    
    # 3. 更新数据
    success = data_manager.update_xxx_mapping(scene_id, shot_id, feature_data)
    
    # 4. 更新项目状态（如需要）
    if success:
        data_manager.update_project_status("feature_name", "completed")
    
    return success
```

### 4. 新功能开发模板

当开发新功能时，请按以下步骤进行：

#### 步骤1：设计数据结构
```python
# 在 unified_data_manager.py 的 _create_default_structure 方法中添加
"new_feature": {
    "settings": {
        "default_setting": "value"
    },
    "shot_mappings": {}
}
```

#### 步骤2：添加数据操作方法
```python
def update_new_feature_mapping(self, scene_id: str, shot_id: str, data: Dict[str, Any]) -> bool:
    """更新新功能映射"""
    shot_key = f"{scene_id}_{shot_id}"
    return self.set_data(f"new_feature.shot_mappings.{shot_key}", data)
```

#### 步骤3：在功能模块中使用
```python
class NewFeatureManager:
    def __init__(self, project_path):
        self.data_manager = UnifiedDataManager(project_path)
    
    def process_shot(self, scene_id, shot_id, parameters):
        # 处理逻辑
        result_data = self._process_logic(parameters)
        
        # 保存结果到统一数据管理
        self.data_manager.update_new_feature_mapping(scene_id, shot_id, result_data)
```

## 📊 数据验证和测试

### 开发时必须进行的测试

1. **数据结构完整性测试**
```python
def test_data_structure():
    data_manager = UnifiedDataManager(test_project_path)
    data_manager.ensure_data_structure()
    
    # 验证新功能字段存在
    assert data_manager.get_data("new_feature") is not None
```

2. **数据保存和加载测试**
```python
def test_data_persistence():
    # 保存测试数据
    data_manager.set_data("new_feature.test_field", "test_value")
    
    # 重新加载验证
    new_manager = UnifiedDataManager(test_project_path)
    assert new_manager.get_data("new_feature.test_field") == "test_value"
```

3. **镜头关联测试**
```python
def test_shot_mapping():
    data_manager.update_new_feature_mapping("scene_1", "shot_1", test_data)
    
    # 验证数据正确保存
    shot_data = data_manager.get_shot_data("scene_1", "shot_1")
    assert shot_data["new_feature"] is not None
```

## 🔧 常用操作示例

### 配音功能示例
```python
# 添加角色配音设置
character_voice = {
    "voice_id": "voice_001",
    "voice_name": "甜美女声",
    "voice_engine": "Azure TTS"
}
data_manager.set_data("voice_generation.character_voices.花铃", character_voice)

# 添加镜头配音
voice_mapping = {
    "dialogue_segments": [...],
    "narration_segments": [...]
}
data_manager.update_voice_mapping("scene_1", "shot_1", voice_mapping)
```

### 字幕功能示例
```python
# 添加字幕映射
subtitle_mapping = {
    "subtitle_segments": [...],
    "subtitle_file": "path/to/subtitle.srt",
    "status": "已生成"
}
data_manager.update_subtitle_mapping("scene_1", "shot_1", subtitle_mapping)
```

## 🚨 注意事项

1. **备份机制**：重要操作前会自动创建备份
2. **错误处理**：所有数据操作都有错误处理和日志记录
3. **性能考虑**：大量数据操作时可以设置 `auto_save=False` 然后手动保存
4. **版本兼容**：新功能不能破坏现有数据结构

## 📝 开发检查清单

在提交新功能代码前，请确认：

- [ ] 所有数据都保存在 `project.json` 中
- [ ] 使用了 `UnifiedDataManager` 进行数据操作
- [ ] 添加了相应的数据结构定义
- [ ] 编写了数据验证测试
- [ ] 更新了项目状态管理
- [ ] 没有创建额外的配置文件
- [ ] 遵循了镜头关联规范

## 🎉 总结

通过遵循这个统一数据管理指南，我们确保：

✅ **数据一致性**：所有功能数据都在一个地方  
✅ **易于维护**：统一的数据操作接口  
✅ **便于备份**：只需要备份一个文件  
✅ **功能协作**：不同功能间数据无缝关联  
✅ **项目迁移**：简单的项目复制和恢复  

遵循这些原则，我们的AI视频生成器将拥有一个强大、一致、易于维护的数据管理系统！
