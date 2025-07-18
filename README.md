# AI视频创作工具

一个基于AI的智能视频创作平台，支持文本到视频的完整创作流程，包括语音生成、图像生成、视频生成和多平台一键发布。

## 主要功能

### 🎬 五阶段分镜系统
- **文本创作**：AI辅助的故事创作和文本优化
- **语音生成**：多种TTS引擎支持，包括Azure、百度、阿里云等
- **图像生成**：支持多种AI图像生成引擎
- **视频生成**：集成多种视频生成服务
- **一键发布**：支持抖音、快手、小红书、B站等多平台发布

### 🚀 核心特性
- **智能分镜**：自动将文本分解为视频分镜
- **角色一致性**：保持角色在不同场景中的一致性
- **批量处理**：支持批量生成和处理
- **项目管理**：完整的项目保存和加载功能
- **多平台发布**：一键发布到多个视频平台

## 快速开始

### 环境要求
- Python 3.8+
- Windows 10/11
- Chrome浏览器（用于平台发布）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/ljc0311/a4.git
cd a4
```

2. **创建虚拟环境**
```bash
python -m venv venv
venv\Scripts\activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置设置**
- 复制 `config/*.example.json` 文件并重命名为对应的配置文件
- 根据需要配置API密钥和其他设置

5. **运行程序**
```bash
python main.py
```

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
