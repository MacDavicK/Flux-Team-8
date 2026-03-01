# Cursor Prompt: Post-Merge Frontend Verification & Repair

## Context

You are working on the **Flux** project (`~/Downloads/Flux`).  
A branch integration merge was just completed by Claude Code CLI, creating branch `integration/pre-release` from `main`.

The merge brought in code from 4 branches in this order:
1. `conv_agent` — docs only (no FE impact)
2. `feature/ci-automated-testing` — CI workflows, test scaffolding, FE config changes
3. `backend` — Scheduler Agent BE + FE (SCRUM-30: scheduler_agent.py, RescheduleModal, FlowTimeline, api.ts, etc.)
4. Voice files cherry-picked from `feature/scheduler-fe` — `speech.d.ts` + `useVoiceNegotiation.ts`

**Your job:** Verify the frontend compiles, all imports resolve, and the merged code is coherent. Fix any TypeScript errors or broken imports caused by the merge. Do NOT change application logic — only fix integration issues.

---

## Step 1: Audit — Read Before Writing

Read these files first to understand the current state:

```
frontend/package.json                              — check dependencies are complete
frontend/tsconfig.json                             — check paths, module resolution
frontend/vite.config.ts                            — check aliases, plugins
frontend/biome.json                                — check lint rules

frontend/src/routes/index.tsx                      — main page, imports FlowTimeline + RescheduleModal
frontend/src/components/flow/v2/FlowTimeline.tsx   — timeline component
frontend/src/components/flow/v2/TimelineEvent.tsx  — event pebble component
frontend/src/components/modals/RescheduleModal.tsx — negotiation modal (API-driven)
frontend/src/utils/api.ts                          — API client (scheduler endpoints)
frontend/src/utils/useVoiceNegotiation.ts          — voice hook (SCRUM-34)
frontend/src/types/speech.d.ts                     — Web Speech API type declarations
```

Also check for any new files the `feature/ci-automated-testing` branch brought:
```
frontend/vitest.config.ts
frontend/src/test/setup.ts
frontend/src/test/smoke.test.ts
```

---

## Step 2: TypeScript Compilation Check

Run:
```bash
cd ~/Downloads/Flux/frontend
npx tsc --noEmit 2>&1
```

If there are errors, categorize them:

### Category A: Missing imports (merge artifact)
Fix by adding the missing import statement. Example:
- `useVoiceNegotiation` imported in `RescheduleModal.tsx` but file path wrong → fix import path
- `speech.d.ts` not included in tsconfig → add to `include` array

### Category B: Type mismatches (version conflict)
If `FlowTimeline.tsx` expects a prop interface that doesn't match what `index.tsx` passes, reconcile by checking which version is more complete. The `backend` branch (`1909c31`) version is canonical — preserve its interfaces.

### Category C: Duplicate declarations
If `feature/ci-automated-testing` and `backend` both declare the same type/component differently, keep the `backend` version and remove the duplicate.

---

## Step 3: Verify Voice Integration (SCRUM-34)

The `useVoiceNegotiation.ts` hook was cherry-picked from `feature/scheduler-fe` but the `RescheduleModal.tsx` came from `backend`. Check if:

1. `RescheduleModal.tsx` imports `useVoiceNegotiation` — if NOT, it needs to be wired in.
2. The hook's interface matches what the modal expects.

**If the modal does NOT import the voice hook:** The `backend` branch version of the modal may not have the voice integration that was in `feature/scheduler-fe`. In that case:

Add the voice layer to `RescheduleModal.tsx`:
- Import `useVoiceNegotiation` from `../../utils/useVoiceNegotiation`
- Add voice state management (speaking, listening indicators)
- Wire `speak()` to fire when modal opens with AI message
- Wire `startListening()` after TTS completes
- Map detected commands ("yes" → accept first suggestion, "tomorrow" → accept tomorrow slot, "skip" → skip today)
- Add a `VITE_ENABLE_VOICE` env check so voice is opt-in

Reference the hook's exported interface:
```typescript
// useVoiceNegotiation exports:
{
  speak: (text: string) => void;
  startListening: () => void;
  stopListening: () => void;
  isListening: boolean;
  isSpeaking: boolean;
  lastCommand: string | null;
  isSupported: boolean;
}
```

---

## Step 4: Verify API Client Coherence

Check `frontend/src/utils/api.ts`:
- Must export `fetchSchedulerSuggestions(eventId: string)` — calls `POST /scheduler/suggest`
- Must export `applyReschedule(eventId: string, newStart: string, newEnd: string)` — calls `POST /scheduler/apply`
- Must export `fetchTodayTasks()` — calls `GET /scheduler/tasks` (if this endpoint exists in the backend branch)
- Must use the correct base URL from env: `VITE_API_URL` or fallback to `http://localhost:8000`

Also check `frontend/src/lib/apiClient.ts` — the `feature/ci-automated-testing` branch may have brought in a competing API client. If both exist:
- Keep `src/utils/api.ts` as the scheduler-specific client
- Keep `src/lib/apiClient.ts` as the generic client
- Ensure no circular imports between them

---

## Step 5: Verify CI Test Configuration

Check that the test scaffolding from `feature/ci-automated-testing` still works:
```bash
cd ~/Downloads/Flux/frontend
npx vitest run --reporter=verbose 2>&1 | head -30
```

If tests fail due to missing modules or import errors introduced by the merge, fix the imports. Do NOT rewrite test logic.

---

## Step 6: Dev Server Smoke Test

```bash
cd ~/Downloads/Flux/frontend
npm run dev
```

Verify the dev server starts without errors. Check the terminal output for:
- No "Module not found" errors
- No "Cannot resolve" errors
- Vite HMR connects successfully

---

## Step 7: Environment File

Ensure `frontend/.env.example` exists with these keys (no real values):
```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_URL=http://localhost:8000
VITE_USE_MOCK=true
VITE_ENABLE_VOICE=false
VITE_ENABLE_DEMO_MODE=false
```

If `.env.example` doesn't exist, create it. If `.env` contains real keys, do NOT commit it — ensure it's in `.gitignore`.

---

## Rules

1. **Do NOT change application logic.** Only fix compilation errors, broken imports, and merge artifacts.
2. **Do NOT delete any files** unless they are exact duplicates created by the merge.
3. **The `backend` branch version of any file is canonical** when there's a conflict between versions.
4. **All changes must compile clean:** `npx tsc --noEmit` must pass with 0 errors before you're done.
5. **Commit message format:** `fix(merge): <description of what was fixed>`
6. **If you encounter errors that require application logic changes** (not just import fixes), STOP and list them. Do not guess at the correct behavior.
