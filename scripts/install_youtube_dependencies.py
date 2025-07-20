#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube发布器依赖安装脚本
自动安装YouTube发布所需的依赖包
"""

import subprocess
import sys
import os
from pathlib import Path

def install_package(package):
    """安装Python包"""
    try:
        print(f"📦 安装 {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package} 安装失败: {e}")
        return False

def check_package(package):
    """检查包是否已安装"""
    try:
        __import__(package)
        return True
    except ImportError:
        return False

def install_youtube_dependencies():
    """安装YouTube发布器依赖"""
    print("🚀 开始安装YouTube发布器依赖...")
    
    # YouTube API依赖
    api_packages = [
        "google-api-python-client",
        "google-auth-httplib2", 
        "google-auth-oauthlib"
    ]
    
    # Selenium依赖
    selenium_packages = [
        "selenium",
        "webdriver-manager"
    ]
    
    # 视频处理依赖
    video_packages = [
        "opencv-python"
    ]
    
    # 其他依赖
    other_packages = [
        "aiohttp",
        "requests"
    ]
    
    all_packages = api_packages + selenium_packages + video_packages + other_packages
    
    failed_packages = []
    
    for package in all_packages:
        if not install_package(package):
            failed_packages.append(package)
    
    print("\n" + "="*50)
    if failed_packages:
        print(f"❌ 以下包安装失败: {', '.join(failed_packages)}")
        print("请手动安装这些包或检查网络连接")
        return False
    else:
        print("✅ 所有依赖安装成功!")
        return True

def create_config_template():
    """创建配置文件模板"""
    try:
        print("📝 创建配置文件模板...")
        
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        # 复制配置模板
        example_file = config_dir / "youtube_config.example.py"
        config_file = config_dir / "youtube_config.py"
        
        if example_file.exists() and not config_file.exists():
            import shutil
            shutil.copy(example_file, config_file)
            print(f"✅ 配置文件已创建: {config_file}")
        
        # 创建凭据文件占位符
        credentials_file = config_dir / "youtube_credentials.json"
        if not credentials_file.exists():
            credentials_content = '''{
    "installed": {
        "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
        "project_id": "your-project-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "YOUR_CLIENT_SECRET",
        "redirect_uris": ["http://localhost"]
    }
}'''
            with open(credentials_file, 'w', encoding='utf-8') as f:
                f.write(credentials_content)
            print(f"📄 凭据文件模板已创建: {credentials_file}")
            print("⚠️ 请替换为您的实际YouTube API凭据")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")
        return False

def check_chrome_installation():
    """检查Chrome安装"""
    try:
        print("🔍 检查Chrome浏览器...")
        
        # Windows Chrome路径
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        chrome_found = False
        for path in chrome_paths:
            if os.path.exists(path):
                print(f"✅ 找到Chrome: {path}")
                chrome_found = True
                break
        
        if not chrome_found:
            print("⚠️ 未找到Chrome浏览器")
            print("请安装Chrome浏览器: https://www.google.com/chrome/")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 检查Chrome失败: {e}")
        return False

def show_next_steps():
    """显示后续步骤"""
    print("\n" + "="*60)
    print("📋 后续设置步骤")
    print("="*60)
    print()
    print("🔑 YouTube API设置:")
    print("1. 访问 https://console.developers.google.com/")
    print("2. 创建项目并启用 YouTube Data API v3")
    print("3. 创建 OAuth 2.0 客户端ID凭据")
    print("4. 下载凭据JSON文件，替换 config/youtube_credentials.json")
    print()
    print("🌐 Selenium设置:")
    print("1. 启动Chrome调试模式:")
    print("   chrome.exe --remote-debugging-port=9222 --user-data-dir=youtube_selenium")
    print("2. 在浏览器中登录 YouTube Studio")
    print()
    print("🧪 测试:")
    print("运行测试脚本: python examples/youtube_publisher_example.py")
    print()
    print("="*60)

def main():
    """主函数"""
    print("🚀 YouTube发布器依赖安装程序")
    print("="*50)
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        return False
    
    print(f"✅ Python版本: {sys.version}")
    
    # 安装依赖
    if not install_youtube_dependencies():
        return False
    
    # 创建配置文件
    if not create_config_template():
        return False
    
    # 检查Chrome
    check_chrome_installation()
    
    # 显示后续步骤
    show_next_steps()
    
    print("\n🎉 YouTube发布器依赖安装完成!")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
