from app.agents.notice_summarizer import NoticeSummarizer
from app.llm.mock import MockLLMClient


class _StaticLLM:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self.payload


def test_notice_summarizer_uses_fallback_when_disabled() -> None:
    summarizer = NoticeSummarizer(llm_client=MockLLMClient(), enabled=False)
    result = summarizer.summarize(
        previous_issues=[{"rootCauseLabel": "value_error", "normalizedMessage": "latex error"}],
        new_issues=[],
        base_rule="Use Tex for plain text",
    )
    assert result["source"] == "heuristic"
    assert "latex error" in result["root_cause"]
    assert result["preferred_pattern"] == "Use Tex for plain text"


def test_notice_summarizer_parses_llm_json() -> None:
    summarizer = NoticeSummarizer(
        llm_client=_StaticLLM(
            '{"essence":"MathTex is not a generic text container","root_cause":"Natural language exceeded math parser scope",'
            '"never_do":["Do not place full Chinese sentences in MathTex"],'
            '"guardrails":["Split math and natural language layers"],'
            '"trigger_signals":["latex error converting to dvi"],'
            '"preferred_pattern":"Use Text for Chinese sentences","confidence":0.91}'
        ),
        enabled=True,
    )
    result = summarizer.summarize(previous_issues=[], new_issues=[], base_rule="base")
    assert result["source"] == "llm"
    assert result["confidence"] == 0.91
    assert result["preferred_pattern"].startswith("Use Text")


def test_notice_rule_cleaning_removes_markdown_noise() -> None:
    cleaned = NoticeSummarizer.clean_rule("1. `Use Text for labels`")
    assert cleaned == "Use Text for labels"


