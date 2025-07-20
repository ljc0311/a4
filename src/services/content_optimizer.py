# -*- coding: utf-8 -*-
"""
内容AI优化服务
集成现有LLM服务实现标题生成、描述优化、标签推荐等AI内容优化功能
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from src.services.llm_service import LLMService
from src.utils.logger import logger

@dataclass
class OptimizedContent:
    """优化后的内容"""
    title: str
    description: str
    tags: List[str]
    hashtags: List[str]
    keywords: List[str]
    platform_specific: Dict[str, Dict[str, Any]]  # 平台特定优化

class ContentOptimizer:
    """内容AI优化服务"""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        
        # 平台特定配置
        self.platform_configs = {
            'douyin': {
                'title_max_length': 55,
                'description_max_length': 2200,
                'max_tags': 10,
                'trending_topics': ['热门', '推荐', '生活', '美食', '旅行', '科技', '娱乐'],
                'style': '年轻化、活泼、有趣'
            },
            'kuaishou': {
                'title_max_length': 50,
                'description_max_length': 2200,
                'max_tags': 10,
                'trending_topics': ['生活', '搞笑', '美食', '农村', '技能', '情感'],
                'style': '真实、接地气、温暖'
            },
            'xiaohongshu': {
                'title_max_length': 100,
                'description_max_length': 1000,
                'max_tags': 20,
                'trending_topics': ['种草', '好物推荐', '生活方式', '美妆', '穿搭', '旅行'],
                'style': '精致、分享、种草'
            },
            'bilibili': {
                'title_max_length': 80,
                'description_max_length': 2000,
                'max_tags': 12,
                'trending_topics': ['科技', '游戏', '动漫', '知识', '生活', '娱乐'],
                'style': '专业、有趣、有深度'
            },
            'wechat_channels': {
                'title_max_length': 64,
                'description_max_length': 600,
                'max_tags': 8,
                'trending_topics': ['生活', '分享', '正能量', '实用', '温暖'],
                'style': '温和、正面、有价值'
            },
            'youtube': {
                'title_max_length': 100,
                'description_max_length': 5000,
                'max_tags': 15,
                'trending_topics': ['trending', 'viral', 'popular', 'amazing', 'must-watch'],
                'style': '国际化、吸引眼球、SEO友好'
            }
        }
        
        logger.info("内容AI优化服务初始化完成")
        
    async def optimize_content(self, 
                             original_title: str = "",
                             original_description: str = "",
                             video_content_summary: str = "",
                             target_platforms: List[str] = None,
                             target_audience: str = "大众",
                             content_type: str = "娱乐") -> OptimizedContent:
        """
        优化内容
        
        Args:
            original_title: 原始标题
            original_description: 原始描述
            video_content_summary: 视频内容摘要
            target_platforms: 目标平台列表
            target_audience: 目标受众
            content_type: 内容类型
        """
        try:
            logger.info("开始AI内容优化...")
            
            # 如果没有指定平台，使用所有平台
            if not target_platforms:
                target_platforms = list(self.platform_configs.keys())
                
            # 生成基础优化内容
            base_content = await self._generate_base_content(
                original_title, original_description, video_content_summary,
                target_audience, content_type
            )
            
            # 为每个平台生成特定优化
            platform_specific = {}
            for platform in target_platforms:
                platform_content = await self._optimize_for_platform(
                    base_content, platform, target_audience, content_type
                )
                platform_specific[platform] = platform_content
                
            # 生成通用标签和关键词
            tags, hashtags, keywords = await self._generate_tags_and_keywords(
                base_content['title'], base_content['description'], 
                video_content_summary, target_platforms
            )
            
            result = OptimizedContent(
                title=base_content['title'],
                description=base_content['description'],
                tags=tags,
                hashtags=hashtags,
                keywords=keywords,
                platform_specific=platform_specific
            )
            
            logger.info("AI内容优化完成")
            return result
            
        except Exception as e:
            logger.error(f"内容优化失败: {e}")
            # 返回基础内容作为备选
            return OptimizedContent(
                title=original_title or "精彩视频",
                description=original_description or "分享精彩内容",
                tags=["视频", "分享"],
                hashtags=["#视频", "#分享"],
                keywords=["视频", "内容"],
                platform_specific={}
            )
            
    async def _generate_base_content(self, 
                                   original_title: str,
                                   original_description: str,
                                   video_summary: str,
                                   target_audience: str,
                                   content_type: str) -> Dict[str, str]:
        """生成基础优化内容"""
        try:
            prompt = f"""
作为一个专业的短视频内容优化专家，请帮我优化以下视频内容：

原始信息：
- 原始标题：{original_title}
- 原始描述：{original_description}
- 视频内容摘要：{video_summary}
- 目标受众：{target_audience}
- 内容类型：{content_type}

请生成：
1. 一个吸引人的标题（50字以内）
2. 一个详细的描述（200字以内）

要求：
- 标题要有吸引力，能激发用户点击欲望
- 描述要详细介绍视频内容，包含关键信息
- 语言要符合短视频平台的风格
- 考虑SEO优化，包含相关关键词

请以JSON格式返回：
{{
    "title": "优化后的标题",
    "description": "优化后的描述"
}}
"""

            response = await self.llm_service.generate_response(prompt)
            
            # 解析JSON响应
            try:
                content = json.loads(response)
                return {
                    'title': content.get('title', original_title or '精彩视频'),
                    'description': content.get('description', original_description or '分享精彩内容')
                }
            except json.JSONDecodeError:
                # 如果JSON解析失败，尝试提取内容
                title_match = re.search(r'"title":\s*"([^"]*)"', response)
                desc_match = re.search(r'"description":\s*"([^"]*)"', response)
                
                return {
                    'title': title_match.group(1) if title_match else (original_title or '精彩视频'),
                    'description': desc_match.group(1) if desc_match else (original_description or '分享精彩内容')
                }
                
        except Exception as e:
            logger.error(f"生成基础内容失败: {e}")
            return {
                'title': original_title or '精彩视频',
                'description': original_description or '分享精彩内容'
            }
            
    async def _optimize_for_platform(self, 
                                   base_content: Dict[str, str],
                                   platform: str,
                                   target_audience: str,
                                   content_type: str) -> Dict[str, Any]:
        """为特定平台优化内容"""
        try:
            config = self.platform_configs.get(platform, {})
            
            prompt = f"""
请为{platform}平台优化以下内容：

基础内容：
- 标题：{base_content['title']}
- 描述：{base_content['description']}

平台特点：
- 标题最大长度：{config.get('title_max_length', 50)}字符
- 描述最大长度：{config.get('description_max_length', 1000)}字符
- 平台风格：{config.get('style', '通用')}
- 热门话题：{', '.join(config.get('trending_topics', []))}

请优化并返回JSON格式：
{{
    "title": "适合{platform}的标题",
    "description": "适合{platform}的描述",
    "suggested_hashtags": ["#标签1", "#标签2"],
    "optimization_tips": "优化建议"
}}
"""

            response = await self.llm_service.generate_response(prompt)
            
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # 备选解析
                return {
                    'title': base_content['title'][:config.get('title_max_length', 50)],
                    'description': base_content['description'][:config.get('description_max_length', 1000)],
                    'suggested_hashtags': [f"#{tag}" for tag in config.get('trending_topics', [])[:3]],
                    'optimization_tips': f"已针对{platform}平台进行基础优化"
                }
                
        except Exception as e:
            logger.error(f"平台优化失败 {platform}: {e}")
            config = self.platform_configs.get(platform, {})
            return {
                'title': base_content['title'][:config.get('title_max_length', 50)],
                'description': base_content['description'][:config.get('description_max_length', 1000)],
                'suggested_hashtags': [],
                'optimization_tips': "使用基础优化"
            }
            
    async def _generate_tags_and_keywords(self, 
                                        title: str,
                                        description: str,
                                        video_summary: str,
                                        platforms: List[str]) -> Tuple[List[str], List[str], List[str]]:
        """生成标签和关键词"""
        try:
            prompt = f"""
基于以下内容生成相关的标签和关键词：

标题：{title}
描述：{description}
视频摘要：{video_summary}
目标平台：{', '.join(platforms)}

请生成：
1. 10个相关标签（不带#号）
2. 10个话题标签（带#号）
3. 15个SEO关键词

要求：
- 标签要准确反映视频内容
- 话题标签要热门且相关
- 关键词要有利于搜索发现

请以JSON格式返回：
{{
    "tags": ["标签1", "标签2", ...],
    "hashtags": ["#话题1", "#话题2", ...],
    "keywords": ["关键词1", "关键词2", ...]
}}
"""

            response = await self.llm_service.generate_response(prompt)
            
            try:
                result = json.loads(response)
                return (
                    result.get('tags', [])[:10],
                    result.get('hashtags', [])[:10],
                    result.get('keywords', [])[:15]
                )
            except json.JSONDecodeError:
                # 备选方案：从内容中提取关键词
                return self._extract_keywords_fallback(title, description, video_summary)
                
        except Exception as e:
            logger.error(f"生成标签和关键词失败: {e}")
            return self._extract_keywords_fallback(title, description, video_summary)
            
    def _extract_keywords_fallback(self, title: str, description: str, summary: str) -> Tuple[List[str], List[str], List[str]]:
        """备选关键词提取方法"""
        # 简单的关键词提取
        text = f"{title} {description} {summary}".lower()
        
        # 常见标签
        common_tags = ["视频", "分享", "生活", "有趣", "精彩", "推荐"]
        
        # 常见话题标签
        common_hashtags = ["#视频", "#分享", "#生活", "#推荐", "#精彩"]
        
        # 从文本中提取的关键词
        words = re.findall(r'\b\w+\b', text)
        keywords = list(set(words))[:10] + common_tags
        
        return common_tags, common_hashtags, keywords[:15]
        
    async def generate_title_suggestions(self, 
                                       video_summary: str,
                                       platform: str = "通用",
                                       count: int = 5) -> List[str]:
        """生成标题建议"""
        try:
            config = self.platform_configs.get(platform, {})
            max_length = config.get('title_max_length', 50)
            style = config.get('style', '通用')
            
            prompt = f"""
基于以下视频内容，为{platform}平台生成{count}个吸引人的标题：

视频内容：{video_summary}
平台风格：{style}
标题长度限制：{max_length}字符

要求：
- 标题要有吸引力，能激发点击欲望
- 符合平台风格和用户习惯
- 包含关键信息和关键词
- 长度控制在限制范围内

请返回{count}个标题，每行一个。
"""

            response = await self.llm_service.generate_response(prompt)
            
            # 解析标题列表
            titles = [line.strip() for line in response.split('\n') if line.strip()]
            
            # 过滤长度并返回指定数量
            valid_titles = [title for title in titles if len(title) <= max_length]
            
            return valid_titles[:count] if valid_titles else [f"精彩{platform}视频"]
            
        except Exception as e:
            logger.error(f"生成标题建议失败: {e}")
            return [f"精彩{platform}视频"]
            
    async def optimize_description_for_seo(self, 
                                         description: str,
                                         keywords: List[str],
                                         platform: str = "通用") -> str:
        """为SEO优化描述"""
        try:
            config = self.platform_configs.get(platform, {})
            max_length = config.get('description_max_length', 1000)
            
            prompt = f"""
请优化以下描述，使其更适合SEO和{platform}平台：

原始描述：{description}
关键词：{', '.join(keywords)}
长度限制：{max_length}字符

要求：
- 自然地融入关键词
- 保持描述的可读性和吸引力
- 符合平台特点
- 控制在长度限制内

请返回优化后的描述：
"""

            response = await self.llm_service.generate_response(prompt)
            
            # 确保长度符合要求
            optimized = response.strip()
            if len(optimized) > max_length:
                optimized = optimized[:max_length-3] + "..."
                
            return optimized
            
        except Exception as e:
            logger.error(f"SEO描述优化失败: {e}")
            return description[:config.get('description_max_length', 1000)]
