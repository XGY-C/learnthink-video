from pathlib import Path

from app.tools.audio_timeline_composer import AudioTimelineComposer


def test_compose_single_audio_copy(tmp_path: Path):
    src = tmp_path / "a.wav"
    src.write_bytes(b"fake-audio")
    composer = AudioTimelineComposer(ffmpeg_bin="ffmpeg")

    report = composer.compose(
        audio_assets=[{"status": "ready", "path": str(src)}],
        attempt_dir=tmp_path,
    )

    assert report["success"] is True
    assert report["mode"] == "copy_single"
    assert Path(report["audio_path"]).exists()


def test_compose_empty_assets(tmp_path: Path):
    composer = AudioTimelineComposer(ffmpeg_bin="ffmpeg")
    report = composer.compose(audio_assets=[], attempt_dir=tmp_path)
    assert report["success"] is False
    assert report["error"] == "audio_timeline_invalid"


def test_compose_honors_audio_policy_for_concat(tmp_path: Path, monkeypatch):
    a = tmp_path / "a.wav"
    b = tmp_path / "b.wav"
    a.write_bytes(b"a")
    b.write_bytes(b"b")

    captured_cmds: list[list[str]] = []

    class _Result:
        def __init__(self, returncode: int = 0):
            self.returncode = returncode
            self.stdout = ""
            self.stderr = ""

    def _fake_run(cmd, capture_output, text, check):
        captured_cmds.append(cmd)
        Path(cmd[-1]).write_bytes(b"ok")
        return _Result(0)

    monkeypatch.setattr("app.tools.audio_timeline_composer.subprocess.run", _fake_run)

    composer = AudioTimelineComposer(ffmpeg_bin="ffmpeg")
    report = composer.compose(
        audio_assets=[
            {"status": "ready", "path": str(a)},
            {"status": "ready", "path": str(b)},
        ],
        attempt_dir=tmp_path,
        audio_policy={
            "targetSampleRate": 48000,
            "insertSilenceBetweenScenesMs": 200,
            "normalizeVolume": True,
        },
    )

    assert report["success"] is True
    assert report["effective_policy"]["targetSampleRate"] == 48000
    assert report["effective_policy"]["insertSilenceBetweenScenesMs"] == 200
    assert report["effective_policy"]["normalizeVolume"] is True

    concat_cmd = captured_cmds[-1]
    assert "-af" in concat_cmd
    assert "loudnorm=I=-16:TP=-1.5:LRA=11" in concat_cmd
    assert "-ar" in concat_cmd
    assert "48000" in concat_cmd


def test_compose_applies_bgm_when_enabled(tmp_path: Path, monkeypatch):
    a = tmp_path / "a.wav"
    a.write_bytes(b"a")
    bgm = tmp_path / "bgm.mp3"
    bgm.write_bytes(b"bgm")

    captured_cmds: list[list[str]] = []

    class _Result:
        def __init__(self, returncode: int = 0):
            self.returncode = returncode
            self.stdout = ""
            self.stderr = ""

    def _fake_run(cmd, capture_output, text, check):
        captured_cmds.append(cmd)
        Path(cmd[-1]).write_bytes(b"ok")
        return _Result(0)

    monkeypatch.setattr("app.tools.audio_timeline_composer.subprocess.run", _fake_run)

    composer = AudioTimelineComposer(ffmpeg_bin="ffmpeg")
    report = composer.compose(
        audio_assets=[{"status": "ready", "path": str(a)}],
        attempt_dir=tmp_path,
        audio_policy={"targetSampleRate": 44100},
        bgm_policy={"enabled": True, "volume": 0.2, "ducking": True},
        bgm_asset={"status": "ready", "path": str(bgm)},
    )

    assert report["success"] is True
    assert report["bgm_applied"] is True
    assert report["effective_bgm_policy"]["enabled"] is True
    bgm_cmd = report["bgm_command"]
    assert "-filter_complex" in bgm_cmd
    assert any("sidechaincompress" in part for part in bgm_cmd)


