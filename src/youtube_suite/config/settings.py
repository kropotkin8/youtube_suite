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

    ffmpeg_path: str = "ffmpeg"

    hf_token: str | None = None
    whisper_model: str = "small"
    whisperx_device: str = "cpu"
    diarization_device: str = "cpu"

    min_clip_duration: float = 5.0
    max_clip_duration: float = 30.0
    target_clip_duration: float = 15.0
    num_clips: int = 5

    score_semantic: float = 0.4
    score_energy: float = 0.2
    score_speaker_change: float = 0.15
    score_keyword: float = 0.15
    score_sentiment: float = 0.1

    embedding_model: str = "all-mpnet-base-v2"
    audio_sample_rate: int = 16000
    audio_channels: int = 1

    cip_data_dir: Path = Path("./data")

    @property
    def score_weights(self) -> dict[str, float]:
        return {
            "semantic": self.score_semantic,
            "energy": self.score_energy,
            "speaker_change": self.score_speaker_change,
            "keyword": self.score_keyword,
            "sentiment": self.score_sentiment,
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
    return s
