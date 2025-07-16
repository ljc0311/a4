"""
代理绕过工具
用于确保本地服务连接不受代理软件影响
"""

import requests
import os
from typing import Dict, Any, Optional
from src.utils.logger import logger

class ProxyBypass:
    """代理绕过工具类"""
    
    @staticmethod
    def get_no_proxy_config() -> Dict[str, str]:
        """获取无代理配置
        
        Returns:
            Dict: 无代理配置字典
        """
        return {
            'http': '',
            'https': '',
            'no_proxy': 'localhost,127.0.0.1,::1'
        }
    
    @staticmethod
    def requests_get(url: str, bypass_proxy: bool = True, **kwargs) -> requests.Response:
        """发送GET请求，可选择绕过代理
        
        Args:
            url: 请求URL
            bypass_proxy: 是否绕过代理
            **kwargs: 其他requests参数
            
        Returns:
            requests.Response: 响应对象
        """
        if bypass_proxy and ProxyBypass._is_local_url(url):
            kwargs['proxies'] = ProxyBypass.get_no_proxy_config()
            logger.debug(f"绕过代理访问本地URL: {url}")
        
        return requests.get(url, **kwargs)
    
    @staticmethod
    def requests_post(url: str, bypass_proxy: bool = True, **kwargs) -> requests.Response:
        """发送POST请求，可选择绕过代理
        
        Args:
            url: 请求URL
            bypass_proxy: 是否绕过代理
            **kwargs: 其他requests参数
            
        Returns:
            requests.Response: 响应对象
        """
        if bypass_proxy and ProxyBypass._is_local_url(url):
            kwargs['proxies'] = ProxyBypass.get_no_proxy_config()
            logger.debug(f"绕过代理访问本地URL: {url}")
        
        return requests.post(url, **kwargs)
    
    @staticmethod
    def _is_local_url(url: str) -> bool:
        """检查是否为本地URL
        
        Args:
            url: 要检查的URL
            
        Returns:
            bool: 是否为本地URL
        """
        local_hosts = [
            'localhost',
            '127.0.0.1',
            '0.0.0.0',
            '::1'
        ]
        
        url_lower = url.lower()
        return any(host in url_lower for host in local_hosts)
    
    @staticmethod
    def set_environment_no_proxy():
        """设置环境变量以绕过代理"""
        no_proxy_hosts = 'localhost,127.0.0.1,0.0.0.0,::1'
        
        # 设置环境变量
        os.environ['NO_PROXY'] = no_proxy_hosts
        os.environ['no_proxy'] = no_proxy_hosts
        
        logger.info(f"设置NO_PROXY环境变量: {no_proxy_hosts}")
    
    @staticmethod
    def check_proxy_interference(url: str) -> Dict[str, Any]:
        """检查代理是否干扰本地连接
        
        Args:
            url: 要测试的URL
            
        Returns:
            Dict: 检查结果
        """
        result = {
            'url': url,
            'with_proxy': {'success': False, 'error': '', 'status_code': None},
            'without_proxy': {'success': False, 'error': '', 'status_code': None},
            'proxy_interference': False
        }
        
        # 测试使用系统代理
        try:
            response = requests.get(url, timeout=10)
            result['with_proxy']['success'] = True
            result['with_proxy']['status_code'] = response.status_code
        except Exception as e:
            result['with_proxy']['error'] = str(e)
        
        # 测试绕过代理
        try:
            response = ProxyBypass.requests_get(url, bypass_proxy=True, timeout=10)
            result['without_proxy']['success'] = True
            result['without_proxy']['status_code'] = response.status_code
        except Exception as e:
            result['without_proxy']['error'] = str(e)
        
        # 判断是否存在代理干扰
        result['proxy_interference'] = (
            not result['with_proxy']['success'] and 
            result['without_proxy']['success']
        )
        
        return result
    
    @staticmethod
    def get_proxy_diagnostic_info() -> Dict[str, Any]:
        """获取代理诊断信息
        
        Returns:
            Dict: 诊断信息
        """
        info = {
            'environment_variables': {},
            'proxy_interference_test': {},
            'recommendations': []
        }
        
        # 检查环境变量
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'no_proxy']
        for var in proxy_vars:
            info['environment_variables'][var] = os.environ.get(var, 'Not set')
        
        # 测试本地连接
        test_url = 'http://127.0.0.1:8188/queue'
        info['proxy_interference_test'] = ProxyBypass.check_proxy_interference(test_url)
        
        # 生成建议
        if info['proxy_interference_test']['proxy_interference']:
            info['recommendations'].extend([
                "检测到代理软件可能干扰本地服务连接",
                "建议在代理软件中添加本地地址到绕过列表",
                "或者临时关闭代理软件进行测试"
            ])
        
        if not info['environment_variables']['NO_PROXY']:
            info['recommendations'].append("建议设置NO_PROXY环境变量包含本地地址")
        
        return info

# 全局实例
proxy_bypass = ProxyBypass()
