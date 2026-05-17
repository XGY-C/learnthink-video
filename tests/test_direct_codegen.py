from app.agents.direct_codegen import DirectCodegenAgent


def _scene_ir() -> dict:
    return {
        "projectBrief": {
            "videoSpec": {"background": "#000000", "resolution": "1920x1080", "fps": 30},
            "subtitleSpec": {"enabled": False, "position": "bottom", "fontSize": 30},
        },
        "outputPolicy": {"sceneClassName": "GeneratedVideoScene"},
        "scenes": [
            {
                "durationSec": 3,
                "objects": [
                    {"id": "OBJ001", "type": "formula", "content": "x^2+1=0", "placement": "center", "style": {"scale": 1.0}},
                    {"id": "OBJ002", "type": "shape", "content": "Parabola of f(x)=x^2", "placement": "right", "style": {"scale": 0.8}},
                ],
                "subtitleItems": [],
            }
        ],
    }


def test_direct_codegen_emits_semantic_helpers():
    code = DirectCodegenAgent().run(_scene_ir())
    assert "def make_formula(" in code
    assert "if t == \"formula\":" in code
    assert "MathTex(" in code
    assert "Axes(" in code

