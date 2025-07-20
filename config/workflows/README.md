# ComfyUI 工作流配置说明

本目录用于存放 ComfyUI 工作流配置文件，支持多种不同的图像生成工作流。

## 工作流配置文件格式

每个工作流配置文件都是一个 JSON 文件，包含以下结构：

```json
{
  "name": "工作流名称",
  "description": "工作流描述",
  "workflow": {
    // ComfyUI 工作流的完整 JSON 定义
  },
  "parameters": {
    "参数名称": {
      "type": "参数类型",
      "default": "默认值",
      "description": "参数描述",
      "min": "最小值（数值类型）",
      "max": "最大值（数值类型）",
      "options": ["选项1", "选项2"] // 选择类型的选项
    }
  }
}
```

## 支持的参数类型

- `int`: 整数类型，支持 min/max 范围
- `float`: 浮点数类型，支持 min/max 范围
- `string`: 字符串类型
- `select`: 选择类型，需要提供 options 数组
- `boolean`: 布尔类型

## 如何添加新的工作流

1. 在 ComfyUI 中设计并测试你的工作流
2. 导出工作流的 JSON 文件
3. 在本目录创建新的配置文件（如 `my_workflow.json`）
4. 按照上述格式填写配置信息
5. 将导出的工作流 JSON 放入 `workflow` 字段
6. 定义可配置的参数
7. 重启应用或点击刷新按钮加载新工作流

## 现有工作流

- `default_workflow.json`: 基础 SD1.5 工作流
- `kuaishou_workflow.json`: 快手文生图工作流模板
- `flux_workflow.json`: Flux 工作流模板

## 注意事项

1. 工作流 JSON 中的节点 ID 必须与参数配置中引用的 ID 一致
2. 参数名称将作为 UI 中的标签显示
3. 确保工作流在 ComfyUI 中能正常运行
4. 建议为每个工作流提供详细的描述信息