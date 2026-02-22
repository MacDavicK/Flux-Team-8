#!/usr/bin/env bash
# ============================================================
# Flux — Development Environment Setup (macOS / Linux)
# Installs frontend and backend dependencies, copies .env files,
# and validates that required tools (Node.js, Python) are present.
# For Supabase setup (applies all migrations + canonical seed), run:
# bash scripts/supabase_setup.sh
# Usage:  bash scripts/setup.sh
# ============================================================

set -e  # Exit immediately on any error

# ---------- Colored output helpers ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---------- Resolve project root ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo ""
echo "=============================="
echo "  Flux — Project Setup"
echo "=============================="
echo ""

# ---------- 1. Check Node.js >= 18 ----------
if ! command -v node &> /dev/null; then
  error "Node.js is not installed. Please install Node.js 18+ from https://nodejs.org"
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
  error "Node.js 18+ is required (found v$(node -v)). Please upgrade."
fi
info "Node.js $(node -v) detected"

# ---------- 2. Check Python >= 3.11 ----------
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
  PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
  PYTHON_CMD="python"
else
  error "Python is not installed. Please install Python 3.11+ from https://python.org"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
  error "Python 3.11+ is required (found $PYTHON_VERSION). Please upgrade."
fi
info "Python $PYTHON_VERSION detected"

# ---------- 3. Frontend setup ----------
echo ""
echo "--- Frontend Setup ---"

cd "$PROJECT_ROOT/frontend"
npm install
info "Frontend dependencies installed"

if [ ! -f .env ]; then
  cp .env.example .env
  info "Created frontend/.env from .env.example"
else
  warn "frontend/.env already exists — skipping copy"
fi

# ---------- 4. Backend setup ----------
echo ""
echo "--- Backend Setup ---"

cd "$PROJECT_ROOT/backend"

if [ ! -f requirements.txt ]; then
  warn "backend/requirements.txt not found — skipping Python dependency install"
else
  $PYTHON_CMD -m venv venv
  # Activate venv (POSIX-compatible)
  source venv/bin/activate
  pip install --upgrade pip --quiet
  pip install -r requirements.txt
  info "Backend dependencies installed in venv"
fi

if [ ! -f .env ]; then
  cp .env.example .env
  info "Created backend/.env from .env.example"
else
  warn "backend/.env already exists — skipping copy"
fi

# ---------- 5. Done ----------
cd "$PROJECT_ROOT"

echo ""
echo "=============================="
echo -e "  ${GREEN}Setup complete!${NC}"
echo "=============================="
echo ""
echo "Next steps:"
echo "  1. Set up Supabase:  bash scripts/supabase_setup.sh"
echo "     (applies all SQL migrations in supabase/migrations/)"
echo "  2. Fill in API keys in backend/.env"
echo "  3. Start frontend:   cd frontend && npm run dev"
echo "  4. Start backend:    cd backend && source venv/bin/activate && make dev"
echo "  5. Open http://localhost:5173 in your browser"
echo ""
