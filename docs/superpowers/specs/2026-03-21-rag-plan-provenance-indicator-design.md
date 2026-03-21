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

- Showing provenance on non-plan messages
- Showing RAG confidence scores or chunk content
- Any changes to the RAG retrieval pipeline or goal planner logic

---

## Backend Changes

### `ChatMessageResponse` schema (`backend/app/models/api_schemas.py`)

Add two optional fields:

```python
rag_used: bool = False
rag_sources: list[dict] = []  # Each dict: {"title": str, "url": str}
```

### `chat.py` (`backend/app/api/v1/chat.py`)

After the LangGraph run completes, extract `rag_output` from the result state and populate the new fields on the response:

```python
rag_output = result.get("rag_output") or {}
response.rag_used = rag_output.get("retrieved", False)
response.rag_sources = rag_output.get("sources", [])
```

`rag_output` is already a first-class field in `AgentState` with shape `{"retrieved": bool, "sources": [{"title": str, "url": str}], "context": str}`. No changes to the agent pipeline are needed.

---

## Frontend Changes

### Type update

Update the `ChatMessageResponse` TypeScript type to include:

```typescript
rag_used?: boolean
rag_sources?: { title: string; url: string }[]
```

### Provenance indicator component

A small inline component rendered **below** the assistant message bubble, only when the message carries a `proposed_plan`.

**When `rag_used === true`:**
```
Sources cited ↗
```
- Clickable — toggles an inline list of source titles (with URLs if available)
- Collapses on second click
- No network call — sources are already in the message payload

**When `rag_used === false` (or absent) and message has a plan:**
```
AI-generated plan · always verify with a professional
```
- Static, no interaction

**Styling for both states:**
- `text-xs` font size
- `text-muted-foreground` color (low contrast)
- No border, no card, no icon that draws attention
- Sits flush below the message bubble with a small top margin

---

## Data Flow

```
AgentState.rag_output { retrieved, sources, context }
    ↓
chat.py extracts retrieved + sources
    ↓
ChatMessageResponse { rag_used, rag_sources }
    ↓
Frontend message payload
    ↓
ProvenanceIndicator rendered below message bubble (only if proposed_plan present)
```

---

## Files to Change

| File | Change |
|------|--------|
| `backend/app/models/api_schemas.py` | Add `rag_used`, `rag_sources` to `ChatMessageResponse` |
| `backend/app/api/v1/chat.py` | Populate new fields from `rag_output` after graph run |
| `frontend/src/routes/chat.tsx` | Add provenance indicator below plan message bubble |
| `frontend/src/components/chat/` | New `ProvenanceIndicator` component (or inline in chat.tsx) |

---

## Copy

| State | Text |
|-------|------|
| RAG used | `Sources cited ↗` (collapsed) / source list (expanded) |
| LLM only | `AI-generated plan · always verify with a professional` |
