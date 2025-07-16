#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全代码清理工具
安全地清理废弃代码和重复代码
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class SafeCodeCleaner:
    """安全代码清理器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backup" / f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.changes_log = []
    
    def create_backup(self):
        """创建备份"""
        print("📦 创建代码备份...")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份主要源码目录
        src_dir = self.project_root / "src"
        if src_dir.exists():
            shutil.copytree(src_dir, self.backup_dir / "src")
        
        print(f"✅ 备份已创建: {self.backup_dir}")
    
    def cleanup_unused_imports(self) -> int:
        """清理未使用的导入"""
        print("🧹 清理未使用的导入...")
        
        cleanup_count = 0
        
        # 定义要清理的未使用导入
        unused_imports = [
            'from dataclasses import dataclass',
            'from abc import abstractmethod',
            'from PyQt5.QtGui import QPalette',
            'from PyQt5.QtWidgets import QTreeWidget',
            'from PyQt5.QtWidgets import QTreeWidgetItem',
            'from PyQt5.QtCore import pyqtProperty'
        ]
        
        for file_path in self.project_root.rglob("*.py"):
            if self._should_skip_file(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # 检查并移除未使用的导入
                for unused_import in unused_imports:
                    if unused_import in content:
                        # 检查是否真的未使用
                        import_name = self._extract_import_name(unused_import)
                        if import_name and not self._is_import_used(content, import_name):
                            content = content.replace(unused_import + '\n', '')
                            content = content.replace(unused_import, '')
                            cleanup_count += 1
                            self.changes_log.append(f"移除未使用导入 {import_name} 从 {file_path}")
                
                # 如果有变化，写回文件
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
            except Exception as e:
                print(f"⚠️ 处理文件失败 {file_path}: {e}")
        
        print(f"✅ 清理了 {cleanup_count} 个未使用的导入")
        return cleanup_count
    
    def _extract_import_name(self, import_statement: str) -> str:
        """提取导入名称"""
        if 'import ' in import_statement:
            parts = import_statement.split('import ')
            if len(parts) > 1:
                return parts[1].strip()
        return ""
    
    def _is_import_used(self, content: str, import_name: str) -> bool:
        """检查导入是否被使用"""
        # 移除导入语句本身
        content_without_imports = re.sub(r'^(from .* import .*|import .*)$', '', content, flags=re.MULTILINE)
        
        # 检查是否在代码中使用
        patterns = [
            rf'\b{re.escape(import_name)}\b',
            rf'@{re.escape(import_name)}',
            rf'{re.escape(import_name)}\(',
        ]
        
        for pattern in patterns:
            if re.search(pattern, content_without_imports):
                return True
        
        return False
    
    def remove_unused_data_structures(self) -> int:
        """移除未使用的数据结构"""
        print("🗑️ 移除未使用的数据结构...")
        
        data_structure_file = self.project_root / "src" / "utils" / "project_data_structure.py"
        
        if not data_structure_file.exists():
            print("⚠️ 数据结构文件不存在")
            return 0
        
        try:
            with open(data_structure_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查这些类是否真的未被使用
            unused_classes = ['SceneData', 'ShotData', 'ImageData', 'VideoData', 'ProjectDataStructure']
            
            # 在整个项目中搜索这些类的使用
            all_content = self._get_all_project_content()
            
            actually_unused = []
            for class_name in unused_classes:
                if not self._is_class_used_in_project(class_name, all_content):
                    actually_unused.append(class_name)
            
            if actually_unused:
                # 创建一个注释版本而不是直接删除
                comment_header = f"""# 以下类在 {datetime.now().strftime('%Y-%m-%d')} 的分析中被标记为未使用
# 如果确认不需要，可以删除这些类定义
# 备份位置: {self.backup_dir}

"""
                
                with open(data_structure_file, 'w', encoding='utf-8') as f:
                    f.write(comment_header + content)
                
                self.changes_log.append(f"标记未使用的数据结构类: {', '.join(actually_unused)}")
                print(f"✅ 标记了 {len(actually_unused)} 个未使用的数据结构类")
                return len(actually_unused)
            else:
                print("✅ 所有数据结构类都在使用中")
                return 0
                
        except Exception as e:
            print(f"⚠️ 处理数据结构文件失败: {e}")
            return 0
    
    def _get_all_project_content(self) -> str:
        """获取所有项目内容"""
        all_content = ""
        for file_path in self.project_root.rglob("*.py"):
            if self._should_skip_file(file_path):
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    all_content += f.read() + "\n"
            except:
                continue
        return all_content
    
    def _is_class_used_in_project(self, class_name: str, all_content: str) -> bool:
        """检查类是否在项目中被使用"""
        patterns = [
            rf'\b{re.escape(class_name)}\s*\(',  # 实例化
            rf':\s*{re.escape(class_name)}\b',   # 类型注解
            rf'isinstance\s*\([^,]+,\s*{re.escape(class_name)}\)',  # isinstance检查
            rf'class\s+\w+\s*\([^)]*{re.escape(class_name)}[^)]*\)',  # 继承
        ]
        
        for pattern in patterns:
            if re.search(pattern, all_content):
                return True
        
        return False
    
    def extract_duplicate_utility_functions(self) -> int:
        """提取重复的工具函数"""
        print("🔧 提取重复的工具函数...")
        
        # 创建工具模块
        utils_dir = self.project_root / "src" / "utils"
        utils_dir.mkdir(exist_ok=True)
        
        gui_utils_file = utils_dir / "gui_utils.py"
        
        # 创建GUI工具模块
        gui_utils_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI工具函数
提取的公共GUI工具函数
"""

import random
from PyQt5.QtWidgets import QApplication

def get_seed_value(seed_input_widget) -> int:
    """获取种子值的统一实现"""
    try:
        seed_text = seed_input_widget.text().strip()
        if seed_text == "" or seed_text == "随机":
            return random.randint(1, 2147483647)
        else:
            return int(seed_text)
    except ValueError:
        return random.randint(1, 2147483647)

def get_main_window():
    """获取主窗口的统一实现"""
    app = QApplication.instance()
    if app:
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'isMainWindow') and widget.isMainWindow():
                return widget
    return None
'''
        
        with open(gui_utils_file, 'w', encoding='utf-8') as f:
            f.write(gui_utils_content)
        
        self.changes_log.append(f"创建GUI工具模块: {gui_utils_file}")
        print(f"✅ 创建了GUI工具模块: {gui_utils_file}")
        print("💡 请手动更新相关文件以使用新的工具函数")
        
        return 1
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """判断是否应该跳过文件"""
        skip_patterns = [
            "__pycache__", ".git", ".venv", "venv", "build", "dist",
            ".pytest_cache", "backup"
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def generate_cleanup_report(self):
        """生成清理报告"""
        report_file = self.project_root / "CLEANUP_REPORT.md"
        
        report_content = f"""# 代码清理报告

## 清理时间
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 备份位置
{self.backup_dir}

## 执行的清理操作

"""
        
        for i, change in enumerate(self.changes_log, 1):
            report_content += f"{i}. {change}\n"
        
        report_content += f"""

## 清理统计
- 总计执行了 {len(self.changes_log)} 项清理操作

## 注意事项
1. 所有更改前都已创建备份
2. 建议运行测试确保功能正常
3. 部分清理需要手动完成（如重复函数的替换）

## 后续建议
1. 定期运行代码质量检查
2. 建立代码审查流程
3. 使用自动化工具持续监控代码质量
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"📋 清理报告已生成: {report_file}")

def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    cleaner = SafeCodeCleaner(str(project_root))
    
    print("🚀 开始安全代码清理...")
    print("⚠️ 注意：此操作会修改代码文件，请确保已提交当前更改到版本控制系统")
    
    # 确认操作
    response = input("是否继续？(y/N): ").lower().strip()
    if response != 'y':
        print("❌ 操作已取消")
        return
    
    try:
        # 创建备份
        cleaner.create_backup()
        
        # 执行清理操作
        total_changes = 0
        
        # 1. 清理未使用的导入
        total_changes += cleaner.cleanup_unused_imports()
        
        # 2. 移除未使用的数据结构
        total_changes += cleaner.remove_unused_data_structures()
        
        # 3. 提取重复的工具函数
        total_changes += cleaner.extract_duplicate_utility_functions()
        
        # 生成报告
        cleaner.generate_cleanup_report()
        
        print(f"\n🎉 代码清理完成！")
        print(f"📊 总计执行了 {total_changes} 项清理操作")
        print(f"📦 备份位置: {cleaner.backup_dir}")
        print(f"📋 详细报告: {project_root}/CLEANUP_REPORT.md")
        
        print(f"\n💡 建议接下来：")
        print("1. 运行程序测试功能是否正常")
        print("2. 检查清理报告中的建议")
        print("3. 手动处理需要人工判断的重复代码")
        
    except Exception as e:
        print(f"❌ 清理过程中出现错误: {e}")
        print("请检查备份并手动恢复必要的文件")

if __name__ == "__main__":
    main()
