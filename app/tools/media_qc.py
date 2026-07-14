from __future__ import annotations

from pathlib import Path

from app.tools.ffprobe_reader import FFProbeReader


class MediaQC:
    def __init__(
        self,
        ffprobe_bin: str = "ffprobe",
        max_av_duration_diff_sec: float = 0.5,
        expected_resolution: str | None = None,
    ) -> None:
        self.ffprobe = FFProbeReader(ffprobe_bin)
        self.max_av_duration_diff_sec = max_av_duration_diff_sec
        self.expected_resolution = expected_resolution

    def check(self, final_video_path: Path, expected_resolution: str | None = None) -> dict:
        checks: list[dict] = []

        probe = self.ffprobe.probe(final_video_path)
        if not probe.get("available"):
            return {
                "passed": False,
                "error": "ffprobe_failed",
                "reason": probe.get("reason") or "ffprobe_failed",
                "probe": probe,
                "checks": checks,
            }

        payload = probe.get("payload") or {}
        streams = payload.get("streams") or []
        fmt = payload.get("format") or {}

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        # --- Hard-fail checks ---

        # Check 3: Video stream presence
        video_stream_ok = video_stream is not None
        checks.append({
            "name": "video_stream_present",
            "passed": video_stream_ok,
            "detail": "found" if video_stream_ok else "video stream not found",
        })

        # Audio stream presence
        audio_stream_ok = audio_stream is not None
        checks.append({
            "name": "audio_stream_present",
            "passed": audio_stream_ok,
            "detail": "found" if audio_stream_ok else "audio stream not found",
        })

        # Check 4: File size check (>= 10KB)
        try:
            file_size = final_video_path.stat().st_size
        except OSError:
            file_size = 0
        file_size_ok = file_size >= 10240
        checks.append({
            "name": "file_size",
            "passed": file_size_ok,
            "detail": f"{file_size} bytes",
        })

        # Check 1: Minimum video duration (>= 1s)
        video_duration = self._duration(video_stream) or self._safe_float(fmt.get("duration"))
        duration_ok = video_duration >= 1.0
        checks.append({
            "name": "duration_min",
            "passed": duration_ok,
            "detail": f"{video_duration}s",
        })

        # AV duration diff
        audio_duration = self._duration(audio_stream)
        duration_diff = abs(video_duration - audio_duration)
        av_diff_ok = duration_diff <= self.max_av_duration_diff_sec
        checks.append({
            "name": "av_duration_diff",
            "passed": av_diff_ok,
            "detail": f"diff={duration_diff:.3f}s",
        })

        # --- Warning checks ---

        # Check 2: Video resolution match
        effective_resolution = expected_resolution or self.expected_resolution
        if effective_resolution and video_stream:
            expected_w, expected_h = self._parse_resolution(effective_resolution)
            actual_w = int(video_stream.get("width") or 0)
            actual_h = int(video_stream.get("height") or 0)
            resolution_match = expected_w == actual_w and expected_h == actual_h
            checks.append({
                "name": "resolution_match",
                "passed": resolution_match,
                "detail": f"expected {expected_w}x{expected_h}, got {actual_w}x{actual_h}",
                "severity": "warning",
            })

        # Check 5: Frame rate check (10-120 fps)
        if video_stream:
            fps = self._parse_frame_rate(
                video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")
            )
            fps_ok = 10.0 <= fps <= 120.0
            checks.append({
                "name": "frame_rate",
                "passed": fps_ok,
                "detail": f"{fps}fps",
                "severity": "warning",
            })

        # Determine overall pass/fail (only hard-fail checks affect `passed`)
        hard_fail_checks = [c for c in checks if c.get("severity") != "warning"]
        all_hard_pass = all(c["passed"] for c in hard_fail_checks)

        error = None
        reason = None
        if not all_hard_pass:
            if not video_stream_ok:
                error = "output_missing_video_stream"
                reason = "video stream not found"
            elif not audio_stream_ok:
                error = "output_missing_audio_stream"
                reason = "audio stream not found"
            elif not file_size_ok:
                error = "video_file_too_small"
                reason = f"Video file too small: {file_size} bytes, possibly corrupted"
            elif not duration_ok:
                error = "video_duration_too_short"
                reason = f"Video duration too short: {video_duration}s"
            elif not av_diff_ok:
                error = "final_duration_mismatch"
                reason = f"duration diff {duration_diff:.3f}s exceeds {self.max_av_duration_diff_sec:.3f}s"

        return {
            "passed": all_hard_pass,
            "error": error,
            "reason": reason,
            "durationDiffSec": duration_diff,
            "videoDurationSec": video_duration,
            "audioDurationSec": audio_duration,
            "probe": probe,
            "checks": checks,
        }

    @staticmethod
    def _parse_resolution(resolution: str) -> tuple[int, int]:
        if "x" in resolution.lower():
            w, h = resolution.lower().split("x")
            return int(w), int(h)
        if "," in resolution:
            w, h = resolution.split(",")
            return int(w), int(h)
        return 1920, 1080

    @staticmethod
    def _parse_frame_rate(rate: str | None) -> float:
        if not rate or rate == "0/0":
            return 0.0
        try:
            if "/" in rate:
                num, den = rate.split("/")
                num_f = float(num)
                den_f = float(den)
                return num_f / den_f if den_f != 0 else 0.0
            return float(rate)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _duration(stream: dict | None) -> float:
        if not stream:
            return 0.0
        value = stream.get("duration")
        if value in (None, ""):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _safe_float(value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

