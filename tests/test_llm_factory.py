from app.core.config import Settings
from app.llm.factory import build_llm_client
from app.llm.mock import MockLLMClient
from app.llm.openai_compatible import OpenAICompatibleLLMClient


def test_factory_accepts_openai_alias():
    settings = Settings(
        ENABLE_LLM_ASSIST=True,
        LLM_PROVIDER="openai",
        LLM_BASE_URL="https://api.deepseek.com/v1",
        LLM_API_KEY="test-key",
        LLM_MODEL="deepseek-reasoner",
    )
    client = build_llm_client(settings)
    assert isinstance(client, OpenAICompatibleLLMClient)


def test_factory_uses_mock_when_disabled():
    settings = Settings(ENABLE_LLM_ASSIST=False)
    client = build_llm_client(settings)
    assert isinstance(client, MockLLMClient)

