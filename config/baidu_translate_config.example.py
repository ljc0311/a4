# -*- coding: utf-8 -*-
"""
百度翻译API配置文件模板
请复制此文件为 baidu_translate_config.py 并填入您的实际配置信息
"""

# 百度翻译API配置
# 请到 https://fanyi-api.baidu.com/ 申请您的APP ID和密钥
BAIDU_TRANSLATE_CONFIG = {
    # 请将下面的占位符替换为您的实际APP ID
    'app_id': 'YOUR_BAIDU_APP_ID_HERE',
    
    # 请将下面的占位符替换为您的实际密钥
    'secret_key': 'YOUR_BAIDU_SECRET_KEY_HERE',
    
    # API URL（通常不需要修改）
    'api_url': 'https://fanyi-api.baidu.com/api/trans/vip/translate'
}

# 使用说明：
# 1. 复制此文件为 baidu_translate_config.py
# 2. 访问 https://fanyi-api.baidu.com/
# 3. 注册并登录百度开发者账号
# 4. 创建翻译应用，获取APP ID和密钥
# 5. 将上面的占位符替换为实际值
# 6. 保存文件后重启程序

# 注意事项：
# - 百度翻译API有免费额度限制，超出后需要付费
# - 请妥善保管您的APP ID和密钥，不要泄露给他人
# - 如果不配置此文件，程序将使用原始中文提示词，不进行翻译