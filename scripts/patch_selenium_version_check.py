#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修补Selenium版本检查的脚本
"""

import os
import sys
import importlib.util
from pathlib import Path

def patch_selenium_version_check():
    """修补Selenium版本检查"""
    try:
        # 查找selenium安装位置
        import selenium
        selenium_path = Path(selenium.__file__).parent
        
        print(f"找到Selenium安装位置: {selenium_path}")
        
        # 查找ChromeDriver服务文件
        service_file = selenium_path / "webdriver" / "chrome" / "service.py"
        
        if not service_file.exists():
            print("❌ 未找到Chrome服务文件")
            return False
        
        print(f"找到Chrome服务文件: {service_file}")
        
        # 读取原始文件
        with open(service_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经修补过
        if "# PATCHED FOR VERSION COMPATIBILITY" in content:
            print("✅ Selenium版本检查已经修补过")
            return True
        
        # 备份原始文件
        backup_file = service_file.with_suffix('.py.backup')
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"已备份原始文件: {backup_file}")
        
        # 修补版本检查
        # 查找版本检查相关的代码并注释掉
        lines = content.split('\n')
        patched_lines = []
        
        for line in lines:
            # 如果包含版本检查相关的代码，就注释掉
            if any(keyword in line.lower() for keyword in [
                'version', 'compatibility', 'supported', 'check'
            ]) and any(keyword in line for keyword in [
                'raise', 'exception', 'error'
            ]):
                patched_lines.append(f"    # PATCHED: {line}")
            else:
                patched_lines.append(line)
        
        # 在文件开头添加标记
        patched_content = "# PATCHED FOR VERSION COMPATIBILITY\n" + '\n'.join(patched_lines)
        
        # 写入修补后的文件
        with open(service_file, 'w', encoding='utf-8') as f:
            f.write(patched_content)
        
        print("✅ Selenium版本检查修补完成")
        return True
        
    except Exception as e:
        print(f"❌ 修补失败: {e}")
        return False

def restore_selenium_backup():
    """恢复Selenium备份"""
    try:
        import selenium
        selenium_path = Path(selenium.__file__).parent
        service_file = selenium_path / "webdriver" / "chrome" / "service.py"
        backup_file = service_file.with_suffix('.py.backup')
        
        if backup_file.exists():
            with open(backup_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            with open(service_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Selenium备份已恢复")
            return True
        else:
            print("❌ 未找到备份文件")
            return False
            
    except Exception as e:
        print(f"❌ 恢复失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("Selenium版本检查修补工具")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        print("恢复Selenium备份...")
        restore_selenium_backup()
    else:
        print("修补Selenium版本检查...")
        if patch_selenium_version_check():
            print("\n🎉 修补成功！")
            print("现在可以尝试使用抖音发布功能了。")
            print("\n如需恢复原始文件，请运行:")
            print("python scripts/patch_selenium_version_check.py restore")
        else:
            print("\n❌ 修补失败")

if __name__ == "__main__":
    main()
