from __future__ import annotations

import logging
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
        logger.info("[api] render request received task=%s scenes=%s", task_id, len(request.timed_scenes))
        try:
            result = self.runner.invoke(task_id=task_id, request=request)
        except RuntimeError as exc:
            result = {
                "taskId": task_id,
                "success": False,
                "status": "FAILED",
                "videoUrl": None,
                "ossObjectKey": None,
                "message": str(exc),
                "attempts": 0,
                "taskDir": None,
            }
        logger.info(
            "[api] render request finished task=%s success=%s status=%s attempts=%s",
            task_id,
            result.get("success"),
            result.get("status"),
            result.get("attempts"),
        )
        return RenderResponse(**result)
