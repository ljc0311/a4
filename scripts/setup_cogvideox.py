#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CogVideoX-Flash 快速设置脚本
帮助用户快速配置和测试CogVideoX-Flash视频生成功能
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_banner():
    """打印欢迎横幅"""
    print("=" * 60)
    print("🎬 CogVideoX-Flash 视频生成引擎设置向导")
    print("=" * 60)
    print("欢迎使用智谱AI免费视频生成服务！")
    print("本向导将帮助您快速配置和测试CogVideoX-Flash引擎。")
    print()


def check_dependencies():
    """检查依赖项"""
    print("🔍 检查依赖项...")
    
    required_packages = [
        'aiohttp',
        'asyncio',
        'pathlib',
    ]
    
    optional_packages = [
        ('PIL', 'Pillow', '用于图像处理'),
        ('numpy', 'numpy', '用于图像数组操作'),
        ('cv2', 'opencv-python', '用于视频信息获取'),
    ]
    
    missing_required = []
    missing_optional = []
    
    # 检查必需包
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            missing_required.append(package)
            print(f"  ❌ {package}")
    
    # 检查可选包
    for import_name, package_name, description in optional_packages:
        try:
            __import__(import_name)
            print(f"  ✅ {package_name} ({description})")
        except ImportError:
            missing_optional.append((package_name, description))
            print(f"  ⚠️ {package_name} ({description}) - 可选")
    
    if missing_required:
        print(f"\n❌ 缺少必需依赖项: {', '.join(missing_required)}")
        print("请运行: pip install " + " ".join(missing_required))
        return False
    
    if missing_optional:
        print(f"\n⚠️ 缺少可选依赖项:")
        for package_name, description in missing_optional:
            print(f"  - {package_name}: {description}")
        print("建议安装: pip install " + " ".join([p[0] for p in missing_optional]))
    
    print("✅ 依赖项检查完成")
    return True


def setup_api_key():
    """设置API密钥"""
    print("\n🔑 配置API密钥")
    print("-" * 30)
    
    # 检查环境变量
    existing_key = os.getenv('ZHIPU_API_KEY')
    if existing_key:
        print(f"✅ 发现环境变量中的API密钥: {existing_key[:8]}...")
        use_existing = input("是否使用现有密钥？(y/n): ").lower().strip()
        if use_existing in ['y', 'yes', '']:
            return existing_key
    
    print("\n📝 请获取您的智谱AI API密钥:")
    print("1. 访问: https://open.bigmodel.cn/")
    print("2. 注册并登录账号")
    print("3. 在控制台中创建API密钥")
    print("4. 复制密钥并粘贴到下方")
    print()
    
    while True:
        api_key = input("请输入您的API密钥: ").strip()
        if not api_key:
            print("❌ API密钥不能为空")
            continue
        
        if len(api_key) < 10:
            print("❌ API密钥长度似乎不正确")
            continue
        
        # 询问是否保存到环境变量
        save_env = input("是否保存到环境变量？(y/n): ").lower().strip()
        if save_env in ['y', 'yes']:
            print(f"\n💡 请将以下命令添加到您的shell配置文件中:")
            print(f"export ZHIPU_API_KEY='{api_key}'")
            print("然后重新启动终端或运行: source ~/.bashrc")
        
        return api_key


def create_config_file(api_key):
    """创建配置文件"""
    print("\n📄 创建配置文件...")
    
    config_dir = Path("config")
    config_file = config_dir / "video_generation_config.py"
    
    # 检查是否已存在配置文件
    if config_file.exists():
        print(f"⚠️ 配置文件已存在: {config_file}")
        overwrite = input("是否覆盖现有配置？(y/n): ").lower().strip()
        if overwrite not in ['y', 'yes']:
            print("保持现有配置文件")
            return str(config_file)
    
    # 读取示例配置
    example_file = config_dir / "video_generation_config.example.py"
    if example_file.exists():
        with open(example_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换API密钥
        content = content.replace('YOUR_ZHIPU_API_KEY_HERE', api_key)
        
        # 写入配置文件
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 配置文件已创建: {config_file}")
        return str(config_file)
    else:
        print(f"❌ 示例配置文件不存在: {example_file}")
        return None


async def test_connection(api_key):
    """测试连接"""
    print("\n🔗 测试连接...")
    
    try:
        from src.models.video_engines.video_generation_service import VideoGenerationService
        from config.video_generation_config import get_config
        
        # 创建临时配置
        config = get_config('development')
        config['engines']['cogvideox_flash']['api_key'] = api_key
        
        service = VideoGenerationService(config)
        
        # 测试连接
        result = await service.test_engine('cogvideox_flash')
        
        if result:
            print("✅ 连接测试成功！")
            
            # 获取引擎信息
            info = service.get_engine_info('cogvideox_flash')
            if info:
                print(f"📊 引擎信息:")
                print(f"  名称: {info['name']}")
                print(f"  免费: {'是' if info['is_free'] else '否'}")
                print(f"  最大时长: {info['max_duration']}秒")
                print(f"  支持分辨率: {len(info['supported_resolutions'])}种")
        else:
            print("❌ 连接测试失败")
            print("请检查API密钥是否正确，或网络连接是否正常")
        
        await service.shutdown()
        return result
        
    except Exception as e:
        print(f"❌ 测试连接时出错: {e}")
        return False


async def run_demo(api_key):
    """运行演示"""
    print("\n🎬 运行演示...")
    
    try:
        from src.models.video_engines.video_generation_service import generate_video_simple
        import tempfile
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            print("正在生成演示视频...")
            print("提示词: 一朵花在微风中轻轻摇摆")
            
            result = await generate_video_simple(
                prompt="一朵花在微风中轻轻摇摆",
                duration=3.0,
                output_dir=temp_dir,
                api_key=api_key
            )
            
            if result.success:
                print(f"✅ 演示视频生成成功!")
                print(f"  路径: {result.video_path}")
                print(f"  时长: {result.duration:.1f}秒")
                print(f"  生成时间: {result.generation_time:.1f}秒")
                print(f"  文件大小: {result.file_size / 1024 / 1024:.2f}MB")
                
                # 询问是否保存到永久位置
                save_demo = input("\n是否将演示视频保存到output目录？(y/n): ").lower().strip()
                if save_demo in ['y', 'yes']:
                    import shutil
                    output_dir = Path("output/videos")
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    demo_path = output_dir / "cogvideox_demo.mp4"
                    shutil.copy2(result.video_path, demo_path)
                    print(f"✅ 演示视频已保存到: {demo_path}")
                
                return True
            else:
                print(f"❌ 演示视频生成失败: {result.error_message}")
                return False
                
    except Exception as e:
        print(f"❌ 运行演示时出错: {e}")
        return False


def print_next_steps():
    """打印后续步骤"""
    print("\n🎉 设置完成！")
    print("=" * 40)
    print("📚 后续步骤:")
    print("1. 查看使用示例: python examples/cogvideox_usage_examples.py")
    print("2. 运行完整测试: python tests/test_cogvideox_integration.py")
    print("3. 阅读详细文档: docs/cogvideox_integration_guide.md")
    print("4. 在您的项目中使用:")
    print()
    print("   from src.models.video_engines.video_generation_service import generate_video_simple")
    print("   result = await generate_video_simple('您的提示词', api_key='您的密钥')")
    print()
    print("💡 提示:")
    print("- CogVideoX-Flash完全免费使用")
    print("- 支持最长10秒视频生成")
    print("- 支持文生视频和图生视频")
    print("- 支持最高4K分辨率输出")


async def main():
    """主函数"""
    print_banner()
    
    # 检查依赖项
    if not check_dependencies():
        print("\n❌ 请先安装必需的依赖项")
        return
    
    # 设置API密钥
    api_key = setup_api_key()
    if not api_key:
        print("\n❌ 未配置API密钥，设置中止")
        return
    
    # 创建配置文件
    config_file = create_config_file(api_key)
    if not config_file:
        print("\n❌ 配置文件创建失败")
        return
    
    # 测试连接
    connection_ok = await test_connection(api_key)
    if not connection_ok:
        print("\n❌ 连接测试失败，请检查配置")
        return
    
    # 询问是否运行演示
    run_demo_choice = input("\n是否运行演示生成一个测试视频？(y/n): ").lower().strip()
    if run_demo_choice in ['y', 'yes']:
        demo_ok = await run_demo(api_key)
        if not demo_ok:
            print("⚠️ 演示运行失败，但基本配置已完成")
    
    # 打印后续步骤
    print_next_steps()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 设置已取消")
    except Exception as e:
        print(f"\n❌ 设置过程中出错: {e}")
        print("请检查错误信息并重试")
