from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from app.agents.planner import RequestPlanner
from app.agents.code_expert import ManimCodeExpert
from app.agents.diagnoser import ErrorDiagnoser
from app.agents.repair import RepairAgent
from app.agents.validator import FixValidator
from app.core.config import Settings
from app.llm.factory import build_llm_client
from app.models.contracts import RenderRequest
from app.models.task import TaskState
from app.storage.notice_repo import NoticeRepository
from app.storage.task_repo import TaskRepository
from app.tools.prompt_loader import PromptLoader
from app.tools.render_executor import RenderExecutor
from app.tools.oss_uploader import OSSUploader
from app.utils.file_utils import write_json, write_text

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, settings: Settings, task_repo: TaskRepository) -> None:
        self.settings = settings
        self.task_repo = task_repo
        self.notice_repo = NoticeRepository(settings.prompt_root)
        self.prompt_loader = PromptLoader(settings.prompt_root)
        llm_client = build_llm_client(settings)

        self.planner = RequestPlanner()
        self.code_expert = ManimCodeExpert()
        self.diagnoser = ErrorDiagnoser(llm_client=llm_client, enable_llm_fallback=settings.enable_llm_assist)
        self.repair_agent = RepairAgent()
        self.validator = FixValidator()
        self.render_executor = RenderExecutor(settings.manim_bin, settings.ffprobe_bin)
        self.oss_uploader = OSSUploader(settings)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _update_task_state(self, state: TaskState, **updates) -> TaskState:
        data = state.model_dump(by_alias=True)
        data.update(updates)
        data["updatedAt"] = self._utc_now()
        new_state = TaskState(**data)
        self.task_repo.save_task_state(new_state)
        return new_state

    def run(self, task_id: str, request: RenderRequest) -> dict:
        state = self.task_repo.init_task(task_id=task_id, max_attempts=min(request.render_policy.max_repair_rounds, self.settings.max_attempts))
        self.task_repo.save_request_artifact(task_id, "request.json", request.model_dump(by_alias=True))

        state = self._update_task_state(state, status="PLANNED")
        plan_result = self.planner.run(request)
        self.task_repo.save_request_artifact(task_id, "normalized_request.json", plan_result["normalizedRequest"])
        self.task_repo.save_request_artifact(task_id, "scene_ir.json", plan_result["sceneIR"])
        self.task_repo.save_request_artifact(task_id, "risk_report.json", plan_result["riskReport"])

        state = self._update_task_state(state, status="CODE_GENERATED")
        current_code = self.code_expert.run(plan_result["sceneIR"])

        previous_issues: list[dict] = []
        notices = self.notice_repo.load()

        for attempt_no in range(1, state.max_attempts + 1):
            attempt_dir = self.task_repo.prepare_attempt(task_id, attempt_no)
            code_file = attempt_dir / "generated.py"
            write_text(code_file, current_code)

            state = self._update_task_state(state, status="RENDERING", attemptCount=attempt_no)
            render_report = self.render_executor.run(request=request, code_file=code_file, attempt_dir=attempt_dir)

            if render_report["success"]:
                state = self._update_task_state(
                    state,
                    status="RENDER_SUCCEEDED",
                    finalVideoPath=render_report["video_path"],
                )

                object_key = self._build_oss_object_key(task_id, request.output_policy.file_base_name)
                state = self._update_task_state(state, status="UPLOADING_OSS")
                upload_result = self.oss_uploader.upload(Path(render_report["video_path"]), object_key)

                final_result = {
                    "taskId": task_id,
                    "success": True,
                    "status": "COMPLETED",
                    "videoUrl": upload_result.get("url"),
                    "ossObjectKey": upload_result.get("object_key"),
                    "message": "Video rendered successfully",
                    "attempts": attempt_no,
                    "taskDir": str(self.task_repo.task_dir(task_id)),
                }
                self.task_repo.save_final_result(task_id, final_result)
                self._update_task_state(state, status="COMPLETED", finalOssUrl=upload_result.get("url"))
                return final_result

            state = self._update_task_state(state, status="RENDER_FAILED")

            issue_payload = self.diagnoser.run(render_report)
            write_json(attempt_dir / "issues.json", issue_payload)
            current_issues = issue_payload["issues"]
            latest_issue_ids = [issue["issueId"] for issue in current_issues]
            state = self._update_task_state(state, latestIssueIds=latest_issue_ids)

            state = self._update_task_state(state, status="REPAIRING")
            repair_result = self.repair_agent.run(
                code=current_code,
                issues=current_issues,
                attempt_no=attempt_no,
                notices=notices,
            )
            current_code = repair_result["code"]
            write_json(attempt_dir / "repair_decision.json", repair_result["metadata"])

            state = self._update_task_state(state, status="VALIDATING_FIX")
            if previous_issues:
                validation = self.validator.run(
                    target_issues=previous_issues,
                    new_issues=current_issues,
                    introduced_earlier_blocker=False,
                )
                write_json(attempt_dir / "validation.json", validation)
                if validation["shouldLearn"] and validation.get("candidateNotice") and previous_issues:
                    self.notice_repo.append_validated_notice(
                        issue_type=previous_issues[0]["rootCauseLabel"],
                        rule=validation["candidateNotice"],
                    )

            previous_issues = current_issues

        final_result = {
            "taskId": task_id,
            "success": False,
            "status": "FAILED",
            "videoUrl": None,
            "ossObjectKey": None,
            "message": "Render failed after max attempts",
            "attempts": state.max_attempts,
            "taskDir": str(self.task_repo.task_dir(task_id)),
        }
        self.task_repo.save_final_result(task_id, final_result)
        self._update_task_state(state, status="FAILED")
        return final_result

    def _build_oss_object_key(self, task_id: str, file_base_name: str) -> str:
        prefix = self.settings.oss_path_prefix.strip("/")
        return f"{prefix}/{task_id}/{file_base_name}.mp4"
