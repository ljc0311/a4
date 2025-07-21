# 🎬 AI视频创作工具

> **项目状态**: ✅ 已清理优化，准备上传GitHub备份

一个基于AI的智能视频创作平台，支持文本到视频的完整创作流程，包括语音生成、图像生成、视频生成和多平台一键发布。

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

### 🎬 五阶段分镜系统
- **📝 文本创作**：AI辅助的故事创作和文本优化
- **🎤 语音生成**：多种TTS引擎支持，包括Azure、百度、阿里云等
- **🎨 图像生成**：支持多种AI图像生成引擎（Pollinations、ComfyUI、智谱AI等）
- **🎥 视频生成**：集成多种视频生成服务（CogVideoX、Doubao等）
- **📤 一键发布**：支持抖音、YouTube等多平台发布

### 🚀 核心特性
- **🎯 智能分镜**：自动将文本分解为视频分镜
- **👤 角色一致性**：保持角色在不同场景中的一致性
- **⚡ 批量处理**：支持批量生成和处理
- **📁 项目管理**：完整的项目保存和加载功能
- **🌐 多平台发布**：一键发布到多个视频平台
- **🎨 现代化UI**：Material Design 3.0风格的用户界面

### 🎯 支持的平台
- **📱 抖音**：完整的发布流程支持
- **🎬 YouTube**：API和Selenium双重支持
- **📺 快手**：自动化发布（开发中）
- **📖 小红书**：图文发布支持（开发中）
- **🎮 B站**：视频投稿支持（开发中）

## 🚀 快速开始

### 📋 环境要求
- **Python**: 3.8+ (推荐 3.9+)
- **操作系统**: Windows 10/11, macOS, Linux
- **浏览器**: Chrome 120+ (用于平台发布)
- **内存**: 建议 8GB+
- **存储**: 建议 10GB+ 可用空间

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
cp config/llm_config.example.json config/llm_config.json
cp config/tts_config.example.json config/tts_config.json

# 根据需要配置API密钥
```

#### 5. 运行程序
```bash
python main.py
```

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

## 🔧 高级功能

### 🎨 图像生成引擎

#### Pollinations AI (免费)
- 完全免费使用
- 无需API密钥
- 支持多种艺术风格

#### 智谱AI CogView
- 高质量图像生成
- 支持中文提示词
- 需要API密钥

#### ComfyUI (本地)
- 本地部署，数据安全
- 高度可定制
- 需要本地安装

### 🎥 视频生成引擎

#### CogVideoX
- 智谱AI视频生成
- 支持图像到视频
- 高质量输出

#### Doubao (豆包)
- 字节跳动视频生成
- 多种模型支持
- 快速生成

### 📤 发布平台

#### 抖音发布
- 自动登录检测
- 视频上传和信息填写
- 标签和描述自动化

#### YouTube发布
- API和Selenium双重支持
- 自动翻译和优化
- 多语言内容支持

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
