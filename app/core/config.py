from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# 获取项目根目录的绝对路径 (即 app 文件夹的上一级)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# 定义外部存储根目录 (项目目录的同级目录下的 video/runtime)
EXTERNAL_RUNTIME_ROOT = PROJECT_ROOT.parent / "video" / "runtime"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Manim Video API Service", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_to_file: bool = Field(default=False, alias="LOG_TO_FILE")
    use_json_log: bool = Field(default=False, alias="USE_JSON_LOG")

    # 使用计算好的绝对路径作为默认值
    runtime_root: Path = Field(default=EXTERNAL_RUNTIME_ROOT / "tasks", alias="RUNTIME_ROOT")
    prompt_root: Path = Field(default=Path("prompts"), alias="PROMPT_ROOT")
    max_attempts: int = Field(default=6, alias="MAX_ATTEMPTS")
    enable_llm_assist: bool = Field(default=False, alias="ENABLE_LLM_ASSIST")
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str | None = Field(default=None, alias="LLM_MODEL")

    # DeepSeek 思考模式配置
    deepseek_enable_thinking: bool = Field(default=True, alias="DEEPSEEK_ENABLE_THINKING")
    deepseek_reasoning_effort: str = Field(default="high", alias="DEEPSEEK_REASONING_EFFORT")

    # 智能体模型配置
    planner_model: str | None = Field(default=None, alias="PLANNER_MODEL")
    planner_enable_thinking: bool = Field(default=True, alias="PLANNER_ENABLE_THINKING")
    code_expert_model: str | None = Field(default=None, alias="CODE_EXPERT_MODEL")
    code_expert_enable_thinking: bool = Field(default=True, alias="CODE_EXPERT_ENABLE_THINKING")
    diagnoser_model: str | None = Field(default=None, alias="DIAGNOSER_MODEL")
    repair_model: str | None = Field(default=None, alias="REPAIR_MODEL")
    repair_enable_thinking: bool = Field(default=True, alias="REPAIR_ENABLE_THINKING")
    summarizer_model: str | None = Field(default=None, alias="SUMMARIZER_MODEL")
    redlines_model: str | None = Field(default=None, alias="REDLINES_MODEL")

    oss_enabled: bool = Field(default=False, alias="OSS_ENABLED")
    oss_endpoint: str | None = Field(default=None, alias="OSS_ENDPOINT")
    oss_bucket: str | None = Field(default=None, alias="OSS_BUCKET")
    oss_access_key_id: str | None = Field(default=None, alias="OSS_ACCESS_KEY_ID")
    oss_access_key_secret: str | None = Field(default=None, alias="OSS_ACCESS_KEY_SECRET")
    oss_security_token: str | None = Field(default=None, alias="OSS_SECURITY_TOKEN")
    oss_public_base_url: str | None = Field(default=None, alias="OSS_PUBLIC_BASE_URL")
    oss_path_prefix: str = Field(default="videos", alias="OSS_PATH_PREFIX")

    ffprobe_bin: str = Field(default="ffprobe", alias="FFPROBE_BIN")
    manim_bin: str = Field(default="manim", alias="MANIM_BIN")
    ffmpeg_bin: str = Field(default="ffmpeg", alias="FFMPEG_BIN")
    audio_cache_root: Path = Field(default=EXTERNAL_RUNTIME_ROOT / "audio_cache", alias="AUDIO_CACHE_ROOT")
    max_av_duration_diff_sec: float = Field(default=0.5, alias="MAX_AV_DURATION_DIFF_SEC")

    enable_render_cache: bool = Field(default=True, alias="ENABLE_RENDER_CACHE")
    cache_root: Path = Field(default=EXTERNAL_RUNTIME_ROOT / "render_cache", alias="CACHE_ROOT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.runtime_root.mkdir(parents=True, exist_ok=True)
    settings.audio_cache_root.mkdir(parents=True, exist_ok=True)
    settings.cache_root.mkdir(parents=True, exist_ok=True)
    return settings
