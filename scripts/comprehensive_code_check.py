#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面的代码检查工具
检查项目中的常见BUG和语法错误
"""

import os
import ast
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

class CodeChecker:
    """代码检查器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = []
        
    def check_all(self) -> List[Dict[str, Any]]:
        """执行所有检查"""
        print("🔍 开始全面代码检查...")
        
        # 获取所有Python文件
        python_files = list(self.project_root.rglob("*.py"))
        print(f"📁 找到 {len(python_files)} 个Python文件")
        
        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue
                
            print(f"🔍 检查文件: {file_path.relative_to(self.project_root)}")
            self._check_file(file_path)
        
        return self.issues
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """判断是否应该跳过文件"""
        skip_patterns = [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "env",
            "build",
            "dist",
            ".pytest_cache"
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _check_file(self, file_path: Path):
        """检查单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 语法检查
            self._check_syntax(file_path, content)
            
            # 导入检查
            self._check_imports(file_path, content)
            
            # 异常处理检查
            self._check_exception_handling(file_path, content)
            
            # 资源管理检查
            self._check_resource_management(file_path, content)
            
            # 异步代码检查
            self._check_async_code(file_path, content)
            
            # GUI线程安全检查
            self._check_gui_thread_safety(file_path, content)
            
        except Exception as e:
            self._add_issue(file_path, "文件读取错误", f"无法读取文件: {e}", "critical")
    
    def _check_syntax(self, file_path: Path, content: str):
        """检查语法错误"""
        try:
            ast.parse(content)
        except SyntaxError as e:
            self._add_issue(
                file_path, "语法错误", 
                f"第{e.lineno}行: {e.msg}", 
                "critical"
            )
    
    def _check_imports(self, file_path: Path, content: str):
        """检查导入问题"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 检查循环导入风险
            if line.startswith('from') and 'import' in line:
                if 'src.' in line and file_path.name != '__init__.py':
                    # 检查是否可能存在循环导入
                    imported_module = line.split('from')[1].split('import')[0].strip()
                    if self._check_potential_circular_import(file_path, imported_module):
                        self._add_issue(
                            file_path, "潜在循环导入", 
                            f"第{i}行: {line}", 
                            "warning"
                        )
            
            # 检查未使用的导入（简单检查）
            if line.startswith('import ') or line.startswith('from '):
                if 'as ' in line:
                    alias = line.split(' as ')[-1].strip()
                    if alias not in content:
                        self._add_issue(
                            file_path, "未使用的导入", 
                            f"第{i}行: {line}", 
                            "info"
                        )
    
    def _check_exception_handling(self, file_path: Path, content: str):
        """检查异常处理"""
        lines = content.split('\n')
        
        in_try_block = False
        has_except = False
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            if line.startswith('try:'):
                in_try_block = True
                has_except = False
            elif line.startswith('except'):
                has_except = True
                # 检查裸露的except
                if line == 'except:':
                    self._add_issue(
                        file_path, "裸露的except", 
                        f"第{i}行: 应该指定具体的异常类型", 
                        "warning"
                    )
            elif in_try_block and (line.startswith('def ') or line.startswith('class ') or line == ''):
                if not has_except:
                    self._add_issue(
                        file_path, "缺少异常处理", 
                        f"try块缺少对应的except", 
                        "warning"
                    )
                in_try_block = False
    
    def _check_resource_management(self, file_path: Path, content: str):
        """检查资源管理"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 检查文件操作是否使用with语句
            if 'open(' in line and 'with ' not in line:
                if '=' in line:  # 赋值语句
                    self._add_issue(
                        file_path, "资源管理问题", 
                        f"第{i}行: 建议使用with语句管理文件资源", 
                        "warning"
                    )
            
            # 检查数据库连接
            if any(db_op in line for db_op in ['connect(', 'cursor(', 'execute(']):
                if 'with ' not in line and 'close()' not in content:
                    self._add_issue(
                        file_path, "资源管理问题", 
                        f"第{i}行: 数据库连接可能未正确关闭", 
                        "warning"
                    )
    
    def _check_async_code(self, file_path: Path, content: str):
        """检查异步代码问题"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 检查await在非async函数中使用
            if 'await ' in line:
                # 查找包含此行的函数定义
                line_pos = content.find(line)
                if line_pos != -1:
                    func_start = content.rfind('def ', 0, line_pos)
                    if func_start != -1:
                        func_end = content.find('\n', func_start)
                        if func_end != -1:
                            func_line = content[func_start:func_end]
                            if 'async def' not in func_line and 'def ' in func_line:
                                self._add_issue(
                                    file_path, "异步代码错误",
                                    f"第{i}行: await在非async函数中使用",
                                    "error"
                                )
            
            # 检查异步函数调用未使用await
            if re.search(r'(\w+)\s*\(.*\)', line):
                if 'async def' in content and 'await' not in line:
                    # 这是一个简化的检查，实际需要更复杂的AST分析
                    pass
    
    def _check_gui_thread_safety(self, file_path: Path, content: str):
        """检查GUI线程安全问题"""
        if 'PyQt5' not in content and 'PySide2' not in content:
            return
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 检查在非主线程中直接操作GUI
            if any(gui_op in line for gui_op in ['.setText(', '.setVisible(', '.update(', '.repaint()']):
                if 'QThread' in content or 'threading' in content:
                    self._add_issue(
                        file_path, "GUI线程安全", 
                        f"第{i}行: 可能在非主线程中操作GUI", 
                        "warning"
                    )
    
    def _check_potential_circular_import(self, file_path: Path, imported_module: str) -> bool:
        """检查潜在的循环导入"""
        # 简化的循环导入检查
        try:
            module_path = self.project_root / imported_module.replace('.', '/') / '__init__.py'
            if not module_path.exists():
                module_path = self.project_root / (imported_module.replace('.', '/') + '.py')
            
            if module_path.exists():
                with open(module_path, 'r', encoding='utf-8') as f:
                    module_content = f.read()
                
                # 检查是否导入了当前文件的模块
                current_module = str(file_path.relative_to(self.project_root)).replace('/', '.').replace('.py', '')
                return current_module in module_content
        except:
            pass
        
        return False
    
    def _add_issue(self, file_path: Path, issue_type: str, description: str, severity: str):
        """添加问题"""
        self.issues.append({
            'file': str(file_path.relative_to(self.project_root)),
            'type': issue_type,
            'description': description,
            'severity': severity
        })

def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    checker = CodeChecker(str(project_root))
    
    issues = checker.check_all()
    
    print("\n" + "=" * 60)
    print("代码检查结果")
    print("=" * 60)
    
    if not issues:
        print("✅ 没有发现问题！")
        return
    
    # 按严重程度分组
    by_severity = {}
    for issue in issues:
        severity = issue['severity']
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(issue)
    
    # 显示结果
    severity_order = ['critical', 'error', 'warning', 'info']
    severity_icons = {
        'critical': '🚨',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    }
    
    for severity in severity_order:
        if severity in by_severity:
            print(f"\n{severity_icons[severity]} {severity.upper()} ({len(by_severity[severity])}个问题):")
            for issue in by_severity[severity][:10]:  # 只显示前10个
                print(f"  📁 {issue['file']}")
                print(f"     {issue['type']}: {issue['description']}")
            
            if len(by_severity[severity]) > 10:
                print(f"     ... 还有 {len(by_severity[severity]) - 10} 个问题")
    
    print(f"\n📊 总计发现 {len(issues)} 个问题")

if __name__ == "__main__":
    main()
