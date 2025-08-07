
# GUI调试说明

## 问题诊断步骤

1. **检查翻译是否被触发**
   在GUI中生成配音时，查看日志中是否有：
   ```
   🔧 [DEBUG] 需要翻译，开始翻译流程...
   ```

2. **检查翻译是否成功**
   查看日志中是否有：
   ```
   🔧 [DEBUG] 翻译成功，已设置display_text: ...
   ```

3. **检查传递给TTS的文本**
   在VoiceGenerationThread中，检查实际使用的文本：
   ```python
   text_to_generate = segment.get('translated_text', segment.get('original_text', ...))
   ```

## 可能的问题和解决方案

### 问题1: 翻译没有被触发
**症状**: 日志中没有 "需要翻译，开始翻译流程..."
**原因**: 
- voice_language_combo.currentData() 返回值不是 "en-US"
- 语言检测结果不正确

**解决方案**:
```python
# 在GUI中添加调试代码
target_language_str = self.voice_language_combo.currentData()
print(f"DEBUG: target_language_str = {target_language_str}")
print(f"DEBUG: target_language = {target_language}")
```

### 问题2: 翻译失败
**症状**: 有翻译日志但没有 "翻译成功" 日志
**原因**: 
- API Manager未正确初始化
- 翻译服务异常

**解决方案**:
```python
# 检查翻译服务状态
print(f"DEBUG: bilingual_voice_service.api_manager = {self.bilingual_voice_service.api_manager}")
print(f"DEBUG: bilingual_voice_service.llm_service = {self.bilingual_voice_service.llm_service}")
```

### 问题3: 翻译文本没有传递给TTS
**症状**: 翻译成功但仍然生成中文配音
**原因**: VoiceGenerationThread中的文本获取逻辑有问题

**解决方案**:
在VoiceGenerationThread.run()中添加调试：
```python
text_to_generate = segment.get('translated_text', segment.get('original_text', ...))
print(f"DEBUG: text_to_generate = {text_to_generate}")
print(f"DEBUG: segment keys = {list(segment.keys())}")
```

## 快速修复建议

如果翻译功能正常但配音仍然失败，尝试以下修复：

1. **强制使用英文文本**:
```python
# 在VoiceGenerationThread中
if target_language == LanguageCode.ENGLISH:
    # 强制使用翻译文本
    text_to_generate = segment.get('translated_text') or segment.get('display_text') or segment.get('original_text', '')
```

2. **验证音色ID**:
```python
# 确保使用正确的音色ID
voice_id = self.voice_combo.currentData()
if not voice_id or not voice_id.startswith('en-US-'):
    voice_id = 'en-US-AvaNeural'  # 使用默认英文音色
```

3. **添加文本语言验证**:
```python
# 在生成配音前验证文本语言
import re
chinese_chars = len(re.findall(r'[一-鿿]', text_to_generate))
if chinese_chars > 0 and target_language == LanguageCode.ENGLISH:
    logger.warning(f"警告：英文配音模式下检测到中文字符 ({chinese_chars} 个)")
```
