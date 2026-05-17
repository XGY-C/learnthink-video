from __future__ import annotations

from pathlib import Path
import yaml


class NoticeRepository:
    def __init__(self, prompt_root: Path) -> None:
        self.file_path = Path(prompt_root) / "notices" / "validated_notices.yaml"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("[]\n", encoding="utf-8")

    def load(self) -> list[dict]:
        return yaml.safe_load(self.file_path.read_text(encoding="utf-8")) or []

    def append_validated_notice(
        self,
        issue_type: str,
        rule: str,
        evidence_attempts: int = 1,
        essence: str | None = None,
        root_cause: str | None = None,
        never_do: list[str] | None = None,
        guardrails: list[str] | None = None,
        trigger_signals: list[str] | None = None,
        preferred_pattern: str | None = None,
        source: str = "validator",
        confidence: float | None = None,
    ) -> None:
        preferred = (preferred_pattern or rule or "").strip()
        notices = self.load()
        for notice in notices:
            if notice.get("issue_type") == issue_type and notice.get("preferred_pattern") == preferred:
                evidence = notice.setdefault("evidence", {})
                evidence["verified_attempts"] = evidence.get("verified_attempts", 1) + evidence_attempts
                if essence:
                    notice["essence"] = essence
                if root_cause:
                    notice["root_cause"] = root_cause
                if never_do:
                    notice["never_do"] = never_do
                if guardrails:
                    notice["guardrails"] = guardrails
                if trigger_signals:
                    notice["trigger_signals"] = trigger_signals
                if preferred:
                    notice["preferred_pattern"] = preferred
                notice["source"] = source or notice.get("source") or "validator"
                if confidence is not None:
                    notice["confidence"] = confidence
                break
        else:
            notices.append(
                {
                    "id": f"NOTICE_{len(notices)+1:04d}",
                    "issue_type": issue_type,
                    "essence": essence or f"该问题属于 {issue_type} 类错误，需要抽象为稳定预防规则。",
                    "root_cause": root_cause or issue_type,
                    "never_do": never_do or ["不要在未定位根因时反复使用同一失败路径。"],
                    "guardrails": guardrails or [preferred or "先定位根因，再应用对应修复策略。"],
                    "trigger_signals": trigger_signals or [issue_type],
                    "preferred_pattern": preferred,
                    "source": source,
                    "confidence": confidence if confidence is not None else 0.8,
                    "evidence": {"verified_attempts": evidence_attempts, "success_rate": 1.0},
                    "status": "validated",
                }
            )
        self.file_path.write_text(yaml.safe_dump(notices, allow_unicode=True, sort_keys=False), encoding="utf-8")
