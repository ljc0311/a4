#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Vheer网站的JavaScript文件，查找API端点
"""

import asyncio
import aiohttp
import re
import json
from typing import List, Set

class VheerJSAnalyzer:
    """Vheer JavaScript 分析器"""
    
    def __init__(self):
        self.base_url = "https://vheer.com"
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
    async def initialize(self):
        """初始化会话"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )
        
    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()
            
    async def get_js_files(self) -> List[str]:
        """获取JavaScript文件列表"""
        try:
            async with self.session.get(f"{self.base_url}/app/text-to-image") as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # 查找JavaScript文件
                    js_files = re.findall(r'src="([^"]*\.js[^"]*)"', content)
                    
                    # 过滤和清理URL
                    cleaned_files = []
                    for js_file in js_files:
                        if js_file.startswith('/_next/'):
                            cleaned_files.append(js_file)
                    
                    return cleaned_files
                    
        except Exception as e:
            print(f"获取JS文件列表失败: {e}")
            return []
            
    async def analyze_js_file(self, js_path: str) -> Set[str]:
        """分析单个JavaScript文件"""
        found_endpoints = set()
        
        try:
            url = f"{self.base_url}{js_path}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # 查找API相关的模式
                    patterns = [
                        # API端点模式
                        r'["\'](/api/[^"\']+)["\']',
                        r'["\']([^"\']*api[^"\']*)["\']',
                        
                        # URL模式
                        r'url["\s]*:["\s]*["\']([^"\']+)["\']',
                        r'endpoint["\s]*:["\s]*["\']([^"\']+)["\']',
                        r'baseURL["\s]*:["\s]*["\']([^"\']+)["\']',
                        
                        # 函数调用模式
                        r'fetch\(["\']([^"\']+)["\']',
                        r'axios\.[a-z]+\(["\']([^"\']+)["\']',
                        r'\.post\(["\']([^"\']+)["\']',
                        r'\.get\(["\']([^"\']+)["\']',
                        
                        # 特定的生成相关端点
                        r'["\']([^"\']*generate[^"\']*)["\']',
                        r'["\']([^"\']*image[^"\']*)["\']',
                        r'["\']([^"\']*create[^"\']*)["\']',
                        
                        # Next.js API路由
                        r'["\']([^"\']*/_next/[^"\']*)["\']',
                        
                        # 可能的外部API
                        r'["\'](https://[^"\']*api[^"\']*)["\']',
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        for match in matches:
                            # 过滤有效的端点
                            if self._is_valid_endpoint(match):
                                found_endpoints.add(match)
                    
                    # 查找特定的关键词
                    keywords = ['generate', 'create', 'upload', 'process', 'submit', 'api']
                    for keyword in keywords:
                        # 查找包含关键词的字符串
                        keyword_pattern = rf'["\']([^"\']*{keyword}[^"\']*)["\']'
                        matches = re.findall(keyword_pattern, content, re.IGNORECASE)
                        for match in matches:
                            if self._is_valid_endpoint(match):
                                found_endpoints.add(match)
                                
        except Exception as e:
            print(f"分析JS文件 {js_path} 失败: {e}")
            
        return found_endpoints
        
    def _is_valid_endpoint(self, endpoint: str) -> bool:
        """检查是否是有效的端点"""
        if not endpoint:
            return False
            
        # 过滤掉明显不是API端点的字符串
        invalid_patterns = [
            r'^[a-zA-Z]$',  # 单个字母
            r'^\d+$',       # 纯数字
            r'^[a-zA-Z]{1,3}$',  # 太短的字符串
            r'\.css$',      # CSS文件
            r'\.png$|\.jpg$|\.jpeg$|\.gif$|\.webp$',  # 图片文件
            r'\.woff$|\.woff2$|\.ttf$',  # 字体文件
            r'^#',          # 锚点
            r'^javascript:',  # JavaScript代码
            r'^data:',      # Data URL
            r'^mailto:',    # 邮件链接
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, endpoint, re.IGNORECASE):
                return False
                
        # 检查是否包含有用的关键词
        useful_keywords = [
            'api', 'generate', 'create', 'upload', 'process', 'submit',
            'image', 'text', 'ai', 'model', 'endpoint', 'service'
        ]
        
        endpoint_lower = endpoint.lower()
        for keyword in useful_keywords:
            if keyword in endpoint_lower:
                return True
                
        # 检查是否是路径格式
        if endpoint.startswith('/') and len(endpoint) > 3:
            return True
            
        # 检查是否是完整URL
        if endpoint.startswith('http') and 'api' in endpoint_lower:
            return True
            
        return False
        
    async def analyze_all_js_files(self):
        """分析所有JavaScript文件"""
        print("=== 获取JavaScript文件列表 ===")
        js_files = await self.get_js_files()
        print(f"发现 {len(js_files)} 个JavaScript文件")
        
        all_endpoints = set()
        
        print("\n=== 分析JavaScript文件 ===")
        for i, js_file in enumerate(js_files[:15]):  # 限制分析前15个文件
            print(f"\n分析文件 {i+1}/{min(15, len(js_files))}: {js_file}")
            
            endpoints = await self.analyze_js_file(js_file)
            if endpoints:
                print(f"  发现 {len(endpoints)} 个可能的端点:")
                for endpoint in sorted(endpoints):
                    print(f"    - {endpoint}")
                    all_endpoints.add(endpoint)
            else:
                print("  未发现端点")
                
        print(f"\n=== 汇总结果 ===")
        print(f"总共发现 {len(all_endpoints)} 个唯一端点:")
        
        # 按类型分组显示
        api_endpoints = [ep for ep in all_endpoints if '/api/' in ep]
        generate_endpoints = [ep for ep in all_endpoints if 'generate' in ep.lower()]
        image_endpoints = [ep for ep in all_endpoints if 'image' in ep.lower()]
        other_endpoints = [ep for ep in all_endpoints if ep not in api_endpoints + generate_endpoints + image_endpoints]
        
        if api_endpoints:
            print(f"\nAPI端点 ({len(api_endpoints)}):")
            for ep in sorted(api_endpoints):
                print(f"  - {ep}")
                
        if generate_endpoints:
            print(f"\n生成相关端点 ({len(generate_endpoints)}):")
            for ep in sorted(generate_endpoints):
                print(f"  - {ep}")
                
        if image_endpoints:
            print(f"\n图像相关端点 ({len(image_endpoints)}):")
            for ep in sorted(image_endpoints):
                print(f"  - {ep}")
                
        if other_endpoints:
            print(f"\n其他端点 ({len(other_endpoints)}):")
            for ep in sorted(other_endpoints)[:10]:  # 只显示前10个
                print(f"  - {ep}")
                
        return all_endpoints

async def main():
    """主函数"""
    analyzer = VheerJSAnalyzer()
    
    try:
        await analyzer.initialize()
        print("Vheer JavaScript 分析器启动")
        print("=" * 50)
        
        endpoints = await analyzer.analyze_all_js_files()
        
        print("\n" + "=" * 50)
        print("分析完成")
        
        # 保存结果到文件
        with open('vheer_endpoints.json', 'w', encoding='utf-8') as f:
            json.dump(list(endpoints), f, indent=2, ensure_ascii=False)
        print("结果已保存到 vheer_endpoints.json")
        
    except Exception as e:
        print(f"分析过程中出错: {e}")
    finally:
        await analyzer.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
