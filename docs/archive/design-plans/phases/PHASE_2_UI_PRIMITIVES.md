# Phase 2: UI Primitives — Component by Component

## Goal
Port all 20 UI primitive components from the AI Studio prototype. Each component is built, visually validated in BOTH light and dark mode, then committed before moving to the next.

## Pre-requisite
Phase 1 complete (utils, animations, theme context working)

## Critical Rule
**Port, don't rewrite.** Copy the prototype code, change imports from relative to `@/` aliases, add any missing TypeScript types. Do NOT "improve" styling.

---

## Build Order (dependency chain — simplest first)

### 2.1 GlassCard
**Source:** `docs/design/references/components/ui/GlassCard.tsx`
**Target:** `frontend/src/components/ui/GlassCard.tsx`

The foundation component. Every card, panel, and container uses this.

**Key specs:**
- 4 variants: default, elevated, subtle, dark
- `rounded-2xl`
- backdrop-blur-xl
- Framer Motion hover animation (optional)
- Dark: `bg-obsidian-300/60 border-white/10`
- Light: `bg-paper-100/80 border-deep-teal-800/10`

**Validation:** Render all 4 variants side by side in light and dark mode on DevPage.

---

### 2.2 Badge
**Source:** `docs/design/references/components/ui/Badge.tsx`
**Target:** `frontend/src/components/ui/Badge.tsx`

**Key specs:**
- Variants: success (gain), danger (loss), warning, info, neutral
- Soft translucent backgrounds (NOT solid)
- Optional dot indicator
- Small caps text

**Validation:** All 5 variants in both modes.

---

### 2.3 Skeleton
**Source:** `docs/design/references/components/ui/Skeleton.tsx`
**Target:** `frontend/src/components/ui/Skeleton.tsx`

**Key specs:**
- Pulse animation
- Light: `bg-deep-teal-800/5`
- Dark: `bg-white/5`

---

### 2.4 Logo
**Source:** `docs/design/references/components/ui/Logo.tsx`
**Target:** `frontend/src/components/ui/Logo.tsx`

**Key specs:**
- 3-layer SVG diagonal stripes (the Paravant "wings")
- Turquoise color, opacity layers (90/75/60%)
- "PARAVANT" wordmark in Cinzel, tracking-[0.15em]
- `showText` prop to hide text (collapsed sidebar)

**Validation:** Compare with `screenshots/target/sidebar/expanded-sidebar.png` top-left corner.

---

### 2.5 Avatar
**Source:** `docs/design/references/components/ui/Avatar.tsx`
**Target:** `frontend/src/components/ui/Avatar.tsx`

**Key specs:**
- Image with fallback (initials)
- Status dot (online/offline/away)
- Sizes: sm, md, lg
- Green glow on status dot

**Validation:** Compare with sidebar avatar in prototype screenshots.

---

### 2.6 Button (create from spec — not in prototype as standalone)

Create based on design patterns seen across prototype components:

**Variants:**
- primary: `bg-turquoise text-white hover:bg-turquoise-bright`
- secondary: `bg-deep-teal-800/5 dark:bg-white/5 text-deep-teal-800 dark:text-paper-100`
- danger: `bg-loss/10 text-loss hover:bg-loss/20`
- ghost: `bg-transparent hover:bg-deep-teal-800/5 dark:hover:bg-white/5`
- emergency: `bg-loss text-white animate-pulse`

**Sizes:** sm, md, lg
**States:** default, hover (scale 1.02, y: -1), disabled, loading
**Radius:** `rounded-xl`

---

### 2.7 Input
**Source:** `docs/design/references/components/ui/Input.tsx`
**Target:** `frontend/src/components/ui/Input.tsx`

**Key specs:**
- Glass background
- Focus ring: `ring-2 ring-turquoise-mist/30`
- Error state: `ring-loss/50`
- Monospace option for numeric inputs

---

### 2.8 Toggle
**Source:** `docs/design/references/components/ui/Toggle.tsx`
**Target:** `frontend/src/components/ui/Toggle.tsx`

---

### 2.9 Progress
**Source:** `docs/design/references/components/ui/Progress.tsx`
**Target:** `frontend/src/components/ui/Progress.tsx`

---

### 2.10 Tooltip
**Source:** `docs/design/references/components/ui/Tooltip.tsx`
**Target:** `frontend/src/components/ui/Tooltip.tsx`

---

### 2.11 Tabs
**Source:** `docs/design/references/components/ui/Tabs.tsx`
**Target:** `frontend/src/components/ui/Tabs.tsx`

**Key specs:**
- Animated underline indicator (framer-motion layoutId)
- Glass background for tab bar
- Used extensively (Cockpit live data, Alerts page, System page)

---

### 2.12 Modal
**Source:** `docs/design/references/components/ui/Modal.tsx`
**Target:** `frontend/src/components/ui/Modal.tsx`

**Key specs:**
- Backdrop: `bg-black/50 backdrop-blur-sm`
- Panel: GlassCard elevated variant
- Framer-motion enter/exit
- Focus trap
- Escape to close

---

### 2.13 SearchInput
**Source:** `docs/design/references/components/ui/SearchInput.tsx`
**Target:** `frontend/src/components/ui/SearchInput.tsx`

**Key specs:**
- Search icon left
- Cmd+K keyboard hint right
- Glass background
- Used in header

---

### 2.14 Dropdown
**Source:** `docs/design/references/components/ui/Dropdown.tsx`
**Target:** `frontend/src/components/ui/Dropdown.tsx`

**Key specs:**
- Glass panel
- Animated open/close
- Divider support
- Danger item styling
- Used for user menu, export menu

---

### 2.15 Toast
**Source:** `docs/design/references/components/ui/Toast.tsx`
**Target:** `frontend/src/components/ui/Toast.tsx`

---

### 2.16 EmptyState
**Source:** `docs/design/references/components/ui/EmptyState.tsx`
**Target:** `frontend/src/components/ui/EmptyState.tsx`

---

### 2.17 LoadingState
**Source:** `docs/design/references/components/ui/LoadingState.tsx`
**Target:** `frontend/src/components/ui/LoadingState.tsx`

---

### 2.18 MetricCard
**Source:** `docs/design/references/components/ui/MetricCard.tsx`
**Target:** `frontend/src/components/ui/MetricCard.tsx`

**This is the signature component.** Compare carefully with cockpit PDF:
- Label: `text-xs font-mono font-bold uppercase tracking-widest`
- Value: `font-mono font-medium tracking-tighter tabular-nums text-3xl`
- Trend indicator with arrow icon + percentage
- Sparkline zone: absolute bottom, h-20, opacity 30-40%
- Icon container: `p-1.5 rounded-lg backdrop-blur-sm`
- Min height: 140px
- GlassCard wrapper with hover animation

**Validation:** Must match the "NET LIQUIDITY / $994,272.52 / +1.24%" card in cockpit.pdf exactly.

---

### 2.19 DataTable
**Source:** `docs/design/references/components/dashboard/DataTable.tsx`
**Target:** `frontend/src/components/ui/DataTable.tsx`

**Key specs:**
- Glass-panel container
- Sticky header
- Hover highlight on rows
- Monospace for numbers
- Sortable columns

---

### 2.20 ErrorBoundary
**Source:** `docs/design/references/components/ui/ErrorBoundary.tsx`
**Target:** `frontend/src/components/ui/ErrorBoundary.tsx`

---

## Barrel Export

**File:** `frontend/src/components/ui/index.ts`

```typescript
export { GlassCard } from './GlassCard';
export { Badge } from './Badge';
export { Skeleton } from './Skeleton';
export { Logo } from './Logo';
export { Avatar } from './Avatar';
export { Button } from './Button';
export { Input } from './Input';
export { Toggle } from './Toggle';
export { Progress } from './Progress';
export { Tooltip } from './Tooltip';
export { Tabs } from './Tabs';
export { Modal } from './Modal';
export { SearchInput } from './SearchInput';
export { Dropdown } from './Dropdown';
export { Toast } from './Toast';
export { EmptyState } from './EmptyState';
export { LoadingState } from './LoadingState';
export { MetricCard } from './MetricCard';
export { DataTable } from './DataTable';
export { ErrorBoundary } from './ErrorBoundary';
```

---

## DevPage Component Gallery

Update `frontend/src/pages/DevPage.tsx` to show ALL 20 components with various props. This is your visual regression testing page.

Organize by category:
1. **Surfaces:** GlassCard (4 variants)
2. **Data Display:** Badge, MetricCard, DataTable, Progress
3. **Inputs:** Button, Input, Toggle, SearchInput
4. **Feedback:** Toast, Modal, Tooltip, EmptyState, LoadingState, Skeleton
5. **Navigation:** Tabs, Dropdown
6. **Branding:** Logo, Avatar

---

## Validation Checklist (ALL must pass before Phase 3)

- [ ] All 20 components render without errors
- [ ] All components work in light mode
- [ ] All components work in dark mode
- [ ] GlassCard: 4 variants visually distinct, blur effect visible
- [ ] MetricCard: matches cockpit PDF layout exactly
- [ ] Badge: translucent backgrounds (not solid)
- [ ] Logo: SVG wings render, "PARAVANT" in Cinzel
- [ ] Avatar: image loads, fallback works, status dot has glow
- [ ] Modal: backdrop blur, focus trap, escape to close
- [ ] Tabs: animated indicator slides between tabs
- [ ] DataTable: sortable, glass styling, monospace numbers
- [ ] All interactive components have visible focus indicators
