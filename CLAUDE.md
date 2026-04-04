# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup
```bash
pip install -e ".[dev]"          # Base install + dev tools
pip install -e ".[shorts]"       # Add shorts pipeline (WhisperX, pyannote, torch)
alembic upgrade head             # Create DB schemas and tables
```

### Running
```bash
uvicorn youtube_suite.api.main:app --reload --host 0.0.0.0 --port 8000
docker-compose up                # PostgreSQL + API via Docker
```

### CLI (Market ETL)
```bash
cip market videos trending --region ES
cip market videos by-ids "vid1,vid2"
cip market channels by-ids "ch1,ch2"
cip market video-stats snapshot [video_ids]
cip market comments for-video VID_ID --max-pages N
cip market search videos "QUERY" --limit 25
```

### Tests
```bash
pytest tests/
pytest tests/test_smoke.py       # Single test file
```

## Architecture

Layered monorepo: **API → Application → Infrastructure → Domain**

```
src/youtube_suite/
├── api/          # FastAPI routers (market, studio, jobs, insights)
├── application/  # Business logic services
├── infrastructure/
│   ├── persistence/    # SQLAlchemy ORM models + session
│   ├── youtube_etl/    # Extract → Transform → Load pipeline
│   ├── media/          # FFmpeg wrappers
│   ├── ml/             # ASR + shorts ML models
│   ├── nlp/            # OpenAI description generator
│   └── storage/        # Local file storage
├── domain/       # Protocol interfaces (TranscriptionPort, FileStoragePort)
├── config/       # Pydantic settings (loads from .env)
└── cli.py        # Typer CLI entry point (`cip` command)
```

### Database: Three PostgreSQL Schemas

- **market** — YouTube ETL data: `channels`, `videos`, `video_stats_timeseries`, `comments`
- **studio** — Creator assets: `media_assets`, `transcript_segments`, `generated_descriptions`, `subtitle_artifacts`
- **app** — Operational state: `jobs`, `job_events`

Cross-schema join: `studio.media_assets.market_video_id → market.videos.video_id`

### Async Job Pattern

Long-running pipelines (subtitles, shorts) run as FastAPI background tasks. Status is persisted in `app.jobs` with a `progress` float, `status` enum, and `result_json`. Clients poll `GET /jobs/{job_id}`.

### Dual ASR Pipelines

- **Studio pipeline** uses `faster-whisper` (lightweight, CPU-friendly). See `infrastructure/ml/faster_whisper_transcriber.py`.
- **Shorts pipeline** uses `WhisperX` (alignment + diarization via pyannote.audio). Requires `pip install -e ".[shorts]"` and `HF_TOKEN` env var.

### Shorts Scoring

Highlights are scored across five weighted factors (semantic similarity, audio energy, speaker changes, keyword presence, sentiment). Weights are configurable via `.env` variables. See `infrastructure/ml/shorts/highlights_service.py`.

### Configuration

All config is loaded via Pydantic settings in `config/settings.py` from `.env`. Copy `.env.example` to get started. Key variables: `DATABASE_URL`, `YT_API_KEY`, `OPENAI_API_KEY`, `FFMPEG_PATH`, `HF_TOKEN`, `CIP_DATA_DIR`.
