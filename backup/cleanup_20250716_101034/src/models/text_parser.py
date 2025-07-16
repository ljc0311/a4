"""
文本解析与分镜生成模块
- 支持 Markdown/TXT 纯文本输入
- 调用通义或 Deepseek API 生成分镜与场景描述
- 提取角色与场景元素
"""
import re
from typing import List, Dict
import json
import jieba
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

from .llm_api import LLMApi
from src.utils.logger import logger

# 预设风格模板
STYLE_TEMPLATES = {
    '电影风格': '{scene}，{role}，电影感，戏剧性光影，超写实，4K，胶片颗粒，景深',
    '动漫风格': '{scene}，{role}，动漫风，鲜艳色彩，干净线条，赛璐璐渲染，日本动画',
    '吉卜力风格': '{scene}，{role}，吉卜力风，柔和色彩，奇幻，梦幻，丰富背景',
    '赛博朋克风格': '{scene}，{role}，赛博朋克，霓虹灯，未来都市，雨夜，暗色氛围',
    '水彩插画风格': '{scene}，{role}，水彩画风，柔和笔触，粉彩色，插画，温柔',
    '像素风格': '{scene}，{role}，像素风，8位，复古，低分辨率，游戏风',
    '写实摄影风格': '{scene}，{role}，真实光线，高细节，写实摄影，4K',
}

class TextParser:
    def __init__(self, llm_api: LLMApi = None, style: str = None):
        self.llm_api = llm_api
        # 如果没有指定风格，从配置中获取默认风格
        if style is None:
            from src.utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            style = config_manager.get_setting("default_style", "电影风格")
        self.style = style if style in STYLE_TEMPLATES else config_manager.get_setting("default_style", "电影风格")
        # 优化：移除NER模型加载，提高启动速度
        self.ner = None
        # 场景和角色词库提升为类属性，便于多处调用
        self.scene_words = ['市场', '夜晚', '白天', '街道', '网吧', '路边', '屋内', '房间', '大厅', '门口', '广场', '教室', '车站', '公园', '超市', '餐厅', '楼道', '走廊', '桥', '河边', '山', '树林', '田野', '村庄', '城市', '乡村', '办公室', '工地', '医院', '商场', '地铁', '公交', '车厢', '机场', '码头', '浴室', '厨房', '卫生间', '卧室', '床', '沙发', '书房', '阳台', '楼下', '楼上', '门廊', '院子', '操场', '球场', '电影院', '舞台', '会议室', '实验室', '仓库', '隧道', '地下室', '天台', '屋顶', '停车场']
        self.role_words = ['主角', '保安', '大狗', '小狗', '警察', '老师', '学生', '父亲', '母亲', '小孩', '老人', '服务员', '售货员', '司机', '乘客', '医生', '护士', '病人', '顾客', '老板', '同事', '朋友', '陌生人', '路人', '小偷', '演员', '主持人', '观众', '记者', '摄影师', '作家', '歌手', '舞者', '画家', '工人', '农民', '士兵', '军官', '将军', '警卫', '保姆', '厨师', '厨娘', '老板娘', '女主', '男主', '女儿', '儿子', '孙子', '孙女', '猫', '狗', '鸟', '马', '牛', '羊', '猪', '鸡', '鸭', '鹅', '兔', '熊', '狼', '狐狸', '猴', '老虎', '狮子', '蛇', '鱼', '乌龟', '青蛙', '动物']

    def parse_text(self, text: str, style: str = None, progress_callback=None) -> Dict:
        """
        解析输入文本，生成分镜、场景描述、角色与元素。
        如果text看起来像是已经生成的分镜表格，则直接解析；
        否则调用大模型生成分镜。
        
        Args:
            text: 输入文本
            style: 风格参数
            progress_callback: 进度回调函数，用于更新进度和检查取消状态
            
        返回结构：
        {
            'shots': [
                {'scene': '...', 'description': '...', 'characters': [...]},
                ...
            ],
            'error': '...' (可选)
        }
        """
        if not text or not isinstance(text, str):
            return {'shots': [], 'error': '输入文本不能为空'}
            
        # 检查text是否已经是分镜表格格式
        is_table_format = ('|' in text and '文案' in text and '场景' in text and '角色' in text)
        
        if self.llm_api and not is_table_format:
            try:
                # 调用大模型生成分镜，传递风格参数和进度回调
                raw_llm_output = self.llm_api.generate_shots(text, self.style, progress_callback)
                logger.debug(f"Raw LLM Output for parsing:\n{raw_llm_output}")
                
                # 检查API返回的错误信息 - 更精确的错误检测
                if isinstance(raw_llm_output, str):
                    # 只有当返回内容明确是错误信息时才判断为错误
                    error_patterns = [
                        'api错误', 'api密钥', 'network error', 'timeout error', 
                        'invalid api key', '请求超时', '网络错误', '调用失败',
                        'api调用失败', '未知错误'
                    ]
                    if any(pattern in raw_llm_output.lower() for pattern in error_patterns):
                        logger.error(f"LLM API返回错误: {raw_llm_output}")
                        return {'shots': [], 'error': f'大模型API返回错误: {raw_llm_output}'}
                
                if not raw_llm_output or not isinstance(raw_llm_output, str):
                    logger.error(f"LLM API返回内容为空或格式不正确: {raw_llm_output}")
                    return {'shots': [], 'error': '大模型API返回内容为空或格式不正确'}
                    
                # 使用API返回的内容进行解析
                text_to_parse = raw_llm_output
            except KeyboardInterrupt:
                logger.info("大模型调用被用户中断")
                return {'shots': [], 'error': '操作被用户中断'}
            except Exception as e:
                logger.error(f"调用大模型生成分镜失败: {str(e)}", exc_info=True)
                return {'shots': [], 'error': f'调用大模型生成分镜失败: {str(e)}'}
        elif is_table_format:
            # 直接解析传入的文本（可能是已经生成的表格）
            text_to_parse = text
        else:
            # 如果没有LLM API且输入不是表格格式，则返回错误
            logger.error("无法处理输入文本：既不是表格格式，也无法调用LLM API")
            return {'shots': [], 'error': '输入文本格式无法识别，且无法调用大模型处理'}
            
        try:
            # 尝试解析为Markdown表格
            shots_data = []
            lines = [line.strip() for line in text_to_parse.split('\n') if line.strip()]
                
            # 查找表格开始位置和表头
            header_line_idx = -1
            for i, line in enumerate(lines):
                if line.startswith('|') and '文案' in line and '场景' in line and '角色' in line:
                    header_line_idx = i
                    break
            
            if header_line_idx == -1:
                return {'shots': [], 'error': '无法识别分镜表格格式或缺少表头'}

            # 提取表头，用于映射数据
            header_parts = [h.strip() for h in lines[header_line_idx].strip('|').split('|')]
            # 定义期望的列名及其在shots_data中的对应键
            expected_columns = {
                '文案': 'description',
                '场景': 'scene',
                '角色': 'role',
                '提示词': 'prompt',
                '主图': 'image',
                '视频运镜': 'video_prompt',
                '音频': 'audio',
                '操作': 'operation',
                '备选图片': 'alternative_images'
            }
            # 构建列名到索引的映射
            col_to_idx = {col_name: header_parts.index(col_name) for col_name in header_parts if col_name in expected_columns}

            # 解析表格内容 - 优化：预先准备样式模板
            # 优先使用传入的style参数，如果没有或无效则使用实例的style
            current_style = style if style and style in STYLE_TEMPLATES else self.style
            style_template = STYLE_TEMPLATES.get(current_style, STYLE_TEMPLATES['电影风格'])
            
            # 从表头下方第二行开始解析数据（跳过表头和分隔线）
            for i in range(header_line_idx + 2, len(lines)):
                line = lines[i]
                if not line.startswith('|'):
                    continue
                    
                parts = [part.strip() for part in line.strip('|').split('|')]
                
                # 确保行有足够多的列
                if len(parts) < len(header_parts):
                    continue  # 直接跳过，减少日志输出

                shot = {}
                # 优化：直接索引访问，减少循环
                for col_name, key in expected_columns.items():
                    if col_name in col_to_idx:
                        idx = col_to_idx[col_name]
                        shot[key] = parts[idx] if idx < len(parts) else ''
                    else:
                        shot[key] = ''

                # 优化：如果表格中已经有提示词，直接使用，跳过复杂的场景角色提取
                if not shot.get('prompt'):
                    # 简化处理：直接使用原始场景和角色，避免复杂的提取逻辑
                    scene = shot.get('scene', '通用场景') or '通用场景'
                    role = shot.get('role', '通用角色') or '通用角色'
                    shot['prompt'] = style_template.format(scene=scene, role=role)

                shots_data.append(shot)
            
            if not shots_data:
                logger.warning(f"未能从文本中解析出有效分镜: {text_to_parse[:200]}...") # 记录部分解析内容以供调试
                return {'shots': [], 'error': '未能解析出有效分镜，请检查大模型输出或输入文本格式'}
                
            return {'shots': shots_data}
            
        except Exception as e:
            logger.error(f"分镜解析失败: {str(e)}", exc_info=True)
            return {'shots': [], 'error': f'分镜解析失败: {str(e)}'}

    # 移除了简单正则分段的降级处理，因为在没有LLM API且输入不是表格时，已在前置逻辑中返回错误

    def extract_characters(self, text: str) -> List[str]:
        # 优化：使用简单正则匹配，避免NER模型调用
        pattern = r'[\u4e00-\u9fa5]{2,4}'
        return list(set(re.findall(pattern, text)))

    def extract_elements(self, text: str) -> List[str]:
        # 优化：使用简单的关键词匹配替代jieba分词
        element_words = ['古董', '桌子', '椅子', '书', '笔', '电脑', '手机', '车', '房子', '树', '花', '水', '火', '风', '雨', '雪', '太阳', '月亮', '星星', '山', '河', '海', '桥', '路', '门', '窗', '灯', '音乐', '声音', '颜色', '光线', '影子', '时间', '空间', '人群', '建筑', '设备', '工具', '食物', '衣服', '鞋子', '包', '钱', '卡片', '纸张', '照片', '画', '雕塑', '花瓶', '杯子', '盘子', '碗', '筷子', '勺子', '刀', '叉子']
        found = [w for w in element_words if w in text]
        return list(set(found))

    def extract_scene(self, text: str) -> str:
        # 优化：使用字符串包含检查替代jieba分词，提高性能
        scene_words = ['市场', '夜晚', '街道', '房间', '教室', '森林', '公园', '车站', '餐厅', '办公室', '广场', '桥', '山', '河', '湖', '海', '屋顶', '地下室', '走廊', '大厅', '门口', '楼梯', '阳台', '花园', '商店', '超市', '医院', '学校', '工厂', '码头', '隧道', '地铁', '机场', '车库', '剧院', '舞台', '教堂', '寺庙', '实验室', '图书馆', '书房', '卧室', '浴室', '厨房', '客厅', '庭院', '仓库', '展厅', '画廊']
        found = [w for w in scene_words if w in text]
        return '，'.join(found) if found else text[:8]

    def extract_roles(self, text: str) -> str:
        # 优化：直接使用字符串包含检查，跳过NER和jieba分词以提高性能
        role_words = ['主角', '保安', '大狗', '摊主', '警察', '老师', '学生', '医生', '护士', '顾客', '老板', '服务员', '路人', '小孩', '老人', '父亲', '母亲', '朋友', '同事', '敌人', '助手', '陌生人', '演员', '歌手', '画家', '司机', '乘客', '游客', '主持人', '观众', '记者', '摄影师', '作家', '诗人', '舞者', '运动员', '裁判', '教练', '队长', '士兵', '将军', '国王', '王后', '公主', '王子', '魔法师', '怪物', '机器人', '动物', '猫', '狗', '鸟', '鱼', '马', '熊', '狼', '狐狸', '兔子', '龙', '精灵', '妖精', '鬼魂', '僵尸', '吸血鬼', '超人', '英雄', '反派']
        found = [w for w in role_words if w in text]
        return '，'.join(found) if found else ''

# 用法示例：
# parser = TextParser(llm_api=YourLLMApi())
# result = parser.parse_text(your_markdown_or_txt)