# 🎬 AI视频创作工具 v2.0

> **项目状态**: ✅ 生产就绪，功能完整，持续更新中

一个功能强大的AI驱动视频创作平台，提供从文本到视频的完整自动化创作流程。支持多种AI引擎、智能分镜、批量处理和多平台一键发布，让视频创作变得简单高效。

## 🌟 核心亮点

- **🤖 多AI引擎集成**：支持智谱AI、Pollinations、CogVideoX等多种先进AI服务
- **⚡ 智能批量处理**：支持39个镜头并发处理，大幅提升创作效率
- **🎯 精准分镜系统**：AI辅助的智能分镜，确保视频节奏和连贯性
- **🌐 多平台发布**：一键发布到抖音、YouTube、快手等主流平台
- **🎨 现代化界面**：Material Design 3.0风格，用户体验优秀
- **📁 项目管理**：完整的项目保存、加载和版本管理功能

## 📋 项目清理状态

**✅ 已完成清理项目**
- 删除了所有测试文件和调试脚本
- 清理了缓存文件和临时目录
- 移除了无用的备份和日志文件
- 优化了项目结构，保留核心功能代码
- 更新了.gitignore文件，确保敏感信息不被上传

**🗂️ 当前项目结构**
```
a4/
├── src/                    # ✅ 核心源代码
├── config/                 # ✅ 配置文件（敏感信息已排除）
├── assets/                 # ✅ 资源文件
├── doc/                   # ✅ 文档
├── scripts/               # ✅ 必要脚本
├── ffmpeg/                # ✅ FFmpeg工具
├── sound_library/         # ✅ 音效库
├── output/                # ✅ 输出目录（将被忽略）
├── data/                  # ✅ 数据目录（将被忽略）
├── main.py                # ✅ 主程序入口
├── install.py             # ✅ 安装脚本
├── requirements.txt       # ✅ 依赖列表
└── README.md              # ✅ 项目说明
```

## ✨ 主要功能

### 🎬 完整创作流程
- **📝 智能文本创作**：AI辅助的故事创作、文本优化和分镜生成
- **🎤 多引擎语音合成**：支持Edge-TTS、Azure、百度等多种TTS服务
- **🎨 AI图像生成**：集成Pollinations、智谱AI CogView、ComfyUI等引擎
- **🎥 视频生成与合成**：CogVideoX-Flash、豆包等先进视频生成技术
- **📤 多平台一键发布**：自动化发布到抖音、YouTube、快手等平台

### 🚀 技术特性

#### 🎯 智能分镜系统
- **自动分镜**：AI智能将长文本分解为适合的视频片段
- **角色一致性**：跨场景保持角色外观和风格的一致性
- **场景连贯性**：确保视频场景转换自然流畅
- **时长控制**：精确控制每个分镜的时长和节奏

#### ⚡ 高效批量处理
- **并发生成**：支持最多3个任务同时进行，大幅提升效率
- **队列管理**：智能任务队列，自动处理39个镜头的批量生成
- **错误恢复**：自动重试机制，确保生成任务的稳定性
- **进度监控**：实时显示生成进度和任务状态

#### 🎨 多样化AI引擎

**图像生成引擎**
- **Pollinations AI**：完全免费，无需API密钥，支持多种艺术风格
- **智谱AI CogView**：高质量中文图像生成，支持复杂场景描述
- **ComfyUI**：本地部署，完全可控，支持自定义工作流

**视频生成引擎**
- **CogVideoX-Flash**：智谱AI免费视频生成，支持图生视频和文生视频
- **豆包视频生成**：字节跳动高质量视频生成服务
- **Vheer**：免费图生视频服务，适合快速原型制作

**语音合成引擎**
- **Edge-TTS**：微软免费TTS，支持多种语言和音色
- **Azure TTS**：企业级语音合成，音质优秀
- **百度TTS**：中文语音合成专家，自然度高

### 🌐 发布平台支持

#### 📱 抖音发布
- **自动登录检测**：智能检测登录状态，自动处理登录流程
- **视频上传**：支持高清视频上传，自动压缩优化
- **信息填写**：自动填写标题、描述、标签等发布信息
- **发布监控**：实时监控发布状态，确保发布成功

#### 🎬 YouTube发布
- **双重支持**：YouTube API和Selenium自动化双重保障
- **多语言支持**：自动翻译标题和描述，支持国际化发布
- **SEO优化**：智能生成标签和描述，提升视频曝光度
- **批量发布**：支持批量上传和发布管理

#### 📺 快手发布
- **元素识别**：智能识别页面元素，适应界面变化
- **自动化流程**：完整的自动化发布流程
- **错误处理**：完善的错误处理和重试机制

## 🚀 快速开始

### 📋 系统要求

#### 基础环境
- **Python**: 3.8+ (推荐 3.9-3.11)
- **操作系统**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **浏览器**: Chrome 120+ (用于平台发布功能)
- **内存**: 建议 8GB+ (批量处理需要更多内存)
- **存储**: 建议 20GB+ 可用空间 (包含模型缓存和输出文件)

#### 网络要求
- **稳定网络连接**：用于AI服务API调用
- **代理支持**：支持HTTP/HTTPS代理配置
- **带宽建议**：上行带宽2Mbps+（用于视频上传）

#### 硬件建议
- **CPU**: 4核心以上 (并发处理需要)
- **GPU**: 可选，用于本地ComfyUI加速
- **SSD**: 推荐使用SSD存储，提升文件读写速度

### 🛠️ 安装步骤

#### 1. 克隆项目
```bash
git clone https://github.com/ljc0311/a4.git
cd a4
```

#### 2. 创建虚拟环境
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. 安装依赖
```bash
# 安装核心依赖
pip install -r requirements.txt

# 可选：安装YouTube发布依赖
python scripts/install_youtube_dependencies.py
```

#### 4. 配置设置
```bash
# 复制配置文件模板
cp config/app_settings.example.json config/app_settings.json

# 编辑配置文件，添加API密钥
# 主要配置项：
# - 智谱AI API密钥 (用于CogVideoX和CogView)
# - 其他AI服务API密钥 (可选)
```

#### 5. Chrome浏览器配置 (用于平台发布)
```bash
# Windows: 启动Chrome调试模式
chrome.exe --remote-debugging-port=9222 --user-data-dir=selenium_chrome_data

# macOS: 启动Chrome调试模式
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=selenium_chrome_data

# Linux: 启动Chrome调试模式
google-chrome --remote-debugging-port=9222 --user-data-dir=selenium_chrome_data
```

#### 6. 运行程序
```bash
python main.py
```

### 🎯 快速体验

#### 免费试用 (无需API密钥)
1. **图像生成**：使用Pollinations AI，完全免费
2. **语音合成**：使用Edge-TTS，无需配置
3. **基础功能**：文本创作、分镜管理、项目保存

#### 完整功能 (需要API密钥)
1. **配置智谱AI密钥**：获得CogVideoX视频生成和CogView图像生成
2. **配置其他服务**：根据需要添加百度、阿里云等服务密钥
3. **平台发布**：配置各平台账号信息，实现一键发布

## ⚙️ 配置说明

### 🔑 API密钥配置

#### LLM服务配置 (`config/llm_config.json`)
```json
{
  "providers": {
    "zhipu": {
      "api_key": "your_zhipu_api_key",
      "base_url": "https://open.bigmodel.cn/api/paas/v4/"
    },
    "gemini": {
      "api_key": "your_gemini_api_key"
    }
  }
}
```

#### TTS服务配置 (`config/tts_config.json`)
```json
{
  "azure": {
    "subscription_key": "your_azure_key",
    "region": "eastus"
  },
  "baidu": {
    "app_id": "your_app_id",
    "api_key": "your_api_key",
    "secret_key": "your_secret_key"
  }
}
```

#### YouTube API配置 (`config/youtube_config.py`)
```python
YOUTUBE_API_CONFIG = {
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret',
    'redirect_uri': 'http://localhost:8080'
}
```

## 📖 使用指南

### 🎬 创建第一个视频项目

1. **启动程序**：运行 `python main.py`
2. **创建项目**：点击"新建项目"，输入项目名称
3. **文本创作**：在文本创作模块输入故事内容
4. **AI优化**：使用AI优化功能增强文本质量
5. **语音生成**：选择合适的语音引擎生成配音
6. **图像生成**：为每个分镜生成对应图像
7. **视频生成**：将图像和语音合成为视频
8. **一键发布**：选择目标平台进行发布

### 🎯 最佳实践

#### 文本创作
- 保持每个分镜40字符左右
- 使用生动的描述性语言
- 考虑视觉呈现效果

#### 语音生成
- 控制每段语音在10秒左右
- 选择适合内容风格的语音
- 注意语音的自然流畅度

#### 图像生成
- 使用详细的提示词描述
- 保持角色和场景的一致性
- 选择合适的图像风格

#### 视频发布
- 确保视频时长匹配音频
- 添加合适的标题和描述
- 选择相关的标签和分类

## 🔧 高级功能详解

### 🎨 图像生成引擎对比

| 引擎 | 费用 | 质量 | 速度 | 中文支持 | 特色功能 |
|------|------|------|------|----------|----------|
| **Pollinations AI** | 免费 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | 无需API密钥，多种艺术风格 |
| **智谱AI CogView** | 付费 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | 中文优化，高质量输出 |
| **ComfyUI** | 免费 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ | 本地部署，完全可控 |

### 🎥 视频生成引擎对比

| 引擎 | 费用 | 质量 | 时长 | 分辨率 | 特色功能 |
|------|------|------|------|--------|----------|
| **CogVideoX-Flash** | 免费 | ⭐⭐⭐⭐⭐ | 10秒 | 4K | 图生视频，文生视频 |
| **豆包 Pro** | 付费 | ⭐⭐⭐⭐⭐ | 30秒 | 4K | 高质量，多种模型 |
| **豆包 Lite** | 付费 | ⭐⭐⭐⭐ | 15秒 | 1080P | 性价比高，速度快 |
| **Vheer** | 免费 | ⭐⭐⭐ | 5秒 | 1080P | 图生视频，快速生成 |

### 📤 发布平台功能

#### 🎯 智能发布特性
- **自动重试**：网络异常时自动重试发布
- **状态监控**：实时监控发布进度和状态
- **批量管理**：支持批量发布和管理
- **模板系统**：预设发布模板，快速应用

#### 🔧 高级配置
- **代理支持**：支持HTTP/HTTPS代理配置
- **浏览器配置**：自定义Chrome启动参数
- **超时设置**：可配置的网络超时时间
- **错误处理**：完善的错误处理和日志记录

### 🚀 性能优化

#### 并发处理优化
- **智能队列管理**：自动管理任务队列，避免资源冲突
- **内存优化**：智能内存管理，支持大批量处理
- **网络优化**：连接池复用，减少网络延迟
- **缓存机制**：智能缓存，避免重复计算

#### 错误恢复机制
- **自动重试**：网络错误和API限制自动重试
- **降级处理**：高级功能失败时自动降级到基础功能
- **状态恢复**：程序重启后自动恢复未完成的任务
- **数据备份**：自动备份项目数据，防止数据丢失

## 🛠️ 开发指南

### 📁 项目结构
```
ai4/
├── src/                    # 源代码
│   ├── gui/               # 用户界面
│   ├── services/          # 核心服务
│   ├── models/            # 数据模型
│   ├── utils/             # 工具函数
│   └── core/              # 核心组件
├── config/                # 配置文件
├── scripts/               # 实用脚本
├── examples/              # 示例代码
├── doc/                   # 文档
└── requirements.txt       # 依赖列表
```

### 🔌 扩展开发

#### 添加新的图像生成引擎
1. 继承 `ImageGenerationEngine` 基类
2. 实现必要的接口方法
3. 在配置中注册新引擎

#### 添加新的发布平台
1. 继承 `SeleniumPublisherBase` 基类
2. 实现平台特定的发布逻辑
3. 在发布管理器中注册

### 🧪 测试

```bash
# 运行核心测试
python -m pytest tests/

# 测试特定功能
python examples/youtube_publish_example.py
```

## 🐛 故障排除

### 常见问题

#### 1. Chrome浏览器问题
```bash
# 启动Chrome调试模式
python scripts/start_chrome_debug.py
```

#### 2. 依赖安装失败
```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

#### 3. API密钥配置
- 检查配置文件格式是否正确
- 确认API密钥有效性
- 查看日志文件获取详细错误信息

#### 4. 视频生成失败
- 检查网络连接
- 确认API配额充足
- 尝试降低视频质量设置

### 📋 日志查看
```bash
# 查看系统日志
tail -f logs/system.log

# 查看特定模块日志
grep "ERROR" logs/system.log
```

## 🤝 贡献指南

### 🔄 提交代码
1. Fork 项目仓库
2. 创建功能分支
3. 提交代码更改
4. 创建 Pull Request

### 📝 代码规范
- 使用 Black 进行代码格式化
- 遵循 PEP 8 编码规范
- 添加适当的注释和文档

### 🧪 测试要求
- 为新功能添加测试用例
- 确保所有测试通过
- 更新相关文档

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - GUI框架
- [Selenium](https://selenium.dev/) - 网页自动化
- [OpenCV](https://opencv.org/) - 计算机视觉
- [MoviePy](https://zulko.github.io/moviepy/) - 视频处理
- [Pollinations AI](https://pollinations.ai/) - 免费图像生成
- [智谱AI](https://zhipuai.cn/) - AI服务支持

## 📞 联系方式

- **GitHub**: [ljc0311](https://github.com/ljc0311)
- **项目地址**: [https://github.com/ljc0311/a4](https://github.com/ljc0311/a4)
- **问题反馈**: [Issues](https://github.com/ljc0311/a4/issues)

---

**⭐ 如果这个项目对您有帮助，请给我们一个星标！**

## 配置说明

### API配置
项目支持多种AI服务，需要配置相应的API密钥：

- **语音生成**：Azure TTS、百度TTS、阿里云TTS等
- **图像生成**：智谱AI、百度文心一格等
- **视频生成**：CogVideoX、豆包等
- **LLM服务**：OpenAI、智谱AI、百度文心等

详细配置说明请参考 `doc/` 文件夹中的相关文档。

### 浏览器配置
一键发布功能需要Chrome浏览器的调试模式：

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir=selenium
```

## 项目结构

```
├── src/                    # 源代码
│   ├── gui/               # 用户界面
│   ├── services/          # 核心服务
│   ├── utils/             # 工具函数
│   └── ...
├── config/                # 配置文件
├── doc/                   # 文档
├── assets/                # 资源文件
├── output/                # 输出文件
└── requirements.txt       # 依赖列表
```

## 文档

详细文档位于 `doc/` 文件夹中，包括：

- 功能使用指南
- API配置说明
- 故障排除指南
- 开发文档

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 联系方式

如有问题或建议，请通过GitHub Issues联系我们。

---

## ⚠️ 重要提示

**项目清理完成，可安全上传GitHub**
- ✅ 所有敏感信息已通过.gitignore排除
- ✅ 测试文件和调试脚本已清理
- ✅ 缓存和临时文件已删除
- ✅ 项目结构已优化

**配置要求**
- 📝 配置文件需要根据实际环境进行设置
- 🔑 API密钥需要单独配置
- 🌐 发布功能需要相应平台的登录信息

**开发状态**
- 🚧 项目仍在积极开发中
- 🔄 功能和API可能会发生变化
- 📈 持续优化和功能增强中
