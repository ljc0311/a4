import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from .logger import logger
from .character_detection_config import CharacterDetectionConfig

class CharacterSceneManager:
    """角色场景数据库管理器 - 负责管理项目中的角色和场景一致性数据"""
    
    def __init__(self, project_root: str, service_manager=None):
        self.project_root = project_root
        
        # 统一使用src/character_scene_db目录结构
        # 检测现有的角色数据库路径，优先使用有数据的目录
        possible_db_paths = [
            os.path.join(project_root, 'src', 'character_scene_db'),
            os.path.join(project_root, 'character_scene_db')  # 兼容旧项目
        ]
        
        self.database_dir = None
        for db_path in possible_db_paths:
            characters_file = os.path.join(db_path, 'characters.json')
            if os.path.exists(characters_file):
                # 检查文件是否可读（不管是否有数据）
                try:
                    with open(characters_file, 'r', encoding='utf-8') as f:
                        json.load(f)  # 只要能正常解析JSON就使用这个路径
                        self.database_dir = db_path
                        break
                except:
                    continue
        
        # 如果没有找到可用的数据库，使用统一的默认路径
        if not self.database_dir:
            self.database_dir = os.path.join(project_root, 'src', 'character_scene_db')
        
        os.makedirs(self.database_dir, exist_ok=True)
        
        # 数据库文件路径
        self.characters_file = os.path.join(self.database_dir, 'characters.json')
        self.scenes_file = os.path.join(self.database_dir, 'scenes.json')
        self.consistency_rules_file = os.path.join(self.database_dir, 'consistency_rules.json')
        
        # 服务管理器（用于调用LLM服务）
        self.service_manager = service_manager
        
        # 初始化数据结构
        self._init_database_files()
    
    def _init_database_files(self):
        """初始化数据库文件"""
        # 初始化角色数据库
        if not os.path.exists(self.characters_file):
            default_characters = {
                "characters": {},
                "last_updated": "",
                "version": "1.0"
            }
            self._save_json(self.characters_file, default_characters)
        
        # 初始化场景数据库
        if not os.path.exists(self.scenes_file):
            default_scenes = {
                "scenes": {},
                "scene_categories": {
                    "indoor": ["家庭", "办公室", "教室", "餐厅", "卧室", "客厅", "厨房", "浴室"],
                    "outdoor": ["街道", "公园", "广场", "山林", "海边", "田野", "城市", "乡村"],
                    "special": ["梦境", "回忆", "幻想", "虚拟空间"]
                },
                "last_updated": "",
                "version": "1.0"
            }
            self._save_json(self.scenes_file, default_scenes)
        
        # 初始化一致性规则
        if not os.path.exists(self.consistency_rules_file):
            default_rules = {
                "character_consistency": {
                    "appearance_keywords": ["外貌", "长相", "身材", "发型", "眼睛", "肤色"],
                    "clothing_keywords": ["服装", "衣服", "穿着", "打扮", "装扮"],
                    "personality_keywords": ["性格", "气质", "表情", "神态", "情绪"]
                },
                "scene_consistency": {
                    "environment_keywords": ["环境", "背景", "场所", "地点", "位置"],
                    "lighting_keywords": ["光线", "照明", "明暗", "阴影", "光影"],
                    "atmosphere_keywords": ["氛围", "气氛", "情调", "感觉", "风格"]
                },
                "last_updated": "",
                "version": "1.0"
            }
            self._save_json(self.consistency_rules_file, default_rules)
    
    def _save_json(self, file_path: str, data: Dict):
        """保存JSON数据到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存JSON文件失败 {file_path}: {e}")
    
    def _load_json(self, file_path: str) -> Dict:
        """从文件加载JSON数据"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载JSON文件失败 {file_path}: {e}")
        return {}
    
    def extract_characters_from_text(self, text: str, world_bible: str = "") -> List[Dict[str, Any]]:
        """从文本中提取角色信息

        Args:
            text: 输入文本
            world_bible: 世界观圣经内容，用于提供时代背景信息

        Returns:
            List[Dict]: 提取的角色信息列表
        """
        try:
            # 使用大模型进行智能角色提取，结合世界观圣经
            return self._extract_characters_with_llm(text, world_bible)
        except Exception as e:
            logger.error(f"大模型角色提取失败，使用备用方法: {e}")
            # 备用方案：使用基于LLM的简化版本
            return self._extract_characters_fallback(text)
    
    def _extract_characters_with_llm(self, text: str, world_bible: str = "") -> List[Dict[str, Any]]:
        """使用大模型提取角色信息，结合世界观圣经的时代背景"""

        # 智能检测文化背景
        cultural_info = self._detect_cultural_background(text, world_bible)

        # 构建包含世界观信息的提示词
        world_bible_context = ""
        if world_bible:
            world_bible_context = f"""
📖 **世界观圣经参考**：
{world_bible[:500]}...

请根据世界观圣经中的时代背景、文化设定来分析角色特征。
"""

        # 添加文化背景指导
        cultural_context = f"""
🌍 **文化背景指导**：
根据文本分析，角色可能属于{cultural_info['culture']}文化背景。
请在描述角色时考虑相应的文化特征，但不要硬编码特定国家。
如果文本中没有明确的文化指示，请使用通用的人类特征描述。
"""

        prompt = f"""
请分析以下文本，提取其中的所有角色信息。重点关注角色的外貌特征和服装，生成专门用于AI文生图的一致性描述。

{world_bible_context}

{cultural_context}

🎯 **重要要求**：
1. **时代背景**：根据世界观圣经确定角色所处的历史时期，避免时代错误（如古代人穿现代服装）
2. **国家人种**：根据文本内容和世界观圣经智能判断角色的国家和人种特征，不要硬编码特定国家，如果无法确定则使用"人类"
3. **外貌特征**：详细描述符合时代背景和地域特色的面部特征、体型、发型等
4. **服装颜色**：每件服装只使用一种具体颜色，如"深蓝色战袍"、"黑色长裤"、"红色连衣裙"，避免"红色或蓝色"等模糊描述
5. **一致性提示词**：生成包含时代背景和地域特色的AI绘画提示词

⚠️ **避免内容**：
- 避免时代错误（古代人不能有现代特征）
- 避免硬编码特定国家（除非文本明确指出）
- 避免模糊的服装颜色描述（如"红色或蓝色"、"多种颜色"）
- 减少或不要眼神表情描述
- 避免抽象的性格描述
- 不要过多的行为习惯描述

请以JSON格式返回，格式如下：
{{
  "characters": [
    {{
      "name": "角色名称",
      "description": "角色的基本描述",
      "historical_period": "历史时期（如：战国时期、唐朝、现代等）",
      "appearance": {{
        "nationality": "国家人种（根据文本内容智能判断，如：中国人、英国人、日本人等，无法确定时使用'人类'）",
        "gender": "性别",
        "age_range": "年龄范围",
        "height": "身高描述",
        "hair": "符合时代的发型和发色",
        "eyes": "眼睛特征（颜色、形状）",
        "skin": "肤色（具体描述）",
        "build": "体型（具体描述）",
        "facial_features": "面部特征（鼻子、嘴唇、脸型等）"
      }},
      "clothing": {{
        "period_style": "时代服装风格（如：战国军装、唐朝官服等）",
        "style": "具体服装款式",
        "primary_color": "主要颜色（只选择一种具体颜色，如：深蓝色、暗红色、墨绿色等）",
        "material": "符合时代的服装材质",
        "accessories": ["时代配饰1", "时代配饰2"],
        "details": "服装细节描述"
      }},
      "consistency_prompt": "专门用于AI文生图的角色一致性提示词，包含：历史时期+国家人种+外貌特征+具体颜色的服装（如深蓝色战袍），控制在60字以内"
    }}
  ]
}}

文本内容：
{text}

请返回JSON格式的角色信息：
"""
        
        # 这里需要调用LLM服务
        # 由于当前上下文中没有直接的LLM服务实例，我们先返回一个占位符
        # 实际实现时需要注入LLM服务依赖
        logger.info("正在使用大模型提取角色信息...")
        
        # 使用线程池执行异步调用，避免阻塞GUI主线程
        if self.service_manager:
            try:
                from src.core.service_manager import ServiceType
                llm_service = self.service_manager.get_service(ServiceType.LLM)
                if llm_service:
                    try:
                        # 使用线程池执行异步操作，避免在主线程中使用asyncio.run()
                        result = self._execute_llm_with_timeout(
                            llm_service, prompt, max_tokens=3000, temperature=0.3, timeout=60
                        )

                        if result and result.success:
                            return self._parse_llm_character_response(result.data['content'])
                        else:
                            logger.warning("LLM调用未返回成功结果")
                            return []
                    except Exception as e:
                        logger.error(f"LLM调用失败: {e}")
                        raise
            except Exception as e:
                logger.error(f"调用LLM服务失败: {e}")

        # 如果LLM服务不可用，返回空列表
        logger.warning("LLM服务不可用，跳过智能角色提取")
        return []

    def _execute_llm_with_timeout(self, llm_service, prompt: str, max_tokens: int = 3000,
                                 temperature: float = 0.3, timeout: int = 60):
        """在线程池中执行LLM调用，避免阻塞GUI主线程"""
        import concurrent.futures
        import threading

        def run_async_in_thread():
            """在新线程中运行异步操作"""
            try:
                # 创建新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # 执行异步操作
                    result = loop.run_until_complete(
                        llm_service.execute(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
                    )
                    return result
                finally:
                    # 清理事件循环
                    try:
                        pending = asyncio.all_tasks(loop)
                        for task in pending:
                            task.cancel()
                        if pending:
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    except Exception as cleanup_error:
                        logger.warning(f"清理事件循环时出错: {cleanup_error}")
                    finally:
                        loop.close()
            except Exception as e:
                logger.error(f"线程中执行LLM调用失败: {e}")
                return None

        # 使用线程池执行，设置超时
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_async_in_thread)
            try:
                result = future.result(timeout=timeout)
                return result
            except concurrent.futures.TimeoutError:
                logger.error(f"LLM调用超时 ({timeout}秒)")
                return None
            except Exception as e:
                logger.error(f"LLM调用执行失败: {e}")
                return None

    def _extract_characters_fallback(self, text: str) -> List[Dict[str, Any]]:
        """备用角色提取方法（基于LLM的简化版本）"""
        try:
            # 智能检测文化背景
            cultural_info = self._detect_cultural_background(text)
            default_nationality = cultural_info.get('nationality', '人类')

            # 使用简化的LLM提示词进行角色提取
            simple_prompt = f"""
请简单分析以下文本，提取主要角色名称。只需要返回角色名称列表，每行一个角色名。

文本内容：
{text[:1000]}

角色名称：
"""

            # 如果有LLM服务，使用简化提示词
            if self.service_manager:
                try:
                    from src.core.service_manager import ServiceType
                    llm_service = self.service_manager.get_service(ServiceType.LLM)
                    if llm_service:
                        result = self._execute_llm_with_timeout(
                            llm_service, simple_prompt, max_tokens=500, temperature=0.1, timeout=30
                        )

                        if result and result.success:
                            # 解析简单的角色名称列表
                            character_names = []
                            lines = result.data['content'].strip().split('\n')
                            for line in lines:
                                line = line.strip()
                                if line and not line.startswith('角色') and len(line) < 20:
                                    character_names.append(line)

                            # 为每个角色创建基础信息
                            characters = []
                            for char_name in character_names[:5]:  # 限制最多5个角色
                                # 🔧 修复：生成更详细的角色一致性描述
                                # 根据角色名称推测年龄和性别
                                age_gender_info = self._infer_age_gender_from_name(char_name)

                                character_info = {
                                    "name": char_name,
                                    "description": f"从文本中识别的{char_name}角色",
                                    "appearance": f"国家人种：{default_nationality}，性别：{age_gender_info['gender']}，年龄：{age_gender_info['age']}岁，发型：{age_gender_info['hair']}，肤色：白皙，体型：{age_gender_info['build']}，面部特征：{age_gender_info['face']}",
                                    "clothing": f"风格：{age_gender_info['clothing_style']}，颜色：{age_gender_info['clothing_color']}，材质：{age_gender_info['material']}，配饰：{age_gender_info['accessories']}",
                                    "personality": "",
                                    "consistency_prompt": f"{default_nationality}，{age_gender_info['age']}岁{age_gender_info['gender_desc']}，{age_gender_info['build']}，{age_gender_info['face']}，{age_gender_info['hair']}，{age_gender_info['clothing_color']}{age_gender_info['clothing_style']}，{age_gender_info['accessories']}",
                                    "extracted_from_text": True,
                                    "manual_edited": False
                                }
                                characters.append(character_info)

                            return characters
                except Exception as e:
                    logger.warning(f"简化LLM角色提取失败: {e}")

            # 🔧 修复：最终备用方案也使用详细的角色描述
            age_gender_info = self._infer_age_gender_from_name("主要角色")
            return [{
                "name": "主要角色",
                "description": "从文本中识别的主要角色",
                "appearance": f"国家人种：{default_nationality}，性别：{age_gender_info['gender']}，年龄：{age_gender_info['age']}岁，发型：{age_gender_info['hair']}，肤色：白皙，体型：{age_gender_info['build']}，面部特征：{age_gender_info['face']}",
                "clothing": f"风格：{age_gender_info['clothing_style']}，颜色：{age_gender_info['clothing_color']}，材质：{age_gender_info['material']}，配饰：{age_gender_info['accessories']}",
                "personality": "",
                "consistency_prompt": f"{default_nationality}，{age_gender_info['age']}岁{age_gender_info['gender_desc']}，{age_gender_info['build']}，{age_gender_info['face']}，{age_gender_info['hair']}，{age_gender_info['clothing_color']}{age_gender_info['clothing_style']}，{age_gender_info['accessories']}",
                "extracted_from_text": True,
                "manual_edited": False
            }]

        except Exception as e:
            logger.error(f"备用角色提取失败: {e}")
            return []
    
    def extract_scenes_from_text(self, text: str, world_bible: str = "") -> List[Dict[str, Any]]:
        """从文本中提取场景信息（已禁用）

        Args:
            text: 输入文本
            world_bible: 世界观圣经内容，用于提供时代背景信息

        Returns:
            List[Dict]: 提取的场景信息列表
        """
        try:
            # 使用大模型进行智能场景提取，结合世界观圣经
            return self._extract_scenes_with_llm(text, world_bible)
        except Exception as e:
            logger.error(f"大模型场景提取失败，使用备用方法: {e}")
            # 备用方案：使用基于LLM的简化版本
            return self._extract_scenes_fallback(text)
    
    def _extract_scenes_with_llm(self, text: str, world_bible: str = "") -> List[Dict[str, Any]]:
        """使用大模型提取场景信息，结合世界观圣经的时代背景"""

        # 构建包含世界观信息的提示词
        world_bible_context = ""
        if world_bible:
            world_bible_context = f"""
📖 **世界观圣经参考**：
{world_bible[:500]}...

请根据世界观圣经中的时代背景、地理环境、文化设定来分析场景特征。
"""

        prompt = f"""
请分析以下文本，提取其中的所有场景信息。重点关注场景的基本信息，不需要详细的增强描述。

{world_bible_context}

🎯 **提取要求**：
1. **基本信息**：场景名称、类型、简单描述
2. **时代背景**：根据世界观圣经确定场景所处的历史时期
3. **简单特征**：基本的环境、光线、氛围信息
4. **一致性提示词**：生成简单的AI绘画提示词

请以JSON格式返回，格式如下：
{{
  "scenes": [
    {{
      "name": "场景名称",
      "category": "场景类型（indoor/outdoor/special）",
      "description": "场景的基本描述",
      "environment": "基本环境描述",
      "lighting": "基本光线描述",
      "atmosphere": "基本氛围描述",
      "consistency_prompt": "简单的AI绘画一致性提示词，控制在50字以内"
    }}
  ]
}}

文本内容：
{text}

请返回JSON格式的场景信息：
"""

        # 调用LLM服务
        logger.info("正在使用大模型提取场景信息...")

        # 使用线程池执行异步调用，避免阻塞GUI主线程
        if self.service_manager:
            try:
                from src.core.service_manager import ServiceType
                llm_service = self.service_manager.get_service(ServiceType.LLM)
                if llm_service:
                    try:
                        # 使用线程池执行异步操作，避免在主线程中使用asyncio.run()
                        result = self._execute_llm_with_timeout(
                            llm_service, prompt, max_tokens=2000, temperature=0.3, timeout=60
                        )

                        if result and result.success:
                            return self._parse_llm_scene_response(result.data['content'])
                        else:
                            logger.warning("LLM调用未返回成功结果")
                            return []
                    except Exception as e:
                        logger.error(f"LLM调用失败: {e}")
                        raise
            except Exception as e:
                logger.error(f"调用LLM服务失败: {e}")

        # 如果LLM服务不可用，返回空列表
        logger.warning("LLM服务不可用，跳过智能场景提取")
        return []


    
    def _extract_scenes_fallback(self, text: str) -> List[Dict[str, Any]]:
        """备用场景提取方法（基于LLM的简化版本）"""
        try:
            # 使用简化的LLM提示词进行场景提取
            simple_prompt = f"""
请简单分析以下文本，提取主要场景地点。只需要返回场景名称列表，每行一个场景。

文本内容：
{text[:1000]}

场景地点：
"""

            # 如果有LLM服务，使用简化提示词
            if self.service_manager:
                try:
                    from src.core.service_manager import ServiceType
                    llm_service = self.service_manager.get_service(ServiceType.LLM)
                    if llm_service:
                        result = self._execute_llm_with_timeout(
                            llm_service, simple_prompt, max_tokens=500, temperature=0.1, timeout=30
                        )

                        if result and result.success:
                            # 解析简单的场景名称列表
                            scene_names = []
                            lines = result.data['content'].strip().split('\n')
                            for line in lines:
                                line = line.strip()
                                if line and not line.startswith('场景') and len(line) < 30:
                                    scene_names.append(line)

                            # 为每个场景创建基础信息
                            scenes = []
                            for scene_name in scene_names[:5]:  # 限制最多5个场景
                                scene_info = {
                                    "name": scene_name,
                                    "category": "indoor" if any(word in scene_name for word in ['室内', '房间', '屋', '厅', '院']) else "outdoor",
                                    "description": f"从文本中识别的{scene_name}场景",
                                    "environment": f"地点：{scene_name}",
                                    "lighting": "自然光照",
                                    "atmosphere": "基本氛围",
                                    "consistency_prompt": f"{scene_name}场景",
                                    "extracted_from_text": True,
                                    "manual_edited": False
                                }
                                scenes.append(scene_info)

                            return scenes
                except Exception as e:
                    logger.warning(f"简化LLM场景提取失败: {e}")

            # 最终备用方案：返回通用场景
            return [{
                "name": "主要场景",
                "category": "indoor",
                "description": "从文本中识别的主要场景",
                "environment": "室内场景",
                "lighting": "自然光照",
                "atmosphere": "基本氛围",
                "consistency_prompt": "室内场景",
                "extracted_from_text": True,
                "manual_edited": False
            }]

        except Exception as e:
            logger.error(f"备用场景提取失败: {e}")
            return []
    
    def _parse_llm_character_response(self, llm_response: str) -> List[Dict[str, Any]]:
        """解析LLM返回的角色信息"""
        try:
            # 尝试从响应中提取JSON
            import re
            json_match = re.search(r'\[.*\]', llm_response, re.DOTALL)
            if json_match:
                characters_data = json.loads(json_match.group())
                
                # 验证和标准化数据格式
                validated_characters = []
                for char in characters_data:
                    if isinstance(char, dict) and 'name' in char:
                        # 🔧 修复：处理外貌信息，确保国家人种为"中国人"
                        appearance = char.get('appearance', {})
                        if isinstance(appearance, dict):
                            # 获取国家人种，如果是"人类"或"未知"，则改为"中国人"
                            nationality = appearance.get('nationality', '中国人')
                            if nationality in ['人类', '未知', 'human', '']:
                                nationality = '中国人'

                            appearance_str = f"国家人种：{nationality}，性别：{appearance.get('gender', '未知')}，年龄：{appearance.get('age_range', '未知')}，发型：{appearance.get('hair', '未知')}，肤色：{appearance.get('skin', '未知')}，体型：{appearance.get('build', '未知')}"
                            if appearance.get('facial_features'):
                                appearance_str += f"，面部特征：{appearance.get('facial_features')}"
                        else:
                            # 如果appearance不是字典，直接处理字符串
                            appearance_str = str(appearance)
                            # 替换"人类"为"中国人"
                            appearance_str = appearance_str.replace('国家人种：人类', '国家人种：中国人')

                        # 处理服装信息
                        clothing = char.get('clothing', {})
                        if isinstance(clothing, dict):
                            # 优先使用primary_color，如果没有则使用colors数组的第一个
                            primary_color = clothing.get('primary_color', '')
                            if not primary_color:
                                colors = clothing.get('colors', [])
                                if colors and isinstance(colors, list) and len(colors) > 0:
                                    primary_color = colors[0]
                                else:
                                    primary_color = '未知'

                            clothing_str = f"风格：{clothing.get('style', '未知')}，颜色：{primary_color}，材质：{clothing.get('material', '未知')}，配饰：{', '.join(clothing.get('accessories', []))}"
                            if clothing.get('details'):
                                clothing_str += f"，细节：{clothing.get('details')}"
                        else:
                            clothing_str = str(clothing)

                        # 🔧 修复：处理一致性描述，确保包含"中国人"和详细信息
                        consistency_prompt = char.get('consistency_prompt', '')
                        if consistency_prompt:
                            # 替换"人类"为"中国人"
                            consistency_prompt = consistency_prompt.replace('人类', '中国人')
                            # 如果一致性描述过于简单，尝试增强
                            if len(consistency_prompt) < 20:
                                # 从外貌和服装信息中提取关键信息来增强
                                age_info = appearance.get('age_range', '成年') if isinstance(appearance, dict) else '成年'
                                gender_info = appearance.get('gender', '男性') if isinstance(appearance, dict) else '男性'
                                build_info = appearance.get('build', '匀称') if isinstance(appearance, dict) else '匀称'
                                clothing_style = clothing.get('style', '传统服装') if isinstance(clothing, dict) else '传统服装'
                                clothing_color = clothing.get('primary_color', '深色') if isinstance(clothing, dict) else '深色'

                                consistency_prompt = f"中国人，{age_info}{gender_info}，{build_info}，{clothing_color}{clothing_style}"
                        else:
                            # 如果没有一致性描述，生成一个基础的
                            consistency_prompt = "中国人，成年男性，匀称体型，传统服装"

                        validated_char = {
                            'id': char.get('name', '').replace(' ', '_').lower(),
                            'name': char.get('name', ''),
                            'description': char.get('description', ''),
                            'appearance': appearance_str,
                            'clothing': clothing_str,
                            'personality': char.get('personality', ''),  # 保留但不强调
                            'consistency_prompt': consistency_prompt,
                            'created_at': self._get_current_time(),
                            'updated_at': self._get_current_time()
                        }
                        validated_characters.append(validated_char)
                
                logger.info(f"成功解析{len(validated_characters)}个角色")
                return validated_characters
            else:
                logger.warning("LLM响应中未找到有效的JSON格式")
                return []
        except Exception as e:
            logger.error(f"解析LLM角色响应失败: {e}")
            return []
    
    def _parse_llm_scene_response(self, llm_response: str) -> List[Dict[str, Any]]:
        """解析LLM返回的场景信息"""
        try:
            # 尝试从响应中提取JSON
            import re
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group())
                scenes_data = response_data.get('scenes', [])

                # 验证和标准化数据格式
                validated_scenes = []
                for scene in scenes_data:
                    if isinstance(scene, dict) and 'name' in scene:
                        validated_scene = {
                            'id': scene.get('name', '').replace(' ', '_').lower(),
                            'name': scene.get('name', ''),
                            'description': scene.get('description', ''),
                            'environment': scene.get('environment', ''),
                            'lighting': scene.get('lighting', ''),
                            'atmosphere': scene.get('atmosphere', ''),
                            'consistency_prompt': scene.get('consistency_prompt', ''),
                            'created_at': self._get_current_time(),
                            'updated_at': self._get_current_time()
                        }
                        validated_scenes.append(validated_scene)

                logger.info(f"成功解析{len(validated_scenes)}个场景")
                return validated_scenes
            else:
                logger.warning("LLM响应中未找到有效的JSON格式")
                return []
        except Exception as e:
            logger.error(f"解析LLM场景响应失败: {e}")
            return []
    
    def save_character(self, character_id: str, character_data: Dict[str, Any]):
        """保存角色信息
        
        Args:
            character_id: 角色ID
            character_data: 角色数据
        """
        try:
            characters_db = self._load_json(self.characters_file)
            characters_db["characters"][character_id] = character_data
            characters_db["last_updated"] = self._get_current_time()
            self._save_json(self.characters_file, characters_db)
            logger.info(f"角色信息已保存: {character_id}")
        except Exception as e:
            logger.error(f"保存角色信息失败: {e}")
    
    def save_scene(self, scene_id: str, scene_data: Dict[str, Any]):
        """保存场景信息

        Args:
            scene_id: 场景ID
            scene_data: 场景数据
        """
        try:
            # 🔧 修复：只过滤掉真正无用的场景数据（包含字典字符串的ID）
            scene_name = scene_data.get('name', '')

            # 检查是否是无用的自动生成场景（只过滤包含字典字符串的ID）
            if (scene_id.startswith('镜头场景_') and '{' in scene_id):
                logger.warning(f"跳过保存无用的自动生成场景: {scene_id}")
                return

            scenes_db = self._load_json(self.scenes_file)
            scenes_db["scenes"][scene_id] = scene_data
            scenes_db["last_updated"] = self._get_current_time()
            self._save_json(self.scenes_file, scenes_db)
            logger.info(f"场景信息已保存: {scene_id}")
        except Exception as e:
            logger.error(f"保存场景信息失败: {e}")
    
    def get_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        """获取角色信息
        
        Args:
            character_id: 角色ID
            
        Returns:
            Optional[Dict]: 角色数据
        """
        characters_db = self._load_json(self.characters_file)
        return characters_db.get("characters", {}).get(character_id)
    
    def get_scene(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """获取场景信息
        
        Args:
            scene_id: 场景ID
            
        Returns:
            Optional[Dict]: 场景数据
        """
        scenes_db = self._load_json(self.scenes_file)
        return scenes_db.get("scenes", {}).get(scene_id)
    
    def get_all_characters(self) -> Dict[str, Any]:
        """获取所有角色信息"""
        characters_db = self._load_json(self.characters_file)
        return characters_db.get("characters", {})
    
    def get_all_scenes(self) -> Dict[str, Any]:
        """获取所有场景信息，过滤掉分镜生成的临时场景"""
        scenes_db = self._load_json(self.scenes_file)
        all_scenes = scenes_db.get("scenes", {})

        # 过滤掉分镜生成的临时场景
        filtered_scenes = {}
        for scene_id, scene_data in all_scenes.items():
            # 排除包含字典字符串的无用场景
            if (scene_id.startswith('镜头场景_') and '{' in scene_id):
                continue

            filtered_scenes[scene_id] = scene_data

        return filtered_scenes

    def clean_auto_generated_scenes(self) -> int:
        """清理自动生成的临时场景数据

        Returns:
            int: 清理的场景数量
        """
        scenes_db = self._load_json(self.scenes_file)
        all_scenes = scenes_db.get("scenes", {})

        # 找出需要清理的场景
        scenes_to_remove = []
        for scene_id, scene_data in all_scenes.items():
            scene_name = scene_data.get('name', '')

            # 标记需要删除的场景（只删除包含字典字符串的无用场景）
            if (scene_id.startswith('镜头场景_') and '{' in scene_id):
                scenes_to_remove.append(scene_id)

        # 删除标记的场景
        for scene_id in scenes_to_remove:
            del all_scenes[scene_id]

        # 保存更新后的数据
        scenes_db["scenes"] = all_scenes
        scenes_db["last_updated"] = self._get_current_time()
        self._save_json(self.scenes_file, scenes_db)

        logger.info(f"清理了 {len(scenes_to_remove)} 个自动生成的临时场景")
        return len(scenes_to_remove)
    
    def delete_character(self, character_id: str):
        """删除角色信息"""
        try:
            characters_db = self._load_json(self.characters_file)
            if character_id in characters_db.get("characters", {}):
                del characters_db["characters"][character_id]
                characters_db["last_updated"] = self._get_current_time()
                self._save_json(self.characters_file, characters_db)
                logger.info(f"角色信息已删除: {character_id}")
        except Exception as e:
            logger.error(f"删除角色信息失败: {e}")
    
    def delete_scene(self, scene_id: str):
        """删除场景信息"""
        try:
            scenes_db = self._load_json(self.scenes_file)
            if scene_id in scenes_db.get("scenes", {}):
                del scenes_db["scenes"][scene_id]
                scenes_db["last_updated"] = self._get_current_time()
                self._save_json(self.scenes_file, scenes_db)
                logger.info(f"场景信息已删除: {scene_id}")
        except Exception as e:
            logger.error(f"删除场景信息失败: {e}")
    
    def generate_consistency_prompt(self, character_ids: Optional[List[str]] = None, scene_ids: Optional[List[str]] = None) -> str:
        """生成一致性提示词
        
        Args:
            character_ids: 要包含的角色ID列表
            scene_ids: 要包含的场景ID列表
            
        Returns:
            str: 生成的一致性提示词
        """
        prompt_parts = []
        
        # 添加角色一致性提示
        if character_ids:
            characters = self.get_all_characters()
            for char_id in character_ids:
                if char_id in characters:
                    char_data = characters[char_id]
                    if char_data.get("consistency_prompt"):
                        prompt_parts.append(f"角色{char_data['name']}: {char_data['consistency_prompt']}")
        
        # 添加场景一致性提示
        if scene_ids:
            scenes = self.get_all_scenes()
            for scene_id in scene_ids:
                if scene_id in scenes:
                    scene_data = scenes[scene_id]
                    if scene_data.get("consistency_prompt"):
                        prompt_parts.append(f"场景{scene_data['name']}: {scene_data['consistency_prompt']}")
        
        return "; ".join(prompt_parts)

    def _detect_cultural_background(self, text: str, world_bible: str = "") -> Dict[str, Any]:
        """智能检测文本的文化背景信息

        Args:
            text: 输入文本
            world_bible: 世界观圣经内容

        Returns:
            Dict: 包含国家、地区、时代等信息
        """
        try:
            # 文化背景关键词映射
            cultural_indicators = {
                "中国": {
                    "keywords": ["中国", "华夏", "汉族", "唐朝", "宋朝", "明朝", "清朝", "战国", "春秋", "秦朝", "汉朝", "元朝", "民国", "长安", "北京", "南京", "洛阳", "开封", "杭州", "成都", "西安", "邯郸"],
                    "names": ["李", "王", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴", "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗"],
                    "nationality": "中国人",
                    "ethnicity": "东亚人"
                },
                "日本": {
                    "keywords": ["日本", "东京", "京都", "大阪", "江户", "平安", "镰仓", "室町", "战国", "明治", "大正", "昭和", "和服", "武士", "忍者", "天皇", "幕府"],
                    "names": ["田中", "佐藤", "铃木", "高桥", "渡边", "伊藤", "山本", "中村", "小林", "加藤", "吉田", "山田", "佐佐木", "山口", "松本"],
                    "nationality": "日本人",
                    "ethnicity": "东亚人"
                },
                "英国": {
                    "keywords": ["英国", "英格兰", "苏格兰", "威尔士", "伦敦", "曼彻斯特", "利物浦", "爱丁堡", "维多利亚", "都铎", "斯图亚特", "汉诺威", "温莎"],
                    "names": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson", "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez"],
                    "nationality": "英国人",
                    "ethnicity": "欧洲人"
                },
                "美国": {
                    "keywords": ["美国", "纽约", "洛杉矶", "芝加哥", "休斯顿", "费城", "凤凰城", "圣安东尼奥", "圣地亚哥", "达拉斯", "圣何塞", "华盛顿"],
                    "names": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson", "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez"],
                    "nationality": "美国人",
                    "ethnicity": "多元化"
                },
                "法国": {
                    "keywords": ["法国", "巴黎", "马赛", "里昂", "图卢兹", "尼斯", "南特", "斯特拉斯堡", "蒙彼利埃", "波尔多", "里尔"],
                    "names": ["Martin", "Bernard", "Thomas", "Petit", "Robert", "Richard", "Durand", "Dubois", "Moreau", "Laurent", "Simon", "Michel", "Lefebvre", "Leroy", "Roux"],
                    "nationality": "法国人",
                    "ethnicity": "欧洲人"
                }
            }

            # 分析世界观圣经
            combined_text = f"{world_bible} {text}"

            # 计算每种文化的匹配分数
            culture_scores = {}
            for culture, indicators in cultural_indicators.items():
                score = 0

                # 关键词匹配
                for keyword in indicators["keywords"]:
                    if keyword in combined_text:
                        score += 2

                # 人名匹配
                for name in indicators["names"]:
                    if name in combined_text:
                        score += 3

                culture_scores[culture] = score

            # 找到最高分的文化背景
            if culture_scores:
                best_culture = max(culture_scores.keys(), key=lambda x: culture_scores[x])
                if culture_scores[best_culture] > 0:
                    return {
                        "nationality": cultural_indicators[best_culture]["nationality"],
                        "ethnicity": cultural_indicators[best_culture]["ethnicity"],
                        "culture": best_culture,
                        "confidence": min(culture_scores[best_culture] / 10, 1.0)
                    }

            # 🔧 修复：默认返回中国人而不是"人类"
            return {
                "nationality": "中国人",
                "ethnicity": "东亚人",
                "culture": "中国",
                "confidence": 0.0
            }

        except Exception as e:
            logger.error(f"文化背景检测失败: {e}")
            return {
                "nationality": "中国人",
                "ethnicity": "东亚人",
                "culture": "中国",
                "confidence": 0.0
            }

    def get_world_bible_content(self) -> str:
        """获取世界观圣经内容

        Returns:
            str: 世界观圣经内容
        """
        try:
            # 方法1：从项目文件中读取
            if hasattr(self, 'project_root') and self.project_root:
                import os
                import json

                # 尝试从project.json中读取
                project_file = os.path.join(self.project_root, 'project.json')
                if os.path.exists(project_file):
                    try:
                        with open(project_file, 'r', encoding='utf-8') as f:
                            project_data = json.load(f)

                        # 尝试从五阶段分镜数据中获取
                        if 'five_stage_storyboard' in project_data:
                            world_bible = project_data['five_stage_storyboard'].get('world_bible', '')
                            if world_bible:
                                logger.debug("从五阶段分镜数据获取世界观圣经内容")
                                return world_bible

                        # 尝试从根级别获取
                        world_bible = project_data.get('world_bible', '')
                        if world_bible:
                            logger.debug("从项目根级别获取世界观圣经内容")
                            return world_bible

                    except Exception as e:
                        logger.warning(f"读取项目文件失败: {e}")

                # 方法2：从专门的世界观圣经文件中读取
                world_bible_file = os.path.join(self.project_root, 'texts', 'world_bible.json')
                if os.path.exists(world_bible_file):
                    try:
                        with open(world_bible_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            world_bible = data.get('content', '')
                            if world_bible:
                                logger.debug("从世界观圣经文件获取内容")
                                return world_bible
                    except Exception as e:
                        logger.warning(f"读取世界观圣经文件失败: {e}")

            logger.debug("未找到世界观圣经内容")
            return ""

        except Exception as e:
            logger.error(f"获取世界观圣经内容失败: {e}")
            return ""

    def auto_extract_and_save(self, text: str) -> Dict[str, Any]:
        """自动提取并保存角色和场景信息

        Args:
            text: 输入文本

        Returns:
            Dict: 提取结果统计
        """
        try:
            # 清除之前自动提取的角色和场景（替换而不是追加）
            self._clear_auto_extracted_data()

            # 获取世界观圣经内容
            world_bible = self.get_world_bible_content()
            if world_bible:
                logger.info("获取到世界观圣经内容，将用于指导提取")
            else:
                logger.info("未找到世界观圣经内容，使用默认提取方式")

            # 提取角色（结合世界观圣经）
            extracted_characters = self.extract_characters_from_text(text, world_bible)
            character_count = 0
            for char in extracted_characters:
                char_id = f"auto_{char['name']}_{self._get_current_time().replace(':', '_')}"
                self.save_character(char_id, char)
                character_count += 1

            # 提取场景（结合世界观圣经）- 但不进行增强描述
            extracted_scenes = self.extract_scenes_from_text(text, world_bible)
            scene_count = 0
            for scene in extracted_scenes:
                # 使用简单的场景名称
                scene_name = scene.get('name', f'场景{scene_count + 1}')
                # 清理场景名称，移除特殊字符
                clean_scene_name = scene_name.replace(':', '_').replace('/', '_').replace('\\', '_')
                scene_id = f"auto_{clean_scene_name}_{self._get_current_time().replace(':', '_')}"
                self.save_scene(scene_id, scene)
                scene_count += 1

            result = {
                "success": True,
                "characters_extracted": character_count,
                "scenes_extracted": scene_count,
                "message": f"成功提取 {character_count} 个角色和 {scene_count} 个场景"
            }

            logger.info(f"自动提取完成: {result['message']}")
            return result

        except Exception as e:
            logger.error(f"自动提取失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "自动提取失败"
            }
    
    def _clear_auto_extracted_data(self):
        """清除之前自动提取的角色和场景数据"""
        try:
            # 清除自动提取的角色（ID以"auto_"开头的）
            characters_db = self._load_json(self.characters_file)
            characters = characters_db.get("characters", {})
            auto_character_ids = [char_id for char_id in characters.keys() if char_id.startswith("auto_")]
            
            for char_id in auto_character_ids:
                del characters[char_id]
                logger.info(f"已清除自动提取的角色: {char_id}")
            
            if auto_character_ids:
                characters_db["last_updated"] = self._get_current_time()
                self._save_json(self.characters_file, characters_db)
            
            # 清除自动提取的场景（ID以"auto_"开头的）
            scenes_db = self._load_json(self.scenes_file)
            scenes = scenes_db.get("scenes", {})
            auto_scene_ids = [scene_id for scene_id in scenes.keys() if scene_id.startswith("auto_")]
            
            for scene_id in auto_scene_ids:
                del scenes[scene_id]
                logger.info(f"已清除自动提取的场景: {scene_id}")
            
            if auto_scene_ids:
                scenes_db["last_updated"] = self._get_current_time()
                self._save_json(self.scenes_file, scenes_db)
            
            # 🔧 修复：同时清除项目数据中的selected_characters和selected_scenes列表中的相关ID
            self._clear_project_selections(auto_character_ids, auto_scene_ids)

            if auto_character_ids or auto_scene_ids:
                logger.info(f"已清除 {len(auto_character_ids)} 个自动提取的角色和 {len(auto_scene_ids)} 个自动提取的场景")

        except Exception as e:
            logger.error(f"清除自动提取数据失败: {e}")

    def _clear_project_selections(self, auto_character_ids: List[str], auto_scene_ids: List[str]):
        """清除项目数据中的selected_characters和selected_scenes列表中的自动提取ID"""
        try:
            if not auto_character_ids and not auto_scene_ids:
                return

            # 读取项目文件
            project_file = os.path.join(self.project_root, 'project.json')
            if not os.path.exists(project_file):
                logger.warning("项目文件不存在，跳过清除项目选择")
                return

            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 检查是否有五阶段分镜数据
            if 'five_stage_storyboard' not in project_data:
                logger.debug("项目中没有五阶段分镜数据，跳过清除项目选择")
                return

            five_stage_data = project_data['five_stage_storyboard']
            updated = False

            # 🔧 修复：清除selected_characters中的所有自动提取角色ID（不仅仅是当前批次）
            if 'selected_characters' in five_stage_data:
                original_count = len(five_stage_data['selected_characters'])
                five_stage_data['selected_characters'] = [
                    char_id for char_id in five_stage_data['selected_characters']
                    if not char_id.startswith('auto_')
                ]
                removed_chars = original_count - len(five_stage_data['selected_characters'])
                if removed_chars > 0:
                    logger.info(f"已从项目选择中清除 {removed_chars} 个自动提取的角色ID")
                    updated = True

            # 🔧 修复：清除selected_scenes中的所有自动提取场景ID（不仅仅是当前批次）
            if 'selected_scenes' in five_stage_data:
                original_count = len(five_stage_data['selected_scenes'])
                five_stage_data['selected_scenes'] = [
                    scene_id for scene_id in five_stage_data['selected_scenes']
                    if not scene_id.startswith('auto_')
                ]
                removed_scenes = original_count - len(five_stage_data['selected_scenes'])
                if removed_scenes > 0:
                    logger.info(f"已从项目选择中清除 {removed_scenes} 个自动提取的场景ID")
                    updated = True

            # 如果有更新，保存项目文件
            if updated:
                with open(project_file, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, ensure_ascii=False, indent=2)
                logger.info("项目选择数据已更新")

        except Exception as e:
            logger.error(f"清除项目选择数据失败: {e}")

    def _infer_age_gender_from_name(self, char_name: str) -> Dict[str, str]:
        """🔧 新增：根据角色名称推测年龄、性别等信息"""
        try:
            # 性别推测关键词
            male_keywords = ['公子', '少爷', '先生', '君', '王', '将军', '大人', '兄', '父', '爷', '叔', '伯']
            female_keywords = ['小姐', '夫人', '娘', '母', '姐', '妹', '女']

            # 年龄推测关键词
            young_keywords = ['少', '小', '童', '儿', '子']
            middle_keywords = ['中', '成', '母', '父']  # 🔧 修复：添加"母"和"父"到中年关键词
            old_keywords = ['老', '长', '翁', '婆', '爷', '奶']

            # 默认值
            gender = "男"
            gender_desc = "男性"
            age = 25

            # 性别推测
            for keyword in female_keywords:
                if keyword in char_name:
                    gender = "女"
                    gender_desc = "女性"
                    break

            # 年龄推测
            for keyword in young_keywords:
                if keyword in char_name:
                    age = 18
                    break
            for keyword in old_keywords:
                if keyword in char_name:
                    age = 55
                    break
            for keyword in middle_keywords:
                if keyword in char_name:
                    age = 35
                    break

            # 根据性别和年龄生成详细信息
            if gender == "女":
                if age <= 20:
                    build = "娇小玲珑"
                    face = "圆脸清秀"
                    hair = "黑色长发束成马尾"
                    clothing_style = "长裙"
                    clothing_color = "粉色"
                    material = "丝绸"
                    accessories = "发簪装饰"
                elif age <= 40:
                    build = "匀称优雅"
                    face = "瓜子脸端庄"
                    hair = "黑色长发盘成发髻"
                    clothing_style = "长袍"
                    clothing_color = "浅蓝色"
                    material = "锦缎"
                    accessories = "玉镯装饰"
                else:
                    build = "丰满慈祥"
                    face = "圆脸慈眉善目"
                    hair = "花白头发盘成发髻"
                    clothing_style = "宽袖袍"
                    clothing_color = "深紫色"
                    material = "棉麻"
                    accessories = "银簪装饰"
            else:
                if age <= 20:
                    build = "瘦削挺拔"
                    face = "清秀俊朗"
                    hair = "黑色短发整齐"
                    clothing_style = "长袍"
                    clothing_color = "青色"
                    material = "麻布"
                    accessories = "腰带装饰"
                elif age <= 40:
                    build = "健壮有力"
                    face = "方脸英武"
                    hair = "黑色短发利落"
                    clothing_style = "战袍"
                    clothing_color = "深蓝色"
                    material = "皮革"
                    accessories = "佩剑装饰"
                else:
                    build = "魁梧威严"
                    face = "国字脸威严"
                    hair = "花白短发整齐"
                    clothing_style = "宽袖袍"
                    clothing_color = "深灰色"
                    material = "丝绸"
                    accessories = "玉佩装饰"

            return {
                'gender': gender,
                'gender_desc': gender_desc,
                'age': str(age),
                'build': build,
                'face': face,
                'hair': hair,
                'clothing_style': clothing_style,
                'clothing_color': clothing_color,
                'material': material,
                'accessories': accessories
            }

        except Exception as e:
            logger.error(f"推测角色信息失败: {e}")
            # 返回默认值
            return {
                'gender': "男",
                'gender_desc': "男性",
                'age': "25",
                'build': "匀称",
                'face': "普通面容",
                'hair': "黑色短发",
                'clothing_style': "长袍",
                'clothing_color': "深蓝色",
                'material': "棉布",
                'accessories': "腰带装饰"
            }

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def export_database(self, export_path: str) -> bool:
        """导出数据库到指定路径

        Args:
            export_path: 导出路径

        Returns:
            bool: 导出是否成功
        """
        try:
            import shutil
            if self.database_dir and os.path.exists(self.database_dir):
                shutil.copytree(self.database_dir, export_path, dirs_exist_ok=True)
                logger.info(f"数据库已导出到: {export_path}")
                return True
            else:
                logger.error("数据库目录不存在")
                return False
        except Exception as e:
            logger.error(f"导出数据库失败: {e}")
            return False
    
    def auto_match_characters_to_shots(self, storyboard_data: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """自动将角色匹配到相关的分镜中"""
        logger.info("开始自动匹配角色到分镜...")
        
        characters = self.get_all_characters()
        character_shot_mapping = {}
        
        for character_id, character in characters.items():
            character_name = character.get('name', '')
            character_shot_mapping[character_id] = []
            
            # 遍历所有分镜，查找包含该角色的分镜
            for i, shot in enumerate(storyboard_data):
                shot_text = ''
                
                # 收集分镜中的所有文本信息
                if 'description' in shot:
                    shot_text += shot['description'] + ' '
                if 'dialogue' in shot:
                    shot_text += shot['dialogue'] + ' '
                if 'action' in shot:
                    shot_text += shot['action'] + ' '
                if 'scene_description' in shot:
                    shot_text += shot['scene_description'] + ' '
                
                shot_text = shot_text.lower()
                
                # 检查角色名称是否出现在分镜文本中
                if character_name.lower() in shot_text:
                    character_shot_mapping[character_id].append(f"shot_{i+1}")
                    logger.debug(f"角色 {character_name} 匹配到分镜 {i+1}")
        
        logger.info(f"完成角色到分镜的自动匹配，共匹配{len([shots for shots in character_shot_mapping.values() if shots])}个角色")
        return character_shot_mapping
    
    def get_consistency_rules(self) -> Dict[str, Any]:
        """获取一致性规则"""
        return self._load_json(self.consistency_rules_file)
    
    def save_consistency_rules(self, rules: Dict[str, Any]):
        """保存一致性规则"""
        self._save_json(self.consistency_rules_file, rules)
    
    def update_character_shot_mapping(self, character_id: str, shot_ids: List[str]):
        """更新指定角色的分镜映射"""
        consistency_rules = self.get_consistency_rules()
        if 'character_shot_mapping' not in consistency_rules:
            consistency_rules['character_shot_mapping'] = {}
        
        consistency_rules['character_shot_mapping'][character_id] = shot_ids
        consistency_rules['updated_at'] = self._get_current_time()
        self.save_consistency_rules(consistency_rules)
        
        logger.info(f"已更新角色 {character_id} 的分镜映射: {shot_ids}")
    
    def get_character_shot_mapping(self, character_id: Optional[str] = None) -> Dict[str, List[str]]:
        """获取角色分镜映射"""
        consistency_rules = self.get_consistency_rules()
        character_shot_mapping = consistency_rules.get('character_shot_mapping', {})
        
        if character_id:
            return {character_id: character_shot_mapping.get(character_id, [])}
        return character_shot_mapping
    
    def import_database(self, import_path: str) -> bool:
        """从指定路径导入数据库

        Args:
            import_path: 导入路径

        Returns:
            bool: 导入是否成功
        """
        try:
            import shutil
            if os.path.exists(import_path) and self.database_dir:
                shutil.copytree(import_path, self.database_dir, dirs_exist_ok=True)
                logger.info(f"数据库已从 {import_path} 导入")
                return True
            else:
                if not os.path.exists(import_path):
                    logger.error(f"导入路径不存在: {import_path}")
                else:
                    logger.error("数据库目录未初始化")
                return False
        except Exception as e:
            logger.error(f"导入数据库失败: {e}")
            return False