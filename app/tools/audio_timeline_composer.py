from __future__ import annotations

import subprocess
from pathlib import Path


class AudioTimelineComposer:
    def __init__(self, ffmpeg_bin: str = "ffmpeg", target_sample_rate: int = 44100) -> None:
        self.ffmpeg_bin = ffmpeg_bin
        self.target_sample_rate = target_sample_rate

    def compose(
        self,
        audio_assets: list[dict],
        attempt_dir: Path,
        audio_policy: dict | None = None,
        bgm_policy: dict | None = None,
        bgm_asset: dict | None = None,
    ) -> dict:
        # Normalize attempt dir once so generated artifacts and concat paths are stable.
        attempt_dir = attempt_dir.resolve()
        policy = audio_policy or {}
        bgm = bgm_policy or {}
        target_sample_rate = int(policy.get("targetSampleRate", self.target_sample_rate))
        insert_silence_ms = int(policy.get("insertSilenceBetweenScenesMs", 0))
        normalize_volume = bool(policy.get("normalizeVolume", False))
        bgm_enabled = bool(bgm.get("enabled", False))
        bgm_ducking = bool(bgm.get("ducking", True))
        bgm_volume = float(bgm.get("volume", 0.15))

        ready_files = [
            self._to_abs_path(Path(asset["path"]))
            for asset in audio_assets
            if asset.get("status") == "ready" and asset.get("path")
        ]
        output_path = attempt_dir / "mixed_audio.m4a"
        primary_audio_path = attempt_dir / "mixed_audio_primary.m4a" if bgm_enabled else output_path

        if not ready_files:
            return {
                "success": False,
                "error": "audio_timeline_invalid",
                "audio_path": None,
                "input_count": 0,
                "effective_policy": {
                    "targetSampleRate": target_sample_rate,
                    "insertSilenceBetweenScenesMs": insert_silence_ms,
                    "normalizeVolume": normalize_volume,
                },
                "effective_bgm_policy": {
                    "enabled": bgm_enabled,
                    "ducking": bgm_ducking,
                    "volume": bgm_volume,
                },
            }

        if len(ready_files) == 1 and insert_silence_ms <= 0 and not normalize_volume and not bgm_enabled:
            primary_audio_path.write_bytes(ready_files[0].read_bytes())
            return {
                "success": True,
                "audio_path": str(primary_audio_path),
                "input_count": 1,
                "mode": "copy_single",
                "bgm_applied": False,
                "effective_policy": {
                    "targetSampleRate": target_sample_rate,
                    "insertSilenceBetweenScenesMs": insert_silence_ms,
                    "normalizeVolume": normalize_volume,
                },
                "effective_bgm_policy": {
                    "enabled": bgm_enabled,
                    "ducking": bgm_ducking,
                    "volume": bgm_volume,
                },
            }

        list_inputs = self._inject_silence(ready_files, attempt_dir, insert_silence_ms, target_sample_rate)
        if list_inputs is None:
            return {
                "success": False,
                "error": "audio_timeline_invalid",
                "audio_path": None,
                "stderr": "failed to generate silence segment",
                "input_count": len(ready_files),
                "effective_policy": {
                    "targetSampleRate": target_sample_rate,
                    "insertSilenceBetweenScenesMs": insert_silence_ms,
                    "normalizeVolume": normalize_volume,
                },
                "effective_bgm_policy": {
                    "enabled": bgm_enabled,
                    "ducking": bgm_ducking,
                    "volume": bgm_volume,
                },
            }

        list_file = attempt_dir / "audio_list.txt"
        escaped_files = ["file '{}'".format(str(self._to_abs_path(path)).replace("'", "''")) for path in list_inputs]
        list_file.write_text("\n".join(escaped_files), encoding="utf-8")

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
        ]

        if normalize_volume:
            cmd.extend(["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"])

        cmd.extend([
            "-ar",
            str(target_sample_rate),
            "-ac",
            "2",
            "-c:a",
            "aac",
            str(primary_audio_path),
        ])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError as exc:
            return {
                "success": False,
                "error": "audio_timeline_invalid",
                "audio_path": None,
                "stderr": f"FileNotFoundError: {exc}",
                "command": cmd,
            }

        base_success = result.returncode == 0 and primary_audio_path.exists()
        if not base_success:
            return {
                "success": False,
                "error": "audio_timeline_invalid",
                "audio_path": None,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": cmd,
                "input_count": len(ready_files),
                "segments": len(list_inputs),
                "mode": "concat",
                "effective_policy": {
                    "targetSampleRate": target_sample_rate,
                    "insertSilenceBetweenScenesMs": insert_silence_ms,
                    "normalizeVolume": normalize_volume,
                },
                "effective_bgm_policy": {
                    "enabled": bgm_enabled,
                    "ducking": bgm_ducking,
                    "volume": bgm_volume,
                },
            }

        bgm_result = self._apply_bgm(
            primary_audio_path=primary_audio_path,
            output_path=output_path,
            target_sample_rate=target_sample_rate,
            bgm_enabled=bgm_enabled,
            bgm_ducking=bgm_ducking,
            bgm_volume=bgm_volume,
            bgm_asset=bgm_asset,
        )

        return {
            "success": bgm_result["success"],
            "error": None if bgm_result["success"] else "audio_timeline_invalid",
            "audio_path": bgm_result.get("audio_path"),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": cmd,
            "input_count": len(ready_files),
            "segments": len(list_inputs),
            "mode": "concat",
            "bgm_applied": bgm_result.get("bgm_applied", False),
            "bgm_fallback_reason": bgm_result.get("bgm_fallback_reason"),
            "bgm_command": bgm_result.get("bgm_command"),
            "effective_policy": {
                "targetSampleRate": target_sample_rate,
                "insertSilenceBetweenScenesMs": insert_silence_ms,
                "normalizeVolume": normalize_volume,
            },
            "effective_bgm_policy": {
                "enabled": bgm_enabled,
                "ducking": bgm_ducking,
                "volume": bgm_volume,
            },
        }

    def _apply_bgm(
        self,
        primary_audio_path: Path,
        output_path: Path,
        target_sample_rate: int,
        bgm_enabled: bool,
        bgm_ducking: bool,
        bgm_volume: float,
        bgm_asset: dict | None,
    ) -> dict:
        if not bgm_enabled:
            if primary_audio_path != output_path:
                output_path.write_bytes(primary_audio_path.read_bytes())
            return {"success": True, "audio_path": str(output_path), "bgm_applied": False}

        bgm_path = Path((bgm_asset or {}).get("path") or "")
        if (bgm_asset or {}).get("status") != "ready" or not bgm_path.exists():
            if primary_audio_path != output_path:
                output_path.write_bytes(primary_audio_path.read_bytes())
            return {
                "success": True,
                "audio_path": str(output_path),
                "bgm_applied": False,
                "bgm_fallback_reason": "bgm_unavailable",
            }

        if bgm_ducking:
            filter_complex = (
                f"[1:a]volume={bgm_volume}[bgm];"
                "[bgm][0:a]sidechaincompress=threshold=0.04:ratio=8[ducked];"
                "[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=2[mix]"
            )
        else:
            filter_complex = f"[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[mix]"

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(primary_audio_path),
            "-i",
            str(bgm_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[mix]",
            "-ar",
            str(target_sample_rate),
            "-ac",
            "2",
            "-c:a",
            "aac",
            str(output_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            output_path.write_bytes(primary_audio_path.read_bytes())
            return {
                "success": True,
                "audio_path": str(output_path),
                "bgm_applied": False,
                "bgm_fallback_reason": "ffmpeg_not_found_for_bgm",
                "bgm_command": cmd,
            }

        if result.returncode != 0 or not output_path.exists():
            output_path.write_bytes(primary_audio_path.read_bytes())
            return {
                "success": True,
                "audio_path": str(output_path),
                "bgm_applied": False,
                "bgm_fallback_reason": "bgm_mix_failed",
                "bgm_command": cmd,
            }

        return {"success": True, "audio_path": str(output_path), "bgm_applied": True, "bgm_command": cmd}

    def _inject_silence(
        self,
        ready_files: list[Path],
        attempt_dir: Path,
        insert_silence_ms: int,
        target_sample_rate: int,
    ) -> list[Path] | None:
        if insert_silence_ms <= 0 or len(ready_files) <= 1:
            return ready_files

        silence_path = attempt_dir / f"silence_{insert_silence_ms}ms.m4a"
        silence_duration = max(insert_silence_ms / 1000.0, 0.01)
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r={target_sample_rate}:cl=stereo",
            "-t",
            f"{silence_duration:.3f}",
            "-c:a",
            "aac",
            str(silence_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return None
        if result.returncode != 0 or not silence_path.exists():
            return None

        merged: list[Path] = []
        for idx, path in enumerate(ready_files):
            if idx > 0:
                merged.append(silence_path)
            merged.append(path)
        return merged

    @staticmethod
    def _to_abs_path(path: Path) -> Path:
        if path.is_absolute():
            return path
        return (Path.cwd() / path).resolve()

