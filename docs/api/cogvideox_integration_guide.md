# CogVideoX-Flash 视频生成集成指南

## 📖 概述

本指南介绍如何在AI视频生成器中使用智谱AI的CogVideoX-Flash免费视频生成模型。CogVideoX-Flash支持文生视频和图生视频功能，完全免费使用。

## 🚀 快速开始

### 1. 获取API密钥

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册并登录账号
3. 在控制台中创建API密钥
4. 复制您的API密钥

### 2. 配置API密钥

#### 方法一：环境变量（推荐）
```bash
export ZHIPU_API_KEY="your-api-key-here"
```

#### 方法二：配置文件
```python
# 在 config/video_generation_config.py 中配置
'cogvideox_flash': {
    'enabled': True,
    'api_key': 'your-api-key-here',
    # ... 其他配置
}
```

### 3. 基本使用

```python
import asyncio
from src.models.video_engines.video_generation_service import generate_video_simple

async def main():
    # 文生视频
    result = await generate_video_simple(
        prompt="一只可爱的小猫在阳光下打盹",
        duration=5.0,
        api_key="your-api-key-here"
    )
    
    if result.success:
        print(f"视频生成成功: {result.video_path}")
    else:
        print(f"生成失败: {result.error_message}")

asyncio.run(main())
```

## 🎯 功能特性

### ✅ 支持的功能
- **文生视频**: 根据文本描述生成视频
- **图生视频**: 从静态图像生成动态视频
- **高质量输出**: 支持最高4K分辨率
- **高帧率**: 支持最高60fps
- **长时长**: 支持最长10秒视频
- **完全免费**: 无需付费即可使用
- **批量生成**: 支持批量处理多个请求
- **智能音效**: 内置AI音效生成

### 📊 技术规格
- **最大时长**: 10秒
- **支持分辨率**: 720x480 到 3840x2160 (4K)
- **支持帧率**: 24fps, 30fps, 60fps
- **输出格式**: MP4
- **API限制**: 约60次/分钟

## 🛠️ 高级使用

### 详细配置

```python
from src.models.video_engines.video_engine_base import VideoGenerationConfig
from src.models.video_engines.video_generation_service import VideoGenerationService

# 创建详细配置
config = VideoGenerationConfig(
    input_prompt="美丽的日落海景",
    input_image_path="path/to/image.jpg",  # 可选，用于图生视频
    duration=8.0,
    fps=30,
    width=1920,
    height=1080,
    motion_intensity=0.7,  # 运动强度 0.0-1.0
    seed=12345,  # 随机种子，确保结果可重现
    output_format="mp4"
)

# 创建服务
service = VideoGenerationService(video_config)
result = await service.generate_video_from_config(config)
```

### 批量生成

```python
# 创建多个配置
configs = []
prompts = ["春天樱花", "夏日海浪", "秋天落叶", "冬日雪花"]

for prompt in prompts:
    config = VideoGenerationConfig(
        input_prompt=prompt,
        duration=4.0,
        fps=24
    )
    configs.append(config)

# 批量生成
results = await service.batch_generate_videos(configs)
```

### 与视频处理器集成

```python
from src.processors.video_processor import VideoProcessor
from src.core.service_manager import ServiceManager

# 创建处理器
service_manager = ServiceManager()
processor = VideoProcessor(service_manager)

# 从图像生成视频
video_path = await processor.generate_video_from_image(
    image_path="input.jpg",
    prompt="图像开始动起来",
    duration=5.0,
    preferred_engine="cogvideox_flash"
)
```

## 🔧 配置选项

### 引擎配置

```python
{
    'cogvideox_flash': {
        'enabled': True,
        'api_key': 'your-api-key',
        'base_url': 'https://open.bigmodel.cn/api/paas/v4',
        'model': 'cogvideox-flash',
        'timeout': 300,  # 超时时间（秒）
        'max_retries': 3,  # 最大重试次数
        'max_duration': 10.0,  # 最大视频时长
    }
}
```

### 路由策略

- `free_first`: 优先使用免费引擎
- `priority`: 按优先级选择
- `fastest`: 选择最快的引擎
- `cheapest`: 选择最便宜的引擎
- `load_balance`: 负载均衡

### 引擎偏好

- `free`: 偏好免费引擎
- `quality`: 偏好高质量引擎
- `speed`: 偏好快速引擎
- `local`: 偏好本地引擎

## 🧪 测试和验证

### 运行集成测试

```bash
python tests/test_cogvideox_integration.py
```

### 运行使用示例

```bash
python examples/cogvideox_usage_examples.py
```

### 测试项目包括

- ✅ 连接测试
- ✅ 引擎信息获取
- ✅ 文生视频
- ✅ 图生视频
- ✅ 批量生成

## 🚨 错误处理

### 常见错误及解决方案

#### 1. API密钥错误
```
错误: API请求失败 (状态码: 401)
解决: 检查API密钥是否正确配置
```

#### 2. 网络连接问题
```
错误: 连接超时
解决: 检查网络连接，可能需要代理
```

#### 3. 请求频率限制
```
错误: 请求过于频繁
解决: 降低请求频率，添加延迟
```

#### 4. 视频生成超时
```
错误: 视频生成超时
解决: 增加timeout配置或减少视频时长
```

### 错误处理示例

```python
try:
    result = await service.generate_video(prompt="测试")
    if not result.success:
        if "API密钥" in result.error_message:
            print("请检查API密钥配置")
        elif "超时" in result.error_message:
            print("请稍后重试或减少视频时长")
        else:
            print(f"其他错误: {result.error_message}")
except Exception as e:
    print(f"异常: {e}")
```

## 📈 性能优化

### 1. 并发控制
```python
# 限制并发任务数量
config = {
    'concurrent_limit': 2,  # 同时最多2个任务
    # ...
}
```

### 2. 缓存策略
- 相同参数的请求会被缓存
- 使用相同的seed可以获得一致的结果

### 3. 资源管理
```python
# 及时关闭服务释放资源
try:
    # 使用服务
    pass
finally:
    await service.shutdown()
```

## 🔗 API参考

### VideoGenerationService

主要方法：
- `generate_video()`: 生成单个视频
- `batch_generate_videos()`: 批量生成视频
- `get_available_engines()`: 获取可用引擎
- `test_engine()`: 测试引擎连接
- `get_engine_info()`: 获取引擎信息

### VideoGenerationConfig

主要参数：
- `input_prompt`: 文本提示词
- `input_image_path`: 输入图像路径（可选）
- `duration`: 视频时长
- `fps`: 帧率
- `width/height`: 分辨率
- `motion_intensity`: 运动强度

## 🤝 贡献指南

欢迎提交问题和改进建议！

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。

## 🆘 支持

如果遇到问题：

1. 查看本文档的错误处理部分
2. 运行测试脚本诊断问题
3. 检查智谱AI官方文档
4. 提交Issue到项目仓库

---

**注意**: CogVideoX-Flash是免费服务，但可能有使用限制。请合理使用，遵守服务条款。
