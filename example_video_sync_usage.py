#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频音频同步功能使用示例
展示如何在实际项目中使用新的音视频同步功能
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.processors.video_composer import VideoComposer
from src.utils.logger import logger


def example_video_composition():
    """视频合成示例"""
    print("🎬 视频合成示例")
    print("=" * 50)
    
    # 创建视频合成器
    composer = VideoComposer()
    
    # 示例：准备视频和音频片段数据
    # 在实际使用中，这些数据来自您的项目
    video_segments = [
        {
            'video_path': 'path/to/video1.mp4',  # 假设这个视频是3秒
            'subtitle_text': '第一个场景的描述'
        },
        {
            'video_path': 'path/to/video2.mp4',  # 假设这个视频是8秒
            'subtitle_text': '第二个场景的描述'
        },
        {
            'video_path': 'path/to/video3.mp4',  # 假设这个视频是5秒
            'subtitle_text': '第三个场景的描述'
        }
    ]
    
    audio_segments = [
        {
            'audio_path': 'path/to/audio1.mp3',  # 假设这个音频是5秒
        },
        {
            'audio_path': 'path/to/audio2.mp3',  # 假设这个音频是6秒
        },
        {
            'audio_path': 'path/to/audio3.mp3',  # 假设这个音频是4秒
        }
    ]
    
    # 配置参数
    config = {
        'transition_config': {
            'mode': '随机转场',
            'duration': 0.5,
            'intensity': 5
        },
        'subtitle_config': {
            'font_size': 24,
            'font_color': '#ffffff',
            'outline_color': '#000000',
            'position': '底部'
        },
        'music_volume': 30,
        'loop_music': True,
        'fade_in': True,
        'fade_out': True
    }
    
    # 输出路径
    output_path = 'output/final_video.mp4'
    background_music = 'path/to/background_music.mp3'
    
    print("📋 合成配置:")
    print(f"   视频片段数量: {len(video_segments)}")
    print(f"   音频片段数量: {len(audio_segments)}")
    print(f"   输出路径: {output_path}")
    print(f"   背景音乐: {background_music}")
    
    print("\n🔄 新的同步逻辑说明:")
    print("   • 视频时长 < 音频时长 → 循环播放视频直到音频结束")
    print("   • 视频时长 > 音频时长 → 截断视频至音频时长")
    print("   • 视频时长 = 音频时长 → 直接合并")
    print("   • 确保最终视频时长严格等于音频时长")
    
    # 执行合成（示例代码，实际文件路径需要存在）
    # success = composer.compose_final_video(
    #     video_segments,
    #     audio_segments,
    #     background_music,
    #     output_path,
    #     config
    # )
    
    print("\n✅ 合成流程说明:")
    print("   1. 逐个处理视频音频片段对")
    print("   2. 检测每个片段的实际时长")
    print("   3. 根据时长关系选择同步策略:")
    print("      - 循环: 使用 -stream_loop -1 参数")
    print("      - 截断: 使用 -t 参数限制时长")
    print("      - 直接: 正常合并处理")
    print("   4. 连接所有同步后的片段")
    print("   5. 添加字幕和背景音乐")
    
    # 清理资源
    composer.cleanup()


def example_manual_sync():
    """手动同步示例"""
    print("\n🔧 手动同步示例")
    print("=" * 50)
    
    composer = VideoComposer()
    
    # 示例：手动同步单个视频音频对
    video_path = "example_video.mp4"  # 假设10秒
    audio_path = "example_audio.mp3"  # 假设6秒
    output_path = "synced_output.mp4"
    
    print(f"📁 输入文件:")
    print(f"   视频: {video_path}")
    print(f"   音频: {audio_path}")
    print(f"   输出: {output_path}")
    
    # 检测时长（示例值）
    video_duration = 10.0  # composer.get_video_duration(video_path)
    audio_duration = 6.0   # composer.get_audio_duration(audio_path)
    
    print(f"\n⏱️  时长信息:")
    print(f"   视频时长: {video_duration}秒")
    print(f"   音频时长: {audio_duration}秒")
    
    # 创建同步命令
    # cmd = composer._create_sync_command(
    #     video_path, audio_path, 
    #     audio_duration, video_duration, 
    #     output_path
    # )
    
    # 根据时长关系显示会使用的策略
    if abs(video_duration - audio_duration) <= 0.1:
        strategy = "直接合并（时长基本相等）"
    elif video_duration < audio_duration:
        strategy = f"循环播放视频（从{video_duration}秒循环到{audio_duration}秒）"
    else:
        strategy = f"截断视频（从{video_duration}秒截断到{audio_duration}秒）"
    
    print(f"\n🎯 同步策略: {strategy}")
    print(f"   最终输出时长: {audio_duration}秒")
    
    # 执行同步（示例）
    # import subprocess
    # result = subprocess.run(cmd, capture_output=True, timeout=120)
    
    composer.cleanup()


def example_batch_sync():
    """批量同步示例"""
    print("\n📦 批量同步示例")
    print("=" * 50)
    
    # 示例：批量处理多个视频音频对
    sync_pairs = [
        ("video1.mp4", "audio1.mp3", "短视频循环场景"),
        ("video2.mp4", "audio2.mp3", "长视频截断场景"),
        ("video3.mp4", "audio3.mp3", "等长直接合并场景"),
    ]
    
    composer = VideoComposer()
    
    print("🔄 批量处理流程:")
    for i, (video, audio, description) in enumerate(sync_pairs, 1):
        print(f"\n   片段 {i}: {description}")
        print(f"      视频: {video}")
        print(f"      音频: {audio}")
        print(f"      输出: synced_{i:03d}.mp4")
        
        # 在实际使用中，这里会调用同步方法
        # video_duration = composer.get_video_duration(video)
        # audio_duration = composer.get_audio_duration(audio)
        # cmd = composer._create_sync_command(video, audio, audio_duration, video_duration, f"synced_{i:03d}.mp4")
        # result = subprocess.run(cmd, capture_output=True, timeout=120)
    
    print("\n✅ 批量处理完成后，所有片段都将具有与对应音频相同的时长")
    
    composer.cleanup()


def main():
    """主函数"""
    print("🎥 视频音频同步功能使用示例")
    print("=" * 60)
    
    # 基本视频合成示例
    example_video_composition()
    
    # 手动同步示例
    example_manual_sync()
    
    # 批量同步示例
    example_batch_sync()
    
    print("\n" + "=" * 60)
    print("📚 使用说明:")
    print("1. 在实际项目中，确保视频和音频文件路径正确")
    print("2. 新的同步逻辑会自动处理时长不匹配问题")
    print("3. 支持的场景:")
    print("   • 短视频 + 长音频 = 循环视频")
    print("   • 长视频 + 短音频 = 截断视频")
    print("   • 等长视频音频 = 直接合并")
    print("4. 最终输出的视频时长严格等于音频时长")
    print("5. 所有操作都有详细的日志记录")
    
    print("\n🎉 音视频同步功能已就绪，可以在您的项目中使用！")


if __name__ == "__main__":
    main()
