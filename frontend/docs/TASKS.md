# Frontend Migration Tasks

> Generated from diff between current frontend code and `src/types/api.d.ts` (the real backend OpenAPI spec).
> Scoped to the three screens the frontend actually implements: **Flow**, **Chat**, and **Reflection**.

---

## Status

**All 9 tasks completed.** The frontend now calls real `/api/v1/...` endpoints via new services.

---

## Summary of Changes

| Screen | Old Service(s) | New Service(s) | Real Endpoints |
|--------|---------------|----------------|----------------|
| Flow (Home) | `TasksService.getTasks()` | `TasksService.getTodayTasks()`, `TasksService.rescheduleTask()` | `GET /api/v1/tasks/today`, `POST /api/v1/tasks/{id}/reschedule` |
| Chat | `GoalPlannerService`, `OnboardingService` | `ChatService.sendMessage()`, `AccountService.patchMe()` | `POST /api/v1/chat/message`, `PATCH /api/v1/account/me` |
| Reflection | `UserService.*` | `AccountService.getMe()`, `.getOverview()`, `.getWeeklyStats()`, `.getMissedByCategory()` | `GET /api/v1/account/me`, `GET /api/v1/analytics/*` |
| Demo/Simulation | `GoalPlannerService.triggerSimulation()` | `DemoService.triggerLocation()` | `POST /api/v1/demo/trigger-location` |

---

## New Files Created

| File | Purpose |
|------|---------|
| `src/services/AccountService.ts` | `getMe()`, `patchMe()`, `getOverview()`, `getWeeklyStats()`, `getMissedByCategory()` |
| `src/services/ChatService.ts` | `sendMessage(message, conversationId?)` |
| `src/services/DemoService.ts` | `triggerLocation()` |
| `public/site.webmanifest` | PWA web manifest (required by `__root.tsx` link tag) |

## Modified Files

| File | Change |
|------|--------|
| `src/services/TasksService.ts` | Rewritten: `getTodayTasks()` + `rescheduleTask()` |
| `src/routes/reflection.tsx` | Uses `accountService` instead of `userService` |
| `src/routes/chat.tsx` | Uses `chatService` + `accountService`; removed `agentState`/`GoalContext` state |
| `src/routes/index.tsx` | Uses `getTodayTasks()`, wires up `rescheduleTask()` |
| `src/routes/__root.tsx` | Uses `demoService` instead of `goalPlannerService` |
| `src/contexts/SimulationContext.tsx` | Uses `demoService` instead of `goalPlannerService` |
| `src/types/user.ts` | Removed stale onboarding types; added `AccountMe`, `AccountPatchRequest`; legacy analytics shapes kept with `@deprecated` tags |
| `src/types/message.ts` | Added `ChatMessageRequest`, `ChatMessageResponse` |
| `src/types/task.ts` | Added `RescheduleRequest` |
| `src/types/index.ts` | Updated exports |

## Deleted Files (cleanup completed Mar 2026)

The following files were removed as part of the MSW removal and service cleanup:

- `src/services/UserService.ts`
- `src/services/GoalPlannerService.ts`
- `src/services/OnboardingService.ts`
- `src/mocks/` — entire directory deleted (MSW removed; app talks directly to backend)
- `public/mockServiceWorker.js` — MSW service worker artifact

---

## Notes

- **Auth**: `AuthService` already uses Supabase SDK — no changes needed.
- **Conversation ID**: `chat.tsx` persists `conversation_id` from the first `ChatMessageResponse` in component state.
- **`requires_user_action`**: `chat.tsx` renders a "Confirm" button when the flag is true.
- **`proposed_plan`**: mapped to `PlanView` component via cast to `PlanMilestone[]`.
- **Reflection analytics**: `accountService` methods return `unknown[]` / `{[key: string]: unknown}`. Mapping to legacy component shapes is done in `reflection.tsx`. Legacy types (`UserStatsResponse`, etc.) kept with `@deprecated` tags until components are updated.
- **Flow tasks**: `index.tsx` maps raw backend task objects to `TimelineEvent` / `TaskRailItem` shapes via `mapTaskToDisplayTypes()`.
