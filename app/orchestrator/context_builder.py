from __future__ import annotations

from app.storage.notice_repo import NoticeRepository


class ContextBuilder:
    def __init__(self, notice_repo: NoticeRepository) -> None:
        self.notice_repo = notice_repo

    def build_notices_context(self) -> list[dict]:
        return self.notice_repo.load()
