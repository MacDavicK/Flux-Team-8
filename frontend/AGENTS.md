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

## 2. Key Architecture Patterns
- **Glassmorphism**: The design relies heavily on `backdrop-filter`, translucent backgrounds, and organic borders.
- **Component Structure**:
  - `src/components/ui`: Atomic, reusable components (GlassCard, Button, etc.).
  - `src/components/{feature}`: Feature-specific molecules (e.g., `src/components/chat`).
- **Routing**:
  - Root layout: `src/routes/__root.tsx`.
  - Pages: `src/routes/index.tsx` (Flow), `src/routes/chat.tsx`, etc.

## 3. Important Rules for Agents
- **Styling**: ALWAYS use Tailwind classes. Do NOT create new CSS files. Use `src/styles/app.css` for global theme variables.
- **New Components**: Place in `src/components`. Prefer composition over inheritance.
- **Routing**: To add a page, create a file in `src/routes`. `routeTree.gen.ts` is auto-generated; DO NOT edit it manually.
- **Icons**: Use `lucide-react`.

## 4. Commands
- `npm run dev`: Start development server.
- `npm run check`: Run Biome lint & format.

_Generated from codebase analysis._

## 5. Documentation Protocol
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

