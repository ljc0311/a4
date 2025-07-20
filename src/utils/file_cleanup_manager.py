#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的文件清理管理器
整合了图像、视频、临时文件等的清理逻辑
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.utils.logger import logger


class FileCleanupManager:
    """统一的文件清理管理器"""
    
    def __init__(self):
        self.cleanup_rules = {
            'images': {
                'extensions': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'],
                'default_days': 7,
                'size_limit_mb': 100  # 单个文件大小限制
            },
            'videos': {
                'extensions': ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'],
                'default_days': 30,
                'size_limit_mb': 500
            },
            'audio': {
                'extensions': ['.wav', '.mp3', '.flac', '.aac', '.ogg'],
                'default_days': 14,
                'size_limit_mb': 50
            },
            'temp': {
                'extensions': ['.tmp', '.temp', '.cache', '.bak', '.old'],
                'default_days': 1,
                'size_limit_mb': 10
            },
            'logs': {
                'extensions': ['.log'],
                'default_days': 7,
                'size_limit_mb': 10
            }
        }
    
    def cleanup_old_files(self, directory: Path, file_type: str = 'images', 
                         days: Optional[int] = None, dry_run: bool = False) -> Dict[str, Any]:
        """清理旧文件
        
        Args:
            directory: 要清理的目录
            file_type: 文件类型 ('images', 'videos', 'audio', 'temp', 'logs')
            days: 保留天数，None使用默认值
            dry_run: 是否只是预览，不实际删除
            
        Returns:
            Dict: 清理结果统计
        """
        if file_type not in self.cleanup_rules:
            raise ValueError(f"不支持的文件类型: {file_type}")
        
        rules = self.cleanup_rules[file_type]
        days = days or rules['default_days']
        extensions = rules['extensions']
        
        logger.info(f"开始清理 {directory} 中的 {file_type} 文件（{days}天前）")
        
        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)
        
        stats = {
            'scanned': 0,
            'deleted': 0,
            'total_size_mb': 0,
            'freed_size_mb': 0,
            'errors': []
        }
        
        try:
            if not directory.exists():
                logger.warning(f"目录不存在: {directory}")
                return stats
            
            # 扫描文件
            for ext in extensions:
                pattern = f"**/*{ext}"
                for file_path in directory.rglob(pattern):
                    stats['scanned'] += 1
                    
                    try:
                        file_stat = file_path.stat()
                        file_size_mb = file_stat.st_size / (1024 * 1024)
                        stats['total_size_mb'] += file_size_mb
                        
                        # 检查文件年龄
                        if file_stat.st_mtime < cutoff_time:
                            if dry_run:
                                logger.info(f"[预览] 将删除: {file_path} ({file_size_mb:.2f}MB)")
                            else:
                                file_path.unlink()
                                logger.debug(f"已删除: {file_path}")
                            
                            stats['deleted'] += 1
                            stats['freed_size_mb'] += file_size_mb
                            
                    except Exception as e:
                        error_msg = f"处理文件失败 {file_path}: {e}"
                        logger.error(error_msg)
                        stats['errors'].append(error_msg)
            
            # 记录清理结果
            if dry_run:
                logger.info(f"[预览] {file_type} 清理统计: 扫描 {stats['scanned']} 个文件，"
                          f"将删除 {stats['deleted']} 个文件，释放 {stats['freed_size_mb']:.2f}MB")
            else:
                logger.info(f"{file_type} 清理完成: 扫描 {stats['scanned']} 个文件，"
                          f"删除 {stats['deleted']} 个文件，释放 {stats['freed_size_mb']:.2f}MB")
            
        except Exception as e:
            error_msg = f"清理过程中发生错误: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats
    
    def cleanup_large_files(self, directory: Path, file_type: str = 'images',
                           size_limit_mb: Optional[float] = None, dry_run: bool = False) -> Dict[str, Any]:
        """清理超大文件
        
        Args:
            directory: 要清理的目录
            file_type: 文件类型
            size_limit_mb: 大小限制（MB），None使用默认值
            dry_run: 是否只是预览
            
        Returns:
            Dict: 清理结果统计
        """
        if file_type not in self.cleanup_rules:
            raise ValueError(f"不支持的文件类型: {file_type}")
        
        rules = self.cleanup_rules[file_type]
        size_limit_mb = size_limit_mb or rules['size_limit_mb']
        size_limit_bytes = size_limit_mb * 1024 * 1024
        extensions = rules['extensions']
        
        logger.info(f"开始清理 {directory} 中超过 {size_limit_mb}MB 的 {file_type} 文件")
        
        stats = {
            'scanned': 0,
            'deleted': 0,
            'total_size_mb': 0,
            'freed_size_mb': 0,
            'errors': []
        }
        
        try:
            if not directory.exists():
                logger.warning(f"目录不存在: {directory}")
                return stats
            
            # 扫描文件
            for ext in extensions:
                pattern = f"**/*{ext}"
                for file_path in directory.rglob(pattern):
                    stats['scanned'] += 1
                    
                    try:
                        file_size = file_path.stat().st_size
                        file_size_mb = file_size / (1024 * 1024)
                        stats['total_size_mb'] += file_size_mb
                        
                        # 检查文件大小
                        if file_size > size_limit_bytes:
                            if dry_run:
                                logger.info(f"[预览] 将删除超大文件: {file_path} ({file_size_mb:.2f}MB)")
                            else:
                                file_path.unlink()
                                logger.debug(f"已删除超大文件: {file_path}")
                            
                            stats['deleted'] += 1
                            stats['freed_size_mb'] += file_size_mb
                            
                    except Exception as e:
                        error_msg = f"处理文件失败 {file_path}: {e}"
                        logger.error(error_msg)
                        stats['errors'].append(error_msg)
            
            # 记录清理结果
            if dry_run:
                logger.info(f"[预览] 超大{file_type}文件清理统计: 扫描 {stats['scanned']} 个文件，"
                          f"将删除 {stats['deleted']} 个文件，释放 {stats['freed_size_mb']:.2f}MB")
            else:
                logger.info(f"超大{file_type}文件清理完成: 扫描 {stats['scanned']} 个文件，"
                          f"删除 {stats['deleted']} 个文件，释放 {stats['freed_size_mb']:.2f}MB")
            
        except Exception as e:
            error_msg = f"清理过程中发生错误: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats
    
    def cleanup_empty_directories(self, directory: Path, dry_run: bool = False) -> Dict[str, Any]:
        """清理空目录
        
        Args:
            directory: 要清理的根目录
            dry_run: 是否只是预览
            
        Returns:
            Dict: 清理结果统计
        """
        logger.info(f"开始清理 {directory} 中的空目录")
        
        stats = {
            'scanned': 0,
            'deleted': 0,
            'errors': []
        }
        
        try:
            if not directory.exists():
                logger.warning(f"目录不存在: {directory}")
                return stats
            
            # 从最深层开始清理，避免删除父目录后子目录无法访问
            for dir_path in sorted(directory.rglob('*'), key=lambda p: len(p.parts), reverse=True):
                if dir_path.is_dir():
                    stats['scanned'] += 1
                    
                    try:
                        # 检查目录是否为空
                        if not any(dir_path.iterdir()):
                            if dry_run:
                                logger.info(f"[预览] 将删除空目录: {dir_path}")
                            else:
                                dir_path.rmdir()
                                logger.debug(f"已删除空目录: {dir_path}")
                            
                            stats['deleted'] += 1
                            
                    except Exception as e:
                        error_msg = f"处理目录失败 {dir_path}: {e}"
                        logger.error(error_msg)
                        stats['errors'].append(error_msg)
            
            # 记录清理结果
            if dry_run:
                logger.info(f"[预览] 空目录清理统计: 扫描 {stats['scanned']} 个目录，"
                          f"将删除 {stats['deleted']} 个空目录")
            else:
                logger.info(f"空目录清理完成: 扫描 {stats['scanned']} 个目录，"
                          f"删除 {stats['deleted']} 个空目录")
            
        except Exception as e:
            error_msg = f"清理过程中发生错误: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats
    
    def full_cleanup(self, base_directory: Path, dry_run: bool = False) -> Dict[str, Any]:
        """执行完整清理
        
        Args:
            base_directory: 基础目录
            dry_run: 是否只是预览
            
        Returns:
            Dict: 完整清理结果统计
        """
        logger.info(f"开始执行完整清理: {base_directory}")
        
        full_stats = {
            'total_scanned': 0,
            'total_deleted': 0,
            'total_freed_mb': 0,
            'by_type': {},
            'errors': []
        }
        
        # 清理各种类型的文件
        for file_type in self.cleanup_rules.keys():
            try:
                stats = self.cleanup_old_files(base_directory, file_type, dry_run=dry_run)
                full_stats['by_type'][file_type] = stats
                full_stats['total_scanned'] += stats['scanned']
                full_stats['total_deleted'] += stats['deleted']
                full_stats['total_freed_mb'] += stats['freed_size_mb']
                full_stats['errors'].extend(stats['errors'])
            except Exception as e:
                error_msg = f"清理 {file_type} 文件失败: {e}"
                logger.error(error_msg)
                full_stats['errors'].append(error_msg)
        
        # 清理空目录
        try:
            empty_dir_stats = self.cleanup_empty_directories(base_directory, dry_run=dry_run)
            full_stats['empty_directories'] = empty_dir_stats
            full_stats['errors'].extend(empty_dir_stats['errors'])
        except Exception as e:
            error_msg = f"清理空目录失败: {e}"
            logger.error(error_msg)
            full_stats['errors'].append(error_msg)
        
        # 记录总体结果
        if dry_run:
            logger.info(f"[预览] 完整清理统计: 扫描 {full_stats['total_scanned']} 个文件，"
                      f"将删除 {full_stats['total_deleted']} 个文件，"
                      f"释放 {full_stats['total_freed_mb']:.2f}MB")
        else:
            logger.info(f"完整清理完成: 扫描 {full_stats['total_scanned']} 个文件，"
                      f"删除 {full_stats['total_deleted']} 个文件，"
                      f"释放 {full_stats['total_freed_mb']:.2f}MB")
        
        return full_stats


# 全局清理管理器实例
file_cleanup_manager = FileCleanupManager()

# 便捷函数
def cleanup_old_images(directory: Path, days: int = 7, dry_run: bool = False):
    """清理旧图像文件"""
    return file_cleanup_manager.cleanup_old_files(directory, 'images', days, dry_run)

def cleanup_old_videos(directory: Path, days: int = 30, dry_run: bool = False):
    """清理旧视频文件"""
    return file_cleanup_manager.cleanup_old_files(directory, 'videos', days, dry_run)

def cleanup_temp_files(directory: Path, days: int = 1, dry_run: bool = False):
    """清理临时文件"""
    return file_cleanup_manager.cleanup_old_files(directory, 'temp', days, dry_run)

def full_cleanup(directory: Path, dry_run: bool = False):
    """执行完整清理"""
    return file_cleanup_manager.full_cleanup(directory, dry_run)
