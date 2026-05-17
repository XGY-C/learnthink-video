from __future__ import annotations
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError
