# -*- coding: utf-8 -*-
"""
角色检测配置文件
提供可扩展的角色称谓映射和检测规则
"""

class CharacterDetectionConfig:
    """角色检测配置类"""
    
    # 通用角色同义词映射
    UNIVERSAL_SYNONYMS = {
        '主角': ['主人公', '男主', '女主', '主要角色', '核心角色'],
        '男主': ['主角', '主人公', '主要人物', '男性主角', '男性角色', '男主角'],
        '女主': ['主角', '主人公', '主要人物', '女性主角', '女性角色', '女主角'],
        '反派': ['坏人', '恶人', '反面角色', '敌人', '对手', '反角', '恶役'],
        '配角': ['次要角色', '辅助角色', '支持角色', '副角'],
        '路人': ['路人甲', '路人乙', '群众', '背景角色'],
        '朋友': ['好友', '伙伴', '同伴', '友人'],
        '敌人': ['仇人', '对手', '敌手', '反派']
    }
    
    # 动物角色称谓映射
    ANIMAL_SYNONYMS = {
        # 常见宠物
        '小狗': ['狗狗', '犬', '小犬', '幼犬', '宠物狗', '狗子', '汪星人'],
        '小猫': ['猫咪', '猫', '小猫咪', '幼猫', '宠物猫', '猫子', '喵星人'],
        '小鸟': ['鸟儿', '鸟', '小鸟儿', '鸟宝宝'],
        '小兔': ['兔子', '兔兔', '小兔子', '兔儿', '兔宝宝'],
        '小鱼': ['鱼儿', '鱼', '小鱼儿', '鱼宝宝'],
        
        # 野生动物
        '老虎': ['虎', '猛虎', '大虎', '老虎王', '虎王'],
        '狮子': ['雄狮', '母狮', '狮王', '狮子王'],
        '大象': ['象', '大象王', '象王'],
        '熊猫': ['大熊猫', '国宝', '熊猫宝宝'],
        '小熊': ['熊', '熊熊', '熊宝宝', '小熊仔'],
        '猴子': ['猴', '小猴', '猴儿', '猴宝宝'],
        '狐狸': ['狐', '小狐狸', '狐仙'],
        '狼': ['野狼', '狼王', '大灰狼'],
        
        # 海洋动物
        '海豚': ['小海豚', '海豚宝宝'],
        '鲸鱼': ['鲸', '大鲸鱼', '鲸鱼王'],
        '乌龟': ['龟', '小乌龟', '龟仙人'],
        
        # 神话动物
        '龙': ['神龙', '巨龙', '飞龙', '龙王'],
        '凤凰': ['凤', '神鸟', '火凤凰'],
        '麒麟': ['神兽', '瑞兽']
    }
    
    # 职业/身份称谓映射
    PROFESSION_SYNONYMS = {
        '医生': ['大夫', '医师', '主治医生', '医务人员', '白衣天使'],
        '老师': ['教师', '先生', '老师傅', '教授', '导师'],
        '警察': ['民警', '警官', '公安', '执法人员', '警员'],
        '司机': ['驾驶员', '开车的', '车夫', '司机师傅'],
        '学生': ['同学', '学员', '小朋友', '学童'],
        '工人': ['工友', '师傅', '工人师傅'],
        '农民': ['农夫', '种田的', '农民伯伯'],
        '商人': ['老板', '商贩', '生意人'],
        '军人': ['士兵', '战士', '军官'],
        '厨师': ['大厨', '厨子', '做饭的']
    }
    
    # 年龄相关称谓映射
    AGE_SYNONYMS = {
        '小孩': ['孩子', '儿童', '小朋友', '娃娃', '小家伙'],
        '少年': ['青少年', '小伙子', '少女', '年轻人'],
        '青年': ['年轻人', '小伙', '姑娘', '青年人'],
        '中年': ['中年人', '大叔', '阿姨', '中年男子', '中年女子'],
        '老人': ['长者', '老爷爷', '老奶奶', '老人家', '长辈']
    }
    
    # 动物特征描述词
    ANIMAL_DESCRIPTORS = {
        '狗': ['汪汪', '摇尾巴', '忠诚', '看门', '吠叫', '奔跑'],
        '猫': ['喵喵', '爪子', '胡须', '优雅', '敏捷', '慵懒'],
        '虎': ['咆哮', '条纹', '威猛', '森林之王', '利爪', '猛兽'],
        '狮': ['鬃毛', '草原', '王者', '咆哮', '威严', '狮吼'],
        '熊': ['憨厚', '冬眠', '蜂蜜', '笨重', '毛茸茸', '力大'],
        '兔': ['蹦跳', '长耳朵', '胡萝卜', '敏捷', '可爱', '三瓣嘴'],
        '鸟': ['飞翔', '羽毛', '鸣叫', '翅膀', '筑巢', '啁啾'],
        '鱼': ['游泳', '鳞片', '水中', '鱼鳍', '吐泡泡'],
        '象': ['长鼻子', '巨大', '象牙', '厚皮', '温和'],
        '猴': ['爬树', '灵活', '顽皮', '香蕉', '跳跃']
    }
    
    # 特殊类型角色映射
    SPECIAL_TYPE_SYNONYMS = {
        '机器人': ['机械人', '人工智能', 'AI', '机器', '机械', '智能体'],
        '外星人': ['外星生物', '异星人', '宇宙人', '外来者'],
        '精灵': ['小精灵', '森林精灵', '魔法精灵', '仙子'],
        '天使': ['守护天使', '天使长', '圣天使'],
        '恶魔': ['魔鬼', '恶灵', '魔王', '邪灵'],
        '神仙': ['仙人', '神明', '仙女', '神灵'],
        '僵尸': ['丧尸', '活死人', '不死族'],
        '吸血鬼': ['血族', '夜行者', '不死者']
    }
    
    # 特殊类型特征描述
    SPECIAL_TYPE_DESCRIPTORS = {
        '机器人': ['机械', '金属', '电子', '人工智能', '程序', '数据'],
        '外星人': ['外星', '宇宙', '飞船', '异世界', '科技', '未知'],
        '精灵': ['魔法', '森林', '尖耳朵', '魔力', '自然', '神秘'],
        '龙': ['飞行', '火焰', '鳞片', '巨大', '古老', '强大'],
        '天使': ['光明', '翅膀', '神圣', '纯洁', '守护'],
        '恶魔': ['黑暗', '邪恶', '地狱', '诅咒', '恐怖']
    }
    
    # 动物关键词列表
    ANIMAL_KEYWORDS = [
        '狗', '猫', '虎', '狮', '熊', '兔', '鸟', '鱼', '马', '牛', '羊', '猪',
        '鸡', '鸭', '鹅', '鼠', '蛇', '龙', '凤', '鹰', '狼', '狐', '鹿', '象',
        '猴', '熊猫', '企鹅', '海豚', '鲸鱼', '乌龟', '青蛙', '蝴蝶', '蜜蜂',
        '蚂蚁', '蜘蛛', '螃蟹', '章鱼', '鲨鱼', '海星', '水母', '孔雀', '天鹅',
        '鸽子', '麻雀', '乌鸦', '喜鹊', '燕子', '蝙蝠', '松鼠', '刺猬', '袋鼠'
    ]
    
    # 动物类型映射
    ANIMAL_TYPE_MAP = {
        '狗': '狗', '犬': '狗', '猫': '猫', '虎': '老虎', '狮': '狮子',
        '熊': '熊', '兔': '兔子', '鸟': '鸟', '鱼': '鱼', '马': '马',
        '牛': '牛', '羊': '羊', '猪': '猪', '鸡': '鸡', '鸭': '鸭',
        '鹅': '鹅', '鼠': '老鼠', '蛇': '蛇', '龙': '龙', '凤': '凤凰',
        '鹰': '老鹰', '狼': '狼', '狐': '狐狸', '鹿': '鹿', '象': '大象',
        '猴': '猴子', '企鹅': '企鹅', '海豚': '海豚', '鲸': '鲸鱼',
        '龟': '乌龟', '蛙': '青蛙', '蝶': '蝴蝶', '蜂': '蜜蜂'
    }
    
    # 年龄关键词映射
    AGE_KEYWORDS = {
        '小': ['小朋友', '孩子', '儿童', '小孩', '娃娃'],
        '老': ['老人', '长者', '老爷爷', '老奶奶', '老人家'],
        '年轻': ['青年', '小伙', '姑娘', '少年', '年轻人'],
        '中年': ['大叔', '阿姨', '中年人', '中年男子', '中年女子']
    }
    
    @classmethod
    def get_all_synonyms(cls):
        """获取所有同义词映射"""
        return {
            **cls.UNIVERSAL_SYNONYMS,
            **cls.ANIMAL_SYNONYMS,
            **cls.PROFESSION_SYNONYMS,
            **cls.AGE_SYNONYMS,
            **cls.SPECIAL_TYPE_SYNONYMS
        }
    
    @classmethod
    def get_animal_info(cls):
        """获取动物相关信息"""
        return {
            'keywords': cls.ANIMAL_KEYWORDS,
            'descriptors': cls.ANIMAL_DESCRIPTORS,
            'type_map': cls.ANIMAL_TYPE_MAP
        }
    
    @classmethod
    def get_special_type_info(cls):
        """获取特殊类型信息"""
        return {
            'synonyms': cls.SPECIAL_TYPE_SYNONYMS,
            'descriptors': cls.SPECIAL_TYPE_DESCRIPTORS
        }
    
    @classmethod
    def add_custom_synonyms(cls, custom_synonyms: dict):
        """添加自定义同义词映射"""
        for key, values in custom_synonyms.items():
            if key in cls.UNIVERSAL_SYNONYMS:
                cls.UNIVERSAL_SYNONYMS[key].extend(values)
            else:
                cls.UNIVERSAL_SYNONYMS[key] = values
    
    @classmethod
    def add_custom_animal_descriptors(cls, custom_descriptors: dict):
        """添加自定义动物描述词"""
        for animal, descriptors in custom_descriptors.items():
            if animal in cls.ANIMAL_DESCRIPTORS:
                cls.ANIMAL_DESCRIPTORS[animal].extend(descriptors)
            else:
                cls.ANIMAL_DESCRIPTORS[animal] = descriptors
    
    @classmethod
    def normalize_character_name(cls, character_name: str, force_standard: str = None) -> str:
        """将角色名称标准化为统一的称谓
        
        Args:
            character_name: 原始角色名称
            force_standard: 强制使用的标准名称，如果提供则优先使用
            
        Returns:
            str: 标准化后的角色名称
        """
        if not character_name or not character_name.strip():
            return character_name
            
        character_name = character_name.strip()
        
        # 如果提供了强制标准名称，直接使用
        if force_standard and force_standard.strip():
            return force_standard.strip()
        
        # 获取所有同义词映射
        all_synonyms = cls.get_all_synonyms()
        
        # 查找角色名称对应的标准名称
        for standard_name, synonyms in all_synonyms.items():
            if character_name == standard_name:
                return standard_name
            if character_name in synonyms:
                return standard_name
        
        # 如果没有找到映射，返回原名称
        return character_name
    
    @classmethod
    def normalize_character_list(cls, character_list: str, separator: str = '、', force_unify: bool = True) -> str:
        """将角色列表中的所有角色名称标准化
        
        Args:
            character_list: 角色列表字符串，用分隔符分隔
            separator: 分隔符，默认为中文顿号
            force_unify: 是否强制统一同义词，如果为True则将同义词统一为第一个出现的名称
            
        Returns:
            str: 标准化后的角色列表字符串
        """
        if not character_list or not character_list.strip():
            return character_list
            
        # 分割角色列表
        characters = [char.strip() for char in character_list.split(separator) if char.strip()]
        
        if force_unify:
            # 强制统一模式：检测同义词并统一使用第一个出现的名称
            unified_characters = cls._force_unify_characters(characters)
            return separator.join(unified_characters)
        else:
            # 标准化每个角色名称
            normalized_characters = [cls.normalize_character_name(char) for char in characters]
            
            # 去重并保持顺序
            unique_characters = []
            seen = set()
            for char in normalized_characters:
                if char not in seen:
                    unique_characters.append(char)
                    seen.add(char)
            
            # 重新组合
            return separator.join(unique_characters)
    
    @classmethod
    def _force_unify_characters(cls, characters: list) -> list:
        """强制统一角色名称：将同义词统一为第一个出现的名称
        
        Args:
            characters: 角色名称列表
            
        Returns:
            list: 统一后的角色名称列表
        """
        if not characters:
            return characters
            
        # 获取所有同义词映射
        all_synonyms = cls.get_all_synonyms()
        
        # 创建反向映射：从同义词到标准名称
        synonym_to_standard = {}
        for standard_name, synonyms in all_synonyms.items():
            synonym_to_standard[standard_name] = standard_name
            for synonym in synonyms:
                synonym_to_standard[synonym] = standard_name
        
        # 记录每个标准名称第一次出现时使用的实际名称
        first_appearance = {}
        unified_characters = []
        seen_standards = set()
        
        for char in characters:
            # 获取标准名称
            standard_name = synonym_to_standard.get(char, char)
            
            if standard_name not in seen_standards:
                # 第一次出现，记录实际使用的名称
                first_appearance[standard_name] = char
                unified_characters.append(char)
                seen_standards.add(standard_name)
            # 如果已经出现过，跳过（使用第一次出现的名称）
        
        return unified_characters
    
    @classmethod
    def get_unified_character_name(cls, character_names: list) -> str:
        """从多个可能的角色名称中选择统一的名称
        
        Args:
            character_names: 可能的角色名称列表
            
        Returns:
            str: 统一的角色名称（选择第一个出现的）
        """
        if not character_names:
            return ""
        
        # 使用强制统一逻辑
        unified = cls._force_unify_characters(character_names)
        return unified[0] if unified else character_names[0]