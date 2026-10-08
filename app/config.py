from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Summary: OpenRouter free by default; Anthropic remains optional.
    summary_provider: Literal["openrouter", "anthropic"] = "openrouter"
    openrouter_api_key: str = ""
    summary_max_tokens: int = Field(default=4096, ge=256, le=16000)
    summary_timeout_seconds: float = Field(default=180, gt=0, le=600)
    anthropic_api_key: str = ""
    summary_model: str = "openrouter/free"

    @property
    def summary_key_present(self) -> bool:
        key = self.openrouter_api_key if self.summary_provider == "openrouter" else self.anthropic_api_key
        return bool(key.strip())

    # ASR
    asr_backend: str = "scribe"
    elevenlabs_api_key: str = ""
    groq_api_key: str = ""
    groq_asr_model: Literal["whisper-large-v3-turbo", "whisper-large-v3"] = "whisper-large-v3-turbo"
    local_asr_model: str = "biodatlab/whisper-th-medium-combined"
    local_asr_compute: str = "int8"
    local_asr_device: str = "cuda"

    # โครงสร้างพื้นฐาน
    database_url: str = "postgresql://postgres:buzzle@db:5432/buzzle"
    redis_url: str = "redis://redis:6379/0"

    # ที่เก็บไฟล์
    storage_backend: str = "local"
    media_dir: str = "/srv/media"
    max_upload_bytes: int = Field(default=524288000, gt=0)
    max_duration_seconds: int = Field(default=3600, gt=0, le=3600)
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_region: str = "auto"

    public_api_url: str = "http://localhost:8000"


@lru_cache
def settings() -> Settings:
    return Settings()
