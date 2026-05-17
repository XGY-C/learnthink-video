from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class FFProbeReader:
    def __init__(self, ffprobe_bin: str = "ffprobe") -> None:
        self.ffprobe_bin = ffprobe_bin

    def probe(self, video_path: Path) -> dict:
        if not shutil.which(self.ffprobe_bin):
            return {"available": False, "reason": "ffprobe not found"}
        cmd = [
            self.ffprobe_bin,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return {"available": False, "reason": result.stderr.strip()}
        payload = json.loads(result.stdout)
        return {"available": True, "payload": payload}
