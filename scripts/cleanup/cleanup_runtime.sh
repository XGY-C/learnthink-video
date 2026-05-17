#!/bin/bash

# ============================================
# Runtime Directory Cleanup Tool (Linux/Mac)
# ============================================

echo ""
echo "========================================"
echo "Runtime Directory Cleanup Tool"
echo "========================================"
echo ""
echo "This script will clean the runtime/ directory:"
echo "  - Remove all task execution files"
echo "  - Clear audio cache"
echo "  - Keep directory structure (.gitkeep)"
echo ""
echo "WARNING: All generated videos and logs will be deleted!"
echo ""

read -p "Continue? Type YES: " confirm
if [ "$confirm" != "YES" ]; then
    echo "Cancelled"
    exit 0
fi

echo ""
echo "[Step 1] Cleaning runtime/tasks/..."

if [ -d "runtime/tasks" ]; then
    # Clean attempts directories
    for task_dir in runtime/tasks/*/; do
        if [ -d "${task_dir}attempts" ]; then
            task_name=$(basename "$task_dir")
            echo "  Removing attempts in $task_name"
            rm -rf "${task_dir}attempts" 2>/dev/null
        fi
        
        # Clean log files
        if ls "${task_dir}"*.log 1> /dev/null 2>&1; then
            echo "  Removing logs in $task_name"
            rm -f "${task_dir}"*.log 2>/dev/null
        fi
        
        # Clean video files
        if ls "${task_dir}"*.mp4 1> /dev/null 2>&1; then
            echo "  Removing videos in $task_name"
            rm -f "${task_dir}"*.mp4 2>/dev/null
        fi
        
        # Clean image files
        if ls "${task_dir}"*.png 1> /dev/null 2>&1; then
            echo "  Removing images in $task_name"
            rm -f "${task_dir}"*.png 2>/dev/null
        fi
    done
    echo "[OK] Task files cleaned"
else
    echo "[SKIP] runtime/tasks/ does not exist"
fi

echo ""
echo "[Step 2] Cleaning runtime/audio_cache/..."

if [ -d "runtime/audio_cache" ]; then
    for cache_dir in runtime/audio_cache/*/; do
        cache_name=$(basename "$cache_dir")
        echo "  Removing cache: $cache_name"
        rm -rf "$cache_dir" 2>/dev/null
    done
    echo "[OK] Audio cache cleaned"
else
    echo "[SKIP] runtime/audio_cache/ does not exist"
fi

echo ""
echo "[Step 3] Verifying directory structure..."

if [ ! -f "runtime/tasks/.gitkeep" ] && [ -d "runtime/tasks" ]; then
    touch "runtime/tasks/.gitkeep"
    echo "  Created runtime/tasks/.gitkeep"
fi

if [ ! -f "runtime/audio_cache/.gitkeep" ] && [ -d "runtime/audio_cache" ]; then
    touch "runtime/audio_cache/.gitkeep"
    echo "  Created runtime/audio_cache/.gitkeep"
fi

echo "[OK] Directory structure verified"

echo ""
echo "========================================"
echo "Cleanup Complete!"
echo "========================================"
echo ""
echo "Summary:"
echo "- Removed all task attempts and generated files"
echo "- Cleared audio cache"
echo "- Preserved directory structure"
echo ""
echo "Next steps:"
echo "1. Check disk space freed up: df -h"
echo "2. Restart service if needed"
echo ""
