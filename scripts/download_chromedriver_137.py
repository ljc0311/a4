#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载Chrome 137对应的ChromeDriver
"""

import os
import requests
import zipfile
from pathlib import Path

def download_chromedriver_137():
    """下载ChromeDriver 137"""
    try:
        project_root = Path(__file__).parent.parent

        # 尝试多个可能的版本
        versions = [
            "137.0.6910.0",
            "137.0.6909.0",
            "137.0.6908.0",
            "136.0.6877.0",  # 备用版本
            "135.0.6790.0"   # 更早的版本
        ]

        for version in versions:
            try:
                url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/win64/chromedriver-win64.zip"

                print(f"📥 尝试下载ChromeDriver {version}...")
                print(f"URL: {url}")

                # 下载文件
                response = requests.get(url, timeout=60)
                response.raise_for_status()

                print(f"✅ 找到可用版本: {version}")
                break

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    print(f"❌ 版本 {version} 不存在，尝试下一个...")
                    continue
                else:
                    raise
        else:
            print("❌ 所有版本都不可用")
            return False
        
        # 保存zip文件
        zip_path = project_root / "chromedriver_137.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ 下载完成，文件大小: {len(response.content) / 1024 / 1024:.1f} MB")
        
        # 解压文件
        print("📦 正在解压...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 提取chromedriver.exe到项目根目录
            for file_info in zip_ref.filelist:
                if file_info.filename.endswith('chromedriver.exe'):
                    # 读取文件内容
                    with zip_ref.open(file_info) as source:
                        # 写入到项目根目录
                        target_path = project_root / "chromedriver.exe"
                        with open(target_path, 'wb') as target:
                            target.write(source.read())
                    break
        
        # 删除zip文件
        zip_path.unlink()
        
        print(f"✅ ChromeDriver {version} 安装完成")
        
        # 验证安装
        chromedriver_path = project_root / "chromedriver.exe"
        if chromedriver_path.exists():
            import subprocess
            result = subprocess.run([str(chromedriver_path), "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"🔍 验证成功: {result.stdout.strip()}")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("ChromeDriver 137 下载工具")
    print("=" * 50)
    
    if download_chromedriver_137():
        print("\n🎉 ChromeDriver更新成功！")
        print("现在可以尝试使用抖音发布功能了。")
    else:
        print("\n❌ ChromeDriver更新失败")
        print("请手动下载并替换chromedriver.exe文件")
