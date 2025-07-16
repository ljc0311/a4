#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动下载匹配的ChromeDriver版本
"""

import os
import sys
import json
import zipfile
import requests
import subprocess
from pathlib import Path

def get_chrome_version():
    """获取Chrome版本"""
    try:
        # Windows
        if os.name == 'nt':
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
                        # 提取版本号，例如 "Google Chrome 137.0.7151.104"
                        version = version_line.split()[-1]
                        major_version = version.split('.')[0]
                        return version, major_version
        
        # 尝试命令行
        result = subprocess.run(["chrome", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.strip()
            version = version_line.split()[-1]
            major_version = version.split('.')[0]
            return version, major_version
            
    except Exception as e:
        print(f"获取Chrome版本失败: {e}")
    
    return None, None

def get_chromedriver_download_url(chrome_major_version):
    """获取ChromeDriver下载URL"""
    try:
        # 使用Chrome for Testing API
        api_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
        
        print(f"🔍 查询Chrome {chrome_major_version}对应的ChromeDriver...")
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        versions = data.get('versions', [])
        
        # 查找匹配的版本
        for version_info in reversed(versions):  # 从最新版本开始查找
            version = version_info.get('version', '')
            if version.startswith(f"{chrome_major_version}."):
                downloads = version_info.get('downloads', {})
                chromedriver_downloads = downloads.get('chromedriver', [])
                
                # 查找Windows x64版本
                for download in chromedriver_downloads:
                    if download.get('platform') == 'win64':
                        return version, download.get('url')
        
        print(f"❌ 未找到Chrome {chrome_major_version}对应的ChromeDriver")
        return None, None
        
    except Exception as e:
        print(f"获取ChromeDriver下载URL失败: {e}")
        return None, None

def download_chromedriver(url, version):
    """下载ChromeDriver"""
    try:
        print(f"📥 下载ChromeDriver {version}...")
        
        # 创建临时目录
        temp_dir = Path("temp_chromedriver")
        temp_dir.mkdir(exist_ok=True)
        
        # 下载文件
        response = requests.get(url, timeout=300)
        response.raise_for_status()
        
        zip_path = temp_dir / "chromedriver.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        print("✅ 下载完成，正在解压...")
        
        # 解压文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # 查找chromedriver.exe
        chromedriver_exe = None
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file == "chromedriver.exe":
                    chromedriver_exe = Path(root) / file
                    break
            if chromedriver_exe:
                break
        
        if not chromedriver_exe:
            print("❌ 解压后未找到chromedriver.exe")
            return False
        
        # 移动到项目根目录
        project_root = Path(__file__).parent.parent
        target_path = project_root / "chromedriver.exe"
        
        # 备份旧版本
        if target_path.exists():
            backup_path = project_root / "chromedriver_backup.exe"
            if backup_path.exists():
                backup_path.unlink()
            target_path.rename(backup_path)
            print("📦 已备份旧版本ChromeDriver")
        
        # 复制新版本
        import shutil
        shutil.copy2(chromedriver_exe, target_path)
        
        # 清理临时文件
        shutil.rmtree(temp_dir)
        
        print(f"✅ ChromeDriver {version} 安装成功！")
        print(f"📍 安装位置: {target_path}")
        
        return True
        
    except Exception as e:
        print(f"下载ChromeDriver失败: {e}")
        return False

def verify_chromedriver():
    """验证ChromeDriver"""
    try:
        project_root = Path(__file__).parent.parent
        chromedriver_path = project_root / "chromedriver.exe"
        
        if not chromedriver_path.exists():
            print("❌ ChromeDriver不存在")
            return False
        
        result = subprocess.run([str(chromedriver_path), "--version"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            version_line = result.stdout.strip()
            print(f"✅ ChromeDriver版本: {version_line}")
            return True
        else:
            print("❌ ChromeDriver验证失败")
            return False
            
    except Exception as e:
        print(f"验证ChromeDriver失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 ChromeDriver版本匹配工具")
    print("=" * 60)
    
    # 1. 获取Chrome版本
    print("🔍 检测Chrome版本...")
    chrome_version, chrome_major = get_chrome_version()
    
    if not chrome_version:
        print("❌ 无法检测Chrome版本")
        print("💡 请确保Chrome已正确安装")
        return False
    
    print(f"✅ 检测到Chrome版本: {chrome_version}")
    print(f"📊 主版本号: {chrome_major}")
    
    # 2. 检查当前ChromeDriver
    project_root = Path(__file__).parent.parent
    current_chromedriver = project_root / "chromedriver.exe"
    
    if current_chromedriver.exists():
        print("\n🔍 检查当前ChromeDriver...")
        try:
            result = subprocess.run([str(current_chromedriver), "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                current_version = result.stdout.strip()
                print(f"📍 当前ChromeDriver: {current_version}")
                
                # 检查版本是否匹配
                if chrome_major in current_version:
                    print("✅ ChromeDriver版本已匹配，无需更新")
                    return True
                else:
                    print("⚠️  ChromeDriver版本不匹配，需要更新")
        except:
            print("❌ 当前ChromeDriver无法运行")
    else:
        print("📍 未找到ChromeDriver，需要下载")
    
    # 3. 下载匹配的ChromeDriver
    print(f"\n📥 查找Chrome {chrome_major}对应的ChromeDriver...")
    chromedriver_version, download_url = get_chromedriver_download_url(chrome_major)
    
    if not download_url:
        print("❌ 无法找到匹配的ChromeDriver版本")
        print("💡 请手动从以下网址下载:")
        print("   https://googlechromelabs.github.io/chrome-for-testing/")
        return False
    
    print(f"✅ 找到匹配版本: {chromedriver_version}")
    print(f"📥 下载地址: {download_url}")
    
    # 4. 下载并安装
    success = download_chromedriver(download_url, chromedriver_version)
    if not success:
        return False
    
    # 5. 验证安装
    print("\n🔍 验证安装...")
    if verify_chromedriver():
        print("\n🎉 ChromeDriver更新完成！")
        print("✅ 现在可以正常使用Chrome自动化功能了")
        return True
    else:
        print("\n❌ ChromeDriver验证失败")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        input("\n按回车键退出...")
        sys.exit(1)
