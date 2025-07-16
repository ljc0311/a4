# -*- coding: utf-8 -*-
"""
发布器数据模型
定义数据库表结构和数据模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class PlatformAccount(Base):
    """平台账号表"""
    __tablename__ = 'platform_accounts'
    
    id = Column(Integer, primary_key=True)
    platform_name = Column(String(50), nullable=False)  # bilibili, douyin, kuaishou等
    account_name = Column(String(100), nullable=False)  # 账号显示名称
    account_id = Column(String(100))  # 平台账号ID
    credentials = Column(Text)  # 加密后的认证信息(cookies/tokens)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联发布记录
    publish_records = relationship("PublishRecord", back_populates="account")

class VideoTask(Base):
    """视频任务表"""
    __tablename__ = 'video_tasks'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    project_name = Column(String(200))  # 关联的项目名称
    video_path = Column(String(500), nullable=False)  # 原始视频路径
    title = Column(String(200), nullable=False)
    description = Column(Text)
    tags = Column(JSON)  # 标签列表
    cover_path = Column(String(500))  # 封面图片路径
    
    # 发布配置
    target_platforms = Column(JSON)  # 目标平台列表
    schedule_time = Column(DateTime)  # 定时发布时间
    priority = Column(Integer, default=0)  # 任务优先级
    
    # 任务状态
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    progress = Column(Float, default=0.0)  # 任务进度 0.0-1.0
    error_message = Column(Text)  # 错误信息
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # 关联发布记录
    publish_records = relationship("PublishRecord", back_populates="task")

class PublishRecord(Base):
    """发布记录表"""
    __tablename__ = 'publish_records'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(100), ForeignKey('video_tasks.task_id'), nullable=False)
    account_id = Column(Integer, ForeignKey('platform_accounts.id'), nullable=False)
    
    # 平台信息
    platform_name = Column(String(50), nullable=False)
    platform_video_id = Column(String(200))  # 平台返回的视频ID
    platform_video_url = Column(String(500))  # 平台视频链接
    
    # 发布内容
    published_title = Column(String(200))
    published_description = Column(Text)
    published_tags = Column(JSON)
    converted_video_path = Column(String(500))  # 转换后的视频路径
    
    # 发布状态
    status = Column(String(50), nullable=False)  # uploading, published, failed
    error_message = Column(Text)
    publish_time = Column(DateTime)
    
    # 统计数据（可选，用于后续分析）
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    
    # 原始响应数据
    raw_response = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    task = relationship("VideoTask", back_populates="publish_records")
    account = relationship("PlatformAccount", back_populates="publish_records")

class PublishTemplate(Base):
    """发布模板表"""
    __tablename__ = 'publish_templates'
    
    id = Column(Integer, primary_key=True)
    template_name = Column(String(100), nullable=False)
    platform_name = Column(String(50), nullable=False)
    
    # 模板内容
    title_template = Column(String(200))  # 标题模板，支持变量替换
    description_template = Column(Text)   # 描述模板
    default_tags = Column(JSON)           # 默认标签
    category = Column(String(100))        # 分类
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PublishSchedule(Base):
    """发布计划表"""
    __tablename__ = 'publish_schedules'
    
    id = Column(Integer, primary_key=True)
    schedule_name = Column(String(100), nullable=False)
    
    # 计划配置
    platforms = Column(JSON)  # 平台列表
    schedule_type = Column(String(50))  # immediate, scheduled, recurring
    schedule_time = Column(DateTime)    # 计划时间
    recurring_pattern = Column(String(100))  # 重复模式：daily, weekly, monthly
    
    # 内容优化配置
    auto_optimize_title = Column(Boolean, default=True)
    auto_optimize_description = Column(Boolean, default=True)
    auto_generate_tags = Column(Boolean, default=True)
    auto_extract_cover = Column(Boolean, default=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ConversionRecord(Base):
    """视频转换记录表"""
    __tablename__ = 'conversion_records'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(100), ForeignKey('video_tasks.task_id'), nullable=False)
    platform_name = Column(String(50), nullable=False)
    
    # 转换信息
    input_path = Column(String(500), nullable=False)
    output_path = Column(String(500))
    conversion_status = Column(String(50), default='pending')  # pending, processing, completed, failed
    
    # 转换参数
    target_resolution = Column(String(20))
    target_fps = Column(Integer)
    target_bitrate = Column(String(10))
    target_format = Column(String(10))
    
    # 文件信息
    original_size = Column(Integer)  # 字节
    converted_size = Column(Integer)  # 字节
    conversion_time = Column(Float)  # 转换耗时（秒）
    
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 数据模型的辅助类
class TaskStatus:
    """任务状态常量"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    CONVERTING = 'converting'
    UPLOADING = 'uploading'
    PUBLISHING = 'publishing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class PublishStatus:
    """发布状态常量"""
    PENDING = 'pending'
    UPLOADING = 'uploading'
    PROCESSING = 'processing'
    PUBLISHED = 'published'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class ConversionStatus:
    """转换状态常量"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
