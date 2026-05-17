@echo off
chcp 65001 >nul

echo.
echo ========================================
echo Project File Reorganization Tool
echo ========================================
echo.
echo This script will:
echo   1. Delete useless temporary files
echo   2. Remove redundant documents
echo   3. Move documents to docs/ directory
echo.
echo WARNING: Files will be deleted!
echo.

set /p confirm="Continue? Type YES: "
if not "%confirm%"=="YES" (
    echo Cancelled
    pause
    exit /b 0
)

echo.
echo [Step 1] Deleting useless files...

del /F /Q "-ContentType" 2>nul
del /F /Q "-InFile" 2>nul
del /F /Q "-Method" 2>nul
del /F /Q "-Uri" 2>nul
del /F /Q "TODO.txt" 2>nul
del /F /Q "err.log" 2>nul
del /F /Q "log" 2>nul
del /F /Q "随便一个AI写的.txt" 2>nul

echo [OK] Useless files deleted

echo.
echo [Step 2] Removing redundant documents...

del /F /Q "DEEPSEEK_MODEL_UPDATE.md" 2>nul
del /F /Q "DEEPSEEK_IMPLEMENTATION_SUMMARY.md" 2>nul
del /F /Q "GITIGNORE_QUICK_REF.md" 2>nul

echo [OK] Redundant documents removed

echo.
echo [Step 3] Creating docs/ and moving files...

if not exist "docs" mkdir docs

move /Y "DEEPSEEK_THINKING_GUIDE.md" "docs\" 2>nul
move /Y "QUICK_REFERENCE_DEEPSEEK.md" "docs\" 2>nul
move /Y "PROJECT_DOCUMENTATION.md" "docs\" 2>nul
move /Y "PROJECT_FILE_STRUCTURE.md" "docs\" 2>nul
move /Y "PROJECT_CLEANUP_SUMMARY.md" "docs\" 2>nul
move /Y "QUICK_REFERENCE.md" "docs\" 2>nul
move /Y "JAVA_BACKEND_INTEGRATION_DOC.md" "docs\" 2>nul
move /Y "MANIM_DOC_SEARCH_TOOL.md" "docs\" 2>nul
move /Y "IMPLEMENTATION_SUMMARY.md" "docs\" 2>nul
move /Y "OPEN_SOURCE_COMPONENTS_COMPETITION.md" "docs\" 2>nul
move /Y "manim_video_api_interface_doc.md" "docs\" 2>nul

echo [OK] Documents moved to docs/

echo.
echo ========================================
echo Reorganization Complete!
echo ========================================
echo.
echo Summary:
echo - Deleted 8 useless files
echo - Removed 3 redundant documents  
echo - Moved 11 documents to docs/
echo.
echo Next steps:
echo 1. Check docs/ directory
echo 2. Update links in README.md
echo 3. Commit to Git
echo.

pause
