from app.agents.repair import RepairAgent
from app.llm.base import BaseLLMClient


class _StubLLMClient(BaseLLMClient):
    def __init__(self, response: str) -> None:
        self.response = response

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self.response


def test_repair_agent_strips_mathtex_text_segments_for_latex_value_error() -> None:
    code = 'label = MathTex("(-\\\\infty, 0]", "\\\\text{下降}", color=RED)\n'
    issues = [
        {
            "issueId": "ISSUE_001",
            "rootCauseLabel": "value_error",
            "normalizedMessage": "latex error converting to dvi. see log",
        }
    ]

    result = RepairAgent().run(code, issues, attempt_no=1)

    assert "\\\\text{下降}" not in result["code"]
    assert result["metadata"]["changed"] is True
    assert result["metadata"]["progressHint"] == "progress"
    assert result["metadata"]["escalate"] is False
    assert result["llmTrace"]["escalated"] is False
    assert result["llmTrace"]["reason"] == "not_escalated"


def test_repair_agent_sets_escalate_when_no_latex_pattern_found() -> None:
    code = 'label = MathTex("x^2")\n'
    issues = [
        {
            "issueId": "ISSUE_002",
            "rootCauseLabel": "value_error",
            "normalizedMessage": "latex error converting to dvi",
        }
    ]

    result = RepairAgent().run(code, issues, attempt_no=2)

    assert result["code"] == code
    assert result["metadata"]["changed"] is False
    assert result["metadata"]["progressHint"] == "no_change"
    assert result["metadata"]["escalate"] is True
    assert result["metadata"]["fallbackAttempted"] is True
    assert result["metadata"]["fallbackUsed"] is False
    assert result["metadata"]["fallbackReason"] == "llm_fallback_disabled"
    assert result["llmTrace"]["escalated"] is True
    assert result["llmTrace"]["reason"] == "llm_fallback_disabled"


def test_repair_agent_uses_llm_fallback_when_escalated() -> None:
    code = 'label = MathTex("x^2")\n'
    issues = [
        {
            "issueId": "ISSUE_003",
            "rootCauseLabel": "value_error",
            "normalizedMessage": "latex error converting to dvi",
        }
    ]
    llm = _StubLLMClient("""```python\nfrom manim import *\n\nclass GeneratedVideoScene(Scene):\n    def construct(self):\n        self.add(Text('ok'))\n```""")

    result = RepairAgent(llm_client=llm, enable_llm_fallback=True).run(code, issues, attempt_no=3)

    assert result["metadata"]["fallbackAttempted"] is True
    assert result["metadata"]["fallbackUsed"] is True
    assert result["metadata"]["fallbackReason"] is None
    assert result["llmTrace"]["llmAttempted"] is True
    assert result["llmTrace"]["llmUsed"] is True
    assert result["llmTrace"]["reason"] is None
    assert "class GeneratedVideoScene" in result["code"]


def test_repair_agent_marks_llm_fallback_invalid_structure() -> None:
    code = 'label = MathTex("x^2")\n'
    issues = [
        {
            "issueId": "ISSUE_004",
            "rootCauseLabel": "value_error",
            "normalizedMessage": "latex error converting to dvi",
        }
    ]
    llm = _StubLLMClient("not python code")

    result = RepairAgent(llm_client=llm, enable_llm_fallback=True).run(code, issues, attempt_no=4)

    assert result["metadata"]["fallbackAttempted"] is True
    assert result["metadata"]["fallbackUsed"] is False
    assert result["metadata"]["fallbackReason"] == "llm_response_missing_structure"
    assert result["llmTrace"]["llmAttempted"] is True
    assert result["llmTrace"]["llmUsed"] is False

