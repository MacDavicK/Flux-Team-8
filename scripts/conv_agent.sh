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

# -- Load backend .env (if present) -----------------------------------------

ENV_FILE="$PROJECT_ROOT/backend/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
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

    cd "$PROJECT_ROOT"
    python3 -m pytest backend/conv_agent/tests/ -v --tb=short -k "not integration"

    if [ $? -eq 0 ]; then
        ok "Unit tests passed"
    else
        fail "Some unit tests failed"
    fi

    # Run integration tests if DEEPGRAM_API_KEY is set
    if [ -n "${DEEPGRAM_API_KEY:-}" ]; then
        info "DEEPGRAM_API_KEY detected -- running integration tests..."
        python3 -m pytest backend/conv_agent/tests/ -v --tb=short -m integration
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
    info "Starting full stack (dao_service + backend + frontend)..."

    # Start dao_service on port 8001
    info "Starting dao_service on port 8001..."
    cd "$PROJECT_ROOT/backend"
    DAO_PORT=8001 uvicorn dao_service.main:app --host 0.0.0.0 --port 8001 &
    DAO_PID=$!
    ok "dao_service starting (PID: $DAO_PID)"

    # Wait for dao_service readiness (poll /ready up to 10s)
    for i in $(seq 1 10); do
        if curl -sf http://localhost:8001/ready > /dev/null 2>&1; then
            info "dao_service ready"
            break
        fi
        if [ "$i" -eq 10 ]; then
            warn "dao_service readiness check timed out (may still be starting)"
        fi
        sleep 1
    done

    # Start main app on port 8080 (avoids conflict with Docker on 8000)
    info "Starting backend on port 8080..."
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8080 &
    BACKEND_PID=$!
    ok "Backend started (PID: $BACKEND_PID)"

    # Start frontend dev server (VITE_API_BASE tells conv_agent API client where backend lives)
    info "Starting frontend dev server..."
    cd "$PROJECT_ROOT/frontend"
    VITE_API_BASE=http://localhost:8080 npm run dev &
    FRONTEND_PID=$!
    ok "Frontend started (PID: $FRONTEND_PID)"

    echo ""
    info "All servers running. Press Ctrl+C to stop."
    info "  dao_service: http://localhost:8001"
    info "  backend:     http://localhost:8080"
    info "  frontend:    http://localhost:3000"

    # Trap Ctrl+C to clean up all processes
    trap "kill $DAO_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo ''; ok 'Servers stopped.'; exit 0" INT TERM

    # Wait for any process to exit
    wait
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
