from __future__ import annotations

import logging
import threading
import uuid
from app.core.config import Settings
from app.graph.runner import LangGraphRunner
from app.models.contracts import RenderRequest, RenderResponse
from app.storage.task_repo import TaskRepository


logger = logging.getLogger(__name__)


class RenderService:
    def __init__(self, settings: Settings, task_repo: TaskRepository) -> None:
        self.settings = settings
        self.task_repo = task_repo
        self._runner: LangGraphRunner | None = None

    @property
    def runner(self) -> LangGraphRunner:
        if self._runner is None:
            self._runner = LangGraphRunner(settings=self.settings, task_repo=self.task_repo)
        return self._runner

    def render(self, request: RenderRequest) -> RenderResponse:
        task_id = request.request_id or str(uuid.uuid4())
        max_attempts = max(1, min(request.render_policy.max_repair_rounds, self.settings.max_attempts))
        logger.info("[api] render request accepted task=%s scenes=%s maxAttempts=%s",
                     task_id, len(request.timed_scenes), max_attempts)

        self.task_repo.init_task(task_id, max_attempts)
        self.task_repo.save_request_artifact(task_id, "request.json", request.model_dump(by_alias=True))

        thread = threading.Thread(target=self._run_render, args=(task_id, request), daemon=True)
        thread.start()

        return RenderResponse(
            taskId=task_id,
            success=True,
            status="RECEIVED",
            videoUrl=None,
            ossObjectKey=None,
            message="Task accepted",
            attempts=0,
            taskDir=str(self.task_repo.task_dir(task_id)),
        )

    def _run_render(self, task_id: str, request: RenderRequest) -> None:
        logger.info("[render] background task started task=%s", task_id)
        try:
            result = self.runner.invoke(task_id=task_id, request=request)
            logger.info(
                "[render] background task finished task=%s success=%s status=%s attempts=%s",
                task_id,
                result.get("success"),
                result.get("status"),
                result.get("attempts"),
            )
        except Exception as exc:
            logger.error("[render] background task failed task=%s error=%s", task_id, exc)
            self.task_repo.save_final_result(task_id, {
                "taskId": task_id,
                "success": False,
                "status": "FAILED",
                "videoUrl": None,
                "ossObjectKey": None,
                "message": str(exc),
                "attempts": 0,
                "taskDir": str(self.task_repo.task_dir(task_id)),
            })
