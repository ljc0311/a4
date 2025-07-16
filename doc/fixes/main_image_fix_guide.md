# 主图设置功能修复指南

## 问题描述

之前"设为主图"按钮存在以下问题：
1. 点击"设为主图"按钮后，主图信息没有正确保存到项目数据中
2. 视频生成时无法正确获取用户选择的主图
3. 视频生成可能使用错误的图片进行图转视频

## 修复内容

### 1. 修复设为主图功能 (`storyboard_image_generation_tab.py`)

**修复位置**: `set_as_main_image()` 方法

**修复内容**:
- 设置主图时同时更新 `main_image_path` 和 `image_path` 字段
- 确保视频生成能正确获取主图路径
- 添加详细的日志记录

```python
# 修复前
shot_data['main_image_path'] = current_image

# 修复后  
shot_data['main_image_path'] = current_image
shot_data['image_path'] = current_image  # 确保视频生成能正确获取主图
```

### 2. 修复项目数据保存 (`storyboard_image_generation_tab.py`)

**修复位置**: `_save_shot_image_mapping()` 方法

**修复内容**:
- 保存镜头图片映射时确保 `image_path` 指向主图
- 如果设置了主图，优先使用主图路径

```python
# 修复逻辑
if main_image_path and not image_path:
    image_path = main_image_path
elif main_image_path and image_path != main_image_path:
    image_path = main_image_path
```

### 3. 修复视频生成获取图片逻辑 (`video_generation_tab.py`)

**修复位置**: 多个获取图片路径的方法

**修复内容**:
- 所有获取图片路径的地方都优先使用 `main_image_path`
- 保持向后兼容性，如果没有主图路径则使用 `image_path`

**修复的方法**:
1. `_create_scene_data_from_project()` - 方法1：从shot_image_mappings获取
2. `_create_scene_data_from_project()` - 方法2：从image_generation获取  
3. `_create_scene_data_from_project()` - 方法3：从images列表获取
4. `_load_from_legacy_format()` - 从shot数据获取
5. `_get_scene_images()` - 获取场景图片

```python
# 修复前
image_path = img_data.get('image_path', '') or img_data.get('main_image_path', '')

# 修复后
image_path = img_data.get('main_image_path', '') or img_data.get('image_path', '')
```

## 使用方法

### 设置主图
1. 在分镜图像生成标签页中，选择一个镜头
2. 在右侧预览区域浏览生成的图片
3. 找到满意的图片后，点击"设为主图"按钮
4. 系统会显示"已设为主图"的确认消息

### 验证主图设置
1. 切换到视频生成标签页
2. 查看对应镜头的图片预览
3. 确认显示的是刚才设置的主图

### 视频生成
1. 在视频生成标签页中选择镜头
2. 点击"生成视频"按钮
3. 系统会使用设置的主图进行图转视频

## 技术细节

### 数据结构
项目数据中的镜头图片映射结构：
```json
{
  "shot_image_mappings": {
    "scene_1_shot_1": {
      "scene_id": "scene_1",
      "shot_id": "shot_1",
      "main_image_path": "/path/to/user/selected/main/image.jpg",
      "image_path": "/path/to/user/selected/main/image.jpg",
      "generated_images": ["/path/to/image1.jpg", "/path/to/image2.jpg"],
      "status": "已生成"
    }
  }
}
```

### 优先级顺序
视频生成时获取图片的优先级：
1. `main_image_path` (用户设置的主图)
2. `image_path` (当前图片路径)
3. 其他备用路径

### 兼容性
- 完全兼容旧的项目数据格式
- 如果旧项目只有 `image_path` 没有 `main_image_path`，系统会正常使用 `image_path`
- 新项目会同时保存两个字段确保数据完整性

## 测试验证

修复已通过全面测试，包括：
- ✅ 主图设置功能测试
- ✅ 项目数据保存测试  
- ✅ 视频生成获取图片测试
- ✅ 向后兼容性测试
- ✅ 多种数据格式支持测试

## 注意事项

1. **项目保存**: 设置主图后会自动保存到项目文件中
2. **文件存在性**: 系统会验证图片文件是否存在
3. **路径一致性**: 主图路径和当前图片路径会保持一致
4. **日志记录**: 所有操作都有详细的日志记录便于调试

## 故障排除

如果遇到问题：
1. 检查日志文件中的相关错误信息
2. 确认图片文件确实存在于指定路径
3. 验证项目数据中的 `shot_image_mappings` 字段
4. 重新设置主图并保存项目
