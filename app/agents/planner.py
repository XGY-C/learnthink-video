from __future__ import annotations

from app.models.contracts import RenderRequest


class RequestPlanner:
    @staticmethod
    def _collect_timeline_windows(scene, duration: float) -> tuple[list[dict], str]:
        windows: list[dict] = []

        for sentence in sorted(scene.sentences, key=lambda item: item.start_sec):
            start_sec = max(float(sentence.start_sec), 0.0)
            end_sec = min(max(float(sentence.end_sec), start_sec + 0.1), duration)
            windows.append(
                {
                    "sentenceIndex": sentence.index,
                    "text": sentence.text,
                    "startSec": start_sec,
                    "endSec": end_sec,
                    "source": "sentence",
                }
            )

        subtitle_base_idx = len(windows)
        for idx, subtitle in enumerate(sorted(scene.subtitle_items, key=lambda item: item.start_sec), start=1):
            start_sec = max(float(subtitle.start_sec), 0.0)
            end_sec = min(max(float(subtitle.end_sec), start_sec + 0.1), duration)
            windows.append(
                {
                    "sentenceIndex": subtitle_base_idx + idx,
                    "text": subtitle.text,
                    "startSec": start_sec,
                    "endSec": end_sec,
                    "source": "subtitle",
                }
            )

        if not windows:
            return [], "fallback"

        windows = sorted(windows, key=lambda item: (item["startSec"], item["endSec"]))
        merged: list[dict] = [dict(windows[0])]
        for item in windows[1:]:
            prev = merged[-1]
            if item["startSec"] < prev["endSec"]:
                prev["endSec"] = max(prev["endSec"], item["endSec"])
                if item["text"] and item["text"] != prev["text"]:
                    prev["text"] = f"{prev['text']} | {item['text']}" if prev["text"] else item["text"]
                if prev.get("source") != item.get("source"):
                    prev["source"] = "mixed"
            else:
                merged.append(dict(item))

        if scene.sentences and scene.subtitle_items:
            source = "sentences_subtitles"
        elif scene.sentences:
            source = "sentences"
        else:
            source = "subtitles"

        return merged, source

    @staticmethod
    def _build_animation_beat_plan(scene) -> dict:
        duration = max(float(scene.duration_sec), 0.1)
        cues = sorted(scene.animation_cues, key=lambda cue: cue.time_sec)
        windows, source = RequestPlanner._collect_timeline_windows(scene, duration)

        beats: list[dict] = []
        if windows:
            for window in windows:
                beats.append(
                    {
                        "sentenceIndex": window["sentenceIndex"],
                        "text": window["text"],
                        "startSec": window["startSec"],
                        "endSec": window["endSec"],
                        "timelineSource": window.get("source"),
                        "actions": [],
                    }
                )
        else:
            beats.append(
                {
                    "sentenceIndex": 1,
                    "text": "",
                    "startSec": 0.0,
                    "endSec": duration,
                    "actions": [],
                }
            )

        for cue in cues:
            action_payload = {
                "cueId": cue.id,
                "action": cue.action,
                "targetRefs": cue.target_refs,
                "timeSec": float(cue.time_sec),
                "runTimeSec": max(float(cue.run_time_sec), 0.1),
                "intent": cue.intent,
            }

            matched = False
            for beat in beats:
                if beat["startSec"] <= action_payload["timeSec"] <= beat["endSec"]:
                    beat["actions"].append(action_payload)
                    matched = True
                    break
            if not matched:
                beats[-1]["actions"].append(action_payload)

        for beat in beats:
            beat["actions"] = sorted(beat["actions"], key=lambda item: item["timeSec"])

        return {
            "sceneDurationSec": duration,
            "beats": beats,
            "source": source,
        }

    def run(self, request: RenderRequest) -> dict:
        risks: list[dict] = []
        normalized_scenes = []

        for scene in request.timed_scenes:
            if scene.duration_sec <= 0:
                risks.append({
                    "level": "high",
                    "type": "invalid_scene_duration",
                    "message": f"Scene {scene.scene_id} duration <= 0",
                    "sceneId": scene.scene_id,
                })

            object_ids = {obj.id for obj in scene.scene_spec.objects}
            for cue in scene.animation_cues:
                missing = [ref for ref in cue.target_refs if ref not in object_ids]
                if missing:
                    risks.append({
                        "level": "medium",
                        "type": "missing_target_refs",
                        "message": f"Cue {cue.id} has missing target refs: {missing}",
                        "sceneId": scene.scene_id,
                    })

            normalized_scenes.append({
                "sceneId": scene.scene_id,
                "durationSec": max(scene.duration_sec, 0.1),
                "layoutTemplate": scene.scene_spec.layout_template,
                "audioUrl": scene.audio_url,
                "objects": [obj.model_dump(by_alias=True) for obj in scene.scene_spec.objects],
                "subtitleItems": [sub.model_dump(by_alias=True) for sub in scene.subtitle_items],
                "sentences": [sent.model_dump(by_alias=True) for sent in scene.sentences],
                "animationCues": [cue.model_dump(by_alias=True) for cue in scene.animation_cues],
                "animationBeatPlan": self._build_animation_beat_plan(scene),
            })

        return {
            "normalizedRequest": request.model_dump(by_alias=True),
            "sceneIR": {
                "projectBrief": request.project_brief.model_dump(by_alias=True),
                "outputPolicy": request.output_policy.model_dump(by_alias=True),
                "renderPolicy": request.render_policy.model_dump(by_alias=True),
                "audioPolicy": request.audio_policy.model_dump(by_alias=True),
                "bgmPolicy": request.bgm_policy.model_dump(by_alias=True),
                "scenes": normalized_scenes,
            },
            "riskReport": {"risks": risks},
        }
