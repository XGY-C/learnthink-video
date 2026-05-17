from __future__ import annotations


def build_notice_redlines(notices: list[dict]) -> str:
    """Build compact hard constraints from validated notices for prompt injection."""
    if not notices:
        return ""

    lines: list[str] = []
    for notice in notices:
        if str(notice.get("status") or "").lower() not in {"", "validated"}:
            continue

        issue_type = str(notice.get("issue_type") or "unknown_issue")
        never_do = notice.get("never_do") or []
        preferred = (notice.get("preferred_pattern") or "").strip()

        if isinstance(never_do, list):
            banned = [str(item).strip() for item in never_do if str(item).strip()]
        else:
            banned = []

        if not banned and not preferred:
            continue

        lines.append(f"[{issue_type}]")
        for item in banned[:3]:
            lines.append(f"- MUST_NOT: {item}")
        if preferred:
            lines.append(f"- MUST_PREFER: {preferred}")

    return "\n".join(lines)

