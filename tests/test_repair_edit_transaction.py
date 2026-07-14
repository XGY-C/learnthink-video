from __future__ import annotations

from pathlib import Path

from app.storage.task_repo import TaskRepository
from app.utils.repair_edit_transaction import create_repair_edit_transaction


def test_repair_edit_transaction_compileall_pass(tmp_path: Path) -> None:
    repo = TaskRepository(tmp_path)
    state = repo.init_task("t1", max_attempts=3)
    attempt_dir = repo.prepare_attempt(state.task_id, 1)

    before = "from manim import *\n\nclass A(Scene):\n    def construct(self):\n        pass\n"
    after = "from manim import *\n\nclass A(Scene):\n    def construct(self):\n        self.wait(0.1)\n"

    result = create_repair_edit_transaction(
        attempt_dir=attempt_dir,
        before_code=before,
        candidate_code=after,
        repair_metadata={"fixStrategy": "test", "patchSummary": ["add wait"], "expectedOutcome": "ok"},
        llm_trace={"llmUsed": False},
        strategy="patch_first",
    )

    assert result["passed"] is True
    assert result["candidateCode"] == after

    tx_dir = Path(result["txDir"])
    assert (tx_dir / "backup" / "generated.py").exists()
    assert (tx_dir / "diff.patch").exists()
    assert (tx_dir / "gate_report.json").exists()


def test_repair_edit_transaction_compileall_fail(tmp_path: Path) -> None:
    repo = TaskRepository(tmp_path)
    state = repo.init_task("t2", max_attempts=3)
    attempt_dir = repo.prepare_attempt(state.task_id, 1)

    before = "from manim import *\n\nclass A(Scene):\n    def construct(self):\n        pass\n"
    after = "from manim import *\n\nclass A(Scene):\n    def construct(self):\n        def broken(:\n            pass\n"

    result = create_repair_edit_transaction(
        attempt_dir=attempt_dir,
        before_code=before,
        candidate_code=after,
        repair_metadata={"fixStrategy": "test", "patchSummary": ["break"], "expectedOutcome": "fail"},
        llm_trace={"llmUsed": True},
        strategy="patch_first",
    )

    assert result["passed"] is False
    assert result["candidateCode"] is None
    assert "stderr" in result["gateReport"]
