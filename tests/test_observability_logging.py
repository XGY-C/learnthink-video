import logging
from pathlib import Path

from app.llm.openai_compatible import OpenAICompatibleLLMClient
from app.tools.audio_asset_resolver import AudioAssetResolver


class _FakeResponse:
    status_code = 200

    @staticmethod
    def raise_for_status() -> None:
        return None

    @staticmethod
    def json() -> dict:
        return {"choices": [{"message": {"content": "ok"}}]}


def test_openai_compatible_logs_without_secret(monkeypatch, caplog):
    calls: dict = {}

    def _fake_post(url: str, headers: dict, json: dict, timeout: float):
        calls["url"] = url
        calls["headers"] = headers
        calls["json"] = json
        calls["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr("app.llm.openai_compatible.httpx.post", _fake_post)
    client = OpenAICompatibleLLMClient(
        base_url="https://api.deepseek.com/v1",
        api_key="secret-key-123",
        model="deepseek-reasoner",
    )

    with caplog.at_level(logging.INFO):
        result = client.complete(system_prompt="sys", user_prompt="user")

    assert result == "ok"
    assert calls["url"].endswith("/chat/completions")

    joined = "\n".join(record.getMessage() for record in caplog.records)
    assert "[llm]" in joined
    assert "status=start" in joined
    assert "status=ok" in joined
    assert "secret-key-123" not in joined
    assert "system_prompt" not in joined
    assert "user_prompt" not in joined


def test_audio_local_fetch_logs_ready(tmp_path: Path, caplog):
    src = tmp_path / "voice.wav"
    src.write_bytes(b"123456")

    resolver = AudioAssetResolver(cache_root=tmp_path / "cache", ffprobe_bin="ffprobe")

    with caplog.at_level(logging.INFO):
        target, err = resolver._fetch_audio(task_id="task-1", audio_url=str(src))

    assert err is None
    assert target.exists()
    assert target.read_bytes() == b"123456"

    joined = "\n".join(record.getMessage() for record in caplog.records)
    assert "[audio]" in joined
    assert "status=ready" in joined
    assert "task=task-1" in joined

