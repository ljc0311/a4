#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信视频号发布器配置
根据截图界面优化的配置参数
"""

# 微信视频号平台限制
WECHAT_LIMITS = {
    'title_max_length': 16,  # 标题最大长度，建议6-16个字
    'title_min_length': 6,   # 标题最小长度
    'description_max_length': 600,  # 描述最大长度
    'video_max_size_gb': 20,  # 视频最大大小20GB
    'video_max_duration_hours': 8,  # 视频最大时长8小时
    'tags_max_count': 3,  # 最多3个标签
    'recommended_resolution': '720P',  # 建议分辨率
    'recommended_bitrate': '10Mbps',  # 建议码率
    'supported_formats': ['MP4', 'H.264']  # 支持的格式
}

# 微信视频号界面元素选择器 - 🔧 基于2024年12月实际页面结构优化
WECHAT_SELECTORS = {
    # 文件上传 - 🔧 基于2024年12月用户截图的实际页面结构优化
    'file_upload': [
        # 🎯 基于截图中央上传区域的精确选择器（优先级最高）
        '//div[contains(text(), "视频时长")]//ancestor::div[1]//input[@type="file"]',
        '//div[contains(text(), "视频时长")]//ancestor::div[2]//input[@type="file"]',
        '//div[contains(text(), "视频时长")]//ancestor::div[3]//input[@type="file"]',
        '//div[contains(text(), "视频时长")]//ancestor::div[4]//input[@type="file"]',
        '//div[contains(text(), "视频时长")]//ancestor::div[5]//input[@type="file"]',
        '//div[contains(text(), "视频时长")]//parent::div//input[@type="file"]',
        '//div[contains(text(), "视频时长")]//preceding-sibling::*//input[@type="file"]',
        '//div[contains(text(), "视频时长")]//following-sibling::*//input[@type="file"]',

        # 🎯 基于截图中央区域的可点击区域
        '//div[contains(@class, "upload") and contains(@style, "cursor")]//input[@type="file"]',
        '//div[contains(@class, "upload") and @role="button"]//input[@type="file"]',
        '//div[@role="button"]//input[@type="file"]',
        '//div[contains(@style, "cursor: pointer")]//input[@type="file"]',

        # 🎯 基于微信视频号特有的上传提示文本
        '//div[contains(text(), "上传时长8小时内")]//ancestor::div[1]//input[@type="file"]',
        '//div[contains(text(), "上传时长8小时内")]//ancestor::div[2]//input[@type="file"]',
        '//div[contains(text(), "上传时长8小时内")]//ancestor::div[3]//input[@type="file"]',
        '//div[contains(text(), "大小不超过20GB")]//ancestor::div[1]//input[@type="file"]',
        '//div[contains(text(), "大小不超过20GB")]//ancestor::div[2]//input[@type="file"]',
        '//div[contains(text(), "大小不超过20GB")]//ancestor::div[3]//input[@type="file"]',

        # 🎯 基于上传区域的通用选择器
        '//div[contains(@class, "upload")]//input[@type="file"]',
        '//div[contains(@class, "upload-area")]//input[@type="file"]',
        '//div[contains(@class, "upload-zone")]//input[@type="file"]',
        '//div[contains(@class, "file-upload")]//input[@type="file"]',
        '//div[contains(@class, "video-upload")]//input[@type="file"]',
        '//div[contains(@class, "media-upload")]//input[@type="file"]',

        # 🎯 标准文件输入框（基础选择器）
        '//input[@type="file"]',
        '//input[@accept="video/*"]',
        '//input[contains(@accept, ".mp4")]',
        '//input[contains(@accept, "video")]',

        # 🎯 隐藏的文件输入框（常见模式）
        '//input[@type="file" and contains(@style, "display: none")]',
        '//input[@type="file" and contains(@style, "opacity: 0")]',
        '//input[@type="file" and contains(@style, "position: absolute")]',
        '//input[@type="file" and contains(@style, "visibility: hidden")]',

        # 🎯 通过ID和类名查找
        '//input[contains(@id, "upload")][@type="file"]',
        '//input[contains(@id, "file")][@type="file"]',
        '//input[contains(@id, "video")][@type="file"]',
        '//input[contains(@class, "upload")][@type="file"]',
        '//input[contains(@class, "file")][@type="file"]',

        # 🎯 现代化框架组件
        '//div[contains(@class, "ant-upload")]//input[@type="file"]',
        '//div[contains(@class, "el-upload")]//input[@type="file"]',
        '//div[contains(@class, "ivu-upload")]//input[@type="file"]',

        # 🎯 微信特有的组件结构
        '//div[contains(@class, "weui-")]//input[@type="file"]',
        '//div[contains(@class, "wx-")]//input[@type="file"]',

        # 🎯 基于页面布局的查找
        '//div[contains(@class, "center")]//input[@type="file"]',
        '//div[contains(@class, "main")]//input[@type="file"]',
        '//div[contains(@class, "content")]//input[@type="file"]'
    ],

    # 标题输入 - 🔧 基于实际页面结构优化（截图显示右侧有标题输入区域）
    'title_input': [
        # 基于截图右侧区域的标题输入框
        '//div[contains(text(), "标题")]//following-sibling::*//input',
        '//div[contains(text(), "标题")]//following-sibling::*//textarea',
        '//div[contains(text(), "标题")]//parent::div//input',
        '//div[contains(text(), "标题")]//parent::div//textarea',
        '//div[contains(text(), "标题")]//ancestor::div[2]//input',
        '//div[contains(text(), "标题")]//ancestor::div[2]//textarea',

        # 基于placeholder的查找
        '//input[contains(@placeholder, "标题")]',
        '//textarea[contains(@placeholder, "标题")]',
        '//input[contains(@placeholder, "请输入标题")]',
        '//input[contains(@placeholder, "微信视频号主页内容")]',
        '//input[contains(@placeholder, "字数建议6-16个字")]',
        '//input[contains(@placeholder, "6-16个字")]',
        '//input[contains(@placeholder, "输入标题")]',
        '//input[contains(@placeholder, "视频标题")]',

        # 基于标签文本的查找
        '//label[contains(text(), "标题")]//following-sibling::*//input',
        '//label[contains(text(), "标题")]//input',
        '//span[contains(text(), "标题")]//ancestor::div[3]//input',
        '//span[contains(text(), "标题")]//ancestor::div[3]//textarea',

        # 基于CSS类名的查找
        '//div[contains(@class, "title")]//input',
        '//div[contains(@class, "title")]//textarea',
        '//input[contains(@class, "title-input")]',
        '//textarea[contains(@class, "title-input")]',
        '//input[contains(@class, "title")]',
        '//textarea[contains(@class, "title")]',

        # 现代化框架组件
        '//div[contains(@class, "ant-input")]//input[1]',
        '//div[contains(@class, "el-input")]//input',
        '//div[contains(@class, "ivu-input")]//input',

        # 基于表单结构的查找
        '//form//input[1]',
        '//form//div[1]//input',
        '//form//div[contains(@class, "form-item")][1]//input',

        # 基于位置的查找（标题通常在第一个）
        '//div[contains(@class, "form")]//input[1]',
        '//div[contains(@class, "field")]//input[1]',

        # 微信特有的组件
        '//div[contains(@class, "weui-cell")]//input[1]',
        '//div[contains(@class, "wx-input")]//input',

        # 通过相邻元素定位
        '//div[contains(text(), "6-16个字")]//ancestor::div[2]//input',
        '//div[contains(text(), "字数建议")]//ancestor::div[2]//input',

        # 基于右侧面板的查找
        '//div[contains(@class, "right")]//input[1]',
        '//div[contains(@class, "sidebar")]//input[1]',
        '//div[contains(@class, "panel")]//input[1]'
    ],

    # 描述输入 - 🔧 基于2024年最新页面结构优化
    'description_input': [
        # 基于placeholder的查找
        '//textarea[contains(@placeholder, "描述")]',
        '//textarea[contains(@placeholder, "简介")]',
        '//textarea[contains(@placeholder, "请输入描述")]',
        '//textarea[contains(@placeholder, "添加描述")]',
        '//textarea[contains(@placeholder, "视频描述")]',
        '//textarea[contains(@placeholder, "内容描述")]',
        '//textarea[contains(@placeholder, "说点什么")]',

        # 基于标签文本的查找
        '//div[contains(text(), "描述")]//following-sibling::*//textarea',
        '//div[contains(text(), "描述")]//parent::div//textarea',
        '//div[contains(text(), "简介")]//following-sibling::*//textarea',
        '//label[contains(text(), "描述")]//following-sibling::*//textarea',
        '//label[contains(text(), "描述")]//textarea',
        '//span[contains(text(), "描述")]//ancestor::div[3]//textarea',

        # 基于相邻元素定位（声明原创通常在描述下方）
        '//div[contains(text(), "声明原创")]//preceding-sibling::*//textarea',
        '//div[contains(text(), "声明原创")]//ancestor::div[3]//textarea',
        '//div[contains(text(), "位置")]//preceding-sibling::*//textarea',
        '//div[contains(text(), "合集")]//preceding-sibling::*//textarea',

        # 基于CSS类名的查找
        '//div[contains(@class, "description")]//textarea',
        '//div[contains(@class, "content")]//textarea',
        '//div[contains(@class, "desc")]//textarea',
        '//textarea[contains(@class, "desc-input")]',
        '//textarea[contains(@class, "description-input")]',
        '//textarea[contains(@class, "content-input")]',

        # 富文本编辑器
        '//div[contains(@class, "editor")]//textarea',
        '//div[contains(@class, "rich-editor")]//textarea',
        '//div[contains(@class, "text-editor")]//textarea',
        '//div[contains(@contenteditable, "true")]',
        '//div[@contenteditable="true"]',

        # 现代化框架组件
        '//div[contains(@class, "ant-input")]//textarea',
        '//div[contains(@class, "el-textarea")]//textarea',
        '//div[contains(@class, "ivu-input")]//textarea',

        # 基于表单结构的查找（描述通常在第二个）
        '//form//textarea[1]',
        '//form//div[2]//textarea',
        '//form//div[contains(@class, "form-item")][2]//textarea',

        # 基于位置的查找
        '//div[contains(@class, "form")]//textarea[1]',
        '//div[contains(@class, "field")]//textarea[1]',

        # 微信特有的组件
        '//div[contains(@class, "weui-cell")]//textarea',
        '//div[contains(@class, "wx-textarea")]//textarea',

        # 通过行数属性查找（描述框通常有多行）
        '//textarea[@rows]',
        '//textarea[contains(@style, "height")]',

        # 备用查找（所有textarea）
        '//textarea[not(contains(@placeholder, "标题"))]',
        '//textarea[position()>1]'
    ],
    
    # 位置设置
    'location_button': [
        '//div[contains(text(), "位置")]',
        '//span[contains(text(), "位置")]',
        '//button[contains(text(), "位置")]',
        '//div[contains(@class, "location")]',
        '//input[contains(@placeholder, "位置")]'
    ],
    
    'location_input': [
        '//input[contains(@placeholder, "搜索位置")]',
        '//input[contains(@placeholder, "请输入位置")]',
        '//input[contains(@class, "location-input")]'
    ],
    
    'location_result': [
        '//div[contains(@class, "location-result")]//div[1]'
    ],
    
    # 原创声明
    'original_claim': [
        '//input[@type="checkbox" and contains(@id, "original")]',
        '//input[@type="checkbox"]//following-sibling::*[contains(text(), "声明原创")]',
        '//div[contains(text(), "声明原创")]//input[@type="checkbox"]',
        '//span[contains(text(), "声明原创")]//preceding-sibling::input[@type="checkbox"]',
        '//label[contains(text(), "声明原创")]//input[@type="checkbox"]'
    ],
    
    # 合集设置
    'collection_button': [
        '//div[contains(text(), "添加到合集")]',
        '//span[contains(text(), "合集")]',
        '//button[contains(text(), "合集")]',
        '//div[contains(@class, "collection")]'
    ],
    
    'collection_input': [
        '//input[contains(@placeholder, "搜索合集")]',
        '//input[contains(@placeholder, "合集名称")]',
        '//input[contains(@class, "collection-input")]'
    ],
    
    'collection_result': [
        '//div[contains(@class, "collection-result")]//div[1]'
    ],
    
    # 定时发布
    'schedule_option': [
        '//div[contains(text(), "定时发表")]',
        '//span[contains(text(), "定时发表")]',
        '//input[@type="radio"]//following-sibling::*[contains(text(), "定时")]',
        '//label[contains(text(), "定时")]//input[@type="radio"]'
    ],
    
    'time_input': [
        '//input[@type="datetime-local"]',
        '//input[contains(@placeholder, "选择时间")]',
        '//input[contains(@class, "time-picker")]'
    ],
    
    # 发布按钮 - 🔧 基于实际页面结构优化（截图显示右下角有"发表"按钮）
    'publish_button': [
        # 基于截图右下角的发表按钮
        '//button[text()="发表"]',
        '//button[contains(text(), "发表")]',
        '//span[text()="发表"]/parent::button',
        '//span[contains(text(), "发表")]/parent::button',

        # 基于右下角位置的查找
        '//div[contains(@class, "bottom")]//button[contains(text(), "发表")]',
        '//div[contains(@class, "footer")]//button[contains(text(), "发表")]',
        '//div[contains(@class, "action")]//button[contains(text(), "发表")]',
        '//div[contains(@class, "right")]//button[contains(text(), "发表")]',
        '//div[contains(@class, "fixed")]//button[contains(text(), "发表")]',
        '//div[contains(@class, "sticky")]//button[contains(text(), "发表")]',

        # 基于按钮文本的查找
        '//button[contains(text(), "发布")]',
        '//button[contains(text(), "立即发布")]',
        '//button[contains(text(), "立即发表")]',
        '//button[contains(text(), "确认发布")]',
        '//button[contains(text(), "确认发表")]',
        '//button[contains(text(), "提交")]',

        # 基于span内文本的查找
        '//span[contains(text(), "发布")]/parent::button',
        '//span[contains(text(), "立即")]/parent::button',

        # 基于CSS类名的查找
        '//button[contains(@class, "publish")]',
        '//button[contains(@class, "submit")]',
        '//button[contains(@class, "primary")]',
        '//button[contains(@class, "btn-primary")]',
        '//button[contains(@class, "main-btn")]',
        '//button[contains(@class, "action-btn")]',

        # 基于页面区域的查找
        '//div[contains(@class, "toolbar")]//button[contains(text(), "发表")]',
        '//div[contains(@class, "operate")]//button[contains(text(), "发表")]',
        '//div[contains(@class, "publish-area")]//button',
        '//div[contains(@class, "submit-area")]//button',

        # 基于相邻按钮的查找（发表按钮通常在最右边）
        '//button[contains(text(), "保存草稿")]//following-sibling::button[contains(text(), "发表")]',
        '//button[contains(text(), "手机预览")]//following-sibling::button[contains(text(), "发表")]',
        '//button[contains(text(), "预览")]//following-sibling::button[contains(text(), "发表")]',
        '//button[contains(text(), "草稿")]//following-sibling::button[last()]',
        '//button[contains(text(), "预览")]//following-sibling::button[last()]',

        # 基于表单结构的查找
        '//form//button[contains(text(), "发表")]',
        '//form//button[contains(@class, "submit")]',
        '//form//button[last()]',

        # 现代化框架组件
        '//div[contains(@class, "ant-btn")]//button[contains(text(), "发表")]',
        '//button[contains(@class, "ant-btn-primary")]',
        '//div[contains(@class, "el-button")]//button[contains(text(), "发表")]',
        '//button[contains(@class, "el-button--primary")]',

        # 微信特有的组件
        '//div[contains(@class, "weui-btn")]//button[contains(text(), "发表")]',
        '//button[contains(@class, "weui-btn_primary")]',
        '//div[contains(@class, "wx-button")]//button[contains(text(), "发表")]',

        # 基于位置的查找（发表按钮通常在右下角）
        '//div[contains(@style, "position: fixed")]//button[contains(text(), "发表")]',
        '//div[contains(@style, "bottom")]//button[contains(text(), "发表")]',
        '//div[contains(@style, "right")]//button[contains(text(), "发表")]',

        # 基于颜色和样式的查找
        '//button[contains(@class, "primary") and contains(text(), "发表")]',
        '//button[contains(@class, "blue") and contains(text(), "发表")]',
        '//button[contains(@class, "main") and contains(text(), "发表")]',

        # 备用查找（最后的按钮通常是发表按钮）
        '//button[last()]',
        '//div[contains(@class, "button-group")]//button[last()]',
        '//div[contains(@class, "btn-group")]//button[last()]',

        # 通过type属性查找
        '//button[@type="submit"]',
        '//input[@type="submit"]',

        # 基于页面右侧面板的查找
        '//div[contains(@class, "sidebar")]//button[contains(text(), "发表")]',
        '//div[contains(@class, "panel")]//button[contains(text(), "发表")]'
    ],
    
    # 上传进度指示器
    'upload_progress': [
        '//div[contains(@class, "progress")]',
        '//div[contains(text(), "上传中")]',
        '//div[contains(text(), "处理中")]',
        '//div[contains(text(), "%")]',
        '//div[contains(@class, "uploading")]',
        '//div[contains(text(), "正在上传")]',
        '//div[contains(text(), "视频处理中")]'
    ],
    
    # 上传完成指示器
    'upload_complete': [
        '//video',  # 视频预览
        '//input[contains(@placeholder, "标题")]',  # 标题输入框
        '//input[contains(@placeholder, "微信视频号主页内容")]',  # 微信特有标题提示
        '//button[text()="发表"]',  # 发布按钮
        '//textarea[contains(@placeholder, "描述")]',  # 描述输入框
        '//div[contains(text(), "位置")]',
        '//div[contains(text(), "添加到合集")]',
        '//div[contains(text(), "声明原创")]',
        '//button[contains(text(), "保存草稿")]',
        '//button[contains(text(), "手机预览")]'
    ]
}

# 微信视频号发布配置
WECHAT_PUBLISH_CONFIG = {
    'upload_timeout': 600,  # 上传超时时间（秒）
    'upload_check_interval': 5,  # 上传检查间隔（秒）
    'page_load_timeout': 10,  # 页面加载超时时间（秒）
    'element_wait_timeout': 10,  # 元素等待超时时间（秒）
    'publish_wait_time': 8,  # 发布后等待时间（秒）
    'upload_url': 'https://channels.weixin.qq.com/platform/post/create',
    'retry_count': 3,  # 重试次数
    'retry_delay': 2  # 重试延迟（秒）
}

# 微信视频号错误处理
WECHAT_ERROR_DIALOGS = [
    '//div[contains(text(), "确定")]',
    '//button[contains(text(), "确定")]',
    '//button[contains(text(), "知道了")]',
    '//button[contains(text(), "我知道了")]',
    '//button[contains(text(), "取消")]',
    '//div[contains(@class, "modal")]//button',
    '//div[contains(@class, "dialog")]//button'
]

# 微信视频号成功指示器
WECHAT_SUCCESS_INDICATORS = [
    '//div[contains(text(), "发布成功")]',
    '//div[contains(text(), "已发布")]',
    '//span[contains(text(), "发布成功")]',
    '//div[contains(text(), "发表成功")]'
]

def get_wechat_config():
    """获取微信视频号完整配置"""
    return {
        'limits': WECHAT_LIMITS,
        'selectors': WECHAT_SELECTORS,
        'publish_config': WECHAT_PUBLISH_CONFIG,
        'error_dialogs': WECHAT_ERROR_DIALOGS,
        'success_indicators': WECHAT_SUCCESS_INDICATORS
    }

def validate_video_info(video_info: dict) -> dict:
    """🔧 优化：验证视频信息是否符合微信视频号要求，自动修正超限内容"""
    errors = []
    warnings = []

    # 检查标题
    title = video_info.get('title', '')
    if len(title) < WECHAT_LIMITS['title_min_length']:
        warnings.append(f"标题长度建议至少{WECHAT_LIMITS['title_min_length']}个字")
    if len(title) > WECHAT_LIMITS['title_max_length']:
        # 🔧 修复：将标题超限从错误改为警告，并自动截断
        original_title = title
        truncated_title = title[:WECHAT_LIMITS['title_max_length']]
        video_info['title'] = truncated_title  # 自动修正
        warnings.append(f"标题过长已自动截断：'{original_title}' -> '{truncated_title}'")

    # 检查描述
    description = video_info.get('description', '')
    if len(description) > WECHAT_LIMITS['description_max_length']:
        # 🔧 修复：将描述超限从错误改为警告，并自动截断
        original_desc = description
        truncated_desc = description[:WECHAT_LIMITS['description_max_length']]
        video_info['description'] = truncated_desc  # 自动修正
        warnings.append(f"描述过长已自动截断：{len(original_desc)}字 -> {len(truncated_desc)}字")

    # 检查标签
    tags = video_info.get('tags', [])
    if len(tags) > WECHAT_LIMITS['tags_max_count']:
        # 🔧 修复：自动截断标签数量
        original_tags = tags.copy()
        truncated_tags = tags[:WECHAT_LIMITS['tags_max_count']]
        video_info['tags'] = truncated_tags  # 自动修正
        warnings.append(f"标签数量过多已自动截断：{len(original_tags)}个 -> {len(truncated_tags)}个")

    return {
        'valid': len(errors) == 0,  # 🔧 现在应该总是True，因为我们自动修正了所有问题
        'errors': errors,
        'warnings': warnings
    }

# 🔧 新增：完整的微信发布器配置
WECHAT_CONFIG = {
    'platform_name': '微信视频号',
    'base_url': 'https://channels.weixin.qq.com',
    'upload_url': 'https://channels.weixin.qq.com/platform/post/create',
    'login_url': 'https://channels.weixin.qq.com/login.html',

    # 内容限制
    'limits': WECHAT_LIMITS,

    # 选择器配置
    'selectors': WECHAT_SELECTORS,

    # 等待时间配置
    'timeouts': {
        'page_load': 30,
        'element_wait': 10,
        'upload_wait': 600,  # 10分钟上传超时
        'publish_wait': 30
    },

    # 重试配置
    'retry': {
        'max_attempts': 3,
        'delay': 2
    },

    # 发布配置
    'publish_config': WECHAT_PUBLISH_CONFIG,
    'error_dialogs': WECHAT_ERROR_DIALOGS,
    'success_indicators': WECHAT_SUCCESS_INDICATORS
}
