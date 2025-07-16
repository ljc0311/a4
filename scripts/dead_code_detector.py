#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
废弃代码和重复代码检测器
检查项目中未使用的函数、类、变量和重复的代码块
"""

import os
import ast
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict, Counter

class DeadCodeDetector:
    """废弃代码检测器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.all_files = []
        self.all_content = ""
        self.defined_functions = {}  # {name: [file_paths]}
        self.defined_classes = {}    # {name: [file_paths]}
        self.defined_variables = {}  # {name: [file_paths]}
        self.imports = {}           # {name: [file_paths]}
        self.function_calls = set()
        self.class_usages = set()
        self.variable_usages = set()
        self.import_usages = set()
        
        # 重复代码检测
        self.code_blocks = {}       # {hash: [locations]}
        self.duplicate_functions = []
        
        # 结果
        self.dead_code_issues = []
        self.duplicate_code_issues = []
    
    def analyze_project(self) -> Dict[str, Any]:
        """分析整个项目"""
        print("🔍 开始分析项目代码...")
        
        # 收集所有Python文件
        self._collect_files()
        
        # 第一遍：收集所有定义
        print("📝 收集函数、类和变量定义...")
        self._collect_definitions()
        
        # 第二遍：收集所有使用
        print("🔎 分析代码使用情况...")
        self._collect_usages()
        
        # 检测废弃代码
        print("🗑️ 检测废弃代码...")
        self._detect_dead_code()
        
        # 检测重复代码
        print("📋 检测重复代码...")
        self._detect_duplicate_code()
        
        return {
            'dead_code': self.dead_code_issues,
            'duplicate_code': self.duplicate_code_issues
        }
    
    def _collect_files(self):
        """收集所有Python文件"""
        self.all_files = []
        for file_path in self.project_root.rglob("*.py"):
            if self._should_skip_file(file_path):
                continue
            self.all_files.append(file_path)
        
        print(f"📁 找到 {len(self.all_files)} 个Python文件")
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """判断是否应该跳过文件"""
        skip_patterns = [
            "__pycache__", ".git", ".venv", "venv", "build", "dist",
            ".pytest_cache", "test_", "_test.py"
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _collect_definitions(self):
        """收集所有定义"""
        for file_path in self.all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.all_content += content + "\n"
                
                # 解析AST
                try:
                    tree = ast.parse(content)
                    self._analyze_ast_definitions(tree, file_path)
                except SyntaxError:
                    continue
                    
            except Exception as e:
                print(f"⚠️ 无法读取文件 {file_path}: {e}")
    
    def _analyze_ast_definitions(self, tree: ast.AST, file_path: Path):
        """分析AST中的定义"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                if not func_name.startswith('_'):  # 跳过私有函数
                    if func_name not in self.defined_functions:
                        self.defined_functions[func_name] = []
                    self.defined_functions[func_name].append(str(file_path))
            
            elif isinstance(node, ast.ClassDef):
                class_name = node.name
                if class_name not in self.defined_classes:
                    self.defined_classes[class_name] = []
                self.defined_classes[class_name].append(str(file_path))
            
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    import_name = alias.name
                    if import_name not in self.imports:
                        self.imports[import_name] = []
                    self.imports[import_name].append(str(file_path))
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        import_name = alias.name
                        if import_name not in self.imports:
                            self.imports[import_name] = []
                        self.imports[import_name].append(str(file_path))
    
    def _collect_usages(self):
        """收集所有使用情况"""
        # 简单的文本搜索方法（更准确的方法需要复杂的AST分析）
        for func_name in self.defined_functions:
            if self._is_used_in_code(func_name):
                self.function_calls.add(func_name)
        
        for class_name in self.defined_classes:
            if self._is_used_in_code(class_name):
                self.class_usages.add(class_name)
        
        for import_name in self.imports:
            if self._is_used_in_code(import_name):
                self.import_usages.add(import_name)
    
    def _is_used_in_code(self, name: str) -> bool:
        """检查名称是否在代码中被使用"""
        # 使用正则表达式检查使用情况
        patterns = [
            rf'\b{re.escape(name)}\s*\(',  # 函数调用
            rf'\b{re.escape(name)}\s*\.',  # 属性访问
            rf'\b{re.escape(name)}\s*=',   # 赋值
            rf'=\s*{re.escape(name)}\b',   # 被赋值
            rf'\b{re.escape(name)}\s*\[',  # 索引访问
            rf'isinstance\s*\([^,]+,\s*{re.escape(name)}\)',  # isinstance检查
            rf'class\s+\w+\s*\([^)]*{re.escape(name)}[^)]*\)',  # 继承
        ]
        
        for pattern in patterns:
            if re.search(pattern, self.all_content):
                return True
        
        return False
    
    def _detect_dead_code(self):
        """检测废弃代码"""
        # 检测未使用的函数
        for func_name, file_paths in self.defined_functions.items():
            if func_name not in self.function_calls:
                # 排除特殊函数
                if not self._is_special_function(func_name):
                    self.dead_code_issues.append({
                        'type': 'unused_function',
                        'name': func_name,
                        'files': file_paths,
                        'description': f'函数 {func_name} 似乎未被使用'
                    })
        
        # 检测未使用的类
        for class_name, file_paths in self.defined_classes.items():
            if class_name not in self.class_usages:
                # 排除特殊类
                if not self._is_special_class(class_name):
                    self.dead_code_issues.append({
                        'type': 'unused_class',
                        'name': class_name,
                        'files': file_paths,
                        'description': f'类 {class_name} 似乎未被使用'
                    })
        
        # 检测未使用的导入
        for import_name, file_paths in self.imports.items():
            if import_name not in self.import_usages:
                self.dead_code_issues.append({
                    'type': 'unused_import',
                    'name': import_name,
                    'files': file_paths,
                    'description': f'导入 {import_name} 似乎未被使用'
                })
    
    def _is_special_function(self, func_name: str) -> bool:
        """检查是否是特殊函数（不应被标记为废弃）"""
        special_functions = {
            'main', '__init__', '__str__', '__repr__', '__call__',
            '__enter__', '__exit__', '__del__', '__new__',
            'setUp', 'tearDown', 'test_', 'handle_', 'on_',
            'get_', 'set_', 'create_', 'update_', 'delete_'
        }
        
        return (func_name in special_functions or 
                func_name.startswith('test_') or
                func_name.startswith('handle_') or
                func_name.startswith('on_') or
                func_name.startswith('__'))
    
    def _is_special_class(self, class_name: str) -> bool:
        """检查是否是特殊类"""
        special_classes = {
            'QWidget', 'QMainWindow', 'QDialog', 'QThread',
            'Exception', 'Error', 'Config', 'Settings'
        }
        
        return (class_name in special_classes or
                class_name.endswith('Exception') or
                class_name.endswith('Error') or
                class_name.endswith('Config') or
                class_name.endswith('Settings') or
                class_name.endswith('Widget') or
                class_name.endswith('Dialog') or
                class_name.endswith('Window'))
    
    def _detect_duplicate_code(self):
        """检测重复代码"""
        function_signatures = defaultdict(list)
        
        for file_path in self.all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取函数体
                functions = self._extract_functions(content, file_path)
                
                for func_info in functions:
                    # 计算函数体的哈希
                    func_hash = self._calculate_code_hash(func_info['body'])
                    function_signatures[func_hash].append(func_info)
                    
            except Exception:
                continue
        
        # 找出重复的函数
        for func_hash, func_list in function_signatures.items():
            if len(func_list) > 1:
                # 检查是否真的是重复（不只是哈希碰撞）
                if self._are_functions_similar(func_list):
                    self.duplicate_code_issues.append({
                        'type': 'duplicate_function',
                        'functions': func_list,
                        'description': f'发现 {len(func_list)} 个相似的函数'
                    })
    
    def _extract_functions(self, content: str, file_path: Path) -> List[Dict]:
        """提取文件中的函数"""
        functions = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('def ') and not line.startswith('def _'):
                # 找到函数定义
                func_name = line.split('(')[0].replace('def ', '').strip()
                func_start = i
                
                # 找到函数结束
                indent_level = len(lines[i]) - len(lines[i].lstrip())
                func_end = i + 1
                
                while func_end < len(lines):
                    if lines[func_end].strip() == '':
                        func_end += 1
                        continue
                    
                    current_indent = len(lines[func_end]) - len(lines[func_end].lstrip())
                    if current_indent <= indent_level and lines[func_end].strip():
                        break
                    func_end += 1
                
                func_body = '\n'.join(lines[func_start:func_end])
                functions.append({
                    'name': func_name,
                    'file': str(file_path),
                    'start_line': func_start + 1,
                    'end_line': func_end,
                    'body': func_body
                })
                
                i = func_end
            else:
                i += 1
        
        return functions
    
    def _calculate_code_hash(self, code: str) -> str:
        """计算代码的哈希值"""
        # 标准化代码（移除空白和注释）
        normalized = re.sub(r'#.*', '', code)  # 移除注释
        normalized = re.sub(r'\s+', ' ', normalized)  # 标准化空白
        normalized = normalized.strip()
        
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _are_functions_similar(self, func_list: List[Dict]) -> bool:
        """检查函数是否真的相似"""
        if len(func_list) < 2:
            return False
        
        # 简单检查：如果函数体长度相似且内容相似
        first_func = func_list[0]
        first_body = first_func['body']
        
        for func in func_list[1:]:
            if abs(len(func['body']) - len(first_body)) > 50:  # 长度差异太大
                return False
        
        return True

def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    detector = DeadCodeDetector(str(project_root))
    
    results = detector.analyze_project()
    
    print("\n" + "=" * 60)
    print("废弃代码和重复代码检测结果")
    print("=" * 60)
    
    # 显示废弃代码
    dead_code = results['dead_code']
    if dead_code:
        print(f"\n🗑️ 发现 {len(dead_code)} 个废弃代码问题:")
        
        by_type = defaultdict(list)
        for issue in dead_code:
            by_type[issue['type']].append(issue)
        
        for issue_type, issues in by_type.items():
            type_names = {
                'unused_function': '未使用的函数',
                'unused_class': '未使用的类',
                'unused_import': '未使用的导入'
            }
            print(f"\n📋 {type_names.get(issue_type, issue_type)} ({len(issues)}个):")
            
            for issue in issues[:10]:  # 只显示前10个
                print(f"  • {issue['name']} - {issue['description']}")
                if len(issue['files']) == 1:
                    print(f"    文件: {Path(issue['files'][0]).name}")
                else:
                    print(f"    文件: {len(issue['files'])}个文件")
            
            if len(issues) > 10:
                print(f"    ... 还有 {len(issues) - 10} 个")
    else:
        print("\n✅ 没有发现废弃代码")
    
    # 显示重复代码
    duplicate_code = results['duplicate_code']
    if duplicate_code:
        print(f"\n📋 发现 {len(duplicate_code)} 个重复代码问题:")
        
        for i, issue in enumerate(duplicate_code[:5], 1):
            print(f"\n{i}. {issue['description']}:")
            for func in issue['functions']:
                print(f"   • {func['name']} 在 {Path(func['file']).name}:{func['start_line']}")
    else:
        print("\n✅ 没有发现明显的重复代码")
    
    print(f"\n📊 总结:")
    print(f"  废弃代码问题: {len(dead_code)}")
    print(f"  重复代码问题: {len(duplicate_code)}")

if __name__ == "__main__":
    main()
