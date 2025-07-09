"""
ComfyUI辅助工具
提供ComfyUI服务状态检查和启动指导
"""

import requests
import os
import subprocess
import time
from typing import Dict, Optional, Tuple
from src.utils.logger import logger

class ComfyUIHelper:
    """ComfyUI辅助工具类"""
    
    def __init__(self, api_url: str = "http://127.0.0.1:8188"):
        self.api_url = api_url.rstrip('/')
        
    def check_service_status(self, bypass_proxy: bool = True) -> Dict[str, any]:
        """检查ComfyUI服务状态

        Args:
            bypass_proxy: 是否绕过代理设置

        Returns:
            Dict: 包含状态信息的字典
        """
        result = {
            'is_running': False,
            'status_code': None,
            'error_message': '',
            'suggestions': []
        }

        try:
            # 配置请求参数，绕过代理
            request_kwargs = {'timeout': 10}
            if bypass_proxy:
                request_kwargs['proxies'] = {
                    'http': None,
                    'https': None
                }

            response = requests.get(f"{self.api_url}/queue", **request_kwargs)
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                result['is_running'] = True
                logger.info("ComfyUI服务运行正常")
            elif response.status_code == 502:
                result['error_message'] = "ComfyUI服务返回502错误 - 服务未正常启动"
                result['suggestions'] = [
                    "检查ComfyUI是否已正确启动",
                    "确认ComfyUI配置文件是否正确",
                    "检查端口8188是否被其他程序占用",
                    "尝试重启ComfyUI服务"
                ]
            else:
                result['error_message'] = f"ComfyUI服务响应异常: HTTP {response.status_code}"
                result['suggestions'] = [
                    "检查ComfyUI服务状态",
                    "查看ComfyUI日志文件",
                    "尝试重启ComfyUI服务"
                ]
                
        except requests.exceptions.ConnectionError:
            result['error_message'] = "无法连接到ComfyUI服务 - 连接被拒绝"
            result['suggestions'] = [
                "启动ComfyUI服务",
                "确认ComfyUI在端口8188上运行",
                "检查防火墙设置",
                "确认ComfyUI安装路径正确"
            ]
        except requests.exceptions.Timeout:
            result['error_message'] = "ComfyUI服务连接超时"
            result['suggestions'] = [
                "检查网络连接",
                "ComfyUI服务可能响应缓慢，请稍后重试",
                "检查系统资源使用情况"
            ]
        except Exception as e:
            result['error_message'] = f"检查ComfyUI服务时发生异常: {e}"
            result['suggestions'] = [
                "检查网络连接",
                "确认ComfyUI服务地址正确",
                "查看详细错误日志"
            ]
            
        return result
    
    def get_startup_instructions(self) -> str:
        """获取ComfyUI启动指导
        
        Returns:
            str: 启动指导文本
        """
        instructions = """
ComfyUI启动指导:

1. 确保已安装ComfyUI:
   - 从 https://github.com/comfyanonymous/ComfyUI 下载
   - 或使用 git clone https://github.com/comfyanonymous/ComfyUI.git

2. 启动ComfyUI服务:
   方法一 (Windows):
   - 双击 run_nvidia_gpu.bat (NVIDIA显卡)
   - 或双击 run_cpu.bat (CPU模式)
   
   方法二 (命令行):
   - 打开命令提示符
   - 进入ComfyUI目录
   - 运行: python main.py
   
   方法三 (指定端口):
   - 运行: python main.py --port 8188

3. 验证服务启动:
   - 浏览器访问: http://127.0.0.1:8188
   - 应该看到ComfyUI的Web界面

4. 常见问题解决:
   - 端口被占用: 使用 --port 参数指定其他端口
   - 显存不足: 使用 --cpu 参数强制CPU模式
   - 模型缺失: 下载必要的模型文件到 models 目录

5. 推荐配置:
   - 确保有足够的显存 (建议8GB+)
   - 下载基础模型 (如 SD 1.5 或 SDXL)
   - 配置合适的工作流文件
"""
        return instructions.strip()
    
    def find_comfyui_processes(self) -> list:
        """查找正在运行的ComfyUI进程
        
        Returns:
            list: ComfyUI进程信息列表
        """
        processes = []
        try:
            if os.name == 'nt':  # Windows
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
                    for line in lines:
                        if 'main.py' in line or 'comfyui' in line.lower():
                            processes.append(line)
            else:  # Linux/Mac
                result = subprocess.run(
                    ['ps', 'aux'], capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if 'main.py' in line or 'comfyui' in line.lower():
                            processes.append(line)
        except Exception as e:
            logger.warning(f"查找ComfyUI进程失败: {e}")
            
        return processes
    
    def get_diagnostic_info(self) -> Dict[str, any]:
        """获取诊断信息
        
        Returns:
            Dict: 诊断信息
        """
        status = self.check_service_status()
        processes = self.find_comfyui_processes()
        
        return {
            'service_status': status,
            'running_processes': processes,
            'api_url': self.api_url,
            'startup_instructions': self.get_startup_instructions()
        }
    
    def format_diagnostic_report(self) -> str:
        """格式化诊断报告
        
        Returns:
            str: 格式化的诊断报告
        """
        info = self.get_diagnostic_info()
        
        report = f"""
ComfyUI诊断报告
{'='*50}

服务状态:
- API地址: {info['api_url']}
- 运行状态: {'正常' if info['service_status']['is_running'] else '异常'}
"""
        
        if not info['service_status']['is_running']:
            report += f"- 错误信息: {info['service_status']['error_message']}\n"
            report += "- 建议解决方案:\n"
            for suggestion in info['service_status']['suggestions']:
                report += f"  • {suggestion}\n"
        
        if info['running_processes']:
            report += f"\n检测到的相关进程:\n"
            for process in info['running_processes']:
                report += f"  {process}\n"
        else:
            report += f"\n未检测到ComfyUI相关进程\n"
            
        report += f"\n{info['startup_instructions']}"
        
        return report

# 全局实例
comfyui_helper = ComfyUIHelper()
