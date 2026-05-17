from fastapi import APIRouter, HTTPException
from app.models.contracts import RenderRequest, RenderResponse, TaskEnvelope
from app.services.render_service import RenderService
from app.storage.task_repo import TaskRepository
from app.core.config import get_settings

router = APIRouter(prefix="/v1/video", tags=["video"])
settings = get_settings()
task_repo = TaskRepository(settings.runtime_root)
render_service = RenderService(settings=settings, task_repo=task_repo)


@router.post("/render", response_model=RenderResponse)
def render_video(request: RenderRequest) -> RenderResponse:
    return render_service.render(request)


@router.get("/tasks/{task_id}", response_model=TaskEnvelope)
def get_task(task_id: str) -> TaskEnvelope:
    task = task_repo.load_task_state(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    result = task_repo.load_final_result(task_id)
    return TaskEnvelope(task=task, result=result)
