from __future__ import annotations

from app.graph.state import VideoGraphState


def route_after_cache_check(state: VideoGraphState) -> str:
    return "upload_video" if state.get("cache_hit") else "load_notices"


def route_after_asset_resolve(state: VideoGraphState) -> str:
    issues = state.get("current_issues") or []
    if issues:
        return "finalize_failure"
    return "check_cache"


def route_after_codegen(state: VideoGraphState) -> str:
    issues = state.get("current_issues") or []
    if not issues:
        return "render_code"
    if state.get("attempt_no", 1) >= state.get("max_attempts", 1):
        return "finalize_failure"
    return "repair_code"


def route_after_render(state: VideoGraphState) -> str:
    report = state.get("last_render_report") or {}
    if report.get("success"):
        # Even after success, validate the previous fix so learning can be persisted.
        return "validate_previous_fix"

    if state.get("attempt_no", 1) > state.get("max_attempts", 1):
        return "generate_fallback_video"

    return "diagnose_errors"


def route_after_validation(state: VideoGraphState) -> str:
    report = state.get("last_render_report") or {}
    if report.get("success"):
        return "compose_audio_timeline"

    if state.get("loop_guard_reason"):
        return "generate_fallback_video"

    if state.get("attempt_no", 1) > state.get("max_attempts", 1):
        return "generate_fallback_video"
    return "repair_code"


def route_after_repair(state: VideoGraphState) -> str:
    if state.get("loop_guard_reason"):
        return "generate_fallback_video"

    if state.get("attempt_no", 1) > state.get("max_attempts", 1):
        return "generate_fallback_video"

    return "increment_attempt"


def route_after_audio_compose(state: VideoGraphState) -> str:
    report = state.get("audio_mix_report") or {}
    return "mux_audio_video" if report.get("success") else "finalize_failure"


def route_after_fallback_video(state: VideoGraphState) -> str:
    """兜底视频渲染后的路由"""
    status = state.get("status")
    if status == "FALLBACK_SUCCESS":
        # 兜底视频成功，继续合并音频
        return "compose_audio_timeline"
    else:
        # 兜底视频也失败了，直接终止
        return "finalize_failure"


def route_after_mux(state: VideoGraphState) -> str:
    report = state.get("mux_report") or {}
    return "media_qc" if report.get("success") else "finalize_failure"


def route_after_qc(state: VideoGraphState) -> str:
    report = state.get("qc_report") or {}
    return "save_cache" if report.get("passed") else "finalize_failure"

