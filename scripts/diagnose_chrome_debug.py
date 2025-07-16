#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome调试模式诊断工具
"""

import os
import sys
import time
import json
import subprocess
import requests
from pathlib import Path

def check_chrome_processes():
    """检查Chrome进程"""
    try:
        print("🔍 检查Chrome进程...")
        
        if os.name == 'nt':  # Windows
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq chrome.exe'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                chrome_processes = [line for line in lines if 'chrome.exe' in line]
                
                if chrome_processes:
                    print(f"✅ 找到 {len(chrome_processes)} 个Chrome进程:")
                    for i, process in enumerate(chrome_processes[:5], 1):  # 只显示前5个
                        print(f"   {i}. {process.strip()}")
                    return True
                else:
                    print("❌ 未找到Chrome进程")
                    return False
        else:  # Linux/Mac
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            if 'chrome' in result.stdout:
                print("✅ 找到Chrome进程")
                return True
            else:
                print("❌ 未找到Chrome进程")
                return False
                
    except Exception as e:
        print(f"❌ 检查Chrome进程失败: {e}")
        return False

def check_debug_port():
    """检查调试端口"""
    try:
        print("\n🔍 检查调试端口 9222...")
        
        # 检查端口是否被占用
        if os.name == 'nt':  # Windows
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            if ':9222' in result.stdout:
                print("✅ 端口 9222 正在被使用")
                
                # 查找占用端口的进程
                lines = result.stdout.split('\n')
                for line in lines:
                    if ':9222' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            print(f"   占用进程PID: {pid}")
                            
                            # 查找进程名称
                            try:
                                pid_result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                                          capture_output=True, text=True)
                                if 'chrome.exe' in pid_result.stdout:
                                    print("   ✅ 确认是Chrome进程占用")
                                    return True
                                else:
                                    print("   ❌ 非Chrome进程占用端口")
                                    return False
                            except:
                                pass
                        break
                return True
            else:
                print("❌ 端口 9222 未被使用")
                return False
        else:  # Linux/Mac
            result = subprocess.run(['lsof', '-i', ':9222'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                print("✅ 端口 9222 正在被使用")
                return True
            else:
                print("❌ 端口 9222 未被使用")
                return False
                
    except Exception as e:
        print(f"❌ 检查调试端口失败: {e}")
        return False

def test_debug_api():
    """测试调试API"""
    try:
        print("\n🔍 测试Chrome调试API...")
        
        # 测试基本连接
        try:
            response = requests.get("http://127.0.0.1:9222", timeout=5)
            print(f"   基本连接状态码: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ 基本连接成功")
            else:
                print("   ❌ 基本连接失败")
        except Exception as e:
            print(f"   ❌ 基本连接异常: {e}")
        
        # 测试JSON API
        try:
            response = requests.get("http://127.0.0.1:9222/json", timeout=5)
            print(f"   JSON API状态码: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ JSON API连接成功")
                
                try:
                    data = response.json()
                    print(f"   📊 当前标签页数量: {len(data)}")
                    
                    # 显示前3个标签页信息
                    for i, tab in enumerate(data[:3], 1):
                        title = tab.get('title', 'Unknown')[:50]
                        url = tab.get('url', 'Unknown')[:80]
                        print(f"   {i}. {title}")
                        print(f"      URL: {url}")
                    
                    return True
                    
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON解析失败: {e}")
                    print(f"   响应内容: {response.text[:200]}")
                    return False
            else:
                print("   ❌ JSON API连接失败")
                print(f"   响应内容: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"   ❌ JSON API异常: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 测试调试API失败: {e}")
        return False

def check_user_data_dir():
    """检查用户数据目录"""
    try:
        print("\n🔍 检查用户数据目录...")
        
        # 检查当前目录下的selenium文件夹
        selenium_dir = Path("selenium")
        if selenium_dir.exists():
            print(f"✅ 找到用户数据目录: {selenium_dir.absolute()}")
            
            # 检查目录内容
            contents = list(selenium_dir.iterdir())
            print(f"   目录内容数量: {len(contents)}")
            
            # 检查关键文件
            key_files = ['Default', 'Local State', 'Preferences']
            for key_file in key_files:
                if (selenium_dir / key_file).exists():
                    print(f"   ✅ 找到关键文件: {key_file}")
                else:
                    print(f"   ⚠️  缺少文件: {key_file}")
            
            return True
        else:
            print("❌ 未找到用户数据目录 selenium")
            print("   Chrome可能使用了不同的用户数据目录")
            return False
            
    except Exception as e:
        print(f"❌ 检查用户数据目录失败: {e}")
        return False

def check_firewall_and_permissions():
    """检查防火墙和权限"""
    try:
        print("\n🔍 检查防火墙和权限...")
        
        # 检查是否以管理员权限运行
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if is_admin:
                print("✅ 以管理员权限运行")
            else:
                print("⚠️  未以管理员权限运行（可能影响某些功能）")
        except:
            print("⚠️  无法检查管理员权限")
        
        # 测试本地回环连接
        try:
            response = requests.get("http://localhost:9222/json", timeout=2)
            if response.status_code == 200:
                print("✅ localhost连接正常")
            else:
                print("❌ localhost连接异常")
        except:
            print("❌ localhost连接失败")
        
        # 测试127.0.0.1连接
        try:
            response = requests.get("http://127.0.0.1:9222/json", timeout=2)
            if response.status_code == 200:
                print("✅ 127.0.0.1连接正常")
            else:
                print("❌ 127.0.0.1连接异常")
        except:
            print("❌ 127.0.0.1连接失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查防火墙和权限失败: {e}")
        return False

def provide_solutions():
    """提供解决方案"""
    print("\n" + "=" * 60)
    print("💡 常见问题解决方案:")
    print("=" * 60)
    
    print("1. 如果Chrome进程存在但API无法访问:")
    print("   - 完全关闭Chrome: taskkill /f /im chrome.exe")
    print("   - 重新以调试模式启动")
    print("   - 检查防火墙是否阻止了9222端口")
    
    print("\n2. 如果端口被其他程序占用:")
    print("   - 更换端口: --remote-debugging-port=9223")
    print("   - 或结束占用进程")
    
    print("\n3. 如果用户数据目录问题:")
    print("   - 删除selenium目录重新创建")
    print("   - 或使用绝对路径: --user-data-dir=C:\\temp\\selenium")
    
    print("\n4. 推荐的启动命令:")
    print('   "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" \\')
    print("   --remote-debugging-port=9222 \\")
    print("   --user-data-dir=selenium \\")
    print("   --disable-features=VizDisplayCompositor \\")
    print("   --no-first-run --no-default-browser-check")
    
    print("\n5. 如果仍然有问题:")
    print("   - 重启计算机")
    print("   - 更新Chrome到最新版本")
    print("   - 临时关闭杀毒软件")
    
    print("=" * 60)

def main():
    """主函数"""
    print("🚀 Chrome调试模式诊断工具")
    print("=" * 60)
    
    # 诊断步骤
    checks = [
        ("Chrome进程检查", check_chrome_processes),
        ("调试端口检查", check_debug_port),
        ("调试API测试", test_debug_api),
        ("用户数据目录检查", check_user_data_dir),
        ("防火墙和权限检查", check_firewall_and_permissions)
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        print(f"\n{'='*20} {check_name} {'='*20}")
        try:
            result = check_func()
            results[check_name] = result
        except Exception as e:
            print(f"❌ {check_name}执行失败: {e}")
            results[check_name] = False
    
    # 总结结果
    print("\n" + "=" * 60)
    print("📊 诊断结果总结:")
    print("=" * 60)
    
    success_count = 0
    for check_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {check_name.ljust(20)}: {status}")
        if result:
            success_count += 1
    
    print(f"\n总体状态: {success_count}/{len(results)} 项检查通过")
    
    if success_count == len(results):
        print("🎉 Chrome调试模式配置完全正常！")
    elif results.get("调试API测试", False):
        print("✅ Chrome调试模式基本可用")
    else:
        print("❌ Chrome调试模式存在问题")
        provide_solutions()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断诊断")
    except Exception as e:
        print(f"\n❌ 诊断工具运行异常: {e}")
        import traceback
        traceback.print_exc()
