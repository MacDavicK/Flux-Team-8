# Flux - Component Architecture & Design Analysis

## Project Overview

**Flux** is a calendar and goal-setting assistant with an organic glassmorphism design. Built with:
- TANStack Start + React + TypeScript
- Tailwind CSS v4 with custom design tokens
- Framer Motion for animations
- Lucide React for icons

---

## Dependencies Installed

```json
{
  "core": [
    "@tanstack/react-router",
    "@tanstack/react-start",
    "react",
    "react-dom"
  ],
  "styling": [
    "tailwindcss",
    "@tailwindcss/vite",
    "tailwind-merge",
    "clsx"
  ],
  "animation": [
    "framer-motion"
  ],
  "icons": [
    "lucide-react"
  ]
}
```

---

## Routes Structure

| Route | Path | Description |
|-------|------|-------------|
| Flow (Home) | `/` | Main calendar/timeline view |
| Chat | `/chat` | AI goal decomposition interface |
| Reflection | `/reflection` | Profile & analytics dashboard |

**Note:** Demo Panel (Screen 2) is an overlay component, NOT a separate route.

---

## Component Architecture

### Reusable Components

| Component | Location | Description |
|-----------|----------|-------------|
| `BottomNav` | `/components/navigation/BottomNav.tsx` | Fixed bottom navigation with Home, Chat (centered), Profile |
| `GlassCard` | `/components/ui/GlassCard.tsx` | Frosted glass container with backdrop blur |
| `AmbientBackground` | `/components/ui/AmbientBackground.tsx` | Organic gradient background with blobs |
| `DemoToggle` | `/components/demo/DemoToggle.tsx` | Right-side floating demo mode button |
| `DemoPanel` | `/components/demo/DemoPanel.tsx` | Sliding panel with Time Warp & Travel Mode |
| `FloatingFAB` | `/components/ui/FloatingFAB.tsx` | Pulse-animated floating action button |
| `EventPebble` | `/components/timeline/EventPebble.tsx` | Organic-shaped timeline event |
| `ChatBubble` | `/components/chat/ChatBubble.tsx` | Amorphous chat message bubble |
| `StatPill` | `/components/ui/StatPill.tsx` | Glass capsule for stats display |
| `RescheduleModal` | `/components/modals/RescheduleModal.tsx` | Bottom sheet for task rescheduling |

### Screen-Specific Components (Non-Reusable)

| Component | Location | Description |
|-----------|----------|-------------|
| `FlowHeader` | `/components/flow/FlowHeader.tsx` | Ambient header with date & weather |
| `CurrentTimeLine` | `/components/flow/CurrentTimeLine.tsx` | "Now" indicator line |
| `TodoSection` | `/components/flow/TodoSection.tsx` | Time-agnostic tasks section |
| `Timeline` | `/components/flow/Timeline.tsx` | Vertical scrollable timeline |
| `EmptyState` | `/components/flow/EmptyState.tsx` | Breathing orb for empty state |
| `ChatInput` | `/components/chat/ChatInput.tsx` | Glassmorphic input pill |
| `ThinkingIndicator` | `/components/chat/ThinkingIndicator.tsx` | Three floating dots animation |
| `TaskCard` | `/components/chat/TaskCard.tsx` | Extractable task within chat |
| `ProfileHeader` | `/components/reflection/ProfileHeader.tsx` | Avatar with squircle mask |
| `EnergyAura` | `/components/reflection/EnergyAura.tsx` | Canvas-based heat map visualization |
| `FocusDistribution` | `/components/reflection/FocusDistribution.tsx` | Overlapping circles chart |

---

## Design Tokens (Tailwind Config)

### Colors
```javascript
colors: {
  sage: {
    DEFAULT: '#5C7C66',
    dark: '#4A6352',
  },
  stone: {
    DEFAULT: '#EAE7E0',
    dark: '#D4D9D2',
  },
  charcoal: '#2D332F',
  river: '#8A8F8B',
  terracotta: '#C27D66',
  glass: 'rgba(255, 255, 255, 0.4)',
  'glass-border': 'rgba(255, 255, 255, 0.6)',
}
```

### Typography
```javascript
fontFamily: {
  display: ['Fraunces', 'serif'],
  body: ['Satoshi', 'sans-serif'],
}
```

### Border Radius
```javascript
borderRadius: {
  bubble: '24px',
  card: '32px',
}
```

### Shadows
```javascript
boxShadow: {
  ambient: '0 10px 40px -10px rgba(92, 124, 102, 0.2)',
}
```

### Backdrop Blur
```javascript
backdropBlur: {
  glass: '16px',
}
```

---

## Key Design Principles

1. **Glassmorphism**: All cards use `backdrop-blur-[16px]` with white borders at 60% opacity
2. **Organic Shapes**: Heavy border-radius (24px-32px), pebble-like appearance
3. **Ambient Shadows**: Colored ambient shadows, no harsh drop shadows
4. **Mobile-First**: Single column layouts optimized for mobile
5. **Fluid Animations**: Spring physics for interactions, breathing animations for emptiness

---

## Screen-Specific Guidelines

### Screen 1: Flow (Home) - THE BASIS
- **Background**: Warm Stone (#EAE7E0) with organic blob gradients
- **Header**: Fraunces italic date, weather icon floating right
- **Timeline**: Vertical scroll, events as organic "pebbles"
- **Bottom Nav**: Fixed, centered, floating appearance
- **FAB**: Bottom right, 64px circle, gradient from Sage to Terracotta

### Screen 2: Demo Panel - OVERLAY ONLY
- **Position**: Right-center floating button
- **Behavior**: Slides in panel with 2 buttons (Time Warp, Travel Mode)
- **NO separate route** - overlays on current screen

### Screen 3: Chat
- **Background**: Darker Sage (#4A6352) for focus
- **AI Bubbles**: Left-aligned, 4px 24px 24px 24px radius, white 90% opacity
- **User Bubbles**: Right-aligned, 24px 24px 4px 24px radius, Terracotta color
- **Input**: Floating pill 20px from bottom, full width minus margins

### Screen 4: Reflection
- **Visual Style**: Soft, blurred visualizations
- **Energy Aura**: Canvas-based heat map with glowing orbs
- **Focus Distribution**: Three overlapping translucent circles
- **Avatar**: Squircle (not circular) mask

---

## Identified Deviations (Use Screen 1 as Basis)

1. **Bottom Nav**: Screen 3 & 4 may have different nav styling - USE Screen 1's nav
2. **Colors**: Screen 3 has darker background but should use same glass effects
3. **Typography**: All screens use same font families (Fraunces for display, Satoshi for body)
4. **Corner Radius**: Standardize to 24px (bubble) and 32px (card) across all screens

---

## Animation Specifications

| Animation | Duration | Easing |
|-----------|----------|--------|
| Page transitions | 300ms | ease-in-out |
| Bubble float up | 400ms | spring(0.5, 0.7) |
| Glass panel slide | 250ms | cubic-bezier(0.4, 0, 0.2, 1) |
| Breathing (empty state) | 4s | ease-in-out infinite |
| FAB pulse | 2s | ease-in-out infinite |
| Drag magnetic | 150ms | ease-out |
| Modal dissolve | 200ms | ease-out |

---

## File Structure

```
src/
├── components/
│   ├── navigation/
│   │   └── BottomNav.tsx
│   ├── ui/
│   │   ├── GlassCard.tsx
│   │   ├── AmbientBackground.tsx
│   │   ├── FloatingFAB.tsx
│   │   └── StatPill.tsx
│   ├── demo/
│   │   ├── DemoToggle.tsx
│   │   └── DemoPanel.tsx
│   ├── flow/
│   │   ├── FlowHeader.tsx
│   │   ├── CurrentTimeLine.tsx
│   │   ├── Timeline.tsx
│   │   ├── EventPebble.tsx
│   │   ├── TodoSection.tsx
│   │   └── EmptyState.tsx
│   ├── chat/
│   │   ├── ChatBubble.tsx
│   │   ├── ChatInput.tsx
│   │   ├── ThinkingIndicator.tsx
│   │   └── TaskCard.tsx
│   ├── reflection/
│   │   ├── ProfileHeader.tsx
│   │   ├── EnergyAura.tsx
│   │   └── FocusDistribution.tsx
│   └── modals/
│       └── RescheduleModal.tsx
├── hooks/
│   └── useDemoMode.ts
├── styles/
│   └── app.css
├── routes/
│   ├── __root.tsx
│   ├── index.tsx (Flow)
│   ├── chat.tsx
│   └── reflection.tsx
└── utils/
    └── design-tokens.ts
```

---

## End-to-End Flows

### Flow 1: Decomposing a Goal
1. User on **Flow** screen → taps Plus FAB
2. Navigate to **Chat** screen → type goal
3. AI responds with breakdown bubbles → tap "Add to Flow"
4. Tasks animate into **Flow** timeline

### Flow 2: Rescheduling Tasks
1. User on **Flow** → sees overdue task (red glow)
2. Long-press/drag task → **RescheduleModal** appears
3. Drop task into time zone → task dissolves and reforms
4. Toast: "Moved with grace"

---

## Build Order

1. ✅ Set up TANStack Start project
2. ✅ Install dependencies (framer-motion, lucide-react)
3. Create Tailwind config with design tokens
4. Create reusable UI components (GlassCard, BottomNav)
5. Create Flow screen (Screen 1) - BASIS for all
6. Create Demo panel overlay (Screen 2)
7. Create Chat screen (Screen 3)
8. Create Reflection screen (Screen 4)
9. Implement interactions and animations
10. Add drag-and-drop functionality
