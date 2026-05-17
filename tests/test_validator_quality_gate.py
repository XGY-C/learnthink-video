from app.agents.validator import FixValidator


def test_preflight_detects_formula_without_mathtex():
    code = """
obj_1 = make_shape('x^2 + 2x - 15 = 0')
"""
    issues = FixValidator().preflight_code_quality(code)
    labels = {item["rootCauseLabel"] for item in issues}
    assert "formula_not_rendered_with_mathtex" in labels


def test_preflight_detects_placeholder_and_overlap_risk():
    code = """
def _play_scene_01(self):
    obj_1 = make_shape('parabola_two_intersections')
    obj_1.move_to(ORIGIN)
    obj_2 = make_shape('curved_arrow')
    obj_2.move_to(ORIGIN)
"""
    issues = FixValidator().preflight_code_quality(code)
    labels = {item["rootCauseLabel"] for item in issues}
    assert "unresolved_visual_placeholder" in labels
    assert "layout_overlap_risk" in labels


def test_preflight_passes_when_mathtex_and_no_placeholders():
    code = """
expr = MathTex(r'x^2 + 2x - 15 = 0')
obj_1 = Circle()
obj_1.move_to(LEFT)
"""
    issues = FixValidator().preflight_code_quality(code)
    assert issues == []

