# Flux

## Product Overview

**The Pitch:** A calendar and goal-setting assistant that feels less like a spreadsheet and more like a fluid stream of consciousness. By removing rigid grids in favor of floating, ethereal interfaces, we reduce planning anxiety and encourage organic productivity.

**For:** Creative professionals and anxious achievers who feel overwhelmed by traditional, boxy productivity tools and seek a calmer, more intuitive way to manage their time.

**Device:** Mobile

**Design Direction:** **Organic Glassmorphism.** Deep, grounding earth tones (sage, clay, stone) rendered with high-gloss blur effects, fluid gradients, and floating elements. It feels like looking at nature through frosted glass.

**Inspired by:** *Cron* (for interaction density), *Amie* (for joy), *Headspace* (for atmosphere).

---

## Screens

- **Screen 1: Flow (Calendar):** A vertical, fluid timeline of the day where tasks float like leaves on a river.

- **Screen 2: Chat:** A minimalist chat interface for decomposing goals, using floating bubbles against a shifting gradient background.

- **Screen 3: Reflection (Profile & Analytics):** Data visualization using soft, blurred orbs to represent progress and energy levels.

---

## Layout & Components

**Bottom Tabs (Nav):** Condensed, position `fixed` and aligned to the bottom-center, floating. Contains the following -

- **Home**

    - *Position: left*

    - Opens the "Flow" screen.

- **Chat**:
    
    - *Position: center*
    
    - A larger, highlighted icon that bleeds out of the bottom tabs container by `~10px`. Opens the "Chat" screen.

- **Profile**:
    
    - *Position: right*
    
    - Opens "Reflection" screen.

All the tabs have an active (selected) and an inactive (unselected) state.

**Demo Mode Toggle:** A right-center floating button that slides in the Demo Mode options. The sliding panel will contain 2 buttons -

- **Time Warp** - to simulate time skip.
- **Travel Mode** - to simulate special notifications.

---

## Key Flows

**Flow 1: Decomposing a Goal**

1. User is on **Home** -> taps the Plus icon.

2. User enters **Chat** -> types "I want to lose weight for a wedding"

3. AI responds with breakdown bubbles -> User taps "Add to Flow"

4. Result: Tasks materialize and float into the timeline on The Flow.

**Flow 2: Rescheduling Overdue Tasks**

1. User is on **The Flow** -> sees a task glowing faintly red (stress).

2. User drags task bubble -> **Reschedule Modal** blurs into view.

3. User drops task into "Tomorrow Morning" zone -> Task dissolves and reforms in the new slot.

---

<details>

<summary>Design System</summary>

## Color Palette

The palette combines the grounding nature of earth tones with the digital lightness of glass.

- **Primary:** `#5C7C66` (Deep Sage) - Primary actions, active states.

- **Background:** `#EAE7E0` (Warm Stone) - The base layer, parchment-like.

- **Surface:** `rgba(255, 255, 255, 0.4)` - Frosted glass cards (requires backdrop-filter).

- **Text:** `#2D332F` (Charcoal) - Primary legibility.

- **Muted:** `#8A8F8B` (River Rock) - Timestamps, secondary metadata.

- **Accent:** `#C27D66` (Terracotta) - Notifications, urgency, highlights.

- **Gradient 1:** `linear-gradient(135deg, #EAE7E0 0%, #D4D9D2 100%)` - Base atmosphere.

- **Gradient 2:** `radial-gradient(circle at top right, rgba(92, 124, 102, 0.2), transparent)` - Ambient glow.

## Typography

Clean, humanist sans-serifs that feel modern but approachable.

- **Headings:** **Fraunces**, 300 Italic (for "dreamy" headers) or **Satoshi**, 700 (for structure).

    - *Usage:* `Satoshi` for functional headers, `Fraunces` for greetings/insights.

    - *Spec:* 32px

- **Body:** **Satoshi**, 400, 16px. High legibility, geometric but soft.

- **Small text:** **Satoshi**, 500, 13px. Uppercase tracking for labels.

- **Buttons:** **Satoshi**, 600, 15px.

**Style Notes:**

- **Glassmorphism:** All cards use `backdrop-filter: blur(12px)` and thin white borders `border: 1px solid rgba(255,255,255, 0.6)`.

- **Soft Shadows:** No harsh drop shadows. Use colored ambient shadows: `box-shadow: 0 8px 32px rgba(92, 124, 102, 0.15)`.

- **Roundness:** Heavy border radius (`24px` to `32px`) to feel organic and pebble-like.

## Design Tokens

```css

:root {

  --color-primary: #5C7C66;

  --color-bg-base: #EAE7E0;

  --color-glass: rgba(255, 255, 255, 0.4);

  --color-glass-border: rgba(255, 255, 255, 0.6);

  --color-text-main: #2D332F;

  --color-accent: #C27D66;

  

  --font-display: 'Fraunces', serif;

  --font-body: 'Satoshi', sans-serif;

  

  --radius-bubble: 24px;

  --radius-card: 32px;

  

  --shadow-ambient: 0 10px 40px -10px rgba(92, 124, 102, 0.2);

  --blur-glass: blur(16px);

}

```

</details>

---

<details>

<summary>Screen Specifications</summary>

### Screen 1: The Flow (Calendar)

**Purpose:** Primary dashboard. Viewing the day's flow without the rigidity of a grid.

**Layout:** Full-screen vertical scroll. Time flows top-to-bottom. No rigid dividing lines.

**Key Elements:**

- **Ambient Header:** Top 120px. Date in `Fraunces` Italic (e.g., *October 14th*). Weather icon floats right. Background has a slow-moving organic blob gradient (Sage/Clay).

- **To-do Tasks:** A list of time-agnostic events or tasks that the user needs to do but doesn't have a specific time for yet. These tasks are displayed in a separate section from the timed events, usually above or below the main timeline. They are visually distinct from timed events, often appearing as smaller cards or list items with a checkbox or other indicator to show that they are pending.

- **The Current Line:** A horizontal frosted glass line with "Now" text floating on the left. It glows softly.

- **Event Pebbles:** Instead of rectangles, events are organic shapes with `border-radius: 20px`.

    - *Look:* `rgba(255,255,255, 0.5)` background, backdrop blur.

    - *Content:* Title (Bold), Time (Muted) aligned left.

    - *Visual:* Height corresponds to duration. Gaps between pebbles represent free time.

- **Floating FAB:** Bottom right. A perfect circle (64px) with a subtle pulse animation. Gradient background (Sage -> Terracotta). Icon: A simple spark `✨`.

**States:**

- **Empty:** A large, soft gradient orb in the center breathing (scaling up/down). Text: "Open space for clarity."

- **Loading:** Pebbles shimmer with a white skeleton pulse.

**Interactions:**

- **Scroll:** The "Now" line stays sticky for a moment, then releases. Background blobs shift parallax.

- **Tap Event:** Event pebble expands to fill screen (shared element transition).

**Responsive:**

- **Mobile:** Single column stream.

---

### Screen 2: Chat

**Purpose:** AI-assisted breakdown of high-level goals into actionable tasks.

**Layout:** Chat interface, but messages drift up like bubbles in water. Input at bottom.

**Key Elements:**

- **Atmosphere:** Background is a darker Sage `#4A6352` to induce focus.

- **AI Bubbles:** Align Left. Shape: amorphous blob (border-radius: 4px 24px 24px 24px). Color: White, low opacity `0.9`. Text: Charcoal.

- **User Bubbles:** Align Right. Shape: amorphous blob (border-radius: 24px 24px 4px 24px). Color: Terracotta `#C27D66`. Text: White.

- **Input Pill:** Floating 20px from bottom. Full width minus margins. Glassmorphic.

    - *Placeholder:* "What is on your mind?" in Italic serif.

    - *Send Button:* Small arrow icon, appears only when typing.

**States:**

- **Thinking:** Three small dots floating in a rhythmic wave pattern, no bubble container.

**Interactions:**

- **Send:** User bubble floats up from bottom with spring physics.

- **Task Extraction:** When AI suggests tasks, they appear as "cards" within the chat stream. User taps "+" on card -> Card flies to top right corner (implies adding to calendar).

---

### Screen 3: Reflection (Profile & Analytics)

**Purpose:** Visualizing productivity not as "performance" but as "energy flow."

**Layout:** Dashboard of soft, blurred visualizations.

**Key Elements:**

- **Profile Header:** Avatar is a masked shape (squircle), not a circle. Name in `Fraunces`.

- **Energy Aura (Chart):** A canvas area showing task completion.

    - *Visual:* Instead of a bar chart, it's a heat map. Glowing orbs representing productive days. Hotter/Brighter = More tasks.

    - *Interaction:* Scrubbing finger across dates makes the orbs bloom.

- **Focus Distribution:** Three overlapping translucent circles (Work, Personal, Health). Sizes change based on time spent. Intersection colors blend via `mix-blend-mode: multiply`.

**Components:**

- **Stat Pill:** Glass capsule. Icon + Large Number + Label.

**Interactions:**

- **Tap Aura:** Opens detailed list of completed tasks for that day.

---

### Screen 4: Notification Modal

**Purpose:** Letting the user know about in upcoming task, or taking his update for an ongoing task, or notifying them to re-schedule a missed task. Reducing the friction and guilt of moving a task.

**Layout:** Half-screen bottom sheet with heavy blur backdrop.

**Key Elements:**

- **Task Preview:** The task being moved floats at the top, slightly tilted.

- **Time Zones (Options):** Large, touchable targets arranged in a 2x2 grid.

    - *Option 1:* "Later Today" (Sage icon)

    - *Option 2:* "Tomorrow Morning" (Sun icon)

    - *Option 3:* "This Weekend" (Coffee icon)

    - *Option 4:* "Pick Date" (Calendar icon)

- **Visuals:** Each zone has a subtle colored gradient background that activates on hover/drag.

**Interactions:**

- **Drag & Drop:** User drags the Task Preview. The target zones magnetically scale up when the finger is near.

- **Release:** Sound effect (soft *plop*). Modal dissolves. Toast notification: "Moved with grace."

</details>

---

<details>

<summary>Build Guide</summary>

**Stack:** HTML + Tailwind CSS v3 (extended with custom config for blurs/gradients)

**Build Order:**

1.  **Screen 1 (The Stream):** Establishes the core timeline mechanics, glassmorphism utility classes, and the scrolling behavior. This is the "home" base.

2.  **Screen 2 (Clarity):** Focuses on the chat bubble physics and input interactions.

3.  **Screen 4 (Reschedule):** Implements the drag-and-drop mechanics and modal transitions.

4.  **Screen 3 (Reflection):** Complex CSS/Canvas work for the heat map/aura visualizations.

**Tailwind Extensions Needed:**

- `backdrop-blur-xl`: `24px`

- `bg-glass`: `rgba(255, 255, 255, 0.4)`

- Animation keyframes for "breathing" gradients.

