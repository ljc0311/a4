#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频文件管理器
负责管理配音生成的音频文件的存储和组织
"""

import os
import json
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from src.utils.logger import logger


class AudioFileManager:
    """音频文件管理器"""
    
    def __init__(self, project_root: str):
        """
        初始化音频文件管理器
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root)
        # 🔧 修复：project_root已经是项目目录了，直接在其下创建audio和subtitles
        # 因为传入的project_root通常已经是 output/项目名/ 这个路径
        self.audio_root = self.project_root / "audio"
        self.subtitles_root = self.project_root / "subtitles"

        logger.info(f"音频文件管理器路径设置: project_root={self.project_root}, audio_root={self.audio_root}")
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        try:
            self.audio_root.mkdir(parents=True, exist_ok=True)
            self.subtitles_root.mkdir(parents=True, exist_ok=True)
            
            # 为每个引擎创建子目录
            engines = ['edge_tts', 'cosyvoice', 'ttsmaker', 'xunfei', 'elevenlabs']
            for engine in engines:
                (self.audio_root / engine).mkdir(exist_ok=True)
                (self.subtitles_root / engine).mkdir(exist_ok=True)
            
            logger.info(f"音频目录结构已创建: {self.audio_root}")
            
        except Exception as e:
            logger.error(f"创建音频目录失败: {e}")
    
    def get_engine_audio_dir(self, engine_name: str) -> Path:
        """获取指定引擎的音频目录"""
        engine_dir = self.audio_root / engine_name
        # 🔧 确保目录存在
        engine_dir.mkdir(parents=True, exist_ok=True)
        return engine_dir
    
    def get_engine_subtitles_dir(self, engine_name: str) -> Path:
        """获取指定引擎的字幕目录"""
        return self.subtitles_root / engine_name
    
    def generate_audio_filename(self, engine_name: str, segment_index: int,
                              shot_id: Optional[str] = None, extension: str = "mp3") -> str:
        """
        生成音频文件名
        
        Args:
            engine_name: 引擎名称
            segment_index: 段落索引
            shot_id: 镜头ID（可选）
            extension: 文件扩展名
            
        Returns:
            str: 音频文件名
        """
        # 移除时间戳，使用更简洁的文件名
        if shot_id:
            filename = f"{engine_name}_{segment_index:03d}_{shot_id}.{extension}"
        else:
            filename = f"{engine_name}_{segment_index:03d}.{extension}"
        
        return filename
    
    def save_audio_file(self, engine_name: str, segment_index: int,
                       audio_data: bytes, shot_id: Optional[str] = None,
                       extension: str = "mp3") -> Optional[str]:
        """
        保存音频文件
        
        Args:
            engine_name: 引擎名称
            segment_index: 段落索引
            audio_data: 音频数据
            shot_id: 镜头ID（可选）
            extension: 文件扩展名
            
        Returns:
            Optional[str]: 保存的文件路径，失败返回None
        """
        try:
            # 生成文件名
            filename = self.generate_audio_filename(engine_name, segment_index, shot_id, extension)
            
            # 获取目标目录
            target_dir = self.get_engine_audio_dir(engine_name)
            target_path = target_dir / filename
            
            # 保存文件
            with open(target_path, 'wb') as f:
                f.write(audio_data)
            
            logger.info(f"音频文件已保存: {target_path}")
            return str(target_path)
            
        except Exception as e:
            logger.error(f"保存音频文件失败: {e}")
            return None
    
    def copy_audio_file(self, source_path: str, engine_name: str,
                       segment_index: int, shot_id: Optional[str] = None) -> Optional[str]:
        """
        复制音频文件到项目目录
        
        Args:
            source_path: 源文件路径
            engine_name: 引擎名称
            segment_index: 段落索引
            shot_id: 镜头ID（可选）
            
        Returns:
            Optional[str]: 目标文件路径，失败返回None
        """
        try:
            if not os.path.exists(source_path):
                logger.error(f"源音频文件不存在: {source_path}")
                return None
            
            # 获取文件扩展名
            extension = Path(source_path).suffix.lstrip('.')
            
            # 生成目标文件名
            filename = self.generate_audio_filename(engine_name, segment_index, shot_id, extension)
            
            # 获取目标路径
            target_dir = self.get_engine_audio_dir(engine_name)
            target_path = target_dir / filename
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            logger.info(f"音频文件已复制: {source_path} -> {target_path}")
            return str(target_path)
            
        except Exception as e:
            logger.error(f"复制音频文件失败: {e}")
            return None
    
    def save_subtitle_data(self, engine_name: str, segment_index: int,
                          subtitle_data: List[Dict[str, Any]],
                          shot_id: Optional[str] = None) -> Optional[str]:
        """
        保存字幕数据
        
        Args:
            engine_name: 引擎名称
            segment_index: 段落索引
            subtitle_data: 字幕数据
            shot_id: 镜头ID（可选）
            
        Returns:
            Optional[str]: 字幕文件路径，失败返回None
        """
        try:
            # 生成字幕文件名
            filename = self.generate_audio_filename(engine_name, segment_index, shot_id, "json")
            
            # 获取目标目录
            target_dir = self.get_engine_subtitles_dir(engine_name)
            target_path = target_dir / filename
            
            # 保存字幕数据
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(subtitle_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"字幕数据已保存: {target_path}")
            return str(target_path)
            
        except Exception as e:
            logger.error(f"保存字幕数据失败: {e}")
            return None
    
    def get_audio_files(self, engine_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取音频文件列表
        
        Args:
            engine_name: 引擎名称，为None时返回所有引擎的文件
            
        Returns:
            List[Dict[str, Any]]: 音频文件信息列表
        """
        audio_files = []
        
        try:
            if engine_name:
                engines = [engine_name]
            else:
                engines = ['edge_tts', 'cosyvoice', 'ttsmaker', 'xunfei', 'elevenlabs']
            
            for engine in engines:
                engine_dir = self.get_engine_audio_dir(engine)
                if engine_dir.exists():
                    for audio_file in engine_dir.glob("*.mp3"):
                        file_info = {
                            'engine': engine,
                            'filename': audio_file.name,
                            'path': str(audio_file),
                            'size': audio_file.stat().st_size,
                            'created_time': datetime.fromtimestamp(audio_file.stat().st_ctime).isoformat(),
                            'modified_time': datetime.fromtimestamp(audio_file.stat().st_mtime).isoformat()
                        }
                        audio_files.append(file_info)
            
            return audio_files
            
        except Exception as e:
            logger.error(f"获取音频文件列表失败: {e}")
            return []
    
    def delete_audio_file(self, file_path: str) -> bool:
        """
        删除音频文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 删除是否成功
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"音频文件已删除: {file_path}")
                return True
            else:
                logger.warning(f"音频文件不存在: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"删除音频文件失败: {e}")
            return False
    
    def clear_engine_audio(self, engine_name: str) -> bool:
        """
        清空指定引擎的所有音频文件
        
        Args:
            engine_name: 引擎名称
            
        Returns:
            bool: 清空是否成功
        """
        try:
            engine_dir = self.get_engine_audio_dir(engine_name)
            if engine_dir.exists():
                for audio_file in engine_dir.glob("*"):
                    if audio_file.is_file():
                        audio_file.unlink()
                
                logger.info(f"已清空引擎音频文件: {engine_name}")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"清空引擎音频文件失败: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        获取存储信息
        
        Returns:
            Dict[str, Any]: 存储信息
        """
        try:
            storage_info = {
                'total_files': 0,
                'total_size': 0,
                'engines': {}
            }
            
            engines = ['edge_tts', 'cosyvoice', 'ttsmaker', 'xunfei', 'elevenlabs']
            
            for engine in engines:
                engine_dir = self.get_engine_audio_dir(engine)
                engine_info = {
                    'file_count': 0,
                    'total_size': 0,
                    'files': []
                }
                
                if engine_dir.exists():
                    for audio_file in engine_dir.glob("*"):
                        if audio_file.is_file():
                            file_size = audio_file.stat().st_size
                            engine_info['file_count'] += 1
                            engine_info['total_size'] += file_size
                            engine_info['files'].append({
                                'name': audio_file.name,
                                'size': file_size,
                                'path': str(audio_file)
                            })
                
                storage_info['engines'][engine] = engine_info
                storage_info['total_files'] += engine_info['file_count']
                storage_info['total_size'] += engine_info['total_size']
            
            return storage_info
            
        except Exception as e:
            logger.error(f"获取存储信息失败: {e}")
            return {'total_files': 0, 'total_size': 0, 'engines': {}}
    
    def export_audio_files(self, export_dir: str, engine_name: Optional[str] = None) -> bool:
        """
        导出音频文件
        
        Args:
            export_dir: 导出目录
            engine_name: 引擎名称，为None时导出所有引擎的文件
            
        Returns:
            bool: 导出是否成功
        """
        try:
            export_path = Path(export_dir)
            export_path.mkdir(parents=True, exist_ok=True)
            
            audio_files = self.get_audio_files(engine_name)
            
            for file_info in audio_files:
                source_path = Path(file_info['path'])
                target_path = export_path / f"{file_info['engine']}_{source_path.name}"
                
                shutil.copy2(source_path, target_path)
            
            logger.info(f"音频文件已导出到: {export_dir}")
            return True
            
        except Exception as e:
            logger.error(f"导出音频文件失败: {e}")
            return False
