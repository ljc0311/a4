# ComfyUI 安装和配置指南

## 问题诊断

如果您在使用ComfyUI生图时遇到以下错误：
- `502 Server Error: Bad Gateway`
- `无法连接到ComfyUI服务`
- `ComfyUI连接测试失败`

这通常意味着ComfyUI服务没有正常运行。请按照以下步骤解决：

## 1. 安装ComfyUI

### 方法一：从GitHub下载（推荐）
```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
```

### 方法二：下载压缩包
1. 访问 https://github.com/comfyanonymous/ComfyUI
2. 点击 "Code" -> "Download ZIP"
3. 解压到您选择的目录

## 2. 安装依赖

### Windows用户
```bash
# 进入ComfyUI目录
cd ComfyUI

# 安装Python依赖
pip install -r requirements.txt

# 如果有NVIDIA显卡，安装CUDA版本的PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Linux/Mac用户
```bash
# 进入ComfyUI目录
cd ComfyUI

# 安装Python依赖
pip install -r requirements.txt

# 安装PyTorch（根据您的系统选择合适版本）
pip install torch torchvision torchaudio
```

## 3. 下载模型文件

ComfyUI需要AI模型才能工作。请下载以下基础模型：

### 基础模型（必需）
1. **Stable Diffusion 1.5**
   - 下载地址：https://huggingface.co/runwayml/stable-diffusion-v1-5
   - 文件：`v1-5-pruned-emaonly.ckpt`
   - 保存位置：`ComfyUI/models/checkpoints/`

2. **SDXL Base（推荐）**
   - 下载地址：https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
   - 文件：`sd_xl_base_1.0.safetensors`
   - 保存位置：`ComfyUI/models/checkpoints/`

### VAE模型（可选但推荐）
- 下载地址：https://huggingface.co/stabilityai/sd-vae-ft-mse-original
- 文件：`vae-ft-mse-840000-ema-pruned.ckpt`
- 保存位置：`ComfyUI/models/vae/`

## 4. 启动ComfyUI

### Windows用户
```bash
# 方法一：使用批处理文件（如果存在）
run_nvidia_gpu.bat    # NVIDIA显卡用户
run_cpu.bat          # CPU用户

# 方法二：命令行启动
python main.py

# 方法三：指定端口启动
python main.py --port 8188
```

### Linux/Mac用户
```bash
# 基本启动
python main.py

# 指定端口
python main.py --port 8188

# CPU模式（如果显存不足）
python main.py --cpu
```

## 5. 验证安装

1. **检查服务状态**
   - 浏览器访问：http://127.0.0.1:8188
   - 应该看到ComfyUI的Web界面

2. **使用测试脚本**
   ```bash
   # 在AI_Video_Generator目录下运行
   python test_comfyui_connection.py
   ```

## 6. 常见问题解决

### 问题1：端口被占用
```bash
# 使用其他端口启动
python main.py --port 8189

# 然后在AI视频生成器的设置中修改ComfyUI地址为：
# http://127.0.0.1:8189
```

### 问题2：显存不足
```bash
# 使用CPU模式
python main.py --cpu

# 或使用低显存模式
python main.py --lowvram
```

### 问题3：模型加载失败
- 确保模型文件下载完整
- 检查模型文件路径是否正确
- 查看ComfyUI控制台的错误信息

### 问题4：Python环境问题
```bash
# 创建虚拟环境（推荐）
python -m venv comfyui_env

# Windows激活
comfyui_env\Scripts\activate

# Linux/Mac激活
source comfyui_env/bin/activate

# 然后安装依赖
pip install -r requirements.txt
```

## 7. 性能优化建议

### 硬件要求
- **最低配置**：8GB RAM，4GB显存
- **推荐配置**：16GB RAM，8GB+显存
- **最佳配置**：32GB RAM，12GB+显存

### 启动参数优化
```bash
# 高性能模式（大显存）
python main.py --highvram

# 标准模式
python main.py

# 低显存模式
python main.py --lowvram

# 极低显存模式
python main.py --novram

# CPU模式
python main.py --cpu
```

## 8. 集成到AI视频生成器

1. **确保ComfyUI正常运行**
   - 访问 http://127.0.0.1:8188 确认界面正常

2. **在AI视频生成器中选择ComfyUI引擎**
   - 打开AI视频生成器
   - 在图像生成设置中选择"ComfyUI 本地"

3. **测试生成**
   - 尝试生成一张测试图片
   - 如果失败，查看错误信息和诊断报告

## 9. 故障排除

如果仍然遇到问题，请：

1. **查看ComfyUI控制台输出**
   - 启动ComfyUI时的错误信息
   - 生成图片时的日志

2. **检查系统资源**
   - 内存使用情况
   - 显存使用情况
   - 磁盘空间

3. **运行诊断工具**
   ```bash
   python test_comfyui_connection.py
   ```

4. **查看详细日志**
   - AI视频生成器的日志文件
   - ComfyUI的日志输出

## 10. 获取帮助

如果问题仍未解决，请：
- 查看ComfyUI官方文档：https://github.com/comfyanonymous/ComfyUI
- 在GitHub Issues中搜索相似问题
- 提供详细的错误信息和系统配置

---

**注意**：首次启动ComfyUI可能需要较长时间来加载模型，请耐心等待。
