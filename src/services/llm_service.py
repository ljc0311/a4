#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM服务
统一的大语言模型服务，支持多种提供商和模型
"""

import asyncio
import aiohttp
from typing import Dict, Optional

from src.utils.logger import logger
from src.core.service_base import ServiceBase, ServiceResult
from src.core.api_manager import APIManager, APIConfig, APIType

class LLMService(ServiceBase):
    """LLM服务类"""
    
    def __init__(self, api_manager: APIManager):
        super().__init__(api_manager, "LLM服务")
        
        # 预设的提示词模板
        self.prompt_templates = {
            'storyboard_generation': """
你是一个专业的影视分镜师。请根据以下文本内容，生成详细的分镜表格。

要求：
1. 每个镜头包含：镜头编号、场景描述、角色、动作、对话、画面描述
2. 场景描述要具体，包含环境、时间、氛围
3. 角色描述要详细，包含外观、表情、动作
4. 画面描述要适合AI绘画，包含构图、光线、风格
5. 输出格式为JSON，包含shots数组

文本内容：
{text}

风格要求：{style}

请生成分镜表格：
""",
            
            'text_rewrite': """
你是一位专业的文本润色和伪原创专家。请对以下文本进行改写润色，要求：

1. 核心要求：
   - 严格保持原文的核心意思和观点不变
   - 保持原文的逻辑结构和段落层次
   - 保持原文的整体风格和语调

2. 润色优化：
   - 修正错别字、语法错误和病句
   - 优化词汇选择，使表达更准确、自然
   - 调整句式结构，提升语言流畅性
   - 消除重复表达，使文本更简洁

3. 伪原创处理：
   - 适当替换同义词，但不改变专业术语
   - 调整句子结构和表达方式
   - 保持原文长度，不大幅增减内容
   - 确保改写后仍然符合原文的使用场景

4. 输出要求：
   - 只输出改写后的文本内容
   - 不要添加任何解释、评论或格式标记
   - 保持原文的自然段落分隔

原文：
{text}

改写后的文本：
""",

            'story_creation': """
你是一位才华横溢的小说家和故事创作专家。请根据用户提供的主题创作一个引人入胜、内容丰富的完整故事。

创作要求：
1. 故事长度：1500-2000字左右，内容充实，情节完整
2. 结构完整：包含开头、发展、高潮、结局的完整故事结构
3. 人物鲜明：塑造有血有肉的角色，包含主要角色的性格特点和背景
4. 情节生动：包含冲突、转折、悬念等故事元素，让读者产生代入感
5. 描写细腻：适当的环境描写、心理描写和动作描写，增强故事的画面感
6. 主题深刻：在娱乐性的基础上，体现一定的思想内涵或人生感悟
7. 语言优美：使用生动、富有感染力的语言，避免平铺直叙
8. 适合改编：故事应该具有良好的视觉化潜力，便于后续制作成视频

重要格式要求：
- 直接输出纯文本故事内容，不要包含任何标题、章节标记、序号
- 不要使用 ### 、#### 、第一章、开头、发展、高潮、结局等标题格式
- 不要添加任何Markdown格式标记
- 不要包含创作说明、总结或其他非故事内容
- 故事应该是连贯的纯文本叙述

创作主题：{theme}

请开始你的创作：
""",

            'prompt_optimization': """
请优化以下AI绘画提示词，要求：
1. 更加详细和具体
2. 包含艺术风格描述
3. 包含技术参数建议
4. 适合Stable Diffusion等模型

原提示词：
{prompt}

风格：{style}

优化后的提示词：
"""
        }
    
    def get_api_type(self) -> APIType:
        return APIType.LLM
    
    async def _execute_request(self, api_config: APIConfig, **kwargs) -> ServiceResult:
        """执行LLM API请求"""
        try:
            prompt = kwargs.get('prompt', '')
            max_tokens = kwargs.get('max_tokens', 2000)
            temperature = kwargs.get('temperature', 0.7)

            logger.info(f"🔧 LLM API执行请求")
            logger.info(f"  🌐 提供商: {api_config.provider}")
            logger.info(f"  🤖 模型: {api_config.model_name}")
            logger.info(f"  📝 提示词长度: {len(prompt)} 字符")
            logger.info(f"  ⚙️ max_tokens: {max_tokens}, temperature: {temperature}")

            if not prompt:
                logger.error("  ❌ 提示词为空")
                return ServiceResult(success=False, error="提示词不能为空")

            # 根据不同提供商构建请求
            logger.info(f"  🚀 开始调用 {api_config.provider} API...")

            if api_config.provider.lower() == 'deepseek':
                response = await self._call_deepseek_api(api_config, prompt, max_tokens, temperature)
            elif api_config.provider.lower() == 'tongyi':
                response = await self._call_tongyi_api(api_config, prompt, max_tokens, temperature)
            elif api_config.provider.lower() == 'zhipu':
                response = await self._call_zhipu_api(api_config, prompt, max_tokens, temperature)
            elif api_config.provider.lower() == 'google':
                response = await self._call_google_api(api_config, prompt, max_tokens, temperature)
            elif api_config.provider.lower() == 'openai':
                response = await self._call_openai_api(api_config, prompt, max_tokens, temperature)
            elif api_config.provider.lower() == 'siliconflow':
                response = await self._call_siliconflow_api(api_config, prompt, max_tokens, temperature)
            else:
                error_msg = f"不支持的提供商: {api_config.provider}"
                logger.error(f"  ❌ {error_msg}")
                return ServiceResult(success=False, error=error_msg)

            # 记录成功信息
            content_length = len(response.get('content', ''))
            tokens_used = response.get('usage', {}).get('total_tokens', 0)
            logger.info(f"  ✅ API调用成功")
            logger.info(f"  📊 返回内容长度: {content_length} 字符")
            logger.info(f"  🔢 使用Token数: {tokens_used}")

            return ServiceResult(
                success=True,
                data=response,
                metadata={
                    'provider': api_config.provider,
                    'model': api_config.model_name,
                    'tokens_used': tokens_used
                }
            )
            
        except Exception as e:
            logger.error(f"LLM API请求失败: {e}")
            return ServiceResult(success=False, error=str(e))
    
    async def _call_deepseek_api(self, api_config: APIConfig, prompt: str, max_tokens: int, temperature: float) -> Dict:
        """调用DeepSeek API"""
        headers = {
            'Authorization': f'Bearer {api_config.api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            'model': api_config.model_name or 'deepseek-chat',
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens,
            'temperature': temperature
        }

        # 🔧 修复：检查URL是否已经包含endpoint，避免重复添加
        api_url = api_config.api_url
        if not api_url.endswith('/chat/completions'):
            api_url = f"{api_url.rstrip('/')}/chat/completions"

        try:
            # 🔧 增加超时时间，DeepSeek有时响应较慢
            timeout = max(api_config.timeout, 60)  # 至少60秒
            connector = aiohttp.TCPConnector(use_dns_cache=False)

            # 🔧 添加：检测是否需要代理（某些网络环境下DeepSeek也可能需要代理）
            proxy_url = None
            try:
                # 快速测试直连是否可用
                test_connector = aiohttp.TCPConnector(use_dns_cache=False)
                async with aiohttp.ClientSession(connector=test_connector) as test_session:
                    async with test_session.get(
                        "https://api.deepseek.com",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as test_response:
                        if test_response.status not in [200, 404]:  # 404也表示能连通
                            # 直连有问题，尝试代理
                            proxy_url = "http://127.0.0.1:12334"
            except:
                # 直连失败，尝试代理
                proxy_url = "http://127.0.0.1:12334"

            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    api_url,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    proxy=proxy_url  # 🔧 添加：使用代理（如果需要）
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            'content': result['choices'][0]['message']['content'],
                            'usage': result.get('usage', {})
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"API请求失败 (状态码: {response.status}): {error_text}")

        except asyncio.TimeoutError:
            raise Exception(f"DeepSeek API请求超时 (>{timeout}秒)")
        except aiohttp.ClientError as e:
            raise Exception(f"DeepSeek API网络错误: {e}")
        except Exception as e:
            if "API请求失败" in str(e):
                raise  # 重新抛出API错误
            else:
                raise Exception(f"DeepSeek API调用异常: {e}")
    
    async def _call_tongyi_api(self, api_config: APIConfig, prompt: str, max_tokens: int, temperature: float) -> Dict:
        """调用通义千问API"""
        headers = {
            'Authorization': f'Bearer {api_config.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': api_config.model_name or 'qwen-turbo',
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_config.api_url,
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=api_config.timeout)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        'content': result['choices'][0]['message']['content'],
                        'usage': result.get('usage', {})
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"API请求失败 (状态码: {response.status}): {error_text}")
    
    async def _call_zhipu_api(self, api_config: APIConfig, prompt: str, max_tokens: int, temperature: float) -> Dict:
        """调用智谱AI API"""
        headers = {
            'Authorization': f'Bearer {api_config.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': api_config.model_name or 'glm-4-flash',
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_config.api_url,
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=api_config.timeout)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        'content': result['choices'][0]['message']['content'],
                        'usage': result.get('usage', {})
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"API请求失败 (状态码: {response.status}): {error_text}")
    
    async def _call_google_api(self, api_config: APIConfig, prompt: str, max_tokens: int, temperature: float) -> Dict:
        """调用Google Gemini API"""
        headers = {
            'Content-Type': 'application/json'
        }

        data = {
            'contents': [{
                'parts': [{'text': prompt}]
            }],
            'generationConfig': {
                'maxOutputTokens': max_tokens,
                'temperature': temperature
            }
        }

        # 🔧 修复：检查URL是否已经包含完整路径
        if 'generateContent' in api_config.api_url:
            # URL已经包含完整路径，直接添加API密钥
            url = f"{api_config.api_url}?key={api_config.api_key}"
        else:
            # URL只包含基础路径，需要添加模型路径
            url = f"{api_config.api_url}/v1beta/models/{api_config.model_name or 'gemini-1.5-flash'}:generateContent?key={api_config.api_key}"

        # 🔧 添加：检测Hiddify代理支持
        proxy_url = None
        try:
            # 检查Hiddify代理是否可用（端口12334）
            connector = aiohttp.TCPConnector(use_dns_cache=False)
            async with aiohttp.ClientSession(connector=connector) as test_session:
                async with test_session.get(
                    "https://www.google.com",
                    timeout=aiohttp.ClientTimeout(total=3),
                    proxy="http://127.0.0.1:12334"
                ) as test_response:
                    if test_response.status == 200:
                        proxy_url = "http://127.0.0.1:12334"
                        self.logger.info("🌐 检测到Hiddify代理，将使用代理访问Google API")
        except:
            # 代理不可用，使用直连
            pass

        connector = aiohttp.TCPConnector(use_dns_cache=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                url,
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=api_config.timeout),
                proxy=proxy_url  # 🔧 添加：使用代理（如果可用）
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    return {
                        'content': content,
                        'usage': result.get('usageMetadata', {})
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"API请求失败 (状态码: {response.status}): {error_text}")
    
    async def generate_storyboard(self, text: str, style: Optional[str] = None, provider: Optional[str] = None) -> ServiceResult:
        """生成分镜脚本"""
        try:
            # 如果没有指定风格，从配置中获取默认风格
            if style is None:
                from src.utils.config_manager import ConfigManager
                config_manager = ConfigManager()
                style_setting = config_manager.get_setting("default_style", "电影风格")
                style = str(style_setting) if style_setting else "电影风格"
            
            # 选择提供商
            if not provider:
                providers = self.get_available_providers()
                provider = providers[0] if providers else None
            
            # 构建提示词
            prompt = f"""请根据以下文本生成{style}的分镜脚本：

{text}

请按照以下格式输出分镜信息：
镜头1：[场景描述]
镜头2：[场景描述]
...

每个镜头应该包含：
- 场景设置
- 角色动作
- 镜头角度
- 情感氛围"""
            
            # 调用LLM API
            result = await self.execute(provider=provider, prompt=prompt)

            if result.success:
                return ServiceResult(
                    success=True,
                    data={
                        "storyboard": result.data,
                        "style": style,
                        "provider": provider
                    }
                )
            else:
                return result

        except Exception as e:
            logger.error(f"生成分镜脚本失败: {e}")
            return ServiceResult(
                success=False,
                error=str(e)
            )
    


    async def rewrite_text(self, text: str, language: Optional[str] = None, provider: Optional[str] = None) -> ServiceResult:
        """
        改写文本（支持语言参数）
        
        Args:
            text: 要改写的文本
            language: 语言代码 ('zh-CN' 或 'en-US')，如果为None则使用默认中文
            provider: LLM提供商
            
        Returns:
            ServiceResult: 服务执行结果
        """
        try:
            logger.info(f"✏️ LLM服务：开始文本改写")
            logger.info(f"  📝 原文长度: {len(text)} 字符")
            logger.info(f"  📄 原文预览: {text[:50]}...")
            logger.info(f"  🌐 语言: {language or 'zh-CN'}")
            logger.info(f"  🤖 提供商: {provider or '默认'}")

            # 如果指定了语言，尝试使用双语服务
            if language and language != 'zh-CN':
                try:
                    from src.services.bilingual_llm_service import BilingualLLMService
                    from src.models.language_models import LanguageCode
                    
                    # 创建双语服务实例
                    bilingual_service = BilingualLLMService(self.api_manager)
                    
                    # 转换语言代码
                    target_language = LanguageCode.ENGLISH if language == 'en-US' else LanguageCode.CHINESE
                    
                    logger.info(f"✏️ 使用双语LLM服务改写文本，语言: {language}")
                    return await bilingual_service.rewrite_text_bilingual(text, target_language, provider)
                    
                except ImportError as e:
                    logger.warning(f"双语服务不可用，使用默认中文服务: {e}")
                except Exception as e:
                    logger.warning(f"双语服务调用失败，使用默认中文服务: {e}")

            # 使用默认的中文文本改写
            prompt = self.prompt_templates['text_rewrite'].format(text=text)

            logger.info(f"  📝 提示词长度: {len(prompt)} 字符")
            logger.info(f"  ⚙️ 参数设置: max_tokens=1500, temperature=0.8")

            result = await self.execute(
                provider=provider,
                prompt=prompt,
                max_tokens=1500,
                temperature=0.8
            )

            if result.success:
                content_length = len(result.data.get('content', ''))
                logger.info(f"  ✅ 文本改写完成，内容长度: {content_length} 字符")
            else:
                logger.error(f"  ❌ 文本改写失败: {result.error}")

            return result
            
        except Exception as e:
            logger.error(f"文本改写失败: {e}")
            return ServiceResult(success=False, error=str(e))

    async def create_story_from_theme(self, theme: str, provider: Optional[str] = None) -> ServiceResult:
        """根据主题创作故事"""
        logger.info(f"📚 LLM服务：开始故事创作")
        logger.info(f"  🎭 主题: {theme}")
        logger.info(f"  🤖 提供商: {provider or '默认'}")

        prompt = self.prompt_templates['story_creation'].format(theme=theme)

        logger.info(f"  📝 提示词长度: {len(prompt)} 字符")
        logger.info(f"  ⚙️ 参数设置: max_tokens=2500, temperature=0.9")

        result = await self.execute(
            provider=provider,
            prompt=prompt,
            max_tokens=2500,
            temperature=0.9
        )

        if result.success:
            content_length = len(result.data.get('content', ''))
            logger.info(f"  ✅ 故事创作完成，内容长度: {content_length} 字符")
        else:
            logger.error(f"  ❌ 故事创作失败: {result.error}")

        return result

    async def story_creation(self, theme: str, language: Optional[str] = None, provider: Optional[str] = None) -> ServiceResult:
        """
        故事创作方法（支持语言参数）
        
        Args:
            theme: 故事主题
            language: 语言代码 ('zh-CN' 或 'en-US')，如果为None则使用默认中文
            provider: LLM提供商
            
        Returns:
            ServiceResult: 服务执行结果
        """
        try:
            # 如果指定了语言，尝试使用双语服务
            if language and language != 'zh-CN':
                # 导入双语服务（延迟导入避免循环依赖）
                try:
                    from src.services.bilingual_llm_service import BilingualLLMService
                    from src.models.language_models import LanguageCode
                    
                    # 创建双语服务实例
                    bilingual_service = BilingualLLMService(self.api_manager)
                    
                    # 转换语言代码
                    target_language = LanguageCode.ENGLISH if language == 'en-US' else LanguageCode.CHINESE
                    
                    logger.info(f"📚 使用双语LLM服务创作故事，语言: {language}")
                    return await bilingual_service.create_story_bilingual(theme, target_language, provider)
                    
                except ImportError as e:
                    logger.warning(f"双语服务不可用，使用默认中文服务: {e}")
                except Exception as e:
                    logger.warning(f"双语服务调用失败，使用默认中文服务: {e}")
            
            # 使用默认的中文故事创作
            return await self.create_story_from_theme(theme, provider)
            
        except Exception as e:
            logger.error(f"故事创作失败: {e}")
            return ServiceResult(success=False, error=str(e))

    async def optimize_prompt(self, prompt: str, style: str = "写实风格", provider: Optional[str] = None) -> ServiceResult:
        """优化绘画提示词"""
        optimization_prompt = self.prompt_templates['prompt_optimization'].format(
            prompt=prompt,
            style=style
        )
        
        return await self.execute(
            provider=provider,
            prompt=optimization_prompt,
            max_tokens=1000,
            temperature=0.6
        )
    
    async def generate_text(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7, provider: Optional[str] = None) -> ServiceResult:
        """生成文本（通用方法）"""
        return await self.execute(
            provider=provider,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )

    async def custom_request(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7, provider: Optional[str] = None) -> ServiceResult:
        """自定义请求"""
        return await self.execute(
            provider=provider,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    async def _call_openai_api(self, api_config: APIConfig, prompt: str, max_tokens: int, temperature: float) -> Dict:
        """调用OpenAI API"""
        headers = {
            'Authorization': f'Bearer {api_config.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': api_config.model_name or 'gpt-3.5-turbo',
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_config.api_url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        'content': result['choices'][0]['message']['content'],
                        'usage': result.get('usage', {})
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API请求失败 (状态码: {response.status}): {error_text}")
    
    async def _call_siliconflow_api(self, api_config: APIConfig, prompt: str, max_tokens: int, temperature: float) -> Dict:
        """调用SiliconFlow API"""
        headers = {
            'Authorization': f'Bearer {api_config.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': api_config.model_name or 'Qwen/Qwen2.5-7B-Instruct',
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_config.api_url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        'content': result['choices'][0]['message']['content'],
                        'usage': result.get('usage', {})
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"SiliconFlow API请求失败 (状态码: {response.status}): {error_text}")