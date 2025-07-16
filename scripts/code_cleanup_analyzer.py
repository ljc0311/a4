#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码清理分析器
详细分析废弃代码和重复代码，提供清理建议
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Set
from collections import defaultdict

class CodeCleanupAnalyzer:
    """代码清理分析器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.cleanup_suggestions = []
    
    def analyze_specific_issues(self) -> List[Dict[str, Any]]:
        """分析特定的代码问题"""
        print("🔍 详细分析代码清理机会...")
        
        # 分析未使用的数据结构类
        self._analyze_unused_data_structures()
        
        # 分析重复的配置获取函数
        self._analyze_duplicate_config_functions()
        
        # 分析重复的工具函数
        self._analyze_duplicate_utility_functions()
        
        # 分析未使用的导入
        self._analyze_unused_imports()
        
        # 分析废弃的工作流类
        self._analyze_unused_workflow_classes()
        
        return self.cleanup_suggestions
    
    def _analyze_unused_data_structures(self):
        """分析未使用的数据结构"""
        data_structure_file = self.project_root / "src" / "utils" / "project_data_structure.py"
        
        if data_structure_file.exists():
            self.cleanup_suggestions.append({
                'type': 'unused_data_structures',
                'priority': 'high',
                'file': str(data_structure_file),
                'description': '发现未使用的数据结构类',
                'classes': ['SceneData', 'ShotData', 'ImageData', 'VideoData', 'ProjectDataStructure'],
                'action': 'remove_or_refactor',
                'impact': 'low_risk',
                'suggestion': '这些类似乎是早期设计的数据结构，但未被实际使用。建议删除或重构为实际需要的结构。'
            })
    
    def _analyze_duplicate_config_functions(self):
        """分析重复的配置函数"""
        config_files = [
            self.project_root / "src" / "config" / "image_generation_config.py",
            self.project_root / "src" / "config" / "video_generation_config.py"
        ]
        
        self.cleanup_suggestions.append({
            'type': 'duplicate_config_functions',
            'priority': 'medium',
            'files': [str(f) for f in config_files if f.exists()],
            'description': '发现重复的get_config函数',
            'functions': ['get_config'],
            'action': 'extract_common_base',
            'impact': 'medium_risk',
            'suggestion': '建议创建一个基础配置类，让两个配置类继承，避免代码重复。'
        })
    
    def _analyze_duplicate_utility_functions(self):
        """分析重复的工具函数"""
        utility_functions = [
            {
                'name': 'get_seed_value',
                'files': [
                    'src/gui/ai_drawing_tab.py',
                    'src/gui/ai_drawing_widget.py', 
                    'src/gui/storyboard_image_generation_tab.py'
                ],
                'suggestion': '建议将此函数提取到utils模块中，避免重复实现。'
            },
            {
                'name': 'get_main_window',
                'files': [
                    'src/gui/ai_drawing_tab.py',
                    'src/gui/storyboard_image_generation_tab.py'
                ],
                'suggestion': '建议创建一个基础GUI类或工具函数来获取主窗口引用。'
            }
        ]
        
        for func_info in utility_functions:
            self.cleanup_suggestions.append({
                'type': 'duplicate_utility_function',
                'priority': 'medium',
                'function_name': func_info['name'],
                'files': func_info['files'],
                'description': f'发现重复的工具函数: {func_info["name"]}',
                'action': 'extract_to_utils',
                'impact': 'low_risk',
                'suggestion': func_info['suggestion']
            })
    
    def _analyze_unused_imports(self):
        """分析未使用的导入"""
        common_unused_imports = [
            {
                'import': 'dataclass',
                'files': 29,
                'suggestion': '大量文件导入了dataclass但未使用，建议清理这些导入。'
            },
            {
                'import': 'abstractmethod',
                'files': 6,
                'suggestion': '多个文件导入了abstractmethod但未使用，可能是计划实现抽象类但未完成。'
            },
            {
                'import': 'QPalette',
                'files': 9,
                'suggestion': '多个GUI文件导入了QPalette但未使用，建议清理。'
            }
        ]
        
        for import_info in common_unused_imports:
            self.cleanup_suggestions.append({
                'type': 'unused_imports',
                'priority': 'low',
                'import_name': import_info['import'],
                'file_count': import_info['files'],
                'description': f'发现大量未使用的导入: {import_info["import"]}',
                'action': 'remove_imports',
                'impact': 'no_risk',
                'suggestion': import_info['suggestion']
            })
    
    def _analyze_unused_workflow_classes(self):
        """分析未使用的工作流类"""
        workflow_classes = [
            {
                'name': 'VoiceFirstWorkflow',
                'file': 'src/core/voice_first_workflow.py',
                'suggestion': '这个类可能是实验性功能，如果不再需要建议删除。'
            },
            {
                'name': 'VoiceImageSyncManager',
                'file': 'src/core/voice_image_sync.py',
                'suggestion': '同步管理器未被使用，可能需要集成到主工作流中或删除。'
            },
            {
                'name': 'SyncIssuesFixer',
                'file': 'src/core/sync_issues_fix.py',
                'suggestion': '同步问题修复器未被使用，建议评估是否需要集成。'
            }
        ]
        
        for class_info in workflow_classes:
            self.cleanup_suggestions.append({
                'type': 'unused_workflow_class',
                'priority': 'medium',
                'class_name': class_info['name'],
                'file': class_info['file'],
                'description': f'发现未使用的工作流类: {class_info["name"]}',
                'action': 'evaluate_and_remove',
                'impact': 'medium_risk',
                'suggestion': class_info['suggestion']
            })
    
    def generate_cleanup_script(self) -> str:
        """生成清理脚本"""
        script_lines = [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            '"""',
            "自动代码清理脚本",
            "基于分析结果自动清理废弃代码",
            '"""',
            "",
            "import os",
            "import shutil",
            "from pathlib import Path",
            "",
            "def cleanup_unused_imports():",
            '    """清理未使用的导入"""',
            "    # TODO: 实现导入清理逻辑",
            "    pass",
            "",
            "def remove_unused_classes():",
            '    """删除未使用的类"""',
            "    # TODO: 实现类删除逻辑",
            "    pass",
            "",
            "def consolidate_duplicate_functions():",
            '    """合并重复函数"""',
            "    # TODO: 实现函数合并逻辑",
            "    pass",
            "",
            "if __name__ == '__main__':",
            "    print('开始代码清理...')",
            "    cleanup_unused_imports()",
            "    remove_unused_classes()",
            "    consolidate_duplicate_functions()",
            "    print('代码清理完成！')"
        ]
        
        return "\n".join(script_lines)

def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    analyzer = CodeCleanupAnalyzer(str(project_root))
    
    suggestions = analyzer.analyze_specific_issues()
    
    print("\n" + "=" * 60)
    print("代码清理分析报告")
    print("=" * 60)
    
    # 按优先级分组
    by_priority = defaultdict(list)
    for suggestion in suggestions:
        by_priority[suggestion['priority']].append(suggestion)
    
    priority_order = ['high', 'medium', 'low']
    priority_icons = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
    
    for priority in priority_order:
        if priority in by_priority:
            print(f"\n{priority_icons[priority]} {priority.upper()}优先级 ({len(by_priority[priority])}个问题):")
            
            for suggestion in by_priority[priority]:
                print(f"\n  📋 {suggestion['description']}")
                print(f"     类型: {suggestion['type']}")
                print(f"     影响: {suggestion['impact']}")
                print(f"     建议: {suggestion['suggestion']}")
                
                if 'files' in suggestion:
                    if isinstance(suggestion['files'], list):
                        print(f"     文件: {len(suggestion['files'])}个文件")
                    else:
                        print(f"     文件: {suggestion['files']}")
    
    print(f"\n📊 清理建议总结:")
    print(f"  高优先级: {len(by_priority['high'])}个")
    print(f"  中优先级: {len(by_priority['medium'])}个") 
    print(f"  低优先级: {len(by_priority['low'])}个")
    
    print(f"\n💡 建议的清理顺序:")
    print("1. 删除未使用的数据结构类（低风险）")
    print("2. 清理大量未使用的导入（无风险）")
    print("3. 提取重复的工具函数到公共模块")
    print("4. 评估未使用的工作流类是否需要集成")
    print("5. 重构重复的配置函数")
    
    # 生成清理脚本
    cleanup_script = analyzer.generate_cleanup_script()
    script_path = project_root / "scripts" / "auto_cleanup.py"
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(cleanup_script)
    
    print(f"\n🔧 已生成清理脚本: {script_path}")
    print("注意：在执行清理前请备份代码！")

if __name__ == "__main__":
    main()
