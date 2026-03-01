# Agent Memory: Flux Codebase

This file serves as a persistent memory for AI agents working on the Flux project. It contains essential information about the tech stack, architecture, and common patterns.

## 1. Tech Stack Overview
- **Framework**: TanStack Start (React + SSR)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4 (configured via CSS variables in `src/styles/app.css`)
- **Routing**: TanStack Router (File-based in `src/routes`)
- **State**: URL-based (Search Params) + Server State (Loaders) + Local React State
- **Icons**: Lucide React
- **Animations**: Framer Motion
- **API Mocking**: Removed — app talks directly to the backend (localhost:8000 in dev)
- **Auth**: Server-side via `@supabase/ssr`. Supabase keys live in `process.env` only (no `VITE_` prefix). All auth ops are TanStack Start server functions in `src/lib/authServerFns.ts`. No Supabase SDK on the client.
- **Session Storage**: httpOnly cookies (set server-side by `@supabase/ssr`) + React module-level memory (`_inMemoryToken` in `src/lib/apiClient.ts`). Never localStorage.

## 2. Key Architecture Patterns

### Auth & Session (current)
- **No client-side Supabase SDK** — `src/lib/supabase.ts` has been deleted. Do not recreate it.
- **Server client**: `src/lib/supabaseServer.ts` — `@supabase/ssr` `createServerClient` with TanStack Start cookie adapters (`getCookies`/`setCookie`). SERVER-ONLY; never import from client code.
- **Server functions**: `src/lib/authServerFns.ts` — all auth operations as `createServerFn`:
  - `serverLogin` — `signInWithPassword`, sets httpOnly cookie via `@supabase/ssr`
  - `serverSignup` — `signUp`, sets httpOnly cookie
  - `serverLogout` — `signOut`, also explicitly deletes known Supabase cookie names
  - `serverGetAccessToken` — reads session from cookie server-side, returns `{ token, user }`; called on React mount to hydrate in-memory token
  - `serverGetGoogleOAuthUrl` — generates Google OAuth URL server-side (`skipBrowserRedirect: true`), returns `{ url }` to client
- **AuthService** (`src/services/AuthService.ts`) — thin wrapper around server functions. No Supabase SDK import.
- **AuthContext** (`src/contexts/AuthContext.tsx`) — calls `serverGetAccessToken` on mount to hydrate `_inMemoryToken` via `setInMemoryToken`. Periodically refreshes every 45 min. Exposes: `login`, `signup`, `logout`, `loginWithGoogle`, `refreshAuthStatus`.
- **In-memory token**: `_inMemoryToken` in `src/lib/apiClient.ts`. Set via `setInMemoryToken(token)`, read by `apiFetch`. Cleared on logout or page refresh (re-hydrated on next mount).

### Google OAuth Flow (current)
1. `loginWithGoogle()` in `AuthContext` → `authService.loginWithGoogle()` → `serverGetGoogleOAuthUrl()` (server fn) → returns URL
2. Client sets `window.location.href = url` — browser navigates to Google
3. Google redirects to `/auth/callback?code=...`
4. `src/routes/auth/callback.tsx` **loader** runs server-side → calls `exchangeOAuthCode` server fn → `exchangeCodeForSession` → `@supabase/ssr` sets httpOnly cookie → HTTP 302 redirect to `/`
5. On `/` mount, `AuthContext.refreshAuthStatus()` calls `serverGetAccessToken` → hydrates `_inMemoryToken`

### Authenticated API Requests
- ALL backend `/api/v1/*` calls must include `Authorization: Bearer <token>`.
- Use `apiFetch` from `~/lib/apiClient` — it injects `_inMemoryToken` automatically.
- Never call raw `fetch()` in services.
- Token is never in localStorage; it lives in module memory, seeded from the httpOnly cookie via server function on each page load.

### Glassmorphism
The design relies heavily on `backdrop-filter`, translucent backgrounds, and organic borders.

### Splash Screen
Shows on every page load/refresh for 3 seconds. Later will be used to load initial data from server.

### Centralized Type System
All domain types are organized in `src/types/` with domain-specific files (e.g., `user.ts`, `task.ts`) and barrel exports via `index.ts`.

### SSR Safety
TanStack Start runs components on the server during SSR. Browser-only globals (`document`, `window`, `navigator`) are unavailable in Node.js. Always use `isClient()` / `isServer()` from `~/utils/env` to guard such code. Never access browser globals at the module top level or synchronously during render.

### Onboarding Flow
Onboarding uses the `/chat` route. When a user is not onboarded (`user.onboarded === false`), the chat screen displays onboarding questions instead of regular chat. The bottom navigation is hidden during onboarding.

### Data Fetching
- Page-level data: Fetched via TanStack Router `loader` functions (blocking, before page renders).
- Component-level data: Fetched via `useEffect` with local state (non-blocking, shows loading states).

### Loading States
Each component section has its own glassmorphic loading state component (e.g., `StatsLoadingState`, `EnergyAuraLoadingState`).

### Real API Base
All backend endpoints use the `/api/v1/` prefix. The OpenAPI spec is in `src/types/api.d.ts` (auto-generated — do not edit).

### Conversation State
`POST /api/v1/chat/message` returns a `conversation_id`. Persist this in component state or URL search params to maintain chat continuity across messages.

### Onboarding Check
User onboarding state is determined by `AccountMeResponse.onboarded` from `GET /api/v1/account/me`. There is no separate `/api/onboarding/` endpoint.

### Patterns Domain
AI-detected behavioral patterns available via `/api/v1/patterns/`. New — no UI exists yet.

### Component Structure
- `src/components/ui`: Atomic, reusable components (GlassCard, Button, etc.).
- `src/components/{feature}`: Feature-specific molecules (e.g., `src/components/chat`).

### Routing
- Root layout: `src/routes/__root.tsx`.
- Pages: `src/routes/index.tsx` (Flow), `src/routes/chat.tsx` (Chat + Onboarding), etc.

### Navigation Visibility
The bottom navigation (`BottomNav`) is hidden on the login page and when the user is not yet onboarded.

## 3. Important Rules for Agents

### Env Vars
- Supabase env vars MUST use `process.env` with **no `VITE_` prefix**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `APP_URL`, `APP_ENV`.
- Never expose these to the client bundle. They belong in `frontend/.env` and are read only in server functions / `supabaseServer.ts`.

### Styling
ALWAYS use Tailwind classes. Do NOT create new CSS files. Use `src/styles/app.css` for global theme variables.

### Data Fetching
NEVER use direct `fetch` calls in React components. ALWAYS use services from `src/services/`:
- Services encapsulate API logic (URL construction, error handling, response parsing).
- Example: Use `accountService.getMe()` instead of `fetch("/api/v1/account/me")`.
- Current service files:
  - `AccountService` — user account + analytics endpoints
  - `ChatService` — chat message + history endpoints
  - `TasksService` — task CRUD + actions (complete, miss, reschedule)
  - `GoalsService` — goal list, detail, abandon, modify
  - `PatternsService` — pattern list, detail, patch, delete
  - `DemoService` — demo/trigger-location
  - `AuthService` — thin wrapper around `authServerFns` (no Supabase SDK; do NOT call `/api/auth/` endpoints)
- Each service method returns a typed Promise and handles errors consistently.
- **All services MUST use `apiFetch` from `~/lib/apiClient`** — injects `_inMemoryToken` as `Authorization: Bearer <token>`.

### Auth Rules
- NEVER import `@supabase/supabase-js` or `@supabase/ssr` in client components or services.
- NEVER use `getSupabaseClient()` — the old `src/lib/supabase.ts` singleton is deleted.
- NEVER store tokens in `localStorage` or readable cookies.
- `AuthContext` methods are the only public API for auth in components: `login`, `signup`, `logout`, `loginWithGoogle`, `refreshAuthStatus`.
- `serverGetAccessToken`, `serverLogin`, `serverSignup`, `serverLogout`, `serverGetGoogleOAuthUrl` are server-fn internals — do not call from components directly (use `AuthContext` / `AuthService`).

### New Components
Place in `src/components`. Prefer composition over inheritance.

### Routing
To add a page, create a file in `src/routes`. `routeTree.gen.ts` is auto-generated; DO NOT edit it manually.

### Icons
Use `lucide-react`.

### Types
Place new domain types in `src/types/` organized by entity (e.g., `user.ts`, `task.ts`). Export from `src/types/index.ts`.
- Import types from `~/types` (e.g., `import { User, Task } from '~/types'`).
- Use union types for polymorphic content with strict type guards.
- Define strict required vs optional fields; use `?` for optional, never use `any`.

### SSR Safety
NEVER access `document`, `window`, or `navigator` directly in services, utilities, or components without an SSR guard. ALWAYS use the helpers from `~/utils/env`:
```typescript
import { isClient } from "~/utils/env";

if (!isClient()) return; // safe to use browser globals below
```
Violating this causes a `ReferenceError: document is not defined` crash during server rendering.

### API Mocking
MSW has been removed. The app talks directly to the backend. In development the backend runs on `localhost:8000`. Do not add new MSW handlers or restore the `src/mocks/` directory.

### Loading States
- Create feature-specific loading state components (e.g., `StatsLoadingState`).
- Use glassmorphic design with pulsing animations.
- Match the structure of the loaded component.

## 4. Real API Contract

The backend API spec is auto-generated in `src/types/api.d.ts`. **Do not edit that file.** Use it as a reference only.

### Base URL
All endpoints: `/api/v1/`

### Endpoint Summary

| Domain | Method | Path | Notes |
|--------|--------|------|-------|
| **Chat** | POST | `/api/v1/chat/message` | Send message; returns `ChatMessageResponse` with `conversation_id`, `message`, `requires_user_action`, optional `proposed_plan` |
| | GET | `/api/v1/chat/history` | Requires `conversation_id` query param |
| **Goals** | GET | `/api/v1/goals/` | Optional `?status=` filter |
| | GET | `/api/v1/goals/{goal_id}` | |
| | PATCH | `/api/v1/goals/{goal_id}/abandon` | No request body |
| | PATCH | `/api/v1/goals/{goal_id}/modify` | Body: `{ message: string }` |
| | GET | `/api/v1/goals/{goal_id}/tasks` | |
| **Tasks** | GET | `/api/v1/tasks/today` | Today's pending tasks |
| | GET | `/api/v1/tasks/{task_id}` | |
| | PATCH | `/api/v1/tasks/{task_id}/complete` | No request body |
| | PATCH | `/api/v1/tasks/{task_id}/missed` | No request body |
| | POST | `/api/v1/tasks/{task_id}/reschedule` | Body: `{ message: string }` |
| **Analytics** | GET | `/api/v1/analytics/overview` | |
| | GET | `/api/v1/analytics/goals` | Goals progress list |
| | GET | `/api/v1/analytics/missed-by-cat` | Missed tasks by category |
| | GET | `/api/v1/analytics/weekly` | Optional `?weeks=` param |
| **Patterns** | GET | `/api/v1/patterns/` | |
| | GET | `/api/v1/patterns/{pattern_id}` | |
| | PATCH | `/api/v1/patterns/{pattern_id}` | Body: `PatternPatchRequest` |
| | DELETE | `/api/v1/patterns/{pattern_id}` | Returns 204 |
| **Account** | GET | `/api/v1/account/me` | Returns `AccountMeResponse` (includes `onboarded` flag) |
| | PATCH | `/api/v1/account/me` | Body: `AccountPatchRequest` |
| | POST | `/api/v1/account/phone/verify/send` | |
| | POST | `/api/v1/account/phone/verify/confirm` | |
| | POST | `/api/v1/account/whatsapp/opt-in` | |
| | DELETE | `/api/v1/account/` | GDPR erasure; returns 204 |
| | GET | `/api/v1/account/export` | GDPR portability |
| **Demo** | POST | `/api/v1/demo/trigger-location` | Fire push for pending location-triggered tasks |

## 5. Commands
- `npm run dev`: Start development server.
- `npm run check`: Run Biome lint & format.

## 6. Documentation Protocol
To ensure this documentation remains a source of truth, ALL agents must follow this protocol:

### A. When Creating New Components
1.  **Update `PROJECT_KNOWLEDGE.md`**: Add the new component to **Section 3: Project Structure** if it introduces a new folder or significant structural change.
2.  **Update `AGENTS.md`**: If the component introduces a new pattern (e.g., a new way of handling forms), document it in **Section 2: Key Architecture Patterns**.

### B. When Changing Business Logic
1.  **Update `PROJECT_KNOWLEDGE.md`**: If the change affects how state is managed or data is fetched, update **Section 4: Architectural Patterns**.

### C. When Adding Tech/Libraries
1.  **Update `PROJECT_KNOWLEDGE.md`**: Add the new library and its version to **Section 1: Tech Stack**.
2.  **Update `AGENTS.md`**: Add any specific rules or commands related to the new tool in **Section 3: Important Rules for Agents** or **Section 4: Commands**.

### D. General Maintenance
- **Review**: Before starting a task, review `AGENTS.md` and `PROJECT_KNOWLEDGE.md`.
- **Refine**: If you find outdated information, UPDATE IT. Do not leave it for the next agent.
