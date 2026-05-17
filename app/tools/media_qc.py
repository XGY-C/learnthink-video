from __future__ import annotations

from pathlib import Path

from app.tools.ffprobe_reader import FFProbeReader


class MediaQC:
    def __init__(self, ffprobe_bin: str = "ffprobe", max_av_duration_diff_sec: float = 0.5) -> None:
        self.ffprobe = FFProbeReader(ffprobe_bin)
        self.max_av_duration_diff_sec = max_av_duration_diff_sec

    def check(self, final_video_path: Path) -> dict:
        probe = self.ffprobe.probe(final_video_path)
        if not probe.get("available"):
            return {
                "passed": False,
                "error": "output_missing_audio_stream",
                "reason": probe.get("reason") or "ffprobe_failed",
                "probe": probe,
            }

        payload = probe.get("payload") or {}
        streams = payload.get("streams") or []
        fmt = payload.get("format") or {}

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if not audio_stream:
            return {
                "passed": False,
                "error": "output_missing_audio_stream",
                "reason": "audio stream not found",
                "probe": probe,
            }

        video_duration = self._duration(video_stream) or self._safe_float(fmt.get("duration"))
        audio_duration = self._duration(audio_stream)
        duration_diff = abs(video_duration - audio_duration)

        if duration_diff > self.max_av_duration_diff_sec:
            return {
                "passed": False,
                "error": "final_duration_mismatch",
                "reason": f"duration diff {duration_diff:.3f}s exceeds {self.max_av_duration_diff_sec:.3f}s",
                "durationDiffSec": duration_diff,
                "videoDurationSec": video_duration,
                "audioDurationSec": audio_duration,
                "probe": probe,
            }

        return {
            "passed": True,
            "error": None,
            "durationDiffSec": duration_diff,
            "videoDurationSec": video_duration,
            "audioDurationSec": audio_duration,
            "probe": probe,
        }

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

