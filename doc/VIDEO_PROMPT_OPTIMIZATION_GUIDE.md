# 🎬 图转视频提示词优化指南

## 📋 问题分析

### 🔍 当前存在的问题

1. **提示词为空**：所有视频生成记录中的 `prompt` 字段都是空的
2. **使用图像提示词**：直接使用图像生成的 `enhanced_prompt`，不适合视频生成
3. **静态描述过多**：包含大量"静止"、"画面"、"构图"等静态词汇
4. **缺少动态元素**：没有运动、摄像机移动等视频专用描述

### 📊 优化前后对比

#### 优化前（图像提示词）
```
特写镜头下，侧面捕捉现代老水手林海，银白色稀疏头发在侧光中闪烁，深陷锐利眼睛透过深蓝色麻布渔夫服的磨损痕迹，坚定望向远方的眼神如同一道光芒，静止的画面中，三分法构图更显其沉静与坚韧。水彩画风，柔和笔触，粉彩色，插画，温柔。
```

#### 优化后（视频提示词）
```
an elderly sailor named Lin Hai gazing towards in a peaceful environment with gentle, flowing movements. The camera slowly pans to follow the action. Natural lighting shifts subtly. smooth motion, natural movement, cinematic flow, high quality video
```

## 🎯 优化策略

### 1. **移除静态描述**
- ❌ 移除：`静止`、`画面静止`、`静谧`、`静态`
- ❌ 移除：`水彩画风`、`柔和笔触`、`粉彩色`、`插画`
- ❌ 移除：`三分法构图`、`对称构图`、`对角线构图`

### 2. **添加动态元素**
- ✅ 添加：角色动作描述
- ✅ 添加：摄像机运动
- ✅ 添加：光照变化
- ✅ 添加：运动质量描述

### 3. **根据时长调整**
- **3秒以下**：`with subtle movements`
- **3-6秒**：`with gentle, flowing movements`
- **6秒以上**：`with smooth, continuous movements`

## 🛠️ 技术实现

### 新增功能

1. **视频专用优化方法**
   ```python
   def optimize_for_video(self, image_prompt: str, shot_info: Dict = None, duration: float = 5.0) -> str
   ```

2. **静态描述清理**
   ```python
   def _clean_for_video(self, image_prompt: str) -> str
   ```

3. **视频提示词构建**
   ```python
   def _build_video_prompt(self, scene_info: Dict, duration: float) -> str
   ```

### 角色识别扩展

- `林海` → `an elderly sailor named Lin Hai`
- `小雨` → `a young girl named Xiao Yu`
- `老水手` → `an elderly sailor`
- `老人` → `an elderly man`

### 场景识别扩展

- `海面`/`海洋`/`大海` → `on the vast ocean`
- `船`/`渔船` → `on a fishing boat`
- `海底` → `in the underwater world`
- `城市` → `in an ancient city`

### 动作识别扩展

- `坐着` → `sitting peacefully`
- `站着` → `standing calmly`
- `望向` → `gazing towards`
- `摇晃` → `swaying gently`
- `闪烁` → `flickering softly`

## 📈 优化效果

### 质量提升

1. **更适合视频生成**：移除静态描述，添加动态元素
2. **提示词更精准**：专门针对CogVideoX优化
3. **运动更自然**：根据时长调整运动描述
4. **摄像机运动**：添加专业的摄像机移动描述

### 性能优化

1. **提示词长度控制**：避免过长影响生成质量
2. **关键信息保留**：保留角色、场景、动作等核心信息
3. **英文输出**：CogVideoX对英文提示词支持更好

## 🚀 使用方法

### 在代码中使用

```python
from src.processors.cogvideox_prompt_optimizer import CogVideoXPromptOptimizer

# 创建优化器
optimizer = CogVideoXPromptOptimizer()

# 优化图像提示词为视频提示词
video_prompt = optimizer.optimize_for_video(
    image_prompt="原始图像提示词",
    shot_info={"shot_type": "close_up"},
    duration=5.0
)
```

### 自动应用

系统已自动集成到视频生成流程中：
- 视频生成时自动调用 `optimize_for_video` 方法
- 根据设置的视频时长自动调整运动描述
- 生成的视频提示词会记录到日志中

## 📝 建议配置

### 推荐参数

```json
{
  "duration": 5.0,
  "fps": 30,
  "motion_intensity": 0.5,
  "width": 1024,
  "height": 1024
}
```

### 质量设置

- **运动强度**：0.3-0.7 之间，避免过度运动
- **视频时长**：3-8秒最佳，过长可能影响质量
- **分辨率**：1024x1024 或 1920x1080

## 🔧 进一步优化建议

### 1. 个性化优化
- 根据不同类型场景（人物、风景、动作）使用不同模板
- 支持用户自定义提示词模板

### 2. 智能分析
- 分析图像内容自动判断最佳运动类型
- 根据音频内容调整视频节奏

### 3. 质量监控
- 记录优化前后的生成质量对比
- 根据用户反馈持续改进优化策略

## 📊 测试结果

根据测试，新的视频提示词优化功能：
- ✅ 成功识别角色和场景
- ✅ 正确移除静态描述
- ✅ 添加适当的动态元素
- ✅ 根据时长调整运动描述
- ✅ 生成专业的英文提示词

预期能显著提升图转视频的生成质量！
