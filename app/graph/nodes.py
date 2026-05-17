from __future__ import annotations

import logging
from pathlib import Path

from app.agents.code_expert import ManimCodeExpert
from app.agents.diagnoser import ErrorDiagnoser
from app.agents.direct_codegen import DirectCodegenAgent
from app.agents.notice_summarizer import NoticeSummarizer
from app.agents.planner import RequestPlanner
from app.agents.repair import RepairAgent
from app.agents.validator import FixValidator
from app.core.config import Settings
from app.graph.state import VideoGraphState
from app.llm.factory import build_llm_client
from app.models.contracts import RenderRequest
from app.models.task import TaskState
from app.storage.notice_repo import NoticeRepository
from app.storage.task_repo import TaskRepository
from app.tools.audio_asset_resolver import AudioAssetResolver
from app.tools.audio_timeline_composer import AudioTimelineComposer
from app.tools.av_muxer import AVMuxer
from app.tools.media_qc import MediaQC
from app.tools.render_executor import RenderExecutor
from app.tools.oss_uploader import OSSUploader
from app.tools.manim_doc_search import ManimDocSearchTool
from app.utils.file_utils import write_json, write_text


logger = logging.getLogger(__name__)


def _compute_code_change(before: str, after: str) -> dict[str, int | bool]:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    return {
        "changed": before != after,
        "charDelta": len(after) - len(before),
        "lineDelta": len(after_lines) - len(before_lines),
    }


def _compose_failure_message(state: VideoGraphState) -> str:
    base = state.get("error_message") or "Render failed after max attempts"
    details: list[str] = []

    loop_guard_reason = state.get("loop_guard_reason")
    if loop_guard_reason:
        details.append(f"loop_guard={loop_guard_reason}")

    fallback_reason = ((state.get("last_repair_metadata") or {}).get("fallbackReason"))
    if fallback_reason:
        details.append(f"llm_fallback={fallback_reason}")

    if not details:
        return base
    return f"{base} ({'; '.join(details)})"


def _default_notice_rule(issue: dict) -> str:
    root = (issue.get("rootCauseLabel") or "").strip()
    message = (issue.get("normalizedMessage") or "").lower()

    if root == "value_error" and "latex error converting to dvi" in message:
        return (
            "遇到 LaTeX 渲染失败时，避免在 MathTex 中放自然语言文本，中文或长句请改用 Text。"
        )
    if root == "api_deprecation":
        return "生成代码时优先使用当前 Manim API，避免调用已废弃的方法或属性。"
    if root == "undefined_name":
        return "生成场景代码前确保符号已导入或定义，避免未定义名称错误。"
    return f"针对根因 {root or 'unknown_issue'} 增加稳定性防护，避免同类错误再次出现。"


class GraphNodes:
    def __init__(self, settings: Settings, task_repo: TaskRepository) -> None:
        self.settings = settings
        self.task_repo = task_repo
        self.notice_repo = NoticeRepository(settings.prompt_root)

        llm_client_default = build_llm_client(settings)
        llm_client_planner = build_llm_client(settings, agent_name="planner")
        llm_client_code_expert = build_llm_client(settings, agent_name="code_expert")
        llm_client_diagnoser = build_llm_client(settings, agent_name="diagnoser")
        llm_client_repair = build_llm_client(settings, agent_name="repair")
        llm_client_summarizer = build_llm_client(settings, agent_name="summarizer")
        
        # 初始化文档搜索工具
        logger.info("[graph_nodes] initializing ManimDocSearchTool...")
        # 使用项目根目录（app 的父目录）
        project_root = Path(__file__).parent.parent.parent
        docs_root = project_root / "vendor-docs" / "manim"
        logger.info("[graph_nodes] docs_root=%s exists=%s", docs_root, docs_root.exists())
        try:
            doc_search_tool = ManimDocSearchTool(
                docs_root=docs_root,
                enable_semantic_search=False,  # 默认关闭，需要高性能时开启
            )
            logger.info("[graph_nodes] ManimDocSearchTool initialized successfully")
        except Exception as e:
            logger.warning("[graph_nodes] failed to initialize ManimDocSearchTool: %s", e)
            doc_search_tool = None

        self.planner = RequestPlanner()
        self.code_expert = ManimCodeExpert()
        self.direct_codegen = DirectCodegenAgent(llm_client=llm_client_code_expert)
        self.diagnoser = ErrorDiagnoser(llm_client=llm_client_diagnoser, enable_llm_fallback=settings.enable_llm_assist)
        self.repair_agent = RepairAgent(
            llm_client=llm_client_repair,
            enable_llm_fallback=settings.enable_llm_assist,
            doc_search_tool=doc_search_tool,
        )
        self.validator = FixValidator()
        self.notice_summarizer = NoticeSummarizer(llm_client=llm_client_summarizer, enabled=settings.enable_llm_assist)
        self.render_executor = RenderExecutor(settings.manim_bin, settings.ffprobe_bin)
        self.audio_asset_resolver = AudioAssetResolver(settings.audio_cache_root, settings.ffprobe_bin)
        self.audio_timeline_composer = AudioTimelineComposer(settings.ffmpeg_bin)
        self.av_muxer = AVMuxer(settings.ffmpeg_bin)
        self.media_qc_checker = MediaQC(settings.ffprobe_bin, settings.max_av_duration_diff_sec)
        self.oss_uploader = OSSUploader(settings)

    def initialize_task(self, state: VideoGraphState) -> VideoGraphState:
        request = RenderRequest(**state["request_payload"])
        task_state = self.task_repo.init_task(state["task_id"], max_attempts=min(request.render_policy.max_repair_rounds, self.settings.max_attempts))
        self.task_repo.save_request_artifact(state["task_id"], "request.json", request.model_dump(by_alias=True))
        return {
            "status": "RECEIVED",
            "attempt_no": 1,
            "max_attempts": task_state.max_attempts,
            "task_dir": str(self.task_repo.task_dir(state["task_id"])),
            "previous_issues": [],
            "current_issues": [],
            "last_validation": None,
            "last_repair_metadata": None,
            "last_repair_change": None,
            "no_progress_streak": 0,
            "issue_signature_history": [],
            "loop_guard_reason": None,
            "upload_result": None,
            "audio_assets": [],
            "bgm_asset": None,
            "audio_mix_report": None,
            "mux_report": None,
            "qc_report": None,
            "final_video_path": None,
            "final_audio_path": None,
            "final_result": None,
            "error_message": None,
        }

    def plan_request(self, state: VideoGraphState) -> VideoGraphState:
        request = RenderRequest(**state["request_payload"])
        plan = self.planner.run(request)
        self.task_repo.save_request_artifact(state["task_id"], "normalized_request.json", plan["normalizedRequest"])
        self.task_repo.save_request_artifact(state["task_id"], "scene_ir.json", plan["sceneIR"])
        self.task_repo.save_request_artifact(state["task_id"], "risk_report.json", plan["riskReport"])
        self._save_task_state(state["task_id"], "PLANNED", state["attempt_no"], state["max_attempts"])
        return {
            "status": "PLANNED",
            "normalized_request": plan["normalizedRequest"],
            "scene_ir": plan["sceneIR"],
            "risk_report": plan["riskReport"],
        }

    def load_notices(self, state: VideoGraphState) -> VideoGraphState:
        return {"notices": self.notice_repo.load()}

    def resolve_assets(self, state: VideoGraphState) -> VideoGraphState:
        request_payload = state.get("normalized_request") or state.get("request_payload") or {}
        timed_scenes = request_payload.get("timedScenes") or []
        bgm_policy = request_payload.get("bgmPolicy") or {}
        result = self.audio_asset_resolver.resolve(state["task_id"], timed_scenes)
        bgm_asset = self.audio_asset_resolver.resolve_single(
            state["task_id"],
            bgm_policy.get("url"),
            label="BGM",
        )
        assets = result.get("assets") or []
        self.task_repo.save_request_artifact(
            state["task_id"],
            "audio_assets.json",
            {"sceneAssets": result, "bgmAsset": bgm_asset},
        )

        failures = [asset for asset in assets if asset.get("status") == "failed"]
        if failures:
            issues = [
                {
                    "issueId": f"AUDIO_001_{idx:03d}",
                    "stage": "audio",
                    "errorType": "AudioDownloadError",
                    "rootCauseLabel": "audio_download_failed",
                    "normalizedMessage": asset.get("error") or "audio download failed",
                    "signature": f"audio-download-{idx:03d}",
                    "confidence": 0.9,
                    "evidenceLines": [str(asset)],
                }
                for idx, asset in enumerate(failures, start=1)
            ]
            return {
                "status": "ASSET_FAILED",
                "audio_assets": assets,
                "bgm_asset": bgm_asset,
                "current_issues": issues,
                "error_message": "Failed to resolve audio assets",
            }

        return {"audio_assets": assets, "bgm_asset": bgm_asset}

    def generate_code(self, state: VideoGraphState) -> VideoGraphState:
        """生成代码策略：
        1. 首次尝试使用 DirectCodegenAgent（支持 LLM 增强）
        2. 如果多次渲染失败超过限定次数，降级使用 ManimCodeExpert 的确定性代码
        """
        attempt_no = state.get("attempt_no", 1)
        max_attempts = state.get("max_attempts", 3)
        
        # 计算失败阈值：当尝试次数超过一半时，切换到确定性模式
        fallback_threshold = max(1, max_attempts // 2 + 1)
        
        if attempt_no >= fallback_threshold:
            # 多次失败后，使用 ManimCodeExpert 的确定性代码
            logger.info(
                "[generate_code] task=%s attempt=%d >= threshold=%d, switching to ManimCodeExpert (deterministic mode)",
                state["task_id"],
                attempt_no,
                fallback_threshold,
            )
            code = self.code_expert.run(state["scene_ir"])
            strategy = "manim_code_expert_fallback"
            trace_info = {
                "mode": "deterministic_fallback",
                "reason": f"attempt {attempt_no} exceeded fallback threshold {fallback_threshold}",
                "llmAttempted": False,
                "llmUsed": False,
            }
        else:
            # 首次或早期尝试，使用 DirectCodegenAgent（可能使用 LLM）
            logger.info(
                "[generate_code] task=%s attempt=%d < threshold=%d, using DirectCodegenAgent",
                state["task_id"],
                attempt_no,
                fallback_threshold,
            )
            code = self.direct_codegen.run(state["scene_ir"], notices=state.get("notices") or [])
            strategy = "direct_semantic"
            trace_info = getattr(
                self.direct_codegen,
                "last_trace",
                {"mode": "unknown", "llmAttempted": False, "llmUsed": False, "warning": "missing_last_trace"},
            )
        
        # 保存追踪信息
        self.task_repo.save_request_artifact(
            state["task_id"],
            "codegen_trace.json",
            {
                "strategy": strategy,
                "attempt_no": attempt_no,
                "fallback_threshold": fallback_threshold,
                **trace_info,
            },
        )
        
        # 执行代码质量预检
        quality_issues = self.validator.preflight_code_quality(code)

        if quality_issues:
            self.task_repo.save_request_artifact(
                state["task_id"],
                "code_quality_issues.json",
                {"issues": quality_issues},
            )
            self._save_task_state(
                state["task_id"],
                "CODE_REJECTED",
                state["attempt_no"],
                state["max_attempts"],
                latest_issue_ids=[issue["issueId"] for issue in quality_issues],
            )
            return {
                "status": "CODE_REJECTED",
                "current_code": code,
                "current_issues": quality_issues,
                "selected_codegen_strategy": strategy,
                "error_message": "Generated code failed pre-render quality gates",
            }

        self._save_task_state(state["task_id"], "CODE_GENERATED", state["attempt_no"], state["max_attempts"])
        return {
            "status": "CODE_GENERATED",
            "current_code": code,
            "selected_codegen_strategy": strategy,
        }

    def render_code(self, state: VideoGraphState) -> VideoGraphState:
        request = RenderRequest(**state["request_payload"])
        attempt_dir = self.task_repo.prepare_attempt(state["task_id"], state["attempt_no"])
        code_file = attempt_dir / "generated.py"
        write_text(code_file, state["current_code"])

        self._save_task_state(
            state["task_id"],
            "RENDERING",
            state["attempt_no"],
            state["max_attempts"],
            latest_issue_ids=[issue["issueId"] for issue in state.get("current_issues", [])],
        )
        report = self.render_executor.run(request=request, code_file=code_file, attempt_dir=attempt_dir)
        return {"status": "RENDERING", "last_render_report": report}

    def diagnose_errors(self, state: VideoGraphState) -> VideoGraphState:
        issue_payload = self.diagnoser.run(state["last_render_report"])
        attempt_dir = self.task_repo.prepare_attempt(state["task_id"], state["attempt_no"])
        write_json(attempt_dir / "issues.json", issue_payload)
        current_issues = issue_payload["issues"]
        self._save_task_state(
            state["task_id"],
            "RENDER_FAILED",
            state["attempt_no"],
            state["max_attempts"],
            latest_issue_ids=[issue["issueId"] for issue in current_issues],
        )
        return {"status": "RENDER_FAILED", "current_issues": current_issues}

    def validate_previous_fix(self, state: VideoGraphState) -> VideoGraphState:
        previous_issues = state.get("previous_issues") or []
        render_succeeded = bool((state.get("last_render_report") or {}).get("success"))
        if not previous_issues:
            if render_succeeded:
                # Successful render should not carry stale issues into completion state.
                return {"last_validation": None, "current_issues": []}
            return {"last_validation": None}

        new_issues = [] if render_succeeded else (state.get("current_issues") or [])
        validation = self.validator.run(
            target_issues=previous_issues,
            new_issues=new_issues,
            introduced_earlier_blocker=False,
        )
        attempt_dir = self.task_repo.prepare_attempt(state["task_id"], state["attempt_no"])
        write_json(attempt_dir / "validation.json", validation)

        candidate_notice = validation.get("candidateNotice")
        if validation.get("shouldLearn") and previous_issues:
            issue_type = previous_issues[0]["rootCauseLabel"]
            if not candidate_notice:
                base_rule = _default_notice_rule(previous_issues[0])
                summary = self.notice_summarizer.summarize(previous_issues=previous_issues, new_issues=new_issues, base_rule=base_rule)
                candidate_notice = NoticeSummarizer.clean_rule(summary.get("preferred_pattern") or base_rule)
                if candidate_notice:
                    self.notice_repo.append_validated_notice(
                        issue_type=issue_type,
                        rule=candidate_notice,
                        essence=str(summary.get("essence") or f"该问题属于 {issue_type} 类型。"),
                        root_cause=str(summary.get("root_cause") or previous_issues[0].get("normalizedMessage") or issue_type),
                        never_do=summary.get("never_do") if isinstance(summary.get("never_do"), list) else None,
                        guardrails=summary.get("guardrails") if isinstance(summary.get("guardrails"), list) else None,
                        trigger_signals=summary.get("trigger_signals") if isinstance(summary.get("trigger_signals"), list) else None,
                        preferred_pattern=candidate_notice,
                        source=str(summary.get("source") or "heuristic"),
                        confidence=float(summary.get("confidence", 0.75)),
                    )
            elif NoticeSummarizer.clean_rule(candidate_notice):
                candidate_notice = NoticeSummarizer.clean_rule(candidate_notice)
                self.notice_repo.append_validated_notice(
                    issue_type=issue_type,
                    rule=candidate_notice,
                )

        if candidate_notice != validation.get("candidateNotice"):
            validation = {**validation, "candidateNotice": candidate_notice}

        result: VideoGraphState = {"last_validation": validation}
        if validation.get("shouldLearn"):
            # Reload persisted notices so the next repair step sees newly learned constraints.
            result["notices"] = self.notice_repo.load()
        if render_succeeded:
            result["current_issues"] = []
        return result

    def repair_code(self, state: VideoGraphState) -> VideoGraphState:
        previous_code = state["current_code"]
        current_issues = state.get("current_issues") or []
        issue_ids = [issue.get("issueId") for issue in current_issues if issue.get("issueId")]

        latest_notices = self.notice_repo.load()
        repair_result = self.repair_agent.run(
            code=previous_code,
            issues=current_issues,
            attempt_no=state["attempt_no"],
            notices=latest_notices,
        )
        repaired_code = repair_result["code"]
        change = _compute_code_change(previous_code, repaired_code)

        attempt_dir = self.task_repo.prepare_attempt(state["task_id"], state["attempt_no"])
        write_json(attempt_dir / "repair_decision.json", repair_result["metadata"])
        write_json(attempt_dir / "llm_repair_trace.json", repair_result.get("llmTrace") or {})

        next_code_file = self.task_repo.attempts_dir(state["task_id"]) / f"{state['attempt_no'] + 1:02d}" / "generated.py"

        unresolved_ids = (state.get("last_validation") or {}).get("unresolvedIssueIds") or []
        issue_key = "|".join(sorted(issue.get("signature") or issue.get("issueId") or "" for issue in current_issues)) or "none"
        issue_history = ((state.get("issue_signature_history") or []) + [issue_key])[-5:]
        no_progress = bool(unresolved_ids) and not change["changed"]
        no_progress_streak = (state.get("no_progress_streak", 0) + 1) if no_progress else 0
        loop_guard_reason = None
        if no_progress_streak >= 2:
            loop_guard_reason = f"no_progress_streak={no_progress_streak}; unresolved={','.join(unresolved_ids)}"

        logger.info(
            "[repair] task=%s attempt=%s changed=%s charDelta=%s lineDelta=%s issueIds=%s strategy=%s noProgressStreak=%s loopGuard=%s attemptDir=%s nextCodeFile=%s",
            state["task_id"],
            state["attempt_no"],
            change["changed"],
            change["charDelta"],
            change["lineDelta"],
            issue_ids,
            repair_result["metadata"].get("fixStrategy"),
            no_progress_streak,
            loop_guard_reason,
            attempt_dir,
            next_code_file,
        )

        self._save_task_state(
            state["task_id"],
            "REPAIRING",
            state["attempt_no"],
            state["max_attempts"],
            latest_issue_ids=[issue["issueId"] for issue in current_issues],
        )
        return {
            "status": "REPAIRING",
            "current_code": repaired_code,
            "last_repair_metadata": repair_result["metadata"],
            "last_repair_change": change,
            "no_progress_streak": no_progress_streak,
            "issue_signature_history": issue_history,
            "loop_guard_reason": loop_guard_reason,
            "previous_issues": current_issues,
            "notices": latest_notices,
            "error_message": "Repair loop detected with no effective code changes" if loop_guard_reason else state.get("error_message"),
        }

    def increment_attempt(self, state: VideoGraphState) -> VideoGraphState:
        return {"attempt_no": state["attempt_no"] + 1}

    def compose_audio_timeline(self, state: VideoGraphState) -> VideoGraphState:
        attempt_dir = self.task_repo.prepare_attempt(state["task_id"], state["attempt_no"])
        scene_ir = state.get("scene_ir") or {}
        audio_policy = scene_ir.get("audioPolicy") or {}
        bgm_policy = scene_ir.get("bgmPolicy") or {}
        report = self.audio_timeline_composer.compose(
            state.get("audio_assets") or [],
            attempt_dir,
            audio_policy=audio_policy,
            bgm_policy=bgm_policy,
            bgm_asset=state.get("bgm_asset"),
        )
        write_json(attempt_dir / "audio_mix_report.json", report)
        if not report.get("success"):
            issues = [
                {
                    "issueId": "AUDIO_002_TIMELINE",
                    "stage": "audio",
                    "errorType": "AudioTimelineError",
                    "rootCauseLabel": "audio_timeline_invalid",
                    "normalizedMessage": report.get("error") or "audio timeline compose failed",
                    "signature": "audio_timeline_invalid",
                    "confidence": 0.9,
                    "evidenceLines": [report.get("stderr") or ""],
                }
            ]
            return {
                "audio_mix_report": report,
                "current_issues": issues,
                "error_message": "Audio timeline compose failed",
            }

        return {
            "audio_mix_report": report,
            "final_audio_path": report.get("audio_path"),
        }

    def mux_audio_video(self, state: VideoGraphState) -> VideoGraphState:
        attempt_dir = self.task_repo.prepare_attempt(state["task_id"], state["attempt_no"])
        video_path = Path((state.get("last_render_report") or {}).get("video_path") or "")
        audio_path = Path(state.get("final_audio_path") or "")
        report = self.av_muxer.mux(video_path, audio_path, attempt_dir)
        write_json(attempt_dir / "mux_report.json", report)

        if not report.get("success"):
            issues = [
                {
                    "issueId": "DELIVERY_001_MUX",
                    "stage": "delivery",
                    "errorType": "MuxError",
                    "rootCauseLabel": "mux_failed",
                    "normalizedMessage": report.get("error") or "mux failed",
                    "signature": "mux_failed",
                    "confidence": 0.9,
                    "evidenceLines": [report.get("stderr") or ""],
                }
            ]
            return {
                "mux_report": report,
                "current_issues": issues,
                "error_message": "Audio video mux failed",
            }

        return {
            "mux_report": report,
            "final_video_path": report.get("output_path"),
        }

    def media_qc(self, state: VideoGraphState) -> VideoGraphState:
        attempt_dir = self.task_repo.prepare_attempt(state["task_id"], state["attempt_no"])
        qc_report = self.media_qc_checker.check(Path(state.get("final_video_path") or ""))
        write_json(attempt_dir / "qc_report.json", qc_report)

        if not qc_report.get("passed"):
            issues = [
                {
                    "issueId": "DELIVERY_002_QC",
                    "stage": "delivery",
                    "errorType": "MediaQCError",
                    "rootCauseLabel": qc_report.get("error") or "media_qc_failed",
                    "normalizedMessage": qc_report.get("reason") or "media qc failed",
                    "signature": qc_report.get("error") or "media_qc_failed",
                    "confidence": 0.9,
                    "evidenceLines": [qc_report.get("reason") or ""],
                }
            ]
            return {
                "qc_report": qc_report,
                "current_issues": issues,
                "error_message": qc_report.get("reason") or "Media QC failed",
            }

        return {"qc_report": qc_report}

    def upload_video(self, state: VideoGraphState) -> VideoGraphState:
        report = state["last_render_report"]
        object_key = self._build_oss_object_key(state["task_id"], RenderRequest(**state["request_payload"]).output_policy.file_base_name)
        final_video_path = state.get("final_video_path") or report.get("video_path")
        upload_result = self.oss_uploader.upload(Path(final_video_path), object_key)
        final = {
            "taskId": state["task_id"],
            "success": True,
            "status": "COMPLETED",
            "videoUrl": upload_result.get("url"),
            "ossObjectKey": upload_result.get("object_key"),
            "message": "Video rendered successfully",
            "attempts": state["attempt_no"],
            "taskDir": state["task_dir"],
        }
        self.task_repo.save_final_result(state["task_id"], final)
        self._save_task_state(
            state["task_id"],
            "COMPLETED",
            state["attempt_no"],
            state["max_attempts"],
            final_video_path=final_video_path,
            final_oss_url=upload_result.get("url"),
            latest_issue_ids=[issue["issueId"] for issue in state.get("current_issues", [])],
        )
        return {
            "status": "COMPLETED",
            "upload_result": upload_result,
            "final_result": final,
            "final_video_path": final_video_path,
        }

    def finalize_failure(self, state: VideoGraphState) -> VideoGraphState:
        message = _compose_failure_message(state)
        final = {
            "taskId": state["task_id"],
            "success": False,
            "status": "FAILED",
            "videoUrl": None,
            "ossObjectKey": None,
            "message": message,
            "attempts": state["attempt_no"],
            "taskDir": state["task_dir"],
        }
        self.task_repo.save_final_result(state["task_id"], final)
        self._save_task_state(
            state["task_id"],
            "FAILED",
            state["attempt_no"],
            state["max_attempts"],
            latest_issue_ids=[issue["issueId"] for issue in state.get("current_issues", [])],
        )
        return {"status": "FAILED", "final_result": final, "error_message": final["message"]}

    def _save_task_state(
        self,
        task_id: str,
        status: str,
        attempt_count: int,
        max_attempts: int,
        latest_issue_ids: list[str] | None = None,
        final_video_path: str | None = None,
        final_oss_url: str | None = None,
    ) -> None:
        task_state = TaskState(
            taskId=task_id,
            status=status,
            attemptCount=attempt_count,
            maxAttempts=max_attempts,
            latestIssueIds=latest_issue_ids or [],
            finalVideoPath=final_video_path,
            finalOssUrl=final_oss_url,
        )
        self.task_repo.save_task_state(task_state)

    def _build_oss_object_key(self, task_id: str, file_base_name: str) -> str:
        prefix = self.settings.oss_path_prefix.strip("/")
        return f"{prefix}/{task_id}/{file_base_name}.mp4"
