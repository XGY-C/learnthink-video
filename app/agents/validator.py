from __future__ import annotations

import re

from app.models.issues import FixValidationResult


class FixValidator:
    _MATH_HINT_RE = re.compile(r"(\\\\frac|\\\\sqrt|\^|[xabc]2|[xabc]\u00b2|\u0394|=)")
    _PLACEHOLDER_HINT_RE = re.compile(
        r"(parabola_|dotted_line|simple_arrow|curved_arrow|highlight|intersection)",
        re.IGNORECASE,
    )
    _AXES_INVALID_KWARGS_RE = re.compile(r"Axes\s*\((?P<body>[\s\S]*?)\)")

    def preflight_code_quality(self, code: str) -> list[dict]:
        issues: list[dict] = []

        make_shape_lines = [line.strip() for line in code.splitlines() if "make_shape(" in line]
        has_mathtex = ("MathTex(" in code) or ("Tex(" in code)

        # Rule 1: formula-like strings must be rendered with MathTex/Tex instead of generic shapes.
        if not has_mathtex and any(self._MATH_HINT_RE.search(line) for line in make_shape_lines):
            issues.append(
                {
                    "issueId": "QG_001_MATH_RENDER",
                    "stage": "codegen",
                    "errorType": "CodeQualityGateError",
                    "rootCauseLabel": "formula_not_rendered_with_mathtex",
                    "normalizedMessage": "Formula-like content was generated without MathTex/Tex rendering.",
                    "signature": "qg-math-render",
                    "confidence": 0.95,
                    "evidenceLines": make_shape_lines[:6],
                }
            )

        # Rule 2: unresolved placeholder visual tokens should not survive into final generated code.
        placeholder_lines = [line for line in make_shape_lines if self._PLACEHOLDER_HINT_RE.search(line)]
        if placeholder_lines:
            issues.append(
                {
                    "issueId": "QG_002_PLACEHOLDER_VISUAL",
                    "stage": "codegen",
                    "errorType": "CodeQualityGateError",
                    "rootCauseLabel": "unresolved_visual_placeholder",
                    "normalizedMessage": "Placeholder visual tokens were not converted into concrete Manim primitives.",
                    "signature": "qg-placeholder-visual",
                    "confidence": 0.9,
                    "evidenceLines": placeholder_lines[:6],
                }
            )

        # Rule 3: repeated ORIGIN placements in one scene often indicate overlapping objects.
        for scene_idx, chunk in enumerate(code.split("def _play_scene_"), start=0):
            if scene_idx == 0:
                continue
            overlap_count = chunk.count(".move_to(ORIGIN)")
            if overlap_count > 1:
                issues.append(
                    {
                        "issueId": f"QG_003_OVERLAP_{scene_idx:02d}",
                        "stage": "codegen",
                        "errorType": "CodeQualityGateError",
                        "rootCauseLabel": "layout_overlap_risk",
                        "normalizedMessage": "Multiple objects are placed at ORIGIN in the same scene, causing overlap risk.",
                        "signature": f"qg-overlap-scene-{scene_idx:02d}",
                        "confidence": 0.8,
                        "evidenceLines": [f"scene_{scene_idx:02d}: move_to(ORIGIN) x{overlap_count}"],
                    }
                )

        # Rule 4: Manim CE Axes does not accept height/width kwargs; use y_length/x_length instead.
        axes_kwarg_hits = []
        for match in self._AXES_INVALID_KWARGS_RE.finditer(code):
            body = match.group("body")
            if "height=" in body or "width=" in body:
                snippet = f"Axes({body.strip()})"
                axes_kwarg_hits.append(snippet[:180])
        if axes_kwarg_hits:
            issues.append(
                {
                    "issueId": "QG_004_AXES_INVALID_KWARG",
                    "stage": "codegen",
                    "errorType": "CodeQualityGateError",
                    "rootCauseLabel": "invalid_keyword_in_mobject_initialization",
                    "normalizedMessage": "Axes constructor uses unsupported height/width kwargs; use y_length/x_length.",
                    "signature": "qg-axes-invalid-kwargs",
                    "confidence": 0.95,
                    "evidenceLines": axes_kwarg_hits[:6],
                }
            )

        return issues

    @staticmethod
    def is_same_issue(old_issue: dict, new_issue: dict) -> bool:
        return (
            old_issue["stage"] == new_issue["stage"]
            and old_issue["errorType"] == new_issue["errorType"]
            and old_issue["rootCauseLabel"] == new_issue["rootCauseLabel"]
            and (
                old_issue["normalizedMessage"] == new_issue["normalizedMessage"]
                or old_issue["signature"] == new_issue["signature"]
            )
        )

    def run(
        self,
        target_issues: list[dict],
        new_issues: list[dict],
        introduced_earlier_blocker: bool = False,
    ) -> dict:
        target_ids = [issue["issueId"] for issue in target_issues]
        if introduced_earlier_blocker:
            result = FixValidationResult(
                targetIssueIds=target_ids,
                resolvedIssueIds=[],
                unresolvedIssueIds=[],
                blockedIssueIds=target_ids,
                isEffective=False,
                shouldLearn=False,
                reason="A new earlier blocking issue prevented issue-level verification",
                candidateNotice=None,
            )
            return result.model_dump(by_alias=True)

        resolved: list[str] = []
        unresolved: list[str] = []

        for old_issue in target_issues:
            if any(self.is_same_issue(old_issue, new_issue) for new_issue in new_issues):
                unresolved.append(old_issue["issueId"])
            else:
                resolved.append(old_issue["issueId"])

        should_learn = bool(resolved) and not unresolved
        candidate_notice = None
        if should_learn and target_issues:
            root = target_issues[0]["rootCauseLabel"]
            if root == "invalid_run_time":
                candidate_notice = "所有动画时长都应限制到正数安全下限，例如 max(value, 1/fps)。"
            elif root == "missing_import":
                candidate_notice = "在生成场景代码前，必须显式声明所需 import，避免运行期缺失依赖。"
            elif root == "undefined_name":
                candidate_notice = "避免在符号导入或定义之前引用它们，确保名称在使用前可用。"

        result = FixValidationResult(
            targetIssueIds=target_ids,
            resolvedIssueIds=resolved,
            unresolvedIssueIds=unresolved,
            blockedIssueIds=[],
            isEffective=bool(resolved),
            shouldLearn=should_learn,
            reason="Issue-level validation completed",
            candidateNotice=candidate_notice,
        )
        return result.model_dump(by_alias=True)
