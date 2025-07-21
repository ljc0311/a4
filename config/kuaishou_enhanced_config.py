#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手增强版发布器配置文件 - 2024年最新版本
采用最新反检测技术和智能元素检测配置
"""

# 快手增强版发布器配置
KUAISHOU_ENHANCED_CONFIG = {
    'enabled': True,
    'platform_name': 'kuaishou_enhanced',
    'display_name': '快手(增强版)',
    
    # 基础配置
    'driver_type': 'chrome',
    'headless': False,
    'timeout': 30,
    'implicit_wait': 10,
    'page_load_timeout': 60,
    'script_timeout': 30,
    
    # 反检测配置 - 2024年最新技术
    'anti_detection': {
        'enabled': True,
        'use_undetected_chromedriver': True,  # 使用undetected-chromedriver
        'use_selenium_stealth': True,         # 使用selenium-stealth
        'inject_stealth_scripts': True,      # 注入自定义反检测脚本
        'random_user_agent': True,           # 随机User-Agent
        'random_window_size': True,          # 随机窗口大小
        'disable_automation_flags': True,    # 禁用自动化标识
        'fake_plugins': True,                # 伪造插件信息
        'fake_webgl': True,                  # 伪造WebGL指纹
        'fake_canvas': True,                 # 伪造Canvas指纹
    },
    
    # 人性化操作配置
    'human_behavior': {
        'enabled': True,
        'typing_delay_min': 0.05,           # 最小打字间隔(秒)
        'typing_delay_max': 0.15,           # 最大打字间隔(秒)
        'action_delay_min': 0.5,            # 最小操作间隔(秒)
        'action_delay_max': 2.0,            # 最大操作间隔(秒)
        'scroll_behavior': True,            # 启用滚动行为
        'mouse_movement': True,             # 启用鼠标轨迹模拟
    },
    
    # 智能重试配置
    'retry_config': {
        'max_retries': 3,                   # 最大重试次数
        'retry_delay': 2,                   # 重试间隔(秒)
        'exponential_backoff': True,        # 指数退避
        'retry_on_timeout': True,           # 超时重试
        'retry_on_element_not_found': True, # 元素未找到重试
    },
    
    # 上传配置
    'upload_config': {
        'upload_timeout': 300,              # 上传超时(秒)
        'progress_check_interval': 3,       # 进度检查间隔(秒)
        'wait_after_upload': 2,             # 上传后等待时间(秒)
    },
    
    # 内容限制
    'content_limits': {
        'title_max_length': 50,             # 标题最大长度
        'description_max_length': 1000,     # 描述最大长度
        'tags_max_count': 5,                # 最大标签数量
    },
    
    # 调试配置
    'debug_config': {
        'use_debug_mode': True,             # 使用调试模式
        'debug_port': 9222,                 # 调试端口
        'debugger_address': '127.0.0.1:9222',
        'save_screenshots': True,           # 保存截图
        'verbose_logging': True,            # 详细日志
    },
    
    # 模拟模式配置
    'simulation_mode': False,               # 是否启用模拟模式
}

# 快手平台特定的User-Agent列表
KUAISHOU_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
]

# 窗口大小选项
KUAISHOU_WINDOW_SIZES = [
    (1920, 1080),
    (1366, 768),
    (1440, 900),
    (1536, 864),
    (1600, 900),
]

# Chrome选项配置
KUAISHOU_CHROME_OPTIONS = [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-blink-features=AutomationControlled',
    '--disable-extensions',
    '--disable-plugins',
    '--disable-images',  # 可选：禁用图片加载提高速度
    '--disable-javascript',  # 可选：在某些情况下禁用JS
    '--lang=zh-CN',
    '--disable-web-security',
    '--disable-features=VizDisplayCompositor',
    '--disable-ipc-flooding-protection',
]

# 实验性选项
KUAISHOU_EXPERIMENTAL_OPTIONS = {
    "excludeSwitches": ["enable-automation"],
    "useAutomationExtension": False,
    "prefs": {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 2,  # 禁用图片
    }
}

# 反检测脚本
KUAISHOU_STEALTH_SCRIPT = """
// 隐藏webdriver属性
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

// 隐藏Chrome自动化扩展
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// 修改plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// 修改语言
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en-US', 'en'],
});

// 隐藏自动化标识
Object.defineProperty(navigator, 'permissions', {
    get: () => ({
        query: () => Promise.resolve({ state: 'granted' })
    })
});

// 修改User-Agent相关
Object.defineProperty(navigator, 'platform', {
    get: () => 'Win32'
});

// 隐藏Selenium标识
delete window.document.$cdc_asdjflasutopfhvcZLmcfl_;
delete window.$chrome_asyncScriptInfo;
delete window.$cdc_asdjflasutopfhvcZLmcfl_;

// 模拟真实浏览器行为
window.outerHeight = window.screen.height;
window.outerWidth = window.screen.width;

// 隐藏自动化检测
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 4
});

// 伪造WebGL指纹
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
        return 'Intel Inc.';
    }
    if (parameter === 37446) {
        return 'Intel(R) Iris(TM) Graphics 6100';
    }
    return getParameter(parameter);
};

// 伪造Canvas指纹
const toDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    if (type === 'image/png') {
        return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
    }
    return toDataURL.apply(this, arguments);
};

console.log('🛡️ 快手反检测脚本已加载');
"""

# 错误处理配置
KUAISHOU_ERROR_HANDLING = {
    'common_errors': {
        'login_required': '需要登录',
        'upload_failed': '上传失败',
        'network_error': '网络错误',
        'timeout_error': '操作超时',
        'element_not_found': '元素未找到',
    },
    'retry_errors': [
        'timeout',
        'network',
        'element_not_found',
        'stale_element',
    ],
    'fatal_errors': [
        'login_required',
        'account_banned',
        'invalid_video_format',
    ]
}

# 成功指示器
KUAISHOU_SUCCESS_INDICATORS = [
    '发布成功',
    '发布完成',
    '上传成功',
    '提交成功',
    'success',
    'complete',
    'published'
]

# 失败指示器
KUAISHOU_FAILURE_INDICATORS = [
    '发布失败',
    '上传失败',
    '错误',
    '失败',
    'error',
    'failed',
    'fail'
]
