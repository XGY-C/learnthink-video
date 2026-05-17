from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from app.models.task import TaskState
from app.utils.file_utils import write_json, read_json


class TaskRepository:
    def __init__(self, runtime_root: Path) -> None:
        self.runtime_root = Path(runtime_root)
        self.runtime_root.mkdir(parents=True, exist_ok=True)

    def task_dir(self, task_id: str) -> Path:
        return self.runtime_root / task_id

    def attempts_dir(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "attempts"

    def final_dir(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "final"

    def learning_dir(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "learning"

    def init_task(self, task_id: str, max_attempts: int) -> TaskState:
        task_dir = self.task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        self.attempts_dir(task_id).mkdir(parents=True, exist_ok=True)
        self.final_dir(task_id).mkdir(parents=True, exist_ok=True)
        self.learning_dir(task_id).mkdir(parents=True, exist_ok=True)
        state = TaskState(taskId=task_id, status="RECEIVED", maxAttempts=max_attempts)
        self.save_task_state(state)
        return state

    def save_request_artifact(self, task_id: str, name: str, payload: Any) -> Path:
        path = self.task_dir(task_id) / name
        write_json(path, payload)
        return path

    def save_task_state(self, state: TaskState) -> None:
        write_json(self.task_dir(state.task_id) / "task_state.json", state.model_dump(by_alias=True))

    def load_task_state(self, task_id: str) -> dict[str, Any] | None:
        path = self.task_dir(task_id) / "task_state.json"
        if not path.exists():
            return None
        return read_json(path)

    def save_final_result(self, task_id: str, result: dict[str, Any]) -> None:
        write_json(self.final_dir(task_id) / "final_result.json", result)

    def load_final_result(self, task_id: str) -> dict[str, Any] | None:
        path = self.final_dir(task_id) / "final_result.json"
        if not path.exists():
            return None
        return read_json(path)

    def prepare_attempt(self, task_id: str, attempt_no: int) -> Path:
        path = self.attempts_dir(task_id) / f"{attempt_no:02d}"
        path.mkdir(parents=True, exist_ok=True)
        return path
