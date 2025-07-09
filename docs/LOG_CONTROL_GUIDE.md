# 日志控制指南

本指南介绍如何使用AI视频生成器的日志控制功能来减少正常日志输出，同时保留完整的异常日志记录。

## 功能概述

新的日志控制系统提供了以下功能：
- **智能日志级别管理**：区分控制台输出和文件记录
- **三种预设模式**：正常、安静、详细模式
- **完整异常保留**：确保所有错误和警告信息都被记录
- **动态配置**：无需重启应用即可调整日志设置
- **图形界面控制**：通过GUI面板轻松管理
- **命令行工具**：支持脚本化管理

## 使用方法

### 1. 图形界面控制（推荐）

在应用程序的设置页面中找到"日志控制"面板：

- **正常模式**（推荐）：控制台只显示警告和错误，文件记录所有日志
- **安静模式**：控制台只显示错误，最小化输出干扰
- **详细模式**：显示所有日志信息，用于调试问题

### 2. 命令行控制

使用项目根目录下的 `log_control.py` 脚本：

```bash
# 设置为正常模式（推荐）
python log_control.py --mode normal

# 设置为安静模式
python log_control.py --mode quiet

# 设置为详细模式（调试用）
python log_control.py --mode verbose

# 单独设置控制台日志级别
python log_control.py --console WARNING

# 单独设置文件日志级别
python log_control.py --file DEBUG

# 查看当前配置
python log_control.py --status

# 重置为默认配置
python log_control.py --reset
```

### 3. 程序化控制

在代码中使用日志配置管理器：

```python
from src.utils.log_config_manager import (
    enable_normal_mode,
    enable_quiet_mode,
    enable_verbose_mode,
    set_console_level,
    set_file_level
)

# 启用正常模式
enable_normal_mode()

# 或者单独设置级别
set_console_level('WARNING')
set_file_level('DEBUG')
```

## 日志级别说明

| 级别 | 描述 | 包含内容 |
|------|------|----------|
| DEBUG | 调试信息 | 所有日志信息，包括详细的调试数据 |
| INFO | 一般信息 | 程序运行的一般信息和状态更新 |
| WARNING | 警告信息 | 潜在问题和需要注意的情况 |
| ERROR | 错误信息 | 程序错误和异常情况 |
| CRITICAL | 严重错误 | 导致程序无法继续运行的严重错误 |

## 模式详细说明

### 正常模式（推荐）
- **控制台输出**：WARNING 及以上级别
- **文件记录**：DEBUG 及以上级别（完整记录）
- **适用场景**：日常使用，既减少了终端干扰，又保留了完整的日志文件

### 安静模式
- **控制台输出**：ERROR 及以上级别
- **文件记录**：WARNING 及以上级别
- **适用场景**：需要最小化输出的环境，如生产部署

### 详细模式
- **控制台输出**：DEBUG 及以上级别（所有信息）
- **文件记录**：DEBUG 及以上级别（所有信息）
- **适用场景**：问题调试和开发阶段

## 配置文件

日志配置保存在 `config/log_config.json` 文件中：

```json
{
  "console_level": "WARNING",
  "file_level": "DEBUG",
  "error_file_level": "ERROR",
  "enable_console": true,
  "enable_file": true,
  "enable_error_file": true,
  "suppress_repeated_logs": true,
  "suppress_threshold": 10,
  "suppress_interval": 60
}
```

## 日志文件位置

- **主日志文件**：`logs/system.log`（包含所有日志）
- **错误日志文件**：`logs/errors.log`（只包含错误信息）
- **日志轮转**：文件大小超过限制时自动轮转，保留历史版本

## 异常处理保证

无论设置什么日志级别，以下信息都会被完整保留：

1. **所有ERROR和CRITICAL级别的日志**
2. **异常堆栈跟踪信息**
3. **程序崩溃和错误详情**
4. **API调用失败信息**
5. **文件操作错误**
6. **网络连接问题**

## 性能优化

新的日志系统还包含以下性能优化：

- **重复日志抑制**：相同日志消息在短时间内重复出现时会被抑制
- **结构化日志**：文件中的日志采用JSON格式，便于分析
- **异步写入**：减少日志记录对程序性能的影响
- **智能轮转**：自动管理日志文件大小和数量

## 故障排除

### 问题：日志配置不生效
**解决方案**：
1. 检查 `config/log_config.json` 文件是否存在
2. 确保有写入权限
3. 重启应用程序
4. 使用 `--reset` 参数重置配置

### 问题：找不到某些日志信息
**解决方案**：
1. 检查文件日志级别设置
2. 查看 `logs/system.log` 文件
3. 临时启用详细模式进行调试

### 问题：日志文件过大
**解决方案**：
1. 系统会自动轮转日志文件
2. 可以手动删除旧的日志文件
3. 调整日志级别减少记录量

## 最佳实践

1. **日常使用**：建议使用正常模式
2. **问题调试**：临时切换到详细模式
3. **生产环境**：考虑使用安静模式
4. **定期清理**：定期检查和清理旧日志文件
5. **监控异常**：定期查看错误日志文件

## 技术实现

- **配置管理**：`src/utils/log_config_manager.py`
- **日志记录器**：`src/utils/logger.py` 和 `src/utils/optimized_logger.py`
- **GUI控制面板**：`src/gui/log_control_panel.py`
- **命令行工具**：`log_control.py`

通过这套完整的日志控制系统，您可以根据需要灵活调整日志输出，既减少了不必要的信息干扰，又确保了重要的异常信息得到完整保留。