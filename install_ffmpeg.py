#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFmpeg安装和配置脚本
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

def check_ffmpeg():
    """检查FFmpeg是否已安装"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg已安装")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("❌ FFmpeg未安装")
    return False

def download_ffmpeg():
    """下载FFmpeg"""
    print("🔄 开始下载FFmpeg...")
    
    # FFmpeg Windows版本下载链接
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    # 创建下载目录
    download_dir = Path("ffmpeg_download")
    download_dir.mkdir(exist_ok=True)
    
    zip_file = download_dir / "ffmpeg.zip"
    
    try:
        print(f"📥 正在下载: {ffmpeg_url}")
        urllib.request.urlretrieve(ffmpeg_url, zip_file)
        print("✅ 下载完成")
        return zip_file
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return None

def extract_ffmpeg(zip_file):
    """解压FFmpeg"""
    print("📦 正在解压FFmpeg...")
    
    extract_dir = Path("ffmpeg_download")
    
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # 查找解压后的目录
        for item in extract_dir.iterdir():
            if item.is_dir() and "ffmpeg" in item.name.lower():
                return item
        
        print("❌ 未找到FFmpeg目录")
        return None
        
    except Exception as e:
        print(f"❌ 解压失败: {e}")
        return None

def install_ffmpeg(ffmpeg_dir):
    """安装FFmpeg到项目目录"""
    print("🔧 正在安装FFmpeg...")
    
    # 目标目录
    target_dir = Path("ffmpeg")
    
    try:
        # 删除旧的安装
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        # 复制FFmpeg
        shutil.copytree(ffmpeg_dir, target_dir)
        
        # 检查bin目录
        bin_dir = target_dir / "bin"
        if bin_dir.exists():
            ffmpeg_exe = bin_dir / "ffmpeg.exe"
            if ffmpeg_exe.exists():
                print(f"✅ FFmpeg安装成功: {ffmpeg_exe}")
                return str(ffmpeg_exe)
        
        print("❌ 安装失败：未找到ffmpeg.exe")
        return None
        
    except Exception as e:
        print(f"❌ 安装失败: {e}")
        return None

def cleanup_download():
    """清理下载文件"""
    print("🧹 清理下载文件...")
    
    download_dir = Path("ffmpeg_download")
    if download_dir.exists():
        shutil.rmtree(download_dir)
        print("✅ 清理完成")

def test_ffmpeg(ffmpeg_path):
    """测试FFmpeg"""
    print("🧪 测试FFmpeg...")
    
    try:
        result = subprocess.run([ffmpeg_path, '-version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ FFmpeg测试成功")
            print(f"版本信息: {result.stdout.split()[2]}")
            return True
        else:
            print("❌ FFmpeg测试失败")
            return False
    except Exception as e:
        print(f"❌ FFmpeg测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🎬 FFmpeg安装和配置工具")
    print("=" * 50)
    
    # 检查是否已安装
    if check_ffmpeg():
        print("FFmpeg已经可用，无需安装")
        return
    
    # 检查本地是否已有FFmpeg
    local_ffmpeg = Path("ffmpeg/bin/ffmpeg.exe")
    if local_ffmpeg.exists():
        print(f"✅ 发现本地FFmpeg: {local_ffmpeg}")
        if test_ffmpeg(str(local_ffmpeg)):
            print("本地FFmpeg可用")
            return
    
    print("\n🔄 开始自动安装FFmpeg...")
    
    # 下载FFmpeg
    zip_file = download_ffmpeg()
    if not zip_file:
        print("❌ 下载失败，请手动安装FFmpeg")
        print("手动安装步骤:")
        print("1. 访问: https://ffmpeg.org/download.html")
        print("2. 下载Windows版本")
        print("3. 解压到项目目录下的ffmpeg文件夹")
        return
    
    # 解压FFmpeg
    ffmpeg_dir = extract_ffmpeg(zip_file)
    if not ffmpeg_dir:
        cleanup_download()
        return
    
    # 安装FFmpeg
    ffmpeg_path = install_ffmpeg(ffmpeg_dir)
    if not ffmpeg_path:
        cleanup_download()
        return
    
    # 测试FFmpeg
    if test_ffmpeg(ffmpeg_path):
        print("\n🎉 FFmpeg安装成功！")
        print(f"安装路径: {ffmpeg_path}")
        print("\n现在可以使用视频合成功能了")
    else:
        print("❌ FFmpeg安装失败")
    
    # 清理下载文件
    cleanup_download()

if __name__ == "__main__":
    main()
