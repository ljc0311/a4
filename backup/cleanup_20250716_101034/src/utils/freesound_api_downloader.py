#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Freesound API音效下载器
使用Freesound.org官方API下载真实音效文件
"""

import os
import re
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import random

from src.utils.logger import logger


class FreesoundAPIDownloader:
    """Freesound API音效下载器"""
    
    def __init__(self, output_dir: str):
        """
        初始化下载器
        
        Args:
            output_dir: 音效文件输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建音效专用文件夹
        self.sound_effects_dir = self.output_dir / "sound_effects"
        self.sound_effects_dir.mkdir(parents=True, exist_ok=True)
        
        # Freesound API配置
        self.api_key = "AxqpZnunHJhGRuiDHhTvyKnx2UYwfyiAX7rA6I0A"  # 您的API密钥
        self.base_url = "https://freesound.org/apiv2"
        
        # 请求头
        self.headers = {
            'User-Agent': 'AI_Video_Generator/1.0',
            'Authorization': f'Token {self.api_key}',
            'Accept': 'application/json',
        }
        
        # 会话对象
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 🔧 删除简陋的映射表，改用智能翻译
        # 初始化翻译功能
        self._init_translation_services()

    def __del__(self):
        """析构函数，确保会话正确关闭"""
        if hasattr(self, 'session'):
            self.session.close()

        logger.info(f"Freesound API下载器初始化完成，输出目录: {self.sound_effects_dir}")

    def _init_translation_services(self):
        """初始化翻译服务"""
        try:
            # 导入百度翻译
            from src.utils.baidu_translator import translate_text, is_configured as is_baidu_configured
            self.baidu_translate = translate_text
            self.is_baidu_configured = is_baidu_configured

            # 尝试导入LLM服务
            try:
                from src.core.service_manager import ServiceManager, ServiceType

                service_manager = ServiceManager()
                llm_service = service_manager.get_service(ServiceType.LLM)

                if llm_service:
                    self.llm_service = llm_service
                    logger.info("LLM翻译服务初始化成功")
                else:
                    self.llm_service = None
                    logger.info("LLM服务未找到，将仅使用百度翻译")

            except Exception as e:
                logger.warning(f"LLM翻译服务初始化失败: {e}")
                self.llm_api = None

            logger.info("翻译服务初始化完成")

        except Exception as e:
            logger.error(f"翻译服务初始化失败: {e}")
            self.baidu_translate = None
            self.is_baidu_configured = None
            self.llm_api = None
    
    def search_and_download_shortest(self, query: str, filename: Optional[str] = None) -> Optional[str]:
        """
        搜索并下载最短的音效
        
        Args:
            query: 搜索关键词
            filename: 自定义文件名
            
        Returns:
            下载的文件路径，失败返回None
        """
        try:
            logger.info(f"使用Freesound API搜索音效: {query}")
            
            # 翻译中文关键词
            search_query = self._translate_query(query)
            
            # 搜索音效
            sounds = self._search_sounds(search_query)
            
            if not sounds:
                logger.warning(f"未找到匹配的音效: {search_query}")
                return None
            
            # 选择最短的音效
            shortest_sound = self._select_shortest_sound(sounds)
            
            if not shortest_sound:
                logger.warning("未找到合适的音效文件")
                return None
            
            # 下载音效
            downloaded_path = self._download_sound(shortest_sound, query, filename)
            
            if downloaded_path:
                logger.info(f"成功下载Freesound音效: {downloaded_path}")
                return downloaded_path
            else:
                logger.warning("音效下载失败")
                return None
                
        except Exception as e:
            logger.error(f"Freesound API下载失败: {e}")
            return None
    
    def _translate_query(self, query: str) -> str:
        """使用智能翻译将中文音效描述翻译为英文搜索关键词"""
        # 清理查询词
        clean_query = re.sub(r'[【】\[\]（）()]', '', query).strip()

        logger.info(f"开始翻译音效查询词: '{query}' -> 清理后: '{clean_query}'")

        # 如果已经是英文，直接返回
        if not any('\u4e00' <= char <= '\u9fff' for char in clean_query):
            logger.info(f"查询词已是英文，直接使用: '{clean_query}'")
            return clean_query

        # 🔧 优先使用百度翻译
        if hasattr(self, 'is_baidu_configured') and self.is_baidu_configured and self.is_baidu_configured():
            try:
                logger.info("使用百度翻译API翻译音效关键词")
                translated_result = self.baidu_translate(clean_query, 'zh', 'en')

                if translated_result and translated_result.strip():
                    # 清理翻译结果，提取关键词
                    english_keywords = self._extract_sound_keywords(translated_result)
                    logger.info(f"百度翻译成功: '{clean_query}' -> '{english_keywords}'")
                    return english_keywords
                else:
                    logger.warning("百度翻译返回空结果")
            except Exception as e:
                logger.warning(f"百度翻译失败: {e}")
        else:
            logger.info("百度翻译未配置，尝试LLM翻译")

        # 🔧 如果百度翻译失败，使用LLM翻译
        if hasattr(self, 'llm_api') and self.llm_api:
            try:
                logger.info("使用LLM翻译音效关键词")

                # 构建专门的音效翻译提示
                translation_prompt = f"""
请将以下中文音效描述翻译成适合音效搜索的英文关键词。

中文音效描述: {clean_query}

要求:
1. 只返回英文关键词，不要包含任何中文
2. 关键词要简洁明确，适合音效库搜索
3. 如果是复合音效，用空格分隔关键词
4. 不要返回完整句子，只要关键词
5. 例如："脚步声" -> "footsteps"，"鸟鸣声" -> "birds singing"

英文关键词:"""

                response = self.llm_api.rewrite_text(translation_prompt)
                if response and response.strip():
                    # 清理LLM响应，提取关键词
                    english_keywords = self._extract_sound_keywords(response)
                    logger.info(f"LLM翻译成功: '{clean_query}' -> '{english_keywords}'")
                    return english_keywords
                else:
                    logger.warning("LLM翻译返回空结果")
            except Exception as e:
                logger.warning(f"LLM翻译失败: {e}")

        # 🔧 如果所有翻译都失败，使用原查询词
        logger.warning(f"所有翻译方法都失败，使用原查询词: '{clean_query}'")
        return clean_query

    def _extract_sound_keywords(self, text: str) -> str:
        """从翻译结果中提取音效关键词"""
        import re

        # 清理文本
        cleaned = text.strip()

        # 移除常见的无用词汇
        stop_words = ['sound', 'effect', 'audio', 'noise', 'the', 'a', 'an', 'of', 'and', 'or']

        # 提取英文单词
        words = re.findall(r'\b[a-zA-Z]+\b', cleaned.lower())

        # 过滤停用词
        keywords = [word for word in words if word not in stop_words and len(word) > 2]

        # 如果没有提取到关键词，返回原文本的前几个单词
        if not keywords:
            words = cleaned.split()[:3]  # 取前3个词
            keywords = [word.strip('.,!?;:') for word in words if word.strip('.,!?;:')]

        result = ' '.join(keywords[:3])  # 最多3个关键词
        logger.debug(f"关键词提取: '{text}' -> '{result}'")
        return result if result else cleaned
    
    def _search_sounds(self, query: str, max_results: int = 15) -> List[Dict[str, Any]]:
        """搜索音效"""
        try:
            # 构建搜索URL
            search_url = f"{self.base_url}/search/text/"
            
            # 🔧 修复：优化搜索参数，确保音效质量
            params = {
                'query': query,
                'fields': 'id,name,duration,previews,download,filesize,type,samplerate,channels,avg_rating,num_ratings',
                'sort': 'score',  # 按相关性排序，而不是时长
                'page_size': max_results,
                'filter': 'duration:[1 TO 15] samplerate:[22050 TO 48000]'  # 1-15秒，确保音质
            }
            
            # 发送请求
            response = self.session.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                sounds = data.get('results', [])
                logger.info(f"找到 {len(sounds)} 个音效")
                return sounds
            else:
                logger.warning(f"搜索请求失败: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"搜索音效失败: {e}")
            return []
    
    def _select_shortest_sound(self, sounds: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """选择最佳音效 - 综合考虑时长、质量和评分"""
        try:
            # 过滤有效的音效
            valid_sounds = []
            for sound in sounds:
                # 检查是否有下载链接和预览链接
                if (sound.get('download') and
                    sound.get('previews') and
                    sound.get('duration', 0) > 0):
                    valid_sounds.append(sound)

            if not valid_sounds:
                logger.warning("没有找到有效的音效文件")
                return None

            # 🔧 修复：智能选择最佳音效
            # 计算每个音效的综合评分
            for sound in valid_sounds:
                score = 0
                duration = sound.get('duration', 0)
                avg_rating = sound.get('avg_rating', 0)
                num_ratings = sound.get('num_ratings', 0)
                filesize = sound.get('filesize', 0)

                # 时长评分：2-8秒为最佳，过短或过长都减分
                if 2 <= duration <= 8:
                    score += 10
                elif 1 <= duration <= 15:
                    score += 5
                else:
                    score -= 5

                # 评分评分：有评分且评分高的加分
                if avg_rating > 0 and num_ratings > 0:
                    score += avg_rating * 2
                    if num_ratings > 5:
                        score += 2

                # 文件大小评分：太小的文件可能质量不好
                if filesize > 50000:  # 大于50KB
                    score += 3
                elif filesize > 20000:  # 大于20KB
                    score += 1

                sound['_score'] = score

            # 按综合评分排序，选择最佳的
            valid_sounds.sort(key=lambda x: x.get('_score', 0), reverse=True)

            selected = valid_sounds[0]
            logger.info(f"选择音效: {selected.get('name')} (时长: {selected.get('duration')}秒, 评分: {selected.get('_score', 0)})")

            return selected

        except Exception as e:
            logger.error(f"选择音效失败: {e}")
            return None
    
    def _download_sound(self, sound: Dict[str, Any], original_query: str, filename: Optional[str] = None) -> Optional[str]:
        """下载音效文件"""
        try:
            # 生成文件名
            if not filename:
                clean_query = re.sub(r'[^\w\s\u4e00-\u9fff]', '', original_query)
                clean_query = re.sub(r'\s+', '_', clean_query).strip('_')
                
                # 使用简洁的文件名，不包含时间戳
                # 获取文件扩展名
                sound_type = sound.get('type', 'mp3').lower()
                filename = f"{clean_query}.{sound_type}"
            
            file_path = self.sound_effects_dir / filename
            
            # 检查文件是否已存在
            if file_path.exists():
                logger.info(f"音效文件已存在: {file_path}")
                return str(file_path)
            
            # 尝试下载高质量版本（需要OAuth2，这里先尝试预览版本）
            download_url = None
            
            # 获取预览URL（通常是MP3格式）
            previews = sound.get('previews', {})
            if previews:
                # 优先选择高质量预览
                if 'preview-hq-mp3' in previews:
                    download_url = previews['preview-hq-mp3']
                elif 'preview-lq-mp3' in previews:
                    download_url = previews['preview-lq-mp3']
            
            if not download_url:
                logger.warning("未找到可下载的音效URL")
                return None
            
            # 下载文件
            logger.info(f"下载音效: {download_url}")
            response = self.session.get(download_url, timeout=30, stream=True)
            
            if response.status_code == 200:
                # 写入文件
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # 验证文件
                if file_path.exists() and file_path.stat().st_size > 1000:
                    logger.info(f"成功下载音效: {file_path} ({file_path.stat().st_size} 字节)")
                    return str(file_path)
                else:
                    logger.warning(f"下载的文件无效: {file_path}")
                    if file_path.exists():
                        file_path.unlink()
                    return None
            else:
                logger.warning(f"下载失败: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"下载音效失败: {e}")
            return None
