#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键发布功能完整测试套件运行器
运行所有相关测试并生成综合报告
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入测试模块
from test_one_click_publish_complete import run_complete_test
from test_one_click_publish_functional import run_functional_tests
from test_one_click_publish_integration import run_integration_tests

def print_header(title):
    """打印测试标题"""
    print("\n" + "=" * 80)
    print(f"🚀 {title}")
    print("=" * 80)

def print_section(title):
    """打印测试章节"""
    print("\n" + "-" * 60)
    print(f"📋 {title}")
    print("-" * 60)

def run_system_check():
    """运行系统检查"""
    print_section("系统环境检查")
    
    checks = []
    
    # 检查Python版本
    python_version = sys.version_info
    python_ok = python_version >= (3, 7)
    checks.append(("Python版本", f"{python_version.major}.{python_version.minor}.{python_version.micro}", python_ok))
    
    # 检查关键文件
    key_files = [
        "src/gui/simple_one_click_publish_tab.py",
        "src/services/simple_publisher_service.py",
        "src/services/platform_publisher/publisher_factory.py",
        "src/services/platform_publisher/base_publisher.py"
    ]
    
    for file_path in key_files:
        full_path = project_root / file_path
        file_exists = full_path.exists()
        checks.append(("关键文件", file_path, file_exists))
    
    # 检查依赖模块
    dependencies = [
        ("json", "标准库"),
        ("pathlib", "标准库"),
        ("logging", "标准库")
    ]
    
    for module_name, description in dependencies:
        try:
            __import__(module_name)
            dep_ok = True
        except ImportError:
            dep_ok = False
        checks.append(("依赖模块", f"{module_name} ({description})", dep_ok))
    
    # 输出检查结果
    all_passed = True
    for check_type, item, status in checks:
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {check_type:12} - {item}")
        if not status:
            all_passed = False
    
    if all_passed:
        print("\n🎉 系统环境检查全部通过")
    else:
        print("\n⚠️ 系统环境检查发现问题，可能影响测试结果")
    
    return all_passed

def run_pre_test_validation():
    """运行测试前验证"""
    print_section("测试前验证")
    
    validations = []
    
    try:
        # 验证服务初始化
        from src.services.simple_publisher_service import SimplePublisherService
        publisher = SimplePublisherService()
        platforms = publisher.get_supported_platforms()
        validations.append(("发布服务初始化", f"支持{len(platforms)}个平台", True))
    except Exception as e:
        validations.append(("发布服务初始化", f"失败: {e}", False))
    
    try:
        # 验证平台工厂
        from src.services.platform_publisher.publisher_factory import PublisherFactory
        factory_platforms = PublisherFactory.get_supported_platforms()
        validations.append(("平台工厂", f"支持{len(factory_platforms)}个平台", True))
    except Exception as e:
        validations.append(("平台工厂", f"失败: {e}", False))
    
    try:
        # 验证元数据模型
        from src.services.platform_publisher.base_publisher import VideoMetadata
        metadata = VideoMetadata(
            title="测试",
            description="测试",
            tags=["测试"],
            category="测试",
            privacy="public"
        )
        validations.append(("元数据模型", "创建成功", True))
    except Exception as e:
        validations.append(("元数据模型", f"失败: {e}", False))
    
    # 输出验证结果
    all_passed = True
    for validation_type, result, status in validations:
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {validation_type:15} - {result}")
        if not status:
            all_passed = False
    
    return all_passed

def generate_test_report(results):
    """生成测试报告"""
    print_section("测试报告生成")
    
    # 计算总体统计
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    # 生成报告数据
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': success_rate
        },
        'test_results': [
            {
                'test_name': name,
                'status': 'PASS' if success else 'FAIL',
                'success': success
            }
            for name, success in results
        ]
    }
    
    # 保存JSON报告
    report_file = project_root / "tests" / "test_report.json"
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        print(f"   📄 JSON报告已保存: {report_file}")
    except Exception as e:
        print(f"   ❌ JSON报告保存失败: {e}")
    
    # 生成文本报告
    text_report = f"""
# 一键发布功能测试报告

## 测试概要
- 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 总测试数: {total_tests}
- 通过测试: {passed_tests}
- 失败测试: {failed_tests}
- 成功率: {success_rate:.1f}%

## 详细结果
"""
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        text_report += f"- {test_name}: {status}\n"
    
    text_report += f"""
## 结论
"""
    
    if success_rate == 100:
        text_report += "🎉 所有测试通过！一键发布功能运行完全正常。"
    elif success_rate >= 80:
        text_report += "⚠️ 大部分测试通过，但有一些问题需要关注。"
    else:
        text_report += "❌ 测试失败较多，需要修复问题后重新测试。"
    
    # 保存文本报告
    text_report_file = project_root / "tests" / "test_report.md"
    try:
        with open(text_report_file, 'w', encoding='utf-8') as f:
            f.write(text_report)
        print(f"   📄 文本报告已保存: {text_report_file}")
    except Exception as e:
        print(f"   ❌ 文本报告保存失败: {e}")
    
    return report_data

def main():
    """主测试运行函数"""
    start_time = time.time()
    
    print_header("一键发布功能完整测试套件")
    print(f"📅 测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 系统检查
    system_ok = run_system_check()
    if not system_ok:
        print("\n⚠️ 系统环境检查未完全通过，但继续执行测试...")
    
    # 测试前验证
    validation_ok = run_pre_test_validation()
    if not validation_ok:
        print("\n⚠️ 测试前验证未完全通过，但继续执行测试...")
    
    # 运行测试套件
    test_results = []
    
    print_header("执行测试套件")
    
    # 1. 完整性测试
    print_section("1. 完整性测试")
    try:
        complete_result = run_complete_test()
        test_results.append(("完整性测试", complete_result))
    except Exception as e:
        print(f"❌ 完整性测试异常: {e}")
        test_results.append(("完整性测试", False))
    
    # 2. 功能性测试
    print_section("2. 功能性测试")
    try:
        functional_result = run_functional_tests()
        test_results.append(("功能性测试", functional_result))
    except Exception as e:
        print(f"❌ 功能性测试异常: {e}")
        test_results.append(("功能性测试", False))
    
    # 3. 集成测试
    print_section("3. 集成测试")
    try:
        integration_result = run_integration_tests()
        test_results.append(("集成测试", integration_result))
    except Exception as e:
        print(f"❌ 集成测试异常: {e}")
        test_results.append(("集成测试", False))
    
    # 生成测试报告
    report_data = generate_test_report(test_results)
    
    # 输出最终结果
    end_time = time.time()
    duration = end_time - start_time
    
    print_header("测试完成")
    print(f"📅 测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️ 总耗时: {duration:.2f} 秒")
    
    print(f"\n📊 最终结果:")
    print(f"   总测试套件: {report_data['summary']['total_tests']}")
    print(f"   通过套件: {report_data['summary']['passed_tests']}")
    print(f"   失败套件: {report_data['summary']['failed_tests']}")
    print(f"   成功率: {report_data['summary']['success_rate']:.1f}%")
    
    success_rate = report_data['summary']['success_rate']
    if success_rate == 100:
        print("\n🎉 恭喜！所有测试套件通过，一键发布功能运行完全正常！")
        return 0
    elif success_rate >= 80:
        print("\n⚠️ 大部分测试通过，但建议检查失败的测试项目。")
        return 1
    else:
        print("\n❌ 测试失败较多，需要修复问题后重新测试。")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
