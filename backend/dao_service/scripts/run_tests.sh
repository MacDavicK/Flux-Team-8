#!/usr/bin/env bash
# ============================================================
# Flux DAO Service — Test Runner
#
# Runs unit tests, integration tests, or both with coverage.
#
# Usage (from project root):
#   bash backend/dao_service/scripts/run_tests.sh unit         # Unit tests only (no DB needed)
#   bash backend/dao_service/scripts/run_tests.sh integration  # Integration tests (needs Supabase)
#   bash backend/dao_service/scripts/run_tests.sh all          # Both with coverage report
#   bash backend/dao_service/scripts/run_tests.sh              # Defaults to 'all'
# ============================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}ℹ  $1${NC}"; }
success() { echo -e "${GREEN}✓  $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠  $1${NC}"; }
error()   { echo -e "${RED}✗  $1${NC}"; }

MODE="${1:-all}"

# Determine project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

cd "$BACKEND_DIR"

echo ""
echo "========================================"
echo "  Flux DAO Service — Test Runner ($MODE)"
echo "========================================"
echo ""

# --- Check virtual environment ---
if [ -z "${VIRTUAL_ENV:-}" ]; then
    error "No virtual environment is activated."
    error "Activate your venv first: source venv/bin/activate"
    exit 1
fi

# --- Check Supabase for integration tests ---
check_supabase() {
    SUPABASE_CONTAINER="supabase_db_Flux-Team-8"
    if ! docker ps --format '{{.Names}}' | grep -q "$SUPABASE_CONTAINER"; then
        error "Supabase database container is not running ($SUPABASE_CONTAINER)."
        error "Start it with: cd $PROJECT_ROOT && supabase start"
        error "Or run: bash backend/dao_service/scripts/setup_dao.sh"
        exit 1
    fi
    success "Supabase database is running"

    # Truncate tables for clean state
    info "Truncating tables for clean test state..."
    docker exec "$SUPABASE_CONTAINER" psql -U postgres -c "TRUNCATE users CASCADE;" >/dev/null 2>&1
    success "Tables truncated"
}

EXIT_CODE=0

case "$MODE" in
    unit)
        info "Running unit tests..."
        echo ""
        pytest dao_service/tests/unit/ -v --tb=short || EXIT_CODE=$?
        ;;
    integration)
        check_supabase
        info "Running integration tests..."
        echo ""
        pytest dao_service/tests/integration/ -v --tb=short || EXIT_CODE=$?
        ;;
    all)
        info "Running unit tests..."
        echo ""
        pytest dao_service/tests/unit/ -v --tb=short || EXIT_CODE=$?

        if [ $EXIT_CODE -ne 0 ]; then
            error "Unit tests failed. Skipping integration tests."
        else
            echo ""
            check_supabase
            info "Running full suite with coverage..."
            echo ""
            pytest dao_service/tests/ -v --cov=dao_service --cov-report=term-missing --tb=short || EXIT_CODE=$?
        fi
        ;;
    *)
        error "Unknown mode: $MODE"
        echo "Usage: bash backend/dao_service/scripts/run_tests.sh [unit|integration|all]"
        exit 1
        ;;
esac

echo ""
echo "========================================"
if [ $EXIT_CODE -eq 0 ]; then
    success "All tests passed!"
else
    error "Some tests failed (exit code: $EXIT_CODE)"
fi
echo "========================================"

exit $EXIT_CODE
