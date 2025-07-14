# -*- coding: utf-8 -*-
"""
视频格式转换服务
支持多平台视频格式适配和批量处理
"""

import asyncio
import subprocess
import os
import json
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from pathlib import Path
from src.utils.logger import logger

@dataclass
class PlatformSpec:
    """平台视频规格"""
    name: str
    resolution: str  # "1920x1080"
    aspect_ratio: str  # "16:9"
    fps: int
    bitrate: str  # "2M"
    format: str  # "mp4"
    codec: str  # "h264"
    max_duration: int  # 秒，0表示无限制
    max_size: int  # MB

class VideoFormatConverter:
    """视频格式转换服务"""
    
    # 平台规格配置
    PLATFORM_SPECS = {
        'douyin': PlatformSpec(
            name='抖音',
            resolution='1080x1920',
            aspect_ratio='9:16',
            fps=30,
            bitrate='3M',
            format='mp4',
            codec='h264',
            max_duration=60,
            max_size=100
        ),
        'kuaishou': PlatformSpec(
            name='快手',
            resolution='1080x1920',
            aspect_ratio='9:16',
            fps=30,
            bitrate='3M',
            format='mp4',
            codec='h264',
            max_duration=57,
            max_size=100
        ),
        'bilibili': PlatformSpec(
            name='B站',
            resolution='1920x1080',
            aspect_ratio='16:9',
            fps=60,
            bitrate='8M',
            format='mp4',
            codec='h264',
            max_duration=0,  # 无限制
            max_size=8192  # 8GB
        ),
        'xiaohongshu': PlatformSpec(
            name='小红书',
            resolution='1080x1080',
            aspect_ratio='1:1',
            fps=30,
            bitrate='2M',
            format='mp4',
            codec='h264',
            max_duration=60,
            max_size=100
        ),
        'wechat_channels': PlatformSpec(
            name='微信视频号',
            resolution='1080x1920',
            aspect_ratio='9:16',
            fps=30,
            bitrate='2M',
            format='mp4',
            codec='h264',
            max_duration=60,
            max_size=100
        ),
        'youtube_shorts': PlatformSpec(
            name='YouTube Shorts',
            resolution='1080x1920',
            aspect_ratio='9:16',
            fps=30,
            bitrate='4M',
            format='mp4',
            codec='h264',
            max_duration=60,
            max_size=256
        )
    }
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self.temp_dir = Path("temp/video_conversion")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查FFmpeg是否可用
        self._check_ffmpeg()
        
    def _check_ffmpeg(self):
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info("FFmpeg检查通过")
            else:
                logger.warning("FFmpeg可能不可用")
        except Exception as e:
            logger.error(f"FFmpeg检查失败: {e}")
        
    async def convert_for_platform(self, 
                                 input_path: str,
                                 platform: str,
                                 output_dir: str,
                                 progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """为指定平台转换视频格式"""
        try:
            if platform not in self.PLATFORM_SPECS:
                raise ValueError(f"不支持的平台: {platform}")
                
            spec = self.PLATFORM_SPECS[platform]
            
            if progress_callback:
                progress_callback(0.1, "分析视频信息...")
                
            # 分析输入视频
            video_info = await self._analyze_video(input_path)
            
            if progress_callback:
                progress_callback(0.2, "检查转换需求...")
                
            # 检查是否需要转换
            if self._needs_conversion(video_info, spec):
                output_path = os.path.join(output_dir, f"{platform}_{Path(input_path).stem}.{spec.format}")
                
                if progress_callback:
                    progress_callback(0.3, "生成转换命令...")
                
                # 生成FFmpeg命令
                cmd = self._build_ffmpeg_command(input_path, output_path, spec, video_info)
                
                if progress_callback:
                    progress_callback(0.4, "开始视频转换...")
                
                # 执行转换
                success = await self._execute_conversion(
                    cmd, 
                    lambda p, msg: progress_callback(0.4 + p * 0.5, msg) if progress_callback else None
                )
                
                if success and os.path.exists(output_path):
                    if progress_callback:
                        progress_callback(1.0, "转换完成")
                        
                    return {
                        'success': True,
                        'output_path': output_path,
                        'platform': platform,
                        'original_size': os.path.getsize(input_path),
                        'converted_size': os.path.getsize(output_path),
                        'spec_applied': spec.__dict__
                    }
                else:
                    raise Exception("转换失败或输出文件不存在")
            else:
                # 不需要转换，直接返回原文件
                if progress_callback:
                    progress_callback(1.0, "无需转换")
                    
                return {
                    'success': True,
                    'output_path': input_path,
                    'platform': platform,
                    'conversion_needed': False
                }
                
        except Exception as e:
            logger.error(f"视频转换失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'platform': platform
            }
            
    async def _analyze_video(self, video_path: str) -> Dict[str, Any]:
        """分析视频信息"""
        try:
            # 尝试使用ffprobe分析视频
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg', 'ffprobe')
            cmd = [
                ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                info = json.loads(stdout.decode())

                # 提取视频流信息
                video_stream = None
                for stream in info.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        video_stream = stream
                        break

                if video_stream:
                    # 安全地计算帧率
                    fps = 30  # 默认帧率
                    try:
                        r_frame_rate = video_stream.get('r_frame_rate', '30/1')
                        if '/' in r_frame_rate:
                            num, den = r_frame_rate.split('/')
                            fps = int(num) / int(den) if int(den) != 0 else 30
                        else:
                            fps = float(r_frame_rate)
                    except:
                        fps = 30

                    return {
                        'width': int(video_stream.get('width', 0)),
                        'height': int(video_stream.get('height', 0)),
                        'fps': fps,
                        'codec': video_stream.get('codec_name', ''),
                        'duration': float(info.get('format', {}).get('duration', 0)),
                        'bitrate': int(info.get('format', {}).get('bit_rate', 0)),
                        'size': int(info.get('format', {}).get('size', 0))
                    }

            # 如果ffprobe失败，返回默认值
            return {
                'width': 1920,
                'height': 1080,
                'fps': 30,
                'codec': 'unknown',
                'duration': 0,
                'bitrate': 0,
                'size': os.path.getsize(video_path) if os.path.exists(video_path) else 0
            }

        except Exception as e:
            logger.error(f"分析视频信息失败: {e}")
            # 返回基本信息
            return {
                'width': 1920,
                'height': 1080,
                'fps': 30,
                'codec': 'unknown',
                'duration': 0,
                'bitrate': 0,
                'size': os.path.getsize(video_path) if os.path.exists(video_path) else 0
            }
            
    def _needs_conversion(self, video_info: Dict[str, Any], spec: PlatformSpec) -> bool:
        """检查是否需要转换"""
        if not video_info:
            return True
            
        # 检查分辨率
        target_width, target_height = map(int, spec.resolution.split('x'))
        if video_info.get('width') != target_width or video_info.get('height') != target_height:
            return True
            
        # 检查帧率
        if abs(video_info.get('fps', 0) - spec.fps) > 1:
            return True
            
        # 检查编码格式
        if video_info.get('codec', '').lower() != spec.codec.lower():
            return True
            
        return False
        
    def _build_ffmpeg_command(self, input_path: str, output_path: str, 
                             spec: PlatformSpec, video_info: Dict) -> List[str]:
        """构建FFmpeg转换命令"""
        cmd = [
            self.ffmpeg_path,
            '-i', input_path,
            '-c:v', spec.codec,
            '-b:v', spec.bitrate,
            '-r', str(spec.fps),
            '-s', spec.resolution,
            '-aspect', spec.aspect_ratio,
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',  # 优化网络播放
            '-y',  # 覆盖输出文件
            output_path
        ]
        
        # 根据平台添加特殊参数
        if spec.name == 'B站':
            cmd.extend(['-preset', 'medium', '-crf', '23'])
        elif 'shorts' in spec.name.lower() or '抖音' in spec.name:
            cmd.extend(['-preset', 'fast', '-crf', '28'])
            
        return cmd
        
    async def _execute_conversion(self, cmd: List[str], 
                                progress_callback: Optional[Callable] = None) -> bool:
        """执行转换命令"""
        try:
            logger.info(f"执行转换命令: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 模拟进度更新
            if progress_callback:
                for i in range(10):
                    await asyncio.sleep(0.5)
                    progress_callback(i / 10, f"转换进度: {i*10}%")
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("视频转换成功")
                return True
            else:
                error_msg = stderr.decode() if stderr else "未知错误"
                logger.error(f"视频转换失败: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"执行转换命令失败: {e}")
            return False
            
    async def batch_convert(self, tasks: List[Dict[str, Any]], 
                          progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """批量转换视频"""
        results = []
        total_tasks = len(tasks)
        
        for i, task in enumerate(tasks):
            try:
                if progress_callback:
                    progress_callback(i / total_tasks, f"处理任务 {i+1}/{total_tasks}")
                    
                result = await self.convert_for_platform(
                    input_path=task['input_path'],
                    platform=task['platform'],
                    output_dir=task['output_dir'],
                    progress_callback=None  # 不传递内部进度
                )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"批量转换任务 {i+1} 失败: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'platform': task.get('platform', 'unknown')
                })
                
        if progress_callback:
            progress_callback(1.0, "批量转换完成")
            
        return results
        
    def get_platform_specs(self) -> Dict[str, PlatformSpec]:
        """获取所有平台规格"""
        return self.PLATFORM_SPECS.copy()
        
    def get_supported_platforms(self) -> List[str]:
        """获取支持的平台列表"""
        return list(self.PLATFORM_SPECS.keys())
