#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动Chrome调试模式的Python脚本
"""

import os
import sys
import subprocess
import time
import socket
import webbrowser
from pathlib import Path

def is_port_in_use(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_chrome_executable():
    """查找Chrome可执行文件"""
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            return path
    
    return None

def kill_chrome_processes():
    """关闭所有Chrome进程"""
    print("关闭现有Chrome进程...")
    try:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(['pkill', 'chrome'], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    except:
        pass

def start_chrome_debug_mode():
    """启动Chrome调试模式"""
    print("=" * 60)
    print("Chrome调试模式启动工具")
    print("=" * 60)
    
    # 检查端口是否已在使用
    debug_port = 9222
    if is_port_in_use(debug_port):
        print(f"✅ Chrome调试模式已在运行 (端口{debug_port})")
        print(f"📱 调试地址: http://127.0.0.1:{debug_port}")
        
        # 打开调试页面
        try:
            webbrowser.open(f"http://127.0.0.1:{debug_port}")
        except:
            pass
            
        print("\n您现在可以使用程序中的发布功能了")
        return True
    
    # 查找Chrome可执行文件
    chrome_exe = find_chrome_executable()
    if not chrome_exe:
        print("❌ 错误: 未找到Chrome安装")
        print("请确保Chrome已正确安装")
        return False
    
    print(f"找到Chrome: {chrome_exe}")
    
    # 关闭现有Chrome进程
    kill_chrome_processes()
    
    # 创建用户数据目录
    project_root = Path(__file__).parent.parent
    user_data_dir = project_root / "selenium_chrome_data"
    user_data_dir.mkdir(exist_ok=True)
    
    print(f"用户数据目录: {user_data_dir}")
    
    # 启动Chrome调试模式
    print(f"启动Chrome调试模式 (端口{debug_port})...")
    
    cmd = [
        chrome_exe,
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-plugins"
    ]
    
    try:
        # 使用subprocess.Popen启动Chrome
        process = subprocess.Popen(cmd)
        
        # 等待Chrome启动
        print("等待Chrome启动...")
        for _ in range(10):
            if is_port_in_use(debug_port):
                break
            time.sleep(1)
        
        # 验证Chrome是否成功启动
        if is_port_in_use(debug_port):
            print("✅ Chrome调试模式启动成功!")
            print(f"📱 调试地址: http://127.0.0.1:{debug_port}")
            
            # 打开抖音创作者中心
            try:
                time.sleep(2)
                webbrowser.open("https://creator.douyin.com")
            except:
                pass
                
            print("\n🎯 现在您可以:")
            print("1. 在Chrome中手动登录抖音等平台")
            print("2. 使用程序中的发布功能")
            print("\n💡 提示: 保持此窗口打开，关闭会停止调试模式")
            
            # 等待用户按键
            input("\n按Enter键关闭此窗口 (Chrome将继续运行)...")
            return True
        else:
            print("❌ Chrome调试模式启动失败")
            return False
            
    except Exception as e:
        print(f"❌ 启动Chrome失败: {e}")
        return False

if __name__ == "__main__":
    try:
        start_chrome_debug_mode()
    except KeyboardInterrupt:
        print("\n用户取消操作")
    except Exception as e:
        print(f"发生错误: {e}")
    
    print("\n程序结束")
