from __future__ import annotations

from app.core.config import Settings
from app.graph.builder import build_video_graph
from app.graph.nodes import GraphNodes
from app.models.contracts import RenderRequest
from app.storage.task_repo import TaskRepository


class LangGraphRunner:
    def __init__(self, settings: Settings, task_repo: TaskRepository) -> None:
        self.settings = settings
        self.nodes = GraphNodes(settings=settings, task_repo=task_repo)
        self.graph = build_video_graph(self.nodes)

    def invoke(self, task_id: str, request: RenderRequest) -> dict:
        max_attempts = max(1, min(request.render_policy.max_repair_rounds, self.settings.max_attempts))
        recursion_limit = max(25, 12 + max_attempts * 6)
        final_state = self.graph.invoke(
            {
                "task_id": task_id,
                "request_payload": request.model_dump(by_alias=True),
            },
            config={"recursion_limit": recursion_limit},
        )
        return final_state["final_result"]
