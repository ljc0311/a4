#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查和启动Chrome调试模式
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path

def check_chrome_debug_status():
    """检查Chrome调试模式状态"""
    try:
        response = requests.get("http://127.0.0.1:9222/json", timeout=5)
        if response.status_code == 200:
            tabs = response.json()
            return True, len(tabs)
        else:
            return False, 0
    except Exception as e:
        return False, 0

def find_chrome_executable():
    """查找Chrome可执行文件路径"""
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "chrome.exe"  # 如果在PATH中
    ]
    
    for path in possible_paths:
        if os.path.exists(path) or path == "chrome.exe":
            try:
                # 测试是否可以执行
                result = subprocess.run([path, "--version"], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                if result.returncode == 0:
                    return path
            except:
                continue
    
    return None

def kill_chrome_processes():
    """关闭现有的Chrome进程"""
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], 
                         capture_output=True)
        else:  # Linux/Mac
            subprocess.run(["pkill", "-f", "chrome"], 
                         capture_output=True)
        time.sleep(2)
        print("✅ 已关闭现有Chrome进程")
    except Exception as e:
        print(f"⚠️  关闭Chrome进程时出现问题: {e}")

def start_chrome_debug_mode():
    """启动Chrome调试模式"""
    try:
        # 查找Chrome路径
        chrome_path = find_chrome_executable()
        if not chrome_path:
            print("❌ 未找到Chrome安装路径")
            print("💡 请确保Chrome已正确安装")
            return False
        
        print(f"📍 找到Chrome路径: {chrome_path}")
        
        # 关闭现有Chrome进程
        print("🔄 关闭现有Chrome进程...")
        kill_chrome_processes()
        
        # 创建用户数据目录
        user_data_dir = Path("selenium").absolute()
        user_data_dir.mkdir(exist_ok=True)
        
        # 启动Chrome调试模式
        print("🌐 启动Chrome调试模式...")
        cmd = [
            chrome_path,
            "--remote-debugging-port=9222",
            f"--user-data-dir={user_data_dir}",
            "--disable-features=VizDisplayCompositor",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        
        # 在后台启动Chrome
        if os.name == 'nt':  # Windows
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:  # Linux/Mac
            subprocess.Popen(cmd)
        
        # 等待Chrome启动
        print("⏳ 等待Chrome启动...")
        for i in range(10):
            time.sleep(1)
            is_running, tab_count = check_chrome_debug_status()
            if is_running:
                print(f"✅ Chrome调试模式启动成功！")
                print(f"📊 当前标签页数量: {tab_count}")
                return True
            print(f"   等待中... ({i+1}/10)")
        
        print("❌ Chrome调试模式启动超时")
        return False
        
    except Exception as e:
        print(f"❌ 启动Chrome调试模式失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 Chrome调试模式检查和启动工具")
    print("=" * 60)
    
    # 检查当前状态
    print("🔍 检查Chrome调试模式状态...")
    is_running, tab_count = check_chrome_debug_status()
    
    if is_running:
        print("✅ Chrome调试模式已在运行")
        print(f"📊 当前标签页数量: {tab_count}")
        
        # 显示相关标签页
        try:
            response = requests.get("http://127.0.0.1:9222/json", timeout=5)
            tabs = response.json()
            
            kuaishou_tabs = [tab for tab in tabs if 'kuaishou.com' in tab.get('url', '')]
            if kuaishou_tabs:
                print("🎯 发现快手相关标签页:")
                for i, tab in enumerate(kuaishou_tabs[:3]):
                    print(f"   {i+1}. {tab.get('title', 'Unknown')}")
            else:
                print("⚠️  未发现快手相关标签页")
                print("💡 建议打开: https://cp.kuaishou.com/article/publish/video")
        except:
            pass
            
    else:
        print("❌ Chrome调试模式未运行")
        
        user_input = input("是否自动启动Chrome调试模式？(Y/n): ")
        if user_input.lower() != 'n':
            success = start_chrome_debug_mode()
            if not success:
                print("\n💡 手动启动方法:")
                print("1. 完全关闭Chrome")
                print("2. 运行命令:")
                print("   chrome.exe --remote-debugging-port=9222 --user-data-dir=selenium")
                print("3. 或者运行: scripts/start_chrome_debug.bat")
                return
    
    print("\n" + "=" * 60)
    print("🎯 接下来的步骤:")
    print("1. 在Chrome中登录快手账号")
    print("2. 访问: https://cp.kuaishou.com/article/publish/video")
    print("3. 运行测试脚本: python scripts/test_kuaishou_crawler_assist.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
