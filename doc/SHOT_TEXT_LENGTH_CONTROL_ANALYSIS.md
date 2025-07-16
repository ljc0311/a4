# 📋 镜头原文内容长度控制机制分析

## 🎯 核心问题
您希望在生成分镜脚本时，每个场景中的镜头原文内容在正常语速配音情况下能控制在10秒左右。

## 🔍 当前控制机制分析

### 1. **智能文本分割器 (IntelligentTextSplitter)**

#### 📍 位置：`src/utils/intelligent_text_splitter.py`

#### ⚙️ 核心配置参数
```python
@dataclass
class SplitConfig:
    target_duration: float = 10.0      # 🎯 目标时长（秒）
    min_duration: float = 5.0          # 最小时长（秒）
    max_duration: float = 15.0         # 最大时长（秒）
    tolerance: float = 2.0             # 容忍范围（秒）
    chinese_chars_per_second: float = 4.0  # 🔑 中文每秒字数
    english_words_per_second: float = 2.5  # 英文每秒词数
```

#### 🧮 时长估算算法
```python
def _estimate_duration(self, text: str) -> float:
    """估算文本的配音时长"""
    # 统计中文字符和英文单词
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    english_words = len([word for word in text.split() if word.isalpha()])
    
    # 计算基础时长
    if chinese_chars > english_words:
        # 主要是中文：每秒4个字
        base_duration = chinese_chars / self.config.chinese_chars_per_second
    else:
        # 主要是英文：每秒2.5个词
        base_duration = english_words / self.config.english_words_per_second
```

#### 📊 分割逻辑
1. **目标导向分割**：优先生成接近10秒的文本段
2. **语义完整性**：保持句子和段落的完整性
3. **动态调整**：根据内容长度自动调整分割策略
4. **质量评分**：综合时长和语义完整性评分

### 2. **配音界面的时长控制**

#### 📍 位置：`src/gui/voice_generation_tab.py`

#### 🎛️ 用户控制界面
```python
# 目标时长设置
self.target_duration = 10.0  # 默认目标时长10秒

# 时长调整控件
self.duration_spinbox = QDoubleSpinBox()
self.duration_spinbox.setRange(5.0, 30.0)  # 可调范围5-30秒
self.duration_spinbox.setValue(self.target_duration)
```

#### 🔄 智能重新分割功能
```python
def smart_resplit_text(self):
    """智能重新分割文本"""
    # 使用智能分割器重新分割
    voice_segments = create_voice_segments_with_duration_control(
        created_text, 
        self.target_duration  # 使用用户设置的目标时长
    )
```

### 3. **分镜脚本生成的控制机制**

#### 📍 位置：`src/models/llm_api.py`

#### 📏 分镜密度控制
```python
# 分镜数量指导原则
"- 每60-80字的文本内容应该生成至少1个分镜场景\n"
"- 每个对话回合必须有独立的分镜\n"
"- 每个动作或情感变化必须有独立的分镜\n"
```

#### 🎯 动态分镜数量计算
```python
# 为分段添加上下文提示 - 大幅增加分镜密度
expected_min_shots = max(8, len(segment) // 50)  # 每50字至少1个分镜
expected_max_shots = max(15, len(segment) // 30)  # 每30字至少1个分镜
```

## 📊 当前配音时长计算公式

### 中文文本
```
配音时长 = 中文字符数 ÷ 4 (字/秒)
```

### 英文文本
```
配音时长 = 英文单词数 ÷ 2.5 (词/秒)
```

### 示例计算
- **40个中文字符** = 40 ÷ 4 = **10秒**
- **25个英文单词** = 25 ÷ 2.5 = **10秒**

## 🎯 10秒时长控制的实现路径

### 1. **在配音界面中**
- ✅ 用户可以设置目标时长（默认10秒）
- ✅ 智能分割器自动按目标时长分割文本
- ✅ 支持手动重新分割

### 2. **在分镜生成中**
- ⚠️ **问题**：分镜生成主要关注内容完整性，不直接控制时长
- ⚠️ **现状**：按内容逻辑分割，可能产生长短不一的镜头

## 🔧 优化建议

### 1. **增强分镜生成的时长控制**

#### A. 修改分镜生成提示词
```python
# 在分镜生成提示词中添加时长控制要求
"**时长控制要求：**\n"
"- 每个分镜的文案内容应控制在35-45个中文字符（约8-12秒配音时长）\n"
"- 如果原文段落过长，应拆分为多个分镜\n"
"- 如果原文段落过短，可适当合并相邻内容\n"
"- 优先保证配音时长的合理性，同时兼顾内容完整性\n"
```

#### B. 添加后处理验证
```python
def validate_shot_duration(self, shots_data):
    """验证分镜时长并提供优化建议"""
    for shot in shots_data:
        text_content = shot.get('文案', '')
        estimated_duration = self._estimate_duration(text_content)
        
        if estimated_duration > 12:  # 超过12秒
            # 建议拆分
            pass
        elif estimated_duration < 8:  # 少于8秒
            # 建议合并
            pass
```

### 2. **统一时长控制标准**

#### A. 创建全局时长配置
```python
class GlobalDurationConfig:
    TARGET_DURATION = 10.0  # 目标时长
    MIN_DURATION = 8.0      # 最小时长
    MAX_DURATION = 12.0     # 最大时长
    CHINESE_SPEED = 4.0     # 中文语速
    ENGLISH_SPEED = 2.5     # 英文语速
```

#### B. 在分镜生成中应用
```python
# 计算理想的文案长度
ideal_chinese_chars = TARGET_DURATION * CHINESE_SPEED  # 40字
ideal_english_words = TARGET_DURATION * ENGLISH_SPEED  # 25词
```

### 3. **添加实时时长预览**

#### A. 在分镜表格中显示预估时长
```python
# 在分镜表格中添加"预估时长"列
headers = ["文案", "场景", "角色", "提示词", "预估时长", "主图", "视频运镜", "音频", "操作"]
```

#### B. 颜色标识时长状态
```python
# 根据时长给文案单元格着色
if duration < 8:
    cell.setBackground(QColor(255, 255, 0))  # 黄色：过短
elif duration > 12:
    cell.setBackground(QColor(255, 200, 200))  # 红色：过长
else:
    cell.setBackground(QColor(200, 255, 200))  # 绿色：合适
```

## 📈 实施优先级

### 🔥 高优先级
1. **修改分镜生成提示词**：添加明确的时长控制要求
2. **添加分镜时长验证**：生成后检查每个镜头的预估时长

### 🔶 中优先级
3. **统一时长配置**：创建全局配置类
4. **添加时长预览**：在界面中显示预估时长

### 🔷 低优先级
5. **智能优化算法**：自动调整过长或过短的分镜
6. **用户反馈机制**：根据实际配音效果调整参数

## 💡 总结

当前程序已经有较完善的时长控制机制，主要体现在**配音界面的智能分割器**中。但在**分镜脚本生成**阶段，时长控制相对较弱，主要关注内容完整性。

建议优先在分镜生成提示词中添加时长控制要求，并在生成后进行时长验证，这样可以在保证内容完整性的同时，更好地控制每个镜头的配音时长在10秒左右。
