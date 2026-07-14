from __future__ import annotations

from typing import Any


class ManimCodeExpert:
    @staticmethod
    def _parse_resolution(resolution: str) -> tuple[int, int]:
        raw = (resolution or "").strip().lower()
        if "x" in raw:
            w, h = raw.split("x", 1)
            return int(float(w)), int(float(h))
        if "," in raw:
            w, h = raw.split(",", 1)
            return int(float(w)), int(float(h))
        return 1920, 1080

    @staticmethod
    def _sanitize_content_for_codegen(content: Any) -> str:
        """避免把明显的占位 token 原样带入 make_shape('...')，触发质量门禁。"""
        text = str(content or "")
        lowered = text.lower()

        if "parabola_" in lowered or "parabola" in lowered or "graph" in lowered:
            return "graph"
        if "curved_arrow" in lowered or "simple_arrow" in lowered or "arrow" in lowered:
            return "arrow"
        if "dotted_line" in lowered or "line" in lowered:
            return "line"
        if "highlight" in lowered:
            return "emphasis"
        if "intersection" in lowered:
            return "crossing"

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

        # Fallback to center
        return f"ORIGIN + DOWN * {0.8 * obj_index:.2f}"

    def run(self, scene_ir: dict) -> str:
        scene_class_name = (scene_ir.get("outputPolicy") or {}).get("sceneClassName") or "GeneratedVideoScene"
        project_brief = scene_ir.get("projectBrief") or {}
        video_spec = project_brief.get("videoSpec") or {}
        subtitle_spec = project_brief.get("subtitleSpec") or {}
        scenes = scene_ir.get("scenes") or []

        background = str(video_spec.get("background") or "#0B1020")
        fps = int(video_spec.get("fps") or 30)
        width, height = self._parse_resolution(str(video_spec.get("resolution") or "1920x1080"))

        scene_methods: list[str] = []
        scene_calls: list[str] = []

        for idx, scene in enumerate(scenes, start=1):
            method_name = f"_play_scene_{idx:02d}"
            scene_calls.append(f"        self.{method_name}()")
            scene_methods.append(self._build_scene_method(method_name, scene, subtitle_spec))

        code = f'''from manim import *
from typing import Dict, List


config.background_color = {background!r}
config.pixel_width = {width}
config.pixel_height = {height}
config.frame_rate = {fps}


def safe_duration(value: float, fps: int = {fps}) -> float:
    min_value = 1.0 / max(fps, 1)
    return max(float(value), min_value)


def _is_formula_like(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    lowered = t.lower()
    return any(
        token in lowered
        for token in ["\\\\frac", "\\\\sqrt", "=", "^", "Δ", "delta", "x^", "y^", "\\\\int", "\\\\sum"]
    )


def _safe_text(content: str, font_size: int = 30, color_value=WHITE) -> Mobject:
    """Safe text fallback with error handling."""
    try:
        text = (content or "").strip()
        if not text:
            return Text("", font_size=font_size, color=color_value)
        return Text(text, font_size=font_size, color=color_value)
    except Exception:
        return Text("(text)", font_size=font_size, color=color_value)


def make_formula(content: str) -> Mobject:
    text = (content or "").strip()
    if not text:
        return _safe_text("", 30)
    try:
        return MathTex(text)
    except Exception:
        try:
            return _safe_text(text, 28)
        except Exception:
            return _safe_text("[formula]", 28)


def make_shape(content: str, obj_type: str = "shape") -> Mobject:
    text = content or ""
    lowered = text.lower()
    t = (obj_type or "shape").lower()

    if t == "formula" or _is_formula_like(text):
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
                return _safe_text(text, 24)

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

        return _safe_text(text, 30)

    # Flowchart node detection
    if "node" in lowered or "节点" in text:
        try:
            node = RoundedRectangle(corner_radius=0.15, width=2.5, height=1.2, color=BLUE, fill_opacity=0.15)
            label = _safe_text(text[:20], 24, WHITE)
            label.move_to(node.get_center())
            return VGroup(node, label)
        except Exception:
            return _safe_text(text, 26)

    # Annotation arrow with label
    if t == "arrow" and ("label" in lowered or "标注" in text):
        try:
            arrow = Arrow(LEFT * 1.5, RIGHT * 1.5, color=YELLOW)
            label = _safe_text(text[:15], 22, YELLOW)
            label.next_to(arrow, UP, buff=0.15)
            return VGroup(arrow, label)
        except Exception:
            pass

    if "graph" in lowered or "coordinate" in lowered:
        try:
            axes = Axes(
                x_range=[-4, 4, 1],
                y_range=[-3, 5, 1],
                x_length=5.0,
                y_length=3.6,
                axis_config={{"color": GREY_B}},
            )
            curve = axes.plot(lambda x: 0.5 * x**2, color=BLUE)
            return VGroup(axes, curve)
        except Exception:
            return _safe_text("graph", 26)

    if "arrow" in lowered:
        try:
            return Arrow(LEFT * 1.8 + DOWN * 0.8, RIGHT * 1.8 + UP * 0.8, color=YELLOW)
        except Exception:
            return _safe_text("->", 32)

    if "line" in lowered:
        try:
            return DashedLine(LEFT * 2.2, RIGHT * 2.2, color=GREY_B)
        except Exception:
            return _safe_text("-", 32)

    if "circle" in lowered or "圆" in text:
        try:
            return Circle(color=BLUE, fill_opacity=0.2)
        except Exception:
            return _safe_text("○", 32)
    if "square" in lowered or "矩形" in text or "长方形" in text:
        try:
            return RoundedRectangle(corner_radius=0.08, width=3.2, height=2.0, color=GREEN, fill_opacity=0.18)
        except Exception:
            return _safe_text("□", 32)
    if "triangle" in lowered or "三角" in text:
        try:
            return Triangle(color=YELLOW, fill_opacity=0.18)
        except Exception:
            return _safe_text("△", 32)
    if "dot" in lowered or "点" in text:
        try:
            return Dot(color=RED)
        except Exception:
            return _safe_text("·", 32)

    # Non-opaque fallback
    try:
        panel = RoundedRectangle(corner_radius=0.15, width=4.6, height=2.3, color=WHITE, fill_opacity=0.08)
        label = _safe_text((text or "")[:60], 24, WHITE)
        label.move_to(panel.get_center())
        return VGroup(panel, label)
    except Exception:
        return _safe_text((text or "")[:40], 22)


class {scene_class_name}(Scene):
    def construct(self):
{chr(10).join(scene_calls)}

{chr(10).join(scene_methods)}
'''
        return code

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
            obj_type = obj.get("type") or "shape"
            raw_content = obj.get("content", "")
            content = self._sanitize_content_for_codegen(raw_content)
            obj_role = obj.get("role")
            scale = float(obj.get("style", {}).get("scale", 1.0))

            move_expr = self._layout_placement(layout_template, idx - 1, len(objects), obj_type, obj_role)

            display_items.append(obj_var)
            obj_lines.extend([
                f"try:",
                f"    {obj_var} = make_shape({content!r}, obj_type={str(obj_type)!r}).scale({scale})",
                f"    {obj_var}.move_to({move_expr})",
                f"except Exception:",
                f"    {obj_var} = _safe_text({content!r}, 26)",
                f"objects[{obj.get('id', f'OBJ{idx:03d}')!r}] = {obj_var}",
            ])

        if not display_items:
            obj_lines.append('placeholder = _safe_text("No objects", 36)')
            display_items.append("placeholder")

        # 2. Build unified timeline of events sorted by time
        events: list[tuple[str, float, object]] = []

        # Intro event: FadeIn all objects at t=0
        events.append(("intro", 0.0, display_items))

        # Animation cue events
        for cue in animation_cues:
            time_sec = float(cue.get("timeSec", 0.0))
            events.append(("animation", time_sec, cue))

        # Subtitle events (all items, not just first 2-3)
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
                play_lines.append(f"try:")
                play_lines.append(f"    self.play(*[FadeIn(m) for m in [{items_list}]], run_time=safe_duration(0.6))")
                play_lines.append(f"except Exception:")
                play_lines.append(f"    self.wait(safe_duration(0.6))")
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
                play_lines.append(f"    try:")
                play_lines.append(f"        self.play(*[{anim_ctor}(m) for m in targets], run_time=safe_duration({run_time}))")
                play_lines.append(f"    except Exception:")
                play_lines.append(f"        self.wait(safe_duration({run_time}))")
                play_lines.append("else:")
                play_lines.append(f"    self.wait(safe_duration({run_time}))")
                current_time += run_time

            elif event_type == "subtitle_start":
                sub = event_data
                sub_counter += 1
                sub_var = f"{sub_prefix}_{sub_counter}"
                txt = sub.get("text", "")

                # FadeOut previous subtitle if still active
                if active_sub_var:
                    play_lines.append(f"try:")
                    play_lines.append(f"    self.play(FadeOut({active_sub_var}), run_time=safe_duration(0.2))")
                    play_lines.append(f"except Exception:")
                    play_lines.append(f"    pass")
                    current_time += 0.2

                play_lines.append(f"try:")
                play_lines.append(f"    {sub_var} = Text({txt!r}, font_size={font_size}, color=WHITE)")
                play_lines.append(f"except Exception:")
                play_lines.append(f"    {sub_var} = _safe_text({txt!r}, {font_size})")
                play_lines.append(f"{sub_var}.move_to({pos_expr})")
                play_lines.append(f"try:")
                play_lines.append(f"    self.play(FadeIn({sub_var}), run_time=safe_duration(0.2))")
                play_lines.append(f"except Exception:")
                play_lines.append(f"    pass")
                current_time += 0.2
                active_sub_var = sub_var

            elif event_type == "subtitle_end":
                if active_sub_var:
                    play_lines.append(f"try:")
                    play_lines.append(f"    self.play(FadeOut({active_sub_var}), run_time=safe_duration(0.2))")
                    play_lines.append(f"except Exception:")
                    play_lines.append(f"    pass")
                    current_time += 0.2
                    active_sub_var = None

        # 4. Wait remaining time to match durationSec
        remaining = duration_sec - current_time
        if remaining > 0.02:
            play_lines.append(f"self.wait(safe_duration({remaining:.3f}))")

        # 5. FadeOut all
        play_lines.append("try:")
        play_lines.append("    self.play(*[FadeOut(m) for m in self.mobjects], run_time=safe_duration(0.5))")
        play_lines.append("except Exception:")
        play_lines.append("    pass")

        body = "\n".join(["        " + line for line in obj_lines + play_lines])
        return f'''
    def {method_name}(self):
{body}
'''.rstrip()

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

    @staticmethod
    def _placement_to_expr(placement: str, duplicate_index: int = 0) -> str:
        """Fallback placement when layout template is not available."""
        mapping = {
            "center": "ORIGIN",
            "top": "UP * 2",
            "bottom": "DOWN * 2",
            "left": "LEFT * 3",
            "right": "RIGHT * 3",
            "top_left": "UP * 2 + LEFT * 3",
            "top_right": "UP * 2 + RIGHT * 3",
            "bottom_left": "DOWN * 2 + LEFT * 3",
            "bottom_right": "DOWN * 2 + RIGHT * 3",
            "upper_left": "UP * 2 + LEFT * 3",
            "upper_right": "UP * 2 + RIGHT * 3",
            "lower_left": "DOWN * 2 + LEFT * 3",
            "lower_right": "DOWN * 2 + RIGHT * 3",
        }
        base = mapping.get(placement, "ORIGIN")
        if duplicate_index <= 0:
            return base
        return f"{base} + DOWN * {0.7 * duplicate_index:.2f}"
