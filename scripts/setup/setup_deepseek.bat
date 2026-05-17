@echo off
REM ============================================
REM DeepSeek 配置快速设置脚本 (Windows)
REM ============================================

echo.
echo ========================================
echo   DeepSeek 思考模式配置向导
echo ========================================
echo.

REM 检查 .env 文件是否存在
if not exist .env (
    echo [INFO] 未找到 .env 文件，从 .env.example 创建...
    copy .env.example .env >nul
    echo [OK] 已创建 .env 文件
    echo.
)

echo 请选择要使用的配置模板：
echo.
echo 1. DeepSeek V4 Pro + 思考模式 max（推荐 - 最强性能）
echo 2. DeepSeek V4 Pro + 思考模式 high（标准配置）
echo 3. DeepSeek V4 Flash + 思考模式 high（性价比）
echo 4. DeepSeek V4 Flash（无思考模式，最快）
echo 5. OpenAI GPT-4 Turbo
echo 6. 保持当前配置不变
echo.

set /p choice="请输入选项 (1-6): "

if "%choice%"=="1" goto config_v4pro_max
if "%choice%"=="2" goto config_v4pro_high
if "%choice%"=="3" goto config_v4flash_thinking
if "%choice%"=="4" goto config_v4flash_nothinking
if "%choice%"=="5" goto config_openai
if "%choice%"=="6" goto keep_current
goto invalid_choice

:config_v4pro_max
echo.
echo [INFO] 配置: DeepSeek V4 Pro + 思考模式 max
echo.
set API_KEY=
set /p API_KEY="请输入你的 DeepSeek API Key: "

if "%API_KEY%"=="" (
    echo [ERROR] API Key 不能为空
    pause
    exit /b 1
)

REM 使用 PowerShell 更新 .env 文件
powershell -Command "(Get-Content .env) -replace '^ENABLE_LLM_ASSIST=.*', 'ENABLE_LLM_ASSIST=true' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_PROVIDER=.*', 'LLM_PROVIDER=deepseek' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_BASE_URL=.*', 'LLM_BASE_URL=https://api.deepseek.com/v1' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_API_KEY=.*', 'LLM_API_KEY=%API_KEY%' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_MODEL=.*', 'LLM_MODEL=deepseek-v4-pro' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^DEEPSEEK_ENABLE_THINKING=.*', 'DEEPSEEK_ENABLE_THINKING=true' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^DEEPSEEK_REASONING_EFFORT=.*', 'DEEPSEEK_REASONING_EFFORT=max' | Set-Content .env"

echo [OK] 配置已更新
goto test_config

:config_v4pro_high
echo.
echo [INFO] 配置: DeepSeek V4 Pro + 思考模式 high
echo.
set API_KEY=
set /p API_KEY="请输入你的 DeepSeek API Key: "

if "%API_KEY%"=="" (
    echo [ERROR] API Key 不能为空
    pause
    exit /b 1
)

powershell -Command "(Get-Content .env) -replace '^ENABLE_LLM_ASSIST=.*', 'ENABLE_LLM_ASSIST=true' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_PROVIDER=.*', 'LLM_PROVIDER=deepseek' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_BASE_URL=.*', 'LLM_BASE_URL=https://api.deepseek.com/v1' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_API_KEY=.*', 'LLM_API_KEY=%API_KEY%' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_MODEL=.*', 'LLM_MODEL=deepseek-v4-pro' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^DEEPSEEK_ENABLE_THINKING=.*', 'DEEPSEEK_ENABLE_THINKING=true' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^DEEPSEEK_REASONING_EFFORT=.*', 'DEEPSEEK_REASONING_EFFORT=high' | Set-Content .env"

echo [OK] 配置已更新
goto test_config

:config_v4flash_thinking
echo.
echo [INFO] 配置: DeepSeek V4 Flash + 思考模式 high
echo.
set API_KEY=
set /p API_KEY="请输入你的 DeepSeek API Key: "

if "%API_KEY%"=="" (
    echo [ERROR] API Key 不能为空
    pause
    exit /b 1
)

powershell -Command "(Get-Content .env) -replace '^ENABLE_LLM_ASSIST=.*', 'ENABLE_LLM_ASSIST=true' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_PROVIDER=.*', 'LLM_PROVIDER=deepseek' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_BASE_URL=.*', 'LLM_BASE_URL=https://api.deepseek.com/v1' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_API_KEY=.*', 'LLM_API_KEY=%API_KEY%' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_MODEL=.*', 'LLM_MODEL=deepseek-v4-flash' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^DEEPSEEK_ENABLE_THINKING=.*', 'DEEPSEEK_ENABLE_THINKING=true' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^DEEPSEEK_REASONING_EFFORT=.*', 'DEEPSEEK_REASONING_EFFORT=high' | Set-Content .env"

echo [OK] 配置已更新
goto test_config

:config_v4flash_nothinking
echo.
echo [INFO] 配置: DeepSeek V4 Flash（无思考模式）
echo.
set API_KEY=
set /p API_KEY="请输入你的 DeepSeek API Key: "

if "%API_KEY%"=="" (
    echo [ERROR] API Key 不能为空
    pause
    exit /b 1
)

powershell -Command "(Get-Content .env) -replace '^ENABLE_LLM_ASSIST=.*', 'ENABLE_LLM_ASSIST=true' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_PROVIDER=.*', 'LLM_PROVIDER=deepseek' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_BASE_URL=.*', 'LLM_BASE_URL=https://api.deepseek.com/v1' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_API_KEY=.*', 'LLM_API_KEY=%API_KEY%' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_MODEL=.*', 'LLM_MODEL=deepseek-v4-flash' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^DEEPSEEK_ENABLE_THINKING=.*', 'DEEPSEEK_ENABLE_THINKING=false' | Set-Content .env"

echo [OK] 配置已更新
goto test_config

:config_openai
echo.
echo [INFO] 配置: OpenAI GPT-4 Turbo
echo.
set API_KEY=
set /p API_KEY="请输入你的 OpenAI API Key: "

if "%API_KEY%"=="" (
    echo [ERROR] API Key 不能为空
    pause
    exit /b 1
)

powershell -Command "(Get-Content .env) -replace '^ENABLE_LLM_ASSIST=.*', 'ENABLE_LLM_ASSIST=true' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_PROVIDER=.*', 'LLM_PROVIDER=openai' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_BASE_URL=.*', 'LLM_BASE_URL=https://api.openai.com/v1' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_API_KEY=.*', 'LLM_API_KEY=%API_KEY%' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^LLM_MODEL=.*', 'LLM_MODEL=gpt-4-turbo' | Set-Content .env"

echo [OK] 配置已更新
goto test_config

:keep_current
echo.
echo [INFO] 保持当前配置不变
goto show_info

:invalid_choice
echo.
echo [ERROR] 无效的选项
pause
exit /b 1

:test_config
echo.
echo 是否运行配置测试？(Y/N)
set /p run_test="请输入: "

if /i "%run_test%"=="Y" goto run_test
if /i "%run_test%"=="y" goto run_test
goto show_info

:run_test
echo.
echo [INFO] 运行配置测试...
python test_deepseek_thinking.py
goto end

:show_info
echo.
echo ========================================
echo   配置完成！
echo ========================================
echo.
echo 当前配置摘要：
findstr /C:"ENABLE_LLM_ASSIST" /C:"LLM_PROVIDER" /C:"LLM_MODEL" /C:"DEEPSEEK_ENABLE_THINKING" .env
echo.
echo 下一步：
echo   1. 启动服务: python -m app.main
echo   2. 或开发模式: uvicorn app.main:app --reload
echo   3. 查看详细文档: DEEPSEEK_THINKING_GUIDE.md
echo.

:end
pause
