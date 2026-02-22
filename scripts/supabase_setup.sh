#!/usr/bin/env bash
# ============================================================
# Flux — Supabase Local Development Setup
# Checks prerequisites (Docker, Supabase CLI), starts the local
# Supabase stack, applies migrations, and seeds test data.
# Usage:  bash scripts/supabase_setup.sh
# ============================================================

set -e

# ---------- Flags ----------
AUTO_YES=false
if [ "${1:-}" = "--yes" ] || [ "${1:-}" = "-y" ]; then
  AUTO_YES=true
fi

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

CONTAINER_NAME="supabase_db_Flux-Team-8"

if supabase status &> /dev/null 2>&1; then
  DB_RUNNING="$(docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null || echo "false")"
  if [ "$DB_RUNNING" = "true" ]; then
    info "Supabase is already running"
  else
    warn "Supabase is partially running but DB container is not healthy. Restarting stack..."
    supabase stop >/dev/null 2>&1 || true
    supabase start
    info "Supabase local development stack restarted"
  fi
else
  echo "Starting Supabase (first run downloads ~2-3 GB of Docker images)..."
  if supabase start; then
    info "Supabase local development stack started"
  else
    warn "Supabase start failed (likely partial previous state). Forcing stop + retry..."
    supabase stop >/dev/null 2>&1 || true

    # Remove stale Supabase containers that can cause name-collision errors
    STALE_CONTAINERS="$(docker ps -a --format '{{.Names}}' | awk '/^supabase_.*_Flux-Team-8$/ {print $1}')"
    if [ -n "$STALE_CONTAINERS" ]; then
      echo "$STALE_CONTAINERS" | xargs -I {} docker rm -f {} >/dev/null 2>&1 || true
      warn "Removed stale Supabase containers and retrying startup..."
    fi

    supabase start
    info "Supabase local development stack started (after recovery)"
  fi
fi

# ---------- 4. Apply migrations ----------
echo ""
echo "--- Applying Migrations ---"

# Apply every migration in lexical order (timestamp-prefixed files)
for migration in $(ls supabase/migrations/*.sql | sort); do
  migration_file="$(basename "$migration")"
  docker cp "$migration" "$CONTAINER_NAME:/tmp/$migration_file"
  docker exec "$CONTAINER_NAME" psql -v ON_ERROR_STOP=1 -U postgres -f "/tmp/$migration_file"
  info "Applied migration: $migration_file"
done
info "All database migrations applied"

# ---------- 5. Truncate + seed test data ----------
echo ""
echo "--- Seed Test Data (Truncate First) ---"

SEED_FILE="supabase/scripts/seed_test_data.sql"
TRUNCATE_FILE="supabase/scripts/truncate_tables.sql"

if [ ! -f "$SEED_FILE" ]; then
  warn "Seed file not found at $SEED_FILE — skipping"
elif [ ! -f "$TRUNCATE_FILE" ]; then
  warn "Truncate file not found at $TRUNCATE_FILE — skipping seed for safety"
else
  echo ""
  warn "About to TRUNCATE all canonical tables and reseed test data."
  warn "This will DELETE existing local data in Supabase."

  CONFIRM="no"
  if [ "$AUTO_YES" = true ]; then
    CONFIRM="yes"
  else
    printf "Type 'yes' to continue: "
    read -r CONFIRM
  fi

  if [ "$CONFIRM" = "yes" ]; then
    echo "Truncating tables..."
    docker cp "$TRUNCATE_FILE" "$CONTAINER_NAME:/tmp/truncate_tables.sql"
    docker exec "$CONTAINER_NAME" psql -v ON_ERROR_STOP=1 -U postgres -f /tmp/truncate_tables.sql

    echo "Seeding test data..."
    docker cp "$SEED_FILE" "$CONTAINER_NAME:/tmp/seed_test_data.sql"
    docker exec "$CONTAINER_NAME" psql -v ON_ERROR_STOP=1 -U postgres -f /tmp/seed_test_data.sql
    info "Tables truncated and test data seeded"
  else
    warn "Seed skipped by user confirmation."
  fi
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
echo "  bash scripts/supabase_setup.sh --yes  — Non-interactive truncate + seed"
echo "  See validation:   supabase/scripts/VALIDATION_CHECKLIST.md"
echo ""
echo "Studio:  http://127.0.0.1:54323"
echo "API:     http://127.0.0.1:54321/rest/v1"
echo ""
