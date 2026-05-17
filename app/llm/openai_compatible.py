from __future__ import annotations

import logging
import time
from urllib.parse import urlparse

import httpx
from app.llm.base import BaseLLMClient


logger = logging.getLogger(__name__)


class OpenAICompatibleLLMClient(BaseLLMClient):
    def __init__(
        self, 
        base_url: str, 
        api_key: str, 
        model: str,
        enable_thinking: bool = False,
        reasoning_effort: str = "high",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.enable_thinking = enable_thinking
        self.reasoning_effort = reasoning_effort

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        host = urlparse(self.base_url).netloc or "unknown"
        start = time.perf_counter()
        logger.info(
            "[llm] provider=openai_compatible status=start model=%s host=%s thinking=%s effort=%s",
            self.model,
            host,
            self.enable_thinking,
            self.reasoning_effort if self.enable_thinking else "N/A",
        )
        
        # 构建请求体
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        
        # 如果启用思考模式，添加 DeepSeek 特定参数
        if self.enable_thinking:
            request_body["reasoning_effort"] = self.reasoning_effort
            request_body["extra_body"] = {
                "thinking": {
                    "type": "enabled"
                }
            }
        
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            
            # 提取 reasoning_content（如果存在）
            reasoning_content = data["choices"][0]["message"].get("reasoning_content", "")
            if reasoning_content and self.enable_thinking:
                logger.info(
                    "[llm] reasoning_content_length=%d model=%s",
                    len(reasoning_content),
                    self.model,
                )
        except Exception:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.exception(
                "[llm] provider=openai_compatible status=failed model=%s host=%s elapsedMs=%s",
                self.model,
                host,
                elapsed_ms,
            )
            raise

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "[llm] provider=openai_compatible status=ok model=%s host=%s statusCode=%s elapsedMs=%s responseChars=%s",
            self.model,
            host,
            resp.status_code,
            elapsed_ms,
            len(content),
        )
        return content
