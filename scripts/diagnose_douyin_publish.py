#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音发布功能诊断脚本
"""

import os
import sys
import subprocess
import requests
import socket
import time
from pathlib import Path

def check_chrome_installation():
    """检查Chrome安装"""
    print("🔍 检查Chrome安装...")
    
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    
    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            try:
                result = subprocess.run([chrome_path, "--version"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version = result.stdout.strip()
                    print(f"✅ Chrome已安装: {version}")
                    print(f"   路径: {chrome_path}")
                    return True
            except Exception as e:
                print(f"❌ Chrome版本检查失败: {e}")
    
    print("❌ 未找到Chrome安装")
    return False

def check_chromedriver():
    """检查ChromeDriver"""
    print("\n🔍 检查ChromeDriver...")
    
    project_root = Path(__file__).parent.parent
    chromedriver_path = project_root / "chromedriver.exe"
    
    if chromedriver_path.exists():
        try:
            result = subprocess.run([str(chromedriver_path), "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✅ ChromeDriver已安装: {version}")
                print(f"   路径: {chromedriver_path}")
                return True
        except Exception as e:
            print(f"❌ ChromeDriver版本检查失败: {e}")
    
    print("❌ 未找到ChromeDriver")
    return False

def check_debug_port():
    """检查Chrome调试端口"""
    print("\n🔍 检查Chrome调试端口...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', 9222))
        sock.close()
        
        if result == 0:
            print("✅ Chrome调试端口9222已开启")
            
            # 尝试访问调试API
            try:
                response = requests.get('http://127.0.0.1:9222/json', timeout=5)
                if response.status_code == 200:
                    tabs = response.json()
                    print(f"   活动标签页数量: {len(tabs)}")
                    return True
                else:
                    print(f"❌ 调试API访问失败: {response.status_code}")
            except Exception as e:
                print(f"❌ 调试API访问异常: {e}")
        else:
            print("❌ Chrome调试端口9222未开启")
            print("   请运行 start_chrome_debug.bat 启动调试模式")
    
    except Exception as e:
        print(f"❌ 端口检查失败: {e}")
    
    return False

def check_selenium_dependencies():
    """检查Selenium依赖"""
    print("\n🔍 检查Selenium依赖...")
    
    try:
        import selenium
        print(f"✅ Selenium已安装: {selenium.__version__}")
        
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        print("✅ Selenium WebDriver模块正常")
        
        return True
    except ImportError as e:
        print(f"❌ Selenium依赖缺失: {e}")
        return False

def check_network_connectivity():
    """检查网络连接"""
    print("\n🔍 检查网络连接...")
    
    test_urls = [
        "https://creator.douyin.com",
        "https://www.douyin.com",
        "https://www.google.com"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ {url} - 连接正常")
            else:
                print(f"⚠️ {url} - 状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ {url} - 连接失败: {e}")

def check_user_data_directory():
    """检查用户数据目录"""
    print("\n🔍 检查用户数据目录...")
    
    project_root = Path(__file__).parent.parent
    user_data_dir = project_root / "selenium_chrome_data"
    
    if user_data_dir.exists():
        print(f"✅ 用户数据目录存在: {user_data_dir}")
        
        # 检查目录大小
        total_size = sum(f.stat().st_size for f in user_data_dir.rglob('*') if f.is_file())
        print(f"   目录大小: {total_size / 1024 / 1024:.1f} MB")
        
        # 检查是否有登录数据
        default_dir = user_data_dir / "Default"
        if default_dir.exists():
            cookies_file = default_dir / "Cookies"
            if cookies_file.exists():
                print("✅ 发现登录Cookie数据")
            else:
                print("⚠️ 未发现登录Cookie数据")
        
        return True
    else:
        print("❌ 用户数据目录不存在")
        print("   将在首次运行时自动创建")
        return False

def test_chrome_startup():
    """测试Chrome启动"""
    print("\n🔍 测试Chrome启动...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        project_root = Path(__file__).parent.parent
        chromedriver_path = project_root / "chromedriver.exe"
        
        if chromedriver_path.exists():
            service = Service(str(chromedriver_path))
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
        
        # 测试基本功能
        driver.get("https://www.google.com")
        title = driver.title
        driver.quit()
        
        print(f"✅ Chrome启动测试成功: {title}")
        return True
        
    except Exception as e:
        print(f"❌ Chrome启动测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("抖音发布功能诊断工具")
    print("=" * 60)
    
    checks = [
        ("Chrome安装", check_chrome_installation),
        ("ChromeDriver", check_chromedriver),
        ("调试端口", check_debug_port),
        ("Selenium依赖", check_selenium_dependencies),
        ("网络连接", check_network_connectivity),
        ("用户数据目录", check_user_data_directory),
        ("Chrome启动测试", test_chrome_startup)
    ]
    
    results = {}
    
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ {name}检查异常: {e}")
            results[name] = False
    
    # 总结
    print("\n" + "=" * 60)
    print("诊断结果总结")
    print("=" * 60)

    # 确保所有结果都是布尔值
    for name in results:
        if results[name] is None:
            results[name] = False

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:<15} {status}")

    print(f"\n总体状态: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("\n🎉 所有检查都通过！抖音发布功能应该可以正常使用。")
    else:
        print("\n🔧 建议的修复步骤:")
        if not results.get("Chrome安装"):
            print("1. 安装Google Chrome浏览器")
        if not results.get("ChromeDriver"):
            print("2. 运行 python scripts/check_chrome_compatibility.py 更新ChromeDriver")
        if not results.get("调试端口"):
            print("3. 运行 start_chrome_debug.bat 启动Chrome调试模式")
        if not results.get("Selenium依赖"):
            print("4. 运行 pip install selenium 安装Selenium")

if __name__ == "__main__":
    main()
