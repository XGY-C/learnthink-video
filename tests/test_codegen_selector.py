from app.agents.codegen_selector import CodegenSelector
from app.agents.validator import FixValidator


def test_selector_prefers_candidate_without_quality_issues():
    selector = CodegenSelector(FixValidator())

    weak = selector.evaluate_candidate("weak", "obj = make_shape('x^2 + 1 = 0')")
    strong = selector.evaluate_candidate("strong", "expr = MathTex(r'x^2 + 1 = 0')")

    selected = selector.select_best([weak, strong])
    assert selected["strategy"] == "strong"
    assert selected["issueCount"] == 0
    assert selected["critique"] == "No quality-gate issues detected."
    assert "scoreBreakdown" in selected


def test_selector_tie_breaker_prefers_longer_code_when_scores_equal():
    selector = CodegenSelector(FixValidator())

    short = {"strategy": "a", "score": 99.0, "issueCount": 0, "codeLength": 10, "issues": [], "code": "a"}
    long = {"strategy": "b", "score": 99.0, "issueCount": 0, "codeLength": 20, "issues": [], "code": "b"}

    selected = selector.select_best([short, long])
    assert selected["strategy"] == "b"


def test_selector_selection_rationale_mentions_runner_up():
    selector = CodegenSelector(FixValidator())
    weak = selector.evaluate_candidate("weak", "obj = make_shape('x^2 + 1 = 0')")
    strong = selector.evaluate_candidate("strong", "expr = MathTex(r'x^2 + 1 = 0')")
    selected = selector.select_best([weak, strong])
    rationale = selector.selection_rationale(selected, [weak, strong])
    assert "Selected strong" in rationale
    assert "over weak" in rationale


