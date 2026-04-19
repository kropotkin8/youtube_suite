#!/usr/bin/env bash
# start.sh — Launch youtube_suite (API + frontend + Ollama) from WSL
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"
VENV="$PROJECT_DIR/venv/bin/activate"
LOG_DIR="$PROJECT_DIR/data/logs"

mkdir -p "$LOG_DIR"

# ── Colours ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[start]${NC} $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC}  $*"; }
error()   { echo -e "${RED}[error]${NC} $*"; }

# ── Cleanup on exit ────────────────────────────────────────────────────────────
PIDS=()
cleanup() {
    echo ""
    info "Shutting down..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
    info "Done."
}
trap cleanup EXIT INT TERM

# ── 1. Check .env ──────────────────────────────────────────────────────────────
if [[ ! -f "$PROJECT_DIR/.env" ]]; then
    warn ".env not found — copying from .env.example"
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    warn "Edit .env and fill in DATABASE_URL before running again."
    exit 1
fi

# ── 2. Ollama ──────────────────────────────────────────────────────────────────
if command -v ollama &>/dev/null; then
    if ! pgrep -x ollama &>/dev/null; then
        info "Starting Ollama..."
        export OLLAMA_MODELS="${OLLAMA_MODELS:-/mnt/d/ollama/models}"
        ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
        PIDS+=($!)
        sleep 2
        info "Ollama running (logs: data/logs/ollama.log)"
    else
        info "Ollama already running."
    fi
else
    warn "Ollama not found — local LLM unavailable. Install with:"
    warn "  curl -fsSL https://ollama.com/install.sh | sh"
fi

# ── 3. PostgreSQL via Docker (optional) ───────────────────────────────────────
# if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
#     if ! docker ps --format '{{.Names}}' | grep -q "youtube_suite"; then
#         info "Starting PostgreSQL via Docker..."
#         docker compose -f "$PROJECT_DIR/docker-compose.yml" up db -d
#     else
#         info "PostgreSQL already running."
#     fi
# else
#     warn "Docker not available — make sure PostgreSQL is running manually."
# fi

# ── 4. Python venv ─────────────────────────────────────────────────────────────
if [[ ! -f "$VENV" ]]; then
    error "venv not found at $VENV"
    error "Run: pip install -e '.[dev]' && alembic upgrade head"
    exit 1
fi
source "$VENV"

# ── 5. DB migrations ───────────────────────────────────────────────────────────
info "Running DB migrations..."
cd "$PROJECT_DIR"
alembic upgrade head

# ── 6. FastAPI backend ─────────────────────────────────────────────────────────
info "Starting API on http://localhost:8000 ..."
uvicorn youtube_suite.api.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/api.log" 2>&1 &
PIDS+=($!)
sleep 1

# ── 7. Frontend ────────────────────────────────────────────────────────────────
if [[ -d "$FRONTEND_DIR/node_modules" ]]; then
    info "Starting frontend on http://localhost:5173 ..."
    cd "$FRONTEND_DIR"
    npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    PIDS+=($!)
else
    warn "Frontend deps not installed. Run: cd frontend && npm install"
fi

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${GREEN}API${NC}       → http://localhost:8000"
echo -e "  ${GREEN}Docs${NC}      → http://localhost:8000/docs"
echo -e "  ${GREEN}Frontend${NC}  → http://localhost:5173"
echo -e "  ${GREEN}Logs${NC}      → $LOG_DIR/"
echo ""
info "Press Ctrl+C to stop everything."

# Keep script alive
wait
