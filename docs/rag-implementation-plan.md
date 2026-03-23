# RAG Implementation Plan

> Built from scratch to fit the current LangGraph architecture.
> Do NOT refer to the old `rag_service.py` from git history — it used a different pattern.

---

## Architecture Summary

The RAG pipeline integrates as a **4th parallel node** inside the existing `goal_planner` fan-out, gated by the classifier's category output. The graph uses a **two-phase fan-out** so the classifier runs first, then RAG fires conditionally.

```
orchestrator → goal_clarifier → goal_planner (call 1)
    └→ Send(classifier)                          ← Phase 1: solo
         └→ goal_planner (call 2, has category)
              └→ Send(scheduler, pattern_observer, rag_retriever?)   ← Phase 2: gated
                   └→ goal_planner (call 3, LLM + expert context)
                        └→ save_tasks → END
```

RAG fires only when `classifier_output["tags"]` contains at least one of:
`Health | Fitness | Nutrition | Mental Health`

These map to the classifier's actual 14-tag taxonomy (not the corpus article categories).
Gate check: `bool({"Health","Fitness","Nutrition","Mental Health"} & set(classifier_output["tags"]))`

Graceful fallback if Pinecone is unreachable or all scores < 0.4.

---

## Phase 1 — Infrastructure Setup

### 1.1 Add dependencies to `backend/pyproject.toml`

Add to `[project.dependencies]`:
```
pinecone>=5.4.0
langchain-text-splitters>=0.2.4
openai>=1.59.0        # used as OpenRouter embedding client
beautifulsoup4>=4.12.0
pdfplumber>=0.10.0
```

### 1.2 Update `backend/.env.example`

Add a new `Pinecone (RAG)` section after the OpenRouter block:

```bash
# ──────────────────────────────────────────────
# Pinecone (RAG — Vector Store)
# ──────────────────────────────────────────────
# Create a serverless index at: https://app.pinecone.io
# Settings: dimension=1536, metric=cosine
PINECONE_API_KEY=<your-pinecone-api-key>
PINECONE_INDEX_NAME=flux-articles
```

### 1.3 Update `backend/app/config.py`

Add to the `Settings` class:

```python
# Pinecone / RAG
pinecone_api_key: str = ""
pinecone_index_name: str = "flux-articles"
embedding_model: str = "openai/text-embedding-3-small"
rag_chunk_size: int = 2000
rag_chunk_overlap: int = 200
rag_top_k: int = 5
rag_relevance_threshold: float = 0.4
# Classifier tags (from 14-tag taxonomy) that trigger RAG retrieval
rag_trigger_tags: list[str] = ["Health", "Fitness", "Nutrition", "Mental Health"]
```

### 1.4 Update `setup.sh`

Two changes needed:

**A) Add `setup_pinecone()` to the `.env` setup section (Step 2), after `setup_openrouter()`:**

```bash
setup_pinecone() {
    header "── Pinecone (RAG / Vector Store) ───────────────"
    info "Create a serverless index at: https://app.pinecone.io"
    info "Index settings: name=flux-articles, dims=1536, metric=cosine"
    echo

    local api_key index_name
    api_key="$(get_env PINECONE_API_KEY)"
    if is_placeholder "$api_key"; then
        info "Get your key at: https://app.pinecone.io → API Keys"
        api_key="$(ask "PINECONE_API_KEY (leave blank to skip)" "" "secret")"
        [[ -n "$api_key" ]] && set_env "PINECONE_API_KEY" "$api_key"
    else
        success "PINECONE_API_KEY already set"
    fi

    index_name="$(get_env PINECONE_INDEX_NAME)"
    if is_placeholder "$index_name"; then
        local v
        v="$(ask "PINECONE_INDEX_NAME" "flux-articles")"
        set_env "PINECONE_INDEX_NAME" "$v"
    else
        success "PINECONE_INDEX_NAME=${index_name}"
    fi
}
```

Call `setup_pinecone` inside `run_env_setup()` after `setup_openrouter`.

**B) Add `run_rag_ingest()` as a new Step 5 (frontend becomes Step 6):**

This step mirrors how migrations work — runs once on first setup, skips if already done.

```bash
run_rag_ingest() {
    step "Step 5 of 6 — RAG corpus ingestion"

    local api_key index_name
    api_key="$(get_env PINECONE_API_KEY)"
    index_name="$(get_env PINECONE_INDEX_NAME)"
    index_name="${index_name:-flux-articles}"

    # Skip if not configured
    if is_placeholder "$api_key" || [[ -z "$api_key" ]]; then
        warn "PINECONE_API_KEY not set — skipping RAG ingestion."
        info "Configure Pinecone and re-run, or call POST /api/v1/rag/ingest manually."
        return
    fi

    # Get index host from Pinecone control plane
    info "Checking Pinecone index '${index_name}'..."
    local index_json host
    index_json="$(curl -sf \
        -H "Api-Key: ${api_key}" \
        -H "Accept: application/json" \
        "https://api.pinecone.io/indexes/${index_name}" 2>/dev/null || echo "")"

    if [[ -z "$index_json" ]]; then
        warn "Index '${index_name}' not found or Pinecone unreachable."
        info "Create it at https://app.pinecone.io (dims=1536, metric=cosine) then re-run."
        return
    fi

    host="$(echo "$index_json" | python3 -c \
        "import sys,json; print(json.load(sys.stdin).get('host',''))" 2>/dev/null || echo "")"

    if [[ -z "$host" ]]; then
        warn "Could not read index host from Pinecone response — skipping."
        return
    fi

    # Check if index already has vectors (idempotency check)
    local stats vector_count
    stats="$(curl -sf \
        -H "Api-Key: ${api_key}" \
        "https://${host}/describe_index_stats" 2>/dev/null || echo "")"
    vector_count="$(echo "$stats" | python3 -c \
        "import sys,json; print(json.load(sys.stdin).get('totalVectorCount', 0))" 2>/dev/null || echo "0")"

    if [[ "$vector_count" -gt 0 ]]; then
        success "Pinecone index already populated (${vector_count} vectors) — skipping ingestion."
        return
    fi

    # Check articles directory is non-empty
    local articles_dir="$BACKEND_DIR/articles"
    if [[ ! -d "$articles_dir" ]] || [[ -z "$(ls -A "$articles_dir" 2>/dev/null)" ]]; then
        warn "No articles found in backend/articles/ — skipping ingestion."
        info "Add .txt files to backend/articles/ then run:"
        info "  curl -X POST 'http://localhost:8000/api/v1/rag/ingest?articles_dir=${articles_dir}&clear_existing=true'"
        return
    fi

    # Run ingestion via the running backend API
    # APP_ENV=development bypasses auth — no token required
    info "Ingesting RAG article corpus into Pinecone (runs once)..."
    local ingest_response
    ingest_response="$(curl -sf -X POST \
        "http://localhost:8000/api/v1/rag/ingest?articles_dir=${articles_dir}&clear_existing=true" \
        2>/dev/null || echo "")"

    if [[ -z "$ingest_response" ]]; then
        warn "Ingestion request failed — backend may not be ready yet."
        info "Run manually once the backend is up:"
        info "  curl -X POST 'http://localhost:8000/api/v1/rag/ingest?articles_dir=${articles_dir}&clear_existing=true'"
        return
    fi

    local status article_count chunk_count
    status="$(echo "$ingest_response" | python3 -c \
        "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")"
    article_count="$(echo "$ingest_response" | python3 -c \
        "import sys,json; print(json.load(sys.stdin).get('articles', 0))" 2>/dev/null || echo "0")"
    chunk_count="$(echo "$ingest_response" | python3 -c \
        "import sys,json; print(json.load(sys.stdin).get('chunks', 0))" 2>/dev/null || echo "0")"

    if [[ "$status" == "ok" ]]; then
        success "RAG ingestion complete: ${article_count} articles, ${chunk_count} chunks → Pinecone."
    else
        warn "Unexpected ingestion response: ${ingest_response}"
    fi
}
```

Call order in `main()`:
```bash
check_deps        # Step 1
run_env_setup     # Step 2
run_migrations    # Step 3
run_docker        # Step 4  (backend confirmed ready before returning)
run_rag_ingest    # Step 5  (new — backend already up, Pinecone idempotency check)
run_frontend      # Step 6  (was Step 5)
```

> **Teardown note:** Pinecone is a cloud service. No local process or container is started, so no teardown is needed.

> **Auth note:** The `/api/v1/rag/ingest` endpoint uses `Depends(get_current_user)`. In `APP_ENV=development` the dev bypass returns a mock payload without validating any token — so the curl call above works with no `Authorization` header. In production, ingestion should be triggered manually with a valid token.

---

## Ingestion vs. Retrieval Lifecycle

These are two completely separate operations:

| Operation | Trigger | Frequency | Cost |
|---|---|---|---|
| **Ingest** (load → chunk → embed → upsert) | Manual: `POST /api/v1/rag/ingest` | Once at setup; re-run only when corpus changes | ~355 embedding calls |
| **Retrieve** (embed query → Pinecone query) | Automatic: `rag_retriever_node` per goal-planning request | Every qualifying goal planning run | 1 embedding call + 1 Pinecone query |

Pinecone is a persistent cloud database. Vectors survive restarts. The retrieval path never touches the article files — it only queries the already-populated index.

---

## Phase 2 — RAG Service

### 2.1 Create `backend/app/services/rag_service.py`

Module-level singleton following the same pattern as `supabase.py` and `llm.py`.

**Class: `_RagService`**

Methods to implement:

#### `_get_pinecone_index()`
- Lazy-initialise the Pinecone client and return the index handle
- Use `settings.pinecone_api_key` and `settings.pinecone_index_name`
- Cache the index on `self._index` (initialise once)

#### `load_articles(articles_dir: Path) -> list[dict]`
- Read every `.txt` and `.md` file in `articles_dir`
- Parse 2-line header format:
  ```
  Title: <title> | Source: <url>
  Category: <category> | Authority: <authority>
  ---
  <body>
  ```
- Also handle legacy 1-line format: `Title: <title>`
- Return list of `{filename, title, source, category, authority, body}`

#### `chunk_articles(articles: list[dict]) -> list[dict]`
- Use `RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)`
- Each chunk carries all parent metadata plus `chunk_index`

#### `embed_texts(texts: list[str]) -> list[list[float]]`
- Use the `openai` SDK pointed at OpenRouter base URL
- Model: `settings.embedding_model` (`openai/text-embedding-3-small`, 1536 dims)
- Batch in groups of 64
- Return list of float vectors

#### `ingest_articles(articles_dir: Path, clear_existing: bool = True) -> dict`
- Orchestrate: `load_articles → chunk_articles → embed_texts → Pinecone upsert`
- Vector ID format: `{filename}_{chunk_index}`
- Upsert in batches of 100
- If `clear_existing=True`, delete all vectors before upserting
- Return `{"status": "ok", "articles": N, "chunks": M}`

#### `retrieve(query: str, top_k: int = None) -> list[dict]`
- Embed the query string
- Call `index.query(vector=..., top_k=top_k, include_metadata=True)`
- Return list of `{text, title, source, category, authority, score}`
- Catch all exceptions; return `[]` on failure (graceful fallback)

#### `format_rag_context(chunks: list[dict]) -> str`
- Filter chunks below `settings.rag_relevance_threshold`
- Format as numbered blocks:
  ```
  [1] Title: <title>
  Source: <url>
  Content: <text>

  [2] ...
  ```
- Return empty string if no chunks survive the filter

**Module-level singleton:**
```python
rag_service = _RagService()
```

---

## Phase 3 — AgentState Update

### 3.1 Update `backend/app/agents/state.py`

Add `rag_output` to `AgentState` using the existing `_merge_dict` reducer:

```python
rag_output: Annotated[Optional[dict], _merge_dict]
```

Shape of `rag_output`:
```python
{
    "context": "<formatted markdown string or empty string>",
    "sources": [{"title": "...", "url": "..."}],   # deduplicated
    "retrieved": True | False   # whether RAG fired at all
}
```

---

## Phase 4 — rag_retriever_node

### 4.1 Create `backend/app/agents/rag_retriever.py`

Pure async node function following the same pattern as `classifier.py`, `scheduler.py`, etc.

```python
async def rag_retriever_node(state: AgentState) -> dict:
    ...
```

Logic:
1. Build query string from `state["goal_draft"]` fields (goal, target, preferences)
2. Call `rag_service.retrieve(query, top_k=settings.rag_top_k)` — already handles exceptions
3. Format context via `rag_service.format_rag_context(chunks)`
4. Extract deduplicated sources: `[{"title": c["title"], "url": c["source"]} for c in chunks if score >= threshold]`
5. Return:
   ```python
   {"rag_output": {"context": context_str, "sources": sources, "retrieved": bool(context_str)}}
   ```

---

## Phase 5 — Graph Updates

### 5.1 Update `backend/app/agents/graph.py`

**Import:** Add `from app.agents.rag_retriever import rag_retriever_node`

**Add node:** `graph.add_node("rag_retriever", rag_retriever_node)`

**Update `route_from_goal_planner`:**

The function currently handles 2 states. Extend to 3:

```
State 0 — nothing run (classifier_output is None):
    → Send("classifier")

State 1 — classifier done, phase-2 not run (scheduler_output is None):
    → Send("scheduler"), Send("pattern_observer")
    → Send("rag_retriever") only if:
      bool(set(settings.rag_trigger_tags) & set(classifier_output["tags"]))
      e.g. ["Fitness", "Career"] → fires; ["Career", "Financial"] → skips

State 2 — everything done:
    → "goal_planner"  (LLM call)
```

**Add edge:** `graph.add_edge("rag_retriever", "goal_planner")`

---

## Phase 6 — Goal Planner Integration

### 6.1 Update `backend/app/agents/goal_planner.py`

The node already handles call 1 and call 2. Extend routing logic for call 3.

**At call 3 (LLM call), read `rag_output` from state:**

```python
rag_output = state.get("rag_output") or {}
expert_context = rag_output.get("context", "")
rag_sources = rag_output.get("sources", [])
```

**Inject into prompt:**
- If `expert_context` is non-empty: inject as `EXPERT CONTEXT` section with grounding instructions
- If empty: inject fallback text (`"No expert content available — use general knowledge."`)

**Include sources in return value** so the chat endpoint can surface them.

### 6.2 Update `backend/app/agents/prompts/goal_planner.txt`

Add an `{expert_context_section}` and `{rag_rules}` placeholder to the system prompt template. Two variants:
- **RAG rules:** "Ground your recommendations in the expert content above. Cite sources by number."
- **Fallback rules:** "No expert content is available. Use general knowledge."

---

## Phase 7 — API Endpoints

### 7.1 Create `backend/app/api/v1/rag.py`

Two endpoints, both protected by `Depends(get_current_user)`:

#### `POST /api/v1/rag/ingest`
- Query params: `articles_dir: str`, `clear_existing: bool = True`
- Calls `rag_service.ingest_articles(Path(articles_dir), clear_existing)`
- Returns: `{"status": "ok", "articles": N, "chunks": M}`
- Guard: restrict to `APP_ENV=development` or admin role in production

#### `GET /api/v1/rag/search`
- Query params: `q: str`, `top_k: int = 5`
- Calls `rag_service.retrieve(q, top_k)`
- Returns list of `{text, title, source, category, authority, score}`

### 7.2 Register in `backend/app/main.py`

```python
from app.api.v1.rag import router as rag_router
app.include_router(rag_router, prefix="/api/v1")
```

---

## Phase 8 — Article Corpus

### 8.1 Create `backend/articles/` directory

Create 30 `.txt` files matching the registry in `docs/rag-docs/rag-article-corpus.md`.

Each file format:
```
Title: <title> | Source: <url>
Category: <category> | Authority: <authority>
---
<body text>
```

Categories: `weight_loss`, `nutrition`, `strength`, `cardio`, `behavioral`
Authority types: `government`, `peer_reviewed`, `hospital`, `university`

Files to create (see `docs/rag-docs/rag-article-corpus.md` for full registry):

| File | Category | Authority |
|---|---|---|
| `01_nhlbi_aim_healthy_weight.txt` | weight_loss | government |
| `02_cdc_steps_losing_weight.txt` | weight_loss | government |
| `03_who_obesity_overweight.txt` | weight_loss | government |
| `04_mayo_weight_loss_6_strategies.txt` | weight_loss | hospital |
| `05_pmc_prevention_obesity_evidence.txt` | weight_loss | peer_reviewed |
| `06_pmc_rate_weight_loss_prediction.txt` | weight_loss | peer_reviewed |
| `07_who_healthy_diet.txt` | nutrition | government |
| `08_pmc_optimal_diet_strategies.txt` | nutrition | peer_reviewed |
| `09_ucdavis_weight_loss_guidelines.txt` | nutrition | university |
| `10_harvard_healthy_eating_plate.txt` | nutrition | university |
| `11_usda_dietary_guidelines_2020.txt` | nutrition | government |
| `12_harvard_water_intake.txt` | nutrition | university |
| `13_hhs_physical_activity_guidelines.txt` | strength | government |
| `14_who_physical_activity.txt` | strength | government |
| `15_acsm_resistance_training.txt` | strength | government |
| `16_healthdirect_strength_beginners.txt` | strength | government |
| `17_msu_acsm_recommendations.txt` | strength | university |
| `18_kaiser_strength_beginners.txt` | strength | hospital |
| `19_nhs_couch_to_5k.txt` | cardio | government |
| `20_mayo_5k_training.txt` | cardio | hospital |
| `21_pmc_start_to_run_6week.txt` | cardio | peer_reviewed |
| `22_jama_aerobic_dose_response.txt` | cardio | peer_reviewed |
| `23_healthdirect_running_tips.txt` | cardio | government |
| `24_pmc_progressive_overload.txt` | cardio | peer_reviewed |
| `25_pmc_habit_formation_meta.txt` | behavioral | peer_reviewed |
| `26_pmc_sleep_deprivation_weight.txt` | behavioral | peer_reviewed |
| `27_cdc_about_sleep.txt` | behavioral | government |
| `28_cleveland_stress_weight.txt` | behavioral | hospital |
| `29_pmc_self_monitoring_review.txt` | behavioral | peer_reviewed |
| `30_pmc_behavioral_treatment_obesity.txt` | behavioral | peer_reviewed |

> **Note:** Articles 01, 10, 11, 12, 13, 22 may need to be written/supplemented manually
> (original sources returned 403 or insufficient JS-rendered content).

### 8.2 Run ingestion

After the API is running:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/ingest?articles_dir=/abs/path/to/backend/articles&clear_existing=true"
```

---

## Phase 9 — Post-Implementation

### 9.1 Update `docs/PRD.md`
- Add RAG feature section
- Describe classifier-gated retrieval, two-phase fan-out, expert context injection

### 9.2 Update `docs/rag-docs/rag-article-corpus.md`
- Verify article registry matches actual files in `backend/articles/`

### 9.3 Update `pitch-site/index.html`
- Reflect RAG-powered goal planning (evidence-backed, cited plans)

### 9.4 Update `GETTING_STARTED.md`

Three places to update:

**A) External accounts table** — add Pinecone row:
```
| **Pinecone** | Backend | API key + serverless index (dims=1536, metric=cosine, name=flux-articles) | app.pinecone.io → API Keys |
```

**B) Setup steps table** — update to 6 steps:
```
| 5 — RAG ingestion | Checks if the Pinecone index already has vectors; if not, ingests the article corpus automatically. Skipped if PINECONE_API_KEY is not set or vectors already exist. |
| 6 — Frontend      | (was Step 5) Runs npm install then starts the Vite dev server |
```

**C) Re-running setup / idempotency note** — add:
```
- **RAG ingestion** checks totalVectorCount in Pinecone before running — skipped automatically if the index is already populated.
```

### 9.5 Update `backend/README.md` — RAG Operations section

Add a dedicated section covering:

**First-time setup**
- Explain that `setup.sh` handles ingestion automatically on first run
- Pinecone index must be created manually first (dims=1536, metric=cosine)

**Corpus management**
```
# Add or update articles
# 1. Add/edit .txt files in backend/articles/ using the format:
#    Title: <title> | Source: <url>
#    Category: <category> | Authority: <authority>
#    ---
#    <body text>
#
# 2. Re-ingest:
curl -X POST "http://localhost:8000/api/v1/rag/ingest?articles_dir=/abs/path/to/backend/articles&clear_existing=true"
```

**Adding a new RAG category**
```
# 1. Add article .txt files to backend/articles/
# 2. Add the classifier tag to RAG_TRIGGER_TAGS in backend/.env:
#    RAG_TRIGGER_TAGS=["Health","Fitness","Nutrition","Mental Health","NewCategory"]
# 3. Re-ingest (same curl command as above)
# No code changes required.
```

**Debug / verify retrieval quality**
```
curl "http://localhost:8000/api/v1/rag/search?q=your+test+query&top_k=5"
# Scores > 0.4 = relevant, < 0.3 = off-domain (expected for non-health queries)
```

---

## Implementation Order

```
Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5  →  Phase 7  →  Phase 6  →  Phase 8  →  Phase 9
Infra       Service     State       Node        Graph       Router      Planner     Corpus      Docs
(setup.sh
 ingest
 runs here
 automatically)
```

> Phase 6 (goal_planner integration) comes after Phase 5 (graph) because you need to
> understand the 3-state routing before modifying the node.

---

## Files Changed / Created

| Action | File |
|---|---|
| Modified | `backend/pyproject.toml` |
| Modified | `backend/.env.example` |
| Modified | `backend/app/config.py` |
| Modified | `setup.sh` |
| **Created** | `backend/app/services/rag_service.py` |
| Modified | `backend/app/agents/state.py` |
| **Created** | `backend/app/agents/rag_retriever.py` |
| Modified | `backend/app/agents/graph.py` |
| Modified | `backend/app/agents/goal_planner.py` |
| Modified | `backend/app/agents/prompts/goal_planner.txt` |
| **Created** | `backend/app/api/v1/rag.py` |
| Modified | `backend/app/main.py` |
| **Created** | `backend/articles/` (30 × `.txt`) |
| Modified | `docs/PRD.md` |
| Modified | `docs/rag-docs/rag-article-corpus.md` |
| Modified | `pitch-site/index.html` |
| Modified | `GETTING_STARTED.md` |
| Modified | `backend/README.md` |

---

## Key Decisions

| Decision | Rationale |
|---|---|
| Two-phase fan-out (classifier first) | Enables category-gated RAG. Future-proof: adding a new RAG corpus = one category check. |
| RAG as a parallel node, not inside goal_planner | Follows existing architecture. Keeps goal_planner_node's job as orchestration, not retrieval. |
| Module-level singleton for rag_service | Matches pattern of `db`, `llm`, etc. No DI framework needed. |
| OpenRouter for embeddings | Same key already in settings. No new credential type needed. |
| Relevance threshold 0.4 | Filters low-confidence matches within the health corpus (e.g. tangential queries). |
| Pinecone teardown: none | Cloud service. No local container. dev-end.sh unchanged. |
