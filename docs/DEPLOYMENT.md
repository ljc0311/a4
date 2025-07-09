# 部署指南

## 环境准备

### 系统要求
- Windows 10/11, macOS 10.14+, 或 Linux (Ubuntu 18.04+)
- Python 3.8 或更高版本
- 4GB+ RAM (推荐 8GB)
- 稳定的网络连接

### Python环境设置

1. **安装Python**
   - 从 [python.org](https://www.python.org/) 下载并安装Python 3.8+
   - 确保勾选"Add Python to PATH"选项

2. **验证安装**
   ```bash
   python --version
   pip --version
   ```

## 项目部署

### 方法1: 直接下载
1. 从GitHub下载项目ZIP文件
2. 解压到目标目录
3. 进入项目目录

### 方法2: Git克隆
```bash
git clone https://github.com/yourusername/AI_Video_Generator.git
cd AI_Video_Generator
```

## 依赖安装

### 自动安装 (推荐)
```bash
python start.py
```
启动脚本会自动检查并安装依赖。

### 手动安装
```bash
pip install -r requirements.txt
```

### 虚拟环境 (推荐)
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 配置设置

### 1. LLM API配置
复制并编辑配置文件：
```bash
cp config/llm_config.example.json config/llm_config.json
```

编辑 `config/llm_config.json`，填入您的API密钥。

### 2. 翻译API配置 (可选)
```bash
cp config/baidu_translate_config.example.py config/baidu_translate_config.py
```

编辑文件并填入百度翻译API信息。

## 启动应用

### 方法1: 使用启动脚本
```bash
python start.py
```

### 方法2: 直接启动
```bash
python main.py
```

## 故障排除

### 常见问题

1. **PyQt5安装失败**
   ```bash
   # Windows
   pip install PyQt5 -i https://pypi.tuna.tsinghua.edu.cn/simple/
   
   # Linux (Ubuntu/Debian)
   sudo apt-get install python3-pyqt5
   
   # macOS
   brew install pyqt5
   ```

2. **网络连接问题**
   - 检查防火墙设置
   - 确认可以访问AI服务API
   - 考虑使用代理设置

3. **权限问题**
   - 确保对项目目录有读写权限
   - 在Linux/Mac上可能需要使用sudo

## 生产环境部署

### 服务器部署
1. 使用虚拟环境
2. 配置环境变量
3. 使用进程管理器 (如systemd, supervisor)
4. 配置日志轮转

### Docker部署 (计划中)
```dockerfile
# Dockerfile示例
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## 更新升级

### 从GitHub更新
```bash
git pull origin main
pip install -r requirements.txt
```

### 备份数据
更新前请备份：
- `config/` 目录下的配置文件
- `output/` 目录下的项目文件
- `logs/` 目录下的日志文件

## 性能优化

### 系统优化
- 使用SSD存储
- 确保足够的内存
- 关闭不必要的后台程序

### 网络优化
- 使用稳定的网络连接
- 考虑使用CDN加速
- 配置合适的超时设置

## 安全注意事项

1. **API密钥安全**
   - 不要将API密钥提交到版本控制
   - 定期轮换API密钥
   - 使用环境变量存储敏感信息

2. **网络安全**
   - 使用HTTPS连接
   - 验证SSL证书
   - 配置防火墙规则

3. **数据安全**
   - 定期备份重要数据
   - 加密敏感文件
   - 控制文件访问权限
