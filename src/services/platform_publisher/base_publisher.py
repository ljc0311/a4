#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布器基类和相关数据结构
定义了所有发布器共用的基础类和数据类型
"""

import os
import time
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class VideoMetadata:
    """视频元数据"""
    title: str
    description: str
    tags: List[str] = field(default_factory=list)
    cover_path: Optional[str] = None
    category: Optional[str] = None
    privacy: str = "public"  # public, private, unlisted
    allow_comments: bool = True
    allow_ratings: bool = True
    language: str = "zh-CN"
    location: Optional[str] = None
    recording_date: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    platform: Optional[str] = None
    upload_time: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class PublisherBase(ABC):
    """发布器基类"""
    
    def __init__(self, platform_name: str, config: Dict[str, Any]):
        self.platform_name = platform_name
        self.config = config
        self.is_authenticated = False
        
    @abstractmethod
    def authenticate(self) -> bool:
        """认证登录"""
        pass
        
    @abstractmethod
    def publish_video(self, video_path: str, metadata: VideoMetadata) -> Dict[str, Any]:
        """发布视频"""
        pass
        
    @abstractmethod
    def check_status(self, video_id: str) -> Dict[str, Any]:
        """检查视频状态"""
        pass
        
    @abstractmethod
    def close(self) -> None:
        """关闭发布器"""
        pass
        
    def save_credentials(self, credentials: Dict[str, Any]) -> bool:
        """保存凭证"""
        try:
            # 创建凭证目录
            credentials_dir = os.path.join(os.path.expanduser("~"), ".ai_video_generator", "credentials")
            os.makedirs(credentials_dir, exist_ok=True)
            
            # 保存凭证文件
            credentials_file = os.path.join(credentials_dir, f"{self.platform_name}.json")
            with open(credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"保存凭证失败: {e}")
            return False
            
    def load_credentials(self) -> Optional[Dict[str, Any]]:
        """加载凭证"""
        try:
            # 获取凭证文件路径
            credentials_file = os.path.join(
                os.path.expanduser("~"), 
                ".ai_video_generator", 
                "credentials", 
                f"{self.platform_name}.json"
            )
            
            # 检查文件是否存在
            if not os.path.exists(credentials_file):
                return None
                
            # 加载凭证
            with open(credentials_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"加载凭证失败: {e}")
            return None
