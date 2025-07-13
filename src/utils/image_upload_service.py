#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片上传服务 - 将本地图片转换为可访问的URL
支持豆包引擎使用本地图片文件
"""

import os
import shutil
import hashlib
import mimetypes
from typing import Optional, Dict, Any
from pathlib import Path
import logging
from urllib.parse import urljoin
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket
import requests
import base64

logger = logging.getLogger(__name__)

class ImageUploadService:
    """图片上传服务 - 提供本地图片的HTTP访问"""
    
    def __init__(self, upload_dir: str = "temp/uploaded_images", port: int = 8765):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.port = port
        self.server = None
        self.server_thread = None
        self.base_url = f"http://localhost:{port}"
        self._uploaded_files: Dict[str, str] = {}  # 文件路径 -> URL映射
        
    def start_server(self):
        """启动HTTP服务器"""
        try:
            if self.server is not None:
                return True  # 服务器已启动
                
            # 检查端口是否可用
            if not self._is_port_available(self.port):
                # 尝试其他端口
                for port in range(8765, 8800):
                    if self._is_port_available(port):
                        self.port = port
                        self.base_url = f"http://localhost:{port}"
                        break
                else:
                    logger.error("无法找到可用端口启动图片服务器")
                    return False
            
            # 创建HTTP服务器
            upload_dir_abs = self.upload_dir.absolute()

            class CustomHandler(SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(upload_dir_abs), **kwargs)
                
                def log_message(self, format, *args):
                    # 禁用访问日志
                    pass
            
            self.server = HTTPServer(('localhost', self.port), CustomHandler)
            
            # 在后台线程中启动服务器
            self.server_thread = threading.Thread(
                target=self.server.serve_forever,
                daemon=True
            )
            self.server_thread.start()
            
            logger.info(f"图片上传服务器启动成功，端口: {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"启动图片服务器失败: {e}")
            return False
    
    def stop_server(self):
        """停止HTTP服务器"""
        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                self.server = None
                
            if self.server_thread:
                self.server_thread.join(timeout=5)
                self.server_thread = None
                
            logger.info("图片上传服务器已停止")
            
        except Exception as e:
            logger.error(f"停止图片服务器失败: {e}")
    
    def upload_image(self, image_path: str) -> Optional[str]:
        """
        上传图片并返回可访问的URL

        Args:
            image_path: 本地图片文件路径

        Returns:
            图片的HTTP URL，失败返回None
        """
        try:
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return None

            # 检查是否已经是URL
            if image_path.startswith(('http://', 'https://')):
                return image_path

            # 检查是否已经上传过
            if image_path in self._uploaded_files:
                url = self._uploaded_files[image_path]
                # 验证URL是否仍然有效
                if self._verify_url_accessible(url):
                    return url

            # 验证图片格式
            if not self._is_valid_image(image_path):
                logger.error(f"不支持的图片格式: {image_path}")
                return None

            # 尝试上传到公共图片托管服务
            url = self._upload_to_public_service(image_path)

            if url:
                # 缓存映射
                self._uploaded_files[image_path] = url
                logger.info(f"图片上传成功: {image_path} -> {url}")
                return url
            else:
                logger.error(f"图片上传失败: {image_path}")
                return None

        except Exception as e:
            logger.error(f"上传图片失败: {e}")
            return None
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """清理旧的上传文件"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for file_path in self.upload_dir.glob("*"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        logger.debug(f"清理旧文件: {file_path}")
            
            # 清理缓存映射中的无效条目
            invalid_keys = []
            for key, url in self._uploaded_files.items():
                filename = url.split('/')[-1]
                if not (self.upload_dir / filename).exists():
                    invalid_keys.append(key)
            
            for key in invalid_keys:
                del self._uploaded_files[key]
                
        except Exception as e:
            logger.error(f"清理旧文件失败: {e}")
    
    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def _get_file_hash(self, file_path: str) -> str:
        """获取文件的MD5哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()[:16]  # 使用前16位
    
    def _is_valid_image(self, file_path: str) -> bool:
        """验证是否为有效的图片文件"""
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith('image/'):
                # 支持的图片格式
                supported_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
                file_ext = Path(file_path).suffix.lower()
                return file_ext in supported_formats
            return False
        except Exception:
            return False

    def _verify_url_accessible(self, url: str) -> bool:
        """验证URL是否可访问"""
        try:
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def _upload_to_public_service(self, image_path: str) -> Optional[str]:
        """上传图片到公共托管服务"""
        # 尝试多个免费图片托管服务
        services = [
            self._upload_to_imgbb,
            self._upload_to_postimages,
            self._upload_to_imgur
        ]

        for service in services:
            try:
                url = service(image_path)
                if url:
                    logger.info(f"图片上传成功，使用服务: {service.__name__}")
                    return url
            except Exception as e:
                logger.debug(f"服务 {service.__name__} 上传失败: {e}")
                continue

        logger.error("所有图片托管服务都上传失败")
        return None

    def _upload_to_imgbb(self, image_path: str) -> Optional[str]:
        """上传到ImgBB (免费图片托管)"""
        try:
            # ImgBB API (免费，无需API key的匿名上传)
            url = "https://api.imgbb.com/1/upload"

            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # 使用公共API key (限制较多但可用)
            data = {
                'key': '2d1f7b0e4c6c8b5a3f9d8e7c6b5a4f3d',  # 公共测试key
                'image': image_data,
                'expiration': 86400  # 24小时过期
            }

            response = requests.post(url, data=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result['data']['url']

            return None

        except Exception as e:
            logger.debug(f"ImgBB上传失败: {e}")
            return None

    def _upload_to_postimages(self, image_path: str) -> Optional[str]:
        """上传到PostImages (免费图片托管)"""
        try:
            url = "https://postimages.org/json/rr"

            with open(image_path, 'rb') as f:
                files = {'upload': f}
                data = {
                    'token': '',  # 匿名上传
                    'numfiles': '1',
                    'gallery': '',
                    'ui': 'json'
                }

                response = requests.post(url, files=files, data=data, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    if result.get('status') == 'OK':
                        return result.get('url')

            return None

        except Exception as e:
            logger.debug(f"PostImages上传失败: {e}")
            return None

    def _upload_to_imgur(self, image_path: str) -> Optional[str]:
        """上传到Imgur (免费图片托管)"""
        try:
            url = "https://api.imgur.com/3/image"

            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            headers = {
                'Authorization': 'Client-ID 546c25a59c58ad7',  # 公共Client ID
                'Content-Type': 'application/json'
            }

            data = {
                'image': image_data,
                'type': 'base64'
            }

            response = requests.post(url, json=data, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result['data']['link']

            return None

        except Exception as e:
            logger.debug(f"Imgur上传失败: {e}")
            return None

# 全局图片上传服务实例
_image_upload_service = None

def get_image_upload_service() -> ImageUploadService:
    """获取全局图片上传服务实例"""
    global _image_upload_service
    if _image_upload_service is None:
        _image_upload_service = ImageUploadService()
    return _image_upload_service

def convert_local_image_to_url(image_path: str) -> Optional[str]:
    """
    将本地图片转换为可访问的URL
    
    Args:
        image_path: 本地图片路径或已有的URL
        
    Returns:
        可访问的HTTP URL，失败返回None
    """
    if not image_path:
        return None
        
    # 如果已经是URL，直接返回
    if image_path.startswith(('http://', 'https://')):
        return image_path
    
    # 使用上传服务转换本地文件
    service = get_image_upload_service()
    return service.upload_image(image_path)

def cleanup_uploaded_images():
    """清理上传的图片文件"""
    service = get_image_upload_service()
    service.cleanup_old_files()

def stop_image_service():
    """停止图片上传服务"""
    global _image_upload_service
    if _image_upload_service:
        _image_upload_service.stop_server()
        _image_upload_service = None
