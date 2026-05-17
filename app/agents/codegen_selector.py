from __future__ import annotations

from typing import Any

from app.agents.validator import FixValidator


class CodegenSelector:
    def __init__(self, validator: FixValidator) -> None:
        self.validator = validator

    def evaluate_candidate(self, strategy: str, code: str) -> dict[str, Any]:
        issues = self.validator.preflight_code_quality(code)
        score_breakdown = self._score_breakdown(code, issues)
        score = score_breakdown["total"]
        critique = self._build_critique(issues)
        return {
            "strategy": strategy,
            "code": code,
            "score": score,
            "scoreBreakdown": score_breakdown,
            "issues": issues,
            "issueCount": len(issues),
            "issueLabels": [issue.get("rootCauseLabel") for issue in issues],
            "codeLength": len(code),
            "critique": critique,
        }

    @staticmethod
    def _score_breakdown(code: str, issues: list[dict[str, Any]]) -> dict[str, float]:
        # Quality issues dominate the score; richer code is a small tie-breaker.
        issue_penalty = float(len(issues) * 25.0)
        richness_bonus = float(min(len(code) / 300.0, 15.0))
        total = round(100.0 - issue_penalty + richness_bonus, 3)
        return {
            "base": 100.0,
            "issuePenalty": issue_penalty,
            "richnessBonus": round(richness_bonus, 3),
            "total": total,
        }

    @staticmethod
    def _build_critique(issues: list[dict[str, Any]]) -> str:
        if not issues:
            return "No quality-gate issues detected."
        labels = [str(issue.get("rootCauseLabel") or "unknown_issue") for issue in issues]
        uniq = ", ".join(sorted(set(labels)))
        return f"Quality-gate issues detected: {uniq}."

    def select_best(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        if not candidates:
            raise ValueError("No code candidates were provided")
        return sorted(
            candidates,
            key=lambda item: (-float(item["score"]), int(item["issueCount"]), -int(item["codeLength"])),
        )[0]

    @staticmethod
    def selection_rationale(selected: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
        ranked = sorted(
            candidates,
            key=lambda item: (-float(item["score"]), int(item["issueCount"]), -int(item["codeLength"])),
        )
        if len(ranked) < 2:
            return f"Selected {selected['strategy']} as the only candidate."
        second = ranked[1]
        return (
            f"Selected {selected['strategy']} (score={selected['score']}, issues={selected['issueCount']}) "
            f"over {second['strategy']} (score={second['score']}, issues={second['issueCount']})."
        )

