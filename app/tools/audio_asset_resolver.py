from __future__ import annotations

import logging
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.tools.ffprobe_reader import FFProbeReader
from app.utils.hash_utils import sha1_text


logger = logging.getLogger(__name__)


class AudioAssetResolver:
    def __init__(self, cache_root: Path, ffprobe_bin: str, timeout_sec: float = 60.0) -> None:
        self.cache_root = Path(cache_root)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.ffprobe = FFProbeReader(ffprobe_bin)
        self.timeout_sec = timeout_sec

    def resolve(self, task_id: str, timed_scenes: list[dict]) -> dict:
        assets: list[dict] = []
        for idx, scene in enumerate(timed_scenes, start=1):
            scene_id = scene.get("sceneId") or f"SCENE_{idx:03d}"
            audio_url = scene.get("audioUrl")
            if not audio_url:
                assets.append({
                    "sceneId": scene_id,
                    "audioUrl": None,
                    "status": "missing",
                    "path": None,
                    "durationSec": 0.0,
                    "error": "audio_url_missing",
                })
                continue

            local_path, err = self._fetch_audio(task_id, audio_url)
            if err:
                assets.append({
                    "sceneId": scene_id,
                    "audioUrl": audio_url,
                    "status": "failed",
                    "path": None,
                    "durationSec": 0.0,
                    "error": err,
                })
                continue

            probe = self.ffprobe.probe(local_path)
            duration_sec = self._read_duration(probe)
            assets.append({
                "sceneId": scene_id,
                "audioUrl": audio_url,
                "status": "ready",
                "path": str(local_path),
                "durationSec": duration_sec,
                "probe": probe,
            })

        success = all(asset["status"] in {"ready", "missing"} for asset in assets)
        return {"success": success, "assets": assets}

    def resolve_single(self, task_id: str, audio_url: str | None, label: str = "BGM") -> dict:
        if not audio_url:
            return {
                "label": label,
                "audioUrl": None,
                "status": "missing",
                "path": None,
                "durationSec": 0.0,
                "error": "audio_url_missing",
            }

        local_path, err = self._fetch_audio(task_id, audio_url)
        if err:
            return {
                "label": label,
                "audioUrl": audio_url,
                "status": "failed",
                "path": None,
                "durationSec": 0.0,
                "error": err,
            }

        probe = self.ffprobe.probe(local_path)
        return {
            "label": label,
            "audioUrl": audio_url,
            "status": "ready",
            "path": str(local_path),
            "durationSec": self._read_duration(probe),
            "probe": probe,
        }

    def _fetch_audio(self, task_id: str, audio_url: str) -> tuple[Path, str | None]:
        if audio_url.startswith(("http://", "https://")):
            return self._download_remote(task_id, audio_url)

        local_src = Path(audio_url)
        if not local_src.exists():
            logger.warning("[audio] task=%s source=local status=missing path=%s", task_id, audio_url)
            return self.cache_root / "missing", "audio_download_failed"

        suffix = local_src.suffix or ".wav"
        key = sha1_text(f"{task_id}:{audio_url}")[:16]
        target = self.cache_root / task_id / f"{key}{suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(local_src.read_bytes())
        logger.info(
            "[audio] task=%s source=local status=ready src=%s target=%s sizeBytes=%s",
            task_id,
            local_src,
            target,
            target.stat().st_size,
        )
        return target, None

    def _download_remote(self, task_id: str, audio_url: str) -> tuple[Path, str | None]:
        suffix = Path(audio_url).suffix or ".wav"
        key = sha1_text(f"{task_id}:{audio_url}")[:16]
        target = self.cache_root / task_id / f"{key}{suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        host = urlparse(audio_url).netloc or "unknown"
        start = time.perf_counter()
        logger.info("[audio] task=%s source=remote status=start host=%s target=%s", task_id, host, target)

        try:
            with httpx.Client(timeout=self.timeout_sec, follow_redirects=True) as client:
                resp = client.get(audio_url)
                resp.raise_for_status()
                target.write_bytes(resp.content)
        except Exception:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.exception(
                "[audio] task=%s source=remote status=failed host=%s target=%s elapsedMs=%s",
                task_id,
                host,
                target,
                elapsed_ms,
            )
            return target, "audio_download_failed"

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "[audio] task=%s source=remote status=ready host=%s target=%s sizeBytes=%s elapsedMs=%s",
            task_id,
            host,
            target,
            target.stat().st_size,
            elapsed_ms,
        )

        return target, None

    @staticmethod
    def _read_duration(probe: dict) -> float:
        if not probe.get("available"):
            return 0.0
        payload = probe.get("payload") or {}
        fmt = payload.get("format") or {}
        try:
            return float(fmt.get("duration") or 0.0)
        except (TypeError, ValueError):
            return 0.0

