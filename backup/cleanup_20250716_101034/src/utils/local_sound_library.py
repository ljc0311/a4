#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地音效库管理器
管理本地音效文件，提供音效匹配和复制功能
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import random

from src.utils.logger import logger


class LocalSoundLibrary:
    """本地音效库管理器"""
    
    def __init__(self, output_dir: str, library_dir: Optional[str] = None):
        """
        初始化本地音效库
        
        Args:
            output_dir: 音效文件输出目录
            library_dir: 本地音效库目录（可选）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建音效专用文件夹
        self.sound_effects_dir = self.output_dir / "sound_effects"
        self.sound_effects_dir.mkdir(parents=True, exist_ok=True)
        
        # 本地音效库目录
        if library_dir:
            self.library_dir = Path(library_dir)
        else:
            # 默认使用项目根目录下的sound_library文件夹
            self.library_dir = Path("sound_library")
        
        self.library_dir.mkdir(parents=True, exist_ok=True)
        
        # 音效分类映射
        self.sound_categories = {
            'doorbell': ['门铃', 'doorbell', 'bell', 'chime', 'ring'],
            'footsteps': ['脚步', 'footsteps', 'walking', 'steps', 'walk'],
            'rain': ['雨', 'rain', 'rainfall', 'water', 'drop'],
            'phone': ['电话', 'phone', 'telephone', 'call', 'ring'],
            'button': ['按键', 'button', 'click', 'key', 'press'],
            'crowd': ['人群', 'crowd', 'people', 'talk', 'chatter'],
            'ocean': ['海浪', 'ocean', 'wave', 'sea', 'water'],
            'bird': ['鸟', 'bird', 'chirp', 'tweet', 'sing'],
            'wind': ['风', 'wind', 'breeze', 'air', 'blow'],
            'car': ['汽车', 'car', 'vehicle', 'engine', 'drive'],
            'music': ['音乐', 'music', 'song', 'melody', 'tune']
        }
        
        logger.info(f"本地音效库初始化完成")
        logger.info(f"输出目录: {self.sound_effects_dir}")
        logger.info(f"音效库目录: {self.library_dir}")
        
        # 创建示例音效库结构
        self._create_library_structure()
    
    def _create_library_structure(self):
        """创建音效库目录结构"""
        try:
            for category in self.sound_categories.keys():
                category_dir = self.library_dir / category
                category_dir.mkdir(exist_ok=True)
                
                # 创建README文件说明如何使用
                readme_file = category_dir / "README.txt"
                if not readme_file.exists():
                    with open(readme_file, 'w', encoding='utf-8') as f:
                        f.write(f"请将{category}类型的音效文件放在这个文件夹中\n")
                        f.write(f"支持的格式: .mp3, .wav, .ogg\n")
                        f.write(f"关键词: {', '.join(self.sound_categories[category])}\n")
            
            # 创建总体说明文件
            main_readme = self.library_dir / "README.txt"
            if not main_readme.exists():
                with open(main_readme, 'w', encoding='utf-8') as f:
                    f.write("本地音效库使用说明\n")
                    f.write("=" * 30 + "\n\n")
                    f.write("1. 将音效文件按类型放入对应的文件夹中\n")
                    f.write("2. 支持的音频格式: .mp3, .wav, .ogg\n")
                    f.write("3. 文件名可以包含中文或英文描述\n\n")
                    f.write("音效分类:\n")
                    for category, keywords in self.sound_categories.items():
                        f.write(f"- {category}: {', '.join(keywords)}\n")
                        
        except Exception as e:
            logger.error(f"创建音效库结构失败: {e}")
    
    def search_and_copy_sound(self, query: str, filename: Optional[str] = None) -> Optional[str]:
        """
        搜索并复制本地音效
        
        Args:
            query: 搜索关键词
            filename: 自定义文件名
            
        Returns:
            复制的文件路径，失败返回None
        """
        try:
            logger.info(f"在本地音效库中搜索: {query}")
            
            # 查找匹配的音效文件
            sound_files = self._find_matching_sounds(query)
            
            if sound_files:
                # 随机选择一个音效文件
                selected_file = random.choice(sound_files)
                
                # 生成目标文件名
                if not filename:
                    clean_query = re.sub(r'[^\w\s\u4e00-\u9fff]', '', query)
                    clean_query = re.sub(r'\s+', '_', clean_query).strip('_')
                    file_ext = selected_file.suffix
                    filename = f"{clean_query}_local{file_ext}"
                
                target_path = self.sound_effects_dir / filename
                
                # 复制文件
                shutil.copy2(selected_file, target_path)
                
                logger.info(f"成功复制本地音效: {selected_file} -> {target_path}")
                return str(target_path)
            else:
                logger.warning(f"未找到匹配的本地音效: {query}")
                return None
                
        except Exception as e:
            logger.error(f"搜索本地音效失败: {e}")
            return None
    
    def _find_matching_sounds(self, query: str) -> List[Path]:
        """查找匹配的音效文件"""
        matching_files = []
        
        try:
            # 清理查询词
            clean_query = re.sub(r'[【】\[\]（）()]', '', query).lower()
            
            # 在所有分类中搜索
            for category, keywords in self.sound_categories.items():
                # 检查查询词是否匹配分类关键词
                if any(keyword in clean_query for keyword in keywords):
                    category_dir = self.library_dir / category
                    if category_dir.exists():
                        # 查找音频文件
                        for ext in ['*.mp3', '*.wav', '*.ogg']:
                            matching_files.extend(category_dir.glob(ext))
            
            # 如果没有找到分类匹配，在所有文件中搜索文件名匹配
            if not matching_files:
                for category_dir in self.library_dir.iterdir():
                    if category_dir.is_dir():
                        for audio_file in category_dir.glob('*'):
                            if (audio_file.suffix.lower() in ['.mp3', '.wav', '.ogg'] and
                                any(keyword in audio_file.stem.lower() for keyword in clean_query.split())):
                                matching_files.append(audio_file)
            
            logger.info(f"找到 {len(matching_files)} 个匹配的音效文件")
            return matching_files
            
        except Exception as e:
            logger.error(f"查找匹配音效失败: {e}")
            return []
    
    def list_available_sounds(self) -> Dict[str, List[str]]:
        """列出可用的音效文件"""
        available_sounds = {}
        
        try:
            for category in self.sound_categories.keys():
                category_dir = self.library_dir / category
                if category_dir.exists():
                    sound_files = []
                    for ext in ['*.mp3', '*.wav', '*.ogg']:
                        sound_files.extend([f.name for f in category_dir.glob(ext)])
                    available_sounds[category] = sound_files
            
            return available_sounds
            
        except Exception as e:
            logger.error(f"列出音效文件失败: {e}")
            return {}
    
    def get_library_status(self) -> Dict[str, int]:
        """获取音效库状态"""
        status = {}
        
        try:
            total_files = 0
            for category in self.sound_categories.keys():
                category_dir = self.library_dir / category
                if category_dir.exists():
                    count = 0
                    for ext in ['*.mp3', '*.wav', '*.ogg']:
                        count += len(list(category_dir.glob(ext)))
                    status[category] = count
                    total_files += count
                else:
                    status[category] = 0
            
            status['total'] = total_files
            return status
            
        except Exception as e:
            logger.error(f"获取音效库状态失败: {e}")
            return {'total': 0}
