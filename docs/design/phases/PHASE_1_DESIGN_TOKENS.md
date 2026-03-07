# Phase 1: Design Tokens & Utilities

## Goal
Port the utility functions, animation configs, and theme context from the AI Studio prototype. These are the building blocks every component depends on.

## Pre-requisite
Phase 0 complete (Vite project running, Tailwind configured, fonts loading)

---

## Step 1.1: Port `lib/utils.ts`

**Source:** `docs/design/references/lib/utils.ts`
**Target:** `frontend/src/lib/utils.ts`

Port the file exactly. Key functions:
- `cn()` — Tailwind class merging (clsx + tailwind-merge)
- `formatCurrency()` — USD formatting with Intl.NumberFormat
- `formatNumber()` — Number with commas
- `formatPercent()` — Percentage formatting

**Adaptation needed:** Change `from '../../lib/utils'` imports to use `@/lib/utils` in consuming files.

---

## Step 1.2: Port `lib/animations.ts`

**Source:** `docs/design/references/lib/animations.ts`
**Target:** `frontend/src/lib/animations.ts`

This file defines Framer Motion animation presets:
- `smoothSpring` — `{ type: "spring", stiffness: 300, damping: 30 }`
- `gentleFade` — Opacity 0 to 1
- `hoverCard` — Scale 1.01 + translateY(-1px) on hover
- Any other animation configs

---

## Step 1.3: Port `contexts/ThemeContext.tsx`

**Source:** `docs/design/references/contexts/ThemeContext.tsx`
**Target:** `frontend/src/contexts/ThemeContext.tsx`

Key features:
- Mode: light / dark / system
- Theme: ocean / sapphire / emerald / onyx
- Compact mode toggle
- Reduced motion toggle
- Persist to localStorage
- Apply `dark` class on `<html>`
- Apply `data-theme` attribute on `<html>`
- Listen to `prefers-color-scheme` for system mode
- No flash of wrong theme on initial load

**Adaptation:** Change relative imports to `@/` aliases.

---

## Step 1.4: Port `contexts/ToastContext.tsx`

**Source:** `docs/design/references/contexts/ToastContext.tsx`
**Target:** `frontend/src/contexts/ToastContext.tsx`

Toast notification system:
- `addToast({ type, title, message, duration })`
- Stack in bottom-right
- Auto-dismiss
- Max 3 visible

---

## Step 1.5: Create Dev Validation Page

**File:** `frontend/src/pages/DevPage.tsx`

A developer-only page that displays:
1. All theme colors as swatches
2. Font samples (Cinzel, Inter, JetBrains Mono)
3. `formatCurrency(994272.52)` output
4. `formatPercent(0.0124)` output
5. Theme switcher (Ocean/Sapphire/Emerald/Onyx)
6. Light/Dark/System toggle
7. Animation demos (hover card, fade in)

This page lives at route `/dev` and will be used throughout all phases for visual validation.

---

## Validation Checklist

- [ ] `cn('px-4', 'py-2', conditional && 'bg-red')` merges classes correctly
- [ ] `formatCurrency(994272.52)` returns "$994,272.52"
- [ ] `formatPercent(0.0124)` returns "1.24%"
- [ ] Theme switching changes colors globally
- [ ] Dark mode toggle works without flash
- [ ] System mode follows OS preference
- [ ] Toast notifications appear and auto-dismiss
- [ ] Framer Motion animations work (no errors)
- [ ] All 4 theme variants change accent colors visually
