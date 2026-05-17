from __future__ import annotations

from app.core.config import Settings
from app.llm.base import BaseLLMClient
from app.llm.mock import MockLLMClient
from app.llm.openai_compatible import OpenAICompatibleLLMClient


def build_llm_client(settings: Settings, agent_name: str = "default") -> BaseLLMClient:
    provider = (settings.llm_provider or "").strip().lower()
    if not settings.enable_llm_assist or provider not in {"openai_compatible", "openai", "deepseek"}:
        return MockLLMClient()

    # 根据智能体名称获取特定的模型配置
    model = None
    enable_thinking = False
    reasoning_effort = settings.deepseek_reasoning_effort

    if agent_name == "planner":
        model = settings.planner_model or settings.llm_model
        enable_thinking = settings.planner_enable_thinking
    elif agent_name == "code_expert":
        model = settings.code_expert_model or settings.llm_model
        enable_thinking = settings.code_expert_enable_thinking
    elif agent_name == "diagnoser":
        model = settings.diagnoser_model or settings.llm_model
    elif agent_name == "repair":
        model = settings.repair_model or settings.llm_model
        enable_thinking = settings.repair_enable_thinking
    elif agent_name == "summarizer":
        model = settings.summarizer_model or settings.llm_model
    elif agent_name == "redlines":
        model = settings.redlines_model or settings.llm_model
    else:
        model = settings.llm_model
        enable_thinking = settings.deepseek_enable_thinking

    if not (settings.llm_base_url and settings.llm_api_key and model):
        raise ValueError(f"LLM provider is enabled but base_url/api_key/model is incomplete for agent: {agent_name}")

    # 对于 DeepSeek 提供商，传递思考模式配置
    if provider == "deepseek":
        return OpenAICompatibleLLMClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=model,
            enable_thinking=enable_thinking,
            reasoning_effort=reasoning_effort,
        )
    else:
        return OpenAICompatibleLLMClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=model,
        )
