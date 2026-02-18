#!/usr/bin/env bash
# ============================================================
# Flux DAO Service — Environment Setup Script
#
# Checks prerequisites, installs dependencies, and verifies
# database connectivity for the DAO service.
#
# Prerequisites:
#   - Python 3.11+ with a project-level virtual environment activated
#   - Docker Desktop running
#   - Supabase running locally (port 54322)
#
# Usage:
#   bash scripts/setup_backend.sh
# ============================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}ℹ  $1${NC}"; }
success() { echo -e "${GREEN}✓  $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠  $1${NC}"; }
error()   { echo -e "${RED}✗  $1${NC}"; }

echo ""
echo "========================================"
echo "  Flux DAO Service — Environment Setup"
echo "========================================"
echo ""

# --- Check Python 3.11+ ---
info "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>/dev/null | grep -oP '\d+\.\d+' | head -1)
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ -z "$PYTHON_VERSION" ] || [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    error "Python 3.11+ is required. Found: $(python3 --version 2>/dev/null || echo 'not found')"
    error "Install Python 3.11+: https://www.python.org/downloads/"
    exit 1
fi
success "Python $PYTHON_VERSION detected"

# --- Check virtual environment is activated ---
info "Checking virtual environment..."
if [ -z "${VIRTUAL_ENV:-}" ]; then
    error "No virtual environment is activated."
    error "Create and activate one first:"
    error "  python3 -m venv venv"
    error "  source venv/bin/activate"
    exit 1
fi
success "Virtual environment active: $VIRTUAL_ENV"

# --- Check Docker Desktop ---
info "Checking Docker Desktop..."
if ! docker info >/dev/null 2>&1; then
    error "Docker Desktop is not running."
    error "Please start Docker Desktop and try again."
    error "  macOS: Open Docker.app from Applications"
    error "  Linux: sudo systemctl start docker"
    exit 1
fi
success "Docker Desktop is running"

# --- Check Supabase ---
info "Checking Supabase local instance..."
SUPABASE_CONTAINER="supabase_db_Flux-Team-8"

if docker ps --format '{{.Names}}' | grep -q "$SUPABASE_CONTAINER"; then
    success "Supabase database container is running ($SUPABASE_CONTAINER)"
else
    warn "Supabase container ($SUPABASE_CONTAINER) is not running."
    info "Attempting to start Supabase..."

    # Try to find project root (where supabase/ directory is)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

    if [ -f "$PROJECT_ROOT/supabase/config.toml" ]; then
        cd "$PROJECT_ROOT"
        if supabase start 2>/dev/null; then
            success "Supabase started successfully"
        else
            error "Failed to start Supabase automatically."
            error "Please start it manually:"
            error "  cd $PROJECT_ROOT"
            error "  supabase start"
            error ""
            error "If Supabase CLI is not installed:"
            error "  brew install supabase/tap/supabase"
            exit 1
        fi
    else
        error "Cannot find supabase/config.toml in project root."
        error "Please start Supabase manually:"
        error "  cd <project-root>"
        error "  supabase start"
        exit 1
    fi
fi

# --- Verify database connectivity ---
info "Verifying database connectivity..."
if docker exec "$SUPABASE_CONTAINER" psql -U postgres -c "SELECT 1" >/dev/null 2>&1; then
    success "Database is reachable on port 54322"
else
    error "Cannot connect to PostgreSQL in $SUPABASE_CONTAINER."
    error "The container is running but the database is not responding."
    error "Try: docker logs $SUPABASE_CONTAINER"
    exit 1
fi

# --- Install dependencies ---
info "Installing production dependencies..."
pip install -q -r backend/requirements.txt 2>/dev/null || pip install -q -r requirements.txt 2>/dev/null
success "Production dependencies installed"

info "Installing development dependencies..."
pip install -q -r backend/requirements-dev.txt 2>/dev/null || pip install -q -r requirements-dev.txt 2>/dev/null
success "Development dependencies installed"

# --- Create .env if missing ---
BACKEND_DIR="$PROJECT_ROOT/backend"
if [ ! -f "$BACKEND_DIR/.env" ]; then
    info "Creating .env from template..."
    cat > "$BACKEND_DIR/.env" << 'EOF'
# Flux DAO Service — Local Development Environment
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:54322/postgres
SERVICE_API_KEYS=["goal-planner-key-abc","scheduler-key-def","observer-key-ghi"]
EOF
    success ".env file created at $BACKEND_DIR/.env"
else
    success ".env file already exists"
fi

echo ""
echo "========================================"
success "Environment setup complete!"
echo "========================================"
echo ""
info "Next steps:"
echo "  1. Run unit tests:        cd backend && make test-unit"
echo "  2. Run integration tests: cd backend && make test-integration"
echo "  3. Start dev server:      cd backend && make dev"
echo "  4. Open Swagger UI:       http://localhost:8000/docs"
echo ""
