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
| **API Mocking** | MSW | 2.12.x | Mock Service Worker for development |
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
├── mocks/              # MSW API mock handlers
│   ├── browser.ts      # MSW browser setup
│   ├── handlers.ts     # Combined handlers export
│   ├── userHandlers.ts # User API mocks
│   ├── tasksHandlers.ts # Tasks API mocks
│   └── goalPlannerHandlers.ts # Goal planner API mocks
├── services/           # API service layer
│   ├── UserService.ts  # User API service
│   ├── TasksService.ts # Tasks API service
│   └── GoalPlannerService.ts # Goal planner API service
├── types/              # Centralized TypeScript type definitions
│   ├── user.ts         # User, Profile, Preference types + API response types
│   ├── task.ts         # Task, TaskStatus, Priority, TaskCategory types
│   ├── event.ts        # Event, EventType, EventStatus types
│   ├── message.ts      # Message union types (Text, Plan, Task, Notification)
│   ├── goal.ts         # Goal, Milestone, AgentState, GoalContext types
│   ├── notification.ts # Notification, EscalationLevel, LocationReminderState
│   ├── analytics.ts    # EnergyPoint, FocusMetrics, ProductivityMetrics
│   ├── demo.ts         # DemoMode, RescheduleOption, TimeWarpSettings
│   ├── common.ts       # Utility types, ColorTheme, GlassEffect, AnimationConfig
│   └── index.ts        # Barrel exports for all types
├── routes/             # File-based routes (TanStack Router)
│   ├── __root.tsx      # Root layout & HTML shell
│   ├── index.tsx       # Home page (Flow)
│   ├── chat.tsx        # Chat interface + Onboarding flow
│   └── reflection.tsx  # Analytics/Reflection page (with loaders + data fetching)
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
  - Never use direct `fetch` calls in React components.
- **Domain Organization**: Services are organized by domain (e.g., `UserService`, `TasksService`, `GoalPlannerService`).
- **Usage Pattern**: Import and use services directly:
  ```typescript
  import { userService } from "~/services/UserService";
  const profile = await userService.getProfile();
  ```
- **Error Handling**: Services throw typed errors that can be caught by callers.

### SSR Safety
- **Context**: This project uses TanStack Start with SSR. Browser globals (`document`, `window`, `navigator`) are **not available** in Node.js during server rendering.
- **Utility**: Use `isClient()` / `isServer()` from `~/utils/env` to guard any browser-only code:
  ```typescript
  import { isClient } from "~/utils/env";

  if (!isClient()) return; // Safe to use document / window below
  ```
- **Rule**: Never access `document`, `window`, or `navigator` at the module's top level or synchronously during render. Always guard with `isClient()`.

### API Mocking
- **MSW in Development**: All API endpoints are mocked using Mock Service Worker.
- **Handler Organization**: Handlers are organized by domain in `src/mocks/{domain}Handlers.ts`.
- **Realistic Delays**: Handlers include 300-500ms delays to simulate real API latency.
- **Type Safety**: Mock responses are typed using the same types as real API responses.

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

## 5. Design System Highlights

- **Colors**: Sage (`#5C7C66`), Stone (`#EAE7E0`), Terracotta (`#C27D66`).
- **Typography**:
    - **Display**: Fraunces (Serif)
    - **Body**: Satoshi (Sans-serif)
- **Shapes**: High border-radius (24px - 32px) for organic feel.
- **Motion**: Spring animations for interactions, "breathing" animations for idle states.

## 6. Development Workflow
1.  **Modify Route**: Add/Edit file in `src/routes` -> auto-update `routeTree.gen.ts`.
2.  **Add Component**: Create in `src/components/{feature}`.
3.  **Style**: Use Tailwind classes. For complex components, use `styles/app.css` `@layer components`.
4.  **Lint/Format**: Run `npm run check` before committing.
