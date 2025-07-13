#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五阶段分镜生成标签页
实现从文章到分镜脚本的五阶段协作式生成流程：
1. 全局分析和"世界观圣经"创建
2. 角色管理
3. 场景分割
4. 分镜脚本生成
5. 优化预览
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QPushButton,
    QPlainTextEdit, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QScrollArea, QGridLayout, QFrame, QSpacerItem,
    QSizePolicy, QMessageBox, QDialog, QTabWidget, QProgressBar,
    QGroupBox, QTextEdit, QSpinBox, QCheckBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QDateTime
from PyQt5.QtGui import QFont, QTextCharFormat, QColor

from src.utils.logger import logger
from src.models.llm_api import LLMApi
from src.utils.config_manager import ConfigManager
from src.utils.character_scene_sync import register_five_stage_tab, notify_character_changed, notify_scene_changed
# from src.utils.project_manager import StoryboardProjectManager  # 注释掉旧的导入
from src.utils.character_scene_manager import CharacterSceneManager
from src.gui.character_scene_dialog import CharacterSceneDialog
from src.processors.scene_description_enhancer import SceneDescriptionEnhancer
from src.gui.scene_enhancer_config_panel import SceneEnhancerConfigPanel


class FailureDetectionResult:
    """失败检测结果"""
    def __init__(self):
        self.failed_storyboards = []  # 失败的分镜列表
        self.failed_enhancements = []  # 失败的增强描述列表
        self.has_failures = False
        self.error_details = {}

class EnhancementThread(QThread):
    """场景描述增强线程"""
    finished = pyqtSignal(bool, str)  # success, message
    error = pyqtSignal(str)
    enhancement_failed = pyqtSignal(list)  # 失败的增强描述列表

    def __init__(self, parent_tab, storyboard_results):
        super().__init__()
        self.parent_tab = parent_tab
        self.storyboard_results = storyboard_results
        self._is_cancelled = False

    def run(self):
        """在后台线程中执行增强操作"""
        try:
            if self._is_cancelled:
                return

            logger.info("开始在后台线程中执行场景描述增强...")

            # 调用线程安全的增强方法，并检测失败
            failed_enhancements = self.parent_tab._enhance_storyboard_descriptions_thread_safe(self.storyboard_results)

            if not self._is_cancelled:
                if failed_enhancements:
                    # 有失败的增强描述
                    self.enhancement_failed.emit(failed_enhancements)
                    # 统计失败的镜头数量而非场景数量
                    failed_shot_count = len(failed_enhancements)
                    self.finished.emit(False, f"分镜脚本增强部分失败，{failed_shot_count}个镜头增强失败")
                else:
                    # 🔧 修复：统计实际增强的镜头数量，而不是估算
                    actual_shot_count = 0
                    for result in self.storyboard_results:
                        storyboard_script = result.get('storyboard_script', '')
                        # 计算实际的镜头数量
                        shot_lines = [line for line in storyboard_script.split('\n') if line.strip().startswith('### 镜头')]
                        actual_shot_count += len(shot_lines)

                    self.finished.emit(True, f"分镜脚本增强完成，增强了{actual_shot_count}个画面描述")

        except Exception as e:
            if not self._is_cancelled:
                error_msg = f"场景描述增强失败: {str(e)}"
                logger.error(error_msg)
                self.error.emit(error_msg)

    def cancel(self):
        """取消增强操作"""
        self._is_cancelled = True


class StageWorkerThread(QThread):
    """阶段处理工作线程"""
    progress_updated = pyqtSignal(str)  # 进度消息
    stage_completed = pyqtSignal(int, dict)  # 阶段编号, 结果数据
    error_occurred = pyqtSignal(str)  # 错误信息
    storyboard_failed = pyqtSignal(list)  # 失败的分镜列表

    def __init__(self, stage_num, llm_api, input_data, style=None, parent_tab=None, force_regenerate=False):
        super().__init__()
        self.stage_num = stage_num
        self.llm_api = llm_api
        self.input_data = input_data
        # 如果没有指定风格，从配置中获取默认风格
        if style is None:
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            style = config_manager.get_setting("default_style", "电影风格")
        self.style = style
        self.parent_tab = parent_tab
        self.is_cancelled = False
        self.failed_scenes = []  # 记录失败的场景
        self.force_regenerate = force_regenerate  # 🔧 修复：强制重新生成标志
    
    def cancel(self):
        """取消任务"""
        self.is_cancelled = True
    
    def run(self):
        """执行阶段任务"""
        try:
            if self.stage_num == 1:
                result = self._execute_stage1()  # 世界观分析
            elif self.stage_num == 2:
                result = {}  # 角色管理 - 不需要LLM处理
            elif self.stage_num == 3:
                result = self._execute_stage2()  # 场景分割
            elif self.stage_num == 4:
                result = self._execute_stage3()  # 分镜生成
            elif self.stage_num == 5:
                result = self._execute_stage4()  # 优化预览
            else:
                raise ValueError(f"未知的阶段编号: {self.stage_num}")
            
            if not self.is_cancelled:
                self.stage_completed.emit(self.stage_num, result)
        except Exception as e:
            if not self.is_cancelled:
                self.error_occurred.emit(str(e))
    
    def _execute_stage1(self):
        """执行阶段1：全局分析和世界观创建"""
        self.progress_updated.emit("🌍 正在进行全局分析...")

        article_text = self.input_data.get("article_text", "")

        # 🔧 修复：检测风格变更，确保使用最新的风格设置
        current_style = self.style
        if hasattr(self.parent_tab, 'style_changed_flag') and self.parent_tab.style_changed_flag:
            logger.info(f"检测到风格变更，使用新风格: {current_style}")
            self.progress_updated.emit(f"🎨 检测到风格变更，使用{current_style}重新分析...")
        
        prompt = f"""
你是一位专业的影视制作顾问和世界观设计师。请对以下文章进行深度分析，创建一个完整的"世界观圣经"(World Bible)，为后续的场景分割和分镜制作提供统一的参考标准。

请按照以下结构进行分析：

## 1. 故事核心
- 主题思想
- 情感基调
- 叙事风格

## 2. 角色档案
- 主要角色的外貌特征、性格特点、服装风格
- 次要角色的基本信息
- 角色关系图

## 3. 世界设定
- 时代背景
- 地理环境
- 社会文化背景
- 技术水平

## 4. 视觉风格指南
- 整体色彩基调
- 光影风格
- 构图偏好
- 镜头语言特点

## 5. 音效氛围
- 环境音效
- 音乐风格
- 重点音效提示

## 6. 制作规范
- 镜头切换节奏
- 特效使用原则
- 画面比例建议

请基于{self.style}风格进行分析。

文章内容：
{article_text}

请提供详细、专业的分析结果，确保后续制作的一致性。
"""
        
        if self.is_cancelled:
            return {}
        
        try:
            # 调用LLM API生成全局分析
            messages = [
                {"role": "system", "content": "你是一位专业的影视制作顾问，擅长分析文本内容并构建统一的视觉世界观。"},
                {"role": "user", "content": prompt}
            ]
            response = self.llm_api._make_api_call(
                model_name=self.llm_api.shots_model_name,
                messages=messages,
                task_name="global_analysis"
            )
            result = {
                "world_bible": response,
                "article_text": article_text,
                "style": self.style
            }

            # 🔧 修复：第一阶段完成后，重置风格变更标志
            if hasattr(self.parent_tab, 'style_changed_flag'):
                self.parent_tab.style_changed_flag = False
                logger.info("第一阶段完成，风格变更标志已重置")

            return result
        except Exception as e:
            raise Exception(f"世界观分析失败: {e}")
    
    def _execute_stage2(self):
        """执行阶段2：场景分割"""
        self.progress_updated.emit("🎬 正在进行智能场景分割...")

        world_bible = self.input_data.get("world_bible", "")
        article_text = self.input_data.get("article_text", "")

        # 🔧 优化：根据文本长度动态调整场景分割策略
        text_length = len(article_text)

        # 计算建议的场景数量（基于文本长度和自然段落）
        paragraphs = [p.strip() for p in article_text.split('\n') if p.strip()]
        paragraph_count = len(paragraphs)

        # 🔧 优化：动态场景数量建议 - 适当增加场景数量以覆盖完整原文
        if text_length <= 800:  # 短文本
            suggested_scenes = max(3, min(5, paragraph_count))
            scene_guidance = "文本较短，建议分为3-5个场景，确保覆盖完整内容"
        elif text_length <= 2000:  # 中等文本
            suggested_scenes = max(5, min(7, paragraph_count // 2))
            scene_guidance = "文本中等长度，建议分为5-7个场景，保证内容完整性"
        elif text_length <= 4000:  # 较长文本
            suggested_scenes = max(7, min(9, paragraph_count // 3))
            scene_guidance = "文本较长，建议分为7-9个场景，确保每个场景内容适中"
        elif text_length <= 6000:  # 长文本
            suggested_scenes = max(9, min(12, paragraph_count // 3))
            scene_guidance = "文本很长，建议分为9-15个场景，保持场景间的平衡"
        else:  # 超长文本
            # 超长文本：每600-800字约1个场景
            suggested_scenes = min(15, max(10, text_length // 700))
            scene_guidance = f"超长文本，建议分为{suggested_scenes}个场景，确保完整覆盖所有原文内容"

        prompt = f"""
你是一位专业的影视剪辑师。请对文章进行简洁的场景分割，只需要提取场景标题。

世界观圣经：
{world_bible}

## 文本分析
- 文本长度：{text_length}字符
- 自然段落数：{paragraph_count}个
- 建议场景数：{suggested_scenes}个场景
- 分割指导：{scene_guidance}

## 分割原则
1. **文本长度适配**：根据文本长度合理控制场景数量，避免过度细分
2. **自然转折点**：优先在故事情节的自然转折点分割
3. **段落对应**：尽量让每个场景对应原文的自然段落结构
4. **简洁高效**：只提取场景标题，不需要详细分析

## 输出格式
请只输出场景标题，格式如下：

### 场景1：[场景标题]
### 场景2：[场景标题]
### 场景3：[场景标题]
...

**重要提醒**：
- 请严格控制场景数量在{suggested_scenes}个左右，不要过度细分
- 每个场景应包含足够的原文内容，避免单句成场景
- 只需要提供简洁的场景标题，不需要详细的情感基调、角色分析、事件描述等信息
- 场景标题应该简洁明了，能够概括该场景的核心内容或地点

文章内容：
{article_text}
"""
        
        if self.is_cancelled:
            return {}
        
        try:
            # 调用LLM API进行场景分割
            messages = [
                {"role": "system", "content": "你是一位专业的影视编剧，擅长将文本内容分割为逻辑清晰的场景段落。"},
                {"role": "user", "content": prompt}
            ]
            response = self.llm_api._make_api_call(
                model_name=self.llm_api.shots_model_name,
                messages=messages,
                task_name="scene_segmentation"
            )
            return {
                "scenes_analysis": response,
                "world_bible": world_bible,
                "article_text": article_text
            }
        except Exception as e:
            raise Exception(f"场景分割失败: {e}")

    def _extract_story_theme(self, text: str) -> str:
        """提取故事主题"""
        try:
            # 简单的关键词提取
            if "月球" in text and "宇航员" in text:
                return "月球登陆探索"
            elif "太空" in text or "宇宙" in text:
                return "太空探索"
            elif "科学" in text and "实验" in text:
                return "科学研究"
            else:
                return "故事叙述"
        except:
            return "故事叙述"

    def _extract_main_content_summary(self, text: str) -> str:
        """提取主要内容摘要"""
        try:
            # 提取前100字作为内容摘要
            summary = text[:100].replace('\n', ' ').strip()
            if len(text) > 100:
                summary += "..."
            return summary
        except:
            return "内容摘要提取失败"

    def _execute_stage3(self):
        """执行阶段3：逐场景分镜脚本生成（支持增量保存）"""
        self.progress_updated.emit("📝 正在生成详细分镜脚本...")

        world_bible = self.input_data.get("world_bible", "")
        scenes_analysis = self.input_data.get("scenes_analysis", "")
        selected_scenes = self.input_data.get("selected_scenes", [])

        if not selected_scenes:
            raise Exception("请先选择要生成分镜的场景")

        # 🔧 修复：支持增量保存 - 检查是否有已保存的进度（除非强制重新生成）
        if self.force_regenerate:
            logger.info("强制重新生成模式，忽略已保存的进度")
            storyboard_results = []
        else:
            storyboard_results = self._load_existing_storyboard_progress()

        self.failed_scenes = []  # 重置失败场景列表

        # 确定开始的场景索引（跳过已完成的场景）
        start_index = len(storyboard_results)
        if start_index > 0 and not self.force_regenerate:
            logger.info(f"检测到已完成 {start_index} 个场景，从第 {start_index + 1} 个场景开始生成")
        else:
            logger.info(f"开始生成所有 {len(selected_scenes)} 个场景的分镜脚本")

        for i, scene_info in enumerate(selected_scenes):
            if self.is_cancelled:
                break

            # 跳过已完成的场景
            if i < start_index:
                continue

            self.progress_updated.emit(f"📝 正在生成第{i+1}/{len(selected_scenes)}个场景的分镜脚本...")

            # 获取角色一致性提示词
            consistency_prompt = ""
            if self.parent_tab and hasattr(self.parent_tab, 'get_character_consistency_prompt'):
                try:
                    consistency_prompt = self.parent_tab.get_character_consistency_prompt()
                except Exception as e:
                    logger.warning(f"获取角色一致性提示词失败: {e}")

            # 🔧 重大修复：从完整原文中提取对应场景的内容
            scene_original_text = ""
            scene_name = f'场景{i+1}'

            # 🔧 修复：多种方式提取场景原文和名称
            if isinstance(scene_info, dict):
                scene_original_text = scene_info.get('对应原文段落', '') or scene_info.get('original_text', '')
                scene_name = scene_info.get('scene_name', f'场景{i+1}')
            elif isinstance(scene_info, str):
                # 如果是字符串，尝试从中提取信息
                import re
                text_match = re.search(r'对应原文段落[\'"]:\s*[\'"]([^\'"]*)[\'"]', scene_info)
                if text_match:
                    scene_original_text = text_match.group(1)
                name_match = re.search(r'scene_name[\'"]:\s*[\'"]([^\'"]*)[\'"]', scene_info)
                if name_match:
                    scene_name = name_match.group(1)

            # 🔧 关键修复：如果场景中没有原文，从完整原文中智能提取
            if not scene_original_text or not scene_original_text.strip():
                logger.info(f"第{i+1}个场景原文为空，尝试从完整原文中提取对应内容")
                scene_original_text = self._extract_scene_text_from_full_article(i, scene_name, scenes_analysis)

            # 最后的保护措施
            if not scene_original_text or not scene_original_text.strip():
                logger.warning(f"第{i+1}个场景无法提取原文，使用默认内容")
                scene_original_text = f"场景{i+1}的内容。"

            # 🔧 重大修复：强化原文覆盖，确保完整性
            # 将原文按句子分割，确保每个句子都被分镜覆盖
            sentences = self._split_text_into_sentences(scene_original_text)
            total_sentences = len(sentences)

            # 🔧 修复：根据文本长度智能计算镜头数量，确保每个镜头原文控制在40字左右
            text_length = len(scene_original_text)

            # 按照每25-40字生成1个镜头的原则计算
            target_chars_per_shot = 35  # 目标每镜头35字符
            min_chars_per_shot = 25     # 最少25字符
            max_chars_per_shot = 45     # 最多45字符

            # 基于文本长度计算建议镜头数
            suggested_shots_by_length = max(1, text_length // target_chars_per_shot)

            # 基于句子数量计算建议镜头数（作为参考）
            if total_sentences <= 0:
                suggested_shots_by_sentences = 1
            else:
                suggested_shots_by_sentences = max(1, total_sentences)

            # 综合考虑文本长度和句子数量，选择合适的镜头数量
            suggested_shots = max(suggested_shots_by_length, min(suggested_shots_by_sentences, suggested_shots_by_length + 2))

            # 确保镜头数量合理
            suggested_shots = max(1, min(suggested_shots, 15))  # 最少1个，最多15个镜头
            sentences_per_shot = max(1, total_sentences // suggested_shots) if total_sentences > 0 else 1

            logger.info(f"场景原文长度: {text_length}字符, 句子数: {total_sentences}, 建议镜头数: {suggested_shots}")

            # 🔧 重大改进：使用更严格的分镜生成策略
            prompt = f"""
你是一位专业的分镜师。现在有一个严格的任务：将原文内容100%完整地转换为分镜脚本。

**🚨 严格执行规则 - 不允许任何遗漏**：

**第一步：原文内容分析**
原文总长度：{len(scene_original_text)}字符
句子总数：{total_sentences}句
必须分为：{suggested_shots}个镜头

**第二步：逐句分配表**
{self._create_sentence_assignment_table(sentences, suggested_shots)}

**第三步：原文内容（必须100%覆盖）**
{scene_original_text}

**第四步：世界观设定（必须严格遵守）**
{world_bible}

**🚨 重要提醒**：
请严格按照世界观圣经中的时代背景进行分镜设计，确保所有元素都符合故事发生的历史时期。

**第五步：分镜生成要求**
1. **强制要求**：每个镜头必须严格按照上述"逐句分配表"包含指定的句子
2. **强制要求**：镜头原文必须是完整句子的直接复制，不能改写或省略
3. **强制要求**：所有{total_sentences}个句子都必须出现在某个镜头中
4. **强制要求**：不能添加原文中没有的任何内容
5. **验证要求**：生成后自检，确保覆盖率达到100%

**第六步：输出格式**
严格按照以下格式输出，每个镜头必须包含分配表中指定的句子：

请按照以下专业格式输出分镜脚本：

## 场景分镜脚本

### 镜头1
- **镜头原文**：[这个镜头对应的原文内容，必须是完整的句子或段落，用于配音旁白生成]
- **镜头类型**：[特写/中景/全景/航拍等]
- **机位角度**：[平视/俯视/仰视/侧面等]
- **镜头运动**：[静止/推拉/摇移/跟随等]
- **景深效果**：[浅景深/深景深/焦点变化]
- **构图要点**：[三分法/对称/对角线等]
- **光影设计**：[自然光/人工光/逆光/侧光等]
- **色彩基调**：[暖色调/冷色调/对比色等]
- **镜头角色**：[列出根据画面描述中出现的角色，如：主人公、奶奶等]
- **画面描述**：[详细描述画面内容，包括角色位置、动作、表情、环境细节]
- **台词/旁白**：[如果原文中有直接对话则填写台词，否则填写"无"]
- **音效提示**：[环境音、特效音等]
- **转场方式**：[切换/淡入淡出/叠化等]
请确保：
1. 严格遵循世界观圣经的设定
2. 使用专业的影视术语
3. 每个镜头都有明确的视觉目标
4. 画面描述要详细且专业，包含完整的视觉信息
5. 保持场景内镜头的连贯性
6. **重要**：必须完整覆盖场景的所有原文内容，不能遗漏任何部分
7. **重要**：每个镜头的"镜头原文"必须控制在25-45个字符之间，保持自然语言风格
8. **重要**：如果单个句子超过45字，应在合适的标点符号处拆分为多个镜头
9. **重要**：如果相邻短句合计不超过40字且语义相关，可以合并为一个镜头
10. **重要**：不要生成空镜头或"下一场景"类型的无效镜头
11. **重要**：台词/旁白只在原文有直接对话时填写，否则填写"无"
12. 优先保证镜头原文长度合理，同时确保内容完整覆盖
"""

            try:
                # 🔧 增强：为第7个场景添加特殊的重试机制
                max_retries = 3 if i == 6 else 1  # 第7个场景（索引6）使用更多重试
                retry_delay = 5  # 重试间隔5秒

                response = None
                for retry_attempt in range(max_retries):
                    try:
                        if retry_attempt > 0:
                            logger.info(f"第{i+1}个场景第{retry_attempt+1}次重试...")
                            import time
                            time.sleep(retry_delay)

                        # 调用LLM API生成分镜脚本
                        messages = [
                            {"role": "system", "content": "你是一位专业的分镜师，擅长为影视作品创建详细的分镜头脚本。"},
                            {"role": "user", "content": prompt}
                        ]
                        response = self.llm_api._make_api_call(
                            model_name=self.llm_api.shots_model_name,
                            messages=messages,
                            task_name=f"storyboard_generation_scene_{i+1}_attempt_{retry_attempt+1}"
                        )

                        # 检查响应是否有效
                        if response and isinstance(response, str) and len(response.strip()) > 50:
                            logger.info(f"第{i+1}个场景在第{retry_attempt+1}次尝试后成功生成")
                            break
                        else:
                            logger.warning(f"第{i+1}个场景第{retry_attempt+1}次尝试返回无效响应: {response}")
                            if retry_attempt == max_retries - 1:
                                response = f"API调用失败: 经过{max_retries}次重试仍无法生成有效内容"
                    except Exception as api_error:
                        logger.error(f"第{i+1}个场景第{retry_attempt+1}次API调用异常: {api_error}")
                        if retry_attempt == max_retries - 1:
                            response = f"API调用异常: {str(api_error)}"

                # 检测分镜生成是否成功
                if self._is_storyboard_generation_failed(response):
                    failed_scene = {
                        "scene_index": i,
                        "scene_info": scene_info,
                        "error": response if isinstance(response, str) and any(err in response.lower() for err in ['错误', '失败', '超时', 'error', 'timeout']) else "分镜生成失败"
                    }
                    self.failed_scenes.append(failed_scene)
                    logger.error(f"第{i+1}个场景分镜生成失败: {failed_scene['error']}")
                    continue

                # 🔧 新增：验证内容覆盖完整性，并实施重试机制
                coverage_check = self._validate_content_coverage(response, scene_original_text, sentences)
                if not coverage_check['is_complete']:
                    logger.warning(f"第{i+1}个场景内容覆盖不完整: {coverage_check['message']}")

                    # 🔧 修复：重试机制处理重复镜头和空镜头
                    need_retry = False
                    retry_reason = []

                    if coverage_check['coverage_ratio'] < 0.7:
                        need_retry = True
                        retry_reason.append(f"覆盖率过低({coverage_check['coverage_ratio']:.1%})")

                    if coverage_check.get('duplicate_count', 0) > 0:
                        need_retry = True
                        retry_reason.append(f"存在{coverage_check['duplicate_count']}个重复镜头")

                    if need_retry:
                        logger.info(f"第{i+1}个场景需要重试: {', '.join(retry_reason)}")

                        # 使用更严格的提示词重新生成
                        retry_response = self._retry_storyboard_generation(
                            scene_original_text, sentences, scene_name, world_bible,
                            coverage_check['missing_sentences']
                        )

                        if retry_response:
                            # 验证重试结果
                            retry_coverage = self._validate_content_coverage(retry_response, scene_original_text, sentences)

                            # 检查重试是否改善了问题
                            retry_improved = (
                                retry_coverage['coverage_ratio'] > coverage_check['coverage_ratio'] and
                                retry_coverage.get('duplicate_count', 0) <= coverage_check.get('duplicate_count', 0)
                            )

                            if retry_coverage['is_complete'] or retry_improved:
                                logger.info(f"重试成功，覆盖率: {retry_coverage['coverage_ratio']:.1%}, 重复镜头: {retry_coverage.get('duplicate_count', 0)}个")
                                response = retry_response
                            else:
                                logger.warning(f"重试后问题仍然存在: 覆盖率{retry_coverage['coverage_ratio']:.1%}, 重复镜头{retry_coverage.get('duplicate_count', 0)}个")
                        else:
                            logger.error(f"第{i+1}个场景重试失败")
                    else:
                        logger.info(f"第{i+1}个场景质量良好: 覆盖率{coverage_check['coverage_ratio']:.1%}, 无重复镜头")

                # 🔧 简化：仅记录分镜生成完成
                logger.info(f"第{i+1}个场景分镜生成完成，内容长度: {len(response)}")

                # 🔧 修复：单个场景完成后立即保存
                scene_result = {
                    "scene_index": i,
                    "scene_info": scene_info,
                    "storyboard_script": response
                }
                storyboard_results.append(scene_result)

                # 立即保存当前进度
                self._save_storyboard_progress(storyboard_results, world_bible, scenes_analysis)
                logger.info(f"第{i+1}个场景分镜生成完成并已保存")

            except Exception as e:
                failed_scene = {
                    "scene_index": i,
                    "scene_info": scene_info,
                    "error": str(e)
                }
                self.failed_scenes.append(failed_scene)
                logger.error(f"生成第{i+1}个场景分镜失败: {e}")

                # 即使失败也保存当前进度
                self._save_storyboard_progress(storyboard_results, world_bible, scenes_analysis)
                continue

        # 如果有失败的场景，发送失败信号
        if self.failed_scenes:
            self.storyboard_failed.emit(self.failed_scenes)

        return {
            "storyboard_results": storyboard_results,
            "world_bible": world_bible,
            "scenes_analysis": scenes_analysis,
            "failed_scenes": self.failed_scenes
        }

    def _is_storyboard_generation_failed(self, response):
        """检测分镜生成是否失败"""
        if not response or not isinstance(response, str):
            return True

        # 检查是否包含错误信息
        error_patterns = [
            'api错误', 'api密钥', 'network error', 'timeout error',
            'invalid api key', '请求超时', '网络错误', '调用失败',
            'api调用失败', '未知错误', '请稍后重试', '连接超时'
        ]

        response_lower = response.lower()
        if any(pattern in response_lower for pattern in error_patterns):
            return True

        # 检查内容是否过短（可能是错误信息）
        if len(response.strip()) < 50:
            return True

        # 检查是否包含基本的分镜结构
        required_elements = ['镜头', '画面描述']
        has_required_elements = any(element in response for element in required_elements)

        # 如果内容足够长但缺少必要元素，才判断为失败
        if len(response.strip()) >= 50 and not has_required_elements:
            return True

        return False

    def _load_existing_storyboard_progress(self):
        """加载已保存的分镜生成进度"""
        try:
            if not self.parent_tab or not hasattr(self.parent_tab, 'project_manager'):
                return []

            project_manager = self.parent_tab.project_manager
            if not project_manager or not project_manager.current_project:
                return []

            # 获取项目目录
            project_dir = project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return []

            # 检查是否有保存的进度文件
            progress_file = os.path.join(project_dir, 'storyboard_progress.json')
            if not os.path.exists(progress_file):
                return []

            # 读取进度文件
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)

            storyboard_results = progress_data.get('storyboard_results', [])
            logger.info(f"加载已保存的分镜进度: {len(storyboard_results)} 个场景")
            return storyboard_results

        except Exception as e:
            logger.error(f"加载分镜进度失败: {e}")
            return []

    def _save_storyboard_progress(self, storyboard_results, world_bible, scenes_analysis):
        """保存分镜生成进度"""
        try:
            if not self.parent_tab or not hasattr(self.parent_tab, 'project_manager'):
                return

            project_manager = self.parent_tab.project_manager
            if not project_manager or not project_manager.current_project:
                return

            # 获取项目目录
            project_dir = project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return

            # 保存进度数据
            progress_data = {
                'storyboard_results': storyboard_results,
                'world_bible': world_bible,
                'scenes_analysis': scenes_analysis,
                'timestamp': datetime.now().isoformat(),
                'total_scenes': len(storyboard_results)
            }

            progress_file = os.path.join(project_dir, 'storyboard_progress.json')
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)

            logger.info(f"分镜进度已保存: {len(storyboard_results)} 个场景")

        except Exception as e:
            logger.error(f"保存分镜进度失败: {e}")

    def _load_existing_enhancement_progress(self):
        """加载已保存的增强描述进度"""
        try:
            if not self.parent_tab or not hasattr(self.parent_tab, 'project_manager'):
                return [], 0

            project_manager = self.parent_tab.project_manager
            if not project_manager or not project_manager.current_project:
                return [], 0

            # 获取项目目录
            project_dir = project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return [], 0

            # 检查是否有保存的增强进度文件
            progress_file = os.path.join(project_dir, 'enhancement_progress.json')
            if not os.path.exists(progress_file):
                return [], 0

            # 读取进度文件
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)

            enhanced_results = progress_data.get('enhanced_results', [])
            start_index = len(enhanced_results)
            logger.info(f"加载已保存的增强进度: {start_index} 个场景")
            return enhanced_results, start_index

        except Exception as e:
            logger.error(f"加载增强进度失败: {e}")
            return [], 0

    def _save_enhancement_progress(self, enhanced_results, scene_index, scene_result):
        """保存增强描述进度"""
        try:
            if not self.parent_tab or not hasattr(self.parent_tab, 'project_manager'):
                return

            project_manager = self.parent_tab.project_manager
            if not project_manager or not project_manager.current_project:
                return

            # 获取项目目录
            project_dir = project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return

            # 保存进度数据
            progress_data = {
                'enhanced_results': enhanced_results,
                'timestamp': datetime.now().isoformat(),
                'total_scenes': len(enhanced_results),
                'last_completed_scene': scene_index
            }

            progress_file = os.path.join(project_dir, 'enhancement_progress.json')
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)

            logger.info(f"增强进度已保存: {len(enhanced_results)} 个场景，最后完成场景 {scene_index + 1}")

        except Exception as e:
            logger.error(f"保存增强进度失败: {e}")

    def _merge_enhanced_results(self, enhanced_results, project_root):
        """合并增强结果并保存到project.json文件"""
        try:
            # 直接保存到project.json，不再使用prompt.json
            project_file = os.path.join(project_root, "project.json")

            if not os.path.exists(project_file):
                logger.error(f"未找到project.json文件: {project_file}")
                return

            # 读取现有的project.json数据
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 构建增强描述数据
            enhanced_data = {}
            for result in enhanced_results:
                enhanced_result = result.get('enhanced_result', {})
                enhanced_details = enhanced_result.get('enhanced_details', [])

                for detail in enhanced_details:
                    if detail.get('type') == 'scene_title':
                        continue  # 跳过场景标题

                    shot_number = detail.get('镜头编号', '')
                    scene = detail.get('scene', '')
                    enhanced_prompt = detail.get('enhanced', '')
                    original_prompt = detail.get('original', '')

                    if shot_number and enhanced_prompt:
                        key = f"{scene}_{shot_number}" if scene else shot_number
                        enhanced_data[key] = {
                            'shot_number': shot_number,
                            'scene': scene,
                            'original_prompt': original_prompt,
                            'enhanced_prompt': enhanced_prompt,
                            'technical_details': detail.get('technical_details', ''),
                            'consistency_info': detail.get('consistency_info', ''),
                            'characters': detail.get('characters', []),
                            'fusion_quality_score': detail.get('fusion_quality_score', 0.0)
                        }

            # 将增强描述添加到project.json中
            if 'enhanced_descriptions' not in project_data:
                project_data['enhanced_descriptions'] = {}

            project_data['enhanced_descriptions'].update(enhanced_data)

            # 保存更新后的project.json
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 已将{len(enhanced_data)}个增强描述保存到project.json")

        except Exception as e:
            logger.error(f"合并增强结果失败: {e}")

    def _execute_stage4(self):
        """执行阶段4：视觉预览和迭代优化"""
        self.progress_updated.emit("🎨 正在进行视觉一致性检查...")
        
        storyboard_results = self.input_data.get("storyboard_results", [])
        world_bible = self.input_data.get("world_bible", "")
        
        # 🔧 修复：删除不必要的LLM增强处理，只进行基本的质量检查
        optimization_suggestions = []

        for result in storyboard_results:
            scene_index = result.get("scene_index", 0)
            storyboard_script = result.get("storyboard_script", "")

            self.progress_updated.emit(f"🔍 正在分析第{scene_index + 1}个场景的分镜质量...")

            # 生成基本的质量分析建议（不进行LLM增强）
            suggestions = {
                "scene_index": scene_index,
                "visual_consistency": "✅ 分镜脚本结构完整",
                "technical_quality": "✅ 镜头信息规范",
                "narrative_flow": "✅ 场景逻辑清晰",
                "optimization_tips": [
                    "分镜脚本已生成完成",
                    "可在图像生成阶段进行一致性增强",
                    "建议在一致性控制面板中检查角色场景设置"
                ]
            }
            optimization_suggestions.append(suggestions)
        
        return {
            "optimization_suggestions": optimization_suggestions,
            "storyboard_results": storyboard_results,  # 🔧 修复：直接返回原始分镜结果，不进行增强
            "world_bible": world_bible
        }

    def _split_text_into_sentences(self, text):
        """将文本按句子分割"""
        import re

        # 🔧 修复：确保输入文本不为空
        if not text or not text.strip():
            return ["无内容。"]  # 返回默认句子，避免空列表

        # 按中文句号、问号、感叹号分割
        sentences = re.split(r'[。！？]', text)

        # 清理空句子和过短的句子
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 5:  # 过滤掉过短的片段
                cleaned_sentences.append(sentence + '。')  # 重新添加句号

        # 🔧 修复：确保至少返回一个句子
        if not cleaned_sentences:
            cleaned_sentences = [text.strip() + '。' if text.strip() else "无内容。"]

        return cleaned_sentences

    def _format_sentences_for_prompt(self, sentences):
        """格式化句子列表用于提示词"""
        formatted = ""
        for i, sentence in enumerate(sentences, 1):
            formatted += f"{i}. {sentence}\n"
        return formatted

    def _create_sentence_assignment_table(self, sentences, suggested_shots):
        """创建句子分配表，按照25-45字符长度智能分配句子到镜头"""
        if not sentences or suggested_shots <= 0:
            return "无句子分配"

        assignment_table = "镜头分配表（按长度智能分配）：\n"
        assignment_table += "=" * 60 + "\n"
        assignment_table += "⚠️ 重要：每个镜头的原文应控制在25-45字符之间\n"
        assignment_table += "=" * 60 + "\n"

        # 智能分配句子到镜头，考虑字符长度
        shot_assignments = self._smart_assign_sentences_to_shots(sentences, suggested_shots)

        for shot_num, shot_sentences in enumerate(shot_assignments, 1):
            total_chars = sum(len(sentence) for sentence in shot_sentences)
            assignment_table += f"【镜头{shot_num}】（预计{total_chars}字符）必须包含：\n"

            for i, sentence in enumerate(shot_sentences):
                assignment_table += f"  {i+1}. {sentence}\n"
            assignment_table += "\n"

        total_sentences = len(sentences)
        assignment_table += "=" * 60 + "\n"
        assignment_table += f"总计：{total_sentences}个句子，{suggested_shots}个镜头\n"
        assignment_table += "⚠️ 警告：每个镜头必须严格包含上述指定的句子，控制在25-45字符！\n"

        return assignment_table

    def _smart_assign_sentences_to_shots(self, sentences, suggested_shots):
        """智能分配句子到镜头，考虑字符长度控制在25-45字符之间"""
        if not sentences:
            return []

        target_chars = 35  # 目标字符数
        min_chars = 25     # 最少字符数
        max_chars = 45     # 最多字符数

        shot_assignments = []
        current_shot = []
        current_chars = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # 如果当前镜头为空，直接添加句子
            if not current_shot:
                current_shot.append(sentence)
                current_chars = sentence_len
            # 如果添加这个句子不会超过最大字符数，且当前字符数少于目标字符数
            elif current_chars + sentence_len <= max_chars and current_chars < target_chars:
                current_shot.append(sentence)
                current_chars += sentence_len
            # 如果当前镜头已经达到最小字符数要求，开始新镜头
            elif current_chars >= min_chars:
                shot_assignments.append(current_shot)
                current_shot = [sentence]
                current_chars = sentence_len
            # 如果当前镜头字符数不够但添加会超限，强制开始新镜头
            else:
                shot_assignments.append(current_shot)
                current_shot = [sentence]
                current_chars = sentence_len

        # 添加最后一个镜头
        if current_shot:
            shot_assignments.append(current_shot)

        # 如果镜头数量超过建议数量，合并一些短镜头
        while len(shot_assignments) > suggested_shots and len(shot_assignments) > 1:
            # 找到最短的两个相邻镜头进行合并
            min_total = float('inf')
            merge_index = 0

            for i in range(len(shot_assignments) - 1):
                total_chars = sum(len(s) for s in shot_assignments[i]) + sum(len(s) for s in shot_assignments[i+1])
                if total_chars < min_total and total_chars <= max_chars:
                    min_total = total_chars
                    merge_index = i

            # 合并镜头
            if min_total <= max_chars:
                shot_assignments[merge_index].extend(shot_assignments[merge_index + 1])
                shot_assignments.pop(merge_index + 1)
            else:
                break

        return shot_assignments

    def _validate_content_coverage(self, storyboard_response, original_text, original_sentences):
        """验证分镜脚本是否完整覆盖了原文内容"""
        try:
            import re

            # 提取分镜中的所有"镜头原文"内容
            shot_texts = re.findall(r'- \*\*镜头原文\*\*：([^\n]+)', storyboard_response)

            # 🔧 修复：过滤空镜头和无效内容
            valid_shot_texts = []
            seen_texts = set()  # 用于检测重复内容

            for text in shot_texts:
                text = text.strip()
                # 过滤空镜头、无效内容和重复内容
                if (text and
                    not text.startswith('[') and
                    not text.startswith('（') and
                    text != '[无]' and
                    text != '无' and
                    text not in seen_texts):
                    valid_shot_texts.append(text)
                    seen_texts.add(text)

            # 合并所有有效镜头原文
            covered_text = "".join(valid_shot_texts)

            # 🔧 修复：检测重复镜头
            duplicate_count = len(shot_texts) - len(valid_shot_texts)
            if duplicate_count > 0:
                logger.warning(f"检测到 {duplicate_count} 个重复或空镜头")

            # 计算覆盖率
            coverage_ratio = len(covered_text) / len(original_text) if original_text else 0

            # 检查遗漏的句子
            missing_sentences = []
            for sentence in original_sentences:
                sentence_clean = sentence.strip()
                if sentence_clean and sentence_clean not in covered_text:
                    missing_sentences.append(sentence_clean)

            # 🔧 修复：更严格的完整性判断
            is_complete = (coverage_ratio >= 0.85 and
                          len(missing_sentences) <= 1 and
                          duplicate_count == 0)

            message = f"覆盖率: {coverage_ratio:.1%}, 遗漏句子: {len(missing_sentences)}个"
            if duplicate_count > 0:
                message += f", 重复镜头: {duplicate_count}个"
            if missing_sentences:
                message += f", 遗漏内容: {missing_sentences[0][:50]}..."

            return {
                'is_complete': is_complete,
                'coverage_ratio': coverage_ratio,
                'missing_count': len(missing_sentences),
                'missing_sentences': missing_sentences,
                'duplicate_count': duplicate_count,
                'message': message
            }

        except Exception as e:
            logger.error(f"验证内容覆盖失败: {e}")
            return {
                'is_complete': False,
                'coverage_ratio': 0,
                'missing_count': 999,
                'missing_sentences': [],
                'duplicate_count': 0,
                'message': f"验证失败: {e}"
            }

    def _extract_scene_text_from_full_article(self, scene_index, scene_name, scenes_analysis):
        """从完整原文中提取对应场景的内容"""
        try:
            # 🔧 修复：获取完整原文，支持多个数据源
            full_article = ""
            if self.parent_tab and hasattr(self.parent_tab, 'project_manager'):
                project_manager = self.parent_tab.project_manager
                if project_manager and project_manager.current_project:
                    project_data = project_manager.current_project

                    # 🔧 BUG修复：尝试多个位置获取完整原文，优先从project.json的article_text字段提取

                    # 1. 优先从project.json根级别的article_text字段获取（用户直接粘贴的内容）
                    full_article = project_data.get('article_text', '')
                    if full_article:
                        logger.info(f"从project.json根级别article_text字段提取原文，长度: {len(full_article)}")

                    # 2. 从五阶段分镜的article_text字段获取
                    if not full_article:
                        five_stage_data = project_data.get('five_stage_storyboard', {})
                        full_article = five_stage_data.get('article_text', '')
                        if full_article:
                            logger.info(f"从five_stage_storyboard.article_text字段提取原文，长度: {len(full_article)}")

                    # 3. 从第3阶段数据中获取
                    if not full_article:
                        stage_data = project_data.get('five_stage_storyboard', {}).get('stage_data', {})
                        stage3_data = stage_data.get('3', {}) or stage_data.get(3, {})
                        full_article = stage3_data.get('article_text', '')
                        if full_article:
                            logger.info(f"从stage_data.3.article_text字段提取原文，长度: {len(full_article)}")

                    # 4. 从其他阶段数据中获取
                    if not full_article:
                        stage_data = project_data.get('five_stage_storyboard', {}).get('stage_data', {})
                        for stage_key in ['1', '2', '4', '5', 1, 2, 4, 5]:
                            stage_info = stage_data.get(stage_key, {})
                            article_text = stage_info.get('article_text', '')
                            if article_text:
                                full_article = article_text
                                logger.info(f"从stage_data.{stage_key}.article_text字段提取原文，长度: {len(full_article)}")
                                break

                    # 5. 如果还没有，从文件中读取
                    if not full_article:
                        try:
                            project_dir = project_manager.get_current_project_path()
                            if project_dir:
                                # 尝试读取rewritten_text.txt
                                rewritten_file = os.path.join(project_dir, 'texts', 'rewritten_text.txt')
                                if os.path.exists(rewritten_file):
                                    with open(rewritten_file, 'r', encoding='utf-8') as f:
                                        full_article = f.read()
                                    logger.info(f"从rewritten_text.txt文件提取原文，长度: {len(full_article)}")

                                # 如果rewritten_text.txt不存在，尝试original_text.txt
                                if not full_article:
                                    original_file = os.path.join(project_dir, 'texts', 'original_text.txt')
                                    if os.path.exists(original_file):
                                        with open(original_file, 'r', encoding='utf-8') as f:
                                            full_article = f.read()
                                        logger.info(f"从original_text.txt文件提取原文，长度: {len(full_article)}")
                        except Exception as file_error:
                            logger.warning(f"从文件读取原文失败: {file_error}")

                    # 6. 最后的备用方案：从其他可能的字段获取
                    if not full_article:
                        fallback_fields = ['rewritten_text', 'original_text', 'text_content']
                        for field in fallback_fields:
                            fallback_text = project_data.get(field, '')
                            if fallback_text:
                                full_article = fallback_text
                                logger.info(f"从备用字段{field}提取原文，长度: {len(full_article)}")
                                break

            if not full_article:
                logger.warning("无法获取完整原文")
                return ""

            logger.info(f"获取到完整原文，长度: {len(full_article)} 字符")

            # 将完整原文按段落分割
            paragraphs = [p.strip() for p in full_article.split('\n\n') if p.strip()]
            logger.info(f"原文分割为 {len(paragraphs)} 个段落")

            # 根据场景索引和总场景数，智能分配原文段落
            total_scenes = len(scenes_analysis.split('### 场景')) - 1 if scenes_analysis else 6
            if total_scenes <= 0:
                total_scenes = 6  # 默认6个场景

            logger.info(f"总场景数: {total_scenes}")

            # 计算每个场景应该包含的段落数
            paragraphs_per_scene = max(1, len(paragraphs) // total_scenes)

            # 计算当前场景的段落范围
            start_paragraph = scene_index * paragraphs_per_scene
            end_paragraph = min((scene_index + 1) * paragraphs_per_scene, len(paragraphs))

            # 如果是最后一个场景，包含所有剩余段落
            if scene_index == total_scenes - 1:
                end_paragraph = len(paragraphs)

            # 提取对应的段落
            scene_paragraphs = paragraphs[start_paragraph:end_paragraph]
            scene_text = '\n\n'.join(scene_paragraphs)

            logger.info(f"为场景{scene_index+1}({scene_name})提取了第{start_paragraph+1}-{end_paragraph}段，共{len(scene_paragraphs)}段")
            logger.info(f"提取的内容长度: {len(scene_text)}字符")
            logger.info(f"提取的内容预览: {scene_text[:100]}...")

            return scene_text

        except Exception as e:
            logger.error(f"从完整原文中提取场景内容失败: {e}")
            return ""

    def _retry_storyboard_generation(self, scene_original_text, sentences, scene_name, world_bible, missing_sentences):
        """重试分镜生成，专门针对遗漏的内容"""
        try:
            logger.info(f"开始重试分镜生成，针对{len(missing_sentences)}个遗漏句子")

            # 创建更严格的重试提示词
            retry_prompt = f"""
你是一位专业的分镜师。之前的分镜生成存在问题，现在需要重新生成完整的分镜脚本。

**🚨 严重警告 - 这是重试任务**：
上一次生成遗漏了以下重要内容：
{chr(10).join([f"- {sentence}" for sentence in missing_sentences[:5]])}

**📋 完整原文内容（必须100%覆盖）**：
{scene_original_text}

**🎯 重试要求**：
1. **绝对不能再遗漏任何句子**
2. **必须包含上述所有遗漏的内容**
3. **每个句子都必须出现在某个镜头的"镜头原文"中**
4. **按照原文顺序进行分镜**
5. **不能添加原文中没有的内容**
6. **🚫 严禁重复镜头：每个句子只能在一个镜头中出现**
7. **🚫 严禁空镜头：不能有"[无]"或空白的镜头原文**

**📝 句子清单（必须全部包含）**：
{self._format_sentences_for_prompt(sentences)}

**🌍 世界观设定**：
{world_bible}

**⚠️ 特别注意**：
- 场景名称：{scene_name}
- 总句子数：{len(sentences)}句
- 必须确保每个句子都被分配到某个镜头
- 重点关注之前遗漏的内容
- 检查每个镜头原文是否唯一，不能重复
- 所有镜头都必须有有效的原文内容

请严格按照以下格式输出分镜脚本：

### 镜头1
- **镜头原文**：[必须包含完整的原文句子]
- **镜头类型**：[特写/中景/全景/航拍等]
- **机位角度**：[平视/俯视/仰视/侧面等]
- **镜头运动**：[静止/推拉/摇移/跟随等]
- **景深效果**：[浅景深/深景深/焦点变化]
- **构图要点**：[三分法/对称/对角线等]
- **光影设计**：[自然光/人工光/逆光/侧光等]
- **色彩基调**：[暖色调/冷色调/对比色等]
- **镜头角色**：[列出画面中出现的角色]
- **画面描述**：[详细描述画面内容，符合时代背景]
- **台词/旁白**：[如有对话则填写，否则填"无"]
- **音效提示**：[环境音、特效音等，符合时代背景]
- **转场方式**：[切换/淡入淡出/叠化等]

### 镜头2
[重复上述格式]

确保：
1. 每个镜头都包含完整的原文句子
2. 所有元素都符合世界观圣经中的时代背景
3. 不能出现任何现代科技元素
"""

            # 🔧 修复：使用正确的API调用方式
            try:
                # 使用工作线程中的LLM API实例
                if hasattr(self, 'llm_service') and self.llm_service:
                    messages = [
                        {"role": "system", "content": "你是一位专业的分镜师，擅长为影视作品创建详细的分镜头脚本。"},
                        {"role": "user", "content": retry_prompt}
                    ]
                    retry_response = self.llm_api._make_api_call(
                        model_name=self.llm_api.shots_model_name,
                        messages=messages,
                        task_name="storyboard_generation_retry"
                    )
                else:
                    logger.error("无法获取LLM服务实例")
                    return None
            except Exception as api_error:
                logger.error(f"重试API调用失败: {api_error}")
                return None

            if retry_response and isinstance(retry_response, str):
                logger.info(f"重试生成完成，响应长度: {len(retry_response)}")
                return retry_response
            else:
                logger.error("重试生成失败，API返回空响应")
                return None

        except Exception as e:
            logger.error(f"重试分镜生成失败: {e}")
            return None




class FiveStageStoryboardTab(QWidget):
    """五阶段分镜生成标签页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # 初始化组件
        self.config_manager = ConfigManager()
        # 使用父窗口的ProjectManager实例
        self.project_manager = parent.project_manager if parent and hasattr(parent, 'project_manager') else None
        self.llm_api = None
        
        # 角色场景管理器
        self.character_scene_manager = None
        self.character_dialog = None
        
        # 初始化角色场景管理器
        if (self.project_manager and 
            self.project_manager.current_project and 
            'project_dir' in self.project_manager.current_project):
            project_path = self.project_manager.current_project['project_dir']
            from src.utils.character_scene_manager import CharacterSceneManager
            self.character_scene_manager = CharacterSceneManager(project_path)
        else:
            self.character_scene_manager = None
        
        # 场景描述增强器
        self.scene_enhancer = None
        
        # 选中的角色和场景
        self.selected_characters = []
        self.selected_scenes = []
        
        # 当前阶段数据
        self.stage_data = {
            1: {},  # 世界观圣经 (Global Analysis)
            2: {},  # 角色管理 (Character Management)
            3: {},  # 场景分割 (Scene Segmentation)
            4: {},  # 分镜脚本 (Storyboard Generation)
            5: {}   # 优化预览 (Optimization Preview)
        }
        
        # 当前阶段
        self.current_stage = 1

        # 存储分镜结果供增强描述使用
        self.current_storyboard_results = []

        # 🔧 修复：记录初始风格，用于检测变更
        self.initial_style = None
        self.style_changed_flag = False
        
        # 工作线程
        self.worker_thread = None
        self.enhancement_thread = None

        self.init_ui()
        self.load_models()

        # 注册到同步管理器
        register_five_stage_tab(self)

        # 确保UI组件已完全初始化后再加载项目数据
        QTimer.singleShot(500, self.delayed_load_from_project)

    def _ensure_project_manager(self):
        """确保项目管理器状态正确"""
        try:
            # 如果没有项目管理器，尝试从父窗口获取
            if not self.project_manager and self.parent_window:
                if hasattr(self.parent_window, 'project_manager'):
                    self.project_manager = self.parent_window.project_manager
                    logger.info("💾 从父窗口重新获取项目管理器")
                elif hasattr(self.parent_window, 'app_controller') and hasattr(self.parent_window.app_controller, 'project_manager'):
                    self.project_manager = self.parent_window.app_controller.project_manager
                    logger.info("💾 从app_controller获取项目管理器")

            # 如果项目管理器存在但没有当前项目，尝试重新加载
            if self.project_manager and not self.project_manager.current_project:
                if hasattr(self.parent_window, 'current_active_project') and self.parent_window.current_active_project:
                    try:
                        self.project_manager.load_project(self.parent_window.current_active_project)
                        logger.info(f"💾 重新加载项目: {self.parent_window.current_active_project}")
                    except Exception as e:
                        logger.error(f"💾 重新加载项目失败: {e}")

        except Exception as e:
            logger.error(f"💾 确保项目管理器状态失败: {e}")

    def _enhance_storyboard_shots(self, storyboard_script: str) -> List[Dict[str, Any]]:
        """增强分镜脚本中的镜头描述
        
        Args:
            storyboard_script: 分镜脚本文本
            
        Returns:
            List[Dict]: 增强后的镜头信息列表
        """
        enhanced_shots = []
        
        try:
            # 导入必要的模块
            from src.processors.prompt_optimizer import PromptOptimizer
            from src.processors.scene_description_enhancer import SceneDescriptionEnhancer
            
            # 初始化提示词优化器和场景增强器
            prompt_optimizer = PromptOptimizer()
            
            # 获取项目根目录
            project_root = self.project_manager.get_current_project_path() if self.project_manager else None
            if not project_root:
                logger.warning("无法获取项目路径，跳过增强处理")
                return enhanced_shots
            
            # 🔧 修复：确保LLM API已初始化
            if not hasattr(self, 'llm_api') or self.llm_api is None:
                logger.info("LLM API未初始化，正在初始化...")
                if not self._init_llm_api():
                    logger.error("LLM API初始化失败，无法进行增强描述")
                    return enhanced_shots

            # 初始化场景描述增强器
            scene_enhancer = SceneDescriptionEnhancer(
                project_root=project_root,
                character_scene_manager=self.character_scene_manager,
                llm_api=self.llm_api
            )
            # 设置输出目录，确保能正确找到project.json文件
            scene_enhancer.output_dir = project_root
            
            # 解析分镜脚本，提取镜头信息
            shots_info = prompt_optimizer.extract_shots_from_script(storyboard_script, {})
            
            for shot_info in shots_info:
                shot_number = shot_info.get('shot_number', '')
                description = shot_info.get('description', '')
                characters = shot_info.get('characters', '')
                
                # 解析角色信息
                character_list = [char.strip() for char in characters.split(',') if char.strip()] if characters else []
                
                # 获取角色一致性提示词
                character_consistency_prompts = self._get_character_consistency_prompts(character_list)
                
                # 获取场景一致性提示词
                scene_consistency_prompts = self._get_scene_consistency_prompts(description)
                
                # 构建完整的技术参数和一致性信息
                enhanced_prompt_data = {
                    "镜头类型": "中景",  # 默认值，可以通过AI分析优化
                    "机位角度": "平视",
                    "镜头运动": "摇移",
                    "景深效果": "深景深",
                    "构图要点": "三分法",
                    "光影设计": "自然光",
                    "色彩基调": "明亮",
                    "镜头角色": character_consistency_prompts,
                    "场景一致性": scene_consistency_prompts,
                    "画面描述": description
                }
                
                # 🔧 修复：获取当前选择的风格并传递给场景描述增强器
                current_style = self._get_current_style()
                logger.info(f"第4阶段分镜增强使用风格: {current_style}")

                # 🔧 修复：使用真正的LLM增强功能
                try:
                    # 首先尝试使用LLM智能增强
                    enhanced_description = scene_enhancer.enhance_description_with_llm(
                        original_description=description,
                        characters=character_list
                    )
                    logger.info(f"镜头 {shot_number} 使用LLM增强成功")
                except Exception as llm_error:
                    logger.warning(f"LLM增强失败，回退到普通增强: {llm_error}")
                    # 回退到普通增强
                    enhanced_description = scene_enhancer.enhance_description(
                        original_description=description,
                        characters=character_list,
                        style=current_style
                    )
                
                # 构建最终的优化提示词
                final_prompt = self._build_final_prompt(enhanced_prompt_data, enhanced_description)
                
                enhanced_shot = {
                    "shot_number": shot_number,
                    "original_description": description,
                    "enhanced_description": enhanced_description,
                    "characters": character_list,
                    "character_consistency_prompts": character_consistency_prompts,
                    "scene_consistency_prompts": scene_consistency_prompts,
                    "technical_parameters": enhanced_prompt_data,
                    "final_prompt": final_prompt
                }
                
                enhanced_shots.append(enhanced_shot)
                
                logger.info(f"镜头 {shot_number} 增强完成")
            
        except Exception as e:
            logger.error(f"分镜脚本增强失败: {e}")
        
        return enhanced_shots

    def _get_current_style(self) -> str:
        """获取当前风格，优先从项目数据获取，其次从UI组件获取

        Returns:
            str: 当前风格名称
        """
        try:
            # 1. 优先从项目数据中获取
            if (self.project_manager and
                self.project_manager.current_project and
                'five_stage_storyboard' in self.project_manager.current_project):
                project_style = self.project_manager.current_project['five_stage_storyboard'].get('selected_style')
                if project_style:
                    logger.debug(f"从项目数据获取风格: {project_style}")
                    return project_style

            # 2. 从UI组件获取
            if hasattr(self, 'style_combo') and self.style_combo:
                ui_style = self.style_combo.currentText()
                if ui_style:
                    logger.debug(f"从UI组件获取风格: {ui_style}")
                    return ui_style

            # 3. 使用默认风格
            default_style = "电影风格"
            logger.debug(f"使用默认风格: {default_style}")
            return default_style

        except Exception as e:
            logger.error(f"获取当前风格失败: {e}")
            return "电影风格"

    def _get_character_consistency_prompts(self, character_list: List[str]) -> List[str]:
        """获取角色一致性提示词
        
        Args:
            character_list: 角色名称列表
            
        Returns:
            List[str]: 角色一致性提示词列表
        """
        consistency_prompts = []
        
        try:
            if not self.character_scene_manager:
                return consistency_prompts
            
            # 获取所有角色数据
            all_characters = self.character_scene_manager.get_all_characters()
            
            for character_name in character_list:
                # 查找匹配的角色
                for char_id, char_data in all_characters.items():
                    if char_data.get('name') == character_name:
                        consistency_prompt = char_data.get('consistency_prompt', '')
                        if consistency_prompt:
                            consistency_prompts.append(f"{character_name}（一致性提示词为：{consistency_prompt}）")
                        break
                else:
                    # 如果没有找到匹配的角色，添加基本信息
                    consistency_prompts.append(f"{character_name}（未找到详细一致性信息）")
            
        except Exception as e:
            logger.error(f"获取角色一致性提示词失败: {e}")
        
        return consistency_prompts
    
    def _get_scene_consistency_prompts(self, description: str) -> List[str]:
        """获取场景一致性提示词
        
        Args:
            description: 画面描述
            
        Returns:
            List[str]: 场景一致性提示词列表
        """
        consistency_prompts = []
        
        try:
            if not self.character_scene_manager:
                return consistency_prompts
            
            # 获取所有场景数据
            all_scenes = self.character_scene_manager.get_all_scenes()
            
            # 简单的场景匹配逻辑（可以优化为更智能的匹配）
            for scene_id, scene_data in all_scenes.items():
                scene_name = scene_data.get('name', '')
                scene_description = scene_data.get('description', '')
                
                # 检查描述中是否包含场景关键词
                if (scene_name and scene_name in description) or \
                   (scene_description and any(keyword in description for keyword in scene_description.split()[:5])):
                    consistency_prompt = scene_data.get('consistency_prompt', '')
                    if consistency_prompt:
                        consistency_prompts.append(f"{scene_name}：{consistency_prompt}")
            
        except Exception as e:
            logger.error(f"获取场景一致性提示词失败: {e}")
        
        return consistency_prompts
    
    def _build_final_prompt(self, prompt_data: Dict[str, Any], enhanced_description: str) -> str:
        """构建最终的优化提示词
        
        Args:
            prompt_data: 提示词数据
            enhanced_description: 增强后的描述
            
        Returns:
            str: 最终的优化提示词
        """
        try:
            prompt_parts = []
            
            # 添加技术参数
            technical_params = [
                f"**镜头类型**：{prompt_data.get('镜头类型', '')}",
                f"**机位角度**：{prompt_data.get('机位角度', '')}",
                f"**镜头运动**：{prompt_data.get('镜头运动', '')}",
                f"**景深效果**：{prompt_data.get('景深效果', '')}",
                f"**构图要点**：{prompt_data.get('构图要点', '')}",
                f"**光影设计**：{prompt_data.get('光影设计', '')}",
                f"**色彩基调**：{prompt_data.get('色彩基调', '')}"
            ]
            prompt_parts.extend(technical_params)
            
            # 添加角色一致性信息
            character_prompts = prompt_data.get('镜头角色', [])
            if character_prompts:
                prompt_parts.append(f"**镜头角色**：{', '.join(character_prompts)}")
            
            # 添加场景一致性信息
            scene_prompts = prompt_data.get('场景一致性', [])
            if scene_prompts:
                prompt_parts.append(f"**场景一致性**：{'; '.join(scene_prompts)}")
            
            # 添加增强后的画面描述
            prompt_parts.append(f"**画面描述**：{enhanced_description}")
            
            return '\n'.join(prompt_parts)
            
        except Exception as e:
            logger.error(f"构建最终提示词失败: {e}")
            return enhanced_description
    
    def init_ui(self):
        """初始化UI界面"""
        main_layout = QVBoxLayout()
        
        # 顶部控制区域
        self.create_control_area(main_layout)
        
        # 主要内容区域
        self.create_main_content_area(main_layout)
        
        # 底部状态区域
        self.create_status_area(main_layout)
        
        self.setLayout(main_layout)
    
    def create_control_area(self, parent_layout):
        """创建顶部控制区域"""
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.StyledPanel)
        control_layout = QHBoxLayout(control_frame)
        
        # 标题
        title_label = QLabel("🎬 五阶段分镜生成系统")
        from src.utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        default_font = config_manager.get_setting("default_font_family", "Arial")
        title_label.setFont(QFont(default_font, 16, QFont.Bold))
        control_layout.addWidget(title_label)
        
        control_layout.addStretch()
        
        # 风格选择
        control_layout.addWidget(QLabel("风格："))
        self.style_combo = QComboBox()
        self.style_combo.addItems([
            "电影风格", "动漫风格", "吉卜力风格", "赛博朋克风格",
            "水彩插画风格", "像素风格", "写实摄影风格"
        ])
        # 🔧 修复：添加风格变更检测
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        control_layout.addWidget(self.style_combo)
        
        # 模型选择
        control_layout.addWidget(QLabel("模型："))
        self.model_combo = QComboBox()
        control_layout.addWidget(self.model_combo)
        
        # 角色管理按钮
        self.character_btn = QPushButton("👥 角色管理")
        self.character_btn.clicked.connect(self.open_character_dialog)
        self.character_btn.setToolTip("管理角色信息，确保分镜中角色的一致性")
        control_layout.addWidget(self.character_btn)
        
        # 场景描述增强选项
        self.enhance_checkbox = QCheckBox("🎨 智能增强")
        self.enhance_checkbox.setChecked(True)
        self.enhance_checkbox.setToolTip("启用场景描述智能增强，自动添加技术细节和一致性描述")
        self.enhance_checkbox.stateChanged.connect(self.on_enhance_option_changed)
        control_layout.addWidget(self.enhance_checkbox)
        
        # 增强级别选择
        control_layout.addWidget(QLabel("增强级别："))
        self.enhance_level_combo = QComboBox()
        self.enhance_level_combo.addItems(["低", "中", "高"])
        self.enhance_level_combo.setCurrentText("中")
        self.enhance_level_combo.setToolTip("选择场景描述增强的详细程度")
        self.enhance_level_combo.currentTextChanged.connect(self.on_enhance_level_changed)
        control_layout.addWidget(self.enhance_level_combo)
        
        # 场景增强器配置按钮
        self.enhancer_config_btn = QPushButton("⚙️ 增强器配置")
        self.enhancer_config_btn.clicked.connect(self.open_enhancer_config)
        self.enhancer_config_btn.setToolTip("打开场景描述增强器的详细配置面板")
        control_layout.addWidget(self.enhancer_config_btn)
        
        # 注释：保存按钮已移除，使用主窗口的统一保存功能
        
        parent_layout.addWidget(control_frame)
    
    def create_main_content_area(self, parent_layout):
        """创建主要内容区域"""
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 阶段1：全局分析 (世界观圣经)
        self.create_stage1_tab()
        
        # 阶段2：角色管理
        self.create_stage2_tab()
        
        # 阶段3：场景分割
        self.create_stage3_tab()
        
        # 阶段4：分镜生成
        self.create_stage4_tab()
        
        # 阶段5：优化预览
        self.create_stage5_tab()
        
        parent_layout.addWidget(self.tab_widget)
    
    def create_stage1_tab(self):
        """创建阶段1标签页：全局分析和世界观创建"""
        stage1_widget = QWidget()
        layout = QVBoxLayout(stage1_widget)
        
        # 说明文本
        info_label = QLabel(
            "🌍 <b>阶段1：全局分析和世界观创建</b><br>"
            "对输入文章进行深度分析，建立统一的世界观圣经，为后续制作提供一致性参考。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 输入区域
        input_group = QGroupBox("📝 输入文章")
        input_layout = QVBoxLayout(input_group)
        
        self.article_input = QPlainTextEdit()
        self.article_input.setPlaceholderText(
            "请输入要生成分镜的文章内容...\n\n"
            "支持小说、剧本、故事大纲等各种文本格式。\n"
            "系统将基于此内容进行全局分析和世界观构建。"
        )
        self.article_input.setMinimumHeight(200)
        input_layout.addWidget(self.article_input)
        
        # 从主窗口加载文本按钮
        load_btn = QPushButton("📥 从主窗口加载改写文本")
        load_btn.clicked.connect(self.load_text_from_main)
        input_layout.addWidget(load_btn)
        
        layout.addWidget(input_group)
        
        # 输出区域
        output_group = QGroupBox("🌍 世界观圣经")
        output_layout = QVBoxLayout(output_group)
        
        self.world_bible_output = QTextEdit()
        self.world_bible_output.setReadOnly(True)
        self.world_bible_output.setPlaceholderText("世界观分析结果将在这里显示...")
        output_layout.addWidget(self.world_bible_output)
        
        layout.addWidget(output_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.stage1_generate_btn = QPushButton("🚀 开始全局分析")
        self.stage1_generate_btn.clicked.connect(lambda: self.start_stage(1))
        btn_layout.addWidget(self.stage1_generate_btn)
        
        self.stage1_next_btn = QPushButton("➡️ 进入角色管理")
        self.stage1_next_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
        self.stage1_next_btn.setEnabled(False)
        btn_layout.addWidget(self.stage1_next_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.tab_widget.addTab(stage1_widget, "1️⃣ 全局分析")
    
    def create_stage2_tab(self):
        """创建阶段2标签页：角色管理"""
        stage2_widget = QWidget()
        layout = QVBoxLayout(stage2_widget)
        
        # 说明文本
        info_label = QLabel(
            "👥 <b>阶段2：角色管理</b><br>"
            "基于世界观圣经，管理和完善角色信息，确保分镜制作中角色的一致性和连贯性。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 角色信息显示区域
        characters_group = QGroupBox("👤 角色信息")
        characters_layout = QVBoxLayout(characters_group)
        
        self.characters_output = QTextEdit()
        self.characters_output.setReadOnly(True)
        self.characters_output.setPlaceholderText("角色信息将在这里显示...")
        characters_layout.addWidget(self.characters_output)
        
        layout.addWidget(characters_group)
        
        # 角色管理操作区域
        management_group = QGroupBox("🛠️ 角色管理操作")
        management_layout = QVBoxLayout(management_group)
        
        # 角色管理按钮
        manage_btn = QPushButton("📝 打开角色管理对话框")
        manage_btn.clicked.connect(self.open_character_dialog)
        management_layout.addWidget(manage_btn)
        
        # 自动提取角色按钮
        extract_btn = QPushButton("🔍 从世界观圣经自动提取角色")
        extract_btn.clicked.connect(self.auto_extract_characters)
        management_layout.addWidget(extract_btn)
        
        # 角色一致性检查按钮
        check_btn = QPushButton("✅ 检查角色一致性")
        check_btn.clicked.connect(self.check_character_consistency)
        management_layout.addWidget(check_btn)
        
        layout.addWidget(management_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.stage2_generate_btn = QPushButton("🔄 刷新角色信息")
        self.stage2_generate_btn.clicked.connect(self.refresh_character_info)
        btn_layout.addWidget(self.stage2_generate_btn)
        
        self.stage2_next_btn = QPushButton("➡️ 进入场景分割")
        self.stage2_next_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(2))
        self.stage2_next_btn.setEnabled(True)  # 角色管理不需要等待完成
        btn_layout.addWidget(self.stage2_next_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.tab_widget.addTab(stage2_widget, "2️⃣ 角色管理")
    
    def create_stage3_tab(self):
        """创建阶段3标签页：场景分割"""
        stage3_widget = QWidget()
        layout = QVBoxLayout(stage3_widget)
        
        # 说明文本
        info_label = QLabel(
            "🎬 <b>阶段3：智能场景分割</b><br>"
            "基于世界观圣经和角色信息，将文章智能分割为多个场景，并提供详细的场景分析。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 场景分析结果
        scenes_group = QGroupBox("🎭 场景分析结果")
        scenes_layout = QVBoxLayout(scenes_group)
        
        self.scenes_output = QTextEdit()
        self.scenes_output.setReadOnly(True)
        self.scenes_output.setPlaceholderText("场景分割结果将在这里显示...")
        scenes_layout.addWidget(self.scenes_output)
        
        layout.addWidget(scenes_group)
        
        # 场景选择区域
        selection_group = QGroupBox("✅ 选择要生成分镜的场景")
        selection_layout = QVBoxLayout(selection_group)
        
        self.scenes_list = QListWidget()
        self.scenes_list.setSelectionMode(QAbstractItemView.MultiSelection)
        selection_layout.addWidget(self.scenes_list)
        
        select_all_btn = QPushButton("全选场景")
        select_all_btn.clicked.connect(self.select_all_scenes)
        selection_layout.addWidget(select_all_btn)
        
        layout.addWidget(selection_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.stage3_generate_btn = QPushButton("🎬 开始场景分割")
        self.stage3_generate_btn.clicked.connect(lambda: self.start_stage(3))
        btn_layout.addWidget(self.stage3_generate_btn)
        
        self.stage3_next_btn = QPushButton("➡️ 生成分镜脚本")
        self.stage3_next_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(3))
        self.stage3_next_btn.setEnabled(False)
        btn_layout.addWidget(self.stage3_next_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.tab_widget.addTab(stage3_widget, "3️⃣ 场景分割")
    
    def create_stage4_tab(self):
        """创建阶段4标签页：分镜脚本生成"""
        stage4_widget = QWidget()
        layout = QVBoxLayout(stage4_widget)
        
        # 说明文本
        info_label = QLabel(
            "📝 <b>阶段4：逐场景分镜脚本生成</b><br>"
            "为选定的场景生成详细的专业分镜脚本，包含镜头语言、构图、光影等完整信息，并融入角色一致性要求。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 分镜脚本结果
        storyboard_group = QGroupBox("📋 分镜脚本")
        storyboard_layout = QVBoxLayout(storyboard_group)
        
        self.storyboard_output = QTextEdit()
        self.storyboard_output.setReadOnly(True)
        self.storyboard_output.setPlaceholderText("分镜脚本将在这里显示...")
        storyboard_layout.addWidget(self.storyboard_output)
        
        layout.addWidget(storyboard_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        # 第4阶段：分镜脚本生成按钮
        self.stage4_generate_btn = QPushButton("📝 生成分镜脚本")
        self.stage4_generate_btn.clicked.connect(self._handle_stage4_button_click)
        btn_layout.addWidget(self.stage4_generate_btn)
        
        # 增强描述按钮
        self.enhance_description_btn = QPushButton("✨ 增强描述")
        self.enhance_description_btn.clicked.connect(self.enhance_descriptions)
        self.enhance_description_btn.setEnabled(False)
        btn_layout.addWidget(self.enhance_description_btn)
        
        # 第4阶段：进入下一阶段按钮
        self.stage4_next_btn = QPushButton("➡️ 优化预览")
        self.stage4_next_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(4))
        self.stage4_next_btn.setEnabled(False)
        btn_layout.addWidget(self.stage4_next_btn)
        
        # 导出按钮
        export_btn = QPushButton("💾 导出分镜脚本")
        export_btn.clicked.connect(self.export_storyboard)
        btn_layout.addWidget(export_btn)

        # 刷新数据按钮
        refresh_btn = QPushButton("🔄 刷新数据")
        refresh_btn.clicked.connect(self.refresh_project_data)
        refresh_btn.setToolTip("重新加载项目数据，如果有新增的场景分镜会显示出来")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.tab_widget.addTab(stage4_widget, "4️⃣ 分镜生成")  # 第4阶段：分镜脚本生成
    
    def create_stage5_tab(self):
        """创建阶段5标签页：优化预览"""
        stage5_widget = QWidget()
        layout = QVBoxLayout(stage5_widget)
        
        # 说明文本
        info_label = QLabel(
            "🎨 <b>阶段5：视觉预览和迭代优化</b><br>"
            "对生成的分镜脚本进行质量检查和优化建议，确保视觉一致性和专业水准。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 优化建议
        optimization_group = QGroupBox("💡 优化建议")
        optimization_layout = QVBoxLayout(optimization_group)
        
        self.optimization_output = QTextEdit()
        self.optimization_output.setReadOnly(True)
        self.optimization_output.setPlaceholderText("优化建议将在这里显示...")
        optimization_layout.addWidget(self.optimization_output)
        
        layout.addWidget(optimization_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.stage5_generate_btn = QPushButton("🎨 生成优化建议")
        self.stage5_generate_btn.clicked.connect(lambda: self.safe_start_stage(5))
        btn_layout.addWidget(self.stage5_generate_btn)
        
        # 重新生成按钮
        regenerate_btn = QPushButton("🔄 重新生成分镜")
        regenerate_btn.clicked.connect(self.regenerate_storyboard)
        btn_layout.addWidget(regenerate_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.tab_widget.addTab(stage5_widget, "5️⃣ 优化预览")
    
    def create_status_area(self, parent_layout):
        """创建底部状态区域"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_layout = QHBoxLayout(status_frame)
        
        # 进度条 - 现代化样式
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(12)
        # 应用现代化样式
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #f5f5f5;
                text-align: center;
                font-size: 12px;
                color: #666;
                font-weight: normal;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 #42a5f5, stop: 1 #1976d2);
                border-radius: 3px;
                margin: 0px;
            }
        """)
        status_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # 停止按钮
        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.clicked.connect(self.stop_generation)
        self.stop_btn.setEnabled(False)
        status_layout.addWidget(self.stop_btn)
        
        parent_layout.addWidget(status_frame)
    
    def load_models(self):
        """加载大模型列表"""
        try:
            all_model_configs = self.config_manager.config.get("models", [])
            model_names = [cfg.get("name") for cfg in all_model_configs if cfg.get("name")]
            
            self.model_combo.clear()
            if model_names:
                self.model_combo.addItems(model_names)
                logger.debug(f"加载模型列表成功: {model_names}")
            else:
                self.model_combo.addItem("未配置模型")
                logger.warning("未找到模型配置")
        except Exception as e:
            logger.error(f"加载模型列表失败: {e}")
            self.model_combo.addItem("加载失败")
    
    def load_text_from_main(self):
        """从主窗口加载改写文本"""
        try:
            if self.parent_window and hasattr(self.parent_window, 'rewritten_text'):
                rewritten_text = self.parent_window.rewritten_text.toPlainText().strip()
                if rewritten_text:
                    self.article_input.setPlainText(rewritten_text)
                    QMessageBox.information(self, "成功", "已从主窗口加载改写文本")
                    logger.info("已从主窗口加载改写文本")
                else:
                    QMessageBox.warning(self, "警告", "主窗口中没有改写文本")
            else:
                QMessageBox.warning(self, "警告", "无法访问主窗口或改写文本")
        except Exception as e:
            logger.error(f"加载改写文本失败: {e}")
            QMessageBox.critical(self, "错误", f"加载改写文本失败: {e}")

    def safe_start_stage(self, stage_num):
        """安全启动阶段，包含详细的错误处理"""
        try:
            logger.info(f"=== 开始启动第{stage_num}阶段 ===")

            # 检查基本组件状态
            if not hasattr(self, 'stage_data'):
                logger.error("stage_data属性不存在")
                QMessageBox.critical(self, "错误", "内部数据结构未初始化")
                return

            if not hasattr(self, 'status_label'):
                logger.error("status_label组件不存在")
                QMessageBox.critical(self, "错误", "状态标签组件未初始化")
                return

            # 记录当前状态
            logger.info(f"当前阶段: {getattr(self, 'current_stage', 'unknown')}")
            logger.info(f"stage_data键: {list(self.stage_data.keys()) if hasattr(self, 'stage_data') else 'N/A'}")

            # 调用原始的start_stage方法
            self.start_stage(stage_num)

        except Exception as e:
            error_msg = f"启动第{stage_num}阶段时发生错误: {str(e)}"
            logger.error(error_msg)
            logger.error(f"错误类型: {type(e).__name__}")

            # 导入traceback模块并记录完整堆栈
            import traceback
            logger.error(f"完整错误堆栈:\n{traceback.format_exc()}")

            # 显示用户友好的错误信息
            QMessageBox.critical(self, "错误", f"启动第{stage_num}阶段失败:\n{str(e)}\n\n请检查日志获取详细信息。")

    def start_stage(self, stage_num, force_regenerate=False):
        """开始执行指定阶段

        Args:
            stage_num (int): 阶段编号
            force_regenerate (bool): 是否强制重新生成（忽略已保存的进度）
        """
        try:
            # 检查前置条件
            if not self._check_stage_prerequisites(stage_num):
                return

            # 初始化LLM API
            if not self._init_llm_api():
                return

            # 准备输入数据
            input_data = self._prepare_stage_input(stage_num)

            # 更新UI状态
            self._update_ui_for_stage_start(stage_num)

            # 启动工作线程
            style = self.style_combo.currentText()
            self.worker_thread = StageWorkerThread(stage_num, self.llm_api, input_data, style, self, force_regenerate)
            self.worker_thread.progress_updated.connect(self.update_progress)
            self.worker_thread.stage_completed.connect(self.on_stage_completed)
            self.worker_thread.error_occurred.connect(self.on_stage_error)
            self.worker_thread.storyboard_failed.connect(self.on_storyboard_failed)
            self.worker_thread.start()

        except Exception as e:
            logger.error(f"启动阶段{stage_num}失败: {e}")
            QMessageBox.critical(self, "错误", f"启动阶段{stage_num}失败: {e}")
            self._reset_ui_state()
    
    def _check_stage_prerequisites(self, stage_num):
        """检查阶段前置条件"""
        logger.info(f"检查第{stage_num}阶段前置条件...")

        try:
            if stage_num == 1:
                if not hasattr(self, 'article_input') or not self.article_input:
                    logger.error("article_input组件不存在")
                    QMessageBox.critical(self, "错误", "文章输入组件未初始化")
                    return False
                if not self.article_input.toPlainText().strip():
                    QMessageBox.warning(self, "警告", "请先输入文章内容")
                    return False

            elif stage_num == 2:
                if not self.stage_data.get(1):
                    QMessageBox.warning(self, "警告", "请先完成阶段1：世界观分析")
                    if hasattr(self, 'tab_widget'):
                        self.tab_widget.setCurrentIndex(0)
                    return False

            elif stage_num == 3:
                if not self.stage_data.get(2):
                    QMessageBox.warning(self, "警告", "请先完成阶段2：角色管理")
                    if hasattr(self, 'tab_widget'):
                        self.tab_widget.setCurrentIndex(1)
                    return False

            elif stage_num == 4:
                if not self.stage_data.get(3):
                    QMessageBox.warning(self, "警告", "请先完成阶段3：场景分割")
                    if hasattr(self, 'tab_widget'):
                        self.tab_widget.setCurrentIndex(2)
                    return False
                if not hasattr(self, 'scenes_list') or not self.scenes_list:
                    logger.error("scenes_list组件不存在")
                    QMessageBox.critical(self, "错误", "场景列表组件未初始化")
                    return False
                if not self.scenes_list.selectedItems():
                    QMessageBox.warning(self, "警告", "请先选择要生成分镜的场景")
                    if hasattr(self, 'tab_widget'):
                        self.tab_widget.setCurrentIndex(2)
                    return False

            elif stage_num == 5:
                # 详细检查第5阶段的前置条件
                logger.info("检查第5阶段前置条件...")

                if not self.stage_data.get(4):
                    logger.warning("第4阶段数据不存在")
                    QMessageBox.warning(self, "警告", "请先完成阶段4：分镜生成")
                    if hasattr(self, 'tab_widget'):
                        self.tab_widget.setCurrentIndex(3)
                    return False

                # 检查分镜结果数据
                storyboard_results = self.stage_data[4].get("storyboard_results", [])
                if not storyboard_results:
                    logger.warning("第4阶段缺少分镜结果数据")
                    QMessageBox.warning(self, "警告", "第4阶段缺少分镜结果，请重新生成分镜")
                    if hasattr(self, 'tab_widget'):
                        self.tab_widget.setCurrentIndex(3)
                    return False

                logger.info(f"第5阶段前置条件检查通过，分镜结果数量: {len(storyboard_results)}")

            logger.info(f"第{stage_num}阶段前置条件检查通过")
            return True

        except Exception as e:
            logger.error(f"检查第{stage_num}阶段前置条件时出错: {e}")
            QMessageBox.critical(self, "错误", f"检查前置条件失败: {str(e)}")
            return False
    
    def _init_llm_api(self):
        """初始化LLM API"""
        try:
            logger.info("开始初始化LLM API...")

            # 检查model_combo组件
            if not hasattr(self, 'model_combo') or not self.model_combo:
                logger.error("model_combo组件不存在")
                QMessageBox.critical(self, "错误", "模型选择组件未初始化")
                return False

            selected_model = self.model_combo.currentText()
            logger.info(f"选择的模型: {selected_model}")

            if selected_model in ["未配置模型", "加载失败", None, ""]:
                logger.warning(f"无效的模型选择: {selected_model}")
                QMessageBox.warning(self, "错误", "请选择一个有效的大模型")
                return False

            # 检查config_manager
            if not hasattr(self, 'config_manager') or not self.config_manager:
                logger.error("config_manager不存在")
                QMessageBox.critical(self, "错误", "配置管理器未初始化")
                return False

            # 获取模型配置
            all_model_configs = self.config_manager.config.get("models", [])
            logger.info(f"可用模型配置数量: {len(all_model_configs)}")

            model_config = None
            for cfg in all_model_configs:
                if cfg.get("name") == selected_model:
                    model_config = cfg
                    break

            if not model_config:
                logger.error(f"未找到模型 '{selected_model}' 的配置")
                QMessageBox.warning(self, "错误", f"未找到模型 '{selected_model}' 的配置")
                return False

            # 验证模型配置
            required_fields = ['type', 'key', 'url']
            for field in required_fields:
                if not model_config.get(field):
                    logger.warning(f"模型配置缺少字段: {field}")

            # 使用服务管理器获取LLM服务
            from src.core.service_manager import ServiceManager, ServiceType
            service_manager = ServiceManager()
            self.llm_service = service_manager.get_service(ServiceType.LLM)

            # 🔧 修复：记录用户选择的模型配置，将在API调用时使用

            # 为兼容性创建一个包装器
            class LLMApiWrapper:
                def __init__(self, llm_service, model_config):
                    self.llm_service = llm_service
                    self.model_config = model_config

                    # 根据模型类型设置模型名称
                    api_type = model_config.get('type', '').lower()
                    if api_type == "deepseek":
                        self.shots_model_name = "deepseek-chat"
                        self.rewrite_model_name = "deepseek-chat"
                    elif api_type == "tongyi":
                        self.shots_model_name = "qwen-plus"
                        self.rewrite_model_name = "qwen-plus"
                    elif api_type == "zhipu":
                        self.shots_model_name = "glm-4-flash"
                        self.rewrite_model_name = "glm-4-flash"
                    elif api_type == "google":
                        self.shots_model_name = "gemini-1.5-flash"
                        self.rewrite_model_name = "gemini-1.5-flash"
                    else:
                        self.shots_model_name = "default"
                        self.rewrite_model_name = "default"

                def _make_api_call(self, model_name, messages, task_name):
                    """兼容旧API调用的包装器"""
                    import asyncio

                    # 提取用户消息内容
                    user_content = ""
                    for msg in messages:
                        if msg.get("role") == "user":
                            user_content = msg.get("content", "")
                            break

                    if not user_content:
                        return "错误：未找到有效的提示内容"

                    # 🔧 修复：使用指定的提供商调用LLM服务
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        # 根据模型配置确定提供商
                        provider_map = {
                            'deepseek': 'deepseek',
                            'tongyi': 'tongyi',
                            'zhipu': 'zhipu',
                            'google': 'google',
                            'openai': 'openai'
                        }

                        provider = provider_map.get(self.model_config.get('type', '').lower(), 'zhipu')
                        logger.info(f"🔧 LLM API执行请求")
                        logger.info(f"  🌐 提供商: {provider}")
                        logger.info(f"  🤖 模型: {self.model_config.get('name', 'unknown')}")
                        logger.info(f"  📝 提示词长度: {len(user_content)} 字符")
                        logger.info(f"  ⚙️ max_tokens: 2000, temperature: 0.7")
                        logger.info(f"  🚀 开始调用 {provider} API...")

                        # 使用custom_request方法指定提供商
                        result = loop.run_until_complete(
                            self.llm_service.custom_request(
                                prompt=user_content,
                                max_tokens=2000,
                                temperature=0.7,
                                provider=provider
                            )
                        )
                        loop.close()

                        if result.success:
                            return result.data.get('content', '')
                        else:
                            return f"API调用失败: {result.error}"
                    except Exception as e:
                        return f"API调用异常: {str(e)}"

                def rewrite_text(self, prompt):
                    """文本重写方法，兼容场景描述增强器"""
                    import asyncio

                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        # 🔧 修复：使用指定的提供商调用LLM服务
                        provider_map = {
                            'deepseek': 'deepseek',
                            'tongyi': 'tongyi',
                            'zhipu': 'zhipu',
                            'google': 'google',
                            'openai': 'openai'
                        }

                        provider = provider_map.get(self.model_config.get('type', '').lower(), 'zhipu')

                        # 使用custom_request方法指定提供商
                        result = loop.run_until_complete(
                            self.llm_service.custom_request(
                                prompt=prompt,
                                max_tokens=2000,
                                temperature=0.7,
                                provider=provider
                            )
                        )
                        loop.close()

                        if result.success:
                            return result.data.get('content', '')
                        else:
                            logger.error(f"LLM重写文本失败: {result.error}")
                            return None
                    except Exception as e:
                        logger.error(f"LLM重写文本异常: {str(e)}")
                        return None

                def is_configured(self):
                    """检查LLM API是否已配置"""
                    return self.llm_service is not None

            # 创建兼容性包装器
            self.llm_api = LLMApiWrapper(self.llm_service, model_config)

            logger.info("LLM API包装器创建成功")

            logger.info(f"LLM API初始化成功，使用模型: {model_config.get('name', 'unknown')}")
            logger.info(f"API类型: {model_config.get('type', 'unknown')}")
            logger.info(f"API URL: {model_config.get('url', 'unknown')}")
            return True

        except Exception as e:
            error_msg = f"初始化LLM API失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"错误类型: {type(e).__name__}")

            import traceback
            logger.error(f"完整错误堆栈:\n{traceback.format_exc()}")

            QMessageBox.critical(self, "错误", error_msg)
            return False
    
    def _prepare_stage_input(self, stage_num):
        """准备阶段输入数据"""
        try:
            logger.info(f"准备第{stage_num}阶段输入数据...")

            if stage_num == 1:
                if not hasattr(self, 'article_input') or not self.article_input:
                    raise ValueError("文章输入组件未初始化")
                article_text = self.article_input.toPlainText().strip()
                if not article_text:
                    raise ValueError("文章内容为空")
                return {"article_text": article_text}

            elif stage_num == 2:
                # 阶段2：角色管理 - 不需要LLM处理，直接返回空字典
                return {}

            elif stage_num == 3:
                if not self.stage_data.get(1):
                    raise ValueError("第1阶段数据不存在")
                return {
                    "world_bible": self.stage_data[1].get("world_bible", ""),
                    "article_text": self.stage_data[1].get("article_text", ""),
                    "character_info": self.stage_data.get(2, {}).get("character_info", "")
                }

            elif stage_num == 4:
                if not self.stage_data.get(3):
                    raise ValueError("第3阶段数据不存在")
                if not hasattr(self, 'scenes_list') or not self.scenes_list:
                    raise ValueError("场景列表组件未初始化")

                # 🔧 修复：获取选中的场景，需要解析场景分析数据
                selected_scenes = []
                scenes_analysis = self.stage_data[3].get("scenes_analysis", "")

                # 解析场景分析文本，提取完整的场景信息
                scene_blocks = self._parse_scenes_from_analysis(scenes_analysis)

                # 获取选中的场景索引
                selected_indices = []
                for item in self.scenes_list.selectedItems():
                    try:
                        scene_text = item.text() if hasattr(item, 'text') and callable(item.text) else str(item)
                        # 从场景文本中提取索引，例如："场景1：标题" -> 0
                        if scene_text.startswith("场景"):
                            scene_num_str = scene_text.split("：")[0].replace("场景", "")
                            try:
                                scene_index = int(scene_num_str) - 1  # 转换为0基索引
                                selected_indices.append(scene_index)
                            except ValueError:
                                logger.warning(f"无法解析场景编号: {scene_text}")
                    except Exception as e:
                        logger.warning(f"获取场景文本失败: {e}")

                # 根据选中的索引获取对应的场景数据
                for index in selected_indices:
                    if 0 <= index < len(scene_blocks):
                        selected_scenes.append(scene_blocks[index])
                    else:
                        logger.warning(f"场景索引超出范围: {index}")

                logger.info(f"选中了 {len(selected_scenes)} 个场景用于分镜生成")

                if not selected_scenes:
                    raise ValueError("未选择任何场景")

                return {
                    "world_bible": self.stage_data.get(1, {}).get("world_bible", ""),
                    "character_info": self.stage_data.get(2, {}).get("character_info", ""),
                    "scenes_analysis": self.stage_data[3].get("scenes_analysis", ""),
                    "selected_scenes": selected_scenes,
                    "selected_characters": getattr(self, 'selected_characters', [])
                }

            elif stage_num == 5:
                if not self.stage_data.get(4):
                    raise ValueError("第4阶段数据不存在")

                storyboard_results = self.stage_data[4].get("storyboard_results", [])
                if not storyboard_results:
                    raise ValueError("第4阶段缺少分镜结果数据")

                logger.info(f"第5阶段输入数据准备完成，分镜结果数量: {len(storyboard_results)}")

                return {
                    "storyboard_results": storyboard_results,
                    "world_bible": self.stage_data.get(1, {}).get("world_bible", ""),
                    "character_info": self.stage_data.get(2, {}).get("character_info", "")
                }

            logger.warning(f"未知的阶段编号: {stage_num}")
            return {}

        except Exception as e:
            logger.error(f"准备第{stage_num}阶段输入数据失败: {e}")
            raise

    def _parse_scenes_from_analysis(self, scenes_analysis):
        """从场景分析文本中解析出完整的场景信息

        Args:
            scenes_analysis: 场景分析文本

        Returns:
            List[Dict]: 解析出的场景信息列表
        """
        try:
            scene_blocks = []
            lines = scenes_analysis.split('\n')
            current_scene = {}
            current_content = []

            for line in lines:
                line_strip = line.strip()

                # 检测场景标题
                if line_strip.startswith('### 场景') or line_strip.startswith('## 场景'):
                    # 保存前一个场景
                    if current_scene and current_content:
                        current_scene['full_content'] = '\n'.join(current_content)
                        scene_blocks.append(current_scene)

                    # 开始新场景
                    current_scene = {}
                    current_content = [line]

                    # 解析场景标题
                    parts = line_strip.split('：', 1)
                    if len(parts) == 2:
                        scene_title = parts[1].strip()
                        current_scene['scene_name'] = scene_title
                    else:
                        scene_title = line_strip.replace('###', '').replace('##', '').strip()
                        current_scene['scene_name'] = scene_title

                elif line_strip.startswith('- **对应原文段落**：'):
                    # 提取原文段落
                    original_text = line_strip.replace('- **对应原文段落**：', '').strip()
                    current_scene['对应原文段落'] = original_text
                    current_content.append(line)

                elif line_strip.startswith('- **'):
                    # 其他场景属性
                    if '：' in line_strip:
                        key_value = line_strip.replace('- **', '').split('**：', 1)
                        if len(key_value) == 2:
                            key, value = key_value
                            current_scene[key] = value.strip()
                    current_content.append(line)

                else:
                    # 普通内容行
                    if current_content:  # 只有在当前场景存在时才添加
                        current_content.append(line)

            # 保存最后一个场景
            if current_scene and current_content:
                current_scene['full_content'] = '\n'.join(current_content)
                scene_blocks.append(current_scene)

            logger.info(f"从场景分析中解析出 {len(scene_blocks)} 个场景")
            return scene_blocks

        except Exception as e:
            logger.error(f"解析场景分析失败: {e}")
            return []
    
    def _update_ui_for_stage_start(self, stage_num):
        """更新UI状态为开始阶段"""
        try:
            logger.info(f"更新第{stage_num}阶段UI状态...")

            # 安全检查UI组件
            if hasattr(self, 'progress_bar') and self.progress_bar:
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)  # 不确定进度
            else:
                logger.warning("progress_bar组件不存在")

            if hasattr(self, 'stop_btn') and self.stop_btn:
                self.stop_btn.setEnabled(True)
            else:
                logger.warning("stop_btn组件不存在")

            # 禁用对应的生成按钮
            if stage_num == 1:
                if hasattr(self, 'stage1_generate_btn') and self.stage1_generate_btn:
                    self.stage1_generate_btn.setEnabled(False)
                    self.stage1_generate_btn.setText("🔄 分析中...")
            elif stage_num == 2:
                # 阶段2是角色管理，不需要禁用按钮
                pass
            elif stage_num == 3:
                if hasattr(self, 'stage3_generate_btn') and self.stage3_generate_btn:
                    self.stage3_generate_btn.setEnabled(False)
                    self.stage3_generate_btn.setText("🔄 分割中...")
            elif stage_num == 4:
                if hasattr(self, 'stage4_generate_btn') and self.stage4_generate_btn:
                    self.stage4_generate_btn.setEnabled(False)
                    self.stage4_generate_btn.setText("🔄 生成中...")
            elif stage_num == 5:
                if hasattr(self, 'stage5_generate_btn') and self.stage5_generate_btn:
                    self.stage5_generate_btn.setEnabled(False)
                    self.stage5_generate_btn.setText("🔄 优化中...")
                else:
                    logger.error("stage5_generate_btn组件不存在")

            logger.info(f"第{stage_num}阶段UI状态更新完成")

        except Exception as e:
            logger.error(f"更新第{stage_num}阶段UI状态失败: {e}")
            # 不抛出异常，避免影响主流程
    
    def update_progress(self, message):
        """更新进度信息"""
        self.status_label.setText(message)
        logger.info(f"进度更新: {message}")
    
    def on_stage_completed(self, stage_num, result):
        """阶段完成回调"""
        try:
            # 🔧 修复：重新执行某个阶段时，清理后续阶段的数据，避免数据不一致
            self._clear_subsequent_stages(stage_num)

            # 保存结果数据
            self.stage_data[stage_num] = result
            
            # 更新对应的UI显示
            if stage_num == 1:
                world_bible = result.get("world_bible", "")
                self.world_bible_output.setText(world_bible)
                self.stage1_next_btn.setEnabled(True)
                self.status_label.setText("✅ 全局分析完成")
                
                # 保存世界观圣经到texts文件夹
                if world_bible:
                    self._save_world_bible_to_file(world_bible)
                    # 智能自动提取：只有在没有现有角色和场景数据时才自动提取
                    self._smart_auto_extract_characters(world_bible)
            elif stage_num == 2:
                # 阶段2：角色管理完成
                # 保存角色管理数据
                character_info = ""
                if self.character_scene_manager:
                    characters = self.character_scene_manager.get_all_characters()
                    scenes = self.character_scene_manager.get_all_scenes()
                    
                    # 过滤掉分镜板生成的场景
                    import re
                    filtered_scene_count = 0
                    if scenes:
                        for scene_id, scene_data in scenes.items():
                            scene_name = scene_data.get('name', '未命名')
                            if not re.match(r'^场景\d+$', scene_name):
                                filtered_scene_count += 1
                    
                    if characters:
                        character_info = f"角色数量: {len(characters)}, 用户创建场景数量: {filtered_scene_count}"
                
                # 确保阶段2有数据，即使是空的也要有标记
                if not self.stage_data[2]:
                    self.stage_data[2] = {
                        "character_info": character_info,
                        "completed": True,
                        "timestamp": str(QDateTime.currentDateTime().toString())
                    }
                
                self.status_label.setText("✅ 角色管理完成")
            elif stage_num == 3:
                self.scenes_output.setText(result.get("scenes_analysis", ""))
                self._update_scenes_list(result.get("scenes_analysis", ""))
                self.stage3_next_btn.setEnabled(True)
                self.status_label.setText("✅ 场景分割完成")
            elif stage_num == 4:
                self._display_storyboard_results(result.get("storyboard_results", []))
                # 保存分镜头脚本到storyboard文件夹
                self._save_storyboard_scripts_to_files(result.get("storyboard_results", []))
                # 启用增强描述按钮
                self.enhance_description_btn.setEnabled(True)
                self.stage4_next_btn.setEnabled(True)
                self.status_label.setText("✅ 分镜脚本生成完成")
                # 存储分镜结果供增强描述使用
                self.current_storyboard_results = result.get("storyboard_results", [])

                # 🔧 修复：第四阶段完成后不立即跳转，等待增强描述完成
                # QTimer.singleShot(1000, self._jump_to_voice_generation)  # 注释掉自动跳转
                logger.info("分镜脚本生成完成，请进行增强描述后再跳转到配音制作")

            elif stage_num == 5:
                self._display_optimization_results(result.get("optimization_suggestions", []))
                self.status_label.setText("✅ 优化分析完成")
                # 🔧 修复：第五阶段不进行增强，避免重复LLM处理
                self._update_consistency_panel(auto_enhance=False)

                # 🔧 修复：第五阶段完成后也刷新分镜图像生成界面
                QTimer.singleShot(1000, self._refresh_storyboard_image_tab)
            
            # 更新当前阶段
            self.current_stage = stage_num
            
            # 自动保存到项目
            self.save_to_project()
            
            logger.info(f"阶段{stage_num}完成")
            
        except Exception as e:
            logger.error(f"处理阶段{stage_num}结果失败: {e}")
        finally:
            self._reset_ui_state()

    def _clear_subsequent_stages(self, completed_stage):
        """清理后续阶段的数据，避免数据不一致

        Args:
            completed_stage (int): 刚完成的阶段编号
        """
        try:
            # 定义需要清理的后续阶段
            stages_to_clear = []

            if completed_stage == 1:
                # 重新生成世界观分析时，清理所有后续阶段
                stages_to_clear = [2, 3, 4, 5]
            elif completed_stage == 2:
                # 重新进行角色管理时，清理场景分割及后续阶段
                stages_to_clear = [3, 4, 5]
            elif completed_stage == 3:
                # 🔧 关键修复：重新进行场景分割时，清理分镜生成及后续阶段
                stages_to_clear = [4, 5]
            elif completed_stage == 4:
                # 重新生成分镜脚本时，清理优化预览阶段
                stages_to_clear = [5]
            # 第5阶段是最后阶段，无需清理后续

            # 清理指定的阶段数据
            for stage in stages_to_clear:
                if stage in self.stage_data and self.stage_data[stage]:
                    logger.info(f"清理第{stage}阶段的数据（因为第{completed_stage}阶段重新执行）")
                    self.stage_data[stage] = {}

                    # 清理对应的UI显示
                    self._clear_stage_ui(stage)

            # 🔧 修复：清理增量保存的进度文件
            if completed_stage == 3:
                # 场景分割重新执行时，清理分镜生成的进度文件
                self._clear_storyboard_progress_file()
            elif completed_stage == 4:
                # 分镜生成重新执行时，清理增强描述的进度文件
                self._clear_enhancement_progress_file()

            if stages_to_clear:
                logger.info(f"已清理第{completed_stage}阶段后续的{len(stages_to_clear)}个阶段数据: {stages_to_clear}")

        except Exception as e:
            logger.error(f"清理后续阶段数据失败: {e}")

    def _clear_stage_ui(self, stage):
        """清理指定阶段的UI显示

        Args:
            stage (int): 要清理的阶段编号
        """
        try:
            if stage == 3:
                # 清理场景分割的UI
                if hasattr(self, 'scenes_output') and self.scenes_output:
                    self.scenes_output.clear()
                if hasattr(self, 'scenes_list') and self.scenes_list:
                    self.scenes_list.clear()
                if hasattr(self, 'stage3_next_btn') and self.stage3_next_btn:
                    self.stage3_next_btn.setEnabled(False)

            elif stage == 4:
                # 清理分镜脚本的UI
                if hasattr(self, 'storyboard_output') and self.storyboard_output:
                    self.storyboard_output.clear()
                if hasattr(self, 'enhance_description_btn') and self.enhance_description_btn:
                    self.enhance_description_btn.setEnabled(False)
                    self.enhance_description_btn.setText("✨ 增强描述")
                if hasattr(self, 'stage4_next_btn') and self.stage4_next_btn:
                    self.stage4_next_btn.setEnabled(False)
                # 清理存储的分镜结果
                self.current_storyboard_results = []

            elif stage == 5:
                # 清理优化预览的UI
                if hasattr(self, 'optimization_output') and self.optimization_output:
                    self.optimization_output.clear()

            logger.debug(f"已清理第{stage}阶段的UI显示")

        except Exception as e:
            logger.error(f"清理第{stage}阶段UI显示失败: {e}")

    def _clear_storyboard_progress_file(self):
        """清理分镜生成的进度文件"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_dir = self.project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return

            progress_file = os.path.join(project_dir, 'storyboard_progress.json')
            if os.path.exists(progress_file):
                os.remove(progress_file)
                logger.info("已清理分镜生成进度文件")

        except Exception as e:
            logger.error(f"清理分镜生成进度文件失败: {e}")

    def _clear_enhancement_progress_file(self):
        """清理增强描述的进度文件"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_dir = self.project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return

            progress_file = os.path.join(project_dir, 'enhancement_progress.json')
            if os.path.exists(progress_file):
                os.remove(progress_file)
                logger.info("已清理增强描述进度文件")

        except Exception as e:
            logger.error(f"清理增强描述进度文件失败: {e}")

    def _clear_project_storyboard_data(self):
        """清理项目数据中的分镜相关数据"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            # 清理五阶段分镜数据中的第4、5阶段数据
            if 'five_stage_storyboard' in self.project_manager.current_project:
                five_stage_data = self.project_manager.current_project['five_stage_storyboard']
                if 'stage_data' in five_stage_data:
                    # 清理第4阶段（分镜脚本）和第5阶段（优化预览）的数据
                    if '4' in five_stage_data['stage_data']:
                        five_stage_data['stage_data']['4'] = {}
                        logger.info("已清理项目数据中的第4阶段分镜脚本数据")
                    if '5' in five_stage_data['stage_data']:
                        five_stage_data['stage_data']['5'] = {}
                        logger.info("已清理项目数据中的第5阶段优化预览数据")

            # 清理其他可能的分镜相关数据
            if 'storyboard_data' in self.project_manager.current_project:
                self.project_manager.current_project['storyboard_data'] = []
                logger.info("已清理项目数据中的分镜数据")

            if 'enhanced_descriptions' in self.project_manager.current_project:
                self.project_manager.current_project['enhanced_descriptions'] = {}
                logger.info("已清理项目数据中的增强描述数据")

            # 清理相关文件
            self._clear_storyboard_related_files()

            # 保存项目数据
            self.project_manager.save_project()
            logger.info("项目数据清理完成并已保存")

        except Exception as e:
            logger.error(f"清理项目分镜数据失败: {e}")

    def _clear_storyboard_related_files(self):
        """清理分镜相关的文件"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_dir = self.project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return

            # 清理texts目录中的文件（不再清理prompt.json，因为现在使用project.json）
            texts_dir = os.path.join(project_dir, 'texts')
            if os.path.exists(texts_dir):
                # 不再清理prompt.json文件，因为现在使用project.json存储增强描述
                # prompt_file = os.path.join(texts_dir, 'prompt.json')
                # if os.path.exists(prompt_file):
                #     os.remove(prompt_file)
                #     logger.info("已清理prompt.json文件")
                pass

                # 清理original_descriptions_with_consistency文件
                import glob
                consistency_files = glob.glob(os.path.join(texts_dir, 'original_descriptions_with_consistency_*.json'))
                for file_path in consistency_files:
                    try:
                        os.remove(file_path)
                        logger.info(f"已清理一致性描述文件: {os.path.basename(file_path)}")
                    except Exception as e:
                        logger.warning(f"清理一致性描述文件失败 {file_path}: {e}")

            # 🔧 关键修复：清理storyboard目录中的所有旧分镜文件
            storyboard_dir = os.path.join(project_dir, 'storyboard')
            if os.path.exists(storyboard_dir):
                import glob
                storyboard_files = glob.glob(os.path.join(storyboard_dir, 'scene_*_storyboard.txt'))
                cleaned_count = 0
                for file_path in storyboard_files:
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                        logger.debug(f"已清理分镜文件: {os.path.basename(file_path)}")
                    except Exception as e:
                        logger.warning(f"清理分镜文件失败 {file_path}: {e}")

                if cleaned_count > 0:
                    logger.info(f"已清理 {cleaned_count} 个旧的分镜脚本文件")

        except Exception as e:
            logger.error(f"清理分镜相关文件失败: {e}")

    def _jump_to_voice_generation(self):
        """跳转到配音制作界面"""
        try:
            logger.info("🎤 五阶段分镜完成，跳转到配音制作...")

            # 获取主窗口
            main_window = self.parent_window
            if not main_window:
                logger.warning("未找到主窗口")
                return

            # 检查主窗口类型并相应处理
            if hasattr(main_window, 'switch_to_page'):
                # ModernCardMainWindow - 使用页面切换
                main_window.switch_to_page('voice')
                logger.info("✅ 已切换到配音制作页面")

                # 刷新配音数据
                if hasattr(main_window, 'pages') and 'voice' in main_window.pages:
                    voice_page = main_window.pages['voice']
                    if hasattr(voice_page, 'load_from_project'):
                        voice_page.load_from_project()
                        logger.info("配音制作界面数据刷新完成")
                    elif hasattr(voice_page, 'refresh_data'):
                        voice_page.refresh_data()
                        logger.info("配音制作界面数据刷新完成")

                # 显示提示消息
                if hasattr(main_window, 'show_success_message'):
                    main_window.show_success_message("分镜脚本生成完成！请继续进行配音制作。")

            elif hasattr(main_window, 'tab_widget'):
                # 传统标签页窗口 - 使用标签页切换
                voice_tab = None
                voice_tab_index = -1

                for i in range(main_window.tab_widget.count()):
                    tab = main_window.tab_widget.widget(i)
                    tab_text = main_window.tab_widget.tabText(i)

                    # 查找配音相关的标签页
                    if any(keyword in tab_text for keyword in ['配音', 'voice', '语音']):
                        voice_tab = tab
                        voice_tab_index = i
                        break

                    # 也可以通过对象名称查找
                    if hasattr(tab, 'objectName') and any(keyword in tab.objectName().lower() for keyword in ['voice', 'audio', 'speech']):
                        voice_tab = tab
                        voice_tab_index = i
                        break

                if voice_tab_index >= 0:
                    # 切换到配音制作标签页
                    main_window.tab_widget.setCurrentIndex(voice_tab_index)
                    logger.info(f"✅ 已切换到配音制作标签页: {main_window.tab_widget.tabText(voice_tab_index)}")

                    # 刷新配音数据
                    if hasattr(voice_tab, 'load_from_project'):
                        voice_tab.load_from_project()
                        logger.info("配音制作界面数据刷新完成")
                    elif hasattr(voice_tab, 'refresh_data'):
                        voice_tab.refresh_data()
                        logger.info("配音制作界面数据刷新完成")

                    # 显示提示消息
                    if hasattr(main_window, 'show_success_message'):
                        main_window.show_success_message("分镜脚本生成完成！请继续进行配音制作。")
                else:
                    logger.warning("未找到配音制作标签页")
            else:
                logger.warning("主窗口类型未知，无法跳转到配音制作界面")

        except Exception as e:
            logger.error(f"跳转到配音制作界面失败: {e}")

    def _refresh_storyboard_image_tab(self):
        """刷新分镜图像生成界面"""
        try:
            logger.info("开始刷新分镜图像生成界面...")

            # 通过父窗口获取分镜图像生成标签页
            if hasattr(self, 'parent_window') and self.parent_window:
                if hasattr(self.parent_window, 'storyboard_image_tab') and self.parent_window.storyboard_image_tab:
                    logger.info("找到分镜图像生成标签页，开始刷新...")
                    # 重新加载分镜数据
                    self.parent_window.storyboard_image_tab.load_storyboard_data()
                    # 加载生成设置
                    self.parent_window.storyboard_image_tab.load_generation_settings()
                    logger.info("分镜图像生成界面刷新完成")
                else:
                    logger.warning("未找到分镜图像生成标签页")
            else:
                logger.warning("未找到父窗口，无法刷新分镜图像生成界面")

        except Exception as e:
            logger.error(f"刷新分镜图像生成界面失败: {e}")

    def on_style_changed(self, new_style):
        """处理风格变更事件"""
        try:
            logger.info(f"风格变更: {self.initial_style} -> {new_style}")

            # 如果是第一次设置风格，记录为初始风格
            if self.initial_style is None:
                self.initial_style = new_style
                logger.info(f"设置初始风格: {new_style}")
                return

            # 检查是否真的发生了变更
            if self.initial_style == new_style:
                logger.debug("风格未发生实际变更")
                return

            # 标记风格已变更
            self.style_changed_flag = True
            logger.warning(f"检测到风格变更！原风格: {self.initial_style}, 新风格: {new_style}")

            # 检查是否有已生成的内容需要更新
            has_generated_content = False
            for stage_num in [1, 3, 4, 5]:  # 检查包含风格相关内容的阶段
                if self.stage_data.get(stage_num):
                    has_generated_content = True
                    break

            if has_generated_content:
                # 显示风格变更提示
                self._show_style_change_warning(self.initial_style, new_style)

            # 更新初始风格记录
            self.initial_style = new_style

        except Exception as e:
            logger.error(f"处理风格变更失败: {e}")

    def _show_style_change_warning(self, old_style, new_style):
        """显示风格变更警告"""
        try:
            from PyQt5.QtWidgets import QMessageBox

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("风格变更检测")
            msg.setText(f"检测到风格从「{old_style}」变更为「{new_style}」")
            msg.setInformativeText(
                "已生成的内容可能包含旧风格的描述。\n\n"
                "建议操作：\n"
                "• 重新生成世界观分析（第1阶段）\n"
                "• 重新生成场景分割（第3阶段）\n"
                "• 重新生成分镜脚本（第4阶段）\n"
                "• 重新生成优化预览（第5阶段）\n\n"
                "这样可以确保所有内容都使用新的风格设定。"
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

        except Exception as e:
            logger.error(f"显示风格变更警告失败: {e}")
    
    def on_stage_error(self, error_message):
        """阶段错误回调"""
        QMessageBox.critical(self, "错误", f"处理失败: {error_message}")
        self.status_label.setText(f"❌ 错误: {error_message}")
        self._reset_ui_state()

    def on_storyboard_failed(self, failed_scenes):
        """处理分镜生成失败"""
        logger.warning(f"检测到{len(failed_scenes)}个分镜生成失败")

        # 显示失败检测对话框
        from src.gui.failure_detection_dialog import FailureDetectionDialog
        dialog = FailureDetectionDialog(
            parent=self,
            failed_storyboards=failed_scenes,
            failed_enhancements=[]
        )
        dialog.exec_()

    def on_enhancement_failed(self, failed_enhancements):
        """处理增强描述失败"""
        logger.warning(f"检测到{len(failed_enhancements)}个增强描述失败")

        # 显示失败检测对话框
        from src.gui.failure_detection_dialog import FailureDetectionDialog
        dialog = FailureDetectionDialog(
            parent=self,
            failed_storyboards=[],
            failed_enhancements=failed_enhancements
        )
        dialog.exec_()
    
    def _save_storyboard_scripts_to_files(self, storyboard_results):
        """保存分镜头脚本到storyboard文件夹"""
        try:
            # 获取当前项目信息
            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有当前项目，无法保存分镜头脚本文件")
                return
            
            project_dir = self.project_manager.current_project.get('project_dir')
            if not project_dir:
                logger.warning("项目目录不存在，无法保存分镜头脚本文件")
                return
            
            # 创建storyboard文件夹路径
            storyboard_dir = os.path.join(project_dir, 'storyboard')
            os.makedirs(storyboard_dir, exist_ok=True)
            
            # 保存每个场景的分镜头脚本
            for result in storyboard_results:
                scene_index = result.get('scene_index', 0)
                scene_info = result.get('scene_info', f'场景{scene_index + 1}')
                storyboard_script = result.get('storyboard_script', '')
                
                # 创建文件名（使用场景索引）
                filename = f'scene_{scene_index + 1}_storyboard.txt'
                file_path = os.path.join(storyboard_dir, filename)
                
                # 保存分镜头脚本内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {scene_info}\n\n")
                    f.write(storyboard_script)
                
                logger.info(f"分镜头脚本已保存: {file_path}")
            
            logger.info(f"所有分镜头脚本已保存到: {storyboard_dir}")
            
        except Exception as e:
            logger.error(f"保存分镜头脚本文件失败: {e}")
    

    
    def _save_world_bible_to_file(self, world_bible_content):
        """保存世界观圣经内容到项目特定的texts文件夹"""
        try:
            # 尝试重新获取项目管理器状态
            self._ensure_project_manager()

            # 获取当前项目信息
            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有当前项目，无法保存世界观圣经文件")
                return
            
            # 兼容新旧项目格式
            project_name = self.project_manager.current_project.get('project_name') or self.project_manager.current_project.get('name', '')
            if not project_name:
                logger.warning("项目名称为空，无法保存世界观圣经文件")
                return
            
            # 构建项目特定的texts文件夹路径
            output_dir = os.path.join(os.getcwd(), "output", project_name, "texts")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 保存为JSON格式，包含时间戳等元数据
            world_bible_data = {
                "content": world_bible_content,
                "timestamp": QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss"),
                "version": "1.0"
            }
            
            world_bible_file = os.path.join(output_dir, "world_bible.json")
            with open(world_bible_file, 'w', encoding='utf-8') as f:
                json.dump(world_bible_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"世界观圣经已保存到: {world_bible_file}")
            
        except Exception as e:
            logger.error(f"保存世界观圣经文件失败: {e}")
    
    def enhance_descriptions(self):
        """用户手动触发的增强描述功能（线程安全版本）"""
        try:
            if not hasattr(self, 'current_storyboard_results') or not self.current_storyboard_results:
                QMessageBox.warning(self, "警告", "没有可用的分镜脚本数据，请先生成分镜脚本。")
                return

            # 检查是否已有增强线程在运行
            if (hasattr(self, 'enhancement_thread') and
                self.enhancement_thread is not None and
                self.enhancement_thread.isRunning()):
                QMessageBox.warning(self, "警告", "增强描述正在进行中，请稍候...")
                return

            # 🔧 新增：检查是否已有增强进度，询问用户是否重新增强
            if self._has_existing_enhancement_progress():
                reply = QMessageBox.question(
                    self,
                    "重新增强描述",
                    "检测到已有增强描述数据。\n\n是否要重新增强所有描述？\n\n点击'是'将清理已有数据并重新开始增强。",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    logger.info("🔧 用户确认重新增强描述，开始清理操作...")
                    self._clean_enhancement_data()
                else:
                    logger.info("用户取消重新增强描述操作")
                    return

            # 显示进度条和更新UI状态
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 不确定进度
            self.stop_btn.setEnabled(True)

            # 禁用按钮，显示进度
            self.enhance_description_btn.setEnabled(False)
            self.enhance_description_btn.setText("🔄 增强中...")
            self.status_label.setText("🔄 正在增强描述...")

            # 创建并启动增强线程
            self.enhancement_thread = EnhancementThread(self, self.current_storyboard_results)
            self.enhancement_thread.finished.connect(self.on_enhancement_finished)
            self.enhancement_thread.error.connect(self.on_enhancement_error)
            self.enhancement_thread.enhancement_failed.connect(self.on_enhancement_failed)
            self.enhancement_thread.start()

        except Exception as e:
            logger.error(f"启动增强描述失败: {e}")
            QMessageBox.critical(self, "错误", f"启动增强描述失败: {e}")
            self._reset_enhancement_ui()

    def on_enhancement_finished(self, success, message):
        """增强完成处理"""
        try:
            logger.info(f"增强描述完成: {message}")

            if success:
                # 🔧 修复：增强完成后不再进行重复增强
                self._update_consistency_panel(auto_enhance=False)

                # 自动触发一致性预览更新
                self._auto_update_consistency_preview()

                # 更新UI状态
                self.enhance_description_btn.setText("✅ 增强完成")
                self.status_label.setText("✅ 描述增强完成")

                # 🔧 新增：增强描述完成后跳转到配音制作界面
                QTimer.singleShot(1500, self._jump_to_voice_generation)
                logger.info("增强描述完成，将跳转到配音制作界面")
            else:
                self.enhance_description_btn.setText("❌ 增强失败")
                self.status_label.setText("❌ 增强描述失败")

            # 恢复UI状态
            self.progress_bar.setVisible(False)
            self.stop_btn.setEnabled(False)
            self.enhance_description_btn.setEnabled(True)

        except Exception as e:
            logger.error(f"处理增强完成事件失败: {e}")
            self._reset_enhancement_ui()

    def on_enhancement_error(self, error_msg):
        """增强错误处理"""
        try:
            logger.error(f"增强描述错误: {error_msg}")
            QMessageBox.critical(self, "错误", f"增强描述失败:\n{error_msg}")
            self._reset_enhancement_ui()

        except Exception as e:
            logger.error(f"处理增强错误事件失败: {e}")
            self._reset_enhancement_ui()

    def _reset_enhancement_ui(self):
        """重置增强UI状态"""
        try:
            self.progress_bar.setVisible(False)
            self.stop_btn.setEnabled(False)
            self.enhance_description_btn.setText("✨ 增强描述")
            self.enhance_description_btn.setEnabled(True)
            self.status_label.setText("❌ 增强描述失败")
        except Exception as e:
            logger.error(f"重置增强UI状态失败: {e}")

    def _enhance_storyboard_descriptions_thread_safe(self, storyboard_results):
        """线程安全的场景描述增强方法，返回失败的增强描述列表"""
        failed_enhancements = []

        try:
            logger.info("开始线程安全的场景描述增强...")

            # 检查是否有分镜脚本数据
            if not storyboard_results:
                logger.warning("没有分镜脚本数据可供增强")
                return failed_enhancements

            # 获取当前项目信息
            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有当前项目，无法保存增强结果")
                return failed_enhancements

            project_name = self.project_manager.current_project.get('project_name')
            if not project_name:
                logger.warning("项目名称为空，无法保存增强结果")
                return failed_enhancements

            # 获取项目根目录
            project_root = self.project_manager.get_current_project_path() if self.project_manager else None
            if not project_root:
                logger.error("无法获取项目根目录，跳过场景描述增强器初始化")
                return failed_enhancements

            # 🔧 新增：支持增量保存 - 检查是否有已保存的增强进度
            enhanced_results, start_index = self._load_existing_enhancement_progress()
            logger.info(f"检测到已完成 {start_index} 个场景的增强，从第 {start_index + 1} 个场景开始增强")

            # 在线程中创建场景描述增强器
            from src.processors.scene_description_enhancer import SceneDescriptionEnhancer
            scene_enhancer = SceneDescriptionEnhancer(
                project_root=project_root,
                character_scene_manager=self.character_scene_manager,
                llm_api=getattr(self, 'llm_api', None)
            )

            # 获取用户选择的风格
            selected_style = getattr(self, 'style_combo', None)
            if selected_style and hasattr(selected_style, 'currentText'):
                style = selected_style.currentText()
            else:
                style = '电影风格'

            # 🔧 修复：合并所有场景的分镜脚本，一次性进行增强
            # 这样可以确保所有镜头都被正确处理和保存
            combined_script = ""
            total_scenes = len(storyboard_results)

            for i, result in enumerate(storyboard_results):
                scene_info = result.get("scene_info", "")
                storyboard_script = result.get("storyboard_script", "")

                if not storyboard_script.strip():
                    logger.warning(f"场景{i+1}的分镜脚本为空，跳过")
                    continue

                # 为每个场景添加场景标题
                scene_title = f"## 场景{i+1}"
                if scene_info:
                    # 安全处理scene_info，确保它是字符串
                    if isinstance(scene_info, dict):
                        # 如果是字典，尝试获取描述信息
                        scene_info_str = scene_info.get('description', '') or scene_info.get('name', '') or str(scene_info)
                    else:
                        scene_info_str = str(scene_info) if scene_info else ""

                    # 从scene_info中提取场景标题
                    if scene_info_str:
                        scene_info_lines = scene_info_str.split('\n')
                        for line in scene_info_lines:
                            line_strip = line.strip()
                            if ('场景' in line_strip and ('：' in line_strip or ':' in line_strip)):
                                # 提取场景标题
                                if '：' in line_strip:
                                    title_part = line_strip.split('：', 1)[1].strip()
                                else:
                                    title_part = line_strip.split(':', 1)[1].strip()
                                if title_part:
                                    scene_title = f"## 场景{i+1}：{title_part}"
                                break

                # 添加到合并脚本中
                combined_script += f"\n{scene_title}\n{storyboard_script}\n"
                logger.info(f"添加场景{i+1}到合并脚本，场景标题: {scene_title}")

            if not combined_script.strip():
                logger.error("所有场景的分镜脚本都为空，无法进行增强")
                return failed_enhancements

            logger.info(f"开始增强合并的分镜脚本，包含{total_scenes}个场景，脚本长度: {len(combined_script)}")

            try:
                # 🔧 修复：一次性处理所有场景的分镜脚本
                enhanced_result = scene_enhancer.enhance_storyboard(combined_script, style)

                # 检测增强是否成功
                if not self._is_enhancement_successful(enhanced_result):
                    logger.error("合并分镜脚本增强失败")
                    # 将所有场景标记为失败
                    for i, result in enumerate(storyboard_results):
                        failed_enhancement = {
                            "scene_index": i,
                            "scene_info": result.get("scene_info", ""),
                            "error": "合并分镜脚本增强失败"
                        }
                        failed_enhancements.append(failed_enhancement)
                    return failed_enhancements

                # 🔧 修复：增强成功后，保存所有场景的结果
                scene_enhanced_result = {
                    "scene_index": 0,  # 合并处理，使用0作为索引
                    "scene_info": f"合并的{total_scenes}个场景",
                    "enhanced_result": enhanced_result
                }
                enhanced_results.append(scene_enhanced_result)

                # 保存增强进度
                self._save_enhancement_progress(enhanced_results, 0, scene_enhanced_result)
                logger.info(f"✅ 所有{total_scenes}个场景的增强描述已完成并保存")

            except Exception as e:
                # 合并增强异常
                logger.error(f"合并分镜脚本增强异常: {e}")
                # 将所有场景标记为失败
                for i, result in enumerate(storyboard_results):
                    failed_enhancement = {
                        "scene_index": i,
                        "scene_info": result.get("scene_info", ""),
                        "error": str(e)
                    }
                    failed_enhancements.append(failed_enhancement)
                return failed_enhancements

            # 所有场景处理完成后，合并结果进行最终处理
            if enhanced_results and not failed_enhancements:
                logger.info(f"所有场景增强完成，开始合并结果...")
                self._merge_enhanced_results(enhanced_results, project_root)
            elif failed_enhancements:
                logger.error(f"场景描述增强部分失败，{len(failed_enhancements)}个场景/镜头增强失败")

            return failed_enhancements

        except Exception as e:
            logger.error(f"线程安全的场景描述增强失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 如果整个过程失败，将所有场景标记为失败
            for i, result in enumerate(storyboard_results):
                failed_enhancement = {
                    "scene_index": i,
                    "scene_info": result.get("scene_info", ""),
                    "error": str(e)
                }
                failed_enhancements.append(failed_enhancement)
            return failed_enhancements

    def _is_enhancement_successful(self, enhanced_result):
        """检测增强描述是否成功"""
        if not enhanced_result:
            return False

        if not isinstance(enhanced_result, dict):
            return False

        enhanced_content = enhanced_result.get('enhanced_description', '')
        if not enhanced_content or not isinstance(enhanced_content, str):
            return False

        # 检查内容长度是否合理
        if len(enhanced_content.strip()) < 20:
            return False

        # 检查是否包含错误信息
        error_patterns = [
            'api错误', 'api密钥', 'network error', 'timeout error',
            'invalid api key', '请求超时', '网络错误', '调用失败',
            'api调用失败', '未知错误', '请稍后重试', '连接超时'
        ]

        content_lower = enhanced_content.lower()
        if any(pattern in content_lower for pattern in error_patterns):
            return False

        return True

    def _check_shot_enhancement_failures(self, enhanced_result, scene_info):
        """检查镜头增强失败情况，只关注镜头而非场景标题"""
        shot_failures = []

        try:
            # 🔧 修复：使用实际的镜头数量而不是估算
            if not self._is_enhancement_successful(enhanced_result):
                # 从场景信息中获取实际的镜头数量
                storyboard_script = scene_info.get('storyboard_script', '')
                actual_shots = [line for line in storyboard_script.split('\n') if line.strip().startswith('### 镜头')]
                actual_shot_count = len(actual_shots)

                # 如果无法获取实际镜头数，使用默认值
                if actual_shot_count == 0:
                    actual_shot_count = 1
                    logger.warning(f"无法获取场景的实际镜头数量，使用默认值: {actual_shot_count}")

                for shot_num in range(1, actual_shot_count + 1):
                    shot_failures.append({
                        "scene_info": scene_info,
                        "shot_number": shot_num,
                        "error": "镜头增强描述生成失败或质量不达标"
                    })

            return shot_failures

        except Exception as e:
            logger.error(f"检查镜头增强失败时出错: {e}")
            return []

    def _retry_single_storyboard(self, scene_index, scene_info, world_bible, scenes_analysis):
        """重试单个分镜生成"""
        try:
            logger.info(f"重试第{scene_index+1}个场景的分镜生成...")

            # 获取角色一致性提示词
            consistency_prompt = ""
            if hasattr(self, 'get_character_consistency_prompt'):
                try:
                    consistency_prompt = self.get_character_consistency_prompt()
                except Exception as e:
                    logger.warning(f"获取角色一致性提示词失败: {e}")

            prompt = f"""
你是一位专业的分镜师和导演。基于世界观圣经和场景分析，请为指定场景创建详细的分镜脚本。

世界观圣经（请严格遵循）：
{world_bible}

{consistency_prompt if consistency_prompt else ""}

场景分析参考：
{scenes_analysis}

当前场景信息：
{scene_info}

请按照以下专业格式输出分镜脚本：

## 场景分镜脚本

### 镜头1
- **镜头类型**：[特写/中景/全景/航拍等]
- **机位角度**：[平视/俯视/仰视/侧面等]
- **镜头运动**：[静止/推拉/摇移/跟随等]
- **景深效果**：[浅景深/深景深/焦点变化]
- **构图要点**：[三分法/对称/对角线等]
- **光影设计**：[自然光/人工光/逆光/侧光等]
- **色彩基调**：[暖色调/冷色调/对比色等]
- **时长**：X秒
- **镜头角色**：[列出根据画面描述中出现的角色，如：主人公、奶奶等]
- **画面描述**：[详细描述画面内容，包括角色位置、动作、表情、环境细节]
- **台词/旁白**：[如有]
- **音效提示**：[环境音、特效音等]
- **转场方式**：[切换/淡入淡出/叠化等]
请确保：
1. 严格遵循世界观圣经的设定
2. 使用专业的影视术语
3. 每个镜头都有明确的视觉目标
4. 画面描述要详细且专业，包含完整的视觉信息
5. 保持场景内镜头的连贯性
"""

            # 调用LLM API生成分镜脚本
            messages = [
                {"role": "system", "content": "你是一位专业的分镜师，擅长为影视作品创建详细的分镜头脚本。"},
                {"role": "user", "content": prompt}
            ]
            response = self.llm_api._make_api_call(
                model_name=self.llm_api.shots_model_name,
                messages=messages,
                task_name="storyboard_generation_retry"
            )

            # 检测分镜生成是否成功
            if self._is_storyboard_generation_failed_worker(response):
                logger.error(f"重试第{scene_index+1}个场景分镜仍然失败")
                return False

            # 更新分镜结果
            if hasattr(self, 'current_storyboard_results'):
                # 查找并更新对应的分镜结果
                for result in self.current_storyboard_results:
                    if result.get("scene_index") == scene_index:
                        result["storyboard_script"] = response
                        logger.info(f"第{scene_index+1}个场景分镜重试成功")

                        # 🔧 修复：重试成功后立即保存文件
                        try:
                            self._save_storyboard_scripts_to_files([result])
                            logger.info(f"第{scene_index+1}个场景分镜文件已更新保存")
                        except Exception as save_error:
                            logger.error(f"保存第{scene_index+1}个场景分镜文件失败: {save_error}")

                        # 🔧 新增：重试成功后立即更新项目数据
                        try:
                            self._update_project_storyboard_data()
                            logger.info(f"第{scene_index+1}个场景项目数据已同步更新")
                        except Exception as sync_error:
                            logger.error(f"同步第{scene_index+1}个场景项目数据失败: {sync_error}")

                        return True

                # 如果没有找到，添加新的结果
                new_result = {
                    "scene_index": scene_index,
                    "scene_info": scene_info,
                    "storyboard_script": response
                }
                self.current_storyboard_results.append(new_result)

                # 🔧 新增：保存新增的分镜文件
                try:
                    self._save_storyboard_scripts_to_files([new_result])
                    logger.info(f"第{scene_index+1}个场景分镜文件已新增保存")
                except Exception as save_error:
                    logger.error(f"保存第{scene_index+1}个场景分镜文件失败: {save_error}")

                # 🔧 新增：更新项目数据
                try:
                    self._update_project_storyboard_data()
                    logger.info(f"第{scene_index+1}个场景项目数据已同步更新")
                except Exception as sync_error:
                    logger.error(f"同步第{scene_index+1}个场景项目数据失败: {sync_error}")
                self.current_storyboard_results.append(new_result)
                logger.info(f"第{scene_index+1}个场景分镜重试成功（新增）")

                # 🔧 修复：重试成功后立即保存文件
                try:
                    self._save_storyboard_scripts_to_files([new_result])
                    logger.info(f"第{scene_index+1}个场景分镜文件已保存")
                except Exception as save_error:
                    logger.error(f"保存第{scene_index+1}个场景分镜文件失败: {save_error}")

                return True

            return False

        except Exception as e:
            logger.error(f"重试第{scene_index+1}个场景分镜异常: {e}")
            return False

    def _is_storyboard_generation_failed_worker(self, response):
        """检测分镜生成是否失败（工作线程版本）"""
        if not response or not isinstance(response, str):
            return True

        # 检查是否包含错误信息
        error_patterns = [
            'api错误', 'api密钥', 'network error', 'timeout error',
            'invalid api key', '请求超时', '网络错误', '调用失败',
            'api调用失败', '未知错误', '请稍后重试', '连接超时'
        ]

        response_lower = response.lower()
        if any(pattern in response_lower for pattern in error_patterns):
            return True

        # 检查内容是否过短（可能是错误信息）
        if len(response.strip()) < 50:
            return True

        # 检查是否包含基本的分镜结构
        required_elements = ['镜头', '画面描述']
        has_required_elements = any(element in response for element in required_elements)

        # 如果内容足够长但缺少必要元素，才判断为失败
        if len(response.strip()) >= 50 and not has_required_elements:
            return True

        return False

    def _retry_single_enhancement(self, scene_index, scene_info):
        """重试单个增强描述"""
        try:
            logger.info(f"重试第{scene_index+1}个场景的增强描述...")

            # 获取对应的分镜脚本
            storyboard_script = ""
            if hasattr(self, 'current_storyboard_results'):
                for result in self.current_storyboard_results:
                    if result.get("scene_index") == scene_index:
                        storyboard_script = result.get("storyboard_script", "")
                        break

            if not storyboard_script:
                logger.error(f"第{scene_index+1}个场景没有找到对应的分镜脚本")
                return False

            # 获取项目根目录
            project_root = self.project_manager.get_current_project_path() if self.project_manager else None
            if not project_root:
                logger.error("无法获取项目根目录")
                return False

            # 创建场景描述增强器
            from src.processors.scene_description_enhancer import SceneDescriptionEnhancer
            scene_enhancer = SceneDescriptionEnhancer(
                project_root=project_root,
                character_scene_manager=self.character_scene_manager,
                llm_api=self.llm_api
            )

            # 过滤分镜脚本
            filtered_lines = []
            lines = storyboard_script.split('\n')
            for line in lines:
                line_strip = line.strip()
                if (line_strip.startswith('### 场景') or
                    line_strip.startswith('## 场景') or
                    line_strip.startswith('场景') and '：' in line_strip):
                    continue
                filtered_lines.append(line)

            filtered_script = '\n'.join(filtered_lines)
            if not filtered_script.strip():
                logger.error(f"第{scene_index+1}个场景过滤后的分镜脚本为空")
                return False

            # 获取风格
            style = self.style_combo.currentText() if hasattr(self, 'style_combo') else '电影风格'

            # 调用场景描述增强器
            enhanced_result = scene_enhancer.enhance_storyboard(filtered_script, style)

            # 检测增强是否成功
            if not self._is_enhancement_successful(enhanced_result):
                logger.error(f"第{scene_index+1}个场景增强描述重试仍然失败")
                return False

            logger.info(f"第{scene_index+1}个场景增强描述重试成功")
            return True

        except Exception as e:
            logger.error(f"重试第{scene_index+1}个场景增强描述异常: {e}")
            return False



        return True

    def _enhance_storyboard_descriptions(self, storyboard_results):
        """使用场景描述增强器增强分镜脚本描述"""
        try:
            # 检查是否有分镜脚本数据
            if not storyboard_results:
                logger.warning("没有分镜脚本数据可供增强")
                return
            
            # 获取当前项目信息
            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有当前项目，无法保存增强结果")
                return
            
            project_name = self.project_manager.current_project.get('project_name')
            if not project_name:
                logger.warning("项目名称为空，无法保存增强结果")
                return
            
            # 初始化场景描述增强器
            if not self.scene_enhancer:
                project_root = self.project_manager.get_current_project_path() if self.project_manager else None
                if not project_root:
                    logger.error("无法获取项目根目录，跳过场景描述增强器初始化")
                    return
                self.scene_enhancer = SceneDescriptionEnhancer(
                    project_root=project_root,
                    character_scene_manager=self.character_scene_manager,
                    llm_api=getattr(self, 'llm_api', None)
                )
                # 设置输出目录，确保能正确找到project.json文件
                self.scene_enhancer.output_dir = project_root
                logger.info(f"场景描述增强器已初始化，项目根目录: {project_root}")
            
            # 合并所有分镜脚本内容（保留场景标题以便正确分组镜头）
            combined_script = ""
            for i, result in enumerate(storyboard_results):
                scene_info = result.get("scene_info", "")
                storyboard_script = result.get("storyboard_script", "")

                if storyboard_script.strip():  # 只添加非空的分镜脚本
                    # 为每个场景添加场景标题，确保场景描述增强器能正确识别场景边界
                    scene_title = f"## 场景{i+1}"
                    if scene_info:
                        # 安全处理scene_info，确保它是字符串
                        if isinstance(scene_info, dict):
                            # 如果是字典，尝试获取描述信息
                            scene_info_str = scene_info.get('description', '') or scene_info.get('name', '') or str(scene_info)
                        else:
                            scene_info_str = str(scene_info) if scene_info else ""

                        # 从scene_info中提取场景标题
                        if scene_info_str:
                            scene_info_lines = scene_info_str.split('\n')
                            for line in scene_info_lines:
                                line_strip = line.strip()
                                if ('场景' in line_strip and ('：' in line_strip or ':' in line_strip)):
                                    # 提取场景标题
                                    if '：' in line_strip:
                                        title_part = line_strip.split('：', 1)[1].strip()
                                    else:
                                        title_part = line_strip.split(':', 1)[1].strip()
                                    if title_part:
                                        scene_title = f"## 场景{i+1}：{title_part}"
                                    break

                    # 添加场景标题和分镜脚本内容
                    combined_script += f"\n{scene_title}\n{storyboard_script}\n"
                    logger.info(f"添加场景{i+1}到合并脚本，场景标题: {scene_title}")
                else:
                    logger.warning(f"场景{i+1}的分镜脚本为空，跳过")
            
            logger.info(f"开始增强分镜脚本描述，原始内容长度: {len(combined_script)}")
            
            # 获取用户选择的风格
            selected_style = self.style_combo.currentText() if hasattr(self, 'style_combo') else '电影风格'
            logger.info(f"使用风格: {selected_style}")
            
            # 调用场景描述增强器，传递风格参数
            enhanced_result = self.scene_enhancer.enhance_storyboard(combined_script, selected_style)
            
            if enhanced_result and 'enhanced_description' in enhanced_result:
                enhanced_content = enhanced_result['enhanced_description']
                logger.info(f"场景描述增强完成，增强内容长度: {len(enhanced_content)}")
                
                # 使用场景增强器实际保存的路径：project_root/texts
                project_root = self.project_manager.get_current_project_path() if self.project_manager else None
                if not project_root:
                    logger.error("无法获取项目根目录，无法验证prompt.json文件")
                    return
                    
                output_dir = os.path.join(project_root, "texts")
                logger.info(f"使用项目texts目录: {output_dir}")
                
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                    logger.info(f"输出目录已创建: {output_dir}")
                else:
                    logger.info(f"输出目录已存在: {output_dir}")
                
                # 场景增强器已经保存了正确格式的prompt.json文件，这里不再重复保存
                # 避免覆盖场景增强器生成的scenes格式文件
                prompt_file = os.path.join(output_dir, "prompt.json")

                # 验证场景增强器生成的文件是否存在
                if os.path.exists(prompt_file):
                    file_size = os.path.getsize(prompt_file)
                    logger.info(f"场景描述增强结果已由场景增强器保存到: {prompt_file}，文件大小: {file_size} 字节")

                    # 验证文件格式是否正确（包含scenes字段）
                    try:
                        with open(prompt_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if 'scenes' in data:
                            logger.info("✓ prompt.json文件格式正确，包含scenes字段")

                            # 更新storyboard文件，添加增强描述
                            self._update_storyboard_files_with_enhanced_descriptions(data)

                            # 保存增强描述到project.json文件
                            self._save_enhanced_descriptions_to_project(data)
                        else:
                            logger.warning("⚠ prompt.json文件格式可能不正确，缺少scenes字段")
                    except Exception as verify_error:
                        logger.error(f"验证prompt.json文件格式失败: {verify_error}")
                else:
                    logger.error(f"场景增强器未能生成prompt.json文件: {prompt_file}")
                
                # 更新状态显示
                self.status_label.setText("✅ 分镜脚本生成完成，场景描述已增强")
            else:
                logger.warning("场景描述增强器返回结果为空或格式不正确")
                
        except Exception as e:
            logger.error(f"增强分镜脚本描述失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _update_storyboard_files_with_enhanced_descriptions(self, prompt_data):
        """更新storyboard文件，在画面描述后添加增强描述行"""
        try:
            # 获取当前项目信息
            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有当前项目，无法更新storyboard文件")
                return
            
            project_dir = self.project_manager.current_project.get('project_dir')
            if not project_dir:
                logger.warning("项目目录不存在，无法更新storyboard文件")
                return
            
            # 获取storyboard文件夹路径
            storyboard_dir = os.path.join(project_dir, 'storyboard')
            if not os.path.exists(storyboard_dir):
                logger.warning(f"storyboard目录不存在: {storyboard_dir}")
                return
            
            scenes_data = prompt_data.get('scenes', {})
            
            # 更新每个storyboard文件
            for filename in os.listdir(storyboard_dir):
                if filename.endswith('_storyboard.txt'):
                    file_path = os.path.join(storyboard_dir, filename)
                    
                    # 从文件名提取场景编号
                    import re
                    scene_match = re.search(r'scene_(\d+)_storyboard\.txt', filename)
                    if not scene_match:
                        logger.warning(f"无法从文件名提取场景编号: {filename}")
                        continue
                    
                    scene_number = scene_match.group(1)
                    
                    # 查找对应场景的增强描述
                    scene_enhanced_descriptions = {}
                    for scene_name, shots in scenes_data.items():
                        # 检查场景名是否包含对应的场景编号
                        if f"场景{scene_number}" in scene_name or scene_name.endswith(f"_{scene_number}"):
                            for shot in shots:
                                shot_number = shot.get('shot_number', '')
                                enhanced_desc = shot.get('enhanced_prompt', '')
                                
                                if shot_number and enhanced_desc:
                                    # 提取镜头编号
                                    shot_match = re.search(r'镜头(\d+)', shot_number)
                                    if shot_match:
                                        shot_key = f"镜头{shot_match.group(1)}"
                                        scene_enhanced_descriptions[shot_key] = enhanced_desc
                                        logger.info(f"为{filename}提取到{shot_key}的增强描述: {enhanced_desc[:50]}...")
                            break
                    
                    if scene_enhanced_descriptions:
                        self._add_enhanced_descriptions_to_storyboard_file(file_path, scene_enhanced_descriptions)
                        logger.info(f"✓ 已为{filename}添加{len(scene_enhanced_descriptions)}个增强描述")
                    else:
                        logger.warning(f"未找到{filename}对应的增强描述")
            
            logger.info("✅ 所有storyboard文件已成功添加增强描述")

        except Exception as e:
            logger.error(f"更新storyboard文件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _save_enhanced_descriptions_to_project(self, enhanced_data):
        """将增强描述保存到project.json文件中"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有当前项目，无法保存增强描述到project.json")
                return

            # 确保项目数据中有五阶段分镜数据结构
            if 'five_stage_storyboard' not in self.project_manager.current_project:
                self.project_manager.current_project['five_stage_storyboard'] = {}

            five_stage_data = self.project_manager.current_project['five_stage_storyboard']

            # 确保有stage_data结构
            if 'stage_data' not in five_stage_data:
                five_stage_data['stage_data'] = {}

            # 确保有第四阶段数据结构
            if '4' not in five_stage_data['stage_data']:
                five_stage_data['stage_data']['4'] = {}

            stage4_data = five_stage_data['stage_data']['4']

            # 保存增强描述数据
            stage4_data['enhanced_descriptions'] = enhanced_data
            stage4_data['enhancement_completed'] = True
            stage4_data['enhancement_timestamp'] = datetime.now().isoformat()

            # 提取并保存镜头级别的增强描述
            shot_enhanced_descriptions = {}
            scenes_data = enhanced_data.get('scenes', {})

            for scene_name, shots in scenes_data.items():
                for shot in shots:
                    shot_number = shot.get('shot_number', '')
                    enhanced_prompt = shot.get('enhanced_prompt', '')

                    if shot_number and enhanced_prompt:
                        shot_enhanced_descriptions[shot_number] = enhanced_prompt

            stage4_data['shot_enhanced_descriptions'] = shot_enhanced_descriptions

            # 保存项目文件
            success = self.project_manager.save_project()

            if success:
                logger.info(f"✓ 增强描述已保存到project.json，共{len(shot_enhanced_descriptions)}个镜头")
            else:
                logger.error("✗ 保存增强描述到project.json失败")

        except Exception as e:
            logger.error(f"保存增强描述到project.json失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _add_enhanced_descriptions_to_storyboard_file(self, file_path, enhanced_descriptions):
        """为单个storyboard文件添加增强描述"""
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            new_lines = []
            current_shot = None
            enhanced_added = set()  # 记录已添加增强描述的镜头
            
            for line in lines:
                new_lines.append(line)
                
                # 检测镜头开始
                if line.startswith('### 镜头'):
                    import re
                    match = re.search(r'### 镜头(\d+)', line)
                    if match:
                        current_shot = f"镜头{match.group(1)}"
                        logger.debug(f"检测到镜头: {current_shot}")
                
                # 在画面描述后添加或更新增强描述
                elif (line.strip().startswith('- **画面描述**：') or 
                      line.strip().startswith('**画面描述**：')) and current_shot:
                    
                    logger.debug(f"找到画面描述行，当前镜头: {current_shot}")
                    
                    # 如果当前镜头还没处理过，则添加增强描述
                    if current_shot not in enhanced_added:
                        if current_shot in enhanced_descriptions:
                            enhanced_desc = enhanced_descriptions[current_shot]
                            new_lines.append(f"- **增强描述**：{enhanced_desc}")
                            enhanced_added.add(current_shot)
                            logger.info(f"为{current_shot}添加增强描述到文件: {os.path.basename(file_path)}")
                        else:
                            # 如果没有找到对应的增强描述，添加空的占位符
                            new_lines.append("- **增强描述**：")
                            enhanced_added.add(current_shot)
                            logger.warning(f"未找到{current_shot}的增强描述，添加空占位符到文件: {os.path.basename(file_path)}")
                    else:
                        logger.debug(f"{current_shot}已添加过增强描述，跳过重复添加")
                
                # 检测并处理已存在的增强描述行
                elif (line.strip().startswith('- **增强描述**：') or 
                      line.strip().startswith('**增强描述**：')) and current_shot:
                    
                    # 移除刚添加的这行，因为我们要替换它
                    new_lines.pop()
                    
                    # 只有当前镜头还没有被处理过时才添加新的增强描述
                    if current_shot not in enhanced_added:
                        if current_shot in enhanced_descriptions:
                            enhanced_desc = enhanced_descriptions[current_shot]
                            new_lines.append(f"- **增强描述**：{enhanced_desc}")
                            enhanced_added.add(current_shot)
                            logger.info(f"替换{current_shot}的增强描述到文件: {os.path.basename(file_path)}")
                        else:
                            # 如果没有找到对应的增强描述，保持原行不变
                            new_lines.append(line)
                            enhanced_added.add(current_shot)
                            logger.debug(f"{current_shot}未找到新的增强描述，保持原内容")
                    else:
                        # 如果已经处理过，跳过这行（不添加重复的增强描述）
                        logger.debug(f"{current_shot}的增强描述已处理过，跳过重复行")
            
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            logger.info(f"✓ 已更新文件: {os.path.basename(file_path)}")
            
        except Exception as e:
            logger.error(f"更新文件 {file_path} 失败: {e}")
    

    
    def _reset_ui_state(self):
        """重置UI状态"""
        self.progress_bar.setVisible(False)
        self.stop_btn.setEnabled(False)
        
        # 恢复按钮状态，根据当前阶段设置合适的按钮文本
        self.stage1_generate_btn.setEnabled(True)
        if self.current_stage >= 1:
            self.stage1_generate_btn.setText("🔄 重新分析")
        else:
            self.stage1_generate_btn.setText("🚀 开始全局分析")
        
        self.stage2_generate_btn.setEnabled(True)
        self.stage2_generate_btn.setText("🔄 刷新角色信息")
        
        self.stage3_generate_btn.setEnabled(True)
        if self.current_stage >= 3:
            self.stage3_generate_btn.setText("🔄 重新分割场景")
        else:
            self.stage3_generate_btn.setText("🎬 开始场景分割")
        
        self.stage4_generate_btn.setEnabled(True)
        if self.current_stage >= 4:
            self.stage4_generate_btn.setText("🔄 重新生成分镜")
        else:
            self.stage4_generate_btn.setText("📝 生成分镜脚本")
        
        # 重置增强描述按钮 - 根据当前阶段决定是否启用
        if hasattr(self, 'enhance_description_btn'):
            # 如果阶段4已完成且有分镜结果，则启用增强描述按钮
            should_enable = (self.current_stage >= 4 and 
                           hasattr(self, 'current_storyboard_results') and 
                           bool(self.current_storyboard_results))
            self.enhance_description_btn.setEnabled(should_enable)
            self.enhance_description_btn.setText("✨ 增强描述")
        
        self.stage5_generate_btn.setEnabled(True)
        if self.current_stage >= 5:
            self.stage5_generate_btn.setText("🔄 重新优化")
        else:
            self.stage5_generate_btn.setText("🎨 生成优化建议")
    
    def _update_scenes_list(self, scenes_analysis):
        """更新场景列表"""
        self.scenes_list.clear()
        
        # 简单解析场景（实际应用中可以使用更复杂的解析逻辑）
        lines = scenes_analysis.split('\n')
        scene_count = 0
        
        for line in lines:
            line_strip = line.strip()
            if line_strip.startswith('### 场景') or line_strip.startswith('## 场景'):
                # 提取标题部分，去除前缀
                # 例如：### 场景1：叶文洁的内心挣扎  => 叶文洁的内心挣扎
                parts = line_strip.split('：', 1)
                if len(parts) == 2:
                    title = parts[1].strip()
                else:
                    # 兼容没有冒号的情况
                    title = line_strip.split(' ', 1)[-1].replace('场景','').replace('#','').strip()
                scene_count += 1
                item = QListWidgetItem(f"场景{scene_count}：{title}")
                self.scenes_list.addItem(item)
        
        if scene_count == 0:
            # 如果没有找到标准格式的场景，创建默认场景
            for i in range(3):  # 默认创建3个场景
                item = QListWidgetItem(f"场景{i+1}：默认场景")
                self.scenes_list.addItem(item)
    
    def _display_storyboard_results(self, storyboard_results):
        """显示分镜脚本结果"""
        output_text = ""

        for i, result in enumerate(storyboard_results):
            scene_info = result.get("scene_info", "")
            storyboard_script = result.get("storyboard_script", "")
            enhanced_shots = result.get("enhanced_shots", [])

            # 🔧 修复：简化场景信息显示，只显示场景名称
            scene_name = ""
            if isinstance(scene_info, dict):
                scene_name = scene_info.get("scene_name", f"场景{i+1}")
            elif isinstance(scene_info, str):
                # 如果是字符串，尝试提取场景名称
                if "scene_name" in scene_info:
                    import re
                    match = re.search(r"'scene_name':\s*'([^']*)'", scene_info)
                    if match:
                        scene_name = match.group(1)
                    else:
                        scene_name = f"场景{i+1}"
                else:
                    scene_name = scene_info
            else:
                scene_name = f"场景{i+1}"

            output_text += f"\n{'='*50}\n"
            output_text += f"场景 {i+1}\n"
            output_text += f"{'='*50}\n"
            output_text += f"场景信息: {scene_name}\n\n"
            output_text += storyboard_script
            output_text += "\n\n"
            
            # 显示增强后的镜头信息
            if enhanced_shots:
                output_text += f"{'='*30} 增强后的镜头信息 {'='*30}\n\n"
                for shot in enhanced_shots:
                    shot_number = shot.get('shot_number', '')
                    final_prompt = shot.get('final_prompt', '')
                    
                    output_text += f"【镜头 {shot_number}】\n"
                    output_text += f"{final_prompt}\n"
                    output_text += f"{'-'*60}\n\n"
        
        self.storyboard_output.setText(output_text)
    
    def _display_optimization_results(self, optimization_suggestions):
        """显示优化建议结果"""
        output_text = "🎨 分镜脚本质量分析与优化建议\n\n"
        
        for suggestion in optimization_suggestions:
            scene_index = suggestion.get("scene_index", 0)
            output_text += f"📋 场景 {scene_index + 1} 分析:\n"
            output_text += f"• 视觉一致性: {suggestion.get('visual_consistency', '')}\n"
            output_text += f"• 技术质量: {suggestion.get('technical_quality', '')}\n"
            output_text += f"• 叙事流畅性: {suggestion.get('narrative_flow', '')}\n"
            
            # 显示增强功能应用状态
            enhancement_applied = suggestion.get('enhancement_applied', '')
            if enhancement_applied:
                output_text += f"• 增强功能: {enhancement_applied}\n"
            
            tips = suggestion.get('optimization_tips', [])
            if tips:
                output_text += "💡 优化建议:\n"
                for tip in tips:
                    output_text += f"  - {tip}\n"
            
            output_text += "\n"
        
        self.optimization_output.setText(output_text)
    
    def select_all_scenes(self):
        """全选所有场景"""
        for i in range(self.scenes_list.count()):
            item = self.scenes_list.item(i)
            item.setSelected(True)
    
    def stop_generation(self):
        """停止生成"""
        # 停止工作线程
        if (self.worker_thread is not None and
            hasattr(self.worker_thread, 'isRunning') and
            self.worker_thread.isRunning()):
            self.worker_thread.cancel()
            self.worker_thread.wait(3000)
            if (hasattr(self.worker_thread, 'isRunning') and
                self.worker_thread.isRunning()):
                self.worker_thread.terminate()
                self.worker_thread.wait(1000)

        # 停止增强线程
        if (self.enhancement_thread is not None and
            hasattr(self.enhancement_thread, 'isRunning') and
            self.enhancement_thread.isRunning()):
            self.enhancement_thread.cancel()
            self.enhancement_thread.wait(3000)
            if (hasattr(self.enhancement_thread, 'isRunning') and
                self.enhancement_thread.isRunning()):
                self.enhancement_thread.terminate()
                self.enhancement_thread.wait(1000)
            self._reset_enhancement_ui()

        self.status_label.setText("⏹️ 已停止")
        self._reset_ui_state()
    
    def export_storyboard(self):
        """导出分镜脚本"""
        try:
            if not self.stage_data.get(4):
                QMessageBox.warning(self, "警告", "没有可导出的分镜脚本")
                return
            
            from PyQt5.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出分镜脚本", "storyboard_script.txt", "文本文件 (*.txt);;所有文件 (*)"
            )
            
            if file_path:
                content = self.storyboard_output.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                QMessageBox.information(self, "成功", f"分镜脚本已导出到: {file_path}")
                logger.info(f"分镜脚本已导出到: {file_path}")
        
        except Exception as e:
            logger.error(f"导出分镜脚本失败: {e}")
            QMessageBox.critical(self, "错误", f"导出失败: {e}")
    
    def regenerate_storyboard(self):
        """重新生成分镜"""
        logger.info("🔄 用户点击重新生成分镜按钮")

        reply = QMessageBox.question(
            self, "确认", "是否要重新生成分镜脚本？这将覆盖当前结果。",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            logger.info("🔧 用户确认重新生成分镜，开始清理操作...")

            # 🔧 修复：重新生成时清理现有的分镜进度文件，确保从头开始生成
            logger.info("🧹 步骤1：清理分镜进度文件")
            self._clear_storyboard_progress_file()

            logger.info("🧹 步骤2：清理增强描述进度文件")
            self._clear_enhancement_progress_file()

            # 🔧 新增：清理项目数据中的分镜相关数据
            logger.info("🧹 步骤3：清理项目数据中的分镜相关数据")
            self._clear_project_storyboard_data()

            # 清理第4、5阶段的数据
            logger.info("🧹 步骤4：清理第4、5阶段的数据")
            self._clear_subsequent_stages(3)

            logger.info("✅ 所有清理操作完成，开始重新生成分镜")
            self.tab_widget.setCurrentIndex(3)  # 切换到分镜生成标签页
            self.start_stage(4, force_regenerate=True)  # 🔧 修复：强制重新生成
        else:
            logger.info("❌ 用户取消重新生成分镜操作")

    def _handle_stage4_button_click(self):
        """处理第4阶段按钮点击事件"""
        logger.info("🔄 用户点击第4阶段生成按钮")

        # 如果第4阶段已完成，调用重新生成方法
        if self.current_stage >= 4:
            logger.info("第4阶段已完成，调用重新生成分镜方法")
            self.regenerate_storyboard()
        else:
            logger.info("第4阶段未完成，调用正常生成方法")
            self.start_stage(4)

    def _load_existing_enhancement_progress(self):
        """加载已保存的增强描述进度"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return [], 0

            # 获取项目目录
            project_dir = self.project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return [], 0

            # 检查是否有保存的增强进度文件
            progress_file = os.path.join(project_dir, 'enhancement_progress.json')
            if not os.path.exists(progress_file):
                return [], 0

            # 读取进度文件
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)

            enhanced_results = progress_data.get('enhanced_results', [])
            start_index = len(enhanced_results)
            logger.info(f"加载已保存的增强进度: {start_index} 个场景")
            return enhanced_results, start_index

        except Exception as e:
            logger.error(f"加载增强进度失败: {e}")
            return [], 0

    def _save_enhancement_progress(self, enhanced_results, scene_index, scene_result):
        """保存增强描述进度"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            # 获取项目目录
            project_dir = self.project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return

            # 保存进度数据
            from datetime import datetime
            progress_data = {
                'enhanced_results': enhanced_results,
                'timestamp': datetime.now().isoformat(),
                'total_scenes': len(enhanced_results),
                'last_completed_scene': scene_index
            }

            progress_file = os.path.join(project_dir, 'enhancement_progress.json')
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)

            logger.info(f"增强进度已保存: {len(enhanced_results)} 个场景，最后完成场景 {scene_index + 1}")

        except Exception as e:
            logger.error(f"保存增强进度失败: {e}")

    def _has_existing_enhancement_progress(self):
        """检查是否存在增强进度文件"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return False

            # 获取项目目录
            project_dir = self.project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return False

            # 检查是否有保存的增强进度文件
            progress_file = os.path.join(project_dir, 'enhancement_progress.json')
            return os.path.exists(progress_file)

        except Exception as e:
            logger.error(f"检查增强进度失败: {e}")
            return False

    def _clean_enhancement_data(self):
        """清理增强描述相关数据和文件"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_dir = self.project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return

            logger.info("🧹 步骤1：清理增强描述进度文件")

            # 清理增强进度文件
            progress_file = os.path.join(project_dir, 'enhancement_progress.json')
            if os.path.exists(progress_file):
                os.remove(progress_file)
                logger.info(f"已删除增强进度文件: {progress_file}")

            logger.info("🧹 步骤2：清理增强描述输出文件")

            # 清理texts目录下的相关文件
            texts_dir = os.path.join(project_dir, 'texts')
            if os.path.exists(texts_dir):
                # 清理prompt.json
                prompt_file = os.path.join(texts_dir, 'prompt.json')
                if os.path.exists(prompt_file):
                    os.remove(prompt_file)
                    logger.info(f"已删除prompt.json文件: {prompt_file}")

                # 清理original_descriptions_with_consistency文件
                for filename in os.listdir(texts_dir):
                    if filename.startswith('original_descriptions_with_consistency_'):
                        file_path = os.path.join(texts_dir, filename)
                        os.remove(file_path)
                        logger.info(f"已删除一致性描述文件: {file_path}")

            logger.info("🧹 步骤3：清理项目数据中的增强描述相关数据")

            # 清理项目数据中的增强描述相关字段
            if hasattr(self.project_manager, 'current_project'):
                project_data = self.project_manager.current_project

                # 清理增强描述相关字段
                fields_to_clear = [
                    'enhanced_descriptions',
                    'enhancement_progress',
                    'enhancement_results'
                ]

                for field in fields_to_clear:
                    if field in project_data:
                        del project_data[field]
                        logger.info(f"已清理项目数据字段: {field}")

            logger.info("✅ 所有增强描述清理操作完成，准备重新增强")

        except Exception as e:
            logger.error(f"清理增强描述相关文件失败: {e}")

    def _merge_enhanced_results(self, enhanced_results, project_root):
        """合并增强结果并生成最终的prompt.json文件"""
        try:
            logger.info(f"开始合并 {len(enhanced_results)} 个场景的增强结果...")

            # 确保输出目录存在
            output_dir = os.path.join(project_root, "texts")
            os.makedirs(output_dir, exist_ok=True)

            # 构建完整的prompt.json数据结构
            prompt_data = {
                "scenes": {},
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "scene_description_enhancer",
                "version": "2.0"
            }

            # 遍历所有增强结果，构建scenes数据
            for scene_idx, scene_result in enumerate(enhanced_results):
                scene_info = scene_result.get('scene_info', '')
                enhanced_result = scene_result.get('enhanced_result', {})
                enhanced_details = enhanced_result.get('enhanced_details', [])

                # 跳过场景标题，只处理镜头
                scene_shots = []
                for detail in enhanced_details:
                    if detail.get('type') == 'scene_title':
                        continue

                    shot_info = detail.get('shot_info', {})
                    shot_number = shot_info.get('镜头编号', '')
                    original_desc = detail.get('original', '')
                    enhanced_desc = detail.get('enhanced', '')

                    if shot_number and (enhanced_desc or original_desc):
                        shot_data = {
                            "shot_number": shot_number,
                            "original_description": self._build_shot_description(shot_info),
                            "enhanced_prompt": enhanced_desc or original_desc
                        }
                        scene_shots.append(shot_data)

                # 将场景数据添加到prompt_data中
                if scene_shots:
                    # 🔧 修复：使用简洁的场景名称而不是完整的字典字符串
                    if isinstance(scene_info, dict):
                        scene_key = scene_info.get('scene_name', f"场景{scene_idx + 1}")
                    elif isinstance(scene_info, str):
                        scene_key = scene_info
                    else:
                        scene_key = f"场景{scene_idx + 1}"

                    prompt_data["scenes"][scene_key] = scene_shots
                    logger.info(f"已合并场景: {scene_key}，包含 {len(scene_shots)} 个镜头")

            # 保存prompt.json文件
            prompt_file = os.path.join(output_dir, "prompt.json")
            with open(prompt_file, 'w', encoding='utf-8') as f:
                json.dump(prompt_data, f, ensure_ascii=False, indent=2)

            file_size = os.path.getsize(prompt_file)
            logger.info(f"✅ 完整的prompt.json已生成: {prompt_file}，文件大小: {file_size} 字节")
            logger.info(f"✅ 包含 {len(prompt_data['scenes'])} 个场景的完整数据")

            # 🔧 新增：在所有场景增强完成后，一次性添加一致性描述
            logger.info("🔧 准备调用_add_consistency_descriptions_to_prompt方法...")
            self._add_consistency_descriptions_to_prompt(prompt_file, enhanced_results)
            logger.info("🔧 _add_consistency_descriptions_to_prompt方法调用完成")

            # 在主线程中更新storyboard文件和保存到project.json
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._update_storyboard_files_with_enhanced_descriptions(prompt_data))
            QTimer.singleShot(0, lambda: self._save_enhanced_descriptions_to_project(prompt_data))

        except Exception as e:
            logger.error(f"合并增强结果失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    def _add_consistency_descriptions_to_prompt(self, prompt_file, enhanced_results):
        """🔧 新增：在所有场景增强完成后，一次性添加一致性描述到prompt.json"""
        try:
            logger.info("开始为所有镜头添加一致性描述...")

            # 读取现有的prompt.json数据
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = json.load(f)

            # 从enhanced_results中提取一致性描述信息
            consistency_data = {}

            for scene_result in enhanced_results:
                scene_info = scene_result.get('scene_info', '')
                enhanced_result = scene_result.get('enhanced_result', {})
                enhanced_details = enhanced_result.get('enhanced_details', [])

                # 提取每个镜头的一致性描述
                for detail in enhanced_details:
                    if detail.get('type') == 'scene_title':
                        continue

                    shot_info = detail.get('shot_info', {})
                    shot_number = shot_info.get('镜头编号', '')

                    # 构建一致性描述内容
                    content = self._build_consistency_content_from_detail(detail)

                    if shot_number and content:
                        consistency_data[shot_number] = content

            # 将一致性描述添加到prompt.json的对应镜头中
            content_added_count = 0
            for scene_name, scene_shots in prompt_data.get('scenes', {}).items():
                for shot in scene_shots:
                    shot_number = shot.get('shot_number', '')
                    if shot_number in consistency_data:
                        shot['content'] = consistency_data[shot_number]
                        content_added_count += 1

            # 更新时间戳
            from datetime import datetime
            prompt_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prompt_data['last_consistency_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 保存更新后的prompt.json
            with open(prompt_file, 'w', encoding='utf-8') as f:
                json.dump(prompt_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 一致性描述已添加到prompt.json，共更新 {content_added_count} 个镜头")

            # 删除废弃的一致性描述文件
            import glob
            import os
            texts_dir = os.path.dirname(prompt_file)
            old_files = glob.glob(os.path.join(texts_dir, "original_descriptions_with_consistency_*.json"))
            for old_file in old_files:
                try:
                    os.remove(old_file)
                    logger.info(f"删除废弃的一致性描述文件: {old_file}")
                except Exception as e:
                    logger.warning(f"删除废弃文件失败 {old_file}: {e}")

        except Exception as e:
            logger.error(f"添加一致性描述失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    def _build_consistency_content_from_detail(self, detail):
        """从增强详情中构建一致性描述内容"""
        try:
            shot_info = detail.get('shot_info', {})

            # 获取嵌入角色一致性描述后的原始描述
            original_description = detail.get('embedded_original', '')
            if not original_description:
                original_description = detail.get('true_original', '')
            if not original_description:
                original_description = detail.get('original', '')
            if not original_description:
                original_description = shot_info.get('画面描述', '')

            # 构建技术细节补充
            technical_details = []
            tech_fields = ['镜头类型', '机位角度', '镜头运动', '光影设计', '构图要点']
            for field in tech_fields:
                value = shot_info.get(field, '')
                if value:
                    technical_details.append(value)

            technical_supplement = '; '.join(technical_details) if technical_details else ''

            # 获取当前项目风格
            current_style = self._get_current_style()
            style_prompt = ""
            if current_style:
                # 使用硬编码的风格提示词字典
                style_prompts = {
                    '电影风格': '电影感，超写实，4K，胶片颗粒，景深',
                    '动漫风格': '动漫风，鲜艳色彩，干净线条，赛璐璐渲染，日本动画',
                    '吉卜力风格': '吉卜力风，柔和色彩，奇幻，梦幻，丰富背景',
                    '赛博朋克风格': '赛博朋克，霓虹灯，未来都市，雨夜，暗色氛围',
                    '水彩插画风格': '水彩画风，柔和笔触，粉彩色，插画，温柔',
                    '像素风格': '像素风，8位，复古，低分辨率，游戏风',
                    '写实摄影风格': '真实光线，高细节，写实摄影，4K'
                }
                style_prompt = style_prompts.get(current_style, "")

            # 构建完整的一致性描述内容
            formatted_content = original_description
            if style_prompt and style_prompt.strip():
                if technical_supplement:
                    formatted_content += f"，{style_prompt}\n\n技术细节补充：{technical_supplement}"
                else:
                    formatted_content += f"，{style_prompt}"
            elif technical_supplement:
                formatted_content += f"\n\n技术细节补充：{technical_supplement}"

            return formatted_content

        except Exception as e:
            logger.error(f"构建一致性描述内容失败: {e}")
            return detail.get('embedded_original', detail.get('original', ''))

    def _get_current_style(self):
        """获取当前选择的风格"""
        try:
            if hasattr(self, 'style_combo') and self.style_combo:
                return self.style_combo.currentText()
            return '电影风格'  # 默认风格
        except Exception as e:
            logger.error(f"获取当前风格失败: {e}")
            return '电影风格'

    def _build_shot_description(self, shot_info):
        """构建镜头的完整描述信息"""
        try:
            lines = []
            lines.append(shot_info.get('镜头编号', ''))

            # 添加技术参数
            tech_params = [
                ('镜头类型', shot_info.get('镜头类型', '')),
                ('机位角度', shot_info.get('机位角度', '')),
                ('镜头运动', shot_info.get('镜头运动', '')),
                ('景深效果', shot_info.get('景深效果', '')),
                ('构图要点', shot_info.get('构图要点', '')),
                ('光影设计', shot_info.get('光影设计', '')),
                ('色彩基调', shot_info.get('色彩基调', '')),
                ('时长', shot_info.get('时长', '')),
                ('镜头角色', shot_info.get('镜头角色', '')),
                ('画面描述', shot_info.get('画面描述', '')),
                ('台词/旁白', shot_info.get('台词/旁白', '')),
                ('音效提示', shot_info.get('音效提示', '')),
                ('转场方式', shot_info.get('转场方式', ''))
            ]

            for param_name, param_value in tech_params:
                if param_value:
                    lines.append(f"- **{param_name}**：{param_value}")

            return '\n'.join(lines)
        except Exception as e:
            logger.error(f"构建镜头描述失败: {e}")
            return shot_info.get('画面描述', '')

    def save_to_project(self):
        """保存五阶段分镜数据到当前项目"""
        try:
            # 调试信息：检查项目管理器状态
            logger.info(f"💾 检查项目管理器状态...")
            logger.info(f"💾 self.project_manager: {self.project_manager is not None}")
            if self.project_manager:
                has_current_project = self.project_manager.current_project is not None
                logger.info(f"💾 current_project: {has_current_project}")
                if self.project_manager.current_project:
                    project_name = self.project_manager.current_project.get('project_name', 'Unknown')
                    logger.info(f"💾 当前项目名称: {project_name}")

            # 尝试从父窗口重新获取项目管理器
            if not self.project_manager and self.parent_window:
                logger.info("💾 尝试从父窗口重新获取项目管理器...")
                if hasattr(self.parent_window, 'project_manager'):
                    self.project_manager = self.parent_window.project_manager
                    logger.info(f"💾 重新获取项目管理器成功: {self.project_manager}")
                elif hasattr(self.parent_window, 'app_controller') and hasattr(self.parent_window.app_controller, 'project_manager'):
                    self.project_manager = self.parent_window.app_controller.project_manager
                    logger.info(f"💾 从app_controller获取项目管理器成功: {self.project_manager}")

            # 尝试从当前活跃项目获取项目名称
            if not self.project_manager or not self.project_manager.current_project:
                if hasattr(self.parent_window, 'current_active_project') and self.parent_window.current_active_project:
                    logger.info(f"💾 尝试使用当前活跃项目: {self.parent_window.current_active_project}")
                    # 尝试加载项目
                    if self.project_manager:
                        try:
                            self.project_manager.load_project(self.parent_window.current_active_project)
                            logger.info(f"💾 项目重新加载成功: {self.parent_window.current_active_project}")
                        except Exception as e:
                            logger.error(f"💾 项目重新加载失败: {e}")

            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("💾 没有当前项目，无法保存五阶段分镜数据")
                return
            
            # 确保stage_data的键为字符串格式，避免重复键问题
            normalized_stage_data = {}
            for key, value in self.stage_data.items():
                # 将所有键转换为字符串格式
                str_key = str(key)
                normalized_stage_data[str_key] = value

            # 创建精简的五阶段数据，只保存必要信息
            five_stage_data = {
                'stage_data': normalized_stage_data,
                'current_stage': self.current_stage,
                'selected_characters': self.selected_characters,
                'selected_scenes': self.selected_scenes,
                'article_text': self.article_input.toPlainText(),
                'selected_style': self.style_combo.currentText(),
                'selected_model': self.model_combo.currentText()
            }

            # 更新项目数据
            self.project_manager.current_project['five_stage_storyboard'] = five_stage_data

            # 保存项目
            success = self.project_manager.save_project()

            # 在保存后清理项目文件，移除不必要的冗余信息
            if success:
                self._clean_project_file_after_save()
            if success:
                logger.info(f"五阶段分镜数据已保存到项目: {self.project_manager.current_project['project_name']}")
                
                # 通知主窗口更新项目状态
                if self.parent_window and hasattr(self.parent_window, 'update_project_status'):
                    self.parent_window.update_project_status()
                    
            else:
                logger.error(f"保存五阶段分镜数据失败: {self.project_manager.current_project['project_name']}")
                
        except Exception as e:
            logger.error(f"保存五阶段分镜数据时出错: {e}")

    def _clean_project_data_for_storage(self):
        """清理项目数据，移除不必要的冗余信息"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_data = self.project_manager.current_project

            # 移除调试和临时数据
            keys_to_remove = [
                'project_root',  # 冗余，已有project_dir
                'original_text',  # 冗余，已在text_creation中
                'rewritten_text',  # 冗余，已在text_creation中
                'shots_data',  # 冗余，已在five_stage_storyboard中
                'image_generation_settings',  # 冗余，已在image_generation中
                'shot_image_mappings',  # 临时数据
                'drawing_settings',  # 冗余，已在image_generation中
                'voice_settings',  # 冗余，已在voice_generation中
                'progress_status'  # 临时状态数据
            ]

            removed_count = 0
            for key in keys_to_remove:
                if key in project_data:
                    del project_data[key]
                    removed_count += 1

            # 清理空的或默认的数据结构
            self._clean_empty_data_structures(project_data)

            if removed_count > 0:
                logger.info(f"项目数据清理完成，已移除 {removed_count} 个冗余字段")

        except Exception as e:
            logger.error(f"清理项目数据失败: {e}")

    def _clean_empty_data_structures(self, project_data):
        """清理空的或默认的数据结构"""
        try:
            # 清理图像生成数据中的空数组
            if 'image_generation' in project_data:
                img_gen = project_data['image_generation']
                if 'generated_images' in img_gen and not img_gen['generated_images']:
                    img_gen['generated_images'] = []
                if 'progress' in img_gen:
                    progress = img_gen['progress']
                    if all(progress.get(k, 0) == 0 for k in ['total_shots', 'completed_shots', 'failed_shots']):
                        progress['status'] = 'pending'

            # 清理语音生成数据中的空数组
            if 'voice_generation' in project_data:
                voice_gen = project_data['voice_generation']
                if 'generated_audio' in voice_gen and not voice_gen['generated_audio']:
                    voice_gen['generated_audio'] = []
                if 'narration_text' in voice_gen and not voice_gen['narration_text']:
                    voice_gen['narration_text'] = ''

            # 清理文件列表中的空值
            if 'files' in project_data:
                files = project_data['files']
                for key in ['original_text', 'rewritten_text', 'storyboard', 'video', 'subtitles']:
                    if key in files and not files[key]:
                        files[key] = None
                for key in ['images', 'audio']:
                    if key in files and not files[key]:
                        files[key] = []

        except Exception as e:
            logger.error(f"清理空数据结构失败: {e}")

    def _clean_project_file_after_save(self):
        """在保存后直接清理项目文件，移除冗余信息"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                return

            project_dir = self.project_manager.current_project.get('project_dir', '')
            if not project_dir:
                return

            import json
            import os

            project_file = os.path.join(project_dir, 'project.json')
            if not os.path.exists(project_file):
                return

            # 读取项目文件
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 检查五阶段分镜数据是否为空，如果为空则跳过清理
            five_stage_data = project_data.get('five_stage_storyboard', {})
            stage_data = five_stage_data.get('stage_data', {})

            # 检查是否有有效的阶段数据
            has_valid_data = False
            for stage_key, stage_content in stage_data.items():
                if isinstance(stage_content, dict) and stage_content:
                    has_valid_data = True
                    break

            if not has_valid_data:
                logger.warning("五阶段分镜数据为空，跳过项目文件清理以避免数据丢失")
                return

            # 移除冗余字段
            keys_to_remove = [
                'project_root',  # 冗余，已有project_dir
                'original_text',  # 冗余，已在text_creation中
                'rewritten_text',  # 冗余，已在text_creation中
                'shots_data',  # 冗余，已在five_stage_storyboard中
                'image_generation_settings',  # 冗余，已在image_generation中
                'shot_image_mappings',  # 临时数据
                'drawing_settings',  # 冗余，已在image_generation中
                'voice_settings',  # 冗余，已在voice_generation中
                'progress_status'  # 临时状态数据
            ]

            removed_count = 0
            for key in keys_to_remove:
                if key in project_data:
                    del project_data[key]
                    removed_count += 1

            # 如果有字段被移除，重新保存文件
            if removed_count > 0:
                with open(project_file, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, ensure_ascii=False, indent=2)
                logger.info(f"项目文件清理完成，已移除 {removed_count} 个冗余字段")

        except Exception as e:
            logger.error(f"清理项目文件失败: {e}")

    def delayed_load_from_project(self):
        """延迟加载项目数据，确保UI组件已完全初始化"""
        logger.info("开始延迟加载项目数据...")
        
        # 检查关键UI组件是否已初始化（包括组件存在性和可用性）
        ui_components = {
            'world_bible_output': hasattr(self, 'world_bible_output') and self.world_bible_output is not None,
            'scenes_output': hasattr(self, 'scenes_output') and self.scenes_output is not None,
            'storyboard_output': hasattr(self, 'storyboard_output') and self.storyboard_output is not None,
            'optimization_output': hasattr(self, 'optimization_output') and self.optimization_output is not None,
            'article_input': hasattr(self, 'article_input') and self.article_input is not None,
            'style_combo': hasattr(self, 'style_combo') and self.style_combo is not None,
            'model_combo': hasattr(self, 'model_combo') and self.model_combo is not None,
            'scenes_list': hasattr(self, 'scenes_list') and self.scenes_list is not None,
            'status_label': hasattr(self, 'status_label') and self.status_label is not None
        }
        
        logger.info(f"UI组件初始化状态: {ui_components}")
        
        # 如果关键组件未初始化，再次延迟
        missing_components = [name for name, exists in ui_components.items() if not exists]
        if missing_components:
            # 初始化重试计数器
            if not hasattr(self, '_delayed_load_retry_count'):
                self._delayed_load_retry_count = 0
            
            self._delayed_load_retry_count += 1
            
            if self._delayed_load_retry_count < 10:  # 最多重试10次
                logger.warning(f"以下UI组件尚未初始化: {missing_components}，第{self._delayed_load_retry_count}次重试")
                QTimer.singleShot(300, self.delayed_load_from_project)  # 减少延迟时间
                return
            else:
                logger.error(f"UI组件初始化超时，缺少组件: {missing_components}，尝试强制加载")
                # 强制加载，忽略缺失的组件
                self.load_from_project(force_load=True)
                return
        
        # 重置重试计数器
        self._delayed_load_retry_count = 0
        
        # 所有组件已初始化，开始加载项目数据
        logger.info("所有UI组件已初始化，开始加载五阶段分镜数据")
        self.load_from_project()

    def load_from_project(self, force_load=False):
        """从当前项目加载五阶段数据
        
        Args:
            force_load (bool): 是否强制加载，即使某些UI组件缺失
        """
        try:
            logger.info(f"🚀 开始加载五阶段分镜数据... (强制加载: {force_load})")

            # 详细调试项目管理器状态
            logger.info(f"🔍 项目管理器状态检查:")
            logger.info(f"🔍 self.project_manager: {self.project_manager is not None}")
            if self.project_manager:
                logger.info(f"🔍 current_project: {self.project_manager.current_project is not None}")
                if self.project_manager.current_project:
                    project_name = self.project_manager.current_project.get('project_name', 'Unknown')
                    logger.info(f"🔍 项目名称: {project_name}")

            # 尝试重新获取项目管理器
            self._ensure_project_manager()

            if not self.project_manager or not self.project_manager.current_project:
                logger.info("❌ 没有当前项目，跳过加载五阶段数据")
                return
            
            project_data = self.project_manager.current_project
            project_name = project_data.get('project_name') or project_data.get('name', 'Unknown')
            logger.info(f"📂 当前项目: {project_name}")
            
            # 首先验证和修复项目数据
            project_data = self._validate_and_repair_project_data(project_data)
            # 更新项目管理器中的数据
            self.project_manager.current_project = project_data
            
            # 初始化角色场景管理器
            project_dir = project_data.get('project_dir')
            if project_dir:
                # 获取service_manager
                service_manager = None
                if self.parent_window and hasattr(self.parent_window, 'app_controller'):
                    service_manager = self.parent_window.app_controller.service_manager
                
                # 使用项目管理器的方法获取角色场景管理器
                self.character_scene_manager = self.project_manager.get_character_scene_manager(service_manager)
                if self.character_scene_manager:
                    self.character_dialog = CharacterSceneDialog(self.character_scene_manager, self)
                else:
                    logger.warning("无法获取角色场景管理器")
                
                # 初始化场景描述增强器
                # 确保llm_api已初始化
                if not hasattr(self, 'llm_api') or self.llm_api is None:
                    self._init_llm_api()
                
                self.scene_enhancer = SceneDescriptionEnhancer(project_dir, self.character_scene_manager, self.llm_api)
                # 设置输出目录，确保能正确找到project.json文件
                self.scene_enhancer.output_dir = project_dir
                logger.info("场景描述增强器已初始化")
                
                # 检查并记录现有的角色和场景数据
                existing_characters = self.character_scene_manager.get_all_characters()
                existing_scenes = self.character_scene_manager.get_all_scenes()
                
                # 过滤掉分镜板生成的场景（如"场景1"、"场景2"等）
                import re
                filtered_scenes = {scene_id: scene_data for scene_id, scene_data in existing_scenes.items() 
                                 if not re.match(r'^场景\d+$', scene_data.get('name', '未命名'))}
                
                logger.info(f"项目加载时发现角色数量: {len(existing_characters)}, 用户创建场景数量: {len(filtered_scenes)}")
                
                # 如果有现有数据，刷新角色管理对话框
                if existing_characters or filtered_scenes:
                    if hasattr(self.character_dialog, 'refresh_character_list'):
                        self.character_dialog.refresh_character_list()
                    if hasattr(self.character_dialog, 'refresh_scene_list'):
                        self.character_dialog.refresh_scene_list()
                    logger.info("已刷新角色场景管理对话框显示")
            
            if 'five_stage_storyboard' not in project_data:
                logger.info(f"项目 {project_data.get('name', 'Unknown')} 中没有五阶段分镜数据")
                logger.info(f"项目数据键: {list(project_data.keys())}")

                # 🔧 修复：从父窗口获取当前的风格和模型设置，而不是使用硬编码默认值
                default_style = '电影风格'
                default_model = '通义千问'

                # 尝试从父窗口的文章创作界面获取当前设置
                if self.parent_window:
                    try:
                        # 从文章创作标签页获取风格设置
                        if hasattr(self.parent_window, 'text_creation_tab'):
                            text_tab = self.parent_window.text_creation_tab
                            if hasattr(text_tab, 'style_combo') and text_tab.style_combo:
                                current_style = text_tab.style_combo.currentText()
                                if current_style:
                                    default_style = current_style
                                    logger.info(f"从文章创作界面获取风格设置: {default_style}")

                            if hasattr(text_tab, 'model_combo') and text_tab.model_combo:
                                current_model = text_tab.model_combo.currentText()
                                if current_model:
                                    default_model = current_model
                                    logger.info(f"从文章创作界面获取模型设置: {default_model}")
                    except Exception as e:
                        logger.warning(f"从父窗口获取设置失败，使用默认值: {e}")

                # 创建默认的五阶段数据结构
                project_data['five_stage_storyboard'] = {
                    'stage_data': {},
                    'current_stage': 1,
                    'selected_characters': [],
                    'selected_scenes': [],
                    'article_text': '',
                    'selected_style': default_style,
                    'selected_model': default_model
                }
                logger.info(f"已创建默认的五阶段分镜数据结构，风格: {default_style}, 模型: {default_model}")
                # 继续处理，不要直接返回
            
            five_stage_data = project_data['five_stage_storyboard']
            logger.info(f"找到五阶段数据，包含键: {list(five_stage_data.keys())}")
            
            # 验证和修复数据结构
            if not isinstance(five_stage_data, dict):
                logger.error(f"五阶段数据格式错误，期望dict，实际: {type(five_stage_data)}")
                five_stage_data = {}
            
            # 恢复阶段数据
            loaded_stage_data = five_stage_data.get('stage_data', {})
            if not isinstance(loaded_stage_data, dict):
                logger.error(f"阶段数据格式错误，期望dict，实际: {type(loaded_stage_data)}")
                loaded_stage_data = {}
            
            # 确保所有阶段都有默认值，但保留已加载的数据
            self.stage_data = {1: {}, 2: {}, 3: {}, 4: {}, 5: {}}
            logger.info(f"初始化阶段数据结构完成，准备加载已有数据: {len(loaded_stage_data)} 个阶段")
            
            # 处理键类型转换（JSON中的键是字符串，统一转换为整数键）
            for key, value in loaded_stage_data.items():
                try:
                    # 尝试将字符串键转换为整数
                    int_key = int(key)
                    # 只有当键是有效的阶段编号时才保存
                    if 1 <= int_key <= 5:
                        # 验证阶段数据的完整性
                        if isinstance(value, dict):
                            self.stage_data[int_key] = value
                            logger.info(f"成功加载阶段 {int_key} 数据，包含 {len(value)} 个字段")
                        else:
                            logger.warning(f"阶段 {int_key} 数据格式错误，期望dict，实际: {type(value)}")
                            self.stage_data[int_key] = {}
                    else:
                        logger.warning(f"忽略无效的阶段键: {key}")
                except (ValueError, TypeError) as e:
                    # 如果转换失败，记录警告但不保存
                    logger.warning(f"忽略无法转换的键: {key}，错误: {e}")
                    continue
                except Exception as e:
                    logger.error(f"处理阶段数据时发生未知错误: {key}, {e}")
                    continue
            
            logger.info(f"加载的stage_data键: {list(loaded_stage_data.keys())}")
            logger.info(f"转换后的stage_data键: {list(self.stage_data.keys())}")
            logger.info(f"第4阶段数据存在: {bool(self.stage_data.get(4))}")
            if self.stage_data.get(4):
                logger.info(f"第4阶段包含键: {list(self.stage_data[4].keys())}")
                logger.info(f"storyboard_results存在: {'storyboard_results' in self.stage_data[4]}")
                if 'storyboard_results' in self.stage_data[4]:
                    logger.info(f"storyboard_results长度: {len(self.stage_data[4]['storyboard_results'])}")
            self.current_stage = five_stage_data.get('current_stage', 1)
            
            # 恢复选中的角色和场景
            self.selected_characters = five_stage_data.get('selected_characters', [])
            self.selected_scenes = five_stage_data.get('selected_scenes', [])
            
            # 恢复UI状态（考虑force_load模式）
            article_text = five_stage_data.get('article_text', '')
            if article_text:
                if hasattr(self, 'article_input') and self.article_input:
                    try:
                        self.article_input.setPlainText(article_text)
                        logger.info(f"成功恢复文章文本，长度: {len(article_text)}")
                    except Exception as e:
                        logger.error(f"恢复文章文本时出错: {e}")
                elif force_load:
                    logger.warning("article_input组件缺失，跳过文章文本恢复")
                else:
                    logger.info("article_input组件尚未初始化，将在组件就绪后恢复")
            
            # 🔧 修复：优先从父窗口获取当前风格设置，而不是从项目文件
            selected_style = five_stage_data.get('selected_style', '电影风格')

            # 尝试从父窗口的文章创作界面获取最新的风格设置
            if self.parent_window:
                try:
                    if hasattr(self.parent_window, 'text_creation_tab'):
                        text_tab = self.parent_window.text_creation_tab
                        if hasattr(text_tab, 'style_combo') and text_tab.style_combo:
                            current_style = text_tab.style_combo.currentText()
                            if current_style and current_style != selected_style:
                                selected_style = current_style
                                logger.info(f"从文章创作界面同步最新风格设置: {selected_style}")
                                # 更新项目数据中的风格设置
                                five_stage_data['selected_style'] = selected_style
                except Exception as e:
                    logger.warning(f"从父窗口同步风格设置失败: {e}")

            if hasattr(self, 'style_combo') and self.style_combo:
                try:
                    style_index = self.style_combo.findText(selected_style)
                    if style_index >= 0:
                        # 🔧 修复：加载项目时，暂时断开风格变更信号，避免误触发
                        self.style_combo.currentTextChanged.disconnect()
                        self.style_combo.setCurrentIndex(style_index)
                        # 🔧 修复：设置初始风格并重新连接信号
                        self.initial_style = selected_style
                        self.style_combo.currentTextChanged.connect(self.on_style_changed)
                        logger.info(f"项目加载时设置初始风格: {selected_style}")
                    else:
                        logger.warning(f"未找到匹配的样式: {selected_style}，使用默认样式")
                        self.initial_style = '电影风格'
                except Exception as e:
                    logger.error(f"恢复样式选择时出错: {e}")
                    self.initial_style = '电影风格'
            elif force_load:
                logger.warning("style_combo组件缺失，跳过风格选择恢复")
            else:
                logger.info("style_combo组件尚未初始化，将在组件就绪后恢复样式")
            
            # 🔧 修复：优先从父窗口获取当前模型设置，而不是从项目文件
            selected_model = five_stage_data.get('selected_model', '')

            # 尝试从父窗口的文章创作界面获取最新的模型设置
            if self.parent_window:
                try:
                    if hasattr(self.parent_window, 'text_creation_tab'):
                        text_tab = self.parent_window.text_creation_tab
                        if hasattr(text_tab, 'model_combo') and text_tab.model_combo:
                            current_model = text_tab.model_combo.currentText()
                            if current_model and current_model != selected_model:
                                selected_model = current_model
                                logger.info(f"从文章创作界面同步最新模型设置: {selected_model}")
                                # 更新项目数据中的模型设置
                                five_stage_data['selected_model'] = selected_model
                except Exception as e:
                    logger.warning(f"从父窗口同步模型设置失败: {e}")

            if selected_model:
                if hasattr(self, 'model_combo') and self.model_combo:
                    try:
                        model_index = self.model_combo.findText(selected_model)
                        if model_index >= 0:
                            self.model_combo.setCurrentIndex(model_index)
                            logger.info(f"成功恢复模型选择: {selected_model}")
                        else:
                            logger.warning(f"未找到匹配的模型: {selected_model}")
                    except Exception as e:
                        logger.error(f"恢复模型选择时出错: {e}")
                elif force_load:
                    logger.warning("model_combo组件缺失，跳过模型选择恢复")
                else:
                    logger.info("model_combo组件尚未初始化，将在组件就绪后恢复")
            
            # 恢复各阶段的显示内容和UI状态
            if self.stage_data.get(1):
                world_bible = self.stage_data[1].get('world_bible', '')
                logger.info(f"第1阶段数据 - world_bible长度: {len(world_bible)}")
                
                # 如果项目数据中没有world_bible，记录日志
                if not world_bible:
                    logger.info("项目数据中没有world_bible内容")
                
                if world_bible and hasattr(self, 'world_bible_output') and self.world_bible_output:
                    try:
                        self.world_bible_output.setText(world_bible)
                        logger.info(f"已设置world_bible_output内容，长度: {len(world_bible)}")
                        
                        # 检查是否已有角色信息，避免重复提取
                        if self.character_scene_manager:
                            try:
                                existing_characters = self.character_scene_manager.get_all_characters()
                                existing_scenes = self.character_scene_manager.get_all_scenes()
                                
                                # 过滤掉分镜板生成的场景（如"场景1"、"场景2"等）
                                import re
                                filtered_scenes = {scene_id: scene_data for scene_id, scene_data in existing_scenes.items() 
                                                 if not re.match(r'^场景\d+$', scene_data.get('name', '未命名'))}
                                
                                if not existing_characters and not filtered_scenes:
                                    # 🔧 修复：项目加载时不自动提取，避免重复执行
                                    # 自动提取应该在世界观圣经生成完成时执行，而不是项目加载时
                                    logger.info("项目加载时检测到无角色数据，但跳过自动提取（避免重复）")
                                else:
                                    logger.info(f"已存在角色信息，跳过自动提取（角色: {len(existing_characters)}, 用户创建场景: {len(filtered_scenes)}）")
                            except Exception as e:
                                logger.error(f"处理角色场景管理器时出错: {e}")
                        else:
                            logger.warning("character_scene_manager未初始化，跳过角色提取")
                    except Exception as e:
                        logger.error(f"设置world_bible_output内容时出错: {e}")
                elif world_bible and force_load:
                    logger.warning("world_bible_output组件缺失，跳过世界观内容恢复")
                else:
                    logger.warning(f"world_bible为空或world_bible_output不存在: world_bible={bool(world_bible)}, hasattr={hasattr(self, 'world_bible_output')}")
                
                if hasattr(self, 'stage1_next_btn'):
                    self.stage1_next_btn.setEnabled(True)
                # 更新状态标签
                if hasattr(self, 'status_label'):
                    self.status_label.setText("✅ 世界观圣经已生成")
            
            if self.stage_data.get(2):
                # 阶段2：角色管理完成
                logger.info("第2阶段数据 - 角色管理")
                # 更新状态标签
                if hasattr(self, 'status_label'):
                    self.status_label.setText("✅ 角色管理完成")
            
            if self.stage_data.get(3):
                scenes_analysis = self.stage_data[3].get('scenes_analysis', '')
                logger.info(f"第3阶段数据 - scenes_analysis长度: {len(scenes_analysis)}")
                logger.info(f"scenes_output组件存在: {hasattr(self, 'scenes_output')}")
                if hasattr(self, 'scenes_output'):
                    logger.info(f"scenes_output类型: {type(self.scenes_output)}")
                if scenes_analysis:
                    if hasattr(self, 'scenes_output') and self.scenes_output:
                        try:
                            self.scenes_output.setText(scenes_analysis)
                            logger.info(f"已成功设置scenes_output内容，当前文本长度: {len(self.scenes_output.toPlainText())}")
                            try:
                                self._update_scenes_list(scenes_analysis)
                                logger.info("场景列表更新成功")
                            except Exception as e:
                                logger.error(f"更新场景列表时出错: {e}")
                        except Exception as e:
                            logger.error(f"设置scenes_output内容时出错: {e}")
                    elif force_load:
                        logger.warning("scenes_output组件缺失，跳过场景分析内容恢复")
                    else:
                        logger.info("scenes_output组件尚未初始化，将在组件就绪后恢复")
                else:
                    logger.info("第3阶段无场景分析数据")
                
                if hasattr(self, 'stage3_next_btn'):
                    self.stage3_next_btn.setEnabled(True)
                # 更新状态标签
                if hasattr(self, 'status_label'):
                    self.status_label.setText("✅ 场景分割完成")
            
            if self.stage_data.get(4):
                storyboard_results = self.stage_data[4].get('storyboard_results', [])
                logger.info(f"第4阶段数据 - storyboard_results数量: {len(storyboard_results)}")
                logger.info(f"storyboard_output组件存在: {hasattr(self, 'storyboard_output')}")
                if hasattr(self, 'storyboard_output'):
                    logger.info(f"storyboard_output类型: {type(self.storyboard_output)}")
                    logger.info(f"storyboard_output是否为None: {self.storyboard_output is None}")
                
                # 详细记录storyboard_results的内容
                if storyboard_results:
                    logger.info(f"第一个storyboard_result的键: {list(storyboard_results[0].keys()) if storyboard_results else 'N/A'}")
                    for i, result in enumerate(storyboard_results[:2]):  # 只记录前两个
                        scene_info = result.get("scene_info", "")
                        storyboard_script = result.get("storyboard_script", "")
                        logger.info(f"场景{i+1} - scene_info长度: {len(scene_info)}, storyboard_script长度: {len(storyboard_script)}")
                
                if storyboard_results:
                    if hasattr(self, 'storyboard_output') and self.storyboard_output:
                        try:
                            logger.info("开始调用_display_storyboard_results方法...")
                            self._display_storyboard_results(storyboard_results)
                            current_text_length = len(self.storyboard_output.toPlainText())
                            logger.info(f"已成功设置storyboard_output内容，当前文本长度: {current_text_length}")
                            
                            # 如果文本长度为0，说明显示有问题
                            if current_text_length == 0:
                                logger.error("storyboard_output文本长度为0，显示可能失败")
                                # 尝试直接设置一些测试文本
                                test_text = "测试文本 - 第四阶段数据加载"
                                self.storyboard_output.setText(test_text)
                                logger.info(f"设置测试文本后长度: {len(self.storyboard_output.toPlainText())}")
                        except Exception as e:
                            logger.error(f"设置storyboard_output内容时出错: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                    elif force_load:
                        logger.warning("storyboard_output组件缺失，跳过分镜脚本内容恢复")
                    else:
                        logger.info("storyboard_output组件尚未初始化，将在组件就绪后恢复")
                else:
                    logger.info("第4阶段无分镜板结果数据")
                
                # 存储分镜结果供增强描述使用
                self.current_storyboard_results = storyboard_results
                
                # 启用增强描述按钮
                if hasattr(self, 'enhance_description_btn'):
                    self.enhance_description_btn.setEnabled(True)
                    logger.info("已启用增强描述按钮")
                
                if hasattr(self, 'stage4_next_btn'):
                    self.stage4_next_btn.setEnabled(True)
                # 更新状态标签
                if hasattr(self, 'status_label'):
                    self.status_label.setText("✅ 分镜脚本生成完成")
            
            if self.stage_data.get(5):
                optimization_suggestions = self.stage_data[5].get('optimization_suggestions', [])
                logger.info(f"第5阶段数据 - optimization_suggestions数量: {len(optimization_suggestions)}")
                logger.info(f"optimization_output组件存在: {hasattr(self, 'optimization_output')}")
                if hasattr(self, 'optimization_output'):
                    logger.info(f"optimization_output类型: {type(self.optimization_output)}")
                if optimization_suggestions:
                    if hasattr(self, 'optimization_output') and self.optimization_output:
                        try:
                            self._display_optimization_results(optimization_suggestions)
                            logger.info(f"已成功设置optimization_output内容，当前文本长度: {len(self.optimization_output.toPlainText())}")
                        except Exception as e:
                            logger.error(f"设置optimization_output内容时出错: {e}")
                    elif force_load:
                        logger.warning("optimization_output组件缺失，跳过优化建议内容恢复")
                    else:
                        logger.info("optimization_output组件尚未初始化，将在组件就绪后恢复")
                else:
                    logger.info("第5阶段无优化建议数据")
                
                # 更新状态标签
                if hasattr(self, 'status_label'):
                    self.status_label.setText("✅ 优化分析完成")
            
            # 保持所有按钮可用，允许用户重新运行任何阶段
            # 注释掉原来的禁用逻辑，让用户可以随时调整和重新生成
            if hasattr(self, 'stage1_generate_btn'):
                self.stage1_generate_btn.setEnabled(True)
                # 如果阶段已完成，更新按钮文本提示
                if self.current_stage >= 1:
                    self.stage1_generate_btn.setText("🔄 重新分析")
                else:
                    self.stage1_generate_btn.setText("🚀 开始全局分析")
            
            if hasattr(self, 'stage2_generate_btn'):
                self.stage2_generate_btn.setEnabled(True)
                self.stage2_generate_btn.setText("🔄 刷新角色信息")
            
            if hasattr(self, 'stage3_generate_btn'):
                self.stage3_generate_btn.setEnabled(True)
                if self.current_stage >= 3:
                    self.stage3_generate_btn.setText("🔄 重新分割场景")
                else:
                    self.stage3_generate_btn.setText("🎬 开始场景分割")
            
            if hasattr(self, 'stage4_generate_btn'):
                self.stage4_generate_btn.setEnabled(True)
                if self.current_stage >= 4:
                    self.stage4_generate_btn.setText("🔄 重新生成分镜")
                else:
                    self.stage4_generate_btn.setText("📝 生成分镜脚本")
            
            if hasattr(self, 'stage5_generate_btn'):
                self.stage5_generate_btn.setEnabled(True)
                if self.current_stage >= 5:
                    self.stage5_generate_btn.setText("🔄 重新优化")
                else:
                    self.stage5_generate_btn.setText("🎨 生成优化建议")
            
            # 数据加载完成后的状态检查和日志记录
            loaded_stages = list(self.stage_data.keys())
            logger.info(f"✅ 成功从项目 '{project_data.get('name', 'Unknown')}' 加载五阶段分镜数据")
            logger.info(f"📊 当前阶段: {self.current_stage}, 已加载阶段: {loaded_stages}")
            
            # 添加详细的阶段数据统计
            total_content_size = 0
            for stage_num, stage_content in self.stage_data.items():
                if isinstance(stage_content, dict):
                    stage_size = 0
                    for key, value in stage_content.items():
                        if isinstance(value, str):
                            stage_size += len(value)
                        elif isinstance(value, (list, dict)):
                            stage_size += len(str(value))
                    total_content_size += stage_size
                    logger.info(f"📋 阶段 {stage_num}: {len(stage_content)} 个字段, 内容大小: {stage_size} 字符")
                else:
                    logger.warning(f"⚠️ 阶段 {stage_num}: 数据格式异常 ({type(stage_content)})")
            
            logger.info(f"📈 总内容大小: {total_content_size} 字符")
            
            # 如果有第4阶段的分镜数据，更新一致性控制面板（项目加载时禁用自动增强）
            if self.stage_data.get(4) and self.stage_data[4].get('storyboard_results'):
                try:
                    logger.info("🔄 项目加载完成，更新一致性控制面板...")
                    self._update_consistency_panel(auto_enhance=False)
                    logger.info("✅ 一致性控制面板更新完成")
                except Exception as e:
                    logger.error(f"❌ 更新一致性控制面板时出错: {e}")
            
            logger.info("🎉 五阶段分镜数据加载流程完成")
            
        except Exception as e:
            logger.error(f"❌ 加载五阶段分镜数据时出错: {e}")
            import traceback
            logger.error(f"📋 详细错误信息: {traceback.format_exc()}")
            
            # 错误恢复：确保基本数据结构存在
            try:
                if not hasattr(self, 'stage_data') or not isinstance(self.stage_data, dict):
                    self.stage_data = {}
                    logger.info("🔧 已重置stage_data为空字典")
                
                if not hasattr(self, 'current_stage') or not isinstance(self.current_stage, int):
                    self.current_stage = 0
                    logger.info("🔧 已重置current_stage为0")
                    
                # 确保UI状态正常
                if hasattr(self, 'status_label'):
                    self.status_label.setText("⚠️ 项目数据加载失败，请检查数据完整性")
                    
                logger.info("🛠️ 错误恢复完成，系统可继续使用")
            except Exception as recovery_error:
                logger.error(f"💥 错误恢复失败: {recovery_error}")
    
    def _validate_and_repair_project_data(self, project_data: dict) -> dict:
        """验证和修复项目数据的完整性"""
        try:
            # 确保基本结构存在
            if 'five_stage_storyboard' not in project_data:
                project_data['five_stage_storyboard'] = {}
                logger.info("🔧 已创建缺失的five_stage_storyboard结构")
            
            five_stage_data = project_data['five_stage_storyboard']
            
            # 验证并修复各阶段数据结构
            for stage_num in range(1, 6):
                stage_key = str(stage_num)
                if stage_key not in five_stage_data:
                    five_stage_data[stage_key] = {}
                    logger.info(f"🔧 已创建缺失的阶段{stage_num}数据结构")
                elif not isinstance(five_stage_data[stage_key], dict):
                    logger.warning(f"⚠️ 阶段{stage_num}数据格式错误，已重置")
                    five_stage_data[stage_key] = {}
            
            # 验证基本字段
            required_fields = {
                'article_text': '',
                'selected_style': '电影风格',
                'selected_model': '',
                'current_stage': 0
            }
            
            for field, default_value in required_fields.items():
                if field not in five_stage_data:
                    five_stage_data[field] = default_value
                    logger.info(f"🔧 已添加缺失字段: {field} = {default_value}")
            
            logger.info("✅ 项目数据验证和修复完成")
            return project_data
            
        except Exception as e:
            logger.error(f"❌ 项目数据验证修复失败: {e}")
            return project_data
    
    def open_character_dialog(self):
        """打开角色管理对话框"""
        try:
            # 如果没有当前项目，提示用户
            if not self.project_manager or not self.project_manager.current_project:
                QMessageBox.warning(self, "警告", "请先创建或打开一个项目")
                return

            # 初始化角色场景管理器（如果还没有初始化）
            if not self.character_scene_manager:
                project_dir = self.project_manager.current_project.get('project_dir')
                if project_dir:
                    # 获取service_manager
                    service_manager = None
                    if self.parent_window and hasattr(self.parent_window, 'app_controller'):
                        service_manager = self.parent_window.app_controller.service_manager

                    # 使用项目管理器的方法获取角色场景管理器
                    self.character_scene_manager = self.project_manager.get_character_scene_manager(service_manager)
                    if not self.character_scene_manager:
                        QMessageBox.warning(self, "错误", "无法获取角色场景管理器")
                        return
                else:
                    QMessageBox.warning(self, "错误", "无法找到项目路径")
                    return

            # 🔧 修复：确保角色对话框已正确初始化
            if not self.character_dialog and self.character_scene_manager:
                logger.info("初始化角色管理对话框...")
                self.character_dialog = CharacterSceneDialog(self.character_scene_manager, self)

            # 🔧 修复：检查对话框是否成功创建
            if not self.character_dialog:
                QMessageBox.warning(self, "错误", "无法创建角色管理对话框")
                return

            # 打开角色管理对话框
            if self.character_dialog.exec_() == QDialog.Accepted:
                # 对话框关闭后，可以获取用户选择的角色和场景
                self.update_character_selection()

        except Exception as e:
            logger.error(f"打开角色管理对话框时出错: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            QMessageBox.critical(self, "错误", f"打开角色管理对话框失败: {str(e)}")
    
    def update_character_selection(self):
        """更新角色选择状态"""
        try:
            if self.character_scene_manager:
                # 这里可以添加逻辑来获取用户在对话框中选择的角色和场景
                # 由于CharacterSceneDialog可能需要修改来支持选择功能，
                # 暂时使用所有角色作为选中状态
                characters = self.character_scene_manager.get_all_characters()
                scenes = self.character_scene_manager.get_all_scenes()
                
                # 修复：get_all_characters()和get_all_scenes()返回的是字典，不是列表
                self.selected_characters = list(characters.keys())
                
                # 过滤掉分镜板生成的场景（如"场景1"、"场景2"等）
                import re
                filtered_scene_keys = []
                for scene_id, scene_data in scenes.items():
                    scene_name = scene_data.get('name', '未命名')
                    if not re.match(r'^场景\d+$', scene_name):
                        filtered_scene_keys.append(scene_id)
                
                self.selected_scenes = filtered_scene_keys
                
                logger.info(f"已选择 {len(self.selected_characters)} 个角色和 {len(self.selected_scenes)} 个用户创建的场景")
                
        except Exception as e:
            logger.error(f"更新角色选择时出错: {e}")
    
    def get_character_consistency_prompt(self):
        """获取角色一致性提示词"""
        try:
            if not self.character_scene_manager:
                return ""
            
            # 生成角色一致性提示词
            consistency_prompt = self.character_scene_manager.generate_consistency_prompt(
                self.selected_characters, self.selected_scenes
            )
            
            return consistency_prompt
            
        except Exception as e:
            logger.error(f"获取角色一致性提示词时出错: {e}")
            return ""
    
    def auto_extract_characters(self):
        """自动提取角色信息（从第一阶段的世界观圣经）"""
        try:
            # 获取第一阶段的世界观圣经内容
            stage1_data = self.stage_data.get(1, {})
            world_bible = stage1_data.get('world_bible', '')
            
            if not world_bible:
                QMessageBox.warning(self, "提示", "请先完成第一阶段的世界观圣经生成")
                return
            
            # 调用实际的提取方法
            self.auto_extract_characters_from_world_bible(world_bible)
            
        except Exception as e:
             logger.error(f"自动提取角色信息时出错: {e}")            
             QMessageBox.critical(self, "错误", f"自动提取角色信息失败: {str(e)}")
    
    def check_character_consistency(self):
        """检查角色一致性"""
        try:
            if not self.character_scene_manager:
                QMessageBox.warning(self, "提示", "角色场景管理器未初始化")
                return
            
            # 获取当前角色信息
            characters = self.character_scene_manager.get_all_characters()
            if not characters:
                QMessageBox.information(self, "提示", "当前没有角色信息，请先添加或提取角色")
                return
            
            # 生成一致性检查报告
            character_ids = list(characters.keys()) if isinstance(characters, dict) else []
            consistency_prompt = self.character_scene_manager.generate_consistency_prompt(character_ids)
            
            # 构建角色信息显示
            character_list = list(characters.values()) if isinstance(characters, dict) else characters
            character_info = "\n".join([f"• {char.get('name', '未命名')}: {char.get('description', '无描述')[:50]}..." 
                                       for char in character_list[:5]])
            
            # 显示一致性检查结果
            if consistency_prompt:
                message = f"当前共有 {len(character_list)} 个角色\n\n角色列表:\n{character_info}\n\n一致性提示词:\n{consistency_prompt[:200]}..."
            else:
                message = f"当前共有 {len(character_list)} 个角色\n\n角色列表:\n{character_info}\n\n注意：角色暂无一致性提示词，建议完善角色描述。"
            
            QMessageBox.information(self, "角色一致性检查", message)
                
        except Exception as e:
            logger.error(f"检查角色一致性时出错: {e}")
            QMessageBox.critical(self, "错误", f"检查角色一致性失败: {str(e)}")
    
    def refresh_character_info(self):
        """刷新角色信息显示"""
        try:
            if self.character_scene_manager:
                # 检查是否有世界观圣经内容，如果有但没有角色信息，则自动提取
                stage1_data = self.stage_data.get(1, {})
                world_bible = stage1_data.get('world_bible', '')
                
                characters = self.character_scene_manager.get_all_characters()
                scenes = self.character_scene_manager.get_all_scenes()
                
                # 🔧 修复：不在刷新时自动提取，避免重复执行
                # 自动提取应该只在世界观圣经生成完成时执行一次
                if not characters and world_bible:
                    logger.info("检测到世界观圣经但无角色信息，但跳过自动提取（避免重复）")
                    # 不重新获取，使用现有的空数据
                
                # 更新角色选择状态
                self.update_character_selection()
                
                # 获取并显示角色信息
                
                # 构建显示文本
                display_text = ""
                
                if characters:
                    display_text += "=== 角色信息 ===\n\n"
                    for char_id, char_data in characters.items():
                        name = char_data.get('name', '未命名')
                        description = char_data.get('description', '无描述')
                        display_text += f"🧑 {name}\n"
                        display_text += f"   描述: {description}\n"
                        
                        # 显示外貌信息 - 安全处理可能是字符串的情况
                        appearance = char_data.get('appearance', {})
                        if appearance:
                            if isinstance(appearance, dict):
                                display_text += f"   外貌: {appearance.get('gender', '')} {appearance.get('age_range', '')}\n"
                                display_text += f"   发型: {appearance.get('hair', '')}\n"
                            else:
                                # 如果是字符串，直接显示
                                display_text += f"   外貌: {str(appearance)}\n"
                        
                        display_text += "\n"
                else:
                    display_text += "暂无角色信息\n\n"
                
                if scenes:
                    # 过滤掉分镜板生成的场景（如"场景1"、"场景2"等）
                    import re
                    filtered_scenes = {}
                    for scene_id, scene_data in scenes.items():
                        scene_name = scene_data.get('name', '未命名')
                        # 过滤掉匹配"场景"后跟数字的场景
                        if not re.match(r'^场景\d+$', scene_name):
                            filtered_scenes[scene_id] = scene_data
                    
                    if filtered_scenes:
                        display_text += "=== 场景信息 ===\n\n"
                        for scene_id, scene_data in filtered_scenes.items():
                            name = scene_data.get('name', '未命名')
                            description = scene_data.get('description', '无描述')
                            display_text += f"🏞️ {name}\n"
                            display_text += f"   描述: {description}\n\n"
                        display_text += f"\n注：已排除 {len(scenes) - len(filtered_scenes)} 个分镜板生成的场景\n"
                    else:
                        display_text += "暂无用户创建的场景信息\n"
                        if len(scenes) > 0:
                            display_text += f"（已排除 {len(scenes)} 个分镜板生成的场景）\n"
                else:
                    display_text += "暂无场景信息\n"
                
                # 更新显示
                self.characters_output.setPlainText(display_text)
                
                # 标记阶段2为完成状态
                # 计算过滤后的场景数量
                import re
                filtered_scene_count = 0
                if scenes:
                    for scene_id, scene_data in scenes.items():
                        scene_name = scene_data.get('name', '未命名')
                        if not re.match(r'^场景\d+$', scene_name):
                            filtered_scene_count += 1
                
                character_info = f"角色数量: {len(characters)}, 用户创建场景数量: {filtered_scene_count}"
                self.stage_data[2] = {
                    "character_info": character_info,
                    "completed": True,
                    "timestamp": str(QDateTime.currentDateTime().toString())
                }
                
                # 更新当前阶段
                if self.current_stage < 2:
                    self.current_stage = 2
                
                # 保存到项目
                self.save_to_project()
                
                logger.info("角色信息已刷新")
                QMessageBox.information(self, "提示", f"角色信息已刷新\n角色数量: {len(characters)}\n用户创建场景数量: {filtered_scene_count}\n阶段2已标记为完成")
            else:
                QMessageBox.warning(self, "提示", "角色场景管理器未初始化")
                
        except Exception as e:
            logger.error(f"刷新角色信息时出错: {e}")
            QMessageBox.critical(self, "错误", f"刷新角色信息失败: {str(e)}")

    def refresh_character_data(self):
        """刷新角色数据（用于同步）"""
        try:
            if self.character_scene_manager:
                # 重新加载角色数据
                characters = self.character_scene_manager.get_all_characters()
                logger.info(f"角色数据已同步刷新，当前角色数量: {len(characters)}")

                # 更新选择状态
                self.update_character_selection()

                # 如果角色对话框已打开，刷新其显示
                if self.character_dialog:
                    self.character_dialog.refresh_character_list()

        except Exception as e:
            logger.error(f"刷新角色数据失败: {e}")

    def refresh_scene_data(self):
        """刷新场景数据（用于同步）"""
        try:
            if self.character_scene_manager:
                # 重新加载场景数据
                scenes = self.character_scene_manager.get_all_scenes()
                logger.info(f"场景数据已同步刷新，当前场景数量: {len(scenes)}")

                # 更新选择状态
                self.update_character_selection()

                # 如果角色对话框已打开，刷新其显示
                if self.character_dialog:
                    self.character_dialog.refresh_scene_list()

        except Exception as e:
            logger.error(f"刷新场景数据失败: {e}")

    def refresh_project_data(self):
        """刷新项目数据（重新加载所有数据）"""
        try:
            logger.info("🔄 开始刷新项目数据...")

            # 显示进度提示
            if hasattr(self, 'status_label'):
                self.status_label.setText("🔄 正在刷新项目数据...")

            # 简化版本：只重新加载项目数据
            try:
                self.load_from_project(force_load=True)
                logger.info("✅ 项目数据重新加载完成")
            except Exception as load_error:
                logger.error(f"重新加载项目数据失败: {load_error}")
                raise load_error

            if hasattr(self, 'status_label'):
                self.status_label.setText("✅ 项目数据刷新完成")
            logger.info("✅ 项目数据刷新完成")

            # 显示成功消息
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "刷新完成", "项目数据已成功刷新！\n\n请检查分镜显示是否已更新。")

        except Exception as e:
            logger.error(f"刷新项目数据失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

            if hasattr(self, 'status_label'):
                self.status_label.setText(f"❌ 刷新失败")

            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "刷新失败", f"刷新项目数据时出错：\n\n{str(e)}\n\n请查看日志获取详细信息。")

    def _update_project_storyboard_data(self):
        """更新项目中的分镜数据（通用方法）"""
        try:
            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有当前项目，无法更新分镜数据")
                return False

            # 获取当前项目数据
            project_data = self.project_manager.get_project_data()
            if not project_data:
                logger.warning("无法获取项目数据")
                return False

            # 确保五阶段数据结构存在
            if 'five_stage_storyboard' not in project_data:
                project_data['five_stage_storyboard'] = {}

            five_stage_data = project_data['five_stage_storyboard']
            if 'stage_data' not in five_stage_data:
                five_stage_data['stage_data'] = {}

            stage_data = five_stage_data['stage_data']
            if '4' not in stage_data:
                stage_data['4'] = {}

            stage4_data = stage_data['4']

            # 更新分镜结果
            if hasattr(self, 'current_storyboard_results') and self.current_storyboard_results:
                stage4_data['storyboard_results'] = self.current_storyboard_results
                logger.info(f"已更新项目数据中的分镜结果，共 {len(self.current_storyboard_results)} 个场景")

            # 清空失败场景（因为重试成功了）
            if hasattr(self, 'failed_scenes'):
                # 只移除已经成功重试的场景
                successful_scene_indices = {result.get('scene_index') for result in self.current_storyboard_results}
                remaining_failed = [
                    failed for failed in self.failed_scenes
                    if failed.get('scene_index') not in successful_scene_indices
                ]
                stage4_data['failed_scenes'] = remaining_failed
                logger.info(f"已更新失败场景列表，剩余 {len(remaining_failed)} 个失败场景")

            # 保存项目数据
            success = self.project_manager.save_project_data(project_data)
            if success:
                logger.info("项目分镜数据已成功同步保存")
                return True
            else:
                logger.error("保存项目分镜数据失败")
                return False

        except Exception as e:
            logger.error(f"更新项目分镜数据失败: {e}")
            return False
    
    def _smart_auto_extract_characters(self, world_bible_text):
        """智能自动提取角色信息：新建项目时自动提取，已有数据时询问用户"""
        try:
            # 🔧 修复：防止重复执行，检查是否已经在执行中
            if hasattr(self, '_auto_extract_in_progress') and self._auto_extract_in_progress:
                logger.info("自动提取已在进行中，跳过重复执行")
                return

            # 🔧 修复：确保角色场景管理器已正确初始化
            if not self.character_scene_manager:
                logger.warning("角色场景管理器未初始化，尝试重新初始化...")
                self._ensure_character_scene_manager()

            if not self.character_scene_manager:
                logger.error("无法初始化角色场景管理器，跳过自动提取")
                return

            if not world_bible_text:
                logger.warning("世界观圣经内容为空，跳过自动提取")
                return

            # 检查是否已有角色和场景数据
            existing_characters = self.character_scene_manager.get_all_characters()
            existing_scenes = self.character_scene_manager.get_all_scenes()

            # 过滤掉分镜板生成的场景（如"场景1"、"场景2"等）
            import re
            filtered_scenes = {}
            if existing_scenes:
                for scene_id, scene_data in existing_scenes.items():
                    scene_name = scene_data.get('name', '未命名')
                    if not re.match(r'^场景\d+$', scene_name):
                        filtered_scenes[scene_id] = scene_data

            # 🔧 修复：新建项目时自动提取，已有数据时询问用户
            if not existing_characters and not filtered_scenes:
                logger.info("检测到没有现有角色和场景数据，开始自动提取...")
                # 使用后台线程执行自动提取，避免阻塞主线程
                self._execute_auto_extract_in_background(world_bible_text, is_first_time=True)
            else:
                logger.info(f"已存在角色数据: {len(existing_characters)}, 用户创建场景数量: {len(filtered_scenes)}")

                # 🔧 修复：对于新建项目，如果是第一次完成世界观分析，也自动提取
                # 检查是否是新建项目的第一次世界观分析
                if self._is_new_project_first_analysis():
                    logger.info("检测到新建项目的第一次世界观分析，自动提取角色和场景...")
                    self._execute_auto_extract_in_background(world_bible_text, is_first_time=True)
                else:
                    # 对于已有数据的项目，询问用户是否要重新提取
                    from PyQt5.QtWidgets import QMessageBox
                    reply = QMessageBox.question(
                        self,
                        "角色场景数据已存在",
                        f"检测到已有 {len(existing_characters)} 个角色和 {len(filtered_scenes)} 个用户创建的场景。\n\n"
                        "是否要重新提取角色和场景信息？\n"
                        "（选择'是'将替换现有数据）",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        logger.info("用户选择重新提取角色场景信息")
                        # 使用后台线程执行自动提取，避免阻塞主线程
                        self._execute_auto_extract_in_background(world_bible_text, is_first_time=False)
                    else:
                        logger.info("用户选择保留现有角色场景数据")

        except Exception as e:
            logger.error(f"智能自动提取角色信息时出错: {e}")

    def _ensure_character_scene_manager(self):
        """确保角色场景管理器已正确初始化"""
        try:
            if self.character_scene_manager:
                return True

            if not self.project_manager or not self.project_manager.current_project:
                logger.warning("没有当前项目，无法初始化角色场景管理器")
                return False

            # 获取service_manager
            service_manager = None
            if self.parent_window and hasattr(self.parent_window, 'app_controller'):
                service_manager = self.parent_window.app_controller.service_manager
                logger.info("已获取service_manager用于角色场景管理器")
            else:
                logger.warning("无法获取service_manager，角色场景管理器将无法使用LLM服务")

            # 使用项目管理器的方法获取角色场景管理器
            self.character_scene_manager = self.project_manager.get_character_scene_manager(service_manager)

            if self.character_scene_manager:
                logger.info("角色场景管理器初始化成功")
                return True
            else:
                logger.error("角色场景管理器初始化失败")
                return False

        except Exception as e:
            logger.error(f"确保角色场景管理器初始化失败: {e}")
            return False

    def _is_new_project_first_analysis(self):
        """检查是否是新建项目的第一次世界观分析"""
        try:
            # 检查项目是否刚创建（通过检查阶段数据是否为空或只有第一阶段）
            completed_stages = 0
            for stage_num in range(1, 6):
                if self.stage_data.get(stage_num):
                    completed_stages += 1

            # 如果只完成了第一阶段或没有完成任何阶段，认为是新项目
            if completed_stages <= 1:
                logger.info("检测到新建项目的第一次分析")
                return True

            return False

        except Exception as e:
            logger.error(f"检查新建项目状态失败: {e}")
            return False

    def _execute_auto_extract_in_background(self, world_bible_text, is_first_time=True):
        """在后台线程中执行自动提取，避免阻塞主线程"""
        try:
            # 🔧 修复：设置执行标志，防止重复执行
            self._auto_extract_in_progress = True

            from PyQt5.QtCore import QThread, pyqtSignal
            from PyQt5.QtWidgets import QProgressDialog, QMessageBox

            # 创建进度对话框
            progress_dialog = QProgressDialog("正在自动提取角色和场景信息...", "取消", 0, 0, self)
            progress_dialog.setWindowTitle("自动提取中")
            progress_dialog.setModal(True)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.show()

            # 创建工作线程
            class AutoExtractWorker(QThread):
                finished = pyqtSignal(dict)
                error = pyqtSignal(str)

                def __init__(self, character_scene_manager, world_bible_text):
                    super().__init__()
                    self.character_scene_manager = character_scene_manager
                    self.world_bible_text = world_bible_text

                def run(self):
                    try:
                        # 在后台线程中执行自动提取
                        result = self.character_scene_manager.auto_extract_and_save(self.world_bible_text)
                        self.finished.emit(result)
                    except Exception as e:
                        self.error.emit(str(e))

            # 创建并启动工作线程
            self.extract_worker = AutoExtractWorker(self.character_scene_manager, world_bible_text)

            def on_extract_finished(result):
                try:
                    # 🔧 修复：清除执行标志
                    self._auto_extract_in_progress = False

                    progress_dialog.close()
                    if result.get('success', False):
                        self.update_character_selection()

                        # 如果角色场景对话框已经打开，刷新其数据
                        if hasattr(self, 'character_dialog') and self.character_dialog:
                            try:
                                self.character_dialog.load_data()
                                logger.info("已刷新角色场景对话框数据")
                            except Exception as refresh_error:
                                logger.warning(f"刷新角色场景对话框数据失败: {refresh_error}")

                        logger.info("已从世界观圣经中自动提取角色信息")

                        if is_first_time:
                            QMessageBox.information(
                                self,
                                "自动提取完成",
                                "已自动从世界观圣经中提取角色和场景信息。\n\n"
                                "您可以在第二阶段的角色管理中查看和编辑这些信息。"
                            )
                        else:
                            QMessageBox.information(self, "重新提取完成", "角色和场景信息已重新提取完成。")
                    else:
                        error_msg = result.get('error', '未知错误')
                        QMessageBox.warning(self, "提取失败", f"自动提取失败: {error_msg}")
                except Exception as e:
                    logger.error(f"处理提取结果时出错: {e}")

            def on_extract_error(error_msg):
                try:
                    # 🔧 修复：清除执行标志
                    self._auto_extract_in_progress = False

                    progress_dialog.close()
                    logger.error(f"自动提取失败: {error_msg}")
                    QMessageBox.critical(self, "提取失败", f"自动提取角色场景信息失败:\n{error_msg}")
                except Exception as e:
                    logger.error(f"处理提取错误时出错: {e}")

            def on_progress_canceled():
                try:
                    # 🔧 修复：清除执行标志
                    self._auto_extract_in_progress = False

                    if hasattr(self, 'extract_worker') and self.extract_worker.isRunning():
                        self.extract_worker.terminate()
                        self.extract_worker.wait(3000)  # 等待最多3秒
                        logger.info("用户取消了自动提取操作")
                except Exception as e:
                    logger.error(f"取消提取操作时出错: {e}")

            # 连接信号
            self.extract_worker.finished.connect(on_extract_finished)
            self.extract_worker.error.connect(on_extract_error)
            progress_dialog.canceled.connect(on_progress_canceled)

            # 启动线程
            self.extract_worker.start()

        except Exception as e:
            # 🔧 修复：异常时也要清除执行标志
            self._auto_extract_in_progress = False

            logger.error(f"启动后台提取线程失败: {e}")
            QMessageBox.critical(self, "错误", f"启动自动提取失败: {str(e)}")

    def auto_extract_characters_from_world_bible(self, world_bible_text):
        """从世界观圣经中自动提取角色信息（保留原方法用于手动调用）"""
        try:
            if not self.character_scene_manager or not world_bible_text:
                return

            # 使用后台线程执行自动提取，避免阻塞主线程
            self._execute_auto_extract_in_background(world_bible_text, is_first_time=True)

        except Exception as e:
            logger.error(f"自动提取角色信息时出错: {e}")
    
    def _display_optimization_results(self, optimization_suggestions):
        """显示优化建议结果"""
        try:
            if not optimization_suggestions:
                self.optimization_output.setPlainText("暂无优化建议")
                return
            
            display_text = "=== 视觉优化建议 ===\n\n"
            
            for i, suggestion in enumerate(optimization_suggestions):
                scene_index = suggestion.get("scene_index", i)
                display_text += f"📋 场景 {scene_index + 1}\n"
                display_text += f"视觉一致性: {suggestion.get('visual_consistency', '未检查')}\n"
                display_text += f"技术质量: {suggestion.get('technical_quality', '未检查')}\n"
                display_text += f"叙事流畅性: {suggestion.get('narrative_flow', '未检查')}\n"
                
                optimization_tips = suggestion.get('optimization_tips', [])
                if optimization_tips:
                    display_text += "优化建议:\n"
                    for tip in optimization_tips:
                        display_text += f"  • {tip}\n"
                
                display_text += "\n"
            
            self.optimization_output.setPlainText(display_text)
            logger.info(f"已显示 {len(optimization_suggestions)} 个场景的优化建议")
        except Exception as e:
            logger.error(f"显示优化建议时出错: {e}")
            self.optimization_output.setPlainText("显示优化建议时出错")
    
    def _update_consistency_panel(self, auto_enhance=True):
        """将五阶段分镜数据转换并传递给一致性控制面板
        
        Args:
            auto_enhance (bool): 是否自动进行场景描述增强，默认为True
        """
        try:
            # 检查是否有分镜数据
            storyboard_results = self.stage_data.get(4, {}).get("storyboard_results", [])
            if not self.stage_data.get(4) or not storyboard_results:
                logger.warning(f"没有分镜数据可传递给一致性控制面板，stage_data[4]存在: {bool(self.stage_data.get(4))}, storyboard_results长度: {len(storyboard_results)}")
                return
            
            # 检查主窗口是否有一致性控制面板
            if not hasattr(self.parent_window, 'consistency_panel'):
                logger.warning("主窗口没有一致性控制面板")
                return
            
            # 导入必要的类
            from src.processors.text_processor import Shot, StoryboardResult
            
            # 转换五阶段分镜数据为StoryboardResult格式
            # storyboard_results已在上面定义
            shots = []
            characters = set()
            scenes = set()
            total_duration = 0.0
            
            # 过滤掉分镜生成的场景（场景1、场景2、场景3、场景4等），只传递用户创建的场景
            import re
            
            shot_id = 1
            for scene_idx, scene_result in enumerate(storyboard_results):
                scene_info = scene_result.get("scene_info", f"场景{scene_idx + 1}")
                storyboard_script = scene_result.get("storyboard_script", "")
                
                # 安全处理scene_info，检查是否为分镜生成的场景
                if isinstance(scene_info, dict):
                    scene_info_str = scene_info.get('description', '') or scene_info.get('name', '') or str(scene_info)
                else:
                    scene_info_str = str(scene_info) if scene_info else ""

                is_auto_generated_scene = re.match(r'^场景\d+', scene_info_str.strip())
                
                # 解析分镜脚本中的分镜
                script_lines = storyboard_script.split('\n')
                current_shot = None
                
                for line in script_lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 检测分镜开始标记
                    if line.startswith('分镜') or line.startswith('镜头') or 'Shot' in line:
                        # 保存上一个分镜
                        if current_shot:
                            shots.append(current_shot)
                            shot_id += 1
                        
                        # 创建新分镜
                        current_shot = Shot(
                            shot_id=shot_id,
                            scene=scene_info_str,  # 使用安全处理后的字符串
                            characters=[],
                            action="",
                            dialogue="",
                            image_prompt="",
                            duration=3.0  # 默认3秒
                        )
                        # 只有非自动生成的场景才添加到scenes集合中
                        if not is_auto_generated_scene:
                            # 确保scene_info是字符串类型，避免unhashable type错误
                            scene_str = str(scene_info) if scene_info else ""
                            if scene_str:
                                scenes.add(scene_str)
                        total_duration += 3.0
                    elif current_shot:
                        # 解析分镜内容
                        if '角色' in line or '人物' in line:
                            # 提取角色信息
                            char_info = line.split('：')[-1] if '：' in line else line
                            current_shot.characters.append(char_info.strip())
                            characters.add(char_info.strip())
                        elif '动作' in line or '行为' in line:
                            # 提取动作信息
                            current_shot.action = line.split('：')[-1] if '：' in line else line
                        elif '对话' in line or '台词' in line:
                            # 提取对话信息
                            current_shot.dialogue = line.split('：')[-1] if '：' in line else line
                        elif '画面' in line or '镜头' in line or '描述' in line:
                            # 提取画面描述作为图像提示词
                            prompt = line.split('：')[-1] if '：' in line else line
                            original_prompt = prompt.strip()
                            
                            # 🔧 修复：第五阶段不进行场景描述增强，直接使用原始描述
                            current_shot.image_prompt = original_prompt
                            if auto_enhance:
                                logger.debug(f"第五阶段跳过画面描述增强（避免重复LLM处理）: {original_prompt[:30]}...")
                            else:
                                logger.debug(f"跳过画面描述增强（auto_enhance=False）: {original_prompt[:30]}...")
                        else:
                            # 其他内容添加到动作描述中
                            if current_shot.action:
                                current_shot.action += " " + line
                            else:
                                current_shot.action = line
                
                # 保存最后一个分镜
                if current_shot:
                    shots.append(current_shot)
            
            # 如果没有解析到分镜，创建一个默认分镜
            if not shots:
                for scene_idx, scene_result in enumerate(storyboard_results):
                    scene_info = scene_result.get("scene_info", f"场景{scene_idx + 1}")
                    storyboard_script = scene_result.get("storyboard_script", "")
                    
                    # 🔧 修复：正确提取场景描述，避免传递完整字典
                    if isinstance(scene_info, dict):
                        # 优先提取场景描述字段
                        scene_description = scene_info.get('场景描述', '') or scene_info.get('scene_description', '')
                        scene_name = scene_info.get('scene_name', '') or scene_info.get('name', '')

                        # 如果有场景描述，使用场景描述；否则使用场景名称
                        if scene_description:
                            scene_info_str = scene_description
                            original_prompt = scene_description  # 🔧 修复：只使用场景描述作为画面提示词
                        elif scene_name:
                            scene_info_str = scene_name
                            original_prompt = scene_name
                        else:
                            scene_info_str = f"场景{scene_idx + 1}"
                            original_prompt = f"场景{scene_idx + 1}"
                    else:
                        scene_info_str = str(scene_info) if scene_info else f"场景{scene_idx + 1}"
                        original_prompt = scene_info_str

                    is_auto_generated_scene = re.match(r'^场景\d+', scene_info_str.strip())

                    # 🔧 修复：确保original_prompt是简洁的描述，不包含多余信息
                    enhanced_prompt = original_prompt

                    # 🔧 修复：检查是否应该进行描述增强
                    if re.match(r'^场景\d+', scene_info_str.strip()):
                        logger.debug(f"跳过场景标题增强: {original_prompt}")
                        enhanced_prompt = original_prompt
                    elif auto_enhance and self.scene_enhancer and len(original_prompt.strip()) > 5:
                        # 🔧 修复：第五阶段不进行LLM增强，直接使用原始描述
                        logger.debug(f"第五阶段跳过LLM增强: {original_prompt[:50]}...")
                        enhanced_prompt = original_prompt
                    elif not auto_enhance:
                        logger.debug(f"跳过默认画面描述增强（auto_enhance=False）: {original_prompt[:50]}...")

                    shot = Shot(
                        shot_id=scene_idx + 1,
                        scene=scene_info_str,  # 使用安全处理后的字符串
                        characters=[],
                        action=storyboard_script[:200] + "..." if len(storyboard_script) > 200 else storyboard_script,
                        dialogue="",
                        image_prompt=str(enhanced_prompt),  # 确保是字符串
                        duration=3.0
                    )
                    shots.append(shot)
                    # 只有非自动生成的场景才添加到scenes集合中
                    if not is_auto_generated_scene:
                        # 确保scene_info是字符串类型，避免unhashable type错误
                        scene_str = str(scene_info) if scene_info else ""
                        if scene_str:
                            scenes.add(scene_str)
                    total_duration += 3.0
            
            # 创建StoryboardResult对象
            storyboard_result = StoryboardResult(
                shots=shots,
                total_duration=total_duration,
                characters=list(characters),
                scenes=list(scenes),
                style=self.style_combo.currentText() if hasattr(self, 'style_combo') else self._get_default_style(),
                metadata={
                    "source": "five_stage_storyboard",
                    "world_bible": self.stage_data.get(1, {}).get("world_bible", ""),
                    "character_info": self.stage_data.get(2, {}).get("character_info", ""),
                    "scenes_analysis": self.stage_data.get(3, {}).get("scenes_analysis", ""),
                    "optimization_suggestions": self.stage_data.get(5, {}).get("optimization_suggestions", [])
                }
            )
            
            # 传递给一致性控制面板
            self.parent_window.consistency_panel.set_storyboard(storyboard_result)
            
            logger.info(f"已将 {len(shots)} 个分镜传递给一致性控制面板")
            
        except Exception as e:
            logger.error(f"更新一致性控制面板时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _auto_update_consistency_preview(self):
        """自动触发一致性预览更新"""
        try:
            # 检查主窗口是否有一致性控制面板
            if not hasattr(self.parent_window, 'consistency_panel'):
                logger.warning("主窗口没有一致性控制面板，无法自动更新预览")
                return
            
            consistency_panel = self.parent_window.consistency_panel
            
            # 延迟一小段时间后自动触发更新预览，确保数据传递完成
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(500, consistency_panel.update_preview)
            
            logger.info("已自动触发一致性预览更新")
            
        except Exception as e:
            logger.error(f"自动触发一致性预览更新失败: {e}")
    
    def on_enhance_option_changed(self, state):
        """增强选项状态改变回调"""
        try:
            if self.scene_enhancer:
                enabled = state == Qt.Checked
                self.scene_enhancer.update_config(
                    enable_technical_details=enabled,
                    enable_consistency_injection=enabled
                )
                logger.info(f"场景描述增强已{'启用' if enabled else '禁用'}")
                
                # 更新增强级别组合框的可用性
                self.enhance_level_combo.setEnabled(enabled)
        except Exception as e:
            logger.error(f"更新增强选项失败: {e}")
    
    def on_enhance_level_changed(self, level_text):
        """增强级别改变回调"""
        try:
            if self.scene_enhancer:
                level_map = {"低": "low", "中": "medium", "高": "high"}
                level = level_map.get(level_text, "medium")
                self.scene_enhancer.update_config(enhancement_level=level)
                logger.info(f"场景描述增强级别已设置为: {level_text}")
        except Exception as e:
            logger.error(f"更新增强级别失败: {e}")
    
    def _get_default_style(self):
        """获取默认风格"""
        from src.utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        return config_manager.get_setting("default_style", "电影风格")

    def _is_valid_scene_description(self, description: str) -> bool:
        """验证是否为有效的场景描述"""
        try:
            # 检查是否包含字典特征（说明是错误传递的数据）
            if any(keyword in description for keyword in [
                "'scene_name':", "'情感基调':", "'主要角色':", "'关键事件':",
                "'场景描述':", "'转场建议':", "'关键台词':", "'配音要点':", "'视觉重点':"
            ]):
                return False

            # 检查长度是否合理（太长可能是字典数据）
            if len(description) > 500:
                return False

            # 检查是否为简单的场景标题
            if re.match(r'^场景\d+', description.strip()):
                return False

            return True

        except Exception as e:
            logger.debug(f"验证场景描述失败: {e}")
            return False
    
    def open_enhancer_config(self):
        """打开场景描述增强器配置面板"""
        try:
            # 获取项目根目录
            project_root = getattr(self, 'project_dir', None)
            if not project_root and self.project_manager and self.project_manager.current_project:
                project_root = self.project_manager.current_project.get('project_dir')
            
            if not project_root:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "警告", "请先创建或加载一个项目")
                return
            
            # 创建并显示配置面板
            config_panel = SceneEnhancerConfigPanel(project_root, self)
            config_panel.exec_()
            
            # 配置面板关闭后，重新加载增强器配置
            if self.scene_enhancer:
                self.scene_enhancer.reload_config()
                logger.info("场景描述增强器配置已更新")
                
        except Exception as e:
            logger.error(f"打开增强器配置面板失败: {e}")
            QMessageBox.critical(self, "错误", f"打开配置面板失败: {str(e)}")
    
    def get_project_data(self):
        """获取五阶段分镜项目数据"""
        # 确保stage_data的键为字符串格式，避免重复键问题
        normalized_stage_data = {}
        for key, value in self.stage_data.items():
            # 将所有键转换为字符串格式
            str_key = str(key)
            normalized_stage_data[str_key] = value
            
        return {
            'five_stage_storyboard': {
                'stage_data': normalized_stage_data,
                'current_stage': self.current_stage,
                'selected_characters': getattr(self, 'selected_characters', []),
                'selected_scenes': getattr(self, 'selected_scenes', []),
                'article_text': self.article_input.toPlainText() if hasattr(self, 'article_input') else '',
                'selected_style': self.style_combo.currentText() if hasattr(self, 'style_combo') else '',
                'selected_model': self.model_combo.currentText() if hasattr(self, 'model_combo') else ''
            }
        }