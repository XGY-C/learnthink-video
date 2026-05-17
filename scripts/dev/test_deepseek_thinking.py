"""
测试 DeepSeek 思考模式配置

用法:
    python test_deepseek_thinking.py
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings
from app.llm.factory import build_llm_client


def test_configuration():
    """测试配置是否正确加载"""
    print("=" * 60)
    print("DeepSeek 思考模式配置测试")
    print("=" * 60)
    
    settings = get_settings()
    
    print(f"\n📋 当前配置:")
    print(f"  ENABLE_LLM_ASSIST: {settings.enable_llm_assist}")
    print(f"  LLM_PROVIDER: {settings.llm_provider}")
    print(f"  LLM_BASE_URL: {settings.llm_base_url or '未设置'}")
    print(f"  LLM_MODEL: {settings.llm_model or '未设置'}")
    print(f"  DEEPSEEK_ENABLE_THINKING: {settings.deepseek_enable_thinking}")
    print(f"  DEEPSEEK_REASONING_EFFORT: {settings.deepseek_reasoning_effort}")
    
    # 检查 DeepSeek 配置
    if settings.llm_provider.lower() == "deepseek":
        print(f"\n✅ 检测到 DeepSeek 提供商")
        
        if not settings.llm_base_url:
            print(f"❌ 错误: LLM_BASE_URL 未设置")
            return False
        
        if not settings.llm_api_key:
            print(f"❌ 错误: LLM_API_KEY 未设置")
            return False
        
        if not settings.llm_model:
            print(f"❌ 错误: LLM_MODEL 未设置")
            return False
        
        if settings.deepseek_enable_thinking:
            print(f"✅ 思考模式已启用 (effort={settings.deepseek_reasoning_effort})")
        else:
            print(f"⚠️  思考模式已禁用")
        
        return True
    else:
        print(f"\n⚠️  当前提供商不是 DeepSeek: {settings.llm_provider}")
        return False


def test_llm_client():
    """测试 LLM 客户端创建"""
    print("\n" + "=" * 60)
    print("LLM 客户端测试")
    print("=" * 60)
    
    try:
        settings = get_settings()
        
        if not settings.enable_llm_assist:
            print(f"⚠️  LLM 辅助功能未启用 (ENABLE_LLM_ASSIST=false)")
            print(f"   将使用 Mock 客户端")
            client = build_llm_client(settings)
            print(f"✅ Mock 客户端创建成功: {type(client).__name__}")
            return True
        
        client = build_llm_client(settings)
        print(f"✅ LLM 客户端创建成功: {type(client).__name__}")
        
        # 检查是否是 OpenAICompatibleLLMClient
        from app.llm.openai_compatible import OpenAICompatibleLLMClient
        if isinstance(client, OpenAICompatibleLLMClient):
            print(f"  - Base URL: {client.base_url}")
            print(f"  - Model: {client.model}")
            print(f"  - Enable Thinking: {client.enable_thinking}")
            print(f"  - Reasoning Effort: {client.reasoning_effort}")
            
            if settings.llm_provider.lower() == "deepseek" and client.enable_thinking:
                print(f"✅ DeepSeek 思考模式已正确配置")
            else:
                print(f"ℹ️  当前配置不使用 DeepSeek 思考模式")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM 客户端创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_completion():
    """测试简单的完成请求（可选，需要有效的 API Key）"""
    print("\n" + "=" * 60)
    print("简单完成测试（可选）")
    print("=" * 60)
    
    settings = get_settings()
    
    if not settings.enable_llm_assist:
        print(f"⚠️  跳过测试：LLM 辅助功能未启用")
        return True
    
    if settings.llm_provider.lower() != "deepseek":
        print(f"⚠️  跳过测试：当前提供商不是 DeepSeek")
        return True
    
    response = input("\n是否执行真实的 API 调用测试？(y/n): ")
    if response.lower() != 'y':
        print("跳过 API 调用测试")
        return True
    
    try:
        client = build_llm_client(settings)
        
        print(f"\n🔄 发送测试请求...")
        print(f"   Model: {settings.llm_model}")
        print(f"   Thinking: {settings.deepseek_enable_thinking}")
        
        result = client.complete(
            system_prompt="你是一个助手。请简洁回答。",
            user_prompt="9.11 和 9.8 哪个大？请解释原因。"
        )
        
        print(f"\n✅ 收到响应:")
        print(f"   长度: {len(result)} 字符")
        print(f"   内容预览: {result[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试流程"""
    print("\n" + "🚀" * 30)
    print("开始 DeepSeek 思考模式配置测试\n")
    
    results = []
    
    # 测试 1: 配置加载
    results.append(("配置加载", test_configuration()))
    
    # 测试 2: 客户端创建
    results.append(("客户端创建", test_llm_client()))
    
    # 测试 3: 简单完成（可选）
    results.append(("API 调用", test_simple_completion()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name:20s} {status}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请检查配置")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
