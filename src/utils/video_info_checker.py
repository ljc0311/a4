#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频信息检查工具
用于检查MP4视频文件的详细信息，包括时长、分辨率、编码等
"""

import os
import subprocess
import json
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class VideoInfoChecker:
    """视频信息检查器"""
    
    def __init__(self):
        self.ffprobe_path = self._find_ffprobe()
    
    def _find_ffprobe(self) -> str:
        """查找ffprobe可执行文件"""
        # 常见的ffprobe路径
        possible_paths = [
            "ffprobe",
            "ffprobe.exe",
            r"C:\ffmpeg\bin\ffprobe.exe",
            r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
            "/usr/bin/ffprobe",
            "/usr/local/bin/ffprobe"
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, "-version"], 
                                      capture_output=True, 
                                      timeout=5)
                if result.returncode == 0:
                    logger.debug(f"找到ffprobe: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        logger.warning("未找到ffprobe，某些功能可能不可用")
        return "ffprobe"
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        获取视频文件的详细信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            Dict: 包含视频信息的字典
        """
        if not os.path.exists(video_path):
            return {"error": f"视频文件不存在: {video_path}"}
        
        try:
            # 使用ffprobe获取详细信息
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                return {"error": f"ffprobe执行失败: {error_msg}"}
            
            # 解析JSON输出
            probe_data = json.loads(result.stdout.decode('utf-8'))
            
            # 提取关键信息
            info = self._extract_key_info(probe_data)
            info["file_path"] = video_path
            info["file_size_mb"] = os.path.getsize(video_path) / (1024 * 1024)
            
            return info
            
        except subprocess.TimeoutExpired:
            return {"error": "ffprobe执行超时"}
        except json.JSONDecodeError as e:
            return {"error": f"解析ffprobe输出失败: {e}"}
        except Exception as e:
            return {"error": f"获取视频信息失败: {e}"}
    
    def _extract_key_info(self, probe_data: Dict) -> Dict[str, Any]:
        """从ffprobe数据中提取关键信息"""
        info = {}
        
        # 格式信息
        if "format" in probe_data:
            format_info = probe_data["format"]
            info["duration"] = float(format_info.get("duration", 0))
            info["bitrate"] = int(format_info.get("bit_rate", 0))
            info["format_name"] = format_info.get("format_name", "")
            info["format_long_name"] = format_info.get("format_long_name", "")
        
        # 流信息
        video_streams = []
        audio_streams = []
        
        if "streams" in probe_data:
            for stream in probe_data["streams"]:
                if stream.get("codec_type") == "video":
                    video_streams.append({
                        "codec_name": stream.get("codec_name", ""),
                        "width": stream.get("width", 0),
                        "height": stream.get("height", 0),
                        "fps": self._parse_fps(stream.get("r_frame_rate", "")),
                        "bitrate": int(stream.get("bit_rate", 0)) if stream.get("bit_rate") else None,
                        "duration": float(stream.get("duration", 0)) if stream.get("duration") else None
                    })
                elif stream.get("codec_type") == "audio":
                    audio_streams.append({
                        "codec_name": stream.get("codec_name", ""),
                        "sample_rate": int(stream.get("sample_rate", 0)) if stream.get("sample_rate") else None,
                        "channels": stream.get("channels", 0),
                        "bitrate": int(stream.get("bit_rate", 0)) if stream.get("bit_rate") else None,
                        "duration": float(stream.get("duration", 0)) if stream.get("duration") else None
                    })
        
        info["video_streams"] = video_streams
        info["audio_streams"] = audio_streams
        
        # 主要视频流信息（如果存在）
        if video_streams:
            main_video = video_streams[0]
            info["width"] = main_video["width"]
            info["height"] = main_video["height"]
            info["fps"] = main_video["fps"]
            info["video_codec"] = main_video["codec_name"]
        
        # 主要音频流信息（如果存在）
        if audio_streams:
            main_audio = audio_streams[0]
            info["audio_codec"] = main_audio["codec_name"]
            info["sample_rate"] = main_audio["sample_rate"]
            info["channels"] = main_audio["channels"]
        
        return info
    
    def _parse_fps(self, fps_str: str) -> float:
        """解析帧率字符串"""
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                return float(num) / float(den)
            else:
                return float(fps_str)
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    def format_duration(self, seconds: float) -> str:
        """格式化时长为可读字符串"""
        if seconds <= 0:
            return "00:00"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def print_video_info(self, video_path: str) -> None:
        """打印视频信息到控制台"""
        info = self.get_video_info(video_path)
        
        if "error" in info:
            print(f"❌ 错误: {info['error']}")
            return
        
        print(f"📹 视频文件: {os.path.basename(video_path)}")
        print(f"📁 文件大小: {info.get('file_size_mb', 0):.2f} MB")
        print(f"⏱️ 时长: {self.format_duration(info.get('duration', 0))} ({info.get('duration', 0):.2f}秒)")
        print(f"📺 分辨率: {info.get('width', 0)}x{info.get('height', 0)}")
        print(f"🎬 帧率: {info.get('fps', 0):.2f} fps")
        print(f"🎥 视频编码: {info.get('video_codec', 'N/A')}")
        print(f"🎵 音频编码: {info.get('audio_codec', 'N/A')}")
        print(f"🔊 音频: {info.get('sample_rate', 0)} Hz, {info.get('channels', 0)} 声道")
        print(f"📊 比特率: {info.get('bitrate', 0)} bps")
        print(f"📋 格式: {info.get('format_name', 'N/A')}")
        
        # 详细流信息
        if info.get('video_streams'):
            print(f"\n🎥 视频流数量: {len(info['video_streams'])}")
        if info.get('audio_streams'):
            print(f"🎵 音频流数量: {len(info['audio_streams'])}")


def check_video_file(video_path: str) -> Dict[str, Any]:
    """检查单个视频文件的信息"""
    checker = VideoInfoChecker()
    return checker.get_video_info(video_path)


def print_video_file_info(video_path: str) -> None:
    """打印单个视频文件的信息"""
    checker = VideoInfoChecker()
    checker.print_video_info(video_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("用法: python video_info_checker.py <视频文件路径>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    print_video_file_info(video_path)
