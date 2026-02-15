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
