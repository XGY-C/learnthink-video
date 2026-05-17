@echo off

echo.
echo ========================================
echo Complete Project Reorganization
echo ========================================
echo.

set /p confirm="Continue? Type YES: "
if not "%confirm%"=="YES" goto :cancel

echo.
echo Creating directories...

mkdir scripts\setup 2>nul
mkdir scripts\cleanup 2>nul
mkdir scripts\dev 2>nul
mkdir scripts\deployment 2>nul
mkdir examples\requests 2>nul
mkdir examples\curl 2>nul
mkdir examples\demos 2>nul
mkdir docs\guides 2>nul
mkdir docs\legacy 2>nul

echo Done.

echo.
echo Moving setup scripts...
move setup_deepseek.bat scripts\setup\ >nul 2>&1
move setup_deepseek.sh scripts\setup\ >nul 2>&1

echo Moving cleanup scripts...
move cleanup_project.bat scripts\cleanup\ >nul 2>&1
move cleanup_project.sh scripts\cleanup\ >nul 2>&1
move cleanup_runtime.bat scripts\cleanup\ >nul 2>&1
move cleanup_runtime.sh scripts\cleanup\ >nul 2>&1
move reorganize_project.bat scripts\cleanup\ >nul 2>&1
move reorganize_project.sh scripts\cleanup\ >nul 2>&1

echo Moving dev tools...
move start_dev.ps1 scripts\dev\ >nul 2>&1
move check_console_logs.ps1 scripts\dev\ >nul 2>&1
move test_deepseek_thinking.py scripts\dev\ >nul 2>&1

echo Moving deployment tools...
move create_deployment_package.py scripts\deployment\ >nul 2>&1
move start.sh scripts\deployment\ >nul 2>&1
move Dockerfile scripts\deployment\ >nul 2>&1

echo Moving examples...
move sample_request.json examples\requests\ >nul 2>&1
move curl_example.sh examples\curl\ >nul 2>&1
move demo_doc_search.py examples\demos\ >nul 2>&1

echo Moving documents...
move CLEANUP_RUNTIME_GUIDE.md docs\guides\ >nul 2>&1
move FILE_REORGANIZATION_PROPOSAL.md docs\guides\ >nul 2>&1
move REORGANIZATION_GUIDE.md docs\guides\ >nul 2>&1
move "使用说明文档.md" docs\guides\ >nul 2>&1
move README_CN.md docs\legacy\ >nul 2>&1

echo Moving legacy directory...
if exist document move document docs\legacy\ >nul 2>&1

echo.
echo ========================================
echo Complete!
echo ========================================
echo.
echo Root directory is now clean.
echo Check scripts/ and examples/ directories.
echo.
pause
exit /b 0

:cancel
echo Cancelled.
pause
exit /b 0
