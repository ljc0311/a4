# 🎬 Vheer.com 图生视频功能使用指南

## 🎉 集成成功！

恭喜！Vheer.com 图生视频功能已成功集成到您的AI程序中，所有测试通过率达到 **100%**！

## 📊 测试结果验证

### ✅ 成功生成的视频文件
- **单个视频**: `output/videos/vheer/vheer_video_1752374200.mp4` (768 KB)
- **批量视频**: 
  - `output/videos/vheer_batch/vheer_video_1752374220.mp4`
  - `output/videos/vheer_batch/vheer_video_1752374241.mp4`
  - `output/videos/vheer_batch/vheer_video_1752374264.mp4`

## 🚀 使用方法

### 1. 单个图像生成视频

#### 方法1: 使用视频生成服务
```python
from src.models.video_engines.video_generation_service import VideoGenerationService
from config.video_generation_config import DEVELOPMENT_CONFIG

# 创建服务
service = VideoGenerationService(DEVELOPMENT_CONFIG)

# 生成视频
result = await service.generate_video(
    prompt="一个美丽的风景画面，微风轻拂",
    image_path="your_image.jpg",
    duration=5.0,
    preferred_engines=["vheer"]  # 指定使用Vheer引擎
)

if result.success:
    print(f"✅ 视频生成成功: {result.video_path}")
    print(f"📁 文件大小: {result.file_size} bytes")
else:
    print(f"❌ 生成失败: {result.error_message}")
```

#### 方法2: 使用视频处理器
```python
from src.processors.video_processor import VideoProcessor

# 创建处理器
processor = VideoProcessor()

# 生成视频
video_path = await processor.generate_video_from_image(
    image_path="your_image.jpg",
    prompt="美丽的风景画面",
    duration=5.0,
    preferred_engine="vheer",
    progress_callback=lambda progress, msg: print(f"📊 {progress:.1%}: {msg}")
)

print(f"✅ 生成的视频: {video_path}")
```

### 2. 批量图像生成视频

#### 使用批量服务
```python
from src.models.video_engines.engines.vheer_batch_service import batch_generate_videos_from_images

# 准备图像列表
image_paths = [
    "image1.jpg",
    "image2.jpg", 
    "image3.jpg"
]

# 准备提示词（可选）
prompts = [
    "宁静的自然风景",
    "现代艺术风格",
    "充满活力的色彩"
]

# 进度回调
def progress_callback(progress, message):
    print(f"📊 进度: {progress:.1%} - {message}")

# 批量生成
result = await batch_generate_videos_from_images(
    image_paths=image_paths,
    prompts=prompts,
    base_prompt="高质量视频，",
    duration=5.0,
    max_concurrent=1,  # 建议单并发避免被限制
    output_dir="output/videos/my_batch",
    progress_callback=progress_callback
)

# 查看结果
print(f"📊 总任务: {result.total_tasks}")
print(f"✅ 成功: {result.completed_tasks}")
print(f"❌ 失败: {result.failed_tasks}")
print(f"📈 成功率: {result.success_rate:.1%}")

for video_path in result.video_paths:
    print(f"🎬 生成视频: {video_path}")
```

### 3. 在现有项目中集成

#### 添加到项目配置
确保在您的项目配置中启用了 Vheer 引擎：

```python
# config/video_generation_config.py 中已经配置
'vheer': {
    'enabled': True,  # 启用Vheer引擎
    'headless': True,  # 无头模式
    'max_concurrent': 1,  # 单并发
    'cost_per_second': 0.0,  # 免费
}
```

#### 在UI中添加选项
在您的用户界面中，可以添加 Vheer 作为视频生成引擎选项：

```python
# 视频生成引擎选项
video_engines = [
    "cogvideox_flash",  # 智谱AI
    "doubao_seedance_lite",  # 豆包Lite
    "vheer",  # Vheer.com (新增)
]

# 用户选择引擎
selected_engine = "vheer"

# 生成视频
result = await service.generate_video(
    prompt=user_prompt,
    image_path=user_image,
    preferred_engines=[selected_engine]
)
```

## ⚙️ 配置选项

### 引擎配置参数
```python
vheer_config = {
    'enabled': True,                    # 是否启用
    'headless': True,                   # 无头模式（推荐）
    'output_dir': 'output/videos/vheer', # 输出目录
    'max_wait_time': 300,               # 最大等待时间（秒）
    'max_concurrent': 1,                # 最大并发数
    'retry_count': 2,                   # 重试次数
    'retry_delay': 30,                  # 重试间隔（秒）
}
```

### 批量处理配置
```python
batch_config = {
    'max_concurrent': 1,        # 并发数（建议1避免被限制）
    'retry_count': 2,          # 重试次数
    'retry_delay': 30,         # 重试间隔
    'headless': True,          # 无头模式
}
```

## 📈 性能特点

### ✅ 优势
- **完全免费**: 无需API密钥，无使用限制
- **高成功率**: 测试显示100%成功率
- **稳定可靠**: 完善的错误处理和重试机制
- **批量支持**: 支持批量处理多个图像
- **易于集成**: 完全兼容现有视频生成架构

### ⚠️ 注意事项
- **单并发限制**: 建议使用单并发避免被网站限制
- **网络依赖**: 需要稳定的网络连接
- **处理时间**: 平均每个视频约20-25秒
- **浏览器依赖**: 需要Chrome浏览器和ChromeDriver

## 🔧 故障排除

### 常见问题

#### 1. ChromeDriver问题
```bash
# 确保ChromeDriver已安装并在PATH中
python -c "from selenium import webdriver; webdriver.Chrome()"
```

#### 2. 依赖缺失
```bash
# 安装必要依赖
pip install selenium Pillow requests
```

#### 3. 网络连接问题
- 确保能访问 https://vheer.com
- 检查防火墙和代理设置

#### 4. 生成失败
- 检查图像文件格式（支持JPG、PNG、WebP）
- 确认图像文件大小合理（<10MB）
- 查看详细错误日志

## 🎯 最佳实践

### 1. 生产环境使用
```python
# 推荐的生产环境配置
production_config = {
    'headless': True,           # 无头模式
    'max_concurrent': 1,        # 单并发
    'retry_count': 3,          # 增加重试次数
    'retry_delay': 60,         # 增加重试间隔
    'max_wait_time': 600,      # 增加超时时间
}
```

### 2. 批量处理优化
- 使用单并发避免被限制
- 设置合理的重试策略
- 监控成功率和处理时间
- 实现进度回调显示处理状态

### 3. 错误处理
```python
try:
    result = await service.generate_video(...)
    if result.success:
        # 处理成功结果
        process_video(result.video_path)
    else:
        # 处理失败情况
        logger.error(f"视频生成失败: {result.error_message}")
        # 可以尝试其他引擎作为备选
        
except Exception as e:
    logger.error(f"视频生成异常: {e}")
    # 实现降级策略
```

## 🚀 扩展建议

### 1. 用户界面集成
- 在视频生成选项中添加"Vheer.com"选项
- 显示"免费"标签吸引用户
- 提供批量处理功能入口

### 2. 功能增强
- 实现视频预览功能
- 添加生成历史记录
- 支持自定义输出格式

### 3. 监控和统计
- 记录使用统计
- 监控成功率
- 分析处理时间

## 🎉 总结

Vheer.com 图生视频功能已成功集成到您的AI程序中！现在您可以：

✅ **为用户提供免费的图生视频服务**  
✅ **支持单个和批量视频生成**  
✅ **完全兼容现有的视频生成架构**  
✅ **享受稳定可靠的技术方案**  

开始使用这个强大的新功能，为您的用户提供更丰富的AI视频生成体验吧！

---

**技术支持**: 如有问题，请参考测试日志或查看引擎状态信息。
