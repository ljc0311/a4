#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vheer视频后处理工具
去除视频左上角的原图水印区域
"""

import os
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

def get_video_info(video_path):
    """获取视频信息"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width', 0)
                    height = stream.get('height', 0)
                    duration = float(stream.get('duration', 0))
                    fps = eval(stream.get('r_frame_rate', '30/1'))
                    
                    return {
                        'width': width,
                        'height': height,
                        'duration': duration,
                        'fps': fps
                    }
        return None
        
    except Exception as e:
        logger.error(f"获取视频信息失败: {e}")
        return None

def remove_watermark_area(input_path, output_path=None, crop_method='auto'):
    """
    去除视频左上角的水印区域
    
    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径（可选）
        crop_method: 裁剪方法 ('auto', 'manual', 'blur')
    """
    
    if not check_ffmpeg():
        logger.error("❌ FFmpeg未安装，无法处理视频")
        logger.info("请安装FFmpeg: https://ffmpeg.org/download.html")
        return False
        
    input_path = Path(input_path)
    if not input_path.exists():
        logger.error(f"❌ 输入文件不存在: {input_path}")
        return False
        
    # 生成输出路径
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"
    else:
        output_path = Path(output_path)
        
    logger.info(f"🎬 处理视频: {input_path.name}")
    logger.info(f"📁 输出路径: {output_path}")
    
    # 获取视频信息
    video_info = get_video_info(input_path)
    if not video_info:
        logger.error("❌ 无法获取视频信息")
        return False
        
    width = video_info['width']
    height = video_info['height']
    
    logger.info(f"📏 视频尺寸: {width}x{height}")
    
    try:
        if crop_method == 'auto':
            # 方法1: 自动裁剪 - 去除左上角约1/4区域
            crop_x = int(width * 0.25)  # 从25%位置开始
            crop_y = 0                  # 从顶部开始
            crop_width = width - crop_x # 剩余宽度
            crop_height = height        # 保持高度
            
            cmd = [
                'ffmpeg',
                '-i', str(input_path),
                '-vf', f'crop={crop_width}:{crop_height}:{crop_x}:{crop_y}',
                '-c:a', 'copy',  # 音频直接复制
                '-y',  # 覆盖输出文件
                str(output_path)
            ]
            
        elif crop_method == 'manual':
            # 方法2: 手动裁剪 - 精确去除水印区域
            # 假设水印区域大约是左上角200x150像素
            watermark_width = min(200, int(width * 0.3))
            watermark_height = min(150, int(height * 0.3))
            
            # 裁剪掉水印区域后的尺寸
            crop_x = watermark_width
            crop_y = 0
            crop_width = width - watermark_width
            crop_height = height
            
            cmd = [
                'ffmpeg',
                '-i', str(input_path),
                '-vf', f'crop={crop_width}:{crop_height}:{crop_x}:{crop_y}',
                '-c:a', 'copy',
                '-y',
                str(output_path)
            ]
            
        elif crop_method == 'blur':
            # 方法3: 模糊水印区域而不是裁剪
            watermark_width = min(200, int(width * 0.3))
            watermark_height = min(150, int(height * 0.3))
            
            cmd = [
                'ffmpeg',
                '-i', str(input_path),
                '-vf', f'boxblur=enable=\'between(t,0,999)\':x=0:y=0:w={watermark_width}:h={watermark_height}:blur_radius=20',
                '-c:a', 'copy',
                '-y',
                str(output_path)
            ]
            
        else:
            logger.error(f"❌ 不支持的裁剪方法: {crop_method}")
            return False
            
        logger.info(f"🔄 开始处理，方法: {crop_method}")
        
        # 执行FFmpeg命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"✅ 处理成功: {output_path}")
            
            # 检查输出文件
            if output_path.exists() and output_path.stat().st_size > 0:
                original_size = input_path.stat().st_size
                processed_size = output_path.stat().st_size
                logger.info(f"📊 文件大小: {original_size} -> {processed_size} bytes")
                
                # 获取处理后的视频信息
                new_info = get_video_info(output_path)
                if new_info:
                    logger.info(f"📏 新尺寸: {new_info['width']}x{new_info['height']}")
                    
                return True
            else:
                logger.error("❌ 输出文件无效")
                return False
        else:
            logger.error(f"❌ FFmpeg处理失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ 处理超时")
        return False
    except Exception as e:
        logger.error(f"❌ 处理异常: {e}")
        return False

def batch_process_vheer_videos(directory, crop_method='auto', keep_original=True):
    """批量处理Vheer视频文件"""
    
    directory = Path(directory)
    if not directory.exists():
        logger.error(f"❌ 目录不存在: {directory}")
        return
        
    # 查找所有webm文件
    video_files = list(directory.glob("vheer_video_*.webm"))
    
    if not video_files:
        logger.info(f"⏭️ 目录中没有找到Vheer视频文件: {directory}")
        return
        
    logger.info(f"📁 找到 {len(video_files)} 个视频文件")
    
    processed_count = 0
    failed_count = 0
    
    for video_file in video_files:
        # 检查是否已经处理过
        cleaned_file = video_file.parent / f"{video_file.stem}_cleaned{video_file.suffix}"
        if cleaned_file.exists():
            logger.info(f"⏭️ 跳过已处理的文件: {video_file.name}")
            continue
            
        logger.info(f"\n🎬 处理文件 {processed_count + failed_count + 1}/{len(video_files)}: {video_file.name}")
        
        if remove_watermark_area(video_file, cleaned_file, crop_method):
            processed_count += 1
            
            # 询问是否删除原文件
            if not keep_original:
                try:
                    video_file.unlink()
                    logger.info(f"🗑️ 删除原文件: {video_file.name}")
                except Exception as e:
                    logger.error(f"❌ 删除原文件失败: {e}")
        else:
            failed_count += 1
            
    logger.info(f"\n📊 批量处理完成:")
    logger.info(f"✅ 成功处理: {processed_count} 个")
    logger.info(f"❌ 处理失败: {failed_count} 个")

def main():
    """主函数"""
    print("🎬 Vheer视频后处理工具")
    print("去除视频左上角的原图水印区域")
    print("=" * 50)
    
    # 要处理的目录
    directories = [
        "output/videos/vheer",
        "output/videos/vheer_batch",
        "temp/vheer_videos"
    ]
    
    if not check_ffmpeg():
        print("❌ 需要安装FFmpeg才能使用此工具")
        print("下载地址: https://ffmpeg.org/download.html")
        return
        
    print("选择处理方法:")
    print("1. auto - 自动裁剪左侧25%区域")
    print("2. manual - 精确去除水印区域") 
    print("3. blur - 模糊水印区域")
    
    choice = input("请选择方法 (1-3): ").strip()
    
    method_map = {
        '1': 'auto',
        '2': 'manual', 
        '3': 'blur'
    }
    
    crop_method = method_map.get(choice, 'auto')
    logger.info(f"选择的处理方法: {crop_method}")
    
    keep_original = input("保留原始文件? (y/n): ").lower().strip() in ['y', 'yes', '是']
    
    for directory in directories:
        if os.path.exists(directory):
            logger.info(f"\n📁 处理目录: {directory}")
            batch_process_vheer_videos(directory, crop_method, keep_original)
        else:
            logger.info(f"⏭️ 跳过不存在的目录: {directory}")
            
    print("\n🎉 处理完成！")

if __name__ == "__main__":
    main()
