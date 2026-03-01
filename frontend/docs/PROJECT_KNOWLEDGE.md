# Project Knowledge: Flux

> [!NOTE]
> This document serves as a memory module for agents working on the Flux codebase. It details the tech stack, project structure, and key architectural patterns.

## 1. Tech Stack

| Category | Technology | Version | Notes |
|----------|------------|---------|-------|
| **Core** | React | 19.x | Latest stable with hooks |
| | TypeScript | 5.9.x | Strict mode enabled |
| **Build** | Vite | 7.3.x | Fast dev server & bundler |
| **Framework** | TanStack Start | 1.159.x | Full-stack React framework (SSR) |
| **Routing** | TanStack Router | 1.159.x | Type-safe, file-based routing |
| **Styling** | Tailwind CSS | 4.x | Configured via CSS `@theme` directives |
| | clsx / tailwind-merge | - | For dynamic class construction |
| **Animation** | Framer Motion | 12.x | Complex UI transitions & gestures |
| **Icons** | Lucide React | 0.564.x | Standard icon set |
| **Auth** | Supabase SSR | 2.x | `@supabase/ssr` — server-side only. Keys in `process.env` (no `VITE_` prefix). Client: `src/lib/supabaseServer.ts`. Server fns: `src/lib/authServerFns.ts`. No Supabase SDK on client. |
| **API Mocking** | MSW | — | **Removed** — app talks directly to the backend (localhost:8000 in dev) |
| **Linting** | Biome | 2.3.x | Fast linter & formatter (replaces ESLint/Prettier) |

## 2. Key Commands

- **Development**: `npm run dev` (Starts Vite server on port 3000)
- **Build**: `npm run build` (Production build)
- **Start**: `npm run start` (Run production build)
- **Lint**: `npm run lint` (Run Biome linter)
- **Format**: `npm run format` (Run Biome formatter)
- **Check**: `npm run check` (Run Biome check - lint + format)

## 3. Project Structure

The project follows a standard TanStack Start structure:

```
src/
├── components/         # React components
│   ├── chat/           # Chat-specific components
│   ├── flow/           # Flow/Home screen components
│   ├── demo/           # Demo mode components
│   ├── reflection/     # Reflection screen components
│   │   ├── ProfileHeader.tsx
│   │   ├── EnergyAura.tsx
│   │   ├── EnergyAuraLoadingState.tsx
│   │   ├── FocusDistribution.tsx
│   │   ├── FocusDistributionLoadingState.tsx
│   │   ├── StatsLoadingState.tsx
│   │   └── WeeklyInsightLoadingState.tsx
│   ├── navigation/     # Shared navigation (BottomNav)
│   ├── splash/         # Splash screen components (initial load)
│   ├── ui/             # Reusable UI primitives (GlassCard, etc.)
│   └── modals/         # Modal dialogs
│   # src/mocks/ — REMOVED. MSW has been deleted. App talks directly to backend.
├── services/           # API service layer
│   ├── AccountService.ts     # GET/PATCH /api/v1/account/me + analytics endpoints
│   ├── ChatService.ts        # POST /api/v1/chat/message, GET /api/v1/chat/history
│   ├── TasksService.ts       # /api/v1/tasks/ CRUD + complete/miss/reschedule
│   ├── GoalsService.ts       # /api/v1/goals/ CRUD + abandon/modify
│   ├── PatternsService.ts    # /api/v1/patterns/ CRUD
│   ├── DemoService.ts        # POST /api/v1/demo/trigger-location
│   └── AuthService.ts        # Thin wrapper around authServerFns (no Supabase SDK)
├── types/              # Centralized TypeScript type definitions
│   ├── user.ts         # User, AccountMeResponse, AccountPatchRequest, auth types
│   ├── task.ts         # Task, TaskStatus, Priority, TaskCategory, RescheduleRequest
│   ├── event.ts        # Event, EventType, EventStatus types (UI timeline)
│   ├── message.ts      # ChatMessageRequest/Response, ChatHistoryResponse, ApiMessage, MessageContent union
│   ├── goal.ts         # Goal, GoalStatus, GoalModifyRequest, PlanMilestone, AgentState
│   ├── pattern.ts      # Pattern, PatternPatchRequest (new domain)
│   ├── notification.ts # Notification, EscalationLevel, LocationReminderState
│   ├── analytics.ts    # EnergyPoint, FocusMetrics, ProductivityMetrics
│   ├── demo.ts         # DemoMode, RescheduleOption, TimeWarpSettings
│   ├── common.ts       # Utility types, ColorTheme, GlassEffect, AnimationConfig
│   ├── api.d.ts        # Auto-generated OpenAPI types (DO NOT EDIT)
│   └── index.ts        # Barrel exports for all types
├── lib/                # Shared singletons and low-level utilities
│   ├── supabaseServer.ts  # SERVER-ONLY: @supabase/ssr createServerClient with cookie adapters
│   ├── authServerFns.ts   # TanStack Start server fns: serverLogin, serverSignup, serverLogout, serverGetAccessToken, serverGetGoogleOAuthUrl
│   └── apiClient.ts       # apiFetch() — injects _inMemoryToken as Bearer JWT; exports setInMemoryToken/getInMemoryToken
├── routes/             # File-based routes (TanStack Router)
│   ├── __root.tsx      # Root layout & HTML shell
│   ├── index.tsx       # Home page (Flow)
│   ├── chat.tsx        # Chat interface + Onboarding flow
│   ├── reflection.tsx  # Analytics/Reflection page (with loaders + data fetching)
│   └── auth/
│       └── callback.tsx  # Google OAuth callback — exchanges code for session, redirects
├── styles/
│   └── app.css         # Global styles & Tailwind @theme config
├── utils/              # Helper functions & constants
│   ├── env.ts          # Execution context helpers (isClient, isServer)
│   ├── date.ts         # Date formatting / manipulation helpers
│   ├── cn.ts           # Class name merger utility
│   └── seo.ts          # SEO meta tag generators
└── routeTree.gen.ts    # Auto-generated route definition (DO NOT EDIT)
```

## 4. Architectural Patterns

### Routing
- **File-Based**: Routes are defined by files in `src/routes`.
- **Root Layout**: `src/routes/__root.tsx` wraps all pages. It handles the `<html>` and `<body>` tags, global styles, and metadata.
- **Navigation**: Uses `Link` component from `@tanstack/react-router`.
- **Onboarding Flow**: The `/chat` route handles both onboarding and regular chat. When `user.onboarded === false`, the chat screen displays onboarding questions. The bottom navigation is hidden during onboarding.

### Styling
- **Tailwind v4**: Configuration is located in `src/styles/app.css` using the `@theme` directive, NOT in a JavaScript config file.
- **Design Tokens**: CSS variables are used for colors, shadows, and radii (e.g., `--color-sage`, `--radius-card`).
- **Glassmorphism**: Extensive use of `backdrop-filter`, semi-transparent backgrounds, and light borders.
- **Utilities**: Custom utilities like `.glass-card`, `.text-display` are defined in `app.css`.

### Component Design
- **Atomic/Molecule**: Architecture splits into `ui` (atoms) and feature folders (molecules/organisms).
- **Separation of Concerns**: Feature-specific components stay in their respective folders (`flow`, `chat`).
- **Composition**: Shared wrappers like `GlassCard` are used to enforce visual consistency.

### State Management
- **Local State**: `useState`, `useReducer` for component-level logic.
- **URL State**: TanStack Router handles URL-based state (search params, etc.).
- **Server State**: TanStack Start `loader` functions handle data fetching (server-side).

### Data Fetching
- **Page-Level Data**: Use TanStack Router `loader` functions for blocking data fetches (e.g., user profile).
  - Data is available before page renders via `Route.useLoaderData()`.
  - Shows full-page loading state if data is not available.
- **Component-Level Data**: Use `useEffect` with local state for non-blocking fetches (e.g., stats, charts).
  - Each section shows its own loading state while data loads.
  - Allows progressive page rendering.

### Service Layer
- **Encapsulation**: All API calls must go through service classes in `src/services/`.
  - Services handle URL construction, error handling, and response parsing.
  - Never use direct `fetch` calls in React components or services.
  - **Always use `apiFetch` from `~/lib/apiClient`** — it injects the Supabase JWT as `Authorization: Bearer <token>` automatically.
- **Domain Organization**: Services are organized by domain matching the real `/api/v1/` endpoint groups:
  - `AccountService` → `/api/v1/account/` and `/api/v1/analytics/`
  - `ChatService` → `/api/v1/chat/`
  - `TasksService` → `/api/v1/tasks/`
  - `GoalsService` → `/api/v1/goals/`
  - `PatternsService` → `/api/v1/patterns/`
  - `DemoService` → `/api/v1/demo/`
  - `AuthService` → thin wrapper around `authServerFns` (no Supabase SDK; no REST calls to `/api/auth/`)
- **Usage Pattern**: Import and use services directly:
  ```typescript
  import { accountService } from "~/services/AccountService";
  const me = await accountService.getMe();
  // me.onboarded determines if user needs onboarding
  ```
- **Error Handling**: Services throw typed errors that can be caught by callers.
- **Stale services deleted**: `UserService`, `GoalPlannerService`, `OnboardingService` have been removed from the codebase.

### SSR Safety
- **Context**: This project uses TanStack Start with SSR. Browser globals (`document`, `window`, `navigator`) are **not available** in Node.js during server rendering.
- **Utility**: Use `isClient()` / `isServer()` from `~/utils/env` to guard any browser-only code:
  ```typescript
  import { isClient } from "~/utils/env";

  if (!isClient()) return; // Safe to use document / window below
  ```
- **Rule**: Never access `document`, `window`, or `navigator` at the module's top level or synchronously during render. Always guard with `isClient()`.
- **Auth / Supabase**: `supabaseServer.ts` and `authServerFns.ts` are server-only — import them only inside `createServerFn` handlers. The old `src/lib/supabase.ts` browser singleton is deleted; do not recreate it.

### Authentication
- **Provider**: `@supabase/ssr` — server-side only. Supabase keys (`SUPABASE_URL`, `SUPABASE_ANON_KEY`) live in `process.env` with no `VITE_` prefix and are never bundled into client JS.
- **Server client**: `src/lib/supabaseServer.ts` — `createServerClient` from `@supabase/ssr`, configured with TanStack Start cookie helpers. NEVER import from client code.
- **Server functions** (`src/lib/authServerFns.ts`): All auth ops run on the server as `createServerFn`:
  - `serverLogin` / `serverSignup` — sign in/up; `@supabase/ssr` writes session to httpOnly cookies automatically
  - `serverLogout` — signs out; also explicitly deletes Supabase cookie names
  - `serverGetAccessToken` — reads httpOnly session cookie server-side, returns `{ token, user }` for client hydration
  - `serverGetGoogleOAuthUrl` — generates OAuth URL server-side (`skipBrowserRedirect: true`), returns `{ url }`
- **AuthService** (`src/services/AuthService.ts`): Thin wrapper over server functions. No Supabase SDK import.
- **AuthContext** (`src/contexts/AuthContext.tsx`): Calls `serverGetAccessToken` on mount to hydrate `_inMemoryToken` via `setInMemoryToken`. Re-runs every 45 min. Exposes: `login`, `signup`, `logout`, `loginWithGoogle`, `refreshAuthStatus`.
- **Google OAuth Flow**:
  1. `loginWithGoogle()` in `AuthContext` → `authService.loginWithGoogle()` → `serverGetGoogleOAuthUrl()` → returns URL
  2. Client: `window.location.href = url` — browser navigates to Google
  3. Google redirects to `/auth/callback?code=...`
  4. `src/routes/auth/callback.tsx` **loader** (runs server-side) calls `exchangeOAuthCode` server fn → `exchangeCodeForSession` → `@supabase/ssr` sets httpOnly cookie → HTTP 302 to `/`
  5. On `/` mount, `AuthContext.refreshAuthStatus()` hydrates `_inMemoryToken`
- **JWT / Token Flow**: Token lives in httpOnly cookie (server-set) + React module memory (`_inMemoryToken` in `apiClient.ts`). Never in localStorage. `apiFetch` injects it as `Authorization: Bearer <token>`.
- **`onboarded` Source of Truth**: `GET /api/v1/account/me` → `onboarded: boolean`. Fetched in `AuthContext.refreshAuthStatus()`.
- **No client-side Supabase SDK**: `src/lib/supabase.ts` has been deleted. Do not recreate it or import `@supabase/supabase-js` in any client code.

### API Mocking
- **MSW removed**: `src/mocks/` and all MSW handler files have been deleted. Do not add them back.
- The app talks directly to the backend. In development, the backend runs on `localhost:8000`.
- **Real API Spec**: `src/types/api.d.ts` is the authoritative source of truth for all endpoint paths, request bodies, and response shapes.

### Loading States
- **Feature-Specific Loading**: Each component section has its own loading state component.
- **Glassmorphic Design**: Loading states use glassmorphic styling with pulsing animations.
- **Structure Matching**: Loading state components match the structure of the loaded component.
- **Examples**: `StatsLoadingState`, `EnergyAuraLoadingState`, `FocusDistributionLoadingState`, `WeeklyInsightLoadingState`.

### Type System
- **Centralized Types**: All domain types are defined in `src/types/` with clear domain separation.
- **Union Types**: Message and notification content use TypeScript union types for type-safe polymorphism (e.g., `TextMessage | PlanMessage | TaskSuggestionMessage`).
- **Strict Typing**: All types use explicit optional markers (`?`) for optional fields; no use of `any`.
- **Barrel Exports**: All types are exported from `src/types/index.ts` for centralized importing via `~/types`.
- **Enums**: Extensive use of TypeScript enums for state machines (e.g., `AgentState`, `TaskStatus`, `EventType`).
- **Import Pattern**: Always import types from `~/types` rather than deep imports (e.g., `import { User, Task } from '~/types'`).

## 5. Backend API Contract

The real backend API spec is auto-generated in `src/types/api.d.ts`. **Do not edit it.** All endpoints use the `/api/v1/` prefix.

### Chat Flow
- `POST /api/v1/chat/message` — send a user message; returns `ChatMessageResponse`
  - `conversation_id` must be persisted and sent on subsequent messages for multi-turn conversations
  - `requires_user_action: true` signals the UI to show a confirmation/action prompt
  - `proposed_plan` contains structured plan data when the agent proposes a goal plan
- `GET /api/v1/chat/history?conversation_id=...` — retrieve past messages

### User Onboarding
- Onboarding state is determined by `GET /api/v1/account/me` → `onboarded: boolean`
- There is no separate onboarding endpoint — the chat agent handles onboarding flow
- When `onboarded === false`, the chat screen should present onboarding questions

### Task Actions
Tasks support four state transitions via dedicated PATCH/POST endpoints:
- `complete` → marks done; may trigger goal completion or next pipeline goal
- `missed` → marks missed; triggers pattern observer asynchronously
- `reschedule` → POST with `{ message }` — LangGraph agent interprets the reschedule intent

### Patterns (New Domain)
AI-detected behavioral patterns. Stored per user, patchable with `user_override`. No UI currently. Managed via `PatternsService`.

## 6. Design System Highlights

- **Colors**: Sage (`#5C7C66`), Stone (`#EAE7E0`), Terracotta (`#C27D66`).
- **Typography**:
    - **Display**: Fraunces (Serif)
    - **Body**: Satoshi (Sans-serif)
- **Shapes**: High border-radius (24px - 32px) for organic feel.
- **Motion**: Spring animations for interactions, "breathing" animations for idle states.

## 7. Development Workflow
1.  **Modify Route**: Add/Edit file in `src/routes` -> auto-update `routeTree.gen.ts`.
2.  **Add Component**: Create in `src/components/{feature}`.
3.  **Style**: Use Tailwind classes. For complex components, use `styles/app.css` `@layer components`.
4.  **Lint/Format**: Run `npm run check` before committing.
