from app.agents.notice_redlines import build_notice_redlines


def test_build_notice_redlines_keeps_all_validated_notices_without_limit() -> None:
    notices = [
        {
            "issue_type": f"issue_{idx:02d}",
            "never_do": [f"forbid_{idx:02d}"],
            "preferred_pattern": f"prefer_{idx:02d}",
            "status": "validated",
        }
        for idx in range(1, 13)
    ]

    redlines = build_notice_redlines(notices)

    assert "[issue_01]" in redlines
    assert "[issue_12]" in redlines
    assert "forbid_12" in redlines
    assert "prefer_12" in redlines


def test_build_notice_redlines_preserves_input_order() -> None:
    notices = [
        {"issue_type": "first", "never_do": ["a"], "status": "validated"},
        {"issue_type": "second", "never_do": ["b"], "status": "validated"},
        {"issue_type": "third", "never_do": ["c"], "status": "validated"},
    ]

    redlines = build_notice_redlines(notices)

    first_pos = redlines.find("[first]")
    second_pos = redlines.find("[second]")
    third_pos = redlines.find("[third]")
    assert 0 <= first_pos < second_pos < third_pos

