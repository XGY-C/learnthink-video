from app.graph.nodes import _compute_code_change, _compose_failure_message


def test_compute_code_change_detects_no_change() -> None:
    content = "line1\nline2\n"
    change = _compute_code_change(content, content)
    assert change == {"changed": False, "charDelta": 0, "lineDelta": 0}


def test_compute_code_change_reports_deltas() -> None:
    before = "a\nb\n"
    after = "a\nb\nc\nextra"
    change = _compute_code_change(before, after)
    assert change["changed"] is True
    assert change["charDelta"] == len(after) - len(before)
    assert change["lineDelta"] == len(after.splitlines()) - len(before.splitlines())


def test_compose_failure_message_includes_loop_and_fallback_context() -> None:
    message = _compose_failure_message(
        {
            "error_message": "Repair loop detected with no effective code changes",
            "loop_guard_reason": "no_progress_streak=2; unresolved=ISSUE_007",
            "last_repair_metadata": {"fallbackReason": "llm_response_missing_structure"},
        }
    )

    assert "Repair loop detected" in message
    assert "loop_guard=no_progress_streak=2" in message
    assert "llm_fallback=llm_response_missing_structure" in message


def test_compose_failure_message_uses_default_when_no_context() -> None:
    assert _compose_failure_message({}) == "Render failed after max attempts"


