from app.agents.planner import RequestPlanner
from app.models.contracts import RenderRequest


def _minimal_payload() -> dict:
    return {
        "projectBrief": {},
        "timedScenes": [
            {
                "sceneId": "SC001",
                "durationSec": 3.0,
                "subtitleItems": [],
                "animationCues": [],
                "sceneSpec": {"objects": []},
            }
        ],
    }


def test_render_request_supports_default_audio_and_bgm_policy():
    req = RenderRequest(**_minimal_payload())

    assert req.audio_policy.mode == "scene_audio"
    assert req.audio_policy.target_sample_rate == 44100
    assert req.bgm_policy.enabled is False
    assert req.bgm_policy.volume == 0.15
    assert req.project_brief.subtitle_spec.mixed_timeline_policy == "balanced"


def test_render_request_parses_custom_audio_and_bgm_policy():
    payload = _minimal_payload()
    payload["projectBrief"] = {
        "subtitleSpec": {
            "mixedTimelinePolicy": "action_first",
        }
    }
    payload["audioPolicy"] = {
        "mode": "scene_audio",
        "normalizeVolume": True,
        "insertSilenceBetweenScenesMs": 120,
        "targetSampleRate": 48000,
    }
    payload["bgmPolicy"] = {
        "enabled": True,
        "url": "https://example.com/bgm.mp3",
        "volume": 0.2,
        "ducking": False,
    }

    req = RenderRequest(**payload)

    assert req.audio_policy.normalize_volume is True
    assert req.audio_policy.insert_silence_between_scenes_ms == 120
    assert req.audio_policy.target_sample_rate == 48000
    assert req.bgm_policy.enabled is True
    assert req.bgm_policy.url == "https://example.com/bgm.mp3"
    assert req.project_brief.subtitle_spec.mixed_timeline_policy == "action_first"


def test_planner_scene_ir_contains_audio_and_bgm_policy():
    planner = RequestPlanner()
    payload = _minimal_payload()
    payload["audioPolicy"] = {"normalizeVolume": True}
    payload["bgmPolicy"] = {"enabled": True}

    req = RenderRequest(**payload)
    plan = planner.run(req)

    assert "audioPolicy" in plan["sceneIR"]
    assert "bgmPolicy" in plan["sceneIR"]
    assert plan["sceneIR"]["audioPolicy"]["normalizeVolume"] is True
    assert plan["sceneIR"]["bgmPolicy"]["enabled"] is True
    assert "animationBeatPlan" in plan["sceneIR"]["scenes"][0]
    assert "beats" in plan["sceneIR"]["scenes"][0]["animationBeatPlan"]


def test_planner_uses_subtitle_items_for_animation_beats():
    planner = RequestPlanner()
    payload = _minimal_payload()
    payload["timedScenes"][0]["subtitleItems"] = [
        {"text": "第一句", "startSec": 0.0, "endSec": 1.0},
        {"text": "第二句", "startSec": 1.0, "endSec": 2.0},
    ]

    req = RenderRequest(**payload)
    plan = planner.run(req)
    beat_plan = plan["sceneIR"]["scenes"][0]["animationBeatPlan"]

    assert beat_plan["source"] == "subtitles"
    assert len(beat_plan["beats"]) == 2
    assert beat_plan["beats"][0]["startSec"] == 0.0
    assert beat_plan["beats"][1]["endSec"] == 2.0


