# Feature Flags

Frontend behavior is controlled by environment variables (set in `frontend/.env`, copied from `frontend/.env.example`). These act as feature flags for local and demo use.

---

## Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_USE_MOCK` | `true` | When `true`, the app uses mock/local data and does not call the backend API for timeline or reschedule. When `false`, the frontend calls `VITE_API_URL` (e.g. GET /scheduler/tasks, POST /scheduler/suggest, POST /scheduler/apply). |
| `VITE_ENABLE_VOICE` | `false` | Enables voice input (e.g. speech-to-text for tasks). Experimental. |
| `VITE_ENABLE_DEMO_MODE` | `true` | Shows the demo control panel (time warp, force miss, escalation speed, etc.) so you can simulate drift and recovery without waiting for real time. |

---

## Usage

- To run the full stack with real backend: set `VITE_USE_MOCK=false` and ensure `VITE_API_URL` points to your backend (e.g. `http://localhost:8000`).
- To develop UI without the backend: keep `VITE_USE_MOCK=true`.
- For demo day or showcasing flows: use `VITE_ENABLE_DEMO_MODE=true` and the pre-seeded data; see [Demo Mode](demo-mode.md).

All flags are read at build time (Vite embeds them). Change `.env` and restart `npm run dev` to apply.
