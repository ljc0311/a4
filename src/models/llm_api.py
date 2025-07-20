import requests
import json
import time
import re
from typing import Dict, Union, List
import logging
import jieba



class LLMApi:
    def __init__(self, api_type: str, api_key: str, api_url: str):
        # Add debug logging to check received parameters
        print(f"DEBUG LLMApi.__init__: Received api_type={api_type}, api_key={api_key}, api_url={api_url}")
        logger.debug(f"DEBUG LLMApi.__init__: Received api_type={api_type}, api_key={api_key}, api_url={api_url}")

        self.api_type = api_type.lower()
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')

        # 为不同任务确定模型名称
        if self.api_type == "deepseek":
            self.shots_model_name = "deepseek-chat"
            self.rewrite_model_name = "deepseek-chat"
        elif self.api_type == "tongyi":
            self.shots_model_name = "qwen-plus"
            self.rewrite_model_name = "qwen-plus"
        elif self.api_type == "zhipu":
            self.shots_model_name = "glm-4-flash"
            self.rewrite_model_name = "glm-4-flash"
        elif self.api_type == "google":
            self.shots_model_name = "gemini-1.5-flash"
            self.rewrite_model_name = "gemini-1.5-flash"
        else:
            # print(f"警告 (LLMApi __init__): 未知的 api_type '{self.api_type}'。将尝试使用 deepseek-chat 作为默认模型。")
            self.shots_model_name = "deepseek-chat"
            self.rewrite_model_name = "deepseek-chat"

        # 初始化jieba分词，确保只加载一次
        try:
            jieba.initialize()
            logger.info("Jieba分词模型初始化成功。")
        except Exception as e:
            logger.error(f"Jieba分词模型初始化失败: {e}")
        
        # 文本分段配置 - 优化参数以平衡分镜密度和处理效率
        self.max_text_length = 800   # 单次处理的最大文本长度，适中的分段大小
        self.overlap_length = 150    # 分段重叠长度，保证上下文连贯性
        self.summary_threshold = 3000  # 摘要阈值，超过此长度才生成摘要

        # 🔧 新增：模型轮换机制
        self.model_failure_count = {}  # 记录每个模型的失败次数
        self.max_failures_per_model = 2  # 每个模型最大失败次数
        self.current_model_index = 0  # 当前使用的模型索引
        self.available_models = self._load_available_models()
        self.current_model_config = self._get_current_model_config()
    
    def is_configured(self) -> bool:
        """检查LLM API是否已正确配置"""
        return bool(self.api_key and self.api_url and self.api_type)

    def _load_available_models(self):
        """加载所有可用的模型配置"""
        try:
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            models = config_manager.get_models()

            available_models = []
            for model in models:
                if model.get('key') and model.get('url'):  # 只加载有效配置的模型
                    available_models.append({
                        'name': model.get('name', ''),
                        'type': model.get('type', ''),
                        'key': model.get('key', ''),
                        'url': model.get('url', ''),
                        'enabled': model.get('enabled', True)
                    })

            logger.info(f"🔄 加载了 {len(available_models)} 个可用模型: {[m['name'] for m in available_models]}")
            return available_models

        except Exception as e:
            logger.error(f"加载可用模型失败: {e}")
            return []

    def _get_current_model_config(self):
        """获取当前模型配置"""
        if not self.available_models:
            return None

        if self.current_model_index >= len(self.available_models):
            self.current_model_index = 0

        return self.available_models[self.current_model_index]

    def _switch_to_next_model(self):
        """切换到下一个可用模型"""
        if len(self.available_models) <= 1:
            logger.warning("⚠️ 只有一个模型可用，无法切换")
            return False

        old_model = self.current_model_config
        self.current_model_index = (self.current_model_index + 1) % len(self.available_models)
        self.current_model_config = self._get_current_model_config()

        if self.current_model_config:
            # 更新当前实例的配置
            self.api_type = self.current_model_config['type'].lower()
            self.api_key = self.current_model_config['key']
            self.api_url = self.current_model_config['url'].rstrip('/')

            # 更新模型名称
            self._update_model_names()

            logger.info(f"🔄 模型切换: {old_model['name'] if old_model else 'Unknown'} → {self.current_model_config['name']}")
            return True

        return False

    def _update_model_names(self):
        """根据当前API类型更新模型名称"""
        if self.api_type == "deepseek":
            self.shots_model_name = "deepseek-chat"
            self.rewrite_model_name = "deepseek-chat"
        elif self.api_type == "tongyi":
            self.shots_model_name = "qwen-plus"
            self.rewrite_model_name = "qwen-plus"
        elif self.api_type == "zhipu":
            self.shots_model_name = "glm-4-flash"
            self.rewrite_model_name = "glm-4-flash"
        elif self.api_type == "google":
            self.shots_model_name = "gemini-1.5-flash"
            self.rewrite_model_name = "gemini-1.5-flash"
        else:
            self.shots_model_name = "deepseek-chat"
            self.rewrite_model_name = "deepseek-chat"

    def _record_model_failure(self, model_name):
        """记录模型失败次数"""
        if model_name not in self.model_failure_count:
            self.model_failure_count[model_name] = 0

        self.model_failure_count[model_name] += 1
        logger.warning(f"⚠️ 模型 {model_name} 失败次数: {self.model_failure_count[model_name]}/{self.max_failures_per_model}")

        # 如果失败次数达到阈值，尝试切换模型
        if self.model_failure_count[model_name] >= self.max_failures_per_model:
            logger.error(f"❌ 模型 {model_name} 连续失败 {self.max_failures_per_model} 次，尝试切换模型")
            if self._switch_to_next_model():
                # 重置新模型的失败计数
                new_model_name = self.current_model_config['name']
                self.model_failure_count[new_model_name] = 0
                return True

        return False

    def _reset_model_failure_count(self, model_name):
        """重置模型失败计数"""
        if model_name in self.model_failure_count:
            self.model_failure_count[model_name] = 0

    def get_current_model_info(self):
        """获取当前模型信息"""
        if self.current_model_config:
            return {
                'name': self.current_model_config['name'],
                'type': self.current_model_config['type'],
                'failure_count': self.model_failure_count.get(self.current_model_config['name'], 0)
            }
        return {'name': 'Unknown', 'type': self.api_type, 'failure_count': 0}

    def _is_error_response(self, response):
        """检查响应是否为错误响应"""
        if not response:
            return True

        if isinstance(response, str):
            error_patterns = [
                'api错误', 'api密钥', 'network error', 'timeout error',
                'invalid api key', '请求超时', '网络错误', '调用失败',
                'api调用失败', '未知错误', '请稍后重试', '连接超时',
                '所有模型都失败', 'API请求失败'
            ]
            response_lower = response.lower()
            return any(pattern in response_lower for pattern in error_patterns)

        return False

    def _split_text_intelligently(self, text: str) -> list:
        """
        智能分段文本，优先按段落、句子分割，避免截断句子
        增加重叠度处理，确保上下文连贯性
        返回分段后的文本列表
        """
        if len(text) <= self.max_text_length:
            return [text]
            
        segments = []
        current_pos = 0
        
        while current_pos < len(text):
            # 计算当前段的结束位置
            end_pos = min(current_pos + self.max_text_length, len(text))
            
            if end_pos == len(text):
                # 最后一段，直接添加
                segments.append(text[current_pos:end_pos])
                break
            
            # 寻找合适的分割点
            segment_text = text[current_pos:end_pos]
            
            # 优先级1: 寻找段落分隔符（双换行）
            paragraph_split = segment_text.rfind('\n\n')
            if paragraph_split > self.max_text_length * 0.2:  # 大幅降低最小分段比例
                split_pos = current_pos + paragraph_split + 2
                segments.append(text[current_pos:split_pos])
                current_pos = max(current_pos + 1, split_pos - self.overlap_length)
                continue
                
            # 优先级2: 寻找句子结束符
            sentence_endings = ['。', '！', '？', '.', '!', '?']
            best_split = -1
            for i in range(len(segment_text) - 1, int(len(segment_text) * 0.2), -1):  # 大幅降低最小比例
                if segment_text[i] in sentence_endings:
                    best_split = i + 1
                    break
                    
            if best_split > 0:
                split_pos = current_pos + best_split
                segments.append(text[current_pos:split_pos])
                current_pos = max(current_pos + 1, split_pos - self.overlap_length)
                continue
                 
            # 优先级3: 寻找标点符号
            punctuation = ['，', '；', '：', ',', ';', ':']
            best_split = -1
            for i in range(len(segment_text) - 1, int(len(segment_text) * 0.2), -1):  # 大幅降低最小比例
                if segment_text[i] in punctuation:
                    best_split = i + 1
                    break
                    
            if best_split > 0:
                split_pos = current_pos + best_split
                segments.append(text[current_pos:split_pos])
                current_pos = max(current_pos + 1, split_pos - self.overlap_length)
                continue
                 
            # 优先级4: 寻找空格
            space_split = segment_text.rfind(' ')
            if space_split > self.max_text_length * 0.2:  # 大幅降低最小比例
                split_pos = current_pos + space_split + 1
                segments.append(text[current_pos:split_pos])
                current_pos = max(current_pos + 1, split_pos - self.overlap_length)
                continue
                
            # 最后选择：强制分割
            segments.append(text[current_pos:end_pos])
            current_pos = max(current_pos + 1, end_pos - self.overlap_length)
        
        return segments
    
    def _rewrite_text_with_segments(self, text: str, progress_callback=None) -> str:
        """
        分段改写文本
        """
        logger.info("[文本改写] 开始分段改写文本")
        segments = self._smart_split_text(text)
        logger.info(f"[文本改写] 文本分为 {len(segments)} 段进行改写")
        
        rewritten_segments = []
        for i, segment in enumerate(segments):
            if progress_callback:
                progress_callback(f"正在改写第 {i+1}/{len(segments)} 段")
            
            rewritten_segment = self._rewrite_single_text(segment)
            rewritten_segments.append(rewritten_segment)
            
        result = '\n\n'.join(rewritten_segments)
        logger.info(f"[文本改写] 分段改写完成，改写后文本长度: {len(result)}")
        return result
    
    def _rewrite_single_text(self, text: str) -> str:
        """
        改写单段文本
        """
        system_prompt = """
你是一个专业的文本改写助手。请按照以下要求改写文本：

1. 保留原文的核心思想和主要信息
2. 改写后的文本长度应与原文基本一致
3. 使用更加生动、具体的表达方式
4. 保持文本的逻辑结构和段落划分
5. 确保改写后的文本流畅自然
6. 只输出改写后的文本内容，不要添加任何解释或说明
"""
        
        user_prompt = f"请改写以下文本：\n\n{text}"
        
        try:
            response = self._make_api_call(system_prompt, user_prompt)
            
            # 处理返回结果
            if isinstance(response, str):
                return response.strip()
            elif isinstance(response, dict) and 'content' in response:
                return response['content'].strip()
            else:
                logger.error(f"改写文本时收到意外的响应格式: {type(response)}")
                return text  # 返回原文本作为备选
                
        except Exception as e:
            logger.error(f"改写文本时发生错误: {str(e)}")
            return text  # 返回原文本作为备选
    
    def generate_shots(self, text: str, progress_callback=None) -> List[Dict]:
        """
        生成分镜脚本
        """
        logger.info(f"[分镜生成] 开始处理，原文本长度: {len(text)}")
        
        # 检查文本长度，决定处理策略
        if len(text) > self.max_text_length:
            logger.info(f"[分镜生成] 文本长度 {len(text)} 超过限制 {self.max_text_length}，启用分段生成分镜")
            if progress_callback:
                progress_callback(f"文本过长({len(text)}字符)，启用智能分段生成分镜")
            return self._generate_shots_with_segments(text, progress_callback)
        
        # 正常处理流程
        if progress_callback:
            progress_callback("文本长度适中，使用标准分镜生成流程")
        return self._generate_single_shots(text)
    
    def _smart_split_text(self, text: str) -> list:
        """
        智能分段文本，优先按段落、句子分割，避免截断句子
        增加重叠度处理，确保上下文连贯性
        返回分段后的文本列表
        """
        if len(text) <= self.max_text_length:
            return [text]
            
        segments = []
        current_pos = 0
        
        while current_pos < len(text):
            # 计算当前段的结束位置
            end_pos = min(current_pos + self.max_text_length, len(text))
            
            if end_pos == len(text):
                # 最后一段，直接添加
                segments.append(text[current_pos:end_pos])
                break
            
            # 寻找合适的分割点
            segment_text = text[current_pos:end_pos]
            
            # 优先级1: 寻找段落分隔符（双换行）
            paragraph_split = segment_text.rfind('\n\n')
            if paragraph_split > self.max_text_length * 0.2:  # 大幅降低最小分段比例
                split_pos = current_pos + paragraph_split + 2
                segments.append(text[current_pos:split_pos])
                current_pos = max(current_pos + 1, split_pos - self.overlap_length)
                continue
                
            # 优先级2: 寻找句子结束符
            sentence_endings = ['。', '！', '？', '.', '!', '?']
            best_split = -1
            for i in range(len(segment_text) - 1, int(len(segment_text) * 0.2), -1):  # 大幅降低最小比例
                if segment_text[i] in sentence_endings:
                    best_split = i + 1
                    break
                    
            if best_split > 0:
                split_pos = current_pos + best_split
                segments.append(text[current_pos:split_pos])
                current_pos = max(current_pos + 1, split_pos - self.overlap_length)
                continue
                 
            # 优先级3: 寻找标点符号
            punctuation = ['，', '；', '：', ',', ';', ':']
            best_split = -1
            for i in range(len(segment_text) - 1, int(len(segment_text) * 0.2), -1):  # 大幅降低最小比例
                if segment_text[i] in punctuation:
                    best_split = i + 1
                    break
                    
            if best_split > 0:
                split_pos = current_pos + best_split
                segments.append(text[current_pos:split_pos])
                current_pos = max(current_pos + 1, split_pos - self.overlap_length)
                continue
                 
            # 优先级4: 寻找空格
            space_split = segment_text.rfind(' ')
            if space_split > self.max_text_length * 0.2:  # 大幅降低最小比例
                split_pos = current_pos + space_split + 1
                segments.append(text[current_pos:split_pos])
                current_pos = max(current_pos + 1, split_pos - self.overlap_length)
                continue
                
            # 最后选择：强制分割
            segments.append(text[current_pos:end_pos])
            current_pos = max(current_pos + 1, end_pos - self.overlap_length)
        
        return segments

    def _merge_rewritten_segments(self, segments: list) -> str:
        """
        合并改写后的文本段落，处理重叠部分
        """
        if not segments:
            return ""
        if len(segments) == 1:
            return segments[0]
            
        merged_text = segments[0]
        
        for i in range(1, len(segments)):
            current_segment = segments[i]
            
            # 简单合并，添加适当的分隔
            if not merged_text.endswith('\n'):
                merged_text += '\n'
            merged_text += current_segment
            
        # 去除多余的空行，保留段落间的单个换行
        lines = merged_text.split('\n')
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped:  # 非空行
                cleaned_lines.append(line)
                prev_empty = False
            else:  # 空行
                if not prev_empty:  # 只保留第一个空行
                    cleaned_lines.append('')
                prev_empty = True
        
        # 移除开头和结尾的空行
        while cleaned_lines and not cleaned_lines[0].strip():
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
            
        return '\n'.join(cleaned_lines)

    def _remove_series_descriptions(self, text: str) -> str:
        """
        移除改写文本中可能出现的系列描述文本
        """
        if not text:
            return text
            
        # 定义需要移除的系列描述模式
        patterns_to_remove = [
            r'本篇系长篇故事的第.{1,20}篇章[，。].*?[。！？]',
            r'本篇系长文第.{1,20}篇[，。].*?[。！？]', 
            r'本篇为系列长文之第.{1,20}篇章[，。].*?[。！？]',
            r'这是一篇长文本的第.{1,20}部分[，。].*?[。！？]',
            r'本文为.{1,30}系列.*?第.{1,20}部分[，。].*?[。！？]',
            r'此为.{1,30}长篇.*?第.{1,20}章[，。].*?[。！？]'
        ]
        
        import re
        cleaned_text = text
        
        for pattern in patterns_to_remove:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.DOTALL)
        
        # 清理可能产生的多余空行
        lines = cleaned_text.split('\n')
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped:  # 非空行
                cleaned_lines.append(line)
                prev_empty = False
            else:  # 空行
                if not prev_empty:  # 只保留第一个空行
                    cleaned_lines.append('')
                prev_empty = True
        
        # 移除开头和结尾的空行
        while cleaned_lines and not cleaned_lines[0].strip():
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
            
        return '\n'.join(cleaned_lines)

    def _remove_extra_blank_lines(self, text: str) -> str:
        """
        去除文本中多余的空行，保留段落间的单个换行
        """
        if not text:
            return text
            
        lines = text.split('\n')
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped:  # 非空行
                cleaned_lines.append(line)
                prev_empty = False
            else:  # 空行
                if not prev_empty:  # 只保留第一个空行
                    cleaned_lines.append('')
                prev_empty = True
        
        # 移除开头和结尾的空行
        while cleaned_lines and not cleaned_lines[0].strip():
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
            
        return '\n'.join(cleaned_lines)

    def _make_api_call(self, model_name: str, messages: list, task_name: str) -> Union[str, dict, None]:
        """
        通用 API 调用方法，带重试机制和模型轮换。
        返回 message.content 的内容，可能是 str, dict, 或 None。
        出错时返回错误描述字符串。
        """
        # 🔧 新增：获取当前模型信息用于日志
        current_model_info = self.get_current_model_info()
        logger.info(f"🤖 使用模型: {current_model_info['name']} ({current_model_info['type']}) - 任务: {task_name}")

        # 🔧 新增：模型轮换重试机制
        max_model_switches = len(self.available_models) if self.available_models else 1
        model_switch_count = 0

        while model_switch_count < max_model_switches:
            try:
                # 尝试使用当前模型进行API调用
                result = self._single_model_api_call(model_name, messages, task_name)

                # 如果成功，重置失败计数并返回结果
                if result and not self._is_error_response(result):
                    current_model_name = self.current_model_config['name'] if self.current_model_config else 'Unknown'
                    self._reset_model_failure_count(current_model_name)
                    logger.info(f"✅ 模型 {current_model_name} API调用成功")
                    return result

                # 如果失败，记录失败并可能切换模型
                current_model_name = self.current_model_config['name'] if self.current_model_config else 'Unknown'
                logger.error(f"❌ 模型 {current_model_name} API调用失败: {result}")

                # 记录失败并检查是否需要切换模型
                if self._record_model_failure(current_model_name):
                    model_switch_count += 1
                    logger.info(f"🔄 已切换到模型 {self.current_model_config['name']}，继续重试...")
                    continue
                else:
                    # 如果没有切换模型，直接返回错误
                    return result

            except Exception as e:
                current_model_name = self.current_model_config['name'] if self.current_model_config else 'Unknown'
                logger.error(f"❌ 模型 {current_model_name} 调用异常: {e}")

                # 记录失败并检查是否需要切换模型
                if self._record_model_failure(current_model_name):
                    model_switch_count += 1
                    if model_switch_count < max_model_switches:
                        logger.info(f"🔄 已切换到模型 {self.current_model_config['name']}，继续重试...")
                        continue

                # 如果所有模型都尝试过了，返回最后的错误
                return f"所有模型都失败了，最后错误: {str(e)}"

        # 如果所有模型都尝试过了，返回失败信息
        return "所有可用模型都已尝试，API调用失败"

    def _single_model_api_call(self, model_name: str, messages: list, task_name: str) -> Union[str, dict, None]:
        """
        单个模型的API调用方法（不包含重试逻辑，由模型轮换机制处理重试）
        """
        # 根据API类型设置不同的请求格式
        if self.api_type == "google":
            headers = {"Content-Type": "application/json"}
            # Google API使用API key作为查询参数
            full_url = f"{self.api_url}?key={self.api_key}"
            # 转换消息格式为Google Gemini格式
            contents = []
            for msg in messages:
                if msg["role"] == "user":
                    contents.append({"parts": [{"text": msg["content"]}]})
                elif msg["role"] == "assistant":
                    contents.append({"parts": [{"text": msg["content"]}]})
            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 2048
                }
            }
        else:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model_name,
                "messages": messages
            }

            # 智能构建URL - 如果已包含endpoint则直接使用，否则添加
            if self.api_url.endswith('/chat/completions'):
                full_url = self.api_url
            else:
                endpoint = "/chat/completions"
                full_url = f"{self.api_url.rstrip('/')}{endpoint}"

        # 根据任务类型设置不同的超时时间
        if "storyboard" in task_name.lower() or task_name == "generate_shots" or task_name == "generate_shots_summary":
            timeout = 120    # 分镜生成需要更长时间
        else:
            timeout = 60     # 其他任务保持原有超时时间

        # 🔧 修复：单次API调用，不包含重试逻辑
        try:
            logger.info(f"🚀 开始单次API调用 ({task_name})，URL: {full_url}")
            logger.debug(f"API请求payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")

            # 为本地服务禁用代理，外部API使用系统代理
            proxies = {"http": None, "https": None} if "127.0.0.1" in full_url or "localhost" in full_url else None
            resp = requests.post(full_url, json=payload, headers=headers, timeout=timeout, proxies=proxies)

            logger.info(f"API请求已发送，状态码: {resp.status_code}")
            resp.raise_for_status()
            logger.info(f"API响应状态正常，开始解析JSON")

            response_data = resp.json()
            logger.info(f"JSON解析成功，响应数据长度: {len(str(response_data))}")

            # 根据API类型解析不同的响应格式
            if self.api_type == "google":
                # Google Gemini API响应格式
                if response_data and "candidates" in response_data and len(response_data["candidates"]) > 0:
                    candidate = response_data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        content = candidate["content"]["parts"][0].get("text")

                        # 验证API密钥是否有效
                        if content and "invalid api key" in content.lower():
                            return f"API密钥无效，请检查配置"

                        logger.debug(f"✅ API调用成功 ({task_name}). 完整响应数据: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
                        logger.debug(f"✅ API调用成功 ({task_name}). 提取内容: {content}")
                        return content
                return f"Google API响应格式不正确"
            else:
                # OpenAI格式的API响应
                if response_data and "choices" in response_data and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0].get("message", {})
                    content = message.get("content")

                    # 验证API密钥是否有效
                    if content and "invalid api key" in content.lower():
                        return f"API密钥无效，请检查配置"

                    logger.debug(f"✅ API调用成功 ({task_name}). 完整响应数据: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
                    logger.debug(f"✅ API调用成功 ({task_name}). 提取内容: {content}")
                    return content
                else:
                    return f"API响应格式不正确"

        except requests.exceptions.Timeout as e:
            logger.error(f"❌ API调用超时异常 ({task_name}): {str(e)}")
            return f"请求超时，请检查网络连接后重试"
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.error(f"❌ API调用请求异常 ({task_name}): {error_msg}")
            import traceback
            logger.error(f"请求异常堆栈: {traceback.format_exc()}")
            if "401" in error_msg:
                return f"API密钥验证失败，请检查配置"
            elif "invalid api key" in error_msg.lower():
                return f"API密钥无效，请检查配置"
            else:
                return f"网络错误: {error_msg}"
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析异常 ({task_name}): {str(e)}")
            import traceback
            logger.error(f"JSON解析异常堆栈: {traceback.format_exc()}")
            return f"API响应解析错误: {e}"
        except KeyboardInterrupt as e:
            logger.error(f"❌ 用户中断异常 ({task_name}): {str(e)}")
            return "操作被用户中断"
        except SystemExit as e:
            logger.error(f"❌ 系统退出异常 ({task_name}): {str(e)}")
            return f"API调用因SystemExit失败: {e}"
        except Exception as e:
            logger.error(f"❌ 未知异常 ({task_name}): {str(e)}")
            logger.error(f"异常类型: {type(e).__name__}")
            import traceback
            logger.error(f"未知异常堆栈: {traceback.format_exc()}")
            return f"未知错误: {e}"


    def generate_shots(self, text: str, style: str = '电影风格', progress_callback=None) -> str:
        # 检查文本长度，决定是否需要分段处理
        if len(text) > self.max_text_length:
            print(f"文本长度 {len(text)} 超过限制 {self.max_text_length}，启用分段处理生成分镜")
            if progress_callback:
                progress_callback(f"文本过长({len(text)}字符)，启用智能分段处理")
            return self._generate_shots_with_segments(text, style, progress_callback)
        
        # 正常处理流程
        if progress_callback:
            progress_callback("文本长度适中，使用标准处理流程")
        return self._generate_single_shots(text, style)
    
    def _generate_single_shots(self, text: str, style: str = None) -> str:
        """处理单个文本段的分镜生成"""
        # 根据风格生成对应的画风描述
        style_descriptions = {
            '电影风格': '电影感，超写实，4K，胶片颗粒，景深',
            '动漫风格': '动漫风，鲜艳色彩，干净线条，赛璐璐渲染，日本动画',
            '吉卜力风格': '吉卜力风，柔和色彩，奇幻，梦幻，丰富背景',
            '赛博朋克风格': '赛博朋克，霓虹灯，未来都市，雨夜，暗色氛围',
            '水彩插画风格': '水彩画风，柔和笔触，粉彩色，插画，温柔',
            '像素风格': '像素风，8位，复古，低分辨率，游戏风',
            '写实摄影风格': '真实光线，高细节，写实摄影，4K'
        }
        
        # 如果没有传入风格，使用默认的电影风格
        if style is None:
            style = '电影风格'
        current_style_desc = style_descriptions.get(style, style_descriptions['电影风格'])
        
        system_prompt_shots = (
            "你是一个专业的视频分镜师。请根据用户提供的文本内容，生成详细的视频分镜脚本。\n"
            "请严格按照以下Markdown表格格式输出，不要包含任何额外文字、解释或说明。\n"
            "表格必须包含以下列：文案、场景、角色、提示词、主图、视频运镜、音频、操作、备选图片。\n"
            "\n"
            "**核心要求：必须严格按照用户提供的原文内容进行分镜，不得遗漏任何内容！**\n"
            "\n"
            "**重要要求：请为文本内容生成尽可能多的分镜场景。每个重要的情节、对话、动作、情感变化都应该有对应的分镜。不要将多个场景合并到一个分镜中，而是要详细拆分。**\n"
            "\n"
            "**分镜数量指导原则（必须严格遵守）：**\n"
            "- 每25-40字的文本内容应该生成1个分镜场景，确保镜头原文长度适中\n"
            "- 每个对话回合必须有独立的分镜\n"
            "- 每个动作或情感变化必须有独立的分镜\n"
            "- 场景转换必须有独立的分镜\n"
            "- 长句子（超过45字）应拆分为多个分镜，在自然断句处分割\n"
            "- 短句子（少于25字）可适当合并，但合并后不超过40字\n"
            "- 优先保证镜头长度合理，同时确保内容完整覆盖\n"
            "\n"
            "**内容完整性要求（必须严格遵守）：**\n"
            "- 必须覆盖用户提供文本的所有内容，从第一段到最后一段，不得遗漏任何段落或情节\n"
            "- 按照文本的时间顺序生成分镜，确保逻辑连贯\n"
            "- 对于长文本，请特别注意中间部分和后半部分内容的分镜生成\n"
            "- 生成分镜前，请先通读全文，确保理解了文本的完整结构和所有内容\n"
            "- 文案列中的内容必须直接来源于原文，不能自行创作或概括\n"
            "\n"
            "请注意以下生成规则：\n"
            "1. **文案列**: 必须从用户提供的原始文本中提取相应的文案片段，每个分镜的文案应该控制在25-45个字符之间，保持自然语言风格。文案应该能够直接对应到原文的具体段落或句子。绝对不能填写1、2、3等数字！优先在句号、感叹号、问号处分割，其次在逗号、分号处分割，确保语义完整。\n"
            "2. **分镜数量**: 根据文本内容的丰富程度，生成足够多的分镜。确保每个重要情节都有对应的分镜，不要遗漏任何内容。\n"
            "3. **分镜 (场景和视频运镜)**: 必须根据'文案'的文本内容，生成具体、详细且富有画面感的场景描述和视频运镜。确保分镜与文案内容紧密关联，能够直接转化为视觉画面。场景描述应具体到地点、时间、环境细节等。视频运镜应描述镜头如何运动，如推拉摇移、特写、全景等。\n"
            "4. **角色**: 从'文案'中准确提取所有主要角色和次要角色，并列出其具体名称或明确的身份描述（例如：'光头摊主'、'主角'、'路人甲'）。严禁使用'通用角色'等模糊描述。如果文案中没有明确的角色，请根据上下文合理推断并给出具体描述。\n"

            f"5. **提示词**: 结合'文案'、生成的分镜（场景、视频运镜、主图）以及提取的'角色'，综合生成一个详细的、用于图像或视频生成的提示词。提示词应包含以下要素：\n"
            "   - **场景描述**: 详细描述画面背景、环境、光线、氛围等。\n"
            "   - **角色描述**: 详细描述角色的外貌、服装、表情、动作、情绪等。\n"
            f"   - **画风要求**: 必须使用指定的画风风格：{current_style_desc}。\n"
            "   - **技术细节**: 包含分辨率（如'4K'）、画面质感等。\n"
            "   - **其他视觉元素**: 任何有助于AI生成高质量视觉内容的细节。\n"
            "   确保提示词能够直接指导AI生成与分镜内容高度匹配的视觉内容。\n"
            "\n"
            "示例（注意文案长度控制在25-45字之间）：\n"
            "| 文案 | 场景 | 角色 | 提示词 | 主图 | 视频运镜 | 音频 | 操作 | 备选图片 |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            f"| 我在那座冰冷的牢狱中度过了整整七年。 | 监狱内部，昏暗的牢房，主角独自坐在床边。 | 主角 | 监狱牢房内，主角（穿着囚服，神情沧桑）独自坐在简陋的床边，透过铁窗看向外面。{current_style_desc}。 |  | 镜头从牢房外推进，展现主角孤独的身影和沧桑的面容。 | 背景音效为监狱的嘈杂声和铁门声。 | 无 |  |\n"
            f"| 最终因表现良好而获得减刑。 | 监狱办公室，狱警宣布减刑消息。 | 主角, 狱警 | 监狱办公室内，狱警（中年男性，制服整齐）向主角宣布减刑决定，主角神情激动。{current_style_desc}。 |  | 镜头特写狱警的嘴部，然后切换到主角惊喜的表情。 | 背景音效为狱警的宣读声和纸张翻动声。 | 无 |  |\n"
            f"| 重获自由的第一天，电话铃声此起彼伏。 | 监狱大门外，阳光刺眼，主角接听电话。 | 主角 | 刚刚出狱的主角（穿着简单的休闲装，神情略显疲惫）站在监狱门外，手持老式翻盖手机，不断接听电话。{current_style_desc}。 |  | 镜头从监狱大门推出，展现主角接听电话的动作。 | 背景音效为电话铃声和轻微的风声。 | 无 |  |\n"
            "\n"
            "请开始生成：\n"
        )
        messages = [{"role": "system", "content": system_prompt_shots}, {"role": "user", "content": text}]
        content_result = self._make_api_call(self.shots_model_name, messages, "generate_shots")

        logger.debug(f"_make_api_call returned in generate_shots: {content_result[:500] if isinstance(content_result, str) else content_result}")

        if isinstance(content_result, str):
            return content_result
        elif isinstance(content_result, dict):
            # print(f"警告 (generate_shots): API为分镜任务直接返回了字典，将序列化为JSON字符串。") # 你可以取消注释进行调试
            return json.dumps(content_result, ensure_ascii=False, indent=2)
        return content_result if content_result is not None else "API错误 (generate_shots): 未收到有效内容。"
    
    def _generate_shots_with_segments(self, text: str, style: str = None, progress_callback=None) -> str:
        """分段处理超长文本的分镜生成"""
        # 如果没有传入风格，使用默认的电影风格
        if style is None:
            style = '电影风格'
        print(f"[分镜生成] 开始分段生成分镜，原文本长度: {len(text)}")
        logger.info(f"[分镜生成] 开始分段生成分镜，原文本长度: {len(text)}")
        
        # 智能分段
        segments = self._smart_split_text(text)
        print(f"[分镜生成] 文本已分为 {len(segments)} 段，准备生成分镜")
        logger.info(f"[分镜生成] 文本已分为 {len(segments)} 段，准备生成分镜")
        
        if progress_callback:
            progress_callback(f"文本已分为 {len(segments)} 段，正在生成分镜摘要...")
        
        # 优化：只有文本长度超过阈值时才生成摘要，减少不必要的API调用
        summary_text = ""
        if len(text) > self.summary_threshold:
            # 对于超长文本，生成摘要以便大模型理解整体内容
            summary_prompt = (
                "请对以下文本进行简要概括，提取出主要情节、人物和场景，以便后续生成分镜。\n\n"
                f"文本内容：\n{text[:2000]}...（文本过长已省略）"
            )
            
            summary_messages = [
                {"role": "system", "content": "你是一个专业的文本摘要专家，擅长提取文本的核心内容和主要情节。"},
                {"role": "user", "content": summary_prompt}
            ]
            
            summary_result = self._make_api_call(self.shots_model_name, summary_messages, "generate_shots_summary")
            print(f"[分镜生成] 分镜摘要生成完成，长度: {len(summary_result) if isinstance(summary_result, str) else 0}")
            logger.info(f"[分镜生成] 分镜摘要生成完成，长度: {len(summary_result) if isinstance(summary_result, str) else 0}")
            
            if not isinstance(summary_result, str) or summary_result.startswith("API错误"):
                print("[分镜生成] 分镜摘要生成失败，将直接处理分段")
                logger.warning("[分镜生成] 分镜摘要生成失败，将直接处理分段")
                summary_text = ""  # 摘要生成失败，使用空字符串
                if progress_callback:
                    progress_callback("分镜摘要生成失败，开始逐段生成分镜...")
            else:
                summary_text = f"文本整体摘要：\n{summary_result}\n\n"
                if progress_callback:
                    progress_callback("分镜摘要生成完成，开始逐段生成分镜...")
        else:
            print(f"[分镜生成] 文本长度 {len(text)} 未超过摘要阈值 {self.summary_threshold}，跳过摘要生成")
            logger.info(f"[分镜生成] 文本长度 {len(text)} 未超过摘要阈值 {self.summary_threshold}，跳过摘要生成")
            if progress_callback:
                progress_callback("文本长度适中，跳过摘要生成，开始逐段生成分镜...")
        
        # 处理每个分段，生成分镜
        all_shots_results = []
        
        for i, segment in enumerate(segments):
            print(f"[分镜生成] 正在为第 {i+1}/{len(segments)} 段生成分镜，段落长度: {len(segment)}")
            logger.info(f"[分镜生成] 正在为第 {i+1}/{len(segments)} 段生成分镜，段落长度: {len(segment)}")
            
            if progress_callback:
                progress_callback(f"正在为第 {i+1}/{len(segments)} 段生成分镜...")
            
            # 为分段添加上下文提示 - 优化镜头长度控制
            expected_min_shots = max(10, len(segment) // 40)  # 按每40字生成1个分镜
            expected_max_shots = max(15, len(segment) // 25)  # 按每25字生成1个分镜，确保镜头不会过长
            context_prompt = f"{summary_text}这是一篇长文本的第{i+1}部分（共{len(segments)}部分）。\n\n【超严格要求 - 必须严格执行】：\n1. 【文本覆盖】必须100%覆盖这部分的所有文本内容，从第一个字到最后一个字，绝对不能有任何遗漏或跳过\n2. 【分镜密度】这部分内容必须生成 {expected_min_shots} 到 {expected_max_shots} 个分镜，平均每25-40字生成1个分镜\n3. 【镜头长度控制】每个分镜的文案内容必须控制在25-45个字符之间，保持自然语言风格，不要强行断句\n4. 【原文引用】文案列必须逐字逐句引用原文，保持100%的原文完整性，禁止概括、省略或改写\n5. 【自然分割】优先在句号、感叹号、问号处分割；其次在逗号、分号处分割；确保每个镜头的文案语义完整\n6. 【长句处理】如果单个句子超过45字，应在合适的标点符号处拆分为多个镜头，保持语言自然流畅\n7. 【短句合并】如果相邻的短句合计不超过40字且语义相关，可以合并为一个镜头\n8. 【质量检查】生成完成后必须自检：每个镜头的文案是否在25-45字范围内？是否保持了自然语言风格？"
            
            # 生成当前段落的分镜
            segment_shots = self._generate_single_shots(f"{context_prompt}\n\n{segment}", style)
            
            # 检查是否生成成功
            if segment_shots.startswith("API错误"):
                print(f"[分镜生成] 第 {i+1} 段分镜生成失败: {segment_shots[:100]}...")
                logger.error(f"[分镜生成] 第 {i+1} 段分镜生成失败: {segment_shots[:100]}...")
                if progress_callback:
                    progress_callback(f"第 {i+1} 段分镜生成失败，终止操作")
                return f"分段分镜生成失败：第 {i+1} 段处理时出错 - {segment_shots}"
            
            all_shots_results.append(segment_shots)
            print(f"[分镜生成] 第 {i+1} 段分镜生成完成，结果长度: {len(segment_shots)}")
            logger.info(f"[分镜生成] 第 {i+1} 段分镜生成完成，结果长度: {len(segment_shots)}")
            
            if progress_callback:
                progress_callback(f"第 {i+1}/{len(segments)} 段分镜生成完成 ({int((i+1)/len(segments)*100)}%)")

        
        # 合并所有分镜结果
        # 对于分镜表格，我们需要特殊处理合并逻辑
        if progress_callback:
            progress_callback("正在合并所有分镜结果...")
            
        final_result = self._merge_shots_results(all_shots_results)
        print(f"[分镜生成] 分段分镜生成完成，最终结果长度: {len(final_result)}")
        logger.info(f"[分镜生成] 分段分镜生成完成，最终结果长度: {len(final_result)}")
        
        if progress_callback:
            progress_callback("分镜生成完成，已合并所有结果")
            
        return final_result
    
    def _merge_shots_results(self, shots_results: list) -> str:
        """合并多个分镜结果（Markdown表格格式）"""
        if not shots_results:
            return ""
        if len(shots_results) == 1:
            return shots_results[0]
        
        # 分析第一个结果，提取表头
        table_header = ""
        table_separator = ""
        all_data_rows = []
        
        # 处理每个分镜结果
        for result_idx, result in enumerate(shots_results):
            print(f"处理第 {result_idx + 1} 个分镜结果，长度: {len(result)}")
            
            # 跳过非表格内容
            if "|" not in result:
                print(f"第 {result_idx + 1} 个结果不包含表格，跳过")
                continue
                
            lines = result.strip().split("\n")
            current_data_rows = []
            
            for i, line in enumerate(lines):
                line = line.strip()
                if "|" in line and line.startswith("|") and line.endswith("|"):
                    if "---" in line:  # 这是表格分隔行
                        if not table_separator:
                            table_separator = line
                    elif "文案" in line or "场景" in line:  # 这是表头行
                        if not table_header:
                            table_header = line
                    else:  # 这是数据行
                        # 检查是否是有效的数据行（不是空行或只有分隔符）
                        if line.count("|") >= 8:  # 至少应该有9列（包括首尾的|）
                            current_data_rows.append(line)
            
            print(f"第 {result_idx + 1} 个结果提取到 {len(current_data_rows)} 行数据")
            all_data_rows.extend(current_data_rows)
        
        # 构建最终表格
        if not table_header or not table_separator:
            print("警告：没有提取到有效的表头或分隔符，返回第一个结果")
            return shots_results[0]
        
        # 重新编号所有分镜
        renumbered_rows = []
        for idx, row in enumerate(all_data_rows, 1):
            # 替换第一列的编号，保留其他所有列
            parts = row.split("|")
            if len(parts) >= 3:
                # 保持原有的列结构，只替换第二个元素（第一列的内容）

                new_row = "|".join(parts)
                renumbered_rows.append(new_row)
            else:
                renumbered_rows.append(row)
        
        merged_table = f"{table_header}\n{table_separator}\n" + "\n".join(renumbered_rows)
        print(f"合并完成，最终包含 {len(renumbered_rows)} 个分镜")
        return merged_table


    def rewrite_text(self, text: str, progress_callback=None) -> str:
        print("开始文本改写处理")
        logger.info(f"[文本改写] 开始处理，原文本长度: {len(text)}")
        
        # 检查文本长度，决定是否需要分段处理
        if len(text) > self.max_text_length:
            print(f"[文本改写] 文本长度 {len(text)} 超过限制 {self.max_text_length}，启用分段改写")
            logger.info(f"[文本改写] 文本长度 {len(text)} 超过限制 {self.max_text_length}，启用分段改写")
            if progress_callback:
                progress_callback(f"文本过长({len(text)}字符)，启用智能分段改写")
            return self._rewrite_text_with_segments(text, progress_callback)
        
        # 正常处理流程
        if progress_callback:
            progress_callback("文本长度适中，使用标准改写流程")
        return self._rewrite_single_text(text)
    
    def _rewrite_single_text(self, text: str) -> str:
        """处理单个文本段的改写"""
        system_prompt_rewrite = (
            "你是一位专业的文本润色和伪原创专家。你的任务是对用户提供的原始文本进行润色改写，实现伪原创效果。"
            "核心要求：1）严格保持原文的核心意思、观点和逻辑结构不变；2）修正错别字、语法错误和病句；3）优化词汇选择和句式结构，提升语言流畅性；4）适当替换同义词和调整表达方式，但不改变专业术语；5）保持原文长度和详细程度。"
            "输出要求：只输出改写后的纯文本内容，不要添加任何解释、评论、标题或格式标记。确保改写后的文本自然流畅，符合原文的使用场景和语言风格。"
        )
        user_prompt_rewrite = f"请对以下文本进行润色改写，修正错误并优化表达，实现伪原创效果：\n\n原始文本：\n{text}"
        messages = [{"role": "system", "content": system_prompt_rewrite}, {"role": "user", "content": user_prompt_rewrite}]

        content_result = self._make_api_call(self.rewrite_model_name, messages, "rewrite_text")
        
        print(f"DEBUG (llm_api.py rewrite_text): _make_api_call 返回的 content_result 类型: {type(content_result)}")

        if isinstance(content_result, str):
            print(f"DEBUG (llm_api.py rewrite_text): content_result (字符串预览): {content_result[:300]}...")
        elif isinstance(content_result, dict):
            print(f"DEBUG (llm_api.py rewrite_text): content_result (字典预览): {json.dumps(content_result, ensure_ascii=False, indent=2)[:300]}...")
        elif content_result is not None:
            print(f"DEBUG (llm_api.py rewrite_text): content_result (其他类型预览): {str(content_result)[:300]}...")

        # 使用修正后的变量名 content_result 进行后续判断
        if content_result is None:
            return "API错误（rewrite_text）：大模型调用未返回任何内容（content为None）。"

        if isinstance(content_result, dict):
            if 'shots' in content_result:
                error_msg = "API返回错误(rewrite_text): Deepseek API 在 content 字段【直接返回了分镜结构的字典】，而不是预期的纯文本。这似乎是该API的特殊行为。"
                print(f"错误详情 (rewrite_text): {error_msg}")
                return error_msg
            else:
                error_msg = "API返回错误(rewrite_text): Deepseek API 在 content 字段【直接返回了未知结构的字典】，而不是纯文本。"
                print(f"错误详情 (rewrite_text): {error_msg}")
                return error_msg
        elif isinstance(content_result, str):
            try:
                potential_json = json.loads(content_result)
                if isinstance(potential_json, dict) and 'shots' in potential_json:
                    error_msg = "API返回错误(rewrite_text): 大模型返回了【分镜JSON结构的字符串】，而不是预期的纯文本。"
                    print(f"错误详情 (rewrite_text): {error_msg}")
                    return error_msg
            except json.JSONDecodeError:
                print(f"成功 (rewrite_text): 模型返回了纯文本字符串。")
                # 移除可能的系列描述文本
                cleaned_result = self._remove_series_descriptions(content_result)
                # 去除多余的空行
                return self._remove_extra_blank_lines(cleaned_result) 
            
            print(f"警告 (rewrite_text): 模型返回了JSON字符串，但非分镜结构。对于改写任务，通常期望纯文本。")
            # 去除多余的空行
            return self._remove_extra_blank_lines(content_result)
        
        error_msg_fallback = f"API调用处理时发生意外情况(rewrite_text): 收到的 content_result 类型为 {type(content_result).__name__}，内容（预览）: {str(content_result)[:200]}"
        print(f"错误详情 (rewrite_text): {error_msg_fallback}")
        return error_msg_fallback
    
    def _rewrite_text_with_segments(self, text: str, progress_callback=None) -> str:
        """分段处理超长文本的改写"""
        print(f"开始分段改写，原文本长度: {len(text)}")
        
        # 智能分段
        segments = self._smart_split_text(text)
        print(f"文本已分为 {len(segments)} 段")
        
        if progress_callback:
            progress_callback(f"文本已分为 {len(segments)} 段，开始逐段处理...")
            
        rewritten_segments = []
        
        for i, segment in enumerate(segments):
            print(f"正在改写第 {i+1}/{len(segments)} 段，长度: {len(segment)}")
            
            if progress_callback:
                progress_callback(f"正在处理第 {i+1}/{len(segments)} 段文本...")
            
            # 改写当前段落（不添加上下文提示，避免生成不必要的描述）
            rewritten_segment = self._rewrite_single_text(segment)
            
            # 检查是否改写成功
            if rewritten_segment.startswith("API错误") or rewritten_segment.startswith("API返回错误"):
                print(f"第 {i+1} 段改写失败: {rewritten_segment[:100]}...")
                if progress_callback:
                    progress_callback(f"第 {i+1} 段处理失败，终止操作")
                return f"分段改写失败：第 {i+1} 段处理时出错 - {rewritten_segment}"
            
            # 移除可能的系列描述文本
            rewritten_segment = self._remove_series_descriptions(rewritten_segment)
            
            rewritten_segments.append(rewritten_segment)
            print(f"第 {i+1} 段改写完成，改写后长度: {len(rewritten_segment)}")
            
            if progress_callback:
                progress_callback(f"第 {i+1}/{len(segments)} 段处理完成 ({int((i+1)/len(segments)*100)}%)")
        
        # 合并所有改写后的段落
        if progress_callback:
            progress_callback("正在合并所有分段结果...")
            
        final_result = self._merge_rewritten_segments(rewritten_segments)
        print(f"分段改写完成，最终文本长度: {len(final_result)}")
        
        if progress_callback:
            progress_callback("分段处理完成，已合并所有结果")
            
        return final_result

    def create_story_from_theme(self, theme: str, progress_callback=None) -> str:
        """根据主题创作故事"""
        print(f"开始AI故事创作，主题: {theme}")
        logger.info(f"[AI创作] 开始处理，主题: {theme}")

        if progress_callback:
            progress_callback("正在分析创作主题...")

        system_prompt_create = (
            "你是一位才华横溢的小说家和故事创作专家。你的任务是根据用户提供的主题或关键词，创作一个引人入胜、内容丰富的完整故事。"
            "创作要求："
            "1. 故事长度：2000-4000字左右，内容充实，情节完整"
            "2. 结构完整：包含开头、发展、高潮、结局的完整故事结构"
            "3. 人物鲜明：塑造有血有肉的角色，包含主要角色的性格特点和背景"
            "4. 情节生动：包含冲突、转折、悬念等故事元素，让读者产生代入感"
            "5. 描写细腻：适当的环境描写、心理描写和动作描写，增强故事的画面感"
            "6. 主题深刻：在娱乐性的基础上，体现一定的思想内涵或人生感悟"
            "7. 语言优美：使用生动、富有感染力的语言，避免平铺直叙"
            "8. 适合改编：故事应该具有良好的视觉化潜力，便于后续制作成视频"
            "你的输出必须且仅为创作的完整故事文本，不要包含任何额外的说明、标题标记、创作思路解释或其他非故事内容。"
        )

        user_prompt_create = f"请根据以下主题创作一个精彩的故事：\n\n主题：{theme}\n\n请开始你的创作："

        messages = [
            {"role": "system", "content": system_prompt_create},
            {"role": "user", "content": user_prompt_create}
        ]

        if progress_callback:
            progress_callback("正在调用AI模型创作故事...")

        content_result = self._make_api_call(self.rewrite_model_name, messages, "create_story")

        print(f"DEBUG (llm_api.py create_story): _make_api_call 返回的 content_result 类型: {type(content_result)}")

        if isinstance(content_result, str):
            print(f"DEBUG (llm_api.py create_story): content_result (字符串预览): {content_result[:300]}...")
        elif isinstance(content_result, dict):
            print(f"DEBUG (llm_api.py create_story): content_result (字典预览): {json.dumps(content_result, ensure_ascii=False, indent=2)[:300]}...")
        elif content_result is not None:
            print(f"DEBUG (llm_api.py create_story): content_result (其他类型预览): {str(content_result)[:300]}...")

        if content_result is None:
            return "API错误（create_story）：大模型调用未返回任何内容（content为None）。"

        if isinstance(content_result, dict):
            if 'shots' in content_result:
                error_msg = "API返回错误(create_story): 模型返回了分镜结构，而不是预期的故事文本。"
                print(f"错误详情 (create_story): {error_msg}")
                return error_msg
            else:
                error_msg = "API返回错误(create_story): 模型返回了字典结构，而不是纯文本故事。"
                print(f"错误详情 (create_story): {error_msg}")
                return error_msg
        elif isinstance(content_result, str):
            try:
                potential_json = json.loads(content_result)
                if isinstance(potential_json, dict) and 'shots' in potential_json:
                    error_msg = "API返回错误(create_story): 模型返回了分镜JSON结构的字符串，而不是预期的故事文本。"
                    print(f"错误详情 (create_story): {error_msg}")
                    return error_msg
            except json.JSONDecodeError:
                print(f"成功 (create_story): 模型返回了纯文本故事。")
                # 清理和优化故事文本
                cleaned_result = self._clean_story_text(content_result)
                return cleaned_result

            print(f"警告 (create_story): 模型返回了JSON字符串，但非分镜结构。")
            return self._clean_story_text(content_result)

        error_msg_fallback = f"API调用处理时发生意外情况(create_story): 收到的 content_result 类型为 {type(content_result).__name__}，内容（预览）: {str(content_result)[:200]}"
        print(f"错误详情 (create_story): {error_msg_fallback}")
        return error_msg_fallback

    def _clean_story_text(self, text: str) -> str:
        """清理和优化故事文本"""
        # 移除Markdown标题标记
        text = re.sub(r'^#+\s*.*?\n', '', text, flags=re.MULTILINE)

        # 移除章节标题（如：第一章、开头、发展、高潮、结局等）
        text = re.sub(r'^(第[一二三四五六七八九十\d]+章|开头|发展|高潮|结局|序章|尾声)[:：]?\s*.*?\n', '', text, flags=re.MULTILINE)

        # 移除带序号的标题（如：1. 开头、一、开头等）
        text = re.sub(r'^([一二三四五六七八九十\d]+[、.]|[一二三四五六七八九十\d]+\.)\s*(开头|发展|高潮|结局|序章|尾声).*?\n', '', text, flags=re.MULTILINE)

        # 移除可能的创作说明
        text = re.sub(r'(根据.*?主题.*?创作|以下是.*?故事|故事创作完成|创作思路|故事梗概|故事简介).*?\n', '', text, flags=re.IGNORECASE)

        # 移除可能的分段标记（如：#### 开头：相遇与默契）
        text = re.sub(r'^####?\s*.*?[:：].*?\n', '', text, flags=re.MULTILINE)

        # 移除故事标题行（通常在开头）
        lines = text.split('\n')
        cleaned_lines = []
        skip_first_title = True

        for line in lines:
            line_stripped = line.strip()
            # 跳过第一个可能的标题行
            if skip_first_title and line_stripped and not line_stripped[0].islower() and len(line_stripped) < 50:
                # 检查是否像标题（短且首字母大写或中文）
                if '。' not in line_stripped and '！' not in line_stripped and '？' not in line_stripped:
                    skip_first_title = False
                    continue
            skip_first_title = False
            cleaned_lines.append(line)

        text = '\n'.join(cleaned_lines)

        # 移除多余的空行
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)

        # 去除首尾空白
        text = text.strip()

        return text


logger = logging.getLogger(__name__)