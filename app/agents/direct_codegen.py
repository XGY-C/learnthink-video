from __future__ import annotations

import json
import re

from app.llm.base import BaseLLMClient
from app.agents.notice_redlines import build_notice_redlines


class DirectCodegenAgent:
    """Render-aware fallback generator that respects object semantic types.

    This is intentionally deterministic so it can be compared against the legacy
    template generator in a dual-candidate selection stage.
    """

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client
        self.last_trace: dict = {"mode": "deterministic", "llmAttempted": False, "llmUsed": False}

    def run(self, scene_ir: dict, notices: list[dict] | None = None) -> str:
        self.last_trace = {"mode": "deterministic", "llmAttempted": False, "llmUsed": False}
        llm_code = self._try_llm_codegen(scene_ir, notices or [])
        if llm_code:
            self.last_trace = {"mode": "llm", "llmAttempted": True, "llmUsed": True}
            return llm_code
        return self._run_deterministic(scene_ir)

    def _run_deterministic(self, scene_ir: dict) -> str:
        scene_class_name = scene_ir["outputPolicy"]["sceneClassName"]
        project_brief = scene_ir["projectBrief"]
        video_spec = project_brief["videoSpec"]
        subtitle_spec = project_brief["subtitleSpec"]
        scenes = scene_ir["scenes"]

        scene_methods = []
        scene_calls = []

        for idx, scene in enumerate(scenes, start=1):
            method_name = f"_play_scene_{idx:02d}"
            scene_calls.append(f"        self.{method_name}()")
            scene_methods.append(self._build_scene_method(method_name, scene, subtitle_spec))

        code = f'''from manim import *
from typing import Dict


config.background_color = "{video_spec["background"]}"
config.pixel_width = {int(video_spec["resolution"].split("x")[0])}
config.pixel_height = {int(video_spec["resolution"].split("x")[1])}
config.frame_rate = {video_spec["fps"]}


def safe_duration(value: float, fps: int = {video_spec["fps"]}) -> float:
    min_value = 1.0 / max(fps, 1)
    return max(float(value), min_value)


def make_formula(content: str) -> Mobject:
    text = (content or "").strip()
    if not text:
        return Text("", font_size=30, color=WHITE)
    try:
        return MathTex(text)
    except Exception:
        return Text(text, font_size=30, color=WHITE)


def make_visual(obj_type: str, content: str) -> Mobject:
    t = (obj_type or "").lower()
    text = content or ""
    lowered = text.lower()

    if t == "formula":
        return make_formula(text)
    if t in {{"text", "annotation"}}:
        return Text(text, font_size=30, color=WHITE)

    if "coordinate" in lowered or "parabola" in lowered or "graph" in lowered or "function" in lowered:
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-3, 5, 1],
            x_length=5.0,
            y_length=3.6,
            axis_config={{"color": GREY_B}},
        )
        if "x^2" in lowered or "x2" in lowered or "x²" in text:
            curve = axes.plot(lambda x: x**2 / 2, color=BLUE)
        elif "decreasing" in lowered:
            curve = axes.plot(lambda x: -0.6 * x, color=RED)
        else:
            curve = axes.plot(lambda x: 0.6 * x, color=GREEN)
        return VGroup(axes, curve)

    if "arrow" in lowered or "increasing" in lowered:
        return Arrow(LEFT * 1.8 + DOWN * 0.8, RIGHT * 1.8 + UP * 0.8, color=YELLOW)

    if "circle" in lowered or "圆" in text:
        return Circle(color=BLUE, fill_opacity=0.2)
    if "triangle" in lowered or "三角" in text:
        return Triangle(color=YELLOW, fill_opacity=0.2)
    if "dot" in lowered or "点" in text:
        return Dot(color=RED)
    if "square" in lowered or "矩形" in text or "长方形" in text:
        return RoundedRectangle(corner_radius=0.08, width=3.2, height=2.0, color=GREEN, fill_opacity=0.15)

    # Fallback with explicit text to avoid opaque placeholders.
    panel = RoundedRectangle(corner_radius=0.12, width=4.8, height=2.4, color=WHITE, fill_opacity=0.08)
    label = Text(text[:80], font_size=24, color=WHITE)
    label.move_to(panel.get_center())
    return VGroup(panel, label)


class {scene_class_name}(Scene):
    def construct(self):
{chr(10).join(scene_calls)}

{chr(10).join(scene_methods)}
'''
        return code

    def _try_llm_codegen(self, scene_ir: dict, notices: list[dict]) -> str | None:
        if self.llm_client is None:
            return None
        self.last_trace["llmAttempted"] = True

        redlines = build_notice_redlines(notices)
        redline_block = (
            "Hard constraints from validated failure history. If any preference conflicts with these constraints, constraints win.\n"
            f"{redlines}\n"
            if redlines
            else ""
        )

        system_prompt = (
            "You are an expert Manim CE v0.20.1 code generator. "
            "Output a complete single Python file only. "
            "Requirements: use scene object types (formula/text/annotation/shape), "
            "prefer MathTex for formulas, avoid unresolved placeholders, and keep code runnable. "
            "Do not use Axes(height=..., width=...); use Axes(y_length=..., x_length=...) instead."
            + ("\n\n" + redline_block if redline_block else "")
        )
        user_prompt = (
            "Generate high-quality manim code from this scene IR.\n"
            "Use class name from outputPolicy.sceneClassName.\n"
            "Return Python code only.\n\n"
            + (f"Redlines:\n{redlines}\n\n" if redlines else "")
            +
            f"SceneIR:\n{json.dumps(scene_ir, ensure_ascii=False)}"
        )

        try:
            response = self.llm_client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception as exc:
            self.last_trace["llmError"] = str(exc)
            return None

        code = self._extract_python_code(response)
        if not code:
            self.last_trace["llmError"] = "empty_or_unparseable_response"
            return None
        if "from manim import" not in code or "class " not in code:
            self.last_trace["llmError"] = "response_missing_required_python_structure"
            return None
        code, sanitized = self._rewrite_axes_size_kwargs(code)
        if sanitized:
            self.last_trace["sanitizedAxesKwargs"] = True
        return code

    @staticmethod
    def _rewrite_axes_size_kwargs(code: str) -> tuple[str, bool]:
        marker = re.compile(r"\bAxes\s*\(")
        out: list[str] = []
        cursor = 0
        changed = False

        for match in marker.finditer(code):
            out.append(code[cursor:match.end()])
            i = match.end()
            depth = 1
            quote: str | None = None
            escaped = False
            while i < len(code):
                ch = code[i]
                if quote is not None:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == quote:
                        quote = None
                else:
                    if ch in {"\"", "'"}:
                        quote = ch
                    elif ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                        if depth == 0:
                            break
                i += 1

            if i >= len(code):
                out.append(code[match.end():])
                cursor = len(code)
                break

            args = code[match.end():i]
            rewritten = re.sub(r"(?<!\w)height\s*=", "y_length=", args)
            rewritten = re.sub(r"(?<!\w)width\s*=", "x_length=", rewritten)
            if rewritten != args:
                changed = True
            out.append(rewritten)
            out.append(")")
            cursor = i + 1

        out.append(code[cursor:])
        patched = "".join(out)
        return patched, changed

    @staticmethod
    def _extract_python_code(response: str) -> str:
        if not response:
            return ""
        text = response.strip()
        fenced = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if fenced:
            return fenced.group(1).strip()
        return text

    def _build_scene_method(self, method_name: str, scene: dict, subtitle_spec: dict) -> str:
        objects = scene.get("objects", [])
        subtitle_items = scene.get("subtitleItems", [])
        duration_sec = float(scene.get("durationSec", 2.0))

        lines = ["objects: Dict[str, Mobject] = {}"]
        display_items: list[str] = []
        placement_counts: dict[str, int] = {}

        for idx, obj in enumerate(objects, start=1):
            obj_var = f"obj_{idx}"
            obj_type = obj.get("type", "shape")
            content = obj.get("content", "")
            placement = obj.get("placement", "center")
            scale = float(obj.get("style", {}).get("scale", 1.0))

            placement_counts[placement] = placement_counts.get(placement, 0) + 1
            move_expr = self._placement_to_expr(placement, placement_counts[placement] - 1)

            lines.extend(
                [
                    f"{obj_var} = make_visual({obj_type!r}, {content!r}).scale({scale})",
                    f"{obj_var}.move_to({move_expr})",
                    f"objects[{obj.get('id', f'OBJ{idx:03d}')!r}] = {obj_var}",
                ]
            )
            display_items.append(obj_var)

        if display_items:
            lines.append(f"self.play(*[FadeIn(m) for m in [{', '.join(display_items)}]], run_time=safe_duration(0.8))")

        if subtitle_spec.get("enabled", True):
            pos_expr = "DOWN * 3.2" if subtitle_spec.get("position", "bottom") == "bottom" else "UP * 3.2"
            font_size = int(subtitle_spec.get("fontSize", 30))
            for i, item in enumerate(subtitle_items[:3], start=1):
                txt = item.get("text", "")
                start_sec = float(item.get("startSec", 0.0))
                end_sec = float(item.get("endSec", start_sec + 1.0))
                hold = max(end_sec - start_sec - 0.4, 0.1)
                lines.extend(
                    [
                        f"sub_{i} = Text({txt!r}, font_size={font_size}, color=WHITE)",
                        f"sub_{i}.move_to({pos_expr})",
                        f"self.play(FadeIn(sub_{i}), run_time=safe_duration(0.2))",
                        f"self.wait(safe_duration({hold}))",
                        f"self.play(FadeOut(sub_{i}), run_time=safe_duration(0.2))",
                    ]
                )

        lines.append(f"self.wait(safe_duration({max(duration_sec - 1.5, 0.3)}))")
        lines.append("self.play(*[FadeOut(m) for m in self.mobjects], run_time=safe_duration(0.5))")

        body = "\n".join(["        " + line for line in lines])
        return f'''
    def {method_name}(self):
{body}
'''.rstrip()

    @staticmethod
    def _placement_to_expr(placement: str, duplicate_index: int) -> str:
        base_mapping = {
            "center": "ORIGIN",
            "top": "UP * 2.2",
            "bottom": "DOWN * 2.2",
            "left": "LEFT * 4.0",
            "right": "RIGHT * 4.0",
            "top_left": "UP * 2.2 + LEFT * 4.0",
            "top_right": "UP * 2.2 + RIGHT * 4.0",
            "bottom_left": "DOWN * 2.2 + LEFT * 4.0",
            "bottom_right": "DOWN * 2.2 + RIGHT * 4.0",
            "upper_left": "UP * 2.2 + LEFT * 4.0",
            "upper_right": "UP * 2.2 + RIGHT * 4.0",
            "lower_left": "DOWN * 2.2 + LEFT * 4.0",
            "lower_right": "DOWN * 2.2 + RIGHT * 4.0",
        }
        base = base_mapping.get(placement, "ORIGIN")
        if duplicate_index <= 0:
            return base
        return f"{base} + DOWN * {0.7 * duplicate_index:.2f}"

