# -*- coding: utf-8 -*-
"""
百度翻译API模块
提供中文到英文的翻译功能
"""

import hashlib
import os
import random
import time
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 百度翻译API配置
BAIDU_TRANSLATE_CONFIG = {
    'app_id': '',  # 请填入您的百度翻译APP ID
    'secret_key': '',  # 请填入您的百度翻译密钥
    'api_url': 'https://fanyi-api.baidu.com/api/trans/vip/translate'
}

# 尝试从配置文件加载配置
try:
    import sys
    import os
    # 添加项目根目录到路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    config_path = os.path.join(project_root, 'config')
    if config_path not in sys.path:
        sys.path.insert(0, config_path)
    
    from baidu_translate_config import BAIDU_TRANSLATE_CONFIG as CONFIG
    if CONFIG.get('app_id') and CONFIG.get('app_id') != 'your_app_id_here':
        BAIDU_TRANSLATE_CONFIG.update(CONFIG)
        logger.info("已从配置文件加载百度翻译API配置")
except ImportError:
    logger.warning("未找到百度翻译配置文件，请创建 config/baidu_translate_config.py")
except Exception as e:
    logger.warning(f"加载百度翻译配置失败: {e}")

def set_baidu_config(app_id: str, secret_key: str):
    """
    设置百度翻译API配置
    
    Args:
        app_id: 百度翻译APP ID
        secret_key: 百度翻译密钥
    """
    global BAIDU_TRANSLATE_CONFIG
    BAIDU_TRANSLATE_CONFIG['app_id'] = app_id
    BAIDU_TRANSLATE_CONFIG['secret_key'] = secret_key
    logger.info("百度翻译API配置已更新")

def generate_sign(query: str, salt: str, app_id: str, secret_key: str) -> str:
    """
    生成百度翻译API签名
    
    Args:
        query: 待翻译文本
        salt: 随机数
        app_id: APP ID
        secret_key: 密钥
        
    Returns:
        签名字符串
    """
    # 拼接字符串
    sign_str = app_id + query + salt + secret_key
    
    # MD5加密
    md5 = hashlib.md5()
    md5.update(sign_str.encode('utf-8'))
    sign = md5.hexdigest()
    
    return sign

def translate_text(text: str, from_lang: str = 'zh', to_lang: str = 'en') -> Optional[str]:
    """
    使用百度翻译API翻译文本
    
    Args:
        text: 待翻译的文本
        from_lang: 源语言，默认为中文(zh)
        to_lang: 目标语言，默认为英文(en)
        
    Returns:
        翻译结果，失败时返回None
    """
    if not text or not text.strip():
        logger.warning("翻译文本为空")
        return None
    
    app_id = BAIDU_TRANSLATE_CONFIG['app_id']
    secret_key = BAIDU_TRANSLATE_CONFIG['secret_key']
    api_url = BAIDU_TRANSLATE_CONFIG['api_url']
    
    if not app_id or not secret_key:
        logger.error("百度翻译API配置不完整，请先调用set_baidu_config()设置")
        return None
    
    try:
        # 生成随机数
        salt = str(random.randint(32768, 65536))
        
        # 生成签名
        sign = generate_sign(text, salt, app_id, secret_key)
        
        # 构建请求参数
        params = {
            'q': text,
            'from': from_lang,
            'to': to_lang,
            'appid': app_id,
            'salt': salt,
            'sign': sign
        }
        
        logger.debug(f"百度翻译请求参数: {params}")
        
        # 发送请求
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        logger.debug(f"百度翻译响应: {result}")
        
        # 检查响应状态
        if 'error_code' in result:
            error_code = result['error_code']
            error_msg = result.get('error_msg', '未知错误')
            logger.error(f"百度翻译API错误: {error_code} - {error_msg}")
            return None
        
        # 提取翻译结果
        if 'trans_result' in result and result['trans_result']:
            translated_text = result['trans_result'][0]['dst']
            logger.info(f"百度翻译成功: {text[:50]}... -> {translated_text[:50]}...")
            return translated_text
        else:
            logger.error("百度翻译响应格式异常")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("百度翻译请求超时")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"百度翻译请求异常: {e}")
        return None
    except Exception as e:
        logger.error(f"百度翻译异常: {e}")
        return None

def is_configured() -> bool:
    """
    检查百度翻译API是否已配置 - 已禁用

    Returns:
        False - 百度翻译已禁用，避免余额不足错误
    """
    # 🔧 禁用百度翻译，避免余额不足的错误提示
    return False

def test_translation():
    """
    测试百度翻译功能
    """
    if not is_configured():
        print("请先配置百度翻译API")
        return
    
    test_text = "一个美丽的女孩站在花园里，阳光明媚，高清摄影"
    result = translate_text(test_text)
    
    if result:
        print(f"原文: {test_text}")
        print(f"译文: {result}")
    else:
        print("翻译失败")

# 注释掉测试代码，避免与main.py冲突
# if __name__ == "__main__":
#     # 测试代码
#     test_translation()