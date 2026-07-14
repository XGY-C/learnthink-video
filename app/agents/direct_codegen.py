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
        # Code block detection
        if "code" in lowered or "代码" in text:
            try:
                lines = text.split("\\n")[:8]
                code_text = VGroup(*[Text(line, font_size=20, color=GREEN) for line in lines if line.strip()])
                code_text.arrange(DOWN, aligned_edge=LEFT, buff=0.1)
                bg = RoundedRectangle(corner_radius=0.1, width=5.5, height=max(len(lines) * 0.35, 1.5), color=WHITE, fill_opacity=0.05)
                bg.move_to(code_text.get_center())
                return VGroup(bg, code_text)
            except Exception:
                pass

        # Table detection
        if "table" in lowered or "表格" in text:
            try:
                cells = [c.strip() for c in text.split("|") if c.strip()][:4]
                if len(cells) >= 2:
                    data = [cells[:2], cells[2:4] if len(cells) > 2 else ["", ""]]
                    return Table(data, include_outer_lines=True).scale(0.6)
            except Exception:
                pass

        # Brace detection
        if "brace" in lowered or "括号" in text:
            try:
                target = Line(LEFT * 2, RIGHT * 2, color=WHITE)
                return Brace(target, UP, color=YELLOW)
            except Exception:
                pass

        return Text(text, font_size=30, color=WHITE)

    # Flowchart node detection
    if "node" in lowered or "节点" in text:
        try:
            node = RoundedRectangle(corner_radius=0.15, width=2.5, height=1.2, color=BLUE, fill_opacity=0.15)
            label = Text(text[:20], font_size=24, color=WHITE)
            label.move_to(node.get_center())
            return VGroup(node, label)
        except Exception:
            pass

    # Annotation arrow with label
    if t == "arrow" and ("label" in lowered or "标注" in text):
        try:
            arrow = Arrow(LEFT * 1.5, RIGHT * 1.5, color=YELLOW)
            label = Text(text[:15], font_size=22, color=YELLOW)
            label.next_to(arrow, UP, buff=0.15)
            return VGroup(arrow, label)
        except Exception:
            pass

    if "coordinate" in lowered or "parabola" in lowered or "graph" in lowered or "function" in lowered:
        try:
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
        except Exception:
            return Text(text[:40], font_size=24, color=WHITE)

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

    # Fallback with explicit text
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
            "Output a complete single Python file only.\n\n"
            "Requirements:\n"
            "- Use scene object types (formula/text/annotation/shape) to select appropriate Mobjects\n"
            "- Prefer MathTex for formulas, Text for plain language\n"
            "- Avoid unresolved placeholders - all objects must be concrete Manim primitives\n"
            "- Keep code runnable and well-structured\n"
            "- Do not use Axes(height=..., width=...); use Axes(y_length=..., x_length=...) instead\n"
            "- Include: from manim import *, from typing import Dict, config settings, safe_duration function\n"
            "- Each scene should have proper FadeIn/FadeOut animations with safe_duration\n"
            "- Use layoutTemplate to determine object placement\n"
            "- Synchronize animations with sentence timestamps from animationCues.timeSec\n"
            "- Show ALL subtitle items, not just the first few\n\n"
            "Output format:\n"
            "- Return Python code only, no explanations or markdown\n"
            "- Code must be directly executable without modifications"
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

    @staticmethod
    def _layout_placement(layout_template: str, obj_index: int, total_objects: int,
                          obj_type: str, obj_role: str | None) -> str:
        """根据布局模板返回 Manim 位置表达式。"""
        lt = (layout_template or "center_focus").strip()
        t = (obj_type or "shape").lower()
        is_text = t in {"text", "annotation"}
        is_formula = t == "formula"
        is_visual = t in {"shape", "arrow"}

        if lt == "center_focus":
            return f"ORIGIN + DOWN * {0.8 * obj_index:.2f}"

        if lt == "left_text_right_visual":
            if is_text:
                return f"LEFT * 4.0 + UP * {1.5 - 0.8 * obj_index:.2f}"
            return f"RIGHT * 4.0 + UP * {1.5 - 0.8 * obj_index:.2f}"

        if lt == "right_text_left_visual":
            if is_text:
                return f"RIGHT * 4.0 + UP * {1.5 - 0.8 * obj_index:.2f}"
            return f"LEFT * 4.0 + UP * {1.5 - 0.8 * obj_index:.2f}"

        if lt == "top_text_bottom_visual":
            if is_text:
                return f"UP * 2.0 + LEFT * {2.0 - 1.0 * obj_index:.2f}"
            return f"DOWN * 1.5 + RIGHT * {2.0 - 1.0 * obj_index:.2f}"

        if lt == "comparison_split":
            side = "LEFT" if obj_index % 2 == 0 else "RIGHT"
            vert_offset = -0.8 * (obj_index // 2)
            return f"{side} * 3.5 + UP * {vert_offset:.2f}"

        if lt == "formula_center":
            if is_formula:
                return "ORIGIN"
            if is_text:
                return f"UP * 2.5 + DOWN * {0.8 * obj_index:.2f}"
            return f"DOWN * 2.0 + DOWN * {0.8 * obj_index:.2f}"

        if lt == "process_flow":
            x_pos = -5.0 + 2.2 * obj_index
            return f"RIGHT * {x_pos:.2f}"

        return f"ORIGIN + DOWN * {0.8 * obj_index:.2f}"

    @staticmethod
    def _map_action_to_anim(action: str) -> str:
        mapping = {
            "FadeIn": "FadeIn",
            "FadeOut": "FadeOut",
            "Create": "Create",
            "Write": "Write",
            "Indicate": "Indicate",
            "Highlight": "Indicate",
            "PopIn": "FadeIn",
            "Morph": "Transform",
            "Move": "Shift",
            "Scale": "Scale",
        }
        return mapping.get(action, "FadeIn")

    def _build_scene_method(self, method_name: str, scene: dict, subtitle_spec: dict) -> str:
        objects = scene.get("objects", [])
        duration_sec = float(scene.get("durationSec", 2.0))
        layout_template = scene.get("layoutTemplate", "center_focus")

        pos_expr = "DOWN * 3.2" if subtitle_spec.get("position", "bottom") == "bottom" else "UP * 3.2"
        font_size = int(subtitle_spec.get("fontSize", 30))
        subtitle_enabled = subtitle_spec.get("enabled", True)
        mixed_policy = subtitle_spec.get("mixedTimelinePolicy", "balanced")

        # --- 从多种来源提取动画 cues 和字幕 ---
        animation_cues = scene.get("animationCues", [])
        subtitle_items = list(scene.get("subtitleItems", []))

        beat_plan = scene.get("animationBeatPlan") or {}
        beats = beat_plan.get("beats") or []
        use_beat_subtitles = False

        if not animation_cues and beats:
            beat_cues: list[dict] = []
            beat_subs: list[dict] = []
            for beat in beats:
                beat_start = float(beat.get("startSec", 0.0))
                beat_end = float(beat.get("endSec", beat_start + 1.0))
                beat_text = beat.get("text")
                beat_source = beat.get("timelineSource", "sentence")
                actions = beat.get("actions") or []

                show_subtitle = False
                show_actions = True

                if beat_text and subtitle_enabled:
                    if beat_source == "subtitle":
                        show_subtitle = True
                        show_actions = False
                    elif beat_source == "mixed":
                        if mixed_policy == "subtitle_first":
                            show_subtitle = True
                            show_actions = False
                        elif mixed_policy == "action_first":
                            show_subtitle = False
                            show_actions = True
                        else:
                            show_subtitle = True
                            show_actions = True

                if show_subtitle:
                    beat_subs.append({
                        "text": beat_text,
                        "startSec": beat_start,
                        "endSec": beat_end,
                    })

                if show_actions:
                    for action in actions:
                        beat_cues.append({
                            "targetRefs": action.get("targetRefs", []),
                            "action": action.get("action", "FadeIn"),
                            "timeSec": float(action.get("timeSec", beat_start)),
                            "runTimeSec": float(action.get("runTimeSec", 1.0)),
                        })

            animation_cues = beat_cues
            if beat_subs:
                subtitle_items = beat_subs
                use_beat_subtitles = True

        sub_prefix = "sub_beat" if use_beat_subtitles else "sub"

        obj_lines = ["objects: Dict[str, Mobject] = {}"]
        display_items: list[str] = []

        # 1. Create object instances with layout-based placement
        for idx, obj in enumerate(objects, start=1):
            obj_var = f"obj_{idx}"
            obj_type = obj.get("type", "shape")
            content = obj.get("content", "")
            obj_role = obj.get("role")
            scale = float(obj.get("style", {}).get("scale", 1.0))

            move_expr = self._layout_placement(layout_template, idx - 1, len(objects), obj_type, obj_role)

            obj_lines.extend([
                f"{obj_var} = make_visual({obj_type!r}, {content!r}).scale({scale})",
                f"{obj_var}.move_to({move_expr})",
                f"objects[{obj.get('id', f'OBJ{idx:03d}')!r}] = {obj_var}",
            ])
            display_items.append(obj_var)

        if not display_items:
            obj_lines.append('placeholder = Text("No objects", font_size=36, color=WHITE)')
            display_items.append("placeholder")

        # 2. Build unified timeline of events sorted by time
        events: list[tuple[str, float, object]] = []
        events.append(("intro", 0.0, display_items))

        for cue in animation_cues:
            time_sec = float(cue.get("timeSec", 0.0))
            events.append(("animation", time_sec, cue))

        if subtitle_enabled:
            for sub in subtitle_items:
                start = float(sub.get("startSec", 0.0))
                end = float(sub.get("endSec", start + 1.0))
                events.append(("subtitle_start", start, sub))
                events.append(("subtitle_end", end, sub))

        events.sort(key=lambda e: e[1])

        # 3. Walk the timeline generating code
        play_lines: list[str] = []
        current_time = 0.0
        active_sub_var: str | None = None
        sub_counter = 0

        for event_type, event_time, event_data in events:
            gap = event_time - current_time
            if gap > 0.02:
                play_lines.append(f"self.wait(safe_duration({gap:.3f}))")
                current_time = event_time

            if event_type == "intro":
                items_list = ", ".join(event_data)
                play_lines.append(f"self.play(*[FadeIn(m) for m in [{items_list}]], run_time=safe_duration(0.6))")
                current_time += 0.6

            elif event_type == "animation":
                cue = event_data
                target_refs = cue.get("targetRefs") or []
                action = cue.get("action") or "FadeIn"
                run_time = max(float(cue.get("runTimeSec", 1.0)), 0.1)
                anim_ctor = self._map_action_to_anim(action)
                target_terms = [f"objects.get({ref!r})" for ref in target_refs]
                targets_expr = ", ".join(target_terms)

                play_lines.append(f"targets = [m for m in [{targets_expr}] if m is not None]")
                play_lines.append("if targets:")
                play_lines.append(f"    self.play(*[{anim_ctor}(m) for m in targets], run_time=safe_duration({run_time}))")
                play_lines.append("else:")
                play_lines.append(f"    self.wait(safe_duration({run_time}))")
                current_time += run_time

            elif event_type == "subtitle_start":
                sub = event_data
                sub_counter += 1
                sub_var = f"{sub_prefix}_{sub_counter}"
                txt = sub.get("text", "")

                if active_sub_var:
                    play_lines.append(f"self.play(FadeOut({active_sub_var}), run_time=safe_duration(0.2))")
                    current_time += 0.2

                play_lines.append(f"{sub_var} = Text({txt!r}, font_size={font_size}, color=WHITE)")
                play_lines.append(f"{sub_var}.move_to({pos_expr})")
                play_lines.append(f"self.play(FadeIn({sub_var}), run_time=safe_duration(0.2))")
                current_time += 0.2
                active_sub_var = sub_var

            elif event_type == "subtitle_end":
                if active_sub_var:
                    play_lines.append(f"self.play(FadeOut({active_sub_var}), run_time=safe_duration(0.2))")
                    current_time += 0.2
                    active_sub_var = None

        # 4. Wait remaining time
        remaining = duration_sec - current_time
        if remaining > 0.02:
            play_lines.append(f"self.wait(safe_duration({remaining:.3f}))")

        # 5. FadeOut all
        play_lines.append("self.play(*[FadeOut(m) for m in self.mobjects], run_time=safe_duration(0.5))")

        body = "\n".join(["        " + line for line in obj_lines + play_lines])
        return f'''
    def {method_name}(self):
{body}
'''.rstrip()

    @staticmethod
    def _placement_to_expr(placement: str, duplicate_index: int) -> str:
        """Fallback placement when layout template is not available."""
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
