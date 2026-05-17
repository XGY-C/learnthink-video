from __future__ import annotations
from app.llm.base import BaseLLMClient


class MockLLMClient(BaseLLMClient):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return "MOCK_RESPONSE"
