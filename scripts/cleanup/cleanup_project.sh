#!/bin/bash

# ============================================
# 项目文件清理脚本 (Linux/Mac)
# ============================================

echo ""
echo "========================================"
echo "  项目文件清理工具"
echo "========================================"
echo ""

echo "此脚本将清理以下文件："
echo "  1. Python 缓存文件 (__pycache__, *.pyc)"
echo "  2. 测试缓存 (.pytest_cache)"
echo "  3. 日志文件 (*.log)"
echo "  4. 临时文件 (-ContentType, -InFile, -Method, -Uri)"
echo "  5. 运行时数据（可选）"
echo ""

read -p "是否继续？(y/n): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "[1/5] 清理 Python 缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
echo "[OK] Python 缓存已清理"

echo ""
echo "[2/5] 清理测试缓存..."
rm -rf .pytest_cache
echo "[OK] 测试缓存已清理"

echo ""
echo "[3/5] 清理日志文件..."
find . -type f -name "*.log" -delete 2>/dev/null
rm -f err.log out.log 2>/dev/null
echo "[OK] 日志文件已清理"

echo ""
echo "[4/5] 清理临时文件..."
rm -f -- -ContentType -InFile -Method -Uri 2>/dev/null
echo "[OK] 临时文件已清理"

echo ""
read -p "是否清理运行时数据？(y/n，谨慎操作): " clean_runtime
if [ "$clean_runtime" = "y" ] || [ "$clean_runtime" = "Y" ]; then
    echo "[5/5] 清理运行时数据..."
    
    # 清理任务尝试记录，保留目录结构
    if [ -d "runtime/tasks" ]; then
        find runtime/tasks -type d -name "attempts" -exec rm -rf {} + 2>/dev/null
    fi
    
    # 清理音频缓存
    if [ -d "runtime/audio_cache" ]; then
        find runtime/audio_cache -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} + 2>/dev/null
    fi
    
    echo "[OK] 运行时数据已清理"
else
    echo "[SKIP] 跳过运行时数据清理"
fi

echo ""
echo "========================================"
echo "  清理完成！"
echo "========================================"
echo ""
echo "注意："
echo "  - runtime/tasks 目录结构已保留"
echo "  - .gitkeep 文件未被删除"
echo "  - 建议定期运行此脚本保持项目整洁"
echo ""
