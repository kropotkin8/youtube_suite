# Creator Intel Platform

A unified monorepo that combines **YouTube market ingestion** (Data API v3), **creator-side media processing** (transcription, subtitles, AI-assisted descriptions), and optional **podcast-to-Shorts** generation behind a single **FastAPI** service and one **PostgreSQL** database.

---

## Architecture

The codebase follows a **three-layer** layout under `src/youtube_suite/`:

| Layer | Path | Role |
|-------|------|------|
| **Presentation** | `api/` | FastAPI app, routers (`/market`, `/studio`, `/jobs`, `/insights`), Pydantic request/response models, dependency-injected DB sessions. |
| **Application** | `application/` | Use cases: `MarketIngestionService`, `StudioSubtitleService`, shorts orchestration, trending keywords for prompts. No HTTP types here. |
| **Domain** | `domain/` | Thin contracts (e.g. `TranscriptionPort`, `FileStoragePort`) for swapping implementations. |
| **Infrastructure** | `infrastructure/` | SQLAlchemy models & session, YouTube ETL (`youtube_etl/` extract/transform/load), FFmpeg helpers (`media/`), OpenAI descriptions (`nlp/`), `faster-whisper` (`ml/`), optional Shorts stack (`ml/shorts/`), local file storage (`storage/`). |

**Entry points**

- **HTTP:** `youtube_suite.api.main:app` — OpenAPI at `/docs`.
- **CLI:** `cip` — Typer commands under `market` for batch ETL (mirror of the legacy `youtube_analysis` CLI).

**PostgreSQL schemas** (single server, bounded contexts; see Alembic `001_initial_schemas`):

- **`market`** — YouTube catalog: channels, videos, stats time series, comments.
- **`studio`** — Your assets: `media_assets`, transcript segments, generated descriptions, subtitle artifacts. Optional cross-link: `studio.media_assets.market_video_id` → `market.videos.video_id`.
- **`app`** — Operational state: `jobs`, `job_events` (persistent Shorts pipeline state instead of in-memory jobs + ad-hoc JSON files).

Trending keywords for Studio descriptions are derived from **Market** data only (`application/insights/trending_service.py`), keeping analytics and generation loosely coupled but joinable when you set `market_video_id`.

---

## Prerequisites

- **Python** 3.10+
- **PostgreSQL** 15+
- **FFmpeg** on `PATH` (subtitles, audio extract, clip export)
- **Optional (Shorts):** `pip install -e ".[shorts]"`, CUDA if desired, and a **Hugging Face** token (`HF_TOKEN`) for pyannote diarization

---

## Quick start

1. **Clone and environment**

   ```bash
   cd youtube_suite
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate  # Linux/macOS
   pip install -e . --break-system-packages
   # pip install -e ".[dev]"    # pytest, httpx
   # pip install -e ".[shorts]" # Whisper / WhisperX / pyannote / sentence-transformers stack
   ```

2. **Configure**

   Copy `.env.example` to `.env` and set at least:

   - `DATABASE_URL` — SQLAlchemy URL, e.g. `postgresql+psycopg2://user:pass@localhost:5432/creator_intel`
   - `YT_API_KEY` — for Market ETL
   - `OPENAI_API_KEY` — for generated descriptions (Studio)
   - `CIP_DATA_DIR` — optional; defaults to `./data` (uploads, audio, clips)
   - `HF_TOKEN` — if using Shorts diarization

3. **Database migrations**

   ```bash
   alembic upgrade head
   ```

4. **Run the API**

   ```bash
   uvicorn youtube_suite.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Browse **http://localhost:8000/docs** for interactive OpenAPI.

5. **Frontend (React SPA)**

   Requirements: Node.js 18+

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Open **http://localhost:5173** — the Vite dev server proxies all API calls (`/market`, `/studio`, `/jobs`, `/insights`) to the FastAPI backend on port 8000. Both processes must run concurrently.

   **Tabs:**
   - **Market** — Paginated video table with stats, trending sync, YouTube search, KPI cards and charts.
   - **Studio** — Upload videos (drag & drop), view/manage assets, run subtitle/description/shorts pipelines with real-time job progress toasts.

   **Production build:**

   ```bash
   cd frontend
   npm run build   # static output in frontend/dist/
   ```

   To serve the SPA from FastAPI itself, add to `api/main.py`:
   ```python
   from fastapi.staticfiles import StaticFiles
   app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="spa")
   ```

6. **CLI (Market ETL)**

   ```bash
   cip market videos trending --region ES
   cip market videos by-ids "VIDEO_ID_1,VIDEO_ID_2"
   cip market channels by-ids "CHANNEL_ID"
   cip market video-stats snapshot
   cip market comments for-video VIDEO_ID
   cip market search videos "query" --limit 25
   ```

   Note: `cip market init-db` only reminds you to use Alembic; schema is owned by migrations.

6. **Docker** (optional)

   See `docker-compose.yml` for Postgres + API skeleton; ensure `.env` is compatible with the compose `DATABASE_URL`.

---

## API surface (overview)

- **`/market`** — Sync channels, videos, stats snapshots, comments; search-and-load; `GET /market/videos` (paginated list with latest stats); `GET /market/overview` (KPI aggregates); `GET /market/charts/top-videos|views-over-time|category-breakdown` (chart data).
- **`/studio`** — Upload assets, run subtitle/description/shorts pipelines (background tasks), stream original/subtitled video files, list clips for an asset; read transcript segments and generated descriptions.
- **`/jobs`** — Poll job status and progress, list clips, download individual clip files for completed Shorts jobs.
- **`/insights`** — `GET /insights/trending-keywords` from recent high-engagement Market titles + stats.

---

## Main dependencies (base install)

Declared in `pyproject.toml`:

| Area | Packages |
|------|----------|
| **API** | `fastapi`, `uvicorn[standard]`, `python-multipart` |
| **Config** | `pydantic`, `pydantic-settings`, `python-dotenv` |
| **Database** | `sqlalchemy`, `psycopg2-binary`, `alembic` |
| **CLI** | `typer`, `click` |
| **YouTube** | `google-api-python-client`, `python-dateutil` |
| **Studio NLP / ML** | `openai`, `faster-whisper`, `ffmpeg-python` |

**Optional extras**

- **`[shorts]`** — `openai-whisper`, `whisperx`, `torch`, `torchaudio`, `pyannote.audio`, `sentence-transformers`, `numpy`, `scipy` (heavy; use when you need the full Shorts pipeline).
- **`[dev]`** — `pytest`, `httpx` for tests and HTTP client utilities.

System binary: **FFmpeg** is invoked directly for media I/O (not covered by `pip`).

---

## Design notes

1. **Two ASR paths** — `faster-whisper` for Studio subtitles; Whisper + WhisperX (+ optional pyannote) for Shorts, behind lazy imports so the API starts without the `[shorts]` extra.
2. **SQL as contract** — Market and Studio stay in separate schemas; cross-domain joins use `market_video_id` when you link a published video to catalog rows.
3. **Source of truth for stats** — Treat YouTube API ingest as primary; merge rules for external dumps (e.g. Kaggle) should be documented if you add them.

---

## Tests

```bash
pytest
```

---

## License

Specify your license in this repository root if applicable.
