#!/usr/bin/env bash
# ============================================================
# Flux — Supabase Local Development Setup
# Checks prerequisites (Docker, Supabase CLI), starts the local
# Supabase stack, applies migrations, and seeds test data.
# Usage:  bash scripts/supabase_setup.sh
# ============================================================

set -e

# ---------- Colored output helpers ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---------- Resolve project root ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo ""
echo "=============================="
echo "  Flux — Supabase Setup"
echo "=============================="
echo ""

# ---------- 1. Check Docker ----------
if ! command -v docker &> /dev/null; then
  error "Docker is not installed. Please install Docker Desktop from https://docs.docker.com/desktop/install/mac-install/"
fi

if ! docker info &> /dev/null 2>&1; then
  error "Docker Desktop is not running. Please start Docker Desktop and try again."
fi
info "Docker $(docker --version | awk '{print $3}' | tr -d ',') detected and running"

# ---------- 2. Check / Install Supabase CLI ----------
if ! command -v supabase &> /dev/null; then
  echo ""
  echo "--- Installing Supabase CLI ---"
  if command -v brew &> /dev/null; then
    brew install supabase/tap/supabase
    info "Supabase CLI installed via Homebrew"
  else
    error "Supabase CLI is not installed and Homebrew is not available. Install manually: https://supabase.com/docs/guides/local-development/cli/getting-started"
  fi
else
  info "Supabase CLI $(supabase --version 2>/dev/null) detected"
fi

# ---------- 3. Start Supabase ----------
echo ""
echo "--- Starting Supabase ---"

if supabase status &> /dev/null 2>&1; then
  info "Supabase is already running"
else
  echo "Starting Supabase (first run downloads ~2-3 GB of Docker images)..."
  supabase start
  info "Supabase local development stack started"
fi

# ---------- 4. Apply migrations ----------
echo ""
echo "--- Applying Migrations ---"

CONTAINER_NAME="supabase_db_Flux-Team-8"

# Migration script uses IF NOT EXISTS — safe to run every time
docker cp supabase/migrations/*_create_mvp_tables.sql "$CONTAINER_NAME:/tmp/create_mvp_tables.sql"
docker exec "$CONTAINER_NAME" psql -U postgres -f /tmp/create_mvp_tables.sql
info "Database migrations applied"

# ---------- 5. Seed test data ----------
echo ""
echo "--- Checking Test Data ---"

SEED_FILE="supabase/scripts/seed_test_data.sql"
USER_COUNT=$(docker exec "$CONTAINER_NAME" psql -U postgres -tAc "SELECT count(*) FROM users;")

if [ "$USER_COUNT" -gt 0 ]; then
  info "Test data already present ($USER_COUNT users) — skipping seed"
elif [ -f "$SEED_FILE" ]; then
  echo "Seeding test data..."
  docker cp "$SEED_FILE" "$CONTAINER_NAME:/tmp/seed_test_data.sql"
  docker exec "$CONTAINER_NAME" psql -U postgres -f /tmp/seed_test_data.sql
  info "Test data seeded"
else
  warn "Seed file not found at $SEED_FILE — skipping"
fi

# ---------- 6. Done ----------
echo ""
echo "=============================="
echo -e "  ${GREEN}Supabase setup complete!${NC}"
echo "=============================="
echo ""
supabase status
echo ""
echo "Useful commands:"
echo "  supabase status   — Show local URLs and keys"
echo "  supabase stop     — Stop all Supabase containers"
echo "  supabase start    — Restart (fast after first run)"
echo "  supabase db reset — Reset database and re-apply migrations"
echo ""
echo "Studio:  http://127.0.0.1:54323"
echo "API:     http://127.0.0.1:54321/rest/v1"
echo ""
