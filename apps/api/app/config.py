from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Diary to Discovery API"
    app_env: str = "development"
    cors_origin: str = "http://localhost:4173"
    data_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data")
    parser_model: str = "gpt-5.4-mini"
    polish_model: str = "gpt-5.4-mini"
    tts_provider: str = "auto"
    tts_model: str = "gpt-4o-mini-tts"
    stt_model: str = "gpt-4o-mini-transcribe"
    moderation_model: str = "omni-moderation-latest"
    image_model: str = "gpt-image-1.5"
    sora_model: str = "sora-2-pro"
    default_voice: str = "marin"
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    elevenlabs_voice_id: str = "JBFqnCBsd6RMkjVDRZzb"
    elevenlabs_voice_label: str = "ElevenLabs Multilingual Narrator"
    elevenlabs_output_format: str = "mp3_44100_128"
    elevenlabs_language_code: str = "ko"
    elevenlabs_stability: float = 0.42
    elevenlabs_similarity_boost: float = 0.78
    elevenlabs_style: float = 0.08
    elevenlabs_speed: float = 0.94
    elevenlabs_speaker_boost: bool = True
    sora_render_mode: str = "live"
    allow_fallback: bool = False
    uv_bin_path: Path = Path("/Users/gimdonghyeon/.local/bin/uv")
    sora_cli_path: Path = Path("/Users/gimdonghyeon/.codex/skills/sora/scripts/sora.py")
    openai_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    media_storage_backend: Literal["local", "s3"] = "local"
    media_s3_bucket: str | None = None
    media_s3_region: str = "ap-northeast-2"
    media_s3_prefix: str = "media"
    media_s3_public_base_url: str | None = None

    @property
    def entries_dir(self) -> Path:
        return self.data_dir / "entries"

    @property
    def media_mount_dir(self) -> Path:
        return self.data_dir

    @property
    def s3_media_enabled(self) -> bool:
        return self.media_storage_backend == "s3" and bool(self.media_s3_bucket)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.entries_dir.mkdir(parents=True, exist_ok=True)
    return settings
