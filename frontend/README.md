# Flux Frontend

React application for the Flux Life Assistant: Flow timeline, goal chat, and reschedule flows.

---

## Tech stack

- **React 19**, **TypeScript**
- **TanStack Start** (React + SSR), **Vite 7**
- **Framer Motion**, **Tailwind CSS**
- **Lucide React** (icons)

---

## Run locally

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

App: [http://localhost:3000](http://localhost:3000). Hot-reloads on file changes.

---

## Environment variables

Copy from `.env.example`. All are optional; Vite embeds them at build time.

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |
| `VITE_USE_MOCK` | `true` | Use mock data (no backend calls) when true |
| `VITE_API_TIMEOUT` | `10000` | Request timeout (ms) |
| `VITE_ENABLE_DEMO_MODE` | `true` | Show demo control panel (time warp, force miss, etc.) |
| `VITE_ENABLE_VOICE` | `false` | Enable voice input (experimental) |
| `VITE_SUPABASE_URL` | — | Supabase project URL (placeholder in .env.example) |
| `VITE_SUPABASE_ANON_KEY` | — | Supabase anon key (placeholder in .env.example) |

See [docs/feature-flags.md](../docs/feature-flags.md) for how these affect behavior.

---

## Mock vs real backend

- **`VITE_USE_MOCK=true`:** Timeline and reschedule use in-memory or mock data. No backend required. Useful for UI-only work.
- **`VITE_USE_MOCK=false`:** The app calls `VITE_API_URL` for:
  - GET `/scheduler/tasks` (timeline)
  - POST `/scheduler/suggest` (reschedule suggestions)
  - POST `/scheduler/apply` (apply or skip)

Ensure the backend is running (`uvicorn app.main:app --reload`) and CORS allows your dev origin (e.g. http://localhost:3000). Restart `npm run dev` after changing `.env`.

---

## Key components

- **FlowTimeline** (`src/components/flow/v2/FlowTimeline.tsx`): Renders the day timeline with events and a "Now" indicator. Accepts `events` and optional `onShuffleClick(eventId, taskTitle)` for drifted tasks.
- **TimelineEvent** (`src/components/flow/v2/TimelineEvent.tsx`): Single event card; shows "Shuffle?" for drifted tasks when `onShuffleClick` is provided.
- **RescheduleModal** (`src/components/modals/RescheduleModal.tsx`): Bottom sheet for rescheduling a drifted task. Fetches suggestions via API, then calls apply or skip.

---

## API client

`src/utils/api.ts` provides the backend client:

- **Base URL:** From `import.meta.env.VITE_API_URL` (default `http://localhost:8000`).
- **`fetchTimelineTasks()`:** GET `/scheduler/tasks`, returns `Task[]`.
- **`fetchSuggestions(eventId)`:** POST `/scheduler/suggest` with `{ event_id }`, returns suggestions and AI message.
- **`applyReschedule(eventId, action, newStart?, newEnd?)`:** POST `/scheduler/apply` with `event_id`, `action` ("reschedule" | "skip"), and optional `new_start`/`new_end`.

Types: `Task`, `TimelineTasksResponse`, `Suggestion`, `SuggestResponse`. Used by the Flow page and RescheduleModal.

---

## Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start dev server (Vite) |
| `npm run build` | Production build |
| `npm run start` | Run production server (e.g. `.output/server/index.mjs`) |
| `npm run lint` | Biome lint |
| `npm run format` | Biome format |
| `npm run check` | Biome check (lint + format) |
