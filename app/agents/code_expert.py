from __future__ import annotations

class ManimCodeExpert:
    def run(self, scene_ir: dict) -> str:
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
from typing import Dict, List


config.background_color = "{video_spec["background"]}"
config.pixel_width = {int(video_spec["resolution"].split("x")[0])}
config.pixel_height = {int(video_spec["resolution"].split("x")[1])}
config.frame_rate = {video_spec["fps"]}


def safe_duration(value: float, fps: int = {video_spec["fps"]}) -> float:
    min_value = 1.0 / max(fps, 1)
    return max(float(value), min_value)


def make_shape(content: str):
    text = content or ""
    lowered = text.lower()
    if "circle" in lowered or "圆" in text:
        return Circle(color=BLUE, fill_opacity=0.2)
    if "square" in lowered or "矩形" in text or "长方形" in text:
        return RoundedRectangle(corner_radius=0.08, width=3.2, height=2.0, color=GREEN, fill_opacity=0.18)
    if "triangle" in lowered or "三角" in text:
        return Triangle(color=YELLOW, fill_opacity=0.18)
    if "dot" in lowered or "点" in text:
        return Dot(color=RED)
    return RoundedRectangle(corner_radius=0.15, width=3.8, height=2.4, color=WHITE, fill_opacity=0.08)


class {scene_class_name}(Scene):
    def construct(self):
{chr(10).join(scene_calls)}

{chr(10).join(scene_methods)}
'''
        return code

    def _build_scene_method(self, method_name: str, scene: dict, subtitle_spec: dict) -> str:
        objects = scene.get("objects", [])
        subtitle_items = scene.get("subtitleItems", [])
        duration_sec = scene.get("durationSec", 2.0)
        beat_plan = scene.get("animationBeatPlan") or {}
        mixed_policy = subtitle_spec.get("mixedTimelinePolicy", "balanced")

        obj_lines = ["objects: Dict[str, Mobject] = {}"]
        play_lines = []
        display_items = []

        for idx, obj in enumerate(objects, start=1):
            obj_var = f"obj_{idx}"
            content = obj.get("content", "")
            placement = obj.get("placement", "center")
            scale = float(obj.get("style", {}).get("scale", 1.0))
            move_expr = self._placement_to_expr(placement)
            display_items.append(obj_var)
            obj_lines.extend([
                f'{obj_var} = make_shape({content!r}).scale({scale})',
                f'{obj_var}.move_to({move_expr})',
                f'objects[{obj.get("id", f"OBJ{idx:03d}")!r}] = {obj_var}',
            ])

        if display_items:
            play_lines.append(f'self.play(*[FadeIn(m) for m in [{", ".join(display_items)}]], run_time=safe_duration(0.6))')
        else:
            play_lines.append('placeholder = Text("No objects", font_size=36, color=WHITE)')
            play_lines.append('self.play(FadeIn(placeholder), run_time=safe_duration(0.6))')
            display_items.append("placeholder")

        beat_lines = self._build_beat_play_lines(beat_plan, mixed_policy)
        if beat_lines:
            play_lines.extend(beat_lines)

        subtitle_beat_code = self._build_subtitle_beat_lines(beat_plan, subtitle_spec, mixed_policy)
        if subtitle_beat_code:
            play_lines.extend(subtitle_beat_code)

        subtitle_code = [] if subtitle_beat_code else self._build_subtitle_code(subtitle_items, subtitle_spec)
        if subtitle_code:
            play_lines.extend(subtitle_code)

        remaining = max(duration_sec - (0.8 if beat_lines else 1.2), 0.2)
        play_lines.append(f"self.wait(safe_duration({remaining}))")
        play_lines.append(f"self.play(*[FadeOut(m) for m in self.mobjects], run_time=safe_duration(0.5))")

        body = "\n".join(["        " + line for line in obj_lines + play_lines])
        return f'''
    def {method_name}(self):
{body}
'''.rstrip()

    @staticmethod
    def _build_beat_play_lines(beat_plan: dict, mixed_policy: str = "balanced") -> list[str]:
        beats = beat_plan.get("beats") or []
        if not beats:
            return []

        lines: list[str] = []
        for beat in beats:
            timeline_source = beat.get("timelineSource")
            if timeline_source == "mixed" and mixed_policy == "subtitle_first":
                continue

            actions = beat.get("actions") or []
            start_sec = float(beat.get("startSec", 0.0))
            end_sec = float(beat.get("endSec", start_sec + 0.5))
            beat_duration = max(end_sec - start_sec, 0.2)

            if not actions:
                lines.append(f"self.wait(safe_duration({beat_duration}))")
                continue

            # Split beat duration by action count when cue run_time is not explicitly provided.
            default_action_duration = max(beat_duration / max(len(actions), 1), 0.1)
            for action in actions:
                action_name = action.get("action") or "FadeIn"
                target_refs = action.get("targetRefs") or []
                run_time = max(float(action.get("runTimeSec", default_action_duration)), 0.1)

                anim_ctor = ManimCodeExpert._map_action_to_anim(action_name)
                target_terms = [f"objects.get({ref!r})" for ref in target_refs]
                targets_expr = ", ".join(target_terms)

                lines.append(f"targets = [m for m in [{targets_expr}] if m is not None]")
                lines.append("if targets:")
                lines.append(
                    f"    self.play(*[{anim_ctor}(m) for m in targets], run_time=safe_duration({run_time}))"
                )
                lines.append("else:")
                lines.append(f"    self.wait(safe_duration({run_time}))")

        return lines

    @staticmethod
    def _build_subtitle_beat_lines(beat_plan: dict, subtitle_spec: dict, mixed_policy: str = "balanced") -> list[str]:
        if not subtitle_spec.get("enabled", True):
            return []

        beats = beat_plan.get("beats") or []
        subtitle_beats = [beat for beat in beats if beat.get("timelineSource") == "subtitle"]
        if mixed_policy in {"balanced", "subtitle_first"}:
            subtitle_beats.extend([beat for beat in beats if beat.get("timelineSource") == "mixed"])
        if not subtitle_beats:
            return []

        lines: list[str] = []
        pos_expr = "DOWN * 3.2" if subtitle_spec.get("position", "bottom") == "bottom" else "UP * 3.2"
        font_size = int(subtitle_spec.get("fontSize", 30))

        for i, beat in enumerate(subtitle_beats, start=1):
            txt = beat.get("text") or ""
            start_sec = float(beat.get("startSec", 0.0))
            end_sec = float(beat.get("endSec", start_sec + 0.8))
            hold_time = max(end_sec - start_sec - 0.4, 0.1)
            lines.extend([
                f'sub_beat_{i} = Text({txt!r}, font_size={font_size}, color=WHITE)',
                f'sub_beat_{i}.move_to({pos_expr})',
                f'self.play(FadeIn(sub_beat_{i}), run_time=safe_duration(0.2))',
                f'self.wait(safe_duration({hold_time}))',
                f'self.play(FadeOut(sub_beat_{i}), run_time=safe_duration(0.2))',
            ])
        return lines

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
        }
        return mapping.get(action, "FadeIn")

    @staticmethod
    def _placement_to_expr(placement: str) -> str:
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
        }
        return mapping.get(placement, "ORIGIN")

    @staticmethod
    def _build_subtitle_code(subtitle_items: list[dict], subtitle_spec: dict) -> list[str]:
        if not subtitle_spec.get("enabled", True):
            return []

        lines: list[str] = []
        pos_expr = "DOWN * 3.2" if subtitle_spec.get("position", "bottom") == "bottom" else "UP * 3.2"
        font_size = int(subtitle_spec.get("fontSize", 30))

        for i, item in enumerate(subtitle_items[:2], start=1):
            txt = item.get("text", "")
            start_sec = float(item.get("startSec", 0.0))
            end_sec = float(item.get("endSec", start_sec + 1.0))
            run_time = max(end_sec - start_sec, 0.3)
            lines.extend([
                f'sub_{i} = Text({txt!r}, font_size={font_size}, color=WHITE)',
                f'sub_{i}.move_to({pos_expr})',
                f'self.play(FadeIn(sub_{i}), run_time=safe_duration(0.2))',
                f'self.wait(safe_duration({run_time}))',
                f'self.play(FadeOut(sub_{i}), run_time=safe_duration(0.2))',
            ])
        return lines
