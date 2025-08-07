@echo off
echo ========================================
echo 安装Chrome浏览器用于视频发布
echo ========================================
echo.

echo 正在检查Chrome是否已安装...
where chrome >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ Chrome已安装
    chrome --version
    echo.
    echo 如果发布仍有问题，请继续安装最新版本
    pause
) else (
    echo ❌ Chrome未安装
)

echo.
echo 正在使用winget安装Chrome...
winget install Google.Chrome

echo.
echo 安装完成！请重启命令行窗口，然后重新运行发布程序。
echo.
pause