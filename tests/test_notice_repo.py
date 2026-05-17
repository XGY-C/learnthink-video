from pathlib import Path
from app.storage.notice_repo import NoticeRepository


def test_append_notice(tmp_path: Path):
    repo = NoticeRepository(tmp_path)
    repo.append_validated_notice("invalid_run_time", "Clamp to max(value, 1/fps)")
    notices = repo.load()
    assert len(notices) == 1
    assert notices[0]["issue_type"] == "invalid_run_time"
    assert notices[0]["preferred_pattern"] == "Clamp to max(value, 1/fps)"


def test_append_notice_with_summaries(tmp_path: Path):
    repo = NoticeRepository(tmp_path)
    repo.append_validated_notice(
        "value_error",
        "Use Tex for non-math Chinese text",
        essence="MathTex is not a generic natural-language renderer",
        root_cause="MathTex fails on plain Chinese text fragments",
        never_do=["Do not feed full Chinese sentences into MathTex"],
        guardrails=["Switch to Text/Tex for natural-language lines"],
        trigger_signals=["latex error converting to dvi"],
        preferred_pattern="Switch to Text/Tex for natural-language lines",
        source="llm",
        confidence=0.92,
    )
    notice = repo.load()[0]
    assert notice["root_cause"].startswith("MathTex fails")
    assert notice["preferred_pattern"].startswith("Switch to Text")
    assert notice["source"] == "llm"
    assert notice["confidence"] == 0.92


def test_append_notice_merges_duplicate_and_increments_evidence(tmp_path: Path):
    repo = NoticeRepository(tmp_path)
    repo.append_validated_notice("missing_import", "Add typing imports", evidence_attempts=1)
    repo.append_validated_notice("missing_import", "Add typing imports", evidence_attempts=2)
    notice = repo.load()[0]
    assert notice["evidence"]["verified_attempts"] == 3
