#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复Vheer生成的视频文件
将错误命名的WebM文件重命名为正确的扩展名，并可选择转换为MP4格式
"""

import os
import shutil
import subprocess
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

def check_ffmpeg():
    """检查FFmpeg是否可用"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def get_video_info(file_path):
    """获取视频文件信息"""
    try:
        # 使用file命令检查文件类型
        result = subprocess.run(['file', file_path], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            output = result.stdout.lower()
            if 'webm' in output:
                return 'webm'
            elif 'mp4' in output or 'mpeg' in output:
                return 'mp4'
            elif 'matroska' in output:
                return 'mkv'
        return 'unknown'
    except:
        return 'unknown'

def rename_video_files(directory):
    """重命名视频文件为正确的扩展名"""
    directory = Path(directory)
    if not directory.exists():
        logger.error(f"目录不存在: {directory}")
        return []
        
    renamed_files = []
    
    # 查找所有.mp4文件
    for file_path in directory.glob("*.mp4"):
        logger.info(f"检查文件: {file_path.name}")
        
        # 检查实际文件格式
        actual_format = get_video_info(str(file_path))
        logger.info(f"实际格式: {actual_format}")
        
        if actual_format == 'webm':
            # 重命名为.webm
            new_path = file_path.with_suffix('.webm')
            try:
                shutil.move(str(file_path), str(new_path))
                logger.info(f"✅ 重命名: {file_path.name} -> {new_path.name}")
                renamed_files.append((str(file_path), str(new_path)))
            except Exception as e:
                logger.error(f"❌ 重命名失败: {e}")
                
    return renamed_files

def convert_webm_to_mp4(webm_file, mp4_file=None):
    """将WebM文件转换为MP4格式"""
    if not check_ffmpeg():
        logger.error("❌ FFmpeg未安装，无法转换视频格式")
        logger.info("请安装FFmpeg: https://ffmpeg.org/download.html")
        return False
        
    webm_path = Path(webm_file)
    if mp4_file is None:
        mp4_file = webm_path.with_suffix('.mp4')
    else:
        mp4_file = Path(mp4_file)
        
    try:
        logger.info(f"🔄 转换视频: {webm_path.name} -> {mp4_file.name}")
        
        # 使用FFmpeg转换
        cmd = [
            'ffmpeg',
            '-i', str(webm_path),
            '-c:v', 'libx264',  # 视频编码器
            '-c:a', 'aac',      # 音频编码器
            '-movflags', '+faststart',  # 优化网络播放
            '-y',  # 覆盖输出文件
            str(mp4_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"✅ 转换成功: {mp4_file}")
            
            # 检查输出文件大小
            if mp4_file.exists() and mp4_file.stat().st_size > 0:
                original_size = webm_path.stat().st_size
                converted_size = mp4_file.stat().st_size
                logger.info(f"📊 文件大小: {original_size} -> {converted_size} bytes")
                return True
            else:
                logger.error("❌ 转换后的文件无效")
                return False
        else:
            logger.error(f"❌ FFmpeg转换失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ 转换超时")
        return False
    except Exception as e:
        logger.error(f"❌ 转换异常: {e}")
        return False

def fix_vheer_videos():
    """修复Vheer生成的视频文件"""
    print("🔧 Vheer视频文件修复工具")
    print("=" * 50)
    
    # 要处理的目录列表
    directories = [
        "output/videos/vheer",
        "output/videos/vheer_batch",
        "temp/vheer_videos"
    ]
    
    total_renamed = 0
    total_converted = 0
    
    for directory in directories:
        if not os.path.exists(directory):
            logger.info(f"⏭️ 跳过不存在的目录: {directory}")
            continue
            
        logger.info(f"📁 处理目录: {directory}")
        
        # 步骤1: 重命名文件
        renamed_files = rename_video_files(directory)
        total_renamed += len(renamed_files)
        
        if renamed_files:
            logger.info(f"✅ 重命名了 {len(renamed_files)} 个文件")
            
            # 步骤2: 询问是否转换为MP4
            if check_ffmpeg():
                print(f"\n发现 {len(renamed_files)} 个WebM文件")
                choice = input("是否转换为MP4格式? (y/n): ").lower().strip()
                
                if choice in ['y', 'yes', '是']:
                    for original_path, webm_path in renamed_files:
                        mp4_path = Path(webm_path).with_suffix('.mp4')
                        if convert_webm_to_mp4(webm_path, mp4_path):
                            total_converted += 1
                            
                            # 询问是否删除原WebM文件
                            keep_webm = input(f"保留原WebM文件 {Path(webm_path).name}? (y/n): ").lower().strip()
                            if keep_webm not in ['y', 'yes', '是']:
                                try:
                                    os.remove(webm_path)
                                    logger.info(f"🗑️ 删除原文件: {Path(webm_path).name}")
                                except Exception as e:
                                    logger.error(f"❌ 删除失败: {e}")
                else:
                    logger.info("⏭️ 跳过格式转换")
            else:
                logger.info("💡 提示: 安装FFmpeg可以转换为MP4格式")
        else:
            logger.info("✅ 该目录中没有需要修复的文件")
            
        print()
        
    # 打印总结
    print("=" * 50)
    print("📊 修复总结")
    print(f"重命名文件: {total_renamed} 个")
    print(f"转换文件: {total_converted} 个")
    
    if total_renamed > 0:
        print("\n✅ 修复完成！现在视频文件应该可以正常播放了")
        print("💡 WebM格式可以在Chrome、Firefox等现代浏览器中播放")
        print("💡 MP4格式兼容性更好，支持更多播放器")
    else:
        print("\n✅ 没有发现需要修复的文件")

def main():
    """主函数"""
    try:
        fix_vheer_videos()
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断操作")
    except Exception as e:
        logger.error(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
