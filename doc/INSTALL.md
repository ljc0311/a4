# 安装指南

## 🚀 快速安装

### 方法一：自动安装（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/ljc0311/a4.git
cd a4

# 2. 运行自动安装脚本
python install.py
```

### 方法二：手动安装

```bash
# 1. 克隆项目
git clone https://github.com/ljc0311/a4.git
cd a4

# 2. 创建虚拟环境
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 创建配置文件
cp config/app_settings.example.json config/app_settings.json
cp config/llm_config.example.json config/llm_config.json
cp config/tts_config.example.json config/tts_config.json

# 5. 运行程序
python main.py
```

## 📋 系统要求

- **Python**: 3.8+ (推荐 3.9+)
- **操作系统**: Windows 10/11, macOS, Linux
- **浏览器**: Chrome 120+ (用于平台发布)
- **内存**: 建议 8GB+
- **存储**: 建议 10GB+ 可用空间

## 🔧 依赖说明

### 核心依赖
- **PyQt5**: GUI框架
- **requests/aiohttp**: 网络请求
- **selenium**: 网页自动化
- **Pillow/OpenCV**: 图像处理
- **moviepy**: 视频处理
- **beautifulsoup4**: 网页解析

### 平台API
- **google-api-python-client**: YouTube API
- **google-auth-***: Google认证

### 系统工具
- **pyperclip**: 剪贴板操作
- **psutil**: 系统信息
- **tqdm**: 进度条
- **colorama**: 颜色输出

## ⚙️ 配置文件

### LLM配置 (`config/llm_config.json`)
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

### TTS配置 (`config/tts_config.json`)
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

### YouTube配置 (`config/youtube_config.py`)
```python
YOUTUBE_API_CONFIG = {
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret',
    'redirect_uri': 'http://localhost:8080'
}
```

## 🐛 常见问题

### 1. Python版本问题
```bash
# 检查Python版本
python --version

# 如果版本过低，请升级到3.8+
```

### 2. 依赖安装失败
```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 或者逐个安装
pip install PyQt5 requests selenium Pillow opencv-python
```

### 3. Chrome浏览器问题
```bash
# 检查Chrome版本
chrome --version

# 启动Chrome调试模式
python scripts/start_chrome_debug.py
```

### 4. 权限问题
```bash
# Windows: 以管理员身份运行
# macOS/Linux: 使用sudo（如果需要）
sudo python install.py
```

### 5. 网络问题
```bash
# 设置代理（如果需要）
pip install --proxy http://proxy.server:port -r requirements.txt

# 或者使用离线安装包
```

## 🧪 验证安装

### 测试核心功能
```bash
# 测试GUI启动
python main.py

# 测试模块导入
python -c "import PyQt5, requests, selenium, PIL, cv2, numpy; print('所有模块导入成功')"
```

### 测试平台发布
```bash
# 测试YouTube发布
python examples/youtube_publish_example.py

# 测试抖音发布（需要Chrome调试模式）
python scripts/start_chrome_debug.py
```

## 📖 下一步

1. **配置API密钥**: 编辑配置文件添加必要的API密钥
2. **启动程序**: 运行 `python main.py`
3. **创建项目**: 使用GUI创建第一个视频项目
4. **查看文档**: 阅读 `README.md` 了解详细使用说明

## 🆘 获取帮助

- **文档**: 查看 `README.md` 和 `doc/` 目录
- **日志**: 查看 `logs/system.log` 文件
- **Issues**: [GitHub Issues](https://github.com/ljc0311/a4/issues)
- **讨论**: [GitHub Discussions](https://github.com/ljc0311/a4/discussions)
