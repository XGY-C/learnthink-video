from __future__ import annotations

import difflib
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.utils.file_utils import write_json, write_text


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    tool: str
    return_code: int
    stdout: str
    stderr: str
    elapsed_ms: int


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _unified_diff(before: str, after: str, fromfile: str = "a/generated.py", tofile: str = "b/generated.py") -> str:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=fromfile,
            tofile=tofile,
        )
    )


def run_compileall_gate(code: str, working_dir: Path, file_name: str = "generated.py", timeout_sec: int = 15) -> QualityGateResult:
    """Gate: ensure code is syntactically valid (byte-compilable) without importing dependencies."""
    import time

    working_dir.mkdir(parents=True, exist_ok=True)
    candidate_file = working_dir / file_name
    write_text(candidate_file, code)

    start = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", str(candidate_file)],
        cwd=str(working_dir),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    elapsed_ms = int((time.time() - start) * 1000)

    return QualityGateResult(
        passed=proc.returncode == 0,
        tool="python -m compileall",
        return_code=int(proc.returncode),
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        elapsed_ms=elapsed_ms,
    )


def create_repair_edit_transaction(
    *,
    attempt_dir: Path,
    before_code: str,
    candidate_code: str,
    repair_metadata: dict[str, Any],
    llm_trace: dict[str, Any] | None,
    strategy: str,
    timeout_sec: int = 15,
) -> dict[str, Any]:
    """Create a reversible edit transaction journal + quality gate report.

    Note: This function does NOT mutate existing files used by rendering.
    It records backups/diff and returns the gated code to be used for next attempt.
    """

    plan_id = f"{_utc_timestamp()}_{uuid.uuid4().hex[:8]}"
    tx_dir = attempt_dir / "edits" / plan_id
    backup_dir = tx_dir / "backup"
    candidate_dir = tx_dir / "candidate"

    # Backup (string snapshot)
    write_text(backup_dir / "generated.py", before_code)

    # Plan: for now we journal a single rewrite operation (compatible with current RepairAgent output)
    plan = {
        "planId": plan_id,
        "strategy": strategy,
        "createdAt": _utc_timestamp(),
        "reasoningSummary": repair_metadata.get("expectedOutcome") or "",
        "edits": [
            {
                "op": "rewrite_file",
                "filePath": "generated.py",
                "newContentChars": len(candidate_code),
            }
        ],
        "expectedEffects": repair_metadata.get("patchSummary") or [],
        "riskNotes": [],
    }
    write_json(tx_dir / "plan.json", plan)

    # Diff + apply report
    diff_text = _unified_diff(before_code, candidate_code)
    write_text(tx_dir / "diff.patch", diff_text)

    before_lines = before_code.splitlines()
    after_lines = candidate_code.splitlines()
    apply_report = {
        "planId": plan_id,
        "changed": before_code != candidate_code,
        "charDelta": len(candidate_code) - len(before_code),
        "lineDelta": len(after_lines) - len(before_lines),
        "diffChars": len(diff_text),
    }

    # Gate
    try:
        gate_result = run_compileall_gate(
            candidate_code,
            candidate_dir,
            file_name="generated.py",
            timeout_sec=timeout_sec,
        )
        gate_report = {
            "passed": gate_result.passed,
            "tool": gate_result.tool,
            "returnCode": gate_result.return_code,
            "elapsedMs": gate_result.elapsed_ms,
            "stdout": gate_result.stdout,
            "stderr": gate_result.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        gate_report = {
            "passed": False,
            "tool": "python -m compileall",
            "returnCode": -1,
            "elapsedMs": int(timeout_sec * 1000),
            "stdout": "",
            "stderr": f"timeout after {timeout_sec}s: {exc}",
        }

    write_json(tx_dir / "gate_report.json", gate_report)

    # Persist raw repair metadata for audit
    write_json(tx_dir / "repair_metadata.json", repair_metadata)
    write_json(tx_dir / "llm_trace.json", llm_trace or {})

    apply_report["gate"] = {"compileall": {"passed": bool(gate_report.get("passed"))}}
    write_json(tx_dir / "apply_report.json", apply_report)

    return {
        "planId": plan_id,
        "txDir": str(tx_dir),
        "backupDir": str(backup_dir),
        "candidateDir": str(candidate_dir),
        "applyReport": apply_report,
        "gateReport": gate_report,
        "candidateCode": candidate_code if gate_report.get("passed") else None,
        "passed": bool(gate_report.get("passed")),
    }
