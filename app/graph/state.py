from __future__ import annotations

from typing import Any, TypedDict


class VideoGraphState(TypedDict, total=False):
    task_id: str
    status: str
    request_payload: dict[str, Any]
    max_attempts: int
    attempt_no: int
    task_dir: str

    normalized_request: dict[str, Any]
    scene_ir: dict[str, Any]
    risk_report: dict[str, Any]
    notices: list[dict[str, Any]]

    current_code: str
    selected_codegen_strategy: str
    current_issues: list[dict[str, Any]]
    previous_issues: list[dict[str, Any]]

    last_render_report: dict[str, Any]
    last_repair_metadata: dict[str, Any] | None
    last_validation: dict[str, Any] | None
    last_repair_change: dict[str, Any] | None
    no_progress_streak: int
    issue_signature_history: list[str]
    loop_guard_reason: str | None
    upload_result: dict[str, Any] | None
    audio_assets: list[dict[str, Any]]
    bgm_asset: dict[str, Any] | None
    audio_mix_report: dict[str, Any] | None
    mux_report: dict[str, Any] | None
    qc_report: dict[str, Any] | None
    final_video_path: str | None
    final_audio_path: str | None

    cache_key: str | None
    cache_hit: bool

    final_result: dict[str, Any] | None
    error_message: str | None
