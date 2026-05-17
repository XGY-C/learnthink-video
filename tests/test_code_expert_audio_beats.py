from app.agents.code_expert import ManimCodeExpert


def _scene_ir_with_beats() -> dict:
    return {
        "projectBrief": {
            "videoSpec": {"background": "#000000", "resolution": "1920x1080", "fps": 30},
            "subtitleSpec": {"enabled": False, "position": "bottom", "fontSize": 30},
        },
        "outputPolicy": {"sceneClassName": "GeneratedVideoScene"},
        "scenes": [
            {
                "sceneId": "SC001",
                "durationSec": 3.0,
                "objects": [{"id": "OBJ001", "content": "circle", "placement": "center", "style": {"scale": 1.0}}],
                "subtitleItems": [],
                "animationBeatPlan": {
                    "sceneDurationSec": 3.0,
                    "beats": [
                        {
                            "sentenceIndex": 1,
                            "startSec": 0.0,
                            "endSec": 1.0,
                            "timelineSource": "sentence",
                            "actions": [
                                {
                                    "cueId": "CUE001",
                                    "action": "Create",
                                    "targetRefs": ["OBJ001"],
                                    "timeSec": 0.0,
                                    "runTimeSec": 0.8,
                                }
                            ],
                        }
                    ],
                },
            }
        ],
    }


def test_code_expert_uses_animation_beat_plan():
    expert = ManimCodeExpert()
    code = expert.run(_scene_ir_with_beats())

    assert "targets = [m for m in [objects.get('OBJ001')] if m is not None]" in code
    assert "Create(m)" in code
    assert "run_time=safe_duration(0.8)" in code


def test_code_expert_fallback_without_beats():
    expert = ManimCodeExpert()
    ir = _scene_ir_with_beats()
    ir["scenes"][0]["animationBeatPlan"] = {"beats": []}

    code = expert.run(ir)
    assert "Create(m)" not in code
    assert "self.wait(safe_duration(" in code


def test_code_expert_prioritizes_subtitle_timeline_beats():
    expert = ManimCodeExpert()
    ir = _scene_ir_with_beats()
    ir["projectBrief"]["subtitleSpec"]["enabled"] = True
    ir["scenes"][0]["subtitleItems"] = [{"text": "fallback subtitle", "startSec": 0.0, "endSec": 1.0}]
    ir["scenes"][0]["animationBeatPlan"]["beats"] = [
        {
            "sentenceIndex": 1,
            "text": "beat subtitle",
            "startSec": 0.0,
            "endSec": 1.2,
            "timelineSource": "subtitle",
            "actions": [],
        }
    ]

    code = expert.run(ir)

    assert "sub_beat_1 = Text('beat subtitle'" in code
    assert "self.play(FadeIn(sub_beat_1)" in code
    assert "sub_1 = Text('fallback subtitle'" not in code


def test_code_expert_mixed_policy_subtitle_first():
    expert = ManimCodeExpert()
    ir = _scene_ir_with_beats()
    ir["projectBrief"]["subtitleSpec"]["enabled"] = True
    ir["projectBrief"]["subtitleSpec"]["mixedTimelinePolicy"] = "subtitle_first"
    ir["scenes"][0]["animationBeatPlan"]["beats"] = [
        {
            "sentenceIndex": 1,
            "text": "mixed subtitle",
            "startSec": 0.0,
            "endSec": 1.0,
            "timelineSource": "mixed",
            "actions": [
                {
                    "cueId": "CUE001",
                    "action": "Create",
                    "targetRefs": ["OBJ001"],
                    "timeSec": 0.0,
                    "runTimeSec": 0.8,
                }
            ],
        }
    ]

    code = expert.run(ir)
    assert "sub_beat_1 = Text('mixed subtitle'" in code
    assert "Create(m)" not in code


def test_code_expert_mixed_policy_action_first():
    expert = ManimCodeExpert()
    ir = _scene_ir_with_beats()
    ir["projectBrief"]["subtitleSpec"]["enabled"] = True
    ir["projectBrief"]["subtitleSpec"]["mixedTimelinePolicy"] = "action_first"
    ir["scenes"][0]["animationBeatPlan"]["beats"] = [
        {
            "sentenceIndex": 1,
            "text": "mixed subtitle",
            "startSec": 0.0,
            "endSec": 1.0,
            "timelineSource": "mixed",
            "actions": [
                {
                    "cueId": "CUE001",
                    "action": "Create",
                    "targetRefs": ["OBJ001"],
                    "timeSec": 0.0,
                    "runTimeSec": 0.8,
                }
            ],
        }
    ]

    code = expert.run(ir)
    assert "Create(m)" in code
    assert "sub_beat_1 = Text('mixed subtitle'" not in code


