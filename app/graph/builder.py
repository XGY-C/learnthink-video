from __future__ import annotations

import logging
import time

from app.graph.nodes import GraphNodes
from app.graph.router import (
    route_after_cache_check,
    route_after_codegen,
    route_after_audio_compose,
    route_after_asset_resolve,
    route_after_mux,
    route_after_qc,
    route_after_repair,
    route_after_render,
    route_after_validation,
    route_after_fallback_video,
)
from app.graph.state import VideoGraphState


logger = logging.getLogger(__name__)


def _with_node_logging(node_name: str, handler):
    def wrapped(state: VideoGraphState) -> VideoGraphState:
        task_id = state.get("task_id")
        attempt_no = state.get("attempt_no")
        start = time.perf_counter()
        logger.info("[graph] node=%s task=%s attempt=%s start", node_name, task_id, attempt_no)
        try:
            result = handler(state)
        except Exception:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.exception(
                "[graph] node=%s task=%s attempt=%s error elapsedMs=%s",
                node_name,
                task_id,
                attempt_no,
                elapsed_ms,
            )
            raise

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        status = result.get("status") if isinstance(result, dict) else None
        issue_count = len((result or {}).get("current_issues") or []) if isinstance(result, dict) else 0
        logger.info(
            "[graph] node=%s task=%s attempt=%s done status=%s issues=%s elapsedMs=%s",
            node_name,
            task_id,
            attempt_no,
            status,
            issue_count,
            elapsed_ms,
        )
        return result

    return wrapped


def build_video_graph(nodes: GraphNodes):
    try:
        from langgraph.graph import StateGraph, START, END
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("LangGraph is not installed. Please install dependencies from requirements.txt") from exc

    graph = StateGraph(VideoGraphState)

    graph.add_node("initialize_task", _with_node_logging("initialize_task", nodes.initialize_task))
    graph.add_node("plan_request", _with_node_logging("plan_request", nodes.plan_request))
    graph.add_node("load_notices", _with_node_logging("load_notices", nodes.load_notices))
    graph.add_node("resolve_assets", _with_node_logging("resolve_assets", nodes.resolve_assets))
    graph.add_node("check_cache", _with_node_logging("check_cache", nodes.check_cache))
    graph.add_node("generate_code", _with_node_logging("generate_code", nodes.generate_code))
    graph.add_node("render_code", _with_node_logging("render_code", nodes.render_code))
    graph.add_node("compose_audio_timeline", _with_node_logging("compose_audio_timeline", nodes.compose_audio_timeline))
    graph.add_node("mux_audio_video", _with_node_logging("mux_audio_video", nodes.mux_audio_video))
    graph.add_node("media_qc", _with_node_logging("media_qc", nodes.media_qc))
    graph.add_node("diagnose_errors", _with_node_logging("diagnose_errors", nodes.diagnose_errors))
    graph.add_node("validate_previous_fix", _with_node_logging("validate_previous_fix", nodes.validate_previous_fix))
    graph.add_node("repair_code", _with_node_logging("repair_code", nodes.repair_code))
    graph.add_node("increment_attempt", _with_node_logging("increment_attempt", nodes.increment_attempt))
    graph.add_node("generate_fallback_video", _with_node_logging("generate_fallback_video", nodes.generate_fallback_video))
    graph.add_node("save_cache", _with_node_logging("save_cache", nodes.save_cache))
    graph.add_node("upload_video", _with_node_logging("upload_video", nodes.upload_video))
    graph.add_node("finalize_failure", _with_node_logging("finalize_failure", nodes.finalize_failure))

    graph.add_edge(START, "initialize_task")
    graph.add_edge("initialize_task", "plan_request")
    graph.add_edge("plan_request", "resolve_assets")
    graph.add_conditional_edges(
        "resolve_assets",
        route_after_asset_resolve,
        {
            "check_cache": "check_cache",
            "finalize_failure": "finalize_failure",
        },
    )
    graph.add_conditional_edges(
        "check_cache",
        route_after_cache_check,
        {
            "upload_video": "upload_video",
            "load_notices": "load_notices",
        },
    )
    graph.add_edge("load_notices", "generate_code")
    graph.add_conditional_edges(
        "generate_code",
        route_after_codegen,
        {
            "render_code": "render_code",
            "repair_code": "repair_code",
            "finalize_failure": "finalize_failure",
        },
    )

    graph.add_conditional_edges(
        "render_code",
        route_after_render,
        {
            "validate_previous_fix": "validate_previous_fix",
            "diagnose_errors": "diagnose_errors",
            "finalize_failure": "finalize_failure",
        },
    )

    graph.add_conditional_edges(
        "compose_audio_timeline",
        route_after_audio_compose,
        {
            "mux_audio_video": "mux_audio_video",
            "finalize_failure": "finalize_failure",
        },
    )
    graph.add_conditional_edges(
        "mux_audio_video",
        route_after_mux,
        {
            "media_qc": "media_qc",
            "finalize_failure": "finalize_failure",
        },
    )
    graph.add_conditional_edges(
        "media_qc",
        route_after_qc,
        {
            "save_cache": "save_cache",
            "finalize_failure": "finalize_failure",
        },
    )
    graph.add_edge("save_cache", "upload_video")

    graph.add_edge("diagnose_errors", "validate_previous_fix")
    graph.add_conditional_edges(
        "validate_previous_fix",
        route_after_validation,
        {
            "compose_audio_timeline": "compose_audio_timeline",
            "repair_code": "repair_code",
            "generate_fallback_video": "generate_fallback_video",
        },
    )
    graph.add_conditional_edges(
        "repair_code",
        route_after_repair,
        {
            "increment_attempt": "increment_attempt",
            "generate_fallback_video": "generate_fallback_video",
        },
    )
    graph.add_edge("increment_attempt", "render_code")

    graph.add_conditional_edges(
        "generate_fallback_video",
        route_after_fallback_video,
        {
            "compose_audio_timeline": "compose_audio_timeline",
            "finalize_failure": "finalize_failure",
        },
    )

    graph.add_edge("upload_video", END)
    graph.add_edge("finalize_failure", END)

    return graph.compile()
