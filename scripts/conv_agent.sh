#!/usr/bin/env bash
# conv_agent.sh -- Build, test, and run the Flux Conv Agent
# Usage: ./scripts/conv_agent.sh [setup|test|run|build|deploy]
set -euo pipefail

# -- Colors ------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# -- Resolve project root ----------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# -- Load .env files (if present) --------------------------------------------
# backend/.env is loaded first; frontend/.env may override individual values.

BACKEND_ENV="$PROJECT_ROOT/backend/.env"
if [ -f "$BACKEND_ENV" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$BACKEND_ENV"
    set +a
fi

FRONTEND_ENV="$PROJECT_ROOT/frontend/.env"
if [ -f "$FRONTEND_ENV" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$FRONTEND_ENV"
    set +a
fi

# Bridge naming conventions: the backend uses SUPABASE_KEY; the frontend server
# functions expect SUPABASE_ANON_KEY. Map one to the other if needed.
if [ -z "${SUPABASE_ANON_KEY:-}" ] && [ -n "${SUPABASE_KEY:-}" ]; then
    export SUPABASE_ANON_KEY="$SUPABASE_KEY"
fi

# Validate required Supabase env vars and warn early rather than failing at runtime.
if [ -z "${SUPABASE_URL:-}" ] || [ -z "${SUPABASE_ANON_KEY:-}" ]; then
    warn "SUPABASE_URL or SUPABASE_ANON_KEY is not set."
    warn "Create backend/.env (or frontend/.env) with:"
    warn "  SUPABASE_URL=https://<project>.supabase.co"
    warn "  SUPABASE_KEY=<anon-key>   # or SUPABASE_ANON_KEY=<anon-key>"
fi

# -- Subcommands -------------------------------------------------------------

cmd_setup() {
    info "Setting up Flux Conv Agent..."

    # Check Python
    if command -v python3 &>/dev/null; then
        PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        info "Python version: $PY_VERSION"
        PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
        if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
            fail "Python 3.11+ is required (found $PY_VERSION)"
        fi
        ok "Python 3.11+ found"
    else
        fail "Python 3 is not installed"
    fi

    # Install backend dependencies
    info "Installing backend dependencies..."
    cd "$PROJECT_ROOT/backend"
    pip install -r requirements.txt
    ok "Backend dependencies installed"

    # Install dao_service dependencies
    info "Installing dao_service dependencies..."
    pip install -r dao_service/requirements.txt
    ok "dao_service dependencies installed"

    # Check Node.js
    if command -v node &>/dev/null; then
        NODE_VERSION=$(node --version)
        info "Node.js version: $NODE_VERSION"
        ok "Node.js found"
    else
        fail "Node.js is not installed"
    fi

    # Install frontend dependencies
    info "Installing frontend dependencies..."
    cd "$PROJECT_ROOT/frontend"
    npm install
    ok "Frontend dependencies installed"

    echo ""
    info "Setup complete."
    echo ""
    warn "Remember to set DEEPGRAM_API_KEY in your .env file:"
    echo "  echo 'DEEPGRAM_API_KEY=your_key_here' >> $PROJECT_ROOT/backend/.env"
}

cmd_test() {
    info "Running conv_agent unit tests..."

    cd "$PROJECT_ROOT/backend"
    python3 -m pytest conv_agent/tests/ -v --tb=short -m "not integration"

    if [ $? -eq 0 ]; then
        ok "Unit tests passed"
    else
        fail "Some unit tests failed"
    fi

    # Run integration tests if DEEPGRAM_API_KEY is set
    if [ -n "${DEEPGRAM_API_KEY:-}" ]; then
        info "DEEPGRAM_API_KEY detected -- running integration tests..."
        python3 -m pytest conv_agent/tests/ -v --tb=short -m integration
        if [ $? -eq 0 ]; then
            ok "Integration tests passed"
        else
            fail "Some integration tests failed"
        fi
    else
        warn "DEEPGRAM_API_KEY not set -- skipping integration tests"
        warn "Set DEEPGRAM_API_KEY to run integration tests"
    fi
}

cmd_run() {
    info "Starting backend server (dev mode) on port 8080..."

    cd "$PROJECT_ROOT/backend"
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
}

cmd_build() {
    info "Building frontend..."

    cd "$PROJECT_ROOT/frontend"
    npm run build

    ok "Frontend build complete"
}

cmd_deploy() {
    info "Starting full stack via Docker Compose (dao + backend + frontend)..."

    # Supabase must be running before Docker Compose services start,
    # because dao and backend connect to it on host port 54322 / 54321.
    SUPABASE_CONTAINER="supabase_db_Flux-Team-8"
    if ! docker ps --format '{{.Names}}' | grep -q "$SUPABASE_CONTAINER"; then
        warn "Supabase is not running. Attempting to start..."
        cd "$PROJECT_ROOT"
        if supabase start 2>&1; then
            ok "Supabase started"
        else
            warn "Initial start failed (possibly stale containers). Stopping and retrying..."
            supabase stop >/dev/null 2>&1 || true
            supabase start 2>&1 || fail "Failed to start Supabase. Run: bash scripts/supabase_setup.sh"
        fi
    else
        ok "Supabase is running"
    fi

    cd "$PROJECT_ROOT"

    info "Building and starting all services in Docker..."
    docker compose up --build -d

    info "Waiting for backend to be healthy (up to 60s)..."
    for i in $(seq 1 30); do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            ok "Backend is healthy"
            break
        fi
        if [ "$i" -eq 30 ]; then
            warn "Backend health check timed out. Check: docker compose logs backend"
        fi
        sleep 2
    done

    echo ""
    ok "All services running in Docker."
    info "  dao_service: http://localhost:8001  (Swagger: http://localhost:8001/docs)"
    info "  backend:     http://localhost:8000  (Swagger: http://localhost:8000/docs)"
    info "  frontend:    http://localhost:3000"
    echo ""
    info "Useful commands:"
    info "  docker compose logs -f           — tail all logs"
    info "  docker compose logs -f backend   — tail backend only"
    info "  docker compose down              — stop all services"
}

# -- Main --------------------------------------------------------------------

case "${1:-}" in
    setup)  cmd_setup  ;;
    test)   cmd_test   ;;
    run)    cmd_run    ;;
    build)  cmd_build  ;;
    deploy) cmd_deploy ;;
    *)
        echo "Usage: ./scripts/conv_agent.sh [setup|test|run|build|deploy]"
        echo ""
        echo "Subcommands:"
        echo "  setup   Install Python + Node dependencies"
        echo "  test    Run conv_agent pytest suite (unit + integration if DEEPGRAM_API_KEY set)"
        echo "  run     Start backend dev server (uvicorn)"
        echo "  build   Build frontend for production"
        echo "  deploy  Start dao_service + backend + frontend dev servers"
        exit 1
        ;;
esac
