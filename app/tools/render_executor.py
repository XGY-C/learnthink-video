from __future__ import annotations

import logging
import shutil
import subprocess
import time
from pathlib import Path
from app.models.contracts import RenderRequest
from app.tools.ffprobe_reader import FFProbeReader
from app.utils.file_utils import write_text, write_json


logger = logging.getLogger(__name__)


class RenderExecutor:
    def __init__(self, manim_bin: str, ffprobe_bin: str) -> None:
        self.manim_bin = manim_bin
        self.ffprobe = FFProbeReader(ffprobe_bin)

    @staticmethod
    def _parse_resolution(resolution: str) -> tuple[int, int]:
        if "x" in resolution.lower():
            w, h = resolution.lower().split("x")
            return int(w), int(h)
        if "," in resolution:
            w, h = resolution.split(",")
            return int(w), int(h)
        return 1920, 1080

    def run(
        self,
        request: RenderRequest,
        code_file: Path,
        attempt_dir: Path,
    ) -> dict:
        stdout_path = attempt_dir / "stdout.log"
        stderr_path = attempt_dir / "stderr.log"

        width, height = self._parse_resolution(request.project_brief.video_spec.resolution)
        output_name = request.output_policy.file_base_name
        media_dir = attempt_dir / "media"
        log_dir = attempt_dir / "logs"
        media_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)

        timeout = request.render_policy.timeout_sec
        scene_name = request.output_policy.scene_class_name

        manim_path = shutil.which(self.manim_bin) or self.manim_bin

        cmd = [
            manim_path,
            "render",
            str(code_file),
            scene_name,
            "-o", output_name,
            "--media_dir", str(media_dir),
            "--log_dir", str(log_dir),
            "-r", f"{width},{height}",
            "--fps", str(request.project_brief.video_spec.fps),
            "--progress_bar", "none",
            "--renderer", request.render_policy.renderer,
        ]
        start = time.perf_counter()
        logger.info(
            "[render] status=start scene=%s resolution=%sx%s fps=%s attemptDir=%s",
            scene_name,
            width,
            height,
            request.project_brief.video_spec.fps,
            attempt_dir,
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode
        except FileNotFoundError as exc:
            stdout = ""
            stderr = f"FileNotFoundError: {exc}"
            exit_code = 127
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + "\nTimeoutExpired: render command exceeded timeout"
            exit_code = 124

        write_text(stdout_path, stdout)
        write_text(stderr_path, stderr)

        video_path = self._find_video_path(media_dir, output_name)
        exists = video_path is not None and video_path.exists()
        size_bytes = video_path.stat().st_size if exists else 0
        ffprobe = self.ffprobe.probe(video_path) if exists else {"available": False, "reason": "video not found"}

        success = exit_code == 0 and exists and size_bytes > 1024
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "[render] status=done scene=%s success=%s exitCode=%s videoExists=%s sizeBytes=%s elapsedMs=%s",
            scene_name,
            success,
            exit_code,
            exists,
            size_bytes,
            elapsed_ms,
        )

        report = {
            "success": success,
            "exit_code": exit_code,
            "command": cmd,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "media_dir": str(media_dir),
            "video_path": str(video_path) if video_path else None,
            "video_exists": exists,
            "video_size_bytes": size_bytes,
            "ffprobe": ffprobe,
        }
        write_json(attempt_dir / "render_report.json", report)
        return report

    @staticmethod
    def _find_video_path(media_dir: Path, output_name: str) -> Path | None:
        candidates = list(media_dir.rglob(f"{output_name}.mp4"))
        if candidates:
            return candidates[0]
        all_mp4 = list(media_dir.rglob("*.mp4"))
        return all_mp4[0] if all_mp4 else None
