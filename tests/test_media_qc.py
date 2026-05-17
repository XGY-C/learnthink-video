from pathlib import Path

from app.tools.media_qc import MediaQC


class _FakeProbe:
    def __init__(self, payload: dict):
        self.payload = payload

    def probe(self, _: Path) -> dict:
        return self.payload


def test_media_qc_passes_with_audio_stream(tmp_path: Path):
    qc = MediaQC(max_av_duration_diff_sec=0.5)
    qc.ffprobe = _FakeProbe(
        {
            "available": True,
            "payload": {
                "streams": [
                    {"codec_type": "video", "duration": "5.0"},
                    {"codec_type": "audio", "duration": "5.1"},
                ],
                "format": {"duration": "5.1"},
            },
        }
    )

    report = qc.check(tmp_path / "x.mp4")
    assert report["passed"] is True


def test_media_qc_fails_without_audio_stream(tmp_path: Path):
    qc = MediaQC(max_av_duration_diff_sec=0.5)
    qc.ffprobe = _FakeProbe(
        {
            "available": True,
            "payload": {
                "streams": [{"codec_type": "video", "duration": "5.0"}],
                "format": {"duration": "5.0"},
            },
        }
    )

    report = qc.check(tmp_path / "x.mp4")
    assert report["passed"] is False
    assert report["error"] == "output_missing_audio_stream"

