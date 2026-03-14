#!/usr/bin/env bash
# =============================================================================
# Flux Backend — Dev environment teardown
#
# Usage:
#   bash dev-end.sh          # stop all containers, prune build cache & volumes
#   bash dev-end.sh --soft   # stop containers only (keep volumes & build cache)
#
# What this script does:
#   1. Stop & remove all Docker Compose containers (all profiles)
#   2. Remove anonymous/named volumes created by Compose (unless --soft)
#   3. Prune dangling Docker build cache (unless --soft)
#   4. Remove the .venv directory if present
#   5. Remove Python __pycache__ and .pytest_cache directories
#
# What this script does NOT touch:
#   • .env  — your credentials are preserved
#   • Source code
#   • Named Docker volumes shared across projects
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── colours ──────────────────────────────────────────────────────────────────
BOLD="\033[1m"
DIM="\033[2m"
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
RED="\033[31m"
RESET="\033[0m"

header()  { echo -e "\n${BOLD}${CYAN}$*${RESET}"; }
info()    { echo -e "  ${DIM}$*${RESET}"; }
success() { echo -e "  ${GREEN}✔  $*${RESET}"; }
warn()    { echo -e "  ${YELLOW}⚠  $*${RESET}"; }
err()     { echo -e "  ${RED}✖  $*${RESET}"; }
step()    { echo -e "\n${BOLD}${CYAN}┌─ $* ${RESET}"; }

# ── arg parsing ───────────────────────────────────────────────────────────────
SOFT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --soft)  SOFT=true; shift ;;
        -h|--help)
            grep '^#' "$0" | head -20 | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *)
            err "Unknown argument: $1"; exit 1 ;;
    esac
done

# =============================================================================
# MAIN
# =============================================================================

echo -e "\n${BOLD}╔══════════════════════════════════════════════╗"
echo -e "║         Flux Backend — Teardown              ║"
echo -e "╚══════════════════════════════════════════════╝${RESET}"
$SOFT && warn "--soft: volumes and build cache will be kept."

# ── Step 1 — Docker containers ───────────────────────────────────────────────
step "Step 1 — Stop & remove Docker containers"

if ! command -v docker &>/dev/null; then
    warn "docker not found — skipping container teardown."
elif ! docker info &>/dev/null 2>&1; then
    warn "Docker daemon is not running — skipping container teardown."
else
    # Bring down all profiles so ngrok container is also stopped
    down_flags=(--remove-orphans)
    if ! $SOFT; then
        down_flags+=(--volumes)
    fi

    if docker compose --project-directory "$REPO_ROOT" ps --quiet 2>/dev/null | grep -q .; then
        info "Stopping containers..."
        docker compose \
            --project-directory "$REPO_ROOT" \
            --profile ngrok \
            down "${down_flags[@]}"
        success "Containers stopped and removed."
    else
        info "No running containers found for this project."
    fi

    # ── Step 2 — Prune build cache ────────────────────────────────────────────
    step "Step 2 — Docker build cache"
    if ! $SOFT; then
        info "Pruning dangling build cache..."
        docker builder prune --force --filter type=exec.cachemount 2>/dev/null || \
            docker builder prune --force 2>/dev/null || true
        success "Build cache pruned."
    else
        info "Skipping build cache prune (--soft)."
    fi
fi

# ── Step 3 — Python virtual environment ──────────────────────────────────────
step "Step 3 — Python virtual environment"

if [[ -d "$REPO_ROOT/.venv" ]]; then
    rm -rf "$REPO_ROOT/.venv"
    success ".venv removed."
else
    info "No .venv directory found."
fi

# ── Step 4 — Python caches ───────────────────────────────────────────────────
step "Step 4 — Python caches"

cache_count=0
while IFS= read -r -d '' d; do
    rm -rf "$d"
    (( cache_count++ )) || true
done < <(find "$REPO_ROOT" \
    \( -name "__pycache__" -o -name ".pytest_cache" -o -name "*.pyc" \) \
    -not -path "$REPO_ROOT/.venv/*" \
    -print0)

if [[ $cache_count -gt 0 ]]; then
    success "Removed ${cache_count} cache file(s)/director(ies)."
else
    info "No Python cache files found."
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗"
echo -e "║   Teardown complete!                         ║"
echo -e "╚══════════════════════════════════════════════╝${RESET}"
info "Your .env file has been preserved."
info "Run ./dev-start.sh to bring the stack back up."
echo
