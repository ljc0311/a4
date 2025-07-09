#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频合成器 - 使用FFmpeg将视频片段、配音、字幕、背景音乐合成为完整短片
"""

import os
import subprocess
import json
import tempfile
import random
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from src.utils.logger import logger

class VideoComposer:
    """视频合成器"""
    
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.temp_dir = tempfile.mkdtemp(prefix="video_composer_")
    
    def _find_ffmpeg(self) -> str:
        """查找FFmpeg可执行文件"""
        # 常见的FFmpeg路径
        possible_paths = [
            "ffmpeg/bin/ffmpeg.exe",  # 本地安装目录
            "./ffmpeg/bin/ffmpeg.exe",  # 本地目录
            "ffmpeg",  # 系统PATH中
            "ffmpeg.exe",  # Windows
            "/usr/bin/ffmpeg",  # Linux
            "/usr/local/bin/ffmpeg",  # macOS
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, "-version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"找到FFmpeg: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        logger.warning("未找到FFmpeg，某些功能可能不可用")
        return "ffmpeg"  # 默认值
    
    def get_video_info(self, video_path: str) -> Dict:
        """获取视频信息"""
        try:
            cmd = [
                self.ffmpeg_path, "-i", video_path,
                "-f", "null", "-"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )

            # 处理编码问题
            stderr = self._decode_output(result.stderr)
            info = {
                'duration': 0.0,
                'width': 0,
                'height': 0,
                'fps': 30.0
            }
            
            # 解析时长
            if "Duration:" in stderr:
                duration_line = [line for line in stderr.split('\n') if 'Duration:' in line][0]
                duration_str = duration_line.split('Duration:')[1].split(',')[0].strip()
                info['duration'] = self._parse_duration(duration_str)
            
            # 解析分辨率和帧率
            if "Video:" in stderr:
                video_line = [line for line in stderr.split('\n') if 'Video:' in line][0]
                if 'x' in video_line:
                    resolution_part = video_line.split('x')
                    if len(resolution_part) >= 2:
                        try:
                            info['width'] = int(resolution_part[0].split()[-1])
                            info['height'] = int(resolution_part[1].split()[0])
                        except ValueError:
                            pass
                
                if 'fps' in video_line:
                    fps_part = video_line.split('fps')[0].split()[-1]
                    try:
                        info['fps'] = float(fps_part)
                    except ValueError:
                        pass
            
            return info
            
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            return {'duration': 5.0, 'width': 1280, 'height': 720, 'fps': 30.0}
    
    def _parse_duration(self, duration_str: str) -> float:
        """解析时长字符串为秒数"""
        try:
            # 格式: HH:MM:SS.mmm
            parts = duration_str.split(':')
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        except Exception:
            pass
        return 0.0
    
    def create_video_list(self, video_segments: List[Dict]) -> str:
        """创建视频列表文件"""
        try:
            list_file = os.path.join(self.temp_dir, "video_list.txt")
            
            with open(list_file, 'w', encoding='utf-8') as f:
                for segment in video_segments:
                    video_path = segment.get('video_path', '')
                    if os.path.exists(video_path):
                        # FFmpeg concat格式
                        f.write(f"file '{video_path}'\n")
            
            return list_file
            
        except Exception as e:
            logger.error(f"创建视频列表文件失败: {e}")
            raise
    
    def concatenate_videos(self, video_segments: List[Dict], output_path: str, transition_config: Dict = None) -> bool:
        """连接视频片段，支持转场效果"""
        try:
            if not transition_config or len(video_segments) <= 1:
                # 无转场效果，使用简单连接
                return self._simple_concatenate(video_segments, output_path)
            else:
                # 有转场效果，使用复杂滤镜连接
                return self._concatenate_with_transitions(video_segments, output_path, transition_config)

        except Exception as e:
            logger.error(f"连接视频失败: {e}")
            return False

    def _simple_concatenate(self, video_segments: List[Dict], output_path: str) -> bool:
        """简单视频连接（无转场）"""
        try:
            list_file = self.create_video_list(video_segments)

            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                "-y",  # 覆盖输出文件
                output_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode == 0:
                logger.info(f"视频连接成功: {output_path}")
                return True
            else:
                stderr = self._decode_output(result.stderr)
                logger.error(f"视频连接失败: {stderr}")
                return False

        except Exception as e:
            logger.error(f"简单连接视频失败: {e}")
            return False

    def _concatenate_with_transitions(self, video_segments: List[Dict], output_path: str, transition_config: Dict) -> bool:
        """带转场效果的视频连接"""
        try:
            logger.info(f"开始生成带转场效果的视频，片段数量: {len(video_segments)}")

            # 生成转场效果
            transitions = self._generate_transition_effects(video_segments, transition_config)
            duration = transition_config.get('duration', 0.5)

            # 对于多个片段，使用简化的转场方案
            # 为每个片段添加淡入淡出效果，然后连接
            processed_segments = []

            for i, segment in enumerate(video_segments):
                video_path = segment.get('video_path', '')
                if not os.path.exists(video_path):
                    continue

                # 为每个片段添加转场效果
                transition_video = os.path.join(self.temp_dir, f"transition_{i}.mp4")

                if i == 0:
                    # 第一个片段：只添加淡出
                    filter_str = f"fade=t=out:st={segment.get('duration', 5.0) - duration}:d={duration}"
                elif i == len(video_segments) - 1:
                    # 最后一个片段：只添加淡入
                    filter_str = f"fade=t=in:st=0:d={duration}"
                else:
                    # 中间片段：添加淡入和淡出
                    filter_str = f"fade=t=in:st=0:d={duration},fade=t=out:st={segment.get('duration', 5.0) - duration}:d={duration}"

                cmd = [
                    self.ffmpeg_path,
                    "-i", video_path,
                    "-vf", filter_str,
                    "-c:a", "copy",
                    "-y",
                    transition_video
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

                if result.returncode == 0:
                    processed_segments.append({
                        'video_path': transition_video,
                        'duration': segment.get('duration', 5.0)
                    })
                    logger.info(f"片段 {i+1} 转场处理完成")
                else:
                    logger.warning(f"片段 {i+1} 转场处理失败，使用原片段")
                    processed_segments.append(segment)

            # 连接处理后的片段
            if processed_segments:
                return self._simple_concatenate(processed_segments, output_path)
            else:
                return False

        except Exception as e:
            logger.error(f"转场视频合成失败: {e}")
            # 回退到简单连接
            return self._simple_concatenate(video_segments, output_path)
    
    def add_audio_track(self, video_path: str, audio_segments: List[Dict], output_path: str) -> bool:
        """添加音频轨道"""
        try:
            logger.info(f"开始添加音频轨道，音频片段数量: {len(audio_segments)}")

            # 创建音频列表
            audio_list_file = os.path.join(self.temp_dir, "audio_list.txt")
            valid_audio_count = 0

            with open(audio_list_file, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(audio_segments):
                    audio_path = segment.get('audio_path', '')
                    if os.path.exists(audio_path):
                        f.write(f"file '{audio_path}'\n")
                        valid_audio_count += 1
                        logger.info(f"添加音频文件 {i+1}: {audio_path}")
                    else:
                        logger.warning(f"音频文件不存在 {i+1}: {audio_path}")

            logger.info(f"有效音频文件数量: {valid_audio_count}")

            if valid_audio_count == 0:
                logger.error("没有有效的音频文件")
                return False

            # 连接音频文件
            combined_audio = os.path.join(self.temp_dir, "combined_audio.mp3")

            audio_concat_cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", audio_list_file,
                "-c", "copy",
                "-y",
                combined_audio
            ]

            logger.info(f"执行音频连接命令: {' '.join(audio_concat_cmd)}")
            result = subprocess.run(audio_concat_cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.error(f"音频连接失败: {result.stderr}")
                logger.error(f"音频连接命令输出: {result.stdout}")
                return False

            logger.info(f"音频连接成功: {combined_audio}")

            # 检查合并后的音频文件
            if not os.path.exists(combined_audio):
                logger.error(f"合并后的音频文件不存在: {combined_audio}")
                return False

            # 将音频添加到视频
            cmd = [
                self.ffmpeg_path,
                "-i", video_path,
                "-i", combined_audio,
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                "-y",
                output_path
            ]

            logger.info(f"执行音频合并命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, timeout=300)

            if result.returncode == 0:
                logger.info(f"音频添加成功: {output_path}")
                return True
            else:
                stderr = self._decode_output(result.stderr)
                stdout = self._decode_output(result.stdout)
                logger.error(f"音频添加失败: {stderr}")
                logger.error(f"音频添加命令输出: {stdout}")
                return False
                
        except Exception as e:
            logger.error(f"添加音频轨道失败: {e}")
            return False
    
    def add_background_music(self, video_path: str, music_path: str, output_path: str, 
                           volume: float = 0.3, loop: bool = True, 
                           fade_in: bool = True, fade_out: bool = True) -> bool:
        """添加背景音乐"""
        try:
            if not os.path.exists(music_path):
                logger.warning(f"背景音乐文件不存在: {music_path}")
                return False
            
            # 获取视频时长
            video_info = self.get_video_info(video_path)
            video_duration = video_info['duration']
            
            # 构建音频滤镜
            audio_filters = []
            
            # 音量调整
            audio_filters.append(f"volume={volume}")
            
            # 循环播放
            if loop:
                audio_filters.append(f"aloop=loop=-1:size=2e+09")
            
            # 淡入淡出效果
            if fade_in:
                audio_filters.append("afade=t=in:ss=0:d=2")
            
            if fade_out:
                fade_start = max(0, video_duration - 2)
                audio_filters.append(f"afade=t=out:st={fade_start}:d=2")
            
            # 限制音频长度
            audio_filters.append(f"atrim=duration={video_duration}")
            
            filter_complex = "[1:a]" + ",".join(audio_filters) + "[bg]; [0:a][bg]amix=inputs=2:duration=first[out]"
            
            cmd = [
                self.ffmpeg_path,
                "-i", video_path,
                "-i", music_path,
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[out]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-y",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=600)

            if result.returncode == 0:
                logger.info(f"背景音乐添加成功: {output_path}")
                return True
            else:
                stderr = self._decode_output(result.stderr)
                logger.error(f"背景音乐添加失败: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"添加背景音乐失败: {e}")
            return False
    
    def add_subtitles(self, video_path: str, subtitle_segments: List[Dict], output_path: str, subtitle_config: Dict = None) -> bool:
        """添加字幕"""
        try:
            # 创建SRT字幕文件
            srt_file = os.path.join(self.temp_dir, "subtitles.srt")

            with open(srt_file, 'w', encoding='utf-8') as f:
                current_time = 0.0
                subtitle_index = 1

                for i, segment in enumerate(subtitle_segments):
                    text = segment.get('subtitle_text', '').strip()
                    duration = segment.get('duration', 5.0)

                    logger.info(f"处理字幕片段 {i+1}: 文本长度={len(text)}, 时长={duration:.2f}秒")
                    if text:
                        logger.info(f"字幕片段 {i+1} 文本预览: {text[:100]}...")
                    else:
                        logger.warning(f"字幕片段 {i+1} 没有文本内容")

                    if text:  # 只有有文本的才添加字幕
                        # SRT时间格式: HH:MM:SS,mmm
                        start_time = self._seconds_to_srt_time(current_time)
                        end_time = self._seconds_to_srt_time(current_time + duration)

                        f.write(f"{subtitle_index}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{text}\n\n")

                        subtitle_index += 1
                        logger.info(f"添加字幕 {subtitle_index-1}: {start_time} --> {end_time} | {text[:50]}...")

                    current_time += duration

            # 使用FFmpeg添加字幕，支持样式配置
            # 将反斜杠转换为正斜杠，并正确转义冒号
            srt_file_escaped = srt_file.replace('\\', '/').replace(':', '\\\\:')

            # 获取字幕样式配置
            if subtitle_config is None:
                subtitle_config = {}

            font_size = subtitle_config.get('font_size', 24)
            font_color = subtitle_config.get('font_color', '#ffffff')
            outline_color = subtitle_config.get('outline_color', '#000000')
            outline_size = subtitle_config.get('outline_size', 2)
            position = subtitle_config.get('position', '底部')

            # 转换颜色格式 (#ffffff -> &Hffffff)
            font_color_bgr = self._hex_to_bgr(font_color)
            outline_color_bgr = self._hex_to_bgr(outline_color)

            # 设置字幕位置
            alignment = 2  # 底部居中
            if position == "顶部":
                alignment = 8  # 顶部居中
            elif position == "中间":
                alignment = 5  # 中间居中

            # 构建字幕样式
            style = f"FontSize={font_size},PrimaryColour={font_color_bgr},OutlineColour={outline_color_bgr},Outline={outline_size},Alignment={alignment}"

            cmd = [
                self.ffmpeg_path,
                "-i", video_path,
                "-vf", f"subtitles={srt_file_escaped}:force_style='{style}'",
                "-c:a", "copy",
                "-y",
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=300)

            if result.returncode == 0:
                logger.info(f"字幕添加成功: {output_path}")
                return True
            else:
                stderr = self._decode_output(result.stderr)
                logger.error(f"字幕添加失败: {stderr}")
                return False

        except Exception as e:
            logger.error(f"添加字幕失败: {e}")
            return False

    def _seconds_to_srt_time(self, seconds: float) -> str:
        """将秒数转换为SRT时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

    def _hex_to_bgr(self, hex_color: str) -> str:
        """将十六进制颜色转换为BGR格式（用于ASS字幕）"""
        # 移除#号
        hex_color = hex_color.lstrip('#')

        # 解析RGB值
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # 转换为BGR格式并返回ASS格式
        return f"&H{b:02x}{g:02x}{r:02x}"

    def _get_transition_filter(self, transition_type: str, duration: float, intensity: int) -> str:
        """获取转场滤镜"""
        # 强度映射到0.1-1.0
        intensity_value = intensity / 10.0

        transition_filters = {
            "淡入淡出": f"fade=t=in:st=0:d={duration}",
            "左滑": f"slide=direction=left:duration={duration}",
            "右滑": f"slide=direction=right:duration={duration}",
            "上滑": f"slide=direction=up:duration={duration}",
            "下滑": f"slide=direction=down:duration={duration}",
            "缩放": f"zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d={int(duration*30)}:s=1920x1080",
            "旋转": f"rotate=angle='2*PI*t/{duration}':fillcolor=black",
            "溶解": f"fade=t=in:st=0:d={duration}:alpha=1",
            "擦除": f"wipe=direction=right:duration={duration}",
            "推拉": f"push=direction=left:duration={duration}"
        }

        return transition_filters.get(transition_type, transition_filters["淡入淡出"])

    def _get_random_transition(self) -> str:
        """获取随机转场类型"""
        transitions = [
            "淡入淡出", "左滑", "右滑", "上滑", "下滑",
            "缩放", "旋转", "溶解", "擦除", "推拉"
        ]
        return random.choice(transitions)

    def _generate_transition_effects(self, segments: List[Dict], transition_config: Dict) -> List[str]:
        """生成转场效果列表"""
        if len(segments) <= 1:
            return []

        mode = transition_config.get('mode', '随机转场')
        duration = transition_config.get('duration', 0.5)
        intensity = transition_config.get('intensity', 5)
        uniform_type = transition_config.get('uniform_type', '淡入淡出')

        transitions = []

        for i in range(len(segments) - 1):  # 转场数量比片段数量少1
            if mode == "随机转场":
                transition_type = self._get_random_transition()
            elif mode == "统一转场":
                transition_type = uniform_type
            else:  # 自定义转场（暂时使用随机）
                transition_type = self._get_random_transition()

            transitions.append(transition_type)
            logger.info(f"片段 {i+1} -> {i+2} 转场: {transition_type}")

        return transitions

    def get_audio_duration(self, audio_path: str) -> float:
        """获取音频文件时长"""
        try:
            if not audio_path or not os.path.exists(audio_path):
                logger.warning(f"音频文件不存在: {audio_path}")
                return 5.0

            # 方法1：尝试使用mutagen（最可靠）
            try:
                from mutagen import File
                audio_file = File(audio_path)
                if audio_file and hasattr(audio_file, 'info') and hasattr(audio_file.info, 'length'):
                    duration = float(audio_file.info.length)
                    logger.debug(f"mutagen获取音频时长成功: {audio_path} -> {duration:.2f}s")
                    return duration
            except ImportError:
                logger.debug("mutagen未安装，尝试其他方法")
            except Exception as e:
                logger.debug(f"mutagen获取音频时长失败: {e}")

            # 方法2：使用FFmpeg，处理编码问题
            try:
                cmd = [
                    self.ffmpeg_path,
                    "-i", audio_path,
                    "-f", "null",
                    "-"
                ]

                # 使用bytes模式避免编码问题
                result = subprocess.run(cmd, capture_output=True, timeout=30)

                # 尝试不同的编码方式解码stderr
                stderr_text = None
                for encoding in ['utf-8', 'gbk', 'cp1252', 'latin1']:
                    try:
                        stderr_text = result.stderr.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue

                if stderr_text is None:
                    # 如果所有编码都失败，使用errors='ignore'
                    stderr_text = result.stderr.decode('utf-8', errors='ignore')

                # 从stderr中解析时长信息
                if stderr_text:
                    for line in stderr_text.split('\n'):
                        if 'Duration:' in line:
                            # 格式: Duration: 00:00:05.23, start: 0.000000, bitrate: 32 kb/s
                            duration_str = line.split('Duration:')[1].split(',')[0].strip()
                            time_parts = duration_str.split(':')
                            if len(time_parts) == 3:
                                hours = float(time_parts[0])
                                minutes = float(time_parts[1])
                                seconds = float(time_parts[2])
                                total_seconds = hours * 3600 + minutes * 60 + seconds
                                logger.debug(f"FFmpeg获取音频时长成功: {audio_path} -> {total_seconds:.2f}s")
                                return total_seconds

            except Exception as e:
                logger.debug(f"FFmpeg获取音频时长失败: {e}")

            # 方法3：使用文件大小估算（最后的备用方案）
            try:
                file_size = os.path.getsize(audio_path)
                # 假设平均比特率为128kbps
                estimated_duration = file_size / (128 * 1024 / 8)
                estimated_duration = max(1.0, min(estimated_duration, 30.0))  # 限制在1-30秒之间
                logger.debug(f"文件大小估算音频时长: {audio_path} -> {estimated_duration:.2f}s")
                return estimated_duration
            except Exception as e:
                logger.debug(f"文件大小估算失败: {e}")

            logger.warning(f"无法获取音频时长，使用默认值: {audio_path}")
            return 5.0  # 默认5秒

        except Exception as e:
            logger.error(f"获取音频时长失败: {e}")
            return 5.0

    def _decode_output(self, output_bytes: bytes) -> str:
        """解码subprocess输出，处理编码问题"""
        if not output_bytes:
            return ""

        # 尝试不同的编码方式解码
        for encoding in ['utf-8', 'gbk', 'cp1252', 'latin1']:
            try:
                return output_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue

        # 如果所有编码都失败，使用errors='ignore'
        return output_bytes.decode('utf-8', errors='ignore')

    def compose_final_video(self, video_segments: List[Dict], audio_segments: List[Dict],
                          background_music: str, output_path: str, config: Dict) -> bool:
        """合成最终视频 - 新的同步合成方法"""
        try:
            logger.info("开始合成最终视频...")
            logger.info(f"视频片段数量: {len(video_segments)}")
            logger.info(f"音频片段数量: {len(audio_segments)}")

            # 使用新的同步合成方法
            return self.compose_video_with_sync(video_segments, audio_segments, background_music, output_path, config)

        except Exception as e:
            logger.error(f"合成最终视频失败: {e}")
            return False

    def compose_video_with_sync(self, video_segments: List[Dict], audio_segments: List[Dict],
                               background_music: str, output_path: str, config: Dict) -> bool:
        """同步合成视频和音频"""
        try:
            # 创建同步的视频音频片段
            synced_segments = []

            for i, (video_seg, audio_seg) in enumerate(zip(video_segments, audio_segments)):
                video_path = video_seg.get('video_path', '')
                audio_path = audio_seg.get('audio_path', '')
                subtitle_text = video_seg.get('subtitle_text', '')

                if not os.path.exists(video_path) or not os.path.exists(audio_path):
                    logger.warning(f"片段 {i+1} 视频或音频文件不存在")
                    continue

                # 获取音频实际时长
                audio_duration = self.get_audio_duration(audio_path)
                if audio_duration <= 0:
                    audio_duration = 5.0  # 默认5秒

                logger.info(f"片段 {i+1}: 音频时长 {audio_duration:.2f}秒")

                # 创建同步的视频片段（调整视频时长匹配音频）
                synced_video = os.path.join(self.temp_dir, f"synced_{i:03d}.mp4")

                # 使用FFmpeg创建同步的视频音频片段，支持视频循环播放
                # 如果音频时长超过视频时长，让视频循环播放
                cmd = [
                    self.ffmpeg_path,
                    "-stream_loop", "-1",  # 无限循环视频
                    "-i", video_path,
                    "-i", audio_path,
                    "-t", str(audio_duration),  # 设置时长为音频时长
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-filter:a", "volume=3.0",  # 增加音频音量3倍
                    "-map", "0:v:0",  # 使用视频流（循环）
                    "-map", "1:a:0",  # 使用音频流
                    "-shortest",  # 以最短流为准（音频）
                    "-y",
                    synced_video
                ]

                logger.info(f"执行同步命令: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, timeout=60)

                if result.returncode == 0:
                    # 检查生成的文件是否有音频
                    logger.info(f"检查同步后的文件: {synced_video}")
                    if os.path.exists(synced_video):
                        file_size = os.path.getsize(synced_video)
                        logger.info(f"同步文件大小: {file_size} 字节")

                        # 使用FFprobe检查音频流
                        probe_cmd = [
                            self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe'),
                            "-v", "quiet",
                            "-show_streams",
                            "-select_streams", "a",
                            synced_video
                        ]
                        probe_result = subprocess.run(probe_cmd, capture_output=True, timeout=30)
                        stdout = self._decode_output(probe_result.stdout)
                        stderr = self._decode_output(probe_result.stderr)
                        if probe_result.returncode == 0 and stdout.strip():
                            logger.info(f"片段 {i+1} 音频流检测成功")
                            # 检查音频流详细信息
                            if "codec_name" in stdout:
                                logger.info(f"片段 {i+1} 音频编码信息: {stdout[:100]}...")
                        else:
                            logger.warning(f"片段 {i+1} 音频流检测失败")
                            logger.warning(f"FFprobe输出: {stderr}")

                    synced_segments.append({
                        'video_path': synced_video,
                        'duration': audio_duration,
                        'subtitle_text': subtitle_text
                    })
                    logger.info(f"片段 {i+1} 同步成功，字幕文本长度: {len(subtitle_text)}")
                else:
                    stderr = self._decode_output(result.stderr)
                    stdout = self._decode_output(result.stdout)
                    logger.error(f"片段 {i+1} 同步失败: {stderr}")
                    logger.error(f"FFmpeg输出: {stdout}")
                    return False

            # 连接所有同步的片段
            temp_video = os.path.join(self.temp_dir, "concatenated_synced.mp4")
            transition_config = config.get('transition_config', {})
            if not self.concatenate_videos(synced_segments, temp_video, transition_config):
                return False

            # 添加字幕
            temp_video_with_subtitles = os.path.join(self.temp_dir, "video_with_subtitles.mp4")
            has_subtitles = any(seg.get('subtitle_text', '').strip() for seg in synced_segments)

            if has_subtitles:
                logger.info("开始添加字幕...")
                # 获取字幕配置
                subtitle_config = config.get('subtitle_config', {})
                if not self.add_subtitles(temp_video, synced_segments, temp_video_with_subtitles, subtitle_config):
                    logger.warning("字幕添加失败，使用无字幕版本")
                    temp_video_with_subtitles = temp_video
            else:
                logger.info("没有字幕数据，跳过字幕添加")
                temp_video_with_subtitles = temp_video

            # 添加背景音乐
            if background_music and os.path.exists(background_music):
                logger.info("开始添加背景音乐...")
                volume = config.get('music_volume', 30) / 100.0
                loop_music = config.get('loop_music', True)
                fade_in = config.get('fade_in', True)
                fade_out = config.get('fade_out', True)

                if not self.add_background_music(
                    temp_video_with_subtitles,
                    background_music,
                    output_path,
                    volume,
                    loop_music,
                    fade_in,
                    fade_out
                ):
                    logger.warning("背景音乐添加失败，使用无背景音乐版本")
                    import shutil
                    shutil.copy2(temp_video_with_subtitles, output_path)
            else:
                logger.info("没有背景音乐，直接输出视频")
                import shutil
                shutil.copy2(temp_video_with_subtitles, output_path)

            logger.info(f"同步视频合成完成: {output_path}")
            return True

        except Exception as e:
            logger.error(f"合成最终视频失败: {e}")
            return False
    
    def cleanup(self):
        """清理临时文件"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info("临时文件清理完成")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
    
    def __del__(self):
        """析构函数"""
        self.cleanup()
