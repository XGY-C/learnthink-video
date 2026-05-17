#!/bin/bash

# ============================================
# DeepSeek 配置快速设置脚本 (Linux/Mac)
# ============================================

echo ""
echo "========================================"
echo "  DeepSeek 思考模式配置向导"
echo "========================================"
echo ""

# 检查 .env 文件是否存在
if [ ! -f .env ]; then
    echo "[INFO] 未找到 .env 文件，从 .env.example 创建..."
    cp .env.example .env
    echo "[OK] 已创建 .env 文件"
    echo ""
fi

echo "请选择要使用的配置模板："
echo ""
echo "1. DeepSeek V4 Pro + 思考模式 max（推荐 - 最强性能）"
echo "2. DeepSeek V4 Pro + 思考模式 high（标准配置）"
echo "3. DeepSeek V4 Flash + 思考模式 high（性价比）"
echo "4. DeepSeek V4 Flash（无思考模式，最快）"
echo "5. OpenAI GPT-4 Turbo"
echo "6. 保持当前配置不变"
echo ""

read -p "请输入选项 (1-6): " choice

case $choice in
    1)
        echo ""
        echo "[INFO] 配置: DeepSeek V4 Pro + 思考模式 max"
        echo ""
        read -p "请输入你的 DeepSeek API Key: " API_KEY
        
        if [ -z "$API_KEY" ]; then
            echo "[ERROR] API Key 不能为空"
            exit 1
        fi
        
        sed -i.bak "s/^ENABLE_LLM_ASSIST=.*/ENABLE_LLM_ASSIST=true/" .env
        sed -i.bak "s/^LLM_PROVIDER=.*/LLM_PROVIDER=deepseek/" .env
        sed -i.bak "s|^LLM_BASE_URL=.*|LLM_BASE_URL=https://api.deepseek.com/v1|" .env
        sed -i.bak "s/^LLM_API_KEY=.*/LLM_API_KEY=$API_KEY/" .env
        sed -i.bak "s/^LLM_MODEL=.*/LLM_MODEL=deepseek-v4-pro/" .env
        sed -i.bak "s/^DEEPSEEK_ENABLE_THINKING=.*/DEEPSEEK_ENABLE_THINKING=true/" .env
        sed -i.bak "s/^DEEPSEEK_REASONING_EFFORT=.*/DEEPSEEK_REASONING_EFFORT=max/" .env
        
        # 删除备份文件
        rm -f .env.bak
        
        echo "[OK] 配置已更新"
        ;;
        
    2)
        echo ""
        echo "[INFO] 配置: DeepSeek V4 Pro + 思考模式 high"
        echo ""
        read -p "请输入你的 DeepSeek API Key: " API_KEY
        
        if [ -z "$API_KEY" ]; then
            echo "[ERROR] API Key 不能为空"
            exit 1
        fi
        
        sed -i.bak "s/^ENABLE_LLM_ASSIST=.*/ENABLE_LLM_ASSIST=true/" .env
        sed -i.bak "s/^LLM_PROVIDER=.*/LLM_PROVIDER=deepseek/" .env
        sed -i.bak "s|^LLM_BASE_URL=.*|LLM_BASE_URL=https://api.deepseek.com/v1|" .env
        sed -i.bak "s/^LLM_API_KEY=.*/LLM_API_KEY=$API_KEY/" .env
        sed -i.bak "s/^LLM_MODEL=.*/LLM_MODEL=deepseek-v4-pro/" .env
        sed -i.bak "s/^DEEPSEEK_ENABLE_THINKING=.*/DEEPSEEK_ENABLE_THINKING=true/" .env
        sed -i.bak "s/^DEEPSEEK_REASONING_EFFORT=.*/DEEPSEEK_REASONING_EFFORT=high/" .env
        
        rm -f .env.bak
        
        echo "[OK] 配置已更新"
        ;;
        
    3)
        echo ""
        echo "[INFO] 配置: DeepSeek V4 Flash + 思考模式 high"
        echo ""
        read -p "请输入你的 DeepSeek API Key: " API_KEY
        
        if [ -z "$API_KEY" ]; then
            echo "[ERROR] API Key 不能为空"
            exit 1
        fi
        
        sed -i.bak "s/^ENABLE_LLM_ASSIST=.*/ENABLE_LLM_ASSIST=true/" .env
        sed -i.bak "s/^LLM_PROVIDER=.*/LLM_PROVIDER=deepseek/" .env
        sed -i.bak "s|^LLM_BASE_URL=.*|LLM_BASE_URL=https://api.deepseek.com/v1|" .env
        sed -i.bak "s/^LLM_API_KEY=.*/LLM_API_KEY=$API_KEY/" .env
        sed -i.bak "s/^LLM_MODEL=.*/LLM_MODEL=deepseek-v4-flash/" .env
        sed -i.bak "s/^DEEPSEEK_ENABLE_THINKING=.*/DEEPSEEK_ENABLE_THINKING=true/" .env
        sed -i.bak "s/^DEEPSEEK_REASONING_EFFORT=.*/DEEPSEEK_REASONING_EFFORT=high/" .env
        
        rm -f .env.bak
        
        echo "[OK] 配置已更新"
        ;;
        
    4)
        echo ""
        echo "[INFO] 配置: DeepSeek V4 Flash（无思考模式）"
        echo ""
        read -p "请输入你的 DeepSeek API Key: " API_KEY
        
        if [ -z "$API_KEY" ]; then
            echo "[ERROR] API Key 不能为空"
            exit 1
        fi
        
        sed -i.bak "s/^ENABLE_LLM_ASSIST=.*/ENABLE_LLM_ASSIST=true/" .env
        sed -i.bak "s/^LLM_PROVIDER=.*/LLM_PROVIDER=deepseek/" .env
        sed -i.bak "s|^LLM_BASE_URL=.*|LLM_BASE_URL=https://api.deepseek.com/v1|" .env
        sed -i.bak "s/^LLM_API_KEY=.*/LLM_API_KEY=$API_KEY/" .env
        sed -i.bak "s/^LLM_MODEL=.*/LLM_MODEL=deepseek-v4-flash/" .env
        sed -i.bak "s/^DEEPSEEK_ENABLE_THINKING=.*/DEEPSEEK_ENABLE_THINKING=false/" .env
        
        rm -f .env.bak
        
        echo "[OK] 配置已更新"
        ;;
        
    5)
        echo ""
        echo "[INFO] 配置: OpenAI GPT-4 Turbo"
        echo ""
        read -p "请输入你的 OpenAI API Key: " API_KEY
        
        if [ -z "$API_KEY" ]; then
            echo "[ERROR] API Key 不能为空"
            exit 1
        fi
        
        sed -i.bak "s/^ENABLE_LLM_ASSIST=.*/ENABLE_LLM_ASSIST=true/" .env
        sed -i.bak "s/^LLM_PROVIDER=.*/LLM_PROVIDER=openai/" .env
        sed -i.bak "s|^LLM_BASE_URL=.*|LLM_BASE_URL=https://api.openai.com/v1|" .env
        sed -i.bak "s/^LLM_API_KEY=.*/LLM_API_KEY=$API_KEY/" .env
        sed -i.bak "s/^LLM_MODEL=.*/LLM_MODEL=gpt-4-turbo/" .env
        
        rm -f .env.bak
        
        echo "[OK] 配置已更新"
        ;;
        
    6)
        echo ""
        echo "[INFO] 保持当前配置不变"
        ;;
        
    *)
        echo ""
        echo "[ERROR] 无效的选项"
        exit 1
        ;;
esac

# 询问是否运行测试
echo ""
read -p "是否运行配置测试？(y/n): " run_test

if [ "$run_test" = "y" ] || [ "$run_test" = "Y" ]; then
    echo ""
    echo "[INFO] 运行配置测试..."
    python test_deepseek_thinking.py
fi

# 显示配置摘要
echo ""
echo "========================================"
echo "  配置完成！"
echo "========================================"
echo ""
echo "当前配置摘要："
grep -E "^(ENABLE_LLM_ASSIST|LLM_PROVIDER|LLM_MODEL|DEEPSEEK_ENABLE_THINKING)" .env
echo ""
echo "下一步："
echo "  1. 启动服务: python -m app.main"
echo "  2. 或开发模式: uvicorn app.main:app --reload"
echo "  3. 查看详细文档: DEEPSEEK_THINKING_GUIDE.md"
echo ""
