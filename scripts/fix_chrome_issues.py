#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键修复Chrome和ChromeDriver问题
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path

def check_chrome_version():
    """检查Chrome版本"""
    try:
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                result = subprocess.run([chrome_path, "--version"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version_line = result.stdout.strip()
                    version = version_line.split()[-1]
                    major_version = version.split('.')[0]
                    return chrome_path, version, major_version
        
        return None, None, None
        
    except Exception as e:
        print(f"检查Chrome版本失败: {e}")
        return None, None, None

def kill_chrome_processes():
    """关闭所有Chrome进程"""
    try:
        print("🔄 关闭所有Chrome进程...")
        subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], 
                     capture_output=True)
        subprocess.run(["taskkill", "/f", "/im", "chromedriver.exe"], 
                     capture_output=True)
        time.sleep(3)
        print("✅ Chrome进程已关闭")
    except Exception as e:
        print(f"关闭Chrome进程时出现问题: {e}")

def start_chrome_debug():
    """启动Chrome调试模式"""
    try:
        chrome_path, version, major = check_chrome_version()
        if not chrome_path:
            print("❌ 未找到Chrome安装")
            return False
        
        print(f"📍 Chrome路径: {chrome_path}")
        print(f"📊 Chrome版本: {version}")
        
        # 创建用户数据目录
        user_data_dir = Path("selenium").absolute()
        user_data_dir.mkdir(exist_ok=True)
        
        # 启动Chrome调试模式
        cmd = [
            chrome_path,
            "--remote-debugging-port=9222",
            f"--user-data-dir={user_data_dir}",
            "--disable-features=VizDisplayCompositor",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        
        print("🌐 启动Chrome调试模式...")
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        # 等待启动
        for i in range(15):
            time.sleep(1)
            try:
                response = requests.get("http://127.0.0.1:9222/json", timeout=2)
                if response.status_code == 200:
                    print("✅ Chrome调试模式启动成功！")
                    return True
            except:
                pass
            print(f"   等待中... ({i+1}/15)")
        
        print("❌ Chrome调试模式启动超时")
        return False
        
    except Exception as e:
        print(f"启动Chrome调试模式失败: {e}")
        return False

def download_matching_chromedriver():
    """下载匹配的ChromeDriver"""
    try:
        # 运行ChromeDriver更新脚本
        script_path = Path(__file__).parent / "update_chromedriver.py"
        if script_path.exists():
            print("🔧 运行ChromeDriver更新脚本...")
            result = subprocess.run([sys.executable, str(script_path)], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ ChromeDriver更新成功")
                return True
            else:
                print(f"❌ ChromeDriver更新失败: {result.stderr}")
                return False
        else:
            print("❌ 未找到ChromeDriver更新脚本")
            return False
            
    except Exception as e:
        print(f"下载ChromeDriver失败: {e}")
        return False

def test_selenium_connection():
    """测试Selenium连接"""
    try:
        print("🧪 测试Selenium连接...")
        
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        
        # 使用项目中的ChromeDriver
        project_root = Path(__file__).parent.parent
        chromedriver_path = project_root / "chromedriver.exe"
        
        if not chromedriver_path.exists():
            print("❌ ChromeDriver不存在")
            return False
        
        driver = webdriver.Chrome(
            service=webdriver.chrome.service.Service(str(chromedriver_path)),
            options=options
        )
        
        # 测试基本功能
        driver.get("https://www.baidu.com")
        title = driver.title
        driver.quit()
        
        print(f"✅ Selenium连接测试成功！页面标题: {title}")
        return True
        
    except Exception as e:
        print(f"❌ Selenium连接测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 Chrome和ChromeDriver问题一键修复工具")
    print("=" * 60)
    
    # 1. 检查Chrome版本
    print("1️⃣ 检查Chrome版本...")
    chrome_path, version, major = check_chrome_version()
    
    if not chrome_path:
        print("❌ 未找到Chrome安装")
        print("💡 请先安装Google Chrome浏览器")
        return False
    
    print(f"✅ Chrome版本: {version} (主版本: {major})")
    
    # 2. 关闭现有Chrome进程
    print("\n2️⃣ 关闭现有Chrome进程...")
    kill_chrome_processes()
    
    # 3. 下载匹配的ChromeDriver
    print("\n3️⃣ 更新ChromeDriver...")
    if not download_matching_chromedriver():
        print("❌ ChromeDriver更新失败")
        return False
    
    # 4. 启动Chrome调试模式
    print("\n4️⃣ 启动Chrome调试模式...")
    if not start_chrome_debug():
        print("❌ Chrome调试模式启动失败")
        return False
    
    # 5. 测试Selenium连接
    print("\n5️⃣ 测试Selenium连接...")
    if not test_selenium_connection():
        print("❌ Selenium连接测试失败")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 所有问题修复完成！")
    print("✅ Chrome调试模式已启动")
    print("✅ ChromeDriver版本已匹配")
    print("✅ Selenium连接正常")
    print("\n🎯 接下来可以:")
    print("1. 在Chrome中登录快手账号")
    print("2. 访问: https://cp.kuaishou.com/article/publish/video")
    print("3. 运行测试脚本: python scripts/test_kuaishou_crawler_assist.py")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            input("\n按回车键退出...")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        input("按回车键退出...")
        sys.exit(1)
