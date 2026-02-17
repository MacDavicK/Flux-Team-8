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
- **API Mocking**: MSW (Mock Service Worker) for development

## 2. Key Architecture Patterns
- **Glassmorphism**: The design relies heavily on `backdrop-filter`, translucent backgrounds, and organic borders.
- **Splash Screen**: Shows on every page load/refresh for 3 seconds. Later will be used to load initial data from server.
- **Centralized Type System**: All domain types are organized in `src/types/` with domain-specific files (e.g., `user.ts`, `task.ts`) and barrel exports via `index.ts`.
- **Union Types**: Polymorphic content uses TypeScript union types (e.g., different message content types in `MessageContent`).
- **Strict Typing**: All types use explicit optional markers (`?`) and avoid `any`.
- **API Mocking**: MSW handles API mocking in development. Handlers are in `src/mocks/` organized by domain (e.g., `userHandlers.ts`, `tasksHandlers.ts`).
- **Data Fetching**: 
  - Page-level data: Fetched via TanStack Router `loader` functions (blocking, before page renders).
  - Component-level data: Fetched via `useEffect` with local state (non-blocking, shows loading states).
- **Loading States**: Each component section has its own glassmorphic loading state component (e.g., `StatsLoadingState`, `EnergyAuraLoadingState`).
- **Component Structure**:
  - `src/components/ui`: Atomic, reusable components (GlassCard, Button, etc.).
  - `src/components/{feature}`: Feature-specific molecules (e.g., `src/components/chat`).
- **Routing**:
  - Root layout: `src/routes/__root.tsx`.
  - Pages: `src/routes/index.tsx` (Flow), `src/routes/chat.tsx`, etc.

## 3. Important Rules for Agents
- **Styling**: ALWAYS use Tailwind classes. Do NOT create new CSS files. Use `src/styles/app.css` for global theme variables.
- **Data Fetching**: NEVER use direct `fetch` calls in React components. ALWAYS use services from `src/services/`:
  - Services encapsulate API logic (URL construction, error handling, response parsing).
  - Example: Use `userService.getProfile()` instead of `fetch("/api/user/profile")`.
  - Services are organized by domain (e.g., `UserService`, `TasksService`, `GoalPlannerService`).
  - Each service method returns typed Promise and handles errors consistently.
- **New Components**: Place in `src/components`. Prefer composition over inheritance.
- **Routing**: To add a page, create a file in `src/routes`. `routeTree.gen.ts` is auto-generated; DO NOT edit it manually.
- **Icons**: Use `lucide-react`.
- **Types**: Place new domain types in `src/types/` organized by entity (e.g., `user.ts`, `task.ts`). Export from `src/types/index.ts`.
- **Type Imports**: Import types from `~/types` (e.g., `import { User, Task } from '~/types'`).
- **Union Types**: Use union types for polymorphic content with strict type guards.
- **Strict Fields**: Define strict required vs optional fields; use `?` for optional, never use `any`.
- **API Mocking**: 
  - All API endpoints must be mocked using MSW in development.
  - Create handlers in `src/mocks/{domain}Handlers.ts`.
  - Export handlers from `src/mocks/handlers.ts`.
  - Add appropriate delays (300-500ms) to simulate real API latency.
- **Loading States**: 
  - Create feature-specific loading state components (e.g., `StatsLoadingState`).
  - Use glassmorphic design with pulsing animations.
  - Match the structure of the loaded component.

## 4. Commands
- `npm run dev`: Start development server.
- `npm run check`: Run Biome lint & format.

## 5. MCP Configuration
The project uses `.mcp.json` for MCP server configuration. Currently configured:
- **Stitch**: Google Stitch MCP server for design-to-code workflows.

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

