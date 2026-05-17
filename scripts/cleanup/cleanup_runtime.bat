@echo off
chcp 65001 >nul

echo.
echo ========================================
echo Runtime Directory Cleanup Tool
echo ========================================
echo.
echo This script will clean the runtime/ directory:
echo   - Remove all task execution files
echo   - Clear audio cache
echo   - Keep directory structure (.gitkeep)
echo.
echo WARNING: All generated videos and logs will be deleted!
echo.

set /p confirm="Continue? Type YES: "
if not "%confirm%"=="YES" (
    echo Cancelled
    pause
    exit /b 0
)

echo.
echo [Step 1] Cleaning runtime/tasks/...

if exist "runtime\tasks" (
    for /d %%d in (runtime\tasks\*) do (
        if exist "%%d\attempts" (
            echo   Removing attempts in %%~nxd
            rd /s /q "%%d\attempts" 2>nul
        )
        if exist "%%d\*.log" (
            echo   Removing logs in %%~nxd
            del /f /q "%%d\*.log" 2>nul
        )
        if exist "%%d\*.mp4" (
            echo   Removing videos in %%~nxd
            del /f /q "%%d\*.mp4" 2>nul
        )
        if exist "%%d\*.png" (
            echo   Removing images in %%~nxd
            del /f /q "%%d\*.png" 2>nul
        )
    )
    echo [OK] Task files cleaned
) else (
    echo [SKIP] runtime/tasks/ does not exist
)

echo.
echo [Step 2] Cleaning runtime/audio_cache/...

if exist "runtime\audio_cache" (
    for /d %%d in (runtime\audio_cache\*) do (
        echo   Removing cache: %%~nxd
        rd /s /q "%%d" 2>nul
    )
    echo [OK] Audio cache cleaned
) else (
    echo [SKIP] runtime/audio_cache/ does not exist
)

echo.
echo [Step 3] Verifying directory structure...

if not exist "runtime\tasks\.gitkeep" (
    if exist "runtime\tasks" (
        echo. > "runtime\tasks\.gitkeep"
        echo   Created runtime/tasks/.gitkeep
    )
)

if not exist "runtime\audio_cache\.gitkeep" (
    if exist "runtime\audio_cache" (
        echo. > "runtime\audio_cache\.gitkeep"
        echo   Created runtime/audio_cache/.gitkeep
    )
)

echo [OK] Directory structure verified

echo.
echo ========================================
echo Cleanup Complete!
echo ========================================
echo.
echo Summary:
echo - Removed all task attempts and generated files
echo - Cleared audio cache
echo - Preserved directory structure
echo.
echo Next steps:
echo 1. Check disk space freed up
echo 2. Restart service if needed
echo.

pause
