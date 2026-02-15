#!/usr/bin/env bash
# ============================================================
# Flux DAO Service — Build, Deploy & Test Pipeline
#
# Full orchestration script that:
#   1. Checks prerequisites (Docker, Supabase, venv)
#   2. Installs dependencies
#   3. Runs unit tests
#   4. Builds Docker image
#   5. Deploys container
#   6. Runs integration tests
#   7. Generates TEST_REPORT.md
#
# Usage:
#   bash scripts/build_and_test.sh
#   bash scripts/build_and_test.sh --cleanup    # Stop container after tests
# ============================================================

set -uo pipefail

# --- Configuration ---
CLEANUP=false
[ "${1:-}" = "--cleanup" ] && CLEANUP=true

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}ℹ  $1${NC}"; }
success() { echo -e "${GREEN}✓  $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠  $1${NC}"; }
error()   { echo -e "${RED}✗  $1${NC}"; }
header()  { echo -e "\n${BOLD}═══ $1 ═══${NC}\n"; }

# --- Paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
REPORT_FILE="$BACKEND_DIR/TEST_REPORT.md"
RESULTS_DIR="$BACKEND_DIR/test-results"
SUPABASE_CONTAINER="supabase_db_Flux-Team-8"

mkdir -p "$RESULTS_DIR"

# Track results for the report
STEP_RESULTS=()
UNIT_PASSED=0
UNIT_FAILED=0
UNIT_TOTAL=0
INTEG_PASSED=0
INTEG_FAILED=0
INTEG_TOTAL=0
PIPELINE_START=$(date +%s)

record_step() {
    local step_name="$1"
    local status="$2"  # PASS or FAIL
    STEP_RESULTS+=("$status|$step_name")
}

# ============================================================
# STEP 1: Check Docker Desktop
# ============================================================
header "Step 1: Check Docker Desktop"
if docker info >/dev/null 2>&1; then
    success "Docker Desktop is running"
    record_step "Docker Desktop check" "PASS"
else
    error "Docker Desktop is NOT running."
    error ""
    error "How to fix:"
    error "  macOS: Open Docker.app from Applications"
    error "  Linux: sudo systemctl start docker"
    error ""
    error "Then re-run this script."
    record_step "Docker Desktop check" "FAIL"
    exit 1
fi

# ============================================================
# STEP 2: Check/Start Supabase
# ============================================================
header "Step 2: Check Supabase"
if docker ps --format '{{.Names}}' | grep -q "$SUPABASE_CONTAINER"; then
    success "Supabase database container is running"
    record_step "Supabase check" "PASS"
else
    warn "Supabase container ($SUPABASE_CONTAINER) is not running."
    info "Attempting to start Supabase..."

    cd "$PROJECT_ROOT"
    if supabase start 2>&1; then
        success "Supabase started successfully"
        record_step "Supabase check" "PASS"
    else
        error "Failed to start Supabase."
        error ""
        error "How to fix:"
        error "  1. Install Supabase CLI: brew install supabase/tap/supabase"
        error "  2. Navigate to project root: cd $PROJECT_ROOT"
        error "  3. Start Supabase: supabase start"
        error "  4. Run setup script: bash scripts/supabase_setup.sh"
        error ""
        error "Then re-run this script."
        record_step "Supabase check" "FAIL"
        exit 1
    fi
fi

# ============================================================
# STEP 3: Verify DB connectivity
# ============================================================
header "Step 3: Verify Database Connectivity"
if docker exec "$SUPABASE_CONTAINER" psql -U postgres -c "SELECT 1" >/dev/null 2>&1; then
    success "PostgreSQL is reachable on port 54322"
    record_step "DB connectivity" "PASS"
else
    error "Cannot connect to PostgreSQL in $SUPABASE_CONTAINER."
    error ""
    error "The container is running but the database is not responding."
    error "Check container logs: docker logs $SUPABASE_CONTAINER"
    record_step "DB connectivity" "FAIL"
    exit 1
fi

# ============================================================
# STEP 4: Setup dependencies
# ============================================================
header "Step 4: Install Dependencies"
if [ -z "${VIRTUAL_ENV:-}" ]; then
    error "No virtual environment is activated."
    error ""
    error "How to fix:"
    error "  python3 -m venv venv"
    error "  source venv/bin/activate"
    error "  Then re-run this script."
    record_step "Dependencies" "FAIL"
    exit 1
fi

cd "$BACKEND_DIR"
info "Installing production + dev dependencies..."
pip install -q -r requirements.txt && pip install -q -r requirements-dev.txt
if [ $? -eq 0 ]; then
    success "Dependencies installed"
    record_step "Dependencies" "PASS"
else
    error "Failed to install dependencies."
    record_step "Dependencies" "FAIL"
    exit 1
fi

# ============================================================
# STEP 5: Run unit tests
# ============================================================
header "Step 5: Run Unit Tests"
UNIT_OUTPUT=$(pytest tests/unit/ -v --tb=short --junitxml="$RESULTS_DIR/unit.xml" 2>&1) || true
UNIT_EXIT=$?

# Parse results from output
UNIT_PASSED=$(echo "$UNIT_OUTPUT" | grep -oP '\d+ passed' | grep -oP '\d+' || echo "0")
UNIT_FAILED=$(echo "$UNIT_OUTPUT" | grep -oP '\d+ failed' | grep -oP '\d+' || echo "0")
UNIT_TOTAL=$((UNIT_PASSED + UNIT_FAILED))

echo "$UNIT_OUTPUT"

if [ $UNIT_EXIT -eq 0 ]; then
    success "Unit tests: $UNIT_PASSED passed"
    record_step "Unit tests ($UNIT_PASSED/$UNIT_TOTAL passed)" "PASS"
else
    error "Unit tests: $UNIT_FAILED failed out of $UNIT_TOTAL"
    record_step "Unit tests ($UNIT_PASSED/$UNIT_TOTAL passed)" "FAIL"
    warn "Skipping Docker build due to unit test failures."
    # Continue to report generation
fi

# ============================================================
# STEP 6: Build Docker image
# ============================================================
if [ $UNIT_EXIT -eq 0 ]; then
    header "Step 6: Build Docker Image"
    if docker build -t flux-dao-service:latest "$BACKEND_DIR" 2>&1; then
        success "Docker image built: flux-dao-service:latest"
        record_step "Docker build" "PASS"
    else
        error "Docker build failed."
        error ""
        error "Check the Dockerfile and build output above."
        error "Common fixes:"
        error "  - Verify requirements.txt has no syntax errors"
        error "  - Ensure dao_service/ directory exists"
        record_step "Docker build" "FAIL"
        # Continue to report
    fi
fi

# ============================================================
# STEP 7: Deploy container
# ============================================================
CONTAINER_DEPLOYED=false
if [ $UNIT_EXIT -eq 0 ]; then
    header "Step 7: Deploy Container"

    # Stop existing container if running
    docker-compose -f "$BACKEND_DIR/docker-compose.dao-service.yml" down 2>/dev/null || true

    if docker-compose -f "$BACKEND_DIR/docker-compose.dao-service.yml" up -d 2>&1; then
        success "Container deployed: flux-dao-service"
        record_step "Container deployment" "PASS"
        CONTAINER_DEPLOYED=true
    else
        error "Failed to deploy container."
        error ""
        error "Check docker-compose output above."
        error "Try: docker-compose -f backend/docker-compose.dao-service.yml logs"
        record_step "Container deployment" "FAIL"
    fi
fi

# ============================================================
# STEP 8: Wait for health check
# ============================================================
if [ "$CONTAINER_DEPLOYED" = true ]; then
    header "Step 8: Health Check"
    info "Waiting for service to be healthy..."

    HEALTH_OK=false
    for i in $(seq 1 15); do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            HEALTH_OK=true
            break
        fi
        sleep 2
        echo -n "."
    done
    echo ""

    if [ "$HEALTH_OK" = true ]; then
        success "Service is healthy: http://localhost:8000/health"
        record_step "Health check" "PASS"
    else
        error "Service did not become healthy within 30 seconds."
        error ""
        error "Container logs:"
        docker logs flux-dao-service 2>&1 | tail -30
        record_step "Health check" "FAIL"
    fi
fi

# ============================================================
# STEP 9: Run integration tests
# ============================================================
header "Step 9: Run Integration Tests"
info "Truncating tables for clean test state..."
docker exec "$SUPABASE_CONTAINER" psql -U postgres -c "TRUNCATE users CASCADE;" >/dev/null 2>&1

INTEG_OUTPUT=$(pytest tests/integration/ -v --tb=short --junitxml="$RESULTS_DIR/integration.xml" 2>&1) || true
INTEG_EXIT=$?

# Parse results
INTEG_PASSED=$(echo "$INTEG_OUTPUT" | grep -oP '\d+ passed' | grep -oP '\d+' || echo "0")
INTEG_FAILED=$(echo "$INTEG_OUTPUT" | grep -oP '\d+ failed' | grep -oP '\d+' || echo "0")
INTEG_TOTAL=$((INTEG_PASSED + INTEG_FAILED))

echo "$INTEG_OUTPUT"

if [ $INTEG_EXIT -eq 0 ]; then
    success "Integration tests: $INTEG_PASSED passed"
    record_step "Integration tests ($INTEG_PASSED/$INTEG_TOTAL passed)" "PASS"
else
    error "Integration tests: $INTEG_FAILED failed out of $INTEG_TOTAL"
    record_step "Integration tests ($INTEG_PASSED/$INTEG_TOTAL passed)" "FAIL"
fi

# ============================================================
# STEP 10: Generate Test Report
# ============================================================
header "Step 10: Generate Test Report"

PIPELINE_END=$(date +%s)
PIPELINE_DURATION=$((PIPELINE_END - PIPELINE_START))
TOTAL_PASSED=$((UNIT_PASSED + INTEG_PASSED))
TOTAL_FAILED=$((UNIT_FAILED + INTEG_FAILED))
TOTAL_TESTS=$((TOTAL_PASSED + TOTAL_FAILED))

if [ $TOTAL_FAILED -eq 0 ] && [ $UNIT_EXIT -eq 0 ] && [ ${INTEG_EXIT:-1} -eq 0 ]; then
    OVERALL_STATUS="✅ ALL TESTS PASSED"
else
    OVERALL_STATUS="❌ SOME TESTS FAILED"
fi

cat > "$REPORT_FILE" << EOF
# Flux DAO Service — Test Report

**Generated:** $(date -u '+%Y-%m-%d %H:%M:%S UTC')
**Pipeline Duration:** ${PIPELINE_DURATION}s
**Overall Status:** $OVERALL_STATUS

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | $TOTAL_TESTS |
| Passed | $TOTAL_PASSED |
| Failed | $TOTAL_FAILED |
| Unit Tests | $UNIT_PASSED / $UNIT_TOTAL passed |
| Integration Tests | $INTEG_PASSED / $INTEG_TOTAL passed |

## Pipeline Steps

| Step | Status |
|------|--------|
EOF

for result in "${STEP_RESULTS[@]}"; do
    status=$(echo "$result" | cut -d'|' -f1)
    step=$(echo "$result" | cut -d'|' -f2)
    if [ "$status" = "PASS" ]; then
        echo "| $step | ✅ Pass |" >> "$REPORT_FILE"
    else
        echo "| $step | ❌ Fail |" >> "$REPORT_FILE"
    fi
done

cat >> "$REPORT_FILE" << EOF

## Environment

| Component | Version/Status |
|-----------|---------------|
| Python | $(python3 --version 2>&1) |
| pytest | $(pytest --version 2>&1 | head -1) |
| PostgreSQL | Supabase local (port 54322) |
| Docker | $(docker --version 2>&1) |
| OS | $(uname -s) $(uname -m) |

## Test Configuration

- **Database:** Supabase PostgreSQL (localhost:54322)
- **Test Isolation:** Per-test truncation (TRUNCATE users CASCADE)
- **Async Framework:** pytest-asyncio with session-scoped event loop
- **API Client:** httpx AsyncClient with ASGITransport

## Files Modified

- \`backend/dao_service/\` — Application code (renamed from \`app/\`)
- \`backend/tests/conftest.py\` — PostgreSQL test fixtures
- \`backend/Dockerfile\` — Container image
- \`backend/docker-compose.dao-service.yml\` — Service deployment

---
*Report generated by \`scripts/build_and_test.sh\`*
EOF

success "Test report generated: $REPORT_FILE"

# ============================================================
# STEP 11: Cleanup (optional)
# ============================================================
if [ "$CLEANUP" = true ] && [ "$CONTAINER_DEPLOYED" = true ]; then
    header "Step 11: Cleanup"
    docker-compose -f "$BACKEND_DIR/docker-compose.dao-service.yml" down 2>/dev/null
    success "Container stopped and removed"
fi

# ============================================================
# Final Summary
# ============================================================
echo ""
echo "========================================"
echo -e "${BOLD}  Pipeline Summary${NC}"
echo "========================================"
echo ""

for result in "${STEP_RESULTS[@]}"; do
    status=$(echo "$result" | cut -d'|' -f1)
    step=$(echo "$result" | cut -d'|' -f2)
    if [ "$status" = "PASS" ]; then
        success "$step"
    else
        error "$step"
    fi
done

echo ""
echo -e "  Total: ${GREEN}$TOTAL_PASSED passed${NC}, ${RED}$TOTAL_FAILED failed${NC} (${PIPELINE_DURATION}s)"
echo ""

if [ "$CONTAINER_DEPLOYED" = true ] && [ "$CLEANUP" = false ]; then
    info "DAO service is running at http://localhost:8000"
    info "Swagger UI: http://localhost:8000/docs"
    info "To stop: docker-compose -f backend/docker-compose.dao-service.yml down"
fi

echo ""

# Exit with appropriate code
if [ $TOTAL_FAILED -gt 0 ] || [ $UNIT_EXIT -ne 0 ] || [ ${INTEG_EXIT:-1} -ne 0 ]; then
    exit 1
fi
exit 0
