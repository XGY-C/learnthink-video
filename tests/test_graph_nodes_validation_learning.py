import json
from pathlib import Path

from app.graph.nodes import GraphNodes


class _StubValidator:
    def __init__(self, result: dict) -> None:
        self.result = result
        self.calls: list[dict] = []

    def run(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _StubNoticeRepo:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def append_validated_notice(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _StubTaskRepo:
    def __init__(self, root: Path) -> None:
        self.root = root

    def prepare_attempt(self, task_id: str, attempt_no: int) -> Path:
        target = self.root / task_id / "attempts" / f"{attempt_no:02d}"
        target.mkdir(parents=True, exist_ok=True)
        return target


class _StubNoticeSummarizer:
    def __init__(self, result: dict | None = None) -> None:
        self.result = result or {
            "essence": "MathTex is not suitable for full natural language",
            "root_cause": "runtime latex failure",
            "never_do": ["Do not place long natural language in MathTex"],
            "guardrails": ["Use Text for natural language labels"],
            "trigger_signals": ["latex error converting to dvi"],
            "preferred_pattern": "Use Text for plain language labels when MathTex fails",
            "confidence": 0.8,
            "source": "heuristic",
        }
        self.calls: list[dict] = []

    def summarize(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _make_nodes(tmp_path: Path, validator_result: dict) -> GraphNodes:
    nodes = GraphNodes.__new__(GraphNodes)
    nodes.validator = _StubValidator(validator_result)
    nodes.notice_repo = _StubNoticeRepo()
    nodes.notice_summarizer = _StubNoticeSummarizer()
    nodes.task_repo = _StubTaskRepo(tmp_path)
    return nodes


def test_validate_previous_fix_learns_on_success_path(tmp_path: Path) -> None:
    nodes = _make_nodes(
        tmp_path,
        {
            "shouldLearn": True,
            "candidateNotice": "Use NumberLine.numbers",
            "unresolvedIssueIds": [],
        },
    )
    state = {
        "task_id": "task-1",
        "attempt_no": 2,
        "last_render_report": {"success": True},
        "previous_issues": [
            {
                "issueId": "ISSUE_007_x",
                "rootCauseLabel": "api_deprecation",
            }
        ],
        "current_issues": [
            {
                "issueId": "ISSUE_007_x",
                "rootCauseLabel": "api_deprecation",
            }
        ],
    }

    result = nodes.validate_previous_fix(state)

    assert result["current_issues"] == []
    assert result["last_validation"]["shouldLearn"] is True
    assert len(nodes.validator.calls) == 1
    assert nodes.validator.calls[0]["new_issues"] == []

    assert len(nodes.notice_repo.calls) == 1
    assert nodes.notice_repo.calls[0]["issue_type"] == "api_deprecation"

    validation_file = tmp_path / "task-1" / "attempts" / "02" / "validation.json"
    assert validation_file.exists()
    payload = json.loads(validation_file.read_text(encoding="utf-8"))
    assert payload["candidateNotice"] == "Use NumberLine.numbers"


def test_validate_previous_fix_clears_stale_issues_without_previous_issue(tmp_path: Path) -> None:
    nodes = _make_nodes(tmp_path, {"shouldLearn": False, "candidateNotice": None})
    state = {
        "task_id": "task-2",
        "attempt_no": 1,
        "last_render_report": {"success": True},
        "previous_issues": [],
        "current_issues": [{"issueId": "OLD_001"}],
    }

    result = nodes.validate_previous_fix(state)

    assert result == {"last_validation": None, "current_issues": []}
    assert nodes.validator.calls == []
    assert nodes.notice_repo.calls == []


def test_validate_previous_fix_builds_notice_when_candidate_missing(tmp_path: Path) -> None:
    nodes = _make_nodes(
        tmp_path,
        {
            "shouldLearn": True,
            "candidateNotice": None,
            "unresolvedIssueIds": [],
        },
    )
    nodes.notice_summarizer = _StubNoticeSummarizer(
        {
            "essence": "Math and natural language rendering pipelines are different",
            "root_cause": "latex failed",
            "never_do": ["Do not force plain language into MathTex"],
            "guardrails": ["Route natural language to Text"],
            "trigger_signals": ["latex error converting to dvi"],
            "preferred_pattern": "1. `Use Text for natural language labels`",
            "confidence": 0.91,
            "source": "llm",
        }
    )

    state = {
        "task_id": "task-3",
        "attempt_no": 3,
        "last_render_report": {"success": True},
        "previous_issues": [
            {
                "issueId": "ISSUE_007_x",
                "rootCauseLabel": "value_error",
                "normalizedMessage": "latex error converting to dvi",
            }
        ],
        "current_issues": [],
    }

    result = nodes.validate_previous_fix(state)

    assert len(nodes.notice_summarizer.calls) == 1
    assert len(nodes.notice_repo.calls) == 1
    assert nodes.notice_repo.calls[0]["rule"] == "Use Text for natural language labels"
    assert nodes.notice_repo.calls[0]["root_cause"] == "latex failed"
    assert result["last_validation"]["candidateNotice"] == "Use Text for natural language labels"


