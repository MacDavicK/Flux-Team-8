#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Flux Demo Seed — Hosted Supabase
# Usage: bash backend/scripts/seed-hosted.sh
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${REPO_ROOT}/backend/.env"

# ─── Load env ──────────────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: backend/.env not found. Copy backend/.env.example and fill it in."
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# ─── Validate required vars ────────────────────────────────────
missing=()
for var in SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY DATABASE_URL; do
    [[ -z "${!var:-}" ]] && missing+=("$var")
done

if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: missing required env vars in backend/.env:"
    printf '  - %s\n' "${missing[@]}"
    exit 1
fi

echo "→ Supabase URL: $SUPABASE_URL"
echo "→ Database URL: ${DATABASE_URL//:*@/:***@}"

# ─── Check Python deps ─────────────────────────────────────────
echo "→ Checking Python dependencies..."
python3 -c "import supabase" 2>/dev/null || {
    echo "ERROR: supabase package not installed."
    echo "  Run: pip install 'supabase>=2.0.0'"
    exit 1
}
python3 -c "import asyncpg" 2>/dev/null || {
    echo "ERROR: asyncpg package not installed."
    echo "  Run: pip install 'asyncpg>=0.29.0'"
    exit 1
}

# ─── Run seed ──────────────────────────────────────────────────
echo "→ Running seed script..."
python3 "${SCRIPT_DIR}/seed_hosted.py"
