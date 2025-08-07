#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双语模板管理器
管理中英文提示词模板，支持根据语言选择合适的模板
"""

from typing import Dict, Optional
from enum import Enum

from src.models.language_models import LanguageCode
from src.utils.logger import logger


class TemplateType(Enum):
    """模板类型枚举"""
    STORY_CREATION = "story_creation"
    TEXT_REWRITE = "text_rewrite"
    STORYBOARD_GENERATION = "storyboard_generation"
    PROMPT_OPTIMIZATION = "prompt_optimization"
    TEXT_TRANSLATION = "text_translation"


class BilingualTemplateManager:
    """双语模板管理器类"""
    
    def __init__(self):
        self._templates = self._initialize_templates()
        logger.info("双语模板管理器初始化完成")
    
    def _initialize_templates(self) -> Dict[TemplateType, Dict[LanguageCode, str]]:
        """初始化模板库"""
        return {
            TemplateType.STORY_CREATION: {
                LanguageCode.CHINESE: """
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
                LanguageCode.ENGLISH: """
You are a talented novelist and storytelling expert. Please create an engaging, content-rich complete story based on the theme provided by the user.

Creative Requirements:
1. Story Length: Approximately 1500-2000 words, with substantial content and complete plot
2. Complete Structure: Include a complete story structure with beginning, development, climax, and resolution
3. Vivid Characters: Create flesh-and-blood characters with distinct personalities and backgrounds for main characters
4. Dynamic Plot: Include conflicts, twists, suspense and other story elements that create reader engagement
5. Detailed Descriptions: Appropriate environmental, psychological, and action descriptions to enhance visual appeal
6. Profound Theme: Beyond entertainment value, reflect certain philosophical insights or life wisdom
7. Beautiful Language: Use vivid, emotionally engaging language, avoiding plain narration
8. Adaptation-Friendly: The story should have good visualization potential for subsequent video production

Important Format Requirements:
- Output pure text story content directly, without any titles, chapter markers, or numbering
- Do not use ###, ####, Chapter 1, Beginning, Development, Climax, Ending or other title formats
- Do not add any Markdown formatting
- Do not include creative explanations, summaries, or other non-story content
- The story should be coherent plain text narrative

Story Theme: {theme}

Please begin your creation:
"""
            },
            
            TemplateType.TEXT_REWRITE: {
                LanguageCode.CHINESE: """
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
                LanguageCode.ENGLISH: """
You are a professional text polishing and rewriting expert. Please rewrite and polish the following text with these requirements:

1. Core Requirements:
   - Strictly maintain the original core meaning and viewpoints unchanged
   - Preserve the original logical structure and paragraph hierarchy
   - Maintain the overall style and tone of the original text

2. Polishing Optimization:
   - Correct spelling errors, grammatical mistakes, and awkward sentences
   - Optimize vocabulary choices for more accurate and natural expression
   - Adjust sentence structures to improve language fluency
   - Eliminate repetitive expressions to make the text more concise

3. Rewriting Processing:
   - Appropriately replace synonyms while preserving technical terms
   - Adjust sentence structures and expression methods
   - Maintain original text length without significant additions or reductions
   - Ensure the rewritten text still fits the original usage context

4. Output Requirements:
   - Output only the rewritten text content
   - Do not add any explanations, comments, or format markers
   - Maintain the natural paragraph separation of the original text

Original Text:
{text}

Rewritten Text:
"""
            },
            
            TemplateType.STORYBOARD_GENERATION: {
                LanguageCode.CHINESE: """
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
                LanguageCode.ENGLISH: """
You are a professional film storyboard artist. Please generate a detailed storyboard table based on the following text content.

Requirements:
1. Each shot includes: shot number, scene description, characters, actions, dialogue, visual description
2. Scene descriptions should be specific, including environment, time, atmosphere
3. Character descriptions should be detailed, including appearance, expressions, actions
4. Visual descriptions should be suitable for AI painting, including composition, lighting, style
5. Output format should be JSON with shots array

Text Content:
{text}

Style Requirements: {style}

Please generate the storyboard table:
"""
            },
            
            TemplateType.PROMPT_OPTIMIZATION: {
                LanguageCode.CHINESE: """
请优化以下AI绘画提示词，要求：
1. 更加详细和具体
2. 包含艺术风格描述
3. 包含技术参数建议
4. 适合Stable Diffusion等模型

原提示词：
{prompt}

风格：{style}

优化后的提示词：
""",
                LanguageCode.ENGLISH: """
Please optimize the following AI painting prompt with requirements:
1. More detailed and specific
2. Include artistic style descriptions
3. Include technical parameter suggestions
4. Suitable for Stable Diffusion and similar models

Original Prompt:
{prompt}

Style: {style}

Optimized Prompt:
"""
            },
            
            TemplateType.TEXT_TRANSLATION: {
                LanguageCode.CHINESE: """
你是一位专业的翻译专家。请根据以下要求进行翻译：

翻译任务：将提供的文本翻译为中文

翻译要求：
1. 准确传达原文的核心意思和情感色彩
2. 使用自然流畅的中文表达
3. 保持原文的段落结构和逻辑层次
4. 对于专业术语，使用准确的中文对应词汇
5. 确保译文符合中文表达习惯

输出要求：
- 只输出翻译后的中文文本
- 不要添加任何解释、注释或格式标记
- 保持原文的自然段落分隔

原文：
{source_text}

中文译文：
""",
                LanguageCode.ENGLISH: """
You are a professional translation expert. Please translate according to the following requirements:

Translation Task: Translate the provided text into English

Translation Requirements:
1. Accurately convey the core meaning and emotional tone of the original text
2. Use natural and fluent English expressions
3. Preserve the paragraph structure and logical hierarchy of the original text
4. Use accurate English equivalents for technical terms
5. Ensure the translation conforms to native English speaker expression habits

Output Requirements:
- Output only the translated English text
- Do not add any explanations, annotations, or format markers
- Maintain the natural paragraph separation of the original text

Original Text:
{source_text}

English Translation:
"""
            }
        }
    
    def get_template(self, template_type: TemplateType, language: LanguageCode) -> Optional[str]:
        """
        获取指定类型和语言的模板
        
        Args:
            template_type: 模板类型
            language: 语言代码
            
        Returns:
            Optional[str]: 模板字符串，如果不存在则返回None
        """
        try:
            templates_for_type = self._templates.get(template_type, {})
            template = templates_for_type.get(language)
            
            if template is None:
                # 如果指定语言的模板不存在，尝试使用中文模板作为后备
                template = templates_for_type.get(LanguageCode.CHINESE)
                if template is not None:
                    logger.warning(f"未找到 {language.value} 的 {template_type.value} 模板，使用中文模板作为后备")
            
            return template
            
        except Exception as e:
            logger.error(f"获取模板失败: {template_type.value}, {language.value}, 错误: {e}")
            return None
    
    def format_template(self, template_type: TemplateType, language: LanguageCode, **kwargs) -> Optional[str]:
        """
        格式化模板
        
        Args:
            template_type: 模板类型
            language: 语言代码
            **kwargs: 模板参数
            
        Returns:
            Optional[str]: 格式化后的模板字符串
        """
        try:
            template = self.get_template(template_type, language)
            if template is None:
                logger.error(f"未找到模板: {template_type.value}, {language.value}")
                return None
            
            formatted_template = template.format(**kwargs)
            logger.debug(f"模板格式化成功: {template_type.value}, {language.value}")
            return formatted_template
            
        except KeyError as e:
            logger.error(f"模板参数缺失: {e}")
            return None
        except Exception as e:
            logger.error(f"模板格式化失败: {e}")
            return None
    
    def add_custom_template(self, template_type: TemplateType, language: LanguageCode, template: str) -> bool:
        """
        添加自定义模板
        
        Args:
            template_type: 模板类型
            language: 语言代码
            template: 模板字符串
            
        Returns:
            bool: 添加是否成功
        """
        try:
            if template_type not in self._templates:
                self._templates[template_type] = {}
            
            self._templates[template_type][language] = template
            logger.info(f"自定义模板添加成功: {template_type.value}, {language.value}")
            return True
            
        except Exception as e:
            logger.error(f"添加自定义模板失败: {e}")
            return False
    
    def get_available_template_types(self) -> list[TemplateType]:
        """
        获取可用的模板类型列表
        
        Returns:
            list[TemplateType]: 模板类型列表
        """
        return list(self._templates.keys())
    
    def get_supported_languages_for_template(self, template_type: TemplateType) -> list[LanguageCode]:
        """
        获取指定模板类型支持的语言列表
        
        Args:
            template_type: 模板类型
            
        Returns:
            list[LanguageCode]: 支持的语言列表
        """
        templates_for_type = self._templates.get(template_type, {})
        return list(templates_for_type.keys())
    
    def validate_template_parameters(self, template_type: TemplateType, language: LanguageCode, **kwargs) -> Dict[str, bool]:
        """
        验证模板参数
        
        Args:
            template_type: 模板类型
            language: 语言代码
            **kwargs: 要验证的参数
            
        Returns:
            Dict[str, bool]: 参数验证结果
        """
        try:
            template = self.get_template(template_type, language)
            if template is None:
                return {"template_exists": False}
            
            # 尝试格式化模板以检查参数
            try:
                template.format(**kwargs)
                return {"template_exists": True, "parameters_valid": True}
            except KeyError as e:
                return {
                    "template_exists": True, 
                    "parameters_valid": False, 
                    "missing_parameter": str(e)
                }
                
        except Exception as e:
            logger.error(f"验证模板参数失败: {e}")
            return {"template_exists": False, "error": str(e)}
    
    def get_debug_info(self) -> Dict[str, any]:
        """获取调试信息"""
        return {
            "template_types": [t.value for t in self._templates.keys()],
            "template_count": {
                template_type.value: len(templates) 
                for template_type, templates in self._templates.items()
            },
            "supported_languages": list(set(
                lang.value 
                for templates in self._templates.values() 
                for lang in templates.keys()
            ))
        }