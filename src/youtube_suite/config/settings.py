from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://cip:cip@localhost:5432/creator_intel"

    yt_api_key: str | None = None

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20260315"

    local_llm_model: str = "mistral"
    local_llm_base_url: str = "http://localhost:11434"

    ffmpeg_path: str = "ffmpeg"

    hf_token: str | None = None
    whisper_model: str = "small"
    whisperx_device: str = "cpu"
    diarization_device: str = "cpu"

    min_clip_duration: float = 5.0
    max_clip_duration: float = 30.0
    target_clip_duration: float = 15.0
    num_clips: int = 5

    # Scoring weights (must sum to 1.0)
    score_shortability: float = 0.50
    score_semantic: float = 0.20
    score_hook: float = 0.15
    score_speaker_change: float = 0.15

    embedding_model: str = "all-mpnet-base-v2"
    audio_sample_rate: int = 16000
    audio_channels: int = 1

    cip_data_dir: Path = Path("./data")

    @property
    def score_weights(self) -> dict[str, float]:
        return {
            "shortability": self.score_shortability,
            "semantic": self.score_semantic,
            "hook": self.score_hook,
            "speaker_change": self.score_speaker_change,
        }


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings and ensure required data directories exist.

    Returns:
        Singleton ``Settings`` instance loaded from environment variables / ``.env``.
    """
    s = Settings()
    s.cip_data_dir.mkdir(parents=True, exist_ok=True)
    (s.cip_data_dir / "uploads").mkdir(exist_ok=True)
    (s.cip_data_dir / "audio").mkdir(exist_ok=True)
    (s.cip_data_dir / "clips").mkdir(exist_ok=True)
    (s.cip_data_dir / "metadata").mkdir(exist_ok=True)
    (s.cip_data_dir / "models").mkdir(exist_ok=True)
    return s
