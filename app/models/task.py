from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskState(BaseModel):
    task_id: str = Field(alias="taskId")
    status: str
    created_at: str = Field(default_factory=utc_now, alias="createdAt")
    updated_at: str = Field(default_factory=utc_now, alias="updatedAt")
    attempt_count: int = Field(default=0, alias="attemptCount")
    max_attempts: int = Field(default=6, alias="maxAttempts")
    latest_issue_ids: list[str] = Field(default_factory=list, alias="latestIssueIds")
    final_video_path: str | None = Field(default=None, alias="finalVideoPath")
    final_oss_url: str | None = Field(default=None, alias="finalOssUrl")


class AttemptSummary(BaseModel):
    attempt_no: int = Field(alias="attemptNo")
    status: str
    code_path: str = Field(alias="codePath")
    stdout_path: str = Field(alias="stdoutPath")
    stderr_path: str = Field(alias="stderrPath")
    render_report_path: str = Field(alias="renderReportPath")
