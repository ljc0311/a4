"""
Vheer.com 图像生成引擎实现
通过逆向工程 Vheer 网站的 API 调用来实现图像生成
"""

import asyncio
import aiohttp
import requests
import os
import time
import json
import base64
import uuid
from typing import List, Dict, Optional, Callable
from ..image_engine_base import (
    ImageGenerationEngine, EngineType, EngineStatus, 
    GenerationConfig, GenerationResult, EngineInfo, ConfigConverter
)
from src.utils.logger import logger


class VheerEngine(ImageGenerationEngine):
    """Vheer.com 引擎实现"""
    
    def __init__(self, config: Dict = None):
        super().__init__(EngineType.VHEER)
        self.config = config or {}
        self.base_url = "https://vheer.com"
        self.api_url = None  # 将在初始化时发现
        self.output_dir = self.config.get('output_dir', 'temp/image_cache')
        self.session = None
        self.enable_browser_automation = self.config.get('enable_browser_automation', False)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        # 项目相关信息
        self.project_manager = None
        self.current_project_name = None
        
    async def initialize(self) -> bool:
        """初始化引擎"""
        try:
            # 动态获取输出目录
            self.output_dir = self._get_output_dir()
            
            # 创建aiohttp会话
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=60)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            )
            
            # 发现API端点
            if await self._discover_api_endpoints():
                # 测试连接
                if await self.test_connection():
                    self.status = EngineStatus.IDLE
                    logger.info("Vheer引擎初始化成功")
                    return True
                else:
                    self.status = EngineStatus.ERROR
                    logger.error("Vheer引擎连接测试失败")
                    return False
            else:
                self.status = EngineStatus.ERROR
                logger.error("Vheer引擎API端点发现失败")
                return False
                
        except Exception as e:
            self.status = EngineStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Vheer引擎初始化失败: {e}")
            return False
    
    async def _discover_api_endpoints(self) -> bool:
        """发现API端点"""
        try:
            # 访问主页面获取可能的API端点信息
            async with self.session.get(f"{self.base_url}/app/text-to-image") as response:
                if response.status == 200:
                    content = await response.text()

                    # 分析页面内容查找API端点
                    import re

                    # 查找可能的API端点模式
                    patterns = [
                        r'fetch\(["\']([^"\']*api[^"\']*)["\']',
                        r'axios\.[a-z]+\(["\']([^"\']*api[^"\']*)["\']',
                        r'\.post\(["\']([^"\']*generate[^"\']*)["\']',
                        r'action=["\']([^"\']*)["\']',
                        r'url:["\s]*["\']([^"\']*api[^"\']*)["\']',
                        r'endpoint:["\s]*["\']([^"\']*)["\']',
                    ]

                    found_endpoints = set()
                    for pattern in patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        found_endpoints.update(matches)

                    # 过滤有效的端点
                    valid_endpoints = []
                    for endpoint in found_endpoints:
                        if any(keyword in endpoint.lower() for keyword in ['api', 'generate', 'create']):
                            if endpoint.startswith('/'):
                                valid_endpoints.append(f"{self.base_url}{endpoint}")
                            elif endpoint.startswith('http'):
                                valid_endpoints.append(endpoint)

                    if valid_endpoints:
                        self.api_url = valid_endpoints[0]
                        logger.info(f"发现API端点: {self.api_url}")
                        return True
                    else:
                        # 使用常见的端点作为备选
                        common_endpoints = [
                            f"{self.base_url}/api/generate",
                            f"{self.base_url}/api/text-to-image",
                            f"{self.base_url}/generate",
                            f"{self.base_url}/_next/api/generate"
                        ]
                        self.api_url = common_endpoints[0]
                        logger.info(f"使用默认API端点: {self.api_url}")
                        return True
                else:
                    logger.error(f"无法访问Vheer主页: HTTP {response.status}")
                    return False

        except Exception as e:
            logger.error(f"发现API端点失败: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self.session:
                return False
                
            # 发送简单的测试请求到主页
            async with self.session.get(f"{self.base_url}") as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Vheer连接测试失败: {e}")
            return False
    
    def set_project_info(self, project_manager=None, current_project_name=None):
        """设置项目信息"""
        self.project_manager = project_manager
        self.current_project_name = current_project_name
        logger.info(f"Vheer引擎设置项目信息: project_manager={project_manager is not None}, current_project_name={current_project_name}")
    
    def _get_output_dir(self, project_manager=None, current_project_name=None) -> str:
        """获取输出目录"""
        try:
            # 优先使用传入的项目管理器
            if project_manager and current_project_name:
                try:
                    project_root = project_manager.get_current_project_path()
                    if project_root:
                        output_dir = os.path.join(project_root, 'images', 'vheer')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"使用项目输出目录: {output_dir}")
                        return output_dir
                except AttributeError:
                    if hasattr(project_manager, 'current_project') and project_manager.current_project:
                        project_root = project_manager.current_project.get('project_dir')
                        if project_root:
                            output_dir = os.path.join(project_root, 'images', 'vheer')
                            os.makedirs(output_dir, exist_ok=True)
                            logger.info(f"使用项目输出目录: {output_dir}")
                            return output_dir

            # 尝试使用实例变量
            if self.project_manager:
                try:
                    project_root = self.project_manager.get_current_project_path()
                    if project_root:
                        output_dir = os.path.join(project_root, 'images', 'vheer')
                        os.makedirs(output_dir, exist_ok=True)
                        logger.info(f"使用项目输出目录: {output_dir}")
                        return output_dir
                    else:
                        logger.info("当前没有加载项目，使用默认目录")
                except AttributeError:
                    if hasattr(self.project_manager, 'current_project') and self.project_manager.current_project:
                        project_root = self.project_manager.current_project.get('project_dir')
                        if project_root:
                            output_dir = os.path.join(project_root, 'images', 'vheer')
                            os.makedirs(output_dir, exist_ok=True)
                            logger.info(f"使用项目输出目录: {output_dir}")
                            return output_dir
                except Exception as e:
                    logger.warning(f"获取项目路径失败: {e}，使用默认目录")

        except Exception as e:
            logger.warning(f"无法获取项目目录: {e}")

        # 无项目时使用temp/image_cache
        output_dir = os.path.join(os.getcwd(), 'temp', 'image_cache', 'vheer')
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"使用默认输出目录: {output_dir}")
        return output_dir

    async def generate(self, config: GenerationConfig,
                      progress_callback: Optional[Callable] = None,
                      project_manager=None, current_project_name=None) -> GenerationResult:
        """生成图像"""
        # 设置项目信息
        if project_manager and current_project_name:
            self.project_manager = project_manager
            self.current_project_name = current_project_name
            # 更新输出目录
            self.output_dir = self._get_output_dir()

        start_time = time.time()
        self.status = EngineStatus.BUSY

        try:
            if progress_callback:
                progress_callback("准备Vheer生成请求...")

            # 转换配置
            vheer_config = self._convert_config(config)

            # 生成图像
            image_paths = []
            for i in range(config.batch_size):
                if progress_callback:
                    progress_callback(f"生成第 {i+1}/{config.batch_size} 张图像...")

                image_path = await self._generate_single_image(vheer_config, i)
                if image_path:
                    image_paths.append(image_path)
                else:
                    logger.warning(f"第 {i+1} 张图像生成失败")

                # 添加延迟避免请求过于频繁
                if i < config.batch_size - 1:
                    await asyncio.sleep(2)

            generation_time = time.time() - start_time
            success = len(image_paths) > 0

            # 更新统计
            self.update_stats(success, 0.0, "" if success else "部分或全部图像生成失败")

            result = GenerationResult(
                success=success,
                image_paths=image_paths,
                generation_time=generation_time,
                cost=0.0,  # Vheer免费
                engine_type=self.engine_type,
                metadata={
                    'total_requested': config.batch_size,
                    'total_generated': len(image_paths),
                    'config': vheer_config
                }
            )

            if not success:
                result.error_message = f"仅生成了 {len(image_paths)}/{config.batch_size} 张图像"

            return result

        except Exception as e:
            error_msg = f"Vheer生成失败: {e}"
            logger.error(error_msg)
            self.update_stats(False, 0.0, error_msg)

            return GenerationResult(
                success=False,
                error_message=error_msg,
                engine_type=self.engine_type
            )
        finally:
            self.status = EngineStatus.IDLE

    def _convert_config(self, config: GenerationConfig) -> Dict:
        """转换配置为Vheer格式"""
        workflow_id = config.custom_params.get('workflow_id', f'vheer_{uuid.uuid4().hex[:8]}')
        return {
            'prompt': config.prompt,
            'width': config.width,
            'height': config.height,
            'aspect_ratio': self._get_aspect_ratio(config.width, config.height),
            'model': 'quality',  # Vheer的默认模型
            'workflow_id': workflow_id
        }

    def _get_aspect_ratio(self, width: int, height: int) -> str:
        """获取宽高比字符串"""
        ratio_map = {
            (1, 1): "1:1",
            (1, 2): "1:2",
            (2, 1): "2:1",
            (2, 3): "2:3",
            (3, 2): "3:2",
            (9, 16): "9:16",
            (16, 9): "16:9"
        }

        # 计算最接近的比例
        target_ratio = width / height
        best_match = "1:1"
        min_diff = float('inf')

        for (w, h), ratio_str in ratio_map.items():
            ratio = w / h
            diff = abs(ratio - target_ratio)
            if diff < min_diff:
                min_diff = diff
                best_match = ratio_str

        return best_match

    async def _generate_single_image(self, config: Dict, index: int) -> Optional[str]:
        """生成单张图像"""
        try:
            # 方法1: 尝试直接API调用
            image_path = await self._try_direct_api_call(config, index)
            if image_path:
                return image_path

            # 方法2: 尝试模拟浏览器请求
            image_path = await self._try_browser_simulation(config, index)
            if image_path:
                return image_path

            # 方法3: 尝试Selenium自动化 (如果启用)
            image_path = await self._try_selenium_automation(config, index)
            if image_path:
                return image_path

            logger.error("所有生成方法都失败了")
            return None

        except Exception as e:
            logger.error(f"生成单张图像失败: {e}")
            return None

    async def _try_direct_api_call(self, config: Dict, index: int) -> Optional[str]:
        """尝试直接API调用"""
        try:
            # 尝试多种请求数据格式
            request_formats = [
                # 格式1: 标准格式
                {
                    'prompt': config['prompt'],
                    'aspect_ratio': config['aspect_ratio'],
                    'model': config['model'],
                    'width': config['width'],
                    'height': config['height']
                },
                # 格式2: 简化格式
                {
                    'prompt': config['prompt'],
                    'width': config['width'],
                    'height': config['height']
                },
                # 格式3: 文本格式
                {
                    'text': config['prompt'],
                    'size': f"{config['width']}x{config['height']}"
                },
                # 格式4: 表单格式
                {
                    'input': config['prompt'],
                    'ratio': config['aspect_ratio']
                }
            ]

            # 尝试不同的端点
            endpoints_to_try = [
                self.api_url,
                f"{self.base_url}/api/v1/generate",
                f"{self.base_url}/api/text-to-image",
                f"{self.base_url}/_next/api/generate",
                f"{self.base_url}/generate"
            ]

            for endpoint in endpoints_to_try:
                for request_data in request_formats:
                    try:
                        logger.info(f"尝试API调用: {endpoint} with {request_data}")

                        # 发送POST请求
                        async with self.session.post(
                            endpoint,
                            json=request_data,
                            headers={
                                **self.headers,
                                'Content-Type': 'application/json',
                                'Referer': f'{self.base_url}/app/text-to-image',
                                'Origin': self.base_url
                            }
                        ) as response:

                            if response.status == 200:
                                content_type = response.headers.get('content-type', '')

                                if 'image' in content_type:
                                    # 直接返回图像数据
                                    image_data = await response.read()
                                    return await self._save_image_data(image_data, config, index)
                                elif 'json' in content_type:
                                    result = await response.json()

                                    # 处理不同的响应格式
                                    image_url = self._extract_image_url(result)
                                    if image_url:
                                        return await self._download_image(image_url, config, index)
                                else:
                                    # 尝试作为文本处理
                                    text_result = await response.text()
                                    if text_result and len(text_result) < 1000:
                                        logger.info(f"文本响应: {text_result[:200]}...")
                            else:
                                logger.debug(f"端点 {endpoint} 返回状态: {response.status}")

                    except Exception as e:
                        logger.debug(f"端点 {endpoint} 调用失败: {e}")
                        continue

            logger.warning("所有API调用尝试都失败了")
            return None

        except Exception as e:
            logger.error(f"直接API调用失败: {e}")
            return None

    def _extract_image_url(self, result: Dict) -> Optional[str]:
        """从响应中提取图像URL"""
        # 尝试不同的字段名
        url_fields = [
            'image_url', 'url', 'imageUrl', 'image', 'src',
            'data.url', 'data.image_url', 'data.imageUrl',
            'result.url', 'result.image_url', 'result.imageUrl',
            'images.0.url', 'images.0.image_url'
        ]

        for field in url_fields:
            try:
                if '.' in field:
                    # 处理嵌套字段
                    parts = field.split('.')
                    value = result
                    for part in parts:
                        if part.isdigit():
                            value = value[int(part)]
                        else:
                            value = value[part]
                    if value and isinstance(value, str):
                        return value
                else:
                    # 处理简单字段
                    if field in result and result[field]:
                        return result[field]
            except (KeyError, IndexError, TypeError):
                continue

        return None

    async def _try_browser_simulation(self, config: Dict, index: int) -> Optional[str]:
        """尝试模拟浏览器请求"""
        try:
            logger.info("尝试模拟浏览器请求")

            # 首先访问页面获取必要的token或session信息
            async with self.session.get(f"{self.base_url}/app/text-to-image") as response:
                if response.status != 200:
                    logger.error("无法访问Vheer页面")
                    return None

                # 这里可以解析页面获取CSRF token等信息
                page_content = await response.text()

            # 模拟表单提交
            form_data = aiohttp.FormData()
            form_data.add_field('prompt', config['prompt'])
            form_data.add_field('aspect_ratio', config['aspect_ratio'])
            form_data.add_field('model', config['model'])

            # 尝试不同的可能端点
            possible_endpoints = [
                f"{self.base_url}/api/generate",
                f"{self.base_url}/api/text-to-image",
                f"{self.base_url}/generate",
                f"{self.base_url}/api/v1/generate"
            ]

            for endpoint in possible_endpoints:
                try:
                    async with self.session.post(
                        endpoint,
                        data=form_data,
                        headers={
                            **self.headers,
                            'Referer': f'{self.base_url}/app/text-to-image',
                            'Origin': self.base_url
                        }
                    ) as response:

                        if response.status == 200:
                            content_type = response.headers.get('content-type', '')

                            if 'image' in content_type:
                                # 直接返回图像数据
                                return await self._save_image_data(await response.read(), config, index)
                            elif 'json' in content_type:
                                # JSON响应，可能包含图像URL
                                result = await response.json()
                                if 'image_url' in result or 'url' in result:
                                    image_url = result.get('image_url') or result.get('url')
                                    return await self._download_image(image_url, config, index)

                except Exception as e:
                    logger.debug(f"端点 {endpoint} 失败: {e}")
                    continue

            logger.warning("所有端点都失败了")
            return None

        except Exception as e:
            logger.warning(f"浏览器模拟失败: {e}")
            return None

    async def _try_selenium_automation(self, config: Dict, index: int) -> Optional[str]:
        """尝试Selenium自动化方案"""
        try:
            logger.info("尝试Selenium自动化方案")

            # 检查是否启用了浏览器自动化
            if not getattr(self, 'enable_browser_automation', False):
                logger.info("浏览器自动化未启用，跳过")
                return None

            # 导入Selenium相关模块
            try:
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.chrome.options import Options
                import time
            except ImportError:
                logger.warning("Selenium未安装，跳过浏览器自动化")
                return None

            # 设置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # 无头模式
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            driver = None
            try:
                driver = webdriver.Chrome(options=chrome_options)

                # 访问页面
                driver.get(f"{self.base_url}/app/text-to-image")

                # 等待页面加载
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                # 查找输入框
                input_selectors = [
                    "textarea[placeholder*='prompt']",
                    "textarea[placeholder*='describe']",
                    "input[placeholder*='prompt']",
                    "textarea",
                    "input[type='text']"
                ]

                input_element = None
                for selector in input_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements and elements[0].is_displayed():
                            input_element = elements[0]
                            break
                    except:
                        continue

                if not input_element:
                    logger.warning("未找到输入框")
                    return None

                # 输入提示词
                input_element.clear()
                input_element.send_keys(config['prompt'])

                # 查找生成按钮
                button_selectors = [
                    "button[type='submit']",
                    "//button[contains(text(), 'Generate')]",
                    "//button[contains(text(), '生成')]",
                    "button"
                ]

                generate_button = None
                for selector in button_selectors:
                    try:
                        if selector.startswith("//"):
                            elements = driver.find_elements(By.XPATH, selector)
                        else:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)

                        if elements and elements[0].is_displayed():
                            generate_button = elements[0]
                            break
                    except:
                        continue

                if not generate_button:
                    logger.warning("未找到生成按钮")
                    return None

                # 点击生成按钮
                generate_button.click()

                # 等待图像生成
                max_wait = 60
                start_time = time.time()

                while time.time() - start_time < max_wait:
                    # 查找生成的图像
                    img_selectors = [
                        "img[src*='blob:']",
                        "img[src*='data:image']",
                        "img[src*='generated']",
                        ".result-image img",
                        ".output-image img"
                    ]

                    for selector in img_selectors:
                        try:
                            images = driver.find_elements(By.CSS_SELECTOR, selector)
                            for img in images:
                                if img.is_displayed():
                                    src = img.get_attribute('src')
                                    if src:
                                        # 下载图像
                                        return await self._download_selenium_image(src, config, index, driver)
                        except:
                            continue

                    time.sleep(2)

                logger.warning("等待图像生成超时")
                return None

            finally:
                if driver:
                    driver.quit()

        except Exception as e:
            logger.error(f"Selenium自动化失败: {e}")
            return None

    async def _download_selenium_image(self, image_src: str, config: Dict, index: int, driver) -> Optional[str]:
        """下载Selenium获取的图像"""
        try:
            import base64

            if image_src.startswith('data:image'):
                # 处理Base64图像
                header, data = image_src.split(',', 1)
                image_data = base64.b64decode(data)

                # 保存图像
                timestamp = int(time.time())
                filename = f"vheer_selenium_{timestamp}_{index}.png"
                filepath = os.path.join(self.output_dir, filename)

                with open(filepath, 'wb') as f:
                    f.write(image_data)

                logger.info(f"Selenium图像保存成功: {filepath}")
                return filepath

            elif image_src.startswith('blob:'):
                # 处理Blob URL
                script = f"""
                return new Promise((resolve) => {{
                    fetch('{image_src}')
                        .then(response => response.blob())
                        .then(blob => {{
                            const reader = new FileReader();
                            reader.onload = () => resolve(reader.result);
                            reader.readAsDataURL(blob);
                        }})
                        .catch(() => resolve(null));
                }});
                """

                data_url = driver.execute_async_script(script)
                if data_url:
                    return await self._download_selenium_image(data_url, config, index, driver)

            else:
                # 处理普通URL
                async with self.session.get(image_src) as response:
                    if response.status == 200:
                        image_data = await response.read()

                        timestamp = int(time.time())
                        filename = f"vheer_selenium_{timestamp}_{index}.png"
                        filepath = os.path.join(self.output_dir, filename)

                        with open(filepath, 'wb') as f:
                            f.write(image_data)

                        logger.info(f"Selenium图像下载成功: {filepath}")
                        return filepath

        except Exception as e:
            logger.error(f"下载Selenium图像失败: {e}")

        return None

    async def _download_image(self, image_url: str, config: Dict, index: int) -> Optional[str]:
        """下载图像"""
        try:
            # 确保URL是完整的
            if image_url.startswith('/'):
                image_url = self.base_url + image_url
            elif not image_url.startswith('http'):
                image_url = f"{self.base_url}/{image_url}"

            logger.info(f"下载图像: {image_url}")

            async with self.session.get(image_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    return await self._save_image_data(image_data, config, index)
                else:
                    logger.error(f"下载图像失败: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"下载图像失败: {e}")
            return None

    async def _save_image_data(self, image_data: bytes, config: Dict, index: int) -> Optional[str]:
        """保存图像数据"""
        try:
            # 动态获取输出目录
            current_output_dir = self._get_output_dir()
            os.makedirs(current_output_dir, exist_ok=True)

            # 生成文件名
            workflow_id = config.get('workflow_id', f'shot_{index}')
            safe_workflow_id = workflow_id.replace('-', '_').replace(':', '_')
            filename = f"vheer_{safe_workflow_id}.png"
            filepath = os.path.join(current_output_dir, filename)

            # 保存图像
            with open(filepath, 'wb') as f:
                f.write(image_data)

            logger.info(f"图像已保存: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"保存图像失败: {e}")
            return None

    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        return [
            'quality',  # Vheer的质量模型
            'speed',    # 可能的快速模型
            'artistic', # 可能的艺术模型
        ]

    def get_engine_info(self) -> EngineInfo:
        """获取引擎信息"""
        return EngineInfo(
            name="Vheer.com",
            version="1.0",
            description="Vheer.com AI图像生成服务，通过逆向工程实现",
            is_free=True,
            supports_batch=True,
            supports_custom_models=False,
            max_batch_size=5,  # 限制批量大小避免被封
            supported_sizes=[
                (512, 512), (768, 768), (1024, 1024),
                (1024, 768), (768, 1024),
                (1280, 720), (720, 1280),
                (512, 1024), (1024, 512)
            ],
            cost_per_image=0.0,
            rate_limit=30  # 保守的速率限制
        )

    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()
            self.session = None

        self.status = EngineStatus.OFFLINE
        await super().cleanup()
