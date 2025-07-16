# 项目结构说明

## 📁 目录结构

```
ai4/
├── 📁 assets/                    # 静态资源
│   ├── app_icon.png             # 应用图标
│   └── styles.qss               # 样式文件
├── 📁 config/                   # 配置文件
│   ├── app_settings.json        # 应用设置
│   ├── llm_config.json         # LLM配置
│   ├── tts_config.json         # 语音合成配置
│   ├── video_generation_config.py # 视频生成配置
│   └── workflows/              # ComfyUI工作流
├── 📁 data/                    # 数据文件
│   ├── cookies/                # 浏览器Cookie
│   └── publisher/              # 发布相关数据
├── 📁 doc/                     # 📚 项目文档
│   ├── README.md               # 项目说明
│   ├── CHANGELOG.md            # 更新日志
│   ├── CODE_QUALITY_REPORT.md  # 代码质量报告
│   ├── api/                    # API文档
│   ├── features/               # 功能说明
│   ├── fixes/                  # 修复记录
│   ├── guides/                 # 使用指南
│   └── user_guides/            # 用户指南
├── 📁 ffmpeg/                  # FFmpeg工具
├── 📁 logs/                    # 日志文件
├── 📁 output/                  # 输出目录
│   ├── covers/                 # 视频封面
│   ├── published_videos/       # 已发布视频
│   └── videos/                 # 生成的视频
├── 📁 scripts/                 # 🔧 工具脚本
│   ├── auto_cleanup.py         # 自动清理
│   ├── code_cleanup_analyzer.py # 代码分析
│   ├── diagnose_douyin_publish.py # 抖音发布诊断
│   ├── setup_cogvideox.py      # CogVideoX设置
│   └── start_chrome_debug.py   # Chrome调试启动
├── 📁 sound_library/           # 音效库
├── 📁 src/                     # 🚀 源代码
│   ├── audio_processing/       # 音频处理
│   ├── core/                   # 核心模块
│   ├── gui/                    # 图形界面
│   ├── models/                 # 模型接口
│   ├── processors/             # 处理器
│   ├── services/               # 服务层
│   ├── utils/                  # 工具函数
│   └── video_processing/       # 视频处理
├── 📁 temp/                    # 临时文件
├── 📁 tests/                   # 测试文件
├── main.py                     # 🎯 主程序入口
└── requirements.txt            # Python依赖
```

## 🚀 核心模块说明

### src/core/ - 核心功能
- `project_manager.py` - 项目管理器
- `service_manager.py` - 服务管理器
- `singleton_manager.py` - 单例管理器

### src/gui/ - 用户界面
- `modern_card_main_window.py` - 主窗口
- `voice_generation_tab.py` - 配音界面
- `ai_drawing_tab.py` - AI绘图界面
- `video_composition_tab.py` - 视频合成界面
- `one_click_publish_tab.py` - 一键发布界面

### src/models/ - 模型接口
- `llm_models/` - 大语言模型
- `image_engines/` - 图像生成引擎
- `video_engines/` - 视频生成引擎
- `tts_engines/` - 语音合成引擎

### src/services/ - 服务层
- `llm_service.py` - LLM服务
- `image_service.py` - 图像服务
- `voice_service.py` - 语音服务
- `video_service.py` - 视频服务

### src/utils/ - 工具函数
- `gui_utils.py` - GUI工具函数
- `logger.py` - 日志工具
- `config_manager.py` - 配置管理

## 🔧 脚本工具

### 代码质量工具
- `dead_code_detector.py` - 检测废弃代码
- `code_cleanup_analyzer.py` - 代码清理分析
- `comprehensive_code_check.py` - 全面代码检查

### 发布相关工具
- `diagnose_douyin_publish.py` - 抖音发布诊断
- `start_chrome_debug.py` - Chrome调试模式启动

### 环境设置工具
- `setup_cogvideox.py` - CogVideoX环境设置
- `download_matching_chromedriver.py` - ChromeDriver下载

## 📚 文档结构

### 用户文档
- `README.md` - 项目总览
- `user_guides/` - 用户使用指南
- `guides/` - 功能指南

### 开发文档
- `development/` - 开发相关文档
- `api/` - API接口文档
- `technical/` - 技术文档

### 维护文档
- `fixes/` - 问题修复记录
- `reports/` - 各类报告
- `CHANGELOG.md` - 版本更新记录

## 🎯 主要功能模块

1. **文本创作** - AI辅助文本生成和优化
2. **五阶段分镜** - 智能分镜脚本生成
3. **AI绘图** - 多引擎图像生成
4. **AI配音** - 智能语音合成
5. **视频生成** - AI视频生成和合成
6. **一键发布** - 多平台自动发布

## 🔄 数据流向

```
文本输入 → 分镜生成 → 图像生成 → 配音生成 → 视频合成 → 一键发布
```

## 🛠️ 开发环境

- Python 3.8+
- PyQt5 (GUI框架)
- FFmpeg (视频处理)
- Chrome/ChromeDriver (自动化发布)

## 📦 依赖管理

所有Python依赖都在 `requirements.txt` 中定义，使用以下命令安装：

```bash
pip install -r requirements.txt
```

## 🚀 启动方式

```bash
python main.py
```

## 📝 注意事项

1. 首次运行需要配置各种API密钥
2. 发布功能需要Chrome浏览器
3. 视频生成需要足够的磁盘空间
4. 建议在虚拟环境中运行
