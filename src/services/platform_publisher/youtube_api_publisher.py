#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于YouTube Data API v3的发布器
使用官方API进行视频上传，更稳定可靠
"""

import os
import json
import pickle
from typing import Dict, Any, Optional
from pathlib import Path
import asyncio
import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from src.utils.logger import logger

class YouTubeAPIPublisher:
    """基于YouTube Data API v3的发布器"""
    
    # YouTube API作用域
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube.readonly'
    ]
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.youtube = None
        self.credentials_file = config.get('credentials_file', 'config/youtube_credentials.json')
        self.token_file = config.get('token_file', 'config/youtube_token.pickle')
        
        # 创建配置目录
        Path(self.credentials_file).parent.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self) -> bool:
        """初始化YouTube API客户端"""
        try:
            logger.info("🔑 初始化YouTube API客户端...")

            # 检查凭据文件
            if not os.path.exists(self.credentials_file):
                logger.error(f"❌ YouTube API凭据文件不存在: {self.credentials_file}")
                logger.info("📝 请按照以下步骤配置YouTube API:")
                logger.info("1. 访问 https://console.developers.google.com/")
                logger.info("2. 创建项目并启用YouTube Data API v3")
                logger.info("3. 创建OAuth 2.0凭据并下载JSON文件")
                logger.info(f"4. 将文件保存为: {self.credentials_file}")
                return False

            # 🔧 修复：配置代理（仅设置环境变量，避免http参数问题）
            self._configure_proxy_env()

            # 加载或创建认证令牌
            creds = None
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)

            # 如果没有有效凭据，进行OAuth流程
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("🔄 刷新YouTube API令牌...")
                    # 🔧 修复：不传递http参数，使用环境变量代理
                    creds.refresh(Request())
                else:
                    logger.info("🔐 开始YouTube OAuth认证流程...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)

                # 保存凭据
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)

            # 构建YouTube API客户端
            # 使用更简单的方法：设置环境变量让requests使用代理
            if self.config.get('use_proxy') and self.config.get('proxy_url'):
                proxy_url = self.config.get('proxy_url')
                os.environ['HTTP_PROXY'] = proxy_url
                os.environ['HTTPS_PROXY'] = proxy_url
                logger.info(f"🌐 设置环境代理: {proxy_url}")

            self.youtube = build('youtube', 'v3', credentials=creds)
            logger.info("✅ YouTube API客户端初始化成功")
            return True

        except Exception as e:
            logger.error(f"❌ YouTube API初始化失败: {e}")
            return False

    def _configure_proxy_env(self):
        """🔧 修复：配置代理（仅设置环境变量，避免http参数问题）"""
        try:
            # 检查是否启用代理
            if not self.config.get('use_proxy', False):
                logger.info("🌐 代理未启用")
                return

            proxy_url = self.config.get('proxy_url')
            if proxy_url:
                # 设置环境变量代理
                logger.info(f"🌐 使用指定代理: {proxy_url}")
                os.environ['HTTP_PROXY'] = proxy_url
                os.environ['HTTPS_PROXY'] = proxy_url
            else:
                # 清除代理环境变量（使用系统默认）
                logger.info("🌐 使用系统代理设置")
                if 'HTTP_PROXY' in os.environ:
                    del os.environ['HTTP_PROXY']
                if 'HTTPS_PROXY' in os.environ:
                    del os.environ['HTTPS_PROXY']

        except Exception as e:
            logger.warning(f"⚠️ 代理配置失败: {e}")

    def _configure_proxy(self):
        """配置代理设置"""
        try:
            # 检查是否启用代理
            if not self.config.get('use_proxy', False):
                return None

            # 创建HTTP对象
            http = httplib2.Http(timeout=self.config.get('timeout', 60))

            # 检查代理配置
            proxy_url = self.config.get('proxy_url')
            if proxy_url:
                # 手动指定代理
                logger.info(f"🌐 使用指定代理: {proxy_url}")
                import urllib.parse
                parsed = urllib.parse.urlparse(proxy_url)
                proxy_info = httplib2.ProxyInfo(
                    httplib2.socks.PROXY_TYPE_HTTP,
                    parsed.hostname,
                    parsed.port
                )
                http = httplib2.Http(proxy_info=proxy_info, timeout=self.config.get('timeout', 60))
            else:
                # 自动检测系统代理
                logger.info("🌐 使用系统代理设置")
                # httplib2会自动使用系统代理设置

            return http

        except Exception as e:
            logger.warning(f"⚠️ 代理配置失败，使用直连: {e}")
            return httplib2.Http(timeout=self.config.get('timeout', 60))


    
    async def upload_video(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """上传视频到YouTube（增强版：支持封面、翻译、智能内容生成）"""
        try:
            if not self.youtube:
                if not await self.initialize():
                    return {'success': False, 'error': 'YouTube API初始化失败'}

            video_path = video_info.get('video_path')
            if not video_path or not os.path.exists(video_path):
                return {'success': False, 'error': '视频文件不存在'}

            logger.info(f"📤 开始上传视频到YouTube: {video_path}")

            # 🔧 新增：智能内容处理和翻译
            processed_info = await self._process_video_content(video_info)

            # 准备视频元数据（使用处理后的内容）
            title = processed_info.get('title', '未命名视频')[:100]  # YouTube标题限制
            description = processed_info.get('description', '')[:5000]  # YouTube描述限制
            tags = processed_info.get('tags', [])[:15]  # YouTube标签限制
            
            # 检测是否为Shorts（时长小于60秒）
            is_shorts = self._is_shorts_video(video_path)
            if is_shorts:
                title = f"{title} #Shorts"
                if '#Shorts' not in description:
                    description = f"{description}\n\n#Shorts"
            
            # 构建请求体
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': '22'  # People & Blogs
                },
                'status': {
                    'privacyStatus': video_info.get('privacy', 'public'),
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # 创建媒体上传对象
            media = MediaFileUpload(
                video_path,
                chunksize=-1,
                resumable=True,
                mimetype='video/*'
            )
            
            # 执行上传
            logger.info("🚀 开始上传视频文件...")
            insert_request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # 执行可恢复上传
            response = None
            error = None
            retry = 0
            
            while response is None:
                try:
                    status, response = insert_request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        logger.info(f"📊 上传进度: {progress}%")
                        
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        # 可重试的错误
                        retry += 1
                        if retry > 3:
                            logger.error(f"❌ 上传失败，重试次数超限: {e}")
                            return {'success': False, 'error': f'上传失败: {e}'}
                        
                        logger.warning(f"⚠️ 上传遇到临时错误，重试 {retry}/3: {e}")
                        await asyncio.sleep(2 ** retry)  # 指数退避
                        continue
                    else:
                        logger.error(f"❌ 上传失败: {e}")
                        return {'success': False, 'error': f'上传失败: {e}'}
            
            if response:
                video_id = response['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                logger.info(f"✅ 视频上传成功!")
                logger.info(f"📺 视频ID: {video_id}")
                logger.info(f"🔗 视频链接: {video_url}")

                # 🔧 新增：上传封面
                thumbnail_result = await self._upload_thumbnail(video_id, processed_info)

                return {
                    'success': True,
                    'video_id': video_id,
                    'video_url': video_url,
                    'message': '视频上传成功',
                    'thumbnail_uploaded': thumbnail_result.get('success', False),
                    'processed_content': {
                        'title': title,
                        'description': description,
                        'tags': tags
                    }
                }
            else:
                return {'success': False, 'error': '上传响应为空'}
                
        except Exception as e:
            logger.error(f"❌ YouTube视频上传失败: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _process_video_content(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """🔧 新增：智能处理视频内容（翻译、优化、生成）"""
        try:
            logger.info("🎬 开始智能处理YouTube视频内容...")

            # 获取原始内容
            original_title = video_info.get('title', '未命名视频')
            original_description = video_info.get('description', '')
            original_tags = video_info.get('tags', [])

            # 🔧 翻译内容到英文
            translated_content = await self._translate_to_english({
                'title': original_title,
                'description': original_description,
                'tags': original_tags
            })

            # 🔧 优化YouTube内容
            optimized_content = await self._optimize_for_youtube(translated_content)

            logger.info("✅ 视频内容处理完成")
            return optimized_content

        except Exception as e:
            logger.warning(f"⚠️ 内容处理失败，使用原始内容: {e}")
            return {
                'title': video_info.get('title', '未命名视频'),
                'description': video_info.get('description', ''),
                'tags': video_info.get('tags', [])
            }

    async def _translate_to_english(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """翻译内容到英文"""
        try:
            # 🔧 简化：直接使用增强翻译器，避免复杂的LLM集成问题
            from src.utils.enhanced_translator import translate_text_enhanced

            logger.info("🌐 正在翻译内容到英文...")

            # 分别翻译各个部分
            translated_content = {}

            # 翻译标题
            title = content.get('title', '')
            if title:
                translated_title = translate_text_enhanced(title, 'zh', 'en')
                if translated_title and translated_title != title:
                    translated_content['title'] = translated_title
                    logger.info(f"✅ 标题翻译: {title[:30]}... -> {translated_title[:30]}...")
                else:
                    translated_content['title'] = title
                    logger.info(f"⚠️ 标题翻译失败，使用原文: {title[:30]}...")
            else:
                translated_content['title'] = title

            # 翻译描述
            description = content.get('description', '')
            if description:
                translated_desc = translate_text_enhanced(description, 'zh', 'en')
                if translated_desc and translated_desc != description:
                    translated_content['description'] = translated_desc
                    logger.info(f"✅ 描述翻译完成")
                else:
                    translated_content['description'] = description
                    logger.info(f"⚠️ 描述翻译失败，使用原文")
            else:
                translated_content['description'] = description

            # 翻译标签
            tags = content.get('tags', [])
            translated_tags = []
            for tag in tags:
                translated_tag = translate_text_enhanced(tag, 'zh', 'en')
                if translated_tag and translated_tag != tag:
                    translated_tags.append(translated_tag)
                    logger.info(f"✅ 标签翻译: {tag} -> {translated_tag}")
                else:
                    translated_tags.append(tag)
                    logger.info(f"⚠️ 标签翻译失败: {tag}")
            translated_content['tags'] = translated_tags

            logger.info("✅ 内容翻译完成")
            return translated_content

        except Exception as e:
            logger.warning(f"⚠️ 翻译失败，使用原始内容: {e}")
            return content

    async def _optimize_for_youtube(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """优化YouTube内容"""
        try:
            # 使用原始标题，不添加额外前缀
            title = content['title']

            # 优化描述（添加标签）
            description = content['description']
            tags = content['tags']

            # 在描述末尾添加标签
            if tags:
                tag_text = ' '.join([f'#{tag.replace(" ", "")}' for tag in tags])
                description = f"{description}\n\n{tag_text}"

            # 添加标准YouTube描述元素（移除AI相关内容）
            description += "\n\n🔔 订阅频道获取更多内容"
            description += "\n💬 评论分享您的想法"
            description += "\n👍 点赞支持创作"

            return {
                'title': title[:100],  # YouTube限制
                'description': description[:5000],  # YouTube限制
                'tags': tags[:15]  # YouTube限制
            }

        except Exception as e:
            logger.warning(f"⚠️ 内容优化失败: {e}")
            return content

    def _is_shorts_video(self, video_path: str) -> bool:
        """检测是否为Shorts视频（时长<60秒）"""
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            duration = frame_count / fps if fps > 0 else 0
            cap.release()
            return duration < 60
        except:
            # 如果无法检测，默认不是Shorts
            return False

    async def _upload_thumbnail(self, video_id: str, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """🔧 新增：上传视频封面"""
        try:
            # 查找封面文件
            thumbnail_path = await self._find_or_generate_thumbnail(video_info)

            if not thumbnail_path or not os.path.exists(thumbnail_path):
                logger.warning("⚠️ 未找到封面文件，跳过封面上传")
                return {'success': False, 'error': '封面文件不存在'}

            logger.info(f"📸 开始上传封面: {thumbnail_path}")

            # 创建媒体上传对象
            media = MediaFileUpload(
                thumbnail_path,
                mimetype='image/jpeg',
                resumable=True
            )

            # 上传封面
            request = self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=media
            )

            response = request.execute()

            if response:
                logger.info("✅ 封面上传成功")
                return {'success': True, 'response': response}
            else:
                logger.warning("⚠️ 封面上传响应为空")
                return {'success': False, 'error': '封面上传响应为空'}

        except Exception as e:
            logger.warning(f"⚠️ 封面上传失败: {e}")
            return {'success': False, 'error': str(e)}

    async def _find_or_generate_thumbnail(self, video_info: Dict[str, Any]) -> str:
        """查找或生成封面"""
        try:
            video_path = video_info.get('video_path')
            if not video_path:
                return None

            # 1. 查找同名的封面文件
            video_dir = os.path.dirname(video_path)
            video_name = os.path.splitext(os.path.basename(video_path))[0]

            # 常见封面文件扩展名
            thumbnail_extensions = ['.jpg', '.jpeg', '.png', '.webp']

            for ext in thumbnail_extensions:
                thumbnail_path = os.path.join(video_dir, f"{video_name}{ext}")
                if os.path.exists(thumbnail_path):
                    logger.info(f"📸 找到封面文件: {thumbnail_path}")
                    return thumbnail_path

            # 2. 查找通用封面文件
            common_names = ['thumbnail', 'cover', 'poster']
            for name in common_names:
                for ext in thumbnail_extensions:
                    thumbnail_path = os.path.join(video_dir, f"{name}{ext}")
                    if os.path.exists(thumbnail_path):
                        logger.info(f"📸 找到通用封面: {thumbnail_path}")
                        return thumbnail_path

            # 3. 从视频中提取第一帧作为封面
            logger.info("📸 从视频中提取封面...")
            return await self._extract_video_frame(video_path)

        except Exception as e:
            logger.warning(f"⚠️ 查找封面失败: {e}")
            return None

    async def _extract_video_frame(self, video_path: str) -> str:
        """从视频中提取第一帧作为封面"""
        try:
            import cv2

            # 生成封面文件路径
            video_dir = os.path.dirname(video_path)
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            thumbnail_path = os.path.join(video_dir, f"{video_name}_thumbnail.jpg")

            # 打开视频
            cap = cv2.VideoCapture(video_path)

            # 跳到视频的10%位置（通常比第一帧更有代表性）
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            target_frame = int(total_frames * 0.1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

            # 读取帧
            ret, frame = cap.read()
            if ret:
                # 调整尺寸到YouTube推荐的封面尺寸 (1280x720)
                height, width = frame.shape[:2]
                if width > 1280 or height > 720:
                    # 保持宽高比缩放
                    scale = min(1280/width, 720/height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))

                # 保存封面
                cv2.imwrite(thumbnail_path, frame)
                cap.release()

                logger.info(f"✅ 封面提取成功: {thumbnail_path}")
                return thumbnail_path
            else:
                cap.release()
                logger.warning("⚠️ 无法从视频中提取帧")
                return None

        except Exception as e:
            logger.warning(f"⚠️ 视频帧提取失败: {e}")
            return None

    async def get_channel_info(self) -> Dict[str, Any]:
        """获取频道信息"""
        try:
            if not self.youtube:
                if not await self.initialize():
                    return {'success': False, 'error': 'YouTube API初始化失败'}
            
            request = self.youtube.channels().list(
                part='snippet,statistics',
                mine=True
            )
            response = request.execute()
            
            if response['items']:
                channel = response['items'][0]
                return {
                    'success': True,
                    'channel_id': channel['id'],
                    'title': channel['snippet']['title'],
                    'subscriber_count': channel['statistics'].get('subscriberCount', 0),
                    'video_count': channel['statistics'].get('videoCount', 0)
                }
            else:
                return {'success': False, 'error': '未找到频道信息'}
                
        except Exception as e:
            logger.error(f"❌ 获取频道信息失败: {e}")
            return {'success': False, 'error': str(e)}
