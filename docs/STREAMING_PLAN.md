# Plan: Real-Time LangGraph Progress Streaming

## Context

LangGraph calls take 5–11s (observed in LangSmith traces). The frontend shows a static
`ThinkingIndicator` during this time, giving users the perception of a hang or error.

The fix: replace the blocking `ainvoke()` call with `astream_events()` and convert
`POST /api/v1/chat/message` to return an SSE stream. The frontend parses the stream
and updates `ThinkingIndicator` with the current node's human-readable label in
real time. When the stream ends with a `complete` event, the existing rendering
logic runs unchanged.

---

## Decisions Made

| Decision | Reason |
|----------|--------|
| SSE over WebSocket | One-directional; HTTP-native; no protocol upgrade |
| Replace existing endpoint (not add `/stream`) | Cleaner API surface, no dead code |
| `on_chain_start` events only (no `on_chain_end`) | Start events are enough for label updates |
| `astream_events(version="v2")` over `astream` | Node-level granularity, not full state diffs |
| Labels live on the frontend | Decouples UI copy from graph code |
| Enhance `ThinkingIndicator` (not new component) | YAGNI |
| Basic error handling, no retry | Sufficient for local dev |

---

## SSE Event Protocol

Two event types emitted by the backend over `text/event-stream`:

```
data: {"type": "progress", "node": "goal_planner_node"}\n\n

data: {"type": "complete", "data": {<ChatMessageResponse as JSON>}}\n\n

data: {"type": "error", "message": "..."}\n\n
```

Rules:
- `progress` events fire when a node starts (one per node entry, including parallel fan-out nodes)
- `complete` is always the last event; DB persistence happens before it is emitted
- `error` terminates the stream on an unhandled exception
- RESCHEDULE_TASK short-circuit (no LangGraph) emits only `complete` directly

---

## Step-by-Step Implementation

---

### STEP 1 — Backend: Refactor `POST /api/v1/chat/message`

**File:** `backend/app/api/v1/chat.py`

#### 1a. Add imports at top of file

```python
# Add to existing imports
from fastapi.responses import StreamingResponse
import asyncio
```

#### 1b. Replace the `@router.post` decorator and function signature

**Remove:**
```python
@router.post("/message", response_model=ChatMessageResponse)
@limiter.limit("20/minute")
async def send_message(
    request: Request,
    body: ChatMessageRequest,
    current_user=Depends(get_current_user),
) -> ChatMessageResponse:
```

**Replace with:**
```python
@router.post("/message")
@limiter.limit("20/minute")
async def send_message(
    request: Request,
    body: ChatMessageRequest,
    current_user=Depends(get_current_user),
) -> StreamingResponse:
    """SSE stream. Events: progress | complete | error (text/event-stream)."""
    return StreamingResponse(
        _send_message_events(body, current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
```

#### 1c. Extract logic into async generator `_send_message_events`

Move the entire body of the existing `send_message` function into a new private
async generator function. Replace the two key parts:

**Replace `return resp` in the RESCHEDULE_TASK short-circuit (around line 144):**
```python
# OLD:
resp.spoken_summary = build_spoken_summary(resp)
return resp

# NEW:
resp.spoken_summary = build_spoken_summary(resp)
yield f"data: {json.dumps({'type': 'complete', 'data': resp.model_dump()})}\n\n"
return
```

**Replace the `ainvoke` call (around line 277) with `astream_events`:**

```python
# OLD:
result: dict = await _graph_module.compiled_graph.ainvoke(
    state,
    config={"configurable": {"thread_id": langgraph_thread_id}},
)

# NEW:
result: dict | None = None
try:
    async for event in _graph_module.compiled_graph.astream_events(
        state,
        version="v2",
        config={"configurable": {"thread_id": langgraph_thread_id}},
    ):
        if event["event"] == "on_chain_start":
            node = event.get("metadata", {}).get("langgraph_node")
            if node:
                yield f"data: {json.dumps({'type': 'progress', 'node': node})}\n\n"
        elif event["event"] == "on_chain_end" and event.get("name") == "LangGraph":
            result = event["data"].get("output")
except Exception as exc:
    yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
    return

if result is None:
    yield f"data: {json.dumps({'type': 'error', 'message': 'Graph produced no output'})}\n\n"
    return
```

**Replace `return resp` at the bottom of the function:**
```python
# OLD:
resp.spoken_summary = build_spoken_summary(resp)
return resp

# NEW:
resp.spoken_summary = build_spoken_summary(resp)
yield f"data: {json.dumps({'type': 'complete', 'data': resp.model_dump()})}\n\n"
```

**Full generator signature:**
```python
async def _send_message_events(
    body: ChatMessageRequest,
    current_user: dict,
):
    """Async generator yielding SSE events for the chat message endpoint."""
    # ... (entire body of the old send_message, with replacements above)
```

**Important notes:**
- `resp.model_dump()` serializes the `ChatMessageResponse` Pydantic model to a dict.
  If any fields contain non-JSON-serializable types (e.g., `datetime`), use
  `resp.model_dump(mode="json")` instead.
- The `@limiter.limit` decorator still applies to `send_message` (the outer function),
  not the generator — this is correct.
- `response_model=ChatMessageResponse` is removed from the decorator because FastAPI
  doesn't validate `StreamingResponse` bodies.

---

### STEP 2 — Frontend: Create `nodeLabels.ts`

**New file:** `frontend/src/lib/nodeLabels.ts`

```typescript
/**
 * Maps LangGraph node names to human-readable progress labels.
 * Shown in ThinkingIndicator while the backend processes a chat message.
 *
 * Keys must match the names passed to graph.add_node() in graph.py —
 * WITHOUT the _node suffix (e.g. "orchestrator" not "orchestrator_node").
 * astream_events emits metadata.langgraph_node using the add_node() name.
 */
export const NODE_LABELS: Record<string, string> = {
  orchestrator: "Understanding your request...",
  goal_clarifier: "Analyzing your goal...",
  goal_planner: "Building your 6-week plan...",
  classifier: "Categorizing your goal...",
  scheduler: "Scheduling your tasks...",
  pattern_observer: "Identifying habit patterns...",
  save_tasks: "Saving your plan...",
  ask_start_date: "Almost there...",
  onboarding: "Getting to know you...",
  chitchat: "Thinking...",
  task_handler: "Processing your task...",
  goal_modifier: "Updating your goal...",
  reschedule: "Rescheduling your tasks...",
};

export function getNodeLabel(node: string): string {
  return NODE_LABELS[node] ?? "Working on it...";
}
```

---

### STEP 3 — Frontend: Update `ChatService.ts`

**File:** `frontend/src/services/ChatService.ts`

Replace the existing `sendMessage` method with a streaming version.

The method signature is **unchanged** from the caller's perspective — it still returns
`Promise<ChatMessageResponse>`. The streaming is internal.

Key approach: use `apiFetch` (which adds the auth header) to get the `Response`, then
read `response.body` as a `ReadableStream`.

```typescript
async sendMessage(
  message: string,
  conversationId?: string,
  options?: {
    intent?: string;
    task_id?: string;
    answers?: GoalClarifierAnswer[];
  },
  onProgress?: (label: string) => void,
): Promise<ChatMessageResponse> {
  const response = await apiFetch("/api/v1/chat/message", {
    method: "POST",
    body: JSON.stringify({
      message,
      conversation_id: conversationId ?? null,
      ...(options?.intent ? { intent: options.intent } : {}),
      ...(options?.task_id ? { task_id: options.task_id } : {}),
      ...(options?.answers ? { answers: options.answers } : {}),
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to send chat message");
  }

  // Parse SSE stream
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    // Keep incomplete last line in buffer
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (!raw) continue;

      let event: { type: string; node?: string; data?: unknown; message?: string };
      try {
        event = JSON.parse(raw);
      } catch {
        continue;
      }

      if (event.type === "progress" && event.node && onProgress) {
        const { getNodeLabel } = await import("~/lib/nodeLabels");
        onProgress(getNodeLabel(event.node));
      } else if (event.type === "complete") {
        return event.data as ChatMessageResponse;
      } else if (event.type === "error") {
        throw new Error(event.message ?? "Stream error");
      }
    }
  }

  throw new Error("Stream ended without a complete event");
}
```

**Note on `import("~/lib/nodeLabels")`:** This is a dynamic import to avoid a circular
dependency risk. Alternatively, import `getNodeLabel` statically at the top of the file —
both work.

---

### STEP 4 — Frontend: Update `ThinkingIndicator.tsx`

**File:** `frontend/src/components/chat/ThinkingIndicator.tsx`

Add an optional `label` prop. When provided, show it as muted italic text next to the
bouncing dots.

```tsx
import { motion } from "framer-motion";

interface ThinkingIndicatorProps {
  label?: string;
}

export function ThinkingIndicator({ label }: ThinkingIndicatorProps) {
  return (
    <div className="flex items-center gap-2 py-4 px-2">
      <div className="flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-2 h-2 rounded-full bg-sage/60"
            animate={{
              y: [0, -8, 0],
              opacity: [0.4, 1, 0.4],
            }}
            transition={{
              duration: 1.2,
              repeat: Infinity,
              delay: i * 0.15,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>
      {label && (
        <span className="text-sm text-muted-foreground italic">{label}</span>
      )}
    </div>
  );
}
```

---

### STEP 5 — Frontend: Update `chat.tsx`

**File:** `frontend/src/routes/chat.tsx`

#### 5a. Add `progressLabel` state

Find where `isThinking` state is declared (search for `setIsThinking`) and add a
new state variable alongside it:

```typescript
const [progressLabel, setProgressLabel] = useState<string | undefined>(undefined);
```

#### 5b. Update `handleSendMessage` to pass `onProgress`

In `handleSendMessage` (around line 454), replace:

```typescript
// OLD:
const result = await chatService.sendMessage(
  text,
  conversationIdRef.current,
);
```

```typescript
// NEW:
const result = await chatService.sendMessage(
  text,
  conversationIdRef.current,
  undefined,
  (label) => setProgressLabel(label),
);
```

For the call that passes `options` (GOAL_CLARIFY path), find all other invocations of
`chatService.sendMessage` with options and add `onProgress` as the 4th argument
in the same way. Search for all `chatService.sendMessage(` occurrences in `chat.tsx`.

#### 5c. Clear `progressLabel` when thinking ends

Find `setIsThinking(false)` calls and add `setProgressLabel(undefined)` alongside each:

```typescript
// In the setTimeout callback (line ~470):
setIsThinking(false);
setProgressLabel(undefined);

// In the catch block (line ~524):
setIsThinking(false);
setProgressLabel(undefined);

// In the reschedule .then()/.catch() callbacks (lines ~405-433):
setIsThinking(false);
setProgressLabel(undefined);
```

#### 5d. Pass `label` to `ThinkingIndicator`

Find the JSX where `<ThinkingIndicator />` is rendered (likely in the messages
rendering area or `isThinking` conditional) and pass the label:

```tsx
// OLD:
{isThinking && <ThinkingIndicator />}

// NEW:
{isThinking && <ThinkingIndicator label={progressLabel} />}
```

---

## Critical Files

| File | Change |
|------|--------|
| `backend/app/api/v1/chat.py` | Convert `send_message` to return SSE; extract `_send_message_events` generator; replace `ainvoke` with `astream_events` |
| `frontend/src/services/ChatService.ts` | Replace `sendMessage` with streaming SSE parser; add `onProgress` callback param |
| `frontend/src/routes/chat.tsx` | Add `progressLabel` state; pass `onProgress` to `sendMessage`; clear label on finish; pass `label` to `ThinkingIndicator` |
| `frontend/src/components/chat/ThinkingIndicator.tsx` | Add optional `label` prop and render muted italic text |

## New Files

| File | Purpose |
|------|---------|
| `frontend/src/lib/nodeLabels.ts` | Maps LangGraph node names → human readable labels |

---

## Verification

### Manual Test 1: Goal creation (full graph path)
1. Start backend + frontend
2. Send: "I want to learn piano in 3 months"
3. Watch `ThinkingIndicator` — expect labels to cycle:
   - "Understanding your request..." (orchestrator_node)
   - "Analyzing your goal..." (goal_clarifier_node)
   - "Building your 6-week plan..." (goal_planner_node)
   - "Categorizing your goal..." / "Scheduling your tasks..." / "Identifying habit patterns..." (parallel fan-out)
   - "Saving your plan..." (save_tasks_node) — if plan is approved immediately
4. Final `ChatMessageResponse` renders correctly with clarifier questions or plan

### Manual Test 2: Chitchat (short path)
1. Send: "hi"
2. Expect only "Understanding your request..." → "Thinking..." → response

### Manual Test 3: Reschedule (no LangGraph)
1. Navigate to a task reschedule URL (or trigger from home page)
2. No progress labels expected — `complete` event fires immediately
3. `ThinkingIndicator` briefly appears with no label, then response renders

### Manual Test 4: Error handling
1. Kill the backend mid-request (Ctrl+C while request is in flight)
2. Frontend should show the error message: "Sorry, I had trouble understanding that."

### Curl smoke test (backend)
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "hi", "conversation_id": null}' \
  --no-buffer
```
Expected output:
```
data: {"type": "progress", "node": "orchestrator"}
data: {"type": "progress", "node": "chitchat"}
data: {"type": "complete", "data": {"conversation_id": "...", "message": "Hey! ...", ...}}
```

---

## Gotchas / Notes

1. **`astream_events` graph name**: The top-level graph emits `on_chain_end` with
   `name == "LangGraph"` (the default LangGraph compiled graph name). If the graph was
   compiled with a custom name, adjust accordingly. Check `_graph_module.compiled_graph.name`.

2. **Parallel fan-out events**: When `Send()` fires classifier/scheduler/pattern_observer
   in parallel, their `on_chain_start` events may arrive in rapid succession. The UI label
   just updates to the last one — this is acceptable behaviour.

3. **`model_dump(mode="json")`**: If `ChatMessageResponse` contains datetime fields or
   other non-JSON-serializable types, use `resp.model_dump(mode="json")` to ensure
   proper serialization before `json.dumps`.

4. **Rate limiter**: The `@limiter.limit("20/minute")` decorator remains on the outer
   `send_message` function — this is correct and applies before the generator starts.

5. **`apiFetch` compatibility**: `apiFetch` returns a standard `Response` object from
   the browser `fetch` API. `response.body` is a `ReadableStream<Uint8Array>` — this
   is what the `getReader()` call in `ChatService` reads from. No changes needed to
   `apiFetch` itself.

6. **`setTimeout(..., 800)` in chat.tsx**: The existing code delays rendering the AI
   response by 800ms after receiving it. This delay still applies after the `complete`
   event is received — it's intentional UX polish. Keep it.
