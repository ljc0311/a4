#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动下载匹配的ChromeDriver
"""

import os
import sys
import requests
import zipfile
import json
from pathlib import Path

def get_chrome_version():
    """获取当前Chrome版本"""
    try:
        import subprocess
        result = subprocess.run([
            'reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', 
            '/v', 'version'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'version' in line and 'REG_SZ' in line:
                    version = line.split()[-1]
                    return version
    except Exception as e:
        print(f"获取Chrome版本失败: {e}")
    
    return None

def get_available_chromedriver_versions():
    """获取可用的ChromeDriver版本"""
    try:
        # 获取Chrome for Testing的版本信息
        url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        versions = data.get('versions', [])
        
        return versions
    except Exception as e:
        print(f"获取ChromeDriver版本列表失败: {e}")
        return []

def find_matching_chromedriver(chrome_version, available_versions):
    """查找匹配的ChromeDriver版本"""
    chrome_major = chrome_version.split('.')[0]
    
    # 查找完全匹配的版本
    for version_info in reversed(available_versions):
        version = version_info.get('version', '')
        if version == chrome_version:
            return version_info
    
    # 查找主版本号匹配的最新版本
    for version_info in reversed(available_versions):
        version = version_info.get('version', '')
        if version.startswith(chrome_major + '.'):
            return version_info
    
    return None

def download_chromedriver(version_info, output_dir):
    """下载ChromeDriver"""
    try:
        downloads = version_info.get('downloads', {})
        chromedriver_downloads = downloads.get('chromedriver', [])
        
        # 查找Windows 64位版本
        win64_download = None
        for download in chromedriver_downloads:
            if download.get('platform') == 'win64':
                win64_download = download
                break
        
        if not win64_download:
            print("未找到Windows 64位版本的ChromeDriver")
            return False
        
        download_url = win64_download.get('url')
        if not download_url:
            print("下载URL为空")
            return False
        
        print(f"正在下载ChromeDriver {version_info['version']}...")
        print(f"下载URL: {download_url}")
        
        # 下载文件
        response = requests.get(download_url, timeout=300)
        response.raise_for_status()
        
        # 保存到临时文件
        zip_path = os.path.join(output_dir, "chromedriver.zip")
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        print("下载完成，正在解压...")
        
        # 解压文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        
        # 查找chromedriver.exe文件
        chromedriver_exe = None
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file == 'chromedriver.exe':
                    chromedriver_exe = os.path.join(root, file)
                    break
            if chromedriver_exe:
                break
        
        if chromedriver_exe:
            # 移动到项目根目录
            target_path = os.path.join(output_dir, "chromedriver.exe")
            if chromedriver_exe != target_path:
                if os.path.exists(target_path):
                    os.remove(target_path)
                os.rename(chromedriver_exe, target_path)
            
            print(f"✅ ChromeDriver已安装到: {target_path}")
            
            # 清理临时文件
            os.remove(zip_path)
            
            # 清理解压的文件夹
            for root, dirs, files in os.walk(output_dir):
                for dir_name in dirs:
                    if 'chromedriver' in dir_name.lower():
                        import shutil
                        shutil.rmtree(os.path.join(root, dir_name), ignore_errors=True)
                        break
            
            return True
        else:
            print("❌ 解压后未找到chromedriver.exe文件")
            return False
            
    except Exception as e:
        print(f"下载ChromeDriver失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("自动下载匹配的ChromeDriver")
    print("=" * 60)
    
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    
    # 获取Chrome版本
    print("🔍 检测Chrome版本...")
    chrome_version = get_chrome_version()
    if not chrome_version:
        print("❌ 无法获取Chrome版本")
        return False
    
    print(f"✅ 检测到Chrome版本: {chrome_version}")
    
    # 获取可用的ChromeDriver版本
    print("🔍 获取可用的ChromeDriver版本...")
    available_versions = get_available_chromedriver_versions()
    if not available_versions:
        print("❌ 无法获取ChromeDriver版本列表")
        return False
    
    print(f"✅ 获取到 {len(available_versions)} 个可用版本")
    
    # 查找匹配的版本
    print("🔍 查找匹配的ChromeDriver版本...")
    matching_version = find_matching_chromedriver(chrome_version, available_versions)
    if not matching_version:
        print("❌ 未找到匹配的ChromeDriver版本")
        return False
    
    chromedriver_version = matching_version['version']
    print(f"✅ 找到匹配版本: {chromedriver_version}")
    
    # 检查是否已存在
    existing_chromedriver = project_root / "chromedriver.exe"
    if existing_chromedriver.exists():
        print(f"⚠️ 发现现有的ChromeDriver: {existing_chromedriver}")
        choice = input("是否替换现有版本？(y/n): ").lower().strip()
        if choice != 'y':
            print("取消下载")
            return False
    
    # 下载ChromeDriver
    print("📥 开始下载ChromeDriver...")
    success = download_chromedriver(matching_version, str(project_root))
    
    if success:
        print("\n🎉 ChromeDriver下载完成！")
        print(f"Chrome版本: {chrome_version}")
        print(f"ChromeDriver版本: {chromedriver_version}")
        print("现在可以使用真实模式进行抖音发布了。")
        return True
    else:
        print("\n❌ ChromeDriver下载失败")
        return False

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户取消下载")
    except Exception as e:
        print(f"\n下载过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
