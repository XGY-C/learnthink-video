#!/bin/bash

# ============================================
# 项目文件整理脚本 - 最小化方案 (Linux/Mac)
# ============================================

echo ""
echo "========================================"
echo "  项目文件整理工具"
echo "========================================"
echo ""
echo "此脚本将执行以下操作："
echo "  1. 删除无用的临时文件（8个）"
echo "  2. 合并 DeepSeek 相关文档"
echo "  3. 创建 docs/ 目录并移动文档"
echo ""
echo "⚠️  警告：此操作会删除文件，请确保已备份！"
echo ""

read -p "是否继续？(输入 yes 确认): " confirm
if [ "$confirm" != "yes" ]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "[步骤 1/3] 删除无用文件..."
echo ""

deleted_count=0

for file in "-ContentType" "-InFile" "-Method" "-Uri" "TODO.txt" "err.log" "log" "随便一个AI写的.txt"; do
    if [ -e "$file" ]; then
        rm -f "$file"
        echo "  ✓ 删除 $file"
        ((deleted_count++))
    fi
done

echo ""
echo "共删除 $deleted_count 个文件"

echo ""
echo "[步骤 2/3] 整合 DeepSeek 文档..."
echo ""

echo "保留主文档: DEEPSEEK_THINKING_GUIDE.md"
echo "删除冗余文档:"

for file in "DEEPSEEK_MODEL_UPDATE.md" "DEEPSEEK_IMPLEMENTATION_SUMMARY.md" "GITIGNORE_QUICK_REF.md"; do
    if [ -e "$file" ]; then
        rm -f "$file"
        echo "  ✓ 删除 $file"
    fi
done

echo ""
echo "[步骤 3/3] 创建 docs/ 目录并移动文档..."
echo ""

mkdir -p docs

echo "移动文档到 docs/:"

docs=(
    "DEEPSEEK_THINKING_GUIDE.md"
    "QUICK_REFERENCE_DEEPSEEK.md"
    "PROJECT_DOCUMENTATION.md"
    "PROJECT_FILE_STRUCTURE.md"
    "PROJECT_CLEANUP_SUMMARY.md"
    "QUICK_REFERENCE.md"
    "JAVA_BACKEND_INTEGRATION_DOC.md"
    "MANIM_DOC_SEARCH_TOOL.md"
    "IMPLEMENTATION_SUMMARY.md"
    "OPEN_SOURCE_COMPONENTS_COMPETITION.md"
    "manim_video_api_interface_doc.md"
)

for file in "${docs[@]}"; do
    if [ -e "$file" ]; then
        mv "$file" docs/
        echo "  ✓ 移动 $file"
    fi
done

echo ""
echo "========================================"
echo "  整理完成！"
echo "========================================"
echo ""
echo "结果统计："
echo "  - 删除了 $deleted_count 个无用文件"
echo "  - 删除了 3 个冗余文档"
echo "  - 移动了 ${#docs[@]} 个文档到 docs/ 目录"
echo ""
echo "根目录现在的文件更清爽了！"
echo ""
echo "下一步："
echo "  1. 查看 docs/ 目录确认所有文档已移动"
echo "  2. 更新 README.md 中的文档链接"
echo "  3. 提交更改到 Git"
echo ""
