#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI一键发布功能演示脚本
通过程序界面演示一键发布功能
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer

from src.gui.new_main_window import NewMainWindow
from src.utils.logger import logger


class PublishGUIDemo:
    """GUI发布演示"""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        
    def setup_application(self):
        """设置应用程序"""
        try:
            # 创建QApplication
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("AI视频生成器 - 一键发布演示")
            
            # 创建主窗口
            self.main_window = NewMainWindow()
            
            print("✅ GUI应用程序初始化完成")
            return True
            
        except Exception as e:
            print(f"❌ GUI应用程序初始化失败: {e}")
            return False
            
    def show_demo_instructions(self):
        """显示演示说明"""
        instructions = """
🎬 AI视频生成器 - 一键发布功能演示

📋 演示步骤：
1. 程序将自动打开主界面
2. 切换到"一键发布"标签页
3. 选择测试视频文件
4. 填写视频信息（标题、描述、标签）
5. 选择发布平台（建议先选择一个平台测试）
6. 点击"开始发布"按钮
7. 观察发布进度和结果

⚠️ 重要提醒：
• 确保Chrome调试模式已启动 (127.0.0.1:9222)
• 确保已在浏览器中登录相关平台账号
• 建议先使用模拟模式测试，再进行真实发布
• 真实发布会实际上传视频到平台

🔧 技术特点：
• 支持抖音、B站、快手、小红书等平台
• 全自动化发布流程
• 智能错误处理和重试
• 实时进度显示

按回车键继续...
        """
        
        print(instructions)
        input()
        
    def navigate_to_publish_tab(self):
        """导航到发布标签页"""
        try:
            if not self.main_window:
                print("❌ 主窗口未初始化")
                return False
                
            # 查找一键发布标签页
            tab_widget = self.main_window.tab_widget
            
            for i in range(tab_widget.count()):
                tab_text = tab_widget.tabText(i)
                if "发布" in tab_text or "publish" in tab_text.lower():
                    tab_widget.setCurrentIndex(i)
                    print(f"✅ 已切换到标签页: {tab_text}")
                    return True
                    
            print("❌ 未找到发布标签页")
            return False
            
        except Exception as e:
            print(f"❌ 导航到发布标签页失败: {e}")
            return False
            
    def setup_demo_data(self):
        """设置演示数据"""
        try:
            # 查找测试视频
            output_dir = Path("output")
            test_video = None
            
            for project_dir in output_dir.iterdir():
                if project_dir.is_dir():
                    final_video = project_dir / "final_video.mp4"
                    if final_video.exists():
                        test_video = str(final_video)
                        break
                        
            if not test_video:
                print("❌ 未找到测试视频文件")
                return False
                
            print(f"✅ 找到测试视频: {test_video}")
            
            # 演示数据
            demo_data = {
                'video_path': test_video,
                'title': 'AI视频生成器 - 一键发布演示',
                'description': '''🤖 AI视频生成器一键发布功能演示

✨ 主要特点：
• 全自动多平台发布
• 智能内容识别  
• 一键操作，高效便捷
• 支持主流视频平台

#AI视频 #自动发布 #效率工具''',
                'tags': 'AI视频,自动发布,效率工具,演示',
                'platforms': ['douyin']  # 建议先测试一个平台
            }
            
            print("✅ 演示数据准备完成")
            print(f"   视频: {demo_data['title']}")
            print(f"   平台: {', '.join(demo_data['platforms'])}")
            
            return demo_data
            
        except Exception as e:
            print(f"❌ 设置演示数据失败: {e}")
            return None
            
    def show_usage_tips(self):
        """显示使用提示"""
        tips = """
💡 使用提示：

1. 📁 选择视频文件：
   - 点击"选择视频"按钮
   - 选择要发布的视频文件
   - 支持MP4、AVI、MOV等格式

2. ✏️ 填写视频信息：
   - 标题：简洁明了，吸引眼球
   - 描述：详细介绍视频内容
   - 标签：用逗号分隔，便于搜索

3. 🎯 选择发布平台：
   - 勾选要发布的平台
   - 建议先测试单个平台
   - 确保已登录相应账号

4. ⚙️ 发布设置：
   - 模拟模式：安全测试，不实际发布
   - 真实模式：实际发布到平台
   - 自动发布：完成后自动提交

5. 🚀 开始发布：
   - 点击"开始发布"按钮
   - 观察进度条和状态信息
   - 等待发布完成

6. 📊 查看结果：
   - 查看发布结果统计
   - 检查成功/失败状态
   - 根据提示处理问题

现在程序界面将打开，请按照上述步骤进行操作...
        """
        
        print(tips)
        
    def run_demo(self):
        """运行GUI演示"""
        try:
            print("🎬 AI视频生成器 - GUI一键发布功能演示")
            print("=" * 60)
            
            # 1. 显示演示说明
            self.show_demo_instructions()
            
            # 2. 设置应用程序
            print("\n⚙️ 正在初始化GUI应用程序...")
            if not self.setup_application():
                return False
                
            # 3. 准备演示数据
            print("\n📋 正在准备演示数据...")
            demo_data = self.setup_demo_data()
            if not demo_data:
                return False
                
            # 4. 显示使用提示
            print("\n💡 显示使用提示...")
            self.show_usage_tips()
            
            # 5. 显示主窗口
            print("\n🖥️ 正在显示主窗口...")
            self.main_window.show()
            
            # 6. 设置定时器来导航到发布标签页
            def navigate_after_startup():
                self.navigate_to_publish_tab()
                print("\n✅ GUI演示准备完成！")
                print("🎯 请在界面中体验一键发布功能")
                
            QTimer.singleShot(2000, navigate_after_startup)  # 2秒后执行
            
            # 7. 运行应用程序
            print("\n🚀 启动GUI应用程序...")
            return self.app.exec_()
            
        except Exception as e:
            print(f"❌ GUI演示运行失败: {e}")
            return False
            
        finally:
            if self.app:
                self.app.quit()


def main():
    """主函数"""
    demo = PublishGUIDemo()
    
    try:
        result = demo.run_demo()
        
        if result == 0:  # QApplication正常退出
            print("\n✅ GUI演示完成")
            print("🎉 感谢体验一键发布功能！")
            return True
        else:
            print("\n❌ GUI演示异常退出")
            return False
            
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断演示")
        return False
        
    except Exception as e:
        print(f"\n❌ 演示执行失败: {e}")
        return False


if __name__ == "__main__":
    print("🎬 启动GUI一键发布功能演示...")
    
    success = main()
    
    if success:
        print("✨ 演示成功完成！")
    else:
        print("⚠️ 演示遇到问题。")
        
    sys.exit(0 if success else 1)
