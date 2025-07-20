#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube平台特征性优化器
针对YouTube平台的特殊需求进行内容优化
"""

import os
import re
import cv2
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.utils.logger import logger

class YouTubePlatformOptimizer:
    """YouTube平台特征性优化器"""
    
    def __init__(self):
        # YouTube平台特征配置
        self.youtube_config = {
            # 内容限制
            'title_max_length': 100,
            'description_max_length': 5000,
            'tags_max_count': 15,
            
            # Shorts配置
            'shorts_max_duration': 60,  # 秒
            'shorts_aspect_ratio': (9, 16),  # 竖屏
            'shorts_min_resolution': (720, 1280),
            
            # 长视频配置
            'long_video_min_duration': 61,  # 秒
            'long_video_aspect_ratio': (16, 9),  # 横屏
            'long_video_min_resolution': (1280, 720),
            
            # SEO优化
            'trending_keywords': [
                'AI', '人工智能', 'Technology', '科技', 'Tutorial', '教程',
                'Review', '评测', 'Tips', '技巧', 'Guide', '指南',
                'News', '新闻', 'Update', '更新', 'Latest', '最新'
            ],
            
            # 标签优化
            'popular_tags': [
                'AI', 'Technology', 'Tutorial', 'Education', 'Science',
                'Innovation', 'Future', 'Digital', 'Tech', 'Learning'
            ]
        }
    
    def optimize_video_info(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化视频信息以适应YouTube平台
        
        Args:
            video_info: 原始视频信息
            
        Returns:
            优化后的视频信息
        """
        try:
            logger.info("🎬 开始YouTube平台特征性优化...")
            
            optimized_info = video_info.copy()
            
            # 1. 检测视频类型（Shorts vs 长视频）
            video_type = self._detect_video_type(video_info.get('video_path', ''))
            optimized_info['video_type'] = video_type
            
            # 2. 优化标题
            optimized_info['title'] = self._optimize_title(
                video_info.get('title', ''), video_type
            )
            
            # 3. 优化描述
            optimized_info['description'] = self._optimize_description(
                video_info.get('description', ''), video_type
            )
            
            # 4. 优化标签
            optimized_info['tags'] = self._optimize_tags(
                video_info.get('tags', []), video_type
            )
            
            # 5. 设置隐私级别
            optimized_info['privacy'] = self._determine_privacy_level(video_info)
            
            # 6. 设置分类
            optimized_info['category'] = self._determine_category(video_info)
            
            # 7. 添加YouTube特定配置
            optimized_info['youtube_specific'] = self._get_youtube_specific_config(video_type)
            
            logger.info(f"✅ YouTube优化完成，视频类型: {video_type}")
            return optimized_info
            
        except Exception as e:
            logger.error(f"❌ YouTube优化失败: {e}")
            return video_info
    
    def _detect_video_type(self, video_path: str) -> str:
        """检测视频类型（Shorts或长视频）"""
        try:
            if not video_path or not os.path.exists(video_path):
                return 'unknown'
            
            # 获取视频信息
            cap = cv2.VideoCapture(video_path)
            
            # 获取时长
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            duration = frame_count / fps if fps > 0 else 0
            
            # 获取分辨率
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            cap.release()
            
            # 判断是否为Shorts
            is_short_duration = duration <= self.youtube_config['shorts_max_duration']
            is_vertical = height > width  # 竖屏
            
            if is_short_duration and is_vertical:
                return 'shorts'
            elif is_short_duration:
                return 'short_horizontal'  # 短横屏视频
            else:
                return 'long_video'
                
        except Exception as e:
            logger.warning(f"检测视频类型失败: {e}")
            return 'unknown'
    
    def _optimize_title(self, title: str, video_type: str) -> str:
        """优化标题"""
        try:
            if not title:
                title = "AI生成视频"
            
            # 限制长度
            max_length = self.youtube_config['title_max_length']
            
            # 根据视频类型添加特定标识
            if video_type == 'shorts':
                if '#Shorts' not in title:
                    # 为Shorts添加标识，但要考虑长度限制
                    shorts_suffix = ' #Shorts'
                    if len(title) + len(shorts_suffix) <= max_length:
                        title += shorts_suffix
                    else:
                        # 截断标题以容纳#Shorts
                        title = title[:max_length - len(shorts_suffix)] + shorts_suffix
            
            # 添加吸引人的元素
            title = self._add_engaging_elements(title, video_type)
            
            # 最终长度检查
            if len(title) > max_length:
                title = title[:max_length-3] + '...'
            
            return title
            
        except Exception as e:
            logger.warning(f"优化标题失败: {e}")
            return title[:self.youtube_config['title_max_length']]
    
    def _optimize_description(self, description: str, video_type: str) -> str:
        """优化描述"""
        try:
            if not description:
                description = "这是一个AI生成的精彩视频内容。"
            
            # 构建优化的描述
            optimized_desc = description
            
            # 为Shorts添加特殊描述
            if video_type == 'shorts':
                if '#Shorts' not in optimized_desc:
                    optimized_desc += '\n\n#Shorts'
            
            # 添加标准的YouTube描述模板
            template_addition = self._get_description_template(video_type)
            
            # 合并描述
            full_description = f"{optimized_desc}\n\n{template_addition}"
            
            # 限制长度
            max_length = self.youtube_config['description_max_length']
            if len(full_description) > max_length:
                # 保留原描述，截断模板部分
                available_space = max_length - len(optimized_desc) - 4  # 留出换行空间
                if available_space > 0:
                    truncated_template = template_addition[:available_space] + '...'
                    full_description = f"{optimized_desc}\n\n{truncated_template}"
                else:
                    full_description = optimized_desc[:max_length]
            
            return full_description
            
        except Exception as e:
            logger.warning(f"优化描述失败: {e}")
            return description[:self.youtube_config['description_max_length']]
    
    def _optimize_tags(self, tags: List[str], video_type: str) -> List[str]:
        """优化标签"""
        try:
            optimized_tags = list(tags) if tags else []
            
            # 添加视频类型相关标签
            if video_type == 'shorts':
                type_tags = ['Shorts', 'Short', 'Viral', 'Quick']
            else:
                type_tags = ['Video', 'Content', 'Full']
            
            # 添加平台推荐标签
            recommended_tags = self.youtube_config['popular_tags']
            
            # 合并标签
            all_tags = optimized_tags + type_tags + recommended_tags
            
            # 去重并限制数量
            unique_tags = list(dict.fromkeys(all_tags))  # 保持顺序的去重
            max_tags = self.youtube_config['tags_max_count']
            
            return unique_tags[:max_tags]
            
        except Exception as e:
            logger.warning(f"优化标签失败: {e}")
            return tags[:self.youtube_config['tags_max_count']] if tags else []
    
    def _determine_privacy_level(self, video_info: Dict[str, Any]) -> str:
        """确定隐私级别"""
        # 默认为公开，用户可以在配置中覆盖
        return video_info.get('privacy', 'public')
    
    def _determine_category(self, video_info: Dict[str, Any]) -> str:
        """确定视频分类"""
        # 根据内容智能判断分类
        title = video_info.get('title', '').lower()
        description = video_info.get('description', '').lower()
        content = f"{title} {description}"
        
        # 分类映射
        category_keywords = {
            '28': ['tech', 'technology', 'ai', '科技', '技术', '人工智能'],  # Science & Technology
            '27': ['tutorial', 'education', 'learn', '教程', '教育', '学习'],  # Education
            '24': ['entertainment', 'fun', 'funny', '娱乐', '搞笑'],  # Entertainment
            '22': ['blog', 'vlog', 'life', '生活', '日常'],  # People & Blogs
            '10': ['music', 'song', 'audio', '音乐', '歌曲'],  # Music
        }
        
        for category_id, keywords in category_keywords.items():
            if any(keyword in content for keyword in keywords):
                return category_id
        
        # 默认分类：Science & Technology
        return '28'
    
    def _add_engaging_elements(self, title: str, video_type: str) -> str:
        """添加吸引人的元素"""
        try:
            # 为不同类型的视频添加不同的吸引元素
            if video_type == 'shorts':
                engaging_prefixes = ['🔥', '⚡', '🎯', '💥', '🚀']
            else:
                engaging_prefixes = ['🎬', '📺', '🎥', '✨', '🌟']
            
            # 如果标题还没有emoji，添加一个
            if not any(char in title for char in '🔥⚡🎯💥🚀🎬📺🎥✨🌟'):
                import random
                prefix = random.choice(engaging_prefixes)
                title = f"{prefix} {title}"
            
            return title
            
        except Exception as e:
            logger.warning(f"添加吸引元素失败: {e}")
            return title
    
    def _get_description_template(self, video_type: str) -> str:
        """获取描述模板"""
        if video_type == 'shorts':
            return """🎬 精彩短视频内容

🔔 订阅频道获取更多内容
👍 点赞支持创作
💬 评论分享您的想法

#Shorts #Video #Content"""
        else:
            return """🎬 精彩视频内容

📖 视频亮点：
• AI技术驱动的内容创作
• 高质量的视觉效果
• 引人入胜的故事情节

🔔 订阅频道获取更多AI创作内容
👍 点赞支持我们的创作
💬 评论分享您的想法
🔗 分享给更多朋友

#AI #Technology #Innovation #Content #Video"""
    
    def _get_youtube_specific_config(self, video_type: str) -> Dict[str, Any]:
        """获取YouTube特定配置"""
        config = {
            'made_for_kids': False,
            'embeddable': True,
            'public_stats_viewable': True,
            'category_id': '28',  # Science & Technology
        }
        
        if video_type == 'shorts':
            config.update({
                'is_shorts': True,
                'shorts_optimized': True,
                'vertical_video': True
            })
        
        return config

# 全局优化器实例
youtube_optimizer = YouTubePlatformOptimizer()
