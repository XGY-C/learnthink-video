from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from filelock import FileLock


class RenderCache:
    """Content-addressable render cache.

    Cache key = SHA256(scene_ir normalized JSON + sorted audio asset tuples).
    Avoids re-rendering when the same scene plan and audio inputs are submitted.
    """

    def __init__(self, cache_root: Path) -> None:
        self.cache_dir = Path(cache_root)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "cache_index.json"
        self.lock = FileLock(str(self.cache_dir / "cache_index.lock"))
        if not self.index_file.exists():
            self.index_file.write_text("{}", encoding="utf-8")

    @staticmethod
    def compute_key(scene_ir: dict[str, Any], audio_assets: list[dict[str, Any]]) -> str:
        digest = hashlib.sha256()
        digest.update(
            json.dumps(scene_ir, ensure_ascii=False, sort_keys=True).encode("utf-8")
        )
        tuples = sorted(
            (a.get("audioUrl", ""), str(a.get("durationSec", 0)))
            for a in audio_assets
        )
        for url, dur in tuples:
            digest.update(url.encode("utf-8"))
            digest.update(dur.encode("utf-8"))
        return digest.hexdigest()

    def get(self, cache_key: str) -> Path | None:
        with self.lock:
            data: dict = json.loads(self.index_file.read_text(encoding="utf-8"))
            value = data.get(cache_key)
            if not value:
                return None
            path = Path(value)
            if path.exists():
                return path
            return None

    def put(self, cache_key: str, file_path: Path) -> None:
        cache_target = self.cache_dir / f"{cache_key}.mp4"
        shutil.copy2(file_path, cache_target)
        with self.lock:
            data: dict = json.loads(self.index_file.read_text(encoding="utf-8"))
            data[cache_key] = str(cache_target)
            self.index_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
