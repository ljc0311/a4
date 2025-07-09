# 一致性控制系统使用指南

## 概述

本系统实现了一个渐进式智能一致性文生图系统，整合了角色一致性、场景一致性和智能提示词优化功能，为分镜图像生成提供了强大的一致性保障。

## 系统架构

### 核心组件

1. **ConsistencyEnhancedImageProcessor** - 一致性增强图像处理器
   - 位置：`src/processors/consistency_enhanced_image_processor.py`
   - 功能：提供一致性分析、提示词增强和图像生成

2. **ConsistencyControlPanel** - 一致性控制面板
   - 位置：`src/gui/consistency_control_panel.py`
   - 功能：提供可视化的一致性管理界面

3. **CharacterSceneManager** - 角色场景管理器
   - 位置：`src/utils/character_scene_manager.py`
   - 功能：管理角色和场景的一致性数据

### 数据结构

```python
# 一致性配置
class ConsistencyConfig:
    enable_character_consistency: bool = True
    enable_scene_consistency: bool = True
    character_weight: float = 0.8
    scene_weight: float = 0.6
    use_llm_analysis: bool = True
    progressive_enhancement: bool = True

# 一致性数据
class ConsistencyData:
    characters: Dict[str, Any]
    scenes: Dict[str, Any]
    relationships: Dict[str, Any]
    metadata: Dict[str, Any]

# 增强分镜
class EnhancedShot:
    original_shot: Shot
    enhanced_prompt: str
    character_consistency_prompt: str
    scene_consistency_prompt: str
    consistency_elements: List[str]
```

## 功能特性

### 1. 智能一致性分析

- **LLM驱动分析**：使用大语言模型分析分镜序列，识别角色和场景的一致性需求
- **基础规则分析**：当LLM不可用时，使用基础规则进行一致性分析
- **渐进式增强**：根据前序分镜的生成结果，动态调整后续分镜的一致性策略

### 2. 角色一致性管理

- **角色档案管理**：维护每个角色的外貌、服装、特征等信息
- **动态一致性提示**：根据角色在不同场景中的表现，生成适应性提示词
- **角色关系分析**：分析角色间的互动关系，确保表现一致

### 3. 场景一致性控制

- **环境特征管理**：管理场景的环境、光照、氛围等特征
- **场景转换优化**：优化场景间的过渡，保持视觉连贯性
- **时间线一致性**：确保同一场景在不同时间点的一致性

### 4. 提示词智能优化

- **多层次提示词合并**：将原始提示词与一致性提示词智能合并
- **权重平衡**：根据配置动态调整角色和场景一致性的权重
- **冲突解决**：自动检测和解决提示词间的冲突

## 使用方法

### 1. 基础使用流程

1. **创建项目**：在主界面创建新项目
2. **输入文本**：在文本处理标签页输入故事文本
3. **生成分镜**：使用五阶段分镜生成功能创建分镜脚本
4. **配置一致性**：切换到"🎨 一致性控制"标签页
5. **管理角色**：在角色管理选项卡中添加和编辑角色信息
6. **管理场景**：在场景管理选项卡中设置场景特征
7. **预览效果**：使用预览功能查看一致性增强效果
8. **生成图像**：开始生成具有一致性的分镜图像

### 2. 高级配置

#### 一致性配置选项

- **角色一致性权重**：控制角色一致性在提示词中的影响程度（0.0-1.0）
- **场景一致性权重**：控制场景一致性在提示词中的影响程度（0.0-1.0）
- **启用LLM分析**：是否使用大语言模型进行智能分析
- **渐进式增强**：是否启用基于前序结果的动态优化

#### 角色管理

```python
# 角色数据结构示例
character_data = {
    "name": "主角小明",
    "description": "一个勇敢的少年冒险家",
    "appearance": "黑色短发，明亮的眼睛，中等身材",
    "clothing": "蓝色冒险服，棕色皮靴",
    "personality": "勇敢、善良、机智",
    "consistency_prompt": "young brave adventurer, black short hair, bright eyes, blue adventure outfit"
}
```

#### 场景管理

```python
# 场景数据结构示例
scene_data = {
    "name": "神秘森林",
    "description": "充满魔法的古老森林",
    "environment": "茂密的树林，斑驳的阳光",
    "lighting": "柔和的自然光，神秘的氛围",
    "mood": "神秘、宁静、充满魔力",
    "consistency_prompt": "mystical ancient forest, dense trees, dappled sunlight, magical atmosphere"
}
```

### 3. API使用示例

```python
# 初始化一致性增强图像处理器
from processors.consistency_enhanced_image_processor import ConsistencyEnhancedImageProcessor
from utils.character_scene_manager import CharacterSceneManager

# 创建处理器
processor = ConsistencyEnhancedImageProcessor(
    service_manager=service_manager,
    character_scene_manager=character_scene_manager
)

# 配置一致性参数
config = ConsistencyConfig(
    enable_character_consistency=True,
    enable_scene_consistency=True,
    character_weight=0.8,
    scene_weight=0.6,
    use_llm_analysis=True
)

# 生成一致性图像
result = await processor.generate_consistent_storyboard_images(
    storyboard=storyboard_result,
    config=image_config,
    consistency_config=config,
    progress_callback=progress_callback
)
```

## 技术实现细节

### 1. 一致性分析算法

```python
def _analyze_consistency(self, storyboard: StoryboardResult) -> Dict[str, Any]:
    """分析分镜序列的一致性需求"""
    if self.config.use_llm_analysis:
        return await self._llm_analysis(storyboard)
    else:
        return self._basic_analysis(storyboard)
```

### 2. 提示词增强策略

```python
def _enhance_shot_prompt(self, shot: Shot, consistency_data: ConsistencyData, 
                        analysis_result: Dict[str, Any]) -> EnhancedShot:
    """增强单个分镜的提示词"""
    enhanced_shot = EnhancedShot(original_shot=shot)
    
    # 构建一致性元素
    consistency_elements = []
    
    if self.config.enable_character_consistency:
        char_prompt = self._build_character_consistency_prompt(shot, consistency_data, analysis_result)
        consistency_elements.append(char_prompt)
    
    if self.config.enable_scene_consistency:
        scene_prompt = self._build_scene_consistency_prompt(shot, consistency_data, analysis_result)
        consistency_elements.append(scene_prompt)
    
    # 合并提示词
    enhanced_shot.enhanced_prompt = self._merge_prompts(shot.image_prompt, consistency_elements)
    
    return enhanced_shot
```

### 3. 渐进式优化机制

```python
def _apply_progressive_enhancement(self, enhanced_shots: List[EnhancedShot], 
                                 generation_results: List[Any]) -> List[EnhancedShot]:
    """应用渐进式增强"""
    for i, (shot, result) in enumerate(zip(enhanced_shots, generation_results)):
        if i > 0 and result:
            # 基于前序结果优化当前分镜
            shot.enhanced_prompt = self._optimize_based_on_previous(shot, generation_results[:i])
    
    return enhanced_shots
```

## 配置文件

### 一致性配置文件示例

```json
{
  "consistency_config": {
    "enable_character_consistency": true,
    "enable_scene_consistency": true,
    "character_weight": 0.8,
    "scene_weight": 0.6,
    "use_llm_analysis": true,
    "progressive_enhancement": true,
    "max_consistency_elements": 5,
    "prompt_merge_strategy": "weighted"
  },
  "character_defaults": {
    "consistency_prompt_template": "{name}, {appearance}, {clothing}",
    "weight_in_prompt": 0.8
  },
  "scene_defaults": {
    "consistency_prompt_template": "{environment}, {lighting}, {mood}",
    "weight_in_prompt": 0.6
  }
}
```

## 故障排除

### 常见问题

1. **一致性控制面板无法加载**
   - 检查项目是否已创建
   - 确认服务管理器已正确初始化

2. **角色/场景数据丢失**
   - 检查项目目录权限
   - 确认数据文件未被损坏

3. **LLM分析失败**
   - 检查LLM服务配置
   - 确认网络连接正常
   - 可切换到基础分析模式

4. **图像生成质量不佳**
   - 调整一致性权重参数
   - 优化角色和场景描述
   - 检查原始提示词质量

### 日志分析

系统会在以下位置记录详细日志：
- 应用日志：`logs/system.log`
- 一致性分析日志：包含在系统日志中，标记为`[ConsistencyAnalyzer]`
- 图像生成日志：包含在系统日志中，标记为`[ConsistencyEnhancedImageProcessor]`

## 性能优化

### 1. 缓存策略

- **一致性分析缓存**：缓存LLM分析结果，避免重复计算
- **角色场景数据缓存**：内存缓存常用的角色场景数据
- **提示词缓存**：缓存生成的一致性提示词

### 2. 并行处理

- **批量分析**：支持批量进行一致性分析
- **异步生成**：图像生成过程采用异步处理
- **进度回调**：实时显示处理进度

### 3. 内存管理

- **延迟加载**：按需加载角色场景数据
- **数据清理**：定期清理过期的缓存数据
- **内存监控**：监控内存使用情况，防止内存泄漏

## 扩展开发

### 1. 自定义一致性策略

```python
class CustomConsistencyStrategy:
    def analyze(self, storyboard: StoryboardResult) -> Dict[str, Any]:
        # 实现自定义分析逻辑
        pass
    
    def enhance_prompt(self, shot: Shot, analysis_result: Dict[str, Any]) -> str:
        # 实现自定义提示词增强逻辑
        pass
```

### 2. 插件系统

系统支持通过插件扩展功能：
- 一致性分析插件
- 提示词优化插件
- 后处理插件

### 3. API扩展

```python
# 扩展API示例
class ExtendedConsistencyProcessor(ConsistencyEnhancedImageProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_strategies = []
    
    def add_custom_strategy(self, strategy):
        self.custom_strategies.append(strategy)
    
    async def generate_with_custom_strategies(self, storyboard, config):
        # 使用自定义策略生成图像
        pass
```

## 版本历史

- **v1.0.0** - 基础一致性控制系统
- **v1.1.0** - 添加LLM智能分析
- **v1.2.0** - 实现渐进式增强
- **v1.3.0** - 优化UI界面和用户体验
- **v2.0.0** - 完整的一致性控制系统集成

## 贡献指南

欢迎贡献代码和建议！请遵循以下步骤：

1. Fork 项目仓库
2. 创建功能分支
3. 提交代码更改
4. 创建 Pull Request
5. 等待代码审查

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。