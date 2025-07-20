"""
可靠的音频时长检测工具
专门处理Edge-TTS等生成的特殊格式音频文件
"""

import os
import struct
from typing import Optional
from pathlib import Path

from src.utils.logger import logger


class ReliableAudioDuration:
    """可靠的音频时长检测器"""
    
    def __init__(self):
        self.methods = [
            self._try_mutagen_mp3,
            self._try_mutagen_generic,
            self._try_mp3_frame_analysis,
            self._try_file_size_estimation
        ]
    
    def get_duration(self, audio_path: str) -> float:
        """获取音频时长（秒）"""
        if not audio_path or not os.path.exists(audio_path):
            return 0.0
        
        # 尝试各种方法
        for method in self.methods:
            try:
                duration = method(audio_path)
                if duration > 0:
                    logger.debug(f"使用{method.__name__}成功获取时长: {duration:.2f}秒")
                    return duration
            except Exception as e:
                logger.debug(f"{method.__name__}失败: {e}")
                continue
        
        logger.warning(f"所有方法都无法获取音频时长: {os.path.basename(audio_path)}")
        return 0.0
    
    def get_duration_string(self, audio_path: str) -> str:
        """获取音频时长字符串（MM:SS格式）"""
        duration = self.get_duration(audio_path)
        if duration <= 0:
            return "00:00"
        
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def _try_mutagen_mp3(self, audio_path: str) -> float:
        """尝试使用mutagen的MP3类"""
        try:
            import mutagen.mp3
            audio_file = mutagen.mp3.MP3(audio_path)
            if audio_file and audio_file.info and hasattr(audio_file.info, 'length'):
                return float(audio_file.info.length)
        except ImportError:
            raise Exception("mutagen库未安装")
        except Exception as e:
            raise Exception(f"mutagen MP3解析失败: {e}")
        
        raise Exception("mutagen MP3无法获取时长信息")
    
    def _try_mutagen_generic(self, audio_path: str) -> float:
        """尝试使用mutagen的通用File类"""
        try:
            import mutagen
            audio_file = mutagen.File(audio_path)
            if audio_file and audio_file.info and hasattr(audio_file.info, 'length'):
                return float(audio_file.info.length)
        except ImportError:
            raise Exception("mutagen库未安装")
        except Exception as e:
            raise Exception(f"mutagen通用解析失败: {e}")
        
        raise Exception("mutagen通用方法无法获取时长信息")
    
    def _try_mp3_frame_analysis(self, audio_path: str) -> float:
        """尝试分析MP3帧结构"""
        try:
            with open(audio_path, 'rb') as f:
                data = f.read()

            # 查找MP3帧头
            frame_count = 0
            pos = 0
            total_samples = 0
            sample_rate = 0

            while pos < len(data) - 4:
                # 查找帧同步字（11位全1）
                if data[pos] == 0xFF and (data[pos + 1] & 0xE0) == 0xE0:
                    # 解析MP3帧头
                    header = struct.unpack('>I', data[pos:pos+4])[0]

                    # 提取版本、层、比特率、采样率等信息
                    version = (header >> 19) & 0x3
                    layer = (header >> 17) & 0x3
                    bitrate_index = (header >> 12) & 0xF
                    sample_rate_index = (header >> 10) & 0x3
                    padding = (header >> 9) & 0x1

                    # 🔧 修复：正确的版本映射
                    # 计算采样率
                    sample_rates = {
                        3: [44100, 48000, 32000],  # MPEG-1
                        2: [22050, 24000, 16000],  # MPEG-2
                        0: [11025, 12000, 8000],   # MPEG-2.5
                    }

                    if version in sample_rates and sample_rate_index < 3:
                        current_sample_rate = sample_rates[version][sample_rate_index]
                        if sample_rate == 0:
                            sample_rate = current_sample_rate

                    # 🔧 修复：使用正确的比特率表
                    # 计算比特率
                    if version == 3 and layer == 1:  # MPEG-1 Layer III
                        bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
                    elif version == 2 and layer == 1:  # MPEG-2 Layer III
                        bitrates = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]
                    else:
                        bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]

                    if bitrate_index < len(bitrates):
                        bitrate = bitrates[bitrate_index]

                        # 🔧 修复：正确的帧大小计算，包含padding
                        if layer == 1:  # Layer III (MP3)
                            frame_size = int(144 * bitrate * 1000 / current_sample_rate) + padding
                            samples_per_frame = 1152
                        elif layer == 2:  # Layer II
                            frame_size = int(144 * bitrate * 1000 / current_sample_rate) + padding
                            samples_per_frame = 1152
                        else:  # Layer I
                            frame_size = int(12 * bitrate * 1000 / current_sample_rate + padding) * 4
                            samples_per_frame = 384

                        total_samples += samples_per_frame
                        frame_count += 1
                        pos += frame_size if frame_size > 0 else 1
                    else:
                        pos += 1
                else:
                    pos += 1

                # 限制分析的帧数，避免处理过大的文件
                if frame_count > 100:
                    break

            # 🔧 修复：使用实际分析的样本数计算时长
            if frame_count > 0 and sample_rate > 0:
                # 估算总帧数
                avg_frame_size = pos / frame_count if frame_count > 0 else 288  # 默认帧大小
                estimated_total_frames = len(data) / avg_frame_size

                # 计算总样本数
                avg_samples_per_frame = total_samples / frame_count
                total_estimated_samples = estimated_total_frames * avg_samples_per_frame

                # 计算时长
                duration = total_estimated_samples / sample_rate

                if 0.1 <= duration <= 3600:  # 合理的时长范围
                    return duration

        except Exception as e:
            raise Exception(f"MP3帧分析失败: {e}")

        raise Exception("MP3帧分析无法确定时长")
    
    def _try_file_size_estimation(self, audio_path: str) -> float:
        """基于文件大小的估算方法"""
        try:
            file_size = os.path.getsize(audio_path)
            
            # 根据文件扩展名使用不同的估算参数
            ext = Path(audio_path).suffix.lower()
            
            if ext == '.mp3':
                # 假设平均比特率为128kbps
                # 1字节 = 8位，128kbps = 128000位/秒 = 16000字节/秒
                estimated_duration = file_size / 16000
            elif ext == '.wav':
                # WAV文件通常是44.1kHz, 16bit, 立体声
                # 44100 * 2 * 2 = 176400字节/秒
                estimated_duration = file_size / 176400
            else:
                # 默认使用MP3的估算
                estimated_duration = file_size / 16000
            
            # 应用经验修正因子
            # Edge-TTS生成的文件通常比估算值稍长
            correction_factor = 1.2
            estimated_duration *= correction_factor
            
            if 0.1 <= estimated_duration <= 3600:  # 合理的时长范围
                return estimated_duration
            
        except Exception as e:
            raise Exception(f"文件大小估算失败: {e}")
        
        raise Exception("文件大小估算结果不合理")


# 全局实例
_duration_detector = ReliableAudioDuration()


def get_audio_duration(audio_path: str) -> float:
    """获取音频时长（秒）- 全局函数"""
    return _duration_detector.get_duration(audio_path)


def get_audio_duration_string(audio_path: str) -> str:
    """获取音频时长字符串（MM:SS格式）- 全局函数"""
    return _duration_detector.get_duration_string(audio_path)


def batch_analyze_durations(audio_paths: list) -> dict:
    """批量分析音频时长"""
    results = {}
    for path in audio_paths:
        if path and os.path.exists(path):
            results[path] = get_audio_duration(path)
        else:
            results[path] = 0.0
    return results


if __name__ == "__main__":
    # 测试代码
    test_file = "output/16岁/audio/edge_tts/segment_001_manual_segment_001.mp3"
    if os.path.exists(test_file):
        detector = ReliableAudioDuration()
        duration = detector.get_duration(test_file)
        duration_str = detector.get_duration_string(test_file)
        print(f"测试文件: {test_file}")
        print(f"时长: {duration:.2f}秒")
        print(f"格式化时长: {duration_str}")
    else:
        print("测试文件不存在")
