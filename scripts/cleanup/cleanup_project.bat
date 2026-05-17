@echo off
REM ============================================
REM 项目文件清理脚本 (Windows)
REM ============================================

echo.
echo ========================================
echo   项目文件清理工具
echo ========================================
echo.

echo 此脚本将清理以下文件：
echo   1. Python 缓存文件 (__pycache__, *.pyc)
echo   2. 测试缓存 (.pytest_cache)
echo   3. 日志文件 (*.log)
echo   4. 临时文件 (-ContentType, -InFile, -Method, -Uri)
echo   5. 运行时数据（可选）
echo.

set /p confirm="是否继续？(y/n): "
if /i not "%confirm%"=="y" (
    echo 已取消
    pause
    exit /b 0
)

echo.
echo [1/5] 清理 Python 缓存...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc >nul 2>&1
echo [OK] Python 缓存已清理

echo.
echo [2/5] 清理测试缓存...
if exist ".pytest_cache" rd /s /q ".pytest_cache"
echo [OK] 测试缓存已清理

echo.
echo [3/5] 清理日志文件...
del /s /q *.log >nul 2>&1
del /s /q err.log >nul 2>&1
del /s /q out.log >nul 2>&1
echo [OK] 日志文件已清理

echo.
echo [4/5] 清理临时文件...
if exist "-ContentType" del "-ContentType"
if exist "-InFile" del "-InFile"
if exist "-Method" del "-Method"
if exist "-Uri" del "-Uri"
echo [OK] 临时文件已清理

echo.
set /p clean_runtime="是否清理运行时数据？(y/n，谨慎操作): "
if /i "%clean_runtime%"=="y" (
    echo [5/5] 清理运行时数据...
    if exist "runtime\tasks" (
        for /d %%d in (runtime\tasks\*) do (
            if exist "%%d\attempts" rd /s /q "%%d\attempts"
        )
    )
    if exist "runtime\audio_cache" (
        for /d %%d in (runtime\audio_cache\*) do rd /s /q "%%d"
    )
    echo [OK] 运行时数据已清理
) else (
    echo [SKIP] 跳过运行时数据清理
)

echo.
echo ========================================
echo   清理完成！
echo ========================================
echo.
echo 注意：
echo   - runtime/tasks 目录结构已保留
echo   - .gitkeep 文件未被删除
echo   - 建议定期运行此脚本保持项目整洁
echo.

pause
