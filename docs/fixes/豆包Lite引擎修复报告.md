# 豆包Lite引擎修复报告

## 🎯 问题描述

用户在使用豆包Lite引擎时遇到以下错误：

```
[15:31:21] [INFO] 正在初始化视频引擎 doubao_seedance_lite...
[15:31:21] [ERROR] 豆包Lite API连接测试失败，状态码: 404
[15:31:21] [ERROR] 豆包Lite视频引擎初始化失败
[15:31:21] [ERROR] 视频引擎 doubao_seedance_lite 初始化失败，状态: VideoEngineStatus.ERROR
```

## 🔍 问题分析

经过分析，发现了以下几个问题：

1. **模型ID错误**: 使用了错误的模型ID `doubao-seedance-1-0-lite`
2. **API请求格式错误**: 连接测试使用了错误的请求格式
3. **API密钥获取不完整**: 缺少从环境变量获取API密钥的逻辑
4. **状态枚举错误**: 使用了不存在的 `VideoEngineStatus.READY` 状态
5. **会话管理问题**: 初始化失败时未正确清理HTTP会话

## ✅ 修复内容

### 1. 修正模型ID

**文件**: `src/models/video_engines/engines/doubao_lite_engine.py`

```python
# 修复前
self.model = config.get('model', 'doubao-seedance-1-0-lite')

# 修复后
self.model = config.get('model', 'doubao-seedance-1-0-lite-i2v-250428')
```

### 2. 修复API密钥获取逻辑

添加了 `_get_api_key` 方法，支持从配置和环境变量获取API密钥：

```python
def _get_api_key(self, config: Dict[str, Any]) -> str:
    """获取API密钥"""
    try:
        # 优先从配置中获取
        if config.get('api_key'):
            return config['api_key']
        
        # 从环境变量获取ARK_API_KEY
        import os
        api_key = os.getenv('ARK_API_KEY')
        if api_key:
            logger.info("从环境变量ARK_API_KEY获取到豆包API密钥")
            return api_key
        
        logger.warning("未找到豆包API密钥，请在配置中设置或设置ARK_API_KEY环境变量")
        return ''
        
    except Exception as e:
        logger.warning(f"获取豆包API密钥失败: {e}")
        return ''
```

### 3. 修复API连接测试

修正了连接测试的请求格式，使用豆包API的正确格式：

```python
# 修复前 - 错误的messages格式
test_data = {
    "model": self.model,
    "messages": [
        {
            "role": "user",
            "content": [...]
        }
    ]
}

# 修复后 - 正确的content格式
test_data = {
    "model": self.model,
    "content": [
        {
            "type": "text",
            "text": "测试连接 --ratio adaptive --dur 5"
        }
    ]
}
```

### 4. 修复状态枚举

```python
# 修复前
self.status = VideoEngineStatus.READY

# 修复后
self.status = VideoEngineStatus.IDLE
```

### 5. 改进会话管理

在初始化失败时正确清理HTTP会话：

```python
except Exception as e:
    logger.error(f"豆包Lite视频引擎初始化异常: {e}")
    self.status = VideoEngineStatus.ERROR
    # 清理会话
    if self.session and not self.session.closed:
        await self.session.close()
        self.session = None
    return False
```

### 6. 更新配置文件

**文件**: `config/video_generation_config.py`

```python
'doubao_seedance_lite': {
    'enabled': True,  # 启用豆包Lite引擎
    'api_key': '0d5ead96-f0f9-4f0f-90b7-b76a743d6bd6',
    'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
    'model': 'doubao-seedance-1-0-lite-i2v-250428',  # 正确的模型ID
    # ... 其他配置
}
```

### 7. 更新设置界面

**文件**: `src/gui/video_generation_settings_widget.py`

更新了设置界面中的模型显示和保存逻辑。

## 🧪 测试验证

创建了测试脚本验证修复效果：

```
✅ 引擎实例创建成功
✅ API密钥获取成功（支持配置和环境变量）
✅ 引擎初始化成功
✅ API连接测试通过
✅ 会话管理正常
```

## 📊 修复结果

### 修复前
- ❌ 404错误 - 模型ID不正确
- ❌ 初始化失败
- ❌ 会话泄漏警告

### 修复后
- ✅ API连接成功
- ✅ 引擎初始化成功
- ✅ 状态正常 (IDLE)
- ✅ 会话管理正常

## 🚀 使用指南

### 方式1: 配置文件设置API密钥

在 `config/video_generation_config.py` 中设置：

```python
'doubao_seedance_lite': {
    'enabled': True,
    'api_key': 'your-api-key-here',
    # ... 其他配置
}
```

### 方式2: 环境变量设置API密钥

```bash
export ARK_API_KEY=your-api-key-here
```

### 选择引擎

在视频生成界面选择 "💰 豆包视频生成 Lite版 (便宜33%)"

## 📝 相关文件

### 修改的文件
- `src/models/video_engines/engines/doubao_lite_engine.py`
- `config/video_generation_config.py`
- `src/gui/video_generation_settings_widget.py`
- `src/models/video_engines/video_engine_manager.py`
- `src/gui/video_generation_tab.py`

### 引擎特性
- **模型**: doubao-seedance-1-0-lite-i2v-250428
- **成本**: 比Pro版便宜33% (0.013元/秒 vs 0.02元/秒)
- **时长**: 支持5秒和10秒
- **分辨率**: 480p, 720p, 1080p
- **并发**: 最多10个任务

## 🎉 总结

豆包Lite引擎现已完全修复，用户可以正常使用该引擎进行视频生成。主要改进包括：

1. ✅ 正确的模型ID
2. ✅ 完善的API密钥获取机制
3. ✅ 正确的API请求格式
4. ✅ 完善的错误处理和会话管理
5. ✅ 完整的配置和UI支持

**修复完成时间**: 2024年7月12日  
**状态**: ✅ 完全修复
