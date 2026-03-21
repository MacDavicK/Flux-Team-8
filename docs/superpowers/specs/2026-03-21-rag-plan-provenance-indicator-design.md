# RAG Plan Provenance Indicator — Design Spec

**Date:** 2026-03-21
**Status:** Approved

---

## Overview

When the goal planner generates a plan, it may use one of two paths:

1. **RAG-assisted** — classifier tags match health/fitness/nutrition/mental health triggers, Pinecone retrieval succeeds, and expert content is injected into the LLM prompt
2. **LLM-only** — no retrieval, plan is generated from general model knowledge alone

Users currently have no way to tell which path produced their plan. This feature adds a subtle, inline provenance indicator directly below the assistant message bubble that contains the plan.

---

## Goals

- Let users know whether their plan was grounded in cited sources or generated from general LLM knowledge
- Show a concise, non-alarming disclaimer for LLM-only plans
- Allow users to see which sources were used when RAG was active
- Keep the UI unobtrusive — this is informational, not a warning

---

## Non-Goals

- Showing provenance on non-plan messages (reschedule, onboarding, etc.)
- Showing RAG confidence scores or chunk content
- Any changes to the RAG retrieval pipeline or goal planner logic

---

## Backend Changes

### New Pydantic sub-model (`backend/app/models/api_schemas.py`)

Add a typed sub-model for RAG sources (avoids loose `list[dict]` typing):

```python
class RagSource(BaseModel):
    title: str
    url: str = ""
```

### `ChatMessageResponse` schema (`backend/app/models/api_schemas.py`)

Add two optional fields:

```python
rag_used: bool = False
rag_sources: list[RagSource] = []
```

### `chat.py` (`backend/app/api/v1/chat.py`)

**Important scope note:** The `_send_message_events` function has two distinct code paths:
1. A **short-circuit reschedule path** (lines ~95–216) that constructs its own `ChatMessageResponse` and yields it directly — this path never produces a plan, so `rag_used` stays `False` by default. No changes needed here.
2. The **main LangGraph path** that runs `astream_events` and builds a response after the graph completes.

The extraction below applies **only to the main LangGraph path**, after the `astream_events` block:

```python
rag_output = result.get("rag_output") or {}
if rag_output.get("retrieved"):
    resp.rag_used = True
    resp.rag_sources = [
        RagSource(title=s.get("title", ""), url=s.get("url", ""))
        for s in rag_output.get("sources", [])
    ]
```

For all non-GOAL intents (RESCHEDULE_TASK, ONBOARDING, GOAL_CLARIFY), `rag_output` will be absent from state — `result.get("rag_output") or {}` returns `{}` safely, leaving `rag_used=False`.

### Persisting provenance to message history

`rag_used` and `rag_sources` must survive conversation history reload. Add them to the `metadata` dict saved to the `messages` table alongside `proposed_plan`:

```python
metadata = {
    "proposed_plan": goal_draft,
    "classifier_output": result.get("classifier_output"),
    "approval_status": result_approval,
    "rag_used": resp.rag_used,
    "rag_sources": [s.model_dump() for s in resp.rag_sources],
}
```

When loading conversation history (`loadConversation` in `chat.tsx`), read these fields from `m.metadata` alongside `proposed_plan`.

**Important:** In `chat.py`, the `metadata` dict is only written to the database when `goal_draft` is present and the plan is pending approval. The provenance fields must be added **inside that existing conditional**, not unconditionally — the metadata block already contains `proposed_plan`, so adding `rag_used`/`rag_sources` alongside it is the correct placement.

---

## Frontend Changes

### New `provenance` field on `ChatMessage` type

`chat.tsx` stores messages as `ChatMessage` objects with a `content: React.ReactNode` field. Since provenance needs to be accessible at render time (both on new messages and history-loaded ones), add a dedicated field rather than embedding it in the `ReactNode`:

```typescript
interface ChatMessage {
  // ...existing fields...
  provenance?: {
    rag_used: boolean
    rag_sources: { title: string; url: string }[]
  }
}
```

Populate this field in two places:
1. **`handleSendMessage`** — from `result.rag_used` / `result.rag_sources` on the SSE response
2. **`loadConversation`** — from `m.metadata.rag_used` / `m.metadata.rag_sources` on history messages. Only apply to assistant messages that also have a `proposed_plan` in metadata.

### `ProvenanceIndicator` component

Create `frontend/src/components/chat/ProvenanceIndicator.tsx`.

Props:
```typescript
interface ProvenanceIndicatorProps {
  ragUsed: boolean
  ragSources: { title: string; url: string }[]
}
```

**Render rules:**

| `rag_used` | `rag_sources` | Render |
|------------|---------------|--------|
| `true` | non-empty | "Sources cited" toggle — expands to source list |
| `true` | empty | Fall back to LLM-only copy (treat as unverified) |
| `false` | any | Static disclaimer text |

`rag_used` is the authoritative flag. `rag_sources` content is only displayed when `rag_used === true` AND `rag_sources.length > 0`. If `rag_used === false` but `rag_sources` is somehow non-empty, show the LLM-only copy only.

**When RAG used (non-empty sources):**
- A clickable text: `Sources cited` + Lucide `<ArrowUpRight className="w-3 h-3 inline-block ml-0.5" />` from `lucide-react`
- Clicking toggles an inline list of source titles below (with links if `url` is non-empty)
- Collapses on second click
- No network call — sources already in payload

**When LLM-only (or RAG used but no sources):**
- Static: `AI-generated plan · always verify with a professional`
- No interaction

**Styling (both states):**
- `text-xs text-muted-foreground`
- Small top margin below the message bubble (`mt-1`)
- No border, no card, no attention-drawing icons

### Placement in `chat.tsx`

The message list renders `ChatMessage.content` (a `ReactNode`) inside a loop, with `content` passed as a child of `<ChatBubble>`. `ProvenanceIndicator` must be rendered **outside** `<ChatBubble>`, as a sibling — the same pattern used for `<OnboardingOptions>`. Gated on `msg.provenance` being present:

```tsx
{messages.map(msg => (
  <motion.div key={msg.id}>
    <ChatBubble>{msg.content}</ChatBubble>
    {msg.provenance && (
      <ProvenanceIndicator
        ragUsed={msg.provenance.rag_used}
        ragSources={msg.provenance.rag_sources}
      />
    )}
    {msg.options && <OnboardingOptions ... />}
  </motion.div>
))}
```

Only assistant messages with a `proposed_plan` will have `provenance` set, so the indicator naturally appears only on plan messages.

---

## Data Flow

```
AgentState.rag_output { retrieved, sources, context }
    ↓ (main LangGraph path only)
chat.py extracts retrieved + sources → RagSource models
    ↓
ChatMessageResponse { rag_used, rag_sources }
    ↓ (also persisted to messages.metadata)
Frontend SSE handler → ChatMessage.provenance
Frontend loadConversation → ChatMessage.provenance (from metadata)
    ↓
ProvenanceIndicator rendered as sibling below message content
(only when msg.provenance is set, i.e. plan messages only)
```

---

## Files to Change

| File | Change |
|------|--------|
| `backend/app/models/api_schemas.py` | Add `RagSource` model; add `rag_used`, `rag_sources` to `ChatMessageResponse` |
| `backend/app/api/v1/chat.py` | Populate new fields after main LangGraph path; persist to `messages.metadata` (inside existing `goal_draft` conditional) |
| `frontend/src/types/message.ts` | Add `rag_used?: boolean` and `rag_sources?: { title: string; url: string }[]` to the frontend `ChatMessageResponse` interface |
| `frontend/src/routes/chat.tsx` | Add `provenance` to `ChatMessage` type; populate in `handleSendMessage` and `loadConversation`; render `ProvenanceIndicator` outside `<ChatBubble>` in message list |
| `frontend/src/components/chat/ProvenanceIndicator.tsx` | New component (created) |

---

## Copy

| State | Text |
|-------|------|
| RAG used, sources available | `Sources cited` + `<ArrowUpRight />` (collapsed) → source title list (expanded) |
| RAG used, no sources / LLM-only | `AI-generated plan · always verify with a professional` |
