from app.graph.router import (
    route_after_codegen,
    route_after_asset_resolve,
    route_after_audio_compose,
    route_after_mux,
    route_after_qc,
    route_after_repair,
    route_after_render,
    route_after_validation,
)


def test_route_after_render_success():
    state = {"last_render_report": {"success": True}, "attempt_no": 1, "max_attempts": 3}
    assert route_after_render(state) == "validate_previous_fix"


def test_route_after_render_retry():
    state = {"last_render_report": {"success": False}, "attempt_no": 1, "max_attempts": 3}
    assert route_after_render(state) == "diagnose_errors"


def test_route_after_render_fail():
    state = {"last_render_report": {"success": False}, "attempt_no": 3, "max_attempts": 3}
    assert route_after_render(state) == "finalize_failure"


def test_route_after_validation():
    assert route_after_validation({"last_render_report": {"success": True}}) == "compose_audio_timeline"
    assert route_after_validation({"attempt_no": 1, "max_attempts": 3}) == "repair_code"
    assert route_after_validation({"attempt_no": 3, "max_attempts": 3}) == "finalize_failure"
    assert route_after_validation({"attempt_no": 1, "max_attempts": 3, "loop_guard_reason": "no_progress"}) == "finalize_failure"


def test_route_after_repair():
    assert route_after_repair({"attempt_no": 1, "max_attempts": 3}) == "increment_attempt"
    assert route_after_repair({"attempt_no": 3, "max_attempts": 3}) == "finalize_failure"
    assert route_after_repair({"attempt_no": 1, "max_attempts": 3, "loop_guard_reason": "no_progress"}) == "finalize_failure"


def test_route_after_asset_resolve():
    assert route_after_asset_resolve({"current_issues": []}) == "load_notices"
    assert route_after_asset_resolve({"current_issues": [{"issueId": "A1"}]}) == "finalize_failure"


def test_route_after_codegen():
    assert route_after_codegen({"current_issues": []}) == "render_code"
    assert route_after_codegen({"current_issues": [{"issueId": "Q1"}], "attempt_no": 1, "max_attempts": 3}) == "repair_code"
    assert route_after_codegen({"current_issues": [{"issueId": "Q1"}], "attempt_no": 3, "max_attempts": 3}) == "finalize_failure"


def test_route_after_audio_compose():
    assert route_after_audio_compose({"audio_mix_report": {"success": True}}) == "mux_audio_video"
    assert route_after_audio_compose({"audio_mix_report": {"success": False}}) == "finalize_failure"


def test_route_after_mux_and_qc():
    assert route_after_mux({"mux_report": {"success": True}}) == "media_qc"
    assert route_after_mux({"mux_report": {"success": False}}) == "finalize_failure"
    assert route_after_qc({"qc_report": {"passed": True}}) == "upload_video"
    assert route_after_qc({"qc_report": {"passed": False}}) == "finalize_failure"

