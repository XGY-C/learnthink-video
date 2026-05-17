from __future__ import annotations

from pathlib import Path


class PromptLoader:
    def __init__(self, prompt_root: Path) -> None:
        self.prompt_root = Path(prompt_root)

    def load_text(self, relative_path: str) -> str:
        path = self.prompt_root / relative_path
        return path.read_text(encoding="utf-8")

    def load_agent_prompt(self, name: str) -> str:
        return self.load_text(f"system/{name}.md")

    def load_shared(self, name: str) -> str:
        return self.load_text(f"shared/{name}.md")
