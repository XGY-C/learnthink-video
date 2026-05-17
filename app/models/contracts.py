from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class VideoSpec(BaseModel):
    aspect_ratio: str = Field(default="16:9", alias="aspectRatio")
    resolution: str = Field(default="1920x1080")
    fps: int = 30
    background: str = "#0B1020"


class SubtitleSpec(BaseModel):
    enabled: bool = True
    position: Literal["top", "bottom"] = "bottom"
    max_lines: int = Field(default=2, alias="maxLines")
    font_size: int = Field(default=30, alias="fontSize")
    mixed_timeline_policy: Literal["balanced", "subtitle_first", "action_first"] = Field(
        default="balanced",
        alias="mixedTimelinePolicy",
    )


class ProjectBrief(BaseModel):
    style: str = "极简科技感"
    manim_version: str = Field(default="0.20.1", alias="manimVersion")
    video_spec: VideoSpec = Field(default_factory=VideoSpec, alias="videoSpec")
    subtitle_spec: SubtitleSpec = Field(default_factory=SubtitleSpec, alias="subtitleSpec")
    design_rules: list[str] = Field(default_factory=list, alias="designRules")


class SentenceItem(BaseModel):
    index: int
    text: str
    start_sec: float = Field(alias="startSec")
    end_sec: float = Field(alias="endSec")


class SubtitleItem(BaseModel):
    text: str
    start_sec: float = Field(alias="startSec")
    end_sec: float = Field(alias="endSec")


class AnimationCue(BaseModel):
    id: str
    target_refs: list[str] = Field(default_factory=list, alias="targetRefs")
    action: str
    time_sec: float = Field(alias="timeSec")
    run_time_sec: float = Field(alias="runTimeSec")
    intent: str | None = None


class SceneObjectStyle(BaseModel):
    scale: float = 1.0
    emphasis: str | None = None


class SceneObject(BaseModel):
    id: str
    type: str
    content: str
    role: str | None = None
    placement: str = "center"
    style: SceneObjectStyle = Field(default_factory=SceneObjectStyle)


class SceneSpec(BaseModel):
    layout_template: str = Field(default="center_focus", alias="layoutTemplate")
    objects: list[SceneObject] = Field(default_factory=list)


class TimedScene(BaseModel):
    scene_id: str = Field(alias="sceneId")
    audio_url: str | None = Field(default=None, alias="audioUrl")
    duration_sec: float = Field(alias="durationSec")
    sentences: list[SentenceItem] = Field(default_factory=list)
    subtitle_items: list[SubtitleItem] = Field(default_factory=list, alias="subtitleItems")
    animation_cues: list[AnimationCue] = Field(default_factory=list, alias="animationCues")
    scene_spec: SceneSpec = Field(default_factory=SceneSpec, alias="sceneSpec")


class RenderPolicy(BaseModel):
    max_repair_rounds: int = Field(default=6, alias="maxRepairRounds")
    timeout_sec: int = Field(default=600, alias="timeoutSec")
    renderer: Literal["cairo", "opengl"] = "cairo"


class OutputPolicy(BaseModel):
    scene_class_name: str = Field(default="GeneratedVideoScene", alias="sceneClassName")
    file_base_name: str = Field(default="generated_video", alias="fileBaseName")
    need_poster: bool = Field(default=False, alias="needPoster")


class StoragePolicy(BaseModel):
    provider: Literal["aliyun_oss"] = "aliyun_oss"
    bucket: str | None = None
    region: str | None = None
    path_prefix: str | None = Field(default=None, alias="pathPrefix")


class AudioPolicy(BaseModel):
    mode: Literal["scene_audio"] = "scene_audio"
    normalize_volume: bool = Field(default=False, alias="normalizeVolume")
    insert_silence_between_scenes_ms: int = Field(default=0, alias="insertSilenceBetweenScenesMs")
    target_sample_rate: int = Field(default=44100, alias="targetSampleRate")


class BgmPolicy(BaseModel):
    enabled: bool = False
    url: str | None = None
    volume: float = 0.15
    ducking: bool = True


class DebugOptions(BaseModel):
    save_attempts: bool = Field(default=True, alias="saveAttempts")
    save_logs: bool = Field(default=True, alias="saveLogs")
    save_patched_code: bool = Field(default=True, alias="savePatchedCode")


class RenderRequest(BaseModel):
    request_id: str | None = Field(default=None, alias="requestId")
    project_brief: ProjectBrief = Field(alias="projectBrief")
    timed_scenes: list[TimedScene] = Field(alias="timedScenes")
    render_policy: RenderPolicy = Field(default_factory=RenderPolicy, alias="renderPolicy")
    output_policy: OutputPolicy = Field(default_factory=OutputPolicy, alias="outputPolicy")
    storage_policy: StoragePolicy = Field(default_factory=StoragePolicy, alias="storagePolicy")
    audio_policy: AudioPolicy = Field(default_factory=AudioPolicy, alias="audioPolicy")
    bgm_policy: BgmPolicy = Field(default_factory=BgmPolicy, alias="bgmPolicy")
    debug_options: DebugOptions = Field(default_factory=DebugOptions, alias="debugOptions")


class FinalResult(BaseModel):
    task_id: str = Field(alias="taskId")
    success: bool
    status: str
    video_url: str | None = Field(default=None, alias="videoUrl")
    oss_object_key: str | None = Field(default=None, alias="ossObjectKey")
    message: str | None = None
    attempts: int = 0
    task_dir: str | None = Field(default=None, alias="taskDir")


class RenderResponse(FinalResult):
    pass


class TaskEnvelope(BaseModel):
    task: dict[str, Any]
    result: dict[str, Any] | None = None
