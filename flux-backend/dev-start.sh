#!/usr/bin/env bash
# =============================================================================
# Flux Backend — Dev environment setup
#
# Usage:
#   bash dev-start.sh
#
# Steps:
#   1. Dependency check  — Docker, python3, uv
#   2. .env setup        — interactive prompts for all required variables
#   3. Migrations        — apply all SQL migrations (all files are idempotent)
#   4. Docker            — stop stale containers, then start the stack
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$REPO_ROOT/.env"
ENV_EXAMPLE="$REPO_ROOT/.env.example"
MIGRATIONS_DIR="$REPO_ROOT/migrations"

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
    if [[ ! -f "$ENV_FILE" ]]; then echo ""; return; fi
    grep -E "^${key}=" "$ENV_FILE" \
        | head -1 \
        | sed -E "s/^${key}=//" \
        | sed 's/[[:space:]]*#.*//' \
        | tr -d '"'"'" \
        | tr -d '[:space:]'
}

set_env() {
    local key="$1"
    local value="$2"
    if grep -qE "^${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i.bak -E "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
        rm -f "${ENV_FILE}.bak"
    else
        echo "${key}=${value}" >> "$ENV_FILE"
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
        IFS= read -rs reply; echo
    else
        IFS= read -r reply
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
    step "Step 1 of 4 — Dependency check"

    local missing_hard=()
    local missing_soft=()

    command -v python3 &>/dev/null || missing_hard+=("python3")

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
            warn ".env not found — created from .env.example"
        else
            touch "$ENV_FILE"
            warn ".env not found and no .env.example — created empty .env"
        fi
    else
        success ".env file found."
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
        success "VAPID keys generated and written to .env"
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

run_env_setup() {
    step "Step 2 of 4 — .env setup"

    bootstrap_env

    setup_app
    setup_supabase
    setup_openrouter
    setup_langsmith
    setup_sentry
    setup_twilio
    setup_ngrok_env
    setup_vapid
    setup_redis

    echo
    success ".env setup complete."
}

# =============================================================================
# STEP 3 — MIGRATIONS
# =============================================================================

run_migrations() {
    step "Step 3 of 4 — Database migrations"

    info "Running migrations via Docker (postgres:15-alpine) — no local psql required."

    local raw_url
    raw_url="$(get_env DATABASE_URL)"
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
# STEP 4 — DOCKER
# =============================================================================

run_docker() {
    step "Step 4 of 4 — Docker"

    local running
    running="$(docker compose --project-directory "$REPO_ROOT" ps --quiet 2>/dev/null || true)"

    if [[ -n "$running" ]]; then
        warn "Stopping existing containers..."
        docker compose --project-directory "$REPO_ROOT" down --remove-orphans
        success "Stale containers stopped."
    else
        info "No running containers found."
    fi

    info "Starting stack with ngrok profile..."
    docker compose \
        --project-directory "$REPO_ROOT" \
        --profile ngrok \
        up --build --detach --remove-orphans

    echo
    success "Stack is up!"
    info "API:       http://localhost:8000"
    info "Docs:      http://localhost:8000/docs"
    info "Redis:     localhost:6379"
    info "ngrok UI:  http://localhost:4040"
    echo
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo -e "\n${BOLD}╔══════════════════════════════════════════════╗"
    echo -e "║         Flux Backend — Setup                 ║"
    echo -e "╚══════════════════════════════════════════════╝${RESET}"
    echo -e "  Press ${BOLD}Enter${RESET} to keep an existing value shown in ${DIM}[brackets]${RESET}."
    echo -e "  Values marked ${GREEN}✔${RESET} are already configured and will be skipped."

    check_deps
    run_env_setup
    run_migrations
    run_docker

    echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗"
    echo -e "║   Setup complete!                            ║"
    echo -e "╚══════════════════════════════════════════════╝${RESET}"
    echo
}

main "$@"
