#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI视频创作工具安装脚本
自动安装依赖并配置环境
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def print_banner():
    """打印欢迎横幅"""
    print("=" * 60)
    print("🎬 AI视频创作工具 - 自动安装程序")
    print("=" * 60)
    print("这个脚本将帮助您安装所有必要的依赖包")
    print("包括: PyQt5、Selenium、OpenCV、MoviePy等")
    print()

def check_python_version():
    """检查Python版本"""
    print("🔍 检查Python版本...")
    version = sys.version_info
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python版本过低: {version.major}.{version.minor}")
        print("需要Python 3.8或更高版本")
        return False
    
    print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True

def check_pip():
    """检查pip是否可用"""
    print("🔍 检查pip...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      check=True, capture_output=True)
        print("✅ pip可用")
        return True
    except subprocess.CalledProcessError:
        print("❌ pip不可用")
        return False

def upgrade_pip():
    """升级pip"""
    print("📦 升级pip...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True)
        print("✅ pip升级成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ pip升级失败: {e}")
        return False

def install_requirements():
    """安装requirements.txt中的依赖"""
    print("📦 安装项目依赖...")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt文件不存在")
        return False
    
    try:
        # 使用清华镜像加速安装
        cmd = [
            sys.executable, "-m", "pip", "install", 
            "-r", "requirements.txt",
            "-i", "https://pypi.tuna.tsinghua.edu.cn/simple/"
        ]
        
        print("使用清华大学镜像源安装依赖...")
        subprocess.run(cmd, check=True)
        print("✅ 依赖安装成功")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        print("尝试使用默认源...")
        
        try:
            cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
            subprocess.run(cmd, check=True)
            print("✅ 依赖安装成功")
            return True
        except subprocess.CalledProcessError as e2:
            print(f"❌ 依赖安装失败: {e2}")
            return False

def check_chrome():
    """检查Chrome浏览器"""
    print("🔍 检查Chrome浏览器...")
    
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser"
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            print(f"✅ 找到Chrome: {path}")
            return True
    
    print("⚠️ 未找到Chrome浏览器")
    print("请手动安装Chrome浏览器用于平台发布功能")
    return False

def create_config_files():
    """创建配置文件"""
    print("📝 创建配置文件...")
    
    config_dir = Path("config")
    if not config_dir.exists():
        print("❌ config目录不存在")
        return False
    
    # 配置文件映射
    config_files = {
        "app_settings.example.json": "app_settings.json",
        "llm_config.example.json": "llm_config.json",
        "tts_config.example.json": "tts_config.json",
        "youtube_config.example.py": "youtube_config.py"
    }
    
    created_count = 0
    for example_file, target_file in config_files.items():
        example_path = config_dir / example_file
        target_path = config_dir / target_file
        
        if example_path.exists() and not target_path.exists():
            try:
                shutil.copy2(example_path, target_path)
                print(f"✅ 创建配置文件: {target_file}")
                created_count += 1
            except Exception as e:
                print(f"❌ 创建配置文件失败 {target_file}: {e}")
        elif target_path.exists():
            print(f"⚠️ 配置文件已存在: {target_file}")
    
    if created_count > 0:
        print(f"✅ 成功创建 {created_count} 个配置文件")
    
    return True

def create_directories():
    """创建必要的目录"""
    print("📁 创建项目目录...")
    
    directories = [
        "output",
        "output/videos",
        "output/covers",
        "temp",
        "temp/image_cache",
        "logs",
        "user_data"
    ]
    
    created_count = 0
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"✅ 创建目录: {directory}")
                created_count += 1
            except Exception as e:
                print(f"❌ 创建目录失败 {directory}: {e}")
        else:
            print(f"⚠️ 目录已存在: {directory}")
    
    if created_count > 0:
        print(f"✅ 成功创建 {created_count} 个目录")
    
    return True

def test_installation():
    """测试安装"""
    print("🧪 测试安装...")
    
    test_imports = [
        ("PyQt5", "PyQt5.QtWidgets"),
        ("requests", "requests"),
        ("selenium", "selenium"),
        ("PIL", "PIL"),
        ("cv2", "cv2"),
        ("numpy", "numpy")
    ]
    
    failed_imports = []
    for name, module in test_imports:
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name}")
            failed_imports.append(name)
    
    if failed_imports:
        print(f"⚠️ 以下模块导入失败: {', '.join(failed_imports)}")
        return False
    else:
        print("✅ 所有核心模块导入成功")
        return True

def show_next_steps():
    """显示后续步骤"""
    print("\n" + "=" * 60)
    print("🎉 安装完成！")
    print("=" * 60)
    
    print("\n📋 后续步骤:")
    print("1. 配置API密钥:")
    print("   - 编辑 config/llm_config.json 添加LLM API密钥")
    print("   - 编辑 config/tts_config.json 添加TTS API密钥")
    print("   - 编辑 config/youtube_config.py 添加YouTube API配置")
    
    print("\n2. 启动程序:")
    print("   python main.py")
    
    print("\n3. 可选配置:")
    print("   - 安装YouTube发布依赖: python scripts/install_youtube_dependencies.py")
    print("   - 设置Chrome调试模式: python scripts/start_chrome_debug.py")
    
    print("\n📖 更多信息:")
    print("   - 查看README.md了解详细使用说明")
    print("   - 查看doc/README.md了解项目文档")
    
    print("\n🆘 遇到问题?")
    print("   - 查看logs/system.log日志文件")
    print("   - 访问GitHub Issues: https://github.com/ljc0311/a4/issues")

def main():
    """主函数"""
    print_banner()
    
    # 检查基础环境
    if not check_python_version():
        return False
    
    if not check_pip():
        return False
    
    # 升级pip
    if not upgrade_pip():
        print("⚠️ pip升级失败，继续安装...")
    
    # 安装依赖
    if not install_requirements():
        print("❌ 依赖安装失败，请检查网络连接或手动安装")
        return False
    
    # 检查Chrome
    check_chrome()
    
    # 创建配置文件
    if not create_config_files():
        print("⚠️ 配置文件创建失败，请手动创建")
    
    # 创建目录
    if not create_directories():
        print("⚠️ 目录创建失败，请手动创建")
    
    # 测试安装
    if not test_installation():
        print("⚠️ 部分模块测试失败，但基本功能应该可用")
    
    # 显示后续步骤
    show_next_steps()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n❌ 用户取消安装")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 安装过程中发生错误: {e}")
        sys.exit(1)
