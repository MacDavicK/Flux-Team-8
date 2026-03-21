# RAG Plan Provenance Indicator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a subtle inline indicator below plan messages telling the user whether their plan was grounded in cited expert sources (RAG) or generated from general LLM knowledge only.

**Architecture:** Add `rag_used: bool` and `rag_sources: list[RagSource]` to the backend `ChatMessageResponse`, populate them from the existing `rag_output` state field after the LangGraph run, persist them to `messages.metadata` alongside `proposed_plan`, then render a `ProvenanceIndicator` component in the frontend message list as a sibling of `<ChatBubble>`.

**Tech Stack:** Python/Pydantic (FastAPI), TypeScript/React (TanStack Start), Lucide React icons, Tailwind CSS

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/models/api_schemas.py` | Modify | Add `RagSource` sub-model + two new fields to `ChatMessageResponse` |
| `backend/app/api/v1/chat.py` | Modify | Populate `rag_used`/`rag_sources` from state; persist to metadata |
| `frontend/src/types/message.ts` | Modify | Add `rag_used`/`rag_sources` to `ChatMessageResponse`; add `provenance` to `ChatMessage` |
| `frontend/src/components/chat/ProvenanceIndicator.tsx` | Create | New component — renders RAG badge or LLM disclaimer |
| `frontend/src/routes/chat.tsx` | Modify | Import + render `ProvenanceIndicator`; populate `provenance` in `handleSendMessage` and `loadConversation` |

---

## Task 1: Add `RagSource` model and provenance fields to `ChatMessageResponse`

**Files:**
- Modify: `backend/app/models/api_schemas.py`

**Context:** `ChatMessageResponse` is the Pydantic model returned by `POST /api/v1/chat/message`. It currently has no RAG-related fields. `RagSource` must be defined before `ChatMessageResponse`.

- [ ] **Step 1: Add `RagSource` and new fields**

In `backend/app/models/api_schemas.py`, add `RagSource` immediately before `ChatMessageResponse`, then add the two new fields to `ChatMessageResponse`:

```python
class RagSource(BaseModel):
    title: str
    url: str = ""


class ChatMessageResponse(BaseModel):
    conversation_id: str
    message: str
    agent_node: Optional[str] = None
    proposed_plan: Optional[dict] = None
    requires_user_action: bool = False
    options: Optional[list[OnboardingOptionSchema]] = None
    questions: Optional[list[ClarifierQuestionSchema]] = None
    spoken_summary: Optional[str] = None
    rag_used: bool = False
    rag_sources: list[RagSource] = []
```

- [ ] **Step 2: Verify the backend starts cleanly**

```bash
cd backend && python -c "from app.models.api_schemas import ChatMessageResponse, RagSource; print('OK')"
```

Expected output: `OK`

---

## Task 2: Populate provenance fields in `chat.py` after the LangGraph run

**Files:**
- Modify: `backend/app/api/v1/chat.py`

**Context:** The function `_send_message_events` has two code paths:
1. A short-circuit reschedule path (~lines 95–216) — produces no plan, skip.
2. The main LangGraph path — after `astream_events`, builds `resp = ChatMessageResponse(...)` at ~line 432.

`rag_output` is already in state with shape `{"retrieved": bool, "sources": [{"title": str, "url": str}], "context": str}`.

The `metadata` dict (saved to the `messages` table) is built inside an `if goal_draft and (approval_pending or awaiting_start_date):` block at ~line 383. Add `rag_used`/`rag_sources` there too.

- [ ] **Step 1: Add `RagSource` to the import**

At the top of `backend/app/api/v1/chat.py`, find the line that imports from `app.models.api_schemas` and add `RagSource`:

```python
from app.models.api_schemas import (
    ...
    RagSource,
    ...
)
```

- [ ] **Step 2: Extract RAG provenance upfront**

The metadata block that saves to the DB is at ~line 383, but `resp` isn't built until ~line 432. To use provenance in both places, extract it right after the `awaiting_start_date` assignment (~line 379), before the metadata block:

```python
goal_draft = result.get("goal_draft")
result_approval = result.get("approval_status")
approval_pending = result_approval == "pending"
awaiting_start_date = result_approval == "awaiting_start_date"

# Extract RAG provenance upfront — used in both metadata and resp below
_rag_output = result.get("rag_output") or {}
_rag_used = bool(_rag_output.get("retrieved"))
_rag_sources = [
    RagSource(title=s.get("title", ""), url=s.get("url", ""))
    for s in _rag_output.get("sources", [])
] if _rag_used else []
```

- [ ] **Step 3: Add provenance to the metadata block**

Inside the existing `if goal_draft and (approval_pending or awaiting_start_date):` block (~line 383), add `rag_used` and `rag_sources`:

```python
if goal_draft and (approval_pending or awaiting_start_date):
    metadata: dict | None = {
        "proposed_plan": goal_draft,
        "classifier_output": result.get("classifier_output"),
        "approval_status": result_approval,
        "rag_used": _rag_used,
        "rag_sources": [s.model_dump() for s in _rag_sources],
    }
```

- [ ] **Step 4: Pass provenance into `resp` constructor**

When building `resp` (~line 432), pass `_rag_used` and `_rag_sources` directly:

```python
resp = ChatMessageResponse(
    conversation_id=str(conv_id),
    message=reply,
    agent_node=agent_node_value,
    proposed_plan=goal_draft if approval_pending else None,
    requires_user_action=approval_pending,
    options=None if is_clarifier else raw_options,
    questions=raw_options if is_clarifier else None,
    rag_used=_rag_used,
    rag_sources=_rag_sources,
)
```

- [ ] **Step 5: Verify the backend starts cleanly**

```bash
cd backend && python -c "from app.api.v1.chat import router; print('OK')"
```

Expected output: `OK`

---

## Task 3: Update frontend types

**Files:**
- Modify: `frontend/src/types/message.ts`

**Context:** `ChatMessageResponse` (line 206) is the TypeScript mirror of the Pydantic model. `ChatMessage` (line 221) is the UI-only type used in the React state. Both need updating.

- [ ] **Step 1: Add fields to `ChatMessageResponse`**

In `frontend/src/types/message.ts`, update the `ChatMessageResponse` interface:

```typescript
export interface ChatMessageResponse {
  conversation_id: string;
  message: string;
  agent_node?: string | null;
  proposed_plan?: Record<string, unknown> | null;
  requires_user_action: boolean;
  options?: OnboardingOption[] | null;
  questions?: GoalClarifierQuestion[] | null;
  spoken_summary?: string | null;
  rag_used?: boolean;
  rag_sources?: { title: string; url: string }[];
}
```

- [ ] **Step 2: Add `provenance` field to `ChatMessage`**

In `frontend/src/types/message.ts`, add only the `provenance` field to the existing `ChatMessage` interface — do **not** remove or replace existing fields (`options`, `questions` must stay). The final interface should be:

```typescript
export interface ChatMessage {
  id: string;
  type: MessageVariant;
  content: React.ReactNode;
  options?: OnboardingOption[] | null;
  questions?: GoalClarifierQuestion[] | null;
  provenance?: {
    rag_used: boolean;
    rag_sources: { title: string; url: string }[];
  };
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors related to `message.ts`

---

## Task 4: Create `ProvenanceIndicator` component

**Files:**
- Create: `frontend/src/components/chat/ProvenanceIndicator.tsx`

**Context:** This is a new file. Render rules:
- `rag_used === true` AND `rag_sources.length > 0` → "Sources cited" toggle with expandable source list
- Everything else (LLM-only, or RAG with no sources) → static disclaimer text
- Uses Lucide `ArrowUpRight` icon, `text-xs text-muted-foreground` styling

- [ ] **Step 1: Create the component**

```tsx
import { ArrowUpRight } from "lucide-react";
import { useState } from "react";

interface ProvenanceIndicatorProps {
  ragUsed: boolean;
  ragSources: { title: string; url: string }[];
}

export function ProvenanceIndicator({
  ragUsed,
  ragSources,
}: ProvenanceIndicatorProps) {
  const [expanded, setExpanded] = useState(false);
  const showSources = ragUsed && ragSources.length > 0;

  if (showSources) {
    return (
      <div className="mt-1 px-1">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-0.5 text-xs text-muted-foreground hover:text-muted-foreground/80 transition-colors"
        >
          Sources cited
          <ArrowUpRight className="w-3 h-3 inline-block ml-0.5" />
        </button>
        {expanded && (
          <ul className="mt-1 space-y-0.5">
            {ragSources.map((source) => (
              <li key={source.title} className="text-xs text-muted-foreground">
                {source.url ? (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline"
                  >
                    {source.title}
                  </a>
                ) : (
                  source.title
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return (
    <p className="mt-1 px-1 text-xs text-muted-foreground">
      AI-generated plan · always verify with a professional
    </p>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors in `ProvenanceIndicator.tsx`

---

## Task 5: Wire `ProvenanceIndicator` into `chat.tsx`

**Files:**
- Modify: `frontend/src/routes/chat.tsx`

**Context:** Two places need to set `provenance` on a `ChatMessage`, and one place needs to render `ProvenanceIndicator`.

**Rendering:** The message loop is at ~line 715. `ChatBubble` wraps `message.content`. `OnboardingOptions` is already rendered as a sibling outside `ChatBubble`. `ProvenanceIndicator` follows the same sibling pattern.

**New message path (`handleSendMessage`):** `aiMessage` is built at ~line 546. `provenance` should be set when `result.proposed_plan` is present (i.e. when `parsed` is non-null).

**History path (`loadConversation`):** `uiMessages` are mapped at ~line 626. `provenance` should be set when `m.metadata?.proposed_plan` is present (same gate used for `parsed`).

- [ ] **Step 1: Import `ProvenanceIndicator`**

At the top of `frontend/src/routes/chat.tsx`, add:

```tsx
import { ProvenanceIndicator } from "~/components/chat/ProvenanceIndicator";
```

- [ ] **Step 2: Populate `provenance` in `handleSendMessage`**

In the `aiMessage` object (~line 546), add `provenance` after `options`:

```tsx
const aiMessage: ChatMessage = {
  id: msgId,
  type: MessageVariant.AI,
  content: ( /* unchanged */ ),
  options: result.options,
  provenance: result.proposed_plan
    ? {
        rag_used: result.rag_used ?? false,
        rag_sources: result.rag_sources ?? [],
      }
    : undefined,
};
```

- [ ] **Step 3: Populate `provenance` in `loadConversation`**

In the `uiMessages` map (~line 626), add `provenance` to the returned object:

```tsx
return {
  id: `history-${i}`,
  type: m.role === "user" ? MessageVariant.USER : MessageVariant.AI,
  content: ( /* unchanged */ ),
  provenance:
    m.role === "assistant" && m.metadata?.proposed_plan
      ? {
          rag_used: (m.metadata.rag_used as boolean) ?? false,
          rag_sources:
            (m.metadata.rag_sources as { title: string; url: string }[]) ?? [],
        }
      : undefined,
};
```

- [ ] **Step 4: Render `ProvenanceIndicator` in the message loop**

In the message render loop (~line 715), add `ProvenanceIndicator` as a sibling of `ChatBubble`, right after it, following the same pattern as `OnboardingOptions`:

```tsx
<motion.div key={message.id} ...>
  <ChatBubble variant={message.type} animate={false}>
    {message.content}
  </ChatBubble>
  {message.type === MessageVariant.AI && message.provenance && (
    <ProvenanceIndicator
      ragUsed={message.provenance.rag_used}
      ragSources={message.provenance.rag_sources}
    />
  )}
  {message.type === MessageVariant.AI &&
    message.options &&
    message.options.length > 0 && (
      <OnboardingOptions
        options={message.options}
        onSelect={handleSendMessage}
        disabled={isThinking}
      />
    )}
</motion.div>
```

- [ ] **Step 5: Verify TypeScript compiles with no errors**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -40
```

Expected: zero errors

- [ ] **Step 6: Verify the frontend dev server starts**

```bash
cd frontend && npm run dev 2>&1 | head -20
```

Expected: no compile/import errors in the startup output

---

## Manual Testing Checklist

Once the feature is deployed locally:

- [ ] Send a health/fitness goal (e.g. "I want to lose 10 pounds in 6 weeks") — verify the plan message shows "Sources cited ↗"
- [ ] Click "Sources cited ↗" — verify the source list expands
- [ ] Click again — verify it collapses
- [ ] Send a non-health goal (e.g. "I want to learn guitar") — verify the plan message shows "AI-generated plan · always verify with a professional"
- [ ] Reload the page (conversation persisted in URL) — verify the indicator still appears on both message types after history reload
- [ ] Verify the indicator does NOT appear on non-plan messages (reschedule, onboarding options, etc.)
- [ ] To test the "RAG active but no sources" fallback: temporarily set `_rag_sources = []` while keeping `_rag_used = True` in `chat.py`, send a health goal, and verify the plan message shows "AI-generated plan · always verify with a professional" (not "Sources cited"). Revert after testing.
