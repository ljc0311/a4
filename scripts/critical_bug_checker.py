#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键BUG检查器
专门检查可能导致程序崩溃或数据丢失的严重问题
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Any

class CriticalBugChecker:
    """关键BUG检查器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.critical_issues = []
        
    def check_all(self) -> List[Dict[str, Any]]:
        """执行所有关键检查"""
        print("🚨 开始关键BUG检查...")
        
        python_files = list(self.project_root.rglob("*.py"))
        print(f"📁 检查 {len(python_files)} 个Python文件")
        
        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue
                
            self._check_file(file_path)
        
        return self.critical_issues
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """判断是否应该跳过文件"""
        skip_patterns = ["__pycache__", ".git", ".venv", "venv", "build", "dist"]
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _check_file(self, file_path: Path):
        """检查单个文件的关键问题"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查内存泄漏风险
            self._check_memory_leaks(file_path, content)
            
            # 检查资源泄漏
            self._check_resource_leaks(file_path, content)
            
            # 检查线程安全问题
            self._check_thread_safety(file_path, content)
            
            # 检查空指针引用
            self._check_null_references(file_path, content)
            
            # 检查数组越界风险
            self._check_array_bounds(file_path, content)
            
            # 检查死锁风险
            self._check_deadlock_risks(file_path, content)
            
        except Exception as e:
            self._add_critical_issue(file_path, "文件读取错误", f"无法读取文件: {e}")
    
    def _check_memory_leaks(self, file_path: Path, content: str):
        """检查内存泄漏风险"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 检查循环引用风险
            if 'self.' in line and '=' in line and 'self' in line.split('=')[1]:
                if 'parent' in line or 'child' in line:
                    self._add_critical_issue(
                        file_path, "潜在循环引用", 
                        f"第{i}行: {line} - 可能导致内存泄漏"
                    )
            
            # 检查大对象未释放
            if any(pattern in line for pattern in ['QPixmap(', 'QImage(', 'numpy.array(']):
                if 'del ' not in content and 'clear()' not in content:
                    self._add_critical_issue(
                        file_path, "大对象未释放", 
                        f"第{i}行: {line} - 大对象可能未正确释放"
                    )
    
    def _check_resource_leaks(self, file_path: Path, content: str):
        """检查资源泄漏"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 检查文件句柄泄漏
            if 'open(' in line and 'with ' not in line:
                if '.close()' not in content:
                    self._add_critical_issue(
                        file_path, "文件句柄泄漏", 
                        f"第{i}行: {line} - 文件可能未正确关闭"
                    )
            
            # 检查网络连接泄漏
            if any(pattern in line for pattern in ['requests.', 'urllib.', 'socket.']):
                if 'session' in line and 'close()' not in content:
                    self._add_critical_issue(
                        file_path, "网络连接泄漏", 
                        f"第{i}行: {line} - 网络连接可能未正确关闭"
                    )
    
    def _check_thread_safety(self, file_path: Path, content: str):
        """检查线程安全问题"""
        if 'threading' not in content and 'QThread' not in content:
            return
            
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 检查共享变量无锁访问
            if any(pattern in line for pattern in ['self.', 'global ', 'class ']):
                if 'threading' in content and 'lock' not in content.lower():
                    if any(op in line for op in ['+=', '-=', '*=', '/=', '=']):
                        self._add_critical_issue(
                            file_path, "线程安全问题", 
                            f"第{i}行: {line} - 共享变量可能存在竞态条件"
                        )
    
    def _check_null_references(self, file_path: Path, content: str):
        """检查空指针引用"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 检查未检查None的访问
            if '.' in line and 'if ' not in line and 'is not None' not in line:
                # 简单的模式匹配，可能有误报
                if re.search(r'\w+\.\w+\(', line):
                    prev_lines = lines[max(0, i-3):i-1]
                    if not any('if ' in prev_line and 'None' in prev_line for prev_line in prev_lines):
                        if 'self.' not in line:  # 排除self引用
                            self._add_critical_issue(
                                file_path, "潜在空指针引用", 
                                f"第{i}行: {line} - 可能访问None对象"
                            )
    
    def _check_array_bounds(self, file_path: Path, content: str):
        """检查数组越界风险"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 检查列表/数组访问
            if '[' in line and ']' in line:
                # 检查是否有边界检查
                if 'len(' not in line and 'range(' not in line:
                    if 'if ' not in line:
                        self._add_critical_issue(
                            file_path, "潜在数组越界", 
                            f"第{i}行: {line} - 数组访问可能越界"
                        )
    
    def _check_deadlock_risks(self, file_path: Path, content: str):
        """检查死锁风险"""
        if 'lock' not in content.lower():
            return
            
        lines = content.split('\n')
        lock_acquisitions = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # 记录锁获取
            if any(pattern in line for pattern in ['acquire()', 'with ', 'lock']):
                lock_acquisitions.append((i, line))
        
        # 检查嵌套锁
        if len(lock_acquisitions) > 1:
            self._add_critical_issue(
                file_path, "潜在死锁风险", 
                f"发现多个锁操作，可能存在死锁风险"
            )
    
    def _add_critical_issue(self, file_path: Path, issue_type: str, description: str):
        """添加关键问题"""
        self.critical_issues.append({
            'file': str(file_path.relative_to(self.project_root)),
            'type': issue_type,
            'description': description,
            'severity': 'critical'
        })

def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    checker = CriticalBugChecker(str(project_root))
    
    issues = checker.check_all()
    
    print("\n" + "=" * 60)
    print("关键BUG检查结果")
    print("=" * 60)
    
    if not issues:
        print("✅ 没有发现关键问题！")
        return
    
    # 按类型分组
    by_type = {}
    for issue in issues:
        issue_type = issue['type']
        if issue_type not in by_type:
            by_type[issue_type] = []
        by_type[issue_type].append(issue)
    
    # 显示结果
    for issue_type, type_issues in by_type.items():
        print(f"\n🚨 {issue_type} ({len(type_issues)}个问题):")
        for issue in type_issues[:5]:  # 只显示前5个
            print(f"  📁 {issue['file']}")
            print(f"     {issue['description']}")
        
        if len(type_issues) > 5:
            print(f"     ... 还有 {len(type_issues) - 5} 个问题")
    
    print(f"\n📊 总计发现 {len(issues)} 个关键问题")
    
    # 给出修复建议
    print("\n💡 修复建议:")
    print("1. 优先修复内存泄漏和资源泄漏问题")
    print("2. 添加适当的异常处理和边界检查")
    print("3. 使用with语句管理资源")
    print("4. 添加线程同步机制")
    print("5. 添加空值检查")

if __name__ == "__main__":
    main()
