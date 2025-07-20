#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vheer.com 集成依赖安装脚本
"""

import subprocess
import sys
import os
import requests
import zipfile
import platform
from pathlib import Path

def run_command(command):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def install_python_packages():
    """安装Python包"""
    print("=== 安装Python依赖包 ===")
    
    packages = [
        "aiohttp",
        "requests", 
        "selenium",
        "mitmproxy"
    ]
    
    for package in packages:
        print(f"安装 {package}...")
        success, stdout, stderr = run_command(f"{sys.executable} -m pip install {package}")
        
        if success:
            print(f"✅ {package} 安装成功")
        else:
            print(f"❌ {package} 安装失败: {stderr}")
            
def get_chrome_version():
    """获取Chrome版本"""
    try:
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            return version
        elif platform.system() == "Darwin":  # macOS
            result = subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"], 
                                  capture_output=True, text=True)
            return result.stdout.split()[-1]
        else:  # Linux
            result = subprocess.run(["google-chrome", "--version"], capture_output=True, text=True)
            return result.stdout.split()[-1]
    except:
        return None

def download_chromedriver():
    """下载ChromeDriver"""
    print("\n=== 下载ChromeDriver ===")
    
    chrome_version = get_chrome_version()
    if not chrome_version:
        print("❌ 无法检测Chrome版本，请手动下载ChromeDriver")
        print("下载地址: https://chromedriver.chromium.org/")
        return False
        
    print(f"检测到Chrome版本: {chrome_version}")
    
    # 获取主版本号
    major_version = chrome_version.split('.')[0]
    
    try:
        # 获取对应的ChromeDriver版本
        url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
        response = requests.get(url)
        driver_version = response.text.strip()
        
        print(f"对应的ChromeDriver版本: {driver_version}")
        
        # 确定下载URL
        system = platform.system().lower()
        if system == "windows":
            driver_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_win32.zip"
            driver_name = "chromedriver.exe"
        elif system == "darwin":
            driver_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_mac64.zip"
            driver_name = "chromedriver"
        else:
            driver_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_linux64.zip"
            driver_name = "chromedriver"
            
        print(f"下载ChromeDriver: {driver_url}")
        
        # 下载文件
        response = requests.get(driver_url)
        zip_path = "chromedriver.zip"
        
        with open(zip_path, 'wb') as f:
            f.write(response.content)
            
        # 解压文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
            
        # 删除zip文件
        os.remove(zip_path)
        
        # 设置执行权限 (Linux/macOS)
        if system != "windows":
            os.chmod(driver_name, 0o755)
            
        print(f"✅ ChromeDriver下载成功: {driver_name}")
        print(f"请将 {driver_name} 添加到系统PATH中，或放在项目目录下")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromeDriver下载失败: {e}")
        print("请手动下载: https://chromedriver.chromium.org/")
        return False

def test_installation():
    """测试安装"""
    print("\n=== 测试安装 ===")
    
    # 测试Python包
    packages_to_test = ["aiohttp", "requests", "selenium"]
    
    for package in packages_to_test:
        try:
            __import__(package)
            print(f"✅ {package} 导入成功")
        except ImportError:
            print(f"❌ {package} 导入失败")
            
    # 测试ChromeDriver
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.google.com")
        driver.quit()
        
        print("✅ ChromeDriver 测试成功")
        
    except Exception as e:
        print(f"❌ ChromeDriver 测试失败: {e}")
        print("请确保ChromeDriver在PATH中或项目目录下")

def create_test_script():
    """创建测试脚本"""
    print("\n=== 创建测试脚本 ===")
    
    test_script = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
Vheer.com 快速测试脚本
\"\"\"

import asyncio
from vheer_advanced_integration import VheerBrowserIntegration

async def quick_test():
    print("Vheer.com 快速测试")
    
    integration = VheerBrowserIntegration(headless=False)
    
    try:
        if not integration.setup_browser():
            print("❌ 浏览器设置失败")
            return
            
        print("✅ 浏览器设置成功")
        
        # 测试生成
        prompt = "a beautiful sunset over mountains"
        print(f"测试生成: {prompt}")
        
        result = integration.generate_image(prompt)
        
        if result:
            print("✅ 生成成功!")
            for path in result:
                print(f"  图像保存在: {path}")
        else:
            print("❌ 生成失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        
    finally:
        integration.cleanup()

if __name__ == "__main__":
    asyncio.run(quick_test())
"""
    
    with open("quick_test_vheer.py", "w", encoding="utf-8") as f:
        f.write(test_script)
        
    print("✅ 测试脚本创建成功: quick_test_vheer.py")

def main():
    """主函数"""
    print("Vheer.com 集成依赖安装程序")
    print("=" * 50)
    
    print("这个脚本将帮助您安装Vheer.com集成所需的所有依赖")
    print("包括: Python包、ChromeDriver等")
    
    try:
        choice = input("\n是否继续安装? (y/n): ").strip().lower()
    except KeyboardInterrupt:
        print("\n用户取消")
        return
        
    if choice != 'y':
        print("安装取消")
        return
        
    # 安装Python包
    install_python_packages()
    
    # 下载ChromeDriver
    download_chromedriver()
    
    # 测试安装
    test_installation()
    
    # 创建测试脚本
    create_test_script()
    
    print("\n" + "=" * 50)
    print("安装完成!")
    
    print("""
=== 下一步 ===

1. 运行快速测试:
   python quick_test_vheer.py

2. 运行完整测试:
   python test_vheer_complete.py

3. 在您的程序中使用:
   from vheer_advanced_integration import VheerBrowserIntegration
   
   integration = VheerBrowserIntegration()
   integration.setup_browser()
   result = integration.generate_image("your prompt")

=== 注意事项 ===

- 确保Chrome浏览器已安装
- 如果ChromeDriver测试失败，请手动下载并放在PATH中
- 首次运行可能需要较长时间
- 请遵守网站使用条款
""")

if __name__ == "__main__":
    main()
