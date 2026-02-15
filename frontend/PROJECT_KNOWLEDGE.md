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
│   ├── navigation/     # Shared navigation (BottomNav)
│   ├── splash/         # Splash screen components (initial load)
│   ├── ui/             # Reusable UI primitives (GlassCard, etc.)
│   └── modals/         # Modal dialogs
├── routes/             # File-based routes (TanStack Router)
│   ├── __root.tsx      # Root layout & HTML shell
│   ├── index.tsx       # Home page (Flow)
│   ├── chat.tsx        # Chat interface
│   └── reflection.tsx  # Analytics/Reflection page
├── styles/
│   └── app.css         # Global styles & Tailwind @theme config
├── utils/              # Helper functions & constants
│   ├── design-tokens.ts # (Deprecated? Checked, likely unused if CSS var based)
│   ├── cn.ts           # Class name merger utility
│   └── seo.ts          # SEO meta tag generators
└── routeTree.gen.ts    # Auto-generated route definition (DO NOT EDIT)
```

## 4. Architectural Patterns

### Routing
- **File-Based**: Routes are defined by files in `src/routes`.
- **Root Layout**: `src/routes/__root.tsx` wraps all pages. It handles the `<html>` and `<body>` tags, global styles, and metadata.
- **Navigation**: Uses `Link` component from `@tanstack/react-router`.

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
