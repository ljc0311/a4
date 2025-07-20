#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
禁用百度翻译，避免余额不足的错误提示
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def disable_baidu_translation():
    """禁用百度翻译配置"""
    print("🔧 禁用百度翻译配置")
    print("=" * 50)
    
    try:
        # 检查百度翻译配置文件
        baidu_config_file = project_root / "src" / "utils" / "baidu_translator.py"
        
        if baidu_config_file.exists():
            print(f"📋 找到百度翻译文件: {baidu_config_file}")
            
            # 读取文件内容
            with open(baidu_config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否已经禁用
            if "def is_configured():" in content and "return False" in content:
                print("✅ 百度翻译已经被禁用")
                return True
            
            # 修改is_configured函数，直接返回False
            if "def is_configured():" in content:
                # 找到函数并替换
                lines = content.split('\n')
                new_lines = []
                in_function = False
                function_indent = 0
                
                for line in lines:
                    if "def is_configured():" in line:
                        new_lines.append(line)
                        new_lines.append("    \"\"\"检查百度翻译是否配置 - 已禁用\"\"\"")
                        new_lines.append("    return False  # 🔧 禁用百度翻译，避免余额不足错误")
                        in_function = True
                        function_indent = len(line) - len(line.lstrip())
                        continue
                    
                    if in_function:
                        # 检查是否还在函数内
                        if line.strip() == "":
                            new_lines.append(line)
                            continue
                        
                        current_indent = len(line) - len(line.lstrip())
                        if current_indent <= function_indent and line.strip():
                            # 函数结束
                            in_function = False
                            new_lines.append(line)
                        # 跳过函数内的原始代码
                    else:
                        new_lines.append(line)
                
                # 写回文件
                new_content = '\n'.join(new_lines)
                with open(baidu_config_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print("✅ 已禁用百度翻译配置")
                return True
            else:
                print("⚠️ 未找到is_configured函数")
                return False
        else:
            print("⚠️ 未找到百度翻译配置文件")
            return False
            
    except Exception as e:
        print(f"❌ 禁用百度翻译失败: {e}")
        return False


def test_translation_priority():
    """测试翻译优先级"""
    print("\n🔍 测试翻译优先级")
    print("=" * 50)
    
    try:
        from src.utils.enhanced_translator import translate_text_enhanced
        
        # 测试翻译
        test_text = "测试翻译"
        print(f"📋 测试文本: {test_text}")
        
        result = translate_text_enhanced(test_text, 'zh', 'en')
        
        if result and result != test_text:
            print(f"✅ 翻译成功: {test_text} -> {result}")
            return True
        else:
            print(f"⚠️ 翻译失败或未改变: {result}")
            return False
            
    except Exception as e:
        print(f"❌ 翻译测试失败: {e}")
        return False


def create_translation_config():
    """创建优化的翻译配置"""
    print("\n🔧 创建优化的翻译配置")
    print("=" * 50)
    
    try:
        config_content = '''# 翻译服务配置
# 优先级：智谱AI > Google翻译 > 百度翻译(已禁用)

TRANSLATION_CONFIG = {
    "priority": ["zhipu", "google", "baidu"],
    "baidu_enabled": False,  # 禁用百度翻译
    "google_enabled": True,
    "zhipu_enabled": True,
    "timeout": 30,
    "retry_count": 2
}

# 翻译质量配置
QUALITY_CONFIG = {
    "min_length": 1,
    "max_length": 5000,
    "preserve_formatting": True,
    "remove_extra_spaces": True
}
'''
        
        config_file = project_root / "config" / "translation_config.py"
        config_file.parent.mkdir(exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print(f"✅ 翻译配置已创建: {config_file}")
        return True
        
    except Exception as e:
        print(f"❌ 创建翻译配置失败: {e}")
        return False


def main():
    """主函数"""
    print("🔧 禁用百度翻译，优化翻译配置")
    print("避免余额不足的错误提示，优先使用智谱AI")
    print()
    
    tasks = [
        ("禁用百度翻译", disable_baidu_translation),
        ("测试翻译优先级", test_translation_priority),
        ("创建翻译配置", create_translation_config),
    ]
    
    results = {}
    
    for task_name, task_func in tasks:
        print(f"🧪 执行任务: {task_name}")
        try:
            results[task_name] = task_func()
        except Exception as e:
            print(f"💥 任务 {task_name} 异常: {e}")
            results[task_name] = False
    
    # 显示结果
    print("\n" + "=" * 50)
    print("📊 任务结果汇总")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for task_name, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{task_name:<20}: {status}")
        if success:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 项任务成功")
    
    if passed == total:
        print("\n🎉 翻译配置优化完成！")
        print("\n💡 现在的翻译策略:")
        print("1. 优先使用智谱AI进行翻译")
        print("2. 智谱AI失败时使用Google翻译")
        print("3. 不再使用百度翻译，避免余额错误")
        print("4. 翻译质量更高，错误提示更少")
        
        print("\n📋 使用说明:")
        print("- YouTube发布时会自动使用新的翻译策略")
        print("- 不会再看到百度翻译余额不足的错误")
        print("- 翻译质量和速度都会有所提升")
    else:
        print("\n🔧 部分任务失败，请检查配置")


if __name__ == "__main__":
    main()
