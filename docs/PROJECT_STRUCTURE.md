# AI视频生成器 - 项目结构说明

## 📁 项目目录结构

```
AI_Video_Generator/
├── 📄 README.md                    # 项目主要说明文档
├── 📄 LICENSE                      # 开源许可证
├── 📄 requirements.txt             # Python依赖包列表
├── 📄 main.py                      # 主程序入口（GUI版本）
├── 📄 start.py                     # 启动脚本
│
├── 📁 assets/                      # 静态资源文件
│   ├── app_icon.png               # 应用程序图标
│   └── styles.qss                 # Qt样式表
│
├── 📁 config/                      # 配置文件目录
│   ├── app_settings.json          # 应用程序设置
│   ├── llm_config.json            # 大语言模型配置
│   ├── tts_config.json            # 语音合成配置
│   ├── image_generation_config.py # 图像生成配置
│   ├── baidu_translate_config.py  # 百度翻译配置
│   ├── enhancer_config.json       # 描述增强器配置
│   ├── config.json                # 通用配置
│   └── workflows/                 # ComfyUI工作流文件
│
├── 📁 docs/                        # 文档目录
│   ├── PROJECT_OVERVIEW.md        # 项目概览
│   ├── PROJECT_STATUS.md          # 项目状态
│   ├── PROJECT_STRUCTURE.md       # 项目结构说明（本文件）
│   ├── DEPLOYMENT.md              # 部署指南
│   ├── CHANGELOG.md               # 更新日志
│   ├── CONTRIBUTING.md            # 贡献指南
│   ├── ComfyUI_Setup_Guide.md     # ComfyUI安装指南
│   ├── voice_generation_guide.md  # 语音生成指南
│   └── ...                        # 其他技术文档
│
├── 📁 src/                         # 源代码目录
│   ├── __init__.py
│   ├── 📁 core/                    # 核心功能模块
│   │   ├── project_manager.py     # 项目管理器
│   │   ├── data_manager.py        # 数据管理器
│   │   └── ...
│   │
│   ├── 📁 gui/                     # 图形用户界面
│   │   ├── main_window.py         # 主窗口
│   │   ├── tabs/                  # 各功能标签页
│   │   └── ...
│   │
│   ├── 📁 processors/              # 处理器模块
│   │   ├── story_processor.py     # 故事处理器
│   │   ├── scene_processor.py     # 场景处理器
│   │   ├── image_processor.py     # 图像处理器
│   │   └── ...
│   │
│   ├── 📁 services/                # 服务模块
│   │   ├── llm_service.py         # 大语言模型服务
│   │   ├── image_generation_service.py # 图像生成服务
│   │   ├── tts_service.py         # 语音合成服务
│   │   └── ...
│   │
│   ├── 📁 utils/                   # 工具模块
│   │   ├── logger.py              # 日志工具
│   │   ├── file_utils.py          # 文件工具
│   │   ├── pixabay_sound_downloader.py # 音效下载器
│   │   ├── local_sound_library.py # 本地音效库
│   │   └── ...
│   │
│   ├── 📁 models/                  # 数据模型
│   │   ├── project_model.py       # 项目数据模型
│   │   ├── story_model.py         # 故事数据模型
│   │   └── ...
│   │
│   ├── 📁 audio_processing/        # 音频处理模块
│   ├── 📁 video_processing/        # 视频处理模块
│   ├── 📁 batch_processing/        # 批处理模块
│   └── 📁 character_scene_db/      # 角色场景数据库
│
├── 📁 sound_library/               # 本地音效库
│   ├── README.txt                 # 使用说明
│   ├── doorbell/                  # 门铃音效
│   ├── footsteps/                 # 脚步音效
│   ├── rain/                      # 雨声音效
│   └── ...                        # 其他分类音效
│
├── 📁 output/                      # 输出文件目录
│   └── [项目名称]/                # 各项目的输出文件
│
├── 📁 temp/                        # 临时文件目录
│   └── image_cache/               # 图像缓存
│
├── 📁 logs/                        # 日志文件目录
│   └── system.log                 # 系统日志
│
└── 📁 tests/                       # 测试文件目录
    └── test_voice_generation.py   # 语音生成测试
```

## 🔧 主要功能模块

### 1. 核心功能 (src/core/)
- **项目管理器**: 管理项目的创建、加载、保存
- **数据管理器**: 统一管理项目数据结构

### 2. 图形界面 (src/gui/)
- **主窗口**: 应用程序主界面
- **功能标签页**: 五阶段分镜系统、语音生成、设置等

### 3. 处理器 (src/processors/)
- **故事处理器**: 处理原始文本，生成故事结构
- **场景处理器**: 场景分割和描述生成
- **图像处理器**: 图像生成和管理

### 4. 服务 (src/services/)
- **LLM服务**: 与大语言模型交互
- **图像生成服务**: 调用各种图像生成引擎
- **TTS服务**: 语音合成服务

### 5. 工具 (src/utils/)
- **日志工具**: 统一的日志记录
- **文件工具**: 文件操作相关功能
- **音效库**: 音效下载和管理

## 📋 配置文件说明

### 主要配置文件
- `app_settings.json`: 应用程序基本设置
- `llm_config.json`: 大语言模型API配置
- `tts_config.json`: 语音合成引擎配置
- `image_generation_config.py`: 图像生成引擎配置

### 配置文件特点
- 支持示例配置文件 (`.example` 后缀)
- 自动加载和验证配置
- 支持热重载配置更新

## 🎯 数据流向

```
原始文本 → 故事处理 → 场景分割 → 描述增强 → 图像生成 → 语音生成 → 视频合成
    ↓         ↓         ↓         ↓         ↓         ↓         ↓
  project.json 统一数据存储和管理
```

## 📝 开发规范

### 文件命名
- Python文件: `snake_case.py`
- 配置文件: `snake_case.json`
- 文档文件: `UPPER_CASE.md`

### 代码结构
- 每个模块都有清晰的职责分工
- 使用统一的日志记录
- 配置文件集中管理
- 数据模型统一定义

## 🚀 快速开始

1. **安装依赖**: `pip install -r requirements.txt`
2. **配置设置**: 复制 `.example` 文件并修改配置
3. **启动程序**: `python start.py` 或 `python main.py`
4. **创建项目**: 在GUI中创建新的视频项目

## 📚 相关文档

- [项目概览](PROJECT_OVERVIEW.md)
- [部署指南](DEPLOYMENT.md)
- [ComfyUI安装指南](ComfyUI_Setup_Guide.md)
- [语音生成指南](voice_generation_guide.md)
