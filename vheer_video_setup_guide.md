# Vheer.com 图生视频功能测试指南

## 📋 项目概述

本项目专门用于测试和集成 Vheer.com 的图像到视频生成功能。通过浏览器自动化技术，实现了完整的图生视频流程自动化。

## 🎯 功能特点

- ✅ **完整流程自动化**: 从图像上传到视频下载的全自动化流程
- ✅ **智能元素识别**: 自动识别上传区域、生成按钮等关键界面元素
- ✅ **多种上传方式**: 支持文件输入框、拖拽上传、JavaScript上传等多种方式
- ✅ **实时进度监控**: 实时监控视频生成进度和状态
- ✅ **多格式支持**: 支持 JPG、PNG、WebP 等多种图像格式
- ✅ **详细日志记录**: 完整记录每个步骤的执行情况
- ✅ **错误处理机制**: 完善的错误处理和重试机制

## 🛠️ 安装依赖

### 1. Python 依赖

```bash
# 基础依赖
pip install selenium requests

# 图像处理依赖 (用于创建测试图像)
pip install Pillow

# 可选: 异步HTTP客户端
pip install aiohttp
```

### 2. ChromeDriver 安装

#### Windows:
1. 访问 [ChromeDriver 下载页面](https://chromedriver.chromium.org/)
2. 下载与您的 Chrome 版本匹配的驱动
3. 将 `chromedriver.exe` 放在 PATH 中或项目目录下

#### macOS:
```bash
# 使用 Homebrew
brew install chromedriver

# 或手动下载并移动到 /usr/local/bin/
```

#### Linux:
```bash
# Ubuntu/Debian
sudo apt-get install chromium-chromedriver

# 或手动下载
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
```

### 3. 自动安装脚本

运行我们提供的自动安装脚本：

```bash
python install_vheer_dependencies.py
```

## 🚀 快速开始

### 1. 快速测试

运行快速测试脚本验证功能：

```bash
python quick_vheer_video_test.py
```

这个脚本会：
- 自动创建或使用现有的测试图像
- 打开 Vheer 图生视频页面
- 执行完整的图生视频流程
- 验证功能是否正常工作

### 2. 完整测试

运行完整的测试程序：

```bash
python vheer_image_to_video_test.py
```

这个程序提供：
- 多图像批量测试
- 详细的步骤记录
- 完整的错误报告
- 视频文件下载和验证

## 📁 文件结构

```
vheer_video_integration/
├── vheer_image_to_video_test.py    # 完整测试程序
├── quick_vheer_video_test.py       # 快速测试脚本
├── install_vheer_dependencies.py   # 依赖安装脚本
├── vheer_video_setup_guide.md      # 本指南文件
├── temp/                           # 临时文件目录
│   └── vheer_videos/              # 生成的视频输出目录
└── test_images/                    # 测试图像目录
```

## 🔧 配置选项

### 浏览器设置

```python
# 无头模式 (后台运行，不显示浏览器窗口)
tester = VheerImageToVideoTester(headless=True)

# 有头模式 (显示浏览器窗口，可观察过程)
tester = VheerImageToVideoTester(headless=False)
```

### 输出目录

```python
# 自定义输出目录
tester = VheerImageToVideoTester(
    headless=False,
    output_dir="my_custom_output_dir"
)
```

## 📊 测试结果示例

### 成功案例
```
[10:30:15] 🚀 开始测试: test_1_sample
[10:30:15] 📷 输入图像: sample.jpg
[10:30:16] 📖 步骤1: 访问 Vheer 图生视频页面...
[10:30:20] ✅ 页面加载完成
[10:30:21] 📤 步骤2: 上传图像文件...
[10:30:23] ✅ 方法1: 直接上传成功
[10:30:26] 🎬 步骤3: 启动视频生成...
[10:30:27] ✅ 找到生成按钮 (文本): Generate
[10:30:28] ⏳ 步骤4: 等待视频生成完成...
[10:32:45] ✅ 发现生成的视频: blob:https://vheer.com/...
[10:32:46] 📥 步骤5: 下载生成的视频...
[10:32:50] ✅ Blob视频下载成功: temp/vheer_videos/test_1_sample_1705123970.mp4
[10:32:51] ✅ 视频文件验证成功: temp/vheer_videos/test_1_sample_1705123970.mp4 (2.1MB)
```

### 测试总结
```
📊 最终测试总结
============================================================
总测试数: 3
成功测试: 2
失败测试: 1
成功率: 66.7%

✅ 成功生成的视频:
  - temp/vheer_videos/test_1_sample_1705123970.mp4
  - temp/vheer_videos/test_2_photo_1705124120.mp4
```

## 🔍 故障排除

### 常见问题

#### 1. ChromeDriver 版本不匹配
```
错误: SessionNotCreatedException: session not created
解决: 下载与您的 Chrome 版本匹配的 ChromeDriver
```

#### 2. 元素未找到
```
错误: 未找到上传元素
解决: 网站界面可能有变化，检查元素选择器是否需要更新
```

#### 3. 上传失败
```
错误: 图像上传失败
解决: 
- 检查图像文件是否存在
- 确认图像格式是否支持 (JPG, PNG, WebP)
- 检查文件大小是否在限制范围内
```

#### 4. 视频生成超时
```
错误: 视频生成超时或失败
解决:
- 增加等待时间 (max_wait 参数)
- 检查网络连接
- 确认网站服务是否正常
```

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

观察浏览器操作：

```python
# 设置为有头模式并添加延迟
tester = VheerImageToVideoTester(headless=False)
```

## 🎯 集成到现有项目

### 基础集成示例

```python
from vheer_image_to_video_test import VheerImageToVideoTester

async def generate_video_from_image(image_path: str) -> str:
    """将图像转换为视频"""
    tester = VheerImageToVideoTester(headless=True)
    
    try:
        if not tester.setup_browser():
            raise Exception("浏览器设置失败")
            
        result = tester.test_image_to_video(image_path, "production")
        
        if result['success']:
            return result['video_path']
        else:
            raise Exception(f"视频生成失败: {result['error_message']}")
            
    finally:
        tester.cleanup()
```

### 批量处理示例

```python
def batch_generate_videos(image_list: List[str]) -> List[str]:
    """批量生成视频"""
    tester = VheerImageToVideoTester(headless=True)
    video_paths = []
    
    try:
        tester.setup_browser()
        
        for i, image_path in enumerate(image_list):
            result = tester.test_image_to_video(image_path, f"batch_{i}")
            if result['success']:
                video_paths.append(result['video_path'])
                
        return video_paths
        
    finally:
        tester.cleanup()
```

## 📈 性能优化建议

1. **复用浏览器实例**: 对于批量处理，复用同一个浏览器实例
2. **并发限制**: 避免同时运行过多实例，以免被网站限制
3. **缓存机制**: 实现结果缓存，避免重复生成相同内容
4. **错误重试**: 实现智能重试机制处理临时失败

## 🔒 注意事项

1. **遵守使用条款**: 请遵守 Vheer.com 的使用条款和速率限制
2. **网络稳定性**: 确保网络连接稳定，视频生成需要较长时间
3. **资源管理**: 及时清理临时文件和浏览器实例
4. **版本兼容性**: 定期检查网站更新，可能需要调整代码

## 🆘 获取帮助

如果遇到问题：

1. 查看详细日志输出
2. 检查网站是否有界面变化
3. 验证依赖版本是否正确
4. 尝试手动操作验证网站功能

## 🎉 成功标准

测试成功的标志：
- ✅ 能够成功上传图像文件
- ✅ 能够触发视频生成过程  
- ✅ 能够检测生成完成
- ✅ 能够下载生成的视频文件
- ✅ 视频文件完整且可播放

达到这些标准后，就可以考虑将此功能集成到您的 AI 视频生成程序架构中了！
