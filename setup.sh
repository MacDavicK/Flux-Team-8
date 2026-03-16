#!/usr/bin/env bash
# =============================================================================
# Flux — Full-stack dev environment setup
#
# Usage:
#   bash setup.sh
#
# Steps:
#   1. Dependency check  — Docker, python3, node, npm, uv
#   2. .env setup        — interactive prompts for all required variables
#   3. Migrations        — apply all SQL migrations (all files are idempotent)
#   4. Docker            — stop stale containers, then start the backend stack
#   5. Frontend          — install deps and start the dev server
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"
ENV_FILE="$BACKEND_DIR/.env"
ENV_EXAMPLE="$BACKEND_DIR/.env.example"
MIGRATIONS_DIR="$BACKEND_DIR/migrations"
FRONTEND_ENV_FILE="$FRONTEND_DIR/.env"
FRONTEND_ENV_EXAMPLE="$FRONTEND_DIR/.env.example"

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

# ── helpers ───────────────────────────────────────────────────────────────────

get_env() {
    local key="$1"
    local file="${2:-$ENV_FILE}"
    if [[ ! -f "$file" ]]; then echo ""; return; fi
    grep -E "^${key}=" "$file" \
        | head -1 \
        | sed -E "s/^${key}=//" \
        | sed 's/[[:space:]]*#.*//' \
        | tr -d '"'"'" \
        | tr -d '[:space:]'
}

set_env() {
    local key="$1"
    local value="$2"
    local file="${3:-$ENV_FILE}"
    if grep -qE "^${key}=" "$file" 2>/dev/null; then
        sed -i.bak -E "s|^${key}=.*|${key}=${value}|" "$file"
        rm -f "${file}.bak"
    else
        echo "${key}=${value}" >> "$file"
    fi
}

is_placeholder() {
    local v="$1"
    [[ -z "$v" || "$v" == \<* || "$v" == "your-"* || "$v" == "YOUR_"* || "$v" == "mailto:admin@"* || "$v" == "mailto:you@"* ]]
}

ask() {
    local prompt="$1"
    local default="${2:-}"
    local secret="${3:-}"
    local reply

    if [[ -n "$default" ]]; then
        echo -ne "  ${BOLD}${prompt}${RESET} ${DIM}[${default}]${RESET}: " >&2
    else
        echo -ne "  ${BOLD}${prompt}${RESET}: " >&2
    fi

    if [[ "$secret" == "secret" ]]; then
        IFS= read -rsp "" reply; echo
    else
        IFS= read -re reply
    fi

    if [[ -z "$reply" && -n "$default" ]]; then
        reply="$default"
    fi
    echo "$reply"
}

# =============================================================================
# STEP 1 — DEPENDENCY CHECK
# =============================================================================

check_deps() {
    step "Step 1 of 5 — Dependency check"

    local missing_hard=()
    local missing_soft=()

    command -v python3 &>/dev/null || missing_hard+=("python3")
    command -v node   &>/dev/null || missing_hard+=("node (https://nodejs.org)")
    command -v npm    &>/dev/null || missing_hard+=("npm   (bundled with Node.js)")

    if ! command -v docker &>/dev/null; then
        missing_hard+=("docker")
    elif ! docker info &>/dev/null 2>&1; then
        err "Docker is installed but the daemon is not running."
        err "Start Docker Desktop (or 'sudo systemctl start docker') and re-run."
        exit 1
    fi

    command -v uv &>/dev/null || missing_soft+=("uv  (fast Python package manager — https://docs.astral.sh/uv/)")

    if [[ ${#missing_hard[@]} -gt 0 ]]; then
        echo
        err "The following required tools are missing:"
        echo
        for item in "${missing_hard[@]}"; do
            err "  • $item"
        done
        echo
        err "Install instructions:"
        err "  docker  : https://docs.docker.com/get-docker/"
        err "  python3 : https://www.python.org/downloads/"
        err "  node/npm: https://nodejs.org"
        echo
        exit 1
    fi

    if [[ ${#missing_soft[@]} -gt 0 ]]; then
        echo
        warn "Optional tools not found (setup will continue):"
        for item in "${missing_soft[@]}"; do
            warn "  • $item"
        done
    fi

    success "All required dependencies found."
}

# =============================================================================
# STEP 2 — .env SETUP
# =============================================================================

gen_secret_key() {
    python3 -c "import secrets; print(secrets.token_hex(32))"
}

gen_vapid_keys() {
    python3 - <<'PYEOF'
import base64, sys
try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import ec
except ImportError:
    print("ERROR: cryptography package not available. Run: uv sync", file=sys.stderr)
    sys.exit(1)

priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
pub  = priv.public_key()

priv_raw = priv.private_numbers().private_value.to_bytes(32, "big")
priv_b64 = base64.urlsafe_b64encode(priv_raw).rstrip(b"=").decode()

pub_n   = pub.public_numbers()
pub_raw = b"\x04" + pub_n.x.to_bytes(32, "big") + pub_n.y.to_bytes(32, "big")
pub_b64 = base64.urlsafe_b64encode(pub_raw).rstrip(b"=").decode()

print(f"PRIVATE={priv_b64}")
print(f"PUBLIC={pub_b64}")
PYEOF
}

bootstrap_env() {
    if [[ ! -f "$ENV_FILE" ]]; then
        if [[ -f "$ENV_EXAMPLE" ]]; then
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            warn "backend/.env not found — created from backend/.env.example"
        else
            touch "$ENV_FILE"
            warn "backend/.env not found and no .env.example — created empty .env"
        fi
    else
        success "backend/.env file found."
    fi
}

setup_app() {
    header "── App ──────────────────────────────────────────"

    local key
    key="$(get_env SECRET_KEY)"
    if is_placeholder "$key"; then
        local generated
        generated="$(gen_secret_key)"
        set_env "SECRET_KEY" "$generated"
        success "SECRET_KEY auto-generated"
    else
        success "SECRET_KEY already set"
    fi

    local env
    env="$(get_env APP_ENV)"
    if is_placeholder "$env"; then
        local v
        v="$(ask "APP_ENV (development|production)" "development")"
        set_env "APP_ENV" "$v"
    else
        success "APP_ENV=${env}"
    fi
}

setup_supabase() {
    header "── Supabase / PostgreSQL ────────────────────────"
    info "Open your Supabase project → Settings → API to find these values."
    info "Dashboard: https://supabase.com/dashboard"
    echo

    local url anon_key service_key db_url

    url="$(get_env SUPABASE_URL)"
    if is_placeholder "$url"; then
        info "Find this at: Project Settings → API → Project URL"
        url="$(ask "SUPABASE_URL (https://<project>.supabase.co)")"
        set_env "SUPABASE_URL" "$url"
    else
        success "SUPABASE_URL already set"
    fi

    anon_key="$(get_env SUPABASE_ANON_KEY)"
    if is_placeholder "$anon_key"; then
        info "Find this at: Project Settings → API → anon / public key"
        anon_key="$(ask "SUPABASE_ANON_KEY" "" "secret")"
        set_env "SUPABASE_ANON_KEY" "$anon_key"
    else
        success "SUPABASE_ANON_KEY already set"
    fi

    service_key="$(get_env SUPABASE_SERVICE_ROLE_KEY)"
    if is_placeholder "$service_key"; then
        info "Find this at: Project Settings → API → service_role key (keep secret!)"
        service_key="$(ask "SUPABASE_SERVICE_ROLE_KEY" "" "secret")"
        set_env "SUPABASE_SERVICE_ROLE_KEY" "$service_key"
    else
        success "SUPABASE_SERVICE_ROLE_KEY already set"
    fi

    db_url="$(get_env DATABASE_URL)"
    if is_placeholder "$db_url"; then
        info "Find this at: Project Settings → Database → Connection string → URI"
        info "Use port 5432 (direct), NOT 6543 (pooler)."
        info "Format: postgresql+asyncpg://postgres:<password>@db.<project>.supabase.co:5432/postgres"
        db_url="$(ask "DATABASE_URL")"
        set_env "DATABASE_URL" "$db_url"
    else
        success "DATABASE_URL already set"
    fi
}

setup_openrouter() {
    header "── OpenRouter (LLM) ─────────────────────────────"
    info "Sign up and get your API key at: https://openrouter.ai/keys"
    echo

    local api_key
    api_key="$(get_env OPENROUTER_API_KEY)"
    if is_placeholder "$api_key"; then
        info "Get your key at: https://openrouter.ai/keys"
        api_key="$(ask "OPENROUTER_API_KEY (sk-or-...)" "" "secret")"
        set_env "OPENROUTER_API_KEY" "$api_key"
    else
        success "OPENROUTER_API_KEY already set"
    fi
}

setup_deepgram() {
    header "── Deepgram (Voice) ──────────────────────────────"
    info "Sign up and get your API key at: https://console.deepgram.com"
    echo

    local api_key
    api_key="$(get_env DEEPGRAM_API_KEY)"
    if is_placeholder "$api_key"; then
        info "Get your key at: https://console.deepgram.com → API Keys"
        api_key="$(ask "DEEPGRAM_API_KEY (leave blank to skip)" "" "secret")"
        [[ -n "$api_key" ]] && set_env "DEEPGRAM_API_KEY" "$api_key"
    else
        success "DEEPGRAM_API_KEY already set"
    fi
}

setup_langsmith() {
    header "── LangSmith (Agent Tracing) ────────────────────"
    info "Optional but recommended for debugging LangGraph agents."
    info "Sign up at: https://smith.langchain.com"
    echo

    local api_key project
    api_key="$(get_env LANGCHAIN_API_KEY)"
    if is_placeholder "$api_key"; then
        info "Get your key at: https://smith.langchain.com → Settings → API Keys"
        api_key="$(ask "LANGCHAIN_API_KEY (lsv2_... — leave blank to skip)" "" "secret")"
        [[ -n "$api_key" ]] && set_env "LANGCHAIN_API_KEY" "$api_key"
    else
        success "LANGCHAIN_API_KEY already set"
    fi

    project="$(get_env LANGCHAIN_PROJECT)"
    if is_placeholder "$project"; then
        local v
        v="$(ask "LANGCHAIN_PROJECT" "flux-development")"
        set_env "LANGCHAIN_PROJECT" "$v"
    else
        success "LANGCHAIN_PROJECT=${project}"
    fi
}

setup_sentry() {
    header "── Sentry (Error Tracking) ──────────────────────"
    info "Optional. Sign up at: https://sentry.io"
    echo

    local dsn
    dsn="$(get_env SENTRY_DSN)"
    if is_placeholder "$dsn"; then
        info "Find your DSN at: Sentry project → Settings → SDK Setup → DSN"
        dsn="$(ask "SENTRY_DSN (leave blank to skip)")"
        [[ -n "$dsn" ]] && set_env "SENTRY_DSN" "$dsn"
    else
        success "SENTRY_DSN already set"
    fi
}

setup_twilio() {
    header "── Twilio (WhatsApp / Voice / OTP) ─────────────"
    info "Sign up at: https://twilio.com"
    echo

    local sid token wa_from voice_from verify_sid webhook_url

    sid="$(get_env TWILIO_ACCOUNT_SID)"
    if is_placeholder "$sid"; then
        info "Find at: https://console.twilio.com → Account Info → Account SID"
        sid="$(ask "TWILIO_ACCOUNT_SID (AC...)")"
        set_env "TWILIO_ACCOUNT_SID" "$sid"
    else
        success "TWILIO_ACCOUNT_SID already set"
    fi

    token="$(get_env TWILIO_AUTH_TOKEN)"
    if is_placeholder "$token"; then
        info "Find at: https://console.twilio.com → Account Info → Auth Token"
        token="$(ask "TWILIO_AUTH_TOKEN" "" "secret")"
        set_env "TWILIO_AUTH_TOKEN" "$token"
    else
        success "TWILIO_AUTH_TOKEN already set"
    fi

    wa_from="$(get_env TWILIO_WHATSAPP_FROM)"
    if is_placeholder "$wa_from"; then
        info "WhatsApp sandbox: whatsapp:+14155238886"
        wa_from="$(ask "TWILIO_WHATSAPP_FROM" "whatsapp:+14155238886")"
        set_env "TWILIO_WHATSAPP_FROM" "$wa_from"
    else
        success "TWILIO_WHATSAPP_FROM already set"
    fi

    voice_from="$(get_env TWILIO_VOICE_FROM)"
    if is_placeholder "$voice_from"; then
        voice_from="$(ask "TWILIO_VOICE_FROM (+1...)")"
        set_env "TWILIO_VOICE_FROM" "$voice_from"
    else
        success "TWILIO_VOICE_FROM already set"
    fi

    verify_sid="$(get_env TWILIO_VERIFY_SERVICE_SID)"
    if is_placeholder "$verify_sid"; then
        info "Create a Verify service at: https://console.twilio.com → Verify → Services"
        verify_sid="$(ask "TWILIO_VERIFY_SERVICE_SID (VA...)")"
        set_env "TWILIO_VERIFY_SERVICE_SID" "$verify_sid"
    else
        success "TWILIO_VERIFY_SERVICE_SID already set"
    fi

    webhook_url="$(get_env TWILIO_WEBHOOK_BASE_URL)"
    if is_placeholder "$webhook_url"; then
        info "Local dev: use your ngrok static domain (https://<domain>.ngrok-free.app)"
        info "Production: your deployed API URL (https://api.yourapp.com)"
        webhook_url="$(ask "TWILIO_WEBHOOK_BASE_URL")"
        set_env "TWILIO_WEBHOOK_BASE_URL" "$webhook_url"
    else
        success "TWILIO_WEBHOOK_BASE_URL already set"
    fi
}

setup_ngrok_env() {
    header "── ngrok (local dev — Twilio webhooks) ─────────"
    info "Required only for local development so Twilio can reach your machine."
    info "Sign up for free at: https://ngrok.com"
    echo

    local authtoken domain

    authtoken="$(get_env NGROK_AUTHTOKEN)"
    if is_placeholder "$authtoken"; then
        info "Get your token at: https://dashboard.ngrok.com/get-started/your-authtoken"
        authtoken="$(ask "NGROK_AUTHTOKEN (leave blank to skip)" "" "secret")"
        [[ -n "$authtoken" ]] && set_env "NGROK_AUTHTOKEN" "$authtoken"
    else
        success "NGROK_AUTHTOKEN already set"
    fi

    domain="$(get_env NGROK_DOMAIN)"
    if is_placeholder "$domain"; then
        info "Claim a free static domain at: https://dashboard.ngrok.com/cloud-edge/domains"
        domain="$(ask "NGROK_DOMAIN (leave blank to skip)")"
        [[ -n "$domain" ]] && set_env "NGROK_DOMAIN" "$domain"
    else
        success "NGROK_DOMAIN already set"
    fi
}

setup_vapid() {
    header "── Web Push / VAPID ─────────────────────────────"

    local priv pub email

    priv="$(get_env VAPID_PRIVATE_KEY)"
    pub="$(get_env VAPID_PUBLIC_KEY)"

    if is_placeholder "$priv" || is_placeholder "$pub"; then
        info "Generating EC P-256 VAPID key pair automatically..."
        local output
        if ! output="$(gen_vapid_keys 2>&1)"; then
            err "Failed to generate VAPID keys: $output"
            err "Make sure 'cryptography' is installed: uv sync"
            exit 1
        fi
        local priv_val pub_val
        priv_val="$(echo "$output" | grep '^PRIVATE=' | cut -d= -f2)"
        pub_val="$(echo "$output"  | grep '^PUBLIC='  | cut -d= -f2)"
        set_env "VAPID_PRIVATE_KEY" "$priv_val"
        set_env "VAPID_PUBLIC_KEY"  "$pub_val"
        success "VAPID keys generated and written to backend/.env"
        info "Pass VAPID_PUBLIC_KEY to your frontend's PushManager.subscribe():"
        info "  applicationServerKey: '${pub_val}'"
    else
        success "VAPID keys already set"
    fi

    email="$(get_env VAPID_CLAIMS_EMAIL)"
    if is_placeholder "$email"; then
        local v
        v="$(ask "VAPID_CLAIMS_EMAIL (mailto:you@example.com)")"
        [[ -n "$v" ]] && set_env "VAPID_CLAIMS_EMAIL" "$v"
    else
        success "VAPID_CLAIMS_EMAIL already set"
    fi
}

setup_redis() {
    header "── Redis ────────────────────────────────────────"

    local url
    url="$(get_env REDIS_URL)"
    if is_placeholder "$url"; then
        info "Docker Compose starts Redis automatically — default is redis://redis:6379/0"
        info "For local dev without Docker: redis://localhost:6379/0"
        local v
        v="$(ask "REDIS_URL" "redis://redis:6379/0")"
        set_env "REDIS_URL" "$v"
    else
        success "REDIS_URL already set (${url})"
    fi
}

setup_frontend_env() {
    header "── Frontend (.env) ───────────────────────────────"

    if [[ ! -f "$FRONTEND_ENV_FILE" ]]; then
        if [[ -f "$FRONTEND_ENV_EXAMPLE" ]]; then
            cp "$FRONTEND_ENV_EXAMPLE" "$FRONTEND_ENV_FILE"
            warn "frontend/.env not found — created from frontend/.env.example"
        else
            touch "$FRONTEND_ENV_FILE"
            warn "frontend/.env not found and no .env.example — created empty frontend/.env"
        fi
    else
        success "frontend/.env file found."
    fi

    # ── Shared vars: mirror from backend/.env (no re-prompting) ──────────────

    # SUPABASE_URL
    local fe_val backend_val
    fe_val="$(get_env SUPABASE_URL "$FRONTEND_ENV_FILE")"
    backend_val="$(get_env SUPABASE_URL "$ENV_FILE")"
    if is_placeholder "$fe_val" && ! is_placeholder "$backend_val"; then
        set_env "SUPABASE_URL" "$backend_val" "$FRONTEND_ENV_FILE"
        success "SUPABASE_URL  → copied from backend/.env"
    else
        success "SUPABASE_URL  already set in frontend/.env"
    fi

    # SUPABASE_ANON_KEY
    fe_val="$(get_env SUPABASE_ANON_KEY "$FRONTEND_ENV_FILE")"
    backend_val="$(get_env SUPABASE_ANON_KEY "$ENV_FILE")"
    if is_placeholder "$fe_val" && ! is_placeholder "$backend_val"; then
        set_env "SUPABASE_ANON_KEY" "$backend_val" "$FRONTEND_ENV_FILE"
        success "SUPABASE_ANON_KEY  → copied from backend/.env"
    else
        success "SUPABASE_ANON_KEY  already set in frontend/.env"
    fi

    # APP_ENV
    fe_val="$(get_env APP_ENV "$FRONTEND_ENV_FILE")"
    backend_val="$(get_env APP_ENV "$ENV_FILE")"
    if is_placeholder "$fe_val"; then
        set_env "APP_ENV" "${backend_val:-development}" "$FRONTEND_ENV_FILE"
        success "APP_ENV=${backend_val:-development}  → copied from backend/.env"
    else
        success "APP_ENV=${fe_val}  already set in frontend/.env"
    fi

    # ── Frontend-only vars ────────────────────────────────────────────────────

    # APP_URL
    fe_val="$(get_env APP_URL "$FRONTEND_ENV_FILE")"
    if is_placeholder "$fe_val"; then
        local v
        v="$(ask "APP_URL (public frontend URL)" "http://localhost:3000")"
        set_env "APP_URL" "$v" "$FRONTEND_ENV_FILE"
    else
        success "APP_URL=${fe_val}  already set in frontend/.env"
    fi

    # VITE_API_URL — browser-facing URL for the backend API
    fe_val="$(get_env VITE_API_URL "$FRONTEND_ENV_FILE")"
    if is_placeholder "$fe_val"; then
        local v
        v="$(ask "VITE_API_URL (browser → API)" "http://localhost:8000")"
        set_env "VITE_API_URL" "$v" "$FRONTEND_ENV_FILE"
    else
        success "VITE_API_URL=${fe_val}  already set in frontend/.env"
    fi

    # VITE_ENABLE_MOCKS — set to false by default for a real backend run
    fe_val="$(get_env VITE_ENABLE_MOCKS "$FRONTEND_ENV_FILE")"
    if is_placeholder "$fe_val"; then
        set_env "VITE_ENABLE_MOCKS" "false" "$FRONTEND_ENV_FILE"
        success "VITE_ENABLE_MOCKS=false  (set automatically)"
    else
        success "VITE_ENABLE_MOCKS=${fe_val}  already set in frontend/.env"
    fi

    # Sentry (frontend) — optional
    header "── Sentry (Frontend) ────────────────────────────"
    info "Optional. Reuses your Sentry account — frontend project may differ from backend."
    echo

    fe_val="$(get_env VITE_SENTRY_DSN "$FRONTEND_ENV_FILE")"
    if is_placeholder "$fe_val"; then
        info "Find your DSN at: Sentry project → Settings → SDK Setup → DSN"
        local dsn
        dsn="$(ask "VITE_SENTRY_DSN (leave blank to skip)")"
        [[ -n "$dsn" ]] && set_env "VITE_SENTRY_DSN" "$dsn" "$FRONTEND_ENV_FILE"
    else
        success "VITE_SENTRY_DSN already set in frontend/.env"
    fi

    fe_val="$(get_env SENTRY_AUTH_TOKEN "$FRONTEND_ENV_FILE")"
    if is_placeholder "$fe_val"; then
        info "Required only for production builds that upload source maps."
        local tok
        tok="$(ask "SENTRY_AUTH_TOKEN (leave blank to skip)" "" "secret")"
        if [[ -n "$tok" ]]; then
            set_env "SENTRY_AUTH_TOKEN" "$tok" "$FRONTEND_ENV_FILE"
            local org proj
            org="$(ask "SENTRY_ORG (slug)")"
            [[ -n "$org" ]] && set_env "SENTRY_ORG" "$org" "$FRONTEND_ENV_FILE"
            proj="$(ask "SENTRY_PROJECT (slug)")"
            [[ -n "$proj" ]] && set_env "SENTRY_PROJECT" "$proj" "$FRONTEND_ENV_FILE"
        fi
    else
        success "SENTRY_AUTH_TOKEN already set in frontend/.env"
    fi
}

run_env_setup() {
    step "Step 2 of 5 — .env setup"

    bootstrap_env

    setup_app
    setup_supabase
    setup_openrouter
    setup_deepgram
    setup_langsmith
    setup_sentry
    setup_twilio
    setup_ngrok_env
    setup_vapid
    setup_redis
    setup_frontend_env

    echo
    success ".env setup complete."
}

# =============================================================================
# STEP 3 — MIGRATIONS
# =============================================================================

run_migrations() {
    step "Step 3 of 5 — Database migrations"

    info "Running migrations via Docker (postgres:15-alpine) — no local psql required."

    local raw_url
    raw_url="$(get_env MIGRATION_DATABASE_URL)"; [[ -z "$raw_url" ]] && raw_url="$(get_env DATABASE_URL)"
    if [[ -z "$raw_url" || "$raw_url" == \<* ]]; then
        err "DATABASE_URL is not set — cannot run migrations."
        exit 1
    fi

    # Rewrite postgresql+asyncpg:// → postgresql:// for the psql client
    local conn_url="${raw_url/postgresql+asyncpg:\/\//postgresql://}"

    local display_url
    display_url="$(echo "$conn_url" | sed -E 's|:[^:@]+@|:****@|')"
    info "Target: $display_url"

    # Pull image once up-front so subsequent runs are silent
    docker pull postgres:15-alpine 2>/dev/null || true

    local files=()
    while IFS= read -r -d '' f; do
        files+=("$f")
    done < <(find "$MIGRATIONS_DIR" -maxdepth 1 -name "*.sql" -print0 | sort -z)

    if [[ ${#files[@]} -eq 0 ]]; then
        err "No .sql files found in $MIGRATIONS_DIR"
        exit 1
    fi

    local count=0
    for f in "${files[@]}"; do
        local name
        name="$(basename "$f")"
        info "Applying $name ..."

        # Docker's internal DNS resolver can fail to resolve external hostnames like
        # Supabase's db.<project>.supabase.co. Forcing Google DNS (8.8.8.8) fixes this.
        if docker run --rm \
            --dns 8.8.8.8 \
            --network host \
            -v "${f}:/migration/${name}:ro" \
            postgres:15-alpine \
            psql "$conn_url" \
                --no-password \
                --single-transaction \
                --set ON_ERROR_STOP=on \
                --quiet \
                -f "/migration/${name}"; then
            success "$name"
            (( count++ )) || true
        else
            err "Failed on $name — migration halted."
            err "Fix the error above, then re-run this script."
            exit 1
        fi
    done

    echo
    success "${count} migration(s) applied."
}

# =============================================================================
# STEP 4 — DOCKER (backend stack)
# =============================================================================

run_docker() {
    step "Step 4 of 5 — Docker (backend stack)"

    local running
    running="$(docker compose --project-directory "$BACKEND_DIR" ps --quiet 2>/dev/null || true)"

    if [[ -n "$running" ]]; then
        warn "Stopping existing containers..."
        docker compose --project-directory "$BACKEND_DIR" down --remove-orphans
        success "Stale containers stopped."
    else
        info "No running containers found."
    fi

    info "Starting stack with ngrok profile..."
    docker compose \
        --project-directory "$BACKEND_DIR" \
        --profile ngrok \
        up --build --detach --remove-orphans

    echo
    success "Backend stack is up!"
    info "API:       http://localhost:8000"
    info "Docs:      http://localhost:8000/docs"
    info "Redis:     localhost:6379"
    info "ngrok UI:  http://localhost:4040"
    echo

    # Wait until the API is reachable before starting the frontend
    info "Waiting for API to become ready..."
    local attempts=0
    until curl -sf http://localhost:8000/health >/dev/null 2>&1; do
        attempts=$(( attempts + 1 ))
        if [[ $attempts -ge 30 ]]; then
            warn "API did not become ready after 30 seconds — starting frontend anyway."
            break
        fi
        sleep 1
    done
    if [[ $attempts -lt 30 ]]; then
        success "API is ready."
    fi
}

# =============================================================================
# STEP 5 — FRONTEND
# =============================================================================

teardown() {
    echo
    warn "Shutting down — running backend teardown (dev-end.sh)..."
    bash "$BACKEND_DIR/dev-end.sh" --soft
}

run_frontend() {
    step "Step 5 of 5 — Frontend"

    info "Installing frontend dependencies (npm install)..."
    npm --prefix "$FRONTEND_DIR" install

    success "Dependencies installed."
    echo
    info "Starting frontend dev server (npm run dev)..."
    info "Frontend: http://localhost:3000"
    echo
    info "Press Ctrl-C to stop. Docker containers will be brought down automatically."
    echo

    # Bring down Docker containers automatically when the user exits (Ctrl-C / Cmd-C)
    trap teardown EXIT INT TERM

    # Run in the foreground so the user sees live output and can Ctrl-C to stop
    npm --prefix "$FRONTEND_DIR" run dev
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo -e "\n${BOLD}╔══════════════════════════════════════════════╗"
    echo -e "║         Flux — Full-stack Setup              ║"
    echo -e "╚══════════════════════════════════════════════╝${RESET}"
    echo -e "  Press ${BOLD}Enter${RESET} to keep an existing value shown in ${DIM}[brackets]${RESET}."
    echo -e "  Values marked ${GREEN}✔${RESET} are already configured and will be skipped."

    check_deps
    run_env_setup
    run_migrations
    run_docker
    run_frontend

    # Note: run_frontend blocks (foreground dev server), so this banner only
    # appears after the user kills the frontend process.
    echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗"
    echo -e "║   Setup complete!                            ║"
    echo -e "╚══════════════════════════════════════════════╝${RESET}"
    echo
}

main "$@"
