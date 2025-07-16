#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新安装Chrome后的调试设置脚本
"""

import os
import sys
import time
import json
import shutil
import subprocess
import requests
from pathlib import Path

def find_chrome_installation():
    """查找Chrome安装位置"""
    print("🔍 查找Chrome安装位置...")
    
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe")
    ]
    
    found_paths = []
    for path in possible_paths:
        if os.path.exists(path):
            found_paths.append(path)
            print(f"✅ 找到Chrome: {path}")
    
    if not found_paths:
        print("❌ 未找到Chrome安装")
        return None
    
    # 返回第一个找到的路径
    return found_paths[0]

def get_chrome_version(chrome_path):
    """获取Chrome版本"""
    try:
        result = subprocess.run([chrome_path, "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.strip()
            print(f"✅ Chrome版本: {version_line}")
            return version_line
        else:
            print("❌ 无法获取Chrome版本")
            return None
    except Exception as e:
        print(f"❌ 获取Chrome版本失败: {e}")
        return None

def clean_chrome_processes():
    """清理Chrome进程"""
    print("🧹 清理Chrome进程...")
    
    try:
        # 关闭Chrome进程
        subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], 
                     capture_output=True)
        subprocess.run(["taskkill", "/f", "/im", "chromedriver.exe"], 
                     capture_output=True)
        
        print("✅ Chrome进程已清理")
        time.sleep(3)  # 等待进程完全关闭
        
        # 验证是否还有Chrome进程
        result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"], 
                              capture_output=True, text=True)
        if "chrome.exe" in result.stdout:
            print("⚠️  仍有Chrome进程运行，请手动关闭所有Chrome窗口")
            input("关闭所有Chrome窗口后按回车继续...")
        else:
            print("✅ 所有Chrome进程已关闭")
            
    except Exception as e:
        print(f"清理Chrome进程时出错: {e}")

def setup_user_data_directory():
    """设置用户数据目录"""
    print("📁 设置用户数据目录...")
    
    selenium_dir = Path("selenium")
    
    # 如果目录存在，先备份
    if selenium_dir.exists():
        backup_dir = Path("selenium_backup")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        
        shutil.move(str(selenium_dir), str(backup_dir))
        print("📦 已备份旧的用户数据目录")
    
    # 创建新的用户数据目录
    selenium_dir.mkdir(exist_ok=True)
    print(f"✅ 用户数据目录创建: {selenium_dir.absolute()}")
    
    return str(selenium_dir.absolute())

def find_available_port():
    """查找可用端口"""
    print("🔍 查找可用调试端口...")
    
    ports_to_try = [9222, 9223, 9224, 9225]
    
    for port in ports_to_try:
        try:
            # 检查端口是否被占用
            result = subprocess.run(["netstat", "-ano"], 
                                  capture_output=True, text=True)
            if f":{port}" not in result.stdout:
                print(f"✅ 端口 {port} 可用")
                return port
            else:
                print(f"⚠️  端口 {port} 被占用")
        except:
            pass
    
    print("❌ 未找到可用端口，使用默认9222")
    return 9222

def start_chrome_debug(chrome_path, user_data_dir, port):
    """启动Chrome调试模式"""
    print(f"🚀 启动Chrome调试模式...")
    print(f"   Chrome路径: {chrome_path}")
    print(f"   用户数据目录: {user_data_dir}")
    print(f"   调试端口: {port}")
    
    try:
        # Chrome启动参数（移除不安全的--disable-web-security参数）
        cmd = [
            chrome_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "--disable-features=VizDisplayCompositor",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding"
        ]
        
        # 启动Chrome
        process = subprocess.Popen(cmd, 
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        print("⏳ 等待Chrome启动...")
        time.sleep(8)  # 给Chrome更多时间启动
        
        return port, process
        
    except Exception as e:
        print(f"❌ 启动Chrome失败: {e}")
        return None, None

def verify_debug_mode(port, max_attempts=10):
    """验证调试模式"""
    print(f"🔍 验证调试模式 (端口 {port})...")
    
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"   尝试 {attempt}/{max_attempts}...")
            
            # 测试基本连接
            response = requests.get(f"http://127.0.0.1:{port}", timeout=3)
            if response.status_code == 200:
                print("   ✅ 基本连接成功")
            
            # 测试JSON API
            response = requests.get(f"http://127.0.0.1:{port}/json", timeout=3)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ JSON API成功，标签页数量: {len(data)}")
                
                # 显示第一个标签页信息
                if data:
                    first_tab = data[0]
                    print(f"   📄 第一个标签页: {first_tab.get('title', 'Unknown')}")
                
                return True
            
        except requests.exceptions.ConnectionError:
            print(f"   ⏳ 连接失败，等待Chrome完全启动...")
        except Exception as e:
            print(f"   ❌ 验证失败: {e}")
        
        if attempt < max_attempts:
            time.sleep(2)
    
    print("❌ 调试模式验证失败")
    return False

def show_next_steps(port):
    """显示后续步骤"""
    print("\n" + "=" * 60)
    print("🎉 Chrome调试模式设置成功！")
    print("=" * 60)
    print(f"🌐 调试页面: http://localhost:{port}")
    print(f"🔧 API地址: http://127.0.0.1:{port}/json")
    print("\n📋 接下来的步骤:")
    print("1. 在Chrome中登录以下平台:")
    print("   - 抖音: https://creator.douyin.com/creator-micro/content/upload")
    print("   - 快手: https://cp.kuaishou.com/article/publish/video")
    print("   - 小红书: https://creator.xiaohongshu.com/publish/publish")
    print("\n2. 运行测试脚本:")
    print("   python scripts/test_moneyprinter_publish.py")
    print("\n3. 如果需要重新诊断:")
    print("   python scripts/diagnose_chrome_debug.py")
    print("=" * 60)

def main():
    """主函数"""
    print("🚀 重新安装Chrome后的调试设置")
    print("=" * 60)
    
    try:
        # 1. 查找Chrome安装
        chrome_path = find_chrome_installation()
        if not chrome_path:
            print("请确保Chrome已正确安装")
            return False
        
        # 2. 获取Chrome版本
        version = get_chrome_version(chrome_path)
        if not version:
            print("Chrome版本检查失败")
            return False
        
        # 3. 清理Chrome进程
        clean_chrome_processes()
        
        # 4. 设置用户数据目录
        user_data_dir = setup_user_data_directory()
        
        # 5. 查找可用端口
        port = find_available_port()
        
        # 6. 启动Chrome调试模式
        debug_port, process = start_chrome_debug(chrome_path, user_data_dir, port)
        if not debug_port:
            return False
        
        # 7. 验证调试模式
        if verify_debug_mode(debug_port):
            show_next_steps(debug_port)
            return True
        else:
            print("❌ 调试模式验证失败")
            
            # 提供手动验证方法
            print(f"\n💡 手动验证方法:")
            print(f"在浏览器中访问: http://localhost:{debug_port}")
            print("如果能看到调试页面，说明设置成功")
            
            return False
            
    except Exception as e:
        print(f"❌ 设置过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ 设置完成！")
        else:
            print("\n❌ 设置失败，请检查错误信息")
        
        input("\n按回车键退出...")
        
    except KeyboardInterrupt:
        print("\n\n用户中断设置")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        input("按回车键退出...")
