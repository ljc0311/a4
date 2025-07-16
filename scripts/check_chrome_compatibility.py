#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome版本兼容性检查和ChromeDriver自动更新脚本
"""

import os
import sys
import subprocess
import requests
import zipfile
import json
import re
from pathlib import Path

def get_chrome_version():
    """获取Chrome版本"""
    try:
        # Windows Chrome路径
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]

        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                try:
                    # 获取Chrome版本
                    result = subprocess.run([chrome_path, "--version"],
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        version_text = result.stdout.strip()
                        # 提取版本号
                        match = re.search(r'(\d+\.\d+\.\d+\.\d+)', version_text)
                        if match:
                            return match.group(1)
                except:
                    # 尝试使用注册表获取版本
                    try:
                        import winreg
                        key_path = r"SOFTWARE\Google\Chrome\BLBeacon"
                        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
                        version, _ = winreg.QueryValueEx(key, "version")
                        winreg.CloseKey(key)
                        print(f"从注册表获取Chrome版本: {version}")
                        return version
                    except:
                        pass

        # 尝试从ChromeDriver错误消息中提取版本
        try:
            project_root = Path(__file__).parent.parent
            chromedriver_path = project_root / "chromedriver.exe"
            if chromedriver_path.exists():
                # 故意使用不兼容的选项触发错误
                cmd = f'"{chromedriver_path}" --version'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                error_text = result.stderr

                # 从错误消息中提取Chrome版本
                match = re.search(r'Current browser version is (\d+\.\d+\.\d+\.\d+)', error_text)
                if match:
                    version = match.group(1)
                    print(f"从ChromeDriver错误消息中提取Chrome版本: {version}")
                    return version
        except:
            pass

        print("❌ 未找到Chrome安装")
        return None

    except Exception as e:
        print(f"❌ 获取Chrome版本失败: {e}")
        return None

def get_chromedriver_version():
    """获取当前ChromeDriver版本"""
    try:
        project_root = Path(__file__).parent.parent
        chromedriver_path = project_root / "chromedriver.exe"
        
        if chromedriver_path.exists():
            result = subprocess.run([str(chromedriver_path), "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version_text = result.stdout.strip()
                # 提取版本号
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', version_text)
                if match:
                    return match.group(1)
                    
        print("❌ 未找到ChromeDriver")
        return None
        
    except Exception as e:
        print(f"❌ 获取ChromeDriver版本失败: {e}")
        return None

def get_compatible_chromedriver_version(chrome_version):
    """获取兼容的ChromeDriver版本"""
    try:
        # 获取主版本号
        major_version = chrome_version.split('.')[0]
        
        # 查询ChromeDriver版本API
        url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return response.text.strip()
        else:
            print(f"❌ 无法获取ChromeDriver版本信息: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 查询ChromeDriver版本失败: {e}")
        return None

def download_chromedriver(version):
    """下载ChromeDriver"""
    try:
        project_root = Path(__file__).parent.parent
        
        # 下载URL
        url = f"https://chromedriver.storage.googleapis.com/{version}/chromedriver_win32.zip"
        
        print(f"📥 正在下载ChromeDriver {version}...")
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            # 保存zip文件
            zip_path = project_root / "chromedriver_temp.zip"
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            # 解压
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extract('chromedriver.exe', project_root)
            
            # 删除临时文件
            zip_path.unlink()
            
            print(f"✅ ChromeDriver {version} 下载完成")
            return True
        else:
            print(f"❌ 下载失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 下载ChromeDriver失败: {e}")
        return False

def check_compatibility():
    """检查Chrome和ChromeDriver兼容性"""
    print("🔍 检查Chrome和ChromeDriver兼容性...")
    
    # 获取Chrome版本
    chrome_version = get_chrome_version()
    if not chrome_version:
        return False
    
    print(f"📱 Chrome版本: {chrome_version}")
    
    # 获取ChromeDriver版本
    chromedriver_version = get_chromedriver_version()
    if chromedriver_version:
        print(f"🚗 ChromeDriver版本: {chromedriver_version}")
    else:
        print("🚗 ChromeDriver: 未安装")
    
    # 检查主版本号是否匹配
    chrome_major = chrome_version.split('.')[0]
    
    if chromedriver_version:
        chromedriver_major = chromedriver_version.split('.')[0]
        
        if chrome_major == chromedriver_major:
            print("✅ Chrome和ChromeDriver版本兼容")
            return True
        else:
            print(f"❌ 版本不兼容: Chrome {chrome_major}.x vs ChromeDriver {chromedriver_major}.x")
    
    # 获取兼容的ChromeDriver版本
    compatible_version = get_compatible_chromedriver_version(chrome_version)
    if not compatible_version:
        return False
    
    print(f"🎯 推荐ChromeDriver版本: {compatible_version}")
    
    # 询问是否下载
    response = input("是否自动下载兼容的ChromeDriver? (y/n): ")
    if response.lower() in ['y', 'yes', '是']:
        return download_chromedriver(compatible_version)
    
    return False

def main():
    """主函数"""
    print("=" * 50)
    print("Chrome兼容性检查工具")
    print("=" * 50)
    
    try:
        if check_compatibility():
            print("\n✅ 兼容性检查完成")
        else:
            print("\n❌ 兼容性检查失败")
            print("\n🔧 手动解决方案:")
            print("1. 更新Chrome到最新版本")
            print("2. 从 https://chromedriver.chromium.org/ 下载匹配的ChromeDriver")
            print("3. 将chromedriver.exe放到项目根目录")
            
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户取消操作")
    except Exception as e:
        print(f"\n❌ 检查过程中出现错误: {e}")

if __name__ == "__main__":
    main()
