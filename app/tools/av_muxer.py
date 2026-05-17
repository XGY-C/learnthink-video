from __future__ import annotations

import subprocess
from pathlib import Path


class AVMuxer:
    def __init__(self, ffmpeg_bin: str = "ffmpeg") -> None:
        self.ffmpeg_bin = ffmpeg_bin

    def mux(self, silent_video_path: Path, audio_path: Path, attempt_dir: Path, output_name: str = "final_with_audio.mp4") -> dict:
        output_path = attempt_dir / output_name
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(silent_video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError as exc:
            return {
                "success": False,
                "error": "mux_failed",
                "output_path": None,
                "stderr": f"FileNotFoundError: {exc}",
                "command": cmd,
            }

        return {
            "success": result.returncode == 0 and output_path.exists(),
            "error": None if result.returncode == 0 else "mux_failed",
            "output_path": str(output_path) if output_path.exists() else None,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": cmd,
        }

